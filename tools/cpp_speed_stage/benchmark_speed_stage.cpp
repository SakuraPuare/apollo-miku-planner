// Paired, one-pass C++ speed-stage benchmark with real Python path samples.
// Uses exported JSONL references; path construction is excluded from timing.

#include "speed_stage.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

using json = nlohmann::json;
using namespace miku_speed;

namespace {

struct Case {
  std::string kind;
  int seed, blocked_idx;
  Scenario scenario;
  std::vector<double> stations, offsets;
  json expected;
};

struct Stage {
  std::vector<STBoundary> st;
  DPResult dp;
  STBounds bounds;
  QPResult qp;
  bool relaxed = false;
};

Case parse_case(const json& row) {
  if (row.at("schema_version") != "miku-speed-stage-v1")
    throw std::invalid_argument("unknown speed snapshot schema");
  Case item;
  item.kind = row.at("case_kind").get<std::string>();
  item.seed = row.at("seed").get<int>();
  item.blocked_idx = row.at("blocked_idx").get<int>();
  item.stations = row.at("path_stations").get<std::vector<double>>();
  item.offsets = row.at("path_offsets").get<std::vector<double>>();
  item.expected = row.at("expected");
  const auto& scenario = row.at("scenario");
  item.scenario.s_max = scenario.at("s_max").get<double>();
  item.scenario.t_max = scenario.at("t_max").get<double>();
  const auto& ego = scenario.at("ego");
  item.scenario.ego = {ego.at("s0").get<double>(), ego.at("l0").get<double>(),
                       ego.at("v0").get<double>(), ego.at("a0").get<double>(),
                       ego.at("W").get<double>(), ego.at("L").get<double>()};
  for (const auto& raw : scenario.at("obstacles")) {
    Obstacle obs;
    obs.s0 = raw.at("s0").get<double>();
    obs.l0 = raw.at("l0").get<double>();
    obs.vs = raw.at("vs").get<double>();
    obs.vl = raw.at("vl").get<double>();
    obs.W = raw.at("W").get<double>();
    obs.L = raw.at("L").get<double>();
    obs.is_static = raw.at("is_static").get<bool>();
    obs.name = raw.at("name").get<std::string>();
    obs.uncertainty_s0 = raw.at("uncertainty_s0").get<double>();
    obs.uncertainty_l0 = raw.at("uncertainty_l0").get<double>();
    obs.uncertainty_vs = raw.at("uncertainty_vs").get<double>();
    obs.uncertainty_vl = raw.at("uncertainty_vl").get<double>();
    item.scenario.obstacles.push_back(std::move(obs));
  }
  return item;
}

Stage run_stage(const Case& input) {
  Stage result;
  result.st = st_boundary_mapper(input.scenario, input.stations,
                                 input.offsets, true);
  result.dp = speed_dp(input.scenario, result.st);
  BoundsOptions options;
  options.safe_window_mode = true;
  result.bounds = build_st_bounds(input.scenario, result.st, result.dp, options);
  const double target = std::max(input.scenario.s_max - 1.0,
                                 input.scenario.ego.s0);
  for (auto& upper : result.bounds.upper) upper = std::min(upper, target);
  if (input.blocked_idx >= 0) {
    const double blocked_s = std::max(input.stations.at(input.blocked_idx) -
                                      input.scenario.ego.L / 2.0, 0.0);
    for (auto& upper : result.bounds.upper)
      upper = std::min(upper, blocked_s);
  }
  const double prior_lower = result.bounds.lower.back();
  result.bounds.lower.back() = std::min(target, result.bounds.upper.back());
  result.qp = speed_qp(input.scenario, result.bounds.upper,
                        result.bounds.lower, result.dp.ts);
  if (!result.qp.solved && result.bounds.lower.back() > prior_lower + 1e-9) {
    result.bounds.lower.back() = prior_lower;
    result.qp = speed_qp(input.scenario, result.bounds.upper,
                          result.bounds.lower, result.dp.ts);
    result.relaxed = true;
  }
  return result;
}

std::string validate(const Stage& value, const Case& input) {
  const auto& expected = input.expected;
  const auto& st_ref = expected.at("st_boundaries");
  if (value.st.size() != st_ref.size()) return "ST boundary count";
  for (size_t b = 0; b < value.st.size(); ++b) {
    if (value.st[b].intervals.size() != st_ref[b].size())
      return "ST interval count boundary " + std::to_string(b);
    for (size_t i = 0; i < value.st[b].intervals.size(); ++i) {
      const auto& actual = value.st[b].intervals[i];
      if (std::abs(actual.t - st_ref[b][i][0].get<double>()) > 1e-8 ||
          std::abs(actual.s_lo - st_ref[b][i][1].get<double>()) > 1e-8 ||
          std::abs(actual.s_hi - st_ref[b][i][2].get<double>()) > 1e-8)
        return "ST interval values boundary " + std::to_string(b);
    }
  }
  const auto ref_dp = expected.at("dp_s").get<std::vector<double>>();
  if (ref_dp.size() != value.dp.s_dp.size()) return "DP grid size";
  for (size_t j = 0; j < ref_dp.size(); ++j)
    if (std::abs(ref_dp[j] - value.dp.s_dp[j]) > 1e-8) return "DP trajectory";
  size_t forbidden_count = 0;
  for (const auto& row : value.dp.forbidden)
    forbidden_count += std::count(row.begin(), row.end(), true);
  if (forbidden_count != expected.at("forbidden_count").get<size_t>())
    return "DP forbidden occupancy";
  const auto check_grid = [&](const std::vector<double>& data,
                              const char* name) -> std::string {
    const auto reference = expected.at(name).get<std::vector<double>>();
    if (data.size() != reference.size()) return std::string(name) + " size";
    for (size_t j = 0; j < data.size(); ++j)
      if (std::abs(data[j] - reference[j]) > 1e-7)
        return std::string(name) + " at grid " + std::to_string(j);
    return {};
  };
  for (const char* name : {"upper", "lower"}) {
    const std::string error = check_grid(
        std::string(name) == "upper" ? value.bounds.upper : value.bounds.lower, name);
    if (!error.empty()) return error;
  }
  const auto& statuses = expected.at("decision_statuses");
  const auto& labels = expected.at("decision_labels");
  if (value.bounds.decisions.size() != statuses.size()) return "decision count";
  for (size_t j = 0; j < value.bounds.decisions.size(); ++j) {
    if (value.bounds.decisions[j].status != statuses[j].get<std::string>() ||
        value.bounds.decisions[j].homotopy_label != labels[j].get<std::string>())
      return "temporal graph decision";
  }
  if (value.relaxed != expected.at("terminal_goal_relaxed").get<bool>())
    return "terminal goal retry";
  if (value.qp.solved != expected.at("solved").get<bool>())
    return "OSQP feasibility";
  if (value.qp.solved) {
    // Compare trajectory, not merely status/end state; platform OSQP
    // settings and C/Python library versions can differ slightly.
    for (const char* name : {"s", "v", "a"}) {
      const std::vector<double>& values = std::string(name) == "s" ? value.qp.s :
          (std::string(name) == "v" ? value.qp.v : value.qp.a);
      const auto reference = expected.at(name).get<std::vector<double>>();
      if (values.size() != reference.size()) return std::string(name) + " size";
      for (size_t j = 0; j < values.size(); ++j)
        if (std::abs(values[j] - reference[j]) > 1e-2)
          return std::string(name) + " QP trajectory grid " + std::to_string(j);
    }
  }
  return {};
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc < 3 || argc > 5) {
      std::cerr << "usage: " << argv[0] <<
          " INPUT.jsonl OUTPUT.csv [LIMIT] [REPEATS]\n";
      return 1;
    }
    const int limit = argc > 3 ? std::stoi(argv[3]) : 3500;
    const int repeats = argc > 4 ? std::stoi(argv[4]) : 3;
    if (limit <= 0 || repeats <= 0) throw std::invalid_argument("invalid limit/repeats");
    std::ifstream source(argv[1]);
    std::ofstream destination(argv[2]);
    if (!source || !destination) throw std::runtime_error("cannot open input or output");
    destination << "case_kind,seed,runtime_ms,repeats,solved,terminal_goal_relaxed,parity_ok,parity_reason\n";
    std::string line;
    int count = 0, parity = 0;
    double total_ms = 0.0;
    while (count < limit && std::getline(source, line)) {
      if (line.empty()) continue;
      const Case input = parse_case(json::parse(line));
      Stage warm = run_stage(input);
      const std::string problem = validate(warm, input);
      if (problem.empty()) ++parity;
      else if (count < 10) std::cerr << input.kind << '/' << input.seed <<
                                     ": " << problem << '\n';
      std::vector<double> readings;
      readings.reserve(repeats);
      for (int i = 0; i < repeats; ++i) {
        const auto start = std::chrono::steady_clock::now();
        Stage run = run_stage(input);
        const double elapsed_ms = std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - start).count();
        if (!std::isfinite(elapsed_ms)) throw std::runtime_error("invalid runtime");
        readings.push_back(elapsed_ms);
        if (i == 0 && validate(run, input) != problem)
          throw std::runtime_error("non-deterministic stage parity");
      }
      std::sort(readings.begin(), readings.end());
      const double median = readings[readings.size() / 2];
      total_ms += median;
      destination << input.kind << ',' << input.seed << ',' <<
          std::setprecision(12) << median << ',' << repeats << ',' <<
          static_cast<int>(warm.qp.solved) << ',' << static_cast<int>(warm.relaxed)
          << ',' << static_cast<int>(problem.empty()) << ',' << problem << '\n';
      if (++count % 250 == 0)
        std::cout << "benchmarked " << count << " C++ speed stages\n";
    }
    std::cout << "C++ speed stage cases=" << count << " parity=" << parity <<
        " mean_ms=" << std::setprecision(8) << total_ms / count <<
        " output=" << argv[2] << '\n';
    return count == parity ? 0 : 2;
  } catch (const std::exception& error) {
    std::cerr << "speed-stage benchmark: " << error.what() << '\n';
    return 1;
  }
}

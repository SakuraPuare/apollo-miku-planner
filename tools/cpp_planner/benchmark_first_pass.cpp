// Initial MIKU path+speed pipeline, paired against frozen Python snapshots.
// Scenario parsing and parity checks are outside the timed planning region.

#include "miku_path_bounds.h"
#include "miku_path_qp.h"
#include "speed_stage.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace {

using Json = nlohmann::json;

struct Case {
  std::string kind;
  int seed = 0;
  miku_cpp_path::Scenario path_scenario;
  miku_speed::Scenario speed_scenario;
  std::vector<double> expected_stations, expected_offsets;
  int expected_blocked = -1;
  Json expected_speed;
  Json expected_full;
};

struct PipelineResult {
  miku_cpp_path::PathResult path_bounds;
  miku_path_qp::PathResult path;
  miku_speed::DPResult dp;
  miku_speed::STBounds speed_bounds;
  miku_speed::QPResult speed;
  std::vector<double> curvature, lateral_acceleration;
  bool relaxed = false;
};

double Interpolate(const std::vector<double>& xs, const std::vector<double>& ys,
                   double x);

Case ParseCase(const Json& row) {
  if (row.at("schema_version") != "miku-speed-stage-v1") {
    throw std::invalid_argument("unknown snapshot schema");
  }
  Case item;
  item.kind = row.at("case_kind").get<std::string>();
  item.seed = row.at("seed").get<int>();
  item.expected_stations = row.at("path_stations").get<std::vector<double>>();
  item.expected_offsets = row.at("path_offsets").get<std::vector<double>>();
  item.expected_blocked = row.at("blocked_idx").get<int>();
  item.expected_speed = row.at("expected");
  if (row.contains("expected_full")) item.expected_full = row.at("expected_full");
  const auto& raw = row.at("scenario");
  auto& path = item.path_scenario;
  auto& speed = item.speed_scenario;
  path.s_max = speed.s_max = raw.at("s_max").get<double>();
  path.l_road_min = raw.value("l_road_min", path.l_road_min);
  path.l_road_max = raw.value("l_road_max", path.l_road_max);
  path.delta_min = raw.value("delta_min", path.delta_min);
  path.delta_max = raw.value("delta_max", path.delta_max);
  path.lane_borrow = raw.value("lane_borrow", path.lane_borrow);
  path.lane_width = raw.value("lane_width", path.lane_width);
  speed.t_max = raw.at("t_max").get<double>();
  const auto& ego = raw.at("ego");
  path.ego.s0 = speed.ego.s0 = ego.at("s0").get<double>();
  path.ego.l0 = speed.ego.l0 = ego.at("l0").get<double>();
  path.ego.v0 = speed.ego.v0 = ego.at("v0").get<double>();
  path.ego.a0 = speed.ego.a0 = ego.at("a0").get<double>();
  path.ego.width = speed.ego.W = ego.at("W").get<double>();
  path.ego.length = speed.ego.L = ego.at("L").get<double>();
  for (const auto& raw_obs : raw.at("obstacles")) {
    miku_cpp_path::Obstacle path_obs;
    miku_speed::Obstacle speed_obs;
    path_obs.s0 = speed_obs.s0 = raw_obs.at("s0").get<double>();
    path_obs.l0 = speed_obs.l0 = raw_obs.at("l0").get<double>();
    path_obs.vs = speed_obs.vs = raw_obs.at("vs").get<double>();
    path_obs.vl = speed_obs.vl = raw_obs.at("vl").get<double>();
    path_obs.width = speed_obs.W = raw_obs.at("W").get<double>();
    path_obs.length = speed_obs.L = raw_obs.at("L").get<double>();
    path_obs.is_static = speed_obs.is_static = raw_obs.at("is_static").get<bool>();
    path_obs.type = raw_obs.at("obs_type").get<std::string>();
    speed_obs.name = raw_obs.at("name").get<std::string>();
    speed_obs.uncertainty_s0 = raw_obs.at("uncertainty_s0").get<double>();
    speed_obs.uncertainty_l0 = raw_obs.at("uncertainty_l0").get<double>();
    speed_obs.uncertainty_vs = raw_obs.at("uncertainty_vs").get<double>();
    speed_obs.uncertainty_vl = raw_obs.at("uncertainty_vl").get<double>();
    path.obstacles.push_back(std::move(path_obs));
    speed.obstacles.push_back(std::move(speed_obs));
  }
  return item;
}

PipelineResult RunFirstPass(const Case& input, int spatial_rank = 0,
    int temporal_rank = 0, const std::function<double(double)>& tau_fn = {}) {
  PipelineResult result;
  result.path_bounds = miku_cpp_path::PathBounds(input.path_scenario,
                                                spatial_rank, tau_fn);
  result.path = miku_path_qp::OptimizePath(result.path_bounds.stations,
                                          result.path_bounds.lower,
                                          result.path_bounds.upper);
  const auto st = miku_speed::st_boundary_mapper(input.speed_scenario,
      result.path_bounds.stations, result.path.lateral, true);
  result.dp = miku_speed::speed_dp(input.speed_scenario, st);
  miku_speed::BoundsOptions options;
  options.safe_window_mode = true;
  options.tau_fn = tau_fn;
  options.temporal_plan_rank = temporal_rank;
  result.speed_bounds = miku_speed::build_st_bounds(input.speed_scenario, st,
                                                    result.dp, options);
  const double target = std::max(input.speed_scenario.s_max - 1.0,
                                 input.speed_scenario.ego.s0);
  for (double& upper : result.speed_bounds.upper) upper = std::min(upper, target);
  if (result.path_bounds.blocked_index >= 0) {
    const double blocked = std::max(
        result.path_bounds.stations.at(result.path_bounds.blocked_index) -
        input.speed_scenario.ego.L / 2.0, 0.0);
    for (double& upper : result.speed_bounds.upper) upper = std::min(upper, blocked);
  }
  const double prior_lower = result.speed_bounds.lower.back();
  result.speed_bounds.lower.back() =
      std::min(target, result.speed_bounds.upper.back());
  result.speed = miku_speed::speed_qp(input.speed_scenario,
      result.speed_bounds.upper, result.speed_bounds.lower, result.dp.ts);
  if (!result.speed.solved &&
      result.speed_bounds.lower.back() > prior_lower + 1e-9) {
    result.speed_bounds.lower.back() = prior_lower;
    result.speed = miku_speed::speed_qp(input.speed_scenario,
        result.speed_bounds.upper, result.speed_bounds.lower, result.dp.ts);
    result.relaxed = true;
  }
  const auto& offsets = result.path.lateral;
  result.curvature.assign(offsets.size(), 0.0);
  if (offsets.size() >= 3) {
    const double ds = result.path_bounds.stations[1] - result.path_bounds.stations[0];
    for (std::size_t i = 1; i + 1 < offsets.size(); ++i)
      result.curvature[i] = (offsets[i+1] - 2.0*offsets[i] + offsets[i-1]) /
                            (ds*ds);
    result.curvature.front() = result.curvature[1];
    result.curvature.back() = result.curvature[offsets.size()-2];
  }
  if (result.speed.solved) {
    for (std::size_t i = 0; i < result.speed.s.size(); ++i) {
      const double kappa = Interpolate(result.path_bounds.stations,
                                       result.curvature, result.speed.s[i]);
      result.lateral_acceleration.push_back(result.speed.v[i] *
                                            result.speed.v[i] * kappa);
    }
  }
  return result;
}

double Interpolate(const std::vector<double>& xs, const std::vector<double>& ys,
                   double x) {
  if (xs.empty() || xs.size() != ys.size())
    throw std::invalid_argument("invalid interpolation knots");
  if (x <= xs.front()) return ys.front();
  if (x >= xs.back()) return ys.back();
  const auto hi = std::upper_bound(xs.begin(), xs.end(), x) - xs.begin();
  const auto lo = hi - 1;
  const double alpha = (x - xs[lo]) / (xs[hi] - xs[lo]);
  return ys[lo] + alpha * (ys[hi] - ys[lo]);
}

std::function<double(double)> TrajectoryTau(const PipelineResult& result,
                                            const Case& input) {
  const auto& s = result.speed.s;
  if (!result.speed.solved || s.size() < 2)
    return [scn = input.path_scenario](double x) {
      return miku_cpp_path::ArrivalTime(x, scn);
    };
  std::vector<double> unique_s, unique_t;
  for (std::size_t j = 0; j < s.size(); ++j) {
    if (!unique_s.empty() && std::max(s[j], unique_s.back()) <= unique_s.back())
      continue;
    unique_s.push_back(s[j]);
    unique_t.push_back(result.dp.ts[j]);
  }
  const double last_s = unique_s.back(), last_t = unique_t.back();
  const double speed = std::max(result.speed.v.back(), 0.5);
  return [unique_s = std::move(unique_s), unique_t = std::move(unique_t),
          last_s, last_t, speed](double x) {
    if (x > last_s) return last_t + (x - last_s) / speed;
    return Interpolate(unique_s, unique_t, x);
  };
}

using Score = std::tuple<int, int, int, double>;

Score PlannerScore(const PipelineResult& result, const Case& input) {
  if (!result.speed.solved || result.speed.s.empty())
    return {0, 0, 0, -std::numeric_limits<double>::infinity()};
  const double goal = std::max(input.speed_scenario.s_max - 1.0,
                               input.speed_scenario.ego.s0);
  const double progress = result.speed.s.back();
  return {1, static_cast<int>(progress >= goal - 1e-3),
          static_cast<int>(!result.relaxed), progress};
}

struct CompleteResult {
  PipelineResult best;
  int iterations = 1;
  bool converged = false;
};

CompleteResult RunMethod(const Case& input) {
  CompleteResult method;
  auto result = RunFirstPass(input);
  if (!result.speed.solved) {
    const auto spatial_count = std::max<std::size_t>(1,
        std::min<std::size_t>(3, result.path_bounds.spatial_candidate_count));
    for (std::size_t spatial_rank = 0; spatial_rank < spatial_count; ++spatial_rank) {
      auto spatial = result;
      if (spatial_rank > 0) {
        spatial = RunFirstPass(input, static_cast<int>(spatial_rank));
        if (spatial.speed.solved) {
          result = std::move(spatial);
          break;
        }
      }
      std::size_t temporal_count = 0;
      for (const auto& decision : spatial.speed_bounds.decisions) {
        temporal_count = std::max(temporal_count,
            static_cast<std::size_t>(decision.graph_candidate_count));
      }
      temporal_count = std::max<std::size_t>(1,
          std::min<std::size_t>(3, temporal_count));
      for (std::size_t temporal_rank = 1; temporal_rank < temporal_count; ++temporal_rank) {
        auto alternate = RunFirstPass(input, static_cast<int>(spatial_rank),
                                      static_cast<int>(temporal_rank));
        if (alternate.speed.solved) {
          result = std::move(alternate);
          break;
        }
      }
      if (result.speed.solved) break;
    }
  }
  method.best = result;
  bool any_dynamic = false, any_static = false;
  for (const auto& obs : input.path_scenario.obstacles) {
    any_dynamic |= !obs.is_static;
    any_static |= obs.is_static;
  }
  if (std::get<1>(PlannerScore(result, input)) == 0 && any_dynamic && !any_static) {
    std::vector<double> probes, previous_tau;
    probes.reserve(64);
    previous_tau.reserve(64);
    for (int i = 0; i < 64; ++i) {
      const double s = input.path_scenario.ego.s0 +
          (input.path_scenario.s_max - input.path_scenario.ego.s0) * i / 63.0;
      probes.push_back(s);
      previous_tau.push_back(miku_cpp_path::ArrivalTime(s, input.path_scenario));
    }
    const auto trajectory_tau = TrajectoryTau(result, input);
    std::vector<double> updated_tau;
    updated_tau.reserve(probes.size());
    double max_change = 0.0;
    for (std::size_t j = 0; j < probes.size(); ++j) {
      const double updated = 0.7 * trajectory_tau(probes[j]) +
                             0.3 * previous_tau[j];
      updated_tau.push_back(updated);
      max_change = std::max(max_change, std::abs(updated - previous_tau[j]));
    }
    const auto damped_tau = [probes = std::move(probes),
                             updated_tau = std::move(updated_tau)](double s) {
      return Interpolate(probes, updated_tau, s);
    };
    result = RunFirstPass(input, 0, 0, damped_tau);
    method.iterations = 2;
    if (PlannerScore(result, input) > PlannerScore(method.best, input))
      method.best = std::move(result);
    if (max_change <= 0.05) method.converged = true;
  }
  return method;
}

std::string Compare(const std::vector<double>& actual,
                    const std::vector<double>& expected, double tolerance,
                    const char* name) {
  if (actual.size() != expected.size()) return std::string(name) + " length";
  for (std::size_t i = 0; i < actual.size(); ++i) {
    if (!std::isfinite(actual[i]) || std::abs(actual[i] - expected[i]) > tolerance)
      return std::string(name) + " at " + std::to_string(i);
  }
  return {};
}

std::string Validate(const PipelineResult& result, const Case& input) {
  if (const auto err = Compare(result.path_bounds.stations,
          input.expected_stations, 1e-9, "path stations"); !err.empty()) return err;
  if (result.path_bounds.blocked_index != input.expected_blocked)
    return "blocked index";
  if (const auto err = Compare(result.path.lateral,
          input.expected_offsets, 1e-2, "path offsets"); !err.empty()) return err;
  const auto& expected = input.expected_speed;
  if (result.speed.solved != expected.at("solved").get<bool>())
    return "speed QP status";
  if (result.relaxed != expected.at("terminal_goal_relaxed").get<bool>())
    return "terminal retry";
  if (const auto err = Compare(result.speed_bounds.upper,
          expected.at("upper").get<std::vector<double>>(), 1e-2, "ST upper");
      !err.empty()) return err;
  if (const auto err = Compare(result.speed_bounds.lower,
          expected.at("lower").get<std::vector<double>>(), 1e-2, "ST lower");
      !err.empty()) return err;
  if (!result.speed.solved) return {};
  for (const char* name : {"s", "v", "a"}) {
    const auto& actual = std::string(name) == "s" ? result.speed.s :
                         std::string(name) == "v" ? result.speed.v : result.speed.a;
    if (const auto err = Compare(actual,
            expected.at(name).get<std::vector<double>>(), 1e-2, name);
        !err.empty()) return err;
  }
  return {};
}

std::string ValidateFull(const CompleteResult& method, const Case& input) {
  const auto& reference = input.expected_full;
  if (reference.is_null()) return "missing full-method reference";
  if (method.iterations != reference.at("iterations").get<int>())
    return "iteration count";
  if (method.converged != reference.at("converged").get<bool>())
    return "convergence";
  const auto& result = method.best;
  if (const auto err = Compare(result.path_bounds.stations,
          reference.at("path_stations").get<std::vector<double>>(),
          1e-9, "full path stations"); !err.empty()) return err;
  if (const auto err = Compare(result.path.lateral,
          reference.at("path_offsets").get<std::vector<double>>(),
          1e-2, "full path offsets"); !err.empty()) return err;
  if (const auto err = Compare(result.curvature,
          reference.at("curvature").get<std::vector<double>>(),
          1e-2, "full curvature"); !err.empty()) return err;
  if (result.path_bounds.blocked_index != reference.at("blocked_idx").get<int>())
    return "full blocked index";
  if (result.path_bounds.spatial_candidate_count !=
      reference.at("spatial_candidate_count").get<std::size_t>())
    return "full spatial candidate count";
  std::size_t temporal_count = 0;
  for (const auto& decision : result.speed_bounds.decisions)
    temporal_count = std::max(temporal_count,
        static_cast<std::size_t>(decision.graph_candidate_count));
  if (temporal_count != reference.at("temporal_candidate_count").get<std::size_t>())
    return "full temporal candidate count";
  if (result.relaxed != reference.at("terminal_goal_relaxed").get<bool>())
    return "full terminal retry";
  if (result.speed.solved != !reference.at("s").is_null())
    return "full speed QP status";
  if (!result.speed.solved) return {};
  if (const auto err = Compare(result.lateral_acceleration,
          reference.at("lateral_acceleration").get<std::vector<double>>(),
          1e-2, "full lateral acceleration"); !err.empty()) return err;
  for (const char* name : {"s", "v", "a"}) {
    const auto& actual = std::string(name) == "s" ? result.speed.s :
                         std::string(name) == "v" ? result.speed.v : result.speed.a;
    if (const auto err = Compare(actual,
            reference.at(name).get<std::vector<double>>(), 1e-2, name);
        !err.empty()) return err;
  }
  return {};
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc < 3 || argc > 6) {
      std::cerr << "usage: " << argv[0]
                << " INPUT.jsonl OUTPUT.csv [LIMIT] [REPEATS] [first|full]\n";
      return 1;
    }
    const int limit = argc > 3 ? std::stoi(argv[3]) : 3500;
    const int repeats = argc > 4 ? std::stoi(argv[4]) : 3;
    const std::string mode = argc > 5 ? argv[5] : "first";
    if (limit <= 0 || repeats <= 0) throw std::invalid_argument("limit/repeats");
    if (mode != "first" && mode != "full") throw std::invalid_argument("mode");
    std::ifstream source(argv[1]);
    std::ofstream output(argv[2]);
    if (!source || !output) throw std::runtime_error("cannot open input/output");
    output << "case_kind,seed,runtime_ms,repeats,path_qp_solved,speed_qp_solved,"
              "terminal_goal_relaxed,iterations,converged,parity_ok,parity_reason\n";
    int cases = 0, matched = 0;
    double total_ms = 0.0;
    std::string line;
    while (cases < limit && std::getline(source, line)) {
      if (line.empty()) continue;
      const Case input = ParseCase(Json::parse(line));
      const auto run = [&]() -> CompleteResult {
        if (mode == "full") return RunMethod(input);
        return {RunFirstPass(input), 1, false};
      };
      const auto validate = [&](const CompleteResult& outcome) {
        return mode == "full" ? ValidateFull(outcome, input) :
                                Validate(outcome.best, input);
      };
      const auto warmup = run();
      const auto problem = validate(warmup);
      if (problem.empty()) ++matched;
      else if (cases < 10) std::cerr << input.kind << '/' << input.seed << ": "
                                    << problem << '\n';
      std::vector<double> timings;
      timings.reserve(repeats);
      for (int i = 0; i < repeats; ++i) {
        const auto start = std::chrono::steady_clock::now();
        const auto result = run();
        const auto elapsed = std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - start).count();
        if (i == 0 && validate(result) != problem)
          throw std::runtime_error("non-deterministic parity");
        timings.push_back(elapsed);
      }
      std::sort(timings.begin(), timings.end());
      const double median = timings[timings.size() / 2];
      total_ms += median;
      output << input.kind << ',' << input.seed << ',' << std::setprecision(12)
             << median << ',' << repeats << ',' << warmup.best.path.solved << ','
             << warmup.best.speed.solved << ',' << warmup.best.relaxed << ','
             << warmup.iterations << ',' << warmup.converged << ','
             << problem.empty() << ',' << problem << '\n';
      if (++cases % 250 == 0)
        std::cout << "benchmarked " << cases << " C++ " << mode << " cases\n";
    }
    std::cout << "C++ " << mode << " cases=" << cases << " parity=" << matched
              << " mean_ms=" << total_ms / cases << '\n';
    return cases == matched ? 0 : 2;
  } catch (const std::exception& err) {
    std::cerr << "first-pass benchmark: " << err.what() << '\n';
    return 1;
  }
}

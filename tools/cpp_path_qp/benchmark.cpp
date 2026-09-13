// Run the frozen Python path QP's numerical inputs through the C++ OSQP port.

#include "tools/cpp_path_qp/miku_path_qp.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include <osqp/osqp.h>

namespace {

struct Case {
  std::string kind;
  int seed = -1;
  int blocked = -1;
  int candidate_count = 0;
  std::vector<double> station;
  std::vector<double> lower;
  std::vector<double> upper;
  std::vector<double> expected;
};

std::vector<std::string> SplitTsv(const std::string& line) {
  std::vector<std::string> values;
  std::istringstream stream(line);
  std::string value;
  while (std::getline(stream, value, '\t')) {
    values.push_back(value);
  }
  return values;
}

std::vector<Case> ReadCases(const std::string& path) {
  std::ifstream stream(path);
  if (!stream) {
    throw std::runtime_error("cannot read path input: " + path);
  }
  std::string line;
  if (!std::getline(stream, line) ||
      line != "case_kind\tseed\tstation_idx\ts\tl_min\tl_max\t"
              "expected_l_path\tblocked_idx\tspatial_candidate_count") {
    throw std::runtime_error("unexpected path input TSV schema");
  }
  std::vector<Case> cases;
  while (std::getline(stream, line)) {
    if (line.empty()) {
      continue;
    }
    const auto row = SplitTsv(line);
    if (row.size() != 9) {
      throw std::runtime_error("incorrect station TSV column count");
    }
    const int seed = std::stoi(row[1]);
    if (cases.empty() || cases.back().kind != row[0] ||
        cases.back().seed != seed) {
      Case value;
      value.kind = row[0];
      value.seed = seed;
      value.blocked = std::stoi(row[7]);
      value.candidate_count = std::stoi(row[8]);
      cases.push_back(std::move(value));
    }
    auto& current = cases.back();
    if (current.station.size() != static_cast<std::size_t>(std::stoi(row[2])) ||
        current.blocked != std::stoi(row[7]) ||
        current.candidate_count != std::stoi(row[8])) {
      throw std::runtime_error("station index or case metadata is inconsistent");
    }
    current.station.push_back(std::stod(row[3]));
    current.lower.push_back(std::stod(row[4]));
    current.upper.push_back(std::stod(row[5]));
    current.expected.push_back(std::stod(row[6]));
  }
  if (cases.empty()) {
    throw std::runtime_error("no path-QP input cases");
  }
  return cases;
}

void Benchmark(const std::vector<Case>& cases, const std::string& output_path,
               int repeats, double tolerance) {
  if (repeats <= 0 || tolerance <= 0.0) {
    throw std::invalid_argument("repeat count and numeric tolerance must be positive");
  }
  std::ofstream output(output_path);
  if (!output) {
    throw std::runtime_error("cannot write raw path-QP timing: " + output_path);
  }
  output << "case_kind,seed,station_count,blocked_idx,repeats,runtime_ms,"
            "max_abs_error_m,solved,iterations,solver_ms\n"
         << std::setprecision(17);
  int mismatch_count = 0;
  std::string first_mismatch;
  double worst_error = 0.0;
  double total_ms = 0.0;
  double checksum = 0.0;
  int solved_count = 0;
  for (const auto& test_case : cases) {
    for (int i = 0; i < 3; ++i) {
      const auto result = miku_path_qp::OptimizePath(
          test_case.station, test_case.lower, test_case.upper);
      checksum += std::accumulate(result.lateral.begin(), result.lateral.end(), 0.0);
    }
    const auto started = std::chrono::steady_clock::now();
    miku_path_qp::PathResult result;
    for (int i = 0; i < repeats; ++i) {
      result = miku_path_qp::OptimizePath(
          test_case.station, test_case.lower, test_case.upper);
      checksum += std::accumulate(result.lateral.begin(), result.lateral.end(), 0.0);
    }
    const auto finished = std::chrono::steady_clock::now();
    const double elapsed_ms =
        std::chrono::duration<double, std::milli>(finished - started).count();
    const double runtime_ms = elapsed_ms / repeats;
    total_ms += elapsed_ms;
    solved_count += result.solved ? 1 : 0;
    double error = 0.0;
    for (std::size_t i = 0; i < result.lateral.size(); ++i) {
      error = std::max(error, std::abs(result.lateral[i] - test_case.expected[i]));
    }
    worst_error = std::max(worst_error, error);
    if (!std::isfinite(error) || error > tolerance) {
      ++mismatch_count;
      if (first_mismatch.empty()) {
        first_mismatch = test_case.kind + "/" + std::to_string(test_case.seed);
      }
    }
    output << test_case.kind << ',' << test_case.seed << ','
           << test_case.station.size() << ',' << test_case.blocked << ','
           << repeats << ',' << runtime_ms << ',' << error << ','
           << (result.solved ? 1 : 0) << ',' << result.iterations << ','
           << result.solver_ms << '\n';
  }
  std::cout << "osqp_version=" << osqp_version() << " cases=" << cases.size()
            << " solved=" << solved_count << " mismatch=" << mismatch_count
            << " max_abs_error_m=" << worst_error << " total_elapsed_s="
            << total_ms / 1000.0 << " checksum=" << checksum << '\n';
  if (mismatch_count) {
    throw std::runtime_error("path-QP mismatch vs Python at " + first_mismatch);
  }
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 4 && argc != 5) {
      std::cerr << "usage: " << argv[0]
                << " input.tsv cpp_raw.csv repeats [abs_tolerance_m=0.001]\n";
      return 2;
    }
    const auto cases = ReadCases(argv[1]);
    Benchmark(cases, argv[2], std::stoi(argv[3]),
              argc == 5 ? std::stod(argv[4]) : 0.001);
  } catch (const std::exception& error) {
    std::cerr << "path-QP benchmark error: " << error.what() << '\n';
    return 1;
  }
}

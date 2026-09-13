#include "miku_case_csv.h"

#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

volatile double checksum_sink = 0.0;

void WriteCsvField(std::ostream& output, const std::string& value) {
  if (value.find_first_of(",\"\n\r") == std::string::npos) {
    output << value;
    return;
  }
  output << '"';
  for (char ch : value) {
    if (ch == '"') output << '"';
    output << ch;
  }
  output << '"';
}

void Run(const std::string& input_filename, const std::string& output_filename,
         int repeat, int rank) {
  const auto cases = miku_cpp_path::ReadCaseCsv(input_filename);
  std::ofstream output(output_filename);
  if (!output) throw std::runtime_error("cannot open output: " + output_filename);
  output << std::setprecision(17);
  output << "case_kind,seed,station_idx,s,l_min,l_max,blocked_idx,group_count,"
            "spatial_candidate_count,runtime_ms\n";
  double elapsed_ms = 0.0;
  std::size_t station_count = 0;
  double checksum = 0.0;
  for (const auto& item : cases) {
    for (int warmup = 0; warmup < 3; ++warmup) {
      checksum_sink = miku_cpp_path::PathBounds(item.scenario, rank).lower.front();
    }
    miku_cpp_path::PathResult result;
    const auto begin = std::chrono::steady_clock::now();
    for (int i = 0; i < repeat; ++i) {
      result = miku_cpp_path::PathBounds(item.scenario, rank);
      checksum += result.lower.front() + result.upper.back() +
                  result.blocked_index + result.spatial_candidate_count;
    }
    const auto end = std::chrono::steady_clock::now();
    const double runtime_ms =
        std::chrono::duration<double, std::milli>(end - begin).count() / repeat;
    elapsed_ms += runtime_ms * repeat;
    station_count += result.stations.size();
    for (std::size_t i = 0; i < result.stations.size(); ++i) {
      WriteCsvField(output, item.kind);
      output << ',' << item.seed << ',' << i << ',' << result.stations[i] << ','
             << result.lower[i] << ',' << result.upper[i] << ','
             << result.blocked_index << ',' << result.groups.size() << ','
             << result.spatial_candidate_count << ',' << runtime_ms << '\n';
    }
  }
  checksum_sink = checksum;
  std::cout << std::setprecision(17)
            << "{\"case_count\":" << cases.size()
            << ",\"station_count\":" << station_count
            << ",\"repeat_count\":" << repeat
            << ",\"candidate_rank\":" << rank
            << ",\"elapsed_s\":" << elapsed_ms / 1000.0
            << ",\"per_call_us\":"
            << elapsed_ms * 1000.0 / (repeat * cases.size())
            << ",\"checksum\":" << checksum_sink << "}\n";
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 3 && argc != 4 && argc != 5) {
      throw std::invalid_argument(
          "usage: run_path_bounds INPUT.csv OUTPUT.csv [REPEAT=1] [CANDIDATE_RANK=0]");
    }
    const int repeat = argc >= 4 ? std::stoi(argv[3]) : 1;
    const int rank = argc >= 5 ? std::stoi(argv[4]) : 0;
    if (repeat <= 0 || rank < 0) {
      throw std::invalid_argument("repeat must be positive; rank nonnegative");
    }
    Run(argv[1], argv[2], repeat, rank);
  } catch (const std::exception& exception) {
    std::cerr << exception.what() << '\n';
    return EXIT_FAILURE;
  }
}

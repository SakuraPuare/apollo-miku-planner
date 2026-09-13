// Standalone benchmark for the geometry primitives in miku_geometry.py.
// It measures no QP solve, temporal search, safety certificate, or Apollo cycle.

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace {

struct Interval {
  double u;
  double v;
};

struct Band {
  int split;
  double lower;
  double upper;
  double gap;
  std::vector<int> directions;
};

struct GapResult {
  std::vector<int> ordered_indices;
  int split;
  double lower;
  double upper;
  double gap;
  std::vector<double> candidate_gaps;
  std::vector<double> prefix_max_v;
  std::vector<int> directions;
};

struct Case {
  std::string kind;
  int seed;
  int group;
  double road_lower;
  double road_upper;
  std::vector<Interval> intervals;
  int expected_split = -1;
  double expected_gap = 0.0;
  double expected_lower = 0.0;
  double expected_upper = 0.0;
  std::vector<Band> expected_bands;
};

volatile double checksum_sink = 0.0;

std::vector<std::string> ParseCsvLine(const std::string& line) {
  std::vector<std::string> fields;
  std::string field;
  bool quoted = false;
  for (std::size_t i = 0; i < line.size(); ++i) {
    const char ch = line[i];
    if (ch == '"') {
      if (quoted && i + 1 < line.size() && line[i + 1] == '"') {
        field += '"';
        ++i;
      } else {
        quoted = !quoted;
      }
    } else if (ch == ',' && !quoted) {
      fields.push_back(std::move(field));
      field.clear();
    } else {
      field += ch;
    }
  }
  if (quoted) {
    throw std::runtime_error("unclosed CSV quote");
  }
  if (!field.empty() && field.back() == '\r') {
    field.pop_back();
  }
  fields.push_back(std::move(field));
  return fields;
}

std::vector<int> OrderedIndices(const std::vector<Interval>& intervals) {
  std::vector<int> indices(intervals.size());
  std::iota(indices.begin(), indices.end(), 0);
  std::sort(indices.begin(), indices.end(), [&](int a, int b) {
    if (intervals[a].u != intervals[b].u) {
      return intervals[a].u < intervals[b].u;
    }
    if (intervals[a].v != intervals[b].v) {
      return intervals[a].v > intervals[b].v;
    }
    return a < b;
  });
  return indices;
}

std::vector<double> PrefixMaxV(const std::vector<Interval>& intervals,
                               const std::vector<int>& indices,
                               double road_lower) {
  std::vector<double> prefix = {road_lower};
  prefix.reserve(indices.size() + 1);
  for (const int index : indices) {
    prefix.push_back(std::max(prefix.back(), intervals[index].v));
  }
  return prefix;
}

std::vector<int> Directions(const std::vector<int>& ordered, int split) {
  std::vector<int> directions(ordered.size());
  for (std::size_t i = 0; i < ordered.size(); ++i) {
    directions[ordered[i]] = static_cast<int>(i < static_cast<std::size_t>(split));
  }
  return directions;
}

GapResult SolveMaxGap(const Case& test_case) {
  const auto& intervals = test_case.intervals;
  const auto indices = OrderedIndices(intervals);
  const auto prefix = PrefixMaxV(intervals, indices, test_case.road_lower);
  const int count = static_cast<int>(indices.size());
  std::vector<double> gaps;
  gaps.reserve(count + 1);
  for (int split = 0; split <= count; ++split) {
    const double upper = split == count
                             ? test_case.road_upper
                             : std::min(test_case.road_upper, intervals[indices[split]].u);
    gaps.push_back(upper - prefix[split]);
  }
  const int split = static_cast<int>(
      std::distance(gaps.begin(), std::max_element(gaps.begin(), gaps.end())));
  const double upper = split == count
                           ? test_case.road_upper
                           : std::min(test_case.road_upper, intervals[indices[split]].u);
  return {indices, split, prefix[split], upper, gaps[split], gaps,
          std::vector<double>(prefix.begin() + 1, prefix.end()),
          Directions(indices, split)};
}

std::vector<Band> EnumerateLateralBands(const Case& test_case, int top_k) {
  const auto& intervals = test_case.intervals;
  const auto indices = OrderedIndices(intervals);
  const auto prefix = PrefixMaxV(intervals, indices, test_case.road_lower);
  const int count = static_cast<int>(indices.size());
  std::vector<Band> bands;
  bands.reserve(count + 1);
  for (int split = 0; split <= count; ++split) {
    const double lower = prefix[split];
    const double upper = split == count
                             ? test_case.road_upper
                             : std::min(test_case.road_upper, intervals[indices[split]].u);
    bands.push_back({split, lower, upper, upper - lower, Directions(indices, split)});
  }
  const double centre = 0.5 * (test_case.road_lower + test_case.road_upper);
  std::sort(bands.begin(), bands.end(), [&](const Band& a, const Band& b) {
    if (a.gap != b.gap) {
      return a.gap > b.gap;
    }
    const double da = std::abs(0.5 * (a.lower + a.upper) - centre);
    const double db = std::abs(0.5 * (b.lower + b.upper) - centre);
    if (da != db) {
      return da < db;
    }
    return a.split < b.split;
  });
  if (top_k > 0 && bands.size() > static_cast<std::size_t>(top_k)) {
    bands.resize(top_k);
  }
  return bands;
}

int IndexOf(const std::unordered_map<std::string, int>& headers,
            const std::string& key) {
  const auto it = headers.find(key);
  if (it == headers.end()) {
    throw std::runtime_error("missing CSV column: " + key);
  }
  return it->second;
}

bool NearlyEqual(double a, double b) {
  return std::abs(a - b) <= 1e-9 * std::max({1.0, std::abs(a), std::abs(b)});
}

double ResultChecksum(const GapResult& gap, const std::vector<Band>& bands) {
  double sum = gap.gap;
  for (const auto& band : bands) {
    sum += band.gap;
  }
  return sum;
}

std::vector<Case> ReadCases(const std::string& path) {
  std::ifstream input(path);
  if (!input) {
    throw std::runtime_error("cannot open input: " + path);
  }
  std::string line;
  if (!std::getline(input, line)) {
    throw std::runtime_error("empty input CSV");
  }
  const auto columns = ParseCsvLine(line);
  std::unordered_map<std::string, int> headers;
  for (std::size_t i = 0; i < columns.size(); ++i) {
    headers[columns[i]] = static_cast<int>(i);
  }
  const int kind_col = IndexOf(headers, "case_kind");
  const int seed_col = IndexOf(headers, "seed");
  const int group_col = IndexOf(headers, "group_index");
  const int road_lower_col = IndexOf(headers, "road_lower");
  const int road_upper_col = IndexOf(headers, "road_upper");
  const int count_col = IndexOf(headers, "n");
  const bool verify = headers.count("expected_split") != 0;

  std::vector<Case> cases;
  while (std::getline(input, line)) {
    if (line.empty()) {
      continue;
    }
    const auto fields = ParseCsvLine(line);
    if (fields.size() != columns.size()) {
      throw std::runtime_error("CSV row has wrong number of columns: " + line);
    }
    Case test_case;
    test_case.kind = fields[kind_col];
    test_case.seed = std::stoi(fields[seed_col]);
    test_case.group = std::stoi(fields[group_col]);
    test_case.road_lower = std::stod(fields[road_lower_col]);
    test_case.road_upper = std::stod(fields[road_upper_col]);
    const int count = std::stoi(fields[count_col]);
    if (count < 0 || test_case.road_lower > test_case.road_upper) {
      throw std::runtime_error("invalid interval count or road limits");
    }
    for (int i = 0; i < count; ++i) {
      const double u = std::stod(fields[IndexOf(headers, "obs" + std::to_string(i) + "_u")]);
      const double v = std::stod(fields[IndexOf(headers, "obs" + std::to_string(i) + "_v")]);
      if (!std::isfinite(u) || !std::isfinite(v) || u > v) {
        throw std::runtime_error("invalid forbidden interval");
      }
      test_case.intervals.push_back({u, v});
    }
    if (verify) {
      test_case.expected_split = std::stoi(fields[IndexOf(headers, "expected_split")]);
      test_case.expected_gap = std::stod(fields[IndexOf(headers, "expected_gap")]);
      test_case.expected_lower = std::stod(fields[IndexOf(headers, "expected_lower")]);
      test_case.expected_upper = std::stod(fields[IndexOf(headers, "expected_upper")]);
      const int band_count = std::stoi(fields[IndexOf(headers, "expected_band_count")]);
      if (band_count < 0 || band_count > 3) {
        throw std::runtime_error("invalid expected band count");
      }
      for (int i = 0; i < band_count; ++i) {
        const std::string prefix = "expected_band" + std::to_string(i) + "_";
        Band band;
        band.split = std::stoi(fields[IndexOf(headers, prefix + "split")]);
        band.gap = std::stod(fields[IndexOf(headers, prefix + "gap")]);
        band.lower = std::stod(fields[IndexOf(headers, prefix + "lower")]);
        band.upper = std::stod(fields[IndexOf(headers, prefix + "upper")]);
        test_case.expected_bands.push_back(std::move(band));
      }
    }
    cases.push_back(std::move(test_case));
  }
  return cases;
}

void WriteCsvValue(std::ostream& output, const std::string& value) {
  output << '"';
  for (const char ch : value) {
    if (ch == '"') {
      output << '"';
    }
    output << ch;
  }
  output << '"';
}

void Benchmark(const std::vector<Case>& cases, const std::string& output_path,
               int repeats, int top_k) {
  if (repeats <= 0 || top_k <= 0) {
    throw std::runtime_error("repeat count and top_k must be positive");
  }
  std::ofstream output(output_path);
  if (!output) {
    throw std::runtime_error("cannot open output: " + output_path);
  }
  output << "case_kind,seed,group_index,interval_count,repeats,runtime_ms,"
            "max_gap_split,max_gap_lower,max_gap_upper,max_gap_width,band_count";
  for (int i = 0; i < top_k; ++i) {
    output << ",band" << i << "_split,band" << i << "_lower,band" << i
           << "_upper,band" << i << "_width";
  }
  output << '\n' << std::setprecision(17);
  double total_ms = 0.0;
  std::size_t verified = 0;
  for (const auto& test_case : cases) {
    const auto gap = SolveMaxGap(test_case);
    const auto bands = EnumerateLateralBands(test_case, top_k);
    if (test_case.expected_split >= 0) {
      if (gap.split != test_case.expected_split ||
          !NearlyEqual(gap.gap, test_case.expected_gap) ||
          !NearlyEqual(gap.lower, test_case.expected_lower) ||
          !NearlyEqual(gap.upper, test_case.expected_upper) ||
          bands.size() != test_case.expected_bands.size()) {
        throw std::runtime_error("Python/C++ max-gap mismatch: " + test_case.kind +
                                 "/" + std::to_string(test_case.seed) + "/" +
                                 std::to_string(test_case.group));
      }
      for (std::size_t i = 0; i < bands.size(); ++i) {
        const auto& expected = test_case.expected_bands[i];
        if (bands[i].split != expected.split || !NearlyEqual(bands[i].gap, expected.gap) ||
            !NearlyEqual(bands[i].lower, expected.lower) ||
            !NearlyEqual(bands[i].upper, expected.upper)) {
          throw std::runtime_error("Python/C++ band mismatch: " + test_case.kind +
                                   "/" + std::to_string(test_case.seed) + "/" +
                                   std::to_string(test_case.group) + "/band" +
                                   std::to_string(i));
        }
      }
      ++verified;
    }
    for (int warmup = 0; warmup < 3; ++warmup) {
      checksum_sink += ResultChecksum(SolveMaxGap(test_case),
                                     EnumerateLateralBands(test_case, top_k));
    }
    const auto started = std::chrono::steady_clock::now();
    for (int repeat = 0; repeat < repeats; ++repeat) {
      const auto gap = SolveMaxGap(test_case);
      const auto bands = EnumerateLateralBands(test_case, top_k);
      checksum_sink += ResultChecksum(gap, bands);
    }
    const auto finished = std::chrono::steady_clock::now();
    const double runtime_ms =
        std::chrono::duration<double, std::milli>(finished - started).count() / repeats;
    total_ms += runtime_ms;
    WriteCsvValue(output, test_case.kind);
    output << ',' << test_case.seed << ',' << test_case.group << ','
           << test_case.intervals.size() << ',' << repeats << ',' << runtime_ms << ','
           << gap.split << ',' << gap.lower << ',' << gap.upper << ',' << gap.gap
           << ',' << bands.size();
    for (int i = 0; i < top_k; ++i) {
      if (i < static_cast<int>(bands.size())) {
        output << ',' << bands[i].split << ',' << bands[i].lower << ','
               << bands[i].upper << ',' << bands[i].gap;
      } else {
        output << ",,,,";
      }
    }
    output << '\n';
  }
  std::cerr << "Measured " << cases.size() << " geometry groups ("
            << repeats << " repeats/group, top_k=" << top_k
            << "); verified " << verified << " groups; mean per-call time "
            << (cases.empty() ? 0 : total_ms / cases.size())
            << " ms; checksum=" << checksum_sink << '\n';
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 4 && argc != 5) {
      std::cerr << "usage: " << argv[0]
                << " projected_cases.csv raw_cpp.csv repeats [top_k=3]\n";
      return 2;
    }
    const auto cases = ReadCases(argv[1]);
    Benchmark(cases, argv[2], std::stoi(argv[3]), argc == 5 ? std::stoi(argv[4]) : 3);
  } catch (const std::exception& error) {
    std::cerr << "benchmark error: " << error.what() << '\n';
    return 1;
  }
}

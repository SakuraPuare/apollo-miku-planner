#include "miku_case_csv.h"

#include <fstream>
#include <map>
#include <stdexcept>
#include <utility>

namespace miku_cpp_path {
namespace {

std::vector<std::string> ParseCsvLine(const std::string& line) {
  std::vector<std::string> cells;
  std::string cell;
  bool quoted = false;
  for (std::size_t i = 0; i < line.size(); ++i) {
    const char ch = line[i];
    if (ch == '"') {
      if (quoted && i + 1 < line.size() && line[i + 1] == '"') {
        cell += ch;
        ++i;
      } else {
        quoted = !quoted;
      }
    } else if (ch == ',' && !quoted) {
      cells.push_back(std::move(cell));
      cell.clear();
    } else {
      cell += ch;
    }
  }
  if (quoted) throw std::runtime_error("unterminated CSV field");
  if (!cell.empty() && cell.back() == '\r') cell.pop_back();
  cells.push_back(std::move(cell));
  return cells;
}

}  // namespace

std::vector<InputCase> ReadCaseCsv(const std::string& filename) {
  std::ifstream input(filename);
  if (!input) throw std::runtime_error("cannot open input: " + filename);
  std::string line;
  if (!std::getline(input, line)) throw std::runtime_error("empty input CSV");
  const auto columns = ParseCsvLine(line);
  std::map<std::string, std::size_t> header;
  for (std::size_t i = 0; i < columns.size(); ++i) header.emplace(columns[i], i);
  std::vector<InputCase> cases;
  while (std::getline(input, line)) {
    if (line.empty()) continue;
    const auto cells = ParseCsvLine(line);
    const auto field = [&](const std::string& name) -> const std::string& {
      auto it = header.find(name);
      if (it == header.end() || it->second >= cells.size()) {
        throw std::runtime_error("missing CSV field: " + name);
      }
      return cells[it->second];
    };
    const auto number = [&](const std::string& name) { return std::stod(field(name)); };
    if (field("schema_version") != "miku-cpp-input-v1") {
      throw std::runtime_error("unsupported case CSV schema");
    }
    InputCase item;
    item.kind = field("case_kind");
    item.seed = std::stoi(field("seed"));
    auto& scenario = item.scenario;
    scenario.ego = {number("ego_s0"), number("ego_l0"), number("ego_v0"),
                    number("ego_a0"), number("ego_W"), number("ego_L")};
    scenario.s_max = number("s_max");
    scenario.t_max = number("t_max");
    scenario.l_road_min = number("l_road_min");
    scenario.l_road_max = number("l_road_max");
    scenario.delta_min = number("delta_min");
    scenario.delta_max = number("delta_max");
    scenario.lane_borrow = field("lane_borrow");
    scenario.lane_width = number("lane_width");
    const int obstacle_count = std::stoi(field("obstacle_count"));
    if (obstacle_count < 0) throw std::runtime_error("negative obstacle_count");
    for (int i = 0; i < obstacle_count; ++i) {
      const auto key = [i](const std::string& name) {
        return "obs" + std::to_string(i) + "_" + name;
      };
      scenario.obstacles.push_back({number(key("s0")), number(key("l0")),
                                    number(key("vs")), number(key("vl")),
                                    number(key("W")), number(key("L")),
                                    field(key("is_static")) == "1",
                                    field(key("obs_type")),
                                    "obs" + std::to_string(i),
                                    number(key("uncertainty_s0")),
                                    number(key("uncertainty_l0")),
                                    number(key("uncertainty_vs")),
                                    number(key("uncertainty_vl"))});
    }
    cases.push_back(std::move(item));
  }
  return cases;
}

}  // namespace miku_cpp_path

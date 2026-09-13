#ifndef MIKU_CPP_PATH_STAGE_MIKU_CASE_CSV_H_
#define MIKU_CPP_PATH_STAGE_MIKU_CASE_CSV_H_

#include "miku_path_bounds.h"

#include <string>
#include <vector>

namespace miku_cpp_path {

struct InputCase {
  std::string kind;
  int seed = 0;
  Scenario scenario;
};

// Loads tools/export_miku_cases.py schema miku-cpp-input-v1.
std::vector<InputCase> ReadCaseCsv(const std::string& filename);

}  // namespace miku_cpp_path

#endif  // MIKU_CPP_PATH_STAGE_MIKU_CASE_CSV_H_

#pragma once

#include <vector>

namespace miku_path_qp {

struct PathResult {
  std::vector<double> lateral;
  bool solved = false;
  int iterations = 0;
  double solver_ms = 0.0;
};

// Port of the frozen supplement's apollo_pipeline.path_optimizer function.
// This is the path QP only, not the complete planner or an Apollo cycle.
PathResult OptimizePath(const std::vector<double>& s_arr,
                        const std::vector<double>& l_min,
                        const std::vector<double>& l_max);

}  // namespace miku_path_qp

#include "tools/cpp_path_qp/miku_path_qp.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

#include <osqp/osqp.h>

namespace miku_path_qp {
namespace {

constexpr double kLateralWeight = 0.5;
constexpr double kSlopeWeight = 100.0;
constexpr double kCurvatureWeight = 800.0;

}  // namespace

PathResult OptimizePath(const std::vector<double>& s_arr,
                        const std::vector<double>& l_min,
                        const std::vector<double>& l_max) {
  const auto n = static_cast<OSQPInt>(s_arr.size());
  if (n < 2 || l_min.size() != s_arr.size() || l_max.size() != s_arr.size()) {
    throw std::invalid_argument("path grid and lateral bounds need equal length >= 2");
  }
  const double ds = s_arr[1] - s_arr[0];
  if (!std::isfinite(ds) || ds <= 0.0) {
    throw std::invalid_argument("path station step must be positive and finite");
  }
  for (OSQPInt j = 0; j < n; ++j) {
    if (!std::isfinite(l_min[j]) || !std::isfinite(l_max[j]) ||
        l_min[j] > l_max[j]) {
      throw std::invalid_argument("path lateral bounds must be finite and ordered");
    }
  }

  // Preserve the frozen Python assembly order before converting the symmetric
  // Hessian to CSC upper triangular form expected by OSQP.
  std::vector<double> dense(static_cast<std::size_t>(n) * n, 0.0);
  const auto at = [&](OSQPInt row, OSQPInt column) -> double& {
    return dense[static_cast<std::size_t>(row) * n + column];
  };
  for (OSQPInt j = 0; j < n; ++j) {
    at(j, j) += 2.0 * kLateralWeight;
  }
  for (OSQPInt j = 0; j < n - 1; ++j) {
    const double c = 2.0 * kSlopeWeight / std::pow(ds, 2);
    at(j, j) += c;
    at(j + 1, j + 1) += c;
    at(j, j + 1) -= c;
    at(j + 1, j) -= c;
  }
  for (OSQPInt j = 0; j < n - 2; ++j) {
    const double c = 2.0 * kCurvatureWeight / std::pow(ds, 4);
    constexpr int coefficient[] = {1, -2, 1};
    for (OSQPInt a = 0; a < 3; ++a) {
      for (OSQPInt b = 0; b < 3; ++b) {
        at(j + a, j + b) += c * coefficient[a] * coefficient[b];
      }
    }
  }

  std::vector<OSQPInt> p_col(static_cast<std::size_t>(n) + 1, 0);
  std::vector<OSQPInt> p_row;
  std::vector<OSQPFloat> p_value;
  for (OSQPInt column = 0; column < n; ++column) {
    p_col[column] = static_cast<OSQPInt>(p_value.size());
    for (OSQPInt row = 0; row <= column; ++row) {
      const double value = at(row, column);
      if (value != 0.0) {
        p_row.push_back(row);
        p_value.push_back(value);
      }
    }
  }
  p_col[n] = static_cast<OSQPInt>(p_value.size());
  std::vector<OSQPInt> a_col(static_cast<std::size_t>(n) + 1);
  std::vector<OSQPInt> a_row(n);
  std::vector<OSQPFloat> a_value(n, 1.0);
  std::vector<OSQPFloat> q(n, 0.0);
  for (OSQPInt j = 0; j < n; ++j) {
    a_col[j] = j;
    a_row[j] = j;
  }
  a_col[n] = n;

  OSQPCscMatrix* p = OSQPCscMatrix_new(
      n, n, static_cast<OSQPInt>(p_value.size()), p_value.data(), p_row.data(),
      p_col.data());
  OSQPCscMatrix* a = OSQPCscMatrix_new(
      n, n, n, a_value.data(), a_row.data(), a_col.data());
  if (!p || !a) {
    OSQPCscMatrix_free(p);
    OSQPCscMatrix_free(a);
    throw std::runtime_error("OSQP CSC allocation failed");
  }

  OSQPSettings settings;
  osqp_set_default_settings(&settings);
  settings.verbose = 0;
  settings.polishing = 1;
  settings.max_iter = 40000;
  settings.eps_abs = 1e-6;
  settings.eps_rel = 1e-6;

  OSQPSolver* solver = nullptr;
  const OSQPInt setup_status = osqp_setup(
      &solver, p, q.data(), a, l_min.data(), l_max.data(), n, n, &settings);
  if (setup_status != OSQP_NO_ERROR) {
    OSQPCscMatrix_free(p);
    OSQPCscMatrix_free(a);
    throw std::runtime_error("OSQP path setup failed: " +
                             std::string(osqp_error_message(setup_status)));
  }

  const auto start = std::chrono::steady_clock::now();
  const OSQPInt solve_status = osqp_solve(solver);
  const auto finish = std::chrono::steady_clock::now();

  PathResult result;
  result.solver_ms =
      std::chrono::duration<double, std::milli>(finish - start).count();
  result.solved = solve_status == OSQP_NO_ERROR &&
                  solver->info->status_val == OSQP_SOLVED;
  result.iterations = solver->info->iter;
  result.lateral.resize(static_cast<std::size_t>(n));
  for (OSQPInt j = 0; j < n; ++j) {
    result.lateral[j] = result.solved
                            ? solver->solution->x[j]
                            : std::clamp(0.0, l_min[j], l_max[j]);
  }
  osqp_cleanup(solver);
  OSQPCscMatrix_free(p);
  OSQPCscMatrix_free(a);
  return result;
}

}  // namespace miku_path_qp

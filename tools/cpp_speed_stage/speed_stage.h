#pragma once

#include <functional>
#include <map>
#include <string>
#include <utility>
#include <vector>

namespace miku_speed {

struct Ego {
  double s0 = 0.0, l0 = 0.0, v0 = 8.0, a0 = 0.0;
  double W = 2.11, L = 4.0;
};

struct Obstacle {
  double s0 = 0.0, l0 = 0.0, vs = 0.0, vl = 0.0;
  double W = 0.5, L = 0.5;
  bool is_static = false;
  std::string name;
  double uncertainty_s0 = 0.0, uncertainty_l0 = 0.0;
  double uncertainty_vs = 0.0, uncertainty_vl = 0.0;
};

struct Scenario {
  Ego ego;
  std::vector<Obstacle> obstacles;
  double s_max = 25.0, t_max = 3.5;
};

struct STInterval {
  double t, s_lo, s_hi;
};

struct STBoundary {
  std::string name;
  std::vector<STInterval> intervals;
  bool is_static = false;
  double vs = 0.0, vl = 0.0;
};

struct DPResult {
  std::vector<double> ts, s_dp, ss;
  std::vector<std::vector<bool>> forbidden;
};

struct TimeWindow {
  double start, end;
};

struct Decision {
  std::string name, status, homotopy_label;
  TimeWindow window{0.0, 0.0};
  double target_arrival = 0.0, homotopy_cost = 0.0;
  int window_index = -1, candidate_count = 0;
  int graph_candidate_count = 0, temporal_plan_rank = 0;
};

struct STBounds {
  std::vector<double> upper, lower;
  std::vector<Decision> decisions;
};

struct BoundsOptions {
  bool safe_window_mode = false;
  std::vector<std::pair<double, double>> corridor;
  std::function<double(double)> tau_fn;
  std::map<std::string, std::string> preferred_homotopy;
  int temporal_plan_rank = 0;
};

struct QPResult {
  bool solved = false;
  std::string status;
  std::vector<double> s, v, a;
  // Like Python speed_qp: time spent only in osqp_solve, excluding setup.
  double solve_ms = 0.0;
};

std::vector<STBoundary> st_boundary_mapper(const Scenario& scn,
    const std::vector<double>& path_stations,
    const std::vector<double>& path_offsets, bool robust_prediction = false);

DPResult speed_dp(const Scenario& scn, const std::vector<STBoundary>& boundaries);

STBounds build_st_bounds(const Scenario& scn,
    const std::vector<STBoundary>& boundaries, const DPResult& dp,
    const BoundsOptions& options = {});

QPResult speed_qp(const Scenario& scn, const std::vector<double>& upper,
    const std::vector<double>& lower, const std::vector<double>& ts);

}  // namespace miku_speed

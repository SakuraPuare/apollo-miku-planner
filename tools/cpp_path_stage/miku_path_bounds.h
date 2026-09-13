#ifndef MIKU_CPP_PATH_STAGE_MIKU_PATH_BOUNDS_H_
#define MIKU_CPP_PATH_STAGE_MIKU_PATH_BOUNDS_H_

#include <cstddef>
#include <functional>
#include <string>
#include <vector>

namespace miku_cpp_path {

struct Ego {
  double s0 = 0.0;
  double l0 = 0.0;
  double v0 = 8.0;
  double a0 = 0.0;
  double width = 2.11;
  double length = 4.0;
};

struct Obstacle {
  double s0 = 0.0;
  double l0 = 0.0;
  double vs = 0.0;
  double vl = 0.0;
  double width = 0.5;
  double length = 0.5;
  bool is_static = false;
  std::string type = "vehicle";
  std::string name;
  double uncertainty_s0 = 0.0;
  double uncertainty_l0 = 0.0;
  double uncertainty_vs = 0.0;
  double uncertainty_vl = 0.0;
};

struct Scenario {
  Ego ego;
  std::vector<Obstacle> obstacles;
  double s_max = 25.0;
  double t_max = 3.5;
  double l_road_min = -1.875;
  double l_road_max = 1.875;
  double delta_min = 0.1;
  double delta_max = 0.4;
  std::string lane_borrow = "none";
  double lane_width = 3.75;
};

struct GroupDecision {
  int split_index = -1;  // -1 means no path-active obstacles in this group.
  double gap = 0.0;
  std::size_t active_obstacle_count = 0;
};

struct PathResult {
  std::vector<double> stations;
  std::vector<double> lower;
  std::vector<double> upper;
  int blocked_index = -1;
  std::vector<GroupDecision> groups;
  std::size_t spatial_candidate_count = 0;
};

double ComputeThreat(std::size_t obstacle_index, const Scenario& scenario);
double ComputeDelta(std::size_t obstacle_index, const Scenario& scenario);
double ArrivalTime(double station, const Scenario& scenario);

// Reproduces frozen supplement path_bounds_decider(scn, "miku") only.
// Supplying tau_fn also supports its iterative arrival-time replanning call.
PathResult PathBounds(const Scenario& scenario, int candidate_rank = 0,
                      const std::function<double(double)>& tau_fn = {});

}  // namespace miku_cpp_path

#endif  // MIKU_CPP_PATH_STAGE_MIKU_PATH_BOUNDS_H_

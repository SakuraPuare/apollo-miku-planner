#include "speed_stage.h"

#include <cassert>
#include <cmath>
#include <iostream>
#include <vector>

using namespace miku_speed;

int main() {
  Scenario scn;
  scn.s_max = 25.0;
  scn.t_max = 3.5;
  std::vector<double> stations(51), offsets(51, 0.0);
  for (size_t j = 0; j < stations.size(); ++j) stations[j] = 0.5 * j;
  Obstacle crossing;
  crossing.name = "crossing";
  crossing.s0 = 12.0;
  crossing.l0 = 0.0;
  crossing.vl = 2.0;
  crossing.uncertainty_l0 = 0.1;
  scn.obstacles.push_back(crossing);
  const auto mapped = st_boundary_mapper(scn, stations, offsets, true);
  assert(mapped.size() == 1 && mapped[0].intervals.size() == 15);
  assert(std::abs(mapped[0].intervals.front().s_lo - 9.6) < 1e-9);
  assert(std::abs(mapped[0].intervals.back().t - 0.7) < 1e-9);
  assert(std::abs(mapped[0].intervals.back().s_hi - 14.4) < 1e-9);
  const auto dp = speed_dp(scn, mapped);
  assert(dp.ts.size() == 36 && dp.s_dp.size() == 36);
  // Python's dt=0.1, ds=0.5 grid cannot accelerate from v0=8 within its
  // first-step limits; preserve this behavior rather than masking it.
  for (const double s : dp.s_dp) assert(s == 0.0);
  BoundsOptions opts;
  opts.safe_window_mode = true;
  auto bounds = build_st_bounds(scn, mapped, dp, opts);
  assert(bounds.upper.size() == dp.ts.size());
  assert(bounds.decisions.size() == 1);
  assert(bounds.decisions.front().status == "selected");
  assert(bounds.decisions.front().homotopy_label == "yield_after");
  assert(std::abs(bounds.decisions.front().window.start - 0.9) < 1e-9);
  assert(std::abs(bounds.decisions.front().target_arrival -
                  1.5136195008360884) < 1e-8);
  assert(std::abs(bounds.upper[9] - 9.55) < 1e-9);
  assert(bounds.upper[10] == 1e4);
  for (auto& upper : bounds.upper) upper = std::min(upper, scn.s_max - 1);
  bounds.lower.back() = std::min(scn.s_max - 1, bounds.upper.back());
  auto solved = speed_qp(scn, bounds.upper, bounds.lower, dp.ts);
  assert(solved.solved && solved.s.size() == dp.ts.size());
  assert(std::abs(solved.s.front() - scn.ego.s0) < 1e-4);
  assert(std::abs(solved.v.front() - scn.ego.v0) < 1e-4);
  assert(std::abs(solved.s.back() - 24.000001) < 1e-4);
  assert(std::abs(solved.v.back() - 5.15208122929052) < 1e-3);
  assert(std::abs(solved.s[9] - 7.107835369) < 1e-3);
  assert(std::abs(solved.a[20] - -1.013767013) < 1e-3);
  auto impossible_lower = bounds.lower;
  impossible_lower.front() = 2.0;
  assert(!speed_qp(scn, bounds.upper, impossible_lower, dp.ts).solved);

  STBoundary persistent{"persistent", {}, false, 0.0, 2.0};
  for (int k = 0; k <= 70; ++k)
    persistent.intervals.push_back({k * 0.05, 9.6, 14.4});
  const auto stopped = build_st_bounds(scn, {persistent}, dp, opts);
  assert(stopped.decisions.size() == 1);
  assert(stopped.decisions.front().status == "stop");
  for (auto upper : stopped.upper) assert(std::abs(upper - 9.6) < 1e-9);
  Scenario unobstructed = scn;
  unobstructed.ego.v0 = 5.0;
  unobstructed.obstacles.clear();
  const auto free_dp = speed_dp(unobstructed, {});
  for (size_t j = 0; j < free_dp.s_dp.size(); ++j)
    assert(std::abs(free_dp.s_dp[j] - 0.5 * j) < 1e-9);
  std::cout << "ST=" << mapped[0].intervals.size()
            << " choice=" << bounds.decisions.front().homotopy_label
            << " speed_qp_status=" << solved.status << '\n';
}

/******************************************************************************
 * Copyright 2024 The Apollo Authors. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *****************************************************************************/

#include "modules/planning/tasks/speed_bounds_decider/st_corridor_generator.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <string>

#include "cyber/common/log.h"

namespace apollo {
namespace planning {

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

std::vector<STCorridorPoint> STCorridorGenerator::Generate(
    const std::vector<const STBoundary*>& boundaries,
    const std::vector<ThreatInfo>& threat_info,
    const common::TrajectoryPoint& init_point,
    double total_time,
    double total_length,
    double dt) const {
  std::vector<STCorridorPoint> corridor;

  if (total_time <= 0.0 || dt <= 0.0 || total_length <= 0.0) {
    AERROR << "[STCorridorGenerator] Invalid parameters: total_time="
           << total_time << " dt=" << dt << " total_length=" << total_length;
    return corridor;
  }

  const int num_steps = static_cast<int>(std::ceil(total_time / dt)) + 1;
  corridor.reserve(num_steps);

  // Initial corridor slice: ego is at s=0 with initial velocity.
  double prev_lo = 0.0;
  double prev_hi = 0.0;
  double prev_v_lo = std::max(0.0, init_point.v());
  double prev_v_hi = std::max(0.0, init_point.v());

  // t=0 slice
  {
    STCorridorPoint pt;
    pt.t = 0.0;
    pt.s_lower = 0.0;
    pt.s_upper = 0.0;
    corridor.push_back(pt);
  }

  for (int k = 1; k < num_steps; ++k) {
    const double t = std::min(k * dt, total_time);

    // 1. Compute kinematic reachable set from previous corridor slice.
    auto [reach_lo, reach_hi] =
        KinematicReach(prev_lo, prev_hi, prev_v_lo, prev_v_hi, dt,
                       total_length);

    // 2. Clip with active boundaries → free intervals.
    auto free_intervals =
        GetFreeIntervals(t, reach_lo, reach_hi, boundaries, threat_info);

    // 3. Select best interval.
    std::pair<double, double> chosen;
    if (free_intervals.empty()) {
      // No free space — keep a narrow corridor just above the previous lower.
      AWARN << "[STCorridorGenerator] No free interval at t=" << t
            << "; using fallback.";
      chosen = {prev_lo, std::max(prev_lo, prev_hi)};
    } else {
      chosen = SelectBestInterval(free_intervals, prev_lo, prev_hi,
                                   init_point.v(), dt);
    }

    STCorridorPoint pt;
    pt.t       = t;
    pt.s_lower = chosen.first;
    pt.s_upper = chosen.second;
    corridor.push_back(pt);

    // Update velocity bounds for next iteration (rough estimate from ds/dt).
    prev_v_lo = std::max(0.0, (chosen.first  - prev_lo) / dt);
    prev_v_hi = std::min(kMaxSpeed, (chosen.second - prev_lo) / dt);
    prev_lo = chosen.first;
    prev_hi = chosen.second;

    ADEBUG << "[STCorridorGenerator] t=" << t
           << " s_lower=" << pt.s_lower
           << " s_upper=" << pt.s_upper;
  }

  return corridor;
}

// ---------------------------------------------------------------------------
// Private helpers
// ---------------------------------------------------------------------------

std::pair<double, double> STCorridorGenerator::KinematicReach(
    double prev_lo, double prev_hi,
    double prev_v_lo, double prev_v_hi,
    double dt, double s_max) const {
  // Lower bound: max deceleration from lower s
  //   s_lo_new = prev_lo + prev_v_lo * dt + 0.5 * kMaxDec * dt^2
  const double s_lo = std::max(
      0.0,
      prev_lo + prev_v_lo * dt + 0.5 * kMaxDec * dt * dt);

  // Upper bound: max acceleration from upper s
  //   s_hi_new = prev_hi + prev_v_hi * dt + 0.5 * kMaxAcc * dt^2
  const double s_hi = std::min(
      s_max,
      prev_hi + prev_v_hi * dt + 0.5 * kMaxAcc * dt * dt);

  return {s_lo, std::max(s_lo, s_hi)};
}

std::vector<std::pair<double, double>> STCorridorGenerator::GetFreeIntervals(
    double t,
    double s_lo, double s_hi,
    const std::vector<const STBoundary*>& boundaries,
    const std::vector<ThreatInfo>& threat_info) const {
  // Build a list of blocked [lo, hi] intervals at time t from each boundary.
  std::vector<std::pair<double, double>> blocked;

  for (size_t i = 0; i < boundaries.size(); ++i) {
    const auto* b = boundaries[i];
    if (!b || b->IsEmpty()) continue;

    double b_upper = 0.0;
    double b_lower = 0.0;
    if (!b->GetBoundarySRange(t, &b_upper, &b_lower)) {
      continue;  // boundary not active at this t
    }

    // Apply safety distance from threat info if available.
    double d_safe = 0.3;  // default MINOR
    if (i < threat_info.size()) {
      d_safe = threat_info[i].d_safe;
    }
    b_lower = std::max(0.0, b_lower - d_safe);
    b_upper = b_upper + d_safe;

    // Only record if it overlaps [s_lo, s_hi]
    if (b_upper > s_lo && b_lower < s_hi) {
      blocked.emplace_back(b_lower, b_upper);
    }
  }

  if (blocked.empty()) {
    // Entire reachable range is free.
    return {{s_lo, s_hi}};
  }

  // Sort blocked intervals by lower bound.
  std::sort(blocked.begin(), blocked.end());

  // Compute free intervals as complement of union(blocked) within [s_lo, s_hi].
  std::vector<std::pair<double, double>> free_intervals;
  double cursor = s_lo;

  for (const auto& [blo, bhi] : blocked) {
    if (blo > cursor) {
      // Gap before this blocked interval.
      free_intervals.emplace_back(cursor, std::min(blo, s_hi));
    }
    cursor = std::max(cursor, bhi);
    if (cursor >= s_hi) break;
  }

  // Trailing free interval.
  if (cursor < s_hi) {
    free_intervals.emplace_back(cursor, s_hi);
  }

  return free_intervals;
}

std::pair<double, double> STCorridorGenerator::SelectBestInterval(
    const std::vector<std::pair<double, double>>& intervals,
    double prev_lo, double prev_hi,
    double cruise_speed, double dt) const {
  const double prev_center = 0.5 * (prev_lo + prev_hi);
  const double cruise_ds = cruise_speed * dt;

  double best_score = -1.0;
  std::pair<double, double> best = intervals.front();

  for (const auto& [lo, hi] : intervals) {
    const double width = hi - lo;
    if (width < 0.0) continue;

    // Width score: normalised by reference width.
    const double score_width = std::min(1.0, width / kRefWidth);

    // Continuity score: how well does this interval align with the previous?
    const double center = 0.5 * (lo + hi);
    const double dist_to_prev = std::fabs(center - prev_center);
    const double score_cont =
        std::max(0.0, 1.0 - dist_to_prev / kRefWidth);

    // Speed feasibility: is cruise_ds reachable within this interval?
    const double target_s = prev_lo + cruise_ds;
    const double score_speed =
        (target_s >= lo && target_s <= hi) ? 1.0
            : std::max(0.0, 1.0 - std::fabs(target_s - center) / kRefWidth);

    const double score =
        kWa * score_width + kWb * score_cont + kWc * score_speed;

    if (score > best_score) {
      best_score = score;
      best = {lo, hi};
    }
  }

  return best;
}

}  // namespace planning
}  // namespace apollo

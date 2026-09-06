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

#include "modules/planning/tasks/speed_bounds_decider/threat_assessor.h"

#include <algorithm>
#include <cmath>
#include <string>
#include <unordered_map>

#include "cyber/common/log.h"
#include "modules/common_msgs/perception_msgs/perception_obstacle.pb.h"

namespace apollo {
namespace planning {

namespace {

// Find obstacle by id in the obstacle list.
const Obstacle* FindObstacle(
    const std::vector<const Obstacle*>& obstacles,
    const std::string& id) {
  for (const auto* obs : obstacles) {
    if (obs && obs->Id() == id) {
      return obs;
    }
  }
  return nullptr;
}

// Linear saturation: map x ∈ [lo, hi] → [0, 1], clamp outside.
double Saturate(double x, double lo, double hi) {
  if (hi <= lo) return 0.0;
  return std::max(0.0, std::min(1.0, (x - lo) / (hi - lo)));
}

}  // namespace

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

std::vector<ThreatInfo> ThreatAssessor::Assess(
    const std::vector<const STBoundary*>& boundaries,
    const std::vector<const Obstacle*>& obstacles,
    const common::TrajectoryPoint& ego_state) const {
  std::vector<ThreatInfo> results;
  results.reserve(boundaries.size());

  for (const auto* boundary : boundaries) {
    if (!boundary || boundary->IsEmpty()) {
      continue;
    }

    const std::string& obs_id = boundary->id();
    const Obstacle* obs = FindObstacle(obstacles, obs_id);

    // --- compute individual factors ---
    const double f_ttc        = ComputeTTC(*boundary, ego_state);
    const double f_overlap    = ComputeOverlapRate(*boundary,
                                                    ego_state.path_point().x());
    const double f_vel        = obs ? ComputeRelativeVel(*obs, ego_state) : 0.5;
    const double f_type       = obs ? ComputeTypeFactor(*obs) : 0.5;
    const double f_interaction = ComputeInteractionFactor(*boundary, boundaries);

    const double score = kW1 * f_ttc + kW2 * f_overlap + kW3 * f_vel +
                         kW4 * f_type + kW5 * f_interaction;

    ThreatInfo info;
    info.obstacle_id = obs_id;
    info.score = std::max(0.0, std::min(1.0, score));

    if (info.score >= kCriticalThreshold) {
      info.level  = 2;  // CRITICAL
      info.dt     = kCriticalDt;
      info.d_safe = kCriticalDSafe;
    } else if (info.score >= kImportantThreshold) {
      info.level  = 1;  // IMPORTANT
      info.dt     = kImportantDt;
      info.d_safe = kImportantDSafe;
    } else {
      info.level  = 0;  // MINOR
      info.dt     = kMinorDt;
      info.d_safe = kMinorDSafe;
    }

    ADEBUG << "[ThreatAssessor] id=" << obs_id
           << " score=" << info.score
           << " level=" << info.level
           << " f_ttc=" << f_ttc
           << " f_overlap=" << f_overlap
           << " f_vel=" << f_vel
           << " f_type=" << f_type
           << " f_interaction=" << f_interaction;

    results.push_back(info);
  }

  return results;
}

// ---------------------------------------------------------------------------
// Private helpers
// ---------------------------------------------------------------------------

double ThreatAssessor::ComputeTTC(
    const STBoundary& b, const common::TrajectoryPoint& ego) const {
  // Estimate TTC as the earliest time the boundary lower edge reaches ego's
  // current s position.
  const double ego_s = 0.0;  // ego is always at s=0 in the ST frame
  const double ego_v = ego.v();

  // Find the minimum t where lower_s <= ego_s + ego_v * t
  // Approximation: use the boundary's min_t and min_s.
  const double min_s = b.min_s();
  const double min_t = b.min_t();

  double ttc = kMaxTTC;
  if (ego_v > 0.1) {
    // Time for ego to reach the lower boundary leading edge
    const double s_to_boundary = min_s - ego_s;
    if (s_to_boundary > 0.0) {
      ttc = s_to_boundary / ego_v;
    } else {
      // ego is already past min_s → imminent
      ttc = min_t;
    }
  } else {
    // Static ego: check if boundary is very close in s
    ttc = (min_s < 5.0) ? kMinTTC : kMaxTTC;
  }

  ttc = std::max(0.0, ttc);
  // Inverse mapping: low TTC → high threat
  return 1.0 - Saturate(ttc, kMinTTC, kMaxTTC);
}

double ThreatAssessor::ComputeOverlapRate(
    const STBoundary& b, double /*ego_width*/) const {
  // Measure blocked s-range at the boundary's earliest time slice.
  const double t_start = b.min_t();
  double s_upper = 0.0;
  double s_lower = 0.0;
  if (!b.GetBoundarySRange(t_start, &s_upper, &s_lower)) {
    return 0.0;
  }
  const double blocked_s = std::max(0.0, s_upper - s_lower);
  return Saturate(blocked_s, 0.0, kRefSRange);
}

double ThreatAssessor::ComputeRelativeVel(
    const Obstacle& obs, const common::TrajectoryPoint& ego) const {
  // Positive closing speed → obstacle approaching ego.
  const double obs_speed = obs.speed();
  const double ego_speed = ego.v();
  // Closing speed (ego moves forward, obstacle may move toward or away)
  const double closing = ego_speed - obs_speed;
  // Threat increases when closing speed is high
  return Saturate(closing, 0.0, kRefClosingSpeed);
}

double ThreatAssessor::ComputeTypeFactor(const Obstacle& obs) const {
  using Type = apollo::perception::PerceptionObstacle;
  switch (obs.Perception().type()) {
    case Type::PEDESTRIAN:
      return 1.0;
    case Type::BICYCLE:
      return 0.8;
    case Type::VEHICLE:
      return 0.6;
    case Type::UNKNOWN_MOVABLE:
      return 0.5;
    case Type::UNKNOWN_UNMOVABLE:
    case Type::UNKNOWN:
    default:
      return 0.3;
  }
}

double ThreatAssessor::ComputeInteractionFactor(
    const STBoundary& b,
    const std::vector<const STBoundary*>& all_boundaries) const {
  // Count how many OTHER boundaries temporally overlap with b.
  int overlap_count = 0;
  const double t_lo = b.min_t();
  const double t_hi = b.max_t();

  for (const auto* other : all_boundaries) {
    if (!other || other == &b || other->IsEmpty()) {
      continue;
    }
    // Check temporal overlap
    if (other->min_t() < t_hi && other->max_t() > t_lo) {
      ++overlap_count;
    }
  }

  // Saturate: 0 overlaps → 0.0; 3+ overlaps → 1.0
  return Saturate(static_cast<double>(overlap_count), 0.0, 3.0);
}

}  // namespace planning
}  // namespace apollo

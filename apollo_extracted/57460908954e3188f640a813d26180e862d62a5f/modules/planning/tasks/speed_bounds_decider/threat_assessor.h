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

/**
 * @file threat_assessor.h
 * @brief Multi-factor threat assessment for ST-graph obstacles.
 *
 * Computes a composite threat score Θ ∈ [0,1] for each obstacle using:
 *   Θ = w1·f_TTC + w2·f_overlap + w3·f_vel + w4·f_type + w5·f_interaction
 * and assigns each obstacle to a threat level (MINOR / IMPORTANT / CRITICAL).
 */

#pragma once

#include <string>
#include <vector>

#include "modules/common_msgs/basic_msgs/pnc_point.pb.h"
#include "modules/planning/planning_base/common/obstacle.h"
#include "modules/planning/planning_base/common/speed/st_boundary.h"

namespace apollo {
namespace planning {

/**
 * @struct ThreatInfo
 * @brief Per-obstacle threat assessment result.
 */
struct ThreatInfo {
  std::string obstacle_id;
  double score;    ///< Composite threat score in [0, 1].
  int level;       ///< 0=MINOR, 1=IMPORTANT, 2=CRITICAL
  double d_safe;   ///< Dynamic safety distance (m).
  double dt;       ///< Recommended ST-scan time step (s) for this obstacle.
};

/**
 * @class ThreatAssessor
 * @brief Evaluates multi-factor threat scores for a set of ST boundaries.
 */
class ThreatAssessor {
 public:
  ThreatAssessor() = default;

  /**
   * @brief Assess threat levels for all non-empty ST boundaries.
   *
   * @param boundaries   Pointers to non-empty STBoundary objects.
   * @param obstacles    Matching Obstacle pointers (same order / by id lookup).
   * @param ego_state    Current ego vehicle trajectory point.
   * @return             One ThreatInfo entry per boundary.
   */
  std::vector<ThreatInfo> Assess(
      const std::vector<const STBoundary*>& boundaries,
      const std::vector<const Obstacle*>& obstacles,
      const common::TrajectoryPoint& ego_state) const;

 private:
  // --- factor computations ---

  /**
   * @brief Time-to-collision factor f_TTC ∈ [0,1].
   * Lower TTC → higher threat.
   */
  double ComputeTTC(const STBoundary& b,
                    const common::TrajectoryPoint& ego) const;

  /**
   * @brief ST-overlap rate factor f_overlap ∈ [0,1].
   * Fraction of ego's reachable s-range that is blocked.
   */
  double ComputeOverlapRate(const STBoundary& b, double ego_width) const;

  /**
   * @brief Relative velocity factor f_vel ∈ [0,1].
   * Closing speed normalised by a reference closing speed.
   */
  double ComputeRelativeVel(const Obstacle& obs,
                            const common::TrajectoryPoint& ego) const;

  /**
   * @brief Obstacle type factor f_type ∈ [0,1].
   * Pedestrians/cyclists → higher; parked vehicles → lower.
   */
  double ComputeTypeFactor(const Obstacle& obs) const;

  /**
   * @brief Interaction factor f_interaction ∈ [0,1].
   * Increases when multiple boundaries overlap in time.
   */
  double ComputeInteractionFactor(
      const STBoundary& b,
      const std::vector<const STBoundary*>& all_boundaries) const;

  // --- weights (must sum to 1.0) ---
  static constexpr double kW1 = 0.3;  ///< TTC weight
  static constexpr double kW2 = 0.2;  ///< Overlap weight
  static constexpr double kW3 = 0.2;  ///< Relative velocity weight
  static constexpr double kW4 = 0.1;  ///< Type weight
  static constexpr double kW5 = 0.2;  ///< Interaction weight

  // --- thresholds ---
  static constexpr double kCriticalThreshold  = 0.7;
  static constexpr double kImportantThreshold = 0.3;

  // --- per-level parameters ---
  static constexpr double kCriticalDt    = 0.05;
  static constexpr double kImportantDt   = 0.10;
  static constexpr double kMinorDt       = 0.20;

  static constexpr double kCriticalDSafe   = 1.0;
  static constexpr double kImportantDSafe  = 0.5;
  static constexpr double kMinorDSafe      = 0.3;

  // --- TTC computation constants ---
  static constexpr double kMinTTC = 0.5;   ///< TTC below which score = 1
  static constexpr double kMaxTTC = 8.0;   ///< TTC above which score = 0

  // --- relative velocity constants ---
  static constexpr double kRefClosingSpeed = 10.0;  ///< m/s

  // --- overlap reference ---
  static constexpr double kRefSRange = 50.0;  ///< normalisation length (m)
};

}  // namespace planning
}  // namespace apollo

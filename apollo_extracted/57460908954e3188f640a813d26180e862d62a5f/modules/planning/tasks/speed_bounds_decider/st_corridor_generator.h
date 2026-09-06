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
 * @file st_corridor_generator.h
 * @brief Scan-line based spatiotemporal drivable corridor generator.
 *
 * At each time step t_k the generator:
 *   1. Computes a kinematic reachable set [s_lo, s_hi] from the previous step.
 *   2. Clips the reachable set with all active ST boundaries to obtain free
 *      intervals.
 *   3. Selects the best free interval based on width, continuity, and speed
 *      feasibility.
 *
 * The resulting STCorridorPoint sequence is suitable for direct use with
 * StGraphData::SetSTDrivableBoundary().
 */

#pragma once

#include <utility>
#include <vector>

#include "modules/common_msgs/basic_msgs/pnc_point.pb.h"
#include "modules/planning/planning_base/common/speed/st_boundary.h"
#include "modules/planning/tasks/speed_bounds_decider/threat_assessor.h"

namespace apollo {
namespace planning {

/**
 * @struct STCorridorPoint
 * @brief One time-slice of the drivable corridor.
 */
struct STCorridorPoint {
  double t;
  double s_lower;
  double s_upper;
};

/**
 * @class STCorridorGenerator
 * @brief Generates a temporally-continuous drivable corridor in ST space.
 */
class STCorridorGenerator {
 public:
  STCorridorGenerator() = default;

  /**
   * @brief Generate the drivable corridor via scan-line sweep.
   *
   * @param boundaries    Active (non-empty) ST boundaries.
   * @param threat_info   Per-boundary threat assessment from ThreatAssessor.
   * @param init_point    Ego initial state.
   * @param total_time    ST graph time horizon (s).
   * @param total_length  Path length (s axis upper bound, m).
   * @param dt            Base scan-line time step (s).
   * @return              Sequence of corridor points covering [0, total_time].
   */
  std::vector<STCorridorPoint> Generate(
      const std::vector<const STBoundary*>& boundaries,
      const std::vector<ThreatInfo>& threat_info,
      const common::TrajectoryPoint& init_point,
      double total_time,
      double total_length,
      double dt = 0.1) const;

 private:
  /**
   * @brief Compute the kinematic reachable s-interval for the next step.
   *
   * Uses constant deceleration / acceleration limits to bound how far s can
   * change from [prev_lo, prev_hi] within time dt.
   */
  std::pair<double, double> KinematicReach(double prev_lo, double prev_hi,
                                            double prev_v_lo, double prev_v_hi,
                                            double dt,
                                            double s_max) const;

  /**
   * @brief Clip [s_lo, s_hi] with all active boundaries at time t, returning
   * a sorted list of free intervals.
   *
   * @param t             Current time slice.
   * @param s_lo          Reachable lower s bound.
   * @param s_hi          Reachable upper s bound.
   * @param boundaries    All active ST boundaries.
   * @param threat_info   Per-boundary threat info (for d_safe application).
   * @return              Sorted, non-overlapping free intervals within [s_lo, s_hi].
   */
  std::vector<std::pair<double, double>> GetFreeIntervals(
      double t,
      double s_lo, double s_hi,
      const std::vector<const STBoundary*>& boundaries,
      const std::vector<ThreatInfo>& threat_info) const;

  /**
   * @brief Select the best free interval from candidates.
   *
   * Scoring: w_a·width + w_b·continuity + w_c·speed_feasibility
   *
   * @param intervals     Candidate free intervals.
   * @param prev_lo       Previous corridor lower bound (continuity anchor).
   * @param prev_hi       Previous corridor upper bound (continuity anchor).
   * @param cruise_speed  Desired cruise speed (m/s).
   * @param dt            Time step (s).
   * @return              Selected (s_lower, s_upper) pair.
   */
  std::pair<double, double> SelectBestInterval(
      const std::vector<std::pair<double, double>>& intervals,
      double prev_lo, double prev_hi,
      double cruise_speed, double dt) const;

  // Kinematic constants
  static constexpr double kMaxAcc   =  4.0;  ///< m/s²
  static constexpr double kMaxDec   = -6.0;  ///< m/s²
  static constexpr double kMaxSpeed = 30.0;  ///< m/s

  // Scoring weights
  static constexpr double kWa = 0.4;   ///< width weight
  static constexpr double kWb = 0.4;   ///< continuity weight
  static constexpr double kWc = 0.2;   ///< speed feasibility weight

  // Reference width for normalisation (m)
  static constexpr double kRefWidth = 20.0;
};

}  // namespace planning
}  // namespace apollo

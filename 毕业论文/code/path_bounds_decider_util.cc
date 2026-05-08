/******************************************************************************
 * Copyright 2023 The Apollo Authors. All Rights Reserved.
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

#include "modules/planning/planning_interface_base/task_base/common/path_util/path_bounds_decider_util.h"

#include <algorithm>
#include <cmath>
#include <functional>
#include <limits>
#include <set>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>

#include "modules/common/configs/vehicle_config_helper.h"
#include "modules/common/math/linear_interpolation.h"
#include "modules/common/util/util.h"
#include "modules/planning/planning_base/common/sl_polygon.h"
#include "modules/planning/planning_base/common/util/util.h"
#include "modules/planning/planning_base/gflags/planning_gflags.h"

namespace apollo {
namespace planning {

using apollo::common::VehicleConfigHelper;

namespace {

constexpr double kMikuBoundaryEpsilon = 1.0e-6;

struct MikuObstacleInfo {
    const Obstacle* obstacle = nullptr;
    SLBoundary sl_boundary;
    double min_s = 0.0;
    double max_s = 0.0;
    double center_s = 0.0;
    double center_l = 0.0;
    double constraint_s = 0.0;
    double constraint_end_s = 0.0;
    double longitudinal_speed = 0.0;
    double lateral_buffer = 0.0;
    double threat = 0.0;
    double u = 0.0;
    double v = 0.0;
    double arrival_time = 0.0;
    bool is_dynamic = false;
    size_t polygon_index = 0;
};

struct MikuGroupDecision {
    std::vector<size_t> group_indices;
    std::vector<size_t> ordered_indices;
    int p_star = 0;
    double gap = 0.0;
};

double Clamp(const double x, const double low, const double high) {
    return std::max(low, std::min(high, x));
}

double EstimateArrivalTime(const double ref_s, const SLState& init_sl_state) {
    const double ds = ref_s - init_sl_state.first[0];
    if (ds <= 0.0) {
        return 0.0;
    }
    const double v0 = std::max(0.0, init_sl_state.first[1]);
    const double a0 = init_sl_state.first[2];
    if (std::fabs(a0) < 1.0e-3) {
        return ds / std::max(v0, 1.0e-3);
    }
    const double discriminant = v0 * v0 + 2.0 * a0 * ds;
    if (discriminant <= 0.0) {
        return std::numeric_limits<double>::infinity();
    }
    const double t = (-v0 + std::sqrt(discriminant)) / a0;
    return std::isfinite(t) && t >= 0.0 ? t : ds / std::max(v0, 1.0e-3);
}

bool ProjectObstacleAtTime(
        const ReferenceLine& reference_line,
        const Obstacle& obstacle,
        const double time,
        SLBoundary* const sl_boundary) {
    if (obstacle.IsStatic() || time <= kMikuBoundaryEpsilon || !obstacle.HasTrajectory()) {
        *sl_boundary = obstacle.PerceptionSLBoundary();
        return true;
    }
    const double query_time = std::isfinite(time) ? time : FLAGS_prediction_total_time;
    const auto point = obstacle.GetPointAtTime(query_time);
    const auto box = obstacle.GetBoundingBox(point);
    return reference_line.GetSLBoundary(box, sl_boundary, obstacle.PerceptionSLBoundary().start_s());
}

double LongitudinalVelocityOnReferenceLine(
        const ReferenceLine& reference_line,
        const Obstacle& obstacle,
        const double ref_s) {
    const auto& velocity = obstacle.Perception().velocity();
    const auto ref_point = reference_line.GetReferencePoint(ref_s);
    return velocity.x() * std::cos(ref_point.heading()) + velocity.y() * std::sin(ref_point.heading());
}

double ObstacleTypeFactor(const Obstacle& obstacle) {
    using apollo::perception::PerceptionObstacle;
    const auto& perception = obstacle.Perception();
    if (perception.has_sub_type() && perception.sub_type() == PerceptionObstacle::ST_TRAFFICCONE) {
        return 0.15;
    }
    if (perception.type() == PerceptionObstacle::UNKNOWN_UNMOVABLE && perception.length() <= 1.0
        && perception.width() <= 0.5) {
        return 0.15;
    }
    switch (perception.type()) {
    case PerceptionObstacle::PEDESTRIAN:
    case PerceptionObstacle::BICYCLE:
        return 1.0;
    case PerceptionObstacle::VEHICLE:
        return 0.7;
    case PerceptionObstacle::UNKNOWN_MOVABLE:
    case PerceptionObstacle::UNKNOWN:
        return 0.5;
    case PerceptionObstacle::UNKNOWN_UNMOVABLE:
        return 0.3;
    default:
        return 0.5;
    }
}

double ComputeInteractionFactor(
        const MikuObstacleInfo& info,
        const std::vector<MikuObstacleInfo>& infos,
        const MikuPathBoundsConfig& config) {
    if (infos.size() <= 1 || config.interaction_distance <= kMikuBoundaryEpsilon) {
        return 0.0;
    }
    double value = 0.0;
    for (const auto& other : infos) {
        if (other.obstacle == info.obstacle) {
            continue;
        }
        const double distance = std::hypot(info.center_s - other.center_s, info.center_l - other.center_l);
        if (distance < config.interaction_distance) {
            value += (config.interaction_distance - distance) / config.interaction_distance;
        }
    }
    return Clamp(value / static_cast<double>(infos.size() - 1), 0.0, 1.0);
}

double ComputeThreatScore(
        const MikuObstacleInfo& info,
        const std::vector<MikuObstacleInfo>& infos,
        const SLState& init_sl_state,
        const MikuPathBoundsConfig& config) {
    const double ego_s = init_sl_state.first[0];
    const double ego_v = std::max(0.0, init_sl_state.first[1]);
    const double rel_v = ego_v - info.longitudinal_speed;
    double f_ttc = 0.0;
    const double ds = info.center_s - ego_s;
    if (ds > 0.0 && rel_v > 1.0e-3) {
        const double ttc = ds / rel_v;
        if (ttc <= config.ttc_critical) {
            f_ttc = 1.0;
        } else if (ttc < config.ttc_max) {
            f_ttc = (config.ttc_max - ttc) / (config.ttc_max - config.ttc_critical);
        }
    }

    const double ego_half_width = VehicleConfigHelper::GetConfig().vehicle_param().width() * 0.5;
    const double ego_l_min = init_sl_state.second[0] - ego_half_width;
    const double ego_l_max = init_sl_state.second[0] + ego_half_width;
    const double overlap = std::max(
            0.0, std::min(info.sl_boundary.end_l(), ego_l_max) - std::max(info.sl_boundary.start_l(), ego_l_min));
    const double f_overlap = Clamp(overlap / std::max(0.1, ego_half_width * 2.0), 0.0, 1.0);
    const double v_limit = std::max(1.0, config.velocity_limit);
    const double f_vel = 1.0 / (1.0 + std::exp(-5.0 * rel_v / v_limit));
    const double f_type = ObstacleTypeFactor(*info.obstacle);
    const double f_inter = ComputeInteractionFactor(info, infos, config);

    return Clamp(0.30 * f_ttc + 0.20 * f_overlap + 0.15 * f_vel + 0.10 * f_type + 0.25 * f_inter, 0.0, 1.0);
}

bool IsIgnoredObstacle(const Obstacle& obstacle) {
    return obstacle.HasLongitudinalDecision() && obstacle.HasLateralDecision() && obstacle.IsIgnore();
}

std::vector<std::vector<size_t>> GroupObstaclesByLongitudinalOverlap(
        const std::vector<MikuObstacleInfo>& infos,
        const bool enable_grouping) {
    std::vector<size_t> order(infos.size());
    for (size_t i = 0; i < infos.size(); ++i) {
        order[i] = i;
    }
    std::sort(order.begin(), order.end(), [&infos](const size_t lhs, const size_t rhs) {
        return infos[lhs].min_s < infos[rhs].min_s;
    });

    std::vector<std::vector<size_t>> groups;
    if (!enable_grouping) {
        for (const size_t index : order) {
            groups.push_back({index});
        }
        return groups;
    }

    double s_max = -std::numeric_limits<double>::infinity();
    for (const size_t index : order) {
        if (groups.empty() || infos[index].min_s > s_max) {
            groups.push_back({index});
            s_max = infos[index].max_s;
        } else {
            groups.back().push_back(index);
            s_max = std::max(s_max, infos[index].max_s);
        }
    }
    return groups;
}

bool GetGroupRoadBounds(
        const PathBoundary& path_boundary,
        const std::vector<MikuObstacleInfo>& infos,
        const std::vector<size_t>& group_indices,
        double* const lower_bound,
        double* const upper_bound) {
    double s_min = std::numeric_limits<double>::infinity();
    double s_max = -std::numeric_limits<double>::infinity();
    for (const size_t index : group_indices) {
        s_min = std::min(s_min, infos[index].min_s);
        s_max = std::max(s_max, infos[index].max_s);
    }
    if (!std::isfinite(s_min) || !std::isfinite(s_max)) {
        return false;
    }
    *lower_bound = -std::numeric_limits<double>::infinity();
    *upper_bound = std::numeric_limits<double>::infinity();
    bool has_overlap = false;
    for (const auto& point : path_boundary) {
        if (point.s + FLAGS_path_bounds_decider_resolution < s_min) {
            continue;
        }
        if (point.s > s_max + FLAGS_obstacle_lon_end_buffer_park + FLAGS_path_bounds_decider_resolution) {
            break;
        }
        *lower_bound = std::max(*lower_bound, point.l_lower.l);
        *upper_bound = std::min(*upper_bound, point.l_upper.l);
        has_overlap = true;
    }
    return has_overlap && *lower_bound <= *upper_bound;
}

MikuGroupDecision CalculateOptimalNudgeDirection(
        const std::vector<MikuObstacleInfo>& infos,
        const std::vector<size_t>& group_indices,
        const double road_lower,
        const double road_upper,
        const bool enable_max_gap) {
    MikuGroupDecision decision;
    decision.group_indices = group_indices;
    for (const size_t index : group_indices) {
        if (infos[index].u < road_upper && infos[index].v > road_lower) {
            decision.ordered_indices.push_back(index);
        }
    }
    std::sort(
            decision.ordered_indices.begin(),
            decision.ordered_indices.end(),
            [&infos](const size_t lhs, const size_t rhs) {
                if (std::fabs(infos[lhs].u - infos[rhs].u) > kMikuBoundaryEpsilon) {
                    return infos[lhs].u < infos[rhs].u;
                }
                return infos[lhs].v > infos[rhs].v;
            });
    const int k = static_cast<int>(decision.ordered_indices.size());
    if (k == 0) {
        decision.p_star = 0;
        decision.gap = road_upper - road_lower;
        return decision;
    }

    std::vector<double> gaps;
    gaps.reserve(static_cast<size_t>(k + 1));
    gaps.push_back(infos[decision.ordered_indices.front()].u - road_lower);
    for (int p = 1; p < k; ++p) {
        gaps.push_back(infos[decision.ordered_indices[p]].u - infos[decision.ordered_indices[p - 1]].v);
    }
    gaps.push_back(road_upper - infos[decision.ordered_indices.back()].v);

    if (enable_max_gap) {
        decision.p_star = static_cast<int>(std::distance(gaps.begin(), std::max_element(gaps.begin(), gaps.end())));
    } else {
        decision.p_star = gaps.back() >= gaps.front() ? k : 0;
    }
    decision.gap = gaps[decision.p_star];
    return decision;
}

bool UpdateMikuBoundaryAtS(
        const ReferenceLine& reference_line,
        const SLState& init_sl_state,
        const MikuPathBoundsConfig& config,
        const std::vector<MikuObstacleInfo>& infos,
        const MikuGroupDecision& decision,
        const size_t path_index,
        PathBoundary* const path_boundary,
        std::string* const blocked_id,
        double* const narrowest_width) {
    auto& path_point = path_boundary->at(path_index);
    const double s = path_point.s;
    double lower = path_point.l_lower.l;
    double upper = path_point.l_upper.l;
    std::string lower_id = path_point.l_lower.id;
    std::string upper_id = path_point.l_upper.id;
    bool has_active_obstacle = false;

    for (size_t order_pos = 0; order_pos < decision.ordered_indices.size(); ++order_pos) {
        const size_t index = decision.ordered_indices[order_pos];
        const auto& info = infos[index];
        SLBoundary sl_boundary;
        const double tau
                = info.is_dynamic && config.enable_dynamic_projection ? EstimateArrivalTime(s, init_sl_state) : 0.0;
        if (!ProjectObstacleAtTime(reference_line, *info.obstacle, tau, &sl_boundary)) {
            continue;
        }
        double min_s = sl_boundary.start_s();
        double max_s = sl_boundary.end_s() + FLAGS_obstacle_lon_end_buffer_park;
        if (max_s - min_s < FLAGS_path_bounds_decider_resolution) {
            max_s += FLAGS_path_bounds_decider_resolution;
            min_s -= FLAGS_path_bounds_decider_resolution;
        }
        if (s < min_s || s > max_s) {
            continue;
        }
        has_active_obstacle = true;
        const double center_buffer
                = VehicleConfigHelper::GetConfig().vehicle_param().width() * 0.5 + info.lateral_buffer;
        const double u = sl_boundary.start_l() - center_buffer;
        const double v = sl_boundary.end_l() + center_buffer;
        if (static_cast<int>(order_pos) < decision.p_star) {
            if (v > lower) {
                lower = v;
                lower_id = info.obstacle->Id();
            }
        } else {
            if (u < upper) {
                upper = u;
                upper_id = info.obstacle->Id();
            }
        }
    }

    if (!has_active_obstacle) {
        return true;
    }
    if (lower > upper) {
        *blocked_id = lower_id.empty() ? upper_id : lower_id;
        if (blocked_id->empty() && !decision.ordered_indices.empty()) {
            *blocked_id = infos[decision.ordered_indices.front()].obstacle->Id();
        }
        PathBoundsDeciderUtil::TrimPathBounds(static_cast<int>(path_index), path_boundary);
        return false;
    }
    if (lower > path_point.l_lower.l) {
        path_point.l_lower.l = lower;
        path_point.l_lower.type = BoundType::OBSTACLE;
        path_point.l_lower.id = lower_id;
        path_point.is_nudge_bound[RIGHT_INDEX] = true;
    }
    if (upper < path_point.l_upper.l) {
        path_point.l_upper.l = upper;
        path_point.l_upper.type = BoundType::OBSTACLE;
        path_point.l_upper.id = upper_id;
        path_point.is_nudge_bound[LEFT_INDEX] = true;
    }
    *narrowest_width = std::min(*narrowest_width, path_point.l_upper.l - path_point.l_lower.l);
    return true;
}

}  // namespace

bool PathBoundsDeciderUtil::InitPathBoundary(
        const ReferenceLineInfo& reference_line_info,
        PathBoundary* const path_bound,
        SLState init_sl_state) {
    // Sanity checks.
    CHECK_NOTNULL(path_bound);
    path_bound->clear();
    const auto& reference_line = reference_line_info.reference_line();
    path_bound->set_delta_s(FLAGS_path_bounds_decider_resolution);

    const auto& vehicle_config = common::VehicleConfigHelper::Instance()->GetConfig();
    const double ego_front_to_center = vehicle_config.vehicle_param().front_edge_to_center();

    for (double curr_s = init_sl_state.first[0]; curr_s
         < std::fmin(init_sl_state.first[0]
                             + std::fmax(
                                     FLAGS_path_bounds_horizon,
                                     reference_line_info.GetCruiseSpeed() * FLAGS_trajectory_time_length),
                     reference_line.Length() - ego_front_to_center);
         curr_s += FLAGS_path_bounds_decider_resolution) {
        path_bound->emplace_back(curr_s, std::numeric_limits<double>::lowest(), std::numeric_limits<double>::max());
    }

    // Return.
    if (path_bound->empty()) {
        ADEBUG << "Empty path boundary in InitPathBoundary";
        return false;
    }
    return true;
}

void PathBoundsDeciderUtil::GetStartPoint(
        common::TrajectoryPoint planning_start_point,
        const ReferenceLine& reference_line,
        SLState* init_sl_state) {
    if (FLAGS_use_front_axe_center_in_path_planning) {
        planning_start_point = InferFrontAxeCenterFromRearAxeCenter(planning_start_point);
    }
    AINFO << std::fixed << "Plan at the starting point: x = " << planning_start_point.path_point().x()
          << ", y = " << planning_start_point.path_point().y()
          << ", and angle = " << planning_start_point.path_point().theta();

    // Initialize some private variables.
    // ADC s/l info.
    *init_sl_state = reference_line.ToFrenetFrame(planning_start_point);
}

double PathBoundsDeciderUtil::GetADCLaneWidth(const ReferenceLine& reference_line, const double adc_s) {
    double lane_left_width = 0.0;
    double lane_right_width = 0.0;
    if (!reference_line.GetLaneWidth(adc_s, &lane_left_width, &lane_right_width)) {
        constexpr double kDefaultLaneWidth = 5.0;
        AWARN << "Failed to get lane width at planning start point.";
        return kDefaultLaneWidth;
    } else {
        return lane_left_width + lane_right_width;
    }
}

bool PathBoundsDeciderUtil::UpdatePathBoundaryWithBuffer(
        double left_bound,
        double right_bound,
        BoundType left_type,
        BoundType right_type,
        std::string left_id,
        std::string right_id,
        PathBoundPoint* const bound_point) {
    if (!UpdateLeftPathBoundaryWithBuffer(left_bound, left_type, left_id, bound_point)) {
        return false;
    }
    if (!UpdateRightPathBoundaryWithBuffer(right_bound, right_type, right_id, bound_point)) {
        return false;
    }
    return true;
}

bool PathBoundsDeciderUtil::UpdateLeftPathBoundaryWithBuffer(
        double left_bound,
        BoundType left_type,
        std::string left_id,
        PathBoundPoint* const bound_point) {
    double adc_half_width = VehicleConfigHelper::GetConfig().vehicle_param().width() / 2.0;
    left_bound = left_bound - adc_half_width;
    PathBoundPoint new_point = *bound_point;
    if (new_point.l_upper.l > left_bound) {
        new_point.l_upper.l = left_bound;
        new_point.l_upper.type = left_type;
        new_point.l_upper.id = left_id;
    }
    // Check if ADC is blocked.
    // If blocked, don't update anything, return false.
    if (new_point.l_lower.l > new_point.l_upper.l) {
        ADEBUG << "Path is blocked at" << new_point.l_lower.l << " " << new_point.l_upper.l;
        return false;
    }
    // Otherwise, update path_boundaries and center_line; then return true.
    *bound_point = new_point;
    return true;
}

bool PathBoundsDeciderUtil::UpdateRightPathBoundaryWithBuffer(
        double right_bound,
        BoundType right_type,
        std::string right_id,
        PathBoundPoint* const bound_point) {
    double adc_half_width = VehicleConfigHelper::GetConfig().vehicle_param().width() / 2.0;
    right_bound = right_bound + adc_half_width;
    PathBoundPoint new_point = *bound_point;
    if (new_point.l_lower.l < right_bound) {
        new_point.l_lower.l = right_bound;
        new_point.l_lower.type = right_type;
        new_point.l_lower.id = right_id;
    }
    // Check if ADC is blocked.
    // If blocked, don't update anything, return false.
    if (new_point.l_lower.l > new_point.l_upper.l) {
        ADEBUG << "Path is blocked at";
        return false;
    }
    // Otherwise, update path_boundaries and center_line; then return true.
    *bound_point = new_point;
    return true;
}

void PathBoundsDeciderUtil::TrimPathBounds(const int path_blocked_idx, PathBoundary* const path_boundaries) {
    if (path_blocked_idx != -1) {
        if (path_blocked_idx == 0) {
            AINFO << "Completely blocked. Cannot move at all.";
        }
        double front_edge_to_center = VehicleConfigHelper::GetConfig().vehicle_param().front_edge_to_center();
        double trimmed_s = path_boundaries->at(path_blocked_idx).s - front_edge_to_center;
        AINFO << "Trimmed from " << path_boundaries->back().s << " to " << path_boundaries->at(path_blocked_idx).s;
        while (path_boundaries->size() > 1 && path_boundaries->back().s > trimmed_s) {
            path_boundaries->pop_back();
        }
    }
}

void PathBoundsDeciderUtil::GetSLPolygons(
        const ReferenceLineInfo& reference_line_info,
        std::vector<SLPolygon>* polygons,
        const SLState& init_sl_state) {
    polygons->clear();
    auto obstacles = reference_line_info.path_decision().obstacles();
    const double adc_back_edge_s = reference_line_info.AdcSlBoundary().start_s();
    for (const auto* obstacle : obstacles.Items()) {
        if (!IsWithinPathDeciderScopeObstacle(*obstacle)) {
            continue;
        }
        auto xy_poly = obstacle->PerceptionPolygon();

        // if (obstacle->PerceptionSLBoundary().end_s() < init_sl_state.first[0]) {
        //     continue;
        // }
        if (obstacle->PerceptionSLBoundary().end_s() < adc_back_edge_s) {
            continue;
        }
        const auto obstacle_sl = obstacle->PerceptionSLBoundary();
        polygons->emplace_back(obstacle_sl, obstacle->Id());
    }
    sort(polygons->begin(), polygons->end(), [](const SLPolygon& a, const SLPolygon& b) {
        return a.MinS() < b.MinS();
    });
}

bool PathBoundsDeciderUtil::UpdatePathBoundaryBySLPolygon(
        const ReferenceLineInfo& reference_line_info,
        std::vector<SLPolygon>* const sl_polygon,
        const SLState& init_sl_state,
        PathBoundary* const path_boundary,
        std::string* const blocked_id,
        double* const narrowest_width) {
    std::vector<double> center_l;
    double max_nudge_check_distance;
    if (reference_line_info.IsChangeLanePath() || path_boundary->label().find("regular/left") != std::string::npos
        || path_boundary->label().find("regular/right") != std::string::npos) {
        center_l.push_back((path_boundary->front().l_upper.l + path_boundary->front().l_lower.l) * 0.5);
        max_nudge_check_distance = FLAGS_max_nudge_check_distance_in_lk;
    } else {
        center_l.push_back(0.0);
        max_nudge_check_distance = FLAGS_max_nudge_check_distance_in_lc;
    }

    *narrowest_width = path_boundary->front().l_upper.l - path_boundary->front().l_lower.l;
    double mid_l = (path_boundary->front().l_upper.l + path_boundary->front().l_lower.l) / 2;
    size_t nudge_check_count = size_t(max_nudge_check_distance / FLAGS_path_bounds_decider_resolution);
    double last_max_nudge_l = center_l.front();

    for (size_t i = 1; i < path_boundary->size(); ++i) {
        double path_boundary_s = path_boundary->at(i).s;
        auto& left_bound = path_boundary->at(i).l_upper;
        auto& right_bound = path_boundary->at(i).l_lower;
        double default_width = right_bound.l - left_bound.l;
        auto begin_it = center_l.end() - std::min(nudge_check_count, center_l.size());
        last_max_nudge_l = *std::max_element(
                begin_it, center_l.end(), [](double a, double b) { return std::fabs(a) < std::fabs(b); });
        // AINFO << "last max nudge l: " << last_max_nudge_l;
        for (size_t j = 0; j < sl_polygon->size(); j++) {
            // double min_s = sl_polygon->at(j).MinS() -
            // FLAGS_path_bounds_decider_resolution; double max_s =
            // sl_polygon->at(j).MaxS() + FLAGS_path_bounds_decider_resolution;
            double min_s = sl_polygon->at(j).MinS();
            double max_s = sl_polygon->at(j).MaxS() + FLAGS_obstacle_lon_end_buffer_park;
            if (max_s - min_s < FLAGS_path_bounds_decider_resolution) {
                max_s += FLAGS_path_bounds_decider_resolution;
                min_s -= FLAGS_path_bounds_decider_resolution;
            }
            if (max_s < path_boundary_s) {
                continue;
            }
            if (min_s > path_boundary_s) {
                break;
            }
            double l_lower = sl_polygon->at(j).GetRightBoundaryByS(path_boundary_s);
            double l_upper = sl_polygon->at(j).GetLeftBoundaryByS(path_boundary_s);
            if (sl_polygon->at(j).NudgeInfo() == SLPolygon::UNDEFINED) {
                AINFO << "last_max_nudge_l: " << last_max_nudge_l << ", obs id: " << sl_polygon->at(j).id()
                      << ", obs l: " << l_lower << ", " << l_upper;
                double obs_l = (l_lower + l_upper) / 2;
                if (std::fabs(obs_l - mid_l) < 0.4 && std::fabs(path_boundary_s - init_sl_state.first[0]) < 5.0) {
                    if (init_sl_state.second[0] < obs_l) {
                        sl_polygon->at(j).SetNudgeInfo(SLPolygon::RIGHT_NUDGE);
                        AINFO << sl_polygon->at(j).id() << " right nudge with init_sl_state";
                    } else {
                        sl_polygon->at(j).SetNudgeInfo(SLPolygon::LEFT_NUDGE);
                        AINFO << sl_polygon->at(j).id() << " left nudge width init_sl_state";
                    }
                } else {
                    if (last_max_nudge_l < obs_l) {
                        sl_polygon->at(j).SetNudgeInfo(SLPolygon::RIGHT_NUDGE);
                        AINFO << sl_polygon->at(j).id() << " right nudge";
                    } else {
                        sl_polygon->at(j).SetNudgeInfo(SLPolygon::LEFT_NUDGE);
                        AINFO << sl_polygon->at(j).id() << " left nudge";
                    }
                }
            } else {
                AINFO << "last_max_nudge_l: " << last_max_nudge_l << ", obs id: " << sl_polygon->at(j).id()
                      << ", obs l: " << l_lower << ", " << l_upper << ", nudge info: " << sl_polygon->at(j).NudgeInfo();
            }
            if (sl_polygon->at(j).NudgeInfo() == SLPolygon::RIGHT_NUDGE) {
                // right nudge
                l_lower -= GetBufferBetweenADCCenterAndEdge();
                if (l_lower <= right_bound.l) {
                    // boundary is blocked
                    *blocked_id = sl_polygon->at(j).id();
                    AINFO << "blocked at " << *blocked_id << ", " << path_boundary_s << ", l_lower: " << l_lower
                          << ", l_upper: " << l_upper;
                    sl_polygon->at(j).SetNudgeInfo(SLPolygon::BLOCKED);
                    break;
                }
                if (l_lower < left_bound.l) {
                    AINFO << "update left_bound: s " << path_boundary_s << ", l " << left_bound.l << " -> " << l_lower;
                    left_bound.l = l_lower;
                    left_bound.type = BoundType::OBSTACLE;
                    left_bound.id = sl_polygon->at(j).id();
                    *narrowest_width = std::min(*narrowest_width, left_bound.l - right_bound.l);
                }
            } else {
                // left nudge
                l_upper += GetBufferBetweenADCCenterAndEdge();
                if (l_upper >= left_bound.l) {
                    // boundary is blocked
                    *blocked_id = sl_polygon->at(j).id();
                    AINFO << "blocked at " << *blocked_id << ", " << path_boundary_s << ", l_lower: " << l_lower
                          << ", l_upper: " << l_upper;
                    sl_polygon->at(j).SetNudgeInfo(SLPolygon::BLOCKED);
                    break;
                }
                if (l_upper > right_bound.l) {
                    AINFO << "update right_bound: s " << path_boundary_s << ", l " << right_bound.l << " -> "
                          << l_upper;
                    right_bound.l = l_upper;
                    right_bound.type = BoundType::OBSTACLE;
                    right_bound.id = sl_polygon->at(j).id();
                    *narrowest_width = std::min(*narrowest_width, left_bound.l - right_bound.l);
                }
            }
            last_max_nudge_l
                    = std::fabs((left_bound.l + right_bound.l) / 2.0 - mid_l) > std::fabs(last_max_nudge_l - mid_l)
                    ? (left_bound.l + right_bound.l) / 2.0
                    : last_max_nudge_l;
        }
        // if blocked, trim path
        if (!blocked_id->empty()) {
            TrimPathBounds(i, path_boundary);
            *narrowest_width = default_width;
            return false;
        }
        center_l.push_back((left_bound.l + right_bound.l) / 2.0);
        // AINFO << "update s: " << path_boundary_s
        //       << ", center_l: " << center_l.back();
    }
    return true;
}

bool PathBoundsDeciderUtil::AddCornerPoint(
        double s,
        double l_lower,
        double l_upper,
        const PathBoundary& path_boundary,
        ObsCornerConstraints* extra_constraints) {
    size_t left_index = 0;
    size_t right_index = 0;
    double left_weight = 0.0;
    double right_weight = 0.0;
    if (!path_boundary.get_interpolated_s_weight(s, &left_weight, &right_weight, &left_index, &right_index)) {
        AERROR << "Fail to find extra path bound point in path boundary: " << s
               << ", path boundary start s: " << path_boundary.front().s
               << ", path boundary end s: " << path_boundary.back().s;
        return false;
    }
    if (left_weight < 0.05 || right_weight < 0.05) {
        // filter contraint that near evaulated point
        return false;
    }
    ADEBUG << "corner" << s << "left_weight" << left_weight << "right_weight" << right_weight << "left_index"
           << left_index << "right_index" << right_index << "l_lower" << l_lower << "l_upper" << l_upper;
    extra_constraints->emplace_back(left_weight, right_weight, l_lower, l_upper, left_index, right_index, s);
    return true;
}

bool PathBoundsDeciderUtil::AddCornerPoint(
        SLPoint sl_pt,
        const PathBoundary& path_boundary,
        ObsCornerConstraints* extra_constraints,
        bool is_left,
        std::string obs_id,
        bool is_front_pt) {
    size_t left_index = 0;
    size_t right_index = 0;
    double left_weight = 0.0;
    double right_weight = 0.0;
    if (!path_boundary.get_interpolated_s_weight(sl_pt.s(), &left_weight, &right_weight, &left_index, &right_index)) {
        AERROR << "Fail to find extra path bound point in path boundary: " << sl_pt.s()
               << ", path boundary start s: " << path_boundary.front().s
               << ", path boundary end s: " << path_boundary.back().s;
        return true;
    }
    // if (left_weight < 0.05 || right_weight < 0.05) {
    //   // filter contraint that near evaulated point
    //   return true;
    // }

    double bound_l_upper
            = path_boundary.get_upper_bound_by_interpolated_index(left_weight, right_weight, left_index, right_index);
    double bound_l_lower
            = path_boundary.get_lower_bound_by_interpolated_index(left_weight, right_weight, left_index, right_index);

    double corner_l
            = is_left ? sl_pt.l() - GetBufferBetweenADCCenterAndEdge() : sl_pt.l() + GetBufferBetweenADCCenterAndEdge();
    if ((is_left && corner_l < bound_l_upper) || (!is_left && corner_l > bound_l_lower)) {
        if (is_left) {
            bound_l_upper = corner_l;
        } else {
            bound_l_lower = corner_l;
        }
        extra_constraints->emplace_back(
                left_weight, right_weight, bound_l_lower, bound_l_upper, left_index, right_index, sl_pt.s(), obs_id);
        if (bound_l_upper < bound_l_lower) {
            extra_constraints->blocked_id = obs_id;
            extra_constraints->block_left_index = left_index;
            extra_constraints->block_right_index = right_index;
            AINFO << "AddCornerPoint blocked id: " << obs_id << ", index [" << left_index << ", " << right_index << "]";
            return false;
        }
    }

    if (FLAGS_enable_expand_obs_corner) {
        double add_s = is_front_pt ? sl_pt.s() - FLAGS_expand_obs_corner_lon_buffer
                                   : sl_pt.s() + FLAGS_expand_obs_corner_lon_buffer;
        if (!path_boundary.get_interpolated_s_weight(add_s, &left_weight, &right_weight, &left_index, &right_index)) {
            return true;
        }

        bound_l_upper = path_boundary.get_upper_bound_by_interpolated_index(
                left_weight, right_weight, left_index, right_index);
        bound_l_lower = path_boundary.get_lower_bound_by_interpolated_index(
                left_weight, right_weight, left_index, right_index);

        if ((is_left && corner_l < bound_l_upper) || (!is_left && corner_l > bound_l_lower)) {
            if (is_left) {
                bound_l_upper = corner_l;
            } else {
                bound_l_lower = corner_l;
            }
            extra_constraints->emplace_back(
                    left_weight, right_weight, bound_l_lower, bound_l_upper, left_index, right_index, add_s, obs_id);
            if (bound_l_upper < bound_l_lower) {
                extra_constraints->blocked_id = obs_id;
                extra_constraints->block_left_index = left_index;
                extra_constraints->block_right_index = right_index;
                AINFO << "AddCornerPoint blocked id: " << obs_id << ", index [" << left_index << ", " << right_index
                      << "]";
                return false;
            }
        }
    }

    return true;
}

void PathBoundsDeciderUtil::AddCornerBounds(
        const std::vector<SLPolygon>& sl_polygons,
        PathBoundary* const path_boundary) {
    auto* extra_path_bound = path_boundary->mutable_extra_path_bound();
    for (const auto& obs_polygon : sl_polygons) {
        if (obs_polygon.MinS() > path_boundary->back().s) {
            ADEBUG << "obs_polygon.MinS()" << obs_polygon.MinS() << "path_boundary->back().s"
                   << path_boundary->back().s;
            break;
        }
        if (obs_polygon.MaxS() < path_boundary->front().s) {
            continue;
        }
        if (obs_polygon.NudgeInfo() == SLPolygon::LEFT_NUDGE) {
            for (size_t i = 0; i < obs_polygon.LeftBoundary().size(); i++) {
                auto pt = obs_polygon.LeftBoundary().at(i);
                bool is_front_pt = i < (obs_polygon.LeftBoundary().size() * 0.5);
                if (!AddCornerPoint(pt, *path_boundary, extra_path_bound, false, obs_polygon.id(), is_front_pt)) {
                    break;
                }
            }
            // for (auto pt : obs_polygon.LeftBoundary()) {
            //   if (!AddCornerPoint(pt, *path_boundary, extra_path_bound, false,
            //                       obs_polygon.id())) {
            //     break;
            //   }
            // }
        } else if (obs_polygon.NudgeInfo() == SLPolygon::RIGHT_NUDGE) {
            for (size_t i = 0; i < obs_polygon.RightBoundary().size(); i++) {
                auto pt = obs_polygon.RightBoundary().at(i);
                bool is_front_pt = i > (obs_polygon.RightBoundary().size() * 0.5);
                if (!AddCornerPoint(pt, *path_boundary, extra_path_bound, true, obs_polygon.id(), is_front_pt)) {
                    break;
                }
            }
            // for (auto pt : obs_polygon.RightBoundary()) {
            //   if (!AddCornerPoint(pt, *path_boundary, extra_path_bound, true,
            //                       obs_polygon.id())) {
            //     break;
            //   }
            // }
        } else {
            AINFO << "no nugde info, ignore obs: " << obs_polygon.id();
        }
        if (!extra_path_bound->blocked_id.empty()) {
            break;
        }
    }
    // sort(extra_path_bound->begin(), extra_path_bound->end(),
    //      [](const InterPolatedPoint& a, const InterPolatedPoint& b) {
    //        return a.rear_axle_s < b.rear_axle_s;
    //      });
}

void PathBoundsDeciderUtil::AddAdcVertexBounds(PathBoundary* const path_boundary) {
    auto* adc_vertex_bound = path_boundary->mutable_adc_vertex_bound();
    // front_edge_to_center in Apollo is the front edge to rear center
    double front_edge_to_center
            = apollo::common::VehicleConfigHelper::GetConfig().vehicle_param().front_edge_to_center();
    for (size_t i = 0; i < path_boundary->size(); i++) {
        double rear_axle_s = path_boundary->at(i).s - front_edge_to_center;
        if (rear_axle_s <= path_boundary->start_s()) {
            continue;
        }
        size_t left_index = 0;
        size_t right_index = 0;
        double left_weight = 0.0;
        double right_weight = 0.0;
        if (!path_boundary->get_interpolated_s_weight(
                    rear_axle_s, &left_weight, &right_weight, &left_index, &right_index)) {
            AERROR << "Fail to find vertex path bound point in path boundary: " << path_boundary->at(i).s
                   << "path boundary start s: " << path_boundary->front().s
                   << ", path boundary end s: " << path_boundary->back().s;
            continue;
        }
        adc_vertex_bound->emplace_back(
                left_weight,
                right_weight,
                path_boundary->at(i).l_lower.l,
                path_boundary->at(i).l_upper.l,
                left_index,
                right_index,
                rear_axle_s);
    }
    adc_vertex_bound->front_edge_to_center = front_edge_to_center;
}

bool PathBoundsDeciderUtil::GetBoundaryFromStaticObstacles(
        const ReferenceLineInfo& reference_line_info,
        std::vector<SLPolygon>* const sl_polygons,
        const SLState& init_sl_state,
        PathBoundary* const path_boundary,
        std::string* const blocking_obstacle_id,
        double* const narrowest_width) {
    UpdatePathBoundaryBySLPolygon(
            reference_line_info, sl_polygons, init_sl_state, path_boundary, blocking_obstacle_id, narrowest_width);
    AddExtraPathBound(*sl_polygons, path_boundary, init_sl_state, blocking_obstacle_id);
    return true;
}

bool PathBoundsDeciderUtil::GetBoundaryFromMikuObstacles(
        const ReferenceLineInfo& reference_line_info,
        const SLState& init_sl_state,
        const MikuPathBoundsConfig& config,
        PathBoundary* const path_boundary,
        std::string* const blocking_obstacle_id,
        double* const narrowest_width,
        std::vector<std::pair<double, double>>* const speed_constraints) {
    CHECK_NOTNULL(path_boundary);
    CHECK_NOTNULL(blocking_obstacle_id);
    CHECK_NOTNULL(narrowest_width);
    CHECK_NOTNULL(speed_constraints);
    speed_constraints->clear();

    const auto& reference_line = reference_line_info.reference_line();
    const auto& indexed_obstacles = reference_line_info.path_decision().obstacles();
    const double adc_back_edge_s = reference_line_info.AdcSlBoundary().start_s();
    const double adc_half_width = VehicleConfigHelper::GetConfig().vehicle_param().width() * 0.5;

    std::vector<MikuObstacleInfo> infos;
    infos.reserve(indexed_obstacles.Items().size());
    for (const auto* obstacle : indexed_obstacles.Items()) {
        if (obstacle == nullptr || obstacle->IsVirtual() || IsIgnoredObstacle(*obstacle)) {
            continue;
        }

        MikuObstacleInfo info;
        info.obstacle = obstacle;
        info.is_dynamic = !obstacle->IsStatic();
        const auto& current_sl = obstacle->PerceptionSLBoundary();
        info.constraint_s = current_sl.start_s();
        info.constraint_end_s = current_sl.end_s();
        info.arrival_time = info.is_dynamic && config.enable_dynamic_projection
                ? EstimateArrivalTime(info.constraint_s, init_sl_state)
                : 0.0;
        info.longitudinal_speed = LongitudinalVelocityOnReferenceLine(
                reference_line, *obstacle, std::max(init_sl_state.first[0], current_sl.start_s()));
        if (!ProjectObstacleAtTime(reference_line, *obstacle, info.arrival_time, &info.sl_boundary)) {
            continue;
        }
        if (info.sl_boundary.end_s() < adc_back_edge_s) {
            continue;
        }
        info.min_s = info.sl_boundary.start_s();
        info.max_s = info.sl_boundary.end_s();
        info.center_s = 0.5 * (info.sl_boundary.start_s() + info.sl_boundary.end_s());
        info.center_l = 0.5 * (info.sl_boundary.start_l() + info.sl_boundary.end_l());
        infos.push_back(info);
    }

    if (infos.empty()) {
        *narrowest_width = path_boundary->front().l_upper.l - path_boundary->front().l_lower.l;
        return true;
    }

    for (auto& info : infos) {
        if (config.enable_threat_buffer) {
            info.threat = ComputeThreatScore(info, infos, init_sl_state, config);
            const double ratio = Clamp(info.threat, 0.0, 1.0);
            const double buffer_min = std::min(config.threat_buffer_min, config.threat_buffer_max);
            const double buffer_max = std::max(config.threat_buffer_min, config.threat_buffer_max);
            info.lateral_buffer = buffer_min + (buffer_max - buffer_min) * ratio;
        } else {
            info.threat = 1.0;
            info.lateral_buffer = FLAGS_obstacle_lat_buffer;
        }
        const double center_buffer = adc_half_width + info.lateral_buffer;
        info.u = info.sl_boundary.start_l() - center_buffer;
        info.v = info.sl_boundary.end_l() + center_buffer;
    }

    std::vector<SLPolygon> miku_sl_polygons;
    miku_sl_polygons.reserve(infos.size());
    for (const auto& info : infos) {
        miku_sl_polygons.emplace_back(info.sl_boundary, info.obstacle->Id());
    }

    const auto groups = GroupObstaclesByLongitudinalOverlap(infos, config.enable_grouping);
    double local_narrowest_width = path_boundary->front().l_upper.l - path_boundary->front().l_lower.l;
    *narrowest_width = local_narrowest_width;
    bool blocked = false;

    for (const auto& group : groups) {
        double road_lower = 0.0;
        double road_upper = 0.0;
        if (!GetGroupRoadBounds(*path_boundary, infos, group, &road_lower, &road_upper)) {
            continue;
        }
        const auto decision
                = CalculateOptimalNudgeDirection(infos, group, road_lower, road_upper, config.enable_max_gap);

        for (size_t order_pos = 0; order_pos < decision.ordered_indices.size(); ++order_pos) {
            const size_t index = decision.ordered_indices[order_pos];
            if (static_cast<int>(order_pos) < decision.p_star) {
                miku_sl_polygons[index].SetNudgeInfo(SLPolygon::LEFT_NUDGE);
            } else {
                miku_sl_polygons[index].SetNudgeInfo(SLPolygon::RIGHT_NUDGE);
            }
        }

        const auto min_it = std::min_element(group.begin(), group.end(), [&infos](const size_t lhs, const size_t rhs) {
            return infos[lhs].min_s < infos[rhs].min_s;
        });
        const auto max_it = std::max_element(group.begin(), group.end(), [&infos](const size_t lhs, const size_t rhs) {
            return infos[lhs].max_s < infos[rhs].max_s;
        });
        if (min_it == group.end() || max_it == group.end()) {
            continue;
        }
        const double group_s_min = infos[*min_it].min_s;
        const double group_s_max = infos[*max_it].max_s;

        for (size_t i = 1; i < path_boundary->size(); ++i) {
            const double path_s = path_boundary->at(i).s;
            if (path_s + FLAGS_path_bounds_decider_resolution < group_s_min) {
                continue;
            }
            if (path_s > group_s_max + FLAGS_obstacle_lon_end_buffer_park + FLAGS_path_bounds_decider_resolution) {
                break;
            }
            if (!UpdateMikuBoundaryAtS(
                        reference_line,
                        init_sl_state,
                        config,
                        infos,
                        decision,
                        i,
                        path_boundary,
                        blocking_obstacle_id,
                        &local_narrowest_width)) {
                blocked = true;
                break;
            }
        }
        if (blocked) {
            break;
        }
    }

    AddExtraPathBound(miku_sl_polygons, path_boundary, init_sl_state, blocking_obstacle_id);
    *narrowest_width = local_narrowest_width;

    for (const auto& info : infos) {
        if (info.is_dynamic && info.arrival_time > kMikuBoundaryEpsilon) {
            speed_constraints->emplace_back(info.constraint_s, info.arrival_time);
            if (info.constraint_end_s - info.constraint_s > 2.0 * adc_half_width) {
                speed_constraints->emplace_back(
                        info.constraint_end_s, EstimateArrivalTime(info.constraint_end_s, init_sl_state));
            }
        }
    }

    return true;
}

double PathBoundsDeciderUtil::GetBufferBetweenADCCenterAndEdge() {
    double adc_half_width = VehicleConfigHelper::GetConfig().vehicle_param().width() / 2.0;

    return (adc_half_width + FLAGS_obstacle_lat_buffer);
}

bool PathBoundsDeciderUtil::IsWithinPathDeciderScopeObstacle(const Obstacle& obstacle) {
    // Obstacle should be non-virtual.
    if (obstacle.IsVirtual()) {
        return false;
    }
    // Obstacle should not have ignore decision.
    if (obstacle.HasLongitudinalDecision() && obstacle.HasLateralDecision() && obstacle.IsIgnore()) {
        return false;
    }
    // Obstacle should not be moving obstacle.
    if (!obstacle.IsStatic() || obstacle.speed() > FLAGS_static_obstacle_speed_threshold) {
        return false;
    }
    // TODO(jiacheng):
    // Some obstacles are not moving, but only because they are waiting for
    // red light (traffic rule) or because they are blocked by others (social).
    // These obstacles will almost certainly move in the near future and we
    // should not side-pass such obstacles.

    return true;
}

common::TrajectoryPoint PathBoundsDeciderUtil::InferFrontAxeCenterFromRearAxeCenter(
        const common::TrajectoryPoint& traj_point) {
    double front_to_rear_axe_distance = VehicleConfigHelper::GetConfig().vehicle_param().wheel_base();
    common::TrajectoryPoint ret = traj_point;
    ret.mutable_path_point()->set_x(
            traj_point.path_point().x() + front_to_rear_axe_distance * std::cos(traj_point.path_point().theta()));
    ret.mutable_path_point()->set_y(
            traj_point.path_point().y() + front_to_rear_axe_distance * std::sin(traj_point.path_point().theta()));
    return ret;
}

bool PathBoundsDeciderUtil::GetBoundaryFromSelfLane(
        const ReferenceLineInfo& reference_line_info,
        const SLState& init_sl_state,
        PathBoundary* const path_bound) {
    // Sanity checks.
    CHECK_NOTNULL(path_bound);
    ACHECK(!path_bound->empty());
    const ReferenceLine& reference_line = reference_line_info.reference_line();
    double adc_lane_width = GetADCLaneWidth(reference_line, init_sl_state.first[0]);
    // Go through every point, update the boundary based on lane info and
    // ADC's position.
    double past_lane_left_width = adc_lane_width / 2.0;
    double past_lane_right_width = adc_lane_width / 2.0;
    int path_blocked_idx = -1;
    for (size_t i = 0; i < path_bound->size(); ++i) {
        double curr_s = (*path_bound)[i].s;
        // 1. Get the current lane width at current point.
        double curr_lane_left_width = 0.0;
        double curr_lane_right_width = 0.0;
        double offset_to_lane_center = 0.0;
        if (!reference_line.GetLaneWidth(curr_s, &curr_lane_left_width, &curr_lane_right_width)) {
            AWARN << "Failed to get lane width at s = " << curr_s;
            curr_lane_left_width = past_lane_left_width;
            curr_lane_right_width = past_lane_right_width;
        } else {
            reference_line.GetOffsetToMap(curr_s, &offset_to_lane_center);
            curr_lane_left_width += offset_to_lane_center;
            curr_lane_right_width -= offset_to_lane_center;
            past_lane_left_width = curr_lane_left_width;
            past_lane_right_width = curr_lane_right_width;
        }

        // 3. Calculate the proper boundary based on lane-width, ADC's position,
        //    and ADC's velocity.
        double offset_to_map = 0.0;
        reference_line.GetOffsetToMap(curr_s, &offset_to_map);

        double curr_left_bound = 0.0;
        double curr_right_bound = 0.0;
        curr_left_bound = curr_lane_left_width - offset_to_map;
        curr_right_bound = -curr_lane_right_width - offset_to_map;
        // 4. Update the boundary.
        if (!UpdatePathBoundaryWithBuffer(
                    curr_left_bound, curr_right_bound, BoundType::LANE, BoundType::LANE, "", "", &path_bound->at(i))) {
            path_blocked_idx = static_cast<int>(i);
        }
        if (path_blocked_idx != -1) {
            break;
        }
    }

    PathBoundsDeciderUtil::TrimPathBounds(path_blocked_idx, path_bound);

    return true;
}

bool PathBoundsDeciderUtil::GetBoundaryFromRoad(
        const ReferenceLineInfo& reference_line_info,
        const SLState& init_sl_state,
        PathBoundary* const path_bound) {
    // Sanity checks.
    CHECK_NOTNULL(path_bound);
    ACHECK(!path_bound->empty());
    const ReferenceLine& reference_line = reference_line_info.reference_line();
    double adc_lane_width = GetADCLaneWidth(reference_line, init_sl_state.first[0]);
    // Go through every point, update the boudnary based on the road boundary.
    double past_road_left_width = adc_lane_width / 2.0;
    double past_road_right_width = adc_lane_width / 2.0;
    int path_blocked_idx = -1;
    for (size_t i = 0; i < path_bound->size(); ++i) {
        // 1. Get road boundary.
        double curr_s = (*path_bound)[i].s;
        double curr_road_left_width = 0.0;
        double curr_road_right_width = 0.0;
        if (!reference_line.GetRoadWidth(curr_s, &curr_road_left_width, &curr_road_right_width)) {
            AWARN << "Failed to get lane width at s = " << curr_s;
            curr_road_left_width = past_road_left_width;
            curr_road_right_width = past_road_right_width;
        }

        past_road_left_width = curr_road_left_width;
        past_road_right_width = curr_road_right_width;

        double curr_left_bound = curr_road_left_width;
        double curr_right_bound = -curr_road_right_width;
        ADEBUG << "At s = " << curr_s << ", left road bound = " << curr_road_left_width
               << ", right road bound = " << curr_road_right_width;

        // 2. Update into path_bound.
        if (!UpdatePathBoundaryWithBuffer(
                    curr_left_bound, curr_right_bound, BoundType::ROAD, BoundType::ROAD, "", "", &path_bound->at(i))) {
            path_blocked_idx = static_cast<int>(i);
        }
        if (path_blocked_idx != -1) {
            break;
        }
    }
    AINFO << "path_blocked_idx: " << path_blocked_idx;
    TrimPathBounds(path_blocked_idx, path_bound);
    return true;
}

bool PathBoundsDeciderUtil::ExtendBoundaryByADC(
        const ReferenceLineInfo& reference_line_info,
        const SLState& init_sl_state,
        const double extend_buffer,
        PathBoundary* const path_bound) {
    double adc_l_to_lane_center = init_sl_state.second[0];
    static constexpr double kMaxLateralAccelerations = 1.5;

    double ADC_speed_buffer = (init_sl_state.second[1] > 0 ? 1.0 : -1.0) * init_sl_state.second[1]
            * init_sl_state.second[1] / kMaxLateralAccelerations / 2.0;
    double adc_half_width = VehicleConfigHelper::GetConfig().vehicle_param().width() / 2.0;
    double left_bound_adc
            = std::fmax(adc_l_to_lane_center, adc_l_to_lane_center + ADC_speed_buffer) + adc_half_width + extend_buffer;
    double right_bound_adc
            = std::fmin(adc_l_to_lane_center, adc_l_to_lane_center + ADC_speed_buffer) - adc_half_width - extend_buffer;

    static constexpr double kEpsilon = 0.05;
    for (size_t i = 0; i < path_bound->size(); ++i) {
        double road_left_width = std::fabs(left_bound_adc) + kEpsilon;
        double road_right_width = std::fabs(right_bound_adc) + kEpsilon;
        reference_line_info.reference_line().GetRoadWidth((*path_bound)[i].s, &road_left_width, &road_right_width);
        double left_bound_road = road_left_width - adc_half_width;
        double right_bound_road = -road_right_width + adc_half_width;

        if (left_bound_adc > (*path_bound)[i].l_upper.l) {
            (*path_bound)[i].l_upper.l
                    = std::max(std::min(left_bound_adc, left_bound_road), (*path_bound)[i].l_upper.l);
            (*path_bound)[i].l_upper.type = BoundType::ADC;
            (*path_bound)[i].l_upper.id = "adc";
        }
        if (right_bound_adc < (*path_bound)[i].l_lower.l) {
            (*path_bound)[i].l_lower.l
                    = std::min(std::max(right_bound_adc, right_bound_road), (*path_bound)[i].l_lower.l);
            (*path_bound)[i].l_lower.type = BoundType::ADC;
            (*path_bound)[i].l_lower.id = "adc";
        }
    }
    return true;
}

void PathBoundsDeciderUtil::ConvertBoundarySAxisFromLaneCenterToRefLine(
        const ReferenceLineInfo& reference_line_info,
        PathBoundary* const path_bound) {
    const ReferenceLine& reference_line = reference_line_info.reference_line();
    for (size_t i = 0; i < path_bound->size(); ++i) {
        // 1. Get road boundary.
        double curr_s = (*path_bound)[i].s;
        double refline_offset_to_lane_center = 0.0;
        reference_line.GetOffsetToMap(curr_s, &refline_offset_to_lane_center);
        (*path_bound)[i].l_lower.l -= refline_offset_to_lane_center;
        (*path_bound)[i].l_upper.l -= refline_offset_to_lane_center;
    }
}

int PathBoundsDeciderUtil::IsPointWithinPathBound(
        const ReferenceLineInfo& reference_line_info,
        const double x,
        const double y,
        const PathBound& path_bound) {
    common::SLPoint point_sl;
    reference_line_info.reference_line().XYToSL({x, y}, &point_sl);
    if (point_sl.s() > path_bound.back().s
        || point_sl.s() < path_bound.front().s - FLAGS_path_bounds_decider_resolution * 2) {
        ADEBUG << "Longitudinally outside the boundary.";
        return -1;
    }
    int idx_after = 0;
    while (idx_after < static_cast<int>(path_bound.size()) && path_bound[idx_after].s < point_sl.s()) {
        ++idx_after;
    }
    ADEBUG << "The idx_after = " << idx_after;
    ADEBUG << "The boundary is: " << "[" << path_bound[idx_after].l_lower.l << ", " << path_bound[idx_after].l_upper.l
           << "].";
    ADEBUG << "The point is at: " << point_sl.l();
    int idx_before = idx_after - 1;
    if (path_bound[idx_before].l_lower.l <= point_sl.l() && path_bound[idx_before].l_upper.l >= point_sl.l()
        && path_bound[idx_after].l_lower.l <= point_sl.l() && path_bound[idx_after].l_upper.l >= point_sl.l()) {
        return idx_after;
    }
    ADEBUG << "Laterally outside the boundary.";
    return -1;
}

bool PathBoundsDeciderUtil::RelaxBoundaryPoint(
        PathBoundPoint* const path_bound_point,
        bool is_left,
        double init_l,
        double heading,
        double delta_s,
        double init_frenet_kappa,
        double min_radius) {
    bool is_success = false;
    double protective_restrict = 0.0;
    double relax_constraint = 0.0;
    double radius = 1.0 / std::fabs(init_frenet_kappa);
    double old_buffer = FLAGS_obstacle_lat_buffer;
    double new_buffer = std::max(FLAGS_ego_front_slack_buffer, FLAGS_nonstatic_obstacle_nudge_l_buffer);
    if (is_left) {
        if (init_frenet_kappa > 0 && heading < 0) {
            is_success = util::left_arc_bound_with_heading_with_reverse_kappa(
                    delta_s, min_radius, heading, init_frenet_kappa, &protective_restrict);
        } else {
            is_success = util::left_arc_bound_with_heading(delta_s, radius, heading, &protective_restrict);
        }

        relax_constraint = std::max(path_bound_point->l_upper.l, init_l + protective_restrict);
        AINFO << "init_pt_l: " << init_l << ", left_bound: " << path_bound_point->l_upper.l << ",  diff s: " << delta_s
              << ", radius: " << radius << ", protective_restrict: " << protective_restrict
              << ", left_obs_constraint: " << relax_constraint;

        if (path_bound_point->is_nudge_bound[LEFT_INDEX]) {
            old_buffer = std::max(FLAGS_obstacle_lat_buffer, FLAGS_static_obstacle_nudge_l_buffer);
        }

        relax_constraint = std::min(path_bound_point->l_upper.l + old_buffer - new_buffer, relax_constraint);
        AINFO << "left_obs_constraint: " << relax_constraint;
        path_bound_point->l_upper.l = relax_constraint;
    } else {
        if (init_frenet_kappa < 0 && heading > 0) {
            is_success = util::right_arc_bound_with_heading_with_reverse_kappa(
                    delta_s, min_radius, heading, init_frenet_kappa, &protective_restrict);
        } else {
            is_success = util::right_arc_bound_with_heading(delta_s, radius, heading, &protective_restrict);
        }
        relax_constraint = std::min(path_bound_point->l_lower.l, init_l + protective_restrict);
        AINFO << "init_pt_l: " << init_l << ", right_bound: " << path_bound_point->l_lower.l << ",  diff s: " << delta_s
              << ", radius: " << radius << ", protective_restrict: " << protective_restrict
              << ", right_obs_constraint: " << relax_constraint;

        if (path_bound_point->is_nudge_bound[RIGHT_INDEX]) {
            old_buffer = std::max(FLAGS_obstacle_lat_buffer, FLAGS_static_obstacle_nudge_l_buffer);
        }

        relax_constraint = std::max(path_bound_point->l_lower.l - old_buffer + new_buffer, relax_constraint);
        AINFO << "right_obs_constraint: " << relax_constraint;
        path_bound_point->l_lower.l = relax_constraint;
    }
    return is_success;
}

bool PathBoundsDeciderUtil::RelaxEgoPathBoundary(PathBoundary* const path_boundary, const SLState& init_sl_state) {
    if (path_boundary->size() < 2) {
        AINFO << "path_boundary size = 0, return.";
        return false;
    }
    const auto& veh_param = common::VehicleConfigHelper::GetConfig().vehicle_param();
    double min_radius = std::max(
            veh_param.min_turn_radius(),
            std::tan(veh_param.max_steer_angle() / veh_param.steer_ratio()) / veh_param.wheel_base());

    double init_frenet_kappa = init_sl_state.second[2] / std::pow(1 + std::pow(init_sl_state.second[1], 2), 1.5);
    if (init_frenet_kappa < 0) {
        init_frenet_kappa = std::min(-1.0 / (min_radius + FLAGS_relax_ego_radius_buffer), init_frenet_kappa);
    } else {
        init_frenet_kappa = std::max(1.0 / (min_radius + FLAGS_relax_ego_radius_buffer), init_frenet_kappa);
    }

    const auto& init_pt = path_boundary->at(0);
    double init_frenet_heading = common::math::Vec2d(1.0, init_sl_state.second[1]).Angle();
    double init_pt_l = init_sl_state.second[0];
    bool left_calculate_success = true;
    bool right_calculate_success = true;
    for (size_t i = 1; i < path_boundary->size(); ++i) {
        auto& left_bound = path_boundary->at(i).l_upper;
        auto& right_bound = path_boundary->at(i).l_lower;
        double delta_s = path_boundary->at(i).s - init_pt.s;
        if (delta_s > FLAGS_relax_path_s_threshold) {
            left_calculate_success = false;
            right_calculate_success = false;
            break;
        }
        if (left_calculate_success
            && (left_bound.type == BoundType::OBSTACLE || path_boundary->at(i).is_nudge_bound[LEFT_INDEX])) {
            left_calculate_success = RelaxBoundaryPoint(
                    &path_boundary->at(i),
                    true,
                    init_pt_l,
                    init_frenet_heading,
                    delta_s,
                    init_frenet_kappa,
                    min_radius);
        }
        if (right_calculate_success
            && (right_bound.type == BoundType::OBSTACLE || path_boundary->at(i).is_nudge_bound[RIGHT_INDEX])) {
            right_calculate_success = RelaxBoundaryPoint(
                    &path_boundary->at(i),
                    false,
                    init_pt_l,
                    init_frenet_heading,
                    delta_s,
                    init_frenet_kappa,
                    min_radius);
        }
        if (!left_calculate_success && !right_calculate_success) {
            break;
        }
    }
    return true;
}

bool PathBoundsDeciderUtil::RelaxObsCornerBoundary(PathBoundary* const path_boundary, const SLState& init_sl_state) {
    if (path_boundary->size() < 2) {
        AINFO << "path_boundary size = 0, return.";
        return false;
    }
    const auto& veh_param = common::VehicleConfigHelper::GetConfig().vehicle_param();
    double min_radius = std::max(
            veh_param.min_turn_radius(),
            std::tan(veh_param.max_steer_angle() / veh_param.steer_ratio()) / veh_param.wheel_base());

    double init_frenet_kappa
            = std::fabs(init_sl_state.second[2] / std::pow(1 + std::pow(init_sl_state.second[1], 2), 1.5));
    if (init_frenet_kappa < 0) {
        init_frenet_kappa = std::min(-1.0 / (min_radius + FLAGS_relax_ego_radius_buffer), init_frenet_kappa);
    } else {
        init_frenet_kappa = std::max(1.0 / (min_radius + FLAGS_relax_ego_radius_buffer), init_frenet_kappa);
    }
    double kappa_radius = 1.0 / std::fabs(init_frenet_kappa);

    const auto& init_pt = path_boundary->at(0);
    double init_frenet_heading = common::math::Vec2d(1.0, init_sl_state.second[1]).Angle();
    double init_pt_l = init_sl_state.second[0];
    bool left_calculate_success = true;
    bool right_calculate_success = true;
    double new_buffer = std::max(FLAGS_ego_front_slack_buffer, FLAGS_nonstatic_obstacle_nudge_l_buffer);
    for (auto& extra_path_bound : *(path_boundary->mutable_extra_path_bound())) {
        double delta_s = extra_path_bound.rear_axle_s - init_pt.s;
        if (delta_s > FLAGS_relax_path_s_threshold) {
            break;
        }

        // calculate the left side
        if (left_calculate_success) {
            double left_protective_restrict = 0.0;
            if (init_frenet_kappa > 0 && init_frenet_heading < 0) {
                left_calculate_success = util::left_arc_bound_with_heading_with_reverse_kappa(
                        delta_s, min_radius, init_frenet_heading, init_frenet_kappa, &left_protective_restrict);
            } else {
                left_calculate_success = util::left_arc_bound_with_heading(
                        delta_s, kappa_radius, init_frenet_heading, &left_protective_restrict);
            }

            double left_obs_constraint = std::max(extra_path_bound.upper_bound, init_pt_l + left_protective_restrict);
            AINFO << "extra_path_bound, init_pt_l: " << init_pt_l << ", left_bound: " << extra_path_bound.upper_bound
                  << ",  diff s: " << delta_s << ", min_radius: " << min_radius
                  << ", init_frenet_heading: " << init_frenet_heading
                  << ", protective_restrict: " << left_protective_restrict
                  << ", left_obs_constraint: " << left_obs_constraint;
            left_obs_constraint = std::min(
                    extra_path_bound.upper_bound + FLAGS_obstacle_lat_buffer - new_buffer, left_obs_constraint);
            AINFO << "extra_path_bound left_obs_constraint: " << left_obs_constraint;
            extra_path_bound.upper_bound = left_obs_constraint;
        }

        if (right_calculate_success) {
            // calculate the right side
            double right_protective_restrict = 0.0;
            if (init_frenet_kappa < 0 && init_frenet_heading > 0) {
                right_calculate_success = util::right_arc_bound_with_heading_with_reverse_kappa(
                        delta_s, min_radius, init_frenet_heading, init_frenet_kappa, &right_protective_restrict);
            } else {
                right_calculate_success = util::right_arc_bound_with_heading(
                        delta_s, kappa_radius, init_frenet_heading, &right_protective_restrict);
            }

            double right_obs_constraint = std::min(extra_path_bound.lower_bound, init_pt_l + right_protective_restrict);
            AINFO << "extra_path_bound, init_pt_l: " << init_pt_l << ", right_bound: " << extra_path_bound.lower_bound
                  << ",  diff s: " << delta_s << ", min_radius: " << min_radius
                  << ", init_frenet_heading: " << init_frenet_heading
                  << ", protective_restrict: " << right_protective_restrict
                  << ", right_obs_constraint: " << right_obs_constraint;
            right_obs_constraint = std::max(
                    extra_path_bound.lower_bound - FLAGS_obstacle_lat_buffer + new_buffer, right_obs_constraint);
            AINFO << "extra_path_bound, right_obs_constraint: " << right_obs_constraint;
            extra_path_bound.lower_bound = right_obs_constraint;
        }

        if (!left_calculate_success && !right_calculate_success) {
            break;
        }
    }
    return true;
}

bool PathBoundsDeciderUtil::UpdateBlockInfoWithObsCornerBoundary(
        PathBoundary* const path_boundary,
        std::string* const blocked_id) {
    if (path_boundary->extra_path_bound().blocked_id.empty()) {
        AINFO << "UpdateBlockInfoWithObsCornerBoundary, block id empty";
        return true;
    }
    auto* extra_path_bound = path_boundary->mutable_extra_path_bound();
    size_t path_boundary_block_index = extra_path_bound->block_right_index;

    // trim path boundary width corner constraints block obstacle id
    *blocked_id = extra_path_bound->blocked_id;
    TrimPathBounds(path_boundary_block_index, path_boundary);
    AINFO << "update block id: " << *blocked_id << ", path_boundary size: " << path_boundary->size();

    if (path_boundary->size() < 1) {
        extra_path_bound->clear();
        AERROR << "UpdateBlockInfoWithObsCornerBoundary, new_path_index < 1";
        return false;
    }

    size_t new_path_index = path_boundary->size() - 1;
    while (extra_path_bound->size() > 0
           && (extra_path_bound->back().id == *blocked_id || extra_path_bound->back().right_index > new_path_index)) {
        AINFO << "remove extra_path_bound: s " << extra_path_bound->back().rear_axle_s << ", index ["
              << extra_path_bound->back().left_index << ", " << extra_path_bound->back().right_index << "]";
        extra_path_bound->pop_back();
    }
    return false;
}

bool PathBoundsDeciderUtil::AddExtraPathBound(
        const std::vector<SLPolygon>& sl_polygons,
        PathBoundary* const path_boundary,
        const SLState& init_sl_state,
        std::string* const blocked_id) {
    RelaxEgoPathBoundary(path_boundary, init_sl_state);
    if (FLAGS_enable_corner_constraint) {
        AddCornerBounds(sl_polygons, path_boundary);
        RelaxObsCornerBoundary(path_boundary, init_sl_state);
        UpdateBlockInfoWithObsCornerBoundary(path_boundary, blocked_id);
    }
    if (FLAGS_enable_adc_vertex_constraint) {
        AddAdcVertexBounds(path_boundary);
    }
    return true;
}

}  // namespace planning
}  // namespace apollo

#include "miku_path_bounds.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <utility>

namespace miku_cpp_path {
namespace {

constexpr double kGapEpsilon = 1e-6;
constexpr int kTopK = 3;

struct Projection {
  std::size_t obstacle_index;
  double s_minus;
  double s_plus;
  double u;
  double v;
  double delta;
};

struct Band {
  int split_index;
  double lower;
  double upper;
  double gap;
};

struct Decision {
  std::vector<Projection> group;
  std::vector<Projection> ordered;
  std::vector<Band> bands;
  int split_index = -1;
  double gap = 0.0;
};

struct SpatialPlan {
  double cost;
  std::vector<int> splits;
};

double TypeScore(const std::string& type) {
  if (type == "ped" || type == "bike") return 1.0;
  if (type == "vehicle") return 0.7;
  if (type == "static") return 0.3;
  if (type == "cone") return 0.15;
  return 0.5;
}

double Centre(const Band& band) { return 0.5 * (band.lower + band.upper); }

std::vector<Projection> OrderedByInterval(std::vector<Projection> projections) {
  std::stable_sort(projections.begin(), projections.end(),
                   [](const Projection& a, const Projection& b) {
                     if (a.u != b.u) return a.u < b.u;
                     if (a.v != b.v) return a.v > b.v;
                     return a.obstacle_index < b.obstacle_index;
                   });
  return projections;
}

std::vector<Band> Bands(const std::vector<Projection>& ordered,
                        double road_lower, double road_upper) {
  std::vector<Band> bands;
  bands.reserve(ordered.size() + 1);
  double prefix_max_v = road_lower;
  for (std::size_t split = 0; split <= ordered.size(); ++split) {
    const double upper = split == ordered.size()
                             ? road_upper
                             : std::min(road_upper, ordered[split].u);
    bands.push_back({static_cast<int>(split), prefix_max_v, upper,
                     upper - prefix_max_v});
    if (split < ordered.size()) {
      prefix_max_v = std::max(prefix_max_v, ordered[split].v);
    }
  }
  return bands;
}

Band MaxGap(const std::vector<Projection>& ordered, double lower, double upper) {
  const auto bands = Bands(ordered, lower, upper);
  return *std::max_element(bands.begin(), bands.end(),
                           [](const Band& a, const Band& b) {
                             return a.gap < b.gap;
                           });
}

std::vector<Band> RankedBands(const std::vector<Projection>& ordered,
                              double lower, double upper) {
  auto bands = Bands(ordered, lower, upper);
  const double road_centre = 0.5 * (lower + upper);
  std::sort(bands.begin(), bands.end(), [road_centre](const Band& a, const Band& b) {
    if (a.gap != b.gap) return a.gap > b.gap;
    const double da = std::abs(Centre(a) - road_centre);
    const double db = std::abs(Centre(b) - road_centre);
    if (da != db) return da < db;
    return a.split_index < b.split_index;
  });
  if (bands.size() > kTopK) bands.resize(kTopK);
  return bands;
}

bool BetterPlan(const SpatialPlan& a, const SpatialPlan& b) {
  if (a.cost != b.cost) return a.cost < b.cost;
  return a.splits < b.splits;
}

std::vector<SpatialPlan> SpatialHomotopies(
    const std::vector<std::vector<Band>>& layers, double initial_lateral) {
  if (layers.empty()) return {{{0.0, {}}}};
  std::vector<std::vector<Band>> feasible;
  feasible.reserve(layers.size());
  for (const auto& layer : layers) {
    feasible.emplace_back();
    for (const auto& band : layer) {
      if (band.gap >= kGapEpsilon) feasible.back().push_back(band);
    }
    if (feasible.back().empty()) return {};
  }

  std::vector<std::vector<SpatialPlan>> states;
  for (std::size_t i = 0; i < feasible.front().size(); ++i) {
    const auto& band = feasible.front()[i];
    states.push_back({{-band.gap + 0.05 * std::abs(Centre(band) - initial_lateral),
                       {band.split_index}}});
  }
  for (std::size_t layer_index = 1; layer_index < feasible.size(); ++layer_index) {
    std::vector<std::vector<SpatialPlan>> next;
    for (std::size_t i = 0; i < feasible[layer_index].size(); ++i) {
      const auto& band = feasible[layer_index][i];
      std::vector<SpatialPlan> expanded;
      for (std::size_t previous_index = 0; previous_index < states.size();
           ++previous_index) {
        for (const auto& prefix : states[previous_index]) {
          SpatialPlan candidate = prefix;
          candidate.cost += -band.gap +
                            0.05 * std::abs(Centre(band) -
                                            Centre(feasible[layer_index - 1][previous_index]));
          candidate.splits.push_back(band.split_index);
          expanded.push_back(std::move(candidate));
        }
      }
      std::sort(expanded.begin(), expanded.end(), BetterPlan);
      if (expanded.size() > kTopK) expanded.resize(kTopK);
      next.push_back(std::move(expanded));
    }
    states = std::move(next);
  }
  std::vector<SpatialPlan> complete;
  for (auto& terminal : states) {
    complete.insert(complete.end(), std::make_move_iterator(terminal.begin()),
                    std::make_move_iterator(terminal.end()));
  }
  std::sort(complete.begin(), complete.end(), BetterPlan);
  if (complete.size() > kTopK) complete.resize(kTopK);
  return complete;
}

}  // namespace

double ComputeThreat(std::size_t obstacle_index, const Scenario& scenario) {
  const auto& obs = scenario.obstacles.at(obstacle_index);
  const auto& ego = scenario.ego;
  const double ds = obs.s0 - ego.s0;
  const double rel_v = ego.v0 - obs.vs;
  double ttc = 0.0;
  if (ds > 0.0 && rel_v > 1e-3) {
    const double arrival = ds / rel_v;
    if (arrival <= 2.0) {
      ttc = 1.0;
    } else if (arrival < 7.0) {
      ttc = (7.0 - arrival) / 5.0;
    }
  }
  const double overlap = std::max(
      0.0, std::min(obs.l0 + obs.width / 2.0, ego.l0 + ego.width / 2.0) -
               std::max(obs.l0 - obs.width / 2.0, ego.l0 - ego.width / 2.0));
  const double lateral = std::min(1.0, overlap / std::max(0.1, std::min(obs.width, ego.width)));
  const double velocity = 1.0 / (1.0 + std::exp(-5.0 * rel_v / 12.0));
  double interaction = 0.0;
  for (std::size_t i = 0; i < scenario.obstacles.size(); ++i) {
    if (i == obstacle_index) continue;
    const auto& other = scenario.obstacles[i];
    const double distance = std::hypot(obs.s0 - other.s0, obs.l0 - other.l0);
    if (distance < 10.0) interaction += (10.0 - distance) / 10.0;
  }
  if (scenario.obstacles.size() > 1) {
    interaction = std::min(1.0, interaction / (scenario.obstacles.size() - 1));
  }
  return 0.30 * ttc + 0.20 * lateral + 0.15 * velocity +
         0.10 * TypeScore(obs.type) + 0.25 * interaction;
}

double ComputeDelta(std::size_t obstacle_index, const Scenario& scenario) {
  return scenario.delta_min +
         (scenario.delta_max - scenario.delta_min) *
             ComputeThreat(obstacle_index, scenario);
}

double ArrivalTime(double station, const Scenario& scenario) {
  const auto& ego = scenario.ego;
  const double ds = station - ego.s0;
  if (ds < 0.0) return 0.0;
  if (std::abs(ego.a0) < 1e-3) return ds / std::max(ego.v0, 1e-3);
  const double disc = ego.v0 * ego.v0 + 2.0 * ego.a0 * ds;
  if (disc < 0.0) return 1e6;
  return (-ego.v0 + std::sqrt(disc)) / ego.a0;
}

PathResult PathBounds(const Scenario& scenario, int candidate_rank,
                      const std::function<double(double)>& tau_fn) {
  if (candidate_rank < 0) throw std::invalid_argument("negative candidate_rank");
  const auto& ego = scenario.ego;
  const double eff_min = scenario.l_road_min -
      ((scenario.lane_borrow == "right" || scenario.lane_borrow == "both")
           ? scenario.lane_width : 0.0);
  const double eff_max = scenario.l_road_max +
      ((scenario.lane_borrow == "left" || scenario.lane_borrow == "both")
           ? scenario.lane_width : 0.0);
  const double road_min = eff_min + scenario.delta_min + ego.width / 2.0;
  const double road_max = eff_max - scenario.delta_min - ego.width / 2.0;
  const auto tau = [&](double station) {
    return tau_fn ? tau_fn(station) : ArrivalTime(station, scenario);
  };

  PathResult result;
  for (std::size_t i = 0; 0.5 * i <= scenario.s_max + 0.01; ++i) {
    result.stations.push_back(0.5 * i);
  }
  result.lower.assign(result.stations.size(), road_min);
  result.upper.assign(result.stations.size(), road_max);

  std::vector<Projection> projected;
  projected.reserve(scenario.obstacles.size());
  for (std::size_t index = 0; index < scenario.obstacles.size(); ++index) {
    const auto& obs = scenario.obstacles[index];
    const double t = obs.is_static ? 0.0 : tau(obs.s0 - obs.length / 2.0);
    const double s = obs.s0 + obs.vs * t;
    const double lateral = obs.l0 + obs.vl * t;
    const double delta = ComputeDelta(index, scenario);
    const double buffer = ego.width / 2.0 + delta;
    projected.push_back({index, s - obs.length / 2.0, s + obs.length / 2.0,
                         lateral - obs.width / 2.0 - buffer,
                         lateral + obs.width / 2.0 + buffer, delta});
  }
  std::stable_sort(projected.begin(), projected.end(),
                   [](const Projection& a, const Projection& b) {
                     return a.s_minus < b.s_minus;
                   });

  std::vector<Decision> decisions;
  double s_max_run = -std::numeric_limits<double>::infinity();
  for (const auto& projection : projected) {
    if (decisions.empty() || projection.s_minus > s_max_run) {
      decisions.emplace_back();
      s_max_run = projection.s_plus;
    } else {
      s_max_run = std::max(s_max_run, projection.s_plus);
    }
    decisions.back().group.push_back(projection);
  }

  for (auto& decision : decisions) {
    decision.gap = road_max - road_min;
    std::vector<Projection> active;
    for (const auto& projection : decision.group) {
      if (!(projection.u < road_max && projection.v > road_min)) continue;
      const auto& obs = scenario.obstacles[projection.obstacle_index];
      if (!obs.is_static && std::abs(obs.vl) >= 0.2 && std::abs(obs.vs) <= 1.0) {
        continue;  // The frozen C5 path delegates localized crossing to speed.
      }
      active.push_back(projection);
    }
    if (active.empty()) continue;
    decision.ordered = OrderedByInterval(active);
    if (MaxGap(decision.ordered, road_min, road_max).gap < kGapEpsilon) {
      active.erase(std::remove_if(active.begin(), active.end(),
                                  [&](const Projection& projection) {
                                    return !scenario.obstacles[projection.obstacle_index].is_static;
                                  }), active.end());
      if (active.empty()) {
        decision.ordered.clear();
        continue;
      }
      decision.ordered = OrderedByInterval(active);
    }
    decision.bands = RankedBands(decision.ordered, road_min, road_max);
    const auto& selected = decision.bands[std::min(
        static_cast<std::size_t>(candidate_rank), decision.bands.size() - 1)];
    decision.split_index = selected.split_index;
    decision.gap = selected.gap;
  }

  std::vector<std::vector<Band>> layers;
  for (const auto& decision : decisions) {
    if (!decision.bands.empty()) layers.push_back(decision.bands);
  }
  if (!layers.empty()) {
    const auto plans = SpatialHomotopies(layers, ego.l0);
    result.spatial_candidate_count = plans.size();
    if (!plans.empty()) {
      const auto& plan = plans[std::min(static_cast<std::size_t>(candidate_rank), plans.size() - 1)];
      std::size_t layer = 0;
      for (auto& decision : decisions) {
        if (decision.bands.empty()) continue;
        decision.split_index = plan.splits[layer];
        const auto selected = std::find_if(
            decision.bands.begin(), decision.bands.end(),
            [&](const Band& band) { return band.split_index == decision.split_index; });
        decision.gap = selected->gap;
        ++layer;
      }
    }
  }

  for (const auto& decision : decisions) {
    result.groups.push_back({decision.split_index, decision.gap,
                             decision.ordered.size()});
    if (decision.split_index < 0) continue;
    double s_lo = std::numeric_limits<double>::infinity();
    double s_hi = -std::numeric_limits<double>::infinity();
    for (const auto& projection : decision.group) {
      s_lo = std::min(s_lo, projection.s_minus);
      s_hi = std::max(s_hi, projection.s_plus);
    }
    s_lo -= ego.length / 2.0;
    s_hi += ego.length / 2.0;
    for (std::size_t i = 0; i < result.stations.size(); ++i) {
      const double station = result.stations[i];
      if (!(s_lo <= station && station <= s_hi)) continue;
      const double t = tau(station);
      double lower = road_min;
      double upper = road_max;
      bool occupied = false;
      for (std::size_t index = 0; index < decision.ordered.size(); ++index) {
        const auto& projected_obs = decision.ordered[index];
        const auto& obs = scenario.obstacles[projected_obs.obstacle_index];
        const double t_obs = obs.is_static ? 0.0 : t;
        const double s = obs.s0 + obs.vs * t_obs;
        if (!(s - obs.length / 2.0 - ego.length / 2.0 <= station &&
              station <= s + obs.length / 2.0 + ego.length / 2.0)) continue;
        occupied = true;
        const double lateral = obs.l0 + obs.vl * t_obs;
        const double buffer = ego.width / 2.0 + projected_obs.delta;
        if (static_cast<int>(index) < decision.split_index) {
          lower = std::max(lower, lateral + obs.width / 2.0 + buffer);
        } else {
          upper = std::min(upper, lateral - obs.width / 2.0 - buffer);
        }
      }
      if (occupied) {
        result.lower[i] = std::max(result.lower[i], lower);
        result.upper[i] = std::min(result.upper[i], upper);
      }
    }
  }

  if (!result.stations.empty()) {
    std::size_t start = 0;
    for (std::size_t i = 1; i < result.stations.size(); ++i) {
      if (std::abs(result.stations[i] - ego.s0) <
          std::abs(result.stations[start] - ego.s0)) start = i;
    }
    for (std::size_t i = 0; i <= start; ++i) {
      result.lower[i] = ego.l0;
      result.upper[i] = ego.l0;
    }
  }
  for (std::size_t i = 0; i < result.stations.size(); ++i) {
    if (result.lower[i] > result.upper[i]) {
      result.blocked_index = static_cast<int>(i);
      const double previous = i > 0
          ? 0.5 * (result.lower[i - 1] + result.upper[i - 1]) : ego.l0;
      for (std::size_t j = i; j < result.stations.size(); ++j) {
        result.lower[j] = previous;
        result.upper[j] = previous;
      }
      break;
    }
  }
  return result;
}

}  // namespace miku_cpp_path

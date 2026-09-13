#include "speed_stage.h"

#include <osqp/osqp.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <map>
#include <memory>
#include <numeric>
#include <stdexcept>
#include <tuple>

namespace miku_speed {
namespace {

std::vector<double> linspace(double last, int size) {
  std::vector<double> result(size);
  for (int j = 0; j < size; ++j) {
    result[j] = j == size - 1 ? last : last * j / (size - 1);
  }
  return result;
}

double interp(double x, const std::vector<double>& xs,
              const std::vector<double>& ys) {
  if (x <= xs.front()) return ys.front();
  if (x >= xs.back()) return ys.back();
  const auto it = std::upper_bound(xs.begin(), xs.end(), x);
  const size_t hi = it - xs.begin();
  const size_t lo = hi - 1;
  return ys[lo] + (x - xs[lo]) * (ys[hi] - ys[lo]) / (xs[hi] - xs[lo]);
}

double arrival_time(double s, const Scenario& scn) {
  const double ds = s - scn.ego.s0;
  if (ds < 0.0) return 0.0;
  if (std::abs(scn.ego.a0) < 1e-3) return ds / std::max(scn.ego.v0, 1e-3);
  const double disc = scn.ego.v0 * scn.ego.v0 + 2 * scn.ego.a0 * ds;
  return disc < 0.0 ? 1e6
                    : (-scn.ego.v0 + std::sqrt(disc)) / scn.ego.a0;
}

std::vector<TimeWindow> safe_windows(const std::vector<TimeWindow>& occupied,
                                     double horizon, double guard) {
  std::vector<TimeWindow> blocked;
  for (const auto& item : occupied) {
    const double start = std::max(0.0, item.start - guard);
    const double end = std::min(horizon, item.end + guard);
    if (start <= end) blocked.push_back({start, end});
  }
  std::sort(blocked.begin(), blocked.end(), [](const auto& a, const auto& b) {
    return std::tie(a.start, a.end) < std::tie(b.start, b.end);
  });
  if (blocked.empty()) return {{0.0, horizon}};
  std::vector<TimeWindow> merged;
  for (const auto& item : blocked) {
    if (merged.empty() || item.start > merged.back().end) {
      merged.push_back(item);
    } else {
      merged.back().end = std::max(merged.back().end, item.end);
    }
  }
  std::vector<TimeWindow> safe;
  double cursor = 0.0;
  for (const auto& item : merged) {
    if (cursor < item.start) safe.push_back({cursor, item.start});
    cursor = std::max(cursor, item.end);
  }
  if (cursor < horizon) safe.push_back({cursor, horizon});
  return safe;
}

struct Conflict {
  size_t boundary_index;
  std::string graph_name, boundary_name;
  double station, s_lo, s_hi, nominal, earliest;
  std::vector<TimeWindow> safe;
};

struct Choice {
  size_t boundary_index;
  int window_index;
  std::string label;
  TimeWindow window;
  double target;
};

struct Plan {
  double cost = 0.0, station = 0.0, time = 0.0;
  int component = -1;
  std::vector<Choice> choices;
};

std::vector<Plan> temporal_plans(const std::vector<Conflict>& conflicts,
                                 const Scenario& scn,
                                 const BoundsOptions& options) {
  std::vector<const Conflict*> ordered;
  for (const auto& conflict : conflicts) ordered.push_back(&conflict);
  std::sort(ordered.begin(), ordered.end(), [](const auto* a, const auto* b) {
    return std::tie(a->station, a->graph_name) <
           std::tie(b->station, b->graph_name);
  });
  std::vector<Plan> beam(1);
  beam.front().station = scn.ego.s0;
  for (const auto* point : ordered) {
    std::vector<Plan> expanded;
    for (const auto& plan : beam) {
      if (point->station < plan.station - 1e-9) continue;
      const double travel_floor = plan.time + (point->station - plan.station) / 13.0;
      for (size_t j = 0; j < point->safe.size(); ++j) {
        const auto& w = point->safe[j];
        std::string label;
        if (point->safe.size() == 1) {
          label = w.start <= 1e-9 ? "before_or_free" : "yield_after";
        } else if (j == 0 && w.start <= 1e-9) {
          label = "pass_before";
        } else if (j == point->safe.size() - 1) {
          label = "yield_after";
        } else {
          label = "intermediate_" + std::to_string(j);
        }
        const double nominal_projection =
            std::clamp(point->nominal, w.start, w.end);
        const double target = std::max({travel_floor, point->earliest,
                                        w.start, nominal_projection});
        if (target > w.end + 1e-9) continue;
        double increment = std::abs(target - point->nominal);
        if (plan.component >= 0 && static_cast<int>(j) != plan.component)
          increment += 0.10;
        const auto preferred = options.preferred_homotopy.find(
            point->boundary_name);
        if (preferred != options.preferred_homotopy.end() &&
            preferred->second != label) increment += 0.20;
        Plan next = plan;
        next.cost += increment;
        next.station = point->station;
        next.time = target;
        next.component = static_cast<int>(j);
        next.choices.push_back({point->boundary_index,
                                static_cast<int>(j), label, w, target});
        expanded.push_back(std::move(next));
      }
    }
    std::stable_sort(expanded.begin(), expanded.end(),
                     [](const auto& a, const auto& b) {
      if (a.cost != b.cost) return a.cost < b.cost;
      if (a.time != b.time) return a.time < b.time;
      for (size_t i = 0; i < a.choices.size(); ++i) {
        if (a.choices[i].window_index != b.choices[i].window_index)
          return a.choices[i].window_index < b.choices[i].window_index;
      }
      return false;
    });
    if (expanded.size() > 8) expanded.resize(8);
    beam = std::move(expanded);
    if (beam.empty()) break;
  }
  return beam;
}

struct Matrix {
  int rows, cols;
  std::vector<std::map<OSQPInt, OSQPFloat>> columns;
  explicit Matrix(int r, int c) : rows(r), cols(c), columns(c) {}
  void add(int r, int c, double value) { columns.at(c)[r] += value; }
};

struct CSC {
  std::vector<OSQPInt> p, i;
  std::vector<OSQPFloat> x;
  OSQPCscMatrix view{};
  explicit CSC(const Matrix& mat) {
    p.push_back(0);
    for (const auto& col : mat.columns) {
      for (const auto& [row, value] : col) {
        if (value == 0.0) continue;
        i.push_back(row);
        x.push_back(value);
      }
      p.push_back(static_cast<OSQPInt>(i.size()));
    }
    view = {mat.rows, mat.cols, p.data(), i.data(), x.data(),
            static_cast<OSQPInt>(x.size()), -1, 0};
  }
};

}  // namespace

std::vector<STBoundary> st_boundary_mapper(const Scenario& scn,
    const std::vector<double>& path_stations,
    const std::vector<double>& path_offsets, bool robust_prediction) {
  if (path_stations.empty() || path_stations.size() != path_offsets.size() ||
      !std::is_sorted(path_stations.begin(), path_stations.end()))
    throw std::invalid_argument("invalid path samples");
  std::vector<STBoundary> boundaries;
  const auto& ego = scn.ego;
  for (const auto& obs : scn.obstacles) {
    STBoundary boundary{obs.name, {}, obs.is_static, obs.vs, obs.vl};
    for (int k = 0; k * 0.05 <= scn.t_max + 0.01; ++k) {
      const double t = k * 0.05;
      const double os = obs.s0 + obs.vs * t;
      const double ol = obs.l0 + obs.vl * t;
      if (os < 0.0 || os > scn.s_max) continue;
      const double longitudinal_half_extent = (obs.L + ego.L) / 2.0;
      const double envelope_lo = std::max(path_stations.front(),
                                           os - longitudinal_half_extent);
      const double envelope_hi = std::min(path_stations.back(),
                                           os + longitudinal_half_extent);
      double min_l = std::min(interp(envelope_lo, path_stations, path_offsets),
                              interp(envelope_hi, path_stations, path_offsets));
      double max_l = std::max(interp(envelope_lo, path_stations, path_offsets),
                              interp(envelope_hi, path_stations, path_offsets));
      for (size_t j = 0; j < path_stations.size(); ++j) {
        if (path_stations[j] >= envelope_lo && path_stations[j] <= envelope_hi) {
          min_l = std::min(min_l, path_offsets[j]);
          max_l = std::max(max_l, path_offsets[j]);
        }
      }
      double lateral_uncertainty = 0.0;
      double longitudinal_uncertainty = 0.0;
      if (robust_prediction && !obs.is_static) {
        lateral_uncertainty = obs.uncertainty_l0 + obs.uncertainty_vl * t;
        longitudinal_uncertainty = obs.uncertainty_s0 + obs.uncertainty_vs * t;
      }
      if (!obs.is_static) longitudinal_uncertainty += 0.15;
      if (ol - obs.W / 2 - lateral_uncertainty >= max_l + ego.W / 2 ||
          ol + obs.W / 2 + lateral_uncertainty <= min_l - ego.W / 2) continue;
      const double s_lo = os - obs.L / 2 - ego.L / 2 - longitudinal_uncertainty;
      const double s_hi = os + obs.L / 2 + ego.L / 2 + longitudinal_uncertainty;
      if (s_hi < ego.s0 - 1e-9) continue;
      boundary.intervals.push_back({t, s_lo, s_hi});
    }
    boundaries.push_back(std::move(boundary));
  }
  return boundaries;
}

DPResult speed_dp(const Scenario& scn, const std::vector<STBoundary>& boundaries) {
  constexpr double dt = 0.1, ds = 0.5;
  const int nt = static_cast<int>(scn.t_max / dt) + 1;
  const int ns = static_cast<int>(scn.s_max / ds) + 1;
  if (nt < 2 || ns < 2) throw std::invalid_argument("speed horizon too short");
  DPResult result{linspace(scn.t_max, nt), {}, linspace(scn.s_max, ns),
                  std::vector<std::vector<bool>>(nt, std::vector<bool>(ns))};
  for (const auto& b : boundaries) {
    for (const auto& interval : b.intervals) {
      const int ti = static_cast<int>(std::nearbyint(interval.t / dt));
      if (ti < 0 || ti >= nt) continue;
      const int lo = std::max(0, static_cast<int>(std::floor(interval.s_lo / ds)));
      const int hi = std::min(ns - 1, static_cast<int>(std::ceil(interval.s_hi / ds)));
      for (int si = lo; si <= hi; ++si) result.forbidden[ti][si] = true;
    }
  }
  constexpr double inf = 1e15;
  std::vector<std::vector<double>> cost(nt, std::vector<double>(ns, inf));
  std::vector<std::vector<int>> parent(nt, std::vector<int>(ns, -1));
  const int start = std::clamp(static_cast<int>(std::nearbyint(scn.ego.s0 / ds)),
                               0, ns - 1);
  cost[0][start] = 0.0;
  for (int ti = 0; ti < nt - 1; ++ti) {
    for (int si = 0; si < ns; ++si) {
      if (cost[ti][si] >= inf || result.forbidden[ti][si]) continue;
      const double v_now = parent[ti][si] >= 0
          ? (si - parent[ti][si]) * ds / dt : scn.ego.v0;
      const int high = std::min(ns - 1, si + static_cast<int>(std::ceil(13 * dt / ds)));
      for (int sj = si; sj <= high; ++sj) {
        if (result.forbidden[ti + 1][sj]) continue;
        const double v_eff = (sj - si) * ds / dt;
        if (v_eff < 0.0 || v_eff > 13.001) continue;
        const double a_eff = (v_eff - v_now) / dt;
        if (a_eff < -4.1 || a_eff > 2.1) continue;
        const double step = std::pow(v_eff - scn.ego.v0, 2) +
                            0.5 * std::pow(a_eff, 2);
        const double next_cost = cost[ti][si] + step;
        if (next_cost < cost[ti + 1][sj]) {
          cost[ti + 1][sj] = next_cost;
          parent[ti + 1][sj] = si;
        }
      }
    }
  }
  int best = 0;
  double best_cost = inf;
  for (int j = 0; j < ns; ++j) {
    if (!result.forbidden.back()[j] && cost.back()[j] < best_cost) {
      best_cost = cost.back()[j];
      best = j;
    }
  }
  if (best_cost >= inf) {
    for (int j = 0; j < ns; ++j) {
      if (cost.back()[j] < best_cost) {
        best_cost = cost.back()[j];
        best = j;
      }
    }
  }
  result.s_dp.resize(nt);
  for (int ti = nt - 1; ti >= 0; --ti) {
    result.s_dp[ti] = result.ss[best];
    if (ti > 0 && parent[ti][best] >= 0) best = parent[ti][best];
  }
  return result;
}

STBounds build_st_bounds(const Scenario& scn,
    const std::vector<STBoundary>& boundaries, const DPResult& dp,
    const BoundsOptions& options) {
  if (dp.ts.size() < 2) throw std::invalid_argument("missing speed grid");
  const size_t nt = dp.ts.size();
  const double dt = dp.ts[1] - dp.ts[0];
  STBounds result{std::vector<double>(nt, 1e4), std::vector<double>(nt, 0.0), {}};
  for (const auto& b : boundaries) {
    if (b.is_static && !b.intervals.empty()) {
      double block = std::numeric_limits<double>::infinity();
      for (const auto& interval : b.intervals)
        block = std::min(block, interval.s_lo);
      for (auto& bound : result.upper) bound = std::min(bound, block);
    }
  }
  std::vector<Conflict> conflicts;
  for (size_t bi = 0; bi < boundaries.size(); ++bi) {
    const auto& b = boundaries[bi];
    if (!options.safe_window_mode || b.is_static || b.intervals.empty() ||
        std::abs(b.vl) < 0.2 || std::abs(b.vs) > 1.0) continue;
    std::vector<double> times;
    double s_lo = std::numeric_limits<double>::infinity();
    double s_hi = -std::numeric_limits<double>::infinity();
    for (const auto& item : b.intervals) {
      times.push_back(item.t);
      s_lo = std::min(s_lo, item.s_lo);
      s_hi = std::max(s_hi, item.s_hi);
    }
    std::sort(times.begin(), times.end());
    std::vector<TimeWindow> occupied;
    double enter = times.front(), previous = enter;
    for (size_t j = 1; j < times.size(); ++j) {
      if (times[j] - previous > 0.075) {
        occupied.push_back({enter, previous});
        enter = times[j];
      }
      previous = times[j];
    }
    occupied.push_back({enter, previous});
    const double distance = std::max(s_hi - scn.ego.s0, 0.0);
    const double earliest = distance > 0.0
        ? (-scn.ego.v0 + std::sqrt(scn.ego.v0 * scn.ego.v0 +
                                   4.0 * distance)) / 2.0 : 0.0;
    const double guard = 0.10 + 0.05 * std::min(std::abs(b.vl), 2.0);
    const double station = (s_lo + s_hi) / 2;
    conflicts.push_back({bi, std::to_string(bi) + ":" + b.name, b.name,
                         s_hi, s_lo, s_hi,
                         options.tau_fn ? options.tau_fn(station)
                                        : arrival_time(station, scn),
                         std::min(std::max(earliest, 0.0), scn.t_max),
                         safe_windows(occupied, scn.t_max, guard)});
  }
  const auto plans = temporal_plans(conflicts, scn, options);
  const Plan* selected = plans.empty() ? nullptr :
      &plans[std::min(static_cast<size_t>(std::max(0, options.temporal_plan_rank)),
                       plans.size() - 1)];
  for (size_t bi = 0; bi < boundaries.size(); ++bi) {
    const auto& b = boundaries[bi];
    if (b.is_static || b.intervals.empty()) continue;
    if (!options.safe_window_mode || std::abs(b.vl) < 0.2 ||
        std::abs(b.vs) > 1.0) {
      for (const auto& interval : b.intervals) {
        const int ti = static_cast<int>(std::nearbyint(interval.t / dt));
        if (ti >= 0 && ti < static_cast<int>(nt))
          result.upper[ti] = std::min(result.upper[ti], interval.s_lo);
      }
      continue;
    }
    const auto conflict = std::find_if(conflicts.begin(), conflicts.end(),
        [bi](const auto& item) { return item.boundary_index == bi; });
    if (conflict == conflicts.end()) throw std::logic_error("missing conflict");
    const Choice* choice = nullptr;
    if (selected != nullptr) {
      for (const auto& item : selected->choices) {
        if (item.boundary_index == bi) choice = &item;
      }
    }
    Decision decision;
    decision.name = b.name;
    decision.graph_candidate_count = static_cast<int>(plans.size());
    if (choice == nullptr) {
      decision.status = "stop";
      for (auto& upper : result.upper)
        upper = std::min(upper, conflict->s_lo);
    } else {
      decision.status = "selected";
      decision.window = choice->window;
      decision.target_arrival = choice->target;
      decision.window_index = choice->window_index;
      decision.homotopy_label = choice->label;
      decision.candidate_count = static_cast<int>(conflict->safe.size());
      decision.homotopy_cost = selected->cost;
      decision.temporal_plan_rank = options.temporal_plan_rank;
      if (choice->window.start > 1e-9) {
        for (size_t j = 0; j < nt; ++j) {
          if (dp.ts[j] < choice->window.start)
            result.upper[j] = std::min(result.upper[j], conflict->s_lo - 0.05);
        }
      }
      if (choice->window.end < scn.t_max - 1e-9) {
        for (size_t j = 0; j < nt; ++j) {
          if (dp.ts[j] >= choice->window.end)
            result.lower[j] = std::max(result.lower[j], conflict->s_hi + 0.05);
        }
      }
    }
    result.decisions.push_back(std::move(decision));
  }
  for (const auto& [s_k, tau_k] : options.corridor) {
    for (size_t j = 0; j < nt; ++j) {
      if (dp.ts[j] < tau_k) result.upper[j] = std::min(result.upper[j], s_k);
    }
  }
  return result;
}

QPResult speed_qp(const Scenario& scn, const std::vector<double>& upper,
                  const std::vector<double>& lower,
                  const std::vector<double>& ts) {
  const int K = static_cast<int>(ts.size());
  if (K < 2 || upper.size() != ts.size() || lower.size() != ts.size())
    throw std::invalid_argument("speed QP expects aligned grids of size >= 2");
  const double dt = ts[1] - ts[0];
  if (dt <= 0.0) throw std::invalid_argument("speed grid must be increasing");
  const int n = 3 * K;
  const int equality_count = 2 * (K - 1) + 3;
  const int m = equality_count + n;
  Matrix P(n, n), A(m, n);
  std::vector<OSQPFloat> q(n, 0.0), lb(m), ub(m);
  for (int j = 0; j < K; ++j) {
    P.add(3 * j + 1, 3 * j + 1, 10.0);
    P.add(3 * j + 2, 3 * j + 2, 2.0);
    q[3 * j + 1] -= 10.0 * scn.ego.v0;
  }
  const double c = 200.0 / (dt * dt);
  for (int j = 0; j < K - 1; ++j) {
    P.add(3 * j + 2, 3 * j + 2, c);
    P.add(3 * (j + 1) + 2, 3 * (j + 1) + 2, c);
    P.add(3 * j + 2, 3 * (j + 1) + 2, -c);
  }
  const double target = std::min(upper.back(), scn.s_max - 1.0);
  P.add(3 * (K - 1), 3 * (K - 1), 40.0);
  q[3 * (K - 1)] -= 40.0 * target;
  int r = 0;
  for (int j = 0; j < K - 1; ++j) {
    A.add(r, 3 * (j + 1), 1.0);
    A.add(r, 3 * j, -1.0);
    A.add(r, 3 * j + 1, -dt);
    A.add(r, 3 * j + 2, -0.5 * dt * dt);
    lb[r] = ub[r] = 0.0;
    ++r;
    A.add(r, 3 * (j + 1) + 1, 1.0);
    A.add(r, 3 * j + 1, -1.0);
    A.add(r, 3 * j + 2, -dt);
    lb[r] = ub[r] = 0.0;
    ++r;
  }
  for (const double initial : {scn.ego.s0, scn.ego.v0, scn.ego.a0}) {
    A.add(r, r - 2 * (K - 1), 1.0);
    lb[r] = ub[r] = initial;
    ++r;
  }
  for (int j = 0; j < K; ++j) {
    A.add(equality_count + 3 * j, 3 * j, 1.0);
    A.add(equality_count + 3 * j + 1, 3 * j + 1, 1.0);
    A.add(equality_count + 3 * j + 2, 3 * j + 2, 1.0);
    lb[equality_count + 3 * j] = lower[j];
    ub[equality_count + 3 * j] = std::max(upper[j], lower[j] + 1e-6);
    lb[equality_count + 3 * j + 1] = 0.0;
    ub[equality_count + 3 * j + 1] = 13.0;
    lb[equality_count + 3 * j + 2] = -4.0;
    ub[equality_count + 3 * j + 2] = 2.0;
  }
  CSC sparse_P(P), sparse_A(A);
  OSQPSettings settings;
  osqp_set_default_settings(&settings);
  settings.verbose = 0;
  settings.polishing = 1;
  settings.max_iter = 60000;
  settings.eps_abs = 1e-5;
  settings.eps_rel = 1e-5;
  OSQPSolver* raw = nullptr;
  const int setup_status = osqp_setup(&raw, &sparse_P.view, q.data(),
      &sparse_A.view, lb.data(), ub.data(), m, n, &settings);
  std::unique_ptr<OSQPSolver, decltype(&osqp_cleanup)> solver(raw, osqp_cleanup);
  QPResult result;
  if (setup_status != 0 || raw == nullptr) {
    result.status = "setup_error:" + std::to_string(setup_status);
    return result;
  }
  const auto begin = std::chrono::steady_clock::now();
  const int solve_status = osqp_solve(raw);
  result.solve_ms = std::chrono::duration<double, std::milli>(
      std::chrono::steady_clock::now() - begin).count();
  result.status = solve_status == 0 ? raw->info->status
                                    : "solve_error:" + std::to_string(solve_status);
  if (solve_status == 0 && raw->info->status_val == OSQP_SOLVED) {
    result.solved = true;
    for (int j = 0; j < K; ++j) {
      result.s.push_back(raw->solution->x[3 * j]);
      result.v.push_back(raw->solution->x[3 * j + 1]);
      result.a.push_back(raw->solution->x[3 * j + 2]);
    }
  }
  return result;
}

}  // namespace miku_speed

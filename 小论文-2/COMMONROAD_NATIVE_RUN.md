# CommonRoad native-output audit run (internal)

## Reproduction environment

- Python: `/home/kent/.local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu/bin/python3.12`
- Isolated environment: `/tmp/miku-cr-312`
- `commonroad-io`: 2024.3
- `commonroad-drivability-checker`: 2025.4.0
- `commonroad-route-planner`: 2025.1.0
- `commonroad-clcs`: 2025.2.0
- `commonroad-reactive-planner`: 2025.1
- Planner OSQP in this isolated environment: 0.6.7.post3

The project environment uses Python 3.14, for which the public reactive-planner
dependency `triangle` has no compatible wheel.  The run therefore uses a
separate Python 3.12 environment; this does not change the paper's claims.

## Command and result

```text
PYTHONPATH=可视化 /tmp/miku-cr-312/bin/python \
  可视化/run_commonroad_miku_native.py --timeout 30
```

The command completed for all four official Lankershim XML scenarios and wrote
`小论文-2/generated/commonroad_miku_native_results.json`.  All eight rows
(B0 and MIKU for each scenario) used the official reader, planning-problem
identifier, KS-state trajectory, solution writer, and drivability checker.

Under the fixed `dt=0.1, horizon_steps=100` protocol, MIKU produces two valid
solutions, one planner failure, and one evaluator-invalid solution. The two
valid rows pass the official dynamics, obstacle, boundary, and goal checks.
The remaining rows are retained with their failure diagnostics; no failure is
converted into a success or a leaderboard score.

The native KS tracker now combines bounded pure-pursuit feedback with a
feed-forward curvature term estimated from adjacent planned path knots. This
is a uniform execution rule for all scenarios; the 16-scenario audit showed no
change in the valid/non-valid counts, so it is retained as an execution
consistency improvement rather than reported as a benchmark gain.

After this tracker, the native writer performs a deterministic terminal
steering-rate shooting refinement under the official BMW-320i KS integrator.
It adjusts at most 20 steering-rate knots, keeps the planner's longitudinal
controls and rate bounds unchanged, and is accepted only when the simulated
terminal position/orientation residual decreases. The evaluator remains the
authority for dynamics, lanelet-boundary, obstacle, and goal validity. On the
16-scene extension the current conservative goal-region semantics produce
7/16 valid solutions; the
fixed four-scene main protocol remains 2/4.

The adapter now projects all four corners of a CommonRoad goal rectangle into
conservative Frenet station/lateral intervals and compiles the terminal lateral
constraint as an interval rather than a centre-point equality. The planning
horizon retains the centre projection for execution compatibility; the interval
is recorded in every native JSON row and remains subject to the official
evaluator.

For goal time intervals, the speed QP enumerates admissible discrete knots
between the declared start and end times and records the selected knot. This
prevents the latest time instant from being treated as the only legal goal hit;
it does not relax the official goal, dynamics, collision, or boundary checks.

The adapter reads the goal orientation from the direct `goalState` child rather
than the orientation stored inside the goal rectangle. For local Frenet
heading mismatches up to 0.5 rad, the path QP gradually matches the terminal
tangent over its last four segments. Larger mismatches are intentionally not
converted into `tan(delta_heading)` lateral offsets, because that approximation
would create artificial lane-boundary excursions.

## Negative-result diagnostics

The native runner records the failure stage rather than leaving a planner
failure indistinguishable from an I/O or evaluator failure. In the current
100-step run, scenario 3 is rejected at `speed_qp` after all finite
space/time homotopy candidates fail the continuous safety certificate;
scenario 4 reaches a solved geometric candidate but the official KS rollout
misses its short goal region: its goal-time interval is only about 0.4 s,
while the initial speed is about 0.99 m/s and the BMW-320i input bound is
|steering_angle_speed| <= 0.4 rad/s. Scenarios 1 and 2 pass the full evaluator.
These failures are retained under `failure_diagnostics` in
`generated/commonroad_miku_native_results.json`; they are not reasons to relax
safety constraints or drop inconvenient obstacles.

## Evidence boundary

The output/evaluator boundary is native CommonRoad. MIKU receives the official
reference route and every published dynamic-obstacle rectangle pose for
auditing; the four corners of each state are projected into a conservative,
time-interpolated Frenet occupancy envelope. A route-relevance filter then
passes only obstacles whose swept envelope intersects the reachable route
corridor to the planner, while retaining source, projected, relevant and
irrelevant counts in the report. This prevents traffic on unrelated lanes or
behind the route from becoming a false `s=0` forward constraint without
silently deleting source data. Lanelet routing and the planning-problem goal
remain official. The route-lanelet left/right bounds define the external
Frenet road envelope; unrestricted global lane-borrow is not enabled without
an adjacent-lane reachability proof.
Traffic-control rules are recorded but are not optimized by the current Frenet
planner, so the result is a scoped compatibility benchmark rather than a
general leaderboard claim.

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

MIKU produced four planner failures and zero valid solutions.  B0 produced
native solution files, but none of the four rows reached the goal under the
40-step protocol.  These are retained as diagnostic rows; no failure is
converted into a success or a leaderboard score.

## Evidence boundary

The output/evaluator boundary is native CommonRoad. MIKU receives the official
reference route and every published dynamic-obstacle rectangle pose; the four
corners of each state are projected into a conservative, time-interpolated
Frenet occupancy envelope consumed by ST mapping and continuous safety
validation. Lanelet routing and the planning-problem goal remain official.
Traffic-control rules are recorded but are not optimized by the current Frenet
planner, so the result is a scoped compatibility benchmark rather than a
general leaderboard claim.

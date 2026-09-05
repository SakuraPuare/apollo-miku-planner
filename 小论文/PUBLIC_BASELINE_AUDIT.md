# Public-baseline audit (internal)

The manuscript does not claim superiority over external methods. This record keeps
the two independently auditable public method assets separate from the paired
Apollo-protocol results.

## 1. CommonRoad Reactive Planner

- Source protocol: CommonRoad NGSIM Lankershim 2020a scenarios.
- Runner: `可视化/run_commonroad_reactive.py`.
- Recorded asset: `小论文-2/generated/commonroad_reactive_results.json`.
- Four pinned scenarios were processed; two produced valid solutions and two
  produced planner failures. Failures remain in the denominator.
- Official reader, route/reference-path utilities, solution writer, and
  drivability checker were used.
- This is an independently run public competitor, not a claim that MIKU's
  restricted adapter is a native CommonRoad planner.

## 2. Cortado public planner family

- Public repository: `/home/kent/scy/Cortado`.
- Repository commit: `f24357c3f0fca56c4ceb55a0710679a67c7c51df`.
- Public benchmark assets:
  - `benchmark/baselines_closed_loop/baselines_closed_loop_highway-v0.csv`
  - `benchmark/baselines_closed_loop/baselines_closed_loop_merge-v0.csv`
  - `benchmark/commonroad/us101_per_scene.csv`
- The benchmark includes Cortado, SSC, EM, Frenet and NLVO method rows, and its
  CSV hashes are recorded in the project audit log.
- These runs use the public Cortado benchmark protocol and are not silently
  merged with the four-scenario CommonRoad audit or the 3,500-case Apollo
  protocol. They are diagnostic external context only.

## Fairness boundary

The two public assets satisfy the auditability requirement for external context,
but they do not justify an across-dataset leaderboard claim. A future revision may
add a native MIKU CommonRoad exporter and shared evaluator; until then the paper
must keep external results in an audit/limitation paragraph and retain B0--B3 as
internal mechanism controls.


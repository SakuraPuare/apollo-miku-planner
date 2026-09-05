# Apollo runtime run index (internal)

This is an index of an existing Apollo/CyberRT process run. It records what the
runtime actually emitted; it is not a claim that the run produced a successful
planning trajectory.

## Run identity

| Item | Value |
|---|---|
| Source repository | `/home/kent/core-11.0` |
| Source branch | `2026/11.0` |
| Source commit | `57460908954e3188f640a813d26180e862d62a5f` |
| Runtime start window | 2026-04-04 02:09:17 +08:00 |
| Runtime log end | 2026-04-04 02:27:18 +08:00 |
| Planning process | `mainboard -d /apollo/modules/planning/planning_component/dag/planning.dag -d /apollo/modules/external_command/process_component/dag/external_command_process.dag` |
| Prediction process | `mainboard -d /apollo/modules/prediction/dag/prediction.dag` |
| Control process | `mainboard -d /apollo/modules/control/control_component/dag/control.dag` |
| Planning PID recorded in bvar | `973132` |
| Mainboard PID recorded in bvar | `973132` |

## Raw artifacts

| Artifact | Size | SHA-256 |
|---|---:|---|
| `data/log/dreamview_plus.log` | 6,614,551 B | `81f735d51a8ec49f531051eca324295faaebbbe8c3fe8846bad25737660567cb` |
| `dumps/planning.dag_external_command_process.dag.data` | 5,603 B | `06791e06b30fb31059403bfe899c8af7d2e55e6edf8a78380c07cdc11d90a9e8` |
| `dumps/planning.dag_external_command_process.dag.latency.data` | 17,353 B | `2397d987c013e6476d5b5ab5d39284b0c141a20a82a63786127c2ec8ce509a1d` |
| `dumps/prediction.dag.data` | 2,146 B | recorded in the fixture manifest |
| `dumps/control.dag.data` | 2,482 B | recorded in the fixture manifest |

## Runtime observations

- The Planning bvar dump reports `mainboard_planning_apollo_planning : 10595`.
- Prediction and localization readers have non-zero message counts in the same
  dump, confirming that the planning process was attached to the CyberRT graph.
- The log repeatedly reports `planning has no trajectory point`,
  `Failed to create reference line from routing`, and
  `PLANNING_ERROR: Fail to shrink routing segments`.
- Dreamview also reports that its scenario-set file was unavailable at
  `/home/kent/.apollo/resources/scenario_sets/scenario/scenario_set.json`.

## Evidence boundary

This run proves that the pinned Apollo Planning/CyberRT process was launched and
produced runtime diagnostics. It does **not** prove a successful MIKU trajectory,
does not identify a particular paper scenario, and does not provide a valid
closed-loop metric. The exact scenario → input → output mapping therefore remains
pending, and the paper must not use this run as a successful Apollo benchmark.


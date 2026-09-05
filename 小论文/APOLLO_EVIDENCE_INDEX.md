# Apollo evidence index (internal submission audit)

This file is an internal traceability record. It is not part of the manuscript and
must not be copied into the paper. The manuscript may mention the Apollo platform,
but every runtime metric must remain tied to a scenario, configuration, source
commit, and raw output file.

## Source provenance (P0: complete)

- Repository snapshot: `../core-11.0`
- Branch: `2026/11.0`
- Planning commit: `57460908954e3188f640a813d26180e862d62a5f`
- Parent commit: `f60a467f4b16227032e1f79153146a1f0769ef87`
- Subject: `feat(planning): add multi-obstacle spatiotemporal corridor optimization`
- Commit date: 2026-02-19 02:19:53 +08:00
- Source snapshot: `apollo_extracted/`
- Snapshot manifest: `apollo_extracted/SHA256SUMS`
- License record: `apollo_extracted/APOLLO_LICENSE`

The commit changes the following planning paths:

```text
modules/planning/WORKSPACE
modules/planning/tasks/piecewise_jerk_speed/piecewise_jerk_speed_optimizer.cc
modules/planning/tasks/speed_bounds_decider/BUILD
modules/planning/tasks/speed_bounds_decider/proto/speed_bounds_decider.proto
modules/planning/tasks/speed_bounds_decider/speed_bounds_decider.cc
modules/planning/tasks/speed_bounds_decider/speed_bounds_decider.h
modules/planning/tasks/speed_bounds_decider/st_corridor_generator.cc
modules/planning/tasks/speed_bounds_decider/st_corridor_generator.h
modules/planning/tasks/speed_bounds_decider/threat_assessor.cc
modules/planning/tasks/speed_bounds_decider/threat_assessor.h
```

The feature flag is `use_multi_obstacle_corridor` and its default is `false`.
This index therefore distinguishes source provenance from evidence that the flag
was enabled during a particular runtime replay.

## Indexed fixtures and hashes (P0: indexed)

The complete path inventory is in `../apollo_fixture_manifest.json`. The indexed
fixture groups are:

- `garage_initial_state` planning input protobufs;
- `sunnyvale_big_loop_replay` planning input protobufs and map;
- planner configuration and ST-boundary interface protobufs;
- Apollo vehicle-model parameter files;
- Sunnyvale map binaries and routing metadata.

The runtime dump inventory includes Planning, Prediction, Control, CyberRT
mainboard, Dreamview Plus, and Cyber monitor files under `../core-11.0/dumps/`.
The following files have recorded SHA-256 values in the audit log:

```text
planning.dag_external_command_process.dag.data
planning.dag_external_command_process.dag.latency.data
prediction.dag.data
control.dag.data
mainboard_default_972347.data
bvar.dreamview_plus.data
speed_bounds_decider.proto
planner_config.pb.txt
sim_map.bin
vehicle_param.pb.txt
```

## Runtime closure status (P1: not yet complete)

| Evidence item | Status | Required closure artifact |
|---|---|---|
| Source commit and parent | complete | commit record and diff manifest |
| Planning fixture paths | complete | fixture manifest |
| Fixture content replayed in a fresh run | pending | replay command, exit status, environment digest |
| Exact scenario → input → output mapping | pending | scenario/config/output index |
| Planning protobuf output and status code | pending | per-scenario output record |
| Dreamview/CyberRT log linkage | pending | run-log index and timestamps |
| Native Apollo build | blocked | 11.0 AEM build reaches C++ compilation but fails on missing `third_party/var/bvar/bvar.h`; command/error in `APOLLO_BUILD_ATTEMPT.md` |
| Closed-loop metric provenance | pending | raw output plus metric-generation script |

Until the pending rows are closed, the paper must not describe the existing dump
inventory alone as a newly replayed native Apollo benchmark, and must not attach
the 3,500-scenario aggregate to an unindexed runtime output.

The existing process run is indexed separately in `APOLLO_RUNTIME_RUN_INDEX.md`.
It provides launch and diagnostic evidence, but its repeated planning failures
mean that it cannot close the successful closed-loop replay gate.

## Manuscript wording boundary

The supported claim is that MIKU is integrated at the Apollo Planning-compatible
path/velocity boundary and that representative interface behavior is documented.
The 3,500-scenario aggregate is a frozen numerical protocol result and must carry
its own seed/configuration provenance. It is not silently reclassified as a fresh
Dreamview/CyberRT replay. No physical-road test is claimed.

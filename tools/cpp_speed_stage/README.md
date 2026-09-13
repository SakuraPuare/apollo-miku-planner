# C++ speed stage for the Python Apollo-pipeline simulation

Build and exercise independently of the path stage:

```sh
g++ -std=c++17 -O2 -Itools/cpp_speed_stage \
  tools/cpp_speed_stage/speed_stage.cpp \
  tools/cpp_speed_stage/test_speed_stage.cpp \
  -losqp -o /tmp/miku_speed_stage_test
/tmp/miku_speed_stage_test
```

This ports `st_boundary_mapper`, `speed_dp`, `build_st_bounds`, the temporal
homotopy graph from `miku_time.py`, and `speed_qp` from the simulation code.
Pass the path-stage output samples to `st_boundary_mapper`. The caller must
apply the `run_pipeline` goal, blocked-path, and terminal-goal retry rules; this
standalone module does not provide complete MIKU planning or an Apollo runtime.
`QPResult::solve_ms` excludes QP assembly and OSQP setup, like Python's
`speed_qp` timer. Benchmark whole stages externally with a steady wall clock.

## Paired first-pass speed-stage benchmark

Requires the locked Python dependencies in the manuscript supplement `.venv`,
`nlohmann/json.hpp`, and the system OSQP headers/library. From the repository
root, the Python scripts explicitly import the frozen
`小论文/jits_submission/supplement/code/可视化` implementation:

```sh
'小论文/jits_submission/supplement/code/.venv/bin/python' tools/export_miku_cases.py
'小论文/jits_submission/supplement/code/.venv/bin/python' tools/cpp_speed_stage/export_path_snapshots.py
g++ -std=c++17 -O2 -Itools/cpp_speed_stage \
  tools/cpp_speed_stage/speed_stage.cpp \
  tools/cpp_speed_stage/benchmark_speed_stage.cpp \
  -losqp -o /tmp/miku_speed_stage_benchmark
/tmp/miku_speed_stage_benchmark \
  submission_artifacts/cpp_benchmark/miku_speed_stage_3500.jsonl \
  submission_artifacts/cpp_benchmark/miku_speed_stage.cpp_raw.csv 3500 3
'小论文/jits_submission/supplement/code/.venv/bin/python' tools/cpp_speed_stage/benchmark_speed_stage.py --repeats 3
'小论文/jits_submission/supplement/code/.venv/bin/python' tools/cpp_speed_stage/summarize_speed_stage.py
```

The JSONL stores real Python `path_bounds_decider` / `path_optimizer` results,
plus ST/DP/decision/QP reference outputs for all planning scenarios. Every C++
case validates its outputs against the Python references before recording
timings. Python reruns the same stage from identical path samples and validates
its results too. Raw CSV rows report the median of three separately timed
runs, following an untimed warm-up for each case; compare only C++ rows with
`parity_ok=1` and the same `(case_kind, seed)` in the Python CSV.

The timed region is one initial **speed stage**: ST projection, DP, temporal
decision and ST bound construction, goal/blocked-path trimming, OSQP speed QP
and the conditional terminal-goal retry. It excludes path-stage computation,
outer MIKU path/speed iteration, alternate spatial/temporal candidates,
scenario generation, I/O and reference validation. It is not a complete
planning runtime, an Apollo integration measurement, or a justified multiplier
for the manuscript's full Python runtime distribution.

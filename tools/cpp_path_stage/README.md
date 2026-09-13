# Frozen MIKU Path-Boundary Port

This standalone C++17 library ports the frozen supplementary
`可视化/apollo_pipeline.py` implementation of `compute_threat`, `compute_delta`,
`arrival_time`, `_miku_path_bounds`, and its `path_bounds_decider(..., "miku")`
postprocessing. It includes grouped obstacle projection, temporal-only crossing
handling, per-obstacle dynamic boundary writeback, ranked Top-3 lateral bands,
Top-3 spatial dynamic programming, the ego start constraint, and blocked trim.
This is one planner stage, **not** an Apollo planning-cycle or full-MIKU runtime.

The C++ library uses the standalone standard library, with no Apollo/OSQP
dependency. From the repository root:

```sh
g++ -std=c++17 -O3 -DNDEBUG -Wall -Wextra -Wpedantic -Werror \
  tools/cpp_path_stage/miku_path_bounds.cpp \
  tools/cpp_path_stage/miku_case_csv.cpp \
  tools/cpp_path_stage/run_path_bounds.cpp \
  -o /tmp/miku_cpp_path_bounds

/tmp/miku_cpp_path_bounds \
  submission_artifacts/cpp_benchmark/miku_cases_3500.csv \
  submission_artifacts/cpp_benchmark/miku_path_bounds_3500.csv 500

'小论文/jits_submission/supplement/code/.venv/bin/python' \
  tools/cpp_path_stage/validate_path_bounds.py \
  --cpp submission_artifacts/cpp_benchmark/miku_path_bounds_3500.csv \
  --python submission_artifacts/cpp_benchmark/miku_path_qp_3500.tsv
```

`tools/export_miku_cases.py` generates `miku_cases_3500.csv` from the frozen
supplement's **planning** scenarios (seven case families, seeds 0..499). The
reference TSV is exported by `tools/benchmark_miku_path_qp.py`; it records
Python's actual path bounds before its QP solve. Parsing, warmup, CSV output,
and Python case generation are outside the timed calls. The C++ runner prints
JSON timing and writes one result row per station with per-scenario mean
`runtime_ms`. Re-run the Python stage with:

```sh
'小论文/jits_submission/supplement/code/.venv/bin/python' \
  tools/cpp_path_stage/benchmark_path_bounds.py \
  --input submission_artifacts/cpp_benchmark/miku_cases_3500.csv \
  --repeat 20 \
  --summary submission_artifacts/cpp_benchmark/miku_path_bounds_3500.python.json

'小论文/jits_submission/supplement/code/.venv/bin/python' \
  tools/cpp_path_stage/summarize_path_bounds.py \
  --input submission_artifacts/cpp_benchmark/miku_cases_3500.csv \
  --cpp submission_artifacts/cpp_benchmark/miku_path_bounds_3500.csv \
  --reference submission_artifacts/cpp_benchmark/miku_path_qp_3500.tsv \
  --cpp-repeat 500 \
  --python submission_artifacts/cpp_benchmark/miku_path_bounds_3500.python.json \
  --python-raw submission_artifacts/cpp_benchmark/miku_path_bounds_3500.python_raw.csv \
  --summary submission_artifacts/cpp_benchmark/miku_path_bounds_3500.calibration.json
```

The saved 3,500-case comparison checks 286,500 stations, their blocked indices,
and spatial candidate counts against frozen Python; maximal measured numerical
error was **0**. Initial rank 1/2 smoke tests each checked 14 cases and 1,146
stations with error 0. The separate stage calibration JSON includes per-case
timings, normalized result checksums, compiler flags, and the stage-only ratio.
The saved Python and C++ repetition runs had brief CPU overlap; do not treat
this stage's ratio as a precise full-pipeline conversion factor.

## C++ Integration

`miku_case_csv.h` provides `ReadCaseCsv(filename)` returning
`std::vector<miku_cpp_path::InputCase>` with `kind`, `seed`, and `scenario`.
`miku_path_bounds.h` provides `PathBounds(scenario, candidate_rank=0, tau_fn={})`
returning `stations`, `lower`, `upper`, `blocked_index`, `groups`, and
`spatial_candidate_count`. A callback `tau_fn(station)` supports arrival-time
updates in iterative replanning. Build and link both library `.cpp` files
above, excluding `run_path_bounds.cpp` when embedding them in another runner.

`miku_path_qp::OptimizePath(result.stations, result.lower, result.upper)` from
`tools/cpp_path_qp/miku_path_qp.h` consumes these vectors directly. For
`miku_speed::Scenario` from `tools/cpp_speed_stage/speed_stage.h`, copy the
input scenario's ego `s0,l0,v0,a0,width,length` to speed ego `s0,l0,v0,a0,W,L`,
copy `s_max,t_max`, and map each obstacle's `width,length` to `W,L` plus its
motion/uncertainty values. Pass the QP lateral solution and `result.stations`
to `miku_speed::st_boundary_mapper`.

`miku_cases_3500.csv` does not contain the obstacles' Python `name`, so the
loader provides stable names `obs0`, `obs1`, etc. These suffice for identity
within one scenario but must be checked if a downstream log or cross-cycle
preference matches the original text labels. The port currently implements
only full MIKU flags and optional candidate rank/arrival-time callback. It
does not port the baseline, ablation variants, `split_overrides`, path QP,
speed-stage algorithms, full run-method retries, or Apollo module integration.

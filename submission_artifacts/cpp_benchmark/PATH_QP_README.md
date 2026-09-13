# MIKU path-QP Python/C++ calibration

This benchmark ports the frozen supplement's `apollo_pipeline.path_optimizer`
to standalone C++ using the system OSQP C API.  It accepts the same `s_arr`,
`l_min` and `l_max` vectors, assembles the same quadratic objective and box
constraints, and returns the path lateral offsets.  It does **not** implement
path-boundary construction, ST search, speed QP or a full Apollo cycle.

From the repository root, regenerate the paired data without overwriting the
manuscript's frozen evidence:

```bash
'小论文/jits_submission/supplement/code/.venv/bin/python' tools/benchmark_miku_path_qp.py \
  --seeds 500 --repeat 5 --coverage-seeds 20 --coverage-stride 25 \
  --output submission_artifacts/cpp_benchmark/miku_path_qp_3500.tsv

g++ -std=c++17 -O3 -DNDEBUG -Wall -Wextra -Wpedantic -Werror -I. \
  tools/cpp_path_qp/miku_path_qp.cpp tools/cpp_path_qp/benchmark.cpp \
  -losqp -o /tmp/miku_path_qp_benchmark

/tmp/miku_path_qp_benchmark \
  submission_artifacts/cpp_benchmark/miku_path_qp_3500.tsv \
  submission_artifacts/cpp_benchmark/miku_path_qp_3500.cpp_raw.csv 5 0.001

'小论文/jits_submission/supplement/code/.venv/bin/python' \
  tools/summarize_miku_path_qp_benchmark.py
```

The TSV contains one row per path station and the original Python QP's
expected path point.  Both timed programs pre-warm three QPs per case, then
time five complete calls including Hessian/CSC construction, OSQP setup/solve,
solution extraction and fallback.  The summary verifies that both raw CSVs
contain the same 3,500 cases, repeat counts and 286,500 stations; the C++
benchmark compares every path point against Python before reporting success.

In the recorded run, 17,500 timed Python calls totaled 11.130931 s and the
same C++ calls totaled 2.651576 s, a `python_to_cpp_ratio` of 4.197855 for
the **path QP only**.  All 3,500 C++ solves succeeded; the largest reported
path-point absolute error was 0 m.  On 140 stratified Python full-planner
calls, `path_optimizer` consumed 112.0294 ms out of 3,052.7664 ms (3.6698%).
The per-case timings, input hash, compiler, OSQP versions, and numerical
checks are recorded in `miku_path_qp_3500.calibration.json`.

`miku_path_qp::OptimizePath(s_arr, l_min, l_max)` in
`tools/cpp_path_qp/miku_path_qp.h` is available for the composed first-cycle
C++ planner.  The path-QP ratio alone is not a measured full-planner ratio or
an Apollo real-time latency measurement.

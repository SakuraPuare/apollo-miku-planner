# MIKU geometry primitive benchmark

This is a paired Python/C++ benchmark of exactly two spatial primitives:
`solve_max_gap` followed by `enumerate_lateral_bands(top_k=3)`. The input CSV
contains every active interval group encountered in the initial MIKU path-bound
construction for seven scenario families and 500 seeds per family (3,500
scenarios, 3,115 active groups). The exporter uses the same scenario generator
as the manuscript, and the C++ runner checks the maximum-gap result and every
ranked candidate against Python's output before recording timing. Both runners
parse inputs outside the timed region and, per group, perform three warmups
followed by 500 timed call pairs.

From the repository root, reproduce the measurements with:

```bash
'小论文/jits_submission/supplement/code/.venv/bin/python' tools/benchmark_miku_geometry.py --seeds 500 --repeat 500 --coverage-seeds 20 --coverage-stride 25 --output submission_artifacts/cpp_benchmark/miku_geometry_3500.csv
g++ -std=c++17 -O3 -DNDEBUG -Wall -Wextra -Wpedantic -Werror tools/miku_geometry_cpp_benchmark.cpp -o /tmp/miku_geometry_cpp_benchmark
/tmp/miku_geometry_cpp_benchmark submission_artifacts/cpp_benchmark/miku_geometry_3500.csv submission_artifacts/cpp_benchmark/miku_geometry_3500.cpp_raw.csv 500 3
python tools/summarize_miku_geometry_benchmark.py --input submission_artifacts/cpp_benchmark/miku_geometry_3500.csv --python-json submission_artifacts/cpp_benchmark/miku_geometry_3500.python.json --python-raw submission_artifacts/cpp_benchmark/miku_geometry_3500.python_raw.csv --cpp-raw submission_artifacts/cpp_benchmark/miku_geometry_3500.cpp_raw.csv --cpp-source tools/miku_geometry_cpp_benchmark.cpp --output submission_artifacts/cpp_benchmark/miku_geometry_3500.calibration.json
```

The input, Python per-group timings, C++ per-group
timings, and paired calibration are respectively `miku_geometry_3500.csv`,
`miku_geometry_3500.python_raw.csv`, `miku_geometry_3500.cpp_raw.csv`, and
`miku_geometry_3500.calibration.json`. The calibration records source/input
SHA-256 digests, compiler flags, hardware, run counts, and output validation.

In the recorded run, Python took 6.815926 s and C++ took 0.168078 s for
1,557,500 paired primitive calls, yielding a 40.552264 Python/C++ ratio for
*these two primitives only*. Instrumenting the complete Python MIKU call on
140 sampled cases measured these primitives at 0.06728% of its wall time.
The path/speed QPs, ST stage, temporal/certified search, safety checks,
refinement, and Apollo/CyberRT scheduling have **not** been ported or timed
here. Any full-method time divided by 40.552264 is an extrapolated number,
not a measured C++ planning latency or real-time guarantee.

## Paired initial speed-stage benchmark

The independent speed-stage implementation (`tools/cpp_speed_stage/`) is
paired on all 3,500 planning scenarios. Its JSONL snapshot contains the
**actual first-pass Python MIKU path** (`s_arr`, `l_path`, path bounds, blocked
index) plus full scenario fields and Python stage-output references. Source
imports explicitly resolve to the manuscript supplement's frozen
`code/可视化/apollo_pipeline.py` under Python 3.12.13 (NumPy 2.4.4, SciPy
1.17.1, OSQP 1.1.1). The C++ stage uses system OSQP and GCC 16.2.1 with
`-std=c++17 -O2 -Wall -Wextra -Werror` on an Intel Core i9-14900HX.

In both languages, the timed region includes ST mapping, speed DP, temporal
graph/bound construction, goal/blocked-path trimming, speed-QP **assembly,
setup, solve**, and conditional retry on a failed hard terminal goal. It
excludes Python path construction, outer MIKU iteration, alternative spatial
or temporal candidates, scenario generation, JSON/CSV I/O and validation.
Each case has one untimed warm-up and three individually timed repetitions;
the CSV records their median. The C++ runner first validates every ST
interval, forbidden/DP result, all speed bounds, temporal decisions and QP
trajectory against Python's exported reference (QP coordinate tolerance
`1e-2`); only validated cases enter the paired summary.

| Metric (3,500 first-pass speed stages) | Python | C++ |
| --- | ---: | ---: |
| Mean (ms) | 15.789 | 12.089 |
| P50 (ms) | 8.588 | 3.800 |
| P95 (ms) | 49.479 | 45.082 |
| P99 (ms) | 150.206 | 147.168 |

The ratio of paired sums is **1.306059 Python/C++** for this initial speed
stage only. Numerical parity: **3,500/3,500**; QP solved in 3,157 cases,
failed in 343, with terminal-goal relaxation in 525 (all status flags match).
Per-case, per-family timings and input/source/output SHA-256 digests are in
`miku_speed_stage.calibration.json`; raw measurements are
`miku_speed_stage.python_raw.csv` and `miku_speed_stage.cpp_raw.csv`.

To reproduce from the repository root after setting up the supplement's
locked `.venv`:

```sh
'小论文/jits_submission/supplement/code/.venv/bin/python' tools/export_miku_cases.py
'小论文/jits_submission/supplement/code/.venv/bin/python' tools/cpp_speed_stage/export_path_snapshots.py
g++ -std=c++17 -O2 -Wall -Wextra -Werror -Itools/cpp_speed_stage tools/cpp_speed_stage/speed_stage.cpp tools/cpp_speed_stage/benchmark_speed_stage.cpp -losqp -o /tmp/miku_speed_stage_benchmark
/tmp/miku_speed_stage_benchmark submission_artifacts/cpp_benchmark/miku_speed_stage_3500.jsonl submission_artifacts/cpp_benchmark/miku_speed_stage.cpp_raw.csv 3500 3
'小论文/jits_submission/supplement/code/.venv/bin/python' tools/cpp_speed_stage/benchmark_speed_stage.py --repeats 3
'小论文/jits_submission/supplement/code/.venv/bin/python' tools/cpp_speed_stage/summarize_speed_stage.py
```

This speed-stage ratio cannot by itself rescale complete Python planning
times, and neither benchmark measures Apollo/CyberRT scheduling or per-cycle
latency on deployment hardware.

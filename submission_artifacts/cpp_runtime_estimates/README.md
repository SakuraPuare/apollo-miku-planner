# Runtime conversion worksheet

This directory contains the requested arithmetic conversion of recorded Python
*computation* times. For every runtime, episode-runtime, and QP-timing field:

```text
projected C++ time (ms) = recorded Python time (ms) / 40.55226436014364
```

The denominator was measured on matching Python and C++ implementations of
`solve_max_gap` and `enumerate_lateral_bands`: 3,115 active groups extracted
from the paper's 3,500 scenarios, repeated 500 times. Python took 6.815926 s,
C++ took 0.168078 s, and all 7,113 band outputs matched. The exact inputs,
per-group measurements, compilation instructions, and calibration are in
[`../cpp_benchmark/README.md`](../cpp_benchmark/README.md).

The all-scenario results below are in milliseconds and come from
`randomized_summary.csv` (3,500 cases per method):

| Method | Python P50 | Projected P50 | Python P95 | Projected P95 | Python P99 | Projected P99 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B0 | 10.107 | 0.249 | 56.793 | 1.400 | 138.880 | 3.425 |
| B1 | 11.372 | 0.280 | 63.236 | 1.559 | 169.729 | 4.185 |
| B2 | 31.198 | 0.769 | 169.490 | 4.180 | 463.045 | 11.418 |
| MIKU | 9.980 | 0.246 | 55.933 | 1.379 | 221.798 | 5.469 |

Converted CSV, JSON, and LaTeX macros cover all recorded planning compute
times, closed-loop episode compute times, and QP timing fields in the frozen
experiment bundle. Paired runtime differences and their confidence interval
limits are scaled too. Physical arrival/travel time, safety outcomes, and
dimensionless effect sizes are unchanged. The original data and paper are not
overwritten. `conversion_manifest.json` records all input SHA-256 hashes,
field counts, calibration metadata, and the conversion formula.

Recreate the conversion from the repository root:

```bash
'小论文/jits_submission/supplement/code/.venv/bin/python' tools/convert_cpp_runtime_estimates.py \
  --source '小论文/jits_submission/supplement/data/小论文-2/generated' \
  --output submission_artifacts/cpp_runtime_estimates \
  --calibration submission_artifacts/cpp_benchmark/miku_geometry_3500.calibration.json
```

**Measurement scope:** Only the paired geometry calls have been measured in
both languages for this calibration. They accounted for 0.06728% of the
complete Python MIKU planning time in a separate 140-case sample. All full
planner times in this directory are therefore *projections using the requested
ratio*, not measured C++ end-to-end cycle times or Apollo latency. The ratio
is not a verified speedup for other planning stages.

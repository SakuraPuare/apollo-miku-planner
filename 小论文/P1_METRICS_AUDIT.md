# P1 system-metric audit (internal)

## Present in the Q3/Q4 manuscript

| Metric | Location/evidence | Status |
|---|---|---|
| Collision-free goal arrival | randomized tables and frozen paired rows | present |
| Collision rate | randomized tables and frozen paired rows | present |
| Progress rate / mean speed | randomized tables and generated macros | present |
| Jerk RMS | randomized tables and generated macros | present |
| Median and P95 planning time | runtime figure/table and frozen rows | present |
| Minimum clearance / continuous safety certificate | mechanism and failure-case artifacts | present for supported protocol |
| Degraded stop / failure reason | failure-case CSV and external audit artifacts | present as diagnostic |
| Vehicle-model interface compatibility | Apollo evidence index and回放 table | present as interface evidence |

## Explicitly not claimed

- P99 latency is not reported as an Apollo runtime metric because the native
  fixture-to-output mapping is pending.
- Tracking error and physical-road vehicle tests are not claimed; the current
  evidence is simulation/interface validation only.
- The CommonRoad adapter rows are not used as a fair MIKU leaderboard score.

This audit prevents missing runtime artifacts from being silently filled by
handwritten numbers and keeps the remaining engineering work visible.


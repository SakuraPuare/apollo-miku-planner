# MIKU replication supplement

This archive accompanies the manuscript *Interaction-Aware Space--Time
Homotopy Constraints for Path--Velocity Planning in Dynamic Multi-Obstacle
Traffic*. It contains the frozen numerical outputs, the source used to
generate them, focused tests, and the figure-generation utility.

## Provenance

The primary results are frozen from commit
`29a337ac70f8c36e0a7bfccc2b6c97eb74a3afc2` (`miku-random-v2`). The copied
files under `data/小论文-2/generated/` are byte-for-byte copies of the
generated files at that commit. The manuscript does not use the current
checkout's smaller regression bundle or a later random-seed protocol for its
3,500-case claims. The root repository's original integrity manifest is
available at `submission_artifacts/SHA256SUMS`; this supplement also carries
the package-local `SHA256SUMS` manifest used for the final archive.

## Package map

| Path | Contents | Role in the paper |
| --- | --- | --- |
| `data/小论文-2/generated/randomized_*` | 14,000 method rows, aggregates, paired statistics and metadata | Main 3,500 paired open-loop protocol |
| `data/小论文-2/generated/randomized_ablation_*` | Subtractive component ablations | RQ2 mechanism analysis |
| `data/小论文-2/generated/closed_loop_*` | 1,400 rolling-replanning rows and summaries | Separate 700-case robustness protocol |
| `data/小论文-2/generated/joint_reference_*` | 140 finite-grid rows and summaries | 70-case B3 computational reference |
| `data/小论文-2/generated/sensitivity_*` | Sensitivity and trajectory exports | Supporting diagnostics |
| `code/可视化/` | Scenario generators, planners, metrics and protocol runners | Reproduction source |
| `code/tests/` | Geometry, timing, schema and pipeline tests | Verification of invariants and output contracts |
| `data/小论文-2/generated/evidence_dashboard.*` | Recreated four-panel evidence figure | Figure 4 source output |

The three Dreamview screenshots in the manuscript are supplied in the parent
submission `figures/dreamview/` directory. Apollo source and binaries are not
redistributed here; the manuscript reports only the interface-level evidence
that can be inspected under the applicable upstream licenses.

## Protocols

| Protocol | Cases | Seeds per family | Purpose | Pool with main result? |
| --- | ---: | ---: | --- | --- |
| `miku-random-v2` | 3,500 | 500 | Matched B0, B1, B2 and MIKU comparison across seven generated families | Yes; this is the headline result |
| `miku-randomized-ablation-v1` | 3,500 | 500 | One-component-at-a-time ablations on the same cases | Reported separately |
| `miku-rolling-v1` | 700 | 100 | 0.5-s execution and rolling replanning | No |
| `miku-joint-reference-v2` | 70 | 10 | Coarse finite-grid B3 reference | No |
| fixed-section geometry check | 4,000 | 20 x 200 | Scan versus exhaustive `2^k` enumeration | Analytical check |

All scenario families are generated straight-road cases. Obstacle motion is
constant velocity, and the prediction-noise family applies bounded errors only
to the planning input while collision truth remains unperturbed. These facts
define the scope of the reported evidence; the archive is not a public-data,
field, hardware-in-the-loop, or road-test dataset.

## Reproduction

The tested environment is Python 3.12 or newer on Linux. Dependency pins are
in `code/pyproject.toml` and `code/uv.lock`. From this directory, a typical
setup and verification sequence is:

```bash
cd code
uv sync --locked
PYTHONPATH=可视化 uv run pytest -q tests
```

The same commands can be run with an already provisioned `python` and
`pytest` by replacing `uv run` with the local interpreter. The convenience
script `reproduce.sh` provides `tests`, `figures`, `verify`, and an explicit
`full` mode. Full regeneration writes to a directory supplied by the caller;
it never overwrites the frozen archive unless that directory is chosen
explicitly.

For example, to regenerate the main protocol in a fresh output directory:

```bash
OUT=/tmp/miku-random-v2-reproduction
mkdir -p "$OUT"
cd code
PYTHONPATH=可视化 uv run python 可视化/run_randomized_experiments.py \
  --seed-start 0 --seeds 500 --output "$OUT"
uv run python generate_submission_figures.py --data-dir "$OUT"
```

The ablation, rolling, and finite-grid protocols use the corresponding
`run_randomized_ablation.py`, `run_closed_loop_experiments.py`, and
`run_joint_reference_experiments.py` entry points with their documented seed
counts. Full regeneration is computationally heavier than the focused test
suite. The reported confidence intervals use 5,000 paired percentile-bootstrap
resamples and binary outcomes use exact McNemar tests, as implemented in
`可视化/experiment_metrics.py`.

## Integrity and metadata note

Run `./reproduce.sh verify` after the package-local `SHA256SUMS` file has been
created. The frozen `randomized_results.json` also contains a legacy
`decision_gates.C5_safe_window` text field from an earlier audit. That string
is not consumed by the runner or any aggregation. The authoritative v2 method
configuration is `methods[].flags`, and the component definition and effect of
the temporal homotopy graph are recorded in
`randomized_ablation_results.json`. The discrepancy is documented, without
altering the frozen JSON, in `metadata_corrections.md`.

## Interpretation boundaries

The maximum-gap scan is exact only for the fixed-section interval abstraction
and is checked against exhaustive enumeration. B3 is a coarse finite-grid beam
search, not a continuous global oracle. Apollo evidence checks a software
insertion point and three representative Dreamview cases; it does not measure
native Apollo latency or establish physical-road safety. These boundaries are
also stated in the manuscript's Results, Discussion, and Limitations sections.

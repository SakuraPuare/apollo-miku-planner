# Frozen metadata correction note

## Scope

The file `data/小论文-2/generated/randomized_results.json` is preserved
unchanged from the frozen evaluation commit
`29a337ac70f8c36e0a7bfccc2b6c97eb74a3afc2`. Its SHA-256 is
`10ba825b23967160c51a7710ac6fe985be9f8dba63bce89fc212f6e937df5034`.

## Legacy field

The JSON object contains the following historical audit note:

```text
decision_gates.C5_safe_window:
Excluded from the main MIKU method after corrected deterministic ablation
showed no independent benefit and one repeatable regression.
```

This text predates the `miku-random-v2` method configuration and is not read by
the scenario runner, metric aggregation, bootstrap code, or figure generator.
It therefore has no effect on any reported row or statistic.

## Authoritative interpretation

For protocol v2, the method flags in `methods[].flags` are authoritative:

- MIKU has `corridor_inject=true` and `robust_prediction=true`.
- The subtractive A5 variant in
  `randomized_ablation_results.json` has `corridor_inject=false` and is the
  reported *without temporal homotopy graph* ablation.
- The manuscript's delayed-crossing result (89.6% for MIKU versus 66.8% for
  A5) is computed from those frozen rows.

The archived JSON is not rewritten to hide the provenance issue. This note
separates the stale audit label from the executable configuration so that a
reviewer can reproduce the exact archive and understand which field controls
the analysis.

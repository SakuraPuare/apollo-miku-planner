# Submission artifact bundle

This directory is the supplement bundle produced from the frozen experiment
commit `29a337a` plus the current 700-case regression checkout.

- `frozen_3500/` contains the manuscript's 3,500 paired rows, ablation rows and
  closed-loop artifact files exported from the frozen commit.
- `regression_700/` contains the smaller fast regression package used by the
  current test suite.
- `SHA256SUMS` was generated after extraction and is the integrity manifest.

The frozen bundle is the source for the 3,500-case claims in the manuscript; the
700-case bundle must not replace it in a submission package.


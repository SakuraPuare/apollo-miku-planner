#!/usr/bin/env bash
set -euo pipefail

SUPPLEMENT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CODE_ROOT="$SUPPLEMENT_ROOT/code"
DATA_ROOT="$SUPPLEMENT_ROOT/data/小论文-2/generated"

if command -v uv >/dev/null 2>&1; then
  RUN=(uv run --project "$CODE_ROOT" python)
  TEST=(uv run --project "$CODE_ROOT" pytest)
else
  RUN=(python)
  TEST=(python -m pytest)
fi

export PYTHONPATH="$CODE_ROOT/可视化"

mode=${1:-tests}
case "$mode" in
  tests)
    "${TEST[@]}" -q "$CODE_ROOT/tests"
    ;;
  figures)
    "${RUN[@]}" "$CODE_ROOT/generate_submission_figures.py" --data-dir "$DATA_ROOT"
    ;;
  verify)
    if [ ! -f "$SUPPLEMENT_ROOT/SHA256SUMS" ]; then
      printf '%s\n' "Missing supplement/SHA256SUMS; create it for the final archive first." >&2
      exit 2
    fi
    (cd "$SUPPLEMENT_ROOT" && sha256sum -c SHA256SUMS)
    ;;
  full)
    output=${2:?usage: ./reproduce.sh full OUTPUT_DIRECTORY}
    mkdir -p "$output"
    "${RUN[@]}" "$CODE_ROOT/可视化/run_randomized_experiments.py" \
      --seed-start 0 --seeds 500 --output "$output/open_loop"
    "${RUN[@]}" "$CODE_ROOT/可视化/run_randomized_ablation.py" \
      --seed-start 0 --seeds 500 --output "$output/ablation"
    "${RUN[@]}" "$CODE_ROOT/可视化/run_closed_loop_experiments.py" \
      --seed-start 0 --seeds 100 --output "$output/rolling"
    "${RUN[@]}" "$CODE_ROOT/可视化/run_joint_reference_experiments.py" \
      --seed-start 0 --seeds 10 --output "$output/joint_reference"
    "${RUN[@]}" "$CODE_ROOT/generate_submission_figures.py" \
      --data-dir "$output/open_loop"
    ;;
  *)
    printf '%s\n' "usage: ./reproduce.sh {tests|figures|verify|full OUTPUT_DIRECTORY}" >&2
    exit 2
    ;;
esac

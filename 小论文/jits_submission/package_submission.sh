#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
OUT="$ROOT/deliverables"
STAGE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/miku-jits-package.XXXXXX")"

cleanup() {
  if [[ -n "${STAGE_ROOT:-}" && -d "$STAGE_ROOT" && "$STAGE_ROOT" == */miku-jits-package.* ]]; then
    rm -rf -- "$STAGE_ROOT"
  fi
}
trap cleanup EXIT

NAMED="$STAGE_ROOT/MIKU_JITS_named"
ANON="$STAGE_ROOT/MIKU_JITS_anonymous"
SUPPLEMENT="$STAGE_ROOT/MIKU_JITS_supplement"
mkdir -p "$OUT" "$NAMED/sections" "$NAMED/figures/dreamview" \
  "$ANON/sections" "$ANON/figures/dreamview" "$SUPPLEMENT"

(
  cd "$ROOT"
  latexmk -pdf -interaction=nonstopmode -halt-on-error manuscript.tex
  latexmk -pdf -interaction=nonstopmode -halt-on-error \
    -jobname=anonymous anonymous.tex
)

common_root=(manuscript.tex anonymous.tex interact.cls references.bib)
for file in "${common_root[@]}"; do
  cp -p "$ROOT/$file" "$NAMED/$file"
  cp -p "$ROOT/$file" "$ANON/$file"
done

for file in "$ROOT"/sections/*.tex; do
  cp -p "$file" "$NAMED/sections/"
  case "$file" in
    *_named.tex) ;;
    *) cp -p "$file" "$ANON/sections/" ;;
  esac
done

figure_files=(
  evidence_dashboard.pdf
  fig_framework_en.pdf fig_framework_en.tex
  fig_max_gap_en.pdf fig_max_gap_en.tex
  fig_narrow_en.pdf fig_narrow_en.tex
  fig_teaser_en.pdf fig_teaser_en.tex
  ped_macros.tex standalone_figure.tex
)
for file in "${figure_files[@]}"; do
  cp -p "$ROOT/figures/$file" "$NAMED/figures/$file"
  cp -p "$ROOT/figures/$file" "$ANON/figures/$file"
done
for file in "$ROOT"/figures/dreamview/*.png; do
  cp -p "$file" "$NAMED/figures/dreamview/"
  cp -p "$file" "$ANON/figures/dreamview/"
done

cp -p "$ROOT/manuscript.pdf" "$NAMED/manuscript.pdf"
cp -p "$ROOT/anonymous.pdf" "$NAMED/anonymous.pdf"
cp -p "$ROOT/anonymous.pdf" "$ANON/anonymous.pdf"
cp -p "$ROOT/named_metadata.tex" "$NAMED/named_metadata.tex"
cp -p "$ROOT/README.md" "$ROOT/author_information.md" \
  "$ROOT/cover_letter.md" "$ROOT/submission_checklist.md" \
  "$ROOT/validate_submission.py" "$ROOT/package_submission.sh" "$NAMED/"
cp -p "$ROOT/anonymous_submission_readme.md" "$ANON/"

rsync -a --exclude='.venv/' --exclude='.pytest_cache/' \
  --exclude='__pycache__/' --exclude='*.pyc' \
  "$ROOT/supplement/" "$NAMED/supplement/"
rsync -a "$NAMED/supplement/" "$ANON/supplement/"
rsync -a "$NAMED/supplement/" "$SUPPLEMENT/"

identity_pattern='JiaWang Liao|YuFei Hu|ChaoYang Shi|ChengJiao Sun|jiao1952@126\.com|Hubei University of Arts and Science|Xiangyang Municipal Key Laboratory|2025BEB002'
if rg -l --hidden -g '!*.pdf' -g '!*.png' -e "$identity_pattern" "$ANON"; then
  echo "Anonymous source package contains identifying text." >&2
  exit 1
fi
if pdftotext -layout "$ANON/anonymous.pdf" - | rg -e "$identity_pattern"; then
  echo "Anonymous PDF contains identifying text." >&2
  exit 1
fi
if ! pdfinfo "$ANON/anonymous.pdf" | rg -q '^Author:[[:space:]]+Anonymous[[:space:]]*$'; then
  echo "Anonymous PDF metadata is not anonymized." >&2
  exit 1
fi

bsdtar -a -cf "$STAGE_ROOT/MIKU_JITS_named_submission.zip" \
  -C "$STAGE_ROOT" MIKU_JITS_named
bsdtar -a -cf "$STAGE_ROOT/MIKU_JITS_anonymous_submission.zip" \
  -C "$STAGE_ROOT" MIKU_JITS_anonymous
bsdtar -a -cf "$STAGE_ROOT/MIKU_JITS_supplement.zip" \
  -C "$STAGE_ROOT" MIKU_JITS_supplement

cp -f "$ROOT/manuscript.pdf" "$OUT/MIKU_JITS_named.pdf"
cp -f "$ROOT/anonymous.pdf" "$OUT/MIKU_JITS_anonymous.pdf"
mv -f "$STAGE_ROOT/MIKU_JITS_named_submission.zip" "$OUT/"
mv -f "$STAGE_ROOT/MIKU_JITS_anonymous_submission.zip" "$OUT/"
mv -f "$STAGE_ROOT/MIKU_JITS_supplement.zip" "$OUT/"

(
  cd "$OUT"
  sha256sum \
    MIKU_JITS_named.pdf \
    MIKU_JITS_anonymous.pdf \
    MIKU_JITS_named_submission.zip \
    MIKU_JITS_anonymous_submission.zip \
    MIKU_JITS_supplement.zip > SHA256SUMS
)

echo "Submission artifacts written to $OUT"

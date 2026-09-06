#!/usr/bin/env bash
set -euo pipefail

source_root="${1:-/home/kent/core-11.0}"
commit="${2:-57460908954e3188f640a813d26180e862d62a5f}"
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target_root="${project_root}/apollo_extracted/${commit}"

if [[ ! -d "${source_root}/.git" ]]; then
  echo "source root is not a git worktree: ${source_root}" >&2
  exit 2
fi
if ! git -C "${source_root}" cat-file -e "${commit}^{commit}"; then
  echo "commit not found: ${commit}" >&2
  exit 2
fi
if [[ -e "${target_root}" ]]; then
  echo "refusing to overwrite existing snapshot: ${target_root}" >&2
  exit 3
fi

mkdir -p "${target_root}"
git -C "${source_root}" archive "${commit}" --format=tar \
  $(git -C "${source_root}" diff-tree --no-commit-id --name-only -r "${commit}") \
  | tar -xf - -C "${target_root}"

# The proto below is an existing Apollo interface consumed by the MIKU patch.
interface_file="modules/planning/planning_base/proto/st_drivable_boundary.proto"
mkdir -p "${target_root}/$(dirname "${interface_file}")"
git -C "${source_root}" show "${commit}:${interface_file}" > "${target_root}/${interface_file}"

cp "${source_root}/LICENSE" "${target_root}/APOLLO_LICENSE"
{
  echo "Apollo-MIKU source snapshot"
  echo "source_root=${source_root}"
  echo "commit=${commit}"
  echo "commit_subject=$(git -C "${source_root}" log -1 --format=%s "${commit}")"
  echo "commit_date=$(git -C "${source_root}" log -1 --format=%cI "${commit}")"
  echo ""
  echo "files and sha256:"
  find "${target_root}" -type f ! -name MANIFEST.txt -print0 \
    | sort -z \
    | while IFS= read -r -d '' file; do
        printf '%s  %s\n' "$(sha256sum "${file}" | cut -d ' ' -f1)" "${file#"${target_root}/"}"
      done
} > "${target_root}/MANIFEST.txt"

echo "created ${target_root}"

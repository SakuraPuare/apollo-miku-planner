#!/usr/bin/env bash
set -euo pipefail

source_root="${1:-/home/kent/core-11.0}"
commit="${2:-57460908954e3188f640a813d26180e862d62a5f}"
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
snapshot="${project_root}/apollo_extracted/${commit}"

if [[ ! -f "${snapshot}/MANIFEST.txt" ]]; then
  echo "snapshot manifest missing: ${snapshot}/MANIFEST.txt" >&2
  exit 2
fi
if ! git -C "${source_root}" cat-file -e "${commit}^{commit}"; then
  echo "commit not found: ${commit}" >&2
  exit 2
fi

status=0
while read -r expected relative; do
  [[ -z "${expected}" || "${expected}" == Apollo-MIKU* || "${expected}" == source_root=* || "${expected}" == commit=* || "${expected}" == commit_subject=* || "${expected}" == commit_date=* || "${expected}" == files* ]] && continue
  [[ "${relative}" == "APOLLO_LICENSE" ]] && continue
  snapshot_file="${snapshot}/${relative}"
  if [[ "${relative}" == "modules/planning/planning_base/proto/st_drivable_boundary.proto" ]]; then
    actual="$(git -C "${source_root}" show "${commit}:${relative}" | sha256sum | cut -d ' ' -f1)"
  else
    actual="$(git -C "${source_root}" show "${commit}:${relative}" | sha256sum | cut -d ' ' -f1)"
  fi
  if [[ ! -f "${snapshot_file}" ]]; then
    echo "MISSING ${relative}" >&2
    status=1
  elif [[ "${actual}" != "${expected}" ]]; then
    echo "MISMATCH ${relative}: expected ${expected}, got ${actual}" >&2
    status=1
  fi
done < "${snapshot}/MANIFEST.txt"

if [[ "${status}" -eq 0 ]]; then
  echo "Apollo snapshot verified: ${snapshot}"
fi
exit "${status}"

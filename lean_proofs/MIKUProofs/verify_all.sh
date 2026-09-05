#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$(dirname "$0")"
python "$root/lean_proofs/check_lean_links.py"
if rg -n '\b(sorry|axiom)\b' --glob '*.lean' "$root/lean_proofs"; then
  echo 'forbidden sorry/axiom found' >&2
  exit 1
fi
lake env lean MIKUCommon.lean
lake env lean Kinematics.lean
lake env lean QP.lean
lake env lean LinearQP.lean
lake env lean ContinuousSafety.lean
lake env lean GeometrySafety.lean
lake env lean WindowAlgebra.lean
lake env lean STCorridor.lean
lake env lean SafeWindowComplement.lean
lake env lean Partition.lean
lake env lean QuadraticSweep.lean
lake env lean MaxGap.lean
lake env lean PrefixGap.lean
lake env lean FiniteSearch.lean
lake env lean LayeredSearch.lean
lake env lean Feasibility.lean
lake env lean Rolling.lean
lake env lean Refinement.lean
lake env lean Threat.lean
lake env lean ThreatExact.lean
lake env lean ThreatSigmoid.lean
lake env lean TypeThreat.lean
lake env lean RobustEnvelope.lean
lake env lean RobustSafety.lean
lake env lean CorridorLowerBound.lean
lake env lean TimeWindows.lean
lake env lean Scanline.lean
lake env lean Grouping.lean
lake env lean Certificates.lean
lake env lean Fallback.lean
lake env lean "$root/小论文/lean/Paper3.lean"
lake env lean "$root/小论文-2/lean/Paper2.lean"
if command -v uv >/dev/null 2>&1; then
  (cd "$root" && uv run pytest -q tests/test_miku_geometry.py tests/test_miku_time.py tests/test_joint_homotopy_search.py)
fi
echo "All current MIKU Lean proofs verified."

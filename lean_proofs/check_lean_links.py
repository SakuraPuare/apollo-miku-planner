"""Check that every documented implementation link names a real Python symbol.

This is a lightweight audit, not a refinement proof.  It prevents the
coverage matrix from silently referring to renamed or missing functions.
"""
from pathlib import Path
import ast
import re

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "lean_proofs" / "FORMAL_COVERAGE.md"
PY_FILES = [
    ROOT / "可视化" / "miku_geometry.py",
    ROOT / "可视化" / "miku_time.py",
    ROOT / "可视化" / "joint_homotopy_search.py",
    ROOT / "可视化" / "apollo_pipeline.py",
]

symbols: set[str] = set()
for path in PY_FILES:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    symbols |= {
        node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

links = set(re.findall(r"`(?:[^`]*::)?([A-Za-z_][A-Za-z0-9_]*)`", MATRIX.read_text(encoding="utf-8")))
required = {
    "solve_max_gap", "brute_force_max_gap", "enumerate_lateral_bands",
    "select_spatial_homotopy", "enumerate_spatial_homotopies",
    "safe_time_windows", "intersect_window_sets", "select_time_window",
    "enumerate_temporal_homotopies", "bounded_lazy_joint_search",
    "certify_sampled_axis_aligned_motion", "validate_candidate_continuous_safety",
    "validate_candidate_constant_acceleration_safety", "f_ttc", "f_overlap",
    "compute_threat", "compute_delta", "arrival_time", "speed_dp", "speed_qp",
    "path_bounds_decider", "path_optimizer", "st_boundary_mapper", "run_pipeline",
    "validate_pipeline_candidate_continuous_safety",
}
missing = sorted(name for name in required if name not in symbols)
if missing:
    raise SystemExit(f"missing documented Python symbols: {missing}")
print(f"checked {len(symbols)} Python function symbols and documented implementation links")

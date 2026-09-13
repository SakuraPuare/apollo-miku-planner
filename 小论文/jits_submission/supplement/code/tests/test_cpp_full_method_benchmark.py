"""Check complete-method Python parity includes path and speed postprocessing."""

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.cpp_planner.benchmark_full_method import validate_full  # noqa: E402


def _sample():
    path_stations = [0.0, 0.5]
    reference = {
        "iterations": 2,
        "converged": True,
        "blocked_idx": -1,
        "spatial_candidate_count": 3,
        "temporal_candidate_count": 2,
        "terminal_goal_relaxed": False,
        "path_stations": path_stations,
        "path_offsets": [0.0, 0.1],
        "curvature": [0.0, 0.2],
        "lateral_acceleration": [0.0, 1.1],
        "s": [0.0, 0.5],
        "v": [1.0, 1.1],
        "a": [0.0, 0.1],
    }
    result = {
        "blocked_idx": -1,
        "spatial_homotopy_candidate_count": 3,
        "temporal_homotopy_candidate_count": 2,
        "terminal_goal_relaxed": False,
        "s_arr": np.asarray(path_stations),
        "l_path": np.asarray(reference["path_offsets"]),
        "kappa_s": np.asarray(reference["curvature"]),
        "a_y": np.asarray(reference["lateral_acceleration"]),
        "s_qp": np.asarray(reference["s"]),
        "v_qp": np.asarray(reference["v"]),
        "a_qp": np.asarray(reference["a"]),
    }
    return SimpleNamespace(iterations=2, converged=True, result=result), reference


def test_complete_method_parity_checks_curvature_and_lateral_acceleration():
    method, reference = _sample()
    assert validate_full(method, reference, 0.01) == ""

    method.result["kappa_s"][1] += 0.02
    assert validate_full(method, reference, 0.01) == "curvature at 1"

    method.result["kappa_s"][1] -= 0.02
    method.result["a_y"][1] += 0.02
    assert validate_full(method, reference, 0.01) == "lateral acceleration at 1"


def test_complete_method_parity_accepts_consistent_unsolved_speed():
    method, reference = _sample()
    for field in ("s", "v", "a", "lateral_acceleration"):
        reference[field] = None
    for field in ("s_qp", "v_qp", "a_qp", "a_y"):
        method.result[field] = None
    assert validate_full(method, reference, 0.01) == ""

    method.result["a_y"] = np.asarray([0.0, 0.0])
    assert validate_full(method, reference, 0.01) == "lateral acceleration nullability"

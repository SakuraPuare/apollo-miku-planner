"""Verify the standalone C++ path-QP harness receives frozen Python inputs."""

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.benchmark_miku_path_qp import _read, benchmark, export  # noqa: E402


def test_path_qp_export_and_python_rerun(tmp_path):
    input_path = tmp_path / "path_qp.tsv"
    exported = export(0, 1, input_path)
    assert exported["case_count"] == 7
    assert exported["station_count"] == 573

    cases = _read(input_path)
    assert len(cases) == 7
    assert cases[0][0] == ("crossing_pedestrian", 0)
    assert len(cases[0][1]) == 65
    assert cases[0][1][1] == 0.5
    assert cases[3][0] == ("narrow_multi_obstacle", 0)
    assert cases[3][-1] >= -1

    measured = benchmark(cases, input_path, repeats=2, tolerance=1e-5)
    assert measured["measured_call_count"] == 14
    assert measured["python_aggregate_elapsed_s"] > 0
    assert measured["max_python_rerun_abs_error_m"] == 0

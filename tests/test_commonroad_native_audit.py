from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_native_commonroad_audit_artifact_has_standard_entities() -> None:
    path = ROOT / "小论文-2" / "generated" / "commonroad_native_audit.json"
    rows = json.loads(path.read_text(encoding="utf-8"))

    assert len(rows) == 4
    assert {row["lanelets"] for row in rows} == {95}
    assert all(row["planning_problems"] == 1 for row in rows)
    assert all(row["dynamic_obstacles"] > 0 for row in rows)
    assert all(
        row["rectangular_obstacles"] == row["dynamic_obstacles"] for row in rows
    )
    assert all(row["predicted_trajectory_states"] > 0 for row in rows)

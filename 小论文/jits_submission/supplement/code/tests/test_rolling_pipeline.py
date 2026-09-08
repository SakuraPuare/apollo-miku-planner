from __future__ import annotations

from apollo_pipeline import AblationFlags, Ego, Obstacle, Scenario, run_pipeline


def test_passed_static_obstacle_does_not_cap_rolling_speed_bounds_behind_ego():
    scenario = Scenario(
        ego=Ego(s0=15.0, v0=4.0),
        obstacles=[
            Obstacle(
                s0=5.0,
                l0=0.0,
                W=1.8,
                L=4.0,
                is_static=True,
                obs_type="static",
            )
        ],
        s_max=25.0,
        t_max=4.0,
    )

    result = run_pipeline(AblationFlags.baseline(), scenario)

    assert result["st_bounds"][0]["intervals"] == []
    assert result["s_qp"] is not None
    assert result["s_qp"][-1] > scenario.ego.s0

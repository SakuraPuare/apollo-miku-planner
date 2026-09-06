from __future__ import annotations

import sys

import pytest
import numpy as np

sys.path.insert(0, "可视化")
from commonroad_adapter import (  # noqa: E402
    _circular_midpoint,
    _project,
    _route,
    adapt_commonroad_xml,
)
from run_commonroad_miku_native import _circular_midpoint as _native_circular_midpoint  # noqa: E402


MINIMAL_XML = b"""
<commonRoad benchmarkID="unit-test">
  <lanelet id="a">
    <leftBound><point><x>0</x><y>1</y></point><point><x>10</x><y>1</y></point></leftBound>
    <rightBound><point><x>0</x><y>-1</y></point><point><x>10</x><y>-1</y></point></rightBound>
    <successor ref="b"/>
  </lanelet>
  <lanelet id="b">
    <leftBound><point><x>10</x><y>1</y></point><point><x>20</x><y>1</y></point></leftBound>
    <rightBound><point><x>10</x><y>-1</y></point><point><x>20</x><y>-1</y></point></rightBound>
  </lanelet>
  <dynamicObstacle id="1">
    <type>car</type>
    <shape><rectangle><length>4</length><width>2</width></rectangle></shape>
    <initialState>
      <position><point><x>7</x><y>0.5</y></point></position>
      <orientation><exact>0</exact></orientation>
      <velocity><exact>3</exact></velocity>
    </initialState>
    <trajectory>
      <state>
        <position><point><x>10.2</x><y>0.7</y></point></position>
        <time><exact>1</exact></time>
      </state>
    </trajectory>
  </dynamicObstacle>
  <planningProblem id="p">
    <initialState>
      <position><point><x>0</x><y>0</y></point></position>
      <velocity><exact>5</exact></velocity>
    </initialState>
    <goalState>
      <position><rectangle><center><x>19</x><y>0</y></center></rectangle></position>
      <time><intervalEnd>8</intervalEnd></time>
    </goalState>
  </planningProblem>
</commonRoad>
"""


def test_commonroad_adapter_projects_route_and_obstacle():
    result = adapt_commonroad_xml(MINIMAL_XML, preserve_sampled_prediction=True)
    assert result.benchmark_id == "unit-test"
    assert result.route_lanelet_ids == ("a", "b")
    assert result.projected_obstacles == 1
    assert result.skipped_obstacles == 0
    assert result.trajectory_states_used == 1
    assert result.scenario.s_max > result.scenario.ego.s0
    assert result.scenario.goal_lateral == pytest.approx(0.0)
    obstacle = result.scenario.obstacles[0]
    assert obstacle.s0 == pytest.approx(7.0)
    assert obstacle.l0 == pytest.approx(0.5)
    assert obstacle.vs == pytest.approx(3.0)
    assert obstacle.uncertainty_vs == pytest.approx(0.2)
    assert obstacle.uncertainty_vl == pytest.approx(0.2)
    assert obstacle.prediction_t == pytest.approx((0.0, 1.0))
    assert obstacle.position_at(0.5)[0] == pytest.approx(8.6)
    assert obstacle.position_at(0.5)[1] == pytest.approx(0.6)
    assert obstacle.occupancy_t == pytest.approx((0.0, 1.0))
    assert obstacle.occupancy_s_min[0] < obstacle.occupancy_s_max[0]
    assert obstacle.occupancy_l_min[0] < obstacle.occupancy_l_max[0]
    assert obstacle.occupancy_bounds_at(0.5)[0] < obstacle.occupancy_bounds_at(0.5)[1]


def test_commonroad_goal_orientation_becomes_frenet_terminal_heading():
    source = MINIMAL_XML.replace(
        b"<center><x>19</x><y>0</y></center>",
        b"<orientation>-0.7</orientation><center><x>19</x><y>0</y></center>",
    ).replace(
        b"<time><intervalEnd>8</intervalEnd></time>",
        b"<orientation><exact>0.2</exact></orientation>"
        b"<time><intervalEnd>8</intervalEnd></time>",
    )
    result = adapt_commonroad_xml(source)
    assert result.scenario.goal_heading_error == pytest.approx(0.2)


def test_commonroad_goal_rectangle_is_preserved_as_frenet_interval():
    source = MINIMAL_XML.replace(
        b"<position><rectangle><center><x>19</x><y>0</y></center></rectangle></position>",
        b"<position><rectangle><length>4</length><width>2</width>"
        b"<orientation>0</orientation><center><x>19</x><y>0</y></center>"
        b"</rectangle></position>",
    )
    result = adapt_commonroad_xml(source)
    scenario = result.scenario
    assert scenario.goal_s_min == pytest.approx(17.0)
    assert scenario.goal_s_max == pytest.approx(21.0)
    assert scenario.goal_l_min == pytest.approx(-1.0)
    assert scenario.goal_l_max == pytest.approx(1.0)
    assert scenario.s_max == pytest.approx(19.0)


def test_adapter_preserves_station_varying_lanelet_bounds():
    source = MINIMAL_XML.replace(
        b"<leftBound><point><x>10</x><y>1</y></point><point><x>20</x><y>1</y></point></leftBound>",
        b"<leftBound><point><x>10</x><y>1</y></point><point><x>20</x><y>2</y></point></leftBound>",
    ).replace(
        b"<rightBound><point><x>10</x><y>-1</y></point><point><x>20</x><y>-1</y></point></rightBound>",
        b"<rightBound><point><x>10</x><y>-1</y></point><point><x>20</x><y>-2</y></point></rightBound>",
    )
    scenario = adapt_commonroad_xml(source).scenario
    assert scenario.road_s_profile is not None
    assert np.ptp(scenario.road_l_max_profile) > 0.1
    assert np.ptp(scenario.road_l_min_profile) > 0.1


def test_goal_orientation_midpoint_wraps_across_pi():
    midpoint = _circular_midpoint(3.05, -3.05)
    assert abs(abs(midpoint) - 3.141592653589793) < 0.1
    assert abs(abs(_native_circular_midpoint(3.05, -3.05)) - 3.141592653589793) < 0.1


def test_commonroad_adapter_rejects_missing_route():
    with pytest.raises(ValueError, match="no successor route"):
        _route({"a": ("missing",), "b": ()}, "a", "b")


def test_project_preserves_signed_station_outside_route_endpoints():
    import numpy as np

    polyline = np.asarray([[0.0, 0.0], [10.0, 0.0]])
    before = _project(polyline, np.asarray([-3.0, 1.0]))
    after = _project(polyline, np.asarray([13.0, -1.0]))
    assert before[0] == pytest.approx(-3.0)
    assert before[1] == pytest.approx(1.0)
    assert after[0] == pytest.approx(13.0)
    assert after[1] == pytest.approx(-1.0)


def test_adapter_audits_but_excludes_route_irrelevant_obstacle():
    source = MINIMAL_XML.replace(b"<x>7</x>", b"<x>-20</x>").replace(
        b"<x>10.2</x>", b"<x>-19</x>"
    )
    result = adapt_commonroad_xml(
        source, project_all_dynamic_obstacles=True, preserve_sampled_prediction=True
    )
    assert result.source_dynamic_obstacles == 1
    assert result.projected_obstacles == 1
    assert result.planner_relevant_obstacles == 0
    assert result.route_irrelevant_obstacles == 1
    assert result.scenario.obstacles == []

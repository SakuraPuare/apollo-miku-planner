from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "可视化")
from commonroad_adapter import _route, adapt_commonroad_xml  # noqa: E402


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
    result = adapt_commonroad_xml(MINIMAL_XML)
    assert result.benchmark_id == "unit-test"
    assert result.route_lanelet_ids == ("a", "b")
    assert result.projected_obstacles == 1
    assert result.skipped_obstacles == 0
    assert result.trajectory_states_used == 1
    assert result.scenario.s_max > result.scenario.ego.s0
    obstacle = result.scenario.obstacles[0]
    assert obstacle.s0 == pytest.approx(7.0)
    assert obstacle.l0 == pytest.approx(0.5)
    assert obstacle.vs == pytest.approx(3.0)
    assert obstacle.uncertainty_vs == pytest.approx(0.2)
    assert obstacle.uncertainty_vl == pytest.approx(0.2)


def test_commonroad_adapter_rejects_missing_route():
    with pytest.raises(ValueError, match="no successor route"):
        _route({"a": ("missing",), "b": ()}, "a", "b")

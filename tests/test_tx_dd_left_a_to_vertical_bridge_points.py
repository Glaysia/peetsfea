from __future__ import annotations

import math

import pytest

from peetsfea.backend.pyaedt.geometry.build_rx_dd import (
    _sheet_points_from_edge_pair,
    _tx_dd_xy_tools,
    _txdd_left_a_edge_from_points,
)
from peetsfea.backend.pyaedt.geometry.build import _edge_points_at_path_end


_Point3 = tuple[float, float, float]
_Edge2P = tuple[_Point3, _Point3]


def _legacy_sheet_points_from_edge_pair(*, dd_edge: _Edge2P, vertical_edge: _Edge2P) -> list[list[float]]:
    dd_edge_0, dd_edge_1 = dd_edge
    v_edge_0, v_edge_1 = vertical_edge
    same_pair_cost = math.dist(dd_edge_0, v_edge_0) + math.dist(dd_edge_1, v_edge_1)
    cross_pair_cost = math.dist(dd_edge_0, v_edge_1) + math.dist(dd_edge_1, v_edge_0)
    if cross_pair_cost < same_pair_cost:
        v_edge_0, v_edge_1 = v_edge_1, v_edge_0
    return [
        [dd_edge_0[0], dd_edge_0[1], dd_edge_0[2]],
        [dd_edge_1[0], dd_edge_1[1], dd_edge_1[2]],
        [v_edge_1[0], v_edge_1[1], v_edge_1[2]],
        [v_edge_0[0], v_edge_0[1], v_edge_0[2]],
    ]


@pytest.mark.parametrize(
    ("dd_edge", "vertical_edge"),
    [
        (((0.0, 1.0, 2.0), (0.0, 1.0, 8.0)), ((3.0, 1.0, 2.1), (3.0, 1.0, 7.9))),
        (((5.0, -2.0, 10.0), (5.0, -2.0, 14.0)), ((1.0, -2.0, 14.1), (1.0, -2.0, 10.1))),
    ],
)
def test_sheet_points_from_edge_pair_matches_legacy(dd_edge: _Edge2P, vertical_edge: _Edge2P) -> None:
    expected = _legacy_sheet_points_from_edge_pair(dd_edge=dd_edge, vertical_edge=vertical_edge)
    actual = _sheet_points_from_edge_pair(dd_edge=dd_edge, vertical_edge=vertical_edge)
    for exp_row, act_row in zip(expected, actual, strict=True):
        for exp_axis, act_axis in zip(exp_row, act_row, strict=True):
            assert act_axis == pytest.approx(exp_axis, abs=1e-9)


def test_txdd_left_a_edge_from_points_returns_expected_pair() -> None:
    points = {
        0: ((1.0, 2.0, 3.0), 0.5),
        1: ((1.0, 2.0, 6.0), 0.5),
    }
    edge = _txdd_left_a_edge_from_points(txdd_left_a_points=points)
    assert edge == (((1.0, 2.0, 3.0), (1.0, 2.0, 6.0)))


def test_txdd_left_a_edge_from_points_missing_layer_raises() -> None:
    points = {0: ((1.0, 2.0, 3.0), 0.5)}
    with pytest.raises(ValueError, match=r"layer points \[0,1\] were not captured"):
        _txdd_left_a_edge_from_points(txdd_left_a_points=points)


def test_txdd_left_a_edge_from_points_trace_mismatch_raises() -> None:
    points = {
        0: ((1.0, 2.0, 3.0), 0.5),
        1: ((1.0, 2.0, 6.0), 0.7),
    }
    with pytest.raises(ValueError, match=r"lower/upper A trace must match"):
        _txdd_left_a_edge_from_points(txdd_left_a_points=points)


def test_edge_points_at_path_end_matches_expected_a_edge_for_left_path() -> None:
    points = [[0.0, 0.0, 2.0], [1.0, 0.0, 2.0]]
    edge = _edge_points_at_path_end(points=points, trace=2.0)
    assert edge[0] == pytest.approx((1.0, 1.0, 2.0), abs=1e-9)
    assert edge[1] == pytest.approx((1.0, -1.0, 2.0), abs=1e-9)


def test_tx_dd_xy_tools_prefers_txdd_object_maps_over_group_objects() -> None:
    tools = _tx_dd_xy_tools(
        txdd_right_object_names={1: "coil_tx_dd_right_top", 0: "coil_tx_dd_right_bottom"},
        txdd_left_object_names={1: "coil_tx_dd_left_top", 0: "coil_tx_dd_left_bottom"},
        live_object_names={
            "coil_tx_dd_right_top",
            "coil_tx_dd_right_bottom",
            "coil_tx_dd_left_top",
            "coil_tx_dd_left_bottom",
        },
        group_objects={
            "tx_dd": ["bridge_tx_dd_to_tx_vertical", "bridge_tx_dd_left_a_to_tx_vertical"],
            "tx_vertical": ["bridge_tx_dd_left_a_to_tx_vertical"],
            "rx_dd": [],
        },
    )
    assert tools == [
        "coil_tx_dd_left_bottom",
        "coil_tx_dd_left_top",
        "coil_tx_dd_right_bottom",
        "coil_tx_dd_right_top",
    ]


def test_tx_dd_xy_tools_falls_back_to_group_when_maps_empty() -> None:
    tools = _tx_dd_xy_tools(
        txdd_right_object_names={},
        txdd_left_object_names={},
        live_object_names={"coil_tx_dd_a", "coil_tx_dd_b"},
        group_objects={"tx_dd": ["coil_tx_dd_a", "coil_tx_dd_a", "coil_tx_dd_b"], "tx_vertical": [], "rx_dd": []},
    )
    assert tools == ["coil_tx_dd_a", "coil_tx_dd_b"]


def test_tx_dd_xy_tools_filters_dead_names_from_maps() -> None:
    tools = _tx_dd_xy_tools(
        txdd_right_object_names={0: "right_live", 1: "right_dead"},
        txdd_left_object_names={0: "left_live", 1: "left_dead"},
        live_object_names={"right_live", "left_live"},
        group_objects={"tx_dd": ["fallback_live"], "tx_vertical": [], "rx_dd": []},
    )
    assert tools == ["left_live", "right_live"]


def test_tx_dd_xy_tools_returns_empty_when_all_map_and_fallback_names_dead() -> None:
    tools = _tx_dd_xy_tools(
        txdd_right_object_names={0: "right_dead", 1: "right_dead_2"},
        txdd_left_object_names={0: "left_dead", 1: "left_dead_2"},
        live_object_names=set(),
        group_objects={"tx_dd": ["fallback_dead"], "tx_vertical": [], "rx_dd": []},
    )
    assert tools == []

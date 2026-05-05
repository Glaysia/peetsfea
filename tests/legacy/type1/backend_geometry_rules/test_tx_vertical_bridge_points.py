from __future__ import annotations

import pytest

from peetsfea.legacy.type1.backend.pyaedt.geometry.build import (
    _edge_points_at_tx_vertical_opposite_terminal,
    _edge_points_at_tx_vertical_terminal,
    _edge_points_at_yz_terminal,
    _tx_vertical_bridge_edges_from_node,
)


_Point3 = tuple[float, float, float]
_Edge2P = tuple[_Point3, _Point3]


def test_tx_vertical_bridge_edges_for_zx_mode_use_actual_terminal_edges() -> None:
    points = [
        [10.0, 0.0, 9.0],
        [20.0, 0.0, 9.0],
        [20.0, 0.0, 1.0],
    ]
    expected_out = _edge_points_at_tx_vertical_terminal(points=points, trace=1.0, plane="ZX", cu_thickness=0.2)
    expected_in = _edge_points_at_tx_vertical_opposite_terminal(points=points, trace=1.0, plane="ZX", cu_thickness=0.2)
    actual_out, actual_in = _tx_vertical_bridge_edges_from_node(
        start_xyz=(10.0, 0.0, 9.0),
        end_xyz=(20.0, 0.0, 1.0),
        trace=1.0,
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(30.0, 10.0, 20.0),
        plane="ZX",
        points=points,
        cu_thickness=0.2,
    )
    for expected_edge, actual_edge in ((expected_out, actual_out), (expected_in, actual_in)):
        for expected_point, actual_point in zip(expected_edge, actual_edge, strict=True):
            for expected_axis, actual_axis in zip(expected_point, actual_point, strict=True):
                assert actual_axis == pytest.approx(expected_axis, abs=1e-9)


def test_edge_points_at_yz_terminal_use_actual_terminal_cross_section() -> None:
    actual = _edge_points_at_yz_terminal(
        terminal_xyz=(5.0, 6.0, 39.5),
        neighbor_xyz=(5.0, 105.0, 39.5),
        trace=1.0,
    )

    assert actual == ((5.0, 6.0, 39.0), (5.0, 6.0, 40.0))


def test_tx_vertical_bridge_edges_for_yz_mode_use_start_and_end_terminals() -> None:
    points = [
        [5.0, 8.0, 2.5],
        [5.0, 103.0, 2.5],
        [5.0, 103.0, 37.5],
        [5.0, 6.0, 37.5],
        [5.0, 6.0, 0.5],
        [5.0, 105.0, 0.5],
        [5.0, 105.0, 39.5],
        [5.0, 6.0, 39.5],
    ]

    actual_out, actual_in = _tx_vertical_bridge_edges_from_node(
        start_xyz=(5.0, 8.0, 2.5),
        end_xyz=(5.0, 6.0, 39.5),
        trace=1.0,
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(10.0, 110.0, 50.0),
        plane="YZ",
        points=points,
        cu_thickness=0.2,
    )

    assert actual_out == ((5.0, 8.0, 2.0), (5.0, 8.0, 3.0))
    assert actual_in == ((5.0, 6.0, 39.0), (5.0, 6.0, 40.0))


def test_tx_vertical_global_selection_keys_choose_max_for_right_and_min_for_left() -> None:
    candidates = [
        (3.0, "tx_vertical_0", 2, ((30.0, 0.0, 0.0), (30.0, 0.0, 1.0)), ((31.0, 0.0, 0.0), (31.0, 0.0, 1.0))),
        (-2.0, "tx_vertical_0", 1, ((20.0, 0.0, 0.0), (20.0, 0.0, 1.0)), ((21.0, 0.0, 0.0), (21.0, 0.0, 1.0))),
        (1.0, "tx_vertical_0", 0, ((10.0, 0.0, 0.0), (10.0, 0.0, 1.0)), ((11.0, 0.0, 0.0), (11.0, 0.0, 1.0))),
    ]
    selected_right_key: tuple[float, str, int] | None = None
    selected_left_key: tuple[float, str, int] | None = None
    selected_right: _Edge2P | None = None  # terminal edge for max y_center
    selected_left: _Edge2P | None = None  # opposite edge for min y_center
    for y_center, board_id, instance_index, right_edge, left_edge in candidates:
        right_key = (-y_center, board_id, instance_index)
        left_key = (y_center, board_id, instance_index)
        if selected_right_key is None or right_key < selected_right_key:
            selected_right_key = right_key
            selected_right = right_edge
        if selected_left_key is None or left_key < selected_left_key:
            selected_left_key = left_key
            selected_left = left_edge

    assert selected_right_key == (-3.0, "tx_vertical_0", 2)
    assert selected_left_key == (-2.0, "tx_vertical_0", 1)
    assert selected_right == ((30.0, 0.0, 0.0), (30.0, 0.0, 1.0))
    assert selected_left == ((21.0, 0.0, 0.0), (21.0, 0.0, 1.0))

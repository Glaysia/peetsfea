from __future__ import annotations

import math

import pytest

from peetsfea.backend.pyaedt.geometry.build import _tx_vertical_bridge_edges_from_node


_Point3 = tuple[float, float, float]
_Edge2P = tuple[_Point3, _Point3]


def _legacy_bridge_edges_from_node(
    *,
    start_xyz: _Point3,
    end_xyz: _Point3,
    trace: float,
    tx_vertical_region_min: _Point3,
    tx_vertical_region_max: _Point3,
) -> tuple[_Edge2P, _Edge2P]:
    half = trace / 2.0
    min_x_allowed = tx_vertical_region_min[0] + half
    max_x_allowed = tx_vertical_region_max[0] - half
    if min_x_allowed > max_x_allowed:
        raise ValueError(
            "tx_vertical bridge x-margin exceeds region width "
            f"(min_x_allowed={min_x_allowed}, max_x_allowed={max_x_allowed}, bridge_trace={trace})"
        )
    source_dx = end_xyz[0] - start_xyz[0]
    source_anchor_x = start_xyz[0] if abs(source_dx) <= 1e-9 else start_xyz[0] + math.copysign(half, source_dx)
    target_dx = start_xyz[0] - end_xyz[0]
    target_anchor_x = end_xyz[0] if abs(target_dx) <= 1e-9 else end_xyz[0] + math.copysign(half, target_dx)
    source_bridge_x = min(max(source_anchor_x, min_x_allowed), max_x_allowed)
    target_bridge_x = min(max(target_anchor_x, min_x_allowed), max_x_allowed)
    source_bridge_x = min(max(source_bridge_x, min_x_allowed), max_x_allowed)
    target_bridge_x = min(max(target_bridge_x + trace, min_x_allowed), max_x_allowed)
    bridge_out_edge: _Edge2P = (
        (source_bridge_x, start_xyz[1], start_xyz[2] - half),
        (source_bridge_x, start_xyz[1], start_xyz[2] + half),
    )
    bridge_in_edge: _Edge2P = (
        (target_bridge_x, end_xyz[1], end_xyz[2] - half),
        (target_bridge_x, end_xyz[1], end_xyz[2] + half),
    )
    return bridge_out_edge, bridge_in_edge


@pytest.mark.parametrize(
    ("start_xyz", "end_xyz", "trace", "region_min", "region_max"),
    [
        ((1.0, 10.0, 20.0), (5.0, 10.0, 20.0), 1.2, (0.0, -100.0, 0.0), (10.0, 100.0, 50.0)),
        ((4.0, -3.0, 7.0), (4.0, -3.0, 9.0), 0.8, (0.0, -50.0, 0.0), (8.0, 50.0, 20.0)),
        ((-5.0, 2.5, 11.0), (0.2, 2.5, 11.0), 1.0, (0.0, -30.0, 0.0), (3.0, 30.0, 20.0)),
        ((2.7, 0.0, 15.0), (2.9, 0.0, 15.0), 1.4, (0.0, -10.0, 0.0), (3.2, 10.0, 30.0)),
    ],
)
def test_tx_vertical_bridge_edges_match_legacy_formula(
    start_xyz: _Point3,
    end_xyz: _Point3,
    trace: float,
    region_min: _Point3,
    region_max: _Point3,
) -> None:
    expected_out, expected_in = _legacy_bridge_edges_from_node(
        start_xyz=start_xyz,
        end_xyz=end_xyz,
        trace=trace,
        tx_vertical_region_min=region_min,
        tx_vertical_region_max=region_max,
    )
    actual_out, actual_in = _tx_vertical_bridge_edges_from_node(
        start_xyz=start_xyz,
        end_xyz=end_xyz,
        trace=trace,
        tx_vertical_region_min=region_min,
        tx_vertical_region_max=region_max,
    )
    for expected_edge, actual_edge in ((expected_out, actual_out), (expected_in, actual_in)):
        for expected_point, actual_point in zip(expected_edge, actual_edge, strict=True):
            for expected_axis, actual_axis in zip(expected_point, actual_point, strict=True):
                assert actual_axis == pytest.approx(expected_axis, abs=1e-9)


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

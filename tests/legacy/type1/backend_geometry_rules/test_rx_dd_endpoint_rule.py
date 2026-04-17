from __future__ import annotations

import pytest

from peetsfea.legacy.type1.backend.pyaedt.geometry.rules.placement_rules import (
    _build_rxdd_right_points_A_to_d_cw,
    _current_direction_from_xy_points,
    _instance_side,
    _validate_rxdd_single_layer_count,
)


def test_build_rxdd_right_points_A_to_d_cw_is_clockwise() -> None:
    points = _build_rxdd_right_points_A_to_d_cw(
        turns=3,
        outer_x=120.0,
        outer_y=80.0,
        trace=1.2,
        gap=0.3,
    )
    assert _current_direction_from_xy_points(points) == "cw"


def test_rx_world_y_mirror_from_right_path_is_counter_clockwise() -> None:
    right_points = _build_rxdd_right_points_A_to_d_cw(
        turns=2,
        outer_x=100.0,
        outer_y=60.0,
        trace=1.0,
        gap=0.25,
    )
    x_const = 42.0
    axis_y = 10.0
    pair_offset = 30.0
    z_center = 200.0

    right_world = [[x_const, axis_y + pair_offset + point[0], z_center + point[1]] for point in right_points]
    left_world = [[point[0], (2.0 * axis_y) - point[1], point[2]] for point in right_world]

    assert len(left_world) == len(right_world)
    for right, left in zip(right_world, left_world, strict=True):
        assert left[0] == pytest.approx(right[0], abs=1e-9)
        assert left[1] == pytest.approx((2.0 * axis_y) - right[1], abs=1e-9)
        assert left[2] == pytest.approx(right[2], abs=1e-9)

    right_projected = [[point[1], point[2], 0.0] for point in right_world]
    left_projected = [[point[1], point[2], 0.0] for point in left_world]
    assert _current_direction_from_xy_points(right_projected) == "cw"
    assert _current_direction_from_xy_points(left_projected) == "ccw"


@pytest.mark.parametrize("instance_count", [1, 3, 4])
def test_validate_rxdd_single_layer_count_rejects_non_two(instance_count: int) -> None:
    with pytest.raises(ValueError, match=r"only instance_count=2 is supported"):
        _validate_rxdd_single_layer_count(instance_count)


def test_validate_rxdd_single_layer_count_accepts_two() -> None:
    _validate_rxdd_single_layer_count(2)


def test_rx_side_axis_convention_matches_plus_x_view() -> None:
    left_side = _instance_side("rx_dd", (0.0, -1.0, 0.0))
    right_side = _instance_side("rx_dd", (0.0, 1.0, 0.0))
    assert left_side == "left"
    assert right_side == "right"

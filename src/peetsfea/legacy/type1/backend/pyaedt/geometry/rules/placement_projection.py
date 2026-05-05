from __future__ import annotations

from typing import Literal, cast

from .placement_geometry import _current_direction_from_xy_points
from .placement_types import _YzDdPairPlacement
from .spiral_points import (
    _build_rect_spiral_centerline_absolute,
    _map_xy_points_to_yz,
    _mirror_points_about_y_axis_line,
)


def _build_rxdd_right_points_A_to_d_cw(
    *,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
    corner_mode: int = 0,
) -> list[list[float]]:
    points = [
        list(point)
        for point in _build_rect_spiral_centerline_absolute(
            turns=turns,
            outer_x=outer_x,
            outer_y=outer_y,
            trace=trace,
            gap=gap,
            z=0.0,
            corner_mode=corner_mode,
        )
    ]
    direction = _current_direction_from_xy_points(points)
    if direction != "cw":
        raise ValueError(
            "rx_dd right endpoint contract violation: A->d path must be clockwise "
            f"(actual_direction={direction})"
        )
    return points


def _build_yz_dd_pair_from_right_local(
    *,
    right_local_points: list[list[float]],
    x_const: float,
    axis_y: float,
    z_center: float,
    pair_center_distance: float,
    expected_right_direction: Literal["cw", "ccw"] = "cw",
    expected_left_direction: Literal["cw", "ccw"] = "ccw",
) -> list[_YzDdPairPlacement]:
    pair_half_distance = pair_center_distance / 2.0
    right_points = _map_xy_points_to_yz(
        right_local_points,
        x_const=x_const,
        y_center=axis_y + pair_half_distance,
        z_center=z_center,
    )
    left_points = _mirror_points_about_y_axis_line(right_points, axis_y=axis_y)
    right_projected = [[point[1], point[2], 0.0] for point in right_points]
    left_projected = [[point[1], point[2], 0.0] for point in left_points]
    right_direction = _current_direction_from_xy_points(right_projected)
    left_direction = _current_direction_from_xy_points(left_projected)
    if right_direction != expected_right_direction:
        raise ValueError(
            "YZ DD pair right-half winding contract violation "
            f"(actual_direction={right_direction}, expected={expected_right_direction})"
        )
    if left_direction != expected_left_direction:
        raise ValueError(
            "YZ DD pair left-half winding contract violation "
            f"(actual_direction={left_direction}, expected={expected_left_direction})"
        )
    right_direction_final = cast(Literal["cw", "ccw"], right_direction)
    left_direction_final = cast(Literal["cw", "ccw"], left_direction)
    return [
        ("left", left_points, axis_y - pair_half_distance, left_direction_final),
        ("right", right_points, axis_y + pair_half_distance, right_direction_final),
    ]


def _build_yz_dd_half_from_local(
    *,
    local_points: list[list[float]],
    x_const: float,
    axis_y: float,
    z_center: float,
    pair_center_distance: float,
    side: Literal["left", "right"],
    expected_direction: Literal["cw", "ccw"],
) -> tuple[list[list[float]], float, Literal["cw", "ccw"]]:
    pair_half_distance = pair_center_distance / 2.0
    side_sign = 1.0 if side == "right" else -1.0
    world_points = [
        [
            x_const,
            axis_y + (side_sign * pair_half_distance) + (side_sign * point[0]),
            z_center + point[1],
        ]
        for point in local_points
    ]
    projected = [[point[1], point[2], 0.0] for point in world_points]
    direction = _current_direction_from_xy_points(projected)
    if direction != expected_direction:
        raise ValueError(
            "YZ DD half winding contract violation "
            f"(side={side}, actual_direction={direction}, expected={expected_direction})"
        )
    return (
        world_points,
        axis_y + (side_sign * pair_half_distance),
        cast(Literal["cw", "ccw"], direction),
    )

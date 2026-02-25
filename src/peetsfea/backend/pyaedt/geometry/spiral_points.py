from __future__ import annotations

from typing import cast

from peetsfea.types.manifest import CadProbe

_Point2 = tuple[float, float]
_Point3 = tuple[float, float, float]

def _build_rect_spiral_centerline_absolute(turns: int, outer_x: float, outer_y: float, trace: float, gap: float, z: float) -> list[_Point3]:
    if turns < 1:
        raise ValueError("turns must be >= 1")
    if trace <= 0:
        raise ValueError("trace must be > 0")
    if gap < 0:
        raise ValueError("gap must be >= 0")

    pitch = trace + gap
    half_trace = trace / 2.0

    left = -(outer_x / 2.0) + half_trace
    right = (outer_x / 2.0) - half_trace
    top = (outer_y / 2.0) - half_trace
    bottom = -(outer_y / 2.0) + half_trace

    if left >= right or bottom >= top:
        raise ValueError("centerline outer width must be > 0")

    points: list[_Point3] = []
    for turn_idx in range(turns):
        left_k = left + (turn_idx * pitch)
        right_k = right - (turn_idx * pitch)
        top_k = top - (turn_idx * pitch)
        bottom_k = bottom + (turn_idx * pitch)

        if left_k >= right_k or bottom_k >= top_k:
            raise ValueError("invalid spiral dimensions for requested turns")

        if turn_idx == 0:
            points.append((left_k, top_k, z))

        points.append((right_k, top_k, z))
        points.append((right_k, bottom_k, z))
        points.append((left_k, bottom_k, z))

        if turn_idx < turns - 1:
            next_top = top - ((turn_idx + 1) * pitch)
            next_left = left + ((turn_idx + 1) * pitch)
            points.append((left_k, next_top, z))
            points.append((next_left, next_top, z))

    return points


def _build_square_spiral_centerline_absolute(turns: int, outer: float, trace: float, gap: float, z: float) -> list[_Point3]:
    return _build_rect_spiral_centerline_absolute(turns=turns, outer_x=outer, outer_y=outer, trace=trace, gap=gap, z=z)


def _square_spiral_points(turns: int, outer: float, trace: float, gap: float, z: float) -> list[list[float]]:
    return [list(p) for p in _build_square_spiral_centerline_absolute(turns=turns, outer=outer, trace=trace, gap=gap, z=z)]


def _translate_points(points: list[list[float]], dx: float, dy: float, dz: float) -> list[list[float]]:
    return [[point[0] + dx, point[1] + dy, point[2] + dz] for point in points]


def _map_xy_points_to_yz(points: list[list[float]], *, x_const: float, y_center: float, z_center: float) -> list[list[float]]:
    return [[x_const, y_center + point[0], z_center + point[1]] for point in points]


def _map_xy_points_to_zx(points: list[list[float]], *, x_center: float, y_const: float, z_center: float) -> list[list[float]]:
    return [[x_center + point[0], y_const, z_center + point[1]] for point in points]


def _mirror_xy_points_about_x_axis(points: list[list[float]]) -> list[list[float]]:
    # Mirror around local X-axis (y -> -y) so paired DD coils have opposite winding.
    return [[point[0], -point[1], point[2]] for point in points]


def _mirror_points_about_y_axis_line(points: list[list[float]], *, axis_y: float) -> list[list[float]]:
    # Mirror around world X-axis line at Y=axis_y (equivalent to y -> 2*axis_y - y).
    return [[point[0], (2.0 * axis_y) - point[1], point[2]] for point in points]


def _dd_instance_points(base_points: list[list[float]], *, mirror_winding: bool) -> list[list[float]]:
    if not mirror_winding:
        return base_points
    return _mirror_xy_points_about_x_axis(base_points)



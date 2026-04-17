from __future__ import annotations

import math
from typing import cast

from peetsfea.types.manifest import CadProbe

_Point2 = tuple[float, float]
_Point3 = tuple[float, float, float]


def _vector_norm(dx: float, dy: float, dz: float) -> float:
    return math.sqrt((dx * dx) + (dy * dy) + (dz * dz))


def _apply_corner_mode_to_polyline(
    points: list[_Point3],
    *,
    corner_mode: int,
    trace: float,
    gap: float,
) -> list[_Point3]:
    if corner_mode == 0:
        return list(points)
    if corner_mode != 1:
        raise ValueError(f"corner_mode must be 0 or 1 (actual={corner_mode})")
    if trace <= 0.0:
        raise ValueError(f"trace must be > 0 for corner processing (actual={trace})")
    if gap < 0.0:
        raise ValueError(f"gap must be >= 0 for corner processing (actual={gap})")
    if len(points) < 3:
        return list(points)

    eps = 1e-9
    trim_target = min(trace, (trace + gap) / 2.0)
    if trim_target <= eps:
        return list(points)

    shaped: list[_Point3] = [points[0]]
    for index in range(1, len(points) - 1):
        prev_point = points[index - 1]
        curr_point = points[index]
        next_point = points[index + 1]

        in_dx = curr_point[0] - prev_point[0]
        in_dy = curr_point[1] - prev_point[1]
        in_dz = curr_point[2] - prev_point[2]
        out_dx = next_point[0] - curr_point[0]
        out_dy = next_point[1] - curr_point[1]
        out_dz = next_point[2] - curr_point[2]

        in_len = _vector_norm(in_dx, in_dy, in_dz)
        out_len = _vector_norm(out_dx, out_dy, out_dz)
        if in_len <= eps or out_len <= eps:
            raise ValueError("corner_mode blunt cannot process zero-length segment")

        in_dir = (in_dx / in_len, in_dy / in_len, in_dz / in_len)
        out_dir = (out_dx / out_len, out_dy / out_len, out_dz / out_len)
        dot = (in_dir[0] * out_dir[0]) + (in_dir[1] * out_dir[1]) + (in_dir[2] * out_dir[2])
        if abs(abs(dot) - 1.0) <= eps:
            shaped.append(curr_point)
            continue

        trim = min(trim_target, (in_len / 2.0) - eps, (out_len / 2.0) - eps)
        if trim <= eps:
            shaped.append(curr_point)
            continue

        entry_point: _Point3 = (
            curr_point[0] - (in_dir[0] * trim),
            curr_point[1] - (in_dir[1] * trim),
            curr_point[2] - (in_dir[2] * trim),
        )
        exit_point: _Point3 = (
            curr_point[0] + (out_dir[0] * trim),
            curr_point[1] + (out_dir[1] * trim),
            curr_point[2] + (out_dir[2] * trim),
        )
        if _vector_norm(
            entry_point[0] - shaped[-1][0],
            entry_point[1] - shaped[-1][1],
            entry_point[2] - shaped[-1][2],
        ) > eps:
            shaped.append(entry_point)
        if _vector_norm(
            exit_point[0] - shaped[-1][0],
            exit_point[1] - shaped[-1][1],
            exit_point[2] - shaped[-1][2],
        ) > eps:
            shaped.append(exit_point)

    if _vector_norm(
        points[-1][0] - shaped[-1][0],
        points[-1][1] - shaped[-1][1],
        points[-1][2] - shaped[-1][2],
    ) > eps:
        shaped.append(points[-1])
    return shaped


def _apply_corner_mode_to_polyline_lists(
    points: list[list[float]],
    *,
    corner_mode: int,
    trace: float,
    gap: float,
) -> list[list[float]]:
    return [
        [point[0], point[1], point[2]]
        for point in _apply_corner_mode_to_polyline(
            [cast(_Point3, (float(p[0]), float(p[1]), float(p[2]))) for p in points],
            corner_mode=corner_mode,
            trace=trace,
            gap=gap,
        )
    ]


def _build_rect_spiral_centerline_absolute(
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
    z: float,
    *,
    corner_mode: int = 0,
) -> list[_Point3]:
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

    return _apply_corner_mode_to_polyline(points, corner_mode=corner_mode, trace=trace, gap=gap)


def _build_square_spiral_centerline_absolute(
    turns: int,
    outer: float,
    trace: float,
    gap: float,
    z: float,
    *,
    corner_mode: int = 0,
) -> list[_Point3]:
    return _build_rect_spiral_centerline_absolute(
        turns=turns,
        outer_x=outer,
        outer_y=outer,
        trace=trace,
        gap=gap,
        z=z,
        corner_mode=corner_mode,
    )


def _square_spiral_points(
    turns: int,
    outer: float,
    trace: float,
    gap: float,
    z: float,
    *,
    corner_mode: int = 0,
) -> list[list[float]]:
    return [
        list(p)
        for p in _build_square_spiral_centerline_absolute(
            turns=turns,
            outer=outer,
            trace=trace,
            gap=gap,
            z=z,
            corner_mode=corner_mode,
        )
    ]


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

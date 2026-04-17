from __future__ import annotations

import math
from typing import Literal, cast

from .debug_checks import _compute_pitch_checks
from .placement_types import PlacementKernelInput, PlacementKernelOutput, _Point2, _Point3


def _axis_aligned_segments_intersect_2d(a0: _Point2, a1: _Point2, b0: _Point2, b1: _Point2, eps: float) -> bool:
    ax0, ay0 = a0
    ax1, ay1 = a1
    bx0, by0 = b0
    bx1, by1 = b1
    a_vertical = abs(ax0 - ax1) <= eps
    b_vertical = abs(bx0 - bx1) <= eps
    if a_vertical and b_vertical:
        if abs(ax0 - bx0) > eps:
            return False
        a_min, a_max = sorted((ay0, ay1))
        b_min, b_max = sorted((by0, by1))
        return max(a_min, b_min) <= (min(a_max, b_max) + eps)
    if (not a_vertical) and (not b_vertical):
        if abs(ay0 - by0) > eps:
            return False
        a_min, a_max = sorted((ax0, ax1))
        b_min, b_max = sorted((bx0, bx1))
        return max(a_min, b_min) <= (min(a_max, b_max) + eps)
    if a_vertical:
        v_x = ax0
        v_min, v_max = sorted((ay0, ay1))
        h_y = by0
        h_min, h_max = sorted((bx0, bx1))
    else:
        v_x = bx0
        v_min, v_max = sorted((by0, by1))
        h_y = ay0
        h_min, h_max = sorted((ax0, ax1))
    return (h_min - eps) <= v_x <= (h_max + eps) and (v_min - eps) <= h_y <= (v_max + eps)


def _orientation(a: _Point2, b: _Point2, c: _Point2, eps: float) -> int:
    value = ((b[0] - a[0]) * (c[1] - a[1])) - ((b[1] - a[1]) * (c[0] - a[0]))
    if abs(value) <= eps:
        return 0
    return 1 if value > 0.0 else -1


def _point_on_segment(a: _Point2, b: _Point2, p: _Point2, eps: float) -> bool:
    return (
        min(a[0], b[0]) - eps <= p[0] <= max(a[0], b[0]) + eps
        and min(a[1], b[1]) - eps <= p[1] <= max(a[1], b[1]) + eps
    )


def _segments_intersect_2d(a0: _Point2, a1: _Point2, b0: _Point2, b1: _Point2, eps: float) -> bool:
    oa = _orientation(a0, a1, b0, eps)
    ob = _orientation(a0, a1, b1, eps)
    oc = _orientation(b0, b1, a0, eps)
    od = _orientation(b0, b1, a1, eps)
    if oa != ob and oc != od:
        return True
    if oa == 0 and _point_on_segment(a0, a1, b0, eps):
        return True
    if ob == 0 and _point_on_segment(a0, a1, b1, eps):
        return True
    if oc == 0 and _point_on_segment(b0, b1, a0, eps):
        return True
    if od == 0 and _point_on_segment(b0, b1, a1, eps):
        return True
    return False


def _find_txdd_right_inner_c_index(base_points: list[list[float]]) -> int:
    bottom_right_candidates = [
        (idx, abs(point[0]), abs(point[1]))
        for idx, point in enumerate(base_points)
        if point[0] > 0.0 and point[1] < 0.0
    ]
    if not bottom_right_candidates:
        raise ValueError("tx_dd right endpoint contract violation: cannot locate inner bottom-right anchor for c->A")
    min_abs_x = min(candidate[1] for candidate in bottom_right_candidates)
    min_x_candidates = [candidate for candidate in bottom_right_candidates if abs(candidate[1] - min_abs_x) <= 1e-9]
    min_abs_y = min(candidate[2] for candidate in min_x_candidates)
    min_xy_candidates = [candidate for candidate in min_x_candidates if abs(candidate[2] - min_abs_y) <= 1e-9]
    return max(candidate[0] for candidate in min_xy_candidates)


def _build_txdd_right_points_c_to_a(
    *,
    base: list[list[float]],
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
) -> list[list[float]]:
    c_index = _find_txdd_right_inner_c_index(base)
    points = [point[:] for point in reversed(base[: c_index + 1])]
    upper_a = [
        -(outer_x + (trace + gap)) / 2.0 + (trace / 2.0),
        (outer_y + (trace + gap)) / 2.0 - (trace / 2.0),
        0.0,
    ]
    last = points[-1]
    if abs(last[0] - upper_a[0]) > 1e-9:
        points.append([upper_a[0], last[1], last[2]])
    if abs(points[-1][1] - upper_a[1]) > 1e-9:
        points.append([upper_a[0], upper_a[1], upper_a[2]])
    if len(points) < 2:
        raise ValueError("tx_dd right endpoint contract violation: c->A path is too short")
    return points


def _build_txdd_right_points_c_to_a_one_turn(
    *,
    base: list[list[float]],
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
) -> list[list[float]]:
    _ = base
    pitch = trace + gap
    left = -(outer_x / 2.0) + (trace / 2.0)
    right = (outer_x / 2.0) - (trace / 2.0)
    top = (outer_y / 2.0) - (trace / 2.0)
    bottom = -(outer_y / 2.0) + (trace / 2.0)
    aligned_upper_a = [
        -(outer_x + pitch) / 2.0 + (trace / 2.0),
        (outer_y + pitch) / 2.0 - (trace / 2.0),
        0.0,
    ]
    return [
        [right, bottom, 0.0],
        [right, top, 0.0],
        [left, top, 0.0],
        [aligned_upper_a[0], top, 0.0],
        aligned_upper_a,
    ]


def _build_txdd_right_points_a_to_d_one_turn(
    *,
    base: list[list[float]],
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
) -> list[list[float]]:
    _ = base
    pitch = trace + gap
    left = -(outer_x / 2.0) + (trace / 2.0)
    right = (outer_x / 2.0) - (trace / 2.0)
    top = (outer_y / 2.0) - (trace / 2.0)
    bottom = -(outer_y / 2.0) + (trace / 2.0)
    inner_left = left + pitch
    inner_top = top - pitch
    inner_bottom = bottom + pitch
    if inner_left < right and inner_bottom < inner_top:
        return [
            [left, top, 0.0],
            [left, bottom, 0.0],
            [right, bottom, 0.0],
            [right, inner_top, 0.0],
            [inner_left, inner_top, 0.0],
            [inner_left, inner_bottom, 0.0],
        ]
    raise ValueError(
        "tx_dd one-turn endpoint contract violation: compact one-turn geometry is unsupported "
        f"(outer_x={outer_x}, outer_y={outer_y}, trace={trace}, gap={gap})"
    )


def _build_txdd_right_points_a_to_d_multi_turn(*, base: list[list[float]]) -> list[list[float]]:
    mirrored_x = [[-point[0], point[1], point[2]] for point in base]
    outer_a = base[0]
    sentinel = object()
    a_index = next(
        (
            idx
            for idx, point in enumerate(mirrored_x)
            if abs(point[0] - outer_a[0]) <= 1e-9 and abs(point[1] - outer_a[1]) <= 1e-9
        ),
        sentinel,
    )
    if a_index is sentinel:
        raise ValueError("tx_dd right endpoint contract violation: cannot locate outer A anchor for A->D->...->d")
    resolved_a_index = cast(int, a_index)
    rotated = mirrored_x[resolved_a_index:] + mirrored_x[:resolved_a_index]
    c_index = _find_txdd_right_inner_c_index(rotated)
    d_index = c_index - 1
    if d_index < 1:
        raise ValueError("tx_dd right endpoint contract violation: A->D->...->d path is too short")
    return [point[:] for point in rotated[: d_index + 1]]


def _build_txdd_right_points_a_to_d(
    *,
    base: list[list[float]],
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
) -> list[list[float]]:
    if len(base) == 4:
        return _build_txdd_right_points_a_to_d_one_turn(
            base=base,
            outer_x=outer_x,
            outer_y=outer_y,
            trace=trace,
            gap=gap,
        )
    return _build_txdd_right_points_a_to_d_multi_turn(base=base)


def _validate_txdd_right_points(
    points: list[list[float]],
    *,
    trace: float,
    gap: float,
    corner_mode: int = 0,
) -> None:
    if len(points) < 2:
        raise ValueError("tx_dd right endpoint contract violation: generated centerline is too short")
    eps = 1e-9
    for idx in range(len(points) - 1):
        p0 = points[idx]
        p1 = points[idx + 1]
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        if abs(dx) <= eps and abs(dy) <= eps:
            raise ValueError("tx_dd right endpoint contract violation: zero-length segment generated")
        if corner_mode == 0 and abs(dx) > eps and abs(dy) > eps:
            raise ValueError("tx_dd right endpoint contract violation: non-axis-aligned segment generated")
    for idx in range(1, len(points) - 1):
        p_prev = points[idx - 1]
        p_curr = points[idx]
        p_next = points[idx + 1]
        vx1 = p_curr[0] - p_prev[0]
        vy1 = p_curr[1] - p_prev[1]
        vx2 = p_next[0] - p_curr[0]
        vy2 = p_next[1] - p_curr[1]
        if abs(vx1 + vx2) <= eps and abs(vy1 + vy2) <= eps:
            raise ValueError("tx_dd right endpoint contract violation: immediate backtracking segment generated")
    segments: list[tuple[_Point2, _Point2]] = [
        ((points[idx][0], points[idx][1]), (points[idx + 1][0], points[idx + 1][1]))
        for idx in range(len(points) - 1)
    ]
    for idx in range(len(segments)):
        for jdx in range(idx + 1, len(segments)):
            if jdx <= idx + 1:
                continue
            a0, a1 = segments[idx]
            b0, b1 = segments[jdx]
            if _segments_intersect_2d(a0, a1, b0, b1, eps):
                raise ValueError(
                    "tx_dd right endpoint contract violation: non-adjacent self-crossing segment generated"
                )
    if corner_mode == 0:
        tuple_points = [cast(_Point3, (float(p[0]), float(p[1]), float(p[2]))) for p in points]
        pitch_checks = _compute_pitch_checks(tuple_points, trace=trace, gap=gap, eps=1e-6)
        if any(check["delta"] > 1e-6 for check in pitch_checks):
            raise ValueError("tx_dd right endpoint contract violation: pitch consistency check failed")


def _edge_points_from_terminal(input_value: PlacementKernelInput) -> PlacementKernelOutput:
    points = input_value.points
    trace = input_value.trace
    terminal = input_value.terminal
    if len(points) < 2:
        raise ValueError("Cannot compute tx_dd terminal edge from path with fewer than 2 points")
    if trace <= 0.0:
        raise ValueError(f"tx_dd terminal edge trace must be > 0 (actual={trace})")
    if terminal == "start":
        terminal_point = points[0]
        neighbor_point = points[1]
    else:
        terminal_point = points[-1]
        neighbor_point = points[-2]
    dx = terminal_point[0] - neighbor_point[0]
    dy = terminal_point[1] - neighbor_point[1]
    seg_len = math.hypot(dx, dy)
    if seg_len <= 1e-12:
        raise ValueError("Cannot compute tx_dd terminal edge from zero-length terminal segment")
    nx = -dy / seg_len
    ny = dx / seg_len
    half_trace = trace / 2.0
    p0: _Point3 = (
        terminal_point[0] + (nx * half_trace),
        terminal_point[1] + (ny * half_trace),
        terminal_point[2],
    )
    p1: _Point3 = (
        terminal_point[0] - (nx * half_trace),
        terminal_point[1] - (ny * half_trace),
        terminal_point[2],
    )
    return PlacementKernelOutput(edge=(p0, p1))


def _edge_points_at_xy_terminal(
    *,
    points: list[list[float]],
    trace: float,
    terminal: Literal["start", "end"],
) -> tuple[_Point3, _Point3]:
    return _edge_points_from_terminal(
        PlacementKernelInput(points=points, trace=trace, terminal=terminal)
    ).edge


def _required_pair_spacing_mm(kind: Literal["tx_dd", "rx_dd"], outer_x: float, outer_y: float) -> float:
    if kind == "tx_dd":
        return outer_y
    return outer_x


def _current_direction_from_xy_points(points: list[list[float]], *, eps: float = 1e-9) -> Literal["cw", "ccw"]:
    if len(points) < 3:
        raise ValueError("cannot determine current direction from fewer than 3 points")
    for idx in range(1, len(points) - 1):
        vx1 = points[idx][0] - points[idx - 1][0]
        vy1 = points[idx][1] - points[idx - 1][1]
        vx2 = points[idx + 1][0] - points[idx][0]
        vy2 = points[idx + 1][1] - points[idx][1]
        cross = (vx1 * vy2) - (vy1 * vx2)
        if abs(cross) <= eps:
            continue
        return "ccw" if cross > 0.0 else "cw"
    raise ValueError("cannot determine current direction from collinear points")


def _max_feasible_turns(outer: float, trace: float, gap: float) -> int:
    pitch = trace + gap
    if pitch <= 0:
        return 0
    raw = (outer + (2.0 * gap)) / (2.0 * pitch)
    max_turns = int(math.floor(raw - 1e-12))
    return max(0, max_turns)

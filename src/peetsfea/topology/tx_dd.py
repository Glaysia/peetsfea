from __future__ import annotations

import math
from collections.abc import Iterator, Sequence
from typing import Literal

from peetsfea.types.runtime_selection import TerminalLabel

Point3 = tuple[float, float, float]
Edge2P = tuple[Point3, Point3]


def txdd_instance_count_from_layer_count(layer_count: int) -> int:
    if layer_count == 1:
        return 2
    if layer_count == 2:
        return 4
    raise ValueError(f"tx_dd layer_count must be 1 or 2 (actual={layer_count})")


def txdd_layer_count_from_instance_count(instance_count: int) -> int:
    if instance_count == 2:
        return 1
    if instance_count == 4:
        return 2
    raise ValueError(f"tx_dd instance_count must be 2 or 4 (actual={instance_count})")


def txdd_right_terminal_labels(
    *,
    layer_count: int | None = None,
    instance_count: int | None = None,
    layer_index: int | None,
) -> tuple[TerminalLabel, TerminalLabel]:
    resolved_layer_count, _ = _resolve_txdd_counts(layer_count=layer_count, instance_count=instance_count)
    if resolved_layer_count == 1:
        return "D", "d"
    if layer_index not in (0, 1):
        raise ValueError(
            "tx_dd right terminal label contract violation: layer index must be 0 or 1 for layer_count=2 "
            f"(actual={layer_index})"
        )
    if layer_index == 0:
        return "c", "A"
    return "A", "d"


def _resolve_txdd_counts(*, layer_count: int | None, instance_count: int | None) -> tuple[int, int]:
    if layer_count:
        if layer_count not in (1, 2):
            raise ValueError(f"tx_dd layer_count must be 1 or 2 (actual={layer_count})")
        resolved_instance_count = txdd_instance_count_from_layer_count(layer_count)
        if instance_count and instance_count != resolved_instance_count:
            raise ValueError(
                "tx_dd layer_count/instance_count mismatch "
                f"(layer_count={layer_count}, instance_count={instance_count}, "
                f"expected_instance_count={resolved_instance_count})"
            )
        return layer_count, resolved_instance_count
    if not instance_count:
        raise ValueError("tx_dd layer_count or instance_count must be provided")
    return txdd_layer_count_from_instance_count(instance_count), instance_count


def iter_txdd_slots(layer_count: int) -> Iterator[tuple[int, Literal["left", "right"], int]]:
    _ = txdd_instance_count_from_layer_count(layer_count)
    for layer_index in range(layer_count):
        base_instance = layer_index * 2
        yield layer_index, "left", base_instance
        yield layer_index, "right", base_instance + 1


def build_rect_spiral_centerline_absolute(
    *,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
    z: float,
) -> list[Point3]:
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

    points: list[Point3] = []
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


def extend_endpoints(points: Sequence[Point3], *, extension: float) -> list[Point3]:
    if extension <= 0.0 or len(points) < 2:
        return list(points)
    extended = list(points)
    start = list(extended[0])
    start_next = extended[1]
    start_dx = start[0] - start_next[0]
    start_dy = start[1] - start_next[1]
    start_dz = start[2] - start_next[2]
    start_len = math.sqrt((start_dx * start_dx) + (start_dy * start_dy) + (start_dz * start_dz))
    if start_len > 0.0:
        start[0] += (start_dx / start_len) * extension
        start[1] += (start_dy / start_len) * extension
        start[2] += (start_dz / start_len) * extension
    end = list(extended[-1])
    end_prev = extended[-2]
    end_dx = end[0] - end_prev[0]
    end_dy = end[1] - end_prev[1]
    end_dz = end[2] - end_prev[2]
    end_len = math.sqrt((end_dx * end_dx) + (end_dy * end_dy) + (end_dz * end_dz))
    if end_len > 0.0:
        end[0] += (end_dx / end_len) * extension
        end[1] += (end_dy / end_len) * extension
        end[2] += (end_dz / end_len) * extension
    out = extended[:]
    out[0] = (start[0], start[1], start[2])
    out[-1] = (end[0], end[1], end[2])
    return out


def edge_points_at_path_end(*, points: Sequence[Point3], trace: float) -> Edge2P:
    if len(points) < 2:
        raise ValueError("Cannot compute end edge from path with fewer than 2 points")
    end = points[-1]
    prev = points[-2]
    dx = end[0] - prev[0]
    dy = end[1] - prev[1]
    seg_len = math.hypot(dx, dy)
    if seg_len <= 1e-12:
        raise ValueError("Cannot compute end edge from zero-length final segment")
    nx = -dy / seg_len
    ny = dx / seg_len
    half_trace = trace / 2.0
    p0: Point3 = (end[0] + (nx * half_trace), end[1] + (ny * half_trace), end[2])
    p1: Point3 = (end[0] - (nx * half_trace), end[1] - (ny * half_trace), end[2])
    return p0, p1


def find_txdd_right_inner_c_index(base_points: Sequence[Point3]) -> int:
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
    base: Sequence[Point3],
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
) -> list[Point3]:
    c_index = find_txdd_right_inner_c_index(base)
    points = list(reversed(base[: c_index + 1]))
    upper_a: Point3 = (
        -(outer_x + (trace + gap)) / 2.0 + (trace / 2.0),
        (outer_y + (trace + gap)) / 2.0 - (trace / 2.0),
        0.0,
    )
    last = points[-1]
    if abs(last[0] - upper_a[0]) > 1e-9:
        points.append((upper_a[0], last[1], last[2]))
    if abs(points[-1][1] - upper_a[1]) > 1e-9:
        points.append(upper_a)
    if len(points) < 2:
        raise ValueError("tx_dd right endpoint contract violation: c->A path is too short")
    return points


def _build_txdd_right_points_c_to_a_one_turn(
    *,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
) -> list[Point3]:
    pitch = trace + gap
    left = -(outer_x / 2.0) + (trace / 2.0)
    right = (outer_x / 2.0) - (trace / 2.0)
    top = (outer_y / 2.0) - (trace / 2.0)
    bottom = -(outer_y / 2.0) + (trace / 2.0)
    aligned_upper_a: Point3 = (
        -(outer_x + pitch) / 2.0 + (trace / 2.0),
        (outer_y + pitch) / 2.0 - (trace / 2.0),
        0.0,
    )
    return [
        (right, bottom, 0.0),
        (right, top, 0.0),
        (left, top, 0.0),
        (aligned_upper_a[0], top, 0.0),
        aligned_upper_a,
    ]


def _build_txdd_right_points_a_to_d_one_turn(
    *,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
) -> list[Point3]:
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
            (left, top, 0.0),
            (left, bottom, 0.0),
            (right, bottom, 0.0),
            (right, inner_top, 0.0),
            (inner_left, inner_top, 0.0),
            (inner_left, inner_bottom, 0.0),
        ]
    return [
        (left, top, 0.0),
        (left, bottom, 0.0),
        (right, bottom, 0.0),
        (right, top, 0.0),
    ]


def _build_txdd_right_points_a_to_d(
    *,
    base: Sequence[Point3],
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
) -> list[Point3]:
    if len(base) == 4:
        return _build_txdd_right_points_a_to_d_one_turn(
            outer_x=outer_x,
            outer_y=outer_y,
            trace=trace,
            gap=gap,
        )
    mirrored_x = [(-point[0], point[1], point[2]) for point in base]
    outer_a = base[0]
    for idx, point in enumerate(mirrored_x):
        if abs(point[0] - outer_a[0]) <= 1e-9 and abs(point[1] - outer_a[1]) <= 1e-9:
            a_index = idx
            break
    else:
        raise ValueError("tx_dd right endpoint contract violation: cannot locate outer A anchor for A->D->...->d")
    rotated = mirrored_x[a_index:] + mirrored_x[:a_index]
    c_index = find_txdd_right_inner_c_index(rotated)
    d_index = c_index - 1
    if d_index < 1:
        raise ValueError("tx_dd right endpoint contract violation: A->D->...->d path is too short")
    return list(rotated[: d_index + 1])


def _build_txdd_right_points_d_to_d(
    *,
    base: Sequence[Point3],
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
) -> list[Point3]:
    a_to_d_points = _build_txdd_right_points_a_to_d(
        base=base,
        outer_x=outer_x,
        outer_y=outer_y,
        trace=trace,
        gap=gap,
    )
    if len(a_to_d_points) < 3:
        raise ValueError("tx_dd right endpoint contract violation: D->d path is too short")
    return a_to_d_points[1:]


def realize_txdd_geometry(
    *,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
    layer_count: int | None = None,
    instance_count: int | None = None,
    layer_index: int | None,
) -> tuple[int, float, float]:
    layer_count, instance_count = _resolve_txdd_counts(layer_count=layer_count, instance_count=instance_count)
    if turns < 1:
        raise ValueError(f"tx_dd turn_count must be >= 1 (actual={turns})")
    if layer_count == 1:
        return turns, outer_x, outer_y
    if layer_index not in (0, 1):
        raise ValueError(f"tx_dd layer index must be 0 or 1 for layer_count=2 (actual={layer_index})")
    if layer_index == 1:
        return turns, outer_x, outer_y

    pitch = trace + gap
    if pitch <= 0.0:
        raise ValueError(f"tx_dd pitch must be > 0 (trace={trace}, gap={gap})")
    lower_outer_x = outer_x - pitch
    lower_outer_y = outer_y - pitch
    if lower_outer_x <= trace or lower_outer_y <= trace:
        raise ValueError(
            "tx_dd lower-layer interleave contract violation: one-pitch inset leaves no valid lower-layer width "
            f"(outer_x={outer_x}, outer_y={outer_y}, trace={trace}, gap={gap}, "
            f"lower_outer_x={lower_outer_x}, lower_outer_y={lower_outer_y})"
        )
    feasible_lower_turns = min(
        max_feasible_turns(lower_outer_x, trace, gap),
        max_feasible_turns(lower_outer_y, trace, gap),
    )
    if turns > feasible_lower_turns:
        raise ValueError(
            "tx_dd lower-layer interleave contract violation: requested turns do not fit after one-pitch inset "
            f"(turns={turns}, feasible_lower_turns={feasible_lower_turns}, "
            f"lower_outer_x={lower_outer_x}, lower_outer_y={lower_outer_y}, trace={trace}, gap={gap})"
        )
    return turns, lower_outer_x, lower_outer_y


def build_txdd_right_points(
    *,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
    layer_count: int | None = None,
    instance_count: int | None = None,
    layer_index: int | None,
) -> list[Point3]:
    layer_count, instance_count = _resolve_txdd_counts(layer_count=layer_count, instance_count=instance_count)
    turns, outer_x, outer_y = realize_txdd_geometry(
        turns=turns,
        outer_x=outer_x,
        outer_y=outer_y,
        trace=trace,
        gap=gap,
        layer_count=layer_count,
        instance_count=instance_count,
        layer_index=layer_index,
    )
    base = build_rect_spiral_centerline_absolute(
        turns=turns,
        outer_x=outer_x,
        outer_y=outer_y,
        trace=trace,
        gap=gap,
        z=0.0,
    )
    if layer_count == 1:
        return _build_txdd_right_points_d_to_d(
            base=base,
            outer_x=outer_x,
            outer_y=outer_y,
            trace=trace,
            gap=gap,
        )
    if layer_index not in (0, 1):
        raise ValueError(f"tx_dd right endpoint rule requires layer index 0 or 1 (actual={layer_index})")
    if layer_index == 0:
        if turns == 1:
            return _build_txdd_right_points_c_to_a_one_turn(
                outer_x=outer_x,
                outer_y=outer_y,
                trace=trace,
                gap=gap,
            )
        return _build_txdd_right_points_c_to_a(
            base=base,
            outer_x=outer_x,
            outer_y=outer_y,
            trace=trace,
            gap=gap,
        )
    return _build_txdd_right_points_a_to_d(
        base=base,
        outer_x=outer_x,
        outer_y=outer_y,
        trace=trace,
        gap=gap,
    )
def rank_txdd_right_rows(
    rows: Sequence[tuple[float, str, int]],
    *,
    layer_count: int | None = None,
    instance_count: int | None = None,
) -> dict[int, int]:
    layer_count, instance_count = _resolve_txdd_counts(layer_count=layer_count, instance_count=instance_count)
    if layer_count != 2:
        return {}
    if len(rows) != 2:
        raise ValueError(
            "tx_dd right endpoint contract violation: expected exactly 2 right instances for layer_count=2 "
            f"(actual={len(rows)})"
        )
    ordered_rows = sorted(rows, key=lambda item: (item[0], item[1], item[2]))
    return {
        ordered_rows[0][2]: 0,
        ordered_rows[1][2]: 1,
    }


def max_feasible_turns(outer: float, trace: float, gap: float) -> int:
    pitch = trace + gap
    if pitch <= 0:
        return 0
    raw = (outer + (2.0 * gap)) / (2.0 * pitch)
    max_turns = int(math.floor(raw - 1e-12))
    return max(0, max_turns)

from __future__ import annotations

from peetsfea.tx_rect_void_geometry import (
    _EPS,
    _append_point,
    _polygons_overlap_positive_area,
    _segment_strip_polygon,
    _vector_norm_2d,
    Point2,
    Polygon2,
)
from peetsfea.tx_rect_void_spec import _parse_terminal_path
from peetsfea.tx_rect_void_types import CornerLabel, PathDirection, RealizedSingleCoilRectVoid

_CORNER_INDEX_BY_LABEL: dict[CornerLabel, int] = {"A": 0, "B": 1, "C": 2, "D": 3}


def _direction_step(direction: PathDirection) -> int:
    return 1 if direction == "cw" else -1


def _ring_left(*, realized: RealizedSingleCoilRectVoid, ring_index: int) -> float:
    return realized.outer_bounds.min_x + (realized.trace_width_mm / 2.0) + (float(ring_index) * realized.pitch_mm)


def _ring_right(*, realized: RealizedSingleCoilRectVoid, ring_index: int) -> float:
    return realized.outer_bounds.max_x - (realized.trace_width_mm / 2.0) - (float(ring_index) * realized.pitch_mm)


def _ring_top(*, realized: RealizedSingleCoilRectVoid, ring_index: int) -> float:
    return realized.outer_bounds.max_y - (realized.trace_width_mm / 2.0) - (float(ring_index) * realized.pitch_mm)


def _ring_bottom(*, realized: RealizedSingleCoilRectVoid, ring_index: int) -> float:
    return realized.outer_bounds.min_y + (realized.trace_width_mm / 2.0) + (float(ring_index) * realized.pitch_mm)


def _corner_point_by_index(
    *,
    realized: RealizedSingleCoilRectVoid,
    corner_index: int,
    ring_index: int,
) -> tuple[float, float]:
    left = _ring_left(realized=realized, ring_index=ring_index)
    right = _ring_right(realized=realized, ring_index=ring_index)
    top = _ring_top(realized=realized, ring_index=ring_index)
    bottom = _ring_bottom(realized=realized, ring_index=ring_index)
    if left >= right or bottom >= top:
        raise ValueError(
            "tx rect/void requested turns do not fit realized uniform trace geometry "
            f"(ring_index={ring_index}, left={left}, right={right}, top={top}, bottom={bottom})"
        )
    if corner_index == 0:
        return (left, top)
    if corner_index == 1:
        return (right, top)
    if corner_index == 2:
        return (right, bottom)
    if corner_index == 3:
        return (left, bottom)
    raise ValueError(f"corner_index must be 0..3 (actual={corner_index})")


def _mixed_transition_point(
    *,
    realized: RealizedSingleCoilRectVoid,
    start_corner_index: int,
    direction: PathDirection,
    last_corner_ring_index: int,
    next_start_ring_index: int,
) -> tuple[float, float]:
    last_corner = _corner_point_by_index(
        realized=realized,
        corner_index=(start_corner_index - _direction_step(direction)) % 4,
        ring_index=last_corner_ring_index,
    )
    next_start_corner = _corner_point_by_index(
        realized=realized,
        corner_index=start_corner_index,
        ring_index=next_start_ring_index,
    )
    use_next_start_x = (start_corner_index % 2 == 0) if direction == "ccw" else (start_corner_index % 2 == 1)
    if use_next_start_x:
        return (next_start_corner[0], last_corner[1])
    return (last_corner[0], next_start_corner[1])


def _build_same_corner_centerline_sharp(
    *,
    realized: RealizedSingleCoilRectVoid,
    start_corner: CornerLabel,
    direction: PathDirection,
) -> tuple[tuple[float, float], ...]:
    start_corner_index = _CORNER_INDEX_BY_LABEL[start_corner]
    step = _direction_step(direction)
    prep_corner_index = (start_corner_index + step) % 4
    enter_corner_index = (start_corner_index + (2 * step)) % 4
    end_ring_index = realized.turn_count
    _ = _corner_point_by_index(realized=realized, corner_index=start_corner_index, ring_index=end_ring_index)
    points = [
        _corner_point_by_index(realized=realized, corner_index=start_corner_index, ring_index=0),
        _corner_point_by_index(realized=realized, corner_index=prep_corner_index, ring_index=0),
    ]
    for ring_index in range(1, end_ring_index + 1):
        transition_point = _mixed_transition_point(
            realized=realized,
            start_corner_index=enter_corner_index,
            direction=direction,
            last_corner_ring_index=ring_index - 1,
            next_start_ring_index=ring_index,
        )
        _append_point(points, transition_point)
        enter_corner = _corner_point_by_index(
            realized=realized,
            corner_index=enter_corner_index,
            ring_index=ring_index,
        )
        _append_point(points, enter_corner)
        current_corner_index = enter_corner_index
        while current_corner_index != start_corner_index:
            current_corner_index = (current_corner_index + step) % 4
            _append_point(
                points,
                _corner_point_by_index(
                    realized=realized,
                    corner_index=current_corner_index,
                    ring_index=ring_index,
                ),
            )
        if ring_index < end_ring_index:
            _append_point(
                points,
                _corner_point_by_index(
                    realized=realized,
                    corner_index=prep_corner_index,
                    ring_index=ring_index,
                ),
            )
    return tuple(_seed_outer_terminal_points(points))


def _seed_outer_terminal_points(points: tuple[tuple[float, float], ...] | list[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    if len(points) < 2:
        return tuple(points)
    eps = _EPS
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    unique_x = sorted({point[0] for point in points})
    unique_y = sorted({point[1] for point in points})
    seeded = list(points)

    def _is_outer_corner(point: tuple[float, float]) -> bool:
        on_x_extreme = abs(point[0] - min_x) <= eps or abs(point[0] - max_x) <= eps
        on_y_extreme = abs(point[1] - min_y) <= eps or abs(point[1] - max_y) <= eps
        return on_x_extreme and on_y_extreme

    def _seed_from_neighbor(point: tuple[float, float], neighbor: tuple[float, float]) -> tuple[float, float]:
        dx = neighbor[0] - point[0]
        dy = neighbor[1] - point[1]
        if abs(dx) > eps and abs(dy) > eps:
            raise ValueError("tx rect/void outer terminal seed requires axis-aligned terminal segment")
        if abs(dx) <= eps and abs(dy) <= eps:
            raise ValueError("tx rect/void outer terminal seed requires non-zero terminal segment")
        if abs(dx) > eps:
            if abs(point[0] - min_x) <= eps:
                if len(unique_x) <= 1:
                    raise ValueError("tx rect/void outer terminal seed requires inner x ring")
                return (unique_x[1], point[1])
            if abs(point[0] - max_x) <= eps:
                if len(unique_x) <= 1:
                    raise ValueError("tx rect/void outer terminal seed requires inner x ring")
                return (unique_x[-2], point[1])
            return point
        if abs(point[1] - min_y) <= eps:
            if len(unique_y) <= 1:
                raise ValueError("tx rect/void outer terminal seed requires inner y ring")
            return (point[0], unique_y[1])
        if abs(point[1] - max_y) <= eps:
            if len(unique_y) <= 1:
                raise ValueError("tx rect/void outer terminal seed requires inner y ring")
            return (point[0], unique_y[-2])
        return point

    if _is_outer_corner(seeded[0]):
        seeded[0] = _seed_from_neighbor(seeded[0], seeded[1])
    if _is_outer_corner(seeded[-1]):
        seeded[-1] = _seed_from_neighbor(seeded[-1], seeded[-2])
    return tuple(seeded)


def _apply_blunt_corner_to_polyline(
    points: tuple[Point2, ...] | list[Point2],
    *,
    trace: float,
    gap: float,
    forbidden_polygon: Polygon2,
) -> tuple[Point2, ...]:
    if trace <= 0.0:
        raise ValueError(f"trace must be > 0 for blunt corner processing (actual={trace})")
    if gap < 0.0:
        raise ValueError(f"gap must be >= 0 for blunt corner processing (actual={gap})")
    if len(points) < 3:
        return tuple(points)

    trim_target = min(trace, (trace + gap) / 2.0)
    if trim_target <= _EPS:
        return tuple(points)

    shaped: list[Point2] = [points[0]]
    for index in range(1, len(points) - 1):
        prev_point = points[index - 1]
        curr_point = points[index]
        next_point = points[index + 1]

        in_dx = curr_point[0] - prev_point[0]
        in_dy = curr_point[1] - prev_point[1]
        out_dx = next_point[0] - curr_point[0]
        out_dy = next_point[1] - curr_point[1]
        in_len = _vector_norm_2d(in_dx, in_dy)
        out_len = _vector_norm_2d(out_dx, out_dy)
        if in_len <= _EPS or out_len <= _EPS:
            raise ValueError("blunt corner processing cannot consume zero-length segment")

        in_dir = (in_dx / in_len, in_dy / in_len)
        out_dir = (out_dx / out_len, out_dy / out_len)
        dot = (in_dir[0] * out_dir[0]) + (in_dir[1] * out_dir[1])
        if abs(abs(dot) - 1.0) <= _EPS:
            _append_point(shaped, curr_point)
            continue

        trim = min(trim_target, (in_len / 2.0) - _EPS, (out_len / 2.0) - _EPS)
        if trim <= _EPS:
            raise ValueError(
                "blunt corner processing requires segment length larger than bevel trim "
                f"(index={index}, in_len={in_len}, out_len={out_len}, trim_target={trim_target})"
            )

        entry_point = (
            curr_point[0] - (in_dir[0] * trim),
            curr_point[1] - (in_dir[1] * trim),
        )
        exit_point = (
            curr_point[0] + (out_dir[0] * trim),
            curr_point[1] + (out_dir[1] * trim),
        )
        if _polygons_overlap_positive_area(
            _segment_strip_polygon(p0=entry_point, p1=exit_point, trace_width_mm=trace),
            forbidden_polygon,
        ):
            safe_trim = 0.0
            unsafe_trim = trim
            for _attempt in range(40):
                candidate_trim = (safe_trim + unsafe_trim) / 2.0
                if candidate_trim <= _EPS:
                    break
                candidate_entry_point = (
                    curr_point[0] - (in_dir[0] * candidate_trim),
                    curr_point[1] - (in_dir[1] * candidate_trim),
                )
                candidate_exit_point = (
                    curr_point[0] + (out_dir[0] * candidate_trim),
                    curr_point[1] + (out_dir[1] * candidate_trim),
                )
                if _polygons_overlap_positive_area(
                    _segment_strip_polygon(
                        p0=candidate_entry_point,
                        p1=candidate_exit_point,
                        trace_width_mm=trace,
                    ),
                    forbidden_polygon,
                ):
                    unsafe_trim = candidate_trim
                else:
                    safe_trim = candidate_trim
            if safe_trim <= _EPS:
                raise ValueError(
                    "blunt corner processing could not keep bevel outside forbidden polygon "
                    f"(index={index}, corner={curr_point}, trim_target={trim_target})"
                )
            trim = max(_EPS, safe_trim - 1e-6)

        entry_point = (
            curr_point[0] - (in_dir[0] * trim),
            curr_point[1] - (in_dir[1] * trim),
        )
        exit_point = (
            curr_point[0] + (out_dir[0] * trim),
            curr_point[1] + (out_dir[1] * trim),
        )
        _append_point(shaped, entry_point)
        _append_point(shaped, exit_point)

    _append_point(shaped, points[-1])
    return tuple(shaped)


def build_tx_rect_void_centerline(realized: RealizedSingleCoilRectVoid) -> tuple[tuple[float, float], ...]:
    terminal = _parse_terminal_path(realized.terminal_path)
    points = list(
        _apply_blunt_corner_to_polyline(
            _build_same_corner_centerline_sharp(
                realized=realized,
                start_corner=terminal.outer_corner,
                direction=terminal.direction,
            ),
            trace=realized.trace_width_mm,
            gap=realized.gap_width_mm,
            forbidden_polygon=_void_polygon(realized),
        )
    )
    if len(points) < 2:
        raise ValueError("tx rect/void centerline must contain at least two points")
    if len(points) != len(set(points)):
        raise ValueError(f"tx rect/void centerline must not reuse points (points={points})")
    return tuple(points)


def _void_polygon(realized: RealizedSingleCoilRectVoid) -> Polygon2:
    void_bounds = realized.void_bounds
    return (
        (void_bounds.min_x, void_bounds.min_y),
        (void_bounds.max_x, void_bounds.min_y),
        (void_bounds.max_x, void_bounds.max_y),
        (void_bounds.min_x, void_bounds.max_y),
    )


__all__ = [
    "build_tx_rect_void_centerline",
]

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

CopperFeature = Literal["planar_segment", "terminal_stub", "vertical_bus"]
TerminalColumn = Literal["none", "start", "end"]
Point2 = tuple[float, float]
Polygon2 = tuple[Point2, ...]

_EPS = 1e-9


@dataclass(frozen=True)
class RectBounds:
    min_x: float
    max_x: float
    min_y: float
    max_y: float


@dataclass(frozen=True)
class CopperPrimitive:
    label: str
    feature: CopperFeature
    layer_index: int
    segment_index: int
    terminal_column: TerminalColumn
    polygon_xy: Polygon2
    origin_z: float
    size_z: float


@dataclass(frozen=True)
class _PolylineSegment2:
    start: Point2
    end: Point2
    tangent: Point2
    left_normal: Point2


def _append_point(points: list[Point2], point: Point2) -> None:
    if points and abs(points[-1][0] - point[0]) <= _EPS and abs(points[-1][1] - point[1]) <= _EPS:
        return
    points.append(point)


def _vector_norm_2d(dx: float, dy: float) -> float:
    return math.hypot(dx, dy)


def _polygon_bounds(polygon_xy: Polygon2) -> RectBounds:
    if len(polygon_xy) < 3:
        raise ValueError("polygon bounds require at least three points")
    xs = tuple(point[0] for point in polygon_xy)
    ys = tuple(point[1] for point in polygon_xy)
    return RectBounds(min_x=min(xs), max_x=max(xs), min_y=min(ys), max_y=max(ys))


def _points_equal(first: Point2, second: Point2) -> bool:
    return abs(first[0] - second[0]) <= _EPS and abs(first[1] - second[1]) <= _EPS


def _add_point2(first: Point2, second: Point2) -> Point2:
    return (first[0] + second[0], first[1] + second[1])


def _subtract_point2(first: Point2, second: Point2) -> Point2:
    return (first[0] - second[0], first[1] - second[1])


def _scale_point2(point: Point2, scalar: float) -> Point2:
    return (point[0] * scalar, point[1] * scalar)


def _cross_2d(first: Point2, second: Point2) -> float:
    return (first[0] * second[1]) - (first[1] * second[0])


def _segment_bbox_overlaps(first_start: Point2, first_end: Point2, second_start: Point2, second_end: Point2) -> bool:
    return (
        max(min(first_start[0], first_end[0]), min(second_start[0], second_end[0]))
        <= min(max(first_start[0], first_end[0]), max(second_start[0], second_end[0])) + _EPS
        and max(min(first_start[1], first_end[1]), min(second_start[1], second_end[1]))
        <= min(max(first_start[1], first_end[1]), max(second_start[1], second_end[1])) + _EPS
    )


def _orient_2d(first: Point2, second: Point2, third: Point2) -> float:
    return _cross_2d(_subtract_point2(second, first), _subtract_point2(third, first))


def _point_on_segment(point: Point2, start: Point2, end: Point2) -> bool:
    if abs(_orient_2d(start, end, point)) > _EPS:
        return False
    return (
        min(start[0], end[0]) - _EPS <= point[0] <= max(start[0], end[0]) + _EPS
        and min(start[1], end[1]) - _EPS <= point[1] <= max(start[1], end[1]) + _EPS
    )


def _segments_properly_intersect(first_start: Point2, first_end: Point2, second_start: Point2, second_end: Point2) -> bool:
    if not _segment_bbox_overlaps(first_start, first_end, second_start, second_end):
        return False
    orient_a = _orient_2d(first_start, first_end, second_start)
    orient_b = _orient_2d(first_start, first_end, second_end)
    orient_c = _orient_2d(second_start, second_end, first_start)
    orient_d = _orient_2d(second_start, second_end, first_end)
    if abs(orient_a) <= _EPS or abs(orient_b) <= _EPS or abs(orient_c) <= _EPS or abs(orient_d) <= _EPS:
        return False
    return ((orient_a > 0.0) != (orient_b > 0.0)) and ((orient_c > 0.0) != (orient_d > 0.0))


def _segments_overlap_collinearly_with_positive_length(
    first_start: Point2,
    first_end: Point2,
    second_start: Point2,
    second_end: Point2,
) -> bool:
    if (
        abs(_orient_2d(first_start, first_end, second_start)) > _EPS
        or abs(_orient_2d(first_start, first_end, second_end)) > _EPS
    ):
        return False
    if not _segment_bbox_overlaps(first_start, first_end, second_start, second_end):
        return False
    if abs(first_end[0] - first_start[0]) >= abs(first_end[1] - first_start[1]):
        overlap = min(max(first_start[0], first_end[0]), max(second_start[0], second_end[0])) - max(
            min(first_start[0], first_end[0]),
            min(second_start[0], second_end[0]),
        )
    else:
        overlap = min(max(first_start[1], first_end[1]), max(second_start[1], second_end[1])) - max(
            min(first_start[1], first_end[1]),
            min(second_start[1], second_end[1]),
        )
    return overlap > _EPS


def _polygon_edges(polygon_xy: Polygon2) -> tuple[tuple[Point2, Point2], ...]:
    if len(polygon_xy) < 3:
        raise ValueError("polygon edges require at least three points")
    return tuple((polygon_xy[index], polygon_xy[(index + 1) % len(polygon_xy)]) for index in range(len(polygon_xy)))


def _polygon_is_simple(polygon_xy: Polygon2) -> bool:
    if len(polygon_xy) < 3:
        return False
    if len(set(polygon_xy)) != len(polygon_xy):
        return False
    edges = _polygon_edges(polygon_xy)
    for first_index, (first_start, first_end) in enumerate(edges):
        for second_index in range(first_index + 1, len(edges)):
            if second_index == first_index + 1:
                continue
            if first_index == 0 and second_index == len(edges) - 1:
                continue
            second_start, second_end = edges[second_index]
            if not _segment_bbox_overlaps(first_start, first_end, second_start, second_end):
                continue
            if _segments_properly_intersect(first_start, first_end, second_start, second_end):
                return False
            if _segments_overlap_collinearly_with_positive_length(first_start, first_end, second_start, second_end):
                return False
            shared_points = tuple(
                point
                for point in (first_start, first_end)
                if _point_on_segment(point, second_start, second_end)
                and not _points_equal(point, second_start)
                and not _points_equal(point, second_end)
            ) + tuple(
                point
                for point in (second_start, second_end)
                if _point_on_segment(point, first_start, first_end)
                and not _points_equal(point, first_start)
                and not _points_equal(point, first_end)
            )
            if shared_points:
                return False
    return True


def _point_in_polygon_strict(point: Point2, polygon_xy: Polygon2) -> bool:
    x_coord, y_coord = point
    inside = False
    for start_point, end_point in _polygon_edges(polygon_xy):
        if _point_on_segment(point, start_point, end_point):
            return False
        start_x, start_y = start_point
        end_x, end_y = end_point
        intersects = (start_y > y_coord) != (end_y > y_coord)
        if not intersects:
            continue
        cross_x = start_x + ((end_x - start_x) * (y_coord - start_y) / (end_y - start_y))
        if cross_x > x_coord + _EPS:
            inside = not inside
    return inside


def _polygons_overlap_positive_area(first: Polygon2, second: Polygon2) -> bool:
    for first_start, first_end in _polygon_edges(first):
        for second_start, second_end in _polygon_edges(second):
            if not _segment_bbox_overlaps(first_start, first_end, second_start, second_end):
                continue
            if _segments_properly_intersect(first_start, first_end, second_start, second_end):
                return True
    for point in first:
        if _point_in_polygon_strict(point, second):
            return True
    for point in second:
        if _point_in_polygon_strict(point, first):
            return True
    return False


def _segment_strip_polygon(
    *,
    p0: Point2,
    p1: Point2,
    trace_width_mm: float,
) -> Polygon2:
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    length = _vector_norm_2d(dx, dy)
    if length <= _EPS:
        raise ValueError(f"tx rect/void centerline segment must have non-zero length (p0={p0}, p1={p1})")
    if trace_width_mm <= 0.0:
        raise ValueError(f"tx rect/void segment trace width must be > 0 (actual={trace_width_mm})")
    unit_x = dx / length
    unit_y = dy / length
    half_trace = trace_width_mm / 2.0
    perp_x = -unit_y * half_trace
    perp_y = unit_x * half_trace
    return (
        (p0[0] + perp_x, p0[1] + perp_y),
        (p1[0] + perp_x, p1[1] + perp_y),
        (p1[0] - perp_x, p1[1] - perp_y),
        (p0[0] - perp_x, p0[1] - perp_y),
    )


def _polyline_segment(start: Point2, end: Point2) -> _PolylineSegment2:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = _vector_norm_2d(dx, dy)
    if length <= _EPS:
        raise ValueError(f"polyline segment must have non-zero length (start={start}, end={end})")
    tangent = (dx / length, dy / length)
    return _PolylineSegment2(
        start=start,
        end=end,
        tangent=tangent,
        left_normal=(-tangent[1], tangent[0]),
    )


def _polyline_segments(centerline: tuple[Point2, ...]) -> tuple[_PolylineSegment2, ...]:
    if len(centerline) < 2:
        raise ValueError("polyline segments require at least two centerline points")
    return tuple(_polyline_segment(start, end) for start, end in zip(centerline[:-1], centerline[1:]))


def trace_outline_polygon(
    centerline: tuple[Point2, ...],
    trace_width_mm: float,
) -> Polygon2:
    if trace_width_mm <= 0.0:
        raise ValueError(f"trace outline polygon requires trace width > 0 (actual={trace_width_mm})")
    segments = _polyline_segments(centerline)
    segment_count = len(segments)
    half_trace = trace_width_mm / 2.0

    left_chain: list[Point2] = []
    right_chain: list[Point2] = []

    first_segment = segments[0]
    last_segment = segments[segment_count - 1]
    _append_point(left_chain, _add_point2(first_segment.start, _scale_point2(first_segment.left_normal, half_trace)))
    for vertex_index in range(1, len(centerline) - 1):
        _append_point(
            left_chain,
            _offset_join_point(
                centerline,
                trace_width_mm=trace_width_mm,
                vertex_index=vertex_index,
                side="left",
            ),
        )
    _append_point(left_chain, _add_point2(last_segment.end, _scale_point2(last_segment.left_normal, half_trace)))

    _append_point(right_chain, _add_point2(last_segment.end, _scale_point2(last_segment.left_normal, -half_trace)))
    for vertex_index in range(len(centerline) - 2, 0, -1):
        _append_point(
            right_chain,
            _offset_join_point(
                centerline,
                trace_width_mm=trace_width_mm,
                vertex_index=vertex_index,
                side="right",
            ),
        )
    _append_point(right_chain, _add_point2(first_segment.start, _scale_point2(first_segment.left_normal, -half_trace)))

    outline_polygon = tuple(left_chain + right_chain)
    if not _polygon_is_simple(outline_polygon):
        raise ValueError(f"trace outline polygon must remain simple (polygon={outline_polygon})")
    return outline_polygon


def _offset_join_point(
    centerline: tuple[Point2, ...],
    *,
    trace_width_mm: float,
    vertex_index: int,
    side: Literal["left", "right"],
) -> Point2:
    if vertex_index <= 0 or vertex_index >= len(centerline) - 1:
        raise ValueError(
            "offset join point requires an internal centerline vertex "
            f"(vertex_index={vertex_index}, point_count={len(centerline)})"
        )
    if trace_width_mm <= 0.0:
        raise ValueError(f"trace width must be > 0 for outline join point (actual={trace_width_mm})")
    half_trace = trace_width_mm / 2.0
    sign = 1.0 if side == "left" else -1.0
    segments = _polyline_segments(centerline)
    prev_segment = segments[vertex_index - 1]
    next_segment = segments[vertex_index]
    vertex = centerline[vertex_index]
    prev_offset_point = _add_point2(vertex, _scale_point2(prev_segment.left_normal, half_trace * sign))
    next_offset_point = _add_point2(vertex, _scale_point2(next_segment.left_normal, half_trace * sign))
    cross = _cross_2d(prev_segment.tangent, next_segment.tangent)
    if abs(cross) <= _EPS:
        return next_offset_point
    offset_delta = _subtract_point2(next_offset_point, prev_offset_point)
    travel = _cross_2d(offset_delta, next_segment.tangent) / cross
    return _add_point2(prev_offset_point, _scale_point2(prev_segment.tangent, travel))


def _segment_joined_polygon(
    centerline: tuple[Point2, ...],
    *,
    trace_width_mm: float,
    segment_index: int,
) -> Polygon2:
    if trace_width_mm <= 0.0:
        raise ValueError(f"trace width must be > 0 for segment joined polygon (actual={trace_width_mm})")
    segments = _polyline_segments(centerline)
    if segment_index < 0 or segment_index >= len(segments):
        raise ValueError(
            "segment joined polygon requires a valid segment index "
            f"(segment_index={segment_index}, segment_count={len(segments)})"
        )
    half_trace = trace_width_mm / 2.0
    segment = segments[segment_index]
    start_point = segment.start
    end_point = segment.end
    start_left = _add_point2(start_point, _scale_point2(segment.left_normal, half_trace))
    start_right = _add_point2(start_point, _scale_point2(segment.left_normal, -half_trace))
    end_left = _add_point2(end_point, _scale_point2(segment.left_normal, half_trace))
    end_right = _add_point2(end_point, _scale_point2(segment.left_normal, -half_trace))
    if segment_index > 0:
        prev_segment = segments[segment_index - 1]
        start_turn_cross = _cross_2d(prev_segment.tangent, segment.tangent)
        if start_turn_cross > _EPS:
            start_right = _offset_join_point(centerline, trace_width_mm=trace_width_mm, vertex_index=segment_index, side="right")
        elif start_turn_cross < -_EPS:
            start_left = _offset_join_point(centerline, trace_width_mm=trace_width_mm, vertex_index=segment_index, side="left")
    if segment_index < len(segments) - 1:
        next_segment = segments[segment_index + 1]
        end_turn_cross = _cross_2d(segment.tangent, next_segment.tangent)
        if end_turn_cross > _EPS:
            end_right = _offset_join_point(
                centerline,
                trace_width_mm=trace_width_mm,
                vertex_index=segment_index + 1,
                side="right",
            )
        elif end_turn_cross < -_EPS:
            end_left = _offset_join_point(
                centerline,
                trace_width_mm=trace_width_mm,
                vertex_index=segment_index + 1,
                side="left",
            )
    polygon = (start_left, end_left, end_right, start_right)
    if not _polygon_is_simple(polygon):
        raise ValueError(
            "segment joined polygon must remain simple "
            f"(segment_index={segment_index}, polygon={polygon})"
        )
    return polygon


def _terminal_stub_polygon(
    *,
    endpoint_xy: Point2,
    inward_point_xy: Point2,
    stub_side_mm: float,
    overlap_mm: float,
) -> Polygon2:
    dx = inward_point_xy[0] - endpoint_xy[0]
    dy = inward_point_xy[1] - endpoint_xy[1]
    length = _vector_norm_2d(dx, dy)
    if length <= _EPS:
        raise ValueError(
            "tx rect/void terminal stub requires distinct inward point "
            f"(endpoint={endpoint_xy}, inward={inward_point_xy})"
        )
    if stub_side_mm <= 0.0:
        raise ValueError(f"tx rect/void terminal stub side must be > 0 (actual={stub_side_mm})")
    unit_x = dx / length
    unit_y = dy / length
    perp_x = -unit_y
    perp_y = unit_x
    half_stub = stub_side_mm / 2.0
    center_xy = (
        endpoint_xy[0] + (unit_x * (half_stub - overlap_mm)),
        endpoint_xy[1] + (unit_y * (half_stub - overlap_mm)),
    )
    return (
        (
            center_xy[0] + (unit_x * half_stub) + (perp_x * half_stub),
            center_xy[1] + (unit_y * half_stub) + (perp_y * half_stub),
        ),
        (
            center_xy[0] + (unit_x * half_stub) - (perp_x * half_stub),
            center_xy[1] + (unit_y * half_stub) - (perp_y * half_stub),
        ),
        (
            center_xy[0] - (unit_x * half_stub) - (perp_x * half_stub),
            center_xy[1] - (unit_y * half_stub) - (perp_y * half_stub),
        ),
        (
            center_xy[0] - (unit_x * half_stub) + (perp_x * half_stub),
            center_xy[1] - (unit_y * half_stub) + (perp_y * half_stub),
        ),
    )


def _rect_polygon_from_bounds(bounds: RectBounds) -> Polygon2:
    return (
        (bounds.min_x, bounds.min_y),
        (bounds.max_x, bounds.min_y),
        (bounds.max_x, bounds.max_y),
        (bounds.min_x, bounds.max_y),
    )


def _planar_bounds_from_polygons(polygons_xy: tuple[Polygon2, ...]) -> RectBounds:
    if len(polygons_xy) == 0:
        raise ValueError("planar bounds require at least one polygon")
    bounds = tuple(_polygon_bounds(polygon_xy) for polygon_xy in polygons_xy)
    return RectBounds(
        min_x=min(bound.min_x for bound in bounds),
        max_x=max(bound.max_x for bound in bounds),
        min_y=min(bound.min_y for bound in bounds),
        max_y=max(bound.max_y for bound in bounds),
    )


def _planar_bounds_from_primitives(copper_primitives: tuple[CopperPrimitive, ...]) -> RectBounds:
    return _planar_bounds_from_polygons(tuple(primitive.polygon_xy for primitive in copper_primitives))

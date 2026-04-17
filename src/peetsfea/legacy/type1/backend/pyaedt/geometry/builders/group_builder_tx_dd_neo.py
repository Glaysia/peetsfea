from __future__ import annotations

from typing import Callable, Literal, cast

from peetsfea.aedt import Modeler3D
from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance, TerminalLabel

from ..build_state import Edge2P, FinalizeInputs, GeometryBuildState, GeometryRuntimeContext, Point3, TxDdSceneRegistry, require_tx_dd_scene
from ..rules.placement_rules import _current_direction_from_xy_points, _edge_points_at_xy_terminal, _segments_intersect_2d, _tx_dd_center_y_and_layer
from ..rules.spiral_points import _apply_corner_mode_to_polyline_lists
from .group_builder_tx_dd_geometry import _append_tx_dd_external_stub_source, _directed_landing_section_from_raw_edge, _xy_terminal_inward_dir, _XY_PLANE_NORMAL
from .neo_coil_instance import NeoCoilBoxInstance, NeoCoilInstance

_NEO_TX_DD_FR4_PREFIX = "neo_fr4_tx_dd_"
_NEO_FR4_EPOXY_GREEN = (0, 128, 0)
_NEO_FR4_TRANSPARENCY = 0.85
_NEO_TX_DD_LEFT_PREFIX = "neo_coil_tx_dd_left_"
_NEO_TX_DD_RIGHT_PREFIX = "neo_coil_tx_dd_right_"
_NEO_COPPER_COLOR = (184, 115, 51)
_NEO_COPPER_TRANSPARENCY = 0.0
_SINGLE_LAYER_TX_DD_BOARD_IDS = ("tx_main_0",)
_DOUBLE_LAYER_TX_DD_BOARD_IDS = ("tx_main_0", "tx_main_1")
_TX_DD_LAYER_INDEX_BY_BOARD_ID = {
    "tx_main_0": 0,
    "tx_main_1": 1,
}
_PathDirection = Literal["cw", "ccw"]
_CORNER_INDEX_BY_UPPER_LABEL = {"A": 0, "B": 1, "C": 2, "D": 3}
_UPPER_LABEL_BY_CORNER_INDEX = {0: "A", 1: "B", 2: "C", 3: "D"}


def _pcb_has_tx_dd_mount(pcb: ResolvedPcbInstance) -> bool:
    return any(mount["kind"] == "tx_dd" for mount in pcb["mounts"])


def _right_tx_dd_selector_index(pcb: ResolvedPcbInstance) -> int:
    selector_indices = [
        mount["selector_index"]
        for mount in pcb["mounts"]
        if mount["kind"] == "tx_dd" and mount["selector_mode"] == "index"
    ]
    assert selector_indices, f"neo tx_dd right build requires tx_dd index mounts on {pcb['id']}"
    resolved_selector_indices = [selector_index for selector_index in selector_indices if isinstance(selector_index, int)]
    assert resolved_selector_indices, f"neo tx_dd right build requires concrete tx_dd selector_index values on {pcb['id']}"
    return max(resolved_selector_indices)


def _left_tx_dd_selector_index(pcb: ResolvedPcbInstance) -> int:
    selector_indices = [
        mount["selector_index"]
        for mount in pcb["mounts"]
        if mount["kind"] == "tx_dd" and mount["selector_mode"] == "index"
    ]
    assert selector_indices, f"neo tx_dd left build requires tx_dd index mounts on {pcb['id']}"
    resolved_selector_indices = [selector_index for selector_index in selector_indices if isinstance(selector_index, int)]
    assert resolved_selector_indices, f"neo tx_dd left build requires concrete tx_dd selector_index values on {pcb['id']}"
    return min(resolved_selector_indices)


def _single_transform(group: ResolvedCoilGroup) -> dict[str, float]:
    transforms = group["instance_transforms"]
    assert len(transforms) == 1, f"neo tx_dd right build requires exactly 1 instance transform (actual={len(transforms)})"
    return transforms[0]


def _flip_direction(direction: Literal["cw", "ccw"]) -> Literal["cw", "ccw"]:
    return "ccw" if direction == "cw" else "cw"


def _direction_step(direction: _PathDirection) -> int:
    return 1 if direction == "cw" else -1


def _validate_neo_axis_aligned_path(points: list[Point3]) -> None:
    if len(points) < 2:
        raise ValueError("neo tx_dd right path must contain at least 2 points")
    eps = 1e-9
    for point_index in range(len(points) - 1):
        p0 = points[point_index]
        p1 = points[point_index + 1]
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        if abs(dx) <= eps and abs(dy) <= eps:
            raise ValueError("neo tx_dd right path generated a zero-length segment")
        if abs(dx) > eps and abs(dy) > eps:
            raise ValueError("neo tx_dd right path generated a non-axis-aligned segment")
    for point_index in range(1, len(points) - 1):
        p_prev = points[point_index - 1]
        p_curr = points[point_index]
        p_next = points[point_index + 1]
        vx1 = p_curr[0] - p_prev[0]
        vy1 = p_curr[1] - p_prev[1]
        vx2 = p_next[0] - p_curr[0]
        vy2 = p_next[1] - p_curr[1]
        if abs(vx1 + vx2) <= eps and abs(vy1 + vy2) <= eps:
            raise ValueError("neo tx_dd right path generated an immediate backtracking segment")
    segments = [(points[idx], points[idx + 1]) for idx in range(len(points) - 1)]
    for idx in range(len(segments)):
        for jdx in range(idx + 1, len(segments)):
            if jdx <= idx + 1:
                continue
            a0, a1 = segments[idx]
            b0, b1 = segments[jdx]
            if _segments_intersect_2d((a0[0], a0[1]), (a1[0], a1[1]), (b0[0], b0[1]), (b1[0], b1[1]), eps):
                shared_points = (
                    (a0, b0),
                    (a0, b1),
                    (a1, b0),
                    (a1, b1),
                )
                if any(abs(p0[0] - p1[0]) <= eps and abs(p0[1] - p1[1]) <= eps for p0, p1 in shared_points):
                    continue
                raise ValueError("neo tx_dd right path generated a non-adjacent self-crossing segment")


def _ring_left(*, left: float, pitch: float, layer_index: int) -> float:
    return left + (layer_index * pitch)


def _ring_right(*, right: float, pitch: float, layer_index: int) -> float:
    return right - (layer_index * pitch)


def _ring_top(*, top: float, pitch: float, layer_index: int) -> float:
    return top - (layer_index * pitch)


def _ring_bottom(*, bottom: float, pitch: float, layer_index: int) -> float:
    return bottom + (layer_index * pitch)


def _same_corner_upper_label(label: TerminalLabel) -> Literal["A", "B", "C", "D"]:
    resolved = label.upper()
    assert resolved in _CORNER_INDEX_BY_UPPER_LABEL
    return cast(Literal["A", "B", "C", "D"], resolved)


def _corner_index(label: TerminalLabel) -> int:
    upper_label = _same_corner_upper_label(label)
    return _CORNER_INDEX_BY_UPPER_LABEL[upper_label]


def _corner_point(
    *,
    corner_index: int,
    layer_index: int,
    left: float,
    right: float,
    top: float,
    bottom: float,
    pitch: float,
) -> Point3:
    left_k = _ring_left(left=left, pitch=pitch, layer_index=layer_index)
    right_k = _ring_right(right=right, pitch=pitch, layer_index=layer_index)
    top_k = _ring_top(top=top, pitch=pitch, layer_index=layer_index)
    bottom_k = _ring_bottom(bottom=bottom, pitch=pitch, layer_index=layer_index)
    if left_k >= right_k or bottom_k >= top_k:
        raise ValueError(
            "neo tx_dd right requested turns do not fit realized geometry "
            f"(corner_index={corner_index}, layer_index={layer_index}, left_k={left_k}, right_k={right_k}, top_k={top_k}, bottom_k={bottom_k})"
        )
    if corner_index == 0:
        return (left_k, top_k, 0.0)
    if corner_index == 1:
        return (right_k, top_k, 0.0)
    if corner_index == 2:
        return (right_k, bottom_k, 0.0)
    if corner_index == 3:
        return (left_k, bottom_k, 0.0)
    raise ValueError(f"neo tx_dd right corner_index must be 0..3 (actual={corner_index})")


def _mixed_transition_point(
    *,
    start_corner_index: int,
    direction: _PathDirection,
    last_corner_layer_index: int,
    next_start_layer_index: int,
    left: float,
    right: float,
    top: float,
    bottom: float,
    pitch: float,
) -> Point3:
    last_corner = _corner_point(
        corner_index=(start_corner_index - _direction_step(direction)) % 4,
        layer_index=last_corner_layer_index,
        left=left,
        right=right,
        top=top,
        bottom=bottom,
        pitch=pitch,
    )
    next_start_corner = _corner_point(
        corner_index=start_corner_index,
        layer_index=next_start_layer_index,
        left=left,
        right=right,
        top=top,
        bottom=bottom,
        pitch=pitch,
    )
    use_next_start_x = (start_corner_index % 2 == 0) if direction == "ccw" else (start_corner_index % 2 == 1)
    if use_next_start_x:
        return (next_start_corner[0], last_corner[1], 0.0)
    return (last_corner[0], next_start_corner[1], 0.0)


def _build_txdd_right_points_outer_to_inner(
    *,
    start_corner_index: int,
    end_corner_index: int,
    direction: _PathDirection,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
) -> list[Point3]:
    if turns < 1:
        raise ValueError(f"neo tx_dd right turns must be >= 1 (actual={turns})")
    if trace <= 0.0:
        raise ValueError(f"neo tx_dd right trace must be > 0 (actual={trace})")
    if gap < 0.0:
        raise ValueError(f"neo tx_dd right gap must be >= 0 (actual={gap})")
    pitch = trace + gap
    half_trace = trace / 2.0
    left = -(outer_x / 2.0) + half_trace
    right = (outer_x / 2.0) - half_trace
    top = (outer_y / 2.0) - half_trace
    bottom = -(outer_y / 2.0) + half_trace
    if left >= right or bottom >= top:
        raise ValueError(
            "neo tx_dd right outer geometry must leave positive centerline area "
            f"(outer_x={outer_x}, outer_y={outer_y}, trace={trace})"
        )
    end_layer_index = turns
    _ = _corner_point(
        corner_index=start_corner_index,
        layer_index=end_layer_index,
        left=left,
        right=right,
        top=top,
        bottom=bottom,
        pitch=pitch,
    )
    points = [
        _corner_point(
            corner_index=start_corner_index,
            layer_index=0,
            left=left,
            right=right,
            top=top,
            bottom=bottom,
            pitch=pitch,
        )
    ]
    step = _direction_step(direction)
    for layer_index in range(end_layer_index):
        for offset in range(1, 4):
            points.append(
                _corner_point(
                    corner_index=(start_corner_index + (step * offset)) % 4,
                    layer_index=layer_index,
                    left=left,
                    right=right,
                    top=top,
                    bottom=bottom,
                    pitch=pitch,
                )
            )
        next_start = _corner_point(
            corner_index=start_corner_index,
            layer_index=layer_index + 1,
            left=left,
            right=right,
            top=top,
            bottom=bottom,
            pitch=pitch,
        )
        transition_point = _mixed_transition_point(
            start_corner_index=start_corner_index,
            direction=direction,
            last_corner_layer_index=layer_index,
            next_start_layer_index=layer_index + 1,
            left=left,
            right=right,
            top=top,
            bottom=bottom,
            pitch=pitch,
        )
        if transition_point != points[-1]:
            points.append(transition_point)
        if next_start != points[-1]:
            points.append(next_start)

    delta = (
        (end_corner_index - start_corner_index) % 4
        if direction == "cw"
        else (start_corner_index - end_corner_index) % 4
    )
    steps_to_end = 4 if delta == 0 else delta
    for offset in range(1, steps_to_end + 1):
        points.append(
            _corner_point(
                corner_index=(start_corner_index + (step * offset)) % 4,
                layer_index=end_layer_index,
                left=left,
                right=right,
                top=top,
                bottom=bottom,
                pitch=pitch,
            )
        )
    _validate_neo_axis_aligned_path(points)
    resolved_direction = _current_direction_from_xy_points([[point[0], point[1], point[2]] for point in points])
    if resolved_direction != direction:
        raise ValueError(
            "neo tx_dd right outer->inner planner generated unexpected winding "
            f"(actual={resolved_direction}, expected={direction}, turns={turns}, start_corner_index={start_corner_index}, end_corner_index={end_corner_index})"
        )
    return points


def _build_txdd_right_points_same_corner(
    *,
    start_corner_index: int,
    direction: _PathDirection,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
) -> list[Point3]:
    if turns < 1:
        raise ValueError(f"neo tx_dd right turns must be >= 1 (actual={turns})")
    if trace <= 0.0:
        raise ValueError(f"neo tx_dd right trace must be > 0 (actual={trace})")
    if gap < 0.0:
        raise ValueError(f"neo tx_dd right gap must be >= 0 (actual={gap})")
    pitch = trace + gap
    half_trace = trace / 2.0
    left = -(outer_x / 2.0) + half_trace
    right = (outer_x / 2.0) - half_trace
    top = (outer_y / 2.0) - half_trace
    bottom = -(outer_y / 2.0) + half_trace
    if left >= right or bottom >= top:
        raise ValueError(
            "neo tx_dd right outer geometry must leave positive centerline area "
            f"(outer_x={outer_x}, outer_y={outer_y}, trace={trace})"
        )
    end_layer_index = turns
    _ = _corner_point(
        corner_index=start_corner_index,
        layer_index=end_layer_index,
        left=left,
        right=right,
        top=top,
        bottom=bottom,
        pitch=pitch,
    )
    step = _direction_step(direction)
    prep_corner_index = (start_corner_index + step) % 4
    enter_corner_index = (start_corner_index + (2 * step)) % 4
    points = [
        _corner_point(
            corner_index=start_corner_index,
            layer_index=0,
            left=left,
            right=right,
            top=top,
            bottom=bottom,
            pitch=pitch,
        ),
        _corner_point(
            corner_index=prep_corner_index,
            layer_index=0,
            left=left,
            right=right,
            top=top,
            bottom=bottom,
            pitch=pitch,
        ),
    ]
    for layer_index in range(1, end_layer_index + 1):
        transition_point = _mixed_transition_point(
            start_corner_index=enter_corner_index,
            direction=direction,
            last_corner_layer_index=layer_index - 1,
            next_start_layer_index=layer_index,
            left=left,
            right=right,
            top=top,
            bottom=bottom,
            pitch=pitch,
        )
        if transition_point != points[-1]:
            points.append(transition_point)
        enter_corner = _corner_point(
            corner_index=enter_corner_index,
            layer_index=layer_index,
            left=left,
            right=right,
            top=top,
            bottom=bottom,
            pitch=pitch,
        )
        if enter_corner != points[-1]:
            points.append(enter_corner)
        current_corner_index = enter_corner_index
        while current_corner_index != start_corner_index:
            current_corner_index = (current_corner_index + step) % 4
            corner = _corner_point(
                corner_index=current_corner_index,
                layer_index=layer_index,
                left=left,
                right=right,
                top=top,
                bottom=bottom,
                pitch=pitch,
            )
            if corner != points[-1]:
                points.append(corner)
        if layer_index < end_layer_index:
            prep_corner = _corner_point(
                corner_index=prep_corner_index,
                layer_index=layer_index,
                left=left,
                right=right,
                top=top,
                bottom=bottom,
                pitch=pitch,
            )
            if prep_corner != points[-1]:
                points.append(prep_corner)
    _validate_neo_axis_aligned_path(points)
    resolved_direction = _current_direction_from_xy_points([[point[0], point[1], point[2]] for point in points])
    if resolved_direction != direction:
        raise ValueError(
            "neo tx_dd right same-corner planner generated unexpected winding "
            f"(actual={resolved_direction}, expected={direction}, turns={turns}, start_corner_index={start_corner_index})"
        )
    return points


def _parse_terminal_path_contract(
    terminal_path: str,
) -> tuple[TerminalLabel, _PathDirection, TerminalLabel]:
    parts = terminal_path.split("_")
    if len(parts) != 4 or parts[2] != "to":
        raise ValueError(f"neo tx_dd terminal path must match '<start>_<cw|ccw>_to_<end>' (actual={terminal_path})")
    start_label = parts[0]
    direction = parts[1]
    end_label = parts[3]
    resolved_start = cast(TerminalLabel, start_label)
    resolved_end = cast(TerminalLabel, end_label)
    assert resolved_start in {"A", "B", "C", "D", "a", "b", "c", "d"}
    assert resolved_end in {"A", "B", "C", "D", "a", "b", "c", "d"}
    assert direction in {"cw", "ccw"}
    assert resolved_start.islower() != resolved_end.islower()
    return (
        resolved_start,
        cast(_PathDirection, direction),
        resolved_end,
    )


def _apply_corner_mode_to_neo_path(
    *,
    points: list[Point3],
    corner_mode: int,
    trace: float,
    gap: float,
    expected_direction: _PathDirection,
    selected_path: str,
) -> list[Point3]:
    shaped_points = [
        cast(Point3, (float(point[0]), float(point[1]), float(point[2])))
        for point in _apply_corner_mode_to_polyline_lists(
            [[point[0], point[1], point[2]] for point in points],
            corner_mode=corner_mode,
            trace=trace,
            gap=gap,
        )
    ]
    resolved_direction = _current_direction_from_xy_points([[point[0], point[1], point[2]] for point in shaped_points])
    if resolved_direction != expected_direction:
        raise ValueError(
            "neo tx_dd corner_mode shaping changed winding unexpectedly "
            f"(actual={resolved_direction}, expected={expected_direction}, selected_path={selected_path}, corner_mode={corner_mode})"
        )
    return shaped_points


def _seed_outer_terminal_points(
    *,
    points: list[Point3],
) -> list[Point3]:
    if len(points) < 2:
        return list(points)
    eps = 1e-9
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    unique_x = sorted({point[0] for point in points})
    unique_y = sorted({point[1] for point in points})
    seeded = list(points)

    def _is_outer_corner(point: Point3) -> bool:
        on_x_extreme = abs(point[0] - min_x) <= eps or abs(point[0] - max_x) <= eps
        on_y_extreme = abs(point[1] - min_y) <= eps or abs(point[1] - max_y) <= eps
        return on_x_extreme and on_y_extreme

    def _seed_from_neighbor(point: Point3, neighbor: Point3) -> Point3:
        dx = neighbor[0] - point[0]
        dy = neighbor[1] - point[1]
        if abs(dx) > eps and abs(dy) > eps:
            raise ValueError("neo tx_dd outer terminal seed adjustment requires axis-aligned terminal segment")
        if abs(dx) <= eps and abs(dy) <= eps:
            raise ValueError("neo tx_dd outer terminal seed adjustment requires non-zero terminal segment")
        if abs(dx) > eps:
            if abs(point[0] - min_x) <= eps:
                assert len(unique_x) > 1, "neo tx_dd outer terminal seed adjustment requires inner x ring"
                return cast(Point3, (unique_x[1], point[1], point[2]))
            if abs(point[0] - max_x) <= eps:
                assert len(unique_x) > 1, "neo tx_dd outer terminal seed adjustment requires inner x ring"
                return cast(Point3, (unique_x[-2], point[1], point[2]))
            return point
        if abs(point[1] - min_y) <= eps:
            assert len(unique_y) > 1, "neo tx_dd outer terminal seed adjustment requires inner y ring"
            return cast(Point3, (point[0], unique_y[1], point[2]))
        if abs(point[1] - max_y) <= eps:
            assert len(unique_y) > 1, "neo tx_dd outer terminal seed adjustment requires inner y ring"
            return cast(Point3, (point[0], unique_y[-2], point[2]))
        return point

    if _is_outer_corner(seeded[0]):
        seeded[0] = _seed_from_neighbor(seeded[0], seeded[1])
    if _is_outer_corner(seeded[-1]):
        seeded[-1] = _seed_from_neighbor(seeded[-1], seeded[-2])
    return seeded


def _resolve_single_layer_path(
    *,
    selected_path: str,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
    corner_mode: int = 0,
) -> tuple[
    list[Point3],
    TerminalLabel,
    TerminalLabel,
    _PathDirection,
]:
    start_label, direction, end_label = _parse_terminal_path_contract(selected_path)
    start_corner_index = _corner_index(start_label)
    end_corner_index = _corner_index(end_label)

    def _shape_points(raw_points: list[Point3]) -> list[Point3]:
        seeded_points = _seed_outer_terminal_points(points=raw_points)
        _validate_neo_axis_aligned_path(seeded_points)
        return _apply_corner_mode_to_neo_path(
            points=seeded_points,
            corner_mode=corner_mode,
            trace=trace,
            gap=gap,
            expected_direction=direction,
            selected_path=selected_path,
        )

    if start_corner_index == end_corner_index:
        if start_label.isupper():
            points = _build_txdd_right_points_same_corner(
                start_corner_index=start_corner_index,
                direction=direction,
                turns=turns,
                outer_x=outer_x,
                outer_y=outer_y,
                trace=trace,
                gap=gap,
            )
            return (
                _shape_points(points),
                start_label,
                end_label,
                direction,
            )
        reverse_direction = _flip_direction(direction)
        inward_points = _build_txdd_right_points_same_corner(
            start_corner_index=end_corner_index,
            direction=reverse_direction,
            turns=turns,
            outer_x=outer_x,
            outer_y=outer_y,
            trace=trace,
            gap=gap,
        )
        points = list(reversed(inward_points))
        resolved_direction = _current_direction_from_xy_points([[point[0], point[1], point[2]] for point in points])
        if resolved_direction != direction:
            raise ValueError(
                "neo tx_dd right same-corner inner->outer planner generated unexpected winding "
                f"(actual={resolved_direction}, expected={direction}, selected_path={selected_path})"
            )
        return (
            _shape_points(points),
            start_label,
            end_label,
            direction,
        )
    if start_label.isupper():
        if not end_label.islower():
            raise ValueError(
                "neo tx_dd right outer-start contract requires lowercase end terminal "
                f"(selected_path={selected_path})"
            )
        points = _build_txdd_right_points_outer_to_inner(
            start_corner_index=start_corner_index,
            end_corner_index=end_corner_index,
            direction=direction,
            turns=turns,
            outer_x=outer_x,
                outer_y=outer_y,
                trace=trace,
                gap=gap,
            )
        return (
            _shape_points(points),
            start_label,
            end_label,
            direction,
        )
    if not end_label.isupper():
        raise ValueError(
            "neo tx_dd inner-start contract requires uppercase end terminal "
            f"(selected_path={selected_path})"
        )
    reverse_direction = _flip_direction(direction)
    inward_points = _build_txdd_right_points_outer_to_inner(
        start_corner_index=end_corner_index,
        end_corner_index=start_corner_index,
        direction=reverse_direction,
        turns=turns,
        outer_x=outer_x,
        outer_y=outer_y,
        trace=trace,
        gap=gap,
    )
    points = list(reversed(inward_points))
    resolved_direction = _current_direction_from_xy_points([[point[0], point[1], point[2]] for point in points])
    if resolved_direction != direction:
        raise ValueError(
            "neo tx_dd right inner->outer planner generated unexpected winding "
            f"(actual={resolved_direction}, expected={direction}, selected_path={selected_path})"
        )
    return (
        _shape_points(points),
        start_label,
        end_label,
        direction,
    )


def _translate_points(points: list[Point3], *, dx: float, dy: float, dz: float) -> list[Point3]:
    return [(point[0] + dx, point[1] + dy, point[2] + dz) for point in points]


def _anchor_z_for_single_layer_tx_dd_path(
    *,
    tx_dd_scene: TxDdSceneRegistry,
    transform: dict[str, float],
    board_z: float,
    tx_dd_top_clearance: float,
    cu_thickness: float,
) -> float:
    return tx_dd_scene["region_max"][2] - tx_dd_top_clearance - cu_thickness - board_z + transform["dz"]


def _place_single_layer_tx_dd_path_at_center_y(
    *,
    local_points: list[Point3],
    tx_dd_scene: TxDdSceneRegistry,
    transform: dict[str, float],
    center_y: float,
    anchor_z: float,
) -> list[Point3]:
    local_min_y = min(point[1] for point in local_points)
    local_max_y = max(point[1] for point in local_points)
    min_world_y = local_min_y + center_y
    max_world_y = local_max_y + center_y
    if min_world_y < tx_dd_scene["region_min"][1] or max_world_y > tx_dd_scene["region_max"][1]:
        raise ValueError(
            "neo tx_dd single-layer path must stay inside tx_dd Y bounds "
            f"(min_world_y={min_world_y}, max_world_y={max_world_y}, region_min_y={tx_dd_scene['region_min'][1]}, region_max_y={tx_dd_scene['region_max'][1]})"
        )
    return _translate_points(
        local_points,
        dx=tx_dd_scene["center_x"] + transform["dx"],
        dy=center_y,
        dz=anchor_z,
    )


def _place_single_layer_tx_dd_path_at_center_y_with_left_anchor(
    *,
    local_points: list[Point3],
    tx_dd_scene: TxDdSceneRegistry,
    transform: dict[str, float],
    center_y: float,
    anchor_z: float,
    trace_width: float,
) -> list[Point3]:
    local_min_y = min(point[1] for point in local_points)
    local_max_y = max(point[1] for point in local_points)
    min_world_y = local_min_y + center_y
    max_world_y = local_max_y + center_y
    if min_world_y < tx_dd_scene["region_min"][1] or max_world_y > tx_dd_scene["region_max"][1]:
        raise ValueError(
            "neo tx_dd single-layer path must stay inside tx_dd Y bounds "
            f"(min_world_y={min_world_y}, max_world_y={max_world_y}, region_min_y={tx_dd_scene['region_min'][1]}, region_max_y={tx_dd_scene['region_max'][1]})"
        )
    local_min_x = min(point[0] for point in local_points)
    target_min_centerline_x = tx_dd_scene["region_min"][0] + (trace_width / 2.0)
    return _translate_points(
        local_points,
        dx=(target_min_centerline_x - local_min_x) + transform["dx"],
        dy=center_y,
        dz=anchor_z,
    )


def _place_single_layer_tx_dd_path(
    *,
    local_points: list[Point3],
    tx_dd_scene: TxDdSceneRegistry,
    transform: dict[str, float],
    board_z: float,
    tx_dd_top_clearance: float,
    cu_thickness: float,
) -> tuple[list[Point3], float, float]:
    local_min_y = min(point[1] for point in local_points)
    local_max_y = max(point[1] for point in local_points)
    center_y = (tx_dd_scene["region_max"][1] - local_max_y) + transform["dy"]
    anchor_z = _anchor_z_for_single_layer_tx_dd_path(
        tx_dd_scene=tx_dd_scene,
        transform=transform,
        board_z=board_z,
        tx_dd_top_clearance=tx_dd_top_clearance,
        cu_thickness=cu_thickness,
    )
    world_points = _place_single_layer_tx_dd_path_at_center_y(
        local_points=local_points,
        tx_dd_scene=tx_dd_scene,
        transform=transform,
        center_y=center_y,
        anchor_z=anchor_z,
    )
    return world_points, center_y, anchor_z


def _symmetric_single_layer_tx_dd_inner_edge_center_y(
    *,
    tx_dd_scene: TxDdSceneRegistry,
    transform: dict[str, float],
    group: ResolvedCoilGroup,
    instance_index: int,
    outer_y: float,
    local_points: list[Point3],
    trace_width: float,
) -> float:
    if trace_width <= 0.0:
        raise ValueError(f"neo tx_dd single-layer placement requires trace_width > 0 (actual={trace_width})")
    baseline_center_y, layer_index = _tx_dd_center_y_and_layer(
        layer_count=1,
        instance_count=2,
        instance_index=instance_index,
        pair_clearance_mm=float(group["spacing_mm"]),
        outer_y=outer_y,
        region_center_y=tx_dd_scene["center_y"],
        region_min_y=tx_dd_scene["region_min"][1],
        region_max_y=tx_dd_scene["region_max"][1],
    )
    if layer_index != 0:
        raise ValueError(
            "neo tx_dd single-layer placement must resolve to layer_index=0 "
            f"(actual={layer_index}, instance_index={instance_index})"
        )
    axis_y = tx_dd_scene["center_y"] + transform["dy"]
    inner_edge_distance = (float(group["spacing_mm"]) + trace_width) / 2.0
    local_min_y = min(point[1] for point in local_points)
    local_max_y = max(point[1] for point in local_points)
    if (baseline_center_y + transform["dy"]) >= axis_y:
        return axis_y + inner_edge_distance - local_min_y
    return axis_y - inner_edge_distance - local_max_y


def _instantiate_single_layer_tx_dd_coil(
    *,
    modeler: Modeler3D,
    state: GeometryBuildState,
    design_id: str,
    board_id: str,
    group_instance_index: int,
    name_prefix: str,
    instance_side: Literal["left", "right", "center"],
    path_points: list[Point3],
    trace_width: float,
    thickness: float,
    start_label: TerminalLabel,
    end_label: TerminalLabel,
    current_direction: Literal["cw", "ccw"],
) -> str:
    return NeoCoilInstance(
        name_prefix=name_prefix,
        group_kind="tx_dd",
        board_id=board_id,
        group_instance_index=group_instance_index,
        layer_index=0,
        path_points=path_points,
        trace_width=trace_width,
        thickness=thickness,
        material="copper",
        color_rgb=_NEO_COPPER_COLOR,
        transparency=_NEO_COPPER_TRANSPARENCY,
        plane="XY",
        start_label=start_label,
        end_label=end_label,
        dd_family="tx_dd",
        dd_pair_index=0,
        instance_side=instance_side,
        current_direction=current_direction,
    ).instantiate(
        modeler=modeler,
        state=state,
        design_id=design_id,
    )


def _capture_single_layer_tx_dd_stub_sources(
    *,
    finalize_inputs: FinalizeInputs,
    board_id: str,
    object_name: str,
    path_points: list[Point3],
    trace_width: float,
    instance_side: Literal["left", "right", "center"],
) -> None:
    if board_id not in finalize_inputs.txdd_start_stub_sources:
        finalize_inputs.txdd_start_stub_sources[board_id] = []
    point_lists = [[point[0], point[1], point[2]] for point in path_points]
    start_edge = _edge_points_at_xy_terminal(points=point_lists, trace=trace_width, terminal="start")
    start_role: Literal["feed_in", "inter_half_entry"] = "feed_in" if instance_side == "right" else "inter_half_entry"
    start_landing = _directed_landing_section_from_raw_edge(
        edge=start_edge,
        outward_dir=(-1.0, 0.0, 0.0),
        plane_normal=_XY_PLANE_NORMAL,
        object_name=object_name,
        dd_family="tx_dd",
        dd_pair_index=0,
        side=instance_side,
        terminal_polarity="positive",
        terminal_role=start_role,
        context="neo tx_dd start landing",
    )
    start_landing["inward_dir"] = _xy_terminal_inward_dir(
        points=point_lists,
        terminal="start",
        context="neo tx_dd start landing inward_dir",
    )
    _append_tx_dd_external_stub_source(
        finalize_inputs=finalize_inputs,
        board_id=board_id,
        trace=trace_width,
        landing=start_landing,
        context="neo tx_dd start stub source",
    )
    end_edge = _edge_points_at_xy_terminal(points=point_lists, trace=trace_width, terminal="end")
    end_role: Literal["feed_out", "inter_half_exit"] = "inter_half_exit" if instance_side == "right" else "feed_out"
    end_landing = _directed_landing_section_from_raw_edge(
        edge=end_edge,
        outward_dir=(-1.0, 0.0, 0.0),
        plane_normal=_XY_PLANE_NORMAL,
        object_name=object_name,
        dd_family="tx_dd",
        dd_pair_index=0,
        side=instance_side,
        terminal_polarity="negative",
        terminal_role=end_role,
        context="neo tx_dd end landing",
    )
    end_landing["inward_dir"] = _xy_terminal_inward_dir(
        points=point_lists,
        terminal="end",
        context="neo tx_dd end landing inward_dir",
    )
    _append_tx_dd_external_stub_source(
        finalize_inputs=finalize_inputs,
        board_id=board_id,
        trace=trace_width,
        landing=end_landing,
        context="neo tx_dd end stub source",
    )
    if instance_side == "right":
        finalize_inputs.tx_series_binding.set_once(
            "feed_in",
            start_landing,
            context="neo tx_dd single-layer feed binding",
        )
        finalize_inputs.tx_series_binding.set_once(
            "inter_half_exit",
            end_landing,
            context="neo tx_dd single-layer chain binding",
        )
        return
    finalize_inputs.tx_series_binding.set_once(
        "inter_half_entry",
        start_landing,
        context="neo tx_dd single-layer chain binding",
    )
    finalize_inputs.tx_series_binding.set_once(
        "feed_out",
        end_landing,
        context="neo tx_dd single-layer feed binding",
    )


def _build_single_layer_tx_dd_coil(
    *,
    modeler: Modeler3D,
    ctx: GeometryRuntimeContext,
    state: GeometryBuildState,
    finalize_inputs: FinalizeInputs,
    pcb: ResolvedPcbInstance,
    group: ResolvedCoilGroup,
    geometry: GroupGeometryParams,
    selected_path: str,
    name_prefix: str,
    instance_side: Literal["left", "right", "center"],
    group_instance_index: int,
) -> None:
    transform = _single_transform(group)
    tx_dd_scene = require_tx_dd_scene(ctx)
    local_points, start_label, end_label, current_direction = _resolve_single_layer_path(
        selected_path=selected_path,
        turns=int(geometry["turn_count"]),
        outer_x=ctx.tx_dd_outer_x,
        outer_y=ctx.tx_dd_outer_y,
        trace=float(geometry["trace"]),
        gap=float(geometry["gap"]),
        corner_mode=ctx.corner_mode,
    )
    center_y = _symmetric_single_layer_tx_dd_inner_edge_center_y(
        tx_dd_scene=tx_dd_scene,
        transform=transform,
        group=group,
        instance_index=group_instance_index,
        outer_y=ctx.tx_dd_outer_y,
        local_points=local_points,
        trace_width=float(geometry["trace"]),
    )
    board_z = pcb["position"][2]
    anchor_z = _anchor_z_for_single_layer_tx_dd_path(
        tx_dd_scene=tx_dd_scene,
        transform=transform,
        board_z=board_z,
        tx_dd_top_clearance=ctx.tx_dd_top_clearance,
        cu_thickness=ctx.cu_thickness,
    )
    world_points = _place_single_layer_tx_dd_path_at_center_y_with_left_anchor(
        local_points=local_points,
        tx_dd_scene=tx_dd_scene,
        transform=transform,
        center_y=center_y,
        anchor_z=anchor_z,
        trace_width=float(geometry["trace"]),
    )
    created_name = _instantiate_single_layer_tx_dd_coil(
        modeler=modeler,
        state=state,
        design_id=ctx.design_id,
        board_id=pcb["id"],
        group_instance_index=group_instance_index,
        name_prefix=name_prefix,
        instance_side=instance_side,
        path_points=world_points,
        trace_width=float(geometry["trace"]),
        thickness=ctx.cu_thickness,
        start_label=start_label,
        end_label=end_label,
        current_direction=current_direction,
    )
    _capture_single_layer_tx_dd_stub_sources(
        finalize_inputs=finalize_inputs,
        board_id=pcb["id"],
        object_name=created_name,
        path_points=world_points,
        trace_width=float(geometry["trace"]),
        instance_side=instance_side,
    )


def _build_single_layer_tx_dd_right_coil(
    *,
    modeler: Modeler3D,
    ctx: GeometryRuntimeContext,
    state: GeometryBuildState,
    finalize_inputs: FinalizeInputs,
    pcb: ResolvedPcbInstance,
    group: ResolvedCoilGroup,
    geometry: GroupGeometryParams,
) -> None:
    _build_single_layer_tx_dd_coil(
        modeler=modeler,
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        pcb=pcb,
        group=group,
        geometry=geometry,
        selected_path=str(ctx.selected["neo_tx_dd_right_terminal_path"]),
        name_prefix=_NEO_TX_DD_RIGHT_PREFIX,
        instance_side="right",
        group_instance_index=_right_tx_dd_selector_index(pcb),
    )


def _build_single_layer_tx_dd_left_coil(
    *,
    modeler: Modeler3D,
    ctx: GeometryRuntimeContext,
    state: GeometryBuildState,
    finalize_inputs: FinalizeInputs,
    pcb: ResolvedPcbInstance,
    group: ResolvedCoilGroup,
    geometry: GroupGeometryParams,
) -> None:
    _build_single_layer_tx_dd_coil(
        modeler=modeler,
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        pcb=pcb,
        group=group,
        geometry=geometry,
        selected_path=str(ctx.selected["neo_tx_dd_left_terminal_path"]),
        name_prefix=_NEO_TX_DD_LEFT_PREFIX,
        instance_side="left",
        group_instance_index=_left_tx_dd_selector_index(pcb),
    )


def _create_tx_dd_neo_fr4(
    *,
    modeler: Modeler3D,
    ctx: GeometryRuntimeContext,
    state: GeometryBuildState,
    pcb: ResolvedPcbInstance,
    layer_index: int,
) -> None:
    tx_dd_scene = require_tx_dd_scene(ctx)
    region_min = tx_dd_scene["region_min"]
    region_max = tx_dd_scene["region_max"]
    if ctx.pcb_thickness <= 0.0:
        raise ValueError(f"tx_dd neo FR4 pcb_thickness must be > 0 (actual={ctx.pcb_thickness})")
    span_x = region_max[0] - region_min[0]
    span_y = region_max[1] - region_min[1]
    if span_x <= 0.0 or span_y <= 0.0:
        raise ValueError(
            "tx_dd neo FR4 scene region must have positive XY span "
            f"(region_min={region_min}, region_max={region_max})"
        )
    board_z = pcb["position"][2]
    top_surface_z = tx_dd_scene["region_max"][2] - ctx.tx_dd_top_clearance - ctx.cu_thickness - board_z
    NeoCoilBoxInstance(
        name_prefix=_NEO_TX_DD_FR4_PREFIX,
        board_id=pcb["id"],
        layer_index=layer_index,
        origin_xyz=(region_min[0], region_min[1], top_surface_z - ctx.pcb_thickness),
        size_xyz=(span_x, span_y, ctx.pcb_thickness),
        material="FR4_epoxy",
        color_rgb=_NEO_FR4_EPOXY_GREEN,
        transparency=_NEO_FR4_TRANSPARENCY,
        registry_target="fr4_only",
    ).instantiate(
        modeler=modeler,
        state=state,
        design_id=ctx.design_id,
    )


def _build_single_layer_tx_dd_neo(
    *,
    modeler: Modeler3D,
    ctx: GeometryRuntimeContext,
    state: GeometryBuildState,
    finalize_inputs: FinalizeInputs,
    pcb: ResolvedPcbInstance,
    group: ResolvedCoilGroup,
    geometry: GroupGeometryParams,
) -> None:
    has_tx_dd_mount = _pcb_has_tx_dd_mount(pcb)
    if not has_tx_dd_mount:
        return
    if pcb["id"] not in _SINGLE_LAYER_TX_DD_BOARD_IDS:
        raise ValueError(
            "tx_dd neo single-layer build only supports tx_main_0 "
            f"(pcb_id={pcb['id']}, mounts={pcb['mounts']})"
        )
    _create_tx_dd_neo_fr4(
        modeler=modeler,
        ctx=ctx,
        state=state,
        pcb=pcb,
        layer_index=0,
    )
    _build_single_layer_tx_dd_right_coil(
        modeler=modeler,
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        pcb=pcb,
        group=group,
        geometry=geometry,
    )
    _build_single_layer_tx_dd_left_coil(
        modeler=modeler,
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        pcb=pcb,
        group=group,
        geometry=geometry,
    )


def _build_double_layer_tx_dd_neo(
    *,
    modeler: Modeler3D,
    ctx: GeometryRuntimeContext,
    state: GeometryBuildState,
    pcb: ResolvedPcbInstance,
) -> None:
    has_tx_dd_mount = _pcb_has_tx_dd_mount(pcb)
    if not has_tx_dd_mount:
        return
    if pcb["id"] not in _DOUBLE_LAYER_TX_DD_BOARD_IDS:
        raise ValueError(
            "tx_dd neo double-layer build only supports tx_main_0/tx_main_1 "
            f"(pcb_id={pcb['id']}, mounts={pcb['mounts']})"
        )
    assert pcb["id"] in _TX_DD_LAYER_INDEX_BY_BOARD_ID, f"missing tx_dd neo layer index for {pcb['id']}"
    _create_tx_dd_neo_fr4(
        modeler=modeler,
        ctx=ctx,
        state=state,
        pcb=pcb,
        layer_index=_TX_DD_LAYER_INDEX_BY_BOARD_ID[pcb["id"]],
    )


def build_for_board(
    *,
    modeler: Modeler3D,
    ctx: GeometryRuntimeContext,
    state: GeometryBuildState,
    finalize_inputs: FinalizeInputs,
    board_idx: int,
    pcb: ResolvedPcbInstance,
    group: ResolvedCoilGroup,
    geometry: GroupGeometryParams,
    edge_points_at_path_end: Callable[..., Edge2P],
) -> None:
    _ = board_idx, edge_points_at_path_end
    if pcb["id"] not in finalize_inputs.txdd_start_stub_sources:
        finalize_inputs.txdd_start_stub_sources[pcb["id"]] = []
    if group["kind"] != "tx_dd":
        raise ValueError(f"tx_dd neo builder only supports tx_dd groups (actual={group['kind']})")
    if pcb["role"] != "tx":
        if _pcb_has_tx_dd_mount(pcb):
            raise ValueError(
                "tx_dd neo builder found tx_dd mount on non-tx pcb "
                f"(pcb_id={pcb['id']}, role={pcb['role']})"
            )
        return
    layer_count = int(group["layer_count"])
    if layer_count == 1:
        _build_single_layer_tx_dd_neo(
            modeler=modeler,
            ctx=ctx,
            state=state,
            finalize_inputs=finalize_inputs,
            pcb=pcb,
            group=group,
            geometry=geometry,
        )
        return
    if layer_count == 2:
        _build_double_layer_tx_dd_neo(
            modeler=modeler,
            ctx=ctx,
            state=state,
            pcb=pcb,
        )
        return
    raise ValueError(f"tx_dd neo builder only supports layer_count 1 or 2 (actual={layer_count})")

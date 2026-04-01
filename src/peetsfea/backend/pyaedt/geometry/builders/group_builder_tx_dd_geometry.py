from __future__ import annotations

from typing import Literal, cast

from peetsfea.aedt import Object3d
from peetsfea.aedt import Modeler3D
from peetsfea.types.manifest import ResolvedPcbMount

from ..build_state import DirectedLandingSection, Edge2P, FinalizeInputs, OrderedTerminalSection, Point3
from ..rules.solid_ops import safe_unite
from ..rules.cad_probe import _object_name


_XY_PLANE_NORMAL: Point3 = (0.0, 0.0, 1.0)
_TXDD_VIA_TAB_LENGTH_W = 2.0
_ABSENT_DD_PAIR_INDEX = -1


def _normalize_vector3(vector: Point3, *, context: str) -> Point3:
    length = ((vector[0] ** 2) + (vector[1] ** 2) + (vector[2] ** 2)) ** 0.5
    if length <= 1e-12:
        raise ValueError(f"{context} must have non-zero length")
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def _cross3(first: Point3, second: Point3) -> Point3:
    return (
        (first[1] * second[2]) - (first[2] * second[1]),
        (first[2] * second[0]) - (first[0] * second[2]),
        (first[0] * second[1]) - (first[1] * second[0]),
    )


def _ordered_terminal_section_from_center_tangent(
    *,
    center: Point3,
    tangent_out: Point3,
    plane_normal: Point3,
    trace: float,
    context: str,
) -> OrderedTerminalSection:
    if trace <= 0.0:
        raise ValueError(f"{context} trace must be > 0 (actual={trace})")
    tangent_unit = _normalize_vector3(tangent_out, context=f"{context} tangent_out")
    plane_normal_unit = _normalize_vector3(plane_normal, context=f"{context} plane_normal")
    width_dir = _normalize_vector3(
        _cross3(plane_normal_unit, tangent_unit),
        context=f"{context} width_dir",
    )
    half_trace = trace / 2.0
    p0: Point3 = (
        center[0] + (width_dir[0] * half_trace),
        center[1] + (width_dir[1] * half_trace),
        center[2] + (width_dir[2] * half_trace),
    )
    p1: Point3 = (
        center[0] - (width_dir[0] * half_trace),
        center[1] - (width_dir[1] * half_trace),
        center[2] - (width_dir[2] * half_trace),
    )
    return {
        "p0": p0,
        "p1": p1,
        "center": center,
        "tangent_out": tangent_unit,
        "plane_normal": plane_normal_unit,
    }


def _ordered_xy_terminal_section(
    *,
    points: list[list[float]],
    trace: float,
    terminal: Literal["start", "end"],
    context: str,
) -> OrderedTerminalSection:
    if len(points) < 2:
        raise ValueError(f"{context} requires at least 2 points")
    if terminal == "start":
        terminal_point = points[0]
        neighbor_point = points[1]
    else:
        terminal_point = points[-1]
        neighbor_point = points[-2]
    center: Point3 = cast(Point3, tuple(float(v) for v in terminal_point))
    tangent_out: Point3 = (
        float(terminal_point[0] - neighbor_point[0]),
        float(terminal_point[1] - neighbor_point[1]),
        float(terminal_point[2] - neighbor_point[2]),
    )
    return _ordered_terminal_section_from_center_tangent(
        center=center,
        tangent_out=tangent_out,
        plane_normal=_XY_PLANE_NORMAL,
        trace=trace,
        context=context,
    )


def _xy_terminal_inward_dir(
    *,
    points: list[list[float]],
    terminal: Literal["start", "end"],
    context: str,
) -> Point3:
    if len(points) < 2:
        raise ValueError(f"{context} requires at least 2 points")
    if terminal == "start":
        terminal_point = points[0]
        neighbor_point = points[1]
    else:
        terminal_point = points[-1]
        neighbor_point = points[-2]
    return _normalize_vector3(
        (
            float(neighbor_point[0] - terminal_point[0]),
            float(neighbor_point[1] - terminal_point[1]),
            float(neighbor_point[2] - terminal_point[2]),
        ),
        context=context,
    )


def _translate_point3_local(point: Point3, *, dx: float, dy: float, dz: float) -> Point3:
    return (point[0] + dx, point[1] + dy, point[2] + dz)


def _translate_edge2p_local(edge: Edge2P, *, dx: float, dy: float, dz: float) -> Edge2P:
    return (
        _translate_point3_local(edge[0], dx=dx, dy=dy, dz=dz),
        _translate_point3_local(edge[1], dx=dx, dy=dy, dz=dz),
    )


def _center_directed_tail_end(
    point: Point3,
    *,
    center_xy: tuple[float, float],
    trace: float,
    context: str,
) -> Point3:
    if trace <= 0.0:
        raise ValueError(f"{context} trace must be > 0 (actual={trace})")
    center_dx = center_xy[0] - point[0]
    center_dy = center_xy[1] - point[1]
    center_len = (center_dx * center_dx + center_dy * center_dy) ** 0.5
    if center_len <= 1e-12:
        raise ValueError(f"{context} center-directed tail cannot be resolved from zero-length vector")
    return (
        point[0] + ((center_dx / center_len) * trace),
        point[1] + ((center_dy / center_len) * trace),
        point[2],
    )


def _distance_sq_xy(point: Point3, *, center_xy: tuple[float, float]) -> float:
    dx = point[0] - center_xy[0]
    dy = point[1] - center_xy[1]
    return (dx * dx) + (dy * dy)


def _terminal_turn_sign(points: list[list[float]], *, terminal_kind: Literal["start", "end"], context: str) -> float:
    if len(points) < 3:
        raise ValueError(f"{context} requires at least 3 points to resolve turn sign")
    if terminal_kind == "start":
        first = points[0]
        second = points[1]
        third = points[2]
        v1x = second[0] - first[0]
        v1y = second[1] - first[1]
        v2x = third[0] - second[0]
        v2y = third[1] - second[1]
    elif terminal_kind == "end":
        first = points[-3]
        second = points[-2]
        third = points[-1]
        v1x = second[0] - first[0]
        v1y = second[1] - first[1]
        v2x = third[0] - second[0]
        v2y = third[1] - second[1]
    else:
        raise ValueError(f"{context} terminal_kind must be start/end (actual={terminal_kind})")
    return (v1x * v2y) - (v1y * v2x)


def _build_center_directed_tail_outline(
    *,
    terminal_edge: Edge2P,
    center_xy: tuple[float, float],
    inward_tangent_xy: tuple[float, float],
    terminal_kind: Literal["start", "end"],
    turn_sign: float,
    trace: float,
    length: float,
    context: str,
) -> tuple[list[list[float]], Edge2P, Point3]:
    if trace <= 0.0:
        raise ValueError(f"{context} trace must be > 0 (actual={trace})")
    if length <= 0.0:
        raise ValueError(f"{context} length must be > 0 (actual={length})")
    if terminal_kind == "start":
        anchor_corner = terminal_edge[1] if turn_sign >= 0.0 else terminal_edge[0]
    elif terminal_kind == "end":
        anchor_corner = terminal_edge[0] if turn_sign >= 0.0 else terminal_edge[1]
    else:
        raise ValueError(f"{context} terminal_kind must be start/end (actual={terminal_kind})")
    edge_midpoint: Point3 = (
        (terminal_edge[0][0] + terminal_edge[1][0]) / 2.0,
        (terminal_edge[0][1] + terminal_edge[1][1]) / 2.0,
        (terminal_edge[0][2] + terminal_edge[1][2]) / 2.0,
    )
    width_dx = anchor_corner[0] - edge_midpoint[0]
    width_dy = anchor_corner[1] - edge_midpoint[1]
    width_len = (width_dx * width_dx + width_dy * width_dy) ** 0.5
    tangent_dx, tangent_dy = inward_tangent_xy
    tangent_len = (tangent_dx * tangent_dx + tangent_dy * tangent_dy) ** 0.5
    if width_len <= 1e-12 or tangent_len <= 1e-12:
        raise ValueError(f"{context} center-directed tail cannot be resolved from zero-length geometry")
    dir_x = (width_dx / width_len) + (tangent_dx / tangent_len)
    dir_y = (width_dy / width_len) + (tangent_dy / tangent_len)
    dir_len = (dir_x * dir_x + dir_y * dir_y) ** 0.5
    if dir_len <= 1e-12:
        raise ValueError(f"{context} center-directed tail cannot be resolved from degenerate direction")
    dir_x /= dir_len
    dir_y /= dir_len
    perp_x = -dir_y
    perp_y = dir_x
    other_terminal_corner = terminal_edge[0] if anchor_corner == terminal_edge[1] else terminal_edge[1]
    width_candidate_pos: Point3 = (
        anchor_corner[0] + (perp_x * trace),
        anchor_corner[1] + (perp_y * trace),
        anchor_corner[2],
    )
    width_candidate_neg: Point3 = (
        anchor_corner[0] - (perp_x * trace),
        anchor_corner[1] - (perp_y * trace),
        anchor_corner[2],
    )
    near_second = min(
        (width_candidate_pos, width_candidate_neg),
        key=lambda point: ((point[0] - other_terminal_corner[0]) ** 2) + ((point[1] - other_terminal_corner[1]) ** 2),
    )
    far_first: Point3 = (
        anchor_corner[0] + (dir_x * length),
        anchor_corner[1] + (dir_y * length),
        anchor_corner[2],
    )
    far_second: Point3 = (
        near_second[0] + (dir_x * length),
        near_second[1] + (dir_y * length),
        near_second[2],
    )
    outline_points = [
        [anchor_corner[0], anchor_corner[1], anchor_corner[2]],
        [near_second[0], near_second[1], near_second[2]],
        [far_second[0], far_second[1], far_second[2]],
        [far_first[0], far_first[1], far_first[2]],
    ]
    far_edge: Edge2P = (far_first, far_second)
    far_midpoint: Point3 = (
        (far_first[0] + far_second[0]) / 2.0,
        (far_first[1] + far_second[1]) / 2.0,
        (far_first[2] + far_second[2]) / 2.0,
    )
    return outline_points, far_edge, far_midpoint


def _create_txdd_terminal_tail(
    *,
    modeler: Modeler3D,
    base_object_name: str,
    tail_suffix: str,
    tail_outline_points: list[list[float]],
    trace: float,
    cu_thickness: float,
    context: str,
) -> str:
    tail_name = f"{base_object_name}_{tail_suffix}"
    tail_created = modeler.create_polyline(
        points=tail_outline_points,
        name=tail_name,
        material="copper",
        close_surface=True,
    )
    if not tail_created:
        raise ValueError(f"{context} tail polyline creation failed (name={tail_name})")
    tail_loop_obj = cast(Object3d, tail_created)
    tail_loop_name = _object_name(tail_loop_obj)
    covered = modeler.cover_lines(assignment=tail_loop_name)  # type: ignore[misc]
    if not covered:
        raise ValueError(f"{context} tail cover_lines failed (name={tail_name})")
    if covered is True:
        covered_name = tail_loop_name
    else:
        covered_name = covered if isinstance(covered, str) else _object_name(cast(Object3d, covered))
    thickened = modeler.thicken_sheet(assignment=covered_name, thickness=cu_thickness)  # type: ignore[misc]
    if not thickened:
        raise ValueError(f"{context} tail thicken failed (name={tail_name})")
    thickened_name = thickened if isinstance(thickened, str) else _object_name(cast(Object3d, thickened))
    return safe_unite(
        modeler=modeler,
        targets=[base_object_name, thickened_name],
        error_context=context,
    )


def _normalize_tail_inward_dir(
    *,
    from_point: Point3,
    to_point: Point3,
    context: str,
) -> Point3:
    return _normalize_vector3(
        (
            from_point[0] - to_point[0],
            from_point[1] - to_point[1],
            from_point[2] - to_point[2],
        ),
        context=context,
    )


def _iter_tx_dd_slots(layer_count: int) -> tuple[tuple[int, int], ...]:
    if layer_count == 1:
        return ((0, 1),)
    if layer_count == 2:
        return ((0, 1), (1, 3))
    raise ValueError(f"tx_dd layer_count must be 1 or 2 (actual={layer_count})")


def _txdd_layer_slot_from_selector_index(selector_index: int, *, layer_count: int) -> int:
    if selector_index < 0 or selector_index >= (layer_count * 2):
        raise ValueError(
            "tx_dd mount selector_index must reference a valid half-instance "
            f"(selector_index={selector_index}, layer_count={layer_count})"
        )
    return selector_index // 2


def _txdd_expected_slot_indices_for_layer(layer_index: int, *, layer_count: int) -> frozenset[int]:
    if layer_index < 0 or layer_index >= layer_count:
        raise ValueError(
            "tx_dd layer slot must reference a valid realized layer "
            f"(layer_index={layer_index}, layer_count={layer_count})"
        )
    start = layer_index * 2
    return frozenset((start, start + 1))


def _txdd_slot_is_mounted(
    mounts: list[ResolvedPcbMount],
    *,
    layer_index: int,
    layer_count: int,
) -> bool:
    mounted_half_indices: set[int] = set()
    for mount in mounts:
        if mount["kind"] != "tx_dd":
            continue
        selector_mode = mount["selector_mode"]
        selector_index = mount["selector_index"]
        if selector_mode == "all":
            return True
        if selector_mode != "index":
            continue
        assert isinstance(selector_index, int), "tx_dd index mount must declare selector_index"
        resolved_index = selector_index
        resolved_layer_index = _txdd_layer_slot_from_selector_index(
            resolved_index,
            layer_count=layer_count,
        )
        if resolved_layer_index == layer_index:
            mounted_half_indices.add(resolved_index)
    if not mounted_half_indices:
        return False
    expected_slot_indices = _txdd_expected_slot_indices_for_layer(
        layer_index,
        layer_count=layer_count,
    )
    return bool(mounted_half_indices & expected_slot_indices)


def _edge_midpoint(edge: Edge2P) -> Point3:
    return (
        (edge[0][0] + edge[1][0]) / 2.0,
        (edge[0][1] + edge[1][1]) / 2.0,
        (edge[0][2] + edge[1][2]) / 2.0,
    )


def _ordered_terminal_section_from_landing(landing: DirectedLandingSection) -> OrderedTerminalSection:
    return {
        "p0": landing["p_plus"],
        "p1": landing["p_minus"],
        "center": landing["center"],
        "tangent_out": landing["outward_dir"],
        "plane_normal": landing["plane_normal"],
    }


def _append_tx_dd_external_stub_source(
    *,
    finalize_inputs: FinalizeInputs,
    board_id: str,
    trace: float,
    landing: DirectedLandingSection,
    context: str,
) -> None:
    if landing["dd_family"] != "tx_dd":
        raise ValueError(
            f"{context} contract violation: external tx_dd stub source must come from tx_dd landings "
            f"(dd_family={landing['dd_family']})"
        )
    object_name = landing["object_name"]
    if not object_name:
        raise ValueError(f"{context} contract violation: external tx_dd stub source object_name is empty")
    assert board_id in finalize_inputs.txdd_start_stub_sources, f"{context} contract violation: board_id {board_id} not registered"
    inward_dir_present = "inward_dir" in landing
    if inward_dir_present:
        inward_dir = cast(Point3, landing["inward_dir"])
        finalize_inputs.txdd_start_stub_sources[board_id].append((landing["center"], trace, object_name, inward_dir))
        return
    finalize_inputs.txdd_start_stub_sources[board_id].append((landing["center"], trace, object_name))


def _directed_landing_section_from_raw_edge(
    *,
    edge: Edge2P,
    outward_dir: Point3,
    plane_normal: Point3,
    object_name: str,
    dd_family: Literal["none", "tx_dd", "rx_dd"],
    dd_pair_index: int,
    side: Literal["left", "right", "center"],
    terminal_polarity: Literal["positive", "negative", "neutral"],
    terminal_role: Literal[
        "none",
        "feed_in",
        "feed_out",
        "inter_half_entry",
        "inter_half_exit",
        "series_entry",
        "series_exit",
    ],
    context: str,
) -> DirectedLandingSection:
    outward_unit = _normalize_vector3(outward_dir, context=f"{context} outward_dir")
    plane_normal_unit = _normalize_vector3(plane_normal, context=f"{context} plane_normal")
    center = _edge_midpoint(edge)
    return {
        "p_plus": edge[0],
        "p_minus": edge[1],
        "center": center,
        "outward_dir": outward_unit,
        "plane_normal": plane_normal_unit,
        "object_name": object_name,
        "dd_family": dd_family,
        "dd_pair_index": dd_pair_index,
        "side": side,
        "terminal_polarity": terminal_polarity,
        "terminal_role": terminal_role,
    }

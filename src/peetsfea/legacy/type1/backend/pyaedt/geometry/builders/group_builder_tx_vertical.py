from __future__ import annotations

from typing import Callable, Literal, cast

from peetsfea.aedt import Modeler3D

from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance, TerminalLabel
from peetsfea.types.runtime_selection import coil_group_selected_count

from ..build_state import (
    BridgeAnchor,
    DirectedLandingSection,
    Edge2P,
    FinalizeInputs,
    GeometryBuildState,
    GeometryRuntimeContext,
    NO_DD_PAIR_INDEX,
    OrderedTerminalSection,
    Point3,
    TxVerticalLinkNode,
    require_tx_vertical_scene,
    state_is_set,
)
from ..rules.debug_checks import _bbox_violations
from ..rules.placement_rules import (
    _coil_instance_offset,
    _instance_side,
    _max_feasible_turns,
    _mount_allows_instance,
)
from ..rules.spiral_points import (
    _build_rect_spiral_centerline_absolute,
    _map_xy_points_to_zx,
)
from .neo_coil_instance import NeoCoilInstance

_ZX_PLANE_NORMAL: Point3 = (0.0, -1.0, 0.0)
_NEO_TX_VERTICAL_PREFIX = "neo_coil_tx_vertical_"
_NEO_COPPER_COLOR = (184, 115, 51)
_NEO_COPPER_TRANSPARENCY = 0.0


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


def _tx_vertical_ordered_terminal_section(
    *,
    points: list[list[float]],
    trace: float,
    terminal_kind: Literal["outer_right", "outer_left"],
) -> OrderedTerminalSection:
    if len(points) < 2:
        raise ValueError("tx_vertical ordered terminal section requires at least 2 points")
    start = points[0]
    end = points[-1]
    choose_start = (start[2] > end[2]) or (abs(start[2] - end[2]) <= 1e-12 and start[0] < end[0])
    if terminal_kind == "outer_right":
        terminal_point, neighbor_point = (start, points[1]) if choose_start else (end, points[-2])
    else:
        terminal_point, neighbor_point = (end, points[-2]) if choose_start else (start, points[1])
    plane_normal = _ZX_PLANE_NORMAL
    center: Point3 = cast(Point3, tuple(float(v) for v in terminal_point))
    tangent_out: Point3 = (
        float(terminal_point[0] - neighbor_point[0]),
        float(terminal_point[1] - neighbor_point[1]),
        float(terminal_point[2] - neighbor_point[2]),
    )
    return _ordered_terminal_section_from_center_tangent(
        center=center,
        tangent_out=tangent_out,
        plane_normal=plane_normal,
        trace=trace,
        context=f"tx_vertical {terminal_kind} ordered terminal section",
    )


def _edge_midpoint(edge: Edge2P) -> Point3:
    return (
        (edge[0][0] + edge[1][0]) / 2.0,
        (edge[0][1] + edge[1][1]) / 2.0,
        (edge[0][2] + edge[1][2]) / 2.0,
    )


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
    return {
        "p_plus": edge[0],
        "p_minus": edge[1],
        "center": _edge_midpoint(edge),
        "outward_dir": outward_unit,
        "plane_normal": plane_normal_unit,
        "object_name": object_name,
        "dd_family": dd_family,
        "dd_pair_index": dd_pair_index,
        "side": side,
        "terminal_polarity": terminal_polarity,
        "terminal_role": terminal_role,
    }


def _assign_tx_series_terminal_once(
    *,
    finalize_inputs: FinalizeInputs,
    terminal_name: Literal["series_entry", "series_exit"],
    landing: DirectedLandingSection,
    context: str,
) -> None:
    finalize_inputs.tx_series_binding.set_once(terminal_name, landing, context=context)


def _resolve_tx_vertical_zx_series_chain_landings_from_nodes(
    *,
    nodes: list[TxVerticalLinkNode],
) -> tuple[DirectedLandingSection, DirectedLandingSection]:
    if not nodes:
        raise ValueError("tx_vertical ZX series-chain contract violation: expected at least 1 linked node")
    sorted_nodes = sorted(nodes, key=lambda node: (node[4], node[0], node[1]))
    lower_node = sorted_nodes[0]
    upper_node = sorted_nodes[-1]
    series_entry = _directed_landing_section_from_raw_edge(
        edge=lower_node[8],
        outward_dir=(1.0, 0.0, 0.0),
        plane_normal=_ZX_PLANE_NORMAL,
        object_name=lower_node[1],
        dd_family="none",
        dd_pair_index=NO_DD_PAIR_INDEX,
        side="left",
        terminal_polarity="positive",
        terminal_role="series_entry",
        context="tx_vertical ZX series_entry landing",
    )
    series_exit = _directed_landing_section_from_raw_edge(
        edge=upper_node[7],
        outward_dir=(1.0, 0.0, 0.0),
        plane_normal=_ZX_PLANE_NORMAL,
        object_name=upper_node[1],
        dd_family="none",
        dd_pair_index=NO_DD_PAIR_INDEX,
        side="right",
        terminal_polarity="negative",
        terminal_role="series_exit",
        context="tx_vertical ZX series_exit landing",
    )
    return series_entry, series_exit


def _build_tx_vertical_local_points(
    *,
    turns: int,
    outer_x: float,
    outer_z: float,
    trace: float,
    gap: float,
    corner_mode: int,
) -> list[list[float]]:
    return [
        list(point)
        for point in _build_rect_spiral_centerline_absolute(
            turns=turns,
            outer_x=outer_x,
            outer_y=outer_z,
            trace=trace,
            gap=gap,
            z=0.0,
            corner_mode=corner_mode,
        )
    ]


def _parse_tx_vertical_terminal_path_contract(
    selected_path: str,
) -> tuple[TerminalLabel, TerminalLabel, Literal["cw", "ccw"]]:
    parts = selected_path.split("_")
    if len(parts) != 4 or parts[2] != "to":
        raise ValueError(
            "neo tx_vertical terminal path must match '<start>_<cw|ccw>_to_<end>' "
            f"(actual={selected_path})"
        )
    start_label = parts[0]
    direction = parts[1]
    end_label = parts[3]
    if start_label not in {"A", "B", "C", "D", "a", "b", "c", "d"}:
        raise ValueError(f"neo tx_vertical terminal path start terminal is unsupported (actual={start_label})")
    if end_label not in {"A", "B", "C", "D", "a", "b", "c", "d"}:
        raise ValueError(f"neo tx_vertical terminal path end terminal is unsupported (actual={end_label})")
    if direction not in {"cw", "ccw"}:
        raise ValueError(f"neo tx_vertical terminal path direction must be 'cw' or 'ccw' (actual={direction})")
    if start_label.isupper() == end_label.isupper():
        raise ValueError(
            "neo tx_vertical terminal path must use one uppercase and one lowercase terminal "
            f"(actual={selected_path})"
        )
    return (
        cast(TerminalLabel, start_label),
        cast(TerminalLabel, end_label),
        cast(Literal["cw", "ccw"], direction),
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
    edge_points_at_tx_vertical_terminal: Callable[..., Edge2P],
    edge_points_at_tx_vertical_opposite_terminal: Callable[..., Edge2P],
    tx_vertical_bridge_edges_from_node: Callable[..., tuple[Edge2P, Edge2P]],
) -> None:
    if group["kind"] != "tx_vertical":
        raise ValueError(f"tx_vertical builder contract violation: unsupported group kind {group['kind']}")
    tx_vertical_scene = require_tx_vertical_scene(ctx)
    tx_vertical_region_min = tx_vertical_scene["region_min"]
    tx_vertical_region_max = tx_vertical_scene["region_max"]
    tx_vertical_center_x = tx_vertical_scene["center_x"]
    tx_vertical_center_y = tx_vertical_scene["center_y"]
    has_tx_vertical_mount = any(mount["kind"] == "tx_vertical" for mount in pcb["mounts"])

    turns = geometry["turn_count"]
    trace = geometry["trace"]
    gap = geometry["gap"]
    if turns < 1:
        raise ValueError("selected_group_geometry.tx_vertical.turn_count must be >= 1")
    if turns > 9:
        raise ValueError("selected_group_geometry.tx_vertical.turn_count must be <= 9")
    if trace <= 0:
        raise ValueError("selected_group_geometry.tx_vertical.trace must be > 0")
    if gap < 0:
        raise ValueError("selected_group_geometry.tx_vertical.gap must be >= 0")

    tx_vertical_zone_h = tx_vertical_region_max[2] - tx_vertical_region_min[2]
    tx_vertical_outer_z = min(ctx.tx_vertical_outer_y, tx_vertical_zone_h)
    tx_vertical_span_primary = ctx.tx_vertical_outer_x
    tx_vertical_max_turns = min(
        _max_feasible_turns(tx_vertical_span_primary, trace, gap),
        _max_feasible_turns(tx_vertical_outer_z, trace, gap),
    )
    if tx_vertical_max_turns < 1:
        raise ValueError(
            "tx_vertical cannot fit in tx_region_vertical "
            f"(available_primary_span={tx_vertical_span_primary}, available_outer_z={tx_vertical_outer_z})"
        )
    if turns > tx_vertical_max_turns:
        raise ValueError(
            "Infeasible turn_count for tx_vertical: "
            f"requested={turns}, feasible_max={tx_vertical_max_turns} "
            f"(primary_span={tx_vertical_span_primary}, outer_z={tx_vertical_outer_z}, trace={trace}, gap={gap})"
        )
    if ctx.tx_vertical_orientation_mode != 1:
        raise ValueError(
            "tx_vertical orientation_mode contract violation: only mode 1 is supported "
            f"(actual={ctx.tx_vertical_orientation_mode})"
        )
    if ctx.tx_vertical_plane != "ZX":
        raise ValueError("tx_vertical plane contract violation: expected ZX")
    tx_vertical_points = _build_tx_vertical_local_points(
        turns=turns,
        outer_x=tx_vertical_span_primary,
        outer_z=tx_vertical_outer_z,
        trace=trace,
        gap=gap,
        corner_mode=ctx.corner_mode,
    )
    tx_vertical_center_z = tx_vertical_region_min[2] + (tx_vertical_outer_z / 2.0)
    zx_start_label, zx_end_label, zx_current_direction = _parse_tx_vertical_terminal_path_contract(
        ctx.selected["neo_tx_vertical_zx_terminal_path"]
    )

    instance_count = coil_group_selected_count(group)
    spacing_mm = group["spacing_mm"]
    transforms = group["instance_transforms"]
    transform = transforms[0] if transforms else {"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0}

    def _register_tx_vertical_path(
        *,
        world_points: list[list[float]],
        group_instance_index: int,
        side: Literal["left", "right", "center"],
        start_label: TerminalLabel,
        end_label: TerminalLabel,
        current_direction: Literal["cw", "ccw"],
        register_link_node: bool = True,
    ) -> tuple[str, float, Edge2P, Edge2P, Point3, Point3, Edge2P, Edge2P]:
        obj_name = NeoCoilInstance(
            name_prefix=_NEO_TX_VERTICAL_PREFIX,
            group_kind="tx_vertical",
            board_id=pcb["id"],
            group_instance_index=group_instance_index,
            layer_index=0,
            path_points=[cast(Point3, tuple(float(v) for v in point)) for point in world_points],
            trace_width=trace,
            thickness=ctx.cu_thickness,
            material="copper",
            color_rgb=_NEO_COPPER_COLOR,
            transparency=_NEO_COPPER_TRANSPARENCY,
            plane="ZX",
            start_label=start_label,
            end_label=end_label,
            dd_family="none",
            dd_pair_index=NO_DD_PAIR_INDEX,
            instance_side=side,
            current_direction=current_direction,
        ).instantiate(
            modeler=modeler,
            state=state,
            design_id=ctx.design_id,
        )
        assert state.cad_probe, "neo tx_vertical instantiate must append cad_probe"
        probe = state.cad_probe[-1]
        state.coil_plane_bboxes.append((pcb["id"], "ZX", probe["bbox"]))

        violations = _bbox_violations(
            object_name=obj_name,
            bbox=probe["bbox"],
            region_kind="tx_region_vertical",
            region_min=tx_vertical_region_min,
            region_max=tx_vertical_region_max,
        )
        if violations:
            state.placement_violations.extend(violations)
            first = violations[0]
            raise ValueError(
                f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
                f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
            )
        start_xyz = cast(Point3, tuple(float(v) for v in world_points[0]))
        end_xyz = cast(Point3, tuple(float(v) for v in world_points[-1]))
        y_center = (probe["bbox"][1] + probe["bbox"][4]) / 2.0
        outer_right_section = _tx_vertical_ordered_terminal_section(
            points=world_points,
            trace=trace,
            terminal_kind="outer_right",
        )
        outer_left_section = _tx_vertical_ordered_terminal_section(
            points=world_points,
            trace=trace,
            terminal_kind="outer_left",
        )
        terminal_edge = cast(Edge2P, (outer_right_section["p0"], outer_right_section["p1"]))
        opposite_terminal_edge = cast(Edge2P, (outer_left_section["p0"], outer_left_section["p1"]))
        bridge_out_edge, bridge_in_edge = tx_vertical_bridge_edges_from_node(
            points=world_points,
            start_xyz=start_xyz,
            end_xyz=end_xyz,
            trace=trace,
            tx_vertical_region_min=tx_vertical_region_min,
            tx_vertical_region_max=tx_vertical_region_max,
            cu_thickness=ctx.cu_thickness,
        )
        outer_right_edge = terminal_edge
        outer_left_edge = opposite_terminal_edge
        right_key = (-y_center, pcb["id"], group_instance_index)
        if (
            not state_is_set(finalize_inputs.tx_vertical_outer_right_selection_key)
            or right_key < finalize_inputs.tx_vertical_outer_right_selection_key
        ):
            outer_right_landing = _directed_landing_section_from_raw_edge(
                edge=outer_right_edge,
                outward_dir=(1.0, 0.0, 0.0),
                plane_normal=outer_right_section["plane_normal"],
                object_name=obj_name,
                dd_family="none",
                dd_pair_index=NO_DD_PAIR_INDEX,
                side="right",
                terminal_polarity="neutral",
                terminal_role="none",
                context="tx_vertical outer right directed landing",
            )
            finalize_inputs.tx_vertical_outer_right_selection_key = right_key
            finalize_inputs.tx_vertical_global_outer_right_edge = outer_right_edge
            finalize_inputs.tx_vertical_global_outer_right_section = outer_right_section
            finalize_inputs.tx_vertical_global_outer_right_landing = outer_right_landing
            finalize_inputs.tx_vertical_global_outer_right_anchor = cast(
                BridgeAnchor,
                {
                    "center": outer_right_section["center"],
                    "trace": trace,
                    "plane_normal": outer_right_section["plane_normal"],
                    "object_name": obj_name,
                    "dd_family": "none",
                    "dd_pair_index": NO_DD_PAIR_INDEX,
                    "side": "right",
                },
            )
        left_key = (y_center, pcb["id"], group_instance_index)
        if (
            not state_is_set(finalize_inputs.tx_vertical_outer_left_selection_key)
            or left_key < finalize_inputs.tx_vertical_outer_left_selection_key
        ):
            outer_left_landing = _directed_landing_section_from_raw_edge(
                edge=outer_left_edge,
                outward_dir=(1.0, 0.0, 0.0),
                plane_normal=outer_left_section["plane_normal"],
                object_name=obj_name,
                dd_family="none",
                dd_pair_index=NO_DD_PAIR_INDEX,
                side="left",
                terminal_polarity="neutral",
                terminal_role="none",
                context="tx_vertical outer left directed landing",
            )
            finalize_inputs.tx_vertical_outer_left_selection_key = left_key
            finalize_inputs.tx_vertical_global_outer_left_edge = outer_left_edge
            finalize_inputs.tx_vertical_global_outer_left_section = outer_left_section
            finalize_inputs.tx_vertical_global_outer_left_landing = outer_left_landing
            finalize_inputs.tx_vertical_global_outer_left_anchor = cast(
                BridgeAnchor,
                {
                    "center": outer_left_section["center"],
                    "trace": trace,
                    "plane_normal": outer_left_section["plane_normal"],
                    "object_name": obj_name,
                    "dd_family": "none",
                    "dd_pair_index": NO_DD_PAIR_INDEX,
                    "side": "left",
                },
            )
        if register_link_node:
            board_key = (pcb["id"], board_idx)
            if board_key not in finalize_inputs.tx_vertical_nodes_by_board:
                finalize_inputs.tx_vertical_nodes_by_board[board_key] = []
            board_nodes = finalize_inputs.tx_vertical_nodes_by_board[board_key]
            board_nodes.append(
                (group_instance_index, obj_name, start_xyz, end_xyz, y_center, trace, world_center_x, bridge_out_edge, bridge_in_edge)
            )
        return (
            obj_name,
            y_center,
            bridge_out_edge,
            bridge_in_edge,
            start_xyz,
            end_xyz,
            terminal_edge,
            opposite_terminal_edge,
        )

    for instance_index in range(instance_count):
        if not _mount_allows_instance(pcb["mounts"], "tx_vertical", instance_index):
            continue
        off_x, off_y, off_z = _coil_instance_offset(
            "tx_vertical",
            instance_index,
            instance_count,
            spacing_mm,
            trace_mm=trace,
        )
        side = _instance_side("tx_vertical", (off_x, off_y, off_z))
        world_center_x = tx_vertical_center_x + transform["dx"] + off_x
        logical_center_y = tx_vertical_center_y + transform["dy"] + off_y
        world_center_z = tx_vertical_center_z + transform["dz"] + off_z
        top_points = _map_xy_points_to_zx(
            tx_vertical_points,
            x_center=world_center_x,
            y_const=logical_center_y,
            z_center=world_center_z,
        )
        _register_tx_vertical_path(
            world_points=top_points,
            group_instance_index=instance_index,
            side=side,
            start_label=zx_start_label,
            end_label=zx_end_label,
            current_direction=zx_current_direction,
        )
    # ZX active-path truth is owned only by actual tx_vertical link nodes on the mounted host board.
    # Global outer-* fields may still exist as geometry/debug metadata, but they must never drive
    # series_entry / series_exit capture for non-host boards or host boards without linked nodes.
    if not has_tx_vertical_mount:
        return
    board_key = (pcb["id"], board_idx)
    if board_key not in finalize_inputs.tx_vertical_nodes_by_board:
        raise ValueError(
            "tx_vertical ZX series-chain contract violation: mounted tx_vertical board captured no linked nodes "
            f"(board_id={pcb['id']}, board_idx={board_idx})"
        )
    board_nodes = finalize_inputs.tx_vertical_nodes_by_board[board_key]
    if not board_nodes:
        raise ValueError(
            "tx_vertical ZX series-chain contract violation: mounted tx_vertical board captured no linked nodes "
            f"(board_id={pcb['id']}, board_idx={board_idx})"
        )
    series_entry, series_exit = _resolve_tx_vertical_zx_series_chain_landings_from_nodes(nodes=board_nodes)
    _assign_tx_series_terminal_once(
        finalize_inputs=finalize_inputs,
        terminal_name="series_entry",
        landing=series_entry,
        context="tx_vertical ZX series terminal",
    )
    _assign_tx_series_terminal_once(
        finalize_inputs=finalize_inputs,
        terminal_name="series_exit",
        landing=series_exit,
        context="tx_vertical ZX series terminal",
    )

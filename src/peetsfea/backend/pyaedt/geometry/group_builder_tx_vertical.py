from __future__ import annotations

from typing import Callable, Literal, cast

from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance

from .build_state import Edge2P, FinalizeInputs, GeometryBuildState, GeometryRuntimeContext, Point3
from .cad_probe import _object_name, _probe_cad_object
from .debug_checks import _bbox_violations
from .placement_rules import (
    _build_polarity,
    _build_yz_dd_pair_from_right_local,
    _build_rxdd_right_points_A_to_d_cw,
    _coil_instance_offset,
    _current_direction_from_xy_points,
    _instance_side,
    _max_feasible_turns,
    _mount_allows_instance,
)
from .spiral_points import (
    _build_rect_spiral_centerline_absolute,
    _map_xy_points_to_zx,
)


def _build_tx_vertical_local_points(
    *,
    layout_mode: Literal[1, 2],
    turns: int,
    outer_x: float,
    outer_z: float,
    trace: float,
    gap: float,
) -> list[list[float]]:
    if layout_mode == 2:
        return _build_rxdd_right_points_A_to_d_cw(
            turns=turns,
            outer_x=outer_x,
            outer_y=outer_z,
            trace=trace,
            gap=gap,
        )
    return [
        list(point)
        for point in _build_rect_spiral_centerline_absolute(
            turns=turns,
            outer_x=outer_x,
            outer_y=outer_z,
            trace=trace,
            gap=gap,
            z=0.0,
        )
    ]


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
    if (
        ctx.tx_vertical_region_min is None
        or ctx.tx_vertical_region_max is None
        or ctx.tx_vertical_center_x is None
        or ctx.tx_vertical_center_y is None
    ):
        raise ValueError("tx_vertical scene context is not ready")
    tx_vertical_region_min = ctx.tx_vertical_region_min
    tx_vertical_region_max = ctx.tx_vertical_region_max
    tx_vertical_center_x = ctx.tx_vertical_center_x
    tx_vertical_center_y = ctx.tx_vertical_center_y

    turns = geometry["turn_count_max"]
    trace = geometry["trace"]
    gap = geometry["gap"]
    if turns < 1:
        raise ValueError("selected_group_geometry.tx_vertical.turn_count_max must be >= 1")
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
            "Infeasible turn_count_max for tx_vertical: "
            f"requested={turns}, feasible_max={tx_vertical_max_turns} "
            f"(primary_span={tx_vertical_span_primary}, outer_z={tx_vertical_outer_z}, trace={trace}, gap={gap})"
        )
    tx_vertical_points = _build_tx_vertical_local_points(
        layout_mode=ctx.tx_vertical_layout_mode,
        turns=turns,
        outer_x=tx_vertical_span_primary,
        outer_z=tx_vertical_outer_z,
        trace=trace,
        gap=gap,
    )
    tx_vertical_center_z = tx_vertical_region_min[2] + (tx_vertical_outer_z / 2.0)

    instance_count = group["selected_count"]
    spacing_mm = group["spacing_mm"]
    transforms = group["instance_transforms"]
    transform = transforms[0] if transforms else {"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0}
    if ctx.tx_vertical_plane not in {"ZX", "YZ"}:
        raise ValueError("tx_vertical plane contract violation: expected ZX or YZ")

    def _register_tx_vertical_path(
        *,
        world_points: list[list[float]],
        local_points: list[list[float]],
        plane: Literal["ZX", "YZ"],
        group_instance_index: int,
        side: Literal["left", "right", "center"],
        current_direction_override: Literal["cw", "ccw"] | None = None,
        register_link_node: bool = True,
    ) -> tuple[str, float, Edge2P, Edge2P, Point3, Point3]:
        top_name = f"coil_tx_vertical_g{group_instance_index}_b{board_idx}_{ctx.design_id}"
        top_created = modeler.create_polyline(
            points=world_points,
            name=top_name,
            material="copper",
            xsection_type="Rectangle",
            xsection_width=trace,  # type: ignore[arg-type]
            xsection_height=ctx.cu_thickness,  # type: ignore[arg-type]
        )
        if not top_created:
            raise ValueError(
                "tx_vertical polyline creation failed "
                f"(name={top_name}, points={len(world_points)}, group_kind=tx_vertical)"
            )
        top_obj = cast(Object3d, top_created)
        obj_name = _object_name(top_obj, top_name)
        state.object_names.append(obj_name)
        probe = _probe_cad_object(top_obj, top_name)
        state.cad_probe.append(probe)
        state.coil_plane_bboxes.append((pcb["id"], plane, probe["bbox"]))

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
        state.group_objects["tx_vertical"].append(obj_name)

        start_xyz = cast(Point3, tuple(float(v) for v in world_points[0]))
        end_xyz = cast(Point3, tuple(float(v) for v in world_points[-1]))
        state.group_endpoints.append(
            {
                "group_kind": "tx_vertical",
                "group_instance_index": group_instance_index,
                "board_id": pcb["id"],
                "start_xyz": start_xyz,
                "end_xyz": end_xyz,
                "start_label": "A",
                "end_label": "a",
                "present": True,
            }
        )
        default_current_direction, b_field_direction = _build_polarity("tx_vertical", side)
        current_direction = current_direction_override or _current_direction_from_xy_points(local_points) or default_current_direction
        state.coil_polarity.append(
            {
                "group_kind": "tx_vertical",
                "group_instance_index": group_instance_index,
                "board_id": pcb["id"],
                "instance_side": side,
                "current_direction": current_direction,
                "b_field_direction": b_field_direction,
            }
        )

        y_center = (probe["bbox"][1] + probe["bbox"][4]) / 2.0
        terminal_edge = edge_points_at_tx_vertical_terminal(points=world_points, trace=trace, plane=ctx.tx_vertical_plane)
        opposite_terminal_edge = edge_points_at_tx_vertical_opposite_terminal(
            points=world_points,
            trace=trace,
            plane=ctx.tx_vertical_plane,
        )
        bridge_out_edge, bridge_in_edge = tx_vertical_bridge_edges_from_node(
            points=world_points,
            start_xyz=start_xyz,
            end_xyz=end_xyz,
            trace=trace,
            tx_vertical_region_min=tx_vertical_region_min,
            tx_vertical_region_max=tx_vertical_region_max,
            plane=ctx.tx_vertical_plane,
        )
        right_key = (-y_center, pcb["id"], group_instance_index)
        if (
            finalize_inputs.tx_vertical_outer_right_selection_key is None
            or right_key < finalize_inputs.tx_vertical_outer_right_selection_key
        ):
            finalize_inputs.tx_vertical_outer_right_selection_key = right_key
            finalize_inputs.tx_vertical_global_outer_right_edge = terminal_edge
        left_key = (y_center, pcb["id"], group_instance_index)
        if (
            finalize_inputs.tx_vertical_outer_left_selection_key is None
            or left_key < finalize_inputs.tx_vertical_outer_left_selection_key
        ):
            finalize_inputs.tx_vertical_outer_left_selection_key = left_key
            finalize_inputs.tx_vertical_global_outer_left_edge = opposite_terminal_edge
        if register_link_node:
            board_key = (pcb["id"], board_idx)
            board_nodes = finalize_inputs.tx_vertical_nodes_by_board.setdefault(board_key, [])
            board_nodes.append(
                (group_instance_index, obj_name, start_xyz, end_xyz, y_center, trace, bridge_out_edge, bridge_in_edge)
            )
        return obj_name, y_center, bridge_out_edge, bridge_in_edge, start_xyz, end_xyz

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
        if ctx.tx_vertical_layout_mode == 2 and ctx.tx_vertical_plane == "YZ":
            pair_center_distance = tx_vertical_span_primary + ctx.tx_vertical_mode2_pair_spacing_mm
            mode2_registered: dict[Literal["left", "right"], tuple[str, Point3]] = {}
            for pair_side, pair_world_points, _pair_y_center, pair_current_direction in _build_yz_dd_pair_from_right_local(
                right_local_points=tx_vertical_points,
                x_const=world_center_x,
                axis_y=logical_center_y,
                z_center=world_center_z,
                pair_center_distance=pair_center_distance,
            ):
                group_instance_index = (instance_index * 2) if pair_side == "left" else (instance_index * 2) + 1
                obj_name, _y_center, _bridge_out_edge, _bridge_in_edge, _start_xyz, end_xyz = _register_tx_vertical_path(
                    world_points=pair_world_points,
                    local_points=tx_vertical_points,
                    plane="YZ",
                    group_instance_index=group_instance_index,
                    side=pair_side,
                    current_direction_override=pair_current_direction,
                    register_link_node=False,
                )
                mode2_registered[pair_side] = (obj_name, end_xyz)
            if "left" not in mode2_registered or "right" not in mode2_registered:
                raise ValueError("tx_vertical mode 2 pair registration contract violation: missing left/right half")
            left_name, left_end_xyz = mode2_registered["left"]
            right_name, right_end_xyz = mode2_registered["right"]
            board_key = (pcb["id"], board_idx)
            if board_key in finalize_inputs.tx_vertical_mode2_connect_sources_by_board:
                raise ValueError(
                    "tx_vertical mode 2 connect-source contract violation: duplicate board entry "
                    f"(board_id={pcb['id']}, board_idx={board_idx})"
                )
            finalize_inputs.tx_vertical_mode2_connect_sources_by_board[board_key] = [
                (pcb["id"], instance_index, "c", left_end_xyz, trace, left_name),
                (pcb["id"], instance_index, "d", right_end_xyz, trace, right_name),
            ]
            continue
        if ctx.tx_vertical_plane == "ZX":
            top_points = _map_xy_points_to_zx(
                tx_vertical_points,
                x_center=world_center_x,
                y_const=logical_center_y,
                z_center=world_center_z,
            )
            _register_tx_vertical_path(
                world_points=top_points,
                local_points=tx_vertical_points,
                plane="ZX",
                group_instance_index=instance_index,
                side=side,
            )
        else:
            raise ValueError("tx_vertical plane contract violation: YZ plane is supported only for layout_mode=2")

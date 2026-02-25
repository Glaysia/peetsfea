from __future__ import annotations

from typing import Callable, cast

from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance

from .build_state import Edge2P, FinalizeInputs, GeometryBuildState, GeometryRuntimeContext, Point3
from .cad_probe import _object_name, _probe_cad_object
from .debug_checks import _bbox_violations
from .placement_rules import (
    _build_polarity,
    _coil_instance_offset,
    _current_direction_from_xy_points,
    _instance_side,
    _max_feasible_turns,
    _mount_allows_instance,
)
from .spiral_points import _build_rect_spiral_centerline_absolute, _map_xy_points_to_zx


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
    tx_vertical_outer_y = min(ctx.tx_vertical_outer_y, tx_vertical_zone_h)
    tx_vertical_max_turns = min(
        _max_feasible_turns(ctx.tx_vertical_outer_x, trace, gap),
        _max_feasible_turns(tx_vertical_outer_y, trace, gap),
    )
    if tx_vertical_max_turns < 1:
        raise ValueError(
            "tx_vertical cannot fit in tx_region_vertical "
            f"(available_outer_x={ctx.tx_vertical_outer_x}, available_outer_y={tx_vertical_outer_y})"
        )
    if turns > tx_vertical_max_turns:
        raise ValueError(
            "Infeasible turn_count_max for tx_vertical: "
            f"requested={turns}, feasible_max={tx_vertical_max_turns} "
            f"(outer_x={ctx.tx_vertical_outer_x}, outer_y={tx_vertical_outer_y}, trace={trace}, gap={gap})"
        )
    tx_vertical_points = [
        list(point)
        for point in _build_rect_spiral_centerline_absolute(
            turns=turns,
            outer_x=ctx.tx_vertical_outer_x,
            outer_y=tx_vertical_outer_y,
            trace=trace,
            gap=gap,
            z=0.0,
        )
    ]
    tx_vertical_center_z = tx_vertical_region_min[2] + (tx_vertical_outer_y / 2.0)

    instance_count = group["selected_count"]
    spacing_mm = group["spacing_mm"]
    transforms = group["instance_transforms"]
    transform = transforms[0] if transforms else {"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0}
    if ctx.tx_vertical_plane != "ZX":
        raise ValueError("tx_vertical plane contract violation: expected ZX")

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
        top_points = _map_xy_points_to_zx(
            tx_vertical_points,
            x_center=tx_vertical_center_x + transform["dx"] + off_x,
            y_const=tx_vertical_center_y + transform["dy"] + off_y,
            z_center=tx_vertical_center_z + transform["dz"] + off_z,
        )
        top_name = f"coil_tx_vertical_g{instance_index}_b{board_idx}_{ctx.design_id}"
        top_created = modeler.create_polyline(
            points=top_points,
            name=top_name,
            material="copper",
            xsection_type="Rectangle",
            xsection_width=trace,  # type: ignore[arg-type]
            xsection_height=ctx.cu_thickness,  # type: ignore[arg-type]
        )
        if not top_created:
            raise ValueError(
                "tx_vertical polyline creation failed "
                f"(name={top_name}, points={len(top_points)}, group_kind=tx_vertical)"
            )
        top_obj = cast(Object3d, top_created)
        obj_name = _object_name(top_obj, top_name)
        state.object_names.append(obj_name)
        probe = _probe_cad_object(top_obj, top_name)
        state.cad_probe.append(probe)
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
        state.group_objects["tx_vertical"].append(obj_name)

        start_xyz = cast(Point3, tuple(float(v) for v in top_points[0]))
        end_xyz = cast(Point3, tuple(float(v) for v in top_points[-1]))
        side = _instance_side("tx_vertical", (off_x, off_y, off_z))
        state.group_endpoints.append(
            {
                "group_kind": "tx_vertical",
                "group_instance_index": instance_index,
                "board_id": pcb["id"],
                "start_xyz": start_xyz,
                "end_xyz": end_xyz,
                "start_label": "A",
                "end_label": "a",
                "present": True,
            }
        )
        default_current_direction, b_field_direction = _build_polarity("tx_vertical", side)
        current_direction = _current_direction_from_xy_points(top_points) or default_current_direction
        state.coil_polarity.append(
            {
                "group_kind": "tx_vertical",
                "group_instance_index": instance_index,
                "board_id": pcb["id"],
                "instance_side": side,
                "current_direction": current_direction,
                "b_field_direction": b_field_direction,
            }
        )

        y_center = (probe["bbox"][1] + probe["bbox"][4]) / 2.0
        terminal_edge = edge_points_at_tx_vertical_terminal(points=top_points, trace=trace)
        opposite_terminal_edge = edge_points_at_tx_vertical_opposite_terminal(points=top_points, trace=trace)
        bridge_out_edge, bridge_in_edge = tx_vertical_bridge_edges_from_node(
            start_xyz=start_xyz,
            end_xyz=end_xyz,
            trace=trace,
            tx_vertical_region_min=tx_vertical_region_min,
            tx_vertical_region_max=tx_vertical_region_max,
        )
        right_key = (-y_center, pcb["id"], instance_index)
        if (
            finalize_inputs.tx_vertical_outer_right_selection_key is None
            or right_key < finalize_inputs.tx_vertical_outer_right_selection_key
        ):
            finalize_inputs.tx_vertical_outer_right_selection_key = right_key
            finalize_inputs.tx_vertical_global_outer_right_edge = terminal_edge
        left_key = (y_center, pcb["id"], instance_index)
        if (
            finalize_inputs.tx_vertical_outer_left_selection_key is None
            or left_key < finalize_inputs.tx_vertical_outer_left_selection_key
        ):
            finalize_inputs.tx_vertical_outer_left_selection_key = left_key
            finalize_inputs.tx_vertical_global_outer_left_edge = opposite_terminal_edge
        board_key = (pcb["id"], board_idx)
        board_nodes = finalize_inputs.tx_vertical_nodes_by_board.setdefault(board_key, [])
        board_nodes.append(
            (instance_index, obj_name, start_xyz, end_xyz, y_center, trace, bridge_out_edge, bridge_in_edge)
        )

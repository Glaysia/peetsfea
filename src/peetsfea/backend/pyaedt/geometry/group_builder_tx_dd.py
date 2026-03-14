from __future__ import annotations

from typing import Callable, cast

from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance

from .build_state import Edge2P, FinalizeInputs, GeometryBuildState, GeometryRuntimeContext, Point3
from .cad_probe import _object_name, _probe_cad_object, _probe_from_points
from .debug_checks import _bbox_violations
from .placement_rules import (
    _build_polarity,
    _current_direction_from_xy_points,
    _extend_endpoints,
    _instance_side,
    _max_feasible_turns,
    _mount_allows_instance,
    _realized_txdd_geometry,
    _tx_dd_center_y_and_layer,
    _txdd_right_layer_rank_by_z,
    _txdd_right_points,
)
from .spiral_points import _mirror_points_about_y_axis_line, _translate_points


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
    if ctx.tx_dd_region_min is None or ctx.tx_dd_region_max is None or ctx.tx_dd_center_x is None or ctx.tx_dd_center_y is None:
        raise ValueError("tx_dd scene context is not ready")
    tx_dd_region_min = ctx.tx_dd_region_min
    tx_dd_region_max = ctx.tx_dd_region_max
    tx_dd_center_x = ctx.tx_dd_center_x
    tx_dd_center_y = ctx.tx_dd_center_y

    turns = geometry["turn_count_max"]
    trace = geometry["trace"]
    gap = geometry["gap"]
    if turns < 1:
        raise ValueError("selected_group_geometry.tx_dd.turn_count_max must be >= 1")
    if trace <= 0:
        raise ValueError("selected_group_geometry.tx_dd.trace must be > 0")
    if gap < 0:
        raise ValueError("selected_group_geometry.tx_dd.gap must be >= 0")
    max_turns = min(
        _max_feasible_turns(ctx.tx_dd_outer_x, trace, gap),
        _max_feasible_turns(ctx.tx_dd_outer_y, trace, gap),
    )
    if max_turns < 1:
        raise ValueError(
            "Invalid geometry for tx_dd: cannot fit at least one turn on both X/Y axes "
            f"(turns={turns}, trace={trace}, gap={gap})"
        )
    if turns > max_turns:
        raise ValueError(
            f"Infeasible turn_count_max for tx_dd: requested={turns}, feasible_max={max_turns} "
            f"(outer_x={ctx.tx_dd_outer_x}, outer_y={ctx.tx_dd_outer_y}, trace={trace}, gap={gap})"
        )
    instance_count = group["selected_count"]
    for layer_index in ((0, 1) if instance_count == 4 else (0,)):
        _realized_txdd_geometry(
            turns=turns,
            outer_x=ctx.tx_dd_outer_x,
            outer_y=ctx.tx_dd_outer_y,
            trace=trace,
            gap=gap,
            instance_count=instance_count,
            layer_index=layer_index,
        )
    spacing_mm = group["spacing_mm"]
    transforms = group["instance_transforms"]
    transform = transforms[0] if transforms else {"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0}
    txdd_right_layer_rank: dict[int, int] = {}
    if instance_count == 4:
        tx_dd_anchor_z = tx_dd_region_max[2] - ctx.tx_dd_top_clearance - ctx.cu_thickness
        txdd_right_layer_rank = _txdd_right_layer_rank_by_z(
            selected_pcbs=ctx.selected_pcbs,
            instance_count=instance_count,
            transform_dz=transform["dz"],
            tx_dd_anchor_z=tx_dd_anchor_z,
        )

    board_z = pcb["position"][2]
    for instance_index in range(instance_count):
        local_slot = instance_index % 2
        if local_slot == 0:
            _tx_dd_center_y_and_layer(
                instance_count=instance_count,
                instance_index=instance_index,
                pair_clearance_mm=spacing_mm,
                outer_y=ctx.tx_dd_outer_y,
                region_center_y=tx_dd_center_y,
                region_min_y=tx_dd_region_min[1],
                region_max_y=tx_dd_region_max[1],
            )
            right_index = instance_index + 1
            _tx_dd_center_y_and_layer(
                instance_count=instance_count,
                instance_index=right_index,
                pair_clearance_mm=spacing_mm,
                outer_y=ctx.tx_dd_outer_y,
                region_center_y=tx_dd_center_y,
                region_min_y=tx_dd_region_min[1],
                region_max_y=tx_dd_region_max[1],
            )
            left_mounted = _mount_allows_instance(pcb["mounts"], "tx_dd", instance_index)
            right_mounted = right_index < instance_count and _mount_allows_instance(
                pcb["mounts"], "tx_dd", right_index
            )
            if left_mounted and not right_mounted:
                raise ValueError(
                    "tx_dd mirror source missing: left instance is mounted without matching right "
                    f"(board_id={pcb['id']}, left_index={instance_index}, right_index={right_index})"
                )
            continue
        if not _mount_allows_instance(pcb["mounts"], "tx_dd", instance_index):
            continue

        right_index = instance_index
        left_index = right_index - 1
        right_center_y, tx_dd_layer_index = _tx_dd_center_y_and_layer(
            instance_count=instance_count,
            instance_index=right_index,
            pair_clearance_mm=spacing_mm,
            outer_y=ctx.tx_dd_outer_y,
            region_center_y=tx_dd_center_y,
            region_min_y=tx_dd_region_min[1],
            region_max_y=tx_dd_region_max[1],
        )
        right_layer_index = txdd_right_layer_rank.get(right_index, tx_dd_layer_index)
        tx_dd_points = _txdd_right_points(
            turns=turns,
            outer_x=ctx.tx_dd_outer_x,
            outer_y=ctx.tx_dd_outer_y,
            trace=trace,
            gap=gap,
            instance_count=instance_count,
            layer_index=right_layer_index,
        )

        raw_right_a_local: Point3 | None = None
        right_a_point: Point3 | None = None
        if instance_count == 4 and right_layer_index in (0, 1):
            raw_right_a_source = tx_dd_points[-1] if right_layer_index == 0 else tx_dd_points[0]
            raw_right_a_local = cast(Point3, tuple(float(v) for v in raw_right_a_source))

        tx_dd_points = _extend_endpoints(tx_dd_points, extension=(trace / 2.0))
        tx_dd_anchor_z = tx_dd_region_max[2] - ctx.tx_dd_top_clearance - ctx.cu_thickness
        tx_dd_dx = tx_dd_center_x + transform["dx"]
        tx_dd_dy = right_center_y + transform["dy"]
        tx_dd_dz = tx_dd_anchor_z - board_z + transform["dz"]
        right_top_points = _translate_points(tx_dd_points, dx=tx_dd_dx, dy=tx_dd_dy, dz=tx_dd_dz)

        if instance_count == 4 and right_layer_index in (0, 1):
            if raw_right_a_local is None:
                raise ValueError(
                    "tx_dd layer bridge contract violation: raw right A anchor was not captured "
                    f"(layer_index={right_layer_index})"
                )
            right_a_point = (
                raw_right_a_local[0] + tx_dd_dx,
                raw_right_a_local[1] + tx_dd_dy,
                raw_right_a_local[2] + tx_dd_dz,
            )
            finalize_inputs.txdd_right_a_points[right_layer_index] = (cast(Point3, right_a_point), trace)

        right_name = f"coil_tx_dd_g{right_index}_b{board_idx}_{ctx.design_id}"
        right_created = modeler.create_polyline(
            points=right_top_points,
            name=right_name,
            material="copper",
            xsection_type="Rectangle",
            xsection_width=trace,  # type: ignore[arg-type]
            xsection_height=ctx.cu_thickness,  # type: ignore[arg-type]
        )
        if not right_created:
            raise ValueError(
                "tx_dd right polyline creation failed "
                f"(name={right_name}, points={len(right_top_points)}, group_kind=tx_dd)"
            )
        right_obj = cast(Object3d, right_created)
        right_obj_name = _object_name(right_obj, right_name)
        capture_dd_right_d_edge = (instance_count == 2) or (instance_count == 4 and right_layer_index == 1)
        if capture_dd_right_d_edge:
            d_edge_points = edge_points_at_path_end(points=right_top_points, trace=trace)
            selection_key = (-right_center_y, pcb["id"], right_index)
            if (
                finalize_inputs.txdd_global_right_d_selection_key is None
                or selection_key < finalize_inputs.txdd_global_right_d_selection_key
            ):
                finalize_inputs.txdd_global_right_d_selection_key = selection_key
                finalize_inputs.txdd_global_right_d_edge = d_edge_points
                finalize_inputs.txdd_global_right_d_object_name = right_obj_name

        state.object_names.append(right_obj_name)
        if instance_count == 2 and right_index == 1:
            finalize_inputs.txdd_start_stub_sources.setdefault(pcb["id"], []).append(
                (cast(Point3, tuple(float(v) for v in right_top_points[0])), trace, right_obj_name)
            )
        elif instance_count == 4 and right_layer_index == 0:
            finalize_inputs.txdd_start_stub_sources.setdefault(pcb["id"], []).append(
                (cast(Point3, tuple(float(v) for v in right_top_points[0])), trace, right_obj_name)
            )
        if instance_count == 4 and right_layer_index in (0, 1):
            finalize_inputs.txdd_right_object_names[right_layer_index] = right_obj_name

        right_probe = _probe_cad_object(right_obj, right_name)
        state.cad_probe.append(right_probe)
        state.coil_plane_bboxes.append((pcb["id"], "XY", right_probe["bbox"]))
        right_violations = _bbox_violations(
            object_name=right_obj_name,
            bbox=right_probe["bbox"],
            region_kind="tx_region_dd",
            region_min=tx_dd_region_min,
            region_max=tx_dd_region_max,
        )
        if right_violations:
            state.placement_violations.extend(right_violations)
            first = right_violations[0]
            raise ValueError(
                f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
                f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
            )
        state.group_objects["tx_dd"].append(right_obj_name)
        right_start_xyz = cast(Point3, tuple(float(v) for v in right_top_points[0]))
        right_end_xyz = cast(Point3, tuple(float(v) for v in right_top_points[-1]))
        state.group_endpoints.append(
            {
                "group_kind": "tx_dd",
                "group_instance_index": right_index,
                "board_id": pcb["id"],
                "start_xyz": right_start_xyz,
                "end_xyz": right_end_xyz,
                "start_label": "A",
                "end_label": "a",
                "present": True,
            }
        )
        right_off_y = right_center_y - tx_dd_center_y
        right_side = _instance_side("tx_dd", (0.0, right_off_y, 0.0))
        default_right_current_direction, right_b_field_direction = _build_polarity("tx_dd", right_side)
        right_current_direction = _current_direction_from_xy_points(right_top_points) or default_right_current_direction
        state.coil_polarity.append(
            {
                "group_kind": "tx_dd",
                "group_instance_index": right_index,
                "board_id": pcb["id"],
                "instance_side": right_side,
                "current_direction": right_current_direction,
                "b_field_direction": right_b_field_direction,
            }
        )

        if not _mount_allows_instance(pcb["mounts"], "tx_dd", left_index):
            continue
        mirror_origin = [
            tx_dd_center_x + transform["dx"],
            tx_dd_center_y + transform["dy"],
            tx_dd_anchor_z - board_z + transform["dz"],
        ]
        mirrored_created = modeler.duplicate_and_mirror(
            assignment=right_obj_name,
            origin=mirror_origin,
            vector=[0.0, 1.0, 0.0],
            duplicate_assignment=True,
        )
        if not isinstance(mirrored_created, list) or len(mirrored_created) != 1:
            raise ValueError(
                "tx_dd mirror creation failed: expected exactly one mirrored object "
                f"(board_id={pcb['id']}, right_index={right_index}, result={mirrored_created})"
            )
        left_obj_name = str(mirrored_created[0])
        state.object_names.append(left_obj_name)
        left_top_points = _mirror_points_about_y_axis_line(
            right_top_points,
            axis_y=tx_dd_center_y + transform["dy"],
        )
        capture_dd_left_vertical_link_edge = (instance_count == 2) or (instance_count == 4 and right_layer_index == 1)
        if capture_dd_left_vertical_link_edge:
            if instance_count == 2:
                left_vertical_link_edge_points = edge_points_at_path_end(points=list(reversed(left_top_points)), trace=trace)
            else:
                left_vertical_link_edge_points = edge_points_at_path_end(points=left_top_points, trace=trace)
            if finalize_inputs.txdd_global_left_vertical_link_edge is not None:
                prev_object_name = finalize_inputs.txdd_global_left_vertical_link_object_name
                raise ValueError(
                    "tx_dd global left vertical-link edge must be unique for tx_dd_left->tx_vertical bridge contract "
                    f"(existing: object_name={prev_object_name}; "
                    f"new: board_id={pcb['id']}, instance_index={right_index}, object_name={left_obj_name})"
                )
            finalize_inputs.txdd_global_left_vertical_link_edge = left_vertical_link_edge_points
            finalize_inputs.txdd_global_left_vertical_link_object_name = left_obj_name
        if instance_count == 2:
            finalize_inputs.txdd_start_stub_sources.setdefault(pcb["id"], []).append(
                (cast(Point3, tuple(float(v) for v in left_top_points[-1])), trace, left_obj_name)
            )
        elif instance_count == 4 and right_layer_index == 0:
            finalize_inputs.txdd_start_stub_sources.setdefault(pcb["id"], []).append(
                (cast(Point3, tuple(float(v) for v in left_top_points[-1])), trace, left_obj_name)
            )
        if instance_count == 4 and right_layer_index in (0, 1):
            finalize_inputs.txdd_left_object_names[right_layer_index] = left_obj_name
            if right_a_point is None:
                raise ValueError(
                    "tx_dd left layer bridge contract violation: right A anchor missing "
                    f"(layer_index={right_layer_index})"
                )
            left_a_point = (
                right_a_point[0],
                (2.0 * (tx_dd_center_y + transform["dy"])) - right_a_point[1],
                right_a_point[2],
            )
            finalize_inputs.txdd_left_a_points[right_layer_index] = (cast(Point3, left_a_point), trace)
        left_probe = _probe_from_points(left_obj_name, left_top_points)
        state.cad_probe.append(left_probe)
        state.coil_plane_bboxes.append((pcb["id"], "XY", left_probe["bbox"]))
        left_violations = _bbox_violations(
            object_name=left_obj_name,
            bbox=left_probe["bbox"],
            region_kind="tx_region_dd",
            region_min=tx_dd_region_min,
            region_max=tx_dd_region_max,
        )
        if left_violations:
            state.placement_violations.extend(left_violations)
            first = left_violations[0]
            raise ValueError(
                f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
                f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
            )
        state.group_objects["tx_dd"].append(left_obj_name)
        left_start_xyz = cast(Point3, tuple(float(v) for v in left_top_points[0]))
        left_end_xyz = cast(Point3, tuple(float(v) for v in left_top_points[-1]))
        state.group_endpoints.append(
            {
                "group_kind": "tx_dd",
                "group_instance_index": left_index,
                "board_id": pcb["id"],
                "start_xyz": left_start_xyz,
                "end_xyz": left_end_xyz,
                "start_label": "A",
                "end_label": "a",
                "present": True,
            }
        )
        left_center_y, _ = _tx_dd_center_y_and_layer(
            instance_count=instance_count,
            instance_index=left_index,
            pair_clearance_mm=spacing_mm,
            outer_y=ctx.tx_dd_outer_y,
            region_center_y=tx_dd_center_y,
            region_min_y=tx_dd_region_min[1],
            region_max_y=tx_dd_region_max[1],
        )
        left_off_y = left_center_y - tx_dd_center_y
        left_side = _instance_side("tx_dd", (0.0, left_off_y, 0.0))
        default_left_current_direction, left_b_field_direction = _build_polarity("tx_dd", left_side)
        left_current_direction = _current_direction_from_xy_points(left_top_points) or default_left_current_direction
        state.coil_polarity.append(
            {
                "group_kind": "tx_dd",
                "group_instance_index": left_index,
                "board_id": pcb["id"],
                "instance_side": left_side,
                "current_direction": left_current_direction,
                "b_field_direction": left_b_field_direction,
            }
        )

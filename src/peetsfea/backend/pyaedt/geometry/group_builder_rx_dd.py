from __future__ import annotations

from typing import Callable, Literal, cast

from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance, TerminalLabel

from .build_state import FinalizeInputs, GeometryBuildState, GeometryRuntimeContext, Point3
from .cad_probe import _object_name, _probe_cad_object
from .debug_checks import _bbox_violations
from .placement_rules import (
    _build_polarity,
    _build_yz_dd_pair_from_right_local,
    _build_rxdd_right_points_A_to_d_cw,
    _instance_side,
    _max_feasible_turns,
    _mount_allows_instance,
    _rx_dd_center_offset_y,
    _validate_rxdd_single_layer_count,
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
    append_rxdd_back_stub_sources_if_needed: Callable[..., None],
) -> None:
    if ctx.rx_region_min is None or ctx.rx_region_max is None or ctx.rx_center_y is None:
        raise ValueError("rx_dd scene context is not ready")
    rx_region_min = ctx.rx_region_min
    rx_region_max = ctx.rx_region_max
    rx_center_y = ctx.rx_center_y

    turns = geometry["turn_count_max"]
    trace = geometry["trace"]
    gap = geometry["gap"]
    if turns < 1:
        raise ValueError("selected_group_geometry.rx_dd.turn_count_max must be >= 1")
    if turns > 3:
        raise ValueError("selected_group_geometry.rx_dd.turn_count_max must be <= 3")
    if trace <= 0:
        raise ValueError("selected_group_geometry.rx_dd.trace must be > 0")
    if gap < 0:
        raise ValueError("selected_group_geometry.rx_dd.gap must be >= 0")
    max_turns = min(
        _max_feasible_turns(ctx.rx_dd_outer_x, trace, gap),
        _max_feasible_turns(ctx.rx_dd_outer_y, trace, gap),
    )
    if max_turns < 1:
        raise ValueError(
            "Invalid geometry for rx_dd: cannot fit at least one turn on both X/Y axes "
            f"(turns={turns}, trace={trace}, gap={gap})"
        )
    if turns > max_turns:
        raise ValueError(
            f"Infeasible turn_count_max for rx_dd: requested={turns}, feasible_max={max_turns} "
            f"(outer_x={ctx.rx_dd_outer_x}, outer_y={ctx.rx_dd_outer_y}, trace={trace}, gap={gap})"
        )

    instance_count = group["selected_count"]
    spacing_mm = group["spacing_mm"]
    transforms = group["instance_transforms"]
    transform = transforms[0] if transforms else {"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0}
    _validate_rxdd_single_layer_count(instance_count)
    if spacing_mm < 0:
        raise ValueError(f"rx_dd edge gap must be >= 0 (actual={spacing_mm})")
    if abs(transform["dz"]) > 1e-12:
        raise ValueError("rx_dd transform dz must be 0 for bottom-anchor contract")
    if abs(transform["dx"]) > 1e-12:
        raise ValueError("rx_dd transform dx must be 0 for +X face-anchor contract")

    rxdd_right_local_points = _build_rxdd_right_points_A_to_d_cw(
        turns=turns,
        outer_x=ctx.rx_dd_outer_x,
        outer_y=ctx.rx_dd_outer_y,
        trace=trace,
        gap=gap,
    )
    rx_anchor_x = rx_region_max[0] - ctx.rx_face_clearance - ctx.cu_thickness
    # Bottom-anchor contract: coil bottom touches RX region minimum Z.
    rx_center_z = rx_region_min[2] + (ctx.rx_dd_outer_y / 2.0) + 1e-6
    axis_y = rx_center_y + transform["dy"]
    pair_placements_by_side: dict[Literal["left", "right"], tuple[list[list[float]], Literal["cw", "ccw"]]] = {}
    pair_center_distance = ctx.rx_dd_outer_x + spacing_mm
    for pair_side, world_points, _y_center, current_direction in _build_yz_dd_pair_from_right_local(
        right_local_points=rxdd_right_local_points,
        x_const=rx_anchor_x + transform["dx"],
        axis_y=axis_y,
        z_center=rx_center_z + transform["dz"],
        pair_center_distance=pair_center_distance,
    ):
        pair_placements_by_side[pair_side] = (world_points, current_direction)

    for instance_index in range(instance_count):
        if not _mount_allows_instance(pcb["mounts"], "rx_dd", instance_index):
            continue
        off_y = _rx_dd_center_offset_y(
            instance_index=instance_index,
            instance_count=instance_count,
            outer_x=ctx.rx_dd_outer_x,
            edge_gap_mm=spacing_mm,
        )
        rx_side = _instance_side("rx_dd", (0.0, off_y, 0.0))
        if rx_side == "center":
            raise ValueError(
                "rx_dd side contract violation: instance side must be left or right "
                f"(instance_index={instance_index}, off_y={off_y})"
            )
        placement = pair_placements_by_side.get(rx_side)
        if placement is None:
            raise ValueError(f"rx_dd pair placement is missing side '{rx_side}'")
        top_points, current_direction = placement

        top_name = f"coil_rx_dd_g{instance_index}_b{board_idx}_{ctx.design_id}"
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
                "rx_dd polyline creation failed "
                f"(name={top_name}, points={len(top_points)}, group_kind=rx_dd)"
            )
        top_obj = cast(Object3d, top_created)
        obj_name = _object_name(top_obj, top_name)
        state.object_names.append(obj_name)
        probe = _probe_cad_object(top_obj, top_name)
        state.cad_probe.append(probe)
        state.coil_plane_bboxes.append((pcb["id"], "YZ", probe["bbox"]))
        violations = _bbox_violations(
            object_name=obj_name,
            bbox=probe["bbox"],
            region_kind="rx_region_actual",
            region_min=rx_region_min,
            region_max=rx_region_max,
        )
        if violations:
            state.placement_violations.extend(violations)
            first = violations[0]
            raise ValueError(
                f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
                f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
            )
        state.group_objects["rx_dd"].append(obj_name)

        start_xyz = cast(Point3, tuple(float(v) for v in top_points[0]))
        end_xyz = cast(Point3, tuple(float(v) for v in top_points[-1]))
        start_label: TerminalLabel = "A" if rx_side == "right" else "B"
        end_label: TerminalLabel = "d" if rx_side == "right" else "c"
        state.group_endpoints.append(
            {
                "group_kind": "rx_dd",
                "group_instance_index": instance_index,
                "board_id": pcb["id"],
                "start_xyz": start_xyz,
                "end_xyz": end_xyz,
                "start_label": start_label,
                "end_label": end_label,
                "present": True,
            }
        )
        append_rxdd_back_stub_sources_if_needed(
            kind="rx_dd",
            board_id=pcb["id"],
            instance_index=instance_index,
            start_xyz=start_xyz,
            end_xyz=end_xyz,
            start_label=start_label,
            end_label=end_label,
            trace=trace,
            source_object_name=obj_name,
            storage=finalize_inputs.rxdd_back_stub_sources,
        )

        default_current_direction, b_field_direction = _build_polarity("rx_dd", rx_side)
        expected_right_direction: Literal["cw", "ccw"] = "cw"
        expected_left_direction: Literal["cw", "ccw"] = "ccw"
        expected = expected_right_direction if rx_side == "right" else expected_left_direction
        if current_direction != expected:
            raise ValueError(
                "rx_dd current direction contract violation "
                f"(instance_index={instance_index}, side={rx_side}, actual={current_direction}, expected={expected})"
            )
        state.coil_polarity.append(
            {
                "group_kind": "rx_dd",
                "group_instance_index": instance_index,
                "board_id": pcb["id"],
                "instance_side": rx_side,
                "current_direction": current_direction,
                "b_field_direction": b_field_direction,
            }
        )

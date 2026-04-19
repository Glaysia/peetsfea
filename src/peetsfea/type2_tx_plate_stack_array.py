from __future__ import annotations

import math
from dataclasses import replace
from typing import cast

import build123d as bd

from peetsfea.type2_plate_stack import build_plate_stack_scene_data
from peetsfea.type2_plate_stack import total_plate_stack_thickness_mm
from peetsfea.type2_step_ledger import ExportedBodyGroup
from peetsfea.type2_step_ledger import ModeledObjectSceneData
from peetsfea.type2_step_spec import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import resolve_modeled_plate_stack_y_usage_ratio
from peetsfea.type2_step_spec import resolve_modeled_plate_stack_z_usage_ratio
from peetsfea.type2_step_spec import resolve_modeled_tx_array_x_usage_ratio
from peetsfea.type2_step_spec import resolve_modeled_tx_coil_count

_TX_PLATE_COPPER_NAME = "tx_plate_copper"
_TX_FERRITE_GROUP_NAME = "g_ferrite_tx"
_TX_COPPER_GROUP_NAME = "g_copper_tx"
_PLATE_STACK_STUB_LENGTH_MM = 5.0


def expected_tx_plate_stack_array_body_names(
    *,
    tx_coil_count: int,
) -> tuple[str, ...]:
    if tx_coil_count < 1:
        raise ValueError(f"tx_coil_count must be >= 1 (actual={tx_coil_count})")
    if tx_coil_count == 1:
        return (
            "tx_plate_copper",
            "tx_pcb_wall",
            "tx_stack_pet_psa",
            "tx_stack_ferrite",
            "tx_stack_air",
            "tx_pcb_coil",
        )
    names: list[str] = [_TX_PLATE_COPPER_NAME]
    for index in range(tx_coil_count):
        names.extend(
            (
                f"tx_b{index}_pcb_wall",
                f"tx_b{index}_stack_pet_psa",
                f"tx_b{index}_stack_ferrite",
                f"tx_b{index}_stack_air",
                f"tx_b{index}_pcb_coil",
            )
        )
    return tuple(names)


def expected_tx_plate_stack_array_body_groups(
    *,
    tx_coil_count: int,
) -> tuple[ExportedBodyGroup, ...]:
    if tx_coil_count < 1:
        raise ValueError(f"tx_coil_count must be >= 1 (actual={tx_coil_count})")
    if tx_coil_count == 1:
        ferrite_members = ("tx_stack_pet_psa", "tx_stack_ferrite", "tx_stack_air")
    else:
        ferrite_members = tuple(
            member_name
            for index in range(tx_coil_count)
            for member_name in (
                f"tx_b{index}_stack_pet_psa",
                f"tx_b{index}_stack_ferrite",
                f"tx_b{index}_stack_air",
            )
        )
    copper_members = (_TX_PLATE_COPPER_NAME,)
    return (
        {
            "group_name": _TX_COPPER_GROUP_NAME,
            "member_body_names": copper_members,
        },
        {
            "group_name": _TX_FERRITE_GROUP_NAME,
            "member_body_names": ferrite_members,
        },
    )


def build_tx_plate_stack_array_scene_data(
    spec: ModeledTxPlateStackSpec,
    *,
    owner_spec: NonModelBoxSpec,
    rx_owner_spec: NonModelBoxSpec,
    seed: int,
) -> tuple[tuple[bd.Shape, ...], ModeledObjectSceneData]:
    tx_coil_count = resolve_modeled_tx_coil_count(spec, seed=seed)
    if tx_coil_count == 1:
        return build_plate_stack_scene_data(spec, owner_spec=owner_spec, seed=seed)
    if tx_coil_count < 2:
        raise RuntimeError(f"type2 tx plate-stack array requires tx_coil_count >= 2 (actual={tx_coil_count})")
    if owner_spec.object_id != "tx_region":
        raise RuntimeError(
            "type2 tx plate-stack array requires tx_region owner "
            f"(actual={owner_spec.object_id})"
        )
    if owner_spec.plane != "YZ":
        raise RuntimeError(f"type2 tx plate-stack array requires YZ owner plane (actual={owner_spec.plane})")
    if rx_owner_spec.object_id != "rx_region_max":
        raise RuntimeError(
            "type2 tx plate-stack array requires rx_region_max owner context "
            f"(actual={rx_owner_spec.object_id})"
        )
    if rx_owner_spec.plane != "YZ":
        raise RuntimeError(f"type2 tx plate-stack array requires YZ rx owner plane (actual={rx_owner_spec.plane})")

    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if owner_size_x <= 0.0 or owner_size_y <= 0.0 or owner_size_z <= 0.0:
        raise RuntimeError(f"type2 tx plate-stack array owner size must be positive (size={owner_spec.size_xyz})")

    rx_origin_x, _rx_origin_y, rx_origin_z = rx_owner_spec.origin_xyz
    rx_size_x, rx_size_y, rx_size_z = rx_owner_spec.size_xyz
    if rx_size_x <= 0.0 or rx_size_y <= 0.0 or rx_size_z <= 0.0:
        raise RuntimeError(f"type2 tx plate-stack array rx owner size must be positive (size={rx_owner_spec.size_xyz})")
    rotation_target_xyz = (rx_origin_x + (rx_size_x / 2.0), 0.0, rx_origin_z)

    total_thickness_mm = total_plate_stack_thickness_mm(spec=spec)
    if total_thickness_mm <= 0.0:
        raise RuntimeError(f"type2 tx plate-stack array total thickness must be > 0 (actual={total_thickness_mm})")
    max_branch_origin_x = owner_origin_x + owner_size_x - total_thickness_mm
    if max_branch_origin_x < owner_origin_x:
        raise RuntimeError(
            "type2 tx plate-stack array branch thickness must fit owner X span "
            f"(owner_size_x={owner_size_x}, total_thickness_mm={total_thickness_mm})"
        )
    full_branch_origin_span_x = max_branch_origin_x - owner_origin_x
    x_usage_ratio = resolve_modeled_tx_array_x_usage_ratio(spec, seed=seed)
    branch_origin_span_x = full_branch_origin_span_x * x_usage_ratio
    branch_step_x = branch_origin_span_x / float(tx_coil_count - 1)
    if branch_step_x < 0.0:
        raise RuntimeError(
            "type2 tx plate-stack array branch step must be >= 0 "
            f"(branch_step_x={branch_step_x})"
        )
    max_used_branch_origin_x = owner_origin_x + branch_origin_span_x

    z_usage_ratio = resolve_modeled_plate_stack_z_usage_ratio(spec, seed=seed)
    active_conductor_size_z = owner_size_z * z_usage_ratio
    base_conductor_min_z = owner_origin_z + owner_size_z - active_conductor_size_z
    owner_max_z = owner_origin_z + owner_size_z
    if rotation_target_xyz[2] <= owner_max_z + 1e-9:
        raise RuntimeError(
            "type2 tx plate-stack array rotation target must be above tx-region top "
            f"(target={rotation_target_xyz}, tx_region_max_z={owner_max_z})"
        )

    y_usage_ratio = resolve_modeled_plate_stack_y_usage_ratio(spec, seed=seed)
    active_size_y = owner_size_y * y_usage_ratio
    active_min_y = -active_size_y / 2.0
    active_max_y = active_size_y / 2.0
    tip_y = active_min_y - _PLATE_STACK_STUB_LENGTH_MM

    branch_copper_shapes: list[bd.Shape] = []
    branch_pcb_shapes: list[bd.Shape] = []
    branch_ferrite_shapes: list[bd.Shape] = []
    branch_input_edges: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    branch_output_edges: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    copied_branch_rotation_angles_deg: list[float] = []
    copied_branch_hinge_edges_xyz: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    first_branch_scene_data: ModeledObjectSceneData
    branch_spec = replace(
        spec,
        z_usage_ratio=RangeSpec(is_integer=False, start=1.0, end=1.0, count=1),
    )
    for index in range(tx_coil_count):
        branch_origin_x = owner_origin_x + (branch_step_x * float(index))
        branch_conductor_min_z = base_conductor_min_z
        branch_owner_spec = replace(
            owner_spec,
            origin_xyz=(branch_origin_x, owner_origin_y, branch_conductor_min_z),
            size_xyz=(total_thickness_mm, owner_size_y, active_conductor_size_z),
        )
        branch_shapes, branch_scene_data = build_plate_stack_scene_data(
            branch_spec,
            owner_spec=branch_owner_spec,
            seed=seed,
        )
        if index == 0:
            first_branch_scene_data = branch_scene_data

        branch_rotation_angle_deg = 0.0
        branch_min_x = branch_origin_x
        branch_max_x = branch_origin_x + total_thickness_mm
        branch_hinge_x = _resolve_branch_hinge_x(
            branch_min_x=branch_min_x,
            branch_max_x=branch_max_x,
        )
        branch_hinge_axis = bd.Axis(
            (branch_hinge_x, 0.0, owner_max_z),
            (0.0, 1.0, 0.0),
        )
        if index > 0:
            branch_rotation_angle_deg = _compute_tx_plate_stack_copy_branch_rotation_angle_deg(
                branch_min_x=branch_min_x,
                branch_max_x=branch_max_x,
                branch_hinge_x=branch_hinge_x,
                owner_max_z=owner_max_z,
                rotation_target_xyz=rotation_target_xyz,
            )
            if not _is_nonzero_angle_deg(branch_rotation_angle_deg):
                raise RuntimeError(
                    "type2 tx plate-stack array copied branches must rotate "
                    f"(branch_index={index}, angle_deg={branch_rotation_angle_deg})"
                )
        copied_branch_rotation_angles_deg.append(branch_rotation_angle_deg)
        copied_branch_hinge_edges_xyz.append(
            (
                (branch_hinge_x, active_min_y, owner_max_z),
                (branch_hinge_x, active_max_y, owner_max_z),
            )
        )
        branch_shape_by_label = {shape.label: shape for shape in branch_shapes}

        if "tx_plate_copper" not in branch_shape_by_label and _TX_COPPER_GROUP_NAME not in branch_shape_by_label:
            raise RuntimeError(
                f"type2 tx branch is missing tx plate copper/group contract (branch_index={index})"
            )
        if "tx_pcb_wall" not in branch_shape_by_label or "tx_pcb_coil" not in branch_shape_by_label:
            raise RuntimeError(f"type2 tx branch is missing required PCB bodies (branch_index={index})")
        if _TX_FERRITE_GROUP_NAME not in branch_shape_by_label:
            raise RuntimeError(f"type2 tx branch is missing ferrite group compound (branch_index={index})")
        if "tx_plate_copper" in branch_shape_by_label:
            copper_shape = branch_shape_by_label["tx_plate_copper"]
        else:
            copper_group_shape = branch_shape_by_label[_TX_COPPER_GROUP_NAME]
            copper_children = tuple(cast(bd.Shape, child) for child in copper_group_shape.children)
            if len(copper_children) != 1:
                raise RuntimeError(
                    "type2 tx branch copper group must contain one plate copper child "
                    f"(branch_index={index}, child_count={len(copper_children)})"
                )
            copper_shape = copper_children[0]
        ferrite_group_shape = branch_shape_by_label[_TX_FERRITE_GROUP_NAME]
        ferrite_children = tuple(cast(bd.Shape, child) for child in ferrite_group_shape.children)
        if len(ferrite_children) != 3:
            raise RuntimeError(
                "type2 tx branch ferrite group must contain exactly three children "
                f"(branch_index={index}, child_count={len(ferrite_children)})"
            )

        copper_shape = _rotated_labeled_shape(
            shape=copper_shape,
            axis=branch_hinge_axis,
            angle_deg=branch_rotation_angle_deg,
            label=f"tx_b{index}_plate_copper_source",
        )
        _require_branch_z_bounds(
            shape=copper_shape,
            branch_index=index,
            owner_origin_z=owner_origin_z,
            owner_size_z=owner_size_z,
        )
        branch_copper_shapes.append(copper_shape)

        branch_pcb_wall_shape = _rotated_labeled_shape(
            shape=branch_shape_by_label["tx_pcb_wall"],
            axis=branch_hinge_axis,
            angle_deg=branch_rotation_angle_deg,
            label=f"tx_b{index}_pcb_wall",
        )
        _require_branch_z_bounds(
            shape=branch_pcb_wall_shape,
            branch_index=index,
            owner_origin_z=owner_origin_z,
            owner_size_z=owner_size_z,
        )
        branch_pcb_shapes.append(branch_pcb_wall_shape)

        branch_pcb_coil_shape = _rotated_labeled_shape(
            shape=branch_shape_by_label["tx_pcb_coil"],
            axis=branch_hinge_axis,
            angle_deg=branch_rotation_angle_deg,
            label=f"tx_b{index}_pcb_coil",
        )
        _require_branch_z_bounds(
            shape=branch_pcb_coil_shape,
            branch_index=index,
            owner_origin_z=owner_origin_z,
            owner_size_z=owner_size_z,
        )
        branch_pcb_shapes.append(branch_pcb_coil_shape)

        ferrite_child_by_label = {shape.label: shape for shape in ferrite_children}
        required_ferrite_child_labels = ("tx_stack_pet_psa", "tx_stack_ferrite", "tx_stack_air")
        for required_label in required_ferrite_child_labels:
            if required_label not in ferrite_child_by_label:
                raise RuntimeError(
                    "type2 tx branch ferrite group contract drifted "
                    f"(branch_index={index}, missing={required_label}, actual={tuple(ferrite_child_by_label)})"
                )
        branch_ferrite_pet_psa_shape = _rotated_labeled_shape(
            shape=ferrite_child_by_label["tx_stack_pet_psa"],
            axis=branch_hinge_axis,
            angle_deg=branch_rotation_angle_deg,
            label=f"tx_b{index}_stack_pet_psa",
        )
        branch_ferrite_shape = _rotated_labeled_shape(
            shape=ferrite_child_by_label["tx_stack_ferrite"],
            axis=branch_hinge_axis,
            angle_deg=branch_rotation_angle_deg,
            label=f"tx_b{index}_stack_ferrite",
        )
        branch_ferrite_air_shape = _rotated_labeled_shape(
            shape=ferrite_child_by_label["tx_stack_air"],
            axis=branch_hinge_axis,
            angle_deg=branch_rotation_angle_deg,
            label=f"tx_b{index}_stack_air",
        )
        for branch_ferrite_family_shape in (
            branch_ferrite_pet_psa_shape,
            branch_ferrite_shape,
            branch_ferrite_air_shape,
        ):
            _require_branch_z_bounds(
                shape=branch_ferrite_family_shape,
                branch_index=index,
                owner_origin_z=owner_origin_z,
                owner_size_z=owner_size_z,
            )
        branch_ferrite_shapes.extend((branch_ferrite_pet_psa_shape, branch_ferrite_shape, branch_ferrite_air_shape))

        terminal_metadata = branch_scene_data["terminal_metadata"]
        branch_vertices = cast(tuple[tuple[float, float, float], ...], terminal_metadata["port_sheet_vertices_xyz"])
        if len(branch_vertices) != 4:
            raise RuntimeError(
                f"type2 tx branch terminal metadata must contain four vertices (branch_index={index})"
            )
        if index > 0:
            branch_vertices = tuple(
                _rotate_point_about_axis_y(
                    point=point,
                    axis=branch_hinge_axis,
                    angle_deg=branch_rotation_angle_deg,
                )
                for point in branch_vertices
            )
        branch_input_edges.append((branch_vertices[0], branch_vertices[3]))
        branch_output_edges.append((branch_vertices[1], branch_vertices[2]))

    input_points = tuple(point for edge in branch_input_edges for point in edge)
    output_points = tuple(point for edge in branch_output_edges for point in edge)
    input_z_min = min(point[2] for point in input_points)
    input_z_max = max(point[2] for point in input_points)
    output_z_min = min(point[2] for point in output_points)
    output_z_max = max(point[2] for point in output_points)
    if input_z_max <= input_z_min:
        raise RuntimeError(
            "type2 tx array input bus Z range must be positive "
            f"(z_min={input_z_min}, z_max={input_z_max})"
        )
    if output_z_max <= output_z_min:
        raise RuntimeError(
            "type2 tx array output bus Z range must be positive "
            f"(z_min={output_z_min}, z_max={output_z_max})"
        )
    if len(branch_input_edges) != tx_coil_count or len(branch_output_edges) != tx_coil_count:
        raise RuntimeError(
            "type2 tx array terminal edge ledger must contain one input/output edge per branch "
            f"(branch_count={tx_coil_count}, input_edges={len(branch_input_edges)}, output_edges={len(branch_output_edges)})"
        )
    input_connector_shapes: list[bd.Shape] = []
    output_connector_shapes: list[bd.Shape] = []
    for index in range(tx_coil_count - 1):
        input_label = f"tx_array_input_bridge_s{index}"
        input_vertices = _bridge_connector_vertices(
            label=input_label,
            first_edge=branch_input_edges[index],
            second_edge=branch_input_edges[index + 1],
        )
        input_connector_shapes.append(
            _labeled_bridge_connector_body(
                label=input_label,
                edge_points=input_vertices,
                y_min=tip_y,
                thickness_y_mm=spec.copper_thickness_mm,
            )
        )

        output_label = f"tx_array_output_bridge_s{index}"
        output_vertices = _bridge_connector_vertices(
            label=output_label,
            first_edge=branch_output_edges[index],
            second_edge=branch_output_edges[index + 1],
        )
        output_connector_shapes.append(
            _labeled_bridge_connector_body(
                label=output_label,
                edge_points=output_vertices,
                y_min=tip_y,
                thickness_y_mm=spec.copper_thickness_mm,
            )
        )
    bridge_connector_shapes = (*input_connector_shapes, *output_connector_shapes)
    for connector_shape in bridge_connector_shapes:
        if not connector_shape.label:
            raise RuntimeError("type2 tx array connector bridge label must be non-empty")
        connector_solids = tuple(connector_shape.solids())
        if len(connector_solids) != 1:
            raise RuntimeError(
                "type2 tx array connector bridge must contain exactly one solid "
                f"(label={connector_shape.label}, solid_count={len(connector_solids)})"
            )
        connector_bbox = connector_shape.bounding_box()
        connector_size_y = connector_bbox.max.Y - connector_bbox.min.Y
        if connector_size_y <= 0.0:
            raise RuntimeError(
                "type2 tx array connector bridge thickness must be positive "
                f"(label={connector_shape.label}, thickness_y_mm={connector_size_y})"
            )
        if abs(connector_size_y - spec.copper_thickness_mm) > 1e-9:
            raise RuntimeError(
                "type2 tx array connector bridge thickness must match copper thickness "
                f"(label={connector_shape.label}, thickness_y_mm={connector_size_y}, copper_thickness_mm={spec.copper_thickness_mm})"
            )
        if abs(connector_bbox.min.Y - tip_y) > 1e-9:
            raise RuntimeError(
                "type2 tx array connector bridge Y min must align with branch tip Y plane "
                f"(label={connector_shape.label}, actual={connector_bbox.min.Y}, expected={tip_y})"
            )
    fused_copper_shape = _build_labeled_united_copper_body(
        label=_TX_PLATE_COPPER_NAME,
        source_shapes=tuple((*branch_copper_shapes, *bridge_connector_shapes)),
    )
    fused_copper_solids = tuple(fused_copper_shape.solids())
    if len(fused_copper_solids) != 1:
        raise RuntimeError(
            "type2 tx array copper fuse must resolve to one solid "
            f"(solid_count={len(fused_copper_solids)})"
        )
    fused_copper_solid = fused_copper_solids[0]
    if fused_copper_solid.volume <= 0.0:
        raise RuntimeError(
            "type2 tx array fused copper must have positive volume "
            f"(volume={fused_copper_solid.volume})"
        )
    fused_copper_solid.label = _TX_PLATE_COPPER_NAME

    ferrite_group_shape = bd.Compound(children=tuple(branch_ferrite_shapes), label=_TX_FERRITE_GROUP_NAME)
    top_level_shapes: list[bd.Shape] = [cast(bd.Shape, fused_copper_solid)]
    top_level_shapes.extend(branch_pcb_shapes)
    top_level_shapes.append(cast(bd.Shape, ferrite_group_shape))

    expected_exported_body_names = expected_tx_plate_stack_array_body_names(tx_coil_count=tx_coil_count)
    expected_exported_body_groups = expected_tx_plate_stack_array_body_groups(tx_coil_count=tx_coil_count)
    if not branch_input_edges or not branch_output_edges:
        raise RuntimeError("type2 tx array terminal metadata requires at least one branch range")
    if not copied_branch_rotation_angles_deg:
        raise RuntimeError("type2 tx array copied branch rotation angles must record every branch")
    bbox_list = tuple(shape.bounding_box() for shape in top_level_shapes)
    min_x = min(bbox.min.X for bbox in bbox_list)
    max_x = max(bbox.max.X for bbox in bbox_list)
    min_y = min(bbox.min.Y for bbox in bbox_list)
    max_y = max(bbox.max.Y for bbox in bbox_list)
    min_z = min(bbox.min.Z for bbox in bbox_list)
    max_z = max(bbox.max.Z for bbox in bbox_list)
    canonical_coordinates = dict(first_branch_scene_data["canonical_coordinates"])
    canonical_coordinates["outer_bounds_min_xyz"] = (min_x, min_y, min_z)
    canonical_coordinates["outer_bounds_max_xyz"] = (max_x, max_y, max_z)
    canonical_coordinates["outer_bounds_size_xyz"] = (max_x - min_x, max_y - min_y, max_z - min_z)
    canonical_coordinates["copied_branch_rotation_target_xyz"] = rotation_target_xyz
    canonical_coordinates["copied_branch_hinge_edge_endpoints_xyz"] = tuple(copied_branch_hinge_edges_xyz)
    canonical_coordinates["copied_branch_rotation_angles_deg"] = tuple(copied_branch_rotation_angles_deg)

    terminal_metadata = dict(first_branch_scene_data["terminal_metadata"])
    return (
        tuple(top_level_shapes),
        {
            "object_id": spec.object_id,
            "role": spec.role,
            "plane": "YZ",
            "placement_owner_id": "tx_region",
            "material": spec.material,
            "model_state": True,
            "expected_exported_body_names": expected_exported_body_names,
            "expected_exported_body_count": len(expected_exported_body_names),
            "expected_exported_body_groups": expected_exported_body_groups,
            "canonical_coordinates": canonical_coordinates,
            "terminal_metadata": terminal_metadata,
        },
    )


def _compute_tx_plate_stack_copy_branch_rotation_angle_deg(
    *,
    branch_min_x: float,
    branch_max_x: float,
    branch_hinge_x: float,
    owner_max_z: float,
    rotation_target_xyz: tuple[float, float, float],
) -> float:
    target_x, target_y, target_z = rotation_target_xyz
    if not math.isfinite(target_x) or not math.isfinite(target_y) or not math.isfinite(target_z):
        raise RuntimeError(
            "type2 tx plate-stack copy branch rotation target must be finite "
            f"(target={rotation_target_xyz})"
        )
    if target_z <= owner_max_z + 1e-9:
        raise RuntimeError(
            "type2 tx plate-stack copy branch rotation target must be above top hinge plane "
            f"(target={rotation_target_xyz}, owner_max_z={owner_max_z})"
        )
    if branch_min_x >= branch_max_x - 1e-9:
        raise RuntimeError(
            "type2 tx plate-stack copy branch X bounds are invalid "
            f"(branch_min_x={branch_min_x}, branch_max_x={branch_max_x})"
        )
    _resolved_hinge_x = _resolve_branch_hinge_x(
        branch_min_x=branch_min_x,
        branch_max_x=branch_max_x,
    )
    if abs(branch_hinge_x - _resolved_hinge_x) > 1e-9:
        raise RuntimeError(
            "type2 tx plate-stack copy branch hinge resolution drifted "
            f"(branch_hinge_x={branch_hinge_x}, resolved_hinge_x={_resolved_hinge_x})"
        )
    target_vector_x = target_x - branch_hinge_x
    target_vector_y = target_y
    target_vector_z = target_z - owner_max_z
    if abs(target_vector_x) <= 1e-9:
        raise RuntimeError(
            "type2 tx plate-stack copy branch rotation target X projection is too close to hinge "
            f"(branch_hinge_x={branch_hinge_x}, target={rotation_target_xyz})"
        )
    if target_vector_z <= 1e-9:
        raise RuntimeError(
            "type2 tx plate-stack copy branch rotation target must be above hinge plane "
            f"(target={rotation_target_xyz}, owner_max_z={owner_max_z})"
        )
    angle_deg = -abs(math.degrees(math.atan2(abs(target_vector_x), target_vector_z)))
    if not math.isfinite(angle_deg):
        raise RuntimeError(
            "type2 tx plate-stack copy branch rotation angle must be finite "
            f"(branch_min_x={branch_min_x}, branch_max_x={branch_max_x}, target={rotation_target_xyz})"
        )
    if abs(angle_deg) <= 1e-9:
        raise RuntimeError(
            "type2 tx plate-stack copy branch rotation angle must be nonzero "
            f"(branch_min_x={branch_min_x}, branch_max_x={branch_max_x}, target={rotation_target_xyz})"
        )
    if abs(angle_deg) >= 90.0 - 1e-9:
        raise RuntimeError(
            "type2 tx plate-stack copy branch rotation angle must stay within physical hinge range "
            f"(branch_min_x={branch_min_x}, branch_max_x={branch_max_x}, angle_deg={angle_deg}, target={rotation_target_xyz})"
        )
    return angle_deg


def _resolve_branch_hinge_x(
    *,
    branch_min_x: float,
    branch_max_x: float,
) -> float:
    if branch_min_x >= branch_max_x - 1e-9:
        raise RuntimeError(
            "type2 tx plate-stack hinge resolution requires valid branch x bounds "
            f"(branch_min_x={branch_min_x}, branch_max_x={branch_max_x})"
        )
    return branch_max_x


def _is_nonzero_angle_deg(angle_deg: float) -> bool:
    return abs(angle_deg) > 1e-9


def _rotate_shape_about_y_axis(
    *,
    shape: bd.Shape,
    axis: bd.Axis,
    angle_deg: float,
) -> bd.Shape:
    if not _is_nonzero_angle_deg(angle_deg):
        return shape
    rotated_shape = shape.rotate(axis, angle_deg)
    return rotated_shape


def _rotated_labeled_shape(
    *,
    shape: bd.Shape,
    axis: bd.Axis,
    angle_deg: float,
    label: str,
) -> bd.Shape:
    rotated_shape = _rotate_shape_about_y_axis(shape=shape, axis=axis, angle_deg=angle_deg)
    rotated_shape.label = label
    return rotated_shape


def _require_branch_z_bounds(
    *,
    shape: bd.Shape,
    branch_index: int,
    owner_origin_z: float,
    owner_size_z: float,
) -> None:
    branch_bbox = shape.bounding_box()
    if branch_bbox.min.Z < owner_origin_z - 1e-9:
        raise RuntimeError(
            "type2 tx plate-stack array branch min Z exceeds tx_region lower bound "
            f"(branch_index={branch_index}, branch_min_z={branch_bbox.min.Z}, tx_region_min_z={owner_origin_z})"
        )
    owner_max_z = owner_origin_z + owner_size_z
    if branch_bbox.max.Z > owner_max_z + 1e-9:
        raise RuntimeError(
            "type2 tx plate-stack array branch max Z exceeds tx_region upper bound "
            f"(branch_index={branch_index}, branch_max_z={branch_bbox.max.Z}, tx_region_max_z={owner_max_z})"
        )


def _rotate_point_about_axis_y(
    *,
    point: tuple[float, float, float],
    axis: bd.Axis,
    angle_deg: float,
) -> tuple[float, float, float]:
    if not _is_nonzero_angle_deg(angle_deg):
        return point
    axis_x = axis.position.X
    axis_z = axis.position.Z
    angle_rad = math.radians(angle_deg)
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    point_x, point_y, point_z = point
    translated_x = point_x - axis_x
    translated_z = point_z - axis_z
    rotated_x = axis_x + (cos_theta * translated_x) + (sin_theta * translated_z)
    rotated_z = axis_z + (-sin_theta * translated_x) + (cos_theta * translated_z)
    return (rotated_x, point_y, rotated_z)


def _bridge_connector_vertices(
    *,
    label: str,
    first_edge: tuple[tuple[float, float, float], tuple[float, float, float]],
    second_edge: tuple[tuple[float, float, float], tuple[float, float, float]],
) -> tuple[tuple[float, float, float], ...]:
    edge_points = (first_edge[0], second_edge[0], second_edge[1], first_edge[1])
    first_y = edge_points[0][1]
    for point_index, point in enumerate(edge_points):
        if abs(point[1] - first_y) > 1e-9:
            raise RuntimeError(
                "type2 tx array connector bridge points must share one Y plane "
                f"(label={label}, point_index={point_index}, y={point[1]}, expected_y={first_y})"
            )
    return edge_points


def _labeled_bridge_connector_body(
    *,
    label: str,
    edge_points: tuple[tuple[float, float, float], ...],
    y_min: float,
    thickness_y_mm: float,
) -> bd.Shape:
    if len(edge_points) != 4:
        raise RuntimeError(
            "type2 tx array connector bridge requires exactly four points "
            f"(label={label}, point_count={len(edge_points)})"
        )
    if thickness_y_mm <= 0.0:
        raise RuntimeError(
            "type2 tx array connector bridge thickness must be > 0 "
            f"(label={label}, thickness_y_mm={thickness_y_mm})"
        )
    x_min = min(point[0] for point in edge_points)
    x_max = max(point[0] for point in edge_points)
    z_min = min(point[2] for point in edge_points)
    z_max = max(point[2] for point in edge_points)
    size_x = x_max - x_min
    size_z = z_max - z_min
    if size_x <= 0.0:
        raise RuntimeError(
            "type2 tx array connector bridge X span must be positive "
            f"(label={label}, size_x={size_x})"
        )
    if size_z <= 0.0:
        raise RuntimeError(
            "type2 tx array connector bridge Z span must be positive "
            f"(label={label}, size_z={size_z})"
        )
    bridge_shape = cast(
        bd.Shape,
        bd.Box(
            size_x,
            thickness_y_mm,
            size_z,
            align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
        ).moved(bd.Location((x_min, y_min, z_min))),
    )
    solids = tuple(bridge_shape.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "type2 tx array connector bridge must resolve to exactly one solid "
            f"(label={label}, solid_count={len(solids)})"
        )
    bridge_solid = solids[0]
    if bridge_solid.volume <= 0.0:
        raise RuntimeError(
            "type2 tx array connector bridge must have positive volume "
            f"(label={label}, volume={bridge_solid.volume})"
        )
    bridge_solid.label = label
    return cast(bd.Shape, bridge_solid)


def _build_labeled_united_copper_body(*, label: str, source_shapes: tuple[bd.Shape, ...]) -> bd.Shape:
    if len(source_shapes) == 0:
        raise RuntimeError(f"type2 tx array copper unite requires at least one source body (label={label})")
    fused_shape_or_list: bd.Shape | bd.ShapeList[bd.Shape] = source_shapes[0]
    for source_shape in source_shapes[1:]:
        fuse_base_shape = (
            cast(bd.Shape, bd.Compound(children=tuple(fused_shape_or_list)))
            if isinstance(fused_shape_or_list, bd.ShapeList)
            else fused_shape_or_list
        )
        fused_shape_or_list = fuse_base_shape.fuse(source_shape)
    if isinstance(fused_shape_or_list, bd.ShapeList):
        if len(fused_shape_or_list) != 1:
            raise RuntimeError(
                "type2 tx array copper unite must resolve to one connected shape "
                f"(label={label}, connected_shape_count={len(fused_shape_or_list)})"
            )
        united_shape = cast(bd.Shape, fused_shape_or_list[0])
    else:
        united_shape = fused_shape_or_list
    united_solids = tuple(united_shape.solids())
    if len(united_solids) != 1:
        raise RuntimeError(
            "type2 tx array copper unite must resolve to one solid "
            f"(label={label}, solid_count={len(united_solids)})"
        )
    united_solid = united_solids[0]
    united_solid.label = label
    return cast(bd.Shape, united_solid)


__all__ = [
    "build_tx_plate_stack_array_scene_data",
    "expected_tx_plate_stack_array_body_groups",
    "expected_tx_plate_stack_array_body_names",
]

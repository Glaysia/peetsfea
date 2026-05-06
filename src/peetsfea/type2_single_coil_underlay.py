from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
from typing import Literal, cast

import build123d as bd
from build123d.topology import Shape

from peetsfea.type2_step_ledger import ExportedBodyGroup
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import Point3

_UNDERLAY_FERRITE_THICKNESS_MM = 0.20
_UNDERLAY_PET_PSA_THICKNESS_MM = 0.15
_UNDERLAY_AIR_THICKNESS_MM = 0.02
_RX_BACKING_AIR_RATIO = 0.2
_RX_BACKING_PET_PSA_RATIO = 1.5
_RX_BACKING_FERRITE_RATIO = 2.0
_UNDERLAY_MAX_LABEL_LENGTH = 32
_TX_FERRITE_GROUP_NAME = "g_ferrite_tx"
_TX_OUTER_FERRITE_GROUP_NAME = "g_ferrite_tx_outer"
_RX_FERRITE_GROUP_NAME = "g_ferrite_rx"


@dataclass(frozen=True)
class _TxUnderlayPlacementDescriptor:
    repeat_count: int
    floor_origin_x: float
    floor_origin_y: float
    floor_size_x: float
    floor_size_y: float
    floor_top_z: float
    floor_min_z: float
    wall_min_x: float
    wall_origin_y: float
    wall_origin_z: float
    wall_size_y: float
    wall_size_z: float


@dataclass(frozen=True)
class _TxInnerUnderlayPlacementDescriptor:
    repeat_count: int
    footprint_origin_x: float
    footprint_origin_y: float
    footprint_size_x: float
    footprint_size_y: float
    stack_top_z: float
    stack_min_z: float
    pet_thickness_mm: float
    ferrite_thickness_mm: float


@dataclass(frozen=True)
class _TxVoidStackPlacementDescriptor:
    void_min_x: float
    void_max_x: float
    void_min_y: float
    void_max_y: float
    z_bottom: float
    z_top: float
    pet_thickness_mm: float
    ferrite_thickness_mm: float


def ferrite_group_name_for_modeled_role(
    *,
    role: Literal["tx_single_coil", "tx_inner_single_coil", "tx_outer_single_coil", "rx_single_coil"],
) -> str:
    if role == "tx_single_coil":
        return _TX_FERRITE_GROUP_NAME
    if role == "tx_inner_single_coil":
        return _TX_FERRITE_GROUP_NAME
    if role == "tx_outer_single_coil":
        return _TX_OUTER_FERRITE_GROUP_NAME
    if role == "rx_single_coil":
        return _RX_FERRITE_GROUP_NAME
    raise RuntimeError(f"unsupported ferrite grouping role: {role}")


def _build_labeled_solid_box(*, label: str, origin_xyz: Point3, size_xyz: Point3) -> Shape:
    if len(label) > _UNDERLAY_MAX_LABEL_LENGTH:
        raise RuntimeError(
            "type2 underlay body label must be <= 32 chars "
            f"(label={label}, length={len(label)})"
        )
    size_x, size_y, size_z = size_xyz
    if size_x <= 0.0 or size_y <= 0.0 or size_z <= 0.0:
        raise RuntimeError(
            "type2 underlay body size must be positive "
            f"(label={label}, origin={origin_xyz}, size={size_xyz})"
        )
    shape = bd.Box(
        size_x,
        size_y,
        size_z,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    ).moved(bd.Location(origin_xyz))
    solids = tuple(shape.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "type2 underlay STEP body must contain exactly one solid "
            f"(label={label}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = label
    return solid


def _build_labeled_group(*, label: str, children: tuple[Shape, ...]) -> Shape:
    if len(label) > _UNDERLAY_MAX_LABEL_LENGTH:
        raise RuntimeError(
            "type2 underlay group label must be <= 32 chars "
            f"(label={label}, length={len(label)})"
        )
    if len(children) == 0:
        raise RuntimeError(f"type2 underlay group must contain children (label={label})")
    group = bd.Compound(children=children, label=label)
    return cast(Shape, group)


def is_single_coil_ferrite_pet_psa_tool_label(label: str) -> bool:
    normalized_label = label.lower()
    return "ferrite" in normalized_label or "pet_psa" in normalized_label


def _require_unique_labeled_scene_shapes(*, scene_children: tuple[Shape, ...], context: str) -> dict[str, Shape]:
    if len(scene_children) == 0:
        raise RuntimeError(f"{context} requires at least one scene shape")
    labels = tuple(shape.label for shape in scene_children)
    unlabeled_count = sum(1 for label in labels if label == "")
    if unlabeled_count != 0:
        raise RuntimeError(
            f"{context} requires every top-level scene shape to be labeled "
            f"(unlabeled_count={unlabeled_count}, labels={labels})"
        )
    shapes_by_label = {shape.label: shape for shape in scene_children}
    if len(shapes_by_label) != len(scene_children):
        raise RuntimeError(f"{context} requires unique top-level scene labels (labels={labels})")
    return shapes_by_label


def _require_single_valid_positive_solid(*, shape: Shape, label: str, context: str) -> Shape:
    solids = tuple(shape.solids())
    if len(solids) != 1:
        raise RuntimeError(
            f"{context} shape must contain exactly one solid "
            f"(label={label}, solid_count={len(solids)})"
        )
    solid = solids[0]
    if not solid.is_valid:
        raise RuntimeError(f"{context} shape solid must be valid (label={label})")
    if solid.volume <= 0.0:
        raise RuntimeError(
            f"{context} shape solid must have positive volume "
            f"(label={label}, volume={solid.volume})"
        )
    solid.label = label
    return cast(Shape, solid)


def _tool_shapes_from_group(
    *,
    group_shape: Shape,
    group_label: str,
    tool_label_predicate: Callable[[str], bool],
    context: str,
) -> tuple[Shape, ...]:
    children = tuple(group_shape.children)
    if len(children) == 0:
        raise RuntimeError(f"{context} ferrite/PET_PSA tool group must contain children (group_label={group_label})")
    accepted_children: list[Shape] = []
    child_labels: list[str] = []
    for child in children:
        child_label = child.label
        if child_label == "":
            raise RuntimeError(f"{context} ferrite/PET_PSA tool group child must be labeled (group_label={group_label})")
        child_labels.append(child_label)
        if tool_label_predicate(child_label):
            accepted_children.append(cast(Shape, child))
    if len(child_labels) != len(set(child_labels)):
        raise RuntimeError(
            f"{context} ferrite/PET_PSA tool group child labels must be unique "
            f"(group_label={group_label}, child_labels={tuple(child_labels)})"
        )
    if len(accepted_children) == 0:
        raise RuntimeError(
            f"{context} ferrite/PET_PSA tool group did not contain ferrite/PET_PSA children "
            f"(group_label={group_label}, child_labels={tuple(child_labels)})"
        )
    return tuple(accepted_children)


def _compound_tool_shape(*, tool_shapes: tuple[Shape, ...], context: str) -> Shape:
    if len(tool_shapes) == 0:
        raise RuntimeError(f"{context} requires at least one ferrite/PET_PSA tool shape")
    for tool_shape in tool_shapes:
        _require_single_valid_positive_solid(shape=tool_shape, label=tool_shape.label, context=f"{context} tool")
    return cast(Shape, bd.Compound(children=tool_shapes, label=f"{context}_tools"))


def single_coil_scene_children_with_ferrite_pet_psa_clearance(
    *,
    scene_children: tuple[Shape, ...],
    ferrite_tool_labels: tuple[str, ...],
    ferrite_tool_group_labels: tuple[str, ...],
    pcb_blank_labels: tuple[str, ...],
    context: str,
    tool_label_predicate: Callable[[str], bool] = is_single_coil_ferrite_pet_psa_tool_label,
) -> tuple[Shape, ...]:
    shapes_by_label = _require_unique_labeled_scene_shapes(scene_children=scene_children, context=context)
    if len(pcb_blank_labels) == 0:
        raise RuntimeError(f"{context} requires at least one PCB/FR4 blank label")
    if len(pcb_blank_labels) != len(set(pcb_blank_labels)):
        raise RuntimeError(f"{context} PCB/FR4 blank labels must be unique (labels={pcb_blank_labels})")
    if len(ferrite_tool_labels) != len(set(ferrite_tool_labels)):
        raise RuntimeError(f"{context} ferrite/PET_PSA tool labels must be unique (labels={ferrite_tool_labels})")
    if len(ferrite_tool_group_labels) != len(set(ferrite_tool_group_labels)):
        raise RuntimeError(
            f"{context} ferrite/PET_PSA tool group labels must be unique "
            f"(labels={ferrite_tool_group_labels})"
        )

    tool_shapes: list[Shape] = []
    if len(ferrite_tool_labels) == 0 and len(ferrite_tool_group_labels) == 0:
        for scene_shape in scene_children:
            if tool_label_predicate(scene_shape.label):
                tool_shapes.append(scene_shape)
    else:
        for tool_label in ferrite_tool_labels:
            if tool_label not in shapes_by_label:
                raise RuntimeError(f"{context} missing ferrite/PET_PSA tool label (label={tool_label})")
            tool_shapes.append(shapes_by_label[tool_label])
        for group_label in ferrite_tool_group_labels:
            if group_label not in shapes_by_label:
                raise RuntimeError(f"{context} missing ferrite/PET_PSA tool group label (label={group_label})")
            group_tool_shapes = _tool_shapes_from_group(
                group_shape=shapes_by_label[group_label],
                group_label=group_label,
                tool_label_predicate=tool_label_predicate,
                context=context,
            )
            tool_shapes.extend(group_tool_shapes)

    tool_labels = tuple(shape.label for shape in tool_shapes)
    if len(tool_labels) != len(set(tool_labels)):
        raise RuntimeError(f"{context} resolved ferrite/PET_PSA tool labels must be unique (labels={tool_labels})")
    tool_shape = _compound_tool_shape(tool_shapes=tuple(tool_shapes), context=context)
    blank_label_set = set(pcb_blank_labels)
    cleared_scene_children: list[Shape] = []
    for scene_shape in scene_children:
        label = scene_shape.label
        if label not in blank_label_set:
            cleared_scene_children.append(scene_shape)
            continue
        _require_single_valid_positive_solid(shape=scene_shape, label=label, context=f"{context} blank")
        raw_cut_shape = scene_shape.cut(tool_shape)
        assert isinstance(raw_cut_shape, Shape), (
            f"{context} cut must return a build123d Shape "
            f"(label={label}, actual_type={type(raw_cut_shape)!r})"
        )
        cut_shape = raw_cut_shape.clean().fix()
        assert isinstance(cut_shape, Shape), (
            f"{context} cleaned cut must return a build123d Shape "
            f"(label={label}, actual_type={type(cut_shape)!r})"
        )
        cleared_scene_children.append(
            _require_single_valid_positive_solid(shape=cut_shape, label=label, context=f"{context} cut")
        )

    cleared_labels = tuple(shape.label for shape in cleared_scene_children)
    original_labels = tuple(shape.label for shape in scene_children)
    if cleared_labels != original_labels:
        raise RuntimeError(
            f"{context} boolean clearance must preserve top-level label order "
            f"(original={original_labels}, cleared={cleared_labels})"
        )
    cleared_blank_count = sum(1 for shape in cleared_scene_children if shape.label in blank_label_set)
    if cleared_blank_count != len(pcb_blank_labels):
        raise RuntimeError(
            f"{context} did not find every PCB/FR4 blank label "
            f"(expected={pcb_blank_labels}, cleared_count={cleared_blank_count})"
        )
    return tuple(cleared_scene_children)


def single_coil_expected_ferrite_groups(
    *,
    role: Literal["tx_single_coil", "tx_inner_single_coil", "tx_outer_single_coil", "rx_single_coil"],
    underlay_scene_children: tuple[Shape, ...],
) -> tuple[ExportedBodyGroup, ...]:
    if len(underlay_scene_children) == 0:
        return ()
    member_body_names = tuple(shape.label for shape in underlay_scene_children)
    if any(member_name == "" for member_name in member_body_names):
        raise RuntimeError(
            "type2 ferrite grouping requires labeled underlay members "
            f"(role={role}, member_body_names={member_body_names})"
        )
    return (
        {
            "group_name": ferrite_group_name_for_modeled_role(role=role),
            "member_body_names": member_body_names,
        },
    )


def single_coil_scene_children_with_grouped_ferrite_family(
    *,
    base_scene_children: tuple[Shape, ...],
    underlay_scene_children: tuple[Shape, ...],
    expected_exported_body_groups: tuple[ExportedBodyGroup, ...],
) -> tuple[Shape, ...]:
    if len(underlay_scene_children) == 0:
        if len(expected_exported_body_groups) != 0:
            raise RuntimeError(
                "type2 ferrite group contract mismatch: no underlay members but groups were declared "
                f"(groups={expected_exported_body_groups})"
            )
        return base_scene_children
    if len(expected_exported_body_groups) != 1:
        raise RuntimeError(
            "type2 ferrite group contract requires exactly one group when underlay members are exported "
            f"(group_count={len(expected_exported_body_groups)})"
        )
    group_entry = expected_exported_body_groups[0]
    member_body_names = group_entry["member_body_names"]
    underlay_member_body_names = tuple(shape.label for shape in underlay_scene_children)
    if member_body_names != underlay_member_body_names:
        raise RuntimeError(
            "type2 ferrite group members must match underlay export order "
            f"(expected={member_body_names}, actual={underlay_member_body_names})"
        )
    shapes_by_label = {shape.label: shape for shape in underlay_scene_children}
    if len(shapes_by_label) != len(underlay_scene_children):
        raise RuntimeError(
            "type2 underlay scene body names must be unique for ferrite grouping "
            f"(body_names={underlay_member_body_names})"
        )
    ferrite_group_shape = _build_labeled_group(
        label=group_entry["group_name"],
        children=tuple(shapes_by_label[member_name] for member_name in member_body_names),
    )
    return base_scene_children + (ferrite_group_shape,)


def _underlay_unit_thickness_mm() -> float:
    return _UNDERLAY_FERRITE_THICKNESS_MM + _UNDERLAY_PET_PSA_THICKNESS_MM + _UNDERLAY_AIR_THICKNESS_MM


def _effective_underlay_layer_thickness_mm(*, repeat_count: int, layer_thickness_mm: float, context: str) -> float:
    if repeat_count < 1:
        raise RuntimeError(f"{context} repeat count must be >= 1 (actual={repeat_count})")
    effective_thickness_mm = float(repeat_count) * layer_thickness_mm
    if effective_thickness_mm <= 0.0:
        raise RuntimeError(
            f"{context} effective thickness must be > 0 "
            f"(repeat_count={repeat_count}, layer_thickness_mm={layer_thickness_mm})"
        )
    return effective_thickness_mm


def resolve_tx_underlay_placement_descriptor(
    *,
    owner_spec: NonModelBoxSpec,
    modeled_min_z: float,
    modeled_max_x: float,
    repeat_count: int,
    gap_mm: float,
) -> _TxUnderlayPlacementDescriptor:
    if owner_spec.plane != "XY":
        raise RuntimeError(f"type2 tx underlay requires XY owner plane (owner={owner_spec.object_id})")
    if repeat_count < 1:
        raise RuntimeError(f"type2 tx underlay repeat count must be >= 1 when underlay is emitted (actual={repeat_count})")
    if gap_mm <= 0.0:
        raise RuntimeError(
            "type2 tx underlay gap must be positive "
            f"(object_id={owner_spec.object_id}, gap_mm={gap_mm})"
        )
    footprint_origin_x, footprint_origin_y, footprint_origin_z = owner_spec.origin_xyz
    footprint_size_x, footprint_size_y, owner_size_z = owner_spec.size_xyz
    if footprint_size_x <= 0.0 or footprint_size_y <= 0.0:
        raise RuntimeError(
            "type2 tx underlay footprint must be positive "
            f"(object_id={owner_spec.object_id}, size={owner_spec.size_xyz})"
        )
    unit_thickness_mm = _underlay_unit_thickness_mm()
    total_thickness_mm = repeat_count * unit_thickness_mm
    floor_min_z = modeled_min_z - gap_mm - total_thickness_mm
    if floor_min_z < footprint_origin_z:
        raise RuntimeError(
            "type2 tx underlay stack must fit inside tx_region thickness "
            f"(owner={owner_spec.object_id}, owner_min_z={footprint_origin_z}, underlay_min_z={floor_min_z}, "
            f"modeled_min_z={modeled_min_z}, gap_mm={gap_mm}, repeat_count={repeat_count})"
        )
    wall_min_x = footprint_origin_x
    available_wall_span_mm = modeled_max_x - wall_min_x
    if total_thickness_mm > available_wall_span_mm:
        raise RuntimeError(
            "type2 tx wall underlay stack must fit inside tx_region wall-side span "
            f"(owner={owner_spec.object_id}, wall_min_x={wall_min_x}, modeled_max_x={modeled_max_x}, "
            f"required_thickness_mm={total_thickness_mm}, available_thickness_mm={available_wall_span_mm}, "
            f"repeat_count={repeat_count})"
        )
    wall_size_z = floor_min_z - footprint_origin_z
    if wall_size_z <= 0.0:
        raise RuntimeError(
            "type2 tx wall underlay stack requires positive remaining height below XY underlay "
            f"(owner={owner_spec.object_id}, owner_min_z={footprint_origin_z}, floor_underlay_min_z={floor_min_z})"
        )
    return _TxUnderlayPlacementDescriptor(
        repeat_count=repeat_count,
        floor_origin_x=footprint_origin_x,
        floor_origin_y=footprint_origin_y,
        floor_size_x=footprint_size_x,
        floor_size_y=footprint_size_y,
        floor_top_z=modeled_min_z - gap_mm,
        floor_min_z=floor_min_z,
        wall_min_x=wall_min_x,
        wall_origin_y=footprint_origin_y,
        wall_origin_z=footprint_origin_z,
        wall_size_y=footprint_size_y,
        wall_size_z=wall_size_z,
    )


def resolve_tx_inner_single_coil_underlay_placement_descriptor(
    *,
    owner_spec: NonModelBoxSpec,
    actual_region_min_xyz: Point3,
    actual_region_size_xyz: Point3,
    repeat_count: int,
    pet_psa_thickness_mm: float,
    ferrite_thickness_mm: float,
) -> _TxInnerUnderlayPlacementDescriptor:
    if owner_spec.plane != "XY":
        raise RuntimeError(
            f"type2 tx_inner underlay requires XY owner plane (owner={owner_spec.object_id})"
        )
    if repeat_count < 0:
        raise RuntimeError(
            f"type2 tx_inner underlay repeat count must be >= 0 (actual={repeat_count})"
        )
    if not math.isfinite(pet_psa_thickness_mm) or pet_psa_thickness_mm <= 0.0:
        raise RuntimeError(
            "type2 tx_inner underlay PET_PSA thickness must be finite and > 0 "
            f"(object_id={owner_spec.object_id}, pet_psa_thickness_mm={pet_psa_thickness_mm})"
        )
    if not math.isfinite(ferrite_thickness_mm) or ferrite_thickness_mm <= 0.0:
        raise RuntimeError(
            "type2 tx_inner underlay ferrite thickness must be finite and > 0 "
            f"(object_id={owner_spec.object_id}, ferrite_thickness_mm={ferrite_thickness_mm})"
        )
    actual_region_min_x, actual_region_min_y, actual_region_min_z = actual_region_min_xyz
    actual_region_size_x, actual_region_size_y, actual_region_size_z = actual_region_size_xyz
    if (
        not math.isfinite(actual_region_min_x)
        or not math.isfinite(actual_region_min_y)
        or not math.isfinite(actual_region_min_z)
        or not math.isfinite(actual_region_size_x)
        or not math.isfinite(actual_region_size_y)
        or not math.isfinite(actual_region_size_z)
    ):
        raise RuntimeError(f"type2 tx_inner actual region geometry must be finite (object_id={owner_spec.object_id})")
    if actual_region_size_x <= 0.0 or actual_region_size_y <= 0.0 or actual_region_size_z <= 0.0:
        raise RuntimeError(
            "type2 tx_inner actual region design bounds must be positive "
            f"(object_id={owner_spec.object_id}, actual_region_size_mm={actual_region_size_xyz})"
        )
    layer_pair_thickness_mm = pet_psa_thickness_mm + ferrite_thickness_mm
    total_thickness_mm = repeat_count * layer_pair_thickness_mm
    stack_top_z = actual_region_min_z
    stack_min_z = stack_top_z - total_thickness_mm
    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if stack_top_z > owner_origin_z + owner_size_z:
        raise RuntimeError(
            "type2 tx_inner underlay stack top must be below tx_inner_region top boundary "
            f"(owner={owner_spec.object_id}, owner_max_z={owner_origin_z + owner_size_z}, stack_top_z={stack_top_z})"
        )
    if stack_min_z < owner_origin_z - 1e-12:
        raise RuntimeError(
            "type2 tx_inner underlay stack must fit inside tx_inner_region bottom boundary "
            f"(owner={owner_spec.object_id}, owner_min_z={owner_origin_z}, stack_min_z={stack_min_z}, "
            f"repeat_count={repeat_count}, pet_psa_thickness_mm={pet_psa_thickness_mm}, ferrite_thickness_mm={ferrite_thickness_mm})"
        )
    if actual_region_min_x < owner_origin_x - 1e-12 or actual_region_min_y < owner_origin_y - 1e-12:
        raise RuntimeError(
            "type2 tx_inner underlay footprint must stay within tx_inner_region min bounds "
            f"(owner={owner_spec.object_id}, owner_min_xyz={(owner_origin_x, owner_origin_y)}, "
            f"actual_region_min_xyz={(actual_region_min_x, actual_region_min_y)})"
        )
    if actual_region_min_x + actual_region_size_x > owner_origin_x + owner_size_x + 1e-12:
        raise RuntimeError(
            "type2 tx_inner underlay footprint must stay within tx_inner_region max bounds "
            f"(owner={owner_spec.object_id}, owner_max_x={owner_origin_x + owner_size_x}, actual_region_max_x={actual_region_min_x + actual_region_size_x})"
        )
    if actual_region_min_y + actual_region_size_y > owner_origin_y + owner_size_y + 1e-12:
        raise RuntimeError(
            "type2 tx_inner underlay footprint must stay within tx_inner_region max bounds "
            f"(owner={owner_spec.object_id}, owner_max_y={owner_origin_y + owner_size_y}, actual_region_max_y={actual_region_min_y + actual_region_size_y})"
        )
    if repeat_count == 0:
        if total_thickness_mm != 0.0:
            raise RuntimeError(
                "type2 tx_inner underlay total thickness must be zero when repeat_count is zero "
                f"(owner={owner_spec.object_id}, total_thickness_mm={total_thickness_mm})"
            )
        return _TxInnerUnderlayPlacementDescriptor(
            repeat_count=0,
            footprint_origin_x=actual_region_min_x,
            footprint_origin_y=actual_region_min_y,
            footprint_size_x=actual_region_size_x,
            footprint_size_y=actual_region_size_y,
            stack_top_z=stack_top_z,
            stack_min_z=stack_top_z,
            pet_thickness_mm=pet_psa_thickness_mm,
            ferrite_thickness_mm=ferrite_thickness_mm,
        )
    return _TxInnerUnderlayPlacementDescriptor(
        repeat_count=repeat_count,
        footprint_origin_x=actual_region_min_x,
        footprint_origin_y=actual_region_min_y,
        footprint_size_x=actual_region_size_x,
        footprint_size_y=actual_region_size_y,
        stack_top_z=stack_top_z,
        stack_min_z=stack_min_z,
        pet_thickness_mm=pet_psa_thickness_mm,
        ferrite_thickness_mm=ferrite_thickness_mm,
    )


def resolve_tx_outer_single_coil_underlay_placement_descriptor(
    *,
    actual_region_min_xyz: Point3,
    actual_region_size_xyz: Point3,
    repeat_count: int,
    pet_psa_thickness_mm: float,
    ferrite_thickness_mm: float,
    owner_thickness_mm: float,
) -> _TxInnerUnderlayPlacementDescriptor:
    if repeat_count < 0:
        raise RuntimeError(
            f"type2 tx_outer underlay repeat count must be >= 0 (actual={repeat_count})"
        )
    geometry_values = actual_region_min_xyz + actual_region_size_xyz + (
        pet_psa_thickness_mm,
        ferrite_thickness_mm,
        owner_thickness_mm,
    )
    if any(not math.isfinite(value) for value in geometry_values):
        raise RuntimeError(
            "type2 tx_outer underlay geometry must be finite "
            f"(actual_region_min_xyz={actual_region_min_xyz}, actual_region_size_xyz={actual_region_size_xyz}, "
            f"pet_psa_thickness_mm={pet_psa_thickness_mm}, ferrite_thickness_mm={ferrite_thickness_mm}, "
            f"owner_thickness_mm={owner_thickness_mm})"
        )
    actual_region_min_x, actual_region_min_y, actual_region_min_z = actual_region_min_xyz
    actual_region_size_x, actual_region_size_y, actual_region_size_z = actual_region_size_xyz
    if actual_region_size_x <= 0.0 or actual_region_size_y <= 0.0 or actual_region_size_z <= 0.0:
        raise RuntimeError(
            "type2 tx_outer underlay design bounds must be positive "
            f"(actual_region_size_mm={actual_region_size_xyz})"
        )
    if pet_psa_thickness_mm <= 0.0 or ferrite_thickness_mm <= 0.0 or owner_thickness_mm <= 0.0:
        raise RuntimeError(
            "type2 tx_outer underlay thicknesses must be positive "
            f"(pet_psa_thickness_mm={pet_psa_thickness_mm}, ferrite_thickness_mm={ferrite_thickness_mm}, "
            f"owner_thickness_mm={owner_thickness_mm})"
        )
    total_thickness_mm = repeat_count * (pet_psa_thickness_mm + ferrite_thickness_mm)
    stack_top_z = actual_region_min_z
    stack_min_z = stack_top_z - total_thickness_mm
    virtual_owner_min_z = -owner_thickness_mm
    if stack_min_z < virtual_owner_min_z - 1e-12:
        raise RuntimeError(
            "type2 tx_outer underlay stack must fit inside tx_outer_region virtual thickness "
            f"(owner_min_z={virtual_owner_min_z}, stack_min_z={stack_min_z}, repeat_count={repeat_count}, "
            f"pet_psa_thickness_mm={pet_psa_thickness_mm}, ferrite_thickness_mm={ferrite_thickness_mm})"
        )
    return _TxInnerUnderlayPlacementDescriptor(
        repeat_count=repeat_count,
        footprint_origin_x=actual_region_min_x,
        footprint_origin_y=actual_region_min_y,
        footprint_size_x=actual_region_size_x,
        footprint_size_y=actual_region_size_y,
        stack_top_z=stack_top_z,
        stack_min_z=stack_min_z,
        pet_thickness_mm=pet_psa_thickness_mm,
        ferrite_thickness_mm=ferrite_thickness_mm,
    )


def build_tx_inner_single_coil_underlay_shapes(
    descriptor: _TxInnerUnderlayPlacementDescriptor,
) -> tuple[Shape, ...]:
    return _build_tx_single_coil_underlay_shapes(
        descriptor,
        context="type2 tx_inner underlay",
        pet_psa_label_prefix="tx_underlay_pet_psa_u",
        ferrite_label_prefix="tx_underlay_ferrite_u",
    )


def build_tx_outer_single_coil_underlay_shapes(
    descriptor: _TxInnerUnderlayPlacementDescriptor,
) -> tuple[Shape, ...]:
    return _build_tx_single_coil_underlay_shapes(
        descriptor,
        context="type2 tx_outer underlay",
        pet_psa_label_prefix="tx_outer_underlay_pet_psa_u",
        ferrite_label_prefix="tx_outer_underlay_ferrite_u",
    )


def _build_tx_single_coil_underlay_shapes(
    descriptor: _TxInnerUnderlayPlacementDescriptor,
    *,
    context: str,
    pet_psa_label_prefix: str,
    ferrite_label_prefix: str,
) -> tuple[Shape, ...]:
    if descriptor.repeat_count == 0:
        return ()
    if (
        not math.isfinite(descriptor.stack_top_z)
        or not math.isfinite(descriptor.stack_min_z)
        or descriptor.footprint_size_x <= 0.0
        or descriptor.footprint_size_y <= 0.0
        or descriptor.pet_thickness_mm <= 0.0
        or descriptor.ferrite_thickness_mm <= 0.0
    ):
        raise RuntimeError(
            "type2 tx_inner underlay geometry parameters must be finite and positive "
            f"(repeat_count={descriptor.repeat_count}, stack_top_z={descriptor.stack_top_z}, "
            f"stack_min_z={descriptor.stack_min_z}, pet_thickness_mm={descriptor.pet_thickness_mm}, "
            f"ferrite_thickness_mm={descriptor.ferrite_thickness_mm})"
        )
    current_top_z = descriptor.stack_top_z
    scene_children: list[Shape] = []
    for repeat_index in range(descriptor.repeat_count):
        pet_origin_xyz = (
            descriptor.footprint_origin_x,
            descriptor.footprint_origin_y,
            current_top_z - descriptor.pet_thickness_mm,
        )
        scene_children.append(
            _build_labeled_solid_box(
                label=f"{pet_psa_label_prefix}{repeat_index}",
                origin_xyz=pet_origin_xyz,
                size_xyz=(
                    descriptor.footprint_size_x,
                    descriptor.footprint_size_y,
                    descriptor.pet_thickness_mm,
                ),
            )
        )
        ferrite_origin_xyz = (
            descriptor.footprint_origin_x,
            descriptor.footprint_origin_y,
            pet_origin_xyz[2] - descriptor.ferrite_thickness_mm,
        )
        scene_children.append(
            _build_labeled_solid_box(
                label=f"{ferrite_label_prefix}{repeat_index}",
                origin_xyz=ferrite_origin_xyz,
                size_xyz=(
                    descriptor.footprint_size_x,
                    descriptor.footprint_size_y,
                    descriptor.ferrite_thickness_mm,
                ),
            )
        )
        current_top_z = ferrite_origin_xyz[2]
    expected_stack_min_z = descriptor.stack_top_z - (
        descriptor.repeat_count * (descriptor.pet_thickness_mm + descriptor.ferrite_thickness_mm)
    )
    if not math.isclose(current_top_z, expected_stack_min_z, rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError(
            f"{context} stack thickness mismatch "
            f"(repeat_count={descriptor.repeat_count}, current_top_z={current_top_z}, expected={expected_stack_min_z})"
        )
    return tuple(scene_children)


def resolve_tx_inner_single_coil_void_stack_placement_descriptor(
    *,
    void_min_x: float,
    void_max_x: float,
    void_min_y: float,
    void_max_y: float,
    z_bottom: float,
    z_top: float,
    pet_psa_thickness_mm: float,
    ferrite_thickness_mm: float,
) -> _TxVoidStackPlacementDescriptor:
    geometry_values = (
        void_min_x,
        void_max_x,
        void_min_y,
        void_max_y,
        z_bottom,
        z_top,
        pet_psa_thickness_mm,
        ferrite_thickness_mm,
    )
    if any(not math.isfinite(value) for value in geometry_values):
        raise RuntimeError(
            "type2 tx_inner void stack geometry must be finite "
            f"(void_min_x={void_min_x}, void_max_x={void_max_x}, void_min_y={void_min_y}, "
            f"void_max_y={void_max_y}, z_bottom={z_bottom}, z_top={z_top}, "
            f"pet_psa_thickness_mm={pet_psa_thickness_mm}, ferrite_thickness_mm={ferrite_thickness_mm})"
        )
    if void_max_x <= void_min_x or void_max_y <= void_min_y:
        raise RuntimeError(
            "type2 tx_inner void stack footprint must be positive "
            f"(void_min_x={void_min_x}, void_max_x={void_max_x}, void_min_y={void_min_y}, void_max_y={void_max_y})"
        )
    if z_top <= z_bottom:
        raise RuntimeError(
            "type2 tx_inner void stack Z span must be positive "
            f"(z_bottom={z_bottom}, z_top={z_top})"
        )
    if pet_psa_thickness_mm <= 0.0 or ferrite_thickness_mm <= 0.0:
        raise RuntimeError(
            "type2 tx_inner void stack sheet thicknesses must be finite and > 0 "
            f"(pet_psa_thickness_mm={pet_psa_thickness_mm}, ferrite_thickness_mm={ferrite_thickness_mm})"
        )
    return _TxVoidStackPlacementDescriptor(
        void_min_x=void_min_x,
        void_max_x=void_max_x,
        void_min_y=void_min_y,
        void_max_y=void_max_y,
        z_bottom=z_bottom,
        z_top=z_top,
        pet_thickness_mm=pet_psa_thickness_mm,
        ferrite_thickness_mm=ferrite_thickness_mm,
    )


def _build_tx_void_stack_shapes(
    descriptor: _TxVoidStackPlacementDescriptor,
    *,
    context: str,
    ferrite_label_prefix: str,
    pet_psa_label_prefix: str,
) -> tuple[Shape, ...]:
    span_y = descriptor.void_max_y - descriptor.void_min_y
    span_z = descriptor.z_top - descriptor.z_bottom
    remaining_x = descriptor.void_max_x - descriptor.void_min_x
    geometry_values = (
        descriptor.void_min_x,
        descriptor.void_max_x,
        descriptor.void_min_y,
        descriptor.void_max_y,
        descriptor.z_bottom,
        descriptor.z_top,
        descriptor.pet_thickness_mm,
        descriptor.ferrite_thickness_mm,
        span_y,
        span_z,
        remaining_x,
    )
    if any(not math.isfinite(value) for value in geometry_values):
        raise RuntimeError(f"{context} descriptor must be finite (descriptor={descriptor})")
    if remaining_x <= 0.0 or span_y <= 0.0 or span_z <= 0.0:
        raise RuntimeError(f"{context} descriptor spans must be positive (descriptor={descriptor})")
    if descriptor.pet_thickness_mm <= 0.0 or descriptor.ferrite_thickness_mm <= 0.0:
        raise RuntimeError(f"{context} descriptor thicknesses must be positive (descriptor={descriptor})")

    current_x = descriptor.void_min_x
    ferrite_index = 0
    pet_index = 0
    next_is_ferrite = True
    scene_children: list[Shape] = []
    while current_x < descriptor.void_max_x - 1e-12:
        nominal_thickness = descriptor.ferrite_thickness_mm if next_is_ferrite else descriptor.pet_thickness_mm
        sheet_thickness = min(nominal_thickness, descriptor.void_max_x - current_x)
        if sheet_thickness <= 0.0 or not math.isfinite(sheet_thickness):
            raise RuntimeError(
                f"{context} sheet thickness must be finite and positive "
                f"(current_x={current_x}, void_max_x={descriptor.void_max_x}, nominal_thickness={nominal_thickness})"
            )
        if next_is_ferrite:
            label = f"{ferrite_label_prefix}{ferrite_index}"
            ferrite_index += 1
        else:
            label = f"{pet_psa_label_prefix}{pet_index}"
            pet_index += 1
        scene_children.append(
            _build_labeled_solid_box(
                label=label,
                origin_xyz=(current_x, descriptor.void_min_y, descriptor.z_bottom),
                size_xyz=(sheet_thickness, span_y, span_z),
            )
        )
        current_x += sheet_thickness
        next_is_ferrite = not next_is_ferrite
    if not math.isclose(current_x, descriptor.void_max_x, rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError(
            f"{context} must end exactly at void.max_x "
            f"(actual_end_x={current_x}, void_max_x={descriptor.void_max_x})"
        )
    if len(scene_children) == 0:
        raise RuntimeError(f"{context} must emit at least one sheet (descriptor={descriptor})")
    return tuple(scene_children)


def _build_tx_inner_void_stack_pair_shapes(
    descriptor: _TxVoidStackPlacementDescriptor,
) -> tuple[Shape, ...]:
    context = "type2 tx_inner void stack"
    span_x = descriptor.void_max_x - descriptor.void_min_x
    span_y = descriptor.void_max_y - descriptor.void_min_y
    span_z = descriptor.z_top - descriptor.z_bottom
    minimum_pair_width = descriptor.ferrite_thickness_mm + descriptor.pet_thickness_mm
    geometry_values = (
        descriptor.void_min_x,
        descriptor.void_max_x,
        descriptor.void_min_y,
        descriptor.void_max_y,
        descriptor.z_bottom,
        descriptor.z_top,
        descriptor.pet_thickness_mm,
        descriptor.ferrite_thickness_mm,
        span_x,
        span_y,
        span_z,
        minimum_pair_width,
    )
    if any(not math.isfinite(value) for value in geometry_values):
        raise RuntimeError(f"{context} descriptor must be finite (descriptor={descriptor})")
    if span_x <= 0.0 or span_y <= 0.0 or span_z <= 0.0:
        raise RuntimeError(f"{context} descriptor spans must be positive (descriptor={descriptor})")
    if descriptor.pet_thickness_mm <= 0.0 or descriptor.ferrite_thickness_mm <= 0.0:
        raise RuntimeError(f"{context} descriptor thicknesses must be positive (descriptor={descriptor})")

    pair_count = 0
    pair_span_x = 0.0
    for candidate_pair_count in range(4, 0, -1):
        candidate_pair_span_x = span_x / float(candidate_pair_count)
        if candidate_pair_span_x >= minimum_pair_width:
            pair_count = candidate_pair_count
            pair_span_x = candidate_pair_span_x
            break
    if pair_count == 0:
        raise RuntimeError(
            f"{context} void stack width cannot fit one minimum ferrite/PET_PSA pair "
            f"(void_width={span_x}, ferrite_min_width={descriptor.ferrite_thickness_mm}, "
            f"pet_psa_min_width={descriptor.pet_thickness_mm}, minimum_pair_width={minimum_pair_width})"
        )

    leftover_pair_width = pair_span_x - minimum_pair_width
    if leftover_pair_width < 0.0 or not math.isfinite(leftover_pair_width):
        raise RuntimeError(
            f"{context} pair leftover width must be finite and non-negative "
            f"(pair_count={pair_count}, pair_span_x={pair_span_x}, minimum_pair_width={minimum_pair_width})"
        )
    ferrite_width = descriptor.ferrite_thickness_mm + (leftover_pair_width / 2.0)
    pet_width = descriptor.pet_thickness_mm + (leftover_pair_width / 2.0)
    if ferrite_width <= 0.0 or pet_width <= 0.0:
        raise RuntimeError(
            f"{context} pair sheet widths must be positive "
            f"(pair_count={pair_count}, ferrite_width={ferrite_width}, pet_psa_width={pet_width})"
        )

    current_x = descriptor.void_min_x
    scene_children: list[Shape] = []
    for pair_index in range(pair_count):
        scene_children.append(
            _build_labeled_solid_box(
                label=f"tx_void_ferrite_u{pair_index}",
                origin_xyz=(current_x, descriptor.void_min_y, descriptor.z_bottom),
                size_xyz=(ferrite_width, span_y, span_z),
            )
        )
        current_x += ferrite_width
        scene_children.append(
            _build_labeled_solid_box(
                label=f"tx_void_pet_psa_u{pair_index}",
                origin_xyz=(current_x, descriptor.void_min_y, descriptor.z_bottom),
                size_xyz=(pet_width, span_y, span_z),
            )
        )
        current_x += pet_width
    if not math.isclose(current_x, descriptor.void_max_x, rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError(
            f"{context} must end exactly at void.max_x "
            f"(actual_end_x={current_x}, void_max_x={descriptor.void_max_x}, pair_count={pair_count})"
        )
    return tuple(scene_children)


def build_tx_inner_single_coil_void_stack_shapes(
    descriptor: _TxVoidStackPlacementDescriptor,
) -> tuple[Shape, ...]:
    return _build_tx_inner_void_stack_pair_shapes(descriptor)



def build_tx_outer_single_coil_void_stack_shapes(
    descriptor: _TxVoidStackPlacementDescriptor,
) -> tuple[Shape, ...]:
    return _build_tx_void_stack_shapes(
        descriptor,
        context="type2 tx_outer void stack",
        ferrite_label_prefix="tx_outer_void_ferrite_u",
        pet_psa_label_prefix="tx_outer_void_pet_psa_u",
    )


def build_tx_wall_parallel_scene_shapes(descriptor: _TxUnderlayPlacementDescriptor) -> tuple[Shape, ...]:
    ferrite_thickness_mm = _effective_underlay_layer_thickness_mm(
        repeat_count=descriptor.repeat_count,
        layer_thickness_mm=_UNDERLAY_FERRITE_THICKNESS_MM,
        context="type2 tx wall underlay ferrite",
    )
    pet_thickness_mm = _effective_underlay_layer_thickness_mm(
        repeat_count=descriptor.repeat_count,
        layer_thickness_mm=_UNDERLAY_PET_PSA_THICKNESS_MM,
        context="type2 tx wall underlay pet_psa",
    )
    air_thickness_mm = _effective_underlay_layer_thickness_mm(
        repeat_count=descriptor.repeat_count,
        layer_thickness_mm=_UNDERLAY_AIR_THICKNESS_MM,
        context="type2 tx wall underlay air",
    )
    ferrite_origin_x = descriptor.wall_min_x
    pet_origin_x = ferrite_origin_x + ferrite_thickness_mm
    air_origin_x = pet_origin_x + pet_thickness_mm
    return (
        _build_labeled_solid_box(
            label="tx_wall_ferrite_u0",
            origin_xyz=(ferrite_origin_x, descriptor.wall_origin_y, descriptor.wall_origin_z),
            size_xyz=(
                ferrite_thickness_mm,
                descriptor.wall_size_y,
                descriptor.wall_size_z,
            ),
        ),
        _build_labeled_solid_box(
            label="tx_wall_pet_psa_u0",
            origin_xyz=(pet_origin_x, descriptor.wall_origin_y, descriptor.wall_origin_z),
            size_xyz=(
                pet_thickness_mm,
                descriptor.wall_size_y,
                descriptor.wall_size_z,
            ),
        ),
        _build_labeled_solid_box(
            label="tx_wall_air_u0",
            origin_xyz=(air_origin_x, descriptor.wall_origin_y, descriptor.wall_origin_z),
            size_xyz=(
                air_thickness_mm,
                descriptor.wall_size_y,
                descriptor.wall_size_z,
            ),
        ),
    )


def build_rx_underlay_scene_shapes(
    *,
    owner_spec: NonModelBoxSpec,
    repeat_count: int,
    modeled_bounds_min_xyz: Point3,
    modeled_bounds_max_xyz: Point3,
) -> tuple[Shape, ...]:
    if owner_spec.plane != "YZ":
        raise RuntimeError(f"type2 rx underlay requires YZ owner plane (owner={owner_spec.object_id})")
    if repeat_count < 1:
        raise RuntimeError(f"type2 rx underlay repeat count must be >= 1 when underlay is emitted (actual={repeat_count})")
    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if owner_size_y <= 0.0 or owner_size_z <= 0.0:
        raise RuntimeError(
            "type2 rx underlay footprint must be positive "
            f"(object_id={owner_spec.object_id}, size={owner_spec.size_xyz})"
        )
    owner_max_x = owner_origin_x + owner_size_x
    modeled_min_x = modeled_bounds_min_xyz[0]
    modeled_max_x = modeled_bounds_max_xyz[0]
    if modeled_max_x > owner_max_x + 1e-9:
        raise RuntimeError(
            "type2 rx modeled stack must fit inside rx_region_max thickness "
            f"(owner={owner_spec.object_id}, owner_max_x={owner_max_x}, modeled_max_x={modeled_max_x})"
        )
    if modeled_min_x < owner_origin_x - 1e-9:
        raise RuntimeError(
            "type2 rx modeled stack must not extend past rx_region_max -X boundary "
            f"(owner={owner_spec.object_id}, owner_min_x={owner_origin_x}, modeled_min_x={modeled_min_x})"
        )
    available_backing_thickness_mm = modeled_min_x - owner_origin_x
    if available_backing_thickness_mm <= 0.0:
        raise RuntimeError(
            "type2 rx full backing requires positive remaining thickness "
            f"(owner={owner_spec.object_id}, owner_min_x={owner_origin_x}, modeled_min_x={modeled_min_x}, "
            f"available_backing_thickness_mm={available_backing_thickness_mm})"
        )
    ratio_total = _RX_BACKING_AIR_RATIO + _RX_BACKING_PET_PSA_RATIO + _RX_BACKING_FERRITE_RATIO
    if ratio_total <= 0.0:
        raise RuntimeError(f"type2 rx backing ratio sum must be > 0 (ratio_total={ratio_total})")
    air_thickness_mm = available_backing_thickness_mm * (_RX_BACKING_AIR_RATIO / ratio_total)
    pet_thickness_mm = available_backing_thickness_mm * (_RX_BACKING_PET_PSA_RATIO / ratio_total)
    ferrite_thickness_mm = available_backing_thickness_mm * (_RX_BACKING_FERRITE_RATIO / ratio_total)
    air_origin_x = owner_origin_x
    pet_origin_x = air_origin_x + air_thickness_mm
    ferrite_origin_x = pet_origin_x + pet_thickness_mm
    return (
        _build_labeled_solid_box(
            label="under_rx_ferrite_u0",
            origin_xyz=(ferrite_origin_x, owner_origin_y, owner_origin_z),
            size_xyz=(
                ferrite_thickness_mm,
                owner_size_y,
                owner_size_z,
            ),
        ),
        _build_labeled_solid_box(
            label="under_rx_pet_psa_u0",
            origin_xyz=(pet_origin_x, owner_origin_y, owner_origin_z),
            size_xyz=(
                pet_thickness_mm,
                owner_size_y,
                owner_size_z,
            ),
        ),
        _build_labeled_solid_box(
            label="under_rx_air_u0",
            origin_xyz=(air_origin_x, owner_origin_y, owner_origin_z),
            size_xyz=(
                air_thickness_mm,
                owner_size_y,
                owner_size_z,
            ),
        ),
    )

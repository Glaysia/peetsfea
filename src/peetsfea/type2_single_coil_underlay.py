from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

import build123d as bd

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


def ferrite_group_name_for_modeled_role(*, role: Literal["tx_single_coil", "tx_inner_single_coil", "rx_single_coil"]) -> str:
    if role == "tx_single_coil":
        return _TX_FERRITE_GROUP_NAME
    if role == "tx_inner_single_coil":
        raise RuntimeError("tx_inner_single_coil does not own ferrite/underlay grouping")
    if role == "rx_single_coil":
        return _RX_FERRITE_GROUP_NAME
    raise RuntimeError(f"unsupported ferrite grouping role: {role}")


def _build_labeled_solid_box(*, label: str, origin_xyz: Point3, size_xyz: Point3) -> bd.Shape:
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


def _build_labeled_group(*, label: str, children: tuple[bd.Shape, ...]) -> bd.Shape:
    if len(label) > _UNDERLAY_MAX_LABEL_LENGTH:
        raise RuntimeError(
            "type2 underlay group label must be <= 32 chars "
            f"(label={label}, length={len(label)})"
        )
    if len(children) == 0:
        raise RuntimeError(f"type2 underlay group must contain children (label={label})")
    group = bd.Compound(children=children, label=label)
    return cast(bd.Shape, group)


def single_coil_expected_ferrite_groups(
    *,
    role: Literal["tx_single_coil", "tx_inner_single_coil", "rx_single_coil"],
    underlay_scene_children: tuple[bd.Shape, ...],
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
    base_scene_children: tuple[bd.Shape, ...],
    underlay_scene_children: tuple[bd.Shape, ...],
    expected_exported_body_groups: tuple[ExportedBodyGroup, ...],
) -> tuple[bd.Shape, ...]:
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


def build_tx_wall_parallel_scene_shapes(descriptor: _TxUnderlayPlacementDescriptor) -> tuple[bd.Shape, ...]:
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
) -> tuple[bd.Shape, ...]:
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

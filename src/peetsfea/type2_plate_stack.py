from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

import build123d as bd

from peetsfea.type2_step_ledger import ModeledObjectSceneData
from peetsfea.type2_step_spec import ModeledPlateStackRole
from peetsfea.type2_step_spec import ModeledPlateStackSpec
from peetsfea.type2_step_spec import NonModelBoxSpec

_FERRITE_THICKNESS_MM = 0.20
_PET_PSA_THICKNESS_MM = 0.15
_AIR_THICKNESS_MM = 0.02
_MAX_LABEL_LENGTH = 32
_EXPECTED_FERRITE_SET_COUNT = 10


@dataclass(frozen=True)
class _PlateStackRoleConfig:
    role: ModeledPlateStackRole
    prefix: Literal["tx", "rx"]
    modeled_plane: Literal["XY", "YZ"]
    placement_owner_id: str
    owner_plane: Literal["XY", "YZ"]
    thickness_axis_index: Literal[0, 2]


_ROLE_CONFIGS: dict[ModeledPlateStackRole, _PlateStackRoleConfig] = {
    "tx_plate_stack": _PlateStackRoleConfig(
        role="tx_plate_stack",
        prefix="tx",
        modeled_plane="YZ",
        placement_owner_id="tx_region",
        owner_plane="YZ",
        thickness_axis_index=0,
    ),
    "rx_plate_stack": _PlateStackRoleConfig(
        role="rx_plate_stack",
        prefix="rx",
        modeled_plane="YZ",
        placement_owner_id="rx_region_max",
        owner_plane="YZ",
        thickness_axis_index=0,
    ),
}


def _role_config(role: ModeledPlateStackRole) -> _PlateStackRoleConfig:
    if role not in _ROLE_CONFIGS:
        raise RuntimeError(f"unsupported type2 plate-stack role: {role}")
    return _ROLE_CONFIGS[role]


def expected_plate_stack_body_names(*, role: ModeledPlateStackRole, ferrite_set_count: int) -> tuple[str, ...]:
    role_config = _role_config(role)
    prefix = role_config.prefix
    body_names = [f"{prefix}_copper_wall", f"{prefix}_pcb_wall"]
    body_names.extend(f"{prefix}_stack_ferrite_u{index}" for index in range(ferrite_set_count))
    body_names.extend(f"{prefix}_stack_pet_psa_u{index}" for index in range(ferrite_set_count))
    body_names.extend(f"{prefix}_stack_air_u{index}" for index in range(ferrite_set_count))
    body_names.extend((f"{prefix}_pcb_coil", f"{prefix}_copper_coil"))
    return tuple(body_names)


def total_plate_stack_thickness_mm(*, spec: ModeledPlateStackSpec) -> float:
    return (2.0 * spec.pcb_total_thickness_mm) + (
        float(spec.ferrite_set_count)
        * (_FERRITE_THICKNESS_MM + _PET_PSA_THICKNESS_MM + _AIR_THICKNESS_MM)
    )


def build_plate_stack_scene_data(
    spec: ModeledPlateStackSpec,
    *,
    owner_spec: NonModelBoxSpec,
) -> tuple[tuple[bd.Shape, ...], ModeledObjectSceneData]:
    role_config = _role_config(spec.role)
    if owner_spec.object_id != role_config.placement_owner_id:
        raise RuntimeError(
            "type2 plate stack requires fixed placement owner "
            f"(role={spec.role}, expected_owner={role_config.placement_owner_id}, actual={owner_spec.object_id})"
        )
    if owner_spec.plane != role_config.owner_plane:
        raise RuntimeError(
            "type2 plate stack requires fixed owner plane "
            f"(role={spec.role}, owner={owner_spec.object_id}, expected_plane={role_config.owner_plane}, actual={owner_spec.plane})"
        )
    if spec.ferrite_set_count != _EXPECTED_FERRITE_SET_COUNT:
        raise ValueError(
            f"{spec.role}.ferrite_set_count must be {_EXPECTED_FERRITE_SET_COUNT} for the active literal-set contract "
            f"(actual={spec.ferrite_set_count})"
        )
    if spec.pcb_total_thickness_mm <= spec.copper_thickness_mm:
        raise ValueError(
            f"{spec.role}.pcb_total_thickness_mm must be > copper_thickness_mm "
            f"(pcb_total_thickness_mm={spec.pcb_total_thickness_mm}, copper_thickness_mm={spec.copper_thickness_mm})"
        )

    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if role_config.modeled_plane == "YZ":
        if owner_size_y <= 0.0 or owner_size_z <= 0.0:
            raise RuntimeError(
                "type2 plate stack owner footprint must be positive "
                f"(role={spec.role}, owner={owner_spec.object_id}, size={owner_spec.size_xyz})"
            )
    else:
        if owner_size_x <= 0.0 or owner_size_y <= 0.0:
            raise RuntimeError(
                "type2 plate stack owner footprint must be positive "
                f"(role={spec.role}, owner={owner_spec.object_id}, size={owner_spec.size_xyz})"
            )

    total_thickness_mm = total_plate_stack_thickness_mm(spec=spec)
    owner_thickness_budget_mm = owner_size_z if role_config.thickness_axis_index == 2 else owner_size_x
    if total_thickness_mm > owner_thickness_budget_mm:
        if spec.role == "tx_plate_stack":
            raise RuntimeError(
                "type2 tx plate stack must fit inside tx_region thickness "
                f"(owner_size_x={owner_size_x}, total_thickness_mm={total_thickness_mm})"
            )
        raise RuntimeError(
            "type2 rx plate stack must fit inside rx_region_max thickness "
            f"(owner_size_x={owner_size_x}, total_thickness_mm={total_thickness_mm})"
        )

    pcb_epoxy_thickness_mm = spec.pcb_total_thickness_mm - spec.copper_thickness_mm
    current_position_mm = owner_origin_z if role_config.thickness_axis_index == 2 else owner_origin_x
    body_specs: list[tuple[str, tuple[float, float, float], tuple[float, float, float]]] = []

    body_specs.append(
        _body_spec(
            label=f"{role_config.prefix}_copper_wall",
            owner_spec=owner_spec,
            layer_origin_mm=current_position_mm,
            layer_thickness_mm=spec.copper_thickness_mm,
            thickness_axis_index=role_config.thickness_axis_index,
        )
    )
    wall_copper_origin_mm = current_position_mm
    current_position_mm += spec.copper_thickness_mm

    body_specs.append(
        _body_spec(
            label=f"{role_config.prefix}_pcb_wall",
            owner_spec=owner_spec,
            layer_origin_mm=current_position_mm,
            layer_thickness_mm=pcb_epoxy_thickness_mm,
            thickness_axis_index=role_config.thickness_axis_index,
        )
    )
    wall_pcb_origin_mm = current_position_mm
    current_position_mm += pcb_epoxy_thickness_mm

    for index in range(spec.ferrite_set_count):
        body_specs.append(
            _body_spec(
                label=f"{role_config.prefix}_stack_ferrite_u{index}",
                owner_spec=owner_spec,
                layer_origin_mm=current_position_mm,
                layer_thickness_mm=_FERRITE_THICKNESS_MM,
                thickness_axis_index=role_config.thickness_axis_index,
            )
        )
        current_position_mm += _FERRITE_THICKNESS_MM

    for index in range(spec.ferrite_set_count):
        body_specs.append(
            _body_spec(
                label=f"{role_config.prefix}_stack_pet_psa_u{index}",
                owner_spec=owner_spec,
                layer_origin_mm=current_position_mm,
                layer_thickness_mm=_PET_PSA_THICKNESS_MM,
                thickness_axis_index=role_config.thickness_axis_index,
            )
        )
        current_position_mm += _PET_PSA_THICKNESS_MM

    for index in range(spec.ferrite_set_count):
        body_specs.append(
            _body_spec(
                label=f"{role_config.prefix}_stack_air_u{index}",
                owner_spec=owner_spec,
                layer_origin_mm=current_position_mm,
                layer_thickness_mm=_AIR_THICKNESS_MM,
                thickness_axis_index=role_config.thickness_axis_index,
            )
        )
        current_position_mm += _AIR_THICKNESS_MM

    body_specs.append(
        _body_spec(
            label=f"{role_config.prefix}_pcb_coil",
            owner_spec=owner_spec,
            layer_origin_mm=current_position_mm,
            layer_thickness_mm=pcb_epoxy_thickness_mm,
            thickness_axis_index=role_config.thickness_axis_index,
        )
    )
    coil_pcb_origin_mm = current_position_mm
    current_position_mm += pcb_epoxy_thickness_mm

    body_specs.append(
        _body_spec(
            label=f"{role_config.prefix}_copper_coil",
            owner_spec=owner_spec,
            layer_origin_mm=current_position_mm,
            layer_thickness_mm=spec.copper_thickness_mm,
            thickness_axis_index=role_config.thickness_axis_index,
        )
    )
    coil_copper_origin_mm = current_position_mm
    current_position_mm += spec.copper_thickness_mm

    expected_body_names = expected_plate_stack_body_names(role=spec.role, ferrite_set_count=spec.ferrite_set_count)
    actual_body_names = tuple(label for label, _origin_xyz, _size_xyz in body_specs)
    if actual_body_names != expected_body_names:
        raise RuntimeError(
            "type2 plate stack body order drifted from expected contract "
            f"(role={spec.role}, expected={expected_body_names}, actual={actual_body_names})"
        )

    if role_config.thickness_axis_index == 2:
        outer_bounds_max_xyz = (
            owner_origin_x + owner_size_x,
            owner_origin_y + owner_size_y,
            owner_origin_z + total_thickness_mm,
        )
        outer_bounds_size_xyz = (owner_size_x, owner_size_y, total_thickness_mm)
    else:
        outer_bounds_max_xyz = (
            owner_origin_x + total_thickness_mm,
            owner_origin_y + owner_size_y,
            owner_origin_z + owner_size_z,
        )
        outer_bounds_size_xyz = (total_thickness_mm, owner_size_y, owner_size_z)

    shapes = tuple(
        _build_labeled_solid_box(label=label, origin_xyz=origin_xyz, size_xyz=size_xyz)
        for label, origin_xyz, size_xyz in body_specs
    )
    return (
        shapes,
        {
            "object_id": spec.object_id,
            "role": spec.role,
            "plane": role_config.modeled_plane,
            "placement_owner_id": role_config.placement_owner_id,
            "material": spec.material,
            "model_state": True,
            "expected_exported_body_names": expected_body_names,
            "expected_exported_body_count": len(expected_body_names),
            "canonical_coordinates": {
                "frame_origin_xyz": owner_spec.origin_xyz,
                "outer_bounds_min_xyz": owner_spec.origin_xyz,
                "outer_bounds_max_xyz": outer_bounds_max_xyz,
                "outer_bounds_size_xyz": outer_bounds_size_xyz,
                "pcb_layer_z_positions_mm": (wall_pcb_origin_mm, coil_pcb_origin_mm),
                "copper_layer_z_positions_mm": (wall_copper_origin_mm, coil_copper_origin_mm),
            },
            "terminal_metadata": {"kind": "none"},
        },
    )


def _body_spec(
    *,
    label: str,
    owner_spec: NonModelBoxSpec,
    layer_origin_mm: float,
    layer_thickness_mm: float,
    thickness_axis_index: Literal[0, 2],
) -> tuple[str, tuple[float, float, float], tuple[float, float, float]]:
    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if thickness_axis_index == 2:
        return (
            label,
            (owner_origin_x, owner_origin_y, layer_origin_mm),
            (owner_size_x, owner_size_y, layer_thickness_mm),
        )
    if thickness_axis_index == 0:
        return (
            label,
            (layer_origin_mm, owner_origin_y, owner_origin_z),
            (layer_thickness_mm, owner_size_y, owner_size_z),
        )
    raise RuntimeError(f"unsupported plate-stack thickness axis index: {thickness_axis_index}")


def _build_labeled_solid_box(
    *,
    label: str,
    origin_xyz: tuple[float, float, float],
    size_xyz: tuple[float, float, float],
) -> bd.Shape:
    if len(label) > _MAX_LABEL_LENGTH:
        raise RuntimeError(
            "type2 plate stack body label must be <= 32 chars "
            f"(label={label}, length={len(label)})"
        )
    size_x, size_y, size_z = size_xyz
    if size_x <= 0.0 or size_y <= 0.0 or size_z <= 0.0:
        raise RuntimeError(
            "type2 plate stack body size must be positive "
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
            "type2 plate stack body must contain exactly one solid "
            f"(label={label}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = label
    return cast(bd.Shape, solid)


__all__ = [
    "build_plate_stack_scene_data",
    "expected_plate_stack_body_names",
    "total_plate_stack_thickness_mm",
]

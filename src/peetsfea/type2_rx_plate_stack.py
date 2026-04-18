from __future__ import annotations

from typing import cast

import build123d as bd

from peetsfea.type2_step_ledger import ModeledObjectSceneData
from peetsfea.type2_step_spec import ModeledRxPlateStackSpec
from peetsfea.type2_step_spec import NonModelBoxSpec

_FERRITE_THICKNESS_MM = 0.20
_PET_PSA_THICKNESS_MM = 0.15
_AIR_THICKNESS_MM = 0.02
_MAX_LABEL_LENGTH = 32
_EXPECTED_FERRITE_SET_COUNT = 10
_PLACEMENT_OWNER_ID = "rx_region_max"


def expected_rx_plate_stack_body_names(*, ferrite_set_count: int) -> tuple[str, ...]:
    body_names = ["rx_copper_wall", "rx_pcb_wall"]
    body_names.extend(f"rx_stack_ferrite_u{index}" for index in range(ferrite_set_count))
    body_names.extend(f"rx_stack_pet_psa_u{index}" for index in range(ferrite_set_count))
    body_names.extend(f"rx_stack_air_u{index}" for index in range(ferrite_set_count))
    body_names.extend(("rx_pcb_coil", "rx_copper_coil"))
    return tuple(body_names)


def total_rx_plate_stack_thickness_mm(*, spec: ModeledRxPlateStackSpec) -> float:
    return (2.0 * spec.pcb_total_thickness_mm) + (
        float(spec.ferrite_set_count)
        * (_FERRITE_THICKNESS_MM + _PET_PSA_THICKNESS_MM + _AIR_THICKNESS_MM)
    )


def build_rx_plate_stack_scene_data(
    spec: ModeledRxPlateStackSpec,
    *,
    owner_spec: NonModelBoxSpec,
) -> tuple[tuple[bd.Shape, ...], ModeledObjectSceneData]:
    if owner_spec.object_id != _PLACEMENT_OWNER_ID:
        raise RuntimeError(
            "type2 rx plate stack requires rx_region_max placement owner "
            f"(actual={owner_spec.object_id})"
        )
    if owner_spec.plane != "YZ":
        raise RuntimeError(
            "type2 rx plate stack requires YZ owner plane "
            f"(owner={owner_spec.object_id}, plane={owner_spec.plane})"
        )
    if spec.ferrite_set_count != _EXPECTED_FERRITE_SET_COUNT:
        raise ValueError(
            "rx_plate_stack.ferrite_set_count must be 10 for the active literal-set contract "
            f"(actual={spec.ferrite_set_count})"
        )
    if spec.pcb_total_thickness_mm <= spec.copper_thickness_mm:
        raise ValueError(
            "rx_plate_stack.pcb_total_thickness_mm must be > copper_thickness_mm "
            f"(pcb_total_thickness_mm={spec.pcb_total_thickness_mm}, copper_thickness_mm={spec.copper_thickness_mm})"
        )
    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if owner_size_y <= 0.0 or owner_size_z <= 0.0:
        raise RuntimeError(
            "type2 rx plate stack owner footprint must be positive "
            f"(owner={owner_spec.object_id}, size={owner_spec.size_xyz})"
        )
    total_thickness_mm = total_rx_plate_stack_thickness_mm(spec=spec)
    if total_thickness_mm > owner_size_x:
        raise RuntimeError(
            "type2 rx plate stack must fit inside rx_region_max thickness "
            f"(owner_size_x={owner_size_x}, total_thickness_mm={total_thickness_mm})"
        )
    pcb_epoxy_thickness_mm = spec.pcb_total_thickness_mm - spec.copper_thickness_mm
    current_x = owner_origin_x
    body_specs: list[tuple[str, tuple[float, float, float], tuple[float, float, float]]] = []
    body_specs.append(
        (
            "rx_copper_wall",
            (current_x, owner_origin_y, owner_origin_z),
            (spec.copper_thickness_mm, owner_size_y, owner_size_z),
        )
    )
    wall_copper_origin_x = current_x
    current_x += spec.copper_thickness_mm
    body_specs.append(
        (
            "rx_pcb_wall",
            (current_x, owner_origin_y, owner_origin_z),
            (pcb_epoxy_thickness_mm, owner_size_y, owner_size_z),
        )
    )
    wall_pcb_origin_x = current_x
    current_x += pcb_epoxy_thickness_mm
    for index in range(spec.ferrite_set_count):
        body_specs.append(
            (
                f"rx_stack_ferrite_u{index}",
                (current_x, owner_origin_y, owner_origin_z),
                (_FERRITE_THICKNESS_MM, owner_size_y, owner_size_z),
            )
        )
        current_x += _FERRITE_THICKNESS_MM
    for index in range(spec.ferrite_set_count):
        body_specs.append(
            (
                f"rx_stack_pet_psa_u{index}",
                (current_x, owner_origin_y, owner_origin_z),
                (_PET_PSA_THICKNESS_MM, owner_size_y, owner_size_z),
            )
        )
        current_x += _PET_PSA_THICKNESS_MM
    for index in range(spec.ferrite_set_count):
        body_specs.append(
            (
                f"rx_stack_air_u{index}",
                (current_x, owner_origin_y, owner_origin_z),
                (_AIR_THICKNESS_MM, owner_size_y, owner_size_z),
            )
        )
        current_x += _AIR_THICKNESS_MM
    body_specs.append(
        (
            "rx_pcb_coil",
            (current_x, owner_origin_y, owner_origin_z),
            (pcb_epoxy_thickness_mm, owner_size_y, owner_size_z),
        )
    )
    coil_pcb_origin_x = current_x
    current_x += pcb_epoxy_thickness_mm
    body_specs.append(
        (
            "rx_copper_coil",
            (current_x, owner_origin_y, owner_origin_z),
            (spec.copper_thickness_mm, owner_size_y, owner_size_z),
        )
    )
    coil_copper_origin_x = current_x
    current_x += spec.copper_thickness_mm
    expected_body_names = expected_rx_plate_stack_body_names(ferrite_set_count=spec.ferrite_set_count)
    actual_body_names = tuple(label for label, _origin_xyz, _size_xyz in body_specs)
    if actual_body_names != expected_body_names:
        raise RuntimeError(
            "type2 rx plate stack body order drifted from expected contract "
            f"(expected={expected_body_names}, actual={actual_body_names})"
        )
    shapes = tuple(
        _build_labeled_solid_box(label=label, origin_xyz=origin_xyz, size_xyz=size_xyz)
        for label, origin_xyz, size_xyz in body_specs
    )
    return (
        shapes,
        {
            "object_id": spec.object_id,
            "role": "rx_plate_stack",
            "plane": "YZ",
            "placement_owner_id": _PLACEMENT_OWNER_ID,
            "material": spec.material,
            "model_state": True,
            "expected_exported_body_names": expected_body_names,
            "expected_exported_body_count": len(expected_body_names),
            "canonical_coordinates": {
                "frame_origin_xyz": owner_spec.origin_xyz,
                "outer_bounds_min_xyz": owner_spec.origin_xyz,
                "outer_bounds_max_xyz": (
                    owner_origin_x + total_thickness_mm,
                    owner_origin_y + owner_size_y,
                    owner_origin_z + owner_size_z,
                ),
                "outer_bounds_size_xyz": (total_thickness_mm, owner_size_y, owner_size_z),
                "pcb_layer_z_positions_mm": (wall_pcb_origin_x, coil_pcb_origin_x),
                "copper_layer_z_positions_mm": (wall_copper_origin_x, coil_copper_origin_x),
            },
            "terminal_metadata": {"kind": "none"},
        },
    )


def _build_labeled_solid_box(
    *,
    label: str,
    origin_xyz: tuple[float, float, float],
    size_xyz: tuple[float, float, float],
) -> bd.Shape:
    if len(label) > _MAX_LABEL_LENGTH:
        raise RuntimeError(
            "type2 rx plate stack body label must be <= 32 chars "
            f"(label={label}, length={len(label)})"
        )
    size_x, size_y, size_z = size_xyz
    if size_x <= 0.0 or size_y <= 0.0 or size_z <= 0.0:
        raise RuntimeError(
            "type2 rx plate stack body size must be positive "
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
            "type2 rx plate stack body must contain exactly one solid "
            f"(label={label}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = label
    return cast(bd.Shape, solid)


__all__ = [
    "build_rx_plate_stack_scene_data",
    "expected_rx_plate_stack_body_names",
    "total_rx_plate_stack_thickness_mm",
]

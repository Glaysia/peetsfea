from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

import build123d as bd

from peetsfea.type2_step_ledger import ExportedBodyGroup
from peetsfea.type2_step_ledger import ModeledObjectSceneData
from peetsfea.type2_step_spec import ModeledPlateStackRole
from peetsfea.type2_step_spec import ModeledPlateStackSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import resolve_modeled_plate_stack_metal_fill_factor
from peetsfea.type2_step_spec import resolve_modeled_plate_stack_turn_count

_FERRITE_THICKNESS_MM = 0.20
_PET_PSA_THICKNESS_MM = 0.15
_AIR_THICKNESS_MM = 0.02
_MAX_LABEL_LENGTH = 32
_EXPECTED_FERRITE_SET_COUNT = 10
_PLATE_STACK_STUB_LENGTH_MM = 5.0
_PLATE_STACK_TERMINAL_METADATA_KIND = "stub_port"
_GEOMETRY_EPSILON_MM = 1e-9


@dataclass(frozen=True)
class _PlateStackRoleConfig:
    role: ModeledPlateStackRole
    prefix: Literal["tx", "rx"]
    modeled_plane: Literal["XY", "YZ"]
    placement_owner_id: str
    owner_plane: Literal["XY", "YZ"]
    thickness_axis_index: Literal[0, 2]


@dataclass(frozen=True)
class _BridgeEdgeWindow:
    y_edge: Literal["min", "max"]
    z_min_mm: float
    z_max_mm: float


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
_FERRITE_GROUP_NAMES: dict[Literal["tx", "rx"], str] = {
    "tx": "g_ferrite_tx",
    "rx": "g_ferrite_rx",
}


def _role_config(role: ModeledPlateStackRole) -> _PlateStackRoleConfig:
    if role not in _ROLE_CONFIGS:
        raise RuntimeError(f"unsupported type2 plate-stack role: {role}")
    return _ROLE_CONFIGS[role]


def _ferrite_group_name_for_prefix(*, prefix: Literal["tx", "rx"]) -> str:
    if prefix not in _FERRITE_GROUP_NAMES:
        raise RuntimeError(f"unsupported ferrite group prefix: {prefix}")
    return _FERRITE_GROUP_NAMES[prefix]


def expected_plate_stack_body_names(
    *,
    role: ModeledPlateStackRole,
    ferrite_set_count: int,
    turn_count: int,
    pcb_total_thickness_mm: float,
) -> tuple[str, ...]:
    role_config = _role_config(role)
    prefix = role_config.prefix
    if turn_count < 2:
        raise ValueError(f"{role}.turn_count must be >= 2 (actual={turn_count})")
    if pcb_total_thickness_mm <= 0.0:
        raise ValueError(f"{role}.pcb_total_thickness_mm must be > 0 (actual={pcb_total_thickness_mm})")
    body_names = [f"{prefix}_copper_wall_t{index}" for index in range(turn_count)]
    body_names.append(f"{prefix}_pcb_wall")
    for index in range(ferrite_set_count):
        body_names.extend(
            (
                f"{prefix}_stack_pet_psa_u{index}",
                f"{prefix}_stack_ferrite_u{index}",
                f"{prefix}_stack_air_u{index}",
            )
        )
    body_names.append(f"{prefix}_pcb_coil")
    body_names.extend(f"{prefix}_copper_coil_t{index}" for index in range(turn_count - 1))
    body_names.extend(f"{prefix}_bridge_s{index}" for index in range((2 * turn_count) - 2))
    body_names.extend((f"{prefix}_stub_in", f"{prefix}_stub_out"))
    return tuple(body_names)


def total_plate_stack_thickness_mm(*, spec: ModeledPlateStackSpec) -> float:
    return (2.0 * spec.pcb_total_thickness_mm) + (
        float(spec.ferrite_set_count)
        * (_FERRITE_THICKNESS_MM + _PET_PSA_THICKNESS_MM + _AIR_THICKNESS_MM)
    )


def expected_plate_stack_body_groups(
    *,
    role: ModeledPlateStackRole,
    ferrite_set_count: int,
) -> tuple[ExportedBodyGroup, ...]:
    role_config = _role_config(role)
    if ferrite_set_count < 1:
        raise ValueError(f"{role}.ferrite_set_count must be >= 1 for ferrite grouping (actual={ferrite_set_count})")
    ferrite_member_body_names: list[str] = []
    for index in range(ferrite_set_count):
        ferrite_member_body_names.extend(
            (
                f"{role_config.prefix}_stack_pet_psa_u{index}",
                f"{role_config.prefix}_stack_ferrite_u{index}",
                f"{role_config.prefix}_stack_air_u{index}",
            )
        )
    return (
        {
            "group_name": _ferrite_group_name_for_prefix(prefix=role_config.prefix),
            "member_body_names": tuple(ferrite_member_body_names),
        },
    )


def build_plate_stack_scene_data(
    spec: ModeledPlateStackSpec,
    *,
    owner_spec: NonModelBoxSpec,
    seed: int,
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
    if role_config.modeled_plane != "YZ" or role_config.thickness_axis_index != 0:
        raise RuntimeError(
            "type2 striped plate stack currently requires YZ modeled plane and X thickness axis "
            f"(role={spec.role}, modeled_plane={role_config.modeled_plane}, thickness_axis_index={role_config.thickness_axis_index})"
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
    if spec.copper_thickness_mm <= 0.0:
        raise ValueError(f"{spec.role}.copper_thickness_mm must be > 0 (actual={spec.copper_thickness_mm})")

    realized_turn_count = resolve_modeled_plate_stack_turn_count(spec, seed=seed)
    realized_metal_fill_factor = resolve_modeled_plate_stack_metal_fill_factor(spec, seed=seed)
    realized_coil_turn_count = realized_turn_count - 1

    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if owner_size_y <= 0.0 or owner_size_z <= 0.0:
        raise RuntimeError(
            "type2 plate stack owner footprint must be positive "
            f"(role={spec.role}, owner={owner_spec.object_id}, size={owner_spec.size_xyz})"
        )

    total_thickness_mm = total_plate_stack_thickness_mm(spec=spec)
    if total_thickness_mm > owner_size_x:
        if spec.role == "tx_plate_stack":
            raise RuntimeError(
                "type2 tx plate stack must fit inside tx_region thickness "
                f"(owner_size_x={owner_size_x}, total_thickness_mm={total_thickness_mm})"
            )
        raise RuntimeError(
            "type2 rx plate stack must fit inside rx_region_max thickness "
            f"(owner_size_x={owner_size_x}, total_thickness_mm={total_thickness_mm})"
        )
    active_conductor_size_z = owner_size_z
    if active_conductor_size_z <= 0.0:
        raise RuntimeError(
            f"type2 {spec.role} active conductor height must be > 0 "
            f"(owner_size_z={owner_size_z})"
        )

    conductor_origin_z = owner_origin_z
    pitch_z = active_conductor_size_z / float(realized_turn_count)
    trace_height_z = pitch_z * realized_metal_fill_factor
    bridge_span_z = (pitch_z / 2.0) + trace_height_z

    pcb_epoxy_thickness_mm = spec.pcb_total_thickness_mm - spec.copper_thickness_mm
    current_position_mm = owner_origin_x
    body_specs: list[tuple[str, tuple[float, float, float], tuple[float, float, float]]] = []
    bridge_clearance_labels: set[str] = set()

    wall_stripe_z_origins = tuple(
        conductor_origin_z + (pitch_z * float(index))
        for index in range(realized_turn_count)
    )
    coil_stripe_z_origins = tuple(
        conductor_origin_z + (pitch_z / 2.0) + (pitch_z * float(index))
        for index in range(realized_coil_turn_count)
    )

    for index, stripe_origin_z in enumerate(wall_stripe_z_origins):
        body_specs.append(
            _yz_body_spec(
                label=f"{role_config.prefix}_copper_wall_t{index}",
                owner_spec=owner_spec,
                layer_origin_x_mm=current_position_mm,
                layer_thickness_x_mm=spec.copper_thickness_mm,
                body_origin_z_mm=stripe_origin_z,
                body_size_z_mm=trace_height_z,
            )
        )
    wall_copper_origin_mm = current_position_mm
    current_position_mm += spec.copper_thickness_mm

    wall_pcb_label = f"{role_config.prefix}_pcb_wall"
    body_specs.append(
        _yz_body_spec(
            label=wall_pcb_label,
            owner_spec=owner_spec,
            layer_origin_x_mm=current_position_mm,
            layer_thickness_x_mm=pcb_epoxy_thickness_mm,
            body_origin_z_mm=conductor_origin_z,
            body_size_z_mm=active_conductor_size_z,
        )
    )
    bridge_clearance_labels.add(wall_pcb_label)
    wall_pcb_origin_mm = current_position_mm
    current_position_mm += pcb_epoxy_thickness_mm

    for index in range(spec.ferrite_set_count):
        pet_label = f"{role_config.prefix}_stack_pet_psa_u{index}"
        body_specs.append(
            _yz_body_spec(
                label=pet_label,
                owner_spec=owner_spec,
                layer_origin_x_mm=current_position_mm,
                layer_thickness_x_mm=_PET_PSA_THICKNESS_MM,
                body_origin_z_mm=owner_origin_z,
                body_size_z_mm=owner_size_z,
            )
        )
        bridge_clearance_labels.add(pet_label)
        current_position_mm += _PET_PSA_THICKNESS_MM
        ferrite_label = f"{role_config.prefix}_stack_ferrite_u{index}"
        body_specs.append(
            _yz_body_spec(
                label=ferrite_label,
                owner_spec=owner_spec,
                layer_origin_x_mm=current_position_mm,
                layer_thickness_x_mm=_FERRITE_THICKNESS_MM,
                body_origin_z_mm=owner_origin_z,
                body_size_z_mm=owner_size_z,
            )
        )
        bridge_clearance_labels.add(ferrite_label)
        current_position_mm += _FERRITE_THICKNESS_MM
        air_label = f"{role_config.prefix}_stack_air_u{index}"
        body_specs.append(
            _yz_body_spec(
                label=air_label,
                owner_spec=owner_spec,
                layer_origin_x_mm=current_position_mm,
                layer_thickness_x_mm=_AIR_THICKNESS_MM,
                body_origin_z_mm=owner_origin_z,
                body_size_z_mm=owner_size_z,
            )
        )
        bridge_clearance_labels.add(air_label)
        current_position_mm += _AIR_THICKNESS_MM

    coil_pcb_label = f"{role_config.prefix}_pcb_coil"
    body_specs.append(
        _yz_body_spec(
            label=coil_pcb_label,
            owner_spec=owner_spec,
            layer_origin_x_mm=current_position_mm,
            layer_thickness_x_mm=pcb_epoxy_thickness_mm,
            body_origin_z_mm=conductor_origin_z,
            body_size_z_mm=active_conductor_size_z,
        )
    )
    bridge_clearance_labels.add(coil_pcb_label)
    coil_pcb_origin_mm = current_position_mm
    current_position_mm += pcb_epoxy_thickness_mm

    for index, stripe_origin_z in enumerate(coil_stripe_z_origins):
        body_specs.append(
            _yz_body_spec(
                label=f"{role_config.prefix}_copper_coil_t{index}",
                owner_spec=owner_spec,
                layer_origin_x_mm=current_position_mm,
                layer_thickness_x_mm=spec.copper_thickness_mm,
                body_origin_z_mm=stripe_origin_z,
                body_size_z_mm=trace_height_z,
            )
        )
    coil_copper_origin_mm = current_position_mm
    current_position_mm += spec.copper_thickness_mm

    bridge_origin_x_mm = wall_copper_origin_mm + spec.copper_thickness_mm
    bridge_size_x_mm = coil_copper_origin_mm - bridge_origin_x_mm
    if bridge_size_x_mm <= 0.0:
        raise RuntimeError(
            f"type2 {spec.role} bridge X span must be > 0 "
            f"(bridge_size_x_mm={bridge_size_x_mm})"
        )
    bridge_windows: list[_BridgeEdgeWindow] = []
    for index in range((2 * realized_turn_count) - 2):
        stripe_origin_z = (
            wall_stripe_z_origins[index // 2]
            if index % 2 == 0
            else coil_stripe_z_origins[index // 2]
        )
        bridge_y_edge: Literal["min", "max"] = "max" if index % 2 == 0 else "min"
        bridge_origin_y_mm = (
            owner_origin_y + owner_size_y - spec.copper_thickness_mm if bridge_y_edge == "max" else owner_origin_y
        )
        bridge_z_max_mm = stripe_origin_z + bridge_span_z
        bridge_windows.append(
            _BridgeEdgeWindow(
                y_edge=bridge_y_edge,
                z_min_mm=stripe_origin_z,
                z_max_mm=bridge_z_max_mm,
            )
        )
        body_specs.append(
            (
                f"{role_config.prefix}_bridge_s{index}",
                (bridge_origin_x_mm, bridge_origin_y_mm, stripe_origin_z),
                (bridge_size_x_mm, spec.copper_thickness_mm, bridge_span_z),
            )
        )
    if len(bridge_windows) != (2 * realized_turn_count) - 2:
        raise RuntimeError(
            "type2 plate stack bridge window contract drifted "
            f"(role={spec.role}, expected={(2 * realized_turn_count) - 2}, actual={len(bridge_windows)})"
        )

    input_stub_spec = _stub_body_spec(
        label=f"{role_config.prefix}_stub_in",
        owner_spec=owner_spec,
        layer_origin_x_mm=wall_copper_origin_mm,
        layer_thickness_x_mm=spec.copper_thickness_mm,
        stub_origin_z_mm=wall_stripe_z_origins[0],
        stub_size_z_mm=trace_height_z,
    )
    output_stub_spec = _stub_body_spec(
        label=f"{role_config.prefix}_stub_out",
        owner_spec=owner_spec,
        layer_origin_x_mm=wall_copper_origin_mm,
        layer_thickness_x_mm=spec.copper_thickness_mm,
        stub_origin_z_mm=wall_stripe_z_origins[-1],
        stub_size_z_mm=trace_height_z,
    )
    body_specs.extend((input_stub_spec, output_stub_spec))

    expected_body_names = expected_plate_stack_body_names(
        role=spec.role,
        ferrite_set_count=spec.ferrite_set_count,
        turn_count=realized_turn_count,
        pcb_total_thickness_mm=spec.pcb_total_thickness_mm,
    )
    actual_body_names = tuple(label for label, _origin_xyz, _size_xyz in body_specs)
    if actual_body_names != expected_body_names:
        raise RuntimeError(
            "type2 plate stack body order drifted from expected contract "
            f"(role={spec.role}, expected={expected_body_names}, actual={actual_body_names})"
        )
    expected_body_groups = expected_plate_stack_body_groups(
        role=spec.role,
        ferrite_set_count=spec.ferrite_set_count,
    )

    outer_bounds_max_xyz = (
        owner_origin_x + total_thickness_mm,
        owner_origin_y + owner_size_y + _PLATE_STACK_STUB_LENGTH_MM,
        owner_origin_z + owner_size_z,
    )
    outer_bounds_size_xyz = (
        total_thickness_mm,
        owner_size_y + _PLATE_STACK_STUB_LENGTH_MM,
        owner_size_z,
    )

    flat_shapes: tuple[bd.Shape, ...] = tuple(
        _build_labeled_solid_box_with_edge_windows(
            label=label,
            origin_xyz=origin_xyz,
            size_xyz=size_xyz,
            owner_origin_y_mm=owner_origin_y,
            owner_size_y_mm=owner_size_y,
            edge_strip_width_y_mm=spec.copper_thickness_mm,
            edge_windows=tuple(bridge_windows),
        )
        if label in bridge_clearance_labels
        else _build_labeled_solid_box(label=label, origin_xyz=origin_xyz, size_xyz=size_xyz)
        for label, origin_xyz, size_xyz in body_specs
    )
    shapes_by_label = {shape.label: shape for shape in flat_shapes}
    if len(shapes_by_label) != len(flat_shapes):
        raise RuntimeError(f"type2 plate stack shape labels must be unique (role={spec.role})")
    stack_member_names = {
        member_body_name
        for group_entry in expected_body_groups
        for member_body_name in group_entry["member_body_names"]
    }
    group_by_first_member_name = {
        group_entry["member_body_names"][0]: group_entry
        for group_entry in expected_body_groups
    }
    top_level_shapes: list[bd.Shape] = []
    for label, _origin_xyz, _size_xyz in body_specs:
        if label in group_by_first_member_name:
            group_entry = group_by_first_member_name[label]
            top_level_shapes.append(
                _build_labeled_group(
                    label=group_entry["group_name"],
                    children=tuple(shapes_by_label[member_name] for member_name in group_entry["member_body_names"]),
                )
            )
            continue
        if label in stack_member_names:
            continue
        top_level_shapes.append(shapes_by_label[label])
    return (
        tuple(top_level_shapes),
        {
            "object_id": spec.object_id,
            "role": spec.role,
            "plane": role_config.modeled_plane,
            "placement_owner_id": role_config.placement_owner_id,
            "material": spec.material,
            "model_state": True,
            "expected_exported_body_names": expected_body_names,
            "expected_exported_body_count": len(expected_body_names),
            "expected_exported_body_groups": expected_body_groups,
            "canonical_coordinates": {
                "frame_origin_xyz": owner_spec.origin_xyz,
                "outer_bounds_min_xyz": owner_spec.origin_xyz,
                "outer_bounds_max_xyz": outer_bounds_max_xyz,
                "outer_bounds_size_xyz": outer_bounds_size_xyz,
                "pcb_layer_z_positions_mm": (wall_pcb_origin_mm, coil_pcb_origin_mm),
                "copper_layer_z_positions_mm": (wall_copper_origin_mm, coil_copper_origin_mm),
            },
            "terminal_metadata": _plate_stack_terminal_metadata(
                input_stub_spec=input_stub_spec,
                output_stub_spec=output_stub_spec,
            ),
        },
    )


def _plate_stack_terminal_metadata(
    *,
    input_stub_spec: tuple[str, tuple[float, float, float], tuple[float, float, float]],
    output_stub_spec: tuple[str, tuple[float, float, float], tuple[float, float, float]],
) -> dict[str, object]:
    input_label, input_origin_xyz, input_size_xyz = input_stub_spec
    output_label, output_origin_xyz, output_size_xyz = output_stub_spec
    input_origin_x, input_origin_y, input_origin_z = input_origin_xyz
    input_size_x, input_size_y, input_size_z = input_size_xyz
    output_origin_x, output_origin_y, output_origin_z = output_origin_xyz
    output_size_x, output_size_y, output_size_z = output_size_xyz
    input_tip_y = input_origin_y + input_size_y
    output_tip_y = output_origin_y + output_size_y
    if abs(input_tip_y - output_tip_y) > 1e-9:
        raise RuntimeError(
            "type2 plate stack stub tips must share one Y plane "
            f"(input_tip_y={input_tip_y}, output_tip_y={output_tip_y})"
        )
    input_max_x = input_origin_x + input_size_x
    output_max_x = output_origin_x + output_size_x
    if abs(input_origin_x - output_origin_x) > 1e-9 or abs(input_max_x - output_max_x) > 1e-9:
        raise RuntimeError(
            "type2 plate stack stub tips must share one X span "
            f"(input_x={(input_origin_x, input_max_x)}, output_x={(output_origin_x, output_max_x)})"
        )
    z_min = min(input_origin_z, output_origin_z)
    z_max = max(input_origin_z + input_size_z, output_origin_z + output_size_z)
    port_sheet_vertices_xyz = (
        (input_origin_x, input_tip_y, z_min),
        (input_max_x, input_tip_y, z_min),
        (input_max_x, input_tip_y, z_max),
        (input_origin_x, input_tip_y, z_max),
    )
    return {
        "kind": _PLATE_STACK_TERMINAL_METADATA_KIND,
        "input_stub_body_name": input_label,
        "output_stub_body_name": output_label,
        "start_point_plane_mm": (input_tip_y, input_origin_z + (input_size_z / 2.0)),
        "end_point_plane_mm": (output_tip_y, output_origin_z + (output_size_z / 2.0)),
        "port_sheet_vertices_xyz": port_sheet_vertices_xyz,
    }


def _yz_body_spec(
    *,
    label: str,
    owner_spec: NonModelBoxSpec,
    layer_origin_x_mm: float,
    layer_thickness_x_mm: float,
    body_origin_z_mm: float,
    body_size_z_mm: float,
) -> tuple[str, tuple[float, float, float], tuple[float, float, float]]:
    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if owner_spec.plane != "YZ":
        raise RuntimeError(f"type2 striped plate stack requires YZ owner plane (actual={owner_spec.plane})")
    if body_origin_z_mm < owner_origin_z - 1e-9:
        raise RuntimeError(
            "type2 plate stack body Z origin must stay inside owner bounds "
            f"(label={label}, body_origin_z_mm={body_origin_z_mm}, owner_origin_z={owner_origin_z})"
        )
    if (body_origin_z_mm + body_size_z_mm) > (owner_origin_z + owner_size_z + 1e-9):
        raise RuntimeError(
            "type2 plate stack body Z max must stay inside owner bounds "
            f"(label={label}, body_origin_z_mm={body_origin_z_mm}, body_size_z_mm={body_size_z_mm}, owner_max_z={owner_origin_z + owner_size_z})"
        )
    if layer_origin_x_mm < owner_origin_x - 1e-9:
        raise RuntimeError(
            "type2 plate stack body X origin must stay inside owner bounds "
            f"(label={label}, layer_origin_x_mm={layer_origin_x_mm}, owner_origin_x={owner_origin_x})"
        )
    if (layer_origin_x_mm + layer_thickness_x_mm) > (owner_origin_x + owner_size_x + 1e-9):
        raise RuntimeError(
            "type2 plate stack body X max must stay inside owner bounds "
            f"(label={label}, layer_origin_x_mm={layer_origin_x_mm}, layer_thickness_x_mm={layer_thickness_x_mm}, owner_max_x={owner_origin_x + owner_size_x})"
        )
    return (
        label,
        (layer_origin_x_mm, owner_origin_y, body_origin_z_mm),
        (layer_thickness_x_mm, owner_size_y, body_size_z_mm),
    )


def _stub_body_spec(
    *,
    label: str,
    owner_spec: NonModelBoxSpec,
    layer_origin_x_mm: float,
    layer_thickness_x_mm: float,
    stub_origin_z_mm: float,
    stub_size_z_mm: float,
) -> tuple[str, tuple[float, float, float], tuple[float, float, float]]:
    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if layer_origin_x_mm < owner_origin_x - 1e-9:
        raise RuntimeError(
            "type2 plate stack stub X origin must stay inside owner bounds "
            f"(label={label}, layer_origin_x_mm={layer_origin_x_mm}, owner_origin_x={owner_origin_x})"
        )
    if (layer_origin_x_mm + layer_thickness_x_mm) > (owner_origin_x + owner_size_x + 1e-9):
        raise RuntimeError(
            "type2 plate stack stub X max must stay inside owner bounds "
            f"(label={label}, layer_origin_x_mm={layer_origin_x_mm}, layer_thickness_x_mm={layer_thickness_x_mm}, owner_max_x={owner_origin_x + owner_size_x})"
        )
    if stub_origin_z_mm < owner_origin_z - 1e-9:
        raise RuntimeError(
            "type2 plate stack stub Z origin must stay inside owner bounds "
            f"(label={label}, stub_origin_z_mm={stub_origin_z_mm}, owner_origin_z={owner_origin_z})"
        )
    if (stub_origin_z_mm + stub_size_z_mm) > (owner_origin_z + owner_size_z + 1e-9):
        raise RuntimeError(
            "type2 plate stack stub Z max must stay inside owner bounds "
            f"(label={label}, stub_origin_z_mm={stub_origin_z_mm}, stub_size_z_mm={stub_size_z_mm}, owner_max_z={owner_origin_z + owner_size_z})"
        )
    return (
        label,
        (layer_origin_x_mm, owner_origin_y + owner_size_y, stub_origin_z_mm),
        (layer_thickness_x_mm, _PLATE_STACK_STUB_LENGTH_MM, stub_size_z_mm),
    )
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


def _build_labeled_solid_box_with_edge_windows(
    *,
    label: str,
    origin_xyz: tuple[float, float, float],
    size_xyz: tuple[float, float, float],
    owner_origin_y_mm: float,
    owner_size_y_mm: float,
    edge_strip_width_y_mm: float,
    edge_windows: tuple[_BridgeEdgeWindow, ...],
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
    if edge_strip_width_y_mm <= 0.0 or edge_strip_width_y_mm >= owner_size_y_mm:
        raise RuntimeError(
            "type2 plate stack bridge edge-strip width must be inside owner Y span "
            f"(label={label}, edge_strip_width_y_mm={edge_strip_width_y_mm}, owner_size_y_mm={owner_size_y_mm})"
        )
    if len(edge_windows) == 0:
        raise RuntimeError(f"type2 plate stack bridge windows must not be empty for notched slab (label={label})")

    origin_x, origin_y, origin_z = origin_xyz
    max_z = origin_z + size_z
    base_shape = bd.Box(
        size_x,
        size_y,
        size_z,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    ).moved(bd.Location(origin_xyz))

    owner_max_y_mm = owner_origin_y_mm + owner_size_y_mm
    notch_bodies: list[bd.Shape] = []
    for edge_window in edge_windows:
        overlap_z_min_mm = max(origin_z, edge_window.z_min_mm)
        overlap_z_max_mm = min(max_z, edge_window.z_max_mm)
        overlap_z_size_mm = overlap_z_max_mm - overlap_z_min_mm
        if overlap_z_size_mm <= _GEOMETRY_EPSILON_MM:
            continue
        notch_origin_y_mm = (
            owner_origin_y_mm if edge_window.y_edge == "min" else owner_max_y_mm - edge_strip_width_y_mm
        )
        if notch_origin_y_mm < (origin_y - _GEOMETRY_EPSILON_MM) or (
            notch_origin_y_mm + edge_strip_width_y_mm
        ) > (origin_y + size_y + _GEOMETRY_EPSILON_MM):
            raise RuntimeError(
                "type2 plate stack bridge notch Y span must stay inside slab Y bounds "
                f"(label={label}, notch_origin_y_mm={notch_origin_y_mm}, edge_strip_width_y_mm={edge_strip_width_y_mm}, slab_origin_y_mm={origin_y}, slab_size_y_mm={size_y})"
            )
        notch_bodies.append(
            cast(
                bd.Shape,
                bd.Box(
                    size_x,
                    edge_strip_width_y_mm,
                    overlap_z_size_mm,
                    align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
                ).moved(
                    bd.Location(
                        (
                            origin_x,
                            notch_origin_y_mm,
                            overlap_z_min_mm,
                        )
                    )
                ),
            )
        )
    if len(notch_bodies) == 0:
        raise RuntimeError(f"type2 plate stack notch subtraction produced no windows (label={label})")

    notched_shape: bd.Shape = cast(bd.Shape, base_shape)
    for notch_body in notch_bodies:
        notched_shape = cast(bd.Shape, notched_shape - notch_body)
    solids = tuple(notched_shape.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "type2 plate stack body must contain exactly one solid "
            f"(label={label}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = label
    return cast(bd.Shape, solid)


def _build_labeled_group(*, label: str, children: tuple[bd.Shape, ...]) -> bd.Shape:
    if len(label) > _MAX_LABEL_LENGTH:
        raise RuntimeError(
            "type2 plate stack group label must be <= 32 chars "
            f"(label={label}, length={len(label)})"
        )
    if len(children) == 0:
        raise RuntimeError(f"type2 plate stack group must contain children (label={label})")
    group = bd.Compound(children=children, label=label)
    return cast(bd.Shape, group)


__all__ = [
    "build_plate_stack_scene_data",
    "expected_plate_stack_body_groups",
    "expected_plate_stack_body_names",
    "total_plate_stack_thickness_mm",
]

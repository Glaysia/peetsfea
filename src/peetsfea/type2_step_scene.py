from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Literal, cast

import build123d as bd

from peetsfea.tx_rect_void import BoxSpec
from peetsfea.tx_rect_void import SingleCoilProfile
from peetsfea.tx_rect_void import build_tx_rect_void_box_specs
from peetsfea.tx_rect_void import build_tx_rect_void_centerline
from peetsfea.tx_rect_void import build_tx_rect_void_step_scene
from peetsfea.tx_rect_void import load_tx_rect_void_spec
from peetsfea.tx_rect_void import modeled_body_bounds_from_boxes
from peetsfea.tx_rect_void import profile_for_modeled_role
from peetsfea.tx_rect_void import realize_tx_rect_void_spec
from peetsfea.type2_step_ledger import CanonicalCoordinates
from peetsfea.type2_step_ledger import ModeledObjectSceneData
from peetsfea.type2_step_ledger import NonModelObjectLedgerEntry
from peetsfea.type2_step_ledger import NonModelSceneMemberLedgerEntry
from peetsfea.type2_step_spec import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import Point3
from peetsfea.type2_step_spec import render_tx_rect_void_toml

_NON_MODEL_VISIBLE_GROUPS: tuple[tuple[str, str, Literal["XY", "YZ", "ZX", "mixed"], tuple[str, ...]], ...] = (
    ("environment", "environment", "mixed", ("floor", "shelf", "wall", "tv")),
    ("tx_region", "tx_region", "XY", ("tx_region",)),
    ("rx_region_max", "rx_region_max", "YZ", ("rx_region_max",)),
)


def _build_non_model_shape(spec: NonModelBoxSpec) -> bd.Shape:
    size_x, size_y, size_z = spec.size_xyz
    box = bd.Box(
        size_x,
        size_y,
        size_z,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    ).moved(bd.Location(spec.origin_xyz))
    solids = tuple(box.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "non-model box-derived STEP body must contain exactly one solid "
            f"(object_id={spec.object_id}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = spec.object_id
    return solid


def _canonical_from_box(spec: NonModelBoxSpec) -> CanonicalCoordinates:
    origin_x, origin_y, origin_z = spec.origin_xyz
    size_x, size_y, size_z = spec.size_xyz
    return {
        "frame_origin_xyz": spec.origin_xyz,
        "outer_bounds_min_xyz": (origin_x, origin_y, origin_z),
        "outer_bounds_max_xyz": (origin_x + size_x, origin_y + size_y, origin_z + size_z),
        "outer_bounds_size_xyz": spec.size_xyz,
    }


def _canonical_from_non_model_specs(specs: tuple[NonModelBoxSpec, ...], *, context: str) -> CanonicalCoordinates:
    if not specs:
        raise ValueError(f"{context} canonical coordinates require at least one spec")
    min_x = min(spec.origin_xyz[0] for spec in specs)
    min_y = min(spec.origin_xyz[1] for spec in specs)
    min_z = min(spec.origin_xyz[2] for spec in specs)
    max_x = max(spec.origin_xyz[0] + spec.size_xyz[0] for spec in specs)
    max_y = max(spec.origin_xyz[1] + spec.size_xyz[1] for spec in specs)
    max_z = max(spec.origin_xyz[2] + spec.size_xyz[2] for spec in specs)
    return {
        "frame_origin_xyz": (min_x, min_y, min_z),
        "outer_bounds_min_xyz": (min_x, min_y, min_z),
        "outer_bounds_max_xyz": (max_x, max_y, max_z),
        "outer_bounds_size_xyz": (max_x - min_x, max_y - min_y, max_z - min_z),
    }


def require_non_model_object_spec(specs: tuple[NonModelBoxSpec, ...], *, object_id: str) -> NonModelBoxSpec:
    matching_specs = [spec for spec in specs if spec.object_id == object_id]
    if len(matching_specs) != 1:
        raise RuntimeError(
            f"type2 non-model registry must contain exactly one {object_id} object (actual={len(matching_specs)})"
        )
    return matching_specs[0]


def _non_model_group_specs(
    specs: tuple[NonModelBoxSpec, ...],
) -> tuple[tuple[str, str, Literal["XY", "YZ", "ZX", "mixed"], tuple[NonModelBoxSpec, ...]], ...]:
    groups: list[tuple[str, str, Literal["XY", "YZ", "ZX", "mixed"], tuple[NonModelBoxSpec, ...]]] = []
    for object_id, role, plane, member_ids in _NON_MODEL_VISIBLE_GROUPS:
        group_specs = tuple(require_non_model_object_spec(specs, object_id=member_id) for member_id in member_ids)
        groups.append((object_id, role, plane, group_specs))
    return tuple(groups)


def _build_non_model_group_shape(*, object_id: str, specs: tuple[NonModelBoxSpec, ...]) -> bd.Shape:
    if not specs:
        raise ValueError(f"non-model group shape requires at least one spec ({object_id})")
    fused_shape = _build_non_model_shape(specs[0])
    for spec in specs[1:]:
        fused_shape = fused_shape.fuse(_build_non_model_shape(spec))
    solids = tuple(fused_shape.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "non-model visible group must contain exactly one solid "
            f"(object_id={object_id}, source_count={len(specs)}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = object_id
    return solid


def _non_model_scene_members(specs: tuple[NonModelBoxSpec, ...]) -> tuple[NonModelSceneMemberLedgerEntry, ...]:
    members: list[NonModelSceneMemberLedgerEntry] = []
    for object_id, role, plane, group_specs in _non_model_group_specs(specs):
        material_names = tuple(sorted({spec.material for spec in group_specs}))
        material = material_names[0] if len(material_names) == 1 else "mixed"
        members.append(
            {
                "object_id": object_id,
                "role": role,
                "material": material,
                "model_state": False,
                "canonical_coordinates": _canonical_from_non_model_specs(
                    group_specs,
                    context=f"non-model visible group {object_id}",
                ),
                "plane": plane,
                "non_model": True,
            }
        )
    return tuple(members)


def build_non_model_scene_shapes(specs: tuple[NonModelBoxSpec, ...]) -> tuple[bd.Shape, ...]:
    return tuple(
        _build_non_model_group_shape(object_id=object_id, specs=group_specs)
        for object_id, _role, _plane, group_specs in _non_model_group_specs(specs)
    )


def build_non_model_scene_entry(specs: tuple[NonModelBoxSpec, ...]) -> NonModelObjectLedgerEntry:
    if not specs:
        raise ValueError("non-model scene entry requires at least one spec")
    material_names = tuple(sorted({spec.material for spec in specs}))
    material = material_names[0] if len(material_names) == 1 else "mixed"
    member_objects = _non_model_scene_members(specs)
    return {
        "object_id": "type2_non_model_scene",
        "role": "non_model_scene",
        "material": material,
        "model_state": False,
        "canonical_coordinates": _canonical_from_non_model_specs(specs, context="non-model scene"),
        "plane": "mixed",
        "non_model": True,
        "member_object_ids": tuple(member["object_id"] for member in member_objects),
        "member_objects": member_objects,
    }


def single_coil_placement_offset(
    *,
    owner_spec: NonModelBoxSpec,
    tx_rect_void_spec_path: Path,
    seed: int,
    profile: SingleCoilProfile,
) -> Point3:
    tx_rect_void_spec = load_tx_rect_void_spec(tx_rect_void_spec_path)
    realized = realize_tx_rect_void_spec(tx_rect_void_spec, seed=seed, profile=profile)
    local_boxes = build_tx_rect_void_box_specs(realized, profile=profile)
    local_bounds_min_xyz, _local_bounds_max_xyz, local_size_xyz = modeled_body_bounds_from_boxes(local_boxes)
    return _single_coil_placement_offset_from_local_bounds(
        owner_spec=owner_spec,
        local_bounds_min_xyz=local_bounds_min_xyz,
        local_size_xyz=local_size_xyz,
        profile=profile,
    )


def _single_coil_placement_offset_from_local_bounds(
    *,
    owner_spec: NonModelBoxSpec,
    local_bounds_min_xyz: Point3,
    local_size_xyz: Point3,
    profile: SingleCoilProfile,
) -> Point3:
    if owner_spec.plane != profile.plane:
        raise RuntimeError(
            "type2 single-coil placement owner plane must match profile plane "
            f"(owner={owner_spec.object_id}, owner_plane={owner_spec.plane}, profile_plane={profile.plane})"
        )
    world_size_xyz = profile.world_size(local_size_xyz)
    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if world_size_xyz[0] > owner_size_x or world_size_xyz[1] > owner_size_y or world_size_xyz[2] > owner_size_z:
        raise RuntimeError(
            f"type2 {profile.role} realized bounds must fit inside {owner_spec.object_id} "
            f"(coil_size={world_size_xyz}, owner_size={owner_spec.size_xyz})"
        )
    if profile.plane == "XY":
        target_world_min_xyz = (
            owner_origin_x + (owner_size_x - world_size_xyz[0]) / 2.0,
            owner_origin_y + (owner_size_y - world_size_xyz[1]) / 2.0,
            owner_origin_z + owner_size_z - world_size_xyz[2],
        )
    else:
        target_world_min_xyz = (
            owner_origin_x + owner_size_x - world_size_xyz[0],
            owner_origin_y + (owner_size_y - world_size_xyz[1]) / 2.0,
            owner_origin_z,
        )
    world_min_delta = profile.world_delta(local_bounds_min_xyz)
    return (
        target_world_min_xyz[0] - world_min_delta[0],
        target_world_min_xyz[1] - world_min_delta[1],
        target_world_min_xyz[2] - world_min_delta[2],
    )


def _transform_modeled_box_spec(
    box_spec: BoxSpec,
    *,
    profile: SingleCoilProfile,
    frame_origin_xyz: Point3,
) -> BoxSpec:
    return BoxSpec(
        label=box_spec.label,
        role=box_spec.role,
        feature=box_spec.feature,
        layer_index=box_spec.layer_index,
        origin_xyz=profile.world_point(box_spec.origin_xyz, frame_origin_xyz=frame_origin_xyz),
        size_xyz=profile.world_size(box_spec.size_xyz),
    )


def _parse_terminal_path_components(raw_terminal_path: str) -> tuple[str, str, str]:
    parts = raw_terminal_path.split("_")
    if len(parts) != 4 or parts[2] != "to":
        raise ValueError(f"terminal path must use '<outer>_<direction>_to_<inner>' format: {raw_terminal_path}")
    outer_corner, direction, _to_keyword, inner_corner = parts
    if outer_corner not in {"A", "B", "C", "D"}:
        raise ValueError(f"terminal path outer corner must be one of A/B/C/D: {raw_terminal_path}")
    if inner_corner not in {"a", "b", "c", "d"}:
        raise ValueError(f"terminal path inner corner must be one of a/b/c/d: {raw_terminal_path}")
    if direction not in {"cw", "ccw"}:
        raise ValueError(f"terminal path direction must be 'cw' or 'ccw': {raw_terminal_path}")
    return (outer_corner, direction, inner_corner)


def _modeled_terminal_metadata(
    *,
    terminal_path: str,
    centerline: tuple[tuple[float, float], ...],
    profile: SingleCoilProfile,
    frame_origin_xyz: Point3,
    transformed_boxes: tuple[BoxSpec, ...],
) -> dict[str, object]:
    if len(centerline) < 2:
        raise RuntimeError("type2 single-coil centerline must contain at least two points")
    outer_corner, direction, inner_corner = _parse_terminal_path_components(terminal_path)
    start_label = f"{profile.copper_body_prefix}_bus_start"
    end_label = f"{profile.copper_body_prefix}_bus_end"
    start_bus_matches = [box for box in transformed_boxes if box.label == start_label]
    end_bus_matches = [box for box in transformed_boxes if box.label == end_label]
    if profile.role == "tx_single_coil" and start_bus_matches and end_bus_matches:
        if len(start_bus_matches) != 1 or len(end_bus_matches) != 1:
            raise RuntimeError(
                "type2 tx multilayer terminal metadata requires exactly one start/end bus box "
                f"(start_matches={len(start_bus_matches)}, end_matches={len(end_bus_matches)})"
            )
        start_point_plane_mm = (
            start_bus_matches[0].origin_xyz[0] + (start_bus_matches[0].size_xyz[0] / 2.0),
            start_bus_matches[0].origin_xyz[1] + (start_bus_matches[0].size_xyz[1] / 2.0),
        )
        end_point_plane_mm = (
            end_bus_matches[0].origin_xyz[0] + (end_bus_matches[0].size_xyz[0] / 2.0),
            end_bus_matches[0].origin_xyz[1] + (end_bus_matches[0].size_xyz[1] / 2.0),
        )
    else:
        start_point_plane_mm = profile.plane_point(centerline[0], frame_origin_xyz=frame_origin_xyz)
        end_point_plane_mm = profile.plane_point(centerline[-1], frame_origin_xyz=frame_origin_xyz)
    return {
        "path": terminal_path,
        "outer_corner": outer_corner,
        "inner_corner": inner_corner,
        "direction": direction,
        "start_point_plane_mm": start_point_plane_mm,
        "end_point_plane_mm": end_point_plane_mm,
    }


def _modeled_canonical_coordinates(
    *,
    transformed_boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
    frame_origin_xyz: Point3,
) -> dict[str, object]:
    world_bounds_min_xyz, world_bounds_max_xyz, world_bounds_size_xyz = modeled_body_bounds_from_boxes(transformed_boxes)
    pcb_boxes = tuple(box for box in transformed_boxes if box.role == "pcb")
    copper_position_boxes = tuple(
        box for box in transformed_boxes if box.role == "copper" and box.feature == "planar_outline"
    )
    if len(copper_position_boxes) == 0:
        raise RuntimeError("modeled canonical coordinates require at least one planar outline copper box")
    copper_position_boxes_by_layer: dict[int, BoxSpec] = {}
    for copper_box in copper_position_boxes:
        if copper_box.layer_index not in copper_position_boxes_by_layer:
            copper_position_boxes_by_layer[copper_box.layer_index] = copper_box
    pcb_layer_positions = tuple(
        box.origin_xyz[2 if profile.plane == "XY" else 0]
        for box in sorted(pcb_boxes, key=lambda box: box.layer_index)
    )
    copper_layer_positions = tuple(
        box.origin_xyz[2 if profile.plane == "XY" else 0]
        for box in sorted(copper_position_boxes_by_layer.values(), key=lambda box: box.layer_index)
    )
    return {
        "frame_origin_xyz": frame_origin_xyz,
        "outer_bounds_min_xyz": world_bounds_min_xyz,
        "outer_bounds_max_xyz": world_bounds_max_xyz,
        "outer_bounds_size_xyz": world_bounds_size_xyz,
        "pcb_layer_z_positions_mm": pcb_layer_positions,
        "copper_layer_z_positions_mm": copper_layer_positions,
    }


def build_modeled_single_coil_scene_data(
    spec: ModeledTxSingleCoilSpec,
    *,
    owner_spec: NonModelBoxSpec,
    seed: int,
) -> tuple[tuple[bd.Shape, ...], ModeledObjectSceneData]:
    profile = profile_for_modeled_role(spec.role)
    with tempfile.TemporaryDirectory(prefix="type2_tx_rect_void_") as temp_dir:
        temp_toml_path = Path(temp_dir) / f"{spec.object_id}.toml"
        temp_toml_path.write_text(render_tx_rect_void_toml(spec), encoding="utf-8")
        tx_rect_void_spec = load_tx_rect_void_spec(temp_toml_path)
        realized = realize_tx_rect_void_spec(tx_rect_void_spec, seed=seed, profile=profile)
        local_boxes = build_tx_rect_void_box_specs(realized, profile=profile)
        local_bounds_min_xyz, _local_bounds_max_xyz, local_size_xyz = modeled_body_bounds_from_boxes(local_boxes)
        placement_offset_xyz = _single_coil_placement_offset_from_local_bounds(
            owner_spec=owner_spec,
            local_bounds_min_xyz=local_bounds_min_xyz,
            local_size_xyz=local_size_xyz,
            profile=profile,
        )
        transformed_boxes = tuple(
            _transform_modeled_box_spec(
                box_spec,
                profile=profile,
                frame_origin_xyz=placement_offset_xyz,
            )
            for box_spec in local_boxes
        )
        modeled_scene = build_tx_rect_void_step_scene(
            realized,
            transformed_boxes,
            profile=profile,
            frame_origin_xyz=placement_offset_xyz,
        )
        scene_children = tuple(modeled_scene.children)
        if not scene_children:
            raise RuntimeError(f"type2 modeled scene must expose child bodies: {spec.object_id}")
        expected_exported_body_names = tuple(shape.label for shape in scene_children)
        if len(set(expected_exported_body_names)) != len(expected_exported_body_names):
            raise RuntimeError(
                "type2 modeled scene body names must be unique "
                f"(object_id={spec.object_id}, names={expected_exported_body_names})"
            )
        canonical_coordinates = _modeled_canonical_coordinates(
            transformed_boxes=transformed_boxes,
            profile=profile,
            frame_origin_xyz=placement_offset_xyz,
        )
        terminal_metadata = _modeled_terminal_metadata(
            terminal_path=realized.terminal_path,
            centerline=build_tx_rect_void_centerline(realized),
            profile=profile,
            frame_origin_xyz=placement_offset_xyz,
            transformed_boxes=transformed_boxes,
        )

    return (
        scene_children,
        {
            "object_id": spec.object_id,
            "role": spec.role,
            "plane": cast(Literal["XY", "YZ"], profile.plane),
            "placement_owner_id": profile.placement_owner_id,
            "material": spec.material,
            "model_state": True,
            "expected_exported_body_names": expected_exported_body_names,
            "expected_exported_body_count": len(expected_exported_body_names),
            "canonical_coordinates": canonical_coordinates,
            "terminal_metadata": terminal_metadata,
        },
    )


__all__ = [
    "build_modeled_single_coil_scene_data",
    "build_non_model_scene_entry",
    "build_non_model_scene_shapes",
    "require_non_model_object_spec",
    "single_coil_placement_offset",
]

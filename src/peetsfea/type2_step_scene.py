from __future__ import annotations

import hashlib
import math
import tempfile
from dataclasses import dataclass
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
from peetsfea.type2_plate_stack import build_plate_stack_scene_data
from peetsfea.type2_step_ledger import CanonicalCoordinates
from peetsfea.type2_step_ledger import ExportedBodyGroup
from peetsfea.type2_step_ledger import ModeledObjectSceneData
from peetsfea.type2_step_ledger import NonModelObjectLedgerEntry
from peetsfea.type2_step_ledger import NonModelSceneMemberLedgerEntry
from peetsfea.type2_step_spec import ModeledObjectSpec
from peetsfea.type2_step_spec import ModeledRxPlateStackSpec
from peetsfea.type2_step_spec import ModeledSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import NonModelTxRegionActualSpec
from peetsfea.type2_step_spec import Point3
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import render_tx_rect_void_toml
from peetsfea.type2_step_spec import resolve_modeled_underlay_gap_mm
from peetsfea.type2_step_spec import resolve_modeled_underlay_repeat_count
from peetsfea.type2_step_spec import resolve_modeled_wall_parallel_stack_present

_NON_MODEL_VISIBLE_GROUPS: tuple[tuple[str, str, Literal["XY", "YZ", "ZX", "mixed"], tuple[str, ...]], ...] = (
    ("environment", "environment", "mixed", ("floor", "shelf", "wall", "tv")),
    ("tx_region", "tx_region", "XY", ("tx_region",)),
    ("rx_region_max", "rx_region_max", "YZ", ("rx_region_max",)),
)
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


def _ferrite_group_name_for_modeled_role(*, role: Literal["tx_single_coil", "rx_single_coil"]) -> str:
    if role == "tx_single_coil":
        return _TX_FERRITE_GROUP_NAME
    if role == "rx_single_coil":
        return _RX_FERRITE_GROUP_NAME
    raise RuntimeError(f"unsupported ferrite grouping role: {role}")


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
    tx_region_actual_specs = tuple(spec for spec in specs if spec.kind == "tx_region_actual")
    if len(tx_region_actual_specs) == 0:
        raise RuntimeError("type2 non-model registry must contain at least one tx_region_actual concrete object")
    tx_region_actual_sorted_specs = tuple(sorted(tx_region_actual_specs, key=lambda spec: spec.object_id))
    for object_id, role, plane, member_ids in _NON_MODEL_VISIBLE_GROUPS:
        group_specs = tuple(require_non_model_object_spec(specs, object_id=member_id) for member_id in member_ids)
        groups.append((object_id, role, plane, group_specs))
        if object_id == "tx_region":
            groups.append(("tx_region_actual", "tx_region_actual", "XY", tx_region_actual_sorted_specs))
    return tuple(groups)


def _is_concrete_tx_region_actual_object_id(object_id: str) -> bool:
    if object_id == "tx_region_actual":
        return True
    if not object_id.startswith("tx_region_actual_x"):
        return False
    if "_y" not in object_id:
        return False
    x_fragment, y_fragment = object_id.split("_y", maxsplit=1)
    if not x_fragment.startswith("tx_region_actual_x"):
        return False
    x_index_text = x_fragment[len("tx_region_actual_x") :]
    if x_index_text == "" or y_fragment == "":
        return False
    if not x_index_text.isdigit() or not y_fragment.isdigit():
        return False
    return True


def _float_range_candidates(range_spec: RangeSpec) -> tuple[float, ...]:
    if range_spec.is_integer is not False:
        raise ValueError("non-model actual region usage ratio requires non-integer range spec")
    if range_spec.count == 1:
        return (range_spec.start,)
    step = (range_spec.end - range_spec.start) / float(range_spec.count - 1)
    return tuple(range_spec.start + (step * index) for index in range(range_spec.count))


def _selected_float_candidate(*, range_spec: RangeSpec, owner_path: str, seed: int) -> float:
    candidates = _float_range_candidates(range_spec)
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated for non-model sampled owner: {owner_path}")
    if len(candidates) == 1:
        return candidates[0]
    digest = hashlib.blake2b(f"{seed}:{owner_path}".encode("utf-8"), digest_size=8).digest()
    index = int.from_bytes(digest, byteorder="big", signed=False) % len(candidates)
    return candidates[index]


def _integer_range_candidates(range_spec: RangeSpec) -> tuple[int, ...]:
    if range_spec.is_integer is not True:
        raise ValueError("non-model actual region division count requires integer range spec")
    if range_spec.count == 1:
        value = int(round(range_spec.start))
        if not math.isclose(range_spec.start, float(value), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(
                "non-model actual region fixed integer range must realize to an integer "
                f"(start={range_spec.start})"
            )
        return (value,)
    step = (range_spec.end - range_spec.start) / float(range_spec.count - 1)
    candidates: list[int] = []
    for index in range(range_spec.count):
        raw_value = range_spec.start + (step * index)
        int_value = int(round(raw_value))
        if not math.isclose(raw_value, float(int_value), rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(
                "non-model actual region integer range must realize to integer candidates "
                f"(raw_value={raw_value}, int_value={int_value}, index={index})"
            )
        candidates.append(int_value)
    return tuple(candidates)


def _selected_integer_candidate(*, range_spec: RangeSpec, owner_path: str, seed: int) -> int:
    candidates = _integer_range_candidates(range_spec)
    if len(candidates) == 0:
        raise ValueError(f"No integer candidates generated for non-model sampled owner: {owner_path}")
    if len(candidates) == 1:
        return candidates[0]
    digest = hashlib.blake2b(f"{seed}:{owner_path}".encode("utf-8"), digest_size=8).digest()
    index = int.from_bytes(digest, byteorder="big", signed=False) % len(candidates)
    return candidates[index]


def resolve_non_model_scene_specs(
    *,
    base_specs: tuple[NonModelBoxSpec, ...],
    derived_specs: tuple[NonModelTxRegionActualSpec, ...],
    seed: int,
) -> tuple[NonModelBoxSpec, ...]:
    resolved_specs = list(base_specs)
    for derived_spec in derived_specs:
        resolved_specs.extend(
            _resolved_tx_region_actual_specs(
                derived_spec=derived_spec,
                base_specs=base_specs,
                seed=seed,
            )
        )
    return tuple(resolved_specs)


def _resolved_tx_region_actual_specs(
    *,
    derived_spec: NonModelTxRegionActualSpec,
    base_specs: tuple[NonModelBoxSpec, ...],
    seed: int,
) -> tuple[NonModelBoxSpec, ...]:
    tx_region_spec = require_non_model_object_spec(base_specs, object_id=derived_spec.source_region_id)
    tx_origin_x, tx_origin_y, tx_origin_z = tx_region_spec.origin_xyz
    tx_size_x, tx_size_y, tx_size_z = tx_region_spec.size_xyz
    x_usage_ratio = _selected_float_candidate(
        range_spec=derived_spec.x_usage_ratio,
        owner_path=f"non_model_objects.{derived_spec.object_id}.x_usage_ratio",
        seed=seed,
    )
    y_usage_ratio = _selected_float_candidate(
        range_spec=derived_spec.y_usage_ratio,
        owner_path=f"non_model_objects.{derived_spec.object_id}.y_usage_ratio",
        seed=seed,
    )
    x_division_count = _selected_integer_candidate(
        range_spec=derived_spec.x_division_count,
        owner_path=f"non_model_objects.{derived_spec.object_id}.x_division_count",
        seed=seed,
    )
    y_division_count = _selected_integer_candidate(
        range_spec=derived_spec.y_division_count,
        owner_path=f"non_model_objects.{derived_spec.object_id}.y_division_count",
        seed=seed,
    )
    if x_division_count < 1:
        raise RuntimeError(
            "derived tx_region_actual x_division_count must be >= 1 "
            f"(actual={x_division_count})"
        )
    if y_division_count < 1:
        raise RuntimeError(
            "derived tx_region_actual y_division_count must be >= 1 "
            f"(actual={y_division_count})"
        )
    actual_size_x = tx_size_x * x_usage_ratio
    actual_size_y = tx_size_y * y_usage_ratio
    actual_size_z = tx_size_z
    actual_origin_xyz: Point3 = (
        tx_origin_x,
        tx_origin_y + ((tx_size_y - actual_size_y) / 2.0),
        tx_origin_z,
    )
    if actual_origin_xyz[0] < tx_origin_x - 1e-9:
        raise RuntimeError(
            "derived tx_region_actual must anchor at tx_region min_x "
            f"(tx_region_min_x={tx_origin_x}, tx_region_actual_origin={actual_origin_xyz})"
        )
    if abs((actual_origin_xyz[1] + (actual_size_y / 2.0)) - (tx_origin_y + (tx_size_y / 2.0))) > 1e-9:
        raise RuntimeError(
            "derived tx_region_actual must remain y-centered inside tx_region "
            f"(tx_region_origin={tx_region_spec.origin_xyz}, tx_region_size={tx_region_spec.size_xyz}, "
            f"tx_region_actual_origin={actual_origin_xyz}, tx_region_actual_size={(actual_size_x, actual_size_y, actual_size_z)})"
        )
    if abs(actual_size_z - tx_size_z) > 1e-9 or abs(actual_origin_xyz[2] - tx_origin_z) > 1e-9:
        raise RuntimeError(
            "derived tx_region_actual must preserve full tx_region Z span "
            f"(tx_region_origin={tx_region_spec.origin_xyz}, tx_region_size={tx_region_spec.size_xyz}, "
            f"tx_region_actual_origin={actual_origin_xyz}, tx_region_actual_size={(actual_size_x, actual_size_y, actual_size_z)})"
        )
    tile_size_x = actual_size_x / float(x_division_count)
    tile_size_y = actual_size_y / float(y_division_count)
    if tile_size_x <= 0.0 or tile_size_y <= 0.0:
        raise RuntimeError(
            "derived tx_region_actual tile size must be positive "
            f"(tile_size_x={tile_size_x}, tile_size_y={tile_size_y}, "
            f"x_division_count={x_division_count}, y_division_count={y_division_count})"
        )
    tile_specs: list[NonModelBoxSpec] = []
    for x_index in range(x_division_count):
        for y_index in range(y_division_count):
            tile_origin_xyz: Point3 = (
                actual_origin_xyz[0] + (tile_size_x * float(x_index)),
                actual_origin_xyz[1] + (tile_size_y * float(y_index)),
                actual_origin_xyz[2],
            )
            if x_division_count == 1 and y_division_count == 1:
                tile_object_id = derived_spec.object_id
            else:
                tile_object_id = f"{derived_spec.object_id}_x{x_index}_y{y_index}"
            tile_specs.append(
                NonModelBoxSpec(
                    object_id=tile_object_id,
                    kind=derived_spec.kind,
                    primitive="box",
                    present=True,
                    non_model=True,
                    material=tx_region_spec.material,
                    plane=tx_region_spec.plane,
                    origin_xyz=tile_origin_xyz,
                    size_xyz=(tile_size_x, tile_size_y, actual_size_z),
                )
            )
    return tuple(tile_specs)


def _build_non_model_group_shape(*, object_id: str, specs: tuple[NonModelBoxSpec, ...]) -> bd.Shape:
    if not specs:
        raise ValueError(f"non-model group shape requires at least one spec ({object_id})")
    fused_shape = _build_non_model_shape(specs[0])
    for spec in specs[1:]:
        fused_shape = cast(bd.Shape, fused_shape.fuse(_build_non_model_shape(spec)))
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
        if object_id == "tx_region_actual":
            for tx_region_actual_spec in group_specs:
                if tx_region_actual_spec.kind != "tx_region_actual":
                    raise RuntimeError(
                        "tx_region_actual concrete scene member must preserve kind tx_region_actual "
                        f"(object_id={tx_region_actual_spec.object_id}, kind={tx_region_actual_spec.kind})"
                    )
                if not _is_concrete_tx_region_actual_object_id(tx_region_actual_spec.object_id):
                    raise RuntimeError(
                        "tx_region_actual concrete scene member must use concrete object id contract "
                        f"(object_id={tx_region_actual_spec.object_id})"
                    )
                members.append(
                    {
                        "object_id": tx_region_actual_spec.object_id,
                        "role": role,
                        "material": tx_region_actual_spec.material,
                        "model_state": False,
                        "canonical_coordinates": _canonical_from_box(tx_region_actual_spec),
                        "plane": tx_region_actual_spec.plane,
                        "non_model": True,
                    }
                )
            continue
        resolved_plane = plane
        if object_id == "tx_region":
            if len(group_specs) != 1:
                raise RuntimeError(
                    "tx_region scene member must derive from one source spec "
                    f"(object_id={object_id}, source_count={len(group_specs)})"
                )
            resolved_plane = group_specs[0].plane
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
                "plane": resolved_plane,
                "non_model": True,
            }
        )
    return tuple(members)


def build_non_model_scene_shapes(specs: tuple[NonModelBoxSpec, ...]) -> tuple[bd.Shape, ...]:
    scene_shapes: list[bd.Shape] = []
    for object_id, _role, _plane, group_specs in _non_model_group_specs(specs):
        if object_id == "tx_region_actual":
            for tx_region_actual_spec in group_specs:
                scene_shapes.append(_build_non_model_shape(tx_region_actual_spec))
            continue
        scene_shapes.append(_build_non_model_group_shape(object_id=object_id, specs=group_specs))
    return tuple(scene_shapes)


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
            owner_origin_x,
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


def _local_terminal_plane_points(
    *,
    terminal_path: str,
    centerline: tuple[tuple[float, float], ...],
    transformed_boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
    frame_origin_xyz: Point3,
) -> tuple[tuple[float, float], tuple[float, float]]:
    if len(centerline) < 2:
        raise RuntimeError("type2 single-coil centerline must contain at least two points")
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
        start_point_world = (
            start_bus_matches[0].origin_xyz[0] + (start_bus_matches[0].size_xyz[0] / 2.0),
            start_bus_matches[0].origin_xyz[1] + (start_bus_matches[0].size_xyz[1] / 2.0),
        )
        end_point_world = (
            end_bus_matches[0].origin_xyz[0] + (end_bus_matches[0].size_xyz[0] / 2.0),
            end_bus_matches[0].origin_xyz[1] + (end_bus_matches[0].size_xyz[1] / 2.0),
        )
    else:
        _outer_corner, _direction, _inner_corner = _parse_terminal_path_components(terminal_path)
        start_point_world = profile.plane_point(centerline[0], frame_origin_xyz=frame_origin_xyz)
        end_point_world = profile.plane_point(centerline[-1], frame_origin_xyz=frame_origin_xyz)
    local_origin_plane = profile.plane_point((0.0, 0.0), frame_origin_xyz=frame_origin_xyz)
    return (
        (
            start_point_world[0] - local_origin_plane[0],
            start_point_world[1] - local_origin_plane[1],
        ),
        (
            end_point_world[0] - local_origin_plane[0],
            end_point_world[1] - local_origin_plane[1],
        ),
    )


def _port_sheet_label_for_profile(profile: SingleCoilProfile) -> str:
    if profile.role == "tx_single_coil":
        return "tx_port_sheet"
    if profile.role == "rx_single_coil":
        return "rx_port_sheet"
    raise RuntimeError(f"unsupported single-coil profile role for port sheet label: {profile.role}")


def _port_sheet_owner_bottom_plane_coordinate(*, box: BoxSpec, profile: SingleCoilProfile) -> float:
    if profile.plane == "XY":
        return box.origin_xyz[2]
    return box.origin_xyz[0]


def _port_sheet_owner_bottom_square_plane_bounds(
    *,
    box: BoxSpec,
    profile: SingleCoilProfile,
) -> tuple[tuple[float, float], tuple[float, float]]:
    origin_x, origin_y, origin_z = box.origin_xyz
    size_x, size_y, size_z = box.size_xyz
    if profile.plane == "XY":
        square_side_a = size_x
        square_side_b = size_y
        plane_min = (origin_x, origin_y)
    else:
        square_side_a = size_y
        square_side_b = size_z
        plane_min = (origin_y, origin_z)
    if square_side_a <= 0.0 or square_side_b <= 0.0:
        raise RuntimeError(
            "type2 port sheet requires positive bottom-face square dimensions "
            f"(role={profile.role}, box={box.label}, size={box.size_xyz})"
        )
    if abs(square_side_a - square_side_b) > 1e-9:
        raise RuntimeError(
            "type2 port-sheet owner bottom-face footprint must be square for port sheet derivation "
            f"(role={profile.role}, box={box.label}, size={box.size_xyz})"
        )
    plane_max = (plane_min[0] + square_side_a, plane_min[1] + square_side_b)
    return (plane_min, plane_max)


def _synthetic_tx_bus_owner_box(
    *,
    transformed_boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
    terminal_column: Literal["start", "end"],
) -> BoxSpec:
    terminal_stub_boxes = tuple(box for box in transformed_boxes if box.feature == "terminal_stub")
    matching_stub_boxes = tuple(
        box for box in terminal_stub_boxes if box.label.endswith(f"_stub_{terminal_column}")
    )
    if len(matching_stub_boxes) == 0:
        raise RuntimeError(
            "type2 tx port sheet requires at least one transformed terminal stub per terminal column "
            f"(terminal_column={terminal_column}, actual=0)"
        )
    if len(matching_stub_boxes) * 2 != len(terminal_stub_boxes):
        raise RuntimeError(
            "type2 tx port sheet requires balanced transformed start/end terminal stub boxes "
            f"(terminal_column={terminal_column}, matching={len(matching_stub_boxes)}, total={len(terminal_stub_boxes)})"
        )
    min_x = min(box.origin_xyz[0] for box in matching_stub_boxes)
    min_y = min(box.origin_xyz[1] for box in matching_stub_boxes)
    min_z = min(box.origin_xyz[2] for box in matching_stub_boxes)
    max_x = max(box.origin_xyz[0] + box.size_xyz[0] for box in matching_stub_boxes)
    max_y = max(box.origin_xyz[1] + box.size_xyz[1] for box in matching_stub_boxes)
    max_z = max(box.origin_xyz[2] + box.size_xyz[2] for box in matching_stub_boxes)
    return BoxSpec(
        label=f"{profile.copper_body_prefix}_bus_{terminal_column}",
        role="copper",
        feature="vertical_bus",
        layer_index=0,
        origin_xyz=(min_x, min_y, min_z),
        size_xyz=(max_x - min_x, max_y - min_y, max_z - min_z),
    )


def _port_sheet_owner_boxes(
    *,
    transformed_boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
) -> tuple[BoxSpec, BoxSpec]:
    if profile.role == "tx_single_coil":
        first_box, second_box = (
            _synthetic_tx_bus_owner_box(
                transformed_boxes=transformed_boxes,
                profile=profile,
                terminal_column="start",
            ),
            _synthetic_tx_bus_owner_box(
                transformed_boxes=transformed_boxes,
                profile=profile,
                terminal_column="end",
            ),
        )
    else:
        terminal_stub_boxes = tuple(box for box in transformed_boxes if box.feature == "terminal_stub")
        start_matches = [box for box in terminal_stub_boxes if box.label == f"{profile.copper_body_prefix}_l0_stub_start"]
        end_matches = [box for box in terminal_stub_boxes if box.label == f"{profile.copper_body_prefix}_l0_stub_end"]
        if len(start_matches) != 1 or len(end_matches) != 1 or len(terminal_stub_boxes) != 2:
            raise RuntimeError(
                "type2 port sheet requires exactly one transformed start/end terminal stub box "
                f"(role={profile.role}, start_matches={len(start_matches)}, end_matches={len(end_matches)}, actual={len(terminal_stub_boxes)})"
            )
        first_box, second_box = (start_matches[0], end_matches[0])
    first_bottom_plane_coordinate = _port_sheet_owner_bottom_plane_coordinate(box=first_box, profile=profile)
    second_bottom_plane_coordinate = _port_sheet_owner_bottom_plane_coordinate(box=second_box, profile=profile)
    if abs(first_bottom_plane_coordinate - second_bottom_plane_coordinate) > 1e-9:
        raise RuntimeError(
            "type2 port-sheet owner bottom faces must share one plane "
            f"(role={profile.role}, first={first_box.label}, second={second_box.label}, "
            f"first_bottom={first_bottom_plane_coordinate}, second_bottom={second_bottom_plane_coordinate})"
        )
    return (first_box, second_box)


def _port_sheet_owner_bottom_square_center_plane_xy(
    *,
    box: BoxSpec,
    profile: SingleCoilProfile,
) -> tuple[float, float]:
    (plane_min_u, plane_min_v), (plane_max_u, plane_max_v) = _port_sheet_owner_bottom_square_plane_bounds(
        box=box,
        profile=profile,
    )
    return (
        (plane_min_u + plane_max_u) / 2.0,
        (plane_min_v + plane_max_v) / 2.0,
    )


def _line_signed_distance_in_plane(
    *,
    point_plane_xy: tuple[float, float],
    line_origin_plane_xy: tuple[float, float],
    line_direction_plane_xy: tuple[float, float],
) -> float:
    direction_u, direction_v = line_direction_plane_xy
    direction_length = math.hypot(direction_u, direction_v)
    if direction_length <= 1e-9:
        raise RuntimeError(
            "type2 port sheet inter-owner centerline must have positive length "
            f"(line_origin={line_origin_plane_xy}, line_direction={line_direction_plane_xy})"
        )
    point_offset_u = point_plane_xy[0] - line_origin_plane_xy[0]
    point_offset_v = point_plane_xy[1] - line_origin_plane_xy[1]
    return ((direction_u * point_offset_v) - (direction_v * point_offset_u)) / direction_length


def _plane_point_to_world_xyz(
    *,
    point_plane_xy: tuple[float, float],
    bottom_plane_coordinate: float,
    profile: SingleCoilProfile,
) -> Point3:
    if profile.plane == "XY":
        return (point_plane_xy[0], point_plane_xy[1], bottom_plane_coordinate)
    return (bottom_plane_coordinate, point_plane_xy[0], point_plane_xy[1])


def _selected_diagonal_plane_points_for_stub(
    *,
    box: BoxSpec,
    profile: SingleCoilProfile,
    line_origin_plane_xy: tuple[float, float],
    line_direction_plane_xy: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    (plane_min_u, plane_min_v), (plane_max_u, plane_max_v) = _port_sheet_owner_bottom_square_plane_bounds(
        box=box,
        profile=profile,
    )
    candidate_diagonals = (
        ((plane_min_u, plane_min_v), (plane_max_u, plane_max_v)),
        ((plane_min_u, plane_max_v), (plane_max_u, plane_min_v)),
    )

    def _ordered_endpoints(
        diagonal: tuple[tuple[float, float], tuple[float, float]],
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        first_point_plane_xy, second_point_plane_xy = diagonal

        def _endpoint_sort_key(point_plane_xy: tuple[float, float]) -> tuple[float, float, float]:
            signed_distance = _line_signed_distance_in_plane(
                point_plane_xy=point_plane_xy,
                line_origin_plane_xy=line_origin_plane_xy,
                line_direction_plane_xy=line_direction_plane_xy,
            )
            return (
                signed_distance,
                point_plane_xy[0],
                point_plane_xy[1],
            )

        ordered_points = tuple(sorted(diagonal, key=_endpoint_sort_key, reverse=True))
        if len(ordered_points) != 2:
            raise RuntimeError(f"type2 port sheet diagonal ordering must keep two endpoints: {ordered_points}")
        return cast(tuple[tuple[float, float], tuple[float, float]], ordered_points)

    def _diagonal_selection_key(
        diagonal: tuple[tuple[float, float], tuple[float, float]],
    ) -> tuple[float, float, float, float, float]:
        ordered_first_point_plane_xy, ordered_second_point_plane_xy = _ordered_endpoints(diagonal)
        signed_distance_a = abs(
            _line_signed_distance_in_plane(
                point_plane_xy=ordered_first_point_plane_xy,
                line_origin_plane_xy=line_origin_plane_xy,
                line_direction_plane_xy=line_direction_plane_xy,
            )
        )
        signed_distance_b = abs(
            _line_signed_distance_in_plane(
                point_plane_xy=ordered_second_point_plane_xy,
                line_origin_plane_xy=line_origin_plane_xy,
                line_direction_plane_xy=line_direction_plane_xy,
            )
        )
        return (
            signed_distance_a + signed_distance_b,
            ordered_first_point_plane_xy[0],
            ordered_first_point_plane_xy[1],
            ordered_second_point_plane_xy[0],
            ordered_second_point_plane_xy[1],
        )

    selected_diagonal = max(candidate_diagonals, key=_diagonal_selection_key)
    return _ordered_endpoints(selected_diagonal)


def _build_single_coil_port_sheet_shape(
    *,
    transformed_boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
) -> bd.Shape:
    vertices = _single_coil_port_sheet_vertices(
        transformed_boxes=transformed_boxes,
        profile=profile,
    )
    with bd.BuildLine() as builder:
        bd.Polyline(*vertices, close=True)
    assert builder.line is not None, "type2 port-sheet line builder must produce a wire"
    port_wire = builder.line.wires()[0]
    face = cast(bd.Face, bd.make_face(edges=tuple(port_wire.edges())))
    face.label = _port_sheet_label_for_profile(profile)
    return face


def _single_coil_port_sheet_vertices(
    *,
    transformed_boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
) -> tuple[Point3, Point3, Point3, Point3]:
    first_stub_box, second_stub_box = _port_sheet_owner_boxes(
        transformed_boxes=transformed_boxes,
        profile=profile,
    )
    first_stub_center_plane_xy = _port_sheet_owner_bottom_square_center_plane_xy(box=first_stub_box, profile=profile)
    second_stub_center_plane_xy = _port_sheet_owner_bottom_square_center_plane_xy(box=second_stub_box, profile=profile)
    inter_stub_centerline_direction_plane_xy = (
        second_stub_center_plane_xy[0] - first_stub_center_plane_xy[0],
        second_stub_center_plane_xy[1] - first_stub_center_plane_xy[1],
    )
    first_diagonal_start_plane_xy, first_diagonal_end_plane_xy = _selected_diagonal_plane_points_for_stub(
        box=first_stub_box,
        profile=profile,
        line_origin_plane_xy=first_stub_center_plane_xy,
        line_direction_plane_xy=inter_stub_centerline_direction_plane_xy,
    )
    second_diagonal_start_plane_xy, second_diagonal_end_plane_xy = _selected_diagonal_plane_points_for_stub(
        box=second_stub_box,
        profile=profile,
        line_origin_plane_xy=first_stub_center_plane_xy,
        line_direction_plane_xy=inter_stub_centerline_direction_plane_xy,
    )
    bottom_plane_coordinate = _port_sheet_owner_bottom_plane_coordinate(box=first_stub_box, profile=profile)
    first_diagonal_start_world_xyz = _plane_point_to_world_xyz(
        point_plane_xy=first_diagonal_start_plane_xy,
        bottom_plane_coordinate=bottom_plane_coordinate,
        profile=profile,
    )
    first_diagonal_end_world_xyz = _plane_point_to_world_xyz(
        point_plane_xy=first_diagonal_end_plane_xy,
        bottom_plane_coordinate=bottom_plane_coordinate,
        profile=profile,
    )
    second_diagonal_start_world_xyz = _plane_point_to_world_xyz(
        point_plane_xy=second_diagonal_start_plane_xy,
        bottom_plane_coordinate=bottom_plane_coordinate,
        profile=profile,
    )
    second_diagonal_end_world_xyz = _plane_point_to_world_xyz(
        point_plane_xy=second_diagonal_end_plane_xy,
        bottom_plane_coordinate=bottom_plane_coordinate,
        profile=profile,
    )
    vertices = (
        first_diagonal_start_world_xyz,
        second_diagonal_start_world_xyz,
        second_diagonal_end_world_xyz,
        first_diagonal_end_world_xyz,
    )
    return vertices


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
    outer_corner, direction, inner_corner = _parse_terminal_path_components(terminal_path)
    plane_origin_xy = profile.plane_point((0.0, 0.0), frame_origin_xyz=frame_origin_xyz)
    local_start_xy, local_end_xy = _local_terminal_plane_points(
        terminal_path=terminal_path,
        centerline=centerline,
        transformed_boxes=transformed_boxes,
        profile=profile,
        frame_origin_xyz=frame_origin_xyz,
    )
    start_point_plane_mm = (
        local_start_xy[0] + plane_origin_xy[0],
        local_start_xy[1] + plane_origin_xy[1],
    )
    end_point_plane_mm = (
        local_end_xy[0] + plane_origin_xy[0],
        local_end_xy[1] + plane_origin_xy[1],
    )
    port_sheet_vertices_xyz = _single_coil_port_sheet_vertices(
        transformed_boxes=transformed_boxes,
        profile=profile,
    )
    return {
        "path": terminal_path,
        "outer_corner": outer_corner,
        "inner_corner": inner_corner,
        "direction": direction,
        "start_point_plane_mm": start_point_plane_mm,
        "end_point_plane_mm": end_point_plane_mm,
        "port_sheet_vertices_xyz": port_sheet_vertices_xyz,
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


def _build_labeled_solid_box(
    *,
    label: str,
    origin_xyz: Point3,
    size_xyz: Point3,
) -> bd.Shape:
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


def _single_coil_expected_ferrite_groups(
    *,
    role: Literal["tx_single_coil", "rx_single_coil"],
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
            "group_name": _ferrite_group_name_for_modeled_role(role=role),
            "member_body_names": member_body_names,
        },
    )


def _single_coil_scene_children_with_grouped_ferrite_family(
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


def _shape_min_max_xyz(shape: bd.Shape) -> tuple[Point3, Point3]:
    bbox = shape.bounding_box()
    return (
        (bbox.min.X, bbox.min.Y, bbox.min.Z),
        (bbox.max.X, bbox.max.Y, bbox.max.Z),
    )


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


def _resolve_tx_underlay_placement_descriptor(
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


def _build_tx_wall_parallel_scene_shapes(
    descriptor: _TxUnderlayPlacementDescriptor,
) -> tuple[bd.Shape, ...]:
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


def _build_rx_underlay_scene_shapes(
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


def build_modeled_single_coil_scene_data(
    spec: ModeledSingleCoilSpec,
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
        centerline = build_tx_rect_void_centerline(realized)
        modeled_scene = build_tx_rect_void_step_scene(
            realized,
            transformed_boxes,
            profile=profile,
            frame_origin_xyz=placement_offset_xyz,
        )
        existing_scene_children = tuple(modeled_scene.children)
        port_sheet_label = _port_sheet_label_for_profile(profile)
        base_scene_children = tuple(shape for shape in existing_scene_children if shape.label != port_sheet_label)
        if not base_scene_children:
            raise RuntimeError(f"type2 modeled scene must expose child bodies: {spec.object_id}")
        modeled_bounds_min_xyz, modeled_bounds_max_xyz, _modeled_bounds_size_xyz = modeled_body_bounds_from_boxes(
            transformed_boxes
        )
        underlay_repeat_count = resolve_modeled_underlay_repeat_count(spec, seed=seed)
        if profile.role == "tx_single_coil":
            if cast(Literal["XY", "YZ"], profile.plane) != "XY":
                raise RuntimeError(f"type2 tx underlay requires XY modeled plane (actual={profile.plane})")
            if not isinstance(spec, ModeledTxSingleCoilSpec):
                raise RuntimeError(f"type2 tx underlay gap requires tx modeled spec (object_id={spec.object_id})")
            tx_underlay_descriptor = (
                _resolve_tx_underlay_placement_descriptor(
                    owner_spec=owner_spec,
                    modeled_min_z=modeled_bounds_min_xyz[2],
                    modeled_max_x=modeled_bounds_max_xyz[0],
                    repeat_count=underlay_repeat_count,
                    gap_mm=resolve_modeled_underlay_gap_mm(spec, seed=seed),
                )
                if underlay_repeat_count > 0
                else None
            )
            # TX floor-parallel underlay is intentionally omitted from exported scene bodies.
            # The placement descriptor still owns the wall-stack envelope below the coil.
            wall_underlay_scene_children = (
                _build_tx_wall_parallel_scene_shapes(tx_underlay_descriptor)
                if tx_underlay_descriptor is not None
                and resolve_modeled_wall_parallel_stack_present(spec, seed=seed)
                else ()
            )
            underlay_scene_children = wall_underlay_scene_children
        else:
            underlay_scene_children = (
                _build_rx_underlay_scene_shapes(
                    owner_spec=owner_spec,
                    repeat_count=underlay_repeat_count,
                    modeled_bounds_min_xyz=modeled_bounds_min_xyz,
                    modeled_bounds_max_xyz=modeled_bounds_max_xyz,
                )
                if underlay_repeat_count > 0
                else ()
            )
        expected_exported_body_names = tuple(
            shape.label for shape in (base_scene_children + underlay_scene_children)
        )
        if len(set(expected_exported_body_names)) != len(expected_exported_body_names):
            raise RuntimeError(
                "type2 modeled scene body names must be unique "
                f"(object_id={spec.object_id}, names={expected_exported_body_names})"
            )
        modeled_role = cast(Literal["tx_single_coil", "rx_single_coil"], profile.role)
        expected_exported_body_groups = _single_coil_expected_ferrite_groups(
            role=modeled_role,
            underlay_scene_children=underlay_scene_children,
        )
        scene_children = _single_coil_scene_children_with_grouped_ferrite_family(
            base_scene_children=base_scene_children,
            underlay_scene_children=underlay_scene_children,
            expected_exported_body_groups=expected_exported_body_groups,
        )
        canonical_coordinates = _modeled_canonical_coordinates(
            transformed_boxes=transformed_boxes,
            profile=profile,
            frame_origin_xyz=placement_offset_xyz,
        )
        terminal_metadata = _modeled_terminal_metadata(
            terminal_path=realized.terminal_path,
            centerline=centerline,
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
            "expected_exported_body_groups": expected_exported_body_groups,
            "canonical_coordinates": canonical_coordinates,
            "terminal_metadata": terminal_metadata,
        },
    )


def build_modeled_scene_data(
    spec: ModeledObjectSpec,
    *,
    owner_spec: NonModelBoxSpec,
    seed: int,
) -> tuple[tuple[bd.Shape, ...], ModeledObjectSceneData]:
    if isinstance(spec, (ModeledTxPlateStackSpec, ModeledRxPlateStackSpec)):
        return build_plate_stack_scene_data(spec, owner_spec=owner_spec, seed=seed)
    return build_modeled_single_coil_scene_data(
        cast(ModeledSingleCoilSpec, spec),
        owner_spec=owner_spec,
        seed=seed,
    )


__all__ = [
    "build_modeled_scene_data",
    "build_modeled_single_coil_scene_data",
    "build_non_model_scene_entry",
    "build_non_model_scene_shapes",
    "require_non_model_object_spec",
    "resolve_non_model_scene_specs",
    "single_coil_placement_offset",
]

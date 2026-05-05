from __future__ import annotations

import math
import tempfile
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from typing import Literal, cast

import build123d as bd
from build123d.topology import Shape

from peetsfea.tx_rect_void import BoxSpec
from peetsfea.tx_rect_void import RealizedSingleCoilRectVoid
from peetsfea.tx_rect_void import SingleCoilProfile
from peetsfea.tx_rect_void import TX_PARALLEL_SINGLE_COIL_ROLES
from peetsfea.tx_rect_void import build_tx_rect_void_box_specs
from peetsfea.tx_rect_void import build_tx_rect_void_centerline
from peetsfea.tx_rect_void import build_tx_rect_void_step_scene
from peetsfea.tx_rect_void import load_tx_rect_void_spec
from peetsfea.tx_rect_void import modeled_body_bounds_from_boxes
from peetsfea.tx_rect_void import profile_for_modeled_role
from peetsfea.tx_rect_void import realize_tx_rect_void_spec
from peetsfea.type2_single_coil_underlay import build_rx_underlay_scene_shapes
from peetsfea.type2_single_coil_underlay import build_tx_wall_parallel_scene_shapes
from peetsfea.type2_single_coil_underlay import build_tx_inner_single_coil_underlay_shapes
from peetsfea.type2_single_coil_underlay import build_tx_inner_single_coil_void_stack_shapes
from peetsfea.type2_single_coil_underlay import build_tx_outer_single_coil_underlay_shapes
from peetsfea.type2_single_coil_underlay import build_tx_outer_single_coil_void_stack_shapes
from peetsfea.type2_single_coil_underlay import resolve_tx_inner_single_coil_underlay_placement_descriptor
from peetsfea.type2_single_coil_underlay import resolve_tx_inner_single_coil_void_stack_placement_descriptor
from peetsfea.type2_single_coil_underlay import resolve_tx_outer_single_coil_underlay_placement_descriptor
from peetsfea.type2_single_coil_underlay import resolve_tx_underlay_placement_descriptor
from peetsfea.type2_single_coil_underlay import single_coil_expected_ferrite_groups
from peetsfea.type2_single_coil_underlay import single_coil_scene_children_with_ferrite_pet_psa_clearance
from peetsfea.type2_single_coil_underlay import single_coil_scene_children_with_grouped_ferrite_family
from peetsfea.type2_single_coil_ports import modeled_terminal_metadata
from peetsfea.type2_single_coil_ports import port_sheet_label_for_profile
from peetsfea.type2_step_ledger import CanonicalCoordinates
from peetsfea.type2_step_ledger import ModeledObjectSceneData
from peetsfea.type2_step_spec import ModeledSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxOuterSingleCoilSpec
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import Point3
from peetsfea.type2_step_spec import render_tx_rect_void_toml
from peetsfea.type2_step_spec import resolve_modeled_underlay_gap_mm
from peetsfea.type2_step_spec import resolve_modeled_underlay_repeat_count
from peetsfea.type2_step_spec import resolve_modeled_wall_parallel_stack_present
from peetsfea.type2_step_spec_sampling import resolve_modeled_tx_inner_underlay_ferrite_thickness_mm
from peetsfea.type2_step_spec_sampling import resolve_modeled_tx_inner_underlay_pet_psa_thickness_mm
from peetsfea.type2_step_spec_sampling import _float_range_candidates
from peetsfea.type2_step_spec_sampling import _integer_range_candidates
from peetsfea.type2_step_spec_sampling import _resolve_seeded_candidate_index


@dataclass(frozen=True)
class RealizedSingleCoilFitEnvelope:
    realized: RealizedSingleCoilRectVoid
    local_boxes: tuple[BoxSpec, ...]
    transformed_boxes: tuple[BoxSpec, ...]
    frame_origin_xyz: Point3
    design_outer_bounds_min_xyz: Point3
    design_outer_bounds_max_xyz: Point3
    design_outer_bounds_size_xyz: Point3
    physical_modeled_body_bounds_min_xyz: Point3
    physical_modeled_body_bounds_max_xyz: Point3
    physical_modeled_body_bounds_size_xyz: Point3
    local_bounds_min_xyz: Point3
    local_bounds_max_xyz: Point3
    local_bounds_size_xyz: Point3
    outer_bounds_min_xyz: Point3
    outer_bounds_max_xyz: Point3
    outer_bounds_size_xyz: Point3


@dataclass(frozen=True)
class TxOuterSingleCoilScenePlacement:
    fit_envelope: RealizedSingleCoilFitEnvelope
    scene_children: tuple[Shape, ...]
    angle_deg: float
    frame_origin_xyz: Point3
    design_outer_bounds_min_xyz: Point3
    design_outer_bounds_max_xyz: Point3
    design_outer_bounds_size_xyz: Point3
    physical_modeled_body_bounds_min_xyz: Point3
    physical_modeled_body_bounds_max_xyz: Point3
    physical_modeled_body_bounds_size_xyz: Point3
    physical_modeled_body_canonical_coordinates: CanonicalCoordinates


@dataclass(frozen=True)
class TxRatioDesignOuterPlacement:
    frame_origin_xyz: Point3
    design_outer_bounds_min_xyz: Point3
    design_outer_bounds_max_xyz: Point3
    design_outer_bounds_size_xyz: Point3


def _canonical_from_shape(shape: Shape) -> CanonicalCoordinates:
    bbox = shape.bounding_box()
    min_xyz = (bbox.min.X, bbox.min.Y, bbox.min.Z)
    max_xyz = (bbox.max.X, bbox.max.Y, bbox.max.Z)
    return {
        "frame_origin_xyz": min_xyz,
        "outer_bounds_min_xyz": min_xyz,
        "outer_bounds_max_xyz": max_xyz,
        "outer_bounds_size_xyz": (max_xyz[0] - min_xyz[0], max_xyz[1] - min_xyz[1], max_xyz[2] - min_xyz[2]),
    }


def _canonical_from_scene_children(children: tuple[Shape, ...]) -> CanonicalCoordinates:
    if len(children) == 0:
        raise RuntimeError("type2 modeled scene canonical coordinates require at least one child shape")
    compound = bd.Compound(children=children, label="canonical_bounds")
    return _canonical_from_shape(cast(Shape, compound))


def _single_coil_clearance_blank_body_names(base_scene_children: tuple[Shape, ...]) -> tuple[str, ...]:
    blank_body_names = tuple(shape.label for shape in base_scene_children if "_pcb_l" in shape.label)
    if len(blank_body_names) == 0:
        raise RuntimeError(
            "type2 single-coil ferrite/FR4 clearance requires PCB/FR4 blank bodies "
            f"(base_body_names={tuple(shape.label for shape in base_scene_children)})"
        )
    return blank_body_names


def _single_coil_clearance_tool_body_names(underlay_scene_children: tuple[Shape, ...]) -> tuple[str, ...]:
    tool_body_names = tuple(
        shape.label
        for shape in underlay_scene_children
        if "ferrite" in shape.label or "pet_psa" in shape.label
    )
    if len(tool_body_names) == 0:
        raise RuntimeError(
            "type2 single-coil ferrite/FR4 clearance requires ferrite/PET_PSA tool bodies "
            f"(underlay_body_names={tuple(shape.label for shape in underlay_scene_children)})"
        )
    return tool_body_names


def _apply_single_coil_ferrite_fr4_boolean_clearance(
    *,
    base_scene_children: tuple[Shape, ...],
    underlay_scene_children: tuple[Shape, ...],
    object_id: str,
) -> tuple[tuple[Shape, ...], tuple[Shape, ...]]:
    if len(underlay_scene_children) == 0:
        return base_scene_children, underlay_scene_children
    ordered_scene_children = base_scene_children + underlay_scene_children
    expected_body_names = tuple(shape.label for shape in ordered_scene_children)
    cleared_scene_children = single_coil_scene_children_with_ferrite_pet_psa_clearance(
        scene_children=ordered_scene_children,
        ferrite_tool_labels=_single_coil_clearance_tool_body_names(underlay_scene_children),
        ferrite_tool_group_labels=(),
        pcb_blank_labels=_single_coil_clearance_blank_body_names(base_scene_children),
        context=f"type2.{object_id}.single_coil_ferrite_fr4_clearance",
    )
    actual_body_names = tuple(shape.label for shape in cleared_scene_children)
    if actual_body_names != expected_body_names:
        raise RuntimeError(
            "type2 single-coil ferrite/FR4 clearance must preserve body order and labels "
            f"(object_id={object_id}, expected={expected_body_names}, actual={actual_body_names})"
        )
    base_count = len(base_scene_children)
    return cleared_scene_children[:base_count], cleared_scene_children[base_count:]


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


def _profile_for_modeled_single_coil_role(role: str) -> SingleCoilProfile:
    return profile_for_modeled_role(
        cast(Literal["tx_single_coil", "tx_inner_single_coil", "tx_outer_single_coil", "rx_single_coil"], role)
    )


def _resolve_modeled_single_coil_underlay_repeat_count(
    spec: ModeledSingleCoilSpec,
    *,
    profile: SingleCoilProfile,
    seed: int,
) -> int:
    if profile.role == "tx_outer_single_coil":
        underlay_repeat_count = spec.underlay_repeat_count
        if underlay_repeat_count.is_integer is not True:
            raise RuntimeError("type2 tx_outer_single_coil underlay_repeat_count must be an integer range")
        candidates = _integer_range_candidates(underlay_repeat_count)
        if any(candidate < 0 for candidate in candidates):
            raise RuntimeError(
                "type2 tx_outer_single_coil underlay_repeat_count candidates must be >= 0 "
                f"(actual={candidates})"
            )
        if len(candidates) == 1:
            return candidates[0]
        range_path = "modeled_objects.tx_inner_rect_void_coil.underlay_repeat_count"
        index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
        return candidates[index]
    return resolve_modeled_underlay_repeat_count(spec, seed=seed)


def _resolve_fixed_positive_range_mm(
    range_spec: RangeSpec,
    *,
    context: str,
) -> float:
    candidates = _float_range_candidates(range_spec)
    if len(candidates) != 1 or candidates[0] <= 0.0:
        raise RuntimeError(
            f"{context} must resolve to a single fixed positive value "
            f"(actual={candidates})"
        )
    return candidates[0]


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
        target_min_x = (
            owner_origin_x
            if owner_spec.object_id == "tx_region"
            else owner_origin_x + (owner_size_x - world_size_xyz[0]) / 2.0
        )
        target_world_min_xyz = (
            target_min_x,
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


def _validated_x_position_ratio(*, ratio: float, owner_path: str) -> float:
    if not math.isfinite(ratio):
        raise RuntimeError(f"{owner_path} must resolve to a finite ratio (actual={ratio})")
    if ratio < 0.0 or ratio > 1.0:
        raise RuntimeError(f"{owner_path} must resolve in [0, 1] (actual={ratio})")
    return ratio


def _tx_x_position_ratio(*, spec: ModeledSingleCoilSpec, seed: int) -> float:
    if spec.role not in ("tx_inner_single_coil", "tx_outer_single_coil"):
        raise RuntimeError(f"x_position_ratio is only defined for TX inner/outer roles (actual={spec.role})")
    assert hasattr(spec, "x_position_ratio")
    range_spec = spec.x_position_ratio
    assert isinstance(range_spec, RangeSpec)
    owner_path = f"modeled_objects.{spec.object_id}.x_position_ratio"
    candidates = _float_range_candidates(range_spec)
    if len(candidates) == 0:
        raise RuntimeError(f"No candidates generated for {owner_path}")
    if len(candidates) == 1:
        ratio = candidates[0]
    else:
        index = _resolve_seeded_candidate_index(
            seed=seed,
            range_path=owner_path,
            candidate_count=len(candidates),
        )
        ratio = candidates[index]
    return _validated_x_position_ratio(
        ratio=ratio,
        owner_path=owner_path,
    )


def _single_coil_tx_ratio_design_outer_placement_from_realized(
    *,
    spec: ModeledSingleCoilSpec,
    owner_spec: NonModelBoxSpec,
    realized: RealizedSingleCoilRectVoid,
    local_bounds_min_z: float,
    local_bounds_size_z: float,
    profile: SingleCoilProfile,
    seed: int,
) -> TxRatioDesignOuterPlacement:
    if owner_spec.plane != profile.plane:
        raise RuntimeError(
            "type2 single-coil placement owner plane must match profile plane "
            f"(owner={owner_spec.object_id}, owner_plane={owner_spec.plane}, profile_plane={profile.plane})"
        )
    if profile.plane != "XY":
        raise RuntimeError(f"type2 {profile.role} x_position_ratio placement requires XY plane (actual={profile.plane})")
    local_design_outer_min_xyz = (
        realized.outer_bounds.min_x,
        realized.outer_bounds.min_y,
        local_bounds_min_z,
    )
    local_design_outer_size_xyz = (
        realized.outer_x_mm,
        realized.outer_y_mm,
        local_bounds_size_z,
    )
    world_design_outer_size_xyz = profile.world_size(local_design_outer_size_xyz)
    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if (
        world_design_outer_size_xyz[0] > owner_size_x
        or world_design_outer_size_xyz[1] > owner_size_y
        or world_design_outer_size_xyz[2] > owner_size_z
    ):
        raise RuntimeError(
            f"type2 {profile.role} realized design outer bounds must fit inside {owner_spec.object_id} "
            f"(design_outer_size={world_design_outer_size_xyz}, owner_size={owner_spec.size_xyz})"
        )
    x_position_ratio = _tx_x_position_ratio(spec=spec, seed=seed)
    allowed_center_min_x = owner_origin_x + (world_design_outer_size_xyz[0] / 2.0)
    allowed_center_max_x = owner_origin_x + owner_size_x - (world_design_outer_size_xyz[0] / 2.0)
    target_center_x = allowed_center_min_x + ((allowed_center_max_x - allowed_center_min_x) * x_position_ratio)
    world_design_outer_min_xyz = (
        target_center_x - (world_design_outer_size_xyz[0] / 2.0),
        owner_origin_y + (owner_size_y - world_design_outer_size_xyz[1]) / 2.0,
        owner_origin_z + owner_size_z - world_design_outer_size_xyz[2],
    )
    world_design_outer_max_xyz = (
        world_design_outer_min_xyz[0] + world_design_outer_size_xyz[0],
        world_design_outer_min_xyz[1] + world_design_outer_size_xyz[1],
        world_design_outer_min_xyz[2] + world_design_outer_size_xyz[2],
    )
    world_design_min_delta = profile.world_delta(local_design_outer_min_xyz)
    return TxRatioDesignOuterPlacement(
        frame_origin_xyz=(
            world_design_outer_min_xyz[0] - world_design_min_delta[0],
            world_design_outer_min_xyz[1] - world_design_min_delta[1],
            world_design_outer_min_xyz[2] - world_design_min_delta[2],
        ),
        design_outer_bounds_min_xyz=world_design_outer_min_xyz,
        design_outer_bounds_max_xyz=world_design_outer_max_xyz,
        design_outer_bounds_size_xyz=world_design_outer_size_xyz,
    )


def _single_coil_design_outer_bounds_from_realized(
    *,
    owner_spec: NonModelBoxSpec,
    realized: RealizedSingleCoilRectVoid,
    local_bounds_size_xyz: Point3,
    profile: SingleCoilProfile,
) -> tuple[Point3, Point3, Point3]:
    if owner_spec.plane != profile.plane:
        raise RuntimeError(
            "type2 single-coil design outer bounds owner plane must match profile plane "
            f"(owner={owner_spec.object_id}, owner_plane={owner_spec.plane}, profile_plane={profile.plane})"
        )
    local_design_outer_size_xyz = (
        realized.outer_x_mm,
        realized.outer_y_mm,
        local_bounds_size_xyz[2],
    )
    world_design_outer_size_xyz = profile.world_size(local_design_outer_size_xyz)
    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if (
        world_design_outer_size_xyz[0] > owner_size_x
        or world_design_outer_size_xyz[1] > owner_size_y
        or world_design_outer_size_xyz[2] > owner_size_z
    ):
        raise RuntimeError(
            f"type2 {profile.role} realized design outer bounds must fit inside {owner_spec.object_id} "
            f"(design_outer_size={world_design_outer_size_xyz}, owner_size={owner_spec.size_xyz})"
        )
    if profile.plane == "XY":
        target_min_x = (
            owner_origin_x
            if owner_spec.object_id == "tx_region"
            else owner_origin_x + (owner_size_x - world_design_outer_size_xyz[0]) / 2.0
        )
        world_design_outer_min_xyz = (
            target_min_x,
            owner_origin_y + (owner_size_y - world_design_outer_size_xyz[1]) / 2.0,
            owner_origin_z + owner_size_z - world_design_outer_size_xyz[2],
        )
    else:
        world_design_outer_min_xyz = (
            owner_origin_x + owner_size_x - world_design_outer_size_xyz[0],
            owner_origin_y + (owner_size_y - world_design_outer_size_xyz[1]) / 2.0,
            owner_origin_z,
        )
    world_design_outer_max_xyz = (
        world_design_outer_min_xyz[0] + world_design_outer_size_xyz[0],
        world_design_outer_min_xyz[1] + world_design_outer_size_xyz[1],
        world_design_outer_min_xyz[2] + world_design_outer_size_xyz[2],
    )
    return (world_design_outer_min_xyz, world_design_outer_max_xyz, world_design_outer_size_xyz)


def _scaled_outer_mm_range_from_owner(
    *,
    ratio_range: RangeSpec,
    owner_span_mm: float,
    owner_path: str,
) -> RangeSpec:
    if owner_span_mm <= 0.0:
        raise RuntimeError(f"{owner_path} span must be > 0 for single-coil owner-scaled range (actual={owner_span_mm})")
    return RangeSpec(
        is_integer=False,
        start=ratio_range.start * owner_span_mm,
        end=ratio_range.end * owner_span_mm,
        count=ratio_range.count,
    )


def _spec_with_owner_scaled_outer_ranges(
    spec: ModeledSingleCoilSpec,
    *,
    owner_spec: NonModelBoxSpec,
    profile: SingleCoilProfile,
) -> ModeledSingleCoilSpec:
    if owner_spec.plane != profile.plane:
        raise RuntimeError(
            "type2 single-coil placement owner plane must match profile plane "
            f"(owner={owner_spec.object_id}, owner_plane={owner_spec.plane}, profile_plane={profile.plane})"
        )
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if profile.plane == "XY":
        outer_x_owner_span_mm = owner_size_x
        outer_y_owner_span_mm = owner_size_y
    else:
        outer_x_owner_span_mm = owner_size_y
        outer_y_owner_span_mm = owner_size_z
    return replace(
        spec,
        outer_x_mm=_scaled_outer_mm_range_from_owner(
            ratio_range=spec.outer_x_usage_ratio,
            owner_span_mm=outer_x_owner_span_mm,
            owner_path=f"{owner_spec.object_id}.x",
        ),
        outer_y_mm=_scaled_outer_mm_range_from_owner(
            ratio_range=spec.outer_y_usage_ratio,
            owner_span_mm=outer_y_owner_span_mm,
            owner_path=f"{owner_spec.object_id}.y",
        ),
    )


def resolve_modeled_single_coil_fit_envelope(
    spec: ModeledSingleCoilSpec,
    *,
    owner_spec: NonModelBoxSpec,
    seed: int,
) -> RealizedSingleCoilFitEnvelope:
    profile = _profile_for_modeled_single_coil_role(spec.role)
    with tempfile.TemporaryDirectory(prefix="type2_tx_rect_void_") as temp_dir:
        temp_toml_path = Path(temp_dir) / f"{spec.object_id}.toml"
        owner_scaled_spec = _spec_with_owner_scaled_outer_ranges(
            spec,
            owner_spec=owner_spec,
            profile=profile,
        )
        temp_toml_path.write_text(render_tx_rect_void_toml(owner_scaled_spec), encoding="utf-8")
        tx_rect_void_spec = load_tx_rect_void_spec(temp_toml_path)
        realized = realize_tx_rect_void_spec(tx_rect_void_spec, seed=seed, profile=profile)
    local_boxes = build_tx_rect_void_box_specs(realized, profile=profile)
    local_bounds_min_xyz, local_bounds_max_xyz, local_bounds_size_xyz = modeled_body_bounds_from_boxes(local_boxes)
    if profile.role in ("tx_inner_single_coil", "tx_outer_single_coil"):
        tx_ratio_placement = _single_coil_tx_ratio_design_outer_placement_from_realized(
            spec=spec,
            owner_spec=owner_spec,
            realized=realized,
            local_bounds_min_z=local_bounds_min_xyz[2],
            local_bounds_size_z=local_bounds_size_xyz[2],
            profile=profile,
            seed=seed,
        )
        placement_offset_xyz = tx_ratio_placement.frame_origin_xyz
    else:
        placement_offset_xyz = _single_coil_placement_offset_from_local_bounds(
            owner_spec=owner_spec,
            local_bounds_min_xyz=local_bounds_min_xyz,
            local_size_xyz=local_bounds_size_xyz,
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
    world_bounds_min_xyz, world_bounds_max_xyz, world_bounds_size_xyz = modeled_body_bounds_from_boxes(transformed_boxes)
    if profile.role in ("tx_inner_single_coil", "tx_outer_single_coil"):
        design_outer_bounds_min_xyz = tx_ratio_placement.design_outer_bounds_min_xyz
        design_outer_bounds_max_xyz = tx_ratio_placement.design_outer_bounds_max_xyz
        design_outer_bounds_size_xyz = tx_ratio_placement.design_outer_bounds_size_xyz
    else:
        design_outer_bounds_min_xyz, design_outer_bounds_max_xyz, design_outer_bounds_size_xyz = (
            _single_coil_design_outer_bounds_from_realized(
                owner_spec=owner_spec,
                realized=realized,
                local_bounds_size_xyz=local_bounds_size_xyz,
                profile=profile,
            )
        )
    return RealizedSingleCoilFitEnvelope(
        realized=realized,
        local_boxes=local_boxes,
        transformed_boxes=transformed_boxes,
        frame_origin_xyz=placement_offset_xyz,
        design_outer_bounds_min_xyz=design_outer_bounds_min_xyz,
        design_outer_bounds_max_xyz=design_outer_bounds_max_xyz,
        design_outer_bounds_size_xyz=design_outer_bounds_size_xyz,
        physical_modeled_body_bounds_min_xyz=world_bounds_min_xyz,
        physical_modeled_body_bounds_max_xyz=world_bounds_max_xyz,
        physical_modeled_body_bounds_size_xyz=world_bounds_size_xyz,
        local_bounds_min_xyz=local_bounds_min_xyz,
        local_bounds_max_xyz=local_bounds_max_xyz,
        local_bounds_size_xyz=local_bounds_size_xyz,
        outer_bounds_min_xyz=design_outer_bounds_min_xyz,
        outer_bounds_max_xyz=design_outer_bounds_max_xyz,
        outer_bounds_size_xyz=design_outer_bounds_size_xyz,
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


def _rotate_shape_about_world_y_then_move(
    shape: Shape,
    *,
    angle_deg: float,
    frame_origin_xyz: Point3,
) -> Shape:
    if abs(angle_deg) <= 1e-12:
        rotated_shape = shape
    else:
        rotated_shape = cast(Shape, shape.rotate(bd.Axis((0.0, 0.0, 0.0), (0.0, 1.0, 0.0)), angle_deg))
    moved_shape = cast(Shape, rotated_shape.moved(bd.Location(frame_origin_xyz)))
    moved_shape.label = shape.label
    return moved_shape


def _rotate_point_about_world_y_then_move(
    point_xyz: Point3,
    *,
    angle_deg: float,
    frame_origin_xyz: Point3,
) -> Point3:
    angle_rad = math.radians(angle_deg)
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    return (
        (point_xyz[0] * cos_theta) + (point_xyz[2] * sin_theta) + frame_origin_xyz[0],
        point_xyz[1] + frame_origin_xyz[1],
        (-point_xyz[0] * sin_theta) + (point_xyz[2] * cos_theta) + frame_origin_xyz[2],
    )


def _clip_shape_to_world_z_top(
    shape: Shape,
    *,
    z_top: float,
    label: str,
) -> Shape:
    if not math.isfinite(z_top):
        raise RuntimeError(f"type2 tx outer world clipping top must be finite (label={label}, actual={z_top})")
    bbox = shape.bounding_box()
    min_xyz = (bbox.min.X, bbox.min.Y, bbox.min.Z)
    max_xyz = (bbox.max.X, bbox.max.Y, z_top)
    if max_xyz[0] <= min_xyz[0] or max_xyz[1] <= min_xyz[1] or max_xyz[2] <= min_xyz[2]:
        raise RuntimeError(
            "type2 tx outer world clipping box must be positive "
            f"(label={label}, min_xyz={min_xyz}, max_xyz={max_xyz})"
        )
    clip_box = bd.Box(
        max_xyz[0] - min_xyz[0],
        max_xyz[1] - min_xyz[1],
        max_xyz[2] - min_xyz[2],
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    ).moved(bd.Location(min_xyz))
    clipped_shape = cast(Shape, shape.intersect(clip_box))
    solids = tuple(clipped_shape.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "type2 tx outer world-clipped passive body must contain exactly one solid "
            f"(label={label}, solid_count={len(solids)})"
        )
    clipped_solid = solids[0]
    clipped_solid.label = label
    return clipped_solid


def _transform_outer_terminal_sheet_vertices_xyz(
    *,
    port_sheet_vertices_xyz: tuple[Point3, ...],
    angle_deg: float,
    frame_origin_xyz: Point3,
) -> tuple[Point3, Point3, Point3, Point3]:
    rotated_and_moved_vertices = tuple(
        _rotate_point_about_world_y_then_move(
            point_xyz=point_xyz,
            angle_deg=angle_deg,
            frame_origin_xyz=frame_origin_xyz,
        )
        for point_xyz in port_sheet_vertices_xyz
    )
    if len(rotated_and_moved_vertices) != 4:
        raise RuntimeError(
            "type2 tx outer terminal metadata requires exactly four port-sheet vertices "
            f"(actual={len(rotated_and_moved_vertices)})"
        )
    return cast(tuple[Point3, Point3, Point3, Point3], rotated_and_moved_vertices)


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
    if profile.role in TX_PARALLEL_SINGLE_COIL_ROLES and start_bus_matches and end_bus_matches:
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
    if profile.role in TX_PARALLEL_SINGLE_COIL_ROLES:
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
    if profile.role in TX_PARALLEL_SINGLE_COIL_ROLES:
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
    return (
        first_diagonal_start_world_xyz,
        second_diagonal_start_world_xyz,
        second_diagonal_end_world_xyz,
        first_diagonal_end_world_xyz,
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


def _tx_outer_virtual_owner_spec(
    *,
    owner_spec: NonModelBoxSpec,
    top_edge_length_mm: float,
    y_span_mm: float,
) -> NonModelBoxSpec:
    if top_edge_length_mm <= 0.0 or not math.isfinite(top_edge_length_mm):
        raise RuntimeError(f"tx_outer_single_coil top edge length must be finite and > 0 (actual={top_edge_length_mm})")
    if y_span_mm <= 0.0 or not math.isfinite(y_span_mm):
        raise RuntimeError(f"tx_outer_single_coil y span must be finite and > 0 (actual={y_span_mm})")
    return replace(
        owner_spec,
        origin_xyz=(0.0, 0.0, -owner_spec.size_xyz[2]),
        size_xyz=(top_edge_length_mm, y_span_mm, owner_spec.size_xyz[2]),
    )


def resolve_tx_outer_single_coil_fit_envelope(
    spec: ModeledSingleCoilSpec,
    *,
    owner_spec: NonModelBoxSpec,
    seed: int,
) -> RealizedSingleCoilFitEnvelope:
    from peetsfea.type2_non_model_scene import require_tx_outer_region_prism_provenance
    from peetsfea.type2_non_model_scene import resolve_tx_outer_region_tilt_frame

    profile = _profile_for_modeled_single_coil_role(spec.role)
    if profile.role != "tx_outer_single_coil":
        raise RuntimeError(f"outer tilted fit-envelope helper requires tx_outer_single_coil (actual={profile.role})")
    provenance = require_tx_outer_region_prism_provenance(object_id="tx_outer_region")
    tilt_frame = resolve_tx_outer_region_tilt_frame(provenance=provenance)
    top_inner_start_xyz = provenance["top_inner_start_xyz"]
    top_inner_end_xyz = provenance["top_inner_end_xyz"]
    y_span_mm = top_inner_end_xyz[1] - top_inner_start_xyz[1]
    if y_span_mm <= 0.0:
        raise RuntimeError(
            "tx_outer_single_coil tilt frame requires positive semantic Y span "
            f"(start={top_inner_start_xyz}, end={top_inner_end_xyz})"
        )
    virtual_owner_spec = _tx_outer_virtual_owner_spec(
        owner_spec=owner_spec,
        top_edge_length_mm=tilt_frame.top_edge_length_xyz,
        y_span_mm=y_span_mm,
    )
    return resolve_modeled_single_coil_fit_envelope(spec, owner_spec=virtual_owner_spec, seed=seed)


def _world_aabb_from_tx_outer_prism_local_bounds(
    *,
    min_xyz: Point3,
    max_xyz: Point3,
    angle_deg: float,
    frame_origin_xyz: Point3,
) -> tuple[Point3, Point3, Point3]:
    angle_rad = math.radians(angle_deg)
    sin_angle = math.sin(angle_rad)
    cos_angle = math.cos(angle_rad)
    frame_origin_x, frame_origin_y, frame_origin_z = frame_origin_xyz

    def _to_world(point: Point3) -> Point3:
        point_x, point_y, point_z = point
        return (
            (point_x * cos_angle) + (point_z * sin_angle) + frame_origin_x,
            point_y + frame_origin_y,
            (-point_x * sin_angle) + (point_z * cos_angle) + frame_origin_z,
        )

    min_x, min_y, min_z = min_xyz
    max_x, max_y, max_z = max_xyz
    points = tuple(
        _to_world(point)
        for point in (
            (min_x, min_y, min_z),
            (min_x, min_y, max_z),
            (min_x, max_y, min_z),
            (min_x, max_y, max_z),
            (max_x, min_y, min_z),
            (max_x, min_y, max_z),
            (max_x, max_y, min_z),
            (max_x, max_y, max_z),
        )
    )
    world_min_xyz = (
        min(point[0] for point in points),
        min(point[1] for point in points),
        min(point[2] for point in points),
    )
    world_max_xyz = (
        max(point[0] for point in points),
        max(point[1] for point in points),
        max(point[2] for point in points),
    )
    world_size_xyz = (
        world_max_xyz[0] - world_min_xyz[0],
        world_max_xyz[1] - world_min_xyz[1],
        world_max_xyz[2] - world_min_xyz[2],
    )
    return (world_min_xyz, world_max_xyz, world_size_xyz)


def resolve_tx_outer_single_coil_scene_placement(
    spec: ModeledSingleCoilSpec,
    *,
    owner_spec: NonModelBoxSpec,
    seed: int,
) -> TxOuterSingleCoilScenePlacement:
    from peetsfea.type2_non_model_scene import require_tx_outer_region_prism_provenance
    from peetsfea.type2_non_model_scene import resolve_tx_outer_region_tilt_frame

    profile = _profile_for_modeled_single_coil_role(spec.role)
    if profile.role != "tx_outer_single_coil":
        raise RuntimeError(
            "tx_outer_single_coil scene placement resolver requires tx_outer_single_coil "
            f"(actual={profile.role})"
        )
    provenance = require_tx_outer_region_prism_provenance(object_id="tx_outer_region")
    tilt_frame = resolve_tx_outer_region_tilt_frame(provenance=provenance)
    fit_envelope = resolve_tx_outer_single_coil_fit_envelope(spec, owner_spec=owner_spec, seed=seed)
    virtual_modeled_scene = build_tx_rect_void_step_scene(
        fit_envelope.realized,
        fit_envelope.transformed_boxes,
        profile=profile,
        frame_origin_xyz=fit_envelope.frame_origin_xyz,
    )
    port_sheet_label = port_sheet_label_for_profile(profile)
    virtual_base_scene_children = tuple(shape for shape in virtual_modeled_scene.children if shape.label != port_sheet_label)
    if len(virtual_base_scene_children) == 0:
        raise RuntimeError(f"type2 modeled scene must expose child bodies: {spec.object_id}")
    angle_deg = math.degrees(
        math.atan2(-tilt_frame.local_x_axis_xyz[2], tilt_frame.local_x_axis_xyz[0])
    )
    scene_children = tuple(
        _rotate_shape_about_world_y_then_move(
            cast(Shape, shape),
            angle_deg=angle_deg,
            frame_origin_xyz=tilt_frame.frame_origin_xyz,
        )
        for shape in virtual_base_scene_children
    )
    design_outer_bounds_min_xyz, design_outer_bounds_max_xyz, design_outer_bounds_size_xyz = (
        _world_aabb_from_tx_outer_prism_local_bounds(
            min_xyz=fit_envelope.design_outer_bounds_min_xyz,
            max_xyz=fit_envelope.design_outer_bounds_max_xyz,
            angle_deg=angle_deg,
            frame_origin_xyz=tilt_frame.frame_origin_xyz,
        )
    )
    physical_canonical_coordinates = _canonical_from_scene_children(scene_children)
    physical_modeled_body_bounds_min_xyz = cast(Point3, physical_canonical_coordinates["outer_bounds_min_xyz"])
    physical_modeled_body_bounds_max_xyz = cast(Point3, physical_canonical_coordinates["outer_bounds_max_xyz"])
    physical_modeled_body_bounds_size_xyz = cast(
        Point3,
        physical_canonical_coordinates["outer_bounds_size_xyz"],
    )
    return TxOuterSingleCoilScenePlacement(
        fit_envelope=fit_envelope,
        scene_children=scene_children,
        angle_deg=angle_deg,
        frame_origin_xyz=tilt_frame.frame_origin_xyz,
        design_outer_bounds_min_xyz=design_outer_bounds_min_xyz,
        design_outer_bounds_max_xyz=design_outer_bounds_max_xyz,
        design_outer_bounds_size_xyz=design_outer_bounds_size_xyz,
        physical_modeled_body_bounds_min_xyz=physical_modeled_body_bounds_min_xyz,
        physical_modeled_body_bounds_max_xyz=physical_modeled_body_bounds_max_xyz,
        physical_modeled_body_bounds_size_xyz=physical_modeled_body_bounds_size_xyz,
        physical_modeled_body_canonical_coordinates=physical_canonical_coordinates,
    )


def _build_tx_outer_single_coil_scene_data(
    spec: ModeledSingleCoilSpec,
    *,
    owner_spec: NonModelBoxSpec,
    tx_region_max_z: float,
    seed: int,
) -> tuple[tuple[Shape, ...], ModeledObjectSceneData]:
    profile = _profile_for_modeled_single_coil_role(spec.role)
    if profile.role != "tx_outer_single_coil":
        raise RuntimeError(f"outer tilted scene builder requires tx_outer_single_coil (actual={profile.role})")
    placement = resolve_tx_outer_single_coil_scene_placement(
        spec,
        owner_spec=owner_spec,
        seed=seed,
    )
    if not isinstance(spec, ModeledTxOuterSingleCoilSpec):
        raise RuntimeError(f"type2 tx outer void stack requires tx outer spec (object_id={spec.object_id})")
    fit_envelope = placement.fit_envelope
    centerline = build_tx_rect_void_centerline(fit_envelope.realized)
    base_scene_children = placement.scene_children
    underlay_repeat_count = _resolve_modeled_single_coil_underlay_repeat_count(spec, profile=profile, seed=seed)
    if underlay_repeat_count > 0:
        pet_psa_thickness_mm = _resolve_fixed_positive_range_mm(
            spec.underlay_pet_psa_thickness_mm,
            context="tx_outer_single_coil.underlay_pet_psa_thickness_mm",
        )
        ferrite_thickness_mm = _resolve_fixed_positive_range_mm(
            spec.underlay_ferrite_thickness_mm,
            context="tx_outer_single_coil.underlay_ferrite_thickness_mm",
        )
        void_bounds = fit_envelope.realized.void_bounds
        frame_origin_x, frame_origin_y, _frame_origin_z = fit_envelope.frame_origin_xyz
        raw_overshoot_mm = pet_psa_thickness_mm + ferrite_thickness_mm
        angle_rad = math.radians(placement.angle_deg)
        cos_theta = math.cos(angle_rad)
        sin_theta = math.sin(angle_rad)
        if cos_theta <= 0.0:
            raise RuntimeError(
                "type2 tx outer void stack requires positive local-Z world-Z projection "
                f"(object_id={spec.object_id}, angle_deg={placement.angle_deg})"
            )
        local_void_min_x = frame_origin_x + void_bounds.min_x
        local_void_max_x = frame_origin_x + void_bounds.max_x
        local_z_top_candidates = (
            (tx_region_max_z - placement.frame_origin_xyz[2] + (local_void_min_x * sin_theta)) / cos_theta,
            (tx_region_max_z - placement.frame_origin_xyz[2] + (local_void_max_x * sin_theta)) / cos_theta,
        )
        local_z_top = max(local_z_top_candidates) + raw_overshoot_mm
        virtual_void_stack_descriptor = resolve_tx_inner_single_coil_void_stack_placement_descriptor(
            void_min_x=local_void_min_x,
            void_max_x=local_void_max_x,
            void_min_y=frame_origin_y + void_bounds.min_y,
            void_max_y=frame_origin_y + void_bounds.max_y,
            z_bottom=fit_envelope.design_outer_bounds_min_xyz[2],
            z_top=local_z_top,
            pet_psa_thickness_mm=pet_psa_thickness_mm,
            ferrite_thickness_mm=ferrite_thickness_mm,
        )
        raw_virtual_void_stack_children = build_tx_outer_single_coil_void_stack_shapes(
            virtual_void_stack_descriptor
        )
        world_void_stack_children = tuple(
            _clip_shape_to_world_z_top(
                _rotate_shape_about_world_y_then_move(
                    cast(Shape, shape),
                    angle_deg=placement.angle_deg,
                    frame_origin_xyz=placement.frame_origin_xyz,
                ),
                z_top=tx_region_max_z,
                label=shape.label,
            )
            for shape in raw_virtual_void_stack_children
        )
        virtual_underlay_descriptor = resolve_tx_outer_single_coil_underlay_placement_descriptor(
            actual_region_min_xyz=fit_envelope.design_outer_bounds_min_xyz,
            actual_region_size_xyz=fit_envelope.design_outer_bounds_size_xyz,
            repeat_count=underlay_repeat_count,
            pet_psa_thickness_mm=pet_psa_thickness_mm,
            ferrite_thickness_mm=ferrite_thickness_mm,
            owner_thickness_mm=owner_spec.size_xyz[2],
        )
        virtual_bottom_underlay_children = build_tx_outer_single_coil_underlay_shapes(
            virtual_underlay_descriptor
        )
        bottom_underlay_scene_children = tuple(
            _rotate_shape_about_world_y_then_move(
                cast(Shape, shape),
                angle_deg=placement.angle_deg,
                frame_origin_xyz=placement.frame_origin_xyz,
            )
            for shape in virtual_bottom_underlay_children
        )
        underlay_scene_children = world_void_stack_children + bottom_underlay_scene_children
    else:
        underlay_scene_children = ()
    expected_exported_body_groups = single_coil_expected_ferrite_groups(
        role="tx_outer_single_coil",
        underlay_scene_children=underlay_scene_children,
    )
    scene_children = single_coil_scene_children_with_grouped_ferrite_family(
        base_scene_children=base_scene_children,
        underlay_scene_children=underlay_scene_children,
        expected_exported_body_groups=expected_exported_body_groups,
    )
    canonical_coordinates: dict[str, object] = dict(placement.physical_modeled_body_canonical_coordinates)
    virtual_canonical = _modeled_canonical_coordinates(
        transformed_boxes=fit_envelope.transformed_boxes,
        profile=profile,
        frame_origin_xyz=fit_envelope.frame_origin_xyz,
    )
    canonical_coordinates["pcb_layer_z_positions_mm"] = virtual_canonical["pcb_layer_z_positions_mm"]
    canonical_coordinates["copper_layer_z_positions_mm"] = virtual_canonical["copper_layer_z_positions_mm"]
    owner_max_x = owner_spec.origin_xyz[0] + owner_spec.size_xyz[0]
    owner_min_z = owner_spec.origin_xyz[2]
    bounds_min_xyz = cast(Point3, canonical_coordinates["outer_bounds_min_xyz"])
    bounds_max_xyz = cast(Point3, canonical_coordinates["outer_bounds_max_xyz"])
    max_world_x_protrusion_mm = max(0.0, bounds_max_xyz[0] - owner_max_x)
    max_world_z_underhang_mm = max(0.0, owner_min_z - bounds_min_xyz[2])
    canonical_coordinates["outer_tilt_metadata"] = {
        "max_world_x_protrusion_mm": max_world_x_protrusion_mm,
        "max_world_z_underhang_mm": max_world_z_underhang_mm,
    }
    if underlay_repeat_count > 0:
        canonical_coordinates["outer_void_stack_raw_overshoot_mm"] = raw_overshoot_mm
    terminal_metadata = modeled_terminal_metadata(
        terminal_path=fit_envelope.realized.terminal_path,
        centerline=centerline,
        profile=profile,
        frame_origin_xyz=fit_envelope.frame_origin_xyz,
        transformed_boxes=fit_envelope.transformed_boxes,
    )
    raw_port_sheet_vertices_xyz = terminal_metadata["port_sheet_vertices_xyz"]
    if not isinstance(raw_port_sheet_vertices_xyz, (tuple, list)):
        raise RuntimeError(
            "type2 tx outer terminal metadata requires 4 vertices for port_sheet_vertices_xyz "
            f"(actual={type(raw_port_sheet_vertices_xyz).__name__})"
        )
    if len(raw_port_sheet_vertices_xyz) != 4:
        raise RuntimeError(
            "type2 tx outer terminal metadata requires exactly four port_sheet_vertices_xyz points "
            f"(actual={len(raw_port_sheet_vertices_xyz)})"
        )
    first_point, second_point, third_point, fourth_point = raw_port_sheet_vertices_xyz
    outer_port_sheet_vertices_xyz = _transform_outer_terminal_sheet_vertices_xyz(
        port_sheet_vertices_xyz=cast(
            tuple[Point3, Point3, Point3, Point3],
            (first_point, second_point, third_point, fourth_point),
        ),
        angle_deg=placement.angle_deg,
        frame_origin_xyz=placement.frame_origin_xyz,
    )
    terminal_metadata["port_sheet_vertices_xyz"] = outer_port_sheet_vertices_xyz
    expected_exported_body_names = tuple(shape.label for shape in (base_scene_children + underlay_scene_children))
    if len(set(expected_exported_body_names)) != len(expected_exported_body_names):
        raise RuntimeError(
            "type2 modeled scene body names must be unique "
            f"(object_id={spec.object_id}, names={expected_exported_body_names})"
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


def build_modeled_single_coil_scene_data(
    spec: ModeledSingleCoilSpec,
    *,
    owner_spec: NonModelBoxSpec,
    tx_region_max_z: float,
    seed: int,
) -> tuple[tuple[Shape, ...], ModeledObjectSceneData]:
    profile = _profile_for_modeled_single_coil_role(spec.role)
    if not math.isfinite(tx_region_max_z):
        raise RuntimeError(f"type2 single-coil scene requires finite tx_region_max_z (actual={tx_region_max_z})")
    if profile.role == "tx_outer_single_coil":
        return _build_tx_outer_single_coil_scene_data(
            spec,
            owner_spec=owner_spec,
            tx_region_max_z=tx_region_max_z,
            seed=seed,
        )
    fit_envelope = resolve_modeled_single_coil_fit_envelope(spec, owner_spec=owner_spec, seed=seed)
    centerline = build_tx_rect_void_centerline(fit_envelope.realized)
    modeled_scene = build_tx_rect_void_step_scene(
        fit_envelope.realized,
        fit_envelope.transformed_boxes,
        profile=profile,
        frame_origin_xyz=fit_envelope.frame_origin_xyz,
    )
    existing_scene_children = tuple(modeled_scene.children)
    port_sheet_label = port_sheet_label_for_profile(profile)
    base_scene_children = tuple(shape for shape in existing_scene_children if shape.label != port_sheet_label)
    if len(base_scene_children) == 0:
        raise RuntimeError(f"type2 modeled scene must expose child bodies: {spec.object_id}")
    underlay_repeat_count = _resolve_modeled_single_coil_underlay_repeat_count(spec, profile=profile, seed=seed)
    if profile.role == "tx_single_coil":
        if cast(Literal["XY", "YZ"], profile.plane) != "XY":
            raise RuntimeError(f"type2 tx underlay requires XY modeled plane (actual={profile.plane})")
        if not isinstance(spec, ModeledTxSingleCoilSpec):
            raise RuntimeError(f"type2 tx underlay gap requires tx modeled spec (object_id={spec.object_id})")
        if underlay_repeat_count > 0:
            tx_underlay_descriptor = resolve_tx_underlay_placement_descriptor(
                owner_spec=owner_spec,
                modeled_min_z=fit_envelope.physical_modeled_body_bounds_min_xyz[2],
                modeled_max_x=fit_envelope.physical_modeled_body_bounds_max_xyz[0],
                repeat_count=underlay_repeat_count,
                gap_mm=resolve_modeled_underlay_gap_mm(spec, seed=seed),
            )
            # TX floor-parallel underlay is intentionally omitted from exported scene bodies.
            # The placement descriptor still owns the wall-stack envelope below the coil.
            wall_underlay_scene_children = (
                build_tx_wall_parallel_scene_shapes(tx_underlay_descriptor)
                if resolve_modeled_wall_parallel_stack_present(spec, seed=seed)
                else ()
            )
            underlay_scene_children = wall_underlay_scene_children
        else:
            underlay_scene_children = ()
    elif profile.role == "tx_inner_single_coil":
        if not isinstance(spec, ModeledTxInnerSingleCoilSpec):
            raise RuntimeError(f"type2 tx inner underlay requires tx inner spec (object_id={spec.object_id})")
        if underlay_repeat_count > 0:
            pet_psa_thickness_mm = resolve_modeled_tx_inner_underlay_pet_psa_thickness_mm(
                spec,
                seed=seed,
            )
            ferrite_thickness_mm = resolve_modeled_tx_inner_underlay_ferrite_thickness_mm(
                spec,
                seed=seed,
            )
            tx_inner_underlay_descriptor = resolve_tx_inner_single_coil_underlay_placement_descriptor(
                owner_spec=owner_spec,
                actual_region_min_xyz=fit_envelope.outer_bounds_min_xyz,
                actual_region_size_xyz=fit_envelope.outer_bounds_size_xyz,
                repeat_count=underlay_repeat_count,
                pet_psa_thickness_mm=pet_psa_thickness_mm,
                ferrite_thickness_mm=ferrite_thickness_mm,
            )
            void_bounds = fit_envelope.realized.void_bounds
            frame_origin_x, frame_origin_y, _frame_origin_z = fit_envelope.frame_origin_xyz
            tx_inner_void_stack_descriptor = resolve_tx_inner_single_coil_void_stack_placement_descriptor(
                void_min_x=frame_origin_x + void_bounds.min_x,
                void_max_x=frame_origin_x + void_bounds.max_x,
                void_min_y=frame_origin_y + void_bounds.min_y,
                void_max_y=frame_origin_y + void_bounds.max_y,
                z_bottom=fit_envelope.outer_bounds_min_xyz[2],
                z_top=tx_region_max_z,
                pet_psa_thickness_mm=pet_psa_thickness_mm,
                ferrite_thickness_mm=ferrite_thickness_mm,
            )
            underlay_scene_children = build_tx_inner_single_coil_underlay_shapes(
                tx_inner_underlay_descriptor
            ) + build_tx_inner_single_coil_void_stack_shapes(tx_inner_void_stack_descriptor)
        else:
            underlay_scene_children = ()
    elif profile.role == "tx_outer_single_coil":
        if underlay_repeat_count != 0:
            raise RuntimeError(
                f"type2 {profile.role} underlay repeat count must remain zero (actual={underlay_repeat_count})"
            )
        underlay_scene_children = ()
    else:
        underlay_scene_children = (
            build_rx_underlay_scene_shapes(
                owner_spec=owner_spec,
                repeat_count=underlay_repeat_count,
                modeled_bounds_min_xyz=fit_envelope.physical_modeled_body_bounds_min_xyz,
                modeled_bounds_max_xyz=fit_envelope.physical_modeled_body_bounds_max_xyz,
            )
            if underlay_repeat_count > 0
            else ()
        )
    base_scene_children, underlay_scene_children = _apply_single_coil_ferrite_fr4_boolean_clearance(
        base_scene_children=base_scene_children,
        underlay_scene_children=underlay_scene_children,
        object_id=spec.object_id,
    )
    expected_exported_body_names = tuple(shape.label for shape in (base_scene_children + underlay_scene_children))
    if len(set(expected_exported_body_names)) != len(expected_exported_body_names):
        raise RuntimeError(
            "type2 modeled scene body names must be unique "
            f"(object_id={spec.object_id}, names={expected_exported_body_names})"
        )
    modeled_role = cast(Literal["tx_single_coil", "tx_inner_single_coil", "rx_single_coil"], profile.role)
    expected_exported_body_groups = single_coil_expected_ferrite_groups(
        role=modeled_role,
        underlay_scene_children=underlay_scene_children,
    )
    scene_children = single_coil_scene_children_with_grouped_ferrite_family(
        base_scene_children=base_scene_children,
        underlay_scene_children=underlay_scene_children,
        expected_exported_body_groups=expected_exported_body_groups,
    )
    canonical_coordinates = _modeled_canonical_coordinates(
        transformed_boxes=fit_envelope.transformed_boxes,
        profile=profile,
        frame_origin_xyz=fit_envelope.frame_origin_xyz,
    )
    terminal_metadata = modeled_terminal_metadata(
        terminal_path=fit_envelope.realized.terminal_path,
        centerline=centerline,
        profile=profile,
        frame_origin_xyz=fit_envelope.frame_origin_xyz,
        transformed_boxes=fit_envelope.transformed_boxes,
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


__all__ = [
    "RealizedSingleCoilFitEnvelope",
    "TxOuterSingleCoilScenePlacement",
    "build_modeled_single_coil_scene_data",
    "resolve_modeled_single_coil_fit_envelope",
    "resolve_tx_outer_single_coil_scene_placement",
    "resolve_tx_outer_single_coil_fit_envelope",
    "single_coil_placement_offset",
]

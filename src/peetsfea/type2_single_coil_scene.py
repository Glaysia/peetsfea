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
from peetsfea.tx_rect_void import build_tx_rect_void_box_specs
from peetsfea.tx_rect_void import build_tx_rect_void_step_scene
from peetsfea.tx_rect_void import local_central_void_corridor_y_bounds
from peetsfea.tx_rect_void import load_tx_rect_void_spec
from peetsfea.tx_rect_void import modeled_body_bounds_from_boxes
from peetsfea.tx_rect_void import profile_for_modeled_role
from peetsfea.tx_rect_void import realize_tx_rect_void_spec
from peetsfea.type2_single_coil_underlay import build_rx_underlay_scene_shapes
from peetsfea.type2_single_coil_underlay import build_rx_single_coil_void_stack_shapes
from peetsfea.type2_single_coil_underlay import build_tx_wall_parallel_scene_shapes
from peetsfea.type2_single_coil_underlay import build_tx_inner_single_coil_underlay_shapes
from peetsfea.type2_single_coil_underlay import build_tx_inner_single_coil_void_stack_shapes
from peetsfea.type2_single_coil_underlay import build_tx_outer_single_coil_underlay_shapes
from peetsfea.type2_single_coil_underlay import build_tx_outer_single_coil_void_stack_shapes
from peetsfea.type2_single_coil_underlay import resolve_tx_inner_single_coil_underlay_placement_descriptor
from peetsfea.type2_single_coil_underlay import resolve_tx_inner_single_coil_void_stack_placement_descriptor
from peetsfea.type2_single_coil_underlay import resolve_tx_outer_single_coil_underlay_placement_descriptor
from peetsfea.type2_single_coil_underlay import resolve_tx_underlay_placement_descriptor
from peetsfea.type2_single_coil_underlay import resolve_rx_single_coil_void_stack_placement_descriptor
from peetsfea.type2_single_coil_underlay import single_coil_expected_ferrite_groups
from peetsfea.type2_single_coil_underlay import single_coil_scene_children_with_ferrite_pet_psa_clearance
from peetsfea.type2_single_coil_underlay import single_coil_scene_children_with_grouped_ferrite_family
from peetsfea.type2_single_coil_ports import modeled_terminal_metadata
from peetsfea.type2_single_coil_ports import port_sheet_label_for_profile
from peetsfea.type2_step_ledger import CanonicalCoordinates
from peetsfea.type2_step_ledger import ModeledObjectSceneData
from peetsfea.type2_step_spec import ModeledSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import Point3
from peetsfea.type2_step_spec import render_tx_rect_void_toml
from peetsfea.type2_step_spec import resolve_modeled_single_coil_void_stack_present
from peetsfea.type2_step_spec import resolve_modeled_underlay_gap_mm
from peetsfea.type2_step_spec import resolve_modeled_underlay_repeat_count
from peetsfea.type2_step_spec import resolve_modeled_tx_inner_void_stack_present
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


def _exported_body_canonical_coordinates(
    *,
    scene_children: tuple[Shape, ...],
    expected_exported_body_names: tuple[str, ...],
    object_id: str,
) -> CanonicalCoordinates:
    if len(expected_exported_body_names) == 0:
        raise RuntimeError(f"type2 modeled scene requires expected exported body names (object_id={object_id})")
    if len(set(expected_exported_body_names)) != len(expected_exported_body_names):
        raise RuntimeError(
            "type2 modeled scene expected exported body names must be unique "
            f"(object_id={object_id}, names={expected_exported_body_names})"
        )
    expected_name_set = set(expected_exported_body_names)
    selected_shapes_by_label: dict[str, Shape] = {}
    unexpected_leaf_labels: list[str] = []
    for scene_child in scene_children:
        scene_child_label = scene_child.label
        if scene_child_label in expected_name_set:
            if scene_child_label in selected_shapes_by_label:
                raise RuntimeError(
                    "type2 exported body canonical coordinates found duplicate top-level body label "
                    f"(object_id={object_id}, label={scene_child_label})"
                )
            selected_shapes_by_label[scene_child_label] = scene_child
            continue
        group_children = tuple(scene_child.children)
        if len(group_children) == 0:
            unexpected_leaf_labels.append(scene_child_label)
            continue
        for group_child in group_children:
            group_child_label = group_child.label
            if group_child_label not in expected_name_set:
                unexpected_leaf_labels.append(group_child_label)
                continue
            if group_child_label in selected_shapes_by_label:
                raise RuntimeError(
                    "type2 exported body canonical coordinates found duplicate grouped body label "
                    f"(object_id={object_id}, label={group_child_label}, group={scene_child_label})"
                )
            selected_shapes_by_label[group_child_label] = cast(Shape, group_child)
    if len(unexpected_leaf_labels) != 0:
        raise RuntimeError(
            "type2 exported body canonical coordinates found shapes outside expected exported body names "
            f"(object_id={object_id}, unexpected={tuple(unexpected_leaf_labels)}, "
            f"expected={expected_exported_body_names})"
        )
    selected_labels = tuple(selected_shapes_by_label)
    if selected_labels != expected_exported_body_names:
        missing_labels = tuple(label for label in expected_exported_body_names if label not in selected_shapes_by_label)
        raise RuntimeError(
            "type2 exported body canonical coordinates must resolve every expected body in order "
            f"(object_id={object_id}, expected={expected_exported_body_names}, "
            f"selected={selected_labels}, missing={missing_labels})"
        )
    return _canonical_from_scene_children(tuple(selected_shapes_by_label[label] for label in expected_exported_body_names))


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
    local_bounds_min_xyz: Point3,
    local_bounds_size_xyz: Point3,
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
    del realized
    world_design_outer_size_xyz = profile.world_size(local_bounds_size_xyz)
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
    world_design_min_delta = profile.world_delta(local_bounds_min_xyz)
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


def _single_coil_tx_inner_design_outer_placement_from_realized(
    *,
    spec: ModeledSingleCoilSpec,
    owner_spec: NonModelBoxSpec,
    realized: RealizedSingleCoilRectVoid,
    local_bounds_min_xyz: Point3,
    local_bounds_size_xyz: Point3,
    profile: SingleCoilProfile,
) -> TxRatioDesignOuterPlacement:
    if spec.role != "tx_inner_single_coil":
        raise RuntimeError(f"TX inner lower-X placement requires tx_inner_single_coil role (actual={spec.role})")
    if owner_spec.plane != profile.plane:
        raise RuntimeError(
            "type2 tx inner placement owner plane must match profile plane "
            f"(owner={owner_spec.object_id}, owner_plane={owner_spec.plane}, profile_plane={profile.plane})"
        )
    if profile.plane != "XY":
        raise RuntimeError(f"type2 {profile.role} lower-X placement requires XY plane (actual={profile.plane})")
    del realized
    world_design_outer_size_xyz = profile.world_size(local_bounds_size_xyz)
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
    world_design_outer_min_xyz = (
        owner_origin_x,
        owner_origin_y + (owner_size_y - world_design_outer_size_xyz[1]) / 2.0,
        owner_origin_z + owner_size_z - world_design_outer_size_xyz[2],
    )
    world_design_outer_max_xyz = (
        world_design_outer_min_xyz[0] + world_design_outer_size_xyz[0],
        world_design_outer_min_xyz[1] + world_design_outer_size_xyz[1],
        world_design_outer_min_xyz[2] + world_design_outer_size_xyz[2],
    )
    world_design_min_delta = profile.world_delta(local_bounds_min_xyz)
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
    assert hasattr(spec, "x_ratio")
    raw_x_ratio = object.__getattribute__(spec, "x_ratio")
    assert isinstance(raw_x_ratio, RangeSpec)
    assert hasattr(spec, "y_ratio")
    raw_y_ratio = object.__getattribute__(spec, "y_ratio")
    assert isinstance(raw_y_ratio, RangeSpec)
    return replace(
        spec,
        outer_x_mm=_scaled_outer_mm_range_from_owner(
            ratio_range=raw_x_ratio,
            owner_span_mm=outer_x_owner_span_mm,
            owner_path=f"{owner_spec.object_id}.x",
        ),
        outer_y_mm=_scaled_outer_mm_range_from_owner(
            ratio_range=raw_y_ratio,
            owner_span_mm=outer_y_owner_span_mm,
            owner_path=f"{owner_spec.object_id}.y",
        ),
    )


def _render_core_tx_rect_void_toml_for_scene(spec: ModeledSingleCoilSpec) -> str:
    rendered_toml = render_tx_rect_void_toml(spec)
    active_void_factor_header = "[tx_coil.void_factor]"
    legacy_void_usage_ratio_header = "[tx_coil.void_usage_ratio]"
    if rendered_toml.count(active_void_factor_header) != 1:
        raise RuntimeError(
            "type2 single-coil scene temp TOML renderer must emit exactly one active void_factor section "
            f"(count={rendered_toml.count(active_void_factor_header)})"
        )
    if legacy_void_usage_ratio_header in rendered_toml:
        raise RuntimeError(
            "type2 single-coil scene temp TOML renderer must not pre-emit core void_usage_ratio section"
        )
    return rendered_toml


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
        temp_toml_path.write_text(_render_core_tx_rect_void_toml_for_scene(owner_scaled_spec), encoding="utf-8")
        tx_rect_void_spec = load_tx_rect_void_spec(temp_toml_path)
        realized = realize_tx_rect_void_spec(tx_rect_void_spec, seed=seed, profile=profile)
    local_boxes = build_tx_rect_void_box_specs(realized, profile=profile)
    local_bounds_min_xyz, local_bounds_max_xyz, local_bounds_size_xyz = modeled_body_bounds_from_boxes(local_boxes)
    if profile.role == "tx_inner_single_coil":
        tx_ratio_placement = _single_coil_tx_inner_design_outer_placement_from_realized(
            spec=spec,
            owner_spec=owner_spec,
            realized=realized,
            local_bounds_min_xyz=local_bounds_min_xyz,
            local_bounds_size_xyz=local_bounds_size_xyz,
            profile=profile,
        )
        placement_offset_xyz = tx_ratio_placement.frame_origin_xyz
    elif profile.role == "tx_outer_single_coil":
        tx_ratio_placement = _single_coil_tx_ratio_design_outer_placement_from_realized(
            spec=spec,
            owner_spec=owner_spec,
            realized=realized,
            local_bounds_min_xyz=local_bounds_min_xyz,
            local_bounds_size_xyz=local_bounds_size_xyz,
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
    fit_envelope = placement.fit_envelope
    base_scene_children = placement.scene_children
    underlay_repeat_count = _resolve_modeled_single_coil_underlay_repeat_count(spec, profile=profile, seed=seed)
    if underlay_repeat_count > 0:
        assert hasattr(spec, "underlay_pet_psa_thickness_mm")
        raw_underlay_pet_psa_thickness_mm = object.__getattribute__(spec, "underlay_pet_psa_thickness_mm")
        assert isinstance(raw_underlay_pet_psa_thickness_mm, RangeSpec)
        assert hasattr(spec, "underlay_ferrite_thickness_mm")
        raw_underlay_ferrite_thickness_mm = object.__getattribute__(spec, "underlay_ferrite_thickness_mm")
        assert isinstance(raw_underlay_ferrite_thickness_mm, RangeSpec)
        pet_psa_thickness_mm = _resolve_fixed_positive_range_mm(
            raw_underlay_pet_psa_thickness_mm,
            context="tx_outer_single_coil.underlay_pet_psa_thickness_mm",
        )
        ferrite_thickness_mm = _resolve_fixed_positive_range_mm(
            raw_underlay_ferrite_thickness_mm,
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
    canonical_coordinates["trace_width_mm"] = fit_envelope.realized.trace_width_mm
    if underlay_repeat_count > 0:
        canonical_coordinates["outer_void_stack_raw_overshoot_mm"] = raw_overshoot_mm
    terminal_metadata = modeled_terminal_metadata(
        realized=fit_envelope.realized,
        profile=profile,
        frame_origin_xyz=fit_envelope.frame_origin_xyz,
        transformed_boxes=fit_envelope.transformed_boxes,
    )
    raw_vertices_xyz = terminal_metadata["vertices_xyz"]
    if not isinstance(raw_vertices_xyz, (tuple, list)):
        raise RuntimeError(
            "type2 tx outer terminal metadata requires 4 vertices for vertices_xyz "
            f"(actual={type(raw_vertices_xyz).__name__})"
        )
    if len(raw_vertices_xyz) != 4:
        raise RuntimeError(
            "type2 tx outer terminal metadata requires exactly four vertices_xyz points "
            f"(actual={len(raw_vertices_xyz)})"
        )
    first_point, second_point, third_point, fourth_point = raw_vertices_xyz
    outer_vertices_xyz = _transform_outer_terminal_sheet_vertices_xyz(
        port_sheet_vertices_xyz=cast(
            tuple[Point3, Point3, Point3, Point3],
            (first_point, second_point, third_point, fourth_point),
        ),
        angle_deg=placement.angle_deg,
        frame_origin_xyz=placement.frame_origin_xyz,
    )
    terminal_metadata["vertices_xyz"] = outer_vertices_xyz
    terminal_metadata["integration_line_start_xyz"] = (
        (outer_vertices_xyz[3][0] + outer_vertices_xyz[0][0]) / 2.0,
        (outer_vertices_xyz[3][1] + outer_vertices_xyz[0][1]) / 2.0,
        (outer_vertices_xyz[3][2] + outer_vertices_xyz[0][2]) / 2.0,
    )
    terminal_metadata["integration_line_end_xyz"] = (
        (outer_vertices_xyz[1][0] + outer_vertices_xyz[2][0]) / 2.0,
        (outer_vertices_xyz[1][1] + outer_vertices_xyz[2][1]) / 2.0,
        (outer_vertices_xyz[1][2] + outer_vertices_xyz[2][2]) / 2.0,
    )
    expected_exported_body_names = tuple(shape.label for shape in (base_scene_children + underlay_scene_children))
    if len(set(expected_exported_body_names)) != len(expected_exported_body_names):
        raise RuntimeError(
            "type2 modeled scene body names must be unique "
            f"(object_id={spec.object_id}, names={expected_exported_body_names})"
        )
    exported_body_canonical_coordinates = _exported_body_canonical_coordinates(
        scene_children=scene_children,
        expected_exported_body_names=expected_exported_body_names,
        object_id=spec.object_id,
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
            "exported_body_canonical_coordinates": exported_body_canonical_coordinates,
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
    single_coil_void_stack_present = False
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
        clearance_underlay_scene_children = underlay_scene_children
    elif profile.role == "tx_inner_single_coil":
        if not isinstance(spec, ModeledTxInnerSingleCoilSpec):
            raise RuntimeError(f"type2 tx inner underlay requires tx inner spec (object_id={spec.object_id})")
        pet_psa_thickness_mm = resolve_modeled_tx_inner_underlay_pet_psa_thickness_mm(
            spec,
            seed=seed,
        )
        ferrite_thickness_mm = resolve_modeled_tx_inner_underlay_ferrite_thickness_mm(
            spec,
            seed=seed,
        )
        if underlay_repeat_count > 0:
            tx_inner_underlay_descriptor = resolve_tx_inner_single_coil_underlay_placement_descriptor(
                owner_spec=owner_spec,
                actual_region_min_xyz=fit_envelope.outer_bounds_min_xyz,
                actual_region_size_xyz=fit_envelope.outer_bounds_size_xyz,
                repeat_count=underlay_repeat_count,
                pet_psa_thickness_mm=pet_psa_thickness_mm,
                ferrite_thickness_mm=ferrite_thickness_mm,
            )
            bottom_underlay_scene_children = build_tx_inner_single_coil_underlay_shapes(tx_inner_underlay_descriptor)
        else:
            bottom_underlay_scene_children = ()
        single_coil_void_stack_present = resolve_modeled_tx_inner_void_stack_present(spec, seed=seed)
        if single_coil_void_stack_present:
            void_bounds = fit_envelope.realized.void_bounds
            local_corridor_min_y, local_corridor_max_y = local_central_void_corridor_y_bounds(
                fit_envelope.realized,
                profile=profile,
            )
            frame_origin_x, frame_origin_y, _frame_origin_z = fit_envelope.frame_origin_xyz
            tx_inner_void_stack_descriptor = resolve_tx_inner_single_coil_void_stack_placement_descriptor(
                void_min_x=frame_origin_x + void_bounds.min_x,
                void_max_x=frame_origin_x + void_bounds.max_x,
                void_min_y=frame_origin_y + local_corridor_min_y,
                void_max_y=frame_origin_y + local_corridor_max_y,
                z_bottom=fit_envelope.outer_bounds_min_xyz[2],
                z_top=tx_region_max_z,
                pet_psa_thickness_mm=pet_psa_thickness_mm,
                ferrite_thickness_mm=ferrite_thickness_mm,
            )
            void_stack_scene_children = build_tx_inner_single_coil_void_stack_shapes(tx_inner_void_stack_descriptor)
        else:
            void_stack_scene_children = ()
        underlay_scene_children = bottom_underlay_scene_children + void_stack_scene_children
        clearance_underlay_scene_children = underlay_scene_children
    elif profile.role == "tx_outer_single_coil":
        if underlay_repeat_count != 0:
            raise RuntimeError(
                f"type2 {profile.role} underlay repeat count must remain zero (actual={underlay_repeat_count})"
            )
        underlay_scene_children = ()
        clearance_underlay_scene_children = underlay_scene_children
    elif profile.role == "rx_single_coil":
        rx_backing_scene_children = (
            build_rx_underlay_scene_shapes(
                owner_spec=owner_spec,
                repeat_count=underlay_repeat_count,
                modeled_bounds_min_xyz=fit_envelope.physical_modeled_body_bounds_min_xyz,
                modeled_bounds_max_xyz=fit_envelope.physical_modeled_body_bounds_max_xyz,
            )
            if underlay_repeat_count > 0
            else ()
        )
        single_coil_void_stack_present = resolve_modeled_single_coil_void_stack_present(spec, seed=seed)
        if single_coil_void_stack_present:
            void_bounds = fit_envelope.realized.void_bounds
            local_corridor_min_y, local_corridor_max_y = local_central_void_corridor_y_bounds(
                fit_envelope.realized,
                profile=profile,
            )
            frame_origin_xyz = fit_envelope.frame_origin_xyz
            min_void_corridor_world_xyz = profile.world_point(
                (void_bounds.min_x, local_corridor_min_y, 0.0),
                frame_origin_xyz=frame_origin_xyz,
            )
            max_void_corridor_world_xyz = profile.world_point(
                (void_bounds.max_x, local_corridor_max_y, 0.0),
                frame_origin_xyz=frame_origin_xyz,
            )
            rx_void_stack_descriptor = resolve_rx_single_coil_void_stack_placement_descriptor(
                x_min=fit_envelope.outer_bounds_min_xyz[0],
                x_max=fit_envelope.outer_bounds_max_xyz[0],
                void_min_y=min_void_corridor_world_xyz[1],
                void_max_y=max_void_corridor_world_xyz[1],
                void_min_z=min_void_corridor_world_xyz[2],
                void_max_z=max_void_corridor_world_xyz[2],
            )
            rx_void_stack_scene_children = build_rx_single_coil_void_stack_shapes(rx_void_stack_descriptor)
        else:
            rx_void_stack_scene_children = ()
        underlay_scene_children = rx_backing_scene_children + rx_void_stack_scene_children
        clearance_underlay_scene_children = rx_backing_scene_children
    else:
        raise RuntimeError(f"unsupported single-coil modeled role for scene assembly: {profile.role}")
    if len(clearance_underlay_scene_children) == 0:
        if len(underlay_scene_children) != 0 and profile.role != "rx_single_coil":
            raise RuntimeError(
                "type2 single-coil non-RX underlay children require ferrite/FR4 clearance tools "
                f"(object_id={spec.object_id}, underlay_labels={tuple(shape.label for shape in underlay_scene_children)})"
            )
    else:
        base_scene_children, cleared_underlay_scene_children = _apply_single_coil_ferrite_fr4_boolean_clearance(
            base_scene_children=base_scene_children,
            underlay_scene_children=clearance_underlay_scene_children,
            object_id=spec.object_id,
        )
        if profile.role == "rx_single_coil":
            rx_passive_void_stack_scene_children = underlay_scene_children[len(clearance_underlay_scene_children):]
            underlay_scene_children = cleared_underlay_scene_children + rx_passive_void_stack_scene_children
        else:
            if len(cleared_underlay_scene_children) != len(underlay_scene_children):
                raise RuntimeError(
                    "type2 single-coil ferrite/FR4 clearance output must match underlay count "
                    f"(object_id={spec.object_id}, expected={len(underlay_scene_children)}, "
                    f"actual={len(cleared_underlay_scene_children)})"
                )
            underlay_scene_children = cleared_underlay_scene_children
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
    canonical_coordinates["trace_width_mm"] = fit_envelope.realized.trace_width_mm
    if profile.role == "rx_single_coil":
        canonical_coordinates["void_stack_present"] = single_coil_void_stack_present
    exported_body_canonical_coordinates = _exported_body_canonical_coordinates(
        scene_children=scene_children,
        expected_exported_body_names=expected_exported_body_names,
        object_id=spec.object_id,
    )
    terminal_metadata = modeled_terminal_metadata(
        realized=fit_envelope.realized,
        profile=profile,
        frame_origin_xyz=fit_envelope.frame_origin_xyz,
        transformed_boxes=fit_envelope.transformed_boxes,
    )

    scene_data: dict[str, object] = {
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
        "exported_body_canonical_coordinates": exported_body_canonical_coordinates,
        "terminal_metadata": terminal_metadata,
    }
    if profile.role == "rx_single_coil":
        scene_data["void_stack_present"] = single_coil_void_stack_present
    return (scene_children, cast(ModeledObjectSceneData, scene_data))


__all__ = [
    "RealizedSingleCoilFitEnvelope",
    "TxOuterSingleCoilScenePlacement",
    "build_modeled_single_coil_scene_data",
    "resolve_modeled_single_coil_fit_envelope",
    "resolve_tx_outer_single_coil_scene_placement",
    "resolve_tx_outer_single_coil_fit_envelope",
    "single_coil_placement_offset",
]

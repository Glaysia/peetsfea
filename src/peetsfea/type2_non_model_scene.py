from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Literal
from typing import cast

import build123d as bd
from build123d.topology import Shape

from peetsfea.type2_single_coil_scene import resolve_modeled_single_coil_fit_envelope
from peetsfea.type2_single_coil_scene import resolve_tx_outer_single_coil_scene_placement
from peetsfea.type2_scene_geometry import build_non_model_box_shape
from peetsfea.type2_scene_geometry import canonical_from_non_model_box
from peetsfea.type2_scene_geometry import canonical_from_non_model_specs
from peetsfea.type2_scene_geometry import canonical_from_shape
from peetsfea.type2_step_ledger import CanonicalCoordinates
from peetsfea.type2_step_ledger import NonModelObjectLedgerEntry
from peetsfea.type2_step_ledger import NonModelSceneMemberEntry
from peetsfea.type2_step_ledger import NonModelSceneMemberLedgerEntry
from peetsfea.type2_step_ledger import TxActualRegionBounds
from peetsfea.type2_step_ledger import TxActualRegionProvenance
from peetsfea.type2_step_ledger import TxInnerRegionReferenceLineProvenance
from peetsfea.type2_step_ledger import TxOuterRegionPrismProvenance
from peetsfea.type2_step_spec import ModeledSingleCoilSpec
from peetsfea.type2_step_spec import ModeledObjectSpec
from peetsfea.type2_step_spec import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import NonModelDerivedSpec
from peetsfea.type2_step_spec import NonModelTxRegionActualSpec
from peetsfea.type2_step_spec import NonModelTxRegionActualStackSpaceSpec
from peetsfea.type2_step_spec import NonModelTxRegionSpec
from peetsfea.type2_step_spec import Point3
from peetsfea.type2_step_spec import RangeSpec

_BASE_NON_MODEL_VISIBLE_GROUPS: tuple[tuple[str, str, Literal["XY", "YZ", "ZX", "mixed"], tuple[str, ...]], ...] = (
    ("environment", "environment", "mixed", ("floor", "shelf", "wall", "tv")),
    ("tx_region", "tx_region", "XY", ("tx_region",)),
    ("rx_region_max", "rx_region_max", "YZ", ("rx_region_max",)),
)
_TX_INNER_REGION_OBJECT_ID = "tx_inner_region"
_TX_INNER_REGION_KIND = "tx_inner_region"
_TX_INNER_REGION_SOURCE_REGION_ID = "tx_region"
_TX_INNER_REGION_PROVENANCE_BY_OBJECT_ID: dict[str, TxInnerRegionReferenceLineProvenance] = {}
_TX_INNER_ACTUAL_REGION_OBJECT_ID = "tx_inner_actual_region"
_TX_INNER_ACTUAL_REGION_KIND = "tx_inner_actual_region"
_TX_ACTUAL_REGION_PROVENANCE_BY_OBJECT_ID: dict[str, TxActualRegionProvenance] = {}
_TX_OUTER_REGION_OBJECT_ID = "tx_outer_region"
_TX_OUTER_REGION_KIND = "tx_outer_region"
_TX_OUTER_REGION_PROVENANCE_BY_OBJECT_ID: dict[str, TxOuterRegionPrismProvenance] = {}
_TX_OUTER_ACTUAL_REGION_OBJECT_ID = "tx_outer_actual_region"
_TX_OUTER_ACTUAL_REGION_KIND = "tx_outer_actual_region"


@dataclass(frozen=True)
class TxRegionActualStackSpaceTiltTransform:
    rotation_basis_center: Point3
    rotation_axis: Point3
    rotation_angle_deg: float
    shift_delta_z: float


@dataclass(frozen=True)
class TxOuterRegionPrismTiltFrame:
    frame_origin_xyz: Point3
    local_x_axis_xyz: Point3
    local_y_axis_xyz: Point3
    local_z_axis_xyz: Point3
    top_edge_length_xyz: float


def require_tx_outer_region_prism_provenance(
    object_id: Literal["tx_outer_region"],
) -> TxOuterRegionPrismProvenance:
    if object_id != _TX_OUTER_REGION_OBJECT_ID:
        raise RuntimeError(
            "tx_outer_region prism provenance requires exactly tx_outer_region object id "
            f"(actual={object_id!r})"
        )
    if object_id not in _TX_OUTER_REGION_PROVENANCE_BY_OBJECT_ID:
        raise RuntimeError(
            "tx_outer_region prism provenance is unavailable; resolve tx_outer_region first "
            f"(object_id={object_id})"
        )
    assert object_id in _TX_OUTER_REGION_PROVENANCE_BY_OBJECT_ID
    return _TX_OUTER_REGION_PROVENANCE_BY_OBJECT_ID[object_id]


def resolve_tx_outer_region_tilt_frame(
    *,
    provenance: TxOuterRegionPrismProvenance,
) -> TxOuterRegionPrismTiltFrame:
    top_inner_start_xyz = provenance["top_inner_start_xyz"]
    top_outer_start_xyz = provenance["top_outer_start_xyz"]
    local_x_axis_xyz = _subtract_points(top_outer_start_xyz, top_inner_start_xyz)
    top_edge_length_xyz = math.sqrt(
        (local_x_axis_xyz[0] * local_x_axis_xyz[0])
        + (local_x_axis_xyz[1] * local_x_axis_xyz[1])
        + (local_x_axis_xyz[2] * local_x_axis_xyz[2])
    )
    if not math.isfinite(top_edge_length_xyz):
        raise RuntimeError(
            "tx_outer_region top-edge length must be finite "
            f"(top_inner_start={top_inner_start_xyz}, top_outer_start={top_outer_start_xyz})"
        )
    if top_edge_length_xyz <= 0.0:
        raise RuntimeError(
            "tx_outer_region top-edge length must be > 0 to derive rigid tilt frame "
            f"(top_inner_start={top_inner_start_xyz}, top_outer_start={top_outer_start_xyz})"
        )
    local_x_axis_unit = (
        local_x_axis_xyz[0] / top_edge_length_xyz,
        local_x_axis_xyz[1] / top_edge_length_xyz,
        local_x_axis_xyz[2] / top_edge_length_xyz,
    )
    local_y_axis_xyz = (0.0, 1.0, 0.0)
    local_z_axis_xyz = _normalize_vector(
        _cross_vector(local_x_axis_unit, local_y_axis_xyz),
        context="tx_outer_region prism top-edge to world +Y tilt frame",
    )
    local_z_axis_component = local_z_axis_xyz[2]
    if not math.isfinite(local_z_axis_component):
        raise RuntimeError(
            "tx_outer_region tilt frame z-axis must be finite "
            f"(local_x_axis_unit={local_x_axis_unit}, local_y_axis={local_y_axis_xyz})"
        )
    return TxOuterRegionPrismTiltFrame(
        frame_origin_xyz=top_inner_start_xyz,
        local_x_axis_xyz=local_x_axis_unit,
        local_y_axis_xyz=local_y_axis_xyz,
        local_z_axis_xyz=local_z_axis_xyz,
        top_edge_length_xyz=top_edge_length_xyz,
    )


def _normalize_vector(vector: Point3, *, context: str) -> Point3:
    x, y, z = vector
    norm = math.sqrt((x * x) + (y * y) + (z * z))
    if not math.isfinite(norm):
        raise RuntimeError(f"{context} vector norm must be finite (vector={vector})")
    if norm <= 0.0:
        raise RuntimeError(f"{context} vector norm must be positive (vector={vector})")
    return (x / norm, y / norm, z / norm)


def _cross_vector(a: Point3, b: Point3) -> Point3:
    return (
        (a[1] * b[2]) - (a[2] * b[1]),
        (a[2] * b[0]) - (a[0] * b[2]),
        (a[0] * b[1]) - (a[1] * b[0]),
    )


def _dot_vector(a: Point3, b: Point3) -> float:
    return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])


def _subtract_points(a: Point3, b: Point3) -> Point3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def resolve_tx_region_actual_stack_space_tilt_enabled(
    *,
    derived_spec: NonModelTxRegionActualStackSpaceSpec,
    seed: int,
) -> int:
    tilt_enabled = _selected_integer_candidate(
        range_spec=derived_spec.tilt_enabled,
        owner_path=f"non_model_objects.{derived_spec.object_id}.tilt_enabled",
        seed=seed,
    )
    if tilt_enabled != 1:
        raise RuntimeError(
            "tx_region_actual_stack_space.tilt_enabled must be fixed on at runtime "
            f"(actual={tilt_enabled})"
        )
    return tilt_enabled


def parent_tx_region_actual_object_id_for_stack_space_object_id(*, object_id: str) -> str:
    if object_id == "tx_region_actual_stack_space":
        return "tx_region_actual"
    if not object_id.startswith("tx_region_actual_stack_space_x"):
        raise RuntimeError(
            f"tx_region_actual_stack_space object_id must be concrete for parent lookup (actual={object_id})"
        )
    if "_y" not in object_id:
        raise RuntimeError(
            f"tx_region_actual_stack_space concrete object_id must include y-index (actual={object_id})"
        )
    x_fragment, y_fragment = object_id.split("_y", maxsplit=1)
    if not x_fragment.startswith("tx_region_actual_stack_space_x"):
        raise RuntimeError(f"tx_region_actual_stack_space object_id x fragment invalid (actual={object_id})")
    if not x_fragment[len("tx_region_actual_stack_space_x") :].isdigit() or not y_fragment.isdigit():
        raise RuntimeError(
            f"tx_region_actual_stack_space object_id tile indices must be integers (actual={object_id})"
        )
    return f"tx_region_actual{object_id.removeprefix('tx_region_actual_stack_space')}"


def resolve_tx_region_actual_stack_space_tilt_transform(
    *,
    shape_for_shift: Shape,
    rotation_basis_center: Point3,
    rx_center: Point3,
    tile_bottom_z: float,
    tile_top_z: float,
) -> TxRegionActualStackSpaceTiltTransform:
    target_direction = _subtract_points(rx_center, rotation_basis_center)
    target_unit = _normalize_vector(target_direction, context="tx_region_actual_stack_space tilt target direction")
    source_unit = (0.0, 0.0, 1.0)
    cos_angle = _dot_vector(source_unit, target_unit)
    if cos_angle > 1.0 + 1e-12 or cos_angle < -1.0 - 1e-12:
        raise RuntimeError(
            "non-model tx_region_actual_stack_space tilt target has invalid cosine with +Z "
            f"(value={cos_angle}, target={target_unit})"
        )
    rotation_axis: Point3
    rotation_angle_deg: float
    if abs(1.0 - cos_angle) <= 1e-12:
        rotation_axis = (1.0, 0.0, 0.0)
        rotation_angle_deg = 0.0
    elif abs(-1.0 - cos_angle) <= 1e-12:
        rotation_axis = (1.0, 0.0, 0.0)
        rotation_angle_deg = 180.0
    else:
        rotation_axis = _normalize_vector(
            _cross_vector(source_unit, target_unit),
            context="tx_region_actual_stack_space tilt axis",
        )
        rotation_angle_deg = math.degrees(math.acos(cos_angle))
    rotated_shape = apply_tx_region_actual_stack_space_tilt_transform(
        shape=shape_for_shift,
        transform=TxRegionActualStackSpaceTiltTransform(
            rotation_basis_center=rotation_basis_center,
            rotation_axis=rotation_axis,
            rotation_angle_deg=rotation_angle_deg,
            shift_delta_z=0.0,
        ),
    )
    bbox = rotated_shape.bounding_box()
    shift_delta_z = 0.0
    if bbox.max.Z > tile_top_z:
        shift_delta_z = tile_top_z - bbox.max.Z
        shifted_shape = rotated_shape.moved(bd.Location((0.0, 0.0, shift_delta_z)))
        shifted_bbox = shifted_shape.bounding_box()
        if shifted_bbox.min.Z < tile_bottom_z - 1e-9:
            raise RuntimeError(
                "tilted tx_region_actual_stack_space must stay above its owning tx_region_actual tile bottom "
                f"(shape_label={shape_for_shift.label}, tile_bottom_z={tile_bottom_z}, shifted_min_z={shifted_bbox.min.Z})"
            )
    return TxRegionActualStackSpaceTiltTransform(
        rotation_basis_center=rotation_basis_center,
        rotation_axis=rotation_axis,
        rotation_angle_deg=rotation_angle_deg,
        shift_delta_z=shift_delta_z,
    )


def apply_tx_region_actual_stack_space_tilt_transform(
    *,
    shape: Shape,
    transform: TxRegionActualStackSpaceTiltTransform,
) -> Shape:
    if abs(transform.rotation_angle_deg) <= 1e-12:
        rotated_shape = shape
    else:
        rotated_shape = shape.rotate(
            bd.Axis(transform.rotation_basis_center, transform.rotation_axis),
            transform.rotation_angle_deg,
        )
    rotated_shape.label = shape.label
    if abs(transform.shift_delta_z) <= 1e-12:
        return rotated_shape
    shifted_shape = rotated_shape.moved(bd.Location((0.0, 0.0, transform.shift_delta_z)))
    shifted_shape.label = shape.label
    return shifted_shape


def _rotate_tx_region_actual_stack_space_shape_toward_center(
    *,
    shape: Shape,
    final_body_center: Point3,
    rx_center: Point3,
    tile_bottom_z: float,
    tile_top_z: float,
) -> tuple[Shape, CanonicalCoordinates]:
    transform = resolve_tx_region_actual_stack_space_tilt_transform(
        shape_for_shift=shape,
        rotation_basis_center=final_body_center,
        rx_center=rx_center,
        tile_bottom_z=tile_bottom_z,
        tile_top_z=tile_top_z,
    )
    rotated_shape = apply_tx_region_actual_stack_space_tilt_transform(
        shape=shape,
        transform=transform,
    )
    return rotated_shape, canonical_from_shape(shape=rotated_shape)


def require_non_model_object_spec(specs: tuple[NonModelBoxSpec, ...], *, object_id: str) -> NonModelBoxSpec:
    matching_specs = [spec for spec in specs if spec.object_id == object_id]
    if len(matching_specs) != 1:
        raise RuntimeError(
            f"type2 non-model registry must contain exactly one {object_id} object (actual={len(matching_specs)})"
        )
    return matching_specs[0]


def _contains_non_model_object_spec(specs: tuple[NonModelBoxSpec, ...], *, object_id: str) -> bool:
    return any(spec.object_id == object_id for spec in specs)


def _canonical_from_tx_outer_region_prism(provenance: TxOuterRegionPrismProvenance) -> CanonicalCoordinates:
    vertices = (
        provenance["top_inner_start_xyz"],
        provenance["top_inner_end_xyz"],
        provenance["top_outer_start_xyz"],
        provenance["top_outer_end_xyz"],
        provenance["bottom_inner_start_xyz"],
        provenance["bottom_inner_end_xyz"],
        provenance["bottom_outer_start_xyz"],
        provenance["bottom_outer_end_xyz"],
    )
    min_x = min(point[0] for point in vertices)
    min_y = min(point[1] for point in vertices)
    min_z = min(point[2] for point in vertices)
    max_x = max(point[0] for point in vertices)
    max_y = max(point[1] for point in vertices)
    max_z = max(point[2] for point in vertices)
    return {
        "frame_origin_xyz": (min_x, min_y, min_z),
        "outer_bounds_min_xyz": (min_x, min_y, min_z),
        "outer_bounds_max_xyz": (max_x, max_y, max_z),
        "outer_bounds_size_xyz": (max_x - min_x, max_y - min_y, max_z - min_z),
    }


def _non_model_group_specs(
    specs: tuple[NonModelBoxSpec, ...],
) -> tuple[tuple[str, str, Literal["XY", "YZ", "ZX", "mixed"], tuple[NonModelBoxSpec, ...]], ...]:
    groups: list[tuple[str, str, Literal["XY", "YZ", "ZX", "mixed"], tuple[NonModelBoxSpec, ...]]] = []
    visible_groups: list[tuple[str, str, Literal["XY", "YZ", "ZX", "mixed"], tuple[str, ...]]] = []
    for group in _BASE_NON_MODEL_VISIBLE_GROUPS:
        visible_groups.append(group)
        if group[0] == _TX_INNER_REGION_SOURCE_REGION_ID and _contains_non_model_object_spec(
            specs,
            object_id=_TX_INNER_REGION_OBJECT_ID,
        ):
            visible_groups.append(
                (
                    _TX_INNER_REGION_OBJECT_ID,
                    _TX_INNER_REGION_OBJECT_ID,
                    "XY",
                    (_TX_INNER_REGION_OBJECT_ID,),
                )
            )
            if _contains_non_model_object_spec(specs, object_id=_TX_INNER_ACTUAL_REGION_OBJECT_ID):
                visible_groups.append(
                    (
                        _TX_INNER_ACTUAL_REGION_OBJECT_ID,
                        _TX_INNER_ACTUAL_REGION_OBJECT_ID,
                        "XY",
                        (_TX_INNER_ACTUAL_REGION_OBJECT_ID,),
                    )
                )
            if _contains_non_model_object_spec(specs, object_id=_TX_OUTER_REGION_OBJECT_ID):
                visible_groups.append(
                    (
                        _TX_OUTER_REGION_OBJECT_ID,
                        _TX_OUTER_REGION_OBJECT_ID,
                        "XY",
                        (_TX_OUTER_REGION_OBJECT_ID,),
                    )
                )
                if _contains_non_model_object_spec(specs, object_id=_TX_OUTER_ACTUAL_REGION_OBJECT_ID):
                    visible_groups.append(
                        (
                            _TX_OUTER_ACTUAL_REGION_OBJECT_ID,
                            _TX_OUTER_ACTUAL_REGION_OBJECT_ID,
                            "XY",
                            (_TX_OUTER_ACTUAL_REGION_OBJECT_ID,),
                        )
                    )
    if _contains_non_model_object_spec(specs, object_id=_TX_INNER_REGION_OBJECT_ID):
        tx_inner_group_count = sum(1 for group in visible_groups if group[0] == _TX_INNER_REGION_OBJECT_ID)
        if tx_inner_group_count != 1:
            raise RuntimeError(
                "tx_inner_region visible group must be inserted exactly once "
                f"(actual={tx_inner_group_count})"
            )
    if _contains_non_model_object_spec(specs, object_id=_TX_INNER_ACTUAL_REGION_OBJECT_ID):
        tx_inner_actual_group_count = sum(
            1 for group in visible_groups if group[0] == _TX_INNER_ACTUAL_REGION_OBJECT_ID
        )
        if tx_inner_actual_group_count != 1:
            raise RuntimeError(
                "tx_inner_actual_region visible group must be inserted exactly once "
                f"(actual={tx_inner_actual_group_count})"
            )
    if _contains_non_model_object_spec(specs, object_id=_TX_OUTER_REGION_OBJECT_ID):
        tx_outer_group_count = sum(1 for group in visible_groups if group[0] == _TX_OUTER_REGION_OBJECT_ID)
        if tx_outer_group_count != 1:
            raise RuntimeError(
                "tx_outer_region visible group must be inserted exactly once "
                f"(actual={tx_outer_group_count})"
            )
    if _contains_non_model_object_spec(specs, object_id=_TX_OUTER_ACTUAL_REGION_OBJECT_ID):
        tx_outer_actual_group_count = sum(
            1 for group in visible_groups if group[0] == _TX_OUTER_ACTUAL_REGION_OBJECT_ID
        )
        if tx_outer_actual_group_count != 1:
            raise RuntimeError(
                "tx_outer_actual_region visible group must be inserted exactly once "
                f"(actual={tx_outer_actual_group_count})"
            )
    for object_id, role, plane, member_ids in visible_groups:
        group_specs = tuple(require_non_model_object_spec(specs, object_id=member_id) for member_id in member_ids)
        groups.append((object_id, role, plane, group_specs))
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


def is_concrete_tx_region_actual_stack_space_object_id(object_id: str) -> bool:
    if object_id == "tx_region_actual_stack_space":
        return True
    if not object_id.startswith("tx_region_actual_stack_space_x"):
        return False
    if "_y" not in object_id:
        return False
    x_fragment, y_fragment = object_id.split("_y", maxsplit=1)
    if not x_fragment.startswith("tx_region_actual_stack_space_x"):
        return False
    x_index_text = x_fragment[len("tx_region_actual_stack_space_x") :]
    if x_index_text == "" or y_fragment == "":
        return False
    if not x_index_text.isdigit() or not y_fragment.isdigit():
        return False
    return True


def _concrete_tx_region_actual_stack_space_object_id(*, tx_region_actual_object_id: str) -> str:
    if not _is_concrete_tx_region_actual_object_id(tx_region_actual_object_id):
        raise RuntimeError(
            "tx_region_actual_stack_space object id derivation requires concrete tx_region_actual object id "
            f"(actual={tx_region_actual_object_id})"
        )
    if tx_region_actual_object_id == "tx_region_actual":
        return "tx_region_actual_stack_space"
    suffix = tx_region_actual_object_id.removeprefix("tx_region_actual")
    return f"tx_region_actual_stack_space{suffix}"


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
    derived_specs: tuple[NonModelDerivedSpec, ...],
    seed: int,
    modeled_specs: tuple[ModeledObjectSpec, ...] = (),
) -> tuple[NonModelBoxSpec, ...]:
    _TX_INNER_REGION_PROVENANCE_BY_OBJECT_ID.clear()
    _TX_ACTUAL_REGION_PROVENANCE_BY_OBJECT_ID.clear()
    _TX_OUTER_REGION_PROVENANCE_BY_OBJECT_ID.clear()
    if _contains_non_model_object_spec(base_specs, object_id=_TX_INNER_REGION_OBJECT_ID):
        raise RuntimeError(
            "tx_inner_region must be resolved from tx_reference_line ratios; "
            "base non-model box specs for tx_inner_region are unsupported"
        )
    if _contains_non_model_object_spec(base_specs, object_id=_TX_OUTER_REGION_OBJECT_ID):
        raise RuntimeError(
            "tx_outer_region must be resolved from tx_region/tx_inner_region semantic edges; "
            "base non-model box specs for tx_outer_region are unsupported"
        )
    if _contains_non_model_object_spec(base_specs, object_id=_TX_INNER_ACTUAL_REGION_OBJECT_ID):
        raise RuntimeError(
            "tx_inner_actual_region must be resolved from tx_inner_region and tx_inner_single_coil sizing; "
            "base non-model box specs for tx_inner_actual_region are unsupported"
        )
    if _contains_non_model_object_spec(base_specs, object_id=_TX_OUTER_ACTUAL_REGION_OBJECT_ID):
        raise RuntimeError(
            "tx_outer_actual_region must be resolved from tx_outer_region and tx_outer_single_coil sizing; "
            "base non-model box specs for tx_outer_actual_region are unsupported"
        )
    resolved_specs = list(base_specs)
    tx_region_spec = require_non_model_object_spec(base_specs, object_id=_TX_INNER_REGION_SOURCE_REGION_ID)
    tx_inner_region_resolved = isinstance(tx_region_spec, NonModelTxRegionSpec)
    if tx_inner_region_resolved:
        tx_inner_region_spec = _resolved_tx_inner_region_spec_from_tx_region_spec(
            tx_region_spec=tx_region_spec,
            seed=seed,
        )
        resolved_specs.append(tx_inner_region_spec)
        tx_inner_single_coil_specs = tuple(
            modeled_spec for modeled_spec in modeled_specs if isinstance(modeled_spec, ModeledTxInnerSingleCoilSpec)
        )
        if len(tx_inner_single_coil_specs) > 1:
            raise RuntimeError(
                "tx_inner_actual_region requires exactly one tx_inner_single_coil modeled spec when TX inner coils exist "
                f"(actual={len(tx_inner_single_coil_specs)})"
            )
        if len(tx_inner_single_coil_specs) == 1:
            resolved_specs.append(
                _resolved_tx_inner_actual_region_spec_from_tx_inner_region(
                    tx_inner_region_spec=tx_inner_region_spec,
                    tx_inner_single_coil_spec=tx_inner_single_coil_specs[0],
                    seed=seed,
                )
            )
    tx_region_actual_specs: tuple[NonModelBoxSpec, ...] = ()
    for derived_spec in derived_specs:
        if isinstance(derived_spec, NonModelTxRegionActualStackSpaceSpec):
            continue
        if not isinstance(derived_spec, NonModelTxRegionActualSpec):
            raise RuntimeError(f"unsupported non-model derived spec: {type(derived_spec).__name__}")
        tx_region_actual_specs = _resolved_tx_region_actual_specs(
            derived_spec=derived_spec,
            base_specs=base_specs,
            seed=seed,
        )
        resolved_specs.extend(tx_region_actual_specs)
    for derived_spec in derived_specs:
        if isinstance(derived_spec, NonModelTxRegionActualSpec):
            continue
        if not isinstance(derived_spec, NonModelTxRegionActualStackSpaceSpec):
            raise RuntimeError(f"unsupported non-model derived spec: {type(derived_spec).__name__}")
        resolved_specs.extend(
            _resolved_tx_region_actual_stack_space_specs(
                derived_spec=derived_spec,
                tx_region_actual_specs=tx_region_actual_specs,
                seed=seed,
            )
        )
    return tuple(resolved_specs)


def _semantic_positive_x_positive_z_edge(spec: NonModelBoxSpec) -> tuple[Point3, Point3]:
    origin_x, origin_y, origin_z = spec.origin_xyz
    size_x, size_y, size_z = spec.size_xyz
    max_x = origin_x + size_x
    max_z = origin_z + size_z
    return (
        (max_x, origin_y, max_z),
        (max_x, origin_y + size_y, max_z),
    )


def _resolved_tx_outer_region_stack_parameters(
    *,
    modeled_specs: tuple[ModeledObjectSpec, ...],
    seed: int,
) -> tuple[ModeledTxInnerSingleCoilSpec, int, float, float]:
    tx_inner_specs = tuple(spec for spec in modeled_specs if isinstance(spec, ModeledTxInnerSingleCoilSpec))
    if len(tx_inner_specs) != 1:
        raise RuntimeError(
            "tx_outer_region requires exactly one tx_inner_single_coil modeled spec for stack height "
            f"(actual={len(tx_inner_specs)})"
        )
    tx_inner_spec = tx_inner_specs[0]
    layer_count = _selected_integer_candidate(
        range_spec=tx_inner_spec.layer_count,
        owner_path=f"modeled_objects.{tx_inner_spec.object_id}.layer_count",
        seed=seed,
    )
    layer_gap_mm = _selected_float_candidate(
        range_spec=tx_inner_spec.layer_gap_mm,
        owner_path=f"modeled_objects.{tx_inner_spec.object_id}.layer_gap_mm",
        seed=seed,
    )
    pcb_thickness_mm = tx_inner_spec.pcb_thickness_mm
    if layer_count < 1:
        raise RuntimeError(f"tx_outer_region layer_count must resolve to >= 1 (actual={layer_count})")
    if not math.isfinite(pcb_thickness_mm) or pcb_thickness_mm <= 0.0:
        raise RuntimeError(f"tx_outer_region pcb_thickness_mm must be finite and > 0 (actual={pcb_thickness_mm})")
    if not math.isfinite(layer_gap_mm) or layer_gap_mm <= 0.0:
        raise RuntimeError(f"tx_outer_region layer_gap_mm must be finite and > 0 (actual={layer_gap_mm})")
    return tx_inner_spec, layer_count, layer_gap_mm, pcb_thickness_mm


def _tx_actual_region_bounds(*, min_xyz: Point3, size_xyz: Point3) -> TxActualRegionBounds:
    if not all(math.isfinite(value) for value in min_xyz + size_xyz):
        raise RuntimeError(f"tx actual region bounds values must be finite (min={min_xyz}, size={size_xyz})")
    if size_xyz[0] <= 0.0 or size_xyz[1] <= 0.0 or size_xyz[2] <= 0.0:
        raise RuntimeError(f"tx actual region bounds size must be positive (min={min_xyz}, size={size_xyz})")
    max_xyz = (
        min_xyz[0] + size_xyz[0],
        min_xyz[1] + size_xyz[1],
        min_xyz[2] + size_xyz[2],
    )
    return {
        "min_xyz": min_xyz,
        "max_xyz": max_xyz,
        "size_xyz": size_xyz,
    }


def _tx_actual_region_bounds_from_min_max(*, min_xyz: Point3, max_xyz: Point3) -> TxActualRegionBounds:
    size_xyz = (
        max_xyz[0] - min_xyz[0],
        max_xyz[1] - min_xyz[1],
        max_xyz[2] - min_xyz[2],
    )
    return _tx_actual_region_bounds(min_xyz=min_xyz, size_xyz=size_xyz)


def _canonical_from_tx_actual_region_bounds(bounds: TxActualRegionBounds) -> CanonicalCoordinates:
    return {
        "frame_origin_xyz": bounds["min_xyz"],
        "outer_bounds_min_xyz": bounds["min_xyz"],
        "outer_bounds_max_xyz": bounds["max_xyz"],
        "outer_bounds_size_xyz": bounds["size_xyz"],
    }


def _validated_tx_actual_region_usage_ratio(*, ratio: float, owner_path: str) -> float:
    if not math.isfinite(ratio):
        raise RuntimeError(f"{owner_path} must resolve to a finite ratio (actual={ratio})")
    if ratio <= 0.0 or ratio > 1.0:
        raise RuntimeError(f"{owner_path} must resolve in (0, 1] (actual={ratio})")
    return ratio


def _resolved_tx_inner_actual_region_spec_from_tx_inner_region(
    *,
    tx_inner_region_spec: NonModelBoxSpec,
    tx_inner_single_coil_spec: ModeledTxInnerSingleCoilSpec,
    seed: int,
) -> NonModelBoxSpec:
    if tx_inner_region_spec.object_id != _TX_INNER_REGION_OBJECT_ID:
        raise RuntimeError(
            "tx_inner_actual_region requires tx_inner_region guide source "
            f"(actual={tx_inner_region_spec.object_id})"
        )
    fit_envelope = resolve_modeled_single_coil_fit_envelope(
        tx_inner_single_coil_spec,
        owner_spec=tx_inner_region_spec,
        seed=seed,
    )
    x_usage_ratio_owner_path = f"modeled_objects.{tx_inner_single_coil_spec.object_id}.outer_x_usage_ratio"
    y_usage_ratio_owner_path = f"modeled_objects.{tx_inner_single_coil_spec.object_id}.outer_y_usage_ratio"
    x_usage_ratio = _validated_tx_actual_region_usage_ratio(
        ratio=_selected_float_candidate(
            range_spec=tx_inner_single_coil_spec.outer_x_usage_ratio,
            owner_path=x_usage_ratio_owner_path,
            seed=seed,
        ),
        owner_path=x_usage_ratio_owner_path,
    )
    y_usage_ratio = _validated_tx_actual_region_usage_ratio(
        ratio=_selected_float_candidate(
            range_spec=tx_inner_single_coil_spec.outer_y_usage_ratio,
            owner_path=y_usage_ratio_owner_path,
            seed=seed,
        ),
        owner_path=y_usage_ratio_owner_path,
    )
    physical_modeled_body_bounds = _tx_actual_region_bounds_from_min_max(
        min_xyz=fit_envelope.physical_modeled_body_bounds_min_xyz,
        max_xyz=fit_envelope.physical_modeled_body_bounds_max_xyz,
    )
    guide_bounds = _tx_actual_region_bounds(
        min_xyz=tx_inner_region_spec.origin_xyz,
        size_xyz=tx_inner_region_spec.size_xyz,
    )
    canonical_bounds = _tx_actual_region_bounds_from_min_max(
        min_xyz=fit_envelope.design_outer_bounds_min_xyz,
        max_xyz=fit_envelope.design_outer_bounds_max_xyz,
    )
    _TX_ACTUAL_REGION_PROVENANCE_BY_OBJECT_ID[_TX_INNER_ACTUAL_REGION_OBJECT_ID] = {
        "source_guide_id": tx_inner_region_spec.object_id,
        "modeled_source_id": tx_inner_single_coil_spec.object_id,
        "x_usage_ratio_owner_path": x_usage_ratio_owner_path,
        "y_usage_ratio_owner_path": y_usage_ratio_owner_path,
        "x_usage_ratio": x_usage_ratio,
        "y_usage_ratio": y_usage_ratio,
        "guide_bounds": guide_bounds,
        "actual_region_bounds": canonical_bounds,
        "physical_modeled_body_bounds": physical_modeled_body_bounds,
    }
    return NonModelBoxSpec(
        object_id=_TX_INNER_ACTUAL_REGION_OBJECT_ID,
        kind=_TX_INNER_ACTUAL_REGION_KIND,
        primitive="box",
        present=True,
        non_model=True,
        material=tx_inner_region_spec.material,
        plane=tx_inner_region_spec.plane,
        origin_xyz=canonical_bounds["min_xyz"],
        size_xyz=canonical_bounds["size_xyz"],
    )


def _resolved_tx_outer_actual_region_spec_from_tx_outer_region(
    *,
    tx_outer_region_spec: NonModelBoxSpec,
    tx_outer_single_coil_spec: ModeledSingleCoilSpec,
    seed: int,
) -> NonModelBoxSpec:
    if tx_outer_region_spec.object_id != _TX_OUTER_REGION_OBJECT_ID:
        raise RuntimeError(
            "tx_outer_actual_region requires tx_outer_region guide source "
            f"(actual={tx_outer_region_spec.object_id})"
        )
    placement = resolve_tx_outer_single_coil_scene_placement(
        tx_outer_single_coil_spec,
        owner_spec=tx_outer_region_spec,
        seed=seed,
    )
    x_usage_ratio_owner_path = f"modeled_objects.{tx_outer_single_coil_spec.object_id}.outer_x_usage_ratio"
    y_usage_ratio_owner_path = f"modeled_objects.{tx_outer_single_coil_spec.object_id}.outer_y_usage_ratio"
    x_usage_ratio = _validated_tx_actual_region_usage_ratio(
        ratio=_selected_float_candidate(
            range_spec=tx_outer_single_coil_spec.outer_x_usage_ratio,
            owner_path=x_usage_ratio_owner_path,
            seed=seed,
        ),
        owner_path=x_usage_ratio_owner_path,
    )
    y_usage_ratio = _validated_tx_actual_region_usage_ratio(
        ratio=_selected_float_candidate(
            range_spec=tx_outer_single_coil_spec.outer_y_usage_ratio,
            owner_path=y_usage_ratio_owner_path,
            seed=seed,
        ),
        owner_path=y_usage_ratio_owner_path,
    )
    actual_bounds = _tx_actual_region_bounds_from_min_max(
        min_xyz=placement.design_outer_bounds_min_xyz,
        max_xyz=placement.design_outer_bounds_max_xyz,
    )
    physical_bounds = _tx_actual_region_bounds_from_min_max(
        min_xyz=placement.physical_modeled_body_bounds_min_xyz,
        max_xyz=placement.physical_modeled_body_bounds_max_xyz,
    )
    guide_bounds = _tx_actual_region_bounds(
        min_xyz=tx_outer_region_spec.origin_xyz,
        size_xyz=tx_outer_region_spec.size_xyz,
    )
    _TX_ACTUAL_REGION_PROVENANCE_BY_OBJECT_ID[_TX_OUTER_ACTUAL_REGION_OBJECT_ID] = {
        "source_guide_id": tx_outer_region_spec.object_id,
        "modeled_source_id": tx_outer_single_coil_spec.object_id,
        "x_usage_ratio_owner_path": x_usage_ratio_owner_path,
        "y_usage_ratio_owner_path": y_usage_ratio_owner_path,
        "x_usage_ratio": x_usage_ratio,
        "y_usage_ratio": y_usage_ratio,
        "guide_bounds": guide_bounds,
        "actual_region_bounds": actual_bounds,
        "physical_modeled_body_bounds": physical_bounds,
    }
    return NonModelBoxSpec(
        object_id=_TX_OUTER_ACTUAL_REGION_OBJECT_ID,
        kind=_TX_OUTER_ACTUAL_REGION_KIND,
        primitive="box",
        present=True,
        non_model=True,
        material=tx_outer_region_spec.material,
        plane=tx_outer_region_spec.plane,
        origin_xyz=actual_bounds["min_xyz"],
        size_xyz=actual_bounds["size_xyz"],
    )


def _point_shifted_down(point: Point3, *, height_mm: float) -> Point3:
    return (point[0], point[1], point[2] - height_mm)


def _resolved_tx_outer_region_spec_from_source_regions(
    *,
    tx_region_spec: NonModelBoxSpec,
    tx_inner_region_spec: NonModelBoxSpec,
    modeled_specs: tuple[ModeledObjectSpec, ...],
    seed: int,
) -> NonModelBoxSpec:
    tx_inner_spec, layer_count, layer_gap_mm, pcb_thickness_mm = _resolved_tx_outer_region_stack_parameters(
        modeled_specs=modeled_specs,
        seed=seed,
    )
    height_mm = (pcb_thickness_mm + layer_gap_mm) * float(layer_count)
    if not math.isfinite(height_mm) or height_mm <= 0.0:
        raise RuntimeError(
            "tx_outer_region height must be finite and > 0 "
            f"(pcb_thickness_mm={pcb_thickness_mm}, layer_gap_mm={layer_gap_mm}, "
            f"layer_count={layer_count}, height_mm={height_mm})"
        )
    top_inner_start_xyz, top_inner_end_xyz = _semantic_positive_x_positive_z_edge(tx_inner_region_spec)
    top_outer_start_xyz, top_outer_end_xyz = _semantic_positive_x_positive_z_edge(tx_region_spec)
    provenance: TxOuterRegionPrismProvenance = {
        "source_region_id": tx_region_spec.object_id,
        "inner_region_id": tx_inner_region_spec.object_id,
        "stack_source_object_id": tx_inner_spec.object_id,
        "pcb_thickness_mm": pcb_thickness_mm,
        "layer_gap_mm": layer_gap_mm,
        "layer_count": layer_count,
        "height_mm": height_mm,
        "top_inner_start_xyz": top_inner_start_xyz,
        "top_inner_end_xyz": top_inner_end_xyz,
        "top_outer_start_xyz": top_outer_start_xyz,
        "top_outer_end_xyz": top_outer_end_xyz,
        "bottom_inner_start_xyz": _point_shifted_down(top_inner_start_xyz, height_mm=height_mm),
        "bottom_inner_end_xyz": _point_shifted_down(top_inner_end_xyz, height_mm=height_mm),
        "bottom_outer_start_xyz": _point_shifted_down(top_outer_start_xyz, height_mm=height_mm),
        "bottom_outer_end_xyz": _point_shifted_down(top_outer_end_xyz, height_mm=height_mm),
    }
    _TX_OUTER_REGION_PROVENANCE_BY_OBJECT_ID[_TX_OUTER_REGION_OBJECT_ID] = provenance
    canonical = _canonical_from_tx_outer_region_prism(provenance)
    return NonModelBoxSpec(
        object_id=_TX_OUTER_REGION_OBJECT_ID,
        kind=_TX_OUTER_REGION_KIND,
        primitive="box",
        present=True,
        non_model=True,
        material=tx_region_spec.material,
        plane=tx_region_spec.plane,
        origin_xyz=canonical["outer_bounds_min_xyz"],
        size_xyz=canonical["outer_bounds_size_xyz"],
    )


def _validated_tx_inner_region_ratio(*, ratio: float, owner_path: str) -> float:
    if not math.isfinite(ratio):
        raise RuntimeError(f"{owner_path} must resolve to a finite ratio (actual={ratio})")
    if ratio <= 0.0 or ratio >= 1.0:
        raise RuntimeError(f"{owner_path} must resolve strictly inside (0, 1) (actual={ratio})")
    return ratio


def _validated_tx_inner_region_z_ratio(*, ratio: float, owner_path: str) -> float:
    if not math.isfinite(ratio):
        raise RuntimeError(f"{owner_path} must resolve to a finite ratio (actual={ratio})")
    if ratio <= 0.0 or ratio > 1.0:
        raise RuntimeError(f"{owner_path} must resolve in (0, 1] (actual={ratio})")
    return ratio


def _validated_tx_inner_region_y_usage_ratio(*, ratio: float, owner_path: str) -> float:
    if not math.isfinite(ratio):
        raise RuntimeError(f"{owner_path} must resolve to a finite ratio (actual={ratio})")
    if ratio <= 0.0 or ratio > 1.0:
        raise RuntimeError(f"{owner_path} must resolve in (0, 1] (actual={ratio})")
    return ratio


def _resolved_tx_inner_region_spec_from_tx_region_spec(
    *,
    tx_region_spec: NonModelTxRegionSpec,
    seed: int,
) -> NonModelBoxSpec:
    if tx_region_spec.object_id != _TX_INNER_REGION_SOURCE_REGION_ID:
        raise RuntimeError(
            "tx_inner_region base reference-line resolution requires tx_region source "
            f"(actual={tx_region_spec.object_id})"
        )
    return _resolved_tx_inner_region_from_reference_line(
        source_region_spec=tx_region_spec,
        x_ratio=tx_region_spec.tx_reference_line.x_ratio,
        y_usage_ratio=tx_region_spec.tx_reference_line.y_usage_ratio,
        z_ratio=tx_region_spec.tx_reference_line.z_ratio,
        x_ratio_owner_path="non_model_objects.tx_region.tx_reference_line.x_ratio",
        y_usage_ratio_owner_path="non_model_objects.tx_region.tx_reference_line.y_usage_ratio",
        z_ratio_owner_path="non_model_objects.tx_region.tx_reference_line.z_ratio",
        seed=seed,
    )


def _resolved_tx_inner_region_from_reference_line(
    *,
    source_region_spec: NonModelBoxSpec,
    x_ratio: RangeSpec,
    y_usage_ratio: RangeSpec,
    z_ratio: RangeSpec,
    x_ratio_owner_path: str,
    y_usage_ratio_owner_path: str,
    z_ratio_owner_path: str,
    seed: int,
) -> NonModelBoxSpec:
    tx_region_spec = source_region_spec
    tx_origin_x, tx_origin_y, tx_origin_z = tx_region_spec.origin_xyz
    tx_size_x, tx_size_y, tx_size_z = tx_region_spec.size_xyz
    resolved_x_ratio = _validated_tx_inner_region_ratio(
        ratio=_selected_float_candidate(
            range_spec=x_ratio,
            owner_path=x_ratio_owner_path,
            seed=seed,
        ),
        owner_path=x_ratio_owner_path,
    )
    resolved_z_ratio = _validated_tx_inner_region_z_ratio(
        ratio=_selected_float_candidate(
            range_spec=z_ratio,
            owner_path=z_ratio_owner_path,
            seed=seed,
        ),
        owner_path=z_ratio_owner_path,
    )
    resolved_y_usage_ratio = _validated_tx_inner_region_y_usage_ratio(
        ratio=_selected_float_candidate(
            range_spec=y_usage_ratio,
            owner_path=y_usage_ratio_owner_path,
            seed=seed,
        ),
        owner_path=y_usage_ratio_owner_path,
    )
    x_ref = tx_origin_x + (tx_size_x * resolved_x_ratio)
    z_ref = tx_origin_z + (tx_size_z * resolved_z_ratio)
    inner_size_x = x_ref - tx_origin_x
    inner_size_y = tx_size_y * resolved_y_usage_ratio
    inner_size_z = z_ref - tx_origin_z
    if inner_size_x <= 0.0 or inner_size_y <= 0.0 or inner_size_z <= 0.0:
        raise RuntimeError(
            "tx_inner_region resolved sizes must be positive "
            f"(x_ratio={resolved_x_ratio}, z_ratio={resolved_z_ratio}, "
            f"y_usage_ratio={resolved_y_usage_ratio}, "
            f"size_x={inner_size_x}, size_y={inner_size_y}, size_z={inner_size_z})"
        )
    inner_origin_y = tx_origin_y + ((tx_size_y - inner_size_y) / 2.0)
    _TX_INNER_REGION_PROVENANCE_BY_OBJECT_ID[_TX_INNER_REGION_OBJECT_ID] = {
        "source_region_id": tx_region_spec.object_id,
        "x_ratio_owner_path": x_ratio_owner_path,
        "y_usage_ratio_owner_path": y_usage_ratio_owner_path,
        "z_ratio_owner_path": z_ratio_owner_path,
        "x_ratio": resolved_x_ratio,
        "y_usage_ratio": resolved_y_usage_ratio,
        "z_ratio": resolved_z_ratio,
        "x_ref": x_ref,
        "z_ref": z_ref,
        "line_start_xyz": (x_ref, inner_origin_y, z_ref),
        "line_end_xyz": (x_ref, inner_origin_y + inner_size_y, z_ref),
    }
    return NonModelBoxSpec(
        object_id=_TX_INNER_REGION_OBJECT_ID,
        kind=_TX_INNER_REGION_KIND,
        primitive="box",
        present=True,
        non_model=True,
        material=tx_region_spec.material,
        plane=tx_region_spec.plane,
        origin_xyz=(tx_origin_x, inner_origin_y, tx_origin_z),
        size_xyz=(inner_size_x, inner_size_y, inner_size_z),
    )


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


def _resolved_tx_region_actual_stack_space_specs(
    *,
    derived_spec: NonModelTxRegionActualStackSpaceSpec,
    tx_region_actual_specs: tuple[NonModelBoxSpec, ...],
    seed: int,
) -> tuple[NonModelBoxSpec, ...]:
    if len(tx_region_actual_specs) == 0:
        raise RuntimeError("tx_region_actual_stack_space requires resolved tx_region_actual specs")
    scale_ratio = _selected_float_candidate(
        range_spec=derived_spec.scale_ratio,
        owner_path=f"non_model_objects.{derived_spec.object_id}.scale_ratio",
        seed=seed,
    )
    if scale_ratio <= 0.0 or scale_ratio > 1.0:
        raise RuntimeError(f"tx_region_actual_stack_space scale_ratio must be > 0 and <= 1 (actual={scale_ratio})")
    if derived_spec.total_thickness_mm <= 0.0:
        raise RuntimeError(
            "tx_region_actual_stack_space total_thickness_mm must be > 0 "
            f"(actual={derived_spec.total_thickness_mm})"
        )
    if not math.isclose(derived_spec.total_thickness_mm, 5.0, rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError(
            "tx_region_actual_stack_space total_thickness_mm must be exactly 5.0 in runtime scene resolution "
            f"(actual={derived_spec.total_thickness_mm})"
        )
    stack_space_size_z = derived_spec.total_thickness_mm
    tile_specs: list[NonModelBoxSpec] = []
    for tx_region_actual_spec in tx_region_actual_specs:
        if tx_region_actual_spec.kind != "tx_region_actual":
            raise RuntimeError(
                "tx_region_actual_stack_space source registry must contain only tx_region_actual objects "
                f"(object_id={tx_region_actual_spec.object_id}, kind={tx_region_actual_spec.kind})"
            )
        if not _is_concrete_tx_region_actual_object_id(tx_region_actual_spec.object_id):
            raise RuntimeError(
                "tx_region_actual_stack_space source registry must contain concrete tx_region_actual object ids "
                f"(actual={tx_region_actual_spec.object_id})"
            )
        tile_size_x, tile_size_y, tile_size_z = tx_region_actual_spec.size_xyz
        tile_origin_x, tile_origin_y, tile_origin_z = tx_region_actual_spec.origin_xyz
        stack_space_size_x = tile_size_x * scale_ratio
        stack_space_size_y = tile_size_y * scale_ratio
        stack_space_origin_xyz: Point3 = (
            tile_origin_x + ((tile_size_x - stack_space_size_x) / 2.0),
            tile_origin_y + ((tile_size_y - stack_space_size_y) / 2.0),
            tile_origin_z + tile_size_z - stack_space_size_z,
        )
        tx_region_actual_top_z = tile_origin_z + tile_size_z
        if abs((stack_space_origin_xyz[2] + stack_space_size_z) - tx_region_actual_top_z) > 1e-9:
            raise RuntimeError(
                "tx_region_actual_stack_space top face must touch tx_region_actual top face "
                f"(tx_region_actual_object_id={tx_region_actual_spec.object_id}, "
                f"stack_space_origin={stack_space_origin_xyz}, "
                f"stack_space_size={(stack_space_size_x, stack_space_size_y, stack_space_size_z)}, "
                f"tx_region_actual_top_z={tx_region_actual_top_z})"
            )
        tile_specs.append(
            NonModelBoxSpec(
                object_id=_concrete_tx_region_actual_stack_space_object_id(
                    tx_region_actual_object_id=tx_region_actual_spec.object_id
                ),
                kind=derived_spec.kind,
                primitive="box",
                present=True,
                non_model=True,
                material="__materialless_tx_region_actual_stack_space",
                plane="XY",
                origin_xyz=stack_space_origin_xyz,
                size_xyz=(stack_space_size_x, stack_space_size_y, stack_space_size_z),
            )
        )
    return tuple(tile_specs)


def _build_tx_outer_region_shape(*, spec: NonModelBoxSpec):
    if spec.object_id != _TX_OUTER_REGION_OBJECT_ID or spec.kind != _TX_OUTER_REGION_KIND:
        raise RuntimeError(
            "tx_outer_region shape requires concrete tx_outer_region spec "
            f"(object_id={spec.object_id}, kind={spec.kind})"
        )
    provenance = require_tx_outer_region_prism_provenance(cast(Literal["tx_outer_region"], spec.object_id))
    top_wire = bd.Wire.make_polygon(
        (
            provenance["top_inner_start_xyz"],
            provenance["top_outer_start_xyz"],
            provenance["top_outer_end_xyz"],
            provenance["top_inner_end_xyz"],
        ),
        close=True,
    )
    bottom_wire = bd.Wire.make_polygon(
        (
            provenance["bottom_inner_start_xyz"],
            provenance["bottom_outer_start_xyz"],
            provenance["bottom_outer_end_xyz"],
            provenance["bottom_inner_end_xyz"],
        ),
        close=True,
    )
    shape = bd.Solid.make_loft((top_wire, bottom_wire), ruled=True)
    solids = tuple(shape.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "tx_outer_region STEP body must contain exactly one solid "
            f"(object_id={spec.object_id}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = _TX_OUTER_REGION_OBJECT_ID
    return solid


def _build_non_model_group_shape(*, object_id: str, specs: tuple[NonModelBoxSpec, ...]) -> Shape:
    if not specs:
        raise ValueError(f"non-model group shape requires at least one spec ({object_id})")
    if object_id == _TX_OUTER_REGION_OBJECT_ID:
        if len(specs) != 1:
            raise RuntimeError(
                "tx_outer_region scene shape must derive from one source spec "
                f"(object_id={object_id}, source_count={len(specs)})"
            )
        return _build_tx_outer_region_shape(spec=specs[0])
    fused_shape = build_non_model_box_shape(specs[0])
    for spec in specs[1:]:
        fused_shape = cast(Shape, fused_shape.fuse(build_non_model_box_shape(spec)))
    solids = tuple(fused_shape.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "non-model visible group must contain exactly one solid "
            f"(object_id={object_id}, source_count={len(specs)}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = object_id
    return solid


def _non_model_scene_members(specs: tuple[NonModelBoxSpec, ...]) -> tuple[NonModelSceneMemberEntry, ...]:
    members: list[NonModelSceneMemberEntry] = []
    for object_id, role, plane, group_specs in _non_model_group_specs(specs):
        if object_id == _TX_INNER_REGION_OBJECT_ID:
            if len(group_specs) != 1:
                raise RuntimeError(
                    "tx_inner_region scene member must derive from one source spec "
                    f"(object_id={object_id}, source_count={len(group_specs)})"
                )
            tx_inner_region_spec = group_specs[0]
            if tx_inner_region_spec.kind != _TX_INNER_REGION_KIND:
                raise RuntimeError(
                    "tx_inner_region concrete scene member must preserve tx_inner_region kind "
                    f"(object_id={tx_inner_region_spec.object_id}, kind={tx_inner_region_spec.kind})"
                )
            if tx_inner_region_spec.object_id not in _TX_INNER_REGION_PROVENANCE_BY_OBJECT_ID:
                raise RuntimeError(
                    "tx_inner_region ledger member requires creation-time tx_reference_line provenance "
                    f"(object_id={tx_inner_region_spec.object_id})"
                )
            assert tx_inner_region_spec.object_id in _TX_INNER_REGION_PROVENANCE_BY_OBJECT_ID
            tx_reference_line = _TX_INNER_REGION_PROVENANCE_BY_OBJECT_ID[tx_inner_region_spec.object_id]
            members.append(
                {
                    "object_id": _TX_INNER_REGION_OBJECT_ID,
                    "role": _TX_INNER_REGION_OBJECT_ID,
                    "material": tx_inner_region_spec.material,
                    "model_state": False,
                    "canonical_coordinates": canonical_from_non_model_box(tx_inner_region_spec),
                    "plane": tx_inner_region_spec.plane,
                    "non_model": True,
                    "tx_reference_line": tx_reference_line,
                }
            )
            continue
        if object_id == _TX_INNER_ACTUAL_REGION_OBJECT_ID:
            if len(group_specs) != 1:
                raise RuntimeError(
                    "tx_inner_actual_region scene member must derive from one source spec "
                    f"(object_id={object_id}, source_count={len(group_specs)})"
                )
            tx_inner_actual_region_spec = group_specs[0]
            if tx_inner_actual_region_spec.kind != _TX_INNER_ACTUAL_REGION_KIND:
                raise RuntimeError(
                    "tx_inner_actual_region concrete scene member must preserve tx_inner_actual_region kind "
                    f"(object_id={tx_inner_actual_region_spec.object_id}, kind={tx_inner_actual_region_spec.kind})"
                )
            if tx_inner_actual_region_spec.object_id not in _TX_ACTUAL_REGION_PROVENANCE_BY_OBJECT_ID:
                raise RuntimeError(
                    "tx_inner_actual_region ledger member requires creation-time actual-region provenance "
                    f"(object_id={tx_inner_actual_region_spec.object_id})"
                )
            assert tx_inner_actual_region_spec.object_id in _TX_ACTUAL_REGION_PROVENANCE_BY_OBJECT_ID
            tx_actual_region = _TX_ACTUAL_REGION_PROVENANCE_BY_OBJECT_ID[tx_inner_actual_region_spec.object_id]
            members.append(
                {
                    "object_id": _TX_INNER_ACTUAL_REGION_OBJECT_ID,
                    "role": _TX_INNER_ACTUAL_REGION_OBJECT_ID,
                    "material": tx_inner_actual_region_spec.material,
                    "model_state": False,
                    "canonical_coordinates": _canonical_from_tx_actual_region_bounds(
                        tx_actual_region["actual_region_bounds"]
                    ),
                    "plane": tx_inner_actual_region_spec.plane,
                    "non_model": True,
                    "tx_actual_region": tx_actual_region,
                }
            )
            continue
        if object_id == _TX_OUTER_REGION_OBJECT_ID:
            if len(group_specs) != 1:
                raise RuntimeError(
                    "tx_outer_region scene member must derive from one source spec "
                    f"(object_id={object_id}, source_count={len(group_specs)})"
                )
            tx_outer_region_spec = group_specs[0]
            if tx_outer_region_spec.kind != _TX_OUTER_REGION_KIND:
                raise RuntimeError(
                    "tx_outer_region concrete scene member must preserve tx_outer_region kind "
                    f"(object_id={tx_outer_region_spec.object_id}, kind={tx_outer_region_spec.kind})"
                )
            tx_outer_region_prism = require_tx_outer_region_prism_provenance(
                cast(Literal["tx_outer_region"], tx_outer_region_spec.object_id)
            )
            members.append(
                {
                    "object_id": _TX_OUTER_REGION_OBJECT_ID,
                    "role": _TX_OUTER_REGION_OBJECT_ID,
                    "material": tx_outer_region_spec.material,
                    "model_state": False,
                    "canonical_coordinates": _canonical_from_tx_outer_region_prism(tx_outer_region_prism),
                    "plane": tx_outer_region_spec.plane,
                    "non_model": True,
                    "tx_outer_region_prism": tx_outer_region_prism,
                }
            )
            continue
        if object_id == _TX_OUTER_ACTUAL_REGION_OBJECT_ID:
            if len(group_specs) != 1:
                raise RuntimeError(
                    "tx_outer_actual_region scene member must derive from one source spec "
                    f"(object_id={object_id}, source_count={len(group_specs)})"
                )
            tx_outer_actual_region_spec = group_specs[0]
            if tx_outer_actual_region_spec.kind != _TX_OUTER_ACTUAL_REGION_KIND:
                raise RuntimeError(
                    "tx_outer_actual_region concrete scene member must preserve tx_outer_actual_region kind "
                    f"(object_id={tx_outer_actual_region_spec.object_id}, kind={tx_outer_actual_region_spec.kind})"
                )
            if tx_outer_actual_region_spec.object_id not in _TX_ACTUAL_REGION_PROVENANCE_BY_OBJECT_ID:
                raise RuntimeError(
                    "tx_outer_actual_region ledger member requires creation-time actual-region provenance "
                    f"(object_id={tx_outer_actual_region_spec.object_id})"
                )
            assert tx_outer_actual_region_spec.object_id in _TX_ACTUAL_REGION_PROVENANCE_BY_OBJECT_ID
            tx_actual_region = _TX_ACTUAL_REGION_PROVENANCE_BY_OBJECT_ID[tx_outer_actual_region_spec.object_id]
            members.append(
                {
                    "object_id": _TX_OUTER_ACTUAL_REGION_OBJECT_ID,
                    "role": _TX_OUTER_ACTUAL_REGION_OBJECT_ID,
                    "material": tx_outer_actual_region_spec.material,
                    "model_state": False,
                    "canonical_coordinates": _canonical_from_tx_actual_region_bounds(
                        tx_actual_region["actual_region_bounds"]
                    ),
                    "plane": tx_outer_actual_region_spec.plane,
                    "non_model": True,
                    "tx_actual_region": tx_actual_region,
                }
            )
            continue
        if object_id in ("tx_region_actual", "tx_region_actual_stack_space"):
            expected_kind = "tx_region_actual" if object_id == "tx_region_actual" else "tx_region_actual_stack_space"
            for tx_region_actual_spec in group_specs:
                if tx_region_actual_spec.kind != expected_kind:
                    raise RuntimeError(
                        f"{object_id} concrete scene member must preserve kind {expected_kind} "
                        f"(object_id={tx_region_actual_spec.object_id}, kind={tx_region_actual_spec.kind})"
                    )
                if object_id == "tx_region_actual":
                    if not _is_concrete_tx_region_actual_object_id(tx_region_actual_spec.object_id):
                        raise RuntimeError(
                            "tx_region_actual concrete scene member must use concrete object id contract "
                            f"(object_id={tx_region_actual_spec.object_id})"
                        )
                if object_id == "tx_region_actual_stack_space":
                    if not is_concrete_tx_region_actual_stack_space_object_id(tx_region_actual_spec.object_id):
                        raise RuntimeError(
                            "tx_region_actual_stack_space concrete scene member must use concrete object id contract "
                            f"(object_id={tx_region_actual_spec.object_id})"
                        )
                member_entry: dict[str, object] = {
                    "object_id": tx_region_actual_spec.object_id,
                    "role": role,
                    "model_state": False,
                    "canonical_coordinates": canonical_from_non_model_box(tx_region_actual_spec),
                    "plane": tx_region_actual_spec.plane,
                    "non_model": True,
                }
                if role != "tx_region_actual_stack_space":
                    member_entry["material"] = tx_region_actual_spec.material
                members.append(cast(NonModelSceneMemberLedgerEntry, member_entry))
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
                "canonical_coordinates": canonical_from_non_model_specs(
                    group_specs,
                    context=f"non-model visible group {object_id}",
                ),
                "plane": resolved_plane,
                "non_model": True,
            }
        )
    return tuple(members)


def build_non_model_scene_shapes(specs: tuple[NonModelBoxSpec, ...]) -> tuple[Shape, ...]:
    scene_shapes: list[Shape] = []
    for object_id, _role, _plane, group_specs in _non_model_group_specs(specs):
        scene_shapes.append(_build_non_model_group_shape(object_id=object_id, specs=group_specs))
    return tuple(scene_shapes)


def build_non_model_scene_entry(specs: tuple[NonModelBoxSpec, ...]) -> NonModelObjectLedgerEntry:
    if not specs:
        raise ValueError("non-model scene entry requires at least one spec")
    visible_specs = tuple(
        spec
        for _object_id, _role, _plane, group_specs in _non_model_group_specs(specs)
        for spec in group_specs
    )
    material_names = tuple(sorted({spec.material for spec in visible_specs}))
    material = material_names[0] if len(material_names) == 1 else "mixed"
    member_objects = _non_model_scene_members(specs)
    return {
        "object_id": "type2_non_model_scene",
        "role": "non_model_scene",
        "material": material,
        "model_state": False,
        "canonical_coordinates": canonical_from_non_model_specs(visible_specs, context="non-model scene"),
        "plane": "mixed",
        "non_model": True,
        "member_object_ids": tuple(member["object_id"] for member in member_objects),
        "member_objects": member_objects,
    }


__all__ = [
    "TxRegionActualStackSpaceTiltTransform",
    "TxOuterRegionPrismTiltFrame",
    "apply_tx_region_actual_stack_space_tilt_transform",
    "build_non_model_scene_entry",
    "build_non_model_scene_shapes",
    "resolve_tx_outer_region_tilt_frame",
    "is_concrete_tx_region_actual_stack_space_object_id",
    "require_tx_outer_region_prism_provenance",
    "parent_tx_region_actual_object_id_for_stack_space_object_id",
    "require_non_model_object_spec",
    "resolve_non_model_scene_specs",
    "resolve_tx_region_actual_stack_space_tilt_enabled",
    "resolve_tx_region_actual_stack_space_tilt_transform",
]

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Literal
from typing import cast

import build123d as bd

from peetsfea.type2_scene_geometry import build_non_model_box_shape
from peetsfea.type2_scene_geometry import canonical_from_non_model_box
from peetsfea.type2_scene_geometry import canonical_from_non_model_specs
from peetsfea.type2_scene_geometry import canonical_from_shape
from peetsfea.type2_step_ledger import CanonicalCoordinates
from peetsfea.type2_step_ledger import NonModelObjectLedgerEntry
from peetsfea.type2_step_ledger import NonModelSceneMemberLedgerEntry
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import NonModelDerivedSpec
from peetsfea.type2_step_spec import NonModelTxRegionActualSpec
from peetsfea.type2_step_spec import NonModelTxRegionActualStackSpaceSpec
from peetsfea.type2_step_spec import Point3
from peetsfea.type2_step_spec import RangeSpec

_NON_MODEL_VISIBLE_GROUPS: tuple[tuple[str, str, Literal["XY", "YZ", "ZX", "mixed"], tuple[str, ...]], ...] = (
    ("environment", "environment", "mixed", ("floor", "shelf", "wall", "tv")),
    ("tx_region", "tx_region", "XY", ("tx_region",)),
    ("rx_region_max", "rx_region_max", "YZ", ("rx_region_max",)),
)


@dataclass(frozen=True)
class TxRegionActualStackSpaceTiltTransform:
    rotation_basis_center: Point3
    rotation_axis: Point3
    rotation_angle_deg: float
    shift_delta_z: float


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
    shape_for_shift: bd.Shape,
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
    shape: bd.Shape,
    transform: TxRegionActualStackSpaceTiltTransform,
) -> bd.Shape:
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
    shape: bd.Shape,
    final_body_center: Point3,
    rx_center: Point3,
    tile_bottom_z: float,
    tile_top_z: float,
) -> tuple[bd.Shape, CanonicalCoordinates]:
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


def _non_model_group_specs(
    specs: tuple[NonModelBoxSpec, ...],
) -> tuple[tuple[str, str, Literal["XY", "YZ", "ZX", "mixed"], tuple[NonModelBoxSpec, ...]], ...]:
    groups: list[tuple[str, str, Literal["XY", "YZ", "ZX", "mixed"], tuple[NonModelBoxSpec, ...]]] = []
    tx_region_actual_specs = tuple(spec for spec in specs if spec.kind == "tx_region_actual")
    if len(tx_region_actual_specs) == 0:
        raise RuntimeError("type2 non-model registry must contain at least one tx_region_actual concrete object")
    tx_region_actual_sorted_specs = tuple(sorted(tx_region_actual_specs, key=lambda spec: spec.object_id))
    tx_region_actual_stack_space_specs = tuple(spec for spec in specs if spec.kind == "tx_region_actual_stack_space")
    if len(tx_region_actual_stack_space_specs) == 0:
        raise RuntimeError(
            "type2 non-model registry must contain at least one tx_region_actual_stack_space concrete object "
            f"(actual={len(tx_region_actual_stack_space_specs)})"
        )
    tx_region_actual_stack_space_sorted_specs = tuple(
        sorted(tx_region_actual_stack_space_specs, key=lambda spec: spec.object_id)
    )
    for object_id, role, plane, member_ids in _NON_MODEL_VISIBLE_GROUPS:
        group_specs = tuple(require_non_model_object_spec(specs, object_id=member_id) for member_id in member_ids)
        groups.append((object_id, role, plane, group_specs))
        if object_id == "tx_region":
            groups.append(("tx_region_actual", "tx_region_actual", "XY", tx_region_actual_sorted_specs))
            groups.append(
                (
                    "tx_region_actual_stack_space",
                    "tx_region_actual_stack_space",
                    "XY",
                    tx_region_actual_stack_space_sorted_specs,
                )
            )
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
) -> tuple[NonModelBoxSpec, ...]:
    resolved_specs = list(base_specs)
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


def _build_non_model_group_shape(*, object_id: str, specs: tuple[NonModelBoxSpec, ...]) -> bd.Shape:
    if not specs:
        raise ValueError(f"non-model group shape requires at least one spec ({object_id})")
    fused_shape = build_non_model_box_shape(specs[0])
    for spec in specs[1:]:
        fused_shape = cast(bd.Shape, fused_shape.fuse(build_non_model_box_shape(spec)))
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


def build_non_model_scene_shapes(specs: tuple[NonModelBoxSpec, ...]) -> tuple[bd.Shape, ...]:
    scene_shapes: list[bd.Shape] = []
    for object_id, _role, _plane, group_specs in _non_model_group_specs(specs):
        if object_id in ("tx_region_actual", "tx_region_actual_stack_space"):
            for tx_region_actual_spec in group_specs:
                scene_shapes.append(build_non_model_box_shape(tx_region_actual_spec))
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
        "canonical_coordinates": canonical_from_non_model_specs(specs, context="non-model scene"),
        "plane": "mixed",
        "non_model": True,
        "member_object_ids": tuple(member["object_id"] for member in member_objects),
        "member_objects": member_objects,
    }


__all__ = [
    "TxRegionActualStackSpaceTiltTransform",
    "apply_tx_region_actual_stack_space_tilt_transform",
    "build_non_model_scene_entry",
    "build_non_model_scene_shapes",
    "is_concrete_tx_region_actual_stack_space_object_id",
    "parent_tx_region_actual_object_id_for_stack_space_object_id",
    "require_non_model_object_spec",
    "resolve_non_model_scene_specs",
    "resolve_tx_region_actual_stack_space_tilt_enabled",
    "resolve_tx_region_actual_stack_space_tilt_transform",
]

from __future__ import annotations

import hashlib
import math

from peetsfea.type2_step_spec_types import ModeledPlateStackSpec
from peetsfea.type2_step_spec_types import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec_types import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec_types import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec_types import ModeledSingleCoilSpec
from peetsfea.type2_step_spec_types import NonModelTxRegionActualStackSpaceSpec
from peetsfea.type2_step_spec_types import RangeSpec
from peetsfea.type2_step_spec_types import _TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_COUNT
from peetsfea.type2_step_spec_types import _TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_END
from peetsfea.type2_step_spec_types import _TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_START
from peetsfea.type2_step_spec_types import _TX_PLATE_STACK_COIL_COUNT_CANDIDATES
from peetsfea.type2_step_spec_types import _TX_REGION_ACTUAL_STACK_SPACE_TILT_ENABLED_VALUE
from peetsfea.type2_step_spec_types import _TX_UNDERLAY_GAP_MM_CANDIDATES
from peetsfea.type2_step_spec_types import _TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES
from peetsfea.type2_step_spec_types import _UNDERLAY_REPEAT_COUNT_CANDIDATES
from peetsfea.type2_step_spec_types import _UNDERLAY_REPEAT_COUNT_FIXED_CANDIDATES


def _integer_range_candidates(range_spec: RangeSpec) -> tuple[int, ...]:
    if range_spec.is_integer is not True:
        raise ValueError("integer range candidates require integer range spec")
    if range_spec.count == 1:
        raw_values = (range_spec.start,)
    else:
        step = (range_spec.end - range_spec.start) / float(range_spec.count - 1)
        raw_values = tuple(range_spec.start + (step * index) for index in range(range_spec.count))
    rounded_values = tuple(int(math.floor(value + 0.5)) for value in raw_values)
    deduped_values: list[int] = []
    seen_values: set[int] = set()
    for value in rounded_values:
        if value in seen_values:
            continue
        seen_values.add(value)
        deduped_values.append(value)
    return tuple(deduped_values)


def _float_range_candidates(range_spec: RangeSpec) -> tuple[float, ...]:
    if range_spec.is_integer is not False:
        raise ValueError("float range candidates require non-integer range spec")
    if range_spec.count == 1:
        return (range_spec.start,)
    step = (range_spec.end - range_spec.start) / float(range_spec.count - 1)
    return tuple(range_spec.start + (step * index) for index in range(range_spec.count))


def _resolve_seeded_candidate_index(*, seed: int, range_path: str, candidate_count: int) -> int:
    digest = hashlib.blake2b(f"{seed}:{range_path}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False) % candidate_count


def _is_canonical_tx_plate_stack_array_x_usage_ratio_range(range_spec: RangeSpec) -> bool:
    return (
        range_spec.is_integer is False
        and range_spec.start == _TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_START
        and range_spec.end == _TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_END
        and range_spec.count == _TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_COUNT
    )


def resolve_modeled_underlay_repeat_count(spec: ModeledSingleCoilSpec, *, seed: int) -> int:
    candidates = _integer_range_candidates(spec.underlay_repeat_count)
    if spec.role not in ("tx_single_coil", "tx_inner_single_coil", "rx_single_coil"):
        raise RuntimeError(f"unsupported modeled object role for underlay repeat resolution: {spec.role}")
    if candidates != _UNDERLAY_REPEAT_COUNT_CANDIDATES and not (
        len(candidates) == 1 and candidates[0] in _UNDERLAY_REPEAT_COUNT_FIXED_CANDIDATES
    ):
        raise ValueError(
            f"{spec.role}.underlay_repeat_count must realize to canonical candidates "
            f"{_UNDERLAY_REPEAT_COUNT_CANDIDATES} or a fixed single candidate from "
            f"{_UNDERLAY_REPEAT_COUNT_FIXED_CANDIDATES} "
            f"(actual={candidates})"
        )
    if len(candidates) == 1:
        repeat_count = candidates[0]
    else:
        range_path = f"modeled_objects.{spec.object_id}.underlay_repeat_count"
        index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
        repeat_count = candidates[index]
    return repeat_count


def resolve_modeled_tx_inner_underlay_pet_psa_thickness_mm(
    spec: ModeledTxInnerSingleCoilSpec,
    *,
    seed: int,
) -> float:
    _ = seed
    candidates = _float_range_candidates(spec.underlay_pet_psa_thickness_mm)
    if len(candidates) != 1 or candidates[0] <= 0.0:
        raise ValueError(
            "tx_inner_single_coil.underlay_pet_psa_thickness_mm must resolve to a single fixed positive value "
            f"(actual={candidates})"
        )
    return candidates[0]


def resolve_modeled_tx_inner_underlay_ferrite_thickness_mm(
    spec: ModeledTxInnerSingleCoilSpec,
    *,
    seed: int,
) -> float:
    _ = seed
    candidates = _float_range_candidates(spec.underlay_ferrite_thickness_mm)
    if len(candidates) != 1 or candidates[0] <= 0.0:
        raise ValueError(
            "tx_inner_single_coil.underlay_ferrite_thickness_mm must resolve to a single fixed positive value "
            f"(actual={candidates})"
        )
    return candidates[0]


def resolve_modeled_underlay_gap_mm(spec: ModeledTxSingleCoilSpec, *, seed: int) -> float:
    candidates = _float_range_candidates(spec.underlay_gap_mm)
    if candidates != _TX_UNDERLAY_GAP_MM_CANDIDATES and not (
        len(candidates) == 1 and candidates[0] in _TX_UNDERLAY_GAP_MM_CANDIDATES
    ):
        raise ValueError(
            "tx_single_coil.underlay_gap_mm must realize to canonical candidates "
            f"{_TX_UNDERLAY_GAP_MM_CANDIDATES} or a fixed single candidate from that set "
            f"(actual={candidates})"
        )
    if len(candidates) == 1:
        return candidates[0]
    range_path = f"modeled_objects.{spec.object_id}.underlay_gap_mm"
    index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
    return candidates[index]


def resolve_modeled_wall_parallel_stack_present(spec: ModeledTxSingleCoilSpec, *, seed: int) -> bool:
    candidates = _integer_range_candidates(spec.wall_parallel_stack_present)
    if candidates != _TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES and not (
        len(candidates) == 1 and candidates[0] in _TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES
    ):
        raise ValueError(
            "tx_single_coil.wall_parallel_stack_present must realize to canonical candidates "
            f"{_TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES} or a fixed single candidate from that set "
            f"(actual={candidates})"
        )
    if len(candidates) == 1:
        return bool(candidates[0])
    range_path = f"modeled_objects.{spec.object_id}.wall_parallel_stack_present"
    index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
    return bool(candidates[index])


def resolve_non_model_tx_region_actual_stack_space_tilt_enabled(
    spec: NonModelTxRegionActualStackSpaceSpec,
    *,
    seed: int,
) -> bool:
    _ = seed
    candidates = _integer_range_candidates(spec.tilt_enabled)
    if candidates != (_TX_REGION_ACTUAL_STACK_SPACE_TILT_ENABLED_VALUE,):
        raise ValueError(
            f"{spec.kind}.tilt_enabled must be fixed to {_TX_REGION_ACTUAL_STACK_SPACE_TILT_ENABLED_VALUE} "
            f"(actual={candidates})"
        )
    return True


def resolve_modeled_plate_stack_turn_count(spec: ModeledPlateStackSpec, *, seed: int) -> int:
    candidates = _integer_range_candidates(spec.turn_count)
    if any(candidate < 2 for candidate in candidates):
        raise ValueError(
            f"{spec.role}.turn_count must realize to integers >= 2 "
            f"(actual={candidates})"
        )
    if len(candidates) == 1:
        return candidates[0]
    range_path = f"modeled_objects.{spec.object_id}.turn_count"
    index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
    return candidates[index]


def resolve_modeled_plate_stack_metal_fill_factor(spec: ModeledPlateStackSpec, *, seed: int) -> float:
    candidates = _float_range_candidates(spec.metal_fill_factor)
    if any(candidate <= 0.0 or candidate > 0.6 for candidate in candidates):
        raise ValueError(
            f"{spec.role}.metal_fill_factor must realize to values > 0 and <= 0.6 "
            f"(actual={candidates})"
        )
    if len(candidates) == 1:
        return candidates[0]
    range_path = f"modeled_objects.{spec.object_id}.metal_fill_factor"
    index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
    return candidates[index]


def resolve_modeled_plate_stack_z_usage_ratio(spec: ModeledPlateStackSpec, *, seed: int) -> float:
    candidates = _float_range_candidates(spec.z_usage_ratio)
    if any(candidate <= 0.0 or candidate > 1.0 for candidate in candidates):
        raise ValueError(
            f"{spec.role}.z_usage_ratio must realize to values > 0 and <= 1 "
            f"(actual={candidates})"
        )
    if len(candidates) == 1:
        return candidates[0]
    range_path = f"modeled_objects.{spec.object_id}.z_usage_ratio"
    index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
    return candidates[index]


def resolve_modeled_plate_stack_y_usage_ratio(spec: ModeledPlateStackSpec, *, seed: int) -> float:
    candidates = _float_range_candidates(spec.y_usage_ratio)
    if any(candidate <= 0.0 or candidate > 1.0 for candidate in candidates):
        raise ValueError(
            f"{spec.role}.y_usage_ratio must realize to values > 0 and <= 1 "
            f"(actual={candidates})"
        )
    if len(candidates) == 1:
        return candidates[0]
    range_path = f"modeled_objects.{spec.object_id}.y_usage_ratio"
    index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
    return candidates[index]


def resolve_modeled_tx_coil_count(spec: ModeledTxPlateStackSpec, *, seed: int) -> int:
    candidates = _integer_range_candidates(spec.tx_coil_count)
    if candidates != _TX_PLATE_STACK_COIL_COUNT_CANDIDATES and not (
        len(candidates) == 1 and candidates[0] in _TX_PLATE_STACK_COIL_COUNT_CANDIDATES
    ):
        raise ValueError(
            "tx_plate_stack.tx_coil_count must realize to canonical candidates "
            f"{_TX_PLATE_STACK_COIL_COUNT_CANDIDATES} or a fixed single candidate from that set "
            f"(actual={candidates})"
        )
    if len(candidates) == 1:
        return candidates[0]
    range_path = f"modeled_objects.{spec.object_id}.tx_coil_count"
    index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
    return candidates[index]


def resolve_modeled_tx_array_x_usage_ratio(spec: ModeledTxPlateStackSpec, *, seed: int) -> float:
    candidates = _float_range_candidates(spec.tx_array_x_usage_ratio)
    if any(candidate <= 0.0 or candidate > 1.0 for candidate in candidates):
        raise ValueError(
            "tx_plate_stack.tx_array_x_usage_ratio must realize to values > 0 and <= 1 "
            f"(actual={candidates})"
        )
    if spec.tx_array_x_usage_ratio.count != 1 and not _is_canonical_tx_plate_stack_array_x_usage_ratio_range(
        spec.tx_array_x_usage_ratio
    ):
        raise ValueError(
            "tx_plate_stack.tx_array_x_usage_ratio must use canonical sampled range [false, 0.1, 0.6, 14] "
            "or a fixed single candidate with 0 < r <= 1 "
            f"(actual={_format_range(spec.tx_array_x_usage_ratio)})"
        )
    if len(candidates) == 1:
        return candidates[0]
    range_path = f"modeled_objects.{spec.object_id}.tx_array_x_usage_ratio"
    index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
    return candidates[index]


def _format_range(range_spec: RangeSpec) -> str:
    is_integer = "true" if range_spec.is_integer else "false"
    return f"[{is_integer}, {range_spec.start}, {range_spec.end}, {range_spec.count}]"


__all__ = [
    "_float_range_candidates",
    "_integer_range_candidates",
    "_is_canonical_tx_plate_stack_array_x_usage_ratio_range",
    "_resolve_seeded_candidate_index",
    "resolve_modeled_plate_stack_metal_fill_factor",
    "resolve_modeled_plate_stack_turn_count",
    "resolve_modeled_plate_stack_y_usage_ratio",
    "resolve_modeled_plate_stack_z_usage_ratio",
    "resolve_modeled_tx_array_x_usage_ratio",
    "resolve_modeled_tx_coil_count",
    "resolve_modeled_underlay_gap_mm",
    "resolve_modeled_tx_inner_underlay_ferrite_thickness_mm",
    "resolve_modeled_tx_inner_underlay_pet_psa_thickness_mm",
    "resolve_modeled_underlay_repeat_count",
    "resolve_modeled_wall_parallel_stack_present",
    "resolve_non_model_tx_region_actual_stack_space_tilt_enabled",
]

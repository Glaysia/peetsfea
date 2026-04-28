from __future__ import annotations

import math
from typing import Literal, cast

from peetsfea.type2_step_spec_types import NonModelBoxSpec
from peetsfea.type2_step_spec_types import NonModelDerivedSpec
from peetsfea.type2_step_spec_types import NonModelTxReferenceLineSpec
from peetsfea.type2_step_spec_types import NonModelTxRegionSpec
from peetsfea.type2_step_spec_types import NonModelTxRegionActualSpec
from peetsfea.type2_step_spec_types import NonModelTxRegionActualStackSpaceSpec
from peetsfea.type2_step_spec_types import Point3
from peetsfea.type2_step_spec_types import RangeSpec
from peetsfea.type2_step_spec_types import Type2SimulationPolicy
from peetsfea.type2_step_spec_types import _TYPE2_SCHEMA_ID
from peetsfea.type2_step_spec_types import _TX_REGION_ACTUAL_DIVISION_COUNT_COUNT
from peetsfea.type2_step_spec_types import _TX_REGION_ACTUAL_DIVISION_COUNT_END
from peetsfea.type2_step_spec_types import _TX_REGION_ACTUAL_DIVISION_COUNT_START
from peetsfea.type2_step_spec_types import _TX_REGION_ACTUAL_DIVISION_COUNT_VALUES
from peetsfea.type2_step_spec_types import _TX_REGION_ACTUAL_STACK_SPACE_SCALE_RATIO_COUNT
from peetsfea.type2_step_spec_types import _TX_REGION_ACTUAL_STACK_SPACE_SCALE_RATIO_END
from peetsfea.type2_step_spec_types import _TX_REGION_ACTUAL_STACK_SPACE_SCALE_RATIO_START
from peetsfea.type2_step_spec_types import _TX_REGION_ACTUAL_STACK_SPACE_TILT_ENABLED_VALUE
from peetsfea.type2_step_spec_types import _TX_REGION_ACTUAL_STACK_SPACE_TOTAL_THICKNESS_MM
from peetsfea.type2_step_spec_types import _TX_REGION_ACTUAL_USAGE_RATIO_COUNT
from peetsfea.type2_step_spec_types import _TX_REGION_ACTUAL_USAGE_RATIO_END
from peetsfea.type2_step_spec_types import _TX_REGION_ACTUAL_USAGE_RATIO_START


def _require_key(table: dict[str, object], key: str, context: str) -> object:
    if key not in table:
        raise ValueError(f"{context} is missing required key '{key}'")
    return table[key]


def _require_table(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be a table")
    return cast(dict[str, object], value)


def _require_non_empty_str(table: dict[str, object], key: str, context: str) -> str:
    raw_value = _require_key(table, key, context)
    if not isinstance(raw_value, str):
        raise TypeError(f"{context}.{key} must be str")
    if raw_value == "":
        raise ValueError(f"{context}.{key} must be non-empty")
    return raw_value


def _require_true(table: dict[str, object], key: str, context: str) -> Literal[True]:
    raw_value = _require_key(table, key, context)
    if raw_value is not True:
        raise ValueError(f"{context}.{key} must be true")
    return True


def _require_float_value(table: dict[str, object], key: str, context: str) -> float:
    raw_value = _require_key(table, key, context)
    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
        raise TypeError(f"{context}.{key} must be number")
    return float(raw_value)


def _require_point3(table: dict[str, object], key: str, context: str, *, positive: bool) -> Point3:
    raw_value = _require_key(table, key, context)
    if not isinstance(raw_value, list):
        raise TypeError(f"{context}.{key} must be a list of three numbers")
    if len(raw_value) != 3:
        raise ValueError(f"{context}.{key} must contain exactly three numbers")
    parsed_values: list[float] = []
    for index, component in enumerate(raw_value):
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise TypeError(f"{context}.{key}[{index}] must be numeric")
        value = float(component)
        if positive and value <= 0.0:
            raise ValueError(f"{context}.{key}[{index}] must be > 0")
        parsed_values.append(value)
    return (parsed_values[0], parsed_values[1], parsed_values[2])


def _require_plane(table: dict[str, object], key: str, context: str) -> Literal["XY", "YZ", "ZX"]:
    value = _require_non_empty_str(table, key, context)
    if value == "XY":
        return "XY"
    if value == "YZ":
        return "YZ"
    if value == "ZX":
        return "ZX"
    raise ValueError(f"{context}.{key} must be one of XY, YZ, ZX")


def _require_range(
    table: dict[str, object],
    key: str,
    context: str,
    *,
    expect_integer: bool,
) -> RangeSpec:
    raw_node = _require_key(table, key, context)
    node = _require_table(raw_node, f"{context}.{key}")
    if set(node.keys()) != {"range"}:
        raise ValueError(f"{context}.{key} must contain only ['range']")
    raw_range = node["range"]
    if not isinstance(raw_range, list):
        raise TypeError(f"{context}.{key}.range must be [is_integer, start, end, count]")
    if len(raw_range) != 4:
        raise ValueError(f"{context}.{key}.range must contain exactly four entries")
    raw_is_integer, raw_start, raw_end, raw_count = raw_range
    if not isinstance(raw_is_integer, bool):
        raise TypeError(f"{context}.{key}.range[0] must be bool")
    if raw_is_integer != expect_integer:
        expected = "true" if expect_integer else "false"
        raise ValueError(f"{context}.{key}.range[0] must be {expected}")
    if isinstance(raw_start, bool) or not isinstance(raw_start, (int, float)):
        raise TypeError(f"{context}.{key}.range[1] must be number")
    if isinstance(raw_end, bool) or not isinstance(raw_end, (int, float)):
        raise TypeError(f"{context}.{key}.range[2] must be number")
    if isinstance(raw_count, bool) or not isinstance(raw_count, int):
        raise TypeError(f"{context}.{key}.range[3] must be int")
    if raw_count < 1:
        raise ValueError(f"{context}.{key}.range[3] must be >= 1")
    start = float(raw_start)
    end = float(raw_end)
    if end < start:
        raise ValueError(f"{context}.{key}.range end must be >= start")
    return RangeSpec(is_integer=raw_is_integer, start=start, end=end, count=raw_count)


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


def _require_tx_reference_line_ratio_range(
    table: dict[str, object],
    *,
    key: str,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, key, context, expect_integer=False)
    candidates = _float_range_candidates(range_spec)
    if any(candidate <= 0.0 or candidate >= 1.0 for candidate in candidates):
        raise ValueError(
            f"{context}.{key} must realize to values strictly inside (0, 1) "
            f"(actual={candidates})"
        )
    return range_spec


def _parse_tx_reference_line(table: dict[str, object], *, context: str) -> NonModelTxReferenceLineSpec:
    raw_reference_line = _require_key(table, "tx_reference_line", context)
    reference_line = _require_table(raw_reference_line, f"{context}.tx_reference_line")
    allowed_keys = {"x_ratio", "z_ratio"}
    missing_keys = sorted(allowed_keys - set(reference_line.keys()))
    if missing_keys:
        raise ValueError(f"{context}.tx_reference_line is missing required keys: {missing_keys}")
    extra_keys = sorted(set(reference_line.keys()) - allowed_keys)
    if extra_keys:
        raise ValueError(f"{context}.tx_reference_line contains unsupported keys: {extra_keys}")
    return NonModelTxReferenceLineSpec(
        x_ratio=_require_tx_reference_line_ratio_range(
            reference_line,
            key="x_ratio",
            context=f"{context}.tx_reference_line",
        ),
        z_ratio=_require_tx_reference_line_ratio_range(
            reference_line,
            key="z_ratio",
            context=f"{context}.tx_reference_line",
        ),
    )


def _require_type2_schema_id(root: dict[str, object], *, context: str) -> str:
    schema_id = _require_non_empty_str(root, "schema_id", context)
    if schema_id != _TYPE2_SCHEMA_ID:
        raise ValueError(
            f"{context}.schema_id must be '{_TYPE2_SCHEMA_ID}' for active type2 inputs "
            f"(actual={schema_id!r})"
        )
    return schema_id


def _parse_simulation_policy(root: dict[str, object], *, context: str) -> Type2SimulationPolicy:
    simulation = _require_table(_require_key(root, "simulation", context), f"{context}.simulation")
    expected_keys = {"radiation_margin_mm"}
    missing_keys = sorted(expected_keys - set(simulation.keys()))
    if missing_keys:
        raise ValueError(f"{context}.simulation is missing required keys: {missing_keys}")
    extra_keys = sorted(set(simulation.keys()) - expected_keys)
    if extra_keys:
        raise ValueError(f"{context}.simulation contains unsupported keys: {extra_keys}")
    radiation_margin_mm = _require_float_value(simulation, "radiation_margin_mm", f"{context}.simulation")
    if radiation_margin_mm <= 0.0:
        raise ValueError(f"{context}.simulation.radiation_margin_mm must be > 0")
    return Type2SimulationPolicy(radiation_margin_mm=radiation_margin_mm)


def _parse_non_model_box(
    raw_object: object,
    *,
    index: int,
    seen_object_ids: set[str],
) -> NonModelBoxSpec:
    context = f"non_model_objects[{index}]"
    table = _require_table(raw_object, context)
    object_id = _require_non_empty_str(table, "id", context)
    if object_id in seen_object_ids:
        raise ValueError(f"duplicate object id: {object_id}")
    seen_object_ids.add(object_id)

    primitive = _require_non_empty_str(table, "primitive", context)
    if primitive != "box":
        raise ValueError(f"{context}.primitive must be 'box'")

    kind = _require_non_empty_str(table, "kind", context)
    present = _require_true(table, "present", context)
    non_model = _require_true(table, "non_model", context)
    material = _require_non_empty_str(table, "material", context)
    plane = _require_plane(table, "plane", context)
    origin_xyz = _require_point3(table, "origin_xyz", context, positive=False)
    size_xyz = _require_point3(table, "size_xyz", context, positive=True)

    base_allowed_keys = {
        "id",
        "kind",
        "primitive",
        "present",
        "non_model",
        "material",
        "plane",
        "origin_xyz",
        "size_xyz",
    }
    if object_id == "tx_region":
        if kind != "tx_region":
            raise ValueError(f"{context}.kind must be 'tx_region' for tx_region (actual={kind!r})")
        allowed_keys = base_allowed_keys | {"tx_reference_line"}
        extra_keys = sorted(set(table.keys()) - allowed_keys)
        if extra_keys:
            raise ValueError(f"{context} contains unsupported keys for tx_region (actual={extra_keys})")
        return NonModelTxRegionSpec(
            object_id="tx_region",
            kind="tx_region",
            primitive="box",
            present=present,
            non_model=non_model,
            material=material,
            plane=plane,
            origin_xyz=origin_xyz,
            size_xyz=size_xyz,
            tx_reference_line=_parse_tx_reference_line(table, context=context),
        )

    extra_keys = sorted(set(table.keys()) - base_allowed_keys)
    if extra_keys:
        raise ValueError(f"{context} contains unsupported keys for non-model box (actual={extra_keys})")

    return NonModelBoxSpec(
        object_id=object_id,
        kind=kind,
        primitive="box",
        present=present,
        non_model=non_model,
        material=material,
        plane=plane,
        origin_xyz=origin_xyz,
        size_xyz=size_xyz,
    )


def _is_canonical_tx_region_actual_usage_ratio_range(range_spec: RangeSpec) -> bool:
    return (
        range_spec.is_integer is False
        and math.isclose(range_spec.start, 0.3, rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(range_spec.end, 1.0, rel_tol=0.0, abs_tol=1e-12)
        and range_spec.count == 27
    )


def _is_canonical_tx_region_actual_division_count_range(range_spec: RangeSpec) -> bool:
    return (
        range_spec.is_integer is True
        and math.isclose(range_spec.start, 1.0, rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(range_spec.end, 3.0, rel_tol=0.0, abs_tol=1e-12)
        and range_spec.count == 3
    )


def _require_tx_region_actual_usage_ratio_range(
    table: dict[str, object],
    *,
    key: str,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, key, context, expect_integer=False)
    candidates = _float_range_candidates(range_spec)
    if any(
        candidate < 0.3 or candidate > 1.0
        for candidate in candidates
    ):
        raise ValueError(
            f"{context}.{key} must realize to values in "
            f"[0.3, 1.0] "
            f"(actual={candidates})"
        )
    if _is_canonical_tx_region_actual_usage_ratio_range(range_spec):
        return range_spec
    if range_spec.count == 1 and math.isclose(range_spec.start, range_spec.end, rel_tol=0.0, abs_tol=1e-12):
        return range_spec
    raise ValueError(
        f"{context}.{key}.range must be canonical [false, 0.3, 1.0, 27] "
        "or fixed [false, r, r, 1] for 0.3 <= r <= 1.0 "
        f"(actual={[range_spec.is_integer, range_spec.start, range_spec.end, range_spec.count]})"
    )


def _require_tx_region_actual_division_count_range(
    table: dict[str, object],
    *,
    key: str,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, key, context, expect_integer=True)
    candidates = _integer_range_candidates(range_spec)
    if any(candidate < 1 or candidate > 3 for candidate in candidates):
        raise ValueError(
            f"{context}.{key} must realize to values in [1, 2, 3] "
            f"(actual={candidates})"
        )
    if _is_canonical_tx_region_actual_division_count_range(range_spec):
        return range_spec
    if range_spec.count == 1 and math.isclose(range_spec.start, range_spec.end, rel_tol=0.0, abs_tol=1e-12):
        if int(range_spec.start) in (1, 2, 3):
            return range_spec
    raise ValueError(
        f"{context}.{key}.range must be canonical [true, 1, 3, 3] "
        " or fixed [true, n, n, 1] for n in {1, 2, 3} "
        f"(actual={[range_spec.is_integer, range_spec.start, range_spec.end, range_spec.count]})"
    )


def _parse_non_model_tx_region_actual(
    raw_object: object,
    *,
    index: int,
    seen_object_ids: set[str],
) -> NonModelTxRegionActualSpec:
    context = f"non_model_objects[{index}]"
    table = _require_table(raw_object, context)
    object_id = _require_non_empty_str(table, "id", context)
    if object_id in seen_object_ids:
        raise ValueError(f"duplicate object id: {object_id}")
    seen_object_ids.add(object_id)
    if object_id != "tx_region_actual":
        raise ValueError(f"{context}.id must be 'tx_region_actual' (actual={object_id!r})")
    kind = _require_non_empty_str(table, "kind", context)
    if kind != "tx_region_actual":
        raise ValueError(f"{context}.kind must be 'tx_region_actual' (actual={kind!r})")
    source_region_id = _require_non_empty_str(table, "source_region_id", context)
    if source_region_id != "tx_region":
        raise ValueError(f"{context}.source_region_id must be 'tx_region' (actual={source_region_id!r})")
    allowed_keys = {
        "id",
        "kind",
        "source_region_id",
        "x_usage_ratio",
        "y_usage_ratio",
        "x_division_count",
        "y_division_count",
    }
    extra_keys = sorted(set(table.keys()) - allowed_keys)
    if extra_keys:
        raise ValueError(f"{context} contains unsupported keys for tx_region_actual (actual={extra_keys})")
    return NonModelTxRegionActualSpec(
        object_id="tx_region_actual",
        kind="tx_region_actual",
        source_region_id="tx_region",
        x_usage_ratio=_require_tx_region_actual_usage_ratio_range(table, key="x_usage_ratio", context=context),
        y_usage_ratio=_require_tx_region_actual_usage_ratio_range(table, key="y_usage_ratio", context=context),
        x_division_count=_require_tx_region_actual_division_count_range(table, key="x_division_count", context=context),
        y_division_count=_require_tx_region_actual_division_count_range(table, key="y_division_count", context=context),
    )


def _is_canonical_tx_region_actual_stack_space_scale_ratio_range(range_spec: RangeSpec) -> bool:
    return (
        range_spec.is_integer is False
        and math.isclose(
            range_spec.start,
            0.35,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and math.isclose(
            range_spec.end,
            0.95,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and range_spec.count == 25
    )


def _require_tx_region_actual_stack_space_scale_ratio_range(
    table: dict[str, object],
    *,
    key: str,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, key, context, expect_integer=False)
    candidates = _float_range_candidates(range_spec)
    if any(
        candidate < 0.35
        or candidate > 0.95
        for candidate in candidates
    ):
        raise ValueError(
            f"{context}.{key} must realize to values in "
            f"[0.35, 0.95] "
            f"(actual={candidates})"
        )
    if _is_canonical_tx_region_actual_stack_space_scale_ratio_range(range_spec):
        return range_spec
    if range_spec.count == 1 and math.isclose(range_spec.start, range_spec.end, rel_tol=0.0, abs_tol=1e-12):
        return range_spec
    raise ValueError(
        f"{context}.{key}.range must be canonical [false, 0.35, 0.95, 25] "
        "or fixed [false, r, r, 1] for 0.35 <= r <= 0.95 "
        f"(actual={[range_spec.is_integer, range_spec.start, range_spec.end, range_spec.count]})"
    )


def _require_tx_region_actual_stack_space_tilt_enabled_range(
    table: dict[str, object],
    *,
    key: str,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, key, context, expect_integer=True)
    candidates = _integer_range_candidates(range_spec)
    if (
        candidates == (1,)
        and range_spec.count == 1
        and math.isclose(range_spec.start, range_spec.end, rel_tol=0.0, abs_tol=1e-12)
    ):
        return range_spec
    raise ValueError(
        f"{context}.{key}.range must be fixed [true, 1, 1, 1] "
        f"(actual={[range_spec.is_integer, range_spec.start, range_spec.end, range_spec.count]})"
    )


def _parse_non_model_tx_region_actual_stack_space(
    raw_object: object,
    *,
    index: int,
    seen_object_ids: set[str],
) -> NonModelTxRegionActualStackSpaceSpec:
    context = f"non_model_objects[{index}]"
    table = _require_table(raw_object, context)
    object_id = _require_non_empty_str(table, "id", context)
    if object_id in seen_object_ids:
        raise ValueError(f"duplicate object id: {object_id}")
    seen_object_ids.add(object_id)
    if object_id != "tx_region_actual_stack_space":
        raise ValueError(f"{context}.id must be 'tx_region_actual_stack_space' (actual={object_id!r})")
    kind = _require_non_empty_str(table, "kind", context)
    if kind != "tx_region_actual_stack_space":
        raise ValueError(f"{context}.kind must be 'tx_region_actual_stack_space' (actual={kind!r})")
    source_region_id = _require_non_empty_str(table, "source_region_id", context)
    if source_region_id != "tx_region_actual":
        raise ValueError(f"{context}.source_region_id must be 'tx_region_actual' (actual={source_region_id!r})")
    total_thickness_mm = _require_float_value(table, "total_thickness_mm", context)
    if not math.isclose(
        total_thickness_mm,
        5.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError(
            f"{context}.total_thickness_mm must be 5.0 "
            f"(actual={total_thickness_mm})"
        )
    allowed_keys = {
        "id",
        "kind",
        "source_region_id",
        "total_thickness_mm",
        "tilt_enabled",
        "scale_ratio",
    }
    extra_keys = sorted(set(table.keys()) - allowed_keys)
    if extra_keys:
        raise ValueError(
            f"{context} contains unsupported keys for tx_region_actual_stack_space (actual={extra_keys})"
        )
    return NonModelTxRegionActualStackSpaceSpec(
        object_id="tx_region_actual_stack_space",
        kind="tx_region_actual_stack_space",
        source_region_id="tx_region_actual",
        total_thickness_mm=total_thickness_mm,
        tilt_enabled=_require_tx_region_actual_stack_space_tilt_enabled_range(table, key="tilt_enabled", context=context),
        scale_ratio=_require_tx_region_actual_stack_space_scale_ratio_range(table, key="scale_ratio", context=context),
    )


__all__ = [
    "NonModelBoxSpec",
    "NonModelDerivedSpec",
    "NonModelTxReferenceLineSpec",
    "NonModelTxRegionSpec",
    "NonModelTxRegionActualSpec",
    "NonModelTxRegionActualStackSpaceSpec",
    "Point3",
    "RangeSpec",
    "Type2SimulationPolicy",
]

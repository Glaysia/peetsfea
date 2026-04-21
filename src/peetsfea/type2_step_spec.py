from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Literal, cast
import tomllib

from peetsfea.spec.outputs import parse_outputs_table
from peetsfea.type2_step_spec_types import ModeledObjectRole
from peetsfea.type2_step_spec_types import ModeledObjectSpec
from peetsfea.type2_step_spec_types import ModeledPlateStackRole
from peetsfea.type2_step_spec_types import ModeledPlateStackSpec
from peetsfea.type2_step_spec_types import ModeledRxPlateStackSpec
from peetsfea.type2_step_spec_types import ModeledRxSingleCoilSpec
from peetsfea.type2_step_spec_types import ModeledSingleCoilCommonSpec
from peetsfea.type2_step_spec_types import ModeledSingleCoilRole
from peetsfea.type2_step_spec_types import ModeledSingleCoilSpec
from peetsfea.type2_step_spec_types import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec_types import ModeledTxRectVoidColumnsSpec
from peetsfea.type2_step_spec_types import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec_types import NonModelBoxSpec
from peetsfea.type2_step_spec_types import NonModelDerivedSpec
from peetsfea.type2_step_spec_types import NonModelTxRegionActualSpec
from peetsfea.type2_step_spec_types import NonModelTxRegionActualStackSpaceSpec
from peetsfea.type2_step_spec_types import Point3
from peetsfea.type2_step_spec_types import RangeSpec
from peetsfea.type2_step_spec_constraints import Type2ConstraintComparableRef
from peetsfea.type2_step_spec_constraints import Type2ConstraintComparisonOperator
from peetsfea.type2_step_spec_constraints import Type2ConstraintFuncRef
from peetsfea.type2_step_spec_constraints import Type2ConstraintOperandRef
from peetsfea.type2_step_spec_constraints import Type2ConstraintPathRef
from peetsfea.type2_step_spec_constraints import Type2ConstraintRule
from peetsfea.type2_step_spec_constraints import Type2ConstraintValueRef
from peetsfea.type2_step_spec_constraints import _parse_constraints
from peetsfea.type2_step_spec_constraints import _validate_constraints_for_spec
from peetsfea.type2_step_spec_types import Type2SimulationPolicy
from peetsfea.type2_step_spec_types import Type2StepSpec
from peetsfea.type2_step_spec_types import modeled_object_id_for_role
from peetsfea.type2_step_spec_types import modeled_plane_for_role
from peetsfea.type2_step_spec_types import placement_owner_id_for_role
from peetsfea.type2_step_spec_types import _TYPE2_SCHEMA_ID
from peetsfea.type2_step_spec_types import _TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_COUNT
from peetsfea.type2_step_spec_types import _TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_END
from peetsfea.type2_step_spec_types import _TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_START
from peetsfea.type2_step_spec_types import _TX_PLATE_STACK_COIL_COUNT_CANDIDATES
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_CONNECTION_MODE_EXPECTED
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_CONNECTION_MODE_RANGE
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_LAYER_COUNT_ALLOWED
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_LAYER_COUNT_RANGE_COUNT
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_LAYER_COUNT_RANGE_END
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_LAYER_COUNT_RANGE_START
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_LAYER_GAP_MM_RANGE_COUNT
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_LAYER_GAP_MM_RANGE_END
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_LAYER_GAP_MM_RANGE_START
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_PARALLEL_TOTAL_TURN_COUNT_RANGE_COUNT
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_PARALLEL_TOTAL_TURN_COUNT_RANGE_END
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_PARALLEL_TOTAL_TURN_COUNT_RANGE_START
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_SERIES_TOTAL_TURN_COUNT_RANGE_COUNT
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_SERIES_TOTAL_TURN_COUNT_RANGE_END
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_SERIES_TOTAL_TURN_COUNT_RANGE_START
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_TERMINAL_STUB_LENGTH_MM_RANGE_COUNT
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_TERMINAL_STUB_LENGTH_MM_RANGE_END
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_TERMINAL_STUB_LENGTH_MM_RANGE_START
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_TURN_WEIGHT_A_RANGE_COUNT
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_TURN_WEIGHT_A_RANGE_END
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_TURN_WEIGHT_A_RANGE_START
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_TURN_WEIGHT_B_RANGE_COUNT
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_TURN_WEIGHT_B_RANGE_END
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_TURN_WEIGHT_B_RANGE_START
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_TURN_WEIGHT_C_RANGE_COUNT
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_TURN_WEIGHT_C_RANGE_END
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_TURN_WEIGHT_C_RANGE_START
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
from peetsfea.type2_step_spec_types import _TX_UNDERLAY_GAP_MM_CANDIDATES
from peetsfea.type2_step_spec_types import _TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES
from peetsfea.type2_step_spec_types import _UNDERLAY_REPEAT_COUNT_CANDIDATES
from peetsfea.type2_step_spec_non_model import NonModelBoxSpec
from peetsfea.type2_step_spec_non_model import NonModelDerivedSpec
from peetsfea.type2_step_spec_non_model import NonModelTxRegionActualSpec
from peetsfea.type2_step_spec_non_model import NonModelTxRegionActualStackSpaceSpec
from peetsfea.type2_step_spec_non_model import Point3
from peetsfea.type2_step_spec_non_model import RangeSpec
from peetsfea.type2_step_spec_non_model import Type2SimulationPolicy
from peetsfea.type2_step_spec_non_model import _float_range_candidates
from peetsfea.type2_step_spec_non_model import _integer_range_candidates
from peetsfea.type2_step_spec_non_model import _parse_non_model_box
from peetsfea.type2_step_spec_non_model import _parse_non_model_tx_region_actual
from peetsfea.type2_step_spec_non_model import _parse_non_model_tx_region_actual_stack_space
from peetsfea.type2_step_spec_non_model import _parse_simulation_policy
from peetsfea.type2_step_spec_non_model import _require_float_value
from peetsfea.type2_step_spec_non_model import _require_key
from peetsfea.type2_step_spec_non_model import _require_non_empty_str
from peetsfea.type2_step_spec_non_model import _require_plane
from peetsfea.type2_step_spec_non_model import _require_point3
from peetsfea.type2_step_spec_non_model import _require_range
from peetsfea.type2_step_spec_non_model import _require_table
from peetsfea.type2_step_spec_non_model import _require_true
from peetsfea.type2_step_spec_non_model import _require_type2_schema_id


def modeled_object_id_for_role(role: ModeledObjectRole) -> str:
    if role == "tx_single_coil":
        return "tx_rect_void_coil"
    if role == "rx_single_coil":
        return "rx_rect_void_coil"
    if role == "tx_rect_void_columns":
        return "tx_rect_void_columns"
    if role == "tx_plate_stack":
        return "tx_plate_stack"
    if role == "rx_plate_stack":
        return "rx_plate_stack"
    raise RuntimeError(f"unsupported modeled object role for object_id resolution: {role}")


def placement_owner_id_for_role(role: ModeledObjectRole) -> str:
    if role in ("tx_single_coil", "tx_rect_void_columns", "tx_plate_stack"):
        return "tx_region"
    if role in ("rx_single_coil", "rx_plate_stack"):
        return "rx_region_max"
    raise RuntimeError(f"unsupported modeled object role for placement owner resolution: {role}")


def modeled_plane_for_role(role: ModeledObjectRole) -> Literal["XY", "YZ"]:
    if role == "tx_single_coil":
        return "XY"
    if role == "tx_rect_void_columns":
        return "XY"
    if role == "tx_plate_stack":
        return "YZ"
    if role in ("rx_single_coil", "rx_plate_stack"):
        return "YZ"
    raise RuntimeError(f"unsupported modeled object role for plane resolution: {role}")


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

    return NonModelBoxSpec(
        object_id=object_id,
        kind=_require_non_empty_str(table, "kind", context),
        primitive="box",
        present=_require_true(table, "present", context),
        non_model=_require_true(table, "non_model", context),
        material=_require_non_empty_str(table, "material", context),
        plane=_require_plane(table, "plane", context),
        origin_xyz=_require_point3(table, "origin_xyz", context, positive=False),
        size_xyz=_require_point3(table, "size_xyz", context, positive=True),
    )


def _is_canonical_tx_region_actual_usage_ratio_range(range_spec: RangeSpec) -> bool:
    return (
        range_spec.is_integer is False
        and math.isclose(range_spec.start, _TX_REGION_ACTUAL_USAGE_RATIO_START, rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(range_spec.end, _TX_REGION_ACTUAL_USAGE_RATIO_END, rel_tol=0.0, abs_tol=1e-12)
        and range_spec.count == _TX_REGION_ACTUAL_USAGE_RATIO_COUNT
    )


def _is_canonical_tx_region_actual_division_count_range(range_spec: RangeSpec) -> bool:
    return (
        range_spec.is_integer is True
        and math.isclose(range_spec.start, float(_TX_REGION_ACTUAL_DIVISION_COUNT_START), rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(range_spec.end, float(_TX_REGION_ACTUAL_DIVISION_COUNT_END), rel_tol=0.0, abs_tol=1e-12)
        and range_spec.count == _TX_REGION_ACTUAL_DIVISION_COUNT_COUNT
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
        candidate < _TX_REGION_ACTUAL_USAGE_RATIO_START or candidate > _TX_REGION_ACTUAL_USAGE_RATIO_END
        for candidate in candidates
    ):
        raise ValueError(
            f"{context}.{key} must realize to values in "
            f"[{_TX_REGION_ACTUAL_USAGE_RATIO_START}, {_TX_REGION_ACTUAL_USAGE_RATIO_END}] "
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
        if int(range_spec.start) in _TX_REGION_ACTUAL_DIVISION_COUNT_VALUES:
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
            _TX_REGION_ACTUAL_STACK_SPACE_SCALE_RATIO_START,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and math.isclose(
            range_spec.end,
            _TX_REGION_ACTUAL_STACK_SPACE_SCALE_RATIO_END,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and range_spec.count == _TX_REGION_ACTUAL_STACK_SPACE_SCALE_RATIO_COUNT
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
        candidate < _TX_REGION_ACTUAL_STACK_SPACE_SCALE_RATIO_START
        or candidate > _TX_REGION_ACTUAL_STACK_SPACE_SCALE_RATIO_END
        for candidate in candidates
    ):
        raise ValueError(
            f"{context}.{key} must realize to values in "
            f"[{_TX_REGION_ACTUAL_STACK_SPACE_SCALE_RATIO_START}, {_TX_REGION_ACTUAL_STACK_SPACE_SCALE_RATIO_END}] "
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
        candidates == (_TX_REGION_ACTUAL_STACK_SPACE_TILT_ENABLED_VALUE,)
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
        _TX_REGION_ACTUAL_STACK_SPACE_TOTAL_THICKNESS_MM,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError(
            f"{context}.total_thickness_mm must be {_TX_REGION_ACTUAL_STACK_SPACE_TOTAL_THICKNESS_MM} "
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

from peetsfea.type2_step_spec_non_model import NonModelBoxSpec as NonModelBoxSpec
from peetsfea.type2_step_spec_non_model import NonModelDerivedSpec as NonModelDerivedSpec
from peetsfea.type2_step_spec_non_model import NonModelTxRegionActualSpec as NonModelTxRegionActualSpec
from peetsfea.type2_step_spec_non_model import (
    NonModelTxRegionActualStackSpaceSpec as NonModelTxRegionActualStackSpaceSpec,
)
from peetsfea.type2_step_spec_non_model import Point3 as Point3
from peetsfea.type2_step_spec_non_model import RangeSpec as RangeSpec
from peetsfea.type2_step_spec_non_model import Type2SimulationPolicy as Type2SimulationPolicy
from peetsfea.type2_step_spec_non_model import _float_range_candidates as _float_range_candidates
from peetsfea.type2_step_spec_non_model import _integer_range_candidates as _integer_range_candidates
from peetsfea.type2_step_spec_non_model import _parse_non_model_box as _parse_non_model_box
from peetsfea.type2_step_spec_non_model import _parse_non_model_tx_region_actual as _parse_non_model_tx_region_actual
from peetsfea.type2_step_spec_non_model import (
    _parse_non_model_tx_region_actual_stack_space as _parse_non_model_tx_region_actual_stack_space,
)
from peetsfea.type2_step_spec_non_model import _parse_simulation_policy as _parse_simulation_policy
from peetsfea.type2_step_spec_non_model import _require_float_value as _require_float_value
from peetsfea.type2_step_spec_non_model import _require_key as _require_key
from peetsfea.type2_step_spec_non_model import _require_non_empty_str as _require_non_empty_str
from peetsfea.type2_step_spec_non_model import _require_plane as _require_plane
from peetsfea.type2_step_spec_non_model import _require_point3 as _require_point3
from peetsfea.type2_step_spec_non_model import _require_range as _require_range
from peetsfea.type2_step_spec_non_model import _require_table as _require_table
from peetsfea.type2_step_spec_non_model import _require_true as _require_true
from peetsfea.type2_step_spec_non_model import _require_type2_schema_id as _require_type2_schema_id


def _parse_modeled_single_coil(
    raw_object: object,
    *,
    index: int,
    seen_object_ids: set[str],
    non_model_specs_by_id: dict[str, NonModelBoxSpec],
) -> ModeledSingleCoilSpec:
    from peetsfea.tx_rect_void import profile_for_modeled_role

    context = f"modeled_objects[{index}]"
    table = _require_table(raw_object, context)
    object_id = _require_non_empty_str(table, "object_id", context)
    if object_id in seen_object_ids:
        raise ValueError(f"duplicate object id: {object_id}")
    seen_object_ids.add(object_id)

    role = _require_non_empty_str(table, "role", context)
    if role not in ("tx_single_coil", "rx_single_coil"):
        raise ValueError(f"unsupported modeled object role: {role}")
    modeled_role = cast(ModeledSingleCoilRole, role)
    profile = profile_for_modeled_role(modeled_role)
    if object_id != profile.object_id:
        raise ValueError(
            f"prototype modeled object_id must be '{profile.object_id}' for role {role} "
            f"(actual={object_id})"
        )

    raw_model_state = _require_key(table, "model_state", context)
    if not isinstance(raw_model_state, bool):
        raise TypeError(f"{context}.model_state must be bool")
    if raw_model_state is not True:
        raise ValueError(f"{context}.model_state must be true")

    pcb_thickness_mm = _require_float_value(table, "pcb_thickness_mm", context)
    if pcb_thickness_mm <= 0.0:
        raise ValueError(f"{context}.pcb_thickness_mm must be > 0")
    copper_thickness_mm = _require_float_value(table, "copper_thickness_mm", context)
    if copper_thickness_mm <= 0.0:
        raise ValueError(f"{context}.copper_thickness_mm must be > 0")
    material = _require_non_empty_str(table, "material", context)
    if material != "composite":
        raise ValueError(f"{context}.material must be 'composite' (actual={material})")

    terminal_node = _require_table(_require_key(table, "terminal_path", context), f"{context}.terminal_path")
    if set(terminal_node.keys()) != {"value"}:
        raise ValueError(f"{context}.terminal_path must contain only ['value']")
    terminal_path = _require_non_empty_str(terminal_node, "value", f"{context}.terminal_path")

    unsupported_legacy_single_coil_keys = sorted(
        key
        for key in (
            "outer_x_mm",
            "outer_y_mm",
            "void_x_over_outer_x",
            "void_y_over_outer_y",
            "void_center_x_over_outer_x",
            "void_center_y_over_outer_y",
        )
        if key in table
    )
    if unsupported_legacy_single_coil_keys:
        raise ValueError(
            f"{context} contains unsupported legacy keys for {modeled_role} "
            f"(actual={unsupported_legacy_single_coil_keys})"
        )

    placement_owner_id = placement_owner_id_for_role(modeled_role)
    if placement_owner_id not in non_model_specs_by_id:
        raise ValueError(
            f"{context} requires non-model placement owner '{placement_owner_id}' for role {modeled_role}"
        )
    owner_spec = non_model_specs_by_id[placement_owner_id]

    outer_x_usage_ratio = _require_range(table, "outer_x_usage_ratio", context, expect_integer=False)
    outer_y_usage_ratio = _require_range(table, "outer_y_usage_ratio", context, expect_integer=False)
    outer_x_mm, outer_y_mm = _resolve_single_coil_outer_mm_ranges(
        role=modeled_role,
        owner_spec=owner_spec,
        outer_x_usage_ratio=outer_x_usage_ratio,
        outer_y_usage_ratio=outer_y_usage_ratio,
        context=context,
    )
    turn_count = _require_range(table, "turn_count", context, expect_integer=True)
    layer_count = _require_range(table, "layer_count", context, expect_integer=True)
    underlay_repeat_count = _require_underlay_repeat_count_range(
        table,
        context=context,
        role=modeled_role,
    )
    layer_gap_mm = _require_range(table, "layer_gap_mm", context, expect_integer=False)
    terminal_stub_length_mm = _require_range(table, "terminal_stub_length_mm", context, expect_integer=False)
    void_usage_ratio = _require_range(table, "void_usage_ratio", context, expect_integer=False)
    void_usage_ratio_candidates = _float_range_candidates(void_usage_ratio)
    if any(candidate <= 0.0 or candidate >= 1.0 for candidate in void_usage_ratio_candidates):
        raise ValueError(
            f"{context}.void_usage_ratio must realize to values > 0 and < 1 "
            f"(actual={void_usage_ratio_candidates})"
        )
    margin_ratio = _require_range(table, "margin_ratio", context, expect_integer=False)
    metal_fill_factor = _require_range(table, "metal_fill_factor", context, expect_integer=False)
    tx_allowed_keys = {
        "object_id",
        "role",
        "material",
        "model_state",
        "pcb_thickness_mm",
        "copper_thickness_mm",
        "outer_x_usage_ratio",
        "outer_y_usage_ratio",
        "turn_count",
        "layer_count",
        "underlay_repeat_count",
        "underlay_gap_mm",
        "wall_parallel_stack_present",
        "layer_gap_mm",
        "terminal_stub_length_mm",
        "void_usage_ratio",
        "margin_ratio",
        "metal_fill_factor",
        "terminal_path",
    }
    rx_allowed_keys = {
        "object_id",
        "role",
        "material",
        "model_state",
        "pcb_thickness_mm",
        "copper_thickness_mm",
        "outer_x_usage_ratio",
        "outer_y_usage_ratio",
        "turn_count",
        "layer_count",
        "underlay_repeat_count",
        "layer_gap_mm",
        "terminal_stub_length_mm",
        "void_usage_ratio",
        "margin_ratio",
        "metal_fill_factor",
        "terminal_path",
    }
    if modeled_role == "tx_single_coil":
        extra_keys = sorted(set(table.keys()) - tx_allowed_keys)
        if extra_keys:
            raise ValueError(
                f"{context} contains unsupported keys for {modeled_role} "
                f"(actual={extra_keys})"
            )
        return ModeledTxSingleCoilSpec(
            object_id=object_id,
            role="tx_single_coil",
            material=material,
            model_state=True,
            pcb_thickness_mm=pcb_thickness_mm,
            copper_thickness_mm=copper_thickness_mm,
            outer_x_usage_ratio=outer_x_usage_ratio,
            outer_y_usage_ratio=outer_y_usage_ratio,
            outer_x_mm=outer_x_mm,
            outer_y_mm=outer_y_mm,
            turn_count=turn_count,
            layer_count=layer_count,
            underlay_repeat_count=underlay_repeat_count,
            layer_gap_mm=layer_gap_mm,
            terminal_stub_length_mm=terminal_stub_length_mm,
            void_usage_ratio=void_usage_ratio,
            margin_ratio=margin_ratio,
            metal_fill_factor=metal_fill_factor,
            terminal_path=terminal_path,
            underlay_gap_mm=_require_underlay_gap_range(table, context=context),
            wall_parallel_stack_present=_require_wall_parallel_stack_present_range(table, context=context),
        )
    if "underlay_gap_mm" in table:
        raise ValueError(f"{context}.underlay_gap_mm is unsupported for rx_single_coil")
    if "wall_parallel_stack_present" in table:
        raise ValueError(f"{context}.wall_parallel_stack_present is unsupported for rx_single_coil")
    extra_keys = sorted(set(table.keys()) - rx_allowed_keys)
    if extra_keys:
        raise ValueError(
            f"{context} contains unsupported keys for {modeled_role} "
            f"(actual={extra_keys})"
        )
    return ModeledRxSingleCoilSpec(
        object_id=object_id,
        role="rx_single_coil",
        material=material,
        model_state=True,
        pcb_thickness_mm=pcb_thickness_mm,
        copper_thickness_mm=copper_thickness_mm,
        outer_x_usage_ratio=outer_x_usage_ratio,
        outer_y_usage_ratio=outer_y_usage_ratio,
        outer_x_mm=outer_x_mm,
        outer_y_mm=outer_y_mm,
        turn_count=turn_count,
        layer_count=layer_count,
        underlay_repeat_count=underlay_repeat_count,
        layer_gap_mm=layer_gap_mm,
        terminal_stub_length_mm=terminal_stub_length_mm,
        void_usage_ratio=void_usage_ratio,
        margin_ratio=margin_ratio,
        metal_fill_factor=metal_fill_factor,
        terminal_path=terminal_path,
    )


def _require_tx_rect_void_columns_connection_mode_range(
    table: dict[str, object],
    *,
    key: str,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, key, context, expect_integer=True)
    if (
        math.isclose(range_spec.start, float(_TX_RECT_VOID_COLUMNS_CONNECTION_MODE_EXPECTED[0]), rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(range_spec.end, float(_TX_RECT_VOID_COLUMNS_CONNECTION_MODE_EXPECTED[1]), rel_tol=0.0, abs_tol=1e-12)
        and range_spec.count == _TX_RECT_VOID_COLUMNS_CONNECTION_MODE_RANGE[2]
    ):
        return range_spec
    candidates = _integer_range_candidates(range_spec)
    if range_spec.count == 1 and len(candidates) == 1 and candidates[0] in _TX_RECT_VOID_COLUMNS_CONNECTION_MODE_EXPECTED:
        return range_spec
    raise ValueError(
        f"{context}.{key} must be [true, 0, 1, 2] "
        f"for tx_rect_void_columns connection modes "
        f"(actual={range_spec})"
    )


def _require_tx_rect_void_columns_layer_count_range(
    table: dict[str, object],
    *,
    key: str,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, key, context, expect_integer=True)
    if not (
        math.isclose(range_spec.start, _TX_RECT_VOID_COLUMNS_LAYER_COUNT_RANGE_START, rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(range_spec.end, _TX_RECT_VOID_COLUMNS_LAYER_COUNT_RANGE_END, rel_tol=0.0, abs_tol=1e-12)
        and range_spec.count == _TX_RECT_VOID_COLUMNS_LAYER_COUNT_RANGE_COUNT
    ):
        candidates = _integer_range_candidates(range_spec)
        if range_spec.count == 1 and len(candidates) == 1 and candidates[0] in _TX_RECT_VOID_COLUMNS_LAYER_COUNT_ALLOWED:
            return range_spec
        raise ValueError(
            f"{context}.{key} must be [true, 1, 4, 4] "
            f"(actual={range_spec})"
        )
    candidates = _integer_range_candidates(range_spec)
    if tuple(candidates) != _TX_RECT_VOID_COLUMNS_LAYER_COUNT_ALLOWED:
        raise ValueError(
            f"{context}.{key} must realize to values {_TX_RECT_VOID_COLUMNS_LAYER_COUNT_ALLOWED} "
            f"(actual={candidates})"
        )
    return range_spec


def _require_tx_rect_void_columns_layer_gap_mm_range(
    table: dict[str, object],
    *,
    key: str,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, key, context, expect_integer=False)
    if not (
        math.isclose(range_spec.start, _TX_RECT_VOID_COLUMNS_LAYER_GAP_MM_RANGE_START, rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(range_spec.end, _TX_RECT_VOID_COLUMNS_LAYER_GAP_MM_RANGE_END, rel_tol=0.0, abs_tol=1e-12)
        and range_spec.count == _TX_RECT_VOID_COLUMNS_LAYER_GAP_MM_RANGE_COUNT
    ):
        if (
            range_spec.count == 1
            and range_spec.start == range_spec.end
            and _TX_RECT_VOID_COLUMNS_LAYER_GAP_MM_RANGE_START <= range_spec.start <= _TX_RECT_VOID_COLUMNS_LAYER_GAP_MM_RANGE_END
        ):
            return range_spec
        raise ValueError(
            f"{context}.{key} must be [false, 1.0, 1.8, 5] "
            f"(actual={range_spec})"
        )
    return range_spec


def _require_tx_rect_void_columns_terminal_stub_length_mm_range(
    table: dict[str, object],
    *,
    key: str,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, key, context, expect_integer=False)
    if not (
        math.isclose(
            range_spec.start,
            _TX_RECT_VOID_COLUMNS_TERMINAL_STUB_LENGTH_MM_RANGE_START,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and math.isclose(
            range_spec.end,
            _TX_RECT_VOID_COLUMNS_TERMINAL_STUB_LENGTH_MM_RANGE_END,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and range_spec.count == _TX_RECT_VOID_COLUMNS_TERMINAL_STUB_LENGTH_MM_RANGE_COUNT
    ):
        if (
            range_spec.count == 1
            and math.isclose(range_spec.start, _TX_RECT_VOID_COLUMNS_TERMINAL_STUB_LENGTH_MM_RANGE_START, rel_tol=0.0, abs_tol=1e-12)
            and math.isclose(range_spec.end, _TX_RECT_VOID_COLUMNS_TERMINAL_STUB_LENGTH_MM_RANGE_END, rel_tol=0.0, abs_tol=1e-12)
        ):
            return range_spec
        raise ValueError(
            f"{context}.{key} must be [false, 10.0, 10.0, 1] "
            f"(actual={range_spec})"
        )
    return range_spec


def _require_tx_rect_void_columns_series_total_turn_count_range(
    table: dict[str, object],
    *,
    key: str,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, key, context, expect_integer=True)
    if not (
        math.isclose(range_spec.start, _TX_RECT_VOID_COLUMNS_SERIES_TOTAL_TURN_COUNT_RANGE_START, rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(range_spec.end, _TX_RECT_VOID_COLUMNS_SERIES_TOTAL_TURN_COUNT_RANGE_END, rel_tol=0.0, abs_tol=1e-12)
        and range_spec.count == _TX_RECT_VOID_COLUMNS_SERIES_TOTAL_TURN_COUNT_RANGE_COUNT
    ):
        candidates = _integer_range_candidates(range_spec)
        if (
            range_spec.count == 1
            and len(candidates) == 1
            and _TX_RECT_VOID_COLUMNS_SERIES_TOTAL_TURN_COUNT_RANGE_START <= candidates[0] <= _TX_RECT_VOID_COLUMNS_SERIES_TOTAL_TURN_COUNT_RANGE_END
        ):
            return range_spec
        raise ValueError(
            f"{context}.{key} must be [true, 1, 36, 36] "
            f"(actual={range_spec})"
        )
    candidates = _integer_range_candidates(range_spec)
    if candidates[0] < 1 or candidates[-1] > _TX_RECT_VOID_COLUMNS_SERIES_TOTAL_TURN_COUNT_RANGE_END:
        raise ValueError(
            f"{context}.{key} must realize to integers in [1, 36] "
            f"(actual={candidates})"
        )
    return range_spec


def _require_tx_rect_void_columns_parallel_total_turn_count_range(
    table: dict[str, object],
    *,
    key: str,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, key, context, expect_integer=True)
    if not (
        math.isclose(
            range_spec.start,
            _TX_RECT_VOID_COLUMNS_PARALLEL_TOTAL_TURN_COUNT_RANGE_START,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and math.isclose(
            range_spec.end,
            _TX_RECT_VOID_COLUMNS_PARALLEL_TOTAL_TURN_COUNT_RANGE_END,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and range_spec.count == _TX_RECT_VOID_COLUMNS_PARALLEL_TOTAL_TURN_COUNT_RANGE_COUNT
    ):
        candidates = _integer_range_candidates(range_spec)
        if (
            range_spec.count == 1
            and len(candidates) == 1
            and _TX_RECT_VOID_COLUMNS_PARALLEL_TOTAL_TURN_COUNT_RANGE_START <= candidates[0] <= _TX_RECT_VOID_COLUMNS_PARALLEL_TOTAL_TURN_COUNT_RANGE_END
        ):
            return range_spec
        raise ValueError(
            f"{context}.{key} must be [true, 1, 36, 36] "
            f"(actual={range_spec})"
        )
    return range_spec


def _require_tx_rect_void_columns_turn_weight_range(
    table: dict[str, object],
    *,
    key: str,
    context: str,
    expect_integer: bool,
    expected_start: float,
    expected_end: float,
    expected_count: int,
) -> RangeSpec:
    range_spec = _require_range(table, key, context, expect_integer=expect_integer)
    if not (
        math.isclose(range_spec.start, expected_start, rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(range_spec.end, expected_end, rel_tol=0.0, abs_tol=1e-12)
        and range_spec.count == expected_count
    ):
        if (
            range_spec.count == 1
            and range_spec.start == range_spec.end
            and expected_start <= range_spec.start <= expected_end
        ):
            return range_spec
        raise ValueError(
            f"{context}.{key} must be "
            f"[{str(expect_integer).lower()}, {expected_start}, {expected_end}, {expected_count}] "
            f"(actual={range_spec})"
        )
    return range_spec


def _parse_modeled_tx_rect_void_columns(
    raw_object: object,
    *,
    index: int,
    seen_object_ids: set[str],
    non_model_specs_by_id: dict[str, NonModelBoxSpec],
) -> ModeledTxRectVoidColumnsSpec:
    context = f"modeled_objects[{index}]"
    table = _require_table(raw_object, context)
    object_id = _require_non_empty_str(table, "object_id", context)
    if object_id in seen_object_ids:
        raise ValueError(f"duplicate object id: {object_id}")
    seen_object_ids.add(object_id)
    expected_object_id = modeled_object_id_for_role("tx_rect_void_columns")
    if object_id != expected_object_id:
        raise ValueError(
            f"prototype modeled object_id must be '{expected_object_id}' for role tx_rect_void_columns "
            f"(actual={object_id})"
        )

    role = _require_non_empty_str(table, "role", context)
    if role != "tx_rect_void_columns":
        raise ValueError(f"{context}.role must be 'tx_rect_void_columns' (actual={role!r})")

    raw_model_state = _require_key(table, "model_state", context)
    if not isinstance(raw_model_state, bool):
        raise TypeError(f"{context}.model_state must be bool")
    if raw_model_state is not True:
        raise ValueError(f"{context}.model_state must be true")

    material = _require_non_empty_str(table, "material", context)
    if material != "composite":
        raise ValueError(f"{context}.material must be 'composite' (actual={material})")
    pcb_thickness_mm = _require_float_value(table, "pcb_thickness_mm", context)
    if pcb_thickness_mm <= 0.0:
        raise ValueError(f"{context}.pcb_thickness_mm must be > 0")
    copper_thickness_mm = _require_float_value(table, "copper_thickness_mm", context)
    if copper_thickness_mm <= 0.0:
        raise ValueError(f"{context}.copper_thickness_mm must be > 0")

    terminal_node = _require_table(_require_key(table, "terminal_path", context), f"{context}.terminal_path")
    if set(terminal_node.keys()) != {"value"}:
        raise ValueError(f"{context}.terminal_path must contain only ['value']")
    terminal_path = _require_non_empty_str(terminal_node, "value", f"{context}.terminal_path")

    placement_owner_id = placement_owner_id_for_role("tx_rect_void_columns")
    if placement_owner_id not in non_model_specs_by_id:
        raise ValueError(
            f"{context} requires non-model placement owner '{placement_owner_id}' for role tx_rect_void_columns"
        )

    legacy_rejected_keys = sorted(
        key
        for key in (
            "turn_count_x0",
            "turn_count_x1",
            "turn_count_x2",
            "parallel_equivalent_turn_count",
            "column_connection_mode",
            "row_connection_mode",
        )
        if key in table
    )
    if legacy_rejected_keys:
        raise ValueError(
            f"{context} contains unsupported legacy keys for tx_rect_void_columns "
            f"(actual={legacy_rejected_keys})"
        )

    layer_count = _require_tx_rect_void_columns_layer_count_range(table, key="layer_count", context=context)
    layer_gap_mm = _require_tx_rect_void_columns_layer_gap_mm_range(table, key="layer_gap_mm", context=context)
    terminal_stub_length_mm = _require_tx_rect_void_columns_terminal_stub_length_mm_range(
        table,
        key="terminal_stub_length_mm",
        context=context,
    )
    void_usage_ratio = _require_range(table, "void_usage_ratio", context, expect_integer=False)
    void_usage_ratio_candidates = _float_range_candidates(void_usage_ratio)
    if any(candidate <= 0.0 or candidate >= 1.0 for candidate in void_usage_ratio_candidates):
        raise ValueError(
            f"{context}.void_usage_ratio must realize to values > 0 and < 1 "
            f"(actual={void_usage_ratio_candidates})"
        )
    margin_ratio = _require_range(table, "margin_ratio", context, expect_integer=False)
    metal_fill_factor = _require_range(table, "metal_fill_factor", context, expect_integer=False)
    connection_mode = _require_tx_rect_void_columns_connection_mode_range(table, key="connection_mode", context=context)
    series_total_turn_count = _require_tx_rect_void_columns_series_total_turn_count_range(
        table,
        key="series_total_turn_count",
        context=context,
    )
    parallel_total_turn_count = _require_tx_rect_void_columns_parallel_total_turn_count_range(
        table,
        key="parallel_total_turn_count",
        context=context,
    )
    turn_weight_a = _require_tx_rect_void_columns_turn_weight_range(
        table,
        key="turn_weight_a",
        context=context,
        expect_integer=False,
        expected_start=_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_A_RANGE_START,
        expected_end=_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_A_RANGE_END,
        expected_count=_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_A_RANGE_COUNT,
    )
    turn_weight_b = _require_tx_rect_void_columns_turn_weight_range(
        table,
        key="turn_weight_b",
        context=context,
        expect_integer=False,
        expected_start=_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_B_RANGE_START,
        expected_end=_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_B_RANGE_END,
        expected_count=_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_B_RANGE_COUNT,
    )
    turn_weight_c = _require_tx_rect_void_columns_turn_weight_range(
        table,
        key="turn_weight_c",
        context=context,
        expect_integer=False,
        expected_start=_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_C_RANGE_START,
        expected_end=_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_C_RANGE_END,
        expected_count=_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_C_RANGE_COUNT,
    )
    disallowed_keys = sorted(
        key
        for key in (
            "underlay_repeat_count",
            "underlay_gap_mm",
            "wall_parallel_stack_present",
            "ferrite_set_count",
            "ferrite_thickness_mm",
            "ferrite_gap_mm",
            "underlay_thickness_mm",
            "outer_x_usage_ratio",
            "outer_y_usage_ratio",
            "outer_x_mm",
            "outer_y_mm",
        )
        if key in table
    )
    if disallowed_keys:
        raise ValueError(
            f"{context} contains unsupported keys for tx_rect_void_columns "
            f"(actual={disallowed_keys})"
        )
    allowed_keys = {
        "object_id",
        "role",
        "material",
        "model_state",
        "pcb_thickness_mm",
        "copper_thickness_mm",
        "layer_count",
        "layer_gap_mm",
        "terminal_stub_length_mm",
        "void_usage_ratio",
        "margin_ratio",
        "metal_fill_factor",
        "terminal_path",
        "connection_mode",
        "series_total_turn_count",
        "parallel_total_turn_count",
        "turn_weight_a",
        "turn_weight_b",
        "turn_weight_c",
    }
    extra_keys = sorted(set(table.keys()) - allowed_keys)
    if extra_keys:
        raise ValueError(
            f"{context} contains unsupported keys for tx_rect_void_columns "
            f"(actual={extra_keys})"
        )
    return ModeledTxRectVoidColumnsSpec(
        object_id=object_id,
        role="tx_rect_void_columns",
        material=material,
        model_state=True,
        pcb_thickness_mm=pcb_thickness_mm,
        copper_thickness_mm=copper_thickness_mm,
        layer_count=layer_count,
        layer_gap_mm=layer_gap_mm,
        terminal_stub_length_mm=terminal_stub_length_mm,
        void_usage_ratio=void_usage_ratio,
        margin_ratio=margin_ratio,
        metal_fill_factor=metal_fill_factor,
        terminal_path=terminal_path,
        connection_mode=connection_mode,
        series_total_turn_count=series_total_turn_count,
        parallel_total_turn_count=parallel_total_turn_count,
        turn_weight_a=turn_weight_a,
        turn_weight_b=turn_weight_b,
        turn_weight_c=turn_weight_c,
    )


def _scaled_mm_range_from_usage_ratio(
    ratio_range: RangeSpec,
    *,
    span_mm: float,
    path: str,
) -> RangeSpec:
    if span_mm <= 0.0:
        raise ValueError(f"{path} owner span must be > 0 (actual={span_mm})")
    ratio_candidates = _float_range_candidates(ratio_range)
    if any(candidate <= 0.0 or candidate > 1.0 for candidate in ratio_candidates):
        raise ValueError(f"{path} must realize to values > 0 and <= 1 (actual={ratio_candidates})")
    return RangeSpec(
        is_integer=False,
        start=ratio_range.start * span_mm,
        end=ratio_range.end * span_mm,
        count=ratio_range.count,
    )


def _resolve_single_coil_outer_mm_ranges(
    *,
    role: ModeledSingleCoilRole,
    owner_spec: NonModelBoxSpec,
    outer_x_usage_ratio: RangeSpec,
    outer_y_usage_ratio: RangeSpec,
    context: str,
) -> tuple[RangeSpec, RangeSpec]:
    from peetsfea.tx_rect_void import profile_for_modeled_role

    profile = profile_for_modeled_role(role)
    if owner_spec.plane != profile.plane:
        raise ValueError(
            f"{context} placement owner plane must match modeled role plane "
            f"(owner={owner_spec.object_id}, owner_plane={owner_spec.plane}, role={role}, role_plane={profile.plane})"
        )
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if profile.plane == "XY":
        outer_x_owner_span_mm = owner_size_x
        outer_y_owner_span_mm = owner_size_y
    else:
        outer_x_owner_span_mm = owner_size_y
        outer_y_owner_span_mm = owner_size_z
    outer_x_mm = _scaled_mm_range_from_usage_ratio(
        outer_x_usage_ratio,
        span_mm=outer_x_owner_span_mm,
        path=f"{context}.outer_x_usage_ratio",
    )
    outer_y_mm = _scaled_mm_range_from_usage_ratio(
        outer_y_usage_ratio,
        span_mm=outer_y_owner_span_mm,
        path=f"{context}.outer_y_usage_ratio",
    )
    return (outer_x_mm, outer_y_mm)


def _parse_modeled_plate_stack(
    raw_object: object,
    *,
    index: int,
    seen_object_ids: set[str],
) -> ModeledPlateStackSpec:
    context = f"modeled_objects[{index}]"
    table = _require_table(raw_object, context)
    object_id = _require_non_empty_str(table, "object_id", context)
    if object_id in seen_object_ids:
        raise ValueError(f"duplicate object id: {object_id}")
    seen_object_ids.add(object_id)
    role = _require_non_empty_str(table, "role", context)
    if role not in ("tx_plate_stack", "rx_plate_stack"):
        raise ValueError(f"unsupported modeled object role: {role}")
    plate_role = cast(ModeledPlateStackRole, role)
    expected_object_id = modeled_object_id_for_role(plate_role)
    if object_id != expected_object_id:
        raise ValueError(
            f"prototype modeled object_id must be '{expected_object_id}' for role {role} "
            f"(actual={object_id})"
        )
    raw_model_state = _require_key(table, "model_state", context)
    if not isinstance(raw_model_state, bool):
        raise TypeError(f"{context}.model_state must be bool")
    if raw_model_state is not True:
        raise ValueError(f"{context}.model_state must be true")
    material = _require_non_empty_str(table, "material", context)
    if material != "composite":
        raise ValueError(f"{context}.material must be 'composite' (actual={material})")
    pcb_total_thickness_mm = _require_float_value(table, "pcb_total_thickness_mm", context)
    if pcb_total_thickness_mm <= 0.0:
        raise ValueError(f"{context}.pcb_total_thickness_mm must be > 0")
    copper_thickness_mm = _require_float_value(table, "copper_thickness_mm", context)
    if copper_thickness_mm <= 0.0:
        raise ValueError(f"{context}.copper_thickness_mm must be > 0")
    if pcb_total_thickness_mm <= copper_thickness_mm:
        raise ValueError(
            f"{context}.pcb_total_thickness_mm must be > copper_thickness_mm "
            f"(pcb_total_thickness_mm={pcb_total_thickness_mm}, copper_thickness_mm={copper_thickness_mm})"
        )
    turn_count = _require_range(table, "turn_count", context, expect_integer=True)
    turn_count_candidates = _integer_range_candidates(turn_count)
    if any(candidate < 2 for candidate in turn_count_candidates):
        raise ValueError(
            f"{context}.turn_count must realize to integers >= 2 "
            f"(actual={turn_count_candidates})"
        )
    metal_fill_factor = _require_range(table, "metal_fill_factor", context, expect_integer=False)
    metal_fill_factor_candidates = _float_range_candidates(metal_fill_factor)
    if any(candidate <= 0.0 or candidate > 0.6 for candidate in metal_fill_factor_candidates):
        raise ValueError(
            f"{context}.metal_fill_factor must realize to values > 0 and <= 0.6 "
            f"(actual={metal_fill_factor_candidates})"
        )
    z_usage_ratio = _require_range(table, "z_usage_ratio", context, expect_integer=False)
    z_usage_ratio_candidates = _float_range_candidates(z_usage_ratio)
    if any(candidate <= 0.0 or candidate > 1.0 for candidate in z_usage_ratio_candidates):
        raise ValueError(
            f"{context}.z_usage_ratio must realize to values > 0 and <= 1 "
            f"(actual={z_usage_ratio_candidates})"
        )
    y_usage_ratio = _require_range(table, "y_usage_ratio", context, expect_integer=False)
    y_usage_ratio_candidates = _float_range_candidates(y_usage_ratio)
    if any(candidate <= 0.0 or candidate > 1.0 for candidate in y_usage_ratio_candidates):
        raise ValueError(
            f"{context}.y_usage_ratio must realize to values > 0 and <= 1 "
            f"(actual={y_usage_ratio_candidates})"
        )
    tx_allowed_keys = {
        "object_id",
        "role",
        "material",
        "model_state",
        "pcb_total_thickness_mm",
        "copper_thickness_mm",
        "turn_count",
        "metal_fill_factor",
        "z_usage_ratio",
        "y_usage_ratio",
        "tx_coil_count",
        "tx_array_x_usage_ratio",
    }
    rx_allowed_keys = {
        "object_id",
        "role",
        "material",
        "model_state",
        "pcb_total_thickness_mm",
        "copper_thickness_mm",
        "turn_count",
        "metal_fill_factor",
        "z_usage_ratio",
        "y_usage_ratio",
    }
    if plate_role == "tx_plate_stack":
        extra_keys = sorted(set(table.keys()) - tx_allowed_keys)
        if extra_keys:
            raise ValueError(
                f"{context} contains unsupported keys for {plate_role} "
                f"(actual={extra_keys})"
            )
        tx_coil_count = _require_tx_plate_stack_coil_count_range(table, context=context)
        tx_array_x_usage_ratio = _require_tx_plate_stack_array_x_usage_ratio_range(table, context=context)
        return ModeledTxPlateStackSpec(
            object_id=object_id,
            role="tx_plate_stack",
            material=material,
            model_state=True,
            pcb_total_thickness_mm=pcb_total_thickness_mm,
            copper_thickness_mm=copper_thickness_mm,
            turn_count=turn_count,
            metal_fill_factor=metal_fill_factor,
            z_usage_ratio=z_usage_ratio,
            y_usage_ratio=y_usage_ratio,
            tx_coil_count=tx_coil_count,
            tx_array_x_usage_ratio=tx_array_x_usage_ratio,
        )
    if "tx_coil_count" in table:
        raise ValueError(f"{context}.tx_coil_count is unsupported for rx_plate_stack")
    if "tx_array_x_usage_ratio" in table:
        raise ValueError(f"{context}.tx_array_x_usage_ratio is unsupported for rx_plate_stack")
    extra_keys = sorted(set(table.keys()) - rx_allowed_keys)
    if extra_keys:
        raise ValueError(
            f"{context} contains unsupported keys for {plate_role} "
            f"(actual={extra_keys})"
        )
    return ModeledRxPlateStackSpec(
        object_id=object_id,
        role="rx_plate_stack",
        material=material,
        model_state=True,
        pcb_total_thickness_mm=pcb_total_thickness_mm,
        copper_thickness_mm=copper_thickness_mm,
        turn_count=turn_count,
        metal_fill_factor=metal_fill_factor,
        z_usage_ratio=z_usage_ratio,
        y_usage_ratio=y_usage_ratio,
    )


def _require_underlay_repeat_count_range(
    table: dict[str, object],
    *,
    context: str,
    role: ModeledSingleCoilRole,
) -> RangeSpec:
    range_spec = _require_range(table, "underlay_repeat_count", context, expect_integer=True)
    candidates = _integer_range_candidates(range_spec)
    if candidates == _UNDERLAY_REPEAT_COUNT_CANDIDATES:
        return range_spec
    if (
        range_spec.count == 1
        and range_spec.start == range_spec.end
        and len(candidates) == 1
        and candidates[0] in _UNDERLAY_REPEAT_COUNT_CANDIDATES
    ):
        return range_spec
    raise ValueError(
        f"{context}.underlay_repeat_count.range must be canonical [true, 0, 8, 5] "
        f"or fixed [true, n, n, 1] for n in {_UNDERLAY_REPEAT_COUNT_CANDIDATES} for {role} "
        f"(actual={[range_spec.is_integer, range_spec.start, range_spec.end, range_spec.count]})"
    )
    return range_spec


def _require_underlay_gap_range(
    table: dict[str, object],
    *,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, "underlay_gap_mm", context, expect_integer=False)
    candidates = _float_range_candidates(range_spec)
    if candidates == _TX_UNDERLAY_GAP_MM_CANDIDATES:
        return range_spec
    if (
        range_spec.count == 1
        and range_spec.start == range_spec.end
        and len(candidates) == 1
        and candidates[0] in _TX_UNDERLAY_GAP_MM_CANDIDATES
    ):
        return range_spec
    raise ValueError(
        f"{context}.underlay_gap_mm.range must be canonical [false, 1.0, 10.0, 4] "
        f"or fixed [false, g, g, 1] for g in {_TX_UNDERLAY_GAP_MM_CANDIDATES} for tx_single_coil "
        f"(actual={[range_spec.is_integer, range_spec.start, range_spec.end, range_spec.count]})"
    )
    return range_spec


def _require_wall_parallel_stack_present_range(
    table: dict[str, object],
    *,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, "wall_parallel_stack_present", context, expect_integer=True)
    candidates = _integer_range_candidates(range_spec)
    if candidates == _TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES:
        return range_spec
    if (
        range_spec.count == 1
        and range_spec.start == range_spec.end
        and len(candidates) == 1
        and candidates[0] in _TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES
    ):
        return range_spec
    raise ValueError(
        f"{context}.wall_parallel_stack_present.range must be canonical [true, 0, 1, 2] "
        f"or fixed [true, b, b, 1] for b in {_TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES} for tx_single_coil "
        f"(actual={[range_spec.is_integer, range_spec.start, range_spec.end, range_spec.count]})"
    )


def _require_tx_plate_stack_coil_count_range(
    table: dict[str, object],
    *,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, "tx_coil_count", context, expect_integer=True)
    candidates = _integer_range_candidates(range_spec)
    if candidates == _TX_PLATE_STACK_COIL_COUNT_CANDIDATES:
        return range_spec
    if (
        range_spec.count == 1
        and range_spec.start == range_spec.end
        and len(candidates) == 1
        and candidates[0] in _TX_PLATE_STACK_COIL_COUNT_CANDIDATES
    ):
        return range_spec
    raise ValueError(
        f"{context}.tx_coil_count.range must be canonical [true, 1, 4, 4] "
        f"or fixed [true, n, n, 1] for n in {_TX_PLATE_STACK_COIL_COUNT_CANDIDATES} for tx_plate_stack "
        f"(actual={[range_spec.is_integer, range_spec.start, range_spec.end, range_spec.count]})"
    )


def _is_canonical_tx_plate_stack_array_x_usage_ratio_range(range_spec: RangeSpec) -> bool:
    return (
        range_spec.is_integer is False
        and range_spec.start == _TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_START
        and range_spec.end == _TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_END
        and range_spec.count == _TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_COUNT
    )


def _require_tx_plate_stack_array_x_usage_ratio_range(
    table: dict[str, object],
    *,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, "tx_array_x_usage_ratio", context, expect_integer=False)
    if _is_canonical_tx_plate_stack_array_x_usage_ratio_range(range_spec):
        return range_spec
    if range_spec.count == 1 and range_spec.start == range_spec.end and 0.0 < range_spec.start <= 1.0:
        return range_spec
    raise ValueError(
        f"{context}.tx_array_x_usage_ratio.range must be canonical [false, 0.1, 0.6, 14] "
        "or fixed [false, r, r, 1] for 0 < r <= 1 for tx_plate_stack "
        f"(actual={[range_spec.is_integer, range_spec.start, range_spec.end, range_spec.count]})"
    )


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


def resolve_modeled_underlay_repeat_count(spec: ModeledSingleCoilSpec, *, seed: int) -> int:
    candidates = _integer_range_candidates(spec.underlay_repeat_count)
    if spec.role not in ("tx_single_coil", "rx_single_coil"):
        raise RuntimeError(f"unsupported modeled object role for underlay repeat resolution: {spec.role}")
    if candidates != _UNDERLAY_REPEAT_COUNT_CANDIDATES and not (
        len(candidates) == 1 and candidates[0] in _UNDERLAY_REPEAT_COUNT_CANDIDATES
    ):
        raise ValueError(
            f"{spec.role}.underlay_repeat_count must realize to canonical candidates "
            f"{_UNDERLAY_REPEAT_COUNT_CANDIDATES} or a fixed single candidate from that set "
            f"(actual={candidates})"
        )
    if len(candidates) == 1:
        repeat_count = candidates[0]
    else:
        range_path = f"modeled_objects.{spec.object_id}.underlay_repeat_count"
        index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
        repeat_count = candidates[index]
    return repeat_count


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


def _require_type2_schema_id(root: dict[str, object], *, context: str) -> str:
    schema_id = _require_non_empty_str(root, "schema_id", context)
    if schema_id != _TYPE2_SCHEMA_ID:
        raise ValueError(
            f"{context}.schema_id must be '{_TYPE2_SCHEMA_ID}' for active type2 inputs "
            f"(actual={schema_id!r})"
        )
    return schema_id


def load_type2_step_spec(toml_path: Path) -> Type2StepSpec:
    raw_text = toml_path.read_text(encoding="utf-8")
    raw_spec = tomllib.loads(raw_text)
    root = _require_table(raw_spec, toml_path.name)
    _require_type2_schema_id(root, context=toml_path.name)

    design = _require_table(_require_key(root, "design", toml_path.name), "design")
    units = _require_non_empty_str(design, "units", "design")
    if units != "mm":
        raise ValueError(f"design.units must be 'mm' (actual={units})")

    raw_non_model_objects = _require_key(root, "non_model_objects", toml_path.name)
    if not isinstance(raw_non_model_objects, list):
        raise TypeError("non_model_objects must be an array of tables")
    if len(raw_non_model_objects) == 0:
        raise ValueError("non_model_objects must not be empty")

    raw_modeled_objects = _require_key(root, "modeled_objects", toml_path.name)
    if not isinstance(raw_modeled_objects, list):
        raise TypeError("modeled_objects must be an array of tables")
    if len(raw_modeled_objects) == 0:
        raise ValueError("modeled_objects must not be empty")
    constraints: tuple[Type2ConstraintRule, ...] = ()
    if "constraints" in root:
        constraints = _parse_constraints(root["constraints"], context=f"{toml_path.name}.constraints")

    seen_object_ids: set[str] = set()
    non_model_box_specs: list[NonModelBoxSpec] = []
    non_model_derived_specs: list[NonModelDerivedSpec] = []
    for index, raw_object in enumerate(raw_non_model_objects):
        context = f"{toml_path.name}.non_model_objects[{index}]"
        table = _require_table(raw_object, context)
        kind = _require_non_empty_str(table, "kind", context)
        if kind == "tx_region_actual":
            non_model_derived_specs.append(
                _parse_non_model_tx_region_actual(raw_object, index=index, seen_object_ids=seen_object_ids)
            )
            continue
        if kind == "tx_region_actual_stack_space":
            non_model_derived_specs.append(
                _parse_non_model_tx_region_actual_stack_space(raw_object, index=index, seen_object_ids=seen_object_ids)
            )
            continue
        non_model_box_specs.append(_parse_non_model_box(raw_object, index=index, seen_object_ids=seen_object_ids))
    non_model_objects = tuple(non_model_box_specs)
    non_model_derived_objects = tuple(non_model_derived_specs)
    non_model_specs_by_id = {spec.object_id: spec for spec in non_model_objects}
    tx_region_actual_spec_count = sum(
        1 for spec in non_model_derived_objects if isinstance(spec, NonModelTxRegionActualSpec)
    )
    if tx_region_actual_spec_count != 1:
        raise ValueError(
            f"{toml_path.name} requires exactly one tx_region_actual derived non-model object "
            f"(actual={tx_region_actual_spec_count})"
        )
    tx_region_actual_stack_space_spec_count = sum(
        1 for spec in non_model_derived_objects if isinstance(spec, NonModelTxRegionActualStackSpaceSpec)
    )
    if tx_region_actual_stack_space_spec_count != 1:
        raise ValueError(
            f"{toml_path.name} requires exactly one tx_region_actual_stack_space derived non-model object "
            f"(actual={tx_region_actual_stack_space_spec_count})"
        )
    for spec in non_model_derived_objects:
        if isinstance(spec, NonModelTxRegionActualStackSpaceSpec):
            continue
        if spec.source_region_id not in non_model_specs_by_id:
            raise ValueError(
                f"{toml_path.name} requires tx_region_actual source region '{spec.source_region_id}' in non_model_objects"
            )
        source_spec = non_model_specs_by_id[spec.source_region_id]
        if source_spec.kind != "tx_region":
            raise ValueError(
                f"{toml_path.name} tx_region_actual source region must have kind 'tx_region' "
                f"(actual={source_spec.kind!r})"
            )
    modeled_objects_list: list[ModeledObjectSpec] = []
    for index, raw_object in enumerate(raw_modeled_objects):
        context = f"{toml_path.name}.modeled_objects[{index}]"
        table = _require_table(raw_object, context)
        role = _require_non_empty_str(table, "role", context)
        if role == "tx_rect_void_columns":
            modeled_objects_list.append(
                _parse_modeled_tx_rect_void_columns(
                    raw_object,
                    index=index,
                    seen_object_ids=seen_object_ids,
                    non_model_specs_by_id=non_model_specs_by_id,
                )
            )
            continue
        if role in ("tx_plate_stack", "rx_plate_stack"):
            modeled_objects_list.append(
                _parse_modeled_plate_stack(raw_object, index=index, seen_object_ids=seen_object_ids)
            )
            continue
        modeled_objects_list.append(
            _parse_modeled_single_coil(
                raw_object,
                index=index,
                seen_object_ids=seen_object_ids,
                non_model_specs_by_id=non_model_specs_by_id,
            )
        )
    modeled_objects = tuple(modeled_objects_list)
    type2_step_spec = Type2StepSpec(
        source_toml_path=str(toml_path),
        simulation=_parse_simulation_policy(root, context=toml_path.name),
        outputs=parse_outputs_table(_require_key(root, "outputs", toml_path.name), context=f"{toml_path.name}.outputs"),
        non_model_objects=non_model_objects,
        non_model_derived_objects=non_model_derived_objects,
        modeled_objects=modeled_objects,
        constraints=constraints,
    )
    _validate_constraints_for_spec(constraints, spec=type2_step_spec, context=toml_path.name)
    return type2_step_spec


def _format_range(range_spec: RangeSpec) -> str:
    is_integer = "true" if range_spec.is_integer else "false"
    return f"[{is_integer}, {range_spec.start}, {range_spec.end}, {range_spec.count}]"


def render_tx_rect_void_toml(spec: ModeledSingleCoilCommonSpec) -> str:
    return "\n".join(
        (
            'spec_version = "0.2.22"',
            'schema_id = "peetsfea.tx_rect_void_coil.step.v1"',
            "runtime_compatible = false",
            "",
            "[design]",
            'units = "mm"',
            "",
            "[manufacturing]",
            f"pcb_thickness_mm = {spec.pcb_thickness_mm}",
            f"copper_thickness_mm = {spec.copper_thickness_mm}",
            "",
            "[tx_coil.outer_x_mm]",
            f"range = {_format_range(spec.outer_x_mm)}",
            "[tx_coil.outer_y_mm]",
            f"range = {_format_range(spec.outer_y_mm)}",
            "[tx_coil.turn_count]",
            f"range = {_format_range(spec.turn_count)}",
            "[tx_coil.layer_count]",
            f"range = {_format_range(spec.layer_count)}",
            "[tx_coil.layer_gap_mm]",
            f"range = {_format_range(spec.layer_gap_mm)}",
            "[tx_coil.terminal_stub_length_mm]",
            f"range = {_format_range(spec.terminal_stub_length_mm)}",
            "[tx_coil.void_usage_ratio]",
            f"range = {_format_range(spec.void_usage_ratio)}",
            "[tx_coil.margin_ratio]",
            f"range = {_format_range(spec.margin_ratio)}",
            "[tx_coil.metal_fill_factor]",
            f"range = {_format_range(spec.metal_fill_factor)}",
            "[tx_coil.terminal_path]",
            f'value = "{spec.terminal_path}"',
            "",
        )
    )


from peetsfea.type2_step_spec_modeled import _format_range
from peetsfea.type2_step_spec_modeled import _parse_modeled_plate_stack
from peetsfea.type2_step_spec_modeled import _parse_modeled_single_coil
from peetsfea.type2_step_spec_modeled import _parse_modeled_tx_rect_void_columns
from peetsfea.type2_step_spec_modeled import _resolve_single_coil_outer_mm_ranges
from peetsfea.type2_step_spec_modeled import _require_tx_plate_stack_array_x_usage_ratio_range
from peetsfea.type2_step_spec_modeled import _require_tx_plate_stack_coil_count_range
from peetsfea.type2_step_spec_modeled import _require_tx_rect_void_columns_connection_mode_range
from peetsfea.type2_step_spec_modeled import _require_tx_rect_void_columns_layer_count_range
from peetsfea.type2_step_spec_modeled import _require_tx_rect_void_columns_layer_gap_mm_range
from peetsfea.type2_step_spec_modeled import _require_tx_rect_void_columns_parallel_total_turn_count_range
from peetsfea.type2_step_spec_modeled import _require_tx_rect_void_columns_series_total_turn_count_range
from peetsfea.type2_step_spec_modeled import _require_tx_rect_void_columns_terminal_stub_length_mm_range
from peetsfea.type2_step_spec_modeled import _require_tx_rect_void_columns_turn_weight_range
from peetsfea.type2_step_spec_modeled import _require_underlay_gap_range
from peetsfea.type2_step_spec_modeled import _require_underlay_repeat_count_range
from peetsfea.type2_step_spec_modeled import _require_wall_parallel_stack_present_range
from peetsfea.type2_step_spec_modeled import _resolve_single_coil_outer_mm_ranges
from peetsfea.type2_step_spec_modeled import render_tx_rect_void_toml
from peetsfea.type2_step_spec_modeled import _scaled_mm_range_from_usage_ratio
from peetsfea.type2_step_spec_sampling import resolve_modeled_plate_stack_metal_fill_factor
from peetsfea.type2_step_spec_sampling import resolve_modeled_plate_stack_turn_count
from peetsfea.type2_step_spec_sampling import resolve_modeled_plate_stack_y_usage_ratio
from peetsfea.type2_step_spec_sampling import resolve_modeled_plate_stack_z_usage_ratio
from peetsfea.type2_step_spec_sampling import resolve_modeled_tx_array_x_usage_ratio
from peetsfea.type2_step_spec_sampling import resolve_modeled_tx_coil_count
from peetsfea.type2_step_spec_sampling import resolve_modeled_underlay_gap_mm
from peetsfea.type2_step_spec_sampling import resolve_modeled_underlay_repeat_count
from peetsfea.type2_step_spec_sampling import resolve_modeled_wall_parallel_stack_present
from peetsfea.type2_step_spec_sampling import resolve_non_model_tx_region_actual_stack_space_tilt_enabled
from peetsfea.type2_step_spec_sampling import _float_range_candidates
from peetsfea.type2_step_spec_sampling import _integer_range_candidates
from peetsfea.type2_step_spec_sampling import _is_canonical_tx_plate_stack_array_x_usage_ratio_range
from peetsfea.type2_step_spec_sampling import _resolve_seeded_candidate_index


__all__ = [
    "ModeledObjectSpec",
    "ModeledObjectRole",
    "ModeledPlateStackRole",
    "ModeledPlateStackSpec",
    "ModeledRxPlateStackSpec",
    "ModeledRxSingleCoilSpec",
    "ModeledSingleCoilRole",
    "ModeledSingleCoilCommonSpec",
    "ModeledSingleCoilSpec",
    "ModeledTxPlateStackSpec",
    "ModeledTxSingleCoilSpec",
    "ModeledTxRectVoidColumnsSpec",
    "Type2ConstraintComparisonOperator",
    "Type2ConstraintFuncRef",
    "Type2ConstraintPathRef",
    "Type2ConstraintRule",
    "Type2ConstraintValueRef",
    "NonModelBoxSpec",
    "NonModelDerivedSpec",
    "NonModelTxRegionActualSpec",
    "NonModelTxRegionActualStackSpaceSpec",
    "Point3",
    "RangeSpec",
    "Type2SimulationPolicy",
    "Type2StepSpec",
    "load_type2_step_spec",
    "modeled_object_id_for_role",
    "modeled_plane_for_role",
    "placement_owner_id_for_role",
    "resolve_modeled_plate_stack_metal_fill_factor",
    "resolve_modeled_plate_stack_turn_count",
    "resolve_modeled_plate_stack_z_usage_ratio",
    "resolve_modeled_plate_stack_y_usage_ratio",
    "resolve_modeled_tx_array_x_usage_ratio",
    "resolve_modeled_tx_coil_count",
    "resolve_modeled_underlay_gap_mm",
    "resolve_modeled_underlay_repeat_count",
    "resolve_modeled_wall_parallel_stack_present",
    "resolve_non_model_tx_region_actual_stack_space_tilt_enabled",
    "render_tx_rect_void_toml",
]

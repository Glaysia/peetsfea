from __future__ import annotations

import math
from typing import cast

from peetsfea.tx_rect_void import profile_for_modeled_role
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
from peetsfea.type2_step_spec_types import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec_types import ModeledTxOuterSingleCoilSpec
from peetsfea.type2_step_spec_types import ModeledTxRectVoidColumnsSpec
from peetsfea.type2_step_spec_types import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec_types import modeled_object_id_for_role
from peetsfea.type2_step_spec_types import modeled_plane_for_role
from peetsfea.type2_step_spec_types import placement_owner_id_for_role
from peetsfea.type2_step_spec_types import NonModelBoxSpec
from peetsfea.type2_step_spec_types import RangeSpec
from peetsfea.type2_step_spec_types import _UNDERLAY_REPEAT_COUNT_CANDIDATES
from peetsfea.type2_step_spec_types import _TX_PLATE_STACK_COIL_COUNT_CANDIDATES
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_CONNECTION_MODE_EXPECTED
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_CONNECTION_MODE_RANGE
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_COUNT
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_END
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_START
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_LAYER_COUNT_ALLOWED
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_LAYER_COUNT_RANGE_COUNT
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_LAYER_COUNT_RANGE_END
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_LAYER_COUNT_RANGE_START
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_LAYER_GAP_MM_RANGE_COUNT
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_LAYER_GAP_MM_RANGE_END
from peetsfea.type2_step_spec_types import _TX_RECT_VOID_COLUMNS_LAYER_GAP_MM_RANGE_START
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
from peetsfea.type2_step_spec_types import _TX_UNDERLAY_GAP_MM_CANDIDATES
from peetsfea.type2_step_spec_types import _TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES
from peetsfea.type2_step_spec_non_model import _float_range_candidates
from peetsfea.type2_step_spec_non_model import _integer_range_candidates
from peetsfea.type2_step_spec_non_model import _require_float_value
from peetsfea.type2_step_spec_non_model import _require_key
from peetsfea.type2_step_spec_non_model import _require_non_empty_str
from peetsfea.type2_step_spec_non_model import _require_range
from peetsfea.type2_step_spec_non_model import _require_table
from peetsfea.type2_step_spec_sampling import _is_canonical_tx_plate_stack_array_x_usage_ratio_range


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


def _require_tx_rect_void_columns_equivalent_turn_count_range(
    table: dict[str, object],
    *,
    key: str,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, key, context, expect_integer=False)
    if not (
        math.isclose(
            range_spec.start,
            _TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_START,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and math.isclose(
            range_spec.end,
            _TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_END,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and range_spec.count == _TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_COUNT
    ):
        candidates = _float_range_candidates(range_spec)
        if (
            range_spec.count == 1
            and range_spec.start == range_spec.end
            and len(candidates) == 1
            and _TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_START
            <= candidates[0]
            <= _TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_END
        ):
            return range_spec
        raise ValueError(
            f"{context}.{key} must be [false, 0.1111111111111111, 31.0, 100] "
            f"(actual={range_spec})"
        )
    candidates = _float_range_candidates(range_spec)
    if (
        candidates[0] < _TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_START
        and not math.isclose(
            candidates[0],
            _TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_START,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    ) or (
        candidates[-1] > _TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_END
        and not math.isclose(
            candidates[-1],
            _TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_END,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    ):
        raise ValueError(
            f"{context}.{key} must realize to values in [0.1111111111111111, 31.0] "
            f"(actual={candidates})"
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


def _parse_modeled_single_coil(
    raw_object: object,
    *,
    index: int,
    seen_object_ids: set[str],
    non_model_specs_by_id: dict[str, NonModelBoxSpec],
) -> ModeledSingleCoilSpec:
    context = f"modeled_objects[{index}]"
    table = _require_table(raw_object, context)
    object_id = _require_non_empty_str(table, "object_id", context)
    if object_id in seen_object_ids:
        raise ValueError(f"duplicate object id: {object_id}")
    seen_object_ids.add(object_id)

    role = _require_non_empty_str(table, "role", context)
    if role not in ("tx_single_coil", "tx_inner_single_coil", "rx_single_coil"):
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
    if placement_owner_id not in non_model_specs_by_id and modeled_role != "tx_inner_single_coil":
        raise ValueError(
            f"{context} requires non-model placement owner '{placement_owner_id}' for role {modeled_role}"
        )
    if modeled_role == "tx_inner_single_coil":
        if "tx_region" not in non_model_specs_by_id:
            raise ValueError(f"{context} requires non-model source owner 'tx_region' for role {modeled_role}")
        owner_spec = non_model_specs_by_id["tx_region"]
    else:
        assert placement_owner_id in non_model_specs_by_id
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
    tx_inner_allowed_keys = rx_allowed_keys | {"tx_outer_terminal_path"}
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
    if modeled_role == "tx_inner_single_coil":
        if "underlay_gap_mm" in table:
            raise ValueError(f"{context}.underlay_gap_mm is unsupported for tx_inner_single_coil")
        if "wall_parallel_stack_present" in table:
            raise ValueError(f"{context}.wall_parallel_stack_present is unsupported for tx_inner_single_coil")
        extra_keys = sorted(set(table.keys()) - tx_inner_allowed_keys)
        if extra_keys:
            raise ValueError(
                f"{context} contains unsupported keys for {modeled_role} "
                f"(actual={extra_keys})"
            )
        underlay_candidates = _integer_range_candidates(underlay_repeat_count)
        if underlay_candidates != (0,):
            raise ValueError(
                f"{context}.underlay_repeat_count must be fixed to [true, 0, 0, 1] for tx_inner_single_coil "
                f"(actual={underlay_candidates})"
            )
        return ModeledTxInnerSingleCoilSpec(
            object_id=object_id,
            role="tx_inner_single_coil",
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
            "series_total_turn_count",
            "parallel_total_turn_count",
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
    equivalent_turn_count = _require_tx_rect_void_columns_equivalent_turn_count_range(
        table,
        key="equivalent_turn_count",
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
        "equivalent_turn_count",
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
        equivalent_turn_count=equivalent_turn_count,
        turn_weight_a=turn_weight_a,
        turn_weight_b=turn_weight_b,
        turn_weight_c=turn_weight_c,
    )


def parse_modeled_object(
    raw_object: object,
    *,
    index: int,
    seen_object_ids: set[str],
    non_model_specs_by_id: dict[str, NonModelBoxSpec],
) -> ModeledObjectSpec:
    context = f"modeled_objects[{index}]"
    table = _require_table(raw_object, context)
    role = _require_non_empty_str(table, "role", context)
    if role in ("tx_single_coil", "tx_rect_void_columns", "tx_plate_stack"):
        raise ValueError(f"{context}.role is unsupported in active RxOnly type2 mode (actual={role!r})")
    if role == "tx_inner_single_coil":
        return _parse_modeled_single_coil(
            raw_object,
            index=index,
            seen_object_ids=seen_object_ids,
            non_model_specs_by_id=non_model_specs_by_id,
        )
    if role == "rx_plate_stack":
        return _parse_modeled_plate_stack(raw_object, index=index, seen_object_ids=seen_object_ids)
    if role == "rx_single_coil":
        return _parse_modeled_single_coil(
            raw_object,
            index=index,
            seen_object_ids=seen_object_ids,
            non_model_specs_by_id=non_model_specs_by_id,
        )
    raise ValueError(f"unsupported modeled object role: {role}")


def _parse_tx_outer_terminal_path_selector(raw_object: object, *, index: int) -> str:
    context = f"modeled_objects[{index}]"
    table = _require_table(raw_object, context)
    role = _require_non_empty_str(table, "role", context)
    if "tx_outer_terminal_path" not in table:
        raise ValueError(f"{context}.tx_outer_terminal_path selector is missing")
    if role != "tx_inner_single_coil":
        raise ValueError(
            f"{context}.tx_outer_terminal_path is supported only on tx_inner_single_coil "
            f"(actual_role={role!r})"
        )
    selector_node = _require_table(
        _require_key(table, "tx_outer_terminal_path", context),
        f"{context}.tx_outer_terminal_path",
    )
    if set(selector_node.keys()) != {"value"}:
        raise ValueError(f"{context}.tx_outer_terminal_path must contain only ['value']")
    terminal_path = _require_non_empty_str(selector_node, "value", f"{context}.tx_outer_terminal_path")
    if terminal_path != "A_cw_to_a":
        raise ValueError(
            f"{context}.tx_outer_terminal_path.value must be 'A_cw_to_a' "
            f"for tx_outer_single_coil (actual={terminal_path!r})"
        )
    return terminal_path


def append_tx_outer_single_coil_companion_specs(
    raw_modeled_objects: list[object],
    modeled_objects: tuple[ModeledObjectSpec, ...],
) -> tuple[ModeledObjectSpec, ...]:
    selector_indexes = tuple(
        index
        for index, raw_object in enumerate(raw_modeled_objects)
        if "tx_outer_terminal_path" in _require_table(raw_object, f"modeled_objects[{index}]")
    )
    if len(selector_indexes) == 0:
        return modeled_objects
    if len(selector_indexes) != 1:
        raise ValueError(
            "tx_outer_terminal_path selector must appear exactly once when deriving tx_outer_single_coil "
            f"(actual={len(selector_indexes)})"
        )
    selector_index = selector_indexes[0]
    terminal_path = _parse_tx_outer_terminal_path_selector(raw_modeled_objects[selector_index], index=selector_index)
    tx_inner_specs = tuple(spec for spec in modeled_objects if isinstance(spec, ModeledTxInnerSingleCoilSpec))
    if len(tx_inner_specs) != 1:
        raise ValueError(
            "tx_outer_terminal_path selector requires exactly one tx_inner_single_coil companion "
            f"(actual={len(tx_inner_specs)})"
        )
    tx_inner_spec = tx_inner_specs[0]
    companion = ModeledTxOuterSingleCoilSpec(
        object_id=modeled_object_id_for_role("tx_outer_single_coil"),
        role="tx_outer_single_coil",
        material=tx_inner_spec.material,
        model_state=True,
        pcb_thickness_mm=tx_inner_spec.pcb_thickness_mm,
        copper_thickness_mm=tx_inner_spec.copper_thickness_mm,
        outer_x_usage_ratio=tx_inner_spec.outer_x_usage_ratio,
        outer_y_usage_ratio=tx_inner_spec.outer_y_usage_ratio,
        outer_x_mm=tx_inner_spec.outer_x_mm,
        outer_y_mm=tx_inner_spec.outer_y_mm,
        turn_count=tx_inner_spec.turn_count,
        layer_count=tx_inner_spec.layer_count,
        underlay_repeat_count=tx_inner_spec.underlay_repeat_count,
        layer_gap_mm=tx_inner_spec.layer_gap_mm,
        terminal_stub_length_mm=tx_inner_spec.terminal_stub_length_mm,
        void_usage_ratio=tx_inner_spec.void_usage_ratio,
        margin_ratio=tx_inner_spec.margin_ratio,
        metal_fill_factor=tx_inner_spec.metal_fill_factor,
        terminal_path=terminal_path,
        derived_from_object_id="tx_inner_rect_void_coil",
    )
    existing_object_ids = tuple(spec.object_id for spec in modeled_objects)
    if companion.object_id in existing_object_ids:
        raise ValueError(f"duplicate object id: {companion.object_id}")
    return (*modeled_objects, companion)


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


__all__ = [
    "modeled_object_id_for_role",
    "append_tx_outer_single_coil_companion_specs",
    "modeled_plane_for_role",
    "parse_modeled_object",
    "placement_owner_id_for_role",
    "render_tx_rect_void_toml",
]

from __future__ import annotations

from collections.abc import Callable
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypedDict, cast

from peetsfea.spec.loader import TOMLTable
from peetsfea.type2_rect_void_feasibility import min_centered_rect_void_trace_width_mm
from peetsfea.type2_step_spec import ModeledPlateStackSpec
from peetsfea.type2_step_spec import ModeledRxSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec import NonModelDerivedSpec
from peetsfea.type2_step_spec import NonModelTxRegionActualSpec
from peetsfea.type2_step_spec import NonModelTxRegionActualStackSpaceSpec
from peetsfea.type2_step_spec import NonModelTxRegionSpec
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import Type2StepSpec

REPO_ROOT = Path(__file__).resolve().parents[2]
SampledScalar = int | float
DesignVariableEntry = tuple[str, str]
_SampleExporter = Callable[..., object]
_INTEGER_RANGE_FIELD_NAMES = (
    "turn_count",
    "connection_mode",
    "layer_count",
    "underlay_repeat_count",
    "void_stack_present",
    "sheet_present",
    "wall_parallel_stack_present",
    "tx_coil_count",
    "x_division_count",
    "y_division_count",
)
_SAMPLED_METADATA_TABLE = "sampled"
_SAMPLED_SINGLE_COIL_ROLES: frozenset[str] = frozenset({"tx_inner_single_coil", "rx_single_coil"})
_PLATE_STACK_ROLE_SUFFIX = "_plate_stack"
_TX_RECT_VOID_COLUMNS_ROLE = "tx_rect_void_columns"
_UNSUPPORTED_RXONLY_TX_MODELED_ROLES: frozenset[str] = frozenset(
    {"tx_single_coil", "tx_plate_stack", _TX_RECT_VOID_COLUMNS_ROLE}
)
_TYPE2_CONSTRAINT_RETRY_LIMIT: Final[int] = 64
_CONSTRAINT_COMPARISON_OPERATORS: Final[frozenset[str]] = frozenset({"<", "<=", ">", ">=", "==", "!="})


class _ConstraintPathRef(TypedDict):
    path: str


class _ConstraintValueRef(TypedDict):
    value: int | float


class _ConstraintFuncRef(TypedDict):
    func: str


class _Type2ConstraintRule(TypedDict):
    id: str
    kind: str
    message: str
    enabled: bool
    lhs: _ConstraintPathRef | _ConstraintFuncRef | _ConstraintValueRef
    op: str
    rhs: _ConstraintPathRef | _ConstraintFuncRef | _ConstraintValueRef


class Type2SampleMetadata(TypedDict):
    source_toml_path: str
    seed: int
    sample_index: int
    head_hash4: str
    retry_number: int
    sampled_owner_paths: list[str]


class Type2SampleManifestEntry(TypedDict):
    design_id: str
    seed: int
    sample_index: int
    retry_number: int
    source_toml_path: str
    sampled_toml_path: str
    design_dir: str
    scene_step_path: str
    step_ledger_path: str
    imported_ledger_path: str
    aedt_path: str
    sampled_owner_paths: list[str]


_SampleProgressReporter = Callable[[int, int, "Type2SampleManifestEntry"], None]
_SampleStepStage = Literal["start", "build_scene", "export_scene_step", "finalize_step_artifacts", "done"]
_SampleStepStageReporter = Callable[[_SampleStepStage, Type2SampleManifestEntry], None]


class Type2SampleManifestConfig(TypedDict):
    source_toml_path: str
    seed_first: int
    seed_n: int
    sampler_n: int
    make_step_on_sample: bool
    aedt_builder_n: int


class Type2SampleManifestDocument(TypedDict):
    config: Type2SampleManifestConfig
    entries: list[Type2SampleManifestEntry]


@dataclass(frozen=True)
class PreparedType2Build:
    design_id: str
    seed: int
    source_toml_path: Path
    sampled_toml_path: Path
    design_dir: Path
    scene_step_path: Path
    step_ledger_path: Path
    imported_ledger_path: Path
    aedt_path: Path
    sampled_owner_paths: tuple[str, ...]
    modeled_roles: tuple[str, ...]
    design_variables: tuple[DesignVariableEntry, ...]


def _modeled_spec_role(modeled_spec: object) -> str:
    assert hasattr(modeled_spec, "role"), "type2 modeled spec must expose role"
    raw_role = getattr(modeled_spec, "role")
    assert isinstance(raw_role, str), "type2 modeled spec role must be str"
    return raw_role


def _modeled_roles(spec: Type2StepSpec) -> tuple[str, ...]:
    return tuple(_modeled_spec_role(modeled_spec) for modeled_spec in spec.modeled_objects)


def _non_model_range_owner_specs(spec: Type2StepSpec) -> tuple[tuple[str, RangeSpec], ...]:
    owner_specs: list[tuple[str, RangeSpec]] = []
    for non_model_spec in spec.non_model_objects:
        if isinstance(non_model_spec, NonModelTxRegionSpec):
            owner_specs.extend(_tx_region_reference_line_range_owner_specs(non_model_spec))
    for non_model_spec in spec.non_model_derived_objects:
        owner_specs.extend(_derived_non_model_range_owner_specs(non_model_spec))
    return tuple(owner_specs)


def _parse_constraint_table(raw_value: object, path: str) -> TOMLTable:
    if not isinstance(raw_value, dict):
        raise ValueError(f"{path} must be a table/object")
    return cast(TOMLTable, raw_value)


def _constraint_id_for_rule(index: int) -> str:
    return f"constraints.rules[{index}]"


def _parse_constraint_func(raw_text: str, context: str) -> tuple[str, tuple[str, ...]]:
    text = raw_text.strip()
    if not text.endswith(")") or "(" not in text:
        raise ValueError(
            f"{context}.func must be in the form sum(arg_1, arg_2, ...), "
            "tx_inner_min_trace_width_mm(tx_inner_rect_void_coil), or rx_min_trace_width_mm(rx_rect_void_coil)"
        )
    open_index = text.find("(")
    function_name = text[:open_index].strip()
    if function_name not in ("sum", "tx_inner_min_trace_width_mm", "rx_min_trace_width_mm"):
        raise ValueError(
            f"{context}.func must use one of ['sum', 'tx_inner_min_trace_width_mm', 'rx_min_trace_width_mm'] "
            f"(actual={function_name!r})"
        )
    body = text[open_index + 1 : -1].strip()
    args = _split_function_args(body, context=f"{context}.func")
    if len(args) == 0:
        raise ValueError(f"{context}.func {function_name}() must contain at least one argument")
    if function_name == "tx_inner_min_trace_width_mm" and len(args) != 1:
        raise ValueError(f"{context}.func tx_inner_min_trace_width_mm() must contain exactly one argument")
    if function_name == "rx_min_trace_width_mm" and len(args) != 1:
        raise ValueError(f"{context}.func rx_min_trace_width_mm() must contain exactly one argument")
    return function_name, tuple(args)


def _split_function_args(raw_text: str, context: str) -> tuple[str, ...]:
    if raw_text == "":
        return tuple()
    args: list[str] = []
    token: list[str] = []
    depth = 0
    for index, ch in enumerate(raw_text):
        if ch == "(":
            depth += 1
            token.append(ch)
            continue
        if ch == ")":
            depth -= 1
            if depth < 0:
                raise ValueError(f"{context} has unmatched ')' at index {index}")
            token.append(ch)
            continue
        if ch == "," and depth == 0:
            raw_arg = "".join(token).strip()
            if raw_arg == "":
                raise ValueError(f"{context} contains empty argument")
            args.append(raw_arg)
            token = []
            continue
        token.append(ch)
    if depth != 0:
        raise ValueError(f"{context} has unmatched '('")
    if token:
        raw_arg = "".join(token).strip()
        if raw_arg == "":
            raise ValueError(f"{context} contains empty argument")
        args.append(raw_arg)
    return tuple(args)


def _parse_constraint_operand(
    raw_operand: object,
    path: str,
) -> _ConstraintPathRef | _ConstraintFuncRef | _ConstraintValueRef:
    if isinstance(raw_operand, dict):
        if set(raw_operand.keys()) == {"path"}:
            raw_path = raw_operand["path"]
            if not isinstance(raw_path, str) or raw_path == "":
                raise ValueError(f"{path} path must be a non-empty string")
            return {"path": raw_path}
        if set(raw_operand.keys()) == {"func"}:
            raw_func = raw_operand["func"]
            if not isinstance(raw_func, str) or raw_func == "":
                raise ValueError(f"{path}.func must be a non-empty string")
            return {"func": raw_func.strip()}
        if set(raw_operand.keys()) == {"value"}:
            raw_value = raw_operand["value"]
            if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                raise ValueError(f"{path}.value must be a number")
            return {"value": raw_value}
    raise ValueError(f"{path} must be one of {{path|value|func}}")


def _parse_constraints(source_spec: TOMLTable, source: Type2StepSpec) -> list[_Type2ConstraintRule]:
    if "constraints" not in source_spec:
        return []
    raw_constraints = source_spec["constraints"]
    if not isinstance(raw_constraints, dict):
        raise ValueError("[constraints] must be a table/object")
    raw_rules = cast(object, raw_constraints)
    if "rules" not in cast(TOMLTable, raw_rules):
        raise ValueError("[constraints] must contain rules")
    constraints_table = _parse_constraint_table(raw_rules, "constraints")
    raw_rule_list = constraints_table["rules"]
    if not isinstance(raw_rule_list, list):
        raise ValueError("constraints.rules must be a list of tables")
    if len(raw_rule_list) == 0:
        raise ValueError("constraints.rules must be a non-empty list")
    parsed_rules: list[_Type2ConstraintRule] = []
    rule_ids: set[str] = set()
    for index, raw_rule in enumerate(raw_rule_list):
        rule_path = _constraint_id_for_rule(index)
        if not isinstance(raw_rule, dict):
            raise ValueError(f"{rule_path} must be a table/object")
        raw_rule_dict = cast(TOMLTable, raw_rule)
        if set(raw_rule_dict.keys()) != {"id", "kind", "message", "enabled", "lhs", "op", "rhs"} and not {
            "id",
            "kind",
            "message",
            "lhs",
            "op",
            "rhs",
        }.issubset(set(raw_rule_dict.keys())):
            raise ValueError(f"{rule_path} must contain keys id, kind, message, lhs, op, rhs and optional enabled")
        raw_id = raw_rule_dict["id"]
        if not isinstance(raw_id, str) or raw_id == "":
            raise ValueError(f"{rule_path}.id must be a non-empty string")
        if raw_id in rule_ids:
            raise ValueError(f"{rule_path} duplicate rule id: {raw_id}")
        rule_ids.add(raw_id)
        raw_kind = raw_rule_dict["kind"]
        if raw_kind != "comparison":
            raise ValueError(f"{rule_path}.kind must be 'comparison' for type2 constraints")
        raw_message = raw_rule_dict["message"]
        if not isinstance(raw_message, str) or raw_message == "":
            raise ValueError(f"{rule_path}.message must be a non-empty string")
        raw_enabled = raw_rule_dict["enabled"] if "enabled" in raw_rule_dict else True
        if raw_enabled is not True and raw_enabled is not False:
            raise ValueError(f"{rule_path}.enabled must be bool")
        raw_lhs = _parse_constraint_operand(raw_rule_dict["lhs"], f"{rule_path}.lhs")
        raw_rhs = _parse_constraint_operand(raw_rule_dict["rhs"], f"{rule_path}.rhs")
        raw_op = raw_rule_dict["op"]
        if raw_op not in _CONSTRAINT_COMPARISON_OPERATORS:
            raise ValueError(
                f"{rule_path}.op must be one of {sorted(_CONSTRAINT_COMPARISON_OPERATORS)} "
                f"(actual={raw_op!r})"
            )
        parsed_rules.append(
            {
                "id": raw_id,
                "kind": "comparison",
                "message": raw_message,
                "enabled": bool(raw_enabled),
                "lhs": raw_lhs,
                "op": raw_op,
                "rhs": raw_rhs,
            }
        )
    _validate_constraint_paths(sampled_source=source, constraints=parsed_rules)
    return parsed_rules


def _validate_constraint_path(sampled_source: Type2StepSpec, path: str, *, context: str) -> None:
    try:
        _ = _range_spec_for_owner_path(sampled_source, path)
    except ValueError as exc:
        raise ValueError(f"{context} references unknown owner path: {path}") from exc


def _validate_constraint_paths(sampled_source: Type2StepSpec, *, constraints: list[_Type2ConstraintRule]) -> None:
    for rule in constraints:
        if not rule["enabled"]:
            continue
        for side_key in ("lhs", "rhs"):
            raw_side = rule[side_key]
            if "path" in raw_side:
                _validate_constraint_path(sampled_source, raw_side["path"], context=f"constraints.rules[{rule['id']}]")
            if "func" in raw_side:
                func_name, args = _parse_constraint_func(raw_side["func"], f"constraints.rules[{rule['id']}]")
                if func_name == "sum":
                    for arg in args:
                        _validate_constraint_sum_arg(sampled_source, arg, context=f"constraints.rules[{rule['id']}]")
                    continue
                if func_name == "tx_inner_min_trace_width_mm":
                    _validate_single_coil_min_trace_width_arg(
                        sampled_source,
                        args[0],
                        expected_type=ModeledTxInnerSingleCoilSpec,
                        function_name=func_name,
                        expected_role="tx_inner_single_coil",
                        context=f"constraints.rules[{rule['id']}]",
                    )
                    continue
                if func_name == "rx_min_trace_width_mm":
                    _validate_single_coil_min_trace_width_arg(
                        sampled_source,
                        args[0],
                        expected_type=ModeledRxSingleCoilSpec,
                        function_name=func_name,
                        expected_role="rx_single_coil",
                        context=f"constraints.rules[{rule['id']}]",
                    )
                    continue
                raise ValueError(f"constraints.rules[{rule['id']}].func unsupported function: {func_name}")


def _validate_constraint_sum_arg(sampled_source: Type2StepSpec, arg: str, *, context: str) -> None:
    if arg == "":
        raise ValueError(f"{context}.func contains empty argument")
    try:
        float(arg)
    except ValueError:
        _validate_constraint_path(sampled_source, arg, context=f"{context}.func")


def _validate_single_coil_min_trace_width_arg(
    sampled_source: Type2StepSpec,
    object_id: str,
    *,
    expected_type: type[ModeledTxInnerSingleCoilSpec] | type[ModeledRxSingleCoilSpec],
    function_name: str,
    expected_role: str,
    context: str,
) -> None:
    if object_id == "":
        raise ValueError(f"{context}.func {function_name}() object id must be non-empty")
    matches = [modeled_spec for modeled_spec in sampled_source.modeled_objects if modeled_spec.object_id == object_id]
    if len(matches) != 1:
        raise ValueError(f"{context}.func references unknown modeled object: {object_id}")
    if not isinstance(matches[0], expected_type):
        raise ValueError(
            f"{context}.func {function_name}() requires {expected_role} object "
            f"(actual={object_id})"
        )


def _resolve_constraint_path_value(
    source: Type2StepSpec,
    sampled_values: dict[str, SampledScalar],
    path: str,
    *,
    context: str,
) -> SampledScalar:
    if path in sampled_values:
        return sampled_values[path]
    range_spec = _range_spec_for_owner_path(source, path)
    if range_spec.count != 1:
        raise ValueError(f"{context} references unsampled owner path: {path}")
    if range_spec.is_integer:
        value = int(range_spec.start)
    else:
        value = float(range_spec.start)
    return value


def _resolve_constraint_operand(
    source: Type2StepSpec,
    sampled_values: dict[str, SampledScalar],
    operand: _ConstraintPathRef | _ConstraintFuncRef | _ConstraintValueRef,
    *,
    context: str,
) -> int | float | str:
    if "path" in operand:
        return _resolve_constraint_path_value(
            source,
            sampled_values,
            operand["path"],
            context=context,
        )
    if "value" in operand:
        return operand["value"]
    function = _parse_constraint_func(cast(str, operand["func"]), context=f"{context}.func")
    function_name, args = function
    if function_name == "tx_inner_min_trace_width_mm":
        return _resolve_tx_inner_min_trace_width_mm(
            source,
            sampled_values,
            object_id=args[0],
            context=context,
        )
    if function_name == "rx_min_trace_width_mm":
        return _resolve_rx_min_trace_width_mm(
            source,
            sampled_values,
            object_id=args[0],
            context=context,
        )
    if function_name != "sum":
        raise ValueError(f"{context}.func unsupported function: {function_name}")
    total = 0.0
    for arg in args:
        if " " in arg:
            arg = arg.strip()
        try:
            total += float(arg)
            continue
        except ValueError:
            pass
        total += float(_resolve_constraint_path_value(source, sampled_values, arg, context=context))
    return total


def _resolve_tx_inner_min_trace_width_mm(
    source: Type2StepSpec,
    sampled_values: dict[str, SampledScalar],
    *,
    object_id: str,
    context: str,
) -> float:
    tx_region_matches = [
        non_model_spec
        for non_model_spec in source.non_model_objects
        if isinstance(non_model_spec, NonModelTxRegionSpec) and non_model_spec.object_id == "tx_region"
    ]
    if len(tx_region_matches) != 1:
        raise ValueError(f"{context}.func requires exactly one tx_region source object")
    tx_region_spec = tx_region_matches[0]
    tx_size_x, tx_size_y, _tx_size_z = tx_region_spec.size_xyz
    x_ratio = _resolve_float_constraint_path_value(
        source,
        sampled_values,
        "non_model_objects.tx_region.tx_reference_line.x_ratio",
        context=context,
    )
    y_usage_ratio = _resolve_float_constraint_path_value(
        source,
        sampled_values,
        "non_model_objects.tx_region.tx_reference_line.y_usage_ratio",
        context=context,
    )
    z_ratio = _resolve_float_constraint_path_value(
        source,
        sampled_values,
        "non_model_objects.tx_region.tx_reference_line.z_ratio",
        context=context,
    )
    inner_region_x_mm = tx_size_x * x_ratio
    inner_region_y_mm = tx_size_y * y_usage_ratio
    inner_region_z_mm = _tx_size_z * z_ratio
    if inner_region_z_mm <= 0.0:
        raise ValueError(f"{context}.func resolved tx_inner_region z size must be > 0 (actual={inner_region_z_mm})")

    modeled_spec = _require_tx_inner_single_coil_spec(source, object_id=object_id, context=context)
    owner_prefix = f"modeled_objects.{modeled_spec.object_id}"
    outer_x_usage_ratio = _resolve_float_constraint_path_value(
        source,
        sampled_values,
        f"{owner_prefix}.outer_x_usage_ratio",
        context=context,
    )
    outer_y_usage_ratio = _resolve_float_constraint_path_value(
        source,
        sampled_values,
        f"{owner_prefix}.outer_y_usage_ratio",
        context=context,
    )
    turn_count = _resolve_int_constraint_path_value(
        source,
        sampled_values,
        f"{owner_prefix}.turn_count",
        context=context,
    )
    void_usage_ratio = _resolve_float_constraint_path_value(
        source,
        sampled_values,
        f"{owner_prefix}.void_usage_ratio",
        context=context,
    )
    margin_ratio = _resolve_float_constraint_path_value(
        source,
        sampled_values,
        f"{owner_prefix}.margin_ratio",
        context=context,
    )
    metal_fill_factor = _resolve_float_constraint_path_value(
        source,
        sampled_values,
        f"{owner_prefix}.metal_fill_factor",
        context=context,
    )
    return min_centered_rect_void_trace_width_mm(
        outer_x_mm=inner_region_x_mm * outer_x_usage_ratio,
        outer_y_mm=inner_region_y_mm * outer_y_usage_ratio,
        turn_count=turn_count,
        void_usage_ratio=void_usage_ratio,
        margin_ratio=margin_ratio,
        metal_fill_factor=metal_fill_factor,
    )


def _resolve_rx_min_trace_width_mm(
    source: Type2StepSpec,
    sampled_values: dict[str, SampledScalar],
    *,
    object_id: str,
    context: str,
) -> float:
    rx_region_matches = [
        non_model_spec for non_model_spec in source.non_model_objects if non_model_spec.object_id == "rx_region_max"
    ]
    if len(rx_region_matches) != 1:
        raise ValueError(f"{context}.func requires exactly one rx_region_max source object")
    rx_region_spec = rx_region_matches[0]
    if rx_region_spec.plane != "YZ":
        raise ValueError(f"{context}.func rx_region_max plane must be YZ (actual={rx_region_spec.plane})")
    _owner_size_x, owner_size_y, owner_size_z = rx_region_spec.size_xyz
    modeled_spec = _require_rx_single_coil_spec(source, object_id=object_id, context=context)
    owner_prefix = f"modeled_objects.{modeled_spec.object_id}"
    outer_x_usage_ratio = _resolve_float_constraint_path_value(
        source,
        sampled_values,
        f"{owner_prefix}.outer_x_usage_ratio",
        context=context,
    )
    outer_y_usage_ratio = _resolve_float_constraint_path_value(
        source,
        sampled_values,
        f"{owner_prefix}.outer_y_usage_ratio",
        context=context,
    )
    turn_count = _resolve_int_constraint_path_value(
        source,
        sampled_values,
        f"{owner_prefix}.turn_count",
        context=context,
    )
    void_usage_ratio = _resolve_float_constraint_path_value(
        source,
        sampled_values,
        f"{owner_prefix}.void_usage_ratio",
        context=context,
    )
    margin_ratio = _resolve_float_constraint_path_value(
        source,
        sampled_values,
        f"{owner_prefix}.margin_ratio",
        context=context,
    )
    metal_fill_factor = _resolve_float_constraint_path_value(
        source,
        sampled_values,
        f"{owner_prefix}.metal_fill_factor",
        context=context,
    )
    return min_centered_rect_void_trace_width_mm(
        outer_x_mm=owner_size_y * outer_x_usage_ratio,
        outer_y_mm=owner_size_z * outer_y_usage_ratio,
        turn_count=turn_count,
        void_usage_ratio=void_usage_ratio,
        margin_ratio=margin_ratio,
        metal_fill_factor=metal_fill_factor,
    )


def _require_tx_inner_single_coil_spec(
    source: Type2StepSpec,
    *,
    object_id: str,
    context: str,
) -> ModeledTxInnerSingleCoilSpec:
    matches = [modeled_spec for modeled_spec in source.modeled_objects if modeled_spec.object_id == object_id]
    if len(matches) != 1:
        raise ValueError(f"{context}.func references unknown modeled object: {object_id}")
    modeled_spec = matches[0]
    if not isinstance(modeled_spec, ModeledTxInnerSingleCoilSpec):
        raise ValueError(f"{context}.func requires tx_inner_single_coil object (actual={object_id})")
    return modeled_spec


def _require_rx_single_coil_spec(
    source: Type2StepSpec,
    *,
    object_id: str,
    context: str,
) -> ModeledRxSingleCoilSpec:
    matches = [modeled_spec for modeled_spec in source.modeled_objects if modeled_spec.object_id == object_id]
    if len(matches) != 1:
        raise ValueError(f"{context}.func references unknown modeled object: {object_id}")
    modeled_spec = matches[0]
    if not isinstance(modeled_spec, ModeledRxSingleCoilSpec):
        raise ValueError(f"{context}.func requires rx_single_coil object (actual={modeled_spec.object_id})")
    return modeled_spec


def _resolve_float_constraint_path_value(
    source: Type2StepSpec,
    sampled_values: dict[str, SampledScalar],
    path: str,
    *,
    context: str,
) -> float:
    value = _resolve_constraint_path_value(source, sampled_values, path, context=context)
    if isinstance(value, bool):
        raise ValueError(f"{context} expected float-compatible owner value for {path} (actual={value!r})")
    return float(value)


def _resolve_int_constraint_path_value(
    source: Type2StepSpec,
    sampled_values: dict[str, SampledScalar],
    path: str,
    *,
    context: str,
) -> int:
    value = _resolve_constraint_path_value(source, sampled_values, path, context=context)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{context} expected integer owner value for {path} (actual={value!r})")
    return value


def _evaluate_comparison(lhs: int | float | str, op: str, rhs: int | float | str) -> bool:
    if op in {"<", "<=", ">", ">=", "!="}:
        if isinstance(lhs, str) or isinstance(rhs, str):
            raise ValueError(f"comparison operator {op} is not supported for string operands")
    if op == "<":
        return lhs < rhs  # type: ignore[operator]
    if op == "<=":
        return lhs <= rhs  # type: ignore[operator]
    if op == ">":
        return lhs > rhs  # type: ignore[operator]
    if op == ">=":
        return lhs >= rhs  # type: ignore[operator]
    if op == "==":
        return lhs == rhs
    if op == "!=":
        return lhs != rhs
    raise ValueError(f"Unsupported comparison operator: {op}")


def _require_constraints_satisfied(
    source: Type2StepSpec,
    sampled_values: dict[str, SampledScalar],
    constraints: list[_Type2ConstraintRule],
) -> None:
    for rule in constraints:
        if not rule["enabled"]:
            continue
        lhs_value = _resolve_constraint_operand(
            source,
            sampled_values,
            cast(_ConstraintPathRef | _ConstraintFuncRef | _ConstraintValueRef, rule["lhs"]),
            context=f"constraints.rules[{rule['id']}]",
        )
        rhs_value = _resolve_constraint_operand(
            source,
            sampled_values,
            cast(_ConstraintPathRef | _ConstraintFuncRef | _ConstraintValueRef, rule["rhs"]),
            context=f"constraints.rules[{rule['id']}]",
        )
        if not _evaluate_comparison(lhs_value, rule["op"], rhs_value):
            raise ValueError(
                f"constraint '{rule['id']}' failed: {rule['message']} "
                f"(lhs={lhs_value!r} rhs={rhs_value!r} op={rule['op']})"
            )


def _derived_non_model_range_owner_specs(
    non_model_spec: NonModelDerivedSpec,
) -> tuple[tuple[str, RangeSpec], ...]:
    if isinstance(non_model_spec, NonModelTxRegionActualSpec):
        return _tx_region_actual_range_owner_specs(non_model_spec)
    if isinstance(non_model_spec, NonModelTxRegionActualStackSpaceSpec):
        return _tx_region_actual_stack_space_range_owner_specs(non_model_spec)
    raise RuntimeError(f"unsupported non-model derived spec: {type(non_model_spec).__name__}")


def _tx_region_reference_line_range_owner_specs(
    non_model_spec: NonModelTxRegionSpec,
) -> tuple[tuple[str, RangeSpec], ...]:
    return (
        (
            f"non_model_objects.{non_model_spec.object_id}.z_gap_from_rx_plane_mm",
            non_model_spec.z_gap_from_rx_plane_mm,
        ),
        (
            f"non_model_objects.{non_model_spec.object_id}.tx_reference_line.x_ratio",
            non_model_spec.tx_reference_line.x_ratio,
        ),
        (
            f"non_model_objects.{non_model_spec.object_id}.tx_reference_line.y_usage_ratio",
            non_model_spec.tx_reference_line.y_usage_ratio,
        ),
        (
            f"non_model_objects.{non_model_spec.object_id}.tx_reference_line.z_ratio",
            non_model_spec.tx_reference_line.z_ratio,
        ),
    )


def _tx_region_actual_range_owner_specs(
    non_model_spec: NonModelTxRegionActualSpec,
) -> tuple[tuple[str, RangeSpec], ...]:
    return (
        (f"non_model_objects.{non_model_spec.object_id}.x_usage_ratio", non_model_spec.x_usage_ratio),
        (f"non_model_objects.{non_model_spec.object_id}.y_usage_ratio", non_model_spec.y_usage_ratio),
        (
            f"non_model_objects.{non_model_spec.object_id}.x_division_count",
            non_model_spec.x_division_count,
        ),
        (
            f"non_model_objects.{non_model_spec.object_id}.y_division_count",
            non_model_spec.y_division_count,
        ),
    )


def _tx_region_actual_stack_space_range_owner_specs(
    non_model_spec: NonModelTxRegionActualStackSpaceSpec,
) -> tuple[tuple[str, RangeSpec], ...]:
    return (
        (f"non_model_objects.{non_model_spec.object_id}.scale_ratio", non_model_spec.scale_ratio),
    )


def _modeled_range_owner_specs(spec: Type2StepSpec) -> tuple[tuple[str, RangeSpec], ...]:
    owner_specs: list[tuple[str, RangeSpec]] = []
    for modeled_spec in spec.modeled_objects:
        role = _modeled_spec_role(modeled_spec)
        if role in _UNSUPPORTED_RXONLY_TX_MODELED_ROLES:
            raise ValueError(f"RxOnly type2 sampling does not support active TX modeled sampled owner role: {role}")
        if role in _SAMPLED_SINGLE_COIL_ROLES:
            owner_specs.extend(
                _single_coil_range_owner_specs(
                    cast(ModeledTxSingleCoilSpec | ModeledTxInnerSingleCoilSpec | ModeledRxSingleCoilSpec, modeled_spec)
                )
            )
            continue
        if role == "tv_aluminum_plate":
            owner_specs.extend(_tv_aluminum_plate_range_owner_specs(modeled_spec))
            continue
        if role.endswith(_PLATE_STACK_ROLE_SUFFIX):
            owner_specs.extend(_plate_stack_range_owner_specs(cast(ModeledPlateStackSpec, modeled_spec)))
            continue
        raise RuntimeError(f"unsupported modeled object role for sampled owner resolution: {role}")
    return tuple(owner_specs)


def _all_range_owner_specs(spec: Type2StepSpec) -> tuple[tuple[str, RangeSpec], ...]:
    return _non_model_range_owner_specs(spec) + _modeled_range_owner_specs(spec)


def _single_coil_range_owner_specs(
    modeled_spec: ModeledTxSingleCoilSpec | ModeledTxInnerSingleCoilSpec | ModeledRxSingleCoilSpec,
) -> tuple[tuple[str, RangeSpec], ...]:
    owner_specs: list[tuple[str, RangeSpec]] = [
        (f"modeled_objects.{modeled_spec.object_id}.outer_x_usage_ratio", modeled_spec.outer_x_usage_ratio),
        (f"modeled_objects.{modeled_spec.object_id}.outer_y_usage_ratio", modeled_spec.outer_y_usage_ratio),
    ]
    if not isinstance(modeled_spec, ModeledTxInnerSingleCoilSpec):
        owner_specs.append(
            (f"modeled_objects.{modeled_spec.object_id}.x_position_ratio", modeled_spec.x_position_ratio)
        )
    owner_specs.extend(
        (
            (f"modeled_objects.{modeled_spec.object_id}.void_usage_ratio", modeled_spec.void_usage_ratio),
            (f"modeled_objects.{modeled_spec.object_id}.turn_count", modeled_spec.turn_count),
            (f"modeled_objects.{modeled_spec.object_id}.layer_count", modeled_spec.layer_count),
            (
                f"modeled_objects.{modeled_spec.object_id}.underlay_repeat_count",
                modeled_spec.underlay_repeat_count,
            ),
            (f"modeled_objects.{modeled_spec.object_id}.layer_gap_mm", modeled_spec.layer_gap_mm),
            (
                f"modeled_objects.{modeled_spec.object_id}.terminal_stub_length_mm",
                modeled_spec.terminal_stub_length_mm,
            ),
            (f"modeled_objects.{modeled_spec.object_id}.margin_ratio", modeled_spec.margin_ratio),
            (f"modeled_objects.{modeled_spec.object_id}.metal_fill_factor", modeled_spec.metal_fill_factor),
        )
    )
    if isinstance(modeled_spec, ModeledTxSingleCoilSpec):
        owner_specs.extend(
            (
                (f"modeled_objects.{modeled_spec.object_id}.underlay_gap_mm", modeled_spec.underlay_gap_mm),
                (
                    f"modeled_objects.{modeled_spec.object_id}.wall_parallel_stack_present",
                    modeled_spec.wall_parallel_stack_present,
                ),
            )
        )
    if isinstance(modeled_spec, ModeledTxInnerSingleCoilSpec):
        owner_specs.extend(
            (
                (
                    f"modeled_objects.{modeled_spec.object_id}.void_stack_present",
                    modeled_spec.void_stack_present,
                ),
                (
                    f"modeled_objects.{modeled_spec.object_id}.underlay_pet_psa_thickness_mm",
                    modeled_spec.underlay_pet_psa_thickness_mm,
                ),
                (
                    f"modeled_objects.{modeled_spec.object_id}.underlay_ferrite_thickness_mm",
                    modeled_spec.underlay_ferrite_thickness_mm,
                ),
            )
        )
    return tuple(owner_specs)


def _plate_stack_range_owner_specs(
    modeled_spec: ModeledPlateStackSpec,
) -> tuple[tuple[str, RangeSpec], ...]:
    owner_specs: list[tuple[str, RangeSpec]] = [
        (f"modeled_objects.{modeled_spec.object_id}.turn_count", modeled_spec.turn_count),
        (f"modeled_objects.{modeled_spec.object_id}.metal_fill_factor", modeled_spec.metal_fill_factor),
        (f"modeled_objects.{modeled_spec.object_id}.z_usage_ratio", modeled_spec.z_usage_ratio),
        (f"modeled_objects.{modeled_spec.object_id}.y_usage_ratio", modeled_spec.y_usage_ratio),
    ]
    if isinstance(modeled_spec, ModeledTxPlateStackSpec):
        owner_specs.extend(
            (
                (f"modeled_objects.{modeled_spec.object_id}.tx_coil_count", modeled_spec.tx_coil_count),
                (
                    f"modeled_objects.{modeled_spec.object_id}.tx_array_x_usage_ratio",
                    modeled_spec.tx_array_x_usage_ratio,
                ),
            )
    )
    return tuple(owner_specs)


def _tv_aluminum_plate_range_owner_specs(modeled_spec: object) -> tuple[tuple[str, RangeSpec], ...]:
    assert hasattr(modeled_spec, "object_id"), "tv_aluminum_plate modeled spec must expose object_id"
    raw_object_id = getattr(modeled_spec, "object_id")
    assert isinstance(raw_object_id, str), "tv_aluminum_plate object_id must be str"
    assert raw_object_id != "", "tv_aluminum_plate object_id must be non-empty"
    assert hasattr(modeled_spec, "sheet_present"), "tv_aluminum_plate modeled spec must expose sheet_present"
    raw_sheet_present = getattr(modeled_spec, "sheet_present")
    assert isinstance(raw_sheet_present, RangeSpec), "tv_aluminum_plate sheet_present must be RangeSpec"
    return ((f"modeled_objects.{raw_object_id}.sheet_present", raw_sheet_present),)


def _tx_rect_void_columns_range_owner_specs(modeled_spec: object) -> tuple[tuple[str, RangeSpec], ...]:
    assert hasattr(modeled_spec, "object_id"), "tx_rect_void_columns modeled spec must expose object_id"
    raw_object_id = cast(object, getattr(modeled_spec, "object_id"))
    assert isinstance(raw_object_id, str), "tx_rect_void_columns object_id must be str"
    object_id = raw_object_id
    assert object_id != "", "tx_rect_void_columns object_id must be non-empty"
    owner_root = f"modeled_objects.{object_id}"
    return (
        (f"{owner_root}.connection_mode", _tx_rect_void_columns_range_spec(modeled_spec, "connection_mode")),
        (f"{owner_root}.turn_weight_a", _tx_rect_void_columns_range_spec(modeled_spec, "turn_weight_a")),
        (f"{owner_root}.turn_weight_b", _tx_rect_void_columns_range_spec(modeled_spec, "turn_weight_b")),
        (f"{owner_root}.turn_weight_c", _tx_rect_void_columns_range_spec(modeled_spec, "turn_weight_c")),
        (
            f"{owner_root}.equivalent_turn_count",
            _tx_rect_void_columns_range_spec(modeled_spec, "equivalent_turn_count"),
        ),
    )


def _tx_rect_void_columns_range_spec(modeled_spec: object, field_name: str) -> RangeSpec:
    if not hasattr(modeled_spec, field_name):
        raise RuntimeError(f"tx_rect_void_columns sampled owner missing field: {field_name}")
    raw_range_spec = cast(object, getattr(modeled_spec, field_name))
    assert isinstance(raw_range_spec, RangeSpec), f"tx_rect_void_columns field {field_name} must be a RangeSpec"
    return raw_range_spec


def _tx_rect_void_columns_sampled_connection_mode(
    mode_spec: object,
    *,
    owner_path: str,
    seed: int,
    retry_number: int,
) -> int:
    mode_spec_value = _tx_rect_void_columns_range_spec(mode_spec, "connection_mode")
    if mode_spec_value.count == 1:
        raw_connection_mode = int(round(mode_spec_value.start))
    else:
        raw_connection_mode = _selected_value_for_owner_path(
            mode_spec_value,
            owner_path=owner_path,
            seed=seed,
            retry_number=retry_number,
        )
    if isinstance(raw_connection_mode, bool) or not isinstance(raw_connection_mode, int):
        raise ValueError(f"{owner_path} must resolve to integer connection mode 0 or 1")
    if raw_connection_mode not in {0, 1}:
        raise ValueError(f"{owner_path} must resolve to integer connection mode 0 or 1, actual={raw_connection_mode}")
    return raw_connection_mode


def _tx_rect_void_columns_sampled_owner_values(
    mode_spec: object,
    *,
    owner_prefix: str,
    realized_coil_count: int,
    seed: int,
    retry_number: int,
) -> tuple[tuple[str, SampledScalar], ...]:
    if realized_coil_count < 1:
        raise ValueError(f"tx_rect_void_columns realized_coil_count must be >= 1 (actual={realized_coil_count})")
    sampled_owner_values: list[tuple[str, SampledScalar]] = []
    connection_mode_path = f"{owner_prefix}.connection_mode"
    connection_mode = _tx_rect_void_columns_sampled_connection_mode(
        mode_spec,
        owner_path=connection_mode_path,
        seed=seed,
        retry_number=retry_number,
    )
    connection_mode_range = _tx_rect_void_columns_range_spec(mode_spec, "connection_mode")
    if connection_mode_range.count != 1:
        sampled_owner_values.append(
            (
                connection_mode_path,
                _selected_value_for_owner_path(
                    connection_mode_range,
                    owner_path=connection_mode_path,
                    seed=seed,
                    retry_number=retry_number,
                ),
            )
        )
    for suffix in ("turn_weight_a", "turn_weight_b", "turn_weight_c"):
        owner_path = f"{owner_prefix}.{suffix}"
        range_spec = _tx_rect_void_columns_range_spec(mode_spec, suffix)
        if range_spec.count == 1:
            continue
        sampled_owner_values.append(
            (
                owner_path,
                _selected_value_for_owner_path(
                    range_spec,
                    owner_path=owner_path,
                    seed=seed,
                    retry_number=retry_number,
                ),
            )
        )
    equivalent_owner_path = f"{owner_prefix}.equivalent_turn_count"
    equivalent_range = _tx_rect_void_columns_range_spec(mode_spec, "equivalent_turn_count")
    feasible_candidates = _tx_rect_void_columns_equivalent_turn_count_candidates(
        equivalent_range,
        owner_path=equivalent_owner_path,
        connection_mode=connection_mode,
        realized_coil_count=realized_coil_count,
    )
    if len(feasible_candidates) == 1:
        sampled_owner_values.append((equivalent_owner_path, feasible_candidates[0]))
    else:
        sampled_owner_values.append(
            (
                equivalent_owner_path,
                _selected_value_from_candidates(
                    feasible_candidates,
                    owner_path=equivalent_owner_path,
                    seed=seed,
                    retry_number=retry_number,
                ),
            )
        )

    return tuple(sampled_owner_values)


def _selected_value_from_candidates(
    candidates: tuple[SampledScalar, ...],
    *,
    owner_path: str,
    seed: int,
    retry_number: int,
) -> SampledScalar:
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated for sampled owner: {owner_path}")
    if len(candidates) == 1:
        return candidates[0]
    if retry_number < 0:
        raise ValueError("retry_number must be >= 0")
    hash_key = f"{seed}:{owner_path}" if retry_number == 0 else f"{seed}:{owner_path}:{retry_number}"
    digest = hashlib.blake2b(hash_key.encode("utf-8"), digest_size=8).digest()
    index = int.from_bytes(digest, byteorder="big", signed=False) % len(candidates)
    return candidates[index]


def _tx_rect_void_columns_equivalent_turn_count_candidates(
    range_spec: RangeSpec,
    *,
    owner_path: str,
    connection_mode: int,
    realized_coil_count: int,
) -> tuple[SampledScalar, ...]:
    raw_candidates = _float_range_candidates(range_spec)
    if connection_mode == 1:
        feasible_candidates = tuple(
            candidate
            for candidate in raw_candidates
            if realized_coil_count <= round(candidate) <= 31
        )
    elif connection_mode == 0:
        lower_bound = 1.0 / float(realized_coil_count)
        upper_bound = 10.0 / float(realized_coil_count)
        feasible_candidates = tuple(
            candidate
            for candidate in raw_candidates
            if _value_within_inclusive_bounds(candidate, lower_bound, upper_bound)
        )
    else:
        raise ValueError(f"{owner_path} must resolve to connection mode 0 or 1 (actual={connection_mode})")
    if len(feasible_candidates) == 0:
        raise ValueError(
            f"no feasible equivalent_turn_count candidates for {owner_path} "
            f"(connection_mode={connection_mode}, realized_coil_count={realized_coil_count})"
    )
    return feasible_candidates


def _value_within_inclusive_bounds(value: float, lower_bound: float, upper_bound: float) -> bool:
    return (
        value > lower_bound
        or math.isclose(value, lower_bound, rel_tol=0.0, abs_tol=1e-12)
    ) and (
        value < upper_bound
        or math.isclose(value, upper_bound, rel_tol=0.0, abs_tol=1e-12)
    )


def exportable_sampled_owner_paths(spec: Type2StepSpec) -> tuple[str, ...]:
    return exportable_sampled_owner_paths_for_seed(spec, seed=0)


def exportable_sampled_owner_paths_for_seed(spec: Type2StepSpec, *, seed: int) -> tuple[str, ...]:
    return tuple(owner_path for owner_path, _value in sampled_owner_values(spec, seed=seed))


def _range_spec_for_owner_path(spec: Type2StepSpec, owner_path: str) -> RangeSpec:
    for candidate_owner_path, range_spec in _all_range_owner_specs(spec):
        if candidate_owner_path == owner_path:
            return range_spec
    raise ValueError(f"Unknown type2 sampled owner path: {owner_path}")


def _integer_range_candidates(range_spec: RangeSpec) -> tuple[int, ...]:
    if range_spec.is_integer is not True:
        raise ValueError("integer range candidates require integer range spec")
    if range_spec.count == 1:
        raw_values = (range_spec.start,)
    else:
        step = (range_spec.end - range_spec.start) / float(range_spec.count - 1)
        raw_values = tuple(range_spec.start + (step * index) for index in range(range_spec.count))
    rounded_values = tuple(int(float(value) + 0.5) for value in raw_values)
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


def _selected_value_for_owner_path(
    range_spec: RangeSpec,
    *,
    owner_path: str,
    seed: int,
    retry_number: int = 0,
) -> SampledScalar:
    if retry_number < 0:
        raise ValueError("retry_number must be >= 0")
    candidates: tuple[SampledScalar, ...]
    if range_spec.is_integer:
        candidates = _integer_range_candidates(range_spec)
    else:
        candidates = _float_range_candidates(range_spec)
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated for sampled owner: {owner_path}")
    if len(candidates) == 1:
        return candidates[0]
    hash_key = f"{seed}:{owner_path}" if retry_number == 0 else f"{seed}:{owner_path}:{retry_number}"
    digest = hashlib.blake2b(hash_key.encode("utf-8"), digest_size=8).digest()
    index = int.from_bytes(digest, byteorder="big", signed=False) % len(candidates)
    return candidates[index]


def sampled_owner_values(
    spec: Type2StepSpec,
    *,
    seed: int,
    retry_number: int = 0,
) -> tuple[tuple[str, SampledScalar], ...]:
    sampled_values: list[tuple[str, SampledScalar]] = []
    for owner_path, range_spec in _non_model_range_owner_specs(spec):
        if range_spec.count != 1:
            sampled_values.append(
                (
                    owner_path,
                    _selected_value_for_owner_path(
                        range_spec,
                        owner_path=owner_path,
                        seed=seed,
                        retry_number=retry_number,
                    ),
                )
            )
    for modeled_spec in spec.modeled_objects:
        role = _modeled_spec_role(modeled_spec)
        if role in _UNSUPPORTED_RXONLY_TX_MODELED_ROLES:
            raise ValueError(f"RxOnly type2 sampling does not support active TX modeled sampled owner role: {role}")
        if role in _SAMPLED_SINGLE_COIL_ROLES:
            sampled_values.extend(
                _single_coil_range_owner_values(
                    cast(ModeledTxSingleCoilSpec | ModeledTxInnerSingleCoilSpec | ModeledRxSingleCoilSpec, modeled_spec),
                    seed=seed,
                    retry_number=retry_number,
                )
            )
            continue
        if role == "tv_aluminum_plate":
            sampled_values.extend(
                _tv_aluminum_plate_range_owner_values(modeled_spec, seed=seed, retry_number=retry_number)
            )
            continue
        if role.endswith(_PLATE_STACK_ROLE_SUFFIX):
            sampled_values.extend(
                _plate_stack_range_owner_values(cast(ModeledPlateStackSpec, modeled_spec), seed=seed, retry_number=retry_number)
            )
            continue
        raise RuntimeError(f"unsupported modeled object role for sampled owner resolution: {role}")
    return tuple(sampled_values)


def _tx_rect_void_columns_realized_coil_count(
    *,
    spec: Type2StepSpec,
    sampled_values: tuple[tuple[str, SampledScalar], ...],
    seed: int,
    retry_number: int,
) -> int:
    x_division_count = _integer_sampled_or_fixed_owner_value(
        spec=spec,
        sampled_values=sampled_values,
        owner_path="non_model_objects.tx_region_actual.x_division_count",
        seed=seed,
        retry_number=retry_number,
    )
    y_division_count = _integer_sampled_or_fixed_owner_value(
        spec=spec,
        sampled_values=sampled_values,
        owner_path="non_model_objects.tx_region_actual.y_division_count",
        seed=seed,
        retry_number=retry_number,
    )
    realized_coil_count = x_division_count * y_division_count
    if realized_coil_count < 1:
        raise ValueError(
            "tx_rect_void_columns realized coil count must be >= 1 "
            f"(x_division_count={x_division_count}, y_division_count={y_division_count})"
        )
    return realized_coil_count


def _integer_sampled_or_fixed_owner_value(
    *,
    spec: Type2StepSpec,
    sampled_values: tuple[tuple[str, SampledScalar], ...],
    owner_path: str,
    seed: int,
    retry_number: int,
) -> int:
    for candidate_owner_path, sampled_value in sampled_values:
        if candidate_owner_path != owner_path:
            continue
        if isinstance(sampled_value, bool) or not isinstance(sampled_value, int):
            raise ValueError(f"{owner_path} must resolve to integer value (actual={sampled_value!r})")
        return sampled_value
    range_spec = _range_spec_for_owner_path(spec, owner_path)
    selected_value = _selected_value_for_owner_path(
        range_spec,
        owner_path=owner_path,
        seed=seed,
        retry_number=retry_number,
    )
    if isinstance(selected_value, bool) or not isinstance(selected_value, int):
        raise ValueError(f"{owner_path} must resolve to integer value (actual={selected_value!r})")
    return selected_value


def _single_coil_range_owner_values(
    modeled_spec: ModeledTxSingleCoilSpec | ModeledTxInnerSingleCoilSpec | ModeledRxSingleCoilSpec,
    *,
    seed: int,
    retry_number: int,
) -> tuple[tuple[str, SampledScalar], ...]:
    sampled_values: list[tuple[str, SampledScalar]] = []
    for owner_path, range_spec in _single_coil_range_owner_specs(modeled_spec):
        if range_spec.count == 1:
            continue
        sampled_values.append(
            (
                owner_path,
                _selected_value_for_owner_path(
                    range_spec,
                    owner_path=owner_path,
                    seed=seed,
                    retry_number=retry_number,
                ),
            )
        )
    return tuple(sampled_values)


def _plate_stack_range_owner_values(
    modeled_spec: ModeledPlateStackSpec,
    *,
    seed: int,
    retry_number: int,
) -> tuple[tuple[str, SampledScalar], ...]:
    sampled_values: list[tuple[str, SampledScalar]] = []
    for owner_path, range_spec in _plate_stack_range_owner_specs(modeled_spec):
        if range_spec.count == 1:
            continue
        sampled_values.append(
            (
                owner_path,
                _selected_value_for_owner_path(
                    range_spec,
                    owner_path=owner_path,
                    seed=seed,
                    retry_number=retry_number,
                ),
            )
        )
    return tuple(sampled_values)


def _tv_aluminum_plate_range_owner_values(
    modeled_spec: object,
    *,
    seed: int,
    retry_number: int,
) -> tuple[tuple[str, SampledScalar], ...]:
    sampled_values: list[tuple[str, SampledScalar]] = []
    for owner_path, range_spec in _tv_aluminum_plate_range_owner_specs(modeled_spec):
        if range_spec.count == 1:
            continue
        sampled_values.append(
            (
                owner_path,
                _selected_value_for_owner_path(
                    range_spec,
                    owner_path=owner_path,
                    seed=seed,
                    retry_number=retry_number,
                ),
            )
        )
    return tuple(sampled_values)


__all__ = [
    "SampledScalar",
    "exportable_sampled_owner_paths",
    "exportable_sampled_owner_paths_for_seed",
    "sampled_owner_values",
    "_all_range_owner_specs",
    "_modeled_roles",
    "_parse_constraints",
    "_range_spec_for_owner_path",
    "_require_constraints_satisfied",
]

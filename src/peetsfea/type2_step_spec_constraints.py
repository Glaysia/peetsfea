from __future__ import annotations

from typing import cast

from peetsfea.type2_step_spec_types import ModeledRxPlateStackSpec
from peetsfea.type2_step_spec_types import ModeledRxSingleCoilSpec
from peetsfea.type2_step_spec_types import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec_types import ModeledTxRectVoidColumnsSpec
from peetsfea.type2_step_spec_types import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec_types import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec_types import ModeledTvAluminumPlateSpec
from peetsfea.type2_step_spec_types import NonModelTxRegionSpec
from peetsfea.type2_step_spec_types import NonModelTxRegionActualSpec
from peetsfea.type2_step_spec_types import Type2ConstraintComparableRef
from peetsfea.type2_step_spec_types import Type2ConstraintComparisonOperator
from peetsfea.type2_step_spec_types import Type2ConstraintFuncRef
from peetsfea.type2_step_spec_types import Type2ConstraintOperandRef
from peetsfea.type2_step_spec_types import Type2ConstraintPathRef
from peetsfea.type2_step_spec_types import Type2ConstraintRule
from peetsfea.type2_step_spec_types import Type2ConstraintValueRef
from peetsfea.type2_step_spec_types import Type2StepSpec


def _require_table(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be a table")
    return cast(dict[str, object], value)


def _require_key(table: dict[str, object], key: str, context: str) -> object:
    if key not in table:
        raise ValueError(f"{context} must contain key '{key}'")
    return table[key]


def _require_non_empty_str(table: dict[str, object], key: str, context: str) -> str:
    raw_value = _require_key(table, key, context)
    if not isinstance(raw_value, str) or raw_value == "":
        raise ValueError(f"{context}.{key} must be a non-empty string")
    return raw_value


def _require_constraint_path(value: object, *, dotted_path: str) -> str:
    table = _require_table(value, dotted_path)
    if set(table.keys()) != {"path"}:
        raise ValueError(f"{dotted_path} must contain only ['path']")
    raw_path = _require_non_empty_str(table, "path", dotted_path)
    return raw_path


def _require_constraint_value(value: object, *, dotted_path: str) -> str | float:
    table = _require_table(value, dotted_path)
    if set(table.keys()) != {"value"}:
        raise ValueError(f"{dotted_path} must contain only ['value']")
    raw_value = _require_key(table, "value", dotted_path)
    if isinstance(raw_value, bool):
        raise ValueError(f"{dotted_path}.value must be number|string")
    if isinstance(raw_value, int | float):
        return float(raw_value)
    if isinstance(raw_value, str):
        if raw_value == "":
            raise ValueError(f"{dotted_path}.value must be number|string")
        return raw_value
    raise ValueError(f"{dotted_path}.value must be number|string")


def _split_constraint_func_args(text: str) -> tuple[str, ...]:
    parts: list[str] = []
    token: list[str] = []
    depth = 0
    for char in text:
        if char == "(":
            depth += 1
            token.append(char)
            continue
        if char == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("constraint function expression has unmatched ')'")
            token.append(char)
            continue
        if char == "," and depth == 0:
            piece = "".join(token).strip()
            if piece == "":
                raise ValueError("constraint function argument cannot be empty")
            parts.append(piece)
            token = []
            continue
        token.append(char)
    if depth != 0:
        raise ValueError("constraint function expression has unmatched '('")
    tail = "".join(token).strip()
    if tail:
        parts.append(tail)
    return tuple(parts)


def _parse_constraint_func(value: object, *, dotted_path: str) -> str:
    table = _require_table(value, dotted_path)
    if set(table.keys()) != {"func"}:
        raise ValueError(f"{dotted_path} must contain only ['func']")
    raw_func = _require_non_empty_str(table, "func", dotted_path)
    text = raw_func.strip()
    if not text.endswith(")") or "(" not in text:
        raise ValueError(f"{dotted_path}.func must be a call expression like sum(...)")
    open_index = text.find("(")
    name = text[:open_index].strip()
    if name == "":
        raise ValueError(f"{dotted_path}.func name must be non-empty")
    if name not in ("sum", "tx_inner_min_trace_width_mm", "rx_min_trace_width_mm"):
        raise ValueError(
            f"{dotted_path}.func must be one of ['sum(...)', 'tx_inner_min_trace_width_mm(...)', 'rx_min_trace_width_mm(...)'] "
            f"(actual={name!r})"
        )
    body = text[open_index + 1 : -1].strip()
    if body == "":
        raise ValueError(f"{dotted_path}.func must include at least one argument")
    try:
        args = _split_constraint_func_args(body)
    except ValueError as exc:
        raise ValueError(f"{dotted_path}.func {exc}") from exc
    if name == "tx_inner_min_trace_width_mm" and len(args) != 1:
        raise ValueError(f"{dotted_path}.func tx_inner_min_trace_width_mm() must contain exactly one argument")
    if name == "rx_min_trace_width_mm" and len(args) != 1:
        raise ValueError(f"{dotted_path}.func rx_min_trace_width_mm() must contain exactly one argument")
    return raw_func


def _parse_constraint_comparable_ref(value: object, *, dotted_path: str) -> Type2ConstraintComparableRef:
    if not isinstance(value, dict):
        raise TypeError(f"{dotted_path} must be a table")
    if set(value.keys()) == {"path"}:
        return Type2ConstraintPathRef(path=_require_constraint_path(value, dotted_path=dotted_path))
    if set(value.keys()) == {"func"}:
        return Type2ConstraintFuncRef(func=_parse_constraint_func(value, dotted_path=dotted_path))
    raise ValueError(f"{dotted_path} must contain exactly one of ['path'], ['func']")


def _parse_constraint_rhs_ref(value: object, *, dotted_path: str) -> Type2ConstraintOperandRef:
    if not isinstance(value, dict):
        raise TypeError(f"{dotted_path} must be a table")
    if set(value.keys()) == {"path"}:
        return Type2ConstraintPathRef(path=_require_constraint_path(value, dotted_path=dotted_path))
    if set(value.keys()) == {"value"}:
        return Type2ConstraintValueRef(value=_require_constraint_value(value, dotted_path=dotted_path))
    if set(value.keys()) == {"func"}:
        return Type2ConstraintFuncRef(func=_parse_constraint_func(value, dotted_path=dotted_path))
    raise ValueError(f"{dotted_path} must contain exactly one of ['path'], ['value'], ['func']")


def _parse_constraint_rule(raw_rule: object, *, index: int, context: str) -> Type2ConstraintRule:
    dotted = f"{context}.constraints.rules[{index}]"
    table = _require_table(raw_rule, dotted)
    required_keys = {"id", "kind", "message", "lhs", "op", "rhs"}
    optional_keys = {"enabled"}
    if not required_keys.issubset(table.keys()):
        raise ValueError(f"{dotted} must contain required keys {sorted(required_keys)}")
    extra_keys = set(table.keys()) - (required_keys | optional_keys)
    if extra_keys:
        raise ValueError(f"{dotted} contains unsupported keys (actual={sorted(extra_keys)})")

    raw_id = _require_non_empty_str(table, "id", dotted)
    raw_message = _require_non_empty_str(table, "message", dotted)
    raw_kind = _require_non_empty_str(table, "kind", dotted)
    raw_enabled = table.get("enabled", True)
    if raw_kind != "comparison":
        raise ValueError(f"{dotted}.kind must be 'comparison' (actual={raw_kind!r})")
    if not isinstance(raw_enabled, bool):
        raise ValueError(f"{dotted}.enabled must be bool")
    op = _require_non_empty_str(table, "op", dotted)
    if op not in ("<", "<=", ">", ">=", "=="):
        raise ValueError(f"{dotted}.op must be one of ['<', '<=', '>', '>=', '==']")
    return Type2ConstraintRule(
        id=raw_id,
        message=raw_message,
        enabled=raw_enabled,
        lhs=_parse_constraint_comparable_ref(table["lhs"], dotted_path=f"{dotted}.lhs"),
        op=cast(Type2ConstraintComparisonOperator, op),
        rhs=_parse_constraint_rhs_ref(table["rhs"], dotted_path=f"{dotted}.rhs"),
    )


def _parse_constraints(constraints: object, *, context: str) -> tuple[Type2ConstraintRule, ...]:
    constraints_table = _require_table(constraints, context)
    raw_rules = _require_key(constraints_table, "rules", context)
    if not isinstance(raw_rules, list):
        raise TypeError(f"{context}.rules must be an array of tables")
    if len(raw_rules) == 0:
        raise ValueError(f"{context}.rules must be a non-empty array of tables")
    seen_rule_ids: set[str] = set()
    parsed_rules: list[Type2ConstraintRule] = []
    for index, raw_rule in enumerate(raw_rules):
        parsed = _parse_constraint_rule(raw_rule, index=index, context=context)
        if parsed.id in seen_rule_ids:
            raise ValueError(f"Duplicate constraints.rules id: {parsed.id}")
        seen_rule_ids.add(parsed.id)
        parsed_rules.append(parsed)
    return tuple(parsed_rules)


def _constraint_reference_paths(spec: Type2StepSpec) -> set[str]:
    paths: set[str] = set()
    for non_model_spec in spec.non_model_objects:
        if isinstance(non_model_spec, NonModelTxRegionSpec):
            base = f"non_model_objects.{non_model_spec.object_id}.tx_reference_line"
            paths.add(f"non_model_objects.{non_model_spec.object_id}.z_gap_from_rx_plane_mm")
            paths.update(
                (
                    f"{base}.x_ratio",
                    f"{base}.y_usage_ratio",
                    f"{base}.z_ratio",
                )
            )
    for non_model_spec in spec.non_model_derived_objects:
        base = f"non_model_objects.{non_model_spec.object_id}"
        if isinstance(non_model_spec, NonModelTxRegionActualSpec):
            paths.update(
                (
                    f"{base}.x_usage_ratio",
                    f"{base}.y_usage_ratio",
                    f"{base}.x_division_count",
                    f"{base}.y_division_count",
                )
            )
        else:
            paths.update((f"{base}.scale_ratio", f"{base}.tilt_enabled"))
    for modeled_spec in spec.modeled_objects:
        base = f"modeled_objects.{modeled_spec.object_id}"
        if isinstance(modeled_spec, ModeledTxSingleCoilSpec):
            paths.update(
                (
                    f"{base}.x_ratio",
                    f"{base}.y_ratio",
                    f"{base}.turn_qcount",
                    f"{base}.layer_count",
                    f"{base}.underlay_repeat_count",
                    f"{base}.layer_gap_mm",
                    f"{base}.terminal_stub_length_mm",
                    f"{base}.void_factor",
                    f"{base}.margin_ratio",
                    f"{base}.metal_fill_factor",
                    f"{base}.terminal_start",
                    f"{base}.void_stack_present",
                    f"{base}.underlay_gap_mm",
                    f"{base}.wall_parallel_stack_present",
                )
            )
            continue
        if isinstance(modeled_spec, (ModeledTxInnerSingleCoilSpec, ModeledRxSingleCoilSpec)):
            paths.update(
                (
                    f"{base}.x_ratio",
                    f"{base}.y_ratio",
                    f"{base}.turn_qcount",
                    f"{base}.layer_count",
                    f"{base}.underlay_repeat_count",
                    f"{base}.layer_gap_mm",
                    f"{base}.terminal_stub_length_mm",
                    f"{base}.void_factor",
                    f"{base}.margin_ratio",
                    f"{base}.metal_fill_factor",
                    f"{base}.terminal_start",
                    f"{base}.void_stack_present",
                )
            )
            continue
        if isinstance(modeled_spec, ModeledTxPlateStackSpec):
            paths.update(
                (
                    f"{base}.turn_count",
                    f"{base}.metal_fill_factor",
                    f"{base}.z_usage_ratio",
                    f"{base}.y_usage_ratio",
                    f"{base}.tx_coil_count",
                    f"{base}.tx_array_x_usage_ratio",
                )
            )
            continue
        if isinstance(modeled_spec, ModeledRxPlateStackSpec):
            paths.update(
                (
                    f"{base}.turn_count",
                    f"{base}.metal_fill_factor",
                    f"{base}.z_usage_ratio",
                    f"{base}.y_usage_ratio",
                )
            )
            continue
        if isinstance(modeled_spec, ModeledTxRectVoidColumnsSpec):
            paths.update(
                (
                    f"{base}.layer_count",
                    f"{base}.layer_gap_mm",
                    f"{base}.terminal_stub_length_mm",
                    f"{base}.void_usage_ratio",
                    f"{base}.margin_ratio",
                    f"{base}.metal_fill_factor",
                    f"{base}.connection_mode",
                    f"{base}.equivalent_turn_count",
                    f"{base}.turn_weight_a",
                    f"{base}.turn_weight_b",
                    f"{base}.turn_weight_c",
                )
            )
            continue
        if isinstance(modeled_spec, ModeledTvAluminumPlateSpec):
            paths.add(f"{base}.sheet_present")
            continue
        raise RuntimeError(f"unsupported modeled object for constraint owner-path collection: {modeled_spec.object_id}")
    return paths


def _validate_constraints_for_spec(constraints: tuple[Type2ConstraintRule, ...], *, spec: Type2StepSpec, context: str) -> None:
    valid_paths = _constraint_reference_paths(spec)
    for index, rule in enumerate(constraints):
        dotted = f"{context}.constraints.rules[{index}]"
        if "path" in rule.lhs:
            path = rule.lhs["path"]
            if path not in valid_paths:
                raise ValueError(f"{dotted}.lhs.path references unknown owner path: {path!r}")
        if "path" in rule.rhs:
            path = rule.rhs["path"]
            if path not in valid_paths:
                raise ValueError(f"{dotted}.rhs.path references unknown owner path: {path!r}")
        if "func" in rule.lhs:
            _validate_constraint_func_ref(rule.lhs["func"], spec=spec, dotted_path=f"{dotted}.lhs")
        if "func" in rule.rhs:
            _validate_constraint_func_ref(rule.rhs["func"], spec=spec, dotted_path=f"{dotted}.rhs")


def _validate_constraint_func_ref(func: str, *, spec: Type2StepSpec, dotted_path: str) -> None:
    text = func.strip()
    open_index = text.find("(")
    name = text[:open_index].strip()
    body = text[open_index + 1 : -1].strip()
    args = _split_constraint_func_args(body)
    if name == "sum":
        valid_paths = _constraint_reference_paths(spec)
        for arg in args:
            try:
                float(arg)
            except ValueError:
                if arg not in valid_paths:
                    raise ValueError(f"{dotted_path}.func references unknown owner path: {arg!r}") from None
        return
    if name == "tx_inner_min_trace_width_mm":
        object_id = args[0]
        matches = [modeled_spec for modeled_spec in spec.modeled_objects if modeled_spec.object_id == object_id]
        if len(matches) != 1:
            raise ValueError(f"{dotted_path}.func references unknown modeled object: {object_id!r}")
        modeled_spec = matches[0]
        if not isinstance(modeled_spec, ModeledTxInnerSingleCoilSpec):
            raise ValueError(
                f"{dotted_path}.func requires a tx_inner_single_coil modeled object "
                f"(actual={modeled_spec.object_id!r})"
            )
        return
    if name == "rx_min_trace_width_mm":
        object_id = args[0]
        matches = [modeled_spec for modeled_spec in spec.modeled_objects if modeled_spec.object_id == object_id]
        if len(matches) != 1:
            raise ValueError(f"{dotted_path}.func references unknown modeled object: {object_id!r}")
        modeled_spec = matches[0]
        if not isinstance(modeled_spec, ModeledRxSingleCoilSpec):
            raise ValueError(
                f"{dotted_path}.func requires an rx_single_coil modeled object "
                f"(actual={modeled_spec.object_id!r})"
            )
        return
    raise ValueError(f"{dotted_path}.func unsupported function: {name!r}")


__all__ = [
    "Type2ConstraintComparisonOperator",
    "Type2ConstraintComparableRef",
    "Type2ConstraintFuncRef",
    "Type2ConstraintOperandRef",
    "Type2ConstraintPathRef",
    "Type2ConstraintRule",
    "Type2ConstraintValueRef",
    "_parse_constraints",
    "_validate_constraints_for_spec",
]

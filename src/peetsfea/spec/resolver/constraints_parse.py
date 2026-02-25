from __future__ import annotations

from typing import Literal, cast

from peetsfea.spec.loader import TOMLTable, TOMLValue, require_table

from .types import ComparableRef, ConstraintRule, FuncRef, OperandRef, PathRef, ValueRef


def parse_path_ref(value: TOMLValue, dotted_path: str) -> PathRef:
    table = require_table(value, dotted_path)
    if set(table.keys()) != {"path"}:
        raise ValueError(f"{dotted_path} must contain only ['path']")
    raw_path = table.get("path")
    if not isinstance(raw_path, str) or raw_path == "":
        raise ValueError(f"{dotted_path}.path must be non-empty string")
    return {"path": raw_path}


def parse_value_ref(value: TOMLValue, dotted_path: str) -> ValueRef:
    table = require_table(value, dotted_path)
    if set(table.keys()) != {"value"}:
        raise ValueError(f"{dotted_path} must contain only ['value']")
    raw_value = table.get("value")
    if isinstance(raw_value, bool):
        raise ValueError(f"{dotted_path}.value must be number|string")
    if isinstance(raw_value, (int, float)):
        return {"value": float(raw_value)}
    if isinstance(raw_value, str) and raw_value != "":
        return {"value": raw_value}
    raise ValueError(f"{dotted_path}.value must be number|string")


def parse_comparable_ref(value: TOMLValue, dotted_path: str) -> ComparableRef:
    table = require_table(value, dotted_path)
    if set(table.keys()) != {"path"} and set(table.keys()) != {"func"}:
        raise ValueError(f"{dotted_path} must have exactly one of ['path'], ['func']")
    if "path" in table:
        return parse_path_ref(value, dotted_path)
    raw_func = table.get("func")
    if not isinstance(raw_func, str) or raw_func == "":
        raise ValueError(f"{dotted_path}.func must be non-empty string")
    return {"func": raw_func}


def parse_rhs_ref(value: TOMLValue, dotted_path: str) -> OperandRef:
    table = require_table(value, dotted_path)
    if set(table.keys()) != {"path"} and set(table.keys()) != {"value"} and set(table.keys()) != {"func"}:
        raise ValueError(f"{dotted_path} must have exactly one of ['path'], ['value'], ['func']")
    if "path" in table:
        return parse_path_ref(value, dotted_path)
    if "value" in table:
        return parse_value_ref(value, dotted_path)
    raw_func = table.get("func")
    if not isinstance(raw_func, str) or raw_func == "":
        raise ValueError(f"{dotted_path}.func must be non-empty string")
    return {"func": raw_func}


def parse_rule(raw_rule: TOMLValue, idx: int) -> ConstraintRule:
    dotted = f"constraints.rules[{idx}]"
    table = require_table(raw_rule, dotted)
    base_required = {"id", "kind", "message"}
    base_optional = {"enabled"}
    if not base_required.issubset(table.keys()):
        raise ValueError(f"{dotted} must contain required keys {sorted(base_required)}")
    if set(table.keys()) - (base_required | base_optional | {"lhs", "op", "rhs", "target", "min", "max", "inclusive_min", "inclusive_max", "agg"}):
        raise ValueError(f"{dotted} contains unsupported keys")

    raw_id = table.get("id")
    raw_kind = table.get("kind")
    raw_message = table.get("message")
    raw_enabled = table.get("enabled", True)
    if not isinstance(raw_id, str) or raw_id == "":
        raise ValueError(f"{dotted}.id must be non-empty string")
    if not isinstance(raw_message, str) or raw_message == "":
        raise ValueError(f"{dotted}.message must be non-empty string")
    if not isinstance(raw_enabled, bool):
        raise ValueError(f"{dotted}.enabled must be bool")
    enabled = raw_enabled

    if raw_kind == "comparison":
        allowed = {"id", "kind", "message", "enabled", "lhs", "op", "rhs"}
        if set(table.keys()) != allowed and set(table.keys()) != (allowed - {"enabled"}):
            raise ValueError(f"{dotted} must contain only {sorted(allowed)}")
        op = table.get("op")
        if op not in ("<", "<=", ">", ">=", "=="):
            raise ValueError(f"{dotted}.op must be one of ['<','<=','>','>=','==']")
        op_lit = cast(Literal["<", "<=", ">", ">=", "=="], op)
        lhs = parse_comparable_ref(table["lhs"], f"{dotted}.lhs")
        rhs = parse_rhs_ref(table["rhs"], f"{dotted}.rhs")
        return {"id": raw_id, "kind": "comparison", "message": raw_message, "enabled": enabled, "lhs": lhs, "op": op_lit, "rhs": rhs}

    if raw_kind == "range":
        allowed = {"id", "kind", "message", "enabled", "target", "min", "max", "inclusive_min", "inclusive_max"}
        if set(table.keys()) != allowed and set(table.keys()) != (allowed - {"enabled"}) and set(table.keys()) != (allowed - {"inclusive_min", "inclusive_max"}) and set(table.keys()) != (allowed - {"enabled", "inclusive_min", "inclusive_max"}):
            raise ValueError(f"{dotted} must contain only {sorted(allowed)}")
        target = parse_path_ref(table["target"], f"{dotted}.target")
        raw_min = table.get("min")
        raw_max = table.get("max")
        min_ref = parse_value_ref(raw_min, f"{dotted}.min") if raw_min is not None else None
        max_ref = parse_value_ref(raw_max, f"{dotted}.max") if raw_max is not None else None
        if min_ref is None and max_ref is None:
            raise ValueError(f"{dotted} must define at least one of min/max")
        inclusive_min = table.get("inclusive_min", True)
        inclusive_max = table.get("inclusive_max", True)
        if not isinstance(inclusive_min, bool) or not isinstance(inclusive_max, bool):
            raise ValueError(f"{dotted}.inclusive_min/inclusive_max must be bool")
        return {
            "id": raw_id,
            "kind": "range",
            "message": raw_message,
            "enabled": enabled,
            "target": target,
            "min": min_ref,
            "max": max_ref,
            "inclusive_min": inclusive_min,
            "inclusive_max": inclusive_max,
        }

    if raw_kind == "aggregate":
        allowed = {"id", "kind", "message", "enabled", "agg", "op", "rhs"}
        if set(table.keys()) != allowed and set(table.keys()) != (allowed - {"enabled"}):
            raise ValueError(f"{dotted} must contain only {sorted(allowed)}")
        agg = table.get("agg")
        if agg != "sum_group_selected_count":
            raise ValueError(f"{dotted}.agg must be 'sum_group_selected_count'")
        op = table.get("op")
        if op not in ("<", "<=", ">", ">=", "=="):
            raise ValueError(f"{dotted}.op must be one of ['<','<=','>','>=','==']")
        op_lit = cast(Literal["<", "<=", ">", ">=", "=="], op)
        rhs = parse_value_ref(table["rhs"], f"{dotted}.rhs")
        return {
            "id": raw_id,
            "kind": "aggregate",
            "message": raw_message,
            "enabled": enabled,
            "agg": "sum_group_selected_count",
            "op": op_lit,
            "rhs": rhs,
        }

    raise ValueError(f"{dotted}.kind must be one of ['comparison', 'range', 'aggregate']")


def parse_constraints(spec: TOMLTable) -> list[ConstraintRule]:
    constraints = require_table(spec.get("constraints"), "constraints")
    raw_rules = constraints.get("rules")
    if not isinstance(raw_rules, list):
        raise ValueError("constraints.rules must be a non-empty array of tables")
    if len(raw_rules) == 0:
        raise ValueError("constraints.rules must be a non-empty array of tables")
    parsed_rules: list[ConstraintRule] = []
    ids: set[str] = set()
    for idx, raw_rule in enumerate(raw_rules):
        parsed = parse_rule(raw_rule, idx)
        rule_id = parsed["id"]
        if rule_id in ids:
            raise ValueError(f"Duplicate constraints.rules id: {rule_id}")
        ids.add(rule_id)
        parsed_rules.append(parsed)
    return parsed_rules


def split_call_args(body: str) -> list[str]:
    parts: list[str] = []
    token: list[str] = []
    depth = 0
    for ch in body:
        if ch == "(":
            depth += 1
            token.append(ch)
            continue
        if ch == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("function expression has unmatched ')'" )
            token.append(ch)
            continue
        if ch == "," and depth == 0:
            piece = "".join(token).strip()
            if piece == "":
                raise ValueError("function argument cannot be empty")
            parts.append(piece)
            token = []
            continue
        token.append(ch)
    if depth != 0:
        raise ValueError("function expression has unmatched '('" )
    tail = "".join(token).strip()
    if tail:
        parts.append(tail)
    return parts


def parse_func_call(func_text: str) -> tuple[str, list[str]]:
    text = func_text.strip()
    if not text.endswith(")") or "(" not in text:
        raise ValueError("rhs.func must be a call expression like name(arg,...)")
    open_idx = text.find("(")
    name = text[:open_idx].strip()
    body = text[open_idx + 1 : -1].strip()
    if name == "":
        raise ValueError("rhs.func function name cannot be empty")
    return name, split_call_args(body) if body else []

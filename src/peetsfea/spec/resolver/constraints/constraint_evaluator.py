from __future__ import annotations

from typing import Literal, cast

from peetsfea.spec.loader import TOMLTable
from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance, SelectedParameters
from peetsfea.types.runtime_selection import coil_group_selected_count

from .constraint_functions import resolve_func_ref
from .constraint_paths import resolve_selected_comparable_path, resolve_selected_numeric_path
from .constraints_parse import parse_constraints
from ..types import ComparableRef, ConstraintRule, FuncRef, GroupKind, OperandRef, PathRef, SelectionConstraintError, ValueRef


def compare(lhs: float | str, rhs: float | str, op: Literal["<", "<=", ">", ">=", "=="]) -> bool:
    if op == "==":
        return lhs == rhs
    if not isinstance(lhs, (int, float)) or not isinstance(rhs, (int, float)):
        raise ValueError(f"Operator '{op}' supports only numeric operands")
    if op == "<":
        return float(lhs) < float(rhs)
    if op == "<=":
        return float(lhs) <= float(rhs)
    if op == ">":
        return float(lhs) > float(rhs)
    if op == ">=":
        return float(lhs) >= float(rhs)
    return False


def resolve_operand_ref(
    *,
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    pcbs: list[ResolvedPcbInstance],
    value_ref: OperandRef | ComparableRef,
) -> tuple[float | str, str | None]:
    if "path" in value_ref:
        path_ref = cast(PathRef, value_ref)
        return (
            resolve_selected_comparable_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, path_ref["path"]),
            None,
        )
    if "value" in value_ref:
        scalar_ref = cast(ValueRef, value_ref)
        return scalar_ref["value"], None
    func_ref = cast(FuncRef, value_ref)
    return resolve_func_ref(
        selected=selected,
        group_geometry_by_kind=group_geometry_by_kind,
        coil_groups_by_kind=coil_groups_by_kind,
        pcbs=pcbs,
        func_text=func_ref["func"],
    )


def evaluate_constraints(
    rules: list[ConstraintRule],
    selected: SelectedParameters,
    coil_groups: list[ResolvedCoilGroup],
    group_geometry: list[GroupGeometryParams],
    pcbs: list[ResolvedPcbInstance],
) -> None:
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams] = {entry["kind"]: entry for entry in group_geometry}
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup] = {entry["kind"]: entry for entry in coil_groups}
    for rule in rules:
        if not rule["enabled"]:
            continue
        if rule["kind"] == "comparison":
            lhs_value, lhs_debug = resolve_operand_ref(
                selected=selected,
                group_geometry_by_kind=group_geometry_by_kind,
                coil_groups_by_kind=coil_groups_by_kind,
                pcbs=pcbs,
                value_ref=rule["lhs"],
            )
            rhs_value, rhs_debug = resolve_operand_ref(
                selected=selected,
                group_geometry_by_kind=group_geometry_by_kind,
                coil_groups_by_kind=coil_groups_by_kind,
                pcbs=pcbs,
                value_ref=rule["rhs"],
            )
            if not compare(lhs_value, rhs_value, rule["op"]):
                extra_parts = [part for part in (lhs_debug, rhs_debug) if part is not None]
                extra_debug = f", debug=({' | '.join(extra_parts)})" if extra_parts else ""
                raise SelectionConstraintError(
                    f"Constraint {rule['id']} failed: {rule['message']} "
                    f"(lhs={lhs_value}, rhs={rhs_value}{extra_debug})"
                )
            continue
        if rule["kind"] == "range":
            target_value = resolve_selected_numeric_path(
                selected,
                group_geometry_by_kind,
                coil_groups_by_kind,
                pcbs,
                rule["target"]["path"],
            )
            if rule["min"] is not None:
                min_value = float(rule["min"]["value"])
                min_ok = target_value >= min_value if rule["inclusive_min"] else target_value > min_value
                if not min_ok:
                    raise SelectionConstraintError(
                        f"Constraint {rule['id']} failed: {rule['message']} (lhs={target_value}, rhs={min_value})"
                    )
            if rule["max"] is not None:
                max_value = float(rule["max"]["value"])
                max_ok = target_value <= max_value if rule["inclusive_max"] else target_value < max_value
                if not max_ok:
                    raise SelectionConstraintError(
                        f"Constraint {rule['id']} failed: {rule['message']} (lhs={target_value}, rhs={max_value})"
                    )
            continue
        aggregate_value = float(sum(coil_group_selected_count(group) for group in coil_groups))
        rhs_value = float(rule["rhs"]["value"])
        if not compare(aggregate_value, rhs_value, rule["op"]):
            raise SelectionConstraintError(
                f"Constraint {rule['id']} failed: {rule['message']} (lhs={aggregate_value}, rhs={rhs_value})"
            )


def validate_constraints(
    spec: TOMLTable,
    selected: SelectedParameters,
    coil_groups: list[ResolvedCoilGroup],
    group_geometry: list[GroupGeometryParams],
    pcbs: list[ResolvedPcbInstance],
) -> None:
    rules = parse_constraints(spec)
    evaluate_constraints(rules, selected, coil_groups, group_geometry, pcbs)


__all__ = ["compare", "evaluate_constraints", "resolve_operand_ref", "validate_constraints"]

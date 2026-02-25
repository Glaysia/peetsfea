from __future__ import annotations

from typing import Literal, cast

from peetsfea.spec.loader import TOMLTable
from peetsfea.types.manifest import (
    GroupGeometryParams,
    ResolvedCoilGroup,
    ResolvedPcbInstance,
    ResolvedPcbMount,
    SelectedParameters,
)

from .constants import GROUP_KIND_ORDER
from .constraints_parse import parse_constraints, parse_func_call
from .group_geometry import max_feasible_turns
from .types import ComparableRef, ConstraintRule, FuncRef, GroupKind, OperandRef, PathRef, SelectionConstraintError, ValueRef


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


def parse_group_kind(text: str, *, field_name: str) -> GroupKind:
    if text not in GROUP_KIND_ORDER:
        raise ValueError(f"{field_name} must be one of {list(GROUP_KIND_ORDER)}")
    return cast(GroupKind, text)


def resolve_selected_numeric_path(
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    pcbs: list[ResolvedPcbInstance],
    path: str,
) -> float:
    alias_path: dict[str, str] = {
        "outer_x": "tx_dd_outer_x",
        "outer_y": "tx_dd_outer_y",
    }
    normalized_path = alias_path.get(path, path)
    if path == "tx_region_leftover_z_mm":
        return (
            float(selected["tx_region_thickness_mm"])
            - float(selected["tx_region_vertical_z_mm"])
            - float(selected["tx_region_dd_z_mm"])
        )
    if path.startswith("selected_group_geometry."):
        parts = path.split(".")
        if len(parts) != 3:
            raise ValueError(f"Unknown constraint path: {path}")
        kind = parse_group_kind(parts[1], field_name="selected_group_geometry kind")
        field = parts[2]
        group = group_geometry_by_kind.get(kind)
        if group is None:
            raise ValueError(f"Unknown selected_group_geometry kind: {kind}")
        raw = group.get(field)
        if raw is None:
            raise ValueError(f"Unknown constraint path: {path}")
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"Constraint path '{path}' is not numeric")
        return float(raw)
    if path.startswith("selected_coil_groups."):
        parts = path.split(".")
        if len(parts) != 3:
            raise ValueError(f"Unknown constraint path: {path}")
        kind = parse_group_kind(parts[1], field_name="selected_coil_groups kind")
        field = parts[2]
        group = coil_groups_by_kind.get(kind)
        if group is None:
            raise ValueError(f"Unknown selected_coil_groups kind: {kind}")
        raw = group.get(field)
        if raw is None:
            raise ValueError(f"Unknown constraint path: {path}")
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"Constraint path '{path}' is not numeric")
        return float(raw)
    if path.startswith("selected_pcbs."):
        parts = path.split(".")
        if len(parts) != 3:
            raise ValueError(f"Unknown constraint path: {path}")
        pcb_id = parts[1]
        field = parts[2]
        pcb = next((entry for entry in pcbs if entry["id"] == pcb_id), None)
        if pcb is None:
            raise ValueError(f"Unknown selected_pcbs id: {pcb_id}")
        if field == "present":
            return float(1 if pcb["present"] else 0)
        if field == "rotation_deg":
            return float(pcb["rotation_deg"])
        if field == "position_x":
            return float(pcb["position"][0])
        if field == "position_y":
            return float(pcb["position"][1])
        if field == "position_z":
            return float(pcb["position"][2])
        raise ValueError(f"Constraint path '{path}' is not numeric")
    if path.startswith("selected_mounts."):
        parts = path.split(".")
        if len(parts) != 3:
            raise ValueError(f"Unknown constraint path: {path}")
        kind = parse_group_kind(parts[1], field_name="selected_mounts kind")
        field = parts[2]
        mounts = mounts_for_kind(pcbs, kind)
        if field == "mount_count":
            return float(len(mounts))
        if field == "index_mount_count":
            return float(sum(1 for mount in mounts if mount["selector_mode"] == "index"))
        if field == "all_mount_count":
            return float(sum(1 for mount in mounts if mount["selector_mode"] == "all"))
        if field == "max_selector_index":
            index_values = [
                cast(int, mount["selector_index"])
                for mount in mounts
                if mount["selector_mode"] == "index" and mount["selector_index"] is not None
            ]
            return float(max(index_values)) if index_values else -1.0
        raise ValueError(f"Constraint path '{path}' is not numeric")
    value = selected.get(normalized_path)
    if value is None:
        raise ValueError(f"Unknown constraint path: {path}")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Constraint path '{path}' is not numeric")
    return float(value)


def resolve_selected_comparable_path(
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    pcbs: list[ResolvedPcbInstance],
    path: str,
) -> float | str:
    alias_path: dict[str, str] = {
        "outer_x": "tx_dd_outer_x",
        "outer_y": "tx_dd_outer_y",
    }
    normalized_path = alias_path.get(path, path)
    if path == "tx_region_leftover_z_mm":
        return resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, path)
    if path.startswith("selected_group_geometry.") or path.startswith("selected_coil_groups."):
        return resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, path)
    if path.startswith("selected_pcbs."):
        parts = path.split(".")
        if len(parts) != 3:
            raise ValueError(f"Unknown constraint path: {path}")
        pcb_id = parts[1]
        field = parts[2]
        pcb = next((entry for entry in pcbs if entry["id"] == pcb_id), None)
        if pcb is None:
            raise ValueError(f"Unknown selected_pcbs id: {pcb_id}")
        if field in ("present", "rotation_deg", "position_x", "position_y", "position_z"):
            return resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, path)
        if field == "role":
            return pcb["role"]
        if field == "z_mode":
            return pcb["z_mode"]
        if field == "z_relative_base_id":
            return pcb["z_relative_base_id"] if pcb["z_relative_base_id"] is not None else ""
        if field == "z_delta_path":
            return pcb["z_delta_path"] if pcb["z_delta_path"] is not None else ""
        raise ValueError(f"Constraint path '{path}' is not comparable")
    if path.startswith("selected_mounts."):
        return resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, path)
    value = selected.get(normalized_path)
    if value is None:
        raise ValueError(f"Unknown constraint path: {path}")
    if isinstance(value, bool):
        raise ValueError(f"Constraint path '{path}' is not comparable")
    if isinstance(value, (int, float, str)):
        return value
    raise ValueError(f"Constraint path '{path}' is not comparable")


def try_parse_number(text: str) -> float | None:
    value = text.strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def mounts_for_kind(pcbs: list[ResolvedPcbInstance], kind: GroupKind) -> list[ResolvedPcbMount]:
    out: list[ResolvedPcbMount] = []
    for pcb in pcbs:
        out.extend([mount for mount in pcb["mounts"] if mount["kind"] == kind])
    return out


def max_supported_instances(kind: GroupKind, coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup]) -> int:
    hard_limit: int
    if kind == "tx_dd":
        hard_limit = 4
    elif kind == "tx_vertical":
        hard_limit = 7
    else:
        hard_limit = 2
    group = coil_groups_by_kind.get(kind)
    selected = int(group["selected_count"]) if group is not None else 0
    return max(selected, hard_limit)


def eval_numeric_expr(
    *,
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    pcbs: list[ResolvedPcbInstance],
    expr: str,
) -> tuple[float, str | None]:
    maybe_number = try_parse_number(expr)
    if maybe_number is not None:
        return maybe_number, None
    text = expr.strip()
    if text.endswith(")") and "(" in text:
        return resolve_func_ref(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
            coil_groups_by_kind=coil_groups_by_kind,
            pcbs=pcbs,
            func_text=text,
        )
    return resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, text), None


def resolve_func_ref(
    *,
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    pcbs: list[ResolvedPcbInstance],
    func_text: str,
) -> tuple[float, str | None]:
    name, parts = parse_func_call(func_text)
    if name in ("add", "mul", "min", "max"):
        if len(parts) < 2:
            raise ValueError(f"rhs.func {name}() must have at least 2 arguments")
        values = [
            eval_numeric_expr(
                selected=selected,
                group_geometry_by_kind=group_geometry_by_kind,
                coil_groups_by_kind=coil_groups_by_kind,
                pcbs=pcbs,
                expr=part,
            )[0]
            for part in parts
        ]
        if name == "add":
            return float(sum(values)), None
        if name == "mul":
            out = 1.0
            for value in values:
                out *= value
            return out, None
        if name == "min":
            return float(min(values)), None
        return float(max(values)), None
    if name == "sub":
        if len(parts) != 3:
            raise ValueError("rhs.func sub() must have 3 arguments")
        a, _ = eval_numeric_expr(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
            coil_groups_by_kind=coil_groups_by_kind,
            pcbs=pcbs,
            expr=parts[0],
        )
        b, _ = eval_numeric_expr(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
            coil_groups_by_kind=coil_groups_by_kind,
            pcbs=pcbs,
            expr=parts[1],
        )
        c, _ = eval_numeric_expr(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
            coil_groups_by_kind=coil_groups_by_kind,
            pcbs=pcbs,
            expr=parts[2],
        )
        return (a - b - c), None
    if name == "active_group":
        if len(parts) != 1:
            raise ValueError("rhs.func active_group() must have 1 group kind argument")
        kind = parse_group_kind(parts[0], field_name="active_group kind")
        group = coil_groups_by_kind.get(kind)
        if group is None:
            raise ValueError(f"active_group unknown kind: {kind}")
        return (1.0 if int(group["selected_count"]) > 0 else 0.0), None
    if name in ("feasible_turns", "feasible_turns_max"):
        if len(parts) != 4 or any(part == "" for part in parts):
            raise ValueError(
                f"rhs.func {name}() must have 4 arguments: "
                "kind, outer_x_path, outer_y_path, outer_cap_y_path"
            )
        kind = parse_group_kind(parts[0], field_name="feasible_turns kind")
        group_geometry = group_geometry_by_kind.get(kind)
        if group_geometry is None:
            raise ValueError(f"feasible_turns unknown geometry kind: {kind}")
        trace = float(group_geometry["trace"])
        gap = float(group_geometry["gap"])
        turns = int(group_geometry["turn_count_max"])
        outer_x = resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, parts[1])
        outer_y = resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, parts[2])
        cap_y = resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, parts[3])
        available_outer_y = min(outer_y, cap_y)
        feasible_turns_max = min(max_feasible_turns(outer_x, trace, gap), max_feasible_turns(available_outer_y, trace, gap))
        feasible_turns = min(turns, feasible_turns_max)
        debug = (
            f"func={name} kind={kind} turns={turns} trace={trace} gap={gap} "
            f"outer_x={outer_x} outer_y={outer_y} cap_y={cap_y} available_outer_y={available_outer_y} "
            f"feasible_turns_max={feasible_turns_max} feasible_turns={feasible_turns}"
        )
        if name == "feasible_turns_max":
            return float(feasible_turns_max), debug
        return float(feasible_turns), debug
    if name == "max_supported_mount_index":
        if len(parts) != 1:
            raise ValueError("rhs.func max_supported_mount_index() must have 1 group kind argument")
        kind = parse_group_kind(parts[0], field_name="max_supported_mount_index kind")
        return float(max_supported_instances(kind, coil_groups_by_kind) - 1), None
    if name == "max_mount_selector_index":
        if len(parts) != 1:
            raise ValueError("rhs.func max_mount_selector_index() must have 1 group kind argument")
        kind = parse_group_kind(parts[0], field_name="max_mount_selector_index kind")
        mounts = mounts_for_kind(pcbs, kind)
        index_mounts = [mount for mount in mounts if mount["selector_mode"] == "index" and mount["selector_index"] is not None]
        if not index_mounts:
            return -1.0, None
        return float(max(cast(int, mount["selector_index"]) for mount in index_mounts)), None
    raise ValueError(
        "rhs.func supports only "
        "add(...), mul(...), min(...), max(...), sub(...), active_group(kind), "
        "feasible_turns(kind,outer_x_path,outer_y_path,outer_cap_y_path), "
        "feasible_turns_max(kind,outer_x_path,outer_y_path,outer_cap_y_path), "
        "max_supported_mount_index(kind), max_mount_selector_index(kind)"
    )


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
        aggregate_value = float(sum(group["selected_count"] for group in coil_groups))
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

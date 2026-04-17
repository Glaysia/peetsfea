from __future__ import annotations

from typing import Callable, cast

from peetsfea.legacy.type1.topology.tx_dd import build_txdd_right_points, edge_points_at_path_end, extend_endpoints, rank_txdd_right_rows
from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance, SelectedParameters
from peetsfea.types.runtime_selection import coil_group_selected_count

from .constraint_paths import (
    _mount_allows_instance,
    _tx_dd_center_y_and_layer,
    _tx_vertical_instance_offset_y,
    max_supported_instances,
    mounts_for_kind,
    parse_group_kind,
    resolve_selected_numeric_path,
)
from .constraints_parse import parse_func_call
from ..domains.group_geometry import max_feasible_turns
from ..types import GroupKind

_Point3 = tuple[float, float, float]


def _txdd_right_layer_rank_by_z(*, selected_pcbs: list[ResolvedPcbInstance], instance_count: int) -> dict[int, int]:
    if instance_count != 4:
        return {}
    rows: list[tuple[float, str, int]] = []
    for instance_index in range(instance_count):
        if instance_index % 2 == 0:
            continue
        candidates: list[tuple[str, float]] = []
        for pcb in selected_pcbs:
            if not pcb["present"]:
                continue
            if _mount_allows_instance(pcb["mounts"], "tx_dd", instance_index):
                candidates.append((pcb["id"], -float(pcb["position"][2])))
        if len(candidates) != 1:
            raise ValueError(
                "tx_dd right endpoint contract violation: each right instance must map to exactly one mounted board "
                f"(instance_index={instance_index}, candidates={len(candidates)})"
            )
        board_id, z_center = candidates[0]
        rows.append((z_center, board_id, instance_index))
    return rank_txdd_right_rows(rows, instance_count=instance_count)


def _tx_bridge_representative_right_edge_y(
    *,
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    pcbs: list[ResolvedPcbInstance],
) -> tuple[float, float]:
    assert "tx_dd" in coil_groups_by_kind, "tx_bridge_right_y_margin_ok requires selected tx_dd group"
    assert "tx_vertical" in coil_groups_by_kind, "tx_bridge_right_y_margin_ok requires selected tx_vertical group"
    assert "tx_dd" in group_geometry_by_kind, "tx_bridge_right_y_margin_ok requires selected tx_dd geometry"
    assert "tx_vertical" in group_geometry_by_kind, "tx_bridge_right_y_margin_ok requires selected tx_vertical geometry"
    tx_dd_group = coil_groups_by_kind["tx_dd"]
    tx_vertical_group = coil_groups_by_kind["tx_vertical"]
    tx_dd_geometry = group_geometry_by_kind["tx_dd"]
    tx_vertical_geometry = group_geometry_by_kind["tx_vertical"]
    tx_region_outer_h = float(selected["tx_region_outer_h_mm"])
    tx_region_min_y = -tx_region_outer_h / 2.0
    tx_region_max_y = tx_region_outer_h / 2.0
    tx_region_center_y = (tx_region_min_y + tx_region_max_y) / 2.0

    tx_dd_transforms = tx_dd_group["instance_transforms"]
    tx_dd_transform_dy = tx_dd_transforms[0]["dy"] if tx_dd_transforms else 0.0
    tx_dd_instance_count = coil_group_selected_count(tx_dd_group)
    tx_dd_outer_y = float(selected["tx_dd_outer_y"])
    tx_dd_spacing_mm = float(tx_dd_group["spacing_mm"])
    tx_dd_turns = int(tx_dd_geometry["turn_count"])
    tx_dd_outer_x = float(selected["tx_dd_outer_x"])
    tx_dd_trace = float(tx_dd_geometry["trace"])
    tx_dd_gap = float(tx_dd_geometry["gap"])
    txdd_right_layer_rank = _txdd_right_layer_rank_by_z(selected_pcbs=pcbs, instance_count=tx_dd_instance_count)
    dd_right_edges: list[tuple[tuple[float, str, int], float]] = []
    for pcb in pcbs:
        if not pcb["present"]:
            continue
        for instance_index in range(tx_dd_instance_count):
            if instance_index % 2 == 0:
                continue
            if not _mount_allows_instance(pcb["mounts"], "tx_dd", instance_index):
                continue
            center_y, tx_dd_layer_index = _tx_dd_center_y_and_layer(
                instance_count=tx_dd_instance_count,
                instance_index=instance_index,
                pair_clearance_mm=tx_dd_spacing_mm,
                outer_y=tx_dd_outer_y,
                region_center_y=tx_region_center_y,
                region_min_y=tx_region_min_y,
                region_max_y=tx_region_max_y,
            )
            if instance_index in txdd_right_layer_rank:
                right_layer_index = txdd_right_layer_rank[instance_index]
            else:
                right_layer_index = tx_dd_layer_index
            capture_dd_right_d_edge = (tx_dd_instance_count == 2) or (
                tx_dd_instance_count == 4 and right_layer_index == 1
            )
            if not capture_dd_right_d_edge:
                continue
            right_points_local = build_txdd_right_points(
                turns=tx_dd_turns,
                outer_x=tx_dd_outer_x,
                outer_y=tx_dd_outer_y,
                trace=tx_dd_trace,
                gap=tx_dd_gap,
                instance_count=tx_dd_instance_count,
                layer_index=right_layer_index,
            )
            right_points_local = extend_endpoints(right_points_local, extension=(tx_dd_trace / 2.0))
            right_points = [(point[0], point[1] + center_y + tx_dd_transform_dy, point[2]) for point in right_points_local]
            d_edge = edge_points_at_path_end(points=right_points, trace=tx_dd_trace)
            candidate_edge_y = max(d_edge[0][1], d_edge[1][1])
            y_center = center_y + tx_dd_transform_dy
            selection_key = (-y_center, pcb["id"], instance_index)
            dd_right_edges.append((selection_key, candidate_edge_y))
    if len(dd_right_edges) == 0:
        raise ValueError("tx_bridge_right_y_margin_ok cannot resolve tx_dd right representative edge Y")
    dd_right_edge_y = min(dd_right_edges, key=lambda item: item[0])[1]

    tx_vertical_instance_count = coil_group_selected_count(tx_vertical_group)
    if tx_vertical_instance_count <= 0:
        raise ValueError(
            "tx_bridge_right_y_margin_ok expected tx_vertical instance_count >= 1 while resolving representative edge Y"
        )
    tx_vertical_transforms = tx_vertical_group["instance_transforms"]
    tx_vertical_transform_dy = tx_vertical_transforms[0]["dy"] if tx_vertical_transforms else 0.0
    tx_vertical_spacing_mm = float(tx_vertical_group["spacing_mm"])
    tx_vertical_trace = float(tx_vertical_geometry["trace"])
    vertical_right_edges: list[tuple[tuple[float, str, int], float]] = []
    for pcb in pcbs:
        if not pcb["present"]:
            continue
        for instance_index in range(tx_vertical_instance_count):
            if not _mount_allows_instance(pcb["mounts"], "tx_vertical", instance_index):
                continue
            off_y = _tx_vertical_instance_offset_y(
                instance_index=instance_index,
                instance_count=tx_vertical_instance_count,
                spacing_mm=tx_vertical_spacing_mm,
                trace_mm=tx_vertical_trace,
            )
            y_center = tx_region_center_y + tx_vertical_transform_dy + off_y
            selection_key = (-y_center, pcb["id"], instance_index)
            vertical_reference_y = y_center
            vertical_right_edges.append((selection_key, vertical_reference_y))
    if len(vertical_right_edges) == 0:
        raise ValueError("tx_bridge_right_y_margin_ok cannot resolve tx_vertical right representative edge Y")
    vertical_right_reference_y = min(vertical_right_edges, key=lambda item: item[0])[1]
    return dd_right_edge_y, vertical_right_reference_y


def eval_numeric_expr(
    *,
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    pcbs: list[ResolvedPcbInstance],
    expr: str,
) -> tuple[float, str | None]:
    try:
        return float(expr.strip()), None
    except ValueError:
        pass
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

    def _eval_all(parts_text: list[str]) -> list[float]:
        return [
            eval_numeric_expr(
                selected=selected,
                group_geometry_by_kind=group_geometry_by_kind,
                coil_groups_by_kind=coil_groups_by_kind,
                pcbs=pcbs,
                expr=part,
            )[0]
            for part in parts_text
        ]

    def _handle_add(parts_text: list[str]) -> tuple[float, str | None]:
        if len(parts_text) < 2:
            raise ValueError("rhs.func add() must have at least 2 arguments")
        return float(sum(_eval_all(parts_text))), None

    def _handle_mul(parts_text: list[str]) -> tuple[float, str | None]:
        if len(parts_text) < 2:
            raise ValueError("rhs.func mul() must have at least 2 arguments")
        out = 1.0
        for value in _eval_all(parts_text):
            out *= value
        return out, None

    def _handle_min(parts_text: list[str]) -> tuple[float, str | None]:
        if len(parts_text) < 2:
            raise ValueError("rhs.func min() must have at least 2 arguments")
        return float(min(_eval_all(parts_text))), None

    def _handle_max(parts_text: list[str]) -> tuple[float, str | None]:
        if len(parts_text) < 2:
            raise ValueError("rhs.func max() must have at least 2 arguments")
        return float(max(_eval_all(parts_text))), None

    def _handle_sub(parts_text: list[str]) -> tuple[float, str | None]:
        if len(parts_text) != 3:
            raise ValueError("rhs.func sub() must have 3 arguments")
        values = _eval_all(parts_text)
        return values[0] - values[1] - values[2], None

    def _handle_active_group(parts_text: list[str]) -> tuple[float, str | None]:
        if len(parts_text) != 1:
            raise ValueError("rhs.func active_group() must have 1 group kind argument")
        kind = parse_group_kind(parts_text[0], field_name="active_group kind")
        if kind not in coil_groups_by_kind:
            raise ValueError(f"active_group unknown kind: {kind}")
        group = coil_groups_by_kind[kind]
        return (1.0 if coil_group_selected_count(group) > 0 else 0.0), None

    def _handle_feasible_turns(parts_text: list[str], *, max_only: bool) -> tuple[float, str | None]:
        if len(parts_text) != 4 or any(part == "" for part in parts_text):
            raise ValueError(
                "rhs.func feasible_turns/feasible_turns_max() must have 4 arguments: "
                "kind, outer_x_path, outer_y_path, outer_cap_y_path"
            )
        kind = parse_group_kind(parts_text[0], field_name="feasible_turns kind")
        if kind not in group_geometry_by_kind:
            raise ValueError(f"feasible_turns unknown geometry kind: {kind}")
        geometry_entry = group_geometry_by_kind[kind]
        trace = float(geometry_entry["trace"])
        gap = float(geometry_entry["gap"])
        turns = int(geometry_entry["turn_count"])
        outer_x = resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, parts_text[1])
        outer_y = resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, parts_text[2])
        cap_y = resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, parts_text[3])
        if kind in coil_groups_by_kind:
            selected_count = coil_group_selected_count(coil_groups_by_kind[kind])
        else:
            selected_count = 0
        realized_outer_x = outer_x
        realized_outer_y = outer_y
        if kind == "tx_dd" and selected_count == 4:
            pitch = trace + gap
            if pitch > 0.0:
                realized_outer_x = max(0.0, outer_x - pitch)
                realized_outer_y = max(0.0, outer_y - pitch)
        available_outer_y = min(realized_outer_y, cap_y)
        feasible_turns_max = min(
            max_feasible_turns(realized_outer_x, trace, gap),
            max_feasible_turns(available_outer_y, trace, gap),
        )
        feasible_turns = min(turns, feasible_turns_max)
        debug = (
            f"func={'feasible_turns_max' if max_only else 'feasible_turns'} kind={kind} "
            f"turns={turns} trace={trace} gap={gap} outer_x={outer_x} outer_y={outer_y} "
            f"realized_outer_x={realized_outer_x} realized_outer_y={realized_outer_y} cap_y={cap_y} "
            f"available_outer_y={available_outer_y} feasible_turns_max={feasible_turns_max} feasible_turns={feasible_turns}"
        )
        return (float(feasible_turns_max), debug) if max_only else (float(feasible_turns), debug)

    def _handle_max_supported_mount_index(parts_text: list[str]) -> tuple[float, str | None]:
        if len(parts_text) != 1:
            raise ValueError("rhs.func max_supported_mount_index() must have 1 group kind argument")
        kind = parse_group_kind(parts_text[0], field_name="max_supported_mount_index kind")
        return float(max_supported_instances(kind, coil_groups_by_kind) - 1), None

    def _handle_max_mount_selector_index(parts_text: list[str]) -> tuple[float, str | None]:
        if len(parts_text) != 1:
            raise ValueError("rhs.func max_mount_selector_index() must have 1 group kind argument")
        kind = parse_group_kind(parts_text[0], field_name="max_mount_selector_index kind")
        mounts = mounts_for_kind(pcbs, kind)
        index_mounts = [
            mount for mount in mounts if mount["selector_mode"] == "index" and isinstance(mount["selector_index"], int)
        ]
        if not index_mounts:
            return -1.0, None
        return float(max(cast(int, mount["selector_index"]) for mount in index_mounts)), None

    def _handle_tx_bridge_right_y_margin_ok(parts_text: list[str]) -> tuple[float, str | None]:
        if len(parts_text) != 1:
            raise ValueError("rhs.func tx_bridge_right_y_margin_ok() must have 1 argument: margin_mm")
        margin_mm, _ = eval_numeric_expr(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
            coil_groups_by_kind=coil_groups_by_kind,
            pcbs=pcbs,
            expr=parts_text[0],
        )
        if margin_mm < 0.0:
            raise ValueError(f"rhs.func tx_bridge_right_y_margin_ok() margin_mm must be >= 0 (actual={margin_mm})")
        if "tx_vertical" not in coil_groups_by_kind:
            raise ValueError("rhs.func tx_bridge_right_y_margin_ok() requires tx_vertical group")
        tx_vertical_group = coil_groups_by_kind["tx_vertical"]
        if coil_group_selected_count(tx_vertical_group) == 0:
            return 1.0, "func=tx_bridge_right_y_margin_ok skipped because tx_vertical.selected_count == 0"
        dd_right_edge_y, vertical_right_edge_y = _tx_bridge_representative_right_edge_y(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
            coil_groups_by_kind=coil_groups_by_kind,
            pcbs=pcbs,
        )
        ok = dd_right_edge_y >= (vertical_right_edge_y + margin_mm)
        debug = (
            "func=tx_bridge_right_y_margin_ok "
            f"dd_right_edge_y={dd_right_edge_y} vertical_right_edge_y={vertical_right_edge_y} "
            f"margin_mm={margin_mm} ok={ok}"
        )
        return (1.0 if ok else 0.0), debug

    def _handle_tx_bridge_no_pierce_ok(parts_text: list[str]) -> tuple[float, str | None]:
        if len(parts_text) != 1:
            raise ValueError("rhs.func tx_bridge_no_pierce_ok() must have 1 argument: clearance_mm")
        clearance_mm, _ = eval_numeric_expr(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
            coil_groups_by_kind=coil_groups_by_kind,
            pcbs=pcbs,
            expr=parts_text[0],
        )
        if clearance_mm < 0.0:
            raise ValueError(f"rhs.func tx_bridge_no_pierce_ok() clearance_mm must be >= 0 (actual={clearance_mm})")
        if "tx_vertical" not in coil_groups_by_kind:
            raise ValueError("rhs.func tx_bridge_no_pierce_ok() requires tx_vertical group")
        tx_vertical_group = coil_groups_by_kind["tx_vertical"]
        if coil_group_selected_count(tx_vertical_group) == 0:
            return 1.0, "func=tx_bridge_no_pierce_ok skipped because tx_vertical.selected_count == 0"
        if "tx_vertical" not in group_geometry_by_kind:
            raise ValueError("rhs.func tx_bridge_no_pierce_ok() requires tx_vertical geometry")
        tx_vertical_geometry = group_geometry_by_kind["tx_vertical"]
        dd_right_edge_y, vertical_right_reference_y = _tx_bridge_representative_right_edge_y(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
            coil_groups_by_kind=coil_groups_by_kind,
            pcbs=pcbs,
        )
        vertical_right_outer_edge_y = vertical_right_reference_y + (float(tx_vertical_geometry["trace"]) / 2.0)
        ok = dd_right_edge_y >= (vertical_right_outer_edge_y + clearance_mm)
        debug = (
            "func=tx_bridge_no_pierce_ok "
            f"dd_right_edge_y={dd_right_edge_y} vertical_right_outer_edge_y={vertical_right_outer_edge_y} "
            f"clearance_mm={clearance_mm} ok={ok}"
        )
        return (1.0 if ok else 0.0), debug

    func_dispatch: dict[str, Callable[[list[str]], tuple[float, str | None]]] = {
        "add": _handle_add,
        "mul": _handle_mul,
        "min": _handle_min,
        "max": _handle_max,
        "sub": _handle_sub,
        "active_group": _handle_active_group,
        "feasible_turns": lambda values: _handle_feasible_turns(values, max_only=False),
        "feasible_turns_max": lambda values: _handle_feasible_turns(values, max_only=True),
        "max_supported_mount_index": _handle_max_supported_mount_index,
        "max_mount_selector_index": _handle_max_mount_selector_index,
        "tx_bridge_right_y_margin_ok": _handle_tx_bridge_right_y_margin_ok,
        "tx_bridge_no_pierce_ok": _handle_tx_bridge_no_pierce_ok,
    }
    if name not in func_dispatch:
        raise ValueError(
            "rhs.func supports only "
            "add(...), mul(...), min(...), max(...), sub(...), active_group(kind), "
            "feasible_turns(kind,outer_x_path,outer_y_path,outer_cap_y_path), "
            "feasible_turns_max(kind,outer_x_path,outer_y_path,outer_cap_y_path), "
            "max_supported_mount_index(kind), max_mount_selector_index(kind), "
            "tx_bridge_right_y_margin_ok(margin_mm), "
            "tx_bridge_no_pierce_ok(clearance_mm)"
        )
    return func_dispatch[name](parts)


__all__ = [
    "eval_numeric_expr",
    "resolve_func_ref",
]

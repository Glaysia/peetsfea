from __future__ import annotations

import math
from typing import Callable, Literal, cast

from peetsfea.placement_math import tx_vertical_mode2_center_x_from_tx_dd_min
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


def _alias_constraint_path(path: str) -> str:
    alias_path: dict[str, str] = {"outer_x": "tx_dd_outer_x", "outer_y": "tx_dd_outer_y"}
    return alias_path.get(path, path)


def _resolve_selected_group_geometry_numeric(
    *,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    path: str,
) -> float:
    parts = path.split(".")
    if len(parts) != 3:
        raise ValueError(f"Unknown constraint path: {path}")
    kind = parse_group_kind(parts[1], field_name="selected_group_geometry kind")
    field = parts[2]
    geometry_entry = group_geometry_by_kind.get(kind)
    if geometry_entry is None:
        raise ValueError(f"Unknown selected_group_geometry kind: {kind}")
    raw = geometry_entry.get(field)
    if raw is None:
        raise ValueError(f"Unknown constraint path: {path}")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"Constraint path '{path}' is not numeric")
    return float(raw)


def _resolve_selected_coil_groups_numeric(
    *,
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    path: str,
) -> float:
    parts = path.split(".")
    if len(parts) != 3:
        raise ValueError(f"Unknown constraint path: {path}")
    kind = parse_group_kind(parts[1], field_name="selected_coil_groups kind")
    field = parts[2]
    coil_group_entry = coil_groups_by_kind.get(kind)
    if coil_group_entry is None:
        raise ValueError(f"Unknown selected_coil_groups kind: {kind}")
    raw = coil_group_entry.get(field)
    if raw is None:
        raise ValueError(f"Unknown constraint path: {path}")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"Constraint path '{path}' is not numeric")
    return float(raw)


def _resolve_selected_pcbs_numeric(*, pcbs: list[ResolvedPcbInstance], path: str) -> float:
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


def _resolve_selected_mounts_numeric(*, pcbs: list[ResolvedPcbInstance], path: str) -> float:
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


def _resolve_scalar_numeric(*, selected: SelectedParameters, path: str) -> float:
    normalized_path = _alias_constraint_path(path)
    value = selected.get(normalized_path)
    if value is None:
        raise ValueError(f"Unknown constraint path: {path}")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Constraint path '{path}' is not numeric")
    return float(value)


def resolve_selected_numeric_path(
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    pcbs: list[ResolvedPcbInstance],
    path: str,
) -> float:
    if path == "tx_region_leftover_z_mm":
        return (
            float(selected["tx_region_thickness_mm"])
            - float(selected["tx_region_vertical_z_mm"])
            - float(selected["tx_region_dd_z_mm"])
        )
    prefix_numeric_handlers: tuple[tuple[str, Callable[[], float]], ...] = (
        ("selected_group_geometry.", lambda: _resolve_selected_group_geometry_numeric(group_geometry_by_kind=group_geometry_by_kind, path=path)),
        ("selected_coil_groups.", lambda: _resolve_selected_coil_groups_numeric(coil_groups_by_kind=coil_groups_by_kind, path=path)),
        ("selected_pcbs.", lambda: _resolve_selected_pcbs_numeric(pcbs=pcbs, path=path)),
        ("selected_mounts.", lambda: _resolve_selected_mounts_numeric(pcbs=pcbs, path=path)),
    )
    for prefix, handler in prefix_numeric_handlers:
        if path.startswith(prefix):
            return handler()
    return _resolve_scalar_numeric(selected=selected, path=path)


def _resolve_selected_pcbs_comparable(
    *,
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    pcbs: list[ResolvedPcbInstance],
    path: str,
) -> float | str:
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


def resolve_selected_comparable_path(
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    pcbs: list[ResolvedPcbInstance],
    path: str,
) -> float | str:
    if path == "tx_region_leftover_z_mm":
        return resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, path)
    if path.startswith("selected_group_geometry.") or path.startswith("selected_coil_groups.") or path.startswith("selected_mounts."):
        return resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, path)
    if path.startswith("selected_pcbs."):
        return _resolve_selected_pcbs_comparable(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
            coil_groups_by_kind=coil_groups_by_kind,
            pcbs=pcbs,
            path=path,
        )
    normalized_path = _alias_constraint_path(path)
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
        hard_limit = 6
    else:
        hard_limit = 2
    group = coil_groups_by_kind.get(kind)
    selected = int(group["selected_count"]) if group is not None else 0
    return max(selected, hard_limit)


_Point3 = tuple[float, float, float]
_Edge2P = tuple[_Point3, _Point3]


def _mount_allows_instance(mounts: list[ResolvedPcbMount], kind: GroupKind, instance_index: int) -> bool:
    for mount in mounts:
        if mount["kind"] != kind:
            continue
        selector_mode = mount["selector_mode"]
        selector_index = mount["selector_index"]
        if selector_mode == "all":
            return True
        if selector_mode == "index" and selector_index == instance_index:
            return True
    return False


def _tx_dd_center_y_and_layer(
    *,
    instance_count: int,
    instance_index: int,
    pair_clearance_mm: float,
    outer_y: float,
    region_center_y: float,
    region_min_y: float,
    region_max_y: float,
) -> tuple[float, int]:
    if instance_count not in (2, 4):
        raise ValueError(f"tx_dd selected_count must be 2 or 4 (actual={instance_count})")
    if instance_index < 0 or instance_index >= instance_count:
        raise ValueError(f"tx_dd instance index out of range: {instance_index}")
    half_outer_y = outer_y / 2.0
    pair_center_distance = outer_y + pair_clearance_mm
    half_center_distance = pair_center_distance / 2.0
    local_slot = instance_index % 2
    layer_index = 0 if instance_count == 2 else (instance_index // 2)
    sign = -1.0 if local_slot == 0 else 1.0
    center_y = region_center_y + (sign * half_center_distance)
    if (center_y - half_outer_y) < region_min_y or (center_y + half_outer_y) > region_max_y:
        raise ValueError(
            "tx_dd symmetric placement out of region "
            f"(pair_clearance_mm={pair_clearance_mm}, outer_y={outer_y}, "
            f"instance_index={instance_index}, region_min_y={region_min_y}, region_max_y={region_max_y})"
        )
    return center_y, layer_index


def _tx_vertical_instance_offset_y(*, instance_index: int, instance_count: int, spacing_mm: float, trace_mm: float) -> float:
    if instance_count <= 0:
        raise ValueError(f"tx_vertical selected_count must be >= 1 (actual={instance_count})")
    if instance_index < 0 or instance_index >= instance_count:
        raise ValueError(
            f"tx_vertical instance index out of range (instance_index={instance_index}, instance_count={instance_count})"
        )
    denom = max(1, instance_count - 1)
    d = spacing_mm / float(denom)
    if d < 0.0:
        raise ValueError(f"tx_vertical center gap d must be >= 0 (actual={d})")
    if instance_count % 2 == 0:
        center = (instance_count - 1) / 2.0
        return (float(instance_index) - center) * d
    edge_half_thickness = trace_mm / 2.0
    mid = instance_count // 2
    rel = instance_index - mid
    if rel == 0:
        return edge_half_thickness
    sign = -1.0 if rel < 0 else 1.0
    return sign * (abs(rel) * d)


def _build_rect_spiral_centerline_absolute(
    *, turns: int, outer_x: float, outer_y: float, trace: float, gap: float, z: float
) -> list[_Point3]:
    if turns < 1:
        raise ValueError("turns must be >= 1")
    if trace <= 0:
        raise ValueError("trace must be > 0")
    if gap < 0:
        raise ValueError("gap must be >= 0")
    pitch = trace + gap
    half_trace = trace / 2.0
    left = -(outer_x / 2.0) + half_trace
    right = (outer_x / 2.0) - half_trace
    top = (outer_y / 2.0) - half_trace
    bottom = -(outer_y / 2.0) + half_trace
    if left >= right or bottom >= top:
        raise ValueError("centerline outer width must be > 0")
    points: list[_Point3] = []
    for turn_idx in range(turns):
        left_k = left + (turn_idx * pitch)
        right_k = right - (turn_idx * pitch)
        top_k = top - (turn_idx * pitch)
        bottom_k = bottom + (turn_idx * pitch)
        if left_k >= right_k or bottom_k >= top_k:
            raise ValueError("invalid spiral dimensions for requested turns")
        if turn_idx == 0:
            points.append((left_k, top_k, z))
        points.append((right_k, top_k, z))
        points.append((right_k, bottom_k, z))
        points.append((left_k, bottom_k, z))
        if turn_idx < turns - 1:
            next_top = top - ((turn_idx + 1) * pitch)
            next_left = left + ((turn_idx + 1) * pitch)
            points.append((left_k, next_top, z))
            points.append((next_left, next_top, z))
    return points


def _extend_endpoints(points: list[_Point3], *, extension: float) -> list[_Point3]:
    if extension <= 0.0 or len(points) < 2:
        return points[:]
    extended = [point for point in points]
    start = list(extended[0])
    start_next = extended[1]
    start_dx = start[0] - start_next[0]
    start_dy = start[1] - start_next[1]
    start_dz = start[2] - start_next[2]
    start_len = math.sqrt((start_dx * start_dx) + (start_dy * start_dy) + (start_dz * start_dz))
    if start_len > 0.0:
        start[0] += (start_dx / start_len) * extension
        start[1] += (start_dy / start_len) * extension
        start[2] += (start_dz / start_len) * extension
    end = list(extended[-1])
    end_prev = extended[-2]
    end_dx = end[0] - end_prev[0]
    end_dy = end[1] - end_prev[1]
    end_dz = end[2] - end_prev[2]
    end_len = math.sqrt((end_dx * end_dx) + (end_dy * end_dy) + (end_dz * end_dz))
    if end_len > 0.0:
        end[0] += (end_dx / end_len) * extension
        end[1] += (end_dy / end_len) * extension
        end[2] += (end_dz / end_len) * extension
    out = extended[:]
    out[0] = (start[0], start[1], start[2])
    out[-1] = (end[0], end[1], end[2])
    return out


def _edge_points_at_path_end(*, points: list[_Point3], trace: float) -> _Edge2P:
    if len(points) < 2:
        raise ValueError("Cannot compute end edge from path with fewer than 2 points")
    end = points[-1]
    prev = points[-2]
    dx = end[0] - prev[0]
    dy = end[1] - prev[1]
    seg_len = math.hypot(dx, dy)
    if seg_len <= 1e-12:
        raise ValueError("Cannot compute end edge from zero-length final segment")
    nx = -dy / seg_len
    ny = dx / seg_len
    half_trace = trace / 2.0
    p0: _Point3 = (end[0] + (nx * half_trace), end[1] + (ny * half_trace), end[2])
    p1: _Point3 = (end[0] - (nx * half_trace), end[1] - (ny * half_trace), end[2])
    return p0, p1


def _find_txdd_right_inner_c_index(base_points: list[_Point3]) -> int:
    bottom_right_candidates = [
        (idx, abs(point[0]), abs(point[1]))
        for idx, point in enumerate(base_points)
        if point[0] > 0.0 and point[1] < 0.0
    ]
    if not bottom_right_candidates:
        raise ValueError("tx_dd right endpoint contract violation: cannot locate inner bottom-right anchor for c->A")
    min_abs_x = min(candidate[1] for candidate in bottom_right_candidates)
    min_x_candidates = [candidate for candidate in bottom_right_candidates if abs(candidate[1] - min_abs_x) <= 1e-9]
    min_abs_y = min(candidate[2] for candidate in min_x_candidates)
    min_xy_candidates = [candidate for candidate in min_x_candidates if abs(candidate[2] - min_abs_y) <= 1e-9]
    return max(candidate[0] for candidate in min_xy_candidates)


def _build_txdd_right_points_c_to_a(
    *,
    base: list[_Point3],
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
) -> list[_Point3]:
    c_index = _find_txdd_right_inner_c_index(base)
    points = [point for point in reversed(base[: c_index + 1])]
    upper_a = (
        -(outer_x + (trace + gap)) / 2.0 + (trace / 2.0),
        (outer_y + (trace + gap)) / 2.0 - (trace / 2.0),
        0.0,
    )
    last = points[-1]
    if abs(last[0] - upper_a[0]) > 1e-9:
        points.append((upper_a[0], last[1], last[2]))
    if abs(points[-1][1] - upper_a[1]) > 1e-9:
        points.append(upper_a)
    if len(points) < 2:
        raise ValueError("tx_dd right endpoint contract violation: c->A path is too short")
    return points


def _build_txdd_right_points_a_to_d(*, base: list[_Point3]) -> list[_Point3]:
    mirrored_x = [(-point[0], point[1], point[2]) for point in base]
    outer_a = base[0]
    a_index = next(
        (
            idx
            for idx, point in enumerate(mirrored_x)
            if abs(point[0] - outer_a[0]) <= 1e-9 and abs(point[1] - outer_a[1]) <= 1e-9
        ),
        None,
    )
    if a_index is None:
        raise ValueError("tx_dd right endpoint contract violation: cannot locate outer A anchor for A->D->...->d")
    rotated = mirrored_x[a_index:] + mirrored_x[:a_index]
    c_index = _find_txdd_right_inner_c_index(rotated)
    d_index = c_index - 1
    if d_index < 1:
        raise ValueError("tx_dd right endpoint contract violation: A->D->...->d path is too short")
    return [point for point in rotated[: d_index + 1]]


def _txdd_right_points(
    *,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
    instance_count: int,
    layer_index: int | None,
) -> list[_Point3]:
    turns, outer_x, outer_y = _realized_txdd_geometry(
        turns=turns,
        outer_x=outer_x,
        outer_y=outer_y,
        trace=trace,
        gap=gap,
        instance_count=instance_count,
        layer_index=layer_index,
    )
    base = _build_rect_spiral_centerline_absolute(
        turns=turns,
        outer_x=outer_x,
        outer_y=outer_y,
        trace=trace,
        gap=gap,
        z=0.0,
    )
    if instance_count == 2:
        return _build_txdd_right_points_a_to_d(base=base)
    if instance_count != 4:
        raise ValueError(f"tx_dd selected_count must be 2 or 4 for right endpoint rule (actual={instance_count})")
    if layer_index not in (0, 1):
        raise ValueError(f"tx_dd right endpoint rule requires layer index 0 or 1 (actual={layer_index})")
    if layer_index == 0:
        return _build_txdd_right_points_c_to_a(
            base=base,
            outer_x=outer_x,
            outer_y=outer_y,
            trace=trace,
            gap=gap,
        )
    return _build_txdd_right_points_a_to_d(base=base)


def _realized_txdd_geometry(
    *,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
    instance_count: int,
    layer_index: int | None,
) -> tuple[int, float, float]:
    if turns < 1:
        raise ValueError(f"tx_dd turn_count_max must be >= 1 (actual={turns})")
    if instance_count == 2:
        return turns, outer_x, outer_y
    if instance_count != 4:
        raise ValueError(f"tx_dd selected_count must be 2 or 4 (actual={instance_count})")
    if layer_index not in (0, 1):
        raise ValueError(f"tx_dd layer index must be 0 or 1 for selected_count=4 (actual={layer_index})")
    if layer_index == 1:
        return turns, outer_x, outer_y

    pitch = trace + gap
    if pitch <= 0.0:
        raise ValueError(f"tx_dd pitch must be > 0 (trace={trace}, gap={gap})")
    lower_outer_x = outer_x - pitch
    lower_outer_y = outer_y - pitch
    if lower_outer_x <= trace or lower_outer_y <= trace:
        raise ValueError(
            "tx_dd lower-layer interleave contract violation: one-pitch inset leaves no valid lower-layer width "
            f"(outer_x={outer_x}, outer_y={outer_y}, trace={trace}, gap={gap}, "
            f"lower_outer_x={lower_outer_x}, lower_outer_y={lower_outer_y})"
        )
    feasible_lower_turns = min(
        max_feasible_turns(lower_outer_x, trace, gap),
        max_feasible_turns(lower_outer_y, trace, gap),
    )
    if turns > feasible_lower_turns:
        raise ValueError(
            "tx_dd lower-layer interleave contract violation: requested turns do not fit after one-pitch inset "
            f"(turns={turns}, feasible_lower_turns={feasible_lower_turns}, "
            f"lower_outer_x={lower_outer_x}, lower_outer_y={lower_outer_y}, trace={trace}, gap={gap})"
        )
    return turns, lower_outer_x, lower_outer_y


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
    if len(rows) != 2:
        raise ValueError(
            "tx_dd right endpoint contract violation: expected exactly 2 right instances for selected_count=4 "
            f"(actual={len(rows)})"
        )
    rows.sort(key=lambda item: (item[0], item[1], item[2]))
    return {rows[0][2]: 0, rows[1][2]: 1}


def _tx_bridge_representative_right_edge_y(
    *,
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    pcbs: list[ResolvedPcbInstance],
) -> tuple[float, float]:
    tx_dd_group = coil_groups_by_kind.get("tx_dd")
    if tx_dd_group is None:
        raise ValueError("tx_bridge_right_y_margin_ok requires selected tx_dd group")
    tx_vertical_group = coil_groups_by_kind.get("tx_vertical")
    if tx_vertical_group is None:
        raise ValueError("tx_bridge_right_y_margin_ok requires selected tx_vertical group")
    tx_dd_geometry = group_geometry_by_kind.get("tx_dd")
    if tx_dd_geometry is None:
        raise ValueError("tx_bridge_right_y_margin_ok requires selected tx_dd geometry")
    tx_vertical_geometry = group_geometry_by_kind.get("tx_vertical")
    if tx_vertical_geometry is None:
        raise ValueError("tx_bridge_right_y_margin_ok requires selected tx_vertical geometry")

    tx_region_outer_h = float(selected["tx_region_outer_h_mm"])
    tx_region_min_y = -tx_region_outer_h / 2.0
    tx_region_max_y = tx_region_outer_h / 2.0
    tx_region_center_y = (tx_region_min_y + tx_region_max_y) / 2.0

    tx_dd_transforms = tx_dd_group["instance_transforms"]
    tx_dd_transform_dy = tx_dd_transforms[0]["dy"] if tx_dd_transforms else 0.0
    tx_dd_instance_count = int(tx_dd_group["selected_count"])
    tx_dd_outer_y = float(selected["tx_dd_outer_y"])
    tx_dd_spacing_mm = float(tx_dd_group["spacing_mm"])
    tx_dd_turns = int(tx_dd_geometry["turn_count_max"])
    tx_dd_outer_x = float(selected["tx_dd_outer_x"])
    tx_dd_trace = float(tx_dd_geometry["trace"])
    tx_dd_gap = float(tx_dd_geometry["gap"])
    txdd_right_layer_rank = _txdd_right_layer_rank_by_z(selected_pcbs=pcbs, instance_count=tx_dd_instance_count)
    dd_right_selection_key: tuple[float, str, int] | None = None
    dd_right_edge_y: float | None = None
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
            right_layer_index = txdd_right_layer_rank.get(instance_index, tx_dd_layer_index)
            capture_dd_right_d_edge = (tx_dd_instance_count == 2) or (
                tx_dd_instance_count == 4 and right_layer_index == 1
            )
            if not capture_dd_right_d_edge:
                continue
            right_points_local = _txdd_right_points(
                turns=tx_dd_turns,
                outer_x=tx_dd_outer_x,
                outer_y=tx_dd_outer_y,
                trace=tx_dd_trace,
                gap=tx_dd_gap,
                instance_count=tx_dd_instance_count,
                layer_index=right_layer_index,
            )
            right_points_local = _extend_endpoints(right_points_local, extension=(tx_dd_trace / 2.0))
            right_points = [
                (point[0], point[1] + center_y + tx_dd_transform_dy, point[2]) for point in right_points_local
            ]
            d_edge = _edge_points_at_path_end(points=right_points, trace=tx_dd_trace)
            candidate_edge_y = max(d_edge[0][1], d_edge[1][1])
            y_center = center_y + tx_dd_transform_dy
            selection_key = (-y_center, pcb["id"], instance_index)
            if dd_right_selection_key is None or selection_key < dd_right_selection_key:
                dd_right_selection_key = selection_key
                dd_right_edge_y = candidate_edge_y
    if dd_right_edge_y is None:
        raise ValueError("tx_bridge_right_y_margin_ok cannot resolve tx_dd right representative edge Y")

    tx_vertical_instance_count = int(tx_vertical_group["selected_count"])
    if tx_vertical_instance_count <= 0:
        raise ValueError(
            "tx_bridge_right_y_margin_ok expected tx_vertical selected_count >= 1 while resolving representative edge Y"
        )
    tx_vertical_transforms = tx_vertical_group["instance_transforms"]
    tx_vertical_transform_dy = tx_vertical_transforms[0]["dy"] if tx_vertical_transforms else 0.0
    tx_vertical_spacing_mm = float(tx_vertical_group["spacing_mm"])
    tx_vertical_trace = float(tx_vertical_geometry["trace"])
    tx_vertical_layout_mode = int(selected["tx_vertical_layout_mode"])
    tx_vertical_plane = cast(Literal["ZX", "YZ"], selected["tx_vertical_plane"])
    vertical_right_selection_key: tuple[float, str, int] | None = None
    vertical_right_reference_y: float | None = None
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
            if vertical_right_selection_key is None or selection_key < vertical_right_selection_key:
                vertical_right_selection_key = selection_key
                if tx_vertical_layout_mode == 2 or tx_vertical_plane == "YZ":
                    vertical_right_reference_y = y_center + (float(selected["tx_vertical_outer_x"]) / 2.0)
                else:
                    vertical_right_reference_y = y_center
    if vertical_right_reference_y is None:
        raise ValueError("tx_bridge_right_y_margin_ok cannot resolve tx_vertical right representative edge Y")
    return dd_right_edge_y, vertical_right_reference_y


def _tx_vertical_mode2_center_x_in_region_ok(
    *,
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
) -> tuple[float, str]:
    tx_vertical_layout_mode = int(selected["tx_vertical_layout_mode"])
    if tx_vertical_layout_mode != 2:
        return 1.0, "func=tx_vertical_mode2_center_x_in_region_ok skipped because tx_vertical_layout_mode != 2"
    tx_vertical_geometry = group_geometry_by_kind.get("tx_vertical")
    if tx_vertical_geometry is None:
        raise ValueError("tx_vertical_mode2_center_x_in_region_ok requires tx_vertical geometry")
    tx_region_min_x = 0.0
    tx_region_max_x = float(selected["tx_region_outer_w_mm"])
    tx_dd_outer_x = float(selected["tx_dd_outer_x"])
    ratio = float(selected["tx_vertical_mode2_x_ratio_to_tx_dd_center"])
    center_x = tx_vertical_mode2_center_x_from_tx_dd_min(
        tx_dd_min_x=tx_region_min_x,
        tx_dd_outer_x=tx_dd_outer_x,
        x_ratio=ratio,
    )
    half_trace = float(tx_vertical_geometry["trace"]) / 2.0
    min_center_x = tx_region_min_x + half_trace
    max_center_x = tx_region_max_x - half_trace
    ok = min_center_x <= center_x <= max_center_x
    debug = (
        "func=tx_vertical_mode2_center_x_in_region_ok "
        f"center_x={center_x} min_center_x={min_center_x} max_center_x={max_center_x} "
        f"ratio={ratio} tx_dd_min_x={tx_region_min_x} tx_dd_max_x={tx_region_min_x + tx_dd_outer_x} ok={ok}"
    )
    return (1.0 if ok else 0.0), debug


def _tx_vertical_mode2_pair_y_in_region_ok(
    *,
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    pcbs: list[ResolvedPcbInstance],
) -> tuple[float, str]:
    tx_vertical_layout_mode = int(selected["tx_vertical_layout_mode"])
    if tx_vertical_layout_mode != 2:
        return 1.0, "func=tx_vertical_mode2_pair_y_in_region_ok skipped because tx_vertical_layout_mode != 2"
    tx_vertical_group = coil_groups_by_kind.get("tx_vertical")
    if tx_vertical_group is None:
        raise ValueError("tx_vertical_mode2_pair_y_in_region_ok requires tx_vertical group")
    tx_vertical_geometry = group_geometry_by_kind.get("tx_vertical")
    if tx_vertical_geometry is None:
        raise ValueError("tx_vertical_mode2_pair_y_in_region_ok requires tx_vertical geometry")

    tx_region_outer_h = float(selected["tx_region_outer_h_mm"])
    tx_region_min_y = -tx_region_outer_h / 2.0
    tx_region_max_y = tx_region_outer_h / 2.0
    tx_region_center_y = (tx_region_min_y + tx_region_max_y) / 2.0
    transforms = tx_vertical_group["instance_transforms"]
    transform_dy = transforms[0]["dy"] if transforms else 0.0
    spacing_mm = float(tx_vertical_group["spacing_mm"])
    trace_mm = float(tx_vertical_geometry["trace"])
    half_span = float(selected["tx_vertical_outer_x"]) + (float(selected["tx_vertical_mode2_pair_spacing_mm"]) / 2.0)

    checked_instances = 0
    for pcb in pcbs:
        if not pcb["present"]:
            continue
        for instance_index in range(int(tx_vertical_group["selected_count"])):
            if not _mount_allows_instance(pcb["mounts"], "tx_vertical", instance_index):
                continue
            checked_instances += 1
            off_y = _tx_vertical_instance_offset_y(
                instance_index=instance_index,
                instance_count=int(tx_vertical_group["selected_count"]),
                spacing_mm=spacing_mm,
                trace_mm=trace_mm,
            )
            logical_center_y = tx_region_center_y + transform_dy + off_y
            pair_min_y = logical_center_y - half_span
            pair_max_y = logical_center_y + half_span
            ok = pair_min_y >= tx_region_min_y and pair_max_y <= tx_region_max_y
            debug = (
                "func=tx_vertical_mode2_pair_y_in_region_ok "
                f"instance_index={instance_index} board_id={pcb['id']} "
                f"logical_center_y={logical_center_y} half_span={half_span} "
                f"pair_min_y={pair_min_y} pair_max_y={pair_max_y} "
                f"region_min_y={tx_region_min_y} region_max_y={tx_region_max_y} ok={ok}"
            )
            if not ok:
                return 0.0, debug

    if checked_instances == 0:
        return 1.0, "func=tx_vertical_mode2_pair_y_in_region_ok skipped because no mounted tx_vertical instance"
    return 1.0, (
        "func=tx_vertical_mode2_pair_y_in_region_ok "
        f"checked_instances={checked_instances} half_span={half_span} "
        f"region_min_y={tx_region_min_y} region_max_y={tx_region_max_y} ok=True"
    )


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
        group = coil_groups_by_kind.get(kind)
        if group is None:
            raise ValueError(f"active_group unknown kind: {kind}")
        return (1.0 if int(group["selected_count"]) > 0 else 0.0), None

    def _handle_feasible_turns(parts_text: list[str], *, max_only: bool) -> tuple[float, str | None]:
        if len(parts_text) != 4 or any(part == "" for part in parts_text):
            raise ValueError(
                "rhs.func feasible_turns/feasible_turns_max() must have 4 arguments: "
                "kind, outer_x_path, outer_y_path, outer_cap_y_path"
            )
        kind = parse_group_kind(parts_text[0], field_name="feasible_turns kind")
        geometry_entry = group_geometry_by_kind.get(kind)
        if geometry_entry is None:
            raise ValueError(f"feasible_turns unknown geometry kind: {kind}")
        trace = float(geometry_entry["trace"])
        gap = float(geometry_entry["gap"])
        turns = int(geometry_entry["turn_count_max"])
        outer_x = resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, parts_text[1])
        outer_y = resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, parts_text[2])
        cap_y = resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, parts_text[3])
        group_entry = coil_groups_by_kind.get(kind)
        selected_count = int(group_entry["selected_count"]) if group_entry is not None else 0
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
            mount for mount in mounts if mount["selector_mode"] == "index" and mount["selector_index"] is not None
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
        tx_vertical_group = coil_groups_by_kind.get("tx_vertical")
        if tx_vertical_group is None:
            raise ValueError("rhs.func tx_bridge_right_y_margin_ok() requires tx_vertical group")
        if int(tx_vertical_group["selected_count"]) == 0:
            return 1.0, "func=tx_bridge_right_y_margin_ok skipped because tx_vertical.selected_count == 0"
        tx_vertical_plane = cast(Literal["ZX", "YZ"], selected["tx_vertical_plane"])
        if tx_vertical_plane == "YZ":
            return 1.0, "func=tx_bridge_right_y_margin_ok skipped because tx_vertical_plane == 'YZ'"
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
        tx_vertical_group = coil_groups_by_kind.get("tx_vertical")
        if tx_vertical_group is None:
            raise ValueError("rhs.func tx_bridge_no_pierce_ok() requires tx_vertical group")
        if int(tx_vertical_group["selected_count"]) == 0:
            return 1.0, "func=tx_bridge_no_pierce_ok skipped because tx_vertical.selected_count == 0"
        tx_vertical_plane = cast(Literal["ZX", "YZ"], selected["tx_vertical_plane"])
        if tx_vertical_plane == "YZ":
            return 1.0, "func=tx_bridge_no_pierce_ok skipped because tx_vertical_plane == 'YZ'"
        tx_vertical_geometry = group_geometry_by_kind.get("tx_vertical")
        if tx_vertical_geometry is None:
            raise ValueError("rhs.func tx_bridge_no_pierce_ok() requires tx_vertical geometry")
        dd_right_edge_y, vertical_right_reference_y = _tx_bridge_representative_right_edge_y(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
            coil_groups_by_kind=coil_groups_by_kind,
            pcbs=pcbs,
        )
        if tx_vertical_plane == "YZ":
            vertical_right_outer_edge_y = vertical_right_reference_y
        else:
            vertical_right_outer_edge_y = vertical_right_reference_y + (float(tx_vertical_geometry["trace"]) / 2.0)
        ok = dd_right_edge_y >= (vertical_right_outer_edge_y + clearance_mm)
        debug = (
            "func=tx_bridge_no_pierce_ok "
            f"dd_right_edge_y={dd_right_edge_y} vertical_right_outer_edge_y={vertical_right_outer_edge_y} "
            f"clearance_mm={clearance_mm} ok={ok}"
        )
        return (1.0 if ok else 0.0), debug

    def _handle_tx_vertical_mode2_center_x_in_region_ok(parts_text: list[str]) -> tuple[float, str | None]:
        if len(parts_text) != 0:
            raise ValueError("rhs.func tx_vertical_mode2_center_x_in_region_ok() must not have arguments")
        value, debug = _tx_vertical_mode2_center_x_in_region_ok(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
        )
        return value, debug

    def _handle_tx_vertical_mode2_pair_y_in_region_ok(parts_text: list[str]) -> tuple[float, str | None]:
        if len(parts_text) != 0:
            raise ValueError("rhs.func tx_vertical_mode2_pair_y_in_region_ok() must not have arguments")
        value, debug = _tx_vertical_mode2_pair_y_in_region_ok(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
            coil_groups_by_kind=coil_groups_by_kind,
            pcbs=pcbs,
        )
        return value, debug

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
        "tx_vertical_mode2_center_x_in_region_ok": _handle_tx_vertical_mode2_center_x_in_region_ok,
        "tx_vertical_mode2_pair_y_in_region_ok": _handle_tx_vertical_mode2_pair_y_in_region_ok,
    }
    handler = func_dispatch.get(name)
    if handler is None:
        raise ValueError(
            "rhs.func supports only "
            "add(...), mul(...), min(...), max(...), sub(...), active_group(kind), "
            "feasible_turns(kind,outer_x_path,outer_y_path,outer_cap_y_path), "
            "feasible_turns_max(kind,outer_x_path,outer_y_path,outer_cap_y_path), "
            "max_supported_mount_index(kind), max_mount_selector_index(kind), "
            "tx_bridge_right_y_margin_ok(margin_mm), "
            "tx_bridge_no_pierce_ok(clearance_mm), "
            "tx_vertical_mode2_center_x_in_region_ok(), "
            "tx_vertical_mode2_pair_y_in_region_ok()"
        )
    return handler(parts)


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

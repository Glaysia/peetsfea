from __future__ import annotations

from typing import Callable, cast

from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance, ResolvedPcbMount, SelectedParameters
from peetsfea.types.runtime_selection import coil_group_selected_count

from ..constants import GROUP_KIND_ORDER
from ..types import GroupKind


def parse_group_kind(text: str, *, field_name: str) -> GroupKind:
    if text not in GROUP_KIND_ORDER:
        raise ValueError(f"{field_name} must be one of {list(GROUP_KIND_ORDER)}")
    return cast(GroupKind, text)


def _alias_constraint_path(path: str) -> str:
    alias_path: dict[str, str] = {"outer_x": "tx_dd_outer_x", "outer_y": "tx_dd_outer_y"}
    if path in alias_path:
        return alias_path[path]
    return path


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
    if kind not in group_geometry_by_kind:
        raise ValueError(f"Unknown selected_group_geometry kind: {kind}")
    geometry_entry = group_geometry_by_kind[kind]
    if field not in geometry_entry:
        raise ValueError(f"Unknown constraint path: {path}")
    raw = geometry_entry[field]
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
    if kind not in coil_groups_by_kind:
        raise ValueError(f"Unknown selected_coil_groups kind: {kind}")
    coil_group_entry = coil_groups_by_kind[kind]
    if field == "selected_count":
        return float(coil_group_selected_count(coil_group_entry))
    if field not in coil_group_entry:
        raise ValueError(f"Unknown constraint path: {path}")
    raw = coil_group_entry[field]
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"Constraint path '{path}' is not numeric")
    return float(raw)


def _resolve_selected_pcbs_numeric(*, pcbs: list[ResolvedPcbInstance], path: str) -> float:
    parts = path.split(".")
    if len(parts) != 3:
        raise ValueError(f"Unknown constraint path: {path}")
    pcb_id = parts[1]
    field = parts[2]
    for entry in pcbs:
        if entry["id"] == pcb_id:
            pcb = entry
            break
    else:
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
            if mount["selector_mode"] == "index" and isinstance(mount["selector_index"], int)
        ]
        return float(max(index_values)) if index_values else -1.0
    raise ValueError(f"Constraint path '{path}' is not numeric")


def _resolve_scalar_numeric(*, selected: SelectedParameters, path: str) -> float:
    normalized_path = _alias_constraint_path(path)
    if normalized_path not in selected:
        raise ValueError(f"Unknown constraint path: {path}")
    value = selected[normalized_path]
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
    for entry in pcbs:
        if entry["id"] == pcb_id:
            pcb = entry
            break
    else:
        raise ValueError(f"Unknown selected_pcbs id: {pcb_id}")
    if field in ("present", "rotation_deg", "position_x", "position_y", "position_z"):
        return resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, path)
    if field == "role":
        return pcb["role"]
    if field == "z_mode":
        return pcb["z_mode"]
    if field == "z_relative_base_id":
        if not isinstance(pcb["z_relative_base_id"], str) or pcb["z_relative_base_id"] == "":
            raise ValueError(f"Constraint path '{path}' requires relative_to_pcb z_relative_base_id")
        return pcb["z_relative_base_id"]
    if field == "z_delta_path":
        if not isinstance(pcb["z_delta_path"], str) or pcb["z_delta_path"] == "":
            raise ValueError(f"Constraint path '{path}' requires relative_to_pcb z_delta_path")
        return pcb["z_delta_path"]
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
    if normalized_path not in selected:
        raise ValueError(f"Unknown constraint path: {path}")
    value = selected[normalized_path]
    if isinstance(value, bool):
        raise ValueError(f"Constraint path '{path}' is not comparable")
    if isinstance(value, (int, float, str)):
        return value
    raise ValueError(f"Constraint path '{path}' is not comparable")


def try_parse_number(text: str) -> float:
    value = text.strip()
    if value == "":
        raise ValueError("empty numeric expression")
    return float(value)


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
    if kind in coil_groups_by_kind:
        selected = coil_group_selected_count(coil_groups_by_kind[kind])
    else:
        selected = 0
    return max(selected, hard_limit)


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
        raise ValueError(f"tx_dd instance_count must be 2 or 4 (actual={instance_count})")
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
        raise ValueError(f"tx_vertical instance_count must be >= 1 (actual={instance_count})")
    if instance_index < 0 or instance_index >= instance_count:
        raise ValueError(
            f"tx_vertical instance index out of range (instance_index={instance_index}, instance_count={instance_count})"
        )
    denom = max(1, instance_count - 1)
    d = spacing_mm / float(denom)
    if d < 0.0:
        raise ValueError(f"tx_vertical center gap d must be >= 0 (actual={d})")
    center = (instance_count - 1) / 2.0
    return (float(instance_index) - center) * d


__all__ = [
    "_mount_allows_instance",
    "_tx_dd_center_y_and_layer",
    "_tx_vertical_instance_offset_y",
    "max_supported_instances",
    "mounts_for_kind",
    "parse_group_kind",
    "resolve_selected_comparable_path",
    "resolve_selected_numeric_path",
    "try_parse_number",
]

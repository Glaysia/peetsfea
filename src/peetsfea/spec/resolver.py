from __future__ import annotations

import math
from typing import Literal, Sequence, TypedDict, TypeAlias, cast

from peetsfea.spec.loader import TOMLTable, TOMLValue, require_table
from peetsfea.types.manifest import (
    GroupGeometryParams,
    ResolvedCoilGroup,
    ResolvedPcbInstance,
    SelectedParameters,
    SelectedParametersMax,
)


Number: TypeAlias = int | float
SamplingContext: TypeAlias = dict[str, Number]

SCALAR_RANGE_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("coil_shape.tx_dd.outer_x", "tx_dd_outer_x", False),
    ("coil_shape.tx_dd.outer_y", "tx_dd_outer_y", False),
    ("coil_shape.tx_vertical.outer_x", "tx_vertical_outer_x", False),
    ("coil_shape.tx_vertical.outer_y", "tx_vertical_outer_y", False),
    ("coil_shape.rx_dd.outer_x", "rx_dd_outer_x", False),
    ("coil_shape.rx_dd.outer_y", "rx_dd_outer_y", False),
    ("coil_shape.inner_margin_x", "inner_margin_x", False),
    ("coil_shape.inner_margin_y", "inner_margin_y", False),
    ("coil_spacing.tx_dd_pair_spacing_ratio", "tx_dd_pair_spacing_ratio", False),
    ("coil_spacing.rx_dd_pair_spacing_ratio", "rx_dd_pair_spacing_ratio", False),
    ("coil_spacing.tx_vertical_span_mm", "tx_vertical_span_mm", False),
    ("tv.width_mm", "tv_width_mm", False),
    ("tv.height_mm", "tv_height_mm", False),
    ("tv.thickness_mm", "tv_thickness_mm", False),
    ("tv.base_z_mm", "tv_base_z_mm", False),
    ("tx.region.outer_w_mm", "tx_region_outer_w_mm", False),
    ("tx.region.outer_h_mm", "tx_region_outer_h_mm", False),
    ("tx.region.thickness_mm", "tx_region_thickness_mm", False),
    ("tx.region.z_parts.vertical_z_mm", "tx_region_vertical_z_mm", False),
    ("tx.region.z_parts.dd_z_mm", "tx_region_dd_z_mm", False),
    ("rx.region.outer_w_mm", "rx_region_outer_w_mm", False),
    ("rx.region.outer_h_mm", "rx_region_outer_h_mm", False),
    ("rx.region.thickness_mm", "rx_region_thickness_mm", False),
    ("wall.thickness_mm", "wall_thickness_mm", False),
    ("wall.size_y_mm", "wall_size_y_mm", False),
    ("wall.size_z_mm", "wall_size_z_mm", False),
    ("floor.thickness_mm", "floor_thickness_mm", False),
    ("floor.size_x_mm", "floor_size_x_mm", False),
    ("floor.size_y_mm", "floor_size_y_mm", False),
    ("coil_material.via_diameter_mm", "via_diameter_mm", False),
    ("coil_material.pcb_thickness_mm", "pcb_thickness_mm", False),
    ("coil_material.cu_thickness_mm", "cu_thickness_mm", False),
    ("coil_material.fr4_er", "fr4_er", False),
    ("scene_anchor.shelf_height_mm", "shelf_height_mm", False),
    ("scene_anchor.shelf_min_size_x_mm", "shelf_min_size_x_mm", False),
    ("scene_anchor.rx_region_bottom_from_tv_mm", "rx_region_bottom_from_tv_mm", False),
    ("coil_placement.tx_dd_top_clearance_mm", "tx_dd_top_clearance_mm", False),
    ("coil_placement.rx_face_clearance_mm", "rx_face_clearance_mm", False),
)

SCALAR_OFFSET: dict[str, int] = {path: idx for idx, (path, _, _) in enumerate(SCALAR_RANGE_SPECS)}
GROUP_KIND_ORDER: tuple[str, ...] = ("tx_dd", "tx_vertical", "rx_dd")
GROUP_OFFSET_BASE = 100
PCB_OFFSET_BASE = 200
GROUP_GEOMETRY_OFFSET_BASE = 300
ATTEMPT_STRIDE = 1009


class SelectionConstraintError(ValueError):
    pass


REMOVED_PATHS: tuple[str, ...] = (
    "coil_shape.outer_x",
    "coil_shape.outer_y",
    "coil_spacing.tx_dd_pair_spacing_mm",
    "coil_spacing.rx_dd_pair_spacing_mm",
)


def _reject_removed_paths(spec: TOMLTable) -> None:
    for path in REMOVED_PATHS:
        try:
            _read_path(spec, path)
        except ValueError:
            continue
        raise ValueError(f"Removed path in spec_version 0.1.8: {path}")

def _build_candidates(is_integer: bool, start: float, end: float, count: int) -> Sequence[Number]:
    raw_values: list[float]
    if count == 1:
        raw_values = [start]
    else:
        step = (end - start) / float(count - 1)
        raw_values = [start + (step * i) for i in range(count)]

    if not is_integer:
        return tuple(raw_values)

    rounded = [int(math.floor(value + 0.5)) for value in raw_values]
    deduped: list[Number] = []
    seen: set[int] = set()
    for value in rounded:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return tuple(deduped)


def _read_path(root: TOMLTable, dotted_path: str) -> TOMLValue:
    parts = dotted_path.split(".")
    current: TOMLValue = root
    for idx, part in enumerate(parts):
        if not isinstance(current, dict):
            raise ValueError(f"{'.'.join(parts[:idx])} must be a table/object")
        if part not in current:
            raise ValueError(f"Missing required path: {dotted_path}")
        current = current[part]
    return current


def _parse_range_at_path(root: TOMLTable, dotted_path: str, expect_integer: bool) -> tuple[bool, float, float, int]:
    table = require_table(_read_path(root, dotted_path), dotted_path)
    if set(table.keys()) != {"range"}:
        raise ValueError(f"{dotted_path} supports only the 'range' key")

    raw_range = table.get("range")
    if not isinstance(raw_range, list) or len(raw_range) != 4:
        raise ValueError(f"{dotted_path}.range must be [is_integer, start, end, count]")
    is_integer, start, end, count = raw_range

    if not isinstance(is_integer, bool):
        raise ValueError(f"{dotted_path}.range[0] (is_integer) must be bool")
    if isinstance(start, bool) or not isinstance(start, (int, float)):
        raise ValueError(f"{dotted_path}.range[1] (start) must be number")
    if isinstance(end, bool) or not isinstance(end, (int, float)):
        raise ValueError(f"{dotted_path}.range[2] (end) must be number")
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError(f"{dotted_path}.range[3] (count) must be int")
    if count < 1:
        raise ValueError(f"{dotted_path}.range[3] (count) must be >= 1")
    if end < start:
        raise ValueError(f"{dotted_path}.range[2] (end) must be >= range[1] (start)")
    if is_integer != expect_integer:
        expected = "true" if expect_integer else "false"
        raise ValueError(f"{dotted_path}.range[0] (is_integer) must be {expected}")
    return is_integer, float(start), float(end), count


def _sample_candidate(candidates: Sequence[Number], *, seed: int, offset: int, attempt: int) -> Number:
    if len(candidates) == 0:
        raise ValueError("No candidates available for sampling")
    return candidates[(seed + offset + (attempt * ATTEMPT_STRIDE)) % len(candidates)]


def _select_range_value(
    root: TOMLTable,
    dotted_path: str,
    expect_integer: bool,
    seed: int,
    offset: int,
    attempt: int,
    context: SamplingContext,
) -> Number:
    if dotted_path in context:
        return context[dotted_path]
    is_integer, start, end, count = _parse_range_at_path(root, dotted_path, expect_integer=expect_integer)
    candidates = _build_candidates(is_integer=is_integer, start=start, end=end, count=count)
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated from {dotted_path}.range")
    selected = _sample_candidate(candidates, seed=seed, offset=offset, attempt=attempt)
    context[dotted_path] = selected
    return selected


def _select_range_end_value(root: TOMLTable, dotted_path: str, expect_integer: bool) -> Number:
    is_integer, _, end, _ = _parse_range_at_path(root, dotted_path, expect_integer=expect_integer)
    if is_integer:
        return int(math.floor(end + 0.5))
    return float(end)


def _parse_string_value_at_path(root: TOMLTable, dotted_path: str, *, allowed: set[str]) -> str:
    table = require_table(_read_path(root, dotted_path), dotted_path)
    if set(table.keys()) != {"value"}:
        raise ValueError(f"{dotted_path} supports only the 'value' key")
    raw_value = table.get("value")
    if not isinstance(raw_value, str):
        raise ValueError(f"{dotted_path}.value must be string")
    if raw_value not in allowed:
        raise ValueError(f"{dotted_path}.value must be one of {sorted(allowed)}")
    return raw_value


def _resolve_group_geometry(
    spec: TOMLTable,
    seed: int,
    attempt: int,
    context: SamplingContext,
    selected_params: SelectedParameters,
) -> list[GroupGeometryParams]:
    groups_table = require_table(spec.get("coil_groups_params"), "coil_groups_params")
    required_kinds = set(GROUP_KIND_ORDER)
    if set(groups_table.keys()) != required_kinds:
        raise ValueError("coil_groups_params must contain exactly {tx_dd, tx_vertical, rx_dd}")

    selected_geometry: list[GroupGeometryParams] = []
    for idx, kind in enumerate(GROUP_KIND_ORDER):
        kind_root = f"coil_groups_params.{kind}"
        kind_table = require_table(groups_table.get(kind), kind_root)
        if set(kind_table.keys()) != {"turn_count_max", "band_ratio", "metal_ratio"}:
            raise ValueError(f"{kind_root} must contain only ['turn_count_max', 'band_ratio', 'metal_ratio']")

        offset = GROUP_GEOMETRY_OFFSET_BASE + (idx * 10)
        turns = _select_range_value(
            spec, f"{kind_root}.turn_count_max", expect_integer=True, seed=seed, offset=offset, attempt=attempt, context=context
        )
        band_ratio = _select_range_value(
            spec,
            f"{kind_root}.band_ratio",
            expect_integer=False,
            seed=seed,
            offset=offset + 1,
            attempt=attempt,
            context=context,
        )
        metal_ratio = _select_range_value(
            spec,
            f"{kind_root}.metal_ratio",
            expect_integer=False,
            seed=seed,
            offset=offset + 2,
            attempt=attempt,
            context=context,
        )
        n_turns = int(turns)
        band_ratio_float = float(band_ratio)
        ratio = float(metal_ratio)
        if n_turns < 1:
            raise ValueError(f"{kind_root}.turn_count_max must be >= 1")
        if band_ratio_float <= 0 or band_ratio_float >= 1:
            raise ValueError(f"{kind_root}.band_ratio must be > 0 and < 1")
        if ratio <= 0 or ratio >= 1:
            raise ValueError(f"{kind_root}.metal_ratio must be > 0 and < 1")
        if kind == "tx_dd":
            outer_x = float(selected_params["tx_dd_outer_x"])
            outer_y = float(selected_params["tx_dd_outer_y"])
        elif kind == "tx_vertical":
            outer_x = float(selected_params["tx_vertical_outer_x"])
            outer_y = float(selected_params["tx_vertical_outer_y"])
        else:
            outer_x = float(selected_params["rx_dd_outer_x"])
            outer_y = float(selected_params["rx_dd_outer_y"])
        effective_outer_y = min(outer_y, float(selected_params["tx_region_vertical_z_mm"])) if kind == "tx_vertical" else outer_y
        base_outer = min(outer_x, effective_outer_y)
        if base_outer <= 0:
            raise ValueError(f"{kind_root}.base_outer (derived) must be > 0")
        band_mm = band_ratio_float * base_outer
        pitch = band_mm / float(n_turns)
        trace = pitch * ratio
        gap = pitch * (1.0 - ratio)
        if trace <= 0:
            raise ValueError(f"{kind_root}.trace (derived) must be > 0")
        if gap < 0:
            raise ValueError(f"{kind_root}.gap (derived) must be >= 0")
        selected_geometry.append(
            {
                "kind": cast(Literal["tx_dd", "tx_vertical", "rx_dd"], kind),
                "turn_count_max": n_turns,
                "band_ratio": band_ratio_float,
                "metal_ratio": ratio,
                "trace": trace,
                "gap": gap,
            }
        )
    return selected_geometry


def _parse_group_transforms(group: TOMLTable, field_name: str) -> list[dict[str, float]]:
    raw = group.get(field_name)
    if not isinstance(raw, list):
        raise ValueError(f"{field_name} must be a list")
    transforms: list[dict[str, float]] = []
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"{field_name}[{idx}] must be a table/object")
        required = {"dx", "dy", "dz", "rot_deg"}
        if set(entry.keys()) != required:
            raise ValueError(f"{field_name}[{idx}] must contain only {sorted(required)}")
        parsed: dict[str, float] = {}
        for key in ("dx", "dy", "dz", "rot_deg"):
            value = entry.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{field_name}[{idx}].{key} must be number")
            parsed[key] = float(value)
        transforms.append(parsed)
    return transforms


def _parse_group_count(
    group: TOMLTable,
    kind: str,
    seed: int,
    offset: int,
    attempt: int,
    context: SamplingContext,
    key_prefix: str,
) -> tuple[int, int]:
    if kind == "tx_dd":
        value = _select_count_field(group, "count_mode", seed, offset, attempt, context, f"{key_prefix}.count_mode")
        if value not in (2, 4):
            raise ValueError("tx_dd count_mode must resolve to 2 or 4")
        return value, value
    if kind == "tx_vertical":
        value = _select_count_field(group, "count_range", seed, offset, attempt, context, f"{key_prefix}.count_range")
        if value < 0 or value > 4:
            raise ValueError("tx_vertical count_range must resolve to [0,4]")
        return value, value
    if kind == "rx_dd":
        value = _select_count_field(group, "count_fixed", seed, offset, attempt, context, f"{key_prefix}.count_fixed")
        if value != 2:
            raise ValueError("rx_dd count_fixed must resolve to 2")
        return value, value
    raise ValueError(f"Unsupported coil_groups.kind: {kind}")


def _select_count_field(
    group: TOMLTable,
    field_name: str,
    seed: int,
    offset: int,
    attempt: int,
    context: SamplingContext,
    path_key: str,
) -> int:
    if path_key in context:
        return int(context[path_key])
    if field_name not in group:
        raise ValueError(f"coil_groups.{field_name} is required")
    raw_range = group.get(field_name)
    if not isinstance(raw_range, list) or len(raw_range) != 4:
        raise ValueError(f"coil_groups.{field_name} must be [is_integer, start, end, count]")
    is_integer, start, end, count = raw_range
    if not isinstance(is_integer, bool) or not is_integer:
        raise ValueError(f"coil_groups.{field_name}[0] (is_integer) must be true")
    if isinstance(start, bool) or not isinstance(start, (int, float)):
        raise ValueError(f"coil_groups.{field_name}[1] (start) must be number")
    if isinstance(end, bool) or not isinstance(end, (int, float)):
        raise ValueError(f"coil_groups.{field_name}[2] (end) must be number")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError(f"coil_groups.{field_name}[3] (count) must be int >= 1")
    candidates = _build_candidates(is_integer=True, start=float(start), end=float(end), count=count)
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated from coil_groups.{field_name}")
    selected = int(_sample_candidate(candidates, seed=seed, offset=offset, attempt=attempt))
    context[path_key] = selected
    return selected


def _resolve_coil_groups(
    spec: TOMLTable, seed: int, attempt: int, selected: SelectedParameters, context: SamplingContext
) -> list[ResolvedCoilGroup]:
    raw_groups = spec.get("coil_groups")
    if not isinstance(raw_groups, list) or len(raw_groups) == 0:
        raise ValueError("coil_groups must be a non-empty array of tables")

    resolved: list[ResolvedCoilGroup] = []
    seen_kinds: set[str] = set()
    spacing_by_kind = {
        "tx_dd": selected["tx_dd_pair_spacing_mm"],
        "tx_vertical": selected["tx_vertical_span_mm"],
        "rx_dd": selected["rx_dd_pair_spacing_mm"],
    }
    for idx, raw_group in enumerate(raw_groups):
        if not isinstance(raw_group, dict):
            raise ValueError(f"coil_groups[{idx}] must be a table/object")
        group = raw_group
        raw_kind = group.get("kind")
        if raw_kind not in GROUP_KIND_ORDER:
            raise ValueError("coil_groups.kind must be one of {tx_dd, tx_vertical, rx_dd}")
        kind = str(raw_kind)
        seen_kinds.add(kind)
        transforms = _parse_group_transforms(group, "instance_transforms")
        requested_count, selected_count = _parse_group_count(
            group, kind, seed, GROUP_OFFSET_BASE + idx, attempt, context, f"coil_groups[{idx}]"
        )
        resolved.append(
            {
                "kind": kind,  # type: ignore[typeddict-item]
                "requested_count": requested_count,
                "selected_count": selected_count,
                "spacing_mm": float(spacing_by_kind[kind]),
                "instance_transforms": transforms,
            }
        )

    missing = [kind for kind in GROUP_KIND_ORDER if kind not in seen_kinds]
    if missing:
        raise ValueError(f"Missing required coil groups: {', '.join(missing)}")

    return resolved


def _parse_position(value: TOMLValue, name: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{name} must be [x, y, z]")
    out: list[float] = []
    for idx, entry in enumerate(value):
        if isinstance(entry, bool) or not isinstance(entry, (int, float)):
            raise ValueError(f"{name}[{idx}] must be number")
        out.append(float(entry))
    return (out[0], out[1], out[2])


def _resolve_pcbs(spec: TOMLTable, seed: int, attempt: int, context: SamplingContext) -> list[ResolvedPcbInstance]:
    raw_pcbs = spec.get("pcbs")
    if not isinstance(raw_pcbs, list) or len(raw_pcbs) == 0:
        raise ValueError("pcbs must be a non-empty array of tables")

    resolved: list[ResolvedPcbInstance] = []
    ids: set[str] = set()
    for idx, raw_pcb in enumerate(raw_pcbs):
        if not isinstance(raw_pcb, dict):
            raise ValueError(f"pcbs[{idx}] must be a table/object")
        pcb = raw_pcb
        raw_id = pcb.get("id")
        raw_role = pcb.get("role")
        if not isinstance(raw_id, str) or not raw_id:
            raise ValueError(f"pcbs[{idx}].id must be non-empty string")
        if raw_id in ids:
            raise ValueError(f"Duplicate pcb id: {raw_id}")
        ids.add(raw_id)
        if raw_role not in ("tx", "rx"):
            raise ValueError(f"pcbs[{idx}].role must be 'tx' or 'rx'")
        role = cast(Literal["tx", "rx"], raw_role)

        raw_position = pcb.get("position")
        if raw_position is None:
            raise ValueError(f"pcbs[{idx}].position must be [x, y, z]")
        position = _parse_position(raw_position, f"pcbs[{idx}].position")
        raw_rotation = pcb.get("rotation_deg")
        if isinstance(raw_rotation, bool) or not isinstance(raw_rotation, (int, float)):
            raise ValueError(f"pcbs[{idx}].rotation_deg must be number")
        raw_mounts = pcb.get("mounts")
        if not isinstance(raw_mounts, list) or any(not isinstance(item, str) for item in raw_mounts):
            raise ValueError(f"pcbs[{idx}].mounts must be list[str]")
        mounts = [cast(str, item) for item in raw_mounts]
        raw_present = pcb.get("present")
        if not isinstance(raw_present, list) or len(raw_present) != 4:
            raise ValueError(f"pcbs[{idx}].present must be [is_integer, start, end, count]")
        is_integer, start, end, count = raw_present
        if is_integer is not True:
            raise ValueError(f"pcbs[{idx}].present[0] (is_integer) must be true")
        if any(isinstance(v, bool) for v in (start, end, count)):
            raise ValueError(f"pcbs[{idx}].present values must be numeric")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or not isinstance(count, int):
            raise ValueError(f"pcbs[{idx}].present must be [is_integer, start, end, count]")
        candidates = _build_candidates(True, float(start), float(end), count)
        if not all(int(v) in (0, 1) for v in candidates):
            raise ValueError(f"pcbs[{idx}].present candidates must be 0 or 1")
        present_key = f"pcbs[{idx}].present"
        if present_key in context:
            present = bool(int(context[present_key]))
        else:
            present = bool(int(_sample_candidate(candidates, seed=seed, offset=PCB_OFFSET_BASE + idx, attempt=attempt)))
            context[present_key] = int(present)

        resolved.append(
            {
                "id": raw_id,
                "role": role,
                "position": position,
                "rotation_deg": float(raw_rotation),
                "present": present,
                "mounts": mounts,
            }
        )
    return resolved


def _validate_mounts(coil_groups: list[ResolvedCoilGroup], pcbs: list[ResolvedPcbInstance]) -> None:
    def _max_supported_instances(kind: Literal["tx_dd", "tx_vertical", "rx_dd"]) -> int:
        if kind == "tx_dd":
            return 4
        if kind == "tx_vertical":
            return 4
        return 2

    allowed_instances: dict[Literal["tx_dd", "tx_vertical", "rx_dd"], int] = {group["kind"]: group["selected_count"] for group in coil_groups}
    for pcb in pcbs:
        for mount in pcb["mounts"]:
            if ":" not in mount:
                raise ValueError(f"Invalid mount token '{mount}'; expected '<kind>:<index|*>'")
            kind, selector = mount.split(":", 1)
            if kind not in allowed_instances:
                raise ValueError(f"Mount references unknown coil group kind: {kind}")
            kind_key = cast(Literal["tx_dd", "tx_vertical", "rx_dd"], kind)
            if selector == "*":
                continue
            if not selector.isdigit():
                raise ValueError(f"Mount selector must be '*' or integer index: {mount}")
            idx = int(selector)
            max_instances = max(allowed_instances[kind_key], _max_supported_instances(kind_key))
            if idx < 0 or idx >= max_instances:
                raise ValueError(f"Mount index out of range for {kind}: {mount}")


def _resolve_selected_scalars(spec: TOMLTable, seed: int, attempt: int, context: SamplingContext) -> dict[str, Number]:
    selected: dict[str, Number] = {}
    for path, key, expect_integer in SCALAR_RANGE_SPECS:
        selected[key] = _select_range_value(
            spec, path, expect_integer=expect_integer, seed=seed, offset=SCALAR_OFFSET[path], attempt=attempt, context=context
        )
    return selected


def _resolve_selected_max_scalars(spec: TOMLTable) -> dict[str, Number]:
    selected: dict[str, Number] = {}
    for path, key, expect_integer in SCALAR_RANGE_SPECS:
        selected[key] = _select_range_end_value(spec, path, expect_integer=expect_integer)
    return selected


class PathRef(TypedDict):
    path: str


class ValueRef(TypedDict):
    value: float | str


class FuncRef(TypedDict):
    func: str


ComparableRef: TypeAlias = PathRef | FuncRef
OperandRef: TypeAlias = PathRef | ValueRef | FuncRef
GroupKind: TypeAlias = Literal["tx_dd", "tx_vertical", "rx_dd"]


class ComparisonRule(TypedDict):
    id: str
    kind: Literal["comparison"]
    message: str
    enabled: bool
    lhs: ComparableRef
    op: Literal["<", "<=", ">", ">=", "=="]
    rhs: OperandRef


class RangeRule(TypedDict):
    id: str
    kind: Literal["range"]
    message: str
    enabled: bool
    target: PathRef
    min: ValueRef | None
    max: ValueRef | None
    inclusive_min: bool
    inclusive_max: bool


class AggregateRule(TypedDict):
    id: str
    kind: Literal["aggregate"]
    message: str
    enabled: bool
    agg: Literal["sum_group_selected_count"]
    op: Literal["<", "<=", ">", ">=", "=="]
    rhs: ValueRef


ConstraintRule: TypeAlias = ComparisonRule | RangeRule | AggregateRule


def _parse_path_ref(value: TOMLValue, dotted_path: str) -> PathRef:
    table = require_table(value, dotted_path)
    if set(table.keys()) != {"path"}:
        raise ValueError(f"{dotted_path} must contain only ['path']")
    raw_path = table.get("path")
    if not isinstance(raw_path, str) or raw_path == "":
        raise ValueError(f"{dotted_path}.path must be non-empty string")
    return {"path": raw_path}


def _parse_value_ref(value: TOMLValue, dotted_path: str) -> ValueRef:
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


def _parse_comparable_ref(value: TOMLValue, dotted_path: str) -> ComparableRef:
    table = require_table(value, dotted_path)
    if set(table.keys()) != {"path"} and set(table.keys()) != {"func"}:
        raise ValueError(f"{dotted_path} must have exactly one of ['path'], ['func']")
    if "path" in table:
        return _parse_path_ref(value, dotted_path)
    raw_func = table.get("func")
    if not isinstance(raw_func, str) or raw_func == "":
        raise ValueError(f"{dotted_path}.func must be non-empty string")
    return {"func": raw_func}


def _parse_rhs_ref(value: TOMLValue, dotted_path: str) -> OperandRef:
    table = require_table(value, dotted_path)
    if set(table.keys()) != {"path"} and set(table.keys()) != {"value"} and set(table.keys()) != {"func"}:
        raise ValueError(f"{dotted_path} must have exactly one of ['path'], ['value'], ['func']")
    if "path" in table:
        return _parse_path_ref(value, dotted_path)
    if "value" in table:
        return _parse_value_ref(value, dotted_path)
    raw_func = table.get("func")
    if not isinstance(raw_func, str) or raw_func == "":
        raise ValueError(f"{dotted_path}.func must be non-empty string")
    return {"func": raw_func}


def _parse_rule(raw_rule: TOMLValue, idx: int) -> ConstraintRule:
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
        lhs = _parse_comparable_ref(table["lhs"], f"{dotted}.lhs")
        rhs = _parse_rhs_ref(table["rhs"], f"{dotted}.rhs")
        return {"id": raw_id, "kind": "comparison", "message": raw_message, "enabled": enabled, "lhs": lhs, "op": op_lit, "rhs": rhs}

    if raw_kind == "range":
        allowed = {"id", "kind", "message", "enabled", "target", "min", "max", "inclusive_min", "inclusive_max"}
        if set(table.keys()) != allowed and set(table.keys()) != (allowed - {"enabled"}) and set(table.keys()) != (allowed - {"inclusive_min", "inclusive_max"}) and set(table.keys()) != (allowed - {"enabled", "inclusive_min", "inclusive_max"}):
            raise ValueError(f"{dotted} must contain only {sorted(allowed)}")
        target = _parse_path_ref(table["target"], f"{dotted}.target")
        raw_min = table.get("min")
        raw_max = table.get("max")
        min_ref = _parse_value_ref(raw_min, f"{dotted}.min") if raw_min is not None else None
        max_ref = _parse_value_ref(raw_max, f"{dotted}.max") if raw_max is not None else None
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
        rhs = _parse_value_ref(table["rhs"], f"{dotted}.rhs")
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


def _parse_constraints(spec: TOMLTable) -> list[ConstraintRule]:
    constraints = require_table(spec.get("constraints"), "constraints")
    raw_rules = constraints.get("rules")
    if not isinstance(raw_rules, list):
        raise ValueError("constraints.rules must be a non-empty array of tables")
    if len(raw_rules) == 0:
        raise ValueError("constraints.rules must be a non-empty array of tables")
    parsed_rules: list[ConstraintRule] = []
    ids: set[str] = set()
    for idx, raw_rule in enumerate(raw_rules):
        parsed = _parse_rule(raw_rule, idx)
        rule_id = parsed["id"]
        if rule_id in ids:
            raise ValueError(f"Duplicate constraints.rules id: {rule_id}")
        ids.add(rule_id)
        parsed_rules.append(parsed)
    return parsed_rules


def _compare(lhs: float | str, rhs: float | str, op: Literal["<", "<=", ">", ">=", "=="]) -> bool:
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


def _max_feasible_turns(outer: float, trace: float, gap: float) -> int:
    pitch = trace + gap
    if pitch <= 0:
        return 0
    raw = (outer + (2.0 * gap)) / (2.0 * pitch)
    return max(0, int(math.floor(raw - 1e-12)))


def _parse_group_kind(text: str, *, field_name: str) -> GroupKind:
    if text not in GROUP_KIND_ORDER:
        raise ValueError(f"{field_name} must be one of {list(GROUP_KIND_ORDER)}")
    return cast(GroupKind, text)


def _resolve_selected_numeric_path(
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
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
        kind = _parse_group_kind(parts[1], field_name="selected_group_geometry kind")
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
        kind = _parse_group_kind(parts[1], field_name="selected_coil_groups kind")
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
    value = selected.get(normalized_path)
    if value is None:
        raise ValueError(f"Unknown constraint path: {path}")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Constraint path '{path}' is not numeric")
    return float(value)


def _resolve_selected_comparable_path(
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    path: str,
) -> float | str:
    alias_path: dict[str, str] = {
        "outer_x": "tx_dd_outer_x",
        "outer_y": "tx_dd_outer_y",
    }
    normalized_path = alias_path.get(path, path)
    if path == "tx_region_leftover_z_mm":
        return _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, path)
    if path.startswith("selected_group_geometry.") or path.startswith("selected_coil_groups."):
        return _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, path)
    value = selected.get(normalized_path)
    if value is None:
        raise ValueError(f"Unknown constraint path: {path}")
    if isinstance(value, bool):
        raise ValueError(f"Constraint path '{path}' is not comparable")
    if isinstance(value, (int, float, str)):
        return value
    raise ValueError(f"Constraint path '{path}' is not comparable")


def _parse_func_call(func_text: str) -> tuple[str, list[str]]:
    if not func_text.endswith(")") or "(" not in func_text:
        raise ValueError("rhs.func must be a call expression like name(arg,...)")
    open_idx = func_text.find("(")
    name = func_text[:open_idx].strip()
    body = func_text[open_idx + 1 : -1]
    parts = [part.strip() for part in body.split(",")] if body.strip() else []
    if name == "":
        raise ValueError("rhs.func function name cannot be empty")
    return name, parts


def _resolve_func_ref(
    *,
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    func_text: str,
) -> tuple[float, str | None]:
    name, parts = _parse_func_call(func_text)
    if name == "min":
        if len(parts) != 2 or any(part == "" for part in parts):
            raise ValueError("rhs.func min() must have 2 path arguments")
        return min(
            _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, parts[0]),
            _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, parts[1]),
        ), None
    if name == "sub":
        if len(parts) != 3 or any(part == "" for part in parts):
            raise ValueError("rhs.func sub() must have 3 path arguments")
        return (
            _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, parts[0])
            - _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, parts[1])
            - _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, parts[2])
        ), None
    if name == "active_group":
        if len(parts) != 1 or parts[0] == "":
            raise ValueError("rhs.func active_group() must have 1 group kind argument")
        kind = _parse_group_kind(parts[0], field_name="active_group kind")
        group = coil_groups_by_kind.get(kind)
        if group is None:
            raise ValueError(f"active_group unknown kind: {kind}")
        return (1.0 if int(group["selected_count"]) > 0 else 0.0), None
    if name == "feasible_turns":
        if len(parts) != 4 or any(part == "" for part in parts):
            raise ValueError(
                "rhs.func feasible_turns() must have 4 arguments: "
                "kind, outer_x_path, outer_y_path, outer_cap_y_path"
            )
        kind = _parse_group_kind(parts[0], field_name="feasible_turns kind")
        group_geometry = group_geometry_by_kind.get(kind)
        if group_geometry is None:
            raise ValueError(f"feasible_turns unknown geometry kind: {kind}")
        turns = int(group_geometry["turn_count_max"])
        trace = float(group_geometry["trace"])
        gap = float(group_geometry["gap"])
        outer_x = _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, parts[1])
        outer_y = _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, parts[2])
        cap_y = _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, parts[3])
        available_outer_y = min(outer_y, cap_y)
        feasible_turns = min(
            turns,
            _max_feasible_turns(outer_x, trace, gap),
            _max_feasible_turns(available_outer_y, trace, gap),
        )
        debug = (
            f"func=feasible_turns kind={kind} turns={turns} trace={trace} gap={gap} "
            f"outer_x={outer_x} outer_y={outer_y} cap_y={cap_y} available_outer_y={available_outer_y} "
            f"feasible_turns={feasible_turns}"
        )
        return float(feasible_turns), debug
    raise ValueError(
        "rhs.func supports only "
        "min(path_a,path_b), sub(path_a,path_b,path_c), active_group(kind), "
        "feasible_turns(kind,outer_x_path,outer_y_path,outer_cap_y_path)"
    )


def _resolve_operand_ref(
    *,
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    value_ref: OperandRef | ComparableRef,
) -> tuple[float | str, str | None]:
    if "path" in value_ref:
        path_ref = cast(PathRef, value_ref)
        return (
            _resolve_selected_comparable_path(selected, group_geometry_by_kind, coil_groups_by_kind, path_ref["path"]),
            None,
        )
    if "value" in value_ref:
        scalar_ref = cast(ValueRef, value_ref)
        return scalar_ref["value"], None
    func_ref = cast(FuncRef, value_ref)
    return _resolve_func_ref(
        selected=selected,
        group_geometry_by_kind=group_geometry_by_kind,
        coil_groups_by_kind=coil_groups_by_kind,
        func_text=func_ref["func"],
    )


def _evaluate_constraints(
    rules: list[ConstraintRule],
    selected: SelectedParameters,
    coil_groups: list[ResolvedCoilGroup],
    group_geometry: list[GroupGeometryParams],
) -> None:
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams] = {entry["kind"]: entry for entry in group_geometry}
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup] = {entry["kind"]: entry for entry in coil_groups}
    for rule in rules:
        if not rule["enabled"]:
            continue
        if rule["kind"] == "comparison":
            lhs_value, lhs_debug = _resolve_operand_ref(
                selected=selected,
                group_geometry_by_kind=group_geometry_by_kind,
                coil_groups_by_kind=coil_groups_by_kind,
                value_ref=rule["lhs"],
            )
            rhs_value, rhs_debug = _resolve_operand_ref(
                selected=selected,
                group_geometry_by_kind=group_geometry_by_kind,
                coil_groups_by_kind=coil_groups_by_kind,
                value_ref=rule["rhs"],
            )
            if not _compare(lhs_value, rhs_value, rule["op"]):
                extra_parts = [part for part in (lhs_debug, rhs_debug) if part is not None]
                extra_debug = f", debug=({' | '.join(extra_parts)})" if extra_parts else ""
                raise SelectionConstraintError(
                    f"Constraint {rule['id']} failed: {rule['message']} "
                    f"(lhs={lhs_value}, rhs={rhs_value}{extra_debug})"
                )
            continue
        if rule["kind"] == "range":
            target_value = _resolve_selected_numeric_path(
                selected,
                group_geometry_by_kind,
                coil_groups_by_kind,
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
        if not _compare(aggregate_value, rhs_value, rule["op"]):
            raise SelectionConstraintError(
                f"Constraint {rule['id']} failed: {rule['message']} (lhs={aggregate_value}, rhs={rhs_value})"
            )


def _validate_constraints(
    spec: TOMLTable,
    selected: SelectedParameters,
    coil_groups: list[ResolvedCoilGroup],
    group_geometry: list[GroupGeometryParams],
) -> None:
    rules = _parse_constraints(spec)
    _evaluate_constraints(rules, selected, coil_groups, group_geometry)


def _validate_ratio_and_spacing_constraints(
    *,
    selected: SelectedParameters,
    groups: list[ResolvedCoilGroup],
) -> None:
    eps = 1e-12
    tx_ratio = float(selected["tx_dd_pair_spacing_ratio"])
    rx_ratio = float(selected["rx_dd_pair_spacing_ratio"])
    if tx_ratio < -eps or tx_ratio > (0.12 + eps):
        raise SelectionConstraintError(
            f"ratio out of range (path=coil_spacing.tx_dd_pair_spacing_ratio, ratio={tx_ratio}, "
            "spacing_mm=n/a, lhs=n/a, rhs=[0.0,0.12])"
        )
    if rx_ratio < -eps or rx_ratio > (0.03 + eps):
        raise SelectionConstraintError(
            f"ratio out of range (path=coil_spacing.rx_dd_pair_spacing_ratio, ratio={rx_ratio}, "
            "spacing_mm=n/a, lhs=n/a, rhs=[0.0,0.03])"
        )
    by_kind = {group["kind"]: group for group in groups}
    tx_group = by_kind.get("tx_dd")
    rx_group = by_kind.get("rx_dd")
    if tx_group is not None and int(tx_group["selected_count"]) > 0:
        spacing_mm = float(selected["tx_dd_pair_spacing_mm"])
        lhs = (2.0 * float(selected["tx_dd_outer_y"])) + spacing_mm
        rhs = float(selected["tx_region_outer_h_mm"])
        if lhs > rhs:
            raise SelectionConstraintError(
                "selection hard check failed "
                "(path=coil_spacing.tx_dd_pair_spacing_ratio, "
                f"ratio={tx_ratio}, spacing_mm={spacing_mm}, lhs={lhs}, rhs={rhs})"
            )
    if rx_group is not None and int(rx_group["selected_count"]) > 0:
        spacing_mm = float(selected["rx_dd_pair_spacing_mm"])
        lhs = (2.0 * float(selected["rx_dd_outer_x"])) + spacing_mm
        rhs = float(selected["rx_region_outer_w_mm"])
        if lhs > rhs:
            raise SelectionConstraintError(
                "selection hard check failed "
                "(path=coil_spacing.rx_dd_pair_spacing_ratio, "
                f"ratio={rx_ratio}, spacing_mm={spacing_mm}, lhs={lhs}, rhs={rhs})"
            )


def _resolve_selection(
    spec: TOMLTable, seed: int, attempt: int = 0
) -> tuple[SelectedParameters, SelectedParametersMax, list[ResolvedCoilGroup], list[GroupGeometryParams], list[ResolvedPcbInstance]]:
    _reject_removed_paths(spec)
    context: SamplingContext = {}
    raw = _resolve_selected_scalars(spec, seed, attempt, context)
    raw_max = _resolve_selected_max_scalars(spec)
    dd_mirror_plane = _parse_string_value_at_path(spec, "coil_placement.dd_mirror_plane", allowed={"XZ"})
    rx_plane = _parse_string_value_at_path(spec, "coil_placement.rx_plane", allowed={"YZ"})
    tx_vertical_plane = _parse_string_value_at_path(spec, "coil_placement.tx_vertical_plane", allowed={"ZX"})

    selected: SelectedParameters = {
        "tx_dd_outer_x": float(raw["tx_dd_outer_x"]),
        "tx_dd_outer_y": float(raw["tx_dd_outer_y"]),
        "tx_vertical_outer_x": float(raw["tx_vertical_outer_x"]),
        "tx_vertical_outer_y": float(raw["tx_vertical_outer_y"]),
        "rx_dd_outer_x": float(raw["rx_dd_outer_x"]),
        "rx_dd_outer_y": float(raw["rx_dd_outer_y"]),
        "inner_margin_x": float(raw["inner_margin_x"]),
        "inner_margin_y": float(raw["inner_margin_y"]),
        "tx_dd_pair_spacing_ratio": float(raw["tx_dd_pair_spacing_ratio"]),
        "rx_dd_pair_spacing_ratio": float(raw["rx_dd_pair_spacing_ratio"]),
        "tx_dd_pair_spacing_mm": float(raw["tx_dd_pair_spacing_ratio"]) * float(raw["tx_region_outer_h_mm"]),
        "rx_dd_pair_spacing_mm": float(raw["rx_dd_pair_spacing_ratio"]) * float(raw["rx_region_outer_h_mm"]),
        "tx_vertical_span_mm": float(raw["tx_vertical_span_mm"]),
        "tv_width_mm": float(raw["tv_width_mm"]),
        "tv_height_mm": float(raw["tv_height_mm"]),
        "tv_thickness_mm": float(raw["tv_thickness_mm"]),
        "tv_base_z_mm": float(raw["tv_base_z_mm"]),
        "tx_region_outer_w_mm": float(raw["tx_region_outer_w_mm"]),
        "tx_region_outer_h_mm": float(raw["tx_region_outer_h_mm"]),
        "tx_region_thickness_mm": float(raw["tx_region_thickness_mm"]),
        "tx_region_vertical_z_mm": float(raw["tx_region_vertical_z_mm"]),
        "tx_region_dd_z_mm": float(raw["tx_region_dd_z_mm"]),
        "rx_region_outer_w_mm": float(raw["rx_region_outer_w_mm"]),
        "rx_region_outer_h_mm": float(raw["rx_region_outer_h_mm"]),
        "rx_region_thickness_mm": float(raw["rx_region_thickness_mm"]),
        "wall_thickness_mm": float(raw["wall_thickness_mm"]),
        "wall_size_y_mm": float(raw["wall_size_y_mm"]),
        "wall_size_z_mm": float(raw["wall_size_z_mm"]),
        "floor_thickness_mm": float(raw["floor_thickness_mm"]),
        "floor_size_x_mm": float(raw["floor_size_x_mm"]),
        "floor_size_y_mm": float(raw["floor_size_y_mm"]),
        "shelf_height_mm": float(raw["shelf_height_mm"]),
        "shelf_min_size_x_mm": float(raw["shelf_min_size_x_mm"]),
        "rx_region_bottom_from_tv_mm": float(raw["rx_region_bottom_from_tv_mm"]),
        "tx_dd_top_clearance_mm": float(raw["tx_dd_top_clearance_mm"]),
        "rx_face_clearance_mm": float(raw["rx_face_clearance_mm"]),
        "dd_mirror_plane": cast(Literal["XZ"], dd_mirror_plane),
        "rx_plane": cast(Literal["YZ"], rx_plane),
        "tx_vertical_plane": cast(Literal["ZX"], tx_vertical_plane),
        "via_diameter_mm": float(raw["via_diameter_mm"]),
        "pcb_thickness_mm": float(raw["pcb_thickness_mm"]),
        "cu_thickness_mm": float(raw["cu_thickness_mm"]),
        "via_diameter": float(raw["via_diameter_mm"]),
        "pcb_thickness": float(raw["pcb_thickness_mm"]),
        "cu_thickness": float(raw["cu_thickness_mm"]),
        "fr4_er": float(raw["fr4_er"]),
    }
    selected_max: SelectedParametersMax = {
        "tx_region_outer_w_mm": float(raw_max["tx_region_outer_w_mm"]),
        "tx_region_outer_h_mm": float(raw_max["tx_region_outer_h_mm"]),
        "tx_region_thickness_mm": float(raw_max["tx_region_thickness_mm"]),
        "tx_region_vertical_z_mm": float(raw_max["tx_region_vertical_z_mm"]),
        "tx_region_dd_z_mm": float(raw_max["tx_region_dd_z_mm"]),
        "rx_region_outer_w_mm": float(raw_max["rx_region_outer_w_mm"]),
        "rx_region_outer_h_mm": float(raw_max["rx_region_outer_h_mm"]),
        "rx_region_thickness_mm": float(raw_max["rx_region_thickness_mm"]),
    }
    groups = _resolve_coil_groups(spec, seed, attempt, selected, context)
    group_geometry = _resolve_group_geometry(spec, seed, attempt, context, selected)
    pcbs = _resolve_pcbs(spec, seed, attempt, context)
    _validate_ratio_and_spacing_constraints(selected=selected, groups=groups)
    _validate_mounts(groups, pcbs)
    _validate_constraints(spec, selected, groups, group_geometry)
    return selected, selected_max, groups, group_geometry, pcbs


def resolve_selected_parameters(spec: TOMLTable, seed: int, attempt: int = 0) -> SelectedParameters:
    selected, _, _, _, _ = _resolve_selection(spec, seed, attempt)
    return selected


def resolve_selection(
    spec: TOMLTable, seed: int, attempt: int = 0
) -> tuple[SelectedParameters, SelectedParametersMax, list[ResolvedCoilGroup], list[GroupGeometryParams], list[ResolvedPcbInstance]]:
    return _resolve_selection(spec, seed, attempt)

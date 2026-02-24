from __future__ import annotations

import math
from typing import Literal, Sequence, TypedDict, TypeAlias, cast

from peetsfea.spec.loader import TOMLTable, TOMLValue, require_table
from peetsfea.types.manifest import (
    GroupGeometryParams,
    ResolvedCoilGroup,
    ResolvedPcbInstance,
    ResolvedPcbMount,
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
    ("pcb_spacing.tx_main_1_z_from_tx_main_0_mm", "tx_main_1_z_from_tx_main_0_mm", False),
)

SCALAR_OFFSET: dict[str, int] = {path: idx for idx, (path, _, _) in enumerate(SCALAR_RANGE_SPECS)}
GROUP_KIND_ORDER: tuple[str, ...] = ("tx_dd", "tx_vertical", "rx_dd")
GROUP_OFFSET_BASE = 100
PCB_OFFSET_BASE = 200
GROUP_GEOMETRY_OFFSET_BASE = 300
PCB_SPACING_OFFSET_BASE = 400
ATTEMPT_STRIDE = 1009


class SelectionConstraintError(ValueError):
    pass


REMOVED_PATHS: tuple[str, ...] = (
    "coil_shape.outer_x",
    "coil_shape.outer_y",
    "coil_spacing.tx_dd_pair_spacing_mm",
    "coil_spacing.rx_dd_pair_spacing_mm",
)

DERIVED_RANGE_PATHS: dict[str, str] = {
    "coil_shape.tx_vertical.outer_x": "coil_shape.tx_dd.outer_x",
}


def _reject_removed_paths(spec: TOMLTable) -> None:
    for path in REMOVED_PATHS:
        try:
            _read_path(spec, path)
        except ValueError:
            continue
        raise ValueError(f"Removed path in spec_version 0.2.0: {path}")


def _read_range_definition(root: TOMLTable, dotted_path: str) -> list[TOMLValue]:
    table = require_table(_read_path(root, dotted_path), dotted_path)
    if set(table.keys()) != {"range"}:
        raise ValueError(f"{dotted_path} supports only the 'range' key")
    raw_range = table.get("range")
    if not isinstance(raw_range, list) or len(raw_range) != 4:
        raise ValueError(f"{dotted_path}.range must be [is_integer, start, end, count]")
    return raw_range


def _is_dummy_derived_range(raw_range: list[TOMLValue]) -> bool:
    if len(raw_range) != 4:
        return False
    is_integer, start, end, count = raw_range
    return (
        isinstance(is_integer, bool)
        and is_integer is False
        and isinstance(start, (int, float))
        and not isinstance(start, bool)
        and float(start) == -1.0
        and isinstance(end, (int, float))
        and not isinstance(end, bool)
        and float(end) == -1.0
        and isinstance(count, int)
        and not isinstance(count, bool)
        and count == -1
    )


def _ensure_dummy_derived_range(raw_range: list[TOMLValue], dotted_path: str) -> None:
    if not _is_dummy_derived_range(raw_range):
        raise ValueError(f"{dotted_path}.range for derived path must be exactly [false, -1, -1, -1]")


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
    raw_range = _read_range_definition(root, dotted_path)
    if dotted_path in DERIVED_RANGE_PATHS:
        _ensure_dummy_derived_range(raw_range, dotted_path)
        derived_from_path = DERIVED_RANGE_PATHS[dotted_path]
        selected = _select_range_value(
            root,
            derived_from_path,
            expect_integer=expect_integer,
            seed=seed,
            offset=offset,
            attempt=attempt,
            context=context,
        )
        context[dotted_path] = selected
        return selected
    if _is_dummy_derived_range(raw_range):
        raise ValueError(
            f"{dotted_path}.range uses reserved derived marker [false, -1, -1, -1] "
            "but this path is not declared as derived"
        )
    is_integer, start, end, count = _parse_range_at_path(root, dotted_path, expect_integer=expect_integer)
    candidates = _build_candidates(is_integer=is_integer, start=start, end=end, count=count)
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated from {dotted_path}.range")
    selected = _sample_candidate(candidates, seed=seed, offset=offset, attempt=attempt)
    context[dotted_path] = selected
    return selected


def _select_range_end_value(root: TOMLTable, dotted_path: str, expect_integer: bool) -> Number:
    raw_range = _read_range_definition(root, dotted_path)
    if dotted_path in DERIVED_RANGE_PATHS:
        _ensure_dummy_derived_range(raw_range, dotted_path)
        return _select_range_end_value(root, DERIVED_RANGE_PATHS[dotted_path], expect_integer=expect_integer)
    if _is_dummy_derived_range(raw_range):
        raise ValueError(
            f"{dotted_path}.range uses reserved derived marker [false, -1, -1, -1] "
            "but this path is not declared as derived"
        )
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


def _parse_pcb_mounts(value: TOMLValue, name: str) -> list[ResolvedPcbMount]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    mounts: list[ResolvedPcbMount] = []
    for idx, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise ValueError(f"{name}[{idx}] must be a table/object")
        if set(entry.keys()) - {"kind", "selector_mode", "selector_index"}:
            raise ValueError(f"{name}[{idx}] contains unsupported keys")
        kind_raw = entry.get("kind")
        if kind_raw not in GROUP_KIND_ORDER:
            raise ValueError(f"{name}[{idx}].kind must be one of {list(GROUP_KIND_ORDER)}")
        selector_mode_raw = entry.get("selector_mode")
        if selector_mode_raw not in ("all", "index"):
            raise ValueError(f"{name}[{idx}].selector_mode must be 'all' or 'index'")
        selector_mode = cast(Literal["all", "index"], selector_mode_raw)
        selector_index_raw = entry.get("selector_index")
        selector_index: int | None
        if selector_mode == "all":
            if selector_index_raw is not None:
                raise ValueError(f"{name}[{idx}].selector_index must be omitted when selector_mode='all'")
            selector_index = None
        else:
            if isinstance(selector_index_raw, bool) or not isinstance(selector_index_raw, int):
                raise ValueError(f"{name}[{idx}].selector_index must be int when selector_mode='index'")
            if selector_index_raw < 0:
                raise ValueError(f"{name}[{idx}].selector_index must be >= 0")
            selector_index = selector_index_raw
        mounts.append(
            {
                "kind": cast(Literal["tx_dd", "tx_vertical", "rx_dd"], kind_raw),
                "selector_mode": selector_mode,
                "selector_index": selector_index,
            }
        )
    return mounts


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
        mounts = _parse_pcb_mounts(pcb.get("mounts"), f"pcbs[{idx}].mounts")
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

        raw_z_mode = pcb.get("z_mode")
        if raw_z_mode not in ("absolute", "relative_to_pcb"):
            raise ValueError(f"pcbs[{idx}].z_mode must be 'absolute' or 'relative_to_pcb'")
        z_mode = cast(Literal["absolute", "relative_to_pcb"], raw_z_mode)
        raw_z_relative_base_id = pcb.get("z_relative_base_id")
        raw_z_delta_path = pcb.get("z_delta_path")
        z_relative_base_id: str | None = None
        z_delta_path: str | None = None
        if z_mode == "absolute":
            if raw_z_relative_base_id is not None or raw_z_delta_path is not None:
                raise ValueError(
                    f"pcbs[{idx}] absolute z_mode must not set z_relative_base_id or z_delta_path"
                )
        else:
            if not isinstance(raw_z_relative_base_id, str) or raw_z_relative_base_id == "":
                raise ValueError(f"pcbs[{idx}].z_relative_base_id must be non-empty string when z_mode='relative_to_pcb'")
            if not isinstance(raw_z_delta_path, str) or raw_z_delta_path == "":
                raise ValueError(f"pcbs[{idx}].z_delta_path must be non-empty string when z_mode='relative_to_pcb'")
            z_relative_base_id = raw_z_relative_base_id
            z_delta_path = raw_z_delta_path

        resolved.append(
            {
                "id": raw_id,
                "role": role,
                "position": position,
                "rotation_deg": float(raw_rotation),
                "present": present,
                "z_mode": z_mode,
                "z_relative_base_id": z_relative_base_id,
                "z_delta_path": z_delta_path,
                "mounts": mounts,
            }
        )

    by_id = {pcb["id"]: pcb for pcb in resolved}
    for idx, pcb in enumerate(resolved):
        if pcb["z_mode"] != "relative_to_pcb":
            continue
        base_id = pcb["z_relative_base_id"]
        delta_path = pcb["z_delta_path"]
        assert base_id is not None
        assert delta_path is not None
        base = by_id.get(base_id)
        if base is None:
            raise ValueError(f"pcbs[{idx}].z_relative_base_id references unknown pcb id: {base_id}")
        if base["z_mode"] != "absolute":
            raise ValueError(f"pcbs[{idx}].z_relative_base_id must reference an absolute-z pcb (actual={base_id})")
        delta = float(
            _select_range_value(
                spec,
                delta_path,
                expect_integer=False,
                seed=seed,
                offset=PCB_SPACING_OFFSET_BASE + idx,
                attempt=attempt,
                context=context,
            )
        )
        x, y, _ = pcb["position"]
        pcb["position"] = (x, y, base["position"][2] + delta)
    return resolved


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
        kind = _parse_group_kind(parts[1], field_name="selected_mounts kind")
        field = parts[2]
        mounts = _mounts_for_kind(pcbs, kind)
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


def _resolve_selected_comparable_path(
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
        return _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, path)
    if path.startswith("selected_group_geometry.") or path.startswith("selected_coil_groups."):
        return _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, path)
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
            return _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, path)
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
        return _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, path)
    value = selected.get(normalized_path)
    if value is None:
        raise ValueError(f"Unknown constraint path: {path}")
    if isinstance(value, bool):
        raise ValueError(f"Constraint path '{path}' is not comparable")
    if isinstance(value, (int, float, str)):
        return value
    raise ValueError(f"Constraint path '{path}' is not comparable")


def _split_call_args(body: str) -> list[str]:
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
                raise ValueError("function expression has unmatched ')'")
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
        raise ValueError("function expression has unmatched '('")
    tail = "".join(token).strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_func_call(func_text: str) -> tuple[str, list[str]]:
    text = func_text.strip()
    if not text.endswith(")") or "(" not in text:
        raise ValueError("rhs.func must be a call expression like name(arg,...)")
    open_idx = text.find("(")
    name = text[:open_idx].strip()
    body = text[open_idx + 1 : -1].strip()
    if name == "":
        raise ValueError("rhs.func function name cannot be empty")
    return name, _split_call_args(body) if body else []


def _try_parse_number(text: str) -> float | None:
    value = text.strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _mounts_for_kind(pcbs: list[ResolvedPcbInstance], kind: GroupKind) -> list[ResolvedPcbMount]:
    out: list[ResolvedPcbMount] = []
    for pcb in pcbs:
        out.extend([mount for mount in pcb["mounts"] if mount["kind"] == kind])
    return out


def _max_supported_instances(kind: GroupKind, coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup]) -> int:
    hard_limit: int
    if kind in ("tx_dd", "tx_vertical"):
        hard_limit = 4
    else:
        hard_limit = 2
    group = coil_groups_by_kind.get(kind)
    selected = int(group["selected_count"]) if group is not None else 0
    return max(selected, hard_limit)


def _eval_numeric_expr(
    *,
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    pcbs: list[ResolvedPcbInstance],
    expr: str,
) -> tuple[float, str | None]:
    maybe_number = _try_parse_number(expr)
    if maybe_number is not None:
        return maybe_number, None
    text = expr.strip()
    if text.endswith(")") and "(" in text:
        return _resolve_func_ref(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
            coil_groups_by_kind=coil_groups_by_kind,
            pcbs=pcbs,
            func_text=text,
        )
    return _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, text), None


def _resolve_func_ref(
    *,
    selected: SelectedParameters,
    group_geometry_by_kind: dict[GroupKind, GroupGeometryParams],
    coil_groups_by_kind: dict[GroupKind, ResolvedCoilGroup],
    pcbs: list[ResolvedPcbInstance],
    func_text: str,
) -> tuple[float, str | None]:
    name, parts = _parse_func_call(func_text)
    if name in ("add", "mul", "min", "max"):
        if len(parts) < 2:
            raise ValueError(f"rhs.func {name}() must have at least 2 arguments")
        values = [
            _eval_numeric_expr(
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
        a, _ = _eval_numeric_expr(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
            coil_groups_by_kind=coil_groups_by_kind,
            pcbs=pcbs,
            expr=parts[0],
        )
        b, _ = _eval_numeric_expr(
            selected=selected,
            group_geometry_by_kind=group_geometry_by_kind,
            coil_groups_by_kind=coil_groups_by_kind,
            pcbs=pcbs,
            expr=parts[1],
        )
        c, _ = _eval_numeric_expr(
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
        kind = _parse_group_kind(parts[0], field_name="active_group kind")
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
        kind = _parse_group_kind(parts[0], field_name="feasible_turns kind")
        group_geometry = group_geometry_by_kind.get(kind)
        if group_geometry is None:
            raise ValueError(f"feasible_turns unknown geometry kind: {kind}")
        trace = float(group_geometry["trace"])
        gap = float(group_geometry["gap"])
        turns = int(group_geometry["turn_count_max"])
        outer_x = _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, parts[1])
        outer_y = _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, parts[2])
        cap_y = _resolve_selected_numeric_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, parts[3])
        available_outer_y = min(outer_y, cap_y)
        feasible_turns_max = min(_max_feasible_turns(outer_x, trace, gap), _max_feasible_turns(available_outer_y, trace, gap))
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
        kind = _parse_group_kind(parts[0], field_name="max_supported_mount_index kind")
        return float(_max_supported_instances(kind, coil_groups_by_kind) - 1), None
    if name == "max_mount_selector_index":
        if len(parts) != 1:
            raise ValueError("rhs.func max_mount_selector_index() must have 1 group kind argument")
        kind = _parse_group_kind(parts[0], field_name="max_mount_selector_index kind")
        mounts = _mounts_for_kind(pcbs, kind)
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


def _resolve_operand_ref(
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
            _resolve_selected_comparable_path(selected, group_geometry_by_kind, coil_groups_by_kind, pcbs, path_ref["path"]),
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
        pcbs=pcbs,
        func_text=func_ref["func"],
    )


def _evaluate_constraints(
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
            lhs_value, lhs_debug = _resolve_operand_ref(
                selected=selected,
                group_geometry_by_kind=group_geometry_by_kind,
                coil_groups_by_kind=coil_groups_by_kind,
                pcbs=pcbs,
                value_ref=rule["lhs"],
            )
            rhs_value, rhs_debug = _resolve_operand_ref(
                selected=selected,
                group_geometry_by_kind=group_geometry_by_kind,
                coil_groups_by_kind=coil_groups_by_kind,
                pcbs=pcbs,
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
        if not _compare(aggregate_value, rhs_value, rule["op"]):
            raise SelectionConstraintError(
                f"Constraint {rule['id']} failed: {rule['message']} (lhs={aggregate_value}, rhs={rhs_value})"
            )


def _validate_constraints(
    spec: TOMLTable,
    selected: SelectedParameters,
    coil_groups: list[ResolvedCoilGroup],
    group_geometry: list[GroupGeometryParams],
    pcbs: list[ResolvedPcbInstance],
) -> None:
    rules = _parse_constraints(spec)
    _evaluate_constraints(rules, selected, coil_groups, group_geometry, pcbs)


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
        "tx_main_1_z_from_tx_main_0_mm": float(raw["tx_main_1_z_from_tx_main_0_mm"]),
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
    _validate_constraints(spec, selected, groups, group_geometry, pcbs)
    return selected, selected_max, groups, group_geometry, pcbs


def resolve_selected_parameters(spec: TOMLTable, seed: int, attempt: int = 0) -> SelectedParameters:
    selected, _, _, _, _ = _resolve_selection(spec, seed, attempt)
    return selected


def resolve_selection(
    spec: TOMLTable, seed: int, attempt: int = 0
) -> tuple[SelectedParameters, SelectedParametersMax, list[ResolvedCoilGroup], list[GroupGeometryParams], list[ResolvedPcbInstance]]:
    return _resolve_selection(spec, seed, attempt)

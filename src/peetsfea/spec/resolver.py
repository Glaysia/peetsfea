from __future__ import annotations

import math
from typing import Literal, Sequence, TypeAlias, cast

from peetsfea.spec.loader import TOMLTable, TOMLValue, require_table
from peetsfea.types.manifest import ResolvedCoilGroup, ResolvedPcbInstance, SelectedParameters, SelectedParametersMax


Number: TypeAlias = int | float

SCALAR_RANGE_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("coil_shape.outer_x", "outer_x", False),
    ("coil_shape.outer_y", "outer_y", False),
    ("coil_shape.turn_count_max", "turn_count_max", True),
    ("coil_shape.inner_margin_x", "inner_margin_x", False),
    ("coil_shape.inner_margin_y", "inner_margin_y", False),
    ("coil_spacing.tx_dd_pair_spacing_mm", "tx_dd_pair_spacing_mm", False),
    ("coil_spacing.rx_dd_pair_spacing_mm", "rx_dd_pair_spacing_mm", False),
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
)

SCALAR_OFFSET: dict[str, int] = {path: idx for idx, (path, _, _) in enumerate(SCALAR_RANGE_SPECS)}
GROUP_KIND_ORDER: tuple[str, ...] = ("tx_dd", "tx_vertical", "rx_dd")
GROUP_OFFSET_BASE = 100
PCB_OFFSET_BASE = 200
PROFILE_OFFSET = 300

FIXED_DEFAULTS: dict[str, float] = {
    "pcb_thickness": 1.6,
    "cu_thickness": 0.035,
    "fr4_er": 4.4,
    "via_diameter": 0.5,
}


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


def _select_range_value(root: TOMLTable, dotted_path: str, expect_integer: bool, seed: int, offset: int) -> Number:
    is_integer, start, end, count = _parse_range_at_path(root, dotted_path, expect_integer=expect_integer)
    candidates = _build_candidates(is_integer=is_integer, start=start, end=end, count=count)
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated from {dotted_path}.range")
    return candidates[(seed + offset) % len(candidates)]


def _select_range_end_value(root: TOMLTable, dotted_path: str, expect_integer: bool) -> Number:
    is_integer, _, end, _ = _parse_range_at_path(root, dotted_path, expect_integer=expect_integer)
    if is_integer:
        return int(math.floor(end + 0.5))
    return float(end)


def _parse_profile_table(raw_profile: TOMLValue, dotted_path: str) -> tuple[float, float, float, float]:
    profile = require_table(raw_profile, dotted_path)
    required = {"mode", "base", "outer_bias", "inner_bias", "clamp_min"}
    if set(profile.keys()) != required:
        raise ValueError(f"{dotted_path} must contain only {sorted(required)}")

    mode = profile.get("mode")
    if mode != "biased_linear":
        raise ValueError(f"{dotted_path}.mode must be 'biased_linear'")

    values: list[float] = []
    for key in ("base", "outer_bias", "inner_bias", "clamp_min"):
        raw = profile.get(key)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"{dotted_path}.{key} must be number")
        values.append(float(raw))
    if values[3] <= 0:
        raise ValueError(f"{dotted_path}.clamp_min must be > 0")
    return values[0], values[1], values[2], values[3]


def _parse_profile_entry(entry: TOMLValue, idx: int) -> tuple[str, tuple[float, float, float, float], tuple[float, float, float, float]]:
    dotted_root = f"trace_gap_profile.profiles[{idx}]"
    profile_entry = require_table(entry, dotted_root)
    required = {"id", "trace", "gap"}
    if set(profile_entry.keys()) != required:
        raise ValueError(f"{dotted_root} must contain only {sorted(required)}")

    raw_id = profile_entry.get("id")
    if not isinstance(raw_id, str) or raw_id == "":
        raise ValueError(f"{dotted_root}.id must be non-empty string")

    trace_values = _parse_profile_table(profile_entry.get("trace"), f"{dotted_root}.trace") # type: ignore
    gap_values = _parse_profile_table(profile_entry.get("gap"), f"{dotted_root}.gap") # type: ignore
    return raw_id, trace_values, gap_values


def _resolve_profile_selection(spec: TOMLTable, seed: int) -> tuple[str, float, float, float, float, float, float, float, float]:
    trace_gap_profile = require_table(spec.get("trace_gap_profile"), "trace_gap_profile")
    raw_profiles = trace_gap_profile.get("profiles")
    if not isinstance(raw_profiles, list):
        raise ValueError("trace_gap_profile.profiles must be a non-empty array of tables")
    if len(raw_profiles) == 0:
        raise ValueError("trace_gap_profile.profiles must contain at least one profile")

    parsed_profiles: list[tuple[str, tuple[float, float, float, float], tuple[float, float, float, float]]] = []
    seen_ids: set[str] = set()
    for idx, raw_entry in enumerate(raw_profiles):
        profile_id, trace_values, gap_values = _parse_profile_entry(raw_entry, idx)
        if profile_id in seen_ids:
            raise ValueError(f"Duplicate trace_gap_profile.profiles id: {profile_id}")
        seen_ids.add(profile_id)
        parsed_profiles.append((profile_id, trace_values, gap_values))

    selected_idx = (seed + PROFILE_OFFSET) % len(parsed_profiles)
    selected_id, selected_trace, selected_gap = parsed_profiles[selected_idx]
    return (
        selected_id,
        selected_trace[0],
        selected_trace[1],
        selected_trace[2],
        selected_trace[3],
        selected_gap[0],
        selected_gap[1],
        selected_gap[2],
        selected_gap[3],
    )


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


def _parse_group_count(group: TOMLTable, kind: str, seed: int, offset: int) -> tuple[int, int]:
    if kind == "tx_dd":
        value = _select_count_field(group, "count_mode", seed, offset)
        if value not in (2, 4):
            raise ValueError("tx_dd count_mode must resolve to 2 or 4")
        return value, value
    if kind == "tx_vertical":
        value = _select_count_field(group, "count_range", seed, offset)
        if value < 0 or value > 4:
            raise ValueError("tx_vertical count_range must resolve to [0,4]")
        return value, value
    if kind == "rx_dd":
        value = _select_count_field(group, "count_fixed", seed, offset)
        if value != 2:
            raise ValueError("rx_dd count_fixed must resolve to 2")
        return value, value
    raise ValueError(f"Unsupported coil_groups.kind: {kind}")


def _select_count_field(group: TOMLTable, field_name: str, seed: int, offset: int) -> int:
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
    return int(candidates[(seed + offset) % len(candidates)])


def _resolve_coil_groups(spec: TOMLTable, seed: int, selected: SelectedParameters) -> list[ResolvedCoilGroup]:
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
        requested_count, selected_count = _parse_group_count(group, kind, seed, GROUP_OFFSET_BASE + idx)
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

    total = sum(group["selected_count"] for group in resolved)
    if total > 10:
        raise ValueError("Total selected coil count must be <= 10")
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


def _resolve_pcbs(spec: TOMLTable, seed: int) -> list[ResolvedPcbInstance]:
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
        present = bool(int(candidates[(seed + PCB_OFFSET_BASE + idx) % len(candidates)]))

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
            if idx < 0 or idx >= allowed_instances[kind_key]:
                raise ValueError(f"Mount index out of range for {kind}: {mount}")


def _resolve_selected_scalars(spec: TOMLTable, seed: int) -> dict[str, Number]:
    selected: dict[str, Number] = {}
    for path, key, expect_integer in SCALAR_RANGE_SPECS:
        selected[key] = _select_range_value(spec, path, expect_integer=expect_integer, seed=seed, offset=SCALAR_OFFSET[path])
    return selected


def _resolve_selected_max_scalars(spec: TOMLTable) -> dict[str, Number]:
    selected: dict[str, Number] = {}
    for path, key, expect_integer in SCALAR_RANGE_SPECS:
        selected[key] = _select_range_end_value(spec, path, expect_integer=expect_integer)
    return selected


def _validate_constraints(selected: SelectedParameters, coil_groups: list[ResolvedCoilGroup]) -> None:
    if selected["outer_x"] <= 0 or selected["outer_y"] <= 0:
        raise ValueError("outer_x and outer_y must be > 0")
    if selected["turn_count_max"] < 1:
        raise ValueError("turn_count_max must be >= 1")
    if selected["inner_margin_x"] < 0 or selected["inner_margin_y"] < 0:
        raise ValueError("inner_margin_x/inner_margin_y must be >= 0")
    if selected["tx_dd_pair_spacing_mm"] <= 0 or selected["rx_dd_pair_spacing_mm"] <= 0:
        raise ValueError("tx_dd_pair_spacing_mm and rx_dd_pair_spacing_mm must be > 0")
    if selected["tx_vertical_span_mm"] < 0 or selected["tx_vertical_span_mm"] > 15:
        raise ValueError("tx_vertical_span_mm must be in [0,15]")
    if selected["trace_profile_clamp_min"] <= 0 or selected["gap_profile_clamp_min"] <= 0:
        raise ValueError("profile clamp_min must be > 0")
    if selected["tx_region_outer_w_mm"] <= 0 or selected["tx_region_outer_h_mm"] <= 0:
        raise ValueError("tx.region outer dimensions must be > 0")
    if selected["tx_region_thickness_mm"] <= 0:
        raise ValueError("tx.region.thickness_mm must be > 0")
    if selected["tx_region_vertical_z_mm"] <= 0 or selected["tx_region_dd_z_mm"] <= 0:
        raise ValueError("tx.region.z_parts.vertical_z_mm and tx.region.z_parts.dd_z_mm must be > 0")
    leftover_z = selected["tx_region_thickness_mm"] - selected["tx_region_vertical_z_mm"] - selected["tx_region_dd_z_mm"]
    if leftover_z < 0:
        raise ValueError("tx.region.leftover_z_mm computed negative; reduce vertical_z/dd_z or increase tx.region.thickness_mm")

    if selected["outer"] >= min(selected["tx_region_outer_w_mm"], selected["tx_region_outer_h_mm"]):
        raise ValueError("TX coil outer must be < min(tx.region.outer_w_mm, tx.region.outer_h_mm)")

    total = sum(group["selected_count"] for group in coil_groups)
    if total > 10:
        raise ValueError("Total selected coil count must be <= 10")


def _resolve_selection(spec: TOMLTable, seed: int) -> tuple[SelectedParameters, SelectedParametersMax, list[ResolvedCoilGroup], list[ResolvedPcbInstance]]:
    (
        profile_id,
        trace_base,
        trace_outer_bias,
        trace_inner_bias,
        trace_clamp_min,
        gap_base,
        gap_outer_bias,
        gap_inner_bias,
        gap_clamp_min,
    ) = _resolve_profile_selection(spec, seed)
    raw = _resolve_selected_scalars(spec, seed)
    raw_max = _resolve_selected_max_scalars(spec)

    # Current geometry path is still square-spiral MVP. Keep compatibility fields deterministic.
    derived_outer = min(float(raw["outer_x"]), float(raw["outer_y"]))
    selected: SelectedParameters = {
        "outer_x": float(raw["outer_x"]),
        "outer_y": float(raw["outer_y"]),
        "turn_count_max": int(raw["turn_count_max"]),
        "inner_margin_x": float(raw["inner_margin_x"]),
        "inner_margin_y": float(raw["inner_margin_y"]),
        "tx_dd_pair_spacing_mm": float(raw["tx_dd_pair_spacing_mm"]),
        "rx_dd_pair_spacing_mm": float(raw["rx_dd_pair_spacing_mm"]),
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
        # RX actual thickness is forced to max thickness for deterministic zone alignment.
        "rx_region_thickness_mm": float(raw_max["rx_region_thickness_mm"]),
        "wall_thickness_mm": float(raw["wall_thickness_mm"]),
        "wall_size_y_mm": float(raw["wall_size_y_mm"]),
        "wall_size_z_mm": float(raw["wall_size_z_mm"]),
        "floor_thickness_mm": float(raw["floor_thickness_mm"]),
        "floor_size_x_mm": float(raw["floor_size_x_mm"]),
        "floor_size_y_mm": float(raw["floor_size_y_mm"]),
        "profile_id": profile_id,
        "trace_profile_base": trace_base,
        "trace_profile_outer_bias": trace_outer_bias,
        "trace_profile_inner_bias": trace_inner_bias,
        "trace_profile_clamp_min": trace_clamp_min,
        "gap_profile_base": gap_base,
        "gap_profile_outer_bias": gap_outer_bias,
        "gap_profile_inner_bias": gap_inner_bias,
        "gap_profile_clamp_min": gap_clamp_min,
        "turns": int(raw["turn_count_max"]),
        "outer": derived_outer,
        "trace": trace_base,
        "gap": gap_base,
        "via_diameter": FIXED_DEFAULTS["via_diameter"],
        "pcb_thickness": FIXED_DEFAULTS["pcb_thickness"],
        "cu_thickness": FIXED_DEFAULTS["cu_thickness"],
        "fr4_er": FIXED_DEFAULTS["fr4_er"],
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
    groups = _resolve_coil_groups(spec, seed, selected)
    pcbs = _resolve_pcbs(spec, seed)
    _validate_mounts(groups, pcbs)
    _validate_constraints(selected, groups)
    return selected, selected_max, groups, pcbs


def resolve_selected_parameters(spec: TOMLTable, seed: int) -> SelectedParameters:
    selected, _, _, _ = _resolve_selection(spec, seed)
    return selected


def resolve_selection(spec: TOMLTable, seed: int) -> tuple[SelectedParameters, SelectedParametersMax, list[ResolvedCoilGroup], list[ResolvedPcbInstance]]:
    return _resolve_selection(spec, seed)

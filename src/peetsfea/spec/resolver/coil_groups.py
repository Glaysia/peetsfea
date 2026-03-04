from __future__ import annotations

from peetsfea.spec.loader import TOMLTable
from peetsfea.types.manifest import ResolvedCoilGroup, SelectedParameters

from .constants import GROUP_KIND_ORDER, GROUP_OFFSET_BASE
from .sampling import build_candidates, sample_candidate
from .types import SamplingContext


def parse_group_transforms(group: TOMLTable, field_name: str) -> list[dict[str, float]]:
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


def select_count_field(
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
    candidates = build_candidates(is_integer=True, start=float(start), end=float(end), count=count)
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated from coil_groups.{field_name}")
    selected = int(sample_candidate(candidates, seed=seed, offset=offset, attempt=attempt))
    context[path_key] = selected
    return selected


def parse_group_count(
    group: TOMLTable,
    kind: str,
    seed: int,
    offset: int,
    attempt: int,
    context: SamplingContext,
    key_prefix: str,
) -> tuple[int, int]:
    if kind == "tx_dd":
        value = select_count_field(group, "count_mode", seed, offset, attempt, context, f"{key_prefix}.count_mode")
        if value not in (2, 4):
            raise ValueError("tx_dd count_mode must resolve to 2 or 4")
        return value, value
    if kind == "tx_vertical":
        value = select_count_field(group, "count_range", seed, offset, attempt, context, f"{key_prefix}.count_range")
        if value < 1 or value > 6:
            raise ValueError("tx_vertical count_range must resolve to [1,6]")
        return value, value
    if kind == "rx_dd":
        value = select_count_field(group, "count_fixed", seed, offset, attempt, context, f"{key_prefix}.count_fixed")
        if value != 2:
            raise ValueError("rx_dd count_fixed must resolve to 2")
        return value, value
    raise ValueError(f"Unsupported coil_groups.kind: {kind}")


def resolve_coil_groups(
    spec: TOMLTable, seed: int, attempt: int, selected: SelectedParameters, context: SamplingContext
) -> list[ResolvedCoilGroup]:
    raw_groups = spec.get("coil_groups")
    if not isinstance(raw_groups, list) or len(raw_groups) == 0:
        raise ValueError("coil_groups must be a non-empty array of tables")

    resolved: list[ResolvedCoilGroup] = []
    seen_kinds: set[str] = set()
    for idx, raw_group in enumerate(raw_groups):
        if not isinstance(raw_group, dict):
            raise ValueError(f"coil_groups[{idx}] must be a table/object")
        group = raw_group
        raw_kind = group.get("kind")
        if raw_kind not in GROUP_KIND_ORDER:
            raise ValueError("coil_groups.kind must be one of {tx_dd, tx_vertical, rx_dd}")
        kind = str(raw_kind)
        seen_kinds.add(kind)
        transforms = parse_group_transforms(group, "instance_transforms")
        requested_count, selected_count = parse_group_count(
            group, kind, seed, GROUP_OFFSET_BASE + idx, attempt, context, f"coil_groups[{idx}]"
        )
        if kind == "tx_vertical":
            spacing_mm = float(selected["tx_vertical_center_gap_mm"]) * float(max(0, selected_count - 1))
            selected["tx_vertical_span_mm"] = spacing_mm
        elif kind == "tx_dd":
            spacing_mm = float(selected["tx_dd_pair_spacing_mm"])
        else:
            spacing_mm = float(selected["rx_dd_pair_spacing_mm"])
        resolved.append(
            {
                "kind": kind,  # type: ignore[typeddict-item]
                "requested_count": requested_count,
                "selected_count": selected_count,
                "spacing_mm": spacing_mm,
                "instance_transforms": transforms,
            }
        )

    missing = [kind for kind in GROUP_KIND_ORDER if kind not in seen_kinds]
    if missing:
        raise ValueError(f"Missing required coil groups: {', '.join(missing)}")

    return resolved

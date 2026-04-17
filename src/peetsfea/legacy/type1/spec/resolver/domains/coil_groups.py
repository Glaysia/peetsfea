from __future__ import annotations

from typing import Literal, cast

from peetsfea.spec.loader import TOMLTable
from peetsfea.types.manifest import ResolvedCoilGroup, SelectedParameters

from ..constants import GROUP_KIND_ORDER, GROUP_OFFSET_BASE
from ..sampling import select_range_value
from ..types import SamplingContext


_ALLOWED_KEYS_BY_KIND: dict[str, set[str]] = {
    "tx_dd": {"kind", "stacked_mode", "instance_transforms"},
    "tx_vertical": {"kind", "count_range", "instance_transforms"},
    "rx_dd": {"kind", "count_fixed", "instance_transforms"},
}


def parse_group_transforms(group: TOMLTable, field_name: str) -> list[dict[str, float]]:
    assert field_name in group, f"{field_name} must exist"
    raw = group[field_name]
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
            value = entry[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{field_name}[{idx}].{key} must be number")
            parsed[key] = float(value)
        transforms.append(parsed)
    return transforms


def select_count_field(
    spec: TOMLTable,
    dotted_path: str,
    seed: int,
    offset: int,
    attempt: int,
    context: SamplingContext,
) -> int:
    return int(
        select_range_value(
            spec,
            dotted_path,
            expect_integer=True,
            seed=seed,
            offset=offset,
            attempt=attempt,
            context=context,
        )
    )


def parse_group_count(
    spec: TOMLTable,
    kind: str,
    seed: int,
    offset: int,
    attempt: int,
    context: SamplingContext,
    selected: SelectedParameters,
    key_prefix: str,
) -> tuple[int, int, int]:
    if kind == "tx_dd":
        value = select_count_field(spec, f"{key_prefix}.stacked_mode", seed, offset, attempt, context)
        if value not in (0, 1):
            raise ValueError("tx_dd stacked_mode must resolve to 0 or 1")
        if value == 0:
            return 2, 2, 1
        return 4, 4, 2
    if kind == "tx_vertical":
        # Keep the canonical sampling owner recorded even when mode 0 disables
        # vertical coils, so downstream uniform-seed logic still sees
        # `coil_groups[1].count_range` in the sampling ledger.
        value = select_count_field(spec, f"{key_prefix}.count_range", seed, offset, attempt, context)
        if int(selected["tx_vertical_orientation_mode"]) == 0:
            return 0, 0, 1
        if value < 1 or value > 6:
            raise ValueError("tx_vertical count_range must resolve to [1,6]")
        return value, value, 1
    if kind == "rx_dd":
        value = select_count_field(spec, f"{key_prefix}.count_fixed", seed, offset, attempt, context)
        if value != 2:
            raise ValueError("rx_dd count_fixed must resolve to 2")
        return value, value, 1
    raise ValueError(f"Unsupported coil_groups.kind: {kind}")


def resolve_coil_groups(
    spec: TOMLTable, seed: int, attempt: int, selected: SelectedParameters, context: SamplingContext
) -> list[ResolvedCoilGroup]:
    assert "coil_groups" in spec, "spec must contain coil_groups"
    raw_groups = spec["coil_groups"]
    if not isinstance(raw_groups, list) or len(raw_groups) == 0:
        raise ValueError("coil_groups must be a non-empty array of tables")

    resolved: list[ResolvedCoilGroup] = []
    seen_kinds: set[str] = set()
    for idx, raw_group in enumerate(raw_groups):
        if not isinstance(raw_group, dict):
            raise ValueError(f"coil_groups[{idx}] must be a table/object")
        group = raw_group
        assert "kind" in group, f"coil_groups[{idx}] must contain kind"
        raw_kind = group["kind"]
        if raw_kind not in GROUP_KIND_ORDER:
            raise ValueError("coil_groups.kind must be one of {tx_dd, tx_vertical, rx_dd}")
        kind = str(raw_kind)
        unsupported_keys = set(group.keys()) - _ALLOWED_KEYS_BY_KIND[kind]
        if unsupported_keys:
            raise ValueError(f"coil_groups[{idx}] contains unsupported keys: {sorted(unsupported_keys)}")
        seen_kinds.add(kind)
        transforms = parse_group_transforms(group, "instance_transforms")
        requested_count, selected_count, layer_count = parse_group_count(
            spec, kind, seed, GROUP_OFFSET_BASE + idx, attempt, context, selected, f"coil_groups[{idx}]"
        )
        if kind == "tx_vertical":
            spacing_mm = float(selected["tx_vertical_center_gap_mm"]) * float(max(0, selected_count - 1))
            selected["tx_vertical_span_mm"] = spacing_mm
        elif kind == "tx_dd":
            spacing_mm = float(selected["tx_dd_pair_spacing_mm"])
        else:
            spacing_mm = float(selected["rx_dd_pair_spacing_mm"])
        if kind == "tx_dd":
            resolved.append(
                {
                    "kind": "tx_dd",
                    "layer_count": cast(Literal[1, 2], layer_count),
                    "spacing_mm": spacing_mm,
                    "instance_transforms": transforms,
                }
            )
        elif kind == "tx_vertical":
            resolved.append(
                {
                    "kind": "tx_vertical",
                    "requested_count": requested_count,
                    "selected_count": selected_count,
                    "layer_count": 1,
                    "spacing_mm": spacing_mm,
                    "instance_transforms": transforms,
                }
            )
        else:
            resolved.append(
                {
                    "kind": "rx_dd",
                    "requested_count": 2,
                    "selected_count": 2,
                    "layer_count": 1,
                    "spacing_mm": spacing_mm,
                    "instance_transforms": transforms,
                }
            )

    missing = [kind for kind in GROUP_KIND_ORDER if kind not in seen_kinds]
    if missing:
        raise ValueError(f"Missing required coil groups: {', '.join(missing)}")

    return resolved

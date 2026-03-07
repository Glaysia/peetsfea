from __future__ import annotations

import math
import re
from collections.abc import Iterator, MutableMapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal, cast

from peetsfea.spec.loader import TOMLTable, TOMLValue

from .constants import (
    ATTEMPT_STRIDE,
    DERIVED_RANGE_PATHS,
    FIXED_PCB_RULES,
    GROUP_KIND_ORDER,
    SCALAR_RANGE_SPECS,
)
from .path_access import read_range_definition
from .types import Number, SamplingContext

SamplerKind = Literal["range", "inline_range"]
SamplingValueType = Literal["int", "float"]

_INLINE_RANGE_FIELDS: Final[frozenset[str]] = frozenset({"count_mode", "count_range", "count_fixed", "present"})
_INDEXED_SEGMENT_RE: Final[re.Pattern[str]] = re.compile(r"^(?P<key>[A-Za-z0-9_-]+)(?:\[(?P<index>\d+)\])?$")
_GROUP_COUNT_FIELD_BY_KIND: Final[dict[str, str]] = {
    "tx_dd": "count_mode",
    "tx_vertical": "count_range",
    "rx_dd": "count_fixed",
}
_GROUP_GEOMETRY_RANGE_SPECS: Final[tuple[tuple[str, bool], ...]] = (
    ("coil_groups_params.tx_dd.turn_count_max", True),
    ("coil_groups_params.tx_dd.band_ratio", False),
    ("coil_groups_params.tx_dd.metal_ratio", False),
    ("coil_groups_params.tx_vertical.turn_count_max", True),
    ("coil_groups_params.tx_vertical.band_ratio", False),
    ("coil_groups_params.tx_vertical.metal_ratio", False),
    ("coil_groups_params.rx_dd.turn_count_max", True),
    ("coil_groups_params.rx_dd.band_ratio", False),
    ("coil_groups_params.rx_dd.metal_ratio", False),
)


@dataclass(frozen=True)
class SamplingRegistryEntry:
    canonical_key: str
    owner_path: str
    sampler_kind: SamplerKind
    value_type: SamplingValueType
    export_to_dataset: bool
    replay_affects_design: bool
    fixed_value: Number | None = None


@dataclass(frozen=True)
class ScannedSamplingField:
    path: str
    sampler_kind: SamplerKind
    raw_range: list[TOMLValue]


class SamplingRegistry:
    def __init__(
        self,
        *,
        entries: Sequence[SamplingRegistryEntry],
        aliases: dict[str, str] | None = None,
    ) -> None:
        self._entries_by_owner: dict[str, SamplingRegistryEntry] = {}
        self._entries_by_canonical: dict[str, SamplingRegistryEntry] = {}
        for entry in entries:
            if entry.owner_path in self._entries_by_owner:
                raise ValueError(f"Duplicate sampling owner path: {entry.owner_path}")
            if entry.canonical_key in self._entries_by_canonical:
                raise ValueError(f"Duplicate sampling canonical key: {entry.canonical_key}")
            self._entries_by_owner[entry.owner_path] = entry
            self._entries_by_canonical[entry.canonical_key] = entry

        alias_map = aliases or {}
        for alias_path, owner_path in alias_map.items():
            if alias_path in self._entries_by_owner:
                raise ValueError(f"Derived alias cannot also be an owner path: {alias_path}")
            if owner_path not in self._entries_by_owner:
                raise ValueError(f"Derived alias owner is not registered: {owner_path}")
        self._alias_to_owner = dict(alias_map)

    def owner_paths(self) -> tuple[str, ...]:
        return tuple(self._entries_by_owner.keys())

    def alias_paths(self) -> tuple[str, ...]:
        return tuple(self._alias_to_owner.keys())

    def known_paths(self) -> set[str]:
        return set(self._entries_by_owner.keys()) | set(self._alias_to_owner.keys())

    def entry_for_owner(self, owner_path: str) -> SamplingRegistryEntry | None:
        return self._entries_by_owner.get(owner_path)

    def entry_for_path(self, path: str) -> SamplingRegistryEntry | None:
        owner_path = self.resolve_owner_path(path)
        return self._entries_by_owner.get(owner_path)

    def resolve_owner_path(self, path: str) -> str:
        return self._alias_to_owner.get(path, path)

    def is_alias_path(self, path: str) -> bool:
        return path in self._alias_to_owner


class SamplingLedger(MutableMapping[str, Number]):
    def __init__(self, registry: SamplingRegistry) -> None:
        self._registry = registry
        self._values_by_canonical: dict[str, Number] = {}
        self._path_to_canonical: dict[str, str] = {}

    @property
    def registry(self) -> SamplingRegistry:
        return self._registry

    def record(self, path: str, value: Number) -> Number:
        entry = self._registry.entry_for_path(path)
        if entry is None:
            raise KeyError(path)
        self._values_by_canonical[entry.canonical_key] = value
        self._path_to_canonical[path] = entry.canonical_key
        return value

    def has_canonical_value(self, path: str) -> bool:
        entry = self._registry.entry_for_path(path)
        return entry is not None and entry.canonical_key in self._values_by_canonical

    def canonical_value(self, path: str) -> Number:
        entry = self._registry.entry_for_path(path)
        if entry is None or entry.canonical_key not in self._values_by_canonical:
            raise KeyError(path)
        return self._values_by_canonical[entry.canonical_key]

    def as_dict(self) -> dict[str, Number]:
        return {path: self[path] for path in self._path_to_canonical.keys()}

    def recorded_paths(self) -> tuple[str, ...]:
        return tuple(self._path_to_canonical.keys())

    def sorted_recorded_paths(self) -> tuple[str, ...]:
        return tuple(sorted(self._path_to_canonical.keys()))

    def as_float_vector(self, paths: Sequence[str]) -> tuple[float, ...]:
        return tuple(float(self[path]) for path in paths)

    def __getitem__(self, key: str) -> Number:
        canonical_key = self._path_to_canonical[key]
        return self._values_by_canonical[canonical_key]

    def __setitem__(self, key: str, value: Number) -> None:
        self.record(key, value)

    def __delitem__(self, key: str) -> None:
        canonical_key = self._path_to_canonical.pop(key)
        if canonical_key not in self._path_to_canonical.values():
            del self._values_by_canonical[canonical_key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._path_to_canonical.keys())

    def __len__(self) -> int:
        return len(self._path_to_canonical)


def is_dummy_derived_range(raw_range: list[TOMLValue]) -> bool:
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


def ensure_dummy_derived_range(raw_range: list[TOMLValue], dotted_path: str) -> None:
    if not is_dummy_derived_range(raw_range):
        raise ValueError(f"{dotted_path}.range for derived path must be exactly [false, -1, -1, -1]")


def _read_path_with_indexes(root: TOMLTable, dotted_path: str) -> TOMLValue:
    current: TOMLValue = root
    for segment in dotted_path.split("."):
        match = _INDEXED_SEGMENT_RE.match(segment)
        if match is None:
            raise ValueError(f"Unsupported indexed path: {dotted_path}")
        key = match.group("key")
        raw_index = match.group("index")
        if not isinstance(current, dict):
            raise ValueError(f"{dotted_path} parent must be a table/object")
        if key not in current:
            raise ValueError(f"Missing required path: {dotted_path}")
        current = current[key]
        if raw_index is None:
            continue
        if not isinstance(current, list):
            raise ValueError(f"{'.'.join(dotted_path.split('.')[:-1])} must be an array")
        index = int(raw_index)
        if index < 0 or index >= len(current):
            raise ValueError(f"Index out of range while reading path: {dotted_path}")
        current = cast(TOMLValue, current[index])
    return current


def _write_path_with_indexes(root: TOMLTable, dotted_path: str, value: TOMLValue) -> None:
    segments = dotted_path.split(".")
    if len(segments) == 0:
        raise ValueError("dotted_path must not be empty")

    current: TOMLValue = root
    for segment in segments[:-1]:
        match = _INDEXED_SEGMENT_RE.match(segment)
        if match is None:
            raise ValueError(f"Unsupported indexed path: {dotted_path}")
        key = match.group("key")
        raw_index = match.group("index")
        if not isinstance(current, dict):
            raise ValueError(f"{dotted_path} parent must be a table/object")
        if key not in current:
            raise ValueError(f"Missing required path: {dotted_path}")
        current = current[key]
        if raw_index is None:
            continue
        if not isinstance(current, list):
            raise ValueError(f"{'.'.join(dotted_path.split('.')[:-1])} must be an array")
        index = int(raw_index)
        if index < 0 or index >= len(current):
            raise ValueError(f"Index out of range while writing path: {dotted_path}")
        current = cast(TOMLValue, current[index])

    last_segment = segments[-1]
    match = _INDEXED_SEGMENT_RE.match(last_segment)
    if match is None:
        raise ValueError(f"Unsupported indexed path: {dotted_path}")
    key = match.group("key")
    raw_index = match.group("index")
    if not isinstance(current, dict):
        raise ValueError(f"{dotted_path} parent must be a table/object")
    if key not in current:
        raise ValueError(f"Missing required path: {dotted_path}")
    if raw_index is None:
        current[key] = value
        return

    indexed_parent = current[key]
    if not isinstance(indexed_parent, list):
        raise ValueError(f"{'.'.join(dotted_path.split('.')[:-1])} must be an array")
    index = int(raw_index)
    if index < 0 or index >= len(indexed_parent):
        raise ValueError(f"Index out of range while writing path: {dotted_path}")
    indexed_parent[index] = value


def _parse_range_list(raw_range: list[TOMLValue], dotted_path: str, expect_integer: bool) -> tuple[bool, float, float, int]:
    if len(raw_range) != 4:
        raise ValueError(f"{dotted_path} must be [is_integer, start, end, count]")
    is_integer, start, end, count = raw_range
    if not isinstance(is_integer, bool):
        raise ValueError(f"{dotted_path}[0] (is_integer) must be bool")
    if isinstance(start, bool) or not isinstance(start, (int, float)):
        raise ValueError(f"{dotted_path}[1] (start) must be number")
    if isinstance(end, bool) or not isinstance(end, (int, float)):
        raise ValueError(f"{dotted_path}[2] (end) must be number")
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError(f"{dotted_path}[3] (count) must be int")
    if count < 1:
        raise ValueError(f"{dotted_path}[3] (count) must be >= 1")
    if end < start:
        raise ValueError(f"{dotted_path}[2] (end) must be >= {dotted_path}[1] (start)")
    if is_integer != expect_integer:
        expected = "true" if expect_integer else "false"
        raise ValueError(f"{dotted_path}[0] (is_integer) must be {expected}")
    return is_integer, float(start), float(end), count


def parse_range_at_path(root: TOMLTable, dotted_path: str, expect_integer: bool) -> tuple[bool, float, float, int]:
    raw_range = read_range_definition(root, dotted_path)
    return _parse_range_list(raw_range, f"{dotted_path}.range", expect_integer=expect_integer)


def build_candidates(is_integer: bool, start: float, end: float, count: int) -> Sequence[Number]:
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


def sample_candidate(candidates: Sequence[Number], *, seed: int, offset: int, attempt: int) -> Number:
    if len(candidates) == 0:
        raise ValueError("No candidates available for sampling")
    return candidates[(seed + offset + (attempt * ATTEMPT_STRIDE)) % len(candidates)]


def _entry_from_scalar_range(path: str, expect_integer: bool) -> SamplingRegistryEntry:
    return SamplingRegistryEntry(
        canonical_key=path,
        owner_path=path,
        sampler_kind="range",
        value_type="int" if expect_integer else "float",
        export_to_dataset=True,
        replay_affects_design=True,
    )


def _entry_from_group_geometry(path: str, expect_integer: bool) -> SamplingRegistryEntry:
    return SamplingRegistryEntry(
        canonical_key=path,
        owner_path=path,
        sampler_kind="range",
        value_type="int" if expect_integer else "float",
        export_to_dataset=True,
        replay_affects_design=True,
    )


def _entry_from_group_count(owner_path: str, canonical_key: str) -> SamplingRegistryEntry:
    return SamplingRegistryEntry(
        canonical_key=canonical_key,
        owner_path=owner_path,
        sampler_kind="inline_range",
        value_type="int",
        export_to_dataset=True,
        replay_affects_design=True,
    )


def _entry_from_fixed_group_count(owner_path: str, canonical_key: str) -> SamplingRegistryEntry:
    return SamplingRegistryEntry(
        canonical_key=canonical_key,
        owner_path=owner_path,
        sampler_kind="inline_range",
        value_type="int",
        export_to_dataset=False,
        replay_affects_design=False,
    )


def _entry_from_pcb_present(owner_path: str, canonical_key: str, fixed_value: int | None) -> SamplingRegistryEntry:
    return SamplingRegistryEntry(
        canonical_key=canonical_key,
        owner_path=owner_path,
        sampler_kind="inline_range",
        value_type="int",
        export_to_dataset=False,
        replay_affects_design=False,
        fixed_value=fixed_value,
    )


def build_sampling_registry(spec: TOMLTable) -> SamplingRegistry:
    entries: list[SamplingRegistryEntry] = []
    for path, _, expect_integer in SCALAR_RANGE_SPECS:
        if path in DERIVED_RANGE_PATHS:
            continue
        entries.append(_entry_from_scalar_range(path, expect_integer))
    for path, expect_integer in _GROUP_GEOMETRY_RANGE_SPECS:
        entries.append(_entry_from_group_geometry(path, expect_integer))

    raw_groups = spec.get("coil_groups")
    if isinstance(raw_groups, list):
        for idx, raw_group in enumerate(raw_groups):
            if not isinstance(raw_group, dict):
                continue
            kind = raw_group.get("kind")
            if kind not in GROUP_KIND_ORDER:
                continue
            field_name = _GROUP_COUNT_FIELD_BY_KIND[str(kind)]
            owner_path = f"coil_groups[{idx}].{field_name}"
            canonical_key = f"coil_groups.{kind}.{field_name}"
            if str(kind) == "rx_dd":
                entries.append(_entry_from_fixed_group_count(owner_path, canonical_key))
            else:
                entries.append(_entry_from_group_count(owner_path, canonical_key))

    raw_pcbs = spec.get("pcbs")
    if isinstance(raw_pcbs, list):
        for idx, raw_pcb in enumerate(raw_pcbs):
            if not isinstance(raw_pcb, dict):
                continue
            pcb_id = raw_pcb.get("id")
            if not isinstance(pcb_id, str) or pcb_id == "":
                continue
            fixed_rule = FIXED_PCB_RULES.get(pcb_id)
            fixed_value = int(fixed_rule["present"]) if fixed_rule is not None else None
            entries.append(
                _entry_from_pcb_present(
                    owner_path=f"pcbs[{idx}].present",
                    canonical_key=f"pcbs.{pcb_id}.present",
                    fixed_value=fixed_value,
                )
            )

    return SamplingRegistry(entries=entries, aliases=dict(DERIVED_RANGE_PATHS))


def iter_registry_entries_in_canonical_order(registry: SamplingRegistry) -> tuple[SamplingRegistryEntry, ...]:
    entries: list[SamplingRegistryEntry] = []
    for owner_path in registry.owner_paths():
        entry = registry.entry_for_owner(owner_path)
        if entry is None:
            raise ValueError(f"Sampling registry owner path is missing an entry: {owner_path}")
        entries.append(entry)
    entries.sort(key=lambda entry: entry.canonical_key)
    return tuple(entries)


def scan_sample_like_fields(value: TOMLValue, path: str = "") -> list[ScannedSamplingField]:
    found: list[ScannedSamplingField] = []
    if isinstance(value, dict):
        if set(value.keys()) == {"range"} and isinstance(value.get("range"), list):
            found.append(ScannedSamplingField(path=path, sampler_kind="range", raw_range=cast(list[TOMLValue], value["range"])))
            return found
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in _INLINE_RANGE_FIELDS and isinstance(child, list):
                found.append(
                    ScannedSamplingField(path=child_path, sampler_kind="inline_range", raw_range=cast(list[TOMLValue], child))
                )
                continue
            found.extend(scan_sample_like_fields(cast(TOMLValue, child), child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            child_path = f"{path}[{idx}]" if path else f"[{idx}]"
            found.extend(scan_sample_like_fields(cast(TOMLValue, child), child_path))
    return found


def _read_raw_range_for_path(root: TOMLTable, path: str, sampler_kind: SamplerKind) -> list[TOMLValue]:
    if sampler_kind == "range":
        return read_range_definition(root, path)
    raw_value = _read_path_with_indexes(root, path)
    if not isinstance(raw_value, list):
        raise ValueError(f"{path} must be [is_integer, start, end, count]")
    return cast(list[TOMLValue], raw_value)


def read_sampling_entry_raw_range(root: TOMLTable, entry: SamplingRegistryEntry) -> list[TOMLValue]:
    return _read_raw_range_for_path(root, entry.owner_path, entry.sampler_kind)


def write_sampling_entry_raw_range(root: TOMLTable, entry: SamplingRegistryEntry, raw_range: list[TOMLValue]) -> None:
    if entry.sampler_kind == "range":
        raw_node = _read_path_with_indexes(root, entry.owner_path)
        if not isinstance(raw_node, dict):
            raise ValueError(f"{entry.owner_path} must be a table/object")
        raw_node["range"] = raw_range
        return
    _write_path_with_indexes(root, entry.owner_path, raw_range)


def _expect_integer_for_entry(entry: SamplingRegistryEntry) -> bool:
    return entry.value_type == "int"


def is_sampling_entry_frozen(root: TOMLTable, entry: SamplingRegistryEntry) -> bool:
    raw_range = read_sampling_entry_raw_range(root, entry)
    if entry.sampler_kind == "range" and is_dummy_derived_range(raw_range):
        return False
    _, start, end, count = _parse_range_list(
        raw_range,
        f"{entry.owner_path}.range" if entry.sampler_kind == "range" else entry.owner_path,
        expect_integer=_expect_integer_for_entry(entry),
    )
    return count == 1 and float(start) == float(end)


def _coerce_fixed_value(raw_value: float, *, expect_integer: bool) -> Number:
    if expect_integer:
        return int(math.floor(raw_value + 0.5))
    return float(raw_value)


def preflight_sampling_spec(spec: TOMLTable, registry: SamplingRegistry) -> None:
    scanned_fields = scan_sample_like_fields(spec)
    for field in scanned_fields:
        if registry.is_alias_path(field.path):
            if field.sampler_kind != "range":
                raise ValueError(f"Derived alias must use range table syntax: {field.path}")
            ensure_dummy_derived_range(field.raw_range, field.path)
            continue

        entry = registry.entry_for_owner(field.path)
        if entry is None:
            raise ValueError(f"Unknown sampled field: {field.path}")
        if entry.sampler_kind != field.sampler_kind:
            raise ValueError(f"Sampling field kind mismatch for {field.path}")

        if field.sampler_kind == "range" and is_dummy_derived_range(field.raw_range):
            raise ValueError(
                f"{field.path}.range uses reserved derived marker [false, -1, -1, -1] "
                "but this path is not declared as derived"
            )

        expect_integer = _expect_integer_for_entry(entry)
        dotted_range_path = f"{field.path}.range" if field.sampler_kind == "range" else field.path
        _, start, end, count = _parse_range_list(field.raw_range, dotted_range_path, expect_integer=expect_integer)

        if field.path.endswith(".present"):
            candidates = build_candidates(True, start, end, count)
            if not all(int(candidate) in (0, 1) for candidate in candidates):
                raise ValueError(f"{field.path} candidates must be 0 or 1")

        if not entry.replay_affects_design:
            if count != 1 or float(start) != float(end):
                raise ValueError(f"normalized-away sampled field must be fixed with count=1: {field.path}")

    raw_pcbs = spec.get("pcbs")
    if not isinstance(raw_pcbs, list):
        return
    for idx, raw_pcb in enumerate(raw_pcbs):
        if not isinstance(raw_pcb, dict):
            continue
        z_mode = raw_pcb.get("z_mode")
        if z_mode != "relative_to_pcb":
            continue
        z_delta_path = raw_pcb.get("z_delta_path")
        if not isinstance(z_delta_path, str) or z_delta_path == "":
            continue
        if registry.entry_for_owner(z_delta_path) is None:
            raise ValueError(f"relative_to_pcb z_delta_path must reference registered sampling owner: pcbs[{idx}].z_delta_path")
        if registry.is_alias_path(z_delta_path):
            raise ValueError(f"relative_to_pcb z_delta_path must reference canonical owner path: {z_delta_path}")


def select_range_value(
    root: TOMLTable,
    dotted_path: str,
    expect_integer: bool,
    seed: int,
    offset: int,
    attempt: int,
    context: SamplingContext,
) -> Number:
    ledger = cast(SamplingLedger, context)
    if dotted_path in ledger:
        return ledger[dotted_path]
    if ledger.registry.is_alias_path(dotted_path):
        raw_range = _read_raw_range_for_path(root, dotted_path, "range")
        ensure_dummy_derived_range(raw_range, dotted_path)
        owner_path = ledger.registry.resolve_owner_path(dotted_path)
        selected = select_range_value(
            root,
            owner_path,
            expect_integer=expect_integer,
            seed=seed,
            offset=offset,
            attempt=attempt,
            context=ledger,
        )
        return ledger.record(dotted_path, selected)

    entry = ledger.registry.entry_for_owner(dotted_path)
    if entry is None:
        raise ValueError(f"Sampling path is not registered: {dotted_path}")
    if ledger.has_canonical_value(dotted_path):
        return ledger.record(dotted_path, ledger.canonical_value(dotted_path))
    if _expect_integer_for_entry(entry) != expect_integer:
        expected = "true" if expect_integer else "false"
        raise ValueError(f"{dotted_path} sampling registration requires is_integer={expected}")

    raw_range = _read_raw_range_for_path(root, entry.owner_path, entry.sampler_kind)
    if entry.sampler_kind == "range" and is_dummy_derived_range(raw_range):
        raise ValueError(
            f"{dotted_path}.range uses reserved derived marker [false, -1, -1, -1] "
            "but this path is not declared as derived"
        )
    dotted_range_path = f"{entry.owner_path}.range" if entry.sampler_kind == "range" else entry.owner_path
    is_integer, start, end, count = _parse_range_list(raw_range, dotted_range_path, expect_integer=expect_integer)
    candidates = build_candidates(is_integer=is_integer, start=start, end=end, count=count)
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated from {dotted_range_path}")
    selected = sample_candidate(candidates, seed=seed, offset=offset, attempt=attempt)
    return ledger.record(dotted_path, selected)


def select_range_end_value(root: TOMLTable, dotted_path: str, expect_integer: bool) -> Number:
    raw_range = read_range_definition(root, dotted_path)
    if dotted_path in DERIVED_RANGE_PATHS:
        ensure_dummy_derived_range(raw_range, dotted_path)
        return select_range_end_value(root, DERIVED_RANGE_PATHS[dotted_path], expect_integer=expect_integer)
    if is_dummy_derived_range(raw_range):
        raise ValueError(
            f"{dotted_path}.range uses reserved derived marker [false, -1, -1, -1] "
            "but this path is not declared as derived"
        )
    is_integer, _, end, _ = _parse_range_list(raw_range, f"{dotted_path}.range", expect_integer=expect_integer)
    if is_integer:
        return int(math.floor(end + 0.5))
    return float(end)

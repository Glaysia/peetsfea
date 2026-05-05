from __future__ import annotations

import copy
import re
from typing import Literal, Mapping, cast

from peetsfea.spec.loader import TOMLTable, TOMLValue
from peetsfea.legacy.type1.spec.resolver.sampling import (
    SamplingLedger,
    SamplingRegistryEntry,
    build_sampling_registry,
    is_sampling_entry_frozen,
    iter_registry_entries_in_canonical_order,
    read_sampling_entry_raw_range,
    write_sampling_entry_raw_range,
)

_SNAPSHOT_METADATA_KEY = "snapshot_metadata"
_SAMPLED_OWNER_PATHS_KEY = "sampled_owner_paths"


def detect_repro_mode(spec: Mapping[str, object]) -> Literal["sampled_toml", "frozen_toml"]:
    if not isinstance(spec, dict):
        return "sampled_toml"

    registry = build_sampling_registry(cast(TOMLTable, spec))
    if len(registry.owner_paths()) == 0:
        return "sampled_toml"

    for entry in iter_registry_entries_in_canonical_order(registry):
        if not is_sampling_entry_frozen(cast(TOMLTable, spec), entry):
            return "sampled_toml"
    return "frozen_toml"


def _read_snapshot_owner_paths(spec: TOMLTable) -> tuple[str, ...] | None:
    raw_metadata = spec.get(_SNAPSHOT_METADATA_KEY)
    if not isinstance(raw_metadata, dict):
        return None
    raw_paths = raw_metadata.get(_SAMPLED_OWNER_PATHS_KEY)
    if not isinstance(raw_paths, list):
        return None
    parsed_paths: list[str] = []
    for raw_path in raw_paths:
        if not isinstance(raw_path, str) or raw_path == "":
            return None
        parsed_paths.append(raw_path)
    return tuple(parsed_paths)


def _coerce_selected_value(entry: SamplingRegistryEntry, selected_value: int | float) -> TOMLValue:
    if entry.value_type == "int":
        return int(selected_value)
    return float(selected_value)


def _coerce_frozen_range_value(entry: SamplingRegistryEntry, spec: TOMLTable) -> TOMLValue:
    raw_range = read_sampling_entry_raw_range(spec, entry)
    if len(raw_range) != 4:
        raise ValueError(f"{entry.owner_path} must be [is_integer, start, end, count]")
    start = raw_range[1]
    end = raw_range[2]
    count = raw_range[3]
    if isinstance(start, bool) or not isinstance(start, (int, float)):
        raise ValueError(f"{entry.owner_path} frozen range start must be numeric")
    if isinstance(end, bool) or not isinstance(end, (int, float)):
        raise ValueError(f"{entry.owner_path} frozen range end must be numeric")
    if isinstance(count, bool) or not isinstance(count, int) or count != 1:
        raise ValueError(f"{entry.owner_path} frozen range count must be 1")
    if float(start) != float(end):
        raise ValueError(f"{entry.owner_path} frozen range must have start=end")
    return _coerce_selected_value(entry, float(start))


def _freeze_scalar_range(raw_range: list[TOMLValue], selected_value: TOMLValue) -> list[TOMLValue]:
    is_integer = raw_range[0]
    if not isinstance(is_integer, bool):
        raise ValueError("range[0] must be bool")
    return [is_integer, selected_value, selected_value, 1]


def freeze_sampled_ranges_only(source_spec: TOMLTable, repro_spec: TOMLTable) -> TOMLTable:
    frozen = copy.deepcopy(source_spec)
    registry = build_sampling_registry(source_spec)

    for entry in iter_registry_entries_in_canonical_order(registry):
        if is_sampling_entry_frozen(source_spec, entry):
            continue
        raw_range = read_sampling_entry_raw_range(frozen, entry)
        selected_value = _coerce_frozen_range_value(entry, repro_spec)
        write_sampling_entry_raw_range(frozen, entry, _freeze_scalar_range(raw_range, selected_value))

    return frozen


def require_frozen_sampling_spec(spec: TOMLTable) -> None:
    registry = build_sampling_registry(spec)
    for entry in iter_registry_entries_in_canonical_order(registry):
        if is_sampling_entry_frozen(spec, entry):
            continue
        raise ValueError(
            "Build input TOML must freeze every sampling owner to count=1 with identical bounds; "
            f"first unfrozen owner: {entry.owner_path}"
        )


def freeze_ranges_for_snapshot(spec: TOMLTable, sampling_ledger: SamplingLedger) -> TOMLTable:
    frozen = copy.deepcopy(spec)
    registry = sampling_ledger.registry
    repro_mode = detect_repro_mode(spec)

    for entry in iter_registry_entries_in_canonical_order(registry):
        raw_range = read_sampling_entry_raw_range(frozen, entry)
        if sampling_ledger.has_canonical_value(entry.owner_path):
            selected_value = _coerce_selected_value(entry, sampling_ledger.canonical_value(entry.owner_path))
        elif entry.fixed_value is not None:
            selected_value = _coerce_selected_value(entry, entry.fixed_value)
        elif is_sampling_entry_frozen(frozen, entry):
            selected_value = _coerce_frozen_range_value(entry, frozen)
        else:
            raise ValueError(f"Sampling ledger is missing selected value for replay-affecting owner: {entry.owner_path}")
        write_sampling_entry_raw_range(frozen, entry, _freeze_scalar_range(raw_range, selected_value))

    frozen[_SNAPSHOT_METADATA_KEY] = {
        _SAMPLED_OWNER_PATHS_KEY: list(dataset_owner_paths(spec, repro_mode=repro_mode))
    }
    return frozen


def _effective_dataset_entries(
    spec: TOMLTable,
    *,
    repro_mode: Literal["sampled_toml", "frozen_toml"],
) -> tuple[SamplingRegistryEntry, ...]:
    registry = build_sampling_registry(spec)
    if repro_mode == "frozen_toml":
        snapshot_owner_paths = _read_snapshot_owner_paths(spec)
        if snapshot_owner_paths is not None:
            frozen_entries: list[SamplingRegistryEntry] = []
            for owner_path in snapshot_owner_paths:
                entry = registry.entry_for_owner(owner_path)
                if entry is None:
                    raise ValueError(f"Frozen repro metadata references unknown sampling owner: {owner_path}")
                if not entry.export_to_dataset:
                    raise ValueError(f"Frozen repro metadata references non-exportable sampling owner: {owner_path}")
                frozen_entries.append(entry)
            return tuple(sorted(frozen_entries, key=lambda entry: entry.canonical_key))

    exportable: list[SamplingRegistryEntry] = []
    for entry in iter_registry_entries_in_canonical_order(registry):
        if not entry.export_to_dataset:
            continue
        if repro_mode == "sampled_toml" and is_sampling_entry_frozen(spec, entry):
            continue
        exportable.append(entry)
    return tuple(exportable)


def dataset_owner_paths(spec: TOMLTable, *, repro_mode: Literal["sampled_toml", "frozen_toml"]) -> tuple[str, ...]:
    return tuple(entry.owner_path for entry in _effective_dataset_entries(spec, repro_mode=repro_mode))


def build_dataset_spec(
    spec: TOMLTable,
    sampling_ledger: SamplingLedger,
    design_id: str,
    repro_mode: Literal["sampled_toml", "frozen_toml"],
) -> TOMLTable:
    input_parameters: list[TOMLValue] = []
    for entry in _effective_dataset_entries(spec, repro_mode=repro_mode):
        if sampling_ledger.has_canonical_value(entry.owner_path):
            value = _coerce_selected_value(entry, sampling_ledger.canonical_value(entry.owner_path))
        elif repro_mode == "frozen_toml":
            value = _coerce_frozen_range_value(entry, spec)
        else:
            raise ValueError(f"Sampling ledger is missing dataset owner value: {entry.owner_path}")
        input_parameters.append({"path": entry.owner_path, "value": value})

    constraints = spec.get("constraints")
    constraints_table: TOMLTable = copy.deepcopy(cast(TOMLTable, constraints)) if isinstance(constraints, dict) else {}
    dataset_spec: TOMLTable = {
        "inputs": {"parameters": input_parameters},
        "output": {"placeholder": -1},
        "simulation": {"timeout_sec": 7200},
        "artifacts": {"aedt_file": f"{design_id}.aedt"},
        "constraints": constraints_table,
    }
    return dataset_spec


def _format_number(value: int | float) -> str:
    if isinstance(value, bool):
        raise ValueError("boolean is not a number")
    if isinstance(value, int):
        return str(value)
    return repr(float(value))


def _format_key(key: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]+", key):
        return key
    escaped = key.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _format_toml_value(value: TOMLValue) -> str:
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _format_number(value)
    if isinstance(value, list):
        return "[" + ", ".join(_format_toml_value(cast(TOMLValue, item)) for item in value) + "]"
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            parts.append(f"{_format_key(key)} = {_format_toml_value(cast(TOMLValue, item))}")
        return "{ " + ", ".join(parts) + " }"
    raise ValueError(f"Unsupported TOML value type: {type(value)}")


def _is_array_of_tables(value: TOMLValue) -> bool:
    return isinstance(value, list) and len(value) > 0 and all(isinstance(item, dict) for item in value)


def _render_table(lines: list[str], table: TOMLTable, prefix: str | None) -> None:
    scalar_items: list[tuple[str, TOMLValue]] = []
    table_items: list[tuple[str, TOMLTable]] = []
    aot_items: list[tuple[str, list[TOMLTable]]] = []

    for key, value in table.items():
        if isinstance(value, dict):
            table_items.append((key, cast(TOMLTable, value)))
            continue
        if _is_array_of_tables(cast(TOMLValue, value)):
            aot_items.append((key, cast(list[TOMLTable], value)))
            continue
        scalar_items.append((key, cast(TOMLValue, value)))

    for key, value in scalar_items:
        lines.append(f"{_format_key(key)} = {_format_toml_value(value)}")

    for key, child in table_items:
        child_name = f"{prefix}.{key}" if prefix else key
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(f"[{child_name}]")
        _render_table(lines, child, child_name)

    for key, children in aot_items:
        child_name = f"{prefix}.{key}" if prefix else key
        for child in children:
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(f"[[{child_name}]]")
            _render_table(lines, child, child_name)


def toml_dumps(table: TOMLTable) -> str:
    lines: list[str] = []
    _render_table(lines, table, None)
    return "\n".join(lines).strip() + "\n"

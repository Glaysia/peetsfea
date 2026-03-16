from __future__ import annotations

from peetsfea.spec.loader import TOMLTable, TOMLValue, require_table
from peetsfea.version import SUPPORTED_SPEC_VERSION

from .constants import REMOVED_PATHS


def read_path(root: TOMLTable, dotted_path: str) -> TOMLValue:
    parts = dotted_path.split(".")
    current: TOMLValue = root
    for idx, part in enumerate(parts):
        if not isinstance(current, dict):
            raise ValueError(f"{'.'.join(parts[:idx])} must be a table/object")
        if part not in current:
            raise ValueError(f"Missing required path: {dotted_path}")
        current = current[part]
    return current


def reject_removed_paths(spec: TOMLTable) -> None:
    for path in REMOVED_PATHS:
        try:
            read_path(spec, path)
        except ValueError:
            continue
        raise ValueError(f"Removed path in spec_version {SUPPORTED_SPEC_VERSION}: {path}")


def read_range_definition(root: TOMLTable, dotted_path: str) -> list[TOMLValue]:
    table = require_table(read_path(root, dotted_path), dotted_path)
    if set(table.keys()) != {"range"}:
        raise ValueError(f"{dotted_path} supports only the 'range' key")
    raw_range = table.get("range")
    if not isinstance(raw_range, list) or len(raw_range) != 4:
        raise ValueError(f"{dotted_path}.range must be [is_integer, start, end, count]")
    return raw_range


def parse_string_value_at_path(root: TOMLTable, dotted_path: str, *, allowed: set[str]) -> str:
    table = require_table(read_path(root, dotted_path), dotted_path)
    if set(table.keys()) != {"value"}:
        raise ValueError(f"{dotted_path} supports only the 'value' key")
    raw_value = table.get("value")
    if not isinstance(raw_value, str):
        raise ValueError(f"{dotted_path}.value must be string")
    if raw_value not in allowed:
        raise ValueError(f"{dotted_path}.value must be one of {sorted(allowed)}")
    return raw_value

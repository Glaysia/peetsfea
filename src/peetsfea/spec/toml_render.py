from __future__ import annotations

import re
from typing import cast

from peetsfea.spec.loader import TOMLTable, TOMLValue


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


def _render_table(lines: list[str], table: TOMLTable, prefix: str) -> None:
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
        child_name = f"{prefix}.{key}" if prefix != "" else key
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(f"[{child_name}]")
        _render_table(lines, child, child_name)

    for key, children in aot_items:
        child_name = f"{prefix}.{key}" if prefix != "" else key
        for child in children:
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(f"[[{child_name}]]")
            _render_table(lines, child, child_name)


def toml_dumps(table: TOMLTable) -> str:
    lines: list[str] = []
    _render_table(lines, table, "")
    return "\n".join(lines).strip() + "\n"


__all__ = ["toml_dumps"]

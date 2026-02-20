from __future__ import annotations

from pathlib import Path
import tomllib
from typing import TypeAlias


TOMLPrimitive: TypeAlias = str | int | float | bool
TOMLValue: TypeAlias = TOMLPrimitive | list["TOMLValue"] | dict[str, "TOMLValue"]
TOMLTable: TypeAlias = dict[str, TOMLValue]


def load_toml_bytes(path: Path) -> tuple[TOMLTable, bytes]:
    if not path.exists():
        raise FileNotFoundError(f"TOML file not found: {path}")
    raw = path.read_bytes()
    try:
        parsed = tomllib.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError(f"TOML must be UTF-8: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid TOML format: {path}") from exc
    return parsed, raw


def require_table(value: TOMLValue | None, name: str) -> TOMLTable:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a table/object")
    return value


def require_str(value: TOMLValue | None, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value

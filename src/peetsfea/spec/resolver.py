from __future__ import annotations

import math
from typing import TypeAlias

from peetsfea.spec.loader import TOMLTable, TOMLValue, require_table
from peetsfea.types.manifest import SelectedParameters


Number: TypeAlias = int | float
PARAMETER_OFFSETS: dict[str, int] = {
    "turns": 0,
    "outer": 1,
    "trace": 2,
    "gap": 3,
    "thickness": 4,
}


def _parse_parameter_range(spec: TOMLTable, parameter_name: str) -> tuple[bool, float, float, int]:
    parameters = require_table(spec.get("parameters"), "parameters")
    parameter = require_table(parameters.get(parameter_name), f"parameters.{parameter_name}")
    raw_range = parameter.get("range")
    if not isinstance(raw_range, list) or len(raw_range) != 4:
        raise ValueError(f"parameters.{parameter_name}.range must be [is_integer, start, end, count]")

    is_integer, start, end, count = raw_range

    if not isinstance(is_integer, bool):
        raise ValueError("range[0] (is_integer) must be bool")
    if isinstance(start, bool) or not isinstance(start, (int, float)):
        raise ValueError("range[1] (start) must be number")
    if isinstance(end, bool) or not isinstance(end, (int, float)):
        raise ValueError("range[2] (end) must be number")
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("range[3] (count) must be int")
    if count < 1:
        raise ValueError("range[3] (count) must be >= 1")
    if end < start:
        raise ValueError("range[2] (end) must be >= range[1] (start)")

    return is_integer, float(start), float(end), count


def _build_candidates(is_integer: bool, start: float, end: float, count: int) -> list[Number]:
    if count == 1:
        raw_values: list[Number] = [start]
    else:
        step = (end - start) / (count - 1)
        raw_values = [start + (step * i) for i in range(count)]

    if not is_integer:
        return raw_values

    rounded = [int(math.floor(value + 0.5)) for value in raw_values]
    deduped: list[Number] = []
    seen: set[int] = set()
    for value in rounded:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped


def _select_parameter_value(spec: TOMLTable, parameter_name: str, seed: int, offset: int) -> Number:
    is_integer, start, end, count = _parse_parameter_range(spec=spec, parameter_name=parameter_name)
    candidates = _build_candidates(is_integer=is_integer, start=start, end=end, count=count)
    if not candidates:
        raise ValueError(f"No candidates generated from parameters.{parameter_name}.range")

    if parameter_name == "turns" and not is_integer:
        raise ValueError("parameters.turns.range[0] (is_integer) must be true")
    if parameter_name != "turns" and is_integer:
        raise ValueError(f"parameters.{parameter_name}.range[0] (is_integer) should be false")

    selected_index = (seed + offset) % len(candidates)
    return candidates[selected_index]


def _validate_geometry_constraints(selected: SelectedParameters) -> None:
    turns = selected["turns"]
    outer = selected["outer"]
    trace = selected["trace"]
    gap = selected["gap"]
    thickness = selected["thickness"]

    if turns < 1:
        raise ValueError("Selected turns must be >= 1")
    if trace <= 0:
        raise ValueError("Selected trace must be > 0")
    if gap < 0:
        raise ValueError("Selected gap must be >= 0")
    if thickness <= 0:
        raise ValueError("Selected thickness must be > 0")

    inner_width = outer - (2.0 * turns * trace) - (2.0 * (turns - 1) * gap)
    if inner_width <= 0:
        raise ValueError("Invalid geometry: inner width must be > 0")


def resolve_selected_parameters(spec: TOMLTable, seed: int) -> SelectedParameters:
    raw_selected: dict[str, Number] = {}
    for parameter_name, offset in PARAMETER_OFFSETS.items():
        raw_selected[parameter_name] = _select_parameter_value(
            spec=spec,
            parameter_name=parameter_name,
            seed=seed,
            offset=offset,
        )

    selected: SelectedParameters = {
        "turns": int(raw_selected["turns"]),
        "outer": float(raw_selected["outer"]),
        "trace": float(raw_selected["trace"]),
        "gap": float(raw_selected["gap"]),
        "thickness": float(raw_selected["thickness"]),
    }
    _validate_geometry_constraints(selected)
    return selected

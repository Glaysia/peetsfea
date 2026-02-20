from __future__ import annotations

import math
from typing import Sequence, TypeAlias

from peetsfea.spec.loader import TOMLTable, require_table
from peetsfea.types.manifest import SelectedParameters


Number: TypeAlias = int | float
PARAMETER_ORDER: tuple[str, ...] = (
    "pcb_count",
    "turns",
    "outer",
    "trace",
    "gap",
    "via_diameter",
    "pcb_thickness",
    "cu_thickness",
    "fr4_er",
)
PARAMETER_OFFSETS: dict[str, int] = {name: idx for idx, name in enumerate(PARAMETER_ORDER)}
INTEGER_PARAMETERS: set[str] = {"pcb_count", "turns"}
FIXED_PARAMETERS: set[str] = {"pcb_count", "pcb_thickness", "cu_thickness", "fr4_er"}
FIXED_DEFAULTS: dict[str, float] = {
    "pcb_count": 1.0,
    "pcb_thickness": 1.6,
    "cu_thickness": 0.035,
}


def _parse_parameter_range(parameters: TOMLTable, parameter_name: str) -> tuple[bool, float, float, int]:
    parameter = require_table(parameters.get(parameter_name), f"parameters.{parameter_name}")
    if set(parameter.keys()) != {"range"}:
        raise ValueError(f"parameters.{parameter_name} supports only the 'range' key")

    raw_range = parameter.get("range")
    if not isinstance(raw_range, list) or len(raw_range) != 4:
        raise ValueError(f"parameters.{parameter_name}.range must be [is_integer, start, end, count]")

    is_integer, start, end, count = raw_range

    if not isinstance(is_integer, bool):
        raise ValueError(f"parameters.{parameter_name}.range[0] (is_integer) must be bool")
    if isinstance(start, bool) or not isinstance(start, (int, float)):
        raise ValueError(f"parameters.{parameter_name}.range[1] (start) must be number")
    if isinstance(end, bool) or not isinstance(end, (int, float)):
        raise ValueError(f"parameters.{parameter_name}.range[2] (end) must be number")
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError(f"parameters.{parameter_name}.range[3] (count) must be int")
    if count < 1:
        raise ValueError(f"parameters.{parameter_name}.range[3] (count) must be >= 1")
    if end < start:
        raise ValueError(f"parameters.{parameter_name}.range[2] (end) must be >= range[1] (start)")

    if parameter_name in INTEGER_PARAMETERS and not is_integer:
        raise ValueError(f"parameters.{parameter_name}.range[0] (is_integer) must be true")
    if parameter_name not in INTEGER_PARAMETERS and is_integer:
        raise ValueError(f"parameters.{parameter_name}.range[0] (is_integer) must be false")

    if parameter_name in FIXED_PARAMETERS and (count != 1 or float(start) != float(end)):
        raise ValueError(f"parameters.{parameter_name} must be fixed as start=end and count=1")

    return is_integer, float(start), float(end), count


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


def _select_parameter_value(parameters: TOMLTable, parameter_name: str, seed: int, offset: int) -> Number:
    is_integer, start, end, count = _parse_parameter_range(parameters=parameters, parameter_name=parameter_name)
    candidates = _build_candidates(is_integer=is_integer, start=start, end=end, count=count)
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated from parameters.{parameter_name}.range")

    selected_index = (seed + offset) % len(candidates)
    return candidates[selected_index]


def _validate_geometry_constraints(selected: SelectedParameters) -> None:
    if selected["pcb_count"] != 1:
        raise ValueError("Selected pcb_count must be exactly 1 in this MVP")
    if selected["turns"] < 1:
        raise ValueError("Selected turns must be >= 1")
    if selected["trace"] <= 0:
        raise ValueError("Selected trace must be > 0")
    if selected["gap"] < 0:
        raise ValueError("Selected gap must be >= 0")
    if selected["via_diameter"] <= 0:
        raise ValueError("Selected via_diameter must be > 0")
    if selected["pcb_thickness"] <= 0:
        raise ValueError("Selected pcb_thickness must be > 0")
    if selected["cu_thickness"] <= 0:
        raise ValueError("Selected cu_thickness must be > 0")
    if selected["fr4_er"] <= 1.0:
        raise ValueError("Selected fr4_er must be > 1.0")

    pcb_count_expected = FIXED_DEFAULTS["pcb_count"]
    if not math.isclose(float(selected["pcb_count"]), pcb_count_expected, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"Selected pcb_count must be fixed to {pcb_count_expected}")

    pcb_thickness_expected = FIXED_DEFAULTS["pcb_thickness"]
    if not math.isclose(float(selected["pcb_thickness"]), pcb_thickness_expected, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"Selected pcb_thickness must be fixed to {pcb_thickness_expected}")

    cu_thickness_expected = FIXED_DEFAULTS["cu_thickness"]
    if not math.isclose(float(selected["cu_thickness"]), cu_thickness_expected, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"Selected cu_thickness must be fixed to {cu_thickness_expected}")

    turns = float(selected["turns"])
    inner_width = selected["outer"] - (2.0 * turns * selected["trace"]) - (2.0 * (turns - 1.0) * selected["gap"])
    if inner_width <= 0:
        raise ValueError("Invalid geometry: inner width must be > 0")


def resolve_selected_parameters(spec: TOMLTable, seed: int) -> SelectedParameters:
    parameters = require_table(spec.get("parameters"), "parameters")

    provided = set(parameters.keys())
    expected = set(PARAMETER_ORDER)
    missing = sorted(expected - provided)
    extra = sorted(provided - expected)
    if missing:
        raise ValueError(f"Missing required parameter keys: {', '.join(missing)}")
    if extra:
        raise ValueError(f"Unsupported parameter keys: {', '.join(extra)}")

    raw_selected: dict[str, Number] = {}
    for parameter_name in PARAMETER_ORDER:
        raw_selected[parameter_name] = _select_parameter_value(
            parameters=parameters,
            parameter_name=parameter_name,
            seed=seed,
            offset=PARAMETER_OFFSETS[parameter_name],
        )

    selected: SelectedParameters = {
        "pcb_count": int(raw_selected["pcb_count"]),
        "turns": int(raw_selected["turns"]),
        "outer": float(raw_selected["outer"]),
        "trace": float(raw_selected["trace"]),
        "gap": float(raw_selected["gap"]),
        "via_diameter": float(raw_selected["via_diameter"]),
        "pcb_thickness": float(raw_selected["pcb_thickness"]),
        "cu_thickness": float(raw_selected["cu_thickness"]),
        "fr4_er": float(raw_selected["fr4_er"]),
    }
    _validate_geometry_constraints(selected)
    return selected

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import cast

from peetsfea.types.manifest import OutputVariableSpec, OutputsSpec

ACTIVE_RX_ONLY_OUTPUT_VARIABLE_NAMES = frozenset(
    (
        "Lrx_uH",
        "Qrx_ratio",
        "Rrx_ac_ohm",
        "Xrx_ohm",
        "Grx_S",
        "Brx_S",
        "Srx_self_mag_ratio",
        "eta_rx_accept_ratio",
    )
)
_ACTIVE_OUTPUT_MODE = "RxOnly"


def _require_table(value: object, *, context: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{context} must be a table/object")
    return value


def _require_non_empty_string(value: object, *, context: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{context} must be string")
    if value == "":
        raise ValueError(f"{context} must be non-empty string")
    return value


def parse_outputs_table(raw_outputs: object, *, context: str) -> OutputsSpec:
    outputs = _require_table(raw_outputs, context=context)
    expected_keys = {
        "mode",
        "report_name",
        "solution_name",
        "primary_sweep",
        "report_category",
        "plot_type",
        "variables",
    }
    missing_keys = sorted(expected_keys - set(outputs.keys()))
    if missing_keys:
        raise ValueError(f"{context} is missing required keys: {missing_keys}")
    extra_keys = sorted(set(outputs.keys()) - expected_keys)
    if extra_keys:
        raise ValueError(f"{context} contains unsupported keys: {extra_keys}")

    mode = _require_non_empty_string(outputs["mode"], context=f"{context}.mode")
    if mode != _ACTIVE_OUTPUT_MODE:
        raise ValueError(f"{context}.mode must be '{_ACTIVE_OUTPUT_MODE}' (actual={mode!r})")

    raw_variables = outputs["variables"]
    if not isinstance(raw_variables, list):
        raise ValueError(f"{context}.variables must be an array of tables")
    if len(raw_variables) == 0:
        raise ValueError(f"{context}.variables must be non-empty")

    variables: list[OutputVariableSpec] = []
    seen_names: set[str] = set()
    for index, raw_variable in enumerate(raw_variables):
        if not isinstance(raw_variable, Mapping):
            raise ValueError(f"{context}.variables[{index}] must be a table/object")
        expected_variable_keys = {"name", "expression"}
        extra_variable_keys = sorted(set(raw_variable.keys()) - expected_variable_keys)
        if extra_variable_keys:
            raise ValueError(f"{context}.variables[{index}] contains unsupported keys: {extra_variable_keys}")
        missing_variable_keys = sorted(expected_variable_keys - set(raw_variable.keys()))
        if missing_variable_keys:
            raise ValueError(f"{context}.variables[{index}] is missing required keys: {missing_variable_keys}")
        name = _require_non_empty_string(raw_variable["name"], context=f"{context}.variables[{index}].name")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
            raise ValueError(f"{context}.variables[{index}].name must match ^[A-Za-z][A-Za-z0-9_]*$")
        if name in seen_names:
            raise ValueError(f"{context}.variables[{index}].name must be unique: {name}")
        if name not in ACTIVE_RX_ONLY_OUTPUT_VARIABLE_NAMES:
            raise ValueError(
                f"{context}.variables[{index}].name is not supported for {_ACTIVE_OUTPUT_MODE} "
                f"(actual={name!r})"
            )
        expression = _require_non_empty_string(
            raw_variable["expression"],
            context=f"{context}.variables[{index}].expression",
        )
        if "TX_TML" in expression:
            raise ValueError(
                f"{context}.variables[{index}].expression references TX_TML but {_ACTIVE_OUTPUT_MODE} has no TX terminal"
            )
        seen_names.add(name)
        variables.append({"name": name, "expression": expression})

    return cast(
        OutputsSpec,
        {
            "mode": mode,
            "report_name": _require_non_empty_string(outputs["report_name"], context=f"{context}.report_name"),
            "solution_name": _require_non_empty_string(outputs["solution_name"], context=f"{context}.solution_name"),
            "primary_sweep": _require_non_empty_string(outputs["primary_sweep"], context=f"{context}.primary_sweep"),
            "report_category": _require_non_empty_string(
                outputs["report_category"],
                context=f"{context}.report_category",
            ),
            "plot_type": _require_non_empty_string(outputs["plot_type"], context=f"{context}.plot_type"),
            "variables": variables,
        },
    )


__all__ = ["ACTIVE_RX_ONLY_OUTPUT_VARIABLE_NAMES", "parse_outputs_table"]

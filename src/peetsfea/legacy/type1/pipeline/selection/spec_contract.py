from __future__ import annotations

import re
from typing import Mapping

from peetsfea.types.manifest import EmPolicy, OutputVariableSpec, OutputsSpec


def _require_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be number")
    return float(value)


def _require_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be int")
    return value


def _require_string(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be string")
    return value


def _require_non_empty_string(value: object, name: str) -> str:
    parsed = _require_string(value, name)
    if parsed == "":
        raise ValueError(f"{name} must be non-empty string")
    return parsed


def _parse_simulation_policy(spec: Mapping[str, object]) -> EmPolicy:
    assert "simulation" in spec, "simulation must be present"
    raw_simulation = spec["simulation"]
    if not isinstance(raw_simulation, dict):
        raise ValueError("simulation must be a table/object")
    simulation = raw_simulation
    expected_keys = {
        "radiation_margin_mm",
        "setup_frequency_hz",
        "sweep_start_hz",
        "sweep_stop_hz",
        "validation_gate",
        "max_delta_s",
        "maximum_passes",
        "minimum_passes",
        "minimum_converged_passes",
        "percent_refinement",
        "basis_order",
        "port_accuracy",
    }
    missing_keys = sorted(expected_keys - set(simulation.keys()))
    if missing_keys:
        raise ValueError(f"simulation is missing required keys: {missing_keys}")
    extra_keys = sorted(set(simulation.keys()) - expected_keys)
    if extra_keys:
        raise ValueError(f"simulation contains unsupported keys: {extra_keys}")

    radiation_margin_mm = _require_number(simulation["radiation_margin_mm"], "simulation.radiation_margin_mm")
    setup_frequency_hz = _require_number(simulation["setup_frequency_hz"], "simulation.setup_frequency_hz")
    sweep_start_hz = _require_number(simulation["sweep_start_hz"], "simulation.sweep_start_hz")
    sweep_stop_hz = _require_number(simulation["sweep_stop_hz"], "simulation.sweep_stop_hz")
    raw_validation_gate = _require_string(simulation["validation_gate"], "simulation.validation_gate")
    if raw_validation_gate != "hard_fail":
        raise ValueError("simulation.validation_gate must be 'hard_fail'")
    max_delta_s = _require_number(simulation["max_delta_s"], "simulation.max_delta_s")
    maximum_passes = _require_int(simulation["maximum_passes"], "simulation.maximum_passes")
    minimum_passes = _require_int(simulation["minimum_passes"], "simulation.minimum_passes")
    minimum_converged_passes = _require_int(simulation["minimum_converged_passes"], "simulation.minimum_converged_passes")
    percent_refinement = _require_int(simulation["percent_refinement"], "simulation.percent_refinement")
    basis_order = _require_int(simulation["basis_order"], "simulation.basis_order")
    port_accuracy = _require_int(simulation["port_accuracy"], "simulation.port_accuracy")

    if radiation_margin_mm <= 0.0:
        raise ValueError("simulation.radiation_margin_mm must be > 0")
    if setup_frequency_hz <= 0.0:
        raise ValueError("simulation.setup_frequency_hz must be > 0")
    if sweep_start_hz <= 0.0:
        raise ValueError("simulation.sweep_start_hz must be > 0")
    if sweep_stop_hz <= sweep_start_hz:
        raise ValueError("simulation.sweep_stop_hz must be > simulation.sweep_start_hz")
    if not (0.0 < max_delta_s < 1.0):
        raise ValueError("simulation.max_delta_s must be > 0 and < 1")
    if not (maximum_passes >= minimum_passes >= 1):
        raise ValueError("simulation pass constraints must satisfy maximum_passes >= minimum_passes >= 1")
    if minimum_converged_passes > maximum_passes:
        raise ValueError("simulation.minimum_converged_passes must be <= simulation.maximum_passes")
    if percent_refinement <= 0:
        raise ValueError("simulation.percent_refinement must be > 0")
    if basis_order < 1:
        raise ValueError("simulation.basis_order must be >= 1")
    if port_accuracy < 1:
        raise ValueError("simulation.port_accuracy must be >= 1")
    return {
        "radiation_margin_mm": radiation_margin_mm,
        "setup_frequency_hz": setup_frequency_hz,
        "sweep_start_hz": sweep_start_hz,
        "sweep_stop_hz": sweep_stop_hz,
        "validation_gate": raw_validation_gate,
        "max_delta_s": max_delta_s,
        "maximum_passes": maximum_passes,
        "minimum_passes": minimum_passes,
        "minimum_converged_passes": minimum_converged_passes,
        "percent_refinement": percent_refinement,
        "basis_order": basis_order,
        "port_accuracy": port_accuracy,
    }


def _parse_outputs_spec(spec: Mapping[str, object]) -> OutputsSpec:
    assert "outputs" in spec, "outputs must be present"
    raw_outputs = spec["outputs"]
    if not isinstance(raw_outputs, dict):
        raise ValueError("outputs must be a table/object")
    outputs = raw_outputs
    expected_keys = {
        "report_name",
        "solution_name",
        "primary_sweep",
        "report_category",
        "plot_type",
        "variables",
    }
    missing_keys = sorted(expected_keys - set(outputs.keys()))
    if missing_keys:
        raise ValueError(f"outputs is missing required keys: {missing_keys}")
    extra_keys = sorted(set(outputs.keys()) - expected_keys)
    if extra_keys:
        raise ValueError(f"outputs contains unsupported keys: {extra_keys}")

    raw_variables = outputs["variables"]
    if not isinstance(raw_variables, list):
        raise ValueError("outputs.variables must be an array of tables")
    if len(raw_variables) == 0:
        raise ValueError("outputs.variables must be non-empty")

    variables: list[OutputVariableSpec] = []
    seen_names: set[str] = set()
    for index, raw_variable in enumerate(raw_variables):
        if not isinstance(raw_variable, dict):
            raise ValueError(f"outputs.variables[{index}] must be a table/object")
        expected_variable_keys = {"name", "expression"}
        extra_variable_keys = sorted(set(raw_variable.keys()) - expected_variable_keys)
        if extra_variable_keys:
            raise ValueError(f"outputs.variables[{index}] contains unsupported keys: {extra_variable_keys}")
        missing_variable_keys = sorted(expected_variable_keys - set(raw_variable.keys()))
        if missing_variable_keys:
            raise ValueError(f"outputs.variables[{index}] is missing required keys: {missing_variable_keys}")
        name = _require_non_empty_string(raw_variable["name"], f"outputs.variables[{index}].name")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
            raise ValueError(f"outputs.variables[{index}].name must match ^[A-Za-z][A-Za-z0-9_]*$")
        if name in seen_names:
            raise ValueError(f"outputs.variables[{index}].name must be unique: {name}")
        expression = _require_non_empty_string(raw_variable["expression"], f"outputs.variables[{index}].expression")
        seen_names.add(name)
        variables.append({"name": name, "expression": expression})

    return {
        "report_name": _require_non_empty_string(outputs["report_name"], "outputs.report_name"),
        "solution_name": _require_non_empty_string(outputs["solution_name"], "outputs.solution_name"),
        "primary_sweep": _require_non_empty_string(outputs["primary_sweep"], "outputs.primary_sweep"),
        "report_category": _require_non_empty_string(outputs["report_category"], "outputs.report_category"),
        "plot_type": _require_non_empty_string(outputs["plot_type"], "outputs.plot_type"),
        "variables": variables,
    }


__all__ = ["_parse_outputs_spec", "_parse_simulation_policy"]

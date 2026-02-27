from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Literal, Mapping, cast

from peetsfea.identity.hashing import (
    compose_design_id,
    compute_design_unique_hash,
    compute_toml_hash,
    compute_toml_space_hash,
    get_git_commit,
)
from peetsfea.pipeline.package_export import export_design_zip
from peetsfea.spec.loader import TOMLTable, TOMLValue, load_toml_bytes, require_str, require_table
from peetsfea.spec.resolver import SelectionConstraintError, resolve_selection_with_context
from peetsfea.spec.resolver.constants import DERIVED_RANGE_PATHS
from peetsfea.spec.resolver.sampling import build_candidates as _build_candidates
from peetsfea.types.manifest import (
    DatasetSnapshot,
    EmPolicy,
    GroupGeometryParams,
    Manifest,
    ReproSnapshot,
    ResolvedCoilGroup,
    ResolvedPcbInstance,
    RunResult,
    SelectedParameters,
    SelectedParametersMax,
)

MAX_ATTEMPTS = 64
SUPPORTED_SPEC_VERSION = "0.2.7"


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


def _parse_simulation_policy(spec: Mapping[str, object]) -> EmPolicy:
    raw_simulation = spec.get("simulation")
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


def _collect_range_nodes(value: object) -> list[list[object]]:
    nodes: list[list[object]] = []
    if isinstance(value, dict):
        maybe_range = value.get("range")
        if isinstance(maybe_range, list):
            nodes.append(maybe_range)
        for child in value.values():
            nodes.extend(_collect_range_nodes(child))
    elif isinstance(value, list):
        for child in value:
            nodes.extend(_collect_range_nodes(child))
    return nodes


def _is_derived_dummy_range(entry: list[object]) -> bool:
    if len(entry) != 4:
        return False
    is_integer, start, end, count = entry
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


def _detect_repro_mode(spec: Mapping[str, object]) -> Literal["sampled_toml", "frozen_toml"]:
    range_nodes = _collect_range_nodes(spec)
    if not range_nodes:
        return "sampled_toml"
    for entry in range_nodes:
        if _is_derived_dummy_range(entry):
            continue
        if len(entry) != 4:
            return "sampled_toml"
        _, start, end, count = entry
        if count != 1 or start != end:
            return "sampled_toml"
    return "frozen_toml"


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
    return isinstance(value, list) and (len(value) == 0 or all(isinstance(item, dict) for item in value))


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


def _toml_dumps(table: TOMLTable) -> str:
    lines: list[str] = []
    _render_table(lines, table, None)
    return "\n".join(lines).strip() + "\n"


def _freeze_scalar_range(raw_range: list[TOMLValue], selected_value: int | float) -> list[TOMLValue]:
    is_integer = raw_range[0]
    if not isinstance(is_integer, bool):
        raise ValueError("range[0] must be bool")
    fixed_value: TOMLValue = int(selected_value) if is_integer else float(selected_value)
    return [is_integer, fixed_value, fixed_value, 1]


def _freeze_ranges_for_snapshot(
    spec: TOMLTable,
    selection_context: dict[str, int | float],
) -> TOMLTable:
    frozen = copy.deepcopy(spec)

    def visit(node: TOMLValue, path: str) -> None:
        if isinstance(node, dict):
            if set(node.keys()) == {"range"}:
                range_value = node.get("range")
                if isinstance(range_value, list) and len(range_value) == 4:
                    if path in DERIVED_RANGE_PATHS and _is_derived_dummy_range(cast(list[object], range_value)):
                        return
                    selected = selection_context.get(path)
                    if selected is not None:
                        node["range"] = _freeze_scalar_range(cast(list[TOMLValue], range_value), selected)
                        return
            for key, child in node.items():
                child_path = f"{path}.{key}" if path else key
                if isinstance(child, list) and len(child) == 4:
                    selected = selection_context.get(child_path)
                    if selected is not None:
                        node[key] = _freeze_scalar_range(cast(list[TOMLValue], child), selected)
                        continue
                visit(cast(TOMLValue, child), child_path)
            return
        if isinstance(node, list):
            for idx, item in enumerate(node):
                item_path = f"{path}[{idx}]" if path else f"[{idx}]"
                visit(cast(TOMLValue, item), item_path)

    visit(frozen, "")
    return frozen


def _collect_range_entries(value: TOMLValue, path: str = "") -> list[tuple[str, list[TOMLValue]]]:
    entries: list[tuple[str, list[TOMLValue]]] = []
    if isinstance(value, dict):
        if set(value.keys()) == {"range"}:
            raw_range = value.get("range")
            if isinstance(raw_range, list):
                entries.append((path, cast(list[TOMLValue], raw_range)))
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            entries.extend(_collect_range_entries(cast(TOMLValue, child), child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            child_path = f"{path}[{idx}]" if path else f"[{idx}]"
            entries.extend(_collect_range_entries(cast(TOMLValue, child), child_path))
    return entries


def _resolve_dataset_input_value(
    raw_range: list[TOMLValue],
    selected: int | float | None,
) -> TOMLValue | None:
    if len(raw_range) != 4:
        return None
    is_integer = raw_range[0]
    start = raw_range[1]
    end = raw_range[2]
    if not isinstance(is_integer, bool):
        return None
    if selected is not None:
        return int(selected) if is_integer else float(selected)
    if isinstance(start, bool) or isinstance(end, bool):
        return None
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
        return None
    if float(start) != float(end):
        return None
    return int(start) if is_integer else float(start)


def _build_dataset_spec(
    spec: TOMLTable,
    selection_context: dict[str, int | float],
    design_id: str,
) -> TOMLTable:
    input_parameters: list[TOMLValue] = []
    for path, raw_range in _collect_range_entries(spec):
        if len(raw_range) != 4:
            continue
        raw_count = raw_range[3]
        if isinstance(raw_count, bool) or not isinstance(raw_count, int):
            continue
        if raw_count == 2:
            continue
        if path in DERIVED_RANGE_PATHS and _is_derived_dummy_range(cast(list[object], raw_range)):
            continue
        value = _resolve_dataset_input_value(raw_range, selection_context.get(path))
        if value is None:
            continue
        input_parameters.append(cast(TOMLValue, {"path": path, "value": value}))

    input_parameters.sort(
        key=lambda item: cast(str, cast(dict[str, TOMLValue], item).get("path", ""))
    )
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


@dataclass(frozen=True)
class RunConfig:
    ansys_executable_path: str
    ansys_run_dir: str
    toml_path: str
    seed: int = 1
    backend: str = "hfss"
    non_graphical: bool = True
    close_on_exit: bool = True
    emit_manifest_json: bool = False
    emit_geometry_metadata_json: bool = False
    export_zip: bool = True


def run(config: RunConfig) -> RunResult:
    repo_dir = Path(__file__).resolve().parents[2]
    commit_hash = get_git_commit(repo_dir)

    if config.backend != "hfss":
        raise ValueError("Only backend='hfss' is supported in this MVP")

    toml_path = Path(config.toml_path)
    spec, raw_toml = load_toml_bytes(toml_path)

    spec_version = require_str(spec.get("spec_version"), "spec_version")
    if spec_version != SUPPORTED_SPEC_VERSION:
        raise ValueError(f"spec_version must be '{SUPPORTED_SPEC_VERSION}'")
    design = require_table(spec.get("design"), "design")
    units = require_str(design.get("units"), "design.units")
    raw_design_name = design.get("name")
    design_name = "pcb_design" if raw_design_name is None else require_str(raw_design_name, "design.name")

    backend = require_table(spec.get("backend"), "backend")
    backend_tool = require_str(backend.get("tool"), "backend.tool")
    if backend_tool != "hfss":
        raise ValueError("backend.tool must be 'hfss' for this MVP")
    simulation = _parse_simulation_policy(spec)
    repro_mode = cast(Literal["sampled_toml", "frozen_toml"], _detect_repro_mode(spec))

    selected_parameters: SelectedParameters | None = None
    selected_parameters_max: SelectedParametersMax | None = None
    selected_coil_groups: list[ResolvedCoilGroup] | None = None
    selected_group_geometry: list[GroupGeometryParams] | None = None
    selected_pcbs: list[ResolvedPcbInstance] | None = None
    selection_context: dict[str, int | float] | None = None
    retry_attempt = 0
    retry_count = 0
    last_error = ""
    for attempt in range(MAX_ATTEMPTS):
        try:
            (
                selected_parameters,
                selected_parameters_max,
                selected_coil_groups,
                selected_group_geometry,
                selected_pcbs,
                selection_context,
            ) = resolve_selection_with_context(spec=spec, seed=config.seed, attempt=attempt)
            retry_attempt = attempt
            retry_count = attempt
            break
        except SelectionConstraintError as exc:
            last_error = str(exc)
            continue

    if (
        selected_parameters is None
        or selected_parameters_max is None
        or selected_coil_groups is None
        or selected_group_geometry is None
        or selected_pcbs is None
        or selection_context is None
    ):
        raise RuntimeError(
            "No valid selection within max attempts "
            f"(seed={config.seed}, max_attempts={MAX_ATTEMPTS}, last_error={last_error})"
        )

    toml_hash = compute_toml_hash(raw_toml)
    toml_space_hash = compute_toml_space_hash(toml_hash)
    design_unique_hash = compute_design_unique_hash(
        toml_hash, commit_hash, selected_parameters, selected_group_geometry, selected_coil_groups, selected_pcbs
    )
    design_id = compose_design_id(design_unique_hash, toml_space_hash, config.seed, retry_attempt)

    repro_spec = _freeze_ranges_for_snapshot(spec, selection_context)
    dataset_spec = _build_dataset_spec(spec, selection_context, design_id)

    source_toml_bytes = raw_toml
    repro_snapshot: ReproSnapshot = {"toml_bytes": _toml_dumps(repro_spec).encode("utf-8")}
    dataset_snapshot: DatasetSnapshot = {"toml_bytes": _toml_dumps(dataset_spec).encode("utf-8")}

    output_dir = Path(config.ansys_run_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_output_path = output_dir / f"manifest_{design_id}.json"
    geometry_metadata_output_path = output_dir / f"geometry_metadata_{design_id}.json"
    manifest_path_str = str(manifest_output_path) if config.emit_manifest_json else None
    geometry_metadata_path_str = str(geometry_metadata_output_path) if config.emit_geometry_metadata_json else None
    aedt_output_path = output_dir / f"{design_id}.aedt"
    zip_path_str: str | None = None
    manifest: Manifest = {
        "design_id": design_id,
        "design_unique_hash": design_unique_hash,
        "toml_space_hash": toml_space_hash,
        "toml_hash": toml_hash,
        "peetsfea_commit": commit_hash,
        "seed": config.seed,
        "retry_attempt": retry_attempt,
        "retry_count": retry_count,
        "repro_mode": repro_mode,  # sampled_toml | frozen_toml
        "backend": config.backend,
        "selected_parameters": selected_parameters,
        "selected_parameters_max": selected_parameters_max,
        "selected_coil_groups": selected_coil_groups,
        "selected_group_geometry": selected_group_geometry,
        "selected_pcbs": selected_pcbs,
        "inputs": {
            "ansys_executable_path": config.ansys_executable_path,
            "ansys_run_dir": config.ansys_run_dir,
            "toml_path": config.toml_path,
            "non_graphical": config.non_graphical,
            "close_on_exit": config.close_on_exit,
            "emit_manifest_json": config.emit_manifest_json,
            "emit_geometry_metadata_json": config.emit_geometry_metadata_json,
        },
        "spec": {
            "spec_version": spec_version,
            "design_name": design_name,
            "units": units,
            "simulation": simulation,
        },
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "manifest_path": manifest_path_str,
    }

    if config.emit_manifest_json:
        manifest_output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if config.export_zip and aedt_output_path.exists():
        zip_path = export_design_zip(
            design_id=design_id,
            aedt_path=aedt_output_path,
            repro_toml=repro_snapshot["toml_bytes"],
            dataset_toml=dataset_snapshot["toml_bytes"],
            source_toml=source_toml_bytes,
            output_dir=output_dir,
        )
        zip_path_str = str(zip_path)
    return {
        "manifest": manifest,
        "source_toml_bytes": source_toml_bytes,
        "repro_snapshot": repro_snapshot,
        "dataset_snapshot": dataset_snapshot,
        "manifest_path": manifest_path_str,
        "geometry_metadata_path": geometry_metadata_path_str,
        "zip_path": zip_path_str,
    }


__all__ = ["RunConfig", "run"]

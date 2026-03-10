from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Mapping, cast

from peetsfea.identity.hashing import (
    compose_design_id,
    compute_design_unique_hash,
    compute_toml_hash,
    compute_toml_space_hash,
    get_git_commit,
)
from peetsfea.pipeline.selection_snapshots import (
    build_dataset_spec,
    detect_repro_mode,
    freeze_ranges_for_snapshot,
    toml_dumps,
)
from peetsfea.spec.loader import TOMLTable, load_toml_bytes, require_str, require_table
from peetsfea.spec.resolver import SelectionConstraintError, resolve_selection_result
from peetsfea.spec.resolver.sampling import SamplingLedger, build_candidates as _build_candidates
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
SUPPORTED_SPEC_VERSION = "0.2.13"


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


def _select_feasible_result(
    spec: TOMLTable,
    *,
    seed: int,
) -> tuple[
    SelectedParameters,
    SelectedParametersMax,
    list[ResolvedCoilGroup],
    list[GroupGeometryParams],
    list[ResolvedPcbInstance],
    SamplingLedger,
    int,
    int,
]:
    selected_parameters: SelectedParameters | None = None
    selected_parameters_max: SelectedParametersMax | None = None
    selected_coil_groups: list[ResolvedCoilGroup] | None = None
    selected_group_geometry: list[GroupGeometryParams] | None = None
    selected_pcbs: list[ResolvedPcbInstance] | None = None
    sampling_ledger: SamplingLedger | None = None
    retry_attempt = 0
    retry_count = 0
    last_error = ""
    for attempt in range(MAX_ATTEMPTS):
        try:
            result = resolve_selection_result(spec=spec, seed=seed, attempt=attempt)
            selected_parameters = result.selected_parameters
            selected_parameters_max = result.selected_parameters_max
            selected_coil_groups = result.selected_coil_groups
            selected_group_geometry = result.selected_group_geometry
            selected_pcbs = result.selected_pcbs
            sampling_ledger = result.sampling_ledger
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
        or sampling_ledger is None
    ):
        raise RuntimeError(
            "No valid selection within max attempts "
            f"(seed={seed}, max_attempts={MAX_ATTEMPTS}, last_error={last_error})"
        )

    return (
        selected_parameters,
        selected_parameters_max,
        selected_coil_groups,
        selected_group_geometry,
        selected_pcbs,
        sampling_ledger,
        retry_attempt,
        retry_count,
    )


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
    repro_mode = detect_repro_mode(spec)
    (
        selected_parameters,
        selected_parameters_max,
        selected_coil_groups,
        selected_group_geometry,
        selected_pcbs,
        sampling_ledger,
        retry_attempt,
        retry_count,
    ) = _select_feasible_result(spec, seed=config.seed)

    source_toml_hash = compute_toml_hash(raw_toml)
    repro_spec = freeze_ranges_for_snapshot(spec, sampling_ledger)
    repro_toml_bytes = toml_dumps(repro_spec).encode("utf-8")
    toml_hash = source_toml_hash
    toml_space_hash = compute_toml_space_hash(source_toml_hash)
    design_unique_hash = compute_design_unique_hash(
        source_toml_hash, commit_hash, selected_parameters, selected_group_geometry, selected_coil_groups, selected_pcbs
    )
    design_id = compose_design_id(design_unique_hash, toml_space_hash, config.seed, retry_attempt)
    dataset_spec = build_dataset_spec(spec, sampling_ledger, design_id, repro_mode)

    source_toml_bytes = raw_toml
    repro_snapshot: ReproSnapshot = {"toml_bytes": repro_toml_bytes}
    dataset_snapshot: DatasetSnapshot = {"toml_bytes": toml_dumps(dataset_spec).encode("utf-8")}

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
    # Zip export is temporarily disabled while keeping config/type compatibility.
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

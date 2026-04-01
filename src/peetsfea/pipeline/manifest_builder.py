from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from peetsfea.identity.hashing import compose_design_id, compute_design_unique_hash, compute_toml_hash, compute_toml_space_hash
from peetsfea.pipeline.selection.selection_snapshots import build_dataset_spec, freeze_ranges_for_snapshot, toml_dumps
from peetsfea.spec.loader import TOMLTable
from peetsfea.spec.resolver.sampling import SamplingLedger
from peetsfea.types.manifest import (
    DatasetSnapshot,
    EmPolicy,
    GroupGeometryParams,
    Manifest,
    OutputsSpec,
    ReproSnapshot,
    ResolvedCoilGroup,
    ResolvedPcbInstance,
    RunResult,
    SelectedParameters,
    SelectedParametersMax,
)


def build_run_result(
    *,
    spec: TOMLTable,
    raw_toml: bytes,
    commit_hash: str,
    config_backend: str,
    ansys_executable_path: str,
    ansys_run_dir: str,
    toml_path: str,
    non_graphical: bool,
    close_on_exit: bool,
    emit_manifest_json: bool,
    emit_geometry_metadata_json: bool,
    spec_version: str,
    design_name: str,
    units: str,
    simulation: EmPolicy,
    outputs: OutputsSpec,
    repro_mode: Literal["sampled_toml", "frozen_toml"],
    selected_parameters: SelectedParameters,
    selected_parameters_max: SelectedParametersMax,
    selected_coil_groups: list[ResolvedCoilGroup],
    selected_group_geometry: list[GroupGeometryParams],
    selected_pcbs: list[ResolvedPcbInstance],
    sampling_ledger: SamplingLedger,
    seed: int,
    retry_attempt: int,
    retry_count: int,
) -> RunResult:
    source_toml_hash = compute_toml_hash(raw_toml)
    repro_spec = freeze_ranges_for_snapshot(spec, sampling_ledger)
    repro_toml_bytes = toml_dumps(repro_spec).encode("utf-8")
    toml_hash = source_toml_hash
    toml_space_hash = compute_toml_space_hash(source_toml_hash)
    design_unique_hash = compute_design_unique_hash(
        source_toml_hash,
        commit_hash,
        selected_parameters,
        selected_group_geometry,
        selected_coil_groups,
        selected_pcbs,
    )
    design_id = compose_design_id(design_unique_hash, toml_space_hash, seed, retry_attempt)
    dataset_spec = build_dataset_spec(spec, sampling_ledger, design_id, repro_mode)

    source_toml_bytes = raw_toml
    repro_snapshot: ReproSnapshot = {"toml_bytes": repro_toml_bytes}
    dataset_snapshot: DatasetSnapshot = {"toml_bytes": toml_dumps(dataset_spec).encode("utf-8")}

    output_dir = Path(ansys_run_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_output_path = output_dir / f"manifest_{design_id}.json"
    geometry_metadata_output_path = output_dir / f"geometry_metadata_{design_id}.json"
    manifest_path_str = str(manifest_output_path) if emit_manifest_json else None
    geometry_metadata_path_str = str(geometry_metadata_output_path) if emit_geometry_metadata_json else None
    manifest: Manifest = {
        "design_id": design_id,
        "design_unique_hash": design_unique_hash,
        "toml_space_hash": toml_space_hash,
        "toml_hash": toml_hash,
        "peetsfea_commit": commit_hash,
        "seed": seed,
        "retry_attempt": retry_attempt,
        "retry_count": retry_count,
        "repro_mode": repro_mode,
        "backend": config_backend,
        "selected_parameters": selected_parameters,
        "selected_parameters_max": selected_parameters_max,
        "selected_coil_groups": selected_coil_groups,
        "selected_group_geometry": selected_group_geometry,
        "selected_pcbs": selected_pcbs,
        "inputs": {
            "ansys_executable_path": ansys_executable_path,
            "ansys_run_dir": ansys_run_dir,
            "toml_path": toml_path,
            "source_toml_path": toml_path,
            "non_graphical": non_graphical,
            "close_on_exit": close_on_exit,
            "emit_manifest_json": emit_manifest_json,
            "emit_geometry_metadata_json": emit_geometry_metadata_json,
        },
        "spec": {
            "spec_version": spec_version,
            "design_name": design_name,
            "units": units,
            "simulation": simulation,
            "outputs": outputs,
        },
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "manifest_path": manifest_path_str,
    }
    return {
        "manifest": manifest,
        "source_toml_bytes": source_toml_bytes,
        "repro_snapshot": repro_snapshot,
        "dataset_snapshot": dataset_snapshot,
        "manifest_path": manifest_path_str,
        "geometry_metadata_path": geometry_metadata_path_str,
        "zip_path": None,
    }


__all__ = ["build_run_result"]

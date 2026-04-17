from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from peetsfea.identity.hashing import get_git_commit
from peetsfea.legacy.type1.pipeline.manifest_builder import build_run_result
from peetsfea.legacy.type1.pipeline.selection.selection_runner import _select_feasible_result
from peetsfea.legacy.type1.pipeline.selection.selection_snapshots import detect_repro_mode
from peetsfea.legacy.type1.pipeline.selection.spec_contract import _parse_outputs_spec, _parse_simulation_policy
from peetsfea.spec.loader import load_toml_bytes, require_str, require_table
from peetsfea.types.manifest import RunResult
from peetsfea.version import SUPPORTED_SPEC_VERSION

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
    repo_dir = Path(__file__).resolve().parents[5]
    commit_hash = get_git_commit(repo_dir)

    if config.backend != "hfss":
        raise ValueError("Only backend='hfss' is supported in this MVP")

    toml_path = Path(config.toml_path)
    if len(toml_path.stem) > 30:
        raise ValueError("TOML basename must be <= 30 characters")
    spec, raw_toml = load_toml_bytes(toml_path)

    assert "spec_version" in spec, "spec must contain spec_version"
    spec_version = require_str(spec["spec_version"], "spec_version")
    if spec_version != SUPPORTED_SPEC_VERSION:
        raise ValueError(f"spec_version must be '{SUPPORTED_SPEC_VERSION}'")
    assert "design" in spec, "spec must contain design"
    design = require_table(spec["design"], "design")
    assert "units" in design, "design must contain units"
    units = require_str(design["units"], "design.units")
    design_name = "pcb_design"
    if "name" in design:
        design_name = require_str(design["name"], "design.name")

    assert "backend" in spec, "spec must contain backend"
    backend = require_table(spec["backend"], "backend")
    assert "tool" in backend, "backend must contain tool"
    backend_tool = require_str(backend["tool"], "backend.tool")
    if backend_tool != "hfss":
        raise ValueError("backend.tool must be 'hfss' for this MVP")
    simulation = _parse_simulation_policy(spec)
    outputs = _parse_outputs_spec(spec)
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

    result = build_run_result(
        spec=spec,
        raw_toml=raw_toml,
        commit_hash=commit_hash,
        config_backend=config.backend,
        ansys_executable_path=config.ansys_executable_path,
        ansys_run_dir=config.ansys_run_dir,
        toml_path=config.toml_path,
        non_graphical=config.non_graphical,
        close_on_exit=config.close_on_exit,
        emit_manifest_json=config.emit_manifest_json,
        emit_geometry_metadata_json=config.emit_geometry_metadata_json,
        spec_version=spec_version,
        design_name=design_name,
        units=units,
        simulation=simulation,
        outputs=outputs,
        repro_mode=repro_mode,
        selected_parameters=selected_parameters,
        selected_parameters_max=selected_parameters_max,
        selected_coil_groups=selected_coil_groups,
        selected_group_geometry=selected_group_geometry,
        selected_pcbs=selected_pcbs,
        sampling_ledger=sampling_ledger,
        seed=config.seed,
        retry_attempt=retry_attempt,
        retry_count=retry_count,
    )
    if config.emit_manifest_json:
        manifest_path = result["manifest_path"]
        if not isinstance(manifest_path, str):
            raise ValueError("emit_manifest_json requires result.manifest_path to be a string path")
        Path(manifest_path).write_text(json.dumps(result["manifest"], ensure_ascii=False, indent=2), encoding="utf-8")
    return result


__all__ = ["RunConfig", "run"]

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from peetsfea.identity.hashing import compute_design_id, compute_toml_hash, get_git_commit
from peetsfea.spec.loader import load_toml_bytes, require_str, require_table
from peetsfea.spec.resolver import _build_candidates, resolve_selected_parameters
from peetsfea.types.manifest import Manifest


@dataclass(frozen=True)
class RunConfig:
    ansys_executable_path: str
    ansys_run_dir: str
    toml_path: str
    seed: int = 1
    backend: str = "hfss"
    non_graphical: bool = True
    close_on_exit: bool = True


def run(config: RunConfig) -> Manifest:
    repo_dir = Path(__file__).resolve().parents[2]
    commit_hash = get_git_commit(repo_dir)

    if config.backend != "hfss":
        raise ValueError("Only backend='hfss' is supported in this MVP")

    toml_path = Path(config.toml_path)
    spec, raw_toml = load_toml_bytes(toml_path)

    spec_version = require_str(spec.get("spec_version"), "spec_version")
    design = require_table(spec.get("design"), "design")
    design_name = require_str(design.get("name"), "design.name")
    units = require_str(design.get("units"), "design.units")
    backend = require_table(spec.get("backend"), "backend")
    backend_tool = require_str(backend.get("tool"), "backend.tool")
    if backend_tool != "hfss":
        raise ValueError("backend.tool must be 'hfss' for this MVP")

    selected_parameters = resolve_selected_parameters(spec=spec, seed=config.seed)
    toml_hash = compute_toml_hash(raw_toml)
    design_id = compute_design_id(toml_hash, commit_hash, config.seed, selected_parameters)

    manifest: Manifest = {
        "design_id": design_id,
        "toml_hash": toml_hash,
        "peetsfea_commit": commit_hash,
        "seed": config.seed,
        "backend": config.backend,
        "selected_parameters": selected_parameters,
        "inputs": {
            "ansys_executable_path": config.ansys_executable_path,
            "ansys_run_dir": config.ansys_run_dir,
            "toml_path": config.toml_path,
            "non_graphical": config.non_graphical,
            "close_on_exit": config.close_on_exit,
        },
        "spec": {
            "spec_version": spec_version,
            "design_name": design_name,
            "units": units,
        },
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }

    output_path = Path.cwd() / f"manifest_{design_id}.json"
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(output_path)
    return manifest


__all__ = ["RunConfig", "run", "_build_candidates"]

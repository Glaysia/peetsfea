from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Literal, Mapping, cast

from peetsfea.identity.hashing import (
    compose_design_id,
    compute_design_unique_hash,
    compute_toml_hash,
    compute_toml_space_hash,
    get_git_commit,
)
from peetsfea.spec.loader import load_toml_bytes, require_str, require_table
from peetsfea.spec.resolver import SelectionConstraintError, resolve_selection
from peetsfea.spec.resolver.sampling import build_candidates as _build_candidates
from peetsfea.types.manifest import (
    GroupGeometryParams,
    Manifest,
    ResolvedCoilGroup,
    ResolvedPcbInstance,
    SelectedParameters,
    SelectedParametersMax,
)

MAX_ATTEMPTS = 64
SUPPORTED_SPEC_VERSION = "0.2.5"


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
    repro_mode = cast(Literal["sampled_toml", "frozen_toml"], _detect_repro_mode(spec))

    selected_parameters: SelectedParameters | None = None
    selected_parameters_max: SelectedParametersMax | None = None
    selected_coil_groups: list[ResolvedCoilGroup] | None = None
    selected_group_geometry: list[GroupGeometryParams] | None = None
    selected_pcbs: list[ResolvedPcbInstance] | None = None
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
            ) = resolve_selection(spec=spec, seed=config.seed, attempt=attempt)
            retry_attempt = attempt
            retry_count = attempt
            break
        except SelectionConstraintError as exc:
            last_error = str(exc)
            continue

    if selected_parameters is None or selected_parameters_max is None or selected_coil_groups is None or selected_group_geometry is None or selected_pcbs is None:
        raise RuntimeError(
            "No valid selection within max attempts "
            f"(seed={config.seed}, max_attempts={MAX_ATTEMPTS}, last_error={last_error})"
        )
    assert selected_parameters is not None
    assert selected_parameters_max is not None
    assert selected_coil_groups is not None
    assert selected_group_geometry is not None
    assert selected_pcbs is not None
    toml_hash = compute_toml_hash(raw_toml)
    toml_space_hash = compute_toml_space_hash(toml_hash)
    design_unique_hash = compute_design_unique_hash(
        toml_hash, commit_hash, selected_parameters, selected_group_geometry, selected_coil_groups, selected_pcbs
    )
    design_id = compose_design_id(design_unique_hash, toml_space_hash, config.seed, retry_attempt)

    output_dir = Path(config.ansys_run_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"manifest_{design_id}.json"
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
        },
        "spec": {
            "spec_version": spec_version,
            "design_name": design_name,
            "units": units,
        },
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "manifest_path": str(output_path),
    }

    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


__all__ = ["RunConfig", "run"]

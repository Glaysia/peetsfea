from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance, SelectedParameters


def _require_lower_hex(value: str, expected_len: int, field_name: str) -> None:
    if len(value) != expected_len:
        raise ValueError(f"{field_name} must be {expected_len} hex chars")
    allowed = set("0123456789abcdef")
    if any(char not in allowed for char in value):
        raise ValueError(f"{field_name} must be lowercase hex")


def get_git_commit(repo_dir: Path) -> str:
    try:
        commit_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Failed to read git commit hash with 'git rev-parse HEAD'") from exc

    commit = commit_proc.stdout.strip()
    if len(commit) != 40:
        raise RuntimeError(f"Expected 40-char git commit hash, got: {commit!r}")
    return commit


def compute_toml_hash(raw_toml: bytes) -> str:
    return hashlib.sha256(raw_toml).hexdigest()


def compute_toml_space_hash(toml_hash: str) -> str:
    _require_lower_hex(toml_hash, 64, "toml_hash")
    return toml_hash[:8]


def compute_design_unique_hash(
    toml_hash: str,
    commit_hash: str,
    selected_parameters: SelectedParameters,
    selected_group_geometry: list[GroupGeometryParams],
    selected_coil_groups: list[ResolvedCoilGroup],
    selected_pcbs: list[ResolvedPcbInstance],
) -> str:
    selected_json = json.dumps(selected_parameters, sort_keys=True, separators=(",", ":"))
    selected_group_geometry_json = json.dumps(selected_group_geometry, sort_keys=True, separators=(",", ":"))
    selected_coil_groups_json = json.dumps(selected_coil_groups, sort_keys=True, separators=(",", ":"))
    selected_pcbs_json = json.dumps(selected_pcbs, sort_keys=True, separators=(",", ":"))
    identity_base = f"{toml_hash}:{commit_hash}:{selected_json}:{selected_group_geometry_json}:{selected_coil_groups_json}:{selected_pcbs_json}"
    return hashlib.sha256(identity_base.encode("utf-8")).hexdigest()[:8]


def compose_design_id(unique_hash: str, toml_space_hash: str, seed: int, attempt: int) -> str:
    _require_lower_hex(unique_hash, 8, "unique_hash")
    _require_lower_hex(toml_space_hash, 8, "toml_space_hash")
    return f"{seed}_{unique_hash}_{toml_space_hash}_{attempt}"

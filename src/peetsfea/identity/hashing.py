from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from peetsfea.types.manifest import SelectedParameters


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


def compute_design_id(toml_hash: str, commit_hash: str, seed: int, selected_parameters: SelectedParameters) -> str:
    selected_json = json.dumps(selected_parameters, sort_keys=True, separators=(",", ":"))
    identity_base = f"{toml_hash}:{commit_hash}:{seed}:{selected_json}"
    return hashlib.sha256(identity_base.encode("utf-8")).hexdigest()[:8]

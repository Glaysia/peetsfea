from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tomllib
from typing import Any


@dataclass(frozen=True)
class RunConfig:
    ansys_executable_path: str
    ansys_run_dir: str
    toml_path: str
    seed: int = 1
    backend: str = "hfss"


def _load_toml_bytes(path: Path) -> tuple[dict[str, Any], bytes]:
    if not path.exists():
        raise FileNotFoundError(f"TOML file not found: {path}")
    raw = path.read_bytes()
    try:
        parsed = tomllib.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError(f"TOML must be UTF-8: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid TOML format: {path}") from exc
    return parsed, raw


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a table/object")
    return value


def _require_str(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value


def _parse_range(spec: dict[str, Any]) -> tuple[bool, float, float, int]:
    parameters = _require_dict(spec.get("parameters"), "parameters")
    coil1_turns = _require_dict(parameters.get("coil1_turns"), "parameters.coil1_turns")
    raw_range = coil1_turns.get("range")
    if not isinstance(raw_range, list) or len(raw_range) != 4:
        raise ValueError("parameters.coil1_turns.range must be [is_integer, start, end, count]")

    is_integer, start, end, count = raw_range

    if not isinstance(is_integer, bool):
        raise ValueError("range[0] (is_integer) must be bool")
    if isinstance(start, bool) or not isinstance(start, (int, float)):
        raise ValueError("range[1] (start) must be number")
    if isinstance(end, bool) or not isinstance(end, (int, float)):
        raise ValueError("range[2] (end) must be number")
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("range[3] (count) must be int")
    if count < 1:
        raise ValueError("range[3] (count) must be >= 1")
    if end < start:
        raise ValueError("range[2] (end) must be >= range[1] (start)")

    return is_integer, float(start), float(end), count


def _build_candidates(is_integer: bool, start: float, end: float, count: int) -> list[int | float]:
    if count == 1:
        raw_values = [start]
    else:
        step = (end - start) / (count - 1)
        raw_values = [start + (step * i) for i in range(count)]

    if not is_integer:
        return raw_values

    rounded = [int(math.floor(value + 0.5)) for value in raw_values]
    deduped: list[int] = []
    seen: set[int] = set()
    for value in rounded:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped


def _get_git_commit_and_dirty(repo_dir: Path) -> tuple[str, bool]:
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

    status_proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    is_dirty = bool(status_proc.stdout.strip())
    return commit, is_dirty


def run(config: RunConfig) -> dict[str, Any]:
    repo_dir = Path(__file__).resolve().parents[2]
    commit_hash, is_dirty = _get_git_commit_and_dirty(repo_dir)
    if is_dirty:
        raise RuntimeError("Git working tree is dirty. Commit or stash changes before running.")

    if config.backend != "hfss":
        raise ValueError("Only backend='hfss' is supported in this MVP")

    toml_path = Path(config.toml_path)
    spec, raw_toml = _load_toml_bytes(toml_path)

    spec_version = _require_str(spec.get("spec_version"), "spec_version")
    design = _require_dict(spec.get("design"), "design")
    design_name = _require_str(design.get("name"), "design.name")
    units = _require_str(design.get("units"), "design.units")
    backend = _require_dict(spec.get("backend"), "backend")
    backend_tool = _require_str(backend.get("tool"), "backend.tool")
    if backend_tool != "hfss":
        raise ValueError("backend.tool must be 'hfss' for this MVP")

    is_integer, start, end, count = _parse_range(spec)
    candidates = _build_candidates(is_integer=is_integer, start=start, end=end, count=count)
    if not candidates:
        raise ValueError("No candidates generated from parameters.coil1_turns.range")

    selected_index = config.seed % len(candidates)
    selected_turns = candidates[selected_index]

    toml_hash = hashlib.sha256(raw_toml).hexdigest()
    identity_base = f"{toml_hash}:{commit_hash}:{config.seed}:{selected_turns}"
    design_hash = hashlib.sha256(identity_base.encode("utf-8")).hexdigest()
    design_id = design_hash[:8]

    manifest: dict[str, Any] = {
        "design_id": design_id,
        "toml_hash": toml_hash,
        "peetsfea_commit": commit_hash,
        "seed": config.seed,
        "backend": config.backend,
        "selected_parameters": {"coil1_turns": selected_turns},
        "inputs": {
            "ansys_executable_path": config.ansys_executable_path,
            "ansys_run_dir": config.ansys_run_dir,
            "toml_path": config.toml_path,
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
    return manifest

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from build import build_from_manifest_path

cwd = Path(__file__).parent.resolve()
RUN_TOML_ROOT = cwd / "run" / "toml"
_BATCH_DIR_PATTERN = re.compile(r"^toml_(?P<version>.+)_(?P<seed_start>\d+)$")


@dataclass(frozen=True)
class BuildTarget:
    manifest_path: Path
    ansys_run_dir: Path


def _build_target_for_manifest(manifest_path: Path) -> BuildTarget | None:
    parent_name = manifest_path.parent.name
    match = _BATCH_DIR_PATTERN.match(parent_name)
    if match is None:
        print(f"[multi_build] skip manifest with unsupported parent dir: {manifest_path}")
        return None
    version = match.group("version")
    seed_start = match.group("seed_start")
    ansys_run_dir = cwd / "run" / "aedt" / f"aedt_{version}_{seed_start}"
    return BuildTarget(manifest_path=manifest_path, ansys_run_dir=ansys_run_dir)


def discover_build_targets(run_toml_root: Path = RUN_TOML_ROOT) -> tuple[BuildTarget, ...]:
    manifests = sorted(path for path in run_toml_root.glob("**/manifest.json") if path.parent != run_toml_root)
    targets: list[BuildTarget] = []
    for manifest_path in manifests:
        target = _build_target_for_manifest(manifest_path)
        if target is not None:
            targets.append(target)
    if not targets:
        raise ValueError(f"No batch manifests found under {run_toml_root}")
    return tuple(targets)


def build_all_targets(targets: tuple[BuildTarget, ...] | None = None) -> list[list[bool]]:
    resolved_targets = targets if targets is not None else discover_build_targets()
    results: list[list[bool]] = []
    for target in resolved_targets:
        print(f"[multi_build] start manifest={target.manifest_path} ansys_run_dir={target.ansys_run_dir}")
        target_results = build_from_manifest_path(
            target.manifest_path,
            ansys_run_dir=target.ansys_run_dir,
        )
        print(f"[multi_build] completed manifest={target.manifest_path} count={len(target_results)}")
        results.append(target_results)
    return results


if __name__ == "__main__":
    build_all_targets()

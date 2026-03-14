from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from peetsfea import __version__
from peetsfea.pipeline.run_batch import (
    SampleManifestEntry,
    build_aedt_from_manifest_entry,
    load_sample_manifest,
)

cwd = Path(__file__).parent.resolve()


ANSYS_EXECUTABLE_PATH = "/opt/ansys_inc/v252/AnsysEM"
DEFAULT_BUILD_SEED_START = 0
BUILD_WORKER_COUNT = 12


def default_sample_manifest_path_for_seed_start(seed_start: int, *, workspace_root: Path = cwd) -> Path:
    return workspace_root / "run" / "toml" / f"toml_{__version__}_{seed_start}" / "manifest.json"


def default_ansys_run_dir_for_seed_start(seed_start: int, *, workspace_root: Path = cwd) -> Path:
    return workspace_root / "run" / "aedt" / f"aedt_{__version__}_{seed_start}"


DEFAULT_SAMPLE_MANIFEST_PATH = default_sample_manifest_path_for_seed_start(DEFAULT_BUILD_SEED_START)
DEFAULT_ANSYS_RUN_DIR = default_ansys_run_dir_for_seed_start(DEFAULT_BUILD_SEED_START)


def _is_debug_enabled() -> bool:
    return os.environ.get("PEETSFEA_DEBUG") == "1"


def _build_entry(entry: SampleManifestEntry, *, ansys_run_dir: Path, is_debug: bool) -> bool:
    return build_aedt_from_manifest_entry(
        entry=entry,
        ansys_run_dir=ansys_run_dir,
        ansys_executable_path=ANSYS_EXECUTABLE_PATH,
        is_debug=is_debug,
    )


def _build_worker(task: tuple[SampleManifestEntry, Path]) -> bool:
    entry, ansys_run_dir = task
    return _build_entry(entry, ansys_run_dir=ansys_run_dir, is_debug=False)


def build_from_manifest_path(
    manifest_path: Path = DEFAULT_SAMPLE_MANIFEST_PATH,
    *,
    ansys_run_dir: Path = DEFAULT_ANSYS_RUN_DIR,
) -> list[bool]:
    entries = load_sample_manifest(manifest_path)
    is_debug = _is_debug_enabled()
    if is_debug or BUILD_WORKER_COUNT <= 1:
        return [_build_entry(entry, ansys_run_dir=ansys_run_dir, is_debug=is_debug) for entry in entries]

    tasks = [(entry, ansys_run_dir) for entry in entries]
    with ProcessPoolExecutor(max_workers=BUILD_WORKER_COUNT) as executor:
        return list(executor.map(_build_worker, tasks))


if __name__ == "__main__":
    build_from_manifest_path()

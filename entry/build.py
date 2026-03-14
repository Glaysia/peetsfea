from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from peetsfea import __version__
from peetsfea.pipeline.run_batch import (
    SampleManifestEntry,
    build_aedt_from_manifest_entry_with_options,
    load_sample_manifest,
)

cwd = Path(__file__).resolve().parents[1]


ANSYS_EXECUTABLE_PATH = "/opt/ansys_inc/v252/AnsysEM"
DEFAULT_BUILD_SEED_START = 0
BUILD_WORKER_COUNT = 12


@dataclass(frozen=True)
class BuildRuntime:
    non_graphical: bool
    close_on_exit: bool


DEFAULT_BUILD_RUNTIME = BuildRuntime(non_graphical=True, close_on_exit=True)
DEBUG_BUILD_RUNTIME = BuildRuntime(non_graphical=False, close_on_exit=False)
GUI_VISIBLE_BUILD_RUNTIME = BuildRuntime(non_graphical=False, close_on_exit=True)


def default_sample_manifest_path_for_seed_start(seed_start: int, *, workspace_root: Path = cwd) -> Path:
    return workspace_root / "run" / "toml" / f"toml_{__version__}_{seed_start}" / "manifest.json"


def default_ansys_run_dir_for_seed_start(seed_start: int, *, workspace_root: Path = cwd) -> Path:
    return workspace_root / "run" / "aedt" / f"aedt_{__version__}_{seed_start}"


DEFAULT_SAMPLE_MANIFEST_PATH = default_sample_manifest_path_for_seed_start(DEFAULT_BUILD_SEED_START)
DEFAULT_ANSYS_RUN_DIR = default_ansys_run_dir_for_seed_start(DEFAULT_BUILD_SEED_START)


def _is_debug_enabled() -> bool:
    return os.environ.get("PEETSFEA_DEBUG") == "1"


def _default_runtime() -> BuildRuntime:
    if _is_debug_enabled():
        return DEBUG_BUILD_RUNTIME
    return DEFAULT_BUILD_RUNTIME


def _build_entry(entry: SampleManifestEntry, *, ansys_run_dir: Path, runtime: BuildRuntime) -> bool:
    return build_aedt_from_manifest_entry_with_options(
        entry=entry,
        ansys_run_dir=ansys_run_dir,
        ansys_executable_path=ANSYS_EXECUTABLE_PATH,
        non_graphical=runtime.non_graphical,
        close_on_exit=runtime.close_on_exit,
    )


def _build_worker(task: tuple[SampleManifestEntry, Path, BuildRuntime]) -> bool:
    entry, ansys_run_dir, runtime = task
    return _build_entry(entry, ansys_run_dir=ansys_run_dir, runtime=runtime)


def build_entries(
    entries: list[SampleManifestEntry],
    *,
    ansys_run_dir: Path,
    runtime: BuildRuntime | None = None,
    parallel: bool | None = None,
    max_workers: int | None = None,
) -> list[bool]:
    if not entries:
        return []

    resolved_runtime = runtime or _default_runtime()
    should_parallel = parallel if parallel is not None else resolved_runtime == DEFAULT_BUILD_RUNTIME
    if resolved_runtime.non_graphical is False:
        should_parallel = False

    worker_count = max_workers or BUILD_WORKER_COUNT
    if not should_parallel or worker_count <= 1:
        return [_build_entry(entry, ansys_run_dir=ansys_run_dir, runtime=resolved_runtime) for entry in entries]

    tasks = [(entry, ansys_run_dir, resolved_runtime) for entry in entries]
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        return list(executor.map(_build_worker, tasks))


def build_from_manifest_path(
    manifest_path: Path = DEFAULT_SAMPLE_MANIFEST_PATH,
    *,
    ansys_run_dir: Path = DEFAULT_ANSYS_RUN_DIR,
    runtime: BuildRuntime | None = None,
    parallel: bool | None = None,
    max_workers: int | None = None,
) -> list[bool]:
    entries = load_sample_manifest(manifest_path)
    return build_entries(
        entries,
        ansys_run_dir=ansys_run_dir,
        runtime=runtime,
        parallel=parallel,
        max_workers=max_workers,
    )


if __name__ == "__main__":
    build_from_manifest_path()

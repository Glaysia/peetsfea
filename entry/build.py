from __future__ import annotations

import os
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.pipeline.run_batch import (
    SampleManifestEntry,
    build_aedt_from_manifest_entry_with_options,
    load_sample_manifest,
)
from peetsfea.console_log import error, info

from entry import sample

cwd = Path(__file__).resolve().parents[1]

IS_DEBUG = os.environ.get("PEETSFEA_DEBUG") == "1"
ANSYS_EXECUTABLE_PATH = "/opt/ansys_inc/v252/AnsysEM"
BUILD_PARALLEL = not IS_DEBUG
BUILD_WORKER_COUNT = 1 if IS_DEBUG else 6
BUILD_NON_GRAPHICAL = not IS_DEBUG
BUILD_CLOSE_ON_EXIT = not IS_DEBUG


@dataclass(frozen=True)
class BuildRuntime:
    non_graphical: bool
    close_on_exit: bool


@dataclass(frozen=True)
class BuildTarget:
    manifest_path: Path
    ansys_run_dir: Path


DEFAULT_BUILD_RUNTIME = BuildRuntime(
    non_graphical=BUILD_NON_GRAPHICAL,
    close_on_exit=BUILD_CLOSE_ON_EXIT,
)
GUI_VISIBLE_BUILD_RUNTIME = BuildRuntime(non_graphical=False, close_on_exit=True)
DEFAULT_FIRST_BATCH = sample.iter_sample_batch_profiles()[0]
DEFAULT_SAMPLE_MANIFEST_PATH = sample.sample_manifest_path_for_seed_start(
    DEFAULT_FIRST_BATCH.seed_start,
    workspace_root=cwd,
)
DEFAULT_ANSYS_RUN_DIR = sample.sample_ansys_run_dir_for_seed_start(
    DEFAULT_FIRST_BATCH.seed_start,
    workspace_root=cwd,
)


def _default_runtime() -> BuildRuntime:
    return DEFAULT_BUILD_RUNTIME


def _build_entry(
    entry: SampleManifestEntry,
    *,
    ansys_run_dir: Path,
    runtime: BuildRuntime,
) -> bool:
    return build_aedt_from_manifest_entry_with_options(
        entry=entry,
        ansys_run_dir=ansys_run_dir,
        ansys_executable_path=ANSYS_EXECUTABLE_PATH,
        non_graphical=runtime.non_graphical,
        close_on_exit=runtime.close_on_exit,
    )


def _report_build_exception(entry: SampleManifestEntry, exc: Exception) -> None:
    error(
        "[build] failed "
        f"design_id={entry['design_id']} toml_path={entry['toml_path']} "
        f"exc_type={type(exc).__name__} exc={exc}"
    )
    error(traceback.format_exc().rstrip())


def _build_worker(task: tuple[SampleManifestEntry, Path, BuildRuntime, bool]) -> bool:
    entry, ansys_run_dir, runtime, stop_on_error = task
    if stop_on_error:
        return _build_entry(entry, ansys_run_dir=ansys_run_dir, runtime=runtime)
    try:
        return _build_entry(entry, ansys_run_dir=ansys_run_dir, runtime=runtime)
    except Exception as exc:
        _report_build_exception(entry, exc)
        return False


def build_entries(
    entries: list[SampleManifestEntry],
    *,
    ansys_run_dir: Path,
    runtime: BuildRuntime | None = None,
    parallel: bool | None = None,
    max_workers: int | None = None,
    stop_on_error: bool = True,
) -> list[bool]:
    if not entries:
        return []

    resolved_runtime = runtime or _default_runtime()
    should_parallel = BUILD_PARALLEL if parallel is None else parallel
    if resolved_runtime.non_graphical is False:
        should_parallel = False

    worker_count = BUILD_WORKER_COUNT if max_workers is None else max_workers
    if not should_parallel or worker_count <= 1:
        results: list[bool] = []
        for entry in entries:
            if stop_on_error:
                ok = _build_entry(
                    entry,
                    ansys_run_dir=ansys_run_dir,
                    runtime=resolved_runtime,
                )
            else:
                try:
                    ok = _build_entry(
                        entry,
                        ansys_run_dir=ansys_run_dir,
                        runtime=resolved_runtime,
                    )
                except Exception as exc:
                    _report_build_exception(entry, exc)
                    ok = False
            results.append(ok)
            if stop_on_error and not ok:
                raise RuntimeError(
                    "Build failed and stop_on_error is enabled "
                    f"(design_id={entry['design_id']}, toml_path={entry['toml_path']})"
                )
        info(f"[build] completed entries={len(results)} ok={sum(results)} failed={len(results) - sum(results)}")
        return results

    tasks = [(entry, ansys_run_dir, resolved_runtime, stop_on_error) for entry in entries]
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        results = list(executor.map(_build_worker, tasks))
    for entry, ok in zip(entries, results, strict=True):
        if stop_on_error and not ok:
            raise RuntimeError(
                "Build failed and stop_on_error is enabled "
                f"(design_id={entry['design_id']}, toml_path={entry['toml_path']})"
            )
    info(f"[build] completed entries={len(results)} ok={sum(results)} failed={len(results) - sum(results)}")
    return results


def build_from_manifest_path(
    manifest_path: Path = DEFAULT_SAMPLE_MANIFEST_PATH,
    *,
    ansys_run_dir: Path = DEFAULT_ANSYS_RUN_DIR,
    runtime: BuildRuntime | None = None,
    parallel: bool | None = None,
    max_workers: int | None = None,
    stop_on_error: bool = True,
) -> list[bool]:
    entries = load_sample_manifest(manifest_path)
    return build_entries(
        entries,
        ansys_run_dir=ansys_run_dir,
        runtime=runtime,
        parallel=parallel,
        max_workers=max_workers,
        stop_on_error=stop_on_error,
    )


def iter_default_build_targets(*, workspace_root: Path = cwd) -> tuple[BuildTarget, ...]:
    return tuple(
        BuildTarget(
            manifest_path=sample.sample_manifest_path_for_seed_start(profile.seed_start, workspace_root=workspace_root),
            ansys_run_dir=sample.sample_ansys_run_dir_for_seed_start(profile.seed_start, workspace_root=workspace_root),
        )
        for profile in sample.iter_sample_batch_profiles()
    )


def build_all_targets(targets: tuple[BuildTarget, ...] | None = None) -> list[list[bool]]:
    return build_all_targets_with_options(targets)


def build_all_targets_with_options(
    targets: tuple[BuildTarget, ...] | None = None,
    *,
    runtime: BuildRuntime | None = None,
    parallel: bool | None = None,
    max_workers: int | None = None,
    stop_on_error: bool = True,
) -> list[list[bool]]:
    resolved_targets = targets if targets is not None else iter_default_build_targets()
    results: list[list[bool]] = []

    for target in resolved_targets:
        if not target.manifest_path.exists():
            raise FileNotFoundError(f"Missing batch manifest: {target.manifest_path}")
        info(f"[build] start manifest={target.manifest_path} ansys_run_dir={target.ansys_run_dir}")
        target_results = build_from_manifest_path(
            target.manifest_path,
            ansys_run_dir=target.ansys_run_dir,
            runtime=runtime,
            parallel=parallel,
            max_workers=max_workers,
            stop_on_error=stop_on_error,
        )
        info(f"[build] completed manifest={target.manifest_path} count={len(target_results)}")
        results.append(target_results)
    return results


def main() -> list[list[bool]]:
    return build_all_targets()


if __name__ == "__main__":
    main()

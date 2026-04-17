from __future__ import annotations

import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from peetsfea.legacy.type1.pipeline.run_batch import (
    SampleManifestEntry,
    generate_sample_artifact_for_seed,
    write_sample_manifest,
)
from peetsfea.legacy.type1.pipeline.selection.uniform_seedset import generate_eager_uniform_feasible_seed_points
from peetsfea.console_log import info
from peetsfea.version import __version__

cwd = Path(__file__).resolve().parents[3]
DEFAULT_EAGER_MAX_ATTEMPTS = 64

IS_DEBUG = os.environ.get("PEETSFEA_DEBUG") == "1"
ANSYS_EXECUTABLE_PATH = "/opt/ansys_inc/v252/AnsysEM"
SOURCE_TOML_PATH = cwd / "run" / "legacy" / "type1.toml"
SAMPLE_FIRST_SEED_START = 0
SAMPLE_TOTAL_TOML_COUNT = 10000
SAMPLE_BATCH_TOML_COUNT = 128
SAMPLE_SPARSITY_RATIO = 0.4
SAMPLE_BATCH_SEED_SPAN = max(1, math.ceil(SAMPLE_BATCH_TOML_COUNT / SAMPLE_SPARSITY_RATIO))
SAMPLE_BATCH_COUNT = max(1, math.ceil(SAMPLE_TOTAL_TOML_COUNT / SAMPLE_BATCH_TOML_COUNT))
SAMPLE_MAX_ATTEMPTS = DEFAULT_EAGER_MAX_ATTEMPTS
SAMPLE_PARALLEL = not IS_DEBUG
SAMPLE_WORKER_COUNT = 1 if IS_DEBUG else 12


@dataclass(frozen=True)
class SampleBatchProfile:
    seed_start: int
    seed_end: int
    target_count: int


def sample_output_dir_for_seed_start(seed_start: int, *, workspace_root: Path = cwd) -> Path:
    return workspace_root / "run" / "toml" / f"toml_{__version__}_{seed_start}"


def sample_manifest_path_for_seed_start(seed_start: int, *, workspace_root: Path = cwd) -> Path:
    return sample_output_dir_for_seed_start(seed_start, workspace_root=workspace_root) / "manifest.json"


def sample_ansys_run_dir_for_seed_start(seed_start: int, *, workspace_root: Path = cwd) -> Path:
    return workspace_root / "run" / "aedt" / f"aedt_{__version__}_{seed_start}"


def iter_sample_batch_profiles(
    *,
    total_toml_count: int = SAMPLE_TOTAL_TOML_COUNT,
    batch_toml_count: int = SAMPLE_BATCH_TOML_COUNT,
    first_seed_start: int = SAMPLE_FIRST_SEED_START,
    batch_seed_span: int = SAMPLE_BATCH_SEED_SPAN,
) -> tuple[SampleBatchProfile, ...]:
    if total_toml_count <= 0:
        raise ValueError("total_toml_count must be positive")
    if batch_toml_count <= 0:
        raise ValueError("batch_toml_count must be positive")
    if batch_seed_span <= 0:
        raise ValueError("batch_seed_span must be positive")

    profiles: list[SampleBatchProfile] = []
    remaining_total = total_toml_count
    seed_start = first_seed_start
    while remaining_total > 0:
        target_count = min(batch_toml_count, remaining_total)
        seed_end = seed_start + batch_seed_span
        profiles.append(
            SampleBatchProfile(
                seed_start=seed_start,
                seed_end=seed_end,
                target_count=target_count,
            )
        )
        remaining_total -= target_count
        seed_start = seed_end
    return tuple(profiles)


def _generate_sample_entry(
    task: tuple[int, Path, Path, Path, str],
) -> SampleManifestEntry:
    seed, source_toml_path, output_dir, ansys_run_dir, ansys_executable_path = task
    return generate_sample_artifact_for_seed(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        ansys_run_dir=ansys_run_dir,
        ansys_executable_path=ansys_executable_path,
        seed=seed,
    )


def generate_sample_manifest(
    *,
    seed_start: int,
    seed_end: int,
    target_count: int,
    max_attempts: int = SAMPLE_MAX_ATTEMPTS,
    source_toml_path: Path = SOURCE_TOML_PATH,
    ansys_executable_path: str = ANSYS_EXECUTABLE_PATH,
    output_dir: Path | None = None,
    manifest_path: Path | None = None,
    ansys_run_dir: Path | None = None,
    workspace_root: Path = cwd,
    parallel: bool | None = None,
    max_workers: int | None = None,
) -> list[SampleManifestEntry]:
    resolved_output_dir = output_dir or sample_output_dir_for_seed_start(seed_start, workspace_root=workspace_root)
    resolved_manifest_path = manifest_path or sample_manifest_path_for_seed_start(
        seed_start,
        workspace_root=workspace_root,
    )
    resolved_ansys_run_dir = ansys_run_dir or sample_ansys_run_dir_for_seed_start(
        seed_start,
        workspace_root=workspace_root,
    )
    selected_points = generate_eager_uniform_feasible_seed_points(
        spec_path=source_toml_path,
        seed_start=seed_start,
        seed_end=seed_end,
        target_size=target_count,
        max_attempts=max_attempts,
    )
    info(
        "small-range eager uniform seed selection enabled "
        f"(range=[{seed_start},{seed_end}), target={target_count}, max_attempts={max_attempts})"
    )
    selected_seeds = tuple(point.seed for point in selected_points)
    tasks = [
        (seed, source_toml_path, resolved_output_dir, resolved_ansys_run_dir, ansys_executable_path)
        for seed in selected_seeds
    ]
    should_parallel = False if parallel is None else parallel
    worker_count = 1 if max_workers is None else max_workers

    generated_entries: list[SampleManifestEntry]
    if should_parallel and worker_count > 1:
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            generated_entries = list(executor.map(_generate_sample_entry, tasks))
    else:
        generated_entries = [_generate_sample_entry(task) for task in tasks]

    write_sample_manifest(generated_entries, resolved_manifest_path)
    info(f"wrote sample manifest: {resolved_manifest_path}")
    return generated_entries


def _generate_batch_manifest(
    profile: SampleBatchProfile,
    *,
    source_toml_path: Path,
    ansys_executable_path: str,
    workspace_root: Path,
) -> list[SampleManifestEntry]:
    return generate_sample_manifest(
        seed_start=profile.seed_start,
        seed_end=profile.seed_end,
        target_count=profile.target_count,
        max_attempts=SAMPLE_MAX_ATTEMPTS,
        source_toml_path=source_toml_path,
        ansys_executable_path=ansys_executable_path,
        output_dir=sample_output_dir_for_seed_start(profile.seed_start, workspace_root=workspace_root),
        manifest_path=sample_manifest_path_for_seed_start(profile.seed_start, workspace_root=workspace_root),
        ansys_run_dir=sample_ansys_run_dir_for_seed_start(profile.seed_start, workspace_root=workspace_root),
        workspace_root=workspace_root,
        parallel=False,
        max_workers=1,
    )


def _generate_batch_manifest_task(
    task: tuple[SampleBatchProfile, Path, str, Path],
) -> list[SampleManifestEntry]:
    profile, source_toml_path, ansys_executable_path, workspace_root = task
    return _generate_batch_manifest(
        profile,
        source_toml_path=source_toml_path,
        ansys_executable_path=ansys_executable_path,
        workspace_root=workspace_root,
    )


def generate_all_sample_manifests(
    profiles: tuple[SampleBatchProfile, ...] | None = None,
    *,
    source_toml_path: Path = SOURCE_TOML_PATH,
    ansys_executable_path: str = ANSYS_EXECUTABLE_PATH,
    workspace_root: Path = cwd,
    parallel: bool | None = None,
    max_workers: int | None = None,
) -> list[list[SampleManifestEntry]]:
    resolved_profiles = profiles if profiles is not None else iter_sample_batch_profiles()
    if not resolved_profiles:
        return []

    for profile in resolved_profiles:
        info(
            f"[sample] start range=[{profile.seed_start},{profile.seed_end}) "
            f"target={profile.target_count}"
        )

    should_parallel = SAMPLE_PARALLEL if parallel is None else parallel
    worker_limit = SAMPLE_WORKER_COUNT if max_workers is None else max_workers
    worker_count = max(1, min(len(resolved_profiles), worker_limit))
    tasks = [
        (profile, source_toml_path, ansys_executable_path, workspace_root)
        for profile in resolved_profiles
    ]
    manifests: list[list[SampleManifestEntry]]

    if should_parallel and worker_count > 1:
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            manifests = list(executor.map(_generate_batch_manifest_task, tasks))
    else:
        manifests = [_generate_batch_manifest_task(task) for task in tasks]

    for profile, entries in zip(resolved_profiles, manifests, strict=True):
        manifest_path = sample_manifest_path_for_seed_start(profile.seed_start, workspace_root=workspace_root)
        info(f"[sample] wrote {len(entries)} entries to {manifest_path}")
    return manifests


def main() -> list[list[SampleManifestEntry]]:
    return generate_all_sample_manifests()


if __name__ == "__main__":
    main()

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.pipeline.run_batch import SampleManifestEntry

from entry.build import GUI_VISIBLE_BUILD_RUNTIME, build_entries
from entry.sample import (
    ANSYS_EXECUTABLE_PATH,
    DEFAULT_EAGER_MAX_ATTEMPTS,
    SOURCE_TOML_PATH,
    SampleProfile,
    generate_sample_manifest,
    sample_ansys_run_dir_for_seed_start,
    sample_manifest_path_for_seed_start,
    sample_output_dir_for_seed_start,
)

cwd = Path(__file__).resolve().parents[1]
DEFAULT_BUILD_ONE_PROFILE = SampleProfile(seed_start=0, seed_end=500, target_count=100)


@dataclass(frozen=True)
class SampleBuildBatchResult:
    entries: tuple[SampleManifestEntry, ...]
    build_results: tuple[bool, ...]
    manifest_path: Path
    ansys_run_dir: Path


def generate_and_build_profile(
    profile: SampleProfile = DEFAULT_BUILD_ONE_PROFILE,
    *,
    max_attempts: int = DEFAULT_EAGER_MAX_ATTEMPTS,
    source_toml_path: Path = SOURCE_TOML_PATH,
    ansys_executable_path: str = ANSYS_EXECUTABLE_PATH,
    workspace_root: Path = cwd,
) -> SampleBuildBatchResult:
    output_dir = sample_output_dir_for_seed_start(profile.seed_start, workspace_root=workspace_root)
    manifest_path = sample_manifest_path_for_seed_start(profile.seed_start, workspace_root=workspace_root)
    ansys_run_dir = sample_ansys_run_dir_for_seed_start(profile.seed_start, workspace_root=workspace_root)
    entries = generate_sample_manifest(
        seed_start=profile.seed_start,
        seed_end=profile.seed_end,
        target_count=profile.target_count,
        max_attempts=max_attempts,
        source_toml_path=source_toml_path,
        ansys_executable_path=ansys_executable_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        ansys_run_dir=ansys_run_dir,
        workspace_root=workspace_root,
    )
    build_results = build_entries(
        entries,
        ansys_run_dir=ansys_run_dir,
        runtime=GUI_VISIBLE_BUILD_RUNTIME,
        parallel=False,
    )
    return SampleBuildBatchResult(
        entries=tuple(entries),
        build_results=tuple(build_results),
        manifest_path=manifest_path,
        ansys_run_dir=ansys_run_dir,
    )


def build_one(profile: SampleProfile = DEFAULT_BUILD_ONE_PROFILE) -> SampleBuildBatchResult:
    return generate_and_build_profile(profile)


if __name__ == "__main__":
    build_one()

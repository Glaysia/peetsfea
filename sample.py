from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from peetsfea import __version__
from peetsfea.pipeline.run_batch import (
    SampleManifestEntry,
    generate_sample_artifact_for_seed,
    write_sample_manifest,
)
from peetsfea.pipeline.uniform_seedset import generate_eager_uniform_feasible_seed_points

cwd = Path(__file__).parent.resolve()
DEFAULT_EAGER_MAX_ATTEMPTS = 64

ANSYS_EXECUTABLE_PATH = "/opt/ansys_inc/v252/AnsysEM"
SOURCE_TOML_PATH = cwd / "run" / "type1.toml"


@dataclass(frozen=True)
class SampleProfile:
    seed_start: int
    seed_end: int
    target_count: int


def sample_output_dir_for_seed_start(seed_start: int, *, workspace_root: Path = cwd) -> Path:
    return workspace_root / "run" / "toml" / f"toml_{__version__}_{seed_start}"


def sample_manifest_path_for_seed_start(seed_start: int, *, workspace_root: Path = cwd) -> Path:
    return sample_output_dir_for_seed_start(seed_start, workspace_root=workspace_root) / "manifest.json"


def sample_ansys_run_dir_for_seed_start(seed_start: int, *, workspace_root: Path = cwd) -> Path:
    return workspace_root / "run" / "aedt" / f"aedt_{__version__}_{seed_start}"


def generate_sample_manifest(
    *,
    seed_start: int,
    seed_end: int,
    target_count: int,
    max_attempts: int = DEFAULT_EAGER_MAX_ATTEMPTS,
    source_toml_path: Path = SOURCE_TOML_PATH,
    ansys_executable_path: str = ANSYS_EXECUTABLE_PATH,
    output_dir: Path | None = None,
    manifest_path: Path | None = None,
    ansys_run_dir: Path | None = None,
    workspace_root: Path = cwd,
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
    entries: list[SampleManifestEntry] = []
    selected_points = generate_eager_uniform_feasible_seed_points(
        spec_path=source_toml_path,
        seed_start=seed_start,
        seed_end=seed_end,
        target_size=target_count,
        max_attempts=max_attempts,
    )
    print(
        "small-range eager uniform seed selection enabled "
        f"(range=[{seed_start},{seed_end}), target={target_count}, max_attempts={max_attempts})"
    )
    selected_seeds = tuple(point.seed for point in selected_points)

    for seed in selected_seeds:
        try:
            entry = generate_sample_artifact_for_seed(
                source_toml_path=source_toml_path,
                output_dir=resolved_output_dir,
                ansys_run_dir=resolved_ansys_run_dir,
                ansys_executable_path=ansys_executable_path,
                seed=seed,
            )
        except Exception as exc:
            print(f"[seed={seed}] sample generation failed; skipping: {exc}")
            continue
        entries.append(entry)

    write_sample_manifest(entries, resolved_manifest_path)
    print(f"wrote sample manifest: {resolved_manifest_path}")
    return entries

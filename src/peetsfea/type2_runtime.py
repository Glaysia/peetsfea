from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import TypedDict

from peetsfea.backend.pyaedt.type2_step_setup_ready import Type2SetupReadyResult, setup_type2_step_ledger
from peetsfea.type2_step_export import export_type2_step_artifacts
from peetsfea.type2_sampled import PreparedType2Build, prepare_type2_build

_Exporter = Callable[..., object]
_Runner = Callable[..., Type2SetupReadyResult]


class Type2SteppedArtifact(TypedDict):
    design_id: str
    sampled_toml_path: str
    scene_step_path: str
    step_ledger_path: str


class Type2BuiltArtifact(TypedDict):
    design_id: str
    sampled_toml_path: str
    aedt_path: str
    source_step_ledger_path: str
    imported_ledger_path: str


def export_prepared_type2_design(
    prepared_build: PreparedType2Build,
    *,
    exporter: _Exporter = export_type2_step_artifacts,
) -> Type2SteppedArtifact:
    prepared_build.design_dir.mkdir(parents=True, exist_ok=True)
    exporter(
        toml_path=prepared_build.sampled_toml_path,
        output_dir=prepared_build.design_dir,
        ledger_path=prepared_build.step_ledger_path,
        seed=prepared_build.seed,
    )
    return {
        "design_id": prepared_build.design_id,
        "sampled_toml_path": str(prepared_build.sampled_toml_path),
        "scene_step_path": str(prepared_build.scene_step_path),
        "step_ledger_path": str(prepared_build.step_ledger_path),
    }


def _export_single_sampled_toml(sampled_toml_path_text: str) -> Type2SteppedArtifact:
    prepared_build = prepare_type2_build(Path(sampled_toml_path_text))
    return export_prepared_type2_design(prepared_build)


def export_prepared_type2_designs(
    prepared_builds: tuple[PreparedType2Build, ...],
    *,
    jobs: int,
    exporter: _Exporter = export_type2_step_artifacts,
) -> list[Type2SteppedArtifact]:
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    if len(prepared_builds) == 0:
        return []
    if jobs == 1 or exporter is not export_type2_step_artifacts:
        return [export_prepared_type2_design(prepared_build, exporter=exporter) for prepared_build in prepared_builds]
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        return list(executor.map(_export_single_sampled_toml, (str(prepared_build.sampled_toml_path) for prepared_build in prepared_builds)))


def validate_prepared_type2_step_ledgers(prepared_builds: tuple[PreparedType2Build, ...]) -> None:
    for prepared_build in prepared_builds:
        if not prepared_build.step_ledger_path.is_file():
            raise FileNotFoundError(f"type2 STEP ledger not found: {prepared_build.step_ledger_path}")


def build_prepared_type2_design(
    prepared_build: PreparedType2Build,
    *,
    runner: _Runner = setup_type2_step_ledger,
) -> Type2BuiltArtifact:
    result = runner(
        step_ledger_path=prepared_build.step_ledger_path,
        output_aedt_path=prepared_build.aedt_path,
        imported_ledger_path=prepared_build.imported_ledger_path,
        design_name=prepared_build.design_id,
        design_variables=prepared_build.design_variables,
    )
    return {
        "design_id": prepared_build.design_id,
        "sampled_toml_path": str(prepared_build.sampled_toml_path),
        "aedt_path": result["aedt_path"],
        "source_step_ledger_path": result["source_step_ledger_path"],
        "imported_ledger_path": result["imported_ledger_path"],
    }


def _build_single_sampled_toml(sampled_toml_path_text: str) -> Type2BuiltArtifact:
    prepared_build = prepare_type2_build(Path(sampled_toml_path_text))
    return build_prepared_type2_design(prepared_build)


def build_prepared_type2_designs(
    prepared_builds: tuple[PreparedType2Build, ...],
    *,
    jobs: int,
    runner: _Runner = setup_type2_step_ledger,
) -> list[Type2BuiltArtifact]:
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    if len(prepared_builds) == 0:
        return []
    if jobs == 1 or runner is not setup_type2_step_ledger:
        return [build_prepared_type2_design(prepared_build, runner=runner) for prepared_build in prepared_builds]
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        return list(executor.map(_build_single_sampled_toml, (str(prepared_build.sampled_toml_path) for prepared_build in prepared_builds)))


__all__ = [
    "Type2BuiltArtifact",
    "Type2SteppedArtifact",
    "build_prepared_type2_design",
    "build_prepared_type2_designs",
    "export_prepared_type2_design",
    "export_prepared_type2_designs",
    "validate_prepared_type2_step_ledgers",
]

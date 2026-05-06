from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
from typing import TypedDict

from peetsfea.backend.pyaedt.type2_step_em_solve import Type2EmSolveResult
from peetsfea.backend.pyaedt.type2_step_setup_ready import setup_type2_step_ledger
from peetsfea.backend.pyaedt.type2_step_setup_ready import setup_and_solve_type2_step_ledger
from peetsfea.type2_step_export import export_type2_step_artifacts
from peetsfea.type2_sampled import PreparedType2Build, prepare_type2_build

_Exporter = Callable[..., object]


class _Type2BuildRunnerResult(TypedDict):
    aedt_path: str
    source_step_ledger_path: str
    imported_ledger_path: str


_Runner = Callable[..., _Type2BuildRunnerResult]
_RX_ONLY_MODELED_ROLES: tuple[str] = ("rx_single_coil",)
_RX_WITH_TX_INNER_GEOMETRY_MODELED_ROLES: tuple[str, ...] = ("rx_single_coil", "tx_inner_single_coil")
_SUPPORTED_MODELED_ROLE_SETS: tuple[tuple[str, ...], ...] = (
    _RX_ONLY_MODELED_ROLES,
    _RX_WITH_TX_INNER_GEOMETRY_MODELED_ROLES,
)


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


class _Type2SolveRunnerResult(_Type2BuildRunnerResult):
    em_solve: Type2EmSolveResult


_SolveRunner = Callable[..., _Type2SolveRunnerResult]


class Type2EmArtifact(Type2BuiltArtifact):
    em_solve: Type2EmSolveResult


def _assert_setup_ready_supported(prepared_build: PreparedType2Build) -> None:
    actual_roles = tuple(sorted(prepared_build.modeled_roles))
    if actual_roles in _SUPPORTED_MODELED_ROLE_SETS:
        return
    formatted_supported_sets = ", ".join(str(list(role_set)) for role_set in _SUPPORTED_MODELED_ROLE_SETS)
    raise ValueError(
        "type2 build/setup-ready rejects unsupported modeled roles for active path: "
        f"{actual_roles}. Supported modeled role sets are {formatted_supported_sets}. "
        f"(actual={list(prepared_build.modeled_roles)})"
    )


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
        _validate_prepared_type2_step_ledger(prepared_build.step_ledger_path)


def _validate_prepared_type2_step_ledger(step_ledger_path: Path) -> None:
    if not step_ledger_path.is_file():
        raise FileNotFoundError(f"type2 STEP ledger not found: {step_ledger_path}")
    raw_payload = json.loads(step_ledger_path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        raise TypeError(f"type2 STEP ledger payload must be object: {step_ledger_path}")
    if "scene_step_path" not in raw_payload:
        raise ValueError(f"type2 STEP ledger is missing required key 'scene_step_path': {step_ledger_path}")
    raw_scene_step_path = raw_payload["scene_step_path"]
    if not isinstance(raw_scene_step_path, str):
        raise TypeError(f"type2 STEP ledger scene_step_path must be str: {step_ledger_path}")
    if raw_scene_step_path == "":
        raise ValueError(f"type2 STEP ledger scene_step_path must be non-empty: {step_ledger_path}")
    scene_step_path = Path(raw_scene_step_path)
    if scene_step_path.is_absolute():
        checked_scene_step_path = scene_step_path.resolve(strict=False)
    else:
        checked_scene_step_path = (step_ledger_path.parent / scene_step_path).resolve(strict=False)
    if not checked_scene_step_path.is_file():
        raise FileNotFoundError(f"type2 scene STEP not found: {checked_scene_step_path}")


def ensure_prepared_type2_step_ledger(
    prepared_build: PreparedType2Build,
    *,
    exporter: _Exporter = export_type2_step_artifacts,
) -> None:
    if prepared_build.step_ledger_path.is_file():
        _validate_prepared_type2_step_ledger(prepared_build.step_ledger_path)
        return
    export_prepared_type2_design(prepared_build, exporter=exporter)


def _ensure_single_sampled_toml_step_ledger(sampled_toml_path_text: str) -> None:
    prepared_build = prepare_type2_build(Path(sampled_toml_path_text))
    ensure_prepared_type2_step_ledger(prepared_build)


def ensure_prepared_type2_step_ledgers(
    prepared_builds: tuple[PreparedType2Build, ...],
    *,
    jobs: int,
    exporter: _Exporter = export_type2_step_artifacts,
) -> None:
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    if len(prepared_builds) == 0:
        return
    if jobs == 1 or exporter is not export_type2_step_artifacts:
        for prepared_build in prepared_builds:
            ensure_prepared_type2_step_ledger(prepared_build, exporter=exporter)
        return
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        tuple(
            executor.map(
                _ensure_single_sampled_toml_step_ledger,
                (str(prepared_build.sampled_toml_path) for prepared_build in prepared_builds),
            )
        )


def build_prepared_type2_design(
    prepared_build: PreparedType2Build,
    *,
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _Runner = setup_type2_step_ledger,
) -> Type2BuiltArtifact:
    _assert_setup_ready_supported(prepared_build)
    ensure_prepared_type2_step_ledger(prepared_build, exporter=exporter)
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


def solve_prepared_type2_design(
    prepared_build: PreparedType2Build,
    *,
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _SolveRunner = setup_and_solve_type2_step_ledger,
) -> Type2EmArtifact:
    _assert_setup_ready_supported(prepared_build)
    ensure_prepared_type2_step_ledger(prepared_build, exporter=exporter)
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
        "em_solve": result["em_solve"],
    }


def _build_single_sampled_toml(sampled_toml_path_text: str) -> Type2BuiltArtifact:
    prepared_build = prepare_type2_build(Path(sampled_toml_path_text))
    return build_prepared_type2_design(prepared_build)


def build_prepared_type2_designs(
    prepared_builds: tuple[PreparedType2Build, ...],
    *,
    jobs: int,
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _Runner = setup_type2_step_ledger,
) -> list[Type2BuiltArtifact]:
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    if len(prepared_builds) == 0:
        return []
    if jobs == 1 or runner is not setup_type2_step_ledger or exporter is not export_type2_step_artifacts:
        return [build_prepared_type2_design(prepared_build, exporter=exporter, runner=runner) for prepared_build in prepared_builds]
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        return list(executor.map(_build_single_sampled_toml, (str(prepared_build.sampled_toml_path) for prepared_build in prepared_builds)))


def _solve_single_sampled_toml(sampled_toml_path_text: str) -> Type2EmArtifact:
    prepared_build = prepare_type2_build(Path(sampled_toml_path_text))
    return solve_prepared_type2_design(prepared_build)


def solve_prepared_type2_designs(
    prepared_builds: tuple[PreparedType2Build, ...],
    *,
    jobs: int,
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _SolveRunner = setup_and_solve_type2_step_ledger,
) -> list[Type2EmArtifact]:
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    if len(prepared_builds) == 0:
        return []
    if jobs == 1 or runner is not setup_and_solve_type2_step_ledger or exporter is not export_type2_step_artifacts:
        return [solve_prepared_type2_design(prepared_build, exporter=exporter, runner=runner) for prepared_build in prepared_builds]
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        return list(executor.map(_solve_single_sampled_toml, (str(prepared_build.sampled_toml_path) for prepared_build in prepared_builds)))


__all__ = [
    "Type2BuiltArtifact",
    "Type2EmArtifact",
    "Type2SteppedArtifact",
    "build_prepared_type2_design",
    "build_prepared_type2_designs",
    "ensure_prepared_type2_step_ledger",
    "ensure_prepared_type2_step_ledgers",
    "export_prepared_type2_design",
    "export_prepared_type2_designs",
    "solve_prepared_type2_design",
    "solve_prepared_type2_designs",
    "validate_prepared_type2_step_ledgers",
]

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
from typing import TypedDict

from peetsfea.backend.pyaedt.type2_step_import_core import Type2ImportedLedger
from peetsfea.backend.pyaedt.type2_step_import_pipeline import import_type2_step_ledger
from peetsfea.backend.pyaedt.type2_step_setup_ready import Type2SetupReadyResult, setup_type2_step_ledger
from peetsfea.type2_step_export import export_type2_step_artifacts
from peetsfea.type2_sampled import PreparedType2Build, prepare_type2_build

_Exporter = Callable[..., object]
_Runner = Callable[..., Type2SetupReadyResult]
_SETUP_READY_SUPPORTED_MODELED_ROLES: frozenset[str] = frozenset({"tx_single_coil", "rx_single_coil"})
_SETUP_READY_EXPECTED_MODELED_ROLES = ("rx_single_coil", "tx_single_coil")


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


def _assert_setup_ready_supported(prepared_build: PreparedType2Build) -> None:
    unsupported_roles: list[str] = []
    seen_roles: set[str] = set()
    for role in prepared_build.modeled_roles:
        if role in _SETUP_READY_SUPPORTED_MODELED_ROLES:
            continue
        if role in seen_roles:
            continue
        seen_roles.add(role)
        unsupported_roles.append(role)
    if len(unsupported_roles) != 0:
        raise ValueError(
            "type2 build/setup-ready is unsupported for modeled roles "
            f"{unsupported_roles}; build path remains setup-ready-only and does not auto-switch to import-only"
        )
    actual_roles = tuple(sorted(prepared_build.modeled_roles))
    if actual_roles != _SETUP_READY_EXPECTED_MODELED_ROLES:
        raise ValueError(
            "type2 build/setup-ready requires exactly one tx_single_coil and one rx_single_coil modeled role "
            f"(actual={list(prepared_build.modeled_roles)})"
        )


def _use_import_only_build(prepared_build: PreparedType2Build, *, runner: _Runner) -> bool:
    if runner is not setup_type2_step_ledger:
        return False
    unsupported_roles = [role for role in prepared_build.modeled_roles if role not in _SETUP_READY_SUPPORTED_MODELED_ROLES]
    return len(unsupported_roles) != 0


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


def build_prepared_type2_design(
    prepared_build: PreparedType2Build,
    *,
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _Runner = setup_type2_step_ledger,
) -> Type2BuiltArtifact:
    ensure_prepared_type2_step_ledger(prepared_build, exporter=exporter)
    result: Type2SetupReadyResult | Type2ImportedLedger
    if _use_import_only_build(prepared_build, runner=runner):
        result = import_type2_step_ledger(
            step_ledger_path=prepared_build.step_ledger_path,
            output_aedt_path=prepared_build.aedt_path,
            imported_ledger_path=prepared_build.imported_ledger_path,
            design_name=prepared_build.design_id,
        )
    else:
        _assert_setup_ready_supported(prepared_build)
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


__all__ = [
    "Type2BuiltArtifact",
    "Type2SteppedArtifact",
    "build_prepared_type2_design",
    "build_prepared_type2_designs",
    "ensure_prepared_type2_step_ledger",
    "export_prepared_type2_design",
    "export_prepared_type2_designs",
    "validate_prepared_type2_step_ledgers",
]

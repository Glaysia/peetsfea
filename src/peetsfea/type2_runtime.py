from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
import json
from pathlib import Path
from typing import Literal, TypedDict

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
_RX_ONLY_WITH_TV_ALUMINUM_PLATE_MODELED_ROLES: tuple[str, ...] = ("rx_single_coil", "tv_aluminum_plate")
_RX_WITH_TX_INNER_GEOMETRY_MODELED_ROLES: tuple[str, ...] = ("rx_single_coil", "tx_inner_single_coil")
_RX_WITH_TX_INNER_GEOMETRY_AND_TV_ALUMINUM_PLATE_MODELED_ROLES: tuple[str, ...] = (
    "rx_single_coil",
    "tv_aluminum_plate",
    "tx_inner_single_coil",
)
_SUPPORTED_MODELED_ROLE_SETS: tuple[tuple[str, ...], ...] = (
    _RX_ONLY_MODELED_ROLES,
    _RX_ONLY_WITH_TV_ALUMINUM_PLATE_MODELED_ROLES,
    _RX_WITH_TX_INNER_GEOMETRY_MODELED_ROLES,
    _RX_WITH_TX_INNER_GEOMETRY_AND_TV_ALUMINUM_PLATE_MODELED_ROLES,
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


Type2BuildSkipPhase = Literal["step", "aedt"]
Type2BuildSkippableException = ValueError | RuntimeError


class Type2BuildSkippedEntry(TypedDict):
    design_id: str
    seed: int
    sampled_toml_path: str
    phase: Type2BuildSkipPhase
    error_type: str
    error_message: str


class Type2BuildBatchResult(TypedDict):
    built: list[Type2BuiltArtifact]
    skipped: list[Type2BuildSkippedEntry]


class Type2BuildSkippedLedger(TypedDict):
    manifest_path: str
    skipped: list[Type2BuildSkippedEntry]


class _Type2BuildAttemptBuilt(TypedDict):
    status: Literal["built"]
    built: Type2BuiltArtifact


class _Type2BuildAttemptSkipped(TypedDict):
    status: Literal["skipped"]
    skipped: Type2BuildSkippedEntry


_Type2BuildAttempt = _Type2BuildAttemptBuilt | _Type2BuildAttemptSkipped


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


def _build_type2_skipped_entry(
    prepared_build: PreparedType2Build,
    *,
    phase: Type2BuildSkipPhase,
    exc: Type2BuildSkippableException,
) -> Type2BuildSkippedEntry:
    if not isinstance(exc, (ValueError, RuntimeError)):
        raise TypeError("exc must be ValueError or RuntimeError")
    error_message = str(exc)
    if error_message == "":
        raise ValueError("build skipped exception message must be non-empty")
    return {
        "design_id": prepared_build.design_id,
        "seed": prepared_build.seed,
        "sampled_toml_path": str(prepared_build.sampled_toml_path),
        "phase": phase,
        "error_type": type(exc).__name__,
        "error_message": error_message,
    }


def _build_prepared_type2_design_attempt(
    prepared_build: PreparedType2Build,
    *,
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _Runner = setup_type2_step_ledger,
) -> _Type2BuildAttempt:
    _assert_setup_ready_supported(prepared_build)
    try:
        ensure_prepared_type2_step_ledger(prepared_build, exporter=exporter)
    except (ValueError, RuntimeError) as exc:
        return {
            "status": "skipped",
            "skipped": _build_type2_skipped_entry(prepared_build, phase="step", exc=exc),
        }

    if _is_resume_ready_type2_build(prepared_build):
        return {
            "status": "built",
            "built": {
                "design_id": prepared_build.design_id,
                "sampled_toml_path": str(prepared_build.sampled_toml_path),
                "aedt_path": str(prepared_build.aedt_path),
                "source_step_ledger_path": str(prepared_build.step_ledger_path),
                "imported_ledger_path": str(prepared_build.imported_ledger_path),
            },
        }
    try:
        result = runner(
            step_ledger_path=prepared_build.step_ledger_path,
            output_aedt_path=prepared_build.aedt_path,
            imported_ledger_path=prepared_build.imported_ledger_path,
            design_name=prepared_build.design_id,
            design_variables=prepared_build.design_variables,
        )
    except (ValueError, RuntimeError) as exc:
        return {
            "status": "skipped",
            "skipped": _build_type2_skipped_entry(prepared_build, phase="aedt", exc=exc),
        }
    return {
        "status": "built",
        "built": {
            "design_id": prepared_build.design_id,
            "sampled_toml_path": str(prepared_build.sampled_toml_path),
            "aedt_path": result["aedt_path"],
            "source_step_ledger_path": result["source_step_ledger_path"],
            "imported_ledger_path": result["imported_ledger_path"],
        },
    }


def _resolve_relative_candidate_path(raw_path: str, *, anchor: Path) -> Path:
    candidate_path = Path(raw_path)
    if candidate_path.is_absolute():
        return candidate_path.resolve(strict=False)
    return (anchor / candidate_path).resolve(strict=False)


def _is_resume_ready_type2_build(prepared_build: PreparedType2Build) -> bool:
    if not prepared_build.aedt_path.is_file():
        return False
    if not prepared_build.imported_ledger_path.is_file():
        return False
    try:
        raw_imported_ledger = json.loads(prepared_build.imported_ledger_path.read_text(encoding="utf-8"))
        if not isinstance(raw_imported_ledger, dict):
            return False
        if "source_step_ledger_path" not in raw_imported_ledger:
            return False
        if "aedt_path" not in raw_imported_ledger:
            return False
        if "imported_ledger_path" not in raw_imported_ledger:
            return False
        raw_source_step_ledger_path = raw_imported_ledger["source_step_ledger_path"]
        if not isinstance(raw_source_step_ledger_path, str):
            return False
        raw_aedt_path = raw_imported_ledger["aedt_path"]
        if not isinstance(raw_aedt_path, str):
            return False
        raw_imported_ledger_path = raw_imported_ledger["imported_ledger_path"]
        if not isinstance(raw_imported_ledger_path, str):
            return False
        imported_ledger_dir = prepared_build.imported_ledger_path.parent
        resolved_source_step = _resolve_relative_candidate_path(
            raw_source_step_ledger_path,
            anchor=imported_ledger_dir,
        )
        resolved_aedt = _resolve_relative_candidate_path(raw_aedt_path, anchor=imported_ledger_dir)
        resolved_imported_ledger = _resolve_relative_candidate_path(
            raw_imported_ledger_path,
            anchor=imported_ledger_dir,
        )
    except (TypeError, ValueError, OSError):
        return False
    return (
        resolved_source_step == prepared_build.step_ledger_path.resolve(strict=False)
        and resolved_aedt == prepared_build.aedt_path.resolve(strict=False)
        and resolved_imported_ledger == prepared_build.imported_ledger_path.resolve(strict=False)
    )


def _build_single_sampled_toml_attempt(sampled_toml_path_text: str) -> _Type2BuildAttempt:
    prepared_build = prepare_type2_build(Path(sampled_toml_path_text))
    return _build_prepared_type2_design_attempt(prepared_build)


def _append_build_attempt(
    batch: Type2BuildBatchResult,
    attempt: _Type2BuildAttempt,
) -> None:
    if attempt["status"] == "built":
        batch["built"].append(attempt["built"])
        return
    batch["skipped"].append(attempt["skipped"])


def build_prepared_type2_designs_best_effort(
    prepared_builds: tuple[PreparedType2Build, ...],
    *,
    jobs: int,
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _Runner = setup_type2_step_ledger,
) -> Type2BuildBatchResult:
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    batch: Type2BuildBatchResult = {"built": [], "skipped": []}
    if len(prepared_builds) == 0:
        return batch
    if jobs == 1 or runner is not setup_type2_step_ledger or exporter is not export_type2_step_artifacts:
        for prepared_build in prepared_builds:
            _append_build_attempt(
                batch,
                _build_prepared_type2_design_attempt(prepared_build, exporter=exporter, runner=runner),
            )
        return batch
    future_by_index: dict[Future[_Type2BuildAttempt], int] = {}
    indexed_attempts: list[tuple[int, _Type2BuildAttempt]] = []
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        for index, prepared_build in enumerate(prepared_builds):
            future = executor.submit(_build_single_sampled_toml_attempt, str(prepared_build.sampled_toml_path))
            future_by_index[future] = index
        for future in as_completed(future_by_index):
            indexed_attempts.append((future_by_index[future], future.result()))
    for _, attempt in sorted(indexed_attempts, key=lambda item: item[0]):
        _append_build_attempt(batch, attempt)
    return batch


def write_type2_build_skipped_ledger(
    ledger_path: Path,
    *,
    manifest_path: Path,
    skipped: list[Type2BuildSkippedEntry],
) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    payload: Type2BuildSkippedLedger = {
        "manifest_path": str(manifest_path),
        "skipped": skipped,
    }
    ledger_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


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
    "Type2BuildBatchResult",
    "Type2BuildSkippedEntry",
    "Type2BuildSkippedLedger",
    "Type2EmArtifact",
    "Type2SteppedArtifact",
    "build_prepared_type2_design",
    "build_prepared_type2_designs",
    "build_prepared_type2_designs_best_effort",
    "ensure_prepared_type2_step_ledger",
    "ensure_prepared_type2_step_ledgers",
    "export_prepared_type2_design",
    "export_prepared_type2_designs",
    "solve_prepared_type2_design",
    "solve_prepared_type2_designs",
    "validate_prepared_type2_step_ledgers",
    "write_type2_build_skipped_ledger",
]

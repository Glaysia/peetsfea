from __future__ import annotations

import copy
from collections.abc import Callable, Iterator
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeGuard, TypedDict, cast

from peetsfea.spec.loader import TOMLTable, TOMLValue, load_toml_bytes
from peetsfea.spec.toml_render import toml_dumps
from peetsfea.type2_sampled_sampling import _all_range_owner_specs
from peetsfea.type2_sampled_sampling import _modeled_roles
from peetsfea.type2_sampled_sampling import _parse_constraints
from peetsfea.type2_sampled_sampling import _range_spec_for_owner_path
from peetsfea.type2_sampled_sampling import _require_constraints_satisfied
from peetsfea.type2_sampled_sampling import exportable_sampled_owner_paths
from peetsfea.type2_sampled_sampling import exportable_sampled_owner_paths_for_seed
from peetsfea.type2_sampled_sampling import sampled_owner_values
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import Type2StepSpec
from peetsfea.type2_step_spec import load_type2_step_spec as _load_type2_step_spec
from peetsfea.type2_sampled_skip import Type2SampleSkippedEntry
from peetsfea.type2_sampled_skip import build_type2_sample_skipped_entry
from peetsfea.type2_sampled_skip import copy_type2_sample_skipped_entries
from peetsfea.type2_sampled_skip import load_type2_sample_skipped_entries

REPO_ROOT = Path(__file__).resolve().parents[2]
SampledScalar = int | float
DesignVariableEntry = tuple[str, str]
_SampleExporter = Callable[..., object]
_INTEGER_RANGE_FIELD_NAMES = (
    "turn_count",
    "connection_mode",
    "layer_count",
    "underlay_repeat_count",
    "void_stack_present",
    "wall_parallel_stack_present",
    "tx_coil_count",
    "x_division_count",
    "y_division_count",
)
_SAMPLED_METADATA_TABLE = "sampled"
_SAMPLED_SINGLE_COIL_ROLES: frozenset[str] = frozenset({"tx_single_coil", "rx_single_coil"})
_PLATE_STACK_ROLE_SUFFIX = "_plate_stack"
_TX_RECT_VOID_COLUMNS_ROLE = "tx_rect_void_columns"
_TYPE2_CONSTRAINT_RETRY_LIMIT: Final[int] = 64
_CONSTRAINT_COMPARISON_OPERATORS: Final[frozenset[str]] = frozenset({"<", "<=", ">", ">=", "==", "!="})
_DERIVED_SOURCE_OWNER_PATHS: Final[dict[str, str]] = {
    "modeled_objects.tx_outer_rect_void_coil.x_position_ratio": (
        "modeled_objects.tx_inner_rect_void_coil.tx_outer_x_position_ratio"
    ),
}


def _default_sample_exporter(
    *,
    toml_path: Path,
    output_dir: Path,
    ledger_path: Path,
    seed: int,
    stage_reporter: Callable[[object], None],
) -> object:
    from peetsfea.type2_step_export import export_type2_step_artifacts

    return export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=output_dir,
        ledger_path=ledger_path,
        seed=seed,
        stage_reporter=stage_reporter,
    )


class _ConstraintPathRef(TypedDict):
    path: str


class _ConstraintValueRef(TypedDict):
    value: int | float


class _ConstraintFuncRef(TypedDict):
    func: str


class _Type2ConstraintRule(TypedDict):
    id: str
    kind: str
    message: str
    enabled: bool
    lhs: _ConstraintPathRef | _ConstraintFuncRef | _ConstraintValueRef
    op: str
    rhs: _ConstraintPathRef | _ConstraintFuncRef | _ConstraintValueRef


class Type2SampleMetadata(TypedDict):
    source_toml_path: str
    seed: int
    sample_index: int
    head_hash4: str
    retry_number: int
    sampled_owner_paths: list[str]


class Type2SampleManifestEntry(TypedDict):
    design_id: str
    seed: int
    sample_index: int
    retry_number: int
    source_toml_path: str
    sampled_toml_path: str
    design_dir: str
    scene_step_path: str
    step_ledger_path: str
    imported_ledger_path: str
    aedt_path: str
    sampled_owner_paths: list[str]


_SampleProgressReporter = Callable[[int, int, "Type2SampleManifestEntry"], None]
_SampleSkippedProgressReporter = Callable[[int, int, Type2SampleSkippedEntry], None]
_SampleStepStage = Literal["start", "build_scene", "export_scene_step", "finalize_step_artifacts", "done"]
_SampleStepStageReporter = Callable[[_SampleStepStage, Type2SampleManifestEntry], None]


class Type2SampleManifestConfig(TypedDict):
    source_toml_path: str
    seed_first: int
    seed_n: int
    sampler_n: int
    make_step_on_sample: bool
    aedt_builder_n: int


class Type2SampleManifestDocument(TypedDict):
    config: Type2SampleManifestConfig
    entries: list[Type2SampleManifestEntry]
    skipped: list[Type2SampleSkippedEntry]


class Type2SampleManifestGenerationResult(TypedDict):
    entries: list[Type2SampleManifestEntry]
    skipped: list[Type2SampleSkippedEntry]


@dataclass(frozen=True)
class PreparedType2Build:
    design_id: str
    seed: int
    source_toml_path: Path
    sampled_toml_path: Path
    design_dir: Path
    scene_step_path: Path
    step_ledger_path: Path
    imported_ledger_path: Path
    aedt_path: Path
    sampled_owner_paths: tuple[str, ...]
    modeled_roles: tuple[str, ...]
    design_variables: tuple[DesignVariableEntry, ...]


load_type2_step_spec = _load_type2_step_spec

_MANIFEST_STREAM_CHUNK_SIZE: Final[int] = 1024 * 1024


def _hash4_from_bytes(payload: bytes) -> str:
    return hashlib.blake2b(payload, digest_size=2).hexdigest()


def _current_head_hash4(*, repo_root: Path = REPO_ROOT) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    head_hash = result.stdout.strip()
    if len(head_hash) < 4:
        raise RuntimeError(f"git rev-parse HEAD returned too-short hash: {head_hash!r}")
    return head_hash[:4]


def build_type2_design_id(
    *,
    sample_index: int,
    generated_hash4: str,
    head_hash4: str,
    retry_number: int,
) -> str:
    if sample_index < 0:
        raise ValueError("sample_index must be >= 0")
    if retry_number < 0:
        raise ValueError("retry_number must be >= 0")
    if len(generated_hash4) != 4:
        raise ValueError(f"generated_hash4 must be 4 characters: {generated_hash4}")
    if len(head_hash4) != 4:
        raise ValueError(f"head_hash4 must be 4 characters: {head_hash4}")
    return f"s{sample_index:06d}_{generated_hash4}_{head_hash4}_{retry_number}"


def _sampled_metadata(
    source_toml_path: Path,
    *,
    seed: int,
    sample_index: int,
    head_hash4: str,
    retry_number: int,
    sampled_owner_paths: tuple[str, ...],
) -> Type2SampleMetadata:
    return {
        "source_toml_path": str(source_toml_path.resolve(strict=False)),
        "seed": seed,
        "sample_index": sample_index,
        "head_hash4": head_hash4,
        "retry_number": retry_number,
        "sampled_owner_paths": list(sampled_owner_paths),
    }


def _require_not_sampled_source(raw_spec: TOMLTable, *, context: str) -> None:
    if _SAMPLED_METADATA_TABLE in raw_spec:
        raise ValueError(f"{context} must be a source type2 TOML without [{_SAMPLED_METADATA_TABLE}] metadata")


def _modeled_object_table(raw_spec: TOMLTable, *, object_id: str) -> TOMLTable:
    assert "modeled_objects" in raw_spec, "type2 source TOML must contain modeled_objects"
    raw_modeled_objects = raw_spec["modeled_objects"]
    if not isinstance(raw_modeled_objects, list):
        raise TypeError("modeled_objects must be an array of tables")
    matches: list[TOMLTable] = []
    for entry in raw_modeled_objects:
        if not isinstance(entry, dict):
            raise TypeError("modeled_objects entries must be tables")
        if "object_id" not in entry:
            raise ValueError("modeled_objects entries must contain object_id")
        raw_object_id = entry["object_id"]
        if not isinstance(raw_object_id, str):
            raise TypeError("modeled_objects[].object_id must be str")
        if raw_object_id == object_id:
            matches.append(cast(TOMLTable, entry))
    if len(matches) != 1:
        raise ValueError(f"type2 source TOML must contain exactly one modeled object with object_id={object_id!r}")
    return matches[0]


def _non_model_object_table(raw_spec: TOMLTable, *, object_id: str) -> TOMLTable:
    assert "non_model_objects" in raw_spec, "type2 source TOML must contain non_model_objects"
    raw_non_model_objects = raw_spec["non_model_objects"]
    if not isinstance(raw_non_model_objects, list):
        raise TypeError("non_model_objects must be an array of tables")
    matches: list[TOMLTable] = []
    for entry in raw_non_model_objects:
        if not isinstance(entry, dict):
            raise TypeError("non_model_objects entries must be tables")
        if "id" not in entry:
            raise ValueError("non_model_objects entries must contain id")
        raw_id = entry["id"]
        if not isinstance(raw_id, str):
            raise TypeError("non_model_objects[].id must be str")
        if raw_id == object_id:
            matches.append(cast(TOMLTable, entry))
    if len(matches) != 1:
        raise ValueError(f"type2 source TOML must contain exactly one non-model object with id={object_id!r}")
    return matches[0]


def _freeze_owner_range_in_raw_spec(
    raw_spec: TOMLTable,
    *,
    owner_path: str,
    value: SampledScalar,
    range_spec: RangeSpec,
) -> None:
    if owner_path in _DERIVED_SOURCE_OWNER_PATHS:
        source_owner_path = _DERIVED_SOURCE_OWNER_PATHS[owner_path]
    else:
        source_owner_path = owner_path
    owner_parts = source_owner_path.split(".")
    if len(owner_parts) < 3:
        raise ValueError(f"Unsupported type2 sampled owner path: {owner_path}")
    owner_root, object_id = owner_parts[0], owner_parts[1]
    owner_table: TOMLTable
    if owner_root == "modeled_objects":
        owner_table = _modeled_object_table(raw_spec, object_id=object_id)
    elif owner_root == "non_model_objects":
        owner_table = _non_model_object_table(raw_spec, object_id=object_id)
    else:
        raise ValueError(f"Unsupported type2 sampled owner path: {owner_path}")
    for table_name in owner_parts[2:-1]:
        if table_name not in owner_table:
            raise ValueError(f"type2 source TOML is missing sampled owner table: {owner_path}")
        raw_owner_table = owner_table[table_name]
        if not isinstance(raw_owner_table, dict):
            raise TypeError(f"{owner_path} parent {table_name!r} must be a table")
        owner_table = cast(TOMLTable, raw_owner_table)
    field_name = owner_parts[-1]
    if field_name not in owner_table:
        raise ValueError(f"type2 source TOML is missing sampled owner field: {owner_path}")
    raw_field = owner_table[field_name]
    if not isinstance(raw_field, dict):
        raise TypeError(f"{owner_path} must be a table containing range")
    if range_spec.is_integer:
        frozen_scalar: TOMLValue = int(value)
    else:
        frozen_scalar = float(value)
    raw_field["range"] = [range_spec.is_integer, frozen_scalar, frozen_scalar, 1]


def _sampled_toml_table(
    raw_source_spec: TOMLTable,
    source_spec: Type2StepSpec,
    *,
    source_toml_path: Path,
    seed: int,
    sample_index: int,
    head_hash4: str,
    retry_number: int,
    sampled_values: tuple[tuple[str, SampledScalar], ...],
) -> TOMLTable:
    sampled_spec = copy.deepcopy(raw_source_spec)
    sampled_owner_paths = tuple(owner_path for owner_path, _ in sampled_values)
    for owner_path, value in sampled_values:
        range_spec = _range_spec_for_owner_path(source_spec, owner_path)
        _freeze_owner_range_in_raw_spec(sampled_spec, owner_path=owner_path, value=value, range_spec=range_spec)
    sampled_metadata = _sampled_metadata(
        source_toml_path,
        seed=seed,
        sample_index=sample_index,
        head_hash4=head_hash4,
        retry_number=retry_number,
        sampled_owner_paths=sampled_owner_paths,
    )
    sampled_spec[_SAMPLED_METADATA_TABLE] = cast(TOMLValue, sampled_metadata)
    return sampled_spec


def _design_dir(output_dir: Path, *, design_id: str) -> Path:
    return (output_dir / design_id).resolve(strict=False)


def _sampled_toml_path(design_dir: Path) -> Path:
    return design_dir / "sampled.toml"


def _scene_step_path(design_dir: Path) -> Path:
    return design_dir / "type2_scene.step"


def _step_ledger_path(design_dir: Path) -> Path:
    return design_dir / "type2_step_ledger.json"


def _imported_ledger_path(design_dir: Path) -> Path:
    return design_dir / "type2_imported_ledger.json"


def _aedt_path(design_dir: Path, *, design_id: str) -> Path:
    return design_dir / f"{design_id}.aedt"


def build_sample_manifest_entry(
    *,
    design_id: str,
    seed: int,
    sample_index: int,
    retry_number: int,
    source_toml_path: Path,
    design_dir: Path,
    sampled_owner_paths: tuple[str, ...],
) -> Type2SampleManifestEntry:
    return {
        "design_id": design_id,
        "seed": seed,
        "sample_index": sample_index,
        "retry_number": retry_number,
        "source_toml_path": str(source_toml_path.resolve(strict=False)),
        "sampled_toml_path": str(_sampled_toml_path(design_dir)),
        "design_dir": str(design_dir),
        "scene_step_path": str(_scene_step_path(design_dir)),
        "step_ledger_path": str(_step_ledger_path(design_dir)),
        "imported_ledger_path": str(_imported_ledger_path(design_dir)),
        "aedt_path": str(_aedt_path(design_dir, design_id=design_id)),
        "sampled_owner_paths": list(sampled_owner_paths),
    }


def build_type2_sample_manifest_config(
    *,
    source_toml_path: Path,
    seed_first: int,
    seed_n: int,
    sampler_n: int,
    make_step_on_sample: bool,
    aedt_builder_n: int,
) -> Type2SampleManifestConfig:
    if seed_n < 1:
        raise ValueError("seed_n must be >= 1")
    if sampler_n < 1:
        raise ValueError("sampler_n must be >= 1")
    if not isinstance(make_step_on_sample, bool):
        raise TypeError("make_step_on_sample must be bool")
    if aedt_builder_n < 1:
        raise ValueError("aedt_builder_n must be >= 1")
    return {
        "source_toml_path": str(source_toml_path.resolve(strict=False)),
        "seed_first": seed_first,
        "seed_n": seed_n,
        "sampler_n": sampler_n,
        "make_step_on_sample": make_step_on_sample,
        "aedt_builder_n": aedt_builder_n,
    }


def build_type2_sample_manifest_document(
    *,
    config: Type2SampleManifestConfig,
    entries: list[Type2SampleManifestEntry],
    skipped: list[Type2SampleSkippedEntry],
) -> Type2SampleManifestDocument:
    config_copy: Type2SampleManifestConfig = {
        "source_toml_path": config["source_toml_path"],
        "seed_first": config["seed_first"],
        "seed_n": config["seed_n"],
        "sampler_n": config["sampler_n"],
        "make_step_on_sample": config["make_step_on_sample"],
        "aedt_builder_n": config["aedt_builder_n"],
    }
    entry_copies: list[Type2SampleManifestEntry] = []
    for entry in entries:
        entry_copies.append(
            {
                "design_id": entry["design_id"],
                "seed": entry["seed"],
                "sample_index": entry["sample_index"],
                "retry_number": entry["retry_number"],
                "source_toml_path": entry["source_toml_path"],
                "sampled_toml_path": entry["sampled_toml_path"],
                "design_dir": entry["design_dir"],
                "scene_step_path": entry["scene_step_path"],
                "step_ledger_path": entry["step_ledger_path"],
                "imported_ledger_path": entry["imported_ledger_path"],
                "aedt_path": entry["aedt_path"],
                "sampled_owner_paths": list(entry["sampled_owner_paths"]),
            }
        )
    return {
        "config": config_copy,
        "entries": entry_copies,
        "skipped": copy_type2_sample_skipped_entries(skipped),
    }


def _build_sample_manifest_entry_for_seed(
    *,
    source_toml_path: Path,
    output_dir: Path,
    source_spec: Type2StepSpec,
    raw_source_spec: TOMLTable,
    seed: int,
    sample_index: int,
    head_hash4: str,
) -> Type2SampleManifestEntry:
    constraints = _parse_constraints(raw_source_spec, source_spec)
    sampled_values: tuple[tuple[str, SampledScalar], ...] | None = None
    retry_number: int | None = None
    last_constraint_failure: ValueError | None = None
    for attempt in range(_TYPE2_CONSTRAINT_RETRY_LIMIT):
        candidate_values = sampled_owner_values(
            source_spec,
            seed=seed,
            retry_number=attempt,
        )
        try:
            _require_constraints_satisfied(source_spec, dict(candidate_values), constraints)
        except ValueError as exc:
            last_constraint_failure = exc
            continue
        sampled_values = sampled_owner_values(
            source_spec,
            seed=seed,
            retry_number=attempt,
        )
        retry_number = attempt
        break
    if sampled_values is None or retry_number is None:
        if last_constraint_failure is None:
            raise RuntimeError("type2 constraint retry failed without a captured constraint error")
        raise ValueError(
            "type2 constraints could not be satisfied within retry limit "
            f"(seed={seed}, sample_index={sample_index}, retry_limit={_TYPE2_CONSTRAINT_RETRY_LIMIT})"
        ) from last_constraint_failure
    sampled_table = _sampled_toml_table(
        raw_source_spec,
        source_spec,
        source_toml_path=source_toml_path,
        seed=seed,
        sample_index=sample_index,
        head_hash4=head_hash4,
        retry_number=retry_number,
        sampled_values=sampled_values,
    )
    sampled_toml_text = toml_dumps(sampled_table)
    generated_hash4 = _hash4_from_bytes(sampled_toml_text.encode("utf-8"))
    design_id = build_type2_design_id(
        sample_index=sample_index,
        generated_hash4=generated_hash4,
        head_hash4=head_hash4,
        retry_number=retry_number,
    )
    design_dir = _design_dir(output_dir, design_id=design_id)
    design_dir.mkdir(parents=True, exist_ok=True)
    sampled_toml_path = _sampled_toml_path(design_dir)
    sampled_toml_path.write_text(sampled_toml_text, encoding="utf-8")
    return build_sample_manifest_entry(
        design_id=design_id,
        seed=seed,
        sample_index=sample_index,
        retry_number=retry_number,
        source_toml_path=source_toml_path,
        design_dir=design_dir,
        sampled_owner_paths=tuple(owner_path for owner_path, _ in sampled_values),
    )


def _remove_failed_step_design_dir(*, design_dir: Path, output_dir: Path, sample_index: int) -> None:
    output_root = output_dir.resolve(strict=False)
    resolved_design_dir = design_dir.resolve(strict=False)
    try:
        resolved_design_dir.relative_to(output_root)
    except ValueError as exc:
        raise RuntimeError(
            f"unsafe step-failure cleanup path outside output_dir: sample_index={sample_index}, design_dir={resolved_design_dir}, output_dir={output_root}"
        ) from exc
    if resolved_design_dir.exists():
        shutil.rmtree(resolved_design_dir)


def _no_op_sample_step_stage_reporter(
    phase: _SampleStepStage,
    entry: Type2SampleManifestEntry,
) -> None:
    pass


def _no_op_sample_skip_progress_reporter(
    completed: int,
    total: int,
    skipped: Type2SampleSkippedEntry,
) -> None:
    pass


def _export_step_for_sample_entry(
    entry: Type2SampleManifestEntry,
    *,
    exporter: _SampleExporter,
    report_step_stage: _SampleStepStageReporter = _no_op_sample_step_stage_reporter,
) -> None:
    report_step_stage("start", entry)
    exporter(
        toml_path=Path(entry["sampled_toml_path"]),
        output_dir=Path(entry["design_dir"]),
        ledger_path=Path(entry["step_ledger_path"]),
        seed=entry["seed"],
        stage_reporter=lambda phase: report_step_stage(phase, entry),
    )
    report_step_stage("done", entry)


def _is_skipped_manifest_entry(
    value: Type2SampleManifestEntry | Type2SampleSkippedEntry,
) -> TypeGuard[Type2SampleSkippedEntry]:
    return "phase" in value and "error_type" in value


def _build_sample_manifest_entry_for_seed_task(
    task: tuple[str, str, int, int, str, bool],
) -> Type2SampleManifestEntry | Type2SampleSkippedEntry:
    source_toml_path_text, output_dir_text, seed, sample_index, head_hash4, make_step_on_sample = task
    source_toml_path = Path(source_toml_path_text)
    output_dir = Path(output_dir_text)
    source_spec = _load_type2_step_spec(source_toml_path)
    raw_source_spec, _raw_source_bytes = load_toml_bytes(source_toml_path)
    _require_not_sampled_source(raw_source_spec, context=str(source_toml_path))
    try:
        entry = _build_sample_manifest_entry_for_seed(
            source_toml_path=source_toml_path,
            output_dir=output_dir,
            source_spec=source_spec,
            raw_source_spec=raw_source_spec,
            seed=seed,
            sample_index=sample_index,
            head_hash4=head_hash4,
        )
    except (ValueError, RuntimeError) as exc:
        return build_type2_sample_skipped_entry(
            seed=seed,
            sample_index=sample_index,
            phase="sample",
            exc=exc,
        )
    if make_step_on_sample:
        try:
            _export_step_for_sample_entry(entry, exporter=_default_sample_exporter)
        except (ValueError, RuntimeError) as exc:
            _remove_failed_step_design_dir(
                design_dir=Path(entry["design_dir"]),
                output_dir=output_dir,
                sample_index=sample_index,
            )
            return build_type2_sample_skipped_entry(
                seed=seed,
                sample_index=sample_index,
                phase="step",
                exc=exc,
            )
    return entry


def _emit_sample_progress(
    *,
    report_progress: _SampleProgressReporter | None,
    completed: int,
    total: int,
    entry: Type2SampleManifestEntry,
) -> None:
    if report_progress is not None:
        report_progress(completed, total, entry)


def _emit_sample_skip_progress(
    *,
    report_skipped: _SampleSkippedProgressReporter,
    completed: int,
    total: int,
    skipped: Type2SampleSkippedEntry,
) -> None:
    report_skipped(completed, total, skipped)


def _emit_sample_phase_progress(
    *,
    completed: int,
    total: int,
    result: Type2SampleManifestEntry | Type2SampleSkippedEntry,
    report_progress: _SampleProgressReporter | None,
    report_skipped: _SampleSkippedProgressReporter,
) -> None:
    if _is_skipped_manifest_entry(result):
        _emit_sample_skip_progress(
            report_skipped=report_skipped,
            completed=completed,
            total=total,
            skipped=result,
        )
        return
    entry = cast(Type2SampleManifestEntry, result)
    _emit_sample_progress(
        report_progress=report_progress,
        completed=completed,
        total=total,
        entry=entry,
    )


def generate_sample_manifest_entries(
    *,
    source_toml_path: Path,
    output_dir: Path,
    seed_start: int,
    count: int,
    jobs: int = 1,
    make_step_on_sample: bool = True,
    exporter: _SampleExporter = _default_sample_exporter,
    report_progress: _SampleProgressReporter | None = None,
    report_step_stage: _SampleStepStageReporter = _no_op_sample_step_stage_reporter,
    load_type2_step_spec: Callable[[Path], Type2StepSpec] | None = None,
) -> list[Type2SampleManifestEntry]:
    return generate_sample_manifest_attempts(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        seed_start=seed_start,
        count=count,
        jobs=jobs,
        make_step_on_sample=make_step_on_sample,
        exporter=exporter,
        report_progress=report_progress,
        report_step_stage=report_step_stage,
        load_type2_step_spec=load_type2_step_spec,
    )["entries"]


def generate_sample_manifest_attempts(
    *,
    source_toml_path: Path,
    output_dir: Path,
    seed_start: int,
    count: int,
    jobs: int = 1,
    make_step_on_sample: bool = True,
    exporter: _SampleExporter = _default_sample_exporter,
    report_progress: _SampleProgressReporter | None = None,
    report_skipped: _SampleSkippedProgressReporter = _no_op_sample_skip_progress_reporter,
    report_step_stage: _SampleStepStageReporter = _no_op_sample_step_stage_reporter,
    load_type2_step_spec: Callable[[Path], Type2StepSpec] | None = None,
) -> Type2SampleManifestGenerationResult:
    resolved_spec_loader = load_type2_step_spec
    if resolved_spec_loader is None:
        resolved_spec_loader = globals()["load_type2_step_spec"]
    if count < 1:
        raise ValueError("count must be >= 1")
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    if not isinstance(make_step_on_sample, bool):
        raise TypeError("make_step_on_sample must be bool")
    output_dir.mkdir(parents=True, exist_ok=True)
    seed_values = tuple(range(seed_start, seed_start + count))
    head_hash4 = _current_head_hash4()
    if jobs == 1 or count == 1 or (make_step_on_sample and exporter is not _default_sample_exporter):
        source_spec = resolved_spec_loader(source_toml_path)
        raw_source_spec, _raw_source_bytes = load_toml_bytes(source_toml_path)
        _require_not_sampled_source(raw_source_spec, context=str(source_toml_path))
        entries: list[Type2SampleManifestEntry] = []
        skipped: list[Type2SampleSkippedEntry] = []
        for sample_offset, seed in enumerate(seed_values):
            sample_index = seed_start + sample_offset
            completed = sample_offset + 1
            try:
                entry = _build_sample_manifest_entry_for_seed(
                    source_toml_path=source_toml_path,
                    output_dir=output_dir,
                    source_spec=source_spec,
                    raw_source_spec=raw_source_spec,
                    seed=seed,
                    sample_index=sample_index,
                    head_hash4=head_hash4,
                )
            except (ValueError, RuntimeError) as exc:
                skipped_entry = build_type2_sample_skipped_entry(
                    seed=seed,
                    sample_index=sample_index,
                    phase="sample",
                    exc=exc,
                )
                skipped.append(skipped_entry)
                _emit_sample_phase_progress(
                    completed=completed,
                    total=count,
                    result=skipped_entry,
                    report_progress=report_progress,
                    report_skipped=report_skipped,
                )
                continue
            if make_step_on_sample:
                try:
                    _export_step_for_sample_entry(
                        entry,
                        exporter=exporter,
                        report_step_stage=report_step_stage,
                    )
                except (ValueError, RuntimeError) as exc:
                    _remove_failed_step_design_dir(
                        design_dir=Path(entry["design_dir"]),
                        output_dir=output_dir,
                        sample_index=sample_index,
                    )
                    skipped_entry = build_type2_sample_skipped_entry(
                        seed=seed,
                        sample_index=sample_index,
                        phase="step",
                        exc=exc,
                    )
                    skipped.append(skipped_entry)
                    _emit_sample_phase_progress(
                        completed=completed,
                        total=count,
                        result=skipped_entry,
                        report_progress=report_progress,
                        report_skipped=report_skipped,
                    )
                    continue
            entries.append(entry)
            _emit_sample_progress(
                report_progress=report_progress,
                completed=completed,
                total=count,
                entry=entry,
            )
        return {
            "entries": entries,
            "skipped": skipped,
        }

    tasks = []
    for sample_offset, seed in enumerate(seed_values):
        sample_index = seed_start + sample_offset
        tasks.append(
            (str(source_toml_path), str(output_dir), seed, sample_index, head_hash4, make_step_on_sample)
        )
    results_by_index: dict[int, Type2SampleManifestEntry | Type2SampleSkippedEntry] = {}
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        future_by_index = {
            executor.submit(
                _build_sample_manifest_entry_for_seed_task,
                task,
            ): task[3]
            for task in tasks
        }
        completed = 0
        for future in as_completed(future_by_index):
            result = future.result()
            completed += 1
            sample_index = future_by_index[future]
            if sample_index in results_by_index:
                raise RuntimeError(f"duplicate sample result for sample_index={sample_index}")
            results_by_index[sample_index] = result
            _emit_sample_phase_progress(
                completed=completed,
                total=count,
                result=result,
                report_progress=report_progress,
                report_skipped=report_skipped,
            )
    entries: list[Type2SampleManifestEntry] = []
    skipped: list[Type2SampleSkippedEntry] = []
    for sample_index in seed_values:
        if sample_index not in results_by_index:
            raise RuntimeError(
                f"missing generated manifest result for sample_index={sample_index}; completed={len(results_by_index)}/{len(seed_values)}"
            )
        result = results_by_index[sample_index]
        if _is_skipped_manifest_entry(result):
            skipped.append(result)
        else:
            entries.append(cast(Type2SampleManifestEntry, result))
    return {
        "entries": entries,
        "skipped": skipped,
    }


def write_type2_sample_manifest(*, document: Type2SampleManifestDocument, manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")


def _require_int(value: object, *, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{context} must be int")
    return value


def _load_type2_sample_manifest_config(raw_config: object, *, manifest_path: Path) -> Type2SampleManifestConfig:
    if not isinstance(raw_config, dict):
        raise TypeError(f"type2 sample manifest config must be an object: {manifest_path}")
    required_fields = (
        "source_toml_path",
        "seed_first",
        "seed_n",
        "sampler_n",
        "make_step_on_sample",
        "aedt_builder_n",
    )
    for field_name in required_fields:
        if field_name not in raw_config:
            raise ValueError(f"type2 sample manifest config is missing required key {field_name!r}")
    seed_first = _require_int(raw_config["seed_first"], context="config.seed_first")
    seed_n = _require_int(raw_config["seed_n"], context="config.seed_n")
    sampler_n = _require_int(raw_config["sampler_n"], context="config.sampler_n")
    make_step_on_sample = _require_bool(raw_config["make_step_on_sample"], context="config.make_step_on_sample")
    aedt_builder_n = _require_int(raw_config["aedt_builder_n"], context="config.aedt_builder_n")
    if seed_n < 1:
        raise ValueError("config.seed_n must be >= 1")
    if sampler_n < 1:
        raise ValueError("config.sampler_n must be >= 1")
    if aedt_builder_n < 1:
        raise ValueError("config.aedt_builder_n must be >= 1")
    return {
        "source_toml_path": _require_non_empty_str(raw_config["source_toml_path"], context="config.source_toml_path"),
        "seed_first": seed_first,
        "seed_n": seed_n,
        "sampler_n": sampler_n,
        "make_step_on_sample": make_step_on_sample,
        "aedt_builder_n": aedt_builder_n,
    }


def _load_type2_sample_manifest_entries(raw_entries: object) -> list[Type2SampleManifestEntry]:
    if not isinstance(raw_entries, list):
        raise TypeError("type2 sample manifest entries must be a list")
    entries: list[Type2SampleManifestEntry] = []
    for index, raw_entry in enumerate(raw_entries):
        if not isinstance(raw_entry, dict):
            raise TypeError(f"type2 sample manifest entries[{index}] must be a table/object")
        required_fields = (
            "design_id",
            "seed",
            "sample_index",
            "retry_number",
            "source_toml_path",
            "sampled_toml_path",
            "design_dir",
            "scene_step_path",
            "step_ledger_path",
            "imported_ledger_path",
            "aedt_path",
            "sampled_owner_paths",
        )
        for field_name in required_fields:
            if field_name not in raw_entry:
                raise ValueError(f"type2 sample manifest entries[{index}] is missing required key {field_name!r}")
        sampled_owner_paths = raw_entry["sampled_owner_paths"]
        if not isinstance(sampled_owner_paths, list) or not all(isinstance(item, str) for item in sampled_owner_paths):
            raise TypeError(f"type2 sample manifest entries[{index}].sampled_owner_paths must be a list of strings")
        entries.append(
            {
                "design_id": _require_non_empty_str(raw_entry["design_id"], context=f"entries[{index}].design_id"),
                "seed": _require_int(raw_entry["seed"], context=f"entries[{index}].seed"),
                "sample_index": _require_int(raw_entry["sample_index"], context=f"entries[{index}].sample_index"),
                "retry_number": _require_int(raw_entry["retry_number"], context=f"entries[{index}].retry_number"),
                "source_toml_path": _require_non_empty_str(
                    raw_entry["source_toml_path"], context=f"entries[{index}].source_toml_path"
                ),
                "sampled_toml_path": _require_non_empty_str(
                    raw_entry["sampled_toml_path"], context=f"entries[{index}].sampled_toml_path"
                ),
                "design_dir": _require_non_empty_str(raw_entry["design_dir"], context=f"entries[{index}].design_dir"),
                "scene_step_path": _require_non_empty_str(
                    raw_entry["scene_step_path"], context=f"entries[{index}].scene_step_path"
                ),
                "step_ledger_path": _require_non_empty_str(
                    raw_entry["step_ledger_path"], context=f"entries[{index}].step_ledger_path"
                ),
                "imported_ledger_path": _require_non_empty_str(
                    raw_entry["imported_ledger_path"], context=f"entries[{index}].imported_ledger_path"
                ),
                "aedt_path": _require_non_empty_str(raw_entry["aedt_path"], context=f"entries[{index}].aedt_path"),
                "sampled_owner_paths": list(sampled_owner_paths),
            }
        )
    return entries


def load_type2_sample_manifest(manifest_path: Path) -> Type2SampleManifestDocument:
    if not manifest_path.is_file():
        raise FileNotFoundError(f"type2 sample manifest not found: {manifest_path}")
    raw_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        raise TypeError("type2 sample manifest must be an object")
    if "config" not in raw_payload:
        raise ValueError("type2 sample manifest is missing required key 'config'")
    if "entries" not in raw_payload:
        raise ValueError("type2 sample manifest is missing required key 'entries'")
    if "skipped" in raw_payload:
        skipped = load_type2_sample_skipped_entries(raw_payload["skipped"])
    else:
        skipped = []
    config = _load_type2_sample_manifest_config(raw_payload["config"], manifest_path=manifest_path)
    entries = _load_type2_sample_manifest_entries(raw_payload["entries"])
    return {
        "config": config,
        "entries": entries,
        "skipped": skipped,
    }


def _require_non_empty_str(value: object, *, context: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{context} must be str")
    if value == "":
        raise ValueError(f"{context} must be non-empty")
    return value


def _require_bool(value: object, *, context: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{context} must be bool")
    return value


def load_type2_sample_metadata(sampled_toml_path: Path) -> Type2SampleMetadata:
    raw_spec, _raw_bytes = load_toml_bytes(sampled_toml_path)
    if _SAMPLED_METADATA_TABLE not in raw_spec:
        raise ValueError(f"type2 sampled TOML is missing required [{_SAMPLED_METADATA_TABLE}] metadata: {sampled_toml_path}")
    raw_metadata = raw_spec[_SAMPLED_METADATA_TABLE]
    if not isinstance(raw_metadata, dict):
        raise TypeError(f"{sampled_toml_path}:{_SAMPLED_METADATA_TABLE} must be a table/object")
    required_fields = ("source_toml_path", "seed", "sample_index", "head_hash4", "retry_number", "sampled_owner_paths")
    for field_name in required_fields:
        if field_name not in raw_metadata:
            raise ValueError(f"{sampled_toml_path}:{_SAMPLED_METADATA_TABLE} is missing required key {field_name!r}")
    raw_seed = raw_metadata["seed"]
    if isinstance(raw_seed, bool) or not isinstance(raw_seed, int):
        raise TypeError(f"{sampled_toml_path}:{_SAMPLED_METADATA_TABLE}.seed must be int")
    raw_sample_index = raw_metadata["sample_index"]
    if isinstance(raw_sample_index, bool) or not isinstance(raw_sample_index, int):
        raise TypeError(f"{sampled_toml_path}:{_SAMPLED_METADATA_TABLE}.sample_index must be int")
    raw_retry_number = raw_metadata["retry_number"]
    if isinstance(raw_retry_number, bool) or not isinstance(raw_retry_number, int):
        raise TypeError(f"{sampled_toml_path}:{_SAMPLED_METADATA_TABLE}.retry_number must be int")
    head_hash4 = _require_non_empty_str(
        raw_metadata["head_hash4"],
        context=f"{sampled_toml_path}:{_SAMPLED_METADATA_TABLE}.head_hash4",
    )
    if len(head_hash4) != 4:
        raise ValueError(f"{sampled_toml_path}:{_SAMPLED_METADATA_TABLE}.head_hash4 must be 4 chars")
    raw_sampled_owner_paths = raw_metadata["sampled_owner_paths"]
    if not isinstance(raw_sampled_owner_paths, list):
        raise TypeError(f"{sampled_toml_path}:{_SAMPLED_METADATA_TABLE}.sampled_owner_paths must be a list")
    sampled_owner_paths: list[str] = []
    seen_owner_paths: set[str] = set()
    for index, raw_owner_path in enumerate(raw_sampled_owner_paths):
        owner_path = _require_non_empty_str(
            raw_owner_path,
            context=f"{sampled_toml_path}:{_SAMPLED_METADATA_TABLE}.sampled_owner_paths[{index}]",
        )
        if owner_path in seen_owner_paths:
            raise ValueError(f"duplicate sampled owner path in {sampled_toml_path}: {owner_path}")
        seen_owner_paths.add(owner_path)
        sampled_owner_paths.append(owner_path)
    return {
        "source_toml_path": _require_non_empty_str(
            raw_metadata["source_toml_path"], context=f"{sampled_toml_path}:{_SAMPLED_METADATA_TABLE}.source_toml_path"
        ),
        "seed": raw_seed,
        "sample_index": raw_sample_index,
        "head_hash4": head_hash4,
        "retry_number": raw_retry_number,
        "sampled_owner_paths": sampled_owner_paths,
    }


def _design_id_from_sampled_toml_bytes(
    metadata: Type2SampleMetadata,
    *,
    sampled_toml_bytes: bytes,
) -> str:
    return build_type2_design_id(
        sample_index=metadata["sample_index"],
        generated_hash4=_hash4_from_bytes(sampled_toml_bytes),
        head_hash4=metadata["head_hash4"],
        retry_number=metadata["retry_number"],
    )


def manifest_entry_for_sample_index(
    manifest_path: Path,
    *,
    sample_index: int,
) -> Type2SampleManifestEntry:
    if sample_index < 0:
        raise ValueError(f"sample_index must be >= 0 (actual={sample_index})")
    document = load_type2_sample_manifest(manifest_path)
    entries = document["entries"]
    matching_entries = [
        entry
        for entry in entries
        if entry["sample_index"] == sample_index
    ]
    if len(matching_entries) == 0:
        raise ValueError(
            f"type2 sample manifest has no entry for sample_index={sample_index}; available="
            f"{[entry['sample_index'] for entry in entries]}"
        )
    if len(matching_entries) > 1:
        raise RuntimeError(f"type2 sample manifest has duplicate entries for sample_index={sample_index}")
    return matching_entries[0]


def _range_scalar_from_sampled_toml(spec: Type2StepSpec, owner_path: str) -> SampledScalar:
    range_spec = _range_spec_for_owner_path(spec, owner_path)
    if range_spec.count != 1:
        raise ValueError(f"type2 sampled TOML must freeze sampled owner to count=1: {owner_path}")
    if range_spec.start != range_spec.end:
        raise ValueError(f"type2 sampled TOML must freeze sampled owner with identical bounds: {owner_path}")
    if range_spec.is_integer:
        return int(range_spec.start)
    return float(range_spec.start)


def _design_variable_name(owner_path: str) -> str:
    chars: list[str] = []
    for char in owner_path:
        if char.isalnum() or char == "_":
            chars.append(char)
        else:
            chars.append("_")
    variable_name = "".join(chars).strip("_")
    if variable_name == "":
        raise ValueError(f"type2 design variable name must not be empty after sanitization: {owner_path}")
    return variable_name


def _design_variable_expression(owner_path: str, value: SampledScalar) -> str:
    field_name = owner_path.split(".")[-1]
    if field_name in {"equivalent_turn_count", "turn_weight_a", "turn_weight_b", "turn_weight_c"}:
        return str(float(value))
    if field_name in _INTEGER_RANGE_FIELD_NAMES:
        return str(int(value))
    if field_name.endswith("_ratio") or field_name.endswith("_factor") or "_over_" in field_name:
        return str(float(value))
    if field_name.endswith("_mm"):
        return f"{float(value)}mm"
    raise ValueError(f"Unsupported type2 design variable unit contract for sampled owner: {owner_path}")


def _manifest_entry_from_sampled_toml(metadata: Type2SampleMetadata, sampled_toml_path: Path) -> Type2SampleManifestEntry:
    design_dir = sampled_toml_path.parent.resolve(strict=False)
    sampled_toml_bytes = sampled_toml_path.read_bytes()
    design_id = _design_id_from_sampled_toml_bytes(metadata, sampled_toml_bytes=sampled_toml_bytes)
    return {
        "design_id": design_id,
        "seed": metadata["seed"],
        "sample_index": metadata["sample_index"],
        "retry_number": metadata["retry_number"],
        "source_toml_path": metadata["source_toml_path"],
        "sampled_toml_path": str(sampled_toml_path.resolve(strict=False)),
        "design_dir": str(design_dir),
        "scene_step_path": str(_scene_step_path(design_dir)),
        "step_ledger_path": str(_step_ledger_path(design_dir)),
        "imported_ledger_path": str(_imported_ledger_path(design_dir)),
        "aedt_path": str(_aedt_path(design_dir, design_id=design_id)),
        "sampled_owner_paths": list(metadata["sampled_owner_paths"]),
    }


def prepare_type2_build(
    sampled_toml_path: Path,
    *,
    load_type2_step_spec: Callable[[Path], Type2StepSpec] | None = None,
) -> PreparedType2Build:
    resolved_spec_loader = load_type2_step_spec
    if resolved_spec_loader is None:
        resolved_spec_loader = globals()["load_type2_step_spec"]
    metadata = load_type2_sample_metadata(sampled_toml_path)
    sampled_spec = resolved_spec_loader(sampled_toml_path)
    sampled_modeled_roles = _modeled_roles(sampled_spec)
    source_toml_path = Path(metadata["source_toml_path"]).resolve(strict=False)
    if not source_toml_path.is_file():
        raise FileNotFoundError(f"type2 sampled TOML references missing source_toml_path: {source_toml_path}")
    source_spec = resolved_spec_loader(source_toml_path)
    source_modeled_roles = _modeled_roles(source_spec)
    if sampled_modeled_roles != source_modeled_roles:
        raise ValueError(
            "type2 build input TOML modeled roles must match source TOML "
            f"(expected={source_modeled_roles}, actual={sampled_modeled_roles})"
        )
    expected_sampled_owner_paths = exportable_sampled_owner_paths_for_seed(source_spec, seed=metadata["seed"])
    if tuple(metadata["sampled_owner_paths"]) != expected_sampled_owner_paths:
        raise ValueError(
            "type2 sampled TOML metadata must exactly match source exportable sampled owners "
            f"(expected={expected_sampled_owner_paths}, actual={tuple(metadata['sampled_owner_paths'])})"
        )
    expected_owner_path_set = set(expected_sampled_owner_paths)
    for owner_path, range_spec in _all_range_owner_specs(sampled_spec):
        if owner_path in expected_owner_path_set:
            if range_spec.count != 1:
                raise ValueError(f"type2 build input TOML must freeze sampled owner to count=1: {owner_path}")
            if range_spec.start != range_spec.end:
                raise ValueError(f"type2 build input TOML must freeze sampled owner with identical bounds: {owner_path}")
            continue
        if range_spec.count != 1:
            raise ValueError(f"type2 build input TOML must freeze non-sampled range owners to count=1: {owner_path}")
        if range_spec.start != range_spec.end:
            raise ValueError(
                f"type2 build input TOML must freeze non-sampled range owners with identical bounds: {owner_path}"
            )
    design_variables = tuple(
        (
            _design_variable_name(owner_path),
            _design_variable_expression(owner_path, _range_scalar_from_sampled_toml(sampled_spec, owner_path)),
        )
        for owner_path in metadata["sampled_owner_paths"]
    )
    manifest_entry = _manifest_entry_from_sampled_toml(metadata, sampled_toml_path)
    return PreparedType2Build(
        design_id=manifest_entry["design_id"],
        seed=manifest_entry["seed"],
        source_toml_path=source_toml_path,
        sampled_toml_path=Path(manifest_entry["sampled_toml_path"]),
        design_dir=Path(manifest_entry["design_dir"]),
        scene_step_path=Path(manifest_entry["scene_step_path"]),
        step_ledger_path=Path(manifest_entry["step_ledger_path"]),
        imported_ledger_path=Path(manifest_entry["imported_ledger_path"]),
        aedt_path=Path(manifest_entry["aedt_path"]),
        sampled_owner_paths=tuple(manifest_entry["sampled_owner_paths"]),
        modeled_roles=source_modeled_roles,
        design_variables=design_variables,
    )


def prepared_builds_from_manifest(
    manifest_path: Path,
    *,
    selected_design_ids: tuple[str, ...],
    load_type2_step_spec: Callable[[Path], Type2StepSpec] | None = None,
) -> tuple[PreparedType2Build, ...]:
    resolved_spec_loader = load_type2_step_spec
    if resolved_spec_loader is None:
        resolved_spec_loader = globals()["load_type2_step_spec"]
    requested_design_ids = set(selected_design_ids)
    source_spec_cache: dict[Path, Type2StepSpec] = {}

    def cached_spec_loader(path: Path) -> Type2StepSpec:
        resolved_path = path.resolve(strict=False)
        if resolved_path.name == "sampled.toml":
            return resolved_spec_loader(resolved_path)
        if resolved_path not in source_spec_cache:
            source_spec_cache[resolved_path] = resolved_spec_loader(resolved_path)
        return source_spec_cache[resolved_path]

    prepared_builds: list[PreparedType2Build] = []
    selected_found: set[str] = set()
    for entry in iter_type2_sample_manifest_entries(manifest_path, selected_design_ids=selected_design_ids):
        design_id = entry["design_id"]
        selected_found.add(design_id)
        prepared_builds.append(prepare_type2_build(Path(entry["sampled_toml_path"]), load_type2_step_spec=cached_spec_loader))
    missing_design_ids = requested_design_ids - selected_found
    if missing_design_ids:
        raise ValueError(f"type2 sample manifest is missing requested design ids: {sorted(missing_design_ids)}")
    return tuple(prepared_builds)


def _stream_manifest_json_value(manifest_path: Path, *, key: str) -> Iterator[object]:
    decoder = json.JSONDecoder()
    needle = json.dumps(key)
    buffer = ""
    position = 0
    found_key = False
    found_array = False
    eof = False
    file_size = manifest_path.stat().st_size

    with manifest_path.open("r", encoding="utf-8") as manifest_file:
        def read_more(*, compact: bool) -> None:
            nonlocal buffer, position, eof
            if eof:
                return
            if compact:
                buffer = buffer[position:]
                position = 0
            buffer += manifest_file.read(_MANIFEST_STREAM_CHUNK_SIZE)
            eof = manifest_file.tell() == file_size

        while True:
            if not buffer or (not eof and position >= len(buffer) - _MANIFEST_STREAM_CHUNK_SIZE // 2):
                read_more(compact=True)

            if not found_key:
                key_position = buffer.find(needle, position)
                if key_position < 0:
                    if eof:
                        raise ValueError(f"type2 sample manifest is missing key {key!r}: {manifest_path}")
                    position = max(0, len(buffer) - len(needle))
                    read_more(compact=True)
                    continue
                colon_position = buffer.find(":", key_position + len(needle))
                if colon_position < 0:
                    if eof:
                        raise ValueError(f"type2 sample manifest key {key!r} is missing ':'")
                    position = key_position
                    read_more(compact=True)
                    continue
                found_key = True
                position = colon_position + 1

            while True:
                while position < len(buffer) and buffer[position].isspace():
                    position += 1
                if position >= len(buffer) and not eof:
                    read_more(compact=True)
                    break
                if key != "entries":
                    try:
                        value, end_position = decoder.raw_decode(buffer, position)
                    except json.JSONDecodeError:
                        if eof:
                            raise
                        read_more(compact=False)
                        break
                    yield value
                    position = end_position
                    return
                if not found_array:
                    if position >= len(buffer):
                        if eof:
                            raise ValueError(f"type2 sample manifest key {key!r} is missing array value")
                        read_more(compact=True)
                        break
                    if buffer[position] != "[":
                        raise TypeError(f"type2 sample manifest key {key!r} must be an array")
                    found_array = True
                    position += 1
                while position < len(buffer) and buffer[position].isspace():
                    position += 1
                if position >= len(buffer) and not eof:
                    read_more(compact=True)
                    break
                if position < len(buffer) and buffer[position] == "]":
                    return
                if position < len(buffer) and buffer[position] == ",":
                    position += 1
                    continue
                try:
                    value, end_position = decoder.raw_decode(buffer, position)
                except json.JSONDecodeError:
                    if eof:
                        raise
                    read_more(compact=False)
                    break
                yield value
                position = end_position


def load_type2_sample_manifest_config(manifest_path: Path) -> Type2SampleManifestConfig:
    if not manifest_path.is_file():
        raise FileNotFoundError(f"type2 sample manifest not found: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as manifest_file:
        while True:
            character = manifest_file.read(1)
            if character == "":
                raise TypeError("type2 sample manifest must be an object")
            if character.isspace():
                continue
            if character != "{":
                raise TypeError("type2 sample manifest must be an object")
            break
    value = next(_stream_manifest_json_value(manifest_path, key="config"))
    return _load_type2_sample_manifest_config(value, manifest_path=manifest_path)


def iter_type2_sample_manifest_entries(
    manifest_path: Path,
    *,
    selected_design_ids: tuple[str, ...] = (),
) -> Iterator[Type2SampleManifestEntry]:
    requested_design_ids = set(selected_design_ids)
    selected_found: set[str] = set()
    for value in _stream_manifest_json_value(manifest_path, key="entries"):
        if not isinstance(value, dict):
            raise TypeError(f"type2 sample manifest entry must be object: {manifest_path}")
        entry = _load_type2_sample_manifest_entries([value])[0]
        design_id = entry["design_id"]
        if requested_design_ids and design_id not in requested_design_ids:
            continue
        selected_found.add(design_id)
        yield entry
    missing_design_ids = requested_design_ids - selected_found
    if missing_design_ids:
        raise ValueError(f"type2 sample manifest is missing requested design ids: {sorted(missing_design_ids)}")


__all__ = [
    "DesignVariableEntry",
    "PreparedType2Build",
    "Type2SampleManifestConfig",
    "Type2SampleManifestDocument",
    "Type2SampleManifestGenerationResult",
    "Type2SampleManifestEntry",
    "Type2SampleMetadata",
    "Type2SampleSkippedEntry",
    "build_type2_design_id",
    "build_type2_sample_manifest_config",
    "build_type2_sample_manifest_document",
    "build_sample_manifest_entry",
    "exportable_sampled_owner_paths",
    "exportable_sampled_owner_paths_for_seed",
    "generate_sample_manifest_entries",
    "generate_sample_manifest_attempts",
    "load_type2_sample_manifest",
    "load_type2_sample_manifest_config",
    "load_type2_sample_metadata",
    "iter_type2_sample_manifest_entries",
    "manifest_entry_for_sample_index",
    "prepare_type2_build",
    "prepared_builds_from_manifest",
    "sampled_owner_values",
    "write_type2_sample_manifest",
]

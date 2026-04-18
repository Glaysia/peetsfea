from __future__ import annotations

import copy
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

from peetsfea.spec.loader import TOMLTable, TOMLValue, load_toml_bytes
from peetsfea.spec.toml_render import toml_dumps
from peetsfea.type2_step_spec import ModeledSingleCoilSpec, ModeledTxSingleCoilSpec, RangeSpec, Type2StepSpec, load_type2_step_spec

SampledScalar = int | float
DesignVariableEntry = tuple[str, str]
_INTEGER_RANGE_FIELD_NAMES = ("turn_count", "layer_count", "underlay_repeat_count")
_MODELED_RANGE_FIELD_NAMES = (
    "outer_x_mm",
    "outer_y_mm",
    "turn_count",
    "layer_count",
    "underlay_repeat_count",
    "underlay_gap_mm",
    "layer_gap_mm",
    "terminal_stub_length_mm",
    "void_x_over_outer_x",
    "void_y_over_outer_y",
    "void_center_x_over_outer_x",
    "void_center_y_over_outer_y",
    "margin_ratio",
    "metal_fill_factor",
)
_SAMPLED_METADATA_TABLE = "sampled"


class Type2SampleMetadata(TypedDict):
    source_toml_path: str
    seed: int
    design_id: str
    sampled_owner_paths: list[str]


class Type2SampleManifestEntry(TypedDict):
    design_id: str
    seed: int
    source_toml_path: str
    sampled_toml_path: str
    design_dir: str
    scene_step_path: str
    step_ledger_path: str
    imported_ledger_path: str
    aedt_path: str
    sampled_owner_paths: list[str]


class Type2SampleManifestConfig(TypedDict):
    source_toml_path: str
    seed_first: int
    seed_n: int
    sampler_n: int
    step_builder_n: int
    aedt_builder_n: int


class Type2SampleManifestDocument(TypedDict):
    config: Type2SampleManifestConfig
    entries: list[Type2SampleManifestEntry]


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
    design_variables: tuple[DesignVariableEntry, ...]


def _modeled_range_owner_specs(spec: Type2StepSpec) -> tuple[tuple[str, RangeSpec], ...]:
    owner_specs: list[tuple[str, RangeSpec]] = []
    for modeled_spec in spec.modeled_objects:
        for field_name in _MODELED_RANGE_FIELD_NAMES:
            if field_name == "underlay_gap_mm":
                if isinstance(modeled_spec, ModeledTxSingleCoilSpec):
                    owner_specs.append(
                        (f"modeled_objects.{modeled_spec.object_id}.{field_name}", modeled_spec.underlay_gap_mm)
                    )
                continue
            assert hasattr(modeled_spec, field_name), f"modeled spec is missing required range field: {field_name}"
            range_spec = getattr(modeled_spec, field_name)
            assert isinstance(range_spec, RangeSpec), f"{field_name} must be RangeSpec"
            owner_specs.append((f"modeled_objects.{modeled_spec.object_id}.{field_name}", range_spec))
    return tuple(owner_specs)


def exportable_sampled_owner_paths(spec: Type2StepSpec) -> tuple[str, ...]:
    return tuple(owner_path for owner_path, range_spec in _modeled_range_owner_specs(spec) if range_spec.count != 1)


def _range_spec_for_owner_path(spec: Type2StepSpec, owner_path: str) -> RangeSpec:
    for candidate_owner_path, range_spec in _modeled_range_owner_specs(spec):
        if candidate_owner_path == owner_path:
            return range_spec
    raise ValueError(f"Unknown type2 sampled owner path: {owner_path}")


def _integer_range_candidates(range_spec: RangeSpec) -> tuple[int, ...]:
    if range_spec.is_integer is not True:
        raise ValueError("integer range candidates require integer range spec")
    if range_spec.count == 1:
        raw_values = (range_spec.start,)
    else:
        step = (range_spec.end - range_spec.start) / float(range_spec.count - 1)
        raw_values = tuple(range_spec.start + (step * index) for index in range(range_spec.count))
    rounded_values = tuple(int(float(value) + 0.5) for value in raw_values)
    deduped_values: list[int] = []
    seen_values: set[int] = set()
    for value in rounded_values:
        if value in seen_values:
            continue
        seen_values.add(value)
        deduped_values.append(value)
    return tuple(deduped_values)


def _float_range_candidates(range_spec: RangeSpec) -> tuple[float, ...]:
    if range_spec.is_integer is not False:
        raise ValueError("float range candidates require non-integer range spec")
    if range_spec.count == 1:
        return (range_spec.start,)
    step = (range_spec.end - range_spec.start) / float(range_spec.count - 1)
    return tuple(range_spec.start + (step * index) for index in range(range_spec.count))


def _selected_value_for_owner_path(range_spec: RangeSpec, *, owner_path: str, seed: int) -> SampledScalar:
    candidates: tuple[SampledScalar, ...]
    if range_spec.is_integer:
        candidates = _integer_range_candidates(range_spec)
    else:
        candidates = _float_range_candidates(range_spec)
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated for sampled owner: {owner_path}")
    if len(candidates) == 1:
        return candidates[0]
    digest = hashlib.blake2b(f"{seed}:{owner_path}".encode("utf-8"), digest_size=8).digest()
    index = int.from_bytes(digest, byteorder="big", signed=False) % len(candidates)
    return candidates[index]


def sampled_owner_values(spec: Type2StepSpec, *, seed: int) -> tuple[tuple[str, SampledScalar], ...]:
    sampled_values: list[tuple[str, SampledScalar]] = []
    for owner_path, range_spec in _modeled_range_owner_specs(spec):
        if range_spec.count == 1:
            continue
        sampled_values.append(
            (owner_path, _selected_value_for_owner_path(range_spec, owner_path=owner_path, seed=seed))
        )
    return tuple(sampled_values)


def _normalize_design_id_digest(source_toml_bytes: bytes, *, seed: int, sampled_values: tuple[tuple[str, SampledScalar], ...]) -> str:
    payload = json.dumps(
        {
            "seed": seed,
            "source_toml_hash": hashlib.blake2b(source_toml_bytes, digest_size=8).hexdigest(),
            "sampled_values": list(sampled_values),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.blake2b(payload.encode("utf-8"), digest_size=5).hexdigest()


def build_type2_design_id(source_toml_bytes: bytes, *, seed: int, sampled_values: tuple[tuple[str, SampledScalar], ...]) -> str:
    return f"s{seed}_{_normalize_design_id_digest(source_toml_bytes, seed=seed, sampled_values=sampled_values)}"


def _sampled_metadata(
    source_toml_path: Path,
    *,
    seed: int,
    design_id: str,
    sampled_owner_paths: tuple[str, ...],
) -> Type2SampleMetadata:
    return {
        "source_toml_path": str(source_toml_path.resolve(strict=False)),
        "seed": seed,
        "design_id": design_id,
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
    matches = [
        entry
        for entry in raw_modeled_objects
        if isinstance(entry, dict) and entry.get("object_id") == object_id
    ]
    if len(matches) != 1:
        raise ValueError(f"type2 source TOML must contain exactly one modeled object with object_id={object_id!r}")
    return cast(TOMLTable, matches[0])


def _freeze_owner_range_in_raw_spec(
    raw_spec: TOMLTable,
    *,
    owner_path: str,
    value: SampledScalar,
    range_spec: RangeSpec,
) -> None:
    owner_parts = owner_path.split(".")
    if len(owner_parts) != 3 or owner_parts[0] != "modeled_objects":
        raise ValueError(f"Unsupported type2 sampled owner path: {owner_path}")
    _, object_id, field_name = owner_parts
    modeled_table = _modeled_object_table(raw_spec, object_id=object_id)
    if field_name not in modeled_table:
        raise ValueError(f"type2 source TOML is missing sampled owner field: {owner_path}")
    raw_field = modeled_table[field_name]
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
    design_id: str,
    sampled_values: tuple[tuple[str, SampledScalar], ...],
) -> TOMLTable:
    sampled_spec = copy.deepcopy(raw_source_spec)
    sampled_owner_paths = tuple(owner_path for owner_path, _ in sampled_values)
    for owner_path, value in sampled_values:
        range_spec = _range_spec_for_owner_path(source_spec, owner_path)
        _freeze_owner_range_in_raw_spec(sampled_spec, owner_path=owner_path, value=value, range_spec=range_spec)
    sampled_spec[_SAMPLED_METADATA_TABLE] = _sampled_metadata(
        source_toml_path,
        seed=seed,
        design_id=design_id,
        sampled_owner_paths=sampled_owner_paths,
    )
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
    source_toml_path: Path,
    design_dir: Path,
    sampled_owner_paths: tuple[str, ...],
) -> Type2SampleManifestEntry:
    return {
        "design_id": design_id,
        "seed": seed,
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
    step_builder_n: int,
    aedt_builder_n: int,
) -> Type2SampleManifestConfig:
    if seed_n < 1:
        raise ValueError("seed_n must be >= 1")
    if sampler_n < 1:
        raise ValueError("sampler_n must be >= 1")
    if step_builder_n < 1:
        raise ValueError("step_builder_n must be >= 1")
    if aedt_builder_n < 1:
        raise ValueError("aedt_builder_n must be >= 1")
    return {
        "source_toml_path": str(source_toml_path.resolve(strict=False)),
        "seed_first": seed_first,
        "seed_n": seed_n,
        "sampler_n": sampler_n,
        "step_builder_n": step_builder_n,
        "aedt_builder_n": aedt_builder_n,
    }


def build_type2_sample_manifest_document(
    *,
    config: Type2SampleManifestConfig,
    entries: list[Type2SampleManifestEntry],
) -> Type2SampleManifestDocument:
    return {
        "config": dict(config),
        "entries": [dict(entry) for entry in entries],
    }


def _build_sample_manifest_entry_for_seed(
    *,
    source_toml_path: Path,
    output_dir: Path,
    source_spec: Type2StepSpec,
    raw_source_spec: TOMLTable,
    raw_source_bytes: bytes,
    seed: int,
) -> Type2SampleManifestEntry:
    sampled_values = sampled_owner_values(source_spec, seed=seed)
    design_id = build_type2_design_id(raw_source_bytes, seed=seed, sampled_values=sampled_values)
    design_dir = _design_dir(output_dir, design_id=design_id)
    design_dir.mkdir(parents=True, exist_ok=True)
    sampled_table = _sampled_toml_table(
        raw_source_spec,
        source_spec,
        source_toml_path=source_toml_path,
        seed=seed,
        design_id=design_id,
        sampled_values=sampled_values,
    )
    sampled_toml_path = _sampled_toml_path(design_dir)
    sampled_toml_path.write_text(toml_dumps(sampled_table), encoding="utf-8")
    return build_sample_manifest_entry(
        design_id=design_id,
        seed=seed,
        source_toml_path=source_toml_path,
        design_dir=design_dir,
        sampled_owner_paths=tuple(owner_path for owner_path, _ in sampled_values),
    )


def _build_sample_manifest_entry_for_seed_task(task: tuple[str, str, int]) -> Type2SampleManifestEntry:
    source_toml_path_text, output_dir_text, seed = task
    source_toml_path = Path(source_toml_path_text)
    output_dir = Path(output_dir_text)
    source_spec = load_type2_step_spec(source_toml_path)
    raw_source_spec, raw_source_bytes = load_toml_bytes(source_toml_path)
    _require_not_sampled_source(raw_source_spec, context=str(source_toml_path))
    return _build_sample_manifest_entry_for_seed(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        source_spec=source_spec,
        raw_source_spec=raw_source_spec,
        raw_source_bytes=raw_source_bytes,
        seed=seed,
    )


def generate_sample_manifest_entries(
    *,
    source_toml_path: Path,
    output_dir: Path,
    seed_start: int,
    count: int,
    jobs: int = 1,
) -> list[Type2SampleManifestEntry]:
    if count < 1:
        raise ValueError("count must be >= 1")
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    output_dir.mkdir(parents=True, exist_ok=True)
    seed_values = tuple(range(seed_start, seed_start + count))
    if jobs == 1 or count == 1:
        source_spec = load_type2_step_spec(source_toml_path)
        raw_source_spec, raw_source_bytes = load_toml_bytes(source_toml_path)
        _require_not_sampled_source(raw_source_spec, context=str(source_toml_path))
        return [
            _build_sample_manifest_entry_for_seed(
                source_toml_path=source_toml_path,
                output_dir=output_dir,
                source_spec=source_spec,
                raw_source_spec=raw_source_spec,
                raw_source_bytes=raw_source_bytes,
                seed=seed,
            )
            for seed in seed_values
        ]
    tasks = [(str(source_toml_path), str(output_dir), seed) for seed in seed_values]
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        return list(executor.map(_build_sample_manifest_entry_for_seed_task, tasks))


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
        "step_builder_n",
        "aedt_builder_n",
    )
    for field_name in required_fields:
        if field_name not in raw_config:
            raise ValueError(f"type2 sample manifest config is missing required key {field_name!r}")
    seed_first = _require_int(raw_config["seed_first"], context="config.seed_first")
    seed_n = _require_int(raw_config["seed_n"], context="config.seed_n")
    sampler_n = _require_int(raw_config["sampler_n"], context="config.sampler_n")
    step_builder_n = _require_int(raw_config["step_builder_n"], context="config.step_builder_n")
    aedt_builder_n = _require_int(raw_config["aedt_builder_n"], context="config.aedt_builder_n")
    if seed_n < 1:
        raise ValueError("config.seed_n must be >= 1")
    if sampler_n < 1:
        raise ValueError("config.sampler_n must be >= 1")
    if step_builder_n < 1:
        raise ValueError("config.step_builder_n must be >= 1")
    if aedt_builder_n < 1:
        raise ValueError("config.aedt_builder_n must be >= 1")
    return {
        "source_toml_path": _require_non_empty_str(raw_config["source_toml_path"], context="config.source_toml_path"),
        "seed_first": seed_first,
        "seed_n": seed_n,
        "sampler_n": sampler_n,
        "step_builder_n": step_builder_n,
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
    config = _load_type2_sample_manifest_config(raw_payload["config"], manifest_path=manifest_path)
    entries = _load_type2_sample_manifest_entries(raw_payload["entries"])
    return {
        "config": config,
        "entries": entries,
    }


def _require_non_empty_str(value: object, *, context: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{context} must be str")
    if value == "":
        raise ValueError(f"{context} must be non-empty")
    return value


def load_type2_sample_metadata(sampled_toml_path: Path) -> Type2SampleMetadata:
    raw_spec, _raw_bytes = load_toml_bytes(sampled_toml_path)
    if _SAMPLED_METADATA_TABLE not in raw_spec:
        raise ValueError(f"type2 sampled TOML is missing required [{_SAMPLED_METADATA_TABLE}] metadata: {sampled_toml_path}")
    raw_metadata = raw_spec[_SAMPLED_METADATA_TABLE]
    if not isinstance(raw_metadata, dict):
        raise TypeError(f"{sampled_toml_path}:{_SAMPLED_METADATA_TABLE} must be a table/object")
    required_fields = ("source_toml_path", "seed", "design_id", "sampled_owner_paths")
    for field_name in required_fields:
        if field_name not in raw_metadata:
            raise ValueError(f"{sampled_toml_path}:{_SAMPLED_METADATA_TABLE} is missing required key {field_name!r}")
    raw_seed = raw_metadata["seed"]
    if isinstance(raw_seed, bool) or not isinstance(raw_seed, int):
        raise TypeError(f"{sampled_toml_path}:{_SAMPLED_METADATA_TABLE}.seed must be int")
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
        "design_id": _require_non_empty_str(
            raw_metadata["design_id"], context=f"{sampled_toml_path}:{_SAMPLED_METADATA_TABLE}.design_id"
        ),
        "sampled_owner_paths": sampled_owner_paths,
    }


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
    if field_name in _INTEGER_RANGE_FIELD_NAMES:
        return str(int(value))
    if field_name.endswith("_ratio") or field_name.endswith("_factor") or "_over_" in field_name:
        return str(float(value))
    if field_name.endswith("_mm"):
        return f"{float(value)}mm"
    raise ValueError(f"Unsupported type2 design variable unit contract for sampled owner: {owner_path}")


def _manifest_entry_from_sampled_toml(metadata: Type2SampleMetadata, sampled_toml_path: Path) -> Type2SampleManifestEntry:
    design_dir = sampled_toml_path.parent.resolve(strict=False)
    design_id = metadata["design_id"]
    return {
        "design_id": design_id,
        "seed": metadata["seed"],
        "source_toml_path": metadata["source_toml_path"],
        "sampled_toml_path": str(sampled_toml_path.resolve(strict=False)),
        "design_dir": str(design_dir),
        "scene_step_path": str(_scene_step_path(design_dir)),
        "step_ledger_path": str(_step_ledger_path(design_dir)),
        "imported_ledger_path": str(_imported_ledger_path(design_dir)),
        "aedt_path": str(_aedt_path(design_dir, design_id=design_id)),
        "sampled_owner_paths": list(metadata["sampled_owner_paths"]),
    }


def prepare_type2_build(sampled_toml_path: Path) -> PreparedType2Build:
    metadata = load_type2_sample_metadata(sampled_toml_path)
    sampled_spec = load_type2_step_spec(sampled_toml_path)
    source_toml_path = Path(metadata["source_toml_path"]).resolve(strict=False)
    if not source_toml_path.is_file():
        raise FileNotFoundError(f"type2 sampled TOML references missing source_toml_path: {source_toml_path}")
    source_spec = load_type2_step_spec(source_toml_path)
    expected_sampled_owner_paths = exportable_sampled_owner_paths(source_spec)
    if tuple(metadata["sampled_owner_paths"]) != expected_sampled_owner_paths:
        raise ValueError(
            "type2 sampled TOML metadata must exactly match source exportable sampled owners "
            f"(expected={expected_sampled_owner_paths}, actual={tuple(metadata['sampled_owner_paths'])})"
        )
    for owner_path, range_spec in _modeled_range_owner_specs(sampled_spec):
        if range_spec.count != 1:
            raise ValueError(f"type2 build input TOML must freeze all modeled range owners to count=1: {owner_path}")
        if range_spec.start != range_spec.end:
            raise ValueError(f"type2 build input TOML must freeze modeled range owners with identical bounds: {owner_path}")
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
        design_variables=design_variables,
    )


def prepared_builds_from_manifest(
    manifest_path: Path,
    *,
    selected_design_ids: tuple[str, ...],
) -> tuple[PreparedType2Build, ...]:
    document = load_type2_sample_manifest(manifest_path)
    entries = document["entries"]
    requested_design_ids = set(selected_design_ids)
    prepared_builds: list[PreparedType2Build] = []
    selected_found: set[str] = set()
    for entry in entries:
        design_id = entry["design_id"]
        if requested_design_ids and design_id not in requested_design_ids:
            continue
        selected_found.add(design_id)
        prepared_builds.append(prepare_type2_build(Path(entry["sampled_toml_path"])))
    missing_design_ids = requested_design_ids - selected_found
    if missing_design_ids:
        raise ValueError(f"type2 sample manifest is missing requested design ids: {sorted(missing_design_ids)}")
    return tuple(prepared_builds)


__all__ = [
    "DesignVariableEntry",
    "PreparedType2Build",
    "Type2SampleManifestConfig",
    "Type2SampleManifestDocument",
    "Type2SampleManifestEntry",
    "Type2SampleMetadata",
    "build_type2_sample_manifest_config",
    "build_type2_sample_manifest_document",
    "build_sample_manifest_entry",
    "build_type2_design_id",
    "exportable_sampled_owner_paths",
    "generate_sample_manifest_entries",
    "load_type2_sample_manifest",
    "load_type2_sample_metadata",
    "prepare_type2_build",
    "prepared_builds_from_manifest",
    "sampled_owner_values",
    "write_type2_sample_manifest",
]

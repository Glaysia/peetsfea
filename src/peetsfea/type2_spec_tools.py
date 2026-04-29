from __future__ import annotations

import copy
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from peetsfea.spec.loader import TOMLTable, TOMLValue, load_toml_bytes
from peetsfea.spec.toml_render import toml_dumps
from peetsfea.type2_sampled_sampling import _parse_constraints
from peetsfea.type2_sampled_sampling import _range_spec_for_owner_path
from peetsfea.type2_sampled_sampling import _require_constraints_satisfied
from peetsfea.type2_sampled_sampling import exportable_sampled_owner_paths
from peetsfea.type2_step_spec import Type2ConstraintRule
from peetsfea.type2_step_spec import Type2StepSpec
from peetsfea.type2_step_spec import load_type2_step_spec

SampledScalar = int | float
_SAMPLED_METADATA_TABLE = "sampled"


def validate_type2_toml(path: Path) -> Type2StepSpec:
    return load_type2_step_spec(path)


def extract_type2_constraints(path: Path) -> tuple[Type2ConstraintRule, ...]:
    return validate_type2_toml(path).constraints


def type2_sampled_owner_paths(path: Path) -> tuple[str, ...]:
    return exportable_sampled_owner_paths(validate_type2_toml(path))


def type2_sampled_toml_from_values(
    source_toml_path: Path,
    owner_values: Mapping[str, SampledScalar],
    *,
    seed: int,
    sample_index: int,
    retry_number: int = 0,
    head_hash4: str = "0000",
) -> str:
    _require_int(seed, context="seed")
    _require_int(sample_index, context="sample_index")
    _require_int(retry_number, context="retry_number")
    _require_head_hash4(head_hash4)
    source_spec = load_type2_step_spec(source_toml_path)
    raw_source_spec, _raw_source_bytes = load_toml_bytes(source_toml_path)
    _require_not_sampled_source(raw_source_spec, context=str(source_toml_path))
    expected_owner_paths = exportable_sampled_owner_paths(source_spec)
    _require_exact_owner_values(owner_values, expected_owner_paths)
    sampled_values = _sampled_values_in_owner_order(
        source_spec=source_spec,
        owner_values=owner_values,
        expected_owner_paths=expected_owner_paths,
    )
    constraints = _parse_constraints(raw_source_spec, source_spec)
    _require_constraints_satisfied(source_spec, dict(sampled_values), constraints)
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
    _validate_rendered_sampled_toml(sampled_toml_text)
    return sampled_toml_text


def _require_int(value: int, *, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{context} must be int")
    return value


def _require_head_hash4(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("head_hash4 must be str")
    if len(value) != 4:
        raise ValueError("head_hash4 must contain exactly four characters")
    if value == "":
        raise ValueError("head_hash4 must be non-empty")
    return value


def _require_not_sampled_source(raw_spec: TOMLTable, *, context: str) -> None:
    if _SAMPLED_METADATA_TABLE in raw_spec:
        raise ValueError(f"{context} must be a source type2 TOML without [{_SAMPLED_METADATA_TABLE}] metadata")


def _require_exact_owner_values(
    owner_values: Mapping[str, SampledScalar],
    expected_owner_paths: tuple[str, ...],
) -> None:
    actual_paths = set(owner_values.keys())
    expected_paths = set(expected_owner_paths)
    if actual_paths != expected_paths:
        missing = tuple(sorted(expected_paths - actual_paths))
        extra = tuple(sorted(actual_paths - expected_paths))
        raise ValueError(f"type2 sampled values must exactly match owner paths (missing={missing}, extra={extra})")


def _sampled_values_in_owner_order(
    *,
    source_spec: Type2StepSpec,
    owner_values: Mapping[str, SampledScalar],
    expected_owner_paths: tuple[str, ...],
) -> tuple[tuple[str, SampledScalar], ...]:
    sampled_values: list[tuple[str, SampledScalar]] = []
    for owner_path in expected_owner_paths:
        value = owner_values[owner_path]
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise TypeError(f"{owner_path} sampled value must be int or float")
        range_spec = _range_spec_for_owner_path(source_spec, owner_path)
        if range_spec.is_integer and not isinstance(value, int):
            raise TypeError(f"{owner_path} sampled value must be int")
        sampled_values.append((owner_path, value))
    return tuple(sampled_values)


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
    source_spec: Type2StepSpec,
) -> None:
    range_spec = _range_spec_for_owner_path(source_spec, owner_path)
    owner_parts = owner_path.split(".")
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
    sampled_owner_paths = tuple(owner_path for owner_path, _value in sampled_values)
    for owner_path, value in sampled_values:
        _freeze_owner_range_in_raw_spec(sampled_spec, owner_path=owner_path, value=value, source_spec=source_spec)
    sampled_spec[_SAMPLED_METADATA_TABLE] = cast(
        TOMLValue,
        {
            "source_toml_path": str(source_toml_path.resolve(strict=False)),
            "seed": seed,
            "sample_index": sample_index,
            "head_hash4": head_hash4,
            "retry_number": retry_number,
            "sampled_owner_paths": list(sampled_owner_paths),
        },
    )
    return sampled_spec


def _validate_rendered_sampled_toml(sampled_toml_text: str) -> None:
    with tempfile.TemporaryDirectory(prefix="peetsfea_type2_spec_tools_") as temp_dir:
        temp_path = Path(temp_dir) / "sampled.toml"
        temp_path.write_text(sampled_toml_text, encoding="utf-8")
        load_type2_step_spec(temp_path)


__all__ = [
    "extract_type2_constraints",
    "type2_sampled_owner_paths",
    "type2_sampled_toml_from_values",
    "validate_type2_toml",
]

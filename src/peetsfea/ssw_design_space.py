from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
import tomllib

SPEC_VERSION = "0.3.0"
SCHEMA_ID = "peetsfea.ssw_coil.step.v1"
DEFAULT_REFERENCE_TOML_PATH = Path(__file__).resolve().parents[2] / "examples" / "0.3.0_sweep.toml"

RangeValue = int | float
TomlRoot = dict[str, object]


@dataclass(frozen=True)
class SswDesignSpaceViolation:
    path: str
    code: str
    message: str


@dataclass(frozen=True)
class SswDesignSpaceCheckResult:
    is_subset: bool
    is_point: bool
    dimension_count: int
    free_owner_paths: tuple[str, ...]
    violations: tuple[SswDesignSpaceViolation, ...]


@dataclass(frozen=True)
class SswAedtIdentity:
    design_id: str
    aedt_filename: str
    point_hash: str
    dimension_count: int
    free_owner_paths: tuple[str, ...]


@dataclass(frozen=True)
class _RangeDefinition:
    path: str
    is_integer: bool
    lower: float
    upper: float
    count: int


def _require_table(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be a table")
    return value


def _require_key(table: dict[str, object], key: str, context: str) -> object:
    if key not in table:
        raise ValueError(f"{context} is missing required key {key!r}")
    return table[key]


def _require_non_empty_str(table: dict[str, object], key: str, context: str) -> str:
    raw_value = _require_key(table, key, context)
    if not isinstance(raw_value, str) or raw_value == "":
        raise TypeError(f"{context}.{key} must be a non-empty str")
    return raw_value


def _range_number(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{context} must be numeric")
    return float(value)


def _range_count(value: object, context: str) -> int:
    count_float = _range_number(value, context)
    count = int(count_float)
    if float(count) != count_float:
        raise ValueError(f"{context} must be an integer count")
    return count


def _range_definition(table: dict[str, object], path: str) -> _RangeDefinition:
    raw_range = _require_key(table, "range", path)
    if isinstance(raw_range, (str, bytes)) or not isinstance(raw_range, list):
        raise TypeError(f"{path}.range must be a list")
    if len(raw_range) != 4:
        raise ValueError(f"{path}.range must contain exactly four entries")
    raw_integer = raw_range[0]
    if not isinstance(raw_integer, bool):
        raise TypeError(f"{path}.range[0] must be bool")
    lower = _range_number(raw_range[1], f"{path}.range[1]")
    upper = _range_number(raw_range[2], f"{path}.range[2]")
    count = _range_count(raw_range[3], f"{path}.range[3]")
    if lower > upper:
        raise ValueError(f"{path}.range lower must be <= upper")
    return _RangeDefinition(path=path, is_integer=raw_integer, lower=lower, upper=upper, count=count)


def _load_toml_root(toml_path: Path) -> TomlRoot:
    raw_root = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    root = _require_table(raw_root, str(toml_path))
    spec_version = _require_non_empty_str(root, "spec_version", str(toml_path))
    if spec_version != SPEC_VERSION:
        raise ValueError(f"{toml_path} spec_version must be {SPEC_VERSION!r} (actual={spec_version!r})")
    schema_id = _require_non_empty_str(root, "schema_id", str(toml_path))
    if schema_id != SCHEMA_ID:
        raise ValueError(f"{toml_path} schema_id must be {SCHEMA_ID!r} (actual={schema_id!r})")
    return root


def _record_range(ranges: dict[str, _RangeDefinition], table: dict[str, object], path: str) -> None:
    if path in ranges:
        raise ValueError(f"duplicate SSW design-space range path {path!r}")
    ranges[path] = _range_definition(table, path)


def _collect_section_ranges(
    *,
    root: TomlRoot,
    section_name: Literal["fixed_dimensions", "ferrite"],
    ranges: dict[str, _RangeDefinition],
) -> None:
    if section_name not in root:
        return
    section = _require_table(root[section_name], section_name)
    for key, raw_child in section.items():
        if not isinstance(raw_child, dict):
            continue
        child = _require_table(raw_child, f"{section_name}.{key}")
        if "range" in child:
            _record_range(ranges, child, f"{section_name}.{key}")


def _collect_modeled_object_ranges(*, root: TomlRoot, ranges: dict[str, _RangeDefinition]) -> None:
    if "modeled_objects" not in root:
        return
    raw_objects = root["modeled_objects"]
    if isinstance(raw_objects, (str, bytes)) or not isinstance(raw_objects, list):
        raise TypeError("modeled_objects must be an array of tables")
    seen_roles: set[str] = set()
    for index, raw_object in enumerate(raw_objects):
        context = f"modeled_objects[{index}]"
        table = _require_table(raw_object, context)
        role = _require_non_empty_str(table, "role", context)
        if role in seen_roles:
            raise ValueError(f"modeled_objects role must be unique (duplicate={role!r})")
        seen_roles.add(role)
        for key, raw_child in table.items():
            if key in {"object_id", "role", "material", "model_state"}:
                continue
            if not isinstance(raw_child, dict):
                continue
            child = _require_table(raw_child, f"{context}.{key}")
            if "range" in child:
                _record_range(ranges, child, f"modeled_objects[role={role}].{key}")


def _range_definitions(root: TomlRoot) -> dict[str, _RangeDefinition]:
    ranges: dict[str, _RangeDefinition] = {}
    _collect_section_ranges(root=root, section_name="fixed_dimensions", ranges=ranges)
    _collect_section_ranges(root=root, section_name="ferrite", ranges=ranges)
    _collect_modeled_object_ranges(root=root, ranges=ranges)
    return ranges


def _reference_free_ranges(reference_toml_path: Path) -> dict[str, _RangeDefinition]:
    reference_ranges = _range_definitions(_load_toml_root(reference_toml_path))
    free_ranges: dict[str, _RangeDefinition] = {}
    for path, range_def in reference_ranges.items():
        if range_def.count != 1:
            if range_def.count <= 0:
                raise ValueError(f"reference free range count must be positive (path={path}, count={range_def.count})")
            free_ranges[path] = range_def
    return free_ranges


def _violation(path: str, code: str, message: str) -> SswDesignSpaceViolation:
    return SswDesignSpaceViolation(path=path, code=code, message=message)


def _integer_value_violations(*, candidate: _RangeDefinition) -> tuple[SswDesignSpaceViolation, ...]:
    if not candidate.is_integer:
        return ()
    violations: list[SswDesignSpaceViolation] = []
    if float(int(candidate.lower)) != candidate.lower:
        violations.append(
            _violation(candidate.path, "integer_lower_not_integral", "candidate integer lower bound must be integral")
        )
    if float(int(candidate.upper)) != candidate.upper:
        violations.append(
            _violation(candidate.path, "integer_upper_not_integral", "candidate integer upper bound must be integral")
        )
    return tuple(violations)


def _range_violations(*, reference: _RangeDefinition, candidate: _RangeDefinition) -> tuple[SswDesignSpaceViolation, ...]:
    violations: list[SswDesignSpaceViolation] = []
    if candidate.is_integer != reference.is_integer:
        violations.append(
            _violation(
                candidate.path,
                "integer_flag_mismatch",
                "candidate integer flag must match the reference free range",
            )
        )
    if candidate.count <= 0:
        violations.append(_violation(candidate.path, "non_positive_count", "candidate count must be positive"))
    if candidate.lower < reference.lower:
        violations.append(
            _violation(candidate.path, "lower_bound_outside_reference", "candidate lower bound is below reference")
        )
    if candidate.upper > reference.upper:
        violations.append(
            _violation(candidate.path, "upper_bound_outside_reference", "candidate upper bound is above reference")
        )
    violations.extend(_integer_value_violations(candidate=candidate))
    return tuple(violations)


def _is_point(candidate_ranges: dict[str, _RangeDefinition], free_owner_paths: tuple[str, ...]) -> bool:
    for path in free_owner_paths:
        candidate = candidate_ranges[path]
        if candidate.lower != candidate.upper:
            return False
    return True


def check_ssw_toml_in_design_space(
    candidate_toml_path: Path,
    reference_toml_path: Path = DEFAULT_REFERENCE_TOML_PATH,
) -> SswDesignSpaceCheckResult:
    free_ranges = _reference_free_ranges(reference_toml_path)
    free_owner_paths = tuple(sorted(free_ranges))
    candidate_ranges = _range_definitions(_load_toml_root(candidate_toml_path))
    violations: list[SswDesignSpaceViolation] = []
    for path in free_owner_paths:
        reference = free_ranges[path]
        if path not in candidate_ranges:
            violations.append(_violation(path, "missing_free_path", "candidate is missing reference free range path"))
            continue
        candidate = candidate_ranges[path]
        violations.extend(_range_violations(reference=reference, candidate=candidate))
    is_subset = len(violations) == 0
    is_point = is_subset and _is_point(candidate_ranges, free_owner_paths)
    return SswDesignSpaceCheckResult(
        is_subset=is_subset,
        is_point=is_point,
        dimension_count=len(free_owner_paths),
        free_owner_paths=free_owner_paths,
        violations=tuple(violations),
    )


def _point_value(range_def: _RangeDefinition) -> RangeValue:
    if range_def.lower != range_def.upper:
        raise ValueError(f"{range_def.path} is not a realized point range")
    if range_def.is_integer:
        return int(range_def.lower)
    return float(range_def.lower)


def _identity_payload(
    *,
    candidate_ranges: dict[str, _RangeDefinition],
    free_owner_paths: tuple[str, ...],
) -> dict[str, object]:
    point_values: dict[str, RangeValue] = {}
    for path in free_owner_paths:
        point_values[path] = _point_value(candidate_ranges[path])
    return {
        "free_owner_paths": list(free_owner_paths),
        "point_values": point_values,
    }


def _point_hash(payload: dict[str, object]) -> str:
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.blake2b(payload_bytes, digest_size=8).hexdigest()


def _raise_for_check_failure(result: SswDesignSpaceCheckResult) -> None:
    if result.is_subset:
        return
    details = "; ".join(f"{violation.path}:{violation.code}" for violation in result.violations)
    raise ValueError(f"SSW candidate TOML is outside the reference design space ({details})")


def _raise_for_non_point(candidate_ranges: dict[str, _RangeDefinition], free_owner_paths: tuple[str, ...]) -> None:
    non_point_paths: list[str] = []
    for path in free_owner_paths:
        candidate = candidate_ranges[path]
        if candidate.lower != candidate.upper:
            non_point_paths.append(path)
    if len(non_point_paths) != 0:
        raise ValueError(
            "SSW AEDT identity requires a single realized point; non-point free paths: "
            + ", ".join(non_point_paths)
        )


def build_ssw_aedt_identity(
    candidate_toml_path: Path,
    reference_toml_path: Path = DEFAULT_REFERENCE_TOML_PATH,
) -> SswAedtIdentity:
    result = check_ssw_toml_in_design_space(candidate_toml_path, reference_toml_path)
    _raise_for_check_failure(result)
    candidate_ranges = _range_definitions(_load_toml_root(candidate_toml_path))
    _raise_for_non_point(candidate_ranges, result.free_owner_paths)
    payload = _identity_payload(candidate_ranges=candidate_ranges, free_owner_paths=result.free_owner_paths)
    point_hash = _point_hash(payload)
    design_id = f"0_3_0_p{point_hash}"
    return SswAedtIdentity(
        design_id=design_id,
        aedt_filename=f"{design_id}.aedt",
        point_hash=point_hash,
        dimension_count=result.dimension_count,
        free_owner_paths=result.free_owner_paths,
    )


__all__ = [
    "DEFAULT_REFERENCE_TOML_PATH",
    "SswAedtIdentity",
    "SswDesignSpaceCheckResult",
    "SswDesignSpaceViolation",
    "build_ssw_aedt_identity",
    "check_ssw_toml_in_design_space",
]

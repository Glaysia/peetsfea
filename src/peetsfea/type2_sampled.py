from __future__ import annotations

import copy
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypedDict, cast

from peetsfea.spec.loader import TOMLTable, TOMLValue, load_toml_bytes
from peetsfea.spec.toml_render import toml_dumps
from peetsfea.type2_step_export import export_type2_step_artifacts
from peetsfea.type2_step_spec import ModeledPlateStackSpec
from peetsfea.type2_step_spec import ModeledRxSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec import NonModelDerivedSpec
from peetsfea.type2_step_spec import NonModelTxRegionActualSpec
from peetsfea.type2_step_spec import NonModelTxRegionActualStackSpaceSpec
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import Type2StepSpec
from peetsfea.type2_step_spec import load_type2_step_spec

REPO_ROOT = Path(__file__).resolve().parents[2]
SampledScalar = int | float
DesignVariableEntry = tuple[str, str]
_SampleExporter = Callable[..., object]
_INTEGER_RANGE_FIELD_NAMES = (
    "turn_count",
    "layer_count",
    "underlay_repeat_count",
    "wall_parallel_stack_present",
    "tx_coil_count",
    "x_division_count",
    "y_division_count",
)
_SAMPLED_METADATA_TABLE = "sampled"
_SAMPLED_SINGLE_COIL_ROLES: frozenset[str] = frozenset({"tx_single_coil", "rx_single_coil"})
_PLATE_STACK_ROLE_SUFFIX = "_plate_stack"
_TYPE2_CONSTRAINT_RETRY_LIMIT: Final[int] = 64
_CONSTRAINT_COMPARISON_OPERATORS: Final[frozenset[str]] = frozenset({"<", "<=", ">", ">=", "==", "!="})


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


def _modeled_spec_role(modeled_spec: object) -> str:
    assert hasattr(modeled_spec, "role"), "type2 modeled spec must expose role"
    raw_role = getattr(modeled_spec, "role")
    assert isinstance(raw_role, str), "type2 modeled spec role must be str"
    return raw_role


def _modeled_roles(spec: Type2StepSpec) -> tuple[str, ...]:
    return tuple(_modeled_spec_role(modeled_spec) for modeled_spec in spec.modeled_objects)


def _non_model_range_owner_specs(spec: Type2StepSpec) -> tuple[tuple[str, RangeSpec], ...]:
    owner_specs: list[tuple[str, RangeSpec]] = []
    for non_model_spec in spec.non_model_derived_objects:
        owner_specs.extend(_derived_non_model_range_owner_specs(non_model_spec))
    return tuple(owner_specs)


def _parse_constraint_table(raw_value: object, path: str) -> TOMLTable:
    if not isinstance(raw_value, dict):
        raise ValueError(f"{path} must be a table/object")
    return cast(TOMLTable, raw_value)


def _constraint_id_for_rule(index: int) -> str:
    return f"constraints.rules[{index}]"


def _parse_constraint_func(raw_text: str, context: str) -> tuple[str, tuple[str, ...]]:
    text = raw_text.strip()
    if not text.startswith("sum(") or not text.endswith(")"):
        raise ValueError(f"{context}.func must be in the form sum(arg_1, arg_2, ...)")
    body = text[4:-1].strip()
    args = _split_function_args(body, context=f"{context}.func")
    if len(args) == 0:
        raise ValueError(f"{context}.func sum() must contain at least one argument")
    return "sum", tuple(args)


def _split_function_args(raw_text: str, context: str) -> tuple[str, ...]:
    if raw_text == "":
        return tuple()
    args: list[str] = []
    token: list[str] = []
    depth = 0
    for index, ch in enumerate(raw_text):
        if ch == "(":
            depth += 1
            token.append(ch)
            continue
        if ch == ")":
            depth -= 1
            if depth < 0:
                raise ValueError(f"{context} has unmatched ')' at index {index}")
            token.append(ch)
            continue
        if ch == "," and depth == 0:
            raw_arg = "".join(token).strip()
            if raw_arg == "":
                raise ValueError(f"{context} contains empty argument")
            args.append(raw_arg)
            token = []
            continue
        token.append(ch)
    if depth != 0:
        raise ValueError(f"{context} has unmatched '('")
    if token:
        raw_arg = "".join(token).strip()
        if raw_arg == "":
            raise ValueError(f"{context} contains empty argument")
        args.append(raw_arg)
    return tuple(args)


def _parse_constraint_operand(
    raw_operand: object,
    path: str,
) -> _ConstraintPathRef | _ConstraintFuncRef | _ConstraintValueRef:
    if isinstance(raw_operand, dict):
        if set(raw_operand.keys()) == {"path"}:
            raw_path = raw_operand["path"]
            if not isinstance(raw_path, str) or raw_path == "":
                raise ValueError(f"{path} path must be a non-empty string")
            return {"path": raw_path}
        if set(raw_operand.keys()) == {"func"}:
            raw_func = raw_operand["func"]
            if not isinstance(raw_func, str) or raw_func == "":
                raise ValueError(f"{path}.func must be a non-empty string")
            return {"func": raw_func.strip()}
        if set(raw_operand.keys()) == {"value"}:
            raw_value = raw_operand["value"]
            if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                raise ValueError(f"{path}.value must be a number")
            return {"value": raw_value}
    raise ValueError(f"{path} must be one of {{path|value|func}}")


def _parse_constraints(source_spec: TOMLTable, source: Type2StepSpec) -> list[_Type2ConstraintRule]:
    if "constraints" not in source_spec:
        return []
    raw_constraints = source_spec["constraints"]
    if not isinstance(raw_constraints, dict):
        raise ValueError("[constraints] must be a table/object")
    raw_rules = cast(object, raw_constraints)
    if "rules" not in cast(TOMLTable, raw_rules):
        raise ValueError("[constraints] must contain rules")
    constraints_table = _parse_constraint_table(raw_rules, "constraints")
    raw_rule_list = constraints_table["rules"]
    if not isinstance(raw_rule_list, list):
        raise ValueError("constraints.rules must be a list of tables")
    if len(raw_rule_list) == 0:
        raise ValueError("constraints.rules must be a non-empty list")
    parsed_rules: list[_Type2ConstraintRule] = []
    rule_ids: set[str] = set()
    for index, raw_rule in enumerate(raw_rule_list):
        rule_path = _constraint_id_for_rule(index)
        if not isinstance(raw_rule, dict):
            raise ValueError(f"{rule_path} must be a table/object")
        raw_rule_dict = cast(TOMLTable, raw_rule)
        if set(raw_rule_dict.keys()) != {"id", "kind", "message", "enabled", "lhs", "op", "rhs"} and not {
            "id",
            "kind",
            "message",
            "lhs",
            "op",
            "rhs",
        }.issubset(set(raw_rule_dict.keys())):
            raise ValueError(f"{rule_path} must contain keys id, kind, message, lhs, op, rhs and optional enabled")
        raw_id = raw_rule_dict["id"]
        if not isinstance(raw_id, str) or raw_id == "":
            raise ValueError(f"{rule_path}.id must be a non-empty string")
        if raw_id in rule_ids:
            raise ValueError(f"{rule_path} duplicate rule id: {raw_id}")
        rule_ids.add(raw_id)
        raw_kind = raw_rule_dict["kind"]
        if raw_kind != "comparison":
            raise ValueError(f"{rule_path}.kind must be 'comparison' for type2 constraints")
        raw_message = raw_rule_dict["message"]
        if not isinstance(raw_message, str) or raw_message == "":
            raise ValueError(f"{rule_path}.message must be a non-empty string")
        raw_enabled = raw_rule_dict["enabled"] if "enabled" in raw_rule_dict else True
        if raw_enabled is not True and raw_enabled is not False:
            raise ValueError(f"{rule_path}.enabled must be bool")
        raw_lhs = _parse_constraint_operand(raw_rule_dict["lhs"], f"{rule_path}.lhs")
        raw_rhs = _parse_constraint_operand(raw_rule_dict["rhs"], f"{rule_path}.rhs")
        raw_op = raw_rule_dict["op"]
        if raw_op not in _CONSTRAINT_COMPARISON_OPERATORS:
            raise ValueError(
                f"{rule_path}.op must be one of {sorted(_CONSTRAINT_COMPARISON_OPERATORS)} "
                f"(actual={raw_op!r})"
            )
        parsed_rules.append(
            {
                "id": raw_id,
                "kind": "comparison",
                "message": raw_message,
                "enabled": bool(raw_enabled),
                "lhs": raw_lhs,
                "op": raw_op,
                "rhs": raw_rhs,
            }
        )
    _validate_constraint_paths(sampled_source=source, constraints=parsed_rules)
    return parsed_rules


def _validate_constraint_path(sampled_source: Type2StepSpec, path: str, *, context: str) -> None:
    try:
        _ = _range_spec_for_owner_path(sampled_source, path)
    except ValueError as exc:
        raise ValueError(f"{context} references unknown owner path: {path}") from exc


def _validate_constraint_paths(sampled_source: Type2StepSpec, *, constraints: list[_Type2ConstraintRule]) -> None:
    for rule in constraints:
        if not rule["enabled"]:
            continue
        for side_key in ("lhs", "rhs"):
            raw_side = rule[side_key]
            if "path" in raw_side:
                _validate_constraint_path(sampled_source, raw_side["path"], context=f"constraints.rules[{rule['id']}]")
            if "func" in raw_side:
                func_name, args = _parse_constraint_func(raw_side["func"], f"constraints.rules[{rule['id']}]")
                if func_name != "sum":
                    raise ValueError(f"constraints.rules[{rule['id']}].func only supports sum()")
                for arg in args:
                    _validate_constraint_sum_arg(sampled_source, arg, context=f"constraints.rules[{rule['id']}]")


def _validate_constraint_sum_arg(sampled_source: Type2StepSpec, arg: str, *, context: str) -> None:
    if arg == "":
        raise ValueError(f"{context}.func contains empty argument")
    try:
        float(arg)
    except ValueError:
        _validate_constraint_path(sampled_source, arg, context=f"{context}.func")


def _resolve_constraint_path_value(
    source: Type2StepSpec,
    sampled_values: dict[str, SampledScalar],
    path: str,
    *,
    context: str,
) -> SampledScalar:
    if path in sampled_values:
        return sampled_values[path]
    range_spec = _range_spec_for_owner_path(source, path)
    if range_spec.count != 1:
        raise ValueError(f"{context} references unsampled owner path: {path}")
    if range_spec.is_integer:
        value = int(range_spec.start)
    else:
        value = float(range_spec.start)
    return value


def _resolve_constraint_operand(
    source: Type2StepSpec,
    sampled_values: dict[str, SampledScalar],
    operand: _ConstraintPathRef | _ConstraintFuncRef | _ConstraintValueRef,
    *,
    context: str,
) -> int | float | str:
    if "path" in operand:
        return _resolve_constraint_path_value(
            source,
            sampled_values,
            operand["path"],
            context=context,
        )
    if "value" in operand:
        return operand["value"]
    function = _parse_constraint_func(cast(str, operand["func"]), context=f"{context}.func")
    function_name, args = function
    if function_name != "sum":
        raise ValueError(f"{context}.func only supports sum()")
    total = 0.0
    for arg in args:
        if " " in arg:
            arg = arg.strip()
        try:
            total += float(arg)
            continue
        except ValueError:
            pass
        total += float(_resolve_constraint_path_value(source, sampled_values, arg, context=context))
    return total


def _evaluate_comparison(lhs: int | float | str, op: str, rhs: int | float | str) -> bool:
    if op in {"<", "<=", ">", ">=", "!="}:
        if isinstance(lhs, str) or isinstance(rhs, str):
            raise ValueError(f"comparison operator {op} is not supported for string operands")
    if op == "<":
        return lhs < rhs  # type: ignore[operator]
    if op == "<=":
        return lhs <= rhs  # type: ignore[operator]
    if op == ">":
        return lhs > rhs  # type: ignore[operator]
    if op == ">=":
        return lhs >= rhs  # type: ignore[operator]
    if op == "==":
        return lhs == rhs
    if op == "!=":
        return lhs != rhs
    raise ValueError(f"Unsupported comparison operator: {op}")


def _require_constraints_satisfied(
    source: Type2StepSpec,
    sampled_values: dict[str, SampledScalar],
    constraints: list[_Type2ConstraintRule],
) -> None:
    for rule in constraints:
        if not rule["enabled"]:
            continue
        lhs_value = _resolve_constraint_operand(
            source,
            sampled_values,
            cast(_ConstraintPathRef | _ConstraintFuncRef | _ConstraintValueRef, rule["lhs"]),
            context=f"constraints.rules[{rule['id']}]",
        )
        rhs_value = _resolve_constraint_operand(
            source,
            sampled_values,
            cast(_ConstraintPathRef | _ConstraintFuncRef | _ConstraintValueRef, rule["rhs"]),
            context=f"constraints.rules[{rule['id']}]",
        )
        if not _evaluate_comparison(lhs_value, rule["op"], rhs_value):
            raise ValueError(
                f"constraint '{rule['id']}' failed: {rule['message']} "
                f"(lhs={lhs_value!r} rhs={rhs_value!r} op={rule['op']})"
            )


def _derived_non_model_range_owner_specs(
    non_model_spec: NonModelDerivedSpec,
) -> tuple[tuple[str, RangeSpec], ...]:
    if isinstance(non_model_spec, NonModelTxRegionActualSpec):
        return _tx_region_actual_range_owner_specs(non_model_spec)
    if isinstance(non_model_spec, NonModelTxRegionActualStackSpaceSpec):
        return _tx_region_actual_stack_space_range_owner_specs(non_model_spec)
    raise RuntimeError(f"unsupported non-model derived spec: {type(non_model_spec).__name__}")


def _tx_region_actual_range_owner_specs(
    non_model_spec: NonModelTxRegionActualSpec,
) -> tuple[tuple[str, RangeSpec], ...]:
    return (
        (f"non_model_objects.{non_model_spec.object_id}.x_usage_ratio", non_model_spec.x_usage_ratio),
        (f"non_model_objects.{non_model_spec.object_id}.y_usage_ratio", non_model_spec.y_usage_ratio),
        (
            f"non_model_objects.{non_model_spec.object_id}.x_division_count",
            non_model_spec.x_division_count,
        ),
        (
            f"non_model_objects.{non_model_spec.object_id}.y_division_count",
            non_model_spec.y_division_count,
        ),
    )


def _tx_region_actual_stack_space_range_owner_specs(
    non_model_spec: NonModelTxRegionActualStackSpaceSpec,
) -> tuple[tuple[str, RangeSpec], ...]:
    return (
        (f"non_model_objects.{non_model_spec.object_id}.scale_ratio", non_model_spec.scale_ratio),
    )


def _modeled_range_owner_specs(spec: Type2StepSpec) -> tuple[tuple[str, RangeSpec], ...]:
    owner_specs: list[tuple[str, RangeSpec]] = []
    for modeled_spec in spec.modeled_objects:
        role = _modeled_spec_role(modeled_spec)
        if role in _SAMPLED_SINGLE_COIL_ROLES:
            owner_specs.extend(
                _single_coil_range_owner_specs(cast(ModeledTxSingleCoilSpec | ModeledRxSingleCoilSpec, modeled_spec))
            )
            continue
        if role.endswith(_PLATE_STACK_ROLE_SUFFIX):
            owner_specs.extend(_plate_stack_range_owner_specs(cast(ModeledPlateStackSpec, modeled_spec)))
            continue
        raise RuntimeError(f"unsupported modeled object role for sampled owner resolution: {role}")
    return tuple(owner_specs)


def _all_range_owner_specs(spec: Type2StepSpec) -> tuple[tuple[str, RangeSpec], ...]:
    return _non_model_range_owner_specs(spec) + _modeled_range_owner_specs(spec)


def _single_coil_range_owner_specs(
    modeled_spec: ModeledTxSingleCoilSpec | ModeledRxSingleCoilSpec,
) -> tuple[tuple[str, RangeSpec], ...]:
    owner_specs: list[tuple[str, RangeSpec]] = [
        (f"modeled_objects.{modeled_spec.object_id}.outer_x_usage_ratio", modeled_spec.outer_x_usage_ratio),
        (f"modeled_objects.{modeled_spec.object_id}.outer_y_usage_ratio", modeled_spec.outer_y_usage_ratio),
        (f"modeled_objects.{modeled_spec.object_id}.void_usage_ratio", modeled_spec.void_usage_ratio),
        (f"modeled_objects.{modeled_spec.object_id}.turn_count", modeled_spec.turn_count),
        (f"modeled_objects.{modeled_spec.object_id}.layer_count", modeled_spec.layer_count),
        (
            f"modeled_objects.{modeled_spec.object_id}.underlay_repeat_count",
            modeled_spec.underlay_repeat_count,
        ),
        (f"modeled_objects.{modeled_spec.object_id}.layer_gap_mm", modeled_spec.layer_gap_mm),
        (
            f"modeled_objects.{modeled_spec.object_id}.terminal_stub_length_mm",
            modeled_spec.terminal_stub_length_mm,
        ),
        (f"modeled_objects.{modeled_spec.object_id}.margin_ratio", modeled_spec.margin_ratio),
        (f"modeled_objects.{modeled_spec.object_id}.metal_fill_factor", modeled_spec.metal_fill_factor),
    ]
    if isinstance(modeled_spec, ModeledTxSingleCoilSpec):
        owner_specs.extend(
            (
                (f"modeled_objects.{modeled_spec.object_id}.underlay_gap_mm", modeled_spec.underlay_gap_mm),
                (
                    f"modeled_objects.{modeled_spec.object_id}.wall_parallel_stack_present",
                    modeled_spec.wall_parallel_stack_present,
                ),
            )
        )
    return tuple(owner_specs)


def _plate_stack_range_owner_specs(
    modeled_spec: ModeledPlateStackSpec,
) -> tuple[tuple[str, RangeSpec], ...]:
    owner_specs: list[tuple[str, RangeSpec]] = [
        (f"modeled_objects.{modeled_spec.object_id}.turn_count", modeled_spec.turn_count),
        (f"modeled_objects.{modeled_spec.object_id}.metal_fill_factor", modeled_spec.metal_fill_factor),
        (f"modeled_objects.{modeled_spec.object_id}.z_usage_ratio", modeled_spec.z_usage_ratio),
        (f"modeled_objects.{modeled_spec.object_id}.y_usage_ratio", modeled_spec.y_usage_ratio),
    ]
    if isinstance(modeled_spec, ModeledTxPlateStackSpec):
        owner_specs.extend(
            (
                (f"modeled_objects.{modeled_spec.object_id}.tx_coil_count", modeled_spec.tx_coil_count),
                (
                    f"modeled_objects.{modeled_spec.object_id}.tx_array_x_usage_ratio",
                    modeled_spec.tx_array_x_usage_ratio,
                ),
            )
        )
    return tuple(owner_specs)


def exportable_sampled_owner_paths(spec: Type2StepSpec) -> tuple[str, ...]:
    return tuple(owner_path for owner_path, range_spec in _all_range_owner_specs(spec) if range_spec.count != 1)


def exportable_sampled_owner_paths_for_seed(spec: Type2StepSpec, *, seed: int) -> tuple[str, ...]:
    return tuple(owner_path for owner_path, range_spec in _all_range_owner_specs(spec) if range_spec.count != 1)


def _range_spec_for_owner_path(spec: Type2StepSpec, owner_path: str) -> RangeSpec:
    for candidate_owner_path, range_spec in _all_range_owner_specs(spec):
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


def _selected_value_for_owner_path(
    range_spec: RangeSpec,
    *,
    owner_path: str,
    seed: int,
    retry_number: int = 0,
) -> SampledScalar:
    if retry_number < 0:
        raise ValueError("retry_number must be >= 0")
    candidates: tuple[SampledScalar, ...]
    if range_spec.is_integer:
        candidates = _integer_range_candidates(range_spec)
    else:
        candidates = _float_range_candidates(range_spec)
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated for sampled owner: {owner_path}")
    if len(candidates) == 1:
        return candidates[0]
    hash_key = f"{seed}:{owner_path}" if retry_number == 0 else f"{seed}:{owner_path}:{retry_number}"
    digest = hashlib.blake2b(hash_key.encode("utf-8"), digest_size=8).digest()
    index = int.from_bytes(digest, byteorder="big", signed=False) % len(candidates)
    return candidates[index]


def sampled_owner_values(
    spec: Type2StepSpec,
    *,
    seed: int,
    retry_number: int = 0,
) -> tuple[tuple[str, SampledScalar], ...]:
    sampled_values: list[tuple[str, SampledScalar]] = []
    for owner_path, range_spec in _all_range_owner_specs(spec):
        if range_spec.count == 1:
            continue
        sampled_values.append(
            (
                owner_path,
                _selected_value_for_owner_path(
                    range_spec,
                    owner_path=owner_path,
                    seed=seed,
                    retry_number=retry_number,
                )
            )
        )
    return tuple(sampled_values)


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
    owner_parts = owner_path.split(".")
    if len(owner_parts) != 3:
        raise ValueError(f"Unsupported type2 sampled owner path: {owner_path}")
    owner_root, object_id, field_name = owner_parts
    owner_table: TOMLTable
    if owner_root == "modeled_objects":
        owner_table = _modeled_object_table(raw_spec, object_id=object_id)
    elif owner_root == "non_model_objects":
        owner_table = _non_model_object_table(raw_spec, object_id=object_id)
    else:
        raise ValueError(f"Unsupported type2 sampled owner path: {owner_path}")
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
        candidate_values = sampled_owner_values(source_spec, seed=seed, retry_number=attempt)
        try:
            _require_constraints_satisfied(source_spec, dict(candidate_values), constraints)
        except ValueError as exc:
            last_constraint_failure = exc
            continue
        sampled_values = candidate_values
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


def _no_op_sample_step_stage_reporter(
    phase: _SampleStepStage,
    entry: Type2SampleManifestEntry,
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


def _build_sample_manifest_entry_for_seed_task(task: tuple[str, str, int, int, str, bool]) -> Type2SampleManifestEntry:
    source_toml_path_text, output_dir_text, seed, sample_index, head_hash4, make_step_on_sample = task
    source_toml_path = Path(source_toml_path_text)
    output_dir = Path(output_dir_text)
    source_spec = load_type2_step_spec(source_toml_path)
    raw_source_spec, _raw_source_bytes = load_toml_bytes(source_toml_path)
    _require_not_sampled_source(raw_source_spec, context=str(source_toml_path))
    entry = _build_sample_manifest_entry_for_seed(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        source_spec=source_spec,
        raw_source_spec=raw_source_spec,
        seed=seed,
        sample_index=sample_index,
        head_hash4=head_hash4,
    )
    if make_step_on_sample:
        _export_step_for_sample_entry(entry, exporter=export_type2_step_artifacts)
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


def generate_sample_manifest_entries(
    *,
    source_toml_path: Path,
    output_dir: Path,
    seed_start: int,
    count: int,
    jobs: int = 1,
    make_step_on_sample: bool = True,
    exporter: _SampleExporter = export_type2_step_artifacts,
    report_progress: _SampleProgressReporter | None = None,
    report_step_stage: _SampleStepStageReporter = _no_op_sample_step_stage_reporter,
) -> list[Type2SampleManifestEntry]:
    if count < 1:
        raise ValueError("count must be >= 1")
    if jobs < 1:
        raise ValueError("jobs must be >= 1")
    if not isinstance(make_step_on_sample, bool):
        raise TypeError("make_step_on_sample must be bool")
    output_dir.mkdir(parents=True, exist_ok=True)
    seed_values = tuple(range(seed_start, seed_start + count))
    head_hash4 = _current_head_hash4()
    if jobs == 1 or count == 1 or (make_step_on_sample and exporter is not export_type2_step_artifacts):
        source_spec = load_type2_step_spec(source_toml_path)
        raw_source_spec, _raw_source_bytes = load_toml_bytes(source_toml_path)
        _require_not_sampled_source(raw_source_spec, context=str(source_toml_path))
        entries: list[Type2SampleManifestEntry] = []
        for sample_index, seed in enumerate(seed_values):
            entry = _build_sample_manifest_entry_for_seed(
                source_toml_path=source_toml_path,
                output_dir=output_dir,
                source_spec=source_spec,
                raw_source_spec=raw_source_spec,
                seed=seed,
                sample_index=sample_index,
                head_hash4=head_hash4,
            )
            if make_step_on_sample:
                _export_step_for_sample_entry(
                    entry,
                    exporter=exporter,
                    report_step_stage=report_step_stage,
                )
            entries.append(entry)
            _emit_sample_progress(
                report_progress=report_progress,
                completed=sample_index + 1,
                total=count,
                entry=entry,
            )
        return entries
    tasks = [
        (str(source_toml_path), str(output_dir), seed, sample_index, head_hash4, make_step_on_sample)
        for sample_index, seed in enumerate(seed_values)
    ]
    entries_by_index: dict[int, Type2SampleManifestEntry] = {}
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        future_by_index = {executor.submit(_build_sample_manifest_entry_for_seed_task, task): task[3] for task in tasks}
        completed = 0
        for future in as_completed(future_by_index):
            entry = future.result()
            completed += 1
            entries_by_index[entry["sample_index"]] = entry
            _emit_sample_progress(
                report_progress=report_progress,
                completed=completed,
                total=count,
                entry=entry,
            )
    return [entries_by_index[sample_index] for sample_index in range(count)]


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
    if sample_index >= len(entries):
        raise IndexError(
            f"type2 sample manifest sample_index is out of range (index={sample_index}, count={len(entries)})"
        )
    entry = entries[sample_index]
    if entry["sample_index"] != sample_index:
        raise ValueError(
            "type2 sample manifest entry order must match sample_index "
            f"(index={sample_index}, entry_sample_index={entry['sample_index']})"
        )
    return entry


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
    if field_name in _INTEGER_RANGE_FIELD_NAMES or field_name.startswith("turn_count_x"):
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


def prepare_type2_build(sampled_toml_path: Path) -> PreparedType2Build:
    metadata = load_type2_sample_metadata(sampled_toml_path)
    sampled_spec = load_type2_step_spec(sampled_toml_path)
    sampled_modeled_roles = _modeled_roles(sampled_spec)
    source_toml_path = Path(metadata["source_toml_path"]).resolve(strict=False)
    if not source_toml_path.is_file():
        raise FileNotFoundError(f"type2 sampled TOML references missing source_toml_path: {source_toml_path}")
    source_spec = load_type2_step_spec(source_toml_path)
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
    "build_type2_design_id",
    "build_type2_sample_manifest_config",
    "build_type2_sample_manifest_document",
    "build_sample_manifest_entry",
    "exportable_sampled_owner_paths",
    "exportable_sampled_owner_paths_for_seed",
    "generate_sample_manifest_entries",
    "load_type2_sample_manifest",
    "load_type2_sample_metadata",
    "manifest_entry_for_sample_index",
    "prepare_type2_build",
    "prepared_builds_from_manifest",
    "sampled_owner_values",
    "write_type2_sample_manifest",
]

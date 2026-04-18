from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict, cast

from peetsfea.aedt.failfast import validate_aedt_name
from peetsfea.spec.outputs import parse_outputs_table
from peetsfea.types.manifest import OutputsSpec

_SUPPORTED_MODELED_ROLES: frozenset[str] = frozenset(
    {"tx_single_coil", "rx_single_coil", "tx_plate_stack", "rx_plate_stack"}
)
_SUPPORTED_MODELED_PLANES: frozenset[str] = frozenset({"XY", "YZ"})
_PLATE_STACK_ROLES: frozenset[str] = frozenset({"tx_plate_stack", "rx_plate_stack"})

_NON_MODEL_REQUIRED_FIELDS = (
    "object_id",
    "role",
    "material",
    "model_state",
    "canonical_coordinates",
    "plane",
    "non_model",
)
_MODELED_REQUIRED_FIELDS = (
    "object_id",
    "role",
    "plane",
    "placement_owner_id",
    "material",
    "model_state",
    "expected_exported_body_names",
    "expected_exported_body_count",
    "canonical_coordinates",
    "terminal_metadata",
    "source_metadata_path",
)


class ValidatedStepEntry(TypedDict):
    object_id: str
    entry: dict[str, object]


class ValidatedStepLedger(TypedDict):
    source_toml_path: str
    scene_step_path: Path
    seed: int
    em_policy: "Type2ImportEmPolicy"
    outputs: OutputsSpec
    non_model_objects: list[ValidatedStepEntry]
    modeled_objects: list[ValidatedStepEntry]


class Type2ImportEmPolicy(TypedDict):
    radiation_margin_mm: float


def require_key(table: dict[str, object], *, key: str, context: str) -> object:
    if key not in table:
        raise ValueError(f"{context} is missing required key '{key}'")
    return table[key]


def _require_table(value: object, *, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be an object/table")
    return cast(dict[str, object], value)


def require_non_empty_str(value: object, *, context: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{context} must be str")
    if value == "":
        raise ValueError(f"{context} must be non-empty")
    return value


def require_int(value: object, *, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{context} must be int")
    return value


def _require_float(value: object, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{context} must be number")
    return float(value)


def _require_bool(value: object, *, context: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{context} must be bool")
    return value


def _require_positive_float(value: object, *, context: str) -> float:
    checked_value = _require_float(value, context=context)
    if checked_value <= 0.0:
        raise ValueError(f"{context} must be > 0")
    return checked_value


def _require_entry_list(value: object, *, context: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise TypeError(f"{context} must be a list")
    entries: list[dict[str, object]] = []
    for index, raw_entry in enumerate(value):
        entries.append(_require_table(raw_entry, context=f"{context}[{index}]"))
    return entries


def _require_existing_file_from_text(raw_path: object, *, context: str, ledger_dir: Path) -> Path:
    path_text = require_non_empty_str(raw_path, context=context)
    candidate_path = Path(path_text)
    if not candidate_path.is_absolute():
        candidate_path = ledger_dir / candidate_path
    resolved_path = candidate_path.resolve(strict=False)
    if not resolved_path.is_file():
        raise FileNotFoundError(f"{context} does not exist: {resolved_path}")
    return resolved_path


def require_float_triplet(value: object, *, context: str) -> tuple[float, float, float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{context} must be a sequence of length 3")
    if len(value) != 3:
        raise ValueError(f"{context} must contain exactly 3 entries")
    return (
        _require_float(value[0], context=f"{context}[0]"),
        _require_float(value[1], context=f"{context}[1]"),
        _require_float(value[2], context=f"{context}[2]"),
    )


def _require_required_fields(entry: dict[str, object], *, fields: tuple[str, ...], context: str) -> None:
    for field_name in fields:
        if field_name not in entry:
            raise ValueError(f"{context} is missing required key '{field_name}'")


def _validated_em_policy(raw_policy: object, *, context: str) -> Type2ImportEmPolicy:
    policy = _require_table(raw_policy, context=context)
    radiation_margin_mm = _require_positive_float(
        require_key(policy, key="radiation_margin_mm", context=context),
        context=f"{context}.radiation_margin_mm",
    )
    return {"radiation_margin_mm": radiation_margin_mm}


def _validated_terminal_metadata_kind_none(
    raw_terminal_metadata: object,
    *,
    role: str,
    context: str,
) -> None:
    terminal_metadata = _require_table(raw_terminal_metadata, context=f"{context}.terminal_metadata")
    raw_kind = require_key(
        terminal_metadata,
        key="kind",
        context=f"{context}.terminal_metadata",
    )
    kind = require_non_empty_str(raw_kind, context=f"{context}.terminal_metadata.kind")
    if kind != "none":
        raise ValueError(
            f"{context}.terminal_metadata.kind must be 'none' for {role} import-only geometry metadata "
            f"(actual={kind!r})"
        )
    if len(terminal_metadata) != 1:
        raise ValueError(
            f"{context}.terminal_metadata must be exactly {{'kind': 'none'}} for {role} import-only geometry metadata "
            f"(actual_keys={sorted(terminal_metadata)})"
        )


def validated_object_names(raw_names: Sequence[object], *, context: str) -> list[str]:
    if isinstance(raw_names, (str, bytes)):
        raise TypeError(f"{context}.object_names must be a sequence of strings, not str/bytes")
    names: list[str] = []
    for index, raw_name in enumerate(raw_names):
        if not isinstance(raw_name, str):
            raise TypeError(f"{context}.object_names[{index}] must be str")
        if raw_name == "":
            raise ValueError(f"{context}.object_names[{index}] must be non-empty")
        validate_aedt_name(raw_name, field=f"{context}.object_names[{index}]")
        names.append(raw_name)
    return names


def _validated_non_model_entry(
    entry: dict[str, object],
    *,
    index: int,
) -> ValidatedStepEntry:
    context = f"non_model_objects[{index}]"
    _require_required_fields(entry, fields=_NON_MODEL_REQUIRED_FIELDS, context=context)
    object_id = require_non_empty_str(require_key(entry, key="object_id", context=context), context=f"{context}.object_id")
    require_non_empty_str(require_key(entry, key="role", context=context), context=f"{context}.role")
    require_non_empty_str(require_key(entry, key="material", context=context), context=f"{context}.material")
    if _require_bool(require_key(entry, key="model_state", context=context), context=f"{context}.model_state") is not False:
        raise ValueError(f"{context}.model_state must be false")
    if _require_bool(require_key(entry, key="non_model", context=context), context=f"{context}.non_model") is not True:
        raise ValueError(f"{context}.non_model must be true")
    _require_table(require_key(entry, key="canonical_coordinates", context=context), context=f"{context}.canonical_coordinates")
    require_non_empty_str(require_key(entry, key="plane", context=context), context=f"{context}.plane")
    _require_entry_list(require_key(entry, key="member_objects", context=context), context=f"{context}.member_objects")
    return {"object_id": object_id, "entry": entry}


def _validated_modeled_entry(
    entry: dict[str, object],
    *,
    index: int,
) -> ValidatedStepEntry:
    context = f"modeled_objects[{index}]"
    _require_required_fields(entry, fields=_MODELED_REQUIRED_FIELDS, context=context)
    object_id = require_non_empty_str(require_key(entry, key="object_id", context=context), context=f"{context}.object_id")
    role = require_non_empty_str(require_key(entry, key="role", context=context), context=f"{context}.role")
    if role not in _SUPPORTED_MODELED_ROLES:
        raise ValueError(
            f"{context}.role must be one of ['tx_single_coil', 'rx_single_coil', 'tx_plate_stack', 'rx_plate_stack'] "
            f"(actual={role!r})"
        )
    plane = require_non_empty_str(require_key(entry, key="plane", context=context), context=f"{context}.plane")
    if plane not in _SUPPORTED_MODELED_PLANES:
        raise ValueError(f"{context}.plane must be one of ['XY', 'YZ'] (actual={plane!r})")
    if role == "tx_plate_stack" and plane != "YZ":
        raise ValueError(f"{context}.plane must be 'YZ' for tx_plate_stack import-only geometry (actual={plane!r})")
    if role == "rx_plate_stack" and plane != "YZ":
        raise ValueError(f"{context}.plane must be 'YZ' for rx_plate_stack import-only geometry (actual={plane!r})")
    require_non_empty_str(
        require_key(entry, key="placement_owner_id", context=context),
        context=f"{context}.placement_owner_id",
    )
    require_non_empty_str(require_key(entry, key="material", context=context), context=f"{context}.material")
    if _require_bool(require_key(entry, key="model_state", context=context), context=f"{context}.model_state") is not True:
        raise ValueError(f"{context}.model_state must be true")
    _require_table(require_key(entry, key="canonical_coordinates", context=context), context=f"{context}.canonical_coordinates")
    expected_exported_body_names = validated_object_names(
        cast(
            Sequence[object],
            require_key(entry, key="expected_exported_body_names", context=context),
        ),
        context=f"{context}.expected_exported_body_names",
    )
    expected_exported_body_count = require_int(
        require_key(entry, key="expected_exported_body_count", context=context),
        context=f"{context}.expected_exported_body_count",
    )
    if expected_exported_body_count < 1:
        raise ValueError(f"{context}.expected_exported_body_count must be >= 1")
    if expected_exported_body_count != len(expected_exported_body_names):
        raise ValueError(
            f"{context}.expected_exported_body_count must match expected_exported_body_names length "
            f"(count={expected_exported_body_count}, names={len(expected_exported_body_names)})"
        )
    raw_terminal_metadata = require_key(entry, key="terminal_metadata", context=context)
    if role in _PLATE_STACK_ROLES:
        _validated_terminal_metadata_kind_none(
            raw_terminal_metadata,
            role=role,
            context=context,
        )
    else:
        terminal_metadata = _require_table(raw_terminal_metadata, context=f"{context}.terminal_metadata")
        if "kind" in terminal_metadata:
            kind = require_non_empty_str(
                require_key(terminal_metadata, key="kind", context=f"{context}.terminal_metadata"),
                context=f"{context}.terminal_metadata.kind",
            )
            raise ValueError(
                f"{context}.terminal_metadata.kind {kind!r} is unsupported for coil import; "
                "coil roles require explicit terminal geometry metadata"
            )
    require_non_empty_str(
        require_key(entry, key="source_metadata_path", context=context),
        context=f"{context}.source_metadata_path",
    )
    return {"object_id": object_id, "entry": entry}


def require_member_objects(entry: dict[str, object], *, context: str) -> list[dict[str, object]]:
    raw_member_objects = require_key(entry, key="member_objects", context=context)
    return _require_entry_list(raw_member_objects, context=f"{context}.member_objects")


def member_object_id(entry: dict[str, object], *, context: str) -> str:
    return require_non_empty_str(require_key(entry, key="object_id", context=context), context=f"{context}.object_id")


def _member_canonical_coordinates(entry: dict[str, object], *, context: str) -> dict[str, object]:
    return _require_table(
        require_key(entry, key="canonical_coordinates", context=context),
        context=f"{context}.canonical_coordinates",
    )


def find_owner_member(non_model_entries: list[ValidatedStepEntry], *, object_id: str) -> dict[str, object]:
    matching_members: list[dict[str, object]] = []
    for entry_index, validated_entry in enumerate(non_model_entries):
        member_objects = require_member_objects(
            validated_entry["entry"],
            context=f"non_model_objects[{entry_index}]",
        )
        for member_index, member_object in enumerate(member_objects):
            member_context = f"non_model_objects[{entry_index}].member_objects[{member_index}]"
            if member_object_id(member_object, context=member_context) == object_id:
                matching_members.append(member_object)
    if len(matching_members) != 1:
        raise ValueError(
            f"type2 STEP ledger must contain exactly one {object_id} member object "
            f"(actual={len(matching_members)})"
        )
    return matching_members[0]


def outer_bounds_min_xyz(entry: dict[str, object], *, context: str) -> tuple[float, float, float]:
    canonical_coordinates = _member_canonical_coordinates(entry, context=context)
    return require_float_triplet(
        require_key(canonical_coordinates, key="outer_bounds_min_xyz", context=f"{context}.canonical_coordinates"),
        context=f"{context}.canonical_coordinates.outer_bounds_min_xyz",
    )


def outer_bounds_size_xyz(entry: dict[str, object], *, context: str) -> tuple[float, float, float]:
    canonical_coordinates = _member_canonical_coordinates(entry, context=context)
    return require_float_triplet(
        require_key(canonical_coordinates, key="outer_bounds_size_xyz", context=f"{context}.canonical_coordinates"),
        context=f"{context}.canonical_coordinates.outer_bounds_size_xyz",
    )


def load_step_ledger(step_ledger_path: Path) -> ValidatedStepLedger:
    if not step_ledger_path.is_file():
        raise FileNotFoundError(f"type2 STEP ledger not found: {step_ledger_path}")
    ledger_dir = step_ledger_path.parent
    raw_payload = json.loads(step_ledger_path.read_text(encoding="utf-8"))
    payload = _require_table(raw_payload, context="type2_step_ledger")
    source_toml_path = require_non_empty_str(
        require_key(payload, key="source_toml_path", context="type2_step_ledger"),
        context="type2_step_ledger.source_toml_path",
    )
    scene_step_path = _require_existing_file_from_text(
        require_key(payload, key="scene_step_path", context="type2_step_ledger"),
        context="type2_step_ledger.scene_step_path",
        ledger_dir=ledger_dir,
    )
    seed = require_int(require_key(payload, key="seed", context="type2_step_ledger"), context="type2_step_ledger.seed")
    em_policy = _validated_em_policy(
        require_key(payload, key="em_policy", context="type2_step_ledger"),
        context="type2_step_ledger.em_policy",
    )
    outputs = parse_outputs_table(
        require_key(payload, key="outputs", context="type2_step_ledger"),
        context="type2_step_ledger.outputs",
    )
    raw_non_model_entries = _require_entry_list(
        require_key(payload, key="non_model_objects", context="type2_step_ledger"),
        context="type2_step_ledger.non_model_objects",
    )
    if len(raw_non_model_entries) == 0:
        raise ValueError("type2_step_ledger.non_model_objects must not be empty")
    raw_modeled_entries = _require_entry_list(
        require_key(payload, key="modeled_objects", context="type2_step_ledger"),
        context="type2_step_ledger.modeled_objects",
    )
    if len(raw_modeled_entries) == 0:
        raise ValueError("type2_step_ledger.modeled_objects must not be empty")

    seen_object_ids: set[str] = set()
    non_model_entries: list[ValidatedStepEntry] = []
    for index, raw_entry in enumerate(raw_non_model_entries):
        validated_entry = _validated_non_model_entry(raw_entry, index=index)
        object_id = validated_entry["object_id"]
        if object_id in seen_object_ids:
            raise ValueError(f"duplicate type2 object id in STEP ledger: {object_id}")
        seen_object_ids.add(object_id)
        non_model_entries.append(validated_entry)

    modeled_entries: list[ValidatedStepEntry] = []
    for index, raw_entry in enumerate(raw_modeled_entries):
        validated_entry = _validated_modeled_entry(raw_entry, index=index)
        object_id = validated_entry["object_id"]
        if object_id in seen_object_ids:
            raise ValueError(f"duplicate type2 object id in STEP ledger: {object_id}")
        seen_object_ids.add(object_id)
        modeled_entries.append(validated_entry)

    member_object_ids: list[str] = []
    for entry_index, validated_entry in enumerate(non_model_entries):
        member_objects = require_member_objects(validated_entry["entry"], context=f"non_model_objects[{entry_index}]")
        for member_index, member_object in enumerate(member_objects):
            member_context = f"non_model_objects[{entry_index}].member_objects[{member_index}]"
            member_object_ids.append(member_object_id(member_object, context=member_context))
    for index, validated_entry in enumerate(modeled_entries):
        context = f"modeled_objects[{index}]"
        owner_id = require_non_empty_str(
            require_key(validated_entry["entry"], key="placement_owner_id", context=context),
            context=f"{context}.placement_owner_id",
        )
        if member_object_ids.count(owner_id) != 1:
            raise ValueError(
                f"type2 STEP ledger must contain exactly one {owner_id} member object "
                f"(actual={member_object_ids.count(owner_id)})"
            )

    return {
        "source_toml_path": source_toml_path,
        "scene_step_path": scene_step_path,
        "seed": seed,
        "em_policy": em_policy,
        "outputs": outputs,
        "non_model_objects": non_model_entries,
        "modeled_objects": modeled_entries,
    }


__all__ = [
    "ValidatedStepEntry",
    "ValidatedStepLedger",
    "Type2ImportEmPolicy",
    "find_owner_member",
    "load_step_ledger",
    "member_object_id",
    "outer_bounds_min_xyz",
    "outer_bounds_size_xyz",
    "require_float_triplet",
    "require_int",
    "require_key",
    "require_member_objects",
    "require_non_empty_str",
    "validated_object_names",
]

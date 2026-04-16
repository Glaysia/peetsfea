from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypedDict, cast

from peetsfea.aedt import Hfss
from peetsfea.aedt.failfast import raise_on_false, validate_aedt_name
from peetsfea.aedt.proxies import set_object_color, set_object_transparency
from peetsfea.aedt.protocols import HfssSession, ModelerSession
from peetsfea.backend.pyaedt.type2_modeled_import_adapter import build_single_imported_modeled_object_entry

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SOURCE_STEP_LEDGER_PATH = REPO_ROOT / "run" / "step" / "type2" / "type2_step_ledger.json"
DEFAULT_OUTPUT_AEDT_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_import" / "type2_import.aedt"
DEFAULT_IMPORTED_LEDGER_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_import" / "type2_imported_ledger.json"
DEFAULT_DESIGN_NAME = "type2_step_import"
_NON_MODEL_COLOR = (128, 128, 128)
_NON_MODEL_TRANSPARENCY = 0.85
_TX_PCB_COLOR = (0, 128, 0)
_TX_PCB_TRANSPARENCY = 0.85
_TX_PCB_MATERIAL = "FR4_epoxy"
_TX_COPPER_COLOR = (184, 115, 51)
_TX_COPPER_TRANSPARENCY = 0.0
_TX_COPPER_MATERIAL = "copper"
_TX_REGION_OBJECT_ID = "tx_region"


class _ValidatedStepEntry(TypedDict):
    object_id: str
    step_path: Path
    entry: dict[str, object]


class _ValidatedStepLedger(TypedDict):
    source_toml_path: str
    seed: int
    non_model_objects: list[_ValidatedStepEntry]
    modeled_objects: list[_ValidatedStepEntry]


class Type2ImportedLedger(TypedDict):
    source_toml_path: str
    source_step_ledger_path: str
    seed: int
    aedt_path: str
    imported_ledger_path: str
    non_model_objects: list[dict[str, object]]
    modeled_objects: list[dict[str, object]]


HfssFactory = Callable[[str], HfssSession]

_NON_MODEL_REQUIRED_FIELDS = (
    "object_id",
    "role",
    "material",
    "model_state",
    "step_path",
    "canonical_coordinates",
    "plane",
    "non_model",
)
_MODELED_REQUIRED_FIELDS = (
    "object_id",
    "role",
    "material",
    "model_state",
    "step_path",
    "expected_exported_body_names",
    "expected_exported_body_count",
    "canonical_coordinates",
    "terminal_metadata",
    "source_metadata_path",
)
_ADAPTER_LEDGER_FIELDS = (
    "object_id",
    "role",
    "material",
    "model_state",
    "step_path",
    "canonical_coordinates",
    "terminal_metadata",
    "imported_object_names",
)


def create_headless_hfss(design_name: str) -> HfssSession:
    return cast(HfssSession, Hfss(design=design_name, non_graphical=True, new_desktop=True))


def _require_key(table: dict[str, object], *, key: str, context: str) -> object:
    if key not in table:
        raise ValueError(f"{context} is missing required key '{key}'")
    return table[key]


def _require_table(value: object, *, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be an object/table")
    return cast(dict[str, object], value)


def _require_non_empty_str(value: object, *, context: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{context} must be str")
    if value == "":
        raise ValueError(f"{context} must be non-empty")
    return value


def _require_int(value: object, *, context: str) -> int:
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


def _require_entry_list(value: object, *, context: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise TypeError(f"{context} must be a list")
    entries: list[dict[str, object]] = []
    for index, raw_entry in enumerate(value):
        entries.append(_require_table(raw_entry, context=f"{context}[{index}]"))
    return entries


def _require_existing_file_from_text(raw_path: object, *, context: str, ledger_dir: Path) -> Path:
    path_text = _require_non_empty_str(raw_path, context=context)
    candidate_path = Path(path_text)
    if not candidate_path.is_absolute():
        candidate_path = ledger_dir / candidate_path
    resolved_path = candidate_path.resolve(strict=False)
    if not resolved_path.is_file():
        raise FileNotFoundError(f"{context} does not exist: {resolved_path}")
    return resolved_path


def _require_float_triplet(value: object, *, context: str) -> tuple[float, float, float]:
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


def _validated_non_model_entry(
    entry: dict[str, object],
    *,
    index: int,
    ledger_dir: Path,
) -> _ValidatedStepEntry:
    context = f"non_model_objects[{index}]"
    _require_required_fields(entry, fields=_NON_MODEL_REQUIRED_FIELDS, context=context)
    object_id = _require_non_empty_str(_require_key(entry, key="object_id", context=context), context=f"{context}.object_id")
    _require_non_empty_str(_require_key(entry, key="role", context=context), context=f"{context}.role")
    _require_non_empty_str(_require_key(entry, key="material", context=context), context=f"{context}.material")
    if _require_bool(_require_key(entry, key="model_state", context=context), context=f"{context}.model_state") is not False:
        raise ValueError(f"{context}.model_state must be false")
    if _require_bool(_require_key(entry, key="non_model", context=context), context=f"{context}.non_model") is not True:
        raise ValueError(f"{context}.non_model must be true")
    _require_table(_require_key(entry, key="canonical_coordinates", context=context), context=f"{context}.canonical_coordinates")
    _require_non_empty_str(_require_key(entry, key="plane", context=context), context=f"{context}.plane")
    _require_entry_list(_require_key(entry, key="member_objects", context=context), context=f"{context}.member_objects")
    step_path = _require_existing_file_from_text(
        _require_key(entry, key="step_path", context=context),
        context=f"{context}.step_path",
        ledger_dir=ledger_dir,
    )
    return {"object_id": object_id, "step_path": step_path, "entry": entry}


def _validated_modeled_entry(
    entry: dict[str, object],
    *,
    index: int,
    ledger_dir: Path,
) -> _ValidatedStepEntry:
    context = f"modeled_objects[{index}]"
    _require_required_fields(entry, fields=_MODELED_REQUIRED_FIELDS, context=context)
    object_id = _require_non_empty_str(_require_key(entry, key="object_id", context=context), context=f"{context}.object_id")
    role = _require_non_empty_str(_require_key(entry, key="role", context=context), context=f"{context}.role")
    if role != "tx_single_coil":
        raise ValueError(f"{context}.role must be 'tx_single_coil' for the prototype import path (actual={role!r})")
    _require_non_empty_str(_require_key(entry, key="material", context=context), context=f"{context}.material")
    if _require_bool(_require_key(entry, key="model_state", context=context), context=f"{context}.model_state") is not True:
        raise ValueError(f"{context}.model_state must be true")
    _require_table(_require_key(entry, key="canonical_coordinates", context=context), context=f"{context}.canonical_coordinates")
    _validated_object_names(
        cast(
            Sequence[object],
            _require_key(entry, key="expected_exported_body_names", context=context),
        ),
        context=f"{context}.expected_exported_body_names",
    )
    expected_exported_body_count = _require_int(
        _require_key(entry, key="expected_exported_body_count", context=context),
        context=f"{context}.expected_exported_body_count",
    )
    if expected_exported_body_count < 1:
        raise ValueError(f"{context}.expected_exported_body_count must be >= 1")
    _require_table(_require_key(entry, key="terminal_metadata", context=context), context=f"{context}.terminal_metadata")
    _require_non_empty_str(
        _require_key(entry, key="source_metadata_path", context=context),
        context=f"{context}.source_metadata_path",
    )
    step_path = _require_existing_file_from_text(
        _require_key(entry, key="step_path", context=context),
        context=f"{context}.step_path",
        ledger_dir=ledger_dir,
    )
    return {"object_id": object_id, "step_path": step_path, "entry": entry}


def _load_step_ledger(step_ledger_path: Path) -> _ValidatedStepLedger:
    if not step_ledger_path.is_file():
        raise FileNotFoundError(f"type2 STEP ledger not found: {step_ledger_path}")
    ledger_dir = step_ledger_path.parent
    raw_payload = json.loads(step_ledger_path.read_text(encoding="utf-8"))
    payload = _require_table(raw_payload, context="type2_step_ledger")
    source_toml_path = _require_non_empty_str(
        _require_key(payload, key="source_toml_path", context="type2_step_ledger"),
        context="type2_step_ledger.source_toml_path",
    )
    seed = _require_int(_require_key(payload, key="seed", context="type2_step_ledger"), context="type2_step_ledger.seed")
    raw_non_model_entries = _require_entry_list(
        _require_key(payload, key="non_model_objects", context="type2_step_ledger"),
        context="type2_step_ledger.non_model_objects",
    )
    if len(raw_non_model_entries) == 0:
        raise ValueError("type2_step_ledger.non_model_objects must not be empty")
    raw_modeled_entries = _require_entry_list(
        _require_key(payload, key="modeled_objects", context="type2_step_ledger"),
        context="type2_step_ledger.modeled_objects",
    )
    if len(raw_modeled_entries) != 1:
        raise ValueError(
            "type2 STEP import prototype requires exactly one modeled object "
            f"(actual={len(raw_modeled_entries)})"
        )

    seen_object_ids: set[str] = set()
    non_model_entries: list[_ValidatedStepEntry] = []
    for index, raw_entry in enumerate(raw_non_model_entries):
        validated_entry = _validated_non_model_entry(raw_entry, index=index, ledger_dir=ledger_dir)
        object_id = validated_entry["object_id"]
        if object_id in seen_object_ids:
            raise ValueError(f"duplicate type2 object id in STEP ledger: {object_id}")
        seen_object_ids.add(object_id)
        non_model_entries.append(validated_entry)

    modeled_entries: list[_ValidatedStepEntry] = []
    for index, raw_entry in enumerate(raw_modeled_entries):
        validated_entry = _validated_modeled_entry(raw_entry, index=index, ledger_dir=ledger_dir)
        object_id = validated_entry["object_id"]
        if object_id in seen_object_ids:
            raise ValueError(f"duplicate type2 object id in STEP ledger: {object_id}")
        seen_object_ids.add(object_id)
        modeled_entries.append(validated_entry)

    _find_tx_region_member(non_model_entries)

    return {
        "source_toml_path": source_toml_path,
        "seed": seed,
        "non_model_objects": non_model_entries,
        "modeled_objects": modeled_entries,
    }


def _validated_object_names(raw_names: Sequence[object], *, context: str) -> list[str]:
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


def _current_object_names(modeler: ModelerSession, *, context: str) -> list[str]:
    return _validated_object_names(cast(Sequence[object], modeler.object_names), context=context)


def _new_imported_object_names(*, before_import: list[str], after_import: list[str], step_path: Path) -> list[str]:
    before_names = set(before_import)
    imported_names = [name for name in after_import if name not in before_names]
    if not imported_names:
        raise RuntimeError(f"STEP import created no new HFSS objects: {step_path}")
    if len(imported_names) != len(set(imported_names)):
        raise RuntimeError(f"STEP import produced duplicate new HFSS object names: {imported_names}")
    return imported_names


def _import_step_object(
    *,
    modeler: ModelerSession,
    step_path: Path,
    model_state: bool,
    object_id: str,
) -> list[str]:
    before_import = _current_object_names(modeler, context=f"{object_id}.before_import")
    import_result = modeler.import_3d_cad(input_file=step_path)
    raise_on_false(import_result, operation="import_3d_cad", context={"object_id": object_id, "input_file": str(step_path)})
    if not isinstance(import_result, bool):
        raise TypeError(f"Modeler3D.import_3d_cad must return bool (actual={type(import_result).__name__})")
    after_import = _current_object_names(modeler, context=f"{object_id}.after_import")
    imported_names = _new_imported_object_names(
        before_import=before_import,
        after_import=after_import,
        step_path=step_path,
    )
    for imported_name in imported_names:
        state_result = modeler.set_object_model_state(imported_name, model_state)
        raise_on_false(
            state_result,
            operation="set_object_model_state",
            context={"object_id": object_id, "name": imported_name, "model": model_state},
        )
    return imported_names


def _imported_names_from_adapter_entry(entry: dict[str, object]) -> list[str]:
    raw_imported_names = _require_key(
        entry,
        key="imported_object_names",
        context="imported_modeled_object_entry",
    )
    if isinstance(raw_imported_names, (str, bytes)) or not isinstance(raw_imported_names, Sequence):
        raise TypeError("imported_modeled_object_entry.imported_object_names must be a sequence of strings")
    return _validated_object_names(
        cast(Sequence[object], raw_imported_names),
        context="imported_modeled_object_entry",
    )


def _require_member_objects(entry: dict[str, object], *, context: str) -> list[dict[str, object]]:
    raw_member_objects = _require_key(entry, key="member_objects", context=context)
    return _require_entry_list(raw_member_objects, context=f"{context}.member_objects")


def _member_object_id(entry: dict[str, object], *, context: str) -> str:
    return _require_non_empty_str(_require_key(entry, key="object_id", context=context), context=f"{context}.object_id")


def _member_canonical_coordinates(entry: dict[str, object], *, context: str) -> dict[str, object]:
    return _require_table(
        _require_key(entry, key="canonical_coordinates", context=context),
        context=f"{context}.canonical_coordinates",
    )


def _find_tx_region_member(non_model_entries: list[_ValidatedStepEntry]) -> dict[str, object]:
    tx_region_members: list[dict[str, object]] = []
    for entry_index, validated_entry in enumerate(non_model_entries):
        member_objects = _require_member_objects(
            validated_entry["entry"],
            context=f"non_model_objects[{entry_index}]",
        )
        for member_index, member_object in enumerate(member_objects):
            member_context = f"non_model_objects[{entry_index}].member_objects[{member_index}]"
            if _member_object_id(member_object, context=member_context) == _TX_REGION_OBJECT_ID:
                tx_region_members.append(member_object)
    if len(tx_region_members) != 1:
        raise ValueError(
            "type2 STEP ledger must contain exactly one tx_region member object "
            f"(actual={len(tx_region_members)})"
        )
    return tx_region_members[0]


def _outer_bounds_min_xyz(entry: dict[str, object], *, context: str) -> tuple[float, float, float]:
    canonical_coordinates = _member_canonical_coordinates(entry, context=context)
    return _require_float_triplet(
        _require_key(canonical_coordinates, key="outer_bounds_min_xyz", context=f"{context}.canonical_coordinates"),
        context=f"{context}.canonical_coordinates.outer_bounds_min_xyz",
    )


def _outer_bounds_size_xyz(entry: dict[str, object], *, context: str) -> tuple[float, float, float]:
    canonical_coordinates = _member_canonical_coordinates(entry, context=context)
    return _require_float_triplet(
        _require_key(canonical_coordinates, key="outer_bounds_size_xyz", context=f"{context}.canonical_coordinates"),
        context=f"{context}.canonical_coordinates.outer_bounds_size_xyz",
    )


def _object_ref(modeler: ModelerSession, *, name: str, context: str) -> object:
    validate_aedt_name(name, field=f"{context}.name")
    object_ref = modeler.get_object_from_name(name)
    assert object_ref is not None, f"{context} did not resolve HFSS object: {name}"
    return object_ref


def _set_object_material(object_ref: object, *, material_name: str, context: str) -> None:
    if material_name == "":
        raise ValueError(f"{context}.material_name must be non-empty")
    assert hasattr(object_ref, "material_name"), f"{context} is missing required material_name attribute"
    setattr(object_ref, "material_name", material_name)


def _apply_object_visual_state(
    *,
    modeler: ModelerSession,
    object_name: str,
    color: tuple[int, int, int],
    transparency: float,
    context: str,
) -> None:
    object_ref = _object_ref(modeler, name=object_name, context=context)
    set_object_color(object_ref, color=color)
    set_object_transparency(object_ref, transparency=transparency)


def _apply_object_material_and_visual_state(
    *,
    modeler: ModelerSession,
    object_name: str,
    material_name: str,
    color: tuple[int, int, int],
    transparency: float,
    context: str,
) -> None:
    object_ref = _object_ref(modeler, name=object_name, context=context)
    _set_object_material(object_ref, material_name=material_name, context=context)
    set_object_color(object_ref, color=color)
    set_object_transparency(object_ref, transparency=transparency)


def _style_non_model_objects(*, modeler: ModelerSession, object_id: str, imported_object_names: list[str]) -> None:
    for imported_name in imported_object_names:
        _apply_object_visual_state(
            modeler=modeler,
            object_name=imported_name,
            color=_NON_MODEL_COLOR,
            transparency=_NON_MODEL_TRANSPARENCY,
            context=f"{object_id}.non_model_visual_state[{imported_name}]",
        )


def _expected_exported_body_names(modeled_entry: dict[str, object], *, context: str) -> list[str]:
    raw_expected_names = _require_key(modeled_entry, key="expected_exported_body_names", context=context)
    expected_names = _validated_object_names(
        cast(Sequence[object], raw_expected_names),
        context=f"{context}.expected_exported_body_names",
    )
    expected_count = _require_int(
        _require_key(modeled_entry, key="expected_exported_body_count", context=context),
        context=f"{context}.expected_exported_body_count",
    )
    if expected_count != len(expected_names):
        raise ValueError(
            f"{context}.expected_exported_body_count must match expected_exported_body_names length "
            f"(count={expected_count}, names={len(expected_names)})"
        )
    return expected_names


def _move_imported_objects(
    *,
    modeler: ModelerSession,
    object_id: str,
    imported_object_names: list[str],
    vector_xyz: tuple[float, float, float],
) -> None:
    move_result = modeler.move(assignment=imported_object_names, vector=list(vector_xyz))
    raise_on_false(
        move_result,
        operation="move",
        context={"object_id": object_id, "assignment": list(imported_object_names), "vector": list(vector_xyz)},
    )


def _move_tx_into_region(
    *,
    modeler: ModelerSession,
    modeled_entry: dict[str, object],
    imported_object_names: list[str],
    tx_region_member: dict[str, object],
) -> None:
    tx_context = "modeled_objects[0]"
    region_context = "non_model_objects[*].member_objects[tx_region]"
    tx_min_x, tx_min_y, tx_min_z = _outer_bounds_min_xyz(modeled_entry, context=tx_context)
    tx_size_x, tx_size_y, tx_size_z = _outer_bounds_size_xyz(modeled_entry, context=tx_context)
    region_min_x, region_min_y, region_min_z = _outer_bounds_min_xyz(tx_region_member, context=region_context)
    region_size_x, region_size_y, region_size_z = _outer_bounds_size_xyz(tx_region_member, context=region_context)
    if tx_size_x > region_size_x or tx_size_y > region_size_y or tx_size_z > region_size_z:
        raise ValueError(
            "tx_rect_void_coil outer bounds must fit inside tx_region "
            f"(tx_size={(tx_size_x, tx_size_y, tx_size_z)}, region_size={(region_size_x, region_size_y, region_size_z)})"
        )
    target_min_x = region_min_x + (region_size_x - tx_size_x) / 2.0
    target_min_y = region_min_y + (region_size_y - tx_size_y) / 2.0
    target_min_z = region_min_z
    _move_imported_objects(
        modeler=modeler,
        object_id=_require_non_empty_str(_require_key(modeled_entry, key="object_id", context=tx_context), context=f"{tx_context}.object_id"),
        imported_object_names=imported_object_names,
        vector_xyz=(
            target_min_x - tx_min_x,
            target_min_y - tx_min_y,
            target_min_z - tx_min_z,
        ),
    )


def _style_tx_imported_objects(
    *,
    modeler: ModelerSession,
    modeled_entry: dict[str, object],
    imported_object_names: list[str],
) -> None:
    context = "modeled_objects[0]"
    expected_names = _expected_exported_body_names(modeled_entry, context=context)
    if len(imported_object_names) != len(expected_names):
        raise ValueError(
            "imported modeled object count must match expected_exported_body_names "
            f"(imported={len(imported_object_names)}, expected={len(expected_names)})"
        )
    for expected_name, imported_name in zip(expected_names, imported_object_names, strict=True):
        if expected_name.startswith("tx_pcb_l"):
            _apply_object_material_and_visual_state(
                modeler=modeler,
                object_name=imported_name,
                material_name=_TX_PCB_MATERIAL,
                color=_TX_PCB_COLOR,
                transparency=_TX_PCB_TRANSPARENCY,
                context=f"{context}.pcb[{imported_name}]",
            )
            continue
        if expected_name.startswith("tx_copper_l"):
            _apply_object_material_and_visual_state(
                modeler=modeler,
                object_name=imported_name,
                material_name=_TX_COPPER_MATERIAL,
                color=_TX_COPPER_COLOR,
                transparency=_TX_COPPER_TRANSPARENCY,
                context=f"{context}.copper[{imported_name}]",
            )
            continue
        raise ValueError(
            "unsupported tx exported body name; expected tx_pcb_l* or tx_copper_l* "
            f"(actual={expected_name!r})"
        )


def _merge_modeled_adapter_entry(
    *,
    export_entry: dict[str, object],
    adapter_entry: dict[str, object],
) -> dict[str, object]:
    for field_name in _ADAPTER_LEDGER_FIELDS:
        if field_name not in adapter_entry:
            raise ValueError(f"imported_modeled_object_entry is missing required key '{field_name}'")
    merged = dict(export_entry)
    merged["imported_object_names"] = _imported_names_from_adapter_entry(adapter_entry)
    return merged


def _import_validated_ledger(
    *,
    hfss: HfssSession,
    step_ledger_path: Path,
    output_aedt_path: Path,
    imported_ledger_path: Path,
    ledger: _ValidatedStepLedger,
) -> Type2ImportedLedger:
    modeler = hfss.modeler
    tx_region_member = _find_tx_region_member(ledger["non_model_objects"])
    imported_non_model_objects: list[dict[str, object]] = []
    for validated_entry in ledger["non_model_objects"]:
        imported_object_names = _import_step_object(
            modeler=modeler,
            step_path=validated_entry["step_path"],
            model_state=False,
            object_id=validated_entry["object_id"],
        )
        _style_non_model_objects(
            modeler=modeler,
            object_id=validated_entry["object_id"],
            imported_object_names=imported_object_names,
        )
        imported_entry = dict(validated_entry["entry"])
        imported_entry["imported_object_names"] = imported_object_names
        imported_non_model_objects.append(imported_entry)

    imported_modeled_objects: list[dict[str, object]] = []
    for validated_entry in ledger["modeled_objects"]:
        imported_object_names = _import_step_object(
            modeler=modeler,
            step_path=validated_entry["step_path"],
            model_state=True,
            object_id=validated_entry["object_id"],
        )
        _move_tx_into_region(
            modeler=modeler,
            modeled_entry=validated_entry["entry"],
            imported_object_names=imported_object_names,
            tx_region_member=tx_region_member,
        )
        _style_tx_imported_objects(
            modeler=modeler,
            modeled_entry=validated_entry["entry"],
            imported_object_names=imported_object_names,
        )
        adapter_entry = build_single_imported_modeled_object_entry(
            modeled_object=validated_entry["entry"],
            imported_step_path=validated_entry["step_path"],
            imported_object_names=imported_object_names,
        )
        imported_modeled_objects.append(
            _merge_modeled_adapter_entry(
                export_entry=validated_entry["entry"],
                adapter_entry=cast(dict[str, object], adapter_entry),
            )
        )

    save_result = hfss.save_project(str(output_aedt_path))
    raise_on_false(save_result, operation="save_project", context={"path": str(output_aedt_path)})

    imported_ledger: Type2ImportedLedger = {
        "source_toml_path": ledger["source_toml_path"],
        "source_step_ledger_path": str(step_ledger_path),
        "seed": ledger["seed"],
        "aedt_path": str(output_aedt_path),
        "imported_ledger_path": str(imported_ledger_path),
        "non_model_objects": imported_non_model_objects,
        "modeled_objects": imported_modeled_objects,
    }
    imported_ledger_path.parent.mkdir(parents=True, exist_ok=True)
    imported_ledger_path.write_text(json.dumps(imported_ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    return imported_ledger


def import_type2_step_ledger(
    *,
    step_ledger_path: Path = DEFAULT_SOURCE_STEP_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
    design_name: str = DEFAULT_DESIGN_NAME,
    hfss_factory: HfssFactory = create_headless_hfss,
) -> Type2ImportedLedger:
    checked_step_ledger_path = step_ledger_path.resolve(strict=False)
    ledger = _load_step_ledger(checked_step_ledger_path)
    output_aedt_path.parent.mkdir(parents=True, exist_ok=True)

    hfss = hfss_factory(design_name)
    try:
        return _import_validated_ledger(
            hfss=hfss,
            step_ledger_path=checked_step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            ledger=ledger,
        )
    finally:
        release_result = hfss.desktop_class.release_desktop(close_projects=True, close_on_exit=True)
        raise_on_false(
            release_result,
            operation="release_desktop",
            context={"close_projects": True, "close_on_exit": True},
        )


def import_type2_step_ledger_into_hfss(
    *,
    hfss: HfssSession,
    step_ledger_path: Path = DEFAULT_SOURCE_STEP_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
) -> Type2ImportedLedger:
    checked_step_ledger_path = step_ledger_path.resolve(strict=False)
    ledger = _load_step_ledger(checked_step_ledger_path)
    output_aedt_path.parent.mkdir(parents=True, exist_ok=True)
    return _import_validated_ledger(
        hfss=hfss,
        step_ledger_path=checked_step_ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        ledger=ledger,
    )


__all__ = [
    "DEFAULT_DESIGN_NAME",
    "DEFAULT_IMPORTED_LEDGER_PATH",
    "DEFAULT_OUTPUT_AEDT_PATH",
    "DEFAULT_SOURCE_STEP_LEDGER_PATH",
    "HfssFactory",
    "Type2ImportedLedger",
    "create_headless_hfss",
    "import_type2_step_ledger_into_hfss",
    "import_type2_step_ledger",
]

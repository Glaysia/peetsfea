from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypedDict, cast

from peetsfea.aedt import Hfss
from peetsfea.aedt.failfast import raise_on_false, validate_aedt_name
from peetsfea.aedt.protocols import HfssSession, ModelerSession
from peetsfea.backend.pyaedt.type2_modeled_import_adapter import build_single_imported_modeled_object_entry

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SOURCE_STEP_LEDGER_PATH = REPO_ROOT / "run" / "step" / "type2" / "type2_step_ledger.json"
DEFAULT_OUTPUT_AEDT_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_import" / "type2_import.aedt"
DEFAULT_IMPORTED_LEDGER_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_import" / "type2_imported_ledger.json"
DEFAULT_DESIGN_NAME = "type2_step_import"


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
    imported_non_model_objects: list[dict[str, object]] = []
    for validated_entry in ledger["non_model_objects"]:
        imported_object_names = _import_step_object(
            modeler=modeler,
            step_path=validated_entry["step_path"],
            model_state=False,
            object_id=validated_entry["object_id"],
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


__all__ = [
    "DEFAULT_DESIGN_NAME",
    "DEFAULT_IMPORTED_LEDGER_PATH",
    "DEFAULT_OUTPUT_AEDT_PATH",
    "DEFAULT_SOURCE_STEP_LEDGER_PATH",
    "HfssFactory",
    "Type2ImportedLedger",
    "create_headless_hfss",
    "import_type2_step_ledger",
]

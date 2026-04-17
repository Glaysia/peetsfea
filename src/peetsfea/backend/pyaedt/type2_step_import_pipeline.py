from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypedDict, cast

from peetsfea.aedt import Hfss
from peetsfea.aedt.failfast import raise_on_false
from peetsfea.aedt.protocols import HfssSession, ModelerSession
from peetsfea.backend.pyaedt.type2_modeled_import_adapter import build_single_imported_modeled_object_entry
from peetsfea.backend.pyaedt.type2_step_import_ledger import (
    ValidatedStepLedger,
    find_owner_member,
    load_step_ledger,
    require_key,
    require_non_empty_str,
    validated_object_names,
)
from peetsfea.backend.pyaedt.type2_step_import_partition import (
    new_imported_object_names,
    partition_imported_scene_object_names,
)
from peetsfea.backend.pyaedt.type2_step_import_style import (
    set_imported_object_model_state,
    style_imported_modeled_objects,
    style_non_model_objects,
    validate_modeled_bounds_against_owner,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SOURCE_STEP_LEDGER_PATH = REPO_ROOT / "run" / "step" / "type2" / "type2_step_ledger.json"
DEFAULT_OUTPUT_AEDT_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_import" / "type2_import.aedt"
DEFAULT_IMPORTED_LEDGER_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_import" / "type2_imported_ledger.json"
DEFAULT_DESIGN_NAME = "type2_step_import"


class Type2ImportedLedger(TypedDict):
    source_toml_path: str
    source_step_ledger_path: str
    scene_step_path: str
    seed: int
    aedt_path: str
    imported_ledger_path: str
    non_model_objects: list[dict[str, object]]
    modeled_objects: list[dict[str, object]]


HfssFactory = Callable[[str], HfssSession]


def create_headless_hfss(design_name: str) -> HfssSession:
    return cast(HfssSession, Hfss(design=design_name, non_graphical=True, new_desktop=True))


def _current_object_names(modeler: ModelerSession, *, context: str) -> list[str]:
    return validated_object_names(cast(Sequence[object], modeler.object_names), context=context)


def _import_scene_step(
    *,
    modeler: ModelerSession,
    step_path: Path,
    object_id: str,
) -> list[str]:
    before_import = _current_object_names(modeler, context=f"{object_id}.before_import")
    import_result = modeler.import_3d_cad(input_file=step_path)
    raise_on_false(import_result, operation="import_3d_cad", context={"object_id": object_id, "input_file": str(step_path)})
    if not isinstance(import_result, bool):
        raise TypeError(f"Modeler3D.import_3d_cad must return bool (actual={type(import_result).__name__})")
    after_import = _current_object_names(modeler, context=f"{object_id}.after_import")
    imported_names = new_imported_object_names(
        before_import=before_import,
        after_import=after_import,
        step_path=step_path,
    )
    return imported_names


def _imported_names_from_adapter_entry(entry: dict[str, object]) -> list[str]:
    raw_imported_names = require_key(
        entry,
        key="imported_object_names",
        context="imported_modeled_object_entry",
    )
    if isinstance(raw_imported_names, (str, bytes)) or not isinstance(raw_imported_names, Sequence):
        raise TypeError("imported_modeled_object_entry.imported_object_names must be a sequence of strings")
    return validated_object_names(
        cast(Sequence[object], raw_imported_names),
        context="imported_modeled_object_entry",
    )


def _merge_modeled_adapter_entry(
    *,
    export_entry: dict[str, object],
    adapter_entry: dict[str, object],
) -> dict[str, object]:
    merged = dict(export_entry)
    merged["imported_object_names"] = _imported_names_from_adapter_entry(adapter_entry)
    return merged


def _import_validated_ledger(
    *,
    hfss: HfssSession,
    step_ledger_path: Path,
    output_aedt_path: Path,
    imported_ledger_path: Path,
    ledger: ValidatedStepLedger,
) -> Type2ImportedLedger:
    modeler = hfss.modeler
    imported_scene_object_names = _import_scene_step(
        modeler=modeler,
        step_path=ledger["scene_step_path"],
        object_id="type2_scene",
    )
    non_model_names_by_object_id, modeled_names_by_object_id = partition_imported_scene_object_names(
        ledger=ledger,
        imported_object_names=imported_scene_object_names,
    )

    imported_non_model_objects: list[dict[str, object]] = []
    for validated_entry in ledger["non_model_objects"]:
        imported_object_names = non_model_names_by_object_id[validated_entry["object_id"]]
        set_imported_object_model_state(
            modeler=modeler,
            object_id=validated_entry["object_id"],
            imported_object_names=imported_object_names,
            model_state=False,
        )
        style_non_model_objects(
            modeler=modeler,
            object_id=validated_entry["object_id"],
            imported_object_names=imported_object_names,
        )
        imported_entry = dict(validated_entry["entry"])
        imported_entry["imported_object_names"] = imported_object_names
        imported_non_model_objects.append(imported_entry)

    imported_modeled_objects: list[dict[str, object]] = []
    for index, validated_entry in enumerate(ledger["modeled_objects"]):
        context = f"modeled_objects[{index}]"
        owner_id = require_non_empty_str(
            require_key(validated_entry["entry"], key="placement_owner_id", context=context),
            context=f"{context}.placement_owner_id",
        )
        owner_member = find_owner_member(ledger["non_model_objects"], object_id=owner_id)
        validate_modeled_bounds_against_owner(
            modeled_entry=validated_entry["entry"],
            owner_member=owner_member,
            context=context,
        )
        imported_object_names = modeled_names_by_object_id[validated_entry["object_id"]]
        set_imported_object_model_state(
            modeler=modeler,
            object_id=validated_entry["object_id"],
            imported_object_names=imported_object_names,
            model_state=True,
        )
        style_imported_modeled_objects(
            modeler=modeler,
            modeled_entry=validated_entry["entry"],
            imported_object_names=imported_object_names,
            context=context,
        )
        adapter_entry = build_single_imported_modeled_object_entry(
            modeled_object=validated_entry["entry"],
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
        "scene_step_path": str(ledger["scene_step_path"]),
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
    ledger = load_step_ledger(checked_step_ledger_path)
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
    try:
        ledger = load_step_ledger(checked_step_ledger_path)
        output_aedt_path.parent.mkdir(parents=True, exist_ok=True)
        return _import_validated_ledger(
            hfss=hfss,
            step_ledger_path=checked_step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            ledger=ledger,
        )
    finally:
        release_result = hfss.desktop_class.release_desktop(close_projects=False, close_on_exit=False)
        raise_on_false(
            release_result,
            operation="release_desktop",
            context={"close_projects": False, "close_on_exit": False},
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

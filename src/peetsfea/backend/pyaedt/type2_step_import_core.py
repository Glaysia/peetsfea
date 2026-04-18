from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict, cast

from peetsfea.aedt.protocols import HfssSession, ModelerSession
from peetsfea.backend.pyaedt.failfast import raise_on_false
from peetsfea.backend.pyaedt.type2_modeled_import_adapter import build_single_imported_modeled_object_entry
from peetsfea.backend.pyaedt.type2_step_import_ledger import (
    ValidatedStepLedger,
    find_owner_member,
    require_key,
    require_non_empty_str,
    validated_object_names,
)
from peetsfea.backend.pyaedt.type2_step_import_partition import (
    new_imported_object_names,
    partition_imported_scene_object_names,
)
from peetsfea.backend.pyaedt.type2_step_import_style import (
    ensure_underlay_materials,
    set_imported_object_model_state,
    style_imported_modeled_objects,
    style_non_model_objects,
    validate_modeled_bounds_against_owner,
)
from peetsfea.backend.pyaedt.type2_step_runtime_common import current_object_names


class Type2ImportedLedger(TypedDict):
    source_toml_path: str
    source_step_ledger_path: str
    scene_step_path: str
    seed: int
    aedt_path: str
    imported_ledger_path: str
    non_model_objects: list[dict[str, object]]
    modeled_objects: list[dict[str, object]]


def _import_scene_step(
    *,
    modeler: ModelerSession,
    step_path: Path,
    object_id: str,
) -> list[str]:
    before_import = current_object_names(modeler, context=f"{object_id}.before_import")
    import_result = modeler.import_3d_cad(input_file=step_path, import_free_surfaces=True)
    raise_on_false(import_result, operation="import_3d_cad", context={"object_id": object_id, "input_file": str(step_path)})
    if not isinstance(import_result, bool):
        raise TypeError(f"Modeler3D.import_3d_cad must return bool (actual={type(import_result).__name__})")
    after_import = current_object_names(modeler, context=f"{object_id}.after_import")
    return new_imported_object_names(
        before_import=before_import,
        after_import=after_import,
        step_path=step_path,
    )


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


def _all_imported_modeled_object_names(modeled_names_by_object_id: dict[str, list[str]]) -> list[str]:
    imported_object_names: list[str] = []
    for object_id, modeled_object_names in modeled_names_by_object_id.items():
        if not modeled_object_names:
            raise ValueError(f"modeled import partition must claim at least one body per modeled object (object_id={object_id})")
        imported_object_names.extend(modeled_object_names)
    return imported_object_names


def build_imported_ledger(
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
    ensure_underlay_materials(
        hfss,
        imported_modeled_object_names=_all_imported_modeled_object_names(modeled_names_by_object_id),
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
        final_imported_object_names = style_imported_modeled_objects(
            modeler=modeler,
            modeled_entry=validated_entry["entry"],
            imported_object_names=imported_object_names,
            context=context,
        )
        adapter_entry = build_single_imported_modeled_object_entry(
            modeled_object=validated_entry["entry"],
            imported_object_names=final_imported_object_names,
        )
        imported_modeled_objects.append(
            _merge_modeled_adapter_entry(
                export_entry=validated_entry["entry"],
                adapter_entry=cast(dict[str, object], adapter_entry),
            )
        )

    return {
        "source_toml_path": ledger["source_toml_path"],
        "source_step_ledger_path": str(step_ledger_path),
        "scene_step_path": str(ledger["scene_step_path"]),
        "seed": ledger["seed"],
        "aedt_path": str(output_aedt_path),
        "imported_ledger_path": str(imported_ledger_path),
        "non_model_objects": imported_non_model_objects,
        "modeled_objects": imported_modeled_objects,
    }


def write_imported_ledger(*, imported_ledger_path: Path, imported_ledger: Type2ImportedLedger) -> None:
    imported_ledger_path.parent.mkdir(parents=True, exist_ok=True)
    imported_ledger_path.write_text(json.dumps(imported_ledger, ensure_ascii=False, indent=2), encoding="utf-8")


__all__ = [
    "Type2ImportedLedger",
    "build_imported_ledger",
    "write_imported_ledger",
]

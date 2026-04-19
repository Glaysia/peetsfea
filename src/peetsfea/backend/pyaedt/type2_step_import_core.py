from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict, cast

from peetsfea.aedt.proxies import create_group
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
    ImportedBodyGroupEntry,
    new_imported_object_names,
    partition_imported_scene_object_names,
    resolve_imported_body_groups,
)
from peetsfea.backend.pyaedt.type2_step_import_style import (
    ensure_underlay_materials,
    set_imported_object_model_state,
    style_imported_modeled_objects,
    style_non_model_objects,
    validate_modeled_bounds_against_owner,
)
from peetsfea.backend.pyaedt.type2_step_runtime_common import current_object_names

_TX_FERRITE_GROUP_NAME = "g_ferrite_tx"
_RX_FERRITE_GROUP_NAME = "g_ferrite_rx"
_TX_MERGED_STACK_MEMBER_NAMES: tuple[str, str, str] = (
    "tx_stack_pet_psa",
    "tx_stack_ferrite",
    "tx_stack_air",
)
_RX_MERGED_STACK_MEMBER_NAMES: tuple[str, str, str] = (
    "rx_stack_pet_psa",
    "rx_stack_ferrite",
    "rx_stack_air",
)


def _is_legacy_ferrite_family_name_for_plate_stack(name: str) -> bool:
    return name.startswith(
        (
            "tx_underlay_ferrite_u",
            "tx_underlay_pet_psa_u",
            "tx_underlay_air_u",
            "tx_wall_ferrite_u",
            "tx_wall_pet_psa_u",
            "tx_wall_air_u",
            "under_rx_ferrite_u",
            "under_rx_pet_psa_u",
            "under_rx_air_u",
        )
    )


class Type2ImportedLedger(TypedDict):
    source_toml_path: str
    source_step_ledger_path: str
    scene_step_path: str
    seed: int
    aedt_path: str
    imported_ledger_path: str
    non_model_objects: list[dict[str, object]]
    modeled_objects: list[dict[str, object]]


def _require_plate_stack_merged_material_contract(*, modeled_entry: dict[str, object], context: str) -> None:
    role = require_non_empty_str(require_key(modeled_entry, key="role", context=context), context=f"{context}.role")
    if role not in ("tx_plate_stack", "rx_plate_stack"):
        return
    expected_member_names: tuple[str, str, str]
    expected_group_name: str
    role_prefix: str
    if role == "tx_plate_stack":
        expected_member_names = _TX_MERGED_STACK_MEMBER_NAMES
        expected_group_name = _TX_FERRITE_GROUP_NAME
        role_prefix = "tx"
    else:
        expected_member_names = _RX_MERGED_STACK_MEMBER_NAMES
        expected_group_name = _RX_FERRITE_GROUP_NAME
        role_prefix = "rx"
    expected_exported_body_names = validated_object_names(
        cast(
            Sequence[object],
            require_key(modeled_entry, key="expected_exported_body_names", context=context),
        ),
        context=f"{context}.expected_exported_body_names",
    )
    expected_name_set = set(expected_exported_body_names)
    missing_merged_member_names = [name for name in expected_member_names if name not in expected_name_set]
    if missing_merged_member_names:
        raise ValueError(
            f"{context}.expected_exported_body_names must include merged plate-stack material members for {role} "
            f"(missing={missing_merged_member_names}, actual={expected_exported_body_names})"
        )
    legacy_ferrite_member_names = [
        name for name in expected_exported_body_names if _is_legacy_ferrite_family_name_for_plate_stack(name)
    ]
    if legacy_ferrite_member_names:
        raise ValueError(
            f"{context}.expected_exported_body_names contains legacy/import-expanded ferrite-family names for {role}; "
            "this import path only accepts merged exact ferrite-family names "
            f"(legacy_names={legacy_ferrite_member_names}, required={list(expected_member_names)})"
        )
    required_exact_names = (
        f"{role_prefix}_pcb_wall",
        f"{role_prefix}_pcb_coil",
        f"{role_prefix}_stub_in",
        f"{role_prefix}_stub_out",
    )
    missing_exact_names = [name for name in required_exact_names if name not in expected_name_set]
    if missing_exact_names:
        raise ValueError(
            f"{context}.expected_exported_body_names must retain full explicit plate-stack bodies for {role} "
            f"(missing={missing_exact_names}, actual={expected_exported_body_names})"
        )
    required_family_prefixes = (
        f"{role_prefix}_copper_wall_t",
        f"{role_prefix}_copper_coil_t",
        f"{role_prefix}_bridge_s",
    )
    missing_family_prefixes = [
        family_prefix
        for family_prefix in required_family_prefixes
        if not any(name.startswith(family_prefix) for name in expected_exported_body_names)
    ]
    if missing_family_prefixes:
        raise ValueError(
            f"{context}.expected_exported_body_names must retain full explicit plate-stack body families for {role} "
            f"(missing_prefixes={missing_family_prefixes}, actual={expected_exported_body_names})"
        )
    raw_groups = require_key(modeled_entry, key="expected_exported_body_groups", context=context)
    if not isinstance(raw_groups, list):
        raise TypeError(f"{context}.expected_exported_body_groups must be a list")
    if len(raw_groups) != 1:
        raise ValueError(
            f"{context}.expected_exported_body_groups must contain exactly one ferrite group for {role} "
            f"(actual={len(raw_groups)})"
        )
    raw_group = raw_groups[0]
    if not isinstance(raw_group, dict):
        raise TypeError(f"{context}.expected_exported_body_groups[0] must be a table/object")
    group_name = require_non_empty_str(
        require_key(raw_group, key="group_name", context=f"{context}.expected_exported_body_groups[0]"),
        context=f"{context}.expected_exported_body_groups[0].group_name",
    )
    if group_name != expected_group_name:
        raise ValueError(
            f"{context}.expected_exported_body_groups[0].group_name must be {expected_group_name!r} "
            f"(actual={group_name!r})"
        )
    group_member_names = validated_object_names(
        cast(
            Sequence[object],
            require_key(raw_group, key="member_body_names", context=f"{context}.expected_exported_body_groups[0]"),
        ),
        context=f"{context}.expected_exported_body_groups[0].member_body_names",
    )
    if group_member_names != list(expected_member_names):
        raise ValueError(
            f"{context}.expected_exported_body_groups[0].member_body_names must match merged plate-stack material contract "
            f"(expected={list(expected_member_names)}, actual={group_member_names})"
        )


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
    imported_body_groups: list[ImportedBodyGroupEntry],
) -> dict[str, object]:
    merged = dict(export_entry)
    merged["imported_object_names"] = _imported_names_from_adapter_entry(adapter_entry)
    merged["imported_body_groups"] = imported_body_groups
    return merged


def _recreate_imported_body_groups(
    *,
    modeler: ModelerSession,
    modeled_entry: dict[str, object],
    imported_object_names: list[str],
    context: str,
) -> list[ImportedBodyGroupEntry]:
    imported_body_groups = resolve_imported_body_groups(
        modeled_entry=modeled_entry,
        imported_object_names=imported_object_names,
        context=context,
    )
    recreated_groups: list[ImportedBodyGroupEntry] = []
    recreated_group_names: set[str] = set()
    for group_entry in imported_body_groups:
        if group_entry["group_name"] in recreated_group_names:
            raise ValueError(
                f"{context}.imported_body_groups contains duplicate group_name "
                f"(group_name={group_entry['group_name']!r})"
            )
        recreated_group_names.add(group_entry["group_name"])
        created_group_name = create_group(
            modeler,
            objects=list(group_entry["member_object_names"]),
            group_name=group_entry["group_name"],
        )
        if created_group_name != group_entry["group_name"]:
            raise RuntimeError(
                f"{context} recreated body group name drifted after HFSS create_group "
                f"(requested={group_entry['group_name']!r}, actual={created_group_name!r})"
            )
        recreated_groups.append(
            {
                "group_name": created_group_name,
                "member_object_names": group_entry["member_object_names"],
            }
        )
    return recreated_groups


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
        _require_plate_stack_merged_material_contract(modeled_entry=validated_entry["entry"], context=context)
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
        imported_body_groups = _recreate_imported_body_groups(
            modeler=modeler,
            modeled_entry=validated_entry["entry"],
            imported_object_names=final_imported_object_names,
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
                imported_body_groups=imported_body_groups,
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

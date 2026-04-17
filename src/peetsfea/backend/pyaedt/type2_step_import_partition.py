from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict, cast

from peetsfea.backend.pyaedt.type2_step_import_ledger import (
    ValidatedStepEntry,
    ValidatedStepLedger,
    member_object_id,
    require_int,
    require_key,
    require_member_objects,
    validated_object_names,
)

_BODY_ROLE_PCB = "pcb"
_BODY_ROLE_COPPER = "copper"
_BODY_ROLE_TX_UNDERLAY_FERRITE = "tx_underlay_ferrite"
_BODY_ROLE_TX_UNDERLAY_PET_PSA = "tx_underlay_pet_psa"
_BODY_ROLE_TX_UNDERLAY_AIR = "tx_underlay_air"


class ModeledBodyNames(TypedDict):
    pcb_names: list[str]
    copper_names: list[str]
    tx_underlay_ferrite_names: list[str]
    tx_underlay_pet_psa_names: list[str]
    tx_underlay_air_names: list[str]


def new_imported_object_names(*, before_import: list[str], after_import: list[str], step_path: Path) -> list[str]:
    before_names = set(before_import)
    imported_names = [name for name in after_import if name not in before_names]
    if not imported_names:
        raise RuntimeError(f"STEP import created no new HFSS objects: {step_path}")
    if len(imported_names) != len(set(imported_names)):
        raise RuntimeError(f"STEP import produced duplicate new HFSS object names: {imported_names}")
    return imported_names


def expected_exported_body_names(modeled_entry: dict[str, object], *, context: str) -> list[str]:
    raw_expected_names = require_key(modeled_entry, key="expected_exported_body_names", context=context)
    expected_names = validated_object_names(
        cast(Sequence[object], raw_expected_names),
        context=f"{context}.expected_exported_body_names",
    )
    expected_count = require_int(
        require_key(modeled_entry, key="expected_exported_body_count", context=context),
        context=f"{context}.expected_exported_body_count",
    )
    if expected_count != len(expected_names):
        raise ValueError(
            f"{context}.expected_exported_body_count must match expected_exported_body_names length "
            f"(count={expected_count}, names={len(expected_names)})"
        )
    return expected_names


def _body_role_from_expected_name(expected_name: str, *, context: str) -> str:
    if expected_name.startswith(("tx_pcb_l", "rx_pcb_l")):
        return _BODY_ROLE_PCB
    if expected_name.startswith(("tx_copper_l", "rx_copper_l")) or expected_name in ("tx_copper_stack", "rx_copper_stack"):
        return _BODY_ROLE_COPPER
    if expected_name.startswith("tx_underlay_ferrite_u"):
        return _BODY_ROLE_TX_UNDERLAY_FERRITE
    if expected_name.startswith("tx_underlay_pet_psa_u"):
        return _BODY_ROLE_TX_UNDERLAY_PET_PSA
    if expected_name.startswith("tx_underlay_air_u"):
        return _BODY_ROLE_TX_UNDERLAY_AIR
    raise ValueError(
        "unsupported exported body name; expected tx_pcb_l*/tx_copper_l*/tx_copper_stack/"
        "tx_underlay_ferrite_u*/tx_underlay_pet_psa_u*/tx_underlay_air_u* "
        "or rx_pcb_l*/rx_copper_l*/rx_copper_stack "
        f"(actual={expected_name!r}, context={context})"
    )


def resolve_modeled_body_names(
    *,
    modeled_entry: dict[str, object],
    imported_object_names: list[str],
    context: str,
) -> ModeledBodyNames:
    expected_names = expected_exported_body_names(modeled_entry, context=context)
    expected_roles = [_body_role_from_expected_name(name, context=context) for name in expected_names]
    if expected_roles.count(_BODY_ROLE_PCB) < 1 or expected_roles.count(_BODY_ROLE_COPPER) != 1:
        raise ValueError(
            "single-coil type2 import requires one or more PCB bodies and exactly one copper body "
            f"(actual={expected_names})"
        )
    missing_required_names = [expected_name for expected_name in expected_names if expected_name not in imported_object_names]
    if missing_required_names:
        raise ValueError(
            "single-coil type2 import is missing required modeled body names after scene import "
            f"(missing={missing_required_names}, expected={expected_names}, actual={imported_object_names})"
        )
    unexpected_names = [name for name in imported_object_names if name not in expected_names]
    if unexpected_names:
        raise ValueError(
            "single-coil type2 import requires exact exported body labels after scene import "
            f"(unexpected={unexpected_names}, expected={expected_names})"
        )
    pcb_names = [name for name in imported_object_names if name.startswith(("tx_pcb_l", "rx_pcb_l"))]
    copper_names = [
        name
        for name in imported_object_names
        if name.startswith(("tx_copper_l", "rx_copper_l")) or name in ("tx_copper_stack", "rx_copper_stack")
    ]
    tx_underlay_ferrite_names = [name for name in imported_object_names if name.startswith("tx_underlay_ferrite_u")]
    tx_underlay_pet_psa_names = [name for name in imported_object_names if name.startswith("tx_underlay_pet_psa_u")]
    tx_underlay_air_names = [name for name in imported_object_names if name.startswith("tx_underlay_air_u")]
    if len(pcb_names) < 1 or len(copper_names) != 1:
        raise ValueError(
            "single-coil type2 import requires one or more PCB bodies and exactly one copper body after exact-name matching "
            f"(actual={imported_object_names})"
        )
    if not (
        len(tx_underlay_ferrite_names)
        == len(tx_underlay_pet_psa_names)
        == len(tx_underlay_air_names)
    ):
        raise ValueError(
            "single-coil type2 import requires matching TX underlay tri-layer body counts after exact-name matching "
            f"(ferrite={tx_underlay_ferrite_names}, pet_psa={tx_underlay_pet_psa_names}, air={tx_underlay_air_names})"
        )
    return {
        "pcb_names": pcb_names,
        "copper_names": copper_names,
        "tx_underlay_ferrite_names": tx_underlay_ferrite_names,
        "tx_underlay_pet_psa_names": tx_underlay_pet_psa_names,
        "tx_underlay_air_names": tx_underlay_air_names,
    }


def _non_model_member_owner_ids(
    non_model_entries: list[ValidatedStepEntry],
) -> dict[str, str]:
    owner_by_member_id: dict[str, str] = {}
    for entry_index, validated_entry in enumerate(non_model_entries):
        object_id = validated_entry["object_id"]
        member_objects = require_member_objects(validated_entry["entry"], context=f"non_model_objects[{entry_index}]")
        for member_index, member_object in enumerate(member_objects):
            member_context = f"non_model_objects[{entry_index}].member_objects[{member_index}]"
            member_id = member_object_id(member_object, context=member_context)
            if member_id in owner_by_member_id:
                raise ValueError(f"duplicate non-model member object id in STEP ledger: {member_id}")
            owner_by_member_id[member_id] = object_id
    return owner_by_member_id


def partition_imported_scene_object_names(
    *,
    ledger: ValidatedStepLedger,
    imported_object_names: list[str],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    modeled_names_by_object_id: dict[str, list[str]] = {}
    claimed_modeled_names: set[str] = set()
    for index, validated_entry in enumerate(ledger["modeled_objects"]):
        context = f"modeled_objects[{index}]"
        expected_names = expected_exported_body_names(validated_entry["entry"], context=context)
        for expected_name in expected_names:
            if expected_name in claimed_modeled_names:
                raise ValueError(f"duplicate modeled expected body name in STEP ledger: {expected_name}")
            if expected_name not in imported_object_names:
                raise ValueError(
                    "scene STEP import is missing required modeled body name "
                    f"(object_id={validated_entry['object_id']}, body_name={expected_name})"
                )
            claimed_modeled_names.add(expected_name)
        modeled_names_by_object_id[validated_entry["object_id"]] = [
            name for name in imported_object_names if name in expected_names
        ]

    non_model_owner_by_member_id = _non_model_member_owner_ids(ledger["non_model_objects"])
    expected_non_model_member_ids = set(non_model_owner_by_member_id)
    imported_non_model_names = [name for name in imported_object_names if name not in claimed_modeled_names]
    unclaimed_names = [name for name in imported_non_model_names if name not in non_model_owner_by_member_id]
    if unclaimed_names:
        raise ValueError(f"scene STEP import produced unclaimed imported object names: {unclaimed_names}")
    missing_non_model_names = sorted(expected_non_model_member_ids - set(imported_non_model_names))
    if missing_non_model_names:
        raise ValueError(f"scene STEP import is missing non-model member object names: {missing_non_model_names}")

    non_model_names_by_object_id: dict[str, list[str]] = {
        validated_entry["object_id"]: [] for validated_entry in ledger["non_model_objects"]
    }
    for imported_name in imported_non_model_names:
        owner_object_id = non_model_owner_by_member_id[imported_name]
        non_model_names_by_object_id[owner_object_id].append(imported_name)

    for validated_entry in ledger["modeled_objects"]:
        object_id = validated_entry["object_id"]
        if not modeled_names_by_object_id[object_id]:
            raise ValueError(f"scene STEP import claimed no modeled bodies for {object_id}")

    return (non_model_names_by_object_id, modeled_names_by_object_id)


__all__ = [
    "expected_exported_body_names",
    "new_imported_object_names",
    "partition_imported_scene_object_names",
    "resolve_modeled_body_names",
]

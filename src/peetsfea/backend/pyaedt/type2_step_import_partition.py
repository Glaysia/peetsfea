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
    require_non_empty_str,
    validated_object_names,
)

_BODY_ROLE_PCB = "pcb"
_BODY_ROLE_COPPER = "copper"
_BODY_ROLE_UNDERLAY_FERRITE = "underlay_ferrite"
_BODY_ROLE_UNDERLAY_PET_PSA = "underlay_pet_psa"
_BODY_ROLE_UNDERLAY_AIR = "underlay_air"
_SINGLE_COIL_ROLES: frozenset[str] = frozenset({"tx_single_coil", "rx_single_coil"})
_PLATE_STACK_ROLES: frozenset[str] = frozenset({"tx_plate_stack", "rx_plate_stack"})
_TX_FERRITE_GROUP_NAME = "g_ferrite_tx"
_RX_FERRITE_GROUP_NAME = "g_ferrite_rx"
_TX_PCB_WALL_NAME = "tx_pcb_wall"
_TX_PCB_COIL_NAME = "tx_pcb_coil"
_TX_COPPER_WALL_NAME = "tx_copper_wall"
_TX_COPPER_COIL_NAME = "tx_copper_coil"
_RX_PCB_WALL_NAME = "rx_pcb_wall"
_RX_PCB_COIL_NAME = "rx_pcb_coil"
_RX_COPPER_WALL_NAME = "rx_copper_wall"
_RX_COPPER_COIL_NAME = "rx_copper_coil"
_TX_UNDERLAY_FERRITE_NAME_PREFIX = "tx_underlay_ferrite_u"
_TX_UNDERLAY_PET_PSA_NAME_PREFIX = "tx_underlay_pet_psa_u"
_TX_UNDERLAY_AIR_NAME_PREFIX = "tx_underlay_air_u"
_TX_WALL_FERRITE_NAME_PREFIX = "tx_wall_ferrite_u"
_TX_WALL_PET_PSA_NAME_PREFIX = "tx_wall_pet_psa_u"
_TX_WALL_AIR_NAME_PREFIX = "tx_wall_air_u"
_TX_STACK_FERRITE_NAME_PREFIX = "tx_stack_ferrite_u"
_TX_STACK_PET_PSA_NAME_PREFIX = "tx_stack_pet_psa_u"
_TX_STACK_AIR_NAME_PREFIX = "tx_stack_air_u"
_RX_UNDERLAY_FERRITE_NAME_PREFIX = "under_rx_ferrite_u"
_RX_UNDERLAY_PET_PSA_NAME_PREFIX = "under_rx_pet_psa_u"
_RX_UNDERLAY_AIR_NAME_PREFIX = "under_rx_air_u"
_RX_STACK_FERRITE_NAME_PREFIX = "rx_stack_ferrite_u"
_RX_STACK_PET_PSA_NAME_PREFIX = "rx_stack_pet_psa_u"
_RX_STACK_AIR_NAME_PREFIX = "rx_stack_air_u"
_TX_FERRITE_GROUP_MEMBER_PREFIXES = (
    _TX_UNDERLAY_FERRITE_NAME_PREFIX,
    _TX_UNDERLAY_PET_PSA_NAME_PREFIX,
    _TX_UNDERLAY_AIR_NAME_PREFIX,
    _TX_WALL_FERRITE_NAME_PREFIX,
    _TX_WALL_PET_PSA_NAME_PREFIX,
    _TX_WALL_AIR_NAME_PREFIX,
    _TX_STACK_FERRITE_NAME_PREFIX,
    _TX_STACK_PET_PSA_NAME_PREFIX,
    _TX_STACK_AIR_NAME_PREFIX,
)
_RX_FERRITE_GROUP_MEMBER_PREFIXES = (
    _RX_UNDERLAY_FERRITE_NAME_PREFIX,
    _RX_UNDERLAY_PET_PSA_NAME_PREFIX,
    _RX_UNDERLAY_AIR_NAME_PREFIX,
    _RX_STACK_FERRITE_NAME_PREFIX,
    _RX_STACK_PET_PSA_NAME_PREFIX,
    _RX_STACK_AIR_NAME_PREFIX,
)
_ALL_FERRITE_GROUP_MEMBER_PREFIXES = (
    *_TX_FERRITE_GROUP_MEMBER_PREFIXES,
    *_RX_FERRITE_GROUP_MEMBER_PREFIXES,
)
_UNDERLAY_FERRITE_NAME_PREFIXES = (
    _TX_UNDERLAY_FERRITE_NAME_PREFIX,
    _TX_WALL_FERRITE_NAME_PREFIX,
    _RX_UNDERLAY_FERRITE_NAME_PREFIX,
    _TX_STACK_FERRITE_NAME_PREFIX,
    _RX_STACK_FERRITE_NAME_PREFIX,
)
_UNDERLAY_PET_PSA_NAME_PREFIXES = (
    _TX_UNDERLAY_PET_PSA_NAME_PREFIX,
    _TX_WALL_PET_PSA_NAME_PREFIX,
    _RX_UNDERLAY_PET_PSA_NAME_PREFIX,
    _TX_STACK_PET_PSA_NAME_PREFIX,
    _RX_STACK_PET_PSA_NAME_PREFIX,
)
_UNDERLAY_AIR_NAME_PREFIXES = (
    _TX_UNDERLAY_AIR_NAME_PREFIX,
    _TX_WALL_AIR_NAME_PREFIX,
    _RX_UNDERLAY_AIR_NAME_PREFIX,
    _TX_STACK_AIR_NAME_PREFIX,
    _RX_STACK_AIR_NAME_PREFIX,
)


class ModeledBodyNames(TypedDict):
    pcb_names: list[str]
    copper_names: list[str]
    underlay_ferrite_names: list[str]
    underlay_pet_psa_names: list[str]
    underlay_air_names: list[str]


class ImportedBodyGroupEntry(TypedDict):
    group_name: str
    member_object_names: list[str]


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


def expected_exported_body_groups(modeled_entry: dict[str, object], *, context: str) -> list[ImportedBodyGroupEntry]:
    role = require_non_empty_str(require_key(modeled_entry, key="role", context=context), context=f"{context}.role")
    expected_names = expected_exported_body_names(modeled_entry, context=context)
    raw_groups = require_key(modeled_entry, key="expected_exported_body_groups", context=context)
    if not isinstance(raw_groups, list):
        raise TypeError(f"{context}.expected_exported_body_groups must be a list")
    groups: list[ImportedBodyGroupEntry] = []
    seen_group_names: set[str] = set()
    for group_index, raw_group in enumerate(raw_groups):
        group_context = f"{context}.expected_exported_body_groups[{group_index}]"
        if not isinstance(raw_group, dict):
            raise TypeError(f"{group_context} must be a table/object")
        group_name = require_non_empty_str(
            require_key(raw_group, key="group_name", context=group_context),
            context=f"{group_context}.group_name",
        )
        if group_name in seen_group_names:
            raise ValueError(f"duplicate expected exported body group name: {group_name}")
        seen_group_names.add(group_name)
        member_object_names = validated_object_names(
            cast(
                Sequence[object],
                require_key(raw_group, key="member_body_names", context=group_context),
            ),
            context=f"{group_context}.member_body_names",
        )
        groups.append(
            {
                "group_name": group_name,
                "member_object_names": member_object_names,
            }
        )
    expected_group_name, expected_member_names = _ferrite_group_contract_for_role(
        role=role,
        expected_names=expected_names,
        context=context,
    )
    if not expected_member_names:
        if len(groups) != 0:
            raise ValueError(
                f"{context}.expected_exported_body_groups must be empty when no ferrite family bodies exist "
                f"(role={role}, actual_groups={len(groups)})"
            )
        return groups
    if len(groups) != 1:
        raise ValueError(
            f"{context}.expected_exported_body_groups must contain exactly one ferrite group "
            f"(role={role}, actual_groups={len(groups)})"
        )
    group_entry = groups[0]
    if group_entry["group_name"] != expected_group_name:
        raise ValueError(
            f"{context}.expected_exported_body_groups[0].group_name must be {expected_group_name!r} "
            f"(actual={group_entry['group_name']!r})"
        )
    if group_entry["member_object_names"] != expected_member_names:
        raise ValueError(
            f"{context}.expected_exported_body_groups[0].member_body_names must match ferrite family members "
            "in expected_exported_body_names order "
            f"(expected={expected_member_names}, actual={group_entry['member_object_names']})"
        )
    return groups


def _ferrite_group_contract_for_role(
    *,
    role: str,
    expected_names: list[str],
    context: str,
) -> tuple[str, list[str]]:
    member_prefixes: tuple[str, ...]
    expected_group_name: str
    if role.startswith("tx_"):
        member_prefixes = _TX_FERRITE_GROUP_MEMBER_PREFIXES
        expected_group_name = _TX_FERRITE_GROUP_NAME
    elif role.startswith("rx_"):
        member_prefixes = _RX_FERRITE_GROUP_MEMBER_PREFIXES
        expected_group_name = _RX_FERRITE_GROUP_NAME
    else:
        raise ValueError(f"{context}.role is unsupported for ferrite group validation (actual={role!r})")
    mismatched_role_members = [
        name
        for name in expected_names
        if name.startswith(_ALL_FERRITE_GROUP_MEMBER_PREFIXES) and not name.startswith(member_prefixes)
    ]
    if mismatched_role_members:
        raise ValueError(
            f"{context}.expected_exported_body_names contains ferrite family bodies that do not match {role} "
            f"(mismatched={mismatched_role_members})"
        )
    ferrite_group_members = [name for name in expected_names if name.startswith(member_prefixes)]
    return (expected_group_name, ferrite_group_members)


def _body_role_from_expected_name(expected_name: str, *, context: str) -> str:
    if expected_name.startswith(("tx_pcb_l", "rx_pcb_l")) or expected_name in (
        _TX_PCB_WALL_NAME,
        _TX_PCB_COIL_NAME,
        _RX_PCB_WALL_NAME,
        _RX_PCB_COIL_NAME,
    ):
        return _BODY_ROLE_PCB
    if expected_name.startswith(("tx_copper_l", "rx_copper_l")) or expected_name in (
            "tx_copper_stack",
            "rx_copper_stack",
            _TX_COPPER_WALL_NAME,
            _TX_COPPER_COIL_NAME,
            _RX_COPPER_WALL_NAME,
            _RX_COPPER_COIL_NAME,
        ):
        return _BODY_ROLE_COPPER
    if expected_name.startswith(
        (
            "tx_copper_wall_t",
            "tx_copper_coil_t",
            "tx_bridge_s",
            "tx_stub_",
            "rx_copper_wall_t",
            "rx_copper_coil_t",
            "rx_bridge_s",
            "rx_stub_",
        )
    ):
        return _BODY_ROLE_COPPER
    if expected_name.startswith(_UNDERLAY_FERRITE_NAME_PREFIXES):
        return _BODY_ROLE_UNDERLAY_FERRITE
    if expected_name.startswith(_UNDERLAY_PET_PSA_NAME_PREFIXES):
        return _BODY_ROLE_UNDERLAY_PET_PSA
    if expected_name.startswith(_UNDERLAY_AIR_NAME_PREFIXES):
        return _BODY_ROLE_UNDERLAY_AIR
    raise ValueError(
        "unsupported exported body name; expected tx_pcb_l*/tx_copper_l*/tx_copper_stack/"
        "tx_copper_wall/tx_pcb_wall/tx_copper_wall_t*/tx_stack_ferrite_u*/tx_stack_pet_psa_u*/"
        "tx_stack_air_u*/tx_pcb_coil/tx_copper_coil/tx_copper_coil_t*/tx_bridge_s*/tx_stub_* "
        "tx_underlay_ferrite_u*/tx_underlay_pet_psa_u*/tx_underlay_air_u* "
        "tx_wall_ferrite_u*/tx_wall_pet_psa_u*/tx_wall_air_u* "
        "or rx_pcb_l*/rx_copper_l*/rx_copper_stack/"
        "rx_copper_wall/rx_pcb_wall/rx_copper_wall_t*/rx_stack_ferrite_u*/rx_stack_pet_psa_u*/"
        "rx_stack_air_u*/rx_pcb_coil/rx_copper_coil/rx_copper_coil_t*/rx_bridge_s*/rx_stub_* "
        "under_rx_ferrite_u*/under_rx_pet_psa_u*/under_rx_air_u* "
        f"(actual={expected_name!r}, context={context})"
    )


def _resolved_pcb_names(imported_object_names: list[str]) -> list[str]:
    return [
        name
        for name in imported_object_names
        if name.startswith(("tx_pcb_l", "rx_pcb_l"))
        or name in (_TX_PCB_WALL_NAME, _TX_PCB_COIL_NAME, _RX_PCB_WALL_NAME, _RX_PCB_COIL_NAME)
    ]


def _resolved_copper_names(imported_object_names: list[str]) -> list[str]:
    return [
        name
        for name in imported_object_names
        if name.startswith(("tx_copper_l", "rx_copper_l"))
        or name.startswith(
            (
                "tx_copper_wall_t",
                "tx_copper_coil_t",
                "tx_bridge_s",
                "tx_stub_",
                "rx_copper_wall_t",
                "rx_copper_coil_t",
                "rx_bridge_s",
                "rx_stub_",
            )
        )
        or name
        in (
            "tx_copper_stack",
            "rx_copper_stack",
            _TX_COPPER_WALL_NAME,
            _TX_COPPER_COIL_NAME,
            _RX_COPPER_WALL_NAME,
            _RX_COPPER_COIL_NAME,
        )
    ]


def _require_exact_name_contract(
    *,
    expected_names: list[str],
    imported_object_names: list[str],
    context: str,
    role_label: str,
) -> None:
    missing_required_names = [expected_name for expected_name in expected_names if expected_name not in imported_object_names]
    if missing_required_names:
        raise ValueError(
            f"{role_label} type2 import is missing required modeled body names after scene import "
            f"(missing={missing_required_names}, expected={expected_names}, actual={imported_object_names})"
        )
    unexpected_names = [name for name in imported_object_names if name not in expected_names]
    if unexpected_names:
        raise ValueError(
            f"{role_label} type2 import requires exact exported body labels after scene import "
            f"(unexpected={unexpected_names}, expected={expected_names})"
        )


def resolve_modeled_body_names(
    *,
    modeled_entry: dict[str, object],
    imported_object_names: list[str],
    context: str,
) -> ModeledBodyNames:
    role = require_non_empty_str(require_key(modeled_entry, key="role", context=context), context=f"{context}.role")
    expected_names = expected_exported_body_names(modeled_entry, context=context)
    expected_roles = [_body_role_from_expected_name(name, context=context) for name in expected_names]
    if role in _SINGLE_COIL_ROLES:
        if expected_roles.count(_BODY_ROLE_PCB) < 1 or expected_roles.count(_BODY_ROLE_COPPER) != 1:
            raise ValueError(
                "single-coil type2 import requires one or more PCB bodies and exactly one copper body "
                f"(actual={expected_names})"
            )
    elif role in _PLATE_STACK_ROLES:
        if expected_roles.count(_BODY_ROLE_PCB) != 2 or expected_roles.count(_BODY_ROLE_COPPER) < 2:
            raise ValueError(
                "plate-stack type2 import requires exactly two PCB bodies and at least two copper bodies "
                f"(actual={expected_names})"
            )
    else:
        raise ValueError(f"{context}.role is unsupported for modeled body partition (actual={role!r})")
    _require_exact_name_contract(
        expected_names=expected_names,
        imported_object_names=imported_object_names,
        context=context,
        role_label="single-coil" if role in _SINGLE_COIL_ROLES else "plate-stack",
    )
    pcb_names = _resolved_pcb_names(imported_object_names)
    copper_names = _resolved_copper_names(imported_object_names)
    underlay_ferrite_names = [name for name in imported_object_names if name.startswith(_UNDERLAY_FERRITE_NAME_PREFIXES)]
    underlay_pet_psa_names = [name for name in imported_object_names if name.startswith(_UNDERLAY_PET_PSA_NAME_PREFIXES)]
    underlay_air_names = [name for name in imported_object_names if name.startswith(_UNDERLAY_AIR_NAME_PREFIXES)]
    if role in _SINGLE_COIL_ROLES:
        if len(pcb_names) < 1 or len(copper_names) != 1:
            raise ValueError(
                "single-coil type2 import requires one or more PCB bodies and exactly one copper body after exact-name matching "
                f"(actual={imported_object_names})"
            )
    else:
        if len(pcb_names) != 2 or len(copper_names) < 2:
            raise ValueError(
                "plate-stack type2 import requires exactly two PCB bodies and at least two copper bodies after exact-name matching "
                f"(actual={imported_object_names})"
            )
    return {
        "pcb_names": pcb_names,
        "copper_names": copper_names,
        "underlay_ferrite_names": underlay_ferrite_names,
        "underlay_pet_psa_names": underlay_pet_psa_names,
        "underlay_air_names": underlay_air_names,
    }


def resolve_imported_body_groups(
    *,
    modeled_entry: dict[str, object],
    imported_object_names: list[str],
    context: str,
) -> list[ImportedBodyGroupEntry]:
    expected_names = expected_exported_body_names(modeled_entry, context=context)
    expected_groups = expected_exported_body_groups(modeled_entry, context=context)
    missing_names = [name for name in expected_names if name not in imported_object_names]
    if missing_names:
        raise ValueError(
            f"{context} cannot resolve imported body groups before exact imported names are present "
            f"(missing={missing_names})"
        )
    imported_name_set = set(imported_object_names)
    resolved_groups: list[ImportedBodyGroupEntry] = []
    for group_entry in expected_groups:
        member_object_names = group_entry["member_object_names"]
        missing_group_members = [name for name in member_object_names if name not in imported_name_set]
        if missing_group_members:
            raise ValueError(
                f"{context} expected body group is missing imported members "
                f"(group_name={group_entry['group_name']}, missing={missing_group_members})"
            )
        resolved_groups.append(group_entry)
    return resolved_groups


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
    "ImportedBodyGroupEntry",
    "expected_exported_body_groups",
    "expected_exported_body_names",
    "new_imported_object_names",
    "partition_imported_scene_object_names",
    "resolve_imported_body_groups",
    "resolve_modeled_body_names",
]

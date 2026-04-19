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
_TX_COPPER_GROUP_NAME = "g_copper_tx"
_RX_COPPER_GROUP_NAME = "g_copper_rx"
_TX_FERRITE_GROUP_NAME = "g_ferrite_tx"
_RX_FERRITE_GROUP_NAME = "g_ferrite_rx"
_TX_PLATE_COPPER_NAME = "tx_plate_copper"
_RX_PLATE_COPPER_NAME = "rx_plate_copper"
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
_TX_STACK_FERRITE_NAME = "tx_stack_ferrite"
_TX_STACK_PET_PSA_NAME = "tx_stack_pet_psa"
_TX_STACK_AIR_NAME = "tx_stack_air"
_RX_UNDERLAY_FERRITE_NAME_PREFIX = "under_rx_ferrite_u"
_RX_UNDERLAY_PET_PSA_NAME_PREFIX = "under_rx_pet_psa_u"
_RX_UNDERLAY_AIR_NAME_PREFIX = "under_rx_air_u"
_RX_STACK_FERRITE_NAME = "rx_stack_ferrite"
_RX_STACK_PET_PSA_NAME = "rx_stack_pet_psa"
_RX_STACK_AIR_NAME = "rx_stack_air"
_TX_SINGLE_COIL_FERRITE_GROUP_MEMBER_PREFIXES = (
    _TX_UNDERLAY_FERRITE_NAME_PREFIX,
    _TX_UNDERLAY_PET_PSA_NAME_PREFIX,
    _TX_UNDERLAY_AIR_NAME_PREFIX,
    _TX_WALL_FERRITE_NAME_PREFIX,
    _TX_WALL_PET_PSA_NAME_PREFIX,
    _TX_WALL_AIR_NAME_PREFIX,
)
_RX_SINGLE_COIL_FERRITE_GROUP_MEMBER_PREFIXES = (
    _RX_UNDERLAY_FERRITE_NAME_PREFIX,
    _RX_UNDERLAY_PET_PSA_NAME_PREFIX,
    _RX_UNDERLAY_AIR_NAME_PREFIX,
)
_TX_PLATE_STACK_FERRITE_GROUP_MEMBER_NAMES = (
    _TX_STACK_PET_PSA_NAME,
    _TX_STACK_FERRITE_NAME,
    _TX_STACK_AIR_NAME,
)
_RX_PLATE_STACK_FERRITE_GROUP_MEMBER_NAMES = (
    _RX_STACK_PET_PSA_NAME,
    _RX_STACK_FERRITE_NAME,
    _RX_STACK_AIR_NAME,
)
_ALL_FERRITE_GROUP_MEMBER_PREFIXES = (
    *_TX_SINGLE_COIL_FERRITE_GROUP_MEMBER_PREFIXES,
    *_RX_SINGLE_COIL_FERRITE_GROUP_MEMBER_PREFIXES,
)
_ALL_FERRITE_GROUP_MEMBER_NAMES = (
    *_TX_PLATE_STACK_FERRITE_GROUP_MEMBER_NAMES,
    *_RX_PLATE_STACK_FERRITE_GROUP_MEMBER_NAMES,
)
_LEGACY_PLATE_STACK_COPPER_NAME_PREFIXES = (
    "tx_copper_wall_t",
    "tx_copper_coil_t",
    "tx_bridge_s",
    "tx_stub_",
    "rx_copper_wall_t",
    "rx_copper_coil_t",
    "rx_bridge_s",
    "rx_stub_",
)
_UNDERLAY_FERRITE_NAME_PREFIXES = (
    _TX_UNDERLAY_FERRITE_NAME_PREFIX,
    _TX_WALL_FERRITE_NAME_PREFIX,
    _RX_UNDERLAY_FERRITE_NAME_PREFIX,
)
_UNDERLAY_PET_PSA_NAME_PREFIXES = (
    _TX_UNDERLAY_PET_PSA_NAME_PREFIX,
    _TX_WALL_PET_PSA_NAME_PREFIX,
    _RX_UNDERLAY_PET_PSA_NAME_PREFIX,
)
_UNDERLAY_AIR_NAME_PREFIXES = (
    _TX_UNDERLAY_AIR_NAME_PREFIX,
    _TX_WALL_AIR_NAME_PREFIX,
    _RX_UNDERLAY_AIR_NAME_PREFIX,
)


def _is_generic_solid_name(name: str) -> bool:
    return name.casefold().startswith("solid")


def _is_ferrite_family_name(name: str) -> bool:
    return name.startswith(_UNDERLAY_FERRITE_NAME_PREFIXES) or name in (
        _TX_STACK_FERRITE_NAME,
        _RX_STACK_FERRITE_NAME,
    )


def _is_pet_psa_family_name(name: str) -> bool:
    return name.startswith(_UNDERLAY_PET_PSA_NAME_PREFIXES) or name in (
        _TX_STACK_PET_PSA_NAME,
        _RX_STACK_PET_PSA_NAME,
    )


def _is_air_family_name(name: str) -> bool:
    return name.startswith(_UNDERLAY_AIR_NAME_PREFIXES) or name in (
        _TX_STACK_AIR_NAME,
        _RX_STACK_AIR_NAME,
    )


def _is_any_ferrite_group_name(name: str) -> bool:
    return name.startswith(_ALL_FERRITE_GROUP_MEMBER_PREFIXES) or name in _ALL_FERRITE_GROUP_MEMBER_NAMES


def _is_legacy_plate_stack_copper_segment_name(name: str) -> bool:
    return name.startswith(_LEGACY_PLATE_STACK_COPPER_NAME_PREFIXES)


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
    expected_group_contract = _group_contract_for_role(
        role=role,
        expected_names=expected_names,
        context=context,
    )
    if len(groups) != len(expected_group_contract):
        raise ValueError(
            f"{context}.expected_exported_body_groups must match required role group contract "
            f"(role={role}, expected_groups={len(expected_group_contract)}, actual_groups={len(groups)})"
        )
    for index, (expected_group_name, expected_member_names) in enumerate(expected_group_contract):
        group_entry = groups[index]
        if group_entry["group_name"] != expected_group_name:
            raise ValueError(
                f"{context}.expected_exported_body_groups[{index}].group_name must be {expected_group_name!r} "
                f"(actual={group_entry['group_name']!r})"
            )
        if group_entry["member_object_names"] != expected_member_names:
            raise ValueError(
                f"{context}.expected_exported_body_groups[{index}].member_body_names must match role contract "
                "in expected_exported_body_names order "
                f"(expected={expected_member_names}, actual={group_entry['member_object_names']})"
            )
    return groups


def _group_contract_for_role(
    *,
    role: str,
    expected_names: list[str],
    context: str,
) -> list[tuple[str, list[str]]]:
    def _single_coil_group_contract(
        *,
        member_prefixes: tuple[str, ...],
        member_names: tuple[str, ...],
        ferrite_group_name: str,
    ) -> list[tuple[str, list[str]]]:
        mismatched_role_members = [
            name
            for name in expected_names
            if _is_any_ferrite_group_name(name)
            and (
                (len(member_prefixes) > 0 and not name.startswith(member_prefixes))
                or (len(member_names) > 0 and name not in member_names)
            )
        ]
        if mismatched_role_members:
            raise ValueError(
                f"{context}.expected_exported_body_names contains ferrite family bodies that do not match {role} "
                f"(mismatched={mismatched_role_members})"
            )
        ferrite_group_members = [
            name
            for name in expected_names
            if (len(member_prefixes) > 0 and name.startswith(member_prefixes))
            or (len(member_names) > 0 and name in member_names)
        ]
        if len(ferrite_group_members) == 0:
            return []
        return [(ferrite_group_name, ferrite_group_members)]

    if role == "tx_single_coil":
        return _single_coil_group_contract(
            member_prefixes=_TX_SINGLE_COIL_FERRITE_GROUP_MEMBER_PREFIXES,
            member_names=(),
            ferrite_group_name=_TX_FERRITE_GROUP_NAME,
        )
    if role == "rx_single_coil":
        return _single_coil_group_contract(
            member_prefixes=_RX_SINGLE_COIL_FERRITE_GROUP_MEMBER_PREFIXES,
            member_names=(),
            ferrite_group_name=_RX_FERRITE_GROUP_NAME,
        )

    if role == "tx_plate_stack":
        ferrite_member_names = _TX_PLATE_STACK_FERRITE_GROUP_MEMBER_NAMES
        ferrite_group_name = _TX_FERRITE_GROUP_NAME
        copper_group_name = _TX_COPPER_GROUP_NAME
        required_plate_copper_name = _TX_PLATE_COPPER_NAME
    elif role == "rx_plate_stack":
        ferrite_member_names = _RX_PLATE_STACK_FERRITE_GROUP_MEMBER_NAMES
        ferrite_group_name = _RX_FERRITE_GROUP_NAME
        copper_group_name = _RX_COPPER_GROUP_NAME
        required_plate_copper_name = _RX_PLATE_COPPER_NAME
    else:
        raise ValueError(f"{context}.role is unsupported for ferrite group validation (actual={role!r})")

    if required_plate_copper_name not in expected_names:
        raise ValueError(
            f"{context}.expected_exported_body_names must include {required_plate_copper_name!r} for {role}"
        )
    legacy_segment_names = [name for name in expected_names if _is_legacy_plate_stack_copper_segment_name(name)]
    if legacy_segment_names:
        raise ValueError(
            f"{context}.expected_exported_body_names contains legacy plate-stack copper segment names "
            f"(legacy_names={legacy_segment_names})"
        )
    mismatched_plate_copper_names = [
        name
        for name in expected_names
        if name in (_TX_PLATE_COPPER_NAME, _RX_PLATE_COPPER_NAME) and name != required_plate_copper_name
    ]
    if mismatched_plate_copper_names:
        raise ValueError(
            f"{context}.expected_exported_body_names contains mismatched plate copper names for {role} "
            f"(mismatched={mismatched_plate_copper_names})"
        )
    mismatched_role_members = [
        name
        for name in expected_names
        if _is_any_ferrite_group_name(name)
        and name not in ferrite_member_names
    ]
    if mismatched_role_members:
        raise ValueError(
            f"{context}.expected_exported_body_names contains ferrite family bodies that do not match {role} "
            f"(mismatched={mismatched_role_members})"
        )
    ferrite_group_members = [
        name
        for name in expected_names
        if name in ferrite_member_names
    ]
    return [
        (copper_group_name, [required_plate_copper_name]),
        (ferrite_group_name, ferrite_group_members),
    ]


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
            _TX_PLATE_COPPER_NAME,
            _RX_PLATE_COPPER_NAME,
            _TX_COPPER_WALL_NAME,
            _TX_COPPER_COIL_NAME,
            _RX_COPPER_WALL_NAME,
            _RX_COPPER_COIL_NAME,
        ):
        return _BODY_ROLE_COPPER
    if _is_ferrite_family_name(expected_name):
        return _BODY_ROLE_UNDERLAY_FERRITE
    if _is_pet_psa_family_name(expected_name):
        return _BODY_ROLE_UNDERLAY_PET_PSA
    if _is_air_family_name(expected_name):
        return _BODY_ROLE_UNDERLAY_AIR
    raise ValueError(
        "unsupported exported body name; expected tx_pcb_l*/tx_copper_l*/tx_copper_stack/"
        "tx_copper_wall/tx_pcb_wall/tx_plate_copper/tx_stack_ferrite/tx_stack_pet_psa/"
        "tx_stack_air/tx_pcb_coil/tx_copper_coil "
        "tx_underlay_ferrite_u*/tx_underlay_pet_psa_u*/tx_underlay_air_u* "
        "tx_wall_ferrite_u*/tx_wall_pet_psa_u*/tx_wall_air_u* "
        "or rx_pcb_l*/rx_copper_l*/rx_copper_stack/"
        "rx_copper_wall/rx_pcb_wall/rx_plate_copper/rx_stack_ferrite/rx_stack_pet_psa/"
        "rx_stack_air/rx_pcb_coil/rx_copper_coil "
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
        or name in (
            "tx_copper_stack",
            "rx_copper_stack",
            _TX_PLATE_COPPER_NAME,
            _RX_PLATE_COPPER_NAME,
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
    generic_solid_names = [name for name in imported_object_names if _is_generic_solid_name(name)]
    if missing_required_names:
        if generic_solid_names:
            raise ValueError(
                f"{role_label} type2 import detected generic SOLID* object names; this is an export-contract violation "
                "(ferrite-family bodies must be STEP-exported with exact merged names, not CAD-default names) "
                f"(missing={missing_required_names}, generic_solid_names={generic_solid_names}, expected={expected_names})"
            )
        raise ValueError(
            f"{role_label} type2 import is missing required modeled body names after scene import "
            f"(missing={missing_required_names}, expected={expected_names}, actual={imported_object_names})"
        )
    unexpected_names = [name for name in imported_object_names if name not in expected_names]
    if unexpected_names:
        unexpected_solid_names = [name for name in unexpected_names if _is_generic_solid_name(name)]
        if unexpected_solid_names:
            raise ValueError(
                f"{role_label} type2 import produced unexpected generic SOLID* object names; this is an export-contract violation "
                "(import never repairs ferrite-family naming drift) "
                f"(unexpected_solid_names={unexpected_solid_names}, expected={expected_names})"
            )
        raise ValueError(
            f"{role_label} type2 import requires exact exported body labels after scene import "
            f"(unexpected={unexpected_names}, expected={expected_names})"
        )


def _require_plate_stack_merged_ferrite_name_contract(*, role: str, expected_names: list[str], context: str) -> None:
    required_merged_names: tuple[str, str, str]
    if role == "tx_plate_stack":
        required_merged_names = (
            _TX_STACK_PET_PSA_NAME,
            _TX_STACK_FERRITE_NAME,
            _TX_STACK_AIR_NAME,
        )
    elif role == "rx_plate_stack":
        required_merged_names = (
            _RX_STACK_PET_PSA_NAME,
            _RX_STACK_FERRITE_NAME,
            _RX_STACK_AIR_NAME,
        )
    else:
        raise ValueError(f"{context}.role is unsupported for plate-stack merged ferrite contract (actual={role!r})")
    expected_name_set = set(expected_names)
    missing_required_names = [name for name in required_merged_names if name not in expected_name_set]
    if missing_required_names:
        raise ValueError(
            f"{context}.expected_exported_body_names must include merged plate-stack ferrite-family exact names "
            f"(missing={missing_required_names}, required={list(required_merged_names)}, actual={expected_names})"
        )
    disallowed_ferrite_family_names = [
        name
        for name in expected_names
        if (_is_ferrite_family_name(name) or _is_pet_psa_family_name(name) or _is_air_family_name(name))
        and name not in required_merged_names
    ]
    if disallowed_ferrite_family_names:
        raise ValueError(
            f"{context}.expected_exported_body_names contains non-merged ferrite-family names for {role}; "
            "this is an export-contract violation "
            f"(disallowed={disallowed_ferrite_family_names}, required={list(required_merged_names)})"
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
        _require_plate_stack_merged_ferrite_name_contract(role=role, expected_names=expected_names, context=context)
        if expected_roles.count(_BODY_ROLE_COPPER) != 1:
            raise ValueError(
                "plate-stack type2 import requires exactly one merged plate copper body "
                f"(actual={expected_names})"
            )
        if (
            expected_roles.count(_BODY_ROLE_UNDERLAY_FERRITE) != 1
            or expected_roles.count(_BODY_ROLE_UNDERLAY_PET_PSA) != 1
            or expected_roles.count(_BODY_ROLE_UNDERLAY_AIR) != 1
        ):
            raise ValueError(
                "plate-stack type2 import requires merged ferrite-family exact names "
                "(exactly one ferrite, one PET_PSA, and one air body) "
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
    underlay_ferrite_names = [name for name in imported_object_names if _is_ferrite_family_name(name)]
    underlay_pet_psa_names = [name for name in imported_object_names if _is_pet_psa_family_name(name)]
    underlay_air_names = [name for name in imported_object_names if _is_air_family_name(name)]
    if role in _SINGLE_COIL_ROLES:
        if len(pcb_names) < 1 or len(copper_names) != 1:
            raise ValueError(
                "single-coil type2 import requires one or more PCB bodies and exactly one copper body after exact-name matching "
                f"(actual={imported_object_names})"
            )
    else:
        legacy_segment_names = [name for name in imported_object_names if _is_legacy_plate_stack_copper_segment_name(name)]
        if legacy_segment_names:
            raise ValueError(
                "plate-stack type2 import rejects legacy copper segment labels as final imported conductors "
                f"(legacy_names={legacy_segment_names})"
            )
        if role == "tx_plate_stack":
            required_copper_name = _TX_PLATE_COPPER_NAME
        else:
            required_copper_name = _RX_PLATE_COPPER_NAME
        if required_copper_name not in copper_names:
            raise ValueError(
                "plate-stack type2 import requires merged plate copper name after exact-name matching "
                f"(required={required_copper_name!r}, actual={copper_names})"
            )
        if len(copper_names) != 1:
            raise ValueError(
                "plate-stack type2 import requires exactly one merged plate copper body after exact-name matching "
                f"(actual={copper_names})"
            )
        if len(underlay_ferrite_names) != 1 or len(underlay_pet_psa_names) != 1 or len(underlay_air_names) != 1:
            raise ValueError(
                "plate-stack type2 import requires merged ferrite-family exact names after exact-name matching "
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
                imported_solid_names = [name for name in imported_object_names if _is_generic_solid_name(name)]
                if imported_solid_names:
                    raise ValueError(
                        "scene STEP import is missing required modeled body name "
                        f"(object_id={validated_entry['object_id']}, body_name={expected_name}); "
                        "detected generic SOLID* modeled names, which is an export-contract violation "
                        "(modeled bodies must arrive with exact exported labels) "
                        f"(generic_solid_names={imported_solid_names})"
                    )
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
        unclaimed_solid_names = [name for name in unclaimed_names if _is_generic_solid_name(name)]
        if unclaimed_solid_names:
            raise ValueError(
                "scene STEP import produced generic SOLID* names that do not map to ledger ownership; "
                "this is an export-contract violation "
                f"(generic_solid_names={unclaimed_solid_names})"
            )
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

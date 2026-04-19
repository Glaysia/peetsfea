from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict, cast

from peetsfea.aedt.protocols import DesignSession, HfssSession, MeshModuleSession
from peetsfea.backend.pyaedt.failfast import raise_on_false
from peetsfea.backend.pyaedt.type2_step_import_ledger import (
    require_key,
    require_non_empty_str,
    validated_object_names,
)

MESH_MODULE_NAME = "MeshSetup"
MESH_LENGTH_OPERATION_NAME = "Length1"
_TX_ROLE = "tx_single_coil"
_RX_ROLE = "rx_single_coil"
_TX_PLATE_STACK_ROLE = "tx_plate_stack"
_RX_PLATE_STACK_ROLE = "rx_plate_stack"
_COIL_ROLE_PAIR: frozenset[str] = frozenset({_TX_ROLE, _RX_ROLE})
_PLATE_STACK_ROLE_PAIR: frozenset[str] = frozenset({_TX_PLATE_STACK_ROLE, _RX_PLATE_STACK_ROLE})
_MIXED_TX_PLATE_STACK_RX_SINGLE_ROLE_PAIR: frozenset[str] = frozenset({_TX_PLATE_STACK_ROLE, _RX_ROLE})
_ALL_SUPPORTED_MESH_ROLES: frozenset[str] = frozenset({*_COIL_ROLE_PAIR, *_PLATE_STACK_ROLE_PAIR})
_TX_MESH_OBJECT_CANDIDATES = ("tx_copper_l0", "tx_copper_stack")
_RX_MESH_OBJECT_NAME = "rx_copper_l0"
_TX_PLATE_MESH_OBJECT_NAME = "tx_plate_copper"
_RX_PLATE_MESH_OBJECT_NAME = "rx_plate_copper"
MESH_LENGTH_MAX_ELEMENTS = "1000"
MESH_LENGTH_MAX_LENGTH = "5mm"


def _is_tx_branch_plate_copper_name(name: str) -> bool:
    if not name.startswith("tx_b") or not name.endswith("_plate_copper"):
        return False
    middle = name[len("tx_b") : -len("_plate_copper")]
    return middle.isdigit()


def _is_tx_array_connector_sheet_name(name: str) -> bool:
    for prefix in ("tx_array_input_sheet_s", "tx_array_output_sheet_s"):
        if not name.startswith(prefix):
            continue
        suffix = name[len(prefix):]
        return suffix.isdigit()
    return False


def _is_tx_plate_stack_mesh_object_name(name: str) -> bool:
    return name == _TX_PLATE_MESH_OBJECT_NAME


class Type2ImportedMeshSummary(TypedDict):
    module_name: str
    operation: str
    operation_name: str
    objects: list[str]
    refine_inside: bool
    enabled: bool
    restrict_elem: bool
    num_max_elem: str
    restrict_length: bool
    max_length: str


def _mesh_assignment_payload(*, object_names: list[str]) -> list[object]:
    return [
        f"NAME:{MESH_LENGTH_OPERATION_NAME}",
        "RefineInside:=",
        False,
        "Enabled:=",
        True,
        "Objects:=",
        object_names,
        "RestrictElem:=",
        False,
        "NumMaxElem:=",
        MESH_LENGTH_MAX_ELEMENTS,
        "RestrictLength:=",
        True,
        "MaxLength:=",
        MESH_LENGTH_MAX_LENGTH,
    ]


def _mesh_summary(*, object_names: list[str]) -> Type2ImportedMeshSummary:
    return {
        "module_name": MESH_MODULE_NAME,
        "operation": "AssignLengthOp",
        "operation_name": MESH_LENGTH_OPERATION_NAME,
        "objects": list(object_names),
        "refine_inside": False,
        "enabled": True,
        "restrict_elem": False,
        "num_max_elem": MESH_LENGTH_MAX_ELEMENTS,
        "restrict_length": True,
        "max_length": MESH_LENGTH_MAX_LENGTH,
    }


def _mesh_setup_module(hfss: HfssSession) -> MeshModuleSession:
    assert (_ := hfss.odesign)
    assert isinstance(_, DesignSession)
    design: DesignSession = _
    raw_mesh_module = raise_on_false(
        design.GetModule(MESH_MODULE_NAME),
        operation="GetModule",
        context={"module_name": MESH_MODULE_NAME},
    )
    assert hasattr(raw_mesh_module, "AssignLengthOp"), (
        f"{MESH_MODULE_NAME} module must expose AssignLengthOp "
        f"(module_type={type(raw_mesh_module).__name__})"
    )
    mesh_module = cast(MeshModuleSession, raw_mesh_module)
    assign_length_op = mesh_module.AssignLengthOp
    assert callable(assign_length_op), (
        f"{MESH_MODULE_NAME}.AssignLengthOp must be callable "
        f"(module_type={type(raw_mesh_module).__name__})"
    )
    return mesh_module


def _imported_object_names(entry: dict[str, object], *, context: str) -> list[str]:
    raw_imported_names = require_key(
        entry,
        key="imported_object_names",
        context=context,
    )
    if isinstance(raw_imported_names, (str, bytes)) or not isinstance(raw_imported_names, Sequence):
        raise TypeError(f"{context}.imported_object_names must be a sequence of strings")
    return validated_object_names(
        cast(Sequence[object], raw_imported_names),
        context=f"{context}.imported_object_names",
    )


def _required_tx_mesh_object_name(entry: dict[str, object], *, context: str) -> str:
    imported_object_names = _imported_object_names(entry, context=context)
    tx_matches = [name for name in imported_object_names if name in _TX_MESH_OBJECT_CANDIDATES]
    if len(tx_matches) != 1:
        raise ValueError(
            "Post-import mesh assignment requires tx_single_coil exact imported object name "
            f"from {_TX_MESH_OBJECT_CANDIDATES} "
            f"(actual={tx_matches}, available={imported_object_names})"
        )
    return tx_matches[0]


def _required_rx_mesh_object_name(entry: dict[str, object], *, context: str) -> str:
    imported_object_names = _imported_object_names(entry, context=context)
    rx_matches = [name for name in imported_object_names if name == _RX_MESH_OBJECT_NAME]
    if len(rx_matches) != 1:
        raise ValueError(
            "Post-import mesh assignment requires rx_single_coil exact imported object name "
            f"{_RX_MESH_OBJECT_NAME!r} "
            f"(actual={rx_matches}, available={imported_object_names})"
        )
    return rx_matches[0]


def _required_supported_mesh_role(entry: dict[str, object], *, context: str) -> str:
    role = require_non_empty_str(require_key(entry, key="role", context=context), context=f"{context}.role")
    if role not in _ALL_SUPPORTED_MESH_ROLES:
        raise ValueError(
            f"{context}.role must be one of ['tx_single_coil', 'rx_single_coil', 'tx_plate_stack', 'rx_plate_stack'] "
            f"(actual={role!r})"
        )
    return role


def _role_name_prefix_for_plate_stack(*, role: str, context: str) -> str:
    if role == _TX_PLATE_STACK_ROLE:
        return "tx_"
    if role == _RX_PLATE_STACK_ROLE:
        return "rx_"
    raise ValueError(
        f"{context}.role must be one of ['tx_plate_stack', 'rx_plate_stack'] for plate-stack mesh target resolution "
        f"(actual={role!r})"
    )


def _required_plate_stack_mesh_object_names(entry: dict[str, object], *, role: str, context: str) -> list[str]:
    imported_object_names = _imported_object_names(entry, context=context)
    if role == _TX_PLATE_STACK_ROLE:
        plate_stack_matches = [name for name in imported_object_names if _is_tx_plate_stack_mesh_object_name(name)]
        required_mesh_object_name = _TX_PLATE_MESH_OBJECT_NAME
        if len(plate_stack_matches) != 1:
            raise ValueError(
                f"{context}.imported_object_names must contain exactly one united plate copper body "
                f"{required_mesh_object_name!r} for plate-stack mesh "
                f"(actual={plate_stack_matches}, available={imported_object_names})"
            )
        pre_unite_copper_names = [
            name
            for name in imported_object_names
            if _is_tx_branch_plate_copper_name(name) or _is_tx_array_connector_sheet_name(name)
        ]
        if pre_unite_copper_names:
            raise ValueError(
                f"{context}.imported_object_names contains pre-unite tx copper leakage for mesh "
                f"(leaked_names={pre_unite_copper_names})"
            )
    else:
        required_mesh_object_name = _RX_PLATE_MESH_OBJECT_NAME
        plate_stack_matches = [name for name in imported_object_names if name == required_mesh_object_name]
        if len(plate_stack_matches) != 1:
            raise ValueError(
                f"{context}.imported_object_names must contain exactly one united plate copper body "
                f"{required_mesh_object_name!r} for plate-stack mesh "
                f"(actual={plate_stack_matches}, available={imported_object_names})"
            )
    role_prefix = _role_name_prefix_for_plate_stack(role=role, context=context)
    legacy_segment_names = [
        name
        for name in imported_object_names
        if name.startswith((f"{role_prefix}copper_wall_t", f"{role_prefix}copper_coil_t", f"{role_prefix}bridge_s", f"{role_prefix}stub_"))
    ]
    if legacy_segment_names:
        raise ValueError(
            f"{context}.imported_object_names contains legacy plate-stack copper segment leakage for mesh "
            f"(legacy_names={legacy_segment_names})"
        )
    solid_drift_names = [name for name in imported_object_names if name.casefold().startswith("solid")]
    if solid_drift_names:
        raise ValueError(
            f"{context}.imported_object_names contains generic SOLID* drift for plate-stack mesh "
            f"(solid_names={solid_drift_names})"
        )
    return plate_stack_matches


def _resolve_supported_mesh_entries(
    imported_modeled_objects: Sequence[dict[str, object]],
) -> list[tuple[str, dict[str, object], str]]:
    if len(imported_modeled_objects) == 1:
        context = "modeled_objects[0]"
        single = imported_modeled_objects[0]
        role = _required_supported_mesh_role(single, context=context)
        if role != _RX_ROLE:
            raise ValueError(
                "Post-import mesh assignment accepts one modeled_objects entry only for rx_single_coil in RX-only mode "
                f"(actual={role!r})"
            )
        return [(role, single, context)]
    if len(imported_modeled_objects) != 2:
        raise ValueError(
            "Post-import mesh assignment requires either one modeled_objects entry or an exact tx/rx role pair "
            f"(actual={len(imported_modeled_objects)})"
        )
    entry_by_role: dict[str, dict[str, object]] = {}
    modeled_roles: list[str] = []
    for index, imported_entry in enumerate(imported_modeled_objects):
        role = _required_supported_mesh_role(imported_entry, context=f"imported_modeled_objects[{index}]")
        if role in entry_by_role:
            raise ValueError(
                "Post-import mesh assignment requires an exact tx/rx role pair without duplicates "
                f"(roles={modeled_roles + [role]})"
            )
        entry_by_role[role] = imported_entry
        modeled_roles.append(role)
    role_set = frozenset(modeled_roles)
    if role_set == _COIL_ROLE_PAIR:
        return [
            (_TX_ROLE, entry_by_role[_TX_ROLE], f"modeled_objects[{_TX_ROLE}]"),
            (_RX_ROLE, entry_by_role[_RX_ROLE], f"modeled_objects[{_RX_ROLE}]"),
        ]
    if role_set == _PLATE_STACK_ROLE_PAIR:
        return [
            (_TX_PLATE_STACK_ROLE, entry_by_role[_TX_PLATE_STACK_ROLE], f"modeled_objects[{_TX_PLATE_STACK_ROLE}]"),
            (_RX_PLATE_STACK_ROLE, entry_by_role[_RX_PLATE_STACK_ROLE], f"modeled_objects[{_RX_PLATE_STACK_ROLE}]"),
        ]
    if role_set == _MIXED_TX_PLATE_STACK_RX_SINGLE_ROLE_PAIR:
        return [
            (_TX_PLATE_STACK_ROLE, entry_by_role[_TX_PLATE_STACK_ROLE], f"modeled_objects[{_TX_PLATE_STACK_ROLE}]"),
            (_RX_ROLE, entry_by_role[_RX_ROLE], f"modeled_objects[{_RX_ROLE}]"),
        ]
    raise ValueError(
        "Post-import mesh assignment requires one exact supported tx/rx role pair: "
        "['tx_single_coil', 'rx_single_coil'] or ['tx_plate_stack', 'rx_plate_stack'] "
        "or ['tx_plate_stack', 'rx_single_coil'] "
        f"(roles={modeled_roles})"
    )


def _required_mesh_object_names(imported_modeled_objects: Sequence[dict[str, object]]) -> list[str]:
    resolved = _resolve_supported_mesh_entries(imported_modeled_objects)
    if len(resolved) == 1:
        role, rx_entry, rx_context = resolved[0]
        assert role == _RX_ROLE, f"single-model mesh input must be rx_single_coil, got {role!r}"
        return [_required_rx_mesh_object_name(rx_entry, context=rx_context)]
    tx_entry: dict[str, object] = {}
    rx_entry: dict[str, object] = {}
    tx_context = ""
    rx_context = ""
    tx_found = False
    rx_found = False
    for role, entry, context in resolved:
        if role in (_TX_ROLE, _TX_PLATE_STACK_ROLE):
            tx_entry = entry
            tx_context = context
            tx_found = True
        elif role in (_RX_ROLE, _RX_PLATE_STACK_ROLE):
            rx_entry = entry
            rx_context = context
            rx_found = True
    if not tx_found:
        raise ValueError(f"mesh resolution missing tx entry from {resolved}")
    if not rx_found:
        raise ValueError(f"mesh resolution missing rx entry from {resolved}")
    tx_role = _required_supported_mesh_role(tx_entry, context=tx_context)
    rx_role = _required_supported_mesh_role(rx_entry, context=rx_context)
    if tx_role == _TX_ROLE and rx_role == _RX_ROLE:
        return [
            _required_tx_mesh_object_name(tx_entry, context=tx_context),
            _required_rx_mesh_object_name(rx_entry, context=rx_context),
        ]
    if tx_role == _TX_PLATE_STACK_ROLE and rx_role == _RX_ROLE:
        return [
            *_required_plate_stack_mesh_object_names(tx_entry, role=tx_role, context=tx_context),
            _required_rx_mesh_object_name(rx_entry, context=rx_context),
        ]
    if tx_role == _TX_PLATE_STACK_ROLE and rx_role == _RX_PLATE_STACK_ROLE:
        return [
            *_required_plate_stack_mesh_object_names(tx_entry, role=tx_role, context=tx_context),
            *_required_plate_stack_mesh_object_names(rx_entry, role=rx_role, context=rx_context),
        ]
    raise ValueError(
        "Post-import mesh assignment resolved unsupported direct role pair "
        f"(tx_role={tx_role!r}, rx_role={rx_role!r})"
    )


def assign_post_import_mesh(
    *,
    hfss: HfssSession,
    imported_modeled_objects: Sequence[dict[str, object]],
) -> Type2ImportedMeshSummary:
    mesh_object_names = _required_mesh_object_names(imported_modeled_objects)
    mesh_module = _mesh_setup_module(hfss)
    assign_result = mesh_module.AssignLengthOp(_mesh_assignment_payload(object_names=mesh_object_names))
    raise_on_false(
        assign_result,
        operation="AssignLengthOp",
        context={
            "module_name": MESH_MODULE_NAME,
            "operation_name": MESH_LENGTH_OPERATION_NAME,
            "objects": mesh_object_names,
            "restrict_elem": False,
            "num_max_elem": MESH_LENGTH_MAX_ELEMENTS,
            "restrict_length": True,
            "max_length": MESH_LENGTH_MAX_LENGTH,
        },
    )
    return _mesh_summary(object_names=mesh_object_names)


__all__ = [
    "Type2ImportedMeshSummary",
    "assign_post_import_mesh",
]

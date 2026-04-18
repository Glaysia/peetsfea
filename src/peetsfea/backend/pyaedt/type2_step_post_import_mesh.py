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
_UNSUPPORTED_DIRECT_MESH_ROLES: frozenset[str] = frozenset({"tx_plate_stack", "rx_plate_stack"})
_TX_MESH_OBJECT_CANDIDATES = ("tx_copper_l0", "tx_copper_stack")
_RX_MESH_OBJECT_NAME = "rx_copper_l0"
MESH_LENGTH_MAX_ELEMENTS = "1000"
MESH_LENGTH_MAX_LENGTH = "5mm"


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


def _required_modeled_entry_for_role(
    imported_modeled_objects: Sequence[dict[str, object]],
    *,
    role: str,
) -> dict[str, object]:
    matches: list[dict[str, object]] = []
    for index, imported_entry in enumerate(imported_modeled_objects):
        context = f"imported_modeled_objects[{index}]"
        entry_role = require_non_empty_str(
            require_key(imported_entry, key="role", context=context),
            context=f"{context}.role",
        )
        if entry_role in _UNSUPPORTED_DIRECT_MESH_ROLES:
            raise ValueError(
                f"{context}.role {entry_role!r} is unsupported in assign_post_import_mesh; "
                "plate-stack roles must stop before direct mesh/port/EM helper execution"
            )
        if entry_role == role:
            matches.append(imported_entry)
    if len(matches) != 1:
        raise ValueError(
            "Post-import mesh assignment requires exactly one modeled entry for each mesh role "
            f"(role={role!r}, actual={len(matches)})"
        )
    return matches[0]


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


def _required_mesh_object_names(imported_modeled_objects: Sequence[dict[str, object]]) -> list[str]:
    tx_entry = _required_modeled_entry_for_role(imported_modeled_objects, role=_TX_ROLE)
    rx_entry = _required_modeled_entry_for_role(imported_modeled_objects, role=_RX_ROLE)
    return [
        _required_tx_mesh_object_name(tx_entry, context=f"modeled_objects[{_TX_ROLE}]"),
        _required_rx_mesh_object_name(rx_entry, context=f"modeled_objects[{_RX_ROLE}]"),
    ]


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

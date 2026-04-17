from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict, cast

from peetsfea.aedt.protocols import DesignSession, HfssSession, MeshModuleSession
from peetsfea.backend.pyaedt.failfast import raise_on_false
from peetsfea.backend.pyaedt.type2_step_import_ledger import require_key, validated_object_names

MESH_MODULE_NAME = "MeshSetup"
MESH_LENGTH_OPERATION_NAME = "Length1"
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
    mesh_module = raise_on_false(
        design.GetModule(MESH_MODULE_NAME),
        operation="GetModule",
        context={"module_name": MESH_MODULE_NAME},
    )
    assert hasattr(mesh_module, "AssignLengthOp"), (
        f"{MESH_MODULE_NAME} module must expose AssignLengthOp "
        f"(module_type={type(mesh_module).__name__})"
    )
    assign_length_op = mesh_module.AssignLengthOp
    assert callable(assign_length_op), (
        f"{MESH_MODULE_NAME}.AssignLengthOp must be callable "
        f"(module_type={type(mesh_module).__name__})"
    )
    return cast(MeshModuleSession, mesh_module)


def _required_mesh_object_names(imported_modeled_objects: Sequence[dict[str, object]]) -> list[str]:
    imported_object_names: list[str] = []
    for index, imported_entry in enumerate(imported_modeled_objects):
        context = f"imported_modeled_objects[{index}]"
        raw_imported_names = require_key(
            imported_entry,
            key="imported_object_names",
            context=context,
        )
        if isinstance(raw_imported_names, (str, bytes)) or not isinstance(raw_imported_names, Sequence):
            raise TypeError(f"{context}.imported_object_names must be a sequence of strings")
        imported_object_names.extend(
            validated_object_names(
                cast(Sequence[object], raw_imported_names),
                context=f"{context}.imported_object_names",
            )
        )

    tx_mesh_object_name = next(
        (candidate_name for candidate_name in _TX_MESH_OBJECT_CANDIDATES if candidate_name in imported_object_names),
        None,
    )
    mesh_object_names: list[str] = []
    missing_object_names: list[str] = []
    if tx_mesh_object_name is None:
        missing_object_names.extend(_TX_MESH_OBJECT_CANDIDATES)
    else:
        mesh_object_names.append(tx_mesh_object_name)
    if _RX_MESH_OBJECT_NAME not in imported_object_names:
        missing_object_names.append(_RX_MESH_OBJECT_NAME)
    else:
        mesh_object_names.append(_RX_MESH_OBJECT_NAME)
    if missing_object_names:
        raise ValueError(
            "Post-import mesh assignment requires exact imported object names "
            f"{[*_TX_MESH_OBJECT_CANDIDATES, _RX_MESH_OBJECT_NAME]}; "
            f"missing={missing_object_names}; available={imported_object_names}"
        )
    return mesh_object_names


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

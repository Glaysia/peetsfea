from __future__ import annotations

from typing import cast

from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput
from peetsfea.backend.pyaedt.type2_step_import_ledger import require_key, require_non_empty_str
from peetsfea.backend.pyaedt.type2_step_import_core import Type2ImportedLedger
from peetsfea.types.manifest import EmPorts, GroupEndpointEntry

_UNSUPPORTED_DIRECT_EM_INPUT_ROLES: frozenset[str] = frozenset({"tx_plate_stack", "rx_plate_stack"})


def _modeled_entry_by_role(imported_ledger: Type2ImportedLedger, *, role: str) -> dict[str, object]:
    matches = [
        entry
        for entry in imported_ledger["modeled_objects"]
        if _required_supported_role_for_direct_em_input(entry, context="modeled_object")
        == role
    ]
    if len(matches) != 1:
        raise ValueError(f"type2 setup-ready requires exactly one modeled object for role {role!r} (actual={len(matches)})")
    return matches[0]


def _imported_object_names(entry: dict[str, object], *, context: str) -> list[str]:
    raw_names = require_key(entry, key="imported_object_names", context=context)
    if isinstance(raw_names, (str, bytes)) or not isinstance(raw_names, list):
        raise TypeError(f"{context}.imported_object_names must be a list of strings")
    names: list[str] = []
    for index, raw_name in enumerate(raw_names):
        names.append(require_non_empty_str(raw_name, context=f"{context}.imported_object_names[{index}]"))
    return names


def _pcb_names(imported_object_names: list[str]) -> list[str]:
    return [name for name in imported_object_names if name.startswith(("tx_pcb_l", "rx_pcb_l"))]


def _copper_names(imported_object_names: list[str]) -> list[str]:
    return [
        name
        for name in imported_object_names
        if name.startswith(("tx_copper_l", "rx_copper_l")) or name in ("tx_copper_stack", "rx_copper_stack")
    ]


def _port_sheet_vertices(entry: dict[str, object], *, context: str) -> tuple[tuple[float, float, float], ...]:
    terminal_metadata = require_key(entry, key="terminal_metadata", context=context)
    assert isinstance(terminal_metadata, dict), f"{context}.terminal_metadata must be a table/object"
    raw_vertices = require_key(terminal_metadata, key="port_sheet_vertices_xyz", context=f"{context}.terminal_metadata")
    if isinstance(raw_vertices, (str, bytes)) or not isinstance(raw_vertices, list):
        raise TypeError(f"{context}.terminal_metadata.port_sheet_vertices_xyz must be a list of world vertices")
    vertices: list[tuple[float, float, float]] = []
    for index, raw_vertex in enumerate(raw_vertices):
        if isinstance(raw_vertex, (str, bytes)) or not isinstance(raw_vertex, list):
            raise TypeError(f"{context}.terminal_metadata.port_sheet_vertices_xyz[{index}] must be a 3-item list")
        if len(raw_vertex) != 3:
            raise ValueError(f"{context}.terminal_metadata.port_sheet_vertices_xyz[{index}] must contain exactly 3 entries")
        vertices.append((float(raw_vertex[0]), float(raw_vertex[1]), float(raw_vertex[2])))
    if len(vertices) != 4:
        raise ValueError(f"{context}.terminal_metadata.port_sheet_vertices_xyz must contain exactly 4 vertices")
    return tuple(vertices)


def _world_point_from_plane(entry: dict[str, object], *, field_name: str, context: str) -> tuple[float, float, float]:
    terminal_metadata = require_key(entry, key="terminal_metadata", context=context)
    assert isinstance(terminal_metadata, dict), f"{context}.terminal_metadata must be a table/object"
    raw_plane_point = require_key(terminal_metadata, key=field_name, context=f"{context}.terminal_metadata")
    if isinstance(raw_plane_point, (str, bytes)) or not isinstance(raw_plane_point, list):
        raise TypeError(f"{context}.terminal_metadata.{field_name} must be a 2-item list")
    if len(raw_plane_point) != 2:
        raise ValueError(f"{context}.terminal_metadata.{field_name} must contain exactly 2 entries")
    point_u = float(raw_plane_point[0])
    point_v = float(raw_plane_point[1])
    plane = require_non_empty_str(require_key(entry, key="plane", context=context), context=f"{context}.plane")
    port_sheet_vertices = _port_sheet_vertices(entry, context=context)
    if plane == "XY":
        return (point_u, point_v, port_sheet_vertices[0][2])
    if plane == "YZ":
        return (port_sheet_vertices[0][0], point_u, point_v)
    raise ValueError(f"{context}.plane must be 'XY' or 'YZ' for type2 setup-ready (actual={plane!r})")


def _endpoint_entry(
    *,
    entry: dict[str, object],
    role: str,
    context: str,
) -> GroupEndpointEntry:
    if role in _UNSUPPORTED_DIRECT_EM_INPUT_ROLES:
        raise ValueError(
            f"{context}.role {role!r} is unsupported in build_type2_em_input; "
            "plate-stack roles must stop before direct mesh/port/EM helper execution"
        )
    terminal_metadata = require_key(entry, key="terminal_metadata", context=context)
    assert isinstance(terminal_metadata, dict), f"{context}.terminal_metadata must be a table/object"
    start_label = require_non_empty_str(
        require_key(terminal_metadata, key="outer_corner", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.outer_corner",
    )
    end_label = require_non_empty_str(
        require_key(terminal_metadata, key="inner_corner", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.inner_corner",
    )
    group_kind = "tx_vertical" if role == "tx_single_coil" else "rx_dd"
    return cast(
        GroupEndpointEntry,
        {
            "group_kind": group_kind,
            "group_instance_index": 0,
            "board_id": require_non_empty_str(
                require_key(entry, key="object_id", context=context),
                context=f"{context}.object_id",
            ),
            "start_xyz": _world_point_from_plane(entry, field_name="start_point_plane_mm", context=context),
            "end_xyz": _world_point_from_plane(entry, field_name="end_point_plane_mm", context=context),
            "start_label": start_label,
            "end_label": end_label,
            "present": True,
        },
    )


def build_type2_em_input(
    *,
    imported_ledger: Type2ImportedLedger,
    ports: EmPorts,
) -> EmPipelineInput:
    tx_entry = _modeled_entry_by_role(imported_ledger, role="tx_single_coil")
    rx_entry = _modeled_entry_by_role(imported_ledger, role="rx_single_coil")
    tx_context = "modeled_objects[tx_single_coil]"
    rx_context = "modeled_objects[rx_single_coil]"
    tx_imported_names = _imported_object_names(tx_entry, context=tx_context)
    rx_imported_names = _imported_object_names(rx_entry, context=rx_context)
    tx_pcb_names = _pcb_names(tx_imported_names)
    tx_copper_names = _copper_names(tx_imported_names)
    rx_pcb_names = _pcb_names(rx_imported_names)
    rx_copper_names = _copper_names(rx_imported_names)
    if len(tx_pcb_names) < 1 or len(tx_copper_names) != 1:
        raise ValueError(f"{tx_context}.imported_object_names must contain one or more PCB names and exactly one copper name")
    if len(rx_pcb_names) < 1 or len(rx_copper_names) != 1:
        raise ValueError(f"{rx_context}.imported_object_names must contain one or more PCB names and exactly one copper name")
    non_model_object_names: list[str] = []
    for index, entry in enumerate(imported_ledger["non_model_objects"]):
        non_model_object_names.extend(_imported_object_names(entry, context=f"non_model_objects[{index}]"))
    object_names = sorted(non_model_object_names + tx_imported_names + rx_imported_names)
    return {
        "ready_objects": {
            "tx_conductors": sorted(tx_copper_names),
            "rx_conductors": sorted(rx_copper_names),
            "ferrite_objects": [],
            "fr4_objects": sorted(tx_pcb_names + rx_pcb_names),
            "scene_bbox_source_objects": sorted(non_model_object_names),
        },
        "endpoints": {
            "tx": [_endpoint_entry(entry=tx_entry, role="tx_single_coil", context=tx_context)],
            "rx": [_endpoint_entry(entry=rx_entry, role="rx_single_coil", context=rx_context)],
        },
        "context": {
            "dd_mirror_plane": "XZ",
            "rx_plane": require_non_empty_str(require_key(rx_entry, key="plane", context=rx_context), context=f"{rx_context}.plane"),
            "tx_vertical_plane": require_non_empty_str(
                require_key(tx_entry, key="plane", context=tx_context),
                context=f"{tx_context}.plane",
            ),
            "source": "type2_step_setup_ready",
            "object_names": object_names,
        },
        "ports": {
            "tx": list(ports["tx"]),
            "rx": list(ports["rx"]),
        },
    }


def _required_supported_role_for_direct_em_input(entry: dict[str, object], *, context: str) -> str:
    role = require_non_empty_str(require_key(entry, key="role", context=context), context=f"{context}.role")
    if role in _UNSUPPORTED_DIRECT_EM_INPUT_ROLES:
        raise ValueError(
            f"{context}.role {role!r} is unsupported in build_type2_em_input; "
            "plate-stack roles must stop before direct mesh/port/EM helper execution"
        )
    return role


__all__ = ["build_type2_em_input"]

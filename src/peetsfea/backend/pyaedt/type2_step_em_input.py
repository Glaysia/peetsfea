from __future__ import annotations

from typing import cast

from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput
from peetsfea.backend.pyaedt.type2_step_import_ledger import require_key, require_non_empty_str
from peetsfea.backend.pyaedt.type2_step_import_core import Type2ImportedLedger
from peetsfea.types.manifest import EmPorts, GroupEndpointEntry

_COIL_ROLE_PAIR: frozenset[str] = frozenset({"tx_single_coil", "rx_single_coil"})
_PLATE_STACK_ROLE_PAIR: frozenset[str] = frozenset({"tx_plate_stack", "rx_plate_stack"})
_ALL_SUPPORTED_ROLES: frozenset[str] = frozenset({*_COIL_ROLE_PAIR, *_PLATE_STACK_ROLE_PAIR})


def _resolve_exact_pair_for_direct_em_input(
    modeled_objects: list[dict[str, object]],
) -> tuple[dict[str, object], dict[str, object], str, str]:
    if len(modeled_objects) != 2:
        raise ValueError(
            "type2 setup-ready EM input requires exactly two modeled_objects entries "
            f"(actual={len(modeled_objects)})"
        )
    entry_by_role: dict[str, dict[str, object]] = {}
    modeled_roles: list[str] = []
    for index, modeled_object in enumerate(modeled_objects):
        role = _required_supported_role_for_direct_em_input(modeled_object, context=f"modeled_objects[{index}]")
        if role in entry_by_role:
            raise ValueError(
                "type2 setup-ready EM input requires an exact tx/rx role pair without duplicates "
                f"(roles={modeled_roles + [role]})"
            )
        entry_by_role[role] = modeled_object
        modeled_roles.append(role)
    role_set = frozenset(modeled_roles)
    if role_set == _COIL_ROLE_PAIR:
        return (
            entry_by_role["tx_single_coil"],
            entry_by_role["rx_single_coil"],
            "modeled_objects[tx_single_coil]",
            "modeled_objects[rx_single_coil]",
        )
    if role_set == _PLATE_STACK_ROLE_PAIR:
        return (
            entry_by_role["tx_plate_stack"],
            entry_by_role["rx_plate_stack"],
            "modeled_objects[tx_plate_stack]",
            "modeled_objects[rx_plate_stack]",
        )
    raise ValueError(
        "type2 setup-ready EM input requires one exact supported tx/rx role pair: "
        "['tx_single_coil', 'rx_single_coil'] or ['tx_plate_stack', 'rx_plate_stack'] "
        f"(roles={modeled_roles})"
    )


def _imported_object_names(entry: dict[str, object], *, context: str) -> list[str]:
    raw_names = require_key(entry, key="imported_object_names", context=context)
    if isinstance(raw_names, (str, bytes)) or not isinstance(raw_names, list):
        raise TypeError(f"{context}.imported_object_names must be a list of strings")
    names: list[str] = []
    for index, raw_name in enumerate(raw_names):
        names.append(require_non_empty_str(raw_name, context=f"{context}.imported_object_names[{index}]"))
    return names


def _pcb_names(imported_object_names: list[str], *, role: str) -> list[str]:
    if role == "tx_single_coil":
        return [name for name in imported_object_names if name.startswith("tx_pcb_l")]
    if role == "rx_single_coil":
        return [name for name in imported_object_names if name.startswith("rx_pcb_l")]
    if role == "tx_plate_stack":
        return [name for name in imported_object_names if name in ("tx_pcb_wall", "tx_pcb_coil")]
    assert role == "rx_plate_stack", f"unsupported role for pcb name resolution (actual={role!r})"
    return [name for name in imported_object_names if name in ("rx_pcb_wall", "rx_pcb_coil")]


def _copper_names(imported_object_names: list[str], *, role: str) -> list[str]:
    if role == "tx_single_coil":
        return [name for name in imported_object_names if name.startswith("tx_copper_l") or name == "tx_copper_stack"]
    if role == "rx_single_coil":
        return [name for name in imported_object_names if name.startswith("rx_copper_l") or name == "rx_copper_stack"]
    if role == "tx_plate_stack":
        return [
            name
            for name in imported_object_names
            if name.startswith(("tx_copper_wall_t", "tx_copper_coil_t", "tx_bridge_s", "tx_stub_"))
            or name in ("tx_copper_wall", "tx_copper_coil", "tx_copper_stack")
        ]
    assert role == "rx_plate_stack", f"unsupported role for copper name resolution (actual={role!r})"
    return [
        name
        for name in imported_object_names
        if name.startswith(("rx_copper_wall_t", "rx_copper_coil_t", "rx_bridge_s", "rx_stub_"))
        or name in ("rx_copper_wall", "rx_copper_coil", "rx_copper_stack")
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
    terminal_metadata = require_key(entry, key="terminal_metadata", context=context)
    assert isinstance(terminal_metadata, dict), f"{context}.terminal_metadata must be a table/object"
    group_kind: str
    start_label: str
    end_label: str
    if role == "tx_single_coil":
        group_kind = "tx_vertical"
        start_label = require_non_empty_str(
            require_key(terminal_metadata, key="outer_corner", context=f"{context}.terminal_metadata"),
            context=f"{context}.terminal_metadata.outer_corner",
        )
        end_label = require_non_empty_str(
            require_key(terminal_metadata, key="inner_corner", context=f"{context}.terminal_metadata"),
            context=f"{context}.terminal_metadata.inner_corner",
        )
    elif role == "rx_single_coil":
        group_kind = "rx_dd"
        start_label = require_non_empty_str(
            require_key(terminal_metadata, key="outer_corner", context=f"{context}.terminal_metadata"),
            context=f"{context}.terminal_metadata.outer_corner",
        )
        end_label = require_non_empty_str(
            require_key(terminal_metadata, key="inner_corner", context=f"{context}.terminal_metadata"),
            context=f"{context}.terminal_metadata.inner_corner",
        )
    elif role == "tx_plate_stack":
        kind = require_non_empty_str(
            require_key(terminal_metadata, key="kind", context=f"{context}.terminal_metadata"),
            context=f"{context}.terminal_metadata.kind",
        )
        if kind != "stub_port":
            raise ValueError(f"{context}.terminal_metadata.kind must be 'stub_port' for tx_plate_stack (actual={kind!r})")
        plane = require_non_empty_str(require_key(entry, key="plane", context=context), context=f"{context}.plane")
        if plane != "YZ":
            raise ValueError(f"{context}.plane must be 'YZ' for tx_plate_stack endpoint conversion (actual={plane!r})")
        group_kind = "tx_plate_stack"
        start_label = "input_stub"
        end_label = "output_stub"
    else:
        assert role == "rx_plate_stack", f"{context}.role must be a supported endpoint role (actual={role!r})"
        kind = require_non_empty_str(
            require_key(terminal_metadata, key="kind", context=f"{context}.terminal_metadata"),
            context=f"{context}.terminal_metadata.kind",
        )
        if kind != "stub_port":
            raise ValueError(f"{context}.terminal_metadata.kind must be 'stub_port' for rx_plate_stack (actual={kind!r})")
        plane = require_non_empty_str(require_key(entry, key="plane", context=context), context=f"{context}.plane")
        if plane != "YZ":
            raise ValueError(f"{context}.plane must be 'YZ' for rx_plate_stack endpoint conversion (actual={plane!r})")
        group_kind = "rx_plate_stack"
        start_label = "input_stub"
        end_label = "output_stub"
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
    tx_entry, rx_entry, tx_context, rx_context = _resolve_exact_pair_for_direct_em_input(imported_ledger["modeled_objects"])
    tx_role = _required_supported_role_for_direct_em_input(tx_entry, context=tx_context)
    rx_role = _required_supported_role_for_direct_em_input(rx_entry, context=rx_context)
    tx_imported_names = _imported_object_names(tx_entry, context=tx_context)
    rx_imported_names = _imported_object_names(rx_entry, context=rx_context)
    tx_pcb_names = _pcb_names(tx_imported_names, role=tx_role)
    tx_copper_names = _copper_names(tx_imported_names, role=tx_role)
    rx_pcb_names = _pcb_names(rx_imported_names, role=rx_role)
    rx_copper_names = _copper_names(rx_imported_names, role=rx_role)
    if tx_role in _COIL_ROLE_PAIR:
        if len(tx_pcb_names) < 1 or len(tx_copper_names) != 1:
            raise ValueError(f"{tx_context}.imported_object_names must contain one or more PCB names and exactly one copper name")
    else:
        if len(tx_pcb_names) != 2 or len(tx_copper_names) < 2:
            raise ValueError(f"{tx_context}.imported_object_names must contain exactly two PCB names and two or more copper names")
    if rx_role in _COIL_ROLE_PAIR:
        if len(rx_pcb_names) < 1 or len(rx_copper_names) != 1:
            raise ValueError(f"{rx_context}.imported_object_names must contain one or more PCB names and exactly one copper name")
    else:
        if len(rx_pcb_names) != 2 or len(rx_copper_names) < 2:
            raise ValueError(f"{rx_context}.imported_object_names must contain exactly two PCB names and two or more copper names")
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
            "tx": [_endpoint_entry(entry=tx_entry, role=tx_role, context=tx_context)],
            "rx": [_endpoint_entry(entry=rx_entry, role=rx_role, context=rx_context)],
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
    if role not in _ALL_SUPPORTED_ROLES:
        raise ValueError(
            f"{context}.role must be one of ['tx_single_coil', 'rx_single_coil', 'tx_plate_stack', 'rx_plate_stack'] "
            f"(actual={role!r})"
        )
    return role


__all__ = ["build_type2_em_input"]

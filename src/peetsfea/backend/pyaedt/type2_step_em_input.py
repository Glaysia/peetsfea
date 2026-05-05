from __future__ import annotations

from typing import cast

from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput
from peetsfea.backend.pyaedt.type2_step_import_ledger import require_key, require_non_empty_str
from peetsfea.backend.pyaedt.type2_step_import_core import Type2ImportedLedger
from peetsfea.types.manifest import EmPorts, GroupEndpointEntry

_RX_SINGLE_COIL_ROLE = "rx_single_coil"
_TX_SINGLE_COIL_ROLE = "tx_single_coil"
_TX_INNER_SINGLE_COIL_ROLE = "tx_inner_single_coil"
_COIL_ROLE_PAIR: frozenset[str] = frozenset({_TX_SINGLE_COIL_ROLE, _RX_SINGLE_COIL_ROLE})
_COIL_TX_INNER_ROLE_PAIR: frozenset[str] = frozenset({_TX_INNER_SINGLE_COIL_ROLE, _RX_SINGLE_COIL_ROLE})
_SINGLE_COIL_TX_ROLES: frozenset[str] = frozenset({_TX_SINGLE_COIL_ROLE, _TX_INNER_SINGLE_COIL_ROLE})
_PLATE_STACK_ROLE_PAIR: frozenset[str] = frozenset({"tx_plate_stack", "rx_plate_stack"})
_MIXED_TX_PLATE_STACK_RX_SINGLE_ROLE_PAIR: frozenset[str] = frozenset(
    {"tx_plate_stack", "rx_single_coil"}
)
_TX_RECT_VOID_COLUMNS_RX_SINGLE_ROLE_PAIR: frozenset[str] = frozenset(
    {"tx_rect_void_columns", "rx_single_coil"}
)
_ALL_SUPPORTED_ROLES: frozenset[str] = frozenset(
    {*_COIL_ROLE_PAIR, _TX_INNER_SINGLE_COIL_ROLE, *_PLATE_STACK_ROLE_PAIR, "tx_rect_void_columns"}
)
_TX_PLATE_COPPER_NAME = "tx_plate_copper"
_RX_PLATE_COPPER_NAME = "rx_plate_copper"
_TX_RECT_VOID_COLUMNS_COPPER_NAME = "tx_rect_void_columns_copper"


def _is_tx_branch_pcb_name(name: str, *, suffix: str) -> bool:
    if not name.startswith("tx_b") or not name.endswith(suffix):
        return False
    middle = name[len("tx_b") : -len(suffix)]
    return middle.isdigit()


def _is_tx_array_connector_sheet_name(name: str) -> bool:
    for prefix in ("tx_array_input_sheet_s", "tx_array_output_sheet_s"):
        if not name.startswith(prefix):
            continue
        suffix = name[len(prefix):]
        return suffix.isdigit()
    return False


def _is_tx_plate_stack_copper_name(name: str) -> bool:
    return name == _TX_PLATE_COPPER_NAME


def _resolve_supported_direct_em_input_entries(
    modeled_objects: list[dict[str, object]],
) -> list[tuple[str, dict[str, object], str]]:
    if len(modeled_objects) == 1:
        context = "modeled_objects[0]"
        single = modeled_objects[0]
        role = _required_supported_role_for_direct_em_input(single, context=context)
        if role != "rx_single_coil":
            raise ValueError(
                "type2 setup-ready EM input accepts one modeled_objects entry only for rx_single_coil "
                f"(actual={role!r})"
            )
        return [("rx", single, context)]
    if len(modeled_objects) != 2:
        raise ValueError(
            "type2 setup-ready EM input requires exactly two modeled_objects entries "
            "for paired mode or one rx_single_coil entry for RX-only mode "
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
        return [
            ("tx", entry_by_role[_TX_SINGLE_COIL_ROLE], f"modeled_objects[{_TX_SINGLE_COIL_ROLE}]"),
            ("rx", entry_by_role[_RX_SINGLE_COIL_ROLE], f"modeled_objects[{_RX_SINGLE_COIL_ROLE}]"),
        ]
    if role_set == _COIL_TX_INNER_ROLE_PAIR:
        return [
            ("tx", entry_by_role[_TX_INNER_SINGLE_COIL_ROLE], f"modeled_objects[{_TX_INNER_SINGLE_COIL_ROLE}]"),
            ("rx", entry_by_role[_RX_SINGLE_COIL_ROLE], f"modeled_objects[{_RX_SINGLE_COIL_ROLE}]"),
        ]
    if role_set == _PLATE_STACK_ROLE_PAIR:
        return [
            ("tx", entry_by_role["tx_plate_stack"], "modeled_objects[tx_plate_stack]"),
            ("rx", entry_by_role["rx_plate_stack"], "modeled_objects[rx_plate_stack]"),
        ]
    if role_set == _MIXED_TX_PLATE_STACK_RX_SINGLE_ROLE_PAIR:
        return [
            ("tx", entry_by_role["tx_plate_stack"], "modeled_objects[tx_plate_stack]"),
            ("rx", entry_by_role["rx_single_coil"], "modeled_objects[rx_single_coil]"),
        ]
    if role_set == _TX_RECT_VOID_COLUMNS_RX_SINGLE_ROLE_PAIR:
        return [
            ("tx", entry_by_role["tx_rect_void_columns"], "modeled_objects[tx_rect_void_columns]"),
            ("rx", entry_by_role["rx_single_coil"], "modeled_objects[rx_single_coil]"),
        ]
    raise ValueError(
        "type2 setup-ready EM input requires one exact supported tx/rx role pair: "
        "['tx_single_coil', 'rx_single_coil'] or ['tx_inner_single_coil', 'rx_single_coil'] "
        "or ['tx_plate_stack', 'rx_plate_stack'] or ['tx_plate_stack', 'rx_single_coil'] "
        "or ['tx_rect_void_columns', 'rx_single_coil'] "
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
    if role == _TX_SINGLE_COIL_ROLE:
        return [name for name in imported_object_names if name.startswith("tx_pcb_l")]
    if role == _RX_SINGLE_COIL_ROLE:
        return [name for name in imported_object_names if name.startswith("rx_pcb_l")]
    if role == _TX_INNER_SINGLE_COIL_ROLE:
        return [name for name in imported_object_names if name.startswith("tx_inner_pcb_l")]
    if role == "tx_plate_stack":
        return [
            name
            for name in imported_object_names
            if name in ("tx_pcb_wall", "tx_pcb_coil")
            or _is_tx_branch_pcb_name(name, suffix="_pcb_wall")
            or _is_tx_branch_pcb_name(name, suffix="_pcb_coil")
        ]
    if role == "tx_rect_void_columns":
        return [name for name in imported_object_names if name.startswith("txrvc_") and "_pcb_l" in name]
    assert role == "rx_plate_stack", f"unsupported role for pcb name resolution (actual={role!r})"
    return [name for name in imported_object_names if name in ("rx_pcb_wall", "rx_pcb_coil")]


def _copper_names(imported_object_names: list[str], *, role: str) -> list[str]:
    if role == _TX_SINGLE_COIL_ROLE:
        return [name for name in imported_object_names if name.startswith("tx_copper_l") or name == "tx_copper_stack"]
    if role == _RX_SINGLE_COIL_ROLE:
        return [name for name in imported_object_names if name.startswith("rx_copper_l") or name == "rx_copper_stack"]
    if role == _TX_INNER_SINGLE_COIL_ROLE:
        return [
            name
            for name in imported_object_names
            if name.startswith("tx_inner_copper_l") or name == "tx_inner_copper_stack"
        ]
    if role == "tx_plate_stack":
        return [name for name in imported_object_names if _is_tx_plate_stack_copper_name(name)]
    if role == "tx_rect_void_columns":
        return [name for name in imported_object_names if name == _TX_RECT_VOID_COLUMNS_COPPER_NAME]
    assert role == "rx_plate_stack", f"unsupported role for copper name resolution (actual={role!r})"
    return [name for name in imported_object_names if name == _RX_PLATE_COPPER_NAME]


def _require_no_plate_stack_legacy_copper_leakage(
    *,
    imported_object_names: list[str],
    role: str,
    context: str,
) -> None:
    if role == "tx_plate_stack":
        role_prefix = "tx_"
    elif role == "rx_plate_stack":
        role_prefix = "rx_"
    else:
        return
    legacy_segment_names = [
        name
        for name in imported_object_names
        if name.startswith((f"{role_prefix}copper_wall_t", f"{role_prefix}copper_coil_t", f"{role_prefix}bridge_s", f"{role_prefix}stub_"))
    ]
    if legacy_segment_names:
        raise ValueError(
            f"{context}.imported_object_names contains legacy plate-stack copper segment leakage "
            f"(legacy_names={legacy_segment_names})"
        )
    if role == "tx_plate_stack":
        pre_unite_copper_names = [
            name
            for name in imported_object_names
            if _is_tx_branch_pcb_name(name, suffix="_plate_copper") or _is_tx_array_connector_sheet_name(name)
        ]
        if pre_unite_copper_names:
            raise ValueError(
                f"{context}.imported_object_names contains pre-unite tx copper leakage "
                f"(leaked_names={pre_unite_copper_names})"
            )
    solid_drift_names = [name for name in imported_object_names if name.casefold().startswith("solid")]
    if solid_drift_names:
        raise ValueError(
            f"{context}.imported_object_names contains generic SOLID* drift "
            f"(solid_names={solid_drift_names})"
        )


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
    if role in (_TX_SINGLE_COIL_ROLE, _TX_INNER_SINGLE_COIL_ROLE):
        group_kind = "tx_vertical"
        start_label = require_non_empty_str(
            require_key(terminal_metadata, key="outer_corner", context=f"{context}.terminal_metadata"),
            context=f"{context}.terminal_metadata.outer_corner",
        )
        end_label = require_non_empty_str(
            require_key(terminal_metadata, key="inner_corner", context=f"{context}.terminal_metadata"),
            context=f"{context}.terminal_metadata.inner_corner",
        )
    elif role == _RX_SINGLE_COIL_ROLE:
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
        if role == "tx_rect_void_columns":
            return _tx_rect_void_columns_endpoint_entry(entry=entry, context=context)
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


def _center_of_vertices(vertices: tuple[tuple[float, float, float], ...]) -> tuple[float, float, float]:
    return (
        sum(vertex[0] for vertex in vertices) / float(len(vertices)),
        sum(vertex[1] for vertex in vertices) / float(len(vertices)),
        sum(vertex[2] for vertex in vertices) / float(len(vertices)),
    )


def _tx_rect_void_columns_tab_face_centers(
    *,
    entry: dict[str, object],
    context: str,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    terminal_metadata = require_key(entry, key="terminal_metadata", context=context)
    assert isinstance(terminal_metadata, dict), f"{context}.terminal_metadata must be a table/object"
    kind = require_non_empty_str(
        require_key(terminal_metadata, key="kind", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.kind",
    )
    if kind not in ("parallel_collector_tabs", "series_collector_tabs"):
        raise ValueError(
            f"{context}.terminal_metadata.kind must be 'parallel_collector_tabs' or 'series_collector_tabs' "
            f"for tx_rect_void_columns endpoint conversion (actual={kind!r})"
        )
    raw_tab_faces = require_key(
        terminal_metadata,
        key="tab_face_vertices_xyz",
        context=f"{context}.terminal_metadata",
    )
    if isinstance(raw_tab_faces, (str, bytes)) or not isinstance(raw_tab_faces, list):
        raise TypeError(f"{context}.terminal_metadata.tab_face_vertices_xyz must be a list")
    centers_by_terminal: dict[str, tuple[float, float, float]] = {}
    for face_index, raw_tab_face in enumerate(raw_tab_faces):
        face_context = f"{context}.terminal_metadata.tab_face_vertices_xyz[{face_index}]"
        if not isinstance(raw_tab_face, dict):
            raise TypeError(f"{face_context} must be a table/object")
        terminal = require_non_empty_str(
            require_key(raw_tab_face, key="terminal", context=face_context),
            context=f"{face_context}.terminal",
        )
        if terminal not in ("start", "end"):
            raise ValueError(f"{face_context}.terminal must be 'start' or 'end' (actual={terminal!r})")
        if terminal in centers_by_terminal:
            raise ValueError(f"{context}.terminal_metadata.tab_face_vertices_xyz contains duplicate terminal {terminal!r}")
        raw_vertices = require_key(raw_tab_face, key="vertices_xyz", context=face_context)
        if isinstance(raw_vertices, (str, bytes)) or not isinstance(raw_vertices, list):
            raise TypeError(f"{face_context}.vertices_xyz must be a list of 3D vertices")
        vertices: list[tuple[float, float, float]] = []
        for vertex_index, raw_vertex in enumerate(raw_vertices):
            if isinstance(raw_vertex, (str, bytes)) or not isinstance(raw_vertex, list):
                raise TypeError(f"{face_context}.vertices_xyz[{vertex_index}] must be a 3-item list")
            if len(raw_vertex) != 3:
                raise ValueError(f"{face_context}.vertices_xyz[{vertex_index}] must contain exactly 3 entries")
            vertices.append((float(raw_vertex[0]), float(raw_vertex[1]), float(raw_vertex[2])))
        if len(vertices) != 4:
            raise ValueError(f"{face_context}.vertices_xyz must contain exactly 4 vertices")
        centers_by_terminal[terminal] = _center_of_vertices(tuple(vertices))
    if set(centers_by_terminal) != {"start", "end"}:
        raise ValueError(
            f"{context}.terminal_metadata.tab_face_vertices_xyz must contain start and end terminals "
            f"(actual={sorted(centers_by_terminal)})"
        )
    return (centers_by_terminal["start"], centers_by_terminal["end"])


def _tx_rect_void_columns_endpoint_entry(
    *,
    entry: dict[str, object],
    context: str,
) -> GroupEndpointEntry:
    start_xyz, end_xyz = _tx_rect_void_columns_tab_face_centers(entry=entry, context=context)
    return cast(
        GroupEndpointEntry,
        {
            "group_kind": "tx_rect_void_columns",
            "group_instance_index": 0,
            "board_id": require_non_empty_str(
                require_key(entry, key="object_id", context=context),
                context=f"{context}.object_id",
            ),
            "start_xyz": start_xyz,
            "end_xyz": end_xyz,
            "start_label": "input_stub",
            "end_label": "output_stub",
            "present": True,
        },
    )


def build_type2_em_input(
    *,
    imported_ledger: Type2ImportedLedger,
    ports: EmPorts,
) -> EmPipelineInput:
    entries = _resolve_supported_direct_em_input_entries(imported_ledger["modeled_objects"])
    if len(entries) == 1:
        _, rx_entry, rx_context = entries[0]
        rx_role = _required_supported_role_for_direct_em_input(rx_entry, context=rx_context)
        rx_imported_names = _imported_object_names(rx_entry, context=rx_context)
        _require_no_plate_stack_legacy_copper_leakage(
            imported_object_names=rx_imported_names,
            role=rx_role,
            context=rx_context,
        )
        rx_pcb_names = _pcb_names(rx_imported_names, role=rx_role)
        rx_copper_names = _copper_names(rx_imported_names, role=rx_role)
        if len(rx_pcb_names) < 1 or len(rx_copper_names) != 1:
            raise ValueError(
                f"{rx_context}.imported_object_names must contain one or more PCB names and exactly one copper name"
            )
        non_model_object_names: list[str] = []
        for index, entry in enumerate(imported_ledger["non_model_objects"]):
            non_model_object_names.extend(_imported_object_names(entry, context=f"non_model_objects[{index}]"))
        object_names = sorted(non_model_object_names + rx_imported_names)
        rx_plane = require_non_empty_str(
            require_key(rx_entry, key="plane", context=rx_context),
            context=f"{rx_context}.plane",
        )
        return {
            "ready_objects": {
                "tx_conductors": [],
                "rx_conductors": sorted(rx_copper_names),
                "ferrite_objects": [],
                "fr4_objects": sorted(rx_pcb_names),
                "scene_bbox_source_objects": sorted(non_model_object_names),
            },
            "endpoints": {
                "tx": [],
                "rx": [_endpoint_entry(entry=rx_entry, role=rx_role, context=rx_context)],
            },
            "context": {
                "dd_mirror_plane": "XZ",
                "rx_plane": rx_plane,
                "tx_vertical_plane": rx_plane,
                "source": "type2_step_setup_ready",
                "object_names": object_names,
            },
            "ports": {
                "tx": list(ports["tx"]),
                "rx": list(ports["rx"]),
            },
        }
    tx_entry: dict[str, object] = {}
    rx_entry: dict[str, object] = {}
    tx_context = ""
    rx_context = ""
    for key, entry, context in entries:
        if key == "tx":
            tx_entry = entry
            tx_context = context
        else:
            rx_entry = entry
            rx_context = context
    tx_role = _required_supported_role_for_direct_em_input(tx_entry, context=tx_context)
    rx_role = _required_supported_role_for_direct_em_input(rx_entry, context=rx_context)
    tx_imported_names = _imported_object_names(tx_entry, context=tx_context)
    rx_imported_names = _imported_object_names(rx_entry, context=rx_context)
    _require_no_plate_stack_legacy_copper_leakage(
        imported_object_names=tx_imported_names,
        role=tx_role,
        context=tx_context,
    )
    _require_no_plate_stack_legacy_copper_leakage(
        imported_object_names=rx_imported_names,
        role=rx_role,
        context=rx_context,
    )
    tx_pcb_names = _pcb_names(tx_imported_names, role=tx_role)
    tx_copper_names = _copper_names(tx_imported_names, role=tx_role)
    rx_pcb_names = _pcb_names(rx_imported_names, role=rx_role)
    rx_copper_names = _copper_names(rx_imported_names, role=rx_role)
    if tx_role in _SINGLE_COIL_TX_ROLES:
        if len(tx_pcb_names) < 1 or len(tx_copper_names) != 1:
            raise ValueError(f"{tx_context}.imported_object_names must contain one or more PCB names and exactly one copper name")
    elif tx_role == "tx_rect_void_columns":
        if len(tx_pcb_names) < 1 or tx_copper_names != [_TX_RECT_VOID_COLUMNS_COPPER_NAME]:
            raise ValueError(
                f"{tx_context}.imported_object_names must contain one or more txrvc PCB names and exact copper "
                f"{_TX_RECT_VOID_COLUMNS_COPPER_NAME!r}"
            )
    else:
        if len(tx_pcb_names) < 2 or len(tx_copper_names) < 1:
            raise ValueError(
                f"{tx_context}.imported_object_names must contain two or more PCB names and one or more plate copper names"
            )
    if rx_role in _COIL_ROLE_PAIR:
        if len(rx_pcb_names) < 1 or len(rx_copper_names) != 1:
            raise ValueError(f"{rx_context}.imported_object_names must contain one or more PCB names and exactly one copper name")
    else:
        if len(rx_pcb_names) != 2 or len(rx_copper_names) != 1:
            raise ValueError(
                f"{rx_context}.imported_object_names must contain exactly two PCB names and exactly one plate copper name"
            )
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
            f"{context}.role must be one of ['tx_single_coil', 'tx_inner_single_coil', 'rx_single_coil', "
            f"'tx_plate_stack', 'rx_plate_stack', 'tx_rect_void_columns'] "
            f"(actual={role!r})"
        )
    return role


__all__ = ["build_type2_em_input"]

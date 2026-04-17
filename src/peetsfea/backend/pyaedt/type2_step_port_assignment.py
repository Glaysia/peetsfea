from __future__ import annotations

from typing import cast

from peetsfea.aedt.proxies import assign_lumped_port, get_boundary_names
from peetsfea.aedt.protocols import HfssSession, ModelerSession
from peetsfea.backend.pyaedt.em_pipeline.steps.excitation_names import (
    normalize_excitation_name,
    normalized_excitation_name_map,
)
from peetsfea.backend.pyaedt.type2_step_import_ledger import require_key, require_non_empty_str
from peetsfea.backend.pyaedt.type2_step_import_core import Type2ImportedLedger
from peetsfea.types.manifest import EmPorts


def _current_excitation_name_map(hfss: HfssSession) -> dict[str, str]:
    return normalized_excitation_name_map(list(hfss.excitation_names))


def _required_numeric_port_name_for_role(*, hfss: HfssSession, role: str) -> str:
    preferred_name = "1" if role == "tx" else "2"
    used_indices: set[int] = set()
    for raw_name in [*get_boundary_names(hfss), *_current_excitation_name_map(hfss)]:
        normalized = normalize_excitation_name(raw_name)
        if not normalized.isdigit():
            continue
        index = int(normalized)
        if index > 0:
            used_indices.add(index)
    preferred_index = int(preferred_name)
    if preferred_index in used_indices:
        raise ValueError(
            f"{role} semantic port requires fixed numeric boundary name {preferred_name} "
            f"(used_indices={sorted(used_indices)})"
        )
    return preferred_name


def _capture_new_excitation_name(
    *,
    hfss: HfssSession,
    before_map: dict[str, str],
    context: str,
    expected_excitation_name: str,
) -> str:
    after_map = _current_excitation_name_map(hfss)
    new_normalized_names = [name for name in after_map if name not in before_map]
    new_names = [after_map[name] for name in new_normalized_names]
    if len(new_names) != 1:
        raise ValueError(f"{context} must create exactly one new excitation (actual={sorted(after_map)}, new={sorted(new_names)})")
    excitation_name = new_names[0]
    if normalize_excitation_name(excitation_name) != expected_excitation_name:
        raise ValueError(
            f"{context} must create expected excitation "
            f"(expected={expected_excitation_name!r}, actual={excitation_name!r})"
        )
    return excitation_name


def _port_sheet_vertices(entry: dict[str, object], *, context: str) -> tuple[tuple[float, float, float], ...]:
    terminal_metadata = require_key(entry, key="terminal_metadata", context=context)
    assert isinstance(terminal_metadata, dict), f"{context}.terminal_metadata must be a table/object"
    raw_vertices = require_key(terminal_metadata, key="port_sheet_vertices_xyz", context=f"{context}.terminal_metadata")
    if isinstance(raw_vertices, (str, bytes)) or not isinstance(raw_vertices, list):
        raise TypeError(f"{context}.terminal_metadata.port_sheet_vertices_xyz must be a list of vertices")
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


def _required_port_sheet_name(entry: dict[str, object], *, context: str) -> str:
    role = require_non_empty_str(require_key(entry, key="role", context=context), context=f"{context}.role")
    raw_imported_names = require_key(entry, key="imported_object_names", context=context)
    if isinstance(raw_imported_names, (str, bytes)) or not isinstance(raw_imported_names, list):
        raise TypeError(f"{context}.imported_object_names must be a list of strings")
    imported_object_names = [
        require_non_empty_str(raw_name, context=f"{context}.imported_object_names[{index}]")
        for index, raw_name in enumerate(raw_imported_names)
    ]
    if role == "tx_single_coil":
        expected_name = "tx_port_sheet"
    elif role == "rx_single_coil":
        expected_name = "rx_port_sheet"
    else:
        raise ValueError(f"{context}.role must be tx_single_coil or rx_single_coil (actual={role!r})")
    if expected_name not in imported_object_names:
        raise ValueError(f"{context}.imported_object_names must contain reconstructed port sheet {expected_name!r}")
    return expected_name


def _edge_matches(
    actual_first: tuple[float, float, float],
    actual_second: tuple[float, float, float],
    expected_first: tuple[float, float, float],
    expected_second: tuple[float, float, float],
    *,
    tol: float = 1e-6,
) -> bool:
    def _close(first: tuple[float, float, float], second: tuple[float, float, float]) -> bool:
        return (
            abs(first[0] - second[0]) <= tol
            and abs(first[1] - second[1]) <= tol
            and abs(first[2] - second[2]) <= tol
        )

    return (_close(actual_first, expected_first) and _close(actual_second, expected_second)) or (
        _close(actual_first, expected_second) and _close(actual_second, expected_first)
    )


def _edge_vertices_xyz(modeler: ModelerSession, *, edge_id: int) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    vertex_ids = modeler.get_edge_vertices(edge_id)
    if len(vertex_ids) != 2:
        raise ValueError(f"edge {edge_id} must expose exactly 2 vertices (actual={vertex_ids})")
    first_raw = modeler.get_vertex_position(int(vertex_ids[0]))
    second_raw = modeler.get_vertex_position(int(vertex_ids[1]))
    if len(first_raw) != 3 or len(second_raw) != 3:
        raise ValueError(f"edge {edge_id} vertex positions must be 3D coordinates")
    return (
        (float(first_raw[0]), float(first_raw[1]), float(first_raw[2])),
        (float(second_raw[0]), float(second_raw[1]), float(second_raw[2])),
    )


def _resolve_sheet_edge_id(
    *,
    modeler: ModelerSession,
    object_name: str,
    expected_first: tuple[float, float, float],
    expected_second: tuple[float, float, float],
    context: str,
) -> int:
    matches: list[int] = []
    for raw_edge_id in modeler.get_object_edges(object_name):
        edge_id = int(raw_edge_id)
        actual_first, actual_second = _edge_vertices_xyz(modeler, edge_id=edge_id)
        if _edge_matches(actual_first, actual_second, expected_first, expected_second):
            matches.append(edge_id)
    if len(matches) != 1:
        raise ValueError(
            f"{context} edge resolution must find exactly one matching sheet edge "
            f"(object_name={object_name}, matches={matches})"
        )
    return matches[0]


def _build_terminal_lumped_port_payload(
    *,
    boundary_name: str,
    signal_edge_id: int,
    reference_edge_id: int,
) -> list[object]:
    return [
        f"NAME:{boundary_name}",
        "Edges:=",
        [signal_edge_id, reference_edge_id],
        "LumpedPortType:=",
        "Terminal",
        "DoDeembed:=",
        False,
        "RenormalizeAllTerminals:=",
        True,
        "ShowReporterFilter:=",
        False,
        "Impedance:=",
        "50ohm",
    ]


def _assign_role_port(
    *,
    hfss: HfssSession,
    modeler: ModelerSession,
    entry: dict[str, object],
    role: str,
    context: str,
) -> str:
    raw_imported_names = require_key(entry, key="imported_object_names", context=context)
    if isinstance(raw_imported_names, (str, bytes)) or not isinstance(raw_imported_names, list):
        raise TypeError(f"{context}.imported_object_names must be a list of strings")
    imported_object_names = [
        require_non_empty_str(raw_name, context=f"{context}.imported_object_names[{index}]")
        for index, raw_name in enumerate(raw_imported_names)
    ]
    copper_names = [
        name
        for name in imported_object_names
        if name.startswith(("tx_copper_l", "rx_copper_l")) or name in ("tx_copper_stack", "rx_copper_stack")
    ]
    if len(copper_names) != 1:
        raise ValueError(f"{context}.imported_object_names must contain exactly one copper body before port assignment")
    sheet_name = _required_port_sheet_name(entry, context=context)
    vertices = _port_sheet_vertices(entry, context=context)
    signal_edge_id = _resolve_sheet_edge_id(
        modeler=modeler,
        object_name=sheet_name,
        expected_first=vertices[3],
        expected_second=vertices[0],
        context=f"{context}.signal",
    )
    reference_edge_id = _resolve_sheet_edge_id(
        modeler=modeler,
        object_name=sheet_name,
        expected_first=vertices[1],
        expected_second=vertices[2],
        context=f"{context}.reference",
    )
    boundary_name = _required_numeric_port_name_for_role(hfss=hfss, role=role)
    expected_excitation_name = f"{boundary_name}_T1"
    before_map = _current_excitation_name_map(hfss)
    assign_lumped_port(
        hfss.oboundary,
        _build_terminal_lumped_port_payload(
            boundary_name=boundary_name,
            signal_edge_id=signal_edge_id,
            reference_edge_id=reference_edge_id,
        ),
        context=context,
    )
    _capture_new_excitation_name(
        hfss=hfss,
        before_map=before_map,
        context=context,
        expected_excitation_name=expected_excitation_name,
    )
    return expected_excitation_name


def assign_type2_lumped_ports(
    *,
    hfss: HfssSession,
    modeler: ModelerSession,
    imported_ledger: Type2ImportedLedger,
) -> EmPorts:
    tx_matches = [
        entry
        for entry in imported_ledger["modeled_objects"]
        if require_non_empty_str(require_key(entry, key="role", context="modeled_object"), context="modeled_object.role")
        == "tx_single_coil"
    ]
    rx_matches = [
        entry
        for entry in imported_ledger["modeled_objects"]
        if require_non_empty_str(require_key(entry, key="role", context="modeled_object"), context="modeled_object.role")
        == "rx_single_coil"
    ]
    if len(tx_matches) != 1 or len(rx_matches) != 1:
        raise ValueError(
            "type2 setup-ready requires exactly one tx_single_coil and one rx_single_coil modeled entry "
            f"(tx={len(tx_matches)}, rx={len(rx_matches)})"
        )
    tx_port = _assign_role_port(
        hfss=hfss,
        modeler=modeler,
        entry=tx_matches[0],
        role="tx",
        context="modeled_objects[tx_single_coil]",
    )
    rx_port = _assign_role_port(
        hfss=hfss,
        modeler=modeler,
        entry=rx_matches[0],
        role="rx",
        context="modeled_objects[rx_single_coil]",
    )
    return {"tx": [tx_port], "rx": [rx_port]}


__all__ = ["assign_type2_lumped_ports"]

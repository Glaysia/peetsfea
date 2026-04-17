from __future__ import annotations

from .build_common import *
from ..tx_stub_faces import edge_points_from_edge_id


def _empty_em_ports() -> EmPorts:
    return cast(EmPorts, {"tx": [], "rx": []})


def _empty_em_port_assignments() -> EmPortAssignments:
    return cast(EmPortAssignments, {"tx": [], "rx": []})


def _normalize_excitation_name(name: str) -> str:
    return str(name).strip().strip("'\"").lstrip("(").rstrip(")")


def _current_excitation_name_map(hfss: Hfss) -> dict[str, str]:
    assert hasattr(hfss, "excitation_names"), "HFSS excitation_names are not available"
    excitation_names = getattr(hfss, "excitation_names")
    assert excitation_names is not None, "HFSS excitation_names are not available"
    raw_names = list(excitation_names)
    normalized_map: dict[str, str] = {}
    for raw_name in raw_names:
        if not isinstance(raw_name, str):
            continue
        normalized_name = _normalize_excitation_name(raw_name)
        if normalized_name:
            normalized_map[normalized_name] = raw_name
    return normalized_map


def _current_boundary_names(hfss: Hfss) -> list[str]:
    assert hasattr(hfss, "oboundary"), "HFSS boundary module is not initialized"
    boundary_module = cast(_BoundaryModule, getattr(hfss, "oboundary"))
    assert boundary_module is not None, "HFSS boundary module is not initialized"
    raw_names = list(boundary_module.GetBoundaries())
    return [str(name) for name in raw_names if isinstance(name, str) and str(name).strip()]


def _required_numeric_port_name_for_role(*, hfss: Hfss, role: Literal["tx", "rx"]) -> str:
    preferred_name = "1" if role == "tx" else "2"
    used_indices: set[int] = set()
    for raw_name in [*_current_boundary_names(hfss), *_current_excitation_name_map(hfss)]:
        match = _NUMERIC_PORT_NAME_PATTERN.fullmatch(_normalize_excitation_name(raw_name))
        if not match:
            continue
        index = int(match.group("index"))
        if index > 0:
            used_indices.add(index)
    preferred_index = int(preferred_name)
    if preferred_index in used_indices:
        raise ValueError(
            f"{role} semantic port requires fixed numeric boundary name {preferred_name} "
            f"(used_indices={sorted(used_indices)})"
        )
    return preferred_name

def _points_close(first: _Point3, second: _Point3, *, tol: float = 1e-6) -> bool:
    return (
        abs(first[0] - second[0]) <= tol
        and abs(first[1] - second[1]) <= tol
        and abs(first[2] - second[2]) <= tol
    )

def _edges_match(target: _Edge2P, candidate: _Edge2P, *, tol: float = 1e-6) -> bool:
    return (_points_close(target[0], candidate[0], tol=tol) and _points_close(target[1], candidate[1], tol=tol)) or (
        _points_close(target[0], candidate[1], tol=tol) and _points_close(target[1], candidate[0], tol=tol)
    )

def _find_matching_edge_id(
    *,
    modeler: Modeler3D,
    object_names: list[str],
    target_edge: _Edge2P,
    context: str,
) -> tuple[str, int]:
    matches: list[tuple[str, int]] = []
    for object_name in object_names:
        for raw_edge_id in list(modeler.get_object_edges(object_name)):
            edge_id = int(raw_edge_id)
            candidate_edge = edge_points_from_edge_id(
                modeler=modeler,
                edge_id=edge_id,
                context=f"{context} candidate edge",
            )
            if _edges_match(target_edge, candidate_edge):
                matches.append((object_name, edge_id))
    if len(matches) != 1:
        raise ValueError(f"{context} edge resolution must find exactly one matching edge (matches={matches})")
    return matches[0]

def _capture_new_excitation_name(
    *,
    hfss: Hfss,
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
    normalized_excitation_name = _normalize_excitation_name(excitation_name)
    if normalized_excitation_name != expected_excitation_name:
        raise ValueError(
            f"{context} must create expected excitation "
            f"(expected={expected_excitation_name!r}, actual={excitation_name!r})"
        )
    return excitation_name

def _edge_midpoint(edge: _Edge2P) -> _Point3:
    return (
        (edge[0][0] + edge[1][0]) / 2.0,
        (edge[0][1] + edge[1][1]) / 2.0,
        (edge[0][2] + edge[1][2]) / 2.0,
    )

def _shift_edge_along_y(edge: _Edge2P, *, delta_y: float) -> _Edge2P:
    return (
        (edge[0][0], edge[0][1] + delta_y, edge[0][2]),
        (edge[1][0], edge[1][1] + delta_y, edge[1][2]),
    )

def _tx_port_edge_sort_key(edge: _Edge2P) -> tuple[float, float, float]:
    midpoint = _edge_midpoint(edge)
    return (-midpoint[1], -midpoint[2], midpoint[0])

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

def _create_terminal_lumped_port_and_capture_assignment(
    *,
    hfss: Hfss,
    modeler: Modeler3D,
    candidate_object_names: list[str],
    signal_edge: _Edge2P,
    reference_edge: _Edge2P,
    role: Literal["tx", "rx"],
    context: str,
) -> EmPortAssignmentEntry:
    signal_object_name, signal_edge_id = _find_matching_edge_id(
        modeler=modeler,
        object_names=candidate_object_names,
        target_edge=signal_edge,
        context=f"{context} signal",
    )
    reference_object_name, reference_edge_id = _find_matching_edge_id(
        modeler=modeler,
        object_names=candidate_object_names,
        target_edge=reference_edge,
        context=f"{context} reference",
    )
    return _create_terminal_lumped_port_and_capture_assignment_from_edge_ids(
        hfss=hfss,
        signal_object_name=signal_object_name,
        signal_edge_id=signal_edge_id,
        reference_object_name=reference_object_name,
        reference_edge_id=reference_edge_id,
        role=role,
        context=context,
    )

def _create_terminal_lumped_port_and_capture_assignment_from_edge_ids(
    *,
    hfss: Hfss,
    signal_object_name: str,
    signal_edge_id: int,
    reference_object_name: str,
    reference_edge_id: int,
    role: Literal["tx", "rx"],
    context: str,
) -> EmPortAssignmentEntry:
    boundary_name = _required_numeric_port_name_for_role(hfss=hfss, role=role)
    expected_excitation_name = f"{boundary_name}_T1"
    before_map = _current_excitation_name_map(hfss)
    assert hasattr(hfss, "oboundary"), "HFSS boundary module is not initialized"
    boundary_module = cast(_BoundaryModule, getattr(hfss, "oboundary"))
    assert boundary_module is not None, "HFSS boundary module is not initialized"
    payload = _build_terminal_lumped_port_payload(
        boundary_name=boundary_name,
        signal_edge_id=signal_edge_id,
        reference_edge_id=reference_edge_id,
    )
    try:
        assign_result = boundary_module.AssignLumpedPort(payload)
        assert assign_result is not False, (
            f"{context} AssignLumpedPort returned False "
            f"(boundary={boundary_name}, signal_edge_id={signal_edge_id}, reference_edge_id={reference_edge_id})"
        )
    except Exception as exc:
        raise
    excitation_name = _capture_new_excitation_name(
        hfss=hfss,
        before_map=before_map,
        context=f"{context} ({role})",
        expected_excitation_name=expected_excitation_name,
    )
    return {
        "boundary_name": boundary_name,
        "excitation_name": excitation_name,
        "signal_object_name": signal_object_name,
        "signal_edge_id": signal_edge_id,
        "reference_object_name": reference_object_name,
        "reference_edge_id": reference_edge_id,
    }


__all__ = [
    '_empty_em_ports',
    '_empty_em_port_assignments',
    '_normalize_excitation_name',
    '_current_excitation_name_map',
    '_current_boundary_names',
    '_required_numeric_port_name_for_role',
    '_points_close',
    '_edges_match',
    '_find_matching_edge_id',
    '_capture_new_excitation_name',
    '_edge_midpoint',
    '_shift_edge_along_y',
    '_tx_port_edge_sort_key',
    '_build_terminal_lumped_port_payload',
    '_create_terminal_lumped_port_and_capture_assignment',
    '_create_terminal_lumped_port_and_capture_assignment_from_edge_ids',
]

from __future__ import annotations

from peetsfea.aedt.failfast import raise_on_false
from peetsfea.aedt.proxies import assign_lumped_port, cover_lines, create_polyline, get_boundary_names
from peetsfea.aedt.protocols import HfssSession, ModelerSession
from peetsfea.backend.pyaedt.em_pipeline.steps.excitation_names import (
    normalize_excitation_name,
    normalized_excitation_name_map,
)
from peetsfea.backend.pyaedt.type2_step_import_ledger import require_key, require_non_empty_str
from peetsfea.backend.pyaedt.type2_step_import_core import Type2ImportedLedger
from peetsfea.types.manifest import EmPorts

_COIL_ROLE_PAIR: frozenset[str] = frozenset({"tx_single_coil", "rx_single_coil"})
_TX_INNER_COIL_ROLE_PAIR: frozenset[str] = frozenset({"tx_inner_single_coil", "rx_single_coil"})
_PLATE_STACK_ROLE_PAIR: frozenset[str] = frozenset({"tx_plate_stack", "rx_plate_stack"})
_MIXED_TX_PLATE_STACK_RX_SINGLE_ROLE_PAIR: frozenset[str] = frozenset(
    {"tx_plate_stack", "rx_single_coil"}
)
_TX_RECT_VOID_COLUMNS_RX_SINGLE_ROLE_PAIR: frozenset[str] = frozenset(
    {"tx_rect_void_columns", "rx_single_coil"}
)
_ALL_SUPPORTED_ROLES: frozenset[str] = frozenset(
    {
        *_COIL_ROLE_PAIR,
        *_TX_INNER_COIL_ROLE_PAIR,
        *_PLATE_STACK_ROLE_PAIR,
        "tx_rect_void_columns",
    }
)
_TX_RECT_VOID_COLUMNS_PORT_SHEET_NAME = "tx_rect_void_columns_port_sheet"
_GEOMETRY_TOLERANCE = 1e-6


def _current_excitation_name_map(hfss: HfssSession) -> dict[str, str]:
    return normalized_excitation_name_map(list(hfss.excitation_names))


def _required_numeric_port_name_for_slot(*, hfss: HfssSession, slot: str) -> str:
    used_indices: set[int] = set()
    for raw_name in [*get_boundary_names(hfss), *_current_excitation_name_map(hfss)]:
        normalized = normalize_excitation_name(raw_name)
        if not normalized.isdigit():
            continue
        index = int(normalized)
        if index > 0:
            used_indices.add(index)
    preferred_index = int(slot)
    if preferred_index in used_indices:
        raise ValueError(
            f"port assignment requires fixed numeric boundary name {slot} "
            f"(used_indices={sorted(used_indices)})"
        )
    return slot


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
    role = require_non_empty_str(require_key(entry, key="role", context=context), context=f"{context}.role")
    if role == "tx_rect_void_columns":
        return _tx_rect_void_columns_port_sheet_vertices(entry, context=context)
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


def _center_of_vertices(vertices: tuple[tuple[float, float, float], ...]) -> tuple[float, float, float]:
    return (
        sum(vertex[0] for vertex in vertices) / float(len(vertices)),
        sum(vertex[1] for vertex in vertices) / float(len(vertices)),
        sum(vertex[2] for vertex in vertices) / float(len(vertices)),
    )


def _tab_face_vertices_by_terminal(
    entry: dict[str, object],
    *,
    context: str,
) -> dict[str, tuple[tuple[float, float, float], ...]]:
    terminal_metadata = require_key(entry, key="terminal_metadata", context=context)
    assert isinstance(terminal_metadata, dict), f"{context}.terminal_metadata must be a table/object"
    kind = require_non_empty_str(
        require_key(terminal_metadata, key="kind", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.kind",
    )
    if kind not in ("parallel_collector_tabs", "series_collector_tabs"):
        raise ValueError(
            f"{context}.terminal_metadata.kind must be 'parallel_collector_tabs' or 'series_collector_tabs' "
            f"for tx_rect_void_columns port assignment (actual={kind!r})"
        )
    raw_tab_faces = require_key(
        terminal_metadata,
        key="tab_face_vertices_xyz",
        context=f"{context}.terminal_metadata",
    )
    if isinstance(raw_tab_faces, (str, bytes)) or not isinstance(raw_tab_faces, list):
        raise TypeError(f"{context}.terminal_metadata.tab_face_vertices_xyz must be a list")
    faces_by_terminal: dict[str, tuple[tuple[float, float, float], ...]] = {}
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
        if terminal in faces_by_terminal:
            raise ValueError(f"{context}.terminal_metadata.tab_face_vertices_xyz contains duplicate terminal {terminal!r}")
        raw_vertices = require_key(raw_tab_face, key="vertices_xyz", context=face_context)
        if isinstance(raw_vertices, (str, bytes)) or not isinstance(raw_vertices, list):
            raise TypeError(f"{face_context}.vertices_xyz must be a list of vertices")
        vertices: list[tuple[float, float, float]] = []
        for vertex_index, raw_vertex in enumerate(raw_vertices):
            if isinstance(raw_vertex, (str, bytes)) or not isinstance(raw_vertex, list):
                raise TypeError(f"{face_context}.vertices_xyz[{vertex_index}] must be a 3-item list")
            if len(raw_vertex) != 3:
                raise ValueError(f"{face_context}.vertices_xyz[{vertex_index}] must contain exactly 3 entries")
            vertices.append((float(raw_vertex[0]), float(raw_vertex[1]), float(raw_vertex[2])))
        if len(vertices) != 4:
            raise ValueError(f"{face_context}.vertices_xyz must contain exactly 4 vertices")
        faces_by_terminal[terminal] = tuple(vertices)
    if set(faces_by_terminal) != {"start", "end"}:
        raise ValueError(
            f"{context}.terminal_metadata.tab_face_vertices_xyz must contain start and end terminals "
            f"(actual={sorted(faces_by_terminal)})"
        )
    return faces_by_terminal


def _edge_vertices_at_axis_extreme(
    vertices: tuple[tuple[float, float, float], ...],
    *,
    axis_index: int,
    use_maximum: bool,
    context: str,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    axis_values = tuple(vertex[axis_index] for vertex in vertices)
    target_value = max(axis_values) if use_maximum else min(axis_values)
    edge_vertices = tuple(vertex for vertex in vertices if abs(vertex[axis_index] - target_value) <= 1e-8)
    if len(edge_vertices) != 2:
        raise ValueError(
            f"{context} must expose exactly one edge at the selected tab-face extreme "
            f"(axis_index={axis_index}, use_maximum={use_maximum}, matches={len(edge_vertices)})"
        )
    sort_axes = tuple(index for index in (0, 1, 2) if index != axis_index)
    sorted_vertices = tuple(sorted(edge_vertices, key=lambda vertex: tuple(vertex[index] for index in sort_axes)))
    return (sorted_vertices[0], sorted_vertices[1])


def _tx_rect_void_columns_port_sheet_vertices(
    entry: dict[str, object],
    *,
    context: str,
) -> tuple[tuple[float, float, float], ...]:
    faces_by_terminal = _tab_face_vertices_by_terminal(entry, context=context)
    start_vertices = faces_by_terminal["start"]
    end_vertices = faces_by_terminal["end"]
    start_center = _center_of_vertices(start_vertices)
    end_center = _center_of_vertices(end_vertices)
    center_delta = tuple(end_center[index] - start_center[index] for index in (0, 1, 2))
    axis_index = max((0, 1, 2), key=lambda index: abs(center_delta[index]))
    if abs(center_delta[axis_index]) <= 1e-8:
        raise ValueError(
            f"{context}.terminal_metadata.tab_face_vertices_xyz start/end tab faces must have non-zero separation "
            f"(start_center={start_center}, end_center={end_center})"
        )
    end_is_positive = center_delta[axis_index] > 0.0
    start_edge = _edge_vertices_at_axis_extreme(
        start_vertices,
        axis_index=axis_index,
        use_maximum=end_is_positive,
        context=f"{context}.terminal_metadata.tab_face_vertices_xyz[start]",
    )
    end_edge = _edge_vertices_at_axis_extreme(
        end_vertices,
        axis_index=axis_index,
        use_maximum=not end_is_positive,
        context=f"{context}.terminal_metadata.tab_face_vertices_xyz[end]",
    )
    return (start_edge[0], end_edge[0], end_edge[1], start_edge[1])


def _tx_rect_void_columns_conductor_port_edges(
    entry: dict[str, object],
    *,
    context: str,
) -> tuple[
    tuple[tuple[float, float, float], tuple[float, float, float]],
    tuple[tuple[float, float, float], tuple[float, float, float]],
]:
    faces_by_terminal = _tab_face_vertices_by_terminal(entry, context=context)
    start_vertices = faces_by_terminal["start"]
    end_vertices = faces_by_terminal["end"]
    start_center = _center_of_vertices(start_vertices)
    end_center = _center_of_vertices(end_vertices)
    center_delta = tuple(end_center[index] - start_center[index] for index in (0, 1, 2))
    axis_index = max((0, 1, 2), key=lambda index: abs(center_delta[index]))
    if abs(center_delta[axis_index]) <= 1e-8:
        raise ValueError(
            f"{context}.terminal_metadata.tab_face_vertices_xyz start/end tab faces must have non-zero separation "
            f"(start_center={start_center}, end_center={end_center})"
        )
    end_is_positive = center_delta[axis_index] > 0.0
    signal_edge = _edge_vertices_at_axis_extreme(
        start_vertices,
        axis_index=axis_index,
        use_maximum=not end_is_positive,
        context=f"{context}.terminal_metadata.tab_face_vertices_xyz[start]",
    )
    reference_edge = _edge_vertices_at_axis_extreme(
        end_vertices,
        axis_index=axis_index,
        use_maximum=end_is_positive,
        context=f"{context}.terminal_metadata.tab_face_vertices_xyz[end]",
    )
    return (signal_edge, reference_edge)


def _target_vary_axis(
    target_first: tuple[float, float, float],
    target_second: tuple[float, float, float],
    *,
    context: str,
) -> int:
    deltas = tuple(abs(target_second[index] - target_first[index]) for index in (0, 1, 2))
    axis_index = max((0, 1, 2), key=lambda index: deltas[index])
    if deltas[axis_index] <= _GEOMETRY_TOLERANCE:
        raise ValueError(f"{context} target conductor edge must be non-degenerate (edge={(target_first, target_second)})")
    return axis_index


def _point_lies_on_target_segment(
    point: tuple[float, float, float],
    *,
    target_first: tuple[float, float, float],
    target_second: tuple[float, float, float],
    axis_index: int,
) -> bool:
    for index in (0, 1, 2):
        if index == axis_index:
            continue
        if abs(point[index] - target_first[index]) > _GEOMETRY_TOLERANCE:
            return False
        if abs(target_second[index] - target_first[index]) > _GEOMETRY_TOLERANCE:
            return False
    lower = min(target_first[axis_index], target_second[axis_index]) - _GEOMETRY_TOLERANCE
    upper = max(target_first[axis_index], target_second[axis_index]) + _GEOMETRY_TOLERANCE
    return lower <= point[axis_index] <= upper


def _ordered_edge_vertices_for_target(
    actual_first: tuple[float, float, float],
    actual_second: tuple[float, float, float],
    *,
    target_first: tuple[float, float, float],
    target_second: tuple[float, float, float],
    axis_index: int,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    target_increases = target_second[axis_index] >= target_first[axis_index]
    actual_vertices = (actual_first, actual_second)
    sorted_vertices = tuple(sorted(actual_vertices, key=lambda vertex: vertex[axis_index]))
    if target_increases:
        return (sorted_vertices[0], sorted_vertices[1])
    return (sorted_vertices[1], sorted_vertices[0])


def _ordered_edge_vertices_for_axis(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    *,
    axis_index: int,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    sorted_vertices = tuple(sorted((first, second), key=lambda vertex: vertex[axis_index]))
    return (sorted_vertices[0], sorted_vertices[1])


def _resolve_conductor_sub_edge_id(
    *,
    modeler: ModelerSession,
    object_name: str,
    target_first: tuple[float, float, float],
    target_second: tuple[float, float, float],
    context: str,
) -> tuple[int, tuple[tuple[float, float, float], tuple[float, float, float]]]:
    axis_index = _target_vary_axis(target_first, target_second, context=context)
    candidates: list[tuple[float, int, tuple[tuple[float, float, float], tuple[float, float, float]]]] = []
    for raw_edge_id in modeler.get_object_edges(object_name):
        edge_id = int(raw_edge_id)
        actual_first, actual_second = _edge_vertices_xyz(modeler, edge_id=edge_id)
        first_matches = _point_lies_on_target_segment(
            actual_first,
            target_first=target_first,
            target_second=target_second,
            axis_index=axis_index,
        )
        second_matches = _point_lies_on_target_segment(
            actual_second,
            target_first=target_first,
            target_second=target_second,
            axis_index=axis_index,
        )
        if not first_matches or not second_matches:
            continue
        length = abs(actual_second[axis_index] - actual_first[axis_index])
        if length <= _GEOMETRY_TOLERANCE:
            continue
        ordered_edge = _ordered_edge_vertices_for_target(
            actual_first,
            actual_second,
            target_first=target_first,
            target_second=target_second,
            axis_index=axis_index,
        )
        candidates.append((length, edge_id, ordered_edge))
    if not candidates:
        raise ValueError(
            f"{context} conductor sub-edge resolution found no conductive edge segment "
            f"(object_name={object_name}, target_edge={(target_first, target_second)})"
        )
    longest_length = max(candidate[0] for candidate in candidates)
    longest_candidates = [
        candidate for candidate in candidates if abs(candidate[0] - longest_length) <= _GEOMETRY_TOLERANCE
    ]
    if len(longest_candidates) != 1:
        raise ValueError(
            f"{context} conductor sub-edge resolution must select exactly one longest edge "
            f"(object_name={object_name}, target_edge={(target_first, target_second)}, "
            f"candidate_edge_ids={[candidate[1] for candidate in longest_candidates]})"
        )
    _length, edge_id, ordered_edge = longest_candidates[0]
    return (edge_id, ordered_edge)


def _distance_point_to_segment(
    point: tuple[float, float, float],
    segment_first: tuple[float, float, float],
    segment_second: tuple[float, float, float],
) -> float:
    segment_vector = tuple(segment_second[index] - segment_first[index] for index in (0, 1, 2))
    point_vector = tuple(point[index] - segment_first[index] for index in (0, 1, 2))
    length_squared = sum(component * component for component in segment_vector)
    if length_squared <= _GEOMETRY_TOLERANCE * _GEOMETRY_TOLERANCE:
        raise ValueError(f"candidate conductor edge must be non-degenerate (edge={(segment_first, segment_second)})")
    parameter = sum(point_vector[index] * segment_vector[index] for index in (0, 1, 2)) / length_squared
    clamped = min(1.0, max(0.0, parameter))
    closest = tuple(segment_first[index] + (clamped * segment_vector[index]) for index in (0, 1, 2))
    return sum((point[index] - closest[index]) ** 2 for index in (0, 1, 2)) ** 0.5


def _face_span(
    vertices: tuple[tuple[float, float, float], ...],
) -> float:
    spans = tuple(max(vertex[index] for vertex in vertices) - min(vertex[index] for vertex in vertices) for index in (0, 1, 2))
    return sum(span * span for span in spans) ** 0.5


def _candidate_conductor_edges_near_face(
    *,
    modeler: ModelerSession,
    object_name: str,
    face_vertices: tuple[tuple[float, float, float], ...],
    context: str,
) -> list[tuple[int, float, float, int, tuple[tuple[float, float, float], tuple[float, float, float]]]]:
    face_center = _center_of_vertices(face_vertices)
    face_span = _face_span(face_vertices)
    max_distance = max(2.0, face_span * 3.0)
    max_length = max(2.0, face_span * 3.0)
    candidates: list[tuple[int, float, float, int, tuple[tuple[float, float, float], tuple[float, float, float]]]] = []
    for raw_edge_id in modeler.get_object_edges(object_name):
        edge_id = int(raw_edge_id)
        first, second = _edge_vertices_xyz(modeler, edge_id=edge_id)
        axis_index = _target_vary_axis(first, second, context=f"{context}.candidate[{edge_id}]")
        length = abs(second[axis_index] - first[axis_index])
        if length <= _GEOMETRY_TOLERANCE:
            continue
        if length > max_length:
            continue
        distance = _distance_point_to_segment(face_center, first, second)
        if distance > max_distance:
            continue
        ordered_edge = _ordered_edge_vertices_for_axis(first, second, axis_index=axis_index)
        candidates.append((axis_index, distance, length, edge_id, ordered_edge))
    if not candidates:
        raise ValueError(
            f"{context} found no conductive edge candidates near terminal tab face "
            f"(object_name={object_name}, face_center={face_center}, max_distance={max_distance})"
        )
    return candidates


def _resolve_conductor_edge_pair_near_tab_faces(
    *,
    modeler: ModelerSession,
    object_name: str,
    signal_face_vertices: tuple[tuple[float, float, float], ...],
    reference_face_vertices: tuple[tuple[float, float, float], ...],
    context: str,
) -> tuple[
    tuple[int, tuple[tuple[float, float, float], tuple[float, float, float]]],
    tuple[int, tuple[tuple[float, float, float], tuple[float, float, float]]],
]:
    signal_candidates = _candidate_conductor_edges_near_face(
        modeler=modeler,
        object_name=object_name,
        face_vertices=signal_face_vertices,
        context=f"{context}.signal",
    )
    reference_candidates = _candidate_conductor_edges_near_face(
        modeler=modeler,
        object_name=object_name,
        face_vertices=reference_face_vertices,
        context=f"{context}.reference",
    )
    pair_candidates: list[
        tuple[
            float,
            float,
            float,
            int,
            int,
            tuple[tuple[float, float, float], tuple[float, float, float]],
            tuple[tuple[float, float, float], tuple[float, float, float]],
        ]
    ] = []
    for signal_axis, signal_distance, signal_length, signal_edge_id, signal_edge in signal_candidates:
        for reference_axis, reference_distance, reference_length, reference_edge_id, reference_edge in reference_candidates:
            if signal_axis != reference_axis:
                continue
            perpendicular_span = sum(
                (
                    ((signal_edge[0][index] + signal_edge[1][index]) / 2.0)
                    - ((reference_edge[0][index] + reference_edge[1][index]) / 2.0)
                )
                ** 2
                for index in (0, 1, 2)
                if index != signal_axis
            ) ** 0.5
            if perpendicular_span <= _GEOMETRY_TOLERANCE:
                continue
            pair_candidates.append(
                (
                    max(signal_distance, reference_distance),
                    signal_distance + reference_distance,
                    -min(signal_length, reference_length),
                    signal_edge_id,
                    reference_edge_id,
                    signal_edge,
                    reference_edge,
                )
            )
    if not pair_candidates:
        raise ValueError(f"{context} found no same-axis conductive edge pair for TX columns terminal assignment")
    pair_candidates.sort(key=lambda candidate: candidate[:5])
    best = pair_candidates[0]
    tied = [candidate for candidate in pair_candidates if candidate[:3] == best[:3]]
    if len(tied) != 1:
        raise ValueError(
            f"{context} conductive edge-pair selection must be unique "
            f"(candidate_edge_pairs={[(candidate[3], candidate[4]) for candidate in tied]})"
        )
    _max_distance, _distance_sum, _negative_min_length, signal_edge_id, reference_edge_id, signal_edge, reference_edge = best
    return ((signal_edge_id, signal_edge), (reference_edge_id, reference_edge))


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
    elif role == "tx_inner_single_coil":
        expected_name = "tx_inner_port_sheet"
    elif role == "tx_plate_stack":
        expected_name = "tx_plate_port_sheet"
    elif role == "rx_plate_stack":
        expected_name = "rx_plate_port_sheet"
    elif role == "tx_rect_void_columns":
        expected_name = _TX_RECT_VOID_COLUMNS_PORT_SHEET_NAME
    else:
        raise ValueError(
            f"{context}.role must be one of ['tx_single_coil', 'tx_inner_single_coil', 'rx_single_coil', 'tx_plate_stack', 'rx_plate_stack', 'tx_rect_void_columns'] "
            f"(actual={role!r})"
        )
    if expected_name not in imported_object_names:
        raise ValueError(f"{context}.imported_object_names must contain reconstructed port sheet {expected_name!r}")
    return expected_name


def _required_port_conductor_name(entry: dict[str, object], *, context: str) -> str:
    role = require_non_empty_str(require_key(entry, key="role", context=context), context=f"{context}.role")
    raw_imported_names = require_key(entry, key="imported_object_names", context=context)
    if isinstance(raw_imported_names, (str, bytes)) or not isinstance(raw_imported_names, list):
        raise TypeError(f"{context}.imported_object_names must be a list of strings")
    imported_object_names = [
        require_non_empty_str(raw_name, context=f"{context}.imported_object_names[{index}]")
        for index, raw_name in enumerate(raw_imported_names)
    ]
    if role in ("tx_single_coil", "rx_single_coil"):
        copper_names = [
            name
            for name in imported_object_names
            if name.startswith(("tx_copper_l", "rx_copper_l")) or name in ("tx_copper_stack", "rx_copper_stack")
        ]
        if len(copper_names) != 1:
            raise ValueError(f"{context}.imported_object_names must contain exactly one copper body before port assignment")
        return copper_names[0]
    if role == "tx_inner_single_coil":
        copper_names = [
            name
            for name in imported_object_names
            if name.startswith("tx_inner_copper_l") or name in ("tx_inner_copper_stack",)
        ]
        if len(copper_names) != 1:
            raise ValueError(
                f"{context}.imported_object_names must contain exactly one tx_inner conductor body "
                f"(actual={imported_object_names})"
            )
        return copper_names[0]
    if role == "tx_plate_stack":
        expected_name = "tx_plate_copper"
    elif role == "rx_plate_stack":
        expected_name = "rx_plate_copper"
    elif role == "tx_rect_void_columns":
        expected_name = "tx_rect_void_columns_copper"
    else:
        raise ValueError(
            f"{context}.role must be one of ['tx_single_coil', 'tx_inner_single_coil', 'rx_single_coil', 'tx_plate_stack', 'rx_plate_stack', 'tx_rect_void_columns'] "
            f"(actual={role!r})"
        )
    if expected_name not in imported_object_names:
        raise ValueError(f"{context}.imported_object_names must contain port conductor {expected_name!r}")
    return expected_name


def _required_port_edge_object_name(entry: dict[str, object], *, context: str) -> str:
    role = require_non_empty_str(require_key(entry, key="role", context=context), context=f"{context}.role")
    if role == "tx_rect_void_columns":
        return _required_port_conductor_name(entry, context=context)
    return _required_port_sheet_name(entry, context=context)


def _require_no_existing_tx_columns_port_sheet(*, modeler: ModelerSession, context: str) -> None:
    colliding_sheet_names = [
        name
        for name in modeler.object_names
        if name == _TX_RECT_VOID_COLUMNS_PORT_SHEET_NAME or name.startswith(f"{_TX_RECT_VOID_COLUMNS_PORT_SHEET_NAME}_")
    ]
    if colliding_sheet_names:
        raise ValueError(
            f"{context} requires exactly one runtime-owned TX columns port sheet created during port assignment; "
            f"found pre-existing sheet names {colliding_sheet_names}"
        )


def _covered_sheet_name(covered: object, *, fallback_name: str, context: str) -> str:
    if covered is True:
        return fallback_name
    if isinstance(covered, list):
        if not covered:
            return fallback_name
        first = covered[0]
        if isinstance(first, str):
            return first
        assert hasattr(first, "name"), f"{context} cover_lines list result item must expose name"
        raw_name = getattr(first, "name")
        assert isinstance(raw_name, str), f"{context} cover_lines list result item name must be str"
        return raw_name
    if isinstance(covered, str):
        return covered
    assert hasattr(covered, "name"), f"{context} cover_lines result must expose name"
    raw_name = getattr(covered, "name")
    assert isinstance(raw_name, str), f"{context} cover_lines result name must be str"
    return raw_name


def _create_tx_columns_port_sheet_from_edges(
    *,
    modeler: ModelerSession,
    signal_edge: tuple[tuple[float, float, float], tuple[float, float, float]],
    reference_edge: tuple[tuple[float, float, float], tuple[float, float, float]],
    context: str,
) -> str:
    _require_no_existing_tx_columns_port_sheet(modeler=modeler, context=context)
    sheet_name = _TX_RECT_VOID_COLUMNS_PORT_SHEET_NAME
    polyline_created = create_polyline(
        modeler,
        points=[
            [signal_edge[0][0], signal_edge[0][1], signal_edge[0][2]],
            [reference_edge[0][0], reference_edge[0][1], reference_edge[0][2]],
            [reference_edge[1][0], reference_edge[1][1], reference_edge[1][2]],
            [signal_edge[1][0], signal_edge[1][1], signal_edge[1][2]],
        ],
        name=sheet_name,
        material="vacuum",
        close_surface=True,
        cover_surface=False,
    )
    assert hasattr(polyline_created, "name"), f"{context} created TX columns port-sheet loop must expose name"
    raw_loop_name = getattr(polyline_created, "name")
    assert isinstance(raw_loop_name, str), f"{context} created TX columns port-sheet loop name must be str"
    loop_name = require_non_empty_str(raw_loop_name, context=f"{context}.port_sheet.loop_name")
    if loop_name != sheet_name:
        raise ValueError(f"{context} created TX columns port-sheet loop name drifted (expected={sheet_name}, actual={loop_name})")
    covered = cover_lines(modeler, assignment=loop_name)
    covered_name = _covered_sheet_name(covered, fallback_name=loop_name, context=context)
    if covered_name != sheet_name:
        raise ValueError(f"{context} covered TX columns port-sheet name drifted (expected={sheet_name}, actual={covered_name})")
    state_result = modeler.set_object_model_state(sheet_name, True)
    raise_on_false(
        state_result,
        operation="set_object_model_state",
        context={"context": context, "name": sheet_name, "model": True},
    )
    sheet_names = [name for name in modeler.object_names if name == sheet_name or name.startswith(f"{sheet_name}_")]
    if sheet_names != [sheet_name]:
        raise ValueError(f"{context} must leave exactly one TX columns port sheet (actual={sheet_names})")
    return sheet_name


def _append_imported_object_name(entry: dict[str, object], *, object_name: str, context: str) -> None:
    raw_imported_names = require_key(entry, key="imported_object_names", context=context)
    if isinstance(raw_imported_names, (str, bytes)) or not isinstance(raw_imported_names, list):
        raise TypeError(f"{context}.imported_object_names must be a list of strings")
    imported_names = [
        require_non_empty_str(raw_name, context=f"{context}.imported_object_names[{index}]")
        for index, raw_name in enumerate(raw_imported_names)
    ]
    if object_name in imported_names:
        raise ValueError(f"{context}.imported_object_names already contains runtime-created object {object_name!r}")
    raw_imported_names.append(object_name)


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
    slot: str = "1",
    context: str,
) -> str:
    if slot not in ("1", "2"):
        raise ValueError(f"{context}.slot must be '1' or '2' for direct port assignment (actual={slot!r})")
    entry_role = _required_supported_role_for_direct_port_assignment(entry, context=context)
    if role == "tx" and not entry_role.startswith("tx_"):
        raise ValueError(f"{context}.role mismatch for tx port assignment (entry_role={entry_role!r})")
    if role == "rx" and not entry_role.startswith("rx_"):
        raise ValueError(f"{context}.role mismatch for rx port assignment (entry_role={entry_role!r})")
    if entry_role == "tx_rect_void_columns":
        edge_object_name = _required_port_conductor_name(entry, context=context)
        faces_by_terminal = _tab_face_vertices_by_terminal(entry, context=context)
        (signal_edge_id, resolved_signal_edge), (reference_edge_id, resolved_reference_edge) = _resolve_conductor_edge_pair_near_tab_faces(
            modeler=modeler,
            object_name=edge_object_name,
            signal_face_vertices=faces_by_terminal["start"],
            reference_face_vertices=faces_by_terminal["end"],
            context=context,
        )
        port_sheet_name = _create_tx_columns_port_sheet_from_edges(
            modeler=modeler,
            signal_edge=resolved_signal_edge,
            reference_edge=resolved_reference_edge,
            context=context,
        )
        _append_imported_object_name(entry, object_name=port_sheet_name, context=context)
    else:
        edge_object_name = _required_port_edge_object_name(entry, context=context)
        vertices = _port_sheet_vertices(entry, context=context)
        signal_expected_first = vertices[3]
        signal_expected_second = vertices[0]
        reference_expected_first = vertices[1]
        reference_expected_second = vertices[2]
        signal_edge_id = _resolve_sheet_edge_id(
            modeler=modeler,
            object_name=edge_object_name,
            expected_first=signal_expected_first,
            expected_second=signal_expected_second,
            context=f"{context}.signal",
        )
        reference_edge_id = _resolve_sheet_edge_id(
            modeler=modeler,
            object_name=edge_object_name,
            expected_first=reference_expected_first,
            expected_second=reference_expected_second,
            context=f"{context}.reference",
        )
    boundary_name = _required_numeric_port_name_for_slot(hfss=hfss, slot=slot)
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
    assignments = _resolve_supported_direct_port_assignment_entries(imported_ledger["modeled_objects"])
    tx_ports: list[str] = []
    rx_ports: list[str] = []
    is_rx_only = len(assignments) == 1
    for port_key, entry, context in assignments:
        slot = "1" if (is_rx_only and port_key == "rx") or port_key == "tx" else "2"
        assigned_port = _assign_role_port(
            hfss=hfss,
            modeler=modeler,
            entry=entry,
            role=port_key,
            slot=slot,
            context=context,
        )
        if port_key == "tx":
            tx_ports.append(assigned_port)
        else:
            rx_ports.append(assigned_port)
    return {"tx": tx_ports, "rx": rx_ports}


def _resolve_supported_direct_port_assignment_entries(
    modeled_objects: list[dict[str, object]],
) -> list[tuple[str, dict[str, object], str]]:
    if len(modeled_objects) == 1:
        context = "modeled_objects[0]"
        single = modeled_objects[0]
        role = _required_supported_role_for_direct_port_assignment(single, context=context)
        if role != "rx_single_coil":
            raise ValueError(
                "type2 setup-ready direct port assignment accepts one modeled_objects entry only for rx_single_coil "
                f"(actual={role!r})"
            )
        return [("rx", single, context)]
    if len(modeled_objects) != 2:
        raise ValueError(
            "type2 setup-ready direct port assignment requires exactly two modeled_objects entries "
            "for paired mode or one rx_single_coil entry for RX-only mode "
            f"(actual={len(modeled_objects)})"
        )
    entry_by_role: dict[str, dict[str, object]] = {}
    modeled_roles: list[str] = []
    for index, modeled_object in enumerate(modeled_objects):
        role = _required_supported_role_for_direct_port_assignment(modeled_object, context=f"modeled_objects[{index}]")
        if role in entry_by_role:
            raise ValueError(
                "type2 setup-ready direct port assignment requires an exact tx/rx role pair without duplicates "
                f"(roles={modeled_roles + [role]})"
            )
        entry_by_role[role] = modeled_object
        modeled_roles.append(role)
    role_set = frozenset(modeled_roles)
    if role_set == _COIL_ROLE_PAIR:
        return [
            ("tx", entry_by_role["tx_single_coil"], "modeled_objects[tx_single_coil]"),
            ("rx", entry_by_role["rx_single_coil"], "modeled_objects[rx_single_coil]"),
        ]
    if role_set == _TX_INNER_COIL_ROLE_PAIR:
        return [
            ("tx", entry_by_role["tx_inner_single_coil"], "modeled_objects[tx_inner_single_coil]"),
            ("rx", entry_by_role["rx_single_coil"], "modeled_objects[rx_single_coil]"),
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
        "type2 setup-ready direct port assignment requires one exact supported tx/rx role pair: "
        "['tx_single_coil', 'rx_single_coil'] or ['tx_plate_stack', 'rx_plate_stack'] "
        "or ['tx_inner_single_coil', 'rx_single_coil'] "
        "or ['tx_plate_stack', 'rx_single_coil'] or ['tx_rect_void_columns', 'rx_single_coil'] "
        f"(roles={modeled_roles})"
    )


def _required_supported_role_for_direct_port_assignment(entry: dict[str, object], *, context: str) -> str:
    role = require_non_empty_str(require_key(entry, key="role", context=context), context=f"{context}.role")
    if role not in _ALL_SUPPORTED_ROLES:
        raise ValueError(
            f"{context}.role must be one of ['tx_single_coil', 'tx_inner_single_coil', 'rx_single_coil', 'tx_plate_stack', 'rx_plate_stack', 'tx_rect_void_columns'] "
            f"(actual={role!r})"
        )
    return role


__all__ = ["assign_type2_lumped_ports"]

from __future__ import annotations

from typing import Literal, Sequence

from peetsfea.aedt import Modeler3D

from .build_state import Edge2P, Point3, StubFaceEdgeRole, StubFaceKind, StubFaceRef, StubFaceSignature


_FACE_COMPARE_TOL = 1e-6


def _require_point3(values: Sequence[float], *, context: str) -> Point3:
    if len(values) != 3:
        raise ValueError(f"{context} must be 3D (actual_len={len(values)})")
    return (float(values[0]), float(values[1]), float(values[2]))


def _points_close(first: Point3, second: Point3, *, tol: float = _FACE_COMPARE_TOL) -> bool:
    return (
        abs(first[0] - second[0]) <= tol
        and abs(first[1] - second[1]) <= tol
        and abs(first[2] - second[2]) <= tol
    )


def _float_close(first: float, second: float, *, tol: float = _FACE_COMPARE_TOL) -> bool:
    return abs(first - second) <= tol


def _canonical_ordered_vertices(vertices: list[Point3]) -> tuple[Point3, ...]:
    return tuple(sorted(vertices, key=lambda point: (point[0], point[1], point[2])))


def edge_points_from_edge_id(
    *,
    modeler: Modeler3D,
    edge_id: int,
    context: str,
) -> Edge2P:
    vertex_ids = list(modeler.get_edge_vertices(edge_id))
    if len(vertex_ids) != 2:
        raise ValueError(f"{context} requires exactly 2 edge vertices (edge_id={edge_id}, actual={len(vertex_ids)})")
    first = _require_point3(modeler.get_vertex_position(vertex_ids[0]), context=f"{context} first vertex")
    second = _require_point3(modeler.get_vertex_position(vertex_ids[1]), context=f"{context} second vertex")
    return first, second


def _face_vertices_from_face_id(
    *,
    modeler: Modeler3D,
    face_id: int,
    context: str,
) -> tuple[Point3, ...]:
    vertex_ids = list(modeler.get_face_vertices(face_id))
    if len(vertex_ids) < 3:
        raise ValueError(f"{context} requires at least 3 face vertices (face_id={face_id}, actual={len(vertex_ids)})")
    vertices = [
        _require_point3(
            modeler.get_vertex_position(int(vertex_id)),
            context=f"{context} face vertex",
        )
        for vertex_id in vertex_ids
    ]
    return _canonical_ordered_vertices(vertices)


def _axis_levels(values: tuple[float, ...], *, tol: float = _FACE_COMPARE_TOL) -> list[float]:
    levels: list[float] = []
    for value in sorted(float(entry) for entry in values):
        if not levels or abs(levels[-1] - value) > tol:
            levels.append(value)
    return levels


def _validate_face_kind(
    *,
    ordered_vertices: tuple[Point3, ...],
    face_kind: StubFaceKind,
    context: str,
) -> None:
    xs = _axis_levels(tuple(point[0] for point in ordered_vertices))
    ys = _axis_levels(tuple(point[1] for point in ordered_vertices))
    zs = _axis_levels(tuple(point[2] for point in ordered_vertices))
    if face_kind == "tx_dd_xy":
        if len(xs) != 2 or len(ys) != 2 or len(zs) != 1:
            raise ValueError(f"{context} must define an XY rectangle (vertices={ordered_vertices})")
        return
    if len(xs) != 2 or len(ys) != 1 or len(zs) != 2:
        raise ValueError(f"{context} must define an XZ rectangle (vertices={ordered_vertices})")


def _face_signature_from_face_id(
    *,
    modeler: Modeler3D,
    face_id: int,
    face_kind: StubFaceKind,
    context: str,
    validate_kind: bool = True,
) -> StubFaceSignature:
    ordered_vertices = _face_vertices_from_face_id(modeler=modeler, face_id=face_id, context=f"{context} vertices")
    if validate_kind:
        _validate_face_kind(ordered_vertices=ordered_vertices, face_kind=face_kind, context=f"{context} kind")
    face_center = _require_point3(modeler.get_face_center(face_id), context=f"{context} center")
    face_area = float(modeler.get_face_area(face_id))
    if face_area <= 0.0:
        raise ValueError(f"{context} must have positive face area (face_id={face_id}, area={face_area})")
    return {
        "ordered_vertices": ordered_vertices,
        "center": face_center,
        "area": face_area,
        "face_kind": face_kind,
    }


def capture_stub_face_ref_from_object(
    *,
    modeler: Modeler3D,
    object_name: str,
    expected_face_center: Point3,
    face_kind: StubFaceKind,
    stub_role: str,
    context: str,
) -> StubFaceRef:
    matches: list[tuple[int, StubFaceSignature]] = []
    for raw_face_id in list(modeler.get_object_faces(object_name)):
        face_id = int(raw_face_id)
        face_center = _require_point3(modeler.get_face_center(face_id), context=f"{context} face center")
        if not _points_close(face_center, expected_face_center):
            continue
        matches.append(
            (
                face_id,
                _face_signature_from_face_id(
                    modeler=modeler,
                    face_id=face_id,
                    face_kind=face_kind,
                    context=f"{context} face signature",
                    validate_kind=True,
                ),
            )
        )
    if len(matches) != 1:
        raise ValueError(
            f"{context} must resolve exactly one face by center "
            f"(object_name={object_name}, expected_face_center={expected_face_center}, matches={len(matches)})"
        )
    face_id, signature = matches[0]
    return {
        "object_name": object_name,
        "face_id": face_id,
        "face_kind": face_kind,
        "stub_role": stub_role,
        "signature": signature,
    }


def _signatures_match(
    *,
    expected: StubFaceSignature,
    candidate: StubFaceSignature,
) -> bool:
    if expected["face_kind"] != candidate["face_kind"]:
        return False
    if not _points_close(expected["center"], candidate["center"]):
        return False
    if not _float_close(expected["area"], candidate["area"]):
        return False
    expected_vertices = expected["ordered_vertices"]
    candidate_vertices = candidate["ordered_vertices"]
    if len(expected_vertices) != len(candidate_vertices):
        return False
    for expected_point, candidate_point in zip(expected_vertices, candidate_vertices, strict=True):
        if not _points_close(expected_point, candidate_point):
            return False
    return True


def remap_stub_face_ref_after_unite(
    *,
    modeler: Modeler3D,
    united_object_name: str,
    face_ref: StubFaceRef,
    context: str,
) -> StubFaceRef:
    matches: list[tuple[int, StubFaceSignature]] = []
    for raw_face_id in list(modeler.get_object_faces(united_object_name)):
        face_id = int(raw_face_id)
        candidate_signature = _face_signature_from_face_id(
            modeler=modeler,
            face_id=face_id,
            face_kind=face_ref["face_kind"],
            context=f"{context} candidate signature",
            validate_kind=False,
        )
        if _signatures_match(expected=face_ref["signature"], candidate=candidate_signature):
            matches.append((face_id, candidate_signature))
    if len(matches) != 1:
        raise ValueError(
            f"{context} unite remap must resolve exactly one face "
            f"(object_name={united_object_name}, matches={len(matches)})"
        )
    face_id, signature = matches[0]
    return {
        "object_name": united_object_name,
        "face_id": face_id,
        "face_kind": face_ref["face_kind"],
        "stub_role": face_ref["stub_role"],
        "signature": signature,
    }


def _candidate_edges_for_face(
    *,
    modeler: Modeler3D,
    face_ref: StubFaceRef,
    context: str,
) -> list[tuple[int, Edge2P]]:
    edge_ids = [int(raw_edge_id) for raw_edge_id in list(modeler.get_face_edges(face_ref["face_id"]))]
    if not edge_ids:
        raise ValueError(f"{context} requires at least one live face edge (face_ref={face_ref})")
    return [
        (
            edge_id,
            edge_points_from_edge_id(modeler=modeler, edge_id=edge_id, context=f"{context} edge"),
        )
        for edge_id in edge_ids
    ]


def _edge_midpoint(edge: Edge2P) -> Point3:
    return (
        (edge[0][0] + edge[1][0]) / 2.0,
        (edge[0][1] + edge[1][1]) / 2.0,
        (edge[0][2] + edge[1][2]) / 2.0,
    )


def _edge_has_constant_y(edge: Edge2P, *, tol: float = _FACE_COMPARE_TOL) -> bool:
    return abs(edge[0][1] - edge[1][1]) <= tol


def _edge_has_constant_z(edge: Edge2P, *, tol: float = _FACE_COMPARE_TOL) -> bool:
    return abs(edge[0][2] - edge[1][2]) <= tol


def _pick_single_edge_id(
    *,
    candidates: list[tuple[int, Edge2P]],
    compare_value: float,
    compare_axis: Literal["y", "z"],
    context: str,
) -> int:
    matching_edge_ids: list[int] = []
    for edge_id, edge in candidates:
        midpoint = _edge_midpoint(edge)
        midpoint_value = midpoint[1] if compare_axis == "y" else midpoint[2]
        if abs(midpoint_value - compare_value) <= _FACE_COMPARE_TOL:
            matching_edge_ids.append(edge_id)
    if len(matching_edge_ids) != 1:
        raise ValueError(
            f"{context} must resolve exactly one face edge "
            f"(compare_axis={compare_axis}, compare_value={compare_value}, matches={matching_edge_ids})"
        )
    return matching_edge_ids[0]


def edge_id_from_face_id(
    *,
    modeler: Modeler3D,
    face_ref: StubFaceRef,
    edge_role: StubFaceEdgeRole,
    peer_face_ref: StubFaceRef | None = None,
    context: str,
) -> int:
    face_signature = _face_signature_from_face_id(
        modeler=modeler,
        face_id=face_ref["face_id"],
        face_kind=face_ref["face_kind"],
        context=f"{context} live face signature",
        validate_kind=False,
    )
    candidates = _candidate_edges_for_face(modeler=modeler, face_ref=face_ref, context=context)
    if face_ref["face_kind"] == "tx_dd_xy":
        y_candidates = [(edge_id, edge) for edge_id, edge in candidates if _edge_has_constant_y(edge)]
        if edge_role == "tx_port":
            if not y_candidates:
                raise ValueError(f"{context} tx_dd port face requires constant-y edges")
            return _pick_single_edge_id(
                candidates=y_candidates,
                compare_value=max(_edge_midpoint(edge)[1] for _, edge in y_candidates),
                compare_axis="y",
                context=context,
            )
        if edge_role != "tx_dd_bridge":
            raise ValueError(f"{context} tx_dd face does not support edge_role={edge_role}")
        if peer_face_ref is None:
            raise ValueError(f"{context} tx_dd bridge requires peer_face_ref")
        if not y_candidates:
            raise ValueError(f"{context} tx_dd bridge face requires constant-y edges")
        y_levels = _axis_levels(tuple(point[1] for point in face_signature["ordered_vertices"]))
        center_y = face_signature["center"][1]
        peer_center_y = _require_point3(
            modeler.get_face_center(peer_face_ref["face_id"]),
            context=f"{context} peer face center",
        )[1]
        selected_y = y_levels[0] if face_ref["stub_role"] == "out_above" else (y_levels[1] if peer_center_y >= center_y else y_levels[0])
        return _pick_single_edge_id(
            candidates=y_candidates,
            compare_value=selected_y,
            compare_axis="y",
            context=context,
        )
    z_candidates = [(edge_id, edge) for edge_id, edge in candidates if _edge_has_constant_z(edge)]
    if not z_candidates:
        raise ValueError(f"{context} tx_vertical face requires constant-z edges")
    if edge_role == "tx_port":
        return _pick_single_edge_id(
            candidates=z_candidates,
            compare_value=max(_edge_midpoint(edge)[2] for _, edge in z_candidates),
            compare_axis="z",
            context=context,
        )
    if edge_role != "tx_vertical_bridge":
        raise ValueError(f"{context} tx_vertical face does not support edge_role={edge_role}")
    if peer_face_ref is None:
        raise ValueError(f"{context} tx_vertical bridge requires peer_face_ref")
    z_levels = _axis_levels(tuple(point[2] for point in face_signature["ordered_vertices"]))
    center_z = face_signature["center"][2]
    peer_center_z = _require_point3(
        modeler.get_face_center(peer_face_ref["face_id"]),
        context=f"{context} peer face center",
    )[2]
    selected_z = z_levels[1] if face_ref["stub_role"] == "in" else (z_levels[1] if peer_center_z >= center_z else z_levels[0])
    return _pick_single_edge_id(
        candidates=z_candidates,
        compare_value=selected_z,
        compare_axis="z",
        context=context,
    )


__all__ = [
    "capture_stub_face_ref_from_object",
    "edge_id_from_face_id",
    "edge_points_from_edge_id",
    "remap_stub_face_ref_after_unite",
]

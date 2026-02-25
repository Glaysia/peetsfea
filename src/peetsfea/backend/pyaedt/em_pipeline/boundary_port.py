from __future__ import annotations

import math

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput
from peetsfea.types.manifest import EmPolicy


_Point3 = tuple[float, float, float]


def build_boundary(policy: EmPolicy) -> dict[str, str]:
    return {
        "type": "radiation",
        "margin_mm": str(float(policy["radiation_margin_mm"])),
    }


def _point3_from_object(value: object) -> _Point3 | None:
    if isinstance(value, (tuple, list)) and len(value) >= 3:
        x = value[0]
        y = value[1]
        z = value[2]
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and isinstance(z, (int, float)):
            return (float(x), float(y), float(z))

    x_attr = getattr(value, "x", None)
    y_attr = getattr(value, "y", None)
    z_attr = getattr(value, "z", None)
    if isinstance(x_attr, (int, float)) and isinstance(y_attr, (int, float)) and isinstance(z_attr, (int, float)):
        return (float(x_attr), float(y_attr), float(z_attr))

    position = getattr(value, "position", None)
    if isinstance(position, (tuple, list)) and len(position) >= 3:
        px = position[0]
        py = position[1]
        pz = position[2]
        if isinstance(px, (int, float)) and isinstance(py, (int, float)) and isinstance(pz, (int, float)):
            return (float(px), float(py), float(pz))

    return None


def _face_vertices(face: object) -> list[_Point3]:
    raw_vertices = getattr(face, "vertices", None)
    if not isinstance(raw_vertices, list):
        return []
    points: list[_Point3] = []
    for vertex in raw_vertices:
        point = _point3_from_object(vertex)
        if point is not None:
            points.append(point)
    return points


def _face_center_z(face: object) -> float | None:
    center = _point3_from_object(getattr(face, "center", None))
    if center is not None:
        return center[2]
    vertices = _face_vertices(face)
    if not vertices:
        return None
    return sum(vertex[2] for vertex in vertices) / float(len(vertices))


def _pick_two_points_from_face(face: object) -> tuple[_Point3, _Point3]:
    vertices = _face_vertices(face)
    if len(vertices) < 2:
        raise ValueError("Face must provide at least two vertices to build a port sheet")
    best_pair = (vertices[0], vertices[1])
    best_dist2 = -1.0
    for idx in range(len(vertices) - 1):
        for jdx in range(idx + 1, len(vertices)):
            p0 = vertices[idx]
            p1 = vertices[jdx]
            dist2 = ((p0[0] - p1[0]) ** 2.0) + ((p0[1] - p1[1]) ** 2.0) + ((p0[2] - p1[2]) ** 2.0)
            if dist2 > best_dist2:
                best_dist2 = dist2
                best_pair = (p0, p1)
    return best_pair


def _resolve_object_name(obj: object, fallback: str) -> str:
    if isinstance(obj, str) and obj:
        return obj
    obj_name = getattr(obj, "name", None)
    if isinstance(obj_name, str) and obj_name:
        return obj_name
    return fallback


def _lookup_model_object(modeler: Modeler3D, object_name: str) -> object | None:
    resolver = getattr(modeler, "get_object_from_name", None)
    if callable(resolver):
        found = resolver(object_name)
        if found:
            return found

    objects_by_name = getattr(modeler, "objects_by_name", None)
    if isinstance(objects_by_name, dict):
        found = objects_by_name.get(object_name)
        if found:
            return found

    return None


def _tx_dd_candidates(tx_conductors: list[str]) -> list[str]:
    tx_dd_names = sorted(name for name in tx_conductors if "tx_dd" in name)
    if tx_dd_names:
        return tx_dd_names
    return sorted(tx_conductors)


def _bottom_sheet_points_from_tx_dd_faces(modeler: Modeler3D, tx_conductors: list[str]) -> list[list[float]] | None:
    best_pair: tuple[float, tuple[object, object]] | None = None
    for object_name in _tx_dd_candidates(tx_conductors):
        obj = _lookup_model_object(modeler, object_name)
        if obj is None:
            continue
        raw_faces = getattr(obj, "faces", None)
        if not isinstance(raw_faces, list) or len(raw_faces) < 2:
            continue
        face_with_z: list[tuple[float, object]] = []
        for face in raw_faces:
            z_center = _face_center_z(face)
            if z_center is None:
                continue
            face_with_z.append((z_center, face))
        if len(face_with_z) < 2:
            continue
        face_with_z.sort(key=lambda item: item[0])
        z_metric = face_with_z[0][0] + face_with_z[1][0]
        if best_pair is None or z_metric < best_pair[0]:
            best_pair = (z_metric, (face_with_z[0][1], face_with_z[1][1]))

    if best_pair is None:
        return None

    face0, face1 = best_pair[1]
    face0_p0, face0_p1 = _pick_two_points_from_face(face0)
    face1_p0, face1_p1 = _pick_two_points_from_face(face1)
    if math.dist(face0_p0, face1_p0) + math.dist(face0_p1, face1_p1) > math.dist(face0_p0, face1_p1) + math.dist(face0_p1, face1_p0):
        face1_p0, face1_p1 = face1_p1, face1_p0
    return [
        [face0_p0[0], face0_p0[1], face0_p0[2]],
        [face0_p1[0], face0_p1[1], face0_p1[2]],
        [face1_p1[0], face1_p1[1], face1_p1[2]],
        [face1_p0[0], face1_p0[1], face1_p0[2]],
    ]


def _create_port_sheet(modeler: Modeler3D, sheet_points: list[list[float]], sheet_name: str) -> str:
    created = modeler.create_polyline(points=sheet_points, name=sheet_name, close_surface=True)
    if not created:
        raise ValueError(f"tx_dd bottom port sheet creation failed (name={sheet_name})")
    return _resolve_object_name(created, sheet_name)


def _assign_lumped_port(hfss: Hfss, sheet_name: str, port_name: str) -> str:
    lumped_port = getattr(hfss, "lumped_port", None)
    if callable(lumped_port):
        try:
            assigned = lumped_port(assignment=sheet_name, name=port_name)  # type: ignore[misc]
        except TypeError:
            assigned = lumped_port(sheet_name, port_name)  # type: ignore[misc]
        if not assigned:
            raise ValueError(f"tx_dd bottom lumped port assignment failed (sheet={sheet_name}, port={port_name})")
        return _resolve_object_name(assigned, port_name)

    assign_lumped_port = getattr(hfss, "assign_lumped_port", None)
    if callable(assign_lumped_port):
        try:
            assigned = assign_lumped_port(assignment=sheet_name, name=port_name)  # type: ignore[misc]
        except TypeError:
            assigned = assign_lumped_port(sheet_name, port_name)  # type: ignore[misc]
        if not assigned:
            raise ValueError(f"tx_dd bottom lumped port assignment failed (sheet={sheet_name}, port={port_name})")
        return _resolve_object_name(assigned, port_name)

    raise ValueError("HFSS API does not expose lumped port assignment method")


def build_ports(hfss: Hfss, modeler: Modeler3D, em_input: EmPipelineInput) -> dict[str, list[str]]:
    endpoints = em_input["endpoints"]
    tx_ports = [f"tx_port_{idx}" for idx, _ in enumerate(endpoints["tx"])]
    rx_ports = [f"rx_port_{idx}" for idx, _ in enumerate(endpoints["rx"])]
    tx_sheet_points = _bottom_sheet_points_from_tx_dd_faces(modeler, em_input["ready_objects"]["tx_conductors"])
    if tx_sheet_points is not None:
        sheet_name = _create_port_sheet(modeler, tx_sheet_points, "sheet_tx_dd_bottom_port_1")
        lumped_port_name = _assign_lumped_port(hfss, sheet_name, "tx_dd_lumped_port_1")
        tx_ports = [lumped_port_name]
    return {"tx": tx_ports, "rx": rx_ports}

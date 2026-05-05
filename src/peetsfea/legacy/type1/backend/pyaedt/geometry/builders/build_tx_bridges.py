from __future__ import annotations

from .build_common import *
from .build_sheet_ops import _create_thickened_sheet_from_points, _sheet_points_from_edge_pair
from ..build_state import StubFaceRef
from ..tx_stub_faces import edge_id_from_face_id, edge_points_from_edge_id


def _require_stub_face_ref(*, landing: _DirectedLandingSection, context: str) -> StubFaceRef:
    assert "stub_face_ref" in landing, f"{context} requires stub_face_ref"
    return cast(StubFaceRef, landing["stub_face_ref"])


def _face_vertices_from_ref(
    *,
    modeler: Modeler3D,
    face_ref: StubFaceRef,
    context: str,
) -> tuple[_Point3, ...]:
    vertex_ids = list(modeler.get_face_vertices(face_ref["face_id"]))
    if len(vertex_ids) < 3:
        raise ValueError(f"{context} requires at least 3 face vertices (face_ref={face_ref})")
    vertices = [
        cast(
            _Point3,
            tuple(float(value) for value in modeler.get_vertex_position(int(vertex_id))),
        )
        for vertex_id in vertex_ids
    ]
    return tuple(sorted(vertices, key=lambda point: (point[0], point[1], point[2])))


def _axis_levels(values: tuple[float, ...], *, tol: float = 1e-6) -> list[float]:
    levels: list[float] = []
    for value in sorted(float(entry) for entry in values):
        if not levels or abs(levels[-1] - value) > tol:
            levels.append(value)
    return levels


def _bridge_region_bounds_from_points(
    *,
    region_min: _Point3,
    region_max: _Point3,
    bridge_points: list[list[float]],
    thickness_margin_mm: float,
) -> tuple[_Point3, _Point3]:
    if not bridge_points:
        raise ValueError("tx chain bridge requires at least one bridge point")
    if thickness_margin_mm < 0.0:
        raise ValueError(
            "tx chain bridge thickness margin must be >= 0 "
            f"(actual={thickness_margin_mm})"
        )
    xs = [float(point[0]) for point in bridge_points]
    ys = [float(point[1]) for point in bridge_points]
    zs = [float(point[2]) for point in bridge_points]
    return (
        (
            min(region_min[0], min(xs) - thickness_margin_mm),
            min(region_min[1], min(ys) - thickness_margin_mm),
            min(region_min[2], min(zs) - thickness_margin_mm),
        ),
        (
            max(region_max[0], max(xs) + thickness_margin_mm),
            max(region_max[1], max(ys) + thickness_margin_mm),
            max(region_max[2], max(zs) + thickness_margin_mm),
        ),
    )


def _shift_tx_dd_edge_inward_from_face(
    *,
    modeler: Modeler3D,
    edge: _Edge2P,
    face_ref: StubFaceRef,
    cu_thickness: float,
) -> _Edge2P:
    if cu_thickness <= 0.0:
        raise ValueError(f"tx chain bridge cu_thickness must be > 0 (actual={cu_thickness})")
    face_vertices = _face_vertices_from_ref(
        modeler=modeler,
        face_ref=face_ref,
        context="tx_dd bridge face vertices",
    )
    ys = _axis_levels(tuple(point[1] for point in face_vertices))
    zs = _axis_levels(tuple(point[2] for point in face_vertices))
    if len(ys) != 2 or len(zs) != 1:
        raise ValueError(f"tx_dd bridge face must define an XY rectangle (face_ref={face_ref}, vertices={face_vertices})")
    center_y = (ys[0] + ys[1]) / 2.0
    edge_y = (edge[0][1] + edge[1][1]) / 2.0
    delta_y = cu_thickness if edge_y < center_y else -cu_thickness
    delta_z = -cu_thickness if face_ref["stub_role"].endswith("_above") else cu_thickness
    return (
        (edge[0][0], edge[0][1] + delta_y, edge[0][2] + delta_z),
        (edge[1][0], edge[1][1] + delta_y, edge[1][2] + delta_z),
    )


def _shift_tx_vertical_edge_inward_from_face(
    *,
    modeler: Modeler3D,
    edge: _Edge2P,
    face_ref: StubFaceRef,
    cu_thickness: float,
) -> _Edge2P:
    if cu_thickness <= 0.0:
        raise ValueError(f"tx chain bridge cu_thickness must be > 0 (actual={cu_thickness})")
    face_vertices = _face_vertices_from_ref(
        modeler=modeler,
        face_ref=face_ref,
        context="tx_vertical bridge face vertices",
    )
    ys = _axis_levels(tuple(point[1] for point in face_vertices))
    zs = _axis_levels(tuple(point[2] for point in face_vertices))
    if len(ys) != 1 or len(zs) != 2:
        raise ValueError(f"tx_vertical bridge face must define an XZ rectangle (face_ref={face_ref}, vertices={face_vertices})")
    center_z = (zs[0] + zs[1]) / 2.0
    edge_z = (edge[0][2] + edge[1][2]) / 2.0
    delta_y = -cu_thickness if face_ref["stub_role"] == "in" else cu_thickness
    delta_z = cu_thickness if edge_z < center_z else -cu_thickness
    return (
        (edge[0][0], edge[0][1] + delta_y, edge[0][2] + delta_z),
        (edge[1][0], edge[1][1] + delta_y, edge[1][2] + delta_z),
    )


def _resolve_tx_chain_bridge_edges_from_faces(
    *,
    modeler: Modeler3D,
    cu_thickness: float,
    tx_dd_landing: _DirectedLandingSection,
    tx_vertical_landing: _DirectedLandingSection,
) -> tuple[_Edge2P, _Edge2P]:
    tx_dd_face_ref = _require_stub_face_ref(
        landing=tx_dd_landing,
        context="tx chain bridge tx_dd_landing",
    )
    tx_vertical_face_ref = _require_stub_face_ref(
        landing=tx_vertical_landing,
        context="tx chain bridge tx_vertical_landing",
    )
    tx_dd_edge_id = edge_id_from_face_id(
        modeler=modeler,
        face_ref=tx_dd_face_ref,
        edge_role="tx_dd_bridge",
        peer_face_ref=tx_vertical_face_ref,
        context="tx chain bridge tx_dd edge",
    )
    tx_vertical_edge_id = edge_id_from_face_id(
        modeler=modeler,
        face_ref=tx_vertical_face_ref,
        edge_role="tx_vertical_bridge",
        peer_face_ref=tx_dd_face_ref,
        context="tx chain bridge tx_vertical edge",
    )
    return (
        _shift_tx_dd_edge_inward_from_face(
            modeler=modeler,
            edge=edge_points_from_edge_id(
                modeler=modeler,
                edge_id=tx_dd_edge_id,
                context="tx chain bridge tx_dd edge points",
            ),
            face_ref=tx_dd_face_ref,
            cu_thickness=cu_thickness,
        ),
        _shift_tx_vertical_edge_inward_from_face(
            modeler=modeler,
            edge=edge_points_from_edge_id(
                modeler=modeler,
                edge_id=tx_vertical_edge_id,
                context="tx chain bridge tx_vertical edge points",
            ),
            face_ref=tx_vertical_face_ref,
            cu_thickness=cu_thickness,
        ),
    )


def _resolve_tx_dd_direct_bridge_edges_from_faces(
    *,
    modeler: Modeler3D,
    cu_thickness: float,
    first_landing: _DirectedLandingSection,
    second_landing: _DirectedLandingSection,
) -> tuple[_Edge2P, _Edge2P]:
    first_face_ref = _require_stub_face_ref(
        landing=first_landing,
        context="tx dd direct bridge first_landing",
    )
    second_face_ref = _require_stub_face_ref(
        landing=second_landing,
        context="tx dd direct bridge second_landing",
    )
    first_edge_id = edge_id_from_face_id(
        modeler=modeler,
        face_ref=first_face_ref,
        edge_role="tx_dd_bridge",
        peer_face_ref=second_face_ref,
        context="tx dd direct bridge first edge",
    )
    second_edge_id = edge_id_from_face_id(
        modeler=modeler,
        face_ref=second_face_ref,
        edge_role="tx_dd_bridge",
        peer_face_ref=first_face_ref,
        context="tx dd direct bridge second edge",
    )
    return (
        _shift_tx_dd_edge_inward_from_face(
            modeler=modeler,
            edge=edge_points_from_edge_id(
                modeler=modeler,
                edge_id=first_edge_id,
                context="tx dd direct bridge first edge points",
            ),
            face_ref=first_face_ref,
            cu_thickness=cu_thickness,
        ),
        _shift_tx_dd_edge_inward_from_face(
            modeler=modeler,
            edge=edge_points_from_edge_id(
                modeler=modeler,
                edge_id=second_edge_id,
                context="tx dd direct bridge second edge points",
            ),
            face_ref=second_face_ref,
            cu_thickness=cu_thickness,
        ),
    )


def _apply_tx_chain_bridge(
    *,
    modeler: Modeler3D,
    cu_thickness: float,
    tx_dd_landing: _DirectedLandingSection,
    tx_vertical_landing: _DirectedLandingSection,
    group_objects: GroupObjects,
    object_names: list[str],
    cad_probe: list[CadProbe],
    bridge_name: str,
    bridge_error_context: str,
    region_min: _Point3,
    region_max: _Point3,
    placement_violations: list[RegionViolation],
) -> str:
    bridge_thickness = cu_thickness * 1.5
    if tx_dd_landing["terminal_polarity"] == tx_vertical_landing["terminal_polarity"]:
        raise ValueError(
            "tx chain bridge contract violation: cross-sign binding required "
            f"(tx_dd_polarity={tx_dd_landing['terminal_polarity']}, tx_vertical_polarity={tx_vertical_landing['terminal_polarity']})"
        )
    if cu_thickness <= 0.0:
        raise ValueError(f"tx chain bridge cu_thickness must be > 0 (actual={cu_thickness})")
    tx_dd_edge, tx_vertical_edge = _resolve_tx_chain_bridge_edges_from_faces(
        modeler=modeler,
        cu_thickness=cu_thickness,
        tx_dd_landing=tx_dd_landing,
        tx_vertical_landing=tx_vertical_landing,
    )
    bridge_sheet_points = _sheet_points_from_edge_pair(dd_edge=tx_dd_edge, vertical_edge=tx_vertical_edge)
    try:
        bridge_object_name, bridge_object = _create_thickened_sheet_from_points(
            modeler=modeler,
            sheet_points=bridge_sheet_points,
            sheet_name=bridge_name,
            thickness=bridge_thickness,
        )
    except ValueError as exc:
        message = str(exc)
        if message.startswith("Sheet loop creation failed"):
            raise ValueError(f"{bridge_error_context} rectangle loop creation failed (name={bridge_name})") from exc
        if message.startswith("Sheet cover_lines failed"):
            raise ValueError(f"{bridge_error_context} cover_lines failed (name={bridge_name})") from exc
        if message.startswith("Sheet thicken failed"):
            raise ValueError(
                f"{bridge_error_context} thicken failed (name={bridge_name}, thickness={cu_thickness * 1.5})"
            ) from exc
        raise
    object_names.append(bridge_object_name)
    group_objects["tx_dd"].append(bridge_object_name)
    bridge_probe = _probe_cad_object(bridge_object)
    cad_probe.append(bridge_probe)
    effective_region_min, effective_region_max = _bridge_region_bounds_from_points(
        region_min=region_min,
        region_max=region_max,
        bridge_points=bridge_sheet_points,
        thickness_margin_mm=bridge_thickness,
    )
    bridge_violations = _bbox_violations(
        object_name=bridge_object_name,
        bbox=bridge_probe["bbox"],
        region_kind="tx_region_vertical",
        region_min=effective_region_min,
        region_max=effective_region_max,
    )
    if bridge_violations:
        placement_violations.extend(bridge_violations)
        first = bridge_violations[0]
        raise ValueError(
            f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
            f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
        )
    return bridge_object_name


def _apply_tx_dd_direct_bridge(
    *,
    modeler: Modeler3D,
    cu_thickness: float,
    first_landing: _DirectedLandingSection,
    second_landing: _DirectedLandingSection,
    group_objects: GroupObjects,
    object_names: list[str],
    cad_probe: list[CadProbe],
    bridge_name: str,
    bridge_error_context: str,
    region_min: _Point3,
    region_max: _Point3,
    placement_violations: list[RegionViolation],
) -> str:
    bridge_thickness = cu_thickness * 1.5
    if first_landing["terminal_polarity"] == second_landing["terminal_polarity"]:
        raise ValueError(
            "tx dd direct bridge contract violation: cross-sign binding required "
            f"(first_polarity={first_landing['terminal_polarity']}, second_polarity={second_landing['terminal_polarity']})"
        )
    first_edge, second_edge = _resolve_tx_dd_direct_bridge_edges_from_faces(
        modeler=modeler,
        cu_thickness=cu_thickness,
        first_landing=first_landing,
        second_landing=second_landing,
    )
    bridge_sheet_points = _sheet_points_from_edge_pair(dd_edge=first_edge, vertical_edge=second_edge)
    try:
        bridge_object_name, bridge_object = _create_thickened_sheet_from_points(
            modeler=modeler,
            sheet_points=bridge_sheet_points,
            sheet_name=bridge_name,
            thickness=bridge_thickness,
        )
    except ValueError as exc:
        message = str(exc)
        if message.startswith("Sheet loop creation failed"):
            raise ValueError(f"{bridge_error_context} rectangle loop creation failed (name={bridge_name})") from exc
        if message.startswith("Sheet cover_lines failed"):
            raise ValueError(f"{bridge_error_context} cover_lines failed (name={bridge_name})") from exc
        if message.startswith("Sheet thicken failed"):
            raise ValueError(
                f"{bridge_error_context} thicken failed (name={bridge_name}, thickness={cu_thickness * 1.5})"
            ) from exc
        raise
    object_names.append(bridge_object_name)
    group_objects["tx_dd"].append(bridge_object_name)
    bridge_probe = _probe_cad_object(bridge_object)
    cad_probe.append(bridge_probe)
    effective_region_min, effective_region_max = _bridge_region_bounds_from_points(
        region_min=region_min,
        region_max=region_max,
        bridge_points=bridge_sheet_points,
        thickness_margin_mm=bridge_thickness,
    )
    bridge_violations = _bbox_violations(
        object_name=bridge_object_name,
        bbox=bridge_probe["bbox"],
        region_kind="tx_region_vertical",
        region_min=effective_region_min,
        region_max=effective_region_max,
    )
    if bridge_violations:
        placement_violations.extend(bridge_violations)
        first = bridge_violations[0]
        raise ValueError(
            f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
            f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
        )
    return bridge_object_name


__all__ = [
    "_apply_tx_chain_bridge",
    "_apply_tx_dd_direct_bridge",
    "_bridge_region_bounds_from_points",
    "_require_stub_face_ref",
    "_resolve_tx_chain_bridge_edges_from_faces",
    "_resolve_tx_dd_direct_bridge_edges_from_faces",
    "_shift_tx_dd_edge_inward_from_face",
    "_shift_tx_vertical_edge_inward_from_face",
]

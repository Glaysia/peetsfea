from __future__ import annotations

from ..build_state import DirectedLandingSection, Edge2P, Point3, StubFaceRef, state_is_set


def _points_match(a: Point3, b: Point3, *, tol: float = 1e-9) -> bool:
    return (
        abs(a[0] - b[0]) <= tol
        and abs(a[1] - b[1]) <= tol
        and abs(a[2] - b[2]) <= tol
    )


def _attach_bridge_stub_edge_to_landing(
    landing: DirectedLandingSection,
    *,
    source_object_name: str,
    anchor_xyz: Point3,
    edge: Edge2P,
    stub_face_ref: StubFaceRef | None = None,
) -> None:
    if not state_is_set(landing):
        return
    if landing["object_name"] != source_object_name:
        return
    if not _points_match(landing["center"], anchor_xyz):
        return
    landing["bridge_stub_edge"] = edge
    if stub_face_ref is not None:
        landing["stub_face_ref"] = stub_face_ref


def _first_active_name(*names: str) -> str:
    for name in names:
        if state_is_set(name):
            return name
    return ""


def _landing_name(landing: DirectedLandingSection) -> str:
    if state_is_set(landing):
        return landing["object_name"]
    return ""


def _edge_midpoint_x(edge: Edge2P) -> float:
    return (edge[0][0] + edge[1][0]) / 2.0


def _attach_txdd_stub_to_semantic_bridge_landing(
    landing: DirectedLandingSection,
    *,
    source_object_name: str,
    stub_role: str,
    edge: Edge2P,
    stub_face_ref: StubFaceRef,
) -> None:
    if not state_is_set(landing):
        return
    if landing["object_name"] != source_object_name:
        return
    if landing["dd_family"] != "tx_dd":
        return
    if stub_role == "out_above" and landing["terminal_role"] == "inter_half_exit" and landing["side"] == "right":
        landing["bridge_stub_edge"] = edge
        landing["stub_face_ref"] = stub_face_ref
        return
    if stub_role == "in_above" and landing["terminal_role"] == "inter_half_entry" and landing["side"] == "left":
        landing["bridge_stub_edge"] = edge
        landing["stub_face_ref"] = stub_face_ref


def _uses_tx_vertical_external_stub_bridge(landing: DirectedLandingSection) -> bool:
    return state_is_set(landing) and (landing["dd_family"] == "none" or "stub_face_ref" in landing)


def _shift_edge_inward_along_x(
    *,
    edge: Edge2P,
    center_x: float,
    cu_thickness_mm: float,
    tol: float = 1e-9,
) -> Edge2P:
    edge_mid_x = _edge_midpoint_x(edge)
    if abs(edge_mid_x - center_x) <= tol:
        raise ValueError(
            "tx_vertical mode1 inward-X bridge shift contract violation: edge midpoint x equals coil center x "
            f"(edge_mid_x={edge_mid_x}, center_x={center_x}, tol={tol})"
        )
    delta_x = cu_thickness_mm * 2.0 if edge_mid_x < center_x else -cu_thickness_mm * 2.0
    return (
        (edge[0][0] + delta_x, edge[0][1], edge[0][2]),
        (edge[1][0] + delta_x, edge[1][1], edge[1][2]),
    )

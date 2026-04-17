from __future__ import annotations

from typing import Sequence, TypeAlias


Point3: TypeAlias = tuple[float, float, float]
Edge2P: TypeAlias = tuple[Point3, Point3]
RxStubPortBackFaceCorners: TypeAlias = tuple[Point3, Point3, Point3, Point3]

# Importable runtime capture for RX port-stub free-end back faces.
RX_STUB_PORT_BACK_FACE_CORNERS_BY_DESIGN: dict[str, dict[str, RxStubPortBackFaceCorners]] = {}


def _require_design_registry(*, design_id: str) -> dict[str, RxStubPortBackFaceCorners]:
    assert design_id in RX_STUB_PORT_BACK_FACE_CORNERS_BY_DESIGN, (
        f"rx stub port back-face capture missing design entry (design_id={design_id})"
    )
    return RX_STUB_PORT_BACK_FACE_CORNERS_BY_DESIGN[design_id]


def reset_rx_stub_port_back_face_corners(design_id: str) -> None:
    RX_STUB_PORT_BACK_FACE_CORNERS_BY_DESIGN[design_id] = {}


def _require_point3(values: Sequence[float], *, context: str) -> Point3:
    if len(values) != 3:
        raise ValueError(f"{context} must be 3D (actual_len={len(values)})")
    return (float(values[0]), float(values[1]), float(values[2]))


def _require_positive_box_sizes(sizes: Point3, *, context: str) -> None:
    if sizes[0] <= 0.0 or sizes[1] <= 0.0 or sizes[2] <= 0.0:
        raise ValueError(f"{context} sizes must all be > 0 (sizes={sizes})")


def _record_rx_stub_port_back_face_corners(
    *,
    design_id: str,
    stub_key: str,
    corners: RxStubPortBackFaceCorners,
) -> str:
    design_registry = _require_design_registry(design_id=design_id)
    design_registry[stub_key] = corners
    return stub_key


def record_rx_dd_port_stub_back_face(
    *,
    design_id: str,
    board_id: str,
    instance_index: int,
    endpoint_label: str,
    origin: Sequence[float],
    sizes: Sequence[float],
) -> str:
    if endpoint_label not in ("A", "c"):
        raise ValueError(f"rx_dd port stub endpoint must be A/c (actual={endpoint_label})")
    box_origin = _require_point3(origin, context="rx_dd port stub origin")
    box_sizes = _require_point3(sizes, context="rx_dd port stub sizes")
    _require_positive_box_sizes(box_sizes, context="rx_dd port stub")
    face_x = box_origin[0]
    min_y = box_origin[1]
    max_y = box_origin[1] + box_sizes[1]
    min_z = box_origin[2]
    max_z = box_origin[2] + box_sizes[2]
    return _record_rx_stub_port_back_face_corners(
        design_id=design_id,
        stub_key=f"rx_dd_port:{board_id}:{instance_index}:{endpoint_label}",
        corners=(
            (face_x, min_y, min_z),
            (face_x, max_y, min_z),
            (face_x, min_y, max_z),
            (face_x, max_y, max_z),
        ),
    )


def get_rx_stub_port_back_face_corners(*, design_id: str, stub_key: str) -> RxStubPortBackFaceCorners:
    by_design = _require_design_registry(design_id=design_id)
    assert stub_key in by_design, (
        f"rx stub port back-face capture missing stub entry (design_id={design_id}, stub_key={stub_key})"
    )
    return by_design[stub_key]


def _sorted_unique(values: tuple[float, float, float, float]) -> list[float]:
    return sorted({float(value) for value in values})


def _back_face_axes(
    *,
    face_corners: RxStubPortBackFaceCorners,
    context: str,
) -> tuple[float, list[float], list[float]]:
    xs = _sorted_unique((face_corners[0][0], face_corners[1][0], face_corners[2][0], face_corners[3][0]))
    ys = _sorted_unique((face_corners[0][1], face_corners[1][1], face_corners[2][1], face_corners[3][1]))
    zs = _sorted_unique((face_corners[0][2], face_corners[1][2], face_corners[2][2], face_corners[3][2]))
    if len(xs) != 1 or len(ys) != 2 or len(zs) != 2:
        raise ValueError(f"{context} must define a YZ rectangle (corners={face_corners})")
    return xs[0], ys, zs


def _back_face_center(*, face_corners: RxStubPortBackFaceCorners) -> Point3:
    x_value, ys, zs = _back_face_axes(face_corners=face_corners, context="rx stub port back face")
    return (x_value, (ys[0] + ys[1]) / 2.0, (zs[0] + zs[1]) / 2.0)


def _rx_port_edge_from_back_face(
    *,
    face_corners: RxStubPortBackFaceCorners,
    peer_face_corners: RxStubPortBackFaceCorners,
) -> Edge2P:
    x_value, ys, zs = _back_face_axes(face_corners=face_corners, context="rx stub port back face")
    face_center = _back_face_center(face_corners=face_corners)
    peer_center = _back_face_center(face_corners=peer_face_corners)
    delta_y = peer_center[1] - face_center[1]
    delta_z = peer_center[2] - face_center[2]
    if abs(delta_y) <= 1e-12 and abs(delta_z) <= 1e-12:
        raise ValueError("rx stub port peer direction must be non-zero")
    if abs(delta_y) >= abs(delta_z):
        edge_y = ys[1] if delta_y >= 0.0 else ys[0]
        return (x_value, edge_y, zs[0]), (x_value, edge_y, zs[1])
    edge_z = zs[1] if delta_z >= 0.0 else zs[0]
    return (x_value, ys[0], edge_z), (x_value, ys[1], edge_z)


def resolve_rx_dd_port_edges_from_back_faces(
    *,
    design_id: str,
    signal_stub_key: str,
    reference_stub_key: str,
) -> tuple[Edge2P, Edge2P]:
    signal_face_corners = get_rx_stub_port_back_face_corners(design_id=design_id, stub_key=signal_stub_key)
    reference_face_corners = get_rx_stub_port_back_face_corners(design_id=design_id, stub_key=reference_stub_key)
    return (
        _rx_port_edge_from_back_face(
            face_corners=signal_face_corners,
            peer_face_corners=reference_face_corners,
        ),
        _rx_port_edge_from_back_face(
            face_corners=reference_face_corners,
            peer_face_corners=signal_face_corners,
        ),
    )


__all__ = [
    "RX_STUB_PORT_BACK_FACE_CORNERS_BY_DESIGN",
    "Edge2P",
    "RxStubPortBackFaceCorners",
    "get_rx_stub_port_back_face_corners",
    "record_rx_dd_port_stub_back_face",
    "reset_rx_stub_port_back_face_corners",
    "resolve_rx_dd_port_edges_from_back_faces",
]

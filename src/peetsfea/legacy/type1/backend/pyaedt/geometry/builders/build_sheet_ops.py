from __future__ import annotations

from .build_common import *

def _create_thickened_sheet_from_points(
    *,
    modeler: Modeler3D,
    sheet_points: list[list[float]],
    sheet_name: str,
    thickness: float,
) -> tuple[str, Object3d]:
    sheet_covered_name, sheet_loop_obj = _create_sheet_from_points(
        modeler=modeler,
        sheet_points=sheet_points,
        sheet_name=sheet_name,
    )
    try:
        thickened = modeler.thicken_sheet(assignment=sheet_covered_name, thickness=thickness)  # type: ignore[misc]
    except TypeError:
        raise
    if not thickened:
        raise ValueError(f"Sheet thicken failed (name={sheet_name}, thickness={thickness})")

    if isinstance(thickened, list):
        first = thickened[0] if thickened else sheet_covered_name
        thickened_name = first if isinstance(first, str) else _object_name(cast(Object3d, first))
        thickened_obj = cast(Object3d, sheet_loop_obj)
    elif isinstance(thickened, str):
        thickened_name = thickened
        thickened_obj = cast(Object3d, sheet_loop_obj)
    else:
        thickened_obj = cast(Object3d, thickened)
        thickened_name = _object_name(thickened_obj)
    return thickened_name, thickened_obj

def _create_sheet_from_points(
    *,
    modeler: Modeler3D,
    sheet_points: list[list[float]],
    sheet_name: str,
) -> tuple[str, Object3d]:
    sheet_created = modeler.create_polyline(points=sheet_points, name=sheet_name, material="copper", close_surface=True)
    if not sheet_created:
        raise ValueError(f"Sheet loop creation failed (name={sheet_name})")

    sheet_loop_obj = cast(Object3d, sheet_created)
    sheet_loop_name = _object_name(sheet_loop_obj)
    try:
        covered = modeler.cover_lines(assignment=sheet_loop_name)  # type: ignore[misc]
    except TypeError:
        raise
    if not covered:
        raise ValueError(f"Sheet cover_lines failed (name={sheet_name})")

    if covered is True:
        sheet_covered_name = sheet_loop_name
    elif isinstance(covered, list):
        first = covered[0] if covered else sheet_loop_name
        sheet_covered_name = first if isinstance(first, str) else _object_name(cast(Object3d, first))
    elif isinstance(covered, str):
        sheet_covered_name = covered
    else:
        sheet_covered_name = _object_name(cast(Object3d, covered))
    return sheet_covered_name, sheet_loop_obj

def _sheet_points_from_edge_pair(*, dd_edge: _Edge2P, vertical_edge: _Edge2P) -> list[list[float]]:
    dd_edge_0, dd_edge_1 = dd_edge
    v_edge_0, v_edge_1 = vertical_edge
    same_pair_cost = math.dist(dd_edge_0, v_edge_0) + math.dist(dd_edge_1, v_edge_1)
    cross_pair_cost = math.dist(dd_edge_0, v_edge_1) + math.dist(dd_edge_1, v_edge_0)
    if cross_pair_cost < same_pair_cost:
        v_edge_0, v_edge_1 = v_edge_1, v_edge_0
    return [
        [dd_edge_0[0], dd_edge_0[1], dd_edge_0[2]],
        [dd_edge_1[0], dd_edge_1[1], dd_edge_1[2]],
        [v_edge_1[0], v_edge_1[1], v_edge_1[2]],
        [v_edge_0[0], v_edge_0[1], v_edge_0[2]],
    ]

def _rxdd_connect_landing_segment_from_anchor_pair(
    *,
    anchor_xyz: _Point3,
    peer_anchor_xyz: _Point3,
    trace: float,
    stub_length_mm: float,
) -> _Edge2P:
    if trace <= 0.0:
        raise ValueError(f"rx_dd connect landing trace must be > 0 (actual={trace})")
    if stub_length_mm <= 0.0:
        raise ValueError(f"rx_dd connect landing stub length must be > 0 (actual={stub_length_mm})")
    if RX_DD_BACK_STUB_AXIS_SIGN_X != -1.0:
        raise ValueError(
            "rx_dd connect landing axis contract violation: RX_DD_BACK_STUB_AXIS_SIGN_X must be -1.0 "
            f"(actual={RX_DD_BACK_STUB_AXIS_SIGN_X})"
        )
    landing_center: _Point3 = (anchor_xyz[0] - stub_length_mm, anchor_xyz[1], anchor_xyz[2])
    peer_center: _Point3 = (peer_anchor_xyz[0] - stub_length_mm, peer_anchor_xyz[1], peer_anchor_xyz[2])
    dy = peer_center[1] - landing_center[1]
    dz = peer_center[2] - landing_center[2]
    centerline_length = math.hypot(dy, dz)
    if centerline_length <= 1e-12:
        raise ValueError("rx_dd connect landing centerline length must be > 0")
    width_dir_y = -dz / centerline_length
    width_dir_z = dy / centerline_length
    half_trace = trace / 2.0
    return (
        (landing_center[0], landing_center[1] + (width_dir_y * half_trace), landing_center[2] + (width_dir_z * half_trace)),
        (landing_center[0], landing_center[1] - (width_dir_y * half_trace), landing_center[2] - (width_dir_z * half_trace)),
    )

def _rxdd_connect_sheet_points_from_anchor_pair(
    *,
    first_anchor_xyz: _Point3,
    second_anchor_xyz: _Point3,
    first_trace: float,
    second_trace: float,
    stub_length_mm: float,
) -> list[list[float]]:
    if abs(first_trace - second_trace) > 1e-9:
        raise ValueError(
            "rx_dd connect bridge trace mismatch "
            f"(first_trace={first_trace}, second_trace={second_trace})"
        )
    first_segment = _rxdd_connect_landing_segment_from_anchor_pair(
        anchor_xyz=first_anchor_xyz,
        peer_anchor_xyz=second_anchor_xyz,
        trace=first_trace,
        stub_length_mm=stub_length_mm,
    )
    second_segment = _rxdd_connect_landing_segment_from_anchor_pair(
        anchor_xyz=second_anchor_xyz,
        peer_anchor_xyz=first_anchor_xyz,
        trace=second_trace,
        stub_length_mm=stub_length_mm,
    )
    return [
        [first_segment[0][0], first_segment[0][1], first_segment[0][2]],
        [first_segment[1][0], first_segment[1][1], first_segment[1][2]],
        [second_segment[0][0], second_segment[0][1], second_segment[0][2]],
        [second_segment[1][0], second_segment[1][1], second_segment[1][2]],
    ]

def _fr4_box_from_plane_bbox(
    *,
    plane: Literal["XY", "YZ", "ZX"],
    bbox: list[float],
    pcb_thickness: float,
    overlap_mm: float,
    eps_len: float,
) -> tuple[list[float], list[float]]:
    min_x, min_y, min_z, max_x, max_y, max_z = bbox
    span_x = max(max_x - min_x, eps_len)
    span_y = max(max_y - min_y, eps_len)
    span_z = max(max_z - min_z, eps_len)
    if plane == "XY":
        origin = [min_x - overlap_mm, min_y - overlap_mm, min_z - pcb_thickness - overlap_mm]
        # Apply overlap in plane only. Keep FR4 thickness axis unchanged to avoid FR4-FR4 intersections.
        sizes = [span_x + (2.0 * overlap_mm), span_y + (2.0 * overlap_mm), max(pcb_thickness, eps_len)]
    elif plane == "YZ":
        origin = [min_x - pcb_thickness - overlap_mm, min_y - overlap_mm, min_z - overlap_mm]
        sizes = [max(pcb_thickness, eps_len), span_y + (2.0 * overlap_mm), span_z + (2.0 * overlap_mm)]
    else:
        origin = [min_x - overlap_mm, min_y - pcb_thickness - overlap_mm, min_z - overlap_mm]
        sizes = [span_x + (2.0 * overlap_mm), max(pcb_thickness, eps_len), span_z + (2.0 * overlap_mm)]
    return origin, sizes
__all__ = [
    '_create_thickened_sheet_from_points',
    '_create_sheet_from_points',
    '_sheet_points_from_edge_pair',
    '_rxdd_connect_landing_segment_from_anchor_pair',
    '_rxdd_connect_sheet_points_from_anchor_pair',
    '_fr4_box_from_plane_bbox',
]

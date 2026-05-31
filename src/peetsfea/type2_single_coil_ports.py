from __future__ import annotations

import math
from typing import Literal
from typing import cast

import build123d as bd
from build123d.topology import Shape

from peetsfea.tx_rect_void import BoxSpec
from peetsfea.tx_rect_void import RealizedSingleCoilRectVoid
from peetsfea.tx_rect_void import SingleCoilProfile
from peetsfea.tx_rect_void import TX_PARALLEL_SINGLE_COIL_ROLES
from peetsfea.tx_rect_void_types import inner_corner_label_for_outer_corner
from peetsfea.tx_rect_void_types import terminal_end_corner_label
from peetsfea.tx_rect_void_types import terminal_path_from_quarter_turns
from peetsfea.tx_rect_void_types import terminal_start_corner_label
from peetsfea.type2_step_spec import Point3

_DERIVED_TERMINAL_DIRECTION: Literal["cw"] = "cw"


def local_terminal_plane_points(
    *,
    centerline: tuple[tuple[float, float], ...],
    transformed_boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
    frame_origin_xyz: Point3,
) -> tuple[tuple[float, float], tuple[float, float]]:
    if len(centerline) < 2:
        raise RuntimeError("type2 single-coil centerline must contain at least two points")
    start_label = f"{profile.copper_body_prefix}_bus_start"
    end_label = f"{profile.copper_body_prefix}_bus_end"
    start_bus_matches = [box for box in transformed_boxes if box.label == start_label]
    end_bus_matches = [box for box in transformed_boxes if box.label == end_label]
    if profile.role in TX_PARALLEL_SINGLE_COIL_ROLES and start_bus_matches and end_bus_matches:
        if len(start_bus_matches) != 1 or len(end_bus_matches) != 1:
            raise RuntimeError(
                "type2 tx multilayer terminal metadata requires exactly one start/end bus box "
                f"(start_matches={len(start_bus_matches)}, end_matches={len(end_bus_matches)})"
            )
        start_point_world = (
            start_bus_matches[0].origin_xyz[0] + (start_bus_matches[0].size_xyz[0] / 2.0),
            start_bus_matches[0].origin_xyz[1] + (start_bus_matches[0].size_xyz[1] / 2.0),
        )
        end_point_world = (
            end_bus_matches[0].origin_xyz[0] + (end_bus_matches[0].size_xyz[0] / 2.0),
            end_bus_matches[0].origin_xyz[1] + (end_bus_matches[0].size_xyz[1] / 2.0),
        )
    else:
        start_point_world = profile.plane_point(centerline[0], frame_origin_xyz=frame_origin_xyz)
        end_point_world = profile.plane_point(centerline[-1], frame_origin_xyz=frame_origin_xyz)
    local_origin_plane = profile.plane_point((0.0, 0.0), frame_origin_xyz=frame_origin_xyz)
    return (
        (
            start_point_world[0] - local_origin_plane[0],
            start_point_world[1] - local_origin_plane[1],
        ),
        (
            end_point_world[0] - local_origin_plane[0],
            end_point_world[1] - local_origin_plane[1],
        ),
    )


def port_sheet_label_for_profile(profile: SingleCoilProfile) -> str:
    if profile.role in TX_PARALLEL_SINGLE_COIL_ROLES:
        return f"{profile.copper_body_prefix.removesuffix('_copper')}_port_sheet"
    if profile.role == "rx_single_coil":
        return "rx_port_sheet"
    raise RuntimeError(f"unsupported single-coil profile role for port sheet label: {profile.role}")


def port_sheet_owner_bottom_plane_coordinate(*, box: BoxSpec, profile: SingleCoilProfile) -> float:
    if profile.plane == "XY":
        return box.origin_xyz[2]
    return box.origin_xyz[0]


def port_sheet_owner_bottom_square_plane_bounds(
    *,
    box: BoxSpec,
    profile: SingleCoilProfile,
) -> tuple[tuple[float, float], tuple[float, float]]:
    origin_x, origin_y, origin_z = box.origin_xyz
    size_x, size_y, size_z = box.size_xyz
    if profile.plane == "XY":
        square_side_a = size_x
        square_side_b = size_y
        plane_min = (origin_x, origin_y)
    else:
        square_side_a = size_y
        square_side_b = size_z
        plane_min = (origin_y, origin_z)
    if square_side_a <= 0.0 or square_side_b <= 0.0:
        raise RuntimeError(
            "type2 port sheet requires positive bottom-face square dimensions "
            f"(role={profile.role}, box={box.label}, size={box.size_xyz})"
        )
    if abs(square_side_a - square_side_b) > 1e-9:
        raise RuntimeError(
            "type2 port-sheet owner bottom-face footprint must be square for port sheet derivation "
            f"(role={profile.role}, box={box.label}, size={box.size_xyz})"
        )
    plane_max = (plane_min[0] + square_side_a, plane_min[1] + square_side_b)
    return (plane_min, plane_max)


def synthetic_tx_bus_owner_box(
    *,
    transformed_boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
    terminal_column: str,
) -> BoxSpec:
    if terminal_column not in {"start", "end"}:
        raise RuntimeError(f"unsupported terminal column: {terminal_column}")
    terminal_stub_boxes = tuple(box for box in transformed_boxes if box.feature == "terminal_stub")
    matching_stub_boxes = tuple(
        box for box in terminal_stub_boxes if box.label.endswith(f"_stub_{terminal_column}")
    )
    if len(matching_stub_boxes) == 0:
        raise RuntimeError(
            "type2 tx port sheet requires at least one transformed terminal stub per terminal column "
            f"(terminal_column={terminal_column}, actual=0)"
        )
    if len(matching_stub_boxes) * 2 != len(terminal_stub_boxes):
        raise RuntimeError(
            "type2 tx port sheet requires balanced transformed start/end terminal stub boxes "
            f"(terminal_column={terminal_column}, matching={len(matching_stub_boxes)}, total={len(terminal_stub_boxes)})"
        )
    min_x = min(box.origin_xyz[0] for box in matching_stub_boxes)
    min_y = min(box.origin_xyz[1] for box in matching_stub_boxes)
    min_z = min(box.origin_xyz[2] for box in matching_stub_boxes)
    max_x = max(box.origin_xyz[0] + box.size_xyz[0] for box in matching_stub_boxes)
    max_y = max(box.origin_xyz[1] + box.size_xyz[1] for box in matching_stub_boxes)
    max_z = max(box.origin_xyz[2] + box.size_xyz[2] for box in matching_stub_boxes)
    return BoxSpec(
        label=f"{profile.copper_body_prefix}_bus_{terminal_column}",
        role="copper",
        feature="vertical_bus",
        layer_index=0,
        origin_xyz=(min_x, min_y, min_z),
        size_xyz=(max_x - min_x, max_y - min_y, max_z - min_z),
    )


def port_sheet_owner_boxes(
    *,
    transformed_boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
) -> tuple[BoxSpec, BoxSpec]:
    if profile.role in TX_PARALLEL_SINGLE_COIL_ROLES:
        first_box, second_box = (
            synthetic_tx_bus_owner_box(
                transformed_boxes=transformed_boxes,
                profile=profile,
                terminal_column="start",
            ),
            synthetic_tx_bus_owner_box(
                transformed_boxes=transformed_boxes,
                profile=profile,
                terminal_column="end",
            ),
        )
    else:
        terminal_stub_boxes = tuple(box for box in transformed_boxes if box.feature == "terminal_stub")
        start_matches = [box for box in terminal_stub_boxes if box.label == f"{profile.copper_body_prefix}_l0_stub_start"]
        end_matches = [box for box in terminal_stub_boxes if box.label == f"{profile.copper_body_prefix}_l0_stub_end"]
        if len(start_matches) != 1 or len(end_matches) != 1 or len(terminal_stub_boxes) != 2:
            raise RuntimeError(
                "type2 port sheet requires exactly one transformed start/end terminal stub box "
                f"(role={profile.role}, start_matches={len(start_matches)}, end_matches={len(end_matches)}, actual={len(terminal_stub_boxes)})"
            )
        first_box, second_box = (start_matches[0], end_matches[0])
    first_bottom_plane_coordinate = port_sheet_owner_bottom_plane_coordinate(box=first_box, profile=profile)
    second_bottom_plane_coordinate = port_sheet_owner_bottom_plane_coordinate(box=second_box, profile=profile)
    if abs(first_bottom_plane_coordinate - second_bottom_plane_coordinate) > 1e-9:
        raise RuntimeError(
            "type2 port-sheet owner bottom faces must share one plane "
            f"(role={profile.role}, first={first_box.label}, second={second_box.label}, "
            f"first_bottom={first_bottom_plane_coordinate}, second_bottom={second_bottom_plane_coordinate})"
        )
    return (first_box, second_box)


def port_sheet_owner_bottom_square_center_plane_xy(
    *,
    box: BoxSpec,
    profile: SingleCoilProfile,
) -> tuple[float, float]:
    (plane_min_u, plane_min_v), (plane_max_u, plane_max_v) = port_sheet_owner_bottom_square_plane_bounds(
        box=box,
        profile=profile,
    )
    return (
        (plane_min_u + plane_max_u) / 2.0,
        (plane_min_v + plane_max_v) / 2.0,
    )


def plane_point_to_world_xyz(
    *,
    point_plane_xy: tuple[float, float],
    bottom_plane_coordinate: float,
    profile: SingleCoilProfile,
) -> Point3:
    if profile.plane == "XY":
        return (point_plane_xy[0], point_plane_xy[1], bottom_plane_coordinate)
    return (bottom_plane_coordinate, point_plane_xy[0], point_plane_xy[1])


def _facing_bottom_face_edge_plane_points(
    *,
    box: BoxSpec,
    profile: SingleCoilProfile,
    target_center_plane_xy: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    (plane_min_u, plane_min_v), (plane_max_u, plane_max_v) = port_sheet_owner_bottom_square_plane_bounds(
        box=box,
        profile=profile,
    )
    center_u = (plane_min_u + plane_max_u) / 2.0
    center_v = (plane_min_v + plane_max_v) / 2.0
    delta_u = target_center_plane_xy[0] - center_u
    delta_v = target_center_plane_xy[1] - center_v
    if math.hypot(delta_u, delta_v) <= 1e-9:
        raise RuntimeError(
            "type2 port sheet owner centers must be separated "
            f"(role={profile.role}, box={box.label}, center={(center_u, center_v)}, target={target_center_plane_xy})"
        )
    if abs(delta_u) >= abs(delta_v):
        edge_u = plane_max_u if delta_u > 0.0 else plane_min_u
        return ((edge_u, plane_min_v), (edge_u, plane_max_v))
    edge_v = plane_max_v if delta_v > 0.0 else plane_min_v
    return ((plane_min_u, edge_v), (plane_max_u, edge_v))


def _edge_center(edge: tuple[Point3, Point3]) -> Point3:
    first, second = edge
    return (
        (first[0] + second[0]) / 2.0,
        (first[1] + second[1]) / 2.0,
        (first[2] + second[2]) / 2.0,
    )


def _distance_sq(first: Point3, second: Point3) -> float:
    return (
        (first[0] - second[0]) ** 2
        + (first[1] - second[1]) ** 2
        + (first[2] - second[2]) ** 2
    )


def build_single_coil_port_sheet_shape(
    *,
    transformed_boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
) -> Shape:
    vertices = single_coil_port_sheet_vertices(
        transformed_boxes=transformed_boxes,
        profile=profile,
    )
    with bd.BuildLine() as builder:
        bd.Polyline(*vertices, close=True)
    assert builder.line is not None, "type2 port-sheet line builder must produce a wire"
    port_wire = builder.line.wires()[0]
    face = cast(bd.Face, bd.make_face(edges=tuple(port_wire.edges())))
    face.label = port_sheet_label_for_profile(profile)
    return face


def single_coil_port_sheet_vertices(
    *,
    transformed_boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
) -> tuple[Point3, Point3, Point3, Point3]:
    signal_box, reference_box = port_sheet_owner_boxes(
        transformed_boxes=transformed_boxes,
        profile=profile,
    )
    signal_center_plane_xy = port_sheet_owner_bottom_square_center_plane_xy(box=signal_box, profile=profile)
    reference_center_plane_xy = port_sheet_owner_bottom_square_center_plane_xy(box=reference_box, profile=profile)
    signal_edge_plane = _facing_bottom_face_edge_plane_points(
        box=signal_box,
        profile=profile,
        target_center_plane_xy=reference_center_plane_xy,
    )
    reference_edge_plane = _facing_bottom_face_edge_plane_points(
        box=reference_box,
        profile=profile,
        target_center_plane_xy=signal_center_plane_xy,
    )
    bottom_plane_coordinate = port_sheet_owner_bottom_plane_coordinate(box=signal_box, profile=profile)
    signal_edge = (
        plane_point_to_world_xyz(
            point_plane_xy=signal_edge_plane[0],
            bottom_plane_coordinate=bottom_plane_coordinate,
            profile=profile,
        ),
        plane_point_to_world_xyz(
            point_plane_xy=signal_edge_plane[1],
            bottom_plane_coordinate=bottom_plane_coordinate,
            profile=profile,
        ),
    )
    reference_edge = (
        plane_point_to_world_xyz(
            point_plane_xy=reference_edge_plane[0],
            bottom_plane_coordinate=bottom_plane_coordinate,
            profile=profile,
        ),
        plane_point_to_world_xyz(
            point_plane_xy=reference_edge_plane[1],
            bottom_plane_coordinate=bottom_plane_coordinate,
            profile=profile,
        ),
    )
    if _distance_sq(signal_edge[0], signal_edge[1]) <= 1e-18:
        raise RuntimeError(f"type2 port sheet signal edge must be non-degenerate (role={profile.role})")
    if _distance_sq(reference_edge[0], reference_edge[1]) <= 1e-18:
        raise RuntimeError(f"type2 port sheet reference edge must be non-degenerate (role={profile.role})")
    if _distance_sq(_edge_center(signal_edge), _edge_center(reference_edge)) <= 1e-18:
        raise RuntimeError(f"type2 port sheet signal/reference edges must be separated (role={profile.role})")
    vertices = (
        signal_edge[1],
        reference_edge[1],
        reference_edge[0],
        signal_edge[0],
    )
    for vertex_index, vertex in enumerate(vertices):
        if not all(math.isfinite(component) for component in vertex):
            raise RuntimeError(
                "type2 port sheet vertices must be finite "
                f"(role={profile.role}, vertex_index={vertex_index}, vertex={vertex})"
            )
    return vertices


def single_coil_port_integration_line(
    *,
    transformed_boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
) -> tuple[Point3, Point3]:
    vertices = single_coil_port_sheet_vertices(
        transformed_boxes=transformed_boxes,
        profile=profile,
    )
    signal_edge = (vertices[3], vertices[0])
    reference_edge = (vertices[1], vertices[2])
    return (_edge_center(signal_edge), _edge_center(reference_edge))


def parse_terminal_path_components(raw_terminal_path: str) -> tuple[str, str, str]:
    parts = raw_terminal_path.split("_")
    if len(parts) != 4 or parts[2] != "to":
        raise ValueError(f"terminal path must use '<outer>_<direction>_to_<inner>' format: {raw_terminal_path}")
    outer_corner, direction, _to_keyword, inner_corner = parts
    if outer_corner not in {"A", "B", "C", "D"}:
        raise ValueError(f"terminal path outer corner must be one of A/B/C/D: {raw_terminal_path}")
    if inner_corner not in {"a", "b", "c", "d"}:
        raise ValueError(f"terminal path inner corner must be one of a/b/c/d: {raw_terminal_path}")
    if direction not in {"cw", "ccw"}:
        raise ValueError(f"terminal path direction must be 'cw' or 'ccw': {raw_terminal_path}")
    return (outer_corner, direction, inner_corner)


def _realized_derived_terminal_fields(
    realized: RealizedSingleCoilRectVoid,
) -> tuple[str, Literal["A", "B", "C", "D"], Literal["cw"], Literal["a", "b", "c", "d"]]:
    raw_terminal_start = realized.terminal_start
    if not isinstance(raw_terminal_start, int) or isinstance(raw_terminal_start, bool):
        raise RuntimeError(
            "type2 single-coil realized terminal_start must be an integer index "
            f"(actual={raw_terminal_start!r})"
        )
    raw_turn_qcount = realized.turn_qcount
    if not isinstance(raw_turn_qcount, int) or isinstance(raw_turn_qcount, bool):
        raise RuntimeError(
            "type2 single-coil realized turn_qcount must be an integer quarter-turn count "
            f"(actual={raw_turn_qcount!r})"
        )
    if raw_turn_qcount <= 0:
        raise RuntimeError(
            "type2 single-coil realized turn_qcount must be positive "
            f"(actual={raw_turn_qcount})"
        )
    outer_corner = terminal_start_corner_label(raw_terminal_start)
    end_corner = terminal_end_corner_label(terminal_start=raw_terminal_start, turn_qcount=raw_turn_qcount)
    expected_path = terminal_path_from_quarter_turns(
        terminal_start=raw_terminal_start,
        turn_qcount=raw_turn_qcount,
    )
    if realized.terminal_start_corner != outer_corner:
        raise RuntimeError(
            "type2 single-coil realized terminal_start_corner must match terminal_start "
            f"(terminal_start={raw_terminal_start}, actual={realized.terminal_start_corner}, expected={outer_corner})"
        )
    if realized.terminal_end_corner != end_corner:
        raise RuntimeError(
            "type2 single-coil realized terminal_end_corner must match terminal_start + turn_qcount "
            f"(terminal_start={raw_terminal_start}, turn_qcount={raw_turn_qcount}, "
            f"actual={realized.terminal_end_corner}, expected={end_corner})"
        )
    if realized.terminal_direction != _DERIVED_TERMINAL_DIRECTION:
        raise RuntimeError(
            "type2 single-coil realized terminal direction must be fixed clockwise "
            f"(actual={realized.terminal_direction})"
        )
    if realized.terminal_path != expected_path:
        raise RuntimeError(
            "type2 single-coil realized terminal_path must match quarter-turn metadata "
            f"(actual={realized.terminal_path}, expected={expected_path})"
        )
    return (
        realized.terminal_path,
        outer_corner,
        _DERIVED_TERMINAL_DIRECTION,
        inner_corner_label_for_outer_corner(end_corner),
    )


def modeled_terminal_metadata(
    *,
    realized: RealizedSingleCoilRectVoid,
    profile: SingleCoilProfile,
    frame_origin_xyz: Point3,
    transformed_boxes: tuple[BoxSpec, ...],
) -> dict[str, object]:
    terminal_path, outer_corner, direction, inner_corner = _realized_derived_terminal_fields(realized)
    vertices_xyz = single_coil_port_sheet_vertices(
        transformed_boxes=transformed_boxes,
        profile=profile,
    )
    integration_line_start_xyz, integration_line_end_xyz = single_coil_port_integration_line(
        transformed_boxes=transformed_boxes,
        profile=profile,
    )
    return {
        "kind": "single_coil_port_v1",
        "path": terminal_path,
        "outer_corner": outer_corner,
        "inner_corner": inner_corner,
        "direction": direction,
        "sheet_name": port_sheet_label_for_profile(profile),
        "vertices_xyz": vertices_xyz,
        "integration_line_start_xyz": integration_line_start_xyz,
        "integration_line_end_xyz": integration_line_end_xyz,
    }


__all__ = [
    "build_single_coil_port_sheet_shape",
    "local_terminal_plane_points",
    "modeled_terminal_metadata",
    "parse_terminal_path_components",
    "port_sheet_label_for_profile",
    "single_coil_port_integration_line",
    "single_coil_port_sheet_vertices",
]

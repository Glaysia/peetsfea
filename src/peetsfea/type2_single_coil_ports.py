from __future__ import annotations

import math
from typing import cast

import build123d as bd

from peetsfea.tx_rect_void import BoxSpec
from peetsfea.tx_rect_void import SingleCoilProfile
from peetsfea.type2_step_spec import Point3


def local_terminal_plane_points(
    *,
    terminal_path: str,
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
    if profile.role == "tx_single_coil" and start_bus_matches and end_bus_matches:
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
        _outer_corner, _direction, _inner_corner = parse_terminal_path_components(terminal_path)
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
    if profile.role == "tx_single_coil":
        return "tx_port_sheet"
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
    if profile.role == "tx_single_coil":
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


def line_signed_distance_in_plane(
    *,
    point_plane_xy: tuple[float, float],
    line_origin_plane_xy: tuple[float, float],
    line_direction_plane_xy: tuple[float, float],
) -> float:
    direction_u, direction_v = line_direction_plane_xy
    direction_length = math.hypot(direction_u, direction_v)
    if direction_length <= 1e-9:
        raise RuntimeError(
            "type2 port sheet inter-owner centerline must have positive length "
            f"(line_origin={line_origin_plane_xy}, line_direction={line_direction_plane_xy})"
        )
    point_offset_u = point_plane_xy[0] - line_origin_plane_xy[0]
    point_offset_v = point_plane_xy[1] - line_origin_plane_xy[1]
    return ((direction_u * point_offset_v) - (direction_v * point_offset_u)) / direction_length


def plane_point_to_world_xyz(
    *,
    point_plane_xy: tuple[float, float],
    bottom_plane_coordinate: float,
    profile: SingleCoilProfile,
) -> Point3:
    if profile.plane == "XY":
        return (point_plane_xy[0], point_plane_xy[1], bottom_plane_coordinate)
    return (bottom_plane_coordinate, point_plane_xy[0], point_plane_xy[1])


def selected_diagonal_plane_points_for_stub(
    *,
    box: BoxSpec,
    profile: SingleCoilProfile,
    line_origin_plane_xy: tuple[float, float],
    line_direction_plane_xy: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    (plane_min_u, plane_min_v), (plane_max_u, plane_max_v) = port_sheet_owner_bottom_square_plane_bounds(
        box=box,
        profile=profile,
    )
    candidate_diagonals = (
        ((plane_min_u, plane_min_v), (plane_max_u, plane_max_v)),
        ((plane_min_u, plane_max_v), (plane_max_u, plane_min_v)),
    )

    def _ordered_endpoints(
        diagonal: tuple[tuple[float, float], tuple[float, float]],
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        def _endpoint_sort_key(point_plane_xy: tuple[float, float]) -> tuple[float, float, float]:
            signed_distance = line_signed_distance_in_plane(
                point_plane_xy=point_plane_xy,
                line_origin_plane_xy=line_origin_plane_xy,
                line_direction_plane_xy=line_direction_plane_xy,
            )
            return (
                signed_distance,
                point_plane_xy[0],
                point_plane_xy[1],
            )

        ordered_points = tuple(sorted(diagonal, key=_endpoint_sort_key, reverse=True))
        if len(ordered_points) != 2:
            raise RuntimeError(f"type2 port sheet diagonal ordering must keep two endpoints: {ordered_points}")
        return cast(tuple[tuple[float, float], tuple[float, float]], ordered_points)

    def _diagonal_selection_key(
        diagonal: tuple[tuple[float, float], tuple[float, float]],
    ) -> tuple[float, float, float, float, float]:
        ordered_first_point_plane_xy, ordered_second_point_plane_xy = _ordered_endpoints(diagonal)
        signed_distance_a = abs(
            line_signed_distance_in_plane(
                point_plane_xy=ordered_first_point_plane_xy,
                line_origin_plane_xy=line_origin_plane_xy,
                line_direction_plane_xy=line_direction_plane_xy,
            )
        )
        signed_distance_b = abs(
            line_signed_distance_in_plane(
                point_plane_xy=ordered_second_point_plane_xy,
                line_origin_plane_xy=line_origin_plane_xy,
                line_direction_plane_xy=line_direction_plane_xy,
            )
        )
        return (
            signed_distance_a + signed_distance_b,
            ordered_first_point_plane_xy[0],
            ordered_first_point_plane_xy[1],
            ordered_second_point_plane_xy[0],
            ordered_second_point_plane_xy[1],
        )

    selected_diagonal = max(candidate_diagonals, key=_diagonal_selection_key)
    return _ordered_endpoints(selected_diagonal)


def build_single_coil_port_sheet_shape(
    *,
    transformed_boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
) -> bd.Shape:
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
    first_stub_box, second_stub_box = port_sheet_owner_boxes(
        transformed_boxes=transformed_boxes,
        profile=profile,
    )
    first_stub_center_plane_xy = port_sheet_owner_bottom_square_center_plane_xy(box=first_stub_box, profile=profile)
    second_stub_center_plane_xy = port_sheet_owner_bottom_square_center_plane_xy(box=second_stub_box, profile=profile)
    inter_stub_centerline_direction_plane_xy = (
        second_stub_center_plane_xy[0] - first_stub_center_plane_xy[0],
        second_stub_center_plane_xy[1] - first_stub_center_plane_xy[1],
    )
    first_diagonal_start_plane_xy, first_diagonal_end_plane_xy = selected_diagonal_plane_points_for_stub(
        box=first_stub_box,
        profile=profile,
        line_origin_plane_xy=first_stub_center_plane_xy,
        line_direction_plane_xy=inter_stub_centerline_direction_plane_xy,
    )
    second_diagonal_start_plane_xy, second_diagonal_end_plane_xy = selected_diagonal_plane_points_for_stub(
        box=second_stub_box,
        profile=profile,
        line_origin_plane_xy=first_stub_center_plane_xy,
        line_direction_plane_xy=inter_stub_centerline_direction_plane_xy,
    )
    bottom_plane_coordinate = port_sheet_owner_bottom_plane_coordinate(box=first_stub_box, profile=profile)
    first_diagonal_start_world_xyz = plane_point_to_world_xyz(
        point_plane_xy=first_diagonal_start_plane_xy,
        bottom_plane_coordinate=bottom_plane_coordinate,
        profile=profile,
    )
    first_diagonal_end_world_xyz = plane_point_to_world_xyz(
        point_plane_xy=first_diagonal_end_plane_xy,
        bottom_plane_coordinate=bottom_plane_coordinate,
        profile=profile,
    )
    second_diagonal_start_world_xyz = plane_point_to_world_xyz(
        point_plane_xy=second_diagonal_start_plane_xy,
        bottom_plane_coordinate=bottom_plane_coordinate,
        profile=profile,
    )
    second_diagonal_end_world_xyz = plane_point_to_world_xyz(
        point_plane_xy=second_diagonal_end_plane_xy,
        bottom_plane_coordinate=bottom_plane_coordinate,
        profile=profile,
    )
    vertices = (
        first_diagonal_start_world_xyz,
        second_diagonal_start_world_xyz,
        second_diagonal_end_world_xyz,
        first_diagonal_end_world_xyz,
    )
    return vertices


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


def modeled_terminal_metadata(
    *,
    terminal_path: str,
    centerline: tuple[tuple[float, float], ...],
    profile: SingleCoilProfile,
    frame_origin_xyz: Point3,
    transformed_boxes: tuple[BoxSpec, ...],
) -> dict[str, object]:
    outer_corner, direction, inner_corner = parse_terminal_path_components(terminal_path)
    plane_origin_xy = profile.plane_point((0.0, 0.0), frame_origin_xyz=frame_origin_xyz)
    local_start_xy, local_end_xy = local_terminal_plane_points(
        terminal_path=terminal_path,
        centerline=centerline,
        transformed_boxes=transformed_boxes,
        profile=profile,
        frame_origin_xyz=frame_origin_xyz,
    )
    start_point_plane_mm = (
        local_start_xy[0] + plane_origin_xy[0],
        local_start_xy[1] + plane_origin_xy[1],
    )
    end_point_plane_mm = (
        local_end_xy[0] + plane_origin_xy[0],
        local_end_xy[1] + plane_origin_xy[1],
    )
    port_sheet_vertices_xyz = single_coil_port_sheet_vertices(
        transformed_boxes=transformed_boxes,
        profile=profile,
    )
    return {
        "path": terminal_path,
        "outer_corner": outer_corner,
        "inner_corner": inner_corner,
        "direction": direction,
        "start_point_plane_mm": start_point_plane_mm,
        "end_point_plane_mm": end_point_plane_mm,
        "port_sheet_vertices_xyz": port_sheet_vertices_xyz,
    }


__all__ = [
    "build_single_coil_port_sheet_shape",
    "local_terminal_plane_points",
    "modeled_terminal_metadata",
    "parse_terminal_path_components",
    "port_sheet_label_for_profile",
    "single_coil_port_sheet_vertices",
]

from __future__ import annotations

import json
import math
from pathlib import Path

import build123d as bd
import pytest

from peetsfea.tx_rect_void import (
    BoxSpec,
    RealizedSingleCoilRectVoid,
    RectBounds,
    RX_SINGLE_COIL_PROFILE,
    SingleCoilProfile,
    TX_SINGLE_COIL_PROFILE,
    _copper_primitives_for_layer,
    _offset_join_point,
    _polygon_bounds,
    _segment_joined_polygon,
    build_tx_rect_void_box_specs,
    build_tx_rect_void_centerline,
    build_tx_rect_void_step_scene,
    export_tx_rect_void_step_from_spec,
    export_tx_rect_void_step,
    load_tx_rect_void_spec,
    modeled_body_bounds_from_boxes,
    realize_tx_rect_void_spec,
)
from peetsfea.tx_rect_void_geometry import CopperPrimitive


def _range(is_integer: bool, start: float, end: float, count: int) -> str:
    flag = "true" if is_integer else "false"
    return f"[{flag}, {start}, {end}, {count}]"


def _spec_text(
    *,
    terminal_path: str = "A_cw_to_a",
    outer_x: float = 100.0,
    outer_y: float = 100.0,
    turn_count: int = 3,
    layer_count: int = 1,
    layer_gap: float = 2.0,
    terminal_stub_length: float = 5.0,
    void_usage_ratio: float = 0.2,
    margin_ratio: float = 0.05,
    metal_fill_factor: float = 0.5,
) -> str:
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.tx_rect_void_coil.step.v1"
runtime_compatible = false

[design]
units = "mm"

[manufacturing]
pcb_thickness_mm = 1.6
copper_thickness_mm = 0.1

[tx_coil.outer_x_mm]
range = {_range(False, outer_x, outer_x, 1)}
[tx_coil.outer_y_mm]
range = {_range(False, outer_y, outer_y, 1)}
[tx_coil.turn_count]
range = {_range(True, float(turn_count), float(turn_count), 1)}
[tx_coil.layer_count]
range = {_range(True, float(layer_count), float(layer_count), 1)}
[tx_coil.layer_gap_mm]
range = {_range(False, layer_gap, layer_gap, 1)}
[tx_coil.terminal_stub_length_mm]
range = {_range(False, terminal_stub_length, terminal_stub_length, 1)}
[tx_coil.void_usage_ratio]
range = {_range(False, void_usage_ratio, void_usage_ratio, 1)}
[tx_coil.margin_ratio]
range = {_range(False, margin_ratio, margin_ratio, 1)}
[tx_coil.metal_fill_factor]
range = {_range(False, metal_fill_factor, metal_fill_factor, 1)}
[tx_coil.terminal_path]
value = "{terminal_path}"
""".strip()


def _write_spec(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "tx_rect_void.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _type2_fixed_toml_with_required_underlay_field(tmp_path: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    source_path = repo_root / "examples" / "type2_fixed.toml"
    source_text = source_path.read_text(encoding="utf-8")
    if "[modeled_objects.underlay_repeat_count]" not in source_text:
        source_lines = source_text.splitlines()
        rewritten_lines: list[str] = []
        modeled_object_count = 0
        inserted_count = 0
        line_index = 0
        while line_index < len(source_lines):
            line = source_lines[line_index]
            rewritten_lines.append(line)
            if line == "[[modeled_objects]]":
                modeled_object_count += 1
            if line == "[modeled_objects.layer_count]":
                line_index += 1
                assert line_index < len(source_lines)
                rewritten_lines.append(source_lines[line_index])
                rewritten_lines.extend(
                    (
                        "",
                        "[modeled_objects.underlay_repeat_count]",
                        "range = [true, 0, 0, 1]",
                    )
                )
                inserted_count += 1
            line_index += 1
        assert inserted_count == modeled_object_count
        source_text = "\n".join(rewritten_lines) + "\n"
    normalized_path = tmp_path / "type2_fixed.with_underlay.toml"
    normalized_path.write_text(source_text, encoding="utf-8")
    return normalized_path


def _box_xy_bounds(box: BoxSpec) -> RectBounds:
    origin_x, origin_y, _origin_z = box.origin_xyz
    size_x, size_y, _size_z = box.size_xyz
    return RectBounds(
        min_x=origin_x,
        max_x=origin_x + size_x,
        min_y=origin_y,
        max_y=origin_y + size_y,
    )


def _copper_boxes(boxes: tuple[BoxSpec, ...]) -> list[BoxSpec]:
    return [box for box in boxes if box.role == "copper"]


def _pcb_boxes(boxes: tuple[BoxSpec, ...]) -> list[BoxSpec]:
    return [box for box in boxes if box.role == "pcb"]


def _box_by_label(boxes: tuple[BoxSpec, ...], *, label: str) -> BoxSpec:
    matches = [box for box in boxes if box.label == label]
    assert len(matches) == 1
    return matches[0]


def _has_blunt_corner_segment(points: tuple[tuple[float, float], ...]) -> bool:
    for first, second in zip(points[:-1], points[1:]):
        if abs(second[0] - first[0]) > 1e-9 and abs(second[1] - first[1]) > 1e-9:
            return True
    return False


def _point_distance_2d(first: tuple[float, float], second: tuple[float, float]) -> float:
    dx = first[0] - second[0]
    dy = first[1] - second[1]
    return (dx * dx + dy * dy) ** 0.5


def _point_distance_to_line_2d(
    point_xy: tuple[float, float],
    *,
    line_start_xy: tuple[float, float],
    line_end_xy: tuple[float, float],
) -> float:
    line_dx = line_end_xy[0] - line_start_xy[0]
    line_dy = line_end_xy[1] - line_start_xy[1]
    line_length = math.hypot(line_dx, line_dy)
    assert line_length > 0.0
    point_dx = point_xy[0] - line_start_xy[0]
    point_dy = point_xy[1] - line_start_xy[1]
    return abs((line_dx * point_dy) - (line_dy * point_dx)) / line_length


def _polygon_center_2d(polygon_xy: tuple[tuple[float, float], ...]) -> tuple[float, float]:
    assert len(polygon_xy) == 4
    return (
        sum(point_xy[0] for point_xy in polygon_xy) / 4.0,
        sum(point_xy[1] for point_xy in polygon_xy) / 4.0,
    )


def _selected_stub_diagonal_world_points(
    *,
    stub_primitive: CopperPrimitive,
    other_stub_primitive: CopperPrimitive,
    profile: SingleCoilProfile,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    stub_center_xy = _polygon_center_2d(stub_primitive.polygon_xy)
    other_stub_center_xy = _polygon_center_2d(other_stub_primitive.polygon_xy)
    diagonal_candidates = (
        (stub_primitive.polygon_xy[0], stub_primitive.polygon_xy[2]),
        (stub_primitive.polygon_xy[1], stub_primitive.polygon_xy[3]),
    )
    best_diagonal_xy = diagonal_candidates[0]
    best_score = -1.0
    for diagonal_xy in diagonal_candidates:
        diagonal_score = sum(
            _point_distance_to_line_2d(
                point_xy,
                line_start_xy=stub_center_xy,
                line_end_xy=other_stub_center_xy,
            )
            for point_xy in diagonal_xy
        )
        if diagonal_score > best_score + 1e-9:
            best_diagonal_xy = diagonal_xy
            best_score = diagonal_score
    alternate_diagonal_xy = diagonal_candidates[1] if best_diagonal_xy == diagonal_candidates[0] else diagonal_candidates[0]
    best_score_check = sum(
        _point_distance_to_line_2d(
            point_xy,
            line_start_xy=stub_center_xy,
            line_end_xy=other_stub_center_xy,
        )
        for point_xy in best_diagonal_xy
    )
    alternate_score = sum(
        _point_distance_to_line_2d(
            point_xy,
            line_start_xy=stub_center_xy,
            line_end_xy=other_stub_center_xy,
        )
        for point_xy in alternate_diagonal_xy
    )
    assert best_score_check >= alternate_score - 1e-9
    first_point_xy, second_point_xy = best_diagonal_xy
    return (
        profile.world_point(
            (first_point_xy[0], first_point_xy[1], stub_primitive.origin_z),
            frame_origin_xyz=(0.0, 0.0, 0.0),
        ),
        profile.world_point(
            (second_point_xy[0], second_point_xy[1], stub_primitive.origin_z),
            frame_origin_xyz=(0.0, 0.0, 0.0),
        ),
    )


def _naive_offset_vertex(
    centerline: tuple[tuple[float, float], ...],
    *,
    trace_width_mm: float,
    vertex_index: int,
    incoming: bool,
    side: str,
) -> tuple[float, float]:
    if incoming:
        start_point = centerline[vertex_index - 1]
        end_point = centerline[vertex_index]
    else:
        start_point = centerline[vertex_index]
        end_point = centerline[vertex_index + 1]
    dx = end_point[0] - start_point[0]
    dy = end_point[1] - start_point[1]
    length = (dx * dx + dy * dy) ** 0.5
    assert length > 0.0
    unit_x = dx / length
    unit_y = dy / length
    sign = 1.0 if side == "left" else -1.0
    half_trace = trace_width_mm / 2.0
    return (
        centerline[vertex_index][0] + ((-unit_y) * half_trace * sign),
        centerline[vertex_index][1] + (unit_x * half_trace * sign),
    )


def _polygon_has_vertex(polygon_xy: tuple[tuple[float, float], ...], point_xy: tuple[float, float]) -> bool:
    return any(_point_distance_2d(vertex, point_xy) <= 1e-6 for vertex in polygon_xy)


def _union_xy_bounds(boxes: list[BoxSpec]) -> RectBounds:
    assert boxes
    bounds = [_box_xy_bounds(box) for box in boxes]
    return RectBounds(
        min_x=min(bound.min_x for bound in bounds),
        max_x=max(bound.max_x for bound in bounds),
        min_y=min(bound.min_y for bound in bounds),
        max_y=max(bound.max_y for bound in bounds),
    )


def _assert_zero_intersection_volume(first: object, second: object) -> None:
    assert isinstance(first, bd.Shape)
    assert isinstance(second, bd.Shape)
    shared_shape = first.intersect(second)
    if shared_shape is None:
        return
    assert isinstance(shared_shape, bd.Shape)
    shared_solids = tuple(shared_shape.solids())
    if len(shared_solids) == 0:
        return
    shared_volume = sum(float(solid.volume) for solid in shared_solids)
    assert shared_volume == pytest.approx(0.0, abs=1e-9)


def _scene_child_by_label(scene: bd.Compound, *, label: str) -> bd.Shape:
    matches = [shape for shape in scene.children if shape.label == label]
    assert len(matches) == 1
    return matches[0]


def _point3_key(point_xyz: tuple[float, float, float]) -> tuple[int, int, int]:
    x, y, z = point_xyz
    return (
        int(round(x * 1_000_000)),
        int(round(y * 1_000_000)),
        int(round(z * 1_000_000)),
    )


def _point3_edge_key(
    first_point_xyz: tuple[float, float, float],
    second_point_xyz: tuple[float, float, float],
) -> frozenset[tuple[int, int, int]]:
    return frozenset((_point3_key(first_point_xyz), _point3_key(second_point_xyz)))


def _assert_port_sheet_is_metadata_only(*, scene: bd.Compound, profile: SingleCoilProfile) -> None:
    port_sheet_label = "tx_port_sheet" if profile.role == "tx_single_coil" else "rx_port_sheet"
    assert port_sheet_label not in tuple(shape.label for shape in scene.children)


def test_load_and_realize_valid_spec_is_deterministic(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(layer_gap=3.0, terminal_stub_length=99.0))
    spec = load_tx_rect_void_spec(toml_path)

    first = realize_tx_rect_void_spec(spec, seed=10)
    second = realize_tx_rect_void_spec(spec, seed=10)

    assert first == second
    assert first.outer_y_mm == pytest.approx(100.0)
    assert first.layer_count == 1
    assert first.terminal_stub_length_mm == pytest.approx(first.layer_gap_mm * 0.8)
    assert first.void_x_over_outer_x == pytest.approx(0.2)
    assert first.void_y_over_outer_y == pytest.approx(0.2)
    assert first.void_center_x_over_outer_x == pytest.approx(0.0)
    assert first.void_center_y_over_outer_y == pytest.approx(0.0)
    assert first.void_x_mm == pytest.approx(first.outer_x_mm * 0.2)
    assert first.void_y_mm == pytest.approx(first.outer_y_mm * 0.2)
    assert first.void_center_x_mm == pytest.approx(0.0)
    assert first.void_center_y_mm == pytest.approx(0.0)
    assert first.side_geometry.left.trace_mm == pytest.approx(first.side_geometry.right.trace_mm)


def test_terminal_stub_length_is_derived_from_layer_gap(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(layer_gap=2.5, terminal_stub_length=99.0))

    realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)

    assert realized.layer_gap_mm == pytest.approx(2.5)
    assert realized.terminal_stub_length_mm == pytest.approx(2.0)


def test_missing_required_key_fails(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text().replace("[tx_coil.outer_x_mm]", "[tx_coil.outer_x_missing]"))

    with pytest.raises(ValueError, match=r"tx_coil is missing required key 'outer_x_mm'"):
        load_tx_rect_void_spec(toml_path)


def test_bad_range_fails(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text().replace("range = [true, 3.0, 3.0, 1]", "range = [false, 3.0, 3.0, 1]", 1))

    with pytest.raises(ValueError, match=r"tx_coil\.turn_count\.range\[0\] must be true"):
        load_tx_rect_void_spec(toml_path)


def test_unsupported_terminal_path_fails(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(terminal_path="A_cw_to_b"))

    with pytest.raises(ValueError, match=r"requires matching outer/inner corners"):
        load_tx_rect_void_spec(toml_path)


@pytest.mark.parametrize(
    "legacy_void_key",
    (
        "void_x_over_outer_x",
        "void_y_over_outer_y",
        "void_center_x_over_outer_x",
        "void_center_y_over_outer_y",
    ),
)
def test_legacy_void_range_key_fails_as_unsupported_schema_input(
    tmp_path: Path,
    legacy_void_key: str,
) -> None:
    toml_path = _write_spec(
        tmp_path,
        _spec_text().replace(
            "[tx_coil.margin_ratio]",
            (
                f"[tx_coil.{legacy_void_key}]\n"
                "range = [false, 0.3, 0.3, 1]\n"
                "[tx_coil.margin_ratio]"
            ),
        ),
    )
    with pytest.raises(
        ValueError,
        match=rf"Unsupported tx_rect_void schema input.*tx_coil\.{legacy_void_key}",
    ):
        load_tx_rect_void_spec(toml_path)


@pytest.mark.parametrize("terminal_path", ("A_cw_to_a", "B_cw_to_b", "C_cw_to_c", "D_cw_to_d", "A_ccw_to_a", "B_ccw_to_b", "C_ccw_to_c", "D_ccw_to_d"))
@pytest.mark.parametrize("turn_count", (1, 4, 6))
def test_geometry_routes_around_void_for_supported_corners(
    tmp_path: Path,
    terminal_path: str,
    turn_count: int,
) -> None:
    toml_path = _write_spec(
        tmp_path,
            _spec_text(
                terminal_path=terminal_path,
                turn_count=turn_count,
                metal_fill_factor=0.60,
            ),
        )
    realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)
    centerline = build_tx_rect_void_centerline(realized)
    boxes = build_tx_rect_void_box_specs(realized)

    assert len(centerline) >= 2
    assert len([box for box in boxes if box.role == "pcb"]) == realized.layer_count
    assert _has_blunt_corner_segment(centerline)


def test_turn_count_above_supported_range_fails(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(turn_count=7))
    with pytest.raises(ValueError, match=r"tx_coil\.turn_count must resolve to \[1,6\]"):
        realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)


def test_step_scene_exports_single_fused_copper_body(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(turn_count=4, terminal_path="D_ccw_to_d"))
    realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)
    boxes = build_tx_rect_void_box_specs(realized)
    scene = build_tx_rect_void_step_scene(realized, boxes)

    assert len([box for box in boxes if box.role == "copper"]) > 1
    assert tuple(shape.label for shape in scene.children) == ("tx_pcb_l0", "tx_copper_l0")
    assert len(scene.solids()) == 2
    copper_bbox = _scene_child_by_label(scene, label="tx_copper_l0").bounding_box()
    assert copper_bbox.min.Z == pytest.approx(-realized.terminal_stub_length_mm)
    assert copper_bbox.max.Z == pytest.approx(realized.pcb_thickness_mm + realized.copper_thickness_mm)
    _assert_port_sheet_is_metadata_only(scene=scene, profile=TX_SINGLE_COIL_PROFILE)
    _assert_zero_intersection_volume(
        _scene_child_by_label(scene, label="tx_pcb_l0"),
        _scene_child_by_label(scene, label="tx_copper_l0"),
    )


def test_rx_step_scene_exports_single_fused_copper_body_for_notebook_scale_geometry(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _spec_text(
            terminal_path="D_ccw_to_d",
            outer_x=318.6671250920941,
            outer_y=104.169329765159,
            turn_count=3,
            layer_count=1,
        ),
    )
    realized = realize_tx_rect_void_spec(
        load_tx_rect_void_spec(toml_path),
        seed=0,
        profile=RX_SINGLE_COIL_PROFILE,
    )
    boxes = build_tx_rect_void_box_specs(realized, profile=RX_SINGLE_COIL_PROFILE)
    scene = build_tx_rect_void_step_scene(
        realized,
        boxes,
        profile=RX_SINGLE_COIL_PROFILE,
    )

    assert len([box for box in boxes if box.role == "copper"]) > 1
    assert tuple(shape.label for shape in scene.children) == ("rx_pcb_l0", "rx_copper_l0")
    assert len(scene.solids()) == 2
    _assert_port_sheet_is_metadata_only(scene=scene, profile=RX_SINGLE_COIL_PROFILE)
    _assert_zero_intersection_volume(
        _scene_child_by_label(scene, label="rx_pcb_l0"),
        _scene_child_by_label(scene, label="rx_copper_l0"),
    )


def test_box_decomposition_keeps_planar_outline_and_adds_terminal_stubs(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(turn_count=2, terminal_path="D_ccw_to_d"))
    realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)
    boxes = build_tx_rect_void_box_specs(realized)
    stub_boxes = [box for box in boxes if box.feature == "terminal_stub"]
    planar_copper_boxes = [box for box in boxes if box.role == "copper" and box.feature == "planar_outline"]

    assert len(stub_boxes) == 2
    assert len(planar_copper_boxes) == 1
    assert all(box.origin_xyz[2] == pytest.approx(realized.pcb_thickness_mm) for box in planar_copper_boxes)
    assert all(box.size_xyz[2] == pytest.approx(realized.copper_thickness_mm) for box in planar_copper_boxes)
    assert all(box.size_xyz[0] == pytest.approx(realized.trace_width_mm * 0.60) for box in stub_boxes)
    assert all(box.size_xyz[1] == pytest.approx(realized.trace_width_mm * 0.60) for box in stub_boxes)
    assert all(box.origin_xyz[2] == pytest.approx(-realized.terminal_stub_length_mm) for box in stub_boxes)
    assert all(
        box.size_xyz[2]
        == pytest.approx(realized.terminal_stub_length_mm + realized.pcb_thickness_mm + realized.copper_thickness_mm)
        for box in stub_boxes
    )


@pytest.mark.parametrize("terminal_path", ("D_ccw_to_d",))
@pytest.mark.parametrize("profile_name", ("tx", "rx"))
def test_step_scene_cuts_pcb_volume_out_of_copper_for_supported_profiles(
    tmp_path: Path,
    terminal_path: str,
    profile_name: str,
) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(turn_count=3, terminal_path=terminal_path))
    realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)
    if profile_name == "tx":
        boxes = build_tx_rect_void_box_specs(realized)
        scene = build_tx_rect_void_step_scene(realized, boxes)
    else:
        boxes = build_tx_rect_void_box_specs(realized, profile=RX_SINGLE_COIL_PROFILE)
        scene = build_tx_rect_void_step_scene(realized, boxes, profile=RX_SINGLE_COIL_PROFILE)

    assert tuple(shape.label for shape in scene.children) in (
        ("tx_pcb_l0", "tx_copper_l0"),
        ("rx_pcb_l0", "rx_copper_l0"),
    )
    if profile_name == "tx":
        _assert_port_sheet_is_metadata_only(scene=scene, profile=TX_SINGLE_COIL_PROFILE)
        _assert_zero_intersection_volume(
            _scene_child_by_label(scene, label="tx_pcb_l0"),
            _scene_child_by_label(scene, label="tx_copper_l0"),
        )
    else:
        _assert_port_sheet_is_metadata_only(scene=scene, profile=RX_SINGLE_COIL_PROFILE)
        _assert_zero_intersection_volume(
            _scene_child_by_label(scene, label="rx_pcb_l0"),
            _scene_child_by_label(scene, label="rx_copper_l0"),
        )


def test_same_corner_terminal_path_seeds_outer_terminal_to_next_ring(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(turn_count=4, terminal_path="D_ccw_to_d"))
    realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)
    centerline = build_tx_rect_void_centerline(realized)
    outer_corner_x = realized.outer_bounds.min_x + (realized.trace_width_mm / 2.0)

    assert centerline[0][0] != pytest.approx(outer_corner_x)
    assert centerline[0][0] > outer_corner_x
    assert len(centerline) == len(set(centerline))
    assert _has_blunt_corner_segment(centerline)


def test_outline_box_matches_planar_outline_bounds(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(turn_count=2, terminal_path="D_ccw_to_d"))
    realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)
    centerline = build_tx_rect_void_centerline(realized)
    boxes = build_tx_rect_void_box_specs(realized)
    first_copper_box = _copper_boxes(boxes)[0]
    first_bounds = _box_xy_bounds(first_copper_box)
    copper_primitives = _copper_primitives_for_layer(
        realized=realized,
        centerline=centerline,
        layer_index=0,
        pcb_z=0.0,
        profile=TX_SINGLE_COIL_PROFILE,
    )
    planar_primitive_bounds = tuple(
        _polygon_bounds(primitive.polygon_xy)
        for primitive in copper_primitives
        if primitive.feature == "planar_segment"
    )
    expected_bounds = RectBounds(
        min_x=min(bound.min_x for bound in planar_primitive_bounds),
        max_x=max(bound.max_x for bound in planar_primitive_bounds),
        min_y=min(bound.min_y for bound in planar_primitive_bounds),
        max_y=max(bound.max_y for bound in planar_primitive_bounds),
    )

    assert first_bounds.min_x == pytest.approx(expected_bounds.min_x)
    assert first_bounds.max_x == pytest.approx(expected_bounds.max_x)
    assert first_bounds.min_y == pytest.approx(expected_bounds.min_y)
    assert first_bounds.max_y == pytest.approx(expected_bounds.max_y)


@pytest.mark.parametrize("profile_name", ("tx", "rx"))
def test_layer_primitives_keep_single_joined_segment_authoring_path(
    tmp_path: Path,
    profile_name: str,
) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(turn_count=3, terminal_path="D_ccw_to_d"))
    if profile_name == "tx":
        profile = TX_SINGLE_COIL_PROFILE
        realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)
    else:
        profile = RX_SINGLE_COIL_PROFILE
        realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0, profile=RX_SINGLE_COIL_PROFILE)
    centerline = build_tx_rect_void_centerline(realized)
    primitives = _copper_primitives_for_layer(
        realized=realized,
        centerline=centerline,
        layer_index=0,
        pcb_z=0.0,
        profile=profile,
    )

    assert {primitive.feature for primitive in primitives} == {"planar_segment", "terminal_stub"}
    assert sum(1 for primitive in primitives if primitive.feature == "planar_segment") == len(centerline) - 1
    assert sum(1 for primitive in primitives if primitive.feature == "terminal_stub") == 2


@pytest.mark.parametrize("terminal_path", ("D_ccw_to_d", "A_cw_to_a"))
@pytest.mark.parametrize("profile_name", ("tx", "rx"))
def test_planar_outline_join_uses_offset_intersection_without_notch(
    tmp_path: Path,
    terminal_path: str,
    profile_name: str,
) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(turn_count=3, terminal_path=terminal_path))
    if profile_name == "tx":
        realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)
    else:
        realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0, profile=RX_SINGLE_COIL_PROFILE)
    centerline = build_tx_rect_void_centerline(realized)
    first_segment_polygon = _segment_joined_polygon(
        centerline,
        trace_width_mm=realized.trace_width_mm,
        segment_index=0,
    )
    second_segment_polygon = _segment_joined_polygon(
        centerline,
        trace_width_mm=realized.trace_width_mm,
        segment_index=1,
    )
    incoming_dx = centerline[1][0] - centerline[0][0]
    incoming_dy = centerline[1][1] - centerline[0][1]
    outgoing_dx = centerline[2][0] - centerline[1][0]
    outgoing_dy = centerline[2][1] - centerline[1][1]
    turn_cross = (incoming_dx * outgoing_dy) - (incoming_dy * outgoing_dx)
    if turn_cross > 0.0:
        convex_side = "right"
    else:
        convex_side = "left"
    join_point = _offset_join_point(centerline, trace_width_mm=realized.trace_width_mm, vertex_index=1, side=convex_side)
    naive_in = _naive_offset_vertex(
        centerline,
        trace_width_mm=realized.trace_width_mm,
        vertex_index=1,
        incoming=True,
        side=convex_side,
    )
    naive_out = _naive_offset_vertex(
        centerline,
        trace_width_mm=realized.trace_width_mm,
        vertex_index=1,
        incoming=False,
        side=convex_side,
    )

    assert _polygon_has_vertex(first_segment_polygon, join_point) or _polygon_has_vertex(second_segment_polygon, join_point)
    assert _point_distance_2d(join_point, naive_in) > 1e-6
    assert _point_distance_2d(join_point, naive_out) > 1e-6


def test_layer_gap_below_minimum_fails(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(layer_gap=1.9))

    with pytest.raises(ValueError, match=r"tx_coil\.layer_gap_mm must be >= 2\.0"):
        realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)


def test_tx_multilayer_coil_builds_per_layer_bodies_and_union_bounds(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _spec_text(layer_count=2, layer_gap=2.5, terminal_stub_length=99.0, turn_count=2),
    )

    realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)
    boxes = build_tx_rect_void_box_specs(realized)
    pcb_boxes = _pcb_boxes(boxes)
    copper_boxes = _copper_boxes(boxes)
    start_bus_box = _box_by_label(boxes, label="tx_copper_bus_start")
    end_bus_box = _box_by_label(boxes, label="tx_copper_bus_end")
    expected_top_z = (
        float(realized.layer_count - 1) * (realized.pcb_thickness_mm + realized.layer_gap_mm)
        + realized.pcb_thickness_mm
        + realized.copper_thickness_mm
    )
    modeled_min_xyz, modeled_max_xyz, modeled_size_xyz = modeled_body_bounds_from_boxes(boxes)

    assert realized.layer_count == 2
    assert realized.terminal_stub_length_mm == pytest.approx(realized.layer_gap_mm * 0.8)
    assert tuple(box.label for box in pcb_boxes) == ("tx_pcb_l0", "tx_pcb_l1")
    assert len(pcb_boxes) == realized.layer_count
    assert {box.layer_index for box in copper_boxes} == {0, 1}
    assert start_bus_box.origin_xyz[2] == pytest.approx(-realized.terminal_stub_length_mm)
    assert end_bus_box.origin_xyz[2] == pytest.approx(-realized.terminal_stub_length_mm)
    assert start_bus_box.size_xyz[2] == pytest.approx(expected_top_z + realized.terminal_stub_length_mm)
    assert end_bus_box.size_xyz[2] == pytest.approx(expected_top_z + realized.terminal_stub_length_mm)
    assert modeled_min_xyz[2] == pytest.approx(-realized.terminal_stub_length_mm)
    assert modeled_max_xyz[2] == pytest.approx(expected_top_z)
    assert modeled_size_xyz[2] == pytest.approx(expected_top_z + realized.terminal_stub_length_mm)
 

@pytest.mark.parametrize("layer_count", (2, 3))
def test_tx_multilayer_step_scene_exports_only_modeled_bodies(tmp_path: Path, layer_count: int) -> None:
    toml_path = _write_spec(
        tmp_path,
        _spec_text(layer_count=layer_count, layer_gap=2.5, terminal_stub_length=99.0, turn_count=2),
    )

    realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)
    boxes = build_tx_rect_void_box_specs(realized)
    scene = build_tx_rect_void_step_scene(realized, boxes)

    assert tuple(shape.label for shape in scene.children) == tuple(
        [f"tx_pcb_l{index}" for index in range(layer_count)] + ["tx_copper_stack"]
    )
    _assert_port_sheet_is_metadata_only(scene=scene, profile=TX_SINGLE_COIL_PROFILE)


@pytest.mark.parametrize("layer_count", (2, 3))
def test_tx_multilayer_export_writes_only_modeled_step_bodies(tmp_path: Path, layer_count: int) -> None:
    toml_path = _write_spec(
        tmp_path,
        _spec_text(layer_count=layer_count, layer_gap=2.5, terminal_stub_length=99.0, turn_count=2),
    )
    output_step_path = tmp_path / "out" / "tx_rect_void_multilayer.step"
    metadata_path = tmp_path / "out" / "tx_rect_void_multilayer.metadata.json"

    export_tx_rect_void_step(
        toml_path=toml_path,
        output_step_path=output_step_path,
        metadata_path=metadata_path,
        seed=0,
    )

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["expected_exported_body_names"] == [f"tx_pcb_l{index}" for index in range(layer_count)] + [
        "tx_copper_stack",
    ]
    imported_scene = bd.import_step(output_step_path)
    assert tuple(child.label for child in imported_scene.children) == tuple(payload["expected_exported_body_names"])


@pytest.mark.parametrize("layer_count", (2, 3))
def test_rx_multilayer_coil_still_fails(tmp_path: Path, layer_count: int) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(layer_count=layer_count, layer_gap=2.5))

    with pytest.raises(ValueError, match=r"rx_single_coil\.layer_count must resolve to 1"):
        realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0, profile=RX_SINGLE_COIL_PROFILE)


def test_export_writes_step_and_metadata(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(layer_count=1, turn_count=1))
    output_step_path = tmp_path / "out" / "tx_rect_void.step"
    metadata_path = tmp_path / "out" / "tx_rect_void.metadata.json"

    result = export_tx_rect_void_step(
        toml_path=toml_path,
        output_step_path=output_step_path,
        metadata_path=metadata_path,
        seed=0,
    )

    assert output_step_path.stat().st_size > 0
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["output_step_path"] == str(output_step_path)
    assert payload["realized"]["turn_count"] == 1
    assert payload["expected_exported_body_names"] == ["tx_pcb_l0", "tx_copper_l0"]
    assert payload["expected_exported_body_count"] == 2
    assert len(payload["boxes"]) == len(result.boxes)
    assert len(payload["modeled_objects"]) == 1
    modeled_object = payload["modeled_objects"][0]
    assert modeled_object["object_id"] == "tx_rect_void_coil"
    assert modeled_object["role"] == "tx_single_coil"
    assert modeled_object["plane"] == "XY"
    assert modeled_object["placement_owner_id"] == "tx_region"
    assert modeled_object["material"] == "composite"
    assert modeled_object["model_state"] is True
    assert modeled_object["step_path"] == str(output_step_path)
    assert modeled_object["expected_exported_body_names"] == ["tx_pcb_l0", "tx_copper_l0"]
    assert modeled_object["expected_exported_body_count"] == 2
    assert modeled_object["canonical_coordinates"]["frame_origin_xyz"] == [0.0, 0.0, 0.0]
    expected_min_xyz, expected_max_xyz, expected_size_xyz = modeled_body_bounds_from_boxes(result.boxes)
    assert modeled_object["canonical_coordinates"]["outer_bounds_min_xyz"] == pytest.approx(expected_min_xyz)
    assert modeled_object["canonical_coordinates"]["outer_bounds_max_xyz"] == pytest.approx(expected_max_xyz)
    assert modeled_object["canonical_coordinates"]["outer_bounds_size_xyz"] == pytest.approx(expected_size_xyz)
    assert modeled_object["canonical_coordinates"]["outer_bounds_min_xyz"][2] == pytest.approx(
        -result.realized.terminal_stub_length_mm
    )
    assert modeled_object["canonical_coordinates"]["outer_bounds_size_xyz"][2] == pytest.approx(
        result.realized.terminal_stub_length_mm
        + result.realized.pcb_thickness_mm
        + result.realized.copper_thickness_mm
    )
    assert modeled_object["terminal_metadata"]["path"] == result.realized.terminal_path
    assert modeled_object["terminal_metadata"]["start_point_plane_mm"]
    assert modeled_object["terminal_metadata"]["end_point_plane_mm"]
    imported_scene = bd.import_step(output_step_path)
    assert tuple(child.label for child in imported_scene.children) == tuple(payload["expected_exported_body_names"])


def test_export_from_spec_applies_placement_offset_to_boxes_and_metadata(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(layer_count=1, turn_count=1))
    spec = load_tx_rect_void_spec(toml_path)
    output_step_path = tmp_path / "out" / "tx_rect_void_offset.step"
    metadata_path = tmp_path / "out" / "tx_rect_void_offset.metadata.json"
    local_result = export_tx_rect_void_step_from_spec(
        spec=spec,
        source_toml_path=toml_path,
        output_step_path=tmp_path / "out" / "tx_rect_void_local.step",
        metadata_path=tmp_path / "out" / "tx_rect_void_local.metadata.json",
        seed=0,
    )

    result = export_tx_rect_void_step_from_spec(
        spec=spec,
        source_toml_path=toml_path,
        output_step_path=output_step_path,
        metadata_path=metadata_path,
        seed=0,
        placement_offset_xyz=(10.0, 20.0, 30.0),
    )

    modeled_object = result.modeled_objects[0]
    assert result.boxes[0].origin_xyz[2] >= 30.0
    assert modeled_object.canonical_coordinates.frame_origin_xyz == (10.0, 20.0, 30.0)
    assert modeled_object.canonical_coordinates.outer_bounds_min_xyz[2] == pytest.approx(
        30.0 - local_result.realized.terminal_stub_length_mm
    )
    assert modeled_object.terminal_metadata.start_point_plane_mm == pytest.approx(
        (
            local_result.modeled_objects[0].terminal_metadata.start_point_plane_mm[0] + 10.0,
            local_result.modeled_objects[0].terminal_metadata.start_point_plane_mm[1] + 20.0,
        )
    )


def test_export_smoke_uses_example_spec_and_writes_registry_aligned_metadata(tmp_path: Path) -> None:
    example_toml = _write_spec(tmp_path, _spec_text(layer_count=2, turn_count=6, terminal_path="D_ccw_to_d"))
    output_step_path = tmp_path / "cli" / "tx_rect_void.step"
    metadata_path = tmp_path / "cli" / "tx_rect_void.metadata.json"

    export_tx_rect_void_step(
        toml_path=example_toml,
        output_step_path=output_step_path,
        metadata_path=metadata_path,
        seed=0,
    )

    assert output_step_path.stat().st_size > 0
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["source_toml_path"] == str(example_toml)
    assert payload["output_step_path"] == str(output_step_path)
    assert len(payload["modeled_objects"]) == 1
    modeled_object = payload["modeled_objects"][0]
    assert modeled_object["object_id"] == "tx_rect_void_coil"
    assert modeled_object["role"] == "tx_single_coil"
    assert modeled_object["terminal_metadata"]["path"] == "D_ccw_to_d"
    layer_count = len(modeled_object["canonical_coordinates"]["pcb_layer_z_positions_mm"])
    expected_prefix = [f"tx_pcb_l{index}" for index in range(layer_count)]
    expected_prefix.append("tx_copper_stack" if layer_count > 1 else "tx_copper_l0")
    actual_expected_names = payload["expected_exported_body_names"]
    assert actual_expected_names[: len(expected_prefix)] == expected_prefix
    assert "tx_port_sheet" not in actual_expected_names
    assert payload["expected_exported_body_count"] == len(actual_expected_names)

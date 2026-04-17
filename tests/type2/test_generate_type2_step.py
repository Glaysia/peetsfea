from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from typing import cast

import build123d as bd
import pytest

from entry.generate_type2_step import export_type2_step_artifacts
from entry.generate_type2_step import load_type2_step_spec
from peetsfea.tx_rect_void import BoxSpec
from peetsfea.tx_rect_void import build_tx_rect_void_box_specs
from peetsfea.tx_rect_void import build_tx_rect_void_centerline
from peetsfea.tx_rect_void import load_tx_rect_void_spec
from peetsfea.tx_rect_void import modeled_body_bounds_from_boxes
from peetsfea.tx_rect_void import profile_for_modeled_role
from peetsfea.tx_rect_void import realize_tx_rect_void_spec
from peetsfea.type2_step_spec import render_tx_rect_void_toml
from peetsfea.type2_step_spec import resolve_modeled_underlay_repeat_count

_TX_UNDERLAY_FERRITE_THICKNESS_MM = 0.20
_TX_UNDERLAY_PET_PSA_THICKNESS_MM = 0.15
_TX_UNDERLAY_AIR_THICKNESS_MM = 0.02


def _range(is_integer: bool, start: float, end: float, count: int) -> str:
    flag = "true" if is_integer else "false"
    return f"[{flag}, {start}, {end}, {count}]"


def _type2_spec_text(
    *,
    modeled_object_id: str = "tx_rect_void_coil",
    modeled_role: str = "tx_single_coil",
    terminal_path: str = "A_cw_to_a",
    layer_count: int = 1,
    radiation_margin_mm: float = 3500.0,
    underlay_repeat_count_range: str | None = None,
) -> str:
    if underlay_repeat_count_range is None:
        if modeled_role == "tx_single_coil":
            underlay_repeat_count_range = _range(True, 0.0, 8.0, 5)
        else:
            underlay_repeat_count_range = _range(True, 0.0, 0.0, 1)
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.type2.step.v1"
runtime_compatible = false

[design]
units = "mm"

[simulation]
radiation_margin_mm = {radiation_margin_mm}

[[non_model_objects]]
id = "floor"
kind = "floor"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "XY"
origin_xyz = [0.0, -10.0, -1.0]
size_xyz = [20.0, 20.0, 1.0]

[[non_model_objects]]
id = "shelf"
kind = "shelf"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "XY"
origin_xyz = [0.0, -10.0, 0.0]
size_xyz = [10.0, 20.0, 4.0]

[[non_model_objects]]
id = "wall"
kind = "wall"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [-1.0, -10.0, 0.0]
size_xyz = [1.0, 20.0, 10.0]

[[non_model_objects]]
id = "tv"
kind = "tv"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [0.0, -5.0, 5.0]
size_xyz = [1.0, 10.0, 4.0]

[[non_model_objects]]
id = "tx_region"
kind = "tx_region"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "XY"
origin_xyz = [0.0, -140.0, 0.0]
size_xyz = [160.0, 280.0, 90.0]

[[non_model_objects]]
id = "rx_region_max"
kind = "rx_region_max"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [200.0, -100.0, 0.0]
size_xyz = [10.0, 200.0, 200.0]

[[modeled_objects]]
object_id = "{modeled_object_id}"
role = "{modeled_role}"
material = "composite"
model_state = true
pcb_thickness_mm = 1.6
copper_thickness_mm = 0.1

[modeled_objects.outer_x_mm]
range = {_range(False, 50.0, 50.0, 1)}
[modeled_objects.outer_y_mm]
range = {_range(False, 60.0, 60.0, 1)}
[modeled_objects.turn_count]
range = {_range(True, 2.0, 2.0, 1)}
[modeled_objects.layer_count]
range = {_range(True, float(layer_count), float(layer_count), 1)}
[modeled_objects.underlay_repeat_count]
range = {underlay_repeat_count_range}
[modeled_objects.layer_gap_mm]
range = {_range(False, 2.0, 2.0, 1)}
[modeled_objects.terminal_stub_length_mm]
range = {_range(False, 5.0, 5.0, 1)}
[modeled_objects.void_x_over_outer_x]
range = {_range(False, 0.3, 0.3, 1)}
[modeled_objects.void_y_over_outer_y]
range = {_range(False, 0.3, 0.3, 1)}
[modeled_objects.void_center_x_over_outer_x]
range = {_range(False, 0.0, 0.0, 1)}
[modeled_objects.void_center_y_over_outer_y]
range = {_range(False, 0.0, 0.0, 1)}
[modeled_objects.margin_ratio]
range = {_range(False, 0.05, 0.05, 1)}
[modeled_objects.metal_fill_factor]
range = {_range(False, 0.5, 0.5, 1)}
[modeled_objects.terminal_path]
value = "{terminal_path}"
""".strip()


def _tx_rect_void_spec_text(*, terminal_path: str = "A_cw_to_a") -> str:
    return _tx_rect_void_spec_text_with_layer_count(terminal_path=terminal_path, layer_count=1)


def _tx_rect_void_spec_text_with_layer_count(*, terminal_path: str = "A_cw_to_a", layer_count: int = 1) -> str:
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
range = {_range(False, 50.0, 50.0, 1)}
[tx_coil.outer_y_mm]
range = {_range(False, 60.0, 60.0, 1)}
[tx_coil.turn_count]
range = {_range(True, 2.0, 2.0, 1)}
[tx_coil.layer_count]
range = {_range(True, float(layer_count), float(layer_count), 1)}
[tx_coil.layer_gap_mm]
range = {_range(False, 2.0, 2.0, 1)}
[tx_coil.terminal_stub_length_mm]
range = {_range(False, 5.0, 5.0, 1)}
[tx_coil.void_x_over_outer_x]
range = {_range(False, 0.3, 0.3, 1)}
[tx_coil.void_y_over_outer_y]
range = {_range(False, 0.3, 0.3, 1)}
[tx_coil.void_center_x_over_outer_x]
range = {_range(False, 0.0, 0.0, 1)}
[tx_coil.void_center_y_over_outer_y]
range = {_range(False, 0.0, 0.0, 1)}
[tx_coil.margin_ratio]
range = {_range(False, 0.05, 0.05, 1)}
[tx_coil.metal_fill_factor]
range = {_range(False, 0.5, 0.5, 1)}
[tx_coil.terminal_path]
value = "{terminal_path}"
""".strip()


def _write_spec(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "type2_fixed.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _single_layer_example_text(source_toml: Path) -> str:
    return source_toml.read_text(encoding="utf-8").replace(
        "[modeled_objects.layer_count]\nrange = [true, 2, 2, 1]",
        "[modeled_objects.layer_count]\nrange = [true, 1, 1, 1]",
        1,
    )


def _body_bbox(step_path: Path, *, label: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    shape = bd.import_step(step_path)
    children = tuple(shape.children) if tuple(shape.children) else (shape,)
    matches = [child for child in children if child.label == label]
    assert len(matches) == 1
    bbox = matches[0].bounding_box()
    return ((bbox.min.X, bbox.min.Y, bbox.min.Z), (bbox.max.X, bbox.max.Y, bbox.max.Z))


def _tx_underlay_expected_body_names(*, repeat_count: int) -> tuple[str, ...]:
    body_names: list[str] = []
    for unit_index in range(repeat_count):
        body_names.extend(
            (
                f"tx_underlay_ferrite_u{unit_index}",
                f"tx_underlay_pet_psa_u{unit_index}",
                f"tx_underlay_air_u{unit_index}",
            )
        )
    return tuple(body_names)


def _tx_expected_body_names(*, pcb_layer_count: int, underlay_repeat_count: int) -> tuple[str, ...]:
    names = [f"tx_pcb_l{index}" for index in range(pcb_layer_count)]
    if pcb_layer_count > 1:
        names.append("tx_copper_stack")
    else:
        names.append("tx_copper_l0")
    names.extend(_tx_underlay_expected_body_names(repeat_count=underlay_repeat_count))
    return tuple(names)


def _seed_for_underlay_repeat_count(spec_path: Path, *, object_id: str, expected_repeat_count: int) -> int:
    spec = load_type2_step_spec(spec_path)
    modeled_spec = next(entry for entry in spec.modeled_objects if entry.object_id == object_id)
    for seed in range(512):
        if resolve_modeled_underlay_repeat_count(modeled_spec, seed=seed) == expected_repeat_count:
            return seed
    raise RuntimeError(
        "failed to find deterministic seed for requested underlay repeat count "
        f"(object_id={object_id}, expected_repeat_count={expected_repeat_count})"
    )


def _assert_zero_intersection_volume(first: object, second: object) -> None:
    assert isinstance(first, bd.Shape)
    assert isinstance(second, bd.Shape)
    shared_shape = first.intersect(second)
    if shared_shape is None:
        return
    assert isinstance(shared_shape, bd.Shape)
    assert shared_shape.volume == pytest.approx(0.0, abs=1e-9)


def _single_coil_placement_offset_from_local_bounds(
    *,
    owner_origin_xyz: tuple[float, float, float],
    owner_size_xyz: tuple[float, float, float],
    local_bounds_min_xyz: tuple[float, float, float],
    local_size_xyz: tuple[float, float, float],
    profile: object,
) -> tuple[float, float, float]:
    assert hasattr(profile, "plane")
    assert hasattr(profile, "world_size")
    assert hasattr(profile, "world_delta")
    plane = profile.plane
    world_size_xyz = profile.world_size(local_size_xyz)
    world_min_delta = profile.world_delta(local_bounds_min_xyz)
    if plane == "XY":
        target_world_min_xyz = (
            owner_origin_xyz[0] + (owner_size_xyz[0] - world_size_xyz[0]) / 2.0,
            owner_origin_xyz[1] + (owner_size_xyz[1] - world_size_xyz[1]) / 2.0,
            owner_origin_xyz[2] + owner_size_xyz[2] - world_size_xyz[2],
        )
    else:
        target_world_min_xyz = (
            owner_origin_xyz[0] + owner_size_xyz[0] - world_size_xyz[0],
            owner_origin_xyz[1] + (owner_size_xyz[1] - world_size_xyz[1]) / 2.0,
            owner_origin_xyz[2],
        )
    return (
        target_world_min_xyz[0] - world_min_delta[0],
        target_world_min_xyz[1] - world_min_delta[1],
        target_world_min_xyz[2] - world_min_delta[2],
    )


def _transform_box_to_world(
    *,
    origin_xyz: tuple[float, float, float],
    size_xyz: tuple[float, float, float],
    frame_origin_xyz: tuple[float, float, float],
    profile: object,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    assert hasattr(profile, "world_point")
    assert hasattr(profile, "world_size")
    return (
        profile.world_point(origin_xyz, frame_origin_xyz=frame_origin_xyz),
        profile.world_size(size_xyz),
    )


def _synthetic_tx_bus_owner_boxes(
    *,
    local_boxes: tuple[BoxSpec, ...],
) -> tuple[BoxSpec, BoxSpec]:
    terminal_stub_boxes = tuple(box for box in local_boxes if box.feature == "terminal_stub")

    def _owner_box(terminal_column: str) -> BoxSpec:
        matching_stub_boxes = tuple(
            box for box in terminal_stub_boxes if box.label.endswith(f"_stub_{terminal_column}")
        )
        assert matching_stub_boxes
        assert len(matching_stub_boxes) * 2 == len(terminal_stub_boxes)
        min_x = min(box.origin_xyz[0] for box in matching_stub_boxes)
        min_y = min(box.origin_xyz[1] for box in matching_stub_boxes)
        min_z = min(box.origin_xyz[2] for box in matching_stub_boxes)
        max_x = max(box.origin_xyz[0] + box.size_xyz[0] for box in matching_stub_boxes)
        max_y = max(box.origin_xyz[1] + box.size_xyz[1] for box in matching_stub_boxes)
        max_z = max(box.origin_xyz[2] + box.size_xyz[2] for box in matching_stub_boxes)
        return BoxSpec(
            label=f"tx_copper_bus_{terminal_column}",
            role="copper",
            feature="vertical_bus",
            layer_index=0,
            origin_xyz=(min_x, min_y, min_z),
            size_xyz=(max_x - min_x, max_y - min_y, max_z - min_z),
        )

    return (_owner_box("start"), _owner_box("end"))


def _world_terminal_stub_boxes(
    *,
    source_toml: Path,
    object_id: str,
    seed: int,
) -> tuple[tuple[tuple[float, float, float], tuple[float, float, float]], ...]:
    type2_spec = load_type2_step_spec(source_toml)
    modeled_spec = next(entry for entry in type2_spec.modeled_objects if entry.object_id == object_id)
    profile = profile_for_modeled_role(modeled_spec.role)
    owner_spec = next(spec for spec in type2_spec.non_model_objects if spec.object_id == profile.placement_owner_id)
    with tempfile.TemporaryDirectory() as temp_dir:
        tx_rect_void_toml_path = Path(temp_dir) / f"{object_id}.toml"
        tx_rect_void_toml_path.write_text(render_tx_rect_void_toml(modeled_spec), encoding="utf-8")
        tx_rect_void_spec = load_tx_rect_void_spec(tx_rect_void_toml_path)
        realized = realize_tx_rect_void_spec(tx_rect_void_spec, seed=seed, profile=profile)
    local_boxes = build_tx_rect_void_box_specs(realized, profile=profile)
    local_bounds_min_xyz, _local_bounds_max_xyz, local_size_xyz = modeled_body_bounds_from_boxes(local_boxes)
    frame_origin_xyz = _single_coil_placement_offset_from_local_bounds(
        owner_origin_xyz=owner_spec.origin_xyz,
        owner_size_xyz=owner_spec.size_xyz,
        local_bounds_min_xyz=local_bounds_min_xyz,
        local_size_xyz=local_size_xyz,
        profile=profile,
    )
    if profile.role == "tx_single_coil":
        terminal_stub_boxes = _synthetic_tx_bus_owner_boxes(local_boxes=local_boxes)
    else:
        terminal_stub_boxes = tuple(box for box in local_boxes if box.feature == "terminal_stub")
    return tuple(
        _transform_box_to_world(
            origin_xyz=box.origin_xyz,
            size_xyz=box.size_xyz,
            frame_origin_xyz=frame_origin_xyz,
            profile=profile,
        )
        for box in terminal_stub_boxes
    )


def _shape_vertices(step_path: Path, *, label: str) -> tuple[tuple[float, float, float], ...]:
    shape = bd.import_step(step_path)
    children = tuple(shape.children) if tuple(shape.children) else (shape,)
    matches = [child for child in children if child.label == label]
    assert len(matches) == 1
    unique_vertices: dict[tuple[float, float, float], tuple[float, float, float]] = {}
    for vertex in matches[0].vertices():
        rounded = (round(vertex.X, 8), round(vertex.Y, 8), round(vertex.Z, 8))
        if rounded not in unique_vertices:
            unique_vertices[rounded] = (vertex.X, vertex.Y, vertex.Z)
    return tuple(unique_vertices.values())


def _terminal_stub_bottom_face_square_plane_vertices(
    *,
    terminal_stub_boxes: tuple[tuple[tuple[float, float, float], tuple[float, float, float]], ...],
    plane: str,
) -> tuple[tuple[tuple[tuple[float, float], ...], float], tuple[tuple[tuple[float, float], ...], float]]:
    assert len(terminal_stub_boxes) == 2
    boxes_by_plane: list[tuple[tuple[tuple[float, float], ...], float]] = []
    for box_origin_xyz, box_size_xyz in terminal_stub_boxes:
        if plane == "XY":
            square_side_a = box_size_xyz[0]
            square_side_b = box_size_xyz[1]
            bottom_plane_coordinate = box_origin_xyz[2]
            plane_vertices = (
                (box_origin_xyz[0], box_origin_xyz[1]),
                (box_origin_xyz[0] + box_size_xyz[0], box_origin_xyz[1]),
                (box_origin_xyz[0] + box_size_xyz[0], box_origin_xyz[1] + box_size_xyz[1]),
                (box_origin_xyz[0], box_origin_xyz[1] + box_size_xyz[1]),
            )
        else:
            square_side_a = box_size_xyz[1]
            square_side_b = box_size_xyz[2]
            bottom_plane_coordinate = box_origin_xyz[0]
            plane_vertices = (
                (box_origin_xyz[1], box_origin_xyz[2]),
                (box_origin_xyz[1] + box_size_xyz[1], box_origin_xyz[2]),
                (box_origin_xyz[1] + box_size_xyz[1], box_origin_xyz[2] + box_size_xyz[2]),
                (box_origin_xyz[1], box_origin_xyz[2] + box_size_xyz[2]),
            )
        assert square_side_a > 0.0
        assert square_side_b > 0.0
        assert square_side_a == pytest.approx(square_side_b, abs=1e-8)
        boxes_by_plane.append((plane_vertices, bottom_plane_coordinate))
    first_box, second_box = boxes_by_plane
    assert first_box[1] == pytest.approx(second_box[1], abs=1e-8)
    return (first_box, second_box)


def _stub_centerline_perpendicular_distance(
    *,
    point_xy: tuple[float, float],
    first_center_xy: tuple[float, float],
    second_center_xy: tuple[float, float],
) -> float:
    delta_x = second_center_xy[0] - first_center_xy[0]
    delta_y = second_center_xy[1] - first_center_xy[1]
    denominator = math.hypot(delta_x, delta_y)
    assert denominator > 1e-12
    numerator = abs(
        delta_x * (first_center_xy[1] - point_xy[1])
        - (first_center_xy[0] - point_xy[0]) * delta_y
    )
    return numerator / denominator


def _widest_stub_bottom_face_diagonal_vertices(
    *,
    terminal_stub_boxes: tuple[tuple[tuple[float, float, float], tuple[float, float, float]], ...],
    plane: str,
) -> tuple[tuple[float, float, float], ...]:
    first_box, second_box = _terminal_stub_bottom_face_square_plane_vertices(
        terminal_stub_boxes=terminal_stub_boxes,
        plane=plane,
    )
    first_plane_vertices, first_bottom_plane_coordinate = first_box
    second_plane_vertices, second_bottom_plane_coordinate = second_box
    first_center_xy = (
        sum(point_xy[0] for point_xy in first_plane_vertices) / 4.0,
        sum(point_xy[1] for point_xy in first_plane_vertices) / 4.0,
    )
    second_center_xy = (
        sum(point_xy[0] for point_xy in second_plane_vertices) / 4.0,
        sum(point_xy[1] for point_xy in second_plane_vertices) / 4.0,
    )

    def _selected_diagonal(
        plane_vertices: tuple[tuple[float, float], ...],
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        best_score = -1.0
        best_diagonal: tuple[tuple[float, float], tuple[float, float]] | None = None
        best_key: tuple[tuple[float, float], tuple[float, float]] | None = None
        for first_index, second_index in ((0, 2), (1, 3)):
            diagonal_vertices = (plane_vertices[first_index], plane_vertices[second_index])
            score = sum(
                _stub_centerline_perpendicular_distance(
                    point_xy=point_xy,
                    first_center_xy=first_center_xy,
                    second_center_xy=second_center_xy,
                )
                for point_xy in diagonal_vertices
            )
            candidate_key = tuple(sorted(diagonal_vertices))
            if (
                score > best_score + 1e-9
                or (abs(score - best_score) <= 1e-9 and (best_key is None or candidate_key < best_key))
            ):
                best_score = score
                best_diagonal = diagonal_vertices
                best_key = candidate_key
        assert best_diagonal is not None
        return best_diagonal

    diagonal_vertices: list[tuple[float, float, float]] = []
    for plane_vertices, bottom_plane_coordinate in (
        (first_plane_vertices, first_bottom_plane_coordinate),
        (second_plane_vertices, second_bottom_plane_coordinate),
    ):
        selected_diagonal = _selected_diagonal(plane_vertices)
        for point_u, point_v in selected_diagonal:
            if plane == "XY":
                diagonal_vertices.append((point_u, point_v, bottom_plane_coordinate))
            else:
                diagonal_vertices.append((bottom_plane_coordinate, point_u, point_v))
    return tuple(diagonal_vertices)


def _assert_sheet_vertices_bridge_stub_bottom_face_diagonals(
    *,
    sheet_vertices: tuple[tuple[float, float, float], ...],
    terminal_stub_boxes: tuple[tuple[tuple[float, float, float], tuple[float, float, float]], ...],
    plane: str,
) -> None:
    assert len(sheet_vertices) == 4
    expected_vertices = _widest_stub_bottom_face_diagonal_vertices(
        terminal_stub_boxes=terminal_stub_boxes,
        plane=plane,
    )
    if plane == "XY":
        plane_coordinates = tuple(vertex[2] for vertex in sheet_vertices)
    else:
        plane_coordinates = tuple(vertex[0] for vertex in sheet_vertices)
    assert max(plane_coordinates) - min(plane_coordinates) == pytest.approx(0.0, abs=1e-8)
    assert {
        (round(vertex[0], 8), round(vertex[1], 8), round(vertex[2], 8))
        for vertex in sheet_vertices
    } == {
        (round(vertex[0], 8), round(vertex[1], 8), round(vertex[2], 8))
        for vertex in expected_vertices
    }


def test_load_example_type2_toml_parses_expected_registry_shape() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_fixed.toml"
    spec = load_type2_step_spec(source_toml)

    assert spec.simulation.radiation_margin_mm == pytest.approx(3500.0)
    assert len(spec.non_model_objects) == 6
    assert len(spec.modeled_objects) == 2
    modeled_by_id = {entry.object_id: entry for entry in spec.modeled_objects}
    tx_entry = modeled_by_id["tx_rect_void_coil"]
    rx_entry = modeled_by_id["rx_rect_void_coil"]
    assert tx_entry.role == "tx_single_coil"
    assert tx_entry.outer_x_mm.start == pytest.approx(157.810110508654)
    assert tx_entry.outer_y_mm.end == pytest.approx(259.88256431122)
    assert tx_entry.turn_count.start == pytest.approx(2.0)
    assert tx_entry.terminal_stub_length_mm.start == pytest.approx(5.0)
    assert tx_entry.layer_count.end == pytest.approx(2.0)
    assert tx_entry.underlay_repeat_count.start == pytest.approx(0.0)
    assert tx_entry.underlay_repeat_count.end == pytest.approx(8.0)
    assert tx_entry.underlay_repeat_count.count == 5
    assert rx_entry.role == "rx_single_coil"
    assert rx_entry.outer_x_mm.start == pytest.approx(318.6671250920941)
    assert rx_entry.outer_y_mm.end == pytest.approx(104.169329765159)
    assert rx_entry.turn_count.start == pytest.approx(3.0)
    assert rx_entry.terminal_stub_length_mm.end == pytest.approx(5.0)
    assert rx_entry.underlay_repeat_count.start == pytest.approx(0.0)
    assert rx_entry.underlay_repeat_count.end == pytest.approx(0.0)
    assert rx_entry.underlay_repeat_count.count == 1


def test_load_type2_step_spec_rejects_duplicate_object_id(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(modeled_object_id="floor"))

    with pytest.raises(ValueError, match=r"duplicate object id: floor"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_unsupported_modeled_role(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(modeled_role="bad_single_coil"))

    with pytest.raises(ValueError, match=r"unsupported modeled object role: bad_single_coil"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_missing_required_modeled_field(tmp_path: Path) -> None:
    terminal_section_lines = {"[modeled_objects.terminal_path]", 'value = "A_cw_to_a"'}
    toml_text = "\n".join(line for line in _type2_spec_text().splitlines() if line not in terminal_section_lines)
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(ValueError, match=r"modeled_objects\[0\] is missing required key 'terminal_path'"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_non_canonical_tx_underlay_repeat_count(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(underlay_repeat_count_range=_range(True, 0.0, 6.0, 4)),
    )

    with pytest.raises(
        ValueError,
        match=r"modeled_objects\[0\]\.underlay_repeat_count\.range must be \[true, 0, 8, 5\] for tx_single_coil",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_non_zero_rx_underlay_repeat_count(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="rx_rect_void_coil",
            modeled_role="rx_single_coil",
            underlay_repeat_count_range=_range(True, 2.0, 2.0, 1),
        ),
    )

    with pytest.raises(
        ValueError,
        match=r"modeled_objects\[0\]\.underlay_repeat_count\.range must be \[true, 0, 0, 1\] for rx_single_coil",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_missing_simulation_radiation_margin(tmp_path: Path) -> None:
    toml_text = "\n".join(
        line for line in _type2_spec_text().splitlines() if line != "radiation_margin_mm = 3500.0"
    )
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(
        ValueError,
        match=r"type2_fixed\.toml\.simulation is missing required keys: \['radiation_margin_mm'\]",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_non_positive_simulation_radiation_margin(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(radiation_margin_mm=0.0))

    with pytest.raises(ValueError, match=r"type2_fixed\.toml\.simulation\.radiation_margin_mm must be > 0"):
        load_type2_step_spec(toml_path)


def test_render_tx_rect_void_toml_omits_underlay_repeat_count_from_core_bridge(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text())
    spec = load_type2_step_spec(toml_path)
    modeled_spec = next(entry for entry in spec.modeled_objects if entry.object_id == "tx_rect_void_coil")

    rendered = render_tx_rect_void_toml(modeled_spec)

    assert "underlay_repeat_count" not in rendered


def test_export_type2_step_artifacts_writes_single_scene_step_and_ledger(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_fixed.toml"
    type2_spec = load_type2_step_spec(source_toml)
    tx_modeled_spec = next(entry for entry in type2_spec.modeled_objects if entry.object_id == "tx_rect_void_coil")
    tx_underlay_repeat_count = resolve_modeled_underlay_repeat_count(tx_modeled_spec, seed=0)
    output_dir = tmp_path / "out"
    ledger_path = tmp_path / "out" / "type2_ledger.json"

    ledger = export_type2_step_artifacts(
        toml_path=source_toml,
        output_dir=output_dir,
        ledger_path=ledger_path,
        seed=0,
    )

    assert ledger_path.is_file()
    assert ledger_path.stat().st_size > 0
    scene_step_path = Path(ledger["scene_step_path"])
    assert scene_step_path.is_file()
    assert scene_step_path.stat().st_size > 0
    assert scene_step_path.name == "type2_scene.step"
    assert (output_dir / "type2_non_model_scene.step").exists() is False
    assert (output_dir / "type2_combined_preview.step").exists() is False
    assert (output_dir / "objects").exists() is False
    assert ledger["em_policy"] == {"radiation_margin_mm": 3500.0}
    assert len(ledger["non_model_objects"]) == 1
    assert len(ledger["modeled_objects"]) == 2
    non_model_entry = ledger["non_model_objects"][0]
    assert non_model_entry["object_id"] == "type2_non_model_scene"
    assert non_model_entry["role"] == "non_model_scene"
    assert non_model_entry["plane"] == "mixed"
    assert non_model_entry["member_object_ids"] == ("environment", "tx_region", "rx_region_max")
    member_objects = non_model_entry["member_objects"]
    assert len(member_objects) == 3
    environment_member = next(member for member in member_objects if member["object_id"] == "environment")
    assert environment_member["role"] == "environment"
    assert environment_member["plane"] == "mixed"
    assert environment_member["canonical_coordinates"]["outer_bounds_min_xyz"] == (-200.0, -2500.0, -761.0)
    assert environment_member["canonical_coordinates"]["outer_bounds_size_xyz"] == (5200.0, 5000.0, 3300.0)
    tx_region_member = next(member for member in member_objects if member["object_id"] == "tx_region")
    assert tx_region_member["role"] == "tx_region"
    assert tx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"] == (0.0, -140.0, 0.0)
    assert tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"] == (160.0, 280.0, 90.0)
    rx_region_member = next(member for member in member_objects if member["object_id"] == "rx_region_max")
    assert rx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"] == (0.0, -280.0, 139.0)
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert payload["scene_step_path"] == str(scene_step_path)
    assert payload["em_policy"] == {"radiation_margin_mm": 3500.0}
    modeled_by_id = {entry["object_id"]: entry for entry in payload["modeled_objects"]}
    assert set(modeled_by_id) == {"tx_rect_void_coil", "rx_rect_void_coil"}
    for modeled_entry in ledger["modeled_objects"]:
        source_metadata_path = Path(modeled_entry["source_metadata_path"])
        assert source_metadata_path.is_file()
        source_metadata_payload = json.loads(source_metadata_path.read_text(encoding="utf-8"))
        assert source_metadata_payload["source_toml_path"] == str(source_toml)
        assert source_metadata_payload["scene_step_path"] == str(scene_step_path)
    tx_entry = modeled_by_id["tx_rect_void_coil"]
    assert tx_entry["role"] == "tx_single_coil"
    assert tx_entry["plane"] == "XY"
    assert tx_entry["placement_owner_id"] == "tx_region"
    assert tx_entry["terminal_metadata"]["path"] == "D_ccw_to_d"
    tx_port_sheet_vertices = tuple(tuple(vertex) for vertex in tx_entry["terminal_metadata"]["port_sheet_vertices_xyz"])
    assert len(tx_port_sheet_vertices) == 4
    tx_expected_names = list(
        _tx_expected_body_names(
            pcb_layer_count=len(tx_entry["canonical_coordinates"]["pcb_layer_z_positions_mm"]),
            underlay_repeat_count=tx_underlay_repeat_count,
        )
    )
    assert tx_entry["expected_exported_body_names"] == tx_expected_names
    assert tx_entry["expected_exported_body_count"] == len(tx_expected_names)
    modeled_canonical = tx_entry["canonical_coordinates"]
    tx_min_x, tx_min_y, tx_min_z = modeled_canonical["outer_bounds_min_xyz"]
    tx_size_x, tx_size_y, tx_size_z = modeled_canonical["outer_bounds_size_xyz"]
    region_min_x, region_min_y, region_min_z = tx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    region_size_x, region_size_y, _region_size_z = tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"]
    assert tx_min_x == pytest.approx(region_min_x + (region_size_x - tx_size_x) / 2.0)
    assert tx_min_y == pytest.approx(region_min_y + (region_size_y - tx_size_y) / 2.0)
    assert tx_min_z == pytest.approx(region_min_z + tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"][2] - tx_size_z)
    assert modeled_canonical["outer_bounds_min_xyz"][1] + (tx_size_y / 2.0) == pytest.approx(0.0)
    tx_copper_label = "tx_copper_stack" if len(tx_entry["canonical_coordinates"]["pcb_layer_z_positions_mm"]) > 1 else "tx_copper_l0"
    tx_step_min_xyz, tx_step_max_xyz = _body_bbox(scene_step_path, label=tx_copper_label)
    tx_region_center_x = region_min_x + (region_size_x / 2.0)
    tx_region_center_y = region_min_y + (region_size_y / 2.0)
    assert (tx_step_min_xyz[0] + tx_step_max_xyz[0]) / 2.0 == pytest.approx(tx_region_center_x, abs=1e-8)
    assert (tx_step_min_xyz[1] + tx_step_max_xyz[1]) / 2.0 == pytest.approx(tx_region_center_y, abs=1e-8)
    assert tx_step_max_xyz[2] == pytest.approx(region_min_z + tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"][2])
    imported_scene = bd.import_step(scene_step_path)
    scene_children = tuple(imported_scene.children)
    scene_children_by_label = {child.label: child for child in scene_children}
    expected_scene_labels = {"environment", "tx_region", "rx_region_max", "rx_pcb_l0", "rx_copper_l0", *tx_expected_names}
    assert set(scene_children_by_label) == expected_scene_labels
    solid_labels = expected_scene_labels
    for label in solid_labels:
        assert type(scene_children_by_label[label]).__name__ == "Solid"
    rx_entry = modeled_by_id["rx_rect_void_coil"]
    _assert_sheet_vertices_bridge_stub_bottom_face_diagonals(
        sheet_vertices=tx_port_sheet_vertices,
        terminal_stub_boxes=_world_terminal_stub_boxes(
            source_toml=source_toml,
            object_id="tx_rect_void_coil",
            seed=0,
        ),
        plane="XY",
    )
    _assert_sheet_vertices_bridge_stub_bottom_face_diagonals(
        sheet_vertices=tuple(tuple(vertex) for vertex in rx_entry["terminal_metadata"]["port_sheet_vertices_xyz"]),
        terminal_stub_boxes=_world_terminal_stub_boxes(
            source_toml=source_toml,
            object_id="rx_rect_void_coil",
            seed=0,
        ),
        plane="YZ",
    )
    if tx_underlay_repeat_count > 0:
        tx_base_body_names = _tx_expected_body_names(
            pcb_layer_count=len(tx_entry["canonical_coordinates"]["pcb_layer_z_positions_mm"]),
            underlay_repeat_count=0,
        )
        tx_base_min_x = min(_body_bbox(scene_step_path, label=label)[0][0] for label in tx_base_body_names)
        tx_base_min_y = min(_body_bbox(scene_step_path, label=label)[0][1] for label in tx_base_body_names)
        tx_base_max_x = max(_body_bbox(scene_step_path, label=label)[1][0] for label in tx_base_body_names)
        tx_base_max_y = max(_body_bbox(scene_step_path, label=label)[1][1] for label in tx_base_body_names)
        ferrite_min_xyz, ferrite_max_xyz = _body_bbox(scene_step_path, label="tx_underlay_ferrite_u0")
        pet_min_xyz, pet_max_xyz = _body_bbox(scene_step_path, label="tx_underlay_pet_psa_u0")
        air_min_xyz, air_max_xyz = _body_bbox(scene_step_path, label="tx_underlay_air_u0")
        assert ferrite_min_xyz[0] == pytest.approx(tx_base_min_x)
        assert ferrite_min_xyz[1] == pytest.approx(tx_base_min_y)
        assert ferrite_max_xyz[0] == pytest.approx(tx_base_max_x)
        assert ferrite_max_xyz[1] == pytest.approx(tx_base_max_y)
        assert ferrite_max_xyz[2] == pytest.approx(modeled_canonical["outer_bounds_min_xyz"][2])
        assert ferrite_min_xyz[2] == pytest.approx(
            modeled_canonical["outer_bounds_min_xyz"][2] - _TX_UNDERLAY_FERRITE_THICKNESS_MM
        )
        assert pet_max_xyz[2] == pytest.approx(ferrite_min_xyz[2])
        assert pet_min_xyz[2] == pytest.approx(
            ferrite_min_xyz[2] - _TX_UNDERLAY_PET_PSA_THICKNESS_MM
        )
        assert air_max_xyz[2] == pytest.approx(pet_min_xyz[2])
        assert air_min_xyz[2] == pytest.approx(
            pet_min_xyz[2] - _TX_UNDERLAY_AIR_THICKNESS_MM
        )
    _assert_zero_intersection_volume(scene_children_by_label[tx_expected_names[0]], scene_children_by_label[tx_copper_label])
    _assert_zero_intersection_volume(scene_children_by_label["rx_pcb_l0"], scene_children_by_label["rx_copper_l0"])
    rx_min_x, rx_min_y, rx_min_z = rx_entry["canonical_coordinates"]["outer_bounds_min_xyz"]
    rx_size_x, rx_size_y, rx_size_z = rx_entry["canonical_coordinates"]["outer_bounds_size_xyz"]
    rx_region_min_x, rx_region_min_y, rx_region_min_z = rx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    rx_region_size_x, rx_region_size_y, rx_region_size_z = rx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"]
    assert rx_entry["role"] == "rx_single_coil"
    assert rx_entry["plane"] == "YZ"
    assert rx_entry["placement_owner_id"] == "rx_region_max"
    assert rx_entry["expected_exported_body_names"] == ["rx_pcb_l0", "rx_copper_l0"]
    assert rx_entry["expected_exported_body_count"] == 2
    rx_port_sheet_vertices = tuple(tuple(vertex) for vertex in rx_entry["terminal_metadata"]["port_sheet_vertices_xyz"])
    assert len(rx_port_sheet_vertices) == 4
    assert rx_min_x == pytest.approx(rx_region_min_x + rx_region_size_x - rx_size_x)
    assert rx_min_y == pytest.approx(rx_region_min_y + (rx_region_size_y - rx_size_y) / 2.0)
    assert rx_min_z == pytest.approx(rx_region_min_z)
    rx_step_min_xyz, rx_step_max_xyz = _body_bbox(scene_step_path, label="rx_copper_l0")
    assert rx_step_max_xyz[0] == pytest.approx(rx_region_min_x + rx_region_size_x)
    assert (rx_step_min_xyz[1] + rx_step_max_xyz[1]) / 2.0 == pytest.approx(
        rx_region_min_y + (rx_region_size_y / 2.0),
        abs=1e-8,
    )
    assert rx_step_min_xyz[2] == pytest.approx(rx_region_min_z)


@pytest.mark.parametrize("layer_count", (2, 3))
def test_export_type2_step_artifacts_supports_multilayer_tx_port_sheet_path(
    tmp_path: Path,
    layer_count: int,
) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(layer_count=layer_count))
    type2_spec = load_type2_step_spec(toml_path)
    tx_modeled_spec = next(entry for entry in type2_spec.modeled_objects if entry.object_id == "tx_rect_void_coil")
    tx_underlay_repeat_count = resolve_modeled_underlay_repeat_count(tx_modeled_spec, seed=0)
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )
    tx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_rect_void_coil")
    assert tx_entry["expected_exported_body_names"] == _tx_expected_body_names(
        pcb_layer_count=layer_count,
        underlay_repeat_count=tx_underlay_repeat_count,
    )
    _assert_sheet_vertices_bridge_stub_bottom_face_diagonals(
        sheet_vertices=tuple(tuple(vertex) for vertex in tx_entry["terminal_metadata"]["port_sheet_vertices_xyz"]),
        terminal_stub_boxes=_world_terminal_stub_boxes(
            source_toml=toml_path,
            object_id="tx_rect_void_coil",
            seed=0,
        ),
        plane="XY",
    )


@pytest.mark.parametrize("expected_repeat_count", (0, 2, 8))
def test_export_type2_step_artifacts_resolves_tx_underlay_repeat_count_contract(
    tmp_path: Path,
    expected_repeat_count: int,
) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(layer_count=2))
    seed = _seed_for_underlay_repeat_count(
        toml_path,
        object_id="tx_rect_void_coil",
        expected_repeat_count=expected_repeat_count,
    )

    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=seed,
    )

    tx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_rect_void_coil")
    expected_names = _tx_expected_body_names(
        pcb_layer_count=2,
        underlay_repeat_count=expected_repeat_count,
    )
    assert tx_entry["expected_exported_body_names"] == expected_names
    assert tx_entry["expected_exported_body_count"] == len(expected_names)
    imported_scene = bd.import_step(Path(ledger["scene_step_path"]))
    scene_children_by_label = {child.label: child for child in imported_scene.children}
    for label in expected_names:
        assert label in scene_children_by_label
    if expected_repeat_count == 0:
        assert all(not label.startswith("tx_underlay_") for label in scene_children_by_label)
        return

    assert expected_names[-(expected_repeat_count * 3) :] == _tx_underlay_expected_body_names(
        repeat_count=expected_repeat_count
    )
    modeled_min_z = tx_entry["canonical_coordinates"]["outer_bounds_min_xyz"][2]
    ferrite_min_xyz, ferrite_max_xyz = _body_bbox(Path(ledger["scene_step_path"]), label="tx_underlay_ferrite_u0")
    pet_min_xyz, pet_max_xyz = _body_bbox(Path(ledger["scene_step_path"]), label="tx_underlay_pet_psa_u0")
    air_min_xyz, air_max_xyz = _body_bbox(Path(ledger["scene_step_path"]), label="tx_underlay_air_u0")
    assert ferrite_max_xyz[2] == pytest.approx(modeled_min_z)
    assert ferrite_min_xyz[2] == pytest.approx(modeled_min_z - _TX_UNDERLAY_FERRITE_THICKNESS_MM)
    assert pet_max_xyz[2] == pytest.approx(ferrite_min_xyz[2])
    assert pet_min_xyz[2] == pytest.approx(ferrite_min_xyz[2] - _TX_UNDERLAY_PET_PSA_THICKNESS_MM)
    assert air_max_xyz[2] == pytest.approx(pet_min_xyz[2])
    assert air_min_xyz[2] == pytest.approx(pet_min_xyz[2] - _TX_UNDERLAY_AIR_THICKNESS_MM)
    if expected_repeat_count == 8:
        assert expected_names[-1] == "tx_underlay_air_u7"


def test_export_type2_step_artifacts_translates_terminal_metadata_with_tx_region_offset(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(layer_count=1))
    tx_rect_void_toml_path = tmp_path / "tx_rect_void.toml"
    tx_rect_void_toml_path.write_text(_tx_rect_void_spec_text_with_layer_count(layer_count=1), encoding="utf-8")
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    tx_region_member = next(
        member
        for member in ledger["non_model_objects"][0]["member_objects"]
        if member["object_id"] == "tx_region"
    )
    modeled_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_rect_void_coil")
    local_spec = load_tx_rect_void_spec(tx_rect_void_toml_path)
    local_realized = realize_tx_rect_void_spec(local_spec, seed=0)
    local_centerline = build_tx_rect_void_centerline(local_realized)
    local_boxes = build_tx_rect_void_box_specs(local_realized)
    local_bounds_min_xyz, _local_bounds_max_xyz, local_size_xyz = modeled_body_bounds_from_boxes(local_boxes)
    region_min_x, region_min_y, region_min_z = tx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    region_size_x, region_size_y, _region_size_z = tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"]
    placement_offset_x = region_min_x + (region_size_x - local_size_xyz[0]) / 2.0 - local_bounds_min_xyz[0]
    placement_offset_y = region_min_y + (region_size_y - local_size_xyz[1]) / 2.0 - local_bounds_min_xyz[1]
    placement_offset_z = (
        region_min_z
        + tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"][2]
        - local_size_xyz[2]
        - local_bounds_min_xyz[2]
    )

    assert modeled_entry["canonical_coordinates"]["frame_origin_xyz"] == pytest.approx(
        (placement_offset_x, placement_offset_y, placement_offset_z)
    )
    modeled_bounds_min_xyz = modeled_entry["canonical_coordinates"]["outer_bounds_min_xyz"]
    assert isinstance(modeled_bounds_min_xyz, tuple)
    assert modeled_bounds_min_xyz[2] == pytest.approx(
        placement_offset_z + local_bounds_min_xyz[2]
    )
    assert modeled_entry["terminal_metadata"]["start_point_plane_mm"] == pytest.approx(
        (
            local_centerline[0][0] + placement_offset_x,
            local_centerline[0][1] + placement_offset_y,
        )
    )
    assert modeled_entry["terminal_metadata"]["end_point_plane_mm"] == pytest.approx(
        (
            local_centerline[-1][0] + placement_offset_x,
            local_centerline[-1][1] + placement_offset_y,
        )
    )
    expected_tx_port_sheet_vertices = tuple(
        tuple(round(component, 8) for component in vertex)
        for vertex in _widest_stub_bottom_face_diagonal_vertices(
            terminal_stub_boxes=_world_terminal_stub_boxes(
                source_toml=toml_path,
                object_id="tx_rect_void_coil",
                seed=0,
            ),
            plane="XY",
        )
    )
    actual_tx_port_sheet_vertices = tuple(
        tuple(round(component, 8) for component in vertex)
        for vertex in modeled_entry["terminal_metadata"]["port_sheet_vertices_xyz"]
    )
    assert set(actual_tx_port_sheet_vertices) == set(expected_tx_port_sheet_vertices)


def test_export_type2_step_artifacts_places_rx_single_coil_on_rx_region_max_yz_plane(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_fixed.toml"
    ledger = export_type2_step_artifacts(
        toml_path=source_toml,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    rx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "rx_rect_void_coil")
    rx_region_member = next(
        member for member in ledger["non_model_objects"][0]["member_objects"] if member["object_id"] == "rx_region_max"
    )
    rx_min_xyz = rx_entry["canonical_coordinates"]["outer_bounds_min_xyz"]
    assert isinstance(rx_min_xyz, tuple)
    rx_min_x, rx_min_y, rx_min_z = cast(tuple[float, float, float], rx_min_xyz)
    rx_size_xyz = rx_entry["canonical_coordinates"]["outer_bounds_size_xyz"]
    assert isinstance(rx_size_xyz, tuple)
    rx_size_x, rx_size_y, rx_size_z = cast(tuple[float, float, float], rx_size_xyz)
    region_min_x, region_min_y, region_min_z = rx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    region_size_x, region_size_y, region_size_z = rx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"]

    assert rx_entry["plane"] == "YZ"
    assert rx_entry["placement_owner_id"] == "rx_region_max"
    assert rx_min_x == pytest.approx(region_min_x + region_size_x - rx_size_x)
    assert rx_min_y == pytest.approx(region_min_y + (region_size_y - rx_size_y) / 2.0)
    assert rx_min_z == pytest.approx(region_min_z)
    rx_step_min_xyz, rx_step_max_xyz = _body_bbox(Path(ledger["scene_step_path"]), label="rx_copper_l0")
    assert rx_step_max_xyz[0] == pytest.approx(region_min_x + region_size_x)
    assert (rx_step_min_xyz[1] + rx_step_max_xyz[1]) / 2.0 == pytest.approx(
        region_min_y + (region_size_y / 2.0),
        abs=1e-8,
    )
    assert rx_step_min_xyz[2] == pytest.approx(region_min_z)


def test_export_type2_step_artifacts_propagates_custom_radiation_margin_into_step_ledger(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(radiation_margin_mm=4123.5))
    ledger_path = tmp_path / "out" / "ledger.json"

    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=ledger_path,
        seed=0,
    )

    assert ledger["em_policy"] == {"radiation_margin_mm": 4123.5}
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert payload["em_policy"] == {"radiation_margin_mm": 4123.5}


def test_export_type2_step_artifacts_fails_for_invalid_terminal_path(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(terminal_path="A_cw_to_b"))
    output_dir = tmp_path / "out"
    ledger_path = tmp_path / "out" / "ledger.json"

    with pytest.raises(ValueError, match=r"matching outer/inner corners"):
        export_type2_step_artifacts(
            toml_path=toml_path,
            output_dir=output_dir,
            ledger_path=ledger_path,
            seed=0,
        )


def test_export_type2_step_artifacts_fails_when_non_model_export_returns_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import peetsfea.type2_step_export as module_under_test

    toml_path = _write_spec(tmp_path, _type2_spec_text())
    output_dir = tmp_path / "out"
    ledger_path = tmp_path / "out" / "ledger.json"

    def _false_export_step(*args: object, **kwargs: object) -> bool:
        return False

    monkeypatch.setattr(module_under_test.bd, "export_step", _false_export_step)

    with pytest.raises(RuntimeError, match=r"build123d export_step returned False for type2 scene STEP:"):
        export_type2_step_artifacts(
            toml_path=toml_path,
            output_dir=output_dir,
            ledger_path=ledger_path,
            seed=0,
        )

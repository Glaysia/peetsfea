from __future__ import annotations

from collections.abc import Iterable
import math
from dataclasses import replace
from pathlib import Path
from typing import Protocol
from typing import cast

import pytest

from peetsfea.type2_non_model_scene import require_tx_outer_region_prism_provenance
from peetsfea.type2_non_model_scene import resolve_non_model_scene_specs
from peetsfea.type2_non_model_scene import resolve_tx_outer_region_tilt_frame
from peetsfea.type2_single_coil_scene import build_modeled_single_coil_scene_data
from peetsfea.type2_single_coil_scene import resolve_tx_outer_single_coil_fit_envelope
from peetsfea.type2_single_coil_scene import resolve_tx_outer_single_coil_scene_placement
from peetsfea.type2_step_spec import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxOuterSingleCoilSpec
from peetsfea.type2_step_spec import load_type2_step_spec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import Point3
from peetsfea.type2_step_spec import RangeSpec


class _VertexLike(Protocol):
    X: float
    Y: float
    Z: float


class _ShapeWithVertices(Protocol):
    def vertices(self) -> Iterable[_VertexLike]: ...


class _FaceLike(Protocol):
    def normal_at(self) -> _VertexLike: ...


class _ShapeWithFaces(Protocol):
    def faces(self) -> Iterable[_FaceLike]: ...


class _ShapeWithChildren(Protocol):
    children: Iterable[object]


class _ShapeWithLabel(Protocol):
    label: str


def _range_spec(is_integer: bool, start: float, end: float, count: int) -> RangeSpec:
    return RangeSpec(is_integer=is_integer, start=start, end=end, count=count)


def _type2_fixed_spec_path() -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "type2_fixed.toml"


def _world_aabb_from_tx_outer_virtual_bounds(
    *,
    min_xyz: tuple[float, float, float],
    max_xyz: tuple[float, float, float],
    frame_origin_xyz: tuple[float, float, float],
    local_x_axis_xyz: tuple[float, float, float],
) -> dict[str, tuple[float, float, float]]:
    frame_origin_x, frame_origin_y, frame_origin_z = frame_origin_xyz
    local_x_axis_unit_x, local_x_axis_unit_y, local_x_axis_unit_z = local_x_axis_xyz
    angle_rad = math.atan2(-local_x_axis_unit_z, local_x_axis_unit_x)
    cos_angle = math.cos(angle_rad)
    sin_angle = math.sin(angle_rad)

    def _to_world(point: tuple[float, float, float]) -> tuple[float, float, float]:
        point_x, point_y, point_z = point
        return (
            (point_x * cos_angle) + (point_z * sin_angle) + frame_origin_x,
            point_y + frame_origin_y,
            (-point_x * sin_angle) + (point_z * cos_angle) + frame_origin_z,
        )

    min_x, min_y, min_z = min_xyz
    max_x, max_y, max_z = max_xyz
    points = tuple(
        _to_world(point)
        for point in (
            (min_x, min_y, min_z),
            (min_x, min_y, max_z),
            (min_x, max_y, min_z),
            (min_x, max_y, max_z),
            (max_x, min_y, min_z),
            (max_x, min_y, max_z),
            (max_x, max_y, min_z),
            (max_x, max_y, max_z),
        )
    )
    return {
        "min_xyz": (
            min(point[0] for point in points),
            min(point[1] for point in points),
            min(point[2] for point in points),
        ),
        "max_xyz": (
            max(point[0] for point in points),
            max(point[1] for point in points),
            max(point[2] for point in points),
        ),
        "size_xyz": (
            max(point[0] for point in points) - min(point[0] for point in points),
            max(point[1] for point in points) - min(point[1] for point in points),
            max(point[2] for point in points) - min(point[2] for point in points),
        ),
    }


def _assert_prism_local_design_outer_x_position_ratio(
    *,
    design_outer_min_xyz: tuple[float, float, float],
    design_outer_max_xyz: tuple[float, float, float],
    design_outer_size_xyz: tuple[float, float, float],
    prism_local_x_span_mm: float,
    x_position_ratio: float,
) -> None:
    design_outer_half_x = design_outer_size_xyz[0] / 2.0
    design_outer_center_x = design_outer_min_xyz[0] + design_outer_half_x
    expected_center_x = design_outer_half_x + (
        (prism_local_x_span_mm - design_outer_size_xyz[0]) * x_position_ratio
    )
    assert design_outer_center_x == pytest.approx(expected_center_x)
    if x_position_ratio == 0.0:
        assert design_outer_min_xyz[0] == pytest.approx(0.0)
    if x_position_ratio == 1.0:
        assert design_outer_max_xyz[0] == pytest.approx(prism_local_x_span_mm)


def _subtract_points(a: Point3, b: Point3) -> Point3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot_points(a: Point3, b: Point3) -> float:
    return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])


def _normalize_point(point: Point3) -> Point3:
    magnitude = math.sqrt(_dot_points(point, point))
    assert magnitude > 0.0
    return (point[0] / magnitude, point[1] / magnitude, point[2] / magnitude)


def _shape_vertices_xyz(shape: object) -> tuple[Point3, ...]:
    assert hasattr(shape, "vertices")
    shape_with_vertices = cast(_ShapeWithVertices, shape)
    points: list[Point3] = []
    for raw_vertex in shape_with_vertices.vertices():
        assert hasattr(raw_vertex, "X")
        assert hasattr(raw_vertex, "Y")
        assert hasattr(raw_vertex, "Z")
        vertex_x = raw_vertex.X
        vertex_y = raw_vertex.Y
        vertex_z = raw_vertex.Z
        assert isinstance(vertex_x, float)
        assert isinstance(vertex_y, float)
        assert isinstance(vertex_z, float)
        points.append((vertex_x, vertex_y, vertex_z))
    vertices = tuple(points)
    assert vertices
    return vertices


def _shape_label(shape: object) -> str:
    assert hasattr(shape, "label")
    shape_with_label = cast(_ShapeWithLabel, shape)
    raw_label = shape_with_label.label
    assert isinstance(raw_label, str)
    return raw_label


def _flatten_labeled_shapes(shapes: Iterable[object]) -> dict[str, object]:
    shapes_by_label: dict[str, object] = {}
    pending = list(shapes)
    while pending:
        shape = pending.pop(0)
        label = _shape_label(shape)
        if label != "":
            assert label not in shapes_by_label
            shapes_by_label[label] = shape
        if hasattr(shape, "children"):
            shape_with_children = cast(_ShapeWithChildren, shape)
            pending.extend(shape_with_children.children)
    return shapes_by_label


def _assert_shape_has_face_parallel_to(
    *,
    shape: object,
    target_normal_xyz: Point3,
    label: str,
) -> None:
    assert hasattr(shape, "faces")
    shape_with_faces = cast(_ShapeWithFaces, shape)
    target = _normalize_point(target_normal_xyz)
    best_score = -2.0
    for face in shape_with_faces.faces():
        normal = face.normal_at()
        candidate = _normalize_point((normal.X, normal.Y, normal.Z))
        score = abs(_dot_points(candidate, target))
        best_score = max(best_score, score)
    assert best_score >= 0.995, f"{label} has no face parallel to target top clip plane"


def _assert_within_closed_interval(*, actual: float, minimum: float, maximum: float) -> None:
    tolerance = 1e-9
    assert actual >= minimum - tolerance
    assert actual <= maximum + tolerance


def _project_vertices_to_tx_outer_prism_local(
    *,
    vertices_xyz: Iterable[Point3],
    frame_origin_xyz: Point3,
    local_x_axis_xyz: Point3,
    local_y_axis_xyz: Point3,
    local_z_axis_xyz: Point3,
) -> tuple[Point3, ...]:
    return tuple(
        (
            _dot_points(_subtract_points(vertex, frame_origin_xyz), local_x_axis_xyz),
            _dot_points(_subtract_points(vertex, frame_origin_xyz), local_y_axis_xyz),
            _dot_points(_subtract_points(vertex, frame_origin_xyz), local_z_axis_xyz),
        )
        for vertex in vertices_xyz
    )


def _resolve_tx_region_outer_region_and_outer_single_coil(
    *,
    seed: int,
) -> tuple[NonModelBoxSpec, NonModelBoxSpec, ModeledTxOuterSingleCoilSpec]:
    spec = load_type2_step_spec(_type2_fixed_spec_path())
    tx_inner_single_coil_spec = next(
        modeled_spec
        for modeled_spec in spec.modeled_objects
        if modeled_spec.role == "tx_inner_single_coil"
    )
    assert isinstance(tx_inner_single_coil_spec, ModeledTxInnerSingleCoilSpec)
    tx_outer_single_coil_spec = next(
        modeled_spec
        for modeled_spec in spec.modeled_objects
        if modeled_spec.role == "tx_outer_single_coil"
    )
    assert isinstance(tx_outer_single_coil_spec, ModeledTxOuterSingleCoilSpec)
    resolved_non_model_specs = resolve_non_model_scene_specs(
        base_specs=spec.non_model_objects,
        derived_specs=spec.non_model_derived_objects,
        modeled_specs=(tx_inner_single_coil_spec,),
        seed=seed,
    )
    tx_region_spec = next(
        spec_obj for spec_obj in resolved_non_model_specs if spec_obj.object_id == "tx_region"
    )
    tx_outer_region_spec = next(
        spec_obj for spec_obj in resolved_non_model_specs if spec_obj.object_id == "tx_outer_region"
    )
    return tx_region_spec, tx_outer_region_spec, tx_outer_single_coil_spec


def _resolve_outer_region_and_outer_single_coil(
    *,
    seed: int,
) -> tuple[NonModelBoxSpec, ModeledTxOuterSingleCoilSpec]:
    _tx_region_spec, tx_outer_region_spec, tx_outer_single_coil_spec = (
        _resolve_tx_region_outer_region_and_outer_single_coil(seed=seed)
    )
    return tx_outer_region_spec, tx_outer_single_coil_spec


@pytest.mark.parametrize("x_position_ratio", (0.0, 0.5942857142857143, 1.0))
def test_tx_outer_single_coil_fit_envelope_uses_prism_local_design_outer_x_position_ratio(
    x_position_ratio: float,
) -> None:
    seed = 17
    tx_outer_region_spec, tx_outer_single_coil_spec = _resolve_outer_region_and_outer_single_coil(seed=seed)
    fixed_ratio = _range_spec(False, x_position_ratio, x_position_ratio, 1)
    tx_outer_single_coil_spec = replace(tx_outer_single_coil_spec, x_position_ratio=fixed_ratio)
    tilt_frame = resolve_tx_outer_region_tilt_frame(
        provenance=require_tx_outer_region_prism_provenance(object_id="tx_outer_region")
    )
    fit_envelope = resolve_tx_outer_single_coil_fit_envelope(
        tx_outer_single_coil_spec,
        owner_spec=tx_outer_region_spec,
        seed=seed,
    )

    _assert_prism_local_design_outer_x_position_ratio(
        design_outer_min_xyz=fit_envelope.design_outer_bounds_min_xyz,
        design_outer_max_xyz=fit_envelope.design_outer_bounds_max_xyz,
        design_outer_size_xyz=fit_envelope.design_outer_bounds_size_xyz,
        prism_local_x_span_mm=tilt_frame.top_edge_length_xyz,
        x_position_ratio=x_position_ratio,
    )


def test_tx_outer_actual_region_matches_prism_local_placement_without_world_x_shift() -> None:
    seed = 17
    tx_outer_region_spec, tx_outer_single_coil_spec = _resolve_outer_region_and_outer_single_coil(
        seed=seed
    )

    _, tx_outer_scene_data = build_modeled_single_coil_scene_data(
        tx_outer_single_coil_spec,
        owner_spec=tx_outer_region_spec,
        tx_region_max_z=tx_outer_region_spec.origin_xyz[2] + tx_outer_region_spec.size_xyz[2],
        seed=seed,
    )
    canonical_coordinates = tx_outer_scene_data["canonical_coordinates"]
    modeled_outer_region_origin_xyz = canonical_coordinates["outer_bounds_min_xyz"]
    modeled_outer_region_size_xyz = canonical_coordinates["outer_bounds_size_xyz"]

    placement = resolve_tx_outer_single_coil_scene_placement(
        tx_outer_single_coil_spec,
        owner_spec=tx_outer_region_spec,
        seed=seed,
    )
    tilt_frame = resolve_tx_outer_region_tilt_frame(
        provenance=require_tx_outer_region_prism_provenance(object_id="tx_outer_region")
    )
    assert placement.frame_origin_xyz == pytest.approx(tilt_frame.frame_origin_xyz)
    assert placement.physical_modeled_body_bounds_min_xyz == pytest.approx(modeled_outer_region_origin_xyz)
    assert placement.physical_modeled_body_bounds_size_xyz == pytest.approx(modeled_outer_region_size_xyz)


def test_tx_outer_single_coil_fit_envelope_stays_inside_outer_prism_local_frame() -> None:
    seed = 17
    tx_outer_region_spec, tx_outer_single_coil_spec = _resolve_outer_region_and_outer_single_coil(seed=seed)
    provenance = require_tx_outer_region_prism_provenance(object_id="tx_outer_region")
    tilt_frame = resolve_tx_outer_region_tilt_frame(provenance=provenance)
    fit_envelope = resolve_tx_outer_single_coil_fit_envelope(
        tx_outer_single_coil_spec,
        owner_spec=tx_outer_region_spec,
        seed=seed,
    )

    top_inner_start_xyz = provenance["top_inner_start_xyz"]
    top_inner_end_xyz = provenance["top_inner_end_xyz"]
    prism_local_y_span_mm = top_inner_end_xyz[1] - top_inner_start_xyz[1]
    assert prism_local_y_span_mm > 0.0

    _assert_prism_local_design_outer_x_position_ratio(
        design_outer_min_xyz=fit_envelope.design_outer_bounds_min_xyz,
        design_outer_max_xyz=fit_envelope.design_outer_bounds_max_xyz,
        design_outer_size_xyz=fit_envelope.design_outer_bounds_size_xyz,
        prism_local_x_span_mm=tilt_frame.top_edge_length_xyz,
        x_position_ratio=tx_outer_single_coil_spec.x_position_ratio.start,
    )
    _assert_within_closed_interval(
        actual=fit_envelope.outer_bounds_min_xyz[0],
        minimum=0.0,
        maximum=tilt_frame.top_edge_length_xyz,
    )
    _assert_within_closed_interval(
        actual=fit_envelope.outer_bounds_max_xyz[0],
        minimum=0.0,
        maximum=tilt_frame.top_edge_length_xyz,
    )
    _assert_within_closed_interval(
        actual=fit_envelope.outer_bounds_min_xyz[1],
        minimum=0.0,
        maximum=prism_local_y_span_mm,
    )
    _assert_within_closed_interval(
        actual=fit_envelope.outer_bounds_max_xyz[1],
        minimum=0.0,
        maximum=prism_local_y_span_mm,
    )
    _assert_within_closed_interval(
        actual=fit_envelope.outer_bounds_min_xyz[2],
        minimum=-tx_outer_region_spec.size_xyz[2],
        maximum=0.0,
    )
    _assert_within_closed_interval(
        actual=fit_envelope.outer_bounds_max_xyz[2],
        minimum=-tx_outer_region_spec.size_xyz[2],
        maximum=0.0,
    )


def test_tx_outer_single_coil_vertices_project_inside_outer_prism_local_span() -> None:
    seed = 17
    tx_outer_region_spec, tx_outer_single_coil_spec = _resolve_outer_region_and_outer_single_coil(seed=seed)
    provenance = require_tx_outer_region_prism_provenance(object_id="tx_outer_region")
    tilt_frame = resolve_tx_outer_region_tilt_frame(provenance=provenance)

    scene_children, _tx_outer_scene_data = build_modeled_single_coil_scene_data(
        tx_outer_single_coil_spec,
        owner_spec=tx_outer_region_spec,
        tx_region_max_z=tx_outer_region_spec.origin_xyz[2] + tx_outer_region_spec.size_xyz[2],
        seed=seed,
    )
    assert scene_children
    vertices_xyz = tuple(vertex for shape in scene_children for vertex in _shape_vertices_xyz(shape))

    local_x_values = tuple(
        _dot_points(
            _subtract_points(vertex, tilt_frame.frame_origin_xyz),
            tilt_frame.local_x_axis_xyz,
        )
        for vertex in vertices_xyz
    )
    local_y_values = tuple(
        _dot_points(
            _subtract_points(vertex, tilt_frame.frame_origin_xyz),
            tilt_frame.local_y_axis_xyz,
        )
        for vertex in vertices_xyz
    )
    local_z_values = tuple(
        _dot_points(
            _subtract_points(vertex, tilt_frame.frame_origin_xyz),
            tilt_frame.local_z_axis_xyz,
        )
        for vertex in vertices_xyz
    )

    _assert_within_closed_interval(
        actual=min(local_x_values),
        minimum=0.0,
        maximum=tilt_frame.top_edge_length_xyz,
    )
    _assert_within_closed_interval(
        actual=max(local_x_values),
        minimum=0.0,
        maximum=tilt_frame.top_edge_length_xyz,
    )
    top_inner_start_xyz = provenance["top_inner_start_xyz"]
    top_inner_end_xyz = provenance["top_inner_end_xyz"]
    prism_local_y_span_mm = top_inner_end_xyz[1] - top_inner_start_xyz[1]
    assert prism_local_y_span_mm > 0.0
    _assert_within_closed_interval(
        actual=min(local_y_values),
        minimum=0.0,
        maximum=prism_local_y_span_mm,
    )
    _assert_within_closed_interval(
        actual=max(local_y_values),
        minimum=0.0,
        maximum=prism_local_y_span_mm,
    )
    _assert_within_closed_interval(
        actual=min(local_z_values),
        minimum=-tx_outer_region_spec.size_xyz[2],
        maximum=0.0,
    )
    _assert_within_closed_interval(
        actual=max(local_z_values),
        minimum=-tx_outer_region_spec.size_xyz[2],
        maximum=0.0,
    )


def test_tx_outer_void_stack_vertices_stay_inside_realized_outer_void_and_reach_tx_region_top() -> None:
    seed = 17
    tx_region_spec, tx_outer_region_spec, tx_outer_single_coil_spec = (
        _resolve_tx_region_outer_region_and_outer_single_coil(seed=seed)
    )
    tx_region_max_z = tx_region_spec.origin_xyz[2] + tx_region_spec.size_xyz[2]
    provenance = require_tx_outer_region_prism_provenance(object_id="tx_outer_region")
    tilt_frame = resolve_tx_outer_region_tilt_frame(provenance=provenance)
    fit_envelope = resolve_tx_outer_single_coil_fit_envelope(
        tx_outer_single_coil_spec,
        owner_spec=tx_outer_region_spec,
        seed=seed,
    )
    scene_children, _tx_outer_scene_data = build_modeled_single_coil_scene_data(
        tx_outer_single_coil_spec,
        owner_spec=tx_outer_region_spec,
        tx_region_max_z=tx_region_max_z,
        seed=seed,
    )

    shapes_by_label = _flatten_labeled_shapes(scene_children)
    outer_void_stack_labels = tuple(
        label
        for label in shapes_by_label
        if label.startswith("tx_outer_void_ferrite_u") or label.startswith("tx_outer_void_pet_psa_u")
    )
    assert any(label.startswith("tx_outer_void_ferrite_u") for label in outer_void_stack_labels)
    assert any(label.startswith("tx_outer_void_pet_psa_u") for label in outer_void_stack_labels)

    expected_min_x = fit_envelope.frame_origin_xyz[0] + fit_envelope.realized.void_bounds.min_x
    expected_max_x = fit_envelope.frame_origin_xyz[0] + fit_envelope.realized.void_bounds.max_x
    expected_min_y = fit_envelope.frame_origin_xyz[1] + fit_envelope.realized.void_bounds.min_y
    expected_max_y = fit_envelope.frame_origin_xyz[1] + fit_envelope.realized.void_bounds.max_y
    all_local_x_values: list[float] = []
    all_local_y_values: list[float] = []
    all_world_z_values: list[float] = []
    top_clipped_labels: list[str] = []

    for label in outer_void_stack_labels:
        shape = shapes_by_label[label]
        vertices_xyz = _shape_vertices_xyz(shape)
        world_z_values = tuple(vertex[2] for vertex in vertices_xyz)
        local_points = _project_vertices_to_tx_outer_prism_local(
            vertices_xyz=vertices_xyz,
            frame_origin_xyz=tilt_frame.frame_origin_xyz,
            local_x_axis_xyz=tilt_frame.local_x_axis_xyz,
            local_y_axis_xyz=tilt_frame.local_y_axis_xyz,
            local_z_axis_xyz=tilt_frame.local_z_axis_xyz,
        )
        local_x_values = tuple(point[0] for point in local_points)
        local_y_values = tuple(point[1] for point in local_points)
        all_local_x_values.extend(local_x_values)
        all_local_y_values.extend(local_y_values)
        all_world_z_values.extend(world_z_values)
        _assert_within_closed_interval(actual=min(local_x_values), minimum=expected_min_x, maximum=expected_max_x)
        _assert_within_closed_interval(actual=max(local_x_values), minimum=expected_min_x, maximum=expected_max_x)
        _assert_within_closed_interval(actual=min(local_y_values), minimum=expected_min_y, maximum=expected_max_y)
        _assert_within_closed_interval(actual=max(local_y_values), minimum=expected_min_y, maximum=expected_max_y)
        assert max(world_z_values) <= tx_region_max_z + 1e-8
        top_vertex_count = sum(
            1 for world_z in world_z_values if world_z == pytest.approx(tx_region_max_z, abs=1e-8)
        )
        if top_vertex_count >= 4:
            _assert_shape_has_face_parallel_to(
                shape=shape,
                target_normal_xyz=(0.0, 0.0, 1.0),
                label=label,
            )
            top_clipped_labels.append(label)

    assert min(all_local_x_values) == pytest.approx(expected_min_x)
    assert max(all_local_x_values) == pytest.approx(expected_max_x)
    assert min(all_local_y_values) == pytest.approx(expected_min_y)
    assert max(all_local_y_values) == pytest.approx(expected_max_y)
    assert max(all_world_z_values) == pytest.approx(tx_region_max_z, abs=1e-8)
    assert top_clipped_labels

    _scene_children, tx_outer_scene_data = build_modeled_single_coil_scene_data(
        tx_outer_single_coil_spec,
        owner_spec=tx_outer_region_spec,
        tx_region_max_z=tx_region_max_z,
        seed=seed,
    )
    canonical_coordinates = tx_outer_scene_data["canonical_coordinates"]
    assert isinstance(canonical_coordinates, dict)
    if "outer_void_stack_raw_overshoot_mm" in canonical_coordinates:
        raw_overshoot_mm = canonical_coordinates["outer_void_stack_raw_overshoot_mm"]
        assert isinstance(raw_overshoot_mm, float)
        expected_raw_overshoot_mm = (
            tx_outer_single_coil_spec.underlay_pet_psa_thickness_mm.start
            + tx_outer_single_coil_spec.underlay_ferrite_thickness_mm.start
        )
        assert raw_overshoot_mm == pytest.approx(expected_raw_overshoot_mm)


def test_tx_outer_bottom_underlay_labels_and_footprint_match_outer_design_actual() -> None:
    seed = 17
    tx_outer_region_spec, tx_outer_single_coil_spec = _resolve_outer_region_and_outer_single_coil(seed=seed)
    tilt_frame = resolve_tx_outer_region_tilt_frame(
        provenance=require_tx_outer_region_prism_provenance(object_id="tx_outer_region")
    )
    fit_envelope = resolve_tx_outer_single_coil_fit_envelope(
        tx_outer_single_coil_spec,
        owner_spec=tx_outer_region_spec,
        seed=seed,
    )
    scene_children, tx_outer_scene_data = build_modeled_single_coil_scene_data(
        tx_outer_single_coil_spec,
        owner_spec=tx_outer_region_spec,
        tx_region_max_z=tx_outer_region_spec.origin_xyz[2] + tx_outer_region_spec.size_xyz[2],
        seed=seed,
    )
    shapes_by_label = _flatten_labeled_shapes(scene_children)
    bottom_underlay_labels = tuple(
        label
        for label in shapes_by_label
        if label.startswith("tx_outer_underlay_pet_psa_u") or label.startswith("tx_outer_underlay_ferrite_u")
    )

    assert any(label.startswith("tx_outer_underlay_pet_psa_u") for label in bottom_underlay_labels)
    assert any(label.startswith("tx_outer_underlay_ferrite_u") for label in bottom_underlay_labels)
    expected_exported_body_names = tx_outer_scene_data["expected_exported_body_names"]
    assert isinstance(expected_exported_body_names, tuple)
    assert all(label in expected_exported_body_names for label in bottom_underlay_labels)

    expected_min_x = fit_envelope.design_outer_bounds_min_xyz[0]
    expected_max_x = fit_envelope.design_outer_bounds_max_xyz[0]
    expected_min_y = fit_envelope.design_outer_bounds_min_xyz[1]
    expected_max_y = fit_envelope.design_outer_bounds_max_xyz[1]
    expected_top_z = fit_envelope.design_outer_bounds_min_xyz[2]
    all_local_x_values: list[float] = []
    all_local_y_values: list[float] = []
    all_local_z_values: list[float] = []

    for label in bottom_underlay_labels:
        local_points = _project_vertices_to_tx_outer_prism_local(
            vertices_xyz=_shape_vertices_xyz(shapes_by_label[label]),
            frame_origin_xyz=tilt_frame.frame_origin_xyz,
            local_x_axis_xyz=tilt_frame.local_x_axis_xyz,
            local_y_axis_xyz=tilt_frame.local_y_axis_xyz,
            local_z_axis_xyz=tilt_frame.local_z_axis_xyz,
        )
        local_x_values = tuple(point[0] for point in local_points)
        local_y_values = tuple(point[1] for point in local_points)
        local_z_values = tuple(point[2] for point in local_points)
        all_local_x_values.extend(local_x_values)
        all_local_y_values.extend(local_y_values)
        all_local_z_values.extend(local_z_values)
        _assert_within_closed_interval(actual=min(local_x_values), minimum=expected_min_x, maximum=expected_max_x)
        _assert_within_closed_interval(actual=max(local_x_values), minimum=expected_min_x, maximum=expected_max_x)
        _assert_within_closed_interval(actual=min(local_y_values), minimum=expected_min_y, maximum=expected_max_y)
        _assert_within_closed_interval(actual=max(local_y_values), minimum=expected_min_y, maximum=expected_max_y)
        assert max(local_z_values) <= expected_top_z + 1e-8

    assert min(all_local_x_values) == pytest.approx(expected_min_x)
    assert max(all_local_x_values) == pytest.approx(expected_max_x)
    assert min(all_local_y_values) == pytest.approx(expected_min_y)
    assert max(all_local_y_values) == pytest.approx(expected_max_y)
    assert max(all_local_z_values) == pytest.approx(expected_top_z, abs=1e-8)

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Literal, cast

import build123d as bd

from peetsfea.tx_rect_void_centerline import _void_polygon, build_tx_rect_void_centerline
from peetsfea.tx_rect_void_geometry import (
    _planar_bounds_from_polygons,
    _polygon_bounds,
    _polygons_overlap_positive_area,
    _rect_polygon_from_bounds,
    _segment_joined_polygon,
    _terminal_stub_polygon,
    CopperPrimitive,
    Point2,
    Polygon2,
    RectBounds,
    TerminalColumn,
)
from peetsfea.tx_rect_void_spec import _parse_terminal_path, load_tx_rect_void_spec, realize_tx_rect_void_spec
from peetsfea.tx_rect_void_types import (
    BoxSpec,
    ModeledObjectCanonicalCoordinates,
    ModeledObjectEntry,
    ModeledObjectTerminalMetadata,
    RealizedSingleCoilRectVoid,
    SingleCoilRectVoidExportResult,
    SingleCoilRectVoidSpec,
    SingleCoilProfile,
    TX_SINGLE_COIL_PROFILE,
)

_TERMINAL_STUB_SIDE_RATIO = 0.60


def _transform_box_spec(
    box_spec: BoxSpec,
    *,
    profile: SingleCoilProfile,
    frame_origin_xyz: tuple[float, float, float],
) -> BoxSpec:
    local_origin = box_spec.origin_xyz
    local_size = box_spec.size_xyz
    world_origin = profile.world_point(local_origin, frame_origin_xyz=frame_origin_xyz)
    world_size = profile.world_size(local_size)
    return BoxSpec(
        label=box_spec.label,
        role=box_spec.role,
        feature=box_spec.feature,
        layer_index=box_spec.layer_index,
        origin_xyz=world_origin,
        size_xyz=world_size,
    )


def _copper_box_from_primitive(primitive: CopperPrimitive) -> BoxSpec:
    bounds = _polygon_bounds(primitive.polygon_xy)
    return BoxSpec(
        label=primitive.label,
        role="copper",
        feature=primitive.feature,
        layer_index=primitive.layer_index,
        origin_xyz=(bounds.min_x, bounds.min_y, primitive.origin_z),
        size_xyz=(bounds.max_x - bounds.min_x, bounds.max_y - bounds.min_y, primitive.size_z),
    )


def _copper_primitives_for_layer(
    *,
    realized: RealizedSingleCoilRectVoid,
    centerline: tuple[Point2, ...],
    layer_index: int,
    pcb_z: float,
    profile: SingleCoilProfile,
) -> tuple[CopperPrimitive, ...]:
    copper_z = pcb_z + realized.pcb_thickness_mm
    primitives: list[CopperPrimitive] = []
    for segment_index, (p0, p1) in enumerate(zip(centerline[:-1], centerline[1:])):
        _ = p0, p1
        primitives.append(
            CopperPrimitive(
                label=f"{profile.copper_body_prefix}_l{layer_index}_s{segment_index}",
                feature="planar_segment",
                layer_index=layer_index,
                segment_index=segment_index,
                terminal_column="none",
                polygon_xy=_segment_joined_polygon(
                    centerline,
                    trace_width_mm=realized.trace_width_mm,
                    segment_index=segment_index,
                ),
                origin_z=copper_z,
                size_z=realized.copper_thickness_mm,
            )
        )
    stub_side_mm = realized.trace_width_mm * _TERMINAL_STUB_SIDE_RATIO
    overlap_mm = min((stub_side_mm / 2.0) / 2.0, max(realized.copper_thickness_mm, 1e-3))
    stub_origin_z = pcb_z - realized.terminal_stub_length_mm
    stub_size_z = realized.terminal_stub_length_mm + realized.pcb_thickness_mm + realized.copper_thickness_mm
    for stub_name, endpoint_xy, inward_point_xy in (
        ("start", centerline[0], centerline[1]),
        ("end", centerline[-1], centerline[-2]),
    ):
        primitives.append(
            CopperPrimitive(
                label=f"{profile.copper_body_prefix}_l{layer_index}_stub_{stub_name}",
                feature="terminal_stub",
                layer_index=layer_index,
                segment_index=-1,
                terminal_column=cast(TerminalColumn, stub_name),
                polygon_xy=_terminal_stub_polygon(
                    endpoint_xy=endpoint_xy,
                    inward_point_xy=inward_point_xy,
                    stub_side_mm=stub_side_mm,
                    overlap_mm=overlap_mm,
                ),
                origin_z=stub_origin_z,
                size_z=stub_size_z,
            )
        )
    return tuple(primitives)


def _is_tx_multilayer_parallel_stack(
    realized: RealizedSingleCoilRectVoid,
    *,
    profile: SingleCoilProfile,
) -> bool:
    return profile.role == "tx_single_coil" and realized.layer_count > 1


def _vertical_bus_primitive_from_stub_column(
    *,
    realized: RealizedSingleCoilRectVoid,
    profile: SingleCoilProfile,
    copper_primitives: tuple[CopperPrimitive, ...],
    terminal_column: Literal["start", "end"],
) -> CopperPrimitive:
    stub_primitives = tuple(
        primitive
        for primitive in copper_primitives
        if primitive.feature == "terminal_stub" and primitive.terminal_column == terminal_column
    )
    if len(stub_primitives) != realized.layer_count:
        raise ValueError(
            "tx multilayer vertical bus requires one stub per layer in each terminal column "
            f"(terminal_column={terminal_column}, expected={realized.layer_count}, actual={len(stub_primitives)})"
        )
    planar_bounds = _planar_bounds_from_polygons(tuple(primitive.polygon_xy for primitive in stub_primitives))
    min_z = min(primitive.origin_z for primitive in stub_primitives)
    max_z = max(primitive.origin_z + primitive.size_z for primitive in stub_primitives)
    if max_z <= min_z:
        raise ValueError(
            "tx multilayer vertical bus must have positive height "
            f"(terminal_column={terminal_column}, min_z={min_z}, max_z={max_z})"
        )
    return CopperPrimitive(
        label=f"{profile.copper_body_prefix}_bus_{terminal_column}",
        feature="vertical_bus",
        layer_index=0,
        segment_index=-1,
        terminal_column=terminal_column,
        polygon_xy=_rect_polygon_from_bounds(planar_bounds),
        origin_z=min_z,
        size_z=max_z - min_z,
    )


def _validate_copper_primitives_do_not_touch_void(
    realized: RealizedSingleCoilRectVoid,
    copper_primitives: tuple[CopperPrimitive, ...],
) -> None:
    void_polygon = _void_polygon(realized)
    for primitive in copper_primitives:
        if _polygons_overlap_positive_area(primitive.polygon_xy, void_polygon):
            raise ValueError(
                "tx rect/void copper primitive intersects void keepout "
                f"(label={primitive.label}, feature={primitive.feature}, void={realized.void_bounds})"
            )


def _validate_copper_primitives_do_not_short(copper_primitives: tuple[CopperPrimitive, ...]) -> None:
    planar_primitives = tuple(primitive for primitive in copper_primitives if primitive.feature == "planar_segment")
    if len(planar_primitives) == 0:
        raise ValueError("tx rect/void layer must contain at least one planar segment primitive")
    for first_index, first_primitive in enumerate(planar_primitives):
        for second_primitive in planar_primitives[first_index + 1 :]:
            if second_primitive.segment_index <= first_primitive.segment_index + 2:
                continue
            if _polygons_overlap_positive_area(first_primitive.polygon_xy, second_primitive.polygon_xy):
                raise ValueError(
                    "tx rect/void non-adjacent copper primitives overlap and would short turns "
                    f"(first={first_primitive.label}, second={second_primitive.label})"
                )


def _face_from_polygon_xy(polygon_xy: Polygon2) -> bd.Face:
    with bd.BuildLine() as builder:
        bd.Polyline(*polygon_xy, close=True)
    return cast(bd.Face, bd.make_face(builder.line.wires()[0]))


def _plane_for_local_z(
    *,
    profile: SingleCoilProfile,
    frame_origin_xyz: tuple[float, float, float],
    local_z: float,
) -> bd.Plane:
    return bd.Plane(
        origin=profile.world_point((0.0, 0.0, local_z), frame_origin_xyz=frame_origin_xyz),
        x_dir=profile.world_delta((1.0, 0.0, 0.0)),
        z_dir=profile.world_delta((0.0, 0.0, 1.0)),
    )


def _extrude_face_on_plane(
    *,
    face_xy: bd.Face,
    profile: SingleCoilProfile,
    frame_origin_xyz: tuple[float, float, float],
    local_z: float,
    amount: float,
) -> bd.Shape:
    if amount <= 0.0:
        raise ValueError(f"extrusion amount must be > 0 (actual={amount})")
    plane = _plane_for_local_z(profile=profile, frame_origin_xyz=frame_origin_xyz, local_z=local_z)
    world_face = face_xy.moved(plane.location)
    with bd.BuildPart() as builder:
        bd.add(world_face)
        bd.extrude(amount=amount, dir=profile.world_delta((0.0, 0.0, 1.0)))
    part = builder.part
    if part is None:
        raise RuntimeError("build123d extrusion produced no part")
    return part


def _box_xy_bounds(box: BoxSpec) -> RectBounds:
    origin_x, origin_y, _origin_z = box.origin_xyz
    size_x, size_y, _size_z = box.size_xyz
    return RectBounds(
        min_x=origin_x,
        max_x=origin_x + size_x,
        min_y=origin_y,
        max_y=origin_y + size_y,
    )


def modeled_body_bounds_from_boxes(
    boxes: tuple[BoxSpec, ...],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    if len(boxes) == 0:
        raise ValueError("modeled body bounds require at least one box")
    min_x = min(box.origin_xyz[0] for box in boxes)
    min_y = min(box.origin_xyz[1] for box in boxes)
    min_z = min(box.origin_xyz[2] for box in boxes)
    max_x = max(box.origin_xyz[0] + box.size_xyz[0] for box in boxes)
    max_y = max(box.origin_xyz[1] + box.size_xyz[1] for box in boxes)
    max_z = max(box.origin_xyz[2] + box.size_xyz[2] for box in boxes)
    return (
        (min_x, min_y, min_z),
        (max_x, max_y, max_z),
        (max_x - min_x, max_y - min_y, max_z - min_z),
    )


def _planar_outline_box_spec_from_copper_primitives(
    *,
    copper_primitives: tuple[CopperPrimitive, ...],
    layer_index: int,
    copper_z: float,
    copper_thickness_mm: float,
) -> BoxSpec:
    planar_primitives = tuple(
        primitive
        for primitive in copper_primitives
        if primitive.feature == "planar_segment"
    )
    if len(planar_primitives) == 0:
        raise ValueError(f"debug planar outline requires at least one planar primitive (layer={layer_index})")
    planar_bounds = _planar_bounds_from_polygons(tuple(primitive.polygon_xy for primitive in planar_primitives))
    return BoxSpec(
        label=f"copper_outline_l{layer_index}",
        role="copper",
        feature="planar_outline",
        layer_index=layer_index,
        origin_xyz=(planar_bounds.min_x, planar_bounds.min_y, copper_z),
        size_xyz=(planar_bounds.max_x - planar_bounds.min_x, planar_bounds.max_y - planar_bounds.min_y, copper_thickness_mm),
    )


def _pcb_box_spec_from_planar_outline_box(
    *,
    outline_box: BoxSpec,
    layer_index: int,
    pcb_z: float,
    pcb_thickness_mm: float,
    profile: SingleCoilProfile,
) -> BoxSpec:
    planar_bounds = _box_xy_bounds(outline_box)
    size_x = planar_bounds.max_x - planar_bounds.min_x
    size_y = planar_bounds.max_y - planar_bounds.min_y
    if size_x <= 0.0 or size_y <= 0.0:
        raise ValueError(
            "derived PCB planar footprint must have positive size "
            f"(layer={layer_index}, size_x={size_x}, size_y={size_y})"
        )
    return BoxSpec(
        label=f"{profile.pcb_body_prefix}_l{layer_index}",
        role="pcb",
        feature="pcb_layer",
        layer_index=layer_index,
        origin_xyz=(planar_bounds.min_x, planar_bounds.min_y, pcb_z),
        size_xyz=(size_x, size_y, pcb_thickness_mm),
    )


def build_tx_rect_void_box_specs(
    realized: RealizedSingleCoilRectVoid,
    *,
    profile: SingleCoilProfile = TX_SINGLE_COIL_PROFILE,
) -> tuple[BoxSpec, ...]:
    centerline = build_tx_rect_void_centerline(realized)
    boxes: list[BoxSpec] = []
    all_layer_copper_primitives: list[CopperPrimitive] = []
    for layer_index in range(realized.layer_count):
        pcb_z = float(layer_index) * (realized.pcb_thickness_mm + realized.layer_gap_mm)
        copper_primitives = _copper_primitives_for_layer(
            realized=realized,
            centerline=centerline,
            layer_index=layer_index,
            pcb_z=pcb_z,
            profile=profile,
        )
        _validate_copper_primitives_do_not_touch_void(realized, copper_primitives)
        _validate_copper_primitives_do_not_short(copper_primitives)
        all_layer_copper_primitives.extend(copper_primitives)
        outline_box = _planar_outline_box_spec_from_copper_primitives(
            copper_primitives=copper_primitives,
            layer_index=layer_index,
            copper_z=pcb_z + realized.pcb_thickness_mm,
            copper_thickness_mm=realized.copper_thickness_mm,
        )
        layer_copper_boxes = [outline_box] + [
            _copper_box_from_primitive(primitive)
            for primitive in copper_primitives
            if primitive.feature == "terminal_stub"
        ]
        boxes.append(
            _pcb_box_spec_from_planar_outline_box(
                outline_box=outline_box,
                layer_index=layer_index,
                pcb_z=pcb_z,
                pcb_thickness_mm=realized.pcb_thickness_mm,
                profile=profile,
            )
        )
        boxes.extend(layer_copper_boxes)
    if _is_tx_multilayer_parallel_stack(realized, profile=profile):
        bus_primitives = (
            _vertical_bus_primitive_from_stub_column(
                realized=realized,
                profile=profile,
                copper_primitives=tuple(all_layer_copper_primitives),
                terminal_column="start",
            ),
            _vertical_bus_primitive_from_stub_column(
                realized=realized,
                profile=profile,
                copper_primitives=tuple(all_layer_copper_primitives),
                terminal_column="end",
            ),
        )
        boxes.extend(_copper_box_from_primitive(primitive) for primitive in bus_primitives)
    return tuple(boxes)


def _build_box_shape(box_spec: BoxSpec) -> bd.Shape:
    size_x, size_y, size_z = box_spec.size_xyz
    if size_x <= 0.0 or size_y <= 0.0 or size_z <= 0.0:
        raise ValueError(f"box size must be positive for STEP export (box={box_spec})")
    shape = bd.Box(
        size_x,
        size_y,
        size_z,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    ).moved(bd.Location(box_spec.origin_xyz))
    solids = tuple(shape.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "box-derived STEP body must contain exactly one solid "
            f"(label={box_spec.label}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = box_spec.label
    return solid


def _expected_exported_body_names(
    realized: RealizedSingleCoilRectVoid,
    boxes: tuple[BoxSpec, ...],
    *,
    profile: SingleCoilProfile,
) -> tuple[str, ...]:
    pcb_names = tuple(box.label for box in boxes if box.role == "pcb")
    if _is_tx_multilayer_parallel_stack(realized, profile=profile):
        copper_names = (f"{profile.copper_body_prefix}_stack",)
    else:
        copper_layer_indices = tuple(sorted({box.layer_index for box in boxes if box.role == "copper"}))
        copper_names = tuple(f"{profile.copper_body_prefix}_l{layer_index}" for layer_index in copper_layer_indices)
    body_names = pcb_names + copper_names
    if len(body_names) == 0:
        raise ValueError("tx rect/void STEP scene requires at least one exported body")
    if len(body_names) != len(set(body_names)):
        raise ValueError(f"tx rect/void exported body names must be unique (actual={body_names})")
    return body_names


def _single_shape_from_fuse_result(fuse_result: object, *, label: str, source_count: int) -> bd.Shape:
    if isinstance(fuse_result, bd.ShapeList):
        raise RuntimeError(
            "build123d copper fuse returned multiple shapes "
            f"(label={label}, source_count={source_count}, result_count={len(fuse_result)})"
        )
    if not isinstance(fuse_result, bd.Shape):
        raise TypeError(f"build123d copper fuse returned unsupported result type: {type(fuse_result).__name__}")
    solids = tuple(fuse_result.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "fused copper layer must contain exactly one solid "
            f"(label={label}, source_count={source_count}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = label
    return solid


def _single_shape_from_cut_result(cut_result: object, *, label: str, tool_label: str) -> bd.Shape:
    if isinstance(cut_result, bd.ShapeList):
        raise RuntimeError(
            "build123d pcb cut returned multiple shapes "
            f"(label={label}, tool_label={tool_label}, result_count={len(cut_result)})"
        )
    if not isinstance(cut_result, bd.Shape):
        raise TypeError(f"build123d pcb cut returned unsupported result type: {type(cut_result).__name__}")
    solids = tuple(cut_result.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "cut pcb layer must contain exactly one solid "
            f"(label={label}, tool_label={tool_label}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = label
    return solid


def _extrude_copper_primitive(
    *,
    primitive: CopperPrimitive,
    profile: SingleCoilProfile,
    frame_origin_xyz: tuple[float, float, float],
) -> bd.Shape:
    return _extrude_face_on_plane(
        face_xy=_face_from_polygon_xy(primitive.polygon_xy),
        profile=profile,
        frame_origin_xyz=frame_origin_xyz,
        local_z=primitive.origin_z,
        amount=primitive.size_z,
    )


def _fused_copper_shape_from_primitives(
    *,
    copper_primitives: tuple[CopperPrimitive, ...],
    label: str,
    profile: SingleCoilProfile,
    frame_origin_xyz: tuple[float, float, float],
) -> bd.Shape:
    if len(copper_primitives) == 0:
        raise ValueError(f"tx rect/void copper shape requires at least one primitive (label={label})")
    fuse_result: object = _extrude_copper_primitive(
        primitive=copper_primitives[0],
        profile=profile,
        frame_origin_xyz=frame_origin_xyz,
    )
    for primitive in copper_primitives[1:]:
        fuse_result = cast(bd.Shape, fuse_result).fuse(
            _extrude_copper_primitive(
                primitive=primitive,
                profile=profile,
                frame_origin_xyz=frame_origin_xyz,
            )
        )
    return _single_shape_from_fuse_result(
        fuse_result,
        label=label,
        source_count=len(copper_primitives),
    )


def _build_copper_layer_shape(
    *,
    realized: RealizedSingleCoilRectVoid,
    boxes: tuple[BoxSpec, ...],
    centerline: tuple[tuple[float, float], ...],
    layer_index: int,
    profile: SingleCoilProfile,
    frame_origin_xyz: tuple[float, float, float],
) -> bd.Shape:
    _ = boxes
    pcb_z = float(layer_index) * (realized.pcb_thickness_mm + realized.layer_gap_mm)
    copper_primitives = _copper_primitives_for_layer(
        realized=realized,
        centerline=centerline,
        layer_index=layer_index,
        pcb_z=pcb_z,
        profile=profile,
    )
    _validate_copper_primitives_do_not_touch_void(realized, copper_primitives)
    _validate_copper_primitives_do_not_short(copper_primitives)
    return _fused_copper_shape_from_primitives(
        copper_primitives=copper_primitives,
        label=f"{profile.copper_body_prefix}_l{layer_index}",
        profile=profile,
        frame_origin_xyz=frame_origin_xyz,
    )


def _build_tx_multilayer_copper_stack_shape(
    *,
    realized: RealizedSingleCoilRectVoid,
    centerline: tuple[tuple[float, float], ...],
    profile: SingleCoilProfile,
    frame_origin_xyz: tuple[float, float, float],
) -> bd.Shape:
    if not _is_tx_multilayer_parallel_stack(realized, profile=profile):
        raise ValueError("tx multilayer copper stack shape requires tx_single_coil multilayer realized state")
    all_layer_copper_primitives: list[CopperPrimitive] = []
    for layer_index in range(realized.layer_count):
        pcb_z = float(layer_index) * (realized.pcb_thickness_mm + realized.layer_gap_mm)
        copper_primitives = _copper_primitives_for_layer(
            realized=realized,
            centerline=centerline,
            layer_index=layer_index,
            pcb_z=pcb_z,
            profile=profile,
        )
        _validate_copper_primitives_do_not_touch_void(realized, copper_primitives)
        _validate_copper_primitives_do_not_short(copper_primitives)
        all_layer_copper_primitives.extend(copper_primitives)
    bus_primitives = (
        _vertical_bus_primitive_from_stub_column(
            realized=realized,
            profile=profile,
            copper_primitives=tuple(all_layer_copper_primitives),
            terminal_column="start",
        ),
        _vertical_bus_primitive_from_stub_column(
            realized=realized,
            profile=profile,
            copper_primitives=tuple(all_layer_copper_primitives),
            terminal_column="end",
        ),
    )
    return _fused_copper_shape_from_primitives(
        copper_primitives=tuple(all_layer_copper_primitives) + bus_primitives,
        label=f"{profile.copper_body_prefix}_stack",
        profile=profile,
        frame_origin_xyz=frame_origin_xyz,
    )


def _cut_pcb_shape_with_copper(
    *,
    pcb_shape: bd.Shape,
    copper_shape: bd.Shape,
) -> bd.Shape:
    return _single_shape_from_cut_result(
        pcb_shape.cut(copper_shape),
        label=pcb_shape.label,
        tool_label=copper_shape.label,
    )


def build_tx_rect_void_step_scene(
    realized: RealizedSingleCoilRectVoid,
    boxes: tuple[BoxSpec, ...],
    *,
    profile: SingleCoilProfile = TX_SINGLE_COIL_PROFILE,
    frame_origin_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bd.Compound:
    if not boxes:
        raise ValueError("tx rect/void STEP scene requires at least one box")
    expected_body_names = _expected_exported_body_names(realized, boxes, profile=profile)
    pcb_shapes = tuple(_build_box_shape(box_spec) for box_spec in boxes if box_spec.role == "pcb")
    centerline = build_tx_rect_void_centerline(realized)
    if _is_tx_multilayer_parallel_stack(realized, profile=profile):
        copper_shapes = (
            _build_tx_multilayer_copper_stack_shape(
                realized=realized,
                centerline=centerline,
                profile=profile,
                frame_origin_xyz=frame_origin_xyz,
            ),
        )
        cut_pcb_shapes = tuple(
            _cut_pcb_shape_with_copper(
                pcb_shape=pcb_shape,
                copper_shape=copper_shapes[0],
            )
            for pcb_shape in pcb_shapes
        )
    else:
        copper_layer_indices = tuple(sorted({box.layer_index for box in boxes if box.role == "copper"}))
        copper_shapes = tuple(
            _build_copper_layer_shape(
                realized=realized,
                boxes=boxes,
                centerline=centerline,
                layer_index=layer_index,
                profile=profile,
                frame_origin_xyz=frame_origin_xyz,
            )
            for layer_index in copper_layer_indices
        )
        copper_shape_by_layer = {
            layer_index: copper_shape
            for layer_index, copper_shape in zip(copper_layer_indices, copper_shapes, strict=True)
        }
        cut_pcb_shapes_list: list[bd.Shape] = []
        for pcb_shape, pcb_box in zip(
            pcb_shapes,
            tuple(box for box in boxes if box.role == "pcb"),
            strict=True,
        ):
            assert pcb_box.layer_index in copper_shape_by_layer
            cut_pcb_shapes_list.append(
                _cut_pcb_shape_with_copper(
                    pcb_shape=pcb_shape,
                    copper_shape=copper_shape_by_layer[pcb_box.layer_index],
                )
            )
        cut_pcb_shapes = tuple(cut_pcb_shapes_list)
    shapes = cut_pcb_shapes + copper_shapes
    actual_body_names = tuple(shape.label for shape in shapes)
    if actual_body_names != expected_body_names:
        raise RuntimeError(
            "tx rect/void exported body name mismatch "
            f"(expected={expected_body_names}, actual={actual_body_names})"
        )
    expected_body_count = len(expected_body_names)
    if len(shapes) != expected_body_count:
        raise RuntimeError(
            "type2 v1 tx rect/void STEP scene exported unexpected body count "
            f"(expected={expected_body_count}, actual={len(shapes)}, names={actual_body_names})"
        )
    return bd.Compound(children=shapes, label=profile.compound_label)


def _tx_multilayer_bottom_bus_plane_points(
    *,
    boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
) -> tuple[tuple[float, float], tuple[float, float]]:
    if profile.role != "tx_single_coil":
        raise ValueError("multilayer bus plane points are only defined for tx_single_coil")
    start_label = f"{profile.copper_body_prefix}_bus_start"
    end_label = f"{profile.copper_body_prefix}_bus_end"
    start_matches = [box for box in boxes if box.label == start_label]
    end_matches = [box for box in boxes if box.label == end_label]
    if len(start_matches) != 1 or len(end_matches) != 1:
        raise ValueError(
            "tx multilayer terminal metadata requires exactly one start/end bus box "
            f"(start_matches={len(start_matches)}, end_matches={len(end_matches)})"
        )
    start_box = start_matches[0]
    end_box = end_matches[0]
    return (
        (
            start_box.origin_xyz[0] + (start_box.size_xyz[0] / 2.0),
            start_box.origin_xyz[1] + (start_box.size_xyz[1] / 2.0),
        ),
        (
            end_box.origin_xyz[0] + (end_box.size_xyz[0] / 2.0),
            end_box.origin_xyz[1] + (end_box.size_xyz[1] / 2.0),
        ),
    )


def _write_metadata(path: Path, result: SingleCoilRectVoidExportResult) -> None:
    payload = asdict(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_modeled_object_entry(
    *,
    realized: RealizedSingleCoilRectVoid,
    profile: SingleCoilProfile,
    output_step_path: Path,
    expected_exported_body_names: tuple[str, ...],
    placement_offset_xyz: tuple[float, float, float],
    boxes: tuple[BoxSpec, ...],
) -> ModeledObjectEntry:
    terminal_path = _parse_terminal_path(realized.terminal_path)
    centerline = build_tx_rect_void_centerline(realized)
    world_bounds_min_xyz, world_bounds_max_xyz, world_bounds_size_xyz = modeled_body_bounds_from_boxes(boxes)
    pcb_boxes = tuple(box for box in boxes if box.role == "pcb")
    copper_position_boxes = tuple(
        box for box in boxes if box.role == "copper" and box.feature == "planar_outline"
    )
    copper_position_boxes_by_layer: dict[int, BoxSpec] = {}
    for copper_box in copper_position_boxes:
        if copper_box.layer_index not in copper_position_boxes_by_layer:
            copper_position_boxes_by_layer[copper_box.layer_index] = copper_box
    if len(copper_position_boxes_by_layer) != realized.layer_count:
        raise ValueError(
            "modeled object canonical copper layer positions require one planar outline layer representative per layer "
            f"(expected={realized.layer_count}, actual={len(copper_position_boxes_by_layer)})"
        )
    pcb_layer_world_positions_mm = tuple(
        box.origin_xyz[2 if profile.plane == "XY" else 0]
        for box in sorted(pcb_boxes, key=lambda box: box.layer_index)
    )
    copper_layer_world_positions_mm = tuple(
        box.origin_xyz[2 if profile.plane == "XY" else 0]
        for box in sorted(copper_position_boxes_by_layer.values(), key=lambda box: box.layer_index)
    )
    if _is_tx_multilayer_parallel_stack(realized, profile=profile):
        start_point_plane_mm, end_point_plane_mm = _tx_multilayer_bottom_bus_plane_points(
            boxes=boxes,
            profile=profile,
        )
    else:
        start_point_plane_mm = profile.plane_point(centerline[0], frame_origin_xyz=placement_offset_xyz)
        end_point_plane_mm = profile.plane_point(centerline[-1], frame_origin_xyz=placement_offset_xyz)
    return ModeledObjectEntry(
        object_id=profile.object_id,
        role=profile.role,
        plane=profile.plane,
        placement_owner_id=profile.placement_owner_id,
        material="composite",
        model_state=True,
        step_path=str(output_step_path),
        expected_exported_body_names=expected_exported_body_names,
        expected_exported_body_count=len(expected_exported_body_names),
        canonical_coordinates=ModeledObjectCanonicalCoordinates(
            frame_origin_xyz=placement_offset_xyz,
            outer_bounds_min_xyz=world_bounds_min_xyz,
            outer_bounds_max_xyz=world_bounds_max_xyz,
            outer_bounds_size_xyz=world_bounds_size_xyz,
            pcb_layer_z_positions_mm=pcb_layer_world_positions_mm,
            copper_layer_z_positions_mm=copper_layer_world_positions_mm,
        ),
        terminal_metadata=ModeledObjectTerminalMetadata(
            path=terminal_path.raw,
            outer_corner=terminal_path.outer_corner,
            inner_corner=terminal_path.inner_corner,
            direction=terminal_path.direction,
            start_point_plane_mm=start_point_plane_mm,
            end_point_plane_mm=end_point_plane_mm,
        ),
    )


def export_tx_rect_void_step_from_spec(
    *,
    spec: SingleCoilRectVoidSpec,
    source_toml_path: Path,
    output_step_path: Path,
    metadata_path: Path,
    seed: int,
    placement_offset_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
    profile: SingleCoilProfile = TX_SINGLE_COIL_PROFILE,
) -> SingleCoilRectVoidExportResult:
    realized = realize_tx_rect_void_spec(spec, seed=seed, profile=profile)
    local_boxes = build_tx_rect_void_box_specs(realized, profile=profile)
    boxes = tuple(
        _transform_box_spec(
            box_spec,
            profile=profile,
            frame_origin_xyz=placement_offset_xyz,
        )
        for box_spec in local_boxes
    )
    scene = build_tx_rect_void_step_scene(
        realized,
        boxes,
        profile=profile,
        frame_origin_xyz=placement_offset_xyz,
    )
    expected_exported_body_names = _expected_exported_body_names(realized, boxes, profile=profile)
    output_step_path.parent.mkdir(parents=True, exist_ok=True)
    export_ok = bd.export_step(scene, output_step_path)
    if export_ok is not True:
        raise RuntimeError(f"build123d export_step returned False: {output_step_path}")
    modeled_object = _build_modeled_object_entry(
        realized=realized,
        profile=profile,
        output_step_path=output_step_path,
        expected_exported_body_names=expected_exported_body_names,
        placement_offset_xyz=placement_offset_xyz,
        boxes=boxes,
    )
    result = SingleCoilRectVoidExportResult(
        source_toml_path=str(source_toml_path),
        output_step_path=str(output_step_path),
        metadata_path=str(metadata_path),
        expected_exported_body_names=expected_exported_body_names,
        expected_exported_body_count=len(expected_exported_body_names),
        realized=realized,
        boxes=boxes,
        modeled_objects=(modeled_object,),
    )
    _write_metadata(metadata_path, result)
    return result


def export_tx_rect_void_step(
    *,
    toml_path: Path,
    output_step_path: Path,
    metadata_path: Path,
    seed: int,
) -> SingleCoilRectVoidExportResult:
    spec = load_tx_rect_void_spec(toml_path)
    return export_tx_rect_void_step_from_spec(
        spec=spec,
        source_toml_path=toml_path,
        output_step_path=output_step_path,
        metadata_path=metadata_path,
        seed=seed,
    )


__all__ = [
    "build_tx_rect_void_box_specs",
    "build_tx_rect_void_step_scene",
    "export_tx_rect_void_step",
    "export_tx_rect_void_step_from_spec",
    "modeled_body_bounds_from_boxes",
]

from __future__ import annotations

import hashlib
import math
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import build123d as bd

from peetsfea.tx_rect_void import BoxSpec
from peetsfea.tx_rect_void import SingleCoilProfile
from peetsfea.tx_rect_void import build_tx_rect_void_box_specs
from peetsfea.tx_rect_void import build_tx_rect_void_centerline
from peetsfea.tx_rect_void import load_tx_rect_void_spec
from peetsfea.tx_rect_void import modeled_body_bounds_from_boxes
from peetsfea.tx_rect_void import realize_tx_rect_void_spec
from peetsfea.tx_rect_void_geometry import _segment_joined_polygon
from peetsfea.type2_step_spec import ModeledSingleCoilCommonSpec
from peetsfea.type2_step_spec import ModeledTxRectVoidColumnsSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import Point3
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import render_tx_rect_void_toml
from peetsfea.type2_tx_turns import TxConnectionMode
from peetsfea.type2_tx_turns import resolve_tx_turns

_MAX_BODY_LABEL_LENGTH = 32
_TX_RECT_VOID_COLUMNS_PROFILE = SingleCoilProfile(
    role="rx_single_coil",
    object_id="tx_rect_void_columns",
    plane="XY",
    placement_owner_id="tx_region_actual_stack_space",
    pcb_body_prefix="txrvpcb",
    copper_body_prefix="txrvcu",
    compound_label="tx_rect_void_columns_member",
    max_turn_count=36,
)


@dataclass(frozen=True)
class TxRectVoidColumnsTileScene:
    stack_space_object_id: str
    tx_region_actual_object_id: str
    x_index: int
    y_index: int
    stack_space_center_xyz: Point3
    resolved_turn_count: int
    terminal_stub_body_names: tuple[tuple[str, str], ...]
    scene_shapes: tuple[bd.Shape, ...]


@dataclass(frozen=True)
class TxRectVoidColumnsTileTerminalAnchors:
    stack_space_object_id: str
    x_index: int
    y_index: int
    terminal_stub_body_names: tuple[tuple[str, str], ...]
    terminal_anchor_box_specs: tuple[tuple[BoxSpec, BoxSpec], ...]


@dataclass(frozen=True)
class TxRectVoidColumnsBuildResult:
    tile_scenes: tuple[TxRectVoidColumnsTileScene, ...]
    tile_terminal_anchors: tuple[TxRectVoidColumnsTileTerminalAnchors, ...]
    tile_resolved_turn_counts: tuple[int, ...]
    expected_exported_body_names: tuple[str, ...]
    terminal_stub_length_mm: float
    layer_count: int
    connection_mode: TxConnectionMode


@dataclass(frozen=True)
class _ResolvedSingleCoilRangeSpec:
    pcb_thickness_mm: float
    copper_thickness_mm: float
    layer_count: int
    layer_gap_mm: float
    terminal_stub_length_mm: float
    void_usage_ratio: float
    margin_ratio: float
    metal_fill_factor: float
    terminal_path: str


_TX_CONNECTION_MODES: tuple[TxConnectionMode, TxConnectionMode] = (0, 1)
Point2 = tuple[float, float]
Polygon2 = tuple[Point2, ...]


@dataclass(frozen=True)
class _RenderedSingleCoilSpec:
    pcb_thickness_mm: float
    copper_thickness_mm: float
    outer_x_mm: RangeSpec
    outer_y_mm: RangeSpec
    turn_count: RangeSpec
    layer_count: RangeSpec
    layer_gap_mm: RangeSpec
    terminal_stub_length_mm: RangeSpec
    void_usage_ratio: RangeSpec
    margin_ratio: RangeSpec
    metal_fill_factor: RangeSpec
    terminal_path: str


def _float_range_candidates(range_spec: RangeSpec) -> tuple[float, ...]:
    if range_spec.is_integer is not False:
        raise ValueError("tx_rect_void_columns float range candidates require non-integer range")
    if range_spec.count == 1:
        return (range_spec.start,)
    step = (range_spec.end - range_spec.start) / float(range_spec.count - 1)
    return tuple(range_spec.start + (step * index) for index in range(range_spec.count))


def _integer_range_candidates(range_spec: RangeSpec) -> tuple[int, ...]:
    if range_spec.is_integer is not True:
        raise ValueError("tx_rect_void_columns integer range candidates require integer range")
    if range_spec.count == 1:
        value = int(round(range_spec.start))
        if not math.isclose(range_spec.start, float(value), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(
                "tx_rect_void_columns fixed integer range must realize to integer "
                f"(start={range_spec.start})"
            )
        return (value,)
    step = (range_spec.end - range_spec.start) / float(range_spec.count - 1)
    candidates: list[int] = []
    for index in range(range_spec.count):
        raw_value = range_spec.start + (step * index)
        int_value = int(round(raw_value))
        if not math.isclose(raw_value, float(int_value), rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(
                "tx_rect_void_columns integer range must realize to integer candidates "
                f"(raw_value={raw_value}, int_value={int_value}, index={index})"
            )
        candidates.append(int_value)
    return tuple(candidates)


def _selected_float_candidate(*, range_spec: RangeSpec, owner_path: str, seed: int) -> float:
    candidates = _float_range_candidates(range_spec)
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated for tx_rect_void_columns owner: {owner_path}")
    if len(candidates) == 1:
        return candidates[0]
    digest = hashlib.blake2b(f"{seed}:{owner_path}".encode("utf-8"), digest_size=8).digest()
    index = int.from_bytes(digest, byteorder="big", signed=False) % len(candidates)
    return candidates[index]


def _selected_integer_candidate(*, range_spec: RangeSpec, owner_path: str, seed: int) -> int:
    candidates = _integer_range_candidates(range_spec)
    if len(candidates) == 0:
        raise ValueError(f"No integer candidates generated for tx_rect_void_columns owner: {owner_path}")
    if len(candidates) == 1:
        return candidates[0]
    digest = hashlib.blake2b(f"{seed}:{owner_path}".encode("utf-8"), digest_size=8).digest()
    index = int.from_bytes(digest, byteorder="big", signed=False) % len(candidates)
    return candidates[index]


def _selected_feasible_layer_count_and_gap(
    *,
    layer_count_spec: RangeSpec,
    layer_gap_mm_spec: RangeSpec,
    owner_prefix: str,
    stack_space_height_mm: float,
    pcb_thickness_mm: float,
    copper_thickness_mm: float,
    seed: int,
) -> tuple[int, float]:
    if stack_space_height_mm <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns stack-space height must be positive "
            f"(actual={stack_space_height_mm})"
        )
    layer_count_candidates = _integer_range_candidates(layer_count_spec)
    layer_gap_candidates = _float_range_candidates(layer_gap_mm_spec)
    base_height_mm = pcb_thickness_mm + copper_thickness_mm
    feasible_pairs: list[tuple[int, float]] = []
    for layer_count in layer_count_candidates:
        if layer_count < 1 or layer_count > 4:
            continue
        for layer_gap_mm in layer_gap_candidates:
            full_stack_height_mm = base_height_mm + (float(layer_count - 1) * (pcb_thickness_mm + layer_gap_mm))
            if full_stack_height_mm <= stack_space_height_mm + 1e-9:
                feasible_pairs.append((layer_count, layer_gap_mm))
    if len(feasible_pairs) == 0:
        raise RuntimeError(
            "tx_rect_void_columns layer_count/layer_gap_mm ranges have no stack-height-feasible candidate "
            f"(stack_space_height_mm={stack_space_height_mm}, base_height_mm={base_height_mm})"
        )
    owner_path = f"{owner_prefix}.layer_count+layer_gap_mm"
    digest = hashlib.blake2b(f"{seed}:{owner_path}".encode("utf-8"), digest_size=8).digest()
    index = int.from_bytes(digest, byteorder="big", signed=False) % len(feasible_pairs)
    return feasible_pairs[index]


def _selected_parallel_total_turn_count(
    *, spec: ModeledTxRectVoidColumnsSpec, owner_path: str, seed: int
) -> float:
    if not hasattr(spec, "parallel_total_turn_count"):
        raise RuntimeError(
            "tx_rect_void_columns parallel_total_turn_count is not available in the resolved spec "
            f"(owner={owner_path})"
        )
    parallel_total_turn_count = getattr(spec, "parallel_total_turn_count")
    if isinstance(parallel_total_turn_count, bool) or not isinstance(parallel_total_turn_count, RangeSpec):
        raise RuntimeError(
            "tx_rect_void_columns parallel_total_turn_count must resolve as a RangeSpec "
            f"(owner={owner_path}, actual={type(parallel_total_turn_count)!r})"
        )
    if parallel_total_turn_count.is_integer is True:
        return float(
            _selected_integer_candidate(
                range_spec=parallel_total_turn_count,
                owner_path=f"{owner_path}",
                seed=seed,
            )
        )
    if parallel_total_turn_count.is_integer is False:
        return _selected_float_candidate(
            range_spec=parallel_total_turn_count,
            owner_path=f"{owner_path}",
            seed=seed,
        )
    raise RuntimeError(
        "tx_rect_void_columns parallel_total_turn_count owner must be integer-capable "
        f"(owner={owner_path}, is_integer={parallel_total_turn_count.is_integer})"
    )


def _fixed_float_range(*, value: float) -> RangeSpec:
    return RangeSpec(is_integer=False, start=value, end=value, count=1)


def _fixed_int_range(*, value: int) -> RangeSpec:
    return RangeSpec(is_integer=True, start=float(value), end=float(value), count=1)


def _parse_stack_space_tile_indices(*, object_id: str) -> tuple[int, int]:
    if object_id == "tx_region_actual_stack_space":
        return (0, 0)
    if not object_id.startswith("tx_region_actual_stack_space_x"):
        raise RuntimeError(
            "tx_rect_void_columns stack-space tile id must start with tx_region_actual_stack_space_x "
            f"(actual={object_id})"
        )
    if "_y" not in object_id:
        raise RuntimeError(
            "tx_rect_void_columns stack-space tile id must include _y suffix "
            f"(actual={object_id})"
        )
    x_fragment, y_fragment = object_id.split("_y", maxsplit=1)
    x_text = x_fragment[len("tx_region_actual_stack_space_x") :]
    if x_text == "" or y_fragment == "":
        raise RuntimeError(
            "tx_rect_void_columns stack-space tile id indices must be non-empty "
            f"(actual={object_id})"
        )
    if not x_text.isdigit() or not y_fragment.isdigit():
        raise RuntimeError(
            "tx_rect_void_columns stack-space tile id indices must be digits "
            f"(actual={object_id})"
        )
    return (int(x_text), int(y_fragment))


def _parent_tx_region_actual_object_id_for_stack_space(*, object_id: str) -> str:
    if object_id == "tx_region_actual_stack_space":
        return "tx_region_actual"
    return f"tx_region_actual{object_id.removeprefix('tx_region_actual_stack_space')}"


def _single_coil_placement_offset_from_local_bounds(
    *,
    owner_spec: NonModelBoxSpec,
    local_bounds_min_xyz: Point3,
    local_size_xyz: Point3,
) -> Point3:
    if owner_spec.plane != _TX_RECT_VOID_COLUMNS_PROFILE.plane:
        raise RuntimeError(
            "tx_rect_void_columns placement owner plane must match profile plane "
            f"(owner={owner_spec.object_id}, owner_plane={owner_spec.plane}, profile_plane={_TX_RECT_VOID_COLUMNS_PROFILE.plane})"
        )
    world_size_xyz = _TX_RECT_VOID_COLUMNS_PROFILE.world_size(local_size_xyz)
    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    if world_size_xyz[0] > owner_size_x or world_size_xyz[1] > owner_size_y or world_size_xyz[2] > owner_size_z:
        raise RuntimeError(
            "tx_rect_void_columns realized bounds must fit inside stack-space owner "
            f"(owner={owner_spec.object_id}, realized_size={world_size_xyz}, owner_size={owner_spec.size_xyz})"
        )
    target_world_min_xyz = (
        owner_origin_x,
        owner_origin_y + (owner_size_y - world_size_xyz[1]) / 2.0,
        owner_origin_z + owner_size_z - world_size_xyz[2],
    )
    world_min_delta = _TX_RECT_VOID_COLUMNS_PROFILE.world_delta(local_bounds_min_xyz)
    return (
        target_world_min_xyz[0] - world_min_delta[0],
        target_world_min_xyz[1] - world_min_delta[1],
        target_world_min_xyz[2] - world_min_delta[2],
    )


def _transform_modeled_box_spec(
    box_spec: BoxSpec,
    *,
    frame_origin_xyz: Point3,
) -> BoxSpec:
    return BoxSpec(
        label=box_spec.label,
        role=box_spec.role,
        feature=box_spec.feature,
        layer_index=box_spec.layer_index,
        origin_xyz=_TX_RECT_VOID_COLUMNS_PROFILE.world_point(box_spec.origin_xyz, frame_origin_xyz=frame_origin_xyz),
        size_xyz=_TX_RECT_VOID_COLUMNS_PROFILE.world_size(box_spec.size_xyz),
    )


def _single_solid_shape(*, shape: bd.Shape, label: str, context: str) -> bd.Shape:
    solids = tuple(shape.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "tx_rect_void_columns shape operation must yield exactly one solid "
            f"(label={label}, context={context}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = label
    return solid


def _box_shape_from_spec(box_spec: BoxSpec) -> bd.Shape:
    size_x, size_y, size_z = box_spec.size_xyz
    if size_x <= 0.0 or size_y <= 0.0 or size_z <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns box shape requires positive size "
            f"(label={box_spec.label}, size_xyz={box_spec.size_xyz})"
        )
    shape = bd.Box(
        size_x,
        size_y,
        size_z,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    ).moved(bd.Location(box_spec.origin_xyz))
    return _single_solid_shape(
        shape=shape,
        label=box_spec.label,
        context="box",
    )


def _face_from_polygon_xy(polygon_xy: Polygon2) -> bd.Face:
    with bd.BuildLine() as builder:
        bd.Polyline(*polygon_xy, close=True)
    line = builder.line
    if line is None:
        raise RuntimeError("tx_rect_void_columns polygon face builder produced no line")
    wires = tuple(line.wires())
    if len(wires) != 1:
        raise RuntimeError(
            "tx_rect_void_columns polygon face builder must produce exactly one wire "
            f"(actual={len(wires)})"
        )
    return cast(bd.Face, bd.make_face(edges=tuple(wires[0].edges())))


def _extrude_face_xy(
    *,
    face_xy: bd.Face,
    origin_z: float,
    size_z: float,
    label: str,
) -> bd.Shape:
    if size_z <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns face extrusion requires positive height "
            f"(label={label}, size_z={size_z})"
        )
    with bd.BuildPart() as builder:
        bd.add(face_xy.moved(bd.Location((0.0, 0.0, origin_z))))
        bd.extrude(amount=size_z, dir=(0.0, 0.0, 1.0))
    part = builder.part
    if part is None:
        raise RuntimeError(
            "tx_rect_void_columns face extrusion produced no part "
            f"(label={label})"
        )
    return _single_solid_shape(shape=part, label=label, context="extrude")


def _translated_box_spec(
    box_spec: BoxSpec,
    *,
    translation_xyz: Point3,
    label: str,
) -> BoxSpec:
    return BoxSpec(
        label=label,
        role=box_spec.role,
        feature=box_spec.feature,
        layer_index=box_spec.layer_index,
        origin_xyz=(
            box_spec.origin_xyz[0] + translation_xyz[0],
            box_spec.origin_xyz[1] + translation_xyz[1],
            box_spec.origin_xyz[2] + translation_xyz[2],
        ),
        size_xyz=box_spec.size_xyz,
    )


def _scale_translate_polygon_xy(
    polygon_xy: Polygon2,
    *,
    local_min_xy: tuple[float, float],
    fit_scale_x: float,
    fit_scale_y: float,
    translation_xy: tuple[float, float],
) -> Polygon2:
    local_min_x, local_min_y = local_min_xy
    translation_x, translation_y = translation_xy
    return tuple(
        (
            local_min_x + ((point_x - local_min_x) * fit_scale_x) + translation_x,
            local_min_y + ((point_y - local_min_y) * fit_scale_y) + translation_y,
        )
        for point_x, point_y in polygon_xy
    )


def _transformed_trace_face_from_centerline(
    *,
    centerline: tuple[Point2, ...],
    trace_width_mm: float,
    local_min_xy: tuple[float, float],
    fit_scale_x: float,
    fit_scale_y: float,
    translation_xy: tuple[float, float],
) -> bd.Face:
    segment_count = len(centerline) - 1
    if segment_count < 1:
        raise RuntimeError(
            "tx_rect_void_columns trace face requires at least one segment "
            f"(centerline_count={len(centerline)})"
        )
    segment_faces = tuple(
        _face_from_polygon_xy(
            _scale_translate_polygon_xy(
                _segment_joined_polygon(
                    centerline,
                    trace_width_mm=trace_width_mm,
                    segment_index=segment_index,
                ),
                local_min_xy=local_min_xy,
                fit_scale_x=fit_scale_x,
                fit_scale_y=fit_scale_y,
                translation_xy=translation_xy,
            )
        )
        for segment_index in range(segment_count)
    )
    fused_face: object = segment_faces[0]
    for segment_face in segment_faces[1:]:
        fused_face = cast(bd.Face, fused_face).fuse(segment_face)
    if isinstance(fused_face, bd.ShapeList):
        raise RuntimeError(
            "tx_rect_void_columns trace face fuse returned multiple shapes "
            f"(centerline_count={len(centerline)}, segment_count={segment_count}, result_count={len(fused_face)})"
        )
    if not isinstance(fused_face, bd.Face):
        raise TypeError(
            "tx_rect_void_columns trace face fuse returned unsupported type "
            f"(type={type(fused_face).__name__})"
        )
    if len(tuple(fused_face.wires())) != 1:
        raise RuntimeError(
            "tx_rect_void_columns trace face fuse must produce one wire "
            f"(centerline_count={len(centerline)}, wire_count={len(tuple(fused_face.wires()))})"
        )
    return fused_face


def _resolved_column_range_spec(
    *,
    spec: ModeledTxRectVoidColumnsSpec,
    turn_count: int,
    layer_count: int,
    outer_x_mm: float,
    outer_y_mm: float,
    layer_gap_mm: float,
    terminal_stub_length_mm: float,
    void_usage_ratio: float,
    margin_ratio: float,
    metal_fill_factor: float,
) -> _RenderedSingleCoilSpec:
    return _RenderedSingleCoilSpec(
        pcb_thickness_mm=spec.pcb_thickness_mm,
        copper_thickness_mm=spec.copper_thickness_mm,
        outer_x_mm=_fixed_float_range(value=outer_x_mm),
        outer_y_mm=_fixed_float_range(value=outer_y_mm),
        turn_count=_fixed_int_range(value=turn_count),
        layer_count=_fixed_int_range(value=layer_count),
        layer_gap_mm=_fixed_float_range(value=layer_gap_mm),
        terminal_stub_length_mm=_fixed_float_range(value=terminal_stub_length_mm),
        void_usage_ratio=_fixed_float_range(value=void_usage_ratio),
        margin_ratio=_fixed_float_range(value=margin_ratio),
        metal_fill_factor=_fixed_float_range(value=metal_fill_factor),
        terminal_path=spec.terminal_path,
    )


def _resolved_single_coil_range_spec(
    *,
    spec: ModeledTxRectVoidColumnsSpec,
    stack_space_height_mm: float,
    seed: int,
) -> _ResolvedSingleCoilRangeSpec:
    owner_prefix = f"modeled_objects.{spec.object_id}"
    layer_count, layer_gap_mm = _selected_feasible_layer_count_and_gap(
        layer_count_spec=spec.layer_count,
        layer_gap_mm_spec=spec.layer_gap_mm,
        owner_prefix=owner_prefix,
        stack_space_height_mm=stack_space_height_mm,
        pcb_thickness_mm=spec.pcb_thickness_mm,
        copper_thickness_mm=spec.copper_thickness_mm,
        seed=seed,
    )
    if layer_count < 1 or layer_count > 4:
        raise RuntimeError(f"tx_rect_void_columns.layer_count must resolve to [1, 4] (actual={layer_count})")
    return _ResolvedSingleCoilRangeSpec(
        pcb_thickness_mm=spec.pcb_thickness_mm,
        copper_thickness_mm=spec.copper_thickness_mm,
        layer_count=layer_count,
        layer_gap_mm=layer_gap_mm,
        terminal_stub_length_mm=_selected_float_candidate(
            range_spec=spec.terminal_stub_length_mm,
            owner_path=f"{owner_prefix}.terminal_stub_length_mm",
            seed=seed,
        ),
        void_usage_ratio=_selected_float_candidate(
            range_spec=spec.void_usage_ratio,
            owner_path=f"{owner_prefix}.void_usage_ratio",
            seed=seed,
        ),
        margin_ratio=_selected_float_candidate(
            range_spec=spec.margin_ratio,
            owner_path=f"{owner_prefix}.margin_ratio",
            seed=seed,
        ),
        metal_fill_factor=_selected_float_candidate(
            range_spec=spec.metal_fill_factor,
            owner_path=f"{owner_prefix}.metal_fill_factor",
            seed=seed,
        ),
        terminal_path=spec.terminal_path,
    )


def _realized_boxes_for_column(
    *,
    spec: ModeledTxRectVoidColumnsSpec,
    resolved_ranges: _ResolvedSingleCoilRangeSpec,
    owner_spec: NonModelBoxSpec,
    turn_count: int,
    seed: int,
) -> tuple[tuple[bd.Shape, ...], tuple[tuple[BoxSpec, BoxSpec], ...], int]:
    owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
    target_outer_x_mm = owner_size_x
    target_outer_y_mm = owner_size_y
    if target_outer_x_mm <= 0.0 or target_outer_y_mm <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns resolved outer size must be positive "
            f"(owner={owner_spec.object_id}, outer_x_mm={target_outer_x_mm}, outer_y_mm={target_outer_y_mm})"
        )
    if target_outer_x_mm > owner_size_x + 1e-9 or target_outer_y_mm > owner_size_y + 1e-9:
        raise RuntimeError(
            "tx_rect_void_columns resolved outer size must fit stack-space owner footprint "
            f"(owner={owner_spec.object_id}, outer=({target_outer_x_mm}, {target_outer_y_mm}), owner_size={owner_spec.size_xyz})"
        )
    rendered_layer_gap_mm = max(resolved_ranges.layer_gap_mm, 2.0)
    rendered_spec = _resolved_column_range_spec(
        spec=spec,
        turn_count=turn_count,
        layer_count=1,
        outer_x_mm=target_outer_x_mm,
        outer_y_mm=target_outer_y_mm,
        layer_gap_mm=rendered_layer_gap_mm,
        terminal_stub_length_mm=resolved_ranges.terminal_stub_length_mm,
        void_usage_ratio=resolved_ranges.void_usage_ratio,
        margin_ratio=resolved_ranges.margin_ratio,
        metal_fill_factor=resolved_ranges.metal_fill_factor,
    )
    with tempfile.TemporaryDirectory(prefix="type2_tx_rect_void_columns_") as temp_dir:
        temp_toml_path = Path(temp_dir) / f"{spec.object_id}.toml"
        temp_toml_path.write_text(
            render_tx_rect_void_toml(cast(ModeledSingleCoilCommonSpec, rendered_spec)),
            encoding="utf-8",
        )
        tx_rect_void_spec = load_tx_rect_void_spec(temp_toml_path)
        realized = realize_tx_rect_void_spec(
            tx_rect_void_spec,
            seed=seed,
            profile=_TX_RECT_VOID_COLUMNS_PROFILE,
        )
    local_centerline = build_tx_rect_void_centerline(realized)
    local_boxes = build_tx_rect_void_box_specs(realized, profile=_TX_RECT_VOID_COLUMNS_PROFILE)
    local_reference_boxes = tuple(
        box
        for box in local_boxes
        if box.role == "pcb" or (box.role == "copper" and box.feature == "planar_outline")
    )
    if len(local_reference_boxes) == 0:
        raise RuntimeError(
            "tx_rect_void_columns realized single-layer geometry must expose at least one exported base box "
            f"(owner={owner_spec.object_id}, role={ _TX_RECT_VOID_COLUMNS_PROFILE.role})"
        )
    local_min_xyz, _local_max_xyz, local_size_xyz = modeled_body_bounds_from_boxes(local_reference_boxes)
    _all_local_min_xyz, _all_local_max_xyz, all_local_size_xyz = modeled_body_bounds_from_boxes(local_boxes)
    _all_local_size_x, _all_local_size_y, all_local_size_z = all_local_size_xyz
    local_size_x, local_size_y, local_size_z = local_size_xyz
    if local_size_x <= 0.0 or local_size_y <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns realized base bounds must have positive XY size "
            f"(owner={owner_spec.object_id}, local_size_x={local_size_x}, local_size_y={local_size_y})"
        )
    if local_size_z <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns realized base bounds must have positive Z size "
            f"(owner={owner_spec.object_id}, local_size_z={local_size_z})"
        )
    if all_local_size_z <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns realized full local bounds must have positive Z size "
            f"(owner={owner_spec.object_id}, local_size_z={all_local_size_z})"
        )
    layer_step_mm = resolved_ranges.pcb_thickness_mm + resolved_ranges.layer_gap_mm
    full_stack_height_mm = all_local_size_z + (float(resolved_ranges.layer_count - 1) * layer_step_mm)
    if full_stack_height_mm > owner_size_z + 1e-9:
        raise RuntimeError(
            "tx_rect_void_columns resolved full stack height must fit stack-space owner height "
            f"(owner={owner_spec.object_id}, stack_height={full_stack_height_mm}, owner_height={owner_size_z})"
        )
    fit_scale_x = target_outer_x_mm / local_size_x
    fit_scale_y = target_outer_y_mm / local_size_y
    if fit_scale_x <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns fit scale X must be positive "
            f"(owner={owner_spec.object_id}, fit_scale_x={fit_scale_x})"
        )
    if fit_scale_y <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns fit scale Y must be positive "
            f"(owner={owner_spec.object_id}, fit_scale_y={fit_scale_y})"
        )
    scaled_local_boxes: list[BoxSpec] = []
    for local_box in local_boxes:
        local_origin_x, local_origin_y, local_origin_z = local_box.origin_xyz
        local_size_x, local_size_y, local_size_z = local_box.size_xyz
        scaled_local_boxes.append(
            BoxSpec(
                label=local_box.label,
                role=local_box.role,
                feature=local_box.feature,
                layer_index=local_box.layer_index,
                origin_xyz=(
                    local_min_xyz[0] + ((local_origin_x - local_min_xyz[0]) * fit_scale_x),
                    local_min_xyz[1] + ((local_origin_y - local_min_xyz[1]) * fit_scale_y),
                    local_origin_z,
                ),
                size_xyz=(
                    local_size_x * fit_scale_x,
                    local_size_y * fit_scale_y,
                    local_size_z,
                ),
            )
        )
    scaled_reference_boxes = tuple(
        box
        for box in scaled_local_boxes
        if box.role == "pcb" or (box.role == "copper" and box.feature == "planar_outline")
    )
    if len(scaled_reference_boxes) == 0:
        raise RuntimeError(
            "tx_rect_void_columns scaled single-layer geometry must expose at least one exported base box "
            f"(owner={owner_spec.object_id}, role={_TX_RECT_VOID_COLUMNS_PROFILE.role})"
        )
    scaled_min_xyz, _scaled_max_xyz, scaled_size_xyz = modeled_body_bounds_from_boxes(scaled_reference_boxes)
    scaled_size_x, scaled_size_y, scaled_size_z = scaled_size_xyz
    if scaled_size_x <= 0.0 or scaled_size_y <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns scaled local box specs must have positive XY size "
            f"(owner={owner_spec.object_id}, scaled_size_x={scaled_size_x}, scaled_size_y={scaled_size_y})"
        )
    if scaled_size_z <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns scaled local box specs must have positive Z size "
            f"(owner={owner_spec.object_id}, scaled_size_z={scaled_size_z})"
        )
    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    target_min_xyz = (
        owner_origin_x,
        owner_origin_y + ((owner_size_y - scaled_size_y) * 0.5),
        owner_origin_z + owner_size_z - scaled_size_z,
    )
    translation_xyz = (
        target_min_xyz[0] - scaled_min_xyz[0],
        target_min_xyz[1] - scaled_min_xyz[1],
        target_min_xyz[2] - scaled_min_xyz[2],
    )
    translated_local_boxes = tuple(
        _translated_box_spec(
            box_spec,
            translation_xyz=translation_xyz,
            label=box_spec.label,
        )
        for box_spec in scaled_local_boxes
    )
    base_pcb_label = f"{_TX_RECT_VOID_COLUMNS_PROFILE.pcb_body_prefix}_l0"
    base_copper_label = f"{_TX_RECT_VOID_COLUMNS_PROFILE.copper_body_prefix}_l0"
    base_stub_start_label = f"{_TX_RECT_VOID_COLUMNS_PROFILE.copper_body_prefix}_l0_stub_start"
    base_stub_end_label = f"{_TX_RECT_VOID_COLUMNS_PROFILE.copper_body_prefix}_l0_stub_end"
    translated_boxes_by_label = {box.label: box for box in translated_local_boxes}
    translated_outline_candidates = tuple(
        box
        for box in translated_local_boxes
        if box.role == "copper" and box.feature == "planar_outline" and box.layer_index == 0
    )
    if base_pcb_label not in translated_boxes_by_label or len(translated_outline_candidates) != 1:
        raise RuntimeError(
            "tx_rect_void_columns single-layer translated box specs must expose one PCB and one copper outline "
            f"(owner={owner_spec.object_id}, pcb_label={base_pcb_label}, "
            f"outline_count={len(translated_outline_candidates)}, labels={tuple(translated_boxes_by_label.keys())})"
        )
    for expected_label in (base_stub_start_label, base_stub_end_label):
        if expected_label not in tuple(box.label for box in translated_local_boxes if box.feature == "terminal_stub"):
            raise RuntimeError(
                f"tx_rect_void_columns single-layer base geometry must expose {expected_label} anchor metadata "
                f"(owner={owner_spec.object_id})"
            )
    translated_copper_outline_box = translated_outline_candidates[0]
    transformed_trace_face = _transformed_trace_face_from_centerline(
        centerline=local_centerline,
        trace_width_mm=realized.trace_width_mm,
        local_min_xy=(local_min_xyz[0], local_min_xyz[1]),
        fit_scale_x=fit_scale_x,
        fit_scale_y=fit_scale_y,
        translation_xy=(translation_xyz[0], translation_xyz[1]),
    )
    base_trace_copper_shape = _extrude_face_xy(
        face_xy=transformed_trace_face,
        origin_z=translated_copper_outline_box.origin_xyz[2],
        size_z=translated_copper_outline_box.size_xyz[2],
        label=f"{base_copper_label}_trace",
    )
    translated_anchor_boxes_by_label = {
        box.label: box
        for box in translated_local_boxes
        if box.feature == "terminal_stub"
    }
    base_stub_start_shape = _box_shape_from_spec(translated_anchor_boxes_by_label[base_stub_start_label])
    base_stub_end_shape = _box_shape_from_spec(translated_anchor_boxes_by_label[base_stub_end_label])
    copper_with_start_stub = cast(bd.Shape, base_trace_copper_shape.fuse(base_stub_start_shape))
    copper_with_all_stubs = cast(bd.Shape, copper_with_start_stub.fuse(base_stub_end_shape))
    base_copper_shape = _single_solid_shape(
        shape=copper_with_all_stubs,
        label=base_copper_label,
        context="copper_fuse",
    )
    uncut_pcb_shape = _box_shape_from_spec(translated_boxes_by_label[base_pcb_label])
    cut_pcb_shape = cast(bd.Shape, uncut_pcb_shape.cut(base_copper_shape))
    base_pcb_shape = _single_solid_shape(
        shape=cut_pcb_shape,
        label=base_pcb_label,
        context="pcb_cut",
    )
    base_shapes_by_label = {
        base_pcb_label: base_pcb_shape,
        base_copper_label: base_copper_shape,
    }
    layer_shapes: list[bd.Shape] = []
    layer_anchor_box_pairs: list[tuple[BoxSpec, BoxSpec]] = []
    for layer_index in range(resolved_ranges.layer_count):
        downward_layers = resolved_ranges.layer_count - 1 - layer_index
        shift_delta_z = -float(downward_layers) * layer_step_mm
        pcb_shape = base_shapes_by_label[base_pcb_label].moved(bd.Location((0.0, 0.0, shift_delta_z)))
        copper_shape = base_shapes_by_label[base_copper_label].moved(bd.Location((0.0, 0.0, shift_delta_z)))
        pcb_shape.label = f"{_TX_RECT_VOID_COLUMNS_PROFILE.pcb_body_prefix}_l{layer_index}"
        copper_shape.label = f"{_TX_RECT_VOID_COLUMNS_PROFILE.copper_body_prefix}_l{layer_index}"
        anchor_translation_xyz = (0.0, 0.0, shift_delta_z)
        stub_start_anchor = _translated_box_spec(
            translated_anchor_boxes_by_label[base_stub_start_label],
            translation_xyz=anchor_translation_xyz,
            label=f"{_TX_RECT_VOID_COLUMNS_PROFILE.copper_body_prefix}_l{layer_index}_stub_start",
        )
        stub_end_anchor = _translated_box_spec(
            translated_anchor_boxes_by_label[base_stub_end_label],
            translation_xyz=anchor_translation_xyz,
            label=f"{_TX_RECT_VOID_COLUMNS_PROFILE.copper_body_prefix}_l{layer_index}_stub_end",
        )
        layer_shapes.append(pcb_shape)
        layer_shapes.append(copper_shape)
        layer_anchor_box_pairs.append((stub_start_anchor, stub_end_anchor))
    return (tuple(layer_shapes), tuple(layer_anchor_box_pairs), resolved_ranges.layer_count)


def _validate_label_length(*, label: str) -> None:
    if len(label) > _MAX_BODY_LABEL_LENGTH:
        raise RuntimeError(
            "tx_rect_void_columns body name exceeds AEDT-friendly limit "
            f"(label={label}, length={len(label)}, max={_MAX_BODY_LABEL_LENGTH})"
        )


def _deterministic_stub_label(
    *,
    x_index: int,
    y_index: int,
    layer_index: int,
    terminal_hint: str,
) -> str:
    candidate = f"txrvc_x{x_index}_y{y_index}_stub_{terminal_hint}_l{layer_index}"
    if len(candidate) <= _MAX_BODY_LABEL_LENGTH:
        return candidate
    compact_digest = hashlib.blake2b(
        f"txrvc_x{x_index}_y{y_index}_stub_{terminal_hint}_l{layer_index}".encode("utf-8"),
        digest_size=6,
    ).hexdigest()
    terminal_token = terminal_hint[:1] if terminal_hint else "x"
    compact = f"txrvc_x{x_index}_y{y_index}_{terminal_token}_l{layer_index}_{compact_digest[:6]}"
    if len(compact) <= _MAX_BODY_LABEL_LENGTH:
        return compact
    compact_short = f"txrvc_{compact_digest[:12]}"
    if len(compact_short) > _MAX_BODY_LABEL_LENGTH:
        raise RuntimeError(
            "tx_rect_void_columns fallback body name exceeds AEDT-friendly limit "
            f"(label={compact_short}, length={len(compact_short)}, max={_MAX_BODY_LABEL_LENGTH})"
        )
    return compact_short


def _deterministic_terminal_body_label(
    *,
    x_index: int,
    y_index: int,
    terminal_hint: str,
) -> str:
    candidate = f"txrvc_x{x_index}_y{y_index}_stub_{terminal_hint}"
    if len(candidate) <= _MAX_BODY_LABEL_LENGTH:
        return candidate
    compact_digest = hashlib.blake2b(
        f"txrvc_x{x_index}_y{y_index}_stub_{terminal_hint}".encode("utf-8"),
        digest_size=6,
    ).hexdigest()
    compact = f"txrvc_{terminal_hint}_{compact_digest[:6]}"
    if len(compact) <= _MAX_BODY_LABEL_LENGTH:
        return compact
    compact_short = f"txrvc_{compact_digest[:12]}"
    if len(compact_short) > _MAX_BODY_LABEL_LENGTH:
        raise RuntimeError(
            "tx_rect_void_columns fallback body name exceeds AEDT-friendly limit "
            f"(label={compact_short}, length={len(compact_short)}, max={_MAX_BODY_LABEL_LENGTH})"
        )
    return compact_short


def build_tx_rect_void_columns_axis_aligned_tile_scenes(
    *,
    spec: ModeledTxRectVoidColumnsSpec,
    stack_space_specs: tuple[NonModelBoxSpec, ...],
    rx_center_xyz: Point3,
    seed: int,
) -> TxRectVoidColumnsBuildResult:
    if len(stack_space_specs) == 0:
        raise RuntimeError("tx_rect_void_columns requires at least one tx_region_actual_stack_space member")
    indexed_specs = tuple(
        (parsed[0], parsed[1], stack_space_spec)
        for stack_space_spec in stack_space_specs
        for parsed in (_parse_stack_space_tile_indices(object_id=stack_space_spec.object_id),)
    )
    sorted_indexed_specs = tuple(sorted(indexed_specs, key=lambda item: (item[0], item[1], item[2].object_id)))
    x_indices = tuple(sorted({item[0] for item in sorted_indexed_specs}))
    if len(x_indices) < 1 or len(x_indices) > 3:
        raise RuntimeError(
            "tx_rect_void_columns requires realized tx_region_actual x_division_count in [1, 3] "
            f"(actual={len(x_indices)}, x_indices={x_indices})"
        )
    if x_indices != tuple(range(len(x_indices))):
        raise RuntimeError(
            "tx_rect_void_columns stack-space x indices must be contiguous and zero-based "
            f"(actual={x_indices})"
        )
    owner_prefix = f"modeled_objects.{spec.object_id}"
    stack_space_height_mm = min(stack_space_spec.size_xyz[2] for _x_index, _y_index, stack_space_spec in sorted_indexed_specs)
    resolved_ranges = _resolved_single_coil_range_spec(
        spec=spec,
        stack_space_height_mm=stack_space_height_mm,
        seed=seed,
    )
    connection_mode = _selected_integer_candidate(
        range_spec=spec.connection_mode,
        owner_path=f"{owner_prefix}.connection_mode",
        seed=seed,
    )
    if connection_mode not in _TX_CONNECTION_MODES:
        raise RuntimeError(f"tx_rect_void_columns connection_mode must be 0 or 1 (actual={connection_mode})")
    if connection_mode == 0:
        relevant_turn_count = _selected_parallel_total_turn_count(
            spec=spec,
            owner_path=f"{owner_prefix}.parallel_total_turn_count",
            seed=seed,
        )
    else:
        relevant_turn_count = float(
            _selected_integer_candidate(
                range_spec=spec.series_total_turn_count,
                owner_path=f"{owner_prefix}.series_total_turn_count",
                seed=seed,
            )
        )
    turn_weight_a = _selected_float_candidate(
        range_spec=spec.turn_weight_a,
        owner_path=f"{owner_prefix}.turn_weight_a",
        seed=seed,
    )
    turn_weight_b = _selected_float_candidate(
        range_spec=spec.turn_weight_b,
        owner_path=f"{owner_prefix}.turn_weight_b",
        seed=seed,
    )
    turn_weight_c = _selected_float_candidate(
        range_spec=spec.turn_weight_c,
        owner_path=f"{owner_prefix}.turn_weight_c",
        seed=seed,
    )
    stack_space_centers = tuple(
        (
            stack_space_spec.origin_xyz[0] + (stack_space_spec.size_xyz[0] * 0.5),
            stack_space_spec.origin_xyz[1] + (stack_space_spec.size_xyz[1] * 0.5),
            stack_space_spec.origin_xyz[2] + (stack_space_spec.size_xyz[2] * 0.5),
        )
        for _x_index, _y_index, stack_space_spec in sorted_indexed_specs
    )
    resolved_turn_counts = resolve_tx_turns(
        stack_space_centers,
        rx_center_xyz=rx_center_xyz,
        connection_mode=connection_mode,
        relevant_turn_count=relevant_turn_count,
        turn_weight_a=turn_weight_a,
        turn_weight_b=turn_weight_b,
        turn_weight_c=turn_weight_c,
        max_turn_count=_TX_RECT_VOID_COLUMNS_PROFILE.max_turn_count,
    )
    if len(resolved_turn_counts) == 0:
        raise RuntimeError("tx_rect_void_columns turn allocator must produce at least one turn count")
    tile_scenes: list[TxRectVoidColumnsTileScene] = []
    tile_turn_counts: list[int] = []
    tile_terminal_anchors: list[TxRectVoidColumnsTileTerminalAnchors] = []
    expected_body_names: list[str] = []
    for (x_index, y_index, stack_space_spec), turn_count in zip(
        sorted_indexed_specs,
        resolved_turn_counts,
        strict=True,
    ):
        scene_children, terminal_anchor_box_pairs, layer_count = _realized_boxes_for_column(
            spec=spec,
            resolved_ranges=resolved_ranges,
            turn_count=turn_count,
            owner_spec=stack_space_spec,
            seed=seed,
        )
        if layer_count != resolved_ranges.layer_count:
            raise RuntimeError(
                "tx_rect_void_columns resolved layer_count drifted across realized tiles "
                f"(resolved={resolved_ranges.layer_count}, tile={stack_space_spec.object_id}, actual={layer_count})"
            )
        shapes_by_label = {shape.label: shape for shape in scene_children}
        if len(shapes_by_label) != len(scene_children):
            raise RuntimeError(
                "tx_rect_void_columns scene children must have unique labels before deterministic renaming "
                f"(tile={stack_space_spec.object_id})"
            )
        renamed_shapes: list[bd.Shape] = []
        terminal_anchor_box_specs: list[tuple[BoxSpec, BoxSpec]] = []
        for layer_index in range(layer_count):
            old_pcb_label = f"{_TX_RECT_VOID_COLUMNS_PROFILE.pcb_body_prefix}_l{layer_index}"
            old_copper_label = f"{_TX_RECT_VOID_COLUMNS_PROFILE.copper_body_prefix}_l{layer_index}"
            if old_pcb_label not in shapes_by_label or old_copper_label not in shapes_by_label:
                raise RuntimeError(
                    "tx_rect_void_columns tile scene must expose one PCB and one copper body per layer "
                    f"(tile={stack_space_spec.object_id}, layer_index={layer_index})"
                )
            if layer_index >= len(terminal_anchor_box_pairs):
                raise RuntimeError(
                    "tx_rect_void_columns tile scene must expose one start/end terminal anchor pair per layer "
                    f"(tile={stack_space_spec.object_id}, layer_index={layer_index})"
                )
            pcb_label = f"txrvc_x{x_index}_y{y_index}_pcb_l{layer_index}"
            copper_label = f"txrvc_x{x_index}_y{y_index}_cu_l{layer_index}"
            layer_stub_start_label = _deterministic_stub_label(
                x_index=x_index,
                y_index=y_index,
                layer_index=layer_index,
                terminal_hint="s",
            )
            layer_stub_end_label = _deterministic_stub_label(
                x_index=x_index,
                y_index=y_index,
                layer_index=layer_index,
                terminal_hint="e",
            )
            _validate_label_length(label=pcb_label)
            _validate_label_length(label=copper_label)
            _validate_label_length(label=layer_stub_start_label)
            _validate_label_length(label=layer_stub_end_label)
            pcb_shape = shapes_by_label[old_pcb_label]
            copper_shape = shapes_by_label[old_copper_label]
            old_stub_start_box, old_stub_end_box = terminal_anchor_box_pairs[layer_index]
            stub_start_box = _translated_box_spec(
                old_stub_start_box,
                translation_xyz=(0.0, 0.0, 0.0),
                label=layer_stub_start_label,
            )
            stub_end_box = _translated_box_spec(
                old_stub_end_box,
                translation_xyz=(0.0, 0.0, 0.0),
                label=layer_stub_end_label,
            )
            pcb_shape.label = pcb_label
            copper_shape.label = copper_label
            renamed_shapes.append(pcb_shape)
            renamed_shapes.append(copper_shape)
            terminal_anchor_box_specs.append((stub_start_box, stub_end_box))
            expected_body_names.append(pcb_label)
            expected_body_names.append(copper_label)

        generic_stub_start_label = _deterministic_terminal_body_label(
            x_index=x_index,
            y_index=y_index,
            terminal_hint="s",
        )
        generic_stub_end_label = _deterministic_terminal_body_label(
            x_index=x_index,
            y_index=y_index,
            terminal_hint="e",
        )
        _validate_label_length(label=generic_stub_start_label)
        _validate_label_length(label=generic_stub_end_label)
        terminal_stub_names = ((generic_stub_start_label, generic_stub_end_label),)
        expected_body_names.append(generic_stub_start_label)
        expected_body_names.append(generic_stub_end_label)
        tx_region_actual_object_id = _parent_tx_region_actual_object_id_for_stack_space(
            object_id=stack_space_spec.object_id
        )
        if turn_count < 1:
            raise RuntimeError(
                f"tx_rect_void_columns resolved per-tile turn count must be >= 1 (tile={stack_space_spec.object_id}, actual={turn_count})"
            )
        tile_turn_counts.append(turn_count)
        tile_terminal_names = terminal_stub_names
        tile_terminal_anchors.append(
            TxRectVoidColumnsTileTerminalAnchors(
                stack_space_object_id=stack_space_spec.object_id,
                x_index=x_index,
                y_index=y_index,
                terminal_stub_body_names=tile_terminal_names,
                terminal_anchor_box_specs=tuple(terminal_anchor_box_specs),
            )
        )
        stack_space_center_xyz = (
            stack_space_spec.origin_xyz[0] + (stack_space_spec.size_xyz[0] * 0.5),
            stack_space_spec.origin_xyz[1] + (stack_space_spec.size_xyz[1] * 0.5),
            stack_space_spec.origin_xyz[2] + (stack_space_spec.size_xyz[2] * 0.5),
        )
        tile_scenes.append(
            TxRectVoidColumnsTileScene(
                stack_space_object_id=stack_space_spec.object_id,
                tx_region_actual_object_id=tx_region_actual_object_id,
                x_index=x_index,
                y_index=y_index,
                stack_space_center_xyz=stack_space_center_xyz,
                resolved_turn_count=turn_count,
                terminal_stub_body_names=tile_terminal_names,
                scene_shapes=tuple(renamed_shapes),
            )
        )
    if len(expected_body_names) != len(set(expected_body_names)):
        raise RuntimeError(
            "tx_rect_void_columns deterministic body labels must be globally unique "
            f"(count={len(expected_body_names)})"
        )
    return TxRectVoidColumnsBuildResult(
        tile_scenes=tuple(tile_scenes),
        tile_terminal_anchors=tuple(tile_terminal_anchors),
        tile_resolved_turn_counts=tuple(tile_turn_counts),
        expected_exported_body_names=tuple(expected_body_names),
        terminal_stub_length_mm=resolved_ranges.terminal_stub_length_mm,
        layer_count=resolved_ranges.layer_count,
        connection_mode=cast(TxConnectionMode, connection_mode),
    )


__all__ = [
    "TxRectVoidColumnsBuildResult",
    "TxRectVoidColumnsTileScene",
    "TxRectVoidColumnsTileTerminalAnchors",
    "build_tx_rect_void_columns_axis_aligned_tile_scenes",
]

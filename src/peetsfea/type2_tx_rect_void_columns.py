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
from peetsfea.tx_rect_void import build_tx_rect_void_step_scene
from peetsfea.tx_rect_void import load_tx_rect_void_spec
from peetsfea.tx_rect_void import modeled_body_bounds_from_boxes
from peetsfea.tx_rect_void import realize_tx_rect_void_spec
from peetsfea.type2_step_spec import ModeledSingleCoilCommonSpec
from peetsfea.type2_step_spec import ModeledTxRectVoidColumnsSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import Point3
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import render_tx_rect_void_toml

_MAX_BODY_LABEL_LENGTH = 32
_TX_RECT_VOID_COLUMNS_PROFILE = SingleCoilProfile(
    role="rx_single_coil",
    object_id="tx_rect_void_columns",
    plane="XY",
    placement_owner_id="tx_region_actual_stack_space",
    pcb_body_prefix="txrvpcb",
    copper_body_prefix="txrvcu",
    compound_label="tx_rect_void_columns_member",
)


@dataclass(frozen=True)
class TxRectVoidColumnsTileScene:
    stack_space_object_id: str
    tx_region_actual_object_id: str
    x_index: int
    y_index: int
    stack_space_center_xyz: Point3
    scene_shapes: tuple[bd.Shape, ...]


@dataclass(frozen=True)
class TxRectVoidColumnsBuildResult:
    tile_scenes: tuple[TxRectVoidColumnsTileScene, ...]
    expected_exported_body_names: tuple[str, ...]
    layer_count: int


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
    turn_count: int


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
    x_index: int,
    seed: int,
) -> _ResolvedSingleCoilRangeSpec:
    owner_prefix = f"modeled_objects.{spec.object_id}"
    layer_count = _selected_integer_candidate(
        range_spec=spec.layer_count,
        owner_path=f"{owner_prefix}.layer_count",
        seed=seed,
    )
    if layer_count < 1 or layer_count > 3:
        raise RuntimeError(f"tx_rect_void_columns.layer_count must resolve to [1, 3] (actual={layer_count})")
    if x_index == 0:
        turn_count_spec = spec.turn_count_x0
    elif x_index == 1:
        turn_count_spec = spec.turn_count_x1
    elif x_index == 2:
        turn_count_spec = spec.turn_count_x2
    else:
        raise RuntimeError(f"tx_rect_void_columns x index must be in [0, 2] (actual={x_index})")
    turn_count = _selected_integer_candidate(
        range_spec=turn_count_spec,
        owner_path=f"{owner_prefix}.turn_count_x{x_index}",
        seed=seed,
    )
    if turn_count < 1:
        raise RuntimeError(f"tx_rect_void_columns turn_count_x{x_index} must resolve to >= 1 (actual={turn_count})")
    return _ResolvedSingleCoilRangeSpec(
        pcb_thickness_mm=spec.pcb_thickness_mm,
        copper_thickness_mm=spec.copper_thickness_mm,
        layer_count=layer_count,
        layer_gap_mm=_selected_float_candidate(
            range_spec=spec.layer_gap_mm,
            owner_path=f"{owner_prefix}.layer_gap_mm",
            seed=seed,
        ),
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
        turn_count=turn_count,
    )


def _realized_boxes_for_column(
    *,
    spec: ModeledTxRectVoidColumnsSpec,
    resolved_ranges: _ResolvedSingleCoilRangeSpec,
    owner_spec: NonModelBoxSpec,
    seed: int,
) -> tuple[tuple[bd.Shape, ...], int]:
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
        turn_count=resolved_ranges.turn_count,
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
    local_boxes = build_tx_rect_void_box_specs(realized, profile=_TX_RECT_VOID_COLUMNS_PROFILE)
    modeled_scene = build_tx_rect_void_step_scene(
        realized,
        local_boxes,
        profile=_TX_RECT_VOID_COLUMNS_PROFILE,
        frame_origin_xyz=(0.0, 0.0, 0.0),
    )
    base_children_raw = tuple(modeled_scene.children)
    if len(base_children_raw) == 0:
        raise RuntimeError("tx_rect_void_columns base single-layer scene must contain bodies")
    base_compound = bd.Compound(children=base_children_raw, label="tx_rect_void_columns_base")
    base_bbox = base_compound.bounding_box()
    base_min_xyz, _base_max_xyz, base_size_xyz = modeled_body_bounds_from_boxes(local_boxes)
    base_size_x, base_size_y, base_size_z = base_size_xyz
    if base_size_x <= 0.0 or base_size_y <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns base scene must have positive XY size "
            f"(owner={owner_spec.object_id}, base_size_x={base_size_x}, base_size_y={base_size_y})"
        )
    if not math.isclose(base_bbox.max.X - base_bbox.min.X, base_size_x, rel_tol=0.0, abs_tol=1e-9) or not math.isclose(
        base_bbox.max.Y - base_bbox.min.Y,
        base_size_y,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise RuntimeError(
            "tx_rect_void_columns derived box bounds and scene bounds must agree on X/Y "
            f"(owner={owner_spec.object_id}, box_sizes=({base_size_x}, {base_size_y}), "
            f"scene_sizes=({base_bbox.max.X - base_bbox.min.X}, {base_bbox.max.Y - base_bbox.min.Y}))"
        )
    if base_size_z <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns base scene must have positive Z size "
            f"(owner={owner_spec.object_id}, base_size_z={base_size_z})"
        )
    layer_step_mm = resolved_ranges.pcb_thickness_mm + resolved_ranges.layer_gap_mm
    full_stack_height_mm = base_size_z + (float(resolved_ranges.layer_count - 1) * layer_step_mm)
    if full_stack_height_mm > owner_size_z + 1e-9:
        raise RuntimeError(
            "tx_rect_void_columns resolved full stack height must fit stack-space owner height "
            f"(owner={owner_spec.object_id}, stack_height={full_stack_height_mm}, owner_height={owner_size_z})"
        )
    fit_scale_x = target_outer_x_mm / base_size_x
    fit_scale_y = target_outer_y_mm / base_size_y
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
                    base_min_xyz[0] + ((local_origin_x - base_min_xyz[0]) * fit_scale_x),
                    base_min_xyz[1] + ((local_origin_y - base_min_xyz[1]) * fit_scale_y),
                    local_origin_z,
                ),
                size_xyz=(
                    local_size_x * fit_scale_x,
                    local_size_y * fit_scale_y,
                    local_size_z,
                ),
            )
        )
    scaled_scene = build_tx_rect_void_step_scene(
        realized,
        tuple(scaled_local_boxes),
        profile=_TX_RECT_VOID_COLUMNS_PROFILE,
        frame_origin_xyz=(0.0, 0.0, 0.0),
    )
    scaled_children_raw = tuple(scaled_scene.children)
    scaled_compound = bd.Compound(children=scaled_children_raw, label="tx_rect_void_columns_scaled")
    scaled_bbox = scaled_compound.bounding_box()
    scaled_size_x = scaled_bbox.max.X - scaled_bbox.min.X
    scaled_size_y = scaled_bbox.max.Y - scaled_bbox.min.Y
    scaled_size_z = scaled_bbox.max.Z - scaled_bbox.min.Z
    owner_origin_x, owner_origin_y, owner_origin_z = owner_spec.origin_xyz
    target_min_xyz = (
        owner_origin_x,
        owner_origin_y + ((owner_size_y - scaled_size_y) * 0.5),
        owner_origin_z + owner_size_z - scaled_size_z,
    )
    translation_xyz = (
        target_min_xyz[0] - scaled_bbox.min.X,
        target_min_xyz[1] - scaled_bbox.min.Y,
        target_min_xyz[2] - scaled_bbox.min.Z,
    )
    translated_base_children = tuple(
        shape.moved(bd.Location(translation_xyz))
        for shape in scaled_children_raw
    )
    base_pcb_label = f"{_TX_RECT_VOID_COLUMNS_PROFILE.pcb_body_prefix}_l0"
    base_copper_label = f"{_TX_RECT_VOID_COLUMNS_PROFILE.copper_body_prefix}_l0"
    base_shapes_by_label = {shape.label: shape for shape in translated_base_children}
    if base_pcb_label not in base_shapes_by_label or base_copper_label not in base_shapes_by_label:
        raise RuntimeError(
            "tx_rect_void_columns single-layer base geometry must expose one PCB and one copper body "
            f"(owner={owner_spec.object_id}, labels={tuple(base_shapes_by_label.keys())})"
        )
    for expected_label in (base_pcb_label, base_copper_label):
        if expected_label not in base_shapes_by_label:
            raise RuntimeError(
                f"tx_rect_void_columns missing expected base label {expected_label} in base geometry"
            )
    layer_shapes: list[bd.Shape] = []
    for layer_index in range(resolved_ranges.layer_count):
        downward_layers = resolved_ranges.layer_count - 1 - layer_index
        shift_delta_z = -float(downward_layers) * layer_step_mm
        pcb_shape = base_shapes_by_label[base_pcb_label].moved(bd.Location((0.0, 0.0, shift_delta_z)))
        copper_shape = base_shapes_by_label[base_copper_label].moved(bd.Location((0.0, 0.0, shift_delta_z)))
        pcb_shape.label = f"{_TX_RECT_VOID_COLUMNS_PROFILE.pcb_body_prefix}_l{layer_index}"
        copper_shape.label = f"{_TX_RECT_VOID_COLUMNS_PROFILE.copper_body_prefix}_l{layer_index}"
        layer_shapes.append(pcb_shape)
        layer_shapes.append(copper_shape)
    return (tuple(layer_shapes), resolved_ranges.layer_count)


def _validate_label_length(*, label: str) -> None:
    if len(label) > _MAX_BODY_LABEL_LENGTH:
        raise RuntimeError(
            "tx_rect_void_columns body name exceeds AEDT-friendly limit "
            f"(label={label}, length={len(label)}, max={_MAX_BODY_LABEL_LENGTH})"
        )


def build_tx_rect_void_columns_axis_aligned_tile_scenes(
    *,
    spec: ModeledTxRectVoidColumnsSpec,
    stack_space_specs: tuple[NonModelBoxSpec, ...],
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
    resolved_ranges_by_x: dict[int, _ResolvedSingleCoilRangeSpec] = {}
    for x_index in x_indices:
        resolved_ranges_by_x[x_index] = _resolved_single_coil_range_spec(spec=spec, x_index=x_index, seed=seed)
    shared_layer_count = resolved_ranges_by_x[x_indices[0]].layer_count
    for x_index in x_indices[1:]:
        layer_count = resolved_ranges_by_x[x_index].layer_count
        if layer_count != shared_layer_count:
            raise RuntimeError(
                "tx_rect_void_columns layer_count must be shared across realized x columns "
                f"(x0={shared_layer_count}, x{x_index}={layer_count})"
            )
    tile_scenes: list[TxRectVoidColumnsTileScene] = []
    expected_body_names: list[str] = []
    for x_index, y_index, stack_space_spec in sorted_indexed_specs:
        scene_children, layer_count = _realized_boxes_for_column(
            spec=spec,
            resolved_ranges=resolved_ranges_by_x[x_index],
            owner_spec=stack_space_spec,
            seed=seed,
        )
        if layer_count != shared_layer_count:
            raise RuntimeError(
                "tx_rect_void_columns resolved layer_count drifted across realized tiles "
                f"(shared={shared_layer_count}, tile={stack_space_spec.object_id}, actual={layer_count})"
            )
        shapes_by_label = {shape.label: shape for shape in scene_children}
        if len(shapes_by_label) != len(scene_children):
            raise RuntimeError(
                "tx_rect_void_columns scene children must have unique labels before deterministic renaming "
                f"(tile={stack_space_spec.object_id})"
            )
        renamed_shapes: list[bd.Shape] = []
        for layer_index in range(layer_count):
            old_pcb_label = f"{_TX_RECT_VOID_COLUMNS_PROFILE.pcb_body_prefix}_l{layer_index}"
            old_copper_label = f"{_TX_RECT_VOID_COLUMNS_PROFILE.copper_body_prefix}_l{layer_index}"
            if old_pcb_label not in shapes_by_label or old_copper_label not in shapes_by_label:
                raise RuntimeError(
                    "tx_rect_void_columns tile scene must expose one PCB and one copper body per layer "
                    f"(tile={stack_space_spec.object_id}, layer_index={layer_index})"
                )
            pcb_label = f"txrvc_x{x_index}_y{y_index}_pcb_l{layer_index}"
            copper_label = f"txrvc_x{x_index}_y{y_index}_cu_l{layer_index}"
            _validate_label_length(label=pcb_label)
            _validate_label_length(label=copper_label)
            pcb_shape = shapes_by_label[old_pcb_label]
            copper_shape = shapes_by_label[old_copper_label]
            pcb_shape.label = pcb_label
            copper_shape.label = copper_label
            renamed_shapes.append(pcb_shape)
            renamed_shapes.append(copper_shape)
            expected_body_names.append(pcb_label)
            expected_body_names.append(copper_label)
        tx_region_actual_object_id = _parent_tx_region_actual_object_id_for_stack_space(
            object_id=stack_space_spec.object_id
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
        expected_exported_body_names=tuple(expected_body_names),
        layer_count=shared_layer_count,
    )


__all__ = [
    "TxRectVoidColumnsBuildResult",
    "TxRectVoidColumnsTileScene",
    "build_tx_rect_void_columns_axis_aligned_tile_scenes",
]

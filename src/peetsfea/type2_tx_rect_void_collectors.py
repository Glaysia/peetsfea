from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import build123d as bd

Point3 = tuple[float, float, float]

_COLLECTOR_CLEARANCE_MM = 0.5
_COLLECTOR_ROW_RAIL_WIDTH_MM = 0.75
_COLLECTOR_TAB_WIDTH_MM = 0.75
_BALANCE_TOLERANCE_MM = 1e-6
_BRANCH_SPREAD_LIMIT_MM = 5.0
_OVERLAP_TOLERANCE_MM3 = 1e-9
_CONTACT_OVERLAP_MM = 1e-4
_EXPECTED_EXPORT_BODY_NAME = "tx_rect_void_columns_copper"


@dataclass(frozen=True)
class TxRectVoidCollectorTileInput:
    x_index: int
    y_index: int
    tile_copper_shapes: tuple[bd.Shape, ...]
    start_terminal_stub_shape: bd.Shape
    end_terminal_stub_shape: bd.Shape
    start_pickup_vertices: tuple[Point3, ...]
    end_pickup_vertices: tuple[Point3, ...]
    copper_thickness_mm: float


@dataclass(frozen=True)
class TxRectVoidCollectorSourceLabelGroups:
    start_pours: tuple[str, ...]
    end_pours: tuple[str, ...]
    end_layer_drops: tuple[str, ...]
    start_external_tabs: tuple[str, ...]
    end_external_tabs: tuple[str, ...]


@dataclass(frozen=True)
class TxRectVoidCollectorBranchBalanceAudit:
    branch_count: int
    start_total_feed_length_mm: float
    end_total_feed_length_mm: float
    balance_delta_mm: float
    max_branch_total_delta_mm: float
    branch_spread_limit_mm: float
    tolerance_mm: float


@dataclass(frozen=True)
class TxRectVoidCollectorOverlapAudit:
    checked_pair_count: int
    positive_volume_pair_count: int
    max_intersection_volume_mm3: float
    tolerance_mm3: float


@dataclass(frozen=True)
class TxRectVoidCollectorExternalTabFaceVertices:
    start: tuple[Point3, ...]
    end: tuple[Point3, ...]


@dataclass(frozen=True)
class TxRectVoidColumnsCollectorBuildResult:
    fused_copper_shape: bd.Shape
    collector_source_shapes: tuple[bd.Shape, ...]
    expected_exported_body_name: str
    source_labels_grouped_by_role: TxRectVoidCollectorSourceLabelGroups
    external_tab_face_vertices: TxRectVoidCollectorExternalTabFaceVertices
    branch_balance_audit: TxRectVoidCollectorBranchBalanceAudit
    overlap_audit: TxRectVoidCollectorOverlapAudit


@dataclass(frozen=True)
class _PickupRect2D:
    center_x: float
    center_y: float
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float


def _require_single_solid_shape(*, shape: bd.Shape, context: str) -> bd.Shape:
    solids = tuple(shape.solids())
    if len(solids) != 1:
        raise RuntimeError(f"{context} must contain exactly one solid (actual={len(solids)})")
    solid = solids[0]
    assert isinstance(solid, bd.Shape)
    return solid


def _pickup_rect_from_vertices(*, vertices: tuple[Point3, ...], context: str) -> _PickupRect2D:
    if len(vertices) != 4:
        raise RuntimeError(f"{context} pickup rectangle must have exactly four vertices (actual={len(vertices)})")
    xs = tuple(vertex[0] for vertex in vertices)
    ys = tuple(vertex[1] for vertex in vertices)
    zs = tuple(vertex[2] for vertex in vertices)
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    min_z = min(zs)
    max_z = max(zs)
    if max_x <= min_x:
        raise RuntimeError(f"{context} pickup rectangle must have positive X span (min_x={min_x}, max_x={max_x})")
    if max_y <= min_y:
        raise RuntimeError(f"{context} pickup rectangle must have positive Y span (min_y={min_y}, max_y={max_y})")
    return _PickupRect2D(
        center_x=(min_x + max_x) / 2.0,
        center_y=(min_y + max_y) / 2.0,
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y,
        min_z=min_z,
        max_z=max_z,
    )


def _box_shape_from_bounds(
    *,
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float,
    min_z: float,
    max_z: float,
    label: str,
) -> bd.Shape:
    if max_x <= min_x:
        raise ValueError(f"{label} box requires positive X span (min_x={min_x}, max_x={max_x})")
    if max_y <= min_y:
        raise ValueError(f"{label} box requires positive Y span (min_y={min_y}, max_y={max_y})")
    if max_z <= min_z:
        raise ValueError(f"{label} box requires positive Z span (min_z={min_z}, max_z={max_z})")
    shape = bd.Box(
        max_x - min_x,
        max_y - min_y,
        max_z - min_z,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    ).moved(bd.Location((min_x, min_y, min_z)))
    solid = _require_single_solid_shape(shape=cast(bd.Shape, shape), context=label)
    solid.label = label
    return solid


def _box_top_face_vertices(*, min_x: float, max_x: float, min_y: float, max_y: float, max_z: float) -> tuple[Point3, ...]:
    return (
        (min_x, min_y, max_z),
        (max_x, min_y, max_z),
        (max_x, max_y, max_z),
        (min_x, max_y, max_z),
    )


def _shape_intersection_volume_mm3(*, first: bd.Shape, second: bd.Shape) -> float:
    first_box = first.bounding_box()
    second_box = second.bounding_box()
    overlap_x = min(first_box.max.X, second_box.max.X) - max(first_box.min.X, second_box.min.X)
    overlap_y = min(first_box.max.Y, second_box.max.Y) - max(first_box.min.Y, second_box.min.Y)
    overlap_z = min(first_box.max.Z, second_box.max.Z) - max(first_box.min.Z, second_box.min.Z)
    if overlap_x <= 0.0 or overlap_y <= 0.0 or overlap_z <= 0.0:
        return 0.0
    return overlap_x * overlap_y * overlap_z


def _x_interval_distance_to_value(
    *, value: float, min_x: float, max_x: float
) -> float:
    if value < min_x:
        return min_x - value
    if value > max_x:
        return value - max_x
    return 0.0


def _fuse_shapes(*, shapes: tuple[bd.Shape, ...], label: str) -> bd.Shape:
    if len(shapes) == 0:
        raise RuntimeError(f"{label} fuse requires at least one shape")
    fused: bd.Shape | bd.ShapeList[bd.Shape] = shapes[0]
    for shape in shapes[1:]:
        fuse_base = cast(bd.Shape, bd.Compound(children=tuple(fused))) if isinstance(fused, bd.ShapeList) else fused
        fused = fuse_base.fuse(shape)
    if isinstance(fused, bd.ShapeList):
        if len(fused) != 1:
            raise RuntimeError(f"{label} fuse must resolve to one connected shape (count={len(fused)})")
        fused_shape = cast(bd.Shape, fused[0])
    else:
        fused_shape = fused
    solid = _require_single_solid_shape(shape=fused_shape, context=label)
    solid.label = label
    return solid


def _unique_sorted_indices(*, tile_inputs: tuple[TxRectVoidCollectorTileInput, ...]) -> tuple[tuple[int, int], ...]:
    indices = tuple((tile_input.x_index, tile_input.y_index) for tile_input in tile_inputs)
    sorted_indices = tuple(sorted(indices))
    if len(sorted_indices) != len(set(sorted_indices)):
        raise RuntimeError(
            "tx_rect_void_columns collector inputs must have unique x_index/y_index pairs "
            f"(actual={sorted_indices})"
        )
    return sorted_indices


def _build_collector_boxes(
    *,
    tile_inputs: tuple[TxRectVoidCollectorTileInput, ...],
) -> tuple[
    tuple[bd.Shape, ...],
    TxRectVoidCollectorSourceLabelGroups,
    TxRectVoidCollectorExternalTabFaceVertices,
    TxRectVoidCollectorBranchBalanceAudit,
    TxRectVoidCollectorOverlapAudit,
]:
    if len(tile_inputs) == 0:
        raise RuntimeError("tx_rect_void_columns collector build requires at least one tile input")
    ordered_inputs = tuple(sorted(tile_inputs, key=lambda tile_input: (tile_input.y_index, tile_input.x_index)))
    _ = _unique_sorted_indices(tile_inputs=ordered_inputs)

    first_input = ordered_inputs[0]
    assert isinstance(first_input, TxRectVoidCollectorTileInput)
    copper_thickness_mm = first_input.copper_thickness_mm
    if copper_thickness_mm <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns collector build requires positive copper thickness "
            f"(actual={copper_thickness_mm})"
        )
    for tile_input in ordered_inputs[1:]:
        if tile_input.copper_thickness_mm != copper_thickness_mm:
            raise RuntimeError(
                "tx_rect_void_columns collector build requires a shared copper thickness across all tiles "
                f"(first={copper_thickness_mm}, tile={tile_input.x_index},{tile_input.y_index}, "
                f"actual={tile_input.copper_thickness_mm})"
            )

    pickup_contexts = tuple(
        (
            tile_input,
            _pickup_rect_from_vertices(
                vertices=tile_input.start_pickup_vertices,
                context=f"tile[{tile_input.x_index},{tile_input.y_index}].start",
            ),
            _pickup_rect_from_vertices(
                vertices=tile_input.end_pickup_vertices,
                context=f"tile[{tile_input.x_index},{tile_input.y_index}].end",
            ),
        )
        for tile_input in ordered_inputs
    )

    if any(tile_input.start_terminal_stub_shape is tile_input.end_terminal_stub_shape for tile_input in ordered_inputs):
        raise RuntimeError("start and end terminal stub shapes must be distinct per tile")

    validated_inputs: list[tuple[TxRectVoidCollectorTileInput, tuple[bd.Shape, ...], bd.Shape, bd.Shape, _PickupRect2D, _PickupRect2D]] = []
    for tile_input, start_pickup, end_pickup in pickup_contexts:
        assert isinstance(tile_input, TxRectVoidCollectorTileInput)
        if len(tile_input.tile_copper_shapes) == 0:
            raise RuntimeError(
                "tx_rect_void_columns collector tile input requires at least one copper shape "
                f"(tile={tile_input.x_index},{tile_input.y_index})"
            )
        tile_copper_shapes = tuple(
            _require_single_solid_shape(
                shape=tile_copper_shape,
                context=f"tile[{tile_input.x_index},{tile_input.y_index}].tile_copper_shapes[{shape_index}]",
            )
            for shape_index, tile_copper_shape in enumerate(tile_input.tile_copper_shapes)
        )
        start_terminal_stub_shape = _require_single_solid_shape(
            shape=tile_input.start_terminal_stub_shape,
            context=f"tile[{tile_input.x_index},{tile_input.y_index}].start_terminal_stub_shape",
        )
        end_terminal_stub_shape = _require_single_solid_shape(
            shape=tile_input.end_terminal_stub_shape,
            context=f"tile[{tile_input.x_index},{tile_input.y_index}].end_terminal_stub_shape",
        )
        validated_inputs.append(
            (
                tile_input,
                tile_copper_shapes,
                start_terminal_stub_shape,
                end_terminal_stub_shape,
                start_pickup,
                end_pickup,
            )
        )

    all_pickups = tuple(pickup for _tile_input, _tile_shape, _start_shape, _end_shape, start_pickup, end_pickup in validated_inputs for pickup in (start_pickup, end_pickup))
    min_pickup_z = min(pickup.min_z for pickup in all_pickups)
    upper_top_z = min_pickup_z + _CONTACT_OVERLAP_MM
    lower_top_z = upper_top_z - copper_thickness_mm - _COLLECTOR_CLEARANCE_MM
    upper_bottom_z = upper_top_z - copper_thickness_mm
    lower_bottom_z = lower_top_z - copper_thickness_mm

    start_pickups = tuple(
        start_pickup for _tile_input, _tile_shape, _start_shape, _end_shape, start_pickup, _end_pickup in validated_inputs
    )
    end_pickups = tuple(
        end_pickup for _tile_input, _tile_shape, _start_shape, _end_shape, _start_pickup, end_pickup in validated_inputs
    )
    if len(start_pickups) == 0:
        raise RuntimeError("tx_rect_void_columns collector build requires at least one start pickup")
    if len(end_pickups) == 0:
        raise RuntimeError("tx_rect_void_columns collector build requires at least one end pickup")

    pour_y_margin = _COLLECTOR_ROW_RAIL_WIDTH_MM / 2.0
    all_pickup_min_y = min(pickup.min_y for pickup in all_pickups)
    all_pickup_max_y = max(pickup.max_y for pickup in all_pickups)
    start_bus_min_x = min(pickup.min_x for pickup in start_pickups) - _COLLECTOR_CLEARANCE_MM - _COLLECTOR_TAB_WIDTH_MM
    start_bus_max_x = start_bus_min_x + _COLLECTOR_TAB_WIDTH_MM
    start_patch_max_x = max(pickup.max_x for pickup in start_pickups) + _COLLECTOR_CLEARANCE_MM
    end_bus_max_x = max(
        max(pickup.max_x for pickup in end_pickups) + _COLLECTOR_CLEARANCE_MM + _COLLECTOR_TAB_WIDTH_MM,
        start_patch_max_x + _COLLECTOR_CLEARANCE_MM + _COLLECTOR_TAB_WIDTH_MM,
    )
    end_bus_min_x = end_bus_max_x - _COLLECTOR_TAB_WIDTH_MM
    bus_min_y = all_pickup_min_y - pour_y_margin
    bus_max_y = all_pickup_max_y + pour_y_margin
    collector_shapes: list[bd.Shape] = []
    start_pour_labels: list[str] = []
    end_pour_labels: list[str] = []
    end_layer_drop_labels: list[str] = []

    start_bus_label = "txrvc_pour_s_bus"
    end_bus_label = "txrvc_pour_e_bus"
    start_bus = _box_shape_from_bounds(
        min_x=start_bus_min_x,
        max_x=start_bus_max_x,
        min_y=bus_min_y,
        max_y=bus_max_y,
        min_z=upper_bottom_z,
        max_z=upper_top_z,
        label=start_bus_label,
    )
    end_bus = _box_shape_from_bounds(
        min_x=end_bus_min_x,
        max_x=end_bus_max_x,
        min_y=bus_min_y,
        max_y=bus_max_y,
        min_z=lower_bottom_z,
        max_z=lower_top_z,
        label=end_bus_label,
    )
    collector_shapes.append(start_bus)
    collector_shapes.append(end_bus)
    start_pour_labels.append(start_bus_label)
    end_pour_labels.append(end_bus_label)

    for tile_input, _tile_shapes, _start_stub_shape, _end_stub_shape, start_pickup, end_pickup in validated_inputs:
        start_patch_label = f"txrvc_pour_s_x{tile_input.x_index}_y{tile_input.y_index}"
        end_patch_label = f"txrvc_pour_e_x{tile_input.x_index}_y{tile_input.y_index}"
        start_patch = _box_shape_from_bounds(
            min_x=start_bus_max_x,
            max_x=start_pickup.max_x + _COLLECTOR_CLEARANCE_MM,
            min_y=start_pickup.min_y - pour_y_margin,
            max_y=start_pickup.max_y + pour_y_margin,
            min_z=upper_bottom_z,
            max_z=upper_top_z,
            label=start_patch_label,
        )
        end_patch = _box_shape_from_bounds(
            min_x=end_pickup.min_x - _COLLECTOR_CLEARANCE_MM,
            max_x=end_bus_min_x,
            min_y=end_pickup.min_y - pour_y_margin,
            max_y=end_pickup.max_y + pour_y_margin,
            min_z=lower_bottom_z,
            max_z=lower_top_z,
            label=end_patch_label,
        )
        collector_shapes.append(start_patch)
        collector_shapes.append(end_patch)
        start_pour_labels.append(start_patch_label)
        end_pour_labels.append(end_patch_label)

    tab_start_min_x = start_bus_min_x
    tab_start_max_x = start_bus_max_x
    tab_end_min_x = end_bus_min_x
    tab_end_max_x = end_bus_max_x
    start_tab_min_y = bus_max_y - _COLLECTOR_TAB_WIDTH_MM
    start_tab_max_y = bus_max_y
    end_tab_min_y = bus_max_y - _COLLECTOR_TAB_WIDTH_MM
    end_tab_max_y = bus_max_y

    start_tab = _box_shape_from_bounds(
        min_x=tab_start_min_x,
        max_x=tab_start_max_x,
        min_y=start_tab_min_y,
        max_y=start_tab_max_y,
        min_z=upper_bottom_z,
        max_z=upper_top_z,
        label="txrvc_tab_start",
    )
    end_tab = _box_shape_from_bounds(
        min_x=tab_end_min_x,
        max_x=tab_end_max_x,
        min_y=end_tab_min_y,
        max_y=end_tab_max_y,
        min_z=lower_bottom_z,
        max_z=upper_top_z,
        label="txrvc_tab_end",
    )
    collector_shapes.append(start_tab)
    collector_shapes.append(end_tab)

    for tile_input, _tile_shapes, _start_stub_shape, _end_stub_shape, start_pickup, end_pickup in validated_inputs:
        end_drop_label = f"txrvc_drop_e_x{tile_input.x_index}_y{tile_input.y_index}"
        end_layer_drop_labels.append(end_drop_label)
        end_drop = _box_shape_from_bounds(
            min_x=end_pickup.min_x,
            max_x=end_pickup.max_x,
            min_y=end_pickup.min_y,
            max_y=end_pickup.max_y,
            min_z=lower_top_z,
            max_z=end_pickup.min_z + _CONTACT_OVERLAP_MM,
            label=end_drop_label,
        )
        collector_shapes.append(end_drop)

    start_tab_vertices = _box_top_face_vertices(
        min_x=tab_start_min_x,
        max_x=tab_start_max_x,
        min_y=start_tab_min_y,
        max_y=start_tab_max_y,
        max_z=upper_top_z,
    )
    end_tab_vertices = _box_top_face_vertices(
        min_x=tab_end_min_x,
        max_x=tab_end_max_x,
        min_y=end_tab_min_y,
        max_y=end_tab_max_y,
        max_z=upper_top_z,
    )

    start_total_feed_length_mm = 0.0
    end_total_feed_length_mm = 0.0
    branch_total_feed_lengths_mm: list[float] = []
    for tile_input, _tile_shapes, _start_stub_shape, _end_stub_shape, start_pickup, end_pickup in validated_inputs:
        start_reach_mm = _x_interval_distance_to_value(
            value=start_pickup.center_x,
            min_x=start_bus_min_x,
            max_x=start_pickup.max_x + _COLLECTOR_CLEARANCE_MM,
        )
        end_reach_mm = _x_interval_distance_to_value(
            value=end_pickup.center_x,
            min_x=end_pickup.min_x - _COLLECTOR_CLEARANCE_MM,
            max_x=end_bus_max_x,
        )
        start_total_feed_length_mm += start_reach_mm
        end_total_feed_length_mm += end_reach_mm
        branch_total_feed_lengths_mm.append(
            start_reach_mm + end_reach_mm
        )

    balance_delta_mm = abs(start_total_feed_length_mm - end_total_feed_length_mm)
    max_branch_total_delta_mm = max(branch_total_feed_lengths_mm) - min(branch_total_feed_lengths_mm)
    if balance_delta_mm > _BALANCE_TOLERANCE_MM:
        raise RuntimeError(
            "tx_rect_void_columns collector branch pour reach balance drift exceeds tolerance "
            f"(start_total={start_total_feed_length_mm}, end_total={end_total_feed_length_mm}, "
            f"delta={balance_delta_mm}, tolerance={_BALANCE_TOLERANCE_MM})"
        )
    if max_branch_total_delta_mm > _BRANCH_SPREAD_LIMIT_MM:
        raise RuntimeError(
            "tx_rect_void_columns collector mirrored branch pour reach spread exceeds tolerance "
            f"(max_branch_total_delta={max_branch_total_delta_mm}, limit={_BRANCH_SPREAD_LIMIT_MM})"
        )

    positive_volume_pair_count = 0
    max_intersection_volume_mm3 = 0.0
    checked_pair_count = 0
    for start_shape in tuple(
            shape
            for shape in collector_shapes
            if shape.label.startswith("txrvc_pour_s")
            or shape.label == "txrvc_tab_start"
        ):
        for end_shape in tuple(
            shape
            for shape in collector_shapes
            if shape.label.startswith("txrvc_pour_e")
            or shape.label.startswith("txrvc_drop_e_")
            or shape.label == "txrvc_tab_end"
        ):
            checked_pair_count += 1
            intersection_volume_mm3 = _shape_intersection_volume_mm3(first=start_shape, second=end_shape)
            if intersection_volume_mm3 > max_intersection_volume_mm3:
                max_intersection_volume_mm3 = intersection_volume_mm3
            if intersection_volume_mm3 > _OVERLAP_TOLERANCE_MM3:
                positive_volume_pair_count += 1
                raise RuntimeError(
                    "tx_rect_void_columns collector source shapes must not have positive-volume intersection "
                    f"(start_label={start_shape.label}, end_label={end_shape.label}, "
                    f"intersection_volume_mm3={intersection_volume_mm3}, tolerance={_OVERLAP_TOLERANCE_MM3})"
                )

    source_labels_grouped_by_role = TxRectVoidCollectorSourceLabelGroups(
        start_pours=tuple(start_pour_labels),
        end_pours=tuple(end_pour_labels),
        end_layer_drops=tuple(end_layer_drop_labels),
        start_external_tabs=("txrvc_tab_start",),
        end_external_tabs=("txrvc_tab_end",),
    )
    external_tab_face_vertices = TxRectVoidCollectorExternalTabFaceVertices(
        start=start_tab_vertices,
        end=end_tab_vertices,
    )
    branch_balance_audit = TxRectVoidCollectorBranchBalanceAudit(
        branch_count=len(validated_inputs),
        start_total_feed_length_mm=start_total_feed_length_mm,
        end_total_feed_length_mm=end_total_feed_length_mm,
        balance_delta_mm=balance_delta_mm,
        max_branch_total_delta_mm=max_branch_total_delta_mm,
        branch_spread_limit_mm=_BRANCH_SPREAD_LIMIT_MM,
        tolerance_mm=_BALANCE_TOLERANCE_MM,
    )
    overlap_audit = TxRectVoidCollectorOverlapAudit(
        checked_pair_count=checked_pair_count,
        positive_volume_pair_count=positive_volume_pair_count,
        max_intersection_volume_mm3=max_intersection_volume_mm3,
        tolerance_mm3=_OVERLAP_TOLERANCE_MM3,
    )
    return (
        tuple(collector_shapes),
        source_labels_grouped_by_role,
        external_tab_face_vertices,
        branch_balance_audit,
        overlap_audit,
    )


def build_tx_rect_void_columns_parallel_collectors(
    *,
    tile_inputs: tuple[TxRectVoidCollectorTileInput, ...],
) -> TxRectVoidColumnsCollectorBuildResult:
    if len(tile_inputs) == 0:
        raise RuntimeError("tx_rect_void_columns parallel collector build requires at least one tile input")
    collector_source_shapes, source_labels_grouped_by_role, external_tab_face_vertices, branch_balance_audit, overlap_audit = _build_collector_boxes(
        tile_inputs=tile_inputs,
    )
    return TxRectVoidColumnsCollectorBuildResult(
        fused_copper_shape=_fuse_shapes(
            shapes=tuple(
                tile_copper_shape
                for tile_input in tile_inputs
                for tile_copper_shape in tile_input.tile_copper_shapes
            )
            + tuple(
                _require_single_solid_shape(
                    shape=tile_input.start_terminal_stub_shape,
                    context=f"tile[{tile_input.x_index},{tile_input.y_index}].start_terminal_stub_shape",
                )
                for tile_input in tile_inputs
            )
            + tuple(
                _require_single_solid_shape(
                    shape=tile_input.end_terminal_stub_shape,
                    context=f"tile[{tile_input.x_index},{tile_input.y_index}].end_terminal_stub_shape",
                )
                for tile_input in tile_inputs
            )
            + collector_source_shapes,
            label=_EXPECTED_EXPORT_BODY_NAME,
        ),
        collector_source_shapes=collector_source_shapes,
        expected_exported_body_name=_EXPECTED_EXPORT_BODY_NAME,
        source_labels_grouped_by_role=source_labels_grouped_by_role,
        external_tab_face_vertices=external_tab_face_vertices,
        branch_balance_audit=branch_balance_audit,
        overlap_audit=overlap_audit,
    )


def build_tx_rect_void_columns_collectors(
    *,
    connection_mode: int,
    tile_inputs: tuple[TxRectVoidCollectorTileInput, ...],
) -> TxRectVoidColumnsCollectorBuildResult:
    if connection_mode != 0:
        raise RuntimeError(
            "tx_rect_void_columns collectors only support connection_mode=0 "
            f"(actual={connection_mode})"
        )
    return build_tx_rect_void_columns_parallel_collectors(tile_inputs=tile_inputs)


__all__ = [
    "Point3",
    "TxRectVoidCollectorBranchBalanceAudit",
    "TxRectVoidCollectorExternalTabFaceVertices",
    "TxRectVoidCollectorOverlapAudit",
    "TxRectVoidCollectorSourceLabelGroups",
    "TxRectVoidCollectorTileInput",
    "TxRectVoidColumnsCollectorBuildResult",
    "build_tx_rect_void_columns_collectors",
    "build_tx_rect_void_columns_parallel_collectors",
]

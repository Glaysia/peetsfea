from __future__ import annotations

from typing import cast

from peetsfea.topology.tx_dd import (
    build_txdd_right_points as _build_txdd_right_points_shared,
    extend_endpoints as _extend_endpoints_shared,
)

from .placement_geometry import (
    _build_txdd_right_points_a_to_d,
    _build_txdd_right_points_c_to_a,
    _current_direction_from_xy_points,
    _edge_points_at_xy_terminal,
    _max_feasible_turns,
    _validate_txdd_right_points,
)
from .placement_shared import _UNSET, _normalize_layer_index_for_shared, _resolve_txdd_counts
from .placement_types import _Point3, _TxDdRightLocalTopology
from .spiral_points import _apply_corner_mode_to_polyline_lists


def _extend_endpoints(points: list[list[float]], *, extension: float) -> list[list[float]]:
    return [
        [point[0], point[1], point[2]]
        for point in _extend_endpoints_shared(
            [(float(point[0]), float(point[1]), float(point[2])) for point in points],
            extension=extension,
        )
    ]


def _realized_txdd_geometry(
    *,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
    layer_count: object = _UNSET,
    instance_count: object = _UNSET,
    layer_index: object = _UNSET,
) -> tuple[int, float, float]:
    resolved_layer_count, resolved_instance_count = _resolve_txdd_counts(
        layer_count=layer_count,
        instance_count=instance_count,
    )
    if turns < 1:
        raise ValueError(f"tx_dd turn_count must be >= 1 (actual={turns})")
    if resolved_layer_count == 1:
        return turns, outer_x, outer_y
    if layer_index not in (0, 1):
        raise ValueError(f"tx_dd layer index must be 0 or 1 for layer_count=2 (actual={layer_index})")
    if layer_index == 1:
        return turns, outer_x, outer_y
    pitch = trace + gap
    if pitch <= 0.0:
        raise ValueError(f"tx_dd pitch must be > 0 (trace={trace}, gap={gap})")
    lower_outer_x = outer_x - pitch
    lower_outer_y = outer_y - pitch
    if lower_outer_x <= trace or lower_outer_y <= trace:
        raise ValueError(
            "tx_dd lower-layer interleave contract violation: one-pitch inset leaves no valid lower-layer width "
            f"(outer_x={outer_x}, outer_y={outer_y}, trace={trace}, gap={gap}, "
            f"lower_outer_x={lower_outer_x}, lower_outer_y={lower_outer_y})"
        )
    feasible_lower_turns = min(
        _max_feasible_turns(lower_outer_x, trace, gap),
        _max_feasible_turns(lower_outer_y, trace, gap),
    )
    if turns > feasible_lower_turns:
        raise ValueError(
            "tx_dd lower-layer interleave contract violation: requested turns do not fit after one-pitch inset "
            f"(turns={turns}, feasible_lower_turns={feasible_lower_turns}, "
            f"lower_outer_x={lower_outer_x}, lower_outer_y={lower_outer_y}, trace={trace}, gap={gap})"
        )
    _ = resolved_instance_count
    return turns, lower_outer_x, lower_outer_y


def _txdd_right_points(
    *,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
    layer_count: object = _UNSET,
    instance_count: object = _UNSET,
    layer_index: object = _UNSET,
    corner_mode: int = 0,
) -> list[list[float]]:
    resolved_layer_count, resolved_instance_count = _resolve_txdd_counts(
        layer_count=layer_count,
        instance_count=instance_count,
    )
    shared_layer_index = _normalize_layer_index_for_shared(resolved_layer_count, layer_index)
    points = [
        [point[0], point[1], point[2]]
        for point in _build_txdd_right_points_shared(
            turns=turns,
            outer_x=outer_x,
            outer_y=outer_y,
            trace=trace,
            gap=gap,
            layer_count=resolved_layer_count,
            instance_count=resolved_instance_count,
            layer_index=shared_layer_index,
        )
    ]
    if corner_mode != 0:
        points = _apply_corner_mode_to_polyline_lists(points, corner_mode=corner_mode, trace=trace, gap=gap)
    _validate_txdd_right_points(points, trace=trace, gap=gap, corner_mode=corner_mode)
    return points


def _tx_dd_center_y_and_layer(
    *,
    layer_count: object = _UNSET,
    instance_count: object = _UNSET,
    instance_index: int,
    pair_clearance_mm: float,
    outer_y: float,
    region_center_y: float,
    region_min_y: float,
    region_max_y: float,
) -> tuple[float, int]:
    resolved_layer_count, resolved_instance_count = _resolve_txdd_counts(
        layer_count=layer_count,
        instance_count=instance_count,
    )
    if instance_index < 0 or instance_index >= resolved_instance_count:
        raise ValueError(f"tx_dd instance index out of range: {instance_index}")
    half_outer_y = outer_y / 2.0
    pair_center_distance = outer_y + pair_clearance_mm
    half_center_distance = pair_center_distance / 2.0
    local_slot = instance_index % 2
    layer_index = 0 if resolved_layer_count == 1 else (instance_index // 2)
    sign = -1.0 if local_slot == 0 else 1.0
    center_y = region_center_y + (sign * half_center_distance)
    if (center_y - half_outer_y) < region_min_y or (center_y + half_outer_y) > region_max_y:
        raise ValueError(
            "tx_dd symmetric placement out of region "
            f"(pair_clearance_mm={pair_clearance_mm}, outer_y={outer_y}, "
            f"instance_index={instance_index}, region_min_y={region_min_y}, region_max_y={region_max_y})"
        )
    return center_y, layer_index


def _txdd_half_topology(
    *,
    half_side: str,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
    layer_count: object = _UNSET,
    instance_count: object = _UNSET,
    layer_index: object = _UNSET,
    corner_mode: int = 0,
) -> _TxDdRightLocalTopology:
    if half_side == "right":
        return _txdd_right_topology(
            turns=turns,
            outer_x=outer_x,
            outer_y=outer_y,
            trace=trace,
            gap=gap,
            layer_count=layer_count,
            instance_count=instance_count,
            layer_index=layer_index,
            corner_mode=corner_mode,
        )
    raise ValueError(f"_txdd_half_topology only supports right-only tx_dd runtime (actual={half_side})")


def _txdd_right_topology(
    *,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
    layer_count: object = _UNSET,
    instance_count: object = _UNSET,
    layer_index: object = _UNSET,
    corner_mode: int = 0,
) -> _TxDdRightLocalTopology:
    resolved_layer_count, resolved_instance_count = _resolve_txdd_counts(
        layer_count=layer_count,
        instance_count=instance_count,
    )
    points = _txdd_right_points(
        turns=turns,
        outer_x=outer_x,
        outer_y=outer_y,
        trace=trace,
        gap=gap,
        layer_count=resolved_layer_count,
        instance_count=resolved_instance_count,
        layer_index=layer_index,
        corner_mode=corner_mode,
    )
    if turns != 1:
        raise ValueError("_txdd_right_topology is only supported for one-turn tx_dd")
    if resolved_layer_count == 1:
        return _TxDdRightLocalTopology(
            points=points,
            bridge_edge_local=_edge_points_at_xy_terminal(points=points, trace=trace, terminal="end"),
            free_terminal_anchor_local=cast(_Point3, tuple(float(v) for v in points[0])),
            a_anchor_local=None,
            terminal_role="single_right",
        )
    if resolved_layer_count != 2 or layer_index not in (0, 1):
        raise ValueError(
            "tx_dd one-turn topology contract violation: expected layer_count=1 or 2 with layer index 0/1"
        )
    if layer_index == 0:
        return _TxDdRightLocalTopology(
            points=points,
            bridge_edge_local=None,
            free_terminal_anchor_local=cast(_Point3, tuple(float(v) for v in points[0])),
            a_anchor_local=cast(_Point3, tuple(float(v) for v in points[-1])),
            terminal_role="lower_right",
        )
    return _TxDdRightLocalTopology(
        points=points,
        bridge_edge_local=_edge_points_at_xy_terminal(points=points, trace=trace, terminal="end"),
        free_terminal_anchor_local=None,
        a_anchor_local=cast(_Point3, tuple(float(v) for v in points[0])),
        terminal_role="upper_right",
    )

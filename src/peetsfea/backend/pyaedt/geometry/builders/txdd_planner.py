from __future__ import annotations

from typing import Literal, cast

from peetsfea.topology.tx_dd import txdd_right_terminal_labels
from ..build_state import Edge2P, Point3, require_tx_dd_scene
from ..rules.placement_rules import (
    _current_direction_from_xy_points,
    _edge_points_at_xy_terminal,
    _extend_endpoints,
    _instance_side,
    _max_feasible_turns,
    _realized_txdd_geometry,
    _tx_dd_center_y_and_layer,
    _txdd_right_points,
)
from ..rules.spiral_points import _translate_points
from peetsfea.types.manifest import ResolvedPcbMount
from .group_builder_tx_dd_geometry import (
    _iter_tx_dd_slots,
    _translate_edge2p_local,
    _txdd_slot_is_mounted,
)
from .txdd_types import TxDdBuildRequest, TxDdHalfRealization, TxDdRealization, TxDdSlot


def plan_txdd_slots(*, layer_count: int, mounts: list[ResolvedPcbMount]) -> tuple[TxDdSlot, ...]:
    slots: list[TxDdSlot] = []
    for layer_index, right_index in _iter_tx_dd_slots(layer_count):
        if not _txdd_slot_is_mounted(mounts, layer_index=layer_index, layer_count=layer_count):
            continue
        slots.append(
            TxDdSlot(
                layer_index=layer_index,
                right_index=right_index,
            )
        )
    return tuple(slots)


def _validate_request(request: TxDdBuildRequest) -> tuple[int, float, float, int, float, dict[str, float]]:
    if request.group["kind"] != "tx_dd":
        raise ValueError(f"tx_dd builder contract violation: unsupported group kind {request.group['kind']}")
    turns = request.geometry["turn_count"]
    trace = request.geometry["trace"]
    gap = request.geometry["gap"]
    if turns < 1:
        raise ValueError("selected_group_geometry.tx_dd.turn_count must be >= 1")
    if turns > 9:
        raise ValueError("selected_group_geometry.tx_dd.turn_count must be <= 9")
    if trace <= 0:
        raise ValueError("selected_group_geometry.tx_dd.trace must be > 0")
    if gap < 0:
        raise ValueError("selected_group_geometry.tx_dd.gap must be >= 0")
    max_turns = min(
        _max_feasible_turns(request.ctx.tx_dd_outer_x, trace, gap),
        _max_feasible_turns(request.ctx.tx_dd_outer_y, trace, gap),
    )
    if max_turns < 1:
        raise ValueError(
            "Invalid geometry for tx_dd: cannot fit at least one turn on both X/Y axes "
            f"(turns={turns}, trace={trace}, gap={gap})"
        )
    if turns > max_turns:
        raise ValueError(
            f"Infeasible turn_count for tx_dd: requested={turns}, feasible_max={max_turns} "
            f"(outer_x={request.ctx.tx_dd_outer_x}, outer_y={request.ctx.tx_dd_outer_y}, trace={trace}, gap={gap})"
        )
    layer_count = int(request.group["layer_count"])
    instance_count = 2 if layer_count == 1 else 4
    for layer_index in ((0, 1) if instance_count == 4 else (0,)):
        _realized_txdd_geometry(
            turns=turns,
            outer_x=request.ctx.tx_dd_outer_x,
            outer_y=request.ctx.tx_dd_outer_y,
            trace=trace,
            gap=gap,
            instance_count=instance_count,
            layer_index=layer_index,
        )
    transforms = request.group["instance_transforms"]
    transform = transforms[0] if transforms else {"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0}
    return turns, trace, gap, instance_count, request.group["spacing_mm"], transform


def _realize_half(
    *,
    request: TxDdBuildRequest,
    side: Literal["right"],
    layer_index: int,
    instance_index: int,
    turns: int,
    trace: float,
    gap: float,
    instance_count: int,
    center_y: float,
    transform: dict[str, float],
    tx_dd_center_x: float,
    tx_dd_center_y: float,
    tx_dd_anchor_z: float,
    board_z: float,
) -> TxDdHalfRealization:
    if turns == 1:
        local_topology = request.half_topology(
            half_side=side,
            turns=turns,
            outer_x=request.ctx.tx_dd_outer_x,
            outer_y=request.ctx.tx_dd_outer_y,
            trace=trace,
            gap=gap,
            instance_count=instance_count,
            layer_index=layer_index,
            corner_mode=request.ctx.corner_mode,
        )
        local_points = [point[:] for point in local_topology.points]
        if isinstance(local_topology.a_anchor_local, tuple):
            raw_a_local = cast(Point3, local_topology.a_anchor_local)
        else:
            raw_a_source = local_points[-1] if layer_index == 0 else local_points[0]
            raw_a_local = cast(Point3, tuple(float(v) for v in raw_a_source))
        if isinstance(local_topology.bridge_edge_local, tuple):
            raw_bridge_edge = cast(Edge2P, local_topology.bridge_edge_local)
        else:
            raw_bridge_edge = request.edge_points_at_path_end(points=local_points, trace=trace)
    else:
        local_points = _txdd_right_points(
            turns=turns,
            outer_x=request.ctx.tx_dd_outer_x,
            outer_y=request.ctx.tx_dd_outer_y,
            trace=trace,
            gap=gap,
            instance_count=instance_count,
            layer_index=layer_index,
            corner_mode=request.ctx.corner_mode,
        )
        raw_a_source = local_points[-1] if layer_index == 0 else local_points[0]
        raw_a_local = cast(Point3, tuple(float(v) for v in raw_a_source))
        raw_bridge_edge = request.edge_points_at_path_end(points=local_points, trace=trace)
    local_points = _extend_endpoints(local_points, extension=(trace / 2.0))
    dx = tx_dd_center_x + transform["dx"]
    dy = center_y + transform["dy"]
    dz = tx_dd_anchor_z - board_z + transform["dz"]
    world_bridge_edge = _translate_edge2p_local(raw_bridge_edge, dx=dx, dy=dy, dz=dz)
    world_points = _translate_points(local_points, dx=dx, dy=dy, dz=dz)
    a_point_world = (
        raw_a_local[0] + dx,
        raw_a_local[1] + dy,
        raw_a_local[2] + dz,
    )
    main_start_edge = cast(Edge2P, _edge_points_at_xy_terminal(points=world_points, trace=trace, terminal="start"))
    main_end_edge = cast(Edge2P, _edge_points_at_xy_terminal(points=world_points, trace=trace, terminal="end"))
    center_offset_y = center_y - tx_dd_center_y
    instance_side = _instance_side("tx_dd", (0.0, center_offset_y, 0.0))
    if instance_side != "right":
        raise ValueError(
            "tx_dd right-half realization contract violation: instance side must be right "
            f"(actual={instance_side}, instance_index={instance_index})"
        )
    start_label, end_label = txdd_right_terminal_labels(
        instance_count=instance_count,
        layer_index=layer_index,
    )
    current_direction = _current_direction_from_xy_points(local_points)
    if current_direction != "ccw":
        raise ValueError(
            "tx_dd right-half realization contract violation: generated winding must be ccw "
            f"(actual={current_direction}, instance_count={instance_count}, layer_index={layer_index})"
        )
    return TxDdHalfRealization(
        side=side,
        layer_index=layer_index,
        instance_index=instance_index,
        center_x=dx,
        center_y=center_y,
        world_points=world_points,
        bridge_edge_world=world_bridge_edge,
        a_point_world=cast(Point3, a_point_world),
        main_start_edge=main_start_edge,
        main_end_edge=main_end_edge,
        instance_side=instance_side,
        start_label=start_label,
        end_label=end_label,
        current_direction=current_direction,
    )


def build_txdd_realizations(request: TxDdBuildRequest) -> tuple[TxDdRealization, ...]:
    turns, trace, gap, instance_count, spacing_mm, transform = _validate_request(request)
    tx_dd_scene = require_tx_dd_scene(request.ctx)
    tx_dd_region_min = tx_dd_scene["region_min"]
    tx_dd_region_max = tx_dd_scene["region_max"]
    tx_dd_center_x = tx_dd_scene["center_x"]
    tx_dd_center_y = tx_dd_scene["center_y"]
    board_z = request.pcb["position"][2]
    tx_dd_anchor_z = tx_dd_region_max[2] - request.ctx.tx_dd_top_clearance - request.ctx.cu_thickness
    realizations: list[TxDdRealization] = []
    slots = plan_txdd_slots(
        layer_count=int(request.group["layer_count"]),
        mounts=request.pcb["mounts"],
    )
    for slot in slots:
        right_center_y, tx_dd_layer_index = _tx_dd_center_y_and_layer(
            instance_count=instance_count,
            instance_index=slot.right_index,
            pair_clearance_mm=spacing_mm,
            outer_y=request.ctx.tx_dd_outer_y,
            region_center_y=tx_dd_center_y,
            region_min_y=tx_dd_region_min[1],
            region_max_y=tx_dd_region_max[1],
        )
        if tx_dd_layer_index != slot.layer_index:
            raise ValueError(
                "tx_dd slot contract violation: runtime layer index mismatch "
                f"(expected={slot.layer_index}, actual={tx_dd_layer_index}, right_index={slot.right_index})"
            )
        right = _realize_half(
            request=request,
            side="right",
            layer_index=slot.layer_index,
            instance_index=slot.right_index,
            turns=turns,
            trace=trace,
            gap=gap,
            instance_count=instance_count,
            center_y=right_center_y,
            transform=transform,
            tx_dd_center_x=tx_dd_center_x,
            tx_dd_center_y=tx_dd_center_y,
            tx_dd_anchor_z=tx_dd_anchor_z,
            board_z=board_z,
        )
        realizations.append(
            TxDdRealization(
                slot=slot,
                instance_count=instance_count,
                trace=trace,
                right=right,
            )
        )
    return tuple(realizations)

from __future__ import annotations

from typing import cast

from peetsfea.aedt import Object3d
from peetsfea.identity.hashing import object_name_tag_from_design_id
from peetsfea.types.manifest import CadProbe, CoilPolaritySpec, GroupEndpointEntry, RegionViolation

from ..build_state import BridgeAnchor, DdHalfGeometryCapture, DirectedLandingSection, Edge2P, Point3, require_tx_dd_scene
from ..rules.cad_probe import _object_name
from .group_builder_tx_dd_geometry import (
    _TXDD_VIA_TAB_LENGTH_W,
    _XY_PLANE_NORMAL,
    _append_tx_dd_external_stub_source,
    _build_center_directed_tail_outline,
    _create_txdd_terminal_tail,
    _directed_landing_section_from_raw_edge,
    _edge_midpoint,
    _normalize_tail_inward_dir,
    _ordered_terminal_section_from_landing,
    _terminal_turn_sign,
    _xy_terminal_inward_dir,
)
from .txdd_capture_state import record_txdd_half_state
from .txdd_types import TxDdBuildRequest, TxDdRealization


def capture_txdd_right_half(request: TxDdBuildRequest, realization: TxDdRealization) -> None:
    right = realization.right
    state = request.state
    finalize_inputs = request.finalize_inputs
    pcb = request.pcb
    trace = realization.trace
    right_layer_index = realization.slot.layer_index
    right_index = realization.slot.right_index
    object_name_tag = object_name_tag_from_design_id(request.ctx.design_id)
    if realization.instance_count == 4:
        finalize_inputs.txdd_right_a_points[right_layer_index] = (right.a_point_world, trace)

    right_name = f"coil_tx_dd_g{right_index}_b{request.board_idx}_{object_name_tag}"
    right_created = request.modeler.create_polyline(
        points=right.world_points,
        name=right_name,
        material="copper",
        xsection_type="Rectangle",
        xsection_width=trace,  # type: ignore[arg-type]
        xsection_height=request.ctx.cu_thickness,  # type: ignore[arg-type]
    )
    if not right_created:
        raise ValueError(
            "tx_dd right polyline creation failed "
            f"(name={right_name}, points={len(right.world_points)}, group_kind=tx_dd)"
        )
    right_obj = cast(Object3d, right_created)
    right_obj_name = _object_name(right_obj)
    main_right_feed_in_edge_points = cast(Edge2P, right.main_start_edge)
    main_right_feed_out_edge_points = cast(Edge2P, right.main_end_edge)
    right_bridge_edge_points = right.bridge_edge_world

    has_right_feed_in_tail = False
    right_feed_in_tail_far_edge: Edge2P = main_right_feed_in_edge_points
    right_feed_in_tail_far_midpoint: Point3 = _edge_midpoint(main_right_feed_in_edge_points)
    has_right_a_via_tab = False
    if realization.instance_count == 4 and right_layer_index == 0:
        has_right_feed_in_tail = True
        (
            right_feed_in_tail_outline_points,
            right_feed_in_tail_far_edge,
            right_feed_in_tail_far_midpoint,
        ) = _build_center_directed_tail_outline(
            terminal_edge=main_right_feed_in_edge_points,
            center_xy=(right.center_x, right.center_y),
            inward_tangent_xy=(
                right.world_points[1][0] - right.world_points[0][0],
                right.world_points[1][1] - right.world_points[0][1],
            ),
            terminal_kind="start",
            turn_sign=_terminal_turn_sign(
                right.world_points,
                terminal_kind="start",
                context="tx_dd right feed-in via tab",
            ),
            trace=trace,
            length=_TXDD_VIA_TAB_LENGTH_W * trace,
            context="tx_dd right feed-in via tab",
        )
        right_obj_name = _create_txdd_terminal_tail(
            modeler=request.modeler,
            base_object_name=right_obj_name,
            tail_suffix="via_tab_feed_in",
            tail_outline_points=right_feed_in_tail_outline_points,
            trace=trace,
            cu_thickness=request.ctx.cu_thickness,
            context="tx_dd right feed-in via tab",
        )

    has_right_feed_out_tail = False
    right_feed_out_tail_far_edge: Edge2P = main_right_feed_out_edge_points
    right_feed_out_tail_far_midpoint: Point3 = _edge_midpoint(main_right_feed_out_edge_points)
    if realization.instance_count == 4 and right_layer_index == 1:
        has_right_feed_out_tail = True
        (
            right_feed_out_tail_outline_points,
            right_feed_out_tail_far_edge,
            right_feed_out_tail_far_midpoint,
        ) = _build_center_directed_tail_outline(
            terminal_edge=main_right_feed_out_edge_points,
            center_xy=(right.center_x, right.center_y),
            inward_tangent_xy=(
                right.world_points[-2][0] - right.world_points[-1][0],
                right.world_points[-2][1] - right.world_points[-1][1],
            ),
            terminal_kind="end",
            turn_sign=_terminal_turn_sign(
                right.world_points,
                terminal_kind="end",
                context="tx_dd right feed-out via tab",
            ),
            trace=trace,
            length=_TXDD_VIA_TAB_LENGTH_W * trace,
            context="tx_dd right feed-out via tab",
        )
        right_obj_name = _create_txdd_terminal_tail(
            modeler=request.modeler,
            base_object_name=right_obj_name,
            tail_suffix="via_tab_feed_out",
            tail_outline_points=right_feed_out_tail_outline_points,
            trace=trace,
            cu_thickness=request.ctx.cu_thickness,
            context="tx_dd right feed-out via tab",
        )
    if realization.instance_count == 4:
        has_right_a_via_tab = True
        (
            right_a_via_tab_outline_points,
            _ignored_right_a_via_tab_edge,
            right_a_via_tab_far_midpoint,
        ) = (
            _build_center_directed_tail_outline(
                terminal_edge=main_right_feed_out_edge_points,
                center_xy=(right.center_x, right.center_y),
                inward_tangent_xy=(
                    right.world_points[-2][0] - right.world_points[-1][0],
                    right.world_points[-2][1] - right.world_points[-1][1],
                ),
                terminal_kind="end",
                turn_sign=_terminal_turn_sign(
                    right.world_points,
                    terminal_kind="end",
                    context="tx_dd right a via tab",
                ),
                trace=trace,
                length=_TXDD_VIA_TAB_LENGTH_W * trace,
                context="tx_dd right a via tab",
            )
            if right_layer_index == 0
            else _build_center_directed_tail_outline(
                terminal_edge=main_right_feed_in_edge_points,
                center_xy=(right.center_x, right.center_y),
                inward_tangent_xy=(
                    right.world_points[1][0] - right.world_points[0][0],
                    right.world_points[1][1] - right.world_points[0][1],
                ),
                terminal_kind="start",
                turn_sign=_terminal_turn_sign(
                    right.world_points,
                    terminal_kind="start",
                    context="tx_dd right a via tab",
                ),
                trace=trace,
                length=_TXDD_VIA_TAB_LENGTH_W * trace,
                context="tx_dd right a via tab",
            )
        )
        right_obj_name = _create_txdd_terminal_tail(
            modeler=request.modeler,
            base_object_name=right_obj_name,
            tail_suffix="via_tab_a",
            tail_outline_points=right_a_via_tab_outline_points,
            trace=trace,
            cu_thickness=request.ctx.cu_thickness,
            context="tx_dd right a via tab",
        )
    right_feed_in_edge_points = right_feed_in_tail_far_edge if has_right_feed_in_tail else main_right_feed_in_edge_points
    right_feed_out_edge_points = right_feed_out_tail_far_edge if has_right_feed_out_tail else main_right_feed_out_edge_points

    if realization.instance_count == 2:
        right_inter_half_exit_landing = _directed_landing_section_from_raw_edge(
            edge=right_feed_out_edge_points,
            outward_dir=(-1.0, 0.0, 0.0),
            plane_normal=_XY_PLANE_NORMAL,
            object_name=right_obj_name,
            dd_family="tx_dd",
            dd_pair_index=right_layer_index,
            side="right",
            terminal_polarity="negative",
            terminal_role="inter_half_exit",
            context="tx_dd right inter-half-exit landing",
        )
    elif right_layer_index == 1:
        right_bridge_landing = _directed_landing_section_from_raw_edge(
            edge=right_bridge_edge_points,
            outward_dir=(-1.0, 0.0, 0.0),
            plane_normal=_XY_PLANE_NORMAL,
            object_name=right_obj_name,
            dd_family="tx_dd",
            dd_pair_index=right_layer_index,
            side="right",
            terminal_polarity="negative",
            terminal_role="inter_half_exit",
            context="tx_dd right directed landing",
        )
        right_inter_half_exit_landing = right_bridge_landing
        right_bridge_section = _ordered_terminal_section_from_landing(right_bridge_landing)
        d_edge_points = right_bridge_edge_points
        selection_key = (-right.center_y, pcb["id"], right_index)
        if (
            not isinstance(finalize_inputs.txdd_global_right_bridge_selection_key, tuple)
            or selection_key < finalize_inputs.txdd_global_right_bridge_selection_key
        ):
            finalize_inputs.txdd_global_right_bridge_selection_key = selection_key
            finalize_inputs.txdd_global_right_bridge_edge = d_edge_points
            finalize_inputs.txdd_global_right_bridge_section = right_bridge_section
            finalize_inputs.txdd_global_right_bridge_landing = right_bridge_landing
            finalize_inputs.txdd_global_right_bridge_anchor = cast(
                BridgeAnchor,
                {
                    "center": right_bridge_section["center"],
                    "trace": trace,
                    "plane_normal": _XY_PLANE_NORMAL,
                    "object_name": right_obj_name,
                    "dd_family": "tx_dd",
                    "dd_pair_index": right_layer_index,
                    "side": "right",
                },
            )
            finalize_inputs.txdd_global_right_bridge_object_name = right_obj_name
            finalize_inputs.tx_series_binding.inter_half_exit = right_bridge_landing
        if (
            not isinstance(finalize_inputs.txdd_global_right_d_selection_key, tuple)
            or selection_key < finalize_inputs.txdd_global_right_d_selection_key
        ):
            finalize_inputs.txdd_global_right_d_selection_key = selection_key
            finalize_inputs.txdd_global_right_d_edge = d_edge_points
            finalize_inputs.txdd_global_right_d_object_name = right_obj_name
    else:
        right_inter_half_exit_landing = _directed_landing_section_from_raw_edge(
            edge=right_feed_out_edge_points,
            outward_dir=(-1.0, 0.0, 0.0),
            plane_normal=_XY_PLANE_NORMAL,
            object_name=right_obj_name,
            dd_family="tx_dd",
            dd_pair_index=right_layer_index,
            side="right",
            terminal_polarity="negative",
            terminal_role="inter_half_exit",
            context="tx_dd right inter-half-exit landing",
        )

    if realization.instance_count == 2 or (realization.instance_count == 4 and right_layer_index == 0):
        right_feed_in_landing = _directed_landing_section_from_raw_edge(
            edge=right_feed_in_edge_points,
            outward_dir=(-1.0, 0.0, 0.0),
            plane_normal=_XY_PLANE_NORMAL,
            object_name=right_obj_name,
            dd_family="tx_dd",
            dd_pair_index=right_layer_index,
            side="right",
            terminal_polarity="positive",
            terminal_role="feed_in",
            context="tx_dd right feed-in landing",
        )
        right_feed_in_landing["inward_dir"] = _xy_terminal_inward_dir(
            points=right.world_points,
            terminal="start",
            context="tx_dd right feed-in landing inward_dir",
        )
        if has_right_feed_in_tail:
            right_feed_in_landing["inward_dir"] = _normalize_tail_inward_dir(
                from_point=cast(Point3, tuple(float(v) for v in right_feed_in_tail_far_midpoint)),
                to_point=_edge_midpoint(main_right_feed_in_edge_points),
                context="tx_dd right feed-in landing inward_dir",
            )
        finalize_inputs.tx_series_binding.feed_in = right_feed_in_landing
        finalize_inputs.tx_series_binding.inter_half_exit = right_inter_half_exit_landing
        if realization.instance_count == 2:
            finalize_inputs.tx_series_binding.inter_half_entry = right_feed_in_landing
    if realization.instance_count == 4 and right_layer_index == 1:
        right_inter_half_entry_landing = _directed_landing_section_from_raw_edge(
            edge=right_feed_in_edge_points,
            outward_dir=(-1.0, 0.0, 0.0),
            plane_normal=_XY_PLANE_NORMAL,
            object_name=right_obj_name,
            dd_family="tx_dd",
            dd_pair_index=right_layer_index,
            side="right",
            terminal_polarity="positive",
            terminal_role="inter_half_entry",
            context="tx_dd right inter-half-entry landing",
        )
        finalize_inputs.tx_series_binding.inter_half_entry = right_inter_half_entry_landing
        right_feed_out_landing = _directed_landing_section_from_raw_edge(
            edge=right_feed_out_edge_points,
            outward_dir=(-1.0, 0.0, 0.0),
            plane_normal=_XY_PLANE_NORMAL,
            object_name=right_obj_name,
            dd_family="tx_dd",
            dd_pair_index=right_layer_index,
            side="right",
            terminal_polarity="negative",
            terminal_role="feed_out",
            context="tx_dd right feed-out landing",
        )
        right_feed_out_landing["inward_dir"] = _xy_terminal_inward_dir(
            points=right.world_points,
            terminal="end",
            context="tx_dd right feed-out landing inward_dir",
        )
        if has_right_feed_out_tail:
            right_feed_out_landing["inward_dir"] = _normalize_tail_inward_dir(
                from_point=cast(Point3, tuple(float(v) for v in right_feed_out_tail_far_midpoint)),
                to_point=_edge_midpoint(main_right_feed_out_edge_points),
                context="tx_dd right feed-out landing inward_dir",
            )
        finalize_inputs.tx_series_binding.feed_out = right_feed_out_landing
    elif realization.instance_count == 2:
        right_feed_out_landing = _directed_landing_section_from_raw_edge(
            edge=right_feed_out_edge_points,
            outward_dir=(-1.0, 0.0, 0.0),
            plane_normal=_XY_PLANE_NORMAL,
            object_name=right_obj_name,
            dd_family="tx_dd",
            dd_pair_index=right_layer_index,
            side="right",
            terminal_polarity="negative",
            terminal_role="feed_out",
            context="tx_dd right feed-out landing",
        )
        right_feed_out_landing["inward_dir"] = _xy_terminal_inward_dir(
            points=right.world_points,
            terminal="end",
            context="tx_dd right feed-out landing inward_dir",
        )
        if has_right_feed_out_tail:
            right_feed_out_landing["inward_dir"] = _normalize_tail_inward_dir(
                from_point=cast(Point3, tuple(float(v) for v in right_feed_out_tail_far_midpoint)),
                to_point=_edge_midpoint(main_right_feed_out_edge_points),
                context="tx_dd right feed-out landing inward_dir",
            )
        finalize_inputs.tx_series_binding.feed_out = right_feed_out_landing

    state.object_names.append(right_obj_name)
    if has_right_feed_in_tail or realization.instance_count == 2:
        _append_tx_dd_external_stub_source(
            finalize_inputs=finalize_inputs,
            board_id=pcb["id"],
            trace=trace,
            landing=right_feed_in_landing,
            context="tx_dd right external stub source start",
        )
    if has_right_feed_out_tail or realization.instance_count == 2:
        _append_tx_dd_external_stub_source(
            finalize_inputs=finalize_inputs,
            board_id=pcb["id"],
            trace=trace,
            landing=right_feed_out_landing,
            context="tx_dd right external stub source end",
        )
    if realization.instance_count == 2 or right_layer_index == 1:
        finalize_inputs.tx_series_binding.inter_half_exit = right_inter_half_exit_landing
    if realization.instance_count == 4 and right_layer_index == 1:
        finalize_inputs.tx_series_binding.inter_half_entry = right_inter_half_entry_landing
    if realization.instance_count == 4:
        finalize_inputs.txdd_right_object_names[right_layer_index] = right_obj_name
        if has_right_a_via_tab:
            finalize_inputs.txdd_right_a_points[right_layer_index] = (
                cast(Point3, right_a_via_tab_far_midpoint),
                trace,
            )

    record_txdd_half_state(
        request=request,
        half=right,
        object_name=right_obj_name,
        instance_index=right_index,
        layer_index=right_layer_index,
        main_start_edge=main_right_feed_in_edge_points,
        main_end_edge=main_right_feed_out_edge_points,
        has_start_tail=has_right_feed_in_tail,
        start_tail_far_midpoint=right_feed_in_tail_far_midpoint,
        has_end_tail=has_right_feed_out_tail,
        end_tail_far_midpoint=right_feed_out_tail_far_midpoint,
        bridge_edge=right_bridge_edge_points,
        obj=right_obj,
    )

from __future__ import annotations

from collections.abc import Callable

from peetsfea.identity.hashing import object_name_tag_from_design_id

from ..build_state import _empty_em_port_assignments, _empty_em_ports
from .build_fr4_ops import _finalize_fr4_and_save_project
from .finalize_stage_rx import _apply_rxdd_back_stub_stage
from .finalize_stage_stacked import _apply_stacked_txdd_closure
from ..rules.tx_mode0_rotation import rotate_tx_mode0_plan_objects_if_needed
from .finalize_stage_tx import (
    _apply_tx_chain_bridge_stage,
    _apply_tx_global_unite_stage,
    _apply_tx_semantic_port_stage,
    _apply_tx_vertical_stage,
    _apply_txdd_start_stub_stage,
)
from .finalize_types import FinalizeArtifacts, FinalizePlan
from ..rx_stub_ports import reset_rx_stub_port_back_face_corners


def run_finalize_plan(
    plan: FinalizePlan,
    *,
    stacked_txdd_closer: Callable[..., str],
) -> FinalizeArtifacts:
    reset_rx_stub_port_back_face_corners(plan.design_id)
    object_name_tag = object_name_tag_from_design_id(plan.design_id)
    txdd_is_single_layer = _apply_stacked_txdd_closure(plan, stacked_txdd_closer=stacked_txdd_closer)
    resolved_ports = _empty_em_ports()
    resolved_port_assignments = _empty_em_port_assignments()
    _apply_rxdd_back_stub_stage(
        plan,
        object_name_tag=object_name_tag,
        resolved_ports=resolved_ports,
        resolved_port_assignments=resolved_port_assignments,
    )
    _apply_tx_vertical_stage(plan, object_name_tag=object_name_tag, txdd_is_single_layer=txdd_is_single_layer)
    _apply_txdd_start_stub_stage(plan, object_name_tag=object_name_tag)
    _apply_tx_chain_bridge_stage(plan, object_name_tag=object_name_tag, txdd_is_single_layer=txdd_is_single_layer)
    _apply_tx_global_unite_stage(plan)
    rotate_tx_mode0_plan_objects_if_needed(plan)
    _apply_tx_semantic_port_stage(
        plan,
        resolved_ports=resolved_ports,
        resolved_port_assignments=resolved_port_assignments,
    )
    object_names, fr4_object_names, final_ports, final_port_assignments = _finalize_fr4_and_save_project(
        modeler=plan.modeler,
        hfss=plan.hfss,
        aedt_path=plan.aedt_path,
        design_id=plan.design_id,
        pcb_thickness=plan.pcb_thickness,
        tx_board_ids=plan.tx_board_ids,
        txdd_right_object_names=plan.txdd_right_object_names,
        group_objects=plan.group_objects,
        object_names=plan.object_names,
        cad_probe=plan.cad_probe,
        coil_plane_bboxes=plan.coil_plane_bboxes,
        fr4_object_names=plan.fr4_object_names,
        tx_vertical_fr4_names=plan.tx_vertical_fr4_names,
        resolved_ports=resolved_ports,
        resolved_port_assignments=resolved_port_assignments,
    )
    return FinalizeArtifacts(
        object_names=object_names,
        fr4_object_names=fr4_object_names,
        resolved_ports=final_ports,
        resolved_port_assignments=final_port_assignments,
        tx_dd_rotation_angle_deg=plan.tx_dd_rotation_angle_deg,
        tx_dd_rotation_pivot_xyz=plan.tx_dd_rotation_pivot_xyz,
        tx_dd_rotation_object_names=list(plan.tx_dd_rotation_object_names),
    )

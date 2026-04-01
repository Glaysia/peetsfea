from __future__ import annotations

from collections.abc import Callable
from typing import cast

from .build_name_ops import _replace_object_name_in_landing
from .build_topology_ops import _assert_stacked_tx_dd_half_conductors_closed
from .finalize_helpers import _first_active_name, _landing_name
from .finalize_types import FinalizePlan
from ..build_state import state_is_set


def _apply_stacked_txdd_closure(
    plan: FinalizePlan,
    *,
    stacked_txdd_closer: Callable[..., str],
) -> bool:
    txdd_right_bridge_object_name_active = _first_active_name(
        plan.txdd_global_right_bridge_object_name,
        plan.txdd_global_right_d_object_name,
    )
    txdd_layer_keys = set(plan.txdd_right_object_names.keys())
    txdd_anchor_layer_keys = set(plan.txdd_right_a_points.keys())
    txdd_is_stacked = (1 in txdd_layer_keys) or (1 in txdd_anchor_layer_keys)
    if txdd_is_stacked:
        txdd_right_bridge_object_name_active = stacked_txdd_closer(
            modeler=plan.modeler,
            object_names_by_layer=plan.txdd_right_object_names,
            via_anchor_points=plan.txdd_right_a_points,
            primary_object_name=txdd_right_bridge_object_name_active,
            design_id=plan.design_id,
            via_site_label="right_a",
            via_diameter_mm=plan.via_diameter_mm,
            cu_thickness=plan.cu_thickness,
            pcb_thickness=plan.pcb_thickness,
            group_objects=plan.group_objects,
            object_names=plan.object_names,
            cad_probe=plan.cad_probe,
            txdd_start_stub_sources=plan.txdd_start_stub_sources,
            tx_series_binding=plan.tx_series_binding,
            context="stacked tx_dd right half via closure",
        )
    if txdd_right_bridge_object_name_active:
        if state_is_set(plan.txdd_global_right_bridge_object_name):
            plan.txdd_global_right_bridge_object_name = txdd_right_bridge_object_name_active
        if state_is_set(plan.txdd_global_right_d_object_name):
            plan.txdd_global_right_d_object_name = txdd_right_bridge_object_name_active
        _replace_object_name_in_landing(
            plan.txdd_global_right_bridge_landing,
            old_name=_landing_name(plan.txdd_global_right_bridge_landing),
            new_name=txdd_right_bridge_object_name_active,
        )
    if txdd_is_stacked:
        _assert_stacked_tx_dd_half_conductors_closed(
            txdd_right_a_points=plan.txdd_right_a_points,
            txdd_right_object_names=plan.txdd_right_object_names,
        )
    return not txdd_is_stacked

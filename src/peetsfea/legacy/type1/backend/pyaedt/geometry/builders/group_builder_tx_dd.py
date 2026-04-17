from __future__ import annotations

from typing import Callable

from peetsfea.aedt import Modeler3D

from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance

from ..build_state import Edge2P, FinalizeInputs, GeometryBuildState, GeometryRuntimeContext
from ..rules.placement_rules import _txdd_half_topology
from .group_builder_tx_dd_impl import build_for_board_impl


def build_for_board(
    *,
    modeler: Modeler3D,
    ctx: GeometryRuntimeContext,
    state: GeometryBuildState,
    finalize_inputs: FinalizeInputs,
    board_idx: int,
    pcb: ResolvedPcbInstance,
    group: ResolvedCoilGroup,
    geometry: GroupGeometryParams,
    edge_points_at_path_end: Callable[..., Edge2P],
) -> None:
    build_for_board_impl(
        modeler=modeler,
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=board_idx,
        pcb=pcb,
        group=group,
        geometry=geometry,
        edge_points_at_path_end=edge_points_at_path_end,
        half_topology=_txdd_half_topology,
    )

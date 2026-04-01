from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

from peetsfea.aedt import Modeler3D
from peetsfea.backend.pyaedt.geometry.build_state import FinalizeInputs, GeometryBuildState, GeometryRuntimeContext, set_tx_dd_scene
from peetsfea.backend.pyaedt.geometry.builders.txdd_planner import build_txdd_realizations, plan_txdd_slots
from peetsfea.backend.pyaedt.geometry.builders.txdd_types import TxDdBuildRequest
from peetsfea.backend.pyaedt.geometry.rules.placement_rules import _edge_points_at_xy_terminal, _txdd_half_topology
from peetsfea.topology.tx_dd import edge_points_at_path_end
from peetsfea.types.manifest import GroupGeometryParams, Manifest, ResolvedCoilGroup, ResolvedPcbInstance, ResolvedPcbMount, SelectedParameters, SelectedParametersMax


def _build_runtime_context() -> GeometryRuntimeContext:
    ctx = GeometryRuntimeContext(
        manifest=cast(Manifest, {}),
        selected=cast(SelectedParameters, {}),
        selected_max=cast(SelectedParametersMax, {}),
        selected_groups=cast(list[ResolvedCoilGroup], []),
        selected_group_geometry=cast(list[GroupGeometryParams], []),
        selected_pcbs=cast(list[ResolvedPcbInstance], []),
        group_geometry_by_kind=cast(
            dict[Literal["tx_dd", "tx_vertical", "rx_dd"], GroupGeometryParams],
            {},
        ),
        tx_board_ids=set(),
        design_id="unit_test_design",
        aedt_path=Path("/tmp/unit_test_design.aedt"),
        metadata_path=Path("/tmp/unit_test_design.json"),
        close_on_exit=True,
        tx_dd_outer_x=10.0,
        tx_dd_outer_y=8.0,
        tx_vertical_outer_x=10.0,
        tx_vertical_outer_y=10.0,
        rx_dd_outer_x=10.0,
        rx_dd_outer_y=10.0,
        corner_mode=0,
        pcb_thickness=1.6,
        cu_thickness=0.035,
        tx_dd_top_clearance=1.0,
        tx_vertical_orientation_mode=1,
        rx_face_clearance=0.0,
        tx_vertical_plane="ZX",
    )
    set_tx_dd_scene(
        ctx,
        region_min=(-8.0, -10.0, 0.0),
        region_max=(8.0, 10.0, 10.0),
        center_x=0.0,
        center_y=0.0,
    )
    return ctx


def test_plan_txdd_slots_accepts_single_stacked_mount() -> None:
    mounts = cast(
        list[ResolvedPcbMount],
        [
            {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
        ],
    )
    slots = plan_txdd_slots(layer_count=2, mounts=mounts)
    assert len(slots) == 1
    assert slots[0].layer_index == 0
    assert slots[0].right_index == 1


def test_build_txdd_realizations_records_creation_time_coordinates() -> None:
    request = TxDdBuildRequest(
        modeler=cast(Modeler3D, object()),
        ctx=_build_runtime_context(),
        state=GeometryBuildState(),
        finalize_inputs=FinalizeInputs(),
        board_idx=0,
        pcb=cast(
            ResolvedPcbInstance,
            {
                "id": "pcb_tx",
                "position": (0.0, 0.0, 1.0),
                "mounts": [{"kind": "tx_dd", "selector_mode": "all", "selector_index": 0}],
            },
        ),
        group=cast(
            ResolvedCoilGroup,
            {
                "kind": "tx_dd",
                "layer_count": 1,
                "spacing_mm": 2.0,
                "instance_transforms": [],
            },
        ),
        geometry=cast(
            GroupGeometryParams,
            {
                "turn_count": 1,
                "trace": 1.0,
                "gap": 1.0,
            },
        ),
        edge_points_at_path_end=edge_points_at_path_end,
        half_topology=_txdd_half_topology,
    )
    realizations = build_txdd_realizations(request)
    assert len(realizations) == 1
    realization = realizations[0]
    assert realization.right.center_x == 0.0
    assert realization.right.center_y == 5.0
    assert realization.right.main_start_edge == _edge_points_at_xy_terminal(
        points=realization.right.world_points,
        trace=realization.trace,
        terminal="start",
    )
    assert realization.right.a_point_world[2] == 7.965

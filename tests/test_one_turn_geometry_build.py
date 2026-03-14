from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.backend.pyaedt.geometry.build import (
    _append_rxdd_back_stub_sources_if_needed,
    _edge_points_at_tx_vertical_opposite_terminal,
    _edge_points_at_tx_vertical_terminal,
    _tx_vertical_bridge_edges_from_node,
)
from peetsfea.backend.pyaedt.geometry.build_state import FinalizeInputs, GeometryBuildState, GeometryRuntimeContext
from peetsfea.backend.pyaedt.geometry.group_builder_rx_dd import build_for_board as build_rx_dd_for_board
from peetsfea.backend.pyaedt.geometry.group_builder_tx_vertical import build_for_board as build_tx_vertical_for_board
from peetsfea.types.manifest import GroupGeometryParams, Manifest, ResolvedCoilGroup, ResolvedPcbInstance, SelectedParameters, SelectedParametersMax


class _FakePolylineObject:
    def __init__(self, name: str, points: list[list[float]]) -> None:
        self.name = name
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        zs = [point[2] for point in points]
        self.bounding_box = [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
        self.edges: list[object] = []


class _FakeModeler:
    def __init__(self) -> None:
        self.polyline_calls: list[dict[str, object]] = []

    def create_polyline(self, **kwargs: object) -> _FakePolylineObject:
        self.polyline_calls.append(dict(kwargs))
        return _FakePolylineObject(str(kwargs["name"]), cast(list[list[float]], kwargs["points"]))


def _ctx_base(*, selected_pcbs: list[ResolvedPcbInstance]) -> GeometryRuntimeContext:
    return GeometryRuntimeContext(
        manifest=cast(Manifest, {}),
        selected=cast(SelectedParameters, {}),
        selected_max=cast(SelectedParametersMax, {}),
        selected_groups=[],
        selected_group_geometry=[],
        selected_pcbs=selected_pcbs,
        group_geometry_by_kind=cast(
            dict[Literal["tx_dd", "tx_vertical", "rx_dd"], GroupGeometryParams],
            {"tx_dd": cast(GroupGeometryParams, {}), "tx_vertical": cast(GroupGeometryParams, {}), "rx_dd": cast(GroupGeometryParams, {})},
        ),
        tx_board_ids={pcb["id"] for pcb in selected_pcbs if pcb["role"] == "tx"},
        design_id="demo",
        aedt_path=Path("/tmp/demo.aedt"),
        metadata_path=Path("/tmp/demo.json"),
        close_on_exit=True,
        tx_dd_outer_x=20.0,
        tx_dd_outer_y=10.0,
        tx_vertical_outer_x=20.0,
        tx_vertical_outer_y=8.0,
        rx_dd_outer_x=20.0,
        rx_dd_outer_y=8.0,
        pcb_thickness=1.6,
        cu_thickness=0.035,
        tx_dd_top_clearance=0.1,
        rx_face_clearance=0.0,
        tx_vertical_plane="ZX",
    )


def test_tx_vertical_builder_supports_one_turn() -> None:
    pcb = cast(
        ResolvedPcbInstance,
        {
            "id": "tx_vertical_0",
            "role": "tx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [{"kind": "tx_vertical", "selector_mode": "all", "selector_index": None}],
        },
    )
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.tx_vertical_region_min = (0.0, -10.0, 0.0)
    ctx.tx_vertical_region_max = (40.0, 10.0, 20.0)
    ctx.tx_vertical_center_x = 10.0
    ctx.tx_vertical_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_vertical", "requested_count": 1, "selected_count": 1, "spacing_mm": 0.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "tx_vertical", "turn_count_max": 1, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()

    build_tx_vertical_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=group,
        geometry=geometry,
        edge_points_at_tx_vertical_terminal=_edge_points_at_tx_vertical_terminal,
        edge_points_at_tx_vertical_opposite_terminal=_edge_points_at_tx_vertical_opposite_terminal,
        tx_vertical_bridge_edges_from_node=_tx_vertical_bridge_edges_from_node,
    )

    assert len(modeler.polyline_calls) == 1
    assert len(state.group_objects["tx_vertical"]) == 1
    assert len(state.group_endpoints) == 1
    assert state.placement_violations == []


def test_rx_dd_builder_supports_one_turn() -> None:
    pcb = cast(
        ResolvedPcbInstance,
        {
            "id": "rx_main_0",
            "role": "rx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [{"kind": "rx_dd", "selector_mode": "all", "selector_index": None}],
        },
    )
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.rx_region_min = (0.0, -30.0, 0.0)
    ctx.rx_region_max = (4.0, 30.0, 20.0)
    ctx.rx_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "rx_dd", "requested_count": 2, "selected_count": 2, "spacing_mm": 4.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "rx_dd", "turn_count_max": 1, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()

    build_rx_dd_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=group,
        geometry=geometry,
        append_rxdd_back_stub_sources_if_needed=_append_rxdd_back_stub_sources_if_needed,
    )

    assert len(modeler.polyline_calls) == 2
    assert len(state.group_objects["rx_dd"]) == 2
    assert len(state.group_endpoints) == 2
    assert len(finalize_inputs.rxdd_back_stub_sources) == 4
    assert state.placement_violations == []

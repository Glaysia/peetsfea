from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

import pytest
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.backend.pyaedt.geometry.build import (
    _append_rxdd_back_stub_sources_if_needed,
    _edge_points_at_path_end,
    _edge_points_at_yz_terminal,
    _edge_points_at_tx_vertical_opposite_terminal,
    _edge_points_at_tx_vertical_terminal,
    _tx_vertical_bridge_edges_from_node,
)
from peetsfea.backend.pyaedt.geometry.build_rx_dd import (
    _apply_diagonal_connect_pair_conductor,
    _apply_existing_edge_bridge_conductor,
)
from peetsfea.backend.pyaedt.geometry.build_state import FinalizeInputs, GeometryBuildState, GeometryRuntimeContext
from peetsfea.backend.pyaedt.geometry.group_builder_rx_dd import build_for_board as build_rx_dd_for_board
from peetsfea.backend.pyaedt.geometry.group_builder_tx_dd import build_for_board as build_tx_dd_for_board
from peetsfea.backend.pyaedt.geometry.group_builder_tx_vertical import build_for_board as build_tx_vertical_for_board
from peetsfea.backend.pyaedt.geometry.placement_rules import (
    _build_rxdd_right_points_A_to_d_cw,
    _extend_endpoints,
    _tx_dd_center_y_and_layer,
    _txdd_right_points,
)
from peetsfea.backend.pyaedt.geometry.spiral_points import _map_xy_points_to_yz, _mirror_points_about_y_axis_line
from peetsfea.placement_math import tx_vertical_mode2_center_x_from_tx_dd_min
from peetsfea.types.manifest import CadProbe, GroupGeometryParams, GroupObjects, Manifest, ResolvedCoilGroup, ResolvedPcbInstance, SelectedParameters, SelectedParametersMax


class _FakePolylineObject:
    def __init__(self, name: str, points: list[list[float]]) -> None:
        self.name = name
        self.points = [point[:] for point in points]
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        zs = [point[2] for point in points]
        self.bounding_box = [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
        self.edges: list[object] = []


class _FakeModeler:
    def __init__(self) -> None:
        self.polyline_calls: list[dict[str, object]] = []
        self.cover_lines_calls: list[str] = []
        self.thicken_sheet_calls: list[tuple[str, float]] = []
        self.unite_calls: list[list[str]] = []
        self.objects: dict[str, _FakePolylineObject] = {}

    def create_polyline(self, **kwargs: object) -> _FakePolylineObject:
        self.polyline_calls.append(dict(kwargs))
        obj = _FakePolylineObject(str(kwargs["name"]), cast(list[list[float]], kwargs["points"]))
        self.objects[obj.name] = obj
        return obj

    def cover_lines(self, assignment: str) -> str:
        self.cover_lines_calls.append(assignment)
        return assignment

    def thicken_sheet(self, assignment: str, thickness: float) -> _FakePolylineObject:
        self.thicken_sheet_calls.append((assignment, thickness))
        source = self.objects[assignment]
        min_x, min_y, min_z, max_x, max_y, max_z = source.bounding_box
        span_x = max_x - min_x
        span_y = max_y - min_y
        if span_x <= 1e-9:
            points = [
                [min_x, min_y, min_z],
                [min_x + thickness, max_y, max_z],
            ]
        elif span_y <= 1e-9:
            points = [
                [min_x, min_y, min_z],
                [max_x, min_y + thickness, max_z],
            ]
        else:
            points = [
                [min_x, min_y, min_z],
                [max_x, max_y, min_z + thickness],
            ]
        thickened = _FakePolylineObject(assignment, points)
        self.objects[assignment] = thickened
        return thickened

    def duplicate_and_mirror(
        self,
        assignment: str,
        origin: list[float],
        vector: list[float],
        duplicate_assignment: bool,
    ) -> list[str]:
        _ = origin, vector, duplicate_assignment
        return [f"{assignment}_mirror"]

    def unite(self, *, assignment: list[str]) -> str:
        self.unite_calls.append(list(assignment))
        return assignment[0]


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
        tx_vertical_layout_mode=1,
        tx_vertical_mode2_pair_spacing_mm=0.0,
        tx_vertical_mode2_x_ratio_to_tx_dd_center=1.0,
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


def test_tx_vertical_mode2_builder_uses_rxdd_d_path_on_yz_plane() -> None:
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
    ctx.tx_dd_outer_x = 100.0
    ctx.tx_vertical_outer_x = 100.0
    ctx.tx_vertical_outer_y = 40.0
    ctx.tx_vertical_layout_mode = 2
    ctx.tx_vertical_mode2_pair_spacing_mm = 10.0
    ctx.tx_vertical_plane = "YZ"
    ctx.tx_vertical_region_min = (0.0, -110.0, 0.0)
    ctx.tx_vertical_region_max = (300.0, 110.0, 60.0)
    ctx.tx_vertical_center_x = tx_vertical_mode2_center_x_from_tx_dd_min(
        tx_dd_min_x=0.0,
        tx_dd_outer_x=ctx.tx_dd_outer_x,
        x_ratio=0.7,
    )
    ctx.tx_vertical_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_vertical", "requested_count": 1, "selected_count": 1, "spacing_mm": 0.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "tx_vertical", "turn_count_max": 2, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
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

    expected_local_points = list(
        reversed(
            _build_rxdd_right_points_A_to_d_cw(
                turns=2,
                outer_x=100.0,
                outer_y=40.0,
                trace=1.0,
                gap=1.0,
            )
        )
    )
    expected_right_points = _map_xy_points_to_yz(
        expected_local_points,
        x_const=70.0,
        y_center=55.5,
        z_center=20.0,
    )
    expected_left_points = _mirror_points_about_y_axis_line(expected_right_points, axis_y=0.5)
    expected_right_start_edge = _edge_points_at_yz_terminal(
        terminal_xyz=cast(tuple[float, float, float], tuple(expected_right_points[0])),
        neighbor_xyz=cast(tuple[float, float, float], tuple(expected_right_points[1])),
        trace=1.0,
    )
    expected_right_end_edge = _edge_points_at_yz_terminal(
        terminal_xyz=cast(tuple[float, float, float], tuple(expected_right_points[-1])),
        neighbor_xyz=cast(tuple[float, float, float], tuple(expected_right_points[-2])),
        trace=1.0,
    )
    expected_left_start_edge = _edge_points_at_yz_terminal(
        terminal_xyz=cast(tuple[float, float, float], tuple(expected_left_points[0])),
        neighbor_xyz=cast(tuple[float, float, float], tuple(expected_left_points[1])),
        trace=1.0,
    )
    expected_left_end_edge = _edge_points_at_yz_terminal(
        terminal_xyz=cast(tuple[float, float, float], tuple(expected_left_points[-1])),
        neighbor_xyz=cast(tuple[float, float, float], tuple(expected_left_points[-2])),
        trace=1.0,
    )

    assert len(modeler.polyline_calls) == 2
    assert cast(list[list[float]], modeler.polyline_calls[0]["points"]) == expected_left_points
    assert cast(list[list[float]], modeler.polyline_calls[1]["points"]) == expected_right_points
    assert len(state.group_objects["tx_vertical"]) == 2
    assert len(state.group_endpoints) == 2
    assert all(point[0] == 70.0 for point in expected_right_points)
    assert state.coil_plane_bboxes[0][1] == "YZ"
    assert state.coil_plane_bboxes[1][1] == "YZ"
    assert state.coil_polarity == [
        {
            "group_kind": "tx_vertical",
            "group_instance_index": 0,
            "board_id": "tx_vertical_0",
            "instance_side": "left",
            "current_direction": "cw",
            "b_field_direction": "right",
        },
        {
            "group_kind": "tx_vertical",
            "group_instance_index": 1,
            "board_id": "tx_vertical_0",
            "instance_side": "right",
            "current_direction": "ccw",
            "b_field_direction": "right",
        },
    ]
    assert finalize_inputs.tx_vertical_global_outer_right_edge == expected_right_start_edge
    assert finalize_inputs.tx_vertical_global_outer_left_edge == expected_left_end_edge
    assert finalize_inputs.tx_vertical_mode2_terminal_edges_by_board[("tx_vertical_0", 0)] == {
        "right_start_edge": expected_right_start_edge,
        "right_start_object_name": "coil_tx_vertical_g1_b0_demo",
        "right_end_edge": expected_right_end_edge,
        "right_end_object_name": "coil_tx_vertical_g1_b0_demo",
        "left_start_edge": expected_left_start_edge,
        "left_start_object_name": "coil_tx_vertical_g0_b0_demo",
        "left_end_edge": expected_left_end_edge,
        "left_end_object_name": "coil_tx_vertical_g0_b0_demo",
    }
    assert state.placement_violations == []


def test_tx_vertical_mode2_x_ratio_targets_far_txdd_side() -> None:
    assert tx_vertical_mode2_center_x_from_tx_dd_min(tx_dd_min_x=0.0, tx_dd_outer_x=140.0, x_ratio=0.7) == 98.0
    assert tx_vertical_mode2_center_x_from_tx_dd_min(tx_dd_min_x=0.0, tx_dd_outer_x=140.0, x_ratio=1.0) == 140.0


def test_tx_dd_builder_separates_left_feed_and_vertical_link_terminals() -> None:
    pcb = cast(
        ResolvedPcbInstance,
        {
            "id": "tx_main_0",
            "role": "tx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
            ],
        },
    )
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.tx_dd_outer_x = 100.0
    ctx.tx_dd_outer_y = 60.0
    ctx.tx_dd_region_min = (0.0, -80.0, 0.0)
    ctx.tx_dd_region_max = (160.0, 80.0, 20.0)
    ctx.tx_dd_center_x = 50.0
    ctx.tx_dd_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_dd", "requested_count": 2, "selected_count": 2, "spacing_mm": 0.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "tx_dd", "turn_count_max": 2, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()

    build_tx_dd_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=group,
        geometry=geometry,
        edge_points_at_path_end=_edge_points_at_path_end,
    )

    start_stub_sources = finalize_inputs.txdd_start_stub_sources["tx_main_0"]
    assert len(start_stub_sources) == 2
    right_source = start_stub_sources[0]
    left_source = start_stub_sources[1]
    left_endpoint = next(entry for entry in state.group_endpoints if entry["group_kind"] == "tx_dd" and entry["group_instance_index"] == 0)
    assert ctx.tx_dd_region_min is not None
    assert ctx.tx_dd_region_max is not None
    assert ctx.tx_dd_center_x is not None
    assert ctx.tx_dd_center_y is not None
    right_center_y, _ = _tx_dd_center_y_and_layer(
        instance_count=2,
        instance_index=1,
        pair_clearance_mm=0.0,
        outer_y=ctx.tx_dd_outer_y,
        region_center_y=0.0,
        region_min_y=ctx.tx_dd_region_min[1],
        region_max_y=ctx.tx_dd_region_max[1],
    )
    right_local_points = _extend_endpoints(
        _txdd_right_points(
            turns=2,
            outer_x=ctx.tx_dd_outer_x,
            outer_y=ctx.tx_dd_outer_y,
            trace=1.0,
            gap=1.0,
            instance_count=2,
            layer_index=0,
        ),
        extension=0.5,
    )
    tx_dd_anchor_z = ctx.tx_dd_region_max[2] - ctx.tx_dd_top_clearance - ctx.cu_thickness
    right_world_points = [
        [point[0] + ctx.tx_dd_center_x, point[1] + right_center_y, point[2] + tx_dd_anchor_z]
        for point in right_local_points
    ]
    expected_left_points = _mirror_points_about_y_axis_line(right_world_points, axis_y=ctx.tx_dd_center_y)
    expected_left_vertical_link_edge = _edge_points_at_path_end(points=list(reversed(expected_left_points)), trace=1.0)

    assert left_source[0] == left_endpoint["end_xyz"]
    assert left_source[0] != left_endpoint["start_xyz"]
    assert right_source[0] != left_source[0]
    assert finalize_inputs.txdd_global_left_vertical_link_edge == expected_left_vertical_link_edge
    assert finalize_inputs.txdd_global_left_vertical_link_edge != _edge_points_at_path_end(points=expected_left_points, trace=1.0)


def test_tx_dd_builder_keeps_feed_and_vertical_link_on_different_layers_for_four_layer_case() -> None:
    pcb = cast(
        ResolvedPcbInstance,
        {
            "id": "tx_main_0",
            "role": "tx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 2},
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 3},
            ],
        },
    )
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.tx_dd_outer_x = 100.0
    ctx.tx_dd_outer_y = 60.0
    ctx.tx_dd_region_min = (0.0, -80.0, 0.0)
    ctx.tx_dd_region_max = (160.0, 80.0, 20.0)
    ctx.tx_dd_center_x = 50.0
    ctx.tx_dd_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_dd", "requested_count": 4, "selected_count": 4, "spacing_mm": 0.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "tx_dd", "turn_count_max": 2, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()

    build_tx_dd_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=group,
        geometry=geometry,
        edge_points_at_path_end=_edge_points_at_path_end,
    )

    start_stub_sources = finalize_inputs.txdd_start_stub_sources["tx_main_0"]
    left_feed_object_names = {source[2] for source in start_stub_sources if source[2].endswith("_mirror")}

    assert len(start_stub_sources) == 2
    assert len(left_feed_object_names) == 1
    assert finalize_inputs.txdd_global_left_vertical_link_object_name is not None
    assert finalize_inputs.txdd_global_left_vertical_link_object_name not in left_feed_object_names


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


def test_diagonal_connect_pair_conductor_keeps_rx_dd_polyline_connector() -> None:
    modeler = _FakeModeler()
    group_objects = cast(
        GroupObjects,
        {"tx_dd": [], "tx_vertical": [], "rx_dd": ["coil_rx_left", "coil_rx_right"], "ferrite": []},
    )
    object_names = ["coil_rx_left", "coil_rx_right"]
    cad_probe: list[CadProbe] = []

    _apply_diagonal_connect_pair_conductor(
        modeler=cast(Modeler3D, modeler),
        cu_thickness=0.035,
        sources=[
            ("board_0", 0, "c", (1.0, -5.0, 2.0), 1.0, "coil_rx_left"),
            ("board_0", 0, "d", (1.0, 5.0, 8.0), 1.0, "coil_rx_right"),
        ],
        group_objects=group_objects,
        group_key="rx_dd",
        object_names=object_names,
        cad_probe=cad_probe,
        conductor_name="bridge_rx_dd_d_to_c_demo",
        conductor_error_context="rx_dd diagonal connector",
        region_kind="rx_region_actual",
        region_min=(0.0, -10.0, 0.0),
        region_max=(2.0, 10.0, 10.0),
        placement_violations=[],
    )

    assert cast(list[list[float]], modeler.polyline_calls[0]["points"]) == [[1.0, 5.0, 8.0], [1.0, -5.0, 2.0]]
    assert modeler.unite_calls == [["bridge_rx_dd_d_to_c_demo", "coil_rx_left", "coil_rx_right"]]
    assert cad_probe[-1]["bbox"] == [1.0, -5.0, 2.0, 1.0, 5.0, 8.0]


def test_existing_edge_bridge_conductor_builds_thickened_sheet_for_tx_vertical_mode2() -> None:
    modeler = _FakeModeler()
    group_objects = cast(
        GroupObjects,
        {"tx_dd": [], "tx_vertical": ["coil_txv_left", "coil_txv_right"], "rx_dd": [], "ferrite": []},
    )
    object_names = ["coil_txv_left", "coil_txv_right"]
    cad_probe: list[CadProbe] = []

    united_name = _apply_existing_edge_bridge_conductor(
        modeler=cast(Modeler3D, modeler),
        cu_thickness=0.035,
        first_edge=((1.0, 5.0, 8.0), (1.0, 5.0, 9.0)),
        first_object_name="coil_txv_right",
        second_edge=((1.0, -5.0, 2.0), (1.0, -5.0, 3.0)),
        second_object_name="coil_txv_left",
        group_objects=group_objects,
        group_key="tx_vertical",
        object_names=object_names,
        cad_probe=cad_probe,
        bridge_name="bridge_tx_vertical_mode2_pair_demo",
        bridge_error_context="tx_vertical mode2 pair bridge",
        region_kind="tx_region_vertical",
        region_min=(0.0, -10.0, 0.0),
        region_max=(3.0, 10.0, 10.0),
        placement_violations=[],
        x_jog_mm=1.0,
    )

    assert cast(list[list[float]], modeler.polyline_calls[0]["points"]) == [
        [2.0, 5.0, 8.0],
        [2.0, 5.0, 9.0],
        [1.0, 5.0, 9.0],
        [1.0, 5.0, 8.0],
    ]
    assert cast(list[list[float]], modeler.polyline_calls[1]["points"]) == [
        [2.0, 5.0, 8.0],
        [2.0, 5.0, 9.0],
        [2.0, -5.0, 3.0],
        [2.0, -5.0, 2.0],
    ]
    assert cast(list[list[float]], modeler.polyline_calls[2]["points"]) == [
        [2.0, -5.0, 2.0],
        [2.0, -5.0, 3.0],
        [1.0, -5.0, 3.0],
        [1.0, -5.0, 2.0],
    ]
    assert modeler.cover_lines_calls == [
        "bridge_tx_vertical_mode2_pair_demo_jog_out",
        "bridge_tx_vertical_mode2_pair_demo",
        "bridge_tx_vertical_mode2_pair_demo_jog_in",
    ]
    assert modeler.thicken_sheet_calls == [
        ("bridge_tx_vertical_mode2_pair_demo_jog_out", 0.14),
        ("bridge_tx_vertical_mode2_pair_demo", 0.14),
        ("bridge_tx_vertical_mode2_pair_demo_jog_in", 0.14),
    ]
    assert modeler.unite_calls == [[
        "coil_txv_right",
        "coil_txv_left",
        "bridge_tx_vertical_mode2_pair_demo_jog_out",
        "bridge_tx_vertical_mode2_pair_demo",
        "bridge_tx_vertical_mode2_pair_demo_jog_in",
    ]]
    assert cad_probe[-3]["bbox"] == pytest.approx([1.0, 5.0, 8.0, 2.0, 5.14, 9.0], abs=1e-12)
    assert cad_probe[-2]["bbox"] == pytest.approx([2.0, -5.0, 2.0, 2.14, 5.0, 9.0], abs=1e-12)
    assert cad_probe[-1]["bbox"] == pytest.approx([1.0, -5.0, 2.0, 2.0, -4.86, 3.0], abs=1e-12)
    assert united_name == "coil_txv_right"

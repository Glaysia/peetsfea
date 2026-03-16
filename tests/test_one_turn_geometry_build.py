from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

import pytest
from ansys.aedt.core import Hfss
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
    _apply_back_connect_stub_pair_bridge,
    _apply_existing_edge_bridge_conductor,
    _finalize_solids_and_substrates_impl,
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
        self.create_box_calls: list[dict[str, object]] = []
        self.cover_lines_calls: list[str] = []
        self.thicken_sheet_calls: list[tuple[str, float]] = []
        self.subtract_calls: list[dict[str, object]] = []
        self.get_object_faces_calls: list[str] = []
        self.unite_calls: list[list[str]] = []
        self.objects: dict[str, _FakePolylineObject] = {}

    def create_polyline(self, **kwargs: object) -> _FakePolylineObject:
        self.polyline_calls.append(dict(kwargs))
        obj = _FakePolylineObject(str(kwargs["name"]), cast(list[list[float]], kwargs["points"]))
        self.objects[obj.name] = obj
        return obj

    def create_box(self, **kwargs: object) -> _FakePolylineObject:
        self.create_box_calls.append(dict(kwargs))
        origin = cast(list[float], kwargs["origin"])
        sizes = cast(list[float], kwargs["sizes"])
        obj = _FakePolylineObject(
            str(kwargs["name"]),
            [
                origin[:],
                [origin[0] + sizes[0], origin[1] + sizes[1], origin[2] + sizes[2]],
            ],
        )
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

    def subtract(self, *, blank_list: list[str], tool_list: list[str], keep_originals: bool) -> bool:
        self.subtract_calls.append(
            {
                "blank_list": list(blank_list),
                "tool_list": list(tool_list),
                "keep_originals": keep_originals,
            }
        )
        return True

    def get_object_faces(self, assignment: str) -> list[int]:
        self.get_object_faces_calls.append(assignment)
        return [1]

    def unite(self, *, assignment: list[str]) -> str:
        self.unite_calls.append(list(assignment))
        return assignment[0]


class _FakeBoundaryModule:
    def __init__(self) -> None:
        self.auto_identify_ports_calls: list[dict[str, object]] = []

    def AutoIdentifyPorts(
        self,
        faces: list[object],
        is_wave_port: bool,
        reference_conductors: list[object],
        port_name: str,
        renormalize: bool,
    ) -> None:
        self.auto_identify_ports_calls.append(
            {
                "faces": list(faces),
                "is_wave_port": is_wave_port,
                "reference_conductors": list(reference_conductors),
                "port_name": port_name,
                "renormalize": renormalize,
            }
        )


class _FakeHfss:
    def __init__(self) -> None:
        self.oboundary = _FakeBoundaryModule()
        self.save_project_calls: list[str] = []

    def save_project(self, path: str) -> None:
        self.save_project_calls.append(path)


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


def test_tx_vertical_builder_rejects_turn_count_above_three_even_if_feasible() -> None:
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
    ctx.tx_vertical_outer_x = 100.0
    ctx.tx_vertical_outer_y = 40.0
    ctx.tx_vertical_region_min = (0.0, -10.0, 0.0)
    ctx.tx_vertical_region_max = (140.0, 10.0, 60.0)
    ctx.tx_vertical_center_x = 50.0
    ctx.tx_vertical_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_vertical", "requested_count": 1, "selected_count": 1, "spacing_mm": 0.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "tx_vertical", "turn_count_max": 4, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()

    with pytest.raises(ValueError, match=r"selected_group_geometry\.tx_vertical\.turn_count_max must be <= 3"):
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


def test_tx_vertical_mode2_builder_flips_winding_on_yz_plane() -> None:
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

    expected_local_points = _build_rxdd_right_points_A_to_d_cw(
        turns=2,
        outer_x=100.0,
        outer_y=40.0,
        trace=1.0,
        gap=1.0,
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
            "current_direction": "ccw",
            "b_field_direction": "right",
        },
        {
            "group_kind": "tx_vertical",
            "group_instance_index": 1,
            "board_id": "tx_vertical_0",
            "instance_side": "right",
            "current_direction": "cw",
            "b_field_direction": "left",
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


def test_finalize_solids_bridges_tx_vertical_mode2_using_right_end_to_left_start_pair() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    group_objects = cast(
        GroupObjects,
        {
            "tx_dd": ["coil_txdd_right", "coil_txdd_left"],
            "tx_vertical": ["coil_txv_left", "coil_txv_right"],
            "rx_dd": [],
            "ferrite": [],
        },
    )
    object_names = ["coil_txdd_right", "coil_txdd_left", "coil_txv_left", "coil_txv_right"]
    cad_probe: list[CadProbe] = []

    finalized_object_names, _ = _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo_tx_vertical_mode2.aedt"),
        design_id="demo_tx_vertical_mode2",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        tx_board_ids=set(),
        tx_vertical_nodes_by_board={},
        tx_vertical_mode2_terminal_edges_by_board={
            ("tx_vertical_0", 0): {
                "right_start_edge": ((1.0, 5.0, 8.0), (1.0, 5.0, 9.0)),
                "right_start_object_name": "coil_txv_right",
                "right_end_edge": ((1.0, 5.0, 6.0), (1.0, 5.0, 7.0)),
                "right_end_object_name": "coil_txv_right",
                "left_start_edge": ((1.0, -5.0, 4.0), (1.0, -5.0, 5.0)),
                "left_start_object_name": "coil_txv_left",
                "left_end_edge": ((1.0, -5.0, 2.0), (1.0, -5.0, 3.0)),
                "left_end_object_name": "coil_txv_left",
            }
        },
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(3.0, 10.0, 10.0),
        txdd_right_a_points={},
        txdd_right_object_names={},
        txdd_left_a_points={},
        txdd_left_object_names={},
        txdd_start_stub_sources={},
        rxdd_back_stub_sources=[],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=cad_probe,
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        txdd_global_right_d_edge=((0.0, 6.0, 6.0), (0.0, 6.0, 7.0)),
        txdd_global_right_d_object_name="coil_txdd_right",
        txdd_global_left_vertical_link_edge=((0.0, -6.0, 4.0), (0.0, -6.0, 5.0)),
        txdd_global_left_vertical_link_object_name="coil_txdd_left",
        tx_vertical_global_outer_right_edge=((1.0, 5.0, 8.0), (1.0, 5.0, 9.0)),
        tx_vertical_global_outer_left_edge=((1.0, -5.0, 2.0), (1.0, -5.0, 3.0)),
    )

    assert cast(list[list[float]], modeler.polyline_calls[0]["points"]) == [
        [2.0, 5.0, 6.0],
        [2.0, 5.0, 7.0],
        [1.0, 5.0, 7.0],
        [1.0, 5.0, 6.0],
    ]
    assert cast(list[list[float]], modeler.polyline_calls[1]["points"]) == [
        [2.0, 5.0, 6.0],
        [2.0, 5.0, 7.0],
        [2.0, -5.0, 5.0],
        [2.0, -5.0, 4.0],
    ]
    assert cast(list[list[float]], modeler.polyline_calls[2]["points"]) == [
        [2.0, -5.0, 4.0],
        [2.0, -5.0, 5.0],
        [1.0, -5.0, 5.0],
        [1.0, -5.0, 4.0],
    ]
    assert finalized_object_names


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
    right_endpoint = next(entry for entry in state.group_endpoints if entry["group_kind"] == "tx_dd" and entry["group_instance_index"] == 1)
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

    assert right_source[0] == right_endpoint["start_xyz"]
    assert right_source[0] != right_endpoint["end_xyz"]
    assert left_source[0] == left_endpoint["end_xyz"]
    assert left_source[0] != left_endpoint["start_xyz"]
    assert right_source[0] != left_source[0]
    assert finalize_inputs.txdd_global_left_vertical_link_edge == expected_left_vertical_link_edge
    assert finalize_inputs.txdd_global_left_vertical_link_edge != _edge_points_at_path_end(points=expected_left_points, trace=1.0)
    assert state.coil_polarity == [
        {
            "group_kind": "tx_dd",
            "group_instance_index": 1,
            "board_id": "tx_main_0",
            "instance_side": "right",
            "current_direction": "ccw",
            "b_field_direction": "up",
        },
        {
            "group_kind": "tx_dd",
            "group_instance_index": 0,
            "board_id": "tx_main_0",
            "instance_side": "left",
            "current_direction": "cw",
            "b_field_direction": "down",
        },
    ]


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
    assert {
        (
            entry["group_instance_index"],
            entry["instance_side"],
            entry["current_direction"],
            entry["b_field_direction"],
        )
        for entry in state.coil_polarity
    } == {
        (1, "right", "ccw", "up"),
        (3, "right", "ccw", "up"),
        (0, "left", "cw", "down"),
        (2, "left", "cw", "down"),
    }


def test_tx_dd_builder_uses_opposite_left_feed_terminal_for_stacked_four_layer_case() -> None:
    pcbs = [
        cast(
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
        ),
        cast(
            ResolvedPcbInstance,
            {
                "id": "tx_main_1",
                "role": "tx",
                "position": (0.0, 0.0, 4.0),
                "rotation_deg": 0.0,
                "present": True,
                "z_mode": "absolute",
                "z_relative_base_id": None,
                "z_delta_path": None,
                "mounts": [
                    {"kind": "tx_dd", "selector_mode": "index", "selector_index": 2},
                    {"kind": "tx_dd", "selector_mode": "index", "selector_index": 3},
                ],
            },
        ),
    ]
    ctx = _ctx_base(selected_pcbs=pcbs)
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

    for board_idx, pcb in enumerate(pcbs):
        build_tx_dd_for_board(
            modeler=cast(Modeler3D, modeler),
            ctx=ctx,
            state=state,
            finalize_inputs=finalize_inputs,
            board_idx=board_idx,
            pcb=pcb,
            group=group,
            geometry=geometry,
            edge_points_at_path_end=_edge_points_at_path_end,
        )

    lower_board_sources = finalize_inputs.txdd_start_stub_sources["tx_main_1"]
    assert len(lower_board_sources) == 2
    right_lower_source, left_lower_source = lower_board_sources

    lower_right_endpoint = next(
        entry
        for entry in state.group_endpoints
        if entry["group_kind"] == "tx_dd" and entry["board_id"] == "tx_main_1" and entry["group_instance_index"] == 3
    )
    lower_left_endpoint = next(
        entry
        for entry in state.group_endpoints
        if entry["group_kind"] == "tx_dd" and entry["board_id"] == "tx_main_1" and entry["group_instance_index"] == 2
    )

    assert right_lower_source[0] == lower_right_endpoint["start_xyz"]
    assert left_lower_source[0] == lower_left_endpoint["start_xyz"]
    assert left_lower_source[0] != lower_left_endpoint["end_xyz"]


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


def test_back_connect_stub_pair_bridge_builds_minus_x_yz_sheet_for_rx_dd() -> None:
    modeler = _FakeModeler()
    group_objects = cast(
        GroupObjects,
        {"tx_dd": [], "tx_vertical": [], "rx_dd": ["coil_rx_left", "coil_rx_right"], "ferrite": []},
    )
    object_names = ["coil_rx_left", "coil_rx_right"]
    cad_probe: list[CadProbe] = []

    _apply_back_connect_stub_pair_bridge(
        modeler=cast(Modeler3D, modeler),
        design_id="demo",
        cu_thickness=0.035,
        sources=[
            ("board_0", 0, "B", (1.0, -6.0, 1.0), 1.0, "coil_rx_left"),
            ("board_0", 0, "d", (1.0, 5.0, 8.0), 1.0, "coil_rx_right"),
        ],
        endpoint_labels=("d", "B"),
        stub_length_mm=1.0,
        group_objects=group_objects,
        group_key="rx_dd",
        object_names=object_names,
        cad_probe=cad_probe,
        bridge_name="bridge_rx_dd_d_to_b_demo",
        stub_name_prefix="rxc",
        stub_error_context="rx_dd connect stub",
        bridge_error_context="rx_dd yz sheet bridge",
    )

    assert [call["name"] for call in modeler.create_box_calls] == ["rxc_board_0_0_B", "rxc_board_0_0_d"]
    assert cast(list[float], modeler.create_box_calls[0]["origin"]) == [0.0, -6.5, 0.5]
    assert cast(list[float], modeler.create_box_calls[0]["sizes"]) == [1.0, 1.0, 1.0]
    assert cast(list[float], modeler.create_box_calls[1]["origin"]) == [0.0, 4.5, 7.5]
    assert cast(list[float], modeler.create_box_calls[1]["sizes"]) == [1.0, 1.0, 1.0]
    assert cast(list[list[float]], modeler.polyline_calls[0]["points"]) == [
        [0.0, 4.5, 7.5],
        [0.0, 4.5, 8.5],
        [0.0, -6.5, 1.5],
        [0.0, -6.5, 0.5],
    ]
    assert modeler.unite_calls == [
        ["coil_rx_left", "rxc_board_0_0_B"],
        ["coil_rx_right", "rxc_board_0_0_d"],
        ["bridge_rx_dd_d_to_b_demo", "coil_rx_left", "coil_rx_right"],
    ]
    assert cad_probe[-1]["bbox"] == [0.0, -6.5, 0.5, 0.14, 4.5, 8.5]


def test_finalize_solids_routes_rx_port_over_a_to_c_and_pair_connector_over_d_to_b() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    group_objects = cast(
        GroupObjects,
        {"tx_dd": [], "tx_vertical": [], "rx_dd": ["coil_rx_left", "coil_rx_right"], "ferrite": []},
    )
    object_names = ["coil_rx_left", "coil_rx_right"]
    cad_probe: list[CadProbe] = []

    finalized_object_names, _ = _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo.aedt"),
        design_id="demo",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        tx_board_ids=set(),
        tx_vertical_nodes_by_board={},
        tx_vertical_mode2_terminal_edges_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(10.0, 10.0, 10.0),
        txdd_right_a_points={},
        txdd_right_object_names={},
        txdd_left_a_points={},
        txdd_left_object_names={},
        txdd_start_stub_sources={},
        rxdd_back_stub_sources=[
            ("rx_main", 0, "B", (1.0, -6.0, 1.0), 1.0, "coil_rx_left"),
            ("rx_main", 0, "c", (1.0, -5.0, 2.0), 1.0, "coil_rx_left"),
            ("rx_main", 1, "A", (1.0, 6.0, 9.0), 1.0, "coil_rx_right"),
            ("rx_main", 1, "d", (1.0, 5.0, 8.0), 1.0, "coil_rx_right"),
        ],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=cad_probe,
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        txdd_global_right_d_edge=None,
        txdd_global_right_d_object_name=None,
        txdd_global_left_vertical_link_edge=None,
        txdd_global_left_vertical_link_object_name=None,
        tx_vertical_global_outer_right_edge=None,
        tx_vertical_global_outer_left_edge=None,
    )

    assert [call["name"] for call in modeler.create_box_calls] == [
        "rxs_rx_main_0_c",
        "rxs_rx_main_1_A",
        "rxc_rx_main_0_B",
        "rxc_rx_main_1_d",
    ]
    assert cast(list[float], modeler.create_box_calls[2]["origin"]) == [0.0, -6.5, 0.5]
    assert cast(list[float], modeler.create_box_calls[2]["sizes"]) == [1.0, 1.0, 1.0]
    assert cast(list[float], modeler.create_box_calls[3]["origin"]) == [0.0, 4.5, 7.5]
    assert cast(list[float], modeler.create_box_calls[3]["sizes"]) == [1.0, 1.0, 1.0]
    assert cast(list[list[float]], modeler.polyline_calls[0]["points"]) == [
        [0.0, 4.5, 7.5],
        [0.0, 4.5, 8.5],
        [0.0, -6.5, 1.5],
        [0.0, -6.5, 0.5],
    ]
    assert cast(str, modeler.polyline_calls[0]["name"]) == "bridge_rx_dd_d_to_b_demo"
    assert cast(str, modeler.polyline_calls[1]["name"]) == "sheet_rxdd_ports"
    assert modeler.get_object_faces_calls == ["sheet_rxdd_ports"]
    assert hfss.oboundary.auto_identify_ports_calls == [
        {
            "faces": ["NAME:Faces", 1],
            "is_wave_port": False,
            "reference_conductors": ["NAME:ReferenceConductors", "rxs_rx_main_0_c"],
            "port_name": "RX_TML",
            "renormalize": True,
        }
    ]
    assert hfss.save_project_calls == ["/tmp/demo.aedt"]
    assert "bridge_rx_dd_d_to_b_demo" in finalized_object_names


def test_finalize_solids_keeps_rx_port_reference_on_c_stub_when_sources_are_reversed() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    group_objects = cast(
        GroupObjects,
        {"tx_dd": [], "tx_vertical": [], "rx_dd": ["coil_rx_left", "coil_rx_right"], "ferrite": []},
    )
    object_names = ["coil_rx_left", "coil_rx_right"]
    cad_probe: list[CadProbe] = []

    _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo_reversed.aedt"),
        design_id="demo_reversed",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        tx_board_ids=set(),
        tx_vertical_nodes_by_board={},
        tx_vertical_mode2_terminal_edges_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(10.0, 10.0, 10.0),
        txdd_right_a_points={},
        txdd_right_object_names={},
        txdd_left_a_points={},
        txdd_left_object_names={},
        txdd_start_stub_sources={},
        rxdd_back_stub_sources=[
            ("rx_main", 1, "d", (1.0, 5.0, 8.0), 1.0, "coil_rx_right"),
            ("rx_main", 1, "A", (1.0, 6.0, 9.0), 1.0, "coil_rx_right"),
            ("rx_main", 0, "c", (1.0, -5.0, 2.0), 1.0, "coil_rx_left"),
            ("rx_main", 0, "B", (1.0, -6.0, 1.0), 1.0, "coil_rx_left"),
        ],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=cad_probe,
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        txdd_global_right_d_edge=None,
        txdd_global_right_d_object_name=None,
        txdd_global_left_vertical_link_edge=None,
        txdd_global_left_vertical_link_object_name=None,
        tx_vertical_global_outer_right_edge=None,
        tx_vertical_global_outer_left_edge=None,
    )

    assert hfss.oboundary.auto_identify_ports_calls == [
        {
            "faces": ["NAME:Faces", 1],
            "is_wave_port": False,
            "reference_conductors": ["NAME:ReferenceConductors", "rxs_rx_main_0_c"],
            "port_name": "RX_TML",
            "renormalize": True,
        }
    ]


def test_finalize_solids_uses_opposite_tx_stub_as_reference_conductor() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    group_objects = cast(
        GroupObjects,
        {"tx_dd": ["coil_tx_right", "coil_tx_left"], "tx_vertical": [], "rx_dd": [], "ferrite": []},
    )
    object_names = ["coil_tx_right", "coil_tx_left"]
    cad_probe: list[CadProbe] = []

    finalized_object_names, _ = _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo_tx.aedt"),
        design_id="demo_tx",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        tx_board_ids={"tx_main_0"},
        tx_vertical_nodes_by_board={},
        tx_vertical_mode2_terminal_edges_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(10.0, 10.0, 10.0),
        txdd_right_a_points={},
        txdd_right_object_names={},
        txdd_left_a_points={},
        txdd_left_object_names={},
        txdd_start_stub_sources={
            "tx_main_0": [
                ((10.0, 6.0, 9.0), 1.0, "coil_tx_right"),
                ((10.0, -6.0, 9.0), 1.0, "coil_tx_left"),
            ]
        },
        rxdd_back_stub_sources=[],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=cad_probe,
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        txdd_global_right_d_edge=None,
        txdd_global_right_d_object_name=None,
        txdd_global_left_vertical_link_edge=None,
        txdd_global_left_vertical_link_object_name=None,
        tx_vertical_global_outer_right_edge=None,
        tx_vertical_global_outer_left_edge=None,
    )

    assert [call["name"] for call in modeler.create_box_calls] == [
        "txs_tx_main_0_0",
        "txs_tx_main_0_1",
    ]
    assert cast(str, modeler.polyline_calls[0]["name"]) == "sheet_txdd_ports_tx_main_0"
    assert modeler.get_object_faces_calls == ["sheet_txdd_ports_tx_main_0"]
    assert hfss.oboundary.auto_identify_ports_calls == [
        {
            "faces": ["NAME:Faces", 1],
            "is_wave_port": False,
            "reference_conductors": ["NAME:ReferenceConductors", "txs_tx_main_0_1"],
            "port_name": "TX_TML",
            "renormalize": True,
        }
    ]
    assert hfss.save_project_calls == ["/tmp/demo_tx.aedt"]
    assert "sheet_txdd_ports_tx_main_0" in finalized_object_names


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

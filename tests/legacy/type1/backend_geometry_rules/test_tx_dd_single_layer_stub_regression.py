from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

from peetsfea.aedt import Modeler3D

from peetsfea.legacy.type1.backend.pyaedt.geometry.build import _edge_points_at_path_end
from peetsfea.legacy.type1.backend.pyaedt.geometry.build_state import FinalizeInputs, GeometryBuildState, GeometryRuntimeContext
from peetsfea.legacy.type1.backend.pyaedt.geometry.builders.group_builder_tx_dd import build_for_board as build_tx_dd_for_board
from peetsfea.types.manifest import (
    GroupGeometryParams,
    Manifest,
    ResolvedCoilGroup,
    ResolvedPcbInstance,
    SelectedParameters,
    SelectedParametersMax,
)


class _FakeEdgePoint:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z


class _FakeEdge:
    def __init__(self, first: list[float], second: list[float]) -> None:
        self.midpoint = _FakeEdgePoint(
            (first[0] + second[0]) / 2.0,
            (first[1] + second[1]) / 2.0,
            (first[2] + second[2]) / 2.0,
        )


class _FakePolylineObject:
    def __init__(self, name: str, points: list[list[float]], *, close_surface: bool) -> None:
        self.name = name
        self.edge_ids: list[int] = []
        self.edges: list[_FakeEdge] = []
        if points:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            zs = [point[2] for point in points]
            self.bounding_box = [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
        else:
            self.bounding_box = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        for idx in range(len(points) - 1):
            self.edge_ids.append(idx + 1)
            self.edges.append(_FakeEdge(points[idx], points[idx + 1]))
        if close_surface and len(points) > 2:
            self.edge_ids.append(len(self.edge_ids) + 1)
            self.edges.append(_FakeEdge(points[-1], points[0]))


class _FakeModeler:
    def create_polyline(self, **kwargs: object) -> _FakePolylineObject:
        points = cast(list[list[float]], kwargs["points"])
        return _FakePolylineObject(
            str(kwargs["name"]),
            points,
            close_surface=bool(kwargs.get("close_surface", False)),
        )


def _ctx() -> GeometryRuntimeContext:
    return GeometryRuntimeContext(
        manifest=cast(Manifest, {}),
        selected=cast(SelectedParameters, {}),
        selected_max=cast(SelectedParametersMax, {}),
        selected_groups=[],
        selected_group_geometry=[],
        selected_pcbs=[],
        group_geometry_by_kind=cast(
            dict[Literal["tx_dd", "tx_vertical", "rx_dd"], GroupGeometryParams],
            {
                "tx_dd": cast(GroupGeometryParams, {}),
                "tx_vertical": cast(GroupGeometryParams, {}),
                "rx_dd": cast(GroupGeometryParams, {}),
            },
        ),
        tx_board_ids={"tx_main_0"},
        design_id="single_layer_txdd_stub_regression",
        aedt_path=Path("/tmp/single_layer_txdd_stub_regression.aedt"),
        metadata_path=Path("/tmp/single_layer_txdd_stub_regression.json"),
        close_on_exit=True,
        tx_dd_outer_x=100.0,
        tx_dd_outer_y=60.0,
        tx_vertical_outer_x=20.0,
        tx_vertical_outer_y=8.0,
        rx_dd_outer_x=20.0,
        rx_dd_outer_y=8.0,
        corner_mode=0,
        pcb_thickness=1.6,
        cu_thickness=0.035,
        tx_dd_top_clearance=0.1,
        tx_vertical_orientation_mode=1,
        rx_face_clearance=0.0,
        tx_vertical_plane="ZX",
        tx_dd_region_min=(0.0, -80.0, 0.0),
        tx_dd_region_max=(160.0, 80.0, 20.0),
        tx_dd_center_x=50.0,
        tx_dd_center_y=0.0,
    )


def _tx_pcb() -> ResolvedPcbInstance:
    return cast(
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


def test_single_layer_tx_dd_keeps_right_feed_in_external_stub_source() -> None:
    ctx = _ctx()
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_dd", "layer_count": 1, "spacing_mm": 0.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {
            "kind": "tx_dd",
            "turn_count": 1,
            "band_ratio": 0.2,
            "metal_ratio": 0.5,
            "trace": 1.0,
            "gap": 1.0,
        },
    )

    build_tx_dd_for_board(
        modeler=cast(Modeler3D, _FakeModeler()),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=_tx_pcb(),
        group=group,
        geometry=geometry,
        edge_points_at_path_end=_edge_points_at_path_end,
    )

    board_sources = finalize_inputs.txdd_start_stub_sources["tx_main_0"]
    feed_in = finalize_inputs.tx_series_binding.feed_in
    assert "inward_dir" in feed_in
    expected_feed_in_source = (feed_in["center"], geometry["trace"], feed_in["object_name"], feed_in["inward_dir"])

    assert len(board_sources) == 4
    assert expected_feed_in_source in board_sources
    assert sum(1 for source in board_sources if source[2] == feed_in["object_name"]) == 2

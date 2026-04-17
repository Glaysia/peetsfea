from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Literal, cast

import pytest
from peetsfea.aedt import Modeler3D

import peetsfea.legacy.type1.backend.pyaedt.geometry.builders.group_builder_tx_dd as group_builder_tx_dd_module
from peetsfea.legacy.type1.backend.pyaedt.geometry.build import _edge_points_at_path_end
from peetsfea.legacy.type1.backend.pyaedt.geometry.build_state import (
    DirectedLandingSection,
    FinalizeInputs,
    GeometryBuildState,
    GeometryRuntimeContext,
    TxDdStartStubSource,
)
from peetsfea.legacy.type1.backend.pyaedt.geometry.builders.group_builder_tx_dd import build_for_board as build_tx_dd_for_board
from peetsfea.legacy.type1.backend.pyaedt.geometry.rules.placement_rules import _TxDdRightLocalTopology
from peetsfea.types.manifest import (
    GroupGeometryParams,
    Manifest,
    ResolvedCoilGroup,
    ResolvedPcbInstance,
    SelectedParameters,
    SelectedParametersMax,
)

_Point3 = tuple[float, float, float]
_TxDdStartStubSource = TxDdStartStubSource


class _FakeEdge:
    def __init__(self, midpoint: tuple[float, float, float]) -> None:
        self.midpoint = midpoint


class _FakePolylineObject:
    def __init__(self, name: str, points: list[list[float]]) -> None:
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


class _FakeModeler:
    def __init__(self) -> None:
        self.polyline_calls: list[dict[str, object]] = []
        self.cover_lines_calls: list[str] = []
        self.thicken_sheet_calls: list[tuple[str, float]] = []
        self.unite_calls: list[list[str]] = []
        self.objects: dict[str, _FakePolylineObject] = {}
        self.next_edge_id = 1

    def _register_edge(self, obj: _FakePolylineObject, first: list[float], second: list[float]) -> None:
        obj.edge_ids.append(self.next_edge_id)
        obj.edges.append(
            _FakeEdge(
                (
                    (first[0] + second[0]) / 2.0,
                    (first[1] + second[1]) / 2.0,
                    (first[2] + second[2]) / 2.0,
                )
            )
        )
        self.next_edge_id += 1

    def create_polyline(self, **kwargs: object) -> _FakePolylineObject:
        self.polyline_calls.append(dict(kwargs))
        points = cast(list[list[float]], kwargs["points"])
        obj = _FakePolylineObject(str(kwargs["name"]), points)
        close_surface = bool(kwargs.get("close_surface", False))
        for idx in range(len(points) - 1):
            self._register_edge(obj, points[idx], points[idx + 1])
        if close_surface and len(points) > 2:
            self._register_edge(obj, points[-1], points[0])
        self.objects[obj.name] = obj
        return obj

    def cover_lines(self, assignment: str) -> str:
        self.cover_lines_calls.append(assignment)
        return assignment

    def thicken_sheet(self, assignment: str, thickness: float) -> _FakePolylineObject:
        self.thicken_sheet_calls.append((assignment, thickness))
        source = self.objects[assignment]
        thickened = _FakePolylineObject(assignment, [[source.bounding_box[0], source.bounding_box[1], source.bounding_box[2]], [source.bounding_box[3], source.bounding_box[4], source.bounding_box[5] + thickness]])
        thickened.edge_ids = list(source.edge_ids)
        self.objects[assignment] = thickened
        return thickened

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
            {
                "tx_dd": cast(GroupGeometryParams, {}),
                "tx_vertical": cast(GroupGeometryParams, {}),
                "rx_dd": cast(GroupGeometryParams, {}),
            },
        ),
        tx_board_ids={pcb["id"] for pcb in selected_pcbs if pcb["role"] == "tx"},
        design_id="demo_tx_dd_external_owner",
        aedt_path=Path("/tmp/demo_tx_dd_external_owner.aedt"),
        metadata_path=Path("/tmp/demo_tx_dd_external_owner.json"),
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


def _tx_pcb(*, board_id: str, z: float, selector_indices: list[int]) -> ResolvedPcbInstance:
    return cast(
        ResolvedPcbInstance,
        {
            "id": board_id,
            "role": "tx",
            "position": (0.0, 0.0, z),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": selector_index}
                for selector_index in selector_indices
            ],
        },
    )


def _build_tx_dd_finalize_inputs(
    *,
    pcbs: list[ResolvedPcbInstance],
    layer_count: int,
    turns: int,
    trace: float = 1.0,
    gap: float = 1.0,
) -> FinalizeInputs:
    ctx = _ctx_base(selected_pcbs=pcbs)
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_dd", "layer_count": layer_count, "spacing_mm": 0.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {
            "kind": "tx_dd",
            "turn_count": turns,
            "band_ratio": 0.2,
            "metal_ratio": 0.5,
            "trace": trace,
            "gap": gap,
        },
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
    return finalize_inputs


def _stub_source_from_landing(landing: DirectedLandingSection, *, trace: float) -> _TxDdStartStubSource:
    inward_dir = landing.get("inward_dir")
    if inward_dir is None:
        return (landing["center"], trace, landing["object_name"])
    return (landing["center"], trace, landing["object_name"], inward_dir)


def _assert_external_sources_match_feed_bindings(
    *,
    finalize_inputs: FinalizeInputs,
    board_id: str,
    trace: float,
) -> list[_TxDdStartStubSource]:
    feed_in = finalize_inputs.tx_series_binding.feed_in
    feed_out = finalize_inputs.tx_series_binding.feed_out
    inter_half_exit = finalize_inputs.tx_series_binding.inter_half_exit
    inter_half_entry = finalize_inputs.tx_series_binding.inter_half_entry
    assert feed_in is not None
    assert feed_out is not None
    assert inter_half_exit is not None
    assert inter_half_entry is not None
    assert feed_in["terminal_role"] == "feed_in"
    assert feed_out["terminal_role"] == "feed_out"
    assert inter_half_exit["terminal_role"] == "inter_half_exit"
    assert inter_half_entry["terminal_role"] in {"inter_half_entry", "feed_in"}

    start_stub_sources = finalize_inputs.txdd_start_stub_sources[board_id]
    source_object_names = {source[2] for source in start_stub_sources}
    expected_object_names = {
        landing["object_name"]
        for landing in (feed_in, feed_out)
        if landing["object_name"] in source_object_names
    }
    assert expected_object_names.issubset(source_object_names)
    if _stub_source_from_landing(inter_half_exit, trace=trace) != _stub_source_from_landing(feed_out, trace=trace):
        assert _stub_source_from_landing(inter_half_exit, trace=trace) not in start_stub_sources
    if _stub_source_from_landing(inter_half_entry, trace=trace) != _stub_source_from_landing(feed_in, trace=trace):
        assert _stub_source_from_landing(inter_half_entry, trace=trace) not in start_stub_sources
    return start_stub_sources


def test_tx_dd_external_sources_ignore_free_terminal_topology_values(monkeypatch: pytest.MonkeyPatch) -> None:
    original_half_topology = group_builder_tx_dd_module._txdd_half_topology
    wrong_right_anchor: _Point3 = (901.0, 902.0, 903.0)

    def _half_topology_with_wrong_free_terminal(
        *,
        half_side: Literal["right"],
        turns: int,
        outer_x: float,
        outer_y: float,
        trace: float,
        gap: float,
        layer_count: int | None = None,
        instance_count: int | None = None,
        layer_index: int | None,
        corner_mode: int = 0,
    ) -> _TxDdRightLocalTopology:
        topology = original_half_topology(
            half_side=half_side,
            turns=turns,
            outer_x=outer_x,
            outer_y=outer_y,
            trace=trace,
            gap=gap,
            layer_count=layer_count,
            instance_count=instance_count,
            layer_index=layer_index,
            corner_mode=corner_mode,
        )
        return replace(topology, free_terminal_anchor_local=wrong_right_anchor)

    monkeypatch.setattr(group_builder_tx_dd_module, "_txdd_half_topology", _half_topology_with_wrong_free_terminal)

    finalize_inputs = _build_tx_dd_finalize_inputs(
        pcbs=[_tx_pcb(board_id="tx_main_0", z=0.0, selector_indices=[0, 1])],
        layer_count=1,
        turns=1,
    )

    start_stub_sources = _assert_external_sources_match_feed_bindings(
        finalize_inputs=finalize_inputs,
        board_id="tx_main_0",
        trace=1.0,
    )
    assert {source[0] for source in start_stub_sources}.isdisjoint({wrong_right_anchor})


def test_tx_dd_stacked_external_sources_exclude_series_and_a_link_owners() -> None:
    finalize_inputs = _build_tx_dd_finalize_inputs(
        pcbs=[
            _tx_pcb(board_id="tx_main_0", z=0.0, selector_indices=[0, 1]),
            _tx_pcb(board_id="tx_main_1", z=4.0, selector_indices=[2, 3]),
        ],
        layer_count=2,
        turns=1,
    )

    assert len(finalize_inputs.txdd_start_stub_sources) == 2
    start_stub_sources_lower = _assert_external_sources_match_feed_bindings(
        finalize_inputs=finalize_inputs,
        board_id="tx_main_0",
        trace=1.0,
    )
    start_stub_sources_upper = _assert_external_sources_match_feed_bindings(
        finalize_inputs=finalize_inputs,
        board_id="tx_main_1",
        trace=1.0,
    )

    inter_half_exit = finalize_inputs.tx_series_binding.inter_half_exit
    inter_half_entry = finalize_inputs.tx_series_binding.inter_half_entry
    assert inter_half_exit is not None
    assert inter_half_entry is not None

    external_source_points = {source[0] for source in start_stub_sources_lower + start_stub_sources_upper}
    internal_series_points = {inter_half_exit["center"], inter_half_entry["center"]}
    assert external_source_points.isdisjoint(internal_series_points)

    a_link_points = {
        anchor_point
        for anchor_point, _ in list(finalize_inputs.txdd_right_a_points.values())
    }
    assert {source[0] for source in start_stub_sources_lower + start_stub_sources_upper}.isdisjoint(a_link_points)

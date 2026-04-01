from __future__ import annotations

from typing import cast

import pytest
from peetsfea.aedt import Modeler3D

from peetsfea.backend.pyaedt.geometry.build import (
    _edge_points_at_tx_vertical_opposite_terminal,
    _edge_points_at_tx_vertical_terminal,
    _tx_vertical_bridge_edges_from_node,
)
from peetsfea.backend.pyaedt.geometry.build_state import (
    DirectedLandingSection,
    FinalizeInputs,
    GeometryBuildState,
    GeometryRuntimeContext,
    TxVerticalLinkNode,
    state_is_set,
)
from peetsfea.backend.pyaedt.geometry.builders.group_builder_tx_vertical import build_for_board
from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance
from tests.backend_geometry_build.test_one_turn_geometry_build import _FakeModeler, _ctx_base


def _tx_vertical_geometry() -> GroupGeometryParams:
    return cast(
        GroupGeometryParams,
        {"kind": "tx_vertical", "turn_count": 1, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )


def _tx_vertical_group(*, selected_count: int) -> ResolvedCoilGroup:
    return cast(
        ResolvedCoilGroup,
        {
            "kind": "tx_vertical",
            "requested_count": max(selected_count, 1),
            "selected_count": selected_count,
            "spacing_mm": 0.0,
            "instance_transforms": [],
        },
    )


def _host_tx_vertical_pcb() -> ResolvedPcbInstance:
    return cast(
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


def _non_host_tx_pcb() -> ResolvedPcbInstance:
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
            "mounts": [{"kind": "tx_dd", "selector_mode": "index", "selector_index": 0}],
        },
    )


def _prime_tx_vertical_zx_scene(
    *,
    pcb: ResolvedPcbInstance,
) -> tuple[GeometryRuntimeContext, GeometryBuildState, FinalizeInputs]:
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.tx_vertical_region_min = (0.0, -10.0, 0.0)
    ctx.tx_vertical_region_max = (40.0, 10.0, 20.0)
    ctx.tx_vertical_center_x = 10.0
    ctx.tx_vertical_center_y = 0.0
    return ctx, GeometryBuildState(), FinalizeInputs()


def _bogus_landing(
    *,
    role: str,
    polarity: str,
    center: tuple[float, float, float],
) -> DirectedLandingSection:
    return cast(
        DirectedLandingSection,
        {
            "p_plus": center,
            "p_minus": center,
            "center": center,
            "outward_dir": (0.0, 0.0, 1.0),
            "plane_normal": (0.0, 1.0, 0.0),
            "object_name": "bogus_global_outer",
            "dd_family": "none",
            "dd_pair_index": None,
            "side": "center",
            "terminal_polarity": polarity,
            "terminal_role": role,
        },
    )


def _stray_node() -> TxVerticalLinkNode:
    return cast(
        TxVerticalLinkNode,
        (
            99,
            "stray_vertical_obj",
            (1.0, 0.0, 9.0),
            (3.0, 0.0, 2.0),
            0.0,
            1.0,
            2.0,
            ((3.0, 0.0, 2.5), (3.0, 0.0, 1.5)),
            ((1.0, 0.0, 9.5), (1.0, 0.0, 8.5)),
        ),
    )


def _edge_midpoint(edge: tuple[tuple[float, float, float], tuple[float, float, float]]) -> tuple[float, float, float]:
    return (
        (edge[0][0] + edge[1][0]) / 2.0,
        (edge[0][1] + edge[1][1]) / 2.0,
        (edge[0][2] + edge[1][2]) / 2.0,
    )


def test_zx_host_board_populates_series_from_host_link_nodes_only() -> None:
    pcb = _host_tx_vertical_pcb()
    ctx, state, finalize_inputs = _prime_tx_vertical_zx_scene(pcb=pcb)
    finalize_inputs.tx_vertical_global_outer_right_landing = _bogus_landing(
        role="none",
        polarity="neutral",
        center=(400.0, 400.0, 400.0),
    )
    finalize_inputs.tx_vertical_global_outer_left_landing = _bogus_landing(
        role="none",
        polarity="neutral",
        center=(-400.0, -400.0, -400.0),
    )
    modeler = _FakeModeler()

    build_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=_tx_vertical_group(selected_count=1),
        geometry=_tx_vertical_geometry(),
        edge_points_at_tx_vertical_terminal=_edge_points_at_tx_vertical_terminal,
        edge_points_at_tx_vertical_opposite_terminal=_edge_points_at_tx_vertical_opposite_terminal,
        tx_vertical_bridge_edges_from_node=_tx_vertical_bridge_edges_from_node,
    )

    board_nodes = finalize_inputs.tx_vertical_nodes_by_board[("tx_vertical_0", 0)]
    assert len(board_nodes) == 1
    assert state_is_set(finalize_inputs.tx_series_binding.series_entry)
    assert state_is_set(finalize_inputs.tx_series_binding.series_exit)
    assert finalize_inputs.tx_series_binding.series_entry["object_name"] == board_nodes[0][1]
    assert finalize_inputs.tx_series_binding.series_exit["object_name"] == board_nodes[0][1]
    assert finalize_inputs.tx_series_binding.series_entry["center"] == pytest.approx(_edge_midpoint(board_nodes[0][8]))
    assert finalize_inputs.tx_series_binding.series_exit["center"] == pytest.approx(_edge_midpoint(board_nodes[0][7]))
    assert finalize_inputs.tx_series_binding.series_entry["terminal_role"] == "series_entry"
    assert finalize_inputs.tx_series_binding.series_exit["terminal_role"] == "series_exit"
    assert finalize_inputs.tx_series_binding.series_entry["terminal_polarity"] == "positive"
    assert finalize_inputs.tx_series_binding.series_exit["terminal_polarity"] == "negative"
    assert finalize_inputs.tx_series_binding.series_entry["center"] != pytest.approx((400.0, 400.0, 400.0))
    assert finalize_inputs.tx_series_binding.series_exit["center"] != pytest.approx((-400.0, -400.0, -400.0))


def test_zx_non_host_board_skips_series_capture_even_with_stray_nodes() -> None:
    pcb = _non_host_tx_pcb()
    ctx, state, finalize_inputs = _prime_tx_vertical_zx_scene(pcb=pcb)
    finalize_inputs.tx_vertical_nodes_by_board[("tx_main_0", 0)] = [_stray_node()]
    modeler = _FakeModeler()

    build_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=_tx_vertical_group(selected_count=1),
        geometry=_tx_vertical_geometry(),
        edge_points_at_tx_vertical_terminal=_edge_points_at_tx_vertical_terminal,
        edge_points_at_tx_vertical_opposite_terminal=_edge_points_at_tx_vertical_opposite_terminal,
        tx_vertical_bridge_edges_from_node=_tx_vertical_bridge_edges_from_node,
    )

    assert not state.group_objects["tx_vertical"]
    assert finalize_inputs.tx_vertical_nodes_by_board[("tx_main_0", 0)] == [_stray_node()]
    assert not state_is_set(finalize_inputs.tx_series_binding.series_entry)
    assert not state_is_set(finalize_inputs.tx_series_binding.series_exit)


def test_zx_host_board_with_mount_but_no_nodes_hard_fails() -> None:
    pcb = _host_tx_vertical_pcb()
    ctx, state, finalize_inputs = _prime_tx_vertical_zx_scene(pcb=pcb)
    modeler = _FakeModeler()

    with pytest.raises(ValueError, match="mounted tx_vertical board captured no linked nodes"):
        build_for_board(
            modeler=cast(Modeler3D, modeler),
            ctx=ctx,
            state=state,
            finalize_inputs=finalize_inputs,
            board_idx=0,
            pcb=pcb,
            group=_tx_vertical_group(selected_count=0),
            geometry=_tx_vertical_geometry(),
            edge_points_at_tx_vertical_terminal=_edge_points_at_tx_vertical_terminal,
            edge_points_at_tx_vertical_opposite_terminal=_edge_points_at_tx_vertical_opposite_terminal,
            tx_vertical_bridge_edges_from_node=_tx_vertical_bridge_edges_from_node,
        )

    assert not state_is_set(finalize_inputs.tx_series_binding.series_entry)
    assert not state_is_set(finalize_inputs.tx_series_binding.series_exit)

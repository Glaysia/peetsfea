from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

import pytest
from peetsfea.aedt import Hfss, Modeler3D

import peetsfea.backend.pyaedt.geometry.build as geometry_build_module
from peetsfea.backend.pyaedt.geometry.build import _build_all_coils, _build_tx_ferrite, _finalize_geometry
from peetsfea.backend.pyaedt.geometry.build_state import (
    DirectedLandingSection,
    FinalizeInputs,
    GeometryBuildState,
    GeometryRuntimeContext,
    NO_DD_PAIR_INDEX,
)
from peetsfea.types.manifest import (
    EmPortAssignments,
    EmPorts,
    GroupGeometryParams,
    Manifest,
    ResolvedCoilGroup,
    ResolvedPcbInstance,
    SelectedParameters,
    SelectedParametersMax,
)


def _tx_runtime_pcb() -> ResolvedPcbInstance:
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
                {"kind": "tx_vertical", "selector_mode": "all", "selector_index": None},
            ],
        },
    )


def _group(kind: Literal["tx_dd", "tx_vertical", "rx_dd"]) -> ResolvedCoilGroup:
    if kind == "tx_dd":
        return cast(
            ResolvedCoilGroup,
            {
                "kind": "tx_dd",
                "layer_count": 1,
                "spacing_mm": 0.0,
                "instance_transforms": [{"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0}],
            },
        )
    return cast(
        ResolvedCoilGroup,
        {
            "kind": kind,
            "requested_count": 1,
            "selected_count": 1,
            "spacing_mm": 0.0,
            "instance_transforms": [],
        },
    )


def _geometry(kind: Literal["tx_dd", "tx_vertical", "rx_dd"]) -> GroupGeometryParams:
    return cast(
        GroupGeometryParams,
        {
            "kind": kind,
            "turn_count": 1,
            "band_ratio": 0.2,
            "metal_ratio": 0.5,
            "trace": 1.0,
            "gap": 1.0,
        },
    )


def _series_terminal(
    *,
    center: tuple[float, float, float],
    role: str,
    polarity: str,
    side: str,
    object_name: str,
) -> DirectedLandingSection:
    return cast(
        DirectedLandingSection,
        {
            "p_plus": center,
            "p_minus": center,
            "center": center,
            "outward_dir": (1.0, 0.0, 0.0),
            "plane_normal": (0.0, -1.0, 0.0),
            "object_name": object_name,
            "dd_family": "none",
            "dd_pair_index": NO_DD_PAIR_INDEX,
            "side": side,
            "terminal_polarity": polarity,
            "terminal_role": role,
        },
    )


def _ctx_base(*, selected_pcbs: list[ResolvedPcbInstance]) -> GeometryRuntimeContext:
    return GeometryRuntimeContext(
        manifest=cast(Manifest, {}),
        selected=cast(
            SelectedParameters,
            {
                "neo_tx_dd_right_terminal_path": "D_ccw_to_d",
                "neo_tx_dd_left_terminal_path": "a_cw_to_A",
                "neo_tx_vertical_zx_terminal_path": "B_ccw_to_c",
            },
        ),
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
        corner_mode=0,
        pcb_thickness=1.6,
        cu_thickness=0.035,
        tx_dd_top_clearance=0.1,
        tx_vertical_orientation_mode=1,
        rx_face_clearance=0.0,
        tx_vertical_plane="ZX",
    )


def _prime_tx_vertical_scene() -> tuple[GeometryRuntimeContext, GeometryBuildState, FinalizeInputs]:
    pcb = _tx_runtime_pcb()
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.selected_groups = [_group("tx_dd"), _group("tx_vertical")]
    ctx.group_geometry_by_kind = cast(
        dict[Literal["tx_dd", "tx_vertical", "rx_dd"], GroupGeometryParams],
        {
            "tx_dd": _geometry("tx_dd"),
            "tx_vertical": _geometry("tx_vertical"),
            "rx_dd": _geometry("rx_dd"),
        },
    )
    ctx.selected = cast(SelectedParameters, {"via_diameter_mm": 0.5})
    ctx.tx_vertical_region_min = (0.0, -10.0, 0.0)
    ctx.tx_vertical_region_max = (40.0, 10.0, 20.0)
    ctx.tx_vertical_center_x = 10.0
    ctx.tx_vertical_center_y = 0.0
    return ctx, GeometryBuildState(), FinalizeInputs()


def test_build_all_coils_calls_tx_dd_neo_builder_and_keeps_tx_vertical(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx, state, _finalize_inputs = _prime_tx_vertical_scene()
    calls: list[str] = []

    def _fake_tx_dd_for_board(**kwargs: object) -> None:
        _ = kwargs
        calls.append("tx_dd")

    def _fake_tx_vertical_for_board(**kwargs: object) -> None:
        _ = kwargs
        calls.append("tx_vertical")

    monkeypatch.setattr(geometry_build_module, "build_tx_dd_for_board", _fake_tx_dd_for_board)
    monkeypatch.setattr(geometry_build_module, "build_tx_vertical_for_board", _fake_tx_vertical_for_board)

    _build_all_coils(ctx, state, cast(Modeler3D, object()))

    assert calls == ["tx_dd", "tx_vertical"]


def test_finalize_geometry_allows_tx_vertical_only_series_path(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx, state, finalize_inputs = _prime_tx_vertical_scene()
    finalize_inputs.tx_series_binding.series_entry = _series_terminal(
        center=(5.0, 0.0, 10.0),
        role="series_entry",
        polarity="positive",
        side="right",
        object_name="coil_tx_vertical_demo",
    )
    finalize_inputs.tx_series_binding.series_exit = _series_terminal(
        center=(15.0, 0.0, 10.0),
        role="series_exit",
        polarity="negative",
        side="left",
        object_name="coil_tx_vertical_demo",
    )

    finalize_called = {"value": False}

    def _fake_finalize_solids_and_substrates(**kwargs: object) -> tuple[list[str], list[str], EmPorts, EmPortAssignments]:
        _ = kwargs
        finalize_called["value"] = True
        return (
            [],
            [],
            cast(EmPorts, {"tx": [], "rx": []}),
            cast(EmPortAssignments, {"tx": [], "rx": []}),
        )

    monkeypatch.setattr(geometry_build_module, "finalize_solids_and_substrates", _fake_finalize_solids_and_substrates)

    _finalize_geometry(
        ctx,
        state,
        finalize_inputs,
        cast(Modeler3D, object()),
        cast(Hfss, object()),
    )

    assert finalize_called["value"] is True


def test_finalize_geometry_still_requires_feed_terminals_when_tx_dd_capture_exists() -> None:
    ctx, state, finalize_inputs = _prime_tx_vertical_scene()
    finalize_inputs.txdd_right_object_names[0] = "coil_txdd_demo"

    with pytest.raises(AssertionError, match="feed_in"):
        _finalize_geometry(
            ctx,
            state,
            finalize_inputs,
            cast(Modeler3D, object()),
            cast(Hfss, object()),
        )


def test_build_tx_ferrite_enables_tx_ferrite_when_tx_dd_runtime_is_on(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx, state, _finalize_inputs = _prime_tx_vertical_scene()
    captured: dict[str, bool] = {}

    def _fake_create_tx_ferrite_model_objects(**kwargs: object) -> tuple[list[str], list[object], list[object]]:
        assert "enable_tx_ferrite" in kwargs
        raw_enable_tx_ferrite = kwargs["enable_tx_ferrite"]
        assert isinstance(raw_enable_tx_ferrite, bool)
        captured["enable_tx_ferrite"] = raw_enable_tx_ferrite
        return ([], [], [])

    monkeypatch.setattr(geometry_build_module, "_create_tx_ferrite_model_objects", _fake_create_tx_ferrite_model_objects)

    _build_tx_ferrite(
        ctx,
        state,
        cast(Modeler3D, object()),
        cast(Hfss, object()),
    )

    assert "enable_tx_ferrite" in captured
    assert captured["enable_tx_ferrite"] is True

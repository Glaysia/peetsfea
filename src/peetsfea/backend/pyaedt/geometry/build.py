from __future__ import annotations

import json
import math
import os
import subprocess
from pathlib import Path
from typing import Literal, cast

from peetsfea.aedt import Hfss
from peetsfea.aedt import Modeler3D

from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput, EmPipelineResult
from peetsfea.backend.pyaedt.em_pipeline.runner import run_em_pipeline
from peetsfea.backend.pyaedt.failfast import raise_on_false
from peetsfea.console_log import info
from peetsfea.types.manifest import CadProbe, EmPolicy, GeometryMetadata, GroupGeometryParams, Manifest, OutputsSpec, SceneObjectEntry, TerminalLabel
from peetsfea.types.runtime_selection import ResolvedTxVerticalGroup

from .builders.build_artifacts import build_em_artifacts, finalize_solids_and_substrates
from .build_state import (
    DirectedLandingSection,
    Edge2P,
    FinalizeInputs,
    GeometryBuildState,
    GeometryRuntimeContext,
    Point3,
    require_rx_scene,
    require_tx_dd_scene,
    require_tx_vertical_scene,
    set_rx_scene,
    set_tx_dd_scene,
    set_tx_vertical_scene,
)
from .builders.build_tx_dd import extract_build_prelude, validate_build_prelude
from .builders.build_tx_vertical import create_hfss_session
from .builders.group_builder_rx_dd import build_for_board as build_rx_dd_for_board
from .builders.group_builder_tx_dd_neo import build_for_board as build_tx_dd_for_board
from .builders.group_builder_tx_vertical import build_for_board as build_tx_vertical_for_board
from .design_vars import _assign_design_variables
from .metadata import _build_geometry_metadata
from .rules.debug_checks import _build_geometry_debug
from .rules.scene_objects import (
    _bounds_from_scene_entry,
    _create_rx_ferrite_model_objects,
    _create_scene_non_model_objects,
    _create_tx_ferrite_model_objects,
)
from .rules.spiral_points import _build_rect_spiral_centerline_absolute
from peetsfea.backend.pyaedt.geometry import metadata


_RxDdBackStubSource = tuple[str, int, str, Point3, float, str] | tuple[str, int, str, Point3, float, str, Point3]
_TxSeriesFieldName = Literal[
    "feed_in",
    "feed_out",
    "inter_half_exit",
    "inter_half_entry",
    "series_entry",
    "series_exit",
]


def _tx_dd_runtime_enabled() -> bool:
    return True


def _emit_geometry_metadata_enabled(manifest: Manifest) -> bool:
    inputs = manifest["inputs"]
    assert "emit_geometry_metadata_json" in inputs, "manifest inputs are missing emit_geometry_metadata_json"
    raw = inputs["emit_geometry_metadata_json"]
    assert isinstance(raw, bool), "manifest inputs emit_geometry_metadata_json must be bool"
    return raw


def _write_geometry_metadata_if_enabled(manifest: Manifest, metadata: GeometryMetadata, metadata_path: Path) -> None:
    if not _emit_geometry_metadata_enabled(manifest):
        return
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def _require_tx_series_landing(
    finalize_inputs: FinalizeInputs,
    field_name: _TxSeriesFieldName,
) -> DirectedLandingSection:
    return finalize_inputs.tx_series_binding.require(field_name)


def _validate_tx_series_binding_contract(finalize_inputs: FinalizeInputs) -> None:
    field_roles: dict[_TxSeriesFieldName, _TxSeriesFieldName] = {
        "feed_in": "feed_in",
        "feed_out": "feed_out",
    }
    for field_name, expected_role in field_roles.items():
        landing = _require_tx_series_landing(finalize_inputs, field_name)
        actual_role = landing["terminal_role"]
        if actual_role != expected_role:
            raise ValueError(
                "tx series binding contract violation: terminal role mismatch "
                f"(field={field_name}, expected={expected_role}, actual={actual_role})"
            )
    binding = finalize_inputs.tx_series_binding
    feed_in = binding.require("feed_in")
    feed_out = binding.require("feed_out")
    if feed_in["terminal_polarity"] == feed_out["terminal_polarity"]:
        raise ValueError(
            "tx series binding contract violation: external feed terminals must use opposite polarity "
            f"(feed_in={feed_in['terminal_polarity']}, feed_out={feed_out['terminal_polarity']})"
        )


def _tx_dd_finalize_active(finalize_inputs: FinalizeInputs) -> bool:
    return (
        bool(finalize_inputs.txdd_right_object_names)
        or bool(finalize_inputs.txdd_right_a_points)
        or any(bool(sources) for sources in finalize_inputs.txdd_start_stub_sources.values())
        or finalize_inputs.tx_series_binding.has("feed_in")
        or finalize_inputs.tx_series_binding.has("feed_out")
        or finalize_inputs.tx_series_binding.has("inter_half_exit")
        or finalize_inputs.tx_series_binding.has("inter_half_entry")
    )


def _append_rxdd_back_stub_sources_if_needed(
    *,
    kind: str,
    board_id: str,
    instance_index: int,
    start_xyz: Point3,
    end_xyz: Point3,
    start_label: TerminalLabel,
    end_label: TerminalLabel,
    trace: float,
    source_object_name: str,
    storage: list[_RxDdBackStubSource],
    start_inward_dir: Point3,
    end_inward_dir: Point3,
) -> None:
    if kind != "rx_dd":
        return
    storage.append((board_id, instance_index, str(start_label), start_xyz, trace, source_object_name, start_inward_dir))
    storage.append((board_id, instance_index, str(end_label), end_xyz, trace, source_object_name, end_inward_dir))


def _edge_points_at_path_end(*, points: list[list[float]], trace: float) -> Edge2P:
    if len(points) < 2:
        raise ValueError("Cannot compute end edge from path with fewer than 2 points")
    prev = points[-2]
    end = points[-1]
    dx = end[0] - prev[0]
    dy = end[1] - prev[1]
    seg_len = math.hypot(dx, dy)
    if seg_len <= 1e-12:
        raise ValueError("Cannot compute end edge from zero-length final segment")
    nx = -dy / seg_len
    ny = dx / seg_len
    half_trace = trace / 2.0
    p0: Point3 = (end[0] + (nx * half_trace), end[1] + (ny * half_trace), end[2])
    p1: Point3 = (end[0] - (nx * half_trace), end[1] - (ny * half_trace), end[2])
    return p0, p1


def _edge_points_at_tx_vertical_terminal(
    *,
    points: list[list[float]],
    trace: float,
    cu_thickness: float,
) -> Edge2P:
    if len(points) < 2:
        raise ValueError("Cannot compute tx_vertical terminal edge from path with fewer than 2 points")
    start = points[0]
    end = points[-1]
    choose_start = (start[2] > end[2]) or (abs(start[2] - end[2]) <= 1e-12 and start[0] < end[0])
    if choose_start:
        terminal = start
        neighbor = points[1]
    else:
        terminal = end
        neighbor = points[-2]
    dx = terminal[0] - neighbor[0]
    dz = terminal[2] - neighbor[2]
    seg_len = math.hypot(dx, dz)
    if seg_len <= 1e-12:
        raise ValueError("Cannot compute tx_vertical terminal edge from zero-length terminal segment")
    nx = -dz / seg_len
    nz = dx / seg_len
    half_trace = trace / 2.0
    p0: Point3 = (terminal[0] + (nx * half_trace), terminal[1], terminal[2] + (nz * half_trace))
    p1: Point3 = (terminal[0] - (nx * half_trace), terminal[1], terminal[2] - (nz * half_trace))
    if cu_thickness <= 0.0:
        raise ValueError(f"tx_vertical ZX terminal edge cu_thickness must be > 0 (actual={cu_thickness})")
    half_cu = cu_thickness / 2.0
    p0 = (p0[0], p0[1] - half_cu, p0[2])
    p1 = (p1[0], p1[1] - half_cu, p1[2])
    return p0, p1


def _edge_points_at_tx_vertical_opposite_terminal(
    *,
    points: list[list[float]],
    trace: float,
    cu_thickness: float,
) -> Edge2P:
    if len(points) < 2:
        raise ValueError("Cannot compute tx_vertical opposite terminal edge from path with fewer than 2 points")
    start = points[0]
    end = points[-1]
    choose_start = (start[2] > end[2]) or (abs(start[2] - end[2]) <= 1e-12 and start[0] < end[0])
    if choose_start:
        terminal = end
        neighbor = points[-2]
    else:
        terminal = start
        neighbor = points[1]
    dx = terminal[0] - neighbor[0]
    dz = terminal[2] - neighbor[2]
    seg_len = math.hypot(dx, dz)
    if seg_len <= 1e-12:
        raise ValueError("Cannot compute tx_vertical opposite terminal edge from zero-length terminal segment")
    nx = -dz / seg_len
    nz = dx / seg_len
    half_trace = trace / 2.0
    p0: Point3 = (terminal[0] + (nx * half_trace), terminal[1], terminal[2] + (nz * half_trace))
    p1: Point3 = (terminal[0] - (nx * half_trace), terminal[1], terminal[2] - (nz * half_trace))
    if cu_thickness <= 0.0:
        raise ValueError(f"tx_vertical ZX opposite terminal edge cu_thickness must be > 0 (actual={cu_thickness})")
    half_cu = cu_thickness / 2.0
    p0 = (p0[0], p0[1] - half_cu, p0[2])
    p1 = (p1[0], p1[1] - half_cu, p1[2])
    return p0, p1


def _tx_vertical_bridge_edges_from_node(
    *,
    start_xyz: Point3,
    end_xyz: Point3,
    trace: float,
    tx_vertical_region_min: Point3,
    tx_vertical_region_max: Point3,
    points: list[list[float]],
    cu_thickness: float,
) -> tuple[Edge2P, Edge2P]:
    if len(points) < 2:
        raise ValueError("tx_vertical ZX bridge edge resolution requires at least 2 source points")
    _ = start_xyz, end_xyz, tx_vertical_region_min, tx_vertical_region_max
    return (
        _edge_points_at_tx_vertical_terminal(points=points, trace=trace, cu_thickness=cu_thickness),
        _edge_points_at_tx_vertical_opposite_terminal(
            points=points,
            trace=trace,
            cu_thickness=cu_thickness,
        ),
    )


def _prepare_runtime(manifest: Manifest) -> GeometryRuntimeContext:
    manifest["repro_mode"] = "manifest_json"
    selected = manifest["selected_parameters"]
    prelude = extract_build_prelude(manifest)
    validate_build_prelude(prelude)

    run_dir = Path(manifest["inputs"]["ansys_run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)
    design_id = manifest["design_id"]
    aedt_path = run_dir / f"{design_id}.aedt"
    metadata_path = run_dir / f"geometry_metadata_{design_id}.json"

    selected_group_geometry = manifest["selected_group_geometry"]
    group_geometry_by_kind: dict[Literal["tx_dd", "tx_vertical", "rx_dd"], GroupGeometryParams] = {
        entry["kind"]: entry for entry in selected_group_geometry
    }
    missing_geometry = [kind for kind in ("tx_dd", "tx_vertical", "rx_dd") if kind not in group_geometry_by_kind]
    if missing_geometry:
        raise ValueError(f"Missing selected_group_geometry entries: {', '.join(missing_geometry)}")

    selected_pcbs = manifest["selected_pcbs"]
    tx_board_ids: set[str] = {pcb["id"] for pcb in selected_pcbs if pcb["role"] == "tx"}

    return GeometryRuntimeContext(
        manifest=manifest,
        selected=selected,
        selected_max=manifest["selected_parameters_max"],
        selected_groups=manifest["selected_coil_groups"],
        selected_group_geometry=selected_group_geometry,
        selected_pcbs=selected_pcbs,
        group_geometry_by_kind=group_geometry_by_kind,
        tx_board_ids=tx_board_ids,
        design_id=design_id,
        aedt_path=aedt_path,
        metadata_path=metadata_path,
        close_on_exit=manifest["inputs"]["close_on_exit"],
        tx_dd_outer_x=prelude["tx_dd_outer_x"],
        tx_dd_outer_y=prelude["tx_dd_outer_y"],
        tx_vertical_outer_x=prelude["tx_vertical_outer_x"],
        tx_vertical_outer_y=prelude["tx_vertical_outer_y"],
        rx_dd_outer_x=prelude["rx_dd_outer_x"],
        rx_dd_outer_y=prelude["rx_dd_outer_y"],
        corner_mode=cast(Literal[0, 1], prelude["corner_mode"]),
        pcb_thickness=prelude["pcb_thickness"],
        cu_thickness=prelude["cu_thickness"],
        tx_dd_top_clearance=prelude["tx_dd_top_clearance"],
        tx_vertical_orientation_mode=cast(Literal[0, 1], prelude["tx_vertical_orientation_mode"]),
        rx_face_clearance=prelude["rx_face_clearance"],
        tx_vertical_plane=cast(Literal["ZX"], prelude["tx_vertical_plane"]),
    )


def _build_scene(ctx: GeometryRuntimeContext, state: GeometryBuildState, modeler: Modeler3D) -> None:
    scene_names, scene_probes, state.scene_objects = _create_scene_non_model_objects(
        modeler=modeler,
        design_id=ctx.design_id,
        selected=ctx.selected,
        selected_max=ctx.selected_max,
    )
    state.object_names.extend(scene_names)
    state.cad_probe.extend(scene_probes)

    scene_by_kind: dict[str, SceneObjectEntry] = {entry["kind"]: entry for entry in state.scene_objects}
    assert "tx_region_dd" in scene_by_kind, "scene objects are missing tx_region_dd"
    assert "tx_region_vertical" in scene_by_kind, "scene objects are missing tx_region_vertical"
    assert "rx_region_actual" in scene_by_kind, "scene objects are missing rx_region_actual"
    tx_dd_region_min, tx_dd_region_max = _bounds_from_scene_entry(scene_by_kind["tx_region_dd"])
    tx_vertical_region_min, tx_vertical_region_max = _bounds_from_scene_entry(scene_by_kind["tx_region_vertical"])
    rx_region_min, rx_region_max = _bounds_from_scene_entry(scene_by_kind["rx_region_actual"])

    set_tx_dd_scene(
        ctx,
        region_min=tx_dd_region_min,
        region_max=tx_dd_region_max,
        center_x=tx_dd_region_min[0] + (ctx.tx_dd_outer_x / 2.0),
        center_y=(tx_dd_region_min[1] + tx_dd_region_max[1]) / 2.0,
    )
    set_tx_vertical_scene(
        ctx,
        region_min=tx_vertical_region_min,
        region_max=tx_vertical_region_max,
        center_x=tx_vertical_region_min[0] + (ctx.tx_vertical_outer_x / 2.0),
        center_y=(tx_vertical_region_min[1] + tx_vertical_region_max[1]) / 2.0,
    )
    set_rx_scene(
        ctx,
        region_min=rx_region_min,
        region_max=rx_region_max,
        center_y=(rx_region_min[1] + rx_region_max[1]) / 2.0,
    )


def _append_ferrite_results(
    state: GeometryBuildState,
    *,
    ferrite_names: list[str],
    ferrite_probes: list[CadProbe],
    ferrite_entries: list[SceneObjectEntry],
) -> None:
    state.object_names.extend(ferrite_names)
    state.cad_probe.extend(ferrite_probes)
    state.scene_objects.extend(ferrite_entries)
    state.group_objects["ferrite"].extend(ferrite_names)


def _tx_ferrite_live_object_names(ctx: GeometryRuntimeContext, state: GeometryBuildState) -> list[str]:
    tx_fr4_names = [
        name
        for name in state.fr4_object_names
        if any(name.startswith(f"fr4_{board_id}_") or name.startswith(f"neo_fr4_tx_dd_{board_id}_") for board_id in ctx.tx_board_ids)
    ]
    return sorted(set(state.group_objects["tx_dd"] + state.group_objects["tx_vertical"] + tx_fr4_names))


def _rx_ferrite_live_object_names(ctx: GeometryRuntimeContext, state: GeometryBuildState) -> list[str]:
    rx_fr4_names = [
        name
        for name in state.fr4_object_names
        if name.startswith("fr4_rx_shared_")
        or (name.startswith("fr4_") and not any(name.startswith(f"fr4_{board_id}_") for board_id in ctx.tx_board_ids))
    ]
    return sorted(set(state.group_objects["rx_dd"] + rx_fr4_names))


def _build_tx_ferrite(ctx: GeometryRuntimeContext, state: GeometryBuildState, modeler: Modeler3D, hfss: Hfss) -> None:
    ferrite_names, ferrite_probes, ferrite_entries = _create_tx_ferrite_model_objects(
        modeler=modeler,
        hfss=hfss,
        design_id=ctx.design_id,
        selected=ctx.selected,
        cad_probe=state.cad_probe,
        tx_board_ids=ctx.tx_board_ids,
        live_object_names=_tx_ferrite_live_object_names(ctx, state),
        enable_tx_ferrite=_tx_dd_runtime_enabled(),
    )
    _append_ferrite_results(
        state,
        ferrite_names=ferrite_names,
        ferrite_probes=ferrite_probes,
        ferrite_entries=ferrite_entries,
    )


def _build_rx_ferrite(ctx: GeometryRuntimeContext, state: GeometryBuildState, modeler: Modeler3D, hfss: Hfss) -> None:
    ferrite_names, ferrite_probes, ferrite_entries = _create_rx_ferrite_model_objects(
        modeler=modeler,
        hfss=hfss,
        design_id=ctx.design_id,
        selected=ctx.selected,
        scene_objects=state.scene_objects,
        coil_plane_bboxes=state.coil_plane_bboxes,
        tx_board_ids=ctx.tx_board_ids,
        live_object_names=_rx_ferrite_live_object_names(ctx, state),
    )
    _append_ferrite_results(
        state,
        ferrite_names=ferrite_names,
        ferrite_probes=ferrite_probes,
        ferrite_entries=ferrite_entries,
    )


def _build_all_coils(ctx: GeometryRuntimeContext, state: GeometryBuildState, modeler: Modeler3D) -> FinalizeInputs:
    finalize_inputs = FinalizeInputs()
    for board_idx, pcb in enumerate(ctx.selected_pcbs):
        if not pcb["present"]:
            continue
        for group in ctx.selected_groups:
            kind = group["kind"]
            if kind == "tx_vertical":
                group_tx_vertical = cast(ResolvedTxVerticalGroup, group)
                if int(group_tx_vertical["selected_count"]) == 0:
                    continue
                if int(group_tx_vertical["selected_count"]) < 1:
                    raise ValueError("tx_vertical selected_count must be >= 1")
            geometry = ctx.group_geometry_by_kind[kind]
            if kind == "tx_dd":
                build_tx_dd_for_board(
                    modeler=modeler,
                    ctx=ctx,
                    state=state,
                    finalize_inputs=finalize_inputs,
                    board_idx=board_idx,
                    pcb=pcb,
                    group=group,
                    geometry=geometry,
                    edge_points_at_path_end=_edge_points_at_path_end,
                )
            elif kind == "tx_vertical":
                build_tx_vertical_for_board(
                    modeler=modeler,
                    ctx=ctx,
                    state=state,
                    finalize_inputs=finalize_inputs,
                    board_idx=board_idx,
                    pcb=pcb,
                    group=group,
                    geometry=geometry,
                    edge_points_at_tx_vertical_terminal=_edge_points_at_tx_vertical_terminal,
                    edge_points_at_tx_vertical_opposite_terminal=_edge_points_at_tx_vertical_opposite_terminal,
                    tx_vertical_bridge_edges_from_node=_tx_vertical_bridge_edges_from_node,
                )
            else:
                build_rx_dd_for_board(
                    modeler=modeler,
                    ctx=ctx,
                    state=state,
                    finalize_inputs=finalize_inputs,
                    board_idx=board_idx,
                    pcb=pcb,
                    group=group,
                    geometry=geometry,
                    append_rxdd_back_stub_sources_if_needed=_append_rxdd_back_stub_sources_if_needed,
                )
    return finalize_inputs


def _finalize_geometry(
    ctx: GeometryRuntimeContext,
    state: GeometryBuildState,
    finalize_inputs: FinalizeInputs,
    modeler: Modeler3D,
    hfss: Hfss,
) -> None:
    tx_vertical_scene = require_tx_vertical_scene(ctx)
    tx_vertical_region_min = tx_vertical_scene["region_min"]
    tx_vertical_region_max = tx_vertical_scene["region_max"]
    tx_dd_scene = require_tx_dd_scene(ctx)
    if _tx_dd_finalize_active(finalize_inputs):
        _validate_tx_series_binding_contract(finalize_inputs)

    (
        object_names,
        fr4_object_names,
        em_ports,
        em_port_assignments,
        tx_dd_rotation_angle_deg,
        tx_dd_rotation_pivot_xyz,
        tx_dd_rotation_object_names,
    ) = finalize_solids_and_substrates(
        modeler=modeler,
        hfss=hfss,
        aedt_path=ctx.aedt_path,
        design_id=ctx.design_id,
        cu_thickness=ctx.cu_thickness,
        pcb_thickness=ctx.pcb_thickness,
        via_diameter_mm=float(ctx.selected["via_diameter_mm"]),
        tx_vertical_orientation_mode=ctx.tx_vertical_orientation_mode,
        tx_board_ids=ctx.tx_board_ids,
        tx_dd_region_min=tx_dd_scene["region_min"],
        tx_dd_region_max=tx_dd_scene["region_max"],
        tx_dd_center_y=tx_dd_scene["center_y"],
        tx_vertical_nodes_by_board=finalize_inputs.tx_vertical_nodes_by_board,
        tx_vertical_region_min=tx_vertical_region_min,
        tx_vertical_region_max=tx_vertical_region_max,
        txdd_right_a_points=finalize_inputs.txdd_right_a_points,
        txdd_right_object_names=finalize_inputs.txdd_right_object_names,
        txdd_start_stub_sources=finalize_inputs.txdd_start_stub_sources,
        rxdd_back_stub_sources=finalize_inputs.rxdd_back_stub_sources,
        group_objects=state.group_objects,
        object_names=state.object_names,
        cad_probe=state.cad_probe,
        placement_violations=state.placement_violations,
        coil_plane_bboxes=state.coil_plane_bboxes,
        fr4_object_names=state.fr4_object_names,
        tx_vertical_fr4_names=state.tx_vertical_fr4_names,
        coil_polarity=state.coil_polarity,
        dd_half_geometries=state.dd_half_geometries,
        txdd_global_right_bridge_landing=finalize_inputs.txdd_global_right_bridge_landing,
        txdd_global_right_bridge_edge=finalize_inputs.txdd_global_right_bridge_edge,
        txdd_global_right_bridge_section=finalize_inputs.txdd_global_right_bridge_section,
        txdd_global_right_bridge_anchor=finalize_inputs.txdd_global_right_bridge_anchor,
        txdd_global_right_bridge_object_name=finalize_inputs.txdd_global_right_bridge_object_name,
        txdd_global_right_d_edge=finalize_inputs.txdd_global_right_d_edge,
        txdd_global_right_d_object_name=finalize_inputs.txdd_global_right_d_object_name,
        tx_vertical_global_outer_right_edge=finalize_inputs.tx_vertical_global_outer_right_edge,
        tx_vertical_global_outer_left_edge=finalize_inputs.tx_vertical_global_outer_left_edge,
        tx_vertical_global_outer_right_landing=finalize_inputs.tx_vertical_global_outer_right_landing,
        tx_vertical_global_outer_left_landing=finalize_inputs.tx_vertical_global_outer_left_landing,
        tx_vertical_global_outer_right_section=finalize_inputs.tx_vertical_global_outer_right_section,
        tx_vertical_global_outer_left_section=finalize_inputs.tx_vertical_global_outer_left_section,
        tx_vertical_global_outer_right_anchor=finalize_inputs.tx_vertical_global_outer_right_anchor,
        tx_vertical_global_outer_left_anchor=finalize_inputs.tx_vertical_global_outer_left_anchor,
        tx_series_binding=finalize_inputs.tx_series_binding,
    )
    state.object_names = object_names
    state.fr4_object_names = fr4_object_names
    state.em_ports = em_ports
    state.em_port_assignments = em_port_assignments
    state.tx_dd_rotation_angle_deg = tx_dd_rotation_angle_deg
    state.tx_dd_rotation_pivot_xyz = tx_dd_rotation_pivot_xyz
    state.tx_dd_rotation_object_names = tx_dd_rotation_object_names


def _create_major_device_groups(modeler: Modeler3D, state: GeometryBuildState) -> None:
    tx_objects = sorted(set(state.group_objects["tx_dd"] + state.group_objects["tx_vertical"]))
    rx_objects = sorted(set(state.group_objects["rx_dd"]))
    fr4_objects = sorted(set(state.fr4_object_names))
    group_specs = (
        ("Tx", tx_objects),
        ("Rx", rx_objects),
        ("Ferrite", sorted(set(state.group_objects["ferrite"]))),
        ("Fr4", fr4_objects),
    )
    for group_name, object_names in group_specs:
        if not object_names:
            continue
        created_group_name = modeler.create_group(objects=object_names, group_name=group_name)
        if not created_group_name:
            raise ValueError(
                "Failed to create major device group "
                f"(group={group_name}, object_count={len(object_names)})"
            )


def _build_and_save_metadata(
    ctx: GeometryRuntimeContext,
    state: GeometryBuildState,
    manifest: Manifest,
    hfss: Hfss,
) -> GeometryMetadata:
    tx_dd_scene = require_tx_dd_scene(ctx)
    tx_dd_region_min = tx_dd_scene["region_min"]
    _ = tx_dd_region_min

    debug_geometry = ctx.group_geometry_by_kind["tx_dd"]
    debug_centerline_vertices = _build_rect_spiral_centerline_absolute(
        turns=debug_geometry["turn_count"],
        outer_x=ctx.tx_dd_outer_x,
        outer_y=ctx.tx_dd_outer_y,
        trace=debug_geometry["trace"],
        gap=debug_geometry["gap"],
        z=0.0,
        corner_mode=ctx.corner_mode,
    )
    debug = _build_geometry_debug(
        centerline_vertices=debug_centerline_vertices,
        trace=debug_geometry["trace"],
        gap=debug_geometry["gap"],
        eps=1e-6,
        cad_probe=state.cad_probe,
        in_region_ok=len(state.placement_violations) == 0,
        violations=state.placement_violations,
    )

    pitch_max_delta = max((entry["delta"] for entry in debug["pitch_checks"]), default=0.0)
    axis_aligned = all(check["is_vertical"] or check["is_horizontal"] for check in debug["axis_checks"])
    top_probe = cast(CadProbe, object())
    for probe in state.cad_probe:
        if probe["object_name"].startswith("coil_"):
            top_probe = probe
            break
    assert isinstance(top_probe, dict), "geometry debug contract violation: missing top coil CAD probe"
    top_bbox = top_probe["bbox"]
    info(f"[geometry] constraints_ok={debug['constraints_ok']}")
    info(f"[geometry] axis_aligned={axis_aligned} pitch_max_delta={pitch_max_delta:.9f}")
    info(f"[geometry] top_bbox={top_bbox}")

    modeler = cast(Modeler3D, hfss.modeler)
    _create_major_device_groups(modeler, state)
    em_ready_objects, em_endpoints, em_context = build_em_artifacts(
        selected=cast(dict[str, object], ctx.selected),
        object_names=state.object_names,
        group_objects=state.group_objects,
        group_endpoints=state.group_endpoints,
        scene_objects=state.scene_objects,
    )
    em_ready_objects["fr4_objects"] = sorted(state.fr4_object_names)
    em_policy: EmPolicy = manifest["spec"]["simulation"]
    em_input: EmPipelineInput = {
        "ready_objects": em_ready_objects,
        "endpoints": em_endpoints,
        "context": em_context,
        "ports": state.em_ports,
    }
    spec = manifest["spec"]
    assert "outputs" in spec, "manifest spec must include outputs before EM pipeline execution"
    outputs = cast(OutputsSpec, spec["outputs"])
    em_pipeline_result = run_em_pipeline(
        hfss=hfss,
        modeler=modeler,
        em_input=em_input,
        em_policy=em_policy,
        outputs=outputs,
    )
    info(f"[em] validation_ok={em_pipeline_result['validation_report']['ok']}")
    assert hfss.odesign.ValidateDesign(), "HFSS oDesign.ValidateDesign() failed after geometry build and EM pipeline execution"
    hfss.save_project(str(ctx.aedt_path))

    metadata = _build_geometry_metadata(
        manifest=manifest,
        aedt_path=ctx.aedt_path,
        object_names=state.object_names,
        metadata_path=ctx.metadata_path,
        group_objects=state.group_objects,
        unite_groups={
            "tx": sorted(set(state.group_objects["tx_dd"] + state.group_objects["tx_vertical"])),
            "rx": sorted(state.group_objects["rx_dd"]),
            "ferrite": sorted(state.group_objects["ferrite"]),
        },
        group_endpoints=state.group_endpoints,
        coil_polarity=state.coil_polarity,
        em_ready_objects=em_ready_objects,
        em_endpoints=em_endpoints,
        em_ports=state.em_ports,
        em_port_assignments=state.em_port_assignments,
        em_context=em_context,
        em_policy=em_policy,
        em_pipeline_result=em_pipeline_result,
        scene_objects=state.scene_objects,
        tx_dd_rotation_angle_deg=state.tx_dd_rotation_angle_deg,
        tx_dd_rotation_pivot_xyz=state.tx_dd_rotation_pivot_xyz,
        tx_dd_rotation_object_names=state.tx_dd_rotation_object_names,
        debug=debug,
    )
    _write_geometry_metadata_if_enabled(manifest, metadata, ctx.metadata_path)
    return metadata


def _close_hfss_desktop(hfss: Hfss, ctx: GeometryRuntimeContext) -> None:
    desktop = hfss.desktop_class
    assert hasattr(desktop, "aedt_process_id"), "HFSS desktop session is missing aedt_process_id"
    raw_aedt_pid = desktop.aedt_process_id
    assert isinstance(raw_aedt_pid, int), "HFSS desktop session aedt_process_id must be int"
    aedt_pid = raw_aedt_pid
    try:
        raise_on_false(
            desktop.release_desktop(
                close_projects=ctx.close_on_exit,
                close_on_exit=ctx.close_on_exit,
            ),
            operation="release_desktop",
            context={
                "design_id": ctx.design_id,
                "close_projects": ctx.close_on_exit,
                "close_on_exit": ctx.close_on_exit,
            },
        )
    except Exception:
        subprocess.run(["kill", "-9", str(aedt_pid)], check=False)
        raise

def build_square_spiral_from_manifest(manifest: Manifest) -> GeometryMetadata:
    ctx = _prepare_runtime(manifest)
    debug_mode = os.environ.get("PEETSFEA_DEBUG") == "1"
    hfss = create_hfss_session(manifest=manifest, aedt_path=ctx.aedt_path)
    
    _assign_design_variables(hfss, manifest)
    modeler = cast(Modeler3D, hfss.modeler)
    state = GeometryBuildState()
    if debug_mode:
        _build_scene(ctx, state, modeler)
        finalize_inputs = _build_all_coils(ctx, state, modeler)
        _build_tx_ferrite(ctx, state, modeler, hfss)
        _finalize_geometry(ctx, state, finalize_inputs, modeler, hfss)
        _build_rx_ferrite(ctx, state, modeler, hfss)
        metadata = _build_and_save_metadata(ctx, state, manifest, hfss)
        if metadata is False:
            raise RuntimeError(
                "build_square_spiral_from_manifest returned False "
                f"(design_id={ctx.design_id})"
            )
        _close_hfss_desktop(hfss, ctx)
        return metadata
    try:
        _build_scene(ctx, state, modeler)
        finalize_inputs = _build_all_coils(ctx, state, modeler)
        _build_tx_ferrite(ctx, state, modeler, hfss)
        _finalize_geometry(ctx, state, finalize_inputs, modeler, hfss)
        _build_rx_ferrite(ctx, state, modeler, hfss)
        metadata = _build_and_save_metadata(ctx, state, manifest, hfss)
        if metadata is False:
            raise RuntimeError(
                "build_square_spiral_from_manifest returned False "
                f"(design_id={ctx.design_id})"
            )
        return metadata
    finally:
        _close_hfss_desktop(hfss, ctx)

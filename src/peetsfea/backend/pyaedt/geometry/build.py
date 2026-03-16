from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Literal, cast

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.backend.pyaedt.em_pipeline import run_em_pipeline
from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput
from peetsfea.placement_math import tx_vertical_mode2_center_x_from_tx_dd_min
from peetsfea.types.manifest import EmPolicy, GeometryMetadata, GroupGeometryParams, Manifest, SceneObjectEntry, TerminalLabel

from .build_rx_dd import build_em_artifacts, finalize_solids_and_substrates
from .build_state import Edge2P, FinalizeInputs, GeometryBuildState, GeometryRuntimeContext, Point3
from .build_tx_dd import extract_build_prelude, validate_build_prelude
from .build_tx_vertical import create_hfss_session
from .debug_checks import _build_geometry_debug
from .design_vars import _assign_design_variables
from .group_builder_rx_dd import build_for_board as build_rx_dd_for_board
from .group_builder_tx_dd import build_for_board as build_tx_dd_for_board
from .group_builder_tx_vertical import build_for_board as build_tx_vertical_for_board
from .metadata import _build_geometry_metadata
from .placement_rules import _apply_txdd_right_endpoint_rule
from .scene_objects import _bounds_from_scene_entry, _create_ferrite_model_objects, _create_scene_non_model_objects
from .spiral_points import _build_rect_spiral_centerline_absolute


_RxDdBackStubSource = tuple[str, int, str, Point3, float, str]


def _emit_geometry_metadata_enabled(manifest: Manifest) -> bool:
    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict):
        return False
    raw = inputs.get("emit_geometry_metadata_json")
    return bool(raw) if isinstance(raw, bool) else False


def _write_geometry_metadata_if_enabled(manifest: Manifest, metadata: GeometryMetadata, metadata_path: Path) -> None:
    if not _emit_geometry_metadata_enabled(manifest):
        return
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


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
) -> None:
    if kind != "rx_dd":
        return
    storage.append((board_id, instance_index, str(start_label), start_xyz, trace, source_object_name))
    storage.append((board_id, instance_index, str(end_label), end_xyz, trace, source_object_name))


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


def _edge_points_at_yz_terminal(
    *,
    terminal_xyz: Point3,
    neighbor_xyz: Point3,
    trace: float,
) -> Edge2P:
    dy = terminal_xyz[1] - neighbor_xyz[1]
    dz = terminal_xyz[2] - neighbor_xyz[2]
    seg_len = math.hypot(dy, dz)
    if seg_len <= 1e-12:
        raise ValueError("Cannot compute tx_vertical YZ terminal edge from zero-length terminal segment")
    ny = -dz / seg_len
    nz = dy / seg_len
    half_trace = trace / 2.0
    p0: Point3 = (terminal_xyz[0], terminal_xyz[1] + (ny * half_trace), terminal_xyz[2] + (nz * half_trace))
    p1: Point3 = (terminal_xyz[0], terminal_xyz[1] - (ny * half_trace), terminal_xyz[2] - (nz * half_trace))
    return p0, p1


def _edge_points_at_tx_vertical_terminal(
    *,
    points: list[list[float]],
    trace: float,
    plane: Literal["ZX", "YZ"] = "ZX",
) -> Edge2P:
    if plane == "YZ":
        if len(points) < 2:
            raise ValueError("Cannot compute tx_vertical terminal edge from path with fewer than 2 points")
        return _edge_points_at_yz_terminal(
            terminal_xyz=cast(Point3, tuple(float(v) for v in points[0])),
            neighbor_xyz=cast(Point3, tuple(float(v) for v in points[1])),
            trace=trace,
        )
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
    return p0, p1


def _edge_points_at_tx_vertical_opposite_terminal(
    *,
    points: list[list[float]],
    trace: float,
    plane: Literal["ZX", "YZ"] = "ZX",
) -> Edge2P:
    if plane == "YZ":
        if len(points) < 2:
            raise ValueError("Cannot compute tx_vertical opposite terminal edge from path with fewer than 2 points")
        return _edge_points_at_yz_terminal(
            terminal_xyz=cast(Point3, tuple(float(v) for v in points[-1])),
            neighbor_xyz=cast(Point3, tuple(float(v) for v in points[-2])),
            trace=trace,
        )
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
    return p0, p1


def _tx_vertical_bridge_edges_from_node(
    *,
    start_xyz: Point3,
    end_xyz: Point3,
    trace: float,
    tx_vertical_region_min: Point3,
    tx_vertical_region_max: Point3,
    plane: Literal["ZX", "YZ"] = "ZX",
    points: list[list[float]] | None = None,
) -> tuple[Edge2P, Edge2P]:
    if plane == "YZ":
        if points is None:
            raise ValueError("tx_vertical YZ bridge edge resolution requires source points")
        if len(points) < 2:
            raise ValueError("tx_vertical YZ bridge edge resolution requires at least 2 source points")
        return (
            _edge_points_at_yz_terminal(
                terminal_xyz=cast(Point3, tuple(float(v) for v in points[0])),
                neighbor_xyz=cast(Point3, tuple(float(v) for v in points[1])),
                trace=trace,
            ),
            _edge_points_at_yz_terminal(
                terminal_xyz=cast(Point3, tuple(float(v) for v in points[-1])),
                neighbor_xyz=cast(Point3, tuple(float(v) for v in points[-2])),
                trace=trace,
            ),
        )
    half = trace / 2.0
    min_x_allowed = tx_vertical_region_min[0] + half
    max_x_allowed = tx_vertical_region_max[0] - half
    if min_x_allowed > max_x_allowed:
        raise ValueError(
            "tx_vertical bridge x-margin exceeds region width "
            f"(min_x_allowed={min_x_allowed}, max_x_allowed={max_x_allowed}, bridge_trace={trace})"
        )
    source_dx = end_xyz[0] - start_xyz[0]
    source_anchor_x = start_xyz[0] if abs(source_dx) <= 1e-9 else start_xyz[0] + math.copysign(half, source_dx)
    target_dx = start_xyz[0] - end_xyz[0]
    target_anchor_x = end_xyz[0] if abs(target_dx) <= 1e-9 else end_xyz[0] + math.copysign(half, target_dx)
    source_bridge_x = min(max(source_anchor_x, min_x_allowed), max_x_allowed)
    target_bridge_x = min(max(target_anchor_x, min_x_allowed), max_x_allowed)
    source_bridge_x = min(max(source_bridge_x, min_x_allowed), max_x_allowed)
    target_bridge_x = min(max(target_bridge_x + trace, min_x_allowed), max_x_allowed)
    bridge_out_edge: Edge2P = (
        (source_bridge_x, start_xyz[1], start_xyz[2] - half),
        (source_bridge_x, start_xyz[1], start_xyz[2] + half),
    )
    bridge_in_edge: Edge2P = (
        (target_bridge_x, end_xyz[1], end_xyz[2] - half),
        (target_bridge_x, end_xyz[1], end_xyz[2] + half),
    )
    return bridge_out_edge, bridge_in_edge


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
        pcb_thickness=prelude["pcb_thickness"],
        cu_thickness=prelude["cu_thickness"],
        tx_dd_top_clearance=prelude["tx_dd_top_clearance"],
        tx_vertical_layout_mode=cast(Literal[1, 2], prelude["tx_vertical_layout_mode"]),
        tx_vertical_mode2_pair_spacing_mm=prelude["tx_vertical_mode2_pair_spacing_mm"],
        tx_vertical_mode2_x_ratio_to_tx_dd_center=prelude["tx_vertical_mode2_x_ratio_to_tx_dd_center"],
        rx_face_clearance=prelude["rx_face_clearance"],
        tx_vertical_plane=cast(Literal["ZX", "YZ"], prelude["tx_vertical_plane"]),
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
    ctx.tx_dd_region_min, ctx.tx_dd_region_max = _bounds_from_scene_entry(scene_by_kind["tx_region_dd"])
    ctx.tx_vertical_region_min, ctx.tx_vertical_region_max = _bounds_from_scene_entry(scene_by_kind["tx_region_vertical"])
    ctx.rx_region_min, ctx.rx_region_max = _bounds_from_scene_entry(scene_by_kind["rx_region_actual"])

    # TX DD stays attached to the YZ plane side (minimum X of TX region).
    ctx.tx_dd_center_x = ctx.tx_dd_region_min[0] + (ctx.tx_dd_outer_x / 2.0)
    ctx.tx_dd_center_y = (ctx.tx_dd_region_min[1] + ctx.tx_dd_region_max[1]) / 2.0
    if ctx.tx_vertical_plane == "ZX":
        ctx.tx_vertical_center_x = ctx.tx_vertical_region_min[0] + (ctx.tx_vertical_outer_x / 2.0)
    else:
        ctx.tx_vertical_center_x = tx_vertical_mode2_center_x_from_tx_dd_min(
            tx_dd_min_x=ctx.tx_dd_region_min[0],
            tx_dd_outer_x=ctx.tx_dd_outer_x,
            x_ratio=ctx.tx_vertical_mode2_x_ratio_to_tx_dd_center,
        )
    ctx.tx_vertical_center_y = (ctx.tx_vertical_region_min[1] + ctx.tx_vertical_region_max[1]) / 2.0
    ctx.rx_center_y = (ctx.rx_region_min[1] + ctx.rx_region_max[1]) / 2.0


def _build_ferrite(ctx: GeometryRuntimeContext, state: GeometryBuildState, modeler: Modeler3D, hfss: Hfss) -> None:
    ferrite_names, ferrite_probes, ferrite_entries = _create_ferrite_model_objects(
        modeler=modeler,
        hfss=hfss,
        design_id=ctx.design_id,
        selected=ctx.selected,
        scene_objects=state.scene_objects,
        object_names=state.object_names,
        coil_plane_bboxes=state.coil_plane_bboxes,
        cad_probe=state.cad_probe,
        tx_board_ids=ctx.tx_board_ids,
    )
    state.object_names.extend(ferrite_names)
    state.cad_probe.extend(ferrite_probes)
    state.scene_objects.extend(ferrite_entries)
    state.group_objects["ferrite"].extend(ferrite_names)


def _build_all_coils(ctx: GeometryRuntimeContext, state: GeometryBuildState, modeler: Modeler3D) -> FinalizeInputs:
    finalize_inputs = FinalizeInputs()
    for board_idx, pcb in enumerate(ctx.selected_pcbs):
        if not pcb["present"]:
            continue
        for group in ctx.selected_groups:
            kind = group["kind"]
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
    if (
        ctx.tx_vertical_region_min is None
        or ctx.tx_vertical_region_max is None
    ):
        raise ValueError("tx_vertical region bounds were not initialized")

    object_names, fr4_object_names = finalize_solids_and_substrates(
        modeler=modeler,
        hfss=hfss,
        aedt_path=ctx.aedt_path,
        design_id=ctx.design_id,
        cu_thickness=ctx.cu_thickness,
        pcb_thickness=ctx.pcb_thickness,
        tx_board_ids=ctx.tx_board_ids,
        tx_vertical_nodes_by_board=finalize_inputs.tx_vertical_nodes_by_board,
        tx_vertical_mode2_terminal_edges_by_board=finalize_inputs.tx_vertical_mode2_terminal_edges_by_board,
        tx_vertical_region_min=ctx.tx_vertical_region_min,
        tx_vertical_region_max=ctx.tx_vertical_region_max,
        txdd_right_a_points=finalize_inputs.txdd_right_a_points,
        txdd_right_object_names=finalize_inputs.txdd_right_object_names,
        txdd_left_a_points=finalize_inputs.txdd_left_a_points,
        txdd_left_object_names=finalize_inputs.txdd_left_object_names,
        txdd_start_stub_sources=finalize_inputs.txdd_start_stub_sources,
        rxdd_back_stub_sources=finalize_inputs.rxdd_back_stub_sources,
        group_objects=state.group_objects,
        object_names=state.object_names,
        cad_probe=state.cad_probe,
        placement_violations=state.placement_violations,
        coil_plane_bboxes=state.coil_plane_bboxes,
        fr4_object_names=state.fr4_object_names,
        tx_vertical_fr4_names=state.tx_vertical_fr4_names,
        txdd_global_right_d_edge=finalize_inputs.txdd_global_right_d_edge,
        txdd_global_right_d_object_name=finalize_inputs.txdd_global_right_d_object_name,
        txdd_global_left_vertical_link_edge=finalize_inputs.txdd_global_left_vertical_link_edge,
        txdd_global_left_vertical_link_object_name=finalize_inputs.txdd_global_left_vertical_link_object_name,
        tx_vertical_global_outer_right_edge=finalize_inputs.tx_vertical_global_outer_right_edge,
        tx_vertical_global_outer_left_edge=finalize_inputs.tx_vertical_global_outer_left_edge,
    )
    state.object_names = object_names
    state.fr4_object_names = fr4_object_names


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
    if ctx.tx_dd_region_min is None:
        raise ValueError("tx_dd region bounds were not initialized")

    debug_geometry = ctx.group_geometry_by_kind["tx_dd"]
    debug_centerline_vertices = _build_rect_spiral_centerline_absolute(
        turns=debug_geometry["turn_count_max"],
        outer_x=ctx.tx_dd_outer_x,
        outer_y=ctx.tx_dd_outer_y,
        trace=debug_geometry["trace"],
        gap=debug_geometry["gap"],
        z=0.0,
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
    top_probe = next((probe for probe in state.cad_probe if probe["object_name"].startswith("coil_")), None)
    top_bbox = top_probe["bbox"] if top_probe is not None else []
    print(f"[geometry] constraints_ok={debug['constraints_ok']}")
    print(f"[geometry] axis_aligned={axis_aligned} pitch_max_delta={pitch_max_delta:.9f}")
    print(f"[geometry] top_bbox={top_bbox}")

    _apply_txdd_right_endpoint_rule(state.group_endpoints, state.coil_polarity)

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
    outputs = manifest["spec"]["outputs"]
    em_input: EmPipelineInput = {
        "ready_objects": em_ready_objects,
        "endpoints": em_endpoints,
        "context": em_context,
    }
    em_pipeline_result = run_em_pipeline(hfss, modeler, em_input, em_policy, outputs)
    # Reports/post-processing artifacts are added during EM pipeline; persist them before packaging/export.
    hfss.save_project(str(ctx.aedt_path))

    metadata = _build_geometry_metadata(
        manifest=manifest,
        aedt_path=ctx.aedt_path,
        object_names=state.object_names,
        metadata_path=ctx.metadata_path,
        group_objects=state.group_objects,
        unite_groups={
            "tx": sorted(state.group_objects["tx_dd"] + state.group_objects["tx_vertical"]),
            "rx": sorted(state.group_objects["rx_dd"]),
            "ferrite": sorted(state.group_objects["ferrite"]),
        },
        group_endpoints=state.group_endpoints,
        coil_polarity=state.coil_polarity,
        em_ready_objects=em_ready_objects,
        em_endpoints=em_endpoints,
        em_context=em_context,
        em_policy=em_policy,
        em_pipeline_result=em_pipeline_result,
        scene_objects=state.scene_objects,
        debug=debug,
    )
    _write_geometry_metadata_if_enabled(manifest, metadata, ctx.metadata_path)
    return metadata


def build_square_spiral_from_manifest(manifest: Manifest) -> GeometryMetadata:
    ctx = _prepare_runtime(manifest)
    hfss = create_hfss_session(manifest=manifest, aedt_path=ctx.aedt_path)
    _assign_design_variables(hfss, manifest)
    modeler = cast(Modeler3D, hfss.modeler)
    state = GeometryBuildState()
    try:
        _build_scene(ctx, state, modeler)
        finalize_inputs = _build_all_coils(ctx, state, modeler)
        _finalize_geometry(ctx, state, finalize_inputs, modeler, hfss)
        _build_ferrite(ctx, state, modeler, hfss)
        return _build_and_save_metadata(ctx, state, manifest, hfss)
    except Exception as exc:
        raise RuntimeError(f"Failed to build geometry with Pyaedt: {exc}") from exc
    finally:
        try:
            hfss.release_desktop(close_projects=ctx.close_on_exit, close_desktop=ctx.close_on_exit)
        except Exception:
            pass

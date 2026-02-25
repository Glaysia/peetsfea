from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Literal, cast

from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.backend.pyaedt.em_pipeline import default_em_policy, run_em_pipeline
from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput
from peetsfea.types.manifest import (
    CadProbe,
    CoilPolaritySpec,
    EmPolicy,
    GeometryMetadata,
    GroupEndpointEntry,
    GroupGeometryParams,
    GroupObjects,
    Manifest,
    RegionViolation,
    SceneObjectEntry,
    TerminalLabel,
)

from .cad_probe import _object_name, _probe_cad_object, _probe_from_points
from .build_rx_dd import build_em_artifacts, finalize_solids_and_substrates
from .build_tx_dd import extract_build_prelude, validate_build_prelude
from .build_tx_vertical import create_hfss_session
from .debug_checks import _bbox_violations, _build_geometry_debug
from .design_vars import _assign_design_variables
from .metadata import _build_geometry_metadata
from .placement_rules import (
    _apply_txdd_right_endpoint_rule,
    _build_rxdd_right_points_A_to_d_cw,
    _build_polarity,
    _coil_instance_offset,
    _current_direction_from_xy_points,
    _extend_endpoints,
    _instance_side,
    _max_feasible_turns,
    _mount_allows_instance,
    _rx_dd_center_offset_y,
    _tx_dd_center_y_and_layer,
    _txdd_right_layer_rank_by_z,
    _txdd_right_points,
    _validate_rxdd_single_layer_count,
)
from .scene_objects import _bounds_from_scene_entry, _create_scene_non_model_objects
from .spiral_points import (
    _build_rect_spiral_centerline_absolute,
    _map_xy_points_to_yz,
    _map_xy_points_to_zx,
    _mirror_points_about_y_axis_line,
    _translate_points,
)

_Point3 = tuple[float, float, float]
_Edge2P = tuple[_Point3, _Point3]
_BoardKey = tuple[str, int]
_TxVerticalLinkNode = tuple[int, str, _Point3, _Point3, float, float, _Edge2P, _Edge2P]
_TxDdStartStubSource = tuple[_Point3, float, str]
_RxDdBackStubSource = tuple[str, int, str, _Point3, float, str]


def _append_rxdd_back_stub_sources_if_needed(
    *,
    kind: str,
    board_id: str,
    instance_index: int,
    start_xyz: _Point3,
    end_xyz: _Point3,
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


def _edge_points_at_path_end(*, points: list[list[float]], trace: float) -> _Edge2P:
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
    p0: _Point3 = (end[0] + (nx * half_trace), end[1] + (ny * half_trace), end[2])
    p1: _Point3 = (end[0] - (nx * half_trace), end[1] - (ny * half_trace), end[2])
    return p0, p1


def _edge_points_at_tx_vertical_terminal(*, points: list[list[float]], trace: float) -> _Edge2P:
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
    p0: _Point3 = (terminal[0] + (nx * half_trace), terminal[1], terminal[2] + (nz * half_trace))
    p1: _Point3 = (terminal[0] - (nx * half_trace), terminal[1], terminal[2] - (nz * half_trace))
    return p0, p1


def _edge_points_at_tx_vertical_opposite_terminal(*, points: list[list[float]], trace: float) -> _Edge2P:
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
    p0: _Point3 = (terminal[0] + (nx * half_trace), terminal[1], terminal[2] + (nz * half_trace))
    p1: _Point3 = (terminal[0] - (nx * half_trace), terminal[1], terminal[2] - (nz * half_trace))
    return p0, p1


def _tx_vertical_bridge_edges_from_node(
    *,
    start_xyz: _Point3,
    end_xyz: _Point3,
    trace: float,
    tx_vertical_region_min: _Point3,
    tx_vertical_region_max: _Point3,
) -> tuple[_Edge2P, _Edge2P]:
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
    bridge_out_edge: _Edge2P = (
        (source_bridge_x, start_xyz[1], start_xyz[2] - half),
        (source_bridge_x, start_xyz[1], start_xyz[2] + half),
    )
    bridge_in_edge: _Edge2P = (
        (target_bridge_x, end_xyz[1], end_xyz[2] - half),
        (target_bridge_x, end_xyz[1], end_xyz[2] + half),
    )
    return bridge_out_edge, bridge_in_edge


def build_square_spiral_from_manifest(manifest: Manifest) -> GeometryMetadata:
    manifest["repro_mode"] = "manifest_json"
    selected = manifest["selected_parameters"]
    prelude = extract_build_prelude(manifest)
    validate_build_prelude(prelude)
    tx_dd_outer_x = prelude["tx_dd_outer_x"]
    tx_dd_outer_y = prelude["tx_dd_outer_y"]
    tx_vertical_outer_x = prelude["tx_vertical_outer_x"]
    tx_vertical_outer_y = prelude["tx_vertical_outer_y"]
    rx_dd_outer_x = prelude["rx_dd_outer_x"]
    rx_dd_outer_y = prelude["rx_dd_outer_y"]
    pcb_thickness = prelude["pcb_thickness"]
    cu_thickness = prelude["cu_thickness"]
    tx_dd_top_clearance = prelude["tx_dd_top_clearance"]
    rx_face_clearance = prelude["rx_face_clearance"]
    tx_vertical_plane = cast(Literal["ZX"], prelude["tx_vertical_plane"])

    run_dir = Path(manifest["inputs"]["ansys_run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)

    design_id = manifest["design_id"]
    aedt_path = run_dir / f"{design_id}.aedt"
    metadata_path = run_dir / f"geometry_metadata_{design_id}.json"

    selected_groups = manifest["selected_coil_groups"]
    selected_group_geometry = manifest["selected_group_geometry"]
    selected_pcbs = manifest["selected_pcbs"]
    tx_board_ids: set[str] = {pcb["id"] for pcb in selected_pcbs if pcb["role"] == "tx"}
    group_geometry_by_kind: dict[Literal["tx_dd", "tx_vertical", "rx_dd"], GroupGeometryParams] = {
        entry["kind"]: entry for entry in selected_group_geometry
    }
    missing_geometry = [kind for kind in ("tx_dd", "tx_vertical", "rx_dd") if kind not in group_geometry_by_kind]
    if missing_geometry:
        raise ValueError(f"Missing selected_group_geometry entries: {', '.join(missing_geometry)}")

    hfss = create_hfss_session(manifest=manifest, aedt_path=aedt_path)
    _assign_design_variables(hfss, manifest)
    modeler = cast(Modeler3D, hfss.modeler)

    close_on_exit = manifest["inputs"]["close_on_exit"]
    object_names: list[str] = []
    cad_probe: list[CadProbe] = []
    group_objects: GroupObjects = {"tx_dd": [], "tx_vertical": [], "rx_dd": []}
    group_endpoints: list[GroupEndpointEntry] = []
    coil_polarity: list[CoilPolaritySpec] = []
    scene_objects: list[SceneObjectEntry] = []
    placement_violations: list[RegionViolation] = []
    coil_plane_bboxes: list[tuple[str, Literal["XY", "YZ", "ZX"], list[float]]] = []
    fr4_object_names: list[str] = []
    tx_zx_fr4_names: list[str] = []
    txdd_right_a_points: dict[int, tuple[_Point3, float]] = {}
    txdd_right_object_names: dict[int, str] = {}
    txdd_left_a_points: dict[int, tuple[_Point3, float]] = {}
    txdd_left_object_names: dict[int, str] = {}
    txdd_start_stub_sources: dict[str, list[_TxDdStartStubSource]] = {}
    rxdd_back_stub_sources: list[_RxDdBackStubSource] = []
    tx_vertical_nodes_by_board: dict[_BoardKey, list[_TxVerticalLinkNode]] = {}
    txdd_global_right_d_edge: _Edge2P | None = None
    txdd_global_right_d_object_name: str | None = None
    txdd_global_right_d_selection_key: tuple[float, str, int] | None = None
    txdd_global_left_a_edge: _Edge2P | None = None
    txdd_global_left_a_object_name: str | None = None
    tx_vertical_global_outer_right_edge: _Edge2P | None = None
    tx_vertical_global_outer_left_edge: _Edge2P | None = None
    tx_vertical_outer_right_selection_key: tuple[float, str, int] | None = None
    tx_vertical_outer_left_selection_key: tuple[float, str, int] | None = None

    try:
        scene_names, scene_probes, scene_objects = _create_scene_non_model_objects(
            modeler=modeler,
            design_id=design_id,
            selected=selected,
            selected_max=manifest["selected_parameters_max"],
        )
        object_names.extend(scene_names)
        cad_probe.extend(scene_probes)
        scene_by_kind = {entry["kind"]: entry for entry in scene_objects}
        tx_dd_region_min, tx_dd_region_max = _bounds_from_scene_entry(scene_by_kind["tx_region_dd"])
        tx_vertical_region_min, tx_vertical_region_max = _bounds_from_scene_entry(scene_by_kind["tx_region_vertical"])
        rx_region_min, rx_region_max = _bounds_from_scene_entry(scene_by_kind["rx_region_actual"])
        # Keep TX coils attached to the YZ plane side (minimum X of TX region).
        tx_dd_center_x = tx_dd_region_min[0] + (tx_dd_outer_x / 2.0)
        tx_dd_center_y = (tx_dd_region_min[1] + tx_dd_region_max[1]) / 2.0
        tx_vertical_center_x = tx_vertical_region_min[0] + (tx_vertical_outer_x / 2.0)
        tx_vertical_center_y = (tx_vertical_region_min[1] + tx_vertical_region_max[1]) / 2.0
        rx_center_y = (rx_region_min[1] + rx_region_max[1]) / 2.0

        for board_idx, pcb in enumerate(selected_pcbs):
            if not pcb["present"]:
                continue
            board_x, board_y, board_z = pcb["position"]

            for group in selected_groups:
                kind = group["kind"]
                geometry = group_geometry_by_kind[kind]
                turns = geometry["turn_count_max"]
                trace = geometry["trace"]
                gap = geometry["gap"]
                base_points: list[list[float]] | None = None
                if turns < 1:
                    raise ValueError(f"selected_group_geometry.{kind}.turn_count_max must be >= 1")
                if trace <= 0:
                    raise ValueError(f"selected_group_geometry.{kind}.trace must be > 0")
                if gap < 0:
                    raise ValueError(f"selected_group_geometry.{kind}.gap must be >= 0")
                if kind != "tx_vertical":
                    if kind == "tx_dd":
                        active_outer_x = tx_dd_outer_x
                        active_outer_y = tx_dd_outer_y
                    else:
                        active_outer_x = rx_dd_outer_x
                        active_outer_y = rx_dd_outer_y
                    max_turns = min(
                        _max_feasible_turns(active_outer_x, trace, gap),
                        _max_feasible_turns(active_outer_y, trace, gap),
                    )
                    if max_turns < 1:
                        raise ValueError(
                            f"Invalid geometry for {kind}: cannot fit at least one turn on both X/Y axes "
                            f"(turns={turns}, trace={trace}, gap={gap})"
                        )
                    if turns > max_turns:
                        raise ValueError(
                            f"Infeasible turn_count_max for {kind}: requested={turns}, feasible_max={max_turns} "
                            f"(outer_x={active_outer_x}, outer_y={active_outer_y}, trace={trace}, gap={gap})"
                        )
                    base_points = [
                        list(point)
                        for point in _build_rect_spiral_centerline_absolute(
                            turns=turns,
                            outer_x=active_outer_x,
                            outer_y=active_outer_y,
                            trace=trace,
                            gap=gap,
                            z=0.0,
                        )
                    ]
                instance_count = group["selected_count"]
                spacing_mm = group["spacing_mm"]
                transforms = group["instance_transforms"]
                transform = transforms[0] if transforms else {"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0}
                txdd_right_layer_rank: dict[int, int] = {}
                rxdd_right_local_points: list[list[float]] | None = None
                if kind == "rx_dd":
                    _validate_rxdd_single_layer_count(instance_count)
                if kind == "rx_dd" and spacing_mm < 0:
                    raise ValueError(f"rx_dd edge gap must be >= 0 (actual={spacing_mm})")
                if kind == "rx_dd":
                    rxdd_right_local_points = _build_rxdd_right_points_A_to_d_cw(
                        turns=turns,
                        outer_x=rx_dd_outer_x,
                        outer_y=rx_dd_outer_y,
                        trace=trace,
                        gap=gap,
                    )
                if kind == "tx_dd" and instance_count == 4:
                    tx_dd_anchor_z = tx_dd_region_max[2] - tx_dd_top_clearance - cu_thickness
                    txdd_right_layer_rank = _txdd_right_layer_rank_by_z(
                        selected_pcbs=selected_pcbs,
                        instance_count=instance_count,
                        transform_dz=transform["dz"],
                        tx_dd_anchor_z=tx_dd_anchor_z,
                    )

                for instance_index in range(instance_count):
                    if kind == "tx_dd":
                        assert base_points is not None
                        local_slot = instance_index % 2
                        if local_slot == 0:
                            _tx_dd_center_y_and_layer(
                                instance_count=instance_count,
                                instance_index=instance_index,
                                pair_clearance_mm=spacing_mm,
                                outer_y=tx_dd_outer_y,
                                region_center_y=tx_dd_center_y,
                                region_min_y=tx_dd_region_min[1],
                                region_max_y=tx_dd_region_max[1],
                            )
                            right_index = instance_index + 1
                            _tx_dd_center_y_and_layer(
                                instance_count=instance_count,
                                instance_index=right_index,
                                pair_clearance_mm=spacing_mm,
                                outer_y=tx_dd_outer_y,
                                region_center_y=tx_dd_center_y,
                                region_min_y=tx_dd_region_min[1],
                                region_max_y=tx_dd_region_max[1],
                            )
                            left_mounted = _mount_allows_instance(pcb["mounts"], kind, instance_index)
                            right_mounted = right_index < instance_count and _mount_allows_instance(
                                pcb["mounts"], kind, right_index
                            )
                            if left_mounted and not right_mounted:
                                raise ValueError(
                                    "tx_dd mirror source missing: left instance is mounted without matching right "
                                    f"(board_id={pcb['id']}, left_index={instance_index}, right_index={right_index})"
                                )
                            continue
                        if not _mount_allows_instance(pcb["mounts"], kind, instance_index):
                            continue

                        right_index = instance_index
                        left_index = right_index - 1
                        right_center_y, tx_dd_layer_index = _tx_dd_center_y_and_layer(
                            instance_count=instance_count,
                            instance_index=right_index,
                            pair_clearance_mm=spacing_mm,
                            outer_y=tx_dd_outer_y,
                            region_center_y=tx_dd_center_y,
                            region_min_y=tx_dd_region_min[1],
                            region_max_y=tx_dd_region_max[1],
                        )
                        right_layer_index = txdd_right_layer_rank.get(right_index, tx_dd_layer_index)
                        tx_dd_points = _txdd_right_points(
                            turns=turns,
                            outer_x=tx_dd_outer_x,
                            outer_y=tx_dd_outer_y,
                            trace=trace,
                            gap=gap,
                            instance_count=instance_count,
                            layer_index=right_layer_index,
                        )
                        raw_right_a_local: _Point3 | None = None
                        right_a_point: _Point3 | None = None
                        if instance_count == 4 and right_layer_index in (0, 1):
                            raw_right_a_source = tx_dd_points[-1] if right_layer_index == 0 else tx_dd_points[0]
                            raw_right_a_local = cast(_Point3, tuple(float(v) for v in raw_right_a_source))
                        tx_dd_points = _extend_endpoints(tx_dd_points, extension=(trace / 2.0))
                        tx_dd_anchor_z = tx_dd_region_max[2] - tx_dd_top_clearance - cu_thickness
                        tx_dd_dx = tx_dd_center_x + transform["dx"]
                        tx_dd_dy = right_center_y + transform["dy"]
                        tx_dd_dz = tx_dd_anchor_z - board_z + transform["dz"]
                        right_top_points = _translate_points(
                            tx_dd_points,
                            dx=tx_dd_dx,
                            dy=tx_dd_dy,
                            dz=tx_dd_dz,
                        )
                        if instance_count == 4 and right_layer_index in (0, 1):
                            if raw_right_a_local is None:
                                raise ValueError(
                                    "tx_dd layer bridge contract violation: raw right A anchor was not captured "
                                    f"(layer_index={right_layer_index})"
                                )
                            right_a_point = (
                                raw_right_a_local[0] + tx_dd_dx,
                                raw_right_a_local[1] + tx_dd_dy,
                                raw_right_a_local[2] + tx_dd_dz,
                            )
                            txdd_right_a_points[right_layer_index] = (
                                cast(_Point3, right_a_point),
                                trace,
                            )
                        right_name = f"coil_{kind}_g{right_index}_b{board_idx}_{design_id}"
                        right_created = modeler.create_polyline(
                            points=right_top_points,
                            name=right_name,
                            material="copper",
                            xsection_type="Rectangle",
                            xsection_width=trace,  # type: ignore
                            xsection_height=cu_thickness,  # type: ignore
                        )
                        if not right_created:
                            raise ValueError(
                                "tx_dd right polyline creation failed "
                                f"(name={right_name}, points={len(right_top_points)}, group_kind={kind})"
                            )
                        right_obj = cast(Object3d, right_created)
                        right_obj_name = _object_name(right_obj, right_name)
                        capture_dd_right_d_edge = (instance_count == 2) or (instance_count == 4 and right_layer_index == 1)
                        if capture_dd_right_d_edge:
                            d_edge_points = _edge_points_at_path_end(points=right_top_points, trace=trace)
                            selection_key = (-right_center_y, pcb["id"], right_index)
                            if txdd_global_right_d_selection_key is None or selection_key < txdd_global_right_d_selection_key:
                                txdd_global_right_d_selection_key = selection_key
                                txdd_global_right_d_edge = d_edge_points
                                txdd_global_right_d_object_name = right_obj_name
                        object_names.append(right_obj_name)
                        if instance_count == 2 and right_index == 1:
                            txdd_start_stub_sources.setdefault(pcb["id"], []).append(
                                (
                                    cast(_Point3, tuple(float(v) for v in right_top_points[0])),
                                    trace,
                                    right_obj_name,
                                )
                            )
                        elif instance_count == 4 and right_layer_index == 0:
                            txdd_start_stub_sources.setdefault(pcb["id"], []).append(
                                (
                                    cast(_Point3, tuple(float(v) for v in right_top_points[0])),
                                    trace,
                                    right_obj_name,
                                )
                            )
                        if instance_count == 4 and right_layer_index in (0, 1):
                            txdd_right_object_names[right_layer_index] = right_obj_name
                        right_probe = _probe_cad_object(right_obj, right_name)
                        cad_probe.append(right_probe)
                        coil_plane_bboxes.append((pcb["id"], "XY", right_probe["bbox"]))
                        right_violations = _bbox_violations(
                            object_name=right_obj_name,
                            bbox=right_probe["bbox"],
                            region_kind="tx_region_dd",
                            region_min=tx_dd_region_min,
                            region_max=tx_dd_region_max,
                        )
                        if right_violations:
                            placement_violations.extend(right_violations)
                            first = right_violations[0]
                            raise ValueError(
                                f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
                                f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
                            )
                        group_objects[kind].append(right_obj_name)
                        right_start_xyz = cast(_Point3, tuple(float(v) for v in right_top_points[0]))
                        right_end_xyz = cast(_Point3, tuple(float(v) for v in right_top_points[-1]))
                        group_endpoints.append(
                            {
                                "group_kind": kind,
                                "group_instance_index": right_index,
                                "board_id": pcb["id"],
                                "start_xyz": right_start_xyz,
                                "end_xyz": right_end_xyz,
                                "start_label": "A",
                                "end_label": "a",
                                "present": True,
                            }
                        )
                        right_off_y = right_center_y - tx_dd_center_y
                        right_side = _instance_side(kind, (0.0, right_off_y, 0.0))
                        default_right_current_direction, right_b_field_direction = _build_polarity(kind, right_side)
                        right_current_direction = _current_direction_from_xy_points(right_top_points) or default_right_current_direction
                        coil_polarity.append(
                            {
                                "group_kind": kind,
                                "group_instance_index": right_index,
                                "board_id": pcb["id"],
                                "instance_side": right_side,
                                "current_direction": right_current_direction,
                                "b_field_direction": right_b_field_direction,
                            }
                        )

                        if _mount_allows_instance(pcb["mounts"], kind, left_index):
                            mirror_origin = [
                                tx_dd_center_x + transform["dx"],
                                tx_dd_center_y + transform["dy"],
                                tx_dd_anchor_z - board_z + transform["dz"],
                            ]
                            mirrored_created = modeler.duplicate_and_mirror(
                                assignment=right_obj_name,
                                origin=mirror_origin,
                                vector=[0.0, 1.0, 0.0],
                                duplicate_assignment=True,
                            )
                            if not isinstance(mirrored_created, list) or len(mirrored_created) != 1:
                                raise ValueError(
                                    "tx_dd mirror creation failed: expected exactly one mirrored object "
                                    f"(board_id={pcb['id']}, right_index={right_index}, result={mirrored_created})"
                                )
                            left_obj_name = str(mirrored_created[0])
                            object_names.append(left_obj_name)
                            left_top_points = _mirror_points_about_y_axis_line(
                                right_top_points,
                                axis_y=tx_dd_center_y + transform["dy"],
                            )
                            capture_dd_left_a_edge = (instance_count == 2) or (instance_count == 4 and right_layer_index == 1)
                            if capture_dd_left_a_edge:
                                left_a_edge_points = _edge_points_at_path_end(points=left_top_points, trace=trace)
                                if txdd_global_left_a_edge is not None:
                                    prev_object_name = txdd_global_left_a_object_name
                                    raise ValueError(
                                        "tx_dd global left a-edge must be unique for tx_dd_left_a->tx_vertical bridge contract "
                                        f"(existing: object_name={prev_object_name}; "
                                        f"new: board_id={pcb['id']}, instance_index={right_index}, object_name={left_obj_name})"
                                    )
                                txdd_global_left_a_edge = left_a_edge_points
                                txdd_global_left_a_object_name = left_obj_name
                            if instance_count == 2:
                                txdd_start_stub_sources.setdefault(pcb["id"], []).append(
                                    (
                                        cast(_Point3, tuple(float(v) for v in left_top_points[0])),
                                        trace,
                                        left_obj_name,
                                    )
                                )
                            elif instance_count == 4 and right_layer_index == 0:
                                txdd_start_stub_sources.setdefault(pcb["id"], []).append(
                                    (
                                        cast(_Point3, tuple(float(v) for v in left_top_points[0])),
                                        trace,
                                        left_obj_name,
                                    )
                                )
                            if instance_count == 4 and right_layer_index in (0, 1):
                                txdd_left_object_names[right_layer_index] = left_obj_name
                                if right_a_point is None:
                                    raise ValueError(
                                        "tx_dd left layer bridge contract violation: right A anchor missing "
                                        f"(layer_index={right_layer_index})"
                                    )
                                left_a_point = (
                                    right_a_point[0],
                                    (2.0 * (tx_dd_center_y + transform["dy"])) - right_a_point[1],
                                    right_a_point[2],
                                )
                                txdd_left_a_points[right_layer_index] = (cast(_Point3, left_a_point), trace)
                            left_probe = _probe_from_points(left_obj_name, left_top_points)
                            cad_probe.append(left_probe)
                            coil_plane_bboxes.append((pcb["id"], "XY", left_probe["bbox"]))
                            left_violations = _bbox_violations(
                                object_name=left_obj_name,
                                bbox=left_probe["bbox"],
                                region_kind="tx_region_dd",
                                region_min=tx_dd_region_min,
                                region_max=tx_dd_region_max,
                            )
                            if left_violations:
                                placement_violations.extend(left_violations)
                                first = left_violations[0]
                                raise ValueError(
                                    f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
                                    f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
                                )
                            group_objects[kind].append(left_obj_name)
                            left_start_xyz = cast(_Point3, tuple(float(v) for v in left_top_points[0]))
                            left_end_xyz = cast(_Point3, tuple(float(v) for v in left_top_points[-1]))
                            group_endpoints.append(
                                {
                                    "group_kind": kind,
                                    "group_instance_index": left_index,
                                    "board_id": pcb["id"],
                                    "start_xyz": left_start_xyz,
                                    "end_xyz": left_end_xyz,
                                    "start_label": "A",
                                    "end_label": "a",
                                    "present": True,
                                }
                            )
                            left_center_y, _ = _tx_dd_center_y_and_layer(
                                instance_count=instance_count,
                                instance_index=left_index,
                                pair_clearance_mm=spacing_mm,
                                outer_y=tx_dd_outer_y,
                                region_center_y=tx_dd_center_y,
                                region_min_y=tx_dd_region_min[1],
                                region_max_y=tx_dd_region_max[1],
                            )
                            left_off_y = left_center_y - tx_dd_center_y
                            left_side = _instance_side(kind, (0.0, left_off_y, 0.0))
                            default_left_current_direction, left_b_field_direction = _build_polarity(kind, left_side)
                            left_current_direction = _current_direction_from_xy_points(left_top_points) or default_left_current_direction
                            coil_polarity.append(
                                {
                                    "group_kind": kind,
                                    "group_instance_index": left_index,
                                    "board_id": pcb["id"],
                                    "instance_side": left_side,
                                    "current_direction": left_current_direction,
                                    "b_field_direction": left_b_field_direction,
                                }
                            )
                        continue

                    if not _mount_allows_instance(pcb["mounts"], kind, instance_index):
                        continue
                    off_x = 0.0
                    off_y = 0.0
                    off_z = 0.0
                    if kind == "rx_dd":
                        off_y = _rx_dd_center_offset_y(
                            instance_index=instance_index,
                            instance_count=instance_count,
                            outer_x=rx_dd_outer_x,
                            edge_gap_mm=spacing_mm,
                        )
                        if abs(transform["dz"]) > 1e-12:
                            raise ValueError("rx_dd transform dz must be 0 for bottom-anchor contract")
                        if abs(transform["dx"]) > 1e-12:
                            raise ValueError("rx_dd transform dx must be 0 for +X face-anchor contract")
                        rx_anchor_x = rx_region_max[0] - rx_face_clearance - cu_thickness
                        # Bottom-anchor contract: coil bottom touches RX region minimum Z.
                        rx_center_z = rx_region_min[2] + (rx_dd_outer_y / 2.0) + 1e-6
                        axis_y = rx_center_y + transform["dy"]
                        pair_offset_y = abs(off_y)
                        rx_side = _instance_side(kind, (0.0, off_y, 0.0))
                        if rx_side == "center":
                            raise ValueError(
                                "rx_dd side contract violation: instance side must be left or right "
                                f"(instance_index={instance_index}, off_y={off_y})"
                            )
                        if rxdd_right_local_points is None:
                            raise ValueError("rx_dd right path contract violation: right template points missing")
                        rx_dd_points = [point[:] for point in rxdd_right_local_points]
                        translated_xy = _translate_points(
                            rx_dd_points,
                            dx=0.0,
                            dy=0.0,
                            dz=0.0,
                        )
                        top_points = _map_xy_points_to_yz(
                            translated_xy,
                            x_const=rx_anchor_x + transform["dx"] + off_x,
                            y_center=axis_y + pair_offset_y,
                            z_center=rx_center_z + transform["dz"] + off_z,
                        )
                        if rx_side == "left":
                            top_points = [[point[0], (2.0 * axis_y) - point[1], point[2]] for point in top_points]
                    elif kind == "tx_vertical":
                        off_x, off_y, off_z = _coil_instance_offset(
                            kind,
                            instance_index,
                            instance_count,
                            spacing_mm,
                            trace_mm=trace,
                        )
                        tx_vertical_zone_h = tx_vertical_region_max[2] - tx_vertical_region_min[2]
                        tx_vertical_outer_y = min(tx_vertical_outer_y, tx_vertical_zone_h)
                        tx_vertical_max_turns = min(
                            _max_feasible_turns(tx_vertical_outer_x, trace, gap),
                            _max_feasible_turns(tx_vertical_outer_y, trace, gap),
                        )
                        if tx_vertical_max_turns < 1:
                            raise ValueError(
                                "tx_vertical cannot fit in tx_region_vertical "
                                f"(available_outer_x={tx_vertical_outer_x}, available_outer_y={tx_vertical_outer_y})"
                            )
                        if turns > tx_vertical_max_turns:
                            raise ValueError(
                                "Infeasible turn_count_max for tx_vertical: "
                                f"requested={turns}, feasible_max={tx_vertical_max_turns} "
                                f"(outer_x={tx_vertical_outer_x}, outer_y={tx_vertical_outer_y}, trace={trace}, gap={gap})"
                            )
                        tx_vertical_points = [
                            list(point)
                            for point in _build_rect_spiral_centerline_absolute(
                                turns=turns,
                                outer_x=tx_vertical_outer_x,
                                outer_y=tx_vertical_outer_y,
                                trace=trace,
                                gap=gap,
                                z=0.0,
                            )
                        ]
                        tx_vertical_center_z = tx_vertical_region_min[2] + (tx_vertical_outer_y / 2.0)
                        if tx_vertical_plane != "ZX":
                            raise ValueError("tx_vertical plane contract violation: expected ZX")
                        top_points = _map_xy_points_to_zx(
                            tx_vertical_points,
                            x_center=tx_vertical_center_x + transform["dx"] + off_x,
                            y_const=tx_vertical_center_y + transform["dy"] + off_y,
                            z_center=tx_vertical_center_z + transform["dz"] + off_z,
                        )
                    else:
                        assert base_points is not None
                        top_points = _translate_points(
                            base_points,
                            dx=board_x + transform["dx"] + off_x,
                            dy=board_y + transform["dy"] + off_y,
                            dz=board_z + transform["dz"] + off_z,
                        )
                    top_name = f"coil_{kind}_g{instance_index}_b{board_idx}_{design_id}"
                    top_created = modeler.create_polyline(
                        points=top_points,
                        name=top_name,
                        material="copper",
                        xsection_type="Rectangle",
                        xsection_width=trace, # type: ignore
                        xsection_height=cu_thickness, # type: ignore
                    )
                    if not top_created:
                        raise ValueError(
                            "tx_dd right polyline creation failed "
                            f"(name={top_name}, points={len(top_points)}, group_kind={kind})"
                        )
                    top_obj = cast(Object3d, top_created)
                    obj_name = _object_name(top_obj, top_name)
                    object_names.append(obj_name)
                    probe = _probe_cad_object(top_obj, top_name)
                    cad_probe.append(probe)
                    if kind == "rx_dd":
                        plane: Literal["XY", "YZ", "ZX"] = "YZ"
                    elif kind == "tx_vertical":
                        plane = "ZX"
                    else:
                        plane = "XY"
                    coil_plane_bboxes.append((pcb["id"], plane, probe["bbox"]))
                    if kind == "tx_vertical":
                        violations = _bbox_violations(
                            object_name=obj_name,
                            bbox=probe["bbox"],
                            region_kind="tx_region_vertical",
                            region_min=tx_vertical_region_min,
                            region_max=tx_vertical_region_max,
                        )
                    elif kind == "rx_dd":
                        violations = _bbox_violations(
                            object_name=obj_name,
                            bbox=probe["bbox"],
                            region_kind="rx_region_actual",
                            region_min=rx_region_min,
                            region_max=rx_region_max,
                        )
                    else:
                        violations = []
                    if violations:
                        placement_violations.extend(violations)
                        first = violations[0]
                        raise ValueError(
                            f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
                            f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
                        )
                    group_objects[kind].append(obj_name)

                    start_xyz = cast(_Point3, tuple(float(v) for v in top_points[0]))
                    end_xyz = cast(_Point3, tuple(float(v) for v in top_points[-1]))
                    side = _instance_side(kind, (off_x, off_y, off_z))
                    start_label: TerminalLabel = "A"
                    end_label: TerminalLabel = "a"
                    if kind == "rx_dd":
                        if side == "right":
                            start_label = "A"
                            end_label = "d"
                        elif side == "left":
                            start_label = "B"
                            end_label = "c"
                    group_endpoints.append(
                        {
                            "group_kind": kind,
                            "group_instance_index": instance_index,
                            "board_id": pcb["id"],
                            "start_xyz": start_xyz,
                            "end_xyz": end_xyz,
                            "start_label": start_label,
                            "end_label": end_label,
                            "present": True,
                        }
                    )
                    _append_rxdd_back_stub_sources_if_needed(
                        kind=kind,
                        board_id=pcb["id"],
                        instance_index=instance_index,
                        start_xyz=start_xyz,
                        end_xyz=end_xyz,
                        start_label=start_label,
                        end_label=end_label,
                        trace=trace,
                        source_object_name=obj_name,
                        storage=rxdd_back_stub_sources,
                    )
                    default_current_direction, b_field_direction = _build_polarity(kind, side)
                    expected_right_direction: Literal["cw", "ccw"] = "cw"
                    expected_left_direction: Literal["cw", "ccw"] = "ccw"
                    if kind == "rx_dd":
                        yz_projected = [[point[1], point[2], 0.0] for point in top_points]
                        current_direction = _current_direction_from_xy_points(yz_projected) or default_current_direction
                    else:
                        current_direction = _current_direction_from_xy_points(top_points) or default_current_direction
                    if kind == "rx_dd":
                        expected = expected_right_direction if side == "right" else expected_left_direction
                        if current_direction != expected:
                            raise ValueError(
                                "rx_dd current direction contract violation "
                                f"(instance_index={instance_index}, side={side}, actual={current_direction}, expected={expected})"
                            )
                    coil_polarity.append(
                        {
                            "group_kind": kind,
                            "group_instance_index": instance_index,
                            "board_id": pcb["id"],
                            "instance_side": side,
                            "current_direction": current_direction,
                            "b_field_direction": b_field_direction,
                        }
                    )
                    if kind == "tx_vertical":
                        y_center = (probe["bbox"][1] + probe["bbox"][4]) / 2.0
                        terminal_edge = _edge_points_at_tx_vertical_terminal(points=top_points, trace=trace)
                        opposite_terminal_edge = _edge_points_at_tx_vertical_opposite_terminal(points=top_points, trace=trace)
                        bridge_out_edge, bridge_in_edge = _tx_vertical_bridge_edges_from_node(
                            start_xyz=start_xyz,
                            end_xyz=end_xyz,
                            trace=trace,
                            tx_vertical_region_min=tx_vertical_region_min,
                            tx_vertical_region_max=tx_vertical_region_max,
                        )
                        right_key = (-y_center, pcb["id"], instance_index)
                        if (
                            tx_vertical_outer_right_selection_key is None
                            or right_key < tx_vertical_outer_right_selection_key
                        ):
                            tx_vertical_outer_right_selection_key = right_key
                            tx_vertical_global_outer_right_edge = terminal_edge
                        left_key = (y_center, pcb["id"], instance_index)
                        if (
                            tx_vertical_outer_left_selection_key is None
                            or left_key < tx_vertical_outer_left_selection_key
                        ):
                            tx_vertical_outer_left_selection_key = left_key
                            tx_vertical_global_outer_left_edge = opposite_terminal_edge
                        board_key: _BoardKey = (pcb["id"], board_idx)
                        board_nodes = tx_vertical_nodes_by_board.setdefault(board_key, [])
                        board_nodes.append(
                            (instance_index, obj_name, start_xyz, end_xyz, y_center, trace, bridge_out_edge, bridge_in_edge)
                        )

        object_names, fr4_object_names = finalize_solids_and_substrates(
            modeler=modeler,
            hfss=hfss,
            aedt_path=aedt_path,
            design_id=design_id,
            cu_thickness=cu_thickness,
            pcb_thickness=pcb_thickness,
            tx_board_ids=tx_board_ids,
            tx_vertical_nodes_by_board=tx_vertical_nodes_by_board,
            tx_vertical_region_min=tx_vertical_region_min,
            tx_vertical_region_max=tx_vertical_region_max,
            txdd_right_a_points=txdd_right_a_points,
            txdd_right_object_names=txdd_right_object_names,
            txdd_left_a_points=txdd_left_a_points,
            txdd_left_object_names=txdd_left_object_names,
            txdd_start_stub_sources=txdd_start_stub_sources,
            rxdd_back_stub_sources=rxdd_back_stub_sources,
            group_objects=group_objects,
            object_names=object_names,
            cad_probe=cad_probe,
            placement_violations=placement_violations,
            coil_plane_bboxes=coil_plane_bboxes,
            fr4_object_names=fr4_object_names,
            tx_zx_fr4_names=tx_zx_fr4_names,
            txdd_global_right_d_edge=txdd_global_right_d_edge,
            txdd_global_right_d_object_name=txdd_global_right_d_object_name,
            txdd_global_left_a_edge=txdd_global_left_a_edge,
            txdd_global_left_a_object_name=txdd_global_left_a_object_name,
            tx_vertical_global_outer_right_edge=tx_vertical_global_outer_right_edge,
            tx_vertical_global_outer_left_edge=tx_vertical_global_outer_left_edge,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to build geometry with Pyaedt: {exc}") from exc
    finally:
        try:
            hfss.release_desktop(close_projects=close_on_exit, close_desktop=close_on_exit)
        except Exception:
            pass

    eps = 1e-6
    debug_geometry = group_geometry_by_kind["tx_dd"]
    debug_turns = debug_geometry["turn_count_max"]
    debug_centerline_vertices = _build_rect_spiral_centerline_absolute(
        turns=debug_turns,
        outer_x=tx_dd_outer_x,
        outer_y=tx_dd_outer_y,
        trace=debug_geometry["trace"],
        gap=debug_geometry["gap"],
        z=0.0,
    )
    debug = _build_geometry_debug(
        centerline_vertices=debug_centerline_vertices,
        trace=debug_geometry["trace"],
        gap=debug_geometry["gap"],
        eps=eps,
        cad_probe=cad_probe,
        in_region_ok=len(placement_violations) == 0,
        violations=placement_violations,
    )

    pitch_max_delta = max((entry["delta"] for entry in debug["pitch_checks"]), default=0.0)
    axis_aligned = all(check["is_vertical"] or check["is_horizontal"] for check in debug["axis_checks"])
    top_probe = next((probe for probe in cad_probe if probe["object_name"].startswith("coil_")), None)
    top_bbox = top_probe["bbox"] if top_probe is not None else []
    print(f"[geometry] constraints_ok={debug['constraints_ok']}")
    print(f"[geometry] axis_aligned={axis_aligned} pitch_max_delta={pitch_max_delta:.9f}")
    print(f"[geometry] top_bbox={top_bbox}")
    _apply_txdd_right_endpoint_rule(group_endpoints, coil_polarity)

    em_ready_objects, em_endpoints, em_context = build_em_artifacts(
        selected=cast(dict[str, object], selected),
        object_names=object_names,
        group_objects=group_objects,
        group_endpoints=group_endpoints,
        scene_objects=scene_objects,
    )
    em_ready_objects["fr4_objects"] = sorted(fr4_object_names)
    em_policy: EmPolicy = default_em_policy()
    em_input: EmPipelineInput = {
        "ready_objects": em_ready_objects,
        "endpoints": em_endpoints,
        "context": em_context,
    }
    em_pipeline_result = run_em_pipeline(hfss, modeler, em_input, em_policy)

    metadata = _build_geometry_metadata(
        manifest=manifest,
        aedt_path=aedt_path,
        object_names=object_names,
        metadata_path=metadata_path,
        group_objects=group_objects,
        unite_groups={
            "tx": sorted(group_objects["tx_dd"] + group_objects["tx_vertical"]),
            "rx": sorted(group_objects["rx_dd"]),
        },
        group_endpoints=group_endpoints,
        coil_polarity=coil_polarity,
        em_ready_objects=em_ready_objects,
        em_endpoints=em_endpoints,
        em_context=em_context,
        em_policy=em_policy,
        em_pipeline_result=em_pipeline_result,
        scene_objects=scene_objects,
        debug=debug,
    )
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata

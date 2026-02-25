from __future__ import annotations

import math
from pathlib import Path
from typing import Literal, cast

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.types.manifest import (
    CadProbe,
    EmContext,
    EmEndpoints,
    EmReadyObjects,
    GroupEndpointEntry,
    GroupObjects,
    RegionViolation,
    SceneObjectEntry,
)

from .cad_probe import _object_name, _probe_cad_object
from .debug_checks import _bbox_violations


_Point3 = tuple[float, float, float]
_BoardKey = tuple[str, int]
_TxVerticalLinkNode = tuple[int, str, _Point3, _Point3, float, float]


def finalize_solids_and_substrates(
    *,
    modeler: Modeler3D,
    hfss: Hfss,
    aedt_path: Path,
    design_id: str,
    cu_thickness: float,
    pcb_thickness: float,
    tx_board_ids: set[str],
    tx_vertical_nodes_by_board: dict[_BoardKey, list[_TxVerticalLinkNode]],
    tx_vertical_region_min: _Point3,
    tx_vertical_region_max: _Point3,
    txdd_right_a_points: dict[int, tuple[_Point3, float]],
    txdd_right_object_names: dict[int, str],
    group_objects: GroupObjects,
    object_names: list[str],
    cad_probe: list[CadProbe],
    placement_violations: list[RegionViolation],
    coil_plane_bboxes: list[tuple[str, Literal["XY", "YZ", "ZX"], list[float]]],
    fr4_object_names: list[str],
    tx_zx_fr4_names: list[str],
) -> tuple[list[str], list[str]]:
    txdd_bridge_object_name: str | None = None
    for (board_id, board_idx), nodes in tx_vertical_nodes_by_board.items():
        if len(nodes) < 2:
            continue
        sorted_nodes = sorted(nodes, key=lambda node: node[4])
        for idx in range(len(sorted_nodes) - 1):
            (
                source_index,
                _source_name,
                source_start_xyz,
                source_end_xyz,
                _source_y_center,
                source_trace,
            ) = sorted_nodes[idx]
            (
                target_index,
                _target_name,
                target_start_xyz,
                target_end_xyz,
                _target_y_center,
                target_trace,
            ) = sorted_nodes[idx + 1]
            if abs(source_trace - target_trace) > 1e-9:
                raise ValueError(
                    "tx_vertical bridge trace mismatch between adjacent nodes "
                    f"(board_id={board_id}, source_index={source_index}, target_index={target_index}, "
                    f"source_trace={source_trace}, target_trace={target_trace})"
                )
            bridge_trace = source_trace
            x_margin = bridge_trace / 2.0
            min_x_allowed = tx_vertical_region_min[0] + x_margin
            max_x_allowed = tx_vertical_region_max[0] - x_margin
            if min_x_allowed > max_x_allowed:
                raise ValueError(
                    "tx_vertical bridge x-margin exceeds region width "
                    f"(min_x_allowed={min_x_allowed}, max_x_allowed={max_x_allowed}, bridge_trace={bridge_trace})"
                )
            half = bridge_trace / 2.0
            source_dx = source_end_xyz[0] - source_start_xyz[0]
            source_anchor_x = source_start_xyz[0] if abs(source_dx) <= 1e-9 else source_start_xyz[0] + math.copysign(half, source_dx)
            target_dx = target_start_xyz[0] - target_end_xyz[0]
            target_anchor_x = target_end_xyz[0] if abs(target_dx) <= 1e-9 else target_end_xyz[0] + math.copysign(half, target_dx)
            source_bridge_x = min(max(source_anchor_x, min_x_allowed), max_x_allowed)
            target_bridge_x = min(max(target_anchor_x, min_x_allowed), max_x_allowed)
            start_bridge_point = (source_bridge_x, source_start_xyz[1], source_start_xyz[2])
            end_bridge_point = (target_bridge_x, target_end_xyz[1], target_end_xyz[2])
            bridge_sheet_points = [
                [start_bridge_point[0], start_bridge_point[1], start_bridge_point[2] - half],
                [start_bridge_point[0], start_bridge_point[1], start_bridge_point[2] + half],
                [end_bridge_point[0], end_bridge_point[1], end_bridge_point[2] + half],
                [end_bridge_point[0], end_bridge_point[1], end_bridge_point[2] - half],
            ]
            bridge_name = f"bridge_tx_vertical_link_g{source_index}_to_g{target_index}_b{board_idx}_{design_id}"
            bridge_created = modeler.create_polyline(points=bridge_sheet_points, name=bridge_name, material="copper", close_surface=True)
            if not bridge_created:
                raise ValueError(
                    "tx_vertical bridge rectangle loop creation failed "
                    f"(name={bridge_name}, source_index={source_index}, target_index={target_index})"
                )
            bridge_loop_obj = cast(Object3d, bridge_created)
            bridge_loop_name = _object_name(bridge_loop_obj, bridge_name)
            try:
                covered = modeler.cover_lines(assignment=bridge_loop_name)  # type: ignore[misc]
            except TypeError:
                covered = modeler.cover_lines(bridge_loop_name)  # type: ignore[misc]
            if not covered:
                raise ValueError(
                    "tx_vertical bridge cover_lines failed "
                    f"(name={bridge_name}, source_index={source_index}, target_index={target_index})"
                )
            if isinstance(covered, list):
                first = covered[0] if covered else bridge_loop_name
                bridge_sheet_name = first if isinstance(first, str) else _object_name(cast(Object3d, first), bridge_loop_name)
            elif isinstance(covered, str):
                bridge_sheet_name = covered
            else:
                bridge_sheet_name = _object_name(cast(Object3d, covered), bridge_loop_name)
            try:
                thickened = modeler.thicken_sheet(assignment=bridge_sheet_name, thickness=(cu_thickness * 4.0))  # type: ignore[misc]
            except TypeError:
                thickened = modeler.thicken_sheet(bridge_sheet_name, (cu_thickness * 4.0))  # type: ignore[misc]
            if not thickened:
                raise ValueError("tx_vertical bridge thicken failed " f"(name={bridge_name}, thickness={cu_thickness * 4.0})")
            if isinstance(thickened, list):
                first = thickened[0] if thickened else bridge_sheet_name
                bridge_obj_name = first if isinstance(first, str) else _object_name(cast(Object3d, first), bridge_sheet_name)
                bridge_obj = cast(Object3d, bridge_loop_obj)
            elif isinstance(thickened, str):
                bridge_obj_name = thickened
                bridge_obj = cast(Object3d, bridge_loop_obj)
            else:
                bridge_obj = cast(Object3d, thickened)
                bridge_obj_name = _object_name(bridge_obj, bridge_sheet_name)
            object_names.append(bridge_obj_name)
            group_objects["tx_vertical"].append(bridge_obj_name)
            bridge_probe = _probe_cad_object(bridge_obj, bridge_name)
            cad_probe.append(bridge_probe)
            bridge_violations = _bbox_violations(
                object_name=bridge_obj_name,
                bbox=bridge_probe["bbox"],
                region_kind="tx_region_vertical",
                region_min=tx_vertical_region_min,
                region_max=tx_vertical_region_max,
            )
            if bridge_violations:
                placement_violations.extend(bridge_violations)
                first = bridge_violations[0]
                raise ValueError(
                    f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
                    f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
                )

    if 0 in txdd_right_a_points and 1 in txdd_right_a_points:
        lower_a, lower_trace = txdd_right_a_points[0]
        upper_a, upper_trace = txdd_right_a_points[1]
        if abs(lower_trace - upper_trace) > 1e-9:
            raise ValueError(
                "tx_dd layer bridge contract violation: lower/upper A trace must match "
                f"(lower_trace={lower_trace}, upper_trace={upper_trace})"
            )
        bridge_trace = lower_trace
        alignment_eps = 1e-6
        if abs(lower_a[0] - upper_a[0]) > alignment_eps or abs(lower_a[1] - upper_a[1]) > alignment_eps:
            raise ValueError(
                "tx_dd layer bridge contract violation: raw A anchors are not aligned "
                f"(lower_A={lower_a}, upper_A={upper_a})"
            )
        bridge_height = abs(upper_a[2] - lower_a[2])
        if bridge_height <= 1e-9:
            raise ValueError("tx_dd layer bridge contract violation: bridge height must be > 0")
        bridge_center_x = (lower_a[0] + upper_a[0]) / 2.0
        bridge_center_y = (lower_a[1] + upper_a[1]) / 2.0
        bridge_origin = [bridge_center_x - (bridge_trace / 2.0), bridge_center_y - (bridge_trace / 2.0), min(lower_a[2], upper_a[2])]
        bridge_sizes = [bridge_trace, bridge_trace, bridge_height]
        bridge_name = f"bridge_tx_dd_a_link_{design_id}"
        bridge_created = modeler.create_box(origin=bridge_origin, sizes=bridge_sizes, name=bridge_name, material="copper")
        if not bridge_created:
            raise ValueError("tx_dd layer bridge creation failed " f"(name={bridge_name}, origin={bridge_origin}, sizes={bridge_sizes})")
        bridge_obj = cast(Object3d, bridge_created)
        bridge_object_name = _object_name(bridge_obj, bridge_name)
        txdd_bridge_object_name = bridge_object_name
        object_names.append(bridge_object_name)
        group_objects["tx_dd"].append(bridge_object_name)
        cad_probe.append(_probe_cad_object(bridge_obj, bridge_name))

    if txdd_bridge_object_name is not None and 0 in txdd_right_object_names and 1 in txdd_right_object_names:
        txdd_unite_targets = [txdd_right_object_names[0], txdd_bridge_object_name, txdd_right_object_names[1]]
        try:
            unite_result = modeler.unite(assignment=txdd_unite_targets)  # type: ignore[misc]
        except TypeError:
            unite_result = modeler.unite(txdd_unite_targets)  # type: ignore[misc]
        if not unite_result:
            raise ValueError("Failed to unite tx_dd right-layer bridge group " f"(targets={txdd_unite_targets})")
        if isinstance(unite_result, list):
            first = unite_result[0] if unite_result else txdd_unite_targets[0]
            united_object_name = first if isinstance(first, str) else _object_name(cast(Object3d, first), txdd_unite_targets[0])
        elif isinstance(unite_result, str):
            united_object_name = unite_result
        else:
            united_object_name = _object_name(cast(Object3d, unite_result), txdd_unite_targets[0])
        group_objects["tx_dd"] = [name for name in group_objects["tx_dd"] if name not in txdd_unite_targets[1:]]
        if united_object_name not in group_objects["tx_dd"]:
            group_objects["tx_dd"].append(united_object_name)
        object_names = [name for name in object_names if name not in txdd_unite_targets[1:]]
        if united_object_name not in object_names:
            object_names.append(united_object_name)

    tx_vertical_unite_targets = sorted(set(group_objects["tx_vertical"]))
    if len(tx_vertical_unite_targets) > 1:
        try:
            tx_vertical_unite_result = modeler.unite(assignment=tx_vertical_unite_targets)  # type: ignore[misc]
        except TypeError:
            tx_vertical_unite_result = modeler.unite(tx_vertical_unite_targets)  # type: ignore[misc]
        if not tx_vertical_unite_result:
            raise ValueError("Failed to unite tx_vertical group " f"(targets={tx_vertical_unite_targets})")
        if isinstance(tx_vertical_unite_result, list):
            first = tx_vertical_unite_result[0] if tx_vertical_unite_result else tx_vertical_unite_targets[0]
            tx_vertical_united_name = first if isinstance(first, str) else _object_name(cast(Object3d, first), tx_vertical_unite_targets[0])
        elif isinstance(tx_vertical_unite_result, str):
            tx_vertical_united_name = tx_vertical_unite_result
        else:
            tx_vertical_united_name = _object_name(cast(Object3d, tx_vertical_unite_result), tx_vertical_unite_targets[0])
        group_objects["tx_vertical"] = [tx_vertical_united_name]
        object_names = [name for name in object_names if name not in tx_vertical_unite_targets[1:]]
        if tx_vertical_united_name not in object_names:
            object_names.append(tx_vertical_united_name)

    eps_len = 1e-6
    grouped_plane_bboxes: dict[tuple[str, Literal["XY", "YZ", "ZX"], int], list[float]] = {}
    for board_id, plane, bbox in coil_plane_bboxes:
        if len(bbox) < 6:
            continue
        if plane == "XY":
            axis_center = (bbox[2] + bbox[5]) / 2.0
            layer_key = int(round(axis_center / eps_len))
        elif plane == "YZ":
            axis_center = (bbox[0] + bbox[3]) / 2.0
            layer_key = int(round(axis_center / eps_len))
        else:
            axis_center = (bbox[1] + bbox[4]) / 2.0
            layer_key = int(round(axis_center / eps_len))
        key = (board_id, plane, layer_key)
        existing = grouped_plane_bboxes.get(key)
        if existing is None:
            grouped_plane_bboxes[key] = list(bbox[:6])
        else:
            existing[0] = min(existing[0], bbox[0])
            existing[1] = min(existing[1], bbox[1])
            existing[2] = min(existing[2], bbox[2])
            existing[3] = max(existing[3], bbox[3])
            existing[4] = max(existing[4], bbox[4])
            existing[5] = max(existing[5], bbox[5])

    for layer_idx, ((board_id, plane, _), bbox) in enumerate(sorted(grouped_plane_bboxes.items())):
        min_x, min_y, min_z, max_x, max_y, max_z = bbox
        span_x = max(max_x - min_x, eps_len)
        span_y = max(max_y - min_y, eps_len)
        span_z = max(max_z - min_z, eps_len)
        if plane == "XY":
            origin = [min_x, min_y, min_z - pcb_thickness]
            sizes = [span_x, span_y, pcb_thickness]
        elif plane == "YZ":
            origin = [min_x - pcb_thickness, min_y, min_z]
            sizes = [pcb_thickness, span_y, span_z]
        else:
            origin = [min_x, min_y - pcb_thickness, min_z]
            sizes = [span_x, pcb_thickness, span_z]

        substrate_name = f"fr4_{board_id}_{plane.lower()}_{layer_idx}_{design_id}"
        substrate = cast(Object3d, modeler.create_box(origin=origin, sizes=sizes, name=substrate_name, material="FR4_epoxy"))
        substrate_object_name = _object_name(substrate, substrate_name)
        object_names.append(substrate_object_name)
        fr4_object_names.append(substrate_object_name)
        if plane == "ZX" and board_id in tx_board_ids:
            tx_zx_fr4_names.append(substrate_object_name)
        cad_probe.append(_probe_cad_object(substrate, substrate_name))

    if len(tx_zx_fr4_names) > 1:
        tx_zx_fr4_targets = sorted(set(tx_zx_fr4_names))
        try:
            tx_zx_unite_result = modeler.unite(assignment=tx_zx_fr4_targets)  # type: ignore[misc]
        except TypeError:
            tx_zx_unite_result = modeler.unite(tx_zx_fr4_targets)  # type: ignore[misc]
        if not tx_zx_unite_result:
            raise ValueError("Failed to unite tx ZX FR4 group " f"(targets={tx_zx_fr4_targets})")
        if isinstance(tx_zx_unite_result, list):
            first = tx_zx_unite_result[0] if tx_zx_unite_result else tx_zx_fr4_targets[0]
            tx_zx_united_name = first if isinstance(first, str) else _object_name(cast(Object3d, first), tx_zx_fr4_targets[0])
        elif isinstance(tx_zx_unite_result, str):
            tx_zx_united_name = tx_zx_unite_result
        else:
            tx_zx_united_name = _object_name(cast(Object3d, tx_zx_unite_result), tx_zx_fr4_targets[0])
        fr4_object_names = [name for name in fr4_object_names if name not in tx_zx_fr4_targets[1:]]
        if tx_zx_united_name not in fr4_object_names:
            fr4_object_names.append(tx_zx_united_name)
        object_names = [name for name in object_names if name not in tx_zx_fr4_targets[1:]]
        if tx_zx_united_name not in object_names:
            object_names.append(tx_zx_united_name)

    copper_tools = sorted(set(group_objects["tx_dd"] + group_objects["tx_vertical"] + group_objects["rx_dd"]))
    if fr4_object_names and copper_tools:
        subtract_ok = modeler.subtract(blank_list=fr4_object_names, tool_list=copper_tools, keep_originals=True)
        if not subtract_ok:
            raise ValueError(
                "Failed to subtract copper solids from FR4 substrates "
                f"(fr4_count={len(fr4_object_names)}, copper_count={len(copper_tools)})"
            )

    hfss.save_project(str(aedt_path))
    return object_names, fr4_object_names


def build_em_artifacts(
    *,
    selected: dict[str, object],
    object_names: list[str],
    group_objects: GroupObjects,
    group_endpoints: list[GroupEndpointEntry],
    scene_objects: list[SceneObjectEntry],
) -> tuple[EmReadyObjects, EmEndpoints, EmContext]:
    em_ready_objects: EmReadyObjects = {
        "tx_conductors": sorted(group_objects["tx_dd"] + group_objects["tx_vertical"]),
        "rx_conductors": sorted(group_objects["rx_dd"]),
        "fr4_objects": [],
        "scene_bbox_source_objects": sorted([entry["name"] for entry in scene_objects]),
    }
    em_endpoints: EmEndpoints = {
        "tx": [entry for entry in group_endpoints if entry["group_kind"] in ("tx_dd", "tx_vertical")],
        "rx": [entry for entry in group_endpoints if entry["group_kind"] == "rx_dd"],
    }
    em_context: EmContext = {
        "dd_mirror_plane": selected["dd_mirror_plane"],
        "rx_plane": selected["rx_plane"],
        "tx_vertical_plane": selected["tx_vertical_plane"],
        "source": "type1_geometry",
        "object_names": sorted(object_names),
    }
    return em_ready_objects, em_endpoints, em_context

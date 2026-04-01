from __future__ import annotations

import math
from typing import Literal, cast

from peetsfea.aedt import Modeler3D
from peetsfea.aedt import Object3d
from peetsfea.identity.hashing import object_name_tag_from_design_id
from peetsfea.types.manifest import CadProbe, SceneObjectEntry

from ..build_state import (
    FinalizeInputs,
    GeometryBuildState,
    GeometryRuntimeContext,
    Point3,
    require_tx_dd_scene,
)
from .cad_probe import _probe_cad_object
from .debug_checks import _bbox_violations
from ..builders.finalize_types import FinalizePlan


def _bbox_corner_points(bbox: list[float]) -> list[Point3]:
    min_x, min_y, min_z, max_x, max_y, max_z = bbox[:6]
    return [
        (min_x, min_y, min_z),
        (min_x, min_y, max_z),
        (min_x, max_y, min_z),
        (min_x, max_y, max_z),
        (max_x, min_y, min_z),
        (max_x, min_y, max_z),
        (max_x, max_y, min_z),
        (max_x, max_y, max_z),
    ]


def _rotate_point_about_y(point: Point3, *, pivot: Point3, angle_rad: float) -> Point3:
    dx = point[0] - pivot[0]
    dz = point[2] - pivot[2]
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    return (
        pivot[0] + (cos_theta * dx) - (sin_theta * dz),
        point[1],
        pivot[2] + (sin_theta * dx) + (cos_theta * dz),
    )


def compute_tx_mode0_rotation_angle_rad(*, candidate_points: list[Point3], top_z: float, pivot: Point3) -> float:
    allowed_top_offset = top_z - pivot[2]
    if allowed_top_offset < 0.0:
        raise ValueError(
            "tx mode0 rotation requires non-negative top offset "
            f"(top_z={top_z}, pivot_z={pivot[2]})"
        )
    theta_limit = math.pi / 2.0
    eps = 1e-9
    for point in candidate_points:
        dx = point[0] - pivot[0]
        dz = point[2] - pivot[2]
        if dx < -eps or dz < -eps:
            raise ValueError(
                "tx mode0 rotation candidate point must not lie below pivot min_x/min_z "
                f"(point={point}, pivot={pivot})"
            )
        radius = math.hypot(dx, dz)
        if radius <= eps:
            continue
        if point[2] > (top_z + eps):
            raise ValueError(
                "tx mode0 rotation candidate point already exceeds tx_region_dd top "
                f"(point={point}, top_z={top_z})"
            )
        if allowed_top_offset >= (radius - eps):
            continue
        phase = math.atan2(dz, dx)
        point_theta_limit = math.asin(allowed_top_offset / radius) - phase
        if point_theta_limit < -eps:
            raise ValueError(
                "tx mode0 rotation cannot satisfy tx_region_dd top contract for candidate point "
                f"(point={point}, pivot={pivot}, top_z={top_z})"
            )
        theta_limit = min(theta_limit, max(0.0, point_theta_limit))
    return max(0.0, theta_limit)


def _tx_mode0_rotation_target_names(ctx: GeometryRuntimeContext, state: GeometryBuildState) -> list[str]:
    tx_ferrite_names = [name for name in state.group_objects["ferrite"] if name.startswith("ferrite_tx_")]
    tx_fr4_names = [name for name in state.fr4_object_names if any(board_id in name for board_id in ctx.tx_board_ids)]
    tx_object_names = state.group_objects["tx_dd"] + state.group_objects["tx_vertical"]
    live_target_names = [name for name in set(tx_object_names + tx_fr4_names + tx_ferrite_names) if name in state.object_names]
    return sorted(live_target_names)


def _tx_mode0_rotation_target_names_from_finalize_plan(plan: FinalizePlan) -> list[str]:
    tx_ferrite_names = [name for name in plan.group_objects["ferrite"] if name.startswith("ferrite_tx_")]
    tx_fr4_names = [name for name in plan.fr4_object_names if any(board_id in name for board_id in plan.tx_board_ids)]
    tx_object_names = plan.group_objects["tx_dd"] + plan.group_objects["tx_vertical"]
    live_target_names = [name for name in set(tx_object_names + tx_fr4_names + tx_ferrite_names) if name in plan.object_names]
    return sorted(live_target_names)


def _refresh_cad_probe_for_name(modeler: Modeler3D, *, object_name: str) -> CadProbe:
    raw_obj = modeler.get_object_from_name(object_name)
    return cast(CadProbe, _probe_cad_object(cast(Object3d, raw_obj)))


def _find_probe_name_by_bbox(
    *,
    probes: list[CadProbe],
    bbox: list[float],
    target_name_set: set[str],
) -> str:
    for probe in probes:
        if probe["object_name"] not in target_name_set:
            continue
        if probe["bbox"] == bbox:
            return probe["object_name"]
    raise ValueError(f"tx mode0 rotation could not resolve probe owner from bbox {bbox}")


def rotate_tx_mode0_objects_if_needed(
    ctx: GeometryRuntimeContext,
    state: GeometryBuildState,
    finalize_inputs: FinalizeInputs,
    modeler: Modeler3D,
) -> None:
    if ctx.tx_vertical_orientation_mode != 0:
        return
    _ = finalize_inputs
    tx_dd_scene = require_tx_dd_scene(ctx)
    target_names = _tx_mode0_rotation_target_names(ctx, state)
    state.tx_dd_rotation_object_names = list(target_names)
    if not target_names:
        state.tx_dd_rotation_angle_deg = 0.0
        state.tx_dd_rotation_pivot_xyz = (0.0, tx_dd_scene["center_y"], 0.0)
        return

    target_name_set = set(target_names)
    pre_rotation_probes = list(state.cad_probe)
    pre_rotation_tx_xy_bboxes = [
        entry for entry in state.coil_plane_bboxes if entry[0] in ctx.tx_board_ids and entry[1] == "XY"
    ]
    candidate_points: list[Point3] = []
    for probe in state.cad_probe:
        if probe["object_name"] not in target_name_set:
            continue
        candidate_points.extend(_bbox_corner_points(probe["bbox"]))
    for endpoint in state.group_endpoints:
        if endpoint["group_kind"] != "tx_dd":
            continue
        candidate_points.append(endpoint["start_xyz"])
        candidate_points.append(endpoint["end_xyz"])
    if not candidate_points:
        raise ValueError("tx mode0 rotation requires candidate points from tx_dd objects")

    pivot = (
        min(point[0] for point in candidate_points),
        tx_dd_scene["center_y"],
        min(point[2] for point in candidate_points),
    )
    angle_rad = compute_tx_mode0_rotation_angle_rad(
        candidate_points=candidate_points,
        top_z=tx_dd_scene["region_max"][2],
        pivot=pivot,
    )
    angle_deg = math.degrees(angle_rad)
    effective_angle_rad = -angle_rad
    effective_angle_deg = -angle_deg
    state.tx_dd_rotation_angle_deg = angle_deg
    state.tx_dd_rotation_pivot_xyz = pivot
    if angle_deg <= 1e-9:
        return

    cs_name = f"tx_mode0_rot_{object_name_tag_from_design_id(ctx.design_id)}"
    modeler.create_coordinate_system(
        origin=[pivot[0], pivot[1], pivot[2]],
        reference_cs="Global",
        name=cs_name,
        mode="axis",
        x_pointing=[1.0, 0.0, 0.0],
        y_pointing=[0.0, 1.0, 0.0],
    )
    modeler.set_working_coordinate_system(cs_name)
    try:
        modeler.rotate(assignment=target_names, axis="Y", angle=effective_angle_deg, units="deg")
    finally:
        modeler.set_working_coordinate_system("Global")

    refreshed_probe_by_name: dict[str, CadProbe] = {}
    for name in target_names:
        refreshed_probe_by_name[name] = _refresh_cad_probe_for_name(modeler, object_name=name)
    state.cad_probe = [
        refreshed_probe_by_name[probe["object_name"]] if probe["object_name"] in refreshed_probe_by_name else probe
        for probe in state.cad_probe
    ]

    state.group_endpoints = [
        {
            **endpoint,
            "start_xyz": _rotate_point_about_y(endpoint["start_xyz"], pivot=pivot, angle_rad=effective_angle_rad),
            "end_xyz": _rotate_point_about_y(endpoint["end_xyz"], pivot=pivot, angle_rad=effective_angle_rad),
        }
        if endpoint["group_kind"] == "tx_dd"
        else endpoint
        for endpoint in state.group_endpoints
    ]

    state.coil_plane_bboxes = [
        entry for entry in state.coil_plane_bboxes if not (entry[0] in ctx.tx_board_ids and entry[1] == "XY")
    ]
    for board_id, plane, bbox in pre_rotation_tx_xy_bboxes:
        object_name = _find_probe_name_by_bbox(
            probes=pre_rotation_probes,
            bbox=bbox,
            target_name_set=target_name_set,
        )
        assert object_name in refreshed_probe_by_name, f"tx mode0 rotated probe missing for {object_name}"
        state.coil_plane_bboxes.append((board_id, plane, refreshed_probe_by_name[object_name]["bbox"]))

    updated_scene_objects: list[SceneObjectEntry] = []
    for entry in state.scene_objects:
        if entry["kind"] == "tx_ferrite" and entry["name"] in refreshed_probe_by_name:
            probe_bbox = refreshed_probe_by_name[entry["name"]]["bbox"]
            updated_scene_objects.append(
                {
                    **entry,
                    "origin_xyz": (probe_bbox[0], probe_bbox[1], probe_bbox[2]),
                    "size_xyz": (
                        probe_bbox[3] - probe_bbox[0],
                        probe_bbox[4] - probe_bbox[1],
                        probe_bbox[5] - probe_bbox[2],
                    ),
                }
            )
            continue
        updated_scene_objects.append(entry)
    state.scene_objects = updated_scene_objects

    state.placement_violations = [
        entry for entry in state.placement_violations if entry["region_kind"] not in ("tx_region_dd", "tx_region_vertical")
    ]
    tx_dd_only_names = sorted(set(state.group_objects["tx_dd"]) - set(state.group_objects["tx_vertical"]))
    for object_name in tx_dd_only_names:
        assert object_name in refreshed_probe_by_name, f"tx mode0 rotated probe missing for {object_name}"
        violations = _bbox_violations(
            object_name=object_name,
            bbox=refreshed_probe_by_name[object_name]["bbox"],
            region_kind="tx_region_dd",
            region_min=tx_dd_scene["region_min"],
            region_max=tx_dd_scene["region_max"],
        )
        state.placement_violations.extend(violations)


def rotate_tx_mode0_plan_objects_if_needed(plan: FinalizePlan) -> None:
    if plan.tx_vertical_orientation_mode != 0:
        return
    target_names = _tx_mode0_rotation_target_names_from_finalize_plan(plan)
    plan.tx_dd_rotation_object_names[:] = list(target_names)
    if not target_names:
        plan.tx_dd_rotation_angle_deg = 0.0
        plan.tx_dd_rotation_pivot_xyz = (0.0, plan.tx_dd_center_y, 0.0)
        return

    target_name_set = set(target_names)
    candidate_points: list[Point3] = []
    for probe in plan.cad_probe:
        if probe["object_name"] not in target_name_set:
            continue
        candidate_points.extend(_bbox_corner_points(probe["bbox"]))
    if not candidate_points:
        raise ValueError("tx mode0 rotation requires candidate points from finalized tx objects")

    pivot = (
        min(point[0] for point in candidate_points),
        plan.tx_dd_center_y,
        min(point[2] for point in candidate_points),
    )
    angle_rad = compute_tx_mode0_rotation_angle_rad(
        candidate_points=candidate_points,
        top_z=plan.tx_dd_region_max[2],
        pivot=pivot,
    )
    plan.tx_dd_rotation_angle_deg = math.degrees(angle_rad)
    plan.tx_dd_rotation_pivot_xyz = pivot
    if math.degrees(angle_rad) <= 1e-9:
        return

    effective_angle_rad = -angle_rad
    effective_angle_deg = -math.degrees(angle_rad)
    cs_name = f"tx_mode0_rot_{object_name_tag_from_design_id(plan.design_id)}"
    plan.modeler.create_coordinate_system(
        origin=[pivot[0], pivot[1], pivot[2]],
        reference_cs="Global",
        name=cs_name,
        mode="axis",
        x_pointing=[1.0, 0.0, 0.0],
        y_pointing=[0.0, 1.0, 0.0],
    )
    plan.modeler.set_working_coordinate_system(cs_name)
    try:
        plan.modeler.rotate(assignment=target_names, axis="Y", angle=effective_angle_deg, units="deg")
    finally:
        plan.modeler.set_working_coordinate_system("Global")

    refreshed_probe_by_name: dict[str, CadProbe] = {}
    for name in target_names:
        refreshed_probe_by_name[name] = _refresh_cad_probe_for_name(plan.modeler, object_name=name)
    plan.cad_probe[:] = [
        refreshed_probe_by_name[probe["object_name"]] if probe["object_name"] in refreshed_probe_by_name else probe
        for probe in plan.cad_probe
    ]
    plan.placement_violations[:] = [
        entry for entry in plan.placement_violations if entry["region_kind"] not in ("tx_region_dd", "tx_region_vertical")
    ]
    tx_dd_only_names = sorted(set(plan.group_objects["tx_dd"]) - set(plan.group_objects["tx_vertical"]))
    for object_name in tx_dd_only_names:
        assert object_name in refreshed_probe_by_name, f"tx mode0 rotated probe missing for {object_name}"
        plan.placement_violations.extend(
            _bbox_violations(
                object_name=object_name,
                bbox=refreshed_probe_by_name[object_name]["bbox"],
                region_kind="tx_region_dd",
                region_min=plan.tx_dd_region_min,
                region_max=plan.tx_dd_region_max,
            )
        )

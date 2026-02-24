from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Literal, cast

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.backend.pyaedt.em_pipeline import default_em_policy, run_em_pipeline
from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput
from peetsfea.types.manifest import (
    AxisCheckEntry,
    CadProbe,
    CoilPolaritySpec,
    CornerDebugEntry,
    EmContext,
    EmEndpoints,
    EmPipelineResult,
    EmPolicy,
    EmReadyObjects,
    GeometryDebug,
    GeometryMetadata,
    GroupEndpointEntry,
    GroupGeometryParams,
    GroupObjects,
    Manifest,
    PitchCheckEntry,
    RegionViolation,
    SelectedParameters,
    SelectedParametersMax,
    SceneObjectEntry,
    UniteGroups,
)

_Point2 = tuple[float, float]
_Point3 = tuple[float, float, float]


def _build_rect_spiral_centerline_absolute(turns: int, outer_x: float, outer_y: float, trace: float, gap: float, z: float) -> list[_Point3]:
    if turns < 1:
        raise ValueError("turns must be >= 1")
    if trace <= 0:
        raise ValueError("trace must be > 0")
    if gap < 0:
        raise ValueError("gap must be >= 0")

    pitch = trace + gap
    half_trace = trace / 2.0

    left = -(outer_x / 2.0) + half_trace
    right = (outer_x / 2.0) - half_trace
    top = (outer_y / 2.0) - half_trace
    bottom = -(outer_y / 2.0) + half_trace

    if left >= right or bottom >= top:
        raise ValueError("centerline outer width must be > 0")

    points: list[_Point3] = []
    for turn_idx in range(turns):
        left_k = left + (turn_idx * pitch)
        right_k = right - (turn_idx * pitch)
        top_k = top - (turn_idx * pitch)
        bottom_k = bottom + (turn_idx * pitch)

        if left_k >= right_k or bottom_k >= top_k:
            raise ValueError("invalid spiral dimensions for requested turns")

        if turn_idx == 0:
            points.append((left_k, top_k, z))

        points.append((right_k, top_k, z))
        points.append((right_k, bottom_k, z))
        points.append((left_k, bottom_k, z))

        if turn_idx < turns - 1:
            next_top = top - ((turn_idx + 1) * pitch)
            next_left = left + ((turn_idx + 1) * pitch)
            points.append((left_k, next_top, z))
            points.append((next_left, next_top, z))

    return points


def _build_square_spiral_centerline_absolute(turns: int, outer: float, trace: float, gap: float, z: float) -> list[_Point3]:
    return _build_rect_spiral_centerline_absolute(turns=turns, outer_x=outer, outer_y=outer, trace=trace, gap=gap, z=z)


def _square_spiral_points(turns: int, outer: float, trace: float, gap: float, z: float) -> list[list[float]]:
    return [list(p) for p in _build_square_spiral_centerline_absolute(turns=turns, outer=outer, trace=trace, gap=gap, z=z)]


def _translate_points(points: list[list[float]], dx: float, dy: float, dz: float) -> list[list[float]]:
    return [[point[0] + dx, point[1] + dy, point[2] + dz] for point in points]


def _map_xy_points_to_yz(points: list[list[float]], *, x_const: float, y_center: float, z_center: float) -> list[list[float]]:
    return [[x_const, y_center + point[0], z_center + point[1]] for point in points]


def _map_xy_points_to_zx(points: list[list[float]], *, x_center: float, y_const: float, z_center: float) -> list[list[float]]:
    return [[x_center + point[0], y_const, z_center + point[1]] for point in points]


def _mirror_xy_points_about_x_axis(points: list[list[float]]) -> list[list[float]]:
    # Mirror around local X-axis (y -> -y) so paired DD coils have opposite winding.
    return [[point[0], -point[1], point[2]] for point in points]


def _bounds_from_scene_entry(entry: SceneObjectEntry) -> tuple[_Point3, _Point3]:
    ox, oy, oz = entry["origin_xyz"]
    sx, sy, sz = entry["size_xyz"]
    return (ox, oy, oz), (ox + sx, oy + sy, oz + sz)


def _bbox_violations(
    *,
    object_name: str,
    bbox: list[float],
    region_kind: Literal["tx_region_dd", "tx_region_vertical", "rx_region_actual"],
    region_min: _Point3,
    region_max: _Point3,
) -> list[RegionViolation]:
    if len(bbox) < 6:
        return []
    eps = 1e-9
    actual_min = (bbox[0], bbox[1], bbox[2])
    actual_max = (bbox[3], bbox[4], bbox[5])
    violations: list[RegionViolation] = []
    for idx, axis in enumerate(("x", "y", "z")):
        if actual_min[idx] < (region_min[idx] - eps):
            violations.append(
                {
                    "object_name": object_name,
                    "region_kind": region_kind,
                    "axis": cast(Literal["x", "y", "z"], axis),
                    "overflow_mm": region_min[idx] - actual_min[idx],
                    "actual_min": actual_min[idx],
                    "actual_max": actual_max[idx],
                    "region_min": region_min[idx],
                    "region_max": region_max[idx],
                }
            )
        if actual_max[idx] > (region_max[idx] + eps):
            violations.append(
                {
                    "object_name": object_name,
                    "region_kind": region_kind,
                    "axis": cast(Literal["x", "y", "z"], axis),
                    "overflow_mm": actual_max[idx] - region_max[idx],
                    "actual_min": actual_min[idx],
                    "actual_max": actual_max[idx],
                    "region_min": region_min[idx],
                    "region_max": region_max[idx],
                }
            )
    return violations


def _required_pair_spacing_mm(kind: Literal["tx_dd", "rx_dd"], outer_x: float, outer_y: float) -> float:
    if kind == "tx_dd":
        return outer_y
    return outer_x


def _tx_dd_center_y_and_layer(
    *,
    instance_count: int,
    instance_index: int,
    pair_clearance_mm: float,
    outer_y: float,
    region_center_y: float,
    region_min_y: float,
    region_max_y: float,
) -> tuple[float, int]:
    if instance_count not in (2, 4):
        raise ValueError(f"tx_dd selected_count must be 2 or 4 (actual={instance_count})")
    if instance_index < 0 or instance_index >= instance_count:
        raise ValueError(f"tx_dd instance index out of range: {instance_index}")

    half_outer_y = outer_y / 2.0
    pair_center_distance = outer_y + pair_clearance_mm
    half_center_distance = pair_center_distance / 2.0
    local_slot = instance_index % 2
    layer_index = 0 if instance_count == 2 else (instance_index // 2)
    sign = -1.0 if local_slot == 0 else 1.0
    center_y = region_center_y + (sign * half_center_distance)
    if (center_y - half_outer_y) < region_min_y or (center_y + half_outer_y) > region_max_y:
        raise ValueError(
            "tx_dd symmetric placement out of region "
            f"(pair_clearance_mm={pair_clearance_mm}, outer_y={outer_y}, "
            f"instance_index={instance_index}, region_min_y={region_min_y}, region_max_y={region_max_y})"
        )
    return center_y, layer_index


def _max_feasible_turns(outer: float, trace: float, gap: float) -> int:
    pitch = trace + gap
    if pitch <= 0:
        return 0
    raw = (outer + (2.0 * gap)) / (2.0 * pitch)
    max_turns = int(math.floor(raw - 1e-12))
    return max(0, max_turns)


def _rx_dd_center_offset_y(instance_index: int, instance_count: int, outer_x: float, edge_gap_mm: float) -> float:
    if instance_count < 1:
        raise ValueError("rx_dd selected_count must be >= 1")
    if edge_gap_mm < 0:
        raise ValueError(f"rx_dd edge gap must be >= 0 (actual={edge_gap_mm})")
    center = (instance_count - 1) / 2.0
    pair_center_distance = outer_x + edge_gap_mm
    return (instance_index - center) * pair_center_distance


def _coil_instance_offset(kind: str, instance_index: int, instance_count: int, spacing_mm: float) -> _Point3:
    if kind == "tx_vertical":
        if instance_count <= 1:
            return (0.0, 0.0, 0.0)
        delta = spacing_mm / float(instance_count - 1)
        start = -spacing_mm / 2.0
        # tx_vertical span is distributed along the ZX-plane normal (Y axis).
        return (0.0, start + (instance_index * delta), 0.0)
    return (0.0, 0.0, 0.0)


def _mount_allows_instance(mounts: list[str], kind: str, instance_index: int) -> bool:
    token_prefix = f"{kind}:"
    for mount in mounts:
        if not mount.startswith(token_prefix):
            continue
        selector = mount.split(":", 1)[1]
        if selector == "*":
            return True
        if selector.isdigit() and int(selector) == instance_index:
            return True
    return False


def _instance_side(kind: str, instance_offset: _Point3) -> Literal["left", "right", "center"]:
    if kind in ("tx_dd", "rx_dd"):
        if instance_offset[1] < 0:
            return "left"
        if instance_offset[1] > 0:
            return "right"
        return "center"
    return "center"


def _build_polarity(kind: str, side: Literal["left", "right", "center"]) -> tuple[Literal["cw", "ccw"], Literal["up", "down", "left", "right", "into_wall", "out_of_wall"]]:
    if kind == "tx_dd":
        if side == "right":
            return ("ccw", "up")
        if side == "left":
            return ("cw", "down")
        return ("ccw", "up")
    if kind == "tx_vertical":
        return ("ccw", "right")
    # rx_dd
    if side == "right":
        return ("cw", "into_wall")
    if side == "left":
        return ("ccw", "out_of_wall")
    return ("cw", "into_wall")


def _dd_instance_points(base_points: list[list[float]], *, mirror_winding: bool) -> list[list[float]]:
    if not mirror_winding:
        return base_points
    return _mirror_xy_points_about_x_axis(base_points)


def _create_non_model_box(
    modeler: Modeler3D,
    *,
    origin: list[float],
    sizes: list[float],
    name: str,
) -> Object3d:
    try:
        obj = cast(
            Object3d,
            modeler.create_box(
                origin=origin,
                sizes=sizes,
                name=name,
                material="vacuum",
                non_model=True,
            ),
        )
    except TypeError:
        obj = cast(
            Object3d,
            modeler.create_box(
                origin=origin,
                sizes=sizes,
                name=name,
                material="vacuum",
            ),
        )
    # Keep non-model semantics explicit even when backend APIs differ.
    try:
        setattr(obj, "model", False)
    except Exception:
        pass
    try:
        set_model_state = getattr(modeler, "set_object_model_state", None)
        if callable(set_model_state):
            object_name = getattr(obj, "name", name)
            set_model_state(object_name, False)
    except Exception:
        pass
    return obj


def _create_scene_non_model_objects(
    modeler: Modeler3D,
    design_id: str,
    selected: SelectedParameters,
    selected_max: SelectedParametersMax,
) -> tuple[list[str], list[CadProbe], list[SceneObjectEntry]]:
    def _assert_positive(value: float, path: str) -> None:
        if value <= 0:
            raise ValueError(f"{path} must be > 0")

    floor_x = float(selected["floor_size_x_mm"])
    floor_y = float(selected["floor_size_y_mm"])
    floor_t = float(selected["floor_thickness_mm"])
    wall_t = float(selected["wall_thickness_mm"])
    wall_y = float(selected["wall_size_y_mm"])
    wall_z = float(selected["wall_size_z_mm"])
    tv_w = float(selected["tv_width_mm"])
    tv_h = float(selected["tv_height_mm"])
    tv_t = float(selected["tv_thickness_mm"])
    tv_base_z = float(selected["tv_base_z_mm"])
    tx_w = float(selected["tx_region_outer_w_mm"])
    tx_h = float(selected["tx_region_outer_h_mm"])
    tx_t = float(selected["tx_region_thickness_mm"])
    tx_vertical_z = float(selected["tx_region_vertical_z_mm"])
    tx_dd_z = float(selected["tx_region_dd_z_mm"])
    rx_w = float(selected["rx_region_outer_w_mm"])
    rx_h = float(selected["rx_region_outer_h_mm"])
    rx_t = float(selected["rx_region_thickness_mm"])
    shelf_height = float(selected["shelf_height_mm"])
    shelf_min_size_x = float(selected["shelf_min_size_x_mm"])
    rx_region_bottom_from_tv = float(selected["rx_region_bottom_from_tv_mm"])
    tx_w_max = float(selected_max["tx_region_outer_w_mm"])
    tx_h_max = float(selected_max["tx_region_outer_h_mm"])
    tx_t_max = float(selected_max["tx_region_thickness_mm"])
    rx_w_max = float(selected_max["rx_region_outer_w_mm"])
    rx_h_max = float(selected_max["rx_region_outer_h_mm"])
    rx_t_max = float(selected_max["rx_region_thickness_mm"])

    _assert_positive(floor_x, "floor.size_x_mm")
    _assert_positive(floor_y, "floor.size_y_mm")
    _assert_positive(floor_t, "floor.thickness_mm")
    _assert_positive(wall_t, "wall.thickness_mm")
    _assert_positive(wall_y, "wall.size_y_mm")
    _assert_positive(wall_z, "wall.size_z_mm")
    _assert_positive(tv_w, "tv.width_mm")
    _assert_positive(tv_h, "tv.height_mm")
    _assert_positive(tv_t, "tv.thickness_mm")
    _assert_positive(tx_w, "tx.region.outer_w_mm")
    _assert_positive(tx_h, "tx.region.outer_h_mm")
    _assert_positive(tx_t, "tx.region.thickness_mm")
    _assert_positive(tx_vertical_z, "tx.region.z_parts.vertical_z_mm")
    _assert_positive(tx_dd_z, "tx.region.z_parts.dd_z_mm")
    _assert_positive(rx_w, "rx.region.outer_w_mm")
    _assert_positive(rx_h, "rx.region.outer_h_mm")
    _assert_positive(rx_t, "rx.region.thickness_mm")
    _assert_positive(tx_w_max, "tx.region.outer_w_mm(max)")
    _assert_positive(tx_h_max, "tx.region.outer_h_mm(max)")
    _assert_positive(tx_t_max, "tx.region.thickness_mm(max)")
    _assert_positive(rx_w_max, "rx.region.outer_w_mm(max)")
    _assert_positive(rx_h_max, "rx.region.outer_h_mm(max)")
    _assert_positive(rx_t_max, "rx.region.thickness_mm(max)")
    _assert_positive(shelf_height, "scene_anchor.shelf_height_mm")
    _assert_positive(shelf_min_size_x, "scene_anchor.shelf_min_size_x_mm")
    if rx_region_bottom_from_tv < 0:
        raise ValueError("scene_anchor.rx_region_bottom_from_tv_mm must be >= 0")

    if tx_w > tx_w_max or tx_h > tx_h_max or tx_t > tx_t_max:
        raise ValueError("tx.region actual dimensions must be <= max dimensions")
    if rx_w > rx_w_max or rx_h > rx_h_max or rx_t > rx_t_max:
        raise ValueError("rx.region actual dimensions must be <= max dimensions")
    tx_leftover_z = tx_t - tx_vertical_z - tx_dd_z
    if tx_leftover_z < 0:
        raise ValueError("tx.region.leftover_z_mm computed negative; reduce vertical_z/dd_z or increase tx.region.thickness_mm")

    tv_x = 0.0
    # TX region is independent from coil geometry and its bottom touches shelf top.
    tx_origin_x_max = 0.0
    tx_origin_y_max = -tx_h_max / 2.0
    tx_origin_z_max = shelf_height
    shelf_x = max(shelf_min_size_x, tx_w_max * 2.5)
    shelf_y = max(tv_w, tx_h_max)
    # RX region is independent from coil geometry and anchored inside the TV volume.
    rx_origin_x = 0.0
    rx_origin_y = -rx_w / 2.0
    rx_origin_z = tv_base_z + rx_region_bottom_from_tv
    rx_origin_y_max = -rx_w_max / 2.0
    rx_origin_z_max = tv_base_z + rx_region_bottom_from_tv

    # Bottom leftover is kept as free space; DD and vertical zones are contiguous above it.
    tx_dd_origin_z = tx_origin_z_max + tx_leftover_z
    tx_vertical_origin_z = tx_dd_origin_z + tx_dd_z

    scene_specs: list[
        tuple[
            str,
            Literal[
                "tv",
                "wall",
                "floor",
                "shelf",
                "tx_region_max",
                "tx_region_vertical",
                "tx_region_dd",
                "rx_region_max",
                "rx_region_actual",
            ],
            _Point3,
            _Point3,
            Literal["XY", "YZ"],
        ]
    ] = [
        (
            f"scene_floor_{design_id}",
            "floor",
            # Start from the ZY plane (x=0) and place floor below the XY plane.
            (0.0, -floor_y / 2.0, -floor_t),
            (floor_x, floor_y, floor_t),
            "XY",
        ),
        (
            f"scene_shelf_{design_id}",
            "shelf",
            # Shelf bottom touches floor top (z=0), shelf top is z=400.
            (0.0, -shelf_y / 2.0, 0.0),
            (shelf_x, shelf_y, shelf_height),
            "XY",
        ),
        (
            f"scene_wall_{design_id}",
            "wall",
            (-wall_t, -wall_y / 2.0, 0.0),
            (wall_t, wall_y, wall_z),
            "YZ",
        ),
        (
            f"scene_tv_{design_id}",
            "tv",
            (tv_x, -tv_w / 2.0, tv_base_z),
            (tv_t, tv_w, tv_h),
            "YZ",
        ),
        (
            f"scene_tx_region_max_{design_id}",
            "tx_region_max",
            (tx_origin_x_max, tx_origin_y_max, tx_origin_z_max),
            (tx_w_max, tx_h_max, tx_t_max),
            "XY",
        ),
        (
            f"scene_tx_region_vertical_{design_id}",
            "tx_region_vertical",
            (tx_origin_x_max, tx_origin_y_max, tx_vertical_origin_z),
            (tx_w_max, tx_h_max, tx_vertical_z),
            "XY",
        ),
        (
            f"scene_tx_region_dd_{design_id}",
            "tx_region_dd",
            (tx_origin_x_max, tx_origin_y_max, tx_dd_origin_z),
            (tx_w_max, tx_h_max, tx_dd_z),
            "XY",
        ),
        (
            f"scene_rx_region_max_{design_id}",
            "rx_region_max",
            (rx_origin_x, rx_origin_y_max, rx_origin_z_max),
            (rx_t_max, rx_w_max, rx_h_max),
            "YZ",
        ),
        (
            f"scene_rx_region_actual_{design_id}",
            "rx_region_actual",
            (rx_origin_x, rx_origin_y, rx_origin_z),
            (rx_t_max, rx_w, rx_h),
            "YZ",
        ),
    ]

    names: list[str] = []
    probes: list[CadProbe] = []
    entries: list[SceneObjectEntry] = []
    for name, kind, origin_xyz, size_xyz, plane in scene_specs:
        obj = _create_non_model_box(
            modeler,
            origin=[origin_xyz[0], origin_xyz[1], origin_xyz[2]],
            sizes=[size_xyz[0], size_xyz[1], size_xyz[2]],
            name=name,
        )
        obj_name = _object_name(obj, name)
        names.append(obj_name)
        probes.append(_probe_cad_object(obj, name))
        entries.append(
            {
                "name": obj_name,
                "kind": kind,
                "present": True,
                "origin_xyz": origin_xyz,
                "size_xyz": size_xyz,
                "plane": plane,
                "non_model": True,
            }
        )
    return names, probes, entries


def _create_hfss_session(manifest: Manifest, aedt_path: Path) -> Hfss:
    design_name = manifest["spec"]["design_name"]
    non_graphical = manifest["inputs"]["non_graphical"]
    return Hfss(project=str(aedt_path), design=design_name, non_graphical=non_graphical, new_desktop=True)


def _normalize_vector(dx: float, dy: float, eps: float) -> _Point2 | None:
    norm = math.hypot(dx, dy)
    if norm <= eps:
        return None
    return (dx / norm, dy / norm)


def _classify_corner(
    prev_xy: _Point2 | None,
    curr_xy: _Point2,
    next_xy: _Point2 | None,
    vertex_index: int,
    trace: float,
    eps: float,
) -> CornerDebugEntry:
    incoming_dir: _Point2 | None = None
    outgoing_dir: _Point2 | None = None

    if prev_xy is not None:
        incoming_dir = _normalize_vector(curr_xy[0] - prev_xy[0], curr_xy[1] - prev_xy[1], eps)
    if next_xy is not None:
        outgoing_dir = _normalize_vector(next_xy[0] - curr_xy[0], next_xy[1] - curr_xy[1], eps)

    if incoming_dir is None or outgoing_dir is None:
        return {
            "vertex_index": vertex_index,
            "xy": curr_xy,
            "corner_type": "endpoint",
            "incoming_dir": incoming_dir,
            "outgoing_dir": outgoing_dir,
            "offset_applied": None,
        }

    cross_z = (incoming_dir[0] * outgoing_dir[1]) - (incoming_dir[1] * outgoing_dir[0])
    if abs(cross_z) <= eps:
        corner_type: Literal["left_turn", "right_turn", "collinear", "endpoint"] = "collinear"
    elif cross_z > 0.0:
        corner_type = "left_turn"
    else:
        corner_type = "right_turn"

    half_trace = trace / 2.0
    left_normal_in = (-incoming_dir[1], incoming_dir[0])
    left_normal_out = (-outgoing_dir[1], outgoing_dir[0])
    offset = (
        half_trace * (left_normal_in[0] + left_normal_out[0]),
        half_trace * (left_normal_in[1] + left_normal_out[1]),
    )

    return {
        "vertex_index": vertex_index,
        "xy": curr_xy,
        "corner_type": corner_type,
        "incoming_dir": incoming_dir,
        "outgoing_dir": outgoing_dir,
        "offset_applied": offset,
    }


def _compute_axis_checks(vertices: list[_Point3], eps: float) -> list[AxisCheckEntry]:
    checks: list[AxisCheckEntry] = []
    for idx in range(len(vertices) - 1):
        x0, y0, _ = vertices[idx]
        x1, y1, _ = vertices[idx + 1]
        dx = x1 - x0
        dy = y1 - y0
        is_vertical = abs(dx) <= eps
        is_horizontal = abs(dy) <= eps
        checks.append(
            {
                "segment_index": idx,
                "start_xy": (x0, y0),
                "end_xy": (x1, y1),
                "is_vertical": is_vertical,
                "is_horizontal": is_horizontal,
                "x_constant": x0 if is_vertical else None,
                "y_constant": y0 if is_horizontal else None,
            }
        )
    return checks


def _compute_pitch_checks(vertices: list[_Point3], trace: float, gap: float, eps: float) -> list[PitchCheckEntry]:
    pitch_expected = trace + gap
    turns = (len(vertices) + 1) // 5
    checks: list[PitchCheckEntry] = []

    for turn_idx in range(turns - 1):
        base_curr = 5 * turn_idx
        base_next = 5 * (turn_idx + 1)
        lt_curr = vertices[base_curr]
        rt_curr = vertices[base_curr + 1]
        lb_curr = vertices[base_curr + 3]

        lt_next = vertices[base_next]
        rt_next = vertices[base_next + 1]
        lb_next = vertices[base_next + 3]

        deltas = [
            abs(lt_next[0] - lt_curr[0]),
            abs(rt_curr[0] - rt_next[0]),
            abs(lt_curr[1] - lt_next[1]),
            abs(lb_next[1] - lb_curr[1]),
        ]
        pitch_measured = sum(deltas) / len(deltas)
        checks.append(
            {
                "turn_index": turn_idx,
                "pitch_expected": pitch_expected,
                "pitch_measured": pitch_measured,
                "delta": abs(pitch_measured - pitch_expected),
            }
        )

        for value in deltas:
            if abs(value - pitch_expected) > eps:
                checks[-1]["delta"] = max(checks[-1]["delta"], abs(value - pitch_expected))

    return checks


def _validate_turn_box_consistency(vertices: list[_Point3], trace: float, gap: float, eps: float) -> bool:
    pitch = trace + gap
    turns = (len(vertices) + 1) // 5
    widths: list[float] = []
    heights: list[float] = []

    for turn_idx in range(turns):
        base = 5 * turn_idx
        lt = vertices[base]
        rt = vertices[base + 1]
        lb = vertices[base + 3]
        widths.append(rt[0] - lt[0])
        heights.append(lt[1] - lb[1])

        if abs(lt[0] + rt[0]) > eps:
            return False
        if abs(lt[1] + lb[1]) > eps:
            return False

    expected_delta = 2.0 * pitch
    for turn_idx in range(turns - 1):
        width_delta = widths[turn_idx] - widths[turn_idx + 1]
        height_delta = heights[turn_idx] - heights[turn_idx + 1]
        if abs(width_delta - expected_delta) > eps:
            return False
        if abs(height_delta - expected_delta) > eps:
            return False

    return True


def _point_xy(value: object) -> _Point2 | None:
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        x = value[0]
        y = value[1]
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            return (float(x), float(y))

    x_attr = getattr(value, "x", None)
    y_attr = getattr(value, "y", None)
    if isinstance(x_attr, (int, float)) and isinstance(y_attr, (int, float)):
        return (float(x_attr), float(y_attr))

    return None


def _extract_bbox(obj: Object3d) -> list[float]:
    for attr_name in ("bounding_box", "bbox"):
        attr = getattr(obj, attr_name, None)
        raw_bbox: object
        if callable(attr):
            try:
                raw_bbox = attr()
            except Exception:
                continue
        else:
            raw_bbox = attr

        if isinstance(raw_bbox, (tuple, list)) and len(raw_bbox) >= 6:
            values: list[float] = []
            for item in raw_bbox[:6]:
                if isinstance(item, (int, float)):
                    values.append(float(item))
            if len(values) == 6:
                return values

    return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def _extract_edge_samples_xy(obj: Object3d, limit: int = 8) -> list[_Point2]:
    samples: list[_Point2] = []
    edges = getattr(obj, "edges", None)
    if not isinstance(edges, list):
        return samples

    for edge in edges[:limit]:
        candidates = [
            getattr(edge, "midpoint", None),
            getattr(edge, "center", None),
            getattr(edge, "start", None),
            getattr(edge, "end", None),
        ]
        point: _Point2 | None = None
        for candidate in candidates:
            point = _point_xy(candidate)
            if point is not None:
                break

        if point is None:
            vertices = getattr(edge, "vertices", None)
            if isinstance(vertices, list) and vertices:
                point = _point_xy(vertices[0])

        if point is not None:
            samples.append(point)

    return samples


def _probe_cad_object(obj: Object3d, fallback_name: str) -> CadProbe:
    return {
        "object_name": _object_name(obj, fallback_name),
        "bbox": _extract_bbox(obj),
        "edge_samples_xy": _extract_edge_samples_xy(obj),
    }


def _build_geometry_debug(
    centerline_vertices: list[_Point3],
    trace: float,
    gap: float,
    eps: float,
    cad_probe: list[CadProbe],
    in_region_ok: bool,
    violations: list[RegionViolation],
) -> GeometryDebug:
    corners: list[CornerDebugEntry] = []
    for idx, point in enumerate(centerline_vertices):
        prev_xy = None if idx == 0 else (centerline_vertices[idx - 1][0], centerline_vertices[idx - 1][1])
        next_xy = None if idx == len(centerline_vertices) - 1 else (centerline_vertices[idx + 1][0], centerline_vertices[idx + 1][1])
        corners.append(
            _classify_corner(
                prev_xy=prev_xy,
                curr_xy=(point[0], point[1]),
                next_xy=next_xy,
                vertex_index=idx,
                trace=trace,
                eps=eps,
            )
        )

    axis_checks = _compute_axis_checks(centerline_vertices, eps)
    pitch_checks = _compute_pitch_checks(centerline_vertices, trace, gap, eps)

    axis_ok = all(check["is_vertical"] or check["is_horizontal"] for check in axis_checks)
    pitch_ok = all(check["delta"] <= eps for check in pitch_checks)
    symmetry_ok = _validate_turn_box_consistency(centerline_vertices, trace, gap, eps)

    return {
        "centerline_vertices": centerline_vertices,
        "corner_debug": corners,
        "axis_checks": axis_checks,
        "pitch_checks": pitch_checks,
        "cad_probe": cad_probe,
        "constraints_ok": axis_ok and pitch_ok and symmetry_ok,
        "in_region_ok": in_region_ok,
        "violations": violations,
        "eps": eps,
    }


def _build_geometry_metadata(
    manifest: Manifest,
    aedt_path: Path,
    object_names: list[str],
    metadata_path: Path,
    group_objects: GroupObjects,
    unite_groups: UniteGroups,
    group_endpoints: list[GroupEndpointEntry],
    coil_polarity: list[CoilPolaritySpec],
    em_ready_objects: EmReadyObjects,
    em_endpoints: EmEndpoints,
    em_context: EmContext,
    em_policy: EmPolicy,
    em_pipeline_result: EmPipelineResult,
    scene_objects: list[SceneObjectEntry],
    debug: GeometryDebug,
) -> GeometryMetadata:
    return {
        "design_id": manifest["design_id"],
        "design_unique_hash": manifest["design_unique_hash"],
        "toml_space_hash": manifest["toml_space_hash"],
        "toml_hash": manifest["toml_hash"],
        "peetsfea_commit": manifest["peetsfea_commit"],
        "seed": manifest["seed"],
        "retry_attempt": manifest["retry_attempt"],
        "retry_count": manifest["retry_count"],
        "repro_mode": manifest["repro_mode"],
        "selected_parameters": manifest["selected_parameters"],
        "selected_parameters_max": manifest["selected_parameters_max"],
        "selected_group_geometry": manifest["selected_group_geometry"],
        "aedt_path": str(aedt_path),
        "object_names": object_names,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "metadata_path": str(metadata_path),
        "anchor_mode": "copper_outer_edge_corner",
        "group_objects": group_objects,
        "unite_groups": unite_groups,
        "group_endpoints": group_endpoints,
        "coil_polarity": coil_polarity,
        "em_ready_objects": em_ready_objects,
        "em_endpoints": em_endpoints,
        "em_context": em_context,
        "em_policy": em_policy,
        "em_pipeline_result": em_pipeline_result,
        "scene_objects": scene_objects,
        "debug": debug,
    }


def _object_name(obj: Object3d, fallback: str) -> str:
    name = getattr(obj, "name", "")
    if isinstance(name, str) and name:
        return name
    return fallback


def _sanitize_var_name(name: str) -> str:
    chars: list[str] = []
    for ch in name:
        if ch.isalnum() or ch == "_":
            chars.append(ch)
        else:
            chars.append("_")
    return "".join(chars).strip("_")


def _var_expr(name: str, value: int | float | str) -> str:
    if isinstance(value, str):
        return value
    if name.endswith("_count") or name.endswith("turn_count_max") or name.endswith("requested_count") or name.endswith("selected_count"):
        return str(int(value))
    if name.endswith("_deg") or name.endswith("rotation_deg"):
        return f"{float(value)}deg"
    if name == "fr4_er":
        return str(float(value))
    return f"{float(value)}mm"


def _assign_design_variables(hfss: Hfss, manifest: Manifest) -> None:
    selected = manifest["selected_parameters"]
    for key, value in selected.items():
        if isinstance(value, (int, float)):
            hfss[_sanitize_var_name(f"spec_{key}")] = _var_expr(key, value)

    for group in manifest["selected_coil_groups"]:
        kind = group["kind"]
        hfss[_sanitize_var_name(f"group_{kind}_requested_count")] = _var_expr("requested_count", group["requested_count"])
        hfss[_sanitize_var_name(f"group_{kind}_selected_count")] = _var_expr("selected_count", group["selected_count"])
        hfss[_sanitize_var_name(f"group_{kind}_spacing_mm")] = _var_expr("spacing_mm", group["spacing_mm"])

    for geometry in manifest["selected_group_geometry"]:
        kind = geometry["kind"]
        hfss[_sanitize_var_name(f"group_geom_{kind}_turn_count_max")] = _var_expr("turn_count_max", geometry["turn_count_max"])
        hfss[_sanitize_var_name(f"group_geom_{kind}_band_ratio")] = _var_expr("band_ratio", geometry["band_ratio"])
        hfss[_sanitize_var_name(f"group_geom_{kind}_trace_mm")] = _var_expr("trace_mm", geometry["trace"])
        hfss[_sanitize_var_name(f"group_geom_{kind}_gap_mm")] = _var_expr("gap_mm", geometry["gap"])

    for pcb in manifest["selected_pcbs"]:
        pcb_id = _sanitize_var_name(pcb["id"])
        pos_x, pos_y, pos_z = pcb["position"]
        hfss[f"pcb_{pcb_id}_position_x_mm"] = _var_expr("position_x_mm", pos_x)
        hfss[f"pcb_{pcb_id}_position_y_mm"] = _var_expr("position_y_mm", pos_y)
        hfss[f"pcb_{pcb_id}_position_z_mm"] = _var_expr("position_z_mm", pos_z)
        hfss[f"pcb_{pcb_id}_rotation_deg"] = _var_expr("rotation_deg", pcb["rotation_deg"])
        hfss[f"pcb_{pcb_id}_present"] = "1" if pcb["present"] else "0"


def build_square_spiral_from_manifest(manifest: Manifest) -> GeometryMetadata:
    manifest["repro_mode"] = "manifest_json"
    selected = manifest["selected_parameters"]
    tx_dd_outer_x = selected["tx_dd_outer_x"]
    tx_dd_outer_y = selected["tx_dd_outer_y"]
    tx_vertical_outer_x = selected["tx_vertical_outer_x"]
    tx_vertical_outer_y = selected["tx_vertical_outer_y"]
    rx_dd_outer_x = selected["rx_dd_outer_x"]
    rx_dd_outer_y = selected["rx_dd_outer_y"]
    pcb_thickness = selected["pcb_thickness"]
    cu_thickness = selected["cu_thickness"]
    fr4_er = selected["fr4_er"]
    tx_dd_top_clearance = selected["tx_dd_top_clearance_mm"]
    rx_face_clearance = selected["rx_face_clearance_mm"]
    dd_mirror_plane = selected["dd_mirror_plane"]
    rx_plane = selected["rx_plane"]
    tx_vertical_plane = selected["tx_vertical_plane"]

    if pcb_thickness <= 0:
        raise ValueError("selected_parameters.pcb_thickness must be > 0")
    if cu_thickness <= 0:
        raise ValueError("selected_parameters.cu_thickness must be > 0")
    if fr4_er <= 1.0:
        raise ValueError("selected_parameters.fr4_er must be > 1.0")
    if tx_dd_top_clearance < 0:
        raise ValueError("selected_parameters.tx_dd_top_clearance_mm must be >= 0")
    if rx_face_clearance < 0:
        raise ValueError("selected_parameters.rx_face_clearance_mm must be >= 0")
    if dd_mirror_plane != "XZ":
        raise ValueError("selected_parameters.dd_mirror_plane must be 'XZ'")
    if rx_plane != "YZ":
        raise ValueError("selected_parameters.rx_plane must be 'YZ'")
    if tx_vertical_plane != "ZX":
        raise ValueError("selected_parameters.tx_vertical_plane must be 'ZX'")

    run_dir = Path(manifest["inputs"]["ansys_run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)

    design_id = manifest["design_id"]
    aedt_path = run_dir / f"{design_id}.aedt"
    metadata_path = run_dir / f"geometry_metadata_{design_id}.json"

    selected_groups = manifest["selected_coil_groups"]
    selected_group_geometry = manifest["selected_group_geometry"]
    selected_pcbs = manifest["selected_pcbs"]
    group_geometry_by_kind: dict[Literal["tx_dd", "tx_vertical", "rx_dd"], GroupGeometryParams] = {
        entry["kind"]: entry for entry in selected_group_geometry
    }
    missing_geometry = [kind for kind in ("tx_dd", "tx_vertical", "rx_dd") if kind not in group_geometry_by_kind]
    if missing_geometry:
        raise ValueError(f"Missing selected_group_geometry entries: {', '.join(missing_geometry)}")

    hfss = _create_hfss_session(manifest=manifest, aedt_path=aedt_path)
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
                effective_turns = turns
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
                    effective_turns = min(turns, max_turns)
                    if effective_turns < 1:
                        raise ValueError(
                            f"Invalid geometry for {kind}: cannot fit at least one turn on both X/Y axes "
                            f"(turns={turns}, trace={trace}, gap={gap})"
                        )
                    base_points = [
                        list(point)
                        for point in _build_rect_spiral_centerline_absolute(
                            turns=effective_turns,
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
                if kind == "rx_dd" and spacing_mm < 0:
                    raise ValueError(f"rx_dd edge gap must be >= 0 (actual={spacing_mm})")

                for instance_index in range(instance_count):
                    if not _mount_allows_instance(pcb["mounts"], kind, instance_index):
                        continue
                    off_x = 0.0
                    off_y = 0.0
                    off_z = 0.0
                    if kind == "tx_dd":
                        assert base_points is not None
                        tx_dd_instance_center_y, _ = _tx_dd_center_y_and_layer(
                            instance_count=instance_count,
                            instance_index=instance_index,
                            pair_clearance_mm=spacing_mm,
                            outer_y=tx_dd_outer_y,
                            region_center_y=tx_dd_center_y,
                            region_min_y=tx_dd_region_min[1],
                            region_max_y=tx_dd_region_max[1],
                        )
                        off_y = tx_dd_instance_center_y - tx_dd_center_y
                        tx_dd_local_slot = instance_index % 2
                        tx_dd_points = _dd_instance_points(base_points, mirror_winding=(tx_dd_local_slot == 0))
                        tx_dd_anchor_z = tx_dd_region_max[2] - tx_dd_top_clearance - cu_thickness
                        top_points = _translate_points(
                            tx_dd_points,
                            dx=tx_dd_center_x + transform["dx"],
                            dy=tx_dd_instance_center_y + transform["dy"],
                            dz=tx_dd_anchor_z - board_z + transform["dz"] + off_z,
                        )
                    elif kind == "rx_dd":
                        assert base_points is not None
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
                        rx_dd_points = _dd_instance_points(base_points, mirror_winding=(off_y < 0.0))
                        translated_xy = _translate_points(
                            rx_dd_points,
                            dx=0.0,
                            dy=0.0,
                            dz=0.0,
                        )
                        top_points = _map_xy_points_to_yz(
                            translated_xy,
                            x_const=rx_anchor_x + transform["dx"] + off_x,
                            y_center=rx_center_y + transform["dy"] + off_y,
                            z_center=rx_center_z + transform["dz"] + off_z,
                        )
                    elif kind == "tx_vertical":
                        off_x, off_y, off_z = _coil_instance_offset(kind, instance_index, instance_count, spacing_mm)
                        tx_vertical_zone_h = tx_vertical_region_max[2] - tx_vertical_region_min[2]
                        tx_vertical_outer_y = min(tx_vertical_outer_y, tx_vertical_zone_h)
                        tx_vertical_turns = min(
                            turns,
                            _max_feasible_turns(tx_vertical_outer_x, trace, gap),
                            _max_feasible_turns(tx_vertical_outer_y, trace, gap),
                        )
                        if tx_vertical_turns < 1:
                            raise ValueError(
                                "tx_vertical cannot fit in tx_region_vertical "
                                f"(available_outer_x={tx_vertical_outer_x}, available_outer_y={tx_vertical_outer_y})"
                            )
                        tx_vertical_points = [
                            list(point)
                            for point in _build_rect_spiral_centerline_absolute(
                                turns=tx_vertical_turns,
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
                    top_obj = cast(
                        Object3d,
                        modeler.create_polyline(
                            points=top_points,
                            name=top_name,
                            material="copper",
                            xsection_type="Rectangle",
                            xsection_width=trace, # type: ignore
                            xsection_height=cu_thickness, # type: ignore
                        ),
                    )
                    obj_name = _object_name(top_obj, top_name)
                    object_names.append(obj_name)
                    probe = _probe_cad_object(top_obj, top_name)
                    cad_probe.append(probe)
                    if kind == "tx_dd":
                        plane: Literal["XY", "YZ", "ZX"] = "XY"
                    elif kind == "rx_dd":
                        plane = "YZ"
                    else:
                        plane = "ZX"
                    coil_plane_bboxes.append((pcb["id"], plane, probe["bbox"]))
                    if kind == "tx_dd":
                        violations = _bbox_violations(
                            object_name=obj_name,
                            bbox=probe["bbox"],
                            region_kind="tx_region_dd",
                            region_min=tx_dd_region_min,
                            region_max=tx_dd_region_max,
                        )
                    elif kind == "tx_vertical":
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
                    group_endpoints.append(
                        {
                            "group_kind": kind,
                            "group_instance_index": instance_index,
                            "board_id": pcb["id"],
                            "start_xyz": start_xyz,
                            "end_xyz": end_xyz,
                            "present": True,
                        }
                    )
                    side = _instance_side(kind, (off_x, off_y, off_z))
                    current_direction, b_field_direction = _build_polarity(kind, side)
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

        eps_len = 1e-6
        grouped_plane_bboxes: dict[tuple[str, Literal["XY", "YZ", "ZX"], int], list[float]] = {}
        for board_id, plane, bbox in coil_plane_bboxes:
            if len(bbox) < 6:
                continue
            if plane == "XY":
                axis_center = (bbox[2] + bbox[5]) / 2.0
            elif plane == "YZ":
                axis_center = (bbox[0] + bbox[3]) / 2.0
            else:  # ZX
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
            else:  # ZX
                origin = [min_x, min_y - pcb_thickness, min_z]
                sizes = [span_x, pcb_thickness, span_z]

            substrate_name = f"fr4_{board_id}_{plane.lower()}_{layer_idx}_{design_id}"
            substrate = cast(
                Object3d,
                modeler.create_box(
                    origin=origin,
                    sizes=sizes,
                    name=substrate_name,
                    material="FR4_epoxy",
                ),
            )
            substrate_object_name = _object_name(substrate, substrate_name)
            object_names.append(substrate_object_name)
            fr4_object_names.append(substrate_object_name)
            cad_probe.append(_probe_cad_object(substrate, substrate_name))

        hfss.save_project(str(aedt_path))
    except Exception as exc:
        raise RuntimeError(f"Failed to build geometry with Pyaedt: {exc}") from exc
    finally:
        try:
            hfss.release_desktop(close_projects=close_on_exit, close_desktop=close_on_exit)
        except Exception:
            pass

    eps = 1e-6
    debug_geometry = group_geometry_by_kind["tx_dd"]
    debug_turns = min(
        debug_geometry["turn_count_max"],
        _max_feasible_turns(tx_dd_outer_x, debug_geometry["trace"], debug_geometry["gap"]),
        _max_feasible_turns(tx_dd_outer_y, debug_geometry["trace"], debug_geometry["gap"]),
    )
    if debug_turns < 1:
        debug_turns = 1
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

    em_ready_objects: EmReadyObjects = {
        "tx_conductors": sorted(group_objects["tx_dd"] + group_objects["tx_vertical"]),
        "rx_conductors": sorted(group_objects["rx_dd"]),
        "fr4_objects": sorted(fr4_object_names),
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

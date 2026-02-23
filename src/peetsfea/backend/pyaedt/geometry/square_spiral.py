from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Literal, cast

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.types.manifest import (
    AxisCheckEntry,
    CadProbe,
    CoilPolaritySpec,
    CornerDebugEntry,
    GeometryDebug,
    GeometryMetadata,
    GroupEndpointEntry,
    GroupObjects,
    Manifest,
    PitchCheckEntry,
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


def _coil_instance_offset(kind: str, instance_index: int, instance_count: int, spacing_mm: float) -> _Point3:
    if kind in ("tx_dd", "rx_dd"):
        center = (instance_count - 1) / 2.0
        return ((instance_index - center) * spacing_mm, 0.0, 0.0)
    if kind == "tx_vertical":
        if instance_count <= 1:
            return (0.0, 0.0, 0.0)
        delta = spacing_mm / float(instance_count - 1)
        start = -spacing_mm / 2.0
        return (0.0, 0.0, start + (instance_index * delta))
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
        if instance_offset[0] < 0:
            return "left"
        if instance_offset[0] > 0:
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
    debug: GeometryDebug,
) -> GeometryMetadata:
    return {
        "design_id": manifest["design_id"],
        "design_unique_hash": manifest["design_unique_hash"],
        "toml_space_hash": manifest["toml_space_hash"],
        "toml_hash": manifest["toml_hash"],
        "peetsfea_commit": manifest["peetsfea_commit"],
        "seed": manifest["seed"],
        "selected_parameters": manifest["selected_parameters"],
        "aedt_path": str(aedt_path),
        "object_names": object_names,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "metadata_path": str(metadata_path),
        "anchor_mode": "copper_outer_edge_corner",
        "group_objects": group_objects,
        "unite_groups": unite_groups,
        "group_endpoints": group_endpoints,
        "coil_polarity": coil_polarity,
        "debug": debug,
    }


def _object_name(obj: Object3d, fallback: str) -> str:
    name = getattr(obj, "name", "")
    if isinstance(name, str) and name:
        return name
    return fallback


def build_square_spiral_from_manifest(manifest: Manifest) -> GeometryMetadata:
    selected = manifest["selected_parameters"]
    turns = selected["turn_count_max"]
    outer_x = selected["outer_x"]
    outer_y = selected["outer_y"]
    trace = selected["trace"]
    gap = selected["gap"]
    pcb_thickness = selected["pcb_thickness"]
    cu_thickness = selected["cu_thickness"]
    fr4_er = selected["fr4_er"]

    if turns < 1:
        raise ValueError("selected_parameters.turns must be >= 1")
    if trace <= 0:
        raise ValueError("selected_parameters.trace must be > 0")
    if gap < 0:
        raise ValueError("selected_parameters.gap must be >= 0")
    if pcb_thickness <= 0:
        raise ValueError("selected_parameters.pcb_thickness must be > 0")
    if cu_thickness <= 0:
        raise ValueError("selected_parameters.cu_thickness must be > 0")
    if fr4_er <= 1.0:
        raise ValueError("selected_parameters.fr4_er must be > 1.0")

    inner_width_x = outer_x - (2.0 * turns * trace) - (2.0 * (turns - 1) * gap)
    inner_width_y = outer_y - (2.0 * turns * trace) - (2.0 * (turns - 1) * gap)
    if inner_width_x <= 0 or inner_width_y <= 0:
        raise ValueError("Invalid geometry: inner width must be > 0 on both X/Y axes")

    run_dir = Path(manifest["inputs"]["ansys_run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)

    design_id = manifest["design_id"]
    aedt_path = run_dir / f"{design_id}.aedt"
    metadata_path = run_dir / f"geometry_metadata_{design_id}.json"

    centerline_vertices = _build_rect_spiral_centerline_absolute(
        turns=turns,
        outer_x=outer_x,
        outer_y=outer_y,
        trace=trace,
        gap=gap,
        z=0.0,
    )
    base_points = [list(point) for point in centerline_vertices]
    selected_groups = manifest["selected_coil_groups"]
    selected_pcbs = manifest["selected_pcbs"]

    hfss = _create_hfss_session(manifest=manifest, aedt_path=aedt_path)
    modeler = cast(Modeler3D, hfss.modeler)

    close_on_exit = manifest["inputs"]["close_on_exit"]
    object_names: list[str] = []
    cad_probe: list[CadProbe] = []
    group_objects: GroupObjects = {"tx_dd": [], "tx_vertical": [], "rx_dd": []}
    group_endpoints: list[GroupEndpointEntry] = []
    coil_polarity: list[CoilPolaritySpec] = []

    try:
        for board_idx, pcb in enumerate(selected_pcbs):
            if not pcb["present"]:
                continue

            board_x, board_y, board_z = pcb["position"]
            substrate_name = f"fr4_b{board_idx}_{design_id}"
            substrate = cast(
                Object3d,
                modeler.create_box(
                    origin=[board_x - (outer_x / 2.0), board_y - (outer_y / 2.0), board_z - pcb_thickness],
                    sizes=[outer_x, outer_y, pcb_thickness],
                    name=substrate_name,
                    material="FR4_epoxy",
                ),
            )
            object_names.append(_object_name(substrate, substrate_name))
            cad_probe.append(_probe_cad_object(substrate, substrate_name))

            for group in selected_groups:
                kind = group["kind"]
                instance_count = group["selected_count"]
                spacing_mm = group["spacing_mm"]
                transforms = group["instance_transforms"]
                transform = transforms[0] if transforms else {"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0}

                for instance_index in range(instance_count):
                    if not _mount_allows_instance(pcb["mounts"], kind, instance_index):
                        continue
                    off_x, off_y, off_z = _coil_instance_offset(kind, instance_index, instance_count, spacing_mm)
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
                    cad_probe.append(_probe_cad_object(top_obj, top_name))
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

        hfss.save_project(str(aedt_path))
    except Exception as exc:
        raise RuntimeError(f"Failed to build geometry with Pyaedt: {exc}") from exc
    finally:
        try:
            hfss.release_desktop(close_projects=close_on_exit, close_desktop=close_on_exit)
        except Exception:
            pass

    eps = 1e-6
    debug = _build_geometry_debug(
        centerline_vertices=centerline_vertices,
        trace=trace,
        gap=gap,
        eps=eps,
        cad_probe=cad_probe,
    )

    pitch_max_delta = max((entry["delta"] for entry in debug["pitch_checks"]), default=0.0)
    axis_aligned = all(check["is_vertical"] or check["is_horizontal"] for check in debug["axis_checks"])
    top_probe = next((probe for probe in cad_probe if probe["object_name"].startswith("coil_")), None)
    top_bbox = top_probe["bbox"] if top_probe is not None else []
    print(f"[geometry] constraints_ok={debug['constraints_ok']}")
    print(f"[geometry] axis_aligned={axis_aligned} pitch_max_delta={pitch_max_delta:.9f}")
    print(f"[geometry] top_bbox={top_bbox}")

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
        debug=debug,
    )
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata

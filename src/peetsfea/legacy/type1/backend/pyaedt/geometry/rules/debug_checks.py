from __future__ import annotations

import math
from typing import Literal, cast


from peetsfea.types.manifest import AxisCheckEntry, CadProbe, CornerDebugEntry, GeometryDebug, PitchCheckEntry, RegionViolation

_Point2 = tuple[float, float]
_Point3 = tuple[float, float, float]

def _bbox_violations(
    *,
    object_name: str,
    bbox: list[float],
    region_kind: Literal["tx_region_dd", "tx_region_vertical", "rx_region_actual"],
    region_min: _Point3,
    region_max: _Point3,
) -> list[RegionViolation]:
    if len(bbox) < 6:
        raise ValueError(f"{region_kind} bbox must contain at least 6 values for {object_name}")
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


def _normalize_vector(dx: float, dy: float, eps: float) -> _Point2:
    norm = math.hypot(dx, dy)
    if norm <= eps:
        raise ValueError("cannot normalize zero-length vector")
    return (dx / norm, dy / norm)


def _classify_endpoint_corner(
    curr_xy: _Point2,
    vertex_index: int,
) -> CornerDebugEntry:
    return {
        "vertex_index": vertex_index,
        "xy": curr_xy,
        "corner_type": "endpoint",
        "incoming_dir": None,
        "outgoing_dir": None,
        "offset_applied": None,
    }


def _classify_internal_corner(
    prev_xy: _Point2,
    curr_xy: _Point2,
    next_xy: _Point2,
    vertex_index: int,
    trace: float,
    eps: float,
) -> CornerDebugEntry:
    incoming_dir = _normalize_vector(curr_xy[0] - prev_xy[0], curr_xy[1] - prev_xy[1], eps)
    outgoing_dir = _normalize_vector(next_xy[0] - curr_xy[0], next_xy[1] - curr_xy[1], eps)

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
        if idx == 0 or idx == len(centerline_vertices) - 1:
            corners.append(_classify_endpoint_corner(curr_xy=(point[0], point[1]), vertex_index=idx))
        else:
            corners.append(
                _classify_internal_corner(
                    prev_xy=(centerline_vertices[idx - 1][0], centerline_vertices[idx - 1][1]),
                    curr_xy=(point[0], point[1]),
                    next_xy=(centerline_vertices[idx + 1][0], centerline_vertices[idx + 1][1]),
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

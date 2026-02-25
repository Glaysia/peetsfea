from __future__ import annotations

import math
from typing import Literal, cast

from peetsfea.types.manifest import (
    CoilPolaritySpec,
    GroupEndpointEntry,
    GroupGeometryParams,
    Manifest,
    RegionViolation,
    ResolvedPcbInstance,
    ResolvedPcbMount,
    SceneObjectEntry,
    TerminalLabel,
)

from .debug_checks import _compute_pitch_checks
from .spiral_points import _build_rect_spiral_centerline_absolute, _translate_points

_Point2 = tuple[float, float]
_Point3 = tuple[float, float, float]
_GroupInstanceKey = tuple[str, str, int]

def _axis_aligned_segments_intersect_2d(a0: _Point2, a1: _Point2, b0: _Point2, b1: _Point2, eps: float) -> bool:
    ax0, ay0 = a0
    ax1, ay1 = a1
    bx0, by0 = b0
    bx1, by1 = b1
    a_vertical = abs(ax0 - ax1) <= eps
    b_vertical = abs(bx0 - bx1) <= eps
    if a_vertical and b_vertical:
        if abs(ax0 - bx0) > eps:
            return False
        a_min, a_max = sorted((ay0, ay1))
        b_min, b_max = sorted((by0, by1))
        return max(a_min, b_min) <= (min(a_max, b_max) + eps)
    if (not a_vertical) and (not b_vertical):
        if abs(ay0 - by0) > eps:
            return False
        a_min, a_max = sorted((ax0, ax1))
        b_min, b_max = sorted((bx0, bx1))
        return max(a_min, b_min) <= (min(a_max, b_max) + eps)
    if a_vertical:
        v_x = ax0
        v_min, v_max = sorted((ay0, ay1))
        h_y = by0
        h_min, h_max = sorted((bx0, bx1))
    else:
        v_x = bx0
        v_min, v_max = sorted((by0, by1))
        h_y = ay0
        h_min, h_max = sorted((ax0, ax1))
    return (h_min - eps) <= v_x <= (h_max + eps) and (v_min - eps) <= h_y <= (v_max + eps)


def _find_txdd_right_inner_c_index(base_points: list[list[float]]) -> int:
    bottom_right_candidates = [
        (idx, abs(point[0]), abs(point[1]))
        for idx, point in enumerate(base_points)
        if point[0] > 0.0 and point[1] < 0.0
    ]
    if not bottom_right_candidates:
        raise ValueError("tx_dd right endpoint contract violation: cannot locate inner bottom-right anchor for c->A")
    min_abs_x = min(candidate[1] for candidate in bottom_right_candidates)
    min_x_candidates = [candidate for candidate in bottom_right_candidates if abs(candidate[1] - min_abs_x) <= 1e-9]
    min_abs_y = min(candidate[2] for candidate in min_x_candidates)
    min_xy_candidates = [candidate for candidate in min_x_candidates if abs(candidate[2] - min_abs_y) <= 1e-9]
    return max(candidate[0] for candidate in min_xy_candidates)


def _validate_txdd_right_points(
    points: list[list[float]],
    *,
    trace: float,
    gap: float,
) -> None:
    if len(points) < 2:
        raise ValueError("tx_dd right endpoint contract violation: generated centerline is too short")
    eps = 1e-9
    for idx in range(len(points) - 1):
        p0 = points[idx]
        p1 = points[idx + 1]
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        if abs(dx) <= eps and abs(dy) <= eps:
            raise ValueError("tx_dd right endpoint contract violation: zero-length segment generated")
        if abs(dx) > eps and abs(dy) > eps:
            raise ValueError("tx_dd right endpoint contract violation: non-axis-aligned segment generated")
    for idx in range(1, len(points) - 1):
        p_prev = points[idx - 1]
        p_curr = points[idx]
        p_next = points[idx + 1]
        vx1 = p_curr[0] - p_prev[0]
        vy1 = p_curr[1] - p_prev[1]
        vx2 = p_next[0] - p_curr[0]
        vy2 = p_next[1] - p_curr[1]
        if abs(vx1 + vx2) <= eps and abs(vy1 + vy2) <= eps:
            raise ValueError("tx_dd right endpoint contract violation: immediate backtracking segment generated")
    segments: list[tuple[_Point2, _Point2]] = [
        ((points[idx][0], points[idx][1]), (points[idx + 1][0], points[idx + 1][1]))
        for idx in range(len(points) - 1)
    ]
    for idx in range(len(segments)):
        for jdx in range(idx + 1, len(segments)):
            if jdx <= idx + 1:
                continue
            a0, a1 = segments[idx]
            b0, b1 = segments[jdx]
            if _axis_aligned_segments_intersect_2d(a0, a1, b0, b1, eps):
                raise ValueError(
                    "tx_dd right endpoint contract violation: non-adjacent self-crossing segment generated"
                )
    tuple_points = [cast(_Point3, (float(p[0]), float(p[1]), float(p[2]))) for p in points]
    pitch_checks = _compute_pitch_checks(tuple_points, trace=trace, gap=gap, eps=1e-6)
    if any(check["delta"] > 1e-6 for check in pitch_checks):
        raise ValueError("tx_dd right endpoint contract violation: pitch consistency check failed")


def _required_pair_spacing_mm(kind: Literal["tx_dd", "rx_dd"], outer_x: float, outer_y: float) -> float:
    if kind == "tx_dd":
        return outer_y
    return outer_x


def _validate_rxdd_single_layer_count(instance_count: int) -> None:
    if instance_count != 2:
        raise ValueError(
            "rx_dd single-layer contract violation: only selected_count=2 is supported "
            f"(actual={instance_count})"
        )


def _build_rxdd_right_points_a_to_D_cw(
    *,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
) -> list[list[float]]:
    points = [
        list(point)
        for point in _build_rect_spiral_centerline_absolute(
            turns=turns,
            outer_x=outer_x,
            outer_y=outer_y,
            trace=trace,
            gap=gap,
            z=0.0,
        )
    ]
    direction = _current_direction_from_xy_points(points)
    if direction != "cw":
        raise ValueError(
            "rx_dd right endpoint contract violation: a->D path must be clockwise "
            f"(actual_direction={direction})"
        )
    return points


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


def _coil_instance_offset(
    kind: str,
    instance_index: int,
    instance_count: int,
    spacing_mm: float,
    *,
    trace_mm: float | None = None,
) -> _Point3:
    if kind == "tx_vertical":
        if instance_count <= 0:
            raise ValueError(f"tx_vertical selected_count must be >= 1 (actual={instance_count})")
        if instance_index < 0 or instance_index >= instance_count:
            raise ValueError(
                f"tx_vertical instance index out of range (instance_index={instance_index}, instance_count={instance_count})"
            )
        denom = max(1, instance_count - 1)
        d = spacing_mm / float(denom)
        if d < 0.0:
            raise ValueError(f"tx_vertical center gap d must be >= 0 (actual={d})")
        if instance_count % 2 == 0:
            # Even count: centers follow +-d/2, +-3d/2, ... around X-axis.
            center = (instance_count - 1) / 2.0
            return (0.0, (float(instance_index) - center) * d, 0.0)
        edge_half_thickness = (trace_mm / 2.0) if trace_mm is not None else 0.0
        mid = instance_count // 2
        rel = instance_index - mid
        if rel == 0:
            # Odd count: middle copper outer edge touches the X-axis.
            return (0.0, edge_half_thickness, 0.0)
        sign = -1.0 if rel < 0 else 1.0
        return (0.0, sign * (abs(rel) * d), 0.0)
    return (0.0, 0.0, 0.0)


def _mount_allows_instance(mounts: list[ResolvedPcbMount], kind: str, instance_index: int) -> bool:
    for mount in mounts:
        if mount["kind"] != kind:
            continue
        selector_mode = mount["selector_mode"]
        selector_index = mount["selector_index"]
        if selector_mode == "all":
            return True
        if selector_mode == "index" and selector_index == instance_index:
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


def _group_endpoint_key(entry: GroupEndpointEntry) -> _GroupInstanceKey:
    return (entry["group_kind"], entry["board_id"], entry["group_instance_index"])


def _coil_polarity_key(entry: CoilPolaritySpec) -> _GroupInstanceKey:
    return (entry["group_kind"], entry["board_id"], entry["group_instance_index"])


def _endpoint_z_center(entry: GroupEndpointEntry) -> float:
    return (entry["start_xyz"][2] + entry["end_xyz"][2]) / 2.0


def _current_direction_from_xy_points(points: list[list[float]], *, eps: float = 1e-9) -> Literal["cw", "ccw"] | None:
    if len(points) < 3:
        return None
    for idx in range(1, len(points) - 1):
        vx1 = points[idx][0] - points[idx - 1][0]
        vy1 = points[idx][1] - points[idx - 1][1]
        vx2 = points[idx + 1][0] - points[idx][0]
        vy2 = points[idx + 1][1] - points[idx][1]
        cross = (vx1 * vy2) - (vy1 * vx2)
        if abs(cross) <= eps:
            continue
        return "ccw" if cross > 0.0 else "cw"
    return None


def _extend_endpoints(points: list[list[float]], *, extension: float) -> list[list[float]]:
    if extension <= 0.0 or len(points) < 2:
        return [point[:] for point in points]

    extended = [point[:] for point in points]
    start = extended[0]
    start_next = extended[1]
    start_dx = start[0] - start_next[0]
    start_dy = start[1] - start_next[1]
    start_dz = start[2] - start_next[2]
    start_len = math.sqrt((start_dx * start_dx) + (start_dy * start_dy) + (start_dz * start_dz))
    if start_len > 0.0:
        start[0] += (start_dx / start_len) * extension
        start[1] += (start_dy / start_len) * extension
        start[2] += (start_dz / start_len) * extension

    end = extended[-1]
    end_prev = extended[-2]
    end_dx = end[0] - end_prev[0]
    end_dy = end[1] - end_prev[1]
    end_dz = end[2] - end_prev[2]
    end_len = math.sqrt((end_dx * end_dx) + (end_dy * end_dy) + (end_dz * end_dz))
    if end_len > 0.0:
        end[0] += (end_dx / end_len) * extension
        end[1] += (end_dy / end_len) * extension
        end[2] += (end_dz / end_len) * extension

    return extended


def _apply_txdd_right_endpoint_rule(
    group_endpoints: list[GroupEndpointEntry],
    coil_polarity: list[CoilPolaritySpec],
) -> None:
    endpoint_by_key = {_group_endpoint_key(entry): entry for entry in group_endpoints}

    right_candidates: list[tuple[float, str, int, _GroupInstanceKey]] = []
    for polarity_entry in coil_polarity:
        if polarity_entry["group_kind"] != "tx_dd" or polarity_entry["instance_side"] != "right":
            continue
        key = _coil_polarity_key(polarity_entry)
        endpoint_entry = endpoint_by_key.get(key)
        if endpoint_entry is None:
            continue
        right_candidates.append(
            (
                _endpoint_z_center(endpoint_entry),
                polarity_entry["board_id"],
                polarity_entry["group_instance_index"],
                key,
            )
        )

    if not right_candidates:
        return
    # Single-layer tx_dd (selected_count=2) always uses the right endpoint path C->d.
    # In this topology, every right instance index is 1, even if multiple boards contribute.
    if all(candidate[2] == 1 for candidate in right_candidates):
        for _, _, _, key in right_candidates:
            endpoint_entry = endpoint_by_key[key]
            endpoint_entry["start_label"] = "C"
            endpoint_entry["end_label"] = "d"
        return
    if len(right_candidates) > 2:
        raise ValueError(
            "tx_dd right endpoint contract violation: expected 1 or 2 right candidates "
            f"(actual={len(right_candidates)})"
        )

    right_candidates.sort(key=lambda item: (item[0], item[1], item[2]))

    def _set_labels(key: _GroupInstanceKey, start_label: TerminalLabel, end_label: TerminalLabel) -> None:
        endpoint_entry = endpoint_by_key[key]
        endpoint_entry["start_label"] = start_label
        endpoint_entry["end_label"] = end_label

    if len(right_candidates) == 1:
        _set_labels(right_candidates[0][3], "C", "d")
        return

    # Lower layer first by Z center, then deterministic key tie-break.
    _set_labels(right_candidates[0][3], "c", "A")
    _set_labels(right_candidates[1][3], "A", "d")


def _txdd_right_points(
    *,
    turns: int,
    outer_x: float,
    outer_y: float,
    trace: float,
    gap: float,
    instance_count: int,
    layer_index: int | None,
) -> list[list[float]]:
    base = [
        list(point)
        for point in _build_rect_spiral_centerline_absolute(
            turns=turns,
            outer_x=outer_x,
            outer_y=outer_y,
            trace=trace,
            gap=gap,
            z=0.0,
        )
    ]
    if instance_count == 2:
        # Single layer right: C -> d.
        points = base[2:]
        if len(points) < 2:
            raise ValueError("tx_dd right endpoint contract violation: C->d path is too short")
        _validate_txdd_right_points(points, trace=trace, gap=gap)
        return points
    if instance_count != 4:
        raise ValueError(f"tx_dd selected_count must be 2 or 4 for right endpoint rule (actual={instance_count})")
    if layer_index not in (0, 1):
        raise ValueError(f"tx_dd right endpoint rule requires layer index 0 or 1 (actual={layer_index})")
    if layer_index == 0:
        # Lower layer right: c -> A.
        c_index = _find_txdd_right_inner_c_index(base)
        points = [point[:] for point in reversed(base[: c_index + 1])]
        if len(points) < 2:
            raise ValueError("tx_dd right endpoint contract violation: c->A path is too short")
        _validate_txdd_right_points(points, trace=trace, gap=gap)
        return points
    # Upper layer right: A -> D -> ... -> d.
    mirrored_x = [[-point[0], point[1], point[2]] for point in base]
    outer_a = base[0]
    a_index = next(
        (
            idx
            for idx, point in enumerate(mirrored_x)
            if abs(point[0] - outer_a[0]) <= 1e-9 and abs(point[1] - outer_a[1]) <= 1e-9
        ),
        None,
    )
    if a_index is None:
        raise ValueError("tx_dd right endpoint contract violation: cannot locate outer A anchor for A->D->...->d")
    rotated = mirrored_x[a_index:] + mirrored_x[:a_index]
    c_index = _find_txdd_right_inner_c_index(rotated)
    d_index = c_index - 1
    if d_index < 1:
        raise ValueError("tx_dd right endpoint contract violation: A->D->...->d path is too short")
    points = [point[:] for point in rotated[: d_index + 1]]
    _validate_txdd_right_points(points, trace=trace, gap=gap)
    return points


def _txdd_right_layer_rank_by_z(
    *,
    selected_pcbs: list[ResolvedPcbInstance],
    instance_count: int,
    transform_dz: float,
    tx_dd_anchor_z: float,
) -> dict[int, int]:
    if instance_count != 4:
        return {}
    rows: list[tuple[float, str, int]] = []
    for instance_index in range(instance_count):
        if instance_index % 2 == 0:
            continue
        candidates: list[tuple[str, float]] = []
        for pcb in selected_pcbs:
            if not pcb["present"]:
                continue
            mounts = pcb["mounts"]
            if _mount_allows_instance(mounts, "tx_dd", instance_index):
                board_id = pcb["id"]
                board_z = pcb["position"][2]
                final_z = tx_dd_anchor_z - board_z + transform_dz
                candidates.append((board_id, final_z))
        if len(candidates) != 1:
            raise ValueError(
                "tx_dd right endpoint contract violation: each right instance must map to exactly one mounted board "
                f"(instance_index={instance_index}, candidates={len(candidates)})"
            )
        board_id, z_center = candidates[0]
        rows.append((z_center, board_id, instance_index))
    if len(rows) != 2:
        raise ValueError(
            "tx_dd right endpoint contract violation: expected exactly 2 right instances for selected_count=4 "
            f"(actual={len(rows)})"
        )
    rows.sort(key=lambda item: (item[0], item[1], item[2]))
    return {
        rows[0][2]: 0,  # lower z -> c->A
        rows[1][2]: 1,  # upper z -> A->d
    }

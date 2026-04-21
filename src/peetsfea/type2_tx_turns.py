"""Deterministic TX turn allocation helpers for type2 coil columns."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Literal

TxConnectionMode = Literal[0, 1]
Point3 = tuple[float, float, float]
_UNBOUNDED_MAX_TURN_COUNT = 1_000_000_000
_DISTANCE_GROUP_DECIMALS = 12


def _validated_real(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, float | int):
        raise ValueError(f"{name} must be a real number (actual={value!r})")
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise ValueError(f"{name} must be finite (actual={value!r})")
    return numeric_value


def _validated_point3(name: str, value: Sequence[float]) -> Point3:
    if len(value) != 3:
        raise ValueError(f"{name} must contain 3 values (actual={value!r})")
    return (
        _validated_real(f"{name}[0]", value[0]),
        _validated_real(f"{name}[1]", value[1]),
        _validated_real(f"{name}[2]", value[2]),
    )


def _validated_coil_centers(coil_centers_xyz: Sequence[Point3]) -> tuple[Point3, ...]:
    if len(coil_centers_xyz) < 1:
        raise ValueError("coil_centers_xyz must contain at least 1 entry")
    centers: list[Point3] = []
    for index, center in enumerate(coil_centers_xyz):
        if len(center) != 3:
            raise ValueError(f"coil center must be a 3D tuple (index={index}, actual={center!r})")
        x_value = _validated_real(f"coil_centers_xyz[{index}].x", center[0])
        y_value = _validated_real(f"coil_centers_xyz[{index}].y", center[1])
        z_value = _validated_real(f"coil_centers_xyz[{index}].z", center[2])
        centers.append((x_value, y_value, z_value))
    return tuple(centers)


def normalized_tx_plane_distances(coil_centers_xyz: Sequence[Point3], *, rx_center_xyz: Sequence[float]) -> tuple[float, ...]:
    """Return normalized TX-plane (XY) distances preserving input coil order."""
    centers = _validated_coil_centers(coil_centers_xyz)
    rx_center = _validated_point3("rx_center_xyz", rx_center_xyz)
    distances = tuple(math.hypot(center[0] - rx_center[0], center[1] - rx_center[1]) for center in centers)
    max_distance = max(distances)
    if max_distance == 0.0:
        return tuple(0.0 for _ in centers)
    return tuple(distance / max_distance for distance in distances)


def _distance_group_key(distance: float) -> float:
    return round(distance, _DISTANCE_GROUP_DECIMALS)


def _group_indices_by_distance(distances: tuple[float, ...]) -> tuple[tuple[float, tuple[int, ...]], ...]:
    grouped: dict[float, list[int]] = {}
    for index, distance in enumerate(distances):
        group_key = _distance_group_key(distance)
        if group_key in grouped:
            grouped[group_key].append(index)
        else:
            grouped[group_key] = [index]
    grouped_items = sorted(grouped.items(), key=lambda item: (item[0], item[1][0]))
    return tuple((distance, tuple(indices)) for distance, indices in grouped_items)


def _allocate_turns(
    *,
    coil_count: int,
    distances: tuple[float, ...],
    weights: tuple[float, ...],
    target_turn_count: int,
    base_turn_count: int,
    max_turn_count: int,
) -> tuple[int, ...]:
    if len(distances) != coil_count:
        raise RuntimeError(f"distance length mismatch (coil_count={coil_count}, distances={len(distances)})")
    if len(weights) != coil_count:
        raise RuntimeError(f"weights length mismatch (coil_count={coil_count}, weights={len(weights)})")
    if target_turn_count < coil_count:
        raise RuntimeError(
            f"target_turn_count must be >= coil_count (target_turn_count={target_turn_count}, coil_count={coil_count})"
        )

    turns = [base_turn_count] * coil_count
    target_extra_turns = target_turn_count - coil_count
    if target_extra_turns == 0:
        return tuple(turns)

    group_definitions = _group_indices_by_distance(distances)
    group_count = len(group_definitions)
    assert group_count >= 1

    group_distances: list[float] = []
    group_indices: list[tuple[int, ...]] = []
    group_sizes: list[int] = []
    group_weight_totals: list[float] = []
    for distance, indices in group_definitions:
        group_distances.append(distance)
        group_indices.append(indices)
        group_sizes.append(len(indices))
        group_weight = weights[indices[0]] * float(len(indices))
        group_weight_totals.append(group_weight)

    total_weight = sum(group_weight_totals)
    if total_weight <= 0.0:
        raise ValueError("sum(turn_weights) must be > 0 for any valid allocation")

    exact_group_extra_totals = tuple(
        (target_extra_turns * (group_weight / total_weight)) for group_weight in group_weight_totals
    )
    base_group_extra = tuple(
        int(math.floor(value / float(group_size)))
        for value, group_size in zip(exact_group_extra_totals, group_sizes, strict=True)
    )
    next_increment_errors = tuple(
        (float(base_value + 1) * float(group_size)) - exact_value
        for exact_value, base_value, group_size in zip(
            exact_group_extra_totals,
            base_group_extra,
            group_sizes,
            strict=True,
        )
    )

    turns_added_by_group = 0
    for group_index, extra in enumerate(base_group_extra):
        assigned_turn = base_turn_count + extra
        if assigned_turn > max_turn_count:
            raise ValueError(
                "distance group allocation exceeds geometry turn cap "
                f"(group_index={group_index}, distance={group_distances[group_index]}, "
                f"turns={assigned_turn}, max_turn_count={max_turn_count})"
            )
        turns_added_by_group += extra * group_sizes[group_index]
        for index in group_indices[group_index]:
            turns[index] = assigned_turn

    remaining_turns = target_extra_turns - turns_added_by_group
    if remaining_turns <= 0:
        return tuple(turns)

    order = sorted(
        range(group_count),
        key=lambda index: (
            next_increment_errors[index],
            -group_weight_totals[index],
            group_distances[index],
            group_indices[index][0],
        ),
    )
    while remaining_turns > 0:
        made_progress = False
        for group_index in order:
            indices = group_indices[group_index]
            next_turn = turns[indices[0]] + 1
            if next_turn > max_turn_count:
                continue
            made_progress = True
            for index in indices:
                turns[index] = next_turn
            remaining_turns -= group_sizes[group_index]
            if remaining_turns <= 0:
                break
        if not made_progress:
            raise ValueError(
                "cannot satisfy target_turn_count without cap overflow "
                f"(target_turn_count={target_turn_count}, max_turn_count={max_turn_count})"
            )

    total_allocated = sum(turns)
    if total_allocated < target_turn_count:
        raise RuntimeError(
            "turn allocation underflow "
            f"(sum={total_allocated}, target_turn_count={target_turn_count})"
        )
    for coil_index, turn_count in enumerate(turns):
        if turn_count > max_turn_count:
            raise ValueError(
                "distance-group allocation exceeds per-coil max_turn_count "
                f"(coil_index={coil_index}, turns={turn_count}, max_turn_count={max_turn_count})"
            )
    return tuple(turns)


def turn_weights(
    coil_centers_xyz: Sequence[Point3],
    *,
    rx_center_xyz: Sequence[float],
    a: float,
    b: float,
    c: float,
) -> tuple[float, ...]:
    """Return polynomial weights w_i = a + b*d_i + c*d_i^2 for normalized TX-plane distance."""
    coeff_a = _validated_real("turn_weight_a", a)
    coeff_b = _validated_real("turn_weight_b", b)
    coeff_c = _validated_real("turn_weight_c", c)
    distance_values = normalized_tx_plane_distances(coil_centers_xyz, rx_center_xyz=rx_center_xyz)
    for value in distance_values:
        if value < 0.0:
            raise ValueError("normalized TX-plane distances must be non-negative")
    weights = tuple(coeff_a + (coeff_b * x_value) + (coeff_c * x_value * x_value) for x_value in distance_values)
    for index, weight in enumerate(weights):
        if not (weight > 0.0):
            raise ValueError(
                "turn_weight polynomial must be > 0 for all coil centers "
                f"(index={index}, weight={weight})"
            )
    return weights


def allocate_series_turns(
    coil_centers_xyz: Sequence[Point3],
    *,
    rx_center_xyz: Sequence[float],
    series_total_turn_count: int,
    turn_weight_a: float,
    turn_weight_b: float,
    turn_weight_c: float,
    max_turn_count: int = _UNBOUNDED_MAX_TURN_COUNT,
) -> tuple[int, ...]:
    """Allocate series turns with distance-group allocation."""
    if isinstance(series_total_turn_count, bool) or not isinstance(series_total_turn_count, int):
        raise ValueError(
            "series_total_turn_count must be an integer "
            f"(actual={series_total_turn_count!r})"
        )
    if series_total_turn_count < 1:
        raise ValueError(f"series_total_turn_count must be >= 1 (actual={series_total_turn_count})")
    if isinstance(max_turn_count, bool) or not isinstance(max_turn_count, int):
        raise ValueError(f"max_turn_count must be an integer (actual={max_turn_count!r})")
    if max_turn_count < 1:
        raise ValueError(f"max_turn_count must be >= 1 (actual={max_turn_count})")

    distances = normalized_tx_plane_distances(coil_centers_xyz, rx_center_xyz=rx_center_xyz)
    weights = turn_weights(
        coil_centers_xyz,
        rx_center_xyz=rx_center_xyz,
        a=turn_weight_a,
        b=turn_weight_b,
        c=turn_weight_c,
    )
    coil_count = len(weights)
    if series_total_turn_count < coil_count:
        raise ValueError(
            "series_total_turn_count must be >= coil_count "
            f"(series_total_turn_count={series_total_turn_count}, coil_count={coil_count})"
        )
    if series_total_turn_count > coil_count * max_turn_count:
        raise ValueError(
            "series_total_turn_count exceeds geometry turn cap "
            f"(series_total_turn_count={series_total_turn_count}, coil_count={coil_count}, max_turn_count={max_turn_count})"
        )

    return _allocate_turns(
        coil_count=coil_count,
        distances=distances,
        weights=weights,
        target_turn_count=series_total_turn_count,
        base_turn_count=1,
        max_turn_count=max_turn_count,
    )


def allocate_parallel_turns(
    coil_centers_xyz: Sequence[Point3],
    *,
    rx_center_xyz: Sequence[float],
    parallel_total_turn_count: float,
    turn_weight_a: float,
    turn_weight_b: float,
    turn_weight_c: float,
    max_turn_count: int = _UNBOUNDED_MAX_TURN_COUNT,
) -> tuple[int, ...]:
    """Allocate parallel turns with distance-group allocation."""
    if isinstance(parallel_total_turn_count, bool) or not isinstance(parallel_total_turn_count, int | float):
        raise ValueError(
            "parallel_total_turn_count must be a real number "
            f"(actual={parallel_total_turn_count!r})"
        )
    total_turn_count_float = float(parallel_total_turn_count)
    if not (total_turn_count_float > 0.0):
        raise ValueError(
            "parallel_total_turn_count must be > 0 "
            f"(actual={parallel_total_turn_count!r})"
        )
    total_turn_count = round(total_turn_count_float)
    if not math.isclose(total_turn_count_float, float(total_turn_count), rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(
            "parallel_total_turn_count must be an integer value "
            f"(actual={parallel_total_turn_count!r})"
        )
    parallel_total_turn_count_i = int(total_turn_count)

    if isinstance(max_turn_count, bool) or not isinstance(max_turn_count, int):
        raise ValueError(f"max_turn_count must be an integer (actual={max_turn_count!r})")
    if max_turn_count < 1:
        raise ValueError(f"max_turn_count must be >= 1 (actual={max_turn_count})")

    distances = normalized_tx_plane_distances(coil_centers_xyz, rx_center_xyz=rx_center_xyz)
    weights = turn_weights(
        coil_centers_xyz,
        rx_center_xyz=rx_center_xyz,
        a=turn_weight_a,
        b=turn_weight_b,
        c=turn_weight_c,
    )
    coil_count = len(weights)
    if parallel_total_turn_count_i < coil_count:
        raise ValueError(
            "parallel_total_turn_count must be >= coil_count "
            f"(parallel_total_turn_count={parallel_total_turn_count_i}, coil_count={coil_count})"
        )
    if parallel_total_turn_count_i > coil_count * max_turn_count:
        raise ValueError(
            "parallel_total_turn_count exceeds geometry turn cap "
            f"(parallel_total_turn_count={parallel_total_turn_count_i}, coil_count={coil_count}, "
            f"max_turn_count={max_turn_count})"
        )

    return _allocate_turns(
        coil_count=coil_count,
        distances=distances,
        weights=weights,
        target_turn_count=parallel_total_turn_count_i,
        base_turn_count=1,
        max_turn_count=max_turn_count,
    )


def resolve_tx_turns(
    coil_centers_xyz: Sequence[Point3],
    *,
    rx_center_xyz: Sequence[float],
    connection_mode: TxConnectionMode,
    relevant_turn_count: float,
    turn_weight_a: float,
    turn_weight_b: float,
    turn_weight_c: float,
    max_turn_count: int = _UNBOUNDED_MAX_TURN_COUNT,
) -> tuple[int, ...]:
    """Resolve per-coil turns for parallel(0) or series(1) connection mode."""
    if connection_mode == 0:
        return allocate_parallel_turns(
            coil_centers_xyz,
            rx_center_xyz=rx_center_xyz,
            parallel_total_turn_count=relevant_turn_count,
            turn_weight_a=turn_weight_a,
            turn_weight_b=turn_weight_b,
            turn_weight_c=turn_weight_c,
            max_turn_count=max_turn_count,
        )
    if connection_mode == 1:
        finite_turn_count = _validated_real("series_total_turn_count", relevant_turn_count)
        rounded_turn_count = round(finite_turn_count)
        if not math.isclose(finite_turn_count, float(rounded_turn_count), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(
                "series_total_turn_count must be an integer value "
                f"(actual={relevant_turn_count!r})"
            )
        return allocate_series_turns(
            coil_centers_xyz,
            rx_center_xyz=rx_center_xyz,
            series_total_turn_count=int(rounded_turn_count),
            turn_weight_a=turn_weight_a,
            turn_weight_b=turn_weight_b,
            turn_weight_c=turn_weight_c,
            max_turn_count=max_turn_count,
        )
    raise ValueError(f"unsupported connection_mode (actual={connection_mode})")

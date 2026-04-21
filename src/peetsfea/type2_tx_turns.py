"""Deterministic TX turn allocation helpers for type2 coil columns."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Literal

TxConnectionMode = Literal[0, 1]
Point3 = tuple[float, float, float]
_TIE_ABS_TOL = 1e-15


def _validated_real(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, float | int):
        raise ValueError(f"{name} must be a real number (actual={value!r})")
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise ValueError(f"{name} must be finite (actual={value!r})")
    return numeric_value


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


def normalized_x_distances(coil_centers_xyz: Sequence[Point3], *, rx_center_x: float) -> tuple[float, ...]:
    """Return normalized |x - rx_center_x| distances preserving input coil order."""
    centers = _validated_coil_centers(coil_centers_xyz)
    rx_x = _validated_real("rx_center_x", rx_center_x)
    distances = tuple(abs(center[0] - rx_x) for center in centers)
    max_distance = max(distances)
    if max_distance == 0.0:
        return tuple(0.0 for _ in centers)
    return tuple(distance / max_distance for distance in distances)


def turn_weights(
    coil_centers_xyz: Sequence[Point3],
    *,
    rx_center_x: float,
    a: float,
    b: float,
    c: float,
) -> tuple[float, ...]:
    """Return polynomial weights w_i = a + b*x_i + c*x_i^2 for normalized |x|."""
    coeff_a = _validated_real("turn_weight_a", a)
    coeff_b = _validated_real("turn_weight_b", b)
    coeff_c = _validated_real("turn_weight_c", c)
    x_values = normalized_x_distances(coil_centers_xyz, rx_center_x=rx_center_x)
    weights = tuple(coeff_a + (coeff_b * x_value) + (coeff_c * x_value * x_value) for x_value in x_values)
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
    rx_center_x: float,
    series_total_turn_count: int,
    turn_weight_a: float,
    turn_weight_b: float,
    turn_weight_c: float,
) -> tuple[int, ...]:
    """Allocate series turns with one-turn seed then largest-remainder fill."""
    if isinstance(series_total_turn_count, bool) or not isinstance(series_total_turn_count, int):
        raise ValueError(
            "series_total_turn_count must be an integer "
            f"(actual={series_total_turn_count!r})"
        )
    if series_total_turn_count < 1:
        raise ValueError(f"series_total_turn_count must be >= 1 (actual={series_total_turn_count})")

    weights = turn_weights(
        coil_centers_xyz,
        rx_center_x=rx_center_x,
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

    base_turns = [1] * coil_count
    remaining_turns = series_total_turn_count - coil_count
    if remaining_turns == 0:
        return tuple(base_turns)

    total_weight = float(sum(weights))
    exact_extra = tuple((remaining_turns * (weight / total_weight)) for weight in weights)
    floored_extra = [int(math.floor(value)) for value in exact_extra]
    remainders = tuple(value - float(floor_value) for value, floor_value in zip(exact_extra, floored_extra, strict=True))
    floored_sum = sum(floored_extra)
    if floored_sum > remaining_turns:
        raise RuntimeError(
            "series largest-remainder allocation overflow "
            f"(floored_sum={floored_sum}, remaining_turns={remaining_turns})"
        )
    undistributed = remaining_turns - floored_sum
    order = sorted(
        range(coil_count),
        key=lambda index: (-remainders[index], -weights[index], index),
    )
    for rank in range(undistributed):
        base_turns[order[rank]] += 1
    for index in range(coil_count):
        base_turns[index] += floored_extra[index]
    return tuple(base_turns)


def _parallel_error(turns: Sequence[int], weights: Sequence[float], reciprocal_targets: Sequence[float]) -> float:
    return float(
        sum(
            weights[index] * abs((1.0 / float(turns[index])) - reciprocal_targets[index])
            for index in range(len(turns))
        )
    )


def _select_parallel_increment(
    turns: Sequence[int],
    weights: Sequence[float],
    reciprocal_targets: Sequence[float],
    current_error: float,
) -> tuple[int, float, float]:
    best_index = -1
    best_improvement = float("-inf")
    best_weight = float("-inf")
    best_next_error = float("inf")
    for index in range(len(turns)):
        current_turn = turns[index]
        next_turn = current_turn + 1
        current_term = weights[index] * abs((1.0 / float(current_turn)) - reciprocal_targets[index])
        next_term = weights[index] * abs((1.0 / float(next_turn)) - reciprocal_targets[index])
        next_error = current_error - current_term + next_term
        improvement = current_error - next_error

        better_improvement = improvement > (best_improvement + _TIE_ABS_TOL)
        tied_improvement = math.isclose(improvement, best_improvement, rel_tol=0.0, abs_tol=_TIE_ABS_TOL)
        better_weight = weights[index] > (best_weight + _TIE_ABS_TOL)
        tied_weight = math.isclose(weights[index], best_weight, rel_tol=0.0, abs_tol=_TIE_ABS_TOL)
        better_index = best_index < 0 or index < best_index

        if better_improvement or (tied_improvement and (better_weight or (tied_weight and better_index))):
            best_index = index
            best_improvement = improvement
            best_weight = weights[index]
            best_next_error = next_error

    if best_index < 0:
        raise RuntimeError("parallel greedy allocation must choose a candidate increment")
    return best_index, best_improvement, best_next_error


def allocate_parallel_turns(
    coil_centers_xyz: Sequence[Point3],
    *,
    rx_center_x: float,
    parallel_equivalent_turn_count: float,
    turn_weight_a: float,
    turn_weight_b: float,
    turn_weight_c: float,
) -> tuple[int, ...]:
    """Allocate parallel turns by weighted reciprocal-error greedy improvement."""
    equivalent_turns = _validated_real("parallel_equivalent_turn_count", parallel_equivalent_turn_count)
    if not (equivalent_turns > 0.0):
        raise ValueError(
            "parallel_equivalent_turn_count must be > 0 "
            f"(actual={parallel_equivalent_turn_count!r})"
        )
    target_reciprocal_sum = 1.0 / equivalent_turns

    weights = turn_weights(
        coil_centers_xyz,
        rx_center_x=rx_center_x,
        a=turn_weight_a,
        b=turn_weight_b,
        c=turn_weight_c,
    )
    coil_count = len(weights)
    max_reciprocal_sum = float(coil_count)
    if target_reciprocal_sum > max_reciprocal_sum:
        raise ValueError(
            "parallel_equivalent_turn_count is too small for this coil count "
            f"(target_reciprocal_sum={target_reciprocal_sum}, coil_count={coil_count}, "
            f"max_reciprocal_sum={max_reciprocal_sum})"
        )

    total_weight = float(sum(weights))
    reciprocal_targets = tuple((target_reciprocal_sum * (weight / total_weight)) for weight in weights)
    turns = [1] * coil_count
    current_error = _parallel_error(turns, weights, reciprocal_targets)

    while True:
        best_index, best_improvement, best_next_error = _select_parallel_increment(
            turns,
            weights,
            reciprocal_targets,
            current_error,
        )
        if not (best_improvement > _TIE_ABS_TOL):
            break
        turns[best_index] += 1
        current_error = best_next_error

    return tuple(turns)


def resolve_tx_turns(
    coil_centers_xyz: Sequence[Point3],
    *,
    rx_center_x: float,
    connection_mode: TxConnectionMode,
    relevant_turn_count: float,
    turn_weight_a: float,
    turn_weight_b: float,
    turn_weight_c: float,
) -> tuple[int, ...]:
    """Resolve per-coil turns for parallel(0) or series(1) connection mode."""
    if connection_mode == 0:
        return allocate_parallel_turns(
            coil_centers_xyz,
            rx_center_x=rx_center_x,
            parallel_equivalent_turn_count=relevant_turn_count,
            turn_weight_a=turn_weight_a,
            turn_weight_b=turn_weight_b,
            turn_weight_c=turn_weight_c,
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
            rx_center_x=rx_center_x,
            series_total_turn_count=int(rounded_turn_count),
            turn_weight_a=turn_weight_a,
            turn_weight_b=turn_weight_b,
            turn_weight_c=turn_weight_c,
        )
    raise ValueError(f"unsupported connection_mode (actual={connection_mode})")

"""Deterministic TX turn allocation helpers for type2 coil columns."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Literal

TxConnectionMode = Literal[0, 1]
Point3 = tuple[float, float, float]
_UNBOUNDED_MAX_TURN_COUNT = 1_000_000_000


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
    max_turn_count: int = _UNBOUNDED_MAX_TURN_COUNT,
) -> tuple[int, ...]:
    """Allocate series turns with one-turn seed then largest-remainder fill."""
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
    if series_total_turn_count > coil_count * max_turn_count:
        raise ValueError(
            "series_total_turn_count exceeds geometry turn cap "
            f"(series_total_turn_count={series_total_turn_count}, coil_count={coil_count}, max_turn_count={max_turn_count})"
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


def allocate_parallel_turns(
    coil_centers_xyz: Sequence[Point3],
    *,
    rx_center_x: float,
    parallel_total_turn_count: float,
    turn_weight_a: float,
    turn_weight_b: float,
    turn_weight_c: float,
    max_turn_count: int = _UNBOUNDED_MAX_TURN_COUNT,
) -> tuple[int, ...]:
    """Allocate parallel turns with one-turn seed then largest-remainder fill."""
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

    weights = turn_weights(
        coil_centers_xyz,
        rx_center_x=rx_center_x,
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

    turns = [1] * coil_count
    remaining_turn_count = parallel_total_turn_count_i - coil_count
    if remaining_turn_count == 0:
        return tuple(turns)

    total_weight = float(sum(weights))
    exact_extra_turns = tuple((remaining_turn_count * (weight / total_weight)) for weight in weights)
    base_extra_turns = [int(math.floor(value)) for value in exact_extra_turns]
    remainders = tuple(
        value - float(floor_value) for value, floor_value in zip(exact_extra_turns, base_extra_turns, strict=True)
    )
    base_sum = sum(base_extra_turns)
    for index, base_extra_turn in enumerate(base_extra_turns):
        turns[index] += base_extra_turn
    if base_sum > remaining_turn_count:
        raise RuntimeError(
            "parallel largest-remainder allocation overflow "
            f"(base_sum={base_sum}, remaining_turns={remaining_turn_count})"
        )
    undistributed_turns = remaining_turn_count - base_sum
    order = sorted(
        range(coil_count),
        key=lambda index: (-remainders[index], -weights[index], index),
    )
    for rank in range(undistributed_turns):
        target_index = order[rank]
        turns[target_index] += 1

    total_allocated = sum(turns)
    if total_allocated != parallel_total_turn_count_i:
        raise RuntimeError(
            "parallel allocation sum mismatch "
            f"(sum={total_allocated}, expected={parallel_total_turn_count_i})"
        )
    for index, turns_count in enumerate(turns):
        if turns_count > max_turn_count:
            raise ValueError(
                "parallel_total_turn_count allocation exceeds per-coil max_turn_count "
                f"(coil_index={index}, turns={turns_count}, max_turn_count={max_turn_count})"
            )
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
    max_turn_count: int = _UNBOUNDED_MAX_TURN_COUNT,
) -> tuple[int, ...]:
    """Resolve per-coil turns for parallel(0) or series(1) connection mode."""
    if connection_mode == 0:
        return allocate_parallel_turns(
            coil_centers_xyz,
            rx_center_x=rx_center_x,
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
            rx_center_x=rx_center_x,
            series_total_turn_count=int(rounded_turn_count),
            turn_weight_a=turn_weight_a,
            turn_weight_b=turn_weight_b,
            turn_weight_c=turn_weight_c,
            max_turn_count=max_turn_count,
        )
    raise ValueError(f"unsupported connection_mode (actual={connection_mode})")

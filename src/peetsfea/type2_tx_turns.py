"""Deterministic TX turn allocation helpers for type2 coil columns."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Literal

TxConnectionMode = Literal[0, 1]
Point3 = tuple[float, float, float]
_UNBOUNDED_MAX_TURN_COUNT = 1_000_000_000
_DISTANCE_GROUP_DECIMALS = 12
_PARALLEL_BRANCH_MAX_TURN_COUNT = 10
_SERIES_TOTAL_TURN_COUNT_CAP = 31


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

    target_extra_turns = target_turn_count - coil_count
    if target_extra_turns == 0:
        return tuple(base_turn_count for _index in range(coil_count))

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
        target_extra_turns * (group_weight / total_weight) for group_weight in group_weight_totals
    )
    desired_group_extra_turn_counts = tuple(
        exact_group_extra_total / float(group_size)
        for exact_group_extra_total, group_size in zip(exact_group_extra_totals, group_sizes, strict=True)
    )
    extra_turn_capacity = max_turn_count - base_turn_count
    if extra_turn_capacity < 0:
        raise ValueError(
            "base_turn_count exceeds max_turn_count "
            f"(base_turn_count={base_turn_count}, max_turn_count={max_turn_count})"
        )
    suffix_capacity = [0 for _index in range(group_count + 1)]
    suffix_gcd = [0 for _index in range(group_count + 1)]
    for group_index in range(group_count - 1, -1, -1):
        suffix_capacity[group_index] = suffix_capacity[group_index + 1] + (group_sizes[group_index] * extra_turn_capacity)
        suffix_gcd[group_index] = math.gcd(group_sizes[group_index], suffix_gcd[group_index + 1])

    memo: dict[tuple[int, int], tuple[float, tuple[int, ...]]] = {}

    def _solve(group_index: int, remaining_extra_turns: int) -> tuple[float, tuple[int, ...]]:
        state_key = (group_index, remaining_extra_turns)
        if state_key in memo:
            return memo[state_key]
        if remaining_extra_turns < 0 or remaining_extra_turns > suffix_capacity[group_index]:
            raise ValueError(
                "cannot satisfy target_turn_count without cap overflow "
                f"(target_turn_count={target_turn_count}, max_turn_count={max_turn_count})"
            )
        if suffix_gcd[group_index] > 0 and remaining_extra_turns % suffix_gcd[group_index] != 0:
            raise ValueError(
                "cannot satisfy target_turn_count with equal-distance group constraints "
                f"(target_turn_count={target_turn_count}, group_index={group_index})"
            )
        if group_index == group_count:
            if remaining_extra_turns != 0:
                raise RuntimeError(
                    "turn allocation recursion ended with leftover physical turns "
                    f"(remaining_extra_turns={remaining_extra_turns})"
                )
            result = (0.0, ())
            memo[state_key] = result
            return result

        group_size = group_sizes[group_index]
        desired_turn_count = desired_group_extra_turn_counts[group_index]
        max_group_extra = min(extra_turn_capacity, remaining_extra_turns // group_size)
        candidate_extras = list(range(0, max_group_extra + 1))
        candidate_extras.sort(
            key=lambda extra: (
                abs(float(extra) - desired_turn_count),
                extra,
            )
        )

        best_score = math.inf
        best_turn_counts: tuple[int, ...] = ()
        found = False
        next_group_index = group_index + 1
        next_suffix_capacity = suffix_capacity[next_group_index]
        next_suffix_gcd = suffix_gcd[next_group_index]
        for extra_turn_count in candidate_extras:
            consumed_turns = extra_turn_count * group_size
            next_remaining_extra_turns = remaining_extra_turns - consumed_turns
            if next_remaining_extra_turns < 0 or next_remaining_extra_turns > next_suffix_capacity:
                continue
            if next_suffix_gcd > 0 and next_remaining_extra_turns % next_suffix_gcd != 0:
                continue
            child_score, child_turn_counts = _solve(next_group_index, next_remaining_extra_turns)
            score = child_score + (group_size * ((float(extra_turn_count) - desired_turn_count) ** 2))
            candidate_turn_counts = (extra_turn_count,) + child_turn_counts
            if (not found) or score < best_score or (
                math.isclose(score, best_score, rel_tol=0.0, abs_tol=1e-12) and candidate_turn_counts < best_turn_counts
            ):
                best_score = score
                best_turn_counts = candidate_turn_counts
                found = True
        if not found:
            raise ValueError(
                "cannot satisfy target_turn_count with equal-distance group constraints "
                f"(target_turn_count={target_turn_count}, group_index={group_index}, "
                f"remaining_extra_turns={remaining_extra_turns})"
            )
        result = (best_score, best_turn_counts)
        memo[state_key] = result
        return result

    _score, group_extra_turn_counts = _solve(0, target_extra_turns)
    turns = [base_turn_count] * coil_count
    for group_index, extra_turn_count in enumerate(group_extra_turn_counts):
        assigned_turn_count = base_turn_count + extra_turn_count
        if assigned_turn_count > max_turn_count:
            raise ValueError(
                "distance group allocation exceeds per-coil max_turn_count "
                f"(group_index={group_index}, turns={assigned_turn_count}, max_turn_count={max_turn_count})"
            )
        for index in group_indices[group_index]:
            turns[index] = assigned_turn_count
    total_allocated = sum(turns)
    if total_allocated != target_turn_count:
        raise RuntimeError(
            "turn allocation failed to realize exact target_turn_count "
            f"(sum={total_allocated}, target_turn_count={target_turn_count})"
        )
    return tuple(turns)


def _parallel_equivalent_turn_count(turns: Sequence[int]) -> float:
    reciprocal_sum = 0.0
    for turn_count in turns:
        if isinstance(turn_count, bool) or not isinstance(turn_count, int):
            raise ValueError(f"parallel turn counts must be integers (actual={turn_count!r})")
        if turn_count < 1:
            raise ValueError(f"parallel turn counts must be >= 1 (actual={turn_count})")
        reciprocal_sum += 1.0 / float(turn_count)
    if reciprocal_sum <= 0.0:
        raise RuntimeError("parallel turn allocation produced no reciprocal contribution")
    return 1.0 / reciprocal_sum


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
    equivalent_turn_count: float,
    turn_weight_a: float,
    turn_weight_b: float,
    turn_weight_c: float,
    max_turn_count: int = _UNBOUNDED_MAX_TURN_COUNT,
) -> tuple[int, ...]:
    """Allocate series turns with distance-group allocation."""
    series_equivalent_turn_count = _validated_real("equivalent_turn_count", equivalent_turn_count)
    if not (series_equivalent_turn_count > 0.0):
        raise ValueError(f"equivalent_turn_count must be > 0 (actual={equivalent_turn_count!r})")
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
    target_turn_count = int(round(series_equivalent_turn_count))
    if target_turn_count < coil_count:
        raise ValueError(
            "equivalent_turn_count must round to at least one turn per branch in series mode "
            f"(equivalent_turn_count={series_equivalent_turn_count}, coil_count={coil_count}, "
            f"target_turn_count={target_turn_count})"
        )
    if target_turn_count > _SERIES_TOTAL_TURN_COUNT_CAP:
        raise ValueError(
            "equivalent_turn_count rounds above the series total-turn cap "
            f"(equivalent_turn_count={series_equivalent_turn_count}, target_turn_count={target_turn_count}, "
            f"cap={_SERIES_TOTAL_TURN_COUNT_CAP})"
        )
    if target_turn_count > coil_count * max_turn_count:
        raise ValueError(
            "equivalent_turn_count exceeds geometry turn cap "
            f"(equivalent_turn_count={series_equivalent_turn_count}, target_turn_count={target_turn_count}, "
            f"coil_count={coil_count}, max_turn_count={max_turn_count})"
        )

    last_allocation_error = ValueError("series turn allocation did not evaluate any target candidates")
    for candidate_target_turn_count in range(target_turn_count, coil_count - 1, -1):
        try:
            return _allocate_turns(
                coil_count=coil_count,
                distances=distances,
                weights=weights,
                target_turn_count=candidate_target_turn_count,
                base_turn_count=1,
                max_turn_count=max_turn_count,
            )
        except ValueError as exc:
            last_allocation_error = exc
            continue
    raise ValueError(
        "cannot allocate series turns without exceeding the requested equivalent target "
        f"(equivalent_turn_count={series_equivalent_turn_count}, target_turn_count={target_turn_count})"
    ) from last_allocation_error


def allocate_parallel_turns(
    coil_centers_xyz: Sequence[Point3],
    *,
    rx_center_xyz: Sequence[float],
    equivalent_turn_count: float,
    turn_weight_a: float,
    turn_weight_b: float,
    turn_weight_c: float,
    max_turn_count: int = _UNBOUNDED_MAX_TURN_COUNT,
) -> tuple[int, ...]:
    """Allocate parallel turns with distance-group allocation."""
    parallel_equivalent_turn_count = _validated_real("equivalent_turn_count", equivalent_turn_count)
    if not (parallel_equivalent_turn_count > 0.0):
        raise ValueError(f"equivalent_turn_count must be > 0 (actual={equivalent_turn_count!r})")

    if isinstance(max_turn_count, bool) or not isinstance(max_turn_count, int):
        raise ValueError(f"max_turn_count must be an integer (actual={max_turn_count!r})")
    if max_turn_count < 1:
        raise ValueError(f"max_turn_count must be >= 1 (actual={max_turn_count})")
    effective_parallel_cap = min(max_turn_count, _PARALLEL_BRANCH_MAX_TURN_COUNT)

    distances = normalized_tx_plane_distances(coil_centers_xyz, rx_center_xyz=rx_center_xyz)
    weights = turn_weights(
        coil_centers_xyz,
        rx_center_xyz=rx_center_xyz,
        a=turn_weight_a,
        b=turn_weight_b,
        c=turn_weight_c,
    )
    coil_count = len(weights)
    lower_equivalent_bound = 1.0 / float(coil_count)
    upper_equivalent_bound = float(effective_parallel_cap) / float(coil_count)
    if parallel_equivalent_turn_count < lower_equivalent_bound and not math.isclose(
        parallel_equivalent_turn_count,
        lower_equivalent_bound,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError(
            "equivalent_turn_count is below the feasible parallel harmonic range "
            f"(equivalent_turn_count={parallel_equivalent_turn_count}, coil_count={coil_count}, "
            f"minimum={lower_equivalent_bound})"
        )
    if parallel_equivalent_turn_count > upper_equivalent_bound and not math.isclose(
        parallel_equivalent_turn_count,
        upper_equivalent_bound,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError(
            "equivalent_turn_count is above the feasible parallel harmonic range "
            f"(equivalent_turn_count={parallel_equivalent_turn_count}, coil_count={coil_count}, "
            f"maximum={upper_equivalent_bound})"
        )
    first_turn_count = coil_count
    best_turns = _allocate_turns(
        coil_count=coil_count,
        distances=distances,
        weights=weights,
        target_turn_count=first_turn_count,
        base_turn_count=1,
        max_turn_count=effective_parallel_cap,
    )
    best_difference = abs(_parallel_equivalent_turn_count(best_turns) - parallel_equivalent_turn_count)
    best_target_turn_count = first_turn_count
    for target_turn_count in range(coil_count + 1, coil_count * effective_parallel_cap + 1):
        try:
            turns = _allocate_turns(
                coil_count=coil_count,
                distances=distances,
                weights=weights,
                target_turn_count=target_turn_count,
                base_turn_count=1,
                max_turn_count=effective_parallel_cap,
            )
        except ValueError:
            continue
        realized_equivalent_turn_count = _parallel_equivalent_turn_count(turns)
        difference = abs(realized_equivalent_turn_count - parallel_equivalent_turn_count)
        if difference < best_difference:
            best_turns = turns
            best_difference = difference
            best_target_turn_count = target_turn_count
            continue
        if math.isclose(difference, best_difference, rel_tol=0.0, abs_tol=1e-12):
            candidate_key = (target_turn_count, turns)
            best_key = (best_target_turn_count, best_turns)
            if candidate_key < best_key:
                best_turns = turns
                best_difference = difference
                best_target_turn_count = target_turn_count
    return best_turns


def resolve_tx_turns(
    coil_centers_xyz: Sequence[Point3],
    *,
    rx_center_xyz: Sequence[float],
    connection_mode: TxConnectionMode,
    equivalent_turn_count: float,
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
            equivalent_turn_count=equivalent_turn_count,
            turn_weight_a=turn_weight_a,
            turn_weight_b=turn_weight_b,
            turn_weight_c=turn_weight_c,
            max_turn_count=max_turn_count,
        )
    if connection_mode == 1:
        return allocate_series_turns(
            coil_centers_xyz,
            rx_center_xyz=rx_center_xyz,
            equivalent_turn_count=equivalent_turn_count,
            turn_weight_a=turn_weight_a,
            turn_weight_b=turn_weight_b,
            turn_weight_c=turn_weight_c,
            max_turn_count=max_turn_count,
        )
    raise ValueError(f"unsupported connection_mode (actual={connection_mode})")

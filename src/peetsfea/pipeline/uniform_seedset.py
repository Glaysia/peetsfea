from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from peetsfea.spec.loader import TOMLTable
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.resolver import resolve_selection_with_context
from peetsfea.spec.resolver.types import SelectionConstraintError


@dataclass(frozen=True)
class FeasibleSeedPoint:
    seed: int
    attempt: int
    context: dict[str, int | float]


def _first_feasible_point(*, spec: TOMLTable, seed: int, max_attempts: int) -> FeasibleSeedPoint | None:
    for attempt in range(max_attempts):
        try:
            _, _, _, _, _, context = resolve_selection_with_context(spec=spec, seed=seed, attempt=attempt)
            return FeasibleSeedPoint(seed=seed, attempt=attempt, context=context)
        except SelectionConstraintError:
            continue
    return None


def _variable_keys(points: list[FeasibleSeedPoint]) -> tuple[str, ...]:
    if len(points) == 0:
        return tuple()
    values_by_key: dict[str, set[float]] = {}
    for point in points:
        for key, value in point.context.items():
            values_by_key.setdefault(key, set()).add(float(value))
    keys = [key for key, values in values_by_key.items() if len(values) > 1]
    keys.sort()
    return tuple(keys)


def _normalized_vectors(points: list[FeasibleSeedPoint], keys: tuple[str, ...]) -> list[tuple[float, ...]]:
    if len(keys) == 0:
        return [tuple() for _ in points]
    mins: dict[str, float] = {key: float("inf") for key in keys}
    maxs: dict[str, float] = {key: float("-inf") for key in keys}
    for point in points:
        for key in keys:
            value = float(point.context[key])
            mins[key] = min(mins[key], value)
            maxs[key] = max(maxs[key], value)

    vectors: list[tuple[float, ...]] = []
    for point in points:
        row: list[float] = []
        for key in keys:
            value = float(point.context[key])
            span = maxs[key] - mins[key]
            row.append(0.0 if span <= 0.0 else (value - mins[key]) / span)
        vectors.append(tuple(row))
    return vectors


def _dist_sq(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    total = 0.0
    for av, bv in zip(a, b):
        dv = av - bv
        total += dv * dv
    return total


def _choose_initial_index(points: list[FeasibleSeedPoint], vectors: list[tuple[float, ...]]) -> int:
    if len(points) == 1:
        return 0
    if len(vectors[0]) == 0:
        return min(range(len(points)), key=lambda idx: points[idx].seed)
    dims = len(vectors[0])
    centroid = tuple(sum(vec[d] for vec in vectors) / float(len(vectors)) for d in range(dims))
    distances = [(_dist_sq(vectors[idx], centroid), points[idx].seed, idx) for idx in range(len(points))]
    # Stable deterministic tie-break: farther from centroid first, then smaller seed.
    distances.sort(key=lambda row: (-row[0], row[1]))
    return distances[0][2]


def _farthest_point_indices(
    points: list[FeasibleSeedPoint],
    vectors: list[tuple[float, ...]],
    target_size: int,
) -> list[int]:
    if target_size >= len(points):
        return list(range(len(points)))
    selected: list[int] = []
    remaining: set[int] = set(range(len(points)))

    first_idx = _choose_initial_index(points, vectors)
    selected.append(first_idx)
    remaining.remove(first_idx)

    min_dist_sq: dict[int, float] = {}
    for idx in remaining:
        min_dist_sq[idx] = _dist_sq(vectors[idx], vectors[first_idx])

    while len(selected) < target_size and remaining:
        best_idx = min(
            remaining,
            key=lambda idx: (-min_dist_sq[idx], points[idx].seed),
        )
        selected.append(best_idx)
        remaining.remove(best_idx)
        for idx in remaining:
            d2 = _dist_sq(vectors[idx], vectors[best_idx])
            if d2 < min_dist_sq[idx]:
                min_dist_sq[idx] = d2
    return selected


def generate_uniform_feasible_seed_points(
    *,
    spec_path: Path,
    seed_start: int,
    seed_end: int,
    target_size: int,
    max_attempts: int = 64,
) -> list[FeasibleSeedPoint]:
    if seed_end <= seed_start:
        raise ValueError(f"seed_end must be > seed_start (got seed_start={seed_start}, seed_end={seed_end})")
    if target_size < 1:
        raise ValueError(f"target_size must be >= 1 (got {target_size})")
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1 (got {max_attempts})")

    spec, _ = load_toml_bytes(spec_path)
    points: list[FeasibleSeedPoint] = []
    for seed in range(seed_start, seed_end):
        point = _first_feasible_point(spec=spec, seed=seed, max_attempts=max_attempts)
        if point is not None:
            points.append(point)

    if len(points) == 0:
        raise RuntimeError("No feasible seed found in the requested seed range")
    if len(points) < target_size:
        raise RuntimeError(
            "Insufficient feasible seeds for requested target size "
            f"(feasible={len(points)}, target={target_size}, range=[{seed_start},{seed_end}))"
        )

    keys = _variable_keys(points)
    vectors = _normalized_vectors(points, keys)
    picked_indices = _farthest_point_indices(points, vectors, target_size)
    selected_points = [points[idx] for idx in picked_indices]
    selected_points.sort(key=lambda item: item.seed)
    return selected_points


def generate_uniform_feasible_seeds(
    *,
    spec_path: Path,
    seed_start: int,
    seed_end: int,
    target_size: int,
    max_attempts: int = 64,
) -> tuple[int, ...]:
    points = generate_uniform_feasible_seed_points(
        spec_path=spec_path,
        seed_start=seed_start,
        seed_end=seed_end,
        target_size=target_size,
        max_attempts=max_attempts,
    )
    return tuple(point.seed for point in points)

from __future__ import annotations

from collections import deque
from collections.abc import Iterator
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


def iter_feasible_seed_points(
    *,
    spec_path: Path,
    seed_start: int,
    seed_end: int,
    max_attempts: int = 64,
) -> Iterator[FeasibleSeedPoint]:
    if seed_end <= seed_start:
        raise ValueError(f"seed_end must be > seed_start (got seed_start={seed_start}, seed_end={seed_end})")
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1 (got {max_attempts})")
    spec, _ = load_toml_bytes(spec_path)
    for seed in range(seed_start, seed_end):
        point = _first_feasible_point(spec=spec, seed=seed, max_attempts=max_attempts)
        if point is not None:
            yield point


def _dist_sq(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    total = 0.0
    for av, bv in zip(a, b):
        dv = av - bv
        total += dv * dv
    return total


def _raw_vector(point: FeasibleSeedPoint, keys: tuple[str, ...]) -> tuple[float, ...]:
    return tuple(float(point.context[key]) for key in keys)


def _update_minmax(mins: list[float], maxs: list[float], vector: tuple[float, ...]) -> None:
    for idx, value in enumerate(vector):
        if value < mins[idx]:
            mins[idx] = value
        if value > maxs[idx]:
            maxs[idx] = value


def _normalized_vector(vector: tuple[float, ...], mins: list[float], maxs: list[float]) -> tuple[float, ...]:
    out: list[float] = []
    for idx, value in enumerate(vector):
        span = maxs[idx] - mins[idx]
        out.append(0.0 if span <= 1e-12 else (value - mins[idx]) / span)
    return tuple(out)


def _min_dist_sq_to_selected(
    candidate: tuple[float, ...],
    selected_vectors: list[tuple[float, ...]],
    mins: list[float],
    maxs: list[float],
) -> float:
    normalized_candidate = _normalized_vector(candidate, mins, maxs)
    best = float("inf")
    for selected in selected_vectors:
        d2 = _dist_sq(normalized_candidate, _normalized_vector(selected, mins, maxs))
        if d2 < best:
            best = d2
    return best


def iter_uniform_feasible_seed_points(
    *,
    spec_path: Path,
    seed_start: int,
    seed_end: int,
    target_size: int,
    max_attempts: int = 64,
    window_size: int = 128,
) -> Iterator[FeasibleSeedPoint]:
    if target_size < 1:
        raise ValueError(f"target_size must be >= 1 (got {target_size})")
    if window_size < 1:
        raise ValueError(f"window_size must be >= 1 (got {window_size})")

    feasible_iter = iter_feasible_seed_points(
        spec_path=spec_path,
        seed_start=seed_start,
        seed_end=seed_end,
        max_attempts=max_attempts,
    )
    first = next(feasible_iter, None)
    if first is None:
        raise RuntimeError("No feasible seed found in the requested seed range")

    keys = tuple(sorted(first.context.keys()))
    selected_points: list[FeasibleSeedPoint] = [first]
    selected_vectors: list[tuple[float, ...]] = [_raw_vector(first, keys)]
    mins = list(selected_vectors[0])
    maxs = list(selected_vectors[0])
    yield first

    yielded = 1
    if yielded >= target_size:
        return

    buffer: deque[FeasibleSeedPoint] = deque()
    exhausted = False

    def _fill_buffer() -> None:
        nonlocal exhausted
        while len(buffer) < window_size and not exhausted:
            item = next(feasible_iter, None)
            if item is None:
                exhausted = True
                break
            buffer.append(item)

    while yielded < target_size:
        _fill_buffer()
        if len(buffer) == 0:
            raise RuntimeError(
                "Insufficient feasible seeds for requested target size "
                f"(selected={yielded}, target={target_size}, range=[{seed_start},{seed_end}))"
            )

        best_idx = -1
        best_score = -1.0
        best_seed = 0
        best_vector: tuple[float, ...] | None = None
        for idx, point in enumerate(buffer):
            vector = _raw_vector(point, keys)
            cand_mins = mins[:]
            cand_maxs = maxs[:]
            _update_minmax(cand_mins, cand_maxs, vector)
            score = _min_dist_sq_to_selected(vector, selected_vectors, cand_mins, cand_maxs)
            if (
                best_vector is None
                or score > (best_score + 1e-12)
                or (abs(score - best_score) <= 1e-12 and point.seed < best_seed)
            ):
                best_idx = idx
                best_score = score
                best_seed = point.seed
                best_vector = vector

        assert best_idx >= 0
        chosen = buffer[best_idx]
        # Skip lower-score candidates currently in the lookahead window.
        del buffer[best_idx]

        selected_points.append(chosen)
        assert best_vector is not None
        selected_vectors.append(best_vector)
        _update_minmax(mins, maxs, best_vector)
        yield chosen
        yielded += 1


def iter_uniform_feasible_seeds(
    *,
    spec_path: Path,
    seed_start: int,
    seed_end: int,
    target_size: int,
    max_attempts: int = 64,
    window_size: int = 128,
) -> Iterator[int]:
    for point in iter_uniform_feasible_seed_points(
        spec_path=spec_path,
        seed_start=seed_start,
        seed_end=seed_end,
        target_size=target_size,
        max_attempts=max_attempts,
        window_size=window_size,
    ):
        yield point.seed


def generate_uniform_feasible_seed_points(
    *,
    spec_path: Path,
    seed_start: int,
    seed_end: int,
    target_size: int,
    max_attempts: int = 64,
    window_size: int = 128,
) -> list[FeasibleSeedPoint]:
    selected_points = list(
        iter_uniform_feasible_seed_points(
            spec_path=spec_path,
            seed_start=seed_start,
            seed_end=seed_end,
            target_size=target_size,
            max_attempts=max_attempts,
            window_size=window_size,
        )
    )
    selected_points.sort(key=lambda item: item.seed)
    return selected_points


def generate_uniform_feasible_seeds(
    *,
    spec_path: Path,
    seed_start: int,
    seed_end: int,
    target_size: int,
    max_attempts: int = 64,
    window_size: int = 128,
) -> tuple[int, ...]:
    points = generate_uniform_feasible_seed_points(
        spec_path=spec_path,
        seed_start=seed_start,
        seed_end=seed_end,
        target_size=target_size,
        max_attempts=max_attempts,
        window_size=window_size,
    )
    return tuple(point.seed for point in points)

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from peetsfea.console_log import info
from peetsfea.spec.loader import TOMLTable
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.resolver import resolve_selection_result
from peetsfea.spec.resolver.sampling import SamplingLedger
from peetsfea.spec.resolver.types import SelectionConstraintError
from .selection_snapshots import dataset_owner_paths, detect_repro_mode


@dataclass(frozen=True)
class FeasibleSeedPoint:
    seed: int
    attempt: int
    sampling_ledger: SamplingLedger


def _first_feasible_point(*, spec: TOMLTable, seed: int, max_attempts: int) -> FeasibleSeedPoint | None:
    for attempt in range(max_attempts):
        try:
            result = resolve_selection_result(spec=spec, seed=seed, attempt=attempt)
            return FeasibleSeedPoint(seed=seed, attempt=attempt, sampling_ledger=result.sampling_ledger)
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
    return point.sampling_ledger.as_float_vector(keys)


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


def _selection_keys(spec_path: Path) -> tuple[str, ...]:
    spec, _ = load_toml_bytes(spec_path)
    repro_mode = detect_repro_mode(spec)
    return dataset_owner_paths(spec, repro_mode=repro_mode)


def generate_eager_uniform_feasible_seed_points(
    *,
    spec_path: Path,
    seed_start: int,
    seed_end: int,
    target_size: int,
    max_attempts: int = 64,
) -> list[FeasibleSeedPoint]:
    if target_size < 1:
        raise ValueError(f"target_size must be >= 1 (got {target_size})")

    feasible_points = list(
        iter_feasible_seed_points(
            spec_path=spec_path,
            seed_start=seed_start,
            seed_end=seed_end,
            max_attempts=max_attempts,
        )
    )
    if len(feasible_points) == 0:
        raise RuntimeError("No feasible seed found in the requested seed range")
    if len(feasible_points) < target_size:
        raise RuntimeError(
            "Insufficient feasible seeds for requested target size "
            f"(selected={len(feasible_points)}, target={target_size}, range=[{seed_start},{seed_end}))"
        )

    keys = _selection_keys(spec_path)
    selected_points: list[FeasibleSeedPoint] = [feasible_points.pop(0)]
    selected_vectors: list[tuple[float, ...]] = [_raw_vector(selected_points[0], keys)]
    mins = list(selected_vectors[0])
    maxs = list(selected_vectors[0])
    info(f"[uniform] progress 1/{target_size} seed={selected_points[0].seed}")

    while len(selected_points) < target_size:
        best_idx = -1
        best_score = -1.0
        best_seed = 0
        best_vector: tuple[float, ...] | None = None
        for idx, point in enumerate(feasible_points):
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
        chosen = feasible_points.pop(best_idx)
        selected_points.append(chosen)
        assert best_vector is not None
        selected_vectors.append(best_vector)
        _update_minmax(mins, maxs, best_vector)
        info(f"[uniform] progress {len(selected_points)}/{target_size} seed={chosen.seed}")

    return sorted(selected_points, key=lambda point:point.seed)


def generate_eager_uniform_feasible_seeds(
    *,
    spec_path: Path,
    seed_start: int,
    seed_end: int,
    target_size: int,
    max_attempts: int = 64,
) -> tuple[int, ...]:
    points = generate_eager_uniform_feasible_seed_points(
        spec_path=spec_path,
        seed_start=seed_start,
        seed_end=seed_end,
        target_size=target_size,
        max_attempts=max_attempts,
    )
    return tuple(point.seed for point in points)

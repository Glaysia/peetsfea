from __future__ import annotations

from pathlib import Path

import pytest

from peetsfea.pipeline.uniform_seedset import (
    generate_uniform_feasible_seed_points,
    generate_uniform_feasible_seeds,
    iter_uniform_feasible_seed_points,
    iter_uniform_feasible_seeds,
)


def test_generate_uniform_feasible_seeds_is_deterministic() -> None:
    spec_path = Path(__file__).resolve().parents[1] / "examples" / "type1.toml"
    seeds_a = generate_uniform_feasible_seeds(
        spec_path=spec_path,
        seed_start=0,
        seed_end=400,
        target_size=12,
        max_attempts=32,
    )
    seeds_b = generate_uniform_feasible_seeds(
        spec_path=spec_path,
        seed_start=0,
        seed_end=400,
        target_size=12,
        max_attempts=32,
    )
    assert seeds_a == seeds_b
    assert len(seeds_a) == 12
    assert len(set(seeds_a)) == 12
    assert list(seeds_a) == sorted(seeds_a)


def test_generate_uniform_feasible_seed_points_have_context() -> None:
    spec_path = Path(__file__).resolve().parents[1] / "examples" / "type1.toml"
    points = generate_uniform_feasible_seed_points(
        spec_path=spec_path,
        seed_start=0,
        seed_end=250,
        target_size=8,
        max_attempts=32,
    )
    assert len(points) == 8
    for point in points:
        assert point.seed >= 0
        assert point.attempt >= 0
        assert "coil_groups[1].count_range" in point.context


def test_iter_uniform_feasible_seeds_is_deterministic() -> None:
    spec_path = Path(__file__).resolve().parents[1] / "examples" / "type1.toml"
    seeds_a = tuple(
        iter_uniform_feasible_seeds(
            spec_path=spec_path,
            seed_start=0,
            seed_end=400,
            target_size=12,
            max_attempts=32,
            window_size=32,
        )
    )
    seeds_b = tuple(
        iter_uniform_feasible_seeds(
            spec_path=spec_path,
            seed_start=0,
            seed_end=400,
            target_size=12,
            max_attempts=32,
            window_size=32,
        )
    )
    assert seeds_a == seeds_b
    assert len(seeds_a) == 12
    assert len(set(seeds_a)) == 12


def test_iter_uniform_feasible_seed_points_target_size_overflow_errors() -> None:
    spec_path = Path(__file__).resolve().parents[1] / "examples" / "type1.toml"
    points = list(
        generate_uniform_feasible_seed_points(
            spec_path=spec_path,
            seed_start=0,
            seed_end=25,
            target_size=5,
            max_attempts=32,
        )
    )
    assert len(points) == 5
    with pytest.raises(RuntimeError, match="Insufficient feasible seeds"):
        list(
            iter_uniform_feasible_seed_points(
                spec_path=spec_path,
                seed_start=0,
                seed_end=25,
                target_size=50,
                max_attempts=32,
                window_size=8,
            )
        )


def _min_pairwise_distance(points: list[tuple[float, ...]]) -> float:
    if len(points) < 2:
        return 0.0
    best = float("inf")
    for idx in range(len(points)):
        for jdx in range(idx + 1, len(points)):
            d2 = 0.0
            for av, bv in zip(points[idx], points[jdx]):
                dv = av - bv
                d2 += dv * dv
            if d2 < best:
                best = d2
    return best


def test_window_size_increase_improves_or_matches_coverage_metric() -> None:
    spec_path = Path(__file__).resolve().parents[1] / "examples" / "type1.toml"
    small_window = list(
        iter_uniform_feasible_seed_points(
            spec_path=spec_path,
            seed_start=0,
            seed_end=500,
            target_size=18,
            max_attempts=32,
            window_size=1,
        )
    )
    large_window = list(
        iter_uniform_feasible_seed_points(
            spec_path=spec_path,
            seed_start=0,
            seed_end=500,
            target_size=18,
            max_attempts=32,
            window_size=64,
        )
    )

    keys = sorted(small_window[0].context.keys())
    small_vectors = [tuple(float(point.context[key]) for key in keys) for point in small_window]
    large_vectors = [tuple(float(point.context[key]) for key in keys) for point in large_window]
    assert _min_pairwise_distance(large_vectors) >= _min_pairwise_distance(small_vectors)

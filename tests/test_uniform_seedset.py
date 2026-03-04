from __future__ import annotations

from pathlib import Path

from peetsfea.pipeline.uniform_seedset import generate_uniform_feasible_seed_points, generate_uniform_feasible_seeds


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

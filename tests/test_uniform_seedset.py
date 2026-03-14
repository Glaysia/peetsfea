from __future__ import annotations

from pathlib import Path

import pytest

from peetsfea.pipeline.selection_snapshots import dataset_owner_paths, detect_repro_mode
from peetsfea.pipeline.uniform_seedset import (
    generate_eager_uniform_feasible_seed_points,
    generate_eager_uniform_feasible_seeds,
    iter_feasible_seed_points,
)
from peetsfea.spec.loader import TOMLTable, load_toml_bytes
from peetsfea.spec.resolver import SelectionConstraintError, resolve_selection_result


def _first_feasible_result(spec: TOMLTable, *, seed: int, max_attempts: int) -> int:
    for attempt in range(max_attempts):
        try:
            result = resolve_selection_result(spec=spec, seed=seed, attempt=attempt)
            return int(result.selected_parameters["tx_vertical_layout_mode"])
        except SelectionConstraintError:
            continue
    raise AssertionError(f"No feasible selection found for seed={seed}")


def test_generate_eager_uniform_feasible_seeds_is_deterministic() -> None:
    spec_path = Path(__file__).resolve().parents[1] / "examples" / "type1.toml"
    seeds_a = generate_eager_uniform_feasible_seeds(
        spec_path=spec_path,
        seed_start=0,
        seed_end=200,
        target_size=20,
        max_attempts=32,
    )
    seeds_b = generate_eager_uniform_feasible_seeds(
        spec_path=spec_path,
        seed_start=0,
        seed_end=200,
        target_size=20,
        max_attempts=32,
    )
    assert seeds_a == seeds_b
    assert len(seeds_a) == 20
    assert len(set(seeds_a)) == 20


def test_generate_eager_uniform_feasible_seed_points_have_sampling_ledger() -> None:
    spec_path = Path(__file__).resolve().parents[1] / "examples" / "type1.toml"
    points = generate_eager_uniform_feasible_seed_points(
        spec_path=spec_path,
        seed_start=0,
        seed_end=200,
        target_size=12,
        max_attempts=32,
    )
    assert len(points) == 12
    assert len({point.seed for point in points}) == 12
    for point in points:
        assert point.seed >= 0
        assert point.attempt >= 0
        assert "coil_placement.tx_vertical_layout_mode" in point.sampling_ledger
        assert "coil_groups[1].count_range" in point.sampling_ledger


def test_generate_eager_uniform_feasible_seed_points_target_size_overflow_errors() -> None:
    spec_path = Path(__file__).resolve().parents[1] / "examples" / "type1.toml"
    with pytest.raises(RuntimeError, match="Insufficient feasible seeds"):
        generate_eager_uniform_feasible_seed_points(
            spec_path=spec_path,
            seed_start=0,
            seed_end=25,
            target_size=50,
            max_attempts=32,
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


def test_eager_uniform_improves_or_matches_naive_first_feasible_baseline() -> None:
    spec_path = Path(__file__).resolve().parents[1] / "examples" / "type1.toml"
    spec, _ = load_toml_bytes(spec_path)
    eager_points = generate_eager_uniform_feasible_seed_points(
        spec_path=spec_path,
        seed_start=0,
        seed_end=200,
        target_size=20,
        max_attempts=32,
    )
    naive_points = list(
        iter_feasible_seed_points(
            spec_path=spec_path,
            seed_start=0,
            seed_end=200,
            max_attempts=32,
        )
    )[:20]

    keys = dataset_owner_paths(spec, repro_mode=detect_repro_mode(spec))
    eager_vectors = [point.sampling_ledger.as_float_vector(keys) for point in eager_points]
    naive_vectors = [point.sampling_ledger.as_float_vector(keys) for point in naive_points]
    assert _min_pairwise_distance(eager_vectors) >= _min_pairwise_distance(naive_vectors)


def test_example_spec_keeps_mode2_population_above_regression_floor() -> None:
    spec_path = Path(__file__).resolve().parents[1] / "examples" / "type1.toml"
    spec, _ = load_toml_bytes(spec_path)

    mode2_count = 0
    for seed in range(500):
        if _first_feasible_result(spec, seed=seed, max_attempts=64) == 2:
            mode2_count += 1

    assert mode2_count >= 30

from __future__ import annotations

from pathlib import Path
from typing import cast

from peetsfea.spec.loader import TOMLTable, load_toml_bytes
from peetsfea.legacy.type1.spec.resolver.api import _build_selected_parameters, resolve_selected_scalars
from peetsfea.legacy.type1.spec.resolver.domains.coil_groups import resolve_coil_groups
from peetsfea.legacy.type1.spec.resolver.sampling import SamplingLedger, build_sampling_registry
from peetsfea.legacy.type1.spec.resolver import resolve_selection, resolve_selection_result, resolve_selection_with_context
from peetsfea.legacy.type1.spec.resolver.types import SelectionConstraintError, SelectionResult
from peetsfea.types.runtime_selection import ResolvedTxDdGroup, ResolvedTxVerticalGroup
from tests.fixtures.legacy.type1_spec import write_type1_toml


def _first_feasible_result(spec: TOMLTable, *, seed: int) -> tuple[int, SelectionResult]:
    for attempt in range(64):
        try:
            return attempt, resolve_selection_result(spec=spec, seed=seed, attempt=attempt)
        except SelectionConstraintError:
            continue
    raise AssertionError(f"No feasible selection found for seed={seed}")


def test_selection_result_matches_legacy_wrappers(tmp_path: Path) -> None:
    toml_path = tmp_path / "type1.toml"
    write_type1_toml(toml_path)
    spec, _ = load_toml_bytes(toml_path)

    attempt, result = _first_feasible_result(spec, seed=7)
    legacy = resolve_selection(spec=spec, seed=7, attempt=attempt)
    legacy_with_context = resolve_selection_with_context(spec=spec, seed=7, attempt=attempt)

    assert result.selected_parameters == legacy[0]
    assert result.selected_parameters_max == legacy[1]
    assert result.selected_coil_groups == legacy[2]
    assert result.selected_group_geometry == legacy[3]
    assert result.selected_pcbs == legacy[4]
    assert result.sampling_ledger.as_dict() == legacy_with_context[5]


def test_selection_result_exposes_sampling_ledger_paths(tmp_path: Path) -> None:
    toml_path = tmp_path / "type1.toml"
    write_type1_toml(toml_path)
    spec, _ = load_toml_bytes(toml_path)

    _, result = _first_feasible_result(spec, seed=3)

    assert "coil_placement.tx_vertical_orientation_mode" in result.sampling_ledger.recorded_paths()
    assert "coil_shape.corner_mode" in result.sampling_ledger.recorded_paths()
    assert "coil_groups[1].count_range" in result.sampling_ledger.recorded_paths()
    assert "coil_groups[0].stacked_mode" in result.sampling_ledger.recorded_paths()
    assert result.sampling_ledger.sorted_recorded_paths() == tuple(sorted(result.sampling_ledger.recorded_paths()))


def test_corner_mode_can_be_fixed_to_blunt_and_is_recorded(tmp_path: Path) -> None:
    toml_path = tmp_path / "corner_mode_blunt.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "[coil_shape.corner_mode]\nrange = [true, 0, 0, 1]",
        "[coil_shape.corner_mode]\nrange = [true, 1, 1, 1]",
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")
    spec, _ = load_toml_bytes(toml_path)

    _, result = _first_feasible_result(spec, seed=5)

    assert int(result.selected_parameters["corner_mode"]) == 1
    assert "coil_shape.corner_mode" in result.sampling_ledger.recorded_paths()


def test_ferrite_present_sampling_is_deterministic_and_reaches_both_states(tmp_path: Path) -> None:
    toml_path = tmp_path / "type1.toml"
    write_type1_toml(toml_path)
    spec, _ = load_toml_bytes(toml_path)
    registry = build_sampling_registry(spec)

    seen_by_seed: dict[int, bool] = {}
    seen_states: set[bool] = set()
    for seed in range(8):
        context_a = SamplingLedger(registry, seed=seed, attempt=0)
        raw_a = resolve_selected_scalars(spec, seed, 0, context_a)
        selected_a = _build_selected_parameters(spec, raw_a)
        context_b = SamplingLedger(registry, seed=seed, attempt=0)
        raw_b = resolve_selected_scalars(spec, seed, 0, context_b)
        selected_b = _build_selected_parameters(spec, raw_b)
        ferrite_a = bool(selected_a["ferrite_present"])
        ferrite_b = bool(selected_b["ferrite_present"])
        assert ferrite_a == ferrite_b
        seen_by_seed[seed] = ferrite_a
        seen_states.add(ferrite_a)

    assert seen_states == {False, True}
    assert any(state is False for state in seen_by_seed.values())
    assert any(state is True for state in seen_by_seed.values())


def test_sampling_is_deterministic_for_same_seed_and_attempt(tmp_path: Path) -> None:
    toml_path = tmp_path / "type1.toml"
    write_type1_toml(toml_path)
    spec, _ = load_toml_bytes(toml_path)
    registry = build_sampling_registry(spec)

    context_a = SamplingLedger(registry, seed=11, attempt=3)
    raw_a = resolve_selected_scalars(spec, 11, 3, context_a)
    context_b = SamplingLedger(registry, seed=11, attempt=3)
    raw_b = resolve_selected_scalars(spec, 11, 3, context_b)

    assert raw_a == raw_b
    assert context_a.as_dict() == context_b.as_dict()


def test_neo_tx_dd_top_offset_ratio_derives_mm_clearance(tmp_path: Path) -> None:
    toml_path = tmp_path / "neo_tx_dd_top_offset_ratio.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "[coil_placement.neo_tx_dd_top_offset_ratio]\nrange = [false, 0.0, 0.3, 10]",
        "[coil_placement.neo_tx_dd_top_offset_ratio]\nrange = [false, 0.3, 0.3, 1]",
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")
    spec, _ = load_toml_bytes(toml_path)

    _, result = _first_feasible_result(spec, seed=5)

    assert float(result.selected_parameters["tx_dd_top_offset_ratio"]) == 0.3
    assert float(result.selected_parameters["tx_dd_top_clearance_mm"]) == 2.1


def test_tx_vertical_orientation_mode_derives_realized_zx_plane(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_vertical_zx.toml"
    write_type1_toml(toml_path)
    spec, _ = load_toml_bytes(toml_path)

    _, result = _first_feasible_result(spec, seed=5)

    assert int(result.selected_parameters["tx_vertical_orientation_mode"]) == 1
    assert result.selected_parameters["tx_vertical_plane"] == "ZX"


def test_example_spec_keeps_tx_vertical_count_sampling_active_for_mode1(tmp_path: Path) -> None:
    toml_path = tmp_path / "type1.toml"
    write_type1_toml(toml_path)
    spec, _ = load_toml_bytes(toml_path)

    seen_requested_counts: set[int] = set()
    for seed in range(500):
        _, result = _first_feasible_result(spec, seed=seed)
        if int(result.selected_parameters["tx_vertical_orientation_mode"]) != 1:
            continue
        tx_vertical_group = cast(
            ResolvedTxVerticalGroup,
            next(group for group in result.selected_coil_groups if group["kind"] == "tx_vertical"),
        )
        seen_requested_counts.add(int(tx_vertical_group["requested_count"]))
        if len(seen_requested_counts) >= 2 and max(seen_requested_counts) > 1:
            break

    assert max(seen_requested_counts) > 1


def test_tx_vertical_orientation_and_tx_dd_stacked_mode_are_not_coupled(tmp_path: Path) -> None:
    toml_path = tmp_path / "type1.toml"
    write_type1_toml(toml_path)
    spec, _ = load_toml_bytes(toml_path)
    registry = build_sampling_registry(spec)

    seen_combos: set[tuple[int, int]] = set()
    for seed in range(500):
        context = SamplingLedger(registry, seed=seed, attempt=0)
        raw = resolve_selected_scalars(spec, seed, 0, context)
        selected = _build_selected_parameters(spec, raw)
        groups = resolve_coil_groups(spec, seed, 0, selected, context)
        tx_dd_group = cast(ResolvedTxDdGroup, next(group for group in groups if group["kind"] == "tx_dd"))
        seen_combos.add((int(selected["tx_vertical_orientation_mode"]), int(tx_dd_group["layer_count"])))
        if len(seen_combos) == 2:
            break

    assert seen_combos == {(1, 1), (1, 2)}

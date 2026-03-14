from __future__ import annotations

from pathlib import Path
from collections import Counter

from peetsfea.spec.loader import TOMLTable, load_toml_bytes
from peetsfea.spec.resolver.api import _build_selected_parameters, resolve_selected_scalars
from peetsfea.spec.resolver.sampling import SamplingLedger, build_sampling_registry
from peetsfea.spec.resolver import resolve_selection, resolve_selection_result, resolve_selection_with_context
from peetsfea.spec.resolver.types import SelectionConstraintError, SelectionResult
from tests.fixtures.type1_spec import write_type1_toml


def _first_feasible_result(spec: TOMLTable, *, seed: int) -> tuple[int, SelectionResult]:
    for attempt in range(16):
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

    assert "coil_placement.tx_vertical_layout_mode" in result.sampling_ledger.recorded_paths()
    assert "coil_groups[1].count_range" in result.sampling_ledger.recorded_paths()
    assert result.sampling_ledger.sorted_recorded_paths() == tuple(sorted(result.sampling_ledger.recorded_paths()))


def test_ferrite_present_sampling_is_deterministic_and_reaches_both_states(tmp_path: Path) -> None:
    toml_path = tmp_path / "type1.toml"
    write_type1_toml(toml_path)
    spec, _ = load_toml_bytes(toml_path)
    registry = build_sampling_registry(spec)

    seen_by_seed: dict[int, bool] = {}
    seen_states: set[bool] = set()
    for seed in range(8):
        context_a = SamplingLedger(registry)
        raw_a = resolve_selected_scalars(spec, seed, 0, context_a)
        selected_a = _build_selected_parameters(spec, raw_a)
        context_b = SamplingLedger(registry)
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


def test_tx_dd_top_clearance_ratio_derives_mm_clearance(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_dd_top_clearance_ratio.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "[coil_placement.tx_dd_top_clearance_ratio]\nrange = [false, 0.0, 0.3, 10]",
        "[coil_placement.tx_dd_top_clearance_ratio]\nrange = [false, 0.3, 0.3, 1]",
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")
    spec, _ = load_toml_bytes(toml_path)

    _, result = _first_feasible_result(spec, seed=5)

    assert float(result.selected_parameters["tx_dd_top_clearance_ratio"]) == 0.3
    assert float(result.selected_parameters["tx_dd_top_clearance_mm"]) == 2.1


def test_tx_vertical_layout_mode_derives_realized_plane(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_vertical_mode2.toml"
    write_type1_toml(toml_path, tx_region_h=320.0, outer_x=100.0)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 1, 2, 2]",
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 2, 2, 1]",
        1,
    )
    raw = raw.replace(
        "[coil_spacing.tx_vertical_mode2_pair_spacing_ratio]\nrange = [false, 0.0, 0.03, 25]",
        "[coil_spacing.tx_vertical_mode2_pair_spacing_ratio]\nrange = [false, 0.03, 0.03, 1]",
        1,
    )
    raw = raw.replace(
        "[coil_placement.tx_vertical_mode2_x_ratio_to_tx_dd_center]\nrange = [false, 0.7, 1.0, 10]",
        "[coil_placement.tx_vertical_mode2_x_ratio_to_tx_dd_center]\nrange = [false, 1.0, 1.0, 1]",
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")
    spec, _ = load_toml_bytes(toml_path)

    _, result = _first_feasible_result(spec, seed=5)

    assert int(result.selected_parameters["tx_vertical_layout_mode"]) == 2
    assert float(result.selected_parameters["tx_vertical_mode2_pair_spacing_ratio"]) == 0.03
    assert float(result.selected_parameters["tx_vertical_mode2_pair_spacing_mm"]) == 9.6
    assert float(result.selected_parameters["tx_vertical_mode2_x_ratio_to_tx_dd_center"]) == 1.0
    assert result.selected_parameters["tx_vertical_plane"] == "YZ"


def test_tx_vertical_mode2_clamps_selected_count_to_one(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_vertical_mode2_count_clamp.toml"
    write_type1_toml(toml_path, tx_region_h=320.0, outer_x=100.0)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "count_range = [true, 1, 1, 1]",
        "count_range = [true, 6, 6, 1]",
        1,
    )
    raw = raw.replace(
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 1, 2, 2]",
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 2, 2, 1]",
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")
    spec, _ = load_toml_bytes(toml_path)

    _, result = _first_feasible_result(spec, seed=5)

    groups_by_kind = {group["kind"]: group for group in result.selected_coil_groups}
    assert int(groups_by_kind["tx_vertical"]["requested_count"]) == 6
    assert int(groups_by_kind["tx_vertical"]["selected_count"]) == 1
    assert float(result.selected_parameters["tx_vertical_span_mm"]) == 0.0


def test_raw_sampled_tx_vertical_layout_mode_is_evenly_split_on_attempt_zero(tmp_path: Path) -> None:
    toml_path = tmp_path / "type1.toml"
    write_type1_toml(toml_path)
    spec, _ = load_toml_bytes(toml_path)
    registry = build_sampling_registry(spec)

    counts: Counter[int] = Counter()
    for seed in range(500):
        context = SamplingLedger(registry)
        raw = resolve_selected_scalars(spec, seed, 0, context)
        selected = _build_selected_parameters(spec, raw)
        counts[int(selected["tx_vertical_layout_mode"])] += 1

    assert counts == Counter({1: 250, 2: 250})

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

import peetsfea.pipeline.run_design as runner
import peetsfea.spec.resolver.constraints_eval as constraints_eval
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.resolver import SelectionConstraintError, resolve_selection
from peetsfea.spec.resolver.types import GroupKind
from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup
from tests.fixtures.type1_spec import write_type1_toml


def _append_tx_bridge_margin_rule(raw: str, *, margin_mm: float = 1.0) -> str:
    return raw + (
        "\n[[constraints.rules]]\n"
        "id = \"tx_bridge_right_margin\"\n"
        "kind = \"comparison\"\n"
        "message = \"tx_dd right representative y must be >= tx_vertical right representative y + margin\"\n"
        f"lhs = {{ func = \"tx_bridge_right_y_margin_ok({margin_mm})\" }}\n"
        "op = \"==\"\n"
        "rhs = { value = 1.0 }\n"
    )


def _stabilize_group_geometry_sampling(raw: str) -> str:
    out = raw
    out = out.replace(
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 2, 3, 2]",
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    out = out.replace(
        "[coil_groups_params.tx_dd.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.tx_dd.band_ratio]\nrange = [false, 0.2, 0.2, 1]",
    )
    out = out.replace(
        "[coil_groups_params.tx_dd.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.tx_dd.metal_ratio]\nrange = [false, 0.5, 0.5, 1]",
    )
    out = out.replace(
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 2, 3, 2]",
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    out = out.replace(
        "[coil_groups_params.tx_vertical.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.tx_vertical.band_ratio]\nrange = [false, 0.2, 0.2, 1]",
    )
    out = out.replace(
        "[coil_groups_params.tx_vertical.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.tx_vertical.metal_ratio]\nrange = [false, 0.5, 0.5, 1]",
    )
    out = out.replace(
        "[coil_groups_params.rx_dd.turn_count_max]\nrange = [true, 2, 3, 2]",
        "[coil_groups_params.rx_dd.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    out = out.replace(
        "[coil_groups_params.rx_dd.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.rx_dd.band_ratio]\nrange = [false, 0.2, 0.2, 1]",
    )
    out = out.replace(
        "[coil_groups_params.rx_dd.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.rx_dd.metal_ratio]\nrange = [false, 0.5, 0.5, 1]",
    )
    out = out.replace(
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 1, 2, 2]",
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 1, 1, 1]",
    )
    out = out.replace(
        "[coil_spacing.tx_vertical_mode2_pair_spacing_ratio]\nrange = [false, 0.0, 0.03, 25]",
        "[coil_spacing.tx_vertical_mode2_pair_spacing_ratio]\nrange = [false, 0.0, 0.0, 1]",
    )
    out = out.replace(
        "[coil_placement.tx_vertical_mode2_x_ratio_to_tx_dd_center]\nrange = [false, 0.7, 1.0, 10]",
        "[coil_placement.tx_vertical_mode2_x_ratio_to_tx_dd_center]\nrange = [false, 1.0, 1.0, 1]",
    )
    return out


def test_tx_region_constraint_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_geom.toml"
    write_type1_toml(toml_path, outer_x=320.0)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("f" * 40))

    with pytest.raises(RuntimeError, match="No valid selection within max attempts"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))

def test_feasibility_constraint_blocks_infeasible_tx_vertical(tmp_path: Path) -> None:
    toml_path = tmp_path / "feasibility_fail.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace(
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 2, 3, 2]",
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.tx_dd.band_ratio]\nrange = [false, 0.2, 0.2, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.tx_dd.metal_ratio]\nrange = [false, 0.5, 0.5, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 2, 3, 2]",
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 2, 3, 2]",
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.tx_dd.band_ratio]\nrange = [false, 0.2, 0.2, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.tx_dd.metal_ratio]\nrange = [false, 0.5, 0.5, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.rx_dd.turn_count_max]\nrange = [true, 2, 3, 2]",
        "[coil_groups_params.rx_dd.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.rx_dd.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.rx_dd.band_ratio]\nrange = [false, 0.2, 0.2, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.rx_dd.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.rx_dd.metal_ratio]\nrange = [false, 0.5, 0.5, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.tx_vertical.band_ratio]\nrange = [false, 0.9, 0.9, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.tx_vertical.metal_ratio]\nrange = [false, 0.85, 0.85, 1]",
    )
    raw = raw.replace("count_range = [true, 1, 6, 6]", "count_range = [true, 1, 1, 1]")
    raw += (
        "\n[[constraints.rules]]\n"
        "id = \"tx_vertical_feasible_turns_for_active_group\"\n"
        "kind = \"comparison\"\n"
        "message = \"tx_vertical active group must support >=1 feasible turn in capped vertical zone\"\n"
        "lhs = { func = \"feasible_turns(tx_vertical,outer_x,outer_y,tx_region_vertical_z_mm)\" }\n"
        "op = \">=\"\n"
        "rhs = { func = \"active_group(tx_vertical)\" }\n"
    )
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(SelectionConstraintError, match=r"tx_vertical_turn_count_within_feasible_max|tx_vertical_feasible_turns_for_active_group"):
        resolve_selection(spec=spec, seed=2, attempt=0)

def test_tx_vertical_center_gap_range_fails(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_vertical_center_gap_fail.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace("count_range = [true, 1, 6, 6]", "count_range = [true, 6, 6, 1]")
    raw = raw.replace(
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 1, 2, 2]",
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace("rhs = { value = 10.0 }", "rhs = { value = 20.0 }", 1)
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 2, 3, 2]",
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 2, 3, 2]",
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.tx_dd.band_ratio]\nrange = [false, 0.2, 0.2, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.tx_dd.metal_ratio]\nrange = [false, 0.5, 0.5, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.rx_dd.turn_count_max]\nrange = [true, 2, 3, 2]",
        "[coil_groups_params.rx_dd.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.rx_dd.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.rx_dd.band_ratio]\nrange = [false, 0.2, 0.2, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.rx_dd.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.rx_dd.metal_ratio]\nrange = [false, 0.5, 0.5, 1]",
    )
    raw = raw.replace(
        "[coil_spacing.tx_vertical_center_gap_mm]\nrange = [false, 1.62, 15.0, 4]",
        "[coil_spacing.tx_vertical_center_gap_mm]\nrange = [false, 1.5, 1.5, 1]",
    )
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(SelectionConstraintError, match=r"Constraint tx_vertical_center_gap_range failed"):
        resolve_selection(spec=spec, seed=1, attempt=0)

def test_tx_vertical_span_is_derived_from_center_gap_and_count(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_vertical_span_derived.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace("count_range = [true, 1, 6, 6]", "count_range = [true, 6, 6, 1]")
    raw = raw.replace(
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 1, 2, 2]",
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace("rhs = { value = 10.0 }", "rhs = { value = 20.0 }", 1)
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 2, 3, 2]",
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 2, 3, 2]",
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.tx_dd.band_ratio]\nrange = [false, 0.2, 0.2, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.tx_dd.metal_ratio]\nrange = [false, 0.5, 0.5, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.rx_dd.turn_count_max]\nrange = [true, 2, 3, 2]",
        "[coil_groups_params.rx_dd.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.rx_dd.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.rx_dd.band_ratio]\nrange = [false, 0.2, 0.2, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.rx_dd.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.rx_dd.metal_ratio]\nrange = [false, 0.5, 0.5, 1]",
    )
    raw = raw.replace(
        "[coil_spacing.tx_vertical_center_gap_mm]\nrange = [false, 1.62, 15.0, 4]",
        "[coil_spacing.tx_vertical_center_gap_mm]\nrange = [false, 1.62, 1.62, 1]",
    )
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    selected, _, groups, _, _ = resolve_selection(spec=spec, seed=1, attempt=0)
    groups_by_kind = {group["kind"]: group for group in groups}
    assert int(groups_by_kind["tx_vertical"]["selected_count"]) == 6
    assert float(selected["tx_vertical_center_gap_mm"]) == pytest.approx(1.62)
    assert float(selected["tx_vertical_span_mm"]) == pytest.approx(8.1)

def test_ratio_hard_check_failure_contains_details(tmp_path: Path) -> None:
    toml_path = tmp_path / "ratio_fail.toml"
    write_type1_toml(toml_path, tx_region_h=200.0, outer_y=120.0)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace(
        "[coil_spacing.tx_dd_pair_spacing_ratio]\nrange = [false, 0.0, 0.12, 25]",
        "[coil_spacing.tx_dd_pair_spacing_ratio]\nrange = [false, 0.12, 0.12, 1]",
    )
    raw = raw.replace("count_mode = [true, 2, 4, 2]", "count_mode = [true, 2, 2, 1]")
    toml_path.write_text(raw, encoding="utf-8")
    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(SelectionConstraintError, match="Constraint tx_dd_pair_fits_region failed"):
        resolve_selection(spec=spec, seed=1, attempt=0)


def test_tx_bridge_right_margin_rule_passes_when_dd_is_right_enough(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_bridge_right_margin_pass.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = _stabilize_group_geometry_sampling(raw)
    raw = raw.replace("count_mode = [true, 2, 4, 2]", "count_mode = [true, 2, 2, 1]")
    raw = raw.replace("count_range = [true, 1, 6, 6]", "count_range = [true, 1, 1, 1]")
    raw = _append_tx_bridge_margin_rule(raw, margin_mm=1.0)
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    resolve_selection(spec=spec, seed=1, attempt=0)


def test_tx_bridge_right_margin_rule_skips_for_yz_mode(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_bridge_right_margin_yz_skip.toml"
    write_type1_toml(toml_path, tx_region_h=320.0, outer_x=100.0)
    raw = _stabilize_group_geometry_sampling(toml_path.read_text(encoding="utf-8"))
    raw = raw.replace(
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 1, 1, 1]",
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 2, 2, 1]",
        1,
    )
    raw = raw.replace(
        "[coil_placement.tx_vertical_mode2_x_ratio_to_tx_dd_center]\nrange = [false, 0.7, 1.0, 10]",
        "[coil_placement.tx_vertical_mode2_x_ratio_to_tx_dd_center]\nrange = [false, 1.0, 1.0, 1]",
        1,
    )
    raw = _append_tx_bridge_margin_rule(raw, margin_mm=1.0)
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    selected, _, groups, group_geometry, pcbs = resolve_selection(spec=spec, seed=1, attempt=0)
    groups_by_kind = cast(dict[GroupKind, ResolvedCoilGroup], {group["kind"]: group for group in groups})
    geometry_by_kind = cast(
        dict[GroupKind, GroupGeometryParams],
        {entry["kind"]: entry for entry in group_geometry},
    )
    value, debug = constraints_eval.resolve_func_ref(
        selected=selected,
        group_geometry_by_kind=geometry_by_kind,
        coil_groups_by_kind=groups_by_kind,
        pcbs=pcbs,
        func_text="tx_bridge_right_y_margin_ok(1.0)",
    )

    assert value == 1.0
    assert debug == "func=tx_bridge_right_y_margin_ok skipped because tx_vertical_plane == 'YZ'"


def test_tx_bridge_no_pierce_rule_skips_for_yz_mode(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_bridge_no_pierce_yz_skip.toml"
    write_type1_toml(toml_path, tx_region_h=320.0, outer_x=100.0)
    raw = _stabilize_group_geometry_sampling(toml_path.read_text(encoding="utf-8"))
    raw = raw.replace(
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 1, 1, 1]",
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 2, 2, 1]",
        1,
    )
    raw = raw.replace(
        "[coil_placement.tx_vertical_mode2_x_ratio_to_tx_dd_center]\nrange = [false, 0.7, 1.0, 10]",
        "[coil_placement.tx_vertical_mode2_x_ratio_to_tx_dd_center]\nrange = [false, 1.0, 1.0, 1]",
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    selected, _, groups, group_geometry, pcbs = resolve_selection(spec=spec, seed=1, attempt=0)
    groups_by_kind = cast(dict[GroupKind, ResolvedCoilGroup], {group["kind"]: group for group in groups})
    geometry_by_kind = cast(
        dict[GroupKind, GroupGeometryParams],
        {entry["kind"]: entry for entry in group_geometry},
    )
    value, debug = constraints_eval.resolve_func_ref(
        selected=selected,
        group_geometry_by_kind=geometry_by_kind,
        coil_groups_by_kind=groups_by_kind,
        pcbs=pcbs,
        func_text="tx_bridge_no_pierce_ok(0.0)",
    )

    assert value == 1.0
    assert debug == "func=tx_bridge_no_pierce_ok skipped because tx_vertical_plane == 'YZ'"


def test_tx_vertical_mode2_pair_y_in_region_rule_fails_when_pair_is_too_wide(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_vertical_mode2_pair_y_in_region_fail.toml"
    write_type1_toml(toml_path)
    raw = _stabilize_group_geometry_sampling(toml_path.read_text(encoding="utf-8"))
    raw = raw.replace(
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 1, 1, 1]",
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 2, 2, 1]",
        1,
    )
    raw = raw.replace(
        "[coil_spacing.tx_vertical_mode2_pair_spacing_ratio]\nrange = [false, 0.0, 0.0, 1]",
        "[coil_spacing.tx_vertical_mode2_pair_spacing_ratio]\nrange = [false, 0.03, 0.03, 1]",
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(SelectionConstraintError, match=r"Constraint tx_vertical_mode2_pair_y_in_region failed"):
        resolve_selection(spec=spec, seed=1, attempt=0)


def test_tx_vertical_mode2_pair_y_in_region_rule_passes_when_pair_fits(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_vertical_mode2_pair_y_in_region_pass.toml"
    write_type1_toml(toml_path, tx_region_h=320.0, outer_x=100.0)
    raw = _stabilize_group_geometry_sampling(toml_path.read_text(encoding="utf-8"))
    raw = raw.replace(
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 1, 1, 1]",
        "[coil_placement.tx_vertical_layout_mode]\nrange = [true, 2, 2, 1]",
        1,
    )
    raw = raw.replace(
        "[coil_spacing.tx_vertical_mode2_pair_spacing_ratio]\nrange = [false, 0.0, 0.0, 1]",
        "[coil_spacing.tx_vertical_mode2_pair_spacing_ratio]\nrange = [false, 0.03, 0.03, 1]",
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    selected, _, groups, group_geometry, pcbs = resolve_selection(spec=spec, seed=1, attempt=0)
    groups_by_kind = cast(dict[GroupKind, ResolvedCoilGroup], {group["kind"]: group for group in groups})
    geometry_by_kind = cast(
        dict[GroupKind, GroupGeometryParams],
        {entry["kind"]: entry for entry in group_geometry},
    )
    value, debug = constraints_eval.resolve_func_ref(
        selected=selected,
        group_geometry_by_kind=geometry_by_kind,
        coil_groups_by_kind=groups_by_kind,
        pcbs=pcbs,
        func_text="tx_vertical_mode2_pair_y_in_region_ok()",
    )

    assert value == 1.0
    assert "ok=True" in cast(str, debug)


def test_one_turn_selection_succeeds_for_all_groups_with_two_layer_txdd(tmp_path: Path) -> None:
    toml_path = tmp_path / "one_turn_two_layer.toml"
    write_type1_toml(toml_path)
    raw = _stabilize_group_geometry_sampling(toml_path.read_text(encoding="utf-8"))
    raw = raw.replace("count_mode = [true, 2, 4, 2]", "count_mode = [true, 2, 2, 1]")
    raw = raw.replace("count_range = [true, 1, 6, 6]", "count_range = [true, 1, 1, 1]")
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    _, _, groups, group_geometry, _ = resolve_selection(spec=spec, seed=1, attempt=0)
    groups_by_kind = {group["kind"]: group for group in groups}
    turns_by_kind = {entry["kind"]: int(entry["turn_count_max"]) for entry in group_geometry}

    assert int(groups_by_kind["tx_dd"]["selected_count"]) == 2
    assert turns_by_kind == {"tx_dd": 1, "tx_vertical": 1, "rx_dd": 1}


def test_one_turn_selection_succeeds_for_all_groups_with_four_layer_txdd(tmp_path: Path) -> None:
    toml_path = tmp_path / "one_turn_four_layer.toml"
    write_type1_toml(toml_path)
    raw = _stabilize_group_geometry_sampling(toml_path.read_text(encoding="utf-8"))
    raw = raw.replace("count_mode = [true, 2, 4, 2]", "count_mode = [true, 4, 4, 1]")
    raw = raw.replace("count_range = [true, 1, 6, 6]", "count_range = [true, 1, 1, 1]")
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    _, _, groups, group_geometry, _ = resolve_selection(spec=spec, seed=1, attempt=0)
    groups_by_kind = {group["kind"]: group for group in groups}
    turns_by_kind = {entry["kind"]: int(entry["turn_count_max"]) for entry in group_geometry}

    assert int(groups_by_kind["tx_dd"]["selected_count"]) == 4
    assert turns_by_kind == {"tx_dd": 1, "tx_vertical": 1, "rx_dd": 1}


def test_tx_bridge_right_margin_rule_fails_when_dd_is_left_of_vertical(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_bridge_right_margin_fail.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = _stabilize_group_geometry_sampling(raw)
    raw = raw.replace("count_mode = [true, 2, 4, 2]", "count_mode = [true, 2, 2, 1]")
    raw = raw.replace("count_range = [true, 1, 6, 6]", "count_range = [true, 1, 1, 1]")
    raw = raw.replace(
        "[[coil_groups]]\nkind = \"tx_dd\"\ncount_mode = [true, 2, 2, 1]\ninstance_transforms = [{ dx = 0.0, dy = 0.0, dz = 0.0, rot_deg = 0.0 }]",
        "[[coil_groups]]\nkind = \"tx_dd\"\ncount_mode = [true, 2, 2, 1]\ninstance_transforms = [{ dx = 0.0, dy = -90.0, dz = 0.0, rot_deg = 0.0 }]",
    )
    raw = _append_tx_bridge_margin_rule(raw, margin_mm=1.0)
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(
        SelectionConstraintError,
        match=r"Constraint tx_bridge_right_margin failed.*dd_right_edge_y=.*vertical_right_edge_y=",
    ):
        resolve_selection(spec=spec, seed=1, attempt=0)


def test_tx_bridge_right_margin_rule_blocks_case_that_center_only_logic_would_allow(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_bridge_right_margin_center_vs_edge_regression.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = _stabilize_group_geometry_sampling(raw)
    raw = raw.replace("count_mode = [true, 2, 4, 2]", "count_mode = [true, 2, 2, 1]")
    raw = raw.replace("count_range = [true, 1, 6, 6]", "count_range = [true, 5, 5, 1]")
    toml_path.write_text(raw, encoding="utf-8")

    spec_without_rule, _ = load_toml_bytes(toml_path)
    selected, _, groups, group_geometry, pcbs = resolve_selection(spec=spec_without_rule, seed=0, attempt=0)
    groups_by_kind = {group["kind"]: group for group in groups}
    geometry_by_kind = {entry["kind"]: entry for entry in group_geometry}
    tx_dd_group = groups_by_kind["tx_dd"]
    tx_vertical_group = groups_by_kind["tx_vertical"]
    tx_vertical_geometry = geometry_by_kind["tx_vertical"]
    tx_region_outer_h = float(selected["tx_region_outer_h_mm"])
    tx_region_min_y = -tx_region_outer_h / 2.0
    tx_region_max_y = tx_region_outer_h / 2.0
    tx_region_center_y = (tx_region_min_y + tx_region_max_y) / 2.0

    tx_dd_transform_dy = float(tx_dd_group["instance_transforms"][0]["dy"])
    dd_center_candidate: float | None = None
    dd_center_key: tuple[float, str, int] | None = None
    for pcb in pcbs:
        if not pcb["present"]:
            continue
        for instance_index in range(int(tx_dd_group["selected_count"])):
            if instance_index % 2 == 0:
                continue
            if not constraints_eval._mount_allows_instance(pcb["mounts"], "tx_dd", instance_index):
                continue
            center_y, _ = constraints_eval._tx_dd_center_y_and_layer(
                instance_count=int(tx_dd_group["selected_count"]),
                instance_index=instance_index,
                pair_clearance_mm=float(tx_dd_group["spacing_mm"]),
                outer_y=float(selected["tx_dd_outer_y"]),
                region_center_y=tx_region_center_y,
                region_min_y=tx_region_min_y,
                region_max_y=tx_region_max_y,
            )
            world_center_y = center_y + tx_dd_transform_dy
            key = (-world_center_y, pcb["id"], instance_index)
            if dd_center_key is None or key < dd_center_key:
                dd_center_key = key
                dd_center_candidate = world_center_y

    tx_vertical_transform_dy = float(tx_vertical_group["instance_transforms"][0]["dy"])
    vertical_center_candidate: float | None = None
    vertical_center_key: tuple[float, str, int] | None = None
    for pcb in pcbs:
        if not pcb["present"]:
            continue
        for instance_index in range(int(tx_vertical_group["selected_count"])):
            if not constraints_eval._mount_allows_instance(pcb["mounts"], "tx_vertical", instance_index):
                continue
            off_y = constraints_eval._tx_vertical_instance_offset_y(
                instance_index=instance_index,
                instance_count=int(tx_vertical_group["selected_count"]),
                spacing_mm=float(tx_vertical_group["spacing_mm"]),
                trace_mm=float(tx_vertical_geometry["trace"]),
            )
            world_center_y = tx_region_center_y + tx_vertical_transform_dy + off_y
            key = (-world_center_y, pcb["id"], instance_index)
            if vertical_center_key is None or key < vertical_center_key:
                vertical_center_key = key
                vertical_center_candidate = world_center_y

    assert dd_center_candidate is not None
    assert vertical_center_candidate is not None
    assert dd_center_candidate >= (vertical_center_candidate + 1.0)

    raw_with_rule = _append_tx_bridge_margin_rule(raw, margin_mm=1.0)
    toml_path.write_text(raw_with_rule, encoding="utf-8")
    spec_with_rule, _ = load_toml_bytes(toml_path)
    with pytest.raises(
        SelectionConstraintError,
        match=r"Constraint tx_bridge_right_margin failed.*dd_right_edge_y=.*vertical_right_edge_y=",
    ):
        resolve_selection(spec=spec_with_rule, seed=0, attempt=0)


def test_tx_vertical_count_zero_is_rejected(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_bridge_right_margin_vertical_zero.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = _stabilize_group_geometry_sampling(raw)
    raw = raw.replace("count_mode = [true, 2, 4, 2]", "count_mode = [true, 2, 2, 1]")
    raw = raw.replace("count_range = [true, 1, 6, 6]", "count_range = [true, 0, 0, 1]")
    raw = raw.replace(
        "[[coil_groups]]\nkind = \"tx_dd\"\ncount_mode = [true, 2, 2, 1]\ninstance_transforms = [{ dx = 0.0, dy = 0.0, dz = 0.0, rot_deg = 0.0 }]",
        "[[coil_groups]]\nkind = \"tx_dd\"\ncount_mode = [true, 2, 2, 1]\ninstance_transforms = [{ dx = 0.0, dy = -120.0, dz = 0.0, rot_deg = 0.0 }]",
    )
    raw = _append_tx_bridge_margin_rule(raw, margin_mm=1.0)
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(ValueError, match=r"tx_vertical count_range must resolve to \[1,6\]"):
        resolve_selection(spec=spec, seed=1, attempt=0)


def test_tx_bridge_right_margin_rule_rejects_negative_margin(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_bridge_right_margin_negative_margin.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = _stabilize_group_geometry_sampling(raw)
    raw = raw.replace("count_mode = [true, 2, 4, 2]", "count_mode = [true, 2, 2, 1]")
    raw = raw.replace("count_range = [true, 1, 6, 6]", "count_range = [true, 1, 1, 1]")
    raw = _append_tx_bridge_margin_rule(raw, margin_mm=-1.0)
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(ValueError, match=r"margin_mm must be >= 0"):
        resolve_selection(spec=spec, seed=1, attempt=0)


def test_tx_bridge_right_margin_rule_requires_single_argument(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_bridge_right_margin_bad_arity.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = _stabilize_group_geometry_sampling(raw)
    raw = raw.replace("count_mode = [true, 2, 4, 2]", "count_mode = [true, 2, 2, 1]")
    raw = raw.replace("count_range = [true, 1, 6, 6]", "count_range = [true, 1, 1, 1]")
    raw += (
        "\n[[constraints.rules]]\n"
        "id = \"tx_bridge_right_margin_bad_arity\"\n"
        "kind = \"comparison\"\n"
        "message = \"bad arity\"\n"
        "lhs = { func = \"tx_bridge_right_y_margin_ok()\" }\n"
        "op = \"==\"\n"
        "rhs = { value = 1.0 }\n"
    )
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(ValueError, match=r"must have 1 argument: margin_mm"):
        resolve_selection(spec=spec, seed=1, attempt=0)

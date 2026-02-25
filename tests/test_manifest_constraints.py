from __future__ import annotations

from pathlib import Path
import re

import pytest

import peetsfea.pipeline.run_design as runner
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.resolver import SelectionConstraintError, resolve_selection
from tests.fixtures.type1_spec import write_type1_toml

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
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 1, 20, 20]",
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
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 20, 20]",
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 1, 20, 20]",
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
        "[coil_groups_params.rx_dd.turn_count_max]\nrange = [true, 1, 20, 20]",
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
    raw = raw.replace("count_range = [true, 0, 7, 8]", "count_range = [true, 1, 1, 1]")
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
    raw = raw.replace("count_range = [true, 0, 7, 8]", "count_range = [true, 7, 7, 1]")
    raw = raw.replace("rhs = { value = 10.0 }", "rhs = { value = 20.0 }", 1)
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 20, 20]",
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 1, 20, 20]",
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
        "[coil_groups_params.rx_dd.turn_count_max]\nrange = [true, 1, 20, 20]",
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
    raw = raw.replace("count_range = [true, 0, 7, 8]", "count_range = [true, 7, 7, 1]")
    raw = raw.replace("rhs = { value = 10.0 }", "rhs = { value = 20.0 }", 1)
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 20, 20]",
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 1, 20, 20]",
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
        "[coil_groups_params.rx_dd.turn_count_max]\nrange = [true, 1, 20, 20]",
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
    assert int(groups_by_kind["tx_vertical"]["selected_count"]) == 7
    assert float(selected["tx_vertical_center_gap_mm"]) == pytest.approx(1.62)
    assert float(selected["tx_vertical_span_mm"]) == pytest.approx(9.72)

def test_ratio_hard_check_failure_contains_details(tmp_path: Path) -> None:
    toml_path = tmp_path / "ratio_fail.toml"
    write_type1_toml(toml_path, tx_region_h=200.0, outer_y=120.0)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace(
        "[coil_spacing.tx_dd_pair_spacing_ratio]\nrange = [false, 0.0, 0.12, 6]",
        "[coil_spacing.tx_dd_pair_spacing_ratio]\nrange = [false, 0.12, 0.12, 1]",
    )
    raw = raw.replace("count_mode = [true, 2, 4, 2]", "count_mode = [true, 2, 2, 1]")
    toml_path.write_text(raw, encoding="utf-8")
    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(SelectionConstraintError, match="Constraint tx_dd_pair_fits_region failed"):
        resolve_selection(spec=spec, seed=1, attempt=0)


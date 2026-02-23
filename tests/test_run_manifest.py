from __future__ import annotations

from pathlib import Path
import re

import pytest

import peetsfea.pipeline.run_design as runner


def _write_toml(path: Path, *, tx_region_h: float = 200.0, outer_x: float = 220.0, outer_y: float = 180.0) -> None:
    path.write_text(
        "\n".join(
            [
                'spec_version = "0.1.5"',
                "",
                "[design]",
                'units = "mm"',
                "",
                "[backend]",
                'tool = "hfss"',
                "",
                "[tv.width_mm]",
                "range = [false, 1200.0, 1200.0, 1]",
                "[tv.height_mm]",
                "range = [false, 700.0, 700.0, 1]",
                "[tv.thickness_mm]",
                "range = [false, 9.0, 9.0, 1]",
                "[tv.base_z_mm]",
                "range = [false, 700.0, 700.0, 1]",
                "",
                "[tx.region.outer_w_mm]",
                "range = [false, 300.0, 300.0, 1]",
                "[tx.region.outer_h_mm]",
                f"range = [false, {tx_region_h:.1f}, {tx_region_h:.1f}, 1]",
                "[tx.region.thickness_mm]",
                "range = [false, 20.0, 20.0, 1]",
                "[tx.region.z_parts.vertical_z_mm]",
                "range = [false, 8.0, 8.0, 1]",
                "[tx.region.z_parts.dd_z_mm]",
                "range = [false, 7.0, 7.0, 1]",
                "",
                "[rx.region.outer_w_mm]",
                "range = [false, 280.0, 280.0, 1]",
                "[rx.region.outer_h_mm]",
                "range = [false, 180.0, 180.0, 1]",
                "[rx.region.thickness_mm]",
                "range = [false, 4.0, 4.0, 1]",
                "",
                "[wall.thickness_mm]",
                "range = [false, 200.0, 200.0, 1]",
                "[wall.size_y_mm]",
                "range = [false, 4000.0, 4000.0, 1]",
                "[wall.size_z_mm]",
                "range = [false, 3000.0, 3000.0, 1]",
                "",
                "[floor.thickness_mm]",
                "range = [false, 300.0, 300.0, 1]",
                "[floor.size_x_mm]",
                "range = [false, 5000.0, 5000.0, 1]",
                "[floor.size_y_mm]",
                "range = [false, 5000.0, 5000.0, 1]",
                "",
                "[coil_shape.outer_x]",
                f"range = [false, {outer_x:.1f}, {outer_x:.1f}, 1]",
                "[coil_shape.outer_y]",
                f"range = [false, {outer_y:.1f}, {outer_y:.1f}, 1]",
                "[coil_shape.turn_count_max]",
                "range = [true, 8, 8, 1]",
                "[coil_shape.inner_margin_x]",
                "range = [false, 2.0, 2.0, 1]",
                "[coil_shape.inner_margin_y]",
                "range = [false, 2.0, 2.0, 1]",
                "[coil_spacing.tx_dd_pair_spacing_mm]",
                "range = [false, 40.0, 40.0, 1]",
                "[coil_spacing.rx_dd_pair_spacing_mm]",
                "range = [false, 40.0, 40.0, 1]",
                "[coil_spacing.tx_vertical_span_mm]",
                "range = [false, 10.0, 10.0, 1]",
                "",
                "[[trace_gap_profile.profiles]]",
                'id = "p1"',
                "[trace_gap_profile.profiles.trace]",
                'mode = "biased_linear"',
                "base = 0.8",
                "outer_bias = 0.08",
                "inner_bias = -0.06",
                "clamp_min = 0.2",
                "[trace_gap_profile.profiles.gap]",
                'mode = "biased_linear"',
                "base = 0.35",
                "outer_bias = 0.03",
                "inner_bias = -0.03",
                "clamp_min = 0.12",
                "",
                "[[trace_gap_profile.profiles]]",
                'id = "p2"',
                "[trace_gap_profile.profiles.trace]",
                'mode = "biased_linear"',
                "base = 1.0",
                "outer_bias = 0.1",
                "inner_bias = -0.1",
                "clamp_min = 0.2",
                "[trace_gap_profile.profiles.gap]",
                'mode = "biased_linear"',
                "base = 0.5",
                "outer_bias = 0.05",
                "inner_bias = -0.05",
                "clamp_min = 0.15",
                "",
                "[[trace_gap_profile.profiles]]",
                'id = "p3"',
                "[trace_gap_profile.profiles.trace]",
                'mode = "biased_linear"',
                "base = 1.2",
                "outer_bias = 0.12",
                "inner_bias = -0.08",
                "clamp_min = 0.25",
                "[trace_gap_profile.profiles.gap]",
                'mode = "biased_linear"',
                "base = 0.6",
                "outer_bias = 0.07",
                "inner_bias = -0.04",
                "clamp_min = 0.2",
                "",
                "[[trace_gap_profile.profiles]]",
                'id = "p4"',
                "[trace_gap_profile.profiles.trace]",
                'mode = "biased_linear"',
                "base = 0.9",
                "outer_bias = 0.05",
                "inner_bias = -0.12",
                "clamp_min = 0.18",
                "[trace_gap_profile.profiles.gap]",
                'mode = "biased_linear"',
                "base = 0.45",
                "outer_bias = 0.02",
                "inner_bias = -0.08",
                "clamp_min = 0.14",
                "",
                "[[trace_gap_profile.profiles]]",
                'id = "p5"',
                "[trace_gap_profile.profiles.trace]",
                'mode = "biased_linear"',
                "base = 1.1",
                "outer_bias = 0.09",
                "inner_bias = -0.09",
                "clamp_min = 0.22",
                "[trace_gap_profile.profiles.gap]",
                'mode = "biased_linear"',
                "base = 0.55",
                "outer_bias = 0.06",
                "inner_bias = -0.06",
                "clamp_min = 0.17",
                "",
                "[constraints]",
                "[[constraints.rules]]",
                'id = "outer_x_positive"',
                'kind = "comparison"',
                'message = "outer_x must be > 0"',
                'lhs = { path = "outer_x" }',
                'op = ">"',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "outer_y_positive"',
                'kind = "comparison"',
                'message = "outer_y must be > 0"',
                'lhs = { path = "outer_y" }',
                'op = ">"',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "turn_count_min"',
                'kind = "comparison"',
                'message = "turn_count_max must be >= 1"',
                'lhs = { path = "turn_count_max" }',
                'op = ">="',
                "rhs = { value = 1.0 }",
                "",
                "[[constraints.rules]]",
                'id = "inner_margin_x_non_negative"',
                'kind = "comparison"',
                'message = "inner_margin_x must be >= 0"',
                'lhs = { path = "inner_margin_x" }',
                'op = ">="',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "inner_margin_y_non_negative"',
                'kind = "comparison"',
                'message = "inner_margin_y must be >= 0"',
                'lhs = { path = "inner_margin_y" }',
                'op = ">="',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "tx_dd_spacing_positive"',
                'kind = "comparison"',
                'message = "tx_dd_pair_spacing_mm must be > 0"',
                'lhs = { path = "tx_dd_pair_spacing_mm" }',
                'op = ">"',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "rx_dd_spacing_positive"',
                'kind = "comparison"',
                'message = "rx_dd_pair_spacing_mm must be > 0"',
                'lhs = { path = "rx_dd_pair_spacing_mm" }',
                'op = ">"',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "tx_vertical_span_range"',
                'kind = "range"',
                'message = "tx_vertical_span_mm must be in [0,15]"',
                'target = { path = "tx_vertical_span_mm" }',
                "min = { value = 0.0 }",
                "max = { value = 15.0 }",
                "inclusive_min = true",
                "inclusive_max = true",
                "",
                "[[constraints.rules]]",
                'id = "trace_clamp_positive"',
                'kind = "comparison"',
                'message = "trace_profile_clamp_min must be > 0"',
                'lhs = { path = "trace_profile_clamp_min" }',
                'op = ">"',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "gap_clamp_positive"',
                'kind = "comparison"',
                'message = "gap_profile_clamp_min must be > 0"',
                'lhs = { path = "gap_profile_clamp_min" }',
                'op = ">"',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "tx_region_outer_w_positive"',
                'kind = "comparison"',
                'message = "tx_region_outer_w_mm must be > 0"',
                'lhs = { path = "tx_region_outer_w_mm" }',
                'op = ">"',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "tx_region_outer_h_positive"',
                'kind = "comparison"',
                'message = "tx_region_outer_h_mm must be > 0"',
                'lhs = { path = "tx_region_outer_h_mm" }',
                'op = ">"',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "tx_region_thickness_positive"',
                'kind = "comparison"',
                'message = "tx_region_thickness_mm must be > 0"',
                'lhs = { path = "tx_region_thickness_mm" }',
                'op = ">"',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "tx_region_vertical_z_positive"',
                'kind = "comparison"',
                'message = "tx_region_vertical_z_mm must be > 0"',
                'lhs = { path = "tx_region_vertical_z_mm" }',
                'op = ">"',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "tx_region_dd_z_positive"',
                'kind = "comparison"',
                'message = "tx_region_dd_z_mm must be > 0"',
                'lhs = { path = "tx_region_dd_z_mm" }',
                'op = ">"',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "tx_region_leftover_non_negative"',
                'kind = "comparison"',
                'message = "tx.region.leftover_z_mm computed negative; reduce vertical_z/dd_z or increase tx.region.thickness_mm"',
                'lhs = { path = "tx_region_leftover_z_mm" }',
                'op = ">="',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "coil_outer_fits_tx_region"',
                'kind = "comparison"',
                'message = "TX coil outer must be < min(tx.region.outer_w_mm, tx.region.outer_h_mm)"',
                'lhs = { path = "outer" }',
                'op = "<"',
                'rhs = { func = "min(tx_region_outer_w_mm,tx_region_outer_h_mm)" }',
                "",
                "[[constraints.rules]]",
                'id = "max_total_selected_coils"',
                'kind = "aggregate"',
                'message = "Total selected coil count must be <= 10"',
                'agg = "sum_group_selected_count"',
                'op = "<="',
                "rhs = { value = 10.0 }",
                "",
                "[[coil_groups]]",
                'kind = "tx_dd"',
                "count_mode = [true, 2, 4, 2]",
                "instance_transforms = [{ dx = 0.0, dy = 0.0, dz = 0.0, rot_deg = 0.0 }]",
                "",
                "[[coil_groups]]",
                'kind = "tx_vertical"',
                "count_range = [true, 0, 4, 5]",
                "instance_transforms = [{ dx = 0.0, dy = 0.0, dz = 0.0, rot_deg = 0.0 }]",
                "",
                "[[coil_groups]]",
                'kind = "rx_dd"',
                "count_fixed = [true, 2, 2, 1]",
                "instance_transforms = [{ dx = 0.0, dy = 0.0, dz = 0.0, rot_deg = 180.0 }]",
                "",
                "[[pcbs]]",
                'id = "tx_main_0"',
                'role = "tx"',
                "position = [0.0, 0.0, 0.0]",
                "rotation_deg = 0.0",
                "present = [true, 1, 1, 1]",
                'mounts = ["tx_dd:0", "tx_vertical:*"]',
                "",
                "[[pcbs]]",
                'id = "rx_main_0"',
                'role = "rx"',
                "position = [0.0, 0.0, 110.0]",
                "rotation_deg = 0.0",
                "present = [true, 1, 1, 1]",
                'mounts = ["rx_dd:0"]',
            ]
        ),
        encoding="utf-8",
    )


def test_build_candidates_integer_round_and_dedup() -> None:
    values = runner._build_candidates(is_integer=True, start=0.0, end=1.0, count=5)
    assert list(values) == [0, 1]


def test_build_candidates_float() -> None:
    values = runner._build_candidates(is_integer=False, start=0.0, end=1.0, count=3)
    assert list(values) == [0.0, 0.5, 1.0]


def test_run_creates_manifest_and_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "spec.toml"
    _write_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("a" * 40))

    config = runner.RunConfig("/bin/ansysedt", str(tmp_path / "run"), str(toml_path), seed=1, backend="hfss")
    first = runner.run(config)
    second = runner.run(config)

    assert first["design_id"] == second["design_id"]
    assert first["selected_parameters"] == second["selected_parameters"]
    assert first["selected_parameters_max"] == second["selected_parameters_max"]
    assert first["selected_coil_groups"] == second["selected_coil_groups"]
    assert first["selected_pcbs"] == second["selected_pcbs"]
    assert first["design_id"].split("_")[0] == first["design_unique_hash"]
    assert first["design_id"].split("_")[1] == first["toml_space_hash"]
    assert re.fullmatch(r"[0-9a-f]{8}_[0-9a-f]{8}_-?[0-9]+", first["design_id"]) is not None
    assert first["selected_parameters"]["turn_count_max"] == 8
    assert first["selected_parameters"]["outer"] == 180.0
    assert first["selected_parameters"]["profile_id"] == "p2"
    assert first["selected_parameters"]["trace_profile_base"] == 1.0
    assert first["selected_parameters"]["gap_profile_base"] == 0.5
    assert first["selected_parameters"]["tx_region_vertical_z_mm"] == 8.0
    assert first["selected_parameters"]["tx_region_dd_z_mm"] == 7.0
    assert first["selected_parameters"]["rx_region_thickness_mm"] == first["selected_parameters_max"]["rx_region_thickness_mm"]
    assert first["selected_parameters_max"]["tx_region_outer_h_mm"] == 200.0
    assert first["selected_parameters_max"]["rx_region_thickness_mm"] == 4.0
    assert len(first["selected_coil_groups"]) == 3
    assert len(first["selected_pcbs"]) == 2
    assert first["manifest_path"].endswith(f"manifest_{first['design_id']}.json")


def test_run_seed_changes_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "spec.toml"
    _write_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("b" * 40))
    m1 = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))
    m2 = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=2, backend="hfss"))
    assert m1["design_id"] != m2["design_id"]
    assert m1["selected_parameters_max"] == m2["selected_parameters_max"]
    assert m1["selected_parameters"]["profile_id"] == "p2"
    assert m2["selected_parameters"]["profile_id"] == "p3"


def test_profile_selection_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "profile.toml"
    _write_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("1" * 40))
    m1 = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=7, backend="hfss"))
    m2 = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=7, backend="hfss"))
    assert m1["selected_parameters"]["profile_id"] == m2["selected_parameters"]["profile_id"]
    assert m1["selected_parameters"]["trace_profile_base"] == m2["selected_parameters"]["trace_profile_base"]
    assert m1["selected_parameters"]["gap_profile_base"] == m2["selected_parameters"]["gap_profile_base"]


def test_invalid_range_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace("range = [true, 8, 8, 1]", "range = [true, 8, 8, 0]")
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("c" * 40))
    with pytest.raises(ValueError, match="count"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_old_parameters_paths_unsupported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "old_path.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace("[coil_shape.outer_x]", "[parameters.outer_x]")
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("h" * 40))
    with pytest.raises(ValueError, match="Missing required path: coil_shape.outer_x"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_mount_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_mount.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace('mounts = ["rx_dd:0"]', 'mounts = ["rx_dd:5"]')
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("d" * 40))
    with pytest.raises(ValueError, match="Mount index out of range"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_profiles_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "missing_profiles.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    start = raw.index("[[trace_gap_profile.profiles]]")
    end = raw.index("\n[[coil_groups]]")
    raw = raw[:start] + "\n[trace_gap_profile]\nlegacy = true\n" + raw[end:]
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("2" * 40))
    with pytest.raises(ValueError, match="trace_gap_profile.profiles must be a non-empty array of tables"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_profiles_empty_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "empty_profiles.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    start = raw.index("[[trace_gap_profile.profiles]]")
    end = raw.index("\n[[coil_groups]]")
    raw = raw[:start] + "\n[trace_gap_profile]\nprofiles = []\n" + raw[end:]
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("3" * 40))
    with pytest.raises(ValueError, match="trace_gap_profile.profiles must contain at least one profile"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_profile_id_must_be_unique(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "dup_profile_id.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace('id = "p2"', 'id = "p1"', 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("4" * 40))
    with pytest.raises(ValueError, match="Duplicate trace_gap_profile.profiles id"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_profile_trace_and_gap_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "missing_gap_table.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace("[trace_gap_profile.profiles.gap]", "[trace_gap_profile.profiles.gap_removed]", 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("5" * 40))
    with pytest.raises(ValueError, match=r"trace_gap_profile\.profiles\[0\] must contain only"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_profile_mode_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_profile_mode.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace('mode = "biased_linear"', 'mode = "other"', 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("6" * 40))
    with pytest.raises(ValueError, match="mode must be 'biased_linear'"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_profile_clamp_min_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_profile_clamp.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace("clamp_min = 0.2", "clamp_min = 0.0", 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("7" * 40))
    with pytest.raises(ValueError, match="clamp_min must be > 0"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_constraints_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "missing_constraints.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    start = raw.index("[constraints]")
    end = raw.index("\n[[coil_groups]]")
    raw = raw[:start] + "\n" + raw[end:]
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("8" * 40))
    with pytest.raises(ValueError, match="constraints must be a table/object"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_constraints_empty_rules_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "empty_constraints_rules.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    start = raw.index("[constraints]")
    end = raw.index("\n[[coil_groups]]")
    raw = raw[:start] + "\n[constraints]\nrules = []\n" + raw[end:]
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("9" * 40))
    with pytest.raises(ValueError, match="constraints.rules must be a non-empty array of tables"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_constraints_duplicate_rule_id_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "dup_constraint_rule_id.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace('id = "outer_y_positive"', 'id = "outer_x_positive"', 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("a" * 40))
    with pytest.raises(ValueError, match="Duplicate constraints.rules id"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_constraints_invalid_kind_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_constraint_kind.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace('kind = "comparison"', 'kind = "bad_kind"', 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("b" * 40))
    with pytest.raises(ValueError, match=r"constraints\.rules\[0\]\.kind must be one of"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_constraints_invalid_operator_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_constraint_op.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace('op = ">"', 'op = "!="', 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("c" * 40))
    with pytest.raises(ValueError, match=r"constraints\.rules\[0\]\.op must be one of"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_constraints_invalid_aggregate_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_constraint_agg.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace('agg = "sum_group_selected_count"', 'agg = "sum_turns"', 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("d" * 40))
    with pytest.raises(ValueError, match=r"constraints\.rules\[[0-9]+\]\.agg must be 'sum_group_selected_count'"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_constraints_invalid_func_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_constraint_func.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace(
        'rhs = { func = "min(tx_region_outer_w_mm,tx_region_outer_h_mm)" }',
        'rhs = { func = "max(tx_region_outer_w_mm,tx_region_outer_h_mm)" }',
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("e" * 40))
    with pytest.raises(ValueError, match="rhs.func supports only min"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_constraints_unknown_path_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_constraint_path.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace('lhs = { path = "outer_x" }', 'lhs = { path = "not_a_key" }', 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("f" * 40))
    with pytest.raises(ValueError, match="Unknown constraint path: not_a_key"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_tx_region_constraint_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_geom.toml"
    _write_toml(toml_path, tx_region_h=160.0, outer_x=220.0, outer_y=180.0)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("e" * 40))
    with pytest.raises(ValueError, match="TX coil outer must be < min"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_tx_region_leftover_negative_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_tx_parts.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "[tx.region.z_parts.dd_z_mm]\nrange = [false, 7.0, 7.0, 1]",
        "[tx.region.z_parts.dd_z_mm]\nrange = [false, 15.0, 15.0, 1]",
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("f" * 40))
    with pytest.raises(ValueError, match="tx.region.leftover_z_mm computed negative"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_git_commit_lookup_failure_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "spec.toml"
    _write_toml(toml_path)
    monkeypatch.setattr(
        runner,
        "get_git_commit",
        lambda _: (_ for _ in ()).throw(RuntimeError("git commit lookup failed")),
    )
    with pytest.raises(RuntimeError):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))

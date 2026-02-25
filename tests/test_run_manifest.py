from __future__ import annotations

from pathlib import Path
import re

import pytest

import peetsfea.pipeline.run_design as runner
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.resolver import SelectionConstraintError, resolve_selection


def _write_toml(path: Path, *, tx_region_h: float = 200.0, outer_x: float = 140.0, outer_y: float = 80.0) -> None:
    path.write_text(
        "\n".join(
            [
                'spec_version = "0.2.2"',
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
                "[coil_shape.tx_dd.outer_x]",
                f"range = [false, {outer_x:.1f}, {outer_x:.1f}, 1]",
                "[coil_shape.tx_dd.outer_y]",
                f"range = [false, {outer_y:.1f}, {outer_y:.1f}, 1]",
                "[coil_shape.tx_vertical.outer_x]",
                "range = [false, -1, -1, -1]",
                "[coil_shape.tx_vertical.outer_y]",
                f"range = [false, {outer_y:.1f}, {outer_y:.1f}, 1]",
                "[coil_shape.rx_dd.outer_x]",
                "range = [false, 100.0, 100.0, 1]",
                "[coil_shape.rx_dd.outer_y]",
                f"range = [false, {outer_y:.1f}, {outer_y:.1f}, 1]",
                "[coil_shape.inner_margin_x]",
                "range = [false, 2.0, 2.0, 1]",
                "[coil_shape.inner_margin_y]",
                "range = [false, 2.0, 2.0, 1]",
                "[coil_spacing.tx_dd_pair_spacing_ratio]",
                "range = [false, 0.0, 0.12, 6]",
                "[coil_spacing.rx_dd_pair_spacing_ratio]",
                "range = [false, 0.0, 0.03, 8]",
                "[coil_spacing.tx_vertical_center_gap_mm]",
                "range = [false, 1.62, 15.0, 4]",
                "",
                "[coil_groups_params.tx_dd.turn_count_max]",
                "range = [true, 1, 20, 20]",
                "[coil_groups_params.tx_dd.band_ratio]",
                "range = [false, 0.1, 0.9, 81]",
                "[coil_groups_params.tx_dd.metal_ratio]",
                "range = [false, 0.15, 0.85, 71]",
                "",
                "[coil_groups_params.tx_vertical.turn_count_max]",
                "range = [true, 1, 20, 20]",
                "[coil_groups_params.tx_vertical.band_ratio]",
                "range = [false, 0.1, 0.9, 81]",
                "[coil_groups_params.tx_vertical.metal_ratio]",
                "range = [false, 0.15, 0.85, 71]",
                "",
                "[coil_groups_params.rx_dd.turn_count_max]",
                "range = [true, 1, 20, 20]",
                "[coil_groups_params.rx_dd.band_ratio]",
                "range = [false, 0.1, 0.9, 81]",
                "[coil_groups_params.rx_dd.metal_ratio]",
                "range = [false, 0.15, 0.85, 71]",
                "",
                "[coil_material.via_diameter_mm]",
                "range = [false, 0.5, 0.5, 1]",
                "[coil_material.pcb_thickness_mm]",
                "range = [false, 1.6, 1.6, 1]",
                "[coil_material.cu_thickness_mm]",
                "range = [false, 0.035, 0.035, 1]",
                "[coil_material.fr4_er]",
                "range = [false, 4.4, 4.4, 1]",
                "",
                "[scene_anchor.shelf_height_mm]",
                "range = [false, 400.0, 400.0, 1]",
                "[scene_anchor.shelf_min_size_x_mm]",
                "range = [false, 350.0, 350.0, 1]",
                "[scene_anchor.rx_region_bottom_from_tv_mm]",
                "range = [false, 1.0, 1.0, 1]",
                "",
                "[coil_placement.tx_dd_top_clearance_mm]",
                "range = [false, 0.0, 0.0, 1]",
                "[coil_placement.rx_face_clearance_mm]",
                "range = [false, 0.0, 0.0, 1]",
                "[coil_placement.dd_mirror_plane]",
                'value = "XZ"',
                "[coil_placement.rx_plane]",
                'value = "YZ"',
                "[coil_placement.tx_vertical_plane]",
                'value = "ZX"',
                "",
                "[pcb_spacing.tx_main_1_z_from_tx_main_0_mm]",
                "range = [false, 3.0, 10.0, 5]",
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
                'id = "tx_dd_spacing_positive"',
                'kind = "comparison"',
                'message = "tx_dd_pair_spacing_ratio must be >= 0"',
                'lhs = { path = "tx_dd_pair_spacing_ratio" }',
                'op = ">="',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "tx_dd_spacing_ratio_upper_bound"',
                'kind = "comparison"',
                'message = "tx_dd_pair_spacing_ratio must be <= 0.12"',
                'lhs = { path = "tx_dd_pair_spacing_ratio" }',
                'op = "<="',
                "rhs = { value = 0.12 }",
                "",
                "[[constraints.rules]]",
                'id = "rx_dd_spacing_positive"',
                'kind = "comparison"',
                'message = "rx_dd_pair_spacing_ratio must be >= 0"',
                'lhs = { path = "rx_dd_pair_spacing_ratio" }',
                'op = ">="',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "rx_dd_spacing_ratio_upper_bound"',
                'kind = "comparison"',
                'message = "rx_dd_pair_spacing_ratio must be <= 0.03"',
                'lhs = { path = "rx_dd_pair_spacing_ratio" }',
                'op = "<="',
                "rhs = { value = 0.03 }",
                "",
                "[[constraints.rules]]",
                'id = "tx_vertical_center_gap_range"',
                'kind = "range"',
                'message = "tx_vertical_center_gap_mm must be in [1.62,15]"',
                'target = { path = "tx_vertical_center_gap_mm" }',
                "min = { value = 1.62 }",
                "max = { value = 15.0 }",
                "inclusive_min = true",
                "inclusive_max = true",
                "",
                "[[constraints.rules]]",
                'id = "coil_outer_x_fits_tx_region"',
                'kind = "comparison"',
                'message = "TX coil outer_x must be < tx.region.outer_w_mm"',
                'lhs = { path = "outer_x" }',
                'op = "<"',
                'rhs = { path = "tx_region_outer_w_mm" }',
                "",
                "[[constraints.rules]]",
                'id = "tx_dd_pair_fits_region"',
                'kind = "comparison"',
                'message = "2*tx_dd_outer_y + tx_dd_pair_spacing_mm must be <= tx_region_outer_h_mm"',
                'lhs = { func = "add(mul(2,tx_dd_outer_y),tx_dd_pair_spacing_mm)" }',
                'op = "<="',
                'rhs = { path = "tx_region_outer_h_mm" }',
                "",
                "[[constraints.rules]]",
                'id = "rx_dd_pair_fits_region"',
                'kind = "comparison"',
                'message = "2*rx_dd_outer_x + rx_dd_pair_spacing_mm must be <= rx_region_outer_w_mm"',
                'lhs = { func = "add(mul(2,rx_dd_outer_x),rx_dd_pair_spacing_mm)" }',
                'op = "<="',
                'rhs = { path = "rx_region_outer_w_mm" }',
                "",
                "[[constraints.rules]]",
                'id = "tx_vertical_turn_count_within_feasible_max"',
                'kind = "comparison"',
                'message = "tx_vertical turn_count_max must be <= feasible_turns_max under capped vertical zone"',
                'lhs = { path = "selected_group_geometry.tx_vertical.turn_count_max" }',
                'op = "<="',
                'rhs = { func = "feasible_turns_max(tx_vertical,outer_x,outer_y,tx_region_vertical_z_mm)" }',
                "",
                "[[constraints.rules]]",
                'id = "tx_dd_turn_count_within_feasible_max"',
                'kind = "comparison"',
                'message = "tx_dd turn_count_max must be <= feasible_turns_max"',
                'lhs = { path = "selected_group_geometry.tx_dd.turn_count_max" }',
                'op = "<="',
                'rhs = { func = "feasible_turns_max(tx_dd,outer_x,outer_y,outer_y)" }',
                "",
                "[[constraints.rules]]",
                'id = "rx_dd_turn_count_within_feasible_max"',
                'kind = "comparison"',
                'message = "rx_dd turn_count_max must be <= feasible_turns_max"',
                'lhs = { path = "selected_group_geometry.rx_dd.turn_count_max" }',
                'op = "<="',
                'rhs = { func = "feasible_turns_max(rx_dd,outer_x,outer_y,outer_y)" }',
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
                "count_range = [true, 0, 7, 8]",
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
                'z_mode = "absolute"',
                "[[pcbs.mounts]]",
                'kind = "tx_dd"',
                'selector_mode = "index"',
                "selector_index = 0",
                "[[pcbs.mounts]]",
                'kind = "tx_dd"',
                'selector_mode = "index"',
                "selector_index = 1",
                "",
                "[[pcbs]]",
                'id = "tx_main_1"',
                'role = "tx"',
                "position = [0.0, 0.0, 0.0]",
                "rotation_deg = 0.0",
                "present = [true, 1, 1, 1]",
                'z_mode = "relative_to_pcb"',
                'z_relative_base_id = "tx_main_0"',
                'z_delta_path = "pcb_spacing.tx_main_1_z_from_tx_main_0_mm"',
                "[[pcbs.mounts]]",
                'kind = "tx_dd"',
                'selector_mode = "index"',
                "selector_index = 2",
                "[[pcbs.mounts]]",
                'kind = "tx_dd"',
                'selector_mode = "index"',
                "selector_index = 3",
                "",
                "[[pcbs]]",
                'id = "tx_vertical_0"',
                'role = "tx"',
                "position = [0.0, 0.0, 0.0]",
                "rotation_deg = 0.0",
                "present = [true, 1, 1, 1]",
                'z_mode = "absolute"',
                "[[pcbs.mounts]]",
                'kind = "tx_vertical"',
                'selector_mode = "all"',
                "",
                "[[pcbs]]",
                'id = "rx_main_0"',
                'role = "rx"',
                "position = [0.0, 0.0, 110.0]",
                "rotation_deg = 0.0",
                "present = [true, 1, 1, 1]",
                'z_mode = "absolute"',
                "[[pcbs.mounts]]",
                'kind = "rx_dd"',
                'selector_mode = "index"',
                "selector_index = 0",
                "",
                "[[pcbs]]",
                'id = "rx_main_1"',
                'role = "rx"',
                "position = [0.0, 0.0, 112.0]",
                "rotation_deg = 0.0",
                "present = [true, 1, 1, 1]",
                'z_mode = "absolute"',
                "[[pcbs.mounts]]",
                'kind = "rx_dd"',
                'selector_mode = "index"',
                "selector_index = 1",
                "",
                "[[pcbs]]",
                'id = "tx_opt_0"',
                'role = "tx"',
                "position = [40.0, 0.0, 0.0]",
                "rotation_deg = 0.0",
                "present = [true, 0, 0, 1]",
                'z_mode = "absolute"',
                "mounts = []",
                "",
                "[[pcbs]]",
                'id = "tx_opt_1"',
                'role = "tx"',
                "position = [-40.0, 0.0, 0.0]",
                "rotation_deg = 0.0",
                "present = [true, 0, 0, 1]",
                'z_mode = "absolute"',
                "mounts = []",
                "",
                "[[pcbs]]",
                'id = "rx_opt_0"',
                'role = "rx"',
                "position = [40.0, 0.0, 110.0]",
                "rotation_deg = 0.0",
                "present = [true, 0, 0, 1]",
                'z_mode = "absolute"',
                "mounts = []",
                "",
                "[[pcbs]]",
                'id = "rx_opt_1"',
                'role = "rx"',
                "position = [-40.0, 0.0, 110.0]",
                "rotation_deg = 0.0",
                "present = [true, 0, 0, 1]",
                'z_mode = "absolute"',
                "mounts = []",
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

    config = runner.RunConfig("/bin/ansysedt", str(tmp_path / "run"), str(toml_path), seed=7, backend="hfss")
    first = runner.run(config)
    second = runner.run(config)

    assert first["design_id"] == second["design_id"]
    assert first["selected_parameters"] == second["selected_parameters"]
    assert first["selected_group_geometry"] == second["selected_group_geometry"]
    assert first["selected_coil_groups"] == second["selected_coil_groups"]
    assert first["selected_pcbs"] == second["selected_pcbs"]
    assert first["selected_parameters"]["tx_vertical_outer_x"] == first["selected_parameters"]["tx_dd_outer_x"]
    pcbs_by_id = {pcb["id"]: pcb for pcb in first["selected_pcbs"]}
    tx_z_delta = float(pcbs_by_id["tx_main_1"]["position"][2]) - float(pcbs_by_id["tx_main_0"]["position"][2])
    assert tx_z_delta in (3.0, 4.75, 6.5, 8.25, 10.0)
    assert tx_z_delta >= 3.0
    assert first["retry_attempt"] >= 0
    assert first["retry_count"] == first["retry_attempt"]
    assert len(first["selected_group_geometry"]) == 3
    assert {entry["kind"] for entry in first["selected_group_geometry"]} == {"tx_dd", "tx_vertical", "rx_dd"}
    assert first["manifest_path"].endswith(f"manifest_{first['design_id']}.json")
    assert re.fullmatch(r"[0-9a-f]{8}_[0-9a-f]{8}_-?[0-9]+_[0-9]+", first["design_id"]) is not None


def test_seed_changes_group_geometry_and_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "spec.toml"
    _write_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("b" * 40))

    m1 = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))
    m2 = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=2, backend="hfss"))

    assert m1["design_id"] != m2["design_id"]
    assert m1["selected_group_geometry"] != m2["selected_group_geometry"]


def test_missing_group_geometry_section_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "missing_group_params.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    start = raw.index("[coil_groups_params.tx_dd.turn_count_max]")
    end = raw.index("\n[coil_material.via_diameter_mm]")
    toml_path.write_text(raw[:start] + raw[end + 1 :], encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("c" * 40))

    with pytest.raises(ValueError, match="coil_groups_params must be a table/object"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_missing_kind_subfield_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "missing_metal_ratio.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "[coil_groups_params.rx_dd.metal_ratio]",
        "[coil_groups_params.rx_dd.metal_ratio_removed]",
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("d" * 40))

    with pytest.raises(ValueError, match="coil_groups_params.rx_dd must contain only"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_old_profile_only_spec_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "old_profile.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw += "\n[[trace_gap_profile.profiles]]\nid = \"legacy\"\n"
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("e" * 40))

    # Legacy profile block is ignored; new group geometry section remains mandatory/authoritative.
    manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))
    assert len(manifest["selected_group_geometry"]) == 3


def test_tx_region_constraint_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_geom.toml"
    _write_toml(toml_path, outer_x=320.0)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("f" * 40))

    with pytest.raises(RuntimeError, match="No valid selection within max attempts"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_invalid_group_turn_count_range_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_turn_count.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 1, 20, 20]",
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [false, 1, 20, 20]",
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("1" * 40))

    with pytest.raises(ValueError, match=r"coil_groups_params\.tx_dd\.turn_count_max\.range\[0\].*must be true"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_invalid_metal_ratio_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_metal_ratio.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "[coil_groups_params.tx_dd.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.tx_dd.metal_ratio]\nrange = [false, 1.0, 1.0, 1]",
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("3" * 40))

    with pytest.raises(ValueError, match=r"coil_groups_params\.tx_dd\.metal_ratio must be > 0 and < 1"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_invalid_band_ratio_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_band_ratio.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "[coil_groups_params.tx_dd.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.tx_dd.band_ratio]\nrange = [false, 0.0, 0.0, 1]",
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("6" * 40))

    with pytest.raises(ValueError, match=r"coil_groups_params\.tx_dd\.band_ratio must be > 0 and < 1"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_legacy_trace_gap_keys_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "legacy_trace_gap.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace("[coil_groups_params.tx_dd.band_ratio]", "[coil_groups_params.tx_dd.trace]", 1)
    raw = raw.replace("[coil_groups_params.tx_dd.metal_ratio]", "[coil_groups_params.tx_dd.gap]", 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("4" * 40))

    with pytest.raises(ValueError, match=r"coil_groups_params\.tx_dd must contain only"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_unsupported_spec_version_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "old_spec_version.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace('spec_version = "0.2.2"', 'spec_version = "0.1.6"', 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("5" * 40))

    with pytest.raises(ValueError, match=r"spec_version must be '0\.2\.2'"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_retry_attempt_advances_until_constraint_satisfied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "retry.toml"
    _write_toml(toml_path, outer_x=140.0)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "[coil_shape.tx_dd.outer_x]\nrange = [false, 140.0, 140.0, 1]",
        "[coil_shape.tx_dd.outer_x]\nrange = [false, 120.0, 320.0, 2]",
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("2" * 40))

    manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))
    assert manifest["retry_attempt"] > 0
    assert manifest["retry_count"] == manifest["retry_attempt"]


def test_feasibility_constraint_blocks_infeasible_tx_vertical(tmp_path: Path) -> None:
    toml_path = tmp_path / "feasibility_fail.toml"
    _write_toml(toml_path)
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


def test_feasibility_constraint_allows_retry_to_find_valid_case(tmp_path: Path) -> None:
    toml_path = tmp_path / "feasibility_retry.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
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
        "[coil_groups_params.tx_vertical.band_ratio]\nrange = [false, 0.2, 0.9, 2]",
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
    with pytest.raises(SelectionConstraintError):
        resolve_selection(spec=spec, seed=2, attempt=0)

    selected, _, groups, geometries, _ = resolve_selection(spec=spec, seed=2, attempt=1)
    groups_by_kind = {group["kind"]: group for group in groups}
    assert int(groups_by_kind["tx_vertical"]["selected_count"]) == 1
    geom_by_kind = {geom["kind"]: geom for geom in geometries}
    assert float(geom_by_kind["tx_vertical"]["band_ratio"]) == pytest.approx(0.2)
    assert float(selected["tx_region_vertical_z_mm"]) > 0.0


def test_tx_vertical_center_gap_range_fails(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_vertical_center_gap_fail.toml"
    _write_toml(toml_path)
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
    _write_toml(toml_path)
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


def test_repro_mode_sampled_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "sampled.toml"
    _write_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("7" * 40))
    manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=3, backend="hfss"))
    assert manifest["repro_mode"] == "sampled_toml"


def test_repro_mode_frozen_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "frozen.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = re.sub(
        r"range = \[(true|false), ([^,]+), [^,]+, [0-9]+\]",
        lambda m: f"range = [{m.group(1)}, {m.group(2)}, {m.group(2)}, 1]",
        raw,
    )
    raw = raw.replace(
        "[coil_shape.tx_vertical.outer_x]\nrange = [false, -1, -1, 1]",
        "[coil_shape.tx_vertical.outer_x]\nrange = [false, -1, -1, -1]",
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("8" * 40))
    manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=3, backend="hfss"))
    assert manifest["repro_mode"] == "frozen_toml"


def test_removed_path_errors_on_021(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "removed_path.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw += "\n[coil_shape.outer_x]\nrange = [false, 10.0, 10.0, 1]\n"
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("9" * 40))
    with pytest.raises(ValueError, match="Removed path in spec_version 0.2.2"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_tx_vertical_span_removed_path_errors_on_021(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "removed_tx_vertical_span_path.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw += "\n[coil_spacing.tx_vertical_span_mm]\nrange = [false, 3.0, 3.0, 1]\n"
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("a" * 40))
    with pytest.raises(ValueError, match=r"Removed path in spec_version 0.2.2: coil_spacing\.tx_vertical_span_mm"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_ratio_hard_check_failure_contains_details(tmp_path: Path) -> None:
    toml_path = tmp_path / "ratio_fail.toml"
    _write_toml(toml_path, tx_region_h=200.0, outer_y=120.0)
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


def test_tx_main_1_relative_z_requires_spacing_path(tmp_path: Path) -> None:
    toml_path = tmp_path / "missing_pcb_spacing.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    start = raw.index("[pcb_spacing.tx_main_1_z_from_tx_main_0_mm]")
    end = raw.index("\n\n[constraints]")
    toml_path.write_text(raw[:start] + raw[end + 2 :], encoding="utf-8")
    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(ValueError, match=r"Missing required path: pcb_spacing\.tx_main_1_z_from_tx_main_0_mm"):
        resolve_selection(spec=spec, seed=1, attempt=0)


def test_tx_main_1_absolute_z_rejects_relative_fields(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_main_1_absolute_with_relative_fields.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace(
        'z_mode = "relative_to_pcb"',
        'z_mode = "absolute"',
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")
    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(ValueError, match=r"absolute z_mode must not set z_relative_base_id or z_delta_path"):
        resolve_selection(spec=spec, seed=1, attempt=0)


def test_relative_z_mode_requires_base_and_delta_path(tmp_path: Path) -> None:
    toml_path = tmp_path / "relative_z_missing_fields.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace('z_mode = "absolute"', 'z_mode = "relative_to_pcb"', 1)
    start = raw.index('z_relative_base_id = "tx_main_0"')
    end = raw.index("\n[[pcbs.mounts]]", start)
    raw = raw[:start] + raw[end + 1 :]
    toml_path.write_text(raw, encoding="utf-8")
    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(ValueError, match=r"z_relative_base_id must be non-empty string"):
        resolve_selection(spec=spec, seed=1, attempt=0)


def test_derived_dummy_path_maps_to_tx_dd_outer_x(tmp_path: Path) -> None:
    toml_path = tmp_path / "derived_dummy_ok.toml"
    _write_toml(toml_path, outer_x=123.0)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 20, 20]",
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.tx_vertical.band_ratio]\nrange = [false, 0.2, 0.2, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.tx_vertical.metal_ratio]\nrange = [false, 0.5, 0.5, 1]",
    )
    raw = raw.replace("count_range = [true, 0, 7, 8]", "count_range = [true, 1, 1, 1]")
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
    toml_path.write_text(raw, encoding="utf-8")
    spec, _ = load_toml_bytes(toml_path)
    selected, _, _, _, _ = resolve_selection(spec=spec, seed=1, attempt=0)
    assert float(selected["tx_dd_outer_x"]) == pytest.approx(123.0)
    assert float(selected["tx_vertical_outer_x"]) == pytest.approx(123.0)


def test_derived_path_requires_dummy_range_literal(tmp_path: Path) -> None:
    toml_path = tmp_path / "derived_dummy_bad_literal.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "[coil_shape.tx_vertical.outer_x]\nrange = [false, -1, -1, -1]",
        "[coil_shape.tx_vertical.outer_x]\nrange = [false, 60.0, 60.0, 1]",
    )
    toml_path.write_text(raw, encoding="utf-8")
    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(ValueError, match=r"coil_shape\.tx_vertical\.outer_x\.range for derived path must be exactly"):
        resolve_selection(spec=spec, seed=1, attempt=0)


def test_non_derived_path_rejects_dummy_marker(tmp_path: Path) -> None:
    toml_path = tmp_path / "non_derived_dummy_bad.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "[coil_shape.rx_dd.outer_y]\nrange = [false, 80.0, 80.0, 1]",
        "[coil_shape.rx_dd.outer_y]\nrange = [false, -1, -1, -1]",
    )
    toml_path.write_text(raw, encoding="utf-8")
    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(ValueError, match=r"coil_shape\.rx_dd\.outer_y\.range uses reserved derived marker"):
        resolve_selection(spec=spec, seed=1, attempt=0)


def test_pcb_normalization_autocorrects_and_warns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "pcb_normalization_warns.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace(
        "[[pcbs]]\nid = \"tx_main_0\"\nrole = \"tx\"\nposition = [0.0, 0.0, 0.0]\nrotation_deg = 0.0\npresent = [true, 1, 1, 1]\nz_mode = \"absolute\"\n[[pcbs.mounts]]\nkind = \"tx_dd\"\nselector_mode = \"index\"\nselector_index = 0\n[[pcbs.mounts]]\nkind = \"tx_dd\"\nselector_mode = \"index\"\nselector_index = 1",
        "[[pcbs]]\nid = \"tx_main_0\"\nrole = \"tx\"\nposition = [0.0, 0.0, 0.0]\nrotation_deg = 0.0\npresent = [true, 0, 0, 1]\nz_mode = \"absolute\"\n[[pcbs.mounts]]\nkind = \"tx_dd\"\nselector_mode = \"index\"\nselector_index = 0\n[[pcbs.mounts]]\nkind = \"tx_dd\"\nselector_mode = \"index\"\nselector_index = 1\n[[pcbs.mounts]]\nkind = \"tx_vertical\"\nselector_mode = \"all\"",
        1,
    )
    raw = raw.replace(
        "[[pcbs]]\nid = \"tx_opt_0\"\nrole = \"tx\"\nposition = [40.0, 0.0, 0.0]\nrotation_deg = 0.0\npresent = [true, 0, 0, 1]\nz_mode = \"absolute\"\nmounts = []",
        "[[pcbs]]\nid = \"tx_opt_0\"\nrole = \"tx\"\nposition = [40.0, 0.0, 0.0]\nrotation_deg = 0.0\npresent = [true, 1, 1, 1]\nz_mode = \"absolute\"\n[[pcbs.mounts]]\nkind = \"tx_vertical\"\nselector_mode = \"all\"",
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("e" * 40))

    with pytest.warns(UserWarning) as captured:
        manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))
    pcbs = manifest["selected_pcbs"]

    messages = [str(w.message) for w in captured]
    assert any("pcbs.tx_main_0.present normalized" in message for message in messages)
    assert any("pcbs.tx_main_0.mounts normalized" in message for message in messages)
    assert any("pcbs.tx_opt_0.present normalized" in message for message in messages)
    assert any("pcbs.tx_opt_0.mounts normalized" in message for message in messages)

    pcbs_by_id = {pcb["id"]: pcb for pcb in pcbs}
    assert pcbs_by_id["tx_main_0"]["present"] is True
    assert pcbs_by_id["tx_opt_0"]["present"] is False
    assert pcbs_by_id["tx_opt_0"]["mounts"] == []


def test_tx_vertical_single_host_after_normalization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "tx_vertical_single_host.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace(
        "[[pcbs]]\nid = \"tx_main_0\"\nrole = \"tx\"\nposition = [0.0, 0.0, 0.0]\nrotation_deg = 0.0\npresent = [true, 1, 1, 1]\nz_mode = \"absolute\"\n[[pcbs.mounts]]\nkind = \"tx_dd\"\nselector_mode = \"index\"\nselector_index = 0\n[[pcbs.mounts]]\nkind = \"tx_dd\"\nselector_mode = \"index\"\nselector_index = 1",
        "[[pcbs]]\nid = \"tx_main_0\"\nrole = \"tx\"\nposition = [0.0, 0.0, 0.0]\nrotation_deg = 0.0\npresent = [true, 1, 1, 1]\nz_mode = \"absolute\"\n[[pcbs.mounts]]\nkind = \"tx_dd\"\nselector_mode = \"index\"\nselector_index = 0\n[[pcbs.mounts]]\nkind = \"tx_dd\"\nselector_mode = \"index\"\nselector_index = 1\n[[pcbs.mounts]]\nkind = \"tx_vertical\"\nselector_mode = \"all\"",
        1,
    )
    raw = raw.replace(
        "[[pcbs]]\nid = \"tx_main_1\"\nrole = \"tx\"\nposition = [0.0, 0.0, 0.0]\nrotation_deg = 0.0\npresent = [true, 1, 1, 1]\nz_mode = \"relative_to_pcb\"\nz_relative_base_id = \"tx_main_0\"\nz_delta_path = \"pcb_spacing.tx_main_1_z_from_tx_main_0_mm\"\n[[pcbs.mounts]]\nkind = \"tx_dd\"\nselector_mode = \"index\"\nselector_index = 2\n[[pcbs.mounts]]\nkind = \"tx_dd\"\nselector_mode = \"index\"\nselector_index = 3",
        "[[pcbs]]\nid = \"tx_main_1\"\nrole = \"tx\"\nposition = [0.0, 0.0, 0.0]\nrotation_deg = 0.0\npresent = [true, 1, 1, 1]\nz_mode = \"relative_to_pcb\"\nz_relative_base_id = \"tx_main_0\"\nz_delta_path = \"pcb_spacing.tx_main_1_z_from_tx_main_0_mm\"\n[[pcbs.mounts]]\nkind = \"tx_dd\"\nselector_mode = \"index\"\nselector_index = 2\n[[pcbs.mounts]]\nkind = \"tx_dd\"\nselector_mode = \"index\"\nselector_index = 3\n[[pcbs.mounts]]\nkind = \"tx_vertical\"\nselector_mode = \"all\"",
        1,
    )
    raw = raw.replace(
        "[[pcbs]]\nid = \"tx_vertical_0\"\nrole = \"tx\"\nposition = [0.0, 0.0, 0.0]\nrotation_deg = 0.0\npresent = [true, 1, 1, 1]\nz_mode = \"absolute\"\n[[pcbs.mounts]]\nkind = \"tx_vertical\"\nselector_mode = \"all\"",
        "[[pcbs]]\nid = \"tx_vertical_0\"\nrole = \"tx\"\nposition = [0.0, 0.0, 0.0]\nrotation_deg = 0.0\npresent = [true, 1, 1, 1]\nz_mode = \"absolute\"\nmounts = []",
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("c" * 40))

    with pytest.warns(UserWarning):
        manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))
    pcbs = manifest["selected_pcbs"]

    tx_vertical_mount_hosts = [
        pcb["id"]
        for pcb in pcbs
        if any(mount["kind"] == "tx_vertical" for mount in pcb["mounts"])
    ]
    assert tx_vertical_mount_hosts == ["tx_vertical_0"]


def test_optional_boards_forced_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "optional_boards_forced_off.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace(
        "[[pcbs]]\nid = \"tx_opt_0\"\nrole = \"tx\"\nposition = [40.0, 0.0, 0.0]\nrotation_deg = 0.0\npresent = [true, 0, 0, 1]\nz_mode = \"absolute\"\nmounts = []",
        "[[pcbs]]\nid = \"tx_opt_0\"\nrole = \"tx\"\nposition = [40.0, 0.0, 0.0]\nrotation_deg = 0.0\npresent = [true, 1, 1, 1]\nz_mode = \"absolute\"\n[[pcbs.mounts]]\nkind = \"tx_vertical\"\nselector_mode = \"all\"",
        1,
    )
    raw = raw.replace(
        "[[pcbs]]\nid = \"rx_opt_0\"\nrole = \"rx\"\nposition = [40.0, 0.0, 110.0]\nrotation_deg = 0.0\npresent = [true, 0, 0, 1]\nz_mode = \"absolute\"\nmounts = []",
        "[[pcbs]]\nid = \"rx_opt_0\"\nrole = \"rx\"\nposition = [40.0, 0.0, 110.0]\nrotation_deg = 0.0\npresent = [true, 1, 1, 1]\nz_mode = \"absolute\"\n[[pcbs.mounts]]\nkind = \"rx_dd\"\nselector_mode = \"index\"\nselector_index = 0",
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("b" * 40))

    with pytest.warns(UserWarning):
        manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))
    pcbs = manifest["selected_pcbs"]

    pcbs_by_id = {pcb["id"]: pcb for pcb in pcbs}
    assert pcbs_by_id["tx_opt_0"]["present"] is False
    assert pcbs_by_id["tx_opt_0"]["mounts"] == []
    assert pcbs_by_id["rx_opt_0"]["present"] is False
    assert pcbs_by_id["rx_opt_0"]["mounts"] == []


def test_determinism_with_pcb_normalization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "determinism_with_normalization.toml"
    _write_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace(
        "present = [true, 0, 0, 1]",
        "present = [true, 0, 1, 2]",
        4,
    )
    raw = raw.replace(
        "mounts = []",
        "[[pcbs.mounts]]\nkind = \"tx_vertical\"\nselector_mode = \"all\"",
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("d" * 40))

    with pytest.warns(UserWarning):
        first = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=17, backend="hfss"))
    with pytest.warns(UserWarning):
        second = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=17, backend="hfss"))

    assert first["design_id"] == second["design_id"]
    assert first["selected_pcbs"] == second["selected_pcbs"]

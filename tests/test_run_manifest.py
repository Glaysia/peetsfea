from __future__ import annotations

from pathlib import Path
import re

import pytest

import peetsfea.pipeline.run_design as runner
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.resolver import SelectionConstraintError, resolve_selection


def _write_toml(path: Path, *, tx_region_h: float = 200.0, outer_x: float = 140.0, outer_y: float = 120.0) -> None:
    path.write_text(
        "\n".join(
            [
                'spec_version = "0.1.7"',
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
                "[coil_shape.inner_margin_x]",
                "range = [false, 2.0, 2.0, 1]",
                "[coil_shape.inner_margin_y]",
                "range = [false, 2.0, 2.0, 1]",
                "[coil_spacing.tx_dd_pair_spacing_mm]",
                "range = [false, 2.0, 25.0, 6]",
                "[coil_spacing.rx_dd_pair_spacing_mm]",
                "range = [false, 0.0, 5.0, 8]",
                "[coil_spacing.tx_vertical_span_mm]",
                "range = [false, 0.0, 15.0, 4]",
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
                'message = "tx_dd_pair_spacing_mm must be > 0"',
                'lhs = { path = "tx_dd_pair_spacing_mm" }',
                'op = ">"',
                "rhs = { value = 0.0 }",
                "",
                "[[constraints.rules]]",
                'id = "rx_dd_spacing_positive"',
                'kind = "comparison"',
                'message = "rx_dd_pair_spacing_mm must be >= 0"',
                'lhs = { path = "rx_dd_pair_spacing_mm" }',
                'op = ">="',
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
                'id = "coil_outer_x_fits_tx_region"',
                'kind = "comparison"',
                'message = "TX coil outer_x must be < tx.region.outer_w_mm"',
                'lhs = { path = "outer_x" }',
                'op = "<"',
                'rhs = { path = "tx_region_outer_w_mm" }',
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
                'mounts = ["tx_dd:0", "tx_dd:1", "tx_vertical:*"]',
                "",
                "[[pcbs]]",
                'id = "rx_main_0"',
                'role = "rx"',
                "position = [0.0, 0.0, 110.0]",
                "rotation_deg = 0.0",
                "present = [true, 1, 1, 1]",
                'mounts = ["rx_dd:0", "rx_dd:1"]',
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
    assert first["retry_attempt"] == 0
    assert first["retry_count"] == 0
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
    raw = toml_path.read_text(encoding="utf-8").replace('spec_version = "0.1.7"', 'spec_version = "0.1.6"', 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("5" * 40))

    with pytest.raises(ValueError, match=r"spec_version must be '0\.1\.7'"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_retry_attempt_advances_until_constraint_satisfied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "retry.toml"
    _write_toml(toml_path, outer_x=140.0)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "[coil_shape.outer_x]\nrange = [false, 140.0, 140.0, 1]",
        "[coil_shape.outer_x]\nrange = [false, 120.0, 320.0, 2]",
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
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 20, 20]",
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.tx_vertical.band_ratio]\nrange = [false, 0.9, 0.9, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.tx_vertical.metal_ratio]\nrange = [false, 0.85, 0.85, 1]",
    )
    raw = raw.replace("count_range = [true, 0, 4, 5]", "count_range = [true, 1, 1, 1]")
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
    with pytest.raises(SelectionConstraintError, match="tx_vertical_feasible_turns_for_active_group"):
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
        "[coil_groups_params.tx_vertical.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.tx_vertical.band_ratio]\nrange = [false, 0.2, 0.9, 2]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.tx_vertical.metal_ratio]\nrange = [false, 0.85, 0.85, 1]",
    )
    raw = raw.replace("count_range = [true, 0, 4, 5]", "count_range = [true, 1, 1, 1]")
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

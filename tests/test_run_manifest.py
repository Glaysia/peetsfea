from __future__ import annotations

from pathlib import Path
import re

import pytest

import peetsfea.pipeline.run_design as runner


def _write_toml(path: Path, *, tx_region_h: float = 200.0, outer_x: float = 220.0, outer_y: float = 180.0) -> None:
    path.write_text(
        "\n".join(
            [
                'spec_version = "0.1.4"',
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
                "[trace_gap_profile.trace_profile]",
                'mode = "biased_linear"',
                "base = 1.0",
                "outer_bias = 0.1",
                "inner_bias = -0.1",
                "clamp_min = 0.2",
                "",
                "[trace_gap_profile.gap_profile]",
                'mode = "biased_linear"',
                "base = 0.5",
                "outer_bias = 0.05",
                "inner_bias = -0.05",
                "clamp_min = 0.15",
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

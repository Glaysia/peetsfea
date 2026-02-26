from __future__ import annotations

from pathlib import Path
import re

import pytest

import peetsfea.pipeline.run_design as runner
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.resolver import SelectionConstraintError, resolve_selection
from tests.fixtures.type1_spec import write_type1_toml

def test_missing_group_geometry_section_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "missing_group_params.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    start = raw.index("[coil_groups_params.tx_dd.turn_count_max]")
    end = raw.index("\n[coil_material.via_diameter_mm]")
    toml_path.write_text(raw[:start] + raw[end + 1 :], encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("c" * 40))

    with pytest.raises(ValueError, match="coil_groups_params must be a table/object"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))

def test_missing_kind_subfield_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "missing_metal_ratio.toml"
    write_type1_toml(toml_path)
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
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw += "\n[[trace_gap_profile.profiles]]\nid = \"legacy\"\n"
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("e" * 40))

    # Legacy profile block is ignored; new group geometry section remains mandatory/authoritative.
    manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))
    assert len(manifest["selected_group_geometry"]) == 3

def test_invalid_group_turn_count_range_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_turn_count.toml"
    write_type1_toml(toml_path)
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
    write_type1_toml(toml_path)
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
    write_type1_toml(toml_path)
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
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace("[coil_groups_params.tx_dd.band_ratio]", "[coil_groups_params.tx_dd.trace]", 1)
    raw = raw.replace("[coil_groups_params.tx_dd.metal_ratio]", "[coil_groups_params.tx_dd.gap]", 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("4" * 40))

    with pytest.raises(ValueError, match=r"coil_groups_params\.tx_dd must contain only"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))

def test_unsupported_spec_version_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "old_spec_version.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace('spec_version = "0.2.6"', 'spec_version = "0.1.6"', 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("5" * 40))

    with pytest.raises(ValueError, match=r"spec_version must be '0\.2\.6'"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))

def test_removed_path_errors_on_026(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "removed_path.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw += "\n[coil_shape.outer_x]\nrange = [false, 10.0, 10.0, 1]\n"
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("9" * 40))
    with pytest.raises(ValueError, match="Removed path in spec_version 0.2.6"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))

def test_tx_vertical_span_removed_path_errors_on_026(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "removed_tx_vertical_span_path.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw += "\n[coil_spacing.tx_vertical_span_mm]\nrange = [false, 3.0, 3.0, 1]\n"
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("a" * 40))
    with pytest.raises(ValueError, match=r"Removed path in spec_version 0.2.6: coil_spacing\.tx_vertical_span_mm"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_missing_simulation_section_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "missing_simulation.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = re.sub(r"\[simulation\]\n(?:.*\n){5}", "", raw, count=1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("b" * 40))

    with pytest.raises(ValueError, match="simulation must be a table/object"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_invalid_simulation_sweep_order_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "invalid_sweep_order.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace("sweep_stop_hz = 45.0e6", "sweep_stop_hz = 1.0e6", 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("c" * 40))

    with pytest.raises(ValueError, match="simulation.sweep_stop_hz must be > simulation.sweep_start_hz"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_invalid_simulation_validation_gate_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "invalid_validation_gate.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace('validation_gate = "hard_fail"', 'validation_gate = "warn"', 1)
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("d" * 40))

    with pytest.raises(ValueError, match=r"simulation.validation_gate must be 'hard_fail'"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_manifest_includes_simulation_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "manifest_simulation.toml"
    write_type1_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("e" * 40))

    manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))
    assert manifest["spec"]["simulation"] == {
        "radiation_margin_mm": 3500.0,
        "setup_frequency_hz": 6.78e6,
        "sweep_start_hz": 1.0e6,
        "sweep_stop_hz": 45.0e6,
        "validation_gate": "hard_fail",
    }

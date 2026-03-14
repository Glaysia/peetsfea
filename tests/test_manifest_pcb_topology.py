from __future__ import annotations

from pathlib import Path
import re

import pytest

import peetsfea.pipeline.run_design as runner
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.resolver import SelectionConstraintError, resolve_selection
from tests.fixtures.type1_spec import write_type1_toml

def test_tx_main_1_relative_z_requires_spacing_path(tmp_path: Path) -> None:
    toml_path = tmp_path / "missing_pcb_spacing.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    start = raw.index("[pcb_spacing.tx_main_1_z_from_tx_main_0_mm]")
    end = raw.index("\n\n[constraints]")
    toml_path.write_text(raw[:start] + raw[end + 2 :], encoding="utf-8")
    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(ValueError, match=r"Missing required path: pcb_spacing\.tx_main_1_z_from_tx_main_0_mm"):
        resolve_selection(spec=spec, seed=1, attempt=0)

def test_tx_main_1_absolute_z_rejects_relative_fields(tmp_path: Path) -> None:
    toml_path = tmp_path / "tx_main_1_absolute_with_relative_fields.toml"
    write_type1_toml(toml_path)
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
    write_type1_toml(toml_path)
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
    write_type1_toml(toml_path, outer_x=123.0)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace(
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 1, 3, 3]",
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
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 3, 3]",
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
    raw = raw.replace("count_range = [true, 1, 6, 6]", "count_range = [true, 1, 1, 1]")
    raw = raw.replace(
        "[coil_groups_params.rx_dd.turn_count_max]\nrange = [true, 1, 3, 3]",
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
    write_type1_toml(toml_path)
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
    write_type1_toml(toml_path)
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
    write_type1_toml(toml_path)
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
        manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))["manifest"]
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
    write_type1_toml(toml_path)
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
        manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))["manifest"]
    pcbs = manifest["selected_pcbs"]

    tx_vertical_mount_hosts = [
        pcb["id"]
        for pcb in pcbs
        if any(mount["kind"] == "tx_vertical" for mount in pcb["mounts"])
    ]
    assert tx_vertical_mount_hosts == ["tx_vertical_0"]

def test_optional_boards_forced_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "optional_boards_forced_off.toml"
    write_type1_toml(toml_path)
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
        manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))["manifest"]
    pcbs = manifest["selected_pcbs"]

    pcbs_by_id = {pcb["id"]: pcb for pcb in pcbs}
    assert pcbs_by_id["tx_opt_0"]["present"] is False
    assert pcbs_by_id["tx_opt_0"]["mounts"] == []
    assert pcbs_by_id["rx_opt_0"]["present"] is False
    assert pcbs_by_id["rx_opt_0"]["mounts"] == []

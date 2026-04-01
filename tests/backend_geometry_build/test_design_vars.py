from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from peetsfea.aedt import Hfss

import peetsfea.pipeline.run_design as runner
from peetsfea.backend.pyaedt.geometry.design_vars import _assign_design_variables, _sanitize_var_name
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.resolver.sampling import build_sampling_registry, is_sampling_entry_frozen, iter_registry_entries_in_canonical_order
from peetsfea.types.manifest import Manifest
from tests.fixtures.type1_spec import write_type1_toml


def _write_stacked_type1_toml(path: Path) -> None:
    write_type1_toml(path)
    raw = path.read_text(encoding="utf-8")
    raw = raw.replace("stacked_mode = [true, 0, 1, 2]", "stacked_mode = [true, 0, 0, 1]")
    path.write_text(raw, encoding="utf-8")


class _FakeHfss(dict[str, str]):
    pass


def test_assign_design_variables_keeps_all_unfrozen_input_owners(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "type1.toml"
    _write_stacked_type1_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("1" * 40))
    manifest = cast(
        Manifest,
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=11, backend="hfss"))["manifest"],
    )
    fake_hfss = _FakeHfss()

    _assign_design_variables(cast(Hfss, fake_hfss), manifest)

    source_spec, _ = load_toml_bytes(toml_path)
    registry = build_sampling_registry(source_spec)
    expected_names = {
        _sanitize_var_name(entry.owner_path)
        for entry in iter_registry_entries_in_canonical_order(registry)
        if not is_sampling_entry_frozen(source_spec, entry)
    }
    assert set(fake_hfss.keys()) == expected_names
    assert len(fake_hfss) == len(expected_names)
    assert fake_hfss["ferrite_present"] in {"0", "1"}
    assert "coil_placement_tx_vertical_orientation_mode" not in fake_hfss
    assert fake_hfss["coil_groups_1__count_range"].isdigit()
    assert "coil_shape_corner_mode" not in fake_hfss
    assert not fake_hfss["coil_groups_params_neo_tx_dd_band_ratio"].endswith("mm")
    assert "coil_groups_0__stacked_mode" not in fake_hfss
    assert "coil_shape_neo_tx_dd_outer_x" not in fake_hfss
    assert "tv_width_mm" not in fake_hfss
    assert "coil_shape_tx_vertical_outer_x" not in fake_hfss
    assert "tx_dd_pair_spacing_mm" not in fake_hfss


def test_run_manifest_records_source_toml_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "type1.toml"
    write_type1_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("2" * 40))

    manifest = cast(
        Manifest,
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=11, backend="hfss"))["manifest"],
    )

    assert manifest["inputs"].get("source_toml_path") == str(toml_path)


def test_assign_design_variables_reads_values_from_matching_manifest_sections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    toml_path = tmp_path / "type1.toml"
    _write_stacked_type1_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("3" * 40))
    manifest = cast(
        Manifest,
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=11, backend="hfss"))["manifest"],
    )
    fake_hfss = _FakeHfss()

    _assign_design_variables(cast(Hfss, fake_hfss), manifest)

    tx_vertical_group = next(entry for entry in manifest["selected_coil_groups"] if entry["kind"] == "tx_vertical")
    tx_dd_geometry = next(entry for entry in manifest["selected_group_geometry"] if entry["kind"] == "tx_dd")

    assert "coil_placement_tx_vertical_orientation_mode" not in fake_hfss
    assert fake_hfss["ferrite_present"] in {"0", "1"}
    assert "coil_groups_0__stacked_mode" not in fake_hfss
    assert fake_hfss["coil_groups_1__count_range"] == str(tx_vertical_group["requested_count"])
    assert fake_hfss["coil_groups_params_neo_tx_dd_band_ratio"] == str(tx_dd_geometry["band_ratio"])

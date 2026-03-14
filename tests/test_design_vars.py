from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from ansys.aedt.core import Hfss

import peetsfea.pipeline.run_design as runner
from peetsfea.backend.pyaedt.geometry.design_vars import _assign_design_variables, _sanitize_var_name
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.resolver.sampling import build_sampling_registry, is_sampling_entry_frozen, iter_registry_entries_in_canonical_order
from peetsfea.types.manifest import Manifest
from tests.fixtures.type1_spec import write_type1_toml


_EXAMPLE_TYPE1_TOML = Path(__file__).resolve().parents[1] / "examples" / "type1.toml"


class _FakeHfss(dict[str, str]):
    pass


def test_assign_design_variables_keeps_all_unfrozen_input_owners(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = _EXAMPLE_TYPE1_TOML
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
    assert fake_hfss["coil_shape_tx_dd_outer_x"].endswith("mm")
    assert fake_hfss["coil_placement_tx_vertical_layout_mode"].isdigit()
    assert not fake_hfss["coil_spacing_tx_vertical_mode2_pair_spacing_ratio"].endswith("mm")
    assert not fake_hfss["coil_placement_tx_vertical_mode2_x_ratio_to_tx_dd_center"].endswith("mm")
    assert fake_hfss["coil_groups_0__count_mode"].isdigit()
    assert "coil_groups_1__count_range" not in fake_hfss
    assert fake_hfss["coil_groups_params_tx_dd_turn_count_max"].isdigit()
    assert not fake_hfss["coil_groups_params_tx_dd_band_ratio"].endswith("mm")
    assert "tv_width_mm" not in fake_hfss
    assert "coil_shape_tx_vertical_outer_x" not in fake_hfss
    assert "tx_dd_pair_spacing_mm" not in fake_hfss
    assert "tx_vertical_mode2_pair_spacing_mm" not in fake_hfss


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
    toml_path = _EXAMPLE_TYPE1_TOML
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("3" * 40))
    manifest = cast(
        Manifest,
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=11, backend="hfss"))["manifest"],
    )
    fake_hfss = _FakeHfss()

    _assign_design_variables(cast(Hfss, fake_hfss), manifest)

    tx_dd_group = next(entry for entry in manifest["selected_coil_groups"] if entry["kind"] == "tx_dd")
    tx_vertical_group = next(entry for entry in manifest["selected_coil_groups"] if entry["kind"] == "tx_vertical")
    tx_dd_geometry = next(entry for entry in manifest["selected_group_geometry"] if entry["kind"] == "tx_dd")

    assert fake_hfss["coil_shape_tx_dd_outer_x"] == f"{manifest['selected_parameters']['tx_dd_outer_x']}mm"
    assert fake_hfss["coil_placement_tx_vertical_layout_mode"] == str(manifest["selected_parameters"]["tx_vertical_layout_mode"])
    assert fake_hfss["coil_spacing_tx_vertical_mode2_pair_spacing_ratio"] == str(
        manifest["selected_parameters"]["tx_vertical_mode2_pair_spacing_ratio"]
    )
    assert fake_hfss["coil_placement_tx_vertical_mode2_x_ratio_to_tx_dd_center"] == str(
        manifest["selected_parameters"]["tx_vertical_mode2_x_ratio_to_tx_dd_center"]
    )
    assert fake_hfss["coil_groups_0__count_mode"] == str(tx_dd_group["requested_count"])
    assert "coil_groups_1__count_range" not in fake_hfss
    assert fake_hfss["coil_groups_params_tx_dd_turn_count_max"] == str(tx_dd_geometry["turn_count_max"])
    assert fake_hfss["coil_groups_params_tx_dd_band_ratio"] == str(tx_dd_geometry["band_ratio"])

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from ansys.aedt.core import Hfss

import peetsfea.pipeline.run_design as runner
from peetsfea.backend.pyaedt.geometry.design_vars import _assign_design_variables, _sanitize_var_name
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.resolver.constants import SCALAR_RANGE_SPECS
from peetsfea.spec.resolver.sampling import build_sampling_registry, is_sampling_entry_frozen, iter_registry_entries_in_canonical_order
from peetsfea.types.manifest import Manifest
from tests.fixtures.type1_spec import write_type1_toml


class _FakeHfss(dict[str, str]):
    pass


def test_assign_design_variables_keeps_only_unfrozen_scalar_owners(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "type1.toml"
    write_type1_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("1" * 40))
    manifest = cast(
        Manifest,
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=11, backend="hfss"))["manifest"],
    )
    fake_hfss = _FakeHfss()

    _assign_design_variables(cast(Hfss, fake_hfss), manifest)

    source_spec, _ = load_toml_bytes(toml_path)
    registry = build_sampling_registry(source_spec)
    selected_key_by_owner_path = {path: key for path, key, _ in SCALAR_RANGE_SPECS}
    expected_names = {
        _sanitize_var_name(f"spec_{selected_key_by_owner_path[entry.owner_path]}")
        for entry in iter_registry_entries_in_canonical_order(registry)
        if entry.owner_path in selected_key_by_owner_path and not is_sampling_entry_frozen(source_spec, entry)
    }
    assert set(fake_hfss.keys()) == expected_names
    assert "spec_ferrite_present" in fake_hfss
    assert fake_hfss["spec_ferrite_present"] in {"0", "1"}
    assert "spec_tx_dd_pair_spacing_ratio" in fake_hfss
    assert fake_hfss["spec_tx_dd_pair_spacing_ratio"].endswith("mm")
    assert "spec_tv_width_mm" not in fake_hfss
    assert "spec_tx_vertical_span_mm" not in fake_hfss
    assert not any(name.startswith("group_") for name in fake_hfss)
    assert not any(name.startswith("group_geom_") for name in fake_hfss)
    assert not any(name.startswith("pcb_") for name in fake_hfss)


def test_run_manifest_records_source_toml_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "type1.toml"
    write_type1_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("2" * 40))

    manifest = cast(
        Manifest,
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=11, backend="hfss"))["manifest"],
    )

    assert manifest["inputs"].get("source_toml_path") == str(toml_path)

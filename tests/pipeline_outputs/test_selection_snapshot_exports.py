from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

import peetsfea.pipeline.run_design as runner
from peetsfea.pipeline.selection.selection_snapshots import freeze_sampled_ranges_only
from peetsfea.spec.loader import load_toml_bytes, require_table
from tests.fixtures.type1_spec import write_type1_toml


def test_freeze_sampled_ranges_only_preserves_fixed_owners_and_non_sampled_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    toml_path = tmp_path / "type1.toml"
    write_type1_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("f" * 40))

    result = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=11, backend="hfss"))
    source_spec, _ = load_toml_bytes(toml_path)
    repro_spec = tomllib.loads(result["repro_snapshot"]["toml_bytes"].decode("utf-8"))
    resolved_spec = freeze_sampled_ranges_only(source_spec, repro_spec)
    ferrite_table = require_table(resolved_spec["ferrite"], "ferrite")
    source_ferrite_table = require_table(source_spec["ferrite"], "ferrite")
    resolved_present = require_table(ferrite_table["present"], "ferrite.present")
    source_present = require_table(source_ferrite_table["present"], "ferrite.present")
    resolved_tv = require_table(resolved_spec["tv"], "tv")
    source_tv = require_table(source_spec["tv"], "tv")
    resolved_width = require_table(resolved_tv["width_mm"], "tv.width_mm")
    source_width = require_table(source_tv["width_mm"], "tv.width_mm")
    resolved_coil_shape = require_table(resolved_spec["coil_shape"], "coil_shape")
    source_coil_shape = require_table(source_spec["coil_shape"], "coil_shape")
    resolved_tx_vertical = require_table(resolved_coil_shape["neo_tx_vertical"], "coil_shape.neo_tx_vertical")
    source_tx_vertical = require_table(source_coil_shape["neo_tx_vertical"], "coil_shape.neo_tx_vertical")
    resolved_outer_x = require_table(resolved_tx_vertical["outer_x"], "coil_shape.neo_tx_vertical.outer_x")
    source_outer_x = require_table(source_tx_vertical["outer_x"], "coil_shape.neo_tx_vertical.outer_x")

    assert resolved_spec["constraints"] == source_spec["constraints"]
    assert resolved_present["range"] != source_present["range"]
    assert isinstance(resolved_present["range"], list)
    assert resolved_present["range"][3] == 1
    assert resolved_width["range"] == source_width["range"]
    assert resolved_outer_x["range"] == source_outer_x["range"]

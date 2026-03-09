from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

import peetsfea.pipeline.run_design as runner
from peetsfea.pipeline.selection_snapshots import freeze_sampled_ranges_only
from peetsfea.spec.loader import load_toml_bytes
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

    assert resolved_spec["constraints"] == source_spec["constraints"]
    assert resolved_spec["ferrite"]["present"]["range"] != source_spec["ferrite"]["present"]["range"]
    assert resolved_spec["ferrite"]["present"]["range"][3] == 1
    assert resolved_spec["tv"]["width_mm"]["range"] == source_spec["tv"]["width_mm"]["range"]
    assert resolved_spec["coil_shape"]["tx_vertical"]["outer_x"]["range"] == source_spec["coil_shape"]["tx_vertical"]["outer_x"]["range"]


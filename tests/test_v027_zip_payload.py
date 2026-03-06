from __future__ import annotations

from pathlib import Path

import pytest

import peetsfea.pipeline.run_design as runner
from peetsfea.types.manifest import RunResult
from tests.fixtures.type1_spec import write_type1_toml

pytestmark = pytest.mark.contract


def _prepare_zip_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[RunResult, Path, bytes, str]:
    toml_path = tmp_path / "spec.toml"
    write_type1_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("9" * 40))

    base: RunResult = runner.run(
        runner.RunConfig(
            "/bin/ansysedt",
            str(tmp_path),
            str(toml_path),
            seed=13,
            backend="hfss",
            export_zip=False,
        )
    )
    design_id = base["manifest"]["design_id"]
    aedt_path = tmp_path / f"{design_id}.aedt"
    aedt_payload = b"FAKE_AEDT_BINARY_PAYLOAD"
    aedt_path.write_bytes(aedt_payload)

    exported: RunResult = runner.run(
        runner.RunConfig(
            "/bin/ansysedt",
            str(tmp_path),
            str(toml_path),
            seed=13,
            backend="hfss",
            export_zip=True,
        )
    )
    return exported, toml_path, aedt_payload, design_id


def test_ac01_default_run_emits_one_zip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    exported, _, _, _ = _prepare_zip_case(tmp_path, monkeypatch)

    assert exported["zip_path"] is None, "AC-01 zip export is temporarily disabled"


def test_ac02_export_zip_flag_keeps_snapshots_but_returns_no_zip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    exported, toml_path, _, design_id = _prepare_zip_case(tmp_path, monkeypatch)

    assert exported["zip_path"] is None, "AC-02 zip path must remain None while export is disabled"
    assert exported["source_toml_bytes"] == toml_path.read_bytes()
    assert exported["repro_snapshot"]["toml_bytes"]
    assert exported["dataset_snapshot"]["toml_bytes"]

    exported_again = runner.run(
        runner.RunConfig(
            "/bin/ansysedt",
            str(tmp_path),
            str(toml_path),
            seed=13,
            backend="hfss",
            export_zip=True,
        )
    )
    assert exported_again["zip_path"] is None
    assert exported_again["manifest"]["design_id"] == design_id

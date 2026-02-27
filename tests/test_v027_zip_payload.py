from __future__ import annotations

import hashlib
from pathlib import Path
import tomllib
import zipfile

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

    zip_path_str = exported["zip_path"]
    assert zip_path_str is not None, "AC-01 default run must emit one zip when export_zip=True"
    zip_path = Path(zip_path_str)
    assert zip_path.exists(), "AC-01 <design_id>.zip must exist"


def test_ac02_zip_payload_has_exact_four_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    exported, toml_path, aedt_payload, design_id = _prepare_zip_case(tmp_path, monkeypatch)

    zip_path_str = exported["zip_path"]
    assert zip_path_str is not None, "AC-02 zip payload must contain exactly 4 files: zip path missing"
    zip_path = Path(zip_path_str)

    expected_names = [
        f"{design_id}.aedt",
        f"{design_id}.repro.toml",
        f"{design_id}.dataset.toml",
        f"{design_id}.source.toml",
    ]

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = sorted(zf.namelist())
        assert names == sorted(expected_names), "AC-02 zip payload must contain exactly 4 files"

        assert zf.read(f"{design_id}.aedt") == aedt_payload, "AC-02 payload aedt bytes mismatch"

        repro_bytes = zf.read(f"{design_id}.repro.toml")
        dataset_bytes = zf.read(f"{design_id}.dataset.toml")
        source_bytes = zf.read(f"{design_id}.source.toml")

    assert source_bytes == toml_path.read_bytes(), "AC-05 source snapshot bytes must match input TOML"
    assert repro_bytes == exported["repro_snapshot"]["toml_bytes"], "AC-03 repro payload bytes mismatch"
    assert dataset_bytes == exported["dataset_snapshot"]["toml_bytes"], "AC-04 dataset payload bytes mismatch"

    dataset = tomllib.loads(dataset_bytes.decode("utf-8"))
    output = dataset.get("output")
    assert isinstance(output, dict), "AC-04 dataset output.* must be -1: output table missing"
    assert len(output) >= 1, "AC-04 dataset output.* must be -1: output table empty"
    for key, value in output.items():
        assert value == -1, f"AC-04 dataset output.* must be -1: output.{key}={value}"

    simulation = dataset.get("simulation")
    assert isinstance(simulation, dict), "AC-04 dataset simulation.timeout_sec=7200: simulation table missing"
    assert simulation.get("timeout_sec") == 7200, "AC-04 dataset simulation.timeout_sec must be 7200"

    artifacts = dataset.get("artifacts")
    assert isinstance(artifacts, dict), "AC-04 dataset artifacts.aedt_file key missing"
    assert artifacts.get("aedt_file") == f"{design_id}.aedt", "AC-04 artifacts.aedt_file must match <design_id>.aedt"

    first_hash = hashlib.sha256(zip_path.read_bytes()).hexdigest()

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
    zip_path_again_str = exported_again["zip_path"]
    assert zip_path_again_str is not None, "AC-02 deterministic zip hash check: second zip path missing"
    second_hash = hashlib.sha256(Path(zip_path_again_str).read_bytes()).hexdigest()
    assert first_hash == second_hash, "AC-02 deterministic zip hash must be identical for same seed/input"

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest

import peetsfea.pipeline.run_design as runner
from peetsfea.types.manifest import RunResult
from tests.fixtures.type1_spec import write_type1_toml

pytestmark = pytest.mark.contract


def _walk_ranges(value: object, path: str = "") -> list[tuple[str, list[object]]]:
    found: list[tuple[str, list[object]]] = []
    if isinstance(value, dict):
        if set(value.keys()) == {"range"} and isinstance(value.get("range"), list):
            found.append((path, value["range"]))
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            found.extend(_walk_ranges(child, child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            child_path = f"{path}[{idx}]" if path else f"[{idx}]"
            found.extend(_walk_ranges(child, child_path))
    return found


def _build_snapshot_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[RunResult, dict[str, Any], dict[str, Any], bytes, str]:
    toml_path = tmp_path / "type1.toml"
    write_type1_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("f" * 40))

    result = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=11, backend="hfss"))
    repro = tomllib.loads(result["repro_snapshot"]["toml_bytes"].decode("utf-8"))
    dataset = tomllib.loads(result["dataset_snapshot"]["toml_bytes"].decode("utf-8"))
    return result, repro, dataset, toml_path.read_bytes(), toml_path.name


def test_ac03_repro_count_is_forced_to_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, repro, _, _, _ = _build_snapshot_case(tmp_path, monkeypatch)

    for range_path, raw_range in _walk_ranges(repro):
        if len(raw_range) != 4:
            continue
        if not isinstance(raw_range[3], int):
            continue
        is_derived_dummy = (
            isinstance(raw_range[0], bool)
            and raw_range[0] is False
            and isinstance(raw_range[1], (int, float))
            and isinstance(raw_range[2], (int, float))
            and float(raw_range[1]) == -1.0
            and float(raw_range[2]) == -1.0
            and int(raw_range[3]) == -1
        )
        if is_derived_dummy:
            continue
        assert int(raw_range[3]) == 1, f"AC-03 repro count=1 contract violated at {range_path}"


def test_ac04_dataset_placeholders_and_timeout_and_aedt_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result, _, dataset, _, _ = _build_snapshot_case(tmp_path, monkeypatch)

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
    expected_name = f"{result['manifest']['design_id']}.aedt"
    assert artifacts.get("aedt_file") == expected_name, "AC-04 dataset artifacts.aedt_file must match <design_id>.aedt"

    inputs = dataset.get("inputs")
    assert isinstance(inputs, dict), "AC-04 dataset inputs.parameters missing"
    parameters = inputs.get("parameters")
    assert isinstance(parameters, list), "AC-04 dataset inputs.parameters must be a list"

    source_spec = tomllib.loads(result["source_toml_bytes"].decode("utf-8"))
    source_range_counts = {
        path: int(raw_range[3])
        for path, raw_range in _walk_ranges(source_spec)
        if len(raw_range) == 4 and isinstance(raw_range[3], int)
    }
    assert len(parameters) > 0, "AC-04 dataset inputs.parameters must include count!=2 variables"
    for entry in parameters:
        assert isinstance(entry, dict), "AC-04 dataset inputs.parameters entries must be tables"
        path = entry.get("path")
        assert isinstance(path, str), "AC-04 dataset inputs.parameters.path must be string"
        assert path in source_range_counts, f"AC-04 dataset input path not found in source: {path}"
        assert source_range_counts[path] != 2, f"AC-04 dataset inputs must include only count!=2 variables: {path}"

    constraints = dataset.get("constraints")
    assert isinstance(constraints, dict), "AC-04 dataset must include constraints table"


def test_ac05_source_toml_is_byte_identical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result, _, _, source_bytes, _ = _build_snapshot_case(tmp_path, monkeypatch)
    assert result["source_toml_bytes"] == source_bytes, "AC-05 source snapshot must be byte-identical to input TOML"

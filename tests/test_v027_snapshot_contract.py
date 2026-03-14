from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest

import peetsfea.pipeline.run_design as runner
from peetsfea.pipeline.selection_snapshots import dataset_owner_paths, detect_repro_mode
from peetsfea.spec.loader import load_toml_bytes
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

    source_path = tmp_path / "source.toml"
    source_path.write_bytes(result["source_toml_bytes"])
    source_spec, _ = load_toml_bytes(source_path)
    expected_paths = dataset_owner_paths(source_spec, repro_mode=detect_repro_mode(source_spec))

    exported_paths: list[str] = []
    assert len(parameters) > 0, "AC-04 dataset inputs.parameters must include effective sampled owners"
    for entry in parameters:
        assert isinstance(entry, dict), "AC-04 dataset inputs.parameters entries must be tables"
        path = entry.get("path")
        assert isinstance(path, str), "AC-04 dataset inputs.parameters.path must be string"
        exported_paths.append(path)

    assert tuple(exported_paths) == expected_paths
    assert "ferrite.present" in exported_paths
    assert "coil_groups[0].count_mode" in exported_paths
    assert "coil_groups[1].count_range" not in exported_paths
    assert "coil_shape.tx_vertical.outer_x" not in exported_paths
    assert all(not path.startswith("pcbs[") or not path.endswith(".present") for path in exported_paths)

    constraints = dataset.get("constraints")
    assert isinstance(constraints, dict), "AC-04 dataset must include constraints table"


def test_ac05_source_toml_is_byte_identical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result, _, _, source_bytes, _ = _build_snapshot_case(tmp_path, monkeypatch)
    assert result["source_toml_bytes"] == source_bytes, "AC-05 source snapshot must be byte-identical to input TOML"


def test_repro_snapshot_replays_same_design_and_dataset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result, _, dataset, _, _ = _build_snapshot_case(tmp_path, monkeypatch)

    repro_path = tmp_path / "replay.repro.toml"
    repro_path.write_bytes(result["repro_snapshot"]["toml_bytes"])
    replayed = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(repro_path), seed=11, backend="hfss"))
    replayed_dataset = tomllib.loads(replayed["dataset_snapshot"]["toml_bytes"].decode("utf-8"))

    assert replayed["manifest"]["selected_parameters"] == result["manifest"]["selected_parameters"]
    assert replayed["manifest"]["selected_group_geometry"] == result["manifest"]["selected_group_geometry"]
    assert replayed["manifest"]["selected_coil_groups"] == result["manifest"]["selected_coil_groups"]
    assert replayed["manifest"]["selected_pcbs"] == result["manifest"]["selected_pcbs"]
    assert replayed_dataset["inputs"]["parameters"] == dataset["inputs"]["parameters"]
    assert replayed["manifest"]["toml_space_hash"] != result["manifest"]["toml_space_hash"]
    assert replayed["manifest"]["design_id"] != result["manifest"]["design_id"]

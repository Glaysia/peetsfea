from __future__ import annotations

import json
from pathlib import Path
import re
from typing import cast

import pytest

import entry.build as build_entry
from entry.build import build_type2
from entry.sample import sample_type2
from peetsfea.backend.pyaedt.type2_step_setup_ready import Type2SetupReadyResult
from peetsfea.backend.pyaedt.type2_step_post_import_mesh import Type2ImportedMeshSummary


def _source_type2_toml_text() -> str:
    return """
spec_version = "0.2.22"
schema_id = "peetsfea.type2.step.v1"
runtime_compatible = false

[design]
units = "mm"

[backend]
authoring_tool = "build123d"
solver_tool = "hfss"
interchange_format = "step"

[simulation]
radiation_margin_mm = 3500.0

[outputs]
report_name = "Output Variables Table1"
solution_name = "Setup1 : LastAdaptive"
primary_sweep = "Freq"
report_category = "Terminal Solution Data"
plot_type = "Data Table"

[[outputs.variables]]
name = "Ltx_uH"
expression = "im(Zt(TX_TML,TX_TML))/2/pi/freq*1e6"

[[non_model_objects]]
id = "floor"
kind = "floor"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "XY"
origin_xyz = [0.0, -10.0, -1.0]
size_xyz = [20.0, 20.0, 1.0]

[[non_model_objects]]
id = "shelf"
kind = "shelf"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "XY"
origin_xyz = [0.0, -10.0, 0.0]
size_xyz = [10.0, 20.0, 4.0]

[[non_model_objects]]
id = "wall"
kind = "wall"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [-1.0, -10.0, 0.0]
size_xyz = [1.0, 20.0, 10.0]

[[non_model_objects]]
id = "tv"
kind = "tv"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [0.0, -5.0, 5.0]
size_xyz = [1.0, 10.0, 4.0]

[[non_model_objects]]
id = "tx_region"
kind = "tx_region"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "XY"
origin_xyz = [0.0, -140.0, 0.0]
size_xyz = [160.0, 280.0, 90.0]

[[non_model_objects]]
id = "rx_region_max"
kind = "rx_region_max"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [200.0, -100.0, 0.0]
size_xyz = [10.0, 200.0, 200.0]

[[modeled_objects]]
object_id = "tx_rect_void_coil"
role = "tx_single_coil"
material = "composite"
model_state = true
pcb_thickness_mm = 1.6
copper_thickness_mm = 0.1

[modeled_objects.outer_x_mm]
range = [false, 50.0, 60.0, 3]
[modeled_objects.outer_y_mm]
range = [false, 60.0, 60.0, 1]
[modeled_objects.turn_count]
range = [true, 2, 2, 1]
[modeled_objects.layer_count]
range = [true, 1, 1, 1]
[modeled_objects.underlay_repeat_count]
range = [true, 0, 8, 5]
[modeled_objects.underlay_gap_mm]
range = [false, 1.0, 10.0, 4]
[modeled_objects.layer_gap_mm]
range = [false, 2.0, 2.0, 1]
[modeled_objects.terminal_stub_length_mm]
range = [false, 5.0, 5.0, 1]
[modeled_objects.void_x_over_outer_x]
range = [false, 0.30, 0.50, 3]
[modeled_objects.void_y_over_outer_y]
range = [false, 0.30, 0.30, 1]
[modeled_objects.void_center_x_over_outer_x]
range = [false, 0.0, 0.0, 1]
[modeled_objects.void_center_y_over_outer_y]
range = [false, 0.0, 0.0, 1]
[modeled_objects.margin_ratio]
range = [false, 0.05, 0.15, 3]
[modeled_objects.metal_fill_factor]
range = [false, 0.5, 0.5, 1]
[modeled_objects.terminal_path]
value = "A_cw_to_a"
""".strip()


def _write_source_type2_toml(tmp_path: Path) -> Path:
    path = tmp_path / "type2_sweep.toml"
    path.write_text(_source_type2_toml_text(), encoding="utf-8")
    return path


def _write_step_artifacts(*, output_dir: Path, ledger_path: Path) -> None:
    scene_step_path = output_dir / "type2_scene.step"
    scene_step_path.write_text("STEP", encoding="utf-8")
    ledger_path.write_text(json.dumps({"scene_step_path": str(scene_step_path)}, indent=2), encoding="utf-8")


def _fake_setup_result(*, step_ledger_path: Path, output_aedt_path: Path, imported_ledger_path: Path, seed: int) -> Type2SetupReadyResult:
    mesh: Type2ImportedMeshSummary = {
        "module_name": "MeshSetup",
        "operation": "AssignLengthOp",
        "operation_name": "Length1",
        "objects": ["tx_copper_l0"],
        "refine_inside": False,
        "enabled": True,
        "restrict_elem": False,
        "num_max_elem": "1000",
        "restrict_length": True,
        "max_length": "1mm",
    }
    return {
        "source_toml_path": str(step_ledger_path.with_name("sampled.toml")),
        "source_step_ledger_path": str(step_ledger_path),
        "scene_step_path": str(step_ledger_path.with_name("type2_scene.step")),
        "seed": seed,
        "aedt_path": str(output_aedt_path),
        "imported_ledger_path": str(imported_ledger_path),
        "mesh": mesh,
        "boundary": {"type": "radiation", "region_name": "Region", "face_count": "6", "offset_value": "3500mm"},
        "ports": {"tx": ["1_T1"], "rx": ["2_T1"]},
        "sources": {"tx_source_name": "1_T1", "rx_source_name": "2_T1"},
        "analysis": {"setup_name": "Setup1", "setup_frequency_hz": 13560000.0},
        "validation_report": {"ok": True, "gate": "hard_fail", "message": "ok"},
    }


def test_build_type2_reads_aedt_builder_n_from_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"

    def _exporter(**kwargs: object) -> object:
        _write_step_artifacts(output_dir=cast(Path, kwargs["output_dir"]), ledger_path=cast(Path, kwargs["ledger_path"]))
        return {"ok": True}

    sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=4,
        seed_n=2,
        sampler_n=1,
        aedt_builder_n=6,
        exporter=_exporter,
    )

    calls: list[dict[str, object]] = []

    def _fake_build_prepared_type2_designs(prepared_builds: tuple[object, ...], *, jobs: int, runner: object) -> list[dict[str, str]]:
        calls.append({"jobs": jobs, "build_count": len(prepared_builds), "runner": runner})
        return []

    monkeypatch.setattr(build_entry, "build_prepared_type2_designs", _fake_build_prepared_type2_designs)
    results = build_type2(manifest_path=manifest_path)

    assert results == []
    assert calls == [{"jobs": 6, "build_count": 2, "runner": build_entry.setup_type2_step_ledger}]


def test_build_type2_creates_aedt_without_step_export(tmp_path: Path) -> None:
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"

    def _exporter(**kwargs: object) -> object:
        _write_step_artifacts(output_dir=cast(Path, kwargs["output_dir"]), ledger_path=cast(Path, kwargs["ledger_path"]))
        return {"ok": True}

    document = sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=8,
        seed_n=1,
        sampler_n=1,
        aedt_builder_n=2,
        exporter=_exporter,
    )
    runner_calls: list[dict[str, object]] = []

    def _runner(**kwargs: object) -> Type2SetupReadyResult:
        runner_calls.append(dict(kwargs))
        output_aedt_path = cast(Path, kwargs["output_aedt_path"])
        imported_ledger_path = cast(Path, kwargs["imported_ledger_path"])
        output_aedt_path.write_text("AEDT", encoding="utf-8")
        imported_ledger_path.write_text("{}", encoding="utf-8")
        return _fake_setup_result(
            step_ledger_path=cast(Path, kwargs["step_ledger_path"]),
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            seed=8,
        )

    results = build_type2(manifest_path=manifest_path, runner=_runner)

    assert len(results) == 1
    assert len(runner_calls) == 1
    assert re.fullmatch(r"s\d{6}_[0-9a-f]{4}_[0-9a-f]{4}_0", document["entries"][0]["design_id"]) is not None
    assert Path(document["entries"][0]["aedt_path"]).is_file()
    assert Path(document["entries"][0]["imported_ledger_path"]).is_file()
    assert runner_calls[0]["design_name"] == document["entries"][0]["design_id"]
    assert runner_calls[0]["step_ledger_path"] == Path(document["entries"][0]["step_ledger_path"])
    assert tuple(cast(tuple[tuple[str, str], ...], runner_calls[0]["design_variables"])) != ()


def test_build_type2_fails_before_runner_when_step_ledger_is_missing(tmp_path: Path) -> None:
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"

    def _exporter(**kwargs: object) -> object:
        _write_step_artifacts(output_dir=cast(Path, kwargs["output_dir"]), ledger_path=cast(Path, kwargs["ledger_path"]))
        return {"ok": True}

    document = sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=11,
        seed_n=1,
        sampler_n=1,
        aedt_builder_n=1,
        exporter=_exporter,
    )
    Path(document["entries"][0]["step_ledger_path"]).unlink()
    runner_calls: list[dict[str, object]] = []

    def _runner(**kwargs: object) -> Type2SetupReadyResult:
        runner_calls.append(dict(kwargs))
        raise AssertionError("runner must not be called when step ledger is missing")

    with pytest.raises(FileNotFoundError, match=r"type2 STEP ledger not found:"):
        build_type2(manifest_path=manifest_path, runner=_runner)
    assert runner_calls == []


def test_build_type2_rejects_list_manifest_payload(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("[]", encoding="utf-8")

    with pytest.raises(TypeError, match=r"type2 sample manifest must be an object"):
        build_type2(manifest_path=manifest_path)


def test_build_type2_rejects_missing_aedt_builder_n_config(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "config": {
                    "source_toml_path": "/tmp/source.toml",
                    "seed_first": 0,
                    "seed_n": 1,
                    "sampler_n": 1,
                },
                "entries": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"type2 sample manifest config is missing required key 'aedt_builder_n'"):
        build_type2(manifest_path=manifest_path)

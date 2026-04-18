from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tomllib
from typing import cast

import pytest

from entry.sample import sample_type2
from peetsfea.type2_sampled import manifest_entry_for_sample_index


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
[modeled_objects.wall_parallel_stack_present]
range = [true, 0, 1, 2]
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


def _current_head_hash4() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()[:4]


def test_sample_type2_writes_manifest_object_sampled_tomls_and_step_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"
    exporter_calls: list[dict[str, object]] = []

    def _exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        output_dir_arg = cast(Path, kwargs["output_dir"])
        ledger_path = cast(Path, kwargs["ledger_path"])
        scene_step_path = output_dir_arg / "type2_scene.step"
        scene_step_path.write_text("STEP", encoding="utf-8")
        ledger_path.write_text(json.dumps({"scene_step_path": str(scene_step_path)}, indent=2), encoding="utf-8")
        return {"scene_step_path": str(scene_step_path)}

    document = sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=4,
        seed_n=3,
        sampler_n=2,
        aedt_builder_n=6,
        make_step_on_sample=True,
        exporter=_exporter,
    )
    captured = capsys.readouterr()

    assert json.loads(manifest_path.read_text(encoding="utf-8")) == document
    assert document["config"] == {
        "source_toml_path": str(source_toml_path.resolve(strict=False)),
        "seed_first": 4,
        "seed_n": 3,
        "sampler_n": 2,
        "make_step_on_sample": True,
        "aedt_builder_n": 6,
    }
    assert "[sample] stage=sample+step" in captured.out
    assert "[sample] progress 1/3" in captured.out
    assert "[sample] progress 3/3" in captured.out
    assert "[sample] stage=manifest write" in captured.out
    assert "[sample] done" in captured.out
    assert "elapsed_s=" in captured.out
    assert [entry["seed"] for entry in document["entries"]] == [4, 5, 6]
    assert [entry["sample_index"] for entry in document["entries"]] == [0, 1, 2]
    assert [entry["retry_number"] for entry in document["entries"]] == [0, 0, 0]
    assert len(exporter_calls) == 3

    sampled_owner_paths = [
        "modeled_objects.tx_rect_void_coil.outer_x_mm",
        "modeled_objects.tx_rect_void_coil.underlay_repeat_count",
        "modeled_objects.tx_rect_void_coil.underlay_gap_mm",
        "modeled_objects.tx_rect_void_coil.wall_parallel_stack_present",
        "modeled_objects.tx_rect_void_coil.void_x_over_outer_x",
        "modeled_objects.tx_rect_void_coil.margin_ratio",
    ]
    first_entry = document["entries"][0]
    head_hash4 = _current_head_hash4()
    generated_hash4 = hashlib.blake2b(
        Path(first_entry["sampled_toml_path"]).read_bytes(),
        digest_size=2,
    ).hexdigest()
    assert first_entry["design_id"] == f"s000000_{generated_hash4}_{head_hash4}_0"
    assert Path(first_entry["design_dir"]).name == first_entry["design_id"]
    assert first_entry["sampled_owner_paths"] == sampled_owner_paths
    assert Path(first_entry["sampled_toml_path"]).is_file()
    assert Path(first_entry["scene_step_path"]).is_file()
    assert Path(first_entry["step_ledger_path"]).is_file()
    assert Path(first_entry["aedt_path"]).exists() is False

    sampled_payload = tomllib.loads(Path(first_entry["sampled_toml_path"]).read_text(encoding="utf-8"))
    sampled_metadata = sampled_payload["sampled"]
    assert sampled_metadata["source_toml_path"] == str(source_toml_path.resolve(strict=False))
    assert sampled_metadata["seed"] == 4
    assert sampled_metadata["sample_index"] == 0
    assert sampled_metadata["head_hash4"] == head_hash4
    assert sampled_metadata["retry_number"] == 0
    assert sampled_metadata["sampled_owner_paths"] == sampled_owner_paths
    assert "design_id" not in sampled_metadata

    modeled_object = sampled_payload["modeled_objects"][0]
    assert modeled_object["outer_x_mm"]["range"][3] == 1
    assert modeled_object["underlay_repeat_count"]["range"][3] == 1
    assert modeled_object["underlay_gap_mm"]["range"][3] == 1
    assert modeled_object["wall_parallel_stack_present"]["range"][3] == 1
    assert modeled_object["void_x_over_outer_x"]["range"][3] == 1
    assert modeled_object["margin_ratio"]["range"][3] == 1
    assert modeled_object["layer_gap_mm"]["range"] == [False, 2.0, 2.0, 1]
    assert "modeled_objects.tx_rect_void_coil.layer_gap_mm" not in sampled_metadata["sampled_owner_paths"]

    resolved_entry = manifest_entry_for_sample_index(manifest_path, sample_index=0)
    assert resolved_entry["design_id"] == first_entry["design_id"]


def test_manifest_entry_for_sample_index_rejects_out_of_range(tmp_path: Path) -> None:
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"

    def _exporter(**kwargs: object) -> object:
        output_dir_arg = cast(Path, kwargs["output_dir"])
        ledger_path = cast(Path, kwargs["ledger_path"])
        scene_step_path = output_dir_arg / "type2_scene.step"
        scene_step_path.write_text("STEP", encoding="utf-8")
        ledger_path.write_text(json.dumps({"scene_step_path": str(scene_step_path)}, indent=2), encoding="utf-8")
        return {"scene_step_path": str(scene_step_path)}

    sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=10,
        seed_n=2,
        sampler_n=1,
        aedt_builder_n=6,
        exporter=_exporter,
    )

    with pytest.raises(IndexError, match=r"sample_index is out of range"):
        manifest_entry_for_sample_index(manifest_path, sample_index=2)


def test_sample_type2_can_write_manifest_without_step_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"
    exporter_calls: list[dict[str, object]] = []

    def _exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        raise AssertionError("sample exporter must not be called when make_step_on_sample is False")

    document = sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=20,
        seed_n=2,
        sampler_n=2,
        aedt_builder_n=6,
        make_step_on_sample=False,
        exporter=_exporter,
    )
    captured = capsys.readouterr()

    assert document["config"] == {
        "source_toml_path": str(source_toml_path.resolve(strict=False)),
        "seed_first": 20,
        "seed_n": 2,
        "sampler_n": 2,
        "make_step_on_sample": False,
        "aedt_builder_n": 6,
    }
    assert "[sample] stage=sample-only" in captured.out
    assert "[sample] done" in captured.out
    assert exporter_calls == []
    for entry in document["entries"]:
        assert Path(entry["sampled_toml_path"]).is_file()
        assert Path(entry["scene_step_path"]).exists() is False
        assert Path(entry["step_ledger_path"]).exists() is False
        assert Path(entry["aedt_path"]).exists() is False

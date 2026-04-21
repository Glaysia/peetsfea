from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import tomllib
from typing import cast

import pytest

import peetsfea.type2_sampled as type2_sampled
from entry.sample import sample_type2
from peetsfea.type2_sampled import manifest_entry_for_sample_index
from peetsfea.type2_step_spec import NonModelTxRegionActualSpec
from peetsfea.type2_step_spec import NonModelTxRegionActualStackSpaceSpec
from peetsfea.type2_step_spec import ModeledRxSingleCoilSpec
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import load_type2_step_spec

_EXPECTED_SAMPLED_OWNER_PATHS = [
    "non_model_objects.tx_region_actual.x_usage_ratio",
    "non_model_objects.tx_region_actual.y_usage_ratio",
    "non_model_objects.tx_region_actual.x_division_count",
    "non_model_objects.tx_region_actual.y_division_count",
    "non_model_objects.tx_region_actual_stack_space.scale_ratio",
    "modeled_objects.rx_rect_void_coil.outer_x_usage_ratio",
    "modeled_objects.rx_rect_void_coil.outer_y_usage_ratio",
    "modeled_objects.rx_rect_void_coil.void_usage_ratio",
    "modeled_objects.rx_rect_void_coil.turn_count",
    "modeled_objects.rx_rect_void_coil.metal_fill_factor",
]
_RX_NON_SAMPLED_OWNER_PATHS = [
    "modeled_objects.rx_rect_void_coil.layer_count",
    "modeled_objects.rx_rect_void_coil.underlay_repeat_count",
]


@dataclass(frozen=True)
class _FakeRxOnlyType2Spec:
    non_model_derived_objects: tuple[NonModelTxRegionActualSpec | NonModelTxRegionActualStackSpaceSpec, ...]
    modeled_objects: tuple[ModeledRxSingleCoilSpec, ...]


def _patch_rx_only_spec_loader(
    monkeypatch: pytest.MonkeyPatch,
    *,
    loader_calls: list[Path] | None = None,
) -> None:
    source_spec_loader = load_type2_step_spec
    rx_outer_x_usage_ratio = RangeSpec(is_integer=False, start=0.1, end=0.6, count=17)
    rx_outer_y_usage_ratio = RangeSpec(is_integer=False, start=0.1, end=0.6, count=17)
    rx_void_usage_ratio = RangeSpec(is_integer=False, start=0.1, end=0.6, count=17)
    rx_outer_x = RangeSpec(is_integer=False, start=20.0, end=120.0, count=17)
    rx_outer_y = RangeSpec(is_integer=False, start=20.0, end=120.0, count=17)
    rx_turn_count = RangeSpec(is_integer=True, start=2.0, end=6.0, count=5)
    rx_layer_count = RangeSpec(is_integer=True, start=1.0, end=1.0, count=1)
    rx_underlay_repeat_count = RangeSpec(is_integer=True, start=8.0, end=8.0, count=1)
    rx_layer_gap = RangeSpec(is_integer=False, start=2.0, end=2.0, count=1)
    rx_terminal_stub = RangeSpec(is_integer=False, start=5.0, end=5.0, count=1)
    rx_margin_ratio = RangeSpec(is_integer=False, start=0.05, end=0.05, count=1)
    rx_fill_factor = RangeSpec(is_integer=False, start=0.2, end=0.6, count=15)
    tx_region_actual_x_usage_ratio = RangeSpec(is_integer=False, start=0.3, end=1.0, count=27)
    tx_region_actual_y_usage_ratio = RangeSpec(is_integer=False, start=0.3, end=1.0, count=27)
    tx_region_actual_x_division_count = RangeSpec(is_integer=True, start=1, end=3, count=3)
    tx_region_actual_y_division_count = RangeSpec(is_integer=True, start=1, end=3, count=3)
    tx_region_actual_stack_space_scale_ratio = RangeSpec(is_integer=False, start=0.35, end=0.95, count=25)
    tx_region_actual_stack_space_tilt_enabled = RangeSpec(is_integer=True, start=1, end=1, count=1)

    fake_spec = _FakeRxOnlyType2Spec(
        non_model_derived_objects=(
            NonModelTxRegionActualSpec(
                object_id="tx_region_actual",
                kind="tx_region_actual",
                source_region_id="tx_region",
                x_usage_ratio=tx_region_actual_x_usage_ratio,
                y_usage_ratio=tx_region_actual_y_usage_ratio,
                x_division_count=tx_region_actual_x_division_count,
                y_division_count=tx_region_actual_y_division_count,
            ),
            NonModelTxRegionActualStackSpaceSpec(
                object_id="tx_region_actual_stack_space",
                kind="tx_region_actual_stack_space",
                source_region_id="tx_region_actual",
                total_thickness_mm=5.0,
                scale_ratio=tx_region_actual_stack_space_scale_ratio,
                tilt_enabled=tx_region_actual_stack_space_tilt_enabled,
            ),
        ),
        modeled_objects=(
            ModeledRxSingleCoilSpec(
                object_id="rx_rect_void_coil",
                role="rx_single_coil",
                material="composite",
                model_state=True,
                pcb_thickness_mm=0.3,
                copper_thickness_mm=0.1,
                outer_x_usage_ratio=rx_outer_x_usage_ratio,
                outer_y_usage_ratio=rx_outer_y_usage_ratio,
                void_usage_ratio=rx_void_usage_ratio,
                outer_x_mm=rx_outer_x,
                outer_y_mm=rx_outer_y,
                turn_count=rx_turn_count,
                layer_count=rx_layer_count,
                underlay_repeat_count=rx_underlay_repeat_count,
                layer_gap_mm=rx_layer_gap,
                terminal_stub_length_mm=rx_terminal_stub,
                margin_ratio=rx_margin_ratio,
                metal_fill_factor=rx_fill_factor,
                terminal_path="A_cw_to_a",
            ),
        )
    )

    def _patched_loader(toml_path: Path) -> object:
        if loader_calls is not None:
            loader_calls.append(toml_path)
        if toml_path.name == "type2_sweep.toml":
            return fake_spec
        return source_spec_loader(toml_path)
    
    monkeypatch.setattr(type2_sampled, "load_type2_step_spec", _patched_loader)


def _source_type2_toml_text() -> str:
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.type2.step.v8"
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
name = "Lrx_uH"
expression = "im(Zt(RX_TML,RX_TML))/2/pi/freq*1e6"

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
plane = "YZ"
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

[[non_model_objects]]
id = "tx_region_actual"
kind = "tx_region_actual"
source_region_id = "tx_region"
[non_model_objects.x_usage_ratio]
range = [false, 0.3, 1.0, 27]
[non_model_objects.y_usage_ratio]
range = [false, 0.3, 1.0, 27]
[non_model_objects.x_division_count]
range = [true, 1, 3, 3]
[non_model_objects.y_division_count]
range = [true, 1, 3, 3]

[[non_model_objects]]
id = "tx_region_actual_stack_space"
kind = "tx_region_actual_stack_space"
source_region_id = "tx_region_actual"
total_thickness_mm = 5.0
[non_model_objects.scale_ratio]
range = [false, 0.35, 0.95, 25]
[non_model_objects.tilt_enabled]
range = [true, 1, 1, 1]

[[modeled_objects]]
    object_id = "rx_rect_void_coil"
    role = "rx_single_coil"
    material = "composite"
    model_state = true
    pcb_thickness_mm = 0.3
    copper_thickness_mm = 0.1
    [modeled_objects.outer_x_usage_ratio]
    range = [false, 0.1, 0.6, 17]
    [modeled_objects.outer_y_usage_ratio]
    range = [false, 0.1, 0.6, 17]
    [modeled_objects.void_usage_ratio]
    range = [false, 0.1, 0.6, 17]
    [modeled_objects.turn_count]
    range = [true, 2, 6, 5]
    [modeled_objects.layer_count]
    range = [true, 1, 1, 1]
    [modeled_objects.underlay_repeat_count]
    range = [true, 8, 8, 1]
    [modeled_objects.layer_gap_mm]
    range = [false, 2, 2, 1]
    [modeled_objects.terminal_stub_length_mm]
    range = [false, 5, 5, 1]
    [modeled_objects.margin_ratio]
    range = [false, 0.05, 0.05, 1]
    [modeled_objects.metal_fill_factor]
    range = [false, 0.2, 0.6, 15]
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
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_rx_only_spec_loader(monkeypatch)
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"
    exporter_calls: list[dict[str, object]] = []

    def _exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        report_stage = cast(Callable[[str], None], kwargs["stage_reporter"])
        report_stage("build_scene")
        report_stage("export_scene_step")
        report_stage("finalize_step_artifacts")
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
        sampler_n=1,
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
        "sampler_n": 1,
        "make_step_on_sample": True,
        "aedt_builder_n": 6,
    }
    assert "[sample] stage=sample+step" in captured.out
    for entry in document["entries"]:
        assert (
            f"[sample] step start idx={entry['sample_index']} seed={entry['seed']} "
            f"design_id={entry['design_id']}"
        ) in captured.out
        assert (
            f"[sample] step phase=build_scene idx={entry['sample_index']} "
            f"seed={entry['seed']} design_id={entry['design_id']}"
        ) in captured.out
        assert (
            f"[sample] step phase=export_scene_step idx={entry['sample_index']} "
            f"seed={entry['seed']} design_id={entry['design_id']}"
        ) in captured.out
        assert (
            f"[sample] step phase=finalize_step_artifacts idx={entry['sample_index']} "
            f"seed={entry['seed']} design_id={entry['design_id']}"
        ) in captured.out
        assert (
            f"[sample] step done idx={entry['sample_index']} seed={entry['seed']} "
            f"design_id={entry['design_id']}"
        ) in captured.out
    assert "[sample] progress 1/3" in captured.out
    assert "[sample] progress 3/3" in captured.out
    assert "[sample] stage=manifest write" in captured.out
    assert "[sample] done" in captured.out
    assert "elapsed_s=" in captured.out
    assert [entry["seed"] for entry in document["entries"]] == [4, 5, 6]
    assert [entry["sample_index"] for entry in document["entries"]] == [0, 1, 2]
    assert [entry["retry_number"] for entry in document["entries"]] == [0, 0, 0]
    assert len(exporter_calls) == 3

    first_entry = document["entries"][0]
    head_hash4 = _current_head_hash4()
    generated_hash4 = hashlib.blake2b(
        Path(first_entry["sampled_toml_path"]).read_bytes(),
        digest_size=2,
    ).hexdigest()
    assert first_entry["design_id"] == f"s000000_{generated_hash4}_{head_hash4}_0"
    assert Path(first_entry["design_dir"]).name == first_entry["design_id"]
    assert first_entry["sampled_owner_paths"] == _EXPECTED_SAMPLED_OWNER_PATHS
    assert all(path not in first_entry["sampled_owner_paths"] for path in _RX_NON_SAMPLED_OWNER_PATHS)
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
    assert sampled_metadata["sampled_owner_paths"] == _EXPECTED_SAMPLED_OWNER_PATHS
    assert all(path not in sampled_metadata["sampled_owner_paths"] for path in _RX_NON_SAMPLED_OWNER_PATHS)
    assert "design_id" not in sampled_metadata

    non_model_objects = cast(list[dict[str, object]], sampled_payload["non_model_objects"])
    tx_region_actual = next(non_model for non_model in non_model_objects if non_model["id"] == "tx_region_actual")
    tx_region_actual_x_range = cast(list[object], cast(dict[str, object], tx_region_actual["x_usage_ratio"])["range"])
    assert tx_region_actual_x_range[0] is False
    assert tx_region_actual_x_range[3] == 1
    assert tx_region_actual_x_range[1] == tx_region_actual_x_range[2]
    assert 0.3 <= float(cast(int | float, tx_region_actual_x_range[1])) <= 1.0
    tx_region_actual_y_range = cast(list[object], cast(dict[str, object], tx_region_actual["y_usage_ratio"])["range"])
    assert tx_region_actual_y_range[0] is False
    assert tx_region_actual_y_range[3] == 1
    assert tx_region_actual_y_range[1] == tx_region_actual_y_range[2]
    assert 0.3 <= float(cast(int | float, tx_region_actual_y_range[1])) <= 1.0
    tx_region_actual_x_division_count_range = cast(
        list[object], cast(dict[str, object], tx_region_actual["x_division_count"])["range"]
    )
    assert tx_region_actual_x_division_count_range[0] is True
    assert tx_region_actual_x_division_count_range[3] == 1
    assert tx_region_actual_x_division_count_range[1] == tx_region_actual_x_division_count_range[2]
    assert cast(int, tx_region_actual_x_division_count_range[1]) in {1, 2, 3}
    tx_region_actual_y_division_count_range = cast(
        list[object], cast(dict[str, object], tx_region_actual["y_division_count"])["range"]
    )
    assert tx_region_actual_y_division_count_range[0] is True
    assert tx_region_actual_y_division_count_range[3] == 1
    assert tx_region_actual_y_division_count_range[1] == tx_region_actual_y_division_count_range[2]
    assert cast(int, tx_region_actual_y_division_count_range[1]) in {1, 2, 3}
    tx_region_actual_stack_space = next(
        non_model for non_model in non_model_objects if non_model["id"] == "tx_region_actual_stack_space"
    )
    tx_region_actual_stack_space_scale_ratio_range = cast(
        list[object], cast(dict[str, object], tx_region_actual_stack_space["scale_ratio"])["range"]
    )
    assert tx_region_actual_stack_space_scale_ratio_range[0] is False
    assert tx_region_actual_stack_space_scale_ratio_range[3] == 1
    assert tx_region_actual_stack_space_scale_ratio_range[1] == tx_region_actual_stack_space_scale_ratio_range[2]
    assert 0.35 <= float(cast(int | float, tx_region_actual_stack_space_scale_ratio_range[1])) <= 0.95
    tx_region_actual_stack_space_tilt_enabled_range = cast(
        list[object], cast(dict[str, object], tx_region_actual_stack_space["tilt_enabled"])["range"]
    )
    assert tx_region_actual_stack_space_tilt_enabled_range[0] is True
    assert tx_region_actual_stack_space_tilt_enabled_range[3] == 1
    assert tx_region_actual_stack_space_tilt_enabled_range[1] == tx_region_actual_stack_space_tilt_enabled_range[2]
    assert tx_region_actual_stack_space_tilt_enabled_range[1] == 1

    rx_modeled_object = sampled_payload["modeled_objects"][0]
    assert rx_modeled_object["object_id"] == "rx_rect_void_coil"
    assert rx_modeled_object["role"] == "rx_single_coil"
    assert rx_modeled_object["pcb_thickness_mm"] == 0.3
    assert rx_modeled_object["copper_thickness_mm"] == 0.1
    assert "ferrite_set_count" not in rx_modeled_object
    rx_outer_x_range = rx_modeled_object["outer_x_usage_ratio"]["range"]
    assert rx_outer_x_range[0] is False
    assert rx_outer_x_range[3] == 1
    assert rx_outer_x_range[1] == rx_outer_x_range[2]
    assert 0.1 <= float(rx_outer_x_range[1]) <= 0.6
    rx_outer_y_range = rx_modeled_object["outer_y_usage_ratio"]["range"]
    assert rx_outer_y_range[0] is False
    assert rx_outer_y_range[3] == 1
    assert rx_outer_y_range[1] == rx_outer_y_range[2]
    assert 0.1 <= float(rx_outer_y_range[1]) <= 0.6
    rx_void_ratio_range = rx_modeled_object["void_usage_ratio"]["range"]
    assert rx_void_ratio_range[0] is False
    assert rx_void_ratio_range[3] == 1
    assert rx_void_ratio_range[1] == rx_void_ratio_range[2]
    assert 0.1 <= float(rx_void_ratio_range[1]) <= 0.6
    rx_turn_range = rx_modeled_object["turn_count"]["range"]
    assert rx_turn_range[0] is True
    assert rx_turn_range[3] == 1
    assert rx_turn_range[1] == rx_turn_range[2]
    assert rx_turn_range[1] in {2, 3, 4, 5, 6}
    rx_underlay_repeat_count_range = rx_modeled_object["underlay_repeat_count"]["range"]
    assert rx_underlay_repeat_count_range[0] is True
    assert rx_underlay_repeat_count_range[3] == 1
    assert rx_underlay_repeat_count_range[1] == rx_underlay_repeat_count_range[2]
    assert rx_underlay_repeat_count_range[1] == 8
    rx_fill_range = rx_modeled_object["metal_fill_factor"]["range"]
    assert rx_fill_range[0] is False
    assert rx_fill_range[3] == 1
    assert rx_fill_range[1] == rx_fill_range[2]
    assert 0.2 <= float(rx_fill_range[1]) <= 0.6
    assert "tx_coil_count" not in rx_modeled_object
    assert "tx_array_x_usage_ratio" not in rx_modeled_object
    assert rx_modeled_object["layer_count"]["range"] == [True, 1, 1, 1]
    assert rx_modeled_object["layer_gap_mm"]["range"] == [False, 2.0, 2.0, 1]
    assert rx_modeled_object["terminal_stub_length_mm"]["range"] == [False, 5.0, 5.0, 1]
    assert "void_x_over_outer_x" not in rx_modeled_object
    assert "void_y_over_outer_y" not in rx_modeled_object
    assert "void_center_x_over_outer_x" not in rx_modeled_object
    assert "void_center_y_over_outer_y" not in rx_modeled_object
    assert rx_modeled_object["margin_ratio"]["range"] == [False, 0.05, 0.05, 1]
    assert rx_modeled_object["terminal_path"]["value"] == "A_cw_to_a"
    assert "z_usage_ratio" not in rx_modeled_object
    assert "y_usage_ratio" not in rx_modeled_object
    assert "pcb_total_thickness_mm" not in rx_modeled_object
    assert "underlay_gap_mm" not in rx_modeled_object

    resolved_entry = manifest_entry_for_sample_index(manifest_path, sample_index=0)
    assert resolved_entry["design_id"] == first_entry["design_id"]


def test_sample_type2_load_type2_step_spec_hook_via_type2_sampled_module(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    patched_calls: list[Path] = []
    _patch_rx_only_spec_loader(monkeypatch, loader_calls=patched_calls)
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"

    document = sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=101,
        seed_n=2,
        sampler_n=1,
        aedt_builder_n=1,
        make_step_on_sample=False,
    )

    assert patched_calls == [source_toml_path]
    assert [entry["seed"] for entry in document["entries"]] == [101, 102]
    assert [entry["sample_index"] for entry in document["entries"]] == [0, 1]
    assert [entry["retry_number"] for entry in document["entries"]] == [0, 0]
    for entry in document["entries"]:
        assert Path(entry["sampled_toml_path"]).is_file()
        assert Path(entry["scene_step_path"]).exists() is False
        assert Path(entry["step_ledger_path"]).exists() is False
        assert Path(entry["aedt_path"]).exists() is False


def test_manifest_entry_for_sample_index_rejects_out_of_range(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_rx_only_spec_loader(monkeypatch)
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
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_rx_only_spec_loader(monkeypatch)
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
    assert "[sample] step start" not in captured.out
    assert "[sample] step phase=" not in captured.out
    assert "[sample] step done" not in captured.out
    assert exporter_calls == []
    for entry in document["entries"]:
        assert entry["sampled_owner_paths"] == _EXPECTED_SAMPLED_OWNER_PATHS
        assert Path(entry["sampled_toml_path"]).is_file()
        assert Path(entry["scene_step_path"]).exists() is False
        assert Path(entry["step_ledger_path"]).exists() is False
        assert Path(entry["aedt_path"]).exists() is False


def _source_type2_toml_text_with_tx_rect_void_columns(
) -> str:
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.type2.step.v8"
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
id = "tx_region"
kind = "tx_region"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
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

[[non_model_objects]]
id = "tx_region_actual"
kind = "tx_region_actual"
source_region_id = "tx_region"
[non_model_objects.x_usage_ratio]
range = [false, 0.3, 1.0, 27]
[non_model_objects.y_usage_ratio]
range = [false, 0.3, 1.0, 27]
[non_model_objects.x_division_count]
range = [true, 1, 3, 3]
[non_model_objects.y_division_count]
range = [true, 1, 3, 3]

[[non_model_objects]]
id = "tx_region_actual_stack_space"
kind = "tx_region_actual_stack_space"
source_region_id = "tx_region_actual"
total_thickness_mm = 5.0
[non_model_objects.scale_ratio]
range = [false, 0.35, 0.95, 25]
[non_model_objects.tilt_enabled]
range = [true, 1, 1, 1]

[[modeled_objects]]
object_id = "rx_rect_void_coil"
role = "rx_single_coil"
material = "composite"
model_state = true
pcb_thickness_mm = 0.3
copper_thickness_mm = 0.1
[modeled_objects.outer_x_usage_ratio]
range = [false, 0.1, 0.6, 17]
[modeled_objects.outer_y_usage_ratio]
range = [false, 0.1, 0.6, 17]
[modeled_objects.void_usage_ratio]
range = [false, 0.1, 0.6, 17]
[modeled_objects.turn_count]
range = [true, 2, 6, 5]
[modeled_objects.layer_count]
range = [true, 1, 1, 1]
[modeled_objects.underlay_repeat_count]
range = [true, 8, 8, 1]
[modeled_objects.layer_gap_mm]
range = [false, 2, 2, 1]
[modeled_objects.terminal_stub_length_mm]
range = [false, 5, 5, 1]
[modeled_objects.margin_ratio]
range = [false, 0.05, 0.05, 1]
[modeled_objects.metal_fill_factor]
range = [false, 0.2, 0.6, 15]
[modeled_objects.terminal_path]
value = "A_cw_to_a"

[[modeled_objects]]
object_id = "tx_rect_void_columns"
role = "tx_rect_void_columns"
material = "composite"
model_state = true
pcb_thickness_mm = 0.3
copper_thickness_mm = 0.1
[modeled_objects.layer_count]
range = [true, 1, 4, 4]
[modeled_objects.layer_gap_mm]
range = [false, 1.0, 1.8, 5]
[modeled_objects.terminal_stub_length_mm]
range = [false, 10.0, 10.0, 1]
[modeled_objects.void_usage_ratio]
range = [false, 0.1, 0.6, 17]
[modeled_objects.margin_ratio]
range = [false, 0.05, 0.05, 1]
[modeled_objects.metal_fill_factor]
range = [false, 0.2, 0.6, 15]
[modeled_objects.terminal_path]
value = "A_cw_to_a"
[modeled_objects.connection_mode]
range = [true, 0, 1, 2]
[modeled_objects.series_total_turn_count]
range = [true, 1, 36, 36]
[modeled_objects.parallel_total_turn_count]
range = [true, 1, 36, 36]
[modeled_objects.turn_weight_a]
range = [false, 0.5, 1.5, 5]
[modeled_objects.turn_weight_b]
range = [false, -0.5, 0.5, 21]
[modeled_objects.turn_weight_c]
range = [false, -0.3, 0.3, 21]
""".strip()


def test_sampled_owner_values_tx_rect_void_columns_uses_mode_aware_effective_turn_owner(
    tmp_path: Path,
) -> None:
    source_toml_path = tmp_path / "type2_tx_rect_source.toml"
    source_toml_path.write_text(_source_type2_toml_text_with_tx_rect_void_columns(), encoding="utf-8")
    spec = load_type2_step_spec(source_toml_path)

    owner_prefix = "modeled_objects.tx_rect_void_columns"
    connection_mode_path = f"{owner_prefix}.connection_mode"
    series_owner_path = f"{owner_prefix}.series_total_turn_count"
    parallel_owner_path = f"{owner_prefix}.parallel_total_turn_count"
    turn_weight_paths = (
        f"{owner_prefix}.turn_weight_a",
        f"{owner_prefix}.turn_weight_b",
        f"{owner_prefix}.turn_weight_c",
    )
    observed_modes: set[int] = set()
    for seed in range(32):
        sampled_owner_values = dict(type2_sampled.sampled_owner_values(spec, seed=seed))
        assert connection_mode_path in sampled_owner_values
        for turn_weight_path in turn_weight_paths:
            assert turn_weight_path in sampled_owner_values
        assert all("turn_count_x" not in owner_path for owner_path in sampled_owner_values)
        raw_connection_mode = sampled_owner_values[connection_mode_path]
        assert isinstance(raw_connection_mode, int)
        assert raw_connection_mode in {0, 1}
        observed_modes.add(raw_connection_mode)
        has_series_owner = series_owner_path in sampled_owner_values
        has_parallel_owner = parallel_owner_path in sampled_owner_values
        assert has_series_owner is not has_parallel_owner
        if raw_connection_mode == 1:
            assert has_series_owner
            assert has_parallel_owner is False
        else:
            assert has_series_owner is False
            assert has_parallel_owner
    assert observed_modes == {0, 1}


def test_sample_type2_tx_rect_void_columns_sample_only_emits_manifest_and_sampled_toml(
    tmp_path: Path,
) -> None:
    source_toml_path = tmp_path / "type2_tx_rect_source.toml"
    source_toml_path.write_text(_source_type2_toml_text_with_tx_rect_void_columns(), encoding="utf-8")
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"
    document = sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=11,
        seed_n=4,
        sampler_n=1,
        aedt_builder_n=1,
        make_step_on_sample=False,
    )

    assert manifest_path.is_file()
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == document
    assert len(document["entries"]) == 4
    owner_prefix = "modeled_objects.tx_rect_void_columns"
    connection_mode_path = f"{owner_prefix}.connection_mode"
    series_owner_path = f"{owner_prefix}.series_total_turn_count"
    parallel_owner_path = f"{owner_prefix}.parallel_total_turn_count"
    turn_weight_paths = (
        f"{owner_prefix}.turn_weight_a",
        f"{owner_prefix}.turn_weight_b",
        f"{owner_prefix}.turn_weight_c",
    )
    for entry in document["entries"]:
        sampled_owner_paths = cast(list[str], entry["sampled_owner_paths"])
        assert connection_mode_path in sampled_owner_paths
        assert all(turn_weight_path in sampled_owner_paths for turn_weight_path in turn_weight_paths)
        assert (series_owner_path in sampled_owner_paths) is not (parallel_owner_path in sampled_owner_paths)


def test_sample_type2_sweep_ssot_emits_tx_columns_manifest_and_sampled_toml(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml_path = repo_root / "examples" / "type2_sweep.toml"
    spec = load_type2_step_spec(source_toml_path)
    assert len(spec.modeled_objects) == 2
    assert {modeled_object.role for modeled_object in spec.modeled_objects} == {
        "rx_single_coil",
        "tx_rect_void_columns",
    }
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"

    document = sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=21,
        seed_n=2,
        sampler_n=1,
        aedt_builder_n=1,
        make_step_on_sample=False,
    )

    assert manifest_path.is_file()
    assert len(document["entries"]) == 2
    owner_prefix = "modeled_objects.tx_rect_void_columns"
    series_owner_path = f"{owner_prefix}.series_total_turn_count"
    parallel_owner_path = f"{owner_prefix}.parallel_total_turn_count"
    for entry in document["entries"]:
        sampled_owner_paths = cast(list[str], entry["sampled_owner_paths"])
        assert f"{owner_prefix}.connection_mode" in sampled_owner_paths
        assert f"{owner_prefix}.turn_weight_a" in sampled_owner_paths
        assert f"{owner_prefix}.turn_weight_b" in sampled_owner_paths
        assert f"{owner_prefix}.turn_weight_c" in sampled_owner_paths
        assert (f"{owner_prefix}.series_total_turn_count" in sampled_owner_paths) is not (
            f"{owner_prefix}.parallel_total_turn_count" in sampled_owner_paths
        )
        sampled_toml_path = Path(cast(str, entry["sampled_toml_path"]))
        assert sampled_toml_path.is_file()
        sampled_payload = tomllib.loads(sampled_toml_path.read_text(encoding="utf-8"))
        modeled_objects = cast(list[dict[str, object]], sampled_payload["modeled_objects"])
        tx_columns = next(
            modeled_object
            for modeled_object in modeled_objects
            if modeled_object["object_id"] == "tx_rect_void_columns"
        )
        assert "turn_count_x0" not in tx_columns
        assert "column_connection_mode" not in tx_columns
        assert all("turn_count_x" not in owner_path for owner_path in sampled_owner_paths)
        sampled_toml_path = Path(cast(str, entry["sampled_toml_path"]))
        assert sampled_toml_path.is_file()
        assert Path(entry["scene_step_path"]).exists() is False
        assert Path(entry["step_ledger_path"]).exists() is False
        assert Path(entry["aedt_path"]).exists() is False

        sampled_payload = tomllib.loads(sampled_toml_path.read_text(encoding="utf-8"))
        sampled_metadata = cast(dict[str, object], sampled_payload["sampled"])
        assert cast(list[str], sampled_metadata["sampled_owner_paths"]) == sampled_owner_paths
        modeled_objects = cast(list[dict[str, object]], sampled_payload["modeled_objects"])
        tx_rect_columns_object = next(
            modeled_object
            for modeled_object in modeled_objects
            if modeled_object["object_id"] == "tx_rect_void_columns"
        )
        assert "turn_count_x0" not in tx_rect_columns_object
        assert "turn_count_x1" not in tx_rect_columns_object
        assert "turn_count_x2" not in tx_rect_columns_object
        connection_mode_range = cast(
            list[object],
            cast(dict[str, object], tx_rect_columns_object["connection_mode"])["range"],
        )
        assert connection_mode_range[0] is True
        assert connection_mode_range[3] == 1
        assert connection_mode_range[1] == connection_mode_range[2]
        sampled_connection_mode = cast(int, connection_mode_range[1])
        assert sampled_connection_mode in {0, 1}
        if sampled_connection_mode == 1:
            assert series_owner_path in sampled_owner_paths
            assert parallel_owner_path not in sampled_owner_paths
        else:
            assert series_owner_path not in sampled_owner_paths
            assert parallel_owner_path in sampled_owner_paths

        series_range = cast(
            list[object],
            cast(dict[str, object], tx_rect_columns_object["series_total_turn_count"])["range"],
        )
        parallel_range = cast(
            list[object],
            cast(dict[str, object], tx_rect_columns_object["parallel_total_turn_count"])["range"],
        )
        assert series_range[3] == 1
        assert series_range[1] == series_range[2]
        assert parallel_range[3] == 1
        assert parallel_range[1] == parallel_range[2]


def test_sample_type2_fixed_ssot_keeps_two_modeled_objects() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml_path = repo_root / "examples" / "type2_fixed.toml"
    spec = load_type2_step_spec(source_toml_path)

    assert len(spec.modeled_objects) == 2
    assert {modeled_object.role for modeled_object in spec.modeled_objects} == {
        "rx_single_coil",
        "tx_rect_void_columns",
    }

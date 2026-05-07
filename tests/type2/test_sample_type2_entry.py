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

import entry.sample as sample_entry
import peetsfea.type2_sampled as type2_sampled
from entry.sample import run_sample_cli, sample_type2
from peetsfea.type2_sampled import manifest_entry_for_sample_index
from peetsfea.type2_step_spec import NonModelDerivedSpec
from peetsfea.type2_step_spec import NonModelTxReferenceLineSpec
from peetsfea.type2_step_spec import NonModelTxRegionSpec
from peetsfea.type2_step_spec import ModeledRxSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import Type2StepSpec
from peetsfea.type2_step_spec import load_type2_step_spec

_EXPECTED_SAMPLED_OWNER_PATHS = [
    "non_model_objects.tx_region.tx_reference_line.y_usage_ratio",
    "non_model_objects.tx_region.tx_reference_line.z_ratio",
    "modeled_objects.tx_inner_rect_void_coil.outer_y_usage_ratio",
    "modeled_objects.tx_inner_rect_void_coil.void_stack_present",
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
    non_model_objects: tuple[NonModelTxRegionSpec, ...]
    non_model_derived_objects: tuple[NonModelDerivedSpec, ...]
    modeled_objects: tuple[ModeledTxInnerSingleCoilSpec | ModeledRxSingleCoilSpec, ...]


def _range_spec(is_integer: bool, start: float, end: float, count: int) -> RangeSpec:
    return RangeSpec(is_integer=is_integer, start=start, end=end, count=count)


def _tx_inner_single_coil_spec() -> ModeledTxInnerSingleCoilSpec:
    fixed_one = _range_spec(True, 1.0, 1.0, 1)
    fixed_void_stack_present = _range_spec(True, 1.0, 1.0, 1)
    fixed_tx_inner_underlay_thickness = _range_spec(False, 6.0, 6.0, 1)
    fixed_float = _range_spec(False, 1.0, 1.0, 1)
    return ModeledTxInnerSingleCoilSpec(
        object_id="tx_inner_rect_void_coil",
        role="tx_inner_single_coil",
        material="composite",
        model_state=True,
        pcb_thickness_mm=0.3,
        copper_thickness_mm=0.035,
        outer_x_usage_ratio=_range_spec(False, 0.2, 0.8, 7),
        outer_y_usage_ratio=_range_spec(False, 0.2, 0.8, 7),
        outer_x_mm=_range_spec(False, 100.0, 100.0, 1),
        outer_y_mm=_range_spec(False, 80.0, 80.0, 1),
        void_usage_ratio=_range_spec(False, 0.3, 0.3, 1),
        turn_count=_range_spec(True, 2.0, 5.0, 4),
        layer_count=_range_spec(True, 1.0, 1.0, 1),
        underlay_repeat_count=fixed_one,
        void_stack_present=fixed_void_stack_present,
        underlay_pet_psa_thickness_mm=fixed_tx_inner_underlay_thickness,
        underlay_ferrite_thickness_mm=fixed_tx_inner_underlay_thickness,
        layer_gap_mm=_range_spec(False, 2.0, 2.0, 1),
        terminal_stub_length_mm=_range_spec(False, 5.0, 5.0, 1),
        margin_ratio=_range_spec(False, 0.05, 0.05, 1),
        metal_fill_factor=fixed_float,
        terminal_path="B_cw_to_b",
        x_position_ratio=_range_spec(False, 0.0, 0.0, 1),
    )


def test_exportable_sampled_owner_paths_exclude_tx_outer_derived_owners() -> None:
    spec = _FakeRxOnlyType2Spec(
        non_model_objects=(),
        non_model_derived_objects=(),
        modeled_objects=(
            _tx_inner_single_coil_spec(),
        ),
    )

    owner_paths = type2_sampled.exportable_sampled_owner_paths_for_seed(cast(Type2StepSpec, spec), seed=11)

    assert "modeled_objects.tx_inner_rect_void_coil.outer_x_usage_ratio" in owner_paths
    assert "modeled_objects.tx_inner_rect_void_coil.outer_y_usage_ratio" in owner_paths
    assert "modeled_objects.tx_inner_rect_void_coil.turn_count" in owner_paths
    assert "modeled_objects.tx_inner_rect_void_coil.x_position_ratio" not in owner_paths
    assert all(not owner_path.startswith("modeled_objects.tx_outer_rect_void_coil.") for owner_path in owner_paths)


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
    rx_turn_count = RangeSpec(is_integer=True, start=2.0, end=5.0, count=4)
    rx_layer_count = RangeSpec(is_integer=True, start=1.0, end=1.0, count=1)
    rx_underlay_repeat_count = RangeSpec(is_integer=True, start=8.0, end=8.0, count=1)
    rx_layer_gap = RangeSpec(is_integer=False, start=2.0, end=2.0, count=1)
    rx_terminal_stub = RangeSpec(is_integer=False, start=5.0, end=5.0, count=1)
    rx_margin_ratio = RangeSpec(is_integer=False, start=0.05, end=0.05, count=1)
    rx_fill_factor = RangeSpec(is_integer=False, start=0.2, end=0.6, count=15)
    tx_inner_underlay_thickness = RangeSpec(is_integer=False, start=6.0, end=6.0, count=1)
    tx_reference_line_x_ratio = RangeSpec(is_integer=False, start=0.99, end=0.99, count=1)
    tx_reference_line_y_usage_ratio = RangeSpec(is_integer=False, start=0.2, end=1.0, count=17)
    tx_reference_line_z_ratio = RangeSpec(is_integer=False, start=0.75, end=1.0, count=13)

    fake_spec = _FakeRxOnlyType2Spec(
        non_model_objects=(
            NonModelTxRegionSpec(
                object_id="tx_region",
                kind="tx_region",
                primitive="box",
                present=True,
                non_model=True,
                material="vacuum",
                plane="YZ",
                origin_xyz=(0.0, -140.0, 0.0),
                size_xyz=(160.0, 280.0, 90.0),
                tx_reference_line=NonModelTxReferenceLineSpec(
                    x_ratio=tx_reference_line_x_ratio,
                    y_usage_ratio=tx_reference_line_y_usage_ratio,
                    z_ratio=tx_reference_line_z_ratio,
                ),
            ),
        ),
        non_model_derived_objects=(),
        modeled_objects=(
            ModeledTxInnerSingleCoilSpec(
                object_id="tx_inner_rect_void_coil",
                role="tx_inner_single_coil",
                material="composite",
                model_state=True,
                pcb_thickness_mm=0.3,
                copper_thickness_mm=0.035,
                outer_x_usage_ratio=RangeSpec(is_integer=False, start=0.5, end=0.5, count=1),
                outer_y_usage_ratio=RangeSpec(is_integer=False, start=0.2, end=0.9, count=15),
                outer_x_mm=RangeSpec(is_integer=False, start=100.0, end=100.0, count=1),
                outer_y_mm=RangeSpec(is_integer=False, start=80.0, end=80.0, count=1),
                void_usage_ratio=RangeSpec(is_integer=False, start=0.2, end=0.2, count=1),
                turn_count=RangeSpec(is_integer=True, start=2.0, end=2.0, count=1),
                layer_count=RangeSpec(is_integer=True, start=1.0, end=1.0, count=1),
                underlay_repeat_count=RangeSpec(is_integer=True, start=1.0, end=1.0, count=1),
                void_stack_present=RangeSpec(is_integer=True, start=0.0, end=1.0, count=2),
                underlay_pet_psa_thickness_mm=tx_inner_underlay_thickness,
                underlay_ferrite_thickness_mm=tx_inner_underlay_thickness,
                layer_gap_mm=RangeSpec(is_integer=False, start=2.0, end=2.0, count=1),
                terminal_stub_length_mm=RangeSpec(is_integer=False, start=7.5, end=7.5, count=1),
                margin_ratio=RangeSpec(is_integer=False, start=0.05, end=0.05, count=1),
                metal_fill_factor=RangeSpec(is_integer=False, start=0.5, end=0.5, count=1),
                terminal_path="B_cw_to_b",
                x_position_ratio=RangeSpec(is_integer=False, start=0.0, end=0.0, count=1),
            ),
            ModeledRxSingleCoilSpec(
                object_id="rx_rect_void_coil",
                role="rx_single_coil",
                material="composite",
                model_state=True,
                pcb_thickness_mm=3.965,
                copper_thickness_mm=0.035,
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
                x_position_ratio=RangeSpec(is_integer=False, start=0.0, end=0.0, count=1),
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
    return """
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
mode = "RxOnly"
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
[non_model_objects.tx_reference_line.x_ratio]
range = [false, 0.99, 0.99, 1]
[non_model_objects.tx_reference_line.y_usage_ratio]
range = [false, 0.2, 1.0, 85]
[non_model_objects.tx_reference_line.z_ratio]
range = [false, 0.75, 1.0, 65]

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
    object_id = "tx_inner_rect_void_coil"
    role = "tx_inner_single_coil"
    material = "composite"
    model_state = true
    pcb_thickness_mm = 0.3
    copper_thickness_mm = 0.035
    [modeled_objects.outer_x_usage_ratio]
    range = [false, 0.5, 0.5, 1]
    [modeled_objects.outer_y_usage_ratio]
    range = [false, 0.2, 0.9, 150]
    [modeled_objects.x_position_ratio]
    range = [false, 0.0, 0.0, 1]
    [modeled_objects.turn_count]
    range = [true, 2, 2, 1]
    [modeled_objects.layer_count]
    range = [true, 2, 2, 1]
    [modeled_objects.underlay_repeat_count]
    range = [true, 0, 0, 1]
    [modeled_objects.void_stack_present]
    range = [true, 0, 1, 2]
    [modeled_objects.layer_gap_mm]
    range = [false, 2, 2, 1]
    [modeled_objects.terminal_stub_length_mm]
    range = [false, 7.5, 7.5, 1]
    [modeled_objects.margin_ratio]
    range = [false, 0.05, 0.05, 1]
    [modeled_objects.metal_fill_factor]
    range = [false, 0.5, 0.5, 1]
    [modeled_objects.void_usage_ratio]
    range = [false, 0.2, 0.2, 1]
    [modeled_objects.terminal_path]
    value = "B_cw_to_b"

[[modeled_objects]]
    object_id = "rx_rect_void_coil"
    role = "rx_single_coil"
    material = "composite"
    model_state = true
    pcb_thickness_mm = 3.965
    copper_thickness_mm = 0.035
    [modeled_objects.outer_x_usage_ratio]
    range = [false, 0.1, 0.6, 85]
    [modeled_objects.outer_y_usage_ratio]
    range = [false, 0.1, 0.6, 85]
    [modeled_objects.x_position_ratio]
    range = [false, 0.0, 0.0, 1]
    [modeled_objects.void_usage_ratio]
    range = [false, 0.1, 0.6, 85]
    [modeled_objects.turn_count]
    range = [true, 2, 5, 4]
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
    range = [false, 0.2, 0.6, 75]
    [modeled_objects.terminal_path]
    value = "A_cw_to_a"
""".strip()


def _write_source_type2_toml(tmp_path: Path) -> Path:
    path = tmp_path / "type2_sweep.toml"
    path.write_text(_source_type2_toml_text(), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("range_line", "match"),
    (
        ("range = [false, 0.1, 0.1, 1]", r"must be fixed \[false, 0\.0, 0\.0, 1\]"),
        ("range = [false, 0.0, 0.3, 45]", r"must be fixed \[false, 0\.0, 0\.0, 1\]"),
        ("range = [false, 0.0, 0.0, 2]", r"must be fixed \[false, 0\.0, 0\.0, 1\]"),
    ),
)
def test_load_type2_step_spec_rejects_tx_inner_x_position_ratio_non_fixed_zero(
    tmp_path: Path,
    range_line: str,
    match: str,
) -> None:
    fixed_block = """    [modeled_objects.x_position_ratio]
    range = [false, 0.0, 0.0, 1]
    [modeled_objects.turn_count]"""
    invalid_block = f"""    [modeled_objects.x_position_ratio]
    {range_line}
    [modeled_objects.turn_count]"""
    source_toml_path = tmp_path / "type2_invalid_tx_inner_x_position.toml"
    source_toml_path.write_text(
        _source_type2_toml_text().replace(fixed_block, invalid_block, 1),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=match):
        load_type2_step_spec(source_toml_path)


def _current_head_hash4() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()[:4]


def test_run_sample_cli_defaults_to_sample_only(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []

    def _sample_type2(**kwargs: object) -> dict[str, object]:
        calls.append(cast(bool, kwargs["make_step_on_sample"]))
        return {"config": {}, "entries": [], "skipped": []}

    monkeypatch.setattr(sample_entry, "sample_type2", _sample_type2)

    result = run_sample_cli(())

    assert result == {"config": {}, "entries": [], "skipped": []}
    assert calls == [False]


def test_run_sample_cli_omitted_seed_and_sampler_args_preserve_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def _sample_type2(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        return {"config": {}, "entries": [], "skipped": []}

    monkeypatch.setattr(sample_entry, "sample_type2", _sample_type2)

    result = run_sample_cli(())

    assert result == {"config": {}, "entries": [], "skipped": []}
    assert calls == [
        {
            "make_step_on_sample": False,
            "seed_first": sample_entry.SEED_FIRST,
            "seed_n": sample_entry.SEED_N,
            "sampler_n": sample_entry.SAMPLER_N,
        }
    ]


def test_run_sample_cli_seed_and_sampler_overrides_flow_to_sample_type2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def _sample_type2(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        return {"config": {}, "entries": [], "skipped": []}

    monkeypatch.setattr(sample_entry, "sample_type2", _sample_type2)

    result = run_sample_cli(("--seed-first", "7", "--seed-n", "2", "--sampler-n", "1"))

    assert result == {"config": {}, "entries": [], "skipped": []}
    assert calls == [
        {
            "make_step_on_sample": False,
            "seed_first": 7,
            "seed_n": 2,
            "sampler_n": 1,
        }
    ]


def test_run_sample_cli_build_step_flag_enables_step_export(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []

    def _sample_type2(**kwargs: object) -> dict[str, object]:
        calls.append(cast(bool, kwargs["make_step_on_sample"]))
        return {"config": {}, "entries": [], "skipped": []}

    monkeypatch.setattr(sample_entry, "sample_type2", _sample_type2)

    result = run_sample_cli(("--build-step",))

    assert result == {"config": {}, "entries": [], "skipped": []}
    assert calls == [True]


def test_sample_type2_seed_and_sampler_overrides_flow_to_manifest_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []

    def _generate_sample_manifest_attempts(**kwargs: object) -> dict[str, list[object]]:
        calls.append(dict(kwargs))
        return {"entries": [], "skipped": []}

    monkeypatch.setattr(sample_entry, "generate_sample_manifest_attempts", _generate_sample_manifest_attempts)
    source_toml_path = tmp_path / "type2_sweep.toml"

    document = sample_type2(
        source_toml_path=source_toml_path,
        output_dir=tmp_path / "sampled",
        manifest_path=tmp_path / "manifest.json",
        seed_first=7,
        seed_n=2,
        sampler_n=1,
        aedt_builder_n=6,
        make_step_on_sample=False,
    )

    assert document["config"] == {
        "source_toml_path": str(source_toml_path.resolve(strict=False)),
        "seed_first": 7,
        "seed_n": 2,
        "sampler_n": 1,
        "make_step_on_sample": False,
        "aedt_builder_n": 6,
    }
    assert len(calls) == 1
    assert calls[0]["seed_start"] == 7
    assert calls[0]["count"] == 2
    assert calls[0]["jobs"] == 1


def test_sample_type2_default_build_step_omits_exporter_for_worker_pool(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []

    def _generate_sample_manifest_attempts(**kwargs: object) -> dict[str, list[object]]:
        calls.append(dict(kwargs))
        return {"entries": [], "skipped": []}

    monkeypatch.setattr(sample_entry, "generate_sample_manifest_attempts", _generate_sample_manifest_attempts)

    document = sample_type2(
        source_toml_path=tmp_path / "type2_sweep.toml",
        output_dir=tmp_path / "sampled",
        manifest_path=tmp_path / "manifest.json",
        seed_first=4,
        seed_n=3,
        sampler_n=2,
        aedt_builder_n=6,
        make_step_on_sample=True,
    )

    assert document["entries"] == []
    assert document["skipped"] == []
    assert len(calls) == 1
    assert calls[0]["make_step_on_sample"] is True
    assert calls[0]["jobs"] == 2
    assert "exporter" not in calls[0]


def test_sample_type2_custom_exporter_is_forwarded_as_in_process_hook(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []

    def _generate_sample_manifest_attempts(**kwargs: object) -> dict[str, list[object]]:
        calls.append(dict(kwargs))
        return {"entries": [], "skipped": []}

    def _exporter(**kwargs: object) -> object:
        raise AssertionError("custom exporter should be forwarded, not called by sample_type2")

    monkeypatch.setattr(sample_entry, "generate_sample_manifest_attempts", _generate_sample_manifest_attempts)

    document = sample_type2(
        source_toml_path=tmp_path / "type2_sweep.toml",
        output_dir=tmp_path / "sampled",
        manifest_path=tmp_path / "manifest.json",
        seed_first=4,
        seed_n=3,
        sampler_n=2,
        aedt_builder_n=6,
        make_step_on_sample=True,
        exporter=_exporter,
    )

    assert document["entries"] == []
    assert document["skipped"] == []
    assert len(calls) == 1
    assert calls[0]["make_step_on_sample"] is True
    assert calls[0]["jobs"] == 2
    assert calls[0]["exporter"] is _exporter


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
        seed_first=12000,
        seed_n=3,
        sampler_n=1,
        aedt_builder_n=6,
        make_step_on_sample=True,
        exporter=_exporter,
    )
    captured = capsys.readouterr()

    loaded_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert loaded_manifest == document
    assert loaded_manifest["skipped"] == []
    assert document["skipped"] == []
    assert document["config"] == {
        "source_toml_path": str(source_toml_path.resolve(strict=False)),
        "seed_first": 12000,
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
    assert [entry["seed"] for entry in document["entries"]] == [12000, 12001, 12002]
    assert [entry["sample_index"] for entry in document["entries"]] == [12000, 12001, 12002]
    assert [entry["retry_number"] for entry in document["entries"]] == [0, 0, 0]
    assert len(exporter_calls) == 3

    first_entry = document["entries"][0]
    head_hash4 = _current_head_hash4()
    generated_hash4 = hashlib.blake2b(
        Path(first_entry["sampled_toml_path"]).read_bytes(),
        digest_size=2,
    ).hexdigest()
    assert first_entry["design_id"] == f"s012000_{generated_hash4}_{head_hash4}_0"
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
    assert sampled_metadata["seed"] == 12000
    assert sampled_metadata["sample_index"] == 12000
    assert sampled_metadata["head_hash4"] == head_hash4
    assert sampled_metadata["retry_number"] == 0
    assert sampled_metadata["sampled_owner_paths"] == _EXPECTED_SAMPLED_OWNER_PATHS
    assert all(path not in sampled_metadata["sampled_owner_paths"] for path in _RX_NON_SAMPLED_OWNER_PATHS)
    assert all(
        not path.startswith("modeled_objects.tx_outer_rect_void_coil.")
        for path in sampled_metadata["sampled_owner_paths"]
    )
    assert "design_id" not in sampled_metadata

    non_model_objects = cast(list[dict[str, object]], sampled_payload["non_model_objects"])
    tx_region_object = next(non_model for non_model in non_model_objects if non_model["id"] == "tx_region")
    tx_reference_line = cast(dict[str, object], tx_region_object["tx_reference_line"])
    tx_reference_line_x_range = cast(list[object], cast(dict[str, object], tx_reference_line["x_ratio"])["range"])
    assert tx_reference_line_x_range[0] is False
    assert tx_reference_line_x_range[3] == 1
    assert tx_reference_line_x_range[1] == tx_reference_line_x_range[2]
    assert tx_reference_line_x_range[1] == 0.99
    tx_reference_line_y_range = cast(
        list[object], cast(dict[str, object], tx_reference_line["y_usage_ratio"])["range"]
    )
    assert tx_reference_line_y_range[0] is False
    assert tx_reference_line_y_range[3] == 1
    assert tx_reference_line_y_range[1] == tx_reference_line_y_range[2]
    assert 0.2 <= float(cast(int | float, tx_reference_line_y_range[1])) <= 1.0
    tx_reference_line_z_range = cast(list[object], cast(dict[str, object], tx_reference_line["z_ratio"])["range"])
    assert tx_reference_line_z_range[0] is False
    assert tx_reference_line_z_range[3] == 1
    assert tx_reference_line_z_range[1] == tx_reference_line_z_range[2]
    assert 0.75 <= float(cast(int | float, tx_reference_line_z_range[1])) <= 1.0

    modeled_objects_by_id = {
        cast(str, modeled_object["object_id"]): modeled_object
        for modeled_object in cast(list[dict[str, object]], sampled_payload["modeled_objects"])
    }
    tx_inner_modeled_object = modeled_objects_by_id["tx_inner_rect_void_coil"]
    tx_inner_outer_y = cast(dict[str, object], tx_inner_modeled_object["outer_y_usage_ratio"])
    tx_inner_outer_y_range = cast(list[object], tx_inner_outer_y["range"])
    assert tx_inner_outer_y_range[0] is False
    assert tx_inner_outer_y_range[3] == 1
    assert tx_inner_outer_y_range[1] == tx_inner_outer_y_range[2]
    assert 0.2 <= float(cast(int | float, tx_inner_outer_y_range[1])) <= 0.9
    tx_inner_x_position = cast(dict[str, object], tx_inner_modeled_object["x_position_ratio"])
    tx_inner_x_position_range = cast(list[object], tx_inner_x_position["range"])
    assert tx_inner_x_position_range[0] is False
    assert tx_inner_x_position_range[3] == 1
    assert tx_inner_x_position_range[1] == tx_inner_x_position_range[2]
    assert tx_inner_x_position_range[1] == 0.0
    assert "tx_outer_x_position_ratio" not in tx_inner_modeled_object
    assert "tx_outer_terminal_path" not in tx_inner_modeled_object

    rx_modeled_object = modeled_objects_by_id["rx_rect_void_coil"]
    assert rx_modeled_object["object_id"] == "rx_rect_void_coil"
    assert rx_modeled_object["role"] == "rx_single_coil"
    assert rx_modeled_object["pcb_thickness_mm"] == 3.965
    assert rx_modeled_object["copper_thickness_mm"] == 0.035
    assert "ferrite_set_count" not in rx_modeled_object
    rx_outer_x = cast(dict[str, object], rx_modeled_object["outer_x_usage_ratio"])
    rx_outer_x_range = cast(list[object], rx_outer_x["range"])
    assert rx_outer_x_range[0] is False
    assert rx_outer_x_range[3] == 1
    assert rx_outer_x_range[1] == rx_outer_x_range[2]
    assert 0.1 <= float(cast(int | float, rx_outer_x_range[1])) <= 1.0
    rx_outer_y = cast(dict[str, object], rx_modeled_object["outer_y_usage_ratio"])
    rx_outer_y_range = cast(list[object], rx_outer_y["range"])
    assert rx_outer_y_range[0] is False
    assert rx_outer_y_range[3] == 1
    assert rx_outer_y_range[1] == rx_outer_y_range[2]
    assert 0.1 <= float(cast(int | float, rx_outer_y_range[1])) <= 1.0
    rx_void_ratio = cast(dict[str, object], rx_modeled_object["void_usage_ratio"])
    rx_void_ratio_range = cast(list[object], rx_void_ratio["range"])
    assert rx_void_ratio_range[0] is False
    assert rx_void_ratio_range[3] == 1
    assert rx_void_ratio_range[1] == rx_void_ratio_range[2]
    assert 0.1 <= float(cast(int | float, rx_void_ratio_range[1])) <= 0.6
    rx_turn = cast(dict[str, object], rx_modeled_object["turn_count"])
    rx_turn_range = cast(list[object], rx_turn["range"])
    assert rx_turn_range[0] is True
    assert rx_turn_range[3] == 1
    assert rx_turn_range[1] == rx_turn_range[2]
    assert rx_turn_range[1] in {2, 3, 4, 5}
    rx_underlay_repeat_count = cast(dict[str, object], rx_modeled_object["underlay_repeat_count"])
    rx_underlay_repeat_count_range = cast(list[object], rx_underlay_repeat_count["range"])
    assert rx_underlay_repeat_count_range[0] is True
    assert rx_underlay_repeat_count_range[3] == 1
    assert rx_underlay_repeat_count_range[1] == rx_underlay_repeat_count_range[2]
    assert rx_underlay_repeat_count_range[1] == 8
    rx_fill = cast(dict[str, object], rx_modeled_object["metal_fill_factor"])
    rx_fill_range = cast(list[object], rx_fill["range"])
    assert rx_fill_range[0] is False
    assert rx_fill_range[3] == 1
    assert rx_fill_range[1] == rx_fill_range[2]
    assert 0.2 <= float(cast(int | float, rx_fill_range[1])) <= 0.6
    assert "tx_coil_count" not in rx_modeled_object
    assert "tx_array_x_usage_ratio" not in rx_modeled_object
    rx_layer_count = cast(dict[str, object], rx_modeled_object["layer_count"])
    rx_layer_gap = cast(dict[str, object], rx_modeled_object["layer_gap_mm"])
    rx_terminal_stub = cast(dict[str, object], rx_modeled_object["terminal_stub_length_mm"])
    assert rx_layer_count["range"] == [True, 1, 1, 1]
    assert rx_layer_gap["range"] == [False, 2.0, 2.0, 1]
    assert rx_terminal_stub["range"] == [False, 5.0, 5.0, 1]
    assert "void_x_over_outer_x" not in rx_modeled_object
    assert "void_y_over_outer_y" not in rx_modeled_object
    assert "void_center_x_over_outer_x" not in rx_modeled_object
    assert "void_center_y_over_outer_y" not in rx_modeled_object
    rx_margin = cast(dict[str, object], rx_modeled_object["margin_ratio"])
    rx_terminal_path = cast(dict[str, object], rx_modeled_object["terminal_path"])
    assert rx_margin["range"] == [False, 0.05, 0.05, 1]
    assert rx_terminal_path["value"] == "A_cw_to_a"
    assert "z_usage_ratio" not in rx_modeled_object
    assert "y_usage_ratio" not in rx_modeled_object
    assert "pcb_total_thickness_mm" not in rx_modeled_object
    assert "underlay_gap_mm" not in rx_modeled_object

    resolved_entry = manifest_entry_for_sample_index(manifest_path, sample_index=12000)
    assert resolved_entry["design_id"] == first_entry["design_id"]
    with pytest.raises(ValueError, match=r"sample_index.*0"):
        manifest_entry_for_sample_index(manifest_path, sample_index=0)


def test_sample_type2_reports_step_skip_and_removes_partial_design_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_rx_only_spec_loader(monkeypatch)
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"
    skipped_seed = 5
    exporter_calls: list[int] = []

    def _exporter(**kwargs: object) -> object:
        seed = cast(int, kwargs["seed"])
        output_dir_arg = cast(Path, kwargs["output_dir"])
        stage_reporter = cast(Callable[[str], None], kwargs["stage_reporter"])
        stage_reporter("build_scene")
        exporter_calls.append(seed)
        if seed == skipped_seed:
            (output_dir_arg / "partial.txt").write_text("partial", encoding="utf-8")
            raise RuntimeError("simulated step validation failure")
        ledger_path = cast(Path, kwargs["ledger_path"])
        stage_reporter("export_scene_step")
        scene_step_path = output_dir_arg / "type2_scene.step"
        scene_step_path.write_text("STEP", encoding="utf-8")
        ledger_path.write_text(json.dumps({"scene_step_path": str(scene_step_path)}, indent=2), encoding="utf-8")
        stage_reporter("finalize_step_artifacts")

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

    assert document["skipped"] == [
        {
            "seed": skipped_seed,
            "sample_index": 5,
            "phase": "step",
            "error_type": "RuntimeError",
            "error_message": "simulated step validation failure",
        }
    ]
    assert [entry["seed"] for entry in document["entries"]] == [4, 6]
    assert [entry["sample_index"] for entry in document["entries"]] == [4, 6]
    assert "[sample] skip idx=5 seed=5 phase=step error=RuntimeError: simulated step validation failure" in captured.out
    assert "[sample] done count=2 skipped=1 attempted=3" in captured.out
    assert exporter_calls == [4, 5, 6]

    design_dir_paths = [Path(entry["design_dir"]) for entry in document["entries"]]
    assert all(design_dir_path.is_dir() for design_dir_path in design_dir_paths)

    on_disk_dirs = {entry.name for entry in output_dir.iterdir() if entry.is_dir()}
    assert on_disk_dirs == {Path(entry["design_dir"]).name for entry in document["entries"]}
    assert list(output_dir.rglob("partial.txt")) == []


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

    assert document["skipped"] == []
    assert patched_calls == [source_toml_path]
    assert [entry["seed"] for entry in document["entries"]] == [101, 102]
    assert [entry["sample_index"] for entry in document["entries"]] == [101, 102]
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

    assert manifest_entry_for_sample_index(manifest_path, sample_index=10)["sample_index"] == 10
    with pytest.raises(ValueError, match=r"sample_index.*0"):
        manifest_entry_for_sample_index(manifest_path, sample_index=0)
    with pytest.raises(ValueError, match=r"sample_index"):
        manifest_entry_for_sample_index(manifest_path, sample_index=2)


def test_manifest_entry_for_sample_index_indexes_successful_entries_with_skipped_attempts(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    entry_by_success_order = {
        "path_prefix": str(tmp_path / "run" / "sampled" / "type2"),
    }
    manifest_payload = {
        "config": {
            "source_toml_path": str((tmp_path / "source.toml").resolve(strict=False)),
            "seed_first": 4,
            "seed_n": 3,
            "sampler_n": 1,
            "make_step_on_sample": True,
            "aedt_builder_n": 6,
        },
        "entries": [
            {
                "design_id": "s000004_0000_abcd_0",
                "seed": 4,
                "sample_index": 4,
                "retry_number": 0,
                "source_toml_path": str((tmp_path / "source.toml").resolve(strict=False)),
                "sampled_toml_path": f"{entry_by_success_order['path_prefix']}/s000004_0000_abcd_0/sample_4.toml",
                "design_dir": f"{entry_by_success_order['path_prefix']}/s000004_0000_abcd_0",
                "scene_step_path": f"{entry_by_success_order['path_prefix']}/s000004_0000_abcd_0/type2_scene.step",
                "step_ledger_path": f"{entry_by_success_order['path_prefix']}/s000004_0000_abcd_0/type2_step_ledger.json",
                "imported_ledger_path": f"{entry_by_success_order['path_prefix']}/s000004_0000_abcd_0/type2_imported_ledger.json",
                "aedt_path": f"{entry_by_success_order['path_prefix']}/s000004_0000_abcd_0/s000004_0000_abcd_0.aedt",
                "sampled_owner_paths": ["non_model_objects.tx_region_actual.x_usage_ratio"],
            },
            {
                "design_id": "s000006_0000_abcd_0",
                "seed": 6,
                "sample_index": 6,
                "retry_number": 0,
                "source_toml_path": str((tmp_path / "source.toml").resolve(strict=False)),
                "sampled_toml_path": f"{entry_by_success_order['path_prefix']}/s000006_0000_abcd_0/sample_6.toml",
                "design_dir": f"{entry_by_success_order['path_prefix']}/s000006_0000_abcd_0",
                "scene_step_path": f"{entry_by_success_order['path_prefix']}/s000006_0000_abcd_0/type2_scene.step",
                "step_ledger_path": f"{entry_by_success_order['path_prefix']}/s000006_0000_abcd_0/type2_step_ledger.json",
                "imported_ledger_path": f"{entry_by_success_order['path_prefix']}/s000006_0000_abcd_0/type2_imported_ledger.json",
                "aedt_path": f"{entry_by_success_order['path_prefix']}/s000006_0000_abcd_0/s000006_0000_abcd_0.aedt",
                "sampled_owner_paths": ["non_model_objects.tx_region_actual.x_usage_ratio"],
            },
        ],
        "skipped": [
            {
                "seed": 5,
                "sample_index": 5,
                "phase": "step",
                "error_type": "ValueError",
                "error_message": "simulated step failure",
            }
        ],
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

    resolved_entry = manifest_entry_for_sample_index(manifest_path, sample_index=6)
    assert resolved_entry == manifest_payload["entries"][1]
    assert resolved_entry["seed"] == 6

    with pytest.raises(ValueError, match=r"sample_index"):
        manifest_entry_for_sample_index(manifest_path, sample_index=5)


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
        sampler_n=1,
        aedt_builder_n=6,
        make_step_on_sample=False,
        exporter=_exporter,
    )
    captured = capsys.readouterr()

    assert document["skipped"] == []
    assert document["config"] == {
        "source_toml_path": str(source_toml_path.resolve(strict=False)),
        "seed_first": 20,
        "seed_n": 2,
        "sampler_n": 1,
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
    return """
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
mode = "RxOnly"
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
[non_model_objects.tx_reference_line.x_ratio]
range = [false, 0.99, 0.99, 1]
[non_model_objects.tx_reference_line.y_usage_ratio]
range = [false, 0.2, 1.0, 17]
[non_model_objects.tx_reference_line.z_ratio]
range = [false, 0.5, 1.0, 13]

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
object_id = "rx_rect_void_coil"
role = "rx_single_coil"
material = "composite"
model_state = true
pcb_thickness_mm = 3.965
copper_thickness_mm = 0.035
[modeled_objects.outer_x_usage_ratio]
range = [false, 0.1, 0.6, 17]
[modeled_objects.outer_y_usage_ratio]
range = [false, 0.1, 0.6, 17]
[modeled_objects.x_position_ratio]
range = [false, 0.0, 0.0, 1]
[modeled_objects.void_usage_ratio]
range = [false, 0.1, 0.6, 17]
[modeled_objects.turn_count]
range = [true, 2, 5, 4]
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
[modeled_objects.equivalent_turn_count]
range = [false, 0.1111111111111111, 31.0, 100]
[modeled_objects.turn_weight_a]
range = [false, 0.5, 1.5, 5]
[modeled_objects.turn_weight_b]
range = [false, -0.5, 0.5, 21]
[modeled_objects.turn_weight_c]
range = [false, -0.3, 0.3, 21]
""".strip()


def test_sampled_owner_values_rejects_tx_rect_void_columns_modeled_owner(
    tmp_path: Path,
) -> None:
    source_toml_path = tmp_path / "type2_tx_rect_source.toml"
    source_toml_path.write_text(_source_type2_toml_text_with_tx_rect_void_columns(), encoding="utf-8")
    with pytest.raises(ValueError, match=r"unsupported in active RxOnly type2 mode"):
        load_type2_step_spec(source_toml_path)


def test_sample_type2_tx_rect_void_columns_sample_only_records_sample_skip(
    tmp_path: Path,
) -> None:
    source_toml_path = tmp_path / "type2_tx_rect_source.toml"
    source_toml_path.write_text(_source_type2_toml_text_with_tx_rect_void_columns(), encoding="utf-8")
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"
    with pytest.raises(ValueError, match=r"unsupported in active RxOnly type2 mode"):
        sample_type2(
            source_toml_path=source_toml_path,
            output_dir=output_dir,
            manifest_path=manifest_path,
            seed_first=11,
            seed_n=4,
            sampler_n=1,
            aedt_builder_n=1,
            make_step_on_sample=False,
        )

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tomllib
from typing import cast

import pytest

import entry.build as build_entry
import peetsfea.type2_sampled as type2_sampled
from entry.build import (
    _Type2BuildRunnerResult,
    _setup_type2_step_ledger_gui_debug,
    build_type2,
    build_type2_debug,
    run_build_cli,
)
from entry.sample import sample_type2
from peetsfea.type2_runtime import Type2BuiltArtifact
from peetsfea.type2_sampled import PreparedType2Build
from peetsfea.type2_step_spec import ModeledRxPlateStackSpec
from peetsfea.type2_step_spec import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec import RangeSpec

_PLATE_STACK_PCB_TOTAL_THICKNESS_MM = 0.4
_EXPECTED_SAMPLED_OWNER_PATHS = (
    "modeled_objects.tx_plate_stack.turn_count",
    "modeled_objects.tx_plate_stack.metal_fill_factor",
    "modeled_objects.tx_plate_stack.z_usage_ratio",
    "modeled_objects.tx_plate_stack.y_usage_ratio",
    "modeled_objects.tx_plate_stack.tx_coil_count",
    "modeled_objects.tx_plate_stack.tx_array_x_usage_ratio",
    "modeled_objects.rx_plate_stack.turn_count",
    "modeled_objects.rx_plate_stack.metal_fill_factor",
    "modeled_objects.rx_plate_stack.z_usage_ratio",
    "modeled_objects.rx_plate_stack.y_usage_ratio",
)
_EXPECTED_DESIGN_VARIABLE_NAMES = tuple(owner_path.replace(".", "_") for owner_path in _EXPECTED_SAMPLED_OWNER_PATHS)


def _expected_design_variables_for_sampled_toml(sampled_toml_path: Path) -> tuple[tuple[str, str], ...]:
    payload = tomllib.loads(sampled_toml_path.read_text(encoding="utf-8"))
    modeled_objects = cast(list[dict[str, object]], payload["modeled_objects"])
    modeled_by_id: dict[str, dict[str, object]] = {
        cast(str, modeled_object["object_id"]): modeled_object for modeled_object in modeled_objects
    }
    tx_turn_range = cast(list[object], cast(dict[str, object], modeled_by_id["tx_plate_stack"]["turn_count"])["range"])
    tx_fill_range = cast(
        list[object], cast(dict[str, object], modeled_by_id["tx_plate_stack"]["metal_fill_factor"])["range"]
    )
    tx_z_usage_ratio_range = cast(
        list[object], cast(dict[str, object], modeled_by_id["tx_plate_stack"]["z_usage_ratio"])["range"]
    )
    tx_y_usage_ratio_range = cast(
        list[object], cast(dict[str, object], modeled_by_id["tx_plate_stack"]["y_usage_ratio"])["range"]
    )
    tx_coil_count_range = cast(
        list[object], cast(dict[str, object], modeled_by_id["tx_plate_stack"]["tx_coil_count"])["range"]
    )
    tx_array_x_usage_ratio_range = cast(
        list[object], cast(dict[str, object], modeled_by_id["tx_plate_stack"]["tx_array_x_usage_ratio"])["range"]
    )
    rx_turn_range = cast(list[object], cast(dict[str, object], modeled_by_id["rx_plate_stack"]["turn_count"])["range"])
    rx_fill_range = cast(
        list[object], cast(dict[str, object], modeled_by_id["rx_plate_stack"]["metal_fill_factor"])["range"]
    )
    rx_z_usage_ratio_range = cast(
        list[object], cast(dict[str, object], modeled_by_id["rx_plate_stack"]["z_usage_ratio"])["range"]
    )
    rx_y_usage_ratio_range = cast(
        list[object], cast(dict[str, object], modeled_by_id["rx_plate_stack"]["y_usage_ratio"])["range"]
    )
    return (
        (_EXPECTED_DESIGN_VARIABLE_NAMES[0], str(int(cast(int | float, tx_turn_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[1], str(float(cast(int | float, tx_fill_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[2], str(float(cast(int | float, tx_z_usage_ratio_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[3], str(float(cast(int | float, tx_y_usage_ratio_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[4], str(int(cast(int | float, tx_coil_count_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[5], str(float(cast(int | float, tx_array_x_usage_ratio_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[6], str(int(cast(int | float, rx_turn_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[7], str(float(cast(int | float, rx_fill_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[8], str(float(cast(int | float, rx_z_usage_ratio_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[9], str(float(cast(int | float, rx_y_usage_ratio_range[1])))),
    )


@dataclass(frozen=True)
class _FakePlateStackType2Spec:
    modeled_objects: tuple[ModeledTxPlateStackSpec | ModeledRxPlateStackSpec, ...]


def _patch_plate_stack_spec_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    original_loader = type2_sampled.load_type2_step_spec
    tx_turn_count = RangeSpec(is_integer=True, start=3.0, end=5.0, count=3)
    tx_fill_factor = RangeSpec(is_integer=False, start=0.3, end=0.5, count=3)
    tx_z_usage_ratio = RangeSpec(is_integer=False, start=0.1, end=0.3, count=3)
    tx_y_usage_ratio = RangeSpec(is_integer=False, start=0.12, end=0.22, count=3)
    tx_coil_count = RangeSpec(is_integer=True, start=1.0, end=4.0, count=4)
    tx_array_x_usage_ratio = RangeSpec(is_integer=False, start=0.1, end=0.6, count=14)
    rx_turn_count = RangeSpec(is_integer=True, start=6.0, end=8.0, count=3)
    rx_fill_factor = RangeSpec(is_integer=False, start=0.4, end=0.6, count=3)
    rx_z_usage_ratio = RangeSpec(is_integer=False, start=0.2, end=0.4, count=3)
    rx_y_usage_ratio = RangeSpec(is_integer=False, start=0.18, end=0.28, count=3)
    fake_spec = _FakePlateStackType2Spec(
        modeled_objects=(
            ModeledTxPlateStackSpec(
                object_id="tx_plate_stack",
                role="tx_plate_stack",
                material="composite",
                model_state=True,
                pcb_total_thickness_mm=_PLATE_STACK_PCB_TOTAL_THICKNESS_MM,
                copper_thickness_mm=0.035,
                turn_count=tx_turn_count,
                metal_fill_factor=tx_fill_factor,
                z_usage_ratio=tx_z_usage_ratio,
                y_usage_ratio=tx_y_usage_ratio,
                tx_coil_count=tx_coil_count,
                tx_array_x_usage_ratio=tx_array_x_usage_ratio,
            ),
            ModeledRxPlateStackSpec(
                object_id="rx_plate_stack",
                role="rx_plate_stack",
                material="composite",
                model_state=True,
                pcb_total_thickness_mm=_PLATE_STACK_PCB_TOTAL_THICKNESS_MM,
                copper_thickness_mm=0.1,
                turn_count=rx_turn_count,
                metal_fill_factor=rx_fill_factor,
                z_usage_ratio=rx_z_usage_ratio,
                y_usage_ratio=rx_y_usage_ratio,
            ),
        )
    )

    def _patched_loader(toml_path: Path) -> object:
        if toml_path.name == "type2_sweep.toml":
            return fake_spec
        return original_loader(toml_path)

    monkeypatch.setattr(type2_sampled, "load_type2_step_spec", _patched_loader)


def _source_type2_toml_text() -> str:
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.type2.step.v4"
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

[[modeled_objects]]
    object_id = "tx_plate_stack"
    role = "tx_plate_stack"
    material = "composite"
    model_state = true
    pcb_total_thickness_mm = {_PLATE_STACK_PCB_TOTAL_THICKNESS_MM}
    copper_thickness_mm = 0.035
    [modeled_objects.turn_count]
    range = [true, 3, 5, 3]
    [modeled_objects.metal_fill_factor]
    range = [false, 0.3, 0.5, 3]
    [modeled_objects.z_usage_ratio]
    range = [false, 0.1, 0.3, 3]
[modeled_objects.y_usage_ratio]
range = [false, 0.12, 0.22, 3]
[modeled_objects.tx_coil_count]
range = [true, 1, 4, 4]
[modeled_objects.tx_array_x_usage_ratio]
range = [false, 0.1, 0.6, 14]

[[modeled_objects]]
    object_id = "rx_plate_stack"
    role = "rx_plate_stack"
    material = "composite"
    model_state = true
    pcb_total_thickness_mm = {_PLATE_STACK_PCB_TOTAL_THICKNESS_MM}
    copper_thickness_mm = 0.1
    [modeled_objects.turn_count]
    range = [true, 6, 8, 3]
    [modeled_objects.metal_fill_factor]
    range = [false, 0.4, 0.6, 3]
    [modeled_objects.z_usage_ratio]
    range = [false, 0.2, 0.4, 3]
    [modeled_objects.y_usage_ratio]
    range = [false, 0.18, 0.28, 3]
""".strip()


def _write_source_type2_toml(tmp_path: Path) -> Path:
    path = tmp_path / "type2_sweep.toml"
    path.write_text(_source_type2_toml_text(), encoding="utf-8")
    return path


def test_build_type2_reads_aedt_builder_n_from_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_plate_stack_spec_loader(monkeypatch)
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"

    sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=4,
        seed_n=2,
        sampler_n=1,
        aedt_builder_n=6,
        make_step_on_sample=False,
    )

    calls: list[dict[str, object]] = []

    def _fake_build_prepared_type2_designs(
        prepared_builds: tuple[PreparedType2Build, ...],
        *,
        jobs: int,
        exporter: object,
        runner: object,
    ) -> list[dict[str, str]]:
        calls.append(
            {
                "jobs": jobs,
                "build_count": len(prepared_builds),
                "modeled_roles": [tuple(prepared_build.modeled_roles) for prepared_build in prepared_builds],
                "design_variables": [tuple(prepared_build.design_variables) for prepared_build in prepared_builds],
                "sampled_toml_paths": [prepared_build.sampled_toml_path for prepared_build in prepared_builds],
                "exporter": exporter,
                "runner": runner,
            }
        )
        return []

    monkeypatch.setattr(build_entry, "build_prepared_type2_designs", _fake_build_prepared_type2_designs)
    results = build_type2(manifest_path=manifest_path)

    assert results == []
    assert len(calls) == 1
    assert calls[0]["jobs"] == 6
    assert calls[0]["build_count"] == 2
    assert calls[0]["modeled_roles"] == [("tx_plate_stack", "rx_plate_stack"), ("tx_plate_stack", "rx_plate_stack")]
    assert calls[0]["exporter"] is build_entry.export_type2_step_artifacts
    assert calls[0]["runner"] is build_entry.setup_type2_step_ledger
    design_variables_by_design = cast(list[tuple[tuple[str, str], ...]], calls[0]["design_variables"])
    sampled_toml_paths = cast(list[Path], calls[0]["sampled_toml_paths"])
    assert len(design_variables_by_design) == 2
    for index, design_variables in enumerate(design_variables_by_design):
        assert tuple(name for name, _ in design_variables) == _EXPECTED_DESIGN_VARIABLE_NAMES
        assert design_variables == _expected_design_variables_for_sampled_toml(sampled_toml_paths[index])


def test_build_type2_builds_plate_stack_manifest_with_setup_ready_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_plate_stack_spec_loader(monkeypatch)
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"

    sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=8,
        seed_n=1,
        sampler_n=1,
        aedt_builder_n=2,
        make_step_on_sample=False,
    )
    exporter_calls: list[dict[str, object]] = []
    setup_ready_calls: list[dict[str, object]] = []

    def _build_exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        output_dir = cast(Path, kwargs["output_dir"])
        ledger_path = cast(Path, kwargs["ledger_path"])
        scene_step_path = output_dir / "type2_scene.step"
        scene_step_path.write_text("STEP", encoding="utf-8")
        ledger_path.write_text(json.dumps({"scene_step_path": str(scene_step_path)}, indent=2), encoding="utf-8")
        return {"ok": True}

    def _setup_ready_runner(**kwargs: object) -> _Type2BuildRunnerResult:
        setup_ready_calls.append(dict(kwargs))
        step_ledger_path = cast(Path, kwargs["step_ledger_path"])
        output_aedt_path = cast(Path, kwargs["output_aedt_path"])
        imported_ledger_path = cast(Path, kwargs["imported_ledger_path"])
        return {
            "source_step_ledger_path": str(step_ledger_path),
            "aedt_path": str(output_aedt_path),
            "imported_ledger_path": str(imported_ledger_path),
        }

    results = build_type2(
        manifest_path=manifest_path,
        exporter=_build_exporter,
        runner=_setup_ready_runner,
    )

    assert len(results) == 1
    assert exporter_calls != []
    assert len(setup_ready_calls) == 1
    assert set(setup_ready_calls[0].keys()) == {
        "step_ledger_path",
        "output_aedt_path",
        "imported_ledger_path",
        "design_name",
        "design_variables",
    }
    assert cast(str, setup_ready_calls[0]["design_name"]) == results[0]["design_id"]
    design_variables = cast(tuple[tuple[str, str], ...], setup_ready_calls[0]["design_variables"])
    assert tuple(name for name, _ in design_variables) == _EXPECTED_DESIGN_VARIABLE_NAMES
    assert len(design_variables) == len(_EXPECTED_DESIGN_VARIABLE_NAMES)
    assert all(expression != "" for _, expression in design_variables)
    assert results[0]["aedt_path"] == str(cast(Path, setup_ready_calls[0]["output_aedt_path"]))
    assert results[0]["imported_ledger_path"] == str(cast(Path, setup_ready_calls[0]["imported_ledger_path"]))
    assert results[0]["source_step_ledger_path"] == str(cast(Path, setup_ready_calls[0]["step_ledger_path"]))


def test_build_type2_accepts_plate_stack_manifest_when_forced_to_setup_ready_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_plate_stack_spec_loader(monkeypatch)
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"

    sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=8,
        seed_n=1,
        sampler_n=1,
        aedt_builder_n=2,
        make_step_on_sample=False,
    )

    def _build_exporter(**kwargs: object) -> object:
        output_dir_arg = cast(Path, kwargs["output_dir"])
        ledger_path = cast(Path, kwargs["ledger_path"])
        scene_step_path = output_dir_arg / "type2_scene.step"
        scene_step_path.write_text("STEP", encoding="utf-8")
        ledger_path.write_text(json.dumps({"scene_step_path": str(scene_step_path)}, indent=2), encoding="utf-8")
        return {"ok": True}

    calls: list[dict[str, object]] = []

    def _runner(**kwargs: object) -> _Type2BuildRunnerResult:
        calls.append(dict(kwargs))
        step_ledger_path = cast(Path, kwargs["step_ledger_path"])
        output_aedt_path = cast(Path, kwargs["output_aedt_path"])
        imported_ledger_path = cast(Path, kwargs["imported_ledger_path"])
        return {
            "source_step_ledger_path": str(step_ledger_path),
            "aedt_path": str(output_aedt_path),
            "imported_ledger_path": str(imported_ledger_path),
        }

    results = build_type2(manifest_path=manifest_path, exporter=_build_exporter, runner=_runner)
    assert len(results) == 1
    assert len(calls) == 1
    assert set(calls[0].keys()) == {
        "step_ledger_path",
        "output_aedt_path",
        "imported_ledger_path",
        "design_name",
        "design_variables",
    }
    design_variables = cast(tuple[tuple[str, str], ...], calls[0]["design_variables"])
    assert tuple(name for name, _ in design_variables) == _EXPECTED_DESIGN_VARIABLE_NAMES
    assert len(design_variables) == len(_EXPECTED_DESIGN_VARIABLE_NAMES)
    assert all(expression != "" for _, expression in design_variables)


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
                    "make_step_on_sample": True,
                },
                "entries": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"type2 sample manifest config is missing required key 'aedt_builder_n'"):
        build_type2(manifest_path=manifest_path)


def test_build_type2_rejects_missing_make_step_on_sample_config(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "config": {
                    "source_toml_path": "/tmp/source.toml",
                    "seed_first": 0,
                    "seed_n": 1,
                    "sampler_n": 1,
                    "aedt_builder_n": 1,
                },
                "entries": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"type2 sample manifest config is missing required key 'make_step_on_sample'"):
        build_type2(manifest_path=manifest_path)


def test_build_type2_debug_builds_only_requested_design_with_single_job(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_plate_stack_spec_loader(monkeypatch)
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"

    sampled_manifest = sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=8,
        seed_n=2,
        sampler_n=1,
        aedt_builder_n=2,
        make_step_on_sample=False,
    )

    selected_design_id = sampled_manifest["entries"][1]["design_id"]
    captured: dict[str, object] = {}
    expected_result: list[Type2BuiltArtifact] = [
        {
            "design_id": selected_design_id,
            "sampled_toml_path": "sampled.toml",
            "aedt_path": "output.aedt",
            "source_step_ledger_path": "source.ledger",
            "imported_ledger_path": "imported.ledger",
        }
    ]

    def _fake_build_prepared_type2_designs(
        prepared_builds: tuple[PreparedType2Build, ...],
        *,
        jobs: int,
        exporter: object,
        runner: object,
    ) -> list[Type2BuiltArtifact]:
        captured["prepared_builds"] = prepared_builds
        captured["jobs"] = jobs
        captured["exporter"] = exporter
        captured["runner"] = runner
        return expected_result

    def fake_exporter(**kwargs: object) -> object:
        return kwargs

    def fake_runner(**kwargs: object) -> _Type2BuildRunnerResult:
        return {
            "aedt_path": str(kwargs["output_aedt_path"]),
            "source_step_ledger_path": str(kwargs["step_ledger_path"]),
            "imported_ledger_path": str(kwargs["imported_ledger_path"]),
        }

    monkeypatch.setattr(build_entry, "build_prepared_type2_designs", _fake_build_prepared_type2_designs)
    results = build_type2_debug(
        manifest_path=manifest_path,
        design_id=selected_design_id,
        exporter=fake_exporter,
        runner=fake_runner,
    )

    assert results is expected_result
    prepared_builds = cast(tuple[PreparedType2Build, ...], captured["prepared_builds"])
    assert len(prepared_builds) == 1
    assert prepared_builds[0].design_id == selected_design_id
    assert cast(int, captured["jobs"]) == 1
    assert captured["exporter"] is fake_exporter
    assert captured["runner"] is fake_runner


def test_setup_type2_step_ledger_gui_debug_uses_gui_visible_hfss(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class _FakeHfss:
        def __init__(self, *args: object, **kwargs: object) -> None:
            captured["hfss_kwargs"] = dict(kwargs)

    monkeypatch.setattr(build_entry, "Hfss", _FakeHfss)

    def _fake_setup(
        *,
        hfss: object,
        step_ledger_path: Path,
        output_aedt_path: Path,
        imported_ledger_path: Path,
        design_variables: tuple[tuple[str, str], ...],
    ) -> _Type2BuildRunnerResult:
        captured["runner_kwargs"] = {
            "hfss": hfss,
            "step_ledger_path": step_ledger_path,
            "output_aedt_path": output_aedt_path,
            "imported_ledger_path": imported_ledger_path,
            "design_variables": design_variables,
        }
        return {
            "aedt_path": str(output_aedt_path),
            "source_step_ledger_path": str(step_ledger_path),
            "imported_ledger_path": str(imported_ledger_path),
        }

    monkeypatch.setattr(build_entry, "setup_type2_step_ledger_into_hfss", _fake_setup)

    step_ledger_path = Path("/tmp/ledger.json")
    output_aedt_path = Path("/tmp/output.aedt")
    imported_ledger_path = Path("/tmp/imported.json")
    design_variables = (("var_x", "1"), ("var_y", "2"))
    design_name = "design-02"

    result = _setup_type2_step_ledger_gui_debug(
        step_ledger_path=step_ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        design_name=design_name,
        design_variables=design_variables,
    )

    hfss_kwargs = cast(dict[str, object], captured["hfss_kwargs"])
    assert hfss_kwargs["design"] == design_name
    assert hfss_kwargs["non_graphical"] is False
    assert hfss_kwargs["new_desktop"] is True
    assert hfss_kwargs["close_on_exit"] is False

    runner_kwargs = cast(dict[str, object], captured["runner_kwargs"])
    assert isinstance(runner_kwargs["hfss"], _FakeHfss)
    assert runner_kwargs["step_ledger_path"] == step_ledger_path
    assert runner_kwargs["output_aedt_path"] == output_aedt_path
    assert runner_kwargs["imported_ledger_path"] == imported_ledger_path
    assert runner_kwargs["design_variables"] == design_variables
    assert result == {
        "aedt_path": str(output_aedt_path),
        "source_step_ledger_path": str(step_ledger_path),
        "imported_ledger_path": str(imported_ledger_path),
    }


def test_run_build_cli_rejects_debug_without_design_id(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit):
        run_build_cli(("--debug", "--manifest", str(manifest_path)))


def test_run_build_cli_rejects_design_id_without_debug(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit):
        run_build_cli(("--manifest", str(manifest_path), "--design-id", "abc"))

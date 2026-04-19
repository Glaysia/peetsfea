from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tomllib
from typing import cast

import pytest

import entry.build as build_entry
import peetsfea.type2_sampled as type2_sampled
from entry.build import _Type2BuildRunnerResult, build_type2
from entry.sample import sample_type2
from peetsfea.type2_sampled import PreparedType2Build
from peetsfea.type2_step_spec import RangeSpec

_PLATE_STACK_PCB_TOTAL_THICKNESS_MM = 0.4
_EXPECTED_SAMPLED_OWNER_PATHS = (
    "modeled_objects.tx_plate_stack.turn_count",
    "modeled_objects.tx_plate_stack.metal_fill_factor",
    "modeled_objects.rx_plate_stack.turn_count",
    "modeled_objects.rx_plate_stack.metal_fill_factor",
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
    rx_turn_range = cast(list[object], cast(dict[str, object], modeled_by_id["rx_plate_stack"]["turn_count"])["range"])
    rx_fill_range = cast(
        list[object], cast(dict[str, object], modeled_by_id["rx_plate_stack"]["metal_fill_factor"])["range"]
    )
    return (
        (_EXPECTED_DESIGN_VARIABLE_NAMES[0], str(int(cast(int | float, tx_turn_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[1], str(float(cast(int | float, tx_fill_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[2], str(int(cast(int | float, rx_turn_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[3], str(float(cast(int | float, rx_fill_range[1])))),
    )


@dataclass(frozen=True)
class _FakePlateStackModeledSpec:
    object_id: str
    role: str
    turn_count: RangeSpec
    metal_fill_factor: RangeSpec


@dataclass(frozen=True)
class _FakePlateStackType2Spec:
    modeled_objects: tuple[_FakePlateStackModeledSpec, ...]


def _patch_plate_stack_spec_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    original_loader = type2_sampled.load_type2_step_spec
    tx_turn_count = RangeSpec(is_integer=True, start=3.0, end=5.0, count=3)
    tx_fill_factor = RangeSpec(is_integer=False, start=0.3, end=0.5, count=3)
    rx_turn_count = RangeSpec(is_integer=True, start=6.0, end=8.0, count=3)
    rx_fill_factor = RangeSpec(is_integer=False, start=0.4, end=0.6, count=3)
    fake_spec = _FakePlateStackType2Spec(
        modeled_objects=(
            _FakePlateStackModeledSpec(
                object_id="tx_plate_stack",
                role="tx_plate_stack",
                turn_count=tx_turn_count,
                metal_fill_factor=tx_fill_factor,
            ),
            _FakePlateStackModeledSpec(
                object_id="rx_plate_stack",
                role="rx_plate_stack",
                turn_count=rx_turn_count,
                metal_fill_factor=rx_fill_factor,
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
schema_id = "peetsfea.type2.step.v2"
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
ferrite_set_count = 10
[modeled_objects.turn_count]
range = [true, 3, 5, 3]
[modeled_objects.metal_fill_factor]
range = [false, 0.3, 0.5, 3]

[[modeled_objects]]
object_id = "rx_plate_stack"
role = "rx_plate_stack"
material = "composite"
model_state = true
pcb_total_thickness_mm = {_PLATE_STACK_PCB_TOTAL_THICKNESS_MM}
copper_thickness_mm = 0.1
ferrite_set_count = 10
[modeled_objects.turn_count]
range = [true, 6, 8, 3]
[modeled_objects.metal_fill_factor]
range = [false, 0.4, 0.6, 3]
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
    assert len(design_variables) == 4
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
    assert len(design_variables) == 4
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

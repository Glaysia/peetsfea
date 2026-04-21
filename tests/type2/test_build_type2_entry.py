from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
import tomllib
from typing import cast

import pytest

import entry.build as build_entry
import peetsfea.type2_sampled as type2_sampled
import peetsfea.type2_runtime as type2_runtime
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
from peetsfea.type2_step_spec import NonModelTxRegionActualSpec
from peetsfea.type2_step_spec import NonModelTxRegionActualStackSpaceSpec
from peetsfea.type2_step_spec import ModeledRxSingleCoilSpec
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import load_type2_step_spec

_EXPECTED_SAMPLED_OWNER_PATHS = (
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
)
_RX_NON_SAMPLED_OWNER_PATHS = (
    "modeled_objects.rx_rect_void_coil.layer_count",
    "modeled_objects.rx_rect_void_coil.underlay_repeat_count",
)
_RX_NON_SAMPLED_VARIABLE_NAMES = tuple(owner_path.replace(".", "_") for owner_path in _RX_NON_SAMPLED_OWNER_PATHS)
_EXPECTED_DESIGN_VARIABLE_NAMES = tuple(owner_path.replace(".", "_") for owner_path in _EXPECTED_SAMPLED_OWNER_PATHS)
_BuildExporter = Callable[..., object]
_BuildRunner = Callable[..., _Type2BuildRunnerResult]


def _expected_design_variables_for_sampled_toml(sampled_toml_path: Path) -> tuple[tuple[str, str], ...]:
    payload = tomllib.loads(sampled_toml_path.read_text(encoding="utf-8"))
    non_model_objects = cast(list[dict[str, object]], payload["non_model_objects"])
    non_model_by_id: dict[str, dict[str, object]] = {
        cast(str, non_model_object["id"]): non_model_object for non_model_object in non_model_objects
    }
    modeled_objects = cast(list[dict[str, object]], payload["modeled_objects"])
    modeled_by_id: dict[str, dict[str, object]] = {
        cast(str, modeled_object["object_id"]): modeled_object for modeled_object in modeled_objects
    }
    tx_region_actual_x_range = cast(
        list[object], cast(dict[str, object], non_model_by_id["tx_region_actual"]["x_usage_ratio"])["range"]
    )
    tx_region_actual_y_range = cast(
        list[object], cast(dict[str, object], non_model_by_id["tx_region_actual"]["y_usage_ratio"])["range"]
    )
    tx_region_actual_x_division_range = cast(
        list[object], cast(dict[str, object], non_model_by_id["tx_region_actual"]["x_division_count"])["range"]
    )
    tx_region_actual_y_division_range = cast(
        list[object], cast(dict[str, object], non_model_by_id["tx_region_actual"]["y_division_count"])["range"]
    )
    tx_region_actual_stack_space_scale_ratio_range = cast(
        list[object], cast(dict[str, object], non_model_by_id["tx_region_actual_stack_space"]["scale_ratio"])["range"]
    )
    rx_outer_x_range = cast(
        list[object], cast(dict[str, object], modeled_by_id["rx_rect_void_coil"]["outer_x_usage_ratio"])["range"]
    )
    rx_outer_y_range = cast(
        list[object], cast(dict[str, object], modeled_by_id["rx_rect_void_coil"]["outer_y_usage_ratio"])["range"]
    )
    rx_void_ratio_range = cast(
        list[object], cast(dict[str, object], modeled_by_id["rx_rect_void_coil"]["void_usage_ratio"])["range"]
    )
    rx_turn_range = cast(
        list[object], cast(dict[str, object], modeled_by_id["rx_rect_void_coil"]["turn_count"])["range"]
    )
    rx_fill_range = cast(
        list[object], cast(dict[str, object], modeled_by_id["rx_rect_void_coil"]["metal_fill_factor"])["range"]
    )
    return (
        (_EXPECTED_DESIGN_VARIABLE_NAMES[0], str(float(cast(int | float, tx_region_actual_x_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[1], str(float(cast(int | float, tx_region_actual_y_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[2], str(int(cast(int | float, tx_region_actual_x_division_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[3], str(int(cast(int | float, tx_region_actual_y_division_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[4], str(float(cast(int | float, tx_region_actual_stack_space_scale_ratio_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[5], str(float(cast(int | float, rx_outer_x_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[6], str(float(cast(int | float, rx_outer_y_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[7], str(float(cast(int | float, rx_void_ratio_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[8], str(int(cast(int | float, rx_turn_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[9], str(float(cast(int | float, rx_fill_range[1])))),
    )


@dataclass(frozen=True)
class _FakeRxOnlyType2Spec:
    non_model_derived_objects: tuple[NonModelTxRegionActualSpec | NonModelTxRegionActualStackSpaceSpec, ...]
    modeled_objects: tuple[ModeledRxSingleCoilSpec, ...]


def _patch_rx_only_spec_loader(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_load_type2_step_spec_accepts_tx_rect_void_columns_for_parser_sampler_milestone(tmp_path: Path) -> None:
    source_toml_path = tmp_path / "type2_tx_rect_source.toml"
    source_toml_path.write_text(
        """
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
range = [false, 0.2, 0.2, 1]
[modeled_objects.margin_ratio]
range = [false, 0.05, 0.05, 1]
[modeled_objects.metal_fill_factor]
range = [false, 0.5, 0.5, 1]
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
[modeled_objects.terminal_path]
value = "A_cw_to_a"
""".strip(),
        encoding="utf-8",
    )
    spec = load_type2_step_spec(source_toml_path)
    assert len(spec.modeled_objects) == 1
    assert spec.modeled_objects[0].role == "tx_rect_void_columns"


def test_load_type2_step_spec_from_examples_has_two_modeled_objects() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    for example_name in ("type2_sweep.toml", "type2_fixed.toml"):
        source_toml_path = repo_root / "examples" / example_name
        spec = load_type2_step_spec(source_toml_path)
        assert len(spec.modeled_objects) == 2
        assert {modeled_object.role for modeled_object in spec.modeled_objects} == {
            "rx_single_coil",
            "tx_rect_void_columns",
        }


def test_build_type2_reads_aedt_builder_n_from_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_rx_only_spec_loader(monkeypatch)
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
    assert calls[0]["modeled_roles"] == [("rx_single_coil",), ("rx_single_coil",)]
    assert calls[0]["exporter"] is build_entry.export_type2_step_artifacts
    assert calls[0]["runner"] is build_entry.setup_type2_step_ledger
    design_variables_by_design = cast(list[tuple[tuple[str, str], ...]], calls[0]["design_variables"])
    sampled_toml_paths = cast(list[Path], calls[0]["sampled_toml_paths"])
    assert len(design_variables_by_design) == 2
    for index, design_variables in enumerate(design_variables_by_design):
        assert tuple(name for name, _ in design_variables) == _EXPECTED_DESIGN_VARIABLE_NAMES
        assert design_variables == _expected_design_variables_for_sampled_toml(sampled_toml_paths[index])
        assert all(name not in tuple(name for name, _ in design_variables) for name in _RX_NON_SAMPLED_VARIABLE_NAMES)


def test_build_type2_forwards_manifest_path_and_selected_ids_to_prepared_builds_from_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "config": {
                    "source_toml_path": "/tmp/type2_source.toml",
                    "seed_first": 10,
                    "seed_n": 1,
                    "sampler_n": 1,
                    "make_step_on_sample": True,
                    "aedt_builder_n": 7,
                },
                "entries": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    source_toml_path = tmp_path / "source.toml"
    source_toml_path.write_text("[design]\n", encoding="utf-8")
    sampled_toml_path = tmp_path / "sampled.toml"
    sampled_toml_path.write_text("[sampled]\n", encoding="utf-8")
    design_dir = tmp_path / "design-compat"
    design_dir.mkdir()
    scene_step_path = design_dir / "type2_scene.step"
    scene_step_path.write_text("STEP", encoding="utf-8")
    step_ledger_path = design_dir / "type2_step_ledger.json"
    step_ledger_path.write_text(json.dumps({"scene_step_path": str(scene_step_path)}, indent=2), encoding="utf-8")
    imported_ledger_path = design_dir / "type2_imported_ledger.json"
    prepared_build = PreparedType2Build(
        design_id="design-compat",
        seed=10,
        source_toml_path=source_toml_path,
        sampled_toml_path=sampled_toml_path,
        design_dir=design_dir,
        scene_step_path=scene_step_path,
        step_ledger_path=step_ledger_path,
        imported_ledger_path=imported_ledger_path,
        aedt_path=design_dir / "design-compat.aedt",
        sampled_owner_paths=("modeled_objects.rx_rect_void_coil.outer_x_usage_ratio",),
        modeled_roles=("rx_single_coil",),
        design_variables=(("rx_outer_x_usage_ratio", "0.5"),),
    )

    calls: dict[str, object] = {}

    def _fake_prepared_builds_from_manifest(
        manifest_path_arg: Path,
        selected_design_ids: tuple[str, ...],
    ) -> tuple[PreparedType2Build, ...]:
        calls["manifest_path"] = manifest_path_arg
        calls["selected_design_ids"] = selected_design_ids
        return (prepared_build,)

    def _fake_build_prepared_type2_designs(
        prepared_builds: tuple[PreparedType2Build, ...],
        *,
        jobs: int,
        exporter: object,
        runner: object,
    ) -> list[Type2BuiltArtifact]:
        calls["jobs"] = jobs
        assert len(prepared_builds) == 1
        prepared = prepared_builds[0]
        return [
            {
                "design_id": prepared.design_id,
                "sampled_toml_path": str(prepared.sampled_toml_path),
                "aedt_path": str(prepared.aedt_path),
                "source_step_ledger_path": str(prepared.step_ledger_path),
                "imported_ledger_path": str(prepared.imported_ledger_path),
            }
        ]

    monkeypatch.setattr(build_entry, "prepared_builds_from_manifest", _fake_prepared_builds_from_manifest)
    monkeypatch.setattr(type2_sampled, "prepared_builds_from_manifest", _fake_prepared_builds_from_manifest)
    monkeypatch.setattr(build_entry, "build_prepared_type2_designs", _fake_build_prepared_type2_designs)

    results = build_type2(manifest_path=manifest_path)

    assert calls["manifest_path"] == manifest_path
    assert calls["selected_design_ids"] == tuple()
    assert calls["jobs"] == 7
    assert len(results) == 1
    assert results[0]["design_id"] == prepared_build.design_id


def test_build_type2_builds_plate_stack_manifest_with_setup_ready_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_rx_only_spec_loader(monkeypatch)
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

    def _fake_build_prepared_type2_designs(
        prepared_builds: tuple[PreparedType2Build, ...],
        *,
        jobs: int,
        exporter: object,
        runner: object,
    ) -> list[Type2BuiltArtifact]:
        assert jobs == 2
        assert len(prepared_builds) == 1
        prepared_build = prepared_builds[0]
        design_dir = prepared_build.design_dir
        source_step_ledger_path = design_dir / "type2_source_step_ledger.json"
        imported_ledger_path = design_dir / "type2_imported_ledger.json"
        output_aedt_path = design_dir / f"{prepared_build.design_id}.aedt"
        cast(_BuildExporter, exporter)(
            output_dir=design_dir,
            ledger_path=source_step_ledger_path,
        )
        runner_result = cast(_BuildRunner, runner)(
            step_ledger_path=source_step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            design_name=prepared_build.design_id,
            design_variables=prepared_build.design_variables,
        )
        return [
            {
                "design_id": prepared_build.design_id,
                "sampled_toml_path": str(prepared_build.sampled_toml_path),
                "aedt_path": cast(str, cast(dict[str, object], runner_result)["aedt_path"]),
                "source_step_ledger_path": cast(
                    str, cast(dict[str, object], runner_result)["source_step_ledger_path"]
                ),
                "imported_ledger_path": cast(str, cast(dict[str, object], runner_result)["imported_ledger_path"]),
            }
        ]

    monkeypatch.setattr(build_entry, "build_prepared_type2_designs", _fake_build_prepared_type2_designs)
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
    assert all(name not in tuple(name for name, _ in design_variables) for name in _RX_NON_SAMPLED_VARIABLE_NAMES)
    assert all(expression != "" for _, expression in design_variables)
    assert results[0]["aedt_path"] == str(cast(Path, setup_ready_calls[0]["output_aedt_path"]))
    assert results[0]["imported_ledger_path"] == str(cast(Path, setup_ready_calls[0]["imported_ledger_path"]))
    assert results[0]["source_step_ledger_path"] == str(cast(Path, setup_ready_calls[0]["step_ledger_path"]))


def test_build_type2_accepts_plate_stack_manifest_when_forced_to_setup_ready_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_rx_only_spec_loader(monkeypatch)
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

    def _fake_build_prepared_type2_designs(
        prepared_builds: tuple[PreparedType2Build, ...],
        *,
        jobs: int,
        exporter: object,
        runner: object,
    ) -> list[Type2BuiltArtifact]:
        assert jobs == 2
        assert len(prepared_builds) == 1
        prepared_build = prepared_builds[0]
        design_dir = prepared_build.design_dir
        source_step_ledger_path = design_dir / "type2_source_step_ledger.json"
        imported_ledger_path = design_dir / "type2_imported_ledger.json"
        output_aedt_path = design_dir / f"{prepared_build.design_id}.aedt"
        cast(_BuildExporter, exporter)(
            output_dir=design_dir,
            ledger_path=source_step_ledger_path,
        )
        runner_result = cast(_BuildRunner, runner)(
            step_ledger_path=source_step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            design_name=prepared_build.design_id,
            design_variables=prepared_build.design_variables,
        )
        return [
            {
                "design_id": prepared_build.design_id,
                "sampled_toml_path": str(prepared_build.sampled_toml_path),
                "aedt_path": cast(str, cast(dict[str, object], runner_result)["aedt_path"]),
                "source_step_ledger_path": cast(
                    str, cast(dict[str, object], runner_result)["source_step_ledger_path"]
                ),
                "imported_ledger_path": cast(str, cast(dict[str, object], runner_result)["imported_ledger_path"]),
            }
        ]

    monkeypatch.setattr(build_entry, "build_prepared_type2_designs", _fake_build_prepared_type2_designs)
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
    assert all(name not in tuple(name for name, _ in design_variables) for name in _RX_NON_SAMPLED_VARIABLE_NAMES)
    assert all(expression != "" for _, expression in design_variables)


def test_build_prepared_type2_design_accepts_existing_rx_only_step_ledger(tmp_path: Path) -> None:
    design_id = "design-rx"
    design_dir = tmp_path / design_id
    design_dir.mkdir()
    sampled_toml_path = design_dir / "sampled.toml"
    sampled_toml_path.write_text("[sampled]\n", encoding="utf-8")
    source_toml_path = tmp_path / "source.toml"
    source_toml_path.write_text("[design]\n", encoding="utf-8")
    scene_step_path = design_dir / "type2_scene.step"
    scene_step_path.write_text("STEP", encoding="utf-8")
    step_ledger_path = design_dir / "type2_step_ledger.json"
    step_ledger_path.write_text(json.dumps({"scene_step_path": str(scene_step_path)}, indent=2), encoding="utf-8")
    output_aedt_path = design_dir / f"{design_id}.aedt"
    imported_ledger_path = design_dir / "type2_imported_ledger.json"
    design_variables = (("rx_outer_x_usage_ratio", "0.5"), ("rx_outer_y_usage_ratio", "0.6"))
    prepared_build = PreparedType2Build(
        design_id=design_id,
        seed=1,
        source_toml_path=source_toml_path,
        sampled_toml_path=sampled_toml_path,
        design_dir=design_dir,
        scene_step_path=scene_step_path,
        step_ledger_path=step_ledger_path,
        imported_ledger_path=imported_ledger_path,
        aedt_path=output_aedt_path,
        sampled_owner_paths=("modeled_objects.rx_rect_void_coil.outer_x_usage_ratio",),
        modeled_roles=("rx_single_coil",),
        design_variables=design_variables,
    )

    exporter_calls: list[dict[str, object]] = []
    runner_calls: list[dict[str, object]] = []

    def _fake_exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        return {"ok": True}

    def _fake_runner(**kwargs: object) -> _Type2BuildRunnerResult:
        runner_calls.append(dict(kwargs))
        return {
            "aedt_path": str(cast(Path, kwargs["output_aedt_path"])),
            "source_step_ledger_path": str(cast(Path, kwargs["step_ledger_path"])),
            "imported_ledger_path": str(cast(Path, kwargs["imported_ledger_path"])),
        }

    results = type2_runtime.build_prepared_type2_design(
        prepared_build,
        exporter=_fake_exporter,
        runner=_fake_runner,
    )

    assert results["design_id"] == design_id
    assert results["sampled_toml_path"] == str(sampled_toml_path)
    assert results["aedt_path"] == str(output_aedt_path)
    assert results["source_step_ledger_path"] == str(step_ledger_path)
    assert results["imported_ledger_path"] == str(imported_ledger_path)
    assert exporter_calls == []
    assert len(runner_calls) == 1
    assert cast(tuple[tuple[str, str], ...], runner_calls[0]["design_variables"]) == design_variables
    assert runner_calls[0]["step_ledger_path"] == step_ledger_path
    assert runner_calls[0]["output_aedt_path"] == output_aedt_path
    assert runner_calls[0]["imported_ledger_path"] == imported_ledger_path


def test_build_prepared_type2_design_rejects_tx_only_modeled_role_before_runner(tmp_path: Path) -> None:
    design_id = "design-tx"
    design_dir = tmp_path / design_id
    design_dir.mkdir()
    sampled_toml_path = design_dir / "sampled.toml"
    sampled_toml_path.write_text("[sampled]\n", encoding="utf-8")
    source_toml_path = tmp_path / "source.toml"
    source_toml_path.write_text("[design]\n", encoding="utf-8")
    scene_step_path = design_dir / "type2_scene.step"
    scene_step_path.write_text("STEP", encoding="utf-8")
    step_ledger_path = design_dir / "type2_step_ledger.json"
    step_ledger_path.write_text(json.dumps({"scene_step_path": str(scene_step_path)}, indent=2), encoding="utf-8")
    output_aedt_path = design_dir / f"{design_id}.aedt"
    imported_ledger_path = design_dir / "type2_imported_ledger.json"
    prepared_build = PreparedType2Build(
        design_id=design_id,
        seed=1,
        source_toml_path=source_toml_path,
        sampled_toml_path=sampled_toml_path,
        design_dir=design_dir,
        scene_step_path=scene_step_path,
        step_ledger_path=step_ledger_path,
        imported_ledger_path=imported_ledger_path,
        aedt_path=output_aedt_path,
        sampled_owner_paths=("modeled_objects.tx_single_coil.outer_x_usage_ratio",),
        modeled_roles=("tx_single_coil",),
        design_variables=(("tx_outer_x_usage_ratio", "0.5"), ("tx_outer_y_usage_ratio", "0.6")),
    )

    runner_calls: list[dict[str, object]] = []

    def _fake_runner(**kwargs: object) -> _Type2BuildRunnerResult:
        runner_calls.append(dict(kwargs))
        return {
            "aedt_path": str(cast(Path, kwargs["output_aedt_path"])),
            "source_step_ledger_path": str(cast(Path, kwargs["step_ledger_path"])),
            "imported_ledger_path": str(cast(Path, kwargs["imported_ledger_path"])),
        }

    with pytest.raises(ValueError, match=r"type2 build/setup-ready rejects unsupported modeled roles"):
        type2_runtime.build_prepared_type2_design(prepared_build, runner=_fake_runner)

    assert runner_calls == []


def test_build_prepared_type2_design_rejects_tx_rect_void_columns_modeled_role_with_clear_message(tmp_path: Path) -> None:
    design_id = "design-tx-columns"
    design_dir = tmp_path / design_id
    design_dir.mkdir()
    sampled_toml_path = design_dir / "sampled.toml"
    sampled_toml_path.write_text("[sampled]\n", encoding="utf-8")
    source_toml_path = tmp_path / "source.toml"
    source_toml_path.write_text("[design]\n", encoding="utf-8")
    scene_step_path = design_dir / "type2_scene.step"
    scene_step_path.write_text("STEP", encoding="utf-8")
    step_ledger_path = design_dir / "type2_step_ledger.json"
    step_ledger_path.write_text(
        json.dumps({"scene_step_path": str(scene_step_path)}, indent=2),
        encoding="utf-8",
    )
    output_aedt_path = design_dir / f"{design_id}.aedt"
    imported_ledger_path = design_dir / "type2_imported_ledger.json"
    prepared_build = PreparedType2Build(
        design_id=design_id,
        seed=1,
        source_toml_path=source_toml_path,
        sampled_toml_path=sampled_toml_path,
        design_dir=design_dir,
        scene_step_path=scene_step_path,
        step_ledger_path=step_ledger_path,
        imported_ledger_path=imported_ledger_path,
        aedt_path=output_aedt_path,
        sampled_owner_paths=(
            "modeled_objects.tx_rect_void_columns.equivalent_turn_count",
        ),
        modeled_roles=("tx_rect_void_columns",),
        design_variables=(
            ("non_model_objects_tx_region_actual_stack_space_scale_ratio", "0.6"),
            ("modeled_objects_tx_rect_void_columns_equivalent_turn_count", "3.0"),
        ),
    )

    runner_calls: list[dict[str, object]] = []
    exporter_calls: list[dict[str, object]] = []

    def _fake_exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        return {"ok": True}

    def _fake_runner(**kwargs: object) -> _Type2BuildRunnerResult:
        runner_calls.append(dict(kwargs))
        return {
            "aedt_path": str(cast(Path, kwargs["output_aedt_path"])),
            "source_step_ledger_path": str(cast(Path, kwargs["step_ledger_path"])),
            "imported_ledger_path": str(cast(Path, kwargs["imported_ledger_path"])),
        }

    with pytest.raises(
        ValueError,
        match=r"parser/sampler-only milestone.*role is deactivated for active type2 inputs: tx_rect_void_columns",
    ):
        type2_runtime.build_prepared_type2_design(
            prepared_build,
            exporter=_fake_exporter,
            runner=_fake_runner,
        )

    assert runner_calls == []
    assert exporter_calls == []


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
    _patch_rx_only_spec_loader(monkeypatch)
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

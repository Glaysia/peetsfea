from __future__ import annotations

from collections.abc import Callable, Iterable
from concurrent.futures import Future
from dataclasses import dataclass
import json
from pathlib import Path
from queue import Queue as LocalQueue
import tomllib
from typing import Any, cast

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
    solve_type2,
)
from entry.sample import sample_type2
from peetsfea.type2_runtime import Type2BuiltArtifact
from peetsfea.type2_runtime import Type2AedtWorkerProcessError
from peetsfea.type2_sampled import PreparedType2Build
from peetsfea.type2_step_spec import NonModelTxRegionActualSpec
from peetsfea.type2_step_spec import NonModelTxRegionActualStackSpaceSpec
from peetsfea.type2_step_spec import NonModelTxReferenceLineSpec
from peetsfea.type2_step_spec import NonModelTxRegionSpec
from peetsfea.type2_step_spec import ModeledRxSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import load_type2_step_spec

_EXPECTED_SAMPLED_OWNER_PATHS = (
    "non_model_objects.tx_region.tx_reference_line.y_usage_ratio",
    "non_model_objects.tx_region.tx_reference_line.z_ratio",
    "modeled_objects.tx_inner_rect_void_coil.void_stack_present",
    "modeled_objects.rx_rect_void_coil.outer_x_usage_ratio",
    "modeled_objects.rx_rect_void_coil.outer_y_usage_ratio",
    "modeled_objects.rx_rect_void_coil.void_usage_ratio",
    "modeled_objects.rx_rect_void_coil.turn_count",
    "modeled_objects.rx_rect_void_coil.metal_fill_factor",
    "modeled_objects.tv_aluminum_plate.sheet_present",
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
    tx_reference_line = cast(dict[str, object], non_model_by_id["tx_region"]["tx_reference_line"])
    tx_reference_line_y_range = cast(
        list[object], cast(dict[str, object], tx_reference_line["y_usage_ratio"])["range"]
    )
    tx_reference_line_z_range = cast(list[object], cast(dict[str, object], tx_reference_line["z_ratio"])["range"])
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
    tx_inner_void_stack_present_range = cast(
        list[object],
        cast(dict[str, object], modeled_by_id["tx_inner_rect_void_coil"]["void_stack_present"])["range"],
    )
    tv_aluminum_sheet_present_range = cast(
        list[object],
        cast(dict[str, object], modeled_by_id["tv_aluminum_plate"]["sheet_present"])["range"],
    )
    return (
        (_EXPECTED_DESIGN_VARIABLE_NAMES[0], str(float(cast(int | float, tx_reference_line_y_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[1], str(float(cast(int | float, tx_reference_line_z_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[2], str(int(cast(int | float, tx_inner_void_stack_present_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[3], str(float(cast(int | float, rx_outer_x_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[4], str(float(cast(int | float, rx_outer_y_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[5], str(float(cast(int | float, rx_void_ratio_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[6], str(int(cast(int | float, rx_turn_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[7], str(float(cast(int | float, rx_fill_range[1])))),
        (_EXPECTED_DESIGN_VARIABLE_NAMES[8], str(int(cast(int | float, tv_aluminum_sheet_present_range[1])))),
    )


@dataclass(frozen=True)
class _FakeTvAluminumPlateSpec:
    object_id: str
    role: str
    primitive: str
    material: str
    model_state: bool
    source_non_model_object_id: str
    face: str
    thickness_mm: float
    sheet_present: RangeSpec


@dataclass(frozen=True)
class _FakeRxOnlyType2Spec:
    non_model_objects: tuple[NonModelTxRegionSpec, ...]
    non_model_derived_objects: tuple[NonModelTxRegionActualSpec | NonModelTxRegionActualStackSpaceSpec, ...]
    modeled_objects: tuple[ModeledTxInnerSingleCoilSpec | ModeledRxSingleCoilSpec | _FakeTvAluminumPlateSpec, ...]


def _patch_rx_only_spec_loader(monkeypatch: pytest.MonkeyPatch) -> None:
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
                origin_xyz=(0.0, -600.0, 0.0),
                size_xyz=(720.0, 1200.0, 90.0),
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
                outer_y_usage_ratio=RangeSpec(is_integer=False, start=0.6, end=0.6, count=1),
                outer_x_mm=RangeSpec(is_integer=False, start=100.0, end=100.0, count=1),
                outer_y_mm=RangeSpec(is_integer=False, start=80.0, end=80.0, count=1),
                turn_count=RangeSpec(is_integer=True, start=2.0, end=2.0, count=1),
                layer_count=RangeSpec(is_integer=True, start=1.0, end=1.0, count=1),
                underlay_repeat_count=RangeSpec(is_integer=True, start=1.0, end=1.0, count=1),
                void_stack_present=RangeSpec(is_integer=True, start=0.0, end=1.0, count=2),
                underlay_pet_psa_thickness_mm=tx_inner_underlay_thickness,
                underlay_ferrite_thickness_mm=tx_inner_underlay_thickness,
                layer_gap_mm=RangeSpec(is_integer=False, start=2.0, end=2.0, count=1),
                terminal_stub_length_mm=RangeSpec(is_integer=False, start=7.5, end=7.5, count=1),
                void_usage_ratio=RangeSpec(is_integer=False, start=0.2, end=0.2, count=1),
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
            _FakeTvAluminumPlateSpec(
                object_id="tv_aluminum_plate",
                role="tv_aluminum_plate",
                primitive="sheet",
                material="aluminum",
                model_state=True,
                source_non_model_object_id="tv",
                face="+x",
                thickness_mm=0.04,
                sheet_present=RangeSpec(is_integer=True, start=0.0, end=1.0, count=2),
            ),
        )
    )

    def _range_from_modeled(payload: dict[str, object], *, object_id: str, field_name: str) -> RangeSpec:
        modeled_objects = cast(list[dict[str, object]], payload["modeled_objects"])
        modeled_by_id = {cast(str, modeled_object["object_id"]): modeled_object for modeled_object in modeled_objects}
        range_values = cast(
            list[object],
            cast(dict[str, object], modeled_by_id[object_id][field_name])["range"],
        )
        return RangeSpec(
            is_integer=cast(bool, range_values[0]),
            start=float(cast(int | float, range_values[1])),
            end=float(cast(int | float, range_values[2])),
            count=cast(int, range_values[3]),
        )

    def _range_from_tx_reference_line(payload: dict[str, object], *, field_name: str) -> RangeSpec:
        non_model_objects = cast(list[dict[str, object]], payload["non_model_objects"])
        non_model_by_id = {
            cast(str, non_model_object["id"]): non_model_object for non_model_object in non_model_objects
        }
        tx_reference_line = cast(dict[str, object], non_model_by_id["tx_region"]["tx_reference_line"])
        range_values = cast(list[object], cast(dict[str, object], tx_reference_line[field_name])["range"])
        return RangeSpec(
            is_integer=cast(bool, range_values[0]),
            start=float(cast(int | float, range_values[1])),
            end=float(cast(int | float, range_values[2])),
            count=cast(int, range_values[3]),
        )

    def _fake_spec_from_toml(toml_path: Path) -> _FakeRxOnlyType2Spec:
        payload = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        return _FakeRxOnlyType2Spec(
            non_model_objects=(
                NonModelTxRegionSpec(
                    object_id="tx_region",
                    kind="tx_region",
                    primitive="box",
                    present=True,
                    non_model=True,
                    material="vacuum",
                    plane="YZ",
                    origin_xyz=(0.0, -600.0, 0.0),
                    size_xyz=(720.0, 1200.0, 90.0),
                    tx_reference_line=NonModelTxReferenceLineSpec(
                        x_ratio=_range_from_tx_reference_line(payload, field_name="x_ratio"),
                        y_usage_ratio=_range_from_tx_reference_line(payload, field_name="y_usage_ratio"),
                        z_ratio=_range_from_tx_reference_line(payload, field_name="z_ratio"),
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
                    outer_x_usage_ratio=_range_from_modeled(
                        payload, object_id="tx_inner_rect_void_coil", field_name="outer_x_usage_ratio"
                    ),
                    outer_y_usage_ratio=_range_from_modeled(
                        payload, object_id="tx_inner_rect_void_coil", field_name="outer_y_usage_ratio"
                    ),
                    outer_x_mm=RangeSpec(is_integer=False, start=100.0, end=100.0, count=1),
                    outer_y_mm=RangeSpec(is_integer=False, start=80.0, end=80.0, count=1),
                    turn_count=_range_from_modeled(
                        payload, object_id="tx_inner_rect_void_coil", field_name="turn_count"
                    ),
                    layer_count=_range_from_modeled(
                        payload, object_id="tx_inner_rect_void_coil", field_name="layer_count"
                    ),
                    underlay_repeat_count=_range_from_modeled(
                        payload, object_id="tx_inner_rect_void_coil", field_name="underlay_repeat_count"
                    ),
                    void_stack_present=_range_from_modeled(
                        payload, object_id="tx_inner_rect_void_coil", field_name="void_stack_present"
                    ),
                    underlay_pet_psa_thickness_mm=_range_from_modeled(
                        payload,
                        object_id="tx_inner_rect_void_coil",
                        field_name="underlay_pet_psa_thickness_mm",
                    ),
                    underlay_ferrite_thickness_mm=_range_from_modeled(
                        payload,
                        object_id="tx_inner_rect_void_coil",
                        field_name="underlay_ferrite_thickness_mm",
                    ),
                    layer_gap_mm=_range_from_modeled(
                        payload, object_id="tx_inner_rect_void_coil", field_name="layer_gap_mm"
                    ),
                    terminal_stub_length_mm=_range_from_modeled(
                        payload, object_id="tx_inner_rect_void_coil", field_name="terminal_stub_length_mm"
                    ),
                    void_usage_ratio=_range_from_modeled(
                        payload, object_id="tx_inner_rect_void_coil", field_name="void_usage_ratio"
                    ),
                    margin_ratio=_range_from_modeled(
                        payload, object_id="tx_inner_rect_void_coil", field_name="margin_ratio"
                    ),
                    metal_fill_factor=_range_from_modeled(
                        payload, object_id="tx_inner_rect_void_coil", field_name="metal_fill_factor"
                    ),
                    terminal_path="B_cw_to_b",
                    x_position_ratio=_range_from_modeled(
                        payload, object_id="tx_inner_rect_void_coil", field_name="x_position_ratio"
                    ),
                ),
                ModeledRxSingleCoilSpec(
                    object_id="rx_rect_void_coil",
                    role="rx_single_coil",
                    material="composite",
                    model_state=True,
                    pcb_thickness_mm=3.965,
                    copper_thickness_mm=0.035,
                    outer_x_usage_ratio=_range_from_modeled(
                        payload, object_id="rx_rect_void_coil", field_name="outer_x_usage_ratio"
                    ),
                    outer_y_usage_ratio=_range_from_modeled(
                        payload, object_id="rx_rect_void_coil", field_name="outer_y_usage_ratio"
                    ),
                    void_usage_ratio=_range_from_modeled(
                        payload, object_id="rx_rect_void_coil", field_name="void_usage_ratio"
                    ),
                    outer_x_mm=RangeSpec(is_integer=False, start=20.0, end=120.0, count=17),
                    outer_y_mm=RangeSpec(is_integer=False, start=20.0, end=120.0, count=17),
                    turn_count=_range_from_modeled(payload, object_id="rx_rect_void_coil", field_name="turn_count"),
                    layer_count=_range_from_modeled(payload, object_id="rx_rect_void_coil", field_name="layer_count"),
                    underlay_repeat_count=_range_from_modeled(
                        payload, object_id="rx_rect_void_coil", field_name="underlay_repeat_count"
                    ),
                    layer_gap_mm=_range_from_modeled(
                        payload, object_id="rx_rect_void_coil", field_name="layer_gap_mm"
                    ),
                    terminal_stub_length_mm=_range_from_modeled(
                        payload, object_id="rx_rect_void_coil", field_name="terminal_stub_length_mm"
                    ),
                    margin_ratio=_range_from_modeled(payload, object_id="rx_rect_void_coil", field_name="margin_ratio"),
                    metal_fill_factor=_range_from_modeled(
                        payload, object_id="rx_rect_void_coil", field_name="metal_fill_factor"
                    ),
                    terminal_path="A_cw_to_a",
                    x_position_ratio=_range_from_modeled(
                        payload, object_id="rx_rect_void_coil", field_name="x_position_ratio"
                    ),
                ),
                _FakeTvAluminumPlateSpec(
                    object_id="tv_aluminum_plate",
                    role="tv_aluminum_plate",
                    primitive="sheet",
                    material="aluminum",
                    model_state=True,
                    source_non_model_object_id="tv",
                    face="+x",
                    thickness_mm=0.04,
                    sheet_present=_range_from_modeled(
                        payload, object_id="tv_aluminum_plate", field_name="sheet_present"
                    ),
                ),
            ),
        )

    def _patched_loader(toml_path: Path) -> object:
        if toml_path.name == "type2_sweep.toml":
            return fake_spec
        if toml_path.name == "sampled.toml":
            return _fake_spec_from_toml(toml_path)
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
origin_xyz = [0.0, -600.0, 0.0]
size_xyz = [720.0, 1200.0, 90.0]

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
    range = [false, 0.6, 0.6, 1]
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
    [modeled_objects.underlay_pet_psa_thickness_mm]
    range = [false, 3, 3, 1]
    [modeled_objects.underlay_ferrite_thickness_mm]
    range = [false, 3, 3, 1]
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

[[modeled_objects]]
    object_id = "tv_aluminum_plate"
    role = "tv_aluminum_plate"
    primitive = "sheet"
    material = "aluminum"
    model_state = true
    source_non_model_object_id = "tv"
    face = "+x"
    thickness_mm = 0.04
    [modeled_objects.sheet_present]
    range = [true, 0, 1, 2]

""".strip()


def _write_source_type2_toml(tmp_path: Path) -> Path:
    path = tmp_path / "type2_sweep.toml"
    path.write_text(_source_type2_toml_text(), encoding="utf-8")
    return path


def test_load_type2_step_spec_rejects_tx_rect_void_columns_for_rxonly(tmp_path: Path) -> None:
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
range = [false, 0.35, 0.35, 1]

[non_model_objects.tx_reference_line.y_usage_ratio]
range = [false, 1.0, 1.0, 1]

[non_model_objects.tx_reference_line.z_ratio]
range = [false, 0.65, 0.65, 1]

[[modeled_objects]]
object_id = "tx_rect_void_columns"
role = "tx_rect_void_columns"
material = "composite"
model_state = true
pcb_thickness_mm = 3.965
copper_thickness_mm = 0.035
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
    with pytest.raises(ValueError, match=r"unsupported in active RxOnly type2 mode"):
        load_type2_step_spec(source_toml_path)


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
    def _fake_build_type2_sampled_tomls_best_effort(
        sampled_toml_paths: object,
        *,
        jobs: int,
        skipped_ledger_path: Path,
        manifest_path: Path,
        progress_reporter: object,
        reuse_aedt: bool,
        aedt_port_base: int,
        aedt_launch_stagger_sec: float,
    ) -> type2_runtime.Type2BuildBatchResult:
        sampled_toml_path_list = [Path(path) for path in cast(Iterable[str], sampled_toml_paths)]
        calls.append(
            {
                "jobs": jobs,
                "build_count": len(sampled_toml_path_list),
                "sampled_toml_paths": sampled_toml_path_list,
                "skipped_ledger_path": skipped_ledger_path,
                "manifest_path": manifest_path,
                "progress_reporter": progress_reporter,
                "reuse_aedt": reuse_aedt,
                "aedt_port_base": aedt_port_base,
                "aedt_launch_stagger_sec": aedt_launch_stagger_sec,
            }
        )
        return {"built": [], "skipped": []}

    monkeypatch.setattr(
        build_entry,
        "build_type2_sampled_tomls_best_effort",
        _fake_build_type2_sampled_tomls_best_effort,
    )
    results = build_type2(manifest_path=manifest_path)

    assert results == []
    assert len(calls) == 1
    assert calls[0]["jobs"] == 6
    assert calls[0]["reuse_aedt"] is True
    assert calls[0]["aedt_port_base"] == 45000
    assert calls[0]["aedt_launch_stagger_sec"] == 1.0
    assert calls[0]["build_count"] == 2
    assert calls[0]["skipped_ledger_path"] == manifest_path.parent / "type2_build_skipped.json"
    assert calls[0]["manifest_path"] == manifest_path
    sampled_toml_paths = cast(list[Path], calls[0]["sampled_toml_paths"])
    assert len(sampled_toml_paths) == 2
    assert all(sampled_toml_path.name == "sampled.toml" for sampled_toml_path in sampled_toml_paths)


def test_build_type2_retries_worker_process_error_with_bounded_restart(
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
        seed_first=4,
        seed_n=1,
        sampler_n=1,
        aedt_builder_n=1,
        make_step_on_sample=False,
    )
    manifest_entry = sampled_manifest["entries"][0]

    sleeps: list[float] = []
    calls: list[dict[str, object]] = []
    attempted: dict[str, int] = {"count": 0}

    def _fake_build_type2_sampled_tomls_best_effort(
        sampled_toml_paths: object,
        *,
        jobs: int,
        skipped_ledger_path: Path,
        manifest_path: Path,
        progress_reporter: object,
        reuse_aedt: bool,
        aedt_port_base: int,
        aedt_launch_stagger_sec: float,
    ) -> type2_runtime.Type2BuildBatchResult:
        attempted["count"] += 1
        sampled_toml_paths_list = list(cast(Iterable[str], sampled_toml_paths))
        calls.append(
            {
                "jobs": jobs,
                "sampled_toml_paths": sampled_toml_paths_list,
                "skipped_ledger_path": skipped_ledger_path,
                "manifest_path": manifest_path,
                "progress_reporter": progress_reporter,
                "reuse_aedt": reuse_aedt,
                "aedt_port_base": aedt_port_base,
                "aedt_launch_stagger_sec": aedt_launch_stagger_sec,
            }
        )
        if attempted["count"] == 1:
            raise Type2AedtWorkerProcessError("persistent worker process failed on attempt 1")
        return {
            "built": [
                {
                    "design_id": manifest_entry["design_id"],
                    "sampled_toml_path": manifest_entry["sampled_toml_path"],
                    "aedt_path": manifest_entry["aedt_path"],
                    "source_step_ledger_path": manifest_entry["step_ledger_path"],
                    "imported_ledger_path": manifest_entry["imported_ledger_path"],
                }
            ],
            "skipped": [],
        }

    def _sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(
        build_entry,
        "build_type2_sampled_tomls_best_effort",
        _fake_build_type2_sampled_tomls_best_effort,
    )
    results = build_type2(manifest_path=manifest_path, sleep=_sleep)

    assert len(results) == 1
    assert attempted["count"] == 2
    assert sleeps == [60.0]
    assert calls[0]["jobs"] == 1
    assert calls[0]["skipped_ledger_path"] == manifest_path.parent / "type2_build_skipped.json"
    assert calls[0]["manifest_path"] == manifest_path
    assert calls[0]["reuse_aedt"] is True
    assert calls[0]["aedt_port_base"] == 45000
    assert calls[0]["aedt_launch_stagger_sec"] == 1.0
    assert calls[0]["sampled_toml_paths"] == calls[1]["sampled_toml_paths"]


def test_build_type2_does_not_retry_non_worker_exception(
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
        seed_n=1,
        sampler_n=1,
        aedt_builder_n=1,
        make_step_on_sample=False,
    )

    sleeps: list[float] = []
    calls = 0

    def _fake_build_type2_sampled_tomls_best_effort(
        sampled_toml_paths: object,
        *,
        jobs: int,
        skipped_ledger_path: Path,
        manifest_path: Path,
        progress_reporter: object,
        reuse_aedt: bool,
        aedt_port_base: int,
        aedt_launch_stagger_sec: float,
    ) -> type2_runtime.Type2BuildBatchResult:
        nonlocal calls
        calls += 1
        raise ValueError("non-worker failure in builder")

    monkeypatch.setattr(
        build_entry,
        "build_type2_sampled_tomls_best_effort",
        _fake_build_type2_sampled_tomls_best_effort,
    )

    def _sleep(seconds: float) -> None:
        sleeps.append(seconds)

    with pytest.raises(ValueError, match="non-worker failure in builder"):
        build_type2(manifest_path=manifest_path, sleep=_sleep)

    assert calls == 1
    assert sleeps == []


def test_build_type2_raises_after_streaming_skipped_ledger_is_written(
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
        seed_first=4,
        seed_n=1,
        sampler_n=1,
        aedt_builder_n=1,
        make_step_on_sample=False,
    )
    manifest_entry = sampled_manifest["entries"][0]
    skipped: type2_runtime.Type2BuildSkippedEntry = {
        "design_id": manifest_entry["design_id"],
        "seed": manifest_entry["seed"],
        "sampled_toml_path": manifest_entry["sampled_toml_path"],
        "phase": "aedt",
        "error_type": "ValueError",
        "error_message": "imported body bbox drift validation failed",
    }

    def _fake_build_type2_sampled_tomls_best_effort(
        sampled_toml_paths: object,
        *,
        jobs: int,
        skipped_ledger_path: Path,
        manifest_path: Path,
        progress_reporter: object,
        reuse_aedt: bool,
        aedt_port_base: int,
        aedt_launch_stagger_sec: float,
    ) -> type2_runtime.Type2BuildBatchResult:
        _ = list(cast(Iterable[str], sampled_toml_paths))
        _ = jobs, progress_reporter, reuse_aedt, aedt_port_base, aedt_launch_stagger_sec
        build_entry.write_type2_build_skipped_ledger(
            skipped_ledger_path,
            manifest_path=manifest_path,
            skipped=[skipped],
        )
        return {"built": [], "skipped": [skipped]}

    monkeypatch.setattr(
        build_entry,
        "build_type2_sampled_tomls_best_effort",
        _fake_build_type2_sampled_tomls_best_effort,
    )

    with pytest.raises(RuntimeError, match=r"type2 build skipped 1 design"):
        build_type2(manifest_path=manifest_path)

    skipped_ledger_path = manifest_path.parent / "type2_build_skipped.json"
    assert json.loads(skipped_ledger_path.read_text(encoding="utf-8")) == {
        "manifest_path": str(manifest_path),
        "skipped": [skipped],
    }


def test_build_type2_does_not_retry_skipped_validation_errors(
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
        seed_first=4,
        seed_n=1,
        sampler_n=1,
        aedt_builder_n=1,
        make_step_on_sample=False,
    )
    manifest_entry = sampled_manifest["entries"][0]
    skipped: type2_runtime.Type2BuildSkippedEntry = {
        "design_id": manifest_entry["design_id"],
        "seed": manifest_entry["seed"],
        "sampled_toml_path": manifest_entry["sampled_toml_path"],
        "phase": "aedt",
        "error_type": "ValueError",
        "error_message": "unsupported imported body bounds",
    }
    calls = 0
    sleeps: list[float] = []

    def _fake_build_type2_sampled_tomls_best_effort(
        sampled_toml_paths: object,
        *,
        jobs: int,
        skipped_ledger_path: Path,
        manifest_path: Path,
        progress_reporter: object,
        reuse_aedt: bool,
        aedt_port_base: int,
        aedt_launch_stagger_sec: float,
    ) -> type2_runtime.Type2BuildBatchResult:
        nonlocal calls
        calls += 1
        _ = list(cast(Iterable[str], sampled_toml_paths))
        _ = jobs, skipped_ledger_path, manifest_path, progress_reporter
        _ = reuse_aedt, aedt_port_base, aedt_launch_stagger_sec
        return {"built": [], "skipped": [skipped]}

    def _sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(
        build_entry,
        "build_type2_sampled_tomls_best_effort",
        _fake_build_type2_sampled_tomls_best_effort,
    )

    with pytest.raises(RuntimeError, match=r"type2 build skipped 1 design"):
        build_type2(manifest_path=manifest_path, sleep=_sleep)

    assert calls == 1
    assert sleeps == []


def test_build_type2_retries_worker_process_error_three_times_then_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(build_entry, "_BUILD_RESTART_LIMIT", 3)
    _patch_rx_only_spec_loader(monkeypatch)
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"
    sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=4,
        seed_n=1,
        sampler_n=1,
        aedt_builder_n=1,
        make_step_on_sample=False,
    )

    attempts = 0
    sleeps: list[float] = []

    def _fake_build_type2_sampled_tomls_best_effort(
        sampled_toml_paths: object,
        *,
        jobs: int,
        skipped_ledger_path: Path,
        manifest_path: Path,
        progress_reporter: object,
        reuse_aedt: bool,
        aedt_port_base: int,
        aedt_launch_stagger_sec: float,
    ) -> type2_runtime.Type2BuildBatchResult:
        nonlocal attempts
        attempts += 1
        raise Type2AedtWorkerProcessError(f"persistent worker process failed on attempt {attempts}")

    def _sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(
        build_entry,
        "build_type2_sampled_tomls_best_effort",
        _fake_build_type2_sampled_tomls_best_effort,
    )

    with pytest.raises(Type2AedtWorkerProcessError, match="attempt 4"):
        build_type2(manifest_path=manifest_path, sleep=_sleep)

    assert attempts == 4
    assert sleeps == [60.0, 60.0, 60.0]


def test_build_type2_generates_missing_step_for_sample_only_manifest_before_runner(
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
        seed_n=1,
        sampler_n=1,
        aedt_builder_n=1,
        make_step_on_sample=False,
    )

    document = type2_sampled.load_type2_sample_manifest(manifest_path)
    assert document["config"]["make_step_on_sample"] is False
    manifest_entry = document["entries"][0]
    assert not Path(manifest_entry["step_ledger_path"]).exists()

    exporter_calls: list[dict[str, object]] = []
    runner_calls: list[dict[str, object]] = []

    def _fake_exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        output_dir_arg = cast(Path, kwargs["output_dir"])
        ledger_path = cast(Path, kwargs["ledger_path"])
        scene_step_path = output_dir_arg / "type2_scene.step"
        output_dir_arg.mkdir(parents=True, exist_ok=True)
        scene_step_path.write_text("STEP", encoding="utf-8")
        ledger_path.write_text(json.dumps({"scene_step_path": str(scene_step_path)}, indent=2), encoding="utf-8")
        return {"scene_step_path": str(scene_step_path)}

    def _fake_runner(**kwargs: object) -> _Type2BuildRunnerResult:
        runner_calls.append(dict(kwargs))
        return {
            "aedt_path": str(cast(Path, kwargs["output_aedt_path"])),
            "source_step_ledger_path": str(cast(Path, kwargs["step_ledger_path"])),
            "imported_ledger_path": str(cast(Path, kwargs["imported_ledger_path"])),
        }

    results = build_type2(manifest_path=manifest_path, exporter=_fake_exporter, runner=_fake_runner)

    assert len(results) == 1
    assert len(exporter_calls) == 1
    assert len(runner_calls) == 1
    assert cast(Path, exporter_calls[0]["ledger_path"]) == Path(manifest_entry["step_ledger_path"])
    assert cast(Path, runner_calls[0]["step_ledger_path"]) == Path(manifest_entry["step_ledger_path"])
    assert Path(manifest_entry["step_ledger_path"]).is_file()
    assert Path(manifest_entry["scene_step_path"]).is_file()


def test_build_type2_forwards_manifest_path_and_selected_ids_to_streaming_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    sampled_toml_path = tmp_path / "sampled.toml"
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
                "entries": [
                    {
                        "design_id": "design-compat",
                        "seed": 10,
                        "sample_index": 0,
                        "retry_number": 0,
                        "source_toml_path": "/tmp/type2_source.toml",
                        "sampled_toml_path": str(sampled_toml_path),
                        "design_dir": str(tmp_path / "design-compat"),
                        "scene_step_path": str(tmp_path / "design-compat" / "type2_scene.step"),
                        "step_ledger_path": str(tmp_path / "design-compat" / "type2_step_ledger.json"),
                        "imported_ledger_path": str(tmp_path / "design-compat" / "type2_imported_ledger.json"),
                        "aedt_path": str(tmp_path / "design-compat" / "design-compat.aedt"),
                        "sampled_owner_paths": [],
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    calls: dict[str, object] = {}

    def _fake_build_type2_sampled_tomls_best_effort(
        sampled_toml_paths: object,
        *,
        jobs: int,
        skipped_ledger_path: Path,
        manifest_path: Path,
        progress_reporter: object,
        reuse_aedt: bool,
        aedt_port_base: int,
        aedt_launch_stagger_sec: float,
    ) -> type2_runtime.Type2BuildBatchResult:
        calls["jobs"] = jobs
        calls["sampled_toml_paths"] = list(cast(Iterable[str], sampled_toml_paths))
        calls["skipped_ledger_path"] = skipped_ledger_path
        calls["manifest_path"] = manifest_path
        calls["reuse_aedt"] = reuse_aedt
        calls["aedt_port_base"] = aedt_port_base
        calls["aedt_launch_stagger_sec"] = aedt_launch_stagger_sec
        _ = progress_reporter
        return {
            "built": [
                {
                    "design_id": "design-compat",
                    "sampled_toml_path": str(sampled_toml_path),
                    "aedt_path": str(tmp_path / "design-compat" / "design-compat.aedt"),
                    "source_step_ledger_path": str(tmp_path / "design-compat" / "type2_step_ledger.json"),
                    "imported_ledger_path": str(tmp_path / "design-compat" / "type2_imported_ledger.json"),
                }
            ],
            "skipped": [],
        }

    monkeypatch.setattr(
        build_entry,
        "build_type2_sampled_tomls_best_effort",
        _fake_build_type2_sampled_tomls_best_effort,
    )

    results = build_type2(manifest_path=manifest_path, selected_design_ids=("design-compat",))

    assert calls["jobs"] == 7
    assert calls["reuse_aedt"] is True
    assert calls["aedt_port_base"] == 45000
    assert calls["aedt_launch_stagger_sec"] == 1.0
    assert calls["manifest_path"] == manifest_path
    assert calls["skipped_ledger_path"] == manifest_path.parent / "type2_build_skipped.json"
    assert calls["sampled_toml_paths"] == [str(sampled_toml_path)]
    assert len(results) == 1
    assert results[0]["design_id"] == "design-compat"


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

    def _fake_build_prepared_type2_designs_best_effort(
        prepared_builds: tuple[PreparedType2Build, ...],
        *,
        jobs: int,
        exporter: object,
        runner: object,
    ) -> type2_runtime.Type2BuildBatchResult:
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
        return {
            "built": [
                {
                    "design_id": prepared_build.design_id,
                    "sampled_toml_path": str(prepared_build.sampled_toml_path),
                    "aedt_path": cast(str, cast(dict[str, object], runner_result)["aedt_path"]),
                    "source_step_ledger_path": cast(
                        str, cast(dict[str, object], runner_result)["source_step_ledger_path"]
                    ),
                    "imported_ledger_path": cast(str, cast(dict[str, object], runner_result)["imported_ledger_path"]),
                }
            ],
            "skipped": [],
        }

    monkeypatch.setattr(
        build_entry,
        "build_prepared_type2_designs_best_effort",
        _fake_build_prepared_type2_designs_best_effort,
    )
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
    assert all(not name.startswith("modeled_objects_tx_outer_rect_void_coil_") for name, _ in design_variables)
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

    def _fake_build_prepared_type2_designs_best_effort(
        prepared_builds: tuple[PreparedType2Build, ...],
        *,
        jobs: int,
        exporter: object,
        runner: object,
    ) -> type2_runtime.Type2BuildBatchResult:
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
        return {
            "built": [
                {
                    "design_id": prepared_build.design_id,
                    "sampled_toml_path": str(prepared_build.sampled_toml_path),
                    "aedt_path": cast(str, cast(dict[str, object], runner_result)["aedt_path"]),
                    "source_step_ledger_path": cast(
                        str, cast(dict[str, object], runner_result)["source_step_ledger_path"]
                    ),
                    "imported_ledger_path": cast(str, cast(dict[str, object], runner_result)["imported_ledger_path"]),
                }
            ],
            "skipped": [],
        }

    monkeypatch.setattr(
        build_entry,
        "build_prepared_type2_designs_best_effort",
        _fake_build_prepared_type2_designs_best_effort,
    )
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
    assert all(not name.startswith("modeled_objects_tx_outer_rect_void_coil_") for name, _ in design_variables)
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


def test_build_prepared_type2_designs_best_effort_skips_aedt_and_import_runner_for_existing_aedt(
    tmp_path: Path,
) -> None:
    design_id = "design-rx-resume"
    design_dir = tmp_path / design_id
    design_dir.mkdir()
    sampled_toml_path = design_dir / "sampled.toml"
    sampled_toml_path.write_text("[sampled]\n", encoding="utf-8")
    source_toml_path = tmp_path / "source.toml"
    source_toml_path.write_text("[design]\n", encoding="utf-8")
    scene_step_path = design_dir / "type2_scene.step"
    step_ledger_path = design_dir / "type2_step_ledger.json"
    output_aedt_path = design_dir / f"{design_id}.aedt"
    output_aedt_path.write_text("AEDT", encoding="utf-8")
    imported_ledger_path = design_dir / "type2_imported_ledger.json"
    design_variables = (("rx_outer_x_usage_ratio", "0.5"),)
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

    batch = type2_runtime.build_prepared_type2_designs_best_effort(
        (prepared_build,),
        jobs=1,
        exporter=_fake_exporter,
        runner=_fake_runner,
    )

    assert batch["skipped"] == []
    assert len(batch["built"]) == 1
    assert batch["built"][0]["design_id"] == design_id
    assert batch["built"][0]["aedt_path"] == str(output_aedt_path)
    assert batch["built"][0]["source_step_ledger_path"] == str(step_ledger_path)
    assert batch["built"][0]["imported_ledger_path"] == str(imported_ledger_path)
    assert exporter_calls == []
    assert runner_calls == []


def test_build_prepared_type2_designs_best_effort_skips_runner_for_exact_aedt_done_marker(
    tmp_path: Path,
) -> None:
    design_id = "design-rx-done-marker"
    design_dir = tmp_path / design_id
    design_dir.mkdir()
    sampled_toml_path = design_dir / "sampled.toml"
    sampled_toml_path.write_text("[sampled]\n", encoding="utf-8")
    source_toml_path = tmp_path / "source.toml"
    source_toml_path.write_text("[design]\n", encoding="utf-8")
    scene_step_path = design_dir / "type2_scene.step"
    step_ledger_path = design_dir / "type2_step_ledger.json"
    output_aedt_path = design_dir / f"{design_id}.aedt"
    Path(str(output_aedt_path) + ".done").write_text("done\n", encoding="utf-8")
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
        sampled_owner_paths=("modeled_objects.rx_rect_void_coil.outer_x_usage_ratio",),
        modeled_roles=("rx_single_coil",),
        design_variables=(("rx_outer_x_usage_ratio", "0.5"),),
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

    batch = type2_runtime.build_prepared_type2_designs_best_effort(
        (prepared_build,),
        jobs=1,
        exporter=_fake_exporter,
        runner=_fake_runner,
    )

    assert output_aedt_path.is_file() is False
    assert imported_ledger_path.is_file() is False
    assert step_ledger_path.is_file() is False
    assert batch["skipped"] == []
    assert len(batch["built"]) == 1
    assert batch["built"][0]["design_id"] == design_id
    assert batch["built"][0]["aedt_path"] == str(output_aedt_path)
    assert batch["built"][0]["source_step_ledger_path"] == str(step_ledger_path)
    assert batch["built"][0]["imported_ledger_path"] == str(imported_ledger_path)
    assert exporter_calls == []
    assert runner_calls == []


def test_build_prepared_type2_designs_best_effort_skips_runner_when_imported_ledger_is_missing(
    tmp_path: Path,
) -> None:
    design_id = "design-rx-missing-imported"
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
    output_aedt_path.write_text("AEDT", encoding="utf-8")
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
        sampled_owner_paths=("modeled_objects.rx_rect_void_coil.outer_x_usage_ratio",),
        modeled_roles=("rx_single_coil",),
        design_variables=(("rx_outer_x_usage_ratio", "0.5"),),
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

    batch = type2_runtime.build_prepared_type2_designs_best_effort(
        (prepared_build,),
        jobs=1,
        exporter=_fake_exporter,
        runner=_fake_runner,
    )

    assert batch["skipped"] == []
    assert len(batch["built"]) == 1
    assert batch["built"][0]["aedt_path"] == str(output_aedt_path)
    assert batch["built"][0]["source_step_ledger_path"] == str(step_ledger_path)
    assert batch["built"][0]["imported_ledger_path"] == str(imported_ledger_path)
    assert exporter_calls == []
    assert runner_calls == []


def test_build_prepared_type2_designs_best_effort_skips_runner_when_imported_ledger_paths_mismatch_manifest(
    tmp_path: Path,
) -> None:
    design_id = "design-rx-bad-imported"
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
    output_aedt_path.write_text("AEDT", encoding="utf-8")
    imported_ledger_path = design_dir / "type2_imported_ledger.json"
    imported_ledger_payload = {
        "source_step_ledger_path": str(design_dir / "other_step_ledger.json"),
        "aedt_path": str(output_aedt_path),
        "imported_ledger_path": str(imported_ledger_path),
    }
    imported_ledger_path.write_text(json.dumps(imported_ledger_payload, indent=2), encoding="utf-8")
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
        design_variables=(("rx_outer_x_usage_ratio", "0.5"),),
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

    batch = type2_runtime.build_prepared_type2_designs_best_effort(
        (prepared_build,),
        jobs=1,
        exporter=_fake_exporter,
        runner=_fake_runner,
    )

    assert batch["skipped"] == []
    assert len(batch["built"]) == 1
    assert batch["built"][0]["aedt_path"] == str(output_aedt_path)
    assert batch["built"][0]["source_step_ledger_path"] == str(step_ledger_path)
    assert batch["built"][0]["imported_ledger_path"] == str(imported_ledger_path)
    assert exporter_calls == []
    assert runner_calls == []


def test_build_prepared_type2_designs_best_effort_calls_runner_when_aedt_is_missing(tmp_path: Path) -> None:
    design_id = "design-rx-missing-aedt"
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
        sampled_owner_paths=("modeled_objects.rx_rect_void_coil.outer_x_usage_ratio",),
        modeled_roles=("rx_single_coil",),
        design_variables=(("rx_outer_x_usage_ratio", "0.5"),),
    )

    runner_calls: list[dict[str, object]] = []

    def _fake_runner(**kwargs: object) -> _Type2BuildRunnerResult:
        runner_calls.append(dict(kwargs))
        return {
            "aedt_path": str(cast(Path, kwargs["output_aedt_path"])),
            "source_step_ledger_path": str(cast(Path, kwargs["step_ledger_path"])),
            "imported_ledger_path": str(cast(Path, kwargs["imported_ledger_path"])),
        }

    batch = type2_runtime.build_prepared_type2_designs_best_effort(
        (prepared_build,),
        jobs=1,
        runner=_fake_runner,
    )

    assert batch["skipped"] == []
    assert len(batch["built"]) == 1
    assert len(runner_calls) == 1
    assert batch["built"][0]["aedt_path"] == str(output_aedt_path)
    assert cast(Path, runner_calls[0]["step_ledger_path"]) == step_ledger_path
    assert cast(Path, runner_calls[0]["output_aedt_path"]) == output_aedt_path
    assert cast(Path, runner_calls[0]["imported_ledger_path"]) == imported_ledger_path


def test_solve_type2_uses_solve_runner_and_returns_report_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    sampled_toml_path = tmp_path / "sampled.toml"
    design_dir = tmp_path / "design-em"
    manifest_path.write_text(
        json.dumps(
            {
                "config": {
                    "source_toml_path": "/tmp/type2_source.toml",
                    "seed_first": 10,
                    "seed_n": 1,
                    "sampler_n": 1,
                    "make_step_on_sample": True,
                    "aedt_builder_n": 3,
                },
                "entries": [
                    {
                        "design_id": "design-em",
                        "seed": 10,
                        "sample_index": 0,
                        "retry_number": 0,
                        "source_toml_path": "/tmp/type2_source.toml",
                        "sampled_toml_path": str(sampled_toml_path),
                        "design_dir": str(design_dir),
                        "scene_step_path": str(design_dir / "type2_scene.step"),
                        "step_ledger_path": str(design_dir / "type2_step_ledger.json"),
                        "imported_ledger_path": str(design_dir / "type2_imported_ledger.json"),
                        "aedt_path": str(design_dir / "design-em.aedt"),
                        "sampled_owner_paths": [],
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    calls: dict[str, object] = {}

    def _fake_solve_type2_sampled_tomls(
        sampled_toml_paths: object,
        *,
        jobs: int,
        progress_reporter: object,
    ) -> list[dict[str, object]]:
        _ = progress_reporter
        calls["jobs"] = jobs
        calls["sampled_toml_paths"] = list(cast(Iterable[str], sampled_toml_paths))
        return [
            {
                "design_id": "design-em",
                "sampled_toml_path": str(sampled_toml_path),
                "aedt_path": str(design_dir / "design-em.aedt"),
                "source_step_ledger_path": str(design_dir / "type2_step_ledger.json"),
                "imported_ledger_path": str(design_dir / "type2_imported_ledger.json"),
                "em_solve": {
                    "setup_name": "Setup1",
                    "report_name": "Output Variables Table1",
                    "report_csv_path": str(design_dir / "Output_Variables_Table1.csv"),
                },
            }
        ]

    monkeypatch.setattr(build_entry, "solve_type2_sampled_tomls", _fake_solve_type2_sampled_tomls)

    results = solve_type2(manifest_path=manifest_path)

    assert calls["jobs"] == 3
    assert calls["sampled_toml_paths"] == [str(sampled_toml_path)]
    assert results[0]["em_solve"]["report_csv_path"] == str(design_dir / "Output_Variables_Table1.csv")


def test_build_prepared_type2_design_accepts_rx_with_tx_inner_geometry_role(tmp_path: Path) -> None:
    design_id = "design-rx-tx-inner"
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
        sampled_owner_paths=("modeled_objects.tx_inner_rect_void_coil.outer_x_usage_ratio",),
        modeled_roles=("rx_single_coil", "tx_inner_single_coil"),
        design_variables=(("tx_inner_outer_x_usage_ratio", "0.5"),),
    )

    runner_calls: list[dict[str, object]] = []

    def _fake_runner(**kwargs: object) -> _Type2BuildRunnerResult:
        runner_calls.append(dict(kwargs))
        return {
            "aedt_path": str(cast(Path, kwargs["output_aedt_path"])),
            "source_step_ledger_path": str(cast(Path, kwargs["step_ledger_path"])),
            "imported_ledger_path": str(cast(Path, kwargs["imported_ledger_path"])),
        }

    result = type2_runtime.build_prepared_type2_design(prepared_build, runner=_fake_runner)

    assert result["design_id"] == design_id
    assert len(runner_calls) == 1


def test_build_prepared_type2_designs_best_effort_skips_step_value_error(tmp_path: Path) -> None:
    source_toml_path = tmp_path / "source.toml"
    source_toml_path.write_text("[design]\n", encoding="utf-8")
    prepared_builds: list[PreparedType2Build] = []
    for index, design_id in enumerate(("s000000_success", "s000001_failure")):
        design_dir = tmp_path / design_id
        design_dir.mkdir()
        sampled_toml_path = design_dir / "sampled.toml"
        sampled_toml_path.write_text("[sampled]\n", encoding="utf-8")
        prepared_builds.append(
            PreparedType2Build(
                design_id=design_id,
                seed=index,
                source_toml_path=source_toml_path,
                sampled_toml_path=sampled_toml_path,
                design_dir=design_dir,
                scene_step_path=design_dir / "type2_scene.step",
                step_ledger_path=design_dir / "type2_step_ledger.json",
                imported_ledger_path=design_dir / "type2_imported_ledger.json",
                aedt_path=design_dir / f"{design_id}.aedt",
                sampled_owner_paths=("modeled_objects.rx_rect_void_coil.outer_x_usage_ratio",),
                modeled_roles=("rx_single_coil",),
                design_variables=(("rx_outer_x_usage_ratio", "0.5"),),
            )
        )

    def _fake_exporter(**kwargs: object) -> object:
        output_dir = cast(Path, kwargs["output_dir"])
        if output_dir.name == "s000001_failure":
            raise ValueError("central corridor proof failed")
        scene_step_path = output_dir / "type2_scene.step"
        ledger_path = cast(Path, kwargs["ledger_path"])
        scene_step_path.write_text("STEP", encoding="utf-8")
        ledger_path.write_text(json.dumps({"scene_step_path": str(scene_step_path)}, indent=2), encoding="utf-8")
        return {"scene_step_path": str(scene_step_path)}

    def _fake_runner(**kwargs: object) -> _Type2BuildRunnerResult:
        return {
            "aedt_path": str(cast(Path, kwargs["output_aedt_path"])),
            "source_step_ledger_path": str(cast(Path, kwargs["step_ledger_path"])),
            "imported_ledger_path": str(cast(Path, kwargs["imported_ledger_path"])),
        }

    batch = type2_runtime.build_prepared_type2_designs_best_effort(
        tuple(prepared_builds),
        jobs=1,
        exporter=_fake_exporter,
        runner=_fake_runner,
    )

    assert [built["design_id"] for built in batch["built"]] == ["s000000_success"]
    assert len(batch["skipped"]) == 1
    assert batch["skipped"][0]["design_id"] == "s000001_failure"
    assert batch["skipped"][0]["phase"] == "step"
    assert batch["skipped"][0]["error_type"] == "ValueError"
    assert batch["skipped"][0]["error_message"] == "central corridor proof failed"


def test_build_prepared_type2_design_accepts_rx_with_tx_inner_and_outer_geometry_roles(tmp_path: Path) -> None:
    design_id = "design-rx-tx-inner-outer"
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
        sampled_owner_paths=(
            "modeled_objects.rx_rect_void_coil.outer_x_usage_ratio",
            "modeled_objects.tx_inner_rect_void_coil.void_stack_present",
        ),
        modeled_roles=("rx_single_coil", "tx_inner_single_coil"),
        design_variables=(
            ("rx_outer_x_usage_ratio", "0.5"),
            ("tx_inner_void_stack_present", "1"),
        ),
    )

    runner_calls: list[dict[str, object]] = []

    def _fake_runner(**kwargs: object) -> _Type2BuildRunnerResult:
        runner_calls.append(dict(kwargs))
        return {
            "aedt_path": str(cast(Path, kwargs["output_aedt_path"])),
            "source_step_ledger_path": str(cast(Path, kwargs["step_ledger_path"])),
            "imported_ledger_path": str(cast(Path, kwargs["imported_ledger_path"])),
        }

    result = type2_runtime.build_prepared_type2_design(prepared_build, runner=_fake_runner)

    assert result["design_id"] == design_id
    assert len(runner_calls) == 1
    assert runner_calls[0]["step_ledger_path"] == step_ledger_path
    assert runner_calls[0]["output_aedt_path"] == output_aedt_path
    assert runner_calls[0]["imported_ledger_path"] == imported_ledger_path


def test_build_prepared_type2_design_accepts_passive_tv_aluminum_plate_with_txrx_roles(tmp_path: Path) -> None:
    design_id = "design-rx-tx-inner-tv"
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
        sampled_owner_paths=("modeled_objects.tx_inner_rect_void_coil.outer_x_usage_ratio",),
        modeled_roles=("rx_single_coil", "tx_inner_single_coil", "tv_aluminum_plate"),
        design_variables=(("tx_inner_outer_x_usage_ratio", "0.5"),),
    )

    runner_calls: list[dict[str, object]] = []

    def _fake_runner(**kwargs: object) -> _Type2BuildRunnerResult:
        runner_calls.append(dict(kwargs))
        return {
            "aedt_path": str(cast(Path, kwargs["output_aedt_path"])),
            "source_step_ledger_path": str(cast(Path, kwargs["step_ledger_path"])),
            "imported_ledger_path": str(cast(Path, kwargs["imported_ledger_path"])),
        }

    result = type2_runtime.build_prepared_type2_design(prepared_build, runner=_fake_runner)

    assert result["design_id"] == design_id
    assert len(runner_calls) == 1


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
        design_variables=(("tx_single_outer_x_usage_ratio", "0.5"), ("tx_single_outer_y_usage_ratio", "0.6")),
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


def test_build_prepared_type2_design_rejects_tx_rect_void_columns_without_rx_pair(tmp_path: Path) -> None:
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

    with pytest.raises(ValueError, match=r"type2 build/setup-ready rejects unsupported modeled roles"):
        type2_runtime.build_prepared_type2_design(
            prepared_build,
            exporter=_fake_exporter,
            runner=_fake_runner,
        )

    assert runner_calls == []
    assert exporter_calls == []


def test_build_prepared_type2_design_rejects_tx_rect_void_columns_with_rx_single_coil_pair(tmp_path: Path) -> None:
    design_id = "design-columns-rx"
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
        modeled_roles=("rx_single_coil", "tx_rect_void_columns"),
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

    with pytest.raises(ValueError, match=r"type2 build/setup-ready rejects unsupported modeled roles"):
        type2_runtime.build_prepared_type2_design(
            prepared_build,
            exporter=_fake_exporter,
            runner=_fake_runner,
        )

    assert exporter_calls == []
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
        run_aedt_design_validation: bool,
    ) -> _Type2BuildRunnerResult:
        captured["runner_kwargs"] = {
            "hfss": hfss,
            "step_ledger_path": step_ledger_path,
            "output_aedt_path": output_aedt_path,
            "imported_ledger_path": imported_ledger_path,
            "design_variables": design_variables,
            "run_aedt_design_validation": run_aedt_design_validation,
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
    assert runner_kwargs["run_aedt_design_validation"] is False
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


def test_type2_manifest_streaming_iterates_selected_entries(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "config": {
                    "source_toml_path": "/tmp/source.toml",
                    "seed_first": 0,
                    "seed_n": 3,
                    "sampler_n": 1,
                    "make_step_on_sample": False,
                    "aedt_builder_n": 4,
                },
                "entries": [
                    {
                        "design_id": f"design-{index}",
                        "seed": index,
                        "sample_index": index,
                        "retry_number": 0,
                        "source_toml_path": "/tmp/source.toml",
                        "sampled_toml_path": str(tmp_path / f"design-{index}" / "sampled.toml"),
                        "design_dir": str(tmp_path / f"design-{index}"),
                        "scene_step_path": str(tmp_path / f"design-{index}" / "type2_scene.step"),
                        "step_ledger_path": str(tmp_path / f"design-{index}" / "type2_step_ledger.json"),
                        "imported_ledger_path": str(tmp_path / f"design-{index}" / "type2_imported_ledger.json"),
                        "aedt_path": str(tmp_path / f"design-{index}" / f"design-{index}.aedt"),
                        "sampled_owner_paths": [],
                    }
                    for index in range(3)
                ],
                "skipped": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    config = type2_sampled.load_type2_sample_manifest_config(manifest_path)
    entries = tuple(
        type2_sampled.iter_type2_sample_manifest_entries(manifest_path, selected_design_ids=("design-2",))
    )

    assert config["aedt_builder_n"] == 4
    assert [entry["design_id"] for entry in entries] == ["design-2"]


def test_bounded_parallel_results_preserves_order_and_limits_initial_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submit_calls: list[str] = []

    class _FakeProcessPoolExecutor:
        def __init__(self, *, max_workers: int) -> None:
            assert max_workers == 2

        def __enter__(self) -> "_FakeProcessPoolExecutor":
            return self

        def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
            return None

        def submit(self, worker: Callable[[str], object], item: str) -> Future[object]:
            submit_calls.append(item)
            future: Future[object] = Future()
            future.set_result(worker(item))
            return future

    monkeypatch.setattr(type2_runtime, "ProcessPoolExecutor", _FakeProcessPoolExecutor)

    results = list(
        type2_runtime._iter_bounded_parallel_results(
            ("3", "2", "1", "0"),
            jobs=2,
            worker=lambda item: f"result-{item}",
            max_pending=2,
        )
    )

    assert submit_calls[:2] == ["3", "2"]
    assert results == ["result-3", "result-2", "result-1", "result-0"]


def test_build_type2_sampled_tomls_writes_streaming_skipped_ledger(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    ledger_path = tmp_path / "type2_build_skipped.json"
    skipped = {
        "design_id": "design-skip",
        "seed": 1,
        "sampled_toml_path": str(tmp_path / "sampled.toml"),
        "phase": "step",
        "error_type": "ValueError",
        "error_message": "bad geometry",
    }

    def _fake_iter_bounded_parallel_results(
        inputs: object,
        *,
        jobs: int,
        worker: object,
        max_pending: int | None = None,
    ) -> object:
        _ = list(cast(Iterable[str], inputs)), jobs, worker, max_pending
        return iter(
            (
                {
                    "status": "skipped",
                    "skipped": skipped,
                },
            )
        )

    monkeypatch.setattr(type2_runtime, "_iter_bounded_parallel_results", _fake_iter_bounded_parallel_results)

    batch = type2_runtime.build_type2_sampled_tomls_best_effort(
        (tmp_path / "sampled.toml",),
        jobs=2,
        skipped_ledger_path=ledger_path,
        manifest_path=manifest_path,
        reuse_aedt=False,
    )

    assert batch["built"] == []
    assert batch["skipped"] == [skipped]
    assert json.loads(ledger_path.read_text(encoding="utf-8")) == {
        "manifest_path": str(manifest_path),
        "skipped": [skipped],
    }


def test_persistent_aedt_launch_uses_fixed_port_and_keeps_desktop_open() -> None:
    calls: list[dict[str, object]] = []
    releases: list[dict[str, object]] = []

    class _FakeDesktop:
        def release_desktop(self, *, close_projects: bool, close_on_exit: bool) -> bool:
            releases.append({"close_projects": close_projects, "close_on_exit": close_on_exit})
            return True

    class _FakeHfss:
        desktop_class = _FakeDesktop()

    def _fake_hfss_factory(**kwargs: object) -> _FakeHfss:
        calls.append(dict(kwargs))
        return _FakeHfss()

    type2_runtime._launch_persistent_aedt_session(worker_index=2, port=45002, hfss_factory=_fake_hfss_factory)

    assert calls == [
        {
            "project": None,
            "design": "peets_type2_worker_2",
            "non_graphical": True,
            "new_desktop": True,
            "close_on_exit": False,
            "port": 45002,
        }
    ]
    assert releases == [{"close_projects": True, "close_on_exit": False}]


def test_persistent_build_attempt_attaches_per_design_and_closes_only_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    design_id = "design-rx"
    sampled_toml_path = tmp_path / "sampled.toml"
    source_toml_path = tmp_path / "source.toml"
    step_ledger_path = tmp_path / "type2_step_ledger.json"
    imported_ledger_path = tmp_path / "type2_imported_ledger.json"
    aedt_path = tmp_path / f"{design_id}.aedt"
    prepared_build = PreparedType2Build(
        design_id=design_id,
        seed=1,
        source_toml_path=source_toml_path,
        sampled_toml_path=sampled_toml_path,
        design_dir=tmp_path,
        scene_step_path=tmp_path / "type2_scene.step",
        step_ledger_path=step_ledger_path,
        imported_ledger_path=imported_ledger_path,
        aedt_path=aedt_path,
        sampled_owner_paths=(),
        modeled_roles=("rx_single_coil",),
        design_variables=(("rx_outer_x_usage_ratio", "0.5"),),
    )
    create_calls: list[dict[str, object]] = []
    setup_calls: list[dict[str, object]] = []

    class _FakeHfss:
        pass

    def _fake_create_persistent_hfss(**kwargs: object) -> _FakeHfss:
        create_calls.append(dict(kwargs))
        return _FakeHfss()

    def _fake_setup_type2_step_ledger_into_hfss(**kwargs: object) -> _Type2BuildRunnerResult:
        setup_calls.append(dict(kwargs))
        return {
            "aedt_path": str(cast(Path, kwargs["output_aedt_path"])),
            "source_step_ledger_path": str(cast(Path, kwargs["step_ledger_path"])),
            "imported_ledger_path": str(cast(Path, kwargs["imported_ledger_path"])),
        }

    monkeypatch.setattr(type2_runtime, "ensure_prepared_type2_step_ledger", lambda prepared_build: None)
    monkeypatch.setattr(type2_runtime, "_is_resume_ready_type2_build", lambda prepared_build: False)
    monkeypatch.setattr(type2_runtime, "_create_persistent_hfss", _fake_create_persistent_hfss)
    monkeypatch.setattr(type2_runtime, "setup_type2_step_ledger_into_hfss", _fake_setup_type2_step_ledger_into_hfss)

    attempt = type2_runtime._build_prepared_type2_design_attempt_with_persistent_aedt(
        prepared_build,
        worker_index=1,
        port=45001,
    )

    assert attempt["status"] == "built"
    assert create_calls == [
        {
            "design_name": design_id,
            "port": 45001,
            "new_desktop": False,
            "project_path": aedt_path,
            "hfss_factory": type2_runtime.Hfss,
        }
    ]
    assert setup_calls[0]["hfss"].__class__ is _FakeHfss
    assert setup_calls[0]["close_projects_on_release"] is True


def test_start_persistent_build_workers_uses_fixed_ports_and_stagger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ports: list[int] = []
    sleeps: list[float] = []

    class _TrackingQueue:
        def __init__(self) -> None:
            self.messages: list[object] = []
            self.get_call_count = 0

        def put(self, item: object) -> None:
            self.messages.append(item)

        def get(self, timeout: float | None = None) -> object:
            _ = timeout
            self.get_call_count += 1
            if not self.messages:
                raise AssertionError("ready messages must be queued before readiness collection")
            return self.messages.pop(0)

    class _FakeProcess:
        def __init__(self, *, target: object, kwargs: dict[str, object]) -> None:
            self.kwargs = kwargs
            self.pid = 123
            self.exitcode = None

        def start(self) -> None:
            port = cast(int, self.kwargs["port"])
            worker_index = cast(int, self.kwargs["worker_index"])
            ports.append(port)
            cast(LocalQueue[object], self.kwargs["result_queue"]).put(("ready", worker_index, port))

        def is_alive(self) -> bool:
            return False

        def join(self, timeout: float | None = None) -> None:
            _ = timeout

        def terminate(self) -> None:
            pass

    monkeypatch.setattr(type2_runtime, "Process", _FakeProcess)
    task_queue: LocalQueue[Any] = LocalQueue()
    result_queue = _TrackingQueue()

    def _sleep(seconds: float) -> None:
        assert result_queue.get_call_count == 0
        sleeps.append(seconds)

    workers = type2_runtime._start_persistent_build_workers(
        jobs=3,
        aedt_port_base=46000,
        aedt_launch_stagger_sec=1.0,
        task_queue=cast(Any, task_queue),
        result_queue=cast(Any, result_queue),
        sleep=_sleep,
    )

    assert len(workers) == 3
    assert ports == [46000, 46001, 46002]
    assert sleeps == [1.0, 1.0]
    assert result_queue.get_call_count == 3


def test_start_persistent_build_workers_treats_license_launch_failure_as_batch_fatal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeProcess:
        def __init__(self, *, target: object, kwargs: dict[str, object]) -> None:
            self.kwargs = kwargs
            self.pid = 123
            self.exitcode = None

        def start(self) -> None:
            cast(LocalQueue[object], self.kwargs["result_queue"]).put(
                (
                    "fatal",
                    cast(int, self.kwargs["worker_index"]),
                    "RuntimeError: Request name electronics3d_gui 1,hfss_gui 1 does not exist in the licensing pool.",
                )
            )

        def is_alive(self) -> bool:
            return False

        def join(self, timeout: float | None = None) -> None:
            _ = timeout

        def terminate(self) -> None:
            pass

    monkeypatch.setattr(type2_runtime, "Process", _FakeProcess)
    task_queue: LocalQueue[Any] = LocalQueue()
    result_queue: LocalQueue[Any] = LocalQueue()

    with pytest.raises(type2_runtime.Type2AedtWorkerLaunchError, match=r"license pool"):
        type2_runtime._start_persistent_build_workers(
            jobs=1,
            aedt_port_base=46000,
            aedt_launch_stagger_sec=5.0,
            task_queue=cast(Any, task_queue),
            result_queue=cast(Any, result_queue),
            sleep=lambda _: None,
        )


def test_run_build_cli_passes_design_id_to_headless_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")

    calls: dict[str, object] = {}

    def _fake_build_type2(
        *,
        manifest_path: Path,
        selected_design_ids: tuple[str, ...],
        reuse_aedt: bool,
        aedt_port_base: int,
        aedt_launch_stagger_sec: float,
    ) -> list[Type2BuiltArtifact]:
        calls["manifest_path"] = manifest_path
        calls["selected_design_ids"] = selected_design_ids
        calls["reuse_aedt"] = reuse_aedt
        calls["aedt_port_base"] = aedt_port_base
        calls["aedt_launch_stagger_sec"] = aedt_launch_stagger_sec
        return []

    monkeypatch.setattr(build_entry, "build_type2", _fake_build_type2)

    assert run_build_cli(("--manifest", str(manifest_path), "--design-id", "abc")) == []
    assert calls["manifest_path"] == manifest_path
    assert calls["selected_design_ids"] == ("abc",)
    assert calls["reuse_aedt"] is True
    assert calls["aedt_port_base"] == 45000
    assert calls["aedt_launch_stagger_sec"] == 1.0


def test_run_build_cli_passes_aedt_reuse_knobs_to_headless_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    calls: dict[str, object] = {}

    def _fake_build_type2(
        *,
        manifest_path: Path,
        selected_design_ids: tuple[str, ...],
        reuse_aedt: bool,
        aedt_port_base: int,
        aedt_launch_stagger_sec: float,
    ) -> list[Type2BuiltArtifact]:
        calls["manifest_path"] = manifest_path
        calls["selected_design_ids"] = selected_design_ids
        calls["reuse_aedt"] = reuse_aedt
        calls["aedt_port_base"] = aedt_port_base
        calls["aedt_launch_stagger_sec"] = aedt_launch_stagger_sec
        return []

    monkeypatch.setattr(build_entry, "build_type2", _fake_build_type2)

    assert (
        run_build_cli(
            (
                "--manifest",
                str(manifest_path),
                "--no-aedt-reuse",
                "--aedt-port-base",
                "47000",
                "--aedt-launch-stagger-sec",
                "7.5",
            )
        )
        == []
    )
    assert calls == {
        "manifest_path": manifest_path,
        "selected_design_ids": (),
        "reuse_aedt": False,
        "aedt_port_base": 47000,
        "aedt_launch_stagger_sec": 7.5,
    }

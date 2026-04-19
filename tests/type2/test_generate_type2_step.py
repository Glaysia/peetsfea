from __future__ import annotations

from collections.abc import Sequence
import json
import math
import tempfile
from pathlib import Path
from typing import Literal, cast

import build123d as bd
import pytest

from peetsfea.type2_plate_stack import expected_plate_stack_body_names
from peetsfea.type2_plate_stack import total_plate_stack_thickness_mm
from peetsfea.type2_step_ledger import ExportedBodyGroup
from peetsfea.tx_rect_void import BoxSpec
from peetsfea.tx_rect_void import SingleCoilProfile
from peetsfea.tx_rect_void import build_tx_rect_void_box_specs
from peetsfea.tx_rect_void import build_tx_rect_void_centerline
from peetsfea.tx_rect_void import load_tx_rect_void_spec
from peetsfea.tx_rect_void import modeled_body_bounds_from_boxes
from peetsfea.tx_rect_void import profile_for_modeled_role
from peetsfea.tx_rect_void import realize_tx_rect_void_spec
from peetsfea.type2_step_export import export_type2_step_artifacts
from peetsfea.type2_step_spec import ModeledPlateStackSpec
from peetsfea.type2_step_spec import ModeledSingleCoilSpec
from peetsfea.type2_step_spec import load_type2_step_spec
from peetsfea.type2_step_spec import render_tx_rect_void_toml
from peetsfea.type2_step_spec import resolve_modeled_plate_stack_metal_fill_factor
from peetsfea.type2_step_spec import resolve_modeled_plate_stack_turn_count
from peetsfea.type2_step_spec import resolve_modeled_underlay_gap_mm
from peetsfea.type2_step_spec import resolve_modeled_underlay_repeat_count
from peetsfea.type2_step_spec import resolve_modeled_wall_parallel_stack_present
from tests.fixtures.legacy.type1_spec import TYPE1_OUTPUT_VARIABLES, type1_outputs_spec

_TX_UNDERLAY_FERRITE_THICKNESS_MM = 0.20
_TX_UNDERLAY_PET_PSA_THICKNESS_MM = 0.15
_TX_UNDERLAY_AIR_THICKNESS_MM = 0.02
_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM = 0.4
_TX_FERRITE_GROUP_NAME = "g_ferrite_tx"
_RX_FERRITE_GROUP_NAME = "g_ferrite_rx"


def _range(is_integer: bool, start: float, end: float, count: int) -> str:
    flag = "true" if is_integer else "false"
    return f"[{flag}, {start}, {end}, {count}]"


def _outputs_spec_text() -> str:
    lines = [
        "[outputs]",
        'report_name = "Output Variables Table1"',
        'solution_name = "Setup1 : LastAdaptive"',
        'primary_sweep = "Freq"',
        'report_category = "Terminal Solution Data"',
        'plot_type = "Data Table"',
        "",
    ]
    for name, expression in TYPE1_OUTPUT_VARIABLES:
        lines.extend(
            (
                "[[outputs.variables]]",
                f'name = "{name}"',
                f'expression = "{expression}"',
                "",
            )
        )
    return "\n".join(lines).rstrip()


def _remove_outputs_block(toml_text: str) -> str:
    start = toml_text.index("[outputs]")
    end = toml_text.index("[[non_model_objects]]")
    return toml_text[:start].rstrip() + "\n\n" + toml_text[end:]


def _vertex_triplets(raw_vertices: list[list[float]]) -> tuple[tuple[float, float, float], ...]:
    return tuple((vertex[0], vertex[1], vertex[2]) for vertex in raw_vertices)


def _type2_spec_text(
    *,
    modeled_object_id: str = "tx_rect_void_coil",
    modeled_role: str = "tx_single_coil",
    terminal_path: str = "A_cw_to_a",
    layer_count: int = 1,
    radiation_margin_mm: float = 3500.0,
    underlay_repeat_count_range: str | None = None,
    underlay_gap_range: str | None = None,
    wall_parallel_stack_present_range: str | None = None,
) -> str:
    if underlay_repeat_count_range is None:
        underlay_repeat_count_range = _range(True, 0.0, 8.0, 5)
    underlay_gap_section = ""
    wall_parallel_stack_present_section = ""
    if modeled_role == "tx_single_coil":
        if underlay_gap_range is None:
            underlay_gap_range = _range(False, 1.0, 10.0, 4)
        if wall_parallel_stack_present_range is None:
            wall_parallel_stack_present_range = _range(True, 0.0, 0.0, 1)
        underlay_gap_section = f"""
[modeled_objects.underlay_gap_mm]
range = {underlay_gap_range}
""".rstrip()
        wall_parallel_stack_present_section = f"""
[modeled_objects.wall_parallel_stack_present]
range = {wall_parallel_stack_present_range}
""".rstrip()
    elif underlay_gap_range is not None:
        underlay_gap_section = f"""
[modeled_objects.underlay_gap_mm]
range = {underlay_gap_range}
""".rstrip()
    elif wall_parallel_stack_present_range is not None:
        wall_parallel_stack_present_section = f"""
[modeled_objects.wall_parallel_stack_present]
range = {wall_parallel_stack_present_range}
""".rstrip()
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.type2.step.v2"
runtime_compatible = false

[design]
units = "mm"

[simulation]
radiation_margin_mm = {radiation_margin_mm}

{_outputs_spec_text()}

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
object_id = "{modeled_object_id}"
role = "{modeled_role}"
material = "composite"
model_state = true
pcb_thickness_mm = 1.6
copper_thickness_mm = 0.1

[modeled_objects.outer_x_mm]
range = {_range(False, 50.0, 50.0, 1)}
[modeled_objects.outer_y_mm]
range = {_range(False, 60.0, 60.0, 1)}
[modeled_objects.turn_count]
range = {_range(True, 2.0, 2.0, 1)}
[modeled_objects.layer_count]
range = {_range(True, float(layer_count), float(layer_count), 1)}
[modeled_objects.underlay_repeat_count]
range = {underlay_repeat_count_range}
{underlay_gap_section}
{wall_parallel_stack_present_section}
[modeled_objects.layer_gap_mm]
range = {_range(False, 2.0, 2.0, 1)}
[modeled_objects.terminal_stub_length_mm]
range = {_range(False, 5.0, 5.0, 1)}
[modeled_objects.void_x_over_outer_x]
range = {_range(False, 0.3, 0.3, 1)}
[modeled_objects.void_y_over_outer_y]
range = {_range(False, 0.3, 0.3, 1)}
[modeled_objects.void_center_x_over_outer_x]
range = {_range(False, 0.0, 0.0, 1)}
[modeled_objects.void_center_y_over_outer_y]
range = {_range(False, 0.0, 0.0, 1)}
[modeled_objects.margin_ratio]
range = {_range(False, 0.05, 0.05, 1)}
[modeled_objects.metal_fill_factor]
range = {_range(False, 0.5, 0.5, 1)}
    [modeled_objects.terminal_path]
    value = "{terminal_path}"
    """.strip()


def _type2_rx_plate_stack_spec_text(
    *,
    modeled_object_id: str = "rx_plate_stack",
    modeled_role: str = "rx_plate_stack",
    pcb_total_thickness_mm: float = _PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    copper_thickness_mm: float = 0.1,
    ferrite_set_count: int = 10,
    turn_count_range: str = "[true, 3.0, 3.0, 1]",
    metal_fill_factor_range: str = "[false, 0.4, 0.4, 1]",
    radiation_margin_mm: float = 3500.0,
    extra_modeled_lines: tuple[str, ...] = (),
) -> str:
    extra_body = "\n".join(extra_modeled_lines)
    if extra_body != "":
        extra_body = f"\n{extra_body}"
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.type2.step.v2"
runtime_compatible = false

[design]
units = "mm"

[simulation]
radiation_margin_mm = {radiation_margin_mm}

{_outputs_spec_text()}

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
object_id = "{modeled_object_id}"
role = "{modeled_role}"
material = "composite"
model_state = true
pcb_total_thickness_mm = {pcb_total_thickness_mm}
copper_thickness_mm = {copper_thickness_mm}
ferrite_set_count = {ferrite_set_count}
[modeled_objects.turn_count]
range = {turn_count_range}
[modeled_objects.metal_fill_factor]
range = {metal_fill_factor_range}{extra_body}
""".strip()


def _type2_tx_plate_stack_spec_text(
    *,
    modeled_object_id: str = "tx_plate_stack",
    modeled_role: str = "tx_plate_stack",
    pcb_total_thickness_mm: float = _PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    copper_thickness_mm: float = 0.1,
    ferrite_set_count: int = 10,
    turn_count_range: str = "[true, 3.0, 3.0, 1]",
    metal_fill_factor_range: str = "[false, 0.4, 0.4, 1]",
    radiation_margin_mm: float = 3500.0,
    extra_modeled_lines: tuple[str, ...] = (),
) -> str:
    return _type2_rx_plate_stack_spec_text(
        modeled_object_id=modeled_object_id,
        modeled_role=modeled_role,
        pcb_total_thickness_mm=pcb_total_thickness_mm,
        copper_thickness_mm=copper_thickness_mm,
        ferrite_set_count=ferrite_set_count,
        turn_count_range=turn_count_range,
        metal_fill_factor_range=metal_fill_factor_range,
        radiation_margin_mm=radiation_margin_mm,
        extra_modeled_lines=extra_modeled_lines,
    ).replace(
        '[[non_model_objects]]\n'
        'id = "tx_region"\n'
        'kind = "tx_region"\n'
        'primitive = "box"\n'
        'present = true\n'
        'non_model = true\n'
        'material = "vacuum"\n'
        'plane = "XY"\n'
        'origin_xyz = [0.0, -140.0, 0.0]\n'
        'size_xyz = [160.0, 280.0, 90.0]',
        '[[non_model_objects]]\n'
        'id = "tx_region"\n'
        'kind = "tx_region"\n'
        'primitive = "box"\n'
        'present = true\n'
        'non_model = true\n'
        'material = "vacuum"\n'
        'plane = "YZ"\n'
        'origin_xyz = [0.0, -140.0, 0.0]\n'
        'size_xyz = [160.0, 280.0, 90.0]',
        1,
    )


def _tx_rect_void_spec_text(*, terminal_path: str = "A_cw_to_a") -> str:
    return _tx_rect_void_spec_text_with_layer_count(terminal_path=terminal_path, layer_count=1)


def _tx_rect_void_spec_text_with_layer_count(*, terminal_path: str = "A_cw_to_a", layer_count: int = 1) -> str:
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.tx_rect_void_coil.step.v1"
runtime_compatible = false

[design]
units = "mm"

[manufacturing]
pcb_thickness_mm = 1.6
copper_thickness_mm = 0.1

[tx_coil.outer_x_mm]
range = {_range(False, 50.0, 50.0, 1)}
[tx_coil.outer_y_mm]
range = {_range(False, 60.0, 60.0, 1)}
[tx_coil.turn_count]
range = {_range(True, 2.0, 2.0, 1)}
[tx_coil.layer_count]
range = {_range(True, float(layer_count), float(layer_count), 1)}
[tx_coil.layer_gap_mm]
range = {_range(False, 2.0, 2.0, 1)}
[tx_coil.terminal_stub_length_mm]
range = {_range(False, 5.0, 5.0, 1)}
[tx_coil.void_x_over_outer_x]
range = {_range(False, 0.3, 0.3, 1)}
[tx_coil.void_y_over_outer_y]
range = {_range(False, 0.3, 0.3, 1)}
[tx_coil.void_center_x_over_outer_x]
range = {_range(False, 0.0, 0.0, 1)}
[tx_coil.void_center_y_over_outer_y]
range = {_range(False, 0.0, 0.0, 1)}
[tx_coil.margin_ratio]
range = {_range(False, 0.05, 0.05, 1)}
[tx_coil.metal_fill_factor]
range = {_range(False, 0.5, 0.5, 1)}
[tx_coil.terminal_path]
value = "{terminal_path}"
""".strip()


def _write_spec(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "type2_fixed.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _single_layer_example_text(source_toml: Path) -> str:
    return source_toml.read_text(encoding="utf-8").replace(
        "[modeled_objects.layer_count]\nrange = [true, 2, 2, 1]",
        "[modeled_objects.layer_count]\nrange = [true, 1, 1, 1]",
        1,
    )


def _body_bbox(step_path: Path, *, label: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    shapes_by_label = _step_shapes_by_label(step_path)
    matches = [shape for shape_label, shape in shapes_by_label.items() if shape_label == label]
    assert len(matches) == 1
    bbox = matches[0].bounding_box()
    return ((bbox.min.X, bbox.min.Y, bbox.min.Z), (bbox.max.X, bbox.max.Y, bbox.max.Z))


def _iter_shape_tree(shape: bd.Shape) -> tuple[bd.Shape, ...]:
    descendants: list[bd.Shape] = [shape]
    for child in shape.children:
        descendants.extend(_iter_shape_tree(cast(bd.Shape, child)))
    return tuple(descendants)


def _step_shapes_by_label(step_path: Path) -> dict[str, bd.Shape]:
    imported_scene = bd.import_step(step_path)
    top_level_children = tuple(imported_scene.children)
    roots = top_level_children if len(top_level_children) != 0 else (cast(bd.Shape, imported_scene),)
    shapes_by_label: dict[str, bd.Shape] = {}
    for root in roots:
        for shape in _iter_shape_tree(cast(bd.Shape, root)):
            if shape.label == "" or shape.label == "SOLID":
                continue
            if shape.label in shapes_by_label:
                raise AssertionError(f"duplicate STEP label found during recursive scan: {shape.label}")
            shapes_by_label[shape.label] = shape
    return shapes_by_label


def _plate_stack_top_level_expected_body_names(
    *,
    role: Literal["tx_plate_stack", "rx_plate_stack"],
    ferrite_set_count: int,
    turn_count: int,
    pcb_total_thickness_mm: float,
) -> tuple[str, ...]:
    expected_names = expected_plate_stack_body_names(
        role=role,
        ferrite_set_count=ferrite_set_count,
        turn_count=turn_count,
        pcb_total_thickness_mm=pcb_total_thickness_mm,
    )
    expected_groups = (
        _tx_plate_stack_expected_body_groups(ferrite_set_count=ferrite_set_count)
        if role == "tx_plate_stack"
        else _rx_plate_stack_expected_body_groups(ferrite_set_count=ferrite_set_count)
    )
    grouped_member_names = {
        member_name
        for group_entry in expected_groups
        for member_name in group_entry["member_body_names"]
    }
    return tuple(
        [
            *(name for name in expected_names if name not in grouped_member_names),
            *(group_entry["group_name"] for group_entry in expected_groups),
        ]
    )


def _tx_wall_expected_body_names(*, repeat_count: int) -> tuple[str, ...]:
    if repeat_count == 0:
        return ()
    return (
        "tx_wall_ferrite_u0",
        "tx_wall_pet_psa_u0",
        "tx_wall_air_u0",
    )


def _rx_underlay_expected_body_names(*, repeat_count: int) -> tuple[str, ...]:
    if repeat_count == 0:
        return ()
    return (
        "under_rx_ferrite_u0",
        "under_rx_pet_psa_u0",
        "under_rx_air_u0",
    )


def _tx_expected_body_names(
    *,
    pcb_layer_count: int,
    underlay_repeat_count: int,
    wall_parallel_stack_present: bool,
) -> tuple[str, ...]:
    names = [f"tx_pcb_l{index}" for index in range(pcb_layer_count)]
    if pcb_layer_count > 1:
        names.append("tx_copper_stack")
    else:
        names.append("tx_copper_l0")
    if wall_parallel_stack_present and underlay_repeat_count > 0:
        names.extend(_tx_wall_expected_body_names(repeat_count=underlay_repeat_count))
    return tuple(names)


def _rx_expected_body_names(*, underlay_repeat_count: int) -> tuple[str, ...]:
    names = ["rx_pcb_l0", "rx_copper_l0"]
    names.extend(_rx_underlay_expected_body_names(repeat_count=underlay_repeat_count))
    return tuple(names)


def _ferrite_group_name_for_modeled_role(
    *,
    role: Literal["tx_single_coil", "rx_single_coil", "tx_plate_stack", "rx_plate_stack"],
) -> str:
    if role in ("tx_single_coil", "tx_plate_stack"):
        return _TX_FERRITE_GROUP_NAME
    if role in ("rx_single_coil", "rx_plate_stack"):
        return _RX_FERRITE_GROUP_NAME
    raise RuntimeError(f"unsupported ferrite grouping role in test helper: {role}")


def _expected_ferrite_body_groups(
    *,
    role: Literal["tx_single_coil", "rx_single_coil", "tx_plate_stack", "rx_plate_stack"],
    member_body_names: tuple[str, ...],
) -> tuple[ExportedBodyGroup, ...]:
    if len(member_body_names) == 0:
        return ()
    return (
        {
            "group_name": _ferrite_group_name_for_modeled_role(role=role),
            "member_body_names": member_body_names,
        },
    )


def _tx_expected_body_groups(
    *,
    underlay_repeat_count: int,
    wall_parallel_stack_present: bool,
) -> tuple[ExportedBodyGroup, ...]:
    tx_wall_member_names = (
        _tx_wall_expected_body_names(repeat_count=underlay_repeat_count)
        if wall_parallel_stack_present and underlay_repeat_count > 0
        else ()
    )
    return _expected_ferrite_body_groups(
        role="tx_single_coil",
        member_body_names=tx_wall_member_names,
    )


def _rx_expected_body_groups(*, underlay_repeat_count: int) -> tuple[ExportedBodyGroup, ...]:
    return _expected_ferrite_body_groups(
        role="rx_single_coil",
        member_body_names=_rx_underlay_expected_body_names(repeat_count=underlay_repeat_count),
    )


def _rx_plate_stack_expected_body_names(
    *,
    ferrite_set_count: int,
    turn_count: int,
    pcb_total_thickness_mm: float = _PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
) -> tuple[str, ...]:
    return expected_plate_stack_body_names(
        role="rx_plate_stack",
        ferrite_set_count=ferrite_set_count,
        turn_count=turn_count,
        pcb_total_thickness_mm=pcb_total_thickness_mm,
    )


def _tx_plate_stack_expected_body_names(
    *,
    ferrite_set_count: int,
    turn_count: int,
    pcb_total_thickness_mm: float = _PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
) -> tuple[str, ...]:
    return expected_plate_stack_body_names(
        role="tx_plate_stack",
        ferrite_set_count=ferrite_set_count,
        turn_count=turn_count,
        pcb_total_thickness_mm=pcb_total_thickness_mm,
    )


def _tx_plate_stack_expected_body_groups(*, ferrite_set_count: int = 10) -> tuple[ExportedBodyGroup, ...]:
    assert ferrite_set_count >= 1
    member_body_names = (
        "tx_stack_pet_psa",
        "tx_stack_ferrite",
        "tx_stack_air",
    )
    return _expected_ferrite_body_groups(
        role="tx_plate_stack",
        member_body_names=member_body_names,
    )


def _rx_plate_stack_expected_body_groups(*, ferrite_set_count: int = 10) -> tuple[ExportedBodyGroup, ...]:
    assert ferrite_set_count >= 1
    member_body_names = (
        "rx_stack_pet_psa",
        "rx_stack_ferrite",
        "rx_stack_air",
    )
    return _expected_ferrite_body_groups(
        role="rx_plate_stack",
        member_body_names=member_body_names,
    )


def _normalized_body_groups(raw_groups: object) -> list[dict[str, object]]:
    assert isinstance(raw_groups, Sequence)
    assert not isinstance(raw_groups, (str, bytes))
    normalized_groups: list[dict[str, object]] = []
    for raw_group in raw_groups:
        assert isinstance(raw_group, dict)
        raw_group_name = raw_group["group_name"]
        raw_member_body_names = raw_group["member_body_names"]
        assert isinstance(raw_group_name, str)
        assert isinstance(raw_member_body_names, Sequence)
        assert not isinstance(raw_member_body_names, (str, bytes))
        normalized_groups.append(
            {
                "group_name": raw_group_name,
                "member_body_names": list(raw_member_body_names),
            }
        )
    return normalized_groups


def _seed_for_underlay_repeat_count(spec_path: Path, *, object_id: str, expected_repeat_count: int) -> int:
    spec = load_type2_step_spec(spec_path)
    modeled_spec = next(entry for entry in spec.modeled_objects if entry.object_id == object_id)
    assert modeled_spec.role in ("tx_single_coil", "rx_single_coil")
    for seed in range(512):
        if resolve_modeled_underlay_repeat_count(cast(ModeledSingleCoilSpec, modeled_spec), seed=seed) == expected_repeat_count:
            return seed
    raise RuntimeError(
        "failed to find deterministic seed for requested underlay repeat count "
        f"(object_id={object_id}, expected_repeat_count={expected_repeat_count})"
    )


def _assert_zero_intersection_volume(first: object, second: object) -> None:
    assert isinstance(first, bd.Shape)
    assert isinstance(second, bd.Shape)
    shared_shape = first.intersect(second)
    if shared_shape is None:
        return
    assert isinstance(shared_shape, bd.Shape)
    assert sum(solid.volume for solid in shared_shape.solids()) == pytest.approx(0.0, abs=1e-9)


def _assert_plate_stack_bridge_non_overlap(
    *,
    scene_shapes_by_label: dict[str, bd.Shape],
    prefix: Literal["tx", "rx"],
    turn_count: int,
    ferrite_set_count: int,
) -> None:
    assert ferrite_set_count >= 1
    bridge_labels = tuple(f"{prefix}_bridge_s{index}" for index in range((2 * turn_count) - 2))
    copper_labels = (
        *(f"{prefix}_copper_wall_t{index}" for index in range(turn_count)),
        *(f"{prefix}_copper_coil_t{index}" for index in range(turn_count - 1)),
    )
    slab_labels = (
        f"{prefix}_pcb_wall",
        f"{prefix}_pcb_coil",
        f"{prefix}_stack_pet_psa",
        f"{prefix}_stack_ferrite",
        f"{prefix}_stack_air",
    )
    for bridge_label in bridge_labels:
        bridge_shape = scene_shapes_by_label[bridge_label]
        for adjacent_copper_label in copper_labels:
            _assert_zero_intersection_volume(bridge_shape, scene_shapes_by_label[adjacent_copper_label])
        for notched_slab_label in slab_labels:
            _assert_zero_intersection_volume(bridge_shape, scene_shapes_by_label[notched_slab_label])
    max_edge_bridge_labels = tuple(f"{prefix}_bridge_s{index}" for index in range(0, (2 * turn_count) - 2, 2))
    min_edge_bridge_labels = tuple(f"{prefix}_bridge_s{index}" for index in range(1, (2 * turn_count) - 2, 2))
    for labels_for_one_edge in (max_edge_bridge_labels, min_edge_bridge_labels):
        for first_index in range(len(labels_for_one_edge)):
            for second_index in range(first_index + 1, len(labels_for_one_edge)):
                _assert_zero_intersection_volume(
                    scene_shapes_by_label[labels_for_one_edge[first_index]],
                    scene_shapes_by_label[labels_for_one_edge[second_index]],
                )


def _assert_plate_stack_united_ferrite_family_contract(
    *,
    scene_shapes_by_label: dict[str, bd.Shape],
    prefix: Literal["tx", "rx"],
) -> None:
    group_label = _TX_FERRITE_GROUP_NAME if prefix == "tx" else _RX_FERRITE_GROUP_NAME
    expected_member_labels = (
        f"{prefix}_stack_pet_psa",
        f"{prefix}_stack_ferrite",
        f"{prefix}_stack_air",
    )
    group_shape = scene_shapes_by_label[group_label]
    assert type(group_shape).__name__ == "Compound"
    assert tuple(child.label for child in group_shape.children) == expected_member_labels
    for member_label in expected_member_labels:
        member_shape = scene_shapes_by_label[member_label]
        assert type(member_shape).__name__ == "Solid"
        assert len(tuple(member_shape.solids())) == 1
    assert all(not label.startswith(f"{prefix}_stack_pet_psa_u") for label in scene_shapes_by_label)
    assert all(not label.startswith(f"{prefix}_stack_ferrite_u") for label in scene_shapes_by_label)
    assert all(not label.startswith(f"{prefix}_stack_air_u") for label in scene_shapes_by_label)


def _single_coil_placement_offset_from_local_bounds(
    *,
    owner_origin_xyz: tuple[float, float, float],
    owner_size_xyz: tuple[float, float, float],
    local_bounds_min_xyz: tuple[float, float, float],
    local_size_xyz: tuple[float, float, float],
    profile: SingleCoilProfile,
) -> tuple[float, float, float]:
    plane = profile.plane
    world_size_xyz = profile.world_size(local_size_xyz)
    world_min_delta = profile.world_delta(local_bounds_min_xyz)
    if plane == "XY":
        target_world_min_xyz = (
            owner_origin_xyz[0],
            owner_origin_xyz[1] + (owner_size_xyz[1] - world_size_xyz[1]) / 2.0,
            owner_origin_xyz[2] + owner_size_xyz[2] - world_size_xyz[2],
        )
    else:
        target_world_min_xyz = (
            owner_origin_xyz[0] + owner_size_xyz[0] - world_size_xyz[0],
            owner_origin_xyz[1] + (owner_size_xyz[1] - world_size_xyz[1]) / 2.0,
            owner_origin_xyz[2],
        )
    return (
        target_world_min_xyz[0] - world_min_delta[0],
        target_world_min_xyz[1] - world_min_delta[1],
        target_world_min_xyz[2] - world_min_delta[2],
    )


def _transform_box_to_world(
    *,
    origin_xyz: tuple[float, float, float],
    size_xyz: tuple[float, float, float],
    frame_origin_xyz: tuple[float, float, float],
    profile: SingleCoilProfile,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    return (
        profile.world_point(origin_xyz, frame_origin_xyz=frame_origin_xyz),
        profile.world_size(size_xyz),
    )


def _synthetic_tx_bus_owner_boxes(
    *,
    local_boxes: tuple[BoxSpec, ...],
) -> tuple[BoxSpec, BoxSpec]:
    terminal_stub_boxes = tuple(box for box in local_boxes if box.feature == "terminal_stub")

    def _owner_box(terminal_column: str) -> BoxSpec:
        matching_stub_boxes = tuple(
            box for box in terminal_stub_boxes if box.label.endswith(f"_stub_{terminal_column}")
        )
        assert matching_stub_boxes
        assert len(matching_stub_boxes) * 2 == len(terminal_stub_boxes)
        min_x = min(box.origin_xyz[0] for box in matching_stub_boxes)
        min_y = min(box.origin_xyz[1] for box in matching_stub_boxes)
        min_z = min(box.origin_xyz[2] for box in matching_stub_boxes)
        max_x = max(box.origin_xyz[0] + box.size_xyz[0] for box in matching_stub_boxes)
        max_y = max(box.origin_xyz[1] + box.size_xyz[1] for box in matching_stub_boxes)
        max_z = max(box.origin_xyz[2] + box.size_xyz[2] for box in matching_stub_boxes)
        return BoxSpec(
            label=f"tx_copper_bus_{terminal_column}",
            role="copper",
            feature="vertical_bus",
            layer_index=0,
            origin_xyz=(min_x, min_y, min_z),
            size_xyz=(max_x - min_x, max_y - min_y, max_z - min_z),
        )

    return (_owner_box("start"), _owner_box("end"))


def _world_terminal_stub_boxes(
    *,
    source_toml: Path,
    object_id: str,
    seed: int,
) -> tuple[tuple[tuple[float, float, float], tuple[float, float, float]], ...]:
    type2_spec = load_type2_step_spec(source_toml)
    modeled_spec = next(entry for entry in type2_spec.modeled_objects if entry.object_id == object_id)
    assert modeled_spec.role in ("tx_single_coil", "rx_single_coil")
    profile = profile_for_modeled_role(cast(Literal["tx_single_coil", "rx_single_coil"], modeled_spec.role))
    owner_spec = next(spec for spec in type2_spec.non_model_objects if spec.object_id == profile.placement_owner_id)
    with tempfile.TemporaryDirectory() as temp_dir:
        tx_rect_void_toml_path = Path(temp_dir) / f"{object_id}.toml"
        tx_rect_void_toml_path.write_text(render_tx_rect_void_toml(cast(ModeledSingleCoilSpec, modeled_spec)), encoding="utf-8")
        tx_rect_void_spec = load_tx_rect_void_spec(tx_rect_void_toml_path)
        realized = realize_tx_rect_void_spec(tx_rect_void_spec, seed=seed, profile=profile)
    local_boxes = build_tx_rect_void_box_specs(realized, profile=profile)
    local_bounds_min_xyz, _local_bounds_max_xyz, local_size_xyz = modeled_body_bounds_from_boxes(local_boxes)
    frame_origin_xyz = _single_coil_placement_offset_from_local_bounds(
        owner_origin_xyz=owner_spec.origin_xyz,
        owner_size_xyz=owner_spec.size_xyz,
        local_bounds_min_xyz=local_bounds_min_xyz,
        local_size_xyz=local_size_xyz,
        profile=profile,
    )
    if profile.role == "tx_single_coil":
        terminal_stub_boxes = _synthetic_tx_bus_owner_boxes(local_boxes=local_boxes)
    else:
        terminal_stub_boxes = tuple(box for box in local_boxes if box.feature == "terminal_stub")
    return tuple(
        _transform_box_to_world(
            origin_xyz=box.origin_xyz,
            size_xyz=box.size_xyz,
            frame_origin_xyz=frame_origin_xyz,
            profile=profile,
        )
        for box in terminal_stub_boxes
    )


def _shape_vertices(step_path: Path, *, label: str) -> tuple[tuple[float, float, float], ...]:
    shapes_by_label = _step_shapes_by_label(step_path)
    matches = [shape for shape_label, shape in shapes_by_label.items() if shape_label == label]
    assert len(matches) == 1
    shape = cast(bd.Shape, matches[0])
    assert hasattr(shape, "vertices"), f"shape does not expose vertices(): {label}"
    vertices_method = getattr(shape, "vertices")
    assert callable(vertices_method), f"shape.vertices must be callable: {label}"
    unique_vertices: dict[tuple[float, float, float], tuple[float, float, float]] = {}
    for raw_vertex in cast(list[object], vertices_method()):
        assert hasattr(raw_vertex, "X"), f"vertex must expose X: {label}"
        assert hasattr(raw_vertex, "Y"), f"vertex must expose Y: {label}"
        assert hasattr(raw_vertex, "Z"), f"vertex must expose Z: {label}"
        vertex_x = getattr(raw_vertex, "X")
        vertex_y = getattr(raw_vertex, "Y")
        vertex_z = getattr(raw_vertex, "Z")
        assert isinstance(vertex_x, float), f"vertex.X must be float: {label}"
        assert isinstance(vertex_y, float), f"vertex.Y must be float: {label}"
        assert isinstance(vertex_z, float), f"vertex.Z must be float: {label}"
        rounded = (round(vertex_x, 8), round(vertex_y, 8), round(vertex_z, 8))
        if rounded not in unique_vertices:
            unique_vertices[rounded] = (vertex_x, vertex_y, vertex_z)
    return tuple(unique_vertices.values())


def _terminal_stub_bottom_face_square_plane_vertices(
    *,
    terminal_stub_boxes: tuple[tuple[tuple[float, float, float], tuple[float, float, float]], ...],
    plane: str,
) -> tuple[tuple[tuple[tuple[float, float], ...], float], tuple[tuple[tuple[float, float], ...], float]]:
    assert len(terminal_stub_boxes) == 2
    boxes_by_plane: list[tuple[tuple[tuple[float, float], ...], float]] = []
    for box_origin_xyz, box_size_xyz in terminal_stub_boxes:
        if plane == "XY":
            square_side_a = box_size_xyz[0]
            square_side_b = box_size_xyz[1]
            bottom_plane_coordinate = box_origin_xyz[2]
            plane_vertices = (
                (box_origin_xyz[0], box_origin_xyz[1]),
                (box_origin_xyz[0] + box_size_xyz[0], box_origin_xyz[1]),
                (box_origin_xyz[0] + box_size_xyz[0], box_origin_xyz[1] + box_size_xyz[1]),
                (box_origin_xyz[0], box_origin_xyz[1] + box_size_xyz[1]),
            )
        else:
            square_side_a = box_size_xyz[1]
            square_side_b = box_size_xyz[2]
            bottom_plane_coordinate = box_origin_xyz[0]
            plane_vertices = (
                (box_origin_xyz[1], box_origin_xyz[2]),
                (box_origin_xyz[1] + box_size_xyz[1], box_origin_xyz[2]),
                (box_origin_xyz[1] + box_size_xyz[1], box_origin_xyz[2] + box_size_xyz[2]),
                (box_origin_xyz[1], box_origin_xyz[2] + box_size_xyz[2]),
            )
        assert square_side_a > 0.0
        assert square_side_b > 0.0
        assert square_side_a == pytest.approx(square_side_b, abs=1e-8)
        boxes_by_plane.append((plane_vertices, bottom_plane_coordinate))
    first_box, second_box = boxes_by_plane
    assert first_box[1] == pytest.approx(second_box[1], abs=1e-8)
    return (first_box, second_box)


def _stub_centerline_perpendicular_distance(
    *,
    point_xy: tuple[float, float],
    first_center_xy: tuple[float, float],
    second_center_xy: tuple[float, float],
) -> float:
    delta_x = second_center_xy[0] - first_center_xy[0]
    delta_y = second_center_xy[1] - first_center_xy[1]
    denominator = math.hypot(delta_x, delta_y)
    assert denominator > 1e-12
    numerator = abs(
        delta_x * (first_center_xy[1] - point_xy[1])
        - (first_center_xy[0] - point_xy[0]) * delta_y
    )
    return numerator / denominator


def _widest_stub_bottom_face_diagonal_vertices(
    *,
    terminal_stub_boxes: tuple[tuple[tuple[float, float, float], tuple[float, float, float]], ...],
    plane: str,
) -> tuple[tuple[float, float, float], ...]:
    first_box, second_box = _terminal_stub_bottom_face_square_plane_vertices(
        terminal_stub_boxes=terminal_stub_boxes,
        plane=plane,
    )
    first_plane_vertices, first_bottom_plane_coordinate = first_box
    second_plane_vertices, second_bottom_plane_coordinate = second_box
    first_center_xy = (
        sum(point_xy[0] for point_xy in first_plane_vertices) / 4.0,
        sum(point_xy[1] for point_xy in first_plane_vertices) / 4.0,
    )
    second_center_xy = (
        sum(point_xy[0] for point_xy in second_plane_vertices) / 4.0,
        sum(point_xy[1] for point_xy in second_plane_vertices) / 4.0,
    )

    def _selected_diagonal(
        plane_vertices: tuple[tuple[float, float], ...],
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        best_score = -1.0
        best_diagonal: tuple[tuple[float, float], tuple[float, float]] | None = None
        best_key: tuple[tuple[float, float], tuple[float, float]] | None = None
        for first_index, second_index in ((0, 2), (1, 3)):
            diagonal_vertices = (plane_vertices[first_index], plane_vertices[second_index])
            score = sum(
                _stub_centerline_perpendicular_distance(
                    point_xy=point_xy,
                    first_center_xy=first_center_xy,
                    second_center_xy=second_center_xy,
                )
                for point_xy in diagonal_vertices
            )
            sorted_vertices = sorted(diagonal_vertices)
            candidate_key = (sorted_vertices[0], sorted_vertices[1])
            if (
                score > best_score + 1e-9
                or (abs(score - best_score) <= 1e-9 and (best_key is None or candidate_key < best_key))
            ):
                best_score = score
                best_diagonal = diagonal_vertices
                best_key = candidate_key
        assert best_diagonal is not None
        return best_diagonal

    diagonal_vertices: list[tuple[float, float, float]] = []
    for plane_vertices, bottom_plane_coordinate in (
        (first_plane_vertices, first_bottom_plane_coordinate),
        (second_plane_vertices, second_bottom_plane_coordinate),
    ):
        selected_diagonal = _selected_diagonal(plane_vertices)
        for point_u, point_v in selected_diagonal:
            if plane == "XY":
                diagonal_vertices.append((point_u, point_v, bottom_plane_coordinate))
            else:
                diagonal_vertices.append((bottom_plane_coordinate, point_u, point_v))
    return tuple(diagonal_vertices)


def _assert_sheet_vertices_bridge_stub_bottom_face_diagonals(
    *,
    sheet_vertices: tuple[tuple[float, float, float], ...],
    terminal_stub_boxes: tuple[tuple[tuple[float, float, float], tuple[float, float, float]], ...],
    plane: str,
) -> None:
    assert len(sheet_vertices) == 4
    expected_vertices = _widest_stub_bottom_face_diagonal_vertices(
        terminal_stub_boxes=terminal_stub_boxes,
        plane=plane,
    )
    if plane == "XY":
        plane_coordinates = tuple(vertex[2] for vertex in sheet_vertices)
    else:
        plane_coordinates = tuple(vertex[0] for vertex in sheet_vertices)
    assert max(plane_coordinates) - min(plane_coordinates) == pytest.approx(0.0, abs=1e-8)
    assert {
        (round(vertex[0], 8), round(vertex[1], 8), round(vertex[2], 8))
        for vertex in sheet_vertices
    } == {
        (round(vertex[0], 8), round(vertex[1], 8), round(vertex[2], 8))
        for vertex in expected_vertices
    }


def test_load_example_type2_toml_parses_expected_registry_shape() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_fixed.toml"
    spec = load_type2_step_spec(source_toml)

    assert spec.simulation.radiation_margin_mm == pytest.approx(3500.0)
    assert spec.outputs == type1_outputs_spec()
    assert len(spec.non_model_objects) == 6
    assert len(spec.modeled_objects) == 2
    modeled_by_id = {entry.object_id: entry for entry in spec.modeled_objects}
    tx_entry = modeled_by_id["tx_plate_stack"]
    rx_entry = modeled_by_id["rx_plate_stack"]
    assert tx_entry.role == "tx_plate_stack"
    assert tx_entry.pcb_total_thickness_mm == pytest.approx(_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM)
    assert tx_entry.copper_thickness_mm == pytest.approx(0.035)
    assert tx_entry.ferrite_set_count == 10
    assert tx_entry.turn_count.start == pytest.approx(3.0)
    assert tx_entry.turn_count.count == 1
    assert tx_entry.metal_fill_factor.start == pytest.approx(0.4)
    assert rx_entry.role == "rx_plate_stack"
    assert rx_entry.pcb_total_thickness_mm == pytest.approx(_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM)
    assert rx_entry.copper_thickness_mm == pytest.approx(0.1)
    assert rx_entry.ferrite_set_count == 10
    assert rx_entry.turn_count.start == pytest.approx(3.0)
    assert rx_entry.metal_fill_factor.start == pytest.approx(0.4)


def test_load_sweep_example_type2_toml_parses_expected_sampling_contract() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_sweep.toml"
    spec = load_type2_step_spec(source_toml)

    assert spec.simulation.radiation_margin_mm == pytest.approx(3500.0)
    assert spec.outputs == type1_outputs_spec()
    assert len(spec.non_model_objects) == 6
    assert len(spec.modeled_objects) == 2
    modeled_by_id = {entry.object_id: entry for entry in spec.modeled_objects}
    tx_entry = modeled_by_id["tx_plate_stack"]
    rx_entry = modeled_by_id["rx_plate_stack"]
    assert tx_entry.role == "tx_plate_stack"
    assert tx_entry.pcb_total_thickness_mm == pytest.approx(_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM)
    assert tx_entry.copper_thickness_mm == pytest.approx(0.035)
    assert tx_entry.ferrite_set_count == 10
    assert tx_entry.turn_count.start == pytest.approx(2.0)
    assert tx_entry.turn_count.end == pytest.approx(25.0)
    assert tx_entry.turn_count.count == 24
    assert tx_entry.metal_fill_factor.start == pytest.approx(0.2)
    assert tx_entry.metal_fill_factor.end == pytest.approx(0.6)
    assert tx_entry.metal_fill_factor.count == 15
    assert rx_entry.role == "rx_plate_stack"
    assert rx_entry.pcb_total_thickness_mm == pytest.approx(_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM)
    assert rx_entry.copper_thickness_mm == pytest.approx(0.1)
    assert rx_entry.ferrite_set_count == 10
    assert rx_entry.turn_count.start == pytest.approx(2.0)
    assert rx_entry.turn_count.end == pytest.approx(25.0)
    assert rx_entry.turn_count.count == 24
    assert rx_entry.metal_fill_factor.start == pytest.approx(0.2)
    assert rx_entry.metal_fill_factor.end == pytest.approx(0.6)
    assert rx_entry.metal_fill_factor.count == 15


def test_load_type2_step_spec_rejects_duplicate_object_id(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(modeled_object_id="floor"))

    with pytest.raises(ValueError, match=r"duplicate object id: floor"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_unsupported_modeled_role(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(modeled_role="bad_single_coil"))

    with pytest.raises(ValueError, match=r"unsupported modeled object role: bad_single_coil"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_parses_tx_plate_stack_contract(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_tx_plate_stack_spec_text())

    spec = load_type2_step_spec(toml_path)

    assert len(spec.modeled_objects) == 1
    tx_entry = spec.modeled_objects[0]
    assert tx_entry.object_id == "tx_plate_stack"
    assert tx_entry.role == "tx_plate_stack"
    assert tx_entry.pcb_total_thickness_mm == pytest.approx(_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM)
    assert tx_entry.copper_thickness_mm == pytest.approx(0.1)
    assert tx_entry.ferrite_set_count == 10
    assert tx_entry.turn_count.start == pytest.approx(3.0)
    assert tx_entry.metal_fill_factor.start == pytest.approx(0.4)


def test_load_type2_step_spec_rejects_legacy_type2_schema_id(tmp_path: Path) -> None:
    toml_text = _type2_rx_plate_stack_spec_text().replace("peetsfea.type2.step.v2", "peetsfea.type2.step.v1", 1)
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(ValueError, match=r"schema_id must be 'peetsfea\.type2\.step\.v2'"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_tx_plate_stack_object_id_mismatch(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_tx_plate_stack_spec_text(modeled_object_id="tx_rect_void_coil"),
    )

    with pytest.raises(ValueError, match=r"prototype modeled object_id must be 'tx_plate_stack'"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_tx_plate_stack_with_coil_only_fields(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_tx_plate_stack_spec_text(
            extra_modeled_lines=(
                "[modeled_objects.outer_x_mm]",
                f"range = {_range(False, 2.0, 2.0, 1)}",
            ),
        ),
    )

    with pytest.raises(ValueError, match=r"contains unsupported keys for tx_plate_stack"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_tx_plate_stack_when_pcb_budget_is_not_larger_than_copper(
    tmp_path: Path,
) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_tx_plate_stack_spec_text(
            pcb_total_thickness_mm=0.1,
            copper_thickness_mm=0.1,
        ),
    )

    with pytest.raises(ValueError, match=r"pcb_total_thickness_mm must be > copper_thickness_mm"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_rx_plate_stack_object_id_mismatch(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_rx_plate_stack_spec_text(modeled_object_id="rx_rect_void_coil"),
    )

    with pytest.raises(ValueError, match=r"prototype modeled object_id must be 'rx_plate_stack'"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_rx_plate_stack_with_coil_only_fields(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_rx_plate_stack_spec_text(
            extra_modeled_lines=(
                "[modeled_objects.outer_x_mm]",
                f"range = {_range(False, 2.0, 2.0, 1)}",
            ),
        ),
    )

    with pytest.raises(ValueError, match=r"contains unsupported keys for rx_plate_stack"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_rx_plate_stack_when_pcb_budget_is_not_larger_than_copper(
    tmp_path: Path,
) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_rx_plate_stack_spec_text(
            pcb_total_thickness_mm=0.1,
            copper_thickness_mm=0.1,
        ),
    )

    with pytest.raises(ValueError, match=r"pcb_total_thickness_mm must be > copper_thickness_mm"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_plate_stack_turn_count_less_than_two(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_rx_plate_stack_spec_text(turn_count_range=_range(True, 0.0, 0.0, 1)),
    )

    with pytest.raises(ValueError, match=r"turn_count must realize to integers >= 2"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_plate_stack_metal_fill_factor_above_supported_range(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_rx_plate_stack_spec_text(metal_fill_factor_range=_range(False, 0.7, 0.7, 1)),
    )

    with pytest.raises(ValueError, match=r"metal_fill_factor must realize to values > 0 and <= 0.6"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_plate_stack_with_removed_shoe_depth_field(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_rx_plate_stack_spec_text(
            extra_modeled_lines=(
                "[modeled_objects.shoe_depth_mm]",
                "range = [false, 7.0, 7.0, 1]",
            )
        ),
    )

    with pytest.raises(ValueError, match=r"contains unsupported keys for rx_plate_stack"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_missing_required_modeled_field(tmp_path: Path) -> None:
    toml_text = _type2_spec_text().replace('[modeled_objects.terminal_path]\n    value = "A_cw_to_a"', "", 1)
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(ValueError, match=r"modeled_objects\[0\] is missing required key 'terminal_path'"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_non_canonical_tx_underlay_repeat_count(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(underlay_repeat_count_range=_range(True, 0.0, 6.0, 4)),
    )

    with pytest.raises(
        ValueError,
        match=r"modeled_objects\[0\]\.underlay_repeat_count\.range must be canonical \[true, 0, 8, 5\] or fixed \[true, n, n, 1\]",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_non_canonical_rx_underlay_repeat_count(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="rx_rect_void_coil",
            modeled_role="rx_single_coil",
            underlay_repeat_count_range=_range(True, 0.0, 6.0, 4),
        ),
    )

    with pytest.raises(
        ValueError,
        match=r"modeled_objects\[0\]\.underlay_repeat_count\.range must be canonical \[true, 0, 8, 5\] or fixed \[true, n, n, 1\]",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_accepts_fixed_underlay_contract_values(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            underlay_repeat_count_range=_range(True, 6.0, 6.0, 1),
            underlay_gap_range=_range(False, 4.0, 4.0, 1),
            wall_parallel_stack_present_range=_range(True, 1.0, 1.0, 1),
        ),
    )

    spec = load_type2_step_spec(toml_path)
    tx_entry = next(entry for entry in spec.modeled_objects if entry.object_id == "tx_rect_void_coil")
    assert tx_entry.role == "tx_single_coil"

    assert resolve_modeled_underlay_repeat_count(tx_entry, seed=0) == 6
    assert resolve_modeled_underlay_gap_mm(tx_entry, seed=0) == pytest.approx(4.0)
    assert resolve_modeled_wall_parallel_stack_present(tx_entry, seed=0) is True


def test_load_type2_step_spec_rejects_rx_underlay_gap_mm(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="rx_rect_void_coil",
            modeled_role="rx_single_coil",
            underlay_gap_range=_range(False, 1.0, 10.0, 4),
        ),
    )

    with pytest.raises(ValueError, match=r"modeled_objects\[0\]\.underlay_gap_mm is unsupported for rx_single_coil"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_non_canonical_tx_wall_parallel_stack_present(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(wall_parallel_stack_present_range=_range(True, 0.0, 2.0, 3)),
    )

    with pytest.raises(
        ValueError,
        match=r"modeled_objects\[0\]\.wall_parallel_stack_present\.range must be canonical \[true, 0, 1, 2\] or fixed \[true, b, b, 1\]",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_rx_wall_parallel_stack_present(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="rx_rect_void_coil",
            modeled_role="rx_single_coil",
            wall_parallel_stack_present_range=_range(True, 0.0, 1.0, 2),
        ),
    )

    with pytest.raises(
        ValueError,
        match=r"modeled_objects\[0\]\.wall_parallel_stack_present is unsupported for rx_single_coil",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_missing_outputs(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _remove_outputs_block(_type2_spec_text()))

    with pytest.raises(ValueError, match=r"type2_fixed\.toml is missing required key 'outputs'"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_missing_required_outputs_key(tmp_path: Path) -> None:
    toml_text = _type2_spec_text().replace('report_name = "Output Variables Table1"\n', "", 1)
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(
        ValueError,
        match=r"type2_fixed\.toml\.outputs is missing required keys: \['report_name'\]",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_unsupported_outputs_key(tmp_path: Path) -> None:
    toml_text = _type2_spec_text().replace("[outputs]\n", '[outputs]\nextra = "nope"\n', 1)
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(
        ValueError,
        match=r"type2_fixed\.toml\.outputs contains unsupported keys: \['extra'\]",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_empty_outputs_variables(tmp_path: Path) -> None:
    outputs_header = "\n".join(
        (
            "[outputs]",
            'report_name = "Output Variables Table1"',
            'solution_name = "Setup1 : LastAdaptive"',
            'primary_sweep = "Freq"',
            'report_category = "Terminal Solution Data"',
            'plot_type = "Data Table"',
            "variables = []",
        )
    )
    toml_text = _remove_outputs_block(_type2_spec_text()).replace(
        "\n\n[[non_model_objects]]",
        f"\n\n{outputs_header}\n\n[[non_model_objects]]",
        1,
    )
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(ValueError, match=r"type2_fixed\.toml\.outputs\.variables must be non-empty"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_duplicate_output_variable_name(tmp_path: Path) -> None:
    toml_text = _type2_spec_text().replace('name = "Lrx_uH"', 'name = "Ltx_uH"', 1)
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(
        ValueError,
        match=r"type2_fixed\.toml\.outputs\.variables\[1\]\.name must be unique: Ltx_uH",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_invalid_output_variable_name(tmp_path: Path) -> None:
    toml_text = _type2_spec_text().replace('name = "Ltx_uH"', 'name = "1bad"', 1)
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(
        ValueError,
        match=r"type2_fixed\.toml\.outputs\.variables\[0\]\.name must match \^\[A-Za-z\]\[A-Za-z0-9_\]\*\$",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_missing_simulation_radiation_margin(tmp_path: Path) -> None:
    toml_text = "\n".join(
        line for line in _type2_spec_text().splitlines() if line != "radiation_margin_mm = 3500.0"
    )
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(
        ValueError,
        match=r"type2_fixed\.toml\.simulation is missing required keys: \['radiation_margin_mm'\]",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_non_positive_simulation_radiation_margin(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(radiation_margin_mm=0.0))

    with pytest.raises(ValueError, match=r"type2_fixed\.toml\.simulation\.radiation_margin_mm must be > 0"):
        load_type2_step_spec(toml_path)


def test_render_tx_rect_void_toml_omits_type2_underlay_fields_from_core_bridge(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text())
    spec = load_type2_step_spec(toml_path)
    modeled_spec = next(entry for entry in spec.modeled_objects if entry.object_id == "tx_rect_void_coil")
    assert modeled_spec.role == "tx_single_coil"

    rendered = render_tx_rect_void_toml(cast(ModeledSingleCoilSpec, modeled_spec))

    assert "underlay_repeat_count" not in rendered
    assert "underlay_gap_mm" not in rendered
    assert "wall_parallel_stack_present" not in rendered


def test_export_type2_step_artifacts_writes_single_scene_step_and_ledger(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_fixed.toml"
    type2_spec = load_type2_step_spec(source_toml)
    tx_modeled_spec = next(entry for entry in type2_spec.modeled_objects if entry.object_id == "tx_plate_stack")
    rx_modeled_spec = next(entry for entry in type2_spec.modeled_objects if entry.object_id == "rx_plate_stack")
    assert tx_modeled_spec.role == "tx_plate_stack"
    output_dir = tmp_path / "out"
    ledger_path = tmp_path / "out" / "type2_ledger.json"

    ledger = export_type2_step_artifacts(
        toml_path=source_toml,
        output_dir=output_dir,
        ledger_path=ledger_path,
        seed=0,
    )

    assert ledger_path.is_file()
    assert ledger_path.stat().st_size > 0
    scene_step_path = Path(ledger["scene_step_path"])
    assert scene_step_path.is_file()
    assert scene_step_path.stat().st_size > 0
    assert scene_step_path.name == "type2_scene.step"
    assert (output_dir / "type2_non_model_scene.step").exists() is False
    assert (output_dir / "type2_combined_preview.step").exists() is False
    assert (output_dir / "objects").exists() is False
    assert ledger["em_policy"] == {"radiation_margin_mm": 3500.0}
    assert ledger["outputs"] == type1_outputs_spec()
    assert len(ledger["non_model_objects"]) == 1
    assert len(ledger["modeled_objects"]) == 2
    non_model_entry = ledger["non_model_objects"][0]
    assert non_model_entry["object_id"] == "type2_non_model_scene"
    assert non_model_entry["role"] == "non_model_scene"
    assert non_model_entry["plane"] == "mixed"
    assert non_model_entry["member_object_ids"] == ("environment", "tx_region", "rx_region_max")
    member_objects = non_model_entry["member_objects"]
    assert len(member_objects) == 3
    environment_member = next(member for member in member_objects if member["object_id"] == "environment")
    assert environment_member["role"] == "environment"
    assert environment_member["plane"] == "mixed"
    assert environment_member["canonical_coordinates"]["outer_bounds_min_xyz"] == (-200.0, -2500.0, -761.0)
    assert environment_member["canonical_coordinates"]["outer_bounds_size_xyz"] == (5200.0, 5000.0, 3300.0)
    tx_region_member = next(member for member in member_objects if member["object_id"] == "tx_region")
    assert tx_region_member["role"] == "tx_region"
    assert tx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"] == (0.0, -140.0, 0.0)
    assert tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"] == (160.0, 280.0, 90.0)
    rx_region_member = next(member for member in member_objects if member["object_id"] == "rx_region_max")
    assert rx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"] == (0.0, -280.0, 139.0)
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert payload["scene_step_path"] == str(scene_step_path)
    assert payload["em_policy"] == {"radiation_margin_mm": 3500.0}
    assert payload["outputs"] == type1_outputs_spec()
    modeled_by_id = {entry["object_id"]: entry for entry in payload["modeled_objects"]}
    assert set(modeled_by_id) == {"tx_plate_stack", "rx_plate_stack"}
    for modeled_entry in ledger["modeled_objects"]:
        source_metadata_path = Path(modeled_entry["source_metadata_path"])
        assert source_metadata_path.is_file()
        source_metadata_payload = json.loads(source_metadata_path.read_text(encoding="utf-8"))
        assert source_metadata_payload["source_toml_path"] == str(source_toml)
        assert source_metadata_payload["scene_step_path"] == str(scene_step_path)
    tx_entry = modeled_by_id["tx_plate_stack"]
    assert tx_entry["role"] == "tx_plate_stack"
    assert tx_entry["plane"] == "YZ"
    assert tx_entry["placement_owner_id"] == "tx_region"
    assert cast(dict[str, object], tx_entry["terminal_metadata"])["kind"] == "stub_port"
    tx_turn_count = resolve_modeled_plate_stack_turn_count(tx_modeled_spec, seed=0)
    tx_fill = resolve_modeled_plate_stack_metal_fill_factor(tx_modeled_spec, seed=0)
    tx_expected_names = list(
        _tx_plate_stack_expected_body_names(
            ferrite_set_count=tx_modeled_spec.ferrite_set_count,
            turn_count=tx_turn_count,
            pcb_total_thickness_mm=tx_modeled_spec.pcb_total_thickness_mm,
        )
    )
    assert rx_modeled_spec.role == "rx_plate_stack"
    rx_turn_count = resolve_modeled_plate_stack_turn_count(rx_modeled_spec, seed=0)
    rx_fill = resolve_modeled_plate_stack_metal_fill_factor(rx_modeled_spec, seed=0)
    rx_expected_names = list(
        _rx_plate_stack_expected_body_names(
            ferrite_set_count=rx_modeled_spec.ferrite_set_count,
            turn_count=rx_turn_count,
            pcb_total_thickness_mm=rx_modeled_spec.pcb_total_thickness_mm,
        )
    )
    assert tx_entry["expected_exported_body_names"] == tx_expected_names
    assert tx_entry["expected_exported_body_count"] == len(tx_expected_names)
    assert _normalized_body_groups(tx_entry["expected_exported_body_groups"]) == _normalized_body_groups(
        _tx_plate_stack_expected_body_groups()
    )
    assert all(len(name) <= 32 for name in tx_expected_names)
    modeled_canonical = tx_entry["canonical_coordinates"]
    tx_min_x, tx_min_y, tx_min_z = modeled_canonical["outer_bounds_min_xyz"]
    tx_size_x, tx_size_y, tx_size_z = modeled_canonical["outer_bounds_size_xyz"]
    region_min_x, region_min_y, region_min_z = tx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    region_size_x, region_size_y, region_size_z = tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"]
    assert tx_min_x == pytest.approx(region_min_x)
    assert tx_min_y == pytest.approx(region_min_y)
    assert tx_min_z == pytest.approx(region_min_z)
    expected_tx_total_thickness_mm = total_plate_stack_thickness_mm(spec=cast(ModeledPlateStackSpec, tx_modeled_spec))
    assert tx_size_x == pytest.approx(expected_tx_total_thickness_mm)
    assert tx_size_y == pytest.approx(region_size_y + 5.0)
    assert tx_size_z == pytest.approx(region_size_z)
    tx_pitch_z = region_size_z / float(tx_turn_count)
    tx_trace_height_z = tx_pitch_z * tx_fill
    tx_centering_offset_z = (tx_pitch_z - tx_trace_height_z) / 2.0
    tx_step_min_xyz, tx_step_max_xyz = _body_bbox(scene_step_path, label="tx_copper_coil_t0")
    assert tx_step_min_xyz[0] == pytest.approx(region_min_x + expected_tx_total_thickness_mm - tx_modeled_spec.copper_thickness_mm)
    assert tx_step_max_xyz[0] == pytest.approx(region_min_x + expected_tx_total_thickness_mm)
    assert tx_step_min_xyz[1] == pytest.approx(region_min_y)
    assert tx_step_max_xyz[1] == pytest.approx(region_min_y + region_size_y)
    assert tx_step_min_xyz[2] == pytest.approx(region_min_z + (tx_pitch_z / 2.0) + tx_centering_offset_z)
    assert tx_step_max_xyz[2] == pytest.approx(region_min_z + (tx_pitch_z / 2.0) + tx_centering_offset_z + tx_trace_height_z)
    scene_shapes_by_label = _step_shapes_by_label(scene_step_path)
    rx_entry = modeled_by_id["rx_plate_stack"]
    assert _normalized_body_groups(rx_entry["expected_exported_body_groups"]) == _normalized_body_groups(
        _rx_plate_stack_expected_body_groups()
    )
    tx_group_names = [cast(str, group["group_name"]) for group in _tx_plate_stack_expected_body_groups()]
    rx_group_names = [cast(str, group["group_name"]) for group in _rx_plate_stack_expected_body_groups()]
    expected_scene_labels = {
        "environment",
        "tx_region",
        "rx_region_max",
        *tx_expected_names,
        *rx_expected_names,
        *tx_group_names,
        *rx_group_names,
    }
    assert set(scene_shapes_by_label) == expected_scene_labels
    assert "tx_port_sheet" not in scene_shapes_by_label
    merged_stack_labels = {
        "tx_stack_pet_psa",
        "tx_stack_ferrite",
        "tx_stack_air",
        "rx_stack_pet_psa",
        "rx_stack_ferrite",
        "rx_stack_air",
    }
    for label in {"environment", "tx_region", "rx_region_max", *tx_expected_names, *rx_expected_names} - merged_stack_labels:
        assert type(scene_shapes_by_label[label]).__name__ == "Solid"
    for label in merged_stack_labels:
        assert type(scene_shapes_by_label[label]).__name__ == "Solid"
        assert len(tuple(scene_shapes_by_label[label].solids())) == 1
    for label in [*tx_group_names, *rx_group_names]:
        assert type(scene_shapes_by_label[label]).__name__ == "Compound"
    _assert_plate_stack_united_ferrite_family_contract(scene_shapes_by_label=scene_shapes_by_label, prefix="tx")
    _assert_plate_stack_united_ferrite_family_contract(scene_shapes_by_label=scene_shapes_by_label, prefix="rx")
    assert all(not label.startswith("SOLID") for label in scene_shapes_by_label)
    _assert_zero_intersection_volume(scene_shapes_by_label["tx_pcb_wall"], scene_shapes_by_label["tx_copper_wall_t0"])
    _assert_zero_intersection_volume(scene_shapes_by_label["tx_pcb_coil"], scene_shapes_by_label["tx_copper_coil_t0"])
    _assert_zero_intersection_volume(scene_shapes_by_label["rx_pcb_wall"], scene_shapes_by_label["rx_copper_wall_t0"])
    _assert_zero_intersection_volume(scene_shapes_by_label["rx_pcb_coil"], scene_shapes_by_label["rx_copper_coil_t0"])
    _assert_plate_stack_bridge_non_overlap(
        scene_shapes_by_label=scene_shapes_by_label,
        prefix="tx",
        turn_count=tx_turn_count,
        ferrite_set_count=tx_modeled_spec.ferrite_set_count,
    )
    _assert_plate_stack_bridge_non_overlap(
        scene_shapes_by_label=scene_shapes_by_label,
        prefix="rx",
        turn_count=rx_turn_count,
        ferrite_set_count=rx_modeled_spec.ferrite_set_count,
    )
    rx_min_x, rx_min_y, rx_min_z = rx_entry["canonical_coordinates"]["outer_bounds_min_xyz"]
    rx_size_x, rx_size_y, rx_size_z = rx_entry["canonical_coordinates"]["outer_bounds_size_xyz"]
    rx_region_min_x, rx_region_min_y, rx_region_min_z = rx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    rx_region_size_x, rx_region_size_y, rx_region_size_z = rx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"]
    assert rx_entry["role"] == "rx_plate_stack"
    assert rx_entry["plane"] == "YZ"
    assert rx_entry["placement_owner_id"] == "rx_region_max"
    assert rx_entry["expected_exported_body_names"] == rx_expected_names
    assert rx_entry["expected_exported_body_count"] == len(rx_expected_names)
    assert _normalized_body_groups(rx_entry["expected_exported_body_groups"]) == _normalized_body_groups(
        _rx_plate_stack_expected_body_groups()
    )
    assert all(len(name) <= 32 for name in rx_expected_names)
    assert cast(dict[str, object], rx_entry["terminal_metadata"])["kind"] == "stub_port"
    assert rx_min_x == pytest.approx(rx_region_min_x)
    assert rx_min_y == pytest.approx(rx_region_min_y)
    assert rx_min_z == pytest.approx(rx_region_min_z)
    expected_rx_total_thickness_mm = total_plate_stack_thickness_mm(spec=cast(ModeledPlateStackSpec, rx_modeled_spec))
    assert rx_size_x == pytest.approx(expected_rx_total_thickness_mm)
    assert rx_size_y == pytest.approx(rx_region_size_y + 5.0)
    assert rx_size_z == pytest.approx(rx_region_size_z)
    rx_pitch_z = rx_region_size_z / float(rx_turn_count)
    rx_trace_height_z = rx_pitch_z * rx_fill
    rx_centering_offset_z = (rx_pitch_z - rx_trace_height_z) / 2.0
    rx_step_min_xyz, rx_step_max_xyz = _body_bbox(scene_step_path, label="rx_copper_coil_t0")
    assert rx_step_min_xyz[0] == pytest.approx(rx_region_min_x + expected_rx_total_thickness_mm - rx_modeled_spec.copper_thickness_mm)
    assert rx_step_max_xyz[0] == pytest.approx(rx_region_min_x + expected_rx_total_thickness_mm)
    assert rx_step_min_xyz[1] == pytest.approx(rx_region_min_y)
    assert rx_step_max_xyz[1] == pytest.approx(rx_region_min_y + rx_region_size_y)
    assert rx_step_min_xyz[2] == pytest.approx(rx_region_min_z + (rx_pitch_z / 2.0) + rx_centering_offset_z)
    assert rx_step_max_xyz[2] == pytest.approx(
        rx_region_min_z + (rx_pitch_z / 2.0) + rx_centering_offset_z + rx_trace_height_z
    )
    ferrite_first_min_xyz, ferrite_first_max_xyz = _body_bbox(scene_step_path, label="rx_stack_ferrite")
    pet_first_min_xyz, pet_first_max_xyz = _body_bbox(scene_step_path, label="rx_stack_pet_psa")
    air_first_min_xyz, air_first_max_xyz = _body_bbox(scene_step_path, label="rx_stack_air")
    wall_pcb_min_xyz, wall_pcb_max_xyz = _body_bbox(scene_step_path, label="rx_pcb_wall")
    coil_pcb_min_xyz, coil_pcb_max_xyz = _body_bbox(scene_step_path, label="rx_pcb_coil")
    assert wall_pcb_min_xyz[0] == pytest.approx(rx_region_min_x + rx_modeled_spec.copper_thickness_mm)
    assert wall_pcb_max_xyz[0] == pytest.approx(rx_region_min_x + rx_modeled_spec.pcb_total_thickness_mm)
    assert wall_pcb_min_xyz[2] == pytest.approx(rx_region_min_z)
    assert wall_pcb_max_xyz[2] == pytest.approx(rx_region_min_z + rx_region_size_z)
    assert pet_first_min_xyz[0] == pytest.approx(wall_pcb_max_xyz[0])
    assert ferrite_first_min_xyz[0] == pytest.approx(wall_pcb_max_xyz[0])
    assert air_first_min_xyz[0] == pytest.approx(wall_pcb_max_xyz[0])
    assert pet_first_max_xyz[0] == pytest.approx(coil_pcb_min_xyz[0])
    assert ferrite_first_max_xyz[0] == pytest.approx(coil_pcb_min_xyz[0])
    assert air_first_max_xyz[0] == pytest.approx(coil_pcb_min_xyz[0])
    assert coil_pcb_min_xyz[0] == pytest.approx(air_first_max_xyz[0])
    assert coil_pcb_max_xyz[0] == pytest.approx(rx_region_min_x + expected_rx_total_thickness_mm - rx_modeled_spec.copper_thickness_mm)
    assert coil_pcb_min_xyz[2] == pytest.approx(rx_region_min_z)
    assert coil_pcb_max_xyz[2] == pytest.approx(rx_region_min_z + rx_region_size_z)
    tx_bridge_min_xyz, tx_bridge_max_xyz = _body_bbox(scene_step_path, label="tx_bridge_s0")
    assert tx_bridge_min_xyz[0] == pytest.approx(region_min_x + tx_modeled_spec.copper_thickness_mm)
    assert tx_bridge_max_xyz[0] == pytest.approx(region_min_x + expected_tx_total_thickness_mm - tx_modeled_spec.copper_thickness_mm)
    assert tx_bridge_min_xyz[1] == pytest.approx(region_min_y + region_size_y - tx_modeled_spec.copper_thickness_mm)
    assert tx_bridge_max_xyz[1] == pytest.approx(region_min_y + region_size_y)
    assert tx_bridge_min_xyz[2] == pytest.approx(region_min_z + tx_centering_offset_z)
    bridge_min_xyz, bridge_max_xyz = _body_bbox(scene_step_path, label="rx_bridge_s0")
    assert bridge_min_xyz[0] == pytest.approx(rx_region_min_x + rx_modeled_spec.copper_thickness_mm)
    assert bridge_max_xyz[0] == pytest.approx(rx_region_min_x + expected_rx_total_thickness_mm - rx_modeled_spec.copper_thickness_mm)
    assert bridge_min_xyz[1] == pytest.approx(rx_region_min_y + rx_region_size_y - rx_modeled_spec.copper_thickness_mm)
    assert bridge_max_xyz[1] == pytest.approx(rx_region_min_y + rx_region_size_y)
    assert bridge_min_xyz[2] == pytest.approx(rx_region_min_z + rx_centering_offset_z)


@pytest.mark.parametrize("layer_count", (2, 3))
def test_export_type2_step_artifacts_supports_multilayer_tx_port_sheet_path(
    tmp_path: Path,
    layer_count: int,
) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(layer_count=layer_count))
    type2_spec = load_type2_step_spec(toml_path)
    tx_modeled_spec = next(entry for entry in type2_spec.modeled_objects if entry.object_id == "tx_rect_void_coil")
    assert tx_modeled_spec.role == "tx_single_coil"
    tx_underlay_repeat_count = resolve_modeled_underlay_repeat_count(cast(ModeledSingleCoilSpec, tx_modeled_spec), seed=0)
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )
    tx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_rect_void_coil")
    terminal_metadata = cast(dict[str, object], tx_entry["terminal_metadata"])
    assert tx_entry["expected_exported_body_names"] == _tx_expected_body_names(
        pcb_layer_count=layer_count,
        underlay_repeat_count=tx_underlay_repeat_count,
        wall_parallel_stack_present=False,
    )
    assert _normalized_body_groups(tx_entry["expected_exported_body_groups"]) == _normalized_body_groups(
        _tx_expected_body_groups(
            underlay_repeat_count=tx_underlay_repeat_count,
            wall_parallel_stack_present=False,
        )
    )
    _assert_sheet_vertices_bridge_stub_bottom_face_diagonals(
        sheet_vertices=_vertex_triplets(cast(list[list[float]], terminal_metadata["port_sheet_vertices_xyz"])),
        terminal_stub_boxes=_world_terminal_stub_boxes(
            source_toml=toml_path,
            object_id="tx_rect_void_coil",
            seed=0,
        ),
        plane="XY",
    )


@pytest.mark.parametrize("expected_repeat_count", (0, 2, 8))
def test_export_type2_step_artifacts_omits_tx_floor_underlay_bodies_for_all_repeat_counts(
    tmp_path: Path,
    expected_repeat_count: int,
) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(layer_count=2))
    spec = load_type2_step_spec(toml_path)
    tx_modeled_spec = next(entry for entry in spec.modeled_objects if entry.object_id == "tx_rect_void_coil")
    assert tx_modeled_spec.role == "tx_single_coil"
    seed = _seed_for_underlay_repeat_count(
        toml_path,
        object_id="tx_rect_void_coil",
        expected_repeat_count=expected_repeat_count,
    )

    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=seed,
    )

    tx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_rect_void_coil")
    expected_names = _tx_expected_body_names(
        pcb_layer_count=2,
        underlay_repeat_count=expected_repeat_count,
        wall_parallel_stack_present=False,
    )
    assert tx_entry["expected_exported_body_names"] == expected_names
    assert tx_entry["expected_exported_body_count"] == len(expected_names)
    assert _normalized_body_groups(tx_entry["expected_exported_body_groups"]) == _normalized_body_groups(
        _tx_expected_body_groups(
            underlay_repeat_count=expected_repeat_count,
            wall_parallel_stack_present=False,
        )
    )
    imported_scene = bd.import_step(Path(ledger["scene_step_path"]))
    scene_children_by_label = {child.label: child for child in imported_scene.children}
    for label in expected_names:
        assert label in scene_children_by_label
    assert all(not name.startswith("tx_underlay_") for name in expected_names)
    assert all(not label.startswith("tx_underlay_") for label in scene_children_by_label)


def test_export_type2_step_artifacts_groups_tx_wall_ferrite_family_when_exported(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            layer_count=2,
            underlay_repeat_count_range=_range(True, 2.0, 2.0, 1),
            wall_parallel_stack_present_range=_range(True, 1.0, 1.0, 1),
        ),
    )
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    tx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_rect_void_coil")
    expected_names = _tx_expected_body_names(
        pcb_layer_count=2,
        underlay_repeat_count=2,
        wall_parallel_stack_present=True,
    )
    assert tx_entry["expected_exported_body_names"] == expected_names
    assert tx_entry["expected_exported_body_count"] == len(expected_names)
    assert _normalized_body_groups(tx_entry["expected_exported_body_groups"]) == _normalized_body_groups(
        _tx_expected_body_groups(
            underlay_repeat_count=2,
            wall_parallel_stack_present=True,
        )
    )
    scene_shapes_by_label = _step_shapes_by_label(Path(ledger["scene_step_path"]))
    assert "g_ferrite_tx" in scene_shapes_by_label
    assert type(scene_shapes_by_label["g_ferrite_tx"]).__name__ == "Compound"
    for label in _tx_wall_expected_body_names(repeat_count=2):
        assert label in scene_shapes_by_label


def test_export_type2_step_artifacts_groups_rx_underlay_ferrite_family_when_exported(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="rx_rect_void_coil",
            modeled_role="rx_single_coil",
            underlay_repeat_count_range=_range(True, 2.0, 2.0, 1),
        ),
    )
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    rx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "rx_rect_void_coil")
    expected_names = _rx_expected_body_names(underlay_repeat_count=2)
    assert rx_entry["expected_exported_body_names"] == expected_names
    assert rx_entry["expected_exported_body_count"] == len(expected_names)
    assert _normalized_body_groups(rx_entry["expected_exported_body_groups"]) == _normalized_body_groups(
        _rx_expected_body_groups(underlay_repeat_count=2)
    )
    scene_shapes_by_label = _step_shapes_by_label(Path(ledger["scene_step_path"]))
    assert "g_ferrite_rx" in scene_shapes_by_label
    assert type(scene_shapes_by_label["g_ferrite_rx"]).__name__ == "Compound"
    for label in _rx_underlay_expected_body_names(repeat_count=2):
        assert label in scene_shapes_by_label


def test_export_type2_step_artifacts_builds_literal_tx_plate_stack_body_contract(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_tx_plate_stack_spec_text())

    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    tx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_plate_stack")
    expected_names = _tx_plate_stack_expected_body_names(
        ferrite_set_count=10,
        turn_count=3,
        pcb_total_thickness_mm=_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    )
    assert tx_entry["expected_exported_body_names"] == expected_names
    assert tx_entry["expected_exported_body_count"] == len(expected_names)
    assert tx_entry["expected_exported_body_count"] == 16
    assert _normalized_body_groups(tx_entry["expected_exported_body_groups"]) == _normalized_body_groups(
        _tx_plate_stack_expected_body_groups()
    )
    assert cast(dict[str, object], tx_entry["terminal_metadata"])["kind"] == "stub_port"
    scene_children_by_label = _step_shapes_by_label(Path(ledger["scene_step_path"]))
    for label in expected_names:
        assert label in scene_children_by_label
    for group_entry in _tx_plate_stack_expected_body_groups():
        group_name = cast(str, group_entry["group_name"])
        assert group_name in scene_children_by_label
    assert expected_names[0] == "tx_copper_wall_t0"
    assert expected_names[1] == "tx_copper_wall_t1"
    assert expected_names[2] == "tx_copper_wall_t2"
    assert expected_names[3] == "tx_pcb_wall"
    assert expected_names[4] == "tx_stack_pet_psa"
    assert expected_names[5] == "tx_stack_ferrite"
    assert expected_names[6] == "tx_stack_air"
    assert expected_names[-9] == "tx_pcb_coil"
    assert expected_names[-8] == "tx_copper_coil_t0"
    assert expected_names[-7] == "tx_copper_coil_t1"
    assert expected_names[-6] == "tx_bridge_s0"
    assert expected_names[-3] == "tx_bridge_s3"
    assert expected_names[-2] == "tx_stub_in"
    assert expected_names[-1] == "tx_stub_out"
    assert "tx_port_sheet" not in scene_children_by_label
    assert all("_shoe_" not in label for label in expected_names)
    assert all("_shoe_" not in label for label in scene_children_by_label)
    _assert_plate_stack_united_ferrite_family_contract(scene_shapes_by_label=scene_children_by_label, prefix="tx")
    assert all(not label.startswith("SOLID") for label in scene_children_by_label)


def test_export_type2_step_artifacts_builds_literal_rx_plate_stack_body_contract(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_rx_plate_stack_spec_text())

    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    rx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "rx_plate_stack")
    expected_names = _rx_plate_stack_expected_body_names(
        ferrite_set_count=10,
        turn_count=3,
        pcb_total_thickness_mm=_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    )
    assert rx_entry["expected_exported_body_names"] == expected_names
    assert rx_entry["expected_exported_body_count"] == len(expected_names)
    assert rx_entry["expected_exported_body_count"] == 16
    assert _normalized_body_groups(rx_entry["expected_exported_body_groups"]) == _normalized_body_groups(
        _rx_plate_stack_expected_body_groups()
    )
    assert cast(dict[str, object], rx_entry["terminal_metadata"])["kind"] == "stub_port"
    scene_children_by_label = _step_shapes_by_label(Path(ledger["scene_step_path"]))
    for label in expected_names:
        assert label in scene_children_by_label
    for group_entry in _rx_plate_stack_expected_body_groups():
        group_name = cast(str, group_entry["group_name"])
        assert group_name in scene_children_by_label
    assert expected_names[0] == "rx_copper_wall_t0"
    assert expected_names[1] == "rx_copper_wall_t1"
    assert expected_names[2] == "rx_copper_wall_t2"
    assert expected_names[3] == "rx_pcb_wall"
    assert expected_names[4] == "rx_stack_pet_psa"
    assert expected_names[5] == "rx_stack_ferrite"
    assert expected_names[6] == "rx_stack_air"
    assert expected_names[-9] == "rx_pcb_coil"
    assert expected_names[-8] == "rx_copper_coil_t0"
    assert expected_names[-7] == "rx_copper_coil_t1"
    assert expected_names[-6] == "rx_bridge_s0"
    assert expected_names[-3] == "rx_bridge_s3"
    assert expected_names[-2] == "rx_stub_in"
    assert expected_names[-1] == "rx_stub_out"
    assert all("_shoe_" not in label for label in expected_names)
    assert all("_shoe_" not in label for label in scene_children_by_label)
    _assert_plate_stack_united_ferrite_family_contract(scene_shapes_by_label=scene_children_by_label, prefix="rx")
    assert all(not label.startswith("SOLID") for label in scene_children_by_label)


def test_export_type2_step_artifacts_fails_when_tx_plate_stack_exceeds_tx_region_thickness(
    tmp_path: Path,
) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_tx_plate_stack_spec_text().replace("size_xyz = [160.0, 280.0, 90.0]", "size_xyz = [4.0, 280.0, 90.0]"),
    )

    with pytest.raises(RuntimeError, match=r"tx plate stack must fit inside tx_region thickness"):
        export_type2_step_artifacts(
            toml_path=toml_path,
            output_dir=tmp_path / "out",
            ledger_path=tmp_path / "out" / "ledger.json",
            seed=0,
        )


def test_export_type2_step_artifacts_fails_when_rx_plate_stack_exceeds_rx_region_max_thickness(
    tmp_path: Path,
) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_rx_plate_stack_spec_text().replace("size_xyz = [10.0, 200.0, 200.0]", "size_xyz = [4.0, 200.0, 200.0]"),
    )

    with pytest.raises(RuntimeError, match=r"rx plate stack must fit inside rx_region_max thickness"):
        export_type2_step_artifacts(
            toml_path=toml_path,
            output_dir=tmp_path / "out",
            ledger_path=tmp_path / "out" / "ledger.json",
            seed=0,
        )


def test_export_type2_step_artifacts_translates_terminal_metadata_with_tx_region_offset(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(layer_count=1))
    tx_rect_void_toml_path = tmp_path / "tx_rect_void.toml"
    tx_rect_void_toml_path.write_text(_tx_rect_void_spec_text_with_layer_count(layer_count=1), encoding="utf-8")
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    tx_region_member = next(
        member
        for member in ledger["non_model_objects"][0]["member_objects"]
        if member["object_id"] == "tx_region"
    )
    modeled_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_rect_void_coil")
    local_spec = load_tx_rect_void_spec(tx_rect_void_toml_path)
    local_realized = realize_tx_rect_void_spec(local_spec, seed=0)
    local_centerline = build_tx_rect_void_centerline(local_realized)
    local_boxes = build_tx_rect_void_box_specs(local_realized)
    local_bounds_min_xyz, _local_bounds_max_xyz, local_size_xyz = modeled_body_bounds_from_boxes(local_boxes)
    region_min_x, region_min_y, region_min_z = tx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    region_size_x, region_size_y, _region_size_z = tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"]
    placement_offset_x = region_min_x - local_bounds_min_xyz[0]
    placement_offset_y = region_min_y + (region_size_y - local_size_xyz[1]) / 2.0 - local_bounds_min_xyz[1]
    placement_offset_z = (
        region_min_z
        + tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"][2]
        - local_size_xyz[2]
        - local_bounds_min_xyz[2]
    )

    assert modeled_entry["canonical_coordinates"]["frame_origin_xyz"] == pytest.approx(
        (placement_offset_x, placement_offset_y, placement_offset_z)
    )
    modeled_bounds_min_xyz = modeled_entry["canonical_coordinates"]["outer_bounds_min_xyz"]
    assert isinstance(modeled_bounds_min_xyz, tuple)
    assert modeled_bounds_min_xyz[2] == pytest.approx(
        placement_offset_z + local_bounds_min_xyz[2]
    )
    assert modeled_entry["terminal_metadata"]["start_point_plane_mm"] == pytest.approx(
        (
            local_centerline[0][0] + placement_offset_x,
            local_centerline[0][1] + placement_offset_y,
        )
    )
    assert modeled_entry["terminal_metadata"]["end_point_plane_mm"] == pytest.approx(
        (
            local_centerline[-1][0] + placement_offset_x,
            local_centerline[-1][1] + placement_offset_y,
        )
    )
    expected_tx_port_sheet_vertices = tuple(
        tuple(round(component, 8) for component in vertex)
        for vertex in _widest_stub_bottom_face_diagonal_vertices(
            terminal_stub_boxes=_world_terminal_stub_boxes(
                source_toml=toml_path,
                object_id="tx_rect_void_coil",
                seed=0,
            ),
            plane="XY",
        )
    )
    actual_tx_port_sheet_vertices = tuple(
        tuple(round(component, 8) for component in vertex)
        for vertex in cast(
            list[list[float]],
            cast(dict[str, object], modeled_entry["terminal_metadata"])["port_sheet_vertices_xyz"],
        )
    )
    assert set(actual_tx_port_sheet_vertices) == set(expected_tx_port_sheet_vertices)


def test_export_type2_step_artifacts_places_tx_plate_stack_on_tx_region_min_x_anchor(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_tx_plate_stack_spec_text())
    type2_spec = load_type2_step_spec(toml_path)
    tx_modeled_spec = next(entry for entry in type2_spec.modeled_objects if entry.object_id == "tx_plate_stack")
    assert tx_modeled_spec.role == "tx_plate_stack"
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    tx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_plate_stack")
    tx_region_member = next(
        member for member in ledger["non_model_objects"][0]["member_objects"] if member["object_id"] == "tx_region"
    )
    tx_min_xyz = tx_entry["canonical_coordinates"]["outer_bounds_min_xyz"]
    assert isinstance(tx_min_xyz, tuple)
    tx_min_x, tx_min_y, tx_min_z = cast(tuple[float, float, float], tx_min_xyz)
    tx_size_xyz = tx_entry["canonical_coordinates"]["outer_bounds_size_xyz"]
    assert isinstance(tx_size_xyz, tuple)
    tx_size_x, tx_size_y, tx_size_z = cast(tuple[float, float, float], tx_size_xyz)
    region_min_x, region_min_y, region_min_z = tx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    region_size_x, region_size_y, region_size_z = tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"]

    assert tx_entry["plane"] == "YZ"
    assert tx_entry["placement_owner_id"] == "tx_region"
    assert cast(dict[str, object], tx_entry["terminal_metadata"])["kind"] == "stub_port"
    assert list(tx_entry["expected_exported_body_names"]) == list(
        _tx_plate_stack_expected_body_names(
            ferrite_set_count=10,
            turn_count=3,
            pcb_total_thickness_mm=tx_modeled_spec.pcb_total_thickness_mm,
        )
    )
    assert tx_entry["expected_exported_body_count"] == len(tx_entry["expected_exported_body_names"])
    assert tx_min_x == pytest.approx(region_min_x)
    assert tx_min_y == pytest.approx(region_min_y)
    assert tx_min_z == pytest.approx(region_min_z)
    assert tx_size_x == pytest.approx(total_plate_stack_thickness_mm(spec=cast(ModeledPlateStackSpec, tx_modeled_spec)))
    assert tx_size_y == pytest.approx(region_size_y + 5.0)
    assert tx_size_z == pytest.approx(region_size_z)
    tx_pitch_z = region_size_z / 3.0
    tx_trace_height_z = tx_pitch_z * 0.4
    tx_centering_offset_z = (tx_pitch_z - tx_trace_height_z) / 2.0
    tx_step_min_xyz, tx_step_max_xyz = _body_bbox(Path(ledger["scene_step_path"]), label="tx_copper_wall_t0")
    assert tx_step_min_xyz[0] == pytest.approx(region_min_x)
    assert tx_step_max_xyz[0] == pytest.approx(region_min_x + tx_modeled_spec.copper_thickness_mm)
    assert tx_step_min_xyz[1] == pytest.approx(region_min_y)
    assert tx_step_max_xyz[1] == pytest.approx(region_min_y + region_size_y)
    assert tx_step_min_xyz[2] == pytest.approx(region_min_z + tx_centering_offset_z)
    assert tx_step_max_xyz[2] == pytest.approx(region_min_z + tx_centering_offset_z + tx_trace_height_z)


def test_export_type2_step_artifacts_places_rx_plate_stack_on_rx_region_max_min_x_anchor(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_fixed.toml"
    type2_spec = load_type2_step_spec(source_toml)
    rx_modeled_spec = next(entry for entry in type2_spec.modeled_objects if entry.object_id == "rx_plate_stack")
    assert rx_modeled_spec.role == "rx_plate_stack"
    ledger = export_type2_step_artifacts(
        toml_path=source_toml,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    rx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "rx_plate_stack")
    rx_region_member = next(
        member for member in ledger["non_model_objects"][0]["member_objects"] if member["object_id"] == "rx_region_max"
    )
    rx_min_xyz = rx_entry["canonical_coordinates"]["outer_bounds_min_xyz"]
    assert isinstance(rx_min_xyz, tuple)
    rx_min_x, rx_min_y, rx_min_z = cast(tuple[float, float, float], rx_min_xyz)
    rx_size_xyz = rx_entry["canonical_coordinates"]["outer_bounds_size_xyz"]
    assert isinstance(rx_size_xyz, tuple)
    rx_size_x, rx_size_y, rx_size_z = cast(tuple[float, float, float], rx_size_xyz)
    region_min_x, region_min_y, region_min_z = rx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    region_size_x, region_size_y, region_size_z = rx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"]

    assert rx_entry["plane"] == "YZ"
    assert rx_entry["placement_owner_id"] == "rx_region_max"
    assert list(rx_entry["expected_exported_body_names"]) == list(
        _rx_plate_stack_expected_body_names(
            ferrite_set_count=10,
            turn_count=3,
            pcb_total_thickness_mm=rx_modeled_spec.pcb_total_thickness_mm,
        )
    )
    assert rx_entry["expected_exported_body_count"] == len(rx_entry["expected_exported_body_names"])
    assert rx_min_x == pytest.approx(region_min_x)
    assert rx_min_y == pytest.approx(region_min_y)
    assert rx_min_z == pytest.approx(region_min_z)
    assert rx_size_x == pytest.approx(total_plate_stack_thickness_mm(spec=cast(ModeledPlateStackSpec, rx_modeled_spec)))
    assert rx_size_y == pytest.approx(region_size_y + 5.0)
    assert rx_size_z == pytest.approx(region_size_z)
    rx_pitch_z = region_size_z / 3.0
    rx_trace_height_z = rx_pitch_z * 0.4
    rx_centering_offset_z = (rx_pitch_z - rx_trace_height_z) / 2.0
    rx_step_min_xyz, rx_step_max_xyz = _body_bbox(Path(ledger["scene_step_path"]), label="rx_copper_wall_t0")
    assert rx_step_min_xyz[0] == pytest.approx(region_min_x)
    assert rx_step_max_xyz[0] == pytest.approx(region_min_x + rx_modeled_spec.copper_thickness_mm)
    assert rx_step_min_xyz[1] == pytest.approx(region_min_y)
    assert rx_step_max_xyz[1] == pytest.approx(region_min_y + region_size_y)
    assert rx_step_min_xyz[2] == pytest.approx(region_min_z + rx_centering_offset_z)
    assert rx_step_max_xyz[2] == pytest.approx(region_min_z + rx_centering_offset_z + rx_trace_height_z)


def test_export_type2_step_artifacts_propagates_custom_radiation_margin_into_step_ledger(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(radiation_margin_mm=4123.5))
    ledger_path = tmp_path / "out" / "ledger.json"

    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=ledger_path,
        seed=0,
    )

    assert ledger["em_policy"] == {"radiation_margin_mm": 4123.5}
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert payload["em_policy"] == {"radiation_margin_mm": 4123.5}


def test_export_type2_step_artifacts_fails_for_invalid_terminal_path(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(terminal_path="A_cw_to_b"))
    output_dir = tmp_path / "out"
    ledger_path = tmp_path / "out" / "ledger.json"

    with pytest.raises(ValueError, match=r"matching outer/inner corners"):
        export_type2_step_artifacts(
            toml_path=toml_path,
            output_dir=output_dir,
            ledger_path=ledger_path,
            seed=0,
        )


def test_export_type2_step_artifacts_fails_when_non_model_export_returns_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import peetsfea.type2_step_export as module_under_test

    toml_path = _write_spec(tmp_path, _type2_spec_text())
    output_dir = tmp_path / "out"
    ledger_path = tmp_path / "out" / "ledger.json"

    def _false_export_step(*args: object, **kwargs: object) -> bool:
        return False

    monkeypatch.setattr(module_under_test.bd, "export_step", _false_export_step)

    with pytest.raises(RuntimeError, match=r"build123d export_step returned False for type2 scene STEP:"):
        export_type2_step_artifacts(
            toml_path=toml_path,
            output_dir=output_dir,
            ledger_path=ledger_path,
            seed=0,
        )

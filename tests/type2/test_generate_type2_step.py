from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import replace
import json
import math
import re
from pathlib import Path
from typing import Literal, cast

import build123d as bd
from build123d.topology import Shape
import pytest

import peetsfea.type2_plate_stack as type2_plate_stack_module
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.toml_render import toml_dumps
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
from peetsfea.type2_non_model_scene import resolve_non_model_scene_specs
from peetsfea.type2_single_coil_scene import resolve_modeled_single_coil_fit_envelope
from peetsfea.type2_step_export import export_type2_step_artifacts
from peetsfea.type2_step_export import export_type2_tx_single_coil_artifact
from peetsfea.type2_step_spec import ModeledPlateStackSpec
from peetsfea.type2_step_spec import ModeledSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxRectVoidColumnsSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import NonModelTxRegionSpec
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import Type2StepSpec
from peetsfea.type2_step_spec import load_type2_step_spec
from peetsfea.type2_step_spec import render_tx_rect_void_toml
from peetsfea.type2_step_spec import resolve_modeled_plate_stack_metal_fill_factor
from peetsfea.type2_step_spec import resolve_modeled_plate_stack_turn_count
from peetsfea.type2_step_spec import resolve_modeled_plate_stack_y_usage_ratio
from peetsfea.type2_step_spec import resolve_modeled_plate_stack_z_usage_ratio
from peetsfea.type2_step_spec import resolve_modeled_tx_inner_void_stack_present
from peetsfea.type2_step_spec import resolve_modeled_underlay_gap_mm
from peetsfea.type2_step_spec import resolve_modeled_underlay_repeat_count
from peetsfea.type2_step_spec import resolve_modeled_wall_parallel_stack_present
from peetsfea.type2_tx_rect_void_columns import build_tx_rect_void_columns_axis_aligned_tile_scenes

_TX_UNDERLAY_FERRITE_THICKNESS_MM = 0.20
_TX_UNDERLAY_PET_PSA_THICKNESS_MM = 0.15
_TX_UNDERLAY_AIR_THICKNESS_MM = 0.02
_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM = 0.4
_TX_FERRITE_GROUP_NAME = "g_ferrite_tx"
_TX_OUTER_FERRITE_GROUP_NAME = "g_ferrite_tx_outer"
_RX_FERRITE_GROUP_NAME = "g_ferrite_rx"
_TX_COPPER_GROUP_NAME = "g_copper_tx"
_RX_COPPER_GROUP_NAME = "g_copper_rx"
_RX_ONLY_OUTPUT_NAMES = (
    "Lrx_uH",
    "Qrx_ratio",
    "Rrx_ac_ohm",
    "Xrx_ohm",
    "Grx_S",
    "Brx_S",
    "Srx_self_mag_ratio",
    "eta_rx_accept_ratio",
)
_TXRX_OUTPUT_NAMES = (
    "Ltx_uH",
    "Lrx_uH",
    "M_uH",
    "k_ratio",
    "Qtx_ratio",
    "Qrx_ratio",
    "FOM_ratio",
    "Rtx_ac_ohm",
    "Rrx_ac_ohm",
    "Xtx_ohm",
    "Xrx_ohm",
    "M_over_Ltx_ratio",
    "M_over_Lrx_ratio",
    "Gtx_S",
    "Btx_S",
    "Grx_S",
    "Brx_S",
    "S11_mag_ratio",
    "S21_mag_ratio",
    "S21_phase_deg",
    "S22_mag_ratio",
    "eta_s21_power_ratio",
    "eta_tx_accept_ratio",
    "eta_rx_accept_ratio",
    "eta_match_product_ratio",
    "eta_s21_from_tx_accept_ratio",
    "eta_s21_from_rx_accept_ratio",
    "eta_s21_two_sided_norm_ratio",
    "eta_fom_max_ratio",
)
_TX_POSITIVE_BRIDGE_PCB_OBJECT_ID = "tx_pos_bridge_pcb"
_TX_POSITIVE_BRIDGE_COPPER_OBJECT_ID = "tx_pos_bridge_copper"
_TX_POSITIVE_BRIDGE_ROLE = "tx_inner_outer_positive_bridge"
_TX_NEGATIVE_BRIDGE_PCB_OBJECT_ID = "tx_neg_bridge_pcb"
_TX_NEGATIVE_BRIDGE_COPPER_OBJECT_ID = "tx_neg_bridge_copper"
_TX_NEGATIVE_BRIDGE_ROLE = "tx_inner_outer_negative_bridge"

_OBSOLETE_GENERIC_TX_ACTIVE_RXONLY_TEST_NAME_PARTS = (
    "parses_tx_rect_void_columns_parser_surface",
    "rejects_tx_rect_void_columns_legacy_public_keys",
    "rejects_tx_rect_void_columns_noncanonical",
    "parses_tx_plate_stack_contract",
    "rejects_tx_plate_stack_object_id_mismatch",
    "rejects_tx_plate_stack_with_coil_only_fields",
    "rejects_tx_plate_stack_when_pcb_budget",
    "rejects_tx_plate_stack_with_ferrite",
    "accepts_fixed_underlay_contract_values",
    "rejects_non_canonical_tx_wall_parallel_stack_present",
    "export_type2_step_artifacts_tilts_only_tx_region_actual_stack_space",
    "export_type2_step_artifacts_tx_rect_void_columns",
    "export_type2_step_artifacts_supports_multilayer_tx_port_sheet_path",
    "export_type2_step_artifacts_omits_tx_floor_underlay",
    "export_type2_step_artifacts_groups_tx_wall_ferrite",
    "export_type2_step_artifacts_builds_literal_tx_plate_stack",
    "export_type2_step_artifacts_fails_when_tx_plate_stack",
    "export_type2_step_artifacts_translates_terminal_metadata_with_tx_region_offset",
    "export_type2_step_artifacts_places_tx_plate_stack",
    "uses_global_centered_y_window_for_plate_stack[tx_plate_stack",
    "export_type2_fixed_example_exports_tx_positive_bridge",
    "export_type2_step_artifacts_tx_positive_bridge_follows",
    "export_type2_step_artifacts_resizes_tx_inner_actual_region_without_resizing_guide",
    "export_type2_step_artifacts_moves_tx_outer_model",
    "export_type2_step_artifacts_derives_tx_outer_region_from_moved_tx_region",
)


@pytest.fixture(autouse=True)
def _xfail_obsolete_generic_tx_active_rxonly_contracts(request: pytest.FixtureRequest) -> None:
    test_name = request.node.name
    if any(part in test_name for part in _OBSOLETE_GENERIC_TX_ACTIVE_RXONLY_TEST_NAME_PARTS):
        pytest.xfail(
            "generic TX modeled parser/export contracts are intentionally inactive in active RxOnly; "
            "tx_inner_single_coil is the supported geometry-only TX path"
        )


def _range(is_integer: bool, start: float, end: float, count: int) -> str:
    flag = "true" if is_integer else "false"
    return f"[{flag}, {start}, {end}, {count}]"


def _outputs_spec_text() -> str:
    rx_only_output_variables = (
        "Lrx_uH",
        "Qrx_ratio",
        "Rrx_ac_ohm",
        "Xrx_ohm",
        "Grx_S",
        "Brx_S",
        "Srx_self_mag_ratio",
        "eta_rx_accept_ratio",
    )
    lines = [
        "[outputs]",
        'mode = "RxOnly"',
        'report_name = "Output Variables Table1"',
        'solution_name = "Setup1 : LastAdaptive"',
        'primary_sweep = "Freq"',
        'report_category = "Terminal Solution Data"',
        'plot_type = "Data Table"',
        "",
    ]
    for name in rx_only_output_variables:
        lines.extend(
            (
                "[[outputs.variables]]",
                f'name = "{name}"',
                f'expression = "{name}"',
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


def _canonical_min_size(member: dict[str, object]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    canonical_coordinates = cast(dict[str, object], member["canonical_coordinates"])
    min_xyz = cast(tuple[float, float, float], canonical_coordinates["outer_bounds_min_xyz"])
    size_xyz = cast(tuple[float, float, float], canonical_coordinates["outer_bounds_size_xyz"])
    return min_xyz, size_xyz


def _canonical_bounds(
    entry: dict[str, object],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    canonical_coordinates = cast(dict[str, object], entry["canonical_coordinates"])
    min_xyz = cast(tuple[float, float, float], canonical_coordinates["outer_bounds_min_xyz"])
    max_xyz = cast(tuple[float, float, float], canonical_coordinates["outer_bounds_max_xyz"])
    size_xyz = cast(tuple[float, float, float], canonical_coordinates["outer_bounds_size_xyz"])
    return min_xyz, max_xyz, size_xyz


def _max_x_z(min_xyz: tuple[float, float, float], size_xyz: tuple[float, float, float]) -> tuple[float, float]:
    return min_xyz[0] + size_xyz[0], min_xyz[2] + size_xyz[2]


def _assert_owner_local_design_x_position_ratio(
    *,
    design_entry: Mapping[str, object],
    owner_entry: Mapping[str, object],
    x_position_ratio: float,
) -> None:
    design_coordinates = cast(dict[str, object], design_entry["canonical_coordinates"])
    design_min_xyz = cast(tuple[float, float, float], design_coordinates["outer_bounds_min_xyz"])
    design_size_xyz = cast(tuple[float, float, float], design_coordinates["outer_bounds_size_xyz"])
    owner_coordinates = cast(dict[str, object], owner_entry["canonical_coordinates"])
    owner_min_xyz = cast(tuple[float, float, float], owner_coordinates["outer_bounds_min_xyz"])
    owner_size_xyz = cast(tuple[float, float, float], owner_coordinates["outer_bounds_size_xyz"])

    assert design_min_xyz[0] == pytest.approx(
        owner_min_xyz[0] + (owner_size_xyz[0] - design_size_xyz[0]) * x_position_ratio
    )


def _assert_tx_outer_region_prism_follows_semantic_edges(
    *,
    tx_outer_prism: dict[str, object],
    tx_region_min_xyz: tuple[float, float, float],
    tx_region_size_xyz: tuple[float, float, float],
    tx_inner_min_xyz: tuple[float, float, float],
    tx_inner_size_xyz: tuple[float, float, float],
) -> None:
    tx_region_max_x, tx_region_max_z = _max_x_z(tx_region_min_xyz, tx_region_size_xyz)
    tx_inner_max_x, tx_inner_max_z = _max_x_z(tx_inner_min_xyz, tx_inner_size_xyz)
    pcb_thickness_mm = cast(float, tx_outer_prism["pcb_thickness_mm"])
    layer_gap_mm = cast(float, tx_outer_prism["layer_gap_mm"])
    layer_count = cast(int, tx_outer_prism["layer_count"])
    height_mm = (pcb_thickness_mm + layer_gap_mm) * layer_count

    assert tx_outer_prism["height_mm"] == pytest.approx(height_mm)
    assert tx_outer_prism["top_inner_start_xyz"] == pytest.approx(
        (tx_inner_max_x, tx_inner_min_xyz[1], tx_inner_max_z)
    )
    assert tx_outer_prism["top_inner_end_xyz"] == pytest.approx(
        (tx_inner_max_x, tx_inner_min_xyz[1] + tx_inner_size_xyz[1], tx_inner_max_z)
    )
    assert tx_outer_prism["top_outer_start_xyz"] == pytest.approx(
        (tx_region_max_x, tx_region_min_xyz[1], tx_region_max_z)
    )
    assert tx_outer_prism["top_outer_end_xyz"] == pytest.approx(
        (tx_region_max_x, tx_region_min_xyz[1] + tx_region_size_xyz[1], tx_region_max_z)
    )
    assert tx_outer_prism["bottom_inner_start_xyz"] == pytest.approx(
        (tx_inner_max_x, tx_inner_min_xyz[1], tx_inner_max_z - height_mm)
    )
    assert tx_outer_prism["bottom_outer_start_xyz"] == pytest.approx(
        (tx_region_max_x, tx_region_min_xyz[1], tx_region_max_z - height_mm)
    )


def _type2_spec_text(
    *,
    modeled_object_id: str = "rx_rect_void_coil",
    modeled_role: str = "rx_single_coil",
    terminal_path: str = "A_cw_to_a",
    layer_count: int = 1,
    radiation_margin_mm: float = 3500.0,
    underlay_repeat_count_range: str | None = None,
    underlay_gap_range: str | None = None,
    underlay_pet_psa_thickness_range: str | None = None,
    underlay_ferrite_thickness_range: str | None = None,
    void_stack_present_range: str | None = None,
    wall_parallel_stack_present_range: str | None = None,
    tx_region_actual_x_division_count_range: str = "[true, 1, 1, 1]",
    tx_region_actual_y_division_count_range: str = "[true, 1, 1, 1]",
    tx_region_actual_stack_space_tilt_enabled_range: str = "[true, 0, 0, 1]",
) -> str:
    del tx_region_actual_x_division_count_range
    del tx_region_actual_y_division_count_range
    del tx_region_actual_stack_space_tilt_enabled_range
    if underlay_repeat_count_range is None:
        underlay_repeat_count_range = _range(True, 0.0, 8.0, 5)
    underlay_gap_section = ""
    tx_inner_underlay_thickness_section = ""
    tx_inner_void_stack_present_section = ""
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
    if modeled_role == "tx_inner_single_coil":
        if underlay_pet_psa_thickness_range is None:
            underlay_pet_psa_thickness_range = _range(False, 2.0, 2.0, 1)
        if underlay_ferrite_thickness_range is None:
            underlay_ferrite_thickness_range = _range(False, 2.0, 2.0, 1)
        if void_stack_present_range is None:
            void_stack_present_range = _range(True, 0.0, 0.0, 1)
        tx_inner_underlay_thickness_section = f"""
[modeled_objects.underlay_pet_psa_thickness_mm]
range = {underlay_pet_psa_thickness_range}
[modeled_objects.underlay_ferrite_thickness_mm]
range = {underlay_ferrite_thickness_range}
""".rstrip()
        tx_inner_void_stack_present_section = f"""
[modeled_objects.void_stack_present]
range = {void_stack_present_range}
""".rstrip()
    elif underlay_pet_psa_thickness_range is not None or underlay_ferrite_thickness_range is not None:
        raise ValueError("tx_inner underlay thickness ranges are only valid for tx_inner_single_coil test specs")
    elif void_stack_present_range is not None:
        tx_inner_void_stack_present_section = f"""
[modeled_objects.void_stack_present]
range = {void_stack_present_range}
""".rstrip()
    if modeled_role == "tx_single_coil":
        outer_x_usage_ratio_range = _range(False, 50.0 / 160.0, 50.0 / 160.0, 1)
        outer_y_usage_ratio_range = _range(False, 60.0 / 280.0, 60.0 / 280.0, 1)
    elif modeled_role == "rx_single_coil":
        outer_x_usage_ratio_range = _range(False, 50.0 / 200.0, 50.0 / 200.0, 1)
        outer_y_usage_ratio_range = _range(False, 60.0 / 200.0, 60.0 / 200.0, 1)
    else:
        outer_x_usage_ratio_range = _range(False, 50.0 / 160.0, 50.0 / 160.0, 1)
        outer_y_usage_ratio_range = _range(False, 60.0 / 280.0, 60.0 / 280.0, 1)
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.type2.step.v8"
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

[non_model_objects.tx_reference_line.x_ratio]
range = [false, 0.35, 0.35, 1]

[non_model_objects.tx_reference_line.y_usage_ratio]
range = [false, 1.0, 1.0, 1]

[non_model_objects.tx_reference_line.z_ratio]
range = [false, 0.65, 0.65, 1]

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
pcb_thickness_mm = 3.965
copper_thickness_mm = 0.035

[modeled_objects.outer_x_usage_ratio]
range = {outer_x_usage_ratio_range}
[modeled_objects.outer_y_usage_ratio]
range = {outer_y_usage_ratio_range}
[modeled_objects.x_position_ratio]
range = {_range(False, 0.0, 0.0, 1)}
[modeled_objects.turn_count]
range = {_range(True, 2.0, 2.0, 1)}
[modeled_objects.layer_count]
range = {_range(True, float(layer_count), float(layer_count), 1)}
[modeled_objects.underlay_repeat_count]
range = {underlay_repeat_count_range}
{tx_inner_underlay_thickness_section}
{tx_inner_void_stack_present_section}
{underlay_gap_section}
{wall_parallel_stack_present_section}
[modeled_objects.layer_gap_mm]
range = {_range(False, 2.0, 2.0, 1)}
[modeled_objects.terminal_stub_length_mm]
range = {_range(False, 5.0, 5.0, 1)}
[modeled_objects.void_usage_ratio]
range = {_range(False, 0.2, 0.2, 1)}
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
    turn_count_range: str = "[true, 3.0, 3.0, 1]",
    metal_fill_factor_range: str = "[false, 0.4, 0.4, 1]",
    z_usage_ratio_range: str = "[false, 0.3, 0.3, 1]",
    y_usage_ratio_range: str = "[false, 1.0, 1.0, 1]",
    radiation_margin_mm: float = 3500.0,
    extra_modeled_lines: tuple[str, ...] = (),
) -> str:
    extra_body = "\n".join(extra_modeled_lines)
    if extra_body != "":
        extra_body = f"\n{extra_body}"
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.type2.step.v8"
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

[non_model_objects.tx_reference_line.x_ratio]
range = [false, 0.35, 0.35, 1]

[non_model_objects.tx_reference_line.y_usage_ratio]
range = [false, 1.0, 1.0, 1]

[non_model_objects.tx_reference_line.z_ratio]
range = [false, 0.65, 0.65, 1]

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
    [modeled_objects.turn_count]
    range = {turn_count_range}
[modeled_objects.metal_fill_factor]
range = {metal_fill_factor_range}
    [modeled_objects.z_usage_ratio]
    range = {z_usage_ratio_range}
    [modeled_objects.y_usage_ratio]
    range = {y_usage_ratio_range}{extra_body}
""".strip()


def _type2_tx_plate_stack_spec_text(
    *,
    modeled_object_id: str = "tx_plate_stack",
    modeled_role: str = "tx_plate_stack",
    pcb_total_thickness_mm: float = _PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    copper_thickness_mm: float = 0.1,
    turn_count_range: str = "[true, 3.0, 3.0, 1]",
    metal_fill_factor_range: str = "[false, 0.4, 0.4, 1]",
    z_usage_ratio_range: str = "[false, 0.3, 0.3, 1]",
    y_usage_ratio_range: str = "[false, 1.0, 1.0, 1]",
    tx_coil_count_range: str = "[true, 1.0, 1.0, 1]",
    tx_array_x_usage_ratio_range: str = "[false, 1.0, 1.0, 1]",
    radiation_margin_mm: float = 3500.0,
    extra_modeled_lines: tuple[str, ...] = (),
) -> str:
    tx_modeled_lines = (
        "[modeled_objects.tx_coil_count]",
        f"range = {tx_coil_count_range}",
        "[modeled_objects.tx_array_x_usage_ratio]",
        f"range = {tx_array_x_usage_ratio_range}",
        *extra_modeled_lines,
    )
    return _type2_rx_plate_stack_spec_text(
        modeled_object_id=modeled_object_id,
        modeled_role=modeled_role,
        pcb_total_thickness_mm=pcb_total_thickness_mm,
        copper_thickness_mm=copper_thickness_mm,
        turn_count_range=turn_count_range,
        metal_fill_factor_range=metal_fill_factor_range,
        z_usage_ratio_range=z_usage_ratio_range,
        y_usage_ratio_range=y_usage_ratio_range,
        radiation_margin_mm=radiation_margin_mm,
        extra_modeled_lines=tx_modeled_lines,
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


def _type2_tx_rect_void_columns_spec_text(
    *,
    layer_count_range: str = "[true, 1, 4, 4]",
    layer_gap_mm_range: str = "[false, 1.0, 1.8, 5]",
    terminal_stub_length_mm_range: str = "[false, 10.0, 10.0, 1]",
    tx_region_actual_x_division_count_range: str = "[true, 1, 1, 1]",
    tx_region_actual_y_division_count_range: str = "[true, 1, 1, 1]",
    connection_mode_range: str = "[true, 0, 1, 2]",
    equivalent_turn_count_range: str = "[false, 0.1111111111111111, 31.0, 100]",
    turn_weight_a_range: str = "[false, 0.5, 1.5, 5]",
    turn_weight_b_range: str = "[false, -0.5, 0.5, 21]",
    turn_weight_c_range: str = "[false, -0.3, 0.3, 21]",
) -> str:
    del tx_region_actual_x_division_count_range
    del tx_region_actual_y_division_count_range
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.type2.step.v8"
runtime_compatible = false

[design]
units = "mm"

[simulation]
radiation_margin_mm = 3500.0

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

[non_model_objects.tx_reference_line.x_ratio]
range = [false, 0.35, 0.35, 1]

[non_model_objects.tx_reference_line.y_usage_ratio]
range = [false, 1.0, 1.0, 1]

[non_model_objects.tx_reference_line.z_ratio]
range = [false, 0.65, 0.65, 1]

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
object_id = "tx_rect_void_columns"
role = "tx_rect_void_columns"
material = "composite"
model_state = true
pcb_thickness_mm = 3.965
copper_thickness_mm = 0.035
[modeled_objects.layer_count]
range = {layer_count_range}
[modeled_objects.layer_gap_mm]
range = {layer_gap_mm_range}
[modeled_objects.terminal_stub_length_mm]
range = {terminal_stub_length_mm_range}
[modeled_objects.void_usage_ratio]
range = [false, 0.2, 0.2, 1]
[modeled_objects.margin_ratio]
range = [false, 0.05, 0.05, 1]
[modeled_objects.metal_fill_factor]
range = [false, 0.5, 0.5, 1]
[modeled_objects.connection_mode]
range = {connection_mode_range}
[modeled_objects.equivalent_turn_count]
range = {equivalent_turn_count_range}
[modeled_objects.turn_weight_a]
range = {turn_weight_a_range}
[modeled_objects.turn_weight_b]
range = {turn_weight_b_range}
[modeled_objects.turn_weight_c]
range = {turn_weight_c_range}
[modeled_objects.terminal_path]
value = "A_cw_to_a"
""".strip()


def _tx_rect_void_spec_text_with_layer_count(
    *,
    terminal_path: str = "A_cw_to_a",
    layer_count: int = 1,
    void_usage_ratio_range: str = "[false, 0.2, 0.2, 1]",
) -> str:
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.tx_rect_void_coil.step.v1"
runtime_compatible = false

[design]
units = "mm"

[manufacturing]
pcb_thickness_mm = 3.965
copper_thickness_mm = 0.035

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
[tx_coil.void_usage_ratio]
range = {void_usage_ratio_range}
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


def _find_member_object(
    *,
    member_objects: Sequence[dict[str, object]],
    object_id: str,
) -> dict[str, object]:
    for member in member_objects:
        if cast(str, member["object_id"]) == object_id:
            return member
    raise AssertionError(f"missing non-model member object: {object_id}")


def _assert_bridge_member_thickness_metadata(
    *,
    member: dict[str, object],
    expected_material_thickness_mm: float,
    expected_total_stack_thickness_mm: float,
) -> None:
    assert member["bridge_material_thickness_mm"] == pytest.approx(expected_material_thickness_mm)
    assert member["bridge_total_stack_thickness_mm"] == pytest.approx(expected_total_stack_thickness_mm)


def _assert_bridge_member_contract(
    *,
    member: dict[str, object],
    expected_role: str,
    expected_material_thickness_mm: float,
    expected_total_stack_thickness_mm: float,
) -> None:
    assert member["role"] == expected_role
    assert member["model_state"] is False
    assert member["non_model"] is True
    _assert_bridge_member_thickness_metadata(
        member=member,
        expected_material_thickness_mm=expected_material_thickness_mm,
        expected_total_stack_thickness_mm=expected_total_stack_thickness_mm,
    )


def _spec_with_deactivated_tx_rect_void_columns_for_export_dispatch(source_toml: Path) -> Type2StepSpec:
    baseline = load_type2_step_spec(source_toml)
    columns_spec = ModeledTxRectVoidColumnsSpec(
        object_id="tx_rect_void_columns",
        role="tx_rect_void_columns",
        material="composite",
        model_state=True,
        pcb_thickness_mm=3.965,
        copper_thickness_mm=0.035,
        layer_count=RangeSpec(True, 1.0, 4.0, 4),
        layer_gap_mm=RangeSpec(False, 1.0, 1.8, 5),
        terminal_stub_length_mm=RangeSpec(False, 10.0, 10.0, 1),
        void_usage_ratio=RangeSpec(False, 0.2, 0.2, 1),
        margin_ratio=RangeSpec(False, 0.05, 0.05, 1),
        metal_fill_factor=RangeSpec(False, 0.5, 0.5, 1),
        terminal_path="A_cw_to_a",
        connection_mode=RangeSpec(True, 1.0, 1.0, 1),
        equivalent_turn_count=RangeSpec(False, 1.0, 1.0, 1),
        turn_weight_a=RangeSpec(False, 0.5, 1.5, 5),
        turn_weight_b=RangeSpec(False, -0.5, 0.5, 21),
        turn_weight_c=RangeSpec(False, -0.3, 0.3, 21),
    )
    return Type2StepSpec(
        source_toml_path=baseline.source_toml_path,
        simulation=baseline.simulation,
        outputs=baseline.outputs,
        non_model_objects=baseline.non_model_objects,
        non_model_derived_objects=baseline.non_model_derived_objects,
        modeled_objects=(columns_spec,),
        constraints=baseline.constraints,
    )


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


def _normalize_vector_xyz(vector_xyz: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = math.sqrt((vector_xyz[0] ** 2) + (vector_xyz[1] ** 2) + (vector_xyz[2] ** 2))
    assert norm > 0.0
    return (
        vector_xyz[0] / norm,
        vector_xyz[1] / norm,
        vector_xyz[2] / norm,
    )


def _dot_xyz(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    return (first[0] * second[0]) + (first[1] * second[1]) + (first[2] * second[2])


def _face_normal_closest_to_direction(
    *,
    shape: Shape,
    direction_xyz: tuple[float, float, float],
) -> tuple[float, float, float]:
    faces = tuple(shape.faces())
    assert len(faces) > 0
    target = _normalize_vector_xyz(direction_xyz)
    best_score = -2.0
    best_normal = (0.0, 0.0, 0.0)
    for face in faces:
        normal = face.normal_at()
        candidate = _normalize_vector_xyz((normal.X, normal.Y, normal.Z))
        score = _dot_xyz(candidate, target)
        if score > best_score:
            best_score = score
            best_normal = candidate
    return best_normal


def _cross_product_xyz(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        (first[1] * second[2]) - (first[2] * second[1]),
        (first[2] * second[0]) - (first[0] * second[2]),
        (first[0] * second[1]) - (first[1] * second[0]),
    )


def _prism_top_face_normal(
    tx_outer_prism: dict[str, object],
) -> tuple[float, float, float]:
    top_inner_start_xyz = cast(tuple[float, float, float], tx_outer_prism["top_inner_start_xyz"])
    top_outer_start_xyz = cast(tuple[float, float, float], tx_outer_prism["top_outer_start_xyz"])
    top_inner_end_xyz = cast(tuple[float, float, float], tx_outer_prism["top_inner_end_xyz"])
    top_edge_a = (
        top_outer_start_xyz[0] - top_inner_start_xyz[0],
        top_outer_start_xyz[1] - top_inner_start_xyz[1],
        top_outer_start_xyz[2] - top_inner_start_xyz[2],
    )
    top_edge_b = (
        top_inner_end_xyz[0] - top_inner_start_xyz[0],
        top_inner_end_xyz[1] - top_inner_start_xyz[1],
        top_inner_end_xyz[2] - top_inner_start_xyz[2],
    )
    normal = _cross_product_xyz(top_edge_a, top_edge_b)
    return _normalize_vector_xyz(normal)


def _tx_outer_prism_local_axes(
    tx_outer_prism: dict[str, object],
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
]:
    top_inner_start_xyz = cast(tuple[float, float, float], tx_outer_prism["top_inner_start_xyz"])
    top_outer_start_xyz = cast(tuple[float, float, float], tx_outer_prism["top_outer_start_xyz"])
    top_inner_end_xyz = cast(tuple[float, float, float], tx_outer_prism["top_inner_end_xyz"])
    bottom_inner_start_xyz = cast(tuple[float, float, float], tx_outer_prism["bottom_inner_start_xyz"])
    local_x = _normalize_vector_xyz(
        (
            top_outer_start_xyz[0] - top_inner_start_xyz[0],
            top_outer_start_xyz[1] - top_inner_start_xyz[1],
            top_outer_start_xyz[2] - top_inner_start_xyz[2],
        )
    )
    local_y = _normalize_vector_xyz(
        (
            top_inner_end_xyz[0] - top_inner_start_xyz[0],
            top_inner_end_xyz[1] - top_inner_start_xyz[1],
            top_inner_end_xyz[2] - top_inner_start_xyz[2],
        )
    )
    local_z = _normalize_vector_xyz(
        (
            bottom_inner_start_xyz[0] - top_inner_start_xyz[0],
            bottom_inner_start_xyz[1] - top_inner_start_xyz[1],
            bottom_inner_start_xyz[2] - top_inner_start_xyz[2],
        )
    )
    return top_inner_start_xyz, local_x, local_y, local_z


def _tx_outer_prism_local_bounds(
    tx_outer_prism: dict[str, object],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    top_inner_start_xyz = cast(tuple[float, float, float], tx_outer_prism["top_inner_start_xyz"])
    top_outer_start_xyz = cast(tuple[float, float, float], tx_outer_prism["top_outer_start_xyz"])
    top_inner_end_xyz = cast(tuple[float, float, float], tx_outer_prism["top_inner_end_xyz"])
    span_x = math.dist(top_inner_start_xyz, top_outer_start_xyz)
    span_y = math.dist(top_inner_start_xyz, top_inner_end_xyz)
    assert span_x > 0.0
    assert span_y > 0.0
    return (0.0, 0.0, 0.0), (span_x, span_y, 0.0)


def _project_to_tx_outer_prism_local(
    *,
    point_xyz: tuple[float, float, float],
    tx_outer_prism: dict[str, object],
) -> tuple[float, float, float]:
    origin_xyz, local_x, local_y, local_z = _tx_outer_prism_local_axes(tx_outer_prism)
    delta_xyz = (
        point_xyz[0] - origin_xyz[0],
        point_xyz[1] - origin_xyz[1],
        point_xyz[2] - origin_xyz[2],
    )
    return (
        _dot_xyz(delta_xyz, local_x),
        _dot_xyz(delta_xyz, local_y),
        _dot_xyz(delta_xyz, local_z),
    )


def _assert_points_inside_tx_outer_prism_local_bounds(
    *,
    points_xyz: tuple[tuple[float, float, float], ...],
    tx_outer_prism: dict[str, object],
    label: str,
    tolerance: float = 1e-6,
) -> None:
    assert points_xyz
    local_min_xyz, local_max_xyz = _tx_outer_prism_local_bounds(tx_outer_prism)
    for point_xyz in points_xyz:
        local_xyz = _project_to_tx_outer_prism_local(
            point_xyz=point_xyz,
            tx_outer_prism=tx_outer_prism,
        )
        assert local_xyz[0] >= local_min_xyz[0] - tolerance, f"{label} local x below prism: {local_xyz}"
        assert local_xyz[0] <= local_max_xyz[0] + tolerance, f"{label} local x above prism: {local_xyz}"
        assert local_xyz[1] >= local_min_xyz[1] - tolerance, f"{label} local y below prism: {local_xyz}"
        assert local_xyz[1] <= local_max_xyz[1] + tolerance, f"{label} local y above prism: {local_xyz}"


def _assert_tx_outer_points_use_prism_local_span(
    *,
    points_xyz: tuple[tuple[float, float, float], ...],
    tx_outer_prism: dict[str, object],
    label: str,
) -> None:
    assert points_xyz
    local_points = tuple(
        _project_to_tx_outer_prism_local(point_xyz=point_xyz, tx_outer_prism=tx_outer_prism)
        for point_xyz in points_xyz
    )
    local_span_x = max(point[0] for point in local_points) - min(point[0] for point in local_points)
    local_span_y = max(point[1] for point in local_points) - min(point[1] for point in local_points)
    assert local_span_x > 1e-6, f"{label} must occupy tx_outer_region_prism local x"
    assert local_span_y > 1e-6, f"{label} must occupy tx_outer_region_prism local y"


def _assert_tx_outer_actual_region_prism_local_x_position_ratio(
    *,
    actual_region_entry: Mapping[str, object],
    owner_entry: Mapping[str, object],
    x_position_ratio: float,
) -> None:
    tx_outer_prism = cast(dict[str, object], owner_entry["tx_outer_region_prism"])
    local_min_xyz, local_max_xyz = _tx_outer_prism_local_bounds(tx_outer_prism)
    actual_region = cast(dict[str, object], actual_region_entry["tx_actual_region"])
    actual_region_bounds = cast(dict[str, object], actual_region["actual_region_bounds"])
    actual_region_min_xyz = cast(tuple[float, float, float], actual_region_bounds["min_xyz"])
    x_usage_ratio = cast(float, actual_region["x_usage_ratio"])
    top_inner_start_xyz = cast(tuple[float, float, float], tx_outer_prism["top_inner_start_xyz"])
    top_outer_start_xyz = cast(tuple[float, float, float], tx_outer_prism["top_outer_start_xyz"])
    top_span_x = top_outer_start_xyz[0] - top_inner_start_xyz[0]
    top_span_z = top_outer_start_xyz[2] - top_inner_start_xyz[2]
    assert top_span_x > 0.0
    actual_region_top_min_z = top_inner_start_xyz[2] + (
        (actual_region_min_xyz[0] - top_inner_start_xyz[0]) / top_span_x
    ) * top_span_z
    actual_region_local_min_x = _project_to_tx_outer_prism_local(
        point_xyz=(actual_region_min_xyz[0], top_inner_start_xyz[1], actual_region_top_min_z),
        tx_outer_prism=tx_outer_prism,
    )
    local_size_x = (local_max_xyz[0] - local_min_xyz[0]) * x_usage_ratio
    target_min_x = local_min_xyz[0] + ((local_max_xyz[0] - local_min_xyz[0] - local_size_x) * x_position_ratio)
    assert actual_region_local_min_x[0] == pytest.approx(target_min_x)


def _assert_shape_has_face_normal_parallel_to(
    *,
    shape: Shape,
    target_normal_xyz: tuple[float, float, float],
    face_label: str,
    min_dot: float = 0.995,
    min_abs_target_x_component_ratio: float = 0.0,
) -> None:
    faces = tuple(shape.faces())
    assert len(faces) > 0
    target = _normalize_vector_xyz(target_normal_xyz)
    neg_target = (-target[0], -target[1], -target[2])
    best_score = -2.0
    best_normal = (0.0, 0.0, 0.0)
    for face in faces:
        normal = face.normal_at()
        candidate = _normalize_vector_xyz((normal.X, normal.Y, normal.Z))
        score = max(_dot_xyz(candidate, target), _dot_xyz(candidate, neg_target))
        if score > best_score:
            best_score = score
            best_normal = candidate
    assert min_dot <= 1.0
    assert min_abs_target_x_component_ratio >= 0.0
    assert best_score >= min_dot, f"no face in {face_label} is parallel to target normal: {target_normal_xyz}"
    if min_abs_target_x_component_ratio > 0.0:
        required_abs_x = abs(target[0]) * min_abs_target_x_component_ratio
        assert abs(best_normal[0]) >= required_abs_x - 1e-9, (
            f"no face in {face_label} preserves tilted-frame X component: "
            f"target={target_normal_xyz}, best={best_normal}"
        )


def _assert_shape_faces_axis_aligned(shape: Shape) -> None:
    for face in shape.faces():
        normal = face.normal_at()
        normal_xyz = (abs(normal.X), abs(normal.Y), abs(normal.Z))
        dominant_components = sum(1 for component in normal_xyz if component > 1.0 - 1e-9)
        minor_components = sum(1 for component in normal_xyz if component < 1e-9)
        assert dominant_components == 1
        assert minor_components == 2


def _assert_shape_has_no_face_normal_parallel_to(
    *,
    shape: Shape,
    target_normal_xyz: tuple[float, float, float],
    face_label: str,
    max_dot: float = 0.995,
) -> None:
    faces = tuple(shape.faces())
    assert len(faces) > 0
    target = _normalize_vector_xyz(target_normal_xyz)
    neg_target = (-target[0], -target[1], -target[2])
    best_score = -2.0
    best_normal = (0.0, 0.0, 0.0)
    for face in faces:
        normal = face.normal_at()
        candidate = _normalize_vector_xyz((normal.X, normal.Y, normal.Z))
        score = max(_dot_xyz(candidate, target), _dot_xyz(candidate, neg_target))
        if score > best_score:
            best_score = score
            best_normal = candidate
    assert best_score < max_dot, (
        f"face in {face_label} unexpectedly aligns to target normal: "
        f"target={target_normal_xyz}, best={best_normal}, score={best_score}"
    )


def _iter_shape_tree(shape: Shape) -> tuple[Shape, ...]:
    descendants: list[Shape] = [shape]
    for child in shape.children:
        descendants.extend(_iter_shape_tree(cast(Shape, child)))
    return tuple(descendants)


def _step_shapes_by_label(step_path: Path) -> dict[str, Shape]:
    imported_scene = bd.import_step(step_path)
    top_level_children = tuple(imported_scene.children)
    roots = top_level_children if len(top_level_children) != 0 else (cast(Shape, imported_scene),)
    shapes_by_label: dict[str, Shape] = {}
    for root in roots:
        for shape in _iter_shape_tree(cast(Shape, root)):
            if shape.label == "" or shape.label == "SOLID":
                continue
            if shape.label in shapes_by_label:
                raise AssertionError(f"duplicate STEP label found during recursive scan: {shape.label}")
            shapes_by_label[shape.label] = shape
    return shapes_by_label


def _plate_stack_top_level_expected_body_names(
    *,
    role: Literal["tx_plate_stack", "rx_plate_stack"],
    turn_count: int,
    pcb_total_thickness_mm: float,
) -> tuple[str, ...]:
    expected_names = expected_plate_stack_body_names(
        role=role,
        turn_count=turn_count,
        pcb_total_thickness_mm=pcb_total_thickness_mm,
    )
    expected_groups = (
        _tx_plate_stack_expected_body_groups()
        if role == "tx_plate_stack"
        else _rx_plate_stack_expected_body_groups()
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


def _tx_inner_expected_body_names(
    *,
    layer_count: int,
    underlay_repeat_count: int = 0,
    void_stack_count: int = 0,
) -> tuple[str, ...]:
    names = [f"tx_inner_pcb_l{index}" for index in range(layer_count)]
    if layer_count == 1:
        names.append("tx_inner_copper_l0")
    else:
        names.append("tx_inner_copper_stack")
    for repeat_index in range(underlay_repeat_count):
        names.append(f"tx_underlay_pet_psa_u{repeat_index}")
        names.append(f"tx_underlay_ferrite_u{repeat_index}")
    for void_index in range(void_stack_count):
        if void_index % 2 == 0:
            names.append(f"tx_void_ferrite_u{void_index // 2}")
        else:
            names.append(f"tx_void_pet_psa_u{void_index // 2}")
    return tuple(names)


def _tx_outer_expected_base_body_names(*, layer_count: int) -> tuple[str, ...]:
    names = [f"tx_outer_pcb_l{index}" for index in range(layer_count)]
    if layer_count == 1:
        names.append("tx_outer_copper_l0")
    else:
        names.append("tx_outer_copper_stack")
    return tuple(names)


def _rx_expected_body_names(*, underlay_repeat_count: int) -> tuple[str, ...]:
    names = ["rx_pcb_l0", "rx_copper_l0"]
    names.extend(_rx_underlay_expected_body_names(repeat_count=underlay_repeat_count))
    return tuple(names)


def _ferrite_group_name_for_modeled_role(
    *,
    role: Literal["tx_single_coil", "rx_single_coil"],
) -> str:
    if role == "tx_single_coil":
        return _TX_FERRITE_GROUP_NAME
    if role == "rx_single_coil":
        return _RX_FERRITE_GROUP_NAME
    raise RuntimeError(f"unsupported ferrite grouping role in test helper: {role}")


def _expected_ferrite_body_groups(
    *,
    role: Literal["tx_single_coil", "rx_single_coil"],
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
    turn_count: int,
    pcb_total_thickness_mm: float = _PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
) -> tuple[str, ...]:
    return expected_plate_stack_body_names(
        role="rx_plate_stack",
        turn_count=turn_count,
        pcb_total_thickness_mm=pcb_total_thickness_mm,
    )


def _tx_plate_stack_expected_body_names(
    *,
    turn_count: int,
    pcb_total_thickness_mm: float = _PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
) -> tuple[str, ...]:
    return expected_plate_stack_body_names(
        role="tx_plate_stack",
        turn_count=turn_count,
        pcb_total_thickness_mm=pcb_total_thickness_mm,
    )


def _tx_plate_stack_expected_body_groups() -> tuple[ExportedBodyGroup, ...]:
    return (
        {
            "group_name": _TX_COPPER_GROUP_NAME,
            "member_body_names": ("tx_plate_copper",),
        },
        {
            "group_name": _TX_FERRITE_GROUP_NAME,
            "member_body_names": (
                "tx_stack_pet_psa",
                "tx_stack_ferrite",
                "tx_stack_air",
            ),
        },
    )


def _rx_plate_stack_expected_body_groups() -> tuple[ExportedBodyGroup, ...]:
    return (
        {
            "group_name": _RX_COPPER_GROUP_NAME,
            "member_body_names": ("rx_plate_copper",),
        },
        {
            "group_name": _RX_FERRITE_GROUP_NAME,
            "member_body_names": (
                "rx_stack_pet_psa",
                "rx_stack_ferrite",
                "rx_stack_air",
            ),
        },
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
    assert isinstance(first, Shape)
    assert isinstance(second, Shape)
    first_shape = cast(Shape, first)
    second_shape = cast(Shape, second)
    shared_shape = first_shape.intersect(second_shape)
    if shared_shape is None:
        return
    assert isinstance(shared_shape, Shape)
    assert sum(solid.volume for solid in shared_shape.solids()) == pytest.approx(0.0, abs=1e-9)


def _assert_ferrite_family_pcb_clearance_contract(
    *,
    scene_shapes_by_label: dict[str, Shape],
    ferrite_group_name: str,
    ferrite_member_names: tuple[str, ...],
    pcb_body_names: tuple[str, ...],
) -> None:
    ferrite_group = scene_shapes_by_label[ferrite_group_name]
    assert type(ferrite_group).__name__ == "Compound"
    assert tuple(cast(Shape, child).label for child in ferrite_group.children) == ferrite_member_names

    for ferrite_member_name in ferrite_member_names:
        ferrite_shape = scene_shapes_by_label[ferrite_member_name]
        assert len(tuple(ferrite_shape.solids())) == 1
        assert _shape_volume(ferrite_shape) > 0.0
    for pcb_body_name in pcb_body_names:
        pcb_shape = scene_shapes_by_label[pcb_body_name]
        assert len(tuple(pcb_shape.solids())) == 1
        assert _shape_volume(pcb_shape) > 0.0

    for ferrite_member_name in ferrite_member_names:
        ferrite_shape = scene_shapes_by_label[ferrite_member_name]
        for pcb_body_name in pcb_body_names:
            pcb_shape = scene_shapes_by_label[pcb_body_name]
            shared_shape = ferrite_shape.intersect(pcb_shape)
            if shared_shape is None:
                continue
            assert isinstance(shared_shape, Shape)
            shared_volume = sum(solid.volume for solid in shared_shape.solids())
            assert shared_volume == pytest.approx(0.0, abs=1e-9), (
                "ferrite-family body must not retain positive-volume PCB overlap "
                f"(ferrite_body={ferrite_member_name}, pcb_body={pcb_body_name}, volume={shared_volume})"
            )


def _tx_region_actual_tile_names(*, x_division_count: int, y_division_count: int) -> tuple[str, ...]:
    if x_division_count == 1 and y_division_count == 1:
        return ("tx_region_actual",)
    return tuple(
        f"tx_region_actual_x{x_index}_y{y_index}"
        for x_index in range(x_division_count)
        for y_index in range(y_division_count)
    )


def _tx_region_actual_stack_space_tile_names(*, x_division_count: int, y_division_count: int) -> tuple[str, ...]:
    if x_division_count == 1 and y_division_count == 1:
        return ("tx_region_actual_stack_space",)
    return tuple(
        f"tx_region_actual_stack_space_x{x_index}_y{y_index}"
        for x_index in range(x_division_count)
        for y_index in range(y_division_count)
    )


def _assert_tx_region_actual_tiles_contract(
    *,
    scene_shapes_by_label: dict[str, Shape],
    tile_names: tuple[str, ...],
    expected_origin_xyz: tuple[float, float, float],
    expected_size_xyz: tuple[float, float, float],
) -> None:
    tile_boxes = [scene_shapes_by_label[name].bounding_box() for name in tile_names]
    min_x = min(box.min.X for box in tile_boxes)
    min_y = min(box.min.Y for box in tile_boxes)
    min_z = min(box.min.Z for box in tile_boxes)
    max_x = max(box.max.X for box in tile_boxes)
    max_y = max(box.max.Y for box in tile_boxes)
    max_z = max(box.max.Z for box in tile_boxes)
    assert (min_x, min_y, min_z) == pytest.approx(expected_origin_xyz)
    assert (max_x - min_x, max_y - min_y, max_z - min_z) == pytest.approx(expected_size_xyz)
    for first_index in range(len(tile_names)):
        first_box = tile_boxes[first_index]
        for second_index in range(first_index + 1, len(tile_names)):
            second_box = tile_boxes[second_index]
            overlap_x = min(first_box.max.X, second_box.max.X) - max(first_box.min.X, second_box.min.X)
            overlap_y = min(first_box.max.Y, second_box.max.Y) - max(first_box.min.Y, second_box.min.Y)
            overlap_z = min(first_box.max.Z, second_box.max.Z) - max(first_box.min.Z, second_box.min.Z)
            assert overlap_x <= 1e-9 or overlap_y <= 1e-9 or overlap_z <= 1e-9


def _shape_volume(shape: Shape) -> float:
    return sum(solid.volume for solid in shape.solids())


def _modeled_volume_signature(
    *,
    scene_shapes_by_label: dict[str, Shape],
    modeled_expected_names: Sequence[str],
) -> tuple[tuple[str, float], ...]:
    return tuple((name, _shape_volume(scene_shapes_by_label[name])) for name in modeled_expected_names)


def _assert_modeled_bodies_within_tx_region_actual_stack_space(
    *,
    ledger: dict[str, object],
    modeled_object_id: str,
) -> None:
    non_model_entry = cast(dict[str, object], cast(list[object], ledger["non_model_objects"])[0])
    member_objects = cast(list[object], non_model_entry["member_objects"])
    stack_space_members = [
        cast(dict[str, object], member)
        for member in member_objects
        if cast(str, cast(dict[str, object], member)["role"]) == "tx_region_actual_stack_space"
    ]
    assert len(stack_space_members) > 0
    stack_space_boxes = []
    for member in stack_space_members:
        canonical = cast(dict[str, object], member["canonical_coordinates"])
        min_xyz = cast(tuple[float, float, float], canonical["outer_bounds_min_xyz"])
        max_xyz = cast(tuple[float, float, float], canonical["outer_bounds_max_xyz"])
        stack_space_boxes.append((min_xyz, max_xyz))
    modeled_entry = next(
        cast(dict[str, object], entry)
        for entry in cast(list[object], ledger["modeled_objects"])
        if cast(dict[str, object], entry)["object_id"] == modeled_object_id
    )
    expected_names = cast(tuple[str, ...], modeled_entry["expected_exported_body_names"])
    scene_shapes_by_label = _step_shapes_by_label(Path(cast(str, ledger["scene_step_path"])))
    containment_tolerance_mm = 5e-2
    for body_name in expected_names:
        body_shape = scene_shapes_by_label[body_name]
        body_bbox = body_shape.bounding_box()
        contained = False
        for stack_space_min_xyz, stack_space_max_xyz in stack_space_boxes:
            if (
                body_bbox.min.X >= stack_space_min_xyz[0] - containment_tolerance_mm
                and body_bbox.max.X <= stack_space_max_xyz[0] + containment_tolerance_mm
                and body_bbox.min.Y >= stack_space_min_xyz[1] - containment_tolerance_mm
                and body_bbox.max.Y <= stack_space_max_xyz[1] + containment_tolerance_mm
                and body_bbox.min.Z >= stack_space_min_xyz[2] - containment_tolerance_mm
                and body_bbox.max.Z <= stack_space_max_xyz[2] + containment_tolerance_mm
            ):
                contained = True
                break
        assert contained, f"modeled body must fit inside one stack-space tile (body={body_name})"


def _assert_tx_rect_void_columns_bodies_within_stack_space_allowing_stub_protrusion(
    *,
    ledger: dict[str, object],
    modeled_object_id: str,
) -> None:
    non_model_entry = cast(dict[str, object], cast(list[object], ledger["non_model_objects"])[0])
    member_objects = cast(list[object], non_model_entry["member_objects"])
    stack_space_members = [
        cast(dict[str, object], member)
        for member in member_objects
        if cast(str, cast(dict[str, object], member)["role"]) == "tx_region_actual_stack_space"
    ]
    assert len(stack_space_members) > 0
    stack_space_boxes = []
    for member in stack_space_members:
        canonical = cast(dict[str, object], member["canonical_coordinates"])
        min_xyz = cast(tuple[float, float, float], canonical["outer_bounds_min_xyz"])
        max_xyz = cast(tuple[float, float, float], canonical["outer_bounds_max_xyz"])
        stack_space_boxes.append((min_xyz, max_xyz))

    modeled_entry = next(
        cast(dict[str, object], entry)
        for entry in cast(list[object], ledger["modeled_objects"])
        if cast(dict[str, object], entry)["object_id"] == modeled_object_id
    )
    expected_names = cast(tuple[str, ...], modeled_entry["expected_exported_body_names"])
    scene_shapes_by_label = _step_shapes_by_label(Path(cast(str, ledger["scene_step_path"])))
    containment_tolerance_mm = 5e-2
    for body_name in expected_names:
        body_shape = scene_shapes_by_label[body_name]
        if ("_pcb_l" in body_name or "_cu_l" in body_name) and "_stub_" not in body_name:
            body_bbox = body_shape.bounding_box()
            contained = False
            for stack_space_min_xyz, stack_space_max_xyz in stack_space_boxes:
                if (
                    body_bbox.min.X >= stack_space_min_xyz[0] - containment_tolerance_mm
                    and body_bbox.max.X <= stack_space_max_xyz[0] + containment_tolerance_mm
                    and body_bbox.min.Y >= stack_space_min_xyz[1] - containment_tolerance_mm
                    and body_bbox.max.Y <= stack_space_max_xyz[1] + containment_tolerance_mm
                    and body_bbox.min.Z >= stack_space_min_xyz[2] - containment_tolerance_mm
                    and body_bbox.max.Z <= stack_space_max_xyz[2] + containment_tolerance_mm
                ):
                    contained = True
                    break
            assert contained, f"modeled body must fit inside one stack-space tile (body={body_name})"


def _stub_body_touches_or_overlaps_all_layer_anchors(
    *,
    stub_shape: Shape,
    scene_shapes_by_label: dict[str, Shape],
    tile_pcb_cu_labels: tuple[tuple[tuple[int, int], tuple[str, str]], ...],
    tolerance_mm: float = 1e-2,
) -> None:
    stub_bbox = stub_shape.bounding_box()
    for tile_index, pcb_and_copper_labels in tile_pcb_cu_labels:
        connected_for_layer = False
        for anchor_label in pcb_and_copper_labels:
            anchor_shape = scene_shapes_by_label[anchor_label]
            anchor_bbox = anchor_shape.bounding_box()
            overlaps = (
                stub_bbox.max.X >= anchor_bbox.min.X - tolerance_mm
                and stub_bbox.min.X <= anchor_bbox.max.X + tolerance_mm
                and stub_bbox.max.Y >= anchor_bbox.min.Y - tolerance_mm
                and stub_bbox.min.Y <= anchor_bbox.max.Y + tolerance_mm
                and stub_bbox.max.Z >= anchor_bbox.min.Z - tolerance_mm
                and stub_bbox.min.Z <= anchor_bbox.max.Z + tolerance_mm
            )
            if overlaps:
                connected_for_layer = True
                break
        assert connected_for_layer, (
            f"terminal stub must overlap each layer anchor set (stub={stub_shape.label})"
        )


def _assert_plate_stack_bridge_non_overlap(
    *,
    scene_shapes_by_label: dict[str, Shape],
    prefix: Literal["tx", "rx"],
    turn_count: int,
) -> None:
    bridge_labels = tuple(f"{prefix}_bridge_s{index}" for index in range((2 * turn_count) - 1))
    copper_labels = (
        *(f"{prefix}_copper_wall_t{index}" for index in range(turn_count)),
        *(f"{prefix}_copper_coil_t{index}" for index in range(turn_count)),
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
    max_edge_bridge_labels = tuple(f"{prefix}_bridge_s{index}" for index in range(0, (2 * turn_count) - 1, 2))
    min_edge_bridge_labels = tuple(f"{prefix}_bridge_s{index}" for index in range(1, (2 * turn_count) - 1, 2))
    for labels_for_one_edge in (max_edge_bridge_labels, min_edge_bridge_labels):
        for first_index in range(len(labels_for_one_edge)):
            for second_index in range(first_index + 1, len(labels_for_one_edge)):
                _assert_zero_intersection_volume(
                    scene_shapes_by_label[labels_for_one_edge[first_index]],
                    scene_shapes_by_label[labels_for_one_edge[second_index]],
                )


def _plate_stack_pitch_z(*, owner_size_z: float, turn_count: int) -> float:
    assert turn_count >= 2
    return owner_size_z / float(turn_count + 0.5)


def _plate_stack_active_z_bounds(
    *,
    role: Literal["tx_plate_stack", "rx_plate_stack"],
    owner_origin_z: float,
    owner_size_z: float,
    z_usage_ratio: float,
) -> tuple[float, float, float]:
    active_size_z = owner_size_z * z_usage_ratio
    assert active_size_z > 0.0
    if role == "tx_plate_stack":
        active_min_z = owner_origin_z + owner_size_z - active_size_z
    else:
        active_min_z = owner_origin_z
    return active_min_z, active_min_z + active_size_z, active_size_z


def _plate_stack_active_y_bounds(
    *,
    owner_size_y: float,
    y_usage_ratio: float,
) -> tuple[float, float, float]:
    assert owner_size_y > 0.0
    active_size_y = owner_size_y * y_usage_ratio
    assert active_size_y > 0.0
    active_min_y = -active_size_y / 2.0
    return active_min_y, active_min_y + active_size_y, active_size_y


def _assert_plate_stack_united_ferrite_family_contract(
    *,
    scene_shapes_by_label: dict[str, Shape],
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
    wall_label = f"{prefix}_pcb_wall"
    pet_label = f"{prefix}_stack_pet_psa"
    ferrite_label = f"{prefix}_stack_ferrite"
    air_label = f"{prefix}_stack_air"
    coil_label = f"{prefix}_pcb_coil"
    wall_max_x = scene_shapes_by_label[wall_label].bounding_box().max.X
    pet_min_x = scene_shapes_by_label[pet_label].bounding_box().min.X
    pet_max_x = scene_shapes_by_label[pet_label].bounding_box().max.X
    ferrite_min_x = scene_shapes_by_label[ferrite_label].bounding_box().min.X
    ferrite_max_x = scene_shapes_by_label[ferrite_label].bounding_box().max.X
    air_min_x = scene_shapes_by_label[air_label].bounding_box().min.X
    air_max_x = scene_shapes_by_label[air_label].bounding_box().max.X
    coil_min_x = scene_shapes_by_label[coil_label].bounding_box().min.X
    assert wall_max_x == pytest.approx(pet_min_x)
    assert pet_max_x == pytest.approx(ferrite_min_x)
    assert ferrite_max_x == pytest.approx(air_min_x)
    assert air_max_x == pytest.approx(coil_min_x)
    assert (pet_max_x - pet_min_x) == pytest.approx(1.5)
    assert (ferrite_max_x - ferrite_min_x) == pytest.approx(2.0)
    assert (air_max_x - air_min_x) == pytest.approx(0.2)
    assert all(not label.startswith(f"{prefix}_stack_pet_psa_u") for label in scene_shapes_by_label)
    assert all(not label.startswith(f"{prefix}_stack_ferrite_u") for label in scene_shapes_by_label)
    assert all(not label.startswith(f"{prefix}_stack_air_u") for label in scene_shapes_by_label)


def _assert_rx_full_backing_contract(
    *,
    scene_shapes_by_label: dict[str, Shape],
    rx_region_size_x: float,
) -> None:
    underlay_labels = (
        "under_rx_pet_psa_u0",
        "under_rx_ferrite_u0",
        "under_rx_air_u0",
    )
    assert all(label in scene_shapes_by_label for label in underlay_labels)
    ferrite_group = scene_shapes_by_label[_RX_FERRITE_GROUP_NAME]
    assert type(ferrite_group).__name__ == "Compound"
    assert {child.label for child in ferrite_group.children} == set(underlay_labels)

    rx_pcb_shape = scene_shapes_by_label["rx_pcb_l0"]
    rx_copper_shape = scene_shapes_by_label["rx_copper_l0"]
    for underlay_label in underlay_labels:
        underlay_shape = scene_shapes_by_label[underlay_label]
        _assert_zero_intersection_volume(underlay_shape, rx_pcb_shape)
        _assert_zero_intersection_volume(underlay_shape, rx_copper_shape)

    pet_bbox = scene_shapes_by_label["under_rx_pet_psa_u0"].bounding_box()
    ferrite_bbox = scene_shapes_by_label["under_rx_ferrite_u0"].bounding_box()
    air_bbox = scene_shapes_by_label["under_rx_air_u0"].bounding_box()
    pcb_bbox = rx_pcb_shape.bounding_box()
    copper_bbox = rx_copper_shape.bounding_box()
    coil_min_x = min(pcb_bbox.min.X, copper_bbox.min.X)
    coil_max_x = max(pcb_bbox.max.X, copper_bbox.max.X)
    coil_thickness = coil_max_x - coil_min_x
    pet_thickness = pet_bbox.max.X - pet_bbox.min.X
    ferrite_thickness = ferrite_bbox.max.X - ferrite_bbox.min.X
    air_thickness = air_bbox.max.X - air_bbox.min.X
    total_underlay_thickness = pet_thickness + ferrite_thickness + air_thickness
    expected_total_underlay_thickness = rx_region_size_x - coil_thickness
    assert total_underlay_thickness == pytest.approx(expected_total_underlay_thickness)
    assert air_bbox.max.X == pytest.approx(pet_bbox.min.X)
    assert pet_bbox.max.X == pytest.approx(ferrite_bbox.min.X)
    assert ferrite_bbox.max.X == pytest.approx(coil_min_x)

    ratio_denominator = 1.5 + 2.0 + 0.2
    assert pet_thickness == pytest.approx(expected_total_underlay_thickness * (1.5 / ratio_denominator))
    assert ferrite_thickness == pytest.approx(expected_total_underlay_thickness * (2.0 / ratio_denominator))
    assert air_thickness == pytest.approx(expected_total_underlay_thickness * (0.2 / ratio_denominator))


def _assert_plate_stack_united_copper_group_contract(
    *,
    scene_shapes_by_label: dict[str, Shape],
    prefix: Literal["tx", "rx"],
) -> None:
    group_label = _TX_COPPER_GROUP_NAME if prefix == "tx" else _RX_COPPER_GROUP_NAME
    member_label = f"{prefix}_plate_copper"
    group_shape = scene_shapes_by_label[group_label]
    assert type(group_shape).__name__ == "Compound"
    assert tuple(child.label for child in group_shape.children) == (member_label,)
    member_shape = scene_shapes_by_label[member_label]
    assert type(member_shape).__name__ == "Solid"
    assert len(tuple(member_shape.solids())) == 1


def _single_coil_placement_offset_from_local_bounds(
    *,
    owner_object_id: str,
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
        target_world_min_x = (
            owner_origin_xyz[0]
            if owner_object_id == "tx_region"
            else owner_origin_xyz[0] + (owner_size_xyz[0] - world_size_xyz[0]) / 2.0
        )
        target_world_min_xyz = (
            target_world_min_x,
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
    assert modeled_spec.role in ("tx_single_coil", "tx_inner_single_coil", "rx_single_coil")
    profile = profile_for_modeled_role(
        cast(Literal["tx_single_coil", "tx_inner_single_coil", "rx_single_coil"], modeled_spec.role)
    )
    resolved_non_model_specs = resolve_non_model_scene_specs(
        base_specs=type2_spec.non_model_objects,
        derived_specs=type2_spec.non_model_derived_objects,
        seed=seed,
    )
    owner_spec = next(
        spec for spec in resolved_non_model_specs if spec.object_id == profile.placement_owner_id
    )
    fit_envelope = resolve_modeled_single_coil_fit_envelope(
        cast(ModeledSingleCoilSpec, modeled_spec),
        owner_spec=owner_spec,
        seed=seed,
    )
    if profile.role in ("tx_single_coil", "tx_inner_single_coil"):
        terminal_stub_boxes = _synthetic_tx_bus_owner_boxes(local_boxes=fit_envelope.transformed_boxes)
    else:
        terminal_stub_boxes = tuple(box for box in fit_envelope.transformed_boxes if box.feature == "terminal_stub")
    return tuple(
        (box.origin_xyz, box.size_xyz)
        for box in terminal_stub_boxes
    )


def _shape_vertices(step_path: Path, *, label: str) -> tuple[tuple[float, float, float], ...]:
    shapes_by_label = _step_shapes_by_label(step_path)
    matches = [shape for shape_label, shape in shapes_by_label.items() if shape_label == label]
    assert len(matches) == 1
    shape = cast(Shape, matches[0])
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


def _terminal_edge_from_sheet_vertices(
    *,
    sheet_vertices: tuple[tuple[float, float, float], ...],
    edge_role: Literal["signal", "reference"],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    assert len(sheet_vertices) == 4
    if edge_role == "signal":
        start_xyz = sheet_vertices[3]
        end_xyz = sheet_vertices[0]
    elif edge_role == "reference":
        start_xyz = sheet_vertices[1]
        end_xyz = sheet_vertices[2]
    else:
        raise AssertionError(f"unsupported terminal edge role: {edge_role}")
    edge_length_sq = (
        (end_xyz[0] - start_xyz[0]) ** 2
        + (end_xyz[1] - start_xyz[1]) ** 2
        + (end_xyz[2] - start_xyz[2]) ** 2
    )
    assert edge_length_sq > 1e-18
    return start_xyz, end_xyz


def _edge_vertex_set_from_sheet_vertices(
    *,
    sheet_vertices: tuple[tuple[float, float, float], ...],
    edge_role: Literal["signal", "reference"],
) -> set[tuple[float, float, float]]:
    edge = _terminal_edge_from_sheet_vertices(sheet_vertices=sheet_vertices, edge_role=edge_role)
    return _rounded_vertex_set(vertices=(edge[0], edge[1]))


def _edge_vertex_set_from_sheet_metadata(
    *,
    terminal_metadata: dict[str, object],
    edge_role: Literal["signal", "reference"],
) -> set[tuple[float, float, float]]:
    raw_vertices = cast(
        list[list[float]],
        terminal_metadata["port_sheet_vertices_xyz"],
    )
    return _edge_vertex_set_from_sheet_vertices(
        sheet_vertices=_vertex_triplets(raw_vertices),
        edge_role=edge_role,
    )


def _rounded_vertex_set(
    vertices: tuple[tuple[float, float, float], ...],
) -> set[tuple[float, float, float]]:
    return {(round(vertex[0], 8), round(vertex[1], 8), round(vertex[2], 8)) for vertex in vertices}


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
    assert spec.outputs["mode"] == "TxRx"
    assert tuple(variable["name"] for variable in spec.outputs["variables"]) == _TXRX_OUTPUT_NAMES
    assert len(spec.non_model_objects) == 6
    assert len(spec.modeled_objects) == 2
    tx_region_entry = next(entry for entry in spec.non_model_objects if entry.object_id == "tx_region")
    assert isinstance(tx_region_entry, NonModelTxRegionSpec)
    assert tx_region_entry.origin_xyz == pytest.approx((0.0, -900.0, 0.0))
    assert tx_region_entry.size_xyz == pytest.approx((160.0, 1800.0, 90.0))
    assert tx_region_entry.tx_reference_line.x_ratio == RangeSpec(False, 0.99, 0.99, 1)
    assert tx_region_entry.tx_reference_line.y_usage_ratio == RangeSpec(False, 1.0, 1.0, 1)
    tx_inner_entry = next(entry for entry in spec.modeled_objects if entry.object_id == "tx_inner_rect_void_coil")
    assert tx_inner_entry.role == "tx_inner_single_coil"
    assert tx_inner_entry.pcb_thickness_mm == pytest.approx(0.3)
    assert tx_inner_entry.copper_thickness_mm == pytest.approx(0.035)
    assert tx_inner_entry.outer_x_usage_ratio.start == pytest.approx(0.9)
    assert tx_inner_entry.outer_y_usage_ratio.start == pytest.approx(0.9)
    assert tx_inner_entry.x_position_ratio.start == pytest.approx(0.0)
    assert tx_inner_entry.x_position_ratio.end == pytest.approx(0.0)
    assert tx_inner_entry.x_position_ratio.count == 1
    assert tx_inner_entry.turn_count.start == pytest.approx(1.0)
    assert tx_inner_entry.layer_count.start == pytest.approx(1.0)
    assert tx_inner_entry.layer_gap_mm.start == pytest.approx(3.0)
    assert tx_inner_entry.underlay_repeat_count.start == pytest.approx(1.0)
    assert tx_inner_entry.underlay_repeat_count.end == pytest.approx(1.0)
    assert tx_inner_entry.underlay_repeat_count.count == 1
    assert tx_inner_entry.underlay_pet_psa_thickness_mm == RangeSpec(False, 2.0, 2.0, 1)
    assert tx_inner_entry.underlay_ferrite_thickness_mm == RangeSpec(False, 2.0, 2.0, 1)
    assert all(entry.object_id != "tx_outer_rect_void_coil" for entry in spec.modeled_objects)
    assert all(entry.role != "tx_outer_single_coil" for entry in spec.modeled_objects)
    rx_entry = next(entry for entry in spec.modeled_objects if entry.object_id == "rx_rect_void_coil")
    assert rx_entry.object_id == "rx_rect_void_coil"
    assert rx_entry.role == "rx_single_coil"
    assert rx_entry.pcb_thickness_mm == pytest.approx(3.965)
    assert rx_entry.copper_thickness_mm == pytest.approx(0.035)
    assert rx_entry.outer_x_usage_ratio.start == pytest.approx(1.0)
    assert rx_entry.outer_y_usage_ratio.start == pytest.approx(0.6)
    assert rx_entry.outer_x_mm.start == pytest.approx(1800.0)
    assert rx_entry.outer_y_mm.start == pytest.approx(216.0)
    assert rx_entry.turn_count.start == pytest.approx(1.0)
    assert rx_entry.layer_count.start == pytest.approx(1.0)
    assert rx_entry.underlay_repeat_count.start == pytest.approx(8.0)
    assert rx_entry.underlay_repeat_count.end == pytest.approx(8.0)
    assert rx_entry.underlay_repeat_count.count == 1
    assert rx_entry.void_usage_ratio.start == pytest.approx(0.2)
    assert rx_entry.void_usage_ratio.end == pytest.approx(0.2)
    assert rx_entry.void_usage_ratio.count == 1
    assert rx_entry.metal_fill_factor.start == pytest.approx(0.5142857142857142)


def test_load_example_type2_toml_preserves_rx_single_coil_contract() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_fixed.toml"
    spec = load_type2_step_spec(source_toml)

    assert len(spec.modeled_objects) == 2
    tx_inner_entry = next(entry for entry in spec.modeled_objects if entry.object_id == "tx_inner_rect_void_coil")
    assert tx_inner_entry.object_id == "tx_inner_rect_void_coil"
    assert tx_inner_entry.role == "tx_inner_single_coil"
    assert tx_inner_entry.layer_count.start == pytest.approx(1.0)
    assert tx_inner_entry.layer_count.end == pytest.approx(1.0)
    assert tx_inner_entry.layer_count.count == 1
    assert tx_inner_entry.underlay_repeat_count.start == pytest.approx(1.0)
    assert tx_inner_entry.underlay_repeat_count.end == pytest.approx(1.0)
    assert tx_inner_entry.underlay_repeat_count.count == 1
    assert tx_inner_entry.underlay_pet_psa_thickness_mm == RangeSpec(False, 2.0, 2.0, 1)
    assert tx_inner_entry.underlay_ferrite_thickness_mm == RangeSpec(False, 2.0, 2.0, 1)
    assert tx_inner_entry.terminal_path == "B_cw_to_b"
    assert tx_inner_entry.terminal_stub_length_mm == RangeSpec(False, 7.5, 7.5, 1)
    tx_inner_profile = profile_for_modeled_role(cast(Literal["tx_inner_single_coil"], tx_inner_entry.role))
    assert tx_inner_profile.plane == "XY"
    assert tx_inner_profile.object_id == "tx_inner_rect_void_coil"
    assert tx_inner_profile.placement_owner_id == "tx_inner_region"
    assert all(entry.object_id != "tx_outer_rect_void_coil" for entry in spec.modeled_objects)
    assert all(entry.role != "tx_outer_single_coil" for entry in spec.modeled_objects)
    rx_entry = next(entry for entry in spec.modeled_objects if entry.object_id == "rx_rect_void_coil")
    assert rx_entry.object_id == "rx_rect_void_coil"
    assert rx_entry.role == "rx_single_coil"
    assert rx_entry.layer_count.start == pytest.approx(1.0)
    assert rx_entry.layer_count.end == pytest.approx(1.0)
    assert rx_entry.layer_count.count == 1
    assert rx_entry.underlay_repeat_count.start == pytest.approx(8.0)
    assert rx_entry.underlay_repeat_count.end == pytest.approx(8.0)
    assert rx_entry.underlay_repeat_count.count == 1
    assert rx_entry.void_usage_ratio.start == pytest.approx(0.2)
    assert rx_entry.void_usage_ratio.end == pytest.approx(0.2)
    assert rx_entry.void_usage_ratio.count == 1
    assert rx_entry.terminal_path == "A_cw_to_a"
    rx_profile = profile_for_modeled_role(cast(Literal["rx_single_coil"], rx_entry.role))
    assert rx_profile.plane == "YZ"
    assert rx_profile.object_id == "rx_rect_void_coil"
    assert rx_profile.placement_owner_id == "rx_region_max"


def test_load_type2_step_spec_rejects_duplicate_object_id(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(modeled_object_id="floor"))

    with pytest.raises(ValueError, match=r"duplicate object id: floor"):
        load_type2_step_spec(toml_path)


def test_load_type2_sweep_toml_preserves_rx_single_coil_contract() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_sweep.toml"
    spec = load_type2_step_spec(source_toml)

    assert len(spec.modeled_objects) == 2
    assert len(spec.non_model_objects) >= 2
    tx_inner_entry = next(entry for entry in spec.modeled_objects if entry.object_id == "tx_inner_rect_void_coil")
    assert tx_inner_entry.role == "tx_inner_single_coil"
    assert tx_inner_entry.layer_count.start == pytest.approx(1.0)
    assert tx_inner_entry.layer_count.end == pytest.approx(5.0)
    assert tx_inner_entry.layer_count.count == 5
    assert tx_inner_entry.underlay_repeat_count.start == pytest.approx(1.0)
    assert tx_inner_entry.underlay_repeat_count.end == pytest.approx(1.0)
    assert tx_inner_entry.underlay_repeat_count.count == 1
    assert tx_inner_entry.underlay_pet_psa_thickness_mm == RangeSpec(False, 6.0, 6.0, 1)
    assert tx_inner_entry.underlay_ferrite_thickness_mm == RangeSpec(False, 6.0, 6.0, 1)
    assert tx_inner_entry.outer_x_usage_ratio == RangeSpec(False, 0.4, 0.9, 75)
    assert tx_inner_entry.outer_y_usage_ratio == RangeSpec(False, 0.2, 0.9, 150)
    assert all(entry.object_id != "tx_outer_rect_void_coil" for entry in spec.modeled_objects)
    assert all(entry.role != "tx_outer_single_coil" for entry in spec.modeled_objects)
    rx_entry = next(entry for entry in spec.modeled_objects if entry.object_id == "rx_rect_void_coil")
    assert rx_entry.object_id == "rx_rect_void_coil"
    assert rx_entry.role == "rx_single_coil"
    assert rx_entry.outer_x_usage_ratio == RangeSpec(False, 0.1, 1.0, 90)
    assert rx_entry.outer_y_usage_ratio == RangeSpec(False, 0.1, 1.0, 160)
    assert rx_entry.outer_x_mm == RangeSpec(False, 180.0, 1800.0, 90)
    assert rx_entry.outer_y_mm == RangeSpec(False, 36.0, 360.0, 160)
    assert rx_entry.layer_count.start == pytest.approx(1.0)
    assert rx_entry.layer_count.end == pytest.approx(1.0)
    assert rx_entry.layer_count.count == 1
    assert rx_entry.underlay_repeat_count.start == pytest.approx(8.0)
    assert rx_entry.underlay_repeat_count.end == pytest.approx(8.0)
    assert rx_entry.underlay_repeat_count.count == 1
    assert rx_entry.terminal_path == "A_cw_to_a"


def test_load_type2_step_spec_rejects_unsupported_modeled_role(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(modeled_role="bad_single_coil"))

    with pytest.raises(ValueError, match=r"unsupported modeled object role: bad_single_coil"):
        load_type2_step_spec(toml_path)


@pytest.mark.parametrize(
    ("role", "toml_text"),
    (
        (
            "tx_single_coil",
            _type2_spec_text(modeled_object_id="tx_rect_void_coil", modeled_role="tx_single_coil"),
        ),
        ("tx_rect_void_columns", _type2_tx_rect_void_columns_spec_text()),
        ("tx_plate_stack", _type2_tx_plate_stack_spec_text()),
    ),
)
def test_load_type2_step_spec_rejects_generic_tx_modeled_roles_in_active_rxonly(
    tmp_path: Path,
    role: str,
    toml_text: str,
) -> None:
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(
        ValueError,
        match=rf"modeled_objects\[0\]\.role is unsupported in active RxOnly type2 mode \(actual='{role}'\)",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_parses_tx_rect_void_columns_parser_surface(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_tx_rect_void_columns_spec_text())

    spec = load_type2_step_spec(toml_path)

    assert len(spec.modeled_objects) == 1
    tx_columns_entry = spec.modeled_objects[0]
    assert tx_columns_entry.object_id == "tx_rect_void_columns"
    assert tx_columns_entry.role == "tx_rect_void_columns"
    assert tx_columns_entry.layer_count == RangeSpec(True, 1.0, 4.0, 4)
    assert tx_columns_entry.layer_gap_mm == RangeSpec(False, 1.0, 1.8, 5)
    assert tx_columns_entry.terminal_stub_length_mm == RangeSpec(False, 10.0, 10.0, 1)
    assert tx_columns_entry.connection_mode == RangeSpec(True, 0.0, 1.0, 2)
    assert tx_columns_entry.equivalent_turn_count == RangeSpec(False, 0.1111111111111111, 31.0, 100)
    assert tx_columns_entry.turn_weight_a == RangeSpec(False, 0.5, 1.5, 5)
    assert tx_columns_entry.turn_weight_b == RangeSpec(False, -0.5, 0.5, 21)
    assert tx_columns_entry.turn_weight_c == RangeSpec(False, -0.3, 0.3, 21)


@pytest.mark.parametrize(
    "legacy_key",
    (
        "turn_count_x0",
        "turn_count_x1",
        "turn_count_x2",
        "parallel_equivalent_turn_count",
        "column_connection_mode",
        "row_connection_mode",
        "series_total_turn_count",
        "parallel_total_turn_count",
    ),
)
def test_load_type2_step_spec_rejects_tx_rect_void_columns_legacy_public_keys(
    tmp_path: Path,
    legacy_key: str,
) -> None:
    legacy_section = f"[modeled_objects.{legacy_key}]\nrange = [true, 1, 6, 6]"
    toml_path = _write_spec(
        tmp_path,
        _type2_tx_rect_void_columns_spec_text().replace(
            "[modeled_objects.terminal_path]",
            f"{legacy_section}\n[modeled_objects.terminal_path]",
            1,
        ),
    )

    with pytest.raises(ValueError, match=rf"unsupported legacy keys.*{legacy_key}"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_tx_rect_void_columns_noncanonical_connection_mode_range(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_tx_rect_void_columns_spec_text(connection_mode_range="[true, 0, 2, 3]"),
    )

    with pytest.raises(ValueError, match=r"connection_mode must be \[true, 0, 1, 2\]"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_tx_rect_void_columns_noncanonical_layer_count_range(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_tx_rect_void_columns_spec_text(layer_count_range="[true, 1, 3, 3]"),
    )

    with pytest.raises(ValueError, match=r"layer_count must be \[true, 1, 4, 4\]"):
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
    assert not hasattr(tx_entry, "ferrite_set_count")
    assert tx_entry.turn_count.start == pytest.approx(3.0)
    assert tx_entry.metal_fill_factor.start == pytest.approx(0.4)
    assert tx_entry.z_usage_ratio.start == pytest.approx(0.3)
    assert tx_entry.tx_array_x_usage_ratio.start == pytest.approx(1.0)


def test_load_type2_step_spec_rejects_legacy_type2_schema_id(tmp_path: Path) -> None:
    toml_text = _type2_rx_plate_stack_spec_text().replace("peetsfea.type2.step.v8", "peetsfea.type2.step.v1", 1)
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(ValueError, match=r"schema_id must be 'peetsfea\.type2\.step\.v8'"):
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
                "[modeled_objects.outer_x_usage_ratio]",
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
                "[modeled_objects.outer_x_usage_ratio]",
                f"range = {_range(False, 2.0, 2.0, 1)}",
            ),
        ),
    )

    with pytest.raises(ValueError, match=r"contains unsupported keys for rx_plate_stack"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_tx_plate_stack_with_ferrite_set_count_key(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_tx_plate_stack_spec_text(
            extra_modeled_lines=(
                "[modeled_objects.ferrite_set_count]",
                "range = [true, 10, 10, 1]",
            ),
        ),
    )

    with pytest.raises(ValueError, match=r"contains unsupported keys for tx_plate_stack"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_rx_plate_stack_with_ferrite_set_count_key(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_rx_plate_stack_spec_text(
            extra_modeled_lines=(
                "[modeled_objects.ferrite_set_count]",
                "range = [true, 10, 10, 1]",
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


@pytest.mark.parametrize(
    "legacy_key",
    (
        "outer_x_mm",
        "outer_y_mm",
        "void_x_over_outer_x",
        "void_y_over_outer_y",
        "void_center_x_over_outer_x",
        "void_center_y_over_outer_y",
    ),
)
def test_load_type2_step_spec_rejects_single_coil_legacy_public_keys(
    tmp_path: Path,
    legacy_key: str,
) -> None:
    legacy_section = f"[modeled_objects.{legacy_key}]\nrange = [false, 0.3, 0.3, 1]"
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text().replace(
            "[modeled_objects.margin_ratio]",
            f"{legacy_section}\n[modeled_objects.margin_ratio]",
        ),
    )

    with pytest.raises(ValueError, match=rf"unsupported legacy keys.*{legacy_key}"):
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


@pytest.mark.parametrize("invalid_value", (0.0, 1.0))
def test_load_type2_step_spec_rejects_single_coil_non_open_interval_void_usage_ratio(
    tmp_path: Path,
    invalid_value: float,
) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text().replace(
            "[modeled_objects.void_usage_ratio]\nrange = [false, 0.2, 0.2, 1]",
            f"[modeled_objects.void_usage_ratio]\nrange = [false, {invalid_value}, {invalid_value}, 1]",
            1,
        ),
    )

    with pytest.raises(ValueError, match=r"void_usage_ratio must realize to values > 0 and < 1"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_plate_stack_missing_z_usage_ratio(tmp_path: Path) -> None:
    toml_text = _type2_rx_plate_stack_spec_text().replace(
        "    [modeled_objects.z_usage_ratio]\n"
        "    range = [false, 0.3, 0.3, 1]",
        "",
        1,
    )
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(ValueError, match=r"modeled_objects\[0\] is missing required key 'z_usage_ratio'"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_plate_stack_missing_y_usage_ratio(tmp_path: Path) -> None:
    toml_text = _type2_rx_plate_stack_spec_text().replace(
        "    [modeled_objects.y_usage_ratio]\n"
        "    range = [false, 1.0, 1.0, 1]",
        "",
        1,
    )
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(ValueError, match=r"modeled_objects\[0\] is missing required key 'y_usage_ratio'"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_plate_stack_integer_z_usage_ratio(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_rx_plate_stack_spec_text(z_usage_ratio_range=_range(True, 1.0, 1.0, 1)),
    )

    with pytest.raises(ValueError, match=r"z_usage_ratio\.range\[0\] must be false"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_plate_stack_integer_y_usage_ratio(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_rx_plate_stack_spec_text(y_usage_ratio_range=_range(True, 1.0, 1.0, 1)),
    )

    with pytest.raises(ValueError, match=r"y_usage_ratio\.range\[0\] must be false"):
        load_type2_step_spec(toml_path)


@pytest.mark.parametrize("z_usage_ratio_range", (_range(False, 0.0, 0.0, 1), _range(False, 1.1, 1.1, 1)))
def test_load_type2_step_spec_rejects_plate_stack_z_usage_ratio_outside_supported_range(
    tmp_path: Path,
    z_usage_ratio_range: str,
) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_rx_plate_stack_spec_text(z_usage_ratio_range=z_usage_ratio_range),
    )

    with pytest.raises(ValueError, match=r"z_usage_ratio must realize to values > 0 and <= 1"):
        load_type2_step_spec(toml_path)


@pytest.mark.parametrize("y_usage_ratio_range", (_range(False, 0.0, 0.0, 1), _range(False, 1.1, 1.1, 1)))
def test_load_type2_step_spec_rejects_plate_stack_y_usage_ratio_outside_supported_range(
    tmp_path: Path,
    y_usage_ratio_range: str,
) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_rx_plate_stack_spec_text(y_usage_ratio_range=y_usage_ratio_range),
    )

    with pytest.raises(ValueError, match=r"y_usage_ratio must realize to values > 0 and <= 1"):
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


def test_load_type2_step_spec_rejects_tx_inner_underlay_gap_mm(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="tx_inner_rect_void_coil",
            modeled_role="tx_inner_single_coil",
            underlay_repeat_count_range=_range(True, 0.0, 0.0, 1),
            underlay_gap_range=_range(False, 1.0, 1.0, 1),
        ),
    )

    with pytest.raises(ValueError, match=r"modeled_objects\[0\]\.underlay_gap_mm is unsupported for tx_inner_single_coil"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_tx_inner_wall_parallel_stack_present(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="tx_inner_rect_void_coil",
            modeled_role="tx_inner_single_coil",
            underlay_repeat_count_range=_range(True, 0.0, 0.0, 1),
            wall_parallel_stack_present_range=_range(True, 0.0, 0.0, 1),
        ),
    )

    with pytest.raises(
        ValueError,
        match=r"modeled_objects\[0\]\.wall_parallel_stack_present is unsupported for tx_inner_single_coil",
    ):
        load_type2_step_spec(toml_path)


@pytest.mark.parametrize(
    ("field_name", "field_range", "message"),
    (
        (
            "underlay_pet_psa_thickness_mm",
            None,
            r"modeled_objects\[0\] is missing required key 'underlay_pet_psa_thickness_mm'",
        ),
        (
            "underlay_ferrite_thickness_mm",
            None,
            r"modeled_objects\[0\] is missing required key 'underlay_ferrite_thickness_mm'",
        ),
        (
            "underlay_pet_psa_thickness_mm",
            _range(False, 0.0, 0.0, 1),
            r"modeled_objects\[0\]\.underlay_pet_psa_thickness_mm must be fixed \[false, t, t, 1\] with t > 0",
        ),
        (
            "underlay_ferrite_thickness_mm",
            _range(False, -1.0, -1.0, 1),
            r"modeled_objects\[0\]\.underlay_ferrite_thickness_mm must be fixed \[false, t, t, 1\] with t > 0",
        ),
        (
            "underlay_pet_psa_thickness_mm",
            _range(False, 2.0, 4.0, 2),
            r"modeled_objects\[0\]\.underlay_pet_psa_thickness_mm must be fixed \[false, t, t, 1\] with t > 0",
        ),
        (
            "underlay_ferrite_thickness_mm",
            _range(True, 3.0, 3.0, 1),
            r"modeled_objects\[0\]\.underlay_ferrite_thickness_mm\.range\[0\] must be false",
        ),
    ),
)
def test_load_type2_step_spec_rejects_invalid_tx_inner_underlay_thickness_ranges(
    tmp_path: Path,
    field_name: str,
    field_range: str | None,
    message: str,
) -> None:
    toml_text = _type2_spec_text(
        modeled_object_id="tx_inner_rect_void_coil",
        modeled_role="tx_inner_single_coil",
        underlay_repeat_count_range=_range(True, 4.0, 4.0, 1),
    )
    if field_range is None:
        section_start = toml_text.index(f"[modeled_objects.{field_name}]")
        next_section_start = toml_text.index("\n[", section_start + 1)
        toml_text = toml_text[:section_start] + toml_text[next_section_start + 1 :]
    else:
        toml_text = re.sub(
            rf"(\[modeled_objects\.{field_name}\]\nrange = )\[[^\n]+\]",
            rf"\g<1>{field_range}",
            toml_text,
            count=1,
        )
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(ValueError, match=message):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_accepts_tx_inner_fixed_underlay_stack_contract(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="tx_inner_rect_void_coil",
            modeled_role="tx_inner_single_coil",
            underlay_repeat_count_range=_range(True, 1.0, 1.0, 1),
            void_stack_present_range=_range(True, 1.0, 1.0, 1),
            underlay_pet_psa_thickness_range=_range(False, 6.0, 6.0, 1),
            underlay_ferrite_thickness_range=_range(False, 6.0, 6.0, 1),
        ),
    )

    spec = load_type2_step_spec(toml_path)
    tx_inner_entry = next(entry for entry in spec.modeled_objects if entry.object_id == "tx_inner_rect_void_coil")

    assert tx_inner_entry.role == "tx_inner_single_coil"
    assert tx_inner_entry.underlay_repeat_count == RangeSpec(True, 1.0, 1.0, 1)
    assert tx_inner_entry.void_stack_present == RangeSpec(True, 1.0, 1.0, 1)
    assert resolve_modeled_tx_inner_void_stack_present(tx_inner_entry, seed=0) is True
    assert tx_inner_entry.underlay_pet_psa_thickness_mm == RangeSpec(False, 6.0, 6.0, 1)
    assert tx_inner_entry.underlay_ferrite_thickness_mm == RangeSpec(False, 6.0, 6.0, 1)


def test_load_type2_step_spec_accepts_tx_inner_canonical_void_stack_present(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="tx_inner_rect_void_coil",
            modeled_role="tx_inner_single_coil",
            underlay_repeat_count_range=_range(True, 1.0, 1.0, 1),
            void_stack_present_range=_range(True, 0.0, 1.0, 2),
        ),
    )

    spec = load_type2_step_spec(toml_path)
    tx_inner_entry = next(entry for entry in spec.modeled_objects if entry.object_id == "tx_inner_rect_void_coil")

    assert tx_inner_entry.role == "tx_inner_single_coil"
    assert tx_inner_entry.void_stack_present == RangeSpec(True, 0.0, 1.0, 2)
    assert resolve_modeled_tx_inner_void_stack_present(tx_inner_entry, seed=0) in (False, True)


@pytest.mark.parametrize(
    ("modeled_role", "modeled_object_id"),
    (
        ("tx_single_coil", "tx_rect_void_coil"),
        ("rx_single_coil", "rx_rect_void_coil"),
    ),
)
def test_load_type2_step_spec_rejects_void_stack_present_for_non_tx_inner_single_coil(
    tmp_path: Path,
    modeled_role: Literal["tx_single_coil", "rx_single_coil"],
    modeled_object_id: str,
) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id=modeled_object_id,
            modeled_role=modeled_role,
            void_stack_present_range=_range(True, 1.0, 1.0, 1),
        ),
    )

    with pytest.raises(
        ValueError,
        match=rf"modeled_objects\[0\] contains unsupported keys for {modeled_role} .*void_stack_present",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_missing_tx_inner_void_stack_present(tmp_path: Path) -> None:
    toml_text = _type2_spec_text(
        modeled_object_id="tx_inner_rect_void_coil",
        modeled_role="tx_inner_single_coil",
        underlay_repeat_count_range=_range(True, 1.0, 1.0, 1),
    )
    section_start = toml_text.index("[modeled_objects.void_stack_present]")
    next_section_start = toml_text.index("\n[", section_start + 1)
    toml_text = toml_text[:section_start] + toml_text[next_section_start + 1 :]
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(ValueError, match=r"modeled_objects\[0\] is missing required key 'void_stack_present'"):
        load_type2_step_spec(toml_path)


@pytest.mark.parametrize(
    "void_stack_present_range",
    (
        _range(True, 0.0, 2.0, 3),
        _range(True, 2.0, 2.0, 1),
        _range(False, 0.0, 1.0, 2),
    ),
)
def test_load_type2_step_spec_rejects_invalid_tx_inner_void_stack_present(
    tmp_path: Path,
    void_stack_present_range: str,
) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="tx_inner_rect_void_coil",
            modeled_role="tx_inner_single_coil",
            underlay_repeat_count_range=_range(True, 1.0, 1.0, 1),
            void_stack_present_range=void_stack_present_range,
        ),
    )

    with pytest.raises(ValueError, match=r"modeled_objects\[0\]\.void_stack_present"):
        load_type2_step_spec(toml_path)


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
            'mode = "RxOnly"',
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
    toml_text = _type2_spec_text().replace('name = "Qrx_ratio"', 'name = "Lrx_uH"', 1)
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(
        ValueError,
        match=r"type2_fixed\.toml\.outputs\.variables\[1\]\.name must be unique: Lrx_uH",
    ):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_invalid_output_variable_name(tmp_path: Path) -> None:
    toml_text = _type2_spec_text().replace('name = "Lrx_uH"', 'name = "1bad"', 1)
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


@pytest.mark.parametrize(
    ("role", "prefix"),
    (("tx_plate_stack", "tx"), ("rx_plate_stack", "rx")),
)
def test_plate_stack_pre_unite_topology_contract_uses_equal_wall_coil_stripes(
    role: Literal["tx_plate_stack", "rx_plate_stack"],
    prefix: Literal["tx", "rx"],
) -> None:
    turn_count = 4
    pre_unite_names = cast(
        tuple[str, ...],
        type2_plate_stack_module._expected_plate_stack_pre_unite_body_names(
            role=role,
            turn_count=turn_count,
            pcb_total_thickness_mm=_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
        ),
    )
    wall_names = [name for name in pre_unite_names if name.startswith(f"{prefix}_copper_wall_t")]
    coil_names = [name for name in pre_unite_names if name.startswith(f"{prefix}_copper_coil_t")]
    bridge_names = [name for name in pre_unite_names if name.startswith(f"{prefix}_bridge_s")]

    assert wall_names == [f"{prefix}_copper_wall_t{index}" for index in range(turn_count)]
    assert coil_names == [f"{prefix}_copper_coil_t{index}" for index in range(turn_count)]
    assert bridge_names == [f"{prefix}_bridge_s{index}" for index in range((2 * turn_count) - 1)]
    assert pre_unite_names[-2:] == (f"{prefix}_stub_in", f"{prefix}_stub_out")
    path_nodes = [
        *[f"{prefix}_copper_wall_t{index}" for index in range(turn_count)],
        *[f"{prefix}_copper_coil_t{index}" for index in range(turn_count)],
    ]
    assert len(bridge_names) == (2 * turn_count) - 1
    assert len(bridge_names) == len(path_nodes) - 1


def test_render_tx_rect_void_toml_omits_type2_underlay_fields_from_core_bridge(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="tx_inner_rect_void_coil",
            modeled_role="tx_inner_single_coil",
            underlay_repeat_count_range=_range(True, 0.0, 0.0, 1),
        ),
    )
    spec = load_type2_step_spec(toml_path)
    modeled_spec = next(entry for entry in spec.modeled_objects if entry.object_id == "tx_inner_rect_void_coil")
    assert modeled_spec.role == "tx_inner_single_coil"

    rendered = render_tx_rect_void_toml(cast(ModeledSingleCoilSpec, modeled_spec))

    assert "underlay_repeat_count" not in rendered
    assert "underlay_gap_mm" not in rendered
    assert "wall_parallel_stack_present" not in rendered
    assert "[tx_coil.void_usage_ratio]" in rendered
    assert "void_x_over_outer_x" not in rendered
    assert "void_y_over_outer_y" not in rendered
    assert "void_center_x_over_outer_x" not in rendered
    assert "void_center_y_over_outer_y" not in rendered


def test_realize_tx_rect_void_spec_uses_single_void_usage_ratio_for_x_and_y(tmp_path: Path) -> None:
    tx_rect_void_toml_path = tmp_path / "tx_rect_void.toml"
    tx_rect_void_toml_path.write_text(
        _tx_rect_void_spec_text_with_layer_count(
            layer_count=1,
            void_usage_ratio_range=_range(False, 0.2, 0.8, 10),
        ),
        encoding="utf-8",
    )
    spec = load_tx_rect_void_spec(tx_rect_void_toml_path)
    realized = realize_tx_rect_void_spec(spec, seed=7)

    assert 0.0 < realized.void_x_over_outer_x < 1.0
    assert realized.void_x_over_outer_x == pytest.approx(realized.void_y_over_outer_y)
    assert realized.void_center_x_over_outer_x == pytest.approx(0.0)
    assert realized.void_center_y_over_outer_y == pytest.approx(0.0)


def test_export_type2_step_artifacts_rejects_tx_rect_void_columns_modeled_role(tmp_path: Path) -> None:
    source_toml = _write_spec(
        tmp_path,
        _type2_tx_rect_void_columns_spec_text(equivalent_turn_count_range="[false, 1.0, 1.0, 1]"),
    )
    output_dir = tmp_path / "out"
    output_ledger_path = output_dir / "type2_ledger.json"

    with pytest.raises(ValueError, match=r"role is unsupported in active RxOnly type2 mode.*tx_rect_void_columns"):
        export_type2_step_artifacts(
            toml_path=source_toml,
            output_dir=output_dir,
            ledger_path=output_ledger_path,
            seed=0,
        )
    assert not output_ledger_path.exists()


def test_export_type2_step_artifacts_rejects_tx_rect_void_columns_when_legacy_preflight_bypassed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import peetsfea.type2_step_export as module_under_test
    source_toml = _write_spec(
        tmp_path,
        _type2_spec_text(modeled_object_id="rx_rect_void_coil", modeled_role="rx_single_coil"),
    )

    def _no_raise_preflight(*, spec: object, context: str) -> None:
        del spec, context

    def _load_fake_spec(_toml_path: Path) -> Type2StepSpec:
        return _spec_with_deactivated_tx_rect_void_columns_for_export_dispatch(source_toml)

    monkeypatch.setattr(module_under_test, "_raise_if_tx_rect_void_columns_modeled_role_present", _no_raise_preflight)
    monkeypatch.setattr(module_under_test, "load_type2_step_spec", _load_fake_spec)

    output_dir = tmp_path / "out"
    output_ledger_path = output_dir / "type2_ledger.json"
    with pytest.raises(ValueError, match=r"does not support modeled TX geometry.*tx_rect_void_columns"):
        module_under_test.export_type2_step_artifacts(
            toml_path=source_toml,
            output_dir=output_dir,
            ledger_path=output_ledger_path,
            seed=0,
        )
    assert not output_ledger_path.exists()


def test_export_type2_tx_single_coil_artifact_rejects_tx_rect_void_columns_modeled_role(tmp_path: Path) -> None:
    source_toml = _write_spec(tmp_path, _type2_tx_rect_void_columns_spec_text())
    with pytest.raises(
        ValueError,
        match=r"role is unsupported in active RxOnly type2 mode.*tx_rect_void_columns",
    ):
        export_type2_tx_single_coil_artifact(
            toml_path=source_toml,
            output_step_path=tmp_path / "out" / "tx_single_coil.step",
            metadata_path=tmp_path / "out" / "tx_single_coil.metadata.json",
            seed=0,
        )


def test_export_type2_tx_single_coil_artifact_rejects_tx_rect_void_columns_when_preflight_bypassed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import peetsfea.type2_step_export as module_under_test
    source_toml = _write_spec(
        tmp_path,
        _type2_spec_text(modeled_object_id="rx_rect_void_coil", modeled_role="rx_single_coil"),
    )

    def _no_raise_preflight(*, spec: object, context: str) -> None:
        del spec, context

    def _load_fake_spec(_toml_path: Path) -> Type2StepSpec:
        return _spec_with_deactivated_tx_rect_void_columns_for_export_dispatch(source_toml)

    monkeypatch.setattr(module_under_test, "_raise_if_tx_rect_void_columns_modeled_role_present", _no_raise_preflight)
    monkeypatch.setattr(module_under_test, "load_type2_step_spec", _load_fake_spec)

    with pytest.raises(
        ValueError,
        match=r"does not support modeled TX geometry.*tx_rect_void_columns",
    ):
        module_under_test.export_type2_tx_single_coil_artifact(
            toml_path=source_toml,
            output_step_path=tmp_path / "out" / "tx_single_coil.step",
            metadata_path=tmp_path / "out" / "tx_single_coil.metadata.json",
            seed=0,
        )


def test_export_type2_step_artifacts_keeps_tx_region_as_guide_only_for_rxonly(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    toml_path = repo_root / "examples" / "type2_fixed.toml"
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    non_model_entry = ledger["non_model_objects"][0]
    member_object_ids = tuple(cast(Sequence[str], non_model_entry["member_object_ids"]))
    required_guide_member_ids = (
        "environment",
        "tx_region",
        "tx_inner_region",
        "tx_inner_actual_region",
        "rx_region_max",
    )
    assert set(member_object_ids) >= set(required_guide_member_ids)
    assert member_object_ids[: len(required_guide_member_ids)] == required_guide_member_ids
    member_objects = cast(Sequence[dict[str, object]], non_model_entry["member_objects"])
    tx_region_member = next(member for member in member_objects if cast(str, member["object_id"]) == "tx_region")
    assert tx_region_member["model_state"] is False
    assert tx_region_member["non_model"] is True
    tx_region_min_xyz, tx_region_size_xyz = _canonical_min_size(tx_region_member)
    assert tx_region_min_xyz == pytest.approx((0.0, -600.0, 0.0))
    assert tx_region_size_xyz == pytest.approx((720.0, 1200.0, 90.0))
    tx_inner_member = next(member for member in member_objects if cast(str, member["object_id"]) == "tx_inner_region")
    tx_inner_actual_member = next(
        member for member in member_objects if cast(str, member["object_id"]) == "tx_inner_actual_region"
    )
    tx_inner_min_xyz, tx_inner_size_xyz = _canonical_min_size(tx_inner_member)
    tx_inner_actual_min_xyz, tx_inner_actual_max_xyz, tx_inner_actual_size_xyz = _canonical_bounds(
        tx_inner_actual_member
    )
    reference_line = cast(dict[str, object], tx_inner_member["tx_reference_line"])
    assert reference_line["x_ratio"] == pytest.approx(0.99)
    assert reference_line["y_usage_ratio"] == pytest.approx(1.0)
    assert tx_inner_min_xyz == pytest.approx((0.0, -600.0, 0.0))
    assert tx_inner_size_xyz == pytest.approx((712.8, 1200.0, 81.0))
    assert tx_inner_actual_min_xyz[0] == pytest.approx(0.0)
    assert tx_inner_actual_min_xyz[1] == pytest.approx(-54.63440272451783)
    assert tx_inner_actual_max_xyz[1] == pytest.approx(54.634402724517855)
    assert tx_inner_actual_size_xyz[0] == pytest.approx(137.13763380207968)
    assert tx_inner_actual_size_xyz[1] == pytest.approx(109.26880544903568)
    tx_region_actual_members = [member for member in member_objects if cast(str, member["role"]) == "tx_region_actual"]
    assert tx_region_actual_members == []
    tx_region_actual_stack_space_members = [
        member for member in member_objects if cast(str, member["role"]) == "tx_region_actual_stack_space"
    ]
    assert tx_region_actual_stack_space_members == []
    assert all(member["object_id"] != "tx_outer_actual_region" for member in member_objects)
    assert tuple(entry["object_id"] for entry in ledger["modeled_objects"]) == (
        "tx_inner_rect_void_coil",
        "rx_rect_void_coil",
    )
    assert ledger["outputs"]["mode"] == "TxRx"
    assert "TX_TML" in json.dumps(ledger["outputs"], sort_keys=True)
    tx_inner_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_inner_rect_void_coil")
    assert tx_inner_entry["role"] == "tx_inner_single_coil"
    assert tx_inner_entry["expected_exported_body_names"] == _tx_inner_expected_body_names(
        layer_count=2,
        underlay_repeat_count=1,
    )
    assert tx_inner_entry["expected_exported_body_count"] == 5
    assert all(entry["object_id"] != "tx_outer_rect_void_coil" for entry in ledger["modeled_objects"])
    rx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "rx_rect_void_coil")
    assert cast(dict[str, object], rx_entry["terminal_metadata"])["port_sheet_vertices_xyz"]

    scene_shapes_by_label = _step_shapes_by_label(Path(ledger["scene_step_path"]))
    assert "tx_region" in scene_shapes_by_label
    assert "tx_inner_region" in scene_shapes_by_label
    assert "tx_inner_actual_region" in scene_shapes_by_label
    assert "tx_outer_region" not in scene_shapes_by_label
    assert "tx_outer_actual_region" not in scene_shapes_by_label
    assert "tx_region_actual" not in scene_shapes_by_label
    assert "tx_region_actual_stack_space" not in scene_shapes_by_label
    assert all(
        not name.startswith(("tx_outer_pcb_", "tx_outer_copper_", "tx_outer_void_", "tx_outer_underlay_"))
        for name in scene_shapes_by_label
    )


def test_export_type2_step_artifacts_supports_tx_inner_single_coil_layer_count_five_body_contract(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="tx_inner_rect_void_coil",
            modeled_role="tx_inner_single_coil",
            underlay_repeat_count_range=_range(True, 0.0, 0.0, 1),
            void_stack_present_range=_range(True, 0.0, 0.0, 1),
            layer_count=5,
        ),
    )
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    tx_inner_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_inner_rect_void_coil")
    assert tx_inner_entry["role"] == "tx_inner_single_coil"
    expected_names = _tx_inner_expected_body_names(layer_count=5)
    assert tx_inner_entry["expected_exported_body_names"] == expected_names
    assert tx_inner_entry["expected_exported_body_count"] == len(expected_names)
    assert tx_inner_entry["expected_exported_body_count"] == 6
    assert ledger["outputs"]["mode"] == "RxOnly"
    assert "TX_TML" not in json.dumps(ledger["outputs"], sort_keys=True)

    scene_shapes_by_label = _step_shapes_by_label(Path(ledger["scene_step_path"]))
    for body_name in expected_names:
        assert body_name in scene_shapes_by_label
    assert "tx_inner_copper_l0" not in scene_shapes_by_label


def test_export_type2_step_artifacts_keeps_tx_inner_underlay_when_void_stack_disabled(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="tx_inner_rect_void_coil",
            modeled_role="tx_inner_single_coil",
            underlay_repeat_count_range=_range(True, 1.0, 1.0, 1),
            void_stack_present_range=_range(True, 0.0, 0.0, 1),
            layer_count=2,
        ),
    )
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    tx_inner_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_inner_rect_void_coil")
    expected_names = _tx_inner_expected_body_names(layer_count=2, underlay_repeat_count=1)
    assert tx_inner_entry["expected_exported_body_names"] == expected_names
    assert tx_inner_entry["expected_exported_body_count"] == len(expected_names)
    expected_underlay_names = ("tx_underlay_pet_psa_u0", "tx_underlay_ferrite_u0")
    assert all(name in expected_names for name in expected_underlay_names)
    assert all(not name.startswith("tx_void_") for name in expected_names)
    assert _normalized_body_groups(tx_inner_entry["expected_exported_body_groups"]) == _normalized_body_groups(
        (
            {
                "group_name": _TX_FERRITE_GROUP_NAME,
                "member_body_names": expected_underlay_names,
            },
        )
    )

    scene_shapes_by_label = _step_shapes_by_label(Path(ledger["scene_step_path"]))
    assert all(name in scene_shapes_by_label for name in expected_underlay_names)
    assert all(not name.startswith("tx_void_") for name in scene_shapes_by_label)


def test_export_type2_fixed_example_adds_tx_inner_region_guide_only_step_and_ledger(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_fixed.toml"

    ledger = export_type2_step_artifacts(
        toml_path=source_toml,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    non_model_entry = ledger["non_model_objects"][0]
    member_object_ids = tuple(cast(Sequence[str], non_model_entry["member_object_ids"]))
    assert set(member_object_ids) >= {
        "environment",
        "tx_region",
        "tx_inner_region",
        "tx_inner_actual_region",
        "rx_region_max",
    }
    forbidden_member_ids = {
        "tx_outer_region",
        "tx_outer_actual_region",
        _TX_POSITIVE_BRIDGE_PCB_OBJECT_ID,
        _TX_POSITIVE_BRIDGE_COPPER_OBJECT_ID,
        _TX_NEGATIVE_BRIDGE_PCB_OBJECT_ID,
        _TX_NEGATIVE_BRIDGE_COPPER_OBJECT_ID,
    }
    assert forbidden_member_ids.isdisjoint(member_object_ids)
    assert member_object_ids.index("tx_region") < member_object_ids.index("tx_inner_region")
    assert member_object_ids.index("tx_inner_region") < member_object_ids.index("tx_inner_actual_region")
    assert member_object_ids.index("tx_inner_actual_region") < member_object_ids.index("rx_region_max")
    member_objects = cast(Sequence[dict[str, object]], non_model_entry["member_objects"])
    tx_region_member = next(member for member in member_objects if member["object_id"] == "tx_region")
    tx_inner_member = next(member for member in member_objects if member["object_id"] == "tx_inner_region")
    tx_inner_actual_member = next(member for member in member_objects if member["object_id"] == "tx_inner_actual_region")
    tx_region_min_xyz, tx_region_size_xyz = _canonical_min_size(tx_region_member)
    assert tx_region_min_xyz == pytest.approx((0.0, -600.0, 0.0))
    assert tx_region_size_xyz == pytest.approx((720.0, 1200.0, 90.0))
    assert tx_inner_member["role"] == "tx_inner_region"
    assert tx_inner_member["model_state"] is False
    assert tx_inner_member["non_model"] is True
    assert tx_inner_member["material"] == "vacuum"
    assert tx_inner_actual_member["role"] == "tx_inner_actual_region"
    assert tx_inner_actual_member["model_state"] is False
    assert tx_inner_actual_member["non_model"] is True
    assert tx_inner_actual_member["material"] == "vacuum"

    canonical_coordinates = cast(dict[str, object], tx_inner_member["canonical_coordinates"])
    assert canonical_coordinates["outer_bounds_min_xyz"] == pytest.approx((0.0, -600.0, 0.0))
    assert canonical_coordinates["outer_bounds_size_xyz"] == pytest.approx((712.8, 1200.0, 81.0))
    tx_inner_region_min_xyz, tx_inner_region_size_xyz = _canonical_min_size(tx_inner_member)
    reference_line = cast(dict[str, object], tx_inner_member["tx_reference_line"])
    assert reference_line["source_region_id"] == "tx_region"
    assert reference_line["x_ratio"] == pytest.approx(0.99)
    assert reference_line["y_usage_ratio"] == pytest.approx(1.0)
    assert reference_line["z_ratio"] == pytest.approx(0.9)
    assert reference_line["line_start_xyz"] == pytest.approx((712.8, -600.0, 81.0))
    assert reference_line["line_end_xyz"] == pytest.approx((712.8, 600.0, 81.0))
    tx_inner_actual_region = cast(dict[str, object], tx_inner_actual_member["tx_actual_region"])
    assert tx_inner_actual_region["source_guide_id"] == "tx_inner_region"
    assert tx_inner_actual_region["modeled_source_id"] == "tx_inner_rect_void_coil"
    assert tx_inner_actual_region["x_usage_ratio"] == pytest.approx(0.22139465559575477)
    assert tx_inner_actual_region["y_usage_ratio"] == pytest.approx(0.10828440179634166)
    tx_inner_actual_region_bounds = cast(dict[str, object], tx_inner_actual_region["actual_region_bounds"])
    tx_inner_actual_region_min_xyz = cast(tuple[float, float, float], tx_inner_actual_region_bounds["min_xyz"])
    tx_inner_actual_region_max_xyz = cast(tuple[float, float, float], tx_inner_actual_region_bounds["max_xyz"])
    tx_inner_actual_region_size_xyz = cast(tuple[float, float, float], tx_inner_actual_region_bounds["size_xyz"])
    tx_inner_actual_physical_bounds = cast(dict[str, object], tx_inner_actual_region["physical_modeled_body_bounds"])
    tx_inner_actual_physical_min_xyz = cast(
        tuple[float, float, float], tx_inner_actual_physical_bounds["min_xyz"]
    )
    tx_inner_actual_physical_max_xyz = cast(
        tuple[float, float, float], tx_inner_actual_physical_bounds["max_xyz"]
    )
    tx_inner_actual_physical_size_xyz = cast(
        tuple[float, float, float], tx_inner_actual_physical_bounds["size_xyz"]
    )

    assert tuple(entry["object_id"] for entry in ledger["modeled_objects"]) == (
        "tx_inner_rect_void_coil",
        "rx_rect_void_coil",
    )
    tx_inner_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_inner_rect_void_coil")
    assert tx_inner_entry["role"] == "tx_inner_single_coil"
    assert tx_inner_entry["placement_owner_id"] == "tx_inner_region"
    tx_inner_actual_bounds = _canonical_bounds(tx_inner_actual_member)
    tx_inner_model_bounds = _canonical_bounds(cast(dict[str, object], tx_inner_entry))
    tx_inner_actual_min_xyz, tx_inner_actual_max_xyz, tx_inner_actual_size_xyz = tx_inner_actual_bounds
    model_min_xyz, model_max_xyz, model_size_xyz = tx_inner_model_bounds
    assert tx_inner_actual_min_xyz == pytest.approx(tx_inner_actual_region_min_xyz)
    assert tx_inner_actual_max_xyz == pytest.approx(tx_inner_actual_region_max_xyz)
    assert tx_inner_actual_size_xyz == pytest.approx(tx_inner_actual_region_size_xyz)
    assert tx_inner_actual_physical_min_xyz == pytest.approx(model_min_xyz)
    assert tx_inner_actual_physical_max_xyz == pytest.approx(model_max_xyz)
    assert tx_inner_actual_physical_size_xyz == pytest.approx(model_size_xyz)
    assert tx_inner_actual_physical_min_xyz == pytest.approx(tx_inner_actual_region_min_xyz)
    assert tx_inner_actual_physical_max_xyz == pytest.approx(tx_inner_actual_region_max_xyz)
    assert tx_inner_actual_physical_size_xyz == pytest.approx(tx_inner_actual_region_size_xyz)
    assert tx_inner_actual_min_xyz[0] == pytest.approx(0.0)
    assert tx_inner_actual_min_xyz[1] == pytest.approx(-54.63440272451783)
    assert tx_inner_actual_max_xyz[1] == pytest.approx(54.634402724517855)
    assert tx_inner_actual_size_xyz[0] == pytest.approx(137.13763380207968)
    assert tx_inner_actual_size_xyz[1] == pytest.approx(109.26880544903568)
    assert tx_inner_actual_min_xyz[0] <= model_min_xyz[0]
    assert model_max_xyz[0] <= tx_inner_actual_max_xyz[0]
    assert tx_inner_actual_min_xyz[1] <= model_min_xyz[1]
    assert model_max_xyz[1] <= tx_inner_actual_max_xyz[1]
    assert tx_inner_actual_min_xyz[0] == pytest.approx(model_min_xyz[0])
    assert tx_inner_actual_size_xyz[0] == pytest.approx(model_size_xyz[0])
    assert tx_inner_actual_size_xyz[1] == pytest.approx(model_size_xyz[1])
    _assert_owner_local_design_x_position_ratio(
        design_entry=tx_inner_actual_member,
        owner_entry=tx_inner_member,
        x_position_ratio=0.0,
    )
    assert tx_inner_actual_min_xyz[1] == pytest.approx(
        tx_inner_region_min_xyz[1] + (tx_inner_region_size_xyz[1] - tx_inner_actual_size_xyz[1]) / 2.0
    )
    assert tx_inner_entry["expected_exported_body_names"] == _tx_inner_expected_body_names(
        layer_count=2,
        underlay_repeat_count=1,
    )
    assert tx_inner_entry["expected_exported_body_count"] == 5
    tx_inner_terminal_metadata = cast(dict[str, object], tx_inner_entry["terminal_metadata"])
    tx_inner_model_canonical = cast(dict[str, object], tx_inner_entry["canonical_coordinates"])
    tx_inner_terminal_pcb_layer_z_positions = cast(
        tuple[float, ...], tx_inner_model_canonical["pcb_layer_z_positions_mm"]
    )
    tx_inner_outer_bounds_min_xyz = cast(
        tuple[float, float, float], tx_inner_model_canonical["outer_bounds_min_xyz"]
    )
    assert tx_inner_terminal_metadata["path"] == "B_cw_to_b"
    assert tx_inner_terminal_metadata["port_sheet_vertices_xyz"]
    assert tx_inner_outer_bounds_min_xyz[2] == pytest.approx(
        tx_inner_terminal_pcb_layer_z_positions[0] - 7.5
    )
    tx_inner_terminal_stub_boxes = _world_terminal_stub_boxes(
        source_toml=source_toml,
        object_id="tx_inner_rect_void_coil",
        seed=0,
    )
    assert tx_inner_terminal_stub_boxes
    tx_inner_layer0_stub_z = tx_inner_terminal_pcb_layer_z_positions[0] - 7.5
    tx_inner_terminal_stub_layer0_boxes = tuple(
        box
        for box in tx_inner_terminal_stub_boxes
        if abs(box[0][2] - tx_inner_layer0_stub_z) <= 1e-9
    )
    assert len(tx_inner_terminal_stub_layer0_boxes) == 2
    assert {
        tuple(round(component, 8) for component in vertex)
        for vertex in cast(
            list[list[float]],
            tx_inner_terminal_metadata["port_sheet_vertices_xyz"],
        )
    } == {
        tuple(round(component, 8) for component in vertex)
        for vertex in _widest_stub_bottom_face_diagonal_vertices(
            terminal_stub_boxes=tx_inner_terminal_stub_layer0_boxes,
            plane="XY",
        )
    }
    rx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "rx_rect_void_coil")
    assert cast(dict[str, object], rx_entry["terminal_metadata"])["port_sheet_vertices_xyz"]
    assert ledger["outputs"]["mode"] == "TxRx"
    assert "TX_TML" in json.dumps(ledger["outputs"], sort_keys=True)

    scene_shapes_by_label = _step_shapes_by_label(Path(ledger["scene_step_path"]))
    assert "tx_region" in scene_shapes_by_label
    assert "tx_inner_region" in scene_shapes_by_label
    assert "tx_inner_actual_region" in scene_shapes_by_label
    assert "tx_outer_region" not in scene_shapes_by_label
    assert "tx_outer_actual_region" not in scene_shapes_by_label
    assert "tx_region_actual" not in scene_shapes_by_label
    assert "tx_region_actual_stack_space" not in scene_shapes_by_label
    expected_tx_inner_underlay_names = tuple(
        name
        for name in _tx_inner_expected_body_names(layer_count=2, underlay_repeat_count=1)
        if name.startswith("tx_underlay_")
    )
    assert expected_tx_inner_underlay_names == (
        "tx_underlay_pet_psa_u0",
        "tx_underlay_ferrite_u0",
    )
    assert all(name in scene_shapes_by_label for name in expected_tx_inner_underlay_names)
    expected_tx_inner_void_names: tuple[str, ...] = ()
    assert all(not name.startswith("tx_void_") for name in scene_shapes_by_label)
    assert _normalized_body_groups(tx_inner_entry["expected_exported_body_groups"]) == _normalized_body_groups(
        (
            {
                "group_name": _TX_FERRITE_GROUP_NAME,
                "member_body_names": expected_tx_inner_underlay_names,
            },
        )
    )
    _assert_ferrite_family_pcb_clearance_contract(
        scene_shapes_by_label=scene_shapes_by_label,
        ferrite_group_name=_TX_FERRITE_GROUP_NAME,
        ferrite_member_names=expected_tx_inner_underlay_names,
        pcb_body_names=("tx_inner_pcb_l0", "tx_inner_pcb_l1"),
    )
    assert all(
        not name.startswith(("tx_outer_pcb_", "tx_outer_copper_", "tx_outer_void_", "tx_outer_underlay_"))
        for name in scene_shapes_by_label
    )

    previous_top_z = tx_inner_actual_min_xyz[2]
    for repeat_index in range(1):
        pet_name = f"tx_underlay_pet_psa_u{repeat_index}"
        ferrite_name = f"tx_underlay_ferrite_u{repeat_index}"
        pet_bbox = scene_shapes_by_label[pet_name].bounding_box()
        ferrite_bbox = scene_shapes_by_label[ferrite_name].bounding_box()
        for bbox in (pet_bbox, ferrite_bbox):
            assert bbox.min.X == pytest.approx(tx_inner_actual_min_xyz[0])
            assert bbox.max.X == pytest.approx(tx_inner_actual_max_xyz[0])
            assert bbox.min.Y == pytest.approx(tx_inner_actual_min_xyz[1])
            assert bbox.max.Y == pytest.approx(tx_inner_actual_max_xyz[1])
        assert pet_bbox.max.Z == pytest.approx(previous_top_z)
        assert pet_bbox.min.Z == pytest.approx(previous_top_z - 6.0)
        assert ferrite_bbox.max.Z == pytest.approx(pet_bbox.min.Z)
        assert ferrite_bbox.min.Z == pytest.approx(pet_bbox.min.Z - 6.0)
        previous_top_z = ferrite_bbox.min.Z
    assert tx_inner_actual_min_xyz[2] - previous_top_z == pytest.approx(12.0)


def test_export_type2_fixed_example_exports_tx_positive_bridge_non_model_geometry(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_fixed.toml"

    ledger = export_type2_step_artifacts(
        toml_path=source_toml,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    non_model_entry = ledger["non_model_objects"][0]
    member_objects = cast(Sequence[dict[str, object]], non_model_entry["member_objects"])
    member_object_ids = cast(Sequence[str], non_model_entry["member_object_ids"])

    pcb_bridge_member = _find_member_object(
        member_objects=member_objects,
        object_id=_TX_POSITIVE_BRIDGE_PCB_OBJECT_ID,
    )
    copper_bridge_member = _find_member_object(
        member_objects=member_objects,
        object_id=_TX_POSITIVE_BRIDGE_COPPER_OBJECT_ID,
    )
    neg_pcb_bridge_member = _find_member_object(
        member_objects=member_objects,
        object_id=_TX_NEGATIVE_BRIDGE_PCB_OBJECT_ID,
    )
    neg_copper_bridge_member = _find_member_object(
        member_objects=member_objects,
        object_id=_TX_NEGATIVE_BRIDGE_COPPER_OBJECT_ID,
    )

    assert _TX_POSITIVE_BRIDGE_PCB_OBJECT_ID in member_object_ids
    assert _TX_POSITIVE_BRIDGE_COPPER_OBJECT_ID in member_object_ids
    assert _TX_NEGATIVE_BRIDGE_PCB_OBJECT_ID in member_object_ids
    assert _TX_NEGATIVE_BRIDGE_COPPER_OBJECT_ID in member_object_ids
    _assert_bridge_member_contract(
        member=pcb_bridge_member,
        expected_role=_TX_POSITIVE_BRIDGE_ROLE,
        expected_material_thickness_mm=0.365,
        expected_total_stack_thickness_mm=_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    )
    _assert_bridge_member_contract(
        member=copper_bridge_member,
        expected_role=_TX_POSITIVE_BRIDGE_ROLE,
        expected_material_thickness_mm=0.035,
        expected_total_stack_thickness_mm=_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    )
    _assert_bridge_member_contract(
        member=neg_pcb_bridge_member,
        expected_role=_TX_NEGATIVE_BRIDGE_ROLE,
        expected_material_thickness_mm=0.365,
        expected_total_stack_thickness_mm=_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    )
    _assert_bridge_member_contract(
        member=neg_copper_bridge_member,
        expected_role=_TX_NEGATIVE_BRIDGE_ROLE,
        expected_material_thickness_mm=0.035,
        expected_total_stack_thickness_mm=_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    )

    scene_shapes_by_label = _step_shapes_by_label(Path(ledger["scene_step_path"]))
    for bridge_label in (
        _TX_POSITIVE_BRIDGE_PCB_OBJECT_ID,
        _TX_POSITIVE_BRIDGE_COPPER_OBJECT_ID,
        _TX_NEGATIVE_BRIDGE_PCB_OBJECT_ID,
        _TX_NEGATIVE_BRIDGE_COPPER_OBJECT_ID,
    ):
        assert bridge_label in scene_shapes_by_label

    modeled_body_names = tuple(
        body_name
        for member in cast(list[object], ledger["modeled_objects"])
        for body_name in cast(tuple[str, ...], cast(dict[str, object], member)["expected_exported_body_names"])
    )
    assert _TX_POSITIVE_BRIDGE_PCB_OBJECT_ID not in modeled_body_names
    assert _TX_POSITIVE_BRIDGE_COPPER_OBJECT_ID not in modeled_body_names
    assert _TX_NEGATIVE_BRIDGE_PCB_OBJECT_ID not in modeled_body_names
    assert _TX_NEGATIVE_BRIDGE_COPPER_OBJECT_ID not in modeled_body_names


def test_export_type2_step_artifacts_tx_positive_bridge_follows_final_tx_outer_terminal_sheet(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_text = (repo_root / "examples" / "type2_fixed.toml").read_text(encoding="utf-8")
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    baseline_toml = _write_spec(baseline_dir, source_text)
    baseline_ledger = export_type2_step_artifacts(
        toml_path=baseline_toml,
        output_dir=tmp_path / "out_baseline",
        ledger_path=tmp_path / "out_baseline" / "ledger.json",
        seed=0,
    )
    baseline_tx_outer_entry = next(
        member for member in baseline_ledger["modeled_objects"] if member["object_id"] == "tx_outer_rect_void_coil"
    )
    baseline_tx_inner_entry = next(
        member for member in baseline_ledger["modeled_objects"] if member["object_id"] == "tx_inner_rect_void_coil"
    )
    baseline_tx_outer_terminal_vertices = _rounded_vertex_set(
        _vertex_triplets(
            cast(list[list[float]], cast(dict[str, object], baseline_tx_outer_entry["terminal_metadata"])["port_sheet_vertices_xyz"]),
        )
    )
    baseline_tx_inner_terminal_vertices = _rounded_vertex_set(
        _vertex_triplets(
            cast(list[list[float]], cast(dict[str, object], baseline_tx_inner_entry["terminal_metadata"])["port_sheet_vertices_xyz"]),
        )
    )

    moved_source_text = source_text.replace(
        "origin_xyz = [0.0, -140.0, 0.0]\nsize_xyz = [160.0, 280.0, 90.0]",
        "origin_xyz = [12.0, -120.0, 20.0]\nsize_xyz = [220.0, 240.0, 80.0]",
        1,
    )
    moved_toml = _write_spec(tmp_path, moved_source_text)
    ledger = export_type2_step_artifacts(
        toml_path=moved_toml,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    non_model_entry = ledger["non_model_objects"][0]
    member_objects = cast(Sequence[dict[str, object]], non_model_entry["member_objects"])
    pcb_bridge_member = _find_member_object(
        member_objects=member_objects,
        object_id=_TX_POSITIVE_BRIDGE_PCB_OBJECT_ID,
    )
    copper_bridge_member = _find_member_object(
        member_objects=member_objects,
        object_id=_TX_POSITIVE_BRIDGE_COPPER_OBJECT_ID,
    )
    neg_pcb_bridge_member = _find_member_object(
        member_objects=member_objects,
        object_id=_TX_NEGATIVE_BRIDGE_PCB_OBJECT_ID,
    )
    neg_copper_bridge_member = _find_member_object(
        member_objects=member_objects,
        object_id=_TX_NEGATIVE_BRIDGE_COPPER_OBJECT_ID,
    )

    _assert_bridge_member_contract(
        member=pcb_bridge_member,
        expected_role=_TX_POSITIVE_BRIDGE_ROLE,
        expected_material_thickness_mm=0.365,
        expected_total_stack_thickness_mm=_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    )
    _assert_bridge_member_contract(
        member=copper_bridge_member,
        expected_role=_TX_POSITIVE_BRIDGE_ROLE,
        expected_material_thickness_mm=0.035,
        expected_total_stack_thickness_mm=_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    )
    _assert_bridge_member_contract(
        member=neg_pcb_bridge_member,
        expected_role=_TX_NEGATIVE_BRIDGE_ROLE,
        expected_material_thickness_mm=0.365,
        expected_total_stack_thickness_mm=_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    )
    _assert_bridge_member_contract(
        member=neg_copper_bridge_member,
        expected_role=_TX_NEGATIVE_BRIDGE_ROLE,
        expected_material_thickness_mm=0.035,
        expected_total_stack_thickness_mm=_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    )

    tx_inner_entry = next(
        member for member in ledger["modeled_objects"] if member["object_id"] == "tx_inner_rect_void_coil"
    )
    tx_outer_entry = next(
        member for member in ledger["modeled_objects"] if member["object_id"] == "tx_outer_rect_void_coil"
    )
    tx_outer_member = next(member for member in member_objects if member["object_id"] == "tx_outer_region")
    tx_inner_actual_member = next(member for member in member_objects if member["object_id"] == "tx_inner_actual_region")
    tx_inner_actual_min_xyz, tx_inner_actual_max_xyz, _ = _canonical_bounds(tx_inner_actual_member)
    tx_outer_prism = cast(dict[str, object], tx_outer_member["tx_outer_region_prism"])
    tx_outer_terminal_metadata = cast(dict[str, object], tx_outer_entry["terminal_metadata"])
    tx_inner_terminal_metadata = cast(dict[str, object], tx_inner_entry["terminal_metadata"])
    expected_positive_bridge_vertices = (
        _edge_vertex_set_from_sheet_metadata(terminal_metadata=tx_outer_terminal_metadata, edge_role="signal")
        | _edge_vertex_set_from_sheet_metadata(terminal_metadata=tx_inner_terminal_metadata, edge_role="signal")
    )
    expected_negative_bridge_vertices = (
        _edge_vertex_set_from_sheet_metadata(terminal_metadata=tx_outer_terminal_metadata, edge_role="reference")
        | _edge_vertex_set_from_sheet_metadata(terminal_metadata=tx_inner_terminal_metadata, edge_role="reference")
    )
    tx_outer_term_vertices = _vertex_triplets(
        cast(list[list[float]], tx_outer_terminal_metadata["port_sheet_vertices_xyz"]),
    )
    tx_inner_term_vertices = _vertex_triplets(
        cast(list[list[float]], tx_inner_terminal_metadata["port_sheet_vertices_xyz"]),
    )

    positive_bridge_union_vertices = set(
        _rounded_vertex_set(_shape_vertices(Path(ledger["scene_step_path"]), label=_TX_POSITIVE_BRIDGE_PCB_OBJECT_ID))
        | _rounded_vertex_set(
            _shape_vertices(Path(ledger["scene_step_path"]), label=_TX_POSITIVE_BRIDGE_COPPER_OBJECT_ID)
        )
    )
    negative_bridge_union_vertices = set(
        _rounded_vertex_set(_shape_vertices(Path(ledger["scene_step_path"]), label=_TX_NEGATIVE_BRIDGE_PCB_OBJECT_ID))
        | _rounded_vertex_set(
            _shape_vertices(Path(ledger["scene_step_path"]), label=_TX_NEGATIVE_BRIDGE_COPPER_OBJECT_ID)
        )
    )
    assert expected_positive_bridge_vertices <= positive_bridge_union_vertices
    assert expected_negative_bridge_vertices <= negative_bridge_union_vertices
    assert _rounded_vertex_set(tx_outer_term_vertices) != baseline_tx_outer_terminal_vertices
    assert _rounded_vertex_set(tx_inner_term_vertices) != baseline_tx_inner_terminal_vertices
    _assert_points_inside_tx_outer_prism_local_bounds(
        points_xyz=tx_outer_term_vertices,
        tx_outer_prism=tx_outer_prism,
        label="tx_outer terminal_metadata port sheet",
    )
    _assert_tx_outer_points_use_prism_local_span(
        points_xyz=tx_outer_term_vertices,
        tx_outer_prism=tx_outer_prism,
        label="tx_outer terminal_metadata port sheet",
    )
    for terminal_vertex in tx_inner_term_vertices:
        assert terminal_vertex[0] >= tx_inner_actual_min_xyz[0] - 1e-6
        assert terminal_vertex[0] <= tx_inner_actual_max_xyz[0] + 1e-6
        assert terminal_vertex[1] >= tx_inner_actual_min_xyz[1] - 1e-6
        assert terminal_vertex[1] <= tx_inner_actual_max_xyz[1] + 1e-6
        assert terminal_vertex[2] >= tx_inner_actual_min_xyz[2] - 1e-6
        assert terminal_vertex[2] <= tx_inner_actual_max_xyz[2] + 1e-6


def test_export_type2_step_artifacts_centers_tx_inner_region_y_usage_ratio(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_text = (repo_root / "examples" / "type2_fixed.toml").read_text(encoding="utf-8")
    source_text = source_text.replace(
        "range = [false, 1.0, 1.0, 1]",
        "range = [false, 0.5, 0.5, 1]",
        1,
    )
    source_toml = _write_spec(tmp_path, source_text)

    ledger = export_type2_step_artifacts(
        toml_path=source_toml,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    non_model_entry = ledger["non_model_objects"][0]
    member_objects = cast(Sequence[dict[str, object]], non_model_entry["member_objects"])
    tx_inner_member = next(member for member in member_objects if member["object_id"] == "tx_inner_region")
    canonical_coordinates = cast(dict[str, object], tx_inner_member["canonical_coordinates"])
    assert canonical_coordinates["outer_bounds_min_xyz"] == pytest.approx((0.0, -300.0, 0.0))
    assert canonical_coordinates["outer_bounds_size_xyz"] == pytest.approx((712.8, 600.0, 81.0))
    reference_line = cast(dict[str, object], tx_inner_member["tx_reference_line"])
    assert reference_line["y_usage_ratio"] == pytest.approx(0.5)
    assert reference_line["line_start_xyz"] == pytest.approx((712.8, -300.0, 81.0))
    assert reference_line["line_end_xyz"] == pytest.approx((712.8, 300.0, 81.0))
    assert all(member["object_id"] != "tx_outer_region" for member in member_objects)
    assert all(member["object_id"] != "tx_outer_actual_region" for member in member_objects)


def test_export_type2_step_artifacts_resizes_tx_inner_actual_region_without_resizing_guide(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_fixed.toml"
    source_text = source_toml.read_text(encoding="utf-8")
    changed_spec, _source_bytes = load_toml_bytes(source_toml)
    modeled_objects = cast(list[dict[str, object]], changed_spec["modeled_objects"])
    tx_inner_object = next(
        modeled_object
        for modeled_object in modeled_objects
        if modeled_object["object_id"] == "tx_inner_rect_void_coil"
    )
    outer_x_usage_ratio = cast(dict[str, object], tx_inner_object["outer_x_usage_ratio"])
    outer_y_usage_ratio = cast(dict[str, object], tx_inner_object["outer_y_usage_ratio"])
    outer_x_usage_ratio["range"] = [False, 0.25, 0.25, 1]
    outer_y_usage_ratio["range"] = [False, 0.3, 0.3, 1]
    changed_text = toml_dumps(changed_spec)
    assert changed_text != source_text
    baseline_dir = tmp_path / "baseline"
    changed_dir = tmp_path / "changed"
    baseline_dir.mkdir()
    changed_dir.mkdir()
    baseline_toml = _write_spec(baseline_dir, source_text)
    changed_toml = _write_spec(changed_dir, changed_text)

    baseline_ledger = export_type2_step_artifacts(
        toml_path=baseline_toml,
        output_dir=tmp_path / "baseline_out",
        ledger_path=tmp_path / "baseline_out" / "ledger.json",
        seed=0,
    )
    changed_ledger = export_type2_step_artifacts(
        toml_path=changed_toml,
        output_dir=tmp_path / "changed_out",
        ledger_path=tmp_path / "changed_out" / "ledger.json",
        seed=0,
    )

    baseline_member_objects = cast(Sequence[dict[str, object]], baseline_ledger["non_model_objects"][0]["member_objects"])
    changed_member_objects = cast(Sequence[dict[str, object]], changed_ledger["non_model_objects"][0]["member_objects"])
    baseline_guide = next(member for member in baseline_member_objects if member["object_id"] == "tx_inner_region")
    changed_guide = next(member for member in changed_member_objects if member["object_id"] == "tx_inner_region")
    baseline_actual = next(member for member in baseline_member_objects if member["object_id"] == "tx_inner_actual_region")
    changed_actual = next(member for member in changed_member_objects if member["object_id"] == "tx_inner_actual_region")
    baseline_outer_guide = next(member for member in baseline_member_objects if member["object_id"] == "tx_outer_region")
    changed_outer_guide = next(member for member in changed_member_objects if member["object_id"] == "tx_outer_region")
    baseline_outer_actual = next(
        member for member in baseline_member_objects if member["object_id"] == "tx_outer_actual_region"
    )
    changed_outer_actual = next(
        member for member in changed_member_objects if member["object_id"] == "tx_outer_actual_region"
    )

    baseline_guide_min_xyz, baseline_guide_max_xyz, baseline_guide_size_xyz = _canonical_bounds(baseline_guide)
    changed_guide_min_xyz, changed_guide_max_xyz, changed_guide_size_xyz = _canonical_bounds(changed_guide)
    assert changed_guide_min_xyz == pytest.approx(baseline_guide_min_xyz)
    assert changed_guide_max_xyz == pytest.approx(baseline_guide_max_xyz)
    assert changed_guide_size_xyz == pytest.approx(baseline_guide_size_xyz)
    baseline_actual_min_xyz, _baseline_actual_max_xyz, baseline_actual_size_xyz = _canonical_bounds(baseline_actual)
    changed_actual_min_xyz, _changed_actual_max_xyz, changed_actual_size_xyz = _canonical_bounds(changed_actual)
    baseline_inner_entry = next(
        entry for entry in baseline_ledger["modeled_objects"] if entry["object_id"] == "tx_inner_rect_void_coil"
    )
    changed_inner_entry = next(
        entry for entry in changed_ledger["modeled_objects"] if entry["object_id"] == "tx_inner_rect_void_coil"
    )
    baseline_inner_model_min_xyz, baseline_inner_model_max_xyz, baseline_inner_model_size_xyz = _canonical_bounds(
        cast(dict[str, object], baseline_inner_entry)
    )
    changed_inner_model_min_xyz, changed_inner_model_max_xyz, changed_inner_model_size_xyz = _canonical_bounds(
        cast(dict[str, object], changed_inner_entry)
    )
    baseline_actual_region = cast(dict[str, object], baseline_actual["tx_actual_region"])
    changed_actual_region = cast(dict[str, object], changed_actual["tx_actual_region"])
    baseline_actual_region_bounds = cast(dict[str, object], baseline_actual_region["actual_region_bounds"])
    changed_actual_region_bounds = cast(dict[str, object], changed_actual_region["actual_region_bounds"])
    baseline_physical_bounds = cast(dict[str, object], baseline_actual_region["physical_modeled_body_bounds"])
    changed_physical_bounds = cast(dict[str, object], changed_actual_region["physical_modeled_body_bounds"])
    assert baseline_actual_region_bounds["min_xyz"] == pytest.approx(baseline_actual_min_xyz)
    assert baseline_actual_region_bounds["size_xyz"] == pytest.approx(baseline_actual_size_xyz)
    assert changed_actual_region_bounds["min_xyz"] == pytest.approx(changed_actual_min_xyz)
    assert changed_actual_region_bounds["size_xyz"] == pytest.approx(changed_actual_size_xyz)
    assert baseline_physical_bounds["min_xyz"] == pytest.approx(baseline_inner_model_min_xyz)
    assert baseline_physical_bounds["max_xyz"] == pytest.approx(baseline_inner_model_max_xyz)
    assert baseline_physical_bounds["size_xyz"] == pytest.approx(baseline_inner_model_size_xyz)
    assert changed_physical_bounds["min_xyz"] == pytest.approx(changed_inner_model_min_xyz)
    assert changed_physical_bounds["max_xyz"] == pytest.approx(changed_inner_model_max_xyz)
    assert changed_physical_bounds["size_xyz"] == pytest.approx(changed_inner_model_size_xyz)
    assert baseline_physical_bounds["min_xyz"] == pytest.approx(baseline_actual_region_bounds["min_xyz"])
    assert baseline_physical_bounds["size_xyz"] == pytest.approx(baseline_actual_region_bounds["size_xyz"])
    assert changed_physical_bounds["min_xyz"] == pytest.approx(changed_actual_region_bounds["min_xyz"])
    assert changed_physical_bounds["size_xyz"] == pytest.approx(changed_actual_region_bounds["size_xyz"])
    assert changed_actual_size_xyz[0] == pytest.approx(baseline_actual_size_xyz[0] / 2.0)
    assert changed_actual_size_xyz[1] == pytest.approx(baseline_actual_size_xyz[1] / 2.0)
    assert changed_actual_size_xyz[2] == pytest.approx(baseline_actual_size_xyz[2])
    assert changed_actual_min_xyz[0] == pytest.approx(baseline_actual_min_xyz[0])
    assert changed_actual_min_xyz[1] != pytest.approx(baseline_actual_min_xyz[1])
    baseline_outer_guide_min_xyz, baseline_outer_guide_max_xyz, baseline_outer_guide_size_xyz = _canonical_bounds(
        baseline_outer_guide
    )
    changed_outer_guide_min_xyz, changed_outer_guide_max_xyz, changed_outer_guide_size_xyz = _canonical_bounds(
        changed_outer_guide
    )
    assert changed_outer_guide_min_xyz == pytest.approx(baseline_outer_guide_min_xyz)
    assert changed_outer_guide_max_xyz == pytest.approx(baseline_outer_guide_max_xyz)
    assert changed_outer_guide_size_xyz == pytest.approx(baseline_outer_guide_size_xyz)
    baseline_outer_actual_min_xyz, _baseline_outer_actual_max_xyz, baseline_outer_actual_size_xyz = _canonical_bounds(
        baseline_outer_actual
    )
    changed_outer_actual_min_xyz, _changed_outer_actual_max_xyz, changed_outer_actual_size_xyz = _canonical_bounds(
        changed_outer_actual
    )
    assert changed_outer_actual_size_xyz[0] < baseline_outer_actual_size_xyz[0]
    assert changed_outer_actual_size_xyz[1] == pytest.approx(baseline_outer_actual_size_xyz[1] / 2.0)
    assert changed_outer_actual_size_xyz[2] < baseline_outer_actual_size_xyz[2]
    assert changed_outer_actual_min_xyz[0] == pytest.approx(baseline_outer_actual_min_xyz[0])
    assert changed_outer_actual_min_xyz[1] != pytest.approx(baseline_outer_actual_min_xyz[1])


def test_export_type2_step_artifacts_moves_tx_outer_model_and_actual_provenance_with_x_position_ratio(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_fixed.toml"
    source_text = source_toml.read_text(encoding="utf-8")
    mid_ratio_spec, _source_bytes = load_toml_bytes(source_toml)
    mid_ratio_modeled_objects = cast(list[dict[str, object]], mid_ratio_spec["modeled_objects"])
    mid_ratio_tx_inner_object = next(
        modeled_object
        for modeled_object in mid_ratio_modeled_objects
        if modeled_object["object_id"] == "tx_inner_rect_void_coil"
    )
    mid_ratio_tx_outer_x_position_ratio = cast(
        dict[str, object], mid_ratio_tx_inner_object["tx_outer_x_position_ratio"]
    )
    mid_ratio_tx_outer_x_position_ratio["range"] = [False, 0.5942857142857143, 0.5942857142857143, 1]
    mid_ratio_text = toml_dumps(mid_ratio_spec)
    assert mid_ratio_text != source_text
    changed_spec, _changed_source_bytes = load_toml_bytes(source_toml)
    modeled_objects = cast(list[dict[str, object]], changed_spec["modeled_objects"])
    tx_inner_object = next(
        modeled_object
        for modeled_object in modeled_objects
        if modeled_object["object_id"] == "tx_inner_rect_void_coil"
    )
    tx_outer_x_position_ratio = cast(dict[str, object], tx_inner_object["tx_outer_x_position_ratio"])
    tx_outer_x_position_ratio["range"] = [False, 1.0, 1.0, 1]
    changed_text = toml_dumps(changed_spec)
    assert changed_text != source_text
    baseline_dir = tmp_path / "baseline"
    mid_ratio_dir = tmp_path / "mid_ratio"
    changed_dir = tmp_path / "changed"
    baseline_dir.mkdir()
    mid_ratio_dir.mkdir()
    changed_dir.mkdir()
    baseline_toml = _write_spec(baseline_dir, source_text)
    mid_ratio_toml = _write_spec(mid_ratio_dir, mid_ratio_text)
    changed_toml = _write_spec(changed_dir, changed_text)

    baseline_ledger = export_type2_step_artifacts(
        toml_path=baseline_toml,
        output_dir=tmp_path / "baseline_out",
        ledger_path=tmp_path / "baseline_out" / "ledger.json",
        seed=0,
    )
    mid_ratio_ledger = export_type2_step_artifacts(
        toml_path=mid_ratio_toml,
        output_dir=tmp_path / "mid_ratio_out",
        ledger_path=tmp_path / "mid_ratio_out" / "ledger.json",
        seed=0,
    )
    changed_ledger = export_type2_step_artifacts(
        toml_path=changed_toml,
        output_dir=tmp_path / "changed_out",
        ledger_path=tmp_path / "changed_out" / "ledger.json",
        seed=0,
    )

    baseline_member_objects = cast(Sequence[dict[str, object]], baseline_ledger["non_model_objects"][0]["member_objects"])
    mid_ratio_member_objects = cast(
        Sequence[dict[str, object]], mid_ratio_ledger["non_model_objects"][0]["member_objects"]
    )
    changed_member_objects = cast(Sequence[dict[str, object]], changed_ledger["non_model_objects"][0]["member_objects"])
    baseline_outer_member = next(member for member in baseline_member_objects if member["object_id"] == "tx_outer_region")
    mid_ratio_outer_member = next(member for member in mid_ratio_member_objects if member["object_id"] == "tx_outer_region")
    changed_outer_member = next(member for member in changed_member_objects if member["object_id"] == "tx_outer_region")
    baseline_outer_actual_member = next(
        member for member in baseline_member_objects if member["object_id"] == "tx_outer_actual_region"
    )
    mid_ratio_outer_actual_member = next(
        member for member in mid_ratio_member_objects if member["object_id"] == "tx_outer_actual_region"
    )
    changed_outer_actual_member = next(
        member for member in changed_member_objects if member["object_id"] == "tx_outer_actual_region"
    )
    baseline_outer_entry = next(
        entry for entry in baseline_ledger["modeled_objects"] if entry["object_id"] == "tx_outer_rect_void_coil"
    )
    mid_ratio_outer_entry = next(
        entry for entry in mid_ratio_ledger["modeled_objects"] if entry["object_id"] == "tx_outer_rect_void_coil"
    )
    changed_outer_entry = next(
        entry for entry in changed_ledger["modeled_objects"] if entry["object_id"] == "tx_outer_rect_void_coil"
    )

    baseline_outer_min_xyz, baseline_outer_max_xyz, baseline_outer_size_xyz = _canonical_bounds(baseline_outer_member)
    mid_ratio_outer_min_xyz, mid_ratio_outer_max_xyz, mid_ratio_outer_size_xyz = _canonical_bounds(
        mid_ratio_outer_member
    )
    changed_outer_min_xyz, changed_outer_max_xyz, changed_outer_size_xyz = _canonical_bounds(changed_outer_member)
    assert mid_ratio_outer_min_xyz == pytest.approx(baseline_outer_min_xyz)
    assert mid_ratio_outer_max_xyz == pytest.approx(baseline_outer_max_xyz)
    assert mid_ratio_outer_size_xyz == pytest.approx(baseline_outer_size_xyz)
    assert changed_outer_min_xyz == pytest.approx(baseline_outer_min_xyz)
    assert changed_outer_max_xyz == pytest.approx(baseline_outer_max_xyz)
    assert changed_outer_size_xyz == pytest.approx(baseline_outer_size_xyz)

    baseline_model_min_xyz, baseline_model_max_xyz, baseline_model_size_xyz = _canonical_bounds(
        cast(dict[str, object], baseline_outer_entry)
    )
    mid_ratio_model_min_xyz, mid_ratio_model_max_xyz, mid_ratio_model_size_xyz = _canonical_bounds(
        cast(dict[str, object], mid_ratio_outer_entry)
    )
    changed_model_min_xyz, changed_model_max_xyz, changed_model_size_xyz = _canonical_bounds(
        cast(dict[str, object], changed_outer_entry)
    )
    _assert_tx_outer_actual_region_prism_local_x_position_ratio(
        actual_region_entry=baseline_outer_actual_member,
        owner_entry=baseline_outer_member,
        x_position_ratio=0.0,
    )
    _assert_tx_outer_actual_region_prism_local_x_position_ratio(
        actual_region_entry=mid_ratio_outer_actual_member,
        owner_entry=mid_ratio_outer_member,
        x_position_ratio=0.5942857142857143,
    )
    _assert_tx_outer_actual_region_prism_local_x_position_ratio(
        actual_region_entry=changed_outer_actual_member,
        owner_entry=changed_outer_member,
        x_position_ratio=1.0,
    )
    assert mid_ratio_model_min_xyz[0] != pytest.approx(baseline_model_min_xyz[0])
    assert mid_ratio_model_max_xyz[0] != pytest.approx(baseline_model_max_xyz[0])
    assert mid_ratio_model_size_xyz == pytest.approx(baseline_model_size_xyz)
    assert changed_model_min_xyz[0] != pytest.approx(baseline_model_min_xyz[0])
    assert changed_model_max_xyz[0] != pytest.approx(baseline_model_max_xyz[0])
    assert changed_model_size_xyz == pytest.approx(baseline_model_size_xyz)

    baseline_actual_region = cast(dict[str, object], baseline_outer_actual_member["tx_actual_region"])
    mid_ratio_actual_region = cast(dict[str, object], mid_ratio_outer_actual_member["tx_actual_region"])
    changed_actual_region = cast(dict[str, object], changed_outer_actual_member["tx_actual_region"])
    baseline_physical_bounds = cast(dict[str, object], baseline_actual_region["physical_modeled_body_bounds"])
    mid_ratio_physical_bounds = cast(dict[str, object], mid_ratio_actual_region["physical_modeled_body_bounds"])
    changed_physical_bounds = cast(dict[str, object], changed_actual_region["physical_modeled_body_bounds"])
    assert baseline_physical_bounds["min_xyz"] == pytest.approx(baseline_model_min_xyz)
    assert baseline_physical_bounds["max_xyz"] == pytest.approx(baseline_model_max_xyz)
    assert baseline_physical_bounds["size_xyz"] == pytest.approx(baseline_model_size_xyz)
    assert mid_ratio_physical_bounds["min_xyz"] == pytest.approx(mid_ratio_model_min_xyz)
    assert mid_ratio_physical_bounds["max_xyz"] == pytest.approx(mid_ratio_model_max_xyz)
    assert mid_ratio_physical_bounds["size_xyz"] == pytest.approx(mid_ratio_model_size_xyz)
    assert changed_physical_bounds["min_xyz"] == pytest.approx(changed_model_min_xyz)
    assert changed_physical_bounds["max_xyz"] == pytest.approx(changed_model_max_xyz)
    assert changed_physical_bounds["size_xyz"] == pytest.approx(changed_model_size_xyz)

    baseline_actual_min_xyz, baseline_actual_max_xyz, baseline_actual_size_xyz = _canonical_bounds(
        baseline_outer_actual_member
    )
    mid_ratio_actual_min_xyz, mid_ratio_actual_max_xyz, mid_ratio_actual_size_xyz = _canonical_bounds(
        mid_ratio_outer_actual_member
    )
    changed_actual_min_xyz, changed_actual_max_xyz, changed_actual_size_xyz = _canonical_bounds(
        changed_outer_actual_member
    )
    assert mid_ratio_actual_min_xyz[0] != pytest.approx(baseline_actual_min_xyz[0])
    assert mid_ratio_actual_max_xyz[0] != pytest.approx(baseline_actual_max_xyz[0])
    assert mid_ratio_actual_size_xyz == pytest.approx(baseline_actual_size_xyz)
    assert changed_actual_min_xyz[0] != pytest.approx(baseline_actual_min_xyz[0])
    assert changed_actual_max_xyz[0] != pytest.approx(baseline_actual_max_xyz[0])
    assert changed_actual_size_xyz == pytest.approx(baseline_actual_size_xyz)


def test_export_type2_step_artifacts_derives_tx_outer_region_from_moved_tx_region(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_text = (repo_root / "examples" / "type2_fixed.toml").read_text(encoding="utf-8")
    source_text = source_text.replace(
        "origin_xyz = [0.0, -140.0, 0.0]\nsize_xyz = [160.0, 280.0, 90.0]",
        "origin_xyz = [12.0, -120.0, 20.0]\nsize_xyz = [220.0, 240.0, 80.0]",
        1,
    )
    source_toml = _write_spec(tmp_path, source_text)

    ledger = export_type2_step_artifacts(
        toml_path=source_toml,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    non_model_entry = ledger["non_model_objects"][0]
    member_objects = cast(Sequence[dict[str, object]], non_model_entry["member_objects"])
    tx_region_member = next(member for member in member_objects if member["object_id"] == "tx_region")
    tx_inner_member = next(member for member in member_objects if member["object_id"] == "tx_inner_region")
    tx_outer_member = next(member for member in member_objects if member["object_id"] == "tx_outer_region")
    tx_region_min_xyz, tx_region_size_xyz = _canonical_min_size(tx_region_member)
    tx_inner_min_xyz, tx_inner_size_xyz = _canonical_min_size(tx_inner_member)
    tx_outer_prism = cast(dict[str, object], tx_outer_member["tx_outer_region_prism"])
    tx_outer_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_outer_rect_void_coil")
    scene_shapes_by_label = _step_shapes_by_label(Path(ledger["scene_step_path"]))
    tx_outer_top_face_normal = _prism_top_face_normal(tx_outer_prism=tx_outer_prism)

    assert tx_region_min_xyz == pytest.approx((12.0, -120.0, 20.0))
    assert tx_region_size_xyz == pytest.approx((220.0, 240.0, 80.0))
    _assert_tx_outer_region_prism_follows_semantic_edges(
        tx_outer_prism=tx_outer_prism,
        tx_region_min_xyz=tx_region_min_xyz,
        tx_region_size_xyz=tx_region_size_xyz,
        tx_inner_min_xyz=tx_inner_min_xyz,
        tx_inner_size_xyz=tx_inner_size_xyz,
    )
    assert set(tx_outer_entry["expected_exported_body_names"]) <= set(scene_shapes_by_label)
    for body_name in cast(tuple[str, ...], tx_outer_entry["expected_exported_body_names"]):
        outer_body_shape = scene_shapes_by_label[body_name]
        _assert_shape_has_face_normal_parallel_to(
            shape=outer_body_shape,
            target_normal_xyz=tx_outer_top_face_normal,
            face_label=body_name,
            min_dot=0.995,
            min_abs_target_x_component_ratio=0.6,
        )
        outer_body_vertices = _shape_vertices(Path(ledger["scene_step_path"]), label=body_name)
        _assert_points_inside_tx_outer_prism_local_bounds(
            points_xyz=outer_body_vertices,
            tx_outer_prism=tx_outer_prism,
            label=body_name,
        )
        _assert_tx_outer_points_use_prism_local_span(
            points_xyz=outer_body_vertices,
            tx_outer_prism=tx_outer_prism,
            label=body_name,
        )


@pytest.mark.parametrize(
    ("ratio_name", "invalid_range", "match"),
    (
        ("x_ratio", "[false, 0.0, 0.0, 1]", r"tx_reference_line\.x_ratio.*strictly inside"),
        ("y_usage_ratio", "[false, 0.0, 0.0, 1]", r"tx_reference_line\.y_usage_ratio.*\(0, 1\]"),
        ("y_usage_ratio", "[false, 1.1, 1.1, 1]", r"tx_reference_line\.y_usage_ratio.*\(0, 1\]"),
        ("z_ratio", "[false, 1.1, 1.1, 1]", r"tx_reference_line\.z_ratio.*\(0, 1\]"),
    ),
)
def test_load_type2_step_spec_rejects_invalid_tx_reference_line_ratio(
    tmp_path: Path,
    ratio_name: str,
    invalid_range: str,
    match: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_text = (repo_root / "examples" / "type2_fixed.toml").read_text(encoding="utf-8")
    valid_range_by_ratio = {
        "x_ratio": "[false, 0.99, 0.99, 1]",
        "y_usage_ratio": "[false, 1.0, 1.0, 1]",
        "z_ratio": "[false, 0.9, 0.9, 1]",
    }
    assert ratio_name in valid_range_by_ratio
    valid_range = valid_range_by_ratio[ratio_name]
    invalid_text = source_text.replace(f"range = {valid_range}", f"range = {invalid_range}", 1)
    toml_path = _write_spec(tmp_path, invalid_text)

    with pytest.raises(ValueError, match=match):
        load_type2_step_spec(toml_path)


def test_export_type2_step_artifacts_tilts_only_tx_region_actual_stack_space_toward_modeled_rx_center(tmp_path: Path) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="rx_rect_void_coil",
            modeled_role="rx_single_coil",
            tx_region_actual_x_division_count_range="[true, 3, 3, 1]",
            tx_region_actual_y_division_count_range="[true, 3, 3, 1]",
            tx_region_actual_stack_space_tilt_enabled_range="[true, 1, 1, 1]",
        ),
    )
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )
    non_model_entry = ledger["non_model_objects"][0]
    member_objects = non_model_entry["member_objects"]
    scene_shapes_by_label = _step_shapes_by_label(Path(ledger["scene_step_path"]))

    rx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "rx_rect_void_coil")
    rx_canonical = cast(dict[str, object], rx_entry["canonical_coordinates"])
    rx_min_xyz = cast(tuple[float, float, float], rx_canonical["outer_bounds_min_xyz"])
    rx_size_xyz = cast(tuple[float, float, float], rx_canonical["outer_bounds_size_xyz"])
    rx_center = (
        rx_min_xyz[0] + (rx_size_xyz[0] * 0.5),
        rx_min_xyz[1] + (rx_size_xyz[1] * 0.5),
        rx_min_xyz[2] + (rx_size_xyz[2] * 0.5),
    )

    tile_members = {
        cast(str, member["object_id"]): member
        for member in member_objects
        if cast(str, member["role"]) == "tx_region_actual"
    }
    stack_space_members = [
        member for member in member_objects if cast(str, member["role"]) == "tx_region_actual_stack_space"
    ]
    assert len(tile_members) == 9
    assert len(stack_space_members) == 9

    for tile_member in tile_members.values():
        tile_name = cast(str, tile_member["object_id"])
        assert tile_name in scene_shapes_by_label
        _assert_shape_faces_axis_aligned(scene_shapes_by_label[tile_name])

    for stack_space_member in stack_space_members:
        stack_space_object_id = cast(str, stack_space_member["object_id"])
        assert stack_space_object_id in scene_shapes_by_label
        if stack_space_object_id == "tx_region_actual_stack_space":
            parent_tile_id = "tx_region_actual"
        else:
            parent_tile_id = f"tx_region_actual{stack_space_object_id.removeprefix('tx_region_actual_stack_space')}"
        assert parent_tile_id in tile_members
        tile_canonical = cast(dict[str, object], tile_members[parent_tile_id]["canonical_coordinates"])
        tile_min_xyz = cast(tuple[float, float, float], tile_canonical["outer_bounds_min_xyz"])
        tile_size_xyz = cast(tuple[float, float, float], tile_canonical["outer_bounds_size_xyz"])
        tile_bottom_z = tile_min_xyz[2]
        tile_top_z = tile_min_xyz[2] + tile_size_xyz[2]

        stack_space_shape = scene_shapes_by_label[stack_space_object_id]
        stack_space_bbox = stack_space_shape.bounding_box()
        stack_space_center = (
            (stack_space_bbox.min.X + stack_space_bbox.max.X) * 0.5,
            (stack_space_bbox.min.Y + stack_space_bbox.max.Y) * 0.5,
            (stack_space_bbox.min.Z + stack_space_bbox.max.Z) * 0.5,
        )
        direction_to_rx = _normalize_vector_xyz(
            (
                rx_center[0] - stack_space_center[0],
                rx_center[1] - stack_space_center[1],
                rx_center[2] - stack_space_center[2],
            )
        )
        top_face_normal = _face_normal_closest_to_direction(
            shape=stack_space_shape,
            direction_xyz=direction_to_rx,
        )
        assert _dot_xyz(top_face_normal, direction_to_rx) >= 0.999
        assert abs(top_face_normal[2]) < 0.995
        assert stack_space_bbox.max.Z <= tile_top_z + 1e-8
        assert stack_space_bbox.min.Z >= tile_bottom_z - 1e-8

        stack_space_canonical = cast(dict[str, object], stack_space_member["canonical_coordinates"])
        stack_space_canonical_max_xyz = cast(tuple[float, float, float], stack_space_canonical["outer_bounds_max_xyz"])
        assert stack_space_canonical_max_xyz[2] <= tile_top_z + 1e-8


def _assert_tx_rect_void_columns_expected_body_contract(
    *,
    expected_names: tuple[str, ...],
    x_division_count: int,
    y_division_count: int,
) -> None:
    tile_indices = {
        (x_index, y_index)
        for x_index in range(x_division_count)
        for y_index in range(y_division_count)
    }
    pcb_pattern = re.compile(r"^txrvc_x(\d+)_y(\d+)_pcb_l(\d+)$")
    copper_pattern = re.compile(r"^txrvc_x(\d+)_y(\d+)_cu_l(\d+)$")
    stub_pattern = re.compile(r"^txrvc_x(\d+)_y(\d+)_stub_(start|end|s|e)$")
    pcb_layers_by_tile: dict[tuple[int, int], set[int]] = {}
    copper_layers_by_tile: dict[tuple[int, int], set[int]] = {}
    stub_hints_by_tile: dict[tuple[int, int], set[str]] = {}
    body_count_by_tile: dict[tuple[int, int], int] = {}
    fused_copper_body_name = "tx_rect_void_columns_copper"
    parallel_mode = fused_copper_body_name in expected_names

    for body_name in expected_names:
        if body_name == fused_copper_body_name:
            continue
        pcb_match = pcb_pattern.match(body_name)
        if pcb_match is not None:
            tile_index = (int(pcb_match.group(1)), int(pcb_match.group(2)))
            layer_index = int(pcb_match.group(3))
            assert tile_index in tile_indices
            pcb_layers_by_tile.setdefault(tile_index, set()).add(layer_index)
            body_count_by_tile[tile_index] = body_count_by_tile.get(tile_index, 0) + 1
            continue
        copper_match = copper_pattern.match(body_name)
        if copper_match is not None:
            tile_index = (int(copper_match.group(1)), int(copper_match.group(2)))
            layer_index = int(copper_match.group(3))
            assert tile_index in tile_indices
            copper_layers_by_tile.setdefault(tile_index, set()).add(layer_index)
            body_count_by_tile[tile_index] = body_count_by_tile.get(tile_index, 0) + 1
            continue
        stub_match = stub_pattern.match(body_name)
        if stub_match is not None:
            tile_index = (int(stub_match.group(1)), int(stub_match.group(2)))
            terminal_hint_raw = stub_match.group(3)
            terminal_hint = "start" if terminal_hint_raw in ("start", "s") else "end"
            assert tile_index in tile_indices
            stub_hints_by_tile.setdefault(tile_index, set()).add(terminal_hint)
            body_count_by_tile[tile_index] = body_count_by_tile.get(tile_index, 0) + 1
            continue
        raise AssertionError(f"unexpected tx_rect_void_columns body label contract drift: {body_name}")

    assert set(pcb_layers_by_tile) == tile_indices
    if parallel_mode:
        assert copper_layers_by_tile == {}
        assert stub_hints_by_tile == {}
        assert expected_names.count(fused_copper_body_name) == 1
        expected_total_count = 1
        for tile_index in tile_indices:
            pcb_layers = pcb_layers_by_tile[tile_index]
            assert len(pcb_layers) > 0
            assert body_count_by_tile[tile_index] == len(pcb_layers)
            expected_total_count += len(pcb_layers)
        assert len(expected_names) == expected_total_count
        return

    assert set(copper_layers_by_tile) == tile_indices
    assert set(stub_hints_by_tile) == tile_indices

    expected_total_count = 0
    for tile_index in tile_indices:
        pcb_layers = pcb_layers_by_tile[tile_index]
        copper_layers = copper_layers_by_tile[tile_index]
        stub_hints = stub_hints_by_tile[tile_index]
        assert pcb_layers == copper_layers
        assert len(pcb_layers) > 0
        assert stub_hints == {"start", "end"}
        tile_expected_count = (len(pcb_layers) * 2) + 2
        assert body_count_by_tile[tile_index] == tile_expected_count
        expected_total_count += tile_expected_count
    assert len(expected_names) == expected_total_count


def _assert_tx_rect_void_columns_terminal_metadata_contract(
    *,
    terminal_metadata: dict[str, object],
    x_division_count: int,
    y_division_count: int,
) -> None:
    kind = terminal_metadata["kind"]
    if kind == "geometry_only":
        assert terminal_metadata["connection_status"] == "skipped_series"
        assert "source_label_metadata" not in terminal_metadata
        assert "tab_face_vertices_xyz" not in terminal_metadata
        return
    if kind == "series_collector_tabs":
        assert terminal_metadata["connection_mode"] == 1
        source_label_metadata = cast(dict[str, object], terminal_metadata["source_label_metadata"])
        branch_count = x_division_count * y_division_count
        assert len(cast(tuple[str, ...], source_label_metadata["series_links"])) == branch_count - 1
        assert len(cast(tuple[str, ...], source_label_metadata["start_external_tabs"])) == 1
        assert len(cast(tuple[str, ...], source_label_metadata["end_external_tabs"])) == 1
        tab_face_vertices = cast(tuple[dict[str, object], ...], terminal_metadata["tab_face_vertices_xyz"])
        assert len(tab_face_vertices) == 2
        assert {cast(str, entry["terminal"]) for entry in tab_face_vertices} == {"start", "end"}
        for tab_face_entry in tab_face_vertices:
            vertices = cast(tuple[tuple[float, float, float], ...], tab_face_entry["vertices_xyz"])
            assert len(vertices) == 4
        assert terminal_metadata["branch_count"] == branch_count
        link_labels = cast(tuple[str, ...], terminal_metadata["link_labels"])
        assert len(link_labels) == branch_count - 1
        assert len(set(link_labels)) == len(link_labels)
        tile_order = cast(tuple[tuple[int, int], ...], terminal_metadata["tile_order"])
        assert len(tile_order) == branch_count
        assert tile_order == tuple(
            (x_index, y_index)
            for y_index in range(y_division_count)
            for x_index in (
                range(x_division_count)
                if y_index % 2 == 0
                else range(x_division_count - 1, -1, -1)
            )
        )
        path_length_audit = cast(dict[str, object], terminal_metadata["path_length_audit"])
        assert cast(float, path_length_audit["path_length_delta_mm"]) <= cast(float, path_length_audit["tolerance_mm"])
        overlap_audit = cast(dict[str, object], terminal_metadata["overlap_audit"])
        assert overlap_audit["positive_volume_pair_count"] == 0
        assert cast(float, overlap_audit["max_intersection_volume_mm3"]) <= cast(float, overlap_audit["tolerance_mm3"])
        return
    assert kind == "parallel_collector_tabs"
    assert terminal_metadata["connection_mode"] == 0
    source_label_metadata = cast(dict[str, object], terminal_metadata["source_label_metadata"])
    assert "start_row_rails" not in source_label_metadata
    assert "end_row_rails" not in source_label_metadata
    assert "start_spines" not in source_label_metadata
    assert "end_spines" not in source_label_metadata
    assert "start_feeders" not in source_label_metadata
    assert "end_feeders" not in source_label_metadata
    branch_count = x_division_count * y_division_count
    start_pours = cast(tuple[str, ...], source_label_metadata["start_pours"])
    end_pours = cast(tuple[str, ...], source_label_metadata["end_pours"])
    assert len(start_pours) == branch_count + 1
    assert len(end_pours) == branch_count + 1
    assert start_pours[0] == "txrvc_pour_s_bus"
    assert end_pours[0] == "txrvc_pour_e_bus"
    assert all(label.startswith("txrvc_pour_s_") for label in start_pours)
    assert all(label.startswith("txrvc_pour_e_") for label in end_pours)
    assert len(cast(tuple[str, ...], source_label_metadata["end_layer_drops"])) == branch_count
    assert len(cast(tuple[str, ...], source_label_metadata["start_external_tabs"])) == 1
    assert len(cast(tuple[str, ...], source_label_metadata["end_external_tabs"])) == 1
    tab_face_vertices = cast(tuple[dict[str, object], ...], terminal_metadata["tab_face_vertices_xyz"])
    assert len(tab_face_vertices) == 2
    assert {cast(str, entry["terminal"]) for entry in tab_face_vertices} == {"start", "end"}
    for tab_face_entry in tab_face_vertices:
        vertices = cast(tuple[tuple[float, float, float], ...], tab_face_entry["vertices_xyz"])
        assert len(vertices) == 4
    branch_balance_audit = cast(dict[str, object], terminal_metadata["branch_balance_audit"])
    assert cast(float, branch_balance_audit["balance_delta_mm"]) <= cast(float, branch_balance_audit["tolerance_mm"])
    assert cast(float, branch_balance_audit["max_branch_total_delta_mm"]) <= cast(
        float,
        branch_balance_audit["branch_spread_limit_mm"],
    )
    overlap_audit = cast(dict[str, object], terminal_metadata["overlap_audit"])
    assert overlap_audit["positive_volume_pair_count"] == 0
    assert cast(float, overlap_audit["max_intersection_volume_mm3"]) <= cast(float, overlap_audit["tolerance_mm3"])


# Manual performance probe only (excluded from default pytest):
# cd run && ../.venv/bin/python -m pytest ../tests/type2/test_generate_type2_step.py -k "tx_rect_void_columns_grid_variants" --durations=10 -q
def _export_tx_rect_void_columns_spec_and_expect_success(
    *,
    tmp_path: Path,
    x_division_count: int,
    y_division_count: int,
    force_safe_turn_allocation: bool = False,
    turn_profile_overrides: dict[str, str] | None = None,
) -> dict[str, object]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    turn_profile_kwargs: dict[str, str] = {}
    if turn_profile_overrides is not None:
        if force_safe_turn_allocation:
            raise RuntimeError("turn_profile_overrides and force_safe_turn_allocation are mutually exclusive")
        turn_profile_kwargs = dict(turn_profile_overrides)
    elif force_safe_turn_allocation:
        safe_turn_total = max(6, x_division_count * y_division_count)
        turn_profile_kwargs = {
            "connection_mode_range": "[true, 1, 1, 1]",
            "equivalent_turn_count_range": f"[false, {float(safe_turn_total)}, {float(safe_turn_total)}, 1]",
            "turn_weight_a_range": "[false, 1.0, 1.0, 1]",
            "turn_weight_b_range": "[false, 0.0, 0.0, 1]",
            "turn_weight_c_range": "[false, -0.3, 0.3, 21]",
        }
    toml_path = _write_spec(
        tmp_path,
        _type2_tx_rect_void_columns_spec_text(
            tx_region_actual_x_division_count_range=f"[true, {x_division_count}, {x_division_count}, 1]",
            tx_region_actual_y_division_count_range=f"[true, {y_division_count}, {y_division_count}, 1]",
            **turn_profile_kwargs,
        ),
    )
    output_dir = tmp_path / "out"
    output_ledger_path = output_dir / "ledger.json"
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=output_dir,
        ledger_path=output_ledger_path,
        seed=0,
    )
    assert output_ledger_path.exists()
    scene_step_path = Path(cast(str, ledger["scene_step_path"]))
    assert scene_step_path.is_file()
    tx_entry = cast(
        dict[str, object],
        next(
            entry for entry in cast(list[object], ledger["modeled_objects"])
            if cast(dict[str, object], entry)["object_id"] == "tx_rect_void_columns"
        ),
    )
    expected_names = cast(tuple[str, ...], tx_entry["expected_exported_body_names"])
    _assert_tx_rect_void_columns_expected_body_contract(
        expected_names=expected_names,
        x_division_count=x_division_count,
        y_division_count=y_division_count,
    )
    assert cast(int, tx_entry["expected_exported_body_count"]) == len(
        expected_names
    )
    assert cast(int, tx_entry["expected_exported_body_count"]) > 0
    terminal_metadata = cast(dict[str, object], tx_entry["terminal_metadata"])
    _assert_tx_rect_void_columns_terminal_metadata_contract(
        terminal_metadata=terminal_metadata,
        x_division_count=x_division_count,
        y_division_count=y_division_count,
    )
    modeled_metadata_path = output_dir / "metadata" / "tx_rect_void_columns.metadata.json"
    assert modeled_metadata_path.is_file()
    scene_shapes_by_label = _step_shapes_by_label(scene_step_path)
    for body_name in expected_names:
        assert body_name in scene_shapes_by_label
    fused_copper = scene_shapes_by_label["tx_rect_void_columns_copper"]
    for body_name in expected_names:
        if "_pcb_l" in body_name:
            _assert_zero_intersection_volume(scene_shapes_by_label[body_name], fused_copper)
    return tx_entry


@pytest.mark.parametrize(("x_division_count", "y_division_count"), ((1, 1), (2, 3), (3, 3)))
def test_export_type2_step_artifacts_tx_rect_void_columns_grid_variants(
    tmp_path: Path,
    x_division_count: int,
    y_division_count: int,
) -> None:
    _export_tx_rect_void_columns_spec_and_expect_success(
        tmp_path=tmp_path,
        x_division_count=x_division_count,
        y_division_count=y_division_count,
        force_safe_turn_allocation=True,
    )


@pytest.mark.parametrize(("x_division_count", "y_division_count"), ((1, 1), (1, 3), (2, 2), (3, 3)))
def test_export_type2_step_artifacts_tx_rect_void_columns_parallel_collector_variants(
    tmp_path: Path,
    x_division_count: int,
    y_division_count: int,
) -> None:
    safe_parallel_equivalent_turn_count = 1.0 / float(x_division_count * y_division_count)
    tx_entry = _export_tx_rect_void_columns_spec_and_expect_success(
        tmp_path=tmp_path,
        x_division_count=x_division_count,
        y_division_count=y_division_count,
        turn_profile_overrides={
            "connection_mode_range": "[true, 0, 0, 1]",
            "equivalent_turn_count_range": (
                f"[false, {safe_parallel_equivalent_turn_count}, {safe_parallel_equivalent_turn_count}, 1]"
            ),
            "turn_weight_a_range": "[false, 1.0, 1.0, 1]",
            "turn_weight_b_range": "[false, 0.0, 0.0, 1]",
            "turn_weight_c_range": "[false, 0.0, 0.0, 1]",
        },
    )
    expected_names = cast(tuple[str, ...], tx_entry["expected_exported_body_names"])
    assert expected_names.count("tx_rect_void_columns_copper") == 1
    assert not any("_cu_l" in body_name for body_name in expected_names)
    assert not any("_stub_" in body_name for body_name in expected_names)
    terminal_metadata = cast(dict[str, object], tx_entry["terminal_metadata"])
    assert terminal_metadata["kind"] == "parallel_collector_tabs"
    _assert_tx_rect_void_columns_terminal_metadata_contract(
        terminal_metadata=terminal_metadata,
        x_division_count=x_division_count,
        y_division_count=y_division_count,
    )


@pytest.mark.parametrize(("x_division_count", "y_division_count"), ((1, 1), (1, 3), (2, 2), (3, 3)))
def test_export_type2_step_artifacts_tx_rect_void_columns_series_collector_variants(
    tmp_path: Path,
    x_division_count: int,
    y_division_count: int,
) -> None:
    branch_count = x_division_count * y_division_count
    tx_entry = _export_tx_rect_void_columns_spec_and_expect_success(
        tmp_path=tmp_path,
        x_division_count=x_division_count,
        y_division_count=y_division_count,
        turn_profile_overrides={
            "connection_mode_range": "[true, 1, 1, 1]",
            "equivalent_turn_count_range": f"[false, {float(branch_count)}, {float(branch_count)}, 1]",
            "turn_weight_a_range": "[false, 1.0, 1.0, 1]",
            "turn_weight_b_range": "[false, 0.0, 0.0, 1]",
            "turn_weight_c_range": "[false, 0.0, 0.0, 1]",
        },
    )
    expected_names = cast(tuple[str, ...], tx_entry["expected_exported_body_names"])
    assert expected_names.count("tx_rect_void_columns_copper") == 1
    assert not any("_cu_l" in body_name for body_name in expected_names)
    assert not any("_stub_" in body_name for body_name in expected_names)
    terminal_metadata = cast(dict[str, object], tx_entry["terminal_metadata"])
    _assert_tx_rect_void_columns_terminal_metadata_contract(
        terminal_metadata=terminal_metadata,
        x_division_count=x_division_count,
        y_division_count=y_division_count,
    )


def test_export_type2_step_artifacts_tx_rect_void_columns_x1_division_variant(tmp_path: Path) -> None:
    _export_tx_rect_void_columns_spec_and_expect_success(
        tmp_path=tmp_path / "x1_base",
        x_division_count=1,
        y_division_count=2,
        force_safe_turn_allocation=True,
    )


def test_export_type2_step_artifacts_tx_rect_void_columns_series_collector_hides_individual_stub_bodies(
    tmp_path: Path,
) -> None:
    toml_path = _write_spec(
        tmp_path,
        _type2_tx_rect_void_columns_spec_text(
            tx_region_actual_x_division_count_range="[true, 2, 2, 1]",
            tx_region_actual_y_division_count_range="[true, 3, 3, 1]",
            connection_mode_range="[true, 1, 1, 1]",
            equivalent_turn_count_range="[false, 6.0, 6.0, 1]",
            turn_weight_a_range="[false, 1.0, 1.0, 1]",
            turn_weight_b_range="[false, 0.0, 0.0, 1]",
            turn_weight_c_range="[false, 0.0, 0.0, 1]",
        ),
    )
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )
    tx_entry = cast(
        dict[str, object],
        next(
            entry for entry in cast(list[object], ledger["modeled_objects"])
            if cast(dict[str, object], entry)["object_id"] == "tx_rect_void_columns"
        ),
    )
    terminal_metadata = cast(dict[str, object], tx_entry["terminal_metadata"])
    assert terminal_metadata["kind"] == "series_collector_tabs"
    assert "vertical_stub_body_names" not in terminal_metadata
    scene_shapes_by_label = _step_shapes_by_label(Path(cast(str, ledger["scene_step_path"])))
    assert "tx_rect_void_columns_copper" in scene_shapes_by_label
    assert not any("_stub_" in body_name for body_name in scene_shapes_by_label)


@pytest.mark.parametrize(
    ("x_division_count", "case_name"),
    (
        (2, "x_division_2"),
        (3, "x_division_3"),
    ),
)
def test_export_type2_step_artifacts_tx_rect_void_columns_multicolumn_grid_variants(
    tmp_path: Path,
    x_division_count: int,
    case_name: str,
) -> None:
    _export_tx_rect_void_columns_spec_and_expect_success(
        tmp_path=tmp_path / case_name,
        x_division_count=x_division_count,
        y_division_count=2,
        force_safe_turn_allocation=True,
    )


@pytest.mark.parametrize("x_division_count", (1, 2))
def test_export_type2_step_artifacts_tx_rect_void_columns_keeps_y_symmetric_turn_counts(
    tmp_path: Path,
    x_division_count: int,
) -> None:
    y_division_count = 3
    target_total_turn_count = (x_division_count * y_division_count) + 3
    turn_profile_overrides = {
        "connection_mode_range": "[true, 1, 1, 1]",
        "equivalent_turn_count_range": f"[false, {float(target_total_turn_count)}, {float(target_total_turn_count)}, 1]",
        "turn_weight_a_range": "[false, 1.0, 1.0, 1]",
        "turn_weight_b_range": "[false, 0.0, 0.0, 1]",
        "turn_weight_c_range": "[false, 0.0, 0.0, 1]",
    }
    _export_tx_rect_void_columns_spec_and_expect_success(
        tmp_path=tmp_path / "export",
        x_division_count=x_division_count,
        y_division_count=y_division_count,
        turn_profile_overrides=turn_profile_overrides,
    )

    diag_dir = tmp_path / "diag"
    diag_dir.mkdir()
    toml_path = _write_spec(
        diag_dir,
        _type2_tx_rect_void_columns_spec_text(
            tx_region_actual_x_division_count_range=f"[true, {x_division_count}, {x_division_count}, 1]",
            tx_region_actual_y_division_count_range=f"[true, {y_division_count}, {y_division_count}, 1]",
            **turn_profile_overrides,
        ),
    )
    spec = load_type2_step_spec(toml_path)
    tx_columns_spec = cast(
        ModeledTxRectVoidColumnsSpec,
        next(modeled for modeled in spec.modeled_objects if modeled.object_id == "tx_rect_void_columns"),
    )
    assert tx_columns_spec.equivalent_turn_count == RangeSpec(False, float(target_total_turn_count), float(target_total_turn_count), 1)
    resolved_non_model_specs = resolve_non_model_scene_specs(
        base_specs=spec.non_model_objects,
        derived_specs=spec.non_model_derived_objects,
        seed=0,
    )
    stack_space_specs = tuple(
        non_model_spec
        for non_model_spec in resolved_non_model_specs
        if non_model_spec.kind == "tx_region_actual_stack_space"
    )
    assert len(stack_space_specs) == x_division_count * y_division_count
    rx_region_max_spec = next(non_model_spec for non_model_spec in resolved_non_model_specs if non_model_spec.object_id == "rx_region_max")
    rx_center_xyz = (
        rx_region_max_spec.origin_xyz[0] + (rx_region_max_spec.size_xyz[0] * 0.5),
        rx_region_max_spec.origin_xyz[1] + (rx_region_max_spec.size_xyz[1] * 0.5),
        rx_region_max_spec.origin_xyz[2] + (rx_region_max_spec.size_xyz[2] * 0.5),
    )
    build_result = build_tx_rect_void_columns_axis_aligned_tile_scenes(
        spec=tx_columns_spec,
        stack_space_specs=stack_space_specs,
        rx_center_xyz=rx_center_xyz,
        seed=0,
    )
    _assert_tx_rect_void_columns_expected_body_contract(
        expected_names=build_result.expected_exported_body_names,
        x_division_count=x_division_count,
        y_division_count=y_division_count,
    )
    turn_count_by_tile = {
        (tile_scene.x_index, tile_scene.y_index): tile_scene.resolved_turn_count for tile_scene in build_result.tile_scenes
    }
    for x_index in range(x_division_count):
        assert turn_count_by_tile[(x_index, 0)] == turn_count_by_tile[(x_index, 2)]


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
            underlay_repeat_count_range=_range(True, 8.0, 8.0, 1),
        ),
    )
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    rx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "rx_rect_void_coil")
    expected_names = _rx_expected_body_names(underlay_repeat_count=8)
    assert rx_entry["expected_exported_body_names"] == expected_names
    assert rx_entry["expected_exported_body_count"] == len(expected_names)
    assert _normalized_body_groups(rx_entry["expected_exported_body_groups"]) == _normalized_body_groups(
        _rx_expected_body_groups(underlay_repeat_count=8)
    )
    scene_shapes_by_label = _step_shapes_by_label(Path(ledger["scene_step_path"]))
    assert "g_ferrite_rx" in scene_shapes_by_label
    assert type(scene_shapes_by_label["g_ferrite_rx"]).__name__ == "Compound"
    for label in _rx_underlay_expected_body_names(repeat_count=8):
        assert label in scene_shapes_by_label
    _assert_rx_full_backing_contract(
        scene_shapes_by_label=scene_shapes_by_label,
        rx_region_size_x=10.0,
    )


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
        turn_count=3,
        pcb_total_thickness_mm=_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    )
    assert tx_entry["expected_exported_body_names"] == expected_names
    assert tx_entry["expected_exported_body_count"] == len(expected_names)
    assert tx_entry["expected_exported_body_count"] == 6
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
    assert expected_names == (
        "tx_plate_copper",
        "tx_pcb_wall",
        "tx_stack_pet_psa",
        "tx_stack_ferrite",
        "tx_stack_air",
        "tx_pcb_coil",
    )
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
        turn_count=3,
        pcb_total_thickness_mm=_PLATE_STACK_EXAMPLE_PCB_TOTAL_THICKNESS_MM,
    )
    assert rx_entry["expected_exported_body_names"] == expected_names
    assert rx_entry["expected_exported_body_count"] == len(expected_names)
    assert rx_entry["expected_exported_body_count"] == 6
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
    assert expected_names == (
        "rx_plate_copper",
        "rx_pcb_wall",
        "rx_stack_pet_psa",
        "rx_stack_ferrite",
        "rx_stack_air",
        "rx_pcb_coil",
    )
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
    y_usage_ratio = resolve_modeled_plate_stack_y_usage_ratio(tx_modeled_spec, seed=0)
    z_usage_ratio = resolve_modeled_plate_stack_z_usage_ratio(tx_modeled_spec, seed=0)
    active_min_y, active_max_y, active_size_y = _plate_stack_active_y_bounds(
        owner_size_y=region_size_y,
        y_usage_ratio=y_usage_ratio,
    )
    active_min_z, active_max_z, active_size_z = _plate_stack_active_z_bounds(
        role="tx_plate_stack",
        owner_origin_z=region_min_z,
        owner_size_z=region_size_z,
        z_usage_ratio=z_usage_ratio,
    )

    assert tx_entry["plane"] == "YZ"
    assert tx_entry["placement_owner_id"] == "tx_region"
    assert cast(dict[str, object], tx_entry["terminal_metadata"])["kind"] == "stub_port"
    assert list(tx_entry["expected_exported_body_names"]) == list(
        _tx_plate_stack_expected_body_names(
            turn_count=3,
            pcb_total_thickness_mm=tx_modeled_spec.pcb_total_thickness_mm,
        )
    )
    assert tx_entry["expected_exported_body_count"] == len(tx_entry["expected_exported_body_names"])
    assert tx_min_x == pytest.approx(region_min_x)
    assert tx_min_y == pytest.approx(active_min_y - 5.0)
    assert tx_min_z == pytest.approx(active_min_z)
    assert tx_size_x == pytest.approx(total_plate_stack_thickness_mm(spec=cast(ModeledPlateStackSpec, tx_modeled_spec)))
    assert tx_size_y == pytest.approx(active_size_y + 5.0)
    assert tx_size_z == pytest.approx(active_size_z)
    tx_pitch_z = _plate_stack_pitch_z(owner_size_z=active_size_z, turn_count=3)
    tx_trace_height_z = tx_pitch_z * 0.4
    tx_centering_offset_z = (tx_pitch_z - tx_trace_height_z) / 2.0
    tx_step_min_xyz, tx_step_max_xyz = _body_bbox(Path(ledger["scene_step_path"]), label="tx_plate_copper")
    assert tx_step_min_xyz[0] == pytest.approx(region_min_x)
    assert tx_step_max_xyz[0] == pytest.approx(region_min_x + tx_size_x)
    assert tx_step_min_xyz[1] == pytest.approx(active_min_y - 5.0)
    assert tx_step_max_xyz[1] == pytest.approx(active_max_y)
    assert tx_step_min_xyz[2] >= active_min_z + tx_centering_offset_z - 1e-8
    assert tx_step_max_xyz[2] <= active_max_z - tx_centering_offset_z + 1e-8


def test_export_type2_step_artifacts_places_rx_single_coil_on_rx_region_max_min_x_anchor(tmp_path: Path) -> None:
    source_toml = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="rx_rect_void_coil",
            modeled_role="rx_single_coil",
            underlay_repeat_count_range="[true, 8, 8, 1]",
        ),
    )
    type2_spec = load_type2_step_spec(source_toml)
    rx_modeled_spec = next(entry for entry in type2_spec.modeled_objects if entry.object_id == "rx_rect_void_coil")
    assert rx_modeled_spec.role == "rx_single_coil"
    ledger = export_type2_step_artifacts(
        toml_path=source_toml,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    rx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "rx_rect_void_coil")
    rx_region_member = next(
        member for member in ledger["non_model_objects"][0]["member_objects"] if member["object_id"] == "rx_region_max"
    )
    rx_min_xyz = rx_entry["canonical_coordinates"]["outer_bounds_min_xyz"]
    assert isinstance(rx_min_xyz, tuple)
    rx_min_x, rx_min_y, rx_min_z = cast(tuple[float, float, float], rx_min_xyz)
    region_min_x, _, _ = rx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    rx_region_size_x = cast(tuple[float, float, float], rx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"])[0]
    underlay_repeat_count = resolve_modeled_underlay_repeat_count(cast(ModeledSingleCoilSpec, rx_modeled_spec), seed=0)
    assert underlay_repeat_count == 8
    expected_names = _rx_expected_body_names(underlay_repeat_count=8)

    assert rx_entry["plane"] == "YZ"
    assert rx_entry["placement_owner_id"] == "rx_region_max"
    assert tuple(rx_entry["expected_exported_body_names"]) == expected_names
    assert rx_entry["expected_exported_body_count"] == len(expected_names)
    assert _normalized_body_groups(rx_entry["expected_exported_body_groups"]) == _normalized_body_groups(
        _rx_expected_body_groups(underlay_repeat_count=underlay_repeat_count)
    )
    assert rx_min_x >= region_min_x
    rx_step_min_xyz, rx_step_max_xyz = _body_bbox(Path(ledger["scene_step_path"]), label="rx_copper_l0")
    assert rx_step_min_xyz[0] == pytest.approx(rx_min_x)
    assert rx_step_max_xyz[0] > rx_step_min_xyz[0]
    assert rx_step_max_xyz[1] > rx_step_min_xyz[1]
    assert rx_step_max_xyz[2] > rx_min_z
    _assert_rx_full_backing_contract(
        scene_shapes_by_label=_step_shapes_by_label(Path(ledger["scene_step_path"])),
        rx_region_size_x=rx_region_size_x,
    )


@pytest.mark.parametrize(
    ("modeled_role", "region_id", "object_id", "prefix"),
    (("tx_plate_stack", "tx_region", "tx_plate_stack", "tx"), ("rx_plate_stack", "rx_region_max", "rx_plate_stack", "rx")),
)
def test_export_type2_step_artifacts_uses_global_centered_y_window_for_plate_stack(
    tmp_path: Path,
    modeled_role: Literal["tx_plate_stack", "rx_plate_stack"],
    region_id: Literal["tx_region", "rx_region_max"],
    object_id: Literal["tx_plate_stack", "rx_plate_stack"],
    prefix: Literal["tx", "rx"],
) -> None:
    y_usage_ratio_range = _range(False, 0.5, 0.5, 1)
    toml_path = _write_spec(
        tmp_path,
        _type2_tx_plate_stack_spec_text(
            y_usage_ratio_range=y_usage_ratio_range,
        )
        if modeled_role == "tx_plate_stack"
        else _type2_rx_plate_stack_spec_text(y_usage_ratio_range=y_usage_ratio_range),
    )

    type2_spec = load_type2_step_spec(toml_path)
    modeled_spec = next(entry for entry in type2_spec.modeled_objects if entry.object_id == object_id)
    assert modeled_spec.role == modeled_role
    plate_stack_spec = cast(ModeledPlateStackSpec, modeled_spec)
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    modeled_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == object_id)
    region_member = next(
        member
        for member in ledger["non_model_objects"][0]["member_objects"]
        if member["object_id"] == region_id
    )
    region_min_x, _region_min_y, region_min_z = region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    _region_size_x, region_size_y, region_size_z = region_member["canonical_coordinates"]["outer_bounds_size_xyz"]
    y_usage_ratio = resolve_modeled_plate_stack_y_usage_ratio(plate_stack_spec, seed=0)
    z_usage_ratio = resolve_modeled_plate_stack_z_usage_ratio(plate_stack_spec, seed=0)
    fill_factor = resolve_modeled_plate_stack_metal_fill_factor(plate_stack_spec, seed=0)
    active_min_y, active_max_y, active_size_y = _plate_stack_active_y_bounds(
        owner_size_y=region_size_y,
        y_usage_ratio=y_usage_ratio,
    )
    _, active_max_z, active_size_z = _plate_stack_active_z_bounds(
        role=modeled_role,
        owner_origin_z=region_min_z,
        owner_size_z=region_size_z,
        z_usage_ratio=z_usage_ratio,
    )
    active_min_z = active_max_z - active_size_z
    turn_count = resolve_modeled_plate_stack_turn_count(plate_stack_spec, seed=0)
    expected_total_thickness_mm = total_plate_stack_thickness_mm(spec=plate_stack_spec)
    pitch_z = _plate_stack_pitch_z(owner_size_z=active_size_z, turn_count=turn_count)
    trace_height_z = pitch_z * fill_factor
    centering_offset_z = (pitch_z - trace_height_z) / 2.0

    canonical_min_xyz = cast(tuple[float, float, float], modeled_entry["canonical_coordinates"]["outer_bounds_min_xyz"])
    canonical_size_xyz = cast(
        tuple[float, float, float],
        modeled_entry["canonical_coordinates"]["outer_bounds_size_xyz"],
    )
    assert canonical_min_xyz[0] == pytest.approx(region_min_x)
    assert canonical_min_xyz[1] == pytest.approx(active_min_y - 5.0)
    assert canonical_min_xyz[2] == pytest.approx(active_min_z)
    assert canonical_size_xyz[0] == pytest.approx(expected_total_thickness_mm)
    assert canonical_size_xyz[1] == pytest.approx(active_size_y + 5.0)
    assert canonical_size_xyz[2] == pytest.approx(active_size_z)
    assert canonical_min_xyz[1] + canonical_size_xyz[1] == pytest.approx(active_max_y)
    assert canonical_min_xyz[0] + canonical_size_xyz[0] == pytest.approx(region_min_x + expected_total_thickness_mm)

    step_min_xyz, step_max_xyz = _body_bbox(Path(ledger["scene_step_path"]), label=f"{prefix}_plate_copper")
    assert step_min_xyz[0] == pytest.approx(region_min_x)
    assert step_max_xyz[0] == pytest.approx(region_min_x + expected_total_thickness_mm)
    assert step_min_xyz[1] == pytest.approx(active_min_y - 5.0)
    assert step_max_xyz[1] == pytest.approx(active_max_y)
    assert step_min_xyz[2] >= active_min_z + centering_offset_z - 1e-8
    assert step_max_xyz[2] <= active_max_z - centering_offset_z + 1e-8

    terminal_metadata = cast(dict[str, object], modeled_entry["terminal_metadata"])
    start_point_plane = cast(list[float], terminal_metadata["start_point_plane_mm"])
    end_point_plane = cast(list[float], terminal_metadata["end_point_plane_mm"])
    assert start_point_plane[0] == pytest.approx(active_min_y - 5.0)
    assert end_point_plane[0] == pytest.approx(active_min_y - 5.0)

    assert start_point_plane[0] == end_point_plane[0]

    port_sheet_vertices = cast(
        list[list[float]],
        terminal_metadata["port_sheet_vertices_xyz"],
    )
    assert all(round(vertex[1], 8) == round(active_min_y - 5.0, 8) for vertex in port_sheet_vertices)


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


def test_export_type2_step_artifacts_reuses_first_pass_scene_data_for_terminal_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import peetsfea.type2_step_export as module_under_test

    repo_root = Path(__file__).resolve().parents[2]
    toml_path = repo_root / "examples" / "type2_fixed.toml"
    spec = load_type2_step_spec(toml_path)
    modeled_object_ids = tuple(modeled_spec.object_id for modeled_spec in spec.modeled_objects)
    build_calls: list[str] = []
    original_build_modeled_scene_data = module_under_test.build_modeled_scene_data

    def _counting_build_modeled_scene_data(
        modeled_spec: ModeledSingleCoilSpec,
        *,
        owner_spec: NonModelBoxSpec,
        tx_region_max_z: float,
        seed: int,
    ) -> object:
        build_calls.append(modeled_spec.object_id)
        return original_build_modeled_scene_data(
            modeled_spec,
            owner_spec=owner_spec,
            tx_region_max_z=tx_region_max_z,
            seed=seed,
        )

    def _successful_export_step(*args: object, **kwargs: object) -> bool:
        return True

    monkeypatch.setattr(module_under_test, "build_modeled_scene_data", _counting_build_modeled_scene_data)
    monkeypatch.setattr(module_under_test.bd, "export_step", _successful_export_step)

    module_under_test.export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    assert tuple(build_calls) == modeled_object_ids


def test_export_type2_step_artifacts_fails_terminal_metadata_drift_against_first_pass_scene_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import peetsfea.type2_step_export as module_under_test

    toml_path = _write_spec(
        tmp_path,
        _type2_spec_text(
            modeled_object_id="rx_rect_void_coil",
            modeled_role="rx_single_coil",
        ),
    )
    original_build_modeled_scene_data = module_under_test.build_modeled_scene_data
    original_build_type2_step_ledger = module_under_test.build_type2_step_ledger
    build_call_index = 0

    def _tagged_build_modeled_scene_data(
        modeled_spec: ModeledSingleCoilSpec,
        *,
        owner_spec: NonModelBoxSpec,
        tx_region_max_z: float,
        seed: int,
    ) -> object:
        nonlocal build_call_index
        build_call_index += 1
        scene_shapes, scene_data = original_build_modeled_scene_data(
            modeled_spec,
            owner_spec=owner_spec,
            tx_region_max_z=tx_region_max_z,
            seed=seed,
        )
        tagged_scene_data = dict(scene_data)
        terminal_metadata = dict(cast(dict[str, object], tagged_scene_data["terminal_metadata"]))
        terminal_metadata["same_call_scene_data_probe"] = f"call_{build_call_index}"
        tagged_scene_data["terminal_metadata"] = terminal_metadata
        return scene_shapes, tagged_scene_data

    def _drifted_build_type2_step_ledger(*args: object, **kwargs: object) -> object:
        ledger = original_build_type2_step_ledger(*args, **kwargs)
        modeled_entry = ledger["modeled_objects"][0]
        terminal_metadata = dict(cast(dict[str, object], modeled_entry["terminal_metadata"]))
        terminal_metadata["same_call_scene_data_probe"] = "call_2"
        modeled_entry["terminal_metadata"] = terminal_metadata
        return ledger

    def _successful_export_step(*args: object, **kwargs: object) -> bool:
        return True

    monkeypatch.setattr(module_under_test, "build_modeled_scene_data", _tagged_build_modeled_scene_data)
    monkeypatch.setattr(module_under_test, "build_type2_step_ledger", _drifted_build_type2_step_ledger)
    monkeypatch.setattr(module_under_test.bd, "export_step", _successful_export_step)

    with pytest.raises(RuntimeError, match=r"type2 port sheet metadata must match modeled scene construction contract"):
        module_under_test.export_type2_step_artifacts(
            toml_path=toml_path,
            output_dir=tmp_path / "out",
            ledger_path=tmp_path / "out" / "ledger.json",
            seed=0,
        )

    assert build_call_index == 1


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

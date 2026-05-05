from __future__ import annotations

from typing import Literal, cast

from peetsfea.spec.loader import TOMLTable
from peetsfea.types.manifest import SelectedParameters, SelectedParametersMax

from ..constraints.path_access import parse_string_value_at_path, parse_string_value_by_validator_at_path
from ..types import Number


def _validate_neo_tx_dd_terminal_path_contract(value: str) -> None:
    parts = value.split("_")
    if len(parts) != 4 or parts[2] != "to":
        raise ValueError(
            "coil_placement.neo_tx_dd terminal path must match '<start>_<cw|ccw>_to_<end>'"
        )
    start_label = parts[0]
    direction = parts[1]
    end_label = parts[3]
    if len(start_label) != 1 or len(end_label) != 1:
        raise ValueError("coil_placement.neo_tx_dd terminal path terminals must be single letters")
    if start_label not in {"A", "B", "C", "D", "a", "b", "c", "d"}:
        raise ValueError("coil_placement.neo_tx_dd terminal path start terminal is unsupported")
    if end_label not in {"A", "B", "C", "D", "a", "b", "c", "d"}:
        raise ValueError("coil_placement.neo_tx_dd terminal path end terminal is unsupported")
    if direction not in {"cw", "ccw"}:
        raise ValueError("coil_placement.neo_tx_dd terminal path direction must be 'cw' or 'ccw'")
    if start_label.isupper() == end_label.isupper():
        raise ValueError("coil_placement.neo_tx_dd terminal path must use one uppercase and one lowercase terminal")


def _validate_neo_tx_vertical_terminal_path_contract(value: str) -> None:
    parts = value.split("_")
    if len(parts) != 4 or parts[2] != "to":
        raise ValueError(
            "coil_placement.neo_tx_vertical terminal path must match '<start>_<cw|ccw>_to_<end>'"
        )
    start_label = parts[0]
    direction = parts[1]
    end_label = parts[3]
    if len(start_label) != 1 or len(end_label) != 1:
        raise ValueError("coil_placement.neo_tx_vertical terminal path terminals must be single letters")
    if start_label not in {"A", "B", "C", "D", "a", "b", "c", "d"}:
        raise ValueError("coil_placement.neo_tx_vertical terminal path start terminal is unsupported")
    if end_label not in {"A", "B", "C", "D", "a", "b", "c", "d"}:
        raise ValueError("coil_placement.neo_tx_vertical terminal path end terminal is unsupported")
    if direction not in {"cw", "ccw"}:
        raise ValueError("coil_placement.neo_tx_vertical terminal path direction must be 'cw' or 'ccw'")
    if start_label.isupper() == end_label.isupper():
        raise ValueError("coil_placement.neo_tx_vertical terminal path must use one uppercase and one lowercase terminal")


def _build_selected_parameters(spec: TOMLTable, raw: dict[str, Number]) -> SelectedParameters:
    ferrite_present = int(raw["ferrite_present"])
    if ferrite_present not in (0, 1):
        raise ValueError("ferrite.present must resolve to 0 or 1")
    rx_ferrite_thickness_mm = float(raw["rx_ferrite_thickness_mm"])
    tx_ferrite_thickness_mm = float(raw["tx_ferrite_thickness_mm"])
    tx_ferrite_gap_mm = float(raw["tx_ferrite_gap_mm"])
    ferrite_relative_permeability = float(raw["ferrite_relative_permeability"])
    pcb_thickness_mm = float(raw["pcb_thickness_mm"])
    rx_region_thickness_mm = float(raw["rx_region_thickness_mm"])
    tx_region_dd_z_mm = float(raw["tx_region_dd_z_mm"])
    corner_mode = int(raw["corner_mode"])
    tx_dd_top_offset_ratio = float(raw["tx_dd_top_offset_ratio"])
    tx_vertical_orientation_mode = int(raw["tx_vertical_orientation_mode"])
    if rx_ferrite_thickness_mm <= 0.0:
        raise ValueError("ferrite.rx_thickness_mm must be > 0")
    if tx_ferrite_thickness_mm <= 0.0:
        raise ValueError("ferrite.tx_thickness_mm must be > 0")
    if tx_ferrite_gap_mm <= 0.0:
        raise ValueError("ferrite.tx_gap_mm must be > 0")
    if ferrite_relative_permeability <= 1.0:
        raise ValueError("ferrite.relative_permeability must be > 1")
    if corner_mode not in (0, 1):
        raise ValueError("coil_shape.corner_mode must resolve to 0 or 1")
    if tx_vertical_orientation_mode not in (0, 1):
        raise ValueError("coil_placement.tx_vertical_orientation_mode must resolve to 0 or 1")
    if (rx_ferrite_thickness_mm + pcb_thickness_mm) > (rx_region_thickness_mm + 1e-9):
        raise ValueError("ferrite.rx_thickness_mm + coil_material.pcb_thickness_mm must be <= rx.region.thickness_mm")
    tx_vertical_plane: Literal["ZX"] = "ZX"
    return {
        "tx_dd_outer_x": float(raw["tx_dd_outer_x"]),
        "tx_dd_outer_y": float(raw["tx_dd_outer_y"]),
        "tx_vertical_outer_x": float(raw["tx_vertical_outer_x"]),
        "tx_vertical_outer_y": float(raw["tx_vertical_outer_y"]),
        "rx_dd_outer_x": float(raw["rx_dd_outer_x"]),
        "rx_dd_outer_y": float(raw["rx_dd_outer_y"]),
        "corner_mode": corner_mode,
        "tx_dd_pair_spacing_ratio": float(raw["tx_dd_pair_spacing_ratio"]),
        "rx_dd_pair_spacing_ratio": float(raw["rx_dd_pair_spacing_ratio"]),
        "tx_vertical_center_gap_mm": float(raw["tx_vertical_center_gap_mm"]),
        "tx_dd_pair_spacing_mm": float(raw["tx_dd_pair_spacing_ratio"]) * float(raw["tx_region_outer_h_mm"]),
        "rx_dd_pair_spacing_mm": float(raw["rx_dd_pair_spacing_ratio"]) * float(raw["rx_region_outer_h_mm"]),
        "tx_vertical_span_mm": 0.0,
        "tv_width_mm": float(raw["tv_width_mm"]),
        "tv_height_mm": float(raw["tv_height_mm"]),
        "tv_thickness_mm": float(raw["tv_thickness_mm"]),
        "tv_base_z_mm": float(raw["tv_base_z_mm"]),
        "tx_region_outer_w_mm": float(raw["tx_region_outer_w_mm"]),
        "tx_region_outer_h_mm": float(raw["tx_region_outer_h_mm"]),
        "tx_region_thickness_mm": float(raw["tx_region_thickness_mm"]),
        "tx_region_vertical_z_mm": float(raw["tx_region_vertical_z_mm"]),
        "tx_region_dd_z_mm": tx_region_dd_z_mm,
        "rx_region_outer_w_mm": float(raw["rx_region_outer_w_mm"]),
        "rx_region_outer_h_mm": float(raw["rx_region_outer_h_mm"]),
        "rx_region_thickness_mm": float(raw["rx_region_thickness_mm"]),
        "wall_thickness_mm": float(raw["wall_thickness_mm"]),
        "wall_size_y_mm": float(raw["wall_size_y_mm"]),
        "wall_size_z_mm": float(raw["wall_size_z_mm"]),
        "floor_thickness_mm": float(raw["floor_thickness_mm"]),
        "floor_size_x_mm": float(raw["floor_size_x_mm"]),
        "floor_size_y_mm": float(raw["floor_size_y_mm"]),
        "ferrite_present": ferrite_present == 1,
        "rx_ferrite_thickness_mm": rx_ferrite_thickness_mm,
        "tx_ferrite_thickness_mm": tx_ferrite_thickness_mm,
        "tx_ferrite_gap_mm": tx_ferrite_gap_mm,
        "ferrite_relative_permeability": ferrite_relative_permeability,
        "shelf_height_mm": float(raw["shelf_height_mm"]),
        "shelf_min_size_x_mm": float(raw["shelf_min_size_x_mm"]),
        "rx_region_bottom_from_tv_mm": float(raw["rx_region_bottom_from_tv_mm"]),
        "tx_dd_top_offset_ratio": tx_dd_top_offset_ratio,
        "tx_dd_top_clearance_mm": tx_dd_top_offset_ratio * tx_region_dd_z_mm,
        "tx_vertical_orientation_mode": cast(Literal[0, 1], tx_vertical_orientation_mode),
        "rx_face_clearance_mm": float(raw["rx_face_clearance_mm"]),
        "tx_main_1_z_from_tx_main_0_mm": float(raw["tx_main_1_z_from_tx_main_0_mm"]),
        "dd_mirror_plane": cast(Literal["XZ"], parse_string_value_at_path(spec, "coil_placement.dd_mirror_plane", allowed={"XZ"})),
        "rx_plane": cast(Literal["YZ"], parse_string_value_at_path(spec, "coil_placement.rx_plane", allowed={"YZ"})),
        "neo_tx_dd_right_terminal_path": parse_string_value_by_validator_at_path(
            spec,
            "coil_placement.neo_tx_dd_right_terminal_path",
            validator=_validate_neo_tx_dd_terminal_path_contract,
        ),
        "neo_tx_dd_left_terminal_path": parse_string_value_by_validator_at_path(
            spec,
            "coil_placement.neo_tx_dd_left_terminal_path",
            validator=_validate_neo_tx_dd_terminal_path_contract,
        ),
        "neo_tx_vertical_zx_terminal_path": parse_string_value_by_validator_at_path(
            spec,
            "coil_placement.neo_tx_vertical_zx_terminal_path",
            validator=_validate_neo_tx_vertical_terminal_path_contract,
        ),
        "tx_vertical_plane": tx_vertical_plane,
        "via_diameter_mm": float(raw["via_diameter_mm"]),
        "pcb_thickness_mm": pcb_thickness_mm,
        "cu_thickness_mm": float(raw["cu_thickness_mm"]),
        "via_diameter": float(raw["via_diameter_mm"]),
        "pcb_thickness": float(raw["pcb_thickness_mm"]),
        "cu_thickness": float(raw["cu_thickness_mm"]),
        "fr4_er": float(raw["fr4_er"]),
    }


def _build_selected_parameters_max(raw_max: dict[str, Number]) -> SelectedParametersMax:
    return {
        "tx_region_outer_w_mm": float(raw_max["tx_region_outer_w_mm"]),
        "tx_region_outer_h_mm": float(raw_max["tx_region_outer_h_mm"]),
        "tx_region_thickness_mm": float(raw_max["tx_region_thickness_mm"]),
        "tx_region_vertical_z_mm": float(raw_max["tx_region_vertical_z_mm"]),
        "tx_region_dd_z_mm": float(raw_max["tx_region_dd_z_mm"]),
        "rx_region_outer_w_mm": float(raw_max["rx_region_outer_w_mm"]),
        "rx_region_outer_h_mm": float(raw_max["rx_region_outer_h_mm"]),
        "rx_region_thickness_mm": float(raw_max["rx_region_thickness_mm"]),
    }


__all__ = ["_build_selected_parameters", "_build_selected_parameters_max"]

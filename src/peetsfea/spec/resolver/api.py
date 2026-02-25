from __future__ import annotations

from typing import Literal, cast

from peetsfea.spec.loader import TOMLTable
from peetsfea.types.manifest import (
    GroupGeometryParams,
    ResolvedCoilGroup,
    ResolvedPcbInstance,
    SelectedParameters,
    SelectedParametersMax,
)

from .coil_groups import resolve_coil_groups
from .constants import SCALAR_OFFSET, SCALAR_RANGE_SPECS
from .constraints_eval import validate_constraints
from .group_geometry import resolve_group_geometry
from .path_access import parse_string_value_at_path, reject_removed_paths
from .pcbs import normalize_pcbs_fixed_topology, resolve_pcbs
from .sampling import select_range_end_value, select_range_value
from .types import Number, SamplingContext


def resolve_selected_scalars(spec: TOMLTable, seed: int, attempt: int, context: SamplingContext) -> dict[str, Number]:
    selected: dict[str, Number] = {}
    for path, key, expect_integer in SCALAR_RANGE_SPECS:
        selected[key] = select_range_value(
            spec, path, expect_integer=expect_integer, seed=seed, offset=SCALAR_OFFSET[path], attempt=attempt, context=context
        )
    return selected


def resolve_selected_max_scalars(spec: TOMLTable) -> dict[str, Number]:
    selected: dict[str, Number] = {}
    for path, key, expect_integer in SCALAR_RANGE_SPECS:
        selected[key] = select_range_end_value(spec, path, expect_integer=expect_integer)
    return selected


def _resolve_selection(
    spec: TOMLTable, seed: int, attempt: int = 0
) -> tuple[SelectedParameters, SelectedParametersMax, list[ResolvedCoilGroup], list[GroupGeometryParams], list[ResolvedPcbInstance]]:
    reject_removed_paths(spec)
    context: SamplingContext = {}
    raw = resolve_selected_scalars(spec, seed, attempt, context)
    raw_max = resolve_selected_max_scalars(spec)
    dd_mirror_plane = parse_string_value_at_path(spec, "coil_placement.dd_mirror_plane", allowed={"XZ"})
    rx_plane = parse_string_value_at_path(spec, "coil_placement.rx_plane", allowed={"YZ"})
    tx_vertical_plane = parse_string_value_at_path(spec, "coil_placement.tx_vertical_plane", allowed={"ZX"})

    selected: SelectedParameters = {
        "tx_dd_outer_x": float(raw["tx_dd_outer_x"]),
        "tx_dd_outer_y": float(raw["tx_dd_outer_y"]),
        "tx_vertical_outer_x": float(raw["tx_vertical_outer_x"]),
        "tx_vertical_outer_y": float(raw["tx_vertical_outer_y"]),
        "rx_dd_outer_x": float(raw["rx_dd_outer_x"]),
        "rx_dd_outer_y": float(raw["rx_dd_outer_y"]),
        "inner_margin_x": float(raw["inner_margin_x"]),
        "inner_margin_y": float(raw["inner_margin_y"]),
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
        "tx_region_dd_z_mm": float(raw["tx_region_dd_z_mm"]),
        "rx_region_outer_w_mm": float(raw["rx_region_outer_w_mm"]),
        "rx_region_outer_h_mm": float(raw["rx_region_outer_h_mm"]),
        "rx_region_thickness_mm": float(raw["rx_region_thickness_mm"]),
        "wall_thickness_mm": float(raw["wall_thickness_mm"]),
        "wall_size_y_mm": float(raw["wall_size_y_mm"]),
        "wall_size_z_mm": float(raw["wall_size_z_mm"]),
        "floor_thickness_mm": float(raw["floor_thickness_mm"]),
        "floor_size_x_mm": float(raw["floor_size_x_mm"]),
        "floor_size_y_mm": float(raw["floor_size_y_mm"]),
        "shelf_height_mm": float(raw["shelf_height_mm"]),
        "shelf_min_size_x_mm": float(raw["shelf_min_size_x_mm"]),
        "rx_region_bottom_from_tv_mm": float(raw["rx_region_bottom_from_tv_mm"]),
        "tx_dd_top_clearance_mm": float(raw["tx_dd_top_clearance_mm"]),
        "rx_face_clearance_mm": float(raw["rx_face_clearance_mm"]),
        "tx_main_1_z_from_tx_main_0_mm": float(raw["tx_main_1_z_from_tx_main_0_mm"]),
        "dd_mirror_plane": cast(Literal["XZ"], dd_mirror_plane),
        "rx_plane": cast(Literal["YZ"], rx_plane),
        "tx_vertical_plane": cast(Literal["ZX"], tx_vertical_plane),
        "via_diameter_mm": float(raw["via_diameter_mm"]),
        "pcb_thickness_mm": float(raw["pcb_thickness_mm"]),
        "cu_thickness_mm": float(raw["cu_thickness_mm"]),
        "via_diameter": float(raw["via_diameter_mm"]),
        "pcb_thickness": float(raw["pcb_thickness_mm"]),
        "cu_thickness": float(raw["cu_thickness_mm"]),
        "fr4_er": float(raw["fr4_er"]),
    }
    selected_max: SelectedParametersMax = {
        "tx_region_outer_w_mm": float(raw_max["tx_region_outer_w_mm"]),
        "tx_region_outer_h_mm": float(raw_max["tx_region_outer_h_mm"]),
        "tx_region_thickness_mm": float(raw_max["tx_region_thickness_mm"]),
        "tx_region_vertical_z_mm": float(raw_max["tx_region_vertical_z_mm"]),
        "tx_region_dd_z_mm": float(raw_max["tx_region_dd_z_mm"]),
        "rx_region_outer_w_mm": float(raw_max["rx_region_outer_w_mm"]),
        "rx_region_outer_h_mm": float(raw_max["rx_region_outer_h_mm"]),
        "rx_region_thickness_mm": float(raw_max["rx_region_thickness_mm"]),
    }
    groups = resolve_coil_groups(spec, seed, attempt, selected, context)
    group_geometry = resolve_group_geometry(spec, seed, attempt, context, selected)
    pcbs = resolve_pcbs(spec, seed, attempt, context)
    pcbs = normalize_pcbs_fixed_topology(pcbs)
    validate_constraints(spec, selected, groups, group_geometry, pcbs)
    return selected, selected_max, groups, group_geometry, pcbs


def resolve_selected_parameters(spec: TOMLTable, seed: int, attempt: int = 0) -> SelectedParameters:
    selected, _, _, _, _ = _resolve_selection(spec, seed, attempt)
    return selected


def resolve_selection(
    spec: TOMLTable, seed: int, attempt: int = 0
) -> tuple[SelectedParameters, SelectedParametersMax, list[ResolvedCoilGroup], list[GroupGeometryParams], list[ResolvedPcbInstance]]:
    return _resolve_selection(spec, seed, attempt)

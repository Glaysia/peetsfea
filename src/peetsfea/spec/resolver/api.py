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
from .sampling import SamplingLedger, build_sampling_registry, preflight_sampling_spec, select_range_end_value, select_range_value
from .types import Number, SamplingContext, SelectionResult


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
    tx_dd_top_clearance_ratio = float(raw["tx_dd_top_clearance_ratio"])
    if rx_ferrite_thickness_mm <= 0.0:
        raise ValueError("ferrite.rx_thickness_mm must be > 0")
    if tx_ferrite_thickness_mm <= 0.0:
        raise ValueError("ferrite.tx_thickness_mm must be > 0")
    if tx_ferrite_gap_mm <= 0.0:
        raise ValueError("ferrite.tx_gap_mm must be > 0")
    if ferrite_relative_permeability <= 1.0:
        raise ValueError("ferrite.relative_permeability must be > 1")
    if (rx_ferrite_thickness_mm + pcb_thickness_mm) > (rx_region_thickness_mm + 1e-9):
        raise ValueError("ferrite.rx_thickness_mm + coil_material.pcb_thickness_mm must be <= rx.region.thickness_mm")
    return {
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
        "tx_dd_top_clearance_ratio": tx_dd_top_clearance_ratio,
        "tx_dd_top_clearance_mm": tx_dd_top_clearance_ratio * tx_region_dd_z_mm,
        "rx_face_clearance_mm": float(raw["rx_face_clearance_mm"]),
        "tx_main_1_z_from_tx_main_0_mm": float(raw["tx_main_1_z_from_tx_main_0_mm"]),
        "dd_mirror_plane": cast(Literal["XZ"], parse_string_value_at_path(spec, "coil_placement.dd_mirror_plane", allowed={"XZ"})),
        "rx_plane": cast(Literal["YZ"], parse_string_value_at_path(spec, "coil_placement.rx_plane", allowed={"YZ"})),
        "tx_vertical_plane": cast(
            Literal["ZX"], parse_string_value_at_path(spec, "coil_placement.tx_vertical_plane", allowed={"ZX"})
        ),
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


def resolve_selection_result(spec: TOMLTable, seed: int, attempt: int = 0) -> SelectionResult:
    reject_removed_paths(spec)
    registry = build_sampling_registry(spec)
    preflight_sampling_spec(spec, registry)
    context = SamplingLedger(registry)
    raw = resolve_selected_scalars(spec, seed, attempt, context)
    raw_max = resolve_selected_max_scalars(spec)
    selected = _build_selected_parameters(spec, raw)
    selected_max = _build_selected_parameters_max(raw_max)
    groups = resolve_coil_groups(spec, seed, attempt, selected, context)
    group_geometry = resolve_group_geometry(spec, seed, attempt, context, selected)
    pcbs = resolve_pcbs(spec, seed, attempt, context)
    pcbs = normalize_pcbs_fixed_topology(pcbs)
    validate_constraints(spec, selected, groups, group_geometry, pcbs)
    return SelectionResult(
        selected_parameters=selected,
        selected_parameters_max=selected_max,
        selected_coil_groups=groups,
        selected_group_geometry=group_geometry,
        selected_pcbs=pcbs,
        sampling_ledger=context,
    )


def resolve_selected_parameters(spec: TOMLTable, seed: int, attempt: int = 0) -> SelectedParameters:
    return resolve_selection_result(spec, seed, attempt).selected_parameters


def resolve_selection(
    spec: TOMLTable, seed: int, attempt: int = 0
) -> tuple[SelectedParameters, SelectedParametersMax, list[ResolvedCoilGroup], list[GroupGeometryParams], list[ResolvedPcbInstance]]:
    result = resolve_selection_result(spec, seed, attempt)
    return (
        result.selected_parameters,
        result.selected_parameters_max,
        result.selected_coil_groups,
        result.selected_group_geometry,
        result.selected_pcbs,
    )


def resolve_selection_with_context(
    spec: TOMLTable, seed: int, attempt: int = 0
) -> tuple[
    SelectedParameters,
    SelectedParametersMax,
    list[ResolvedCoilGroup],
    list[GroupGeometryParams],
    list[ResolvedPcbInstance],
    SamplingContext,
]:
    result = resolve_selection_result(spec, seed, attempt)
    return (
        result.selected_parameters,
        result.selected_parameters_max,
        result.selected_coil_groups,
        result.selected_group_geometry,
        result.selected_pcbs,
        result.sampling_ledger.as_dict(),
    )

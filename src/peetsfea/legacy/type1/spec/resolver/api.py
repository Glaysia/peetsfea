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

from .constraints.constraints_eval import validate_constraints
from .constants import SCALAR_OFFSET, SCALAR_RANGE_SPECS
from .constraints.path_access import reject_removed_paths
from .domains.coil_groups import resolve_coil_groups
from .domains.group_geometry import resolve_group_geometry
from .domains.pcbs import normalize_pcbs_fixed_topology, resolve_pcbs
from .domains.selected_parameters import _build_selected_parameters, _build_selected_parameters_max
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


def resolve_selection_result(spec: TOMLTable, seed: int, attempt: int = 0) -> SelectionResult:
    reject_removed_paths(spec)
    registry = build_sampling_registry(spec)
    preflight_sampling_spec(spec, registry)
    context = SamplingLedger(registry, seed=seed, attempt=attempt)
    raw = resolve_selected_scalars(spec, seed, attempt, context)
    raw_max = resolve_selected_max_scalars(spec)
    selected = _build_selected_parameters(spec, raw)
    selected_max = _build_selected_parameters_max(raw_max)
    groups = resolve_coil_groups(spec, seed, attempt, selected, context)
    group_geometry = resolve_group_geometry(spec, seed, attempt, context, selected)
    pcbs = resolve_pcbs(spec, seed, attempt, context)
    pcbs = normalize_pcbs_fixed_topology(pcbs, groups)
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

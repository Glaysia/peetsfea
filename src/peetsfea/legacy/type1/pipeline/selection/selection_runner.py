from __future__ import annotations

from peetsfea.spec.loader import TOMLTable
from peetsfea.legacy.type1.spec.resolver import SelectionConstraintError, resolve_selection_result
from peetsfea.legacy.type1.spec.resolver.sampling import SamplingLedger
from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance, SelectedParameters, SelectedParametersMax

MAX_ATTEMPTS = 64


def _select_feasible_result(
    spec: TOMLTable,
    *,
    seed: int,
) -> tuple[
    SelectedParameters,
    SelectedParametersMax,
    list[ResolvedCoilGroup],
    list[GroupGeometryParams],
    list[ResolvedPcbInstance],
    SamplingLedger,
    int,
    int,
]:
    last_error = ""
    for attempt in range(MAX_ATTEMPTS):
        try:
            result = resolve_selection_result(spec=spec, seed=seed, attempt=attempt)
            return (
                result.selected_parameters,
                result.selected_parameters_max,
                result.selected_coil_groups,
                result.selected_group_geometry,
                result.selected_pcbs,
                result.sampling_ledger,
                attempt,
                attempt,
            )
        except SelectionConstraintError as exc:
            last_error = str(exc)
            continue
    raise RuntimeError(
        "No valid selection within max attempts "
        f"(seed={seed}, max_attempts={MAX_ATTEMPTS}, last_error={last_error})"
    )


__all__ = ["MAX_ATTEMPTS", "_select_feasible_result"]

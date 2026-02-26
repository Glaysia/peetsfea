from __future__ import annotations

from typing import TypedDict

from peetsfea.types.manifest import EmContext, EmEndpoints, EmPolicy, EmReadyObjects, PostTemplateResult


class EmPipelineInput(TypedDict):
    ready_objects: EmReadyObjects
    endpoints: EmEndpoints
    context: EmContext


class EmPipelineResult(TypedDict):
    groups: dict[str, list[str]]
    series: dict[str, list[str]]
    subtract: dict[str, list[str]]
    boundary: dict[str, str]
    ports: dict[str, list[str]]
    analysis: dict[str, float | str]
    post_templates: list[PostTemplateResult]
    validation_report: dict[str, str | bool]


def default_em_policy() -> EmPolicy:
    return {
        "radiation_margin_mm": 3500.0,
        "setup_frequency_hz": 6.78e6,
        "sweep_start_hz": 1.0e6,
        "sweep_stop_hz": 45.0e6,
        "validation_gate": "hard_fail",
        "max_delta_s": 0.001,
        "maximum_passes": 35,
        "minimum_passes": 9,
        "minimum_converged_passes": 13,
        "percent_refinement": 65,
        "basis_order": 1,
        "port_accuracy": 2,
    }

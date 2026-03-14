from __future__ import annotations

from typing import TypedDict

from peetsfea.types.manifest import OutputVariableSpec, OutputsSpec


class PostTemplateDefinition(TypedDict):
    template_id: str
    report_name: str
    solution_name: str
    primary_sweep: str
    report_category: str
    plot_type: str
    variations: dict[str, list[str]]
    traces: list[str]
    output_variables: list[OutputVariableSpec]


def build_post_template(outputs: OutputsSpec) -> PostTemplateDefinition:
    traces = [entry["name"] for entry in outputs["variables"]]
    return {
        "template_id": "output_variables_table_1",
        "report_name": outputs["report_name"],
        "solution_name": outputs["solution_name"],
        "primary_sweep": outputs["primary_sweep"],
        "report_category": outputs["report_category"],
        "plot_type": outputs["plot_type"],
        "variations": {outputs["primary_sweep"]: ["All"]},
        "traces": traces,
        "output_variables": list(outputs["variables"]),
    }

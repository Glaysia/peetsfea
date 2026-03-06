from __future__ import annotations

from typing import Final, TypedDict


class OutputVariableDefinition(TypedDict):
    name: str
    expression: str


class PostTemplateDefinition(TypedDict):
    template_id: str
    report_name: str
    solution_name: str
    primary_sweep: str
    report_category: str
    plot_type: str
    f0_hz: float
    variations: dict[str, list[str]]
    traces: list[str]
    output_variables: list[OutputVariableDefinition]


OUTPUT_VARIABLES_TABLE_1: Final[PostTemplateDefinition] = {
    "template_id": "output_variables_table_1",
    "report_name": "Output Variables Table1",
    "solution_name": "Setup1 : LastAdaptive",
    "primary_sweep": "Freq",
    "report_category": "Terminal Solution Data",
    "plot_type": "Data Table",
    "f0_hz": 6.78e6,
    "variations": {"Freq": ["All"]},
    "traces": [
        "Ltx",
        "Lrx",
        "M",
        "k",
        "Qtx",
        "Qrx",
        "FOM",
    ],
    "output_variables": [
        {"name": "Ltx", "expression": "im(Zt(TX_TML,TX_TML))/2/pi/freq*1e6"},
        {"name": "Lrx", "expression": "im(Zt(RX_TML,RX_TML))/2/pi/freq*1e6"},
        {"name": "M", "expression": "abs(im(Zt(TX_TML,RX_TML))/2/pi/freq*1e6)"},
        {"name": "k", "expression": "M/sqrt(Ltx*Lrx)"},
        {"name": "Qtx", "expression": "im(Zt(TX_TML,TX_TML))/re(Zt(TX_TML,TX_TML))"},
        {"name": "Qrx", "expression": "im(Zt(RX_TML,RX_TML))/re(Zt(RX_TML,RX_TML))"},
        {"name": "FOM", "expression": "k*sqrt(Qtx*Qrx)"},
    ],
}


def default_post_templates() -> list[PostTemplateDefinition]:
    return [OUTPUT_VARIABLES_TABLE_1]

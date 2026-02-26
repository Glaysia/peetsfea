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
    "report_name": "Output Variables Table 1",
    "solution_name": "Setup1 : Sweep",
    "primary_sweep": "Freq",
    "report_category": "Output Variables",
    "plot_type": "Data Table",
    "f0_hz": 6.78e6,
    "variations": {"Freq": ["6.78MHz"]},
    "traces": [
        "Ltx",
        "Lrx",
        "M",
        "k",
        "Qtx",
        "Qrx",
        "FOM",
        "S11_mag",
        "S21_mag",
        "Z11_re",
        "Z11_im",
        "Z12_re",
        "Z12_im",
        "Z21_re",
        "Z21_im",
        "Z22_re",
        "Z22_im",
        "ImZtx",
        "ImZrx",
    ],
    "output_variables": [
        {"name": "Ltx", "expression": "im(Z(TX_TML,TX_TML))/2/pi/Freq*1e6"},
        {"name": "Lrx", "expression": "im(Z(RX_TML,RX_TML))/2/pi/Freq*1e6"},
        {"name": "M", "expression": "abs(im(Z(TX_TML,RX_TML))/2/pi/Freq*1e6)"},
        {"name": "k", "expression": "M/sqrt(Ltx*Lrx)"},
        {"name": "Qtx", "expression": "im(Z(TX_TML,TX_TML))/re(Z(TX_TML,TX_TML))"},
        {"name": "Qrx", "expression": "im(Z(RX_TML,RX_TML))/re(Z(RX_TML,RX_TML))"},
        {"name": "FOM", "expression": "k*sqrt(Qtx*Qrx)"},
        {"name": "S11_mag", "expression": "mag(S(TX_TML,TX_TML))"},
        {"name": "S21_mag", "expression": "mag(S(TX_TML,RX_TML))"},
        {"name": "Z11_re", "expression": "re(Z(TX_TML,TX_TML))"},
        {"name": "Z11_im", "expression": "im(Z(TX_TML,TX_TML))"},
        {"name": "Z12_re", "expression": "re(Z(TX_TML,RX_TML))"},
        {"name": "Z12_im", "expression": "im(Z(TX_TML,RX_TML))"},
        {"name": "Z21_re", "expression": "re(Z(RX_TML,TX_TML))"},
        {"name": "Z21_im", "expression": "im(Z(RX_TML,TX_TML))"},
        {"name": "Z22_re", "expression": "re(Z(RX_TML,RX_TML))"},
        {"name": "Z22_im", "expression": "im(Z(RX_TML,RX_TML))"},
        {"name": "ImZtx", "expression": "im(Z(TX_TML,TX_TML))"},
        {"name": "ImZrx", "expression": "im(Z(RX_TML,RX_TML))"},
    ],
}


def default_post_templates() -> list[PostTemplateDefinition]:
    return [OUTPUT_VARIABLES_TABLE_1]

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
    ],
    "output_variables": [
        {"name": "Ltx_uH", "expression": "im(Zt(TX_TML,TX_TML))/2/pi/freq*1e6"},
        {"name": "Lrx_uH", "expression": "im(Zt(RX_TML,RX_TML))/2/pi/freq*1e6"},
        {"name": "M_uH", "expression": "abs(im(Zt(TX_TML,RX_TML))/2/pi/freq*1e6)"},
        {"name": "k_ratio", "expression": "M_uH/sqrt(Ltx_uH*Lrx_uH)"},
        {"name": "Qtx_ratio", "expression": "im(Zt(TX_TML,TX_TML))/re(Zt(TX_TML,TX_TML))"},
        {"name": "Qrx_ratio", "expression": "im(Zt(RX_TML,RX_TML))/re(Zt(RX_TML,RX_TML))"},
        {"name": "FOM_ratio", "expression": "k_ratio*sqrt(Qtx_ratio*Qrx_ratio)"},
        {"name": "Rtx_ac_ohm", "expression": "re(Zt(TX_TML,TX_TML))"},
        {"name": "Rrx_ac_ohm", "expression": "re(Zt(RX_TML,RX_TML))"},
        {"name": "Xtx_ohm", "expression": "im(Zt(TX_TML,TX_TML))"},
        {"name": "Xrx_ohm", "expression": "im(Zt(RX_TML,RX_TML))"},
        {"name": "M_over_Ltx_ratio", "expression": "M_uH/Ltx_uH"},
        {"name": "M_over_Lrx_ratio", "expression": "M_uH/Lrx_uH"},
        {"name": "Gtx_S", "expression": "re(Yt(TX_TML,TX_TML))"},
        {"name": "Btx_S", "expression": "im(Yt(TX_TML,TX_TML))"},
        {"name": "Grx_S", "expression": "re(Yt(RX_TML,RX_TML))"},
        {"name": "Brx_S", "expression": "im(Yt(RX_TML,RX_TML))"},
        {"name": "S11_mag_ratio", "expression": "mag(S(TX_TML,TX_TML))"},
        {"name": "S21_mag_ratio", "expression": "mag(S(TX_TML,RX_TML))"},
        {"name": "S21_phase_deg", "expression": "ang_deg_val(S(TX_TML,RX_TML))"},
    ],
}


def default_post_templates() -> list[PostTemplateDefinition]:
    return [OUTPUT_VARIABLES_TABLE_1]

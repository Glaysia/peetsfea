from __future__ import annotations

from pathlib import Path

from peetsfea.types.manifest import OutputsSpec

TYPE1_OUTPUT_VARIABLES: tuple[tuple[str, str], ...] = (
    ("Ltx_uH", "im(Zt(TX_TML,TX_TML))/2/pi/freq*1e6"),
    ("Lrx_uH", "im(Zt(RX_TML,RX_TML))/2/pi/freq*1e6"),
    ("M_uH", "abs(im(Zt(TX_TML,RX_TML))/2/pi/freq*1e6)"),
    ("k_ratio", "M_uH/sqrt(Ltx_uH*Lrx_uH)"),
    ("Qtx_ratio", "im(Zt(TX_TML,TX_TML))/re(Zt(TX_TML,TX_TML))"),
    ("Qrx_ratio", "im(Zt(RX_TML,RX_TML))/re(Zt(RX_TML,RX_TML))"),
    ("FOM_ratio", "k_ratio*sqrt(Qtx_ratio*Qrx_ratio)"),
    ("Rtx_ac_ohm", "re(Zt(TX_TML,TX_TML))"),
    ("Rrx_ac_ohm", "re(Zt(RX_TML,RX_TML))"),
    ("Xtx_ohm", "im(Zt(TX_TML,TX_TML))"),
    ("Xrx_ohm", "im(Zt(RX_TML,RX_TML))"),
    ("M_over_Ltx_ratio", "M_uH/Ltx_uH"),
    ("M_over_Lrx_ratio", "M_uH/Lrx_uH"),
    ("Gtx_S", "re(Yt(TX_TML,TX_TML))"),
    ("Btx_S", "im(Yt(TX_TML,TX_TML))"),
    ("Grx_S", "re(Yt(RX_TML,RX_TML))"),
    ("Brx_S", "im(Yt(RX_TML,RX_TML))"),
    ("S11_mag_ratio", "mag(S(TX_TML,TX_TML))"),
    ("S21_mag_ratio", "mag(S(TX_TML,RX_TML))"),
    ("S21_phase_deg", "ang_deg_val(S(TX_TML,RX_TML))"),
    ("S22_mag_ratio", "mag(S(RX_TML,RX_TML))"),
    ("eta_s21_power_ratio", "S21_mag_ratio*S21_mag_ratio"),
    ("eta_tx_accept_ratio", "1-S11_mag_ratio*S11_mag_ratio"),
    ("eta_rx_accept_ratio", "1-S22_mag_ratio*S22_mag_ratio"),
    ("eta_match_product_ratio", "eta_tx_accept_ratio*eta_rx_accept_ratio"),
    ("eta_s21_from_tx_accept_ratio", "eta_s21_power_ratio/eta_tx_accept_ratio"),
    ("eta_s21_from_rx_accept_ratio", "eta_s21_power_ratio/eta_rx_accept_ratio"),
    ("eta_s21_two_sided_norm_ratio", "eta_s21_power_ratio/(eta_tx_accept_ratio*eta_rx_accept_ratio)"),
    (
        "eta_fom_max_ratio",
        "(FOM_ratio*FOM_ratio)/((1+sqrt(1+FOM_ratio*FOM_ratio))*(1+sqrt(1+FOM_ratio*FOM_ratio)))",
    ),
)


def type1_outputs_spec() -> OutputsSpec:
    return {
        "report_name": "Output Variables Table1",
        "solution_name": "Setup1 : LastAdaptive",
        "primary_sweep": "Freq",
        "report_category": "Terminal Solution Data",
        "plot_type": "Data Table",
        "variables": [{"name": name, "expression": expression} for name, expression in TYPE1_OUTPUT_VARIABLES],
    }

def write_type1_toml(path: Path, *, tx_region_h: float = 200.0, outer_x: float = 140.0, outer_y: float = 80.0) -> None:
    template_path = Path(__file__).with_name("type1_spec_base.toml")
    raw = template_path.read_text(encoding="utf-8")
    raw = raw.replace("__TX_REGION_H__", f"{tx_region_h:.1f}")
    raw = raw.replace("__TX_DD_OUTER_X__", f"{outer_x:.1f}")
    raw = raw.replace("__OUTER_Y__", f"{outer_y:.1f}")
    path.write_text(raw, encoding="utf-8")

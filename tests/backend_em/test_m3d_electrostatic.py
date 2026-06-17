from __future__ import annotations

from pathlib import Path

import pytest

from peetsfea.backend.pyaedt.m3d_electrostatic import _es_unit_scale, _parse_es_matrix_txt

REAL_EXPORT = """Solution : ESSetup : LastAdaptive
Parameter : CMatrix
Capacitance Unit: pF

Capacitance
\t\ttx_v\trx_v
\ttx_v\t12.05\t-2.292
\trx_v\t-2.292\t14.005

Capacitive Coupling Coefficient
\t\ttx_v\trx_v
\ttx_v\t1\t-0.17643
\trx_v\t-0.17643\t1
"""


def test_es_unit_scale_folds_to_farads() -> None:
    assert _es_unit_scale("pF") == pytest.approx(1e-12)
    assert _es_unit_scale("fF") == pytest.approx(1e-15)
    assert _es_unit_scale("F") == pytest.approx(1.0)


def test_parse_es_matrix_txt_returns_si_capacitance_and_coupling(tmp_path: Path) -> None:
    f = tmp_path / "m3d_es_cmatrix.txt"
    f.write_text(REAL_EXPORT)
    cap, coup = _parse_es_matrix_txt(f)
    # C1 (tx self), C2 (rx self), Cm (mutual) folded to farads
    assert cap["tx_v"]["tx_v"] == pytest.approx(12.05e-12)
    assert cap["rx_v"]["rx_v"] == pytest.approx(14.005e-12)
    assert cap["tx_v"]["rx_v"] == pytest.approx(-2.292e-12)
    # coupling is dimensionless and physical (<1)
    assert coup["tx_v"]["rx_v"] == pytest.approx(-0.17643)
    assert abs(coup["tx_v"]["rx_v"]) < 1.0


def test_parse_es_matrix_txt_raises_on_missing_block(tmp_path: Path) -> None:
    f = tmp_path / "bad.txt"
    f.write_text("Capacitance Unit: pF\n\nNot A Matrix\n")
    with pytest.raises(ValueError, match="Capacitance"):
        _parse_es_matrix_txt(f)

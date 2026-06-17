from __future__ import annotations

from pathlib import Path

import pytest

from peetsfea.backend.pyaedt.m3d_ac_magnetic import _freq_hz, _parse_ac_matrix_txt

# Trimmed real Maxwell AC-Magnetic matrix export (one frequency block).
REAL_EXPORT = """Solution : ACSetup : LastAdaptive
Parameter : LMatrix
Resistance Unit: ohm
Inductance Unit: nH
Flux Unit: Wb

6780000Hz
\tRe(Z), Im(Z)
\t\t\ttx_winding\trx_winding
\t\ttx_winding\t0.11964, 216.48\t0.00035233, 2.8602
\t\trx_winding\t0.00035233, 2.8602\t0.10401, 184.02

\tInductive Coupling Coefficient
\t\t\ttx_winding\trx_winding
\t\ttx_winding\t1\t0.014331
\t\trx_winding\t0.014331\t1

\tR,L
\t\t\ttx_winding\trx_winding
\t\ttx_winding\t0.11964, 5081.6\t0.00035233, 67.141
\t\trx_winding\t0.00035233, 67.141\t0.10401, 4319.6
"""


def test_freq_hz_parses_units() -> None:
    assert _freq_hz("6.78MHz") == pytest.approx(6.78e6)
    assert _freq_hz("100 kHz") == pytest.approx(1e5)
    assert _freq_hz("2GHz") == pytest.approx(2e9)


def test_parse_ac_matrix_txt_returns_rl_and_coupling(tmp_path: Path) -> None:
    f = tmp_path / "m3d_ac_lmatrix.txt"
    f.write_text(REAL_EXPORT)
    R, L, k = _parse_ac_matrix_txt(f, "6.78MHz")
    tx, rx = "tx_winding", "rx_winding"
    # loop inductances (nH) and AC resistances (ohm)
    assert L[tx][tx] == pytest.approx(5081.6)
    assert L[rx][rx] == pytest.approx(4319.6)
    assert L[tx][rx] == pytest.approx(67.141)
    assert R[tx][tx] == pytest.approx(0.11964)
    assert R[rx][rx] == pytest.approx(0.10401)
    assert k == pytest.approx(0.014331)


def test_parse_ac_matrix_txt_raises_on_missing_frequency(tmp_path: Path) -> None:
    f = tmp_path / "m3d_ac_lmatrix.txt"
    f.write_text(REAL_EXPORT)
    with pytest.raises(ValueError, match="no block at"):
        _parse_ac_matrix_txt(f, "13.56MHz")

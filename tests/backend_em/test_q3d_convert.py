from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from peetsfea.ssw_step import DEFAULT_SOURCE_TOML_PATH
from peetsfea.ssw_design_space import build_ssw_aedt_identity
from peetsfea.ssw_aedt_artifacts import (
    AEDT_IMPORTED_LEDGER_NAME,
    AEDT_PORT_LEDGER_NAME,
    export_ssw_aedt_port_artifacts,
)
from peetsfea.backend.pyaedt.ssw_ports import setup_ssw_aedt_ports
from peetsfea.backend.pyaedt.q3d_convert import (
    Q3D_DESIGN_NAME,
    Q3D_FREQUENCY,
    convert_hfss_to_q3d,
)
from peetsfea.backend.pyaedt.q3d_convert import _parse_matrix_csv, _unit_scale

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = REPO_ROOT / "run"


def test_unit_scale_folds_q3d_header_units_to_si() -> None:
    assert _unit_scale('"C(a,a) [pF]"') == pytest.approx(1e-12)
    assert _unit_scale('"ACL(a,a) [uH]"') == pytest.approx(1e-6)
    assert _unit_scale('"ACL(a,b) [nH]"') == pytest.approx(1e-9)
    assert _unit_scale('"ACR(a,a) [ohm]"') == pytest.approx(1.0)
    assert _unit_scale('"ACR(a,b) [mOhm]"') == pytest.approx(1e-3)


def test_parse_matrix_csv_takes_last_converged_pass_and_folds_units(tmp_path: Path) -> None:
    # Mirrors a real Q3D ACL export: per-pass rows, mixed uH/nH units, trailing non-converged
    # passes filled with ``nan``. The parser must return the deepest fully-numeric pass in SI.
    csv_path = tmp_path / "ACL.csv"
    csv_path.write_text(
        '"Freq [GHz]","Pass []","ACL(tx:tx) [uH]","ACL(tx:rx) [nH]","ACL(rx:rx) [uH]"\n'
        "0.00678,1,5.31,117.45,4.65\n"
        "0.00678,2,5.297159,117.3555,4.622353\n"
        "0.00678,3,nan,nan,nan\n"
    )
    values = _parse_matrix_csv(csv_path)
    assert values["ACL(tx:tx)"] == pytest.approx(5.297159e-6)
    assert values["ACL(tx:rx)"] == pytest.approx(117.3555e-9)
    assert values["ACL(rx:rx)"] == pytest.approx(4.622353e-6)


def test_parse_matrix_csv_raises_when_no_pass_converged(tmp_path: Path) -> None:
    csv_path = tmp_path / "ACL.csv"
    csv_path.write_text(
        '"Freq [GHz]","Pass []","ACL(tx:tx) [uH]"\n'
        "0.00678,1,nan\n"
    )
    with pytest.raises(ValueError, match="no converged"):
        _parse_matrix_csv(csv_path)


@pytest.mark.pyaedt_integration
def test_convert_hfss_to_q3d_copies_geometry_and_identifies_nets() -> None:
    out = RUN_DIR / "q3d_convert_test"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    fixed = DEFAULT_SOURCE_TOML_PATH
    identity = build_ssw_aedt_identity(fixed)
    export_ssw_aedt_port_artifacts(source_toml_path=fixed, output_dir=out, seed=0)
    aedt_path = out / identity.aedt_filename
    setup_ssw_aedt_ports(
        port_ledger_path=out / AEDT_PORT_LEDGER_NAME,
        output_aedt_path=aedt_path,
        imported_ledger_path=out / AEDT_IMPORTED_LEDGER_NAME,
        design_name=identity.design_id,
    )

    result = convert_hfss_to_q3d(aedt_path=aedt_path, hfss_design=identity.design_id)

    assert result["q3d_design"] == Q3D_DESIGN_NAME
    assert result["q3d_setup"] == "Q3DSetup"
    assert result["frequency"] == Q3D_FREQUENCY
    # the TX/RX copper coils become the two Q3D conductor nets
    assert set(result["net_names"]) == {"tx_ssw_coil_ssw_copper", "rx_ssw_coil_ssw_copper"}
    # copied geometry includes the conductors and the FR4/ferrite dielectrics
    assert "tx_ssw_coil_ssw_copper" in result["q3d_object_names"]
    assert "rx_ssw_coil_ssw_copper" in result["q3d_object_names"]
    assert "tx_mull_ferrite_sheet" in result["q3d_object_names"]

from __future__ import annotations

from pathlib import Path
from typing import TypedDict, cast

from peetsfea.aedt.failfast import raise_on_false
from peetsfea.aedt.protocols import DesignSession, HfssSession, ReportSetupModuleSession

DEFAULT_TYPE2_EM_SETUP_NAME = "Setup1"
DEFAULT_TYPE2_EM_REPORT_NAME = "Output Variables Table1"


class Type2EmSolveResult(TypedDict):
    setup_name: str
    report_name: str
    report_csv_path: str


def _report_setup_module(hfss: HfssSession) -> ReportSetupModuleSession:
    assert (_ := hfss.odesign)
    assert isinstance(_, DesignSession)
    design: DesignSession = _
    raw_report_setup = design.GetModule("ReportSetup")
    assert hasattr(raw_report_setup, "GetAllReportNames"), (
        "ReportSetup module must expose GetAllReportNames for type2 EM solve export "
        f"(module_type={type(raw_report_setup).__name__})"
    )
    assert hasattr(raw_report_setup, "ExportToFile"), (
        "ReportSetup module must expose ExportToFile for type2 EM solve export "
        f"(module_type={type(raw_report_setup).__name__})"
    )
    report_setup = cast(ReportSetupModuleSession, raw_report_setup)
    return report_setup


def _report_csv_path(*, output_dir: Path, report_name: str) -> Path:
    report_file_stem = report_name.replace(" ", "_")
    if report_file_stem == "":
        raise ValueError("type2 EM report name must be non-empty")
    return output_dir / f"{report_file_stem}.csv"


def solve_type2_setup_ready_hfss(
    hfss: HfssSession,
    *,
    output_dir: Path,
    setup_name: str = DEFAULT_TYPE2_EM_SETUP_NAME,
    report_name: str = DEFAULT_TYPE2_EM_REPORT_NAME,
) -> Type2EmSolveResult:
    if setup_name == "":
        raise ValueError("type2 EM setup_name must be non-empty")
    if report_name == "":
        raise ValueError("type2 EM report_name must be non-empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    raise_on_false(
        hfss.analyze_setup(setup_name, blocking=True),
        operation="analyze_setup",
        context={"setup_name": setup_name},
    )
    report_setup = _report_setup_module(hfss)
    report_names = report_setup.GetAllReportNames()
    if report_name not in set(report_names):
        raise ValueError(
            "type2 EM solve cannot export missing report "
            f"(report_name={report_name!r}, available={list(report_names)!r})"
        )
    report_csv_path = _report_csv_path(output_dir=output_dir, report_name=report_name)
    raise_on_false(
        report_setup.ExportToFile(report_name, str(report_csv_path)),
        operation="ReportSetup.ExportToFile",
        context={"report_name": report_name, "path": str(report_csv_path)},
    )
    if not report_csv_path.is_file():
        raise FileNotFoundError(f"type2 EM report export did not create CSV: {report_csv_path}")
    return {
        "setup_name": setup_name,
        "report_name": report_name,
        "report_csv_path": str(report_csv_path),
    }


__all__ = [
    "DEFAULT_TYPE2_EM_REPORT_NAME",
    "DEFAULT_TYPE2_EM_SETUP_NAME",
    "Type2EmSolveResult",
    "solve_type2_setup_ready_hfss",
]

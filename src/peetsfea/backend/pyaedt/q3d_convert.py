"""Convert an HFSS design into a Q3D Extractor design for R/L/C parasitic cross-validation.

This mirrors the AEDT GUI flow ("copy the HFSS model into a new Q3D design"): it creates a Q3D
design in the same project, copies the conductor geometry across, auto-identifies nets, and adds a
Q3D matrix setup (Cap + AC RL + DC RL) at the target frequency. Source/sink assignment and the solve
are intentionally left to the user — exactly as in the GUI ("a few clicks to convert, then I set a
couple of things and run") — so the project is saved Q3D-ready.

Used for the EM cross-validation plan (docs/em-cross-validation-plan.html): Q3D provides R, L, M, C,
G in one tool to cross-check the HFSS Z-derived values at 6.78 MHz.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TypedDict

from ansys.aedt.core import Hfss as RawHfss
from ansys.aedt.core import Q3d as RawQ3d

from peetsfea.aedt.failfast import raise_on_false

Q3D_DESIGN_NAME = "Q3D_from_HFSS"
Q3D_SETUP_NAME = "Q3DSetup"
Q3D_FREQUENCY = "6.78MHz"

# Matrix quantities to extract. ``C`` is a net-vs-net capacitance; the RL families are
# terminal-vs-terminal (``net:source``). Headless extraction must go through the native
# ReportSetup module (PyAEDT 0.25.1 ``export_matrix_data`` is broken in gRPC mode), and the
# only solution that actually carries matrix data is ``<setup> : AdaptivePass`` with the
# adaptive ``Pass`` as the sweep axis (``LastAdaptive``/``Freq`` reports come back empty).
_C_MATRICES = ("C",)
_RL_MATRICES = ("ACL", "ACR", "DCL", "DCR")
Q3D_MATRIX_NAMES = (*_C_MATRICES, *_RL_MATRICES)


class Q3dConvertResult(TypedDict):
    project_path: str
    hfss_design: str
    q3d_design: str
    q3d_setup: str
    frequency: str
    q3d_object_names: list[str]
    net_names: list[str]


def convert_hfss_to_q3d(
    *,
    aedt_path: Path,
    hfss_design: str,
    q3d_design: str = Q3D_DESIGN_NAME,
    setup_name: str = Q3D_SETUP_NAME,
    frequency: str = Q3D_FREQUENCY,
    non_graphical: bool = True,
    new_desktop: bool = True,
    release_desktop_on_exit: bool = True,
) -> Q3dConvertResult:
    """Create a Q3D design from an HFSS design's geometry, ready for source/sink + solve.

    The HFSS project is opened, a Q3D design is created in the same project, the (non-vacuum,
    non-PEC) solid bodies are copied over, nets are auto-identified, and a matrix setup at
    ``frequency`` is added and saved. PyAEDT ``False`` returns raise immediately (fail-fast).
    """
    aedt_path = Path(aedt_path)
    if not aedt_path.is_file():
        raise FileNotFoundError(f"HFSS project does not exist: {aedt_path}")

    hfss = RawHfss(
        project=str(aedt_path),
        design=hfss_design,
        non_graphical=non_graphical,
        new_desktop=new_desktop,
        close_on_exit=False,
    )
    try:
        q3d = RawQ3d(
            project=hfss.project_name,
            design=q3d_design,
            non_graphical=non_graphical,
            close_on_exit=False,
        )
        raise_on_false(
            q3d.copy_solid_bodies_from(hfss, no_vacuum=True, no_pec=True, include_sheets=False),
            operation="copy_solid_bodies_from",
            context={"hfss_design": hfss_design, "q3d_design": q3d_design},
        )
        raise_on_false(q3d.auto_identify_nets(), operation="auto_identify_nets")

        setup = q3d.create_setup(name=setup_name)
        setup.props["AdaptiveFreq"] = frequency
        raise_on_false(setup.update(), operation="q3d_setup.update", context={"AdaptiveFreq": frequency})

        raise_on_false(
            q3d.save_project(str(aedt_path)),
            operation="save_project",
            context={"path": str(aedt_path)},
        )

        net_names = [str(name) for name in q3d.net_names]
        object_names = [str(name) for name in q3d.modeler.object_names]
        return {
            "project_path": str(aedt_path),
            "hfss_design": hfss_design,
            "q3d_design": q3d_design,
            "q3d_setup": setup_name,
            "frequency": frequency,
            "q3d_object_names": object_names,
            "net_names": net_names,
        }
    finally:
        if release_desktop_on_exit:
            raise_on_false(
                hfss.desktop_class.release_desktop(close_projects=True, close_on_exit=True),
                operation="release_desktop",
                context={"close_projects": True, "close_on_exit": True},
            )


class Q3dMatrixExportResult(TypedDict):
    project_path: str
    q3d_design: str
    solution: str
    nets: list[str]
    terminals: list[str]
    csv_paths: dict[str, str]
    values: dict[str, dict[str, float]]


def _q3d_nets_and_terminals(q3d: RawQ3d) -> tuple[list[str], list[str]]:
    """Return ordered (net names, terminal ``net:source`` names) from the Q3D boundaries.

    Source boundaries carry ``props["Net"]`` = the owning SignalNet's ``props["ID"]``, so the
    terminal names are derived robustly (no name-convention guessing).
    """
    net_by_id: dict[int, str] = {}
    sources: list[tuple[str, int]] = []
    for boundary in q3d.boundaries:
        props = boundary.props
        if boundary.type == "SignalNet":
            net_by_id[int(props["ID"])] = boundary.name
        elif boundary.type == "Source":
            sources.append((boundary.name, int(props["Net"])))
    if not net_by_id:
        raise ValueError("Q3D design has no SignalNet boundaries to build a matrix report from")
    if not sources:
        raise ValueError("Q3D design has no Source boundaries — assign source/sink before export")
    nets = [net_by_id[i] for i in sorted(net_by_id)]
    terminals = [f"{net_by_id[net_id]}:{source}" for source, net_id in sources]
    return nets, terminals


def _parse_matrix_csv(csv_path: Path) -> dict[str, float]:
    """Parse a Q3D matrix Data-Table CSV, returning the last fully-converged adaptive pass.

    Columns are ``Freq, Pass, <q1>, <q2>, ...``; the deepest pass with no ``nan`` cell is the
    converged matrix. Header units (``[pF]``/``[uH]``/``[nH]``/``[ohm]``/``[mOhm]``) are folded
    into a consistent base (F, H, ohm) so callers compare numbers, not unit strings.
    """
    with csv_path.open(newline="") as handle:
        rows = list(csv.reader(handle))
    if len(rows) < 2:
        raise ValueError(f"Q3D matrix CSV has no data rows: {csv_path}")
    header = rows[0]
    scales = [_unit_scale(col) for col in header]
    best: dict[str, float] | None = None
    for row in rows[1:]:
        if len(row) != len(header) or any(cell.strip().lower() == "nan" for cell in row[2:]):
            continue
        best = {
            header[i].split(" [")[0].strip('"'): float(row[i]) * scales[i]
            for i in range(2, len(header))
        }
    if best is None:
        raise ValueError(f"Q3D matrix CSV has no converged (non-nan) pass: {csv_path}")
    return best


def _unit_scale(header_cell: str) -> float:
    unit = header_cell[header_cell.find("[") + 1 : header_cell.find("]")].strip().lower()
    return {
        "pf": 1e-12, "nf": 1e-9, "uf": 1e-6, "f": 1.0,
        "ph": 1e-12, "nh": 1e-9, "uh": 1e-6, "mh": 1e-3, "h": 1.0,
        "mohm": 1e-3, "ohm": 1.0, "kohm": 1e3,
    }.get(unit, 1.0)


def export_q3d_matrices(
    *,
    aedt_path: Path,
    output_dir: Path,
    q3d_design: str = Q3D_DESIGN_NAME,
    setup_name: str = Q3D_SETUP_NAME,
    non_graphical: bool = True,
    new_desktop: bool = True,
    release_desktop_on_exit: bool = True,
) -> Q3dMatrixExportResult:
    """Create the Q3D R/L/C matrix reports and export them to CSV, headlessly.

    Requires a *solved* Q3D design with source/sink assigned. For each of C / AC L / AC R /
    DC L / DC R a ``Matrix`` Data-Table report is built on the ``<setup> : AdaptivePass``
    solution (the only one that carries matrix data headlessly) and exported via the native
    ``ReportSetup.ExportToFile`` — the proven path, since PyAEDT's ``export_matrix_data`` raises
    in gRPC mode. Returns the CSV paths plus the converged matrix values in SI units.
    """
    aedt_path = Path(aedt_path)
    if not aedt_path.is_file():
        raise FileNotFoundError(f"Q3D project does not exist: {aedt_path}")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    q3d = RawQ3d(
        project=str(aedt_path),
        design=q3d_design,
        non_graphical=non_graphical,
        new_desktop=new_desktop,
        close_on_exit=False,
    )
    try:
        nets, terminals = _q3d_nets_and_terminals(q3d)
        solution = f"{setup_name} : AdaptivePass"
        report_module = q3d.odesign.GetModule("ReportSetup")
        csv_paths: dict[str, str] = {}
        values: dict[str, dict[str, float]] = {}
        for matrix in Q3D_MATRIX_NAMES:
            members = nets if matrix in _C_MATRICES else terminals
            traces = [f"{matrix}({a},{b})" for a in members for b in members]
            report_name = f"{matrix}_matrix"
            try:
                report_module.DeleteReports([report_name])
            except Exception:  # report may not exist yet — DeleteReports is best-effort
                pass
            raise_on_false(
                report_module.CreateReport(
                    report_name,
                    "Matrix",
                    "Data Table",
                    solution,
                    ["Context:=", "Original"],
                    ["Pass:=", ["All"], "Freq:=", ["All"]],
                    ["X Component:=", "Pass", "Y Component:=", traces],
                ),
                operation="ReportSetup.CreateReport",
                context={"report_name": report_name, "solution": solution},
            )
            out = output_dir / f"{matrix}.csv"
            if out.exists():
                out.unlink()
            report_module.ExportToFile(report_name, str(out), False)
            if not out.is_file():
                raise FileNotFoundError(f"Q3D matrix export did not create CSV: {out}")
            csv_paths[matrix] = str(out)
            values[matrix] = _parse_matrix_csv(out)

        raise_on_false(q3d.save_project(), operation="save_project")
        return {
            "project_path": str(aedt_path),
            "q3d_design": q3d_design,
            "solution": solution,
            "nets": nets,
            "terminals": terminals,
            "csv_paths": csv_paths,
            "values": values,
        }
    finally:
        if release_desktop_on_exit:
            raise_on_false(
                q3d.desktop_class.release_desktop(close_projects=True, close_on_exit=True),
                operation="release_desktop",
                context={"close_projects": True, "close_on_exit": True},
            )


__all__ = [
    "Q3D_DESIGN_NAME",
    "Q3D_FREQUENCY",
    "Q3D_MATRIX_NAMES",
    "Q3D_SETUP_NAME",
    "Q3dConvertResult",
    "Q3dMatrixExportResult",
    "convert_hfss_to_q3d",
    "export_q3d_matrices",
]

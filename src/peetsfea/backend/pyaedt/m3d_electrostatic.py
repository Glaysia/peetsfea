"""Extract the capacitance matrix from an HFSS coil via a Maxwell 3D Electrostatic design.

Mirrors the AEDT GUI flow ("copy the HFSS model into a new Maxwell 3D Electrostatic design"):
creates the design, copies the conductor + dielectric geometry across, drops the HFSS vacuum/region
remnants, wraps the model in an air region whose outer faces are grounded (0 V), assigns a voltage
excitation to each conductor, builds an electric capacitance matrix, solves, and exports it.

The ground reference matters: with only the two coil conductors and no reference, the Maxwell
capacitance matrix collapses to coupling = 1 (every field line from one coil lands on the other).
Grounding the air-region boundary lets each coil's field terminate on ground too, so the matrix is
physical (self-C on the diagonal, -mutual off-diagonal), comparable to the Q3D CG matrix and the
HFSS self-resonance C1/C2.

Used by the EM cross-validation plan (docs/em-cross-validation-plan.html, §4): Electrostatic gives
C only (no current => no resistance); R comes from HFSS re(Z) or M3D AC Magnetic.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

from ansys.aedt.core import Hfss as RawHfss
from ansys.aedt.core import Maxwell3d
from ansys.aedt.core.modules.boundary.maxwell_boundary import MatrixElectric

from peetsfea.aedt.failfast import raise_on_false

ES_DESIGN_NAME = "M3D_Electrostatic"
ES_SETUP_NAME = "ESSetup"
ES_MATRIX_NAME = "CMatrix"
# HFSS region/vacuum objects are filled with these materials; copy_solid_bodies_from drags them
# across and they collapse the open-region field if kept.
_VACUUM_MATERIALS = {"vacuum", "air"}


class M3dEsResult(TypedDict):
    project_path: str
    hfss_design: str
    es_design: str
    conductors: list[str]
    matrix_file: str
    capacitance: dict[str, dict[str, float]]
    coupling: dict[str, dict[str, float]]


def _es_unit_scale(unit: str) -> float:
    return {"pf": 1e-12, "nf": 1e-9, "uf": 1e-6, "ff": 1e-15, "f": 1.0}.get(unit.strip().lower(), 1.0)


def _parse_es_matrix_txt(matrix_file: Path) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """Parse a Maxwell electrostatic matrix .txt export into (capacitance_SI, coupling) blocks.

    The file holds two labelled square tables ("Capacitance" in the header's unit, then
    "Capacitive Coupling Coefficient", dimensionless). Capacitance is folded to farads.
    """
    text = matrix_file.read_text()
    unit_match = re.search(r"Capacitance Unit:\s*(\w+)", text)
    scale = _es_unit_scale(unit_match.group(1)) if unit_match else 1.0

    def parse_block(title: str, factor: float) -> dict[str, dict[str, float]]:
        # Block = title line, then a header row of column names, then one row per source.
        lines = text.splitlines()
        start = next((i for i, ln in enumerate(lines) if ln.strip() == title), None)
        if start is None:
            raise ValueError(f"matrix export missing '{title}' block: {matrix_file}")
        cols = lines[start + 1].split()
        out: dict[str, dict[str, float]] = {}
        for ln in lines[start + 2 :]:
            parts = ln.split()
            if len(parts) != len(cols) + 1:
                break
            row = parts[0]
            out[row] = {cols[j]: float(parts[j + 1]) * factor for j in range(len(cols))}
        if not out:
            raise ValueError(f"matrix export '{title}' block had no data rows: {matrix_file}")
        return out

    capacitance = parse_block("Capacitance", scale)
    coupling = parse_block("Capacitive Coupling Coefficient", 1.0)
    return capacitance, coupling


def extract_m3d_es_capacitance(
    *,
    aedt_path: Path,
    hfss_design: str,
    output_dir: Path,
    es_design: str = ES_DESIGN_NAME,
    setup_name: str = ES_SETUP_NAME,
    region_padding_percent: float = 100.0,
    maximum_passes: int = 12,
    minimum_passes: int = 2,
    percent_error: float = 1.0,
    percent_refinement: int = 30,
    non_graphical: bool = True,
    new_desktop: bool = True,
    release_desktop_on_exit: bool = True,
) -> M3dEsResult:
    """Build a Maxwell 3D Electrostatic design from an HFSS coil, solve, and export the C matrix.

    Conductors are auto-detected (``get_all_conductors_names``); each gets a voltage excitation and
    the grounded air-region boundary is the reference. Returns the capacitance matrix in farads plus
    the coupling coefficients. PyAEDT ``False`` returns raise immediately (fail-fast).
    """
    aedt_path = Path(aedt_path)
    if not aedt_path.is_file():
        raise FileNotFoundError(f"HFSS project does not exist: {aedt_path}")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    hfss = RawHfss(
        project=str(aedt_path),
        design=hfss_design,
        non_graphical=non_graphical,
        new_desktop=new_desktop,
        close_on_exit=False,
    )
    try:
        m3d = Maxwell3d(
            project=hfss.project_name,
            design=es_design,
            solution_type="Electrostatic",
            non_graphical=non_graphical,
            close_on_exit=False,
        )
        raise_on_false(
            m3d.copy_solid_bodies_from(hfss, no_vacuum=True, no_pec=True, include_sheets=False),
            operation="copy_solid_bodies_from",
            context={"hfss_design": hfss_design, "es_design": es_design},
        )
        # Drop HFSS vacuum/region remnants (open-region field collapses if they remain).
        remnants = [
            name
            for name in m3d.modeler.object_names
            if (m3d.modeler[name].material_name or "").lower() in _VACUUM_MATERIALS
        ]
        if remnants:
            m3d.modeler.delete(remnants)

        conductors = list(m3d.get_all_conductors_names())
        if len(conductors) < 2:
            raise ValueError(f"Electrostatic C matrix needs >=2 conductors, found {conductors}")

        pad = region_padding_percent
        region = m3d.modeler.create_air_region(
            x_pos=pad, y_pos=pad, z_pos=pad, x_neg=pad, y_neg=pad, z_neg=pad
        )
        region_name = region.name if hasattr(region, "name") else "Region"

        signal_sources: list[str] = []
        for conductor in conductors:
            source_name = f"{conductor}_v"
            raise_on_false(
                m3d.assign_voltage(assignment=[conductor], amplitude=1, name=source_name),
                operation="assign_voltage",
                context={"conductor": conductor},
            )
            signal_sources.append(source_name)
        region_faces = [face.id for face in m3d.modeler[region_name].faces]
        raise_on_false(
            m3d.assign_voltage(assignment=region_faces, amplitude=0, name="gnd"),
            operation="assign_voltage(ground)",
        )
        raise_on_false(
            m3d.assign_matrix(
                MatrixElectric(
                    signal_sources=signal_sources, ground_sources=["gnd"], matrix_name=ES_MATRIX_NAME
                )
            ),
            operation="assign_matrix",
            context={"signal_sources": signal_sources},
        )

        setup = m3d.create_setup(name=setup_name)
        setup.props["MaximumPasses"] = maximum_passes
        setup.props["MinimumPasses"] = minimum_passes
        setup.props["PercentError"] = percent_error
        setup.props["PercentRefinement"] = percent_refinement
        raise_on_false(setup.update(), operation="es_setup.update")

        raise_on_false(m3d.save_project(str(aedt_path)), operation="save_project")
        raise_on_false(m3d.analyze(setup=setup_name), operation="analyze", context={"setup": setup_name})
        raise_on_false(m3d.save_project(str(aedt_path)), operation="save_project(post-solve)")

        matrix_file = output_dir / "m3d_es_cmatrix.txt"
        if matrix_file.exists():
            matrix_file.unlink()
        raise_on_false(
            m3d.export_matrix(ES_MATRIX_NAME, str(matrix_file), setup=setup_name),
            operation="export_matrix",
            context={"matrix": ES_MATRIX_NAME},
        )
        if not matrix_file.is_file():
            raise FileNotFoundError(f"Electrostatic matrix export did not create file: {matrix_file}")

        capacitance, coupling = _parse_es_matrix_txt(matrix_file)
        return {
            "project_path": str(aedt_path),
            "hfss_design": hfss_design,
            "es_design": es_design,
            "conductors": conductors,
            "matrix_file": str(matrix_file),
            "capacitance": capacitance,
            "coupling": coupling,
        }
    finally:
        if release_desktop_on_exit:
            raise_on_false(
                hfss.desktop_class.release_desktop(close_projects=True, close_on_exit=True),
                operation="release_desktop",
                context={"close_projects": True, "close_on_exit": True},
            )


__all__ = [
    "ES_DESIGN_NAME",
    "ES_MATRIX_NAME",
    "ES_SETUP_NAME",
    "M3dEsResult",
    "extract_m3d_es_capacitance",
]

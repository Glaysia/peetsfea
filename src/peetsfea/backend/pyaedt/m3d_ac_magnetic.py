"""Extract the AC inductance/resistance matrix from an HFSS coil via Maxwell 3D AC Magnetic.

This mirrors the AEDT GUI flow ("copy the HFSS model into a Maxwell 3D Eddy-Current design"), but a
spiral coil fed by a small port gap can't be excited directly: an internal gap can't be an external
current terminal, and eddy current needs a complete conduction path. So the gap is bridged with
copper (the gap end-face swept across to the other end) and united into the coil -> a CLOSED loop
driven by a single inner coil terminal (a copy of the gap cross-section) carrying a circulating
current. Eddy effects + a constant-mu ferrite (Maxwell eddy current is single-frequency) give the
skin-effect AC R and the loop inductance matrix at 6.78 MHz.

Used by the EM cross-validation plan (docs/em-cross-validation-plan.html, §5): AC Magnetic is the
reference for L/M and AC R, the quantity Q3D's AC RL could not converge.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TypedDict

from ansys.aedt.core import Hfss as RawHfss
from ansys.aedt.core import Maxwell3d
from ansys.aedt.core.modules.boundary.maxwell_boundary import MatrixACMagnetic

from peetsfea.aedt.failfast import raise_on_false

AC_DESIGN_NAME = "M3D_AC_Magnetic"
AC_SETUP_NAME = "ACSetup"
AC_MATRIX_NAME = "LMatrix"
AC_FREQUENCY = "6.78MHz"
COPPER_THICKNESS_MM = 0.07
# Ferrite is frequency-dependent; Maxwell eddy current solves at a single frequency, so the
# permeability is frozen to its 6.78 MHz value (same trick as the Q3D conversion).
FERRITE_PERMEABILITY = 135.6
FERRITE_LOSS_TANGENT = 0.00218


class M3dAcResult(TypedDict):
    project_path: str
    hfss_design: str
    ac_design: str
    frequency: str
    windings: list[str]
    matrix_file: str
    resistance_ohm: dict[str, dict[str, float]]
    inductance_nh: dict[str, dict[str, float]]
    coupling: float


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _freq_hz(frequency: str) -> float:
    units = {"ghz": 1e9, "mhz": 1e6, "khz": 1e3, "hz": 1.0}
    m = re.match(r"([0-9.eE+-]+)\s*([a-zA-Z]+)", frequency.strip())
    if not m:
        raise ValueError(f"cannot parse frequency: {frequency}")
    return float(m.group(1)) * units[m.group(2).lower()]


def _parse_ac_matrix_txt(matrix_file: Path, frequency: str) -> tuple[
    dict[str, dict[str, float]], dict[str, dict[str, float]], float
]:
    """Parse the Maxwell AC-Magnetic matrix .txt for the ``R,L`` block at ``frequency``.

    Returns (resistance[ohm], inductance[nH], coupling). The file lists, per frequency, an
    ``R,L`` table whose cells are ``<R>, <L>`` and an ``Inductive Coupling Coefficient`` table.
    """
    lines = matrix_file.read_text().splitlines()
    target = _freq_hz(frequency)
    # find the frequency block whose header (e.g. "6780000Hz") matches the target
    block_start = None
    for i, ln in enumerate(lines):
        m = re.match(r"\s*([0-9.eE+-]+)Hz\s*$", ln)
        if m and abs(float(m.group(1)) - target) < 1.0:
            block_start = i
            break
    if block_start is None:
        raise ValueError(f"matrix export has no block at {frequency}: {matrix_file}")
    block = lines[block_start : block_start + 40]

    def table(title: str):
        start = next((j for j, ln in enumerate(block) if ln.strip() == title), None)
        if start is None:
            raise ValueError(f"matrix block missing '{title}': {matrix_file}")
        cols = block[start + 1].split()
        rows: dict[str, list[str]] = {}
        for ln in block[start + 2 :]:
            parts = ln.split("\t")
            cells = [p for p in parts if p.strip() != ""]
            if not cells or cells[0] not in cols and not cells[0].endswith("winding"):
                if rows:
                    break
                continue
            rows[cells[0]] = cells[1:]
            if len(rows) == len(cols):
                break
        return cols, rows

    cols, rl_rows = table("R,L")
    resistance: dict[str, dict[str, float]] = {}
    inductance: dict[str, dict[str, float]] = {}
    for r in cols:
        resistance[r], inductance[r] = {}, {}
        for k, c in enumerate(cols):
            rv, lv = rl_rows[r][k].split(",")
            resistance[r][c] = float(rv)
            inductance[r][c] = float(lv)
    _, k_rows = table("Inductive Coupling Coefficient")
    off = [c for c in cols if c != cols[0]][0]
    coupling = float(k_rows[cols[0]][cols.index(off)])
    return resistance, inductance, coupling


def extract_m3d_ac_magnetic_rl(
    *,
    aedt_path: Path,
    hfss_design: str,
    port_ledger_path: Path,
    output_dir: Path,
    ac_design: str = AC_DESIGN_NAME,
    setup_name: str = AC_SETUP_NAME,
    frequency: str = AC_FREQUENCY,
    region_padding_percent: float = 50.0,
    maximum_passes: int = 10,
    minimum_passes: int = 2,
    percent_error: float = 1.0,
    non_graphical: bool = True,
    new_desktop: bool = True,
    release_desktop_on_exit: bool = True,
) -> M3dAcResult:
    """Build a Maxwell 3D AC Magnetic design from an HFSS coil, solve, and export the L/R matrix.

    The port ledger supplies each coil's gap geometry (copper body + the two gap-edge vertex pairs)
    used to bridge the gap into a closed loop and place the coil terminal. Returns the AC resistance
    (ohm) and loop inductance (nH) matrices plus the inductive coupling coefficient.
    """
    aedt_path = Path(aedt_path)
    if not aedt_path.is_file():
        raise FileNotFoundError(f"HFSS project does not exist: {aedt_path}")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger = json.loads(Path(port_ledger_path).read_text())
    keep = set(ledger["copper_body_names"] + ledger["fr4_body_names"] + ledger["ferrite_body_names"])
    copper = {pe["role"]: pe["copper_body_name"] for pe in ledger["port_edges"]}
    gap_mids = {
        pe["role"]: [[sum(v[k] for v in edge) / 2 for k in range(3)] for edge in pe["edge_vertices_xyz"]]
        for pe in ledger["port_edges"]
    }

    hfss = RawHfss(project=str(aedt_path), design=hfss_design, non_graphical=non_graphical,
                   new_desktop=new_desktop, close_on_exit=False)
    try:
        m3d = Maxwell3d(project=hfss.project_name, design=ac_design, solution_type="AC Magnetic",
                        non_graphical=non_graphical, close_on_exit=False)
        raise_on_false(
            m3d.copy_solid_bodies_from(hfss, no_vacuum=True, no_pec=True, include_sheets=False),
            operation="copy_solid_bodies_from",
        )
        remnants = [n for n in m3d.modeler.object_names if n not in keep]
        if remnants:
            m3d.modeler.delete(remnants)

        ferrite_body = ledger["ferrite_body_names"][0]
        fmat = m3d.modeler[ferrite_body].material_name
        m3d.materials[fmat].permeability = FERRITE_PERMEABILITY
        m3d.materials[fmat].magnetic_loss_tangent = FERRITE_LOSS_TANGENT
        cu_mat = m3d.modeler[copper[next(iter(copper))]].material_name

        def nearest_face(body, pt):
            best, bd = None, 1e9
            for f in m3d.modeler[body].faces:
                c = f.center
                d = sum((c[k] - pt[k]) ** 2 for k in range(3)) ** 0.5
                if d < bd:
                    bd, best = d, f
            return best

        windings = []
        for role in copper:
            body = copper[role]
            fa = nearest_face(body, gap_mids[role][0])
            fb = nearest_face(body, gap_mids[role][1])
            # coil terminal = exact copy of the gap end-face (a real conductor cross section)
            term = m3d.modeler.create_object_from_face(fa.id)
            # bridge the gap: extrude the gap face straight to the other end, unite -> closed loop
            bridge = m3d.modeler.create_object_from_face(fa.id)
            m3d.modeler.sweep_along_vector(bridge.name, _sub(fb.center, fa.center))
            m3d.modeler[bridge.name].material_name = cu_mat
            m3d.modeler.unite([body, bridge.name])
            raise_on_false(
                m3d.assign_coil([term.faces[0].id], polarity="Positive", name=f"{role}_coil"),
                operation="assign_coil", context={"role": role},
            )
            wname = f"{role}_winding"
            winding = m3d.assign_winding(winding_type="Current", is_solid=True, current=1, name=wname)
            raise_on_false(winding, operation="assign_winding", context={"role": role})
            raise_on_false(m3d.add_winding_coils(wname, [f"{role}_coil"]), operation="add_winding_coils")
            windings.append(winding)

        coil_bodies = list(copper.values())
        raise_on_false(m3d.eddy_effects_on(coil_bodies), operation="eddy_effects_on")
        m3d.mesh.assign_length_mesh(coil_bodies, maximum_length=2, maximum_elements=50000,
                                    name="coil_len")
        pad = region_padding_percent
        m3d.modeler.create_air_region(x_pos=pad, y_pos=pad, z_pos=pad * 1.2,
                                      x_neg=pad, y_neg=pad, z_neg=pad * 1.2)
        raise_on_false(
            m3d.assign_matrix(MatrixACMagnetic(signal_sources=windings, matrix_name=AC_MATRIX_NAME)),
            operation="assign_matrix",
        )

        setup = m3d.create_setup(name=setup_name)
        setup.props["Frequency"] = frequency
        setup.props["MaximumPasses"] = maximum_passes
        setup.props["MinimumPasses"] = minimum_passes
        setup.props["PercentError"] = percent_error
        raise_on_false(setup.update(), operation="ac_setup.update")

        raise_on_false(m3d.save_project(str(aedt_path)), operation="save_project")
        raise_on_false(m3d.analyze(setup=setup_name), operation="analyze", context={"setup": setup_name})
        raise_on_false(m3d.save_project(str(aedt_path)), operation="save_project(post-solve)")

        matrix_file = output_dir / "m3d_ac_lmatrix.txt"
        if matrix_file.exists():
            matrix_file.unlink()
        raise_on_false(
            m3d.export_matrix(AC_MATRIX_NAME, str(matrix_file), setup=setup_name),
            operation="export_matrix",
        )
        if not matrix_file.is_file():
            raise FileNotFoundError(f"AC matrix export did not create file: {matrix_file}")

        resistance, inductance, coupling = _parse_ac_matrix_txt(matrix_file, frequency)
        return {
            "project_path": str(aedt_path),
            "hfss_design": hfss_design,
            "ac_design": ac_design,
            "frequency": frequency,
            "windings": [w.name for w in windings],
            "matrix_file": str(matrix_file),
            "resistance_ohm": resistance,
            "inductance_nh": inductance,
            "coupling": coupling,
        }
    finally:
        if release_desktop_on_exit:
            raise_on_false(
                hfss.desktop_class.release_desktop(close_projects=True, close_on_exit=True),
                operation="release_desktop",
            )


__all__ = [
    "AC_DESIGN_NAME",
    "AC_FREQUENCY",
    "AC_MATRIX_NAME",
    "AC_SETUP_NAME",
    "M3dAcResult",
    "extract_m3d_ac_magnetic_rl",
]

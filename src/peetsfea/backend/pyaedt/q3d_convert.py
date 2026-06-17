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

from pathlib import Path
from typing import TypedDict

from ansys.aedt.core import Hfss as RawHfss
from ansys.aedt.core import Q3d as RawQ3d

from peetsfea.aedt.failfast import raise_on_false

Q3D_DESIGN_NAME = "Q3D_from_HFSS"
Q3D_SETUP_NAME = "Q3DSetup"
Q3D_FREQUENCY = "6.78MHz"


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


__all__ = [
    "Q3D_DESIGN_NAME",
    "Q3D_FREQUENCY",
    "Q3D_SETUP_NAME",
    "Q3dConvertResult",
    "convert_hfss_to_q3d",
]

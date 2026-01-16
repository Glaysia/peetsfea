from __future__ import annotations

import os
from pathlib import Path

from pyaedt import Desktop, Maxwell3d


def _start_desktop() -> Desktop:
    version = os.getenv("AEDT_VERSION")
    if version:
        return Desktop(version=version, non_graphical=True, new_desktop=False)
    return Desktop(non_graphical=False, new_desktop=False)


def main() -> None:
    project_path = Path("/home/harry/Projects/AedtProjects/byPeetsFea").resolve() / "maxwell_eddy_current.aedt"
    design_name = "EddyCurrentDesign"

    desktop = _start_desktop()
    try:
        m3d = Maxwell3d(
            project=str(project_path),
            design=design_name,
            solution_type="EddyCurrent",
            non_graphical=True,
            new_desktop=False,
        )
        m3d.save_project()
    finally:
        # desktop.close_desktop()
        pass


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
from pathlib import Path

from pyaedt import Desktop, Maxwell3d


class MaxwellEddyCurrentSession:
    def __init__(self, project_path: Path, design_name: str) -> None:
        self.project_path = project_path
        self.design_name = design_name
        self.desktop = self._start_desktop()
        self.m3d = Maxwell3d(
            project=str(self.project_path),
            design=self.design_name,
            solution_type="EddyCurrent",
            non_graphical=True,
            new_desktop=False,
        )

    def _start_desktop(self) -> Desktop:
        version = os.getenv("AEDT_VERSION")
        if version:
            return Desktop(version=version, non_graphical=True, new_desktop=False)
        return Desktop(non_graphical=False, new_desktop=False)

    def save(self) -> None:
        self.m3d.save_project()

    def close(self) -> None:
        self.desktop.close_desktop()


def main() -> None:
    project_path = Path("/home/harry/Projects/AedtProjects/byPeetsFea").resolve() / "maxwell_eddy_current.aedt"
    design_name = "EddyCurrentDesign"

    session = MaxwellEddyCurrentSession(project_path, design_name)
    session.save()


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path

from ansys.aedt.core import Hfss

from peetsfea.types.manifest import Manifest


def create_hfss_session(manifest: Manifest, aedt_path: Path) -> Hfss:
    design_name = manifest["spec"]["design_name"]
    non_graphical = manifest["inputs"]["non_graphical"]
    return Hfss(project=str(aedt_path), design=design_name, non_graphical=non_graphical, new_desktop=True)

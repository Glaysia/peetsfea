"""peetsfea package entry."""

if not __debug__:
    raise RuntimeError("peetsfea requires assertions; python -O is unsupported")

from .pipeline.run_design import RunConfig, run
from .pipeline.package_export import export_design_zip
from .backend.pyaedt.geometry.build import build_square_spiral_from_manifest
from .version import __version__

__all__ = ["__version__", "RunConfig", "build_square_spiral_from_manifest", "export_design_zip", "run"]

"""peetsfea package entry."""

from .pipeline.run_design import RunConfig, run
from .backend.pyaedt.geometry.square_spiral import build_square_spiral_from_manifest

__all__ = ["__version__", "RunConfig", "build_square_spiral_from_manifest", "run"]
__version__ = "0.1.7"

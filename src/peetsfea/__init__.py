"""peetsfea package entry."""

from .pipeline.run_design import RunConfig, run
from .backend.pyaedt.geometry.square_spiral import build_square_spiral_from_manifest

from .pipeline.run_design import SUPPORTED_SPEC_VERSION
__all__ = ["__version__", "RunConfig", "build_square_spiral_from_manifest", "run"]
__version__ = SUPPORTED_SPEC_VERSION

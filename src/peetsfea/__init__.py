"""peetsfea package entry."""

if not __debug__:
    raise RuntimeError("peetsfea requires assertions; python -O is unsupported")

from .version import __version__

__all__ = ["__version__"]

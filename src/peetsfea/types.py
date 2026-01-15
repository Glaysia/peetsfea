"""Type definitions for peetsfea."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AedtMachine:
    """AEDT execution target info."""

    name: str
    is_current_pc: bool = True
    ip_address: str | None = None
    aedt_version: str | None = 'v242'
    use_slurm: bool = False
    max_aedt_instances: int | None = 1

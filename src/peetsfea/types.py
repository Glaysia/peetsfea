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


@dataclass(frozen=True, slots=True)
class PyaedtProcessInfo:
    """Pyaedt process status snapshot for monitoring."""

    status: str = "unknown"
    gui_enabled: bool | None = None
    stage: str | None = None
    stage_elapsed_min: float | None = None
    design_name: str | None = None
    toml_path: str | None = None
    aedt_version: str | None = None
    ip_address: str | None = None
    machine_name: str | None = None
    machine_info: str | None = None

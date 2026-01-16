"""Global configuration for peetsfea."""

from __future__ import annotations

from .types import AedtMachine, PyaedtProcessInfo

machine_list: list[AedtMachine] = []
pyaedt_processes_by_machine: dict[str, list[PyaedtProcessInfo]] = {}

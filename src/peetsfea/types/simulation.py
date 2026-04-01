from __future__ import annotations

from typing import TypedDict


class SimulationPolicy(TypedDict):
    radiation_margin_mm: float
    setup_frequency_hz: float
    sweep_start_hz: float
    sweep_stop_hz: float
    validation_gate: str
    max_delta_s: float
    maximum_passes: int
    minimum_passes: int
    minimum_converged_passes: int
    percent_refinement: int
    basis_order: int
    port_accuracy: int


__all__ = ["SimulationPolicy"]

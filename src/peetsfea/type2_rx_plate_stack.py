from __future__ import annotations

import build123d as bd

from peetsfea.type2_plate_stack import build_plate_stack_scene_data
from peetsfea.type2_plate_stack import expected_plate_stack_body_names
from peetsfea.type2_plate_stack import total_plate_stack_thickness_mm
from peetsfea.type2_step_ledger import ModeledObjectSceneData
from peetsfea.type2_step_spec import ModeledRxPlateStackSpec
from peetsfea.type2_step_spec import NonModelBoxSpec

_RX_PLATE_STACK_ROLE = "rx_plate_stack"


def total_rx_plate_stack_thickness_mm(*, spec: ModeledRxPlateStackSpec) -> float:
    return total_plate_stack_thickness_mm(spec=spec)


def expected_rx_plate_stack_body_names(
    *,
    ferrite_set_count: int,
    turn_count: int,
    pcb_total_thickness_mm: float,
) -> tuple[str, ...]:
    return expected_plate_stack_body_names(
        role=_RX_PLATE_STACK_ROLE,
        ferrite_set_count=ferrite_set_count,
        turn_count=turn_count,
        pcb_total_thickness_mm=pcb_total_thickness_mm,
    )


def build_rx_plate_stack_scene_data(
    spec: ModeledRxPlateStackSpec,
    *,
    owner_spec: NonModelBoxSpec,
    seed: int,
) -> tuple[tuple[bd.Shape, ...], ModeledObjectSceneData]:
    return build_plate_stack_scene_data(spec, owner_spec=owner_spec, seed=seed)


__all__ = [
    "build_rx_plate_stack_scene_data",
    "expected_rx_plate_stack_body_names",
    "total_rx_plate_stack_thickness_mm",
]

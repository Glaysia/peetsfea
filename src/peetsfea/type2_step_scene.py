from __future__ import annotations

from typing import cast

import build123d as bd

from peetsfea.type2_non_model_scene import build_non_model_scene_entry
from peetsfea.type2_non_model_scene import build_non_model_scene_shapes
from peetsfea.type2_non_model_scene import require_non_model_object_spec
from peetsfea.type2_non_model_scene import resolve_non_model_scene_specs
from peetsfea.type2_plate_stack import build_plate_stack_scene_data
from peetsfea.type2_single_coil_scene import build_modeled_single_coil_scene_data
from peetsfea.type2_single_coil_scene import single_coil_placement_offset
from peetsfea.type2_step_ledger import ModeledObjectSceneData
from peetsfea.type2_step_spec import ModeledObjectSpec
from peetsfea.type2_step_spec import ModeledRxPlateStackSpec
from peetsfea.type2_step_spec import ModeledSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec import ModeledTxRectVoidColumnsSpec
from peetsfea.type2_step_spec import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec import NonModelBoxSpec


def _raise_modeled_tx_role_deactivated(*, object_id: str, role: str, context: str) -> None:
    raise ValueError(
        f"{context} does not support modeled TX geometry in active Type2 RxOnly export "
        f"(object_id={object_id}, role={role}). Remove the TX modeled object or use a future two-terminal export path."
    )


def build_modeled_scene_data(
    spec: ModeledObjectSpec,
    *,
    owner_spec: NonModelBoxSpec,
    seed: int,
) -> tuple[tuple[bd.Shape, ...], ModeledObjectSceneData]:
    if isinstance(spec, (ModeledTxSingleCoilSpec, ModeledTxPlateStackSpec, ModeledTxRectVoidColumnsSpec)):
        _raise_modeled_tx_role_deactivated(
            object_id=spec.object_id,
            role=spec.role,
            context="type2 modeled scene generation",
        )
    if isinstance(spec, ModeledRxPlateStackSpec):
        return build_plate_stack_scene_data(spec, owner_spec=owner_spec, seed=seed)
    return build_modeled_single_coil_scene_data(
        cast(ModeledSingleCoilSpec, spec),
        owner_spec=owner_spec,
        seed=seed,
    )


__all__ = [
    "build_modeled_scene_data",
    "build_modeled_single_coil_scene_data",
    "build_non_model_scene_entry",
    "build_non_model_scene_shapes",
    "require_non_model_object_spec",
    "resolve_non_model_scene_specs",
    "single_coil_placement_offset",
]

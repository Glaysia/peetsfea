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
from peetsfea.type2_step_spec import NonModelBoxSpec


def build_modeled_scene_data(
    spec: ModeledObjectSpec,
    *,
    owner_spec: NonModelBoxSpec,
    seed: int,
) -> tuple[tuple[bd.Shape, ...], ModeledObjectSceneData]:
    if isinstance(spec, ModeledTxRectVoidColumnsSpec):
        raise RuntimeError(
            "tx_rect_void_columns scene generation requires tilted tx_region_actual_stack_space placement "
            "and must be built from type2_step_export"
        )
    if isinstance(spec, (ModeledTxPlateStackSpec, ModeledRxPlateStackSpec)):
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

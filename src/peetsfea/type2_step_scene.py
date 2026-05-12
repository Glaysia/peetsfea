from __future__ import annotations

import math
from typing import cast

from build123d.topology import Shape

from peetsfea.type2_non_model_scene import build_non_model_scene_entry
from peetsfea.type2_non_model_scene import build_non_model_scene_shapes
from peetsfea.type2_non_model_scene import require_non_model_object_spec
from peetsfea.type2_non_model_scene import resolve_non_model_scene_specs
from peetsfea.type2_plate_stack import build_plate_stack_scene_data
from peetsfea.type2_single_coil_scene import build_modeled_single_coil_scene_data
from peetsfea.type2_single_coil_scene import single_coil_placement_offset
from peetsfea.type2_step_ledger import ModeledObjectSceneData
from peetsfea.type2_step_ledger import TvAluminumSheetCanonicalCoordinates
from peetsfea.type2_step_spec import ModeledObjectSpec
from peetsfea.type2_step_spec import ModeledRxPlateStackSpec
from peetsfea.type2_step_spec import ModeledSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec import ModeledTxRectVoidColumnsSpec
from peetsfea.type2_step_spec import ModeledTvAluminumPlateSpec
from peetsfea.type2_step_spec import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec_sampling import _integer_range_candidates
from peetsfea.type2_step_spec_sampling import _resolve_seeded_candidate_index


def _raise_modeled_tx_role_deactivated(*, object_id: str, role: str, context: str) -> None:
    raise ValueError(
        f"{context} does not support modeled TX geometry in active Type2 RxOnly export "
        f"(object_id={object_id}, role={role}). Remove the TX modeled object or use a future two-terminal export path."
    )


def _canonical_tv_aluminum_sheet_coordinates(
    *,
    owner_origin_xyz: tuple[float, float, float],
    owner_size_xyz: tuple[float, float, float],
    thickness_mm: float,
    sheet_present: bool,
) -> TvAluminumSheetCanonicalCoordinates:
    sheet_x = owner_origin_xyz[0] + owner_size_xyz[0]
    min_xyz = (sheet_x, owner_origin_xyz[1], owner_origin_xyz[2])
    max_xyz = (sheet_x, owner_origin_xyz[1] + owner_size_xyz[1], owner_origin_xyz[2] + owner_size_xyz[2])
    size_xyz = (0.0, owner_size_xyz[1], owner_size_xyz[2])
    vertices_xyz = (
        (sheet_x, owner_origin_xyz[1], owner_origin_xyz[2]),
        (sheet_x, owner_origin_xyz[1] + owner_size_xyz[1], owner_origin_xyz[2]),
        (sheet_x, owner_origin_xyz[1] + owner_size_xyz[1], owner_origin_xyz[2] + owner_size_xyz[2]),
        (sheet_x, owner_origin_xyz[1], owner_origin_xyz[2] + owner_size_xyz[2]),
    )
    return {
        "frame_origin_xyz": min_xyz,
        "outer_bounds_min_xyz": min_xyz,
        "outer_bounds_max_xyz": max_xyz,
        "outer_bounds_size_xyz": size_xyz,
        "source_non_model_object_id": "tv",
        "source_face": "+X",
        "sheet_present": sheet_present,
        "sheet_thickness_mm": thickness_mm,
        "sheet_vertices_xyz": vertices_xyz,
    }


def _resolve_tv_aluminum_sheet_present(spec: ModeledTvAluminumPlateSpec, *, seed: int) -> bool:
    candidates = _integer_range_candidates(spec.sheet_present)
    if candidates not in ((0,), (1,), (0, 1)):
        raise ValueError(
            "tv_aluminum_plate.sheet_present must realize to canonical candidates (0,), (1,), or (0, 1) "
            f"(actual={candidates})"
        )
    if len(candidates) == 1:
        realized_value = candidates[0]
    else:
        range_path = f"modeled_objects.{spec.object_id}.sheet_present"
        index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
        realized_value = candidates[index]
    if realized_value not in (0, 1):
        raise ValueError(f"tv_aluminum_plate.sheet_present resolved outside boolean domain (actual={realized_value})")
    return realized_value == 1


def build_modeled_scene_data(
    spec: ModeledObjectSpec,
    *,
    owner_spec: NonModelBoxSpec,
    tx_region_max_z: float,
    seed: int,
) -> tuple[tuple[Shape, ...], ModeledObjectSceneData]:
    if isinstance(spec, (ModeledTxSingleCoilSpec, ModeledTxPlateStackSpec, ModeledTxRectVoidColumnsSpec)):
        _raise_modeled_tx_role_deactivated(
            object_id=spec.object_id,
            role=spec.role,
            context="type2 modeled scene generation",
        )
    if spec.role == "tv_aluminum_plate":
        if not isinstance(spec, ModeledTvAluminumPlateSpec):
            raise TypeError(
                "type2 tv_aluminum_plate modeled object must parse as ModeledTvAluminumPlateSpec"
                f" (object_id={spec.object_id}, role={spec.role})"
            )
        if owner_spec.object_id != "tv":
            raise ValueError(
                "type2 tv_aluminum_plate modeled geometry requires non-model source owner 'tv' "
                f"(object_id={spec.object_id}, owner_id={owner_spec.object_id})"
            )
        origin_x, origin_y, origin_z = owner_spec.origin_xyz
        size_x, size_y, size_z = owner_spec.size_xyz
        if not math.isfinite(origin_x) or not math.isfinite(origin_y) or not math.isfinite(origin_z):
            raise ValueError(f"tv source non-model geometry origin must be finite (object_id={owner_spec.object_id})")
        if not math.isfinite(size_x) or not math.isfinite(size_y) or not math.isfinite(size_z):
            raise ValueError(f"tv source non-model geometry size must be finite (object_id={owner_spec.object_id})")
        if size_x <= 0.0 or size_y <= 0.0 or size_z <= 0.0:
            raise ValueError(f"tv source non-model geometry size must be positive (object_id={owner_spec.object_id})")
        thickness_mm = spec.thickness_mm
        if not math.isfinite(thickness_mm):
            raise ValueError(f"tv_aluminum_plate thickness must be finite (object_id={spec.object_id})")
        if thickness_mm <= 0.0:
            raise ValueError(f"tv_aluminum_plate thickness must be positive (object_id={spec.object_id})")
        canonical_coordinates = _canonical_tv_aluminum_sheet_coordinates(
            owner_origin_xyz=(origin_x, origin_y, origin_z),
            owner_size_xyz=(size_x, size_y, size_z),
            thickness_mm=thickness_mm,
            sheet_present=_resolve_tv_aluminum_sheet_present(spec, seed=seed),
        )
        scene_data = cast(
            ModeledObjectSceneData,
            {
                "object_id": spec.object_id,
                "role": "tv_aluminum_plate",
                "plane": "YZ",
                "placement_owner_id": owner_spec.object_id,
                "material": "aluminum",
                "model_state": True,
                "expected_exported_body_names": (),
                "expected_exported_body_count": 0,
                "expected_exported_body_groups": (),
                "canonical_coordinates": canonical_coordinates,
                "terminal_metadata": {},
            },
        )
        return (cast(tuple[Shape, ...], tuple()), scene_data)
    if isinstance(spec, ModeledRxPlateStackSpec):
        return build_plate_stack_scene_data(spec, owner_spec=owner_spec, seed=seed)
    if isinstance(spec, ModeledTxInnerSingleCoilSpec):
        return build_modeled_single_coil_scene_data(
            spec,
            owner_spec=owner_spec,
            tx_region_max_z=tx_region_max_z,
            seed=seed,
        )
    return build_modeled_single_coil_scene_data(
        cast(ModeledSingleCoilSpec, spec),
        owner_spec=owner_spec,
        tx_region_max_z=tx_region_max_z,
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

from __future__ import annotations

from pathlib import Path
import tomllib

from peetsfea.spec.outputs import parse_outputs_table
from peetsfea.type2_step_spec_constraints import Type2ConstraintComparisonOperator
from peetsfea.type2_step_spec_constraints import Type2ConstraintComparableRef
from peetsfea.type2_step_spec_constraints import Type2ConstraintFuncRef
from peetsfea.type2_step_spec_constraints import Type2ConstraintPathRef
from peetsfea.type2_step_spec_constraints import Type2ConstraintRule
from peetsfea.type2_step_spec_constraints import Type2ConstraintValueRef
from peetsfea.type2_step_spec_constraints import _parse_constraints
from peetsfea.type2_step_spec_constraints import _validate_constraints_for_spec
from peetsfea.type2_step_spec_modeled import parse_modeled_object
from peetsfea.type2_step_spec_modeled import append_tx_outer_single_coil_companion_specs
from peetsfea.type2_step_spec_modeled import modeled_object_id_for_role
from peetsfea.type2_step_spec_modeled import modeled_plane_for_role
from peetsfea.type2_step_spec_modeled import placement_owner_id_for_role
from peetsfea.type2_step_spec_modeled import render_tx_rect_void_toml
from peetsfea.type2_step_spec_non_model import NonModelBoxSpec
from peetsfea.type2_step_spec_non_model import NonModelDerivedSpec
from peetsfea.type2_step_spec_non_model import NonModelTxReferenceLineSpec
from peetsfea.type2_step_spec_non_model import NonModelTxRegionActualSpec
from peetsfea.type2_step_spec_non_model import NonModelTxRegionActualStackSpaceSpec
from peetsfea.type2_step_spec_non_model import NonModelTxRegionSpec
from peetsfea.type2_step_spec_non_model import Point3
from peetsfea.type2_step_spec_non_model import RangeSpec
from peetsfea.type2_step_spec_non_model import Type2SimulationPolicy
from peetsfea.type2_step_spec_non_model import _parse_non_model_box
from peetsfea.type2_step_spec_non_model import _parse_simulation_policy
from peetsfea.type2_step_spec_non_model import _require_key
from peetsfea.type2_step_spec_non_model import _require_non_empty_str
from peetsfea.type2_step_spec_non_model import _require_table
from peetsfea.type2_step_spec_non_model import _require_type2_schema_id
from peetsfea.type2_step_spec_sampling import resolve_modeled_plate_stack_metal_fill_factor
from peetsfea.type2_step_spec_sampling import resolve_modeled_plate_stack_turn_count
from peetsfea.type2_step_spec_sampling import resolve_modeled_plate_stack_y_usage_ratio
from peetsfea.type2_step_spec_sampling import resolve_modeled_plate_stack_z_usage_ratio
from peetsfea.type2_step_spec_sampling import resolve_modeled_tx_array_x_usage_ratio
from peetsfea.type2_step_spec_sampling import resolve_modeled_tx_coil_count
from peetsfea.type2_step_spec_sampling import resolve_modeled_underlay_gap_mm
from peetsfea.type2_step_spec_sampling import resolve_modeled_underlay_repeat_count
from peetsfea.type2_step_spec_sampling import resolve_modeled_wall_parallel_stack_present
from peetsfea.type2_step_spec_sampling import resolve_non_model_tx_region_actual_stack_space_tilt_enabled
from peetsfea.type2_step_spec_types import ModeledObjectRole
from peetsfea.type2_step_spec_types import ModeledObjectSpec
from peetsfea.type2_step_spec_types import ModeledPlateStackRole
from peetsfea.type2_step_spec_types import ModeledPlateStackSpec
from peetsfea.type2_step_spec_types import ModeledRxPlateStackSpec
from peetsfea.type2_step_spec_types import ModeledRxSingleCoilSpec
from peetsfea.type2_step_spec_types import ModeledSingleCoilCommonSpec
from peetsfea.type2_step_spec_types import ModeledSingleCoilRole
from peetsfea.type2_step_spec_types import ModeledSingleCoilSpec
from peetsfea.type2_step_spec_types import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec_types import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec_types import ModeledTxOuterSingleCoilSpec
from peetsfea.type2_step_spec_types import ModeledTxRectVoidColumnsSpec
from peetsfea.type2_step_spec_types import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec_types import Type2StepSpec


def load_type2_step_spec(toml_path: Path) -> Type2StepSpec:
    raw_text = toml_path.read_text(encoding="utf-8")
    raw_spec = tomllib.loads(raw_text)
    root = _require_table(raw_spec, toml_path.name)
    _require_type2_schema_id(root, context=toml_path.name)

    design = _require_table(_require_key(root, "design", toml_path.name), "design")
    units = _require_non_empty_str(design, "units", "design")
    if units != "mm":
        raise ValueError(f"design.units must be 'mm' (actual={units})")

    raw_non_model_objects = _require_key(root, "non_model_objects", toml_path.name)
    if not isinstance(raw_non_model_objects, list):
        raise TypeError("non_model_objects must be an array of tables")
    if len(raw_non_model_objects) == 0:
        raise ValueError("non_model_objects must not be empty")

    raw_modeled_objects = _require_key(root, "modeled_objects", toml_path.name)
    if not isinstance(raw_modeled_objects, list):
        raise TypeError("modeled_objects must be an array of tables")
    if len(raw_modeled_objects) == 0:
        raise ValueError("modeled_objects must not be empty")

    constraints: tuple[Type2ConstraintRule, ...] = ()
    if "constraints" in root:
        constraints = _parse_constraints(root["constraints"], context=f"{toml_path.name}.constraints")

    seen_object_ids: set[str] = set()
    non_model_box_specs: list[NonModelBoxSpec] = []
    non_model_derived_specs: list[NonModelDerivedSpec] = []
    for index, raw_object in enumerate(raw_non_model_objects):
        context = f"{toml_path.name}.non_model_objects[{index}]"
        table = _require_table(raw_object, context)
        kind = _require_non_empty_str(table, "kind", context)
        if kind in ("tx_region_actual", "tx_region_actual_stack_space"):
            raise ValueError(
                f"{context}.kind {kind!r} is not supported in active RxOnly type2; "
                "keep only non-modeled guide regions until TX geometry is redesigned"
            )
        non_model_box_specs.append(_parse_non_model_box(raw_object, index=index, seen_object_ids=seen_object_ids))

    non_model_objects = tuple(non_model_box_specs)
    non_model_derived_objects = tuple(non_model_derived_specs)
    non_model_specs_by_id = {spec.object_id: spec for spec in non_model_objects}

    modeled_objects_list: list[ModeledObjectSpec] = []
    for index, raw_object in enumerate(raw_modeled_objects):
        modeled_objects_list.append(
            parse_modeled_object(
                raw_object,
                index=index,
                seen_object_ids=seen_object_ids,
                non_model_specs_by_id=non_model_specs_by_id,
            )
        )

    parsed_modeled_objects = tuple(modeled_objects_list)
    type2_step_spec_for_constraints = Type2StepSpec(
        source_toml_path=str(toml_path),
        simulation=_parse_simulation_policy(root, context=toml_path.name),
        outputs=parse_outputs_table(_require_key(root, "outputs", toml_path.name), context=f"{toml_path.name}.outputs"),
        non_model_objects=non_model_objects,
        non_model_derived_objects=non_model_derived_objects,
        modeled_objects=parsed_modeled_objects,
        constraints=constraints,
    )
    _validate_constraints_for_spec(constraints, spec=type2_step_spec_for_constraints, context=toml_path.name)
    type2_step_spec = Type2StepSpec(
        source_toml_path=type2_step_spec_for_constraints.source_toml_path,
        simulation=type2_step_spec_for_constraints.simulation,
        outputs=type2_step_spec_for_constraints.outputs,
        non_model_objects=type2_step_spec_for_constraints.non_model_objects,
        non_model_derived_objects=type2_step_spec_for_constraints.non_model_derived_objects,
        modeled_objects=append_tx_outer_single_coil_companion_specs(raw_modeled_objects, parsed_modeled_objects),
        constraints=type2_step_spec_for_constraints.constraints,
    )
    return type2_step_spec


__all__ = [
    "ModeledObjectSpec",
    "ModeledObjectRole",
    "ModeledPlateStackRole",
    "ModeledPlateStackSpec",
    "ModeledRxPlateStackSpec",
    "ModeledRxSingleCoilSpec",
    "ModeledSingleCoilRole",
    "ModeledSingleCoilCommonSpec",
    "ModeledSingleCoilSpec",
    "ModeledTxPlateStackSpec",
    "ModeledTxOuterSingleCoilSpec",
    "ModeledTxSingleCoilSpec",
    "ModeledTxRectVoidColumnsSpec",
    "Type2ConstraintComparisonOperator",
    "Type2ConstraintFuncRef",
    "Type2ConstraintPathRef",
    "Type2ConstraintRule",
    "Type2ConstraintValueRef",
    "Type2ConstraintComparableRef",
    "NonModelBoxSpec",
    "NonModelDerivedSpec",
    "NonModelTxRegionActualSpec",
    "NonModelTxRegionActualStackSpaceSpec",
    "Point3",
    "RangeSpec",
    "Type2SimulationPolicy",
    "Type2StepSpec",
    "load_type2_step_spec",
    "modeled_object_id_for_role",
    "modeled_plane_for_role",
    "placement_owner_id_for_role",
    "resolve_modeled_plate_stack_metal_fill_factor",
    "resolve_modeled_plate_stack_turn_count",
    "resolve_modeled_plate_stack_z_usage_ratio",
    "resolve_modeled_plate_stack_y_usage_ratio",
    "resolve_modeled_tx_array_x_usage_ratio",
    "resolve_modeled_tx_coil_count",
    "resolve_modeled_underlay_gap_mm",
    "resolve_modeled_underlay_repeat_count",
    "resolve_modeled_wall_parallel_stack_present",
    "resolve_non_model_tx_region_actual_stack_space_tilt_enabled",
    "render_tx_rect_void_toml",
]

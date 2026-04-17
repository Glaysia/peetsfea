from __future__ import annotations

from peetsfea.aedt.failfast import raise_on_false, validate_aedt_name
from peetsfea.aedt.proxies import set_object_color, set_object_transparency
from peetsfea.aedt.protocols import ModelerSession
from peetsfea.backend.pyaedt.type2_step_import_ledger import (
    outer_bounds_min_xyz,
    outer_bounds_size_xyz,
    require_key,
    require_non_empty_str,
)
from peetsfea.backend.pyaedt.type2_step_import_partition import resolve_modeled_body_names

_NON_MODEL_COLOR = (128, 128, 128)
_NON_MODEL_TRANSPARENCY = 0.85
_TX_PCB_COLOR = (0, 128, 0)
_TX_PCB_TRANSPARENCY = 0.85
_TX_PCB_MATERIAL = "FR4_epoxy"
_TX_COPPER_COLOR = (184, 115, 51)
_TX_COPPER_TRANSPARENCY = 0.0
_TX_COPPER_MATERIAL = "copper"
_PLACEMENT_TOLERANCE = 1e-9


def _object_ref(modeler: ModelerSession, *, name: str, context: str) -> object:
    validate_aedt_name(name, field=f"{context}.name")
    object_ref = modeler.get_object_from_name(name)
    assert object_ref is not None, f"{context} did not resolve HFSS object: {name}"
    return object_ref


def _set_object_material(object_ref: object, *, material_name: str, context: str) -> None:
    if material_name == "":
        raise ValueError(f"{context}.material_name must be non-empty")
    assert hasattr(object_ref, "material_name"), f"{context} is missing required material_name attribute"
    setattr(object_ref, "material_name", material_name)


def _apply_object_visual_state(
    *,
    modeler: ModelerSession,
    object_name: str,
    color: tuple[int, int, int],
    transparency: float,
    context: str,
) -> None:
    object_ref = _object_ref(modeler, name=object_name, context=context)
    set_object_color(object_ref, color=color)
    set_object_transparency(object_ref, transparency=transparency)


def _apply_object_material_and_visual_state(
    *,
    modeler: ModelerSession,
    object_name: str,
    material_name: str,
    color: tuple[int, int, int],
    transparency: float,
    context: str,
) -> None:
    object_ref = _object_ref(modeler, name=object_name, context=context)
    _set_object_material(object_ref, material_name=material_name, context=context)
    set_object_color(object_ref, color=color)
    set_object_transparency(object_ref, transparency=transparency)


def set_imported_object_model_state(
    *,
    modeler: ModelerSession,
    object_id: str,
    imported_object_names: list[str],
    model_state: bool,
) -> None:
    for imported_name in imported_object_names:
        state_result = modeler.set_object_model_state(imported_name, model_state)
        raise_on_false(
            state_result,
            operation="set_object_model_state",
            context={"object_id": object_id, "name": imported_name, "model": model_state},
        )
    return None


def style_non_model_objects(*, modeler: ModelerSession, object_id: str, imported_object_names: list[str]) -> None:
    for imported_name in imported_object_names:
        _apply_object_visual_state(
            modeler=modeler,
            object_name=imported_name,
            color=_NON_MODEL_COLOR,
            transparency=_NON_MODEL_TRANSPARENCY,
            context=f"{object_id}.non_model_visual_state[{imported_name}]",
        )


def validate_modeled_bounds_against_owner(
    *,
    modeled_entry: dict[str, object],
    owner_member: dict[str, object],
    context: str,
) -> None:
    owner_id = require_non_empty_str(
        require_key(modeled_entry, key="placement_owner_id", context=context),
        context=f"{context}.placement_owner_id",
    )
    plane = require_non_empty_str(require_key(modeled_entry, key="plane", context=context), context=f"{context}.plane")
    modeled_min_x, modeled_min_y, modeled_min_z = outer_bounds_min_xyz(modeled_entry, context=context)
    modeled_size_x, modeled_size_y, modeled_size_z = outer_bounds_size_xyz(modeled_entry, context=context)
    owner_context = f"non_model_objects[*].member_objects[{owner_id}]"
    owner_min_x, owner_min_y, owner_min_z = outer_bounds_min_xyz(owner_member, context=owner_context)
    owner_size_x, owner_size_y, owner_size_z = outer_bounds_size_xyz(owner_member, context=owner_context)
    if modeled_size_x > owner_size_x or modeled_size_y > owner_size_y or modeled_size_z > owner_size_z:
        raise ValueError(
            f"{context} outer bounds must fit inside {owner_id} "
            f"(modeled_size={(modeled_size_x, modeled_size_y, modeled_size_z)}, "
            f"owner_size={(owner_size_x, owner_size_y, owner_size_z)})"
        )
    if plane == "XY":
        target_min_x = owner_min_x + (owner_size_x - modeled_size_x) / 2.0
        target_min_y = owner_min_y + (owner_size_y - modeled_size_y) / 2.0
        target_min_z = owner_min_z + owner_size_z - modeled_size_z
        if abs(modeled_min_x - target_min_x) > _PLACEMENT_TOLERANCE:
            if owner_id == "tx_region":
                raise ValueError(
                    "tx_rect_void_coil outer bounds min_x must already be centered inside tx_region "
                    f"(actual={modeled_min_x}, expected={target_min_x})"
                )
            raise ValueError(
                f"{context} outer bounds min_x must already be centered inside {owner_id} "
                f"(actual={modeled_min_x}, expected={target_min_x})"
            )
        if abs(modeled_min_y - target_min_y) > _PLACEMENT_TOLERANCE:
            if owner_id == "tx_region":
                raise ValueError(
                    "tx_rect_void_coil center_y must already align with tx_region center_y "
                    f"(actual_min_y={modeled_min_y}, expected_min_y={target_min_y})"
                )
            raise ValueError(
                f"{context} outer bounds min_y must already be centered inside {owner_id} "
                f"(actual={modeled_min_y}, expected={target_min_y})"
            )
        if abs(modeled_min_z - target_min_z) > _PLACEMENT_TOLERANCE:
            if owner_id == "tx_region":
                raise ValueError(
                    "tx_rect_void_coil outer bounds max_z must already touch tx_region max_z "
                    f"(actual={modeled_min_z}, expected={target_min_z})"
                )
            raise ValueError(
                f"{context} outer bounds max_z must already touch {owner_id} max_z "
                f"(actual={modeled_min_z}, expected={target_min_z})"
            )
        return
    target_min_x = owner_min_x + owner_size_x - modeled_size_x
    target_min_y = owner_min_y + (owner_size_y - modeled_size_y) / 2.0
    target_min_z = owner_min_z
    if abs(modeled_min_x - target_min_x) > _PLACEMENT_TOLERANCE:
        raise ValueError(
            f"{context} outer bounds max_x must already touch {owner_id} max_x "
            f"(actual={modeled_min_x}, expected={target_min_x})"
        )
    if abs(modeled_min_y - target_min_y) > _PLACEMENT_TOLERANCE:
        raise ValueError(
            f"{context} outer bounds min_y must already be centered inside {owner_id} "
            f"(actual={modeled_min_y}, expected={target_min_y})"
        )
    if abs(modeled_min_z - target_min_z) > _PLACEMENT_TOLERANCE:
        raise ValueError(
            f"{context} outer bounds min_z must already touch {owner_id} min_z "
            f"(actual={modeled_min_z}, expected={target_min_z})"
        )


def style_imported_modeled_objects(
    *,
    modeler: ModelerSession,
    modeled_entry: dict[str, object],
    imported_object_names: list[str],
    context: str,
) -> None:
    pcb_names, copper_names = resolve_modeled_body_names(
        modeled_entry=modeled_entry,
        imported_object_names=imported_object_names,
        context=context,
    )
    for pcb_name in pcb_names:
        _apply_object_material_and_visual_state(
            modeler=modeler,
            object_name=pcb_name,
            material_name=_TX_PCB_MATERIAL,
            color=_TX_PCB_COLOR,
            transparency=_TX_PCB_TRANSPARENCY,
            context=f"{context}.pcb[{pcb_name}]",
        )
    copper_name = copper_names[0]
    _apply_object_material_and_visual_state(
        modeler=modeler,
        object_name=copper_name,
        material_name=_TX_COPPER_MATERIAL,
        color=_TX_COPPER_COLOR,
        transparency=_TX_COPPER_TRANSPARENCY,
        context=f"{context}.copper[{copper_name}]",
    )


__all__ = [
    "set_imported_object_model_state",
    "style_imported_modeled_objects",
    "style_non_model_objects",
    "validate_modeled_bounds_against_owner",
]

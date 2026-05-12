from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict, cast

from peetsfea.aedt.proxies import create_group, object_bbox
from peetsfea.aedt.protocols import HfssSession, ModelerSession, Object3dRef
from peetsfea.backend.pyaedt.failfast import raise_on_false
from peetsfea.backend.pyaedt.type2_modeled_import_adapter import build_single_imported_modeled_object_entry
from peetsfea.backend.pyaedt.type2_step_import_ledger import (
    ValidatedStepLedger,
    exported_body_outer_bounds_min_xyz,
    exported_body_outer_bounds_size_xyz,
    find_owner_member,
    find_owner_members_by_concrete_prefix,
    member_object_id,
    outer_bounds_min_xyz,
    outer_bounds_size_xyz,
    require_key,
    require_member_objects,
    require_non_empty_str,
    validated_object_names,
)
from peetsfea.backend.pyaedt.type2_step_import_partition import (
    ImportedBodyGroupEntry,
    expected_exported_body_names,
    new_imported_object_names,
    partition_imported_scene_object_names,
    resolve_imported_body_groups,
)
from peetsfea.backend.pyaedt.type2_step_import_style import (
    ensure_underlay_materials,
    set_imported_object_model_state,
    style_imported_modeled_objects,
    style_non_model_objects,
    validate_modeled_bounds_against_owner,
    validate_tx_inner_modeled_bounds_against_actual_region,
)
from peetsfea.backend.pyaedt.type2_step_runtime_common import current_object_names

_TX_FERRITE_GROUP_NAME = "g_ferrite_tx"
_RX_FERRITE_GROUP_NAME = "g_ferrite_rx"
_TX_COPPER_GROUP_NAME = "g_copper_tx"
_RX_COPPER_GROUP_NAME = "g_copper_rx"
_TX_PLATE_COPPER_NAME = "tx_plate_copper"
_RX_PLATE_COPPER_NAME = "rx_plate_copper"
_TX_MERGED_STACK_MEMBER_NAMES: tuple[str, str, str] = (
    "tx_stack_pet_psa",
    "tx_stack_ferrite",
    "tx_stack_air",
)
_RX_MERGED_STACK_MEMBER_NAMES: tuple[str, str, str] = (
    "rx_stack_pet_psa",
    "rx_stack_ferrite",
    "rx_stack_air",
)
_TX_RECT_VOID_COLUMNS_ROLE = "tx_rect_void_columns"


def _assert_imported_object_bounds_match_ledger(
    *,
    modeler: ModelerSession,
    modeled_entry: dict[str, object],
    imported_object_names: list[str],
    context: str,
    tolerance: float = 1e-6,
) -> None:
    expected_min = exported_body_outer_bounds_min_xyz(modeled_entry, context=context)
    expected_size = exported_body_outer_bounds_size_xyz(modeled_entry, context=context)
    if not imported_object_names:
        raise ValueError(f"{context} must include at least one imported modeled object name")
    if tolerance < 0.0:
        raise ValueError("bbox_tolerance must be non-negative")
    imported_bboxes: list[tuple[float, float, float, float, float, float]] = []
    for imported_object_name in imported_object_names:
        object_ref = cast(Object3dRef, modeler.get_object_from_name(imported_object_name))
        raw_bbox = object_bbox(object_ref)
        if isinstance(raw_bbox, (str, bytes)) or not isinstance(raw_bbox, Sequence):
            raise TypeError(f"{context}.imported_object_bboxes[{imported_object_name}] must expose a 6-value bbox")
        if len(raw_bbox) != 6:
            raise ValueError(f"{context}.imported_object_bboxes[{imported_object_name}] must expose 6-value bbox")
        imported_bboxes.append(
            (
                float(raw_bbox[0]),
                float(raw_bbox[1]),
                float(raw_bbox[2]),
                float(raw_bbox[3]),
                float(raw_bbox[4]),
                float(raw_bbox[5]),
            )
        )
    actual_min = (
        min(bbox[0] for bbox in imported_bboxes),
        min(bbox[1] for bbox in imported_bboxes),
        min(bbox[2] for bbox in imported_bboxes),
    )
    actual_max = (
        max(bbox[3] for bbox in imported_bboxes),
        max(bbox[4] for bbox in imported_bboxes),
        max(bbox[5] for bbox in imported_bboxes),
    )
    actual_size = (
        actual_max[0] - actual_min[0],
        actual_max[1] - actual_min[1],
        actual_max[2] - actual_min[2],
    )
    object_id = require_non_empty_str(
        require_key(modeled_entry, key="object_id", context=context),
        context=f"{context}.object_id",
    )
    for axis_index in (0, 1, 2):
        if abs(actual_min[axis_index] - expected_min[axis_index]) > tolerance:
            raise ValueError(
                f"{context} imported body bbox min drift exceeds tolerance ("
                f"object_id={object_id!r}, imported_object_names={imported_object_names}, "
                f"expected_min={expected_min}, actual_min={actual_min}, expected_size={expected_size}, actual_size={actual_size})"
            )
        if abs(actual_size[axis_index] - expected_size[axis_index]) > tolerance:
            raise ValueError(
                f"{context} imported body bbox size drift exceeds tolerance ("
                f"object_id={object_id!r}, imported_object_names={imported_object_names}, "
                f"expected_size={expected_size}, actual_size={actual_size}, expected_min={expected_min}, actual_min={actual_min})"
            )


def _is_tx_branch_stack_member(name: str, *, suffix: str) -> bool:
    if not name.startswith("tx_b") or not name.endswith(suffix):
        return False
    middle = name[len("tx_b") : -len(suffix)]
    return middle.isdigit()


def _is_tx_array_connector_sheet_name(name: str) -> bool:
    for prefix in ("tx_array_input_sheet_s", "tx_array_output_sheet_s"):
        if not name.startswith(prefix):
            continue
        suffix = name[len(prefix):]
        return suffix.isdigit()
    return False


def _is_tx_pre_unite_plate_stack_copper_name(name: str) -> bool:
    return _is_tx_branch_stack_member(name, suffix="_plate_copper") or _is_tx_array_connector_sheet_name(name)


def _expected_imported_scene_names(ledger: ValidatedStepLedger) -> set[str]:
    expected_names: set[str] = set()
    for index, validated_entry in enumerate(ledger["non_model_objects"]):
        member_objects = require_member_objects(validated_entry["entry"], context=f"non_model_objects[{index}]")
        for member_index, member_object in enumerate(member_objects):
            expected_names.add(member_object_id(member_object, context=f"non_model_objects[{index}].member_objects[{member_index}]"))
    for index, validated_entry in enumerate(ledger["modeled_objects"]):
        expected_names.update(expected_exported_body_names(validated_entry["entry"], context=f"modeled_objects[{index}]"))
    return expected_names


def _is_scene_import_wrapper_name(name: str, *, scene_step_path: Path) -> bool:
    scene_stem = scene_step_path.stem
    if name == scene_stem:
        return True
    prefix = f"{scene_stem}_"
    if not name.startswith(prefix):
        return False
    suffix = name[len(prefix):]
    return suffix.isdigit()


def _remove_scene_import_wrapper_names(
    *,
    ledger: ValidatedStepLedger,
    imported_scene_object_names: list[str],
) -> list[str]:
    expected_names = _expected_imported_scene_names(ledger)
    wrapper_names = [
        name
        for name in imported_scene_object_names
        if name not in expected_names and _is_scene_import_wrapper_name(name, scene_step_path=ledger["scene_step_path"])
    ]
    if not wrapper_names:
        return imported_scene_object_names
    filtered_names = [name for name in imported_scene_object_names if name not in wrapper_names]
    if not filtered_names:
        raise RuntimeError(
            "scene STEP import produced only wrapper group names and no ledger-owned bodies "
            f"(scene_step_path={ledger['scene_step_path']}, wrapper_names={wrapper_names})"
        )
    return filtered_names


def _is_legacy_ferrite_family_name_for_plate_stack(name: str) -> bool:
    return name.startswith(
        (
            "tx_underlay_ferrite_u",
            "tx_underlay_pet_psa_u",
            "tx_underlay_air_u",
            "tx_wall_ferrite_u",
            "tx_wall_pet_psa_u",
            "tx_wall_air_u",
            "under_rx_ferrite_u",
            "under_rx_pet_psa_u",
            "under_rx_air_u",
        )
    )


def _is_legacy_copper_segment_name_for_plate_stack(name: str) -> bool:
    return name.startswith(
        (
            "tx_copper_wall_t",
            "tx_copper_coil_t",
            "tx_bridge_s",
            "tx_stub_",
            "rx_copper_wall_t",
            "rx_copper_coil_t",
            "rx_bridge_s",
            "rx_stub_",
        )
    )


class Type2ImportedLedger(TypedDict):
    source_toml_path: str
    source_step_ledger_path: str
    scene_step_path: str
    seed: int
    aedt_path: str
    imported_ledger_path: str
    non_model_objects: list[dict[str, object]]
    modeled_objects: list[dict[str, object]]


_TV_ALUMINUM_PLATE_ROLE = "tv_aluminum_plate"
_TV_ALUMINUM_PLATE_BODY_NAME = "tv_aluminum_plate"


def _require_plate_stack_merged_material_contract(*, modeled_entry: dict[str, object], context: str) -> None:
    role = require_non_empty_str(require_key(modeled_entry, key="role", context=context), context=f"{context}.role")
    if role not in ("tx_plate_stack", "rx_plate_stack"):
        return
    expected_member_names: tuple[str, str, str]
    expected_group_name: str
    if role == "tx_plate_stack":
        expected_member_names = _TX_MERGED_STACK_MEMBER_NAMES
        expected_group_name = _TX_FERRITE_GROUP_NAME
        expected_copper_group_name = _TX_COPPER_GROUP_NAME
        required_plate_copper_name = _TX_PLATE_COPPER_NAME
    else:
        expected_member_names = _RX_MERGED_STACK_MEMBER_NAMES
        expected_group_name = _RX_FERRITE_GROUP_NAME
        expected_copper_group_name = _RX_COPPER_GROUP_NAME
        required_plate_copper_name = _RX_PLATE_COPPER_NAME
    expected_exported_body_names = validated_object_names(
        cast(
            Sequence[object],
            require_key(modeled_entry, key="expected_exported_body_names", context=context),
        ),
        context=f"{context}.expected_exported_body_names",
    )
    expected_name_set = set(expected_exported_body_names)
    if role == "tx_plate_stack":
        ferrite_names = [name for name in expected_exported_body_names if name.endswith("_stack_ferrite")]
        pet_psa_names = [name for name in expected_exported_body_names if name.endswith("_stack_pet_psa")]
        air_names = [name for name in expected_exported_body_names if name.endswith("_stack_air")]
        if len(ferrite_names) < 1 or len(pet_psa_names) < 1 or len(air_names) < 1:
            raise ValueError(
                f"{context}.expected_exported_body_names must include tx plate-stack ferrite-family members "
                f"(ferrite={ferrite_names}, pet_psa={pet_psa_names}, air={air_names})"
            )
        if len(ferrite_names) != len(pet_psa_names) or len(ferrite_names) != len(air_names):
            raise ValueError(
                f"{context}.expected_exported_body_names must include balanced tx branch ferrite-family members "
                f"(ferrite={len(ferrite_names)}, pet_psa={len(pet_psa_names)}, air={len(air_names)})"
            )
    else:
        missing_merged_member_names = [name for name in expected_member_names if name not in expected_name_set]
        if missing_merged_member_names:
            raise ValueError(
                f"{context}.expected_exported_body_names must include merged plate-stack material members for {role} "
                f"(missing={missing_merged_member_names}, actual={expected_exported_body_names})"
            )
    legacy_ferrite_member_names = [
        name for name in expected_exported_body_names if _is_legacy_ferrite_family_name_for_plate_stack(name)
    ]
    if legacy_ferrite_member_names:
        raise ValueError(
            f"{context}.expected_exported_body_names contains legacy/import-expanded ferrite-family names for {role}; "
            "this import path only accepts merged exact ferrite-family names "
            f"(legacy_names={legacy_ferrite_member_names}, required={list(expected_member_names)})"
        )
    if role == "tx_plate_stack":
        pcb_wall_names = [name for name in expected_exported_body_names if name == "tx_pcb_wall" or _is_tx_branch_stack_member(name, suffix="_pcb_wall")]
        pcb_coil_names = [name for name in expected_exported_body_names if name == "tx_pcb_coil" or _is_tx_branch_stack_member(name, suffix="_pcb_coil")]
        if len(pcb_wall_names) < 1 or len(pcb_coil_names) < 1:
            raise ValueError(
                f"{context}.expected_exported_body_names must retain tx plate-stack pcb wall/coil bodies "
                f"(pcb_wall={pcb_wall_names}, pcb_coil={pcb_coil_names}, actual={expected_exported_body_names})"
            )
        if len(pcb_wall_names) != len(pcb_coil_names):
            raise ValueError(
                f"{context}.expected_exported_body_names must retain balanced tx plate-stack pcb wall/coil counts "
                f"(pcb_wall={len(pcb_wall_names)}, pcb_coil={len(pcb_coil_names)})"
            )
        if required_plate_copper_name not in expected_name_set:
            raise ValueError(
                f"{context}.expected_exported_body_names must retain required final plate-stack bodies for {role} "
                f"(actual={expected_exported_body_names})"
            )
        tx_pre_unite_copper_names = [
            name for name in expected_exported_body_names if _is_tx_pre_unite_plate_stack_copper_name(name)
        ]
        if tx_pre_unite_copper_names:
            raise ValueError(
                f"{context}.expected_exported_body_names contains pre-unite tx copper leakage for {role}; "
                "final imported conductors must use united plate copper names only "
                f"(leaked_names={tx_pre_unite_copper_names})"
            )
    else:
        required_exact_names = (
            "rx_pcb_wall",
            "rx_pcb_coil",
            required_plate_copper_name,
        )
        missing_exact_names = [name for name in required_exact_names if name not in expected_name_set]
        if missing_exact_names:
            raise ValueError(
                f"{context}.expected_exported_body_names must retain required final plate-stack bodies for {role} "
                f"(missing={missing_exact_names}, actual={expected_exported_body_names})"
            )
    legacy_segment_names = [
        name for name in expected_exported_body_names if _is_legacy_copper_segment_name_for_plate_stack(name)
    ]
    if legacy_segment_names:
        raise ValueError(
            f"{context}.expected_exported_body_names contains legacy plate-stack copper segment names for {role}; "
            "final imported conductors must use united plate copper names only "
            f"(legacy_names={legacy_segment_names})"
        )
    raw_groups = require_key(modeled_entry, key="expected_exported_body_groups", context=context)
    if not isinstance(raw_groups, list):
        raise TypeError(f"{context}.expected_exported_body_groups must be a list")
    if len(raw_groups) != 2:
        raise ValueError(
            f"{context}.expected_exported_body_groups must contain copper and ferrite groups for {role} "
            f"(actual={len(raw_groups)})"
        )
    raw_copper_group = raw_groups[0]
    if not isinstance(raw_copper_group, dict):
        raise TypeError(f"{context}.expected_exported_body_groups[0] must be a table/object")
    copper_group_name = require_non_empty_str(
        require_key(raw_copper_group, key="group_name", context=f"{context}.expected_exported_body_groups[0]"),
        context=f"{context}.expected_exported_body_groups[0].group_name",
    )
    if copper_group_name != expected_copper_group_name:
        raise ValueError(
            f"{context}.expected_exported_body_groups[0].group_name must be {expected_copper_group_name!r} "
            f"(actual={copper_group_name!r})"
        )
    copper_group_member_names = validated_object_names(
        cast(
            Sequence[object],
            require_key(raw_copper_group, key="member_body_names", context=f"{context}.expected_exported_body_groups[0]"),
        ),
        context=f"{context}.expected_exported_body_groups[0].member_body_names",
    )
    if role == "tx_plate_stack":
        expected_copper_group_member_names = [required_plate_copper_name]
    else:
        expected_copper_group_member_names = [required_plate_copper_name]
    if copper_group_member_names != expected_copper_group_member_names:
        raise ValueError(
            f"{context}.expected_exported_body_groups[0].member_body_names must match plate copper group contract "
            f"(expected={expected_copper_group_member_names}, actual={copper_group_member_names})"
        )

    raw_ferrite_group = raw_groups[1]
    if not isinstance(raw_ferrite_group, dict):
        raise TypeError(f"{context}.expected_exported_body_groups[1] must be a table/object")
    ferrite_group_name = require_non_empty_str(
        require_key(raw_ferrite_group, key="group_name", context=f"{context}.expected_exported_body_groups[1]"),
        context=f"{context}.expected_exported_body_groups[1].group_name",
    )
    if ferrite_group_name != expected_group_name:
        raise ValueError(
            f"{context}.expected_exported_body_groups[1].group_name must be {expected_group_name!r} "
            f"(actual={ferrite_group_name!r})"
        )
    ferrite_group_member_names = validated_object_names(
        cast(
            Sequence[object],
            require_key(raw_ferrite_group, key="member_body_names", context=f"{context}.expected_exported_body_groups[1]"),
        ),
        context=f"{context}.expected_exported_body_groups[1].member_body_names",
    )
    if role == "tx_plate_stack":
        ferrite_count = len([name for name in ferrite_group_member_names if name.endswith("_stack_ferrite")])
        pet_psa_count = len([name for name in ferrite_group_member_names if name.endswith("_stack_pet_psa")])
        air_count = len([name for name in ferrite_group_member_names if name.endswith("_stack_air")])
        if ferrite_count < 1 or pet_psa_count < 1 or air_count < 1:
            raise ValueError(
                f"{context}.expected_exported_body_groups[1].member_body_names must include tx plate-stack ferrite-family members "
                f"(ferrite={ferrite_count}, pet_psa={pet_psa_count}, air={air_count})"
            )
        if ferrite_count != pet_psa_count or ferrite_count != air_count:
            raise ValueError(
                f"{context}.expected_exported_body_groups[1].member_body_names must include balanced tx branch ferrite-family members "
                f"(ferrite={ferrite_count}, pet_psa={pet_psa_count}, air={air_count})"
            )
    elif ferrite_group_member_names != list(expected_member_names):
        raise ValueError(
            f"{context}.expected_exported_body_groups[1].member_body_names must match merged plate-stack material contract "
            f"(expected={list(expected_member_names)}, actual={ferrite_group_member_names})"
        )


def _import_scene_step(
    *,
    modeler: ModelerSession,
    step_path: Path,
    object_id: str,
) -> list[str]:
    before_import = current_object_names(modeler, context=f"{object_id}.before_import")
    import_result = modeler.import_3d_cad(input_file=step_path, import_free_surfaces=False, create_group=False)
    raise_on_false(import_result, operation="import_3d_cad", context={"object_id": object_id, "input_file": str(step_path)})
    if not isinstance(import_result, bool):
        raise TypeError(f"Modeler3D.import_3d_cad must return bool (actual={type(import_result).__name__})")
    after_import = current_object_names(modeler, context=f"{object_id}.after_import")
    return new_imported_object_names(
        before_import=before_import,
        after_import=after_import,
        step_path=step_path,
    )


def _imported_names_from_adapter_entry(entry: dict[str, object]) -> list[str]:
    raw_imported_names = require_key(
        entry,
        key="imported_object_names",
        context="imported_modeled_object_entry",
    )
    if isinstance(raw_imported_names, (str, bytes)) or not isinstance(raw_imported_names, Sequence):
        raise TypeError("imported_modeled_object_entry.imported_object_names must be a sequence of strings")
    return validated_object_names(
        cast(Sequence[object], raw_imported_names),
        context="imported_modeled_object_entry",
    )


def _merge_modeled_adapter_entry(
    *,
    export_entry: dict[str, object],
    adapter_entry: dict[str, object],
    imported_body_groups: list[ImportedBodyGroupEntry],
) -> dict[str, object]:
    merged = dict(export_entry)
    merged["imported_object_names"] = _imported_names_from_adapter_entry(adapter_entry)
    merged["imported_body_groups"] = imported_body_groups
    return merged


def _merge_tv_aluminum_plate_entry(
    *,
    export_entry: dict[str, object],
    imported_object_names: list[str],
    imported_body_groups: list[ImportedBodyGroupEntry],
    context: str,
) -> dict[str, object]:
    if imported_object_names != [_TV_ALUMINUM_PLATE_BODY_NAME]:
        raise ValueError(
            f"{context} requires exactly one imported tv aluminum plate body "
            f"(expected={[_TV_ALUMINUM_PLATE_BODY_NAME]}, actual={imported_object_names})"
        )
    if imported_body_groups:
        raise ValueError(
            f"{context}.imported_body_groups must be empty for tv_aluminum_plate "
            f"(actual={imported_body_groups})"
        )
    merged = dict(export_entry)
    merged["imported_object_names"] = list(imported_object_names)
    merged["imported_body_groups"] = []
    return merged


def _recreate_imported_body_groups(
    *,
    modeler: ModelerSession,
    modeled_entry: dict[str, object],
    imported_object_names: list[str],
    context: str,
) -> list[ImportedBodyGroupEntry]:
    imported_body_groups = resolve_imported_body_groups(
        modeled_entry=modeled_entry,
        imported_object_names=imported_object_names,
        context=context,
    )
    recreated_groups: list[ImportedBodyGroupEntry] = []
    recreated_group_names: set[str] = set()
    for group_entry in imported_body_groups:
        if group_entry["group_name"] in recreated_group_names:
            raise ValueError(
                f"{context}.imported_body_groups contains duplicate group_name "
                f"(group_name={group_entry['group_name']!r})"
            )
        recreated_group_names.add(group_entry["group_name"])
        created_group_name = create_group(
            modeler,
            objects=list(group_entry["member_object_names"]),
            group_name=group_entry["group_name"],
        )
        if created_group_name != group_entry["group_name"]:
            raise RuntimeError(
                f"{context} recreated body group name drifted after HFSS create_group "
                f"(requested={group_entry['group_name']!r}, actual={created_group_name!r})"
            )
        recreated_groups.append(
            {
                "group_name": created_group_name,
                "member_object_names": group_entry["member_object_names"],
            }
        )
    return recreated_groups


def _all_imported_modeled_object_names(modeled_names_by_object_id: dict[str, list[str]]) -> list[str]:
    imported_object_names: list[str] = []
    for object_id, modeled_object_names in modeled_names_by_object_id.items():
        if not modeled_object_names:
            raise ValueError(f"modeled import partition must claim at least one body per modeled object (object_id={object_id})")
        imported_object_names.extend(modeled_object_names)
    return imported_object_names


def _union_owner_member(
    owner_members: list[dict[str, object]],
    *,
    owner_id: str,
    context: str,
) -> dict[str, object]:
    if len(owner_members) == 0:
        raise ValueError(f"{context} requires at least one concrete owner member for {owner_id}")
    min_points: list[tuple[float, float, float]] = []
    max_points: list[tuple[float, float, float]] = []
    for index, owner_member in enumerate(owner_members):
        member_context = f"{context}.owner_members[{index}]"
        min_x, min_y, min_z = outer_bounds_min_xyz(owner_member, context=member_context)
        size_x, size_y, size_z = outer_bounds_size_xyz(owner_member, context=member_context)
        min_points.append((min_x, min_y, min_z))
        max_points.append((min_x + size_x, min_y + size_y, min_z + size_z))
    union_min = (
        min(point[0] for point in min_points),
        min(point[1] for point in min_points),
        min(point[2] for point in min_points),
    )
    union_max = (
        max(point[0] for point in max_points),
        max(point[1] for point in max_points),
        max(point[2] for point in max_points),
    )
    union_size = (
        union_max[0] - union_min[0],
        union_max[1] - union_min[1],
        union_max[2] - union_min[2],
    )
    return {
        "object_id": owner_id,
        "role": owner_id,
        "canonical_coordinates": {
            "frame_origin_xyz": union_min,
            "outer_bounds_min_xyz": union_min,
            "outer_bounds_max_xyz": union_max,
            "outer_bounds_size_xyz": union_size,
        },
    }


def build_imported_ledger(
    *,
    hfss: HfssSession,
    step_ledger_path: Path,
    output_aedt_path: Path,
    imported_ledger_path: Path,
    ledger: ValidatedStepLedger,
) -> Type2ImportedLedger:
    modeler = hfss.modeler
    imported_scene_object_names = _import_scene_step(
        modeler=modeler,
        step_path=ledger["scene_step_path"],
        object_id="type2_scene",
    )
    imported_scene_object_names = _remove_scene_import_wrapper_names(
        ledger=ledger,
        imported_scene_object_names=imported_scene_object_names,
    )
    non_model_names_by_object_id, modeled_names_by_object_id = partition_imported_scene_object_names(
        ledger=ledger,
        imported_object_names=imported_scene_object_names,
    )
    ensure_underlay_materials(
        hfss,
        imported_modeled_object_names=_all_imported_modeled_object_names(modeled_names_by_object_id),
    )

    imported_non_model_objects: list[dict[str, object]] = []
    for validated_entry in ledger["non_model_objects"]:
        imported_object_names = non_model_names_by_object_id[validated_entry["object_id"]]
        set_imported_object_model_state(
            modeler=modeler,
            object_id=validated_entry["object_id"],
            imported_object_names=imported_object_names,
            model_state=False,
        )
        style_non_model_objects(
            modeler=modeler,
            object_id=validated_entry["object_id"],
            imported_object_names=imported_object_names,
        )
        imported_entry = dict(validated_entry["entry"])
        imported_entry["imported_object_names"] = imported_object_names
        imported_non_model_objects.append(imported_entry)

    imported_modeled_objects: list[dict[str, object]] = []
    for index, validated_entry in enumerate(ledger["modeled_objects"]):
        context = f"modeled_objects[{index}]"
        _require_plate_stack_merged_material_contract(modeled_entry=validated_entry["entry"], context=context)
        owner_id = require_non_empty_str(
            require_key(validated_entry["entry"], key="placement_owner_id", context=context),
            context=f"{context}.placement_owner_id",
        )
        role = require_non_empty_str(
            require_key(validated_entry["entry"], key="role", context=context),
            context=f"{context}.role",
        )
        if role == _TX_RECT_VOID_COLUMNS_ROLE:
            owner_member = _union_owner_member(
                find_owner_members_by_concrete_prefix(ledger["non_model_objects"], object_id=owner_id),
                owner_id=owner_id,
                context=context,
            )
        else:
            owner_member = find_owner_member(ledger["non_model_objects"], object_id=owner_id)
        if role == "tx_inner_single_coil":
            validate_tx_inner_modeled_bounds_against_actual_region(
                modeled_entry=validated_entry["entry"],
                owner_member=owner_member,
                actual_region_member=find_owner_member(ledger["non_model_objects"], object_id="tx_inner_actual_region"),
                context=context,
            )
        else:
            validate_modeled_bounds_against_owner(
                modeled_entry=validated_entry["entry"],
                owner_member=owner_member,
                context=context,
            )
        imported_object_names = modeled_names_by_object_id[validated_entry["object_id"]]
        set_imported_object_model_state(
            modeler=modeler,
            object_id=validated_entry["object_id"],
            imported_object_names=imported_object_names,
            model_state=True,
        )
        _assert_imported_object_bounds_match_ledger(
            modeler=modeler,
            modeled_entry=validated_entry["entry"],
            imported_object_names=imported_object_names,
            context=context,
        )
        final_imported_object_names = style_imported_modeled_objects(
            modeler=modeler,
            modeled_entry=validated_entry["entry"],
            imported_object_names=imported_object_names,
            context=context,
        )
        imported_body_groups = _recreate_imported_body_groups(
            modeler=modeler,
            modeled_entry=validated_entry["entry"],
            imported_object_names=final_imported_object_names,
            context=context,
        )
        if role == _TV_ALUMINUM_PLATE_ROLE:
            imported_modeled_objects.append(
                _merge_tv_aluminum_plate_entry(
                    export_entry=validated_entry["entry"],
                    imported_object_names=final_imported_object_names,
                    imported_body_groups=imported_body_groups,
                    context=context,
                )
            )
        else:
            adapter_entry = build_single_imported_modeled_object_entry(
                modeled_object=validated_entry["entry"],
                imported_object_names=final_imported_object_names,
            )
            imported_modeled_objects.append(
                _merge_modeled_adapter_entry(
                    export_entry=validated_entry["entry"],
                    adapter_entry=cast(dict[str, object], adapter_entry),
                    imported_body_groups=imported_body_groups,
                )
            )

    return {
        "source_toml_path": ledger["source_toml_path"],
        "source_step_ledger_path": str(step_ledger_path),
        "scene_step_path": str(ledger["scene_step_path"]),
        "seed": ledger["seed"],
        "aedt_path": str(output_aedt_path),
        "imported_ledger_path": str(imported_ledger_path),
        "non_model_objects": imported_non_model_objects,
        "modeled_objects": imported_modeled_objects,
    }


def write_imported_ledger(*, imported_ledger_path: Path, imported_ledger: Type2ImportedLedger) -> None:
    imported_ledger_path.parent.mkdir(parents=True, exist_ok=True)
    imported_ledger_path.write_text(json.dumps(imported_ledger, ensure_ascii=False, indent=2), encoding="utf-8")


__all__ = [
    "Type2ImportedLedger",
    "build_imported_ledger",
    "write_imported_ledger",
]

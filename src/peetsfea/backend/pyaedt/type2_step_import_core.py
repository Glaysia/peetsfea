from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict, cast

from peetsfea.aedt.proxies import cover_lines, create_group, create_polyline
from peetsfea.aedt.protocols import HfssSession, ModelerSession
from peetsfea.backend.pyaedt.failfast import raise_on_false
from peetsfea.backend.pyaedt.type2_modeled_import_adapter import build_single_imported_modeled_object_entry
from peetsfea.backend.pyaedt.type2_step_import_ledger import (
    ValidatedStepLedger,
    find_owner_member,
    member_object_id,
    require_float_triplet,
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


def _is_tx_array_copper_name(name: str) -> bool:
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


def _covered_sheet_name(covered: object, *, expected_name: str, context: str) -> str:
    if covered is True:
        return expected_name
    if isinstance(covered, str):
        return require_non_empty_str(covered, context=f"{context}.covered_name")
    if isinstance(covered, list):
        if len(covered) != 1:
            raise RuntimeError(f"{context}.cover_lines result list must contain exactly one item (actual={len(covered)})")
        first = covered[0]
        if isinstance(first, str):
            return require_non_empty_str(first, context=f"{context}.covered_name")
        assert hasattr(first, "name"), f"{context}.cover_lines result object must expose name"
        first_name = getattr(first, "name")
        return require_non_empty_str(first_name, context=f"{context}.covered_name")
    assert hasattr(covered, "name"), f"{context}.cover_lines result must expose name"
    raw_name = getattr(covered, "name")
    return require_non_empty_str(raw_name, context=f"{context}.covered_name")


def _required_sheet_vertices(
    value: object,
    *,
    context: str,
) -> tuple[tuple[float, float, float], ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise TypeError(f"{context} must be a list of 3D vertices")
    vertices: list[tuple[float, float, float]] = []
    for index, raw_vertex in enumerate(value):
        vertices.append(require_float_triplet(raw_vertex, context=f"{context}[{index}]"))
    if len(vertices) != 4:
        raise ValueError(f"{context} must contain exactly 4 vertices")
    return tuple(vertices)


def _connector_sheet_vertices_by_name(
    *,
    modeled_entry: dict[str, object],
    connector_sheet_names: list[str],
    context: str,
) -> dict[str, tuple[tuple[float, float, float], ...]]:
    raw_coordinates = require_key(modeled_entry, key="canonical_coordinates", context=context)
    assert isinstance(raw_coordinates, dict), f"{context}.canonical_coordinates must be a table/object"
    raw_vertices_by_name = require_key(
        raw_coordinates,
        key="connector_sheet_vertices_xyz_by_name",
        context=f"{context}.canonical_coordinates",
    )
    assert isinstance(raw_vertices_by_name, dict), (
        f"{context}.canonical_coordinates.connector_sheet_vertices_xyz_by_name must be a table/object"
    )
    vertices_by_name: dict[str, tuple[tuple[float, float, float], ...]] = {}
    for sheet_name in connector_sheet_names:
        if sheet_name not in raw_vertices_by_name:
            raise ValueError(
                f"{context}.canonical_coordinates.connector_sheet_vertices_xyz_by_name is missing "
                f"required connector sheet vertices (sheet_name={sheet_name!r})"
            )
        vertices_by_name[sheet_name] = _required_sheet_vertices(
            raw_vertices_by_name[sheet_name],
            context=f"{context}.canonical_coordinates.connector_sheet_vertices_xyz_by_name[{sheet_name}]",
        )
    return vertices_by_name


def _create_connector_sheet(
    *,
    modeler: ModelerSession,
    sheet_name: str,
    vertices_xyz: tuple[tuple[float, float, float], ...],
    context: str,
) -> str:
    polyline_created = create_polyline(
        modeler,
        points=[[x, y, z] for x, y, z in vertices_xyz],
        name=sheet_name,
        material="copper",
        close_surface=True,
        cover_surface=False,
    )
    assert hasattr(polyline_created, "name"), f"{context}.create_polyline result must expose name"
    raw_loop_name = getattr(polyline_created, "name")
    loop_name = require_non_empty_str(raw_loop_name, context=f"{context}.loop_name")
    if loop_name != sheet_name:
        raise RuntimeError(
            f"{context}.create_polyline name drifted for TX array connector sheet "
            f"(requested={sheet_name!r}, actual={loop_name!r})"
        )
    covered = cover_lines(modeler, assignment=loop_name)
    covered_name = _covered_sheet_name(covered, expected_name=sheet_name, context=f"{context}[{sheet_name}]")
    if covered_name != sheet_name:
        raise RuntimeError(
            f"{context}.cover_lines name drifted for TX array connector sheet "
            f"(requested={sheet_name!r}, actual={covered_name!r})"
        )
    return covered_name


def _reconstruct_tx_array_connector_sheets(
    *,
    modeler: ModelerSession,
    ledger: ValidatedStepLedger,
    imported_scene_object_names: list[str],
) -> list[str]:
    reconstructed_names = list(imported_scene_object_names)
    claimed_names = set(reconstructed_names)
    for index, validated_entry in enumerate(ledger["modeled_objects"]):
        context = f"modeled_objects[{index}]"
        modeled_entry = validated_entry["entry"]
        role = require_non_empty_str(require_key(modeled_entry, key="role", context=context), context=f"{context}.role")
        if role != "tx_plate_stack":
            continue
        expected_names = expected_exported_body_names(modeled_entry, context=context)
        connector_sheet_names = [name for name in expected_names if _is_tx_array_connector_sheet_name(name)]
        if not connector_sheet_names:
            continue
        already_imported_connector_names = [name for name in connector_sheet_names if name in claimed_names]
        if already_imported_connector_names:
            raise ValueError(
                "TX array connector sheets must be reconstructed from canonical ledger vertices, "
                "not imported as STEP free-surface shells "
                f"(already_imported={already_imported_connector_names})"
            )
        vertices_by_name = _connector_sheet_vertices_by_name(
            modeled_entry=modeled_entry,
            connector_sheet_names=connector_sheet_names,
            context=context,
        )
        for sheet_name in connector_sheet_names:
            created_name = _create_connector_sheet(
                modeler=modeler,
                sheet_name=sheet_name,
                vertices_xyz=vertices_by_name[sheet_name],
                context=f"{context}.tx_array_connector_sheet",
            )
            if created_name in claimed_names:
                raise RuntimeError(
                    "TX array connector sheet reconstruction produced a duplicate object name "
                    f"(sheet_name={created_name!r})"
                )
            reconstructed_names.append(created_name)
            claimed_names.add(created_name)
    return reconstructed_names


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


def _require_plate_stack_merged_material_contract(*, modeled_entry: dict[str, object], context: str) -> None:
    role = require_non_empty_str(require_key(modeled_entry, key="role", context=context), context=f"{context}.role")
    if role not in ("tx_plate_stack", "rx_plate_stack"):
        return
    expected_member_names: tuple[str, str, str]
    expected_group_name: str
    role_prefix: str
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
        tx_copper_names = [
            name for name in expected_exported_body_names if name == required_plate_copper_name or _is_tx_array_copper_name(name)
        ]
        if not tx_copper_names:
            raise ValueError(
                f"{context}.expected_exported_body_names must retain tx plate-stack copper bodies for {role} "
                f"(actual={expected_exported_body_names})"
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
        expected_copper_group_member_names = tx_copper_names
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
    imported_scene_object_names = _reconstruct_tx_array_connector_sheets(
        modeler=modeler,
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
        owner_member = find_owner_member(ledger["non_model_objects"], object_id=owner_id)
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

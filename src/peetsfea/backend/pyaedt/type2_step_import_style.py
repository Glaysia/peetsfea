from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import cast

from peetsfea.aedt.failfast import raise_on_false, validate_aedt_name
from peetsfea.aedt.proxies import cover_lines, create_polyline, set_object_color, set_object_transparency
from peetsfea.aedt.protocols import HfssSession, MaterialsSession, ModelerSession
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
_TX_UNDERLAY_FERRITE_NAME_PREFIX = "tx_underlay_ferrite_u"
_TX_UNDERLAY_PET_PSA_NAME_PREFIX = "tx_underlay_pet_psa_u"
_TX_UNDERLAY_AIR_NAME_PREFIX = "tx_underlay_air_u"
_TX_VOID_FERRITE_NAME_PREFIX = "tx_void_ferrite_u"
_TX_VOID_PET_PSA_NAME_PREFIX = "tx_void_pet_psa_u"
_TX_OUTER_VOID_FERRITE_NAME_PREFIX = "tx_outer_void_ferrite_u"
_TX_OUTER_VOID_PET_PSA_NAME_PREFIX = "tx_outer_void_pet_psa_u"
_TX_OUTER_UNDERLAY_FERRITE_NAME_PREFIX = "tx_outer_underlay_ferrite_u"
_TX_OUTER_UNDERLAY_PET_PSA_NAME_PREFIX = "tx_outer_underlay_pet_psa_u"
_TX_WALL_FERRITE_NAME_PREFIX = "tx_wall_ferrite_u"
_TX_WALL_PET_PSA_NAME_PREFIX = "tx_wall_pet_psa_u"
_TX_WALL_AIR_NAME_PREFIX = "tx_wall_air_u"
_TX_STACK_FERRITE_NAME = "tx_stack_ferrite"
_TX_STACK_PET_PSA_NAME = "tx_stack_pet_psa"
_TX_STACK_AIR_NAME = "tx_stack_air"
_RX_UNDERLAY_FERRITE_NAME_PREFIX = "under_rx_ferrite_u"
_RX_UNDERLAY_PET_PSA_NAME_PREFIX = "under_rx_pet_psa_u"
_RX_UNDERLAY_AIR_NAME_PREFIX = "under_rx_air_u"
_RX_STACK_FERRITE_NAME = "rx_stack_ferrite"
_RX_STACK_PET_PSA_NAME = "rx_stack_pet_psa"
_RX_STACK_AIR_NAME = "rx_stack_air"
_UNDERLAY_FERRITE_NAME_PREFIXES = (
    _TX_UNDERLAY_FERRITE_NAME_PREFIX,
    _TX_VOID_FERRITE_NAME_PREFIX,
    _TX_OUTER_VOID_FERRITE_NAME_PREFIX,
    _TX_OUTER_UNDERLAY_FERRITE_NAME_PREFIX,
    _TX_WALL_FERRITE_NAME_PREFIX,
    _RX_UNDERLAY_FERRITE_NAME_PREFIX,
)
_UNDERLAY_PET_PSA_NAME_PREFIXES = (
    _TX_UNDERLAY_PET_PSA_NAME_PREFIX,
    _TX_VOID_PET_PSA_NAME_PREFIX,
    _TX_OUTER_VOID_PET_PSA_NAME_PREFIX,
    _TX_OUTER_UNDERLAY_PET_PSA_NAME_PREFIX,
    _TX_WALL_PET_PSA_NAME_PREFIX,
    _RX_UNDERLAY_PET_PSA_NAME_PREFIX,
)
_UNDERLAY_AIR_NAME_PREFIXES = (
    _TX_UNDERLAY_AIR_NAME_PREFIX,
    _TX_WALL_AIR_NAME_PREFIX,
    _RX_UNDERLAY_AIR_NAME_PREFIX,
)
_TX_UNDERLAY_FERRITE_COLOR = (89, 94, 107)
_TX_UNDERLAY_FERRITE_TRANSPARENCY = 0.0
_TX_UNDERLAY_PET_PSA_COLOR = (227, 205, 120)
_TX_UNDERLAY_PET_PSA_TRANSPARENCY = 0.55
_TX_UNDERLAY_AIR_COLOR = (180, 215, 255)
_TX_UNDERLAY_AIR_TRANSPARENCY = 0.88
_PET_PSA_MATERIAL = "PET_PSA"
_PET_PSA_PERMITTIVITY = "2.8"
_DATASET_FERRITE_MATERIAL = "MULL12060ferrite"
_DATASET_FERRITE_APPEARANCE_RGB = (89, 94, 107)
_NOTEBOOK_DATASET_IMPORT_PATH = Path(__file__).resolve().parents[4] / "notebooks" / "mu_p.tab"
_MU_R_REAL_DATASET_NAME = "$mu_r_real"
_MU_TAND_M_DATASET_NAME = "$mu_tand_m"
_MU_R_REAL_DATASET_POINTS = (
    (0.001, 133.0),
    (0.003, 134.0),
    (0.005, 135.0),
    (0.008, 136.0),
    (0.01, 137.0),
    (0.012, 142.0),
    (0.015, 152.0),
    (0.018, 160.0),
    (0.02, 166.0),
    (0.025, 150.0),
    (0.03, 130.0),
    (0.04, 100.0),
    (0.05, 82.0),
    (0.07, 65.0),
    (0.1, 50.0),
    (0.15, 35.0),
    (0.2, 25.0),
    (0.3, 15.0),
    (0.5, 10.0),
    (0.7, 11.0),
    (1.0, 18.0),
)
_MU_TAND_M_DATASET_POINTS = (
    (0.001, 0.0),
    (0.003, 0.0),
    (0.005, 0.0),
    (0.008, 0.00367647),
    (0.01, 0.00729927),
    (0.012, 0.0140845),
    (0.015, 0.0328947),
    (0.018, 0.075),
    (0.02, 0.150602),
    (0.025, 0.4),
    (0.03, 0.553846),
    (0.04, 0.76),
    (0.05, 0.890244),
    (0.07, 1.01538),
    (0.1, 1.16),
    (0.15, 1.42857),
    (0.2, 1.8),
    (0.3, 2.46667),
    (0.5, 2.8),
    (0.7, 2.0),
    (1.0, 1.0),
)
_PLACEMENT_TOLERANCE = 1e-9
_PLATE_STACK_STUB_LENGTH_MM = 5.0


def _is_tx_branch_stack_member(name: str, *, suffix: str) -> bool:
    if not name.startswith("tx_b") or not name.endswith(suffix):
        return False
    middle = name[len("tx_b") : -len(suffix)]
    return middle.isdigit()


def _is_tx_plate_stack_array_expected_name(name: str) -> bool:
    return any(
        _is_tx_branch_stack_member(name, suffix=suffix)
        for suffix in (
            "_pcb_wall",
            "_pcb_coil",
            "_stack_pet_psa",
            "_stack_ferrite",
            "_stack_air",
        )
    )


def _is_ferrite_family_name(name: str) -> bool:
    return name.startswith(_UNDERLAY_FERRITE_NAME_PREFIXES) or name in (
        _TX_STACK_FERRITE_NAME,
        _RX_STACK_FERRITE_NAME,
    ) or _is_tx_branch_stack_member(name, suffix="_stack_ferrite")


def _is_pet_psa_family_name(name: str) -> bool:
    return name.startswith(_UNDERLAY_PET_PSA_NAME_PREFIXES) or name in (
        _TX_STACK_PET_PSA_NAME,
        _RX_STACK_PET_PSA_NAME,
    ) or _is_tx_branch_stack_member(name, suffix="_stack_pet_psa")


def _is_air_family_name(name: str) -> bool:
    return name.startswith(_UNDERLAY_AIR_NAME_PREFIXES) or name in (
        _TX_STACK_AIR_NAME,
        _RX_STACK_AIR_NAME,
    ) or _is_tx_branch_stack_member(name, suffix="_stack_air")


def _require_non_negative_float(value: object, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{context} must be number")
    checked_value = float(value)
    if checked_value < 0.0:
        raise ValueError(f"{context} must be >= 0")
    return checked_value


def _tx_outer_tilt_allowances_mm(*, modeled_entry: dict[str, object], context: str) -> tuple[float, float]:
    raw_canonical_coordinates = require_key(
        modeled_entry,
        key="canonical_coordinates",
        context=context,
    )
    if not isinstance(raw_canonical_coordinates, dict):
        raise TypeError(f"{context}.canonical_coordinates must be an object/table")
    if "outer_tilt_metadata" not in raw_canonical_coordinates:
        return (0.0, 0.0)
    raw_outer_tilt_metadata = require_key(
        raw_canonical_coordinates,
        key="outer_tilt_metadata",
        context=f"{context}.canonical_coordinates",
    )
    if not isinstance(raw_outer_tilt_metadata, dict):
        raise TypeError(f"{context}.canonical_coordinates.outer_tilt_metadata must be an object/table")
    raw_max_world_x_protrusion_mm = require_key(
        raw_outer_tilt_metadata,
        key="max_world_x_protrusion_mm",
        context=f"{context}.canonical_coordinates.outer_tilt_metadata",
    )
    raw_max_world_z_underhang_mm = require_key(
        raw_outer_tilt_metadata,
        key="max_world_z_underhang_mm",
        context=f"{context}.canonical_coordinates.outer_tilt_metadata",
    )
    max_world_x_protrusion_mm = _require_non_negative_float(
        raw_max_world_x_protrusion_mm,
        context=f"{context}.canonical_coordinates.outer_tilt_metadata.max_world_x_protrusion_mm",
    )
    max_world_z_underhang_mm = _require_non_negative_float(
        raw_max_world_z_underhang_mm,
        context=f"{context}.canonical_coordinates.outer_tilt_metadata.max_world_z_underhang_mm",
    )
    return (max_world_x_protrusion_mm, max_world_z_underhang_mm)


def _unwrap_raw(value: object, *, context: str) -> object:
    if hasattr(value, "_raw"):
        raw_value = object.__getattribute__(value, "_raw")
        assert raw_value is not None, f"{context}._raw must not be null"
        return raw_value
    return value


def _dataset_payload(dataset_name: str, *, points: tuple[tuple[float, float], ...]) -> list[object]:
    payload: list[object] = [
        f"NAME:{dataset_name}",
        [
            "NAME:Coordinates",
            ["NAME:DimUnits", "GHz", "fraction"],
        ],
    ]
    coordinates = payload[1]
    assert isinstance(coordinates, list), "dataset payload coordinates container must be a list"
    for frequency_ghz, value in points:
        coordinates.append(["NAME:Point", frequency_ghz, value])
    return payload


def _raw_project(hfss: HfssSession) -> object:
    raw_hfss = _unwrap_raw(hfss, context="hfss")
    assert hasattr(raw_hfss, "oproject"), "HFSS session must expose raw oproject for dataset-backed ferrite setup"
    raw_project = getattr(raw_hfss, "oproject")
    assert raw_project is not None, "HFSS raw oproject must not be null"
    return raw_project


def _raw_design(hfss: HfssSession) -> object:
    return _unwrap_raw(hfss.odesign, context="hfss.odesign")


def _raw_materials(hfss: HfssSession) -> object:
    return _unwrap_raw(hfss.materials, context="hfss.materials")


def _materials_session(hfss: HfssSession) -> MaterialsSession:
    return cast(MaterialsSession, _unwrap_raw(hfss.materials, context="hfss.materials"))


def _material_ref_from_material_keys(hfss: HfssSession, *, material_name: str) -> object | None:
    material_keys = _materials_session(hfss).material_keys
    normalized_name = material_name.casefold()
    if normalized_name not in material_keys:
        return None
    return material_keys[normalized_name]


def _definition_manager(raw_project: object) -> object:
    assert hasattr(raw_project, "GetDefinitionManager"), (
        f"Raw project must expose GetDefinitionManager "
        f"(project_type={type(raw_project).__name__})"
    )
    get_definition_manager = getattr(raw_project, "GetDefinitionManager")
    assert callable(get_definition_manager), "Raw project GetDefinitionManager must be callable"
    definition_manager = get_definition_manager()
    assert definition_manager is not None, "Raw project definition manager must not be null"
    return definition_manager


def _project_material_names(definition_manager: object) -> list[str]:
    assert hasattr(definition_manager, "GetProjectMaterialNames"), (
        f"Definition manager must expose GetProjectMaterialNames "
        f"(definition_manager_type={type(definition_manager).__name__})"
    )
    get_project_material_names = getattr(definition_manager, "GetProjectMaterialNames")
    assert callable(get_project_material_names), "Definition manager GetProjectMaterialNames must be callable"
    raw_names = get_project_material_names()
    assert isinstance(raw_names, Sequence), (
        "Definition manager GetProjectMaterialNames result must be a sequence "
        f"(actual={type(raw_names).__name__})"
    )
    assert not isinstance(raw_names, (str, bytes)), (
        "Definition manager GetProjectMaterialNames result must not be str/bytes "
        f"(actual={type(raw_names).__name__})"
    )
    names: list[str] = []
    for index, raw_name in enumerate(raw_names):
        assert isinstance(raw_name, str), (
            "Definition manager GetProjectMaterialNames items must be str "
            f"(index={index}, actual={type(raw_name).__name__})"
        )
        if raw_name == "":
            raise ValueError(f"Definition manager GetProjectMaterialNames returned empty material name at index {index}")
        names.append(raw_name)
    return names


def _dataset_ferrite_material_payload() -> list[object]:
    red, green, blue = _DATASET_FERRITE_APPEARANCE_RGB
    return [
        f"NAME:{_DATASET_FERRITE_MATERIAL}",
        "CoordinateSystemType:=",
        "Cartesian",
        "BulkOrSurfaceType:=",
        1,
        [
            "NAME:PhysicsTypes",
            "set:=",
            ["Electromagnetic", "Thermal", "Structural"],
        ],
        [
            "NAME:AttachedData",
            [
                "NAME:MatAppearanceData",
                "property_data:=",
                "appearance_data",
                "Red:=",
                red,
                "Green:=",
                green,
                "Blue:=",
                blue,
            ],
        ],
        "permittivity:=",
        "6",
        "permeability:=",
        f"pwlx({_MU_R_REAL_DATASET_NAME}, Freq)",
        "conductivity:=",
        "0.01",
        "magnetic_loss_tangent:=",
        f"pwlx({_MU_TAND_M_DATASET_NAME}, Freq)",
        "thermal_conductivity:=",
        "4",
        "mass_density:=",
        "4600",
        "specific_heat:=",
        "750",
        "youngs_modulus:=",
        "119000000000",
        "thermal_expansion_coefficient:=",
        "1e-05",
    ]


def _ensure_project_dataset_ferrite_material_definition(hfss: HfssSession) -> None:
    raw_project = _raw_project(hfss)
    definition_manager = _definition_manager(raw_project)
    payload = _dataset_ferrite_material_payload()
    material_names = _project_material_names(definition_manager)
    existing_case_name = next(
        (name for name in material_names if name.casefold() == _DATASET_FERRITE_MATERIAL.casefold()),
        None,
    )
    if existing_case_name is None:
        assert hasattr(definition_manager, "AddMaterial"), (
            f"Definition manager must expose AddMaterial "
            f"(definition_manager_type={type(definition_manager).__name__})"
        )
        add_material = getattr(definition_manager, "AddMaterial")
        assert callable(add_material), "Definition manager AddMaterial must be callable"
        add_material(payload)
    else:
        assert hasattr(definition_manager, "EditMaterial"), (
            f"Definition manager must expose EditMaterial "
            f"(definition_manager_type={type(definition_manager).__name__})"
        )
        edit_material = getattr(definition_manager, "EditMaterial")
        assert callable(edit_material), "Definition manager EditMaterial must be callable"
        edit_material(existing_case_name, payload)
    persisted_names = _project_material_names(definition_manager)
    if not any(name.casefold() == _DATASET_FERRITE_MATERIAL.casefold() for name in persisted_names):
        raise RuntimeError(
            "Project ferrite material definition was not persisted after AddMaterial/EditMaterial "
            f"(material_name={_DATASET_FERRITE_MATERIAL})"
        )


def _sync_pyaedt_material_lookup(hfss: HfssSession, *, material_name: str) -> None:
    if _material_ref_from_material_keys(hfss, material_name=material_name) is not None:
        return
    raw_materials = _raw_materials(hfss)
    assert hasattr(raw_materials, "_aedmattolibrary"), (
        "Raw materials must expose _aedmattolibrary for post-definition material sync "
        f"(materials_type={type(raw_materials).__name__})"
    )
    sync_material = getattr(raw_materials, "_aedmattolibrary")
    assert callable(sync_material), "Raw materials _aedmattolibrary must be callable"
    sync_material(material_name)
    if _material_ref_from_material_keys(hfss, material_name=material_name) is None:
        raise RuntimeError(
            "PyAEDT materials lookup did not resolve ferrite material after project definition sync "
            f"(material_name={material_name})"
        )


def ensure_notebook_dataset_ferrite_material(hfss: HfssSession) -> str:
    if not _NOTEBOOK_DATASET_IMPORT_PATH.is_file():
        raise FileNotFoundError(f"Notebook ferrite dataset tab file is missing: {_NOTEBOOK_DATASET_IMPORT_PATH}")

    raw_design = _raw_design(hfss)
    assert hasattr(raw_design, "ImportDataset"), (
        f"Raw design must expose ImportDataset for ferrite dataset import "
        f"(design_type={type(raw_design).__name__})"
    )
    import_dataset = getattr(raw_design, "ImportDataset")
    assert callable(import_dataset), "Raw design ImportDataset must be callable"
    raise_on_false(
        import_dataset(str(_NOTEBOOK_DATASET_IMPORT_PATH)),
        operation="ImportDataset",
        context={"path": str(_NOTEBOOK_DATASET_IMPORT_PATH)},
    )

    raw_project = _raw_project(hfss)
    assert hasattr(raw_project, "AddDataset"), (
        f"Raw project must expose AddDataset for ferrite material datasets "
        f"(project_type={type(raw_project).__name__})"
    )
    add_dataset = getattr(raw_project, "AddDataset")
    assert callable(add_dataset), "Raw project AddDataset must be callable"
    raise_on_false(
        add_dataset(_dataset_payload(_MU_R_REAL_DATASET_NAME, points=_MU_R_REAL_DATASET_POINTS)),
        operation="AddDataset",
        context={"dataset_name": _MU_R_REAL_DATASET_NAME},
    )
    raise_on_false(
        add_dataset(_dataset_payload(_MU_TAND_M_DATASET_NAME, points=_MU_TAND_M_DATASET_POINTS)),
        operation="AddDataset",
        context={"dataset_name": _MU_TAND_M_DATASET_NAME},
    )
    _ensure_project_dataset_ferrite_material_definition(hfss)
    _sync_pyaedt_material_lookup(hfss, material_name=_DATASET_FERRITE_MATERIAL)
    return _DATASET_FERRITE_MATERIAL


def _project_material_ref(hfss: HfssSession, *, material_name: str) -> object:
    material_ref = _material_ref_from_material_keys(hfss, material_name=material_name)
    if material_ref is not None:
        return material_ref
    materials = _materials_session(hfss)
    if not bool(materials.exists_material(material_name)):
        raise_on_false(
            materials.add_material(material_name),
            operation="add_material",
            context={"name": material_name},
        )
    _sync_pyaedt_material_lookup(hfss, material_name=material_name)
    material_ref = _material_ref_from_material_keys(hfss, material_name=material_name)
    assert material_ref is not None, (
        "PyAEDT materials lookup must expose the requested material after exists/add+sync "
        f"(material_name={material_name})"
    )
    return material_ref


def _set_material_property(*, material_ref: object, material_name: str, attr_name: str, attr_value: str) -> None:
    assert hasattr(material_ref, attr_name), (
        "Material reference must expose the requested property "
        f"(material_name={material_name}, property={attr_name}, material_type={type(material_ref).__name__})"
    )
    setattr(material_ref, attr_name, attr_value)


def ensure_pet_psa_material(hfss: HfssSession) -> str:
    material_ref = _project_material_ref(hfss, material_name=_PET_PSA_MATERIAL)
    for attr_name, attr_value in (
        ("permittivity", _PET_PSA_PERMITTIVITY),
        ("permeability", "1"),
        ("conductivity", "0"),
        ("dielectric_loss_tangent", "0"),
    ):
        _set_material_property(
            material_ref=material_ref,
            material_name=_PET_PSA_MATERIAL,
            attr_name=attr_name,
            attr_value=attr_value,
        )
    return _PET_PSA_MATERIAL


def ensure_underlay_materials(hfss: HfssSession, *, imported_modeled_object_names: Sequence[str]) -> None:
    underlay_ferrite_names = [
        name for name in imported_modeled_object_names if _is_ferrite_family_name(name)
    ]
    underlay_pet_psa_names = [
        name for name in imported_modeled_object_names if _is_pet_psa_family_name(name)
    ]
    underlay_air_names = [
        name for name in imported_modeled_object_names if _is_air_family_name(name)
    ]
    if not underlay_ferrite_names and not underlay_pet_psa_names and not underlay_air_names:
        return
    ensure_notebook_dataset_ferrite_material(hfss)
    ensure_pet_psa_material(hfss)


def _object_ref(modeler: ModelerSession, *, name: str, context: str) -> object:
    validate_aedt_name(name, field=f"{context}.name")
    object_ref = modeler.get_object_from_name(name)
    assert object_ref is not None, f"{context} did not resolve HFSS object: {name}"
    return object_ref


def _object_valid_properties(object_ref: object, *, context: str) -> tuple[str, ...]:
    assert hasattr(object_ref, "valid_properties"), f"{context} is missing required valid_properties attribute"
    raw_valid_properties = getattr(object_ref, "valid_properties")
    if isinstance(raw_valid_properties, (str, bytes)) or not isinstance(raw_valid_properties, Sequence):
        raise TypeError(
            f"{context}.valid_properties must be a sequence of property names "
            f"(actual={type(raw_valid_properties).__name__})"
        )
    valid_properties: list[str] = []
    for index, raw_property_name in enumerate(raw_valid_properties):
        if not isinstance(raw_property_name, str):
            raise TypeError(
                f"{context}.valid_properties[{index}] must be str "
                f"(actual={type(raw_property_name).__name__})"
            )
        if raw_property_name == "":
            raise ValueError(f"{context}.valid_properties[{index}] must be non-empty")
        valid_properties.append(raw_property_name)
    return tuple(valid_properties)


def _set_object_material(object_ref: object, *, material_name: str, context: str) -> None:
    if material_name == "":
        raise ValueError(f"{context}.material_name must be non-empty")
    valid_properties = _object_valid_properties(object_ref, context=context)
    if "Material" not in valid_properties:
        raise RuntimeError(
            f"{context} does not expose volume Material property "
            f"(valid_properties={valid_properties})"
        )
    assert hasattr(object_ref, "material_name"), f"{context} is missing required material_name attribute"
    setattr(object_ref, "material_name", material_name)


def _set_object_surface_material(object_ref: object, *, material_name: str, context: str) -> None:
    if material_name == "":
        raise ValueError(f"{context}.material_name must be non-empty")
    valid_properties = _object_valid_properties(object_ref, context=context)
    if "Surface Material" not in valid_properties:
        raise RuntimeError(
            f"{context} does not expose sheet Surface Material property "
            f"(valid_properties={valid_properties})"
        )
    assert hasattr(object_ref, "surface_material_name"), (
        f"{context} is missing required surface_material_name attribute"
    )
    setattr(object_ref, "surface_material_name", material_name)


def _require_float(value: object, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{context} must be number")
    return float(value)


def _tx_actual_region_bounds(
    value: object,
    *,
    context: str,
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be an object/table")
    raw_min_xyz = require_key(value, key="min_xyz", context=context)
    raw_max_xyz = require_key(value, key="max_xyz", context=context)
    raw_size_xyz = require_key(value, key="size_xyz", context=context)
    if not isinstance(raw_min_xyz, Sequence) or isinstance(raw_min_xyz, (str, bytes)) or len(raw_min_xyz) != 3:
        raise TypeError(f"{context}.min_xyz must be a sequence of three numbers")
    if not isinstance(raw_max_xyz, Sequence) or isinstance(raw_max_xyz, (str, bytes)) or len(raw_max_xyz) != 3:
        raise TypeError(f"{context}.max_xyz must be a sequence of three numbers")
    if not isinstance(raw_size_xyz, Sequence) or isinstance(raw_size_xyz, (str, bytes)) or len(raw_size_xyz) != 3:
        raise TypeError(f"{context}.size_xyz must be a sequence of three numbers")
    checked_min_xyz = (
        _require_float(raw_min_xyz[0], context=f"{context}.min_xyz[0]"),
        _require_float(raw_min_xyz[1], context=f"{context}.min_xyz[1]"),
        _require_float(raw_min_xyz[2], context=f"{context}.min_xyz[2]"),
    )
    checked_max_xyz = (
        _require_float(raw_max_xyz[0], context=f"{context}.max_xyz[0]"),
        _require_float(raw_max_xyz[1], context=f"{context}.max_xyz[1]"),
        _require_float(raw_max_xyz[2], context=f"{context}.max_xyz[2]"),
    )
    checked_size_xyz = (
        _require_float(raw_size_xyz[0], context=f"{context}.size_xyz[0]"),
        _require_float(raw_size_xyz[1], context=f"{context}.size_xyz[1]"),
        _require_float(raw_size_xyz[2], context=f"{context}.size_xyz[2]"),
    )
    for axis_index, axis_name in enumerate(("x", "y", "z")):
        if checked_size_xyz[axis_index] <= 0.0:
            raise ValueError(f"{context}.size_xyz[{axis_index}] must be positive for {axis_name}")
        expected_max = checked_min_xyz[axis_index] + checked_size_xyz[axis_index]
        if abs(checked_max_xyz[axis_index] - expected_max) > _PLACEMENT_TOLERANCE:
            raise ValueError(
                f"{context}.max_xyz[{axis_index}] must equal min+size for {axis_name} "
                f"(actual={checked_max_xyz[axis_index]}, expected={expected_max})"
            )
    return checked_min_xyz, checked_max_xyz, checked_size_xyz


def _expected_port_sheet_name(modeled_entry: dict[str, object], *, context: str) -> str | None:
    role = require_non_empty_str(require_key(modeled_entry, key="role", context=context), context=f"{context}.role")
    if role == "tx_single_coil":
        return "tx_port_sheet"
    if role == "rx_single_coil":
        return "rx_port_sheet"
    if role == "tx_inner_single_coil":
        return "tx_inner_port_sheet"
    if role == "tx_outer_single_coil":
        return None
    if role == "tx_plate_stack":
        return "tx_plate_port_sheet"
    if role == "rx_plate_stack":
        return "rx_plate_port_sheet"
    if role == "tx_rect_void_columns":
        return "tx_rect_void_columns_port_sheet"
    return None


def _port_sheet_vertices_xyz(modeled_entry: dict[str, object], *, context: str) -> tuple[tuple[float, float, float], ...]:
    role = require_non_empty_str(require_key(modeled_entry, key="role", context=context), context=f"{context}.role")
    if role == "tx_rect_void_columns":
        return _tx_rect_void_columns_port_sheet_vertices_xyz(modeled_entry, context=context)
    terminal_metadata = require_key(modeled_entry, key="terminal_metadata", context=context)
    assert isinstance(terminal_metadata, dict), f"{context}.terminal_metadata must be a table/object"
    raw_vertices = require_key(
        terminal_metadata,
        key="port_sheet_vertices_xyz",
        context=f"{context}.terminal_metadata",
    )
    if isinstance(raw_vertices, (str, bytes)) or not isinstance(raw_vertices, Sequence):
        raise TypeError(f"{context}.terminal_metadata.port_sheet_vertices_xyz must be a sequence of 3D points")
    vertices: list[tuple[float, float, float]] = []
    for vertex_index, raw_vertex in enumerate(raw_vertices):
        if isinstance(raw_vertex, (str, bytes)) or not isinstance(raw_vertex, Sequence):
            raise TypeError(
                f"{context}.terminal_metadata.port_sheet_vertices_xyz[{vertex_index}] must be a sequence of length 3"
            )
        if len(raw_vertex) != 3:
            raise ValueError(
                f"{context}.terminal_metadata.port_sheet_vertices_xyz[{vertex_index}] must contain exactly 3 entries"
            )
        vertices.append(
            (
                _require_float(raw_vertex[0], context=f"{context}.terminal_metadata.port_sheet_vertices_xyz[{vertex_index}][0]"),
                _require_float(raw_vertex[1], context=f"{context}.terminal_metadata.port_sheet_vertices_xyz[{vertex_index}][1]"),
                _require_float(raw_vertex[2], context=f"{context}.terminal_metadata.port_sheet_vertices_xyz[{vertex_index}][2]"),
            )
        )
    if len(vertices) != 4:
        raise ValueError(f"{context}.terminal_metadata.port_sheet_vertices_xyz must contain exactly 4 vertices")
    return tuple(vertices)


def _tx_rect_void_columns_tab_face_vertices_by_terminal(
    modeled_entry: dict[str, object],
    *,
    context: str,
) -> dict[str, tuple[tuple[float, float, float], ...]]:
    terminal_metadata = require_key(modeled_entry, key="terminal_metadata", context=context)
    assert isinstance(terminal_metadata, dict), f"{context}.terminal_metadata must be a table/object"
    kind = require_non_empty_str(
        require_key(terminal_metadata, key="kind", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.kind",
    )
    if kind not in ("parallel_collector_tabs", "series_collector_tabs"):
        raise ValueError(
            f"{context}.terminal_metadata.kind must be 'parallel_collector_tabs' or 'series_collector_tabs' "
            f"for tx_rect_void_columns port sheet reconstruction (actual={kind!r})"
        )
    raw_tab_faces = require_key(
        terminal_metadata,
        key="tab_face_vertices_xyz",
        context=f"{context}.terminal_metadata",
    )
    if isinstance(raw_tab_faces, (str, bytes)) or not isinstance(raw_tab_faces, Sequence):
        raise TypeError(f"{context}.terminal_metadata.tab_face_vertices_xyz must be a sequence")
    faces_by_terminal: dict[str, tuple[tuple[float, float, float], ...]] = {}
    for face_index, raw_face in enumerate(raw_tab_faces):
        face_context = f"{context}.terminal_metadata.tab_face_vertices_xyz[{face_index}]"
        if not isinstance(raw_face, dict):
            raise TypeError(f"{face_context} must be a table/object")
        terminal = require_non_empty_str(
            require_key(raw_face, key="terminal", context=face_context),
            context=f"{face_context}.terminal",
        )
        if terminal not in ("start", "end"):
            raise ValueError(f"{face_context}.terminal must be 'start' or 'end' (actual={terminal!r})")
        if terminal in faces_by_terminal:
            raise ValueError(f"{context}.terminal_metadata.tab_face_vertices_xyz contains duplicate terminal {terminal!r}")
        raw_vertices = require_key(raw_face, key="vertices_xyz", context=face_context)
        if isinstance(raw_vertices, (str, bytes)) or not isinstance(raw_vertices, Sequence):
            raise TypeError(f"{face_context}.vertices_xyz must be a sequence of 3D points")
        vertices: list[tuple[float, float, float]] = []
        for vertex_index, raw_vertex in enumerate(raw_vertices):
            if isinstance(raw_vertex, (str, bytes)) or not isinstance(raw_vertex, Sequence):
                raise TypeError(f"{face_context}.vertices_xyz[{vertex_index}] must be a sequence of length 3")
            if len(raw_vertex) != 3:
                raise ValueError(f"{face_context}.vertices_xyz[{vertex_index}] must contain exactly 3 entries")
            vertices.append(
                (
                    _require_float(raw_vertex[0], context=f"{face_context}.vertices_xyz[{vertex_index}][0]"),
                    _require_float(raw_vertex[1], context=f"{face_context}.vertices_xyz[{vertex_index}][1]"),
                    _require_float(raw_vertex[2], context=f"{face_context}.vertices_xyz[{vertex_index}][2]"),
                )
            )
        if len(vertices) != 4:
            raise ValueError(f"{face_context}.vertices_xyz must contain exactly 4 vertices")
        faces_by_terminal[terminal] = tuple(vertices)
    if set(faces_by_terminal) != {"start", "end"}:
        raise ValueError(
            f"{context}.terminal_metadata.tab_face_vertices_xyz must contain start and end terminals "
            f"(actual={sorted(faces_by_terminal)})"
        )
    return faces_by_terminal


def _center_of_vertices(vertices: tuple[tuple[float, float, float], ...]) -> tuple[float, float, float]:
    return (
        sum(vertex[0] for vertex in vertices) / float(len(vertices)),
        sum(vertex[1] for vertex in vertices) / float(len(vertices)),
        sum(vertex[2] for vertex in vertices) / float(len(vertices)),
    )


def _edge_vertices_at_axis_extreme(
    vertices: tuple[tuple[float, float, float], ...],
    *,
    axis_index: int,
    use_maximum: bool,
    context: str,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    axis_values = tuple(vertex[axis_index] for vertex in vertices)
    target_value = max(axis_values) if use_maximum else min(axis_values)
    tolerance = 1e-8
    edge_vertices = tuple(vertex for vertex in vertices if abs(vertex[axis_index] - target_value) <= tolerance)
    if len(edge_vertices) != 2:
        raise ValueError(
            f"{context} must expose exactly one edge at the selected tab-face extreme "
            f"(axis_index={axis_index}, use_maximum={use_maximum}, matches={len(edge_vertices)})"
        )
    sort_axes = tuple(index for index in (0, 1, 2) if index != axis_index)
    sorted_vertices = tuple(sorted(edge_vertices, key=lambda vertex: tuple(vertex[index] for index in sort_axes)))
    return (sorted_vertices[0], sorted_vertices[1])


def _tx_rect_void_columns_port_sheet_vertices_xyz(
    modeled_entry: dict[str, object],
    *,
    context: str,
) -> tuple[tuple[float, float, float], ...]:
    faces_by_terminal = _tx_rect_void_columns_tab_face_vertices_by_terminal(modeled_entry, context=context)
    start_vertices = faces_by_terminal["start"]
    end_vertices = faces_by_terminal["end"]
    start_center = _center_of_vertices(start_vertices)
    end_center = _center_of_vertices(end_vertices)
    center_delta = tuple(end_center[index] - start_center[index] for index in (0, 1, 2))
    axis_index = max((0, 1, 2), key=lambda index: abs(center_delta[index]))
    if abs(center_delta[axis_index]) <= 1e-8:
        raise ValueError(
            f"{context}.terminal_metadata.tab_face_vertices_xyz start/end tab faces must have non-zero separation "
            f"(start_center={start_center}, end_center={end_center})"
        )
    end_is_positive = center_delta[axis_index] > 0.0
    start_edge = _edge_vertices_at_axis_extreme(
        start_vertices,
        axis_index=axis_index,
        use_maximum=end_is_positive,
        context=f"{context}.terminal_metadata.tab_face_vertices_xyz[start]",
    )
    end_edge = _edge_vertices_at_axis_extreme(
        end_vertices,
        axis_index=axis_index,
        use_maximum=not end_is_positive,
        context=f"{context}.terminal_metadata.tab_face_vertices_xyz[end]",
    )
    return (start_edge[0], end_edge[0], end_edge[1], start_edge[1])


def _covered_sheet_name(covered: object, *, fallback_name: str, context: str) -> str:
    if covered is True:
        return fallback_name
    if isinstance(covered, list):
        first = covered[0] if covered else fallback_name
        if isinstance(first, str):
            return first
        assert hasattr(first, "name"), f"{context} cover_lines list result item must expose name"
        raw_name = getattr(first, "name")
        assert isinstance(raw_name, str), f"{context} cover_lines list result item name must be str"
        return raw_name
    if isinstance(covered, str):
        return covered
    assert hasattr(covered, "name"), f"{context} cover_lines result must expose name"
    raw_name = getattr(covered, "name")
    assert isinstance(raw_name, str), f"{context} cover_lines result name must be str"
    return raw_name


def _reconstruct_port_sheet_if_needed(
    *,
    modeler: ModelerSession,
    modeled_entry: dict[str, object],
    context: str,
) -> list[str]:
    role = require_non_empty_str(require_key(modeled_entry, key="role", context=context), context=f"{context}.role")
    if role == "tx_rect_void_columns":
        return []
    if role == "tx_outer_single_coil":
        return []
    expected_port_sheet_name = _expected_port_sheet_name(modeled_entry, context=context)
    if expected_port_sheet_name is None:
        return []

    port_sheet_vertices_xyz = _port_sheet_vertices_xyz(modeled_entry, context=context)
    polyline_created = create_polyline(
        modeler,
        points=[[x, y, z] for x, y, z in port_sheet_vertices_xyz],
        name=expected_port_sheet_name,
        material="vacuum",
        close_surface=True,
        cover_surface=False,
    )
    loop_name = require_non_empty_str(getattr(polyline_created, "name"), context=f"{context}.reconstructed_port_sheet.loop_name")
    covered = cover_lines(modeler, assignment=loop_name)
    covered_name = _covered_sheet_name(covered, fallback_name=loop_name, context=context)
    reconstructed_context = f"{context}.reconstructed_port_sheet[{covered_name}]"
    object_ref = _object_ref(modeler, name=covered_name, context=reconstructed_context)
    valid_properties = _object_valid_properties(object_ref, context=reconstructed_context)
    # AEDT covered polylines resolve to sheets. Many sheet objects expose no volume
    # "Material" property, so do not issue a volume-material mutation unless the
    # live object explicitly supports it.
    if "Material" in valid_properties:
        _set_object_material(
            object_ref,
            material_name="vacuum",
            context=reconstructed_context,
        )
    state_result = modeler.set_object_model_state(covered_name, True)
    raise_on_false(
        state_result,
        operation="set_object_model_state",
        context={"context": context, "name": covered_name, "model": True},
    )
    return [covered_name]


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


def _apply_copper_material_and_visual_state(
    *,
    modeler: ModelerSession,
    object_name: str,
    context: str,
) -> None:
    object_ref = _object_ref(modeler, name=object_name, context=context)
    valid_properties = _object_valid_properties(object_ref, context=context)
    if "Material" in valid_properties:
        _set_object_material(object_ref, material_name=_TX_COPPER_MATERIAL, context=context)
    elif "Surface Material" in valid_properties:
        _set_object_surface_material(object_ref, material_name=_TX_COPPER_MATERIAL, context=context)
    else:
        raise RuntimeError(
            f"{context} does not expose a supported copper material property "
            f"(valid_properties={valid_properties})"
        )
    set_object_color(object_ref, color=_TX_COPPER_COLOR)
    set_object_transparency(object_ref, transparency=_TX_COPPER_TRANSPARENCY)


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


def validate_tx_inner_modeled_bounds_against_actual_region(
    *,
    modeled_entry: dict[str, object],
    owner_member: dict[str, object],
    actual_region_member: dict[str, object],
    context: str,
) -> None:
    role = require_non_empty_str(require_key(modeled_entry, key="role", context=context), context=f"{context}.role")
    if role != "tx_inner_single_coil":
        raise ValueError(
            "validate_tx_inner_modeled_bounds_against_actual_region only accepts tx_inner_single_coil "
            f"(actual={role!r})"
        )
    modeled_object_id = require_non_empty_str(
        require_key(modeled_entry, key="object_id", context=context),
        context=f"{context}.object_id",
    )
    owner_id = require_non_empty_str(
        require_key(modeled_entry, key="placement_owner_id", context=context),
        context=f"{context}.placement_owner_id",
    )
    if owner_id != "tx_inner_region":
        raise ValueError(
            f"{context}.placement_owner_id must be 'tx_inner_region' for geometry-only tx_inner_single_coil "
            f"(actual={owner_id!r})"
        )
    plane = require_non_empty_str(require_key(modeled_entry, key="plane", context=context), context=f"{context}.plane")
    if plane != "XY":
        raise ValueError(f"{context}.plane must be 'XY' for tx_inner_single_coil geometry (actual={plane!r})")

    actual_region_object_id = require_non_empty_str(
        require_key(actual_region_member, key="object_id", context="tx_inner_actual_region_member"),
        context="tx_inner_actual_region_member.object_id",
    )
    if actual_region_object_id != "tx_inner_actual_region":
        raise ValueError(
            "tx_inner_single_coil actual bounds validation requires tx_inner_actual_region member "
            f"(actual={actual_region_object_id!r})"
        )
    actual_region_role = require_non_empty_str(
        require_key(actual_region_member, key="role", context="tx_inner_actual_region_member"),
        context="tx_inner_actual_region_member.role",
    )
    if actual_region_role != "tx_inner_actual_region":
        raise ValueError(
            "tx_inner_actual_region member role must remain tx_inner_actual_region "
            f"(actual={actual_region_role!r})"
        )
    raw_tx_actual_region = require_key(
        actual_region_member,
        key="tx_actual_region",
        context="tx_inner_actual_region_member",
    )
    if not isinstance(raw_tx_actual_region, dict):
        raise TypeError("tx_inner_actual_region_member.tx_actual_region must be an object/table")
    source_guide_id = require_non_empty_str(
        require_key(raw_tx_actual_region, key="source_guide_id", context="tx_inner_actual_region_member.tx_actual_region"),
        context="tx_inner_actual_region_member.tx_actual_region.source_guide_id",
    )
    if source_guide_id != owner_id:
        raise ValueError(
            "tx_inner_actual_region source guide must match tx_inner_single_coil placement owner "
            f"(source_guide_id={source_guide_id!r}, placement_owner_id={owner_id!r})"
        )
    modeled_source_id = require_non_empty_str(
        require_key(raw_tx_actual_region, key="modeled_source_id", context="tx_inner_actual_region_member.tx_actual_region"),
        context="tx_inner_actual_region_member.tx_actual_region.modeled_source_id",
    )
    if modeled_source_id != modeled_object_id:
        raise ValueError(
            "tx_inner_actual_region modeled source must match tx_inner_single_coil modeled object "
            f"(modeled_source_id={modeled_source_id!r}, object_id={modeled_object_id!r})"
        )

    owner_min_x, owner_min_y, owner_min_z = outer_bounds_min_xyz(owner_member, context="tx_inner_region_member")
    owner_size_x, owner_size_y, owner_size_z = outer_bounds_size_xyz(owner_member, context="tx_inner_region_member")
    owner_max_x = owner_min_x + owner_size_x
    owner_max_y = owner_min_y + owner_size_y
    owner_max_z = owner_min_z + owner_size_z

    actual_min_xyz, actual_max_xyz, actual_size_xyz = _tx_actual_region_bounds(
        require_key(
            raw_tx_actual_region,
            key="actual_region_bounds",
            context="tx_inner_actual_region_member.tx_actual_region",
        ),
        context="tx_inner_actual_region_member.tx_actual_region.actual_region_bounds",
    )
    canonical_actual_min_xyz = outer_bounds_min_xyz(
        actual_region_member,
        context="tx_inner_actual_region_member",
    )
    canonical_actual_size_xyz = outer_bounds_size_xyz(
        actual_region_member,
        context="tx_inner_actual_region_member",
    )
    canonical_actual_max_xyz = (
        canonical_actual_min_xyz[0] + canonical_actual_size_xyz[0],
        canonical_actual_min_xyz[1] + canonical_actual_size_xyz[1],
        canonical_actual_min_xyz[2] + canonical_actual_size_xyz[2],
    )
    if (
        any(abs(actual_min_xyz[index] - canonical_actual_min_xyz[index]) > _PLACEMENT_TOLERANCE for index in range(3))
        or any(abs(actual_size_xyz[index] - canonical_actual_size_xyz[index]) > _PLACEMENT_TOLERANCE for index in range(3))
        or any(abs(actual_max_xyz[index] - canonical_actual_max_xyz[index]) > _PLACEMENT_TOLERANCE for index in range(3))
    ):
        raise ValueError(
            "tx_inner_actual_region canonical coordinates must match tx_actual_region.actual_region_bounds "
            f"(actual_min={actual_min_xyz}, canonical_min={canonical_actual_min_xyz}, "
            f"actual_size={actual_size_xyz}, canonical_size={canonical_actual_size_xyz})"
        )

    if (
        actual_min_xyz[0] < owner_min_x - _PLACEMENT_TOLERANCE
        or actual_max_xyz[0] > owner_max_x + _PLACEMENT_TOLERANCE
        or actual_min_xyz[1] < owner_min_y - _PLACEMENT_TOLERANCE
        or actual_max_xyz[1] > owner_max_y + _PLACEMENT_TOLERANCE
    ):
        raise ValueError(
            "tx_inner_actual_region design bounds must stay contained in tx_inner_region X/Y "
            f"(actual_min={actual_min_xyz}, actual_max={actual_max_xyz}, "
            f"owner_min={(owner_min_x, owner_min_y, owner_min_z)}, owner_max={(owner_max_x, owner_max_y, owner_max_z)})"
        )
    expected_actual_min_y = owner_min_y + (owner_size_y - actual_size_xyz[1]) / 2.0
    if abs(actual_min_xyz[1] - expected_actual_min_y) > _PLACEMENT_TOLERANCE:
        raise ValueError(
            "tx_inner_actual_region design bounds must be centered in tx_inner_region Y "
            f"(actual_min_y={actual_min_xyz[1]}, expected_min_y={expected_actual_min_y})"
        )
    expected_actual_min_z = owner_min_z + owner_size_z - actual_size_xyz[2]
    if abs(actual_min_xyz[2] - expected_actual_min_z) > _PLACEMENT_TOLERANCE:
        raise ValueError(
            "tx_inner_actual_region design bounds max_z must touch tx_inner_region max_z "
            f"(actual_min_z={actual_min_xyz[2]}, expected_min_z={expected_actual_min_z})"
        )

    physical_min_xyz, physical_max_xyz, physical_size_xyz = _tx_actual_region_bounds(
        require_key(
            raw_tx_actual_region,
            key="physical_modeled_body_bounds",
            context="tx_inner_actual_region_member.tx_actual_region",
        ),
        context="tx_inner_actual_region_member.tx_actual_region.physical_modeled_body_bounds",
    )
    modeled_min_xyz = outer_bounds_min_xyz(modeled_entry, context=context)
    modeled_size_xyz = outer_bounds_size_xyz(modeled_entry, context=context)
    modeled_max_xyz = (
        modeled_min_xyz[0] + modeled_size_xyz[0],
        modeled_min_xyz[1] + modeled_size_xyz[1],
        modeled_min_xyz[2] + modeled_size_xyz[2],
    )
    if (
        any(abs(physical_min_xyz[index] - modeled_min_xyz[index]) > _PLACEMENT_TOLERANCE for index in range(3))
        or any(abs(physical_size_xyz[index] - modeled_size_xyz[index]) > _PLACEMENT_TOLERANCE for index in range(3))
        or any(abs(physical_max_xyz[index] - modeled_max_xyz[index]) > _PLACEMENT_TOLERANCE for index in range(3))
    ):
        raise ValueError(
            "tx_inner_actual_region physical provenance must match tx_inner_single_coil modeled bounds "
            f"(physical_min={physical_min_xyz}, modeled_min={modeled_min_xyz}, "
            f"physical_size={physical_size_xyz}, modeled_size={modeled_size_xyz})"
        )
    if (
        physical_min_xyz[0] < actual_min_xyz[0] - _PLACEMENT_TOLERANCE
        or physical_max_xyz[0] > actual_max_xyz[0] + _PLACEMENT_TOLERANCE
        or physical_min_xyz[1] < actual_min_xyz[1] - _PLACEMENT_TOLERANCE
        or physical_max_xyz[1] > actual_max_xyz[1] + _PLACEMENT_TOLERANCE
        or physical_min_xyz[2] < actual_min_xyz[2] - _PLACEMENT_TOLERANCE
        or physical_max_xyz[2] > actual_max_xyz[2] + _PLACEMENT_TOLERANCE
    ):
        raise ValueError(
            "tx_inner_single_coil physical modeled bounds must stay contained in tx_inner_actual_region design bounds "
            f"(physical_min={physical_min_xyz}, physical_max={physical_max_xyz}, "
            f"actual_min={actual_min_xyz}, actual_max={actual_max_xyz})"
        )


def validate_modeled_bounds_against_owner(
    *,
    modeled_entry: dict[str, object],
    owner_member: dict[str, object],
    context: str,
) -> None:
    role = require_non_empty_str(require_key(modeled_entry, key="role", context=context), context=f"{context}.role")
    owner_id = require_non_empty_str(
        require_key(modeled_entry, key="placement_owner_id", context=context),
        context=f"{context}.placement_owner_id",
    )
    plane = require_non_empty_str(require_key(modeled_entry, key="plane", context=context), context=f"{context}.plane")
    modeled_min_x, modeled_min_y, modeled_min_z = outer_bounds_min_xyz(modeled_entry, context=context)
    modeled_size_x, modeled_size_y, modeled_size_z = outer_bounds_size_xyz(modeled_entry, context=context)
    modeled_max_x = modeled_min_x + modeled_size_x
    modeled_max_y = modeled_min_y + modeled_size_y
    modeled_max_z = modeled_min_z + modeled_size_z
    raw_expected_names = require_key(modeled_entry, key="expected_exported_body_names", context=context)
    if not isinstance(raw_expected_names, list):
        raise TypeError(
            f"{context}.expected_exported_body_names must be list[str] "
            f"(actual={type(raw_expected_names).__name__})"
        )
    expected_names = [
        require_non_empty_str(raw_name, context=f"{context}.expected_exported_body_names[{index}]")
        for index, raw_name in enumerate(raw_expected_names)
    ]
    is_tx_array_mode = role == "tx_plate_stack" and any(
        _is_tx_plate_stack_array_expected_name(name) for name in expected_names
    )
    owner_context = f"non_model_objects[*].member_objects[{owner_id}]"
    owner_min_x, owner_min_y, owner_min_z = outer_bounds_min_xyz(owner_member, context=owner_context)
    owner_size_x, owner_size_y, owner_size_z = outer_bounds_size_xyz(owner_member, context=owner_context)
    owner_max_x = owner_min_x + owner_size_x
    owner_max_z = owner_min_z + owner_size_z
    owner_max_y = owner_min_y + owner_size_y
    if role == "tx_rect_void_columns":
        if owner_id != "tx_region_actual_stack_space":
            raise ValueError(
                f"{context}.placement_owner_id must be 'tx_region_actual_stack_space' for tx_rect_void_columns "
                f"(actual={owner_id!r})"
            )
        if plane != "XY":
            raise ValueError(f"{context}.plane must be 'XY' for tx_rect_void_columns geometry (actual={plane!r})")
        if modeled_max_z > owner_max_z + _PLACEMENT_TOLERANCE:
            raise ValueError(
                f"{context} outer bounds max_z must not exceed {owner_id} max_z "
                f"(actual={modeled_max_z}, expected_max={owner_max_z})"
            )
        if modeled_max_x < owner_min_x or modeled_min_x > owner_max_x or modeled_max_y < owner_min_y or modeled_min_y > owner_max_y:
            raise ValueError(
                f"{context} outer bounds must overlap {owner_id} in XY "
                f"(modeled_min={(modeled_min_x, modeled_min_y)}, modeled_max={(modeled_max_x, modeled_max_y)}, "
                f"owner_min={(owner_min_x, owner_min_y)}, owner_max={(owner_max_x, owner_max_y)})"
            )
        return
    allowed_modeled_size_y = (
        owner_size_y + _PLATE_STACK_STUB_LENGTH_MM if role in ("tx_plate_stack", "rx_plate_stack") else owner_size_y
    )
    if role == "tx_outer_single_coil":
        allowed_modeled_size_x = (
            owner_size_x + _tx_outer_tilt_allowances_mm(modeled_entry=modeled_entry, context=context)[0]
        )
    else:
        allowed_modeled_size_x = owner_size_x
    if modeled_size_y > allowed_modeled_size_y or modeled_size_z > owner_size_z or (
        not is_tx_array_mode and modeled_size_x > allowed_modeled_size_x
    ):
        message = (
            f"{context} outer bounds must fit inside {owner_id} "
            f"(modeled_size={(modeled_size_x, modeled_size_y, modeled_size_z)}, "
            f"owner_size={(allowed_modeled_size_x, allowed_modeled_size_y, owner_size_z)})"
        )
        if role == "tx_outer_single_coil":
            message = f"tx_outer_single_coil outer bounds must fit inside {owner_id}"
        raise ValueError(message)
    if role == "tx_plate_stack":
        if owner_id != "tx_region":
            raise ValueError(
                f"{context}.placement_owner_id must be 'tx_region' for tx_plate_stack import-only geometry "
                f"(actual={owner_id!r})"
            )
        if plane != "YZ":
            raise ValueError(f"{context}.plane must be 'YZ' for tx_plate_stack import-only geometry (actual={plane!r})")
        active_size_y = modeled_size_y - _PLATE_STACK_STUB_LENGTH_MM
        active_min_y = modeled_min_y + _PLATE_STACK_STUB_LENGTH_MM
        active_max_y = modeled_min_y + modeled_size_y
        if active_size_y <= 0:
            raise ValueError(
                "tx_plate_stack active Y footprint must be strictly positive after removing the -Y stub overhang "
                f"(modeled_size_y={modeled_size_y}, stub_length={_PLATE_STACK_STUB_LENGTH_MM})"
            )
        expected_active_min_y = -active_size_y / 2.0
        expected_active_max_y = active_size_y / 2.0
        if abs(active_min_y - expected_active_min_y) > _PLACEMENT_TOLERANCE:
            raise ValueError(
                "tx_plate_stack active Y footprint must be centered on global Y=0 after removing -Y stub overhang "
                f"(active_min_y={active_min_y}, expected_active_min_y={expected_active_min_y}, "
                f"stub_length={_PLATE_STACK_STUB_LENGTH_MM})"
            )
        if abs(active_max_y - expected_active_max_y) > _PLACEMENT_TOLERANCE:
            raise ValueError(
                "tx_plate_stack active Y footprint must be centered on global Y=0 after removing -Y stub overhang "
                f"(active_max_y={active_max_y}, expected_active_max_y={expected_active_max_y}, "
                f"stub_length={_PLATE_STACK_STUB_LENGTH_MM})"
            )
        if active_min_y < owner_min_y - _PLACEMENT_TOLERANCE or active_max_y > owner_max_y + _PLACEMENT_TOLERANCE:
            raise ValueError(
                "tx_plate_stack centered active Y footprint must stay within tx_region Y bounds "
                f"(active_min_y={active_min_y}, active_max_y={active_max_y}, "
                f"owner_min_y={owner_min_y}, owner_max_y={owner_max_y})"
            )
        if not is_tx_array_mode and abs(modeled_min_x - owner_min_x) > _PLACEMENT_TOLERANCE:
            raise ValueError(
                "tx_plate_stack outer bounds min_x must already touch tx_region min_x "
                f"(actual={modeled_min_x}, expected={owner_min_x})"
            )
        if abs(modeled_max_z - owner_max_z) > _PLACEMENT_TOLERANCE:
            raise ValueError(
                "tx_plate_stack outer bounds max_z must already touch tx_region max_z "
                f"(actual={modeled_max_z}, expected={owner_max_z})"
            )
        return
    if role == "rx_plate_stack":
        if owner_id != "rx_region_max":
            raise ValueError(
                f"{context}.placement_owner_id must be 'rx_region_max' for rx_plate_stack import-only geometry "
                f"(actual={owner_id!r})"
            )
        if plane != "YZ":
            raise ValueError(f"{context}.plane must be 'YZ' for rx_plate_stack import-only geometry (actual={plane!r})")
        active_size_y = modeled_size_y - _PLATE_STACK_STUB_LENGTH_MM
        active_min_y = modeled_min_y + _PLATE_STACK_STUB_LENGTH_MM
        active_max_y = modeled_min_y + modeled_size_y
        if active_size_y <= 0:
            raise ValueError(
                "rx_plate_stack active Y footprint must be strictly positive after removing the -Y stub overhang "
                f"(modeled_size_y={modeled_size_y}, stub_length={_PLATE_STACK_STUB_LENGTH_MM})"
            )
        expected_active_min_y = -active_size_y / 2.0
        expected_active_max_y = active_size_y / 2.0
        if abs(active_min_y - expected_active_min_y) > _PLACEMENT_TOLERANCE:
            raise ValueError(
                "rx_plate_stack active Y footprint must be centered on global Y=0 after removing -Y stub overhang "
                f"(active_min_y={active_min_y}, expected_active_min_y={expected_active_min_y}, "
                f"stub_length={_PLATE_STACK_STUB_LENGTH_MM})"
            )
        if abs(active_max_y - expected_active_max_y) > _PLACEMENT_TOLERANCE:
            raise ValueError(
                "rx_plate_stack active Y footprint must be centered on global Y=0 after removing -Y stub overhang "
                f"(active_max_y={active_max_y}, expected_active_max_y={expected_active_max_y}, "
                f"stub_length={_PLATE_STACK_STUB_LENGTH_MM})"
            )
        if active_min_y < owner_min_y - _PLACEMENT_TOLERANCE or active_max_y > owner_max_y + _PLACEMENT_TOLERANCE:
            raise ValueError(
                "rx_plate_stack centered active Y footprint must stay within rx_region_max Y bounds "
                f"(active_min_y={active_min_y}, active_max_y={active_max_y}, "
                f"owner_min_y={owner_min_y}, owner_max_y={owner_max_y})"
            )
        if abs(modeled_min_x - owner_min_x) > _PLACEMENT_TOLERANCE:
            raise ValueError(
                "rx_plate_stack outer bounds min_x must already touch rx_region_max min_x "
                f"(actual={modeled_min_x}, expected={owner_min_x})"
            )
        if abs(modeled_min_z - owner_min_z) > _PLACEMENT_TOLERANCE:
            raise ValueError(
                "rx_plate_stack outer bounds min_z must already touch rx_region_max min_z "
                f"(actual={modeled_min_z}, expected={owner_min_z})"
            )
        return
    if role == "tx_outer_single_coil":
        if owner_id != "tx_outer_region":
            raise ValueError(
                f"{context}.placement_owner_id must be 'tx_outer_region' for geometry-only tx_outer_single_coil "
                f"(actual={owner_id!r})"
            )
        if plane != "XY":
            raise ValueError(f"{context}.plane must be 'XY' for tx_outer_single_coil geometry (actual={plane!r})")
        protrusion_allowance_mm, z_underhang_allowance_mm = _tx_outer_tilt_allowances_mm(
            modeled_entry=modeled_entry,
            context=context,
        )
        if (
            modeled_min_x < owner_min_x - _PLACEMENT_TOLERANCE
            or modeled_max_x > owner_max_x + protrusion_allowance_mm + _PLACEMENT_TOLERANCE
            or modeled_min_y < owner_min_y - _PLACEMENT_TOLERANCE
            or modeled_max_y > owner_max_y + _PLACEMENT_TOLERANCE
            or modeled_min_z < owner_min_z - z_underhang_allowance_mm - _PLACEMENT_TOLERANCE
            or modeled_max_z > owner_max_z + _PLACEMENT_TOLERANCE
        ):
            raise ValueError(
                "tx_outer_single_coil outer bounds must fit inside tx_outer_region creation-time bounds "
                f"(modeled_min={(modeled_min_x, modeled_min_y, modeled_min_z)}, "
                f"modeled_max={(modeled_max_x, modeled_max_y, modeled_max_z)}, "
                f"owner_min={(owner_min_x, owner_min_y, owner_min_z)}, "
                f"owner_max={(owner_max_x, owner_max_y, owner_max_z)})"
            )
        return
    if role == "tx_inner_single_coil":
        raise RuntimeError("tx_inner_single_coil bounds require tx_inner_actual_region validation context")
    if plane == "XY":
        target_min_x = owner_min_x if owner_id == "tx_region" else owner_min_x + (owner_size_x - modeled_size_x) / 2.0
        target_min_y = owner_min_y + (owner_size_y - modeled_size_y) / 2.0
        target_min_z = owner_min_z + owner_size_z - modeled_size_z
        if abs(modeled_min_x - target_min_x) > _PLACEMENT_TOLERANCE:
            if owner_id == "tx_region":
                raise ValueError(
                    "tx_rect_void_coil outer bounds min_x must already touch tx_region min_x "
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
) -> list[str]:
    resolved_body_names = resolve_modeled_body_names(
        modeled_entry=modeled_entry,
        imported_object_names=imported_object_names,
        context=context,
    )
    for pcb_name in resolved_body_names["pcb_names"]:
        _apply_object_material_and_visual_state(
            modeler=modeler,
            object_name=pcb_name,
            material_name=_TX_PCB_MATERIAL,
            color=_TX_PCB_COLOR,
            transparency=_TX_PCB_TRANSPARENCY,
            context=f"{context}.pcb[{pcb_name}]",
        )
    for copper_name in resolved_body_names["copper_names"]:
        _apply_copper_material_and_visual_state(
            modeler=modeler,
            object_name=copper_name,
            context=f"{context}.copper[{copper_name}]",
        )
    for ferrite_name in resolved_body_names["underlay_ferrite_names"]:
        _apply_object_material_and_visual_state(
            modeler=modeler,
            object_name=ferrite_name,
            material_name=_DATASET_FERRITE_MATERIAL,
            color=_TX_UNDERLAY_FERRITE_COLOR,
            transparency=_TX_UNDERLAY_FERRITE_TRANSPARENCY,
            context=f"{context}.underlay_ferrite[{ferrite_name}]",
        )
    for pet_psa_name in resolved_body_names["underlay_pet_psa_names"]:
        _apply_object_material_and_visual_state(
            modeler=modeler,
            object_name=pet_psa_name,
            material_name=_PET_PSA_MATERIAL,
            color=_TX_UNDERLAY_PET_PSA_COLOR,
            transparency=_TX_UNDERLAY_PET_PSA_TRANSPARENCY,
            context=f"{context}.underlay_pet_psa[{pet_psa_name}]",
        )
    for air_name in resolved_body_names["underlay_air_names"]:
        _apply_object_material_and_visual_state(
            modeler=modeler,
            object_name=air_name,
            material_name="vacuum",
            color=_TX_UNDERLAY_AIR_COLOR,
            transparency=_TX_UNDERLAY_AIR_TRANSPARENCY,
            context=f"{context}.underlay_air[{air_name}]",
        )
    reconstructed_port_sheet_names = _reconstruct_port_sheet_if_needed(
        modeler=modeler,
        modeled_entry=modeled_entry,
        context=context,
    )
    return list(imported_object_names) + reconstructed_port_sheet_names


__all__ = [
    "ensure_underlay_materials",
    "ensure_pet_psa_material",
    "ensure_notebook_dataset_ferrite_material",
    "set_imported_object_model_state",
    "style_imported_modeled_objects",
    "style_non_model_objects",
    "validate_modeled_bounds_against_owner",
    "validate_tx_inner_modeled_bounds_against_actual_region",
]

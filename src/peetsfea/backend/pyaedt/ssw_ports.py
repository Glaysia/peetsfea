from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Mapping, Sequence
from typing import Callable, Literal, TypeAlias, TypedDict, cast

from peetsfea.aedt import Hfss
from peetsfea.aedt.failfast import raise_on_false
from peetsfea.aedt.protocols import HfssSession, MaterialsSession, ModelerSession
from peetsfea.aedt.proxies import assign_lumped_port, set_object_color, set_object_transparency

DEFAULT_LEDGER_PATH = Path(__file__).resolve().parents[4] / "run" / "ssw_0_3_0_fixed" / "ssw_aedt_port_ledger.json"
DEFAULT_OUTPUT_AEDT_PATH = Path(__file__).resolve().parents[4] / "run" / "ssw_0_3_0_fixed" / "ssw_0_3_0_ports.aedt"
DEFAULT_IMPORTED_LEDGER_PATH = (
    Path(__file__).resolve().parents[4] / "run" / "ssw_0_3_0_fixed" / "ssw_aedt_imported_ledger.json"
)
DEFAULT_DESIGN_NAME = "ssw_0_3_0_ports"
COPPER_COLOR = (184, 115, 51)
COPPER_TRANSPARENCY = 0.0
NON_MODEL_COLOR = (128, 128, 128)
NON_MODEL_TRANSPARENCY = 0.85
FR4_MATERIAL = "fr4"
FR4_PERMITTIVITY = "4.4"
FR4_CONDUCTIVITY = "0"
FR4_DIELECTRIC_LOSS_TANGENT = "0.02"
MULL_FERRITE_ALIAS = "mull_ferrite"
MULL_FERRITE_MATERIAL = "MULL12060ferrite"
MULL_FERRITE_APPEARANCE_RGB = (89, 94, 107)
NOTEBOOK_DATASET_IMPORT_PATH = Path(__file__).resolve().parents[4] / "notebooks" / "mu_p.tab"
MU_R_REAL_DATASET_NAME = "$mu_r_real"
MU_TAND_M_DATASET_NAME = "$mu_tand_m"
MU_R_REAL_DATASET_POINTS = (
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
MU_TAND_M_DATASET_POINTS = (
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

Point3 = tuple[float, float, float]
HfssFactory = Callable[[str], HfssSession]
PortRole = Literal["tx", "rx"]
Axis = Literal["x", "y", "z"]
FaceSide = Literal["min", "max"]
PortEdgeSelection = Literal["nearest_long_face_edges", "axis_spaced_face_edges"]
BoundaryPayloadName = Literal["NAME:1", "NAME:2"]
ExpectedTerminalName = Literal["1_T1", "2_T1"]


class CanonicalCoordinates(TypedDict):
    outer_bounds_min_xyz: list[float]
    outer_bounds_max_xyz: list[float]
    outer_bounds_size_xyz: list[float]


class SswAedtBodyLedgerEntry(TypedDict):
    object_id: str
    role: str
    material: str
    model_state: bool
    canonical_coordinates: CanonicalCoordinates


class SswNearestPortEdgeLedgerEntry(TypedDict):
    role: PortRole
    copper_body_name: str
    selection: Literal["nearest_long_face_edges"]
    face_axis: Axis
    face_side: FaceSide
    anchor_xyz: list[float]
    minimum_edge_length_mm: float


class SswAxisSpacedPortEdgeLedgerEntry(TypedDict):
    role: PortRole
    copper_body_name: str
    selection: Literal["axis_spaced_face_edges"]
    face_axis: Axis
    face_side: FaceSide
    edge_axis: Axis
    spacing_axis: Axis
    edge_length_mm: float
    pair_spacing_mm: float


SswAedtPortEdgeLedgerEntry: TypeAlias = SswNearestPortEdgeLedgerEntry | SswAxisSpacedPortEdgeLedgerEntry


class SswAedtPortStepLedger(TypedDict):
    source_step_ledger_path: str
    scene_step_path: str
    seed: int
    units: Literal["mm"]
    body_names: list[str]
    copper_body_names: list[str]
    non_model_body_names: list[str]
    ferrite_body_names: list[str]
    bodies: list[SswAedtBodyLedgerEntry]
    port_edges: list[SswAedtPortEdgeLedgerEntry]


class VisualAssignment(TypedDict):
    color: list[int]
    transparency: float


class SswAedtImportedLedger(TypedDict):
    source_port_ledger_path: str
    source_step_ledger_path: str
    scene_step_path: str
    aedt_path: str
    imported_object_names: list[str]
    copper_body_names: list[str]
    material_assignments: dict[str, str]
    visual_assignments: dict[str, VisualAssignment]
    non_model_body_names: list[str]
    ferrite_body_names: list[str]


class SswAedtPorts(TypedDict):
    tx: list[str]
    rx: list[str]


class SswAedtPortSetupResult(TypedDict):
    source_port_ledger_path: str
    source_step_ledger_path: str
    scene_step_path: str
    aedt_path: str
    imported_ledger_path: str
    ports: SswAedtPorts
    imported_object_names: list[str]


def create_headless_hfss(design_name: str) -> HfssSession:
    return cast(HfssSession, Hfss(design=design_name, non_graphical=True, new_desktop=True, close_on_exit=False))


def create_graphical_hfss(design_name: str) -> HfssSession:
    return cast(HfssSession, Hfss(design=design_name, non_graphical=False, new_desktop=True, close_on_exit=False))


def write_ssw_aedt_port_ledger(*, ledger_path: Path, ledger: SswAedtPortStepLedger) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_ssw_aedt_port_ledger(ledger_path: Path) -> SswAedtPortStepLedger:
    raw_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(raw_ledger, dict):
        raise TypeError(f"SSW AEDT port ledger must be a JSON object: {ledger_path}")
    for key in (
        "source_step_ledger_path",
        "scene_step_path",
        "seed",
        "units",
        "body_names",
        "copper_body_names",
        "non_model_body_names",
        "ferrite_body_names",
        "bodies",
        "port_edges",
    ):
        if key not in raw_ledger:
            raise ValueError(f"SSW AEDT port ledger is missing required key {key!r}: {ledger_path}")
    return cast(SswAedtPortStepLedger, raw_ledger)


def _required_str_list(ledger: SswAedtPortStepLedger, *, key: str) -> list[str]:
    raw_value = ledger[key]
    if isinstance(raw_value, (str, bytes)) or not isinstance(raw_value, list):
        raise TypeError(f"SSW AEDT port ledger {key} must be a list of strings")
    names: list[str] = []
    for index, raw_name in enumerate(raw_value):
        if not isinstance(raw_name, str):
            raise TypeError(f"SSW AEDT port ledger {key}[{index}] must be str")
        if raw_name == "":
            raise ValueError(f"SSW AEDT port ledger {key}[{index}] must be non-empty")
        names.append(raw_name)
    return names


def _body_materials_by_object_id(ledger: SswAedtPortStepLedger) -> dict[str, str]:
    raw_bodies = ledger["bodies"]
    if isinstance(raw_bodies, (str, bytes)) or not isinstance(raw_bodies, list):
        raise TypeError("SSW AEDT port ledger bodies must be a list")
    body_materials: dict[str, str] = {}
    for index, raw_body in enumerate(raw_bodies):
        if not isinstance(raw_body, dict):
            raise TypeError(f"SSW AEDT port ledger bodies[{index}] must be object")
        if "object_id" not in raw_body:
            raise ValueError(f"SSW AEDT port ledger bodies[{index}] is missing object_id")
        if "material" not in raw_body:
            raise ValueError(f"SSW AEDT port ledger bodies[{index}] is missing material")
        raw_object_id = raw_body["object_id"]
        raw_material = raw_body["material"]
        if not isinstance(raw_object_id, str) or raw_object_id == "":
            raise TypeError(f"SSW AEDT port ledger bodies[{index}].object_id must be non-empty str")
        if not isinstance(raw_material, str) or raw_material == "":
            raise TypeError(f"SSW AEDT port ledger bodies[{index}].material must be non-empty str")
        if raw_object_id in body_materials:
            raise ValueError(f"SSW AEDT port ledger contains duplicate body object_id {raw_object_id!r}")
        body_materials[raw_object_id] = raw_material
    return body_materials


def _assign_object_material(*, hfss: HfssSession, modeler: ModelerSession, object_name: str, material: str) -> str:
    raw_materials = hfss.materials
    assert hasattr(raw_materials, "exists_material"), "Hfss.materials must expose exists_material"
    materials = cast(MaterialsSession, raw_materials)
    raise_on_false(
        materials.exists_material(material),
        operation="Materials.exists_material",
        context={"object_name": object_name, "material": material},
    )
    raise_on_false(
        hfss.assign_material(object_name, material),
        operation="assign_material",
        context={"object_name": object_name, "material": material},
    )
    imported_object = raise_on_false(
        modeler.get_object_from_name(object_name),
        operation="get_object_from_name",
        context={"object_name": object_name},
    )
    assert hasattr(imported_object, "material_name"), (
        f"Imported AEDT object must expose material_name before material assignment (object_name={object_name})"
    )
    assigned_material = getattr(imported_object, "material_name")
    assert isinstance(assigned_material, str), (
        f"Imported AEDT object material_name must read back as str (object_name={object_name})"
    )
    if assigned_material.lower() != material.lower():
        raise RuntimeError(
            "AEDT object material assignment did not stick "
            f"(object_name={object_name}, expected={material!r}, actual={assigned_material!r})"
        )
    return assigned_material


def _set_material_property(material: object, *, material_name: str, attr_name: str, attr_value: str) -> None:
    try:
        setattr(material, attr_name, attr_value)
    except Exception as exc:
        raise RuntimeError(
            "Failed to configure AEDT material property "
            f"(material={material_name}, property={attr_name}, value={attr_value!r})"
        ) from exc


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
        f"Raw project must expose GetDefinitionManager (project_type={type(raw_project).__name__})"
    )
    get_definition_manager = getattr(raw_project, "GetDefinitionManager")
    assert callable(get_definition_manager), "Raw project GetDefinitionManager must be callable"
    definition_manager = get_definition_manager()
    assert definition_manager is not None, "Raw project definition manager must not be null"
    return definition_manager


def _project_material_names(definition_manager: object) -> list[str]:
    assert hasattr(definition_manager, "GetProjectMaterialNames"), (
        "Definition manager must expose GetProjectMaterialNames "
        f"(definition_manager_type={type(definition_manager).__name__})"
    )
    get_project_material_names = getattr(definition_manager, "GetProjectMaterialNames")
    assert callable(get_project_material_names), "Definition manager GetProjectMaterialNames must be callable"
    raw_names = get_project_material_names()
    assert isinstance(raw_names, Sequence), (
        "Definition manager GetProjectMaterialNames result must be a sequence "
        f"(actual={type(raw_names).__name__})"
    )
    assert not isinstance(raw_names, (str, bytes)), "Definition manager GetProjectMaterialNames must not be str/bytes"
    names: list[str] = []
    for index, raw_name in enumerate(raw_names):
        assert isinstance(raw_name, str), (
            "Definition manager GetProjectMaterialNames items must be str "
            f"(index={index}, actual={type(raw_name).__name__})"
        )
        if raw_name == "":
            raise ValueError(f"Definition manager GetProjectMaterialNames returned empty name at index {index}")
        names.append(raw_name)
    return names


def _dataset_ferrite_material_payload() -> list[object]:
    red, green, blue = MULL_FERRITE_APPEARANCE_RGB
    return [
        f"NAME:{MULL_FERRITE_MATERIAL}",
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
        f"pwlx({MU_R_REAL_DATASET_NAME}, Freq)",
        "conductivity:=",
        "0.01",
        "magnetic_loss_tangent:=",
        f"pwlx({MU_TAND_M_DATASET_NAME}, Freq)",
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
    definition_manager = _definition_manager(_raw_project(hfss))
    payload = _dataset_ferrite_material_payload()
    material_names = _project_material_names(definition_manager)
    existing_case_name = next(
        (name for name in material_names if name.casefold() == MULL_FERRITE_MATERIAL.casefold()),
        None,
    )
    if existing_case_name is None:
        assert hasattr(definition_manager, "AddMaterial"), (
            "Definition manager must expose AddMaterial "
            f"(definition_manager_type={type(definition_manager).__name__})"
        )
        add_material = getattr(definition_manager, "AddMaterial")
        assert callable(add_material), "Definition manager AddMaterial must be callable"
        add_material(payload)
    else:
        assert hasattr(definition_manager, "EditMaterial"), (
            "Definition manager must expose EditMaterial "
            f"(definition_manager_type={type(definition_manager).__name__})"
        )
        edit_material = getattr(definition_manager, "EditMaterial")
        assert callable(edit_material), "Definition manager EditMaterial must be callable"
        edit_material(existing_case_name, payload)
    persisted_names = _project_material_names(definition_manager)
    if not any(name.casefold() == MULL_FERRITE_MATERIAL.casefold() for name in persisted_names):
        raise RuntimeError(
            "Project ferrite material definition was not persisted after AddMaterial/EditMaterial "
            f"(material_name={MULL_FERRITE_MATERIAL})"
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


def _ensure_notebook_dataset_ferrite_material(hfss: HfssSession) -> str:
    if not NOTEBOOK_DATASET_IMPORT_PATH.is_file():
        raise FileNotFoundError(f"Notebook ferrite dataset tab file is missing: {NOTEBOOK_DATASET_IMPORT_PATH}")

    raw_design = _raw_design(hfss)
    assert hasattr(raw_design, "ImportDataset"), (
        f"Raw design must expose ImportDataset for ferrite dataset import (design_type={type(raw_design).__name__})"
    )
    import_dataset = getattr(raw_design, "ImportDataset")
    assert callable(import_dataset), "Raw design ImportDataset must be callable"
    raise_on_false(
        import_dataset(str(NOTEBOOK_DATASET_IMPORT_PATH)),
        operation="ImportDataset",
        context={"path": str(NOTEBOOK_DATASET_IMPORT_PATH)},
    )

    raw_project = _raw_project(hfss)
    assert hasattr(raw_project, "AddDataset"), (
        f"Raw project must expose AddDataset for ferrite material datasets (project_type={type(raw_project).__name__})"
    )
    add_dataset = getattr(raw_project, "AddDataset")
    assert callable(add_dataset), "Raw project AddDataset must be callable"
    raise_on_false(
        add_dataset(_dataset_payload(MU_R_REAL_DATASET_NAME, points=MU_R_REAL_DATASET_POINTS)),
        operation="AddDataset",
        context={"dataset_name": MU_R_REAL_DATASET_NAME},
    )
    raise_on_false(
        add_dataset(_dataset_payload(MU_TAND_M_DATASET_NAME, points=MU_TAND_M_DATASET_POINTS)),
        operation="AddDataset",
        context={"dataset_name": MU_TAND_M_DATASET_NAME},
    )
    _ensure_project_dataset_ferrite_material_definition(hfss)
    _sync_pyaedt_material_lookup(hfss, material_name=MULL_FERRITE_MATERIAL)
    return MULL_FERRITE_MATERIAL


def _ensure_fr4_material(hfss: HfssSession) -> str:
    raw_materials = hfss.materials
    assert hasattr(raw_materials, "exists_material"), "Hfss.materials must expose exists_material"
    assert hasattr(raw_materials, "add_material"), "Hfss.materials must expose add_material"
    assert hasattr(raw_materials, "material_keys"), "Hfss.materials must expose material_keys"
    materials = cast(MaterialsSession, raw_materials)
    exists = bool(materials.exists_material(FR4_MATERIAL))
    if exists:
        material_keys = materials.material_keys
        assert FR4_MATERIAL in material_keys, (
            f"AEDT material_keys must contain {FR4_MATERIAL} after exists_material(name)=True"
        )
        material = material_keys[FR4_MATERIAL]
    else:
        material = raise_on_false(
            materials.add_material(FR4_MATERIAL),
            operation="add_material",
            context={"name": FR4_MATERIAL},
        )
    for attr_name, attr_value in (
        ("permeability", "1.0"),
        ("permittivity", FR4_PERMITTIVITY),
        ("conductivity", FR4_CONDUCTIVITY),
        ("dielectric_loss_tangent", FR4_DIELECTRIC_LOSS_TANGENT),
        ("magnetic_loss_tangent", "0"),
    ):
        _set_material_property(
            material,
            material_name=FR4_MATERIAL,
            attr_name=attr_name,
            attr_value=attr_value,
        )
    return FR4_MATERIAL


def _ensure_repo_owned_material(*, hfss: HfssSession, material: str) -> str:
    if material == FR4_MATERIAL:
        return _ensure_fr4_material(hfss)
    if material in (MULL_FERRITE_ALIAS, MULL_FERRITE_MATERIAL):
        return _ensure_notebook_dataset_ferrite_material(hfss)
    return material


def _imported_object_ref(*, modeler: ModelerSession, object_name: str) -> object:
    return raise_on_false(
        modeler.get_object_from_name(object_name),
        operation="get_object_from_name",
        context={"object_name": object_name},
    )


def _apply_visual_state(
    *,
    modeler: ModelerSession,
    object_name: str,
    color: tuple[int, int, int],
    transparency: float,
) -> VisualAssignment:
    object_ref = _imported_object_ref(modeler=modeler, object_name=object_name)
    set_object_color(object_ref, color=color)
    set_object_transparency(object_ref, transparency=transparency)
    return {"color": [color[0], color[1], color[2]], "transparency": transparency}


def _assign_body_materials(
    *,
    hfss: HfssSession,
    modeler: ModelerSession,
    ledger: SswAedtPortStepLedger,
    body_names: list[str],
) -> dict[str, str]:
    body_materials = _body_materials_by_object_id(ledger)
    material_assignments: dict[str, str] = {}
    for object_name in body_names:
        if object_name not in body_materials:
            raise ValueError(f"SSW body has no material entry (object_name={object_name})")
        material = body_materials[object_name]
        assignment_material = _ensure_repo_owned_material(hfss=hfss, material=material)
        material_assignments[object_name] = _assign_object_material(
            hfss=hfss,
            modeler=modeler,
            object_name=object_name,
            material=assignment_material,
        )
    return material_assignments


def _import_ssw_aedt_port_step(
    *,
    hfss: HfssSession,
    ledger_path: Path,
    output_aedt_path: Path,
    ledger: SswAedtPortStepLedger,
) -> SswAedtImportedLedger:
    scene_step_path = Path(ledger["scene_step_path"])
    before_names = set(hfss.modeler.object_names)
    raise_on_false(
        hfss.modeler.import_3d_cad(
            scene_step_path,
            create_group=False,
            import_free_surfaces=False,
            import_materials=False,
        ),
        operation="import_3d_cad",
        context={"scene_step_path": str(scene_step_path)},
    )
    after_names = set(hfss.modeler.object_names)
    expected_names = set(_required_str_list(ledger, key="body_names"))
    missing_names = sorted(expected_names.difference(after_names))
    if missing_names:
        raise ValueError(f"SSW AEDT port STEP import did not create required bodies (missing={missing_names})")
    imported_names = sorted(name for name in after_names if name in expected_names or name not in before_names)
    body_names = _required_str_list(ledger, key="body_names")
    copper_body_names = _required_str_list(ledger, key="copper_body_names")
    material_assignments = _assign_body_materials(
        hfss=hfss,
        modeler=hfss.modeler,
        ledger=ledger,
        body_names=body_names,
    )
    non_model_names = _required_str_list(ledger, key="non_model_body_names")
    ferrite_names = _required_str_list(ledger, key="ferrite_body_names")
    for non_model_name in non_model_names:
        raise_on_false(
            hfss.modeler.set_object_model_state(non_model_name, False),
            operation="set_object_model_state",
            context={"name": non_model_name, "model": False},
        )
    visual_assignments: dict[str, VisualAssignment] = {}
    ferrite_set = set(ferrite_names)
    non_model_set = set(non_model_names)
    overlap = sorted(ferrite_set.intersection(non_model_set))
    if overlap:
        raise ValueError(f"SSW ferrite bodies must remain model objects, not non-model objects (overlap={overlap})")
    for object_name in non_model_names:
        visual_assignments[object_name] = _apply_visual_state(
            modeler=hfss.modeler,
            object_name=object_name,
            color=NON_MODEL_COLOR,
            transparency=NON_MODEL_TRANSPARENCY,
        )
    for object_name in copper_body_names:
        visual_assignments[object_name] = _apply_visual_state(
            modeler=hfss.modeler,
            object_name=object_name,
            color=COPPER_COLOR,
            transparency=COPPER_TRANSPARENCY,
        )
    return {
        "source_port_ledger_path": str(ledger_path),
        "source_step_ledger_path": ledger["source_step_ledger_path"],
        "scene_step_path": str(scene_step_path),
        "aedt_path": str(output_aedt_path),
        "imported_object_names": imported_names,
        "copper_body_names": copper_body_names,
        "material_assignments": material_assignments,
        "visual_assignments": visual_assignments,
        "non_model_body_names": non_model_names,
        "ferrite_body_names": ferrite_names,
    }


def _edge_vertices_xyz(modeler: ModelerSession, *, edge_id: int) -> tuple[Point3, Point3]:
    vertex_ids = modeler.get_edge_vertices(edge_id)
    if len(vertex_ids) != 2:
        raise ValueError(f"edge {edge_id} must expose exactly two vertices")
    first = modeler.get_vertex_position(int(vertex_ids[0]))
    second = modeler.get_vertex_position(int(vertex_ids[1]))
    if len(first) != 3 or len(second) != 3:
        raise ValueError(f"edge {edge_id} vertices must expose 3D positions")
    return (
        (float(first[0]), float(first[1]), float(first[2])),
        (float(second[0]), float(second[1]), float(second[2])),
    )


class EdgeSnapshot(TypedDict):
    edge_id: int
    vertices_xyz: tuple[Point3, Point3]
    midpoint_xyz: Point3
    length_mm: float


EDGE_TOLERANCE_MM = 1e-5


def _axis_index(axis: Axis) -> int:
    if axis == "x":
        return 0
    if axis == "y":
        return 1
    if axis == "z":
        return 2
    raise ValueError(f"unsupported axis {axis!r}")


def _edge_length(vertices: tuple[Point3, Point3]) -> float:
    return (
        (vertices[0][0] - vertices[1][0]) ** 2
        + (vertices[0][1] - vertices[1][1]) ** 2
        + (vertices[0][2] - vertices[1][2]) ** 2
    ) ** 0.5


def _edge_midpoint(vertices: tuple[Point3, Point3]) -> Point3:
    return (
        (vertices[0][0] + vertices[1][0]) / 2.0,
        (vertices[0][1] + vertices[1][1]) / 2.0,
        (vertices[0][2] + vertices[1][2]) / 2.0,
    )


def _point_distance(first: Point3, second: Point3) -> float:
    return (
        (first[0] - second[0]) ** 2
        + (first[1] - second[1]) ** 2
        + (first[2] - second[2]) ** 2
    ) ** 0.5


def _object_edge_snapshots(*, modeler: ModelerSession, object_name: str) -> list[EdgeSnapshot]:
    snapshots: list[EdgeSnapshot] = []
    for raw_edge_id in modeler.get_object_edges(object_name):
        edge_id = int(raw_edge_id)
        vertices = _edge_vertices_xyz(modeler, edge_id=edge_id)
        snapshots.append(
            {
                "edge_id": edge_id,
                "vertices_xyz": vertices,
                "midpoint_xyz": _edge_midpoint(vertices),
                "length_mm": _edge_length(vertices),
            }
        )
    if len(snapshots) == 0:
        raise ValueError(f"imported copper object has no edges (object_name={object_name})")
    return snapshots


def _face_coordinate(edges: list[EdgeSnapshot], *, axis: Axis, side: FaceSide) -> float:
    axis_i = _axis_index(axis)
    coordinates = [point[axis_i] for edge in edges for point in edge["vertices_xyz"]]
    if side == "min":
        return min(coordinates)
    if side == "max":
        return max(coordinates)
    raise ValueError(f"unsupported face side {side!r}")


def _edge_on_face(edge: EdgeSnapshot, *, axis: Axis, coordinate: float) -> bool:
    axis_i = _axis_index(axis)
    return all(abs(point[axis_i] - coordinate) <= EDGE_TOLERANCE_MM for point in edge["vertices_xyz"])


def _edge_aligned_to_axis(edge: EdgeSnapshot, *, axis: Axis) -> bool:
    axis_i = _axis_index(axis)
    first, second = edge["vertices_xyz"]
    deltas = (abs(first[0] - second[0]), abs(first[1] - second[1]), abs(first[2] - second[2]))
    if deltas[axis_i] <= EDGE_TOLERANCE_MM:
        return False
    return all(delta <= EDGE_TOLERANCE_MM for index, delta in enumerate(deltas) if index != axis_i)


def _point_from_rows(raw_point: list[float], *, context: str) -> Point3:
    if len(raw_point) != 3:
        raise ValueError(f"{context} must contain exactly three coordinates")
    return (float(raw_point[0]), float(raw_point[1]), float(raw_point[2]))


def _remaining_axis(*, face_axis: Axis, spacing_axis: Axis) -> Axis:
    if face_axis == spacing_axis:
        raise ValueError(f"face_axis and spacing_axis must differ (axis={face_axis})")
    if face_axis != "x" and spacing_axis != "x":
        return "x"
    if face_axis != "y" and spacing_axis != "y":
        return "y"
    if face_axis != "z" and spacing_axis != "z":
        return "z"
    raise ValueError(f"face_axis and spacing_axis must leave one remaining axis (face={face_axis}, spacing={spacing_axis})")


def _resolve_nearest_long_face_edge_ids(
    *,
    modeler: ModelerSession,
    spec: SswNearestPortEdgeLedgerEntry,
    context: str,
) -> list[int]:
    edges = _object_edge_snapshots(modeler=modeler, object_name=spec["copper_body_name"])
    face_coordinate = _face_coordinate(edges, axis=spec["face_axis"], side=spec["face_side"])
    anchor = _point_from_rows(spec["anchor_xyz"], context=f"{context}.anchor_xyz")
    minimum_length = float(spec["minimum_edge_length_mm"])
    candidates = [
        edge
        for edge in edges
        if _edge_on_face(edge, axis=spec["face_axis"], coordinate=face_coordinate)
        and edge["length_mm"] + EDGE_TOLERANCE_MM >= minimum_length
    ]
    if len(candidates) < 2:
        raise ValueError(
            f"{context} requires at least two long face edges "
            f"(object_name={spec['copper_body_name']}, face_axis={spec['face_axis']}, candidates={len(candidates)})"
        )
    candidates.sort(key=lambda edge: (_point_distance(edge["midpoint_xyz"], anchor), edge["edge_id"]))
    return sorted(edge["edge_id"] for edge in candidates[:2])


def _resolve_axis_spaced_face_edge_ids(
    *,
    modeler: ModelerSession,
    spec: SswAxisSpacedPortEdgeLedgerEntry,
    context: str,
) -> list[int]:
    edges = _object_edge_snapshots(modeler=modeler, object_name=spec["copper_body_name"])
    face_coordinate = _face_coordinate(edges, axis=spec["face_axis"], side=spec["face_side"])
    expected_length = float(spec["edge_length_mm"])
    candidate_edges = [
        edge
        for edge in edges
        if _edge_on_face(edge, axis=spec["face_axis"], coordinate=face_coordinate)
        and _edge_aligned_to_axis(edge, axis=spec["edge_axis"])
        and abs(edge["length_mm"] - expected_length) <= EDGE_TOLERANCE_MM
    ]
    spacing_axis = spec["spacing_axis"]
    spacing_i = _axis_index(spacing_axis)
    remaining_i = _axis_index(_remaining_axis(face_axis=spec["face_axis"], spacing_axis=spacing_axis))
    expected_spacing = float(spec["pair_spacing_mm"])
    matching_pairs: list[tuple[int, int]] = []
    for first_index, first_edge in enumerate(candidate_edges):
        for second_edge in candidate_edges[first_index + 1 :]:
            first_midpoint = first_edge["midpoint_xyz"]
            second_midpoint = second_edge["midpoint_xyz"]
            same_remaining = abs(first_midpoint[remaining_i] - second_midpoint[remaining_i]) <= EDGE_TOLERANCE_MM
            spacing = abs(first_midpoint[spacing_i] - second_midpoint[spacing_i])
            if same_remaining and abs(spacing - expected_spacing) <= EDGE_TOLERANCE_MM:
                matching_pairs.append((first_edge["edge_id"], second_edge["edge_id"]))
    if len(matching_pairs) != 1:
        raise ValueError(
            f"{context} requires exactly one axis-spaced edge pair "
            f"(object_name={spec['copper_body_name']}, matches={matching_pairs})"
        )
    return sorted([matching_pairs[0][0], matching_pairs[0][1]])


def _capture_expected_excitation(*, hfss: HfssSession, expected_name: str, context: str) -> str:
    names = list(hfss.excitation_names)
    if expected_name not in names:
        raise ValueError(f"{context} did not create expected excitation (expected={expected_name!r}, available={names})")
    return expected_name


def _required_raw_key(raw_entry: dict[str, object], *, key: str, context: str) -> object:
    if key not in raw_entry:
        raise ValueError(f"{context} is missing required key {key!r}")
    return raw_entry[key]


def _required_raw_str(raw_entry: dict[str, object], *, key: str, context: str) -> str:
    raw_value = _required_raw_key(raw_entry, key=key, context=context)
    if not isinstance(raw_value, str) or raw_value == "":
        raise TypeError(f"{context}.{key} must be a non-empty str")
    return raw_value


def _required_raw_float(raw_entry: dict[str, object], *, key: str, context: str) -> float:
    raw_value = _required_raw_key(raw_entry, key=key, context=context)
    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
        raise TypeError(f"{context}.{key} must be numeric")
    return float(raw_value)


def _required_raw_point(raw_entry: dict[str, object], *, key: str, context: str) -> list[float]:
    raw_value = _required_raw_key(raw_entry, key=key, context=context)
    if isinstance(raw_value, (str, bytes)) or not isinstance(raw_value, list):
        raise TypeError(f"{context}.{key} must be a list of three numbers")
    if len(raw_value) != 3:
        raise ValueError(f"{context}.{key} must contain exactly three entries")
    point: list[float] = []
    for index, component in enumerate(raw_value):
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise TypeError(f"{context}.{key}[{index}] must be numeric")
        point.append(float(component))
    return point


def _required_port_role(raw_entry: dict[str, object], *, context: str) -> PortRole:
    role = _required_raw_str(raw_entry, key="role", context=context)
    if role == "tx" or role == "rx":
        return role
    raise ValueError(f"{context}.role must be tx or rx (actual={role!r})")


def _required_axis(raw_entry: dict[str, object], *, key: str, context: str) -> Axis:
    axis = _required_raw_str(raw_entry, key=key, context=context)
    if axis == "x" or axis == "y" or axis == "z":
        return axis
    raise ValueError(f"{context}.{key} must be x, y, or z (actual={axis!r})")


def _required_face_side(raw_entry: dict[str, object], *, context: str) -> FaceSide:
    face_side = _required_raw_str(raw_entry, key="face_side", context=context)
    if face_side == "min" or face_side == "max":
        return face_side
    raise ValueError(f"{context}.face_side must be min or max (actual={face_side!r})")


def _nearest_port_edge_entry(raw_entry: dict[str, object], *, context: str) -> SswNearestPortEdgeLedgerEntry:
    minimum_edge_length_mm = _required_raw_float(raw_entry, key="minimum_edge_length_mm", context=context)
    if minimum_edge_length_mm <= 0.0:
        raise ValueError(f"{context}.minimum_edge_length_mm must be positive")
    return {
        "role": _required_port_role(raw_entry, context=context),
        "copper_body_name": _required_raw_str(raw_entry, key="copper_body_name", context=context),
        "selection": "nearest_long_face_edges",
        "face_axis": _required_axis(raw_entry, key="face_axis", context=context),
        "face_side": _required_face_side(raw_entry, context=context),
        "anchor_xyz": _required_raw_point(raw_entry, key="anchor_xyz", context=context),
        "minimum_edge_length_mm": minimum_edge_length_mm,
    }


def _axis_spaced_port_edge_entry(raw_entry: dict[str, object], *, context: str) -> SswAxisSpacedPortEdgeLedgerEntry:
    edge_length_mm = _required_raw_float(raw_entry, key="edge_length_mm", context=context)
    pair_spacing_mm = _required_raw_float(raw_entry, key="pair_spacing_mm", context=context)
    if edge_length_mm <= 0.0:
        raise ValueError(f"{context}.edge_length_mm must be positive")
    if pair_spacing_mm <= 0.0:
        raise ValueError(f"{context}.pair_spacing_mm must be positive")
    return {
        "role": _required_port_role(raw_entry, context=context),
        "copper_body_name": _required_raw_str(raw_entry, key="copper_body_name", context=context),
        "selection": "axis_spaced_face_edges",
        "face_axis": _required_axis(raw_entry, key="face_axis", context=context),
        "face_side": _required_face_side(raw_entry, context=context),
        "edge_axis": _required_axis(raw_entry, key="edge_axis", context=context),
        "spacing_axis": _required_axis(raw_entry, key="spacing_axis", context=context),
        "edge_length_mm": edge_length_mm,
        "pair_spacing_mm": pair_spacing_mm,
    }


def _port_edges_by_role(ledger: SswAedtPortStepLedger) -> dict[PortRole, SswAedtPortEdgeLedgerEntry]:
    raw_edges = ledger["port_edges"]
    if isinstance(raw_edges, (str, bytes)) or not isinstance(raw_edges, list):
        raise TypeError("SSW AEDT port ledger port_edges must be a list")
    edges_by_role: dict[PortRole, SswAedtPortEdgeLedgerEntry] = {}
    for index, raw_edge in enumerate(raw_edges):
        context = f"SSW AEDT port ledger port_edges[{index}]"
        if not isinstance(raw_edge, dict):
            raise TypeError(f"{context} must be object")
        raw_entry = cast(dict[str, object], raw_edge)
        selection = _required_raw_str(raw_entry, key="selection", context=context)
        if selection == "nearest_long_face_edges":
            entry: SswAedtPortEdgeLedgerEntry = _nearest_port_edge_entry(raw_entry, context=context)
        elif selection == "axis_spaced_face_edges":
            entry = _axis_spaced_port_edge_entry(raw_entry, context=context)
        else:
            raise ValueError(f"{context}.selection is unsupported (actual={selection!r})")
        role = entry["role"]
        if role in edges_by_role:
            raise ValueError(f"SSW AEDT port ledger contains duplicate port edge role {role!r}")
        edges_by_role[role] = entry
    if set(edges_by_role) != {"tx", "rx"}:
        raise ValueError(f"SSW AEDT port ledger requires tx and rx port edges (actual={sorted(edges_by_role)})")
    return edges_by_role


def _assign_one_port(
    *,
    hfss: HfssSession,
    modeler: ModelerSession,
    edge_spec: SswAedtPortEdgeLedgerEntry,
    boundary_name: BoundaryPayloadName,
    expected_terminal_name: ExpectedTerminalName,
    context: str,
) -> str:
    selection = edge_spec["selection"]
    if selection == "nearest_long_face_edges":
        edge_ids = _resolve_nearest_long_face_edge_ids(
            modeler=modeler,
            spec=cast(SswNearestPortEdgeLedgerEntry, edge_spec),
            context=context,
        )
    elif selection == "axis_spaced_face_edges":
        edge_ids = _resolve_axis_spaced_face_edge_ids(
            modeler=modeler,
            spec=cast(SswAxisSpacedPortEdgeLedgerEntry, edge_spec),
            context=context,
        )
    else:
        raise ValueError(f"{context} has unsupported port edge selection {selection!r}")
    assign_lumped_port(
        hfss.oboundary,
        [
            boundary_name,
            "Edges:=",
            edge_ids,
            "LumpedPortType:=",
            "Terminal",
            "DoDeembed:=",
            False,
            "RenormalizeAllTerminals:=",
            True,
            "ShowReporterFilter:=",
            False,
            "Impedance:=",
            "50ohm",
        ],
        context=context,
    )
    return _capture_expected_excitation(hfss=hfss, expected_name=expected_terminal_name, context=context)


def _assign_ports(*, hfss: HfssSession, ledger: SswAedtPortStepLedger) -> SswAedtPorts:
    edges_by_role = _port_edges_by_role(ledger)
    return {
        "tx": [
            _assign_one_port(
                hfss=hfss,
                modeler=hfss.modeler,
                edge_spec=edges_by_role["tx"],
                boundary_name="NAME:1",
                expected_terminal_name="1_T1",
                context="ssw.tx_port",
            )
        ],
        "rx": [
            _assign_one_port(
                hfss=hfss,
                modeler=hfss.modeler,
                edge_spec=edges_by_role["rx"],
                boundary_name="NAME:2",
                expected_terminal_name="2_T1",
                context="ssw.rx_port",
            )
        ],
    }


def _write_imported_ledger(*, imported_ledger_path: Path, imported_ledger: SswAedtImportedLedger) -> None:
    imported_ledger_path.parent.mkdir(parents=True, exist_ok=True)
    imported_ledger_path.write_text(json.dumps(imported_ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def setup_ssw_aedt_ports_into_hfss(
    *,
    hfss: HfssSession,
    port_ledger_path: Path = DEFAULT_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
) -> SswAedtPortSetupResult:
    ledger = load_ssw_aedt_port_ledger(port_ledger_path)
    output_aedt_path.parent.mkdir(parents=True, exist_ok=True)
    imported_ledger = _import_ssw_aedt_port_step(
        hfss=hfss,
        ledger_path=port_ledger_path,
        output_aedt_path=output_aedt_path,
        ledger=ledger,
    )
    ports = _assign_ports(hfss=hfss, ledger=ledger)
    raise_on_false(hfss.save_project(str(output_aedt_path)), operation="save_project", context={"path": str(output_aedt_path)})
    _write_imported_ledger(imported_ledger_path=imported_ledger_path, imported_ledger=imported_ledger)
    return {
        "source_port_ledger_path": str(port_ledger_path),
        "source_step_ledger_path": imported_ledger["source_step_ledger_path"],
        "scene_step_path": imported_ledger["scene_step_path"],
        "aedt_path": str(output_aedt_path),
        "imported_ledger_path": str(imported_ledger_path),
        "ports": ports,
        "imported_object_names": imported_ledger["imported_object_names"],
    }


def setup_ssw_aedt_ports(
    *,
    port_ledger_path: Path = DEFAULT_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
    design_name: str = DEFAULT_DESIGN_NAME,
    hfss_factory: HfssFactory = create_headless_hfss,
    release_desktop_on_exit: bool = True,
    close_projects_on_release: bool = True,
) -> SswAedtPortSetupResult:
    hfss = hfss_factory(design_name)
    try:
        return setup_ssw_aedt_ports_into_hfss(
            hfss=hfss,
            port_ledger_path=port_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
        )
    finally:
        if release_desktop_on_exit:
            raise_on_false(
                hfss.desktop_class.release_desktop(close_projects=close_projects_on_release, close_on_exit=True),
                operation="release_desktop",
                context={"close_projects": close_projects_on_release, "close_on_exit": True},
            )


__all__ = [
    "DEFAULT_DESIGN_NAME",
    "DEFAULT_IMPORTED_LEDGER_PATH",
    "DEFAULT_LEDGER_PATH",
    "DEFAULT_OUTPUT_AEDT_PATH",
    "HfssFactory",
    "CanonicalCoordinates",
    "SswAedtBodyLedgerEntry",
    "SswAedtImportedLedger",
    "SswAedtPortEdgeLedgerEntry",
    "SswAedtPorts",
    "SswAedtPortSetupResult",
    "SswAedtPortStepLedger",
    "create_graphical_hfss",
    "create_headless_hfss",
    "load_ssw_aedt_port_ledger",
    "setup_ssw_aedt_ports",
    "setup_ssw_aedt_ports_into_hfss",
    "write_ssw_aedt_port_ledger",
]

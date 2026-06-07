from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Literal, TypedDict, cast

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
PORT_SHEET_COLOR = (180, 215, 255)
PORT_SHEET_TRANSPARENCY = 0.88

Point3 = tuple[float, float, float]
HfssFactory = Callable[[str], HfssSession]
PortRole = Literal["tx", "rx"]


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


class SswAedtPortCellLedgerEntry(TypedDict):
    role: PortRole
    port_sheet_name: str
    port_sheet_vertices_xyz: list[list[float]]
    signal_edge_vertices_xyz: list[list[float]]
    reference_edge_vertices_xyz: list[list[float]]


class SswAedtPortStepLedger(TypedDict):
    source_step_ledger_path: str
    scene_step_path: str
    seed: int
    units: Literal["mm"]
    body_names: list[str]
    copper_body_names: list[str]
    port_sheet_names: list[str]
    non_model_body_names: list[str]
    bodies: list[SswAedtBodyLedgerEntry]
    port_cells: list[SswAedtPortCellLedgerEntry]


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
    port_sheet_names: list[str]
    non_model_body_names: list[str]


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
        "port_sheet_names",
        "non_model_body_names",
        "bodies",
        "port_cells",
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
    imported_object = raise_on_false(
        modeler.get_object_from_name(object_name),
        operation="get_object_from_name",
        context={"object_name": object_name},
    )
    assert hasattr(imported_object, "material_name"), (
        f"Imported AEDT object must expose material_name before material assignment (object_name={object_name})"
    )
    setattr(imported_object, "material_name", material)
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


def _assign_copper_materials(
    *,
    hfss: HfssSession,
    modeler: ModelerSession,
    ledger: SswAedtPortStepLedger,
    copper_body_names: list[str],
) -> dict[str, str]:
    body_materials = _body_materials_by_object_id(ledger)
    material_assignments: dict[str, str] = {}
    for object_name in copper_body_names:
        if object_name not in body_materials:
            raise ValueError(f"SSW copper body has no material entry (object_name={object_name})")
        material = body_materials[object_name]
        if material.lower() != "copper":
            raise ValueError(
                "SSW AEDT copper body must use copper material "
                f"(object_name={object_name}, material={material!r})"
            )
        material_assignments[object_name] = _assign_object_material(
            hfss=hfss,
            modeler=modeler,
            object_name=object_name,
            material=material,
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
            import_free_surfaces=True,
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
    copper_body_names = _required_str_list(ledger, key="copper_body_names")
    material_assignments = _assign_copper_materials(
        hfss=hfss,
        modeler=hfss.modeler,
        ledger=ledger,
        copper_body_names=copper_body_names,
    )
    non_model_names = _required_str_list(ledger, key="non_model_body_names")
    port_sheet_names = _required_str_list(ledger, key="port_sheet_names")
    for non_model_name in non_model_names:
        raise_on_false(
            hfss.modeler.set_object_model_state(non_model_name, False),
            operation="set_object_model_state",
            context={"name": non_model_name, "model": False},
        )
    visual_assignments: dict[str, VisualAssignment] = {}
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
    for object_name in port_sheet_names:
        visual_assignments[object_name] = _apply_visual_state(
            modeler=hfss.modeler,
            object_name=object_name,
            color=PORT_SHEET_COLOR,
            transparency=PORT_SHEET_TRANSPARENCY,
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
        "port_sheet_names": port_sheet_names,
        "non_model_body_names": non_model_names,
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


def _same_point(first: Point3, second: Point3) -> bool:
    return abs(first[0] - second[0]) <= 1e-6 and abs(first[1] - second[1]) <= 1e-6 and abs(first[2] - second[2]) <= 1e-6


def _same_edge(actual: tuple[Point3, Point3], expected: tuple[Point3, Point3]) -> bool:
    return (_same_point(actual[0], expected[0]) and _same_point(actual[1], expected[1])) or (
        _same_point(actual[0], expected[1]) and _same_point(actual[1], expected[0])
    )


def _edge_from_vertex_rows(raw_rows: list[list[float]], *, context: str) -> tuple[Point3, Point3]:
    if len(raw_rows) != 2:
        raise ValueError(f"{context} must contain exactly two vertices")
    vertices: list[Point3] = []
    for index, raw_vertex in enumerate(raw_rows):
        if len(raw_vertex) != 3:
            raise ValueError(f"{context}[{index}] must contain exactly three coordinates")
        vertices.append((float(raw_vertex[0]), float(raw_vertex[1]), float(raw_vertex[2])))
    return (vertices[0], vertices[1])


def _resolve_sheet_edge_id(
    *,
    modeler: ModelerSession,
    sheet_name: str,
    expected_edge: tuple[Point3, Point3],
    context: str,
) -> int:
    matches: list[int] = []
    for raw_edge_id in modeler.get_object_edges(sheet_name):
        edge_id = int(raw_edge_id)
        if _same_edge(_edge_vertices_xyz(modeler, edge_id=edge_id), expected_edge):
            matches.append(edge_id)
    if len(matches) != 1:
        raise ValueError(f"{context} must resolve exactly one sheet edge (sheet={sheet_name}, matches={matches})")
    return matches[0]


def _capture_expected_excitation(*, hfss: HfssSession, expected_name: str, context: str) -> str:
    names = list(hfss.excitation_names)
    if expected_name not in names:
        raise ValueError(f"{context} did not create expected excitation (expected={expected_name!r}, available={names})")
    return expected_name


def _port_cells_by_role(ledger: SswAedtPortStepLedger) -> dict[PortRole, SswAedtPortCellLedgerEntry]:
    raw_cells = ledger["port_cells"]
    if isinstance(raw_cells, (str, bytes)) or not isinstance(raw_cells, list):
        raise TypeError("SSW AEDT port ledger port_cells must be a list")
    cells_by_role: dict[PortRole, SswAedtPortCellLedgerEntry] = {}
    for index, raw_cell in enumerate(raw_cells):
        if not isinstance(raw_cell, dict):
            raise TypeError(f"SSW AEDT port ledger port_cells[{index}] must be object")
        cell = cast(SswAedtPortCellLedgerEntry, raw_cell)
        role = cell["role"]
        if role not in {"tx", "rx"}:
            raise ValueError(f"SSW AEDT port cell role must be tx or rx (actual={role!r})")
        if role in cells_by_role:
            raise ValueError(f"SSW AEDT port ledger contains duplicate port cell role {role!r}")
        cells_by_role[role] = cell
    if set(cells_by_role) != {"tx", "rx"}:
        raise ValueError(f"SSW AEDT port ledger requires tx and rx port cells (actual={sorted(cells_by_role)})")
    return cells_by_role


def _assign_one_port(
    *,
    hfss: HfssSession,
    modeler: ModelerSession,
    cell: SswAedtPortCellLedgerEntry,
    slot: str,
    context: str,
) -> str:
    sheet_name = cell["port_sheet_name"]
    signal_edge_id = _resolve_sheet_edge_id(
        modeler=modeler,
        sheet_name=sheet_name,
        expected_edge=_edge_from_vertex_rows(cell["signal_edge_vertices_xyz"], context=f"{context}.signal_edge_vertices_xyz"),
        context=f"{context}.signal",
    )
    reference_edge_id = _resolve_sheet_edge_id(
        modeler=modeler,
        sheet_name=sheet_name,
        expected_edge=_edge_from_vertex_rows(cell["reference_edge_vertices_xyz"], context=f"{context}.reference_edge_vertices_xyz"),
        context=f"{context}.reference",
    )
    assign_lumped_port(
        hfss.oboundary,
        [
            f"NAME:{slot}",
            "Edges:=",
            [signal_edge_id, reference_edge_id],
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
    return _capture_expected_excitation(hfss=hfss, expected_name=f"{slot}_T1", context=context)


def _assign_ports(*, hfss: HfssSession, ledger: SswAedtPortStepLedger) -> SswAedtPorts:
    cells_by_role = _port_cells_by_role(ledger)
    return {
        "tx": [_assign_one_port(hfss=hfss, modeler=hfss.modeler, cell=cells_by_role["tx"], slot="1", context="ssw.tx_port")],
        "rx": [_assign_one_port(hfss=hfss, modeler=hfss.modeler, cell=cells_by_role["rx"], slot="2", context="ssw.rx_port")],
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
    "SswAedtPortCellLedgerEntry",
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

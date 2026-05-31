from __future__ import annotations

from pathlib import Path
from typing import Callable, TypedDict, cast

from peetsfea.aedt import Hfss
from peetsfea.aedt.failfast import raise_on_false
from peetsfea.aedt.proxies import assign_lumped_port
from peetsfea.aedt.protocols import (
    AnalysisSetupModuleSession,
    DesignSession,
    HfssSession,
    MeshModuleSession,
    ModelerSession,
    ReportSetupModuleSession,
    SolutionsModuleSession,
)
from peetsfea.minimal_step import MinimalPortCellLedgerEntry, MinimalStepLedger, load_minimal_step_ledger

DEFAULT_LEDGER_PATH = Path(__file__).resolve().parents[4] / "run" / "minimal" / "minimal_step_ledger.json"
DEFAULT_OUTPUT_AEDT_PATH = Path(__file__).resolve().parents[4] / "run" / "minimal" / "minimal.aedt"
DEFAULT_IMPORTED_LEDGER_PATH = Path(__file__).resolve().parents[4] / "run" / "minimal" / "minimal_imported_ledger.json"
DEFAULT_DESIGN_NAME = "minimal_step_two_port"
REPORT_NAME = "Output Variables Table1"
SETUP_NAME = "Setup1"
SWEEP_NAME = "Sweep"
MESH_OPERATION_NAME = "Length1"
MESH_MAX_LENGTH = "1mm"
MESH_MAX_ELEMENTS = "24000"

HfssFactory = Callable[[str], HfssSession]


class MinimalMeshSummary(TypedDict):
    operation_name: str
    objects: list[str]
    max_length: str


class MinimalImportedLedger(TypedDict):
    source_step_ledger_path: str
    scene_step_path: str
    aedt_path: str
    imported_object_names: list[str]
    copper_body_names: list[str]
    port_sheet_names: list[str]
    non_model_body_names: list[str]


class EmPorts(TypedDict):
    tx: list[str]
    rx: list[str]


class EmPolicy(TypedDict):
    radiation_margin_mm: float
    setup_frequency_hz: float
    sweep_start_hz: float
    sweep_stop_hz: float
    validation_gate: str
    max_delta_s: float
    maximum_passes: int
    minimum_passes: int
    minimum_converged_passes: int
    percent_refinement: int
    basis_order: int
    port_accuracy: int


class MinimalSetupResult(TypedDict):
    source_step_ledger_path: str
    scene_step_path: str
    aedt_path: str
    imported_ledger_path: str
    mesh: MinimalMeshSummary
    boundary: dict[str, str]
    ports: EmPorts
    sources: dict[str, str]
    analysis: dict[str, float | str]
    reports: list[str]
    validation_report: dict[str, str | bool]


class MinimalSolveResult(TypedDict):
    setup: MinimalSetupResult
    report_csv_path: str


def create_headless_hfss(design_name: str) -> HfssSession:
    return cast(HfssSession, Hfss(design=design_name, non_graphical=True, new_desktop=True, close_on_exit=False))


def _design(hfss: HfssSession) -> DesignSession:
    assert (_ := hfss.odesign)
    assert isinstance(_, DesignSession)
    return _


def _region_object_name(region: object) -> str:
    assert hasattr(region, "name"), "create_region did not return a region object with a name"
    name = getattr(region, "name")
    assert isinstance(name, str) and name, "create_region returned a region object without a valid name"
    return name


def _default_em_policy() -> EmPolicy:
    return {
        "radiation_margin_mm": 100.0,
        "setup_frequency_hz": 6.78e6,
        "sweep_start_hz": 0.1e6,
        "sweep_stop_hz": 100.0e6,
        "validation_gate": "hard_fail",
        "max_delta_s": 0.007,
        "maximum_passes": 10,
        "minimum_passes": 8,
        "minimum_converged_passes": 10,
        "percent_refinement": 22,
        "basis_order": 1,
        "port_accuracy": 2,
    }


def _build_boundary(*, hfss: HfssSession, modeler: ModelerSession, policy: EmPolicy) -> dict[str, str]:
    margin_mm = float(policy["radiation_margin_mm"])
    pad_value_mm = int(round(margin_mm))
    region = raise_on_false(
        modeler.create_region(
            pad_value=pad_value_mm,
            pad_type="Absolute Offset",
            name=f"Region_Abs_{pad_value_mm}mm",
        ),
        operation="create_region",
        context={"pad_value_mm": pad_value_mm},
    )
    region_name = _region_object_name(region)
    region_faces = raise_on_false(
        modeler.get_object_faces(region_name),
        operation="get_object_faces",
        context={"region": region_name},
    )
    if len(region_faces) != 6:
        raise ValueError(
            "Created region does not expose 6 faces required for radiation assignment "
            f"(region={region_name}, face_count={len(region_faces)})"
        )
    for index, face_id in enumerate(region_faces):
        radiation_name = f"Rad_RegionAbs_{index}"
        raise_on_false(
            hfss.assign_radiation_boundary_to_faces([face_id], name=radiation_name),
            operation="assign_radiation_boundary_to_faces",
            context={"region": region_name, "face_id": face_id, "boundary": radiation_name},
        )
    return {
        "type": "radiation",
        "offset_type": "Absolute Offset",
        "offset_value": str(margin_mm),
        "region_name": region_name,
        "face_count": str(len(region_faces)),
    }


def _validate_minimal_setup(*, ports: EmPorts) -> dict[str, str | bool]:
    tx_ports = ports["tx"]
    rx_ports = ports["rx"]
    ok = len(tx_ports) == 1 and len(rx_ports) == 1
    if not ok:
        raise ValueError(f"minimal EM setup requires exactly one TX port and one RX port (ports={ports})")
    return {"ok": True, "gate": "hard_fail", "message": "ok"}


def _required_str_list(ledger: MinimalStepLedger, *, key: str) -> list[str]:
    raw_value = ledger[key]
    if isinstance(raw_value, (str, bytes)) or not isinstance(raw_value, list):
        raise TypeError(f"minimal ledger {key} must be a list of strings")
    names: list[str] = []
    for index, raw_name in enumerate(raw_value):
        if not isinstance(raw_name, str):
            raise TypeError(f"minimal ledger {key}[{index}] must be str")
        if raw_name == "":
            raise ValueError(f"minimal ledger {key}[{index}] must be non-empty")
        names.append(raw_name)
    return names


def _import_minimal_step(
    *,
    hfss: HfssSession,
    ledger_path: Path,
    output_aedt_path: Path,
    ledger: MinimalStepLedger,
) -> MinimalImportedLedger:
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
        raise ValueError(f"minimal STEP import did not create required bodies (missing={missing_names})")
    imported_names = sorted(name for name in after_names if name in expected_names or name not in before_names)
    non_model_names = _required_str_list(ledger, key="non_model_body_names")
    for non_model_name in non_model_names:
        raise_on_false(
            hfss.modeler.set_object_model_state(non_model_name, False),
            operation="set_object_model_state",
            context={"name": non_model_name, "model": False},
        )
    return {
        "source_step_ledger_path": str(ledger_path),
        "scene_step_path": str(scene_step_path),
        "aedt_path": str(output_aedt_path),
        "imported_object_names": imported_names,
        "copper_body_names": _required_str_list(ledger, key="copper_body_names"),
        "port_sheet_names": _required_str_list(ledger, key="port_sheet_names"),
        "non_model_body_names": non_model_names,
    }


def _assign_mesh(*, hfss: HfssSession, copper_body_names: list[str]) -> MinimalMeshSummary:
    if len(copper_body_names) != 4:
        raise ValueError(f"minimal mesh requires exactly four copper pad bodies (actual={copper_body_names})")
    design = _design(hfss)
    raw_mesh_module = design.GetModule("MeshSetup")
    assert hasattr(raw_mesh_module, "AssignLengthOp"), "MeshSetup module must expose AssignLengthOp"
    mesh_module = cast(MeshModuleSession, raw_mesh_module)
    payload: list[object] = [
        f"NAME:{MESH_OPERATION_NAME}",
        "RefineInside:=",
        False,
        "Enabled:=",
        True,
        "Objects:=",
        copper_body_names,
        "RestrictElem:=",
        True,
        "NumMaxElem:=",
        MESH_MAX_ELEMENTS,
        "RestrictLength:=",
        True,
        "MaxLength:=",
        MESH_MAX_LENGTH,
    ]
    raise_on_false(
        mesh_module.AssignLengthOp(payload),
        operation="AssignLengthOp",
        context={"operation_name": MESH_OPERATION_NAME, "objects": copper_body_names},
    )
    return {"operation_name": MESH_OPERATION_NAME, "objects": list(copper_body_names), "max_length": MESH_MAX_LENGTH}


def _edge_vertices_xyz(modeler: ModelerSession, *, edge_id: int) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
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


def _same_point(first: tuple[float, float, float], second: tuple[float, float, float]) -> bool:
    return abs(first[0] - second[0]) <= 1e-6 and abs(first[1] - second[1]) <= 1e-6 and abs(first[2] - second[2]) <= 1e-6


def _same_edge(
    actual: tuple[tuple[float, float, float], tuple[float, float, float]],
    expected: tuple[tuple[float, float, float], tuple[float, float, float]],
) -> bool:
    return (_same_point(actual[0], expected[0]) and _same_point(actual[1], expected[1])) or (
        _same_point(actual[0], expected[1]) and _same_point(actual[1], expected[0])
    )


def _edge_from_vertex_rows(raw_rows: list[list[float]], *, context: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if len(raw_rows) != 2:
        raise ValueError(f"{context} must contain exactly two vertices")
    vertices: list[tuple[float, float, float]] = []
    for index, raw_vertex in enumerate(raw_rows):
        if len(raw_vertex) != 3:
            raise ValueError(f"{context}[{index}] must contain exactly three coordinates")
        vertices.append((float(raw_vertex[0]), float(raw_vertex[1]), float(raw_vertex[2])))
    return (vertices[0], vertices[1])


def _resolve_sheet_edge_id(
    *,
    modeler: ModelerSession,
    sheet_name: str,
    expected_edge: tuple[tuple[float, float, float], tuple[float, float, float]],
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


def _port_cells_by_role(ledger: MinimalStepLedger) -> dict[str, MinimalPortCellLedgerEntry]:
    raw_cells = ledger["port_cells"]
    if isinstance(raw_cells, (str, bytes)) or not isinstance(raw_cells, list):
        raise TypeError("minimal ledger port_cells must be a list")
    cells_by_role: dict[str, MinimalPortCellLedgerEntry] = {}
    for index, raw_cell in enumerate(raw_cells):
        if not isinstance(raw_cell, dict):
            raise TypeError(f"minimal ledger port_cells[{index}] must be object")
        cell = cast(MinimalPortCellLedgerEntry, raw_cell)
        role = cell["role"]
        if role in cells_by_role:
            raise ValueError(f"minimal ledger contains duplicate port cell role {role!r}")
        cells_by_role[role] = cell
    if set(cells_by_role) != {"tx", "rx"}:
        raise ValueError(f"minimal ledger requires tx and rx port cells (actual={sorted(cells_by_role)})")
    return cells_by_role


def _assign_one_port(
    *,
    hfss: HfssSession,
    modeler: ModelerSession,
    cell: MinimalPortCellLedgerEntry,
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


def _assign_ports(*, hfss: HfssSession, ledger: MinimalStepLedger) -> EmPorts:
    cells_by_role = _port_cells_by_role(ledger)
    return {
        "tx": [_assign_one_port(hfss=hfss, modeler=hfss.modeler, cell=cells_by_role["tx"], slot="1", context="minimal.tx_port")],
        "rx": [_assign_one_port(hfss=hfss, modeler=hfss.modeler, cell=cells_by_role["rx"], slot="2", context="minimal.rx_port")],
    }


def _apply_sources(*, hfss: HfssSession, ports: EmPorts) -> dict[str, str]:
    tx_source_name = ports["tx"][0]
    rx_source_name = ports["rx"][0]
    design = _design(hfss)
    raw_solutions = design.GetModule("Solutions")
    assert hasattr(raw_solutions, "EditSources"), "Solutions module must expose EditSources"
    solutions = cast(SolutionsModuleSession, raw_solutions)
    payload: list[object] = [
        [
            "UseIncidentVoltage:=",
            True,
            "IncludePortPostProcessing:=",
            False,
            "UseElementPatternMode:=",
            False,
            "SpecifySystemPower:=",
            False,
        ],
        ["Name:=", tx_source_name, "Magnitude:=", "1V", "Phase:=", "0deg"],
        ["Name:=", rx_source_name, "Magnitude:=", "0V", "Phase:=", "0deg"],
    ]
    raise_on_false(
        solutions.EditSources(payload),
        operation="EditSources",
        context={"tx_source_name": tx_source_name, "rx_source_name": rx_source_name},
    )
    return {
        "tx_source_name": tx_source_name,
        "tx_magnitude": "1V",
        "tx_phase_deg": "0deg",
        "rx_source_name": rx_source_name,
        "rx_magnitude": "0V",
        "rx_phase_deg": "0deg",
    }


def _format_frequency_mhz(frequency_hz: float) -> str:
    return f"{frequency_hz / 1.0e6:g}MHz"


def _analysis_module(hfss: HfssSession) -> AnalysisSetupModuleSession:
    raw_module = _design(hfss).GetModule("AnalysisSetup")
    assert hasattr(raw_module, "InsertSetup"), "AnalysisSetup module must expose InsertSetup"
    assert hasattr(raw_module, "InsertFrequencySweep"), "AnalysisSetup module must expose InsertFrequencySweep"
    return cast(AnalysisSetupModuleSession, raw_module)


def _build_analysis(*, hfss: HfssSession, policy: EmPolicy) -> dict[str, float | str]:
    module = _analysis_module(hfss)
    raise_on_false(
        module.InsertSetup(
            "HfssDriven",
            [
                f"NAME:{SETUP_NAME}",
                "SolveType:=",
                "Single",
                "Frequency:=",
                _format_frequency_mhz(policy["setup_frequency_hz"]),
                "MaxDeltaS:=",
                policy["max_delta_s"],
                "MaximumPasses:=",
                policy["maximum_passes"],
                "MinimumPasses:=",
                policy["minimum_passes"],
                "MinimumConvergedPasses:=",
                policy["minimum_converged_passes"],
                "PercentRefinement:=",
                policy["percent_refinement"],
                "IsEnabled:=",
                True,
                "BasisOrder:=",
                policy["basis_order"],
                "PortAccuracy:=",
                policy["port_accuracy"],
            ],
        ),
        operation="InsertSetup",
        context={"setup_name": SETUP_NAME},
    )
    raise_on_false(
        module.InsertFrequencySweep(
            SETUP_NAME,
            [
                f"NAME:{SWEEP_NAME}",
                "IsEnabled:=",
                True,
                "RangeType:=",
                "LogScale",
                "RangeStart:=",
                "0.1MHz",
                "RangeEnd:=",
                "100MHz",
                "RangeCount:=",
                401,
                "Type:=",
                "Interpolating",
                "SaveFields:=",
                False,
                "SaveRadFields:=",
                False,
            ],
        ),
        operation="InsertFrequencySweep",
        context={"setup_name": SETUP_NAME, "sweep_name": SWEEP_NAME},
    )
    return {
        "setup_name": SETUP_NAME,
        "setup_frequency_hz": policy["setup_frequency_hz"],
        "sweep_name": SWEEP_NAME,
        "sweep_start_hz": 0.1e6,
        "sweep_stop_hz": 100.0e6,
    }


def _report_setup_module(hfss: HfssSession) -> ReportSetupModuleSession:
    raw_module = _design(hfss).GetModule("ReportSetup")
    assert hasattr(raw_module, "CreateReport"), "ReportSetup module must expose CreateReport"
    assert hasattr(raw_module, "GetAllReportNames"), "ReportSetup module must expose GetAllReportNames"
    return cast(ReportSetupModuleSession, raw_module)


def _create_reports(*, hfss: HfssSession, ports: EmPorts) -> list[str]:
    tx_port = ports["tx"][0]
    rx_port = ports["rx"][0]
    variables = {
        "S11_mag_ratio": f"mag(S({tx_port},{tx_port}))",
        "S21_mag_ratio": f"mag(S({tx_port},{rx_port}))",
        "S21_phase_deg": f"ang_deg_val(S({tx_port},{rx_port}))",
        "S22_mag_ratio": f"mag(S({rx_port},{rx_port}))",
    }
    solution_name = f"{SETUP_NAME} : {SWEEP_NAME}"
    for name, expression in variables.items():
        raise_on_false(
            hfss.create_output_variable(variable=name, expression=expression, solution=solution_name),
            operation="create_output_variable",
            context={"name": name, "expression": expression, "solution": solution_name},
        )
    report_setup = _report_setup_module(hfss)
    traces = list(variables.keys())
    raise_on_false(
        report_setup.CreateReport(
            REPORT_NAME,
            "Terminal Solution Data",
            "Data Table",
            solution_name,
            ["Domain:=", "Sweep"],
            ["Freq:=", ["All"]],
            ["X Component:=", "Freq", "Y Component:=", traces],
            [],
        ),
        operation="CreateReport",
        context={"report_name": REPORT_NAME, "solution_name": solution_name},
    )
    report_names = list(report_setup.GetAllReportNames())
    if REPORT_NAME not in report_names:
        raise ValueError(f"minimal report creation did not register required report (available={report_names})")
    return [REPORT_NAME]


def _validate_design(hfss: HfssSession) -> None:
    design = _design(hfss)
    desktop = hfss.desktop_class
    messages = list(desktop.GetMessages("", "", 0))
    validation_result = design.ValidateDesign()
    raise_on_false(validation_result, operation="ValidateDesign", context={"desktop_messages": messages})


def _setup_policy() -> EmPolicy:
    return _default_em_policy()


def _write_imported_ledger(*, imported_ledger_path: Path, imported_ledger: MinimalImportedLedger) -> None:
    import json

    imported_ledger_path.parent.mkdir(parents=True, exist_ok=True)
    imported_ledger_path.write_text(json.dumps(imported_ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def setup_minimal_step_ledger_into_hfss(
    *,
    hfss: HfssSession,
    step_ledger_path: Path = DEFAULT_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
    run_aedt_design_validation: bool = True,
) -> MinimalSetupResult:
    ledger = load_minimal_step_ledger(step_ledger_path)
    output_aedt_path.parent.mkdir(parents=True, exist_ok=True)
    imported_ledger = _import_minimal_step(
        hfss=hfss,
        ledger_path=step_ledger_path,
        output_aedt_path=output_aedt_path,
        ledger=ledger,
    )
    mesh = _assign_mesh(hfss=hfss, copper_body_names=imported_ledger["copper_body_names"])
    policy = _setup_policy()
    boundary = _build_boundary(hfss=hfss, modeler=hfss.modeler, policy=policy)
    ports = _assign_ports(hfss=hfss, ledger=ledger)
    sources = _apply_sources(hfss=hfss, ports=ports)
    analysis = _build_analysis(hfss=hfss, policy=policy)
    reports = _create_reports(hfss=hfss, ports=ports)
    validation_report = _validate_minimal_setup(ports=ports)
    if run_aedt_design_validation:
        _validate_design(hfss)
    raise_on_false(hfss.save_project(str(output_aedt_path)), operation="save_project", context={"path": str(output_aedt_path)})
    _write_imported_ledger(imported_ledger_path=imported_ledger_path, imported_ledger=imported_ledger)
    return {
        "source_step_ledger_path": str(step_ledger_path),
        "scene_step_path": imported_ledger["scene_step_path"],
        "aedt_path": str(output_aedt_path),
        "imported_ledger_path": str(imported_ledger_path),
        "mesh": mesh,
        "boundary": boundary,
        "ports": ports,
        "sources": sources,
        "analysis": analysis,
        "reports": reports,
        "validation_report": validation_report,
    }


def setup_minimal_step_ledger(
    *,
    step_ledger_path: Path = DEFAULT_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
    design_name: str = DEFAULT_DESIGN_NAME,
    hfss_factory: HfssFactory = create_headless_hfss,
) -> MinimalSetupResult:
    hfss = hfss_factory(design_name)
    try:
        return setup_minimal_step_ledger_into_hfss(
            hfss=hfss,
            step_ledger_path=step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
        )
    finally:
        raise_on_false(
            hfss.desktop_class.release_desktop(close_projects=True, close_on_exit=True),
            operation="release_desktop",
            context={"close_projects": True, "close_on_exit": True},
        )


def solve_minimal_step_ledger(
    *,
    step_ledger_path: Path = DEFAULT_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
    design_name: str = DEFAULT_DESIGN_NAME,
    hfss_factory: HfssFactory = create_headless_hfss,
) -> MinimalSolveResult:
    hfss = hfss_factory(design_name)
    try:
        setup = setup_minimal_step_ledger_into_hfss(
            hfss=hfss,
            step_ledger_path=step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
        )
        raise_on_false(hfss.analyze_setup(SETUP_NAME, blocking=True), operation="analyze_setup", context={"setup_name": SETUP_NAME})
        report_setup = _report_setup_module(hfss)
        report_names = list(report_setup.GetAllReportNames())
        if REPORT_NAME not in report_names:
            raise ValueError(f"minimal solve cannot export missing report (report_name={REPORT_NAME!r}, available={report_names})")
        report_csv_path = output_aedt_path.parent / f"{REPORT_NAME.replace(' ', '_')}.csv"
        raise_on_false(
            report_setup.ExportToFile(REPORT_NAME, str(report_csv_path)),
            operation="ReportSetup.ExportToFile",
            context={"report_name": REPORT_NAME, "path": str(report_csv_path)},
        )
        if not report_csv_path.is_file():
            raise FileNotFoundError(f"minimal report export did not create CSV: {report_csv_path}")
        raise_on_false(hfss.save_project(str(output_aedt_path)), operation="save_project", context={"path": str(output_aedt_path)})
        return {"setup": setup, "report_csv_path": str(report_csv_path)}
    finally:
        raise_on_false(
            hfss.desktop_class.release_desktop(close_projects=True, close_on_exit=True),
            operation="release_desktop",
            context={"close_projects": True, "close_on_exit": True},
        )


__all__ = [
    "DEFAULT_DESIGN_NAME",
    "DEFAULT_IMPORTED_LEDGER_PATH",
    "DEFAULT_LEDGER_PATH",
    "DEFAULT_OUTPUT_AEDT_PATH",
    "HfssFactory",
    "EmPolicy",
    "EmPorts",
    "MinimalImportedLedger",
    "MinimalMeshSummary",
    "MinimalSetupResult",
    "MinimalSolveResult",
    "setup_minimal_step_ledger",
    "setup_minimal_step_ledger_into_hfss",
    "solve_minimal_step_ledger",
]

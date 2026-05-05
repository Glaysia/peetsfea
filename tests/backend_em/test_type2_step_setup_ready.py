from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import cast

import pytest

from peetsfea.aedt.protocols import HfssSession, ModelerSession
from peetsfea.backend.pyaedt.type2_step_em_input import build_type2_em_input
from peetsfea.backend.pyaedt.type2_step_import_core import Type2ImportedLedger
from peetsfea.backend.pyaedt.type2_step_post_import_mesh import assign_post_import_mesh
from peetsfea.backend.pyaedt.type2_step_port_assignment import assign_type2_lumped_ports
from peetsfea.backend.pyaedt.type2_step_setup_ready import (
    Type2SetupReadyResult,
    setup_and_solve_type2_step_ledger,
    setup_type2_step_ledger,
    setup_type2_step_ledger_into_hfss,
)
from peetsfea.backend.pyaedt.type2_step_em_solve import solve_type2_setup_ready_hfss
from peetsfea.types.manifest import EmPorts
from tests.backend_em.test_type2_step_import_pipeline import (
    _PLATE_STACK_STUB_LENGTH_MM,
    _PLATE_STACK_TURN_COUNT,
    _FakeDesign as _ImportFakeDesign,
    _FakeHfss as _ImportFakeHfss,
    _FakeMeshModule,
    _FakeModeler as _ImportFakeModeler,
    _expected_mesh_length_payload,
    _expected_ferrite_group_for_role,
    _modeled_entry,
    _non_model_entry_with_tx_inner_region,
    _plate_stack_modeled_entry,
    _plate_stack_terminal_metadata,
    _non_model_entry,
    _plate_stack_modeled_objects,
    _plate_stack_non_model_entry,
    _non_model_entry_with_tx_outer_region,
    _rx_single_coil_entry,
    _rx_plate_stack_entry,
    _rx_plate_stack_expected_names,
    _tx_plate_stack_expected_names,
    _single_layer_modeled_objects,
    _tx_plate_stack_array_expected_groups,
    _tx_plate_stack_array_expected_names,
    _tx_region_actual_member_names,
    _tx_outer_single_coil_entry,
    _source_paths,
    _write_ledger,
)
from tests.fixtures.legacy.type1_spec import TYPE1_OUTPUT_VARIABLES, type1_outputs_spec


def _plate_stack_copper_family_imported_names(*, imported_object_names: list[str], role_prefix: str) -> list[str]:
    target_name = "tx_plate_copper" if role_prefix == "tx" else "rx_plate_copper"
    return [name for name in imported_object_names if name == target_name]


class _FakeBoundaryModule:
    def __init__(self, parent: "_SetupReadyHfss") -> None:
        self._parent = parent
        self.assign_lumped_port_result: object = True
        self.boundary_names: list[str] = []
        self.assign_lumped_port_calls: list[list[object]] = []
        self.excitation_name_override: str = ""

    def AssignLumpedPort(self, props: list[object]) -> object:
        self.assign_lumped_port_calls.append(list(props))
        if self.assign_lumped_port_result is False:
            return False
        raw_name = props[0]
        assert isinstance(raw_name, str) and raw_name.startswith("NAME:")
        boundary_name = raw_name.removeprefix("NAME:")
        self.boundary_names.append(boundary_name)
        excitation_name = self.excitation_name_override or f"{boundary_name}_T1"
        self._parent._excitation_names.append(excitation_name)
        return True

    def GetBoundaries(self) -> list[str]:
        return list(self.boundary_names)


class _FakeAnalysisSetupModule:
    def __init__(self, parent: "_SetupReadyHfss") -> None:
        self._parent = parent

    def InsertSetup(self, setup_type: str, props: list[object]) -> object:
        self._parent.inserted_setup_types.append(setup_type)
        self._parent.inserted_setup_payloads.append(list(props))
        if "Setup1" not in self._parent.setup_names:
            self._parent.setup_names.append("Setup1")
        return True

    def InsertFrequencySweep(self, setup_name: str, props: list[object]) -> object:
        self._parent.inserted_sweep_setup_names.append(setup_name)
        self._parent.inserted_sweep_payloads.append(list(props))
        return True


class _FakeSolutionsModule:
    def __init__(self, parent: "_SetupReadyHfss") -> None:
        self._parent = parent

    def EditSources(self, payload: list[object]) -> object:
        self._parent.edited_sources_payloads.append(list(payload))
        return True


class _FakeReportSetupModule:
    def __init__(self, parent: "_SetupReadyHfss") -> None:
        self._parent = parent

    def CreateReport(
        self,
        plot_name: str,
        report_category: str,
        plot_type: str,
        setup_sweep_name: str,
        context: list[object],
        variations: list[object],
        components: list[object],
        options: list[object],
    ) -> object:
        _ = options
        self._parent.created_reports.append(
            {
                "plot_name": plot_name,
                "report_category": report_category,
                "plot_type": plot_type,
                "setup_sweep_name": setup_sweep_name,
                "context": list(context),
                "variations": list(variations),
                "components": list(components),
            }
        )
        return True

    def GetAllReportNames(self) -> list[str]:
        return [cast(str, report["plot_name"]) for report in self._parent.created_reports]

    def ExportToFile(self, report_name: str, export_path: str) -> object:
        self._parent.exported_report_calls.append((report_name, export_path))
        if self._parent.export_report_result is False:
            return False
        Path(export_path).write_text("Freq,Lrx_uH\n1,2\n", encoding="utf-8")
        return True


class _SetupReadyDesign(_ImportFakeDesign):
    def __init__(self, *, mesh_module: _FakeMeshModule, parent: "_SetupReadyHfss") -> None:
        super().__init__(mesh_module=mesh_module)
        self._parent = parent
        self.validate_design_calls = 0

    def GetModule(self, name: str) -> object:
        self.get_module_calls.append(name)
        if name == "MeshSetup":
            return self.mesh_module
        if name == "AnalysisSetup":
            return _FakeAnalysisSetupModule(self._parent)
        if name == "ReportSetup":
            return _FakeReportSetupModule(self._parent)
        if name == "Solutions":
            return _FakeSolutionsModule(self._parent)
        raise AssertionError(f"unexpected module lookup in fake design: {name}")

    def ValidateDesign(self) -> object:
        self.validate_design_calls += 1
        return self._parent.validate_design_result


class _SetupReadyModeler(_ImportFakeModeler):
    def __init__(self, *, imported_name_batches: list[tuple[str, ...]], import_result: object = True) -> None:
        super().__init__(imported_name_batches=imported_name_batches, import_result=import_result)
        self._polyline_points_by_name: dict[str, list[tuple[float, float, float]]] = {}
        self._object_edge_ids: dict[str, list[int]] = {}
        self._edge_vertices: dict[int, tuple[int, int]] = {}
        self._vertex_positions: dict[int, tuple[float, float, float]] = {}
        self._next_edge_id = 1
        self._next_vertex_id = 1
        self.duplicate_matching_edges = False

    def create_polyline(self, **kwargs: object) -> object:
        points = kwargs["points"]
        assert isinstance(points, list)
        self._polyline_points_by_name[cast(str, kwargs["name"])] = [
            (float(point[0]), float(point[1]), float(point[2]))
            for point in cast(list[list[float]], points)
        ]
        return super().create_polyline(**kwargs)

    def cover_lines(self, assignment: str) -> object:
        result = super().cover_lines(assignment)
        if result is False:
            return result
        points = self._polyline_points_by_name[assignment]
        vertex_ids: list[int] = []
        for point in points:
            vertex_id = self._next_vertex_id
            self._next_vertex_id += 1
            self._vertex_positions[vertex_id] = point
            vertex_ids.append(vertex_id)
        edge_ids: list[int] = []
        edge_vertices = list(zip(vertex_ids, vertex_ids[1:] + vertex_ids[:1], strict=False))
        if self.duplicate_matching_edges:
            edge_vertices.append((vertex_ids[3], vertex_ids[0]))
        for first_vertex_id, second_vertex_id in edge_vertices:
            edge_id = self._next_edge_id
            self._next_edge_id += 1
            self._edge_vertices[edge_id] = (first_vertex_id, second_vertex_id)
            edge_ids.append(edge_id)
        self._object_edge_ids[assignment] = edge_ids
        return result

    def seed_object_edge(
        self,
        *,
        object_name: str,
        first_vertex: tuple[float, float, float],
        second_vertex: tuple[float, float, float],
    ) -> None:
        first_vertex_id = self._next_vertex_id
        self._next_vertex_id += 1
        second_vertex_id = self._next_vertex_id
        self._next_vertex_id += 1
        self._vertex_positions[first_vertex_id] = first_vertex
        self._vertex_positions[second_vertex_id] = second_vertex
        edge_id = self._next_edge_id
        self._next_edge_id += 1
        self._edge_vertices[edge_id] = (first_vertex_id, second_vertex_id)
        if object_name not in self._object_edge_ids:
            self._object_edge_ids[object_name] = []
        self._object_edge_ids[object_name].append(edge_id)

    def get_object_edges(self, assignment: str) -> list[int]:
        return list(self._object_edge_ids.get(assignment, []))

    def get_edge_vertices(self, assignment: int) -> list[int]:
        assert assignment in self._edge_vertices, f"unknown edge id: {assignment}"
        first_vertex_id, second_vertex_id = self._edge_vertices[assignment]
        return [first_vertex_id, second_vertex_id]

    def get_vertex_position(self, assignment: int) -> list[float]:
        assert assignment in self._vertex_positions, f"unknown vertex id: {assignment}"
        x, y, z = self._vertex_positions[assignment]
        return [x, y, z]


class _SetupReadyHfss(_ImportFakeHfss):
    def __init__(self, *, modeler: _SetupReadyModeler, save_project_result: object = True) -> None:
        super().__init__(modeler=modeler, save_project_result=save_project_result)
        self._excitation_names: list[str] = []
        self.setup_names: list[str] = []
        self.inserted_setup_types: list[str] = []
        self.inserted_setup_payloads: list[list[object]] = []
        self.inserted_sweep_setup_names: list[str] = []
        self.inserted_sweep_payloads: list[list[object]] = []
        self.edited_sources_payloads: list[list[object]] = []
        self.created_output_variables: list[tuple[str, str, str]] = []
        self.created_reports: list[dict[str, object]] = []
        self.exported_report_calls: list[tuple[str, str]] = []
        self.export_report_result: object = True
        self.analyze_setup_calls: list[tuple[str, bool]] = []
        self.analyze_setup_result: object = True
        self.validation_settings_calls: list[tuple[str, bool, bool]] = []
        self.validate_design_result: object = True
        self.oboundary = _FakeBoundaryModule(self)
        self.design = _SetupReadyDesign(mesh_module=self.mesh_module, parent=self)

    @property
    def excitation_names(self) -> list[str]:
        return list(self._excitation_names)

    def delete_setup(self, name: str) -> object:
        self.setup_names = [setup_name for setup_name in self.setup_names if setup_name != name]
        return True

    def create_output_variable(self, variable: str, expression: str, solution: str) -> object:
        self.created_output_variables.append((variable, expression, solution))
        return True

    def change_validation_settings(
        self,
        entity_check_level: str = "Strict",
        ignore_unclassified: bool = False,
        skip_intersections: bool = False,
    ) -> object:
        self.validation_settings_calls.append((entity_check_level, ignore_unclassified, skip_intersections))
        return True

    def analyze_setup(self, name: str, blocking: bool = True) -> object:
        self.analyze_setup_calls.append((name, blocking))
        return self.analyze_setup_result

    def get_traces_for_plot(
        self,
        get_self_terms: bool,
        get_mutual_terms: bool,
        first_element_filter: str,
        second_element_filter: str,
        category: str,
        differential_pairs: tuple[object, ...],
    ) -> list[str]:
        _ = (
            get_self_terms,
            get_mutual_terms,
            first_element_filter,
            second_element_filter,
            category,
            differential_pairs,
        )
        if len(self._excitation_names) == 1:
            rx_name = self._excitation_names[0]
            return [f"S({rx_name},{rx_name})"]
        tx_name = self._excitation_names[0]
        rx_name = self._excitation_names[1]
        return [
            f"S({tx_name},{tx_name})",
            f"S({tx_name},{rx_name})",
            f"S({rx_name},{tx_name})",
            f"S({rx_name},{rx_name})",
        ]


def _imported_ledger_payload(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _expected_output_variables() -> list[tuple[str, str, str]]:
    outputs = type1_outputs_spec()
    solution_name = outputs["solution_name"]
    return [
        (
            name,
            expression.replace("TX_TML", "1_T1").replace("RX_TML", "2_T1"),
            solution_name,
        )
        for name, expression in TYPE1_OUTPUT_VARIABLES
    ]


def _expected_rx_only_output_variables() -> list[tuple[str, str, str]]:
    outputs = type1_outputs_spec()
    solution_name = outputs["solution_name"]
    source_by_name = dict(TYPE1_OUTPUT_VARIABLES)
    expected_names = [
        "Lrx_uH",
        "Qrx_ratio",
        "Rrx_ac_ohm",
        "Xrx_ohm",
        "Grx_S",
        "Brx_S",
        "Srx_self_mag_ratio",
        "eta_rx_accept_ratio",
    ]
    expression_by_name = {
        "Lrx_uH": source_by_name["Lrx_uH"],
        "Qrx_ratio": source_by_name["Qrx_ratio"],
        "Rrx_ac_ohm": source_by_name["Rrx_ac_ohm"],
        "Xrx_ohm": source_by_name["Xrx_ohm"],
        "Grx_S": source_by_name["Grx_S"],
        "Brx_S": source_by_name["Brx_S"],
        "Srx_self_mag_ratio": source_by_name["S22_mag_ratio"],
        "eta_rx_accept_ratio": source_by_name["eta_rx_accept_ratio"],
    }
    return [
        (
            name,
            expression_by_name[name].replace("RX_TML", "1_T1"),
            solution_name,
        )
        for name in expected_names
    ]


def _write_txrx_step_ledger(
    path: Path,
    *,
    scene_step_path: Path,
    non_model_objects: list[dict[str, object]],
    modeled_objects: list[dict[str, object]],
    radiation_margin_mm: float = 3500.0,
) -> Path:
    legacy_outputs = type1_outputs_spec()
    outputs = {
        "mode": "TxRx",
        "report_name": legacy_outputs["report_name"],
        "solution_name": legacy_outputs["solution_name"],
        "primary_sweep": legacy_outputs["primary_sweep"],
        "report_category": legacy_outputs["report_category"],
        "plot_type": legacy_outputs["plot_type"],
        "variables": [{"name": name, "expression": expression} for name, expression in TYPE1_OUTPUT_VARIABLES],
    }
    payload = {
        "source_toml_path": str(path.parent / "type2_fixed.toml"),
        "output_dir": str(path.parent),
        "scene_step_path": str(scene_step_path),
        "seed": 7,
        "em_policy": {"radiation_margin_mm": radiation_margin_mm},
        "outputs": outputs,
        "non_model_objects": non_model_objects,
        "modeled_objects": modeled_objects,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _tx_inner_rx_imported_name_batch() -> tuple[str, ...]:
    tx_region_actual_member_names = _tx_region_actual_member_names()
    return (
        "environment",
        "tx_region",
        *tx_region_actual_member_names,
        "rx_region_max",
        "tx_inner_region",
        "tx_inner_actual_region",
        "tx_inner_pcb_l0",
        "tx_inner_copper_l0",
        "rx_pcb_l0",
        "rx_copper_l0",
    )


def _tx_inner_outer_rx_imported_name_batch(*, include_tx_outer_void_stack: bool = False) -> tuple[str, ...]:
    tx_region_actual_member_names = _tx_region_actual_member_names()
    tx_outer_void_stack_names: tuple[str, ...] = ()
    if include_tx_outer_void_stack:
        tx_outer_void_stack_names = (
            "tx_outer_void_ferrite_u0",
            "tx_outer_void_pet_psa_u0",
            "tx_outer_underlay_pet_psa_u0",
            "tx_outer_underlay_ferrite_u0",
        )
    return (
        "environment",
        "tx_region",
        *tx_region_actual_member_names,
        "rx_region_max",
        "tx_inner_region",
        "tx_inner_actual_region",
        "tx_outer_region",
        "tx_outer_pcb_l0",
        "tx_outer_copper_l0",
        *tx_outer_void_stack_names,
        "tx_inner_pcb_l0",
        "tx_inner_copper_l0",
        "rx_pcb_l0",
        "rx_copper_l0",
    )


def _role_aware_mesh_entries(
    *,
    tx_object_name: str = "tx_copper_l0",
    tx_object_id: str = "tx_rect_void_coil",
    tx_role: str = "tx_single_coil",
    tx_pcb_name: str = "tx_pcb_l0",
    tx_sheet_name: str = "tx_port_sheet",
) -> list[dict[str, object]]:
    return [
        {
            "object_id": tx_object_id,
            "role": tx_role,
            "imported_object_names": [
                tx_pcb_name,
                tx_object_name,
                "tx_wall_ferrite_u0",
                "tx_wall_pet_psa_u0",
                "tx_wall_air_u0",
                tx_sheet_name,
            ],
        },
        {
            "object_id": "rx_rect_void_coil",
            "role": "rx_single_coil",
            "imported_object_names": [
                "rx_pcb_l0",
                "rx_copper_l0",
                "under_rx_ferrite_u0",
                "under_rx_pet_psa_u0",
                "under_rx_air_u0",
                "rx_port_sheet",
            ],
        },
    ]


def _coil_modeled_objects_with_imported_names(tmp_path: Path) -> list[dict[str, object]]:
    modeled_objects = _single_layer_modeled_objects(tmp_path)
    modeled_objects[0]["imported_object_names"] = ["tx_pcb_l0", "tx_copper_l0", "tx_port_sheet"]
    modeled_objects[1]["imported_object_names"] = ["rx_pcb_l0", "rx_copper_l0", "rx_port_sheet"]
    return modeled_objects


def _tx_inner_single_coil_modeled_object_with_imported_names(
    tmp_path: Path,
    *,
    include_tx_inner_underlay: bool = False,
) -> dict[str, object]:
    expected_names = ["tx_inner_pcb_l0", "tx_inner_copper_l0"]
    if include_tx_inner_underlay:
        expected_names.extend(["tx_underlay_pet_psa_u0", "tx_underlay_ferrite_u0"])
    modeled_object = _modeled_entry(
        object_id="tx_inner_rect_void_coil",
        role="tx_inner_single_coil",
        placement_owner_id="tx_inner_region",
        origin_xyz=(3.0, -15.0, 67.2),
        size_xyz=(50.0, 30.0, 2.8),
        expected_names=expected_names,
        expected_groups=_expected_ferrite_group_for_role(role="tx_inner_single_coil", expected_names=expected_names),
        source_metadata_path=str(tmp_path / "tx_inner.metadata.json"),
    )
    modeled_object["imported_object_names"] = [
        "tx_inner_pcb_l0",
        "tx_inner_copper_l0",
        "tx_inner_port_sheet",
    ]
    if include_tx_inner_underlay:
        modeled_object["imported_object_names"][2:2] = [
            "tx_underlay_pet_psa_u0",
            "tx_underlay_ferrite_u0",
        ]
    return modeled_object


def _tx_bridge_member_entry(*, object_id: str, role: str) -> dict[str, object]:
    return {
        "object_id": object_id,
        "role": role,
        "material": "vacuum",
        "model_state": False,
        "non_model": True,
        "plane": "YZ",
        "canonical_coordinates": {
            "frame_origin_xyz": [0.0, 0.0, 0.0],
            "outer_bounds_min_xyz": [0.0, 0.0, 0.0],
            "outer_bounds_max_xyz": [1.0, 1.0, 1.0],
            "outer_bounds_size_xyz": [1.0, 1.0, 1.0],
        },
    }


def _non_model_entry_with_tx_bridge_members_for_setup() -> dict[str, object]:
    non_model_object = _non_model_entry_with_tx_inner_region()
    member_object_ids = list(cast(tuple[str, ...], non_model_object["member_object_ids"]))
    member_objects = list(cast(list[dict[str, object]], non_model_object["member_objects"]))
    for member_id in (
        "tx_pos_bridge_pcb",
        "tx_pos_bridge_copper",
        "tx_neg_bridge_pcb",
        "tx_neg_bridge_copper",
    ):
        if member_id not in member_object_ids:
            member_object_ids.append(member_id)
        member_objects.append(_tx_bridge_member_entry(object_id=member_id, role=member_id))
    non_model_object["member_object_ids"] = tuple(member_object_ids)
    non_model_object["member_objects"] = member_objects
    return non_model_object


def _non_model_entry_with_tx_inner_and_outer_regions() -> dict[str, object]:
    non_model_object = _non_model_entry_with_tx_inner_region()
    tx_outer_object = _non_model_entry_with_tx_outer_region()
    member_object_ids = list(cast(tuple[str, ...], non_model_object["member_object_ids"]))
    member_objects = list(cast(list[dict[str, object]], non_model_object["member_objects"]))
    tx_outer_member_objects = cast(list[dict[str, object]], tx_outer_object["member_objects"])
    for member_object in tx_outer_member_objects:
        member_id = cast(str, member_object["object_id"])
        if member_id == "tx_outer_region":
            member_object_ids.append(member_id)
            member_objects.append(member_object)
    non_model_object["member_object_ids"] = tuple(member_object_ids)
    non_model_object["member_objects"] = member_objects
    return non_model_object


def _non_model_entry_with_tx_inner_void_stack_members_for_setup() -> dict[str, object]:
    non_model_object = _non_model_entry_with_tx_inner_region()
    member_object_ids = list(cast(tuple[str, ...], non_model_object["member_object_ids"]))
    member_objects = list(cast(list[dict[str, object]], non_model_object["member_objects"]))
    for member_id in ("tx_void_ferrite_u0", "tx_void_pet_psa_u0"):
        member_object_ids.append(member_id)
        member_objects.append(_tx_bridge_member_entry(object_id=member_id, role=member_id))
    non_model_object["member_object_ids"] = tuple(member_object_ids)
    non_model_object["member_objects"] = member_objects
    return non_model_object


def _rx_single_coil_modeled_object_with_imported_names(tmp_path: Path) -> dict[str, object]:
    modeled_object = _rx_single_coil_entry(tmp_path)
    modeled_object["imported_object_names"] = ["rx_pcb_l0", "rx_copper_l0", "rx_port_sheet"]
    return modeled_object


def _tx_inner_rx_modeled_objects_with_imported_names(tmp_path: Path) -> list[dict[str, object]]:
    return [
        _tx_inner_single_coil_modeled_object_with_imported_names(tmp_path),
        _rx_single_coil_modeled_object_with_imported_names(tmp_path),
    ]


def _tx_inner_rx_modeled_objects_with_tx_inner_underlay_imported_names(tmp_path: Path) -> list[dict[str, object]]:
    return [
        _tx_inner_single_coil_modeled_object_with_imported_names(
            tmp_path,
            include_tx_inner_underlay=True,
        ),
        _rx_single_coil_modeled_object_with_imported_names(tmp_path),
    ]


def _tx_inner_rx_imported_name_batch_with_tx_inner_underlay() -> tuple[str, ...]:
    names = list(_tx_inner_rx_imported_name_batch())
    names[6:6] = [
        "tx_underlay_pet_psa_u0",
        "tx_underlay_ferrite_u0",
        "tx_void_ferrite_u0",
        "tx_void_pet_psa_u0",
    ]
    return tuple(names)


def _tx_inner_multilayer_stack_modeled_object(tmp_path: Path) -> dict[str, object]:
    modeled_object = _modeled_entry(
        object_id="tx_inner_rect_void_coil",
        role="tx_inner_single_coil",
        source_metadata_path=str(tmp_path / "tx_inner.metadata.json"),
        expected_names=["tx_inner_pcb_l0", "tx_inner_pcb_l1", "tx_inner_copper_stack"],
        pcb_layer_positions_mm=[87.2, 91.3],
        copper_layer_positions_mm=[88.8, 92.9],
    )
    modeled_object["imported_object_names"] = [
        "tx_inner_pcb_l0",
        "tx_inner_pcb_l1",
        "tx_inner_copper_stack",
        "tx_inner_port_sheet",
    ]
    return modeled_object


def _plate_stack_modeled_objects_with_imported_names(tmp_path: Path) -> list[dict[str, object]]:
    modeled_objects = _plate_stack_modeled_objects(tmp_path)
    tx_entry = cast(dict[str, object], modeled_objects[0])
    rx_entry = cast(dict[str, object], modeled_objects[1])
    tx_expected_names = cast(list[object], tx_entry["expected_exported_body_names"])
    rx_expected_names = cast(list[object], rx_entry["expected_exported_body_names"])
    tx_entry["imported_object_names"] = [*tx_expected_names, "tx_plate_port_sheet"]
    rx_entry["imported_object_names"] = [*rx_expected_names, "rx_plate_port_sheet"]
    return modeled_objects


def _tx_array_port_sheet_metadata(*, branch_count: int) -> dict[str, object]:
    terminal = _plate_stack_terminal_metadata(
        owner_origin_y=-140.0,
        owner_size_y=280.0,
        owner_origin_z=0.0,
        owner_size_z=90.0,
        copper_thickness_mm=0.035,
        prefix="tx",
    )
    raw_vertices = cast(list[list[float]], terminal["port_sheet_vertices_xyz"])
    raw_vertices[1][0] = 80.0 + float(branch_count)
    raw_vertices[2][0] = 80.0 + float(branch_count)
    return terminal


def _tx_array_modeled_entry(tmp_path: Path, *, branch_count: int) -> dict[str, object]:
    return _plate_stack_modeled_entry(
        object_id="tx_plate_stack",
        role="tx_plate_stack",
        plane="YZ",
        placement_owner_id="tx_region",
        origin_xyz=(0.0, -145.0, 0.0),
        size_xyz=(85.0, 285.0, 90.0),
        source_metadata_path=str(tmp_path / "tx_plate_stack.metadata.json"),
        expected_names=_tx_plate_stack_array_expected_names(branch_count=branch_count),
        expected_groups=_tx_plate_stack_array_expected_groups(branch_count=branch_count),
        pcb_layer_positions_mm=[0.035, 5.3],
        copper_layer_positions_mm=[0.0, 6.865],
        terminal_metadata=_tx_array_port_sheet_metadata(branch_count=branch_count),
    )


def _tx_array_imported_name_batch(*, branch_count: int) -> tuple[str, ...]:
    tx_region_actual_member_names = _tx_region_actual_member_names()
    return (
        "environment",
        "tx_region",
        *tx_region_actual_member_names,
        "rx_region_max",
        *_tx_plate_stack_array_expected_names(branch_count=branch_count),
        *_rx_plate_stack_expected_names(),
    )


def _mixed_tx_plate_stack_rx_single_imported_name_batch() -> tuple[str, ...]:
    tx_region_actual_member_names = _tx_region_actual_member_names()
    return (
        "environment",
        "tx_region",
        *tx_region_actual_member_names,
        "rx_region_max",
        *_tx_plate_stack_expected_names(),
        "rx_pcb_l0",
        "rx_copper_l0",
    )


def _rx_only_imported_name_batch() -> tuple[str, ...]:
    tx_region_actual_member_names = _tx_region_actual_member_names()
    return (
        "environment",
        "tx_region",
        *tx_region_actual_member_names,
        "rx_region_max",
        "rx_pcb_l0",
        "rx_copper_l0",
    )


def _seed_port_sheet_edges_from_terminal_metadata(
    modeler: _SetupReadyModeler,
    *,
    entry: dict[str, object],
    sheet_name: str,
) -> None:
    terminal_metadata = cast(dict[str, object], entry["terminal_metadata"])
    raw_vertices = cast(list[list[float]], terminal_metadata["port_sheet_vertices_xyz"])
    modeler.create_polyline(name=sheet_name, points=raw_vertices, cover_surface=False, close_surface=True, material="vacuum")
    cover_result = modeler.cover_lines(sheet_name)
    assert cover_result is not False


def _seed_tx_rect_void_columns_conductor_port_edges(modeler: _SetupReadyModeler) -> None:
    modeler.seed_object_edge(
        object_name="tx_rect_void_columns_copper",
        first_vertex=(12.0, 5.0, 70.0),
        second_vertex=(12.0, 5.4, 70.0),
    )
    modeler.seed_object_edge(
        object_name="tx_rect_void_columns_copper",
        first_vertex=(12.0, 5.4, 70.0),
        second_vertex=(12.0, 6.0, 70.0),
    )
    modeler.seed_object_edge(
        object_name="tx_rect_void_columns_copper",
        first_vertex=(21.0, 5.0, 69.0),
        second_vertex=(21.0, 5.4, 69.0),
    )
    modeler.seed_object_edge(
        object_name="tx_rect_void_columns_copper",
        first_vertex=(21.0, 5.4, 69.0),
        second_vertex=(21.0, 6.0, 69.0),
    )


def _rewrite_plate_stack_terminal_metadata_to_equal_stripe_pitch(
    entry: dict[str, object],
    *,
    turn_count: int = _PLATE_STACK_TURN_COUNT,
    metal_fill_factor: float = 0.4,
) -> None:
    role = cast(str, entry["role"])
    canonical = cast(dict[str, object], entry["canonical_coordinates"])
    outer_min_xyz = cast(list[float], canonical["outer_bounds_min_xyz"])
    outer_size_xyz = cast(list[float], canonical["outer_bounds_size_xyz"])
    copper_layer_positions_mm = cast(list[float], canonical["copper_layer_z_positions_mm"])
    origin_x, origin_y, origin_z = (float(component) for component in outer_min_xyz)
    _size_x, size_y, size_z = (float(component) for component in outer_size_xyz)
    wall_copper_x = float(copper_layer_positions_mm[0])
    coil_copper_x = float(copper_layer_positions_mm[1])
    owner_min_y = origin_y + _PLATE_STACK_STUB_LENGTH_MM
    sheet_y = owner_min_y - _PLATE_STACK_STUB_LENGTH_MM
    pitch_z = size_z / float(turn_count + 0.5)
    trace_height_z = pitch_z * metal_fill_factor
    stripe_centering_offset_z = (pitch_z - trace_height_z) / 2.0
    wall_first_origin_z = origin_z + stripe_centering_offset_z
    coil_last_origin_z = origin_z + (pitch_z / 2.0) + (pitch_z * float(turn_count - 1)) + stripe_centering_offset_z
    prefix = "tx" if role == "tx_plate_stack" else "rx"
    terminal_metadata = cast(dict[str, object], entry["terminal_metadata"])
    terminal_metadata["kind"] = "stub_port"
    terminal_metadata["input_stub_body_name"] = f"{prefix}_stub_in"
    terminal_metadata["output_stub_body_name"] = f"{prefix}_stub_out"
    terminal_metadata["start_point_plane_mm"] = [sheet_y, wall_first_origin_z + (trace_height_z / 2.0)]
    terminal_metadata["end_point_plane_mm"] = [sheet_y, coil_last_origin_z + (trace_height_z / 2.0)]
    terminal_metadata["port_sheet_vertices_xyz"] = [
        [wall_copper_x, sheet_y, wall_first_origin_z],
        [coil_copper_x, sheet_y, coil_last_origin_z],
        [coil_copper_x, sheet_y, coil_last_origin_z + trace_height_z],
        [wall_copper_x, sheet_y, wall_first_origin_z + trace_height_z],
    ]
    assert sheet_y == pytest.approx(owner_min_y - _PLATE_STACK_STUB_LENGTH_MM)


def _minimal_em_input_ledger(*, modeled_objects: list[dict[str, object]]) -> dict[str, object]:
    non_model_object = _non_model_entry()
    non_model_object["imported_object_names"] = ["environment", "tx_region", *_tx_region_actual_member_names(), "rx_region_max"]
    return {
        "non_model_objects": [non_model_object],
        "modeled_objects": modeled_objects,
    }


def _tx_rect_void_columns_terminal_metadata() -> dict[str, object]:
    return {
        "kind": "parallel_collector_tabs",
        "connection_mode": 0,
        "source_label_metadata": {
            "start_pours": ["txrvc_pour_s_bus"],
            "end_pours": ["txrvc_pour_e_bus"],
            "end_layer_drops": ["txrvc_drop_e_x0_y0"],
            "series_links": [],
            "start_external_tabs": ["txrvc_tab_start"],
            "end_external_tabs": ["txrvc_tab_end"],
        },
        "tab_face_vertices_xyz": [
            {
                "terminal": "start",
                "vertices_xyz": [
                    [12.0, 5.0, 70.0],
                    [13.0, 5.0, 70.0],
                    [13.0, 6.0, 70.0],
                    [12.0, 6.0, 70.0],
                ],
            },
            {
                "terminal": "end",
                "vertices_xyz": [
                    [20.0, 5.0, 69.0],
                    [21.0, 5.0, 69.0],
                    [21.0, 6.0, 69.0],
                    [20.0, 6.0, 69.0],
                ],
            },
        ],
        "branch_balance_audit": {
            "branch_count": 1,
            "start_total_feed_length_mm": 0.0,
            "end_total_feed_length_mm": 0.0,
            "balance_delta_mm": 0.0,
            "max_branch_total_delta_mm": 0.0,
            "branch_spread_limit_mm": 5.0,
            "tolerance_mm": 1e-6,
        },
        "overlap_audit": {
            "checked_pair_count": 1,
            "positive_volume_pair_count": 0,
            "max_intersection_volume_mm3": 0.0,
            "tolerance_mm3": 1e-9,
        },
        "layer_count": 1,
        "x_column_count": 1,
        "y_tile_count": 1,
    }


def _tx_rect_void_columns_non_model_entry() -> dict[str, object]:
    non_model_object = copy.deepcopy(_non_model_entry())
    stack_space_member = {
        "object_id": "tx_region_actual_stack_space",
        "role": "tx_region_actual_stack_space",
        "material": "vacuum",
        "model_state": False,
        "non_model": True,
        "plane": "XY",
        "canonical_coordinates": {
            "frame_origin_xyz": [0.0, -20.0, 60.0],
            "outer_bounds_min_xyz": [0.0, -20.0, 60.0],
            "outer_bounds_max_xyz": [40.0, 20.0, 95.0],
            "outer_bounds_size_xyz": [40.0, 40.0, 35.0],
        },
    }
    member_object_ids = list(cast(tuple[str, ...], non_model_object["member_object_ids"]))
    member_object_ids.append("tx_region_actual_stack_space")
    non_model_object["member_object_ids"] = tuple(member_object_ids)
    member_objects = list(cast(list[dict[str, object]], non_model_object["member_objects"]))
    member_objects.append(stack_space_member)
    non_model_object["member_objects"] = member_objects
    return non_model_object


def _tx_rect_void_columns_entry(tmp_path: Path) -> dict[str, object]:
    modeled_object = _modeled_entry(
        object_id="tx_rect_void_columns",
        role="tx_rect_void_columns",
        plane="XY",
        placement_owner_id="tx_region_actual_stack_space",
        origin_xyz=(10.0, -10.0, 65.0),
        size_xyz=(20.0, 20.0, 25.0),
        source_metadata_path=str(tmp_path / "tx_rect_void_columns.metadata.json"),
        expected_names=["txrvc_x0_y0_pcb_l0", "tx_rect_void_columns_copper"],
        expected_groups=[],
    )
    modeled_object["terminal_metadata"] = _tx_rect_void_columns_terminal_metadata()
    return modeled_object


def _tx_rect_void_columns_imported_name_batch() -> tuple[str, ...]:
    return (
        "environment",
        "tx_region",
        *_tx_region_actual_member_names(),
        "rx_region_max",
        "tx_region_actual_stack_space",
        "txrvc_x0_y0_pcb_l0",
        "tx_rect_void_columns_copper",
        "rx_pcb_l0",
        "rx_copper_l0",
    )


def _tx_rect_void_columns_modeled_objects_with_imported_names(tmp_path: Path) -> list[dict[str, object]]:
    tx_entry = _tx_rect_void_columns_entry(tmp_path)
    tx_entry["imported_object_names"] = [
        "txrvc_x0_y0_pcb_l0",
        "tx_rect_void_columns_copper",
        "tx_rect_void_columns_port_sheet",
    ]
    rx_entry = _rx_single_coil_entry(tmp_path)
    rx_entry["imported_object_names"] = ["rx_pcb_l0", "rx_copper_l0", "rx_port_sheet"]
    return [tx_entry, rx_entry]


def test_setup_type2_step_ledger_builds_mesh_boundary_ports_analysis_and_validation(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry_with_tx_inner_region()],
        modeled_objects=_tx_inner_rx_modeled_objects_with_imported_names(tmp_path),
        radiation_margin_mm=4123.0,
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_tx_inner_rx_imported_name_batch()]))

    result = cast(
        Type2SetupReadyResult,
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            design_name="fake_type2_setup_ready",
            hfss_factory=lambda _: cast(HfssSession, session),
        ),
    )

    assert session.design.import_dataset_calls == []
    assert session.mesh_module.assign_length_op_calls == [_expected_mesh_length_payload(tx_object_name="tx_inner_copper_l0")]
    assert session.modeler.created_region_name == "Region_Abs_4123mm"
    assert session.radiation_boundary_calls == [
        ([10], "Rad_RegionAbs_0"),
        ([11], "Rad_RegionAbs_1"),
        ([12], "Rad_RegionAbs_2"),
        ([13], "Rad_RegionAbs_3"),
        ([14], "Rad_RegionAbs_4"),
        ([15], "Rad_RegionAbs_5"),
    ]
    assert len(session.oboundary.assign_lumped_port_calls) == 2
    assert session._excitation_names == ["1_T1", "2_T1"]
    assert session.edited_sources_payloads
    assert session.inserted_setup_types == ["HfssDriven"]
    outputs = type1_outputs_spec()
    expected_trace_names = [name for name, _ in TYPE1_OUTPUT_VARIABLES]
    assert session.created_output_variables == _expected_output_variables()
    assert session.created_reports[0]["plot_name"] == "Output Variables Table1"
    assert session.created_reports[0]["report_category"] == outputs["report_category"]
    assert session.created_reports[0]["plot_type"] == outputs["plot_type"]
    assert session.created_reports[0]["setup_sweep_name"] == outputs["solution_name"]
    assert session.created_reports[0]["variations"] == [f"{outputs['primary_sweep']}:=", ["All"]]
    assert session.created_reports[0]["components"] == [
        "X Component:=",
        outputs["primary_sweep"],
        "Y Component:=",
        expected_trace_names,
    ]
    assert session.save_project_calls == [str(output_aedt_path)]
    assert session.desktop_class.release_calls == [(True, True)]
    assert result["ports"] == {"tx": ["1_T1"], "rx": ["2_T1"]}
    assert result["sources"]["tx_source_name"] == "1_T1"
    assert result["sources"]["rx_source_name"] == "2_T1"
    assert result["analysis"]["setup_name"] == "Setup1"
    assert result["validation_report"] == {"ok": True, "gate": "hard_fail", "message": "ok"}
    assert result["mesh"]["objects"] == ["tx_inner_copper_l0", "rx_copper_l0"]

    imported_payload = _imported_ledger_payload(imported_ledger_path)
    assert [(entry["role"]) for entry in cast(list[dict[str, object]], imported_payload["modeled_objects"])] == [
        "tx_inner_single_coil",
        "rx_single_coil",
    ]
    assert "mesh" not in imported_payload
    assert "boundary" not in imported_payload
    assert imported_payload["aedt_path"] == str(output_aedt_path)


def test_setup_type2_step_ledger_keeps_tx_outer_single_coil_geometry_only_in_txrx_mode(tmp_path: Path) -> None:
    passive_names = (
        "tx_outer_void_ferrite_u0",
        "tx_outer_void_pet_psa_u0",
        "tx_outer_underlay_pet_psa_u0",
        "tx_outer_underlay_ferrite_u0",
    )
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_objects = _tx_inner_rx_modeled_objects_with_imported_names(tmp_path)
    tx_outer_entry = _tx_outer_single_coil_entry(outer_tilt_protrusion_mm=10.0)
    tx_outer_expected_names = [
        "tx_outer_pcb_l0",
        "tx_outer_copper_l0",
        *passive_names,
    ]
    tx_outer_entry["expected_exported_body_names"] = tx_outer_expected_names
    tx_outer_entry["expected_exported_body_count"] = len(tx_outer_expected_names)
    tx_outer_entry["expected_exported_body_groups"] = _expected_ferrite_group_for_role(
        role="tx_outer_single_coil",
        expected_names=tx_outer_expected_names,
    )
    tx_outer_entry["imported_object_names"] = tx_outer_expected_names
    modeled_objects.append(tx_outer_entry)
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry_with_tx_inner_and_outer_regions()],
        modeled_objects=modeled_objects,
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(
        modeler=_SetupReadyModeler(
            imported_name_batches=[_tx_inner_outer_rx_imported_name_batch(include_tx_outer_void_stack=True)]
        )
    )

    result = cast(
        Type2SetupReadyResult,
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            design_name="fake_type2_setup_ready",
            hfss_factory=lambda _: cast(HfssSession, session),
        ),
    )

    assert session.mesh_module.assign_length_op_calls == [_expected_mesh_length_payload(tx_object_name="tx_inner_copper_l0")]
    assert session._excitation_names == ["1_T1", "2_T1"]
    assert result["ports"] == {"tx": ["1_T1"], "rx": ["2_T1"]}
    assert result["sources"]["tx_source_name"] == "1_T1"
    assert result["sources"]["rx_source_name"] == "2_T1"
    assert result["mesh"]["objects"] == ["tx_inner_copper_l0", "rx_copper_l0"]
    setup_participant_payload = json.dumps(
        {
            "mesh_calls": session.mesh_module.assign_length_op_calls,
            "port_calls": session.oboundary.assign_lumped_port_calls,
            "source_calls": session.edited_sources_payloads,
            "output_variables": session.created_output_variables,
            "reports": session.created_reports,
        }
    )
    for passive_name in passive_names:
        assert passive_name not in result["mesh"]["objects"]
        assert passive_name not in setup_participant_payload
    imported_payload = _imported_ledger_payload(imported_ledger_path)
    imported_modeled_objects = cast(list[dict[str, object]], imported_payload["modeled_objects"])
    assert sorted(cast(str, entry["role"]) for entry in imported_modeled_objects) == [
        "rx_single_coil",
        "tx_inner_single_coil",
        "tx_outer_single_coil",
    ]


def test_setup_type2_step_ledger_keeps_tx_bridge_members_as_non_model_setup_targets(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_objects = _tx_inner_rx_modeled_objects_with_imported_names(tmp_path)
    bridge_names = [
        "tx_pos_bridge_pcb",
        "tx_pos_bridge_copper",
        "tx_neg_bridge_pcb",
        "tx_neg_bridge_copper",
    ]
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry_with_tx_bridge_members_for_setup()],
        modeled_objects=modeled_objects,
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    modeler_names = _tx_inner_rx_imported_name_batch() + tuple(bridge_names)
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[modeler_names]))

    result = cast(
        Type2SetupReadyResult,
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            design_name="fake_type2_setup_ready",
            hfss_factory=lambda _: cast(HfssSession, session),
        ),
    )

    assert result["ports"] == {"tx": ["1_T1"], "rx": ["2_T1"]}

    imported_payload = _imported_ledger_payload(imported_ledger_path)
    non_model_entries = cast(list[dict[str, object]], imported_payload["non_model_objects"])
    modeled_entries = cast(list[dict[str, object]], imported_payload["modeled_objects"])
    non_model_by_id = {cast(str, entry["object_id"]): entry for entry in non_model_entries}
    modeled_by_id = {cast(str, entry["object_id"]): entry for entry in modeled_entries}

    non_model_entry = cast(dict[str, object], non_model_by_id["type2_non_model_scene"])
    non_model_imported_names = cast(list[str], non_model_entry["imported_object_names"])
    assert non_model_imported_names[-4:] == bridge_names

    tx_entry = cast(dict[str, object], modeled_by_id["tx_inner_rect_void_coil"])
    rx_entry = cast(dict[str, object], modeled_by_id["rx_rect_void_coil"])
    tx_imported_names = cast(list[str], tx_entry["imported_object_names"])
    rx_imported_names = cast(list[str], rx_entry["imported_object_names"])
    for bridge_name in bridge_names:
        assert bridge_name not in tx_imported_names
        assert bridge_name not in rx_imported_names


def test_setup_type2_step_ledger_assigns_requested_design_variables_before_save(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry_with_tx_inner_region()],
        modeled_objects=_tx_inner_rx_modeled_objects_with_imported_names(tmp_path),
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_tx_inner_rx_imported_name_batch()]))

    result = cast(
        Type2SetupReadyResult,
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            design_name="fake_type2_setup_ready",
            hfss_factory=lambda _: cast(HfssSession, session),
            design_variables=(
                ("modeled_objects_tx_rect_void_coil_outer_x_mm", "157.8mm"),
                ("modeled_objects_tx_rect_void_coil_margin_ratio", "0.05"),
                ("modeled_objects_tx_rect_void_coil_turn_count", "2"),
            ),
        ),
    )

    assert session.design_variables == {
        "modeled_objects_tx_rect_void_coil_outer_x_mm": "157.8mm",
        "modeled_objects_tx_rect_void_coil_margin_ratio": "0.05",
        "modeled_objects_tx_rect_void_coil_turn_count": "2",
    }
    assert result["aedt_path"] == str(output_aedt_path)
    assert session.save_project_calls == [str(output_aedt_path)]


def test_setup_type2_step_ledger_keeps_mesh_conductor_only_for_tx_inner_single_coil_and_rx_single_coil(
    tmp_path: Path,
) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry_with_tx_inner_region()],
        modeled_objects=_tx_inner_rx_modeled_objects_with_imported_names(tmp_path),
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(
        modeler=_SetupReadyModeler(imported_name_batches=[_tx_inner_rx_imported_name_batch()])
    )

    result = cast(
        Type2SetupReadyResult,
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            design_name="fake_type2_setup_ready",
            hfss_factory=lambda _: cast(HfssSession, session),
        ),
    )

    assert session.mesh_module.assign_length_op_calls == [_expected_mesh_length_payload(tx_object_name="tx_inner_copper_l0")]
    assert result["mesh"]["objects"] == ["tx_inner_copper_l0", "rx_copper_l0"]


def test_setup_type2_step_ledger_keeps_tx_inner_underlay_and_void_stack_passive_for_setup_ready(
    tmp_path: Path,
) -> None:
    passive_names = (
        "tx_underlay_pet_psa_u0",
        "tx_underlay_ferrite_u0",
        "tx_void_ferrite_u0",
        "tx_void_pet_psa_u0",
    )
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_objects = _tx_inner_rx_modeled_objects_with_tx_inner_underlay_imported_names(tmp_path)
    tx_entry = cast(dict[str, object], modeled_objects[0])
    tx_imported_names = cast(list[str], tx_entry["imported_object_names"])
    for passive_name in passive_names[:2]:
        assert passive_name in tx_imported_names
    imported_name_batch = _tx_inner_rx_imported_name_batch_with_tx_inner_underlay()
    for passive_name in passive_names:
        assert passive_name in imported_name_batch
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry_with_tx_inner_void_stack_members_for_setup()],
        modeled_objects=modeled_objects,
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(
        modeler=_SetupReadyModeler(imported_name_batches=[imported_name_batch])
    )

    result = cast(
        Type2SetupReadyResult,
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            design_name="fake_type2_setup_ready",
            hfss_factory=lambda _: cast(HfssSession, session),
        ),
    )

    assert session.mesh_module.assign_length_op_calls == [_expected_mesh_length_payload(tx_object_name="tx_inner_copper_l0")]
    assert session._excitation_names == ["1_T1", "2_T1"]
    assert result["ports"] == {"tx": ["1_T1"], "rx": ["2_T1"]}
    assert result["sources"]["tx_source_name"] == "1_T1"
    assert result["sources"]["rx_source_name"] == "2_T1"
    assert result["mesh"]["objects"] == ["tx_inner_copper_l0", "rx_copper_l0"]
    setup_participant_payload = json.dumps(
        {
            "mesh_calls": session.mesh_module.assign_length_op_calls,
            "port_calls": session.oboundary.assign_lumped_port_calls,
            "source_calls": session.edited_sources_payloads,
            "output_variables": session.created_output_variables,
            "reports": session.created_reports,
        }
    )
    for passive_name in passive_names:
        assert passive_name not in result["mesh"]["objects"]
        assert passive_name not in setup_participant_payload


def test_setup_type2_step_ledger_into_hfss_auto_detaches_after_setup(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_rx_single_coil_entry(tmp_path)],
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_rx_only_imported_name_batch()]))

    result = setup_type2_step_ledger_into_hfss(
        hfss=cast(HfssSession, session),
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
    )

    assert result["aedt_path"] == str(output_aedt_path)
    assert session.insert_design_calls == ["type2_step_import"]
    assert session.desktop_class.release_calls == [(False, False)]


def test_setup_type2_step_ledger_into_hfss_can_skip_aedt_validate_design(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_rx_single_coil_entry(tmp_path)],
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_rx_only_imported_name_batch()]))
    session.validate_design_result = False

    result = setup_type2_step_ledger_into_hfss(
        hfss=cast(HfssSession, session),
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        run_aedt_design_validation=False,
    )

    assert result["aedt_path"] == str(output_aedt_path)
    design = cast(_SetupReadyDesign, session.odesign)
    assert design.validate_design_calls == 0
    assert session.save_project_calls == [str(output_aedt_path)]


def test_setup_type2_step_ledger_rejects_tx_plate_style_modeled_roles_before_hfss(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[
            _modeled_entry(
                source_metadata_path=str(tmp_path / "tx.metadata.json"),
                expected_names=["tx_pcb_l0", "tx_pcb_l1", "tx_copper_stack"],
                pcb_layer_positions_mm=[87.2, 91.3],
                copper_layer_positions_mm=[88.8, 92.9],
            ),
            _rx_single_coil_entry(tmp_path),
        ],
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(
        modeler=_SetupReadyModeler(
            imported_name_batches=[
                (
                    "environment",
                    "tx_region",
                    *_tx_region_actual_member_names(),
                    "rx_region_max",
                    "tx_pcb_l0",
                    "tx_pcb_l1",
                    "tx_copper_stack",
                    "rx_pcb_l0",
                    "rx_copper_l0",
                )
            ]
        )
    )

    with pytest.raises(
        ValueError,
        match=r"type2 setup mode 'TxRx' supports only \['tx_inner_single_coil', 'rx_single_coil'\] for setup-ready orchestration",
    ):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            design_name="fake_type2_setup_ready",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_assign_post_import_mesh_ignores_tx_and_rx_underlay_exact_name_bodies() -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))

    result = assign_post_import_mesh(
        hfss=cast(HfssSession, session),
        imported_modeled_objects=_role_aware_mesh_entries(tx_object_name="tx_copper_stack"),
    )

    assert session.mesh_module.assign_length_op_calls == [_expected_mesh_length_payload(tx_object_name="tx_copper_stack")]
    assert result["objects"] == ["tx_copper_stack", "rx_copper_l0"]


def test_assign_post_import_mesh_rejects_rx_underlay_names_without_rx_copper() -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    imported_modeled_objects = _role_aware_mesh_entries()
    imported_modeled_objects[1]["imported_object_names"] = [
        "rx_pcb_l0",
        "under_rx_ferrite_u0",
        "under_rx_pet_psa_u0",
        "under_rx_air_u0",
        "rx_port_sheet",
    ]

    with pytest.raises(ValueError, match=r"requires rx_single_coil exact imported object name 'rx_copper_l0'"):
        assign_post_import_mesh(
            hfss=cast(HfssSession, session),
            imported_modeled_objects=imported_modeled_objects,
        )


def test_assign_post_import_mesh_accepts_plate_stack_exact_pair(tmp_path: Path) -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    imported_modeled_objects = _plate_stack_modeled_objects_with_imported_names(tmp_path)

    result = assign_post_import_mesh(
        hfss=cast(HfssSession, session),
        imported_modeled_objects=imported_modeled_objects,
    )

    tx_expected = _plate_stack_copper_family_imported_names(
        imported_object_names=cast(list[str], imported_modeled_objects[0]["imported_object_names"]),
        role_prefix="tx",
    )
    rx_expected = _plate_stack_copper_family_imported_names(
        imported_object_names=cast(list[str], imported_modeled_objects[1]["imported_object_names"]),
        role_prefix="rx",
    )
    expected_objects = [*tx_expected, *rx_expected]
    payload = session.mesh_module.assign_length_op_calls[0]
    objects_index = payload.index("Objects:=")

    assert result["objects"] == expected_objects
    assert payload[objects_index + 1] == expected_objects


def test_assign_post_import_mesh_accepts_tx_plate_stack_with_rx_single_coil_mesh(tmp_path: Path) -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    modeled_objects = _plate_stack_modeled_objects_with_imported_names(tmp_path)
    modeled_objects[1] = _coil_modeled_objects_with_imported_names(tmp_path)[1]

    result = assign_post_import_mesh(
        hfss=cast(HfssSession, session),
        imported_modeled_objects=modeled_objects,
    )

    payload = session.mesh_module.assign_length_op_calls[0]
    objects_index = payload.index("Objects:=")

    assert result["objects"] == ["tx_plate_copper", "rx_copper_l0"]
    assert payload[objects_index + 1] == ["tx_plate_copper", "rx_copper_l0"]


def test_assign_post_import_mesh_accepts_tx_inner_single_coil_with_rx_single_coil_mesh() -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    modeled_objects = _role_aware_mesh_entries(
        tx_role="tx_inner_single_coil",
        tx_object_name="tx_inner_copper_l0",
        tx_pcb_name="tx_inner_pcb_l0",
        tx_object_id="tx_inner_rect_void_coil",
        tx_sheet_name="tx_inner_port_sheet",
    )

    result = assign_post_import_mesh(
        hfss=cast(HfssSession, session),
        imported_modeled_objects=modeled_objects,
    )

    payload = session.mesh_module.assign_length_op_calls[0]
    objects_index = payload.index("Objects:=")

    assert result["objects"] == ["tx_inner_copper_l0", "rx_copper_l0"]
    assert payload[objects_index + 1] == ["tx_inner_copper_l0", "rx_copper_l0"]


def test_assign_post_import_mesh_accepts_rx_single_coil_only(tmp_path: Path) -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    modeled_objects = [_coil_modeled_objects_with_imported_names(tmp_path)[1]]

    result = assign_post_import_mesh(
        hfss=cast(HfssSession, session),
        imported_modeled_objects=modeled_objects,
    )

    assert session.mesh_module.assign_length_op_calls == [
        [
            "NAME:Length1",
            "RefineInside:=",
            False,
            "Enabled:=",
            True,
            "Objects:=",
            ["rx_copper_l0"],
            "RestrictElem:=",
            False,
            "NumMaxElem:=",
            "1000",
            "RestrictLength:=",
            True,
            "MaxLength:=",
            "5mm",
        ]
    ]
    assert result["objects"] == ["rx_copper_l0"]


def test_assign_post_import_mesh_rejects_plate_stack_legacy_segment_leakage(tmp_path: Path) -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    imported_modeled_objects = _plate_stack_modeled_objects_with_imported_names(tmp_path)
    tx_imported_names = cast(list[str], imported_modeled_objects[0]["imported_object_names"])
    tx_imported_names.append("tx_stub_in")

    with pytest.raises(ValueError, match=r"legacy plate-stack copper segment leakage"):
        assign_post_import_mesh(
            hfss=cast(HfssSession, session),
            imported_modeled_objects=imported_modeled_objects,
        )


@pytest.mark.parametrize("role", ["rx_plate_stack"])
def test_assign_post_import_mesh_rejects_mixed_role_families(role: str) -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    imported_modeled_objects = _role_aware_mesh_entries()
    target_index = 0 if role == "tx_plate_stack" else 1
    imported_modeled_objects[target_index]["role"] = role
    imported_modeled_objects[target_index]["object_id"] = "tx_plate_stack" if role == "tx_plate_stack" else "rx_plate_stack"

    with pytest.raises(ValueError, match=r"requires one exact supported tx/rx role pair"):
        assign_post_import_mesh(
            hfss=cast(HfssSession, session),
            imported_modeled_objects=imported_modeled_objects,
        )


def test_assign_type2_lumped_ports_accepts_plate_stack_exact_pair(tmp_path: Path) -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    modeled_objects = _plate_stack_modeled_objects_with_imported_names(tmp_path)
    _rewrite_plate_stack_terminal_metadata_to_equal_stripe_pitch(modeled_objects[0])
    _rewrite_plate_stack_terminal_metadata_to_equal_stripe_pitch(modeled_objects[1])
    tx_sheet_name = cast(str, cast(list[object], modeled_objects[0]["imported_object_names"])[-1])
    rx_sheet_name = cast(str, cast(list[object], modeled_objects[1]["imported_object_names"])[-1])
    _seed_port_sheet_edges_from_terminal_metadata(
        cast(_SetupReadyModeler, session.modeler),
        entry=modeled_objects[0],
        sheet_name=tx_sheet_name,
    )
    _seed_port_sheet_edges_from_terminal_metadata(
        cast(_SetupReadyModeler, session.modeler),
        entry=modeled_objects[1],
        sheet_name=rx_sheet_name,
    )

    result = assign_type2_lumped_ports(
        hfss=cast(HfssSession, session),
        modeler=cast(ModelerSession, session.modeler),
        imported_ledger=cast(Type2ImportedLedger, {"modeled_objects": modeled_objects}),
    )

    assert len(session.oboundary.assign_lumped_port_calls) == 2
    for payload in session.oboundary.assign_lumped_port_calls:
        edges_index = payload.index("Edges:=")
        edge_ids = cast(list[int], payload[edges_index + 1])
        assert len(edge_ids) == 2
        signal_vertex_ids = cast(_SetupReadyModeler, session.modeler).get_edge_vertices(edge_ids[0])
        reference_vertex_ids = cast(_SetupReadyModeler, session.modeler).get_edge_vertices(edge_ids[1])
        signal_vertices = [
            cast(tuple[float, float, float], tuple(cast(_SetupReadyModeler, session.modeler).get_vertex_position(vertex_id)))
            for vertex_id in signal_vertex_ids
        ]
        reference_vertices = [
            cast(tuple[float, float, float], tuple(cast(_SetupReadyModeler, session.modeler).get_vertex_position(vertex_id)))
            for vertex_id in reference_vertex_ids
        ]
        signal_x_values = {vertex[0] for vertex in signal_vertices}
        reference_x_values = {vertex[0] for vertex in reference_vertices}
        signal_y_values = {vertex[1] for vertex in signal_vertices}
        reference_y_values = {vertex[1] for vertex in reference_vertices}
        signal_z_values = {vertex[2] for vertex in signal_vertices}
        reference_z_values = {vertex[2] for vertex in reference_vertices}
        assert len(signal_x_values) == 1
        assert len(reference_x_values) == 1
        assert signal_x_values != reference_x_values
        assert len(signal_y_values) == 1
        assert len(reference_y_values) == 1
        assert len(signal_z_values) == 2
        assert len(reference_z_values) == 2
    assert session._excitation_names == ["1_T1", "2_T1"]
    assert result == {"tx": ["1_T1"], "rx": ["2_T1"]}


def test_assign_type2_lumped_ports_accepts_tx_plate_stack_with_rx_single_coil_ports(tmp_path: Path) -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    modeled_objects = _plate_stack_modeled_objects_with_imported_names(tmp_path)
    modeled_objects[1] = _coil_modeled_objects_with_imported_names(tmp_path)[1]
    _rewrite_plate_stack_terminal_metadata_to_equal_stripe_pitch(modeled_objects[0])
    tx_sheet_name = cast(str, cast(list[object], modeled_objects[0]["imported_object_names"])[-1])
    rx_sheet_name = cast(str, cast(list[object], modeled_objects[1]["imported_object_names"])[-1])
    _seed_port_sheet_edges_from_terminal_metadata(
        cast(_SetupReadyModeler, session.modeler),
        entry=modeled_objects[0],
        sheet_name=tx_sheet_name,
    )
    _seed_port_sheet_edges_from_terminal_metadata(
        cast(_SetupReadyModeler, session.modeler),
        entry=modeled_objects[1],
        sheet_name=rx_sheet_name,
    )

    result = assign_type2_lumped_ports(
        hfss=cast(HfssSession, session),
        modeler=cast(ModelerSession, session.modeler),
        imported_ledger=cast(Type2ImportedLedger, {"modeled_objects": modeled_objects}),
    )

    assert len(session.oboundary.assign_lumped_port_calls) == 2
    assert session._excitation_names == ["1_T1", "2_T1"]
    assert result == {"tx": ["1_T1"], "rx": ["2_T1"]}


def test_assign_type2_lumped_ports_accepts_tx_inner_single_coil_with_rx_single_coil_ports(tmp_path: Path) -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    tx_inner_entry = _tx_inner_single_coil_modeled_object_with_imported_names(tmp_path)
    rx_entry = _coil_modeled_objects_with_imported_names(tmp_path)[1]
    modeled_objects = [tx_inner_entry, rx_entry]
    tx_sheet_name = cast(str, cast(list[object], tx_inner_entry["imported_object_names"])[-1])
    rx_sheet_name = cast(str, cast(list[object], rx_entry["imported_object_names"])[-1])
    _seed_port_sheet_edges_from_terminal_metadata(
        cast(_SetupReadyModeler, session.modeler),
        entry=tx_inner_entry,
        sheet_name=tx_sheet_name,
    )
    _seed_port_sheet_edges_from_terminal_metadata(
        cast(_SetupReadyModeler, session.modeler),
        entry=rx_entry,
        sheet_name=rx_sheet_name,
    )

    result = assign_type2_lumped_ports(
        hfss=cast(HfssSession, session),
        modeler=cast(ModelerSession, session.modeler),
        imported_ledger=cast(Type2ImportedLedger, {"modeled_objects": modeled_objects}),
    )

    assert len(session.oboundary.assign_lumped_port_calls) == 2
    assert session._excitation_names == ["1_T1", "2_T1"]
    assert result == {"tx": ["1_T1"], "rx": ["2_T1"]}


def test_assign_type2_lumped_ports_uses_world_port_sheet_vertices_for_tx_inner_single_coil(tmp_path: Path) -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    tx_entry = _tx_inner_single_coil_modeled_object_with_imported_names(tmp_path)
    rx_entry = _rx_single_coil_modeled_object_with_imported_names(tmp_path)
    tx_terminal_metadata = cast(dict[str, object], tx_entry["terminal_metadata"])
    tx_terminal_metadata["port_sheet_vertices_xyz"] = [
        [110.0, 150.0, 250.0],
        [120.0, 150.0, 250.0],
        [120.0, 151.0, 254.0],
        [110.0, 151.0, 254.0],
    ]

    tx_sheet_name = cast(str, cast(list[object], tx_entry["imported_object_names"])[-1])
    rx_sheet_name = cast(str, cast(list[object], rx_entry["imported_object_names"])[-1])
    _seed_port_sheet_edges_from_terminal_metadata(
        cast(_SetupReadyModeler, session.modeler),
        entry=tx_entry,
        sheet_name=tx_sheet_name,
    )
    _seed_port_sheet_edges_from_terminal_metadata(
        cast(_SetupReadyModeler, session.modeler),
        entry=rx_entry,
        sheet_name=rx_sheet_name,
    )

    result = assign_type2_lumped_ports(
        hfss=cast(HfssSession, session),
        modeler=cast(ModelerSession, session.modeler),
        imported_ledger=cast(Type2ImportedLedger, {"modeled_objects": [tx_entry, rx_entry]}),
    )

    assert result == {"tx": ["1_T1"], "rx": ["2_T1"]}
    tx_payload = session.oboundary.assign_lumped_port_calls[0]
    tx_edges_index = tx_payload.index("Edges:=")
    tx_edge_ids = cast(list[int], tx_payload[tx_edges_index + 1])
    assert len(tx_edge_ids) == 2
    world_vertices_for_tx = {
        (110.0, 150.0, 250.0),
        (120.0, 150.0, 250.0),
        (120.0, 151.0, 254.0),
        (110.0, 151.0, 254.0),
    }
    tx_sheet_vertices: set[tuple[float, float, float]] = set()
    for edge_id in tx_edge_ids:
        first_id, second_id = cast(_SetupReadyModeler, session.modeler).get_edge_vertices(int(edge_id))
        for vertex_id in (first_id, second_id):
            vertex_position = cast(list[float], cast(_SetupReadyModeler, session.modeler).get_vertex_position(int(vertex_id)))
            assert len(vertex_position) == 3
            tx_sheet_vertices.add((vertex_position[0], vertex_position[1], vertex_position[2]))
    assert tx_sheet_vertices == world_vertices_for_tx


def test_assign_type2_lumped_ports_accepts_rx_single_coil_only(tmp_path: Path) -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    modeled_objects = [_coil_modeled_objects_with_imported_names(tmp_path)[1]]
    rx_sheet_name = cast(str, cast(list[object], modeled_objects[0]["imported_object_names"])[-1])
    _seed_port_sheet_edges_from_terminal_metadata(
        cast(_SetupReadyModeler, session.modeler),
        entry=modeled_objects[0],
        sheet_name=rx_sheet_name,
    )

    result = assign_type2_lumped_ports(
        hfss=cast(HfssSession, session),
        modeler=cast(ModelerSession, session.modeler),
        imported_ledger=cast(Type2ImportedLedger, {"modeled_objects": modeled_objects}),
    )

    assert len(session.oboundary.assign_lumped_port_calls) == 1
    assert session.oboundary.assign_lumped_port_calls[0][0] == "NAME:1"
    assert session._excitation_names == ["1_T1"]
    assert result == {"tx": [], "rx": ["1_T1"]}


@pytest.mark.parametrize("role", ["rx_plate_stack"])
def test_assign_type2_lumped_ports_rejects_mixed_role_families(tmp_path: Path, role: str) -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    modeled_objects = _plate_stack_modeled_objects_with_imported_names(tmp_path)
    if role == "tx_plate_stack":
        modeled_objects[1] = _coil_modeled_objects_with_imported_names(tmp_path)[1]
    else:
        modeled_objects[0] = _coil_modeled_objects_with_imported_names(tmp_path)[0]

    with pytest.raises(ValueError, match=r"requires one exact supported tx/rx role pair"):
        assign_type2_lumped_ports(
            hfss=cast(HfssSession, session),
            modeler=cast(ModelerSession, session.modeler),
            imported_ledger=cast(Type2ImportedLedger, {"modeled_objects": modeled_objects}),
        )


def test_assign_type2_lumped_ports_rejects_incomplete_plate_stack_pair(tmp_path: Path) -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    modeled_objects = _plate_stack_modeled_objects_with_imported_names(tmp_path)

    with pytest.raises(ValueError, match=r"accepts one modeled_objects entry only for rx_single_coil"):
        assign_type2_lumped_ports(
            hfss=cast(HfssSession, session),
            modeler=cast(ModelerSession, session.modeler),
            imported_ledger=cast(Type2ImportedLedger, {"modeled_objects": [modeled_objects[0]]}),
        )


def test_build_type2_em_input_accepts_plate_stack_exact_pair(tmp_path: Path) -> None:
    modeled_objects = _plate_stack_modeled_objects_with_imported_names(tmp_path)
    _rewrite_plate_stack_terminal_metadata_to_equal_stripe_pitch(modeled_objects[0])
    _rewrite_plate_stack_terminal_metadata_to_equal_stripe_pitch(modeled_objects[1])

    result = build_type2_em_input(
        imported_ledger=cast(Type2ImportedLedger, _minimal_em_input_ledger(modeled_objects=modeled_objects)),
        ports=cast(EmPorts, {"tx": ["1_T1"], "rx": ["2_T1"]}),
    )

    tx_imported_names = cast(list[str], modeled_objects[0]["imported_object_names"])
    rx_imported_names = cast(list[str], modeled_objects[1]["imported_object_names"])
    tx_expected_copper = _plate_stack_copper_family_imported_names(
        imported_object_names=tx_imported_names,
        role_prefix="tx",
    )
    rx_expected_copper = _plate_stack_copper_family_imported_names(
        imported_object_names=rx_imported_names,
        role_prefix="rx",
    )

    assert result["ready_objects"]["tx_conductors"] == sorted(tx_expected_copper)
    assert result["ready_objects"]["rx_conductors"] == sorted(rx_expected_copper)
    assert result["ready_objects"]["ferrite_objects"] == []
    assert result["ready_objects"]["fr4_objects"] == sorted(
        ["tx_pcb_wall", "tx_pcb_coil", "rx_pcb_wall", "rx_pcb_coil"]
    )
    assert result["endpoints"]["tx"][0]["group_kind"] == "tx_plate_stack"
    assert result["endpoints"]["tx"][0]["start_label"] == "input_stub"
    assert result["endpoints"]["tx"][0]["end_label"] == "output_stub"
    assert cast(tuple[float, float, float], result["endpoints"]["tx"][0]["end_xyz"])[2] > cast(
        tuple[float, float, float], result["endpoints"]["tx"][0]["start_xyz"]
    )[2]
    assert result["endpoints"]["rx"][0]["group_kind"] == "rx_plate_stack"
    assert result["endpoints"]["rx"][0]["start_label"] == "input_stub"
    assert result["endpoints"]["rx"][0]["end_label"] == "output_stub"
    assert cast(tuple[float, float, float], result["endpoints"]["rx"][0]["end_xyz"])[2] > cast(
        tuple[float, float, float], result["endpoints"]["rx"][0]["start_xyz"]
    )[2]
    assert result["context"]["tx_vertical_plane"] == "YZ"
    assert result["context"]["rx_plane"] == "YZ"
    assert result["ports"] == {"tx": ["1_T1"], "rx": ["2_T1"]}


def test_build_type2_em_input_accepts_tx_plate_stack_with_rx_single_coil(tmp_path: Path) -> None:
    tx_modeled = cast(
        dict[str, object],
        _plate_stack_modeled_objects_with_imported_names(tmp_path)[0],
    )
    rx_modeled = cast(dict[str, object], _coil_modeled_objects_with_imported_names(tmp_path)[1])
    _rewrite_plate_stack_terminal_metadata_to_equal_stripe_pitch(tx_modeled)
    modeled_objects = [tx_modeled, rx_modeled]

    result = build_type2_em_input(
        imported_ledger=cast(Type2ImportedLedger, _minimal_em_input_ledger(modeled_objects=modeled_objects)),
        ports=cast(EmPorts, {"tx": ["1_T1"], "rx": ["2_T1"]}),
    )

    assert result["ready_objects"]["tx_conductors"] == ["tx_plate_copper"]
    assert result["ready_objects"]["rx_conductors"] == ["rx_copper_l0"]
    assert result["endpoints"]["tx"][0]["group_kind"] == "tx_plate_stack"
    assert result["endpoints"]["rx"][0]["group_kind"] == "rx_dd"
    assert result["ports"] == {"tx": ["1_T1"], "rx": ["2_T1"]}


def test_build_type2_em_input_accepts_tx_inner_single_coil_with_rx_single_coil(tmp_path: Path) -> None:
    modeled_objects = [
        _tx_inner_single_coil_modeled_object_with_imported_names(tmp_path, include_tx_inner_underlay=True),
        cast(dict[str, object], _coil_modeled_objects_with_imported_names(tmp_path)[1]),
    ]

    result = build_type2_em_input(
        imported_ledger=cast(Type2ImportedLedger, _minimal_em_input_ledger(modeled_objects=modeled_objects)),
        ports=cast(EmPorts, {"tx": ["1_T1"], "rx": ["2_T1"]}),
    )

    assert result["ready_objects"]["tx_conductors"] == ["tx_inner_copper_l0"]
    assert result["ready_objects"]["rx_conductors"] == ["rx_copper_l0"]
    assert result["ready_objects"]["fr4_objects"] == ["rx_pcb_l0", "tx_inner_pcb_l0"]
    assert result["ready_objects"]["ferrite_objects"] == []
    assert result["endpoints"]["tx"][0]["group_kind"] == "tx_vertical"
    assert result["endpoints"]["rx"][0]["group_kind"] == "rx_dd"
    assert result["ports"] == {"tx": ["1_T1"], "rx": ["2_T1"]}


def test_build_type2_em_input_accepts_rx_single_coil_only(tmp_path: Path) -> None:
    modeled_objects = [_coil_modeled_objects_with_imported_names(tmp_path)[1]]

    result = build_type2_em_input(
        imported_ledger=cast(Type2ImportedLedger, _minimal_em_input_ledger(modeled_objects=modeled_objects)),
        ports=cast(EmPorts, {"tx": [], "rx": ["1_T1"]}),
    )

    assert result["ready_objects"]["tx_conductors"] == []
    assert result["ready_objects"]["rx_conductors"] == ["rx_copper_l0"]
    assert result["ready_objects"]["fr4_objects"] == ["rx_pcb_l0"]
    assert result["ready_objects"]["ferrite_objects"] == []
    assert result["endpoints"]["tx"] == []
    assert result["endpoints"]["rx"][0]["group_kind"] == "rx_dd"
    assert result["context"]["tx_vertical_plane"] == "YZ"
    assert result["context"]["rx_plane"] == "YZ"
    assert result["ports"] == {"tx": [], "rx": ["1_T1"]}


def test_build_type2_em_input_accepts_tx_plate_stack_array_branch_pcb_names(tmp_path: Path) -> None:
    modeled_objects = _plate_stack_modeled_objects_with_imported_names(tmp_path)
    _rewrite_plate_stack_terminal_metadata_to_equal_stripe_pitch(modeled_objects[0])
    _rewrite_plate_stack_terminal_metadata_to_equal_stripe_pitch(modeled_objects[1])
    tx_imported_names = cast(list[str], modeled_objects[0]["imported_object_names"])
    tx_imported_names[:] = [
        "tx_plate_copper",
        "tx_b0_pcb_wall",
        "tx_b0_pcb_coil",
        "tx_b1_pcb_wall",
        "tx_b1_pcb_coil",
        "tx_b0_stack_pet_psa",
        "tx_b0_stack_ferrite",
        "tx_b0_stack_air",
        "tx_b1_stack_pet_psa",
        "tx_b1_stack_ferrite",
        "tx_b1_stack_air",
        "tx_plate_port_sheet",
    ]

    result = build_type2_em_input(
        imported_ledger=cast(Type2ImportedLedger, _minimal_em_input_ledger(modeled_objects=modeled_objects)),
        ports=cast(EmPorts, {"tx": ["1_T1"], "rx": ["2_T1"]}),
    )

    assert result["ready_objects"]["tx_conductors"] == ["tx_plate_copper"]
    assert result["ready_objects"]["rx_conductors"] == ["rx_plate_copper"]
    assert result["ready_objects"]["fr4_objects"] == sorted(
        [
            "tx_b0_pcb_wall",
            "tx_b0_pcb_coil",
            "tx_b1_pcb_wall",
            "tx_b1_pcb_coil",
            "rx_pcb_wall",
            "rx_pcb_coil",
        ]
    )


def test_build_type2_em_input_rejects_plate_stack_legacy_segment_leakage(tmp_path: Path) -> None:
    modeled_objects = _plate_stack_modeled_objects_with_imported_names(tmp_path)
    tx_imported_names = cast(list[str], modeled_objects[0]["imported_object_names"])
    tx_imported_names.append("tx_bridge_s0")

    with pytest.raises(ValueError, match=r"legacy plate-stack copper segment leakage"):
        build_type2_em_input(
            imported_ledger=cast(Type2ImportedLedger, _minimal_em_input_ledger(modeled_objects=modeled_objects)),
            ports=cast(EmPorts, {"tx": ["1_T1"], "rx": ["2_T1"]}),
        )


def test_build_type2_em_input_rejects_inverse_mixed_role_family(tmp_path: Path) -> None:
    modeled_objects = _plate_stack_modeled_objects_with_imported_names(tmp_path)
    modeled_objects[0] = _coil_modeled_objects_with_imported_names(tmp_path)[0]

    with pytest.raises(ValueError, match=r"requires one exact supported tx/rx role pair"):
        build_type2_em_input(
            imported_ledger=cast(Type2ImportedLedger, _minimal_em_input_ledger(modeled_objects=modeled_objects)),
            ports=cast(EmPorts, {"tx": ["1_T1"], "rx": ["2_T1"]}),
        )


def test_setup_type2_step_ledger_raises_when_required_mesh_role_is_missing(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_single_layer_modeled_objects(tmp_path)[0]],
    )
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(
        modeler=_SetupReadyModeler(
            imported_name_batches=[("environment", "tx_region", *_tx_region_actual_member_names(), "rx_region_max", "tx_pcb_l0", "tx_copper_l0")]
        )
    )

    with pytest.raises(
        ValueError,
        match=r"supports a single modeled role only for RX-only mode",
    ):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=imported_ledger_path,
            hfss_factory=lambda _: cast(HfssSession, session),
        )

    assert session.desktop_class.release_calls == []
    assert not imported_ledger_path.exists()


def test_setup_type2_step_ledger_rx_single_coil_only_runs_full_rx_only_setup_ready(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_rx_single_coil_entry(tmp_path)],
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_rx_only_imported_name_batch()]))

    result = setup_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    assert session.mesh_module.assign_length_op_calls == [
        [
            "NAME:Length1",
            "RefineInside:=",
            False,
            "Enabled:=",
            True,
            "Objects:=",
            ["rx_copper_l0"],
            "RestrictElem:=",
            False,
            "NumMaxElem:=",
            "1000",
            "RestrictLength:=",
            True,
            "MaxLength:=",
            "5mm",
        ]
    ]
    assert len(session.oboundary.assign_lumped_port_calls) == 1
    assert result["ports"] == {"tx": [], "rx": ["1_T1"]}
    assert result["sources"] == {
        "rx_source_name": "1_T1",
        "rx_phase_deg": "0deg",
        "rx_magnitude": "1V",
    }
    assert session._excitation_names == ["1_T1"]
    assert session.created_output_variables == _expected_rx_only_output_variables()
    assert all("TX_TML" not in expression for _name, expression, _solution in session.created_output_variables)
    assert all(not name.lower().startswith(("tx", "s21", "fom")) for name, _expression, _solution in session.created_output_variables)
    outputs = type1_outputs_spec()
    assert session.created_reports[0]["components"] == [
        "X Component:=",
        outputs["primary_sweep"],
        "Y Component:=",
        [name for name, _expression, _solution in _expected_rx_only_output_variables()],
    ]
    assert session.save_project_calls == [str(output_aedt_path)]
    assert session.desktop_class.release_calls == [(True, True)]


def test_solve_type2_setup_ready_hfss_analyzes_and_exports_report(tmp_path: Path) -> None:
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[]))
    session.created_reports.append({"plot_name": "Output Variables Table1"})

    result = solve_type2_setup_ready_hfss(
        cast(HfssSession, session),
        output_dir=tmp_path,
    )

    expected_csv = tmp_path / "Output_Variables_Table1.csv"
    assert result == {
        "setup_name": "Setup1",
        "report_name": "Output Variables Table1",
        "report_csv_path": str(expected_csv),
    }
    assert session.analyze_setup_calls == [("Setup1", True)]
    assert session.exported_report_calls == [("Output Variables Table1", str(expected_csv))]
    assert expected_csv.is_file()


def test_setup_and_solve_type2_step_ledger_keeps_session_for_analysis_export(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_rx_single_coil_entry(tmp_path)],
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_rx_only_imported_name_batch()]))

    result = setup_and_solve_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    expected_csv = output_aedt_path.parent / "Output_Variables_Table1.csv"
    assert result["em_solve"]["report_csv_path"] == str(expected_csv)
    assert session.analyze_setup_calls == [("Setup1", True)]
    assert session.exported_report_calls == [("Output Variables Table1", str(expected_csv))]
    assert session.save_project_calls == [str(output_aedt_path), str(output_aedt_path)]
    assert session.desktop_class.release_calls == [(True, True)]


def test_setup_type2_step_ledger_raises_when_port_sheet_vertices_are_malformed(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_objects = _tx_inner_rx_modeled_objects_with_imported_names(tmp_path)
    terminal_metadata = cast(dict[str, object], modeled_objects[0]["terminal_metadata"])
    terminal_metadata["port_sheet_vertices_xyz"] = [[1.0, 2.0, 3.0]]
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry_with_tx_inner_region()],
        modeled_objects=modeled_objects,
    )
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_tx_inner_rx_imported_name_batch()]))

    with pytest.raises(ValueError, match=r"port_sheet_vertices_xyz must contain exactly 4 vertices"):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_setup_type2_step_ledger_raises_when_sheet_edge_resolution_is_not_unique(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry_with_tx_inner_region()],
        modeled_objects=_tx_inner_rx_modeled_objects_with_imported_names(tmp_path),
    )
    modeler = _SetupReadyModeler(imported_name_batches=[_tx_inner_rx_imported_name_batch()])
    modeler.duplicate_matching_edges = True
    session = _SetupReadyHfss(modeler=modeler)

    with pytest.raises(ValueError, match=r"edge resolution must find exactly one matching sheet edge"):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_setup_type2_step_ledger_raises_when_assign_lumped_port_returns_false(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry_with_tx_inner_region()],
        modeled_objects=_tx_inner_rx_modeled_objects_with_imported_names(tmp_path),
    )
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_tx_inner_rx_imported_name_batch()]))
    session.oboundary.assign_lumped_port_result = False

    with pytest.raises(RuntimeError, match=r"AssignLumpedPort"):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_setup_type2_step_ledger_raises_when_excitation_capture_mismatches_expected_name(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry_with_tx_inner_region()],
        modeled_objects=_tx_inner_rx_modeled_objects_with_imported_names(tmp_path),
    )
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_tx_inner_rx_imported_name_batch()]))
    session.oboundary.excitation_name_override = "wrong"

    with pytest.raises(ValueError, match=r"must create expected excitation"):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_setup_type2_step_ledger_raises_when_create_region_returns_false(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry_with_tx_inner_region()],
        modeled_objects=_tx_inner_rx_modeled_objects_with_imported_names(tmp_path),
    )
    modeler = _SetupReadyModeler(imported_name_batches=[_tx_inner_rx_imported_name_batch()])
    modeler.create_region_returns_false = True
    session = _SetupReadyHfss(modeler=modeler)

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: create_region"):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_setup_type2_step_ledger_raises_when_created_region_does_not_expose_six_faces(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry_with_tx_inner_region()],
        modeled_objects=_tx_inner_rx_modeled_objects_with_imported_names(tmp_path),
    )
    session = _SetupReadyHfss(
        modeler=_SetupReadyModeler(imported_name_batches=[_tx_inner_rx_imported_name_batch()])
    )
    session.modeler.region_faces = [10, 11, 12, 13, 14]

    with pytest.raises(ValueError, match=r"Created region does not expose 6 faces required for radiation assignment"):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_setup_type2_step_ledger_raises_when_radiation_assignment_returns_false(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry_with_tx_inner_region()],
        modeled_objects=_tx_inner_rx_modeled_objects_with_imported_names(tmp_path),
    )
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_tx_inner_rx_imported_name_batch()]))
    session.radiation_boundary_result = False

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: assign_radiation_boundary_to_faces"):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_setup_type2_step_ledger_raises_when_validate_design_returns_false(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry_with_tx_inner_region()],
        modeled_objects=_tx_inner_rx_modeled_objects_with_imported_names(tmp_path),
    )
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_tx_inner_rx_imported_name_batch()]))
    session.validate_design_result = False
    session.desktop_class.messages = ["port assignment is invalid"]

    with pytest.raises(RuntimeError, match=r"ValidateDesign.*port assignment is invalid"):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_setup_type2_step_ledger_rejects_plate_stack_exact_pair_before_hfss(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_objects = _plate_stack_modeled_objects(tmp_path)
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_plate_stack_non_model_entry()],
        modeled_objects=modeled_objects,
    )
    with pytest.raises(
        ValueError,
        match=r"type2 setup mode 'TxRx' supports only \['tx_inner_single_coil', 'rx_single_coil'\] for setup-ready orchestration",
    ):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _design_name: (_ for _ in ()).throw(AssertionError("hfss_factory must not run")),
        )


def test_setup_type2_step_ledger_rejects_tx_rect_void_columns_with_rx_single_coil_before_hfss(
    tmp_path: Path,
) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_objects = [_tx_rect_void_columns_entry(tmp_path), _rx_single_coil_entry(tmp_path)]
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_tx_rect_void_columns_non_model_entry()],
        modeled_objects=modeled_objects,
    )
    with pytest.raises(
        ValueError,
        match=r"type2 setup mode 'TxRx' supports only \['tx_inner_single_coil', 'rx_single_coil'\] for setup-ready orchestration",
    ):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _design_name: (_ for _ in ()).throw(AssertionError("hfss_factory must not run")),
        )


def test_setup_type2_step_ledger_rejects_rotated_tx_plate_stack_array_port_sheet_before_hfss(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    branch_count = 3
    modeled_objects = [_tx_array_modeled_entry(tmp_path, branch_count=branch_count), _rx_plate_stack_entry(tmp_path)]
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_plate_stack_non_model_entry()],
        modeled_objects=modeled_objects,
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    with pytest.raises(
        ValueError,
        match=r"type2 setup mode 'TxRx' supports only \['tx_inner_single_coil', 'rx_single_coil'\] for setup-ready orchestration",
    ):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            hfss_factory=lambda _design_name: (_ for _ in ()).throw(AssertionError("hfss_factory must not run")),
        )


def test_setup_type2_step_ledger_rejects_tx_plate_stack_with_rx_single_coil_before_hfss(
    tmp_path: Path,
) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_objects = _plate_stack_modeled_objects(tmp_path)
    modeled_objects[1] = _rx_single_coil_entry(tmp_path)
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=modeled_objects,
    )
    with pytest.raises(
        ValueError,
        match=r"type2 setup mode 'TxRx' supports only \['tx_inner_single_coil', 'rx_single_coil'\] for setup-ready orchestration",
    ):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _design_name: (_ for _ in ()).throw(AssertionError("hfss_factory must not run")),
        )


def test_setup_type2_step_ledger_rejects_inverse_mixed_role_family_before_hfss(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_objects = _plate_stack_modeled_objects(tmp_path)
    modeled_objects[0] = _modeled_entry(source_metadata_path=str(tmp_path / "tx.metadata.json"))
    _write_txrx_step_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=modeled_objects,
    )

    with pytest.raises(
        ValueError,
        match=r"type2 setup mode 'TxRx' supports only \['tx_inner_single_coil', 'rx_single_coil'\] for setup-ready orchestration",
    ):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _design_name: (_ for _ in ()).throw(AssertionError("hfss_factory must not run")),
        )


def test_setup_type2_step_ledger_rejects_incomplete_plate_stack_pair_before_hfss(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_objects = [_plate_stack_modeled_objects(tmp_path)[0]]
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=modeled_objects,
    )

    with pytest.raises(
        ValueError,
        match=r"supports a single modeled role only for RX-only mode",
    ):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
        hfss_factory=lambda _design_name: (_ for _ in ()).throw(AssertionError("hfss_factory must not run")),
        )


def test_setup_type2_step_ledger_rejects_tx_inner_single_coil_before_hfss(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_tx_inner_single_coil_modeled_object_with_imported_names(tmp_path)],
    )

    with pytest.raises(
        ValueError,
        match=r"type2 STEP ledger must contain exactly one tx_inner_region member object",
    ):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _design_name: (_ for _ in ()).throw(AssertionError("hfss_factory must not run")),
        )


def test_setup_type2_step_ledger_rejects_tx_rect_void_columns_parallel_collector_tabs_without_tab_faces_before_hfss(
    tmp_path: Path,
) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_object = _modeled_entry(
        object_id="tx_rect_void_columns",
        role="tx_rect_void_columns",
        plane="XY",
        placement_owner_id="tx_region_actual_stack_space",
        source_metadata_path=str(tmp_path / "tx_rect_void_columns.metadata.json"),
    )
    modeled_object["terminal_metadata"] = _tx_rect_void_columns_terminal_metadata()
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_tx_rect_void_columns_non_model_entry()],
        modeled_objects=[modeled_object],
    )

    with pytest.raises(
        ValueError,
        match=r"supports a single modeled role only for RX-only mode",
    ):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _design_name: (_ for _ in ()).throw(AssertionError("hfss_factory must not run")),
        )


def test_setup_type2_step_ledger_rejects_tx_rect_void_columns_series_collector_tabs_without_tab_faces_before_hfss(
    tmp_path: Path,
) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_object = _modeled_entry(
        object_id="tx_rect_void_columns",
        role="tx_rect_void_columns",
        plane="XY",
        placement_owner_id="tx_region_actual_stack_space",
        source_metadata_path=str(tmp_path / "tx_rect_void_columns.metadata.json"),
    )
    modeled_object["terminal_metadata"] = _tx_rect_void_columns_terminal_metadata()
    cast(dict[str, object], modeled_object["terminal_metadata"])["kind"] = "series_collector_tabs"
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_tx_rect_void_columns_non_model_entry()],
        modeled_objects=[modeled_object],
    )

    with pytest.raises(
        ValueError,
        match=r"supports a single modeled role only for RX-only mode",
    ):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _design_name: (_ for _ in ()).throw(AssertionError("hfss_factory must not run")),
        )

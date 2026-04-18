from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from peetsfea.aedt.protocols import HfssSession
from peetsfea.backend.pyaedt.type2_step_post_import_mesh import assign_post_import_mesh
from peetsfea.backend.pyaedt.type2_step_setup_ready import (
    setup_type2_step_ledger,
    setup_type2_step_ledger_into_hfss,
)
from tests.backend_em.test_type2_step_import_pipeline import (
    _FakeDesign as _ImportFakeDesign,
    _FakeHfss as _ImportFakeHfss,
    _FakeMeshModule,
    _FakeModeler as _ImportFakeModeler,
    _expected_mesh_length_payload,
    _modeled_entry,
    _non_model_entry,
    _rx_single_coil_entry,
    _single_layer_imported_name_batch,
    _single_layer_imported_name_batch_with_role_aware_underlay,
    _single_layer_modeled_objects,
    _single_layer_modeled_objects_with_role_aware_underlay,
    _source_paths,
    _write_ledger,
)
from tests.fixtures.legacy.type1_spec import TYPE1_OUTPUT_VARIABLES, type1_outputs_spec


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


class _SetupReadyDesign(_ImportFakeDesign):
    def __init__(self, *, mesh_module: _FakeMeshModule, parent: "_SetupReadyHfss") -> None:
        super().__init__(mesh_module=mesh_module)
        self._parent = parent

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


def _role_aware_mesh_entries(*, tx_object_name: str = "tx_copper_l0") -> list[dict[str, object]]:
    return [
        {
            "object_id": "tx_rect_void_coil",
            "role": "tx_single_coil",
            "imported_object_names": [
                "tx_pcb_l0",
                tx_object_name,
                "tx_underlay_ferrite_u0",
                "tx_underlay_pet_psa_u0",
                "tx_underlay_air_u0",
                "tx_wall_ferrite_u0",
                "tx_wall_pet_psa_u0",
                "tx_wall_air_u0",
                "tx_port_sheet",
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


def test_setup_type2_step_ledger_builds_mesh_boundary_ports_analysis_and_validation(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
        radiation_margin_mm=4123.0,
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_single_layer_imported_name_batch()]))

    result = setup_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        design_name="fake_type2_setup_ready",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    assert session.design.import_dataset_calls == []
    assert session.mesh_module.assign_length_op_calls == [_expected_mesh_length_payload()]
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

    imported_payload = _imported_ledger_payload(imported_ledger_path)
    assert "mesh" not in imported_payload
    assert "boundary" not in imported_payload
    assert imported_payload["aedt_path"] == str(output_aedt_path)


def test_setup_type2_step_ledger_assigns_requested_design_variables_before_save(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_single_layer_imported_name_batch()]))

    result = setup_type2_step_ledger(
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
    )

    assert session.design_variables == {
        "modeled_objects_tx_rect_void_coil_outer_x_mm": "157.8mm",
        "modeled_objects_tx_rect_void_coil_margin_ratio": "0.05",
        "modeled_objects_tx_rect_void_coil_turn_count": "2",
    }
    assert result["aedt_path"] == str(output_aedt_path)
    assert session.save_project_calls == [str(output_aedt_path)]


def test_setup_type2_step_ledger_keeps_mesh_conductor_only_when_tx_entry_includes_underlay_bodies(
    tmp_path: Path,
) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects_with_role_aware_underlay(
            tmp_path,
            tx_repeat_count=2,
            tx_wall_repeat_count=1,
            rx_repeat_count=0,
        ),
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(
        modeler=_SetupReadyModeler(
            imported_name_batches=[
                _single_layer_imported_name_batch_with_role_aware_underlay(
                    tx_repeat_count=2,
                    tx_wall_repeat_count=1,
                    rx_repeat_count=0,
                )
            ]
        )
    )

    result = setup_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        design_name="fake_type2_setup_ready",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    assert session.mesh_module.assign_length_op_calls == [_expected_mesh_length_payload()]
    assert result["mesh"]["objects"] == ["tx_copper_l0", "rx_copper_l0"]


def test_setup_type2_step_ledger_into_hfss_auto_detaches_after_setup(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
    )
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_single_layer_imported_name_batch()]))

    result = setup_type2_step_ledger_into_hfss(
        hfss=cast(HfssSession, session),
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
    )

    assert result["aedt_path"] == str(output_aedt_path)
    assert session.insert_design_calls == ["type2_step_import"]
    assert session.desktop_class.release_calls == [(False, False)]


def test_setup_type2_step_ledger_accepts_multilayer_tx_copper_stack_mesh(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
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

    result = setup_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        design_name="fake_type2_setup_ready",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    assert session.mesh_module.assign_length_op_calls == [_expected_mesh_length_payload(tx_object_name="tx_copper_stack")]
    assert result["mesh"]["objects"] == ["tx_copper_stack", "rx_copper_l0"]
    assert result["ports"] == {"tx": ["1_T1"], "rx": ["2_T1"]}


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
            imported_name_batches=[("environment", "tx_region", "rx_region_max", "tx_pcb_l0", "tx_copper_l0")]
        )
    )

    with pytest.raises(ValueError, match=r"requires exactly one modeled entry for each mesh role .*rx_single_coil"):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=imported_ledger_path,
            hfss_factory=lambda _: cast(HfssSession, session),
        )

    assert session.desktop_class.release_calls == [(True, True)]
    assert not imported_ledger_path.exists()


def test_setup_type2_step_ledger_raises_when_port_sheet_vertices_are_malformed(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_objects = _single_layer_modeled_objects(tmp_path)
    terminal_metadata = cast(dict[str, object], modeled_objects[0]["terminal_metadata"])
    terminal_metadata["port_sheet_vertices_xyz"] = [[1.0, 2.0, 3.0]]
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=modeled_objects,
    )
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_single_layer_imported_name_batch()]))

    with pytest.raises(ValueError, match=r"port_sheet_vertices_xyz must contain exactly 4 vertices"):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_setup_type2_step_ledger_raises_when_sheet_edge_resolution_is_not_unique(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
    )
    modeler = _SetupReadyModeler(imported_name_batches=[_single_layer_imported_name_batch()])
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
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
    )
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_single_layer_imported_name_batch()]))
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
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
    )
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_single_layer_imported_name_batch()]))
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
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
    )
    modeler = _SetupReadyModeler(imported_name_batches=[_single_layer_imported_name_batch()])
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
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
    )
    session = _SetupReadyHfss(
        modeler=_SetupReadyModeler(imported_name_batches=[_single_layer_imported_name_batch()])
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
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
    )
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_single_layer_imported_name_batch()]))
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
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
    )
    session = _SetupReadyHfss(modeler=_SetupReadyModeler(imported_name_batches=[_single_layer_imported_name_batch()]))
    session.validate_design_result = False

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: ValidateDesign"):
        setup_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_setup_ready.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, session),
        )

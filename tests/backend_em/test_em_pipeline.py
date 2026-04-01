from __future__ import annotations

import pytest
from typing import cast

from peetsfea.aedt.protocols import HfssSession
from peetsfea.aedt.protocols import ModelerSession

from peetsfea.backend.pyaedt.em_pipeline.steps.analysis import _resolve_port_terms_for_expressions
from peetsfea.backend.pyaedt.em_pipeline.steps.boundary_port import build_boundary
from peetsfea.backend.pyaedt.em_pipeline.steps.boundary_port import build_ports
from peetsfea.backend.pyaedt.em_pipeline import default_em_policy, run_em_pipeline
from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput
from peetsfea.types.manifest import OutputsSpec
from tests.fixtures.type1_spec import TYPE1_OUTPUT_VARIABLES, type1_outputs_spec


class _FakeHfss:
    def __init__(self) -> None:
        self.radiation_assigned_faces: list[int] = []
        self.setup_names: list[str] = []
        self.deleted_setups: list[str] = []
        self.inserted_setup_types: list[str] = []
        self.inserted_setup_payloads: list[list[object]] = []
        self.inserted_sweep_setup_names: list[str] = []
        self.inserted_sweep_payloads: list[list[object]] = []
        self.created_output_variables: list[tuple[str, str, str]] = []
        self.created_reports: list[dict[str, object]] = []
        self.edited_sources_payloads: list[list[object]] = []
        self.available_traces: list[str] = [
            "S(TX_TML,TX_TML)",
            "S(TX_TML,RX_TML)",
            "S(RX_TML,TX_TML)",
            "S(RX_TML,RX_TML)",
        ]
        self._excitation_names: list[str] = ["TX_TML", "RX_TML"]
        self.raise_excitation_names_access = False
        self.radiation_boundary_result = True
        self.output_variable_result = True
        self.traces_raise_categories: set[str] = set()
        self.odesign = self._Design(self)
        self.post = self._Post(self)

    @property
    def excitation_names(self) -> list[str]:
        if self.raise_excitation_names_access:
            raise RuntimeError("excitation names unavailable")
        return self._excitation_names

    @excitation_names.setter
    def excitation_names(self, value: list[str]) -> None:
        self._excitation_names = list(value)

    class _AnalysisModule:
        def __init__(self, parent: "_FakeHfss") -> None:
            self._parent = parent

        def InsertSetup(self, setup_type: str, props: list[object]) -> object:
            self._parent.inserted_setup_types.append(setup_type)
            self._parent.inserted_setup_payloads.append(props)
            if "Setup1" not in self._parent.setup_names:
                self._parent.setup_names.append("Setup1")
            return True

        def InsertFrequencySweep(self, setup_name: str, props: list[object]) -> object:
            self._parent.inserted_sweep_setup_names.append(setup_name)
            self._parent.inserted_sweep_payloads.append(props)
            return True

    class _ReportSetupModule:
        def __init__(self, parent: "_FakeHfss") -> None:
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
            payload = {
                "plot_name": plot_name,
                "report_category": report_category,
                "plot_type": plot_type,
                "setup_sweep_name": setup_sweep_name,
                "context": list(context),
                "variations": list(variations),
                "components": list(components),
            }
            self._parent.created_reports.append(payload)
            return True

        def GetAllReportNames(self) -> list[str]:
            return [str(report["plot_name"]) for report in self._parent.created_reports]

    class _Design:
        def __init__(self, parent: "_FakeHfss") -> None:
            self._parent = parent

        class _SolutionsModule:
            def __init__(self, parent: "_FakeHfss") -> None:
                self._parent = parent

            def EditSources(self, payload: list[object]) -> object:
                self._parent.edited_sources_payloads.append(payload)
                return True

        def GetModule(self, name: str) -> object:
            if name == "AnalysisSetup":
                return _FakeHfss._AnalysisModule(self._parent)
            if name == "ReportSetup":
                return _FakeHfss._ReportSetupModule(self._parent)
            if name == "Solutions":
                return _FakeHfss._Design._SolutionsModule(self._parent)
            raise ValueError(f"unexpected module: {name}")

        def ValidateDesign(self) -> int:
            return 1

    class _Post:
        def __init__(self, parent: "_FakeHfss") -> None:
            self._parent = parent

    def assign_radiation_boundary_to_faces(self, assignment: object, name: str) -> bool:
        _ = name
        if isinstance(assignment, list):
            if not assignment:
                raise ValueError("assignment list must not be empty")
            normalized = assignment[0]
        else:
            normalized = assignment
        face_id = int(normalized)
        self.radiation_assigned_faces.append(face_id)
        return self.radiation_boundary_result

    def delete_setup(self, name: str) -> bool:
        self.deleted_setups.append(name)
        self.setup_names = [setup for setup in self.setup_names if setup != name]
        return True

    def create_output_variable(
        self,
        variable: str,
        expression: str,
        solution: str,
    ) -> bool:
        self.created_output_variables.append((variable, expression, solution))
        return self.output_variable_result

    def get_traces_for_plot(
        self,
        get_self_terms: bool,
        get_mutual_terms: bool,
        first_element_filter: str,
        second_element_filter: str,
        category: str,
        differential_pairs: list[object],
    ) -> list[str]:
        if category in self.traces_raise_categories:
            raise RuntimeError(f"unsupported trace category: {category}")
        _ = (
            get_self_terms,
            get_mutual_terms,
            first_element_filter,
            second_element_filter,
            category,
            differential_pairs,
        )
        return list(self.available_traces)


class _FakeModeler:
    def __init__(self) -> None:
        self.created_region_name: str = ""
        self.created_region_pad_value: float = 0.0
        self.created_region_pad_type: str = ""
        self.create_region_returns_false = False
        self.get_object_faces_returns_false = False

    class _Region:
        def __init__(self, name: str) -> None:
            self.name = name

    def create_region(self, pad_value: int, pad_type: str, name: str) -> "_FakeModeler._Region":
        self.created_region_pad_value = float(pad_value)
        self.created_region_pad_type = pad_type
        self.created_region_name = name
        if self.create_region_returns_false:
            return cast("_FakeModeler._Region", False)
        return _FakeModeler._Region(name)

    def get_object_faces(self, assignment: str) -> list[int]:
        if self.get_object_faces_returns_false:
            return cast(list[int], False)
        if assignment != self.created_region_name:
            return []
        return [10, 11, 12, 13, 14, 15]


def _input() -> EmPipelineInput:
    return {
        "ready_objects": {
            "tx_conductors": ["tx_a"],
            "rx_conductors": ["rx_a"],
            "ferrite_objects": [],
            "fr4_objects": ["fr4_a"],
            "scene_bbox_source_objects": ["scene_a"],
        },
        "endpoints": {
            "tx": [
                {
                    "group_kind": "tx_dd",
                    "group_instance_index": 0,
                    "board_id": "tx_main_0",
                    "start_xyz": (0.0, 0.0, 0.0),
                    "end_xyz": (1.0, 0.0, 0.0),
                    "start_label": "D",
                    "end_label": "d",
                    "present": True,
                }
            ],
            "rx": [
                {
                    "group_kind": "rx_dd",
                    "group_instance_index": 0,
                    "board_id": "rx_main_0",
                    "start_xyz": (0.0, 0.0, 0.0),
                    "end_xyz": (1.0, 0.0, 0.0),
                    "start_label": "A",
                    "end_label": "d",
                    "present": True,
                },
                {
                    "group_kind": "rx_dd",
                    "group_instance_index": 1,
                    "board_id": "rx_main_1",
                    "start_xyz": (0.0, -1.0, 0.0),
                    "end_xyz": (1.0, -1.0, 0.0),
                    "start_label": "B",
                    "end_label": "c",
                    "present": True,
                }
            ],
        },
        "context": {
            "dd_mirror_plane": "XZ",
            "rx_plane": "YZ",
            "tx_vertical_plane": "ZX",
            "source": "type1_geometry",
            "object_names": ["tx_a", "rx_a", "fr4_a"],
        },
        "ports": {"tx": ["TX_TML"], "rx": ["RX_TML"]},
    }


def _outputs() -> OutputsSpec:
    return cast(OutputsSpec, type1_outputs_spec())


def test_run_em_pipeline_returns_full_contract() -> None:
    fake_hfss = _FakeHfss()
    fake_modeler = _FakeModeler()
    result = run_em_pipeline(cast(HfssSession, fake_hfss), cast(ModelerSession, fake_modeler), _input(), default_em_policy(), _outputs())
    assert set(result.keys()) == {
        "groups",
        "series",
        "subtract",
        "boundary",
        "ports",
        "sources",
        "analysis",
        "post_templates",
        "validation_report",
    }
    assert result["validation_report"]["ok"] is True
    assert fake_modeler.created_region_pad_type == "Absolute Offset"
    assert fake_modeler.created_region_pad_value == 3500.0
    assert sorted(fake_hfss.radiation_assigned_faces) == [10, 11, 12, 13, 14, 15]
    assert result["boundary"]["offset_type"] == "Absolute Offset"
    assert result["boundary"]["offset_value"] == "3500.0"
    assert result["sources"]["tx_magnitude"] == "288V"
    assert result["sources"]["rx_magnitude"] == "0V"
    assert result["sources"]["rx_phase_deg"] == "0deg"
    assert result["sources"]["tx_phase_deg"] == "0deg"
    assert fake_hfss.edited_sources_payloads
    assert fake_hfss.inserted_setup_types == ["HfssDriven"]
    assert fake_hfss.inserted_sweep_setup_names == []
    expected_output_names = [name for name, _ in TYPE1_OUTPUT_VARIABLES]
    assert [name for name, _, _ in fake_hfss.created_output_variables] == expected_output_names
    expressions_by_name = {name: expr for name, expr, _ in fake_hfss.created_output_variables}
    assert "Zt(" in expressions_by_name["Ltx_uH"]
    assert "freq" in expressions_by_name["Ltx_uH"]
    assert "Zt(" in expressions_by_name["Lrx_uH"]
    assert "freq" in expressions_by_name["Lrx_uH"]
    assert "Zt(" in expressions_by_name["M_uH"]
    assert "freq" in expressions_by_name["M_uH"]
    assert "M_uH" in expressions_by_name["k_ratio"]
    assert "Ltx_uH" in expressions_by_name["k_ratio"]
    assert "Lrx_uH" in expressions_by_name["k_ratio"]
    assert "im(Zt(" in expressions_by_name["Qtx_ratio"]
    assert "re(Zt(" in expressions_by_name["Qtx_ratio"]
    assert "im(Zt(" in expressions_by_name["Qrx_ratio"]
    assert "re(Zt(" in expressions_by_name["Qrx_ratio"]
    assert "k_ratio" in expressions_by_name["FOM_ratio"]
    assert "Qtx_ratio" in expressions_by_name["FOM_ratio"]
    assert "Qrx_ratio" in expressions_by_name["FOM_ratio"]
    assert "re(Zt(" in expressions_by_name["Rtx_ac_ohm"]
    assert "re(Zt(" in expressions_by_name["Rrx_ac_ohm"]
    assert "im(Zt(" in expressions_by_name["Xtx_ohm"]
    assert "im(Zt(" in expressions_by_name["Xrx_ohm"]
    assert "M_uH/Ltx_uH" in expressions_by_name["M_over_Ltx_ratio"]
    assert "M_uH/Lrx_uH" in expressions_by_name["M_over_Lrx_ratio"]
    assert "re(Yt(" in expressions_by_name["Gtx_S"]
    assert "im(Yt(" in expressions_by_name["Btx_S"]
    assert "re(Yt(" in expressions_by_name["Grx_S"]
    assert "im(Yt(" in expressions_by_name["Brx_S"]
    assert "mag(S(" in expressions_by_name["S11_mag_ratio"]
    assert "mag(S(" in expressions_by_name["S21_mag_ratio"]
    assert "ang_deg_val(S(" in expressions_by_name["S21_phase_deg"]
    assert "mag(S(" in expressions_by_name["S22_mag_ratio"]
    assert expressions_by_name["eta_s21_power_ratio"] == "S21_mag_ratio*S21_mag_ratio"
    assert expressions_by_name["eta_tx_accept_ratio"] == "1-S11_mag_ratio*S11_mag_ratio"
    assert expressions_by_name["eta_rx_accept_ratio"] == "1-S22_mag_ratio*S22_mag_ratio"
    assert expressions_by_name["eta_match_product_ratio"] == "eta_tx_accept_ratio*eta_rx_accept_ratio"
    assert expressions_by_name["eta_s21_from_tx_accept_ratio"] == "eta_s21_power_ratio/eta_tx_accept_ratio"
    assert expressions_by_name["eta_s21_from_rx_accept_ratio"] == "eta_s21_power_ratio/eta_rx_accept_ratio"
    assert (
        expressions_by_name["eta_s21_two_sided_norm_ratio"]
        == "eta_s21_power_ratio/(eta_tx_accept_ratio*eta_rx_accept_ratio)"
    )
    assert (
        expressions_by_name["eta_fom_max_ratio"]
        == "(FOM_ratio*FOM_ratio)/((1+sqrt(1+FOM_ratio*FOM_ratio))*(1+sqrt(1+FOM_ratio*FOM_ratio)))"
    )
    assert fake_hfss.created_reports[0]["plot_name"] == "Output Variables Table1"
    assert fake_hfss.created_reports[0]["report_category"] == "Terminal Solution Data"
    assert fake_hfss.created_reports[0]["plot_type"] == "Data Table"
    assert fake_hfss.created_reports[0]["context"] == []
    assert fake_hfss.created_reports[0]["variations"] == ["Freq:=", ["All"]]
    assert result["analysis"]["sweep_name"] == "disabled"
    assert result["post_templates"] == [
        {
            "template_id": "output_variables_table_1",
            "report_name": "Output Variables Table1",
            "solution_name": "Setup1 : LastAdaptive",
            "traces": expected_output_names,
            "output_variables": expected_output_names,
        }
    ]


def test_run_em_pipeline_hard_fail_validation() -> None:
    data = _input()
    data["ready_objects"]["rx_conductors"] = []
    with pytest.raises(ValueError, match="validation failed"):
        run_em_pipeline(cast(HfssSession, _FakeHfss()), cast(ModelerSession, _FakeModeler()), data, default_em_policy(), _outputs())


def test_build_boundary_raises_when_create_region_returns_false() -> None:
    fake_hfss = _FakeHfss()
    fake_modeler = _FakeModeler()
    fake_modeler.create_region_returns_false = True

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: create_region"):
        build_boundary(cast(HfssSession, fake_hfss), cast(ModelerSession, fake_modeler), default_em_policy())


def test_build_boundary_raises_when_radiation_assignment_returns_false() -> None:
    fake_hfss = _FakeHfss()
    fake_hfss.radiation_boundary_result = False
    fake_modeler = _FakeModeler()

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: assign_radiation_boundary_to_faces"):
        build_boundary(cast(HfssSession, fake_hfss), cast(ModelerSession, fake_modeler), default_em_policy())


def test_build_boundary_raises_when_get_object_faces_returns_false() -> None:
    fake_hfss = _FakeHfss()
    fake_modeler = _FakeModeler()
    fake_modeler.get_object_faces_returns_false = True

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: get_object_faces"):
        build_boundary(cast(HfssSession, fake_hfss), cast(ModelerSession, fake_modeler), default_em_policy())


def test_run_em_pipeline_raises_when_output_variable_creation_returns_false() -> None:
    fake_hfss = _FakeHfss()
    fake_hfss.output_variable_result = False

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: create_output_variable"):
        run_em_pipeline(cast(HfssSession, fake_hfss), cast(ModelerSession, _FakeModeler()), _input(), default_em_policy(), _outputs())


def test_run_em_pipeline_keeps_explicit_ports_even_when_traces_use_numeric_names() -> None:
    fake_hfss = _FakeHfss()
    fake_hfss.available_traces = ["S(1,1)", "S(1,2)", "S(2,1)", "S(2,2)"]
    run_em_pipeline(cast(HfssSession, fake_hfss), cast(ModelerSession, _FakeModeler()), _input(), default_em_policy(), _outputs())
    expressions_by_name = {name: expr for name, expr, _ in fake_hfss.created_output_variables}
    assert "Zt(TX_TML,TX_TML)" in expressions_by_name["Ltx_uH"]
    assert "Zt(RX_TML,RX_TML)" in expressions_by_name["Lrx_uH"]
    assert "Yt(TX_TML,TX_TML)" in expressions_by_name["Gtx_S"]
    assert "Yt(RX_TML,RX_TML)" in expressions_by_name["Grx_S"]
    assert "S(TX_TML,TX_TML)" in expressions_by_name["S11_mag_ratio"]
    assert "S(TX_TML,RX_TML)" in expressions_by_name["S21_mag_ratio"]
    assert "S(TX_TML,RX_TML)" in expressions_by_name["S21_phase_deg"]
    assert "S(RX_TML,RX_TML)" in expressions_by_name["S22_mag_ratio"]


def test_resolve_port_terms_for_expressions_raises_when_trace_probing_fails() -> None:
    fake_hfss = _FakeHfss()
    fake_hfss.traces_raise_categories = {"S(", "St("}
    with pytest.raises(RuntimeError, match=r"unsupported trace category: S\("):
        _resolve_port_terms_for_expressions(
            cast(HfssSession, fake_hfss),
            {"tx": ["TX_TML"], "rx": ["RX_TML"]},
        )


def test_run_em_pipeline_supports_terminal_style_st_traces_with_long_names() -> None:
    fake_hfss = _FakeHfss()
    tx_term = "rxs_rx_main_0_0_B_T1"
    rx_term = "txs_tx_main_0_0_T1"
    fake_hfss.excitation_names = [tx_term, rx_term]
    fake_hfss.available_traces = [
        f"St({tx_term},{tx_term})",
        f"St({tx_term},{rx_term})",
        f"St({rx_term},{tx_term})",
        f"St({rx_term},{rx_term})",
    ]
    data = _input()
    data["ports"] = {"tx": [tx_term], "rx": [rx_term]}
    run_em_pipeline(cast(HfssSession, fake_hfss), cast(ModelerSession, _FakeModeler()), data, default_em_policy(), _outputs())
    expressions_by_name = {name: expr for name, expr, _ in fake_hfss.created_output_variables}
    assert f"Zt({tx_term},{tx_term})" in expressions_by_name["Ltx_uH"]
    assert f"Zt({rx_term},{rx_term})" in expressions_by_name["Lrx_uH"]
    assert f"Yt({tx_term},{tx_term})" in expressions_by_name["Gtx_S"]
    assert f"Yt({rx_term},{rx_term})" in expressions_by_name["Grx_S"]
    assert f"St({tx_term},{tx_term})" in expressions_by_name["S11_mag_ratio"]
    assert f"St({tx_term},{rx_term})" in expressions_by_name["S21_mag_ratio"]
    assert f"St({tx_term},{rx_term})" in expressions_by_name["S21_phase_deg"]
    assert f"St({rx_term},{rx_term})" in expressions_by_name["S22_mag_ratio"]


def test_run_em_pipeline_prefers_stub_excitation_names_for_post_variables() -> None:
    fake_hfss = _FakeHfss()
    tx_name = "txs_tx_main_1_1_T1"
    rx_name = "rxs_rx_main_1_1_c_T1"
    fake_hfss.excitation_names = [tx_name, "rxs_rx_main_0_0_A_T1", rx_name]
    data = _input()
    data["ports"] = {"tx": [tx_name], "rx": [rx_name]}
    run_em_pipeline(cast(HfssSession, fake_hfss), cast(ModelerSession, _FakeModeler()), data, default_em_policy(), _outputs())
    expressions_by_name = {name: expr for name, expr, _ in fake_hfss.created_output_variables}
    assert f"Zt({tx_name},{tx_name})" in expressions_by_name["Ltx_uH"]
    assert f"Zt({rx_name},{rx_name})" in expressions_by_name["Lrx_uH"]
    assert f"Zt({tx_name},{rx_name})" in expressions_by_name["M_uH"]


def test_run_em_pipeline_normalizes_parenthesized_terminal_names() -> None:
    fake_hfss = _FakeHfss()
    tx_term = "rxs_rx_main_0_0_B_T1"
    rx_term = "txs_tx_main_0_0_T1"
    fake_hfss.excitation_names = [f"({tx_term})", f"({rx_term})"]
    fake_hfss.available_traces = [
        f"St({tx_term},{tx_term})",
        f"St({tx_term},{rx_term})",
    ]
    data = _input()
    data["ports"] = {"tx": [tx_term], "rx": [rx_term]}
    run_em_pipeline(cast(HfssSession, fake_hfss), cast(ModelerSession, _FakeModeler()), data, default_em_policy(), _outputs())
    expressions_by_name = {name: expr for name, expr, _ in fake_hfss.created_output_variables}
    assert f"Zt(({tx_term}),({tx_term}))" in expressions_by_name["Ltx_uH"]


def test_build_ports_returns_endpoint_based_default_port_names() -> None:
    ports = build_ports(cast(HfssSession, _FakeHfss()), cast(ModelerSession, _FakeModeler()), _input())
    assert ports == {"tx": ["TX_TML"], "rx": ["RX_TML"]}


def test_build_ports_prefers_geometry_captured_excitation_names() -> None:
    data = _input()
    data["ports"] = {"tx": ["1_T1"], "rx": ["2_T1"]}
    ports = build_ports(cast(HfssSession, _FakeHfss()), cast(ModelerSession, _FakeModeler()), data)
    assert ports == {"tx": ["1_T1"], "rx": ["2_T1"]}


def test_run_em_pipeline_prefers_geometry_captured_excitation_names_for_post_variables() -> None:
    fake_hfss = _FakeHfss()
    fake_hfss.excitation_names = ["1_T1", "2_T1"]
    data = _input()
    data["ports"] = {"tx": ["1_T1"], "rx": ["2_T1"]}
    run_em_pipeline(cast(HfssSession, fake_hfss), cast(ModelerSession, _FakeModeler()), data, default_em_policy(), _outputs())
    expressions_by_name = {name: expr for name, expr, _ in fake_hfss.created_output_variables}
    assert "Zt(1_T1,1_T1)" in expressions_by_name["Ltx_uH"]
    assert "Zt(2_T1,2_T1)" in expressions_by_name["Lrx_uH"]
    assert "Zt(1_T1,2_T1)" in expressions_by_name["M_uH"]


def test_run_em_pipeline_prefers_canonical_rx_stub_for_parenthesized_excitation_names() -> None:
    fake_hfss = _FakeHfss()
    tx_name = "txs_tx_main_1_1_T1"
    rx_name = "rxs_rx_main_1_1_c_T1"
    fake_hfss.excitation_names = [tx_name, "(rxs_rx_main_0_0_A_T1)", f"({rx_name})"]
    data = _input()
    data["ports"] = {"tx": [tx_name], "rx": [rx_name]}
    run_em_pipeline(cast(HfssSession, fake_hfss), cast(ModelerSession, _FakeModeler()), data, default_em_policy(), _outputs())
    expressions_by_name = {name: expr for name, expr, _ in fake_hfss.created_output_variables}
    assert f"Zt(({rx_name}),({rx_name}))" in expressions_by_name["Lrx_uH"]


def test_run_em_pipeline_uses_policy_frequencies_for_setup_and_disabled_sweep_metadata() -> None:
    fake_hfss = _FakeHfss()
    policy = default_em_policy()
    policy["setup_frequency_hz"] = 13.56e6
    policy["sweep_start_hz"] = 2.5e6
    policy["sweep_stop_hz"] = 60.0e6

    result = run_em_pipeline(cast(HfssSession, fake_hfss), cast(ModelerSession, _FakeModeler()), _input(), policy, _outputs())

    setup_payload = fake_hfss.inserted_setup_payloads[0]
    assert "13.56MHz" in setup_payload
    assert fake_hfss.inserted_sweep_payloads == []
    assert result["analysis"]["setup_frequency_hz"] == 13.56e6
    assert result["analysis"]["sweep_name"] == "disabled"
    assert result["analysis"]["sweep_start_hz"] == 2.5e6
    assert result["analysis"]["sweep_stop_hz"] == 60.0e6


def test_default_em_policy_exposes_0214_adaptive_defaults_and_setup_payload() -> None:
    fake_hfss = _FakeHfss()
    policy = default_em_policy()

    assert policy["max_delta_s"] == 0.007
    assert policy["maximum_passes"] == 10
    assert policy["minimum_converged_passes"] == 10
    assert policy["percent_refinement"] == 22

    run_em_pipeline(cast(HfssSession, fake_hfss), cast(ModelerSession, _FakeModeler()), _input(), policy, _outputs())
    setup_payload = fake_hfss.inserted_setup_payloads[0]

    assert 0.007 in setup_payload
    assert 10 in setup_payload
    assert 8 in setup_payload
    assert 10 in setup_payload
    assert 22 in setup_payload
    assert "UseMaxTetIncrease:=" in setup_payload
    assert True in setup_payload
    assert "MaxTetIncrease:=" in setup_payload
    assert 700_000 in setup_payload


def test_run_em_pipeline_uses_adaptive_policy_keys_only_for_exposed_numbers() -> None:
    fake_hfss = _FakeHfss()
    policy = default_em_policy()
    policy["max_delta_s"] = 0.005
    policy["maximum_passes"] = 22
    policy["minimum_passes"] = 5
    policy["minimum_converged_passes"] = 4
    policy["percent_refinement"] = 47
    policy["basis_order"] = 2
    policy["port_accuracy"] = 3

    run_em_pipeline(cast(HfssSession, fake_hfss), cast(ModelerSession, _FakeModeler()), _input(), policy, _outputs())
    setup_payload = fake_hfss.inserted_setup_payloads[0]

    assert 0.005 in setup_payload
    assert 22 in setup_payload
    assert 5 in setup_payload
    assert 4 in setup_payload
    assert 47 in setup_payload
    assert 2 in setup_payload
    assert 3 in setup_payload


def test_run_em_pipeline_raises_when_explicit_rx_port_is_missing_from_excitation_names() -> None:
    fake_hfss = _FakeHfss()
    fake_hfss.excitation_names = [
        "TX_TML",
        "rxs_rx_main_0_0_A_T1",
        "rxs_rx_main_1_1_c_T1",
    ]
    with pytest.raises(ValueError, match="rx source name is not available"):
        run_em_pipeline(cast(HfssSession, fake_hfss), cast(ModelerSession, _FakeModeler()), _input(), default_em_policy(), _outputs())

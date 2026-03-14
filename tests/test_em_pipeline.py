from __future__ import annotations

import pytest
from typing import cast

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.backend.pyaedt.em_pipeline.boundary_port import build_ports
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
        self.created_output_variables: list[tuple[str, str, str | None]] = []
        self.created_reports: list[dict[str, object]] = []
        self.edited_sources_payloads: list[list[object]] = []
        self.available_traces: list[str] = [
            "S(TX_TML,TX_TML)",
            "S(TX_TML,RX_TML)",
            "S(RX_TML,TX_TML)",
            "S(RX_TML,RX_TML)",
        ]
        self.excitation_names: list[str] = []
        self.odesign = self._Design(self)
        self.post = self._Post(self)

    class _AnalysisModule:
        def __init__(self, parent: "_FakeHfss") -> None:
            self._parent = parent

        def InsertSetup(self, setup_type: str, props: list[object]) -> None:
            self._parent.inserted_setup_types.append(setup_type)
            self._parent.inserted_setup_payloads.append(props)
            if "Setup1" not in self._parent.setup_names:
                self._parent.setup_names.append("Setup1")

        def InsertFrequencySweep(self, setup_name: str, props: list[object]) -> None:
            self._parent.inserted_sweep_setup_names.append(setup_name)
            self._parent.inserted_sweep_payloads.append(props)

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
            options: list[object] | None = None,
        ) -> None:
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

        def GetAllReportNames(self) -> list[str]:
            return [str(report["plot_name"]) for report in self._parent.created_reports]

    class _Design:
        def __init__(self, parent: "_FakeHfss") -> None:
            self._parent = parent

        class _SolutionsModule:
            def __init__(self, parent: "_FakeHfss") -> None:
                self._parent = parent

            def EditSources(self, payload: list[object]) -> None:
                self._parent.edited_sources_payloads.append(payload)

        def GetModule(self, name: str) -> object:
            if name == "AnalysisSetup":
                return _FakeHfss._AnalysisModule(self._parent)
            if name == "ReportSetup":
                return _FakeHfss._ReportSetupModule(self._parent)
            if name == "Solutions":
                return _FakeHfss._Design._SolutionsModule(self._parent)
            raise ValueError(f"unexpected module: {name}")

    class _Post:
        def __init__(self, parent: "_FakeHfss") -> None:
            self._parent = parent

    def assign_radiation_boundary_to_faces(self, assignment: object, name: str | None = None) -> bool:
        _ = name
        if isinstance(assignment, list):
            normalized = assignment[0] if assignment else -1
        else:
            normalized = assignment
        if isinstance(normalized, bool):
            face_id = int(normalized)
        elif isinstance(normalized, (int, float, str)):
            face_id = int(normalized)
        else:
            face_id = -1
        self.radiation_assigned_faces.append(face_id)
        return True

    def delete_setup(self, name: str) -> bool:
        self.deleted_setups.append(name)
        self.setup_names = [setup for setup in self.setup_names if setup != name]
        return True

    def create_output_variable(
        self,
        variable: str,
        expression: str,
        solution: str | None = None,
    ) -> bool:
        self.created_output_variables.append((variable, expression, solution))
        return True

    def get_traces_for_plot(
        self,
        get_self_terms: bool = True,
        get_mutual_terms: bool = True,
        first_element_filter: str | None = None,
        second_element_filter: str | None = None,
        category: str = "dB(S",
        differential_pairs: list[object] | None = None,
    ) -> list[str]:
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
        self.created_region_name: str | None = None
        self.created_region_pad_value: float | None = None
        self.created_region_pad_type: str | None = None

    class _Region:
        def __init__(self, name: str) -> None:
            self.name = name

    def create_region(self, pad_value: int, pad_type: str, name: str) -> "_FakeModeler._Region":
        self.created_region_pad_value = float(pad_value)
        self.created_region_pad_type = pad_type
        self.created_region_name = name
        return _FakeModeler._Region(name)

    def get_object_faces(self, assignment: str) -> list[int]:
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
                    "start_label": "A",
                    "end_label": "a",
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
    }


def _outputs() -> OutputsSpec:
    return cast(OutputsSpec, type1_outputs_spec())


def test_run_em_pipeline_returns_full_contract() -> None:
    fake_hfss = _FakeHfss()
    fake_modeler = _FakeModeler()
    result = run_em_pipeline(cast(Hfss, fake_hfss), cast(Modeler3D, fake_modeler), _input(), default_em_policy(), _outputs())
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
    assert result["sources"]["rx_phase_deg"] == "90deg"
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
        run_em_pipeline(cast(Hfss, _FakeHfss()), cast(Modeler3D, _FakeModeler()), data, default_em_policy(), _outputs())


def test_run_em_pipeline_uses_numeric_ports_when_named_ports_are_unavailable() -> None:
    fake_hfss = _FakeHfss()
    fake_hfss.available_traces = ["S(1,1)", "S(1,2)", "S(2,1)", "S(2,2)"]
    run_em_pipeline(cast(Hfss, fake_hfss), cast(Modeler3D, _FakeModeler()), _input(), default_em_policy(), _outputs())
    expressions_by_name = {name: expr for name, expr, _ in fake_hfss.created_output_variables}
    assert "Zt(1,1)" in expressions_by_name["Ltx_uH"]
    assert "Zt(2,2)" in expressions_by_name["Lrx_uH"]
    assert "Yt(1,1)" in expressions_by_name["Gtx_S"]
    assert "Yt(2,2)" in expressions_by_name["Grx_S"]
    assert "S(1,1)" in expressions_by_name["S11_mag_ratio"]
    assert "S(1,2)" in expressions_by_name["S21_mag_ratio"]
    assert "S(1,2)" in expressions_by_name["S21_phase_deg"]
    assert "S(2,2)" in expressions_by_name["S22_mag_ratio"]


def test_run_em_pipeline_supports_terminal_style_st_traces_with_long_names() -> None:
    fake_hfss = _FakeHfss()
    tx_term = "rxs_rx_main_0_0_B_T1"
    rx_term = "txs_tx_main_0_0_T1"
    fake_hfss.available_traces = [
        f"St({tx_term},{tx_term})",
        f"St({tx_term},{rx_term})",
        f"St({rx_term},{tx_term})",
        f"St({rx_term},{rx_term})",
    ]
    run_em_pipeline(cast(Hfss, fake_hfss), cast(Modeler3D, _FakeModeler()), _input(), default_em_policy(), _outputs())
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
    fake_hfss.excitation_names = [
        "txs_tx_main_1_1_T1",
        "rxs_rx_main_1_1_A_T1",
    ]
    run_em_pipeline(cast(Hfss, fake_hfss), cast(Modeler3D, _FakeModeler()), _input(), default_em_policy(), _outputs())
    expressions_by_name = {name: expr for name, expr, _ in fake_hfss.created_output_variables}
    assert "Zt(txs_tx_main_1_1_T1,txs_tx_main_1_1_T1)" in expressions_by_name["Ltx_uH"]
    assert "Zt(rxs_rx_main_1_1_A_T1,rxs_rx_main_1_1_A_T1)" in expressions_by_name["Lrx_uH"]
    assert "Zt(txs_tx_main_1_1_T1,rxs_rx_main_1_1_A_T1)" in expressions_by_name["M_uH"]


def test_run_em_pipeline_normalizes_parenthesized_terminal_names() -> None:
    fake_hfss = _FakeHfss()
    fake_hfss.available_traces = [
        "St((rxs_rx_main_0_0_B_T1,(rxs_rx_main_0_0_B_T1))",
        "St((rxs_rx_main_0_0_B_T1,(txs_tx_main_0_0_T1))",
    ]
    run_em_pipeline(cast(Hfss, fake_hfss), cast(Modeler3D, _FakeModeler()), _input(), default_em_policy(), _outputs())
    expressions_by_name = {name: expr for name, expr, _ in fake_hfss.created_output_variables}
    assert "Zt(rxs_rx_main_0_0_B_T1,rxs_rx_main_0_0_B_T1)" in expressions_by_name["Ltx_uH"]


def test_build_ports_returns_endpoint_based_default_port_names() -> None:
    ports = build_ports(cast(Hfss, _FakeHfss()), cast(Modeler3D, _FakeModeler()), _input())
    assert ports == {"tx": ["TX_TML"], "rx": ["RX_TML"]}


def test_run_em_pipeline_uses_policy_frequencies_for_setup_and_disabled_sweep_metadata() -> None:
    fake_hfss = _FakeHfss()
    policy = default_em_policy()
    policy["setup_frequency_hz"] = 13.56e6
    policy["sweep_start_hz"] = 2.5e6
    policy["sweep_stop_hz"] = 60.0e6

    result = run_em_pipeline(cast(Hfss, fake_hfss), cast(Modeler3D, _FakeModeler()), _input(), policy, _outputs())

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
    assert policy["maximum_passes"] == 13
    assert policy["minimum_converged_passes"] == 10
    assert policy["percent_refinement"] == 20

    run_em_pipeline(cast(Hfss, fake_hfss), cast(Modeler3D, _FakeModeler()), _input(), policy, _outputs())
    setup_payload = fake_hfss.inserted_setup_payloads[0]

    assert 0.007 in setup_payload
    assert 13 in setup_payload
    assert 10 in setup_payload
    assert 20 in setup_payload
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

    run_em_pipeline(cast(Hfss, fake_hfss), cast(Modeler3D, _FakeModeler()), _input(), policy, _outputs())
    setup_payload = fake_hfss.inserted_setup_payloads[0]

    assert 0.005 in setup_payload
    assert 22 in setup_payload
    assert 5 in setup_payload
    assert 4 in setup_payload
    assert 47 in setup_payload
    assert 2 in setup_payload
    assert 3 in setup_payload


def test_run_em_pipeline_falls_back_to_stub_rxdd_source_name_for_90deg_phase() -> None:
    fake_hfss = _FakeHfss()
    fake_hfss.excitation_names = [
        "TX_TML",
        "rxs_rx_main_1_1_A_T1",
    ]
    run_em_pipeline(cast(Hfss, fake_hfss), cast(Modeler3D, _FakeModeler()), _input(), default_em_policy(), _outputs())
    assert fake_hfss.edited_sources_payloads
    sources_payload = fake_hfss.edited_sources_payloads[0]
    payload_text = str(sources_payload)
    assert "rxs_rx_main_1_1_A_T1" in payload_text
    assert "90deg" in payload_text

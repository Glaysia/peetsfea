from __future__ import annotations

import pytest
from typing import cast

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.backend.pyaedt.em_pipeline.boundary_port import build_ports
from peetsfea.backend.pyaedt.em_pipeline import default_em_policy, run_em_pipeline
from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput


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
        self.available_traces: list[str] = [
            "S(TX_TML,TX_TML)",
            "S(TX_TML,RX_TML)",
            "S(RX_TML,TX_TML)",
            "S(RX_TML,RX_TML)",
        ]
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

        def GetModule(self, name: str) -> object:
            if name == "AnalysisSetup":
                return _FakeHfss._AnalysisModule(self._parent)
            if name == "ReportSetup":
                return _FakeHfss._ReportSetupModule(self._parent)
            raise ValueError(f"unexpected module: {name}")

    class _Post:
        def __init__(self, parent: "_FakeHfss") -> None:
            self._parent = parent

    def assign_radiation_boundary_to_faces(self, assignment: int, name: str | None = None) -> bool:
        _ = name
        self.radiation_assigned_faces.append(assignment)
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

    class _Region:
        def __init__(self, name: str) -> None:
            self.name = name

    def create_region(self, pad_value: int, pad_type: str, name: str) -> "_FakeModeler._Region":
        _ = (pad_value, pad_type)
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


def test_run_em_pipeline_returns_full_contract() -> None:
    fake_hfss = _FakeHfss()
    fake_modeler = _FakeModeler()
    result = run_em_pipeline(cast(Hfss, fake_hfss), cast(Modeler3D, fake_modeler), _input(), default_em_policy())
    assert set(result.keys()) == {
        "groups",
        "series",
        "subtract",
        "boundary",
        "ports",
        "analysis",
        "post_templates",
        "validation_report",
    }
    assert result["validation_report"]["ok"] is True
    assert sorted(fake_hfss.radiation_assigned_faces) == [10, 11, 12, 13, 14, 15]
    assert fake_hfss.inserted_setup_types == ["HfssDriven"]
    assert fake_hfss.inserted_sweep_setup_names == ["Setup1"]
    assert [name for name, _, _ in fake_hfss.created_output_variables] == [
        "Ltx",
        "Lrx",
        "M",
        "k",
        "Qtx",
        "Qrx",
        "FOM",
        "S11_mag",
        "S21_mag",
        "Z11_re",
        "Z11_im",
        "Z12_re",
        "Z12_im",
        "Z21_re",
        "Z21_im",
        "Z22_re",
        "Z22_im",
        "ImZtx",
        "ImZrx",
    ]
    expressions_by_name = {name: expr for name, expr, _ in fake_hfss.created_output_variables}
    assert "Z(" in expressions_by_name["Ltx"]
    assert "Freq" in expressions_by_name["Ltx"]
    assert fake_hfss.created_reports[0]["plot_name"] == "Output Variables Table 1"
    assert fake_hfss.created_reports[0]["plot_type"] == "Data Table"
    assert fake_hfss.created_reports[0]["context"] == ["Domain:=", "Sweep"]
    assert fake_hfss.created_reports[0]["variations"] == ["Freq:=", ["6.78MHz"]]
    assert result["post_templates"] == [
        {
            "template_id": "output_variables_table_1",
            "report_name": "Output Variables Table 1",
            "solution_name": "Setup1 : Sweep",
            "traces": [
                "Ltx",
                "Lrx",
                "M",
                "k",
                "Qtx",
                "Qrx",
                "FOM",
                "S11_mag",
                "S21_mag",
                "Z11_re",
                "Z11_im",
                "Z12_re",
                "Z12_im",
                "Z21_re",
                "Z21_im",
                "Z22_re",
                "Z22_im",
                "ImZtx",
                "ImZrx",
            ],
            "output_variables": [
                "Ltx",
                "Lrx",
                "M",
                "k",
                "Qtx",
                "Qrx",
                "FOM",
                "S11_mag",
                "S21_mag",
                "Z11_re",
                "Z11_im",
                "Z12_re",
                "Z12_im",
                "Z21_re",
                "Z21_im",
                "Z22_re",
                "Z22_im",
                "ImZtx",
                "ImZrx",
            ],
        }
    ]


def test_run_em_pipeline_hard_fail_validation() -> None:
    data = _input()
    data["ready_objects"]["rx_conductors"] = []
    with pytest.raises(ValueError, match="validation failed"):
        run_em_pipeline(cast(Hfss, _FakeHfss()), cast(Modeler3D, _FakeModeler()), data, default_em_policy())


def test_run_em_pipeline_uses_numeric_ports_when_named_ports_are_unavailable() -> None:
    fake_hfss = _FakeHfss()
    fake_hfss.available_traces = ["S(1,1)", "S(1,2)", "S(2,1)", "S(2,2)"]
    run_em_pipeline(cast(Hfss, fake_hfss), cast(Modeler3D, _FakeModeler()), _input(), default_em_policy())
    expressions_by_name = {name: expr for name, expr, _ in fake_hfss.created_output_variables}
    assert "Z(1,1)" in expressions_by_name["Ltx"]
    assert "Z(2,2)" in expressions_by_name["Lrx"]
    assert "S(1,2)" in expressions_by_name["S21_mag"]


def test_run_em_pipeline_supports_terminal_style_st_traces_with_long_names() -> None:
    fake_hfss = _FakeHfss()
    tx_term = "stub_rx_dd_back_B_rx_main_0_g0_7dbaea44_3af822c6_0_0_T1"
    rx_term = "stub_tx_dd_start_A_tx_main_0_g0_7dbaea44_3af822c6_0_0_T1"
    fake_hfss.available_traces = [
        f"St({tx_term},{tx_term})",
        f"St({tx_term},{rx_term})",
        f"St({rx_term},{tx_term})",
        f"St({rx_term},{rx_term})",
    ]
    run_em_pipeline(cast(Hfss, fake_hfss), cast(Modeler3D, _FakeModeler()), _input(), default_em_policy())
    expressions_by_name = {name: expr for name, expr, _ in fake_hfss.created_output_variables}
    assert f"Z({tx_term},{tx_term})" in expressions_by_name["Ltx"]
    assert f"Z({rx_term},{rx_term})" in expressions_by_name["Lrx"]
    assert f"St({tx_term},{rx_term})" in expressions_by_name["S21_mag"]


def test_run_em_pipeline_normalizes_parenthesized_terminal_names() -> None:
    fake_hfss = _FakeHfss()
    fake_hfss.available_traces = [
        "St((stub_rxdd_rx_main_0_g0_B_T1,(stub_rxdd_rx_main_0_g0_B_T1))",
        "St((stub_rxdd_rx_main_0_g0_B_T1,(stub_txdd_tx_main_0_0_T1))",
    ]
    run_em_pipeline(cast(Hfss, fake_hfss), cast(Modeler3D, _FakeModeler()), _input(), default_em_policy())
    expressions_by_name = {name: expr for name, expr, _ in fake_hfss.created_output_variables}
    assert "Z(stub_rxdd_rx_main_0_g0_B_T1,stub_rxdd_rx_main_0_g0_B_T1)" in expressions_by_name["Ltx"]
    assert "St(stub_rxdd_rx_main_0_g0_B_T1,stub_txdd_tx_main_0_0_T1)" in expressions_by_name["S21_mag"]


def test_build_ports_returns_endpoint_based_default_port_names() -> None:
    ports = build_ports(cast(Hfss, _FakeHfss()), cast(Modeler3D, _FakeModeler()), _input())
    assert ports == {"tx": ["TX_TML"], "rx": ["RX_TML"]}

from __future__ import annotations

import pytest
from typing import cast

from peetsfea.aedt.protocols import HfssSession

from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineResult, default_em_policy
from peetsfea.backend.pyaedt.em_pipeline.steps.analysis import build_post_templates
from peetsfea.backend.pyaedt.em_pipeline.steps.sources import apply_sources_phase
from peetsfea.backend.pyaedt.em_pipeline.validate import validate_pipeline
from peetsfea.types.manifest import OutputsSpec


class _FakeHfssForSources:
    def __init__(self, excitation_names: list[str]) -> None:
        self.excitation_names = excitation_names
        self.edited_sources_payloads: list[list[object]] = []
        self.odesign = self._Design(self)

    class _Design:
        def __init__(self, parent: "_FakeHfssForSources") -> None:
            self._parent = parent

        class _SolutionsModule:
            def __init__(self, parent: "_FakeHfssForSources") -> None:
                self._parent = parent

            def EditSources(self, payload: list[object]) -> None:
                self._parent.edited_sources_payloads.append(payload)

        def GetModule(self, name: str) -> object:
            if name == "Solutions":
                return _FakeHfssForSources._Design._SolutionsModule(self._parent)
            raise ValueError(f"unexpected module: {name}")


class _FakeHfssForPostTemplates:
    def __init__(self, excitation_names: list[str], traces: list[str]) -> None:
        self.excitation_names = excitation_names
        self._traces = traces
        self.created_output_variables: list[tuple[str, str, str]] = []
        self.report_names: list[str] = []
        self.odesign = self._Design(self)

    class _Design:
        def __init__(self, parent: "_FakeHfssForPostTemplates") -> None:
            self._parent = parent

        class _ReportSetupModule:
            def __init__(self, parent: "_FakeHfssForPostTemplates") -> None:
                self._parent = parent

            def CreateReport(
                self,
                report_name: str,
                report_category: str,
                plot_type: str,
                solution_name: str,
                context: list[object],
                variations: list[object],
                components: list[object],
                empty: list[object],
            ) -> bool:
                del report_category, plot_type, solution_name, context, variations, components, empty
                self._parent.report_names.append(report_name)
                return True

            def GetAllReportNames(self) -> list[str]:
                return list(self._parent.report_names)

        def GetModule(self, name: str) -> object:
            if name == "ReportSetup":
                return _FakeHfssForPostTemplates._Design._ReportSetupModule(self._parent)
            raise ValueError(f"unexpected module: {name}")

    def get_traces_for_plot(
        self,
        expression_filter: bool,
        category_filter: bool,
        context: str,
        setup_name: str,
        trace_filter: str,
        intrinsic_variations: tuple[object, ...],
    ) -> list[str]:
        del expression_filter, category_filter, context, setup_name, trace_filter, intrinsic_variations
        return list(self._traces)

    def create_output_variable(self, *, variable: str, expression: str, solution: str) -> bool:
        self.created_output_variables.append((variable, expression, solution))
        return True


def test_apply_sources_phase_uses_named_tx_rx_ports() -> None:
    fake_hfss = _FakeHfssForSources(["TX_TML", "RX_TML"])
    result = apply_sources_phase(cast(HfssSession, fake_hfss), {"tx": ["TX_TML"], "rx": ["RX_TML"]})

    assert result["tx_source_name"] == "TX_TML"
    assert result["rx_source_name"] == "RX_TML"
    assert result["tx_magnitude"] == "288V"
    assert result["rx_magnitude"] == "0V"
    assert result["tx_phase_deg"] == "0deg"
    assert result["rx_phase_deg"] == "0deg"
    assert fake_hfss.edited_sources_payloads
    payload = fake_hfss.edited_sources_payloads[0]
    payload_text = str(payload)
    assert "TX_TML" in payload_text
    assert "RX_TML" in payload_text
    assert "288V" in payload_text
    assert "0V" in payload_text


def test_apply_sources_phase_prefers_geometry_captured_terminal_names() -> None:
    fake_hfss = _FakeHfssForSources(["1_T1", "2_T1"])
    result = apply_sources_phase(cast(HfssSession, fake_hfss), {"tx": ["1_T1"], "rx": ["2_T1"]})

    assert result["tx_source_name"] == "1_T1"
    assert result["rx_source_name"] == "2_T1"
    payload_text = str(fake_hfss.edited_sources_payloads[0])
    assert "1_T1" in payload_text
    assert "2_T1" in payload_text
    assert "288V" in payload_text
    assert "0V" in payload_text


def test_apply_sources_phase_accepts_parenthesized_geometry_captured_terminal_names() -> None:
    fake_hfss = _FakeHfssForSources(["(1_T1)", "(2_T1)"])
    result = apply_sources_phase(cast(HfssSession, fake_hfss), {"tx": ["1_T1"], "rx": ["2_T1"]})

    assert result["tx_source_name"] == "(1_T1)"
    assert result["rx_source_name"] == "(2_T1)"
    payload_text = str(fake_hfss.edited_sources_payloads[0])
    assert "(1_T1)" in payload_text
    assert "(2_T1)" in payload_text
    assert "288V" in payload_text
    assert "0V" in payload_text


def test_apply_sources_phase_raises_when_rx_source_name_is_missing_even_if_stub_like_name_exists() -> None:
    fake_hfss = _FakeHfssForSources(["TX_TML", "rxs_rx_main_1_1_c_T1"])

    with pytest.raises(ValueError, match="rx source name is not available in HFSS excitation names"):
        apply_sources_phase(cast(HfssSession, fake_hfss), {"tx": ["TX_TML"], "rx": ["RX_TML"]})


def test_apply_sources_phase_raises_when_multiple_stub_like_names_exist_but_rx_source_name_is_missing() -> None:
    fake_hfss = _FakeHfssForSources(["TX_TML", "rxs_rx_main_0_0_A_T1", "rxs_rx_main_1_1_c_T1"])

    with pytest.raises(ValueError, match="rx source name is not available in HFSS excitation names"):
        apply_sources_phase(cast(HfssSession, fake_hfss), {"tx": ["TX_TML"], "rx": ["RX_TML"]})


def test_apply_sources_phase_raises_when_rx_source_is_missing() -> None:
    fake_hfss = _FakeHfssForSources(["TX_TML"])

    with pytest.raises(ValueError, match="rx source name is not available in HFSS excitation names"):
        apply_sources_phase(cast(HfssSession, fake_hfss), {"tx": ["TX_TML"], "rx": ["RX_TML"]})


def test_apply_sources_phase_supports_rx_only_port_mode() -> None:
    fake_hfss = _FakeHfssForSources(["RX_TML"])
    result = apply_sources_phase(cast(HfssSession, fake_hfss), {"tx": [], "rx": ["RX_TML"]})

    assert result["rx_source_name"] == "RX_TML"
    assert result["rx_magnitude"] == "1V"
    assert result["rx_phase_deg"] == "0deg"
    assert list(result.keys()) == ["rx_source_name", "rx_phase_deg", "rx_magnitude"]
    payload_text = str(fake_hfss.edited_sources_payloads[0])
    assert "RX_TML" in payload_text
    assert "1V" in payload_text
    assert "288V" not in payload_text


def test_validate_pipeline_supports_rx_only_mode() -> None:
    policy = default_em_policy()
    result = {
        "groups": {"tx": [], "rx": ["rx_copper_l0"], "fr4": ["rx_pcb_l0"]},
        "series": {"tx": [], "rx": ["rx_copper_l0"]},
        "subtract": {"tx": [], "rx": []},
        "boundary": {"name": "Region"},
        "ports": {"tx": [], "rx": ["RX_TML"]},
        "sources": {"rx_source_name": "RX_TML", "rx_phase_deg": "0deg", "rx_magnitude": "1V"},
        "analysis": {"setup_name": "Setup1", "setup_frequency_hz": 6.78e6},
        "post_templates": [],
        "validation_report": {"ok": False, "gate": "pending", "message": "pending"},
    }
    validation_report = validate_pipeline(cast(EmPipelineResult, result), policy)
    assert validation_report["ok"] is True
    assert validation_report["message"] == "ok"


def test_build_post_templates_supports_rx_only_expression_without_tx_placeholder() -> None:
    fake_hfss = _FakeHfssForPostTemplates(
        excitation_names=["RX_TML"],
        traces=["S(RX_TML,RX_TML)"],
    )
    outputs = {
        "report_name": "rx-only-report",
        "solution_name": "Setup1 : LastAdaptive",
        "primary_sweep": "Freq",
        "report_category": "Output Variables",
        "plot_type": "Rectangular Plot",
        "variables": [
            {"name": "rx_self_s", "expression": "mag(S(RX_TML,RX_TML))"},
        ],
    }

    built = build_post_templates(
        cast(HfssSession, fake_hfss),
        cast(OutputsSpec, outputs),
        {"tx": [], "rx": ["RX_TML"]},
    )

    assert len(built) == 1
    assert len(fake_hfss.created_output_variables) == 1
    assert [report_name for report_name in fake_hfss.report_names] == [
        "rx-only-report",
        "Table1",
        "Table2",
    ]
    _, expression, _ = fake_hfss.created_output_variables[0]
    assert "RX_TML" in expression
    assert "TX_TML" not in expression


def test_build_post_templates_rx_only_rejects_output_expression_with_tx_placeholder() -> None:
    fake_hfss = _FakeHfssForPostTemplates(
        excitation_names=["RX_TML"],
        traces=["S(RX_TML,RX_TML)"],
    )
    outputs = {
        "report_name": "rx-only-report",
        "solution_name": "Setup1 : LastAdaptive",
        "primary_sweep": "Freq",
        "report_category": "Output Variables",
        "plot_type": "Rectangular Plot",
        "variables": [
            {"name": "invalid_tx_ref", "expression": "mag(S(TX_TML,RX_TML))"},
        ],
    }

    with pytest.raises(ValueError, match="references TX_TML"):
        build_post_templates(
            cast(HfssSession, fake_hfss),
            cast(OutputsSpec, outputs),
            {"tx": [], "rx": ["RX_TML"]},
        )

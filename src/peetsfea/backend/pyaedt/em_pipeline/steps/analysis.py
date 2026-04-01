from __future__ import annotations

import re
from typing import cast

from peetsfea.aedt import Hfss
from peetsfea.aedt.protocols import AnalysisSetupModuleSession, DesignSession, HfssSession
from peetsfea.aedt.protocols import ReportSetupModuleSession, TraceProviderSession

from peetsfea.backend.pyaedt.failfast import raise_on_false
from peetsfea.backend.pyaedt.em_pipeline.steps.excitation_names import (
    normalize_excitation_name,
    normalized_excitation_name_map,
)
from peetsfea.backend.pyaedt.em_pipeline.steps.report_templates import build_post_template
from peetsfea.types.manifest import EmPolicy, EmPorts, OutputsSpec, PostTemplateResult


def _format_frequency_mhz(frequency_hz: float) -> str:
    frequency_mhz = frequency_hz / 1.0e6
    return f"{frequency_mhz:g}MHz"


def build_analysis(hfss: HfssSession, policy: EmPolicy) -> dict[str, float | str]:
    setup_name = "Setup1"
    setup_frequency_hz = policy["setup_frequency_hz"]
    sweep_start_hz = policy["sweep_start_hz"]
    sweep_stop_hz = policy["sweep_stop_hz"]
    if setup_name in hfss.setup_names:
        raise_on_false(
            hfss.delete_setup(setup_name),
            operation="delete_setup",
            context={"setup_name": setup_name},
        )
    assert (_:=hfss.odesign)
    assert isinstance(_, DesignSession)
    design: DesignSession = _
    analysis_module = cast(AnalysisSetupModuleSession, design.GetModule("AnalysisSetup"))
    raise_on_false(
        analysis_module.InsertSetup(
            "HfssDriven",
            [
                "NAME:Setup1",
                "SolveType:=",
                "Single",
                "Frequency:=",
                _format_frequency_mhz(setup_frequency_hz),
                "MaxDeltaS:=",
                policy["max_delta_s"],
                "UseMatrixConv:=",
                False,
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
                [
                    "NAME:MeshLink",
                    "ImportMesh:=",
                    False,
                ],
                "BasisOrder:=",
                policy["basis_order"],
                "DoLambdaRefine:=",
                True,
                "DoMaterialLambda:=",
                True,
                "SetLambdaTarget:=",
                False,
                "Target:=",
                0.3333,
                "UseMaxTetIncrease:=",
                True,
                "MaxTetIncrease:=",
                700_000,
                "PortAccuracy:=",
                policy["port_accuracy"],
                "UseABCOnPort:=",
                False,
                "SetPortMinMaxTri:=",
                False,
                "DrivenSolverType:=",
                "Direct Solver",
                "EnhancedLowFreqAccuracy:=",
                False,
                "EnhancedFEBIPreconditioner:=",
                False,
                "SaveRadFieldsOnly:=",
                False,
                "SaveAnyFields:=",
                True,
                "IESolverType:=",
                "Auto",
                "LambdaTargetForIESolver:=",
                0.15,
                "UseDefaultLambdaTgtForIESolver:=",
                True,
                "IE Solver Accuracy:=",
                "Balanced",
                "InfiniteSphereSetup:=",
                "",
                "MaxPass:=",
                10,
                "MinPass:=",
                1,
                "MinConvPass:=",
                1,
                "PerError:=",
                1,
                "PerRefine:=",
                30,
            ],
        ),
        operation="InsertSetup",
        context={"setup_name": setup_name, "setup_frequency_hz": setup_frequency_hz},
    )
    # Frequency sweep creation is temporarily disabled. Keep policy values in the
    # returned payload so downstream callers can still inspect the configured range.
    return {
        "setup_name": setup_name,
        "setup_frequency_hz": setup_frequency_hz,
        "sweep_name": "disabled",
        "sweep_start_hz": sweep_start_hz,
        "sweep_stop_hz": sweep_stop_hz,
    }


def _extract_trace_terms(traces: list[str]) -> list[tuple[str, str, str]]:
    terms: list[tuple[str, str, str]] = []
    for trace in traces:
        match = re.search(r"(St|S|Z|Y)\(([^,]+),([^)]+)\)", trace)
        if not match:
            continue
        function_name = match.group(1).strip()
        port_0 = match.group(2).strip().strip("'\"").lstrip("(").rstrip(")")
        port_1 = match.group(3).strip().strip("'\"").lstrip("(").rstrip(")")
        if function_name and port_0 and port_1:
            terms.append((function_name, port_0, port_1))
    return terms


def _require_terminal_name(*, terminal_name: str, excitation_names: list[str], role: str) -> str:
    normalized_map = normalized_excitation_name_map(excitation_names)
    normalized_terminal_name = normalize_excitation_name(terminal_name)
    if normalized_terminal_name not in normalized_map:
        raise ValueError(
            f"{role} port name is not available in HFSS excitation names "
            f"(port={terminal_name}, available={sorted(normalized_map)})"
        )
    return normalized_map[normalized_terminal_name]


def _resolve_port_terms_for_expressions(hfss: HfssSession, ports: EmPorts) -> tuple[str, str, str]:
    provider: TraceProviderSession = hfss
    traces = provider.get_traces_for_plot(True, True, "", "", "S(", ())
    if not traces:
        raise ValueError("HFSS did not return any traces for EM post-processing")
    terms = _extract_trace_terms(traces)
    if not terms:
        raise ValueError(f"HFSS traces did not contain any terminal terms (traces={traces})")
    function_names = {function_name for function_name, _, _ in terms}
    s_function = "St" if "St" in function_names else "S"
    excitation_names = list(hfss.excitation_names)
    if len(ports["tx"]) != 1 or len(ports["rx"]) != 1:
        raise ValueError(
            "EM post-processing requires exactly one TX port and one RX port "
            f"(tx_ports={ports['tx']}, rx_ports={ports['rx']})"
        )
    tx_terminal_name = _require_terminal_name(
        terminal_name=ports["tx"][0],
        excitation_names=excitation_names,
        role="tx",
    )
    rx_terminal_name = _require_terminal_name(
        terminal_name=ports["rx"][0],
        excitation_names=excitation_names,
        role="rx",
    )
    return tx_terminal_name, rx_terminal_name, s_function


def build_post_templates(hfss: HfssSession, outputs: OutputsSpec, ports: EmPorts) -> list[PostTemplateResult]:
    templates = [build_post_template(outputs)]
    design = cast(DesignSession, hfss.odesign)
    report_setup = cast(ReportSetupModuleSession, design.GetModule("ReportSetup"))
    tx_port_name, rx_port_name, s_function = _resolve_port_terms_for_expressions(hfss, ports)
    built: list[PostTemplateResult] = []
    for template in templates:
        for output_variable in template["output_variables"]:
            expression = (
                output_variable["expression"]
                .replace("TX_TML", tx_port_name)
                .replace("RX_TML", rx_port_name)
                .replace("S(", f"{s_function}(")
            )
            raise_on_false(
                hfss.create_output_variable(
                    variable=output_variable["name"],
                    expression=expression,
                    solution=template["solution_name"],
                ),
                operation="create_output_variable",
                context={
                    "name": output_variable["name"],
                    "solution": template["solution_name"],
                    "tx_port": tx_port_name,
                    "rx_port": rx_port_name,
                },
            )
        context: list[object] = []
        variations: list[object] = []
        for key, values in template["variations"].items():
            variations.extend([f"{key}:=", list(values)])
        components: list[object] = [
            "X Component:=",
            template["primary_sweep"],
            "Y Component:=",
            list(template["traces"]),
        ]
        raise_on_false(
            report_setup.CreateReport(
                template["report_name"],
                template["report_category"],
                template["plot_type"],
                template["solution_name"],
                context,
                variations,
                components,
                [],
            ),
            operation="CreateReport",
            context={
                "report_name": template["report_name"],
                "solution_name": template["solution_name"],
            },
        )
        report_names = report_setup.GetAllReportNames()
        if template["report_name"] not in set(report_names):
            raise ValueError(
                "Failed to create output-variable report in AEDT Results tree "
                f"(report_name={template['report_name']}, solution={template['solution_name']})"
            )
        built.append(
            {
                "template_id": template["template_id"],
                "report_name": template["report_name"],
                "solution_name": template["solution_name"],
                "traces": list(template["traces"]),
                "output_variables": [entry["name"] for entry in template["output_variables"]],
            }
        )
    return built

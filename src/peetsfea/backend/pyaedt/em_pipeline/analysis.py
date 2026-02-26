from __future__ import annotations

import re
from typing import Protocol, cast

from ansys.aedt.core import Hfss

from peetsfea.backend.pyaedt.em_pipeline.report_templates import default_post_templates
from peetsfea.types.manifest import EmPolicy, PostTemplateResult


class _AnalysisSetupModule(Protocol):
    def InsertSetup(self, setup_type: str, props: list[object]) -> None: ...

    def InsertFrequencySweep(self, setup_name: str, props: list[object]) -> None: ...


class _DesignModuleProvider(Protocol):
    def GetModule(self, name: str) -> object: ...


class _ReportSetupModule(Protocol):
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
    ) -> None: ...

    def GetAllReportNames(self) -> list[str] | tuple[str, ...]: ...


class _TraceProvider(Protocol):
    def get_traces_for_plot(
        self,
        get_self_terms: bool = True,
        get_mutual_terms: bool = True,
        first_element_filter: str | None = None,
        second_element_filter: str | None = None,
        category: str = "dB(S",
        differential_pairs: list[object] | None = None,
    ) -> list[str]: ...


def _format_frequency_mhz(frequency_hz: float) -> str:
    frequency_mhz = frequency_hz / 1.0e6
    return f"{frequency_mhz:g}MHz"


def build_analysis(hfss: Hfss, policy: EmPolicy) -> dict[str, float | str]:
    setup_name = "Setup1"
    setup_frequency_hz = policy["setup_frequency_hz"]
    sweep_start_hz = policy["sweep_start_hz"]
    sweep_stop_hz = policy["sweep_stop_hz"]
    if setup_name in hfss.setup_names:
        hfss.delete_setup(setup_name)
    design = hfss.odesign
    assert design is not None and not isinstance(design, str), "HFSS design is not initialized"
    analysis_module = cast(_AnalysisSetupModule, cast(_DesignModuleProvider, design).GetModule("AnalysisSetup"))
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
            False,
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
    )
    analysis_module.InsertFrequencySweep(
        "Setup1",
        [
            "NAME:Sweep",
            "IsEnabled:=",
            True,
            "RangeType:=",
            "LogScale",
            "RangeStart:=",
            _format_frequency_mhz(sweep_start_hz),
            "RangeEnd:=",
            _format_frequency_mhz(sweep_stop_hz),
            "RangeCount:=",
            401,
            "RangeSamples:=",
            401,
            "Type:=",
            "Interpolating",
            "SaveFields:=",
            False,
            "SaveRadFields:=",
            False,
            "InterpTolerance:=",
            0.5,
            "InterpMaxSolns:=",
            250,
            "InterpMinSolns:=",
            0,
            "InterpMinSubranges:=",
            1,
            "InterpUseS:=",
            True,
            "InterpUsePortImped:=",
            True,
            "InterpUsePropConst:=",
            True,
            "UseDerivativeConvergence:=",
            False,
            "InterpDerivTolerance:=",
            0.2,
            "UseFullBasis:=",
            True,
            "EnforcePassivity:=",
            True,
            "PassivityErrorTolerance:=",
            0.0001,
            "EnforceCausality:=",
            False,
            "SMatrixOnlySolveMode:=",
            "Auto",
        ],
    )
    return {
        "setup_name": setup_name,
        "setup_frequency_hz": setup_frequency_hz,
        "sweep_name": "Sweep",
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


def _resolve_port_terms_for_expressions(hfss: Hfss) -> tuple[str, str, str]:
    provider = cast(_TraceProvider, hfss)
    traces: list[str] = []
    categories = ("S(", "St(")
    for category in categories:
        try:
            category_traces = provider.get_traces_for_plot(get_self_terms=True, get_mutual_terms=True, category=category)
        except Exception:
            continue
        traces.extend(category_traces)
    terms = _extract_trace_terms(traces)
    try:
        excitation_names = list(getattr(hfss, "excitation_names", []))
    except Exception:
        excitation_names = []
    normalized_excitation_names = [
        str(name).strip().strip("'\"").lstrip("(").rstrip(")")
        for name in excitation_names
        if isinstance(name, str) and str(name).strip()
    ]
    if not terms and not normalized_excitation_names:
        return ("1", "2", "S")
    ports: list[str] = []
    function_names: list[str] = []
    for function_name, port_0, port_1 in terms:
        if function_name not in function_names:
            function_names.append(function_name)
        if port_0 not in ports:
            ports.append(port_0)
        if port_1 not in ports:
            ports.append(port_1)
    for excitation_name in normalized_excitation_names:
        if excitation_name not in ports:
            ports.append(excitation_name)

    s_function = "St" if "St" in function_names else "S"
    if "TX_TML" in ports and "RX_TML" in ports:
        return ("TX_TML", "RX_TML", s_function)
    if "1" in ports and "2" in ports:
        return ("1", "2", s_function)
    if len(ports) >= 2:
        return (ports[0], ports[1], s_function)
    return ("1", "2", s_function)


def build_post_templates(hfss: Hfss) -> list[PostTemplateResult]:
    templates = default_post_templates()
    design = hfss.odesign
    assert design is not None and not isinstance(design, str), "HFSS design is not initialized"
    report_setup = cast(_ReportSetupModule, cast(_DesignModuleProvider, design).GetModule("ReportSetup"))
    tx_port_name, rx_port_name, s_function = _resolve_port_terms_for_expressions(hfss)
    built: list[PostTemplateResult] = []
    for template in templates:
        for output_variable in template["output_variables"]:
            expression = (
                output_variable["expression"]
                .replace("TX_TML", tx_port_name)
                .replace("RX_TML", rx_port_name)
                .replace("S(", f"{s_function}(")
            )
            created = hfss.create_output_variable(
                variable=output_variable["name"],
                expression=expression,
                solution=template["solution_name"],
            )
            if not created:
                raise ValueError(
                    "Failed to create output variable "
                    f"(name={output_variable['name']}, solution={template['solution_name']}, "
                    f"tx_port={tx_port_name}, rx_port={rx_port_name})"
                )
        context: list[object] = ["Domain:=", "Sweep"]
        variations: list[object] = []
        for key, values in template["variations"].items():
            variations.extend([f"{key}:=", list(values)])
        components: list[object] = [
            "X Component:=",
            template["primary_sweep"],
            "Y Component:=",
            list(template["traces"]),
        ]
        try:
            report_setup.CreateReport(
                template["report_name"],
                template["report_category"],
                template["plot_type"],
                template["solution_name"],
                context,
                variations,
                components,
                [],
            )
        except TypeError:
            # Some AEDT versions expose CreateReport without the final options argument.
            report_setup.CreateReport(
                template["report_name"],
                template["report_category"],
                template["plot_type"],
                template["solution_name"],
                context,
                variations,
                components,
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

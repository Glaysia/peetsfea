from __future__ import annotations

import re
from typing import Literal, TypedDict, cast

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


def _build_frequency_sweep_payload() -> list[object]:
    return [
        "NAME:Sweep",
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
        "RangeSamples:=",
        100,
        [
            "NAME:SweepRanges",
            [
                "NAME:Subrange",
                "RangeType:=",
                "LinearCount",
                "RangeStart:=",
                "0MHz",
                "RangeEnd:=",
                "0MHz",
                "RangeCount:=",
                1,
            ],
        ],
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
        "MinSolvedFreq:=",
        "0.01GHz",
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
        "UseQ3DForDCSolve:=",
        True,
        "SMatrixOnlySolveMode:=",
        "Auto",
    ]


_DIAGNOSTIC_REPORT_TABLE_1_TRACES = [
    "Ltx_uH",
    "Lrx_uH",
    "M_uH",
    "k_ratio",
    "Qtx_ratio",
    "Qrx_ratio",
    "FOM_ratio",
    "Rtx_ac_ohm",
    "Rrx_ac_ohm",
    "Xtx_ohm",
    "Xrx_ohm",
    "M_over_Ltx_ratio",
    "M_over_Lrx_ratio",
    "Gtx_S",
    "Btx_S",
    "Grx_S",
    "Brx_S",
    "S11_mag_ratio",
    "S21_mag_ratio",
    "S21_phase_deg",
    "S22_mag_ratio",
    "eta_s21_power_ratio",
    "eta_tx_accept_ratio",
    "eta_rx_accept_ratio",
    "eta_match_product_ratio",
    "eta_s21_from_tx_accept_ratio",
    "eta_s21_from_rx_accept_ratio",
    "eta_s21_two_sided_norm_ratio",
    "eta_fom_max_ratio",
    "Volume(under_rx_air_u0)",
    "Volume(under_rx_pet_psa_u0)",
    "Volume(under_rx_ferrite_u0)",
    "Volume(rx_copper_l0)",
    "Volume(rx_pcb_l0)",
    "Volume(tx_underlay_ferrite_u0)",
    "Volume(tx_underlay_pet_psa_u0)",
    "Volume(tx_inner_tube_l0)",
    "Area(tx_inner_port_sheet)",
    "Area(rx_port_sheet)",
    "Volume(Region_Abs_3500mm)",
]


_DIAGNOSTIC_REPORT_TABLE_2_TRACES = [
    "Ltx_uH",
    "Lrx_uH",
    "M_uH",
    "k_ratio",
    "Qtx_ratio",
    "Qrx_ratio",
    "FOM_ratio",
    "Rtx_ac_ohm",
    "Rrx_ac_ohm",
    "Xtx_ohm",
    "Xrx_ohm",
    "M_over_Ltx_ratio",
    "M_over_Lrx_ratio",
    "Gtx_S",
    "Btx_S",
    "Grx_S",
    "Brx_S",
    "S11_mag_ratio",
    "S21_mag_ratio",
    "S21_phase_deg",
    "S22_mag_ratio",
    "eta_s21_power_ratio",
    "eta_tx_accept_ratio",
    "eta_rx_accept_ratio",
    "eta_match_product_ratio",
    "eta_s21_from_tx_accept_ratio",
    "eta_s21_from_rx_accept_ratio",
    "eta_s21_two_sided_norm_ratio",
    "eta_fom_max_ratio",
    "SolvedElements",
    "MaxMagDeltaS",
]


def build_analysis(hfss: HfssSession, policy: EmPolicy) -> dict[str, float | str]:
    setup_name = "Setup1"
    setup_frequency_hz = policy["setup_frequency_hz"]
    sweep_name = "Sweep"
    sweep_start_hz = 0.1e6
    sweep_stop_hz = 100.0e6
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
    raise_on_false(
        analysis_module.InsertFrequencySweep(
            setup_name,
            _build_frequency_sweep_payload(),
        ),
        operation="InsertFrequencySweep",
        context={
            "setup_name": setup_name,
            "sweep_name": sweep_name,
            "sweep_start_hz": sweep_start_hz,
            "sweep_stop_hz": sweep_stop_hz,
        },
    )
    return {
        "setup_name": setup_name,
        "setup_frequency_hz": setup_frequency_hz,
        "sweep_name": sweep_name,
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


class _TxRxPostTerms(TypedDict):
    mode: Literal["tx_rx_pair"]
    tx_terminal_name: str
    rx_terminal_name: str
    s_function: str


class _RxOnlyPostTerms(TypedDict):
    mode: Literal["rx_only"]
    rx_terminal_name: str
    s_function: str


def _resolve_port_terms_for_expressions(hfss: HfssSession, ports: EmPorts) -> _TxRxPostTerms | _RxOnlyPostTerms:
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
    tx_ports = ports["tx"]
    rx_ports = ports["rx"]
    has_tx_port = len(tx_ports) == 1
    has_rx_port = len(rx_ports) == 1
    is_tx_rx_pair = has_tx_port and has_rx_port
    is_rx_only = (not has_tx_port) and has_rx_port and len(tx_ports) == 0
    if not (is_tx_rx_pair or is_rx_only):
        raise ValueError(
            "EM post-processing requires either one TX+one RX pair or RX-only "
            f"(tx_ports={tx_ports}, rx_ports={rx_ports})"
        )
    rx_terminal_name = _require_terminal_name(
        terminal_name=rx_ports[0],
        excitation_names=excitation_names,
        role="rx",
    )
    if is_rx_only:
        return {
            "mode": "rx_only",
            "rx_terminal_name": rx_terminal_name,
            "s_function": s_function,
        }
    tx_terminal_name = _require_terminal_name(
        terminal_name=tx_ports[0],
        excitation_names=excitation_names,
        role="tx",
    )
    return {
        "mode": "tx_rx_pair",
        "tx_terminal_name": tx_terminal_name,
        "rx_terminal_name": rx_terminal_name,
        "s_function": s_function,
    }


def build_post_templates(hfss: HfssSession, outputs: OutputsSpec, ports: EmPorts) -> list[PostTemplateResult]:
    templates = [build_post_template(outputs)]
    design = cast(DesignSession, hfss.odesign)
    report_setup = cast(ReportSetupModuleSession, design.GetModule("ReportSetup"))
    terms = _resolve_port_terms_for_expressions(hfss, ports)
    rx_port_name = terms["rx_terminal_name"]
    s_function = terms["s_function"]
    built: list[PostTemplateResult] = []
    for template in templates:
        is_output_variables_report = template["report_name"] == "Output Variables Table1"
        report_solution_name = "Setup1 : Sweep" if is_output_variables_report else template["solution_name"]
        report_context: list[object] = ["Domain:=", "Sweep"] if is_output_variables_report else []
        for output_variable in template["output_variables"]:
            expression = output_variable["expression"]
            create_output_context: dict[str, object] = {
                "name": output_variable["name"],
                "solution": report_solution_name,
                "rx_port": rx_port_name,
                "mode": terms["mode"],
            }
            if terms["mode"] == "tx_rx_pair" and "TX_TML" in expression:
                tx_port_name = terms["tx_terminal_name"]
                expression = expression.replace("TX_TML", tx_port_name)
                create_output_context["tx_port"] = tx_port_name
            if terms["mode"] == "rx_only" and "TX_TML" in expression:
                raise ValueError(
                    "Output expression references TX_TML but RX-only mode has no TX terminal "
                    f"(output={output_variable['name']}, expression={output_variable['expression']})"
                )
            if "RX_TML" in expression:
                expression = expression.replace("RX_TML", rx_port_name)
            expression = expression.replace("S(", f"{s_function}(")
            raise_on_false(
                hfss.create_output_variable(
                    variable=output_variable["name"],
                    expression=expression,
                    solution=report_solution_name,
                ),
                operation="create_output_variable",
                context=create_output_context,
            )
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
                report_solution_name,
                report_context,
                variations,
                components,
                [],
            ),
            operation="CreateReport",
            context={
                "report_name": template["report_name"],
                "solution_name": report_solution_name,
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
                "solution_name": report_solution_name,
                "traces": list(template["traces"]),
                "output_variables": [entry["name"] for entry in template["output_variables"]],
            }
        )

    report_category = templates[0]["report_category"]
    plot_type = templates[0]["plot_type"]
    report_primary_sweep = templates[0]["primary_sweep"]
    diagnostic_reports = [
        {
            "report_name": "Table1",
            "solution_name": "Setup1 : LastAdaptive",
            "context": [],
            "variations": [
                "Freq:=",
                ["All"],
            ],
            "traces": _DIAGNOSTIC_REPORT_TABLE_1_TRACES,
        },
        {
            "report_name": "Table2",
            "solution_name": "Setup1 : AdaptivePass",
            "context": [],
            "variations": [
                "Freq:=",
                ["All"],
                "Pass:=",
                ["All"],
            ],
            "traces": _DIAGNOSTIC_REPORT_TABLE_2_TRACES,
        },
    ]
    for report in diagnostic_reports:
        raise_on_false(
            report_setup.CreateReport(
                report["report_name"],
                report_category,
                plot_type,
                report["solution_name"],
                report["context"],
                report["variations"],
                [
                    "X Component:=",
                    report_primary_sweep,
                    "Y Component:=",
                    report["traces"],
                ],
                [],
            ),
            operation="CreateReport",
            context={
                "report_name": report["report_name"],
                "solution_name": report["solution_name"],
                "report_category": report_category,
                "plot_type": plot_type,
            },
        )
        report_names = report_setup.GetAllReportNames()
        if report["report_name"] not in set(report_names):
            raise ValueError(
                "Failed to create required AEDT report in Results tree "
                f"(report_name={report['report_name']}, solution={report['solution_name']})"
            )

    report_names = set(report_setup.GetAllReportNames())
    expected_report_names = {"Table1", "Table2"}
    expected_report_names.update({template["report_name"] for template in templates})
    for report_name in expected_report_names:
        if report_name not in report_names:
            raise ValueError(
                "Failed to create required AEDT report in Results tree "
                f"(report_name={report_name!r})"
            )
    return built

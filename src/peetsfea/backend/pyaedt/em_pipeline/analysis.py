from __future__ import annotations

from typing import Protocol, cast

from ansys.aedt.core import Hfss

from peetsfea.types.manifest import EmPolicy


class _AnalysisSetupModule(Protocol):
    def InsertSetup(self, setup_type: str, props: list[object]) -> None: ...

    def InsertFrequencySweep(self, setup_name: str, props: list[object]) -> None: ...


class _DesignModuleProvider(Protocol):
    def GetModule(self, name: str) -> object: ...


def build_analysis(hfss: Hfss, policy: EmPolicy) -> dict[str, float | str]:
    _ = policy
    setup_name = "Setup1"
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
            "6.78MHz",
            "MaxDeltaS:=",
            0.001,
            "UseMatrixConv:=",
            False,
            "MaximumPasses:=",
            35,
            "MinimumPasses:=",
            9,
            "MinimumConvergedPasses:=",
            13,
            "PercentRefinement:=",
            65,
            "IsEnabled:=",
            True,
            [
                "NAME:MeshLink",
                "ImportMesh:=",
                False,
            ],
            "BasisOrder:=",
            1,
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
            2,
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
            "1MHz",
            "RangeEnd:=",
            "45MHz",
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
        "setup_frequency_hz": 6.78e6,
        "sweep_name": "Sweep",
        "sweep_start_hz": 1.0e6,
        "sweep_stop_hz": 45.0e6,
    }


def build_post_templates() -> list[str]:
    return ["s_parameters", "z_parameters"]

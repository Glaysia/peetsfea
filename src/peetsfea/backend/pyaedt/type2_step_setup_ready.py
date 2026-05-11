from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypedDict, cast

from peetsfea.aedt.failfast import raise_on_false
from peetsfea.aedt.protocols import DesignSession, HfssSession
from peetsfea.backend.pyaedt.em_pipeline.contracts import default_em_policy
from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineResult
from peetsfea.backend.pyaedt.em_pipeline.series import build_series
from peetsfea.backend.pyaedt.em_pipeline.steps.analysis import build_analysis, build_post_templates
from peetsfea.backend.pyaedt.em_pipeline.steps.boundary_port import build_boundary
from peetsfea.backend.pyaedt.em_pipeline.steps.grouping import build_groups
from peetsfea.backend.pyaedt.em_pipeline.steps.sources import apply_sources_phase
from peetsfea.backend.pyaedt.em_pipeline.subtract import build_subtract
from peetsfea.backend.pyaedt.em_pipeline.validate import validate_pipeline
from peetsfea.backend.pyaedt.type2_step_em_input import build_type2_em_input
from peetsfea.backend.pyaedt.type2_step_import_core import (
    Type2ImportedLedger,
    build_imported_ledger,
    write_imported_ledger,
)
from peetsfea.backend.pyaedt.type2_step_em_solve import Type2EmSolveResult, solve_type2_setup_ready_hfss
from peetsfea.backend.pyaedt.type2_step_import_ledger import ValidatedStepLedger, load_step_ledger
from peetsfea.backend.pyaedt.type2_step_port_assignment import assign_type2_lumped_ports
from peetsfea.backend.pyaedt.type2_step_post_import_mesh import (
    Type2ImportedMeshSummary,
    assign_post_import_mesh,
)
from peetsfea.backend.pyaedt.type2_step_runtime_common import (
    create_headless_hfss,
    prepare_attached_import_design,
)
from peetsfea.type2_sampled import DesignVariableEntry
from peetsfea.types.manifest import EmPolicy, EmPorts, OutputsSpec, OutputVariableSpec

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SOURCE_STEP_LEDGER_PATH = REPO_ROOT / "run" / "step" / "type2" / "type2_step_ledger.json"
DEFAULT_IMPORTED_LEDGER_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_import" / "type2_imported_ledger.json"
DEFAULT_OUTPUT_AEDT_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_setup_ready" / "type2_setup_ready.aedt"
DEFAULT_DESIGN_NAME = "type2_step_setup_ready"
_RX_SINGLE_COIL_ROLE: str = "rx_single_coil"
_TX_INNER_SINGLE_COIL_ROLE: str = "tx_inner_single_coil"
_TX_OUTER_SINGLE_COIL_ROLE: str = "tx_outer_single_coil"
_TV_ALUMINUM_PLATE_ROLE: str = "tv_aluminum_plate"
_SETUP_BRANCH_RX_SINGLE_READY = "rx_single_ready"
_SETUP_BRANCH_TXRX_READY = "txrx_ready"
_ACTIVE_RX_ONLY_OUTPUT_VARIABLE_NAMES: frozenset[str] = frozenset(
    {
        "Lrx_uH",
        "Qrx_ratio",
        "Rrx_ac_ohm",
        "Xrx_ohm",
        "Grx_S",
        "Brx_S",
        "Srx_self_mag_ratio",
        "eta_rx_accept_ratio",
    }
)
_ACTIVE_TXRX_OUTPUT_VARIABLE_NAMES: frozenset[str] = frozenset(
    {
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
    }
)
_RX_ONLY_OUTPUT_VARIABLE_ALIASES: dict[str, str] = {
    "S22_mag_ratio": "Srx_self_mag_ratio",
}

HfssFactory = Callable[[str], HfssSession]


class Type2SetupReadyResult(TypedDict):
    source_toml_path: str
    source_step_ledger_path: str
    scene_step_path: str
    seed: int
    aedt_path: str
    imported_ledger_path: str
    mesh: Type2ImportedMeshSummary
    boundary: dict[str, str]
    ports: EmPorts
    sources: dict[str, str]
    analysis: dict[str, float | str]
    validation_report: dict[str, str | bool]


class Type2SetupSolvedResult(Type2SetupReadyResult):
    em_solve: Type2EmSolveResult


Type2PlateStackPortReadyResult = Type2SetupReadyResult
Type2StepSetupFacadeResult = Type2SetupReadyResult


def _setup_ready_policy(ledger: ValidatedStepLedger) -> EmPolicy:
    policy = default_em_policy()
    policy["radiation_margin_mm"] = ledger["em_policy"]["radiation_margin_mm"]
    return cast(EmPolicy, policy)


def _validate_design(hfss: HfssSession) -> None:
    assert (_ := hfss.odesign)
    assert isinstance(_, DesignSession)
    design: DesignSession = _
    desktop = hfss.desktop_class
    messages = list(desktop.GetMessages("", "", 0))
    try:
        validation_result = design.ValidateDesign()
    except RuntimeError as exc:
        post_validate_messages = list(desktop.GetMessages("", "", 0))
        raise RuntimeError(f"{exc} (desktop_messages={post_validate_messages!r})") from exc
    raise_on_false(
        validation_result,
        operation="ValidateDesign",
        context={"desktop_messages": messages},
    )


def _assign_design_variables(
    hfss: HfssSession,
    *,
    design_variables: tuple[DesignVariableEntry, ...],
) -> None:
    for variable_name, expression in design_variables:
        hfss[variable_name] = expression


def _rx_only_outputs(outputs: OutputsSpec) -> OutputsSpec:
    variables: list[OutputVariableSpec] = []
    emitted_names: set[str] = set()
    for output_variable in outputs["variables"]:
        source_name = output_variable["name"]
        output_name = _RX_ONLY_OUTPUT_VARIABLE_ALIASES[source_name] if source_name in _RX_ONLY_OUTPUT_VARIABLE_ALIASES else source_name
        if output_name not in _ACTIVE_RX_ONLY_OUTPUT_VARIABLE_NAMES:
            continue
        if output_name in emitted_names:
            raise ValueError(f"RX-only output variable name collision (name={output_name!r})")
        expression = output_variable["expression"]
        if "TX_TML" in expression:
            raise ValueError(
                "RX-only active output variable must not reference TX_TML "
                f"(name={source_name!r}, expression={expression!r})"
            )
        variables.append({"name": output_name, "expression": expression})
        emitted_names.add(output_name)
    missing_names = sorted(_ACTIVE_RX_ONLY_OUTPUT_VARIABLE_NAMES.difference(emitted_names))
    if missing_names:
        raise ValueError(f"RX-only output spec is missing active variables (missing={missing_names})")
    return {
        "mode": "RxOnly",
        "report_name": outputs["report_name"],
        "solution_name": outputs["solution_name"],
        "primary_sweep": outputs["primary_sweep"],
        "report_category": outputs["report_category"],
        "plot_type": outputs["plot_type"],
        "variables": variables,
    }


def _txrx_outputs(outputs: OutputsSpec) -> OutputsSpec:
    variables: list[OutputVariableSpec] = []
    emitted_names: set[str] = set()
    for output_variable in outputs["variables"]:
        source_name = output_variable["name"]
        output_name = source_name
        if output_name not in _ACTIVE_TXRX_OUTPUT_VARIABLE_NAMES:
            continue
        if output_name in emitted_names:
            raise ValueError(f"TxRx output variable name collision (name={output_name!r})")
        variables.append({"name": output_name, "expression": output_variable["expression"]})
        emitted_names.add(output_name)
    missing_names = sorted(_ACTIVE_TXRX_OUTPUT_VARIABLE_NAMES.difference(emitted_names))
    if missing_names:
        raise ValueError(f"TxRx output spec is missing active variables (missing={missing_names})")
    return {
        "mode": "TxRx",
        "report_name": outputs["report_name"],
        "solution_name": outputs["solution_name"],
        "primary_sweep": outputs["primary_sweep"],
        "report_category": outputs["report_category"],
        "plot_type": outputs["plot_type"],
        "variables": variables,
    }


def _output_mode(outputs: OutputsSpec) -> str:
    if "mode" in outputs:
        raw_mode = outputs["mode"]
        if not isinstance(raw_mode, str):
            raise TypeError("outputs.mode must be string")
        if raw_mode == "":
            raise ValueError("outputs.mode must be non-empty string")
        return raw_mode
    return "RxOnly"


def _active_output_factory(outputs: OutputsSpec) -> OutputsSpec:
    mode = _output_mode(outputs)
    if mode == "TxRx":
        return _txrx_outputs(outputs)
    if mode == "RxOnly":
        return _rx_only_outputs(outputs)
    raise ValueError(f"unsupported outputs mode {mode!r} for type2 setup-ready")


def _modeled_role(*, entry: dict[str, object], context: str) -> str:
    if "role" not in entry:
        raise ValueError(f"{context} is missing required key 'role'")
    raw_role = entry["role"]
    if not isinstance(raw_role, str):
        raise TypeError(f"{context}.role must be str")
    if raw_role == "":
        raise ValueError(f"{context}.role must be non-empty")
    return raw_role


def _resolve_setup_branch(ledger: ValidatedStepLedger) -> str:
    output_mode = _output_mode(ledger["outputs"])
    modeled_entries = ledger["modeled_objects"]
    modeled_roles: list[str] = []
    for index, modeled_entry in enumerate(modeled_entries):
        role = _modeled_role(
            entry=modeled_entry["entry"],
            context=f"modeled_objects[{index}]",
        )
        modeled_roles.append(role)
    if _TX_OUTER_SINGLE_COIL_ROLE in modeled_roles:
        raise ValueError(
            "type2 setup-ready rejects inactive modeled role 'tx_outer_single_coil'; "
            "active setup supports rx_single_coil, tx_inner_single_coil, and passive tv_aluminum_plate only "
            f"(roles={modeled_roles})"
        )

    if output_mode == "RxOnly":
        if modeled_roles.count(_RX_SINGLE_COIL_ROLE) == 1 and all(
            role in {_RX_SINGLE_COIL_ROLE, _TX_INNER_SINGLE_COIL_ROLE, _TV_ALUMINUM_PLATE_ROLE}
            for role in modeled_roles
        ) and (
            modeled_roles.count(_TX_INNER_SINGLE_COIL_ROLE) <= 1
            and modeled_roles.count(_TV_ALUMINUM_PLATE_ROLE) <= 1
        ):
            return _SETUP_BRANCH_RX_SINGLE_READY
        if len(modeled_entries) == 1:
            raise ValueError(
                "type2 setup facade supports a single modeled role only for RX-only mode "
                f"(required_role={_RX_SINGLE_COIL_ROLE!r}, actual_role={modeled_roles[0]!r})"
            )
        raise ValueError(
            "type2 setup facade supports exactly one active 'rx_single_coil' plus optional "
            "'tx_inner_single_coil' entry for RX-only setup-ready orchestration "
            f"(roles={modeled_roles})"
        )

    if output_mode == "TxRx":
        allowed_txrx_roles = frozenset({_TX_INNER_SINGLE_COIL_ROLE, _RX_SINGLE_COIL_ROLE, _TV_ALUMINUM_PLATE_ROLE})
        if all(role in allowed_txrx_roles for role in modeled_roles) and (
            modeled_roles.count(_TX_INNER_SINGLE_COIL_ROLE) == 1
            and modeled_roles.count(_RX_SINGLE_COIL_ROLE) == 1
            and modeled_roles.count(_TV_ALUMINUM_PLATE_ROLE) <= 1
        ):
            return _SETUP_BRANCH_TXRX_READY
        raise ValueError(
            "type2 setup mode 'TxRx' supports only ['tx_inner_single_coil', 'rx_single_coil'] "
            "plus optional passive 'tv_aluminum_plate' "
            f"for setup-ready orchestration (roles={modeled_roles})"
        )

    raise ValueError(f"type2 setup mode is unsupported (mode={output_mode!r})")


def _txrx_imported_ledger(imported_ledger: Type2ImportedLedger) -> Type2ImportedLedger:
    tx_inner_modeled_objects = [
        entry
        for entry in imported_ledger["modeled_objects"]
        if _modeled_role(entry=entry, context="imported_ledger.modeled_objects[]")
        in {_TX_INNER_SINGLE_COIL_ROLE, _RX_SINGLE_COIL_ROLE}
    ]
    if len(tx_inner_modeled_objects) != 2:
        raise ValueError(
            "type2 TxRx setup requires exactly one tx_inner_single_coil and one rx_single_coil imported object "
            f"(actual={len(tx_inner_modeled_objects)})"
        )
    tx_roles = [
        _modeled_role(entry=entry, context="imported_ledger.modeled_objects[]")
        for entry in tx_inner_modeled_objects
    ]
    if tx_roles.count(_TX_INNER_SINGLE_COIL_ROLE) != 1 or tx_roles.count(_RX_SINGLE_COIL_ROLE) != 1:
        raise ValueError(
            "type2 TxRx setup requires exactly one tx_inner_single_coil and one rx_single_coil imported object "
            f"(roles={tx_roles})"
        )
    inactive_outer_roles = [
        _modeled_role(entry=entry, context="imported_ledger.modeled_objects[]")
        for entry in imported_ledger["modeled_objects"]
        if _modeled_role(entry=entry, context="imported_ledger.modeled_objects[]") == _TX_OUTER_SINGLE_COIL_ROLE
    ]
    if inactive_outer_roles:
        raise ValueError(
            "type2 TxRx setup rejects inactive tx_outer_single_coil imported objects "
            f"(actual={len(inactive_outer_roles)})"
        )
    return {
        "source_toml_path": imported_ledger["source_toml_path"],
        "source_step_ledger_path": imported_ledger["source_step_ledger_path"],
        "scene_step_path": imported_ledger["scene_step_path"],
        "seed": imported_ledger["seed"],
        "aedt_path": imported_ledger["aedt_path"],
        "imported_ledger_path": imported_ledger["imported_ledger_path"],
        "non_model_objects": imported_ledger["non_model_objects"],
        "modeled_objects": tx_inner_modeled_objects,
    }


def _rx_only_imported_ledger(imported_ledger: Type2ImportedLedger) -> Type2ImportedLedger:
    rx_modeled_objects = [
        entry
        for entry in imported_ledger["modeled_objects"]
        if _modeled_role(entry=entry, context="imported_ledger.modeled_objects[]") == _RX_SINGLE_COIL_ROLE
    ]
    if len(rx_modeled_objects) != 1:
        raise ValueError(
            "type2 RX-only setup requires exactly one imported rx_single_coil modeled object "
            f"(actual={len(rx_modeled_objects)})"
        )
    inactive_tx_roles = [
        _modeled_role(entry=entry, context="imported_ledger.modeled_objects[]")
        for entry in imported_ledger["modeled_objects"]
        if _modeled_role(entry=entry, context="imported_ledger.modeled_objects[]")
        in {_TX_INNER_SINGLE_COIL_ROLE, _TX_OUTER_SINGLE_COIL_ROLE}
    ]
    if inactive_tx_roles.count(_TX_OUTER_SINGLE_COIL_ROLE) > 0:
        raise ValueError(
            "type2 RX-only setup rejects inactive tx_outer_single_coil imported objects "
            f"(roles={inactive_tx_roles})"
        )
    return {
        "source_toml_path": imported_ledger["source_toml_path"],
        "source_step_ledger_path": imported_ledger["source_step_ledger_path"],
        "scene_step_path": imported_ledger["scene_step_path"],
        "seed": imported_ledger["seed"],
        "aedt_path": imported_ledger["aedt_path"],
        "imported_ledger_path": imported_ledger["imported_ledger_path"],
        "non_model_objects": imported_ledger["non_model_objects"],
        "modeled_objects": rx_modeled_objects,
    }


def _setup_ready_from_loaded_ledger_full(
    *,
    hfss: HfssSession,
    step_ledger_path: Path,
    output_aedt_path: Path,
    imported_ledger_path: Path,
    ledger: ValidatedStepLedger,
    design_variables: tuple[DesignVariableEntry, ...],
    run_aedt_design_validation: bool = True,
) -> Type2SetupReadyResult:
    _assign_design_variables(hfss, design_variables=design_variables)
    imported_ledger: Type2ImportedLedger = build_imported_ledger(
        hfss=hfss,
        step_ledger_path=step_ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        ledger=ledger,
    )
    rx_only_imported_ledger = _rx_only_imported_ledger(imported_ledger)
    mesh = assign_post_import_mesh(
        hfss=hfss,
        imported_modeled_objects=rx_only_imported_ledger["modeled_objects"],
    )
    em_policy = _setup_ready_policy(ledger)
    boundary = build_boundary(
        hfss=hfss,
        modeler=hfss.modeler,
        policy=em_policy,
    )
    ports = assign_type2_lumped_ports(
        hfss=hfss,
        modeler=hfss.modeler,
        imported_ledger=rx_only_imported_ledger,
    )
    em_input = build_type2_em_input(imported_ledger=rx_only_imported_ledger, ports=ports)
    groups = build_groups(em_input)
    series = build_series(groups)
    subtract = build_subtract(groups)
    sources = apply_sources_phase(hfss, ports)
    analysis = build_analysis(hfss, em_policy)
    post_templates = build_post_templates(hfss, _rx_only_outputs(ledger["outputs"]), ports)
    raise_on_false(
        hfss.change_validation_settings(
            entity_check_level="None",
            ignore_unclassified=False,
            skip_intersections=False,
        ),
        operation="change_validation_settings",
        context={
            "entity_check_level": "None",
            "ignore_unclassified": False,
            "skip_intersections": False,
        },
    )
    validation_result: EmPipelineResult = {
        "groups": groups,
        "series": series,
        "subtract": subtract,
        "boundary": boundary,
        "ports": ports,
        "sources": sources,
        "analysis": analysis,
        "post_templates": post_templates,
        "validation_report": {"ok": False, "gate": "pending", "message": "pending"},
    }
    validation_report = validate_pipeline(validation_result, em_policy)
    if run_aedt_design_validation:
        _validate_design(hfss)
    save_result = hfss.save_project(str(output_aedt_path))
    raise_on_false(save_result, operation="save_project", context={"path": str(output_aedt_path)})
    write_imported_ledger(imported_ledger_path=imported_ledger_path, imported_ledger=imported_ledger)
    return {
        "source_toml_path": imported_ledger["source_toml_path"],
        "source_step_ledger_path": imported_ledger["source_step_ledger_path"],
        "scene_step_path": imported_ledger["scene_step_path"],
        "seed": imported_ledger["seed"],
        "aedt_path": str(output_aedt_path),
        "imported_ledger_path": str(imported_ledger_path),
        "mesh": mesh,
        "boundary": boundary,
        "ports": ports,
        "sources": sources,
        "analysis": analysis,
        "validation_report": validation_report,
    }


def _setup_ready_from_loaded_ledger_by_branch(
    *,
    hfss: HfssSession,
    step_ledger_path: Path,
    output_aedt_path: Path,
    imported_ledger_path: Path,
    ledger: ValidatedStepLedger,
    design_variables: tuple[DesignVariableEntry, ...],
    setup_branch: str,
    run_aedt_design_validation: bool = True,
) -> Type2StepSetupFacadeResult:
    if setup_branch == _SETUP_BRANCH_RX_SINGLE_READY:
        return _setup_ready_from_loaded_ledger_full(
            hfss=hfss,
            step_ledger_path=step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            ledger=ledger,
            design_variables=design_variables,
            run_aedt_design_validation=run_aedt_design_validation,
        )
    if setup_branch == _SETUP_BRANCH_TXRX_READY:
        return _setup_ready_from_loaded_ledger_txrx(
            hfss=hfss,
            step_ledger_path=step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            ledger=ledger,
            design_variables=design_variables,
            run_aedt_design_validation=run_aedt_design_validation,
        )
    raise ValueError(f"type2 setup facade branch is unsupported (branch={setup_branch!r})")


def _setup_ready_from_loaded_ledger_txrx(
    *,
    hfss: HfssSession,
    step_ledger_path: Path,
    output_aedt_path: Path,
    imported_ledger_path: Path,
    ledger: ValidatedStepLedger,
    design_variables: tuple[DesignVariableEntry, ...],
    run_aedt_design_validation: bool = True,
) -> Type2SetupReadyResult:
    _assign_design_variables(hfss, design_variables=design_variables)
    imported_ledger: Type2ImportedLedger = build_imported_ledger(
        hfss=hfss,
        step_ledger_path=step_ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        ledger=ledger,
    )
    txrx_imported_ledger = _txrx_imported_ledger(imported_ledger)
    mesh = assign_post_import_mesh(
        hfss=hfss,
        imported_modeled_objects=txrx_imported_ledger["modeled_objects"],
    )
    em_policy = _setup_ready_policy(ledger)
    boundary = build_boundary(
        hfss=hfss,
        modeler=hfss.modeler,
        policy=em_policy,
    )
    ports = assign_type2_lumped_ports(
        hfss=hfss,
        modeler=hfss.modeler,
        imported_ledger=txrx_imported_ledger,
    )
    em_input = build_type2_em_input(imported_ledger=txrx_imported_ledger, ports=ports)
    groups = build_groups(em_input)
    series = build_series(groups)
    subtract = build_subtract(groups)
    sources = apply_sources_phase(hfss, ports)
    analysis = build_analysis(hfss, em_policy)
    post_templates = build_post_templates(hfss, _active_output_factory(ledger["outputs"]), ports)
    raise_on_false(
        hfss.change_validation_settings(
            entity_check_level="None",
            ignore_unclassified=False,
            skip_intersections=False,
        ),
        operation="change_validation_settings",
        context={
            "entity_check_level": "None",
            "ignore_unclassified": False,
            "skip_intersections": False,
        },
    )
    validation_result: EmPipelineResult = {
        "groups": groups,
        "series": series,
        "subtract": subtract,
        "boundary": boundary,
        "ports": ports,
        "sources": sources,
        "analysis": analysis,
        "post_templates": post_templates,
        "validation_report": {"ok": False, "gate": "pending", "message": "pending"},
    }
    validation_report = validate_pipeline(validation_result, em_policy)
    if run_aedt_design_validation:
        _validate_design(hfss)
    save_result = hfss.save_project(str(output_aedt_path))
    raise_on_false(save_result, operation="save_project", context={"path": str(output_aedt_path)})
    write_imported_ledger(imported_ledger_path=imported_ledger_path, imported_ledger=imported_ledger)
    return {
        "source_toml_path": imported_ledger["source_toml_path"],
        "source_step_ledger_path": imported_ledger["source_step_ledger_path"],
        "scene_step_path": imported_ledger["scene_step_path"],
        "seed": imported_ledger["seed"],
        "aedt_path": str(output_aedt_path),
        "imported_ledger_path": str(imported_ledger_path),
        "mesh": mesh,
        "boundary": boundary,
        "ports": ports,
        "sources": sources,
        "analysis": analysis,
        "validation_report": validation_report,
    }


def setup_type2_step_ledger(
    *,
    step_ledger_path: Path = DEFAULT_SOURCE_STEP_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
    design_name: str = DEFAULT_DESIGN_NAME,
    hfss_factory: HfssFactory = create_headless_hfss,
    design_variables: tuple[DesignVariableEntry, ...] = (),
) -> Type2StepSetupFacadeResult:
    checked_step_ledger_path = step_ledger_path.resolve(strict=False)
    ledger = load_step_ledger(checked_step_ledger_path)
    setup_branch = _resolve_setup_branch(ledger)
    output_aedt_path.parent.mkdir(parents=True, exist_ok=True)
    hfss = hfss_factory(design_name)
    try:
        return _setup_ready_from_loaded_ledger_by_branch(
            hfss=hfss,
            step_ledger_path=checked_step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            ledger=ledger,
            design_variables=design_variables,
            setup_branch=setup_branch,
        )
    finally:
        release_result = hfss.desktop_class.release_desktop(close_projects=True, close_on_exit=True)
        raise_on_false(
            release_result,
            operation="release_desktop",
            context={"close_projects": True, "close_on_exit": True},
        )


def setup_and_solve_type2_step_ledger(
    *,
    step_ledger_path: Path = DEFAULT_SOURCE_STEP_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
    design_name: str = DEFAULT_DESIGN_NAME,
    hfss_factory: HfssFactory = create_headless_hfss,
    design_variables: tuple[DesignVariableEntry, ...] = (),
) -> Type2SetupSolvedResult:
    checked_step_ledger_path = step_ledger_path.resolve(strict=False)
    ledger = load_step_ledger(checked_step_ledger_path)
    setup_branch = _resolve_setup_branch(ledger)
    output_aedt_path.parent.mkdir(parents=True, exist_ok=True)
    hfss = hfss_factory(design_name)
    try:
        setup_result = _setup_ready_from_loaded_ledger_by_branch(
            hfss=hfss,
            step_ledger_path=checked_step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            ledger=ledger,
            design_variables=design_variables,
            setup_branch=setup_branch,
        )
        em_solve = solve_type2_setup_ready_hfss(
            hfss,
            output_dir=output_aedt_path.parent,
        )
        save_result = hfss.save_project(str(output_aedt_path))
        raise_on_false(save_result, operation="save_project", context={"path": str(output_aedt_path)})
        return {
            "source_toml_path": setup_result["source_toml_path"],
            "source_step_ledger_path": setup_result["source_step_ledger_path"],
            "scene_step_path": setup_result["scene_step_path"],
            "seed": setup_result["seed"],
            "aedt_path": setup_result["aedt_path"],
            "imported_ledger_path": setup_result["imported_ledger_path"],
            "mesh": setup_result["mesh"],
            "boundary": setup_result["boundary"],
            "ports": setup_result["ports"],
            "sources": setup_result["sources"],
            "analysis": setup_result["analysis"],
            "validation_report": setup_result["validation_report"],
            "em_solve": em_solve,
        }
    finally:
        release_result = hfss.desktop_class.release_desktop(close_projects=True, close_on_exit=True)
        raise_on_false(
            release_result,
            operation="release_desktop",
            context={"close_projects": True, "close_on_exit": True},
        )


def setup_type2_step_ledger_into_hfss(
    *,
    hfss: HfssSession,
    step_ledger_path: Path = DEFAULT_SOURCE_STEP_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
    design_variables: tuple[DesignVariableEntry, ...] = (),
    run_aedt_design_validation: bool = True,
    close_projects_on_release: bool = False,
) -> Type2StepSetupFacadeResult:
    checked_step_ledger_path = step_ledger_path.resolve(strict=False)
    try:
        ledger = load_step_ledger(checked_step_ledger_path)
        setup_branch = _resolve_setup_branch(ledger)
        output_aedt_path.parent.mkdir(parents=True, exist_ok=True)
        prepare_attached_import_design(hfss)
        return _setup_ready_from_loaded_ledger_by_branch(
            hfss=hfss,
            step_ledger_path=checked_step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            ledger=ledger,
            design_variables=design_variables,
            setup_branch=setup_branch,
            run_aedt_design_validation=run_aedt_design_validation,
        )
    finally:
        release_result = hfss.desktop_class.release_desktop(
            close_projects=close_projects_on_release,
            close_on_exit=False,
        )
        raise_on_false(
            release_result,
            operation="release_desktop",
            context={"close_projects": close_projects_on_release, "close_on_exit": False},
        )


__all__ = [
    "DEFAULT_DESIGN_NAME",
    "DEFAULT_IMPORTED_LEDGER_PATH",
    "DEFAULT_OUTPUT_AEDT_PATH",
    "DEFAULT_SOURCE_STEP_LEDGER_PATH",
    "HfssFactory",
    "Type2PlateStackPortReadyResult",
    "Type2StepSetupFacadeResult",
    "Type2SetupSolvedResult",
    "Type2SetupReadyResult",
    "setup_and_solve_type2_step_ledger",
    "setup_type2_step_ledger",
    "setup_type2_step_ledger_into_hfss",
]

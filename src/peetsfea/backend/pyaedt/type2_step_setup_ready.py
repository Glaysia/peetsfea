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
from peetsfea.types.manifest import EmPolicy, EmPorts

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SOURCE_STEP_LEDGER_PATH = REPO_ROOT / "run" / "step" / "type2" / "type2_step_ledger.json"
DEFAULT_IMPORTED_LEDGER_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_import" / "type2_imported_ledger.json"
DEFAULT_OUTPUT_AEDT_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_setup_ready" / "type2_setup_ready.aedt"
DEFAULT_DESIGN_NAME = "type2_step_setup_ready"
_COIL_ROLE_PAIR: frozenset[str] = frozenset({"tx_single_coil", "rx_single_coil"})
_PLATE_STACK_ROLE_PAIR: frozenset[str] = frozenset({"tx_plate_stack", "rx_plate_stack"})
_MIXED_TX_PLATE_STACK_RX_SINGLE_ROLE_PAIR: frozenset[str] = frozenset(
    {"tx_plate_stack", "rx_single_coil"}
)
_TX_RECT_VOID_COLUMNS_RX_SINGLE_ROLE_PAIR: frozenset[str] = frozenset(
    {"tx_rect_void_columns", "rx_single_coil"}
)
_ALL_SUPPORTED_ROLE_PAIRS: frozenset[str] = frozenset(
    {*_COIL_ROLE_PAIR, *_PLATE_STACK_ROLE_PAIR, *_TX_RECT_VOID_COLUMNS_RX_SINGLE_ROLE_PAIR}
)
_RX_SINGLE_COIL_ROLE: str = "rx_single_coil"
_SETUP_BRANCH_COIL_FULL_READY = "coil_full_setup_ready"
_SETUP_BRANCH_PLATE_STACK_FULL_READY = "plate_stack_full_setup_ready"
_SETUP_BRANCH_MIXED_TX_PLATE_STACK_RX_SINGLE_READY = "mixed_tx_plate_stack_rx_single_ready"
_SETUP_BRANCH_TX_RECT_VOID_COLUMNS_RX_SINGLE_READY = "tx_rect_void_columns_rx_single_ready"
_SETUP_BRANCH_RX_SINGLE_READY = "rx_single_ready"

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
    modeled_entries = ledger["modeled_objects"]
    if len(modeled_entries) == 1:
        only_role = _modeled_role(
            entry=modeled_entries[0]["entry"],
            context="modeled_objects[0]",
        )
        if only_role != _RX_SINGLE_COIL_ROLE:
            raise ValueError(
                "type2 setup facade supports a single modeled role only for RX-only mode "
                f"(required_role={_RX_SINGLE_COIL_ROLE!r}, actual_role={only_role!r})"
            )
        return _SETUP_BRANCH_RX_SINGLE_READY
    if len(modeled_entries) != 2:
        raise ValueError(
            "type2 setup facade requires exactly two modeled_objects entries for paired setup "
            "or one rx_single_coil entry for RX-only "
            f"(actual={len(modeled_entries)})"
        )
    modeled_roles: list[str] = []
    for index, modeled_entry in enumerate(modeled_entries):
        modeled_roles.append(
            _modeled_role(
                entry=modeled_entry["entry"],
                context=f"modeled_objects[{index}]",
            )
        )
    role_set = frozenset(modeled_roles)
    if len(role_set) != 2:
        raise ValueError(
            "type2 setup facade requires an exact tx/rx role pair without duplicates "
            f"(roles={modeled_roles})"
        )
    unsupported_roles = role_set.difference(_ALL_SUPPORTED_ROLE_PAIRS)
    if unsupported_roles:
        raise ValueError(
            "type2 setup facade encountered unsupported modeled roles "
            f"(roles={modeled_roles}, unsupported={sorted(unsupported_roles)})"
        )
    if role_set == _COIL_ROLE_PAIR:
        return _SETUP_BRANCH_COIL_FULL_READY
    if role_set == _PLATE_STACK_ROLE_PAIR:
        return _SETUP_BRANCH_PLATE_STACK_FULL_READY
    if role_set == _MIXED_TX_PLATE_STACK_RX_SINGLE_ROLE_PAIR:
        return _SETUP_BRANCH_MIXED_TX_PLATE_STACK_RX_SINGLE_READY
    if role_set == _TX_RECT_VOID_COLUMNS_RX_SINGLE_ROLE_PAIR:
        return _SETUP_BRANCH_TX_RECT_VOID_COLUMNS_RX_SINGLE_READY
    raise ValueError(
        "type2 setup facade rejects mixed modeled role families; expected exact pair "
        "['tx_single_coil', 'rx_single_coil'] or ['tx_plate_stack', 'rx_plate_stack'] "
        "or ['tx_plate_stack', 'rx_single_coil'] or ['tx_rect_void_columns', 'rx_single_coil'] "
        f"(roles={modeled_roles})"
    )


def _setup_ready_from_loaded_ledger_full(
    *,
    hfss: HfssSession,
    step_ledger_path: Path,
    output_aedt_path: Path,
    imported_ledger_path: Path,
    ledger: ValidatedStepLedger,
    design_variables: tuple[DesignVariableEntry, ...],
) -> Type2SetupReadyResult:
    _assign_design_variables(hfss, design_variables=design_variables)
    imported_ledger: Type2ImportedLedger = build_imported_ledger(
        hfss=hfss,
        step_ledger_path=step_ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        ledger=ledger,
    )
    mesh = assign_post_import_mesh(
        hfss=hfss,
        imported_modeled_objects=imported_ledger["modeled_objects"],
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
        imported_ledger=imported_ledger,
    )
    em_input = build_type2_em_input(imported_ledger=imported_ledger, ports=ports)
    groups = build_groups(em_input)
    series = build_series(groups)
    subtract = build_subtract(groups)
    sources = apply_sources_phase(hfss, ports)
    analysis = build_analysis(hfss, em_policy)
    post_templates = build_post_templates(hfss, ledger["outputs"], ports)
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
) -> Type2StepSetupFacadeResult:
    if setup_branch == _SETUP_BRANCH_COIL_FULL_READY:
        return _setup_ready_from_loaded_ledger_full(
            hfss=hfss,
            step_ledger_path=step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            ledger=ledger,
            design_variables=design_variables,
        )
    if setup_branch == _SETUP_BRANCH_PLATE_STACK_FULL_READY:
        return _setup_ready_from_loaded_ledger_full(
            hfss=hfss,
            step_ledger_path=step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            ledger=ledger,
            design_variables=design_variables,
        )
    if setup_branch == _SETUP_BRANCH_MIXED_TX_PLATE_STACK_RX_SINGLE_READY:
        return _setup_ready_from_loaded_ledger_full(
            hfss=hfss,
            step_ledger_path=step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            ledger=ledger,
            design_variables=design_variables,
        )
    if setup_branch == _SETUP_BRANCH_TX_RECT_VOID_COLUMNS_RX_SINGLE_READY:
        return _setup_ready_from_loaded_ledger_full(
            hfss=hfss,
            step_ledger_path=step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            ledger=ledger,
            design_variables=design_variables,
        )
    if setup_branch == _SETUP_BRANCH_RX_SINGLE_READY:
        return _setup_ready_from_loaded_ledger_full(
            hfss=hfss,
            step_ledger_path=step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            ledger=ledger,
            design_variables=design_variables,
        )
    raise ValueError(f"type2 setup facade branch is unsupported (branch={setup_branch!r})")


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


def setup_type2_step_ledger_into_hfss(
    *,
    hfss: HfssSession,
    step_ledger_path: Path = DEFAULT_SOURCE_STEP_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
    design_variables: tuple[DesignVariableEntry, ...] = (),
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
        )
    finally:
        release_result = hfss.desktop_class.release_desktop(close_projects=False, close_on_exit=False)
        raise_on_false(
            release_result,
            operation="release_desktop",
            context={"close_projects": False, "close_on_exit": False},
        )


__all__ = [
    "DEFAULT_DESIGN_NAME",
    "DEFAULT_IMPORTED_LEDGER_PATH",
    "DEFAULT_OUTPUT_AEDT_PATH",
    "DEFAULT_SOURCE_STEP_LEDGER_PATH",
    "HfssFactory",
    "Type2PlateStackPortReadyResult",
    "Type2StepSetupFacadeResult",
    "Type2SetupReadyResult",
    "setup_type2_step_ledger",
    "setup_type2_step_ledger_into_hfss",
]

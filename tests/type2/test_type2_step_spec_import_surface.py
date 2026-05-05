from __future__ import annotations

import importlib
from types import ModuleType

import pytest

from peetsfea.spec.outputs import parse_outputs_table
from peetsfea.type2_step_spec_modeled import parse_modeled_object


_EXPECTED_PUBLIC_SURFACE: set[str] = {
    "ModeledObjectSpec",
    "ModeledObjectRole",
    "ModeledPlateStackRole",
    "ModeledPlateStackSpec",
    "ModeledRxPlateStackSpec",
    "ModeledRxSingleCoilSpec",
    "ModeledSingleCoilRole",
    "ModeledSingleCoilCommonSpec",
    "ModeledSingleCoilSpec",
    "ModeledTxPlateStackSpec",
    "ModeledTxSingleCoilSpec",
    "ModeledTxRectVoidColumnsSpec",
    "Type2ConstraintComparisonOperator",
    "Type2ConstraintComparableRef",
    "Type2ConstraintFuncRef",
    "Type2ConstraintPathRef",
    "Type2ConstraintRule",
    "Type2ConstraintValueRef",
    "NonModelBoxSpec",
    "NonModelDerivedSpec",
    "NonModelTxRegionActualSpec",
    "NonModelTxRegionActualStackSpaceSpec",
    "Point3",
    "RangeSpec",
    "Type2SimulationPolicy",
    "Type2StepSpec",
    "load_type2_step_spec",
    "modeled_object_id_for_role",
    "modeled_plane_for_role",
    "placement_owner_id_for_role",
    "resolve_modeled_plate_stack_metal_fill_factor",
    "resolve_modeled_plate_stack_turn_count",
    "resolve_modeled_plate_stack_z_usage_ratio",
    "resolve_modeled_plate_stack_y_usage_ratio",
    "resolve_modeled_tx_array_x_usage_ratio",
    "resolve_modeled_tx_coil_count",
    "resolve_modeled_underlay_gap_mm",
    "resolve_modeled_underlay_repeat_count",
    "resolve_modeled_wall_parallel_stack_present",
    "resolve_non_model_tx_region_actual_stack_space_tilt_enabled",
    "render_tx_rect_void_toml",
}

_EXPECTED_SURFACE_ORIGINS: dict[str, str] = {
    "modeled_object_id_for_role": "peetsfea.type2_step_spec_types",
    "modeled_plane_for_role": "peetsfea.type2_step_spec_types",
    "placement_owner_id_for_role": "peetsfea.type2_step_spec_types",
    "render_tx_rect_void_toml": "peetsfea.type2_step_spec_modeled",
    "resolve_modeled_plate_stack_metal_fill_factor": "peetsfea.type2_step_spec_sampling",
    "resolve_modeled_plate_stack_turn_count": "peetsfea.type2_step_spec_sampling",
    "resolve_modeled_plate_stack_z_usage_ratio": "peetsfea.type2_step_spec_sampling",
    "resolve_modeled_plate_stack_y_usage_ratio": "peetsfea.type2_step_spec_sampling",
    "resolve_modeled_tx_array_x_usage_ratio": "peetsfea.type2_step_spec_sampling",
    "resolve_modeled_tx_coil_count": "peetsfea.type2_step_spec_sampling",
    "resolve_modeled_underlay_gap_mm": "peetsfea.type2_step_spec_sampling",
    "resolve_modeled_underlay_repeat_count": "peetsfea.type2_step_spec_sampling",
    "resolve_modeled_wall_parallel_stack_present": "peetsfea.type2_step_spec_sampling",
    "resolve_non_model_tx_region_actual_stack_space_tilt_enabled": "peetsfea.type2_step_spec_sampling",
}


def _load_type2_step_spec_module() -> ModuleType:
    try:
        return importlib.import_module("peetsfea.type2_step_spec")
    except Exception as exc:
        raise AssertionError("failed to import peetsfea.type2_step_spec facade") from exc


@pytest.mark.parametrize("expected_name", sorted(_EXPECTED_PUBLIC_SURFACE))
def test_type2_step_spec_exports_exact_surface(expected_name: str) -> None:
    type2_step_spec = _load_type2_step_spec_module()
    assert hasattr(type2_step_spec, "__all__"), "type2_step_spec facade must define __all__"
    assert expected_name in type2_step_spec.__all__, f"missing exported symbol {expected_name}"


def test_type2_step_spec_exports_no_unexpected_public_surface() -> None:
    type2_step_spec = _load_type2_step_spec_module()
    assert hasattr(type2_step_spec, "__all__"), "type2_step_spec facade must define __all__"
    assert (
        set(type2_step_spec.__all__) == _EXPECTED_PUBLIC_SURFACE
    ), "type2_step_spec facade public import surface drifted"


@pytest.mark.parametrize("name,expected_module", sorted(_EXPECTED_SURFACE_ORIGINS.items()))
def test_type2_step_spec_public_surface_paths(name: str, expected_module: str) -> None:
    type2_step_spec = _load_type2_step_spec_module()
    symbol = getattr(type2_step_spec, name)
    actual_module = getattr(symbol, "__module__")
    assert actual_module == expected_module, f"{name} should come from {expected_module}, got {actual_module}"


def test_outputs_parser_accepts_rx_only_variable_contract() -> None:
    outputs = parse_outputs_table(
        {
            "mode": "RxOnly",
            "report_name": "Output Variables Table1",
            "solution_name": "Setup1 : LastAdaptive",
            "primary_sweep": "Freq",
            "report_category": "Terminal Solution Data",
            "plot_type": "Data Table",
            "variables": [
                {"name": "Lrx_uH", "expression": "im(Zt(RX_TML,RX_TML))/2/pi/freq*1e6"},
                {"name": "eta_rx_accept_ratio", "expression": "1-mag(S(RX_TML,RX_TML))*mag(S(RX_TML,RX_TML))"},
            ],
        },
        context="outputs",
    )

    assert outputs["variables"][0]["name"] == "Lrx_uH"


def test_outputs_parser_accepts_txrx_variable_contract() -> None:
    outputs = parse_outputs_table(
        {
            "mode": "TxRx",
            "report_name": "Output Variables Table1",
            "solution_name": "Setup1 : LastAdaptive",
            "primary_sweep": "Freq",
            "report_category": "Terminal Solution Data",
            "plot_type": "Data Table",
            "variables": [
                {"name": "Ltx_uH", "expression": "im(Zt(TX_TML,TX_TML))/2/pi/freq*1e6"},
                {"name": "Lrx_uH", "expression": "im(Zt(RX_TML,RX_TML))/2/pi/freq*1e6"},
                {"name": "M_uH", "expression": "abs(im(Zt(TX_TML,RX_TML))/2/pi/freq*1e6)"},
                {"name": "k_ratio", "expression": "M_uH/sqrt(Ltx_uH*Lrx_uH)"},
                {"name": "Qtx_ratio", "expression": "im(Zt(TX_TML,TX_TML))/re(Zt(TX_TML,TX_TML))"},
                {"name": "Qrx_ratio", "expression": "im(Zt(RX_TML,RX_TML))/re(Zt(RX_TML,RX_TML))"},
                {"name": "FOM_ratio", "expression": "k_ratio*sqrt(Qtx_ratio*Qrx_ratio)"},
                {"name": "Rtx_ac_ohm", "expression": "re(Zt(TX_TML,TX_TML))"},
                {"name": "Rrx_ac_ohm", "expression": "re(Zt(RX_TML,RX_TML))"},
                {"name": "Xtx_ohm", "expression": "im(Zt(TX_TML,TX_TML))"},
                {"name": "Xrx_ohm", "expression": "im(Zt(RX_TML,RX_TML))"},
                {"name": "M_over_Ltx_ratio", "expression": "M_uH/Ltx_uH"},
                {"name": "M_over_Lrx_ratio", "expression": "M_uH/Lrx_uH"},
                {"name": "Gtx_S", "expression": "re(Yt(TX_TML,TX_TML))"},
                {"name": "Btx_S", "expression": "im(Yt(TX_TML,TX_TML))"},
                {"name": "Grx_S", "expression": "re(Yt(RX_TML,RX_TML))"},
                {"name": "Brx_S", "expression": "im(Yt(RX_TML,RX_TML))"},
                {"name": "S11_mag_ratio", "expression": "mag(S(TX_TML,TX_TML))"},
                {"name": "S21_mag_ratio", "expression": "mag(S(TX_TML,RX_TML))"},
                {"name": "S21_phase_deg", "expression": "ang_deg_val(S(TX_TML,RX_TML))"},
                {"name": "S22_mag_ratio", "expression": "mag(S(RX_TML,RX_TML))"},
                {"name": "eta_s21_power_ratio", "expression": "S21_mag_ratio*S21_mag_ratio"},
                {"name": "eta_tx_accept_ratio", "expression": "1-S11_mag_ratio*S11_mag_ratio"},
                {"name": "eta_rx_accept_ratio", "expression": "1-S22_mag_ratio*S22_mag_ratio"},
                {"name": "eta_match_product_ratio", "expression": "eta_tx_accept_ratio*eta_rx_accept_ratio"},
                {"name": "eta_s21_from_tx_accept_ratio", "expression": "eta_s21_power_ratio/eta_tx_accept_ratio"},
                {"name": "eta_s21_from_rx_accept_ratio", "expression": "eta_s21_power_ratio/eta_rx_accept_ratio"},
                {"name": "eta_s21_two_sided_norm_ratio", "expression": "eta_s21_power_ratio/(eta_tx_accept_ratio*eta_rx_accept_ratio)"},
                {"name": "eta_fom_max_ratio", "expression": "(FOM_ratio*FOM_ratio)/((1+sqrt(1+FOM_ratio*FOM_ratio))*(1+sqrt(1+FOM_ratio*FOM_ratio)))"},
            ],
        },
        context="outputs",
    )

    assert outputs["variables"][-1]["name"] == "eta_fom_max_ratio"


def test_outputs_parser_rejects_unknown_variable_in_txrx_mode() -> None:
    with pytest.raises(ValueError, match=r"outputs\.variables\[0\]\.name is not supported for TxRx"):
        parse_outputs_table(
            {
                "mode": "TxRx",
                "report_name": "Output Variables Table1",
                "solution_name": "Setup1 : LastAdaptive",
                "primary_sweep": "Freq",
                "report_category": "Terminal Solution Data",
                "plot_type": "Data Table",
                "variables": [{"name": "Srx_self_mag_ratio", "expression": "mag(S(RX_TML,RX_TML))"}],
            },
            context="outputs",
        )


def test_outputs_parser_rejects_tx_variable_in_rx_only_mode() -> None:
    with pytest.raises(
        ValueError,
        match=r"outputs\.variables\[0\]\.name is not supported for RxOnly \(actual='Ltx_uH'\)",
    ):
        parse_outputs_table(
            {
                "mode": "RxOnly",
                "report_name": "Output Variables Table1",
                "solution_name": "Setup1 : LastAdaptive",
                "primary_sweep": "Freq",
                "report_category": "Terminal Solution Data",
                "plot_type": "Data Table",
                "variables": [{"name": "Ltx_uH", "expression": "im\\(Zt\\(TX_TML,TX_TML\\)\\)"}],
            },
            context="outputs",
        )


def test_active_modeled_parser_rejects_tx_role() -> None:
    with pytest.raises(
        ValueError,
        match=r"modeled_objects\[0\]\.role is unsupported in active RxOnly type2 mode \(actual='tx_plate_stack'\)",
    ):
        parse_modeled_object(
            {"role": "tx_plate_stack"},
            index=0,
            seen_object_ids=set(),
            non_model_specs_by_id={},
        )

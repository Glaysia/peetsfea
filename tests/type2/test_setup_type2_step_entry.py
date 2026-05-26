from __future__ import annotations

from pathlib import Path
import tomllib
from typing import cast

import pytest

from peetsfea.spec.outputs import ACTIVE_OUTPUT_VARIABLE_NAMES_BY_MODE
from peetsfea.type2_spec_tools import type2_sampled_owner_paths

_TX_MODELED_ROLES = {"tx_single_coil", "tx_rect_void_columns", "tx_plate_stack"}
_TX_SAMPLED_OWNER_IDS = {"tx_region_actual", "tx_region_actual_stack_space"}
_FIXED_TX_REGION_ORIGIN_XYZ = [0.0, -600.0, 0.0]
_FIXED_TX_REGION_SIZE_XYZ = [720.0, 1200.0, 90.0]
_SAMPLED_TX_REGION_ORIGIN_XYZ = [0.0, -600.0, 0.0]
_SAMPLED_TX_REGION_SIZE_XYZ = [720.0, 1200.0, 90.0]
_FIXED_TX_REGION_Z_GAP_RANGE = (False, 80.0, 80.0, 1)
_SAMPLED_TX_REGION_Z_GAP_RANGE = (False, 45.0, 130.0, 17)
_FIXED_TX_REFERENCE_LINE_RATIOS = (0.99, 0.8373223833460517, 0.9641454961430692)
_SAMPLED_TX_REFERENCE_LINE_RANGES = (
    (0.99, 0.99, 1),
    (0.8373223833460517, 0.8373223833460517, 1),
    (0.9641454961430692, 0.9641454961430692, 1),
)
_TV_ALUMINUM_PLATE_OBJECT_ID = "tv_aluminum_plate"
_TV_ALUMINUM_PLATE_ROLE = "tv_aluminum_plate"
_TX_REGION_Z_GAP_OWNER_PATH = "non_model_objects.tx_region.z_gap_from_rx_plane_mm"
_TV_ALUMINUM_PLATE_SHEET_PRESENT_OWNER_PATH = "modeled_objects.tv_aluminum_plate.sheet_present"
_TV_ALUMINUM_PLATE_THICKNESS_MM = 0.04
_FIXED_TV_ALUMINUM_PLATE_SHEET_PRESENT_RANGE = [True, 0, 0, 1]
_SAMPLED_TV_ALUMINUM_PLATE_SHEET_PRESENT_RANGE = [True, 0, 0, 1]
_SAMPLED_TYPE2_OWNER_COUNT = 15
_FIXED_TX_TURN_QCOUNT_RANGE = [True, 4, 4, 1]
_FIXED_RX_TURN_QCOUNT_RANGE = [True, 4, 4, 1]
_SAMPLED_TX_TURN_QCOUNT_RANGE = [True, 4, 12, 9]
_SAMPLED_RX_TURN_QCOUNT_RANGE = [True, 4, 12, 9]
_FIXED_TX_TERMINAL_START_RANGE = [True, 1, 1, 1]
_FIXED_RX_TERMINAL_START_RANGE = [True, 0, 0, 1]
_SAMPLED_TERMINAL_START_RANGE = [True, 0, 3, 4]
_FIXED_TX_VOID_STACK_PRESENT_RANGE = [True, 1, 1, 1]
_FIXED_RX_VOID_STACK_PRESENT_RANGE = [True, 0, 0, 1]
_SAMPLED_VOID_STACK_PRESENT_RANGE = [True, 0, 1, 2]
_EXPECTED_SAMPLED_OWNER_PATHS = (
    "non_model_objects.tx_region.z_gap_from_rx_plane_mm",
    "modeled_objects.tx_inner_rect_void_coil.x_ratio",
    "modeled_objects.tx_inner_rect_void_coil.y_ratio",
    "modeled_objects.tx_inner_rect_void_coil.turn_qcount",
    "modeled_objects.tx_inner_rect_void_coil.void_factor",
    "modeled_objects.tx_inner_rect_void_coil.metal_fill_factor",
    "modeled_objects.tx_inner_rect_void_coil.terminal_start",
    "modeled_objects.tx_inner_rect_void_coil.void_stack_present",
    "modeled_objects.rx_rect_void_coil.x_ratio",
    "modeled_objects.rx_rect_void_coil.y_ratio",
    "modeled_objects.rx_rect_void_coil.turn_qcount",
    "modeled_objects.rx_rect_void_coil.void_factor",
    "modeled_objects.rx_rect_void_coil.metal_fill_factor",
    "modeled_objects.rx_rect_void_coil.terminal_start",
    "modeled_objects.rx_rect_void_coil.void_stack_present",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _example_payload(example_name: str) -> dict[str, object]:
    path = _repo_root() / "examples" / example_name
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _tables(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    raw_tables = payload[key]
    assert isinstance(raw_tables, list)
    tables: list[dict[str, object]] = []
    for raw_table in raw_tables:
        assert isinstance(raw_table, dict)
        tables.append(cast(dict[str, object], raw_table))
    return tables


def _output_variables(payload: dict[str, object]) -> list[dict[str, object]]:
    raw_outputs = payload["outputs"]
    assert isinstance(raw_outputs, dict)
    outputs = cast(dict[str, object], raw_outputs)
    raw_variables = outputs["variables"]
    assert isinstance(raw_variables, list)
    variables: list[dict[str, object]] = []
    for raw_variable in raw_variables:
        assert isinstance(raw_variable, dict)
        variables.append(cast(dict[str, object], raw_variable))
    return variables


def _tx_reference_line_ratio_range(payload: dict[str, object], ratio_name: str) -> tuple[bool, float, float, int]:
    tx_region = next(table for table in _tables(payload, "non_model_objects") if table["id"] == "tx_region")
    raw_reference_line = tx_region["tx_reference_line"]
    assert isinstance(raw_reference_line, dict)
    reference_line = cast(dict[str, object], raw_reference_line)
    raw_ratio = reference_line[ratio_name]
    assert isinstance(raw_ratio, dict)
    ratio = cast(dict[str, object], raw_ratio)
    raw_range = ratio["range"]
    assert isinstance(raw_range, list)
    assert len(raw_range) == 4
    raw_is_integer, raw_start, raw_end, raw_count = raw_range
    assert isinstance(raw_is_integer, bool)
    assert isinstance(raw_start, float)
    assert isinstance(raw_end, float)
    assert isinstance(raw_count, int)
    return (raw_is_integer, raw_start, raw_end, raw_count)


def _tx_region_z_gap_range(payload: dict[str, object]) -> tuple[bool, float, float, int]:
    tx_region = next(table for table in _tables(payload, "non_model_objects") if table["id"] == "tx_region")
    raw_z_gap = tx_region["z_gap_from_rx_plane_mm"]
    assert isinstance(raw_z_gap, dict)
    z_gap = cast(dict[str, object], raw_z_gap)
    raw_range = z_gap["range"]
    assert isinstance(raw_range, list)
    assert len(raw_range) == 4
    raw_is_integer, raw_start, raw_end, raw_count = raw_range
    assert isinstance(raw_is_integer, bool)
    assert isinstance(raw_start, float)
    assert isinstance(raw_end, float)
    assert isinstance(raw_count, int)
    return (raw_is_integer, raw_start, raw_end, raw_count)


def _raw_table_list(payload: dict[str, object], key: str) -> list[object]:
    raw_tables = payload[key]
    assert isinstance(raw_tables, list)
    return raw_tables


def _raw_output_variable_list(payload: dict[str, object]) -> list[object]:
    raw_outputs = payload["outputs"]
    assert isinstance(raw_outputs, dict)
    outputs = cast(dict[str, object], raw_outputs)
    raw_variables = outputs["variables"]
    assert isinstance(raw_variables, list)
    return raw_variables


def _assert_txrx_payload(payload: dict[str, object], *, example_name: str) -> None:
    outputs = cast(dict[str, object], payload["outputs"])
    assert outputs["mode"] == "TxRx"

    variables = _output_variables(payload)
    names = tuple(cast(str, variable["name"]) for variable in variables)
    expressions = tuple(cast(str, variable["expression"]) for variable in variables)
    assert len(names) == len(ACTIVE_OUTPUT_VARIABLE_NAMES_BY_MODE["TxRx"])
    assert frozenset(names) == ACTIVE_OUTPUT_VARIABLE_NAMES_BY_MODE["TxRx"]
    assert any("TX_TML" in expression for expression in expressions)
    assert any("RX_TML" in expression for expression in expressions)

    modeled_objects = _tables(payload, "modeled_objects")
    modeled_roles = tuple(cast(str, table["role"]) for table in modeled_objects)
    assert len(modeled_roles) == 3
    assert frozenset(modeled_roles) == {"tx_inner_single_coil", "rx_single_coil", _TV_ALUMINUM_PLATE_ROLE}
    assert not _TX_MODELED_ROLES.intersection(modeled_roles)
    modeled_by_id = {cast(str, table["object_id"]): table for table in modeled_objects}
    tx_inner = modeled_by_id["tx_inner_rect_void_coil"]
    rx = modeled_by_id["rx_rect_void_coil"]
    assert tx_inner["role"] == "tx_inner_single_coil"
    for coil in (tx_inner, rx):
        assert "x_ratio" in coil
        assert "y_ratio" in coil
        assert "turn_qcount" in coil
        assert "void_factor" in coil
        assert "terminal_start" in coil
        assert "void_stack_present" in coil
        assert "outer_x_usage_ratio" not in coil
        assert "outer_y_usage_ratio" not in coil
        assert "turn_count" not in coil
        assert "void_usage_ratio" not in coil
        assert "terminal_path" not in coil
    assert cast(dict[str, object], tx_inner["underlay_repeat_count"])["range"] == [True, 1, 1, 1]
    if example_name == "type2_fixed.toml":
        assert cast(dict[str, object], tx_inner["turn_qcount"])["range"] == _FIXED_TX_TURN_QCOUNT_RANGE
        assert cast(dict[str, object], rx["turn_qcount"])["range"] == _FIXED_RX_TURN_QCOUNT_RANGE
        assert cast(dict[str, object], tx_inner["terminal_start"])["range"] == _FIXED_TX_TERMINAL_START_RANGE
        assert cast(dict[str, object], rx["terminal_start"])["range"] == _FIXED_RX_TERMINAL_START_RANGE
        assert cast(dict[str, object], tx_inner["void_stack_present"])["range"] == _FIXED_TX_VOID_STACK_PRESENT_RANGE
        assert cast(dict[str, object], rx["void_stack_present"])["range"] == _FIXED_RX_VOID_STACK_PRESENT_RANGE
        assert cast(dict[str, object], tx_inner["underlay_pet_psa_thickness_mm"])["range"] == [False, 6.0, 6.0, 1]
        assert cast(dict[str, object], tx_inner["underlay_ferrite_thickness_mm"])["range"] == [False, 6.0, 6.0, 1]
    elif example_name == "type2_sweep.toml":
        assert cast(dict[str, object], tx_inner["turn_qcount"])["range"] == _SAMPLED_TX_TURN_QCOUNT_RANGE
        assert cast(dict[str, object], rx["turn_qcount"])["range"] == _SAMPLED_RX_TURN_QCOUNT_RANGE
        assert cast(dict[str, object], tx_inner["terminal_start"])["range"] == _SAMPLED_TERMINAL_START_RANGE
        assert cast(dict[str, object], rx["terminal_start"])["range"] == _SAMPLED_TERMINAL_START_RANGE
        assert cast(dict[str, object], tx_inner["void_stack_present"])["range"] == _SAMPLED_VOID_STACK_PRESENT_RANGE
        assert cast(dict[str, object], rx["void_stack_present"])["range"] == _SAMPLED_VOID_STACK_PRESENT_RANGE
        assert cast(dict[str, object], tx_inner["underlay_pet_psa_thickness_mm"])["range"] == [False, 6.0, 6.0, 1]
        assert cast(dict[str, object], tx_inner["underlay_ferrite_thickness_mm"])["range"] == [False, 6.0, 6.0, 1]
    else:
        raise AssertionError(f"unsupported type2 example {example_name!r}")

    non_model_ids = tuple(cast(str, table["id"]) for table in _tables(payload, "non_model_objects"))
    assert "tx_region" in non_model_ids
    assert "tx_inner_region" not in non_model_ids
    assert "rx_region_max" in non_model_ids
    assert _TV_ALUMINUM_PLATE_OBJECT_ID not in non_model_ids
    assert not _TX_SAMPLED_OWNER_IDS.intersection(non_model_ids)
    tv_aluminum_plate = modeled_by_id[_TV_ALUMINUM_PLATE_OBJECT_ID]
    assert tv_aluminum_plate["role"] == _TV_ALUMINUM_PLATE_ROLE
    assert tv_aluminum_plate["primitive"] == "sheet"
    assert tv_aluminum_plate["material"] == "aluminum"
    assert tv_aluminum_plate["model_state"] is True
    assert tv_aluminum_plate["source_non_model_object_id"] == "tv"
    assert tv_aluminum_plate["face"] == "+x"
    assert tv_aluminum_plate["thickness_mm"] == _TV_ALUMINUM_PLATE_THICKNESS_MM
    sheet_present = cast(dict[str, object], tv_aluminum_plate["sheet_present"])
    if example_name == "type2_fixed.toml":
        assert sheet_present["range"] == _FIXED_TV_ALUMINUM_PLATE_SHEET_PRESENT_RANGE
    elif example_name == "type2_sweep.toml":
        assert sheet_present["range"] == _SAMPLED_TV_ALUMINUM_PLATE_SHEET_PRESENT_RANGE
    else:
        raise AssertionError(f"unsupported type2 example {example_name!r}")


def _assert_tx_region_payload(payload: dict[str, object], *, example_name: str) -> None:
    tx_region = next(table for table in _tables(payload, "non_model_objects") if table["id"] == "tx_region")
    z_gap_range = _tx_region_z_gap_range(payload)
    if example_name == "type2_fixed.toml":
        assert tx_region["origin_xyz"] == _FIXED_TX_REGION_ORIGIN_XYZ
        assert tx_region["size_xyz"] == _FIXED_TX_REGION_SIZE_XYZ
        assert z_gap_range == _FIXED_TX_REGION_Z_GAP_RANGE
    elif example_name == "type2_sweep.toml":
        assert tx_region["origin_xyz"] == _SAMPLED_TX_REGION_ORIGIN_XYZ
        assert tx_region["size_xyz"] == _SAMPLED_TX_REGION_SIZE_XYZ
        assert z_gap_range == _SAMPLED_TX_REGION_Z_GAP_RANGE
    else:
        raise AssertionError(f"unsupported type2 example {example_name!r}")


def _assert_tx_reference_line_payload(payload: dict[str, object], *, example_name: str) -> None:
    x_range = _tx_reference_line_ratio_range(payload, "x_ratio")
    y_range = _tx_reference_line_ratio_range(payload, "y_usage_ratio")
    z_range = _tx_reference_line_ratio_range(payload, "z_ratio")
    assert x_range[0] is False
    assert y_range[0] is False
    assert z_range[0] is False
    assert 0.0 < x_range[1] <= x_range[2] < 1.0
    assert 0.0 < y_range[1] <= y_range[2] <= 1.0
    assert 0.0 < z_range[1] <= z_range[2] <= 1.0
    if example_name == "type2_fixed.toml":
        assert x_range == (False, _FIXED_TX_REFERENCE_LINE_RATIOS[0], _FIXED_TX_REFERENCE_LINE_RATIOS[0], 1)
        assert y_range == (False, _FIXED_TX_REFERENCE_LINE_RATIOS[1], _FIXED_TX_REFERENCE_LINE_RATIOS[1], 1)
        assert z_range == (False, _FIXED_TX_REFERENCE_LINE_RATIOS[2], _FIXED_TX_REFERENCE_LINE_RATIOS[2], 1)
        return
    if example_name == "type2_sweep.toml":
        expected_x_start, expected_x_end, expected_x_count = _SAMPLED_TX_REFERENCE_LINE_RANGES[0]
        expected_y_start, expected_y_end, expected_y_count = _SAMPLED_TX_REFERENCE_LINE_RANGES[1]
        expected_z_start, expected_z_end, expected_z_count = _SAMPLED_TX_REFERENCE_LINE_RANGES[2]
        assert x_range == (False, expected_x_start, expected_x_end, expected_x_count)
        assert y_range == (False, expected_y_start, expected_y_end, expected_y_count)
        assert z_range == (False, expected_z_start, expected_z_end, expected_z_count)
        return
    raise AssertionError(f"unsupported example fixture: {example_name}")


def _assert_rejects_tx_output_variable(payload: dict[str, object]) -> None:
    variables = _output_variables(payload)
    for variable in variables:
        name = cast(str, variable["name"])
        expression = cast(str, variable["expression"])
        if name.startswith(("Ltx", "Qtx", "Rtx", "Xtx", "Gtx", "Btx")) or "TX_TML" in expression:
            raise ValueError(f"RxOnly outputs must not include TX output variable {name!r}")


def _assert_rejects_tx_modeled_role(payload: dict[str, object]) -> None:
    for table in _tables(payload, "modeled_objects"):
        role = cast(str, table["role"])
        if role in _TX_MODELED_ROLES:
            raise ValueError(f"RxOnly modeled_objects must not include TX role {role!r}")


def _assert_rejects_tx_sampled_owner(payload: dict[str, object]) -> None:
    for table in _tables(payload, "non_model_objects"):
        object_id = cast(str, table["id"])
        if object_id in _TX_SAMPLED_OWNER_IDS:
            raise ValueError(f"RxOnly non_model_objects must not include TX sampled owner {object_id!r}")


@pytest.mark.parametrize("example_name", ("type2_fixed.toml", "type2_sweep.toml"))
def test_active_type2_examples_are_txrx(example_name: str) -> None:
    payload = _example_payload(example_name)
    _assert_txrx_payload(payload, example_name=example_name)
    _assert_tx_region_payload(payload, example_name=example_name)
    _assert_tx_reference_line_payload(payload, example_name=example_name)


def test_active_type2_sweep_has_15_sampled_dimensions_with_fixed_tv_and_reference_line_owners() -> None:
    owner_paths = type2_sampled_owner_paths(_repo_root() / "examples" / "type2_sweep.toml")

    assert len(owner_paths) == _SAMPLED_TYPE2_OWNER_COUNT
    assert owner_paths == _EXPECTED_SAMPLED_OWNER_PATHS
    assert _TX_REGION_Z_GAP_OWNER_PATH in owner_paths
    assert _TV_ALUMINUM_PLATE_SHEET_PRESENT_OWNER_PATH not in owner_paths
    assert "non_model_objects.tx_region.tx_reference_line.y_usage_ratio" not in owner_paths
    assert "non_model_objects.tx_region.tx_reference_line.z_ratio" not in owner_paths
    assert "modeled_objects.tv_aluminum_plate.thickness_mm" not in owner_paths


def test_rx_only_surface_rejects_tx_output_variable() -> None:
    payload = _example_payload("type2_fixed.toml")
    variables = _raw_output_variable_list(payload)
    variables.append({"name": "Ltx_uH", "expression": "im(Zt(TX_TML,TX_TML))/2/pi/freq*1e6"})

    with pytest.raises(ValueError, match="TX output variable"):
        _assert_rejects_tx_output_variable(payload)


def test_rx_only_surface_rejects_tx_modeled_role() -> None:
    payload = _example_payload("type2_fixed.toml")
    modeled_objects = _raw_table_list(payload, "modeled_objects")
    modeled_objects.append(
        {
            "object_id": "tx_rect_void_columns",
            "role": "tx_rect_void_columns",
            "material": "composite",
            "model_state": True,
        }
    )

    with pytest.raises(ValueError, match="TX role"):
        _assert_rejects_tx_modeled_role(payload)


def test_rx_only_surface_rejects_tx_sampled_owner() -> None:
    payload = _example_payload("type2_fixed.toml")
    non_model_objects = _raw_table_list(payload, "non_model_objects")
    non_model_objects.append({"id": "tx_region_actual", "kind": "tx_region_actual", "source_region_id": "tx_region"})

    with pytest.raises(ValueError, match="TX sampled owner"):
        _assert_rejects_tx_sampled_owner(payload)

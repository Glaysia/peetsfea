from __future__ import annotations

from pathlib import Path
import tomllib
from typing import cast

import pytest


_RX_ONLY_OUTPUT_NAMES = (
    "Lrx_uH",
    "Qrx_ratio",
    "Rrx_ac_ohm",
    "Xrx_ohm",
    "Grx_S",
    "Brx_S",
    "Srx_self_mag_ratio",
    "eta_rx_accept_ratio",
)
_TX_MODELED_ROLES = {"tx_single_coil", "tx_rect_void_columns", "tx_plate_stack"}
_TX_SAMPLED_OWNER_IDS = {"tx_region_actual", "tx_region_actual_stack_space"}


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


def _assert_rx_only_payload(payload: dict[str, object]) -> None:
    outputs = cast(dict[str, object], payload["outputs"])
    assert outputs["mode"] == "RxOnly"

    variables = _output_variables(payload)
    names = tuple(cast(str, variable["name"]) for variable in variables)
    expressions = tuple(cast(str, variable["expression"]) for variable in variables)
    assert names == _RX_ONLY_OUTPUT_NAMES
    assert all("TX_TML" not in expression for expression in expressions)

    modeled_roles = tuple(cast(str, table["role"]) for table in _tables(payload, "modeled_objects"))
    assert modeled_roles == ("rx_single_coil",)
    assert not _TX_MODELED_ROLES.intersection(modeled_roles)

    non_model_ids = tuple(cast(str, table["id"]) for table in _tables(payload, "non_model_objects"))
    assert "tx_region" in non_model_ids
    assert "rx_region_max" in non_model_ids
    assert not _TX_SAMPLED_OWNER_IDS.intersection(non_model_ids)


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
def test_active_type2_examples_are_rx_only(example_name: str) -> None:
    _assert_rx_only_payload(_example_payload(example_name))


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

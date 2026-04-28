from __future__ import annotations

from pathlib import Path
import tomllib
from typing import cast


def _fixed_payload() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "examples" / "type2_fixed.toml"
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _tables(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    raw_tables = payload[key]
    assert isinstance(raw_tables, list)
    tables: list[dict[str, object]] = []
    for raw_table in raw_tables:
        assert isinstance(raw_table, dict)
        tables.append(cast(dict[str, object], raw_table))
    return tables


def test_fixed_viewer_refresh_fixture_is_rx_only() -> None:
    payload = _fixed_payload()

    non_model_ids = tuple(cast(str, table["id"]) for table in _tables(payload, "non_model_objects"))
    assert non_model_ids == ("floor", "shelf", "wall", "tv", "tx_region", "rx_region_max")

    modeled_objects = _tables(payload, "modeled_objects")
    assert len(modeled_objects) == 1
    assert modeled_objects[0]["object_id"] == "rx_rect_void_coil"
    assert modeled_objects[0]["role"] == "rx_single_coil"

    outputs = cast(dict[str, object], payload["outputs"])
    assert outputs["mode"] == "RxOnly"
    raw_variables = outputs["variables"]
    assert isinstance(raw_variables, list)
    for raw_variable in raw_variables:
        assert isinstance(raw_variable, dict)
        variable = cast(dict[str, object], raw_variable)
        assert not cast(str, variable["name"]).startswith(("Ltx", "Qtx", "Rtx", "Xtx", "Gtx", "Btx"))
        assert "TX_TML" not in cast(str, variable["expression"])

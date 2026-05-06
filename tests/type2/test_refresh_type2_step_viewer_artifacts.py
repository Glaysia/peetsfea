from __future__ import annotations

import json
from pathlib import Path
import tomllib
from typing import cast


def _notebook_source_text() -> str:
    notebook_path = Path(__file__).resolve().parents[2] / "notebooks" / "view_step_files.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    raw_cells = notebook["cells"]
    assert isinstance(raw_cells, list)
    source_parts: list[str] = []
    for raw_cell in raw_cells:
        assert isinstance(raw_cell, dict)
        raw_source = raw_cell["source"]
        assert isinstance(raw_source, list)
        for raw_line in raw_source:
            assert isinstance(raw_line, str)
            source_parts.append(raw_line)
    return "".join(source_parts)


def _notebook_code_sources() -> list[str]:
    notebook_path = Path(__file__).resolve().parents[2] / "notebooks" / "view_step_files.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    raw_cells = notebook["cells"]
    assert isinstance(raw_cells, list)
    code_sources: list[str] = []
    for raw_cell in raw_cells:
        assert isinstance(raw_cell, dict)
        if raw_cell["cell_type"] != "code":
            continue
        raw_source = raw_cell["source"]
        assert isinstance(raw_source, list)
        source_lines: list[str] = []
        for raw_line in raw_source:
            assert isinstance(raw_line, str)
            source_lines.append(raw_line)
        code_sources.append("".join(source_lines))
    return code_sources


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


def test_fixed_viewer_refresh_fixture_is_txrx() -> None:
    payload = _fixed_payload()

    non_model_ids = tuple(cast(str, table["id"]) for table in _tables(payload, "non_model_objects"))
    assert non_model_ids == ("floor", "shelf", "wall", "tv", "tx_region", "rx_region_max")

    modeled_objects = _tables(payload, "modeled_objects")
    modeled_object_ids = tuple(cast(str, table["object_id"]) for table in modeled_objects)
    assert set(modeled_object_ids) == {"tx_inner_rect_void_coil", "rx_rect_void_coil", "tv_aluminum_plate"}
    modeled_by_id = {cast(str, table["object_id"]): table for table in modeled_objects}
    assert modeled_by_id["tx_inner_rect_void_coil"]["role"] == "tx_inner_single_coil"
    assert cast(dict[str, object], modeled_by_id["tx_inner_rect_void_coil"]["underlay_repeat_count"])["range"] == [
        True,
        1,
        1,
        1,
    ]
    assert cast(dict[str, object], modeled_by_id["tx_inner_rect_void_coil"]["void_stack_present"])["range"] == [
        True,
        0,
        0,
        1,
    ]
    assert modeled_by_id["rx_rect_void_coil"]["role"] == "rx_single_coil"

    tv_aluminum_plate = modeled_by_id["tv_aluminum_plate"]
    assert tv_aluminum_plate["role"] == "tv_aluminum_plate"
    assert tv_aluminum_plate["material"] == "aluminum"
    assert tv_aluminum_plate["model_state"] is True
    assert tv_aluminum_plate["source_non_model_object_id"] == "tv"
    outputs = cast(dict[str, object], payload["outputs"])
    assert outputs["mode"] == "TxRx"
    raw_variables = outputs["variables"]
    assert isinstance(raw_variables, list)
    variable_names: list[str] = []
    variable_expressions: list[str] = []
    for raw_variable in raw_variables:
        assert isinstance(raw_variable, dict)
        variable = cast(dict[str, object], raw_variable)
        variable_names.append(cast(str, variable["name"]))
        variable_expressions.append(cast(str, variable["expression"]))
    assert "Ltx_uH" in variable_names
    assert "Qtx_ratio" in variable_names
    assert "TX_TML" in "\n".join(variable_expressions)


def test_view_step_notebook_uses_toml_owner_descriptions() -> None:
    notebook_path = Path(__file__).resolve().parents[2] / "notebooks" / "view_step_files.ipynb"
    notebook_text = notebook_path.read_text(encoding="utf-8")

    assert "_OWNER_DESCRIPTIONS" not in notebook_text
    assert "type2_range_owner_descriptions" in notebook_text
    assert "from peetsfea.type2_spec_tools import type2_range_owner_descriptions" in notebook_text
    assert "type2_range_owner_descriptions(sampled_toml_path)" in notebook_text


def test_view_step_notebook_has_no_tx_outer_raw_owner_mapping() -> None:
    notebook_path = Path(__file__).resolve().parents[2] / "notebooks" / "view_step_files.ipynb"
    notebook_text = notebook_path.read_text(encoding="utf-8")

    assert "modeled_objects.tx_outer_rect_void_coil." not in notebook_text
    assert "modeled_objects.tx_inner_rect_void_coil.tx_outer_x_position_ratio" not in notebook_text
    assert "CANONICAL_OWNER_RAW_SOURCE_PATHS" not in notebook_text
    assert "source_path = owner_path" in notebook_text
    assert "_selected_owner_table(payload, source_path)" in notebook_text
    assert "owner_path} = {_selected_owner_value(payload, owner_path)}  # {description}" in notebook_text
    assert "description = owner_descriptions[owner_path]" in notebook_text


def test_view_step_notebook_selects_sampled_manifest_entries_by_sample_index() -> None:
    notebook_text = _notebook_source_text()

    assert "def selected_manifest_entry_for_sample_index(" in notebook_text
    assert 'entry["sample_index"] == sample_index' in notebook_text
    assert "manifest must contain exactly one entry for sample_index={sample_index}" in notebook_text
    assert "from peetsfea.type2_sampled import manifest_entry_for_sample_index" not in notebook_text


def test_view_step_notebook_step_display_and_gui_build_share_sample_index_selector() -> None:
    code_sources = _notebook_code_sources()

    selector_call = "selected_entry = selected_manifest_entry_for_sample_index("
    step_display_text = next(source for source in code_sources if "shown_step = bd.import_step(scene_step_path)" in source)
    gui_build_text = next(source for source in code_sources if "GUI debug build delegated to entry/build.py" in source)

    assert selector_call in step_display_text
    assert selector_call in gui_build_text
    assert "sample_index=VIEW_INDEX" in step_display_text
    assert "sample_index=VIEW_INDEX" in gui_build_text


def test_view_step_notebook_gui_build_supports_fixed_view_index() -> None:
    code_sources = _notebook_code_sources()

    gui_build_text = next(source for source in code_sources if "GUI debug build delegated to entry/build.py" in source)

    assert "if VIEW_INDEX == -1:" in gui_build_text
    assert "setup_type2_step_ledger_into_hfss" in gui_build_text
    assert "step_ledger_path=TYPE2_FIXED_LEDGER_PATH" in gui_build_text
    assert 'output_aedt_path = TYPE2_FIXED_OUTPUT_DIR / "type2_fixed.aedt"' in gui_build_text

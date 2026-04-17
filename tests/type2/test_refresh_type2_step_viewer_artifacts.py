from __future__ import annotations

import json
from pathlib import Path

import pytest

from entry.refresh_type2_step_viewer_artifacts import refresh_type2_step_viewer_artifacts


def _type2_fixed_toml_with_required_underlay_field(tmp_path: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    source_path = repo_root / "examples" / "type2_fixed.toml"
    source_text = source_path.read_text(encoding="utf-8")
    if "[modeled_objects.underlay_repeat_count]" not in source_text:
        source_lines = source_text.splitlines()
        rewritten_lines: list[str] = []
        modeled_object_count = 0
        inserted_count = 0
        line_index = 0
        while line_index < len(source_lines):
            line = source_lines[line_index]
            rewritten_lines.append(line)
            if line == "[[modeled_objects]]":
                modeled_object_count += 1
            if line == "[modeled_objects.layer_count]":
                line_index += 1
                assert line_index < len(source_lines)
                rewritten_lines.append(source_lines[line_index])
                rewritten_lines.extend(
                    (
                        "",
                        "[modeled_objects.underlay_repeat_count]",
                        "range = [true, 0, 0, 1]",
                    )
                )
                inserted_count += 1
            line_index += 1
        assert inserted_count == modeled_object_count
        source_text = "\n".join(rewritten_lines) + "\n"
    normalized_path = tmp_path / "type2_fixed.with_underlay.toml"
    normalized_path.write_text(source_text, encoding="utf-8")
    return normalized_path


def _modeled_entry(payload: dict[str, object], *, object_id: str) -> dict[str, object]:
    modeled_objects = payload["modeled_objects"]
    assert isinstance(modeled_objects, list)
    matches = [entry for entry in modeled_objects if isinstance(entry, dict) and entry["object_id"] == object_id]
    assert len(matches) == 1
    return matches[0]


def _member_entry(payload: dict[str, object], *, object_id: str) -> dict[str, object]:
    non_model_objects = payload["non_model_objects"]
    assert isinstance(non_model_objects, list)
    assert len(non_model_objects) == 1
    non_model_entry = non_model_objects[0]
    assert isinstance(non_model_entry, dict)
    member_objects = non_model_entry["member_objects"]
    assert isinstance(member_objects, list)
    matches = [entry for entry in member_objects if isinstance(entry, dict) and entry["object_id"] == object_id]
    assert len(matches) == 1
    return matches[0]


def test_refresh_type2_step_viewer_artifacts_rebuilds_clean_output_and_validates_tx_rx_placement(tmp_path: Path) -> None:
    toml_path = _type2_fixed_toml_with_required_underlay_field(tmp_path)
    output_dir = tmp_path / "run" / "step" / "type2"
    ledger_path = output_dir / "type2_step_ledger.json"

    output_dir.mkdir(parents=True, exist_ok=True)
    stale_file = output_dir / "stale.txt"
    stale_file.write_text("stale", encoding="utf-8")
    stale_subdir = output_dir / "old"
    stale_subdir.mkdir()
    (stale_subdir / "old.step").write_text("stale", encoding="utf-8")
    stale_preview_step = output_dir / "type2_combined_preview.step"
    stale_preview_step.write_text("stale", encoding="utf-8")
    stale_objects_dir = output_dir / "objects"
    stale_objects_dir.mkdir()
    (stale_objects_dir / "tx_rect_void_coil.step").write_text("stale", encoding="utf-8")

    result = refresh_type2_step_viewer_artifacts(
        toml_path=toml_path,
        output_dir=output_dir,
        ledger_path=ledger_path,
        seed=0,
    )

    assert stale_file.exists() is False
    assert stale_subdir.exists() is False
    assert stale_preview_step.exists() is False
    assert stale_objects_dir.exists() is False
    assert Path(result["ledger_path"]).is_file()
    assert Path(result["scene_step_path"]).is_file()
    assert (output_dir / "type2_scene.step").is_file()
    assert (output_dir / "type2_non_model_scene.step").exists() is False
    assert (output_dir / "objects" / "tx_rect_void_coil.step").exists() is False
    assert (output_dir / "objects" / "rx_rect_void_coil.step").exists() is False
    assert (output_dir / "metadata" / "tx_rect_void_coil.metadata.json").is_file()
    assert (output_dir / "metadata" / "rx_rect_void_coil.metadata.json").is_file()

    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    tx_entry = _modeled_entry(payload, object_id="tx_rect_void_coil")
    rx_entry = _modeled_entry(payload, object_id="rx_rect_void_coil")
    tx_region = _member_entry(payload, object_id="tx_region")
    rx_region = _member_entry(payload, object_id="rx_region_max")

    tx_min_x, tx_min_y, tx_min_z = tx_entry["canonical_coordinates"]["outer_bounds_min_xyz"]
    tx_size_x, tx_size_y, tx_size_z = tx_entry["canonical_coordinates"]["outer_bounds_size_xyz"]
    tx_region_min_x, tx_region_min_y, tx_region_min_z = tx_region["canonical_coordinates"]["outer_bounds_min_xyz"]
    tx_region_size_x, tx_region_size_y, tx_region_size_z = tx_region["canonical_coordinates"]["outer_bounds_size_xyz"]
    tx_pcb_layers = tx_entry["canonical_coordinates"]["pcb_layer_z_positions_mm"]
    assert isinstance(tx_pcb_layers, list)
    tx_expected_names = tx_entry["expected_exported_body_names"]
    assert tx_expected_names[: len(tx_pcb_layers)] == [f"tx_pcb_l{index}" for index in range(len(tx_pcb_layers))]
    assert tx_expected_names[len(tx_pcb_layers)] == ("tx_copper_stack" if len(tx_pcb_layers) > 1 else "tx_copper_l0")
    assert "tx_port_sheet" not in tx_expected_names
    assert tx_entry["expected_exported_body_count"] == len(tx_expected_names)
    tx_port_sheet_vertices = tx_entry["terminal_metadata"]["port_sheet_vertices_xyz"]
    assert len(tx_port_sheet_vertices) == 4
    assert tx_region_min_z == pytest.approx(0.0)
    assert tx_min_x == pytest.approx(tx_region_min_x + (tx_region_size_x - tx_size_x) / 2.0)
    assert tx_min_y == pytest.approx(tx_region_min_y + (tx_region_size_y - tx_size_y) / 2.0)
    assert tx_min_z == pytest.approx(tx_region_min_z + tx_region_size_z - tx_size_z)

    rx_min_x, rx_min_y, rx_min_z = rx_entry["canonical_coordinates"]["outer_bounds_min_xyz"]
    rx_max_x, _rx_max_y, _rx_max_z = rx_entry["canonical_coordinates"]["outer_bounds_max_xyz"]
    rx_size_x, rx_size_y, _rx_size_z = rx_entry["canonical_coordinates"]["outer_bounds_size_xyz"]
    rx_region_min_x, rx_region_min_y, rx_region_min_z = rx_region["canonical_coordinates"]["outer_bounds_min_xyz"]
    rx_region_max_x, _rx_region_max_y, _rx_region_max_z = rx_region["canonical_coordinates"]["outer_bounds_max_xyz"]
    _rx_region_size_x, rx_region_size_y, _rx_region_size_z = rx_region["canonical_coordinates"]["outer_bounds_size_xyz"]
    assert rx_entry["expected_exported_body_names"] == ["rx_pcb_l0", "rx_copper_l0"]
    assert rx_entry["expected_exported_body_count"] == 2
    assert "rx_port_sheet" not in rx_entry["expected_exported_body_names"]
    assert rx_region_min_z == pytest.approx(139.0)
    assert rx_min_x == pytest.approx(rx_region_max_x - rx_size_x)
    assert rx_min_y == pytest.approx(rx_region_min_y + (rx_region_size_y - rx_size_y) / 2.0)
    assert rx_min_z == pytest.approx(rx_region_min_z)
    assert rx_max_x == pytest.approx(rx_region_max_x)

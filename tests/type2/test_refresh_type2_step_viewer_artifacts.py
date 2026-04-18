from __future__ import annotations

import json
from pathlib import Path

import build123d as bd
import pytest

from entry.refresh_type2_step_viewer_artifacts import refresh_type2_step_viewer_artifacts
from peetsfea.type2_step_spec import load_type2_step_spec
from peetsfea.type2_step_spec import resolve_modeled_underlay_gap_mm
from peetsfea.type2_step_spec import resolve_modeled_underlay_repeat_count

_UNDERLAY_FERRITE_THICKNESS_MM = 0.20
_UNDERLAY_PET_PSA_THICKNESS_MM = 0.15
_UNDERLAY_AIR_THICKNESS_MM = 0.02


def _type2_fixed_toml_with_required_underlay_field(tmp_path: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    source_path = repo_root / "examples" / "type2_fixed.toml"
    source_text = source_path.read_text(encoding="utf-8")
    assert source_text.count("[modeled_objects.underlay_repeat_count]") == 2
    assert source_text.count("[modeled_objects.underlay_gap_mm]") == 1
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


def _body_bbox(step_path: Path, *, label: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    shape = bd.import_step(step_path)
    children = tuple(shape.children) if tuple(shape.children) else (shape,)
    matches = [child for child in children if child.label == label]
    assert len(matches) == 1
    bbox = matches[0].bounding_box()
    return ((bbox.min.X, bbox.min.Y, bbox.min.Z), (bbox.max.X, bbox.max.Y, bbox.max.Z))


def test_refresh_type2_step_viewer_artifacts_rebuilds_clean_output_and_validates_tx_rx_placement(tmp_path: Path) -> None:
    toml_path = _type2_fixed_toml_with_required_underlay_field(tmp_path)
    spec = load_type2_step_spec(toml_path)
    tx_spec = next(entry for entry in spec.modeled_objects if entry.object_id == "tx_rect_void_coil")
    rx_spec = next(entry for entry in spec.modeled_objects if entry.object_id == "rx_rect_void_coil")
    tx_repeat_count = resolve_modeled_underlay_repeat_count(tx_spec, seed=0)
    assert hasattr(tx_spec, "underlay_gap_mm")
    tx_gap_mm = resolve_modeled_underlay_gap_mm(tx_spec, seed=0)
    rx_repeat_count = resolve_modeled_underlay_repeat_count(rx_spec, seed=0)
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
    scene_step_path = Path(result["scene_step_path"])
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
    if tx_repeat_count > 0:
        assert tx_expected_names[-(tx_repeat_count * 3) :] == [
            body_name
            for unit_index in range(tx_repeat_count)
            for body_name in (
                f"tx_underlay_ferrite_u{unit_index}",
                f"tx_underlay_pet_psa_u{unit_index}",
                f"tx_underlay_air_u{unit_index}",
            )
        ]
    assert all(len(name) <= 32 for name in tx_expected_names if "underlay" in name)
    assert "tx_port_sheet" not in tx_expected_names
    assert tx_entry["expected_exported_body_count"] == len(tx_expected_names)
    tx_port_sheet_vertices = tx_entry["terminal_metadata"]["port_sheet_vertices_xyz"]
    assert len(tx_port_sheet_vertices) == 4
    assert tx_region_min_z == pytest.approx(0.0)
    assert tx_min_x == pytest.approx(tx_region_min_x)
    assert tx_min_y == pytest.approx(tx_region_min_y + (tx_region_size_y - tx_size_y) / 2.0)
    assert tx_min_z == pytest.approx(tx_region_min_z + tx_region_size_z - tx_size_z)
    if tx_repeat_count > 0:
        ferrite_min_xyz, ferrite_max_xyz = _body_bbox(scene_step_path, label="tx_underlay_ferrite_u0")
        pet_min_xyz, pet_max_xyz = _body_bbox(scene_step_path, label="tx_underlay_pet_psa_u0")
        air_min_xyz, air_max_xyz = _body_bbox(scene_step_path, label="tx_underlay_air_u0")
        assert ferrite_min_xyz[0] == pytest.approx(tx_region_min_x)
        assert ferrite_min_xyz[1] == pytest.approx(tx_region_min_y)
        assert ferrite_max_xyz[0] == pytest.approx(tx_region_min_x + tx_region_size_x)
        assert ferrite_max_xyz[1] == pytest.approx(tx_region_min_y + tx_region_size_y)
        assert ferrite_max_xyz[2] == pytest.approx(tx_min_z - tx_gap_mm)
        assert ferrite_min_xyz[2] == pytest.approx(tx_min_z - tx_gap_mm - _UNDERLAY_FERRITE_THICKNESS_MM)
        assert pet_max_xyz[2] == pytest.approx(ferrite_min_xyz[2])
        assert pet_min_xyz[2] == pytest.approx(pet_max_xyz[2] - _UNDERLAY_PET_PSA_THICKNESS_MM)
        assert air_max_xyz[2] == pytest.approx(pet_min_xyz[2])
        assert air_min_xyz[2] == pytest.approx(air_max_xyz[2] - _UNDERLAY_AIR_THICKNESS_MM)

    rx_min_x, rx_min_y, rx_min_z = rx_entry["canonical_coordinates"]["outer_bounds_min_xyz"]
    rx_max_x, _rx_max_y, _rx_max_z = rx_entry["canonical_coordinates"]["outer_bounds_max_xyz"]
    rx_size_x, rx_size_y, _rx_size_z = rx_entry["canonical_coordinates"]["outer_bounds_size_xyz"]
    rx_region_min_x, rx_region_min_y, rx_region_min_z = rx_region["canonical_coordinates"]["outer_bounds_min_xyz"]
    rx_region_max_x, _rx_region_max_y, _rx_region_max_z = rx_region["canonical_coordinates"]["outer_bounds_max_xyz"]
    _rx_region_size_x, rx_region_size_y, _rx_region_size_z = rx_region["canonical_coordinates"]["outer_bounds_size_xyz"]
    assert rx_entry["expected_exported_body_names"][:2] == ["rx_pcb_l0", "rx_copper_l0"]
    if rx_repeat_count > 0:
        assert rx_entry["expected_exported_body_names"][2:] == [
            body_name
            for unit_index in range(rx_repeat_count)
            for body_name in (
                f"under_rx_ferrite_u{unit_index}",
                f"under_rx_pet_psa_u{unit_index}",
                f"under_rx_air_u{unit_index}",
            )
        ]
    else:
        assert rx_entry["expected_exported_body_names"] == ["rx_pcb_l0", "rx_copper_l0"]
    assert rx_entry["expected_exported_body_count"] == len(rx_entry["expected_exported_body_names"])
    assert all(len(name) <= 32 for name in rx_entry["expected_exported_body_names"] if name.startswith("under_rx_"))
    assert "rx_port_sheet" not in rx_entry["expected_exported_body_names"]
    assert rx_region_min_z == pytest.approx(139.0)
    assert rx_min_x == pytest.approx(rx_region_max_x - rx_size_x)
    assert rx_min_y == pytest.approx(rx_region_min_y + (rx_region_size_y - rx_size_y) / 2.0)
    assert rx_min_z == pytest.approx(rx_region_min_z)
    assert rx_max_x == pytest.approx(rx_region_max_x)
    if rx_repeat_count > 0:
        ferrite_min_xyz, ferrite_max_xyz = _body_bbox(scene_step_path, label="under_rx_ferrite_u0")
        pet_min_xyz, pet_max_xyz = _body_bbox(scene_step_path, label="under_rx_pet_psa_u0")
        air_min_xyz, air_max_xyz = _body_bbox(scene_step_path, label="under_rx_air_u0")
        assert air_min_xyz[0] == pytest.approx(rx_region_min_x)
        assert air_max_xyz[0] == pytest.approx(rx_region_min_x + _UNDERLAY_AIR_THICKNESS_MM)
        assert pet_min_xyz[0] == pytest.approx(air_max_xyz[0])
        assert pet_max_xyz[0] == pytest.approx(pet_min_xyz[0] + _UNDERLAY_PET_PSA_THICKNESS_MM)
        assert ferrite_min_xyz[0] == pytest.approx(pet_max_xyz[0])
        assert ferrite_max_xyz[0] == pytest.approx(ferrite_min_xyz[0] + _UNDERLAY_FERRITE_THICKNESS_MM)
        for min_xyz, max_xyz in (
            (ferrite_min_xyz, ferrite_max_xyz),
            (pet_min_xyz, pet_max_xyz),
            (air_min_xyz, air_max_xyz),
        ):
            assert min_xyz[1] == pytest.approx(rx_region_min_y)
            assert max_xyz[1] == pytest.approx(rx_region_min_y + rx_region_size_y)
            assert min_xyz[2] == pytest.approx(rx_region_min_z)
            assert max_xyz[2] == pytest.approx(rx_region_min_z + _rx_region_size_z)

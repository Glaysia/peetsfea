from __future__ import annotations

from pathlib import Path

import pytest

from peetsfea.backend.pyaedt.type2_modeled_import_adapter import build_single_imported_modeled_object_entry


def _modeled_object(step_path: Path) -> dict[str, object]:
    return {
        "object_id": "tx_rect_void_coil",
        "role": "tx_single_coil",
        "material": "composite",
        "model_state": True,
        "step_path": str(step_path),
        "canonical_coordinates": {
            "frame_origin_xyz": [0.0, 0.0, 0.0],
            "outer_bounds_min_xyz": [-25.0, -15.0, 0.0],
            "outer_bounds_max_xyz": [25.0, 15.0, 2.8],
            "outer_bounds_size_xyz": [50.0, 30.0, 2.8],
            "pcb_layer_z_positions_mm": [0.0, 2.5],
            "copper_layer_z_positions_mm": [1.6, 4.1],
        },
        "terminal_metadata": {
            "path": "A_cw_to_a",
            "outer_corner": "A",
            "inner_corner": "a",
            "direction": "cw",
            "start_point_xy_mm": [-25.0, 15.0],
            "end_point_xy_mm": [-10.0, 5.0],
        },
    }


def test_build_single_imported_modeled_object_entry_returns_validated_contract(tmp_path: Path) -> None:
    step_path = tmp_path / "tx_rect_void.step"
    modeled_object = _modeled_object(step_path)

    result = build_single_imported_modeled_object_entry(
        modeled_object=modeled_object,
        imported_step_path=step_path,
        imported_object_names=("body_1", "body_2"),
    )

    assert result["object_id"] == "tx_rect_void_coil"
    assert result["role"] == "tx_single_coil"
    assert result["material"] == "composite"
    assert result["model_state"] is True
    assert result["step_path"] == str(step_path.resolve(strict=False))
    assert result["canonical_coordinates"]["frame_origin_xyz"] == (0.0, 0.0, 0.0)
    assert result["terminal_metadata"]["direction"] == "cw"
    assert result["imported_object_names"] == ("body_1", "body_2")


def test_build_single_imported_modeled_object_entry_rejects_non_tx_single_coil_role(tmp_path: Path) -> None:
    step_path = tmp_path / "tx_rect_void.step"
    modeled_object = _modeled_object(step_path)
    modeled_object["role"] = "rx_single_coil"

    with pytest.raises(ValueError, match=r"modeled_object\.role must be 'tx_single_coil'"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_step_path=step_path,
            imported_object_names=("body_1",),
        )


def test_build_single_imported_modeled_object_entry_rejects_model_state_false(tmp_path: Path) -> None:
    step_path = tmp_path / "tx_rect_void.step"
    modeled_object = _modeled_object(step_path)
    modeled_object["model_state"] = False

    with pytest.raises(ValueError, match=r"model_state must be true"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_step_path=step_path,
            imported_object_names=("body_1",),
        )


def test_build_single_imported_modeled_object_entry_rejects_step_path_mismatch(tmp_path: Path) -> None:
    step_path = tmp_path / "tx_rect_void.step"
    modeled_object = _modeled_object(step_path)
    imported_step_path = tmp_path / "different.step"

    with pytest.raises(ValueError, match=r"modeled_object\.step_path must match imported_step_path"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_step_path=imported_step_path,
            imported_object_names=("body_1",),
        )


def test_build_single_imported_modeled_object_entry_rejects_empty_imported_object_names(tmp_path: Path) -> None:
    step_path = tmp_path / "tx_rect_void.step"
    modeled_object = _modeled_object(step_path)

    with pytest.raises(ValueError, match=r"imported_object_names must contain at least one object name"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_step_path=step_path,
            imported_object_names=(),
        )


def test_build_single_imported_modeled_object_entry_rejects_duplicate_imported_object_names(tmp_path: Path) -> None:
    step_path = tmp_path / "tx_rect_void.step"
    modeled_object = _modeled_object(step_path)

    with pytest.raises(ValueError, match=r"imported_object_names must be duplicate-free"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_step_path=step_path,
            imported_object_names=("body_1", "body_1"),
        )


def test_build_single_imported_modeled_object_entry_rejects_missing_terminal_metadata(tmp_path: Path) -> None:
    step_path = tmp_path / "tx_rect_void.step"
    modeled_object = _modeled_object(step_path)
    assert "terminal_metadata" in modeled_object
    del modeled_object["terminal_metadata"]

    with pytest.raises(AssertionError, match=r"modeled_object is missing required key 'terminal_metadata'"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_step_path=step_path,
            imported_object_names=("body_1",),
        )


def test_build_single_imported_modeled_object_entry_rejects_bad_terminal_direction(tmp_path: Path) -> None:
    step_path = tmp_path / "tx_rect_void.step"
    modeled_object = _modeled_object(step_path)
    terminal_metadata = modeled_object["terminal_metadata"]
    assert isinstance(terminal_metadata, dict)
    terminal_metadata["direction"] = "clockwise"

    with pytest.raises(ValueError, match=r"terminal_metadata\.direction must be 'cw' or 'ccw'"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_step_path=step_path,
            imported_object_names=("body_1",),
        )

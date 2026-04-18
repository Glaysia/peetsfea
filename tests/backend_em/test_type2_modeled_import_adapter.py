from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from peetsfea.backend.pyaedt.type2_modeled_import_adapter import build_single_imported_modeled_object_entry


def _modeled_object() -> dict[str, object]:
    return {
        "object_id": "tx_rect_void_coil",
        "role": "tx_single_coil",
        "plane": "XY",
        "placement_owner_id": "tx_region",
        "material": "composite",
        "model_state": True,
        "canonical_coordinates": {
            "frame_origin_xyz": [0.0, 0.0, 0.0],
            "outer_bounds_min_xyz": [-25.0, -15.0, 0.0],
            "outer_bounds_max_xyz": [25.0, 15.0, 2.8],
            "outer_bounds_size_xyz": [50.0, 30.0, 2.8],
            "pcb_layer_z_positions_mm": [0.0, 2.5],
            "copper_layer_z_positions_mm": [0.4, 2.9],
        },
        "terminal_metadata": {
            "path": "A_cw_to_a",
            "outer_corner": "A",
            "inner_corner": "a",
            "direction": "cw",
            "start_point_plane_mm": [-25.0, 15.0],
            "end_point_plane_mm": [-10.0, 5.0],
        },
    }


def _plate_stack_modeled_object(
    *,
    object_id: str,
    role: str,
    plane: str,
    placement_owner_id: str,
) -> dict[str, object]:
    modeled_object = _modeled_object()
    modeled_object["object_id"] = object_id
    modeled_object["role"] = role
    modeled_object["plane"] = plane
    modeled_object["placement_owner_id"] = placement_owner_id
    modeled_object["terminal_metadata"] = {
        "kind": "stub_port",
        "input_stub_body_name": f"{object_id}_stub_in",
        "output_stub_body_name": f"{object_id}_stub_out",
        "start_point_plane_mm": [145.0, 5.5],
        "end_point_plane_mm": [145.0, 60.5],
        "port_sheet_vertices_xyz": [
            [0.0, 145.0, 0.0],
            [0.035, 145.0, 0.0],
            [0.035, 145.0, 66.0],
            [0.0, 145.0, 66.0],
        ],
    }
    return modeled_object


def test_build_single_imported_modeled_object_entry_returns_validated_contract(tmp_path: Path) -> None:
    modeled_object = _modeled_object()

    result = build_single_imported_modeled_object_entry(
        modeled_object=modeled_object,
        imported_object_names=("body_1", "body_2"),
    )

    assert result["object_id"] == "tx_rect_void_coil"
    assert result["role"] == "tx_single_coil"
    assert result["plane"] == "XY"
    assert result["placement_owner_id"] == "tx_region"
    assert result["material"] == "composite"
    assert result["model_state"] is True
    assert result["canonical_coordinates"]["frame_origin_xyz"] == (0.0, 0.0, 0.0)
    terminal_metadata = cast(dict[str, object], result["terminal_metadata"])
    assert terminal_metadata["direction"] == "cw"
    assert result["imported_object_names"] == ("body_1", "body_2")


def test_build_single_imported_modeled_object_entry_accepts_rx_single_coil_role(tmp_path: Path) -> None:
    modeled_object = _modeled_object()
    modeled_object["object_id"] = "rx_rect_void_coil"
    modeled_object["role"] = "rx_single_coil"
    modeled_object["plane"] = "YZ"
    modeled_object["placement_owner_id"] = "rx_region_actual"

    result = build_single_imported_modeled_object_entry(
        modeled_object=modeled_object,
        imported_object_names=("body_1",),
    )

    assert result["role"] == "rx_single_coil"
    assert result["plane"] == "YZ"
    assert result["placement_owner_id"] == "rx_region_actual"


@pytest.mark.parametrize(
    ("object_id", "role", "plane", "placement_owner_id"),
    [
        ("tx_plate_stack", "tx_plate_stack", "YZ", "tx_region"),
        ("rx_plate_stack", "rx_plate_stack", "YZ", "rx_region_max"),
    ],
)
def test_build_single_imported_modeled_object_entry_accepts_geometry_only_plate_stack_roles(
    tmp_path: Path,
    object_id: str,
    role: str,
    plane: str,
    placement_owner_id: str,
) -> None:
    modeled_object = _plate_stack_modeled_object(
        object_id=object_id,
        role=role,
        plane=plane,
        placement_owner_id=placement_owner_id,
    )

    result = build_single_imported_modeled_object_entry(
        modeled_object=modeled_object,
        imported_object_names=("body_1", "body_2"),
    )

    assert result["object_id"] == object_id
    assert result["role"] == role
    assert result["plane"] == plane
    assert result["placement_owner_id"] == placement_owner_id
    terminal_metadata = cast(dict[str, object], result["terminal_metadata"])
    assert terminal_metadata["kind"] == "stub_port"
    assert terminal_metadata["input_stub_body_name"] == f"{object_id}_stub_in"
    assert terminal_metadata["output_stub_body_name"] == f"{object_id}_stub_out"
    assert result["imported_object_names"] == ("body_1", "body_2")


def test_build_single_imported_modeled_object_entry_rejects_model_state_false(tmp_path: Path) -> None:
    modeled_object = _modeled_object()
    modeled_object["model_state"] = False

    with pytest.raises(ValueError, match=r"model_state must be true"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_object_names=("body_1",),
        )


def test_build_single_imported_modeled_object_entry_rejects_empty_imported_object_names(tmp_path: Path) -> None:
    modeled_object = _modeled_object()

    with pytest.raises(ValueError, match=r"imported_object_names must contain at least one object name"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_object_names=(),
        )


def test_build_single_imported_modeled_object_entry_rejects_duplicate_imported_object_names(tmp_path: Path) -> None:
    modeled_object = _modeled_object()

    with pytest.raises(ValueError, match=r"imported_object_names must be duplicate-free"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_object_names=("body_1", "body_1"),
        )


def test_build_single_imported_modeled_object_entry_rejects_missing_terminal_metadata(tmp_path: Path) -> None:
    modeled_object = _modeled_object()
    assert "terminal_metadata" in modeled_object
    del modeled_object["terminal_metadata"]

    with pytest.raises(AssertionError, match=r"modeled_object is missing required key 'terminal_metadata'"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_object_names=("body_1",),
        )


def test_build_single_imported_modeled_object_entry_rejects_geometry_only_terminal_metadata_for_single_coil(
    tmp_path: Path,
) -> None:
    modeled_object = _modeled_object()
    modeled_object["terminal_metadata"] = {"kind": "stub_port"}

    with pytest.raises(ValueError, match=r"unsupported for coil import"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_object_names=("body_1",),
        )


def test_build_single_imported_modeled_object_entry_rejects_plate_stack_with_non_sentinel_terminal_metadata(
    tmp_path: Path,
) -> None:
    modeled_object = _plate_stack_modeled_object(
        object_id="tx_plate_stack",
        role="tx_plate_stack",
        plane="XY",
        placement_owner_id="tx_region",
    )
    modeled_object["terminal_metadata"] = {"kind": "port"}

    with pytest.raises(ValueError, match=r"terminal_metadata\.kind must be 'stub_port'"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_object_names=("body_1",),
        )


def test_build_single_imported_modeled_object_entry_rejects_bad_terminal_direction(tmp_path: Path) -> None:
    modeled_object = _modeled_object()
    terminal_metadata = modeled_object["terminal_metadata"]
    assert isinstance(terminal_metadata, dict)
    terminal_metadata["direction"] = "clockwise"

    with pytest.raises(ValueError, match=r"terminal_metadata\.direction must be 'cw' or 'ccw'"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_object_names=("body_1",),
        )


def test_build_single_imported_modeled_object_entry_rejects_bad_plane(tmp_path: Path) -> None:
    modeled_object = _modeled_object()
    modeled_object["plane"] = "ZX"

    with pytest.raises(ValueError, match=r"modeled_object\.plane must be one of \['XY', 'YZ'\]"):
        build_single_imported_modeled_object_entry(
            modeled_object=modeled_object,
            imported_object_names=("body_1",),
        )

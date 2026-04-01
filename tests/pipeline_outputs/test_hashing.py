from __future__ import annotations

import re
from typing import cast

import pytest

from peetsfea.identity.hashing import (
    compose_design_id,
    compute_design_unique_hash,
    compute_toml_space_hash,
    object_name_tag_from_design_id,
)
from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance, SelectedParameters


def _selected_parameters() -> SelectedParameters:
    return {
        "tx_dd_outer_x": 40.0,
        "tx_dd_outer_y": 40.0,
        "tx_vertical_outer_x": 40.0,
        "tx_vertical_outer_y": 40.0,
        "rx_dd_outer_x": 40.0,
        "rx_dd_outer_y": 40.0,
        "corner_mode": 0,
        "tx_dd_pair_spacing_ratio": 0.1,
        "rx_dd_pair_spacing_ratio": 0.02,
        "tx_vertical_center_gap_mm": 10.0,
        "tx_dd_pair_spacing_mm": 40.0,
        "rx_dd_pair_spacing_mm": 40.0,
        "tx_vertical_span_mm": 10.0,
        "tv_width_mm": 1200.0,
        "tv_height_mm": 700.0,
        "tv_thickness_mm": 9.0,
        "tv_base_z_mm": 700.0,
        "tx_region_outer_w_mm": 300.0,
        "tx_region_outer_h_mm": 200.0,
        "tx_region_thickness_mm": 20.0,
        "tx_region_vertical_z_mm": 8.0,
        "tx_region_dd_z_mm": 7.0,
        "rx_region_outer_w_mm": 280.0,
        "rx_region_outer_h_mm": 180.0,
        "rx_region_thickness_mm": 4.0,
        "wall_thickness_mm": 200.0,
        "wall_size_y_mm": 4000.0,
        "wall_size_z_mm": 3000.0,
        "floor_thickness_mm": 300.0,
        "floor_size_x_mm": 5000.0,
        "floor_size_y_mm": 5000.0,
        "ferrite_present": True,
        "rx_ferrite_thickness_mm": 2.0,
        "tx_ferrite_thickness_mm": 2.0,
        "tx_ferrite_gap_mm": 3.1,
        "ferrite_relative_permeability": 500.0,
        "shelf_height_mm": 400.0,
        "shelf_min_size_x_mm": 350.0,
        "rx_region_bottom_from_tv_mm": 1.0,
        "tx_dd_top_offset_ratio": 0.0,
        "tx_dd_top_clearance_mm": 0.0,
        "tx_vertical_orientation_mode": 1,
        "rx_face_clearance_mm": 0.0,
        "tx_main_1_z_from_tx_main_0_mm": 3.0,
        "dd_mirror_plane": "XZ",
        "rx_plane": "YZ",
        "neo_tx_dd_right_terminal_path": "D_ccw_to_d",
        "neo_tx_dd_left_terminal_path": "a_cw_to_A",
        "neo_tx_vertical_zx_terminal_path": "B_ccw_to_c",
        "tx_vertical_plane": "ZX",
        "via_diameter_mm": 0.6,
        "pcb_thickness_mm": 1.6,
        "cu_thickness_mm": 0.035,
        "via_diameter": 0.6,
        "pcb_thickness": 1.6,
        "cu_thickness": 0.035,
        "fr4_er": 4.4,
    }


def _selected_group_geometry() -> list[GroupGeometryParams]:
    return [
        {"kind": "tx_dd", "turn_count": 6, "band_ratio": 0.3, "metal_ratio": 2.0 / 3.0, "trace": 1.0, "gap": 0.5},
        {"kind": "tx_vertical", "turn_count": 4, "band_ratio": 0.25, "metal_ratio": 0.9 / 1.3, "trace": 0.9, "gap": 0.4},
        {"kind": "rx_dd", "turn_count": 7, "band_ratio": 0.35, "metal_ratio": 1.1 / 1.4, "trace": 1.1, "gap": 0.3},
    ]


def test_compute_toml_space_hash_uses_toml_hash_prefix() -> None:
    toml_hash = "a" * 64
    assert compute_toml_space_hash(toml_hash) == "aaaa"


def test_compute_design_unique_hash_is_deterministic() -> None:
    selected = _selected_parameters()
    group_geometry = _selected_group_geometry()
    selected_coil_groups: list[ResolvedCoilGroup] = [
        cast(ResolvedCoilGroup, {"kind": "tx_dd", "layer_count": 1, "spacing_mm": 5.0, "instance_transforms": []}),
        cast(
            ResolvedCoilGroup,
            {"kind": "tx_vertical", "requested_count": 1, "selected_count": 1, "spacing_mm": 2.0, "instance_transforms": []},
        ),
        cast(
            ResolvedCoilGroup,
            {"kind": "rx_dd", "requested_count": 2, "selected_count": 2, "spacing_mm": 1.0, "instance_transforms": []},
        ),
    ]
    selected_pcbs: list[ResolvedPcbInstance] = [
        {
            "id": "tx_main_0",
            "role": "tx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [{"kind": "tx_dd", "selector_mode": "index", "selector_index": 0}],
        }
    ]
    first = compute_design_unique_hash("b" * 64, "c" * 40, selected, group_geometry, selected_coil_groups, selected_pcbs)
    second = compute_design_unique_hash("b" * 64, "c" * 40, selected, group_geometry, selected_coil_groups, selected_pcbs)
    assert first == second
    assert re.fullmatch(r"[0-9a-f]{4}", first) is not None


def test_compute_design_unique_hash_changes_when_source_space_hash_input_changes() -> None:
    selected = _selected_parameters()
    group_geometry = _selected_group_geometry()
    selected_coil_groups: list[ResolvedCoilGroup] = [
        {"kind": "tx_dd", "layer_count": 2, "spacing_mm": 5.0, "instance_transforms": []},
    ]
    selected_pcbs: list[ResolvedPcbInstance] = [
        {
            "id": "tx_main_0",
            "role": "tx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [{"kind": "tx_dd", "selector_mode": "index", "selector_index": 0}],
        }
    ]
    first = compute_design_unique_hash("b" * 64, "c" * 40, selected, group_geometry, selected_coil_groups, selected_pcbs)
    second = compute_design_unique_hash("d" * 64, "c" * 40, selected, group_geometry, selected_coil_groups, selected_pcbs)
    assert first != second


def test_compose_design_id_format() -> None:
    design_id = compose_design_id("dead", "cafe", -3, 2)
    assert design_id == "-000003_dead_cafe_2"
    assert re.fullmatch(r"-?[0-9]{6,}_[0-9a-f]{4}_[0-9a-f]{4}_[0-9]+", design_id) is not None


def test_object_name_tag_from_design_id_uses_unique_hash_segment() -> None:
    assert object_name_tag_from_design_id("-000003_dead_cafe_2") == "dead"


def test_object_name_tag_from_design_id_accepts_pre_normalized_direct_tag() -> None:
    assert object_name_tag_from_design_id("demo") == "demo"


def test_object_name_tag_from_design_id_hashes_non_normalized_design_name() -> None:
    assert object_name_tag_from_design_id("demo_design") == "d7d4"


def test_compute_toml_space_hash_rejects_bad_toml_hash() -> None:
    with pytest.raises(ValueError, match="toml_hash"):
        compute_toml_space_hash("A" * 64)

    with pytest.raises(ValueError, match="toml_hash"):
        compute_toml_space_hash("a" * 63)

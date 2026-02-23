from __future__ import annotations

import re

import pytest

from peetsfea.identity.hashing import compose_design_id, compute_design_unique_hash, compute_toml_space_hash
from peetsfea.types.manifest import SelectedParameters


def _selected_parameters() -> SelectedParameters:
    return {
        "outer_x": 40.0,
        "outer_y": 40.0,
        "turn_count_max": 6,
        "inner_margin_x": 2.0,
        "inner_margin_y": 2.0,
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
        "shelf_height_mm": 400.0,
        "shelf_min_size_x_mm": 350.0,
        "rx_region_bottom_from_tv_mm": 1.0,
        "tx_dd_top_clearance_mm": 0.0,
        "rx_face_clearance_mm": 0.0,
        "dd_mirror_plane": "XZ",
        "rx_plane": "YZ",
        "turns": 6,
        "outer": 40.0,
        "trace": 1.0,
        "gap": 0.5,
        "via_diameter_mm": 0.6,
        "pcb_thickness_mm": 1.6,
        "cu_thickness_mm": 0.035,
        "profile_id": "p1",
        "trace_profile_base": 1.0,
        "trace_profile_outer_bias": 0.1,
        "trace_profile_inner_bias": -0.1,
        "trace_profile_clamp_min": 0.2,
        "gap_profile_base": 0.5,
        "gap_profile_outer_bias": 0.05,
        "gap_profile_inner_bias": -0.05,
        "gap_profile_clamp_min": 0.15,
        "via_diameter": 0.6,
        "pcb_thickness": 1.6,
        "cu_thickness": 0.035,
        "fr4_er": 4.4,
    }


def test_compute_toml_space_hash_uses_toml_hash_prefix() -> None:
    toml_hash = "a" * 64
    assert compute_toml_space_hash(toml_hash) == "aaaaaaaa"


def test_compute_design_unique_hash_is_deterministic() -> None:
    selected = _selected_parameters()
    first = compute_design_unique_hash("b" * 64, "c" * 40, 7, selected)
    second = compute_design_unique_hash("b" * 64, "c" * 40, 7, selected)
    assert first == second
    assert re.fullmatch(r"[0-9a-f]{8}", first) is not None


def test_compose_design_id_format() -> None:
    design_id = compose_design_id("deadbeef", "cafebabe", -3)
    assert design_id == "deadbeef_cafebabe_-3"
    assert re.fullmatch(r"[0-9a-f]{8}_[0-9a-f]{8}_-?[0-9]+", design_id) is not None


def test_compute_toml_space_hash_rejects_bad_toml_hash() -> None:
    with pytest.raises(ValueError, match="toml_hash"):
        compute_toml_space_hash("A" * 64)

    with pytest.raises(ValueError, match="toml_hash"):
        compute_toml_space_hash("a" * 63)

from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
from typing import cast

import pytest

from peetsfea.type2_plate_stack import build_plate_stack_scene_data
from peetsfea.type2_plate_stack import total_plate_stack_thickness_mm
from peetsfea.type2_step_export import export_type2_step_artifacts
from peetsfea.type2_step_spec import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec import load_type2_step_spec
from peetsfea.type2_step_spec import resolve_modeled_plate_stack_z_usage_ratio
from peetsfea.type2_step_spec import resolve_modeled_tx_array_x_usage_ratio
from peetsfea.type2_step_spec import resolve_modeled_tx_coil_count
from tests.type2.test_generate_type2_step import _step_shapes_by_label
from tests.type2.test_generate_type2_step import _type2_tx_plate_stack_spec_text
from tests.type2.test_generate_type2_step import _write_spec


def _seed_for_tx_coil_count(*, spec_path: Path, target_count: int) -> int:
    spec = load_type2_step_spec(spec_path)
    tx_spec = next(entry for entry in spec.modeled_objects if entry.object_id == "tx_plate_stack")
    assert isinstance(tx_spec, ModeledTxPlateStackSpec)
    for seed in range(256):
        if resolve_modeled_tx_coil_count(tx_spec, seed=seed) == target_count:
            return seed
    raise AssertionError(f"failed to resolve seed for target tx_coil_count={target_count}")


def _rotate_point_about_axis_y(
    *,
    point: tuple[float, float, float],
    axis_x: float,
    axis_z: float,
    angle_deg: float,
) -> tuple[float, float, float]:
    rad = angle_deg * (3.141592653589793 / 180.0)
    cos_theta = math.cos(rad)
    sin_theta = math.sin(rad)
    point_x, point_y, point_z = point
    translated_x = point_x - axis_x
    translated_z = point_z - axis_z
    return (
        axis_x + (cos_theta * translated_x) + (sin_theta * translated_z),
        point_y,
        axis_z + (-sin_theta * translated_x) + (cos_theta * translated_z),
    )


def test_export_type2_tx_plate_stack_array_contract(tmp_path: Path) -> None:
    spec_text = _type2_tx_plate_stack_spec_text(
        tx_coil_count_range="[true, 1.0, 4.0, 4]",
        tx_array_x_usage_ratio_range="[false, 0.6, 0.6, 1]",
    )
    if "origin_xyz = [200.0, -100.0, 0.0]" not in spec_text:
        raise AssertionError("test fixture drift: rx_region_max origin expected in template")
    spec_text = spec_text.replace(
        "origin_xyz = [200.0, -100.0, 0.0]",
        "origin_xyz = [200.0, -100.0, 120.0]",
    )
    toml_path = _write_spec(
        tmp_path,
        spec_text,
    )
    seed = _seed_for_tx_coil_count(spec_path=toml_path, target_count=3)
    spec = load_type2_step_spec(toml_path)
    tx_spec = next(entry for entry in spec.modeled_objects if entry.object_id == "tx_plate_stack")
    assert isinstance(tx_spec, ModeledTxPlateStackSpec)
    tx_region_spec = next(entry for entry in spec.non_model_objects if entry.object_id == "tx_region")

    tx_array_x_usage_ratio = resolve_modeled_tx_array_x_usage_ratio(tx_spec, seed=seed)
    tx_z_usage_ratio = resolve_modeled_plate_stack_z_usage_ratio(tx_spec, seed=seed)
    tx_region_origin_x, tx_region_origin_y, tx_region_origin_z = tx_region_spec.origin_xyz
    tx_region_size_x, tx_region_size_y, tx_region_size_z = tx_region_spec.size_xyz
    branch_total_thickness = total_plate_stack_thickness_mm(spec=tx_spec)
    tx_owner_max_branch_origin_x = tx_region_origin_x + tx_region_size_x - branch_total_thickness
    tx_full_branch_origin_span_x = tx_owner_max_branch_origin_x - tx_region_origin_x
    tx_branch_origin_span_x = tx_full_branch_origin_span_x * tx_array_x_usage_ratio
    branch_step_x = tx_branch_origin_span_x / 2.0
    branch_active_size_z = tx_region_size_z * tx_z_usage_ratio
    branch_top_z = tx_region_origin_z + tx_region_size_z

    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "step",
        ledger_path=tmp_path / "step" / "type2_step_ledger.json",
        seed=seed,
    )

    tx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_plate_stack")
    expected_names = tx_entry["expected_exported_body_names"]
    assert "tx_plate_copper" not in expected_names
    assert "tx_b0_plate_copper" in expected_names
    assert "tx_b1_plate_copper" in expected_names
    assert "tx_b2_plate_copper" in expected_names
    assert "tx_array_input_sheet_s0" in expected_names
    assert "tx_array_output_sheet_s1" in expected_names
    assert "tx_b0_pcb_wall" in expected_names
    assert "tx_b1_stack_ferrite" in expected_names
    assert "tx_b2_pcb_coil" in expected_names

    tx_groups = tx_entry["expected_exported_body_groups"]
    assert len(tx_groups) == 2
    assert tx_groups[0]["group_name"] == "g_copper_tx"
    assert tx_groups[0]["member_body_names"] == (
        "tx_b0_plate_copper",
        "tx_b1_plate_copper",
        "tx_b2_plate_copper",
        "tx_array_input_sheet_s0",
        "tx_array_output_sheet_s0",
        "tx_array_input_sheet_s1",
        "tx_array_output_sheet_s1",
    )
    assert tx_groups[1]["group_name"] == "g_ferrite_tx"
    assert len(tx_groups[1]["member_body_names"]) == 9

    scene_shapes_by_label = _step_shapes_by_label(Path(ledger["scene_step_path"]))
    assert "tx_b0_plate_copper" in scene_shapes_by_label
    assert "tx_array_input_sheet_s0" in scene_shapes_by_label
    assert len(tuple(scene_shapes_by_label["tx_array_input_sheet_s0"].solids())) == 0
    assert len(tuple(scene_shapes_by_label["tx_array_input_sheet_s0"].faces())) == 1
    assert "tx_array_output_sheet_s0" in scene_shapes_by_label
    assert len(tuple(scene_shapes_by_label["tx_array_output_sheet_s0"].solids())) == 0
    assert len(tuple(scene_shapes_by_label["tx_array_output_sheet_s0"].faces())) == 1
    for connector_name in ("tx_array_input_sheet_s0", "tx_array_input_sheet_s1", "tx_array_output_sheet_s0", "tx_array_output_sheet_s1"):
        connector_shape = scene_shapes_by_label[connector_name]
        assert len(tuple(connector_shape.solids())) == 0
        assert len(tuple(connector_shape.faces())) == 1
    assert "tx_b0_pcb_wall" in scene_shapes_by_label
    assert "tx_b2_pcb_coil" in scene_shapes_by_label

    tx_region_member = next(
        member for member in ledger["non_model_objects"][0]["member_objects"] if member["object_id"] == "tx_region"
    )
    tx_region_coordinates = cast(dict[str, object], tx_region_member["canonical_coordinates"])
    tx_region_min_xyz = cast(tuple[float, float, float], tx_region_coordinates["outer_bounds_min_xyz"])
    tx_region_size_xyz = cast(tuple[float, float, float], tx_region_coordinates["outer_bounds_size_xyz"])
    tx_region_top_z = tx_region_min_xyz[2] + tx_region_size_xyz[2]
    tx_region_bottom_z = tx_region_min_xyz[2]
    tx_region_max_z = tx_region_min_xyz[2] + tx_region_size_xyz[2]

    rx_region_member = next(
        member for member in ledger["non_model_objects"][0]["member_objects"] if member["object_id"] == "rx_region_max"
    )
    rx_region_coordinates = cast(dict[str, object], rx_region_member["canonical_coordinates"])
    rx_region_min_xyz = cast(tuple[float, float, float], rx_region_coordinates["outer_bounds_min_xyz"])
    rx_region_size_xyz = cast(tuple[float, float, float], rx_region_coordinates["outer_bounds_size_xyz"])

    tx_coordinates = cast(dict[str, object], tx_entry["canonical_coordinates"])
    tx_min_xyz = cast(tuple[float, float, float], tx_coordinates["outer_bounds_min_xyz"])
    tx_size_xyz = cast(tuple[float, float, float], tx_coordinates["outer_bounds_size_xyz"])
    connector_vertices_by_name = cast(dict[str, object], tx_coordinates["connector_sheet_vertices_xyz_by_name"])
    assert set(connector_vertices_by_name) == {
        "tx_array_input_sheet_s0",
        "tx_array_output_sheet_s0",
        "tx_array_input_sheet_s1",
        "tx_array_output_sheet_s1",
    }
    for raw_vertices in connector_vertices_by_name.values():
        connector_vertices = cast(tuple[tuple[float, float, float], ...], raw_vertices)
        assert len(connector_vertices) == 4
        connector_y = connector_vertices[0][1]
        assert all(vertex[1] == pytest.approx(connector_y) for vertex in connector_vertices)
        assert connector_y == pytest.approx(tx_min_xyz[1])
    assert tx_min_xyz[2] + tx_size_xyz[2] == pytest.approx(tx_region_top_z)
    expected_tx_size_x = branch_total_thickness + ((tx_region_size_xyz[0] - branch_total_thickness) * 0.6)
    assert tx_min_xyz[0] == pytest.approx(tx_region_min_xyz[0])
    assert tx_size_xyz[0] > expected_tx_size_x + 1e-6

    copied_angles = cast(tuple[float, ...], tx_coordinates["copied_branch_rotation_angles_deg"])
    assert len(copied_angles) == 3
    assert copied_angles[0] == pytest.approx(0.0)
    assert copied_angles[1] < 0.0
    assert copied_angles[2] < 0.0
    copied_hinge_edges = cast(
        tuple[tuple[tuple[float, float, float], tuple[float, float, float]], ...],
        tx_coordinates["copied_branch_hinge_edge_endpoints_xyz"],
    )
    assert len(copied_hinge_edges) == 3
    expected_rotation_target = (
        rx_region_min_xyz[0] + (rx_region_size_xyz[0] / 2.0),
        0.0,
        rx_region_min_xyz[2],
    )
    assert tx_coordinates["copied_branch_rotation_target_xyz"] == pytest.approx(expected_rotation_target)
    assert expected_rotation_target[2] > tx_region_top_z

    tx_terminal_metadata = cast(dict[str, object], tx_entry["terminal_metadata"])
    assert tx_terminal_metadata["kind"] == "stub_port"
    assert tx_terminal_metadata["input_stub_body_name"] == "tx_array_input_sheet_s0"
    assert tx_terminal_metadata["output_stub_body_name"] == "tx_array_output_sheet_s0"
    terminal_sheet_vertices = cast(tuple[tuple[float, float, float], ...], tx_terminal_metadata["port_sheet_vertices_xyz"])
    assert len(terminal_sheet_vertices) == 4
    branch_input_x_values: list[float] = []
    branch_output_x_values: list[float] = []
    branch_input_z_ranges: list[tuple[float, float]] = []
    branch_output_z_ranges: list[tuple[float, float]] = []

    for branch_index in range(3):
        branch_spec = replace(
            tx_spec,
            z_usage_ratio=type(tx_spec.z_usage_ratio)(is_integer=False, start=1.0, end=1.0, count=1),
        )
        branch_origin_x = tx_region_origin_x + (branch_step_x * float(branch_index))
        branch_origin_spec = replace(
            tx_region_spec,
            origin_xyz=(branch_origin_x, tx_region_origin_y, branch_top_z - branch_active_size_z),
            size_xyz=(branch_total_thickness, tx_region_size_y, branch_active_size_z),
        )
        branch_shapes, branch_scene_data = build_plate_stack_scene_data(
            branch_spec,
            owner_spec=branch_origin_spec,
            seed=seed,
        )
        branch_terminal_metadata = cast(
            dict[str, object],
            branch_scene_data["terminal_metadata"],
        )
        branch_vertices = cast(
            tuple[tuple[float, float, float], ...], branch_terminal_metadata["port_sheet_vertices_xyz"]
        )
        assert len(branch_vertices) == 4
        if branch_index > 0:
            branch_axis_x = copied_hinge_edges[branch_index][0][0]
            branch_vertices = tuple(
                _rotate_point_about_axis_y(
                    point=point,
                    axis_x=branch_axis_x,
                    axis_z=branch_top_z,
                    angle_deg=copied_angles[branch_index],
                )
                for point in branch_vertices
            )
        branch_input_x_values.append(branch_vertices[0][0])
        branch_output_x_values.append(branch_vertices[1][0])
        branch_input_z_ranges.append((min(branch_vertices[0][2], branch_vertices[3][2]), max(branch_vertices[0][2], branch_vertices[3][2])))
        branch_output_z_ranges.append((min(branch_vertices[1][2], branch_vertices[2][2]), max(branch_vertices[1][2], branch_vertices[2][2])))

        if branch_index > 0:
            hinge_edge = copied_hinge_edges[branch_index]
            assert hinge_edge[0][2] == pytest.approx(tx_region_top_z)
            assert hinge_edge[1][2] == pytest.approx(tx_region_top_z)
            assert branch_shapes

            for suffix in ("pcb_wall", "stack_pet_psa", "stack_ferrite", "stack_air", "pcb_coil"):
                branch_shape = scene_shapes_by_label[f"tx_b{branch_index}_{suffix}"]
                assert branch_shape.bounding_box().min.Z >= tx_region_bottom_z - 1e-6
                assert branch_shape.bounding_box().max.Z <= tx_region_max_z + 1e-6

    expected_input_z_min = min(z_min for z_min, _z_max in branch_input_z_ranges)
    expected_input_z_max = max(z_max for _z_min, z_max in branch_input_z_ranges)
    expected_output_z_min = min(z_min for z_min, _z_max in branch_output_z_ranges)
    expected_output_z_max = max(z_max for _z_min, z_max in branch_output_z_ranges)
    expected_terminal_sheet = (
        (min(branch_input_x_values), tx_region_min_xyz[1] - 5.0, expected_input_z_min),
        (max(branch_output_x_values), tx_region_min_xyz[1] - 5.0, expected_output_z_min),
        (max(branch_output_x_values), tx_region_min_xyz[1] - 5.0, expected_output_z_max),
        (min(branch_input_x_values), tx_region_min_xyz[1] - 5.0, expected_input_z_max),
    )
    for expected_vertex, actual_vertex in zip(expected_terminal_sheet, terminal_sheet_vertices, strict=True):
        assert expected_vertex == pytest.approx(actual_vertex)
    assert tx_terminal_metadata["start_point_plane_mm"] == pytest.approx((tx_region_min_xyz[1] - 5.0, (expected_input_z_min + expected_input_z_max) / 2.0))
    assert tx_terminal_metadata["end_point_plane_mm"] == pytest.approx((tx_region_min_xyz[1] - 5.0, (expected_output_z_min + expected_output_z_max) / 2.0))

    for branch_index in range(3):
        branch_shape = scene_shapes_by_label[f"tx_b{branch_index}_pcb_wall"]
        if branch_index == 0:
            assert branch_shape.bounding_box().max.Z == pytest.approx(tx_region_top_z)
        else:
            assert branch_shape.bounding_box().max.Z <= tx_region_top_z + 1e-6

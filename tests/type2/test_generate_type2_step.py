from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import build123d as bd
import pytest

from entry.generate_type2_step import export_type2_step_artifacts
from entry.generate_type2_step import load_type2_step_spec
from peetsfea.tx_rect_void import build_tx_rect_void_box_specs
from peetsfea.tx_rect_void import load_tx_rect_void_spec
from peetsfea.tx_rect_void import modeled_body_bounds_from_boxes
from peetsfea.tx_rect_void import realize_tx_rect_void_spec


def _range(is_integer: bool, start: float, end: float, count: int) -> str:
    flag = "true" if is_integer else "false"
    return f"[{flag}, {start}, {end}, {count}]"


def _type2_spec_text(
    *,
    modeled_object_id: str = "tx_rect_void_coil",
    modeled_role: str = "tx_single_coil",
    terminal_path: str = "A_cw_to_a",
    layer_count: int = 1,
) -> str:
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.type2.step.v1"
runtime_compatible = false

[design]
units = "mm"

[[non_model_objects]]
id = "floor"
kind = "floor"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "XY"
origin_xyz = [0.0, -10.0, -1.0]
size_xyz = [20.0, 20.0, 1.0]

[[non_model_objects]]
id = "shelf"
kind = "shelf"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "XY"
origin_xyz = [0.0, -10.0, 0.0]
size_xyz = [10.0, 20.0, 4.0]

[[non_model_objects]]
id = "wall"
kind = "wall"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [-1.0, -10.0, 0.0]
size_xyz = [1.0, 20.0, 10.0]

[[non_model_objects]]
id = "tv"
kind = "tv"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [0.0, -5.0, 5.0]
size_xyz = [1.0, 10.0, 4.0]

[[non_model_objects]]
id = "tx_region"
kind = "tx_region"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "XY"
origin_xyz = [0.0, -140.0, 0.0]
size_xyz = [160.0, 280.0, 90.0]

[[non_model_objects]]
id = "rx_region_max"
kind = "rx_region_max"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [200.0, -100.0, 0.0]
size_xyz = [10.0, 200.0, 200.0]

[[modeled_objects]]
object_id = "{modeled_object_id}"
role = "{modeled_role}"
material = "composite"
model_state = true
pcb_thickness_mm = 1.6
copper_thickness_mm = 0.1

[modeled_objects.outer_x_mm]
range = {_range(False, 50.0, 50.0, 1)}
[modeled_objects.outer_y_mm]
range = {_range(False, 60.0, 60.0, 1)}
[modeled_objects.turn_count]
range = {_range(True, 2.0, 2.0, 1)}
[modeled_objects.layer_count]
range = {_range(True, float(layer_count), float(layer_count), 1)}
[modeled_objects.layer_gap_mm]
range = {_range(False, 2.0, 2.0, 1)}
[modeled_objects.terminal_stub_length_mm]
range = {_range(False, 5.0, 5.0, 1)}
[modeled_objects.void_x_over_outer_x]
range = {_range(False, 0.3, 0.3, 1)}
[modeled_objects.void_y_over_outer_y]
range = {_range(False, 0.3, 0.3, 1)}
[modeled_objects.void_center_x_over_outer_x]
range = {_range(False, 0.0, 0.0, 1)}
[modeled_objects.void_center_y_over_outer_y]
range = {_range(False, 0.0, 0.0, 1)}
[modeled_objects.margin_ratio]
range = {_range(False, 0.05, 0.05, 1)}
[modeled_objects.metal_fill_factor]
range = {_range(False, 0.5, 0.5, 1)}
[modeled_objects.terminal_path]
value = "{terminal_path}"
""".strip()


def _tx_rect_void_spec_text(*, terminal_path: str = "A_cw_to_a") -> str:
    return _tx_rect_void_spec_text_with_layer_count(terminal_path=terminal_path, layer_count=1)


def _tx_rect_void_spec_text_with_layer_count(*, terminal_path: str = "A_cw_to_a", layer_count: int = 1) -> str:
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.tx_rect_void_coil.step.v1"
runtime_compatible = false

[design]
units = "mm"

[manufacturing]
pcb_thickness_mm = 1.6
copper_thickness_mm = 0.1

[tx_coil.outer_x_mm]
range = {_range(False, 50.0, 50.0, 1)}
[tx_coil.outer_y_mm]
range = {_range(False, 60.0, 60.0, 1)}
[tx_coil.turn_count]
range = {_range(True, 2.0, 2.0, 1)}
[tx_coil.layer_count]
range = {_range(True, float(layer_count), float(layer_count), 1)}
[tx_coil.layer_gap_mm]
range = {_range(False, 2.0, 2.0, 1)}
[tx_coil.terminal_stub_length_mm]
range = {_range(False, 5.0, 5.0, 1)}
[tx_coil.void_x_over_outer_x]
range = {_range(False, 0.3, 0.3, 1)}
[tx_coil.void_y_over_outer_y]
range = {_range(False, 0.3, 0.3, 1)}
[tx_coil.void_center_x_over_outer_x]
range = {_range(False, 0.0, 0.0, 1)}
[tx_coil.void_center_y_over_outer_y]
range = {_range(False, 0.0, 0.0, 1)}
[tx_coil.margin_ratio]
range = {_range(False, 0.05, 0.05, 1)}
[tx_coil.metal_fill_factor]
range = {_range(False, 0.5, 0.5, 1)}
[tx_coil.terminal_path]
value = "{terminal_path}"
""".strip()


def _write_spec(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "type2_fixed.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _single_layer_example_text(source_toml: Path) -> str:
    return source_toml.read_text(encoding="utf-8").replace(
        "[modeled_objects.layer_count]\nrange = [true, 2, 2, 1]",
        "[modeled_objects.layer_count]\nrange = [true, 1, 1, 1]",
        1,
    )


def _body_bbox(step_path: Path, *, label: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    shape = bd.import_step(step_path)
    children = tuple(shape.children) if tuple(shape.children) else (shape,)
    matches = [child for child in children if child.label == label]
    assert len(matches) == 1
    bbox = matches[0].bounding_box()
    return ((bbox.min.X, bbox.min.Y, bbox.min.Z), (bbox.max.X, bbox.max.Y, bbox.max.Z))


def _assert_zero_intersection_volume(first: object, second: object) -> None:
    assert isinstance(first, bd.Shape)
    assert isinstance(second, bd.Shape)
    shared_shape = first.intersect(second)
    if shared_shape is None:
        return
    assert isinstance(shared_shape, bd.Shape)
    assert shared_shape.volume == pytest.approx(0.0, abs=1e-9)


def test_load_example_type2_toml_parses_expected_registry_shape() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_fixed.toml"
    spec = load_type2_step_spec(source_toml)

    assert len(spec.non_model_objects) == 6
    assert len(spec.modeled_objects) == 2
    modeled_by_id = {entry.object_id: entry for entry in spec.modeled_objects}
    tx_entry = modeled_by_id["tx_rect_void_coil"]
    rx_entry = modeled_by_id["rx_rect_void_coil"]
    assert tx_entry.role == "tx_single_coil"
    assert tx_entry.outer_x_mm.start == pytest.approx(157.810110508654)
    assert tx_entry.outer_y_mm.end == pytest.approx(259.88256431122)
    assert tx_entry.turn_count.start == pytest.approx(2.0)
    assert tx_entry.terminal_stub_length_mm.start == pytest.approx(5.0)
    assert tx_entry.layer_count.end == pytest.approx(1.0)
    assert rx_entry.role == "rx_single_coil"
    assert rx_entry.outer_x_mm.start == pytest.approx(318.6671250920941)
    assert rx_entry.outer_y_mm.end == pytest.approx(104.169329765159)
    assert rx_entry.turn_count.start == pytest.approx(3.0)
    assert rx_entry.terminal_stub_length_mm.end == pytest.approx(5.0)


def test_load_type2_step_spec_rejects_duplicate_object_id(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(modeled_object_id="floor"))

    with pytest.raises(ValueError, match=r"duplicate object id: floor"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_unsupported_modeled_role(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(modeled_role="bad_single_coil"))

    with pytest.raises(ValueError, match=r"unsupported modeled object role: bad_single_coil"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_missing_required_modeled_field(tmp_path: Path) -> None:
    terminal_section_lines = {"[modeled_objects.terminal_path]", 'value = "A_cw_to_a"'}
    toml_text = "\n".join(line for line in _type2_spec_text().splitlines() if line not in terminal_section_lines)
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(ValueError, match=r"modeled_objects\[0\] is missing required key 'terminal_path'"):
        load_type2_step_spec(toml_path)


def test_export_type2_step_artifacts_writes_single_scene_step_and_ledger(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_fixed.toml"
    output_dir = tmp_path / "out"
    ledger_path = tmp_path / "out" / "type2_ledger.json"

    ledger = export_type2_step_artifacts(
        toml_path=source_toml,
        output_dir=output_dir,
        ledger_path=ledger_path,
        seed=0,
    )

    assert ledger_path.is_file()
    assert ledger_path.stat().st_size > 0
    scene_step_path = Path(ledger["scene_step_path"])
    assert scene_step_path.is_file()
    assert scene_step_path.stat().st_size > 0
    assert scene_step_path.name == "type2_scene.step"
    assert (output_dir / "type2_non_model_scene.step").exists() is False
    assert (output_dir / "type2_combined_preview.step").exists() is False
    assert (output_dir / "objects").exists() is False
    assert len(ledger["non_model_objects"]) == 1
    assert len(ledger["modeled_objects"]) == 2
    non_model_entry = ledger["non_model_objects"][0]
    assert non_model_entry["object_id"] == "type2_non_model_scene"
    assert non_model_entry["role"] == "non_model_scene"
    assert non_model_entry["plane"] == "mixed"
    assert non_model_entry["member_object_ids"] == ("environment", "tx_region", "rx_region_max")
    member_objects = non_model_entry["member_objects"]
    assert len(member_objects) == 3
    environment_member = next(member for member in member_objects if member["object_id"] == "environment")
    assert environment_member["role"] == "environment"
    assert environment_member["plane"] == "mixed"
    assert environment_member["canonical_coordinates"]["outer_bounds_min_xyz"] == (-200.0, -2500.0, -761.0)
    assert environment_member["canonical_coordinates"]["outer_bounds_size_xyz"] == (5200.0, 5000.0, 3300.0)
    tx_region_member = next(member for member in member_objects if member["object_id"] == "tx_region")
    assert tx_region_member["role"] == "tx_region"
    assert tx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"] == (0.0, -140.0, 0.0)
    assert tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"] == (160.0, 280.0, 90.0)
    rx_region_member = next(member for member in member_objects if member["object_id"] == "rx_region_max")
    assert rx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"] == (0.0, -280.0, 139.0)
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert payload["scene_step_path"] == str(scene_step_path)
    modeled_by_id = {entry["object_id"]: entry for entry in payload["modeled_objects"]}
    assert set(modeled_by_id) == {"tx_rect_void_coil", "rx_rect_void_coil"}
    for modeled_entry in ledger["modeled_objects"]:
        source_metadata_path = Path(modeled_entry["source_metadata_path"])
        assert source_metadata_path.is_file()
        source_metadata_payload = json.loads(source_metadata_path.read_text(encoding="utf-8"))
        assert source_metadata_payload["source_toml_path"] == str(source_toml)
        assert source_metadata_payload["scene_step_path"] == str(scene_step_path)
    tx_entry = modeled_by_id["tx_rect_void_coil"]
    assert tx_entry["role"] == "tx_single_coil"
    assert tx_entry["plane"] == "XY"
    assert tx_entry["placement_owner_id"] == "tx_region"
    assert tx_entry["terminal_metadata"]["path"] == "D_ccw_to_d"
    tx_expected_names = [f"tx_pcb_l{index}" for index in range(len(tx_entry["canonical_coordinates"]["pcb_layer_z_positions_mm"]))]
    if len(tx_entry["canonical_coordinates"]["pcb_layer_z_positions_mm"]) > 1:
        tx_expected_names.append("tx_copper_stack")
    else:
        tx_expected_names.append("tx_copper_l0")
    assert tx_entry["expected_exported_body_names"] == tx_expected_names
    assert tx_entry["expected_exported_body_count"] == len(tx_expected_names)
    modeled_canonical = tx_entry["canonical_coordinates"]
    tx_min_x, tx_min_y, tx_min_z = modeled_canonical["outer_bounds_min_xyz"]
    tx_size_x, tx_size_y, tx_size_z = modeled_canonical["outer_bounds_size_xyz"]
    region_min_x, region_min_y, region_min_z = tx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    region_size_x, region_size_y, _region_size_z = tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"]
    assert tx_min_x == pytest.approx(region_min_x + (region_size_x - tx_size_x) / 2.0)
    assert tx_min_y == pytest.approx(region_min_y + (region_size_y - tx_size_y) / 2.0)
    assert tx_min_z == pytest.approx(region_min_z + tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"][2] - tx_size_z)
    assert modeled_canonical["outer_bounds_min_xyz"][1] + (tx_size_y / 2.0) == pytest.approx(0.0)
    tx_copper_label = "tx_copper_stack" if len(tx_entry["canonical_coordinates"]["pcb_layer_z_positions_mm"]) > 1 else "tx_copper_l0"
    tx_step_min_xyz, tx_step_max_xyz = _body_bbox(scene_step_path, label=tx_copper_label)
    tx_region_center_x = region_min_x + (region_size_x / 2.0)
    tx_region_center_y = region_min_y + (region_size_y / 2.0)
    assert (tx_step_min_xyz[0] + tx_step_max_xyz[0]) / 2.0 == pytest.approx(tx_region_center_x, abs=1e-8)
    assert (tx_step_min_xyz[1] + tx_step_max_xyz[1]) / 2.0 == pytest.approx(tx_region_center_y, abs=1e-8)
    assert tx_step_max_xyz[2] == pytest.approx(region_min_z + tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"][2])
    imported_scene = bd.import_step(scene_step_path)
    scene_children = tuple(imported_scene.children)
    scene_children_by_label = {child.label: child for child in scene_children}
    expected_scene_labels = {"environment", "tx_region", "rx_region_max", "rx_pcb_l0", "rx_copper_l0", *tx_expected_names}
    assert set(scene_children_by_label) == expected_scene_labels
    for label in expected_scene_labels:
        assert type(scene_children_by_label[label]).__name__ == "Solid"
    _assert_zero_intersection_volume(scene_children_by_label[tx_expected_names[0]], scene_children_by_label[tx_copper_label])
    _assert_zero_intersection_volume(scene_children_by_label["rx_pcb_l0"], scene_children_by_label["rx_copper_l0"])
    rx_entry = modeled_by_id["rx_rect_void_coil"]
    rx_min_x, rx_min_y, rx_min_z = rx_entry["canonical_coordinates"]["outer_bounds_min_xyz"]
    rx_size_x, rx_size_y, rx_size_z = rx_entry["canonical_coordinates"]["outer_bounds_size_xyz"]
    rx_region_min_x, rx_region_min_y, rx_region_min_z = rx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    rx_region_size_x, rx_region_size_y, rx_region_size_z = rx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"]
    assert rx_entry["role"] == "rx_single_coil"
    assert rx_entry["plane"] == "YZ"
    assert rx_entry["placement_owner_id"] == "rx_region_max"
    assert rx_entry["expected_exported_body_names"] == ["rx_pcb_l0", "rx_copper_l0"]
    assert rx_entry["expected_exported_body_count"] == 2
    assert rx_min_x == pytest.approx(rx_region_min_x + rx_region_size_x - rx_size_x)
    assert rx_min_y == pytest.approx(rx_region_min_y + (rx_region_size_y - rx_size_y) / 2.0)
    assert rx_min_z == pytest.approx(rx_region_min_z)
    rx_step_min_xyz, rx_step_max_xyz = _body_bbox(scene_step_path, label="rx_copper_l0")
    assert rx_step_max_xyz[0] == pytest.approx(rx_region_min_x + rx_region_size_x)
    assert (rx_step_min_xyz[1] + rx_step_max_xyz[1]) / 2.0 == pytest.approx(
        rx_region_min_y + (rx_region_size_y / 2.0),
        abs=1e-8,
    )
    assert rx_step_min_xyz[2] == pytest.approx(rx_region_min_z)


def test_export_type2_step_artifacts_cuts_pcb_volume_out_of_multilayer_tx_stack(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(layer_count=2))
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    imported_scene = bd.import_step(Path(ledger["scene_step_path"]))
    scene_children_by_label = {child.label: child for child in tuple(imported_scene.children)}

    assert set(("tx_pcb_l0", "tx_pcb_l1", "tx_copper_stack")).issubset(scene_children_by_label)
    _assert_zero_intersection_volume(scene_children_by_label["tx_pcb_l0"], scene_children_by_label["tx_copper_stack"])
    _assert_zero_intersection_volume(scene_children_by_label["tx_pcb_l1"], scene_children_by_label["tx_copper_stack"])


def test_export_type2_step_artifacts_translates_terminal_metadata_with_tx_region_offset(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(layer_count=2))
    tx_rect_void_toml_path = tmp_path / "tx_rect_void.toml"
    tx_rect_void_toml_path.write_text(_tx_rect_void_spec_text_with_layer_count(layer_count=2), encoding="utf-8")
    ledger = export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    tx_region_member = next(
        member
        for member in ledger["non_model_objects"][0]["member_objects"]
        if member["object_id"] == "tx_region"
    )
    modeled_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "tx_rect_void_coil")
    local_spec = load_tx_rect_void_spec(tx_rect_void_toml_path)
    local_realized = realize_tx_rect_void_spec(local_spec, seed=0)
    local_boxes = build_tx_rect_void_box_specs(local_realized)
    local_bounds_min_xyz, _local_bounds_max_xyz, local_size_xyz = modeled_body_bounds_from_boxes(local_boxes)
    start_bus_box = next(box for box in local_boxes if box.label == "tx_copper_bus_start")
    end_bus_box = next(box for box in local_boxes if box.label == "tx_copper_bus_end")
    region_min_x, region_min_y, region_min_z = tx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    region_size_x, region_size_y, _region_size_z = tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"]
    placement_offset_x = region_min_x + (region_size_x - local_size_xyz[0]) / 2.0 - local_bounds_min_xyz[0]
    placement_offset_y = region_min_y + (region_size_y - local_size_xyz[1]) / 2.0 - local_bounds_min_xyz[1]
    placement_offset_z = (
        region_min_z
        + tx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"][2]
        - local_size_xyz[2]
        - local_bounds_min_xyz[2]
    )

    assert modeled_entry["canonical_coordinates"]["frame_origin_xyz"] == pytest.approx(
        (placement_offset_x, placement_offset_y, placement_offset_z)
    )
    modeled_bounds_min_xyz = modeled_entry["canonical_coordinates"]["outer_bounds_min_xyz"]
    assert isinstance(modeled_bounds_min_xyz, tuple)
    assert modeled_bounds_min_xyz[2] == pytest.approx(
        placement_offset_z + local_bounds_min_xyz[2]
    )
    assert modeled_entry["terminal_metadata"]["start_point_plane_mm"] == pytest.approx(
        (
            start_bus_box.origin_xyz[0] + (start_bus_box.size_xyz[0] / 2.0) + placement_offset_x,
            start_bus_box.origin_xyz[1] + (start_bus_box.size_xyz[1] / 2.0) + placement_offset_y,
        )
    )
    assert modeled_entry["terminal_metadata"]["end_point_plane_mm"] == pytest.approx(
        (
            end_bus_box.origin_xyz[0] + (end_bus_box.size_xyz[0] / 2.0) + placement_offset_x,
            end_bus_box.origin_xyz[1] + (end_bus_box.size_xyz[1] / 2.0) + placement_offset_y,
        )
    )


def test_export_type2_step_artifacts_places_rx_single_coil_on_rx_region_max_yz_plane(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2_fixed.toml"
    ledger = export_type2_step_artifacts(
        toml_path=source_toml,
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=0,
    )

    rx_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == "rx_rect_void_coil")
    rx_region_member = next(
        member for member in ledger["non_model_objects"][0]["member_objects"] if member["object_id"] == "rx_region_max"
    )
    rx_min_xyz = rx_entry["canonical_coordinates"]["outer_bounds_min_xyz"]
    assert isinstance(rx_min_xyz, tuple)
    rx_min_x, rx_min_y, rx_min_z = cast(tuple[float, float, float], rx_min_xyz)
    rx_size_xyz = rx_entry["canonical_coordinates"]["outer_bounds_size_xyz"]
    assert isinstance(rx_size_xyz, tuple)
    rx_size_x, rx_size_y, rx_size_z = cast(tuple[float, float, float], rx_size_xyz)
    region_min_x, region_min_y, region_min_z = rx_region_member["canonical_coordinates"]["outer_bounds_min_xyz"]
    region_size_x, region_size_y, region_size_z = rx_region_member["canonical_coordinates"]["outer_bounds_size_xyz"]

    assert rx_entry["plane"] == "YZ"
    assert rx_entry["placement_owner_id"] == "rx_region_max"
    assert rx_min_x == pytest.approx(region_min_x + region_size_x - rx_size_x)
    assert rx_min_y == pytest.approx(region_min_y + (region_size_y - rx_size_y) / 2.0)
    assert rx_min_z == pytest.approx(region_min_z)
    rx_step_min_xyz, rx_step_max_xyz = _body_bbox(Path(ledger["scene_step_path"]), label="rx_copper_l0")
    assert rx_step_max_xyz[0] == pytest.approx(region_min_x + region_size_x)
    assert (rx_step_min_xyz[1] + rx_step_max_xyz[1]) / 2.0 == pytest.approx(
        region_min_y + (region_size_y / 2.0),
        abs=1e-8,
    )
    assert rx_step_min_xyz[2] == pytest.approx(region_min_z)


def test_export_type2_step_artifacts_fails_for_invalid_terminal_path(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(terminal_path="A_cw_to_b"))
    output_dir = tmp_path / "out"
    ledger_path = tmp_path / "out" / "ledger.json"

    with pytest.raises(ValueError, match=r"matching outer/inner corners"):
        export_type2_step_artifacts(
            toml_path=toml_path,
            output_dir=output_dir,
            ledger_path=ledger_path,
            seed=0,
        )


def test_export_type2_step_artifacts_fails_when_non_model_export_returns_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import peetsfea.type2_step_export as module_under_test

    toml_path = _write_spec(tmp_path, _type2_spec_text())
    output_dir = tmp_path / "out"
    ledger_path = tmp_path / "out" / "ledger.json"

    def _false_export_step(*args: object, **kwargs: object) -> bool:
        return False

    monkeypatch.setattr(module_under_test.bd, "export_step", _false_export_step)

    with pytest.raises(RuntimeError, match=r"build123d export_step returned False for type2 scene STEP:"):
        export_type2_step_artifacts(
            toml_path=toml_path,
            output_dir=output_dir,
            ledger_path=ledger_path,
            seed=0,
        )

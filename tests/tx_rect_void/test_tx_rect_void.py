from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from peetsfea.tx_rect_void import (
    BoxSpec,
    RealizedTxRectVoidCoil,
    RectBounds,
    build_tx_rect_void_box_specs,
    build_tx_rect_void_centerline,
    build_tx_rect_void_step_scene,
    export_tx_rect_void_step,
    load_tx_rect_void_spec,
    realize_tx_rect_void_spec,
)


def _range(is_integer: bool, start: float, end: float, count: int) -> str:
    flag = "true" if is_integer else "false"
    return f"[{flag}, {start}, {end}, {count}]"


def _spec_text(
    *,
    terminal_path: str = "A_cw_to_a",
    outer_x: float = 100.0,
    outer_y: float = 100.0,
    turn_count: int = 3,
    layer_count: int = 1,
    layer_gap: float = 2.0,
    void_x_ratio: float = 0.2,
    void_y_ratio: float = 0.2,
    void_center_x_ratio: float = 0.0,
    void_center_y_ratio: float = 0.0,
    margin_ratio: float = 0.05,
    metal_fill_factor: float = 0.5,
) -> str:
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
range = {_range(False, outer_x, outer_x, 1)}
[tx_coil.outer_y_mm]
range = {_range(False, outer_y, outer_y, 1)}
[tx_coil.turn_count]
range = {_range(True, float(turn_count), float(turn_count), 1)}
[tx_coil.layer_count]
range = {_range(True, float(layer_count), float(layer_count), 1)}
[tx_coil.layer_gap_mm]
range = {_range(False, layer_gap, layer_gap, 1)}
[tx_coil.void_x_over_outer_x]
range = {_range(False, void_x_ratio, void_x_ratio, 1)}
[tx_coil.void_y_over_outer_y]
range = {_range(False, void_y_ratio, void_y_ratio, 1)}
[tx_coil.void_center_x_over_outer_x]
range = {_range(False, void_center_x_ratio, void_center_x_ratio, 1)}
[tx_coil.void_center_y_over_outer_y]
range = {_range(False, void_center_y_ratio, void_center_y_ratio, 1)}
[tx_coil.margin_ratio]
range = {_range(False, margin_ratio, margin_ratio, 1)}
[tx_coil.metal_fill_factor]
range = {_range(False, metal_fill_factor, metal_fill_factor, 1)}
[tx_coil.terminal_path]
value = "{terminal_path}"
""".strip()


def _write_spec(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "tx_rect_void.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _box_xy_bounds(box: BoxSpec) -> RectBounds:
    origin_x, origin_y, _origin_z = box.origin_xyz
    size_x, size_y, _size_z = box.size_xyz
    return RectBounds(
        min_x=origin_x,
        max_x=origin_x + size_x,
        min_y=origin_y,
        max_y=origin_y + size_y,
    )


def _copper_boxes(boxes: tuple[BoxSpec, ...]) -> list[BoxSpec]:
    return [box for box in boxes if box.role == "copper"]


def _intersects(first: RectBounds, second: RectBounds) -> bool:
    x_overlap = max(first.min_x, second.min_x) < min(first.max_x, second.max_x) - 1e-9
    y_overlap = max(first.min_y, second.min_y) < min(first.max_y, second.max_y) - 1e-9
    return x_overlap and y_overlap


def _assert_no_copper_void_overlap(realized: RealizedTxRectVoidCoil, boxes: tuple[BoxSpec, ...]) -> None:
    copper_boxes = _copper_boxes(boxes)
    assert copper_boxes
    for box in copper_boxes:
        assert not _intersects(_box_xy_bounds(box), realized.void_bounds)


def test_load_and_realize_valid_spec_is_deterministic(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text())
    spec = load_tx_rect_void_spec(toml_path)

    first = realize_tx_rect_void_spec(spec, seed=10)
    second = realize_tx_rect_void_spec(spec, seed=10)

    assert first == second
    assert first.outer_y_mm == pytest.approx(100.0)
    assert first.layer_count == 1
    assert first.side_geometry.left.trace_mm == pytest.approx(first.side_geometry.right.trace_mm)


def test_missing_required_key_fails(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text().replace("[tx_coil.outer_x_mm]", "[tx_coil.outer_x_missing]"))

    with pytest.raises(ValueError, match=r"tx_coil is missing required key 'outer_x_mm'"):
        load_tx_rect_void_spec(toml_path)


def test_bad_range_fails(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text().replace("range = [true, 3.0, 3.0, 1]", "range = [false, 3.0, 3.0, 1]", 1))

    with pytest.raises(ValueError, match=r"tx_coil\.turn_count\.range\[0\] must be true"):
        load_tx_rect_void_spec(toml_path)


def test_unsupported_terminal_path_fails(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(terminal_path="A_cw_to_b"))

    with pytest.raises(ValueError, match=r"requires matching outer/inner corners"):
        load_tx_rect_void_spec(toml_path)


@pytest.mark.parametrize("terminal_path", ("A_cw_to_a", "B_cw_to_b", "C_cw_to_c", "D_cw_to_d", "A_ccw_to_a", "B_ccw_to_b", "C_ccw_to_c", "D_ccw_to_d"))
@pytest.mark.parametrize("turn_count", (1, 4))
def test_geometry_routes_around_void_for_supported_corners(
    tmp_path: Path,
    terminal_path: str,
    turn_count: int,
) -> None:
    toml_path = _write_spec(
        tmp_path,
            _spec_text(
                terminal_path=terminal_path,
                turn_count=turn_count,
                metal_fill_factor=0.60,
            ),
        )
    realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)
    centerline = build_tx_rect_void_centerline(realized)
    boxes = build_tx_rect_void_box_specs(realized)

    assert len(centerline) >= 2
    assert len([box for box in boxes if box.role == "pcb"]) == realized.layer_count
    _assert_no_copper_void_overlap(realized, boxes)


def test_step_scene_exports_single_fused_copper_body(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(turn_count=4, terminal_path="D_ccw_to_d"))
    realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)
    boxes = build_tx_rect_void_box_specs(realized)
    scene = build_tx_rect_void_step_scene(boxes)

    assert len([box for box in boxes if box.role == "copper"]) > 1
    assert tuple(shape.label for shape in scene.children) == ("tx_pcb_l0", "tx_copper_l0")
    assert len(scene.solids()) == 2


def test_same_corner_terminal_path_seeds_outer_terminal_to_next_ring(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(turn_count=4, terminal_path="D_ccw_to_d"))
    realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)
    centerline = build_tx_rect_void_centerline(realized)
    outer_corner_x = realized.outer_bounds.min_x + (realized.trace_width_mm / 2.0)
    seeded_x = outer_corner_x + realized.pitch_mm

    assert centerline[0][0] == pytest.approx(seeded_x)
    assert centerline[0][0] != pytest.approx(outer_corner_x)
    assert len(centerline) == len(set(centerline))


def test_segment_boxes_extend_to_corner_vertices_not_center_points(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(turn_count=2, terminal_path="D_ccw_to_d"))
    realized = realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)
    centerline = build_tx_rect_void_centerline(realized)
    boxes = build_tx_rect_void_box_specs(realized)
    first_copper_box = _copper_boxes(boxes)[0]
    first_bounds = _box_xy_bounds(first_copper_box)
    half_trace = realized.trace_width_mm / 2.0

    assert first_bounds.min_x == pytest.approx(min(centerline[0][0], centerline[1][0]) - half_trace)
    assert first_bounds.max_x == pytest.approx(max(centerline[0][0], centerline[1][0]) + half_trace)


def test_layer_gap_below_minimum_fails(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(layer_gap=1.9))

    with pytest.raises(ValueError, match=r"tx_coil\.layer_gap_mm must be >= 2\.0"):
        realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)


@pytest.mark.parametrize("layer_count", (2, 3))
def test_multilayer_coil_fails_without_via_connection_contract(tmp_path: Path, layer_count: int) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(layer_count=layer_count, layer_gap=2.5))

    with pytest.raises(ValueError, match=r"layer_count must resolve to 1"):
        realize_tx_rect_void_spec(load_tx_rect_void_spec(toml_path), seed=0)


def test_export_writes_step_and_metadata(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _spec_text(layer_count=1, turn_count=1))
    output_step_path = tmp_path / "out" / "tx_rect_void.step"
    metadata_path = tmp_path / "out" / "tx_rect_void.metadata.json"

    result = export_tx_rect_void_step(
        toml_path=toml_path,
        output_step_path=output_step_path,
        metadata_path=metadata_path,
        seed=0,
    )

    assert output_step_path.stat().st_size > 0
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["output_step_path"] == str(output_step_path)
    assert payload["realized"]["turn_count"] == 1
    assert payload["expected_exported_body_names"] == ["tx_pcb_l0", "tx_copper_l0"]
    assert payload["expected_exported_body_count"] == 2
    assert len(payload["boxes"]) == len(result.boxes)
    assert len(payload["modeled_objects"]) == 1
    modeled_object = payload["modeled_objects"][0]
    assert modeled_object["object_id"] == "tx_rect_void_coil"
    assert modeled_object["role"] == "tx_single_coil"
    assert modeled_object["material"] == "composite"
    assert modeled_object["model_state"] is True
    assert modeled_object["step_path"] == str(output_step_path)
    assert modeled_object["expected_exported_body_names"] == ["tx_pcb_l0", "tx_copper_l0"]
    assert modeled_object["expected_exported_body_count"] == 2
    assert modeled_object["canonical_coordinates"]["frame_origin_xyz"] == [0.0, 0.0, 0.0]
    assert modeled_object["canonical_coordinates"]["outer_bounds_size_xyz"][0] == pytest.approx(
        result.realized.outer_x_mm
    )
    assert modeled_object["terminal_metadata"]["path"] == result.realized.terminal_path
    assert modeled_object["terminal_metadata"]["start_point_xy_mm"]
    assert modeled_object["terminal_metadata"]["end_point_xy_mm"]


def test_cli_smoke_uses_example_spec_and_writes_registry_aligned_metadata(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    example_toml = repo_root / "examples" / "type2.toml"
    output_step_path = tmp_path / "cli" / "tx_rect_void.step"
    metadata_path = tmp_path / "cli" / "tx_rect_void.metadata.json"

    completed = subprocess.run(
        [
            str(repo_root / ".venv" / "bin" / "python"),
            str(repo_root / "entry" / "export_tx_rect_void_step.py"),
            "--toml",
            str(example_toml),
            "--output-step",
            str(output_step_path),
            "--metadata",
            str(metadata_path),
            "--seed",
            "0",
        ],
        capture_output=True,
        check=True,
        text=True,
        cwd=repo_root,
    )

    assert output_step_path.stat().st_size > 0
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["source_toml_path"] == str(example_toml)
    assert payload["modeled_objects"][0]["step_path"] == str(output_step_path)
    assert payload["modeled_objects"][0]["terminal_metadata"]["path"] == payload["realized"]["terminal_path"]
    assert payload["modeled_objects"][0]["expected_exported_body_count"] == 2
    assert "output STEP:" in completed.stdout

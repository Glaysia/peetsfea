from __future__ import annotations

import json
from math import sqrt
from pathlib import Path
from typing import Mapping, cast
import tomllib

import cadquery as cq
import pytest

from entry.debug_view_0_3_0_ssw import AEDT_PORT_LEDGER_NAME, AEDT_SCENE_STEP_NAME, export_ssw_aedt_port_artifacts
import peetsfea.coilmaker as coilmaker
import peetsfea.ssw_step as module_under_test
from peetsfea.ssw_step import (
    SswStepLedger,
    build_ssw_body_boxes,
    export_ssw_step_artifacts,
    load_ssw_fixed_spec,
    load_ssw_step_ledger,
    normal_spiral_trace_width_mm,
)
from peetsfea.ssw_step_constraints import SswConstraintValueRef, parse_ssw_constraint_rules

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXED_TOML = REPO_ROOT / "examples" / "0.3.0_fixed.toml"
SWEEP_TOML = REPO_ROOT / "examples" / "0.3.0_sweep.toml"


def test_load_ssw_fixed_spec_reads_tx_rx_frozen_contract() -> None:
    spec = load_ssw_fixed_spec(FIXED_TOML)

    assert spec.units == "mm"
    assert spec.fixed.width_max_mm == 360.0
    assert spec.fixed.height_max_mm == 180.0
    assert spec.fixed.tx_rx_min_distance_mm == 50.0
    assert spec.fixed.mull_ferrite_thickness_mm == 0.12
    assert spec.ferrite.mull_position_ratio == 0.0
    assert tuple(box.object_id for box in spec.non_model_objects) == (
        "tv",
        "tx_region",
        "tx_region_max",
        "rx_region_max",
    )
    assert spec.tx.role == "tx_ssw_coil"
    assert spec.rx.role == "rx_ssw_coil"
    assert spec.tx.width_ratio == 0.45
    assert spec.rx.height_ratio == 0.9
    assert spec.tx.is_ssw_enabled is True
    assert spec.rx.is_ssw_enabled is False
    assert spec.tx.turn_n_int == 6
    assert spec.rx.turn_n_int == 1
    assert spec.tx.gap_ratio == 0.24
    assert spec.rx.void_area_ratio == 0.25
    assert spec.tx.no_ssw_qturn_start_int == 0
    assert spec.rx.no_ssw_qturn_start_int == 3
    assert spec.rx.no_ssw_qturn_n_int == 0
    assert spec.tx.pcb_gap_mm == 8.0
    assert spec.tx.twist_factor == 5
    assert spec.rx.twist_factor == 1
    assert tuple(rule.id for rule in spec.constraints) == (
        "tx_ssw_single_conductor",
        "rx_ssw_single_conductor",
    )


def test_sweep_toml_declares_ssw_single_conductor_constraints() -> None:
    raw_root = tomllib.loads(SWEEP_TOML.read_text(encoding="utf-8"))
    rules = parse_ssw_constraint_rules(cast(dict[str, object], raw_root), context=SWEEP_TOML.name)

    assert tuple(rule.id for rule in rules) == (
        "tx_ssw_single_conductor",
        "rx_ssw_single_conductor",
    )
    assert tuple(rule.op for rule in rules) == ("==", "==")
    rhs_values: list[str | float] = []
    for rule in rules:
        assert set(rule.rhs.keys()) == {"value"}
        rhs_ref = cast(SswConstraintValueRef, rule.rhs)
        rhs_values.append(rhs_ref["value"])
    assert tuple(rhs_values) == (1.0, 1.0)


def test_load_ssw_fixed_spec_rejects_unfrozen_sweep_ranges() -> None:
    assert "[ferrite.mull_position_ratio]\nrange = [false, 0.0, 1.0, 11]" in SWEEP_TOML.read_text(
        encoding="utf-8"
    )
    with pytest.raises(ValueError, match=r"range must be frozen"):
        load_ssw_fixed_spec(SWEEP_TOML)


def test_load_ssw_fixed_spec_rejects_non_coprime_tx_ssw_constraint(tmp_path: Path) -> None:
    source_text = FIXED_TOML.read_text(encoding="utf-8")
    custom_text = source_text.replace(
        '[modeled_objects.twist_factor]\nrange = [true, 5, 5, 1]\ndescription = "TX SSW band pitch shift per loop"',
        '[modeled_objects.twist_factor]\nrange = [true, 4, 4, 1]\ndescription = "TX SSW band pitch shift per loop"',
    )
    assert custom_text != source_text
    custom_toml = tmp_path / "tx_non_coprime_ssw.toml"
    custom_toml.write_text(custom_text, encoding="utf-8")

    with pytest.raises(ValueError, match="tx_ssw_single_conductor"):
        load_ssw_fixed_spec(custom_toml)


def test_load_ssw_fixed_spec_rejects_non_coprime_rx_when_rx_ssw_enabled(tmp_path: Path) -> None:
    source_text = FIXED_TOML.read_text(encoding="utf-8")
    custom_text = source_text
    custom_text = custom_text.replace(
        '[modeled_objects.is_ssw_enabled]\nrange = [true, 0, 0, 1]\ndescription = "RX SSW enable flag"',
        '[modeled_objects.is_ssw_enabled]\nrange = [true, 1, 1, 1]\ndescription = "RX SSW enable flag"',
    )
    custom_text = custom_text.replace(
        '[modeled_objects.turn_n_int]\nrange = [true, 1, 1, 1]\ndescription = "RX SSW band count"',
        '[modeled_objects.turn_n_int]\nrange = [true, 6, 6, 1]\ndescription = "RX SSW band count"',
    )
    custom_text = custom_text.replace(
        '[modeled_objects.twist_factor]\nrange = [true, 1, 1, 1]\ndescription = "RX SSW band pitch shift per loop"',
        '[modeled_objects.twist_factor]\nrange = [true, 4, 4, 1]\ndescription = "RX SSW band pitch shift per loop"',
    )
    assert custom_text != source_text
    custom_toml = tmp_path / "rx_non_coprime_ssw.toml"
    custom_toml.write_text(custom_text, encoding="utf-8")

    with pytest.raises(ValueError, match="rx_ssw_single_conductor"):
        load_ssw_fixed_spec(custom_toml)


def test_coilmaker_validate_config_rejects_non_coprime_ssw_turn_twist() -> None:
    invalid = coilmaker.RuntimeConfig(
        fixed=coilmaker.FixedDimensions(),
        common=coilmaker.CommonCoilParameters(IS_SSW_ENABLED=True, TURN_N_INT=6),
        spiral=coilmaker.SpiralCoilParameters(),
        ssw=coilmaker.SSWCoilParameters(TWIST_FACTOR=4),
    )
    with pytest.raises(ValueError, match="must be coprime"):
        coilmaker.validate_config(invalid)

    valid = coilmaker.RuntimeConfig(
        fixed=coilmaker.FixedDimensions(),
        common=coilmaker.CommonCoilParameters(IS_SSW_ENABLED=True, TURN_N_INT=6),
        spiral=coilmaker.SpiralCoilParameters(),
        ssw=coilmaker.SSWCoilParameters(TWIST_FACTOR=5),
    )
    assert coilmaker.validate_config(valid) is valid


def _bounds(body: Mapping[str, object]) -> tuple[float, float, float, float, float, float]:
    center = body["center_xyz"]
    size = body["size_xyz"]
    assert isinstance(center, list)
    assert isinstance(size, list)
    assert len(center) == 3
    assert len(size) == 3
    center_x, center_y, center_z = (float(center[0]), float(center[1]), float(center[2]))
    size_x, size_y, size_z = (float(size[0]), float(size[1]), float(size[2]))
    return (
        center_x - size_x / 2.0,
        center_x + size_x / 2.0,
        center_y - size_y / 2.0,
        center_y + size_y / 2.0,
        center_z - size_z / 2.0,
        center_z + size_z / 2.0,
    )


def _numeric_field(body: Mapping[str, object], key: str) -> float:
    value = body[key]
    assert isinstance(value, (int, float))
    return float(value)


def _action_params_by_key(action: Mapping[str, object]) -> dict[str, object]:
    params = action["params"]
    assert isinstance(params, list)
    mapped: dict[str, object] = {}
    for param in params:
        assert isinstance(param, dict)
        key = param["key"]
        value_json = param["value_json"]
        assert isinstance(key, str)
        assert isinstance(value_json, str)
        mapped[key] = tomllib.loads(f"value = {value_json}\n")["value"]
    return mapped


def _point2_param(params: Mapping[str, object], key: str) -> tuple[float, float]:
    value = params[key]
    assert isinstance(value, list)
    assert len(value) == 2
    assert isinstance(value[0], (int, float))
    assert isinstance(value[1], (int, float))
    return float(value[0]), float(value[1])


def _unit_vector(start: tuple[float, float], end: tuple[float, float]) -> tuple[float, float]:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = sqrt(dx**2 + dy**2)
    assert length > 1e-8
    return dx / length, dy / length


def _box_bounds(body: module_under_test._BodyBox) -> tuple[float, float, float, float, float, float]:
    return (
        body.center_xyz[0] - body.size_xyz[0] / 2.0,
        body.center_xyz[0] + body.size_xyz[0] / 2.0,
        body.center_xyz[1] - body.size_xyz[1] / 2.0,
        body.center_xyz[1] + body.size_xyz[1] / 2.0,
        body.center_xyz[2] - body.size_xyz[2] / 2.0,
        body.center_xyz[2] + body.size_xyz[2] / 2.0,
    )


def _combined_box_bounds(
    bodies: tuple[module_under_test._BodyBox, ...],
) -> tuple[float, float, float, float, float, float]:
    assert bodies
    bounds = tuple(_box_bounds(body) for body in bodies)
    return (
        min(bound[0] for bound in bounds),
        max(bound[1] for bound in bounds),
        min(bound[2] for bound in bounds),
        max(bound[3] for bound in bounds),
        min(bound[4] for bound in bounds),
        max(bound[5] for bound in bounds),
    )


def _combined_ledger_bounds(ledger: SswStepLedger, object_id_prefix: str) -> tuple[float, float, float, float, float, float]:
    matching_bodies = tuple(body for body in ledger["bodies"] if body["object_id"].startswith(object_id_prefix))
    assert matching_bodies
    bounds = tuple(_bounds(body) for body in matching_bodies)
    return (
        min(bound[0] for bound in bounds),
        max(bound[1] for bound in bounds),
        min(bound[2] for bound in bounds),
        max(bound[3] for bound in bounds),
        min(bound[4] for bound in bounds),
        max(bound[5] for bound in bounds),
    )


def _combined_bbox_bounds(
    bboxes: tuple[cq.BoundBox, ...],
) -> tuple[float, float, float, float, float, float]:
    assert bboxes
    return (
        min(bbox.xmin for bbox in bboxes),
        max(bbox.xmax for bbox in bboxes),
        min(bbox.ymin for bbox in bboxes),
        max(bbox.ymax for bbox in bboxes),
        min(bbox.zmin for bbox in bboxes),
        max(bbox.zmax for bbox in bboxes),
    )


def _rx_normal_trace_width_mm(spec: module_under_test.SswFixedSpec) -> float:
    return normal_spiral_trace_width_mm(params=spec.rx, fixed=spec.fixed)


def _rx_normal_port_landing_bounds(
    spec: module_under_test.SswFixedSpec,
) -> tuple[float, float, float, float, float, float]:
    config = module_under_test._coilmaker_config(spec.rx, spec.fixed)
    frames = tuple(coilmaker.coil_slot_frames(config))
    assert len(frames) == 1
    frame = frames[0]
    trace_width_mm = _rx_normal_trace_width_mm(spec)
    centerline_points = coilmaker._normal_coil_centerline_points(config, frame)
    landing = coilmaker._normal_port_landing_geometry(config, frame, centerline_points, trace_width_mm)
    placement = module_under_test._placement_for_role(
        spec,
        spec.rx,
        module_under_test._coilmaker_assembly(spec.rx, spec.fixed),
    )
    bboxes: list[cq.BoundBox] = []
    for token in landing.pieces:
        if isinstance(token, coilmaker.BoxToken):
            workplane = coilmaker._render_box_token(token)
        elif isinstance(token, coilmaker.PolygonExtrudeToken):
            rendered = coilmaker._render_polygon_extrude_token(token)
            if rendered is None:
                continue
            workplane = rendered
        else:
            raise TypeError(f"unsupported RX normal port body token {type(token).__name__}")
        bboxes.append(module_under_test._located_bbox(workplane, placement))
    return _combined_bbox_bounds(tuple(bboxes))


def _body_by_name_from_boxes(
    bodies: tuple[module_under_test._BodyBox, ...],
    name: str,
) -> module_under_test._BodyBox:
    matches = tuple(body for body in bodies if body.name == name)
    assert len(matches) == 1
    return matches[0]


def _body_by_name_from_ledger(ledger: SswStepLedger, name: str) -> Mapping[str, object]:
    matches = tuple(body for body in ledger["bodies"] if body["object_id"] == name)
    assert len(matches) == 1
    return matches[0]


def test_build_ssw_body_boxes_uses_tv_below_distance(tmp_path: Path) -> None:
    source_text = FIXED_TOML.read_text(encoding="utf-8")
    custom_text = source_text.replace(
        "[fixed_dimensions.tx_rx_min_distance_mm]\nrange = [false, 50.0, 50.0, 1]",
        "[fixed_dimensions.tx_rx_min_distance_mm]\nrange = [false, 125.0, 125.0, 1]",
    )
    assert custom_text != source_text
    custom_toml = tmp_path / "custom_ssw.toml"
    custom_toml.write_text(custom_text, encoding="utf-8")

    spec = load_ssw_fixed_spec(custom_toml)
    bodies = build_ssw_body_boxes(spec)
    tv_bounds = _box_bounds(_body_by_name_from_boxes(bodies, "tv"))
    tx_region_bounds = _box_bounds(_body_by_name_from_boxes(bodies, "tx_region"))
    tx_bounds = _combined_box_bounds(tuple(body for body in bodies if body.name.startswith("tx_ssw_coil_")))

    assert tv_bounds[4] - tx_region_bounds[5] == pytest.approx(125.0)
    assert tx_bounds[5] == pytest.approx(tx_region_bounds[5])


def test_export_ssw_step_artifacts_writes_tx_rx_coil_scene(tmp_path: Path) -> None:
    artifacts = export_ssw_step_artifacts(source_toml_path=FIXED_TOML, output_dir=tmp_path, seed=0)

    spec = load_ssw_fixed_spec(FIXED_TOML)
    step_path = Path(artifacts["scene_step_path"])
    ledger = load_ssw_step_ledger(Path(artifacts["ledger_path"]))
    token_path = Path(artifacts["token_toml_path"])
    assert step_path.is_file()
    assert step_path.stat().st_size > 0
    assert token_path.is_file()
    token_doc = tomllib.loads(token_path.read_text(encoding="utf-8"))
    metadata = token_doc["metadata"]
    actions = token_doc["actions"]
    assert isinstance(metadata, dict)
    assert isinstance(actions, list)
    assert metadata["format"] == "peetsfea_ssw_scene_action_tokens_v1"
    assert metadata["action_count"] == len(actions)
    action_ops = tuple(str(action["op"]) for action in actions)
    assert "BEGIN_SSW_SCENE" in action_ops
    assert "PLACE_COIL_IN_SCENE" in action_ops
    assert "CREATE_MULL_FERRITE_SHEET" in action_ops
    assert "EXPORT_STEP" in action_ops
    export_actions = tuple(
        action for action in actions if action["op"] == "EXPORT_STEP" and action["target"] == "output.ssw_scene.step"
    )
    assert len(export_actions) == 1
    export_params = export_actions[0]["params"]
    assert isinstance(export_params, list)
    export_inputs = export_actions[0]["inputs"]
    assert isinstance(export_inputs, list)
    assert tuple(str(input_ref) for input_ref in export_inputs) == (
        "non_model.tv",
        "non_model.tx_region",
        "non_model.tx_region_max",
        "non_model.rx_region_max",
        "scene.tx_ssw_coil.placement",
        "scene.rx_ssw_coil.placement",
        "ferrite.tx_mull_ferrite_sheet",
        "ferrite.rx_mull_ferrite_sheet",
    )
    export_param_keys = tuple(str(param["key"]) for param in export_params)
    assert "scene_step_name" in export_param_keys
    assert "token_toml_name" in export_param_keys
    assert "scene_step_path" not in export_param_keys
    assert "token_toml_path" not in export_param_keys
    action_targets = tuple(str(action["target"]) for action in actions)
    assert any(target.startswith("tx_ssw_coil.") for target in action_targets)
    assert any(target.startswith("rx_ssw_coil.") for target in action_targets)
    tx_placement = tuple(action for action in actions if action["target"] == "scene.tx_ssw_coil.placement")
    rx_placement = tuple(action for action in actions if action["target"] == "scene.rx_ssw_coil.placement")
    assert len(tx_placement) == 1
    assert len(rx_placement) == 1
    tx_placement_params = _action_params_by_key(tx_placement[0])
    rx_placement_params = _action_params_by_key(rx_placement[0])
    rx_port_terminals = tuple(
        action for action in actions if action["target"] == "rx_ssw_coil.frame_0.port.terminals"
    )
    rx_port_landing = tuple(
        action for action in actions if action["target"] == "rx_ssw_coil.frame_0.port.landing"
    )
    rx_port_clearance = tuple(
        action for action in actions if action["target"] == "rx_ssw_coil.frame_0.port.clearance"
    )
    rx_port_bridge = tuple(
        action for action in actions if action["target"] == "rx_ssw_coil.frame_0.port.bridge"
    )
    assert len(rx_port_terminals) == 1
    assert len(rx_port_landing) == 1
    assert len(rx_port_clearance) == 1
    assert len(rx_port_bridge) == 1
    assert rx_port_clearance[0]["op"] == "EXTRUDE_POLYGON"
    assert rx_port_bridge[0]["op"] == "EXTRUDE_POLYGON"
    rx_port_terminal_params = _action_params_by_key(rx_port_terminals[0])
    rx_port_landing_params = _action_params_by_key(rx_port_landing[0])
    rx_trace_width_mm = _rx_normal_trace_width_mm(spec)
    outer_terminal_xy = _point2_param(rx_port_terminal_params, "outer_terminal_xy_mm")
    inner_terminal_xy = _point2_param(rx_port_terminal_params, "inner_terminal_xy_mm")
    inner_landing_xy = _point2_param(rx_port_landing_params, "inner_landing_xy_mm")
    rx_config = module_under_test._coilmaker_config(spec.rx, spec.fixed)
    rx_frame = tuple(coilmaker.coil_slot_frames(rx_config))[0]
    rx_centerline_points = coilmaker._normal_coil_centerline_points(rx_config, rx_frame)
    if outer_terminal_xy == rx_centerline_points[0]:
        adjacent_trace_xy = rx_centerline_points[1]
    elif outer_terminal_xy == rx_centerline_points[-1]:
        adjacent_trace_xy = rx_centerline_points[-2]
    else:
        raise AssertionError("RX outer terminal must be a centerline endpoint")
    trace_tangent_xy = _unit_vector(outer_terminal_xy, adjacent_trace_xy)
    landing_direction_xy = _unit_vector(outer_terminal_xy, inner_landing_xy)
    trace_axis = 0 if abs(trace_tangent_xy[0]) > abs(trace_tangent_xy[1]) else 1
    landing_distance_mm = sqrt(
        (inner_landing_xy[0] - outer_terminal_xy[0]) ** 2
        + (inner_landing_xy[1] - outer_terminal_xy[1]) ** 2
    )
    toward_inner_xy = (
        inner_terminal_xy[0] - outer_terminal_xy[0],
        inner_terminal_xy[1] - outer_terminal_xy[1],
    )
    assert tx_placement_params["coil_mode"] == "ssw"
    assert rx_placement_params["coil_mode"] == "normal_spiral"
    assert rx_port_landing_params["pad_mm"] == pytest.approx(rx_trace_width_mm)
    assert landing_distance_mm == pytest.approx(rx_trace_width_mm + spec.fixed.port_length_mm)
    landing_dot_inner = (
        landing_direction_xy[0] * toward_inner_xy[0]
        + landing_direction_xy[1] * toward_inner_xy[1]
    )
    assert landing_direction_xy[trace_axis] == pytest.approx(0.0)
    assert abs(landing_direction_xy[1 - trace_axis]) == pytest.approx(1.0)
    assert landing_dot_inner > 0.0
    assert tx_placement_params["port_face"] == "lower_z"
    assert rx_placement_params["port_face"] == "normal_spiral_landing"
    assert tx_placement_params["no_ssw_qturn_start_int"] == 0
    assert rx_placement_params["no_ssw_qturn_start_int"] == 3
    assert rx_placement_params["no_ssw_qturn_n_int"] == 0
    assert "tx_ssw_coil_pcb_1_fr4" in ledger["fr4_body_names"]
    assert "rx_ssw_coil_pcb_1_fr4" in ledger["fr4_body_names"]
    assert ledger["token_toml_path"] == str(token_path)
    assert ledger["non_model_body_names"] == ["tv", "tx_region", "tx_region_max", "rx_region_max"]
    assert ledger["ferrite_body_names"] == ["tx_mull_ferrite_sheet", "rx_mull_ferrite_sheet"]
    assert "tx_ssw_coil_ssw_copper" in ledger["copper_body_names"]
    assert "rx_ssw_coil_coil_copper" in ledger["copper_body_names"]
    assert "rx_ssw_coil_ssw_copper" not in ledger["copper_body_names"]
    assert len(ledger["body_names"]) == len(set(ledger["body_names"]))
    tv = _body_by_name_from_ledger(ledger, "tv")
    tx_region = _body_by_name_from_ledger(ledger, "tx_region")
    tx_region_max = _body_by_name_from_ledger(ledger, "tx_region_max")
    rx_region_max = _body_by_name_from_ledger(ledger, "rx_region_max")
    tx_copper = _body_by_name_from_ledger(ledger, "tx_ssw_coil_ssw_copper")
    rx_copper = _body_by_name_from_ledger(ledger, "rx_ssw_coil_coil_copper")
    tx_ferrite = _body_by_name_from_ledger(ledger, "tx_mull_ferrite_sheet")
    rx_ferrite = _body_by_name_from_ledger(ledger, "rx_mull_ferrite_sheet")
    tv_bounds = _bounds(tv)
    tx_region_bounds = _bounds(tx_region)
    tx_region_max_bounds = _bounds(tx_region_max)
    rx_region_max_bounds = _bounds(rx_region_max)
    tx_bounds = _bounds(tx_copper)
    rx_bounds = _bounds(rx_copper)
    tx_assembly_bounds = _combined_ledger_bounds(ledger, "tx_ssw_coil_")
    rx_assembly_bounds = _combined_ledger_bounds(ledger, "rx_ssw_coil_")
    tx_ferrite_bounds = _bounds(tx_ferrite)
    rx_ferrite_bounds = _bounds(rx_ferrite)
    tolerance = 1e-6
    assert _numeric_field(tv, "transparency") == pytest.approx(0.6)
    assert _numeric_field(tx_region, "transparency") == pytest.approx(0.2)
    assert _numeric_field(tx_region_max, "transparency") == pytest.approx(0.35)
    assert _numeric_field(rx_region_max, "transparency") == pytest.approx(0.35)
    assert tx_ferrite["role"] == "ferrite"
    assert rx_ferrite["role"] == "ferrite"
    assert tx_ferrite["material"] == "mull_ferrite"
    assert rx_ferrite["material"] == "mull_ferrite"
    assert tx_region_max_bounds[0] == pytest.approx(tx_bounds[0])
    assert tx_region_max_bounds[1] - tx_region_max_bounds[0] == pytest.approx(240.14)
    assert (tx_region_max_bounds[2] + tx_region_max_bounds[3]) / 2.0 == pytest.approx(
        (tx_bounds[2] + tx_bounds[3]) / 2.0
    )
    assert tx_region_max_bounds[3] - tx_region_max_bounds[2] == pytest.approx(480.14)
    assert tx_region_max_bounds[4] == pytest.approx(tx_bounds[5] - 15.0)
    assert tx_region_max_bounds[5] == pytest.approx(tx_bounds[5])
    assert rx_region_max_bounds[0] == pytest.approx(tv_bounds[1] - 5.0)
    assert rx_region_max_bounds[1] == pytest.approx(tv_bounds[1])
    assert rx_region_max_bounds[3] - rx_region_max_bounds[2] == pytest.approx(480.14)
    assert (rx_region_max_bounds[2] + rx_region_max_bounds[3]) / 2.0 == pytest.approx(0.0)
    assert rx_region_max_bounds[5] - rx_region_max_bounds[4] == pytest.approx(240.14)
    assert rx_region_max_bounds[4] == pytest.approx(tv_bounds[4])
    assert tx_ferrite_bounds[0] == pytest.approx(tx_assembly_bounds[0])
    assert tx_ferrite_bounds[1] == pytest.approx(tx_assembly_bounds[1])
    assert tx_ferrite_bounds[2] == pytest.approx(tx_assembly_bounds[2])
    assert tx_ferrite_bounds[3] == pytest.approx(tx_assembly_bounds[3])
    assert tx_ferrite_bounds[4] == pytest.approx(tx_region_max_bounds[4])
    assert tx_ferrite_bounds[5] - tx_ferrite_bounds[4] == pytest.approx(0.12)
    assert rx_ferrite_bounds[0] == pytest.approx(rx_region_max_bounds[0])
    assert rx_ferrite_bounds[1] - rx_ferrite_bounds[0] == pytest.approx(0.12)
    assert rx_ferrite_bounds[2] == pytest.approx(rx_assembly_bounds[2])
    assert rx_ferrite_bounds[3] == pytest.approx(rx_assembly_bounds[3])
    assert rx_ferrite_bounds[4] == pytest.approx(rx_assembly_bounds[4])
    assert rx_ferrite_bounds[5] == pytest.approx(rx_assembly_bounds[5])
    assert rx_bounds[1] == pytest.approx(rx_region_max_bounds[1])
    assert (
        rx_region_max_bounds[0] - tolerance
        <= rx_bounds[0]
        <= rx_bounds[1]
        <= rx_region_max_bounds[1] + tolerance
    )
    assert (
        rx_region_max_bounds[2] - tolerance
        <= rx_bounds[2]
        <= rx_bounds[3]
        <= rx_region_max_bounds[3] + tolerance
    )
    assert (
        rx_region_max_bounds[4] - tolerance
        <= rx_bounds[4]
        <= rx_bounds[5]
        <= rx_region_max_bounds[5] + tolerance
    )
    assert rx_bounds[0] >= tv_bounds[0] - 0.07 - tolerance
    assert rx_bounds[1] <= tv_bounds[1] + tolerance
    assert rx_bounds[2] >= tv_bounds[2] - tolerance
    assert rx_bounds[3] <= tv_bounds[3] + tolerance
    assert rx_bounds[4] >= tv_bounds[4] - 0.07 - tolerance
    assert rx_bounds[5] <= tv_bounds[5] + 0.07 + tolerance
    assert tv_bounds[4] - tx_region_bounds[5] == pytest.approx(50.0)
    assert tx_bounds[5] == pytest.approx(tx_region_bounds[5])
    assert tx_region_bounds[0] - tolerance <= tx_bounds[0] <= tx_bounds[1] <= tx_region_bounds[1] + tolerance
    assert tx_region_bounds[2] - tolerance <= tx_bounds[2] <= tx_bounds[3] <= tx_region_bounds[3] + tolerance
    assert tx_bounds[4] >= tx_region_bounds[4] - tolerance
    assert tx_bounds[5] <= tx_region_bounds[5] + tolerance
    assert tx_region_bounds[1] - tx_region_bounds[0] > tx_bounds[1] - tx_bounds[0]
    assert tx_region_bounds[3] - tx_region_bounds[2] > tx_bounds[3] - tx_bounds[2]
    assert tx_region_bounds[5] - tx_region_bounds[4] > tx_bounds[5] - tx_bounds[4]
    assert tx_bounds[3] - tx_bounds[2] > tx_bounds[1] - tx_bounds[0]
    assert tx_bounds[5] - tx_bounds[4] < 10.0
    assert rx_bounds[1] - rx_bounds[0] < 10.0
    assert rx_bounds[3] - rx_bounds[2] > rx_bounds[5] - rx_bounds[4]
    rx_port_landing_bounds = _rx_normal_port_landing_bounds(spec)
    assert rx_port_landing_bounds[0] == pytest.approx(rx_bounds[0])
    assert rx_port_landing_bounds[1] < rx_bounds[1] - tolerance
    tx_port_anchor = tx_placement_params["port_anchor_world_xyz_mm"]
    rx_port_anchor = rx_placement_params["port_anchor_world_xyz_mm"]
    assert isinstance(tx_port_anchor, list)
    assert isinstance(rx_port_anchor, list)
    assert len(tx_port_anchor) == 3
    assert len(rx_port_anchor) == 3
    assert float(tx_port_anchor[2]) == pytest.approx(tx_bounds[4])
    assert float(rx_port_anchor[0]) == pytest.approx(rx_bounds[0])
    tx_ferrite_actions = tuple(action for action in actions if action["target"] == "ferrite.tx_mull_ferrite_sheet")
    rx_ferrite_actions = tuple(action for action in actions if action["target"] == "ferrite.rx_mull_ferrite_sheet")
    assert len(tx_ferrite_actions) == 1
    assert len(rx_ferrite_actions) == 1
    tx_ferrite_params = _action_params_by_key(tx_ferrite_actions[0])
    rx_ferrite_params = _action_params_by_key(rx_ferrite_actions[0])
    assert tx_ferrite_params["mull_position_ratio"] == 0.0
    assert rx_ferrite_params["mull_position_ratio"] == 0.0
    assert tx_ferrite_params["thickness_mm"] == 0.12
    assert rx_ferrite_params["thickness_mm"] == 0.12


def test_build_ssw_body_boxes_places_mull_ferrite_ratio_one_next_to_coils(tmp_path: Path) -> None:
    source_text = FIXED_TOML.read_text(encoding="utf-8")
    custom_text = source_text.replace(
        "[ferrite.mull_position_ratio]\nrange = [false, 0.0, 0.0, 1]",
        "[ferrite.mull_position_ratio]\nrange = [false, 1.0, 1.0, 1]",
    )
    assert custom_text != source_text
    custom_toml = tmp_path / "mull_ratio_one.toml"
    custom_toml.write_text(custom_text, encoding="utf-8")

    spec = load_ssw_fixed_spec(custom_toml)
    bodies = build_ssw_body_boxes(spec)
    tx_bounds = _combined_box_bounds(tuple(body for body in bodies if body.name.startswith("tx_ssw_coil_")))
    rx_bounds = _combined_box_bounds(tuple(body for body in bodies if body.name.startswith("rx_ssw_coil_")))
    tx_ferrite_bounds = _box_bounds(_body_by_name_from_boxes(bodies, "tx_mull_ferrite_sheet"))
    rx_ferrite_bounds = _box_bounds(_body_by_name_from_boxes(bodies, "rx_mull_ferrite_sheet"))

    assert tx_ferrite_bounds[5] == pytest.approx(tx_bounds[4])
    assert rx_ferrite_bounds[1] == pytest.approx(rx_bounds[0])


def test_build_ssw_body_boxes_rejects_mull_ferrite_sheet_when_interval_is_too_small(tmp_path: Path) -> None:
    source_text = FIXED_TOML.read_text(encoding="utf-8")
    custom_text = source_text.replace(
        "[fixed_dimensions.mull_ferrite_thickness_mm]\nrange = [false, 0.12, 0.12, 1]",
        "[fixed_dimensions.mull_ferrite_thickness_mm]\nrange = [false, 500.0, 500.0, 1]",
    )
    assert custom_text != source_text
    custom_toml = tmp_path / "mull_too_thick.toml"
    custom_toml.write_text(custom_text, encoding="utf-8")

    spec = load_ssw_fixed_spec(custom_toml)
    with pytest.raises(ValueError, match="TX MULL ferrite remaining interval"):
        build_ssw_body_boxes(spec)


def test_export_ssw_aedt_port_artifacts_writes_direct_edge_port_ledger(tmp_path: Path) -> None:
    ledger = export_ssw_aedt_port_artifacts(source_toml_path=FIXED_TOML, output_dir=tmp_path, seed=0)

    aedt_step_path = Path(ledger["scene_step_path"])
    port_ledger_path = tmp_path / AEDT_PORT_LEDGER_NAME
    assert aedt_step_path.name == AEDT_SCENE_STEP_NAME
    assert aedt_step_path.is_file()
    assert aedt_step_path.stat().st_size > 0
    assert port_ledger_path.is_file()
    stored_ledger = json.loads(port_ledger_path.read_text(encoding="utf-8"))
    assert stored_ledger == ledger
    assert ledger["dimension_count"] == 21
    assert len(ledger["design_space_hash"]) == 16
    assert ledger["design_id"] == f"0_3_0_d00021_p{ledger['design_space_hash']}"
    assert ledger["aedt_filename"] == f"{ledger['design_id']}.aedt"
    assert "port_sheet_names" not in ledger
    assert "tx_aedt_port_sheet" not in ledger["body_names"]
    assert "rx_aedt_port_sheet" not in ledger["body_names"]
    assert all(ledger["design_id"] not in body_name for body_name in ledger["body_names"])
    assert "tx_mull_ferrite_sheet" in ledger["ferrite_body_names"]
    assert "rx_mull_ferrite_sheet" in ledger["ferrite_body_names"]
    assert [entry["role"] for entry in ledger["port_edges"]] == ["tx", "rx"]
    tx_entry = ledger["port_edges"][0]
    rx_entry = ledger["port_edges"][1]
    assert tx_entry["copper_body_name"] == "tx_ssw_coil_ssw_copper"
    assert tx_entry["selection"] == "semantic_edge_vertices"
    assert len(tx_entry["edge_vertices_xyz"]) == 2
    assert rx_entry["copper_body_name"] == "rx_ssw_coil_coil_copper"
    assert rx_entry["selection"] == "semantic_edge_vertices"
    assert len(rx_entry["edge_vertices_xyz"]) == 2
    expected_rx_edge_length_mm = _rx_normal_trace_width_mm(load_ssw_fixed_spec(FIXED_TOML))
    for edge in rx_entry["edge_vertices_xyz"]:
        assert len(edge) == 2
        assert len(edge[0]) == 3
        assert len(edge[1]) == 3
        assert sqrt(sum((edge[0][axis] - edge[1][axis]) ** 2 for axis in range(3))) == pytest.approx(
            expected_rx_edge_length_mm
        )


def test_export_ssw_step_artifacts_supports_explicit_rx_spiral_mode(tmp_path: Path) -> None:
    source_text = FIXED_TOML.read_text(encoding="utf-8")
    custom_text = source_text
    custom_text = custom_text.replace(
        '[modeled_objects.no_ssw_qturn_start_int]\nrange = [true, 3, 3, 1]\ndescription = "RX non-SSW quarter-turn start index; fixed disabled for 0.3.0 SSW"',
        '[modeled_objects.no_ssw_qturn_start_int]\nrange = [true, 2, 2, 1]\ndescription = "RX non-SSW quarter-turn start index; fixed disabled for 0.3.0 SSW"',
    )
    custom_text = custom_text.replace(
        '[modeled_objects.no_ssw_qturn_n_int]\nrange = [true, 0, 0, 1]\ndescription = "RX non-SSW quarter-turn count; fixed disabled for 0.3.0 SSW"',
        '[modeled_objects.no_ssw_qturn_n_int]\nrange = [true, 1, 1, 1]\ndescription = "RX non-SSW quarter-turn count; fixed disabled for 0.3.0 SSW"',
    )
    assert custom_text != source_text
    custom_toml = tmp_path / "rx_spiral.toml"
    custom_toml.write_text(custom_text, encoding="utf-8")

    spec = load_ssw_fixed_spec(custom_toml)
    assert spec.tx.is_ssw_enabled is True
    assert spec.rx.is_ssw_enabled is False
    assert spec.rx.no_ssw_qturn_start_int == 2
    assert spec.rx.no_ssw_qturn_n_int == 1

    artifacts = export_ssw_step_artifacts(source_toml_path=custom_toml, output_dir=tmp_path / "out", seed=0)
    ledger = load_ssw_step_ledger(Path(artifacts["ledger_path"]))
    token_doc = tomllib.loads(Path(artifacts["token_toml_path"]).read_text(encoding="utf-8"))
    actions = token_doc["actions"]
    assert isinstance(actions, list)
    action_ops = tuple(str(action["op"]) for action in actions)
    assert "NORMAL_CENTERLINE" in action_ops
    assert "SSW_CONTEXT" in action_ops
    assert "rx_ssw_coil_coil_copper" in ledger["copper_body_names"]
    assert "rx_ssw_coil_ssw_copper" not in ledger["copper_body_names"]
    rx_placement = tuple(action for action in actions if action["target"] == "scene.rx_ssw_coil.placement")
    assert len(rx_placement) == 1
    rx_placement_params = _action_params_by_key(rx_placement[0])
    assert rx_placement_params["coil_mode"] == "normal_spiral"
    assert rx_placement_params["port_face"] == "normal_spiral_landing"
    assert rx_placement_params["no_ssw_qturn_start_int"] == 2
    assert rx_placement_params["no_ssw_qturn_n_int"] == 1


def test_export_ssw_step_artifacts_supports_zero_zero_rx_spiral_selection(tmp_path: Path) -> None:
    source_text = FIXED_TOML.read_text(encoding="utf-8")
    custom_text = source_text.replace(
        (
            '[modeled_objects.no_ssw_qturn_start_int]\nrange = [true, 3, 3, 1]\n'
            'description = "RX non-SSW quarter-turn start index; fixed disabled for 0.3.0 SSW"'
        ),
        (
            '[modeled_objects.no_ssw_qturn_start_int]\nrange = [true, 0, 0, 1]\n'
            'description = "RX non-SSW quarter-turn start index; fixed disabled for 0.3.0 SSW"'
        ),
    )
    assert custom_text != source_text
    custom_toml = tmp_path / "rx_zero_zero.toml"
    custom_toml.write_text(custom_text, encoding="utf-8")

    spec = load_ssw_fixed_spec(custom_toml)
    assert spec.rx.is_ssw_enabled is False
    assert spec.rx.no_ssw_qturn_start_int == 0
    assert spec.rx.no_ssw_qturn_n_int == 0

    artifacts = export_ssw_step_artifacts(source_toml_path=custom_toml, output_dir=tmp_path / "out", seed=0)
    token_doc = tomllib.loads(Path(artifacts["token_toml_path"]).read_text(encoding="utf-8"))
    actions = token_doc["actions"]
    assert isinstance(actions, list)
    rx_placement = tuple(action for action in actions if action["target"] == "scene.rx_ssw_coil.placement")
    assert len(rx_placement) == 1
    rx_placement_params = _action_params_by_key(rx_placement[0])
    assert rx_placement_params["coil_mode"] == "normal_spiral"
    assert rx_placement_params["no_ssw_qturn_start_int"] == 0
    assert rx_placement_params["no_ssw_qturn_n_int"] == 0


def test_export_ssw_step_artifacts_raises_when_step_export_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _skip_save(self: object, path: str, exportType: str) -> None:
        del self, path, exportType

    monkeypatch.setattr(module_under_test.cq.Assembly, "save", _skip_save)

    with pytest.raises(RuntimeError, match="CadQuery STEP export failed for SSW scene"):
        export_ssw_step_artifacts(source_toml_path=FIXED_TOML, output_dir=tmp_path, seed=0)
    token_path = tmp_path / "coil_making_token.toml"
    assert token_path.is_file()
    tomllib.loads(token_path.read_text(encoding="utf-8"))

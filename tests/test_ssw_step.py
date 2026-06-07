from __future__ import annotations

from pathlib import Path
from typing import Mapping
import tomllib

import pytest

import peetsfea.ssw_step as module_under_test
from peetsfea.ssw_step import (
    SswStepLedger,
    build_ssw_body_boxes,
    export_ssw_step_artifacts,
    load_ssw_fixed_spec,
    load_ssw_step_ledger,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXED_TOML = REPO_ROOT / "examples" / "0.3.0_fixed.toml"
SWEEP_TOML = REPO_ROOT / "examples" / "0.3.0_sweep.toml"


def test_load_ssw_fixed_spec_reads_tx_rx_frozen_contract() -> None:
    spec = load_ssw_fixed_spec(FIXED_TOML)

    assert spec.units == "mm"
    assert spec.fixed.width_max_mm == 480.0
    assert spec.fixed.height_max_mm == 240.0
    assert spec.fixed.tx_rx_min_distance_mm == 100.0
    assert tuple(box.object_id for box in spec.non_model_objects) == ("tv", "tx_region")
    assert spec.tx.role == "tx_ssw_coil"
    assert spec.rx.role == "rx_ssw_coil"
    assert spec.tx.width_ratio == 0.6
    assert spec.rx.height_ratio == 0.6
    assert spec.tx.is_ssw_enabled is True
    assert spec.rx.is_ssw_enabled is False
    assert spec.tx.turn_n_int == 3
    assert spec.rx.turn_n_int == 2
    assert spec.tx.gap_ratio == 0.24
    assert spec.rx.void_area_ratio == 0.5
    assert spec.tx.no_ssw_qturn_start_int == 0
    assert spec.rx.no_ssw_qturn_n_int == 0
    assert spec.tx.pcb_gap_mm == 8.0
    assert spec.rx.twist_factor == 1


def test_load_ssw_fixed_spec_rejects_unfrozen_sweep_ranges() -> None:
    with pytest.raises(ValueError, match=r"range must be frozen"):
        load_ssw_fixed_spec(SWEEP_TOML)


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
        "[fixed_dimensions.tx_rx_min_distance_mm]\nrange = [false, 100.0, 100.0, 1]",
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
    assert "EXPORT_STEP" in action_ops
    export_actions = tuple(
        action for action in actions if action["op"] == "EXPORT_STEP" and action["target"] == "output.ssw_scene.step"
    )
    assert len(export_actions) == 1
    export_params = export_actions[0]["params"]
    assert isinstance(export_params, list)
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
    assert tx_placement_params["coil_mode"] == "ssw"
    assert rx_placement_params["coil_mode"] == "normal_spiral"
    assert tx_placement_params["port_face"] == "lower_z"
    assert rx_placement_params["port_face"] == "normal_spiral_landing"
    assert tx_placement_params["no_ssw_qturn_start_int"] == 0
    assert rx_placement_params["no_ssw_qturn_n_int"] == 0
    assert "tx_ssw_coil_pcb_1_fr4" in ledger["fr4_body_names"]
    assert "rx_ssw_coil_pcb_1_fr4" in ledger["fr4_body_names"]
    assert ledger["token_toml_path"] == str(token_path)
    assert ledger["non_model_body_names"] == ["tv", "tx_region"]
    assert "tx_ssw_coil_ssw_copper" in ledger["copper_body_names"]
    assert "rx_ssw_coil_coil_copper" in ledger["copper_body_names"]
    assert "rx_ssw_coil_ssw_copper" not in ledger["copper_body_names"]
    assert len(ledger["body_names"]) == len(set(ledger["body_names"]))
    tv = _body_by_name_from_ledger(ledger, "tv")
    tx_region = _body_by_name_from_ledger(ledger, "tx_region")
    tx_copper = _body_by_name_from_ledger(ledger, "tx_ssw_coil_ssw_copper")
    rx_copper = _body_by_name_from_ledger(ledger, "rx_ssw_coil_coil_copper")
    tv_bounds = _bounds(tv)
    tx_region_bounds = _bounds(tx_region)
    tx_bounds = _bounds(tx_copper)
    rx_bounds = _bounds(rx_copper)
    tolerance = 1e-6
    assert _numeric_field(tv, "transparency") == pytest.approx(0.6)
    assert _numeric_field(tx_region, "transparency") == pytest.approx(0.2)
    assert rx_bounds[0] >= tv_bounds[0] - 0.07 - tolerance
    assert rx_bounds[1] <= tv_bounds[1] + tolerance
    assert rx_bounds[2] >= tv_bounds[2] - tolerance
    assert rx_bounds[3] <= tv_bounds[3] + tolerance
    assert rx_bounds[4] >= tv_bounds[4] - 0.07 - tolerance
    assert rx_bounds[5] <= tv_bounds[5] + 0.07 + tolerance
    assert tv_bounds[4] - tx_region_bounds[5] == pytest.approx(100.0)
    assert tx_bounds[5] == pytest.approx(tx_region_bounds[5])
    assert tx_region_bounds[0] <= tx_bounds[0] <= tx_bounds[1] <= tx_region_bounds[1]
    assert tx_region_bounds[2] <= tx_bounds[2] <= tx_bounds[3] <= tx_region_bounds[3]
    assert tx_bounds[4] >= tx_region_bounds[4] - tolerance
    assert tx_bounds[5] <= tx_region_bounds[5] + tolerance
    assert tx_region_bounds[1] - tx_region_bounds[0] > tx_bounds[1] - tx_bounds[0]
    assert tx_region_bounds[3] - tx_region_bounds[2] > tx_bounds[3] - tx_bounds[2]
    assert tx_region_bounds[5] - tx_region_bounds[4] > tx_bounds[5] - tx_bounds[4]
    assert tx_bounds[3] - tx_bounds[2] > tx_bounds[1] - tx_bounds[0]
    assert tx_bounds[5] - tx_bounds[4] < 10.0
    assert rx_bounds[1] - rx_bounds[0] < 10.0
    assert rx_bounds[3] - rx_bounds[2] > rx_bounds[5] - rx_bounds[4]
    tx_port_anchor = tx_placement_params["port_anchor_world_xyz_mm"]
    rx_port_anchor = rx_placement_params["port_anchor_world_xyz_mm"]
    assert isinstance(tx_port_anchor, list)
    assert isinstance(rx_port_anchor, list)
    assert len(tx_port_anchor) == 3
    assert len(rx_port_anchor) == 3
    assert float(tx_port_anchor[2]) == pytest.approx(tx_bounds[4])
    assert float(rx_port_anchor[0]) == pytest.approx(rx_bounds[0])


def test_export_ssw_step_artifacts_supports_explicit_rx_spiral_mode(tmp_path: Path) -> None:
    source_text = FIXED_TOML.read_text(encoding="utf-8")
    custom_text = source_text
    custom_text = custom_text.replace(
        '[modeled_objects.no_ssw_qturn_start_int]\nrange = [true, 0, 0, 1]\ndescription = "RX non-SSW quarter-turn start index; fixed disabled for 0.3.0 SSW"',
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
    spec = load_ssw_fixed_spec(FIXED_TOML)
    assert spec.rx.is_ssw_enabled is False
    assert spec.rx.no_ssw_qturn_start_int == 0
    assert spec.rx.no_ssw_qturn_n_int == 0

    artifacts = export_ssw_step_artifacts(source_toml_path=FIXED_TOML, output_dir=tmp_path / "out", seed=0)
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

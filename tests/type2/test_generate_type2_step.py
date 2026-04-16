from __future__ import annotations

import json
from pathlib import Path

import pytest

from examples.type2.generate_type2_step import export_type2_step_artifacts
from examples.type2.generate_type2_step import load_type2_step_spec


def _range(is_integer: bool, start: float, end: float, count: int) -> str:
    flag = "true" if is_integer else "false"
    return f"[{flag}, {start}, {end}, {count}]"


def _type2_spec_text(
    *,
    modeled_object_id: str = "tx_rect_void_coil",
    modeled_role: str = "tx_single_coil",
    terminal_path: str = "A_cw_to_a",
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
range = {_range(True, 1.0, 1.0, 1)}
[modeled_objects.layer_gap_mm]
range = {_range(False, 2.0, 2.0, 1)}
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


def _write_spec(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "type2.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_example_type2_toml_parses_expected_registry_shape() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2" / "type2.toml"
    spec = load_type2_step_spec(source_toml)

    assert len(spec.non_model_objects) == 7
    assert len(spec.modeled_objects) == 1
    assert spec.modeled_objects[0].object_id == "tx_rect_void_coil"
    assert spec.modeled_objects[0].role == "tx_single_coil"
    assert spec.modeled_objects[0].outer_y_mm.start == pytest.approx(60.0)
    assert spec.modeled_objects[0].outer_y_mm.end == pytest.approx(130.0)
    assert spec.modeled_objects[0].turn_count.end == pytest.approx(4.0)
    assert spec.modeled_objects[0].layer_count.start == pytest.approx(1.0)
    assert spec.modeled_objects[0].layer_count.end == pytest.approx(1.0)


def test_load_type2_step_spec_rejects_duplicate_object_id(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(modeled_object_id="floor"))

    with pytest.raises(ValueError, match=r"duplicate object id: floor"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_unsupported_modeled_role(tmp_path: Path) -> None:
    toml_path = _write_spec(tmp_path, _type2_spec_text(modeled_role="rx_single_coil"))

    with pytest.raises(ValueError, match=r"unsupported modeled object role: rx_single_coil"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_missing_required_modeled_field(tmp_path: Path) -> None:
    terminal_section_lines = {"[modeled_objects.terminal_path]", 'value = "A_cw_to_a"'}
    toml_text = "\n".join(line for line in _type2_spec_text().splitlines() if line not in terminal_section_lines)
    toml_path = _write_spec(tmp_path, toml_text)

    with pytest.raises(ValueError, match=r"modeled_objects\[0\] is missing required key 'terminal_path'"):
        load_type2_step_spec(toml_path)


def test_export_type2_step_artifacts_writes_object_steps_and_ledger(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    source_toml = repo_root / "examples" / "type2" / "type2.toml"
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
    assert len(ledger["non_model_objects"]) == 7
    assert len(ledger["modeled_objects"]) == 1
    for entry in ledger["non_model_objects"]:
        step_path = Path(entry["step_path"])
        assert step_path.is_file()
        assert step_path.stat().st_size > 0
    modeled_entry = ledger["modeled_objects"][0]
    modeled_step_path = Path(modeled_entry["step_path"])
    assert modeled_step_path.is_file()
    assert modeled_step_path.stat().st_size > 0
    source_metadata_path = Path(modeled_entry["source_metadata_path"])
    assert source_metadata_path.is_file()
    source_metadata_payload = json.loads(source_metadata_path.read_text(encoding="utf-8"))
    assert source_metadata_payload["source_toml_path"] == str(source_toml)
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert payload["modeled_objects"][0]["object_id"] == "tx_rect_void_coil"
    assert payload["modeled_objects"][0]["role"] == "tx_single_coil"
    assert payload["modeled_objects"][0]["terminal_metadata"]["path"] == "D_ccw_to_d"
    assert payload["modeled_objects"][0]["expected_exported_body_names"] == ["tx_pcb_l0", "tx_copper_l0"]
    assert payload["modeled_objects"][0]["expected_exported_body_count"] == 2


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
    from examples.type2 import generate_type2_step as module_under_test

    toml_path = _write_spec(tmp_path, _type2_spec_text())
    output_dir = tmp_path / "out"
    ledger_path = tmp_path / "out" / "ledger.json"

    def _false_export_step(*args: object, **kwargs: object) -> bool:
        return False

    monkeypatch.setattr(module_under_test.bd, "export_step", _false_export_step)

    with pytest.raises(RuntimeError, match=r"build123d export_step returned False for non-model object: floor"):
        export_type2_step_artifacts(
            toml_path=toml_path,
            output_dir=output_dir,
            ledger_path=ledger_path,
            seed=0,
        )

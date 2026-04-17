from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from entry.setup_type2_step import (
    export_and_setup_type2_step,
    export_and_setup_type2_step_into_hfss,
    parse_args,
    setup_type2_step_from_args,
)
from peetsfea.aedt.protocols import HfssSession
from peetsfea.backend.pyaedt.type2_step_setup_ready import Type2SetupReadyResult


def _result(*, step_ledger_path: Path, output_aedt_path: Path, imported_ledger_path: Path) -> Type2SetupReadyResult:
    return {
        "source_toml_path": str(step_ledger_path.with_name("type2_fixed.toml")),
        "source_step_ledger_path": str(step_ledger_path),
        "scene_step_path": str(step_ledger_path.with_name("type2_scene.step")),
        "seed": 3,
        "aedt_path": str(output_aedt_path),
        "imported_ledger_path": str(imported_ledger_path),
        "mesh": {
            "module_name": "MeshSetup",
            "operation": "AssignLengthOp",
            "operation_name": "Length1",
            "objects": ["tx_copper_l0", "rx_copper_l0"],
            "refine_inside": False,
            "enabled": True,
            "restrict_elem": False,
            "num_max_elem": "1000",
            "restrict_length": True,
            "max_length": "5mm",
        },
        "boundary": {
            "type": "radiation",
            "offset_type": "Absolute Offset",
            "offset_value": "3500.0",
            "region_name": "Region_Abs_3500mm",
            "face_count": "6",
        },
        "ports": {"tx": ["1_T1"], "rx": ["2_T1"]},
        "sources": {
            "tx_source_name": "1_T1",
            "rx_source_name": "2_T1",
            "tx_magnitude": "288V",
            "rx_magnitude": "0V",
            "tx_phase_deg": "0deg",
            "rx_phase_deg": "0deg",
        },
        "analysis": {
            "setup_name": "Setup1",
            "setup_frequency_hz": 6.78e6,
            "sweep_name": "disabled",
            "sweep_start_hz": 1.0e6,
            "sweep_stop_hz": 45.0e6,
        },
        "validation_report": {"ok": True, "gate": "hard_fail", "message": "ok"},
    }


def _write_canonical_step_ledger(path: Path, *, seed: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "source_toml_path": str(path.with_name("type2_fixed.toml")),
                "output_dir": str(path.parent),
                "scene_step_path": str(path.with_name("type2_scene.step")),
                "seed": seed,
                "em_policy": {"radiation_margin_mm": 3500.0},
                "non_model_objects": [{"object_id": "nm"}],
                "modeled_objects": [{"object_id": "tx"}, {"object_id": "rx"}],
            }
        ),
        encoding="utf-8",
    )


def test_setup_type2_step_entry_generates_fresh_ledger_before_runtime(tmp_path: Path) -> None:
    toml_path = tmp_path / "type2_fixed.toml"
    output_dir = tmp_path / "step"
    step_ledger_path = output_dir / "type2_step_ledger.json"
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    exporter_calls: list[dict[str, object]] = []
    runner_calls: list[dict[str, object]] = []

    def _exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        _write_canonical_step_ledger(cast(Path, kwargs["ledger_path"]), seed=cast(int, kwargs["seed"]))
        return {"ok": True}

    def _runner(**kwargs: object) -> Type2SetupReadyResult:
        runner_calls.append(dict(kwargs))
        return _result(
            step_ledger_path=cast(Path, kwargs["step_ledger_path"]),
            output_aedt_path=cast(Path, kwargs["output_aedt_path"]),
            imported_ledger_path=cast(Path, kwargs["imported_ledger_path"]),
        )

    args = parse_args(
        [
            "--toml",
            str(toml_path),
            "--output-dir",
            str(output_dir),
            "--step-ledger",
            str(step_ledger_path),
            "--output-aedt",
            str(output_aedt_path),
            "--imported-ledger",
            str(imported_ledger_path),
            "--seed",
            "3",
            "--design-name",
            "entry_fake",
        ]
    )

    result = setup_type2_step_from_args(args, exporter=_exporter, runner=_runner)

    assert exporter_calls == [
        {
            "toml_path": toml_path,
            "output_dir": output_dir,
            "ledger_path": step_ledger_path,
            "seed": 3,
        }
    ]
    assert runner_calls == [
        {
            "step_ledger_path": step_ledger_path,
            "output_aedt_path": output_aedt_path,
            "imported_ledger_path": imported_ledger_path,
            "design_name": "entry_fake",
        }
    ]
    assert result["source_step_ledger_path"] == str(step_ledger_path)


def test_setup_type2_step_entry_uses_existing_ledger_without_export(tmp_path: Path) -> None:
    existing_ledger_path = tmp_path / "existing" / "type2_step_ledger.json"
    _write_canonical_step_ledger(existing_ledger_path, seed=0)
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    exporter_calls: list[dict[str, object]] = []
    runner_calls: list[dict[str, object]] = []

    def _exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        return {"ok": True}

    def _runner(**kwargs: object) -> Type2SetupReadyResult:
        runner_calls.append(dict(kwargs))
        return _result(
            step_ledger_path=cast(Path, kwargs["step_ledger_path"]),
            output_aedt_path=cast(Path, kwargs["output_aedt_path"]),
            imported_ledger_path=cast(Path, kwargs["imported_ledger_path"]),
        )

    args = parse_args(
        [
            "--ledger",
            str(existing_ledger_path),
            "--output-aedt",
            str(output_aedt_path),
            "--imported-ledger",
            str(imported_ledger_path),
            "--design-name",
            "entry_fake",
        ]
    )

    result = setup_type2_step_from_args(args, exporter=_exporter, runner=_runner)

    assert exporter_calls == []
    assert runner_calls == [
        {
            "step_ledger_path": existing_ledger_path,
            "output_aedt_path": output_aedt_path,
            "imported_ledger_path": imported_ledger_path,
            "design_name": "entry_fake",
        }
    ]
    assert result["source_step_ledger_path"] == str(existing_ledger_path)


def test_export_and_setup_type2_step_into_hfss_runs_export_then_attached_runtime(tmp_path: Path) -> None:
    toml_path = tmp_path / "type2_fixed.toml"
    output_dir = tmp_path / "step"
    step_ledger_path = output_dir / "type2_step_ledger.json"
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    exporter_calls: list[dict[str, object]] = []
    runner_calls: list[dict[str, object]] = []
    fake_hfss = cast(HfssSession, object())

    def _exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        return {"ok": True}

    def _runner(**kwargs: object) -> Type2SetupReadyResult:
        runner_calls.append(dict(kwargs))
        return _result(
            step_ledger_path=cast(Path, kwargs["step_ledger_path"]),
            output_aedt_path=cast(Path, kwargs["output_aedt_path"]),
            imported_ledger_path=cast(Path, kwargs["imported_ledger_path"]),
        )

    result = export_and_setup_type2_step_into_hfss(
        hfss=fake_hfss,
        toml_path=toml_path,
        output_dir=output_dir,
        step_ledger_path=step_ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        seed=11,
        exporter=_exporter,
        runner=_runner,
    )

    assert exporter_calls == [
        {
            "toml_path": toml_path,
            "output_dir": output_dir,
            "ledger_path": step_ledger_path,
            "seed": 11,
        }
    ]
    assert runner_calls == [
        {
            "hfss": fake_hfss,
            "step_ledger_path": step_ledger_path,
            "output_aedt_path": output_aedt_path,
            "imported_ledger_path": imported_ledger_path,
        }
    ]
    assert result["source_step_ledger_path"] == str(step_ledger_path)


def test_export_and_setup_type2_step_runs_export_then_headless_runtime(tmp_path: Path) -> None:
    toml_path = tmp_path / "type2_fixed.toml"
    output_dir = tmp_path / "step"
    step_ledger_path = output_dir / "type2_step_ledger.json"
    output_aedt_path = tmp_path / "aedt" / "type2_setup_ready.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    exporter_calls: list[dict[str, object]] = []
    runner_calls: list[dict[str, object]] = []

    def _exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        return {"ok": True}

    def _runner(**kwargs: object) -> Type2SetupReadyResult:
        runner_calls.append(dict(kwargs))
        return _result(
            step_ledger_path=cast(Path, kwargs["step_ledger_path"]),
            output_aedt_path=cast(Path, kwargs["output_aedt_path"]),
            imported_ledger_path=cast(Path, kwargs["imported_ledger_path"]),
        )

    result = export_and_setup_type2_step(
        toml_path=toml_path,
        output_dir=output_dir,
        step_ledger_path=step_ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        seed=17,
        design_name="entry_fake",
        exporter=_exporter,
        runner=_runner,
    )

    assert exporter_calls == [
        {
            "toml_path": toml_path,
            "output_dir": output_dir,
            "ledger_path": step_ledger_path,
            "seed": 17,
        }
    ]
    assert runner_calls == [
        {
            "step_ledger_path": step_ledger_path,
            "output_aedt_path": output_aedt_path,
            "imported_ledger_path": imported_ledger_path,
            "design_name": "entry_fake",
        }
    ]
    assert result["source_step_ledger_path"] == str(step_ledger_path)

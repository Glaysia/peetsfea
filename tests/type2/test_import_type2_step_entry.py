from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from entry.import_type2_step import (
    export_and_import_type2_step,
    export_and_import_type2_step_into_hfss,
    import_type2_step_from_args,
    parse_args,
)
from peetsfea.aedt.protocols import HfssSession
from peetsfea.backend.pyaedt.type2_step_import_pipeline import Type2ImportedLedger


def _result(*, step_ledger_path: Path, output_aedt_path: Path, imported_ledger_path: Path) -> Type2ImportedLedger:
    return {
        "source_toml_path": str(step_ledger_path.with_name("type2_fixed.toml")),
        "source_step_ledger_path": str(step_ledger_path),
        "scene_step_path": str(step_ledger_path.with_name("type2_scene.step")),
        "seed": 3,
        "aedt_path": str(output_aedt_path),
        "imported_ledger_path": str(imported_ledger_path),
        "non_model_objects": [],
        "modeled_objects": [],
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
                "non_model_objects": [],
                "modeled_objects": [],
            }
        ),
        encoding="utf-8",
    )


def test_import_type2_step_entry_generates_fresh_ledger_before_import(tmp_path: Path) -> None:
    toml_path = tmp_path / "type2_fixed.toml"
    output_dir = tmp_path / "step"
    step_ledger_path = output_dir / "type2_step_ledger.json"
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    exporter_calls: list[dict[str, object]] = []
    importer_calls: list[dict[str, object]] = []

    def _exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        _write_canonical_step_ledger(cast(Path, kwargs["ledger_path"]), seed=cast(int, kwargs["seed"]))
        return {"ok": True}

    def _importer(**kwargs: object) -> Type2ImportedLedger:
        importer_calls.append(dict(kwargs))
        step_ledger_path_arg = cast(Path, kwargs["step_ledger_path"])
        step_ledger_payload = json.loads(step_ledger_path_arg.read_text(encoding="utf-8"))
        assert step_ledger_payload["em_policy"] == {"radiation_margin_mm": 3500.0}
        assert "import_time_policy" not in step_ledger_payload
        return _result(
            step_ledger_path=step_ledger_path_arg,
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

    result = import_type2_step_from_args(args, exporter=_exporter, importer=_importer)

    assert exporter_calls == [
        {
            "toml_path": toml_path,
            "output_dir": output_dir,
            "ledger_path": step_ledger_path,
            "seed": 3,
        }
    ]
    assert importer_calls == [
        {
            "step_ledger_path": step_ledger_path,
            "output_aedt_path": output_aedt_path,
            "imported_ledger_path": imported_ledger_path,
            "design_name": "entry_fake",
        }
    ]
    assert result["source_step_ledger_path"] == str(step_ledger_path)


def test_import_type2_step_entry_uses_existing_ledger_without_export(tmp_path: Path) -> None:
    existing_ledger_path = tmp_path / "existing" / "type2_step_ledger.json"
    _write_canonical_step_ledger(existing_ledger_path, seed=0)
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    exporter_calls: list[dict[str, object]] = []
    importer_calls: list[dict[str, object]] = []

    def _exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        return {"ok": True}

    def _importer(**kwargs: object) -> Type2ImportedLedger:
        importer_calls.append(dict(kwargs))
        step_ledger_path_arg = cast(Path, kwargs["step_ledger_path"])
        step_ledger_payload = json.loads(step_ledger_path_arg.read_text(encoding="utf-8"))
        assert step_ledger_payload["em_policy"] == {"radiation_margin_mm": 3500.0}
        assert "import_time_policy" not in step_ledger_payload
        return _result(
            step_ledger_path=step_ledger_path_arg,
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

    result = import_type2_step_from_args(args, exporter=_exporter, importer=_importer)

    assert exporter_calls == []
    assert importer_calls == [
        {
            "step_ledger_path": existing_ledger_path,
            "output_aedt_path": output_aedt_path,
            "imported_ledger_path": imported_ledger_path,
            "design_name": "entry_fake",
        }
    ]
    assert result["source_step_ledger_path"] == str(existing_ledger_path)


def test_export_and_import_type2_step_into_hfss_runs_export_then_attached_import(tmp_path: Path) -> None:
    toml_path = tmp_path / "type2_fixed.toml"
    output_dir = tmp_path / "step"
    step_ledger_path = output_dir / "type2_step_ledger.json"
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    exporter_calls: list[dict[str, object]] = []
    importer_calls: list[dict[str, object]] = []
    fake_hfss = cast(HfssSession, object())

    def _exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        return {"ok": True}

    def _importer(**kwargs: object) -> Type2ImportedLedger:
        importer_calls.append(dict(kwargs))
        return _result(
            step_ledger_path=cast(Path, kwargs["step_ledger_path"]),
            output_aedt_path=cast(Path, kwargs["output_aedt_path"]),
            imported_ledger_path=cast(Path, kwargs["imported_ledger_path"]),
        )

    result = export_and_import_type2_step_into_hfss(
        hfss=fake_hfss,
        toml_path=toml_path,
        output_dir=output_dir,
        step_ledger_path=step_ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        seed=11,
        exporter=_exporter,
        importer=_importer,
    )

    assert exporter_calls == [
        {
            "toml_path": toml_path,
            "output_dir": output_dir,
            "ledger_path": step_ledger_path,
            "seed": 11,
        }
    ]
    assert importer_calls == [
        {
            "hfss": fake_hfss,
            "step_ledger_path": step_ledger_path,
            "output_aedt_path": output_aedt_path,
            "imported_ledger_path": imported_ledger_path,
        }
    ]
    assert result["source_step_ledger_path"] == str(step_ledger_path)


def test_export_and_import_type2_step_runs_export_then_headless_import(tmp_path: Path) -> None:
    toml_path = tmp_path / "type2_fixed.toml"
    output_dir = tmp_path / "step"
    step_ledger_path = output_dir / "type2_step_ledger.json"
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    exporter_calls: list[dict[str, object]] = []
    importer_calls: list[dict[str, object]] = []

    def _exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        return {"ok": True}

    def _importer(**kwargs: object) -> Type2ImportedLedger:
        importer_calls.append(dict(kwargs))
        return _result(
            step_ledger_path=cast(Path, kwargs["step_ledger_path"]),
            output_aedt_path=cast(Path, kwargs["output_aedt_path"]),
            imported_ledger_path=cast(Path, kwargs["imported_ledger_path"]),
        )

    result = export_and_import_type2_step(
        toml_path=toml_path,
        output_dir=output_dir,
        step_ledger_path=step_ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        seed=5,
        design_name="headless_owner",
        exporter=_exporter,
        importer=_importer,
    )

    assert exporter_calls == [
        {
            "toml_path": toml_path,
            "output_dir": output_dir,
            "ledger_path": step_ledger_path,
            "seed": 5,
        }
    ]
    assert importer_calls == [
        {
            "step_ledger_path": step_ledger_path,
            "output_aedt_path": output_aedt_path,
            "imported_ledger_path": imported_ledger_path,
            "design_name": "headless_owner",
        }
    ]
    assert result["source_step_ledger_path"] == str(step_ledger_path)

from __future__ import annotations

import sys
from types import ModuleType
import json
from pathlib import Path
from typing import cast

_stub_generate_type2_step = ModuleType("entry.generate_type2_step")


def _unexpected_export_type2_step_artifacts(**_: object) -> object:
    raise AssertionError("test must provide its own exporter stub")


setattr(_stub_generate_type2_step, "export_type2_step_artifacts", _unexpected_export_type2_step_artifacts)
sys.modules.setdefault("entry.generate_type2_step", _stub_generate_type2_step)

from entry.import_type2_step import (
    export_and_import_type2_step,
    export_and_import_type2_step_into_hfss,
    import_type2_step_from_args,
    parse_args,
)
from peetsfea.aedt.protocols import HfssSession
from peetsfea.backend.pyaedt.type2_step_import_pipeline import Type2ImportedLedger
from tests.fixtures.legacy.type1_spec import type1_outputs_spec


def _result(*, step_ledger_path: Path, output_aedt_path: Path, imported_ledger_path: Path) -> Type2ImportedLedger:
    return {
        "source_toml_path": str(step_ledger_path.with_name("type2_fixed.toml")),
        "source_step_ledger_path": str(step_ledger_path),
        "scene_step_path": str(step_ledger_path.with_name("type2_scene.step")),
        "seed": 3,
        "aedt_path": str(output_aedt_path),
        "imported_ledger_path": str(imported_ledger_path),
        "non_model_objects": [],
        "modeled_objects": [
            {
                "object_id": "tx_rect_void_coil",
                "role": "tx_single_coil",
                "imported_object_names": [
                    "tx_pcb_l0",
                    "tx_copper_l0",
                    "tx_underlay_ferrite_u0",
                    "tx_underlay_pet_psa_u0",
                    "tx_underlay_air_u0",
                    "tx_port_sheet",
                ],
            },
            {
                "object_id": "rx_rect_void_coil",
                "role": "rx_single_coil",
                "imported_object_names": [
                    "rx_pcb_l0",
                    "rx_copper_l0",
                    "under_rx_ferrite_u0",
                    "under_rx_pet_psa_u0",
                    "under_rx_air_u0",
                    "rx_port_sheet",
                ],
            },
        ],
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
                "outputs": type1_outputs_spec(),
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
        assert step_ledger_payload["outputs"] == type1_outputs_spec()
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
    modeled_by_id = {entry["object_id"]: entry for entry in result["modeled_objects"]}
    assert modeled_by_id["tx_rect_void_coil"]["imported_object_names"] == [
        "tx_pcb_l0",
        "tx_copper_l0",
        "tx_underlay_ferrite_u0",
        "tx_underlay_pet_psa_u0",
        "tx_underlay_air_u0",
        "tx_port_sheet",
    ]
    assert modeled_by_id["rx_rect_void_coil"]["imported_object_names"] == [
        "rx_pcb_l0",
        "rx_copper_l0",
        "under_rx_ferrite_u0",
        "under_rx_pet_psa_u0",
        "under_rx_air_u0",
        "rx_port_sheet",
    ]


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
        assert step_ledger_payload["outputs"] == type1_outputs_spec()
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
    tx_entry = next(
        entry for entry in result["modeled_objects"] if cast(str, entry["object_id"]) == "tx_rect_void_coil"
    )
    tx_imported_names = cast(list[str], tx_entry["imported_object_names"])
    assert tx_imported_names[2:5] == [
        "tx_underlay_ferrite_u0",
        "tx_underlay_pet_psa_u0",
        "tx_underlay_air_u0",
    ]
    rx_entry = next(
        entry for entry in result["modeled_objects"] if cast(str, entry["object_id"]) == "rx_rect_void_coil"
    )
    rx_imported_names = cast(list[str], rx_entry["imported_object_names"])
    assert rx_imported_names[2:5] == [
        "under_rx_ferrite_u0",
        "under_rx_pet_psa_u0",
        "under_rx_air_u0",
    ]


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

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import peetsfea.type2_runtime as type2_runtime
from peetsfea.type2_sampled import PreparedType2Build
import peetsfea.type2_sampled as type2_sampled


def _write_sampled_toml(tmp_path: Path) -> Path:
    source_toml_path = tmp_path / "source.toml"
    source_toml_path.write_text("# source fixture exists for sampled metadata\n", encoding="utf-8")
    design_dir = tmp_path / "sampled-design"
    design_dir.mkdir()
    sampled_toml_path = design_dir / "sampled.toml"
    sampled_toml_path.write_text(
        "\n".join(
            (
                "[sampled]",
                f'source_toml_path = "{source_toml_path}"',
                "seed = 71",
                "sample_index = 4",
                'head_hash4 = "abcd"',
                "retry_number = 0",
                "sampled_owner_paths = []",
                "",
            )
        ),
        encoding="utf-8",
    )
    return sampled_toml_path


def _prepared_build_from_sampled_toml(sampled_toml_path: Path) -> PreparedType2Build:
    metadata = type2_sampled.load_type2_sample_metadata(sampled_toml_path)
    manifest_entry = type2_sampled._manifest_entry_from_sampled_toml(metadata, sampled_toml_path)
    design_dir = Path(manifest_entry["design_dir"])
    return PreparedType2Build(
        design_id=manifest_entry["design_id"],
        seed=manifest_entry["seed"],
        source_toml_path=Path(manifest_entry["source_toml_path"]),
        sampled_toml_path=Path(manifest_entry["sampled_toml_path"]),
        design_dir=design_dir,
        scene_step_path=Path(manifest_entry["scene_step_path"]),
        step_ledger_path=Path(manifest_entry["step_ledger_path"]),
        imported_ledger_path=Path(manifest_entry["imported_ledger_path"]),
        aedt_path=Path(manifest_entry["aedt_path"]),
        sampled_owner_paths=tuple(manifest_entry["sampled_owner_paths"]),
        modeled_roles=("rx_single_coil",),
        design_variables=(),
    )


def _write_valid_step_ledger(prepared_build: PreparedType2Build) -> None:
    prepared_build.scene_step_path.write_text("STEP fixture\n", encoding="utf-8")
    prepared_build.step_ledger_path.write_text(
        json.dumps({"scene_step_path": str(prepared_build.scene_step_path)}, indent=2),
        encoding="utf-8",
    )


def test_existing_exact_hash_derived_target_aedt_is_built_without_imported_ledger(tmp_path: Path) -> None:
    sampled_toml_path = _write_sampled_toml(tmp_path)
    prepared_build = _prepared_build_from_sampled_toml(sampled_toml_path)
    generated_hash4 = type2_sampled._hash4_from_bytes(sampled_toml_path.read_bytes())
    expected_design_id = type2_sampled.build_type2_design_id(
        sample_index=4,
        generated_hash4=generated_hash4,
        head_hash4="abcd",
        retry_number=0,
    )
    assert prepared_build.design_id == expected_design_id
    assert prepared_build.aedt_path == sampled_toml_path.parent / f"{expected_design_id}.aedt"

    _write_valid_step_ledger(prepared_build)
    prepared_build.aedt_path.write_text("existing AEDT marker\n", encoding="utf-8")
    assert not prepared_build.imported_ledger_path.exists()

    def _unexpected_exporter(**kwargs: object) -> object:
        raise AssertionError(f"exact AEDT target skip must not export STEP artifacts: {kwargs!r}")

    def _unexpected_runner(**kwargs: object) -> type2_runtime._Type2BuildRunnerResult:
        raise AssertionError(f"exact AEDT target skip must not run AEDT setup: {kwargs!r}")

    batch = type2_runtime.build_prepared_type2_designs_best_effort(
        (prepared_build,),
        jobs=1,
        exporter=_unexpected_exporter,
        runner=_unexpected_runner,
    )

    assert batch["skipped"] == []
    assert batch["built"] == [
        {
            "design_id": expected_design_id,
            "sampled_toml_path": str(sampled_toml_path.resolve(strict=False)),
            "aedt_path": str(prepared_build.aedt_path),
            "source_step_ledger_path": str(prepared_build.step_ledger_path),
            "imported_ledger_path": str(prepared_build.imported_ledger_path),
        }
    ]


def test_missing_exact_hash_derived_target_aedt_runs_normal_build_path(tmp_path: Path) -> None:
    sampled_toml_path = _write_sampled_toml(tmp_path)
    prepared_build = _prepared_build_from_sampled_toml(sampled_toml_path)
    _write_valid_step_ledger(prepared_build)
    (prepared_build.design_dir / "other_existing.aedt").write_text("not the target\n", encoding="utf-8")
    assert not prepared_build.aedt_path.exists()

    runner_calls: list[dict[str, object]] = []

    def _unexpected_exporter(**kwargs: object) -> object:
        raise AssertionError(f"valid existing STEP ledger must not call exporter: {kwargs!r}")

    def _fake_runner(**kwargs: object) -> type2_runtime._Type2BuildRunnerResult:
        runner_calls.append(dict(kwargs))
        return {
            "aedt_path": str(cast(Path, kwargs["output_aedt_path"])),
            "source_step_ledger_path": str(cast(Path, kwargs["step_ledger_path"])),
            "imported_ledger_path": str(cast(Path, kwargs["imported_ledger_path"])),
        }

    batch = type2_runtime.build_prepared_type2_designs_best_effort(
        (prepared_build,),
        jobs=1,
        exporter=_unexpected_exporter,
        runner=_fake_runner,
    )

    assert batch["skipped"] == []
    assert len(batch["built"]) == 1
    assert batch["built"][0]["design_id"] == prepared_build.design_id
    assert batch["built"][0]["aedt_path"] == str(prepared_build.aedt_path)
    assert len(runner_calls) == 1
    assert runner_calls[0]["design_name"] == prepared_build.design_id
    assert runner_calls[0]["output_aedt_path"] == prepared_build.aedt_path
    assert runner_calls[0]["imported_ledger_path"] == prepared_build.imported_ledger_path

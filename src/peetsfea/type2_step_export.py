from __future__ import annotations

import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Literal, cast

import build123d as bd

from peetsfea.tx_rect_void import export_tx_rect_void_step_from_spec
from peetsfea.tx_rect_void import load_tx_rect_void_spec
from peetsfea.tx_rect_void import profile_for_modeled_role
from peetsfea.type2_step_ledger import ModeledObjectSceneData
from peetsfea.type2_step_ledger import Type2DirectModeledArtifact
from peetsfea.type2_step_ledger import Type2StepLedger
from peetsfea.type2_step_ledger import build_modeled_object_ledger_entry
from peetsfea.type2_step_ledger import build_type2_step_ledger
from peetsfea.type2_step_ledger import write_modeled_source_metadata
from peetsfea.type2_step_ledger import write_type2_step_ledger
from peetsfea.type2_step_scene import build_modeled_single_coil_scene_data
from peetsfea.type2_step_scene import build_non_model_scene_entry
from peetsfea.type2_step_scene import build_non_model_scene_shapes
from peetsfea.type2_step_scene import require_non_model_object_spec
from peetsfea.type2_step_scene import single_coil_placement_offset
from peetsfea.type2_step_spec import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import load_type2_step_spec
from peetsfea.type2_step_spec import render_tx_rect_void_toml

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_TOML_PATH = REPO_ROOT / "examples" / "type2_fixed.toml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "run" / "step" / "type2"
DEFAULT_LEDGER_PATH = DEFAULT_OUTPUT_DIR / "type2_step_ledger.json"
DEFAULT_SCENE_STEP_PATH = DEFAULT_OUTPUT_DIR / "type2_scene.step"


def _require_key(table: dict[str, object], key: str, context: str) -> object:
    if key not in table:
        raise ValueError(f"{context} is missing required key '{key}'")
    return table[key]


def _require_table(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be a table")
    return cast(dict[str, object], value)


def _require_non_empty_str(table: dict[str, object], key: str, context: str) -> str:
    raw_value = _require_key(table, key, context)
    if not isinstance(raw_value, str):
        raise TypeError(f"{context}.{key} must be str")
    if raw_value == "":
        raise ValueError(f"{context}.{key} must be non-empty")
    return raw_value


def _remove_generated_type2_artifacts(output_dir: Path) -> None:
    stale_file_paths = (
        output_dir / "type2_non_model_scene.step",
        output_dir / "type2_combined_preview.step",
    )
    for stale_file_path in stale_file_paths:
        if stale_file_path.exists():
            if not stale_file_path.is_file():
                raise RuntimeError(f"type2 generated artifact path must be a file: {stale_file_path}")
            stale_file_path.unlink()
    stale_dir_paths = (
        output_dir / "objects",
        output_dir / "metadata",
    )
    for stale_dir_path in stale_dir_paths:
        if stale_dir_path.exists():
            if not stale_dir_path.is_dir():
                raise RuntimeError(f"type2 generated artifact path must be a directory: {stale_dir_path}")
            shutil.rmtree(stale_dir_path)


def _export_modeled_single_coil(
    spec: ModeledTxSingleCoilSpec,
    *,
    owner_spec: NonModelBoxSpec,
    source_toml_path: Path,
    output_path: Path,
    metadata_path: Path,
    seed: int,
) -> Type2DirectModeledArtifact:
    profile = profile_for_modeled_role(spec.role)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="type2_tx_rect_void_") as temp_dir:
        temp_toml_path = Path(temp_dir) / f"{spec.object_id}.toml"
        temp_toml_path.write_text(render_tx_rect_void_toml(spec), encoding="utf-8")
        placement_offset_xyz = single_coil_placement_offset(
            owner_spec=owner_spec,
            tx_rect_void_spec_path=temp_toml_path,
            seed=seed,
            profile=profile,
        )
        tx_rect_void_spec = load_tx_rect_void_spec(temp_toml_path)
        export_result = export_tx_rect_void_step_from_spec(
            spec=tx_rect_void_spec,
            source_toml_path=source_toml_path,
            output_step_path=output_path,
            metadata_path=metadata_path,
            seed=seed,
            placement_offset_xyz=placement_offset_xyz,
            profile=profile,
        )
    if len(export_result.modeled_objects) != 1:
        raise RuntimeError(
            "tx_rect_void export must return exactly one modeled object "
            f"(actual={len(export_result.modeled_objects)})"
        )
    modeled_object_raw = asdict(export_result.modeled_objects[0])
    modeled_object = _require_table(modeled_object_raw, f"modeled export [{spec.object_id}]")
    exported_object_id = _require_non_empty_str(modeled_object, "object_id", "modeled export object")
    if exported_object_id != spec.object_id:
        raise RuntimeError(
            "modeled object id mismatch between type2 TOML and tx_rect_void export "
            f"(spec={spec.object_id}, exported={exported_object_id})"
        )
    exported_material = _require_non_empty_str(modeled_object, "material", "modeled export object")
    if exported_material != spec.material:
        raise RuntimeError(
            "modeled object material mismatch between type2 TOML and tx_rect_void export "
            f"(spec={spec.material}, exported={exported_material})"
        )
    exported_role = _require_non_empty_str(modeled_object, "role", "modeled export object")
    if exported_role != spec.role:
        raise RuntimeError(f"modeled export role must be {spec.role} (actual={exported_role})")
    raw_model_state = _require_key(modeled_object, "model_state", "modeled export object")
    if raw_model_state is not True:
        raise RuntimeError("modeled export model_state must be true")
    exported_step_path = _require_non_empty_str(modeled_object, "step_path", "modeled export object")
    if exported_step_path != str(output_path):
        raise RuntimeError(
            "modeled export step_path does not match requested output path "
            f"(exported={exported_step_path}, expected={output_path})"
        )

    raw_canonical = _require_key(modeled_object, "canonical_coordinates", "modeled export object")
    canonical_coordinates = _require_table(raw_canonical, "modeled export canonical_coordinates")
    raw_terminal = _require_key(modeled_object, "terminal_metadata", "modeled export object")
    terminal_metadata = _require_table(raw_terminal, "modeled export terminal_metadata")
    raw_expected_names = _require_key(modeled_object, "expected_exported_body_names", "modeled export object")
    if isinstance(raw_expected_names, (str, bytes)) or not isinstance(raw_expected_names, (list, tuple)):
        raise TypeError("modeled export expected_exported_body_names must be a list or tuple")
    expected_exported_body_names: list[str] = []
    for index, raw_name in enumerate(raw_expected_names):
        if not isinstance(raw_name, str) or raw_name == "":
            raise TypeError(f"modeled export expected_exported_body_names[{index}] must be non-empty str")
        expected_exported_body_names.append(raw_name)
    raw_expected_count = _require_key(modeled_object, "expected_exported_body_count", "modeled export object")
    if isinstance(raw_expected_count, bool) or not isinstance(raw_expected_count, int):
        raise TypeError("modeled export expected_exported_body_count must be int")
    if raw_expected_count != len(expected_exported_body_names):
        raise RuntimeError(
            "modeled export expected body count mismatch "
            f"(count={raw_expected_count}, names={expected_exported_body_names})"
        )
    return {
        "object_id": exported_object_id,
        "role": cast(Literal["tx_single_coil", "rx_single_coil"], exported_role),
        "plane": cast(Literal["XY", "YZ"], _require_non_empty_str(modeled_object, "plane", "modeled export object")),
        "placement_owner_id": _require_non_empty_str(modeled_object, "placement_owner_id", "modeled export object"),
        "material": exported_material,
        "model_state": True,
        "step_path": exported_step_path,
        "expected_exported_body_names": tuple(expected_exported_body_names),
        "expected_exported_body_count": raw_expected_count,
        "canonical_coordinates": canonical_coordinates,
        "terminal_metadata": terminal_metadata,
        "source_metadata_path": str(metadata_path),
    }


def export_type2_tx_single_coil_artifact(
    *,
    toml_path: Path,
    output_step_path: Path,
    metadata_path: Path,
    seed: int,
) -> Type2DirectModeledArtifact:
    spec = load_type2_step_spec(toml_path)
    tx_specs = [modeled_spec for modeled_spec in spec.modeled_objects if modeled_spec.role == "tx_single_coil"]
    if len(tx_specs) != 1:
        raise RuntimeError(
            "type2 tx_single_coil direct export requires exactly one tx_single_coil modeled object "
            f"(actual={len(tx_specs)})"
        )
    tx_profile = profile_for_modeled_role("tx_single_coil")
    owner_spec = require_non_model_object_spec(spec.non_model_objects, object_id=tx_profile.placement_owner_id)
    return _export_modeled_single_coil(
        tx_specs[0],
        owner_spec=owner_spec,
        source_toml_path=toml_path,
        output_path=output_step_path,
        metadata_path=metadata_path,
        seed=seed,
    )


def export_type2_step_artifacts(
    *,
    toml_path: Path = SOURCE_TOML_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    seed: int = 0,
) -> Type2StepLedger:
    spec = load_type2_step_spec(toml_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    _remove_generated_type2_artifacts(output_dir)
    scene_step_path = output_dir / DEFAULT_SCENE_STEP_PATH.name
    object_metadata_dir = output_dir / "metadata"

    non_model_entries = [build_non_model_scene_entry(spec.non_model_objects)]
    scene_shapes: list[bd.Shape] = list(build_non_model_scene_shapes(spec.non_model_objects))
    modeled_entries = []
    for modeled_spec in spec.modeled_objects:
        profile = profile_for_modeled_role(modeled_spec.role)
        owner_spec = require_non_model_object_spec(spec.non_model_objects, object_id=profile.placement_owner_id)
        metadata_path = object_metadata_dir / f"{modeled_spec.object_id}.metadata.json"
        modeled_scene_shapes, scene_data = build_modeled_single_coil_scene_data(
            modeled_spec,
            owner_spec=owner_spec,
            seed=seed,
        )
        write_modeled_source_metadata(
            metadata_path=metadata_path,
            source_toml_path=toml_path,
            scene_step_path=scene_step_path,
            scene_data=scene_data,
        )
        modeled_entry = build_modeled_object_ledger_entry(
            scene_data=scene_data,
            source_metadata_path=metadata_path,
        )
        scene_shapes.extend(modeled_scene_shapes)
        modeled_entries.append(modeled_entry)

    scene_body_names = tuple(shape.label for shape in scene_shapes)
    if len(scene_body_names) != len(set(scene_body_names)):
        raise RuntimeError(f"type2 scene STEP body names must be unique (actual={scene_body_names})")
    for shape in scene_shapes:
        solid_count = len(tuple(shape.solids()))
        if solid_count != 1:
            raise RuntimeError(
                "type2 scene STEP top-level child must contain exactly one solid "
                f"(label={shape.label}, solid_count={solid_count})"
            )
    scene = bd.Compound(children=scene_shapes, label="type2_scene")
    export_ok = bd.export_step(scene, scene_step_path)
    if export_ok is not True:
        raise RuntimeError(f"build123d export_step returned False for type2 scene STEP: {scene_step_path}")

    ledger = build_type2_step_ledger(
        source_toml_path=spec.source_toml_path,
        output_dir=output_dir,
        scene_step_path=scene_step_path,
        seed=seed,
        non_model_objects=non_model_entries,
        modeled_objects=modeled_entries,
    )
    write_type2_step_ledger(ledger_path=ledger_path, ledger=ledger)
    return ledger


__all__ = [
    "DEFAULT_LEDGER_PATH",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_SCENE_STEP_PATH",
    "REPO_ROOT",
    "SOURCE_TOML_PATH",
    "Type2DirectModeledArtifact",
    "Type2StepLedger",
    "export_type2_step_artifacts",
    "export_type2_tx_single_coil_artifact",
]

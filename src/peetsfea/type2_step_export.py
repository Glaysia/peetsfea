from __future__ import annotations

import shutil
from pathlib import Path

import build123d as bd

from peetsfea.tx_rect_void import profile_for_modeled_role
from peetsfea.type2_step_ledger import Type2DirectModeledArtifact
from peetsfea.type2_step_ledger import Type2ImportEmPolicy
from peetsfea.type2_step_ledger import Type2StepLedger
from peetsfea.type2_step_ledger import build_modeled_object_ledger_entry
from peetsfea.type2_step_ledger import build_type2_step_ledger
from peetsfea.type2_step_ledger import write_modeled_source_metadata
from peetsfea.type2_step_ledger import write_type2_step_ledger
from peetsfea.type2_step_scene import build_modeled_single_coil_scene_data
from peetsfea.type2_step_scene import build_non_model_scene_entry
from peetsfea.type2_step_scene import build_non_model_scene_shapes
from peetsfea.type2_step_scene import require_non_model_object_spec
from peetsfea.type2_step_spec import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import load_type2_step_spec

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_TOML_PATH = REPO_ROOT / "examples" / "type2_fixed.toml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "run" / "step" / "type2"
DEFAULT_LEDGER_PATH = DEFAULT_OUTPUT_DIR / "type2_step_ledger.json"
DEFAULT_SCENE_STEP_PATH = DEFAULT_OUTPUT_DIR / "type2_scene.step"


def _validate_top_level_scene_child(shape: bd.Shape) -> None:
    solid_count = len(tuple(shape.solids()))
    if solid_count == 1:
        return
    if solid_count != 0:
        raise RuntimeError(
            "type2 scene STEP top-level child must contain either one solid or one sheet "
            f"(label={shape.label}, solid_count={solid_count})"
        )
    face_count = len(tuple(shape.faces()))
    if face_count != 1:
        raise RuntimeError(
            "type2 scene STEP top-level non-solid child must contain exactly one face "
            f"(label={shape.label}, face_count={face_count})"
        )


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
    scene_children, scene_data = build_modeled_single_coil_scene_data(
        spec,
        owner_spec=owner_spec,
        seed=seed,
    )
    for shape in scene_children:
        _validate_top_level_scene_child(shape)
    scene = bd.Compound(children=scene_children, label=profile.compound_label)
    export_ok = bd.export_step(scene, output_path)
    if export_ok is not True:
        raise RuntimeError(f"build123d export_step returned False for modeled type2 STEP: {output_path}")
    write_modeled_source_metadata(
        metadata_path=metadata_path,
        source_toml_path=source_toml_path,
        scene_step_path=output_path,
        scene_data=scene_data,
    )
    return {
        "object_id": scene_data["object_id"],
        "role": scene_data["role"],
        "plane": scene_data["plane"],
        "placement_owner_id": scene_data["placement_owner_id"],
        "material": scene_data["material"],
        "model_state": scene_data["model_state"],
        "step_path": str(output_path),
        "expected_exported_body_names": scene_data["expected_exported_body_names"],
        "expected_exported_body_count": scene_data["expected_exported_body_count"],
        "canonical_coordinates": scene_data["canonical_coordinates"],
        "terminal_metadata": scene_data["terminal_metadata"],
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
    em_policy: Type2ImportEmPolicy = {
        "radiation_margin_mm": spec.simulation.radiation_margin_mm,
    }
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
        _validate_top_level_scene_child(shape)
    scene = bd.Compound(children=scene_shapes, label="type2_scene")
    export_ok = bd.export_step(scene, scene_step_path)
    if export_ok is not True:
        raise RuntimeError(f"build123d export_step returned False for type2 scene STEP: {scene_step_path}")

    ledger = build_type2_step_ledger(
        source_toml_path=spec.source_toml_path,
        output_dir=output_dir,
        scene_step_path=scene_step_path,
        seed=seed,
        em_policy=em_policy,
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

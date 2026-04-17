from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, TypedDict

Point3 = tuple[float, float, float]


class CanonicalCoordinates(TypedDict):
    frame_origin_xyz: Point3
    outer_bounds_min_xyz: Point3
    outer_bounds_max_xyz: Point3
    outer_bounds_size_xyz: Point3


class NonModelSceneMemberLedgerEntry(TypedDict):
    object_id: str
    role: str
    material: str
    model_state: Literal[False]
    canonical_coordinates: CanonicalCoordinates
    plane: Literal["XY", "YZ", "ZX", "mixed"]
    non_model: Literal[True]


class NonModelObjectLedgerEntry(TypedDict):
    object_id: str
    role: str
    material: str
    model_state: Literal[False]
    canonical_coordinates: CanonicalCoordinates
    plane: Literal["XY", "YZ", "ZX", "mixed"]
    non_model: Literal[True]
    member_object_ids: tuple[str, ...]
    member_objects: tuple[NonModelSceneMemberLedgerEntry, ...]


class ModeledObjectSceneData(TypedDict):
    object_id: str
    role: Literal["tx_single_coil", "rx_single_coil"]
    plane: Literal["XY", "YZ"]
    placement_owner_id: str
    material: str
    model_state: Literal[True]
    expected_exported_body_names: tuple[str, ...]
    expected_exported_body_count: int
    canonical_coordinates: dict[str, object]
    terminal_metadata: dict[str, object]


class ModeledObjectLedgerEntry(ModeledObjectSceneData):
    source_metadata_path: str


class Type2StepLedger(TypedDict):
    source_toml_path: str
    output_dir: str
    scene_step_path: str
    seed: int
    non_model_objects: list[NonModelObjectLedgerEntry]
    modeled_objects: list[ModeledObjectLedgerEntry]


class Type2DirectModeledArtifact(ModeledObjectSceneData):
    step_path: str
    source_metadata_path: str


def write_modeled_source_metadata(
    *,
    metadata_path: Path,
    source_toml_path: Path,
    scene_step_path: Path,
    scene_data: ModeledObjectSceneData,
) -> None:
    payload = {
        "source_toml_path": str(source_toml_path),
        "scene_step_path": str(scene_step_path),
        "object_id": scene_data["object_id"],
        "role": scene_data["role"],
        "expected_exported_body_names": scene_data["expected_exported_body_names"],
        "expected_exported_body_count": scene_data["expected_exported_body_count"],
        "canonical_coordinates": scene_data["canonical_coordinates"],
        "terminal_metadata": scene_data["terminal_metadata"],
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_modeled_object_ledger_entry(
    *,
    scene_data: ModeledObjectSceneData,
    source_metadata_path: Path,
) -> ModeledObjectLedgerEntry:
    return {
        "object_id": scene_data["object_id"],
        "role": scene_data["role"],
        "plane": scene_data["plane"],
        "placement_owner_id": scene_data["placement_owner_id"],
        "material": scene_data["material"],
        "model_state": scene_data["model_state"],
        "expected_exported_body_names": scene_data["expected_exported_body_names"],
        "expected_exported_body_count": scene_data["expected_exported_body_count"],
        "canonical_coordinates": scene_data["canonical_coordinates"],
        "terminal_metadata": scene_data["terminal_metadata"],
        "source_metadata_path": str(source_metadata_path),
    }


def build_type2_step_ledger(
    *,
    source_toml_path: str,
    output_dir: Path,
    scene_step_path: Path,
    seed: int,
    non_model_objects: list[NonModelObjectLedgerEntry],
    modeled_objects: list[ModeledObjectLedgerEntry],
) -> Type2StepLedger:
    return {
        "source_toml_path": source_toml_path,
        "output_dir": str(output_dir),
        "scene_step_path": str(scene_step_path),
        "seed": seed,
        "non_model_objects": non_model_objects,
        "modeled_objects": modeled_objects,
    }


def write_type2_step_ledger(*, ledger_path: Path, ledger: Type2StepLedger) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")


__all__ = [
    "CanonicalCoordinates",
    "ModeledObjectLedgerEntry",
    "ModeledObjectSceneData",
    "NonModelObjectLedgerEntry",
    "NonModelSceneMemberLedgerEntry",
    "Point3",
    "Type2DirectModeledArtifact",
    "Type2StepLedger",
    "build_modeled_object_ledger_entry",
    "build_type2_step_ledger",
    "write_modeled_source_metadata",
    "write_type2_step_ledger",
]

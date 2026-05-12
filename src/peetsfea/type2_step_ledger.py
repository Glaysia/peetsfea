from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal, TypedDict

from peetsfea.types.manifest import OutputsSpec

Point3 = tuple[float, float, float]


class Type2ImportEmPolicy(TypedDict):
    radiation_margin_mm: float


class CanonicalCoordinates(TypedDict):
    frame_origin_xyz: Point3
    outer_bounds_min_xyz: Point3
    outer_bounds_max_xyz: Point3
    outer_bounds_size_xyz: Point3


class ExportedBodyGroup(TypedDict):
    group_name: str
    member_body_names: tuple[str, ...]


class ImportedBodyGroup(TypedDict):
    group_name: str
    member_object_names: list[str]


class NonModelSceneMemberLedgerEntry(TypedDict):
    object_id: str
    role: str
    material: str
    model_state: Literal[False]
    canonical_coordinates: CanonicalCoordinates
    plane: Literal["XY", "YZ", "ZX", "mixed"]
    non_model: Literal[True]


class TxInnerRegionReferenceLineProvenance(TypedDict):
    source_region_id: str
    x_ratio_owner_path: str
    y_usage_ratio_owner_path: str
    z_ratio_owner_path: str
    x_ratio: float
    y_usage_ratio: float
    z_ratio: float
    x_ref: float
    z_ref: float
    line_start_xyz: Point3
    line_end_xyz: Point3


class TxOuterRegionPrismProvenance(TypedDict):
    source_region_id: str
    inner_region_id: str
    stack_source_object_id: str
    pcb_thickness_mm: float
    layer_gap_mm: float
    layer_count: int
    height_mm: float
    top_inner_start_xyz: Point3
    top_inner_end_xyz: Point3
    top_outer_start_xyz: Point3
    top_outer_end_xyz: Point3
    bottom_inner_start_xyz: Point3
    bottom_inner_end_xyz: Point3
    bottom_outer_start_xyz: Point3
    bottom_outer_end_xyz: Point3


class TxActualRegionBounds(TypedDict):
    min_xyz: Point3
    max_xyz: Point3
    size_xyz: Point3


class TxActualRegionProvenance(TypedDict):
    source_guide_id: str
    modeled_source_id: str
    x_usage_ratio_owner_path: str
    y_usage_ratio_owner_path: str
    x_usage_ratio: float
    y_usage_ratio: float
    guide_bounds: TxActualRegionBounds
    actual_region_bounds: TxActualRegionBounds
    physical_modeled_body_bounds: TxActualRegionBounds


class TxInnerRegionNonModelSceneMemberLedgerEntry(TypedDict):
    object_id: Literal["tx_inner_region"]
    role: Literal["tx_inner_region"]
    material: str
    model_state: Literal[False]
    canonical_coordinates: CanonicalCoordinates
    plane: Literal["XY", "YZ", "ZX"]
    non_model: Literal[True]
    tx_reference_line: TxInnerRegionReferenceLineProvenance


class TxInnerActualRegionNonModelSceneMemberLedgerEntry(TypedDict):
    object_id: Literal["tx_inner_actual_region"]
    role: Literal["tx_inner_actual_region"]
    material: str
    model_state: Literal[False]
    canonical_coordinates: CanonicalCoordinates
    plane: Literal["XY", "YZ", "ZX"]
    non_model: Literal[True]
    tx_actual_region: TxActualRegionProvenance


class TxOuterRegionNonModelSceneMemberLedgerEntry(TypedDict):
    object_id: Literal["tx_outer_region"]
    role: Literal["tx_outer_region"]
    material: str
    model_state: Literal[False]
    canonical_coordinates: CanonicalCoordinates
    plane: Literal["XY", "YZ", "ZX"]
    non_model: Literal[True]
    tx_outer_region_prism: TxOuterRegionPrismProvenance


class TxOuterActualRegionNonModelSceneMemberLedgerEntry(TypedDict):
    object_id: Literal["tx_outer_actual_region"]
    role: Literal["tx_outer_actual_region"]
    material: str
    model_state: Literal[False]
    canonical_coordinates: CanonicalCoordinates
    plane: Literal["XY", "YZ", "ZX"]
    non_model: Literal[True]
    tx_actual_region: TxActualRegionProvenance


class MateriallessNonModelSceneMemberLedgerEntry(TypedDict):
    object_id: str
    role: str
    model_state: Literal[False]
    canonical_coordinates: CanonicalCoordinates
    plane: Literal["XY", "YZ", "ZX", "mixed"]
    non_model: Literal[True]


NonModelSceneMemberEntry = (
    NonModelSceneMemberLedgerEntry
    | MateriallessNonModelSceneMemberLedgerEntry
    | TxInnerActualRegionNonModelSceneMemberLedgerEntry
    | TxInnerRegionNonModelSceneMemberLedgerEntry
    | TxOuterActualRegionNonModelSceneMemberLedgerEntry
    | TxOuterRegionNonModelSceneMemberLedgerEntry
)


class NonModelObjectLedgerEntry(TypedDict):
    object_id: str
    role: str
    material: str
    model_state: Literal[False]
    canonical_coordinates: CanonicalCoordinates
    plane: Literal["XY", "YZ", "ZX", "mixed"]
    non_model: Literal[True]
    member_object_ids: tuple[str, ...]
    member_objects: tuple[NonModelSceneMemberEntry, ...]


class ModeledObjectSceneData(TypedDict):
    object_id: str
    role: Literal[
        "tx_single_coil",
        "tx_inner_single_coil",
        "tx_outer_single_coil",
        "rx_single_coil",
        "tx_rect_void_columns",
        "tx_plate_stack",
        "rx_plate_stack",
        "tv_aluminum_plate",
    ]
    plane: Literal["XY", "YZ"]
    placement_owner_id: str
    material: str
    model_state: Literal[True]
    expected_exported_body_names: tuple[str, ...]
    expected_exported_body_count: int
    expected_exported_body_groups: tuple[ExportedBodyGroup, ...]
    canonical_coordinates: dict[str, object]
    exported_body_canonical_coordinates: CanonicalCoordinates
    terminal_metadata: dict[str, object]


class ModeledObjectLedgerEntry(ModeledObjectSceneData):
    source_metadata_path: str


class Type2StepLedger(TypedDict):
    schema_version: Literal["type2.step_ledger.v3"]
    source_toml_path: str
    source_toml_sha256: str
    output_dir: str
    scene_step_path: str
    scene_step_sha256: str
    seed: int
    em_policy: Type2ImportEmPolicy
    outputs: OutputsSpec
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
        "expected_exported_body_groups": scene_data["expected_exported_body_groups"],
        "canonical_coordinates": scene_data["canonical_coordinates"],
        "exported_body_canonical_coordinates": scene_data["exported_body_canonical_coordinates"],
        "terminal_metadata": scene_data["terminal_metadata"],
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha256_hex_digest(*, path: Path, context: str) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"{context} does not exist: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        "expected_exported_body_groups": scene_data["expected_exported_body_groups"],
        "canonical_coordinates": scene_data["canonical_coordinates"],
        "exported_body_canonical_coordinates": scene_data["exported_body_canonical_coordinates"],
        "terminal_metadata": scene_data["terminal_metadata"],
        "source_metadata_path": str(source_metadata_path),
    }


def build_type2_step_ledger(
    *,
    source_toml_path: str,
    output_dir: Path,
    scene_step_path: Path,
    seed: int,
    em_policy: Type2ImportEmPolicy,
    outputs: OutputsSpec,
    non_model_objects: list[NonModelObjectLedgerEntry],
    modeled_objects: list[ModeledObjectLedgerEntry],
) -> Type2StepLedger:
    source_toml = Path(source_toml_path)
    scene_step = Path(scene_step_path)
    source_toml_sha256 = _sha256_hex_digest(path=source_toml, context="source_toml_path")
    scene_step_sha256 = _sha256_hex_digest(path=scene_step, context="scene_step_path")
    return {
        "schema_version": "type2.step_ledger.v3",
        "source_toml_path": source_toml_path,
        "source_toml_sha256": source_toml_sha256,
        "output_dir": str(output_dir),
        "scene_step_path": str(scene_step_path),
        "scene_step_sha256": scene_step_sha256,
        "seed": seed,
        "em_policy": em_policy,
        "outputs": outputs,
        "non_model_objects": non_model_objects,
        "modeled_objects": modeled_objects,
    }


def write_type2_step_ledger(*, ledger_path: Path, ledger: Type2StepLedger) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")


__all__ = [
    "CanonicalCoordinates",
    "ExportedBodyGroup",
    "ImportedBodyGroup",
    "MateriallessNonModelSceneMemberLedgerEntry",
    "ModeledObjectLedgerEntry",
    "ModeledObjectSceneData",
    "NonModelObjectLedgerEntry",
    "NonModelSceneMemberEntry",
    "NonModelSceneMemberLedgerEntry",
    "Point3",
    "Type2ImportEmPolicy",
    "Type2DirectModeledArtifact",
    "Type2StepLedger",
    "TxActualRegionBounds",
    "TxActualRegionProvenance",
    "TxInnerActualRegionNonModelSceneMemberLedgerEntry",
    "TxInnerRegionNonModelSceneMemberLedgerEntry",
    "TxInnerRegionReferenceLineProvenance",
    "TxOuterActualRegionNonModelSceneMemberLedgerEntry",
    "TxOuterRegionNonModelSceneMemberLedgerEntry",
    "TxOuterRegionPrismProvenance",
    "build_modeled_object_ledger_entry",
    "build_type2_step_ledger",
    "write_modeled_source_metadata",
    "write_type2_step_ledger",
]

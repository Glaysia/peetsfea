from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

from .em import (
    EmContext,
    EmEndpoints,
    EmPipelineResult,
    EmPolicy,
    EmPortAssignments,
    EmPorts,
    EmReadyObjects,
    OutputsSpec,
)
from .geometry import CoilPolaritySpec, GeometryDebug, GroupEndpointEntry, GroupObjects, SceneObjectEntry, UniteGroups
from .runtime_selection import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance, SelectedParameters, SelectedParametersMax


class ManifestInputs(TypedDict):
    ansys_executable_path: str
    ansys_run_dir: str
    toml_path: str
    source_toml_path: NotRequired[str]
    non_graphical: bool
    close_on_exit: bool
    emit_manifest_json: bool
    emit_geometry_metadata_json: bool


class ManifestSpec(TypedDict):
    spec_version: str
    design_name: str
    units: str
    simulation: EmPolicy
    outputs: OutputsSpec


class Manifest(TypedDict):
    design_id: str
    design_unique_hash: str
    toml_space_hash: str
    toml_hash: str
    peetsfea_commit: str
    seed: int
    retry_attempt: int
    retry_count: int
    repro_mode: Literal["sampled_toml", "frozen_toml", "manifest_json"]
    backend: str
    selected_parameters: SelectedParameters
    selected_parameters_max: SelectedParametersMax
    selected_coil_groups: list[ResolvedCoilGroup]
    selected_group_geometry: list[GroupGeometryParams]
    selected_pcbs: list[ResolvedPcbInstance]
    inputs: ManifestInputs
    spec: ManifestSpec
    created_at_utc: str
    manifest_path: str | None


class ReproSnapshot(TypedDict):
    toml_bytes: bytes


class DatasetSnapshot(TypedDict):
    toml_bytes: bytes


class RunResult(TypedDict):
    manifest: Manifest
    source_toml_bytes: bytes
    repro_snapshot: ReproSnapshot
    dataset_snapshot: DatasetSnapshot
    manifest_path: str | None
    geometry_metadata_path: str | None
    zip_path: str | None


class GeometryMetadata(TypedDict):
    design_id: str
    design_unique_hash: str
    toml_space_hash: str
    toml_hash: str
    peetsfea_commit: str
    seed: int
    retry_attempt: int
    retry_count: int
    repro_mode: Literal["sampled_toml", "frozen_toml", "manifest_json"]
    selected_parameters: SelectedParameters
    selected_parameters_max: SelectedParametersMax
    selected_group_geometry: list[GroupGeometryParams]
    aedt_path: str
    object_names: list[str]
    created_at_utc: str
    metadata_path: str
    anchor_mode: Literal["copper_outer_edge_corner"]
    group_objects: GroupObjects
    unite_groups: UniteGroups
    group_endpoints: list[GroupEndpointEntry]
    coil_polarity: list[CoilPolaritySpec]
    em_ready_objects: EmReadyObjects
    em_endpoints: EmEndpoints
    em_ports: EmPorts
    em_port_assignments: EmPortAssignments
    em_context: EmContext
    em_policy: EmPolicy
    em_pipeline_result: EmPipelineResult
    scene_objects: list[SceneObjectEntry]
    tx_dd_rotation_angle_deg: float
    tx_dd_rotation_pivot_xyz: tuple[float, float, float]
    tx_dd_rotation_object_names: list[str]
    debug: GeometryDebug

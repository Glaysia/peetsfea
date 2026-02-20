from __future__ import annotations

from typing import NotRequired, TypedDict


class ManifestInputs(TypedDict):
    ansys_executable_path: str
    ansys_run_dir: str
    toml_path: str
    non_graphical: bool
    close_on_exit: bool


class ManifestSpec(TypedDict):
    spec_version: str
    design_name: str
    units: str


class SelectedParameters(TypedDict):
    turns: int
    outer: float
    trace: float
    gap: float
    thickness: float


class Manifest(TypedDict):
    design_id: str
    toml_hash: str
    peetsfea_commit: str
    seed: int
    backend: str
    selected_parameters: SelectedParameters
    inputs: ManifestInputs
    spec: ManifestSpec
    created_at_utc: str
    manifest_path: NotRequired[str]


class GeometryMetadata(TypedDict):
    design_id: str
    toml_hash: str
    peetsfea_commit: str
    seed: int
    selected_parameters: SelectedParameters
    aedt_path: str
    object_names: list[str]
    created_at_utc: str
    metadata_path: NotRequired[str]

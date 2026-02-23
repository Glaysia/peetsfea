from __future__ import annotations

from typing import Literal, TypedDict


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
    pcb_count: int
    turns: int
    outer: float
    trace: float
    gap: float
    via_diameter: float
    pcb_thickness: float
    cu_thickness: float
    fr4_er: float


class Manifest(TypedDict):
    design_id: str
    design_unique_hash: str
    toml_space_hash: str
    toml_hash: str
    peetsfea_commit: str
    seed: int
    backend: str
    selected_parameters: SelectedParameters
    inputs: ManifestInputs
    spec: ManifestSpec
    created_at_utc: str
    manifest_path: str


class AxisCheckEntry(TypedDict):
    segment_index: int
    start_xy: tuple[float, float]
    end_xy: tuple[float, float]
    is_vertical: bool
    is_horizontal: bool
    x_constant: float | None
    y_constant: float | None


class CornerDebugEntry(TypedDict):
    vertex_index: int
    xy: tuple[float, float]
    corner_type: Literal["left_turn", "right_turn", "collinear", "endpoint"]
    incoming_dir: tuple[float, float] | None
    outgoing_dir: tuple[float, float] | None
    offset_applied: tuple[float, float] | None


class PitchCheckEntry(TypedDict):
    turn_index: int
    pitch_expected: float
    pitch_measured: float
    delta: float


class CadProbe(TypedDict):
    object_name: str
    bbox: list[float]
    edge_samples_xy: list[tuple[float, float]]


class GeometryDebug(TypedDict):
    centerline_vertices: list[tuple[float, float, float]]
    corner_debug: list[CornerDebugEntry]
    axis_checks: list[AxisCheckEntry]
    pitch_checks: list[PitchCheckEntry]
    cad_probe: list[CadProbe]
    constraints_ok: bool
    eps: float


class GeometryMetadata(TypedDict):
    design_id: str
    design_unique_hash: str
    toml_space_hash: str
    toml_hash: str
    peetsfea_commit: str
    seed: int
    selected_parameters: SelectedParameters
    aedt_path: str
    object_names: list[str]
    created_at_utc: str
    metadata_path: str
    anchor_mode: Literal["copper_outer_edge_corner"]
    debug: GeometryDebug

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

Plane = Literal["XY", "YZ", "ZX"]


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


class SelectedParameters(TypedDict):
    tx_dd_outer_x: float
    tx_dd_outer_y: float
    tx_vertical_outer_x: float
    tx_vertical_outer_y: float
    rx_dd_outer_x: float
    rx_dd_outer_y: float
    inner_margin_x: float
    inner_margin_y: float
    tx_dd_pair_spacing_ratio: float
    rx_dd_pair_spacing_ratio: float
    tx_vertical_center_gap_mm: float
    # Derived from tx_vertical_center_gap_mm * max(0, tx_vertical selected_count - 1).
    tx_dd_pair_spacing_mm: float
    rx_dd_pair_spacing_mm: float
    tx_vertical_span_mm: float
    tv_width_mm: float
    tv_height_mm: float
    tv_thickness_mm: float
    tv_base_z_mm: float
    tx_region_outer_w_mm: float
    tx_region_outer_h_mm: float
    tx_region_thickness_mm: float
    tx_region_vertical_z_mm: float
    tx_region_dd_z_mm: float
    rx_region_outer_w_mm: float
    rx_region_outer_h_mm: float
    rx_region_thickness_mm: float
    wall_thickness_mm: float
    wall_size_y_mm: float
    wall_size_z_mm: float
    floor_thickness_mm: float
    floor_size_x_mm: float
    floor_size_y_mm: float
    ferrite_present: bool
    rx_ferrite_thickness_mm: float
    tx_ferrite_thickness_mm: float
    tx_ferrite_gap_mm: float
    ferrite_relative_permeability: float
    shelf_height_mm: float
    shelf_min_size_x_mm: float
    rx_region_bottom_from_tv_mm: float
    tx_dd_top_clearance_ratio: float
    # Derived from tx_dd_top_clearance_ratio * tx_region_dd_z_mm.
    tx_dd_top_clearance_mm: float
    rx_face_clearance_mm: float
    tx_main_1_z_from_tx_main_0_mm: float
    dd_mirror_plane: Literal["XZ"]
    rx_plane: Literal["YZ"]
    tx_vertical_plane: Literal["ZX"]
    via_diameter_mm: float
    pcb_thickness_mm: float
    cu_thickness_mm: float
    via_diameter: float
    pcb_thickness: float
    cu_thickness: float
    fr4_er: float


class SelectedParametersMax(TypedDict):
    tx_region_outer_w_mm: float
    tx_region_outer_h_mm: float
    tx_region_thickness_mm: float
    tx_region_vertical_z_mm: float
    tx_region_dd_z_mm: float
    rx_region_outer_w_mm: float
    rx_region_outer_h_mm: float
    rx_region_thickness_mm: float


class ResolvedCoilGroup(TypedDict):
    kind: Literal["tx_dd", "tx_vertical", "rx_dd"]
    requested_count: int
    selected_count: int
    spacing_mm: float
    instance_transforms: list[dict[str, float]]


class GroupGeometryParams(TypedDict):
    kind: Literal["tx_dd", "tx_vertical", "rx_dd"]
    turn_count_max: int
    band_ratio: float
    metal_ratio: float
    trace: float
    gap: float


class ResolvedPcbMount(TypedDict):
    kind: Literal["tx_dd", "tx_vertical", "rx_dd"]
    selector_mode: Literal["all", "index"]
    selector_index: int | None


class ResolvedPcbInstance(TypedDict):
    id: str
    role: Literal["tx", "rx"]
    position: tuple[float, float, float]
    rotation_deg: float
    present: bool
    z_mode: Literal["absolute", "relative_to_pcb"]
    z_relative_base_id: str | None
    z_delta_path: str | None
    mounts: list[ResolvedPcbMount]


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


class RegionViolation(TypedDict):
    object_name: str
    region_kind: Literal["tx_region_dd", "tx_region_vertical", "rx_region_actual"]
    axis: Literal["x", "y", "z"]
    overflow_mm: float
    actual_min: float
    actual_max: float
    region_min: float
    region_max: float


class GeometryDebug(TypedDict):
    centerline_vertices: list[tuple[float, float, float]]
    corner_debug: list[CornerDebugEntry]
    axis_checks: list[AxisCheckEntry]
    pitch_checks: list[PitchCheckEntry]
    cad_probe: list[CadProbe]
    constraints_ok: bool
    in_region_ok: bool
    violations: list[RegionViolation]
    eps: float


class GroupObjects(TypedDict):
    tx_dd: list[str]
    tx_vertical: list[str]
    rx_dd: list[str]
    ferrite: list[str]


class UniteGroups(TypedDict):
    tx: list[str]
    rx: list[str]
    ferrite: list[str]


TerminalLabel = Literal["A", "B", "C", "D", "a", "b", "c", "d"]


class GroupEndpointEntry(TypedDict):
    group_kind: Literal["tx_dd", "tx_vertical", "rx_dd"]
    group_instance_index: int
    board_id: str
    start_xyz: tuple[float, float, float]
    end_xyz: tuple[float, float, float]
    start_label: TerminalLabel
    end_label: TerminalLabel
    present: bool


class CoilPolaritySpec(TypedDict):
    group_kind: Literal["tx_dd", "tx_vertical", "rx_dd"]
    group_instance_index: int
    board_id: str
    instance_side: Literal["left", "right", "center"]
    current_direction: Literal["cw", "ccw"]
    b_field_direction: Literal["up", "down", "left", "right", "into_wall", "out_of_wall"]


class SceneObjectEntry(TypedDict):
    name: str
    kind: Literal[
        "tv",
        "wall",
        "floor",
        "shelf",
        "tx_region_max",
        "tx_region_vertical",
        "tx_region_dd",
        "rx_region_max",
        "rx_region_actual",
        "rx_ferrite",
        "tx_ferrite",
    ]
    present: bool
    origin_xyz: tuple[float, float, float]
    size_xyz: tuple[float, float, float]
    plane: Literal["XY", "YZ"]
    non_model: bool


class EmReadyObjects(TypedDict):
    tx_conductors: list[str]
    rx_conductors: list[str]
    ferrite_objects: list[str]
    fr4_objects: list[str]
    scene_bbox_source_objects: list[str]


class EmEndpoints(TypedDict):
    tx: list[GroupEndpointEntry]
    rx: list[GroupEndpointEntry]


class EmContext(TypedDict):
    dd_mirror_plane: str
    rx_plane: str
    tx_vertical_plane: str
    source: str
    object_names: list[str]


class EmPolicy(TypedDict):
    radiation_margin_mm: float
    setup_frequency_hz: float
    sweep_start_hz: float
    sweep_stop_hz: float
    validation_gate: str
    max_delta_s: float
    maximum_passes: int
    minimum_passes: int
    minimum_converged_passes: int
    percent_refinement: int
    basis_order: int
    port_accuracy: int


class OutputVariableSpec(TypedDict):
    name: str
    expression: str


class OutputsSpec(TypedDict):
    report_name: str
    solution_name: str
    primary_sweep: str
    report_category: str
    plot_type: str
    variables: list[OutputVariableSpec]


class PostTemplateResult(TypedDict):
    template_id: str
    report_name: str
    solution_name: str
    traces: list[str]
    output_variables: list[str]


class EmPipelineResult(TypedDict):
    groups: dict[str, list[str]]
    series: dict[str, list[str]]
    subtract: dict[str, list[str]]
    boundary: dict[str, str]
    ports: dict[str, list[str]]
    sources: dict[str, str]
    analysis: dict[str, float | str]
    post_templates: list[PostTemplateResult]
    validation_report: dict[str, str | bool]


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
    em_context: EmContext
    em_policy: EmPolicy
    em_pipeline_result: EmPipelineResult
    scene_objects: list[SceneObjectEntry]
    debug: GeometryDebug

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
    outer_x: float
    outer_y: float
    turn_count_max: int
    inner_margin_x: float
    inner_margin_y: float
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
    shelf_height_mm: float
    shelf_min_size_x_mm: float
    rx_region_bottom_from_tv_mm: float
    tx_dd_top_clearance_mm: float
    rx_face_clearance_mm: float
    dd_mirror_plane: Literal["XZ"]
    rx_plane: Literal["YZ"]
    tx_vertical_plane: Literal["ZX"]
    profile_id: str
    trace_profile_base: float
    trace_profile_outer_bias: float
    trace_profile_inner_bias: float
    trace_profile_clamp_min: float
    gap_profile_base: float
    gap_profile_outer_bias: float
    gap_profile_inner_bias: float
    gap_profile_clamp_min: float
    # Compatibility fields used by current square-spiral MVP geometry path.
    turns: int
    outer: float
    trace: float
    gap: float
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


class ResolvedPcbInstance(TypedDict):
    id: str
    role: Literal["tx", "rx"]
    position: tuple[float, float, float]
    rotation_deg: float
    present: bool
    mounts: list[str]


class Manifest(TypedDict):
    design_id: str
    design_unique_hash: str
    toml_space_hash: str
    toml_hash: str
    peetsfea_commit: str
    seed: int
    backend: str
    selected_parameters: SelectedParameters
    selected_parameters_max: SelectedParametersMax
    selected_coil_groups: list[ResolvedCoilGroup]
    selected_pcbs: list[ResolvedPcbInstance]
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


class UniteGroups(TypedDict):
    tx: list[str]
    rx: list[str]


class GroupEndpointEntry(TypedDict):
    group_kind: Literal["tx_dd", "tx_vertical", "rx_dd"]
    group_instance_index: int
    board_id: str
    start_xyz: tuple[float, float, float]
    end_xyz: tuple[float, float, float]
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
    ]
    present: bool
    origin_xyz: tuple[float, float, float]
    size_xyz: tuple[float, float, float]
    plane: Literal["XY", "YZ"]
    non_model: bool


class GeometryMetadata(TypedDict):
    design_id: str
    design_unique_hash: str
    toml_space_hash: str
    toml_hash: str
    peetsfea_commit: str
    seed: int
    selected_parameters: SelectedParameters
    selected_parameters_max: SelectedParametersMax
    aedt_path: str
    object_names: list[str]
    created_at_utc: str
    metadata_path: str
    anchor_mode: Literal["copper_outer_edge_corner"]
    group_objects: GroupObjects
    unite_groups: UniteGroups
    group_endpoints: list[GroupEndpointEntry]
    coil_polarity: list[CoilPolaritySpec]
    scene_objects: list[SceneObjectEntry]
    debug: GeometryDebug

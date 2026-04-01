from __future__ import annotations

from typing import Literal, TypeAlias, TypedDict


NeoTxDdTerminalPath: TypeAlias = str
NeoTxVerticalTerminalPath: TypeAlias = str


class SelectedParameters(TypedDict):
    tx_dd_outer_x: float
    tx_dd_outer_y: float
    tx_vertical_outer_x: float
    tx_vertical_outer_y: float
    rx_dd_outer_x: float
    rx_dd_outer_y: float
    corner_mode: int
    tx_dd_pair_spacing_ratio: float
    rx_dd_pair_spacing_ratio: float
    tx_vertical_center_gap_mm: float
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
    tx_dd_top_offset_ratio: float
    tx_dd_top_clearance_mm: float
    tx_vertical_orientation_mode: Literal[0, 1]
    rx_face_clearance_mm: float
    tx_main_1_z_from_tx_main_0_mm: float
    dd_mirror_plane: Literal["XZ"]
    rx_plane: Literal["YZ"]
    neo_tx_dd_right_terminal_path: NeoTxDdTerminalPath
    neo_tx_dd_left_terminal_path: NeoTxDdTerminalPath
    neo_tx_vertical_zx_terminal_path: NeoTxVerticalTerminalPath
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


class ResolvedTxDdGroup(TypedDict):
    kind: Literal["tx_dd"]
    layer_count: Literal[1, 2]
    spacing_mm: float
    instance_transforms: list[dict[str, float]]


class ResolvedTxVerticalGroup(TypedDict):
    kind: Literal["tx_vertical"]
    requested_count: int
    selected_count: int
    layer_count: Literal[1]
    spacing_mm: float
    instance_transforms: list[dict[str, float]]


class ResolvedRxDdGroup(TypedDict):
    kind: Literal["rx_dd"]
    requested_count: Literal[2]
    selected_count: Literal[2]
    layer_count: Literal[1]
    spacing_mm: float
    instance_transforms: list[dict[str, float]]


ResolvedCoilGroup: TypeAlias = ResolvedTxDdGroup | ResolvedTxVerticalGroup | ResolvedRxDdGroup


def coil_group_layer_count(group: ResolvedCoilGroup) -> int:
    return int(group["layer_count"])


def coil_group_selected_count(group: ResolvedCoilGroup) -> int:
    if group["kind"] == "tx_dd":
        return 2 if int(group["layer_count"]) == 1 else 4
    return int(group["selected_count"])


def coil_group_requested_count(group: ResolvedCoilGroup) -> int:
    if group["kind"] == "tx_dd":
        return coil_group_selected_count(group)
    return int(group["requested_count"])


class GroupGeometryParams(TypedDict):
    kind: Literal["tx_dd", "tx_vertical", "rx_dd"]
    turn_count: int
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


TerminalLabel = Literal["A", "B", "C", "D", "a", "b", "c", "d"]

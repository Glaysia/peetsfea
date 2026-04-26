from __future__ import annotations

from typing import Literal, TypedDict

from .runtime_selection import TerminalLabel

Plane = Literal["XY", "YZ", "ZX"]


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


class GroupEndpointEntry(TypedDict):
    group_kind: Literal["tx_dd", "tx_vertical", "rx_dd", "tx_plate_stack", "rx_plate_stack", "tx_rect_void_columns"]
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
    dd_family: Literal["none", "tx_dd", "rx_dd"]
    dd_pair_index: int | None
    instance_side: Literal["left", "right", "center"]
    current_direction: Literal["cw", "ccw"]


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

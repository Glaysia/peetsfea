from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast

from peetsfea.types.manifest import (
    CadProbe,
    CoilPolaritySpec,
    GroupEndpointEntry,
    GroupGeometryParams,
    GroupObjects,
    Manifest,
    Plane,
    RegionViolation,
    ResolvedCoilGroup,
    ResolvedPcbInstance,
    SceneObjectEntry,
    SelectedParameters,
    SelectedParametersMax,
)


Point3 = tuple[float, float, float]
Edge2P = tuple[Point3, Point3]
BoardKey = tuple[str, int]
TxVerticalLinkNode = tuple[int, str, Point3, Point3, float, float, Edge2P, Edge2P]
TxDdStartStubSource = tuple[Point3, float, str]
RxDdBackStubSource = tuple[str, int, str, Point3, float, str]


def _empty_group_objects() -> GroupObjects:
    return cast(GroupObjects, {"tx_dd": [], "tx_vertical": [], "rx_dd": [], "ferrite": []})


@dataclass
class GeometryBuildState:
    object_names: list[str] = field(default_factory=list)
    cad_probe: list[CadProbe] = field(default_factory=list)
    group_objects: GroupObjects = field(default_factory=_empty_group_objects)
    group_endpoints: list[GroupEndpointEntry] = field(default_factory=list)
    coil_polarity: list[CoilPolaritySpec] = field(default_factory=list)
    placement_violations: list[RegionViolation] = field(default_factory=list)
    coil_plane_bboxes: list[tuple[str, Plane, list[float]]] = field(default_factory=list)
    fr4_object_names: list[str] = field(default_factory=list)
    tx_zx_fr4_names: list[str] = field(default_factory=list)
    scene_objects: list[SceneObjectEntry] = field(default_factory=list)


@dataclass
class FinalizeInputs:
    txdd_right_a_points: dict[int, tuple[Point3, float]] = field(default_factory=dict)
    txdd_right_object_names: dict[int, str] = field(default_factory=dict)
    txdd_left_a_points: dict[int, tuple[Point3, float]] = field(default_factory=dict)
    txdd_left_object_names: dict[int, str] = field(default_factory=dict)
    txdd_start_stub_sources: dict[str, list[TxDdStartStubSource]] = field(default_factory=dict)
    rxdd_back_stub_sources: list[RxDdBackStubSource] = field(default_factory=list)
    tx_vertical_nodes_by_board: dict[BoardKey, list[TxVerticalLinkNode]] = field(default_factory=dict)
    txdd_global_right_d_edge: Edge2P | None = None
    txdd_global_right_d_object_name: str | None = None
    txdd_global_right_d_selection_key: tuple[float, str, int] | None = None
    txdd_global_left_a_edge: Edge2P | None = None
    txdd_global_left_a_object_name: str | None = None
    tx_vertical_global_outer_right_edge: Edge2P | None = None
    tx_vertical_global_outer_left_edge: Edge2P | None = None
    tx_vertical_outer_right_selection_key: tuple[float, str, int] | None = None
    tx_vertical_outer_left_selection_key: tuple[float, str, int] | None = None


@dataclass
class GeometryRuntimeContext:
    manifest: Manifest
    selected: SelectedParameters
    selected_max: SelectedParametersMax
    selected_groups: list[ResolvedCoilGroup]
    selected_group_geometry: list[GroupGeometryParams]
    selected_pcbs: list[ResolvedPcbInstance]
    group_geometry_by_kind: dict[Literal["tx_dd", "tx_vertical", "rx_dd"], GroupGeometryParams]
    tx_board_ids: set[str]
    design_id: str
    aedt_path: Path
    metadata_path: Path
    close_on_exit: bool
    tx_dd_outer_x: float
    tx_dd_outer_y: float
    tx_vertical_outer_x: float
    tx_vertical_outer_y: float
    rx_dd_outer_x: float
    rx_dd_outer_y: float
    pcb_thickness: float
    cu_thickness: float
    tx_dd_top_clearance: float
    rx_face_clearance: float
    tx_vertical_plane: Literal["ZX"]
    tx_dd_region_min: Point3 | None = None
    tx_dd_region_max: Point3 | None = None
    tx_vertical_region_min: Point3 | None = None
    tx_vertical_region_max: Point3 | None = None
    rx_region_min: Point3 | None = None
    rx_region_max: Point3 | None = None
    tx_dd_center_x: float | None = None
    tx_dd_center_y: float | None = None
    tx_vertical_center_x: float | None = None
    tx_vertical_center_y: float | None = None
    rx_center_y: float | None = None

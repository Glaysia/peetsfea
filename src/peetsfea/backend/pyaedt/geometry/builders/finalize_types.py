from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from peetsfea.aedt import Hfss, Modeler3D
from peetsfea.types.manifest import (
    CadProbe,
    CoilPolaritySpec,
    EmPortAssignments,
    EmPorts,
    GroupObjects,
    RegionViolation,
)

from ..build_state import (
    BoardKey,
    BridgeAnchor,
    DdHalfGeometryCapture,
    DirectedLandingSection,
    Edge2P,
    OrderedTerminalSection,
    Point3,
    RxDdBackStubSource,
    TxDdStartStubSource,
    TxSeriesBindingInputs,
    TxVerticalLinkNode,
)


@dataclass
class FinalizePlan:
    modeler: Modeler3D
    hfss: Hfss
    aedt_path: Path
    design_id: str
    cu_thickness: float
    pcb_thickness: float
    via_diameter_mm: float
    tx_vertical_orientation_mode: Literal[0, 1]
    tx_board_ids: set[str]
    tx_dd_region_min: Point3
    tx_dd_region_max: Point3
    tx_dd_center_y: float
    tx_vertical_nodes_by_board: dict[BoardKey, list[TxVerticalLinkNode]]
    tx_vertical_region_min: Point3
    tx_vertical_region_max: Point3
    txdd_right_a_points: dict[int, tuple[Point3, float]]
    txdd_right_object_names: dict[int, str]
    txdd_start_stub_sources: dict[str, list[TxDdStartStubSource]]
    rxdd_back_stub_sources: list[RxDdBackStubSource]
    group_objects: GroupObjects
    object_names: list[str]
    cad_probe: list[CadProbe]
    placement_violations: list[RegionViolation]
    coil_plane_bboxes: list[tuple[str, Literal["XY", "YZ", "ZX"], list[float]]]
    fr4_object_names: list[str]
    tx_vertical_fr4_names: list[str]
    coil_polarity: list[CoilPolaritySpec]
    dd_half_geometries: list[DdHalfGeometryCapture]
    tx_dd_rotation_angle_deg: float
    tx_dd_rotation_pivot_xyz: Point3
    tx_dd_rotation_object_names: list[str]
    txdd_global_right_bridge_landing: DirectedLandingSection
    txdd_global_right_bridge_edge: Edge2P
    txdd_global_right_bridge_section: OrderedTerminalSection
    txdd_global_right_bridge_object_name: str
    txdd_global_right_d_edge: Edge2P
    txdd_global_right_d_object_name: str
    tx_vertical_global_outer_right_edge: Edge2P
    tx_vertical_global_outer_left_edge: Edge2P
    tx_vertical_global_outer_right_landing: DirectedLandingSection
    tx_vertical_global_outer_left_landing: DirectedLandingSection
    tx_vertical_global_outer_right_section: OrderedTerminalSection
    tx_vertical_global_outer_left_section: OrderedTerminalSection
    txdd_global_right_bridge_anchor: BridgeAnchor
    tx_vertical_global_outer_right_anchor: BridgeAnchor
    tx_vertical_global_outer_left_anchor: BridgeAnchor
    tx_series_binding: TxSeriesBindingInputs


@dataclass(frozen=True)
class FinalizeArtifacts:
    object_names: list[str]
    fr4_object_names: list[str]
    resolved_ports: EmPorts
    resolved_port_assignments: EmPortAssignments
    tx_dd_rotation_angle_deg: float
    tx_dd_rotation_pivot_xyz: Point3
    tx_dd_rotation_object_names: list[str]

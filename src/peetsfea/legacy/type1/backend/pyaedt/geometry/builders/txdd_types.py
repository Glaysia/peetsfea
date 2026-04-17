from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from peetsfea.aedt import Modeler3D
from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance, TerminalLabel

from ..build_state import Edge2P, FinalizeInputs, GeometryBuildState, GeometryRuntimeContext, Point3
from ..rules.placement_types import _TxDdRightLocalTopology


@dataclass(frozen=True)
class TxDdBuildRequest:
    modeler: Modeler3D
    ctx: GeometryRuntimeContext
    state: GeometryBuildState
    finalize_inputs: FinalizeInputs
    board_idx: int
    pcb: ResolvedPcbInstance
    group: ResolvedCoilGroup
    geometry: GroupGeometryParams
    edge_points_at_path_end: Callable[..., Edge2P]
    half_topology: Callable[..., _TxDdRightLocalTopology]


@dataclass(frozen=True)
class TxDdSlot:
    layer_index: int
    right_index: int


@dataclass(frozen=True)
class TxDdHalfRealization:
    side: Literal["left", "right"]
    layer_index: int
    instance_index: int
    center_x: float
    center_y: float
    world_points: list[list[float]]
    bridge_edge_world: Edge2P
    a_point_world: Point3
    main_start_edge: Edge2P
    main_end_edge: Edge2P
    instance_side: Literal["left", "right", "center"]
    start_label: TerminalLabel
    end_label: TerminalLabel
    current_direction: Literal["cw", "ccw"]


@dataclass(frozen=True)
class TxDdRealization:
    slot: TxDdSlot
    instance_count: int
    trace: float
    right: TxDdHalfRealization

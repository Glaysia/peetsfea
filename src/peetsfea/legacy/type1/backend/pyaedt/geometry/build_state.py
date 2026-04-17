from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypedDict, TypeVar, cast

from peetsfea.types.manifest import (
    CadProbe,
    CoilPolaritySpec,
    EmPortAssignments,
    EmPorts,
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
TxVerticalLinkNode = tuple[int, str, Point3, Point3, float, float, float, Edge2P, Edge2P]
BackConnectStubSource = tuple[str, int, str, Point3, float, str]
BackConnectStubSourceWithInwardDir = tuple[str, int, str, Point3, float, str, Point3]
TxDdStartStubSource = tuple[Point3, float, str] | tuple[Point3, float, str, Point3]
RxDdBackStubSource = BackConnectStubSource | BackConnectStubSourceWithInwardDir
TxSeriesFieldName = Literal[
    "feed_in",
    "feed_out",
    "inter_half_exit",
    "inter_half_entry",
    "series_entry",
    "series_exit",
]
NO_DD_PAIR_INDEX = -1
_STATE_UNSET = object()
_SCENE_UNSET = object()
_T = TypeVar("_T")


class OrderedTerminalSection(TypedDict):
    p0: Point3
    p1: Point3
    center: Point3
    tangent_out: Point3
    plane_normal: Point3


class BridgeAnchor(TypedDict):
    center: Point3
    trace: float
    plane_normal: Point3
    object_name: str
    dd_family: Literal["none", "tx_dd", "rx_dd"]
    dd_pair_index: int
    side: Literal["left", "right", "center"]


StubFaceKind = Literal["tx_dd_xy", "tx_vertical_xz"]
StubFaceEdgeRole = Literal["tx_port", "tx_dd_bridge", "tx_vertical_bridge"]


class StubFaceSignature(TypedDict):
    ordered_vertices: tuple[Point3, ...]
    center: Point3
    area: float
    face_kind: StubFaceKind


class StubFaceRef(TypedDict):
    object_name: str
    face_id: int
    face_kind: StubFaceKind
    stub_role: str
    signature: StubFaceSignature


class _DirectedLandingSectionRequired(TypedDict):
    p_plus: Point3
    p_minus: Point3
    center: Point3
    outward_dir: Point3
    plane_normal: Point3
    object_name: str
    dd_family: Literal["none", "tx_dd", "rx_dd"]
    dd_pair_index: int
    side: Literal["left", "right", "center"]
    terminal_polarity: Literal["positive", "negative", "neutral"]
    terminal_role: Literal[
        "none",
        "feed_in",
        "feed_out",
        "inter_half_entry",
        "inter_half_exit",
        "series_entry",
        "series_exit",
    ]


class DirectedLandingSection(_DirectedLandingSectionRequired, total=False):
    inward_dir: Point3
    bridge_stub_edge: Edge2P
    stub_face_ref: StubFaceRef


class TxSeriesChainBinding(TypedDict):
    feed_in: DirectedLandingSection
    feed_out: DirectedLandingSection
    inter_half_exit: DirectedLandingSection
    inter_half_entry: DirectedLandingSection
    series_entry: DirectedLandingSection
    series_exit: DirectedLandingSection


@dataclass
class TxSeriesBindingInputs:
    feed_in: DirectedLandingSection = field(default_factory=lambda: cast(DirectedLandingSection, _STATE_UNSET))
    feed_out: DirectedLandingSection = field(default_factory=lambda: cast(DirectedLandingSection, _STATE_UNSET))
    inter_half_exit: DirectedLandingSection = field(default_factory=lambda: cast(DirectedLandingSection, _STATE_UNSET))
    inter_half_entry: DirectedLandingSection = field(default_factory=lambda: cast(DirectedLandingSection, _STATE_UNSET))
    series_entry: DirectedLandingSection = field(default_factory=lambda: cast(DirectedLandingSection, _STATE_UNSET))
    series_exit: DirectedLandingSection = field(default_factory=lambda: cast(DirectedLandingSection, _STATE_UNSET))

    def has(self, field_name: TxSeriesFieldName) -> bool:
        return state_is_set(getattr(self, field_name))

    def require(self, field_name: TxSeriesFieldName) -> DirectedLandingSection:
        return require_state(cast(DirectedLandingSection, getattr(self, field_name)), name=f"tx_series_binding.{field_name}")

    def set_once(self, field_name: TxSeriesFieldName, landing: DirectedLandingSection, *, context: str) -> None:
        existing = cast(DirectedLandingSection, getattr(self, field_name))
        if state_is_set(existing) and existing != landing:
            raise ValueError(
                f"{context} contract violation: duplicate {field_name} capture "
                f"(existing_object={existing['object_name']}, new_object={landing['object_name']})"
            )
        setattr(self, field_name, landing)


class DdHalfGeometryCapture(TypedDict):
    dd_family: Literal["tx_dd", "rx_dd"]
    dd_pair_index: int
    instance_side: Literal["left", "right"]
    centerline_points: list[Point3]
    start_anchor: Point3
    end_anchor: Point3
    landing_edge: Edge2P


class TxDdSceneRegistry(TypedDict):
    region_min: Point3
    region_max: Point3
    center_x: float
    center_y: float


class TxVerticalSceneRegistry(TypedDict):
    region_min: Point3
    region_max: Point3
    center_x: float
    center_y: float


class RxSceneRegistry(TypedDict):
    region_min: Point3
    region_max: Point3
    center_y: float


class GeometrySceneRegistry(TypedDict):
    tx_dd: TxDdSceneRegistry
    tx_vertical: TxVerticalSceneRegistry
    rx: RxSceneRegistry


_LEGACY_SCENE_FIELD_MAP: dict[str, tuple[Literal["tx_dd", "tx_vertical", "rx"], str]] = {
    "tx_dd_region_min": ("tx_dd", "region_min"),
    "tx_dd_region_max": ("tx_dd", "region_max"),
    "tx_dd_center_x": ("tx_dd", "center_x"),
    "tx_dd_center_y": ("tx_dd", "center_y"),
    "tx_vertical_region_min": ("tx_vertical", "region_min"),
    "tx_vertical_region_max": ("tx_vertical", "region_max"),
    "tx_vertical_center_x": ("tx_vertical", "center_x"),
    "tx_vertical_center_y": ("tx_vertical", "center_y"),
    "rx_region_min": ("rx", "region_min"),
    "rx_region_max": ("rx", "region_max"),
    "rx_center_y": ("rx", "center_y"),
}


def _unset_point3() -> Point3:
    return cast(Point3, _SCENE_UNSET)


def _unset_float() -> float:
    return cast(float, _SCENE_UNSET)


def _unset_edge2p() -> Edge2P:
    return cast(Edge2P, _STATE_UNSET)


def _unset_ordered_terminal_section() -> OrderedTerminalSection:
    return cast(OrderedTerminalSection, _STATE_UNSET)


def _unset_bridge_anchor() -> BridgeAnchor:
    return cast(BridgeAnchor, _STATE_UNSET)


def _unset_directed_landing_section() -> DirectedLandingSection:
    return cast(DirectedLandingSection, _STATE_UNSET)


def _unset_string() -> str:
    return cast(str, _STATE_UNSET)


def _unset_selection_key() -> tuple[float, str, int]:
    return cast(tuple[float, str, int], _STATE_UNSET)


def _unset_tx_series_binding() -> TxSeriesBindingInputs:
    return cast(TxSeriesBindingInputs, _STATE_UNSET)


def state_is_set(value: object) -> bool:
    return value is not _STATE_UNSET


def require_state(value: _T, *, name: str) -> _T:
    assert state_is_set(value), f"{name} is not initialized"
    return value


def _empty_group_objects() -> GroupObjects:
    return cast(GroupObjects, {"tx_dd": [], "tx_vertical": [], "rx_dd": [], "ferrite": []})


def _empty_em_ports() -> EmPorts:
    return cast(EmPorts, {"tx": [], "rx": []})


def _empty_em_port_assignments() -> EmPortAssignments:
    return cast(EmPortAssignments, {"tx": [], "rx": []})


def _empty_geometry_scene_registry() -> GeometrySceneRegistry:
    return cast(
        GeometrySceneRegistry,
        {
            "tx_dd": cast(TxDdSceneRegistry, {}),
            "tx_vertical": cast(TxVerticalSceneRegistry, {}),
            "rx": cast(RxSceneRegistry, {}),
        },
    )


def require_tx_dd_scene(ctx: "GeometryRuntimeContext") -> TxDdSceneRegistry:
    scene_registry = ctx.scene_registry
    assert "tx_dd" in scene_registry, "tx_dd scene registry is not initialized"
    tx_dd_scene = scene_registry["tx_dd"]
    assert "region_min" in tx_dd_scene, "tx_dd scene registry is missing region_min"
    assert "region_max" in tx_dd_scene, "tx_dd scene registry is missing region_max"
    assert "center_x" in tx_dd_scene, "tx_dd scene registry is missing center_x"
    assert "center_y" in tx_dd_scene, "tx_dd scene registry is missing center_y"
    return tx_dd_scene


def require_tx_vertical_scene(ctx: "GeometryRuntimeContext") -> TxVerticalSceneRegistry:
    scene_registry = ctx.scene_registry
    assert "tx_vertical" in scene_registry, "tx_vertical scene registry is not initialized"
    tx_vertical_scene = scene_registry["tx_vertical"]
    assert "region_min" in tx_vertical_scene, "tx_vertical scene registry is missing region_min"
    assert "region_max" in tx_vertical_scene, "tx_vertical scene registry is missing region_max"
    assert "center_x" in tx_vertical_scene, "tx_vertical scene registry is missing center_x"
    assert "center_y" in tx_vertical_scene, "tx_vertical scene registry is missing center_y"
    return tx_vertical_scene


def require_rx_scene(ctx: "GeometryRuntimeContext") -> RxSceneRegistry:
    scene_registry = ctx.scene_registry
    assert "rx" in scene_registry, "rx scene registry is not initialized"
    rx_scene = scene_registry["rx"]
    assert "region_min" in rx_scene, "rx scene registry is missing region_min"
    assert "region_max" in rx_scene, "rx scene registry is missing region_max"
    assert "center_y" in rx_scene, "rx scene registry is missing center_y"
    return rx_scene


def set_tx_dd_scene(
    ctx: "GeometryRuntimeContext",
    *,
    region_min: Point3,
    region_max: Point3,
    center_x: float,
    center_y: float,
) -> None:
    ctx.scene_registry["tx_dd"] = {
        "region_min": region_min,
        "region_max": region_max,
        "center_x": center_x,
        "center_y": center_y,
    }
    ctx.tx_dd_region_min = region_min
    ctx.tx_dd_region_max = region_max
    ctx.tx_dd_center_x = center_x
    ctx.tx_dd_center_y = center_y


def set_tx_vertical_scene(
    ctx: "GeometryRuntimeContext",
    *,
    region_min: Point3,
    region_max: Point3,
    center_x: float,
    center_y: float,
) -> None:
    ctx.scene_registry["tx_vertical"] = {
        "region_min": region_min,
        "region_max": region_max,
        "center_x": center_x,
        "center_y": center_y,
    }
    ctx.tx_vertical_region_min = region_min
    ctx.tx_vertical_region_max = region_max
    ctx.tx_vertical_center_x = center_x
    ctx.tx_vertical_center_y = center_y


def set_rx_scene(
    ctx: "GeometryRuntimeContext",
    *,
    region_min: Point3,
    region_max: Point3,
    center_y: float,
) -> None:
    ctx.scene_registry["rx"] = {
        "region_min": region_min,
        "region_max": region_max,
        "center_y": center_y,
    }
    ctx.rx_region_min = region_min
    ctx.rx_region_max = region_max
    ctx.rx_center_y = center_y


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
    tx_vertical_fr4_names: list[str] = field(default_factory=list)
    scene_objects: list[SceneObjectEntry] = field(default_factory=list)
    em_ports: EmPorts = field(default_factory=_empty_em_ports)
    em_port_assignments: EmPortAssignments = field(default_factory=_empty_em_port_assignments)
    dd_half_geometries: list[DdHalfGeometryCapture] = field(default_factory=list)
    tx_dd_rotation_angle_deg: float = 0.0
    tx_dd_rotation_pivot_xyz: Point3 = (0.0, 0.0, 0.0)
    tx_dd_rotation_object_names: list[str] = field(default_factory=list)


@dataclass
class FinalizeInputs:
    txdd_right_a_points: dict[int, tuple[Point3, float]] = field(default_factory=dict)
    txdd_right_object_names: dict[int, str] = field(default_factory=dict)
    # Debug geometry capture only. TX port ownership must come from tx_series_binding.feed_in/feed_out.
    txdd_start_stub_sources: dict[str, list[TxDdStartStubSource]] = field(default_factory=dict)
    rxdd_back_stub_sources: list[RxDdBackStubSource] = field(default_factory=list)
    tx_vertical_nodes_by_board: dict[BoardKey, list[TxVerticalLinkNode]] = field(default_factory=dict)
    # Legacy bridge/global captures are debug metadata only for the TX deterministic path.
    # Authoritative TX active-path ownership must be resolved from tx_series_binding.
    txdd_global_right_bridge_landing: DirectedLandingSection = field(default_factory=_unset_directed_landing_section)
    txdd_global_right_bridge_edge: Edge2P = field(default_factory=_unset_edge2p)
    txdd_global_right_bridge_section: OrderedTerminalSection = field(default_factory=_unset_ordered_terminal_section)
    txdd_global_right_bridge_anchor: BridgeAnchor = field(default_factory=_unset_bridge_anchor)
    txdd_global_right_bridge_object_name: str = field(default_factory=_unset_string)
    txdd_global_right_bridge_selection_key: tuple[float, str, int] = field(default_factory=_unset_selection_key)
    txdd_global_right_d_edge: Edge2P = field(default_factory=_unset_edge2p)
    txdd_global_right_d_object_name: str = field(default_factory=_unset_string)
    txdd_global_right_d_selection_key: tuple[float, str, int] = field(default_factory=_unset_selection_key)
    tx_vertical_global_outer_right_edge: Edge2P = field(default_factory=_unset_edge2p)
    tx_vertical_global_outer_left_edge: Edge2P = field(default_factory=_unset_edge2p)
    tx_vertical_global_outer_right_landing: DirectedLandingSection = field(default_factory=_unset_directed_landing_section)
    tx_vertical_global_outer_left_landing: DirectedLandingSection = field(default_factory=_unset_directed_landing_section)
    tx_vertical_global_outer_right_section: OrderedTerminalSection = field(default_factory=_unset_ordered_terminal_section)
    tx_vertical_global_outer_left_section: OrderedTerminalSection = field(default_factory=_unset_ordered_terminal_section)
    tx_vertical_global_outer_right_anchor: BridgeAnchor = field(default_factory=_unset_bridge_anchor)
    tx_vertical_global_outer_left_anchor: BridgeAnchor = field(default_factory=_unset_bridge_anchor)
    tx_vertical_outer_right_selection_key: tuple[float, str, int] = field(default_factory=_unset_selection_key)
    tx_vertical_outer_left_selection_key: tuple[float, str, int] = field(default_factory=_unset_selection_key)
    # Left tx_dd path is intentionally removed; downstream series reconnection stays disabled until rebuilt.
    tx_series_binding: TxSeriesBindingInputs = field(default_factory=TxSeriesBindingInputs)


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
    corner_mode: Literal[0, 1]
    pcb_thickness: float
    cu_thickness: float
    tx_dd_top_clearance: float
    tx_vertical_orientation_mode: Literal[0, 1]
    rx_face_clearance: float
    tx_vertical_plane: Literal["ZX"]
    scene_registry: GeometrySceneRegistry = field(default_factory=_empty_geometry_scene_registry)
    tx_dd_region_min: Point3 = field(default_factory=_unset_point3, repr=False)
    tx_dd_region_max: Point3 = field(default_factory=_unset_point3, repr=False)
    tx_dd_center_x: float = field(default_factory=_unset_float, repr=False)
    tx_dd_center_y: float = field(default_factory=_unset_float, repr=False)
    tx_vertical_region_min: Point3 = field(default_factory=_unset_point3, repr=False)
    tx_vertical_region_max: Point3 = field(default_factory=_unset_point3, repr=False)
    tx_vertical_center_x: float = field(default_factory=_unset_float, repr=False)
    tx_vertical_center_y: float = field(default_factory=_unset_float, repr=False)
    rx_region_min: Point3 = field(default_factory=_unset_point3, repr=False)
    rx_region_max: Point3 = field(default_factory=_unset_point3, repr=False)
    rx_center_y: float = field(default_factory=_unset_float, repr=False)

    def __post_init__(self) -> None:
        for field_name in _LEGACY_SCENE_FIELD_MAP:
            self._sync_legacy_scene_field(field_name, self.__dict__[field_name])

    def __setattr__(self, name: str, value: object) -> None:
        object.__setattr__(self, name, value)
        if name == "scene_registry":
            return
        if name in _LEGACY_SCENE_FIELD_MAP and "scene_registry" in self.__dict__:
            self._sync_legacy_scene_field(name, value)

    def _sync_legacy_scene_field(self, field_name: str, value: object) -> None:
        if value is _SCENE_UNSET:
            return
        registry_name, registry_key = _LEGACY_SCENE_FIELD_MAP[field_name]
        scene_registry = self.scene_registry
        registry = scene_registry[registry_name]
        registry[registry_key] = value

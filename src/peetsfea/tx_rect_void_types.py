from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from peetsfea.tx_rect_void_geometry import RectBounds

Number = int | float
CornerLabel = Literal["A", "B", "C", "D"]
InnerCornerLabel = Literal["a", "b", "c", "d"]
PathDirection = Literal["cw", "ccw"]
BoxRole = Literal["pcb", "copper"]
Plane = Literal["XY", "YZ"]
ModeledObjectRole = Literal["tx_single_coil", "rx_single_coil"]
ModeledObjectMaterial = Literal["composite"]


@dataclass(frozen=True)
class SingleCoilProfile:
    role: ModeledObjectRole
    object_id: str
    plane: Plane
    placement_owner_id: str
    pcb_body_prefix: str
    copper_body_prefix: str
    compound_label: str

    def world_delta(self, local_xyz: tuple[float, float, float]) -> tuple[float, float, float]:
        local_x, local_y, local_z = local_xyz
        if self.plane == "XY":
            return (local_x, local_y, local_z)
        return (local_z, local_x, local_y)

    def world_point(
        self,
        local_xyz: tuple[float, float, float],
        *,
        frame_origin_xyz: tuple[float, float, float],
    ) -> tuple[float, float, float]:
        world_dx, world_dy, world_dz = self.world_delta(local_xyz)
        return (
            frame_origin_xyz[0] + world_dx,
            frame_origin_xyz[1] + world_dy,
            frame_origin_xyz[2] + world_dz,
        )

    def world_size(self, local_size_xyz: tuple[float, float, float]) -> tuple[float, float, float]:
        size_x, size_y, size_z = local_size_xyz
        if self.plane == "XY":
            return (size_x, size_y, size_z)
        return (size_z, size_x, size_y)

    def plane_point(
        self,
        local_xy: tuple[float, float],
        *,
        frame_origin_xyz: tuple[float, float, float],
    ) -> tuple[float, float]:
        world_x, world_y, world_z = self.world_point((local_xy[0], local_xy[1], 0.0), frame_origin_xyz=frame_origin_xyz)
        if self.plane == "XY":
            return (world_x, world_y)
        return (world_y, world_z)


TX_SINGLE_COIL_PROFILE = SingleCoilProfile(
    role="tx_single_coil",
    object_id="tx_rect_void_coil",
    plane="XY",
    placement_owner_id="tx_region",
    pcb_body_prefix="tx_pcb",
    copper_body_prefix="tx_copper",
    compound_label="tx_rect_void_coil",
)

RX_SINGLE_COIL_PROFILE = SingleCoilProfile(
    role="rx_single_coil",
    object_id="rx_rect_void_coil",
    plane="YZ",
    placement_owner_id="rx_region_max",
    pcb_body_prefix="rx_pcb",
    copper_body_prefix="rx_copper",
    compound_label="rx_rect_void_coil",
)

_PROFILE_BY_ROLE: dict[ModeledObjectRole, SingleCoilProfile] = {
    "tx_single_coil": TX_SINGLE_COIL_PROFILE,
    "rx_single_coil": RX_SINGLE_COIL_PROFILE,
}


def profile_for_modeled_role(role: ModeledObjectRole) -> SingleCoilProfile:
    return _PROFILE_BY_ROLE[role]


@dataclass(frozen=True)
class RangeSpec:
    path: str
    is_integer: bool
    start: float
    end: float
    count: int


@dataclass(frozen=True)
class SingleCoilRangeSpec:
    outer_x_mm: RangeSpec
    outer_y_mm: RangeSpec
    turn_count: RangeSpec
    layer_count: RangeSpec
    layer_gap_mm: RangeSpec
    terminal_stub_length_mm: RangeSpec
    margin_ratio: RangeSpec
    metal_fill_factor: RangeSpec


@dataclass(frozen=True)
class ManufacturingSpec:
    pcb_thickness_mm: float
    copper_thickness_mm: float


@dataclass(frozen=True)
class TerminalPath:
    raw: str
    outer_corner: CornerLabel
    direction: PathDirection
    inner_corner: InnerCornerLabel


@dataclass(frozen=True)
class SingleCoilRectVoidSpec:
    schema_id: str
    units: Literal["mm"]
    manufacturing: ManufacturingSpec
    tx_coil: SingleCoilRangeSpec
    terminal_path: TerminalPath


@dataclass(frozen=True)
class SideGeometry:
    band_width_mm: float
    pitch_mm: float
    trace_mm: float
    gap_mm: float


@dataclass(frozen=True)
class SingleCoilSideGeometry:
    left: SideGeometry
    right: SideGeometry
    top: SideGeometry
    bottom: SideGeometry


@dataclass(frozen=True)
class RealizedSingleCoilRectVoid:
    seed: int
    terminal_path: str
    outer_x_mm: float
    outer_y_mm: float
    turn_count: int
    layer_count: int
    layer_gap_mm: float
    terminal_stub_length_mm: float
    void_x_over_outer_x: float
    void_y_over_outer_y: float
    void_center_x_over_outer_x: float
    void_center_y_over_outer_y: float
    void_x_mm: float
    void_y_mm: float
    void_center_x_mm: float
    void_center_y_mm: float
    margin_ratio: float
    margin_x_mm: float
    margin_y_mm: float
    metal_fill_factor: float
    trace_width_mm: float
    gap_width_mm: float
    pitch_mm: float
    pcb_thickness_mm: float
    copper_thickness_mm: float
    outer_bounds: RectBounds
    void_bounds: RectBounds
    side_geometry: SingleCoilSideGeometry


@dataclass(frozen=True)
class BoxSpec:
    label: str
    role: BoxRole
    feature: Literal["pcb_layer", "planar_outline", "terminal_stub", "vertical_bus"]
    layer_index: int
    origin_xyz: tuple[float, float, float]
    size_xyz: tuple[float, float, float]


@dataclass(frozen=True)
class ModeledObjectCanonicalCoordinates:
    frame_origin_xyz: tuple[float, float, float]
    outer_bounds_min_xyz: tuple[float, float, float]
    outer_bounds_max_xyz: tuple[float, float, float]
    outer_bounds_size_xyz: tuple[float, float, float]
    pcb_layer_z_positions_mm: tuple[float, ...]
    copper_layer_z_positions_mm: tuple[float, ...]


@dataclass(frozen=True)
class ModeledObjectTerminalMetadata:
    path: str
    outer_corner: CornerLabel
    inner_corner: InnerCornerLabel
    direction: PathDirection
    start_point_plane_mm: tuple[float, float]
    end_point_plane_mm: tuple[float, float]


@dataclass(frozen=True)
class ModeledObjectEntry:
    object_id: str
    role: ModeledObjectRole
    plane: Plane
    placement_owner_id: str
    material: ModeledObjectMaterial
    model_state: Literal[True]
    step_path: str
    expected_exported_body_names: tuple[str, ...]
    expected_exported_body_count: int
    canonical_coordinates: ModeledObjectCanonicalCoordinates
    terminal_metadata: ModeledObjectTerminalMetadata


@dataclass(frozen=True)
class SingleCoilRectVoidExportResult:
    source_toml_path: str
    output_step_path: str
    metadata_path: str
    expected_exported_body_names: tuple[str, ...]
    expected_exported_body_count: int
    realized: RealizedSingleCoilRectVoid
    boxes: tuple[BoxSpec, ...]
    modeled_objects: tuple[ModeledObjectEntry, ...]


__all__ = [
    "BoxSpec",
    "CornerLabel",
    "InnerCornerLabel",
    "ManufacturingSpec",
    "ModeledObjectCanonicalCoordinates",
    "ModeledObjectEntry",
    "ModeledObjectMaterial",
    "ModeledObjectRole",
    "ModeledObjectTerminalMetadata",
    "Number",
    "PathDirection",
    "Plane",
    "RangeSpec",
    "RX_SINGLE_COIL_PROFILE",
    "RectBounds",
    "RealizedSingleCoilRectVoid",
    "SideGeometry",
    "SingleCoilRangeSpec",
    "SingleCoilRectVoidExportResult",
    "SingleCoilRectVoidSpec",
    "SingleCoilSideGeometry",
    "SingleCoilProfile",
    "TerminalPath",
    "TX_SINGLE_COIL_PROFILE",
    "profile_for_modeled_role",
]

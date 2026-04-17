from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from peetsfea.aedt import Modeler3D, Object3d
from peetsfea.aedt.proxies import set_object_color, set_object_transparency
from peetsfea.backend.pyaedt.failfast import raise_on_false
from peetsfea.identity.hashing import object_name_tag_from_design_id
from peetsfea.types.manifest import CoilPolaritySpec, GroupEndpointEntry, TerminalLabel

from ..build_state import GeometryBuildState, Point3
from ..rules.cad_probe import _object_name, _probe_cad_object

NeoCoilRegistryTarget = Literal["tx_dd", "tx_vertical", "rx_dd", "ferrite", "fr4_only"]


@dataclass(frozen=True)
class NeoCoilBoxInstance:
    name_prefix: str
    board_id: str
    layer_index: int
    origin_xyz: Point3
    size_xyz: Point3
    material: str
    color_rgb: tuple[int, int, int]
    transparency: float
    registry_target: NeoCoilRegistryTarget

    def instantiate(
        self,
        *,
        modeler: Modeler3D,
        state: GeometryBuildState,
        design_id: str,
    ) -> str:
        if self.name_prefix == "":
            raise ValueError("neo coil instance name_prefix must be non-empty")
        if not self.name_prefix.startswith("neo_"):
            raise ValueError(f"neo coil instance name_prefix must start with 'neo_' (actual={self.name_prefix})")
        if self.board_id == "":
            raise ValueError("neo coil instance board_id must be non-empty")
        if self.layer_index < 0:
            raise ValueError(f"neo coil instance layer_index must be >= 0 (actual={self.layer_index})")
        if self.material == "":
            raise ValueError("neo coil instance material must be non-empty")
        if self.size_xyz[0] <= 0.0 or self.size_xyz[1] <= 0.0 or self.size_xyz[2] <= 0.0:
            raise ValueError(
                "neo coil instance size_xyz must be > 0 on every axis "
                f"(actual={self.size_xyz})"
            )
        object_name_tag = object_name_tag_from_design_id(design_id)
        object_name = f"{self.name_prefix}{self.board_id}_l{self.layer_index}_{object_name_tag}"
        if object_name in state.object_names:
            raise ValueError(f"neo coil instance name collision detected (name={object_name})")
        created = cast(
            Object3d,
            raise_on_false(
                modeler.create_box(
                    origin=[self.origin_xyz[0], self.origin_xyz[1], self.origin_xyz[2]],
                    sizes=[self.size_xyz[0], self.size_xyz[1], self.size_xyz[2]],
                    name=object_name,
                    material=self.material,
                ),
                operation="create_box",
                context={"name": object_name, "material": self.material},
            ),
        )
        set_object_color(created, color=self.color_rgb)
        set_object_transparency(created, transparency=self.transparency)
        created_name = _object_name(created)
        state.object_names.append(created_name)
        if self.registry_target == "fr4_only":
            state.fr4_object_names.append(created_name)
        else:
            state.group_objects[self.registry_target].append(created_name)
        state.cad_probe.append(_probe_cad_object(created))
        return created_name


@dataclass(frozen=True)
class NeoCoilInstance:
    name_prefix: str
    group_kind: Literal["tx_dd", "tx_vertical", "rx_dd"]
    board_id: str
    group_instance_index: int
    layer_index: int
    path_points: list[Point3]
    trace_width: float
    thickness: float
    material: str
    color_rgb: tuple[int, int, int]
    transparency: float
    plane: Literal["XY", "YZ", "ZX"]
    start_label: TerminalLabel
    end_label: TerminalLabel
    dd_family: Literal["none", "tx_dd", "rx_dd"]
    dd_pair_index: int
    instance_side: Literal["left", "right", "center"]
    current_direction: Literal["cw", "ccw"]

    def instantiate(
        self,
        *,
        modeler: Modeler3D,
        state: GeometryBuildState,
        design_id: str,
    ) -> str:
        if self.name_prefix == "":
            raise ValueError("neo coil instance name_prefix must be non-empty")
        if not self.name_prefix.startswith("neo_"):
            raise ValueError(f"neo coil instance name_prefix must start with 'neo_' (actual={self.name_prefix})")
        if self.board_id == "":
            raise ValueError("neo coil instance board_id must be non-empty")
        if self.group_instance_index < 0:
            raise ValueError(
                f"neo coil instance group_instance_index must be >= 0 (actual={self.group_instance_index})"
            )
        if self.layer_index < 0:
            raise ValueError(f"neo coil instance layer_index must be >= 0 (actual={self.layer_index})")
        if len(self.path_points) < 2:
            raise ValueError("neo coil instance path_points must contain at least 2 points")
        if self.trace_width <= 0.0:
            raise ValueError(f"neo coil instance trace_width must be > 0 (actual={self.trace_width})")
        if self.thickness <= 0.0:
            raise ValueError(f"neo coil instance thickness must be > 0 (actual={self.thickness})")
        if self.material == "":
            raise ValueError("neo coil instance material must be non-empty")
        object_name_tag = object_name_tag_from_design_id(design_id)
        object_name = (
            f"{self.name_prefix}{self.board_id}_i{self.group_instance_index}_l{self.layer_index}_{object_name_tag}"
        )
        if object_name in state.object_names:
            raise ValueError(f"neo coil instance name collision detected (name={object_name})")
        created = cast(
            Object3d,
            raise_on_false(
                modeler.create_polyline(
                    points=[[point[0], point[1], point[2]] for point in self.path_points],
                    name=object_name,
                    material=self.material,
                    xsection_type="Rectangle",
                    xsection_width=self.trace_width,
                    xsection_height=self.thickness,
                ),
                operation="create_polyline",
                context={"name": object_name, "material": self.material},
            ),
        )
        set_object_color(created, color=self.color_rgb)
        set_object_transparency(created, transparency=self.transparency)
        created_name = _object_name(created)
        state.object_names.append(created_name)
        state.group_objects[self.group_kind].append(created_name)
        state.cad_probe.append(_probe_cad_object(created))
        state.group_endpoints.append(
            cast(
                GroupEndpointEntry,
                {
                    "group_kind": self.group_kind,
                    "group_instance_index": self.group_instance_index,
                    "board_id": self.board_id,
                    "start_xyz": self.path_points[0],
                    "end_xyz": self.path_points[-1],
                    "start_label": self.start_label,
                    "end_label": self.end_label,
                    "present": True,
                },
            )
        )
        state.coil_polarity.append(
            cast(
                CoilPolaritySpec,
                {
                    "group_kind": self.group_kind,
                    "group_instance_index": self.group_instance_index,
                    "board_id": self.board_id,
                    "dd_family": self.dd_family,
                    "dd_pair_index": self.dd_pair_index,
                    "instance_side": self.instance_side,
                    "current_direction": self.current_direction,
                },
            )
        )
        return created_name

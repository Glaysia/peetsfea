from __future__ import annotations

import math
from pathlib import Path
from typing import Literal, cast

import pytest
from peetsfea.aedt import Modeler3D
from peetsfea.aedt import Object3d

from peetsfea.backend.pyaedt.geometry.build_state import FinalizeInputs, GeometryBuildState, GeometryRuntimeContext, set_tx_dd_scene
from peetsfea.backend.pyaedt.geometry.rules.cad_probe import _probe_cad_object
from peetsfea.backend.pyaedt.geometry.rules.tx_mode0_rotation import (
    compute_tx_mode0_rotation_angle_rad,
    rotate_tx_mode0_objects_if_needed,
)
from peetsfea.backend.pyaedt.geometry.tx_stub_faces import capture_stub_face_ref_from_object, edge_id_from_face_id, edge_points_from_edge_id
from peetsfea.types.manifest import GroupEndpointEntry, GroupGeometryParams, Manifest, ResolvedPcbInstance, SceneObjectEntry, SelectedParameters, SelectedParametersMax


class _FakeEdgePoint:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z


class _FakeEdge:
    def __init__(self, first: list[float], second: list[float]) -> None:
        self.midpoint = _FakeEdgePoint(
            (first[0] + second[0]) / 2.0,
            (first[1] + second[1]) / 2.0,
            (first[2] + second[2]) / 2.0,
        )


class _FakeObject:
    def __init__(self, name: str, points: list[list[float]]) -> None:
        self.name = name
        self.points = [point[:] for point in points]
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        zs = [point[2] for point in points]
        self.bounding_box = [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
        self.edges: list[_FakeEdge] = []
        self.edge_ids: list[int] = []
        self.face_ids: list[int] = []


class _FakeCoordinateSystem:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeModeler:
    def __init__(self) -> None:
        self.objects: dict[str, _FakeObject] = {}
        self.edge_vertices: dict[int, tuple[int, int]] = {}
        self.vertex_positions: dict[int, list[float]] = {}
        self.face_edges: dict[int, list[int]] = {}
        self.face_vertices: dict[int, list[int]] = {}
        self.face_centers: dict[int, list[float]] = {}
        self.face_areas: dict[int, float] = {}
        self.create_coordinate_system_calls: list[dict[str, object]] = []
        self.set_working_coordinate_system_calls: list[str] = []
        self.rotate_calls: list[dict[str, object]] = []
        self.coordinate_system_origins: dict[str, list[float]] = {"Global": [0.0, 0.0, 0.0]}
        self.current_coordinate_system = "Global"
        self.next_edge_id = 1
        self.next_vertex_id = 1
        self.next_face_id = 1

    def _register_vertex(self, position: list[float]) -> int:
        vertex_id = self.next_vertex_id
        self.next_vertex_id += 1
        self.vertex_positions[vertex_id] = list(position)
        return vertex_id

    def _register_face(self, *, obj: _FakeObject, vertex_ids: list[int], edge_ids: list[int]) -> None:
        points = [self.vertex_positions[vertex_id] for vertex_id in vertex_ids]
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        zs = [point[2] for point in points]
        unique_x = sorted({round(value, 9) for value in xs})
        unique_y = sorted({round(value, 9) for value in ys})
        unique_z = sorted({round(value, 9) for value in zs})
        if len(unique_z) == 1:
            area = (max(xs) - min(xs)) * (max(ys) - min(ys))
        elif len(unique_y) == 1:
            area = (max(xs) - min(xs)) * (max(zs) - min(zs))
        else:
            area = (max(ys) - min(ys)) * (max(zs) - min(zs))
        face_id = self.next_face_id
        self.next_face_id += 1
        self.face_vertices[face_id] = list(vertex_ids)
        self.face_edges[face_id] = list(edge_ids)
        self.face_centers[face_id] = [sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs)]
        self.face_areas[face_id] = area
        obj.face_ids.append(face_id)

    def create_box(self, **kwargs: object) -> _FakeObject:
        origin = cast(list[float], kwargs["origin"])
        sizes = cast(list[float], kwargs["sizes"])
        max_corner = [origin[0] + sizes[0], origin[1] + sizes[1], origin[2] + sizes[2]]
        name = cast(str, kwargs["name"])
        obj = _FakeObject(name=name, points=[origin[:], max_corner])
        corners = {
            "000": [origin[0], origin[1], origin[2]],
            "100": [max_corner[0], origin[1], origin[2]],
            "010": [origin[0], max_corner[1], origin[2]],
            "110": [max_corner[0], max_corner[1], origin[2]],
            "001": [origin[0], origin[1], max_corner[2]],
            "101": [max_corner[0], origin[1], max_corner[2]],
            "011": [origin[0], max_corner[1], max_corner[2]],
            "111": [max_corner[0], max_corner[1], max_corner[2]],
        }
        corner_vertex_ids = {key: self._register_vertex(point) for key, point in corners.items()}
        edge_defs = [
            ("000", "100"),
            ("000", "010"),
            ("000", "001"),
            ("100", "110"),
            ("100", "101"),
            ("010", "110"),
            ("010", "011"),
            ("001", "101"),
            ("001", "011"),
            ("110", "111"),
            ("101", "111"),
            ("011", "111"),
        ]
        edge_ids: dict[tuple[str, str], int] = {}
        for first_key, second_key in edge_defs:
            edge_id = self.next_edge_id
            self.next_edge_id += 1
            self.edge_vertices[edge_id] = (corner_vertex_ids[first_key], corner_vertex_ids[second_key])
            obj.edge_ids.append(edge_id)
            obj.edges.append(_FakeEdge(corners[first_key], corners[second_key]))
            edge_ids[(first_key, second_key)] = edge_id
            edge_ids[(second_key, first_key)] = edge_id
        self._register_face(obj=obj, vertex_ids=[corner_vertex_ids[key] for key in ("000", "100", "110", "010")], edge_ids=[edge_ids[key] for key in (("000", "100"), ("100", "110"), ("110", "010"), ("010", "000"))])
        self._register_face(obj=obj, vertex_ids=[corner_vertex_ids[key] for key in ("001", "101", "111", "011")], edge_ids=[edge_ids[key] for key in (("001", "101"), ("101", "111"), ("111", "011"), ("011", "001"))])
        self._register_face(obj=obj, vertex_ids=[corner_vertex_ids[key] for key in ("000", "100", "101", "001")], edge_ids=[edge_ids[key] for key in (("000", "100"), ("100", "101"), ("101", "001"), ("001", "000"))])
        self._register_face(obj=obj, vertex_ids=[corner_vertex_ids[key] for key in ("010", "110", "111", "011")], edge_ids=[edge_ids[key] for key in (("010", "110"), ("110", "111"), ("111", "011"), ("011", "010"))])
        self._register_face(obj=obj, vertex_ids=[corner_vertex_ids[key] for key in ("000", "010", "011", "001")], edge_ids=[edge_ids[key] for key in (("000", "010"), ("010", "011"), ("011", "001"), ("001", "000"))])
        self._register_face(obj=obj, vertex_ids=[corner_vertex_ids[key] for key in ("100", "110", "111", "101")], edge_ids=[edge_ids[key] for key in (("100", "110"), ("110", "111"), ("111", "101"), ("101", "100"))])
        self.objects[name] = obj
        return obj

    def create_coordinate_system(self, *, origin=None, reference_cs: str = "Global", name: str | None = None, mode: str = "axis", x_pointing=None, y_pointing=None) -> _FakeCoordinateSystem:
        _ = reference_cs, mode, x_pointing, y_pointing
        assert isinstance(origin, list)
        assert name is not None
        self.create_coordinate_system_calls.append({"origin": list(origin), "name": name})
        self.coordinate_system_origins[name] = list(origin)
        return _FakeCoordinateSystem(name)

    def set_working_coordinate_system(self, name: str) -> bool:
        self.set_working_coordinate_system_calls.append(name)
        self.current_coordinate_system = name
        return True

    def rotate(self, assignment: object, axis: str, angle: float = 90.0, units: str = "deg") -> bool:
        self.rotate_calls.append({"assignment": assignment, "axis": axis, "angle": angle, "units": units})
        assert axis == "Y"
        assert units == "deg"
        raw_names = assignment if isinstance(assignment, list) else [assignment]
        names = [cast(str, name) for name in raw_names]
        origin = self.coordinate_system_origins[self.current_coordinate_system]
        angle_rad = -math.radians(float(angle))
        cos_theta = math.cos(angle_rad)
        sin_theta = math.sin(angle_rad)

        def _rotate_point(point: list[float]) -> list[float]:
            dx = point[0] - origin[0]
            dz = point[2] - origin[2]
            return [
                origin[0] + (cos_theta * dx) - (sin_theta * dz),
                point[1],
                origin[2] + (sin_theta * dx) + (cos_theta * dz),
            ]

        for name in names:
            obj = self.objects[name]
            for vertex_id in {vertex_id for face_id in obj.face_ids for vertex_id in self.face_vertices[face_id]}:
                self.vertex_positions[vertex_id] = _rotate_point(self.vertex_positions[vertex_id])
            obj.edges = []
            for edge_id in obj.edge_ids:
                first_vertex_id, second_vertex_id = self.edge_vertices[edge_id]
                obj.edges.append(
                    _FakeEdge(
                        self.vertex_positions[first_vertex_id],
                        self.vertex_positions[second_vertex_id],
                    )
                )
            for face_id in obj.face_ids:
                points = [self.vertex_positions[vertex_id] for vertex_id in self.face_vertices[face_id]]
                xs = [point[0] for point in points]
                ys = [point[1] for point in points]
                zs = [point[2] for point in points]
                self.face_centers[face_id] = [sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs)]
            all_points = [self.vertex_positions[vertex_id] for face_id in obj.face_ids for vertex_id in self.face_vertices[face_id]]
            xs = [point[0] for point in all_points]
            ys = [point[1] for point in all_points]
            zs = [point[2] for point in all_points]
            obj.bounding_box = [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
        return True

    def get_object_from_name(self, assignment: str) -> _FakeObject:
        return self.objects[assignment]

    def get_object_faces(self, assignment: str) -> list[int]:
        return list(self.objects[assignment].face_ids)

    def get_face_edges(self, assignment: int) -> list[int]:
        return list(self.face_edges[int(assignment)])

    def get_face_vertices(self, assignment: int) -> list[int]:
        return list(self.face_vertices[int(assignment)])

    def get_face_center(self, assignment: int) -> list[float]:
        return list(self.face_centers[int(assignment)])

    def get_face_area(self, assignment: int) -> float:
        return float(self.face_areas[int(assignment)])

    def get_edge_vertices(self, assignment: int) -> list[int]:
        first, second = self.edge_vertices[int(assignment)]
        return [first, second]

    def get_vertex_position(self, assignment: int) -> list[float]:
        return list(self.vertex_positions[int(assignment)])


def _ctx_mode0() -> GeometryRuntimeContext:
    return GeometryRuntimeContext(
        manifest=cast(Manifest, {}),
        selected=cast(
            SelectedParameters,
            {
                "neo_tx_dd_right_terminal_path": "D_ccw_to_d",
                "neo_tx_dd_left_terminal_path": "a_cw_to_A",
                "neo_tx_vertical_zx_terminal_path": "B_ccw_to_c",
            },
        ),
        selected_max=cast(SelectedParametersMax, {}),
        selected_groups=[],
        selected_group_geometry=[],
        selected_pcbs=cast(list[ResolvedPcbInstance], []),
        group_geometry_by_kind=cast(
            dict[Literal["tx_dd", "tx_vertical", "rx_dd"], GroupGeometryParams],
            {"tx_dd": cast(GroupGeometryParams, {}), "tx_vertical": cast(GroupGeometryParams, {}), "rx_dd": cast(GroupGeometryParams, {})},
        ),
        tx_board_ids={"tx_main_0"},
        design_id="demo",
        aedt_path=Path("/tmp/demo.aedt"),
        metadata_path=Path("/tmp/demo.json"),
        close_on_exit=True,
        tx_dd_outer_x=20.0,
        tx_dd_outer_y=10.0,
        tx_vertical_outer_x=20.0,
        tx_vertical_outer_y=8.0,
        rx_dd_outer_x=20.0,
        rx_dd_outer_y=8.0,
        corner_mode=0,
        pcb_thickness=1.6,
        cu_thickness=0.035,
        tx_dd_top_clearance=0.1,
        tx_vertical_orientation_mode=0,
        rx_face_clearance=0.0,
        tx_vertical_plane="ZX",
    )


def test_compute_tx_mode0_rotation_angle_reaches_region_top() -> None:
    pivot = (10.0, 0.0, 4.0)
    points = [(10.0, 0.0, 4.0), (18.0, 0.0, 4.0)]
    angle = compute_tx_mode0_rotation_angle_rad(candidate_points=points, top_z=10.0, pivot=pivot)
    rotated_top_z = pivot[2] + ((18.0 - 10.0) * math.sin(angle))
    assert rotated_top_z == pytest.approx(10.0)


def test_rotate_tx_mode0_objects_keeps_tx_stub_face_id_live() -> None:
    ctx = _ctx_mode0()
    set_tx_dd_scene(
        ctx,
        region_min=(10.0, -10.0, 0.0),
        region_max=(30.0, 10.0, 13.0),
        center_x=20.0,
        center_y=0.0,
    )
    modeler = _FakeModeler()
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()

    tx_obj = modeler.create_box(
        origin=[10.5, -2.5, 10.0],
        sizes=[10.0, 1.0, 1.0],
        name="coil_tx_main_0_demo",
        material="copper",
    )
    fr4_obj = modeler.create_box(
        origin=[10.0, -5.0, 9.0],
        sizes=[20.0, 10.0, 1.6],
        name="neo_fr4_tx_dd_tx_main_0_l0_demo",
        material="FR4_epoxy",
    )
    ferrite_obj = modeler.create_box(
        origin=[10.0, -5.0, 6.0],
        sizes=[20.0, 10.0, 2.0],
        name="ferrite_tx_demo",
        material="peetsfea_ferrite_mu500",
    )
    tx_stub_obj = modeler.create_box(
        origin=[10.5, -2.5, 11.0],
        sizes=[1.0, 1.0, 1.0],
        name="txs_in_above_demo",
        material="copper",
    )
    state.object_names = [tx_obj.name, fr4_obj.name, ferrite_obj.name, tx_stub_obj.name]
    state.group_objects["tx_dd"] = [tx_obj.name, tx_stub_obj.name]
    state.group_objects["ferrite"] = [ferrite_obj.name]
    state.fr4_object_names = [fr4_obj.name]
    state.cad_probe = [
        _probe_cad_object(cast(Object3d, tx_obj)),
        _probe_cad_object(cast(Object3d, fr4_obj)),
        _probe_cad_object(cast(Object3d, ferrite_obj)),
        _probe_cad_object(cast(Object3d, tx_stub_obj)),
    ]
    state.group_endpoints = [
        cast(
            GroupEndpointEntry,
            {
                "group_kind": "tx_dd",
                "group_instance_index": 0,
                "board_id": "tx_main_0",
                "start_xyz": (10.5, -2.0, 11.0),
                "end_xyz": (20.5, -2.0, 11.0),
                "start_label": "A",
                "end_label": "B",
                "present": True,
            },
        )
    ]
    state.scene_objects = [
        cast(
            SceneObjectEntry,
            {
                "name": ferrite_obj.name,
                "kind": "tx_ferrite",
                "present": True,
                "origin_xyz": (10.0, -5.0, 6.0),
                "size_xyz": (20.0, 10.0, 2.0),
                "plane": "XY",
                "non_model": False,
            },
        )
    ]
    face_ref = capture_stub_face_ref_from_object(
        modeler=cast(Modeler3D, modeler),
        object_name=tx_stub_obj.name,
        expected_face_center=(11.0, -2.0, 12.0),
        face_kind="tx_dd_xy",
        stub_role="in_above",
        context="tx mode0 stub face capture",
    )

    rotate_tx_mode0_objects_if_needed(ctx, state, finalize_inputs, cast(Modeler3D, modeler))

    assert state.tx_dd_rotation_angle_deg > 0.0
    edge_id = edge_id_from_face_id(
        modeler=cast(Modeler3D, modeler),
        face_ref=face_ref,
        edge_role="tx_port",
        context="tx mode0 rotated port edge",
    )
    rotated_edge = edge_points_from_edge_id(
        modeler=cast(Modeler3D, modeler),
        edge_id=edge_id,
        context="tx mode0 rotated edge points",
    )
    assert rotated_edge[0][1] == pytest.approx(rotated_edge[1][1])
    assert rotated_edge[0][2] != pytest.approx(rotated_edge[1][2])

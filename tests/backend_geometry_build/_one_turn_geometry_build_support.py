from __future__ import annotations
# ruff: noqa: E402

import importlib
import math
import os
import sys
import types
from collections import Counter
from pathlib import Path
from typing import Literal, cast
from unittest.mock import patch

import pytest
from peetsfea.aedt import Hfss
from peetsfea.aedt import Modeler3D
from peetsfea.identity.hashing import object_name_tag_from_design_id

TEST_PEETSFEA_PACKAGE_ROOT = (Path(__file__).resolve().parents[2] / "src" / "peetsfea").resolve()
TEST_GEOMETRY_BUILDERS_ROOT = TEST_PEETSFEA_PACKAGE_ROOT / "backend" / "pyaedt" / "geometry" / "builders"


def _object_name_tag(design_id: str) -> str:
    return object_name_tag_from_design_id(design_id)


def _assert_module_file_under_root(module: types.ModuleType, *, expected_root: Path, context: str) -> None:
    module_file = getattr(module, "__file__", None)
    if module_file is None:
        raise RuntimeError(f"{context} has no __file__")
    resolved_file = Path(module_file).resolve()
    if expected_root not in resolved_file.parents:
        raise RuntimeError(f"{context} points outside {expected_root}: {resolved_file}")


def _assert_bootstrapped_peetsfea_submodule_root(module: types.ModuleType, *, package_root: Path) -> None:
    module_file = getattr(module, "__file__", None)
    if module_file is not None:
        resolved_file = Path(module_file).resolve()
        if package_root not in resolved_file.parents:
            raise RuntimeError(
                "existing peetsfea submodule points outside the expected package root "
                f"{package_root}: {resolved_file}"
            )
        return
    module_paths = getattr(module, "__path__", None)
    if module_paths is None:
        raise RuntimeError("existing peetsfea submodule has neither __file__ nor __path__")
    normalized_paths = {Path(path).resolve() for path in cast(list[str], list(module_paths))}
    if not any(package_root == path or package_root in path.parents for path in normalized_paths):
        raise RuntimeError(
            "existing peetsfea submodule points to unexpected roots "
            f"{sorted(str(path) for path in normalized_paths)}; expected under {package_root}"
        )


def _assert_bootstrapped_peetsfea_package_root(package: types.ModuleType, *, package_root: Path) -> None:
    package_paths = getattr(package, "__path__", None)
    if package_paths is None:
        raise RuntimeError("existing peetsfea module is not a package")
    normalized_paths = {str(Path(path).resolve()) for path in cast(list[str], list(package_paths))}
    expected_path = str(package_root)
    if expected_path not in normalized_paths:
        raise RuntimeError(
            "existing peetsfea package points to unexpected roots "
            f"{sorted(normalized_paths)}; expected {expected_path}"
        )


def _bootstrap_peetsfea_test_package() -> None:
    package_root = TEST_PEETSFEA_PACKAGE_ROOT
    for module_name, existing_module in list(sys.modules.items()):
        if not module_name.startswith("peetsfea"):
            continue
        if not isinstance(existing_module, types.ModuleType):
            raise RuntimeError(f"existing {module_name} entry is not a module")
        _assert_bootstrapped_peetsfea_submodule_root(existing_module, package_root=package_root)
    if "peetsfea" in sys.modules:
        existing_package = sys.modules["peetsfea"]
        if not isinstance(existing_package, types.ModuleType):
            raise RuntimeError("existing peetsfea entry is not a module")
        _assert_bootstrapped_peetsfea_package_root(existing_package, package_root=package_root)
        return
    if not package_root.is_dir():
        raise RuntimeError(f"expected peetsfea package root at {package_root}")
    package = types.ModuleType("peetsfea")
    package.__file__ = str(package_root / "__init__.py")
    package.__package__ = "peetsfea"
    package.__path__ = [str(package_root)]  # type: ignore[attr-defined]
    sys.modules["peetsfea"] = package


_bootstrap_peetsfea_test_package()


def _install_group_builder_tx_dd_test_alias() -> None:
    legacy_module_name = "peetsfea.backend.pyaedt.geometry.builders.group_builder_tx_dd"
    if legacy_module_name in sys.modules:
        existing_module = sys.modules[legacy_module_name]
        if not isinstance(existing_module, types.ModuleType):
            raise RuntimeError(f"existing {legacy_module_name} entry is not a module")
        _assert_module_file_under_root(
            existing_module,
            expected_root=TEST_GEOMETRY_BUILDERS_ROOT,
            context=f"existing {legacy_module_name}",
        )
        return
    builders_root = TEST_GEOMETRY_BUILDERS_ROOT
    if (builders_root / "group_builder_tx_dd.py").is_file():
        return
    backup_module_name = "peetsfea.backend.pyaedt.geometry.builders.group_builder_tx_dd_wrapper_backup"
    if not (builders_root / "group_builder_tx_dd_wrapper_backup.py").is_file():
        raise RuntimeError(
            "expected a test-only group_builder_tx_dd compatibility target under "
            f"{builders_root}"
        )
    backup_module = importlib.import_module(backup_module_name)
    _assert_module_file_under_root(
        backup_module,
        expected_root=builders_root,
        context=f"test-only compatibility module {backup_module_name}",
    )
    sys.modules[legacy_module_name] = backup_module


_install_group_builder_tx_dd_test_alias()

from peetsfea.backend.pyaedt.geometry.build import (
    _create_major_device_groups,
    _append_rxdd_back_stub_sources_if_needed,
    _edge_points_at_path_end,
    _edge_points_at_yz_terminal,
    _edge_points_at_tx_vertical_opposite_terminal,
    _edge_points_at_tx_vertical_terminal,
    _tx_vertical_bridge_edges_from_node,
)
import peetsfea.backend.pyaedt.geometry.builders.build_tx_vertical as build_tx_vertical_module
from peetsfea.backend.pyaedt.geometry.rx_stub_ports import (
    record_rx_dd_port_stub_back_face,
    reset_rx_stub_port_back_face_corners,
    resolve_rx_dd_port_edges_from_back_faces,
)
from peetsfea.backend.pyaedt.geometry.builders.build_artifacts import (
    _anti_parallel_bridge_sheet_points,
    _apply_back_connect_stub_pair_bridge,
    _apply_existing_edge_bridge_conductor,
    _assert_legacy_zx_tx_series_chain_graph,
    _assert_stacked_tx_dd_half_conductors_closed,
    _assert_tx_conductor_graph_common,
    _complete_tx_series_chain_binding,
    _resolve_tx_vertical_zx_series_chain_landings,
    _rxdd_stub_attach_center_from_anchor,
    _finalize_solids_and_substrates_impl,
    _rxdd_connect_landing_segment_from_anchor_pair,
    _rxdd_connect_sheet_points_from_anchor_pair,
    _stub_center_from_anchor,
)
from peetsfea.backend.pyaedt.geometry.build_state import (
    DirectedLandingSection,
    FinalizeInputs,
    GeometryBuildState,
    GeometryRuntimeContext,
    OrderedTerminalSection,
    TxSeriesBindingInputs,
    TxSeriesChainBinding,
    state_is_set,
)
from peetsfea.backend.pyaedt.geometry.builders.group_builder_rx_dd import build_for_board as build_rx_dd_for_board
from peetsfea.backend.pyaedt.geometry.builders.group_builder_tx_dd import (
    build_for_board as build_tx_dd_for_board,
)
from peetsfea.backend.pyaedt.geometry.builders.group_builder_tx_vertical import build_for_board as build_tx_vertical_for_board
from peetsfea.backend.pyaedt.geometry.rules.placement_rules import (
    _build_txdd_right_points_a_to_d_one_turn,
    _build_rxdd_right_points_A_to_d_cw,
    _edge_points_at_xy_terminal,
    _extend_endpoints,
    _tx_dd_center_y_and_layer,
    _txdd_half_topology,
    _txdd_right_points,
    _txdd_right_topology,
)
from peetsfea.backend.pyaedt.geometry.rules.solid_ops import safe_unite
from peetsfea.backend.pyaedt.geometry.rules.spiral_points import _map_xy_points_to_yz, _mirror_points_about_y_axis_line
from peetsfea.types.manifest import CadProbe, GroupGeometryParams, GroupObjects, Manifest, ResolvedCoilGroup, ResolvedPcbInstance, SelectedParameters, SelectedParametersMax

LOCAL_AEDT_NAME_LENGTH_LIMIT = 60


def _normalize_edge_points(edge: tuple[tuple[float, float, float], tuple[float, float, float]]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    first, second = edge
    return (first, second) if first <= second else (second, first)


def _assert_points_close(actual: list[list[float]], expected: list[list[float]]) -> None:
    assert len(actual) == len(expected)
    for actual_point, expected_point in zip(actual, expected, strict=True):
        assert actual_point == pytest.approx(expected_point)


def _assert_edge_close(
    actual: tuple[tuple[float, float, float], tuple[float, float, float]],
    expected: tuple[tuple[float, float, float], tuple[float, float, float]],
) -> None:
    assert actual[0] == pytest.approx(expected[0])
    assert actual[1] == pytest.approx(expected[1])


def _assert_names_fit_local_aedt_limit(names: list[str]) -> None:
    assert all(len(name) <= LOCAL_AEDT_NAME_LENGTH_LIMIT for name in names)


def _created_call_names(calls: list[dict[str, object]]) -> list[str]:
    return [cast(str, call["name"]) for call in calls]


def _noop_close_stacked_tx_dd_half_conductors_with_hex_vias(**kwargs: object) -> str:
    primary_object_name = kwargs["primary_object_name"]
    return cast(str, primary_object_name)


def _assert_created_call_names_fit_local_aedt_limit(calls: list[dict[str, object]]) -> None:
    _assert_names_fit_local_aedt_limit(_created_call_names(calls))


def test_create_major_device_groups_raises_when_group_creation_returns_false() -> None:
    class _GroupFailModeler:
        def create_group(self, *, objects: list[str], group_name: str) -> bool:
            _ = objects, group_name
            return False

    state = GeometryBuildState()
    state.group_objects["tx_dd"] = ["coil_tx_a"]
    state.group_objects["rx_dd"] = ["coil_rx_a"]
    state.group_objects["ferrite"] = ["ferrite_a"]
    state.fr4_object_names = ["fr4_a"]

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: create_group"):
        _create_major_device_groups(cast(Modeler3D, _GroupFailModeler()), state)


def test_safe_unite_raises_when_unite_returns_false() -> None:
    class _FalseUniteModeler:
        def unite(self, assignment: list[str]) -> bool:
            _ = assignment
            return False

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: unite"):
        safe_unite(
            modeler=cast(Modeler3D, _FalseUniteModeler()),
            targets=["a", "b"],
            error_context="demo unite",
        )


class _FakePolylineObject:
    def __init__(self, name: str, points: list[list[float]]) -> None:
        self.name = name
        self.color: tuple[int, int, int] | None = None
        self.transparency: float | None = None
        self.points = [point[:] for point in points]
        if points:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            zs = [point[2] for point in points]
            self.bounding_box = [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
        else:
            self.bounding_box = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.edge_ids: list[int] = []
        self.edges: list[_FakeEdge] = [
            _FakeEdge(points[idx], points[idx + 1]) for idx in range(max(0, len(points) - 1))
        ]


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


class _FakeCoordinateSystem:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeModeler:
    def __init__(self) -> None:
        self.polyline_calls: list[dict[str, object]] = []
        self.create_box_calls: list[dict[str, object]] = []
        self.create_cylinder_calls: list[dict[str, object]] = []
        self.cover_lines_calls: list[str] = []
        self.thicken_sheet_calls: list[tuple[str, float]] = []
        self.subtract_calls: list[dict[str, object]] = []
        self.get_object_faces_calls: list[str] = []
        self.get_object_edges_calls: list[str] = []
        self.unite_calls: list[list[str]] = []
        self.rotate_calls: list[dict[str, object]] = []
        self.create_coordinate_system_calls: list[dict[str, object]] = []
        self.set_working_coordinate_system_calls: list[str] = []
        self.objects: dict[str, _FakePolylineObject] = {}
        self.edge_vertices: dict[int, tuple[int, int]] = {}
        self.vertex_positions: dict[int, list[float]] = {}
        self.next_edge_id = 1
        self.next_vertex_id = 1
        self.coordinate_system_origins: dict[str, list[float]] = {"Global": [0.0, 0.0, 0.0]}
        self.current_coordinate_system = "Global"

    def _register_vertex(self, position: list[float]) -> int:
        vertex_id = self.next_vertex_id
        self.next_vertex_id += 1
        self.vertex_positions[vertex_id] = list(position)
        return vertex_id

    def _register_edge(self, first: list[float], second: list[float]) -> int:
        edge_id = self.next_edge_id
        self.next_edge_id += 1
        first_vertex_id = self._register_vertex(first)
        second_vertex_id = self._register_vertex(second)
        self.edge_vertices[edge_id] = (first_vertex_id, second_vertex_id)
        return edge_id

    def _ensure_object(self, name: str) -> _FakePolylineObject:
        obj = self.objects.get(name)
        if obj is None:
            obj = _FakePolylineObject(name, [])
            self.objects[name] = obj
        return obj

    def create_polyline(self, **kwargs: object) -> _FakePolylineObject:
        self.polyline_calls.append(dict(kwargs))
        points = cast(list[list[float]], kwargs["points"])
        obj = _FakePolylineObject(str(kwargs["name"]), points)
        close_surface = bool(kwargs.get("close_surface", False))
        for idx in range(len(points) - 1):
            obj.edge_ids.append(self._register_edge(points[idx], points[idx + 1]))
        if close_surface and len(points) > 2:
            obj.edge_ids.append(self._register_edge(points[-1], points[0]))
            obj.edges.append(_FakeEdge(points[-1], points[0]))
        self.objects[obj.name] = obj
        return obj

    def create_box(self, **kwargs: object) -> _FakePolylineObject:
        self.create_box_calls.append(dict(kwargs))
        origin = cast(list[float], kwargs["origin"])
        sizes = cast(list[float], kwargs["sizes"])
        max_corner = [origin[0] + sizes[0], origin[1] + sizes[1], origin[2] + sizes[2]]
        obj = _FakePolylineObject(str(kwargs["name"]), [origin[:], max_corner])
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
        edge_keys = [
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
        obj.edges = []
        for first_key, second_key in edge_keys:
            obj.edge_ids.append(self._register_edge(corners[first_key], corners[second_key]))
            obj.edges.append(_FakeEdge(corners[first_key], corners[second_key]))
        self.objects[obj.name] = obj
        return obj

    def create_cylinder(self, **kwargs: object) -> _FakePolylineObject:
        self.create_cylinder_calls.append(dict(kwargs))
        origin = cast(list[float], kwargs["origin"])
        radius = float(cast(float, kwargs["radius"]))
        height = float(cast(float, kwargs["height"]))
        min_corner = [origin[0] - radius, origin[1] - radius, origin[2]]
        max_corner = [origin[0] + radius, origin[1] + radius, origin[2] + height]
        obj = _FakePolylineObject(str(kwargs["name"]), [min_corner, max_corner])
        obj.edges = [_FakeEdge(min_corner, max_corner)]
        self.objects[obj.name] = obj
        return obj

    def cover_lines(self, assignment: str) -> str:
        self.cover_lines_calls.append(assignment)
        return assignment

    def create_coordinate_system(
        self,
        origin=None,
        reference_cs: str = "Global",
        name: str | None = None,
        mode: str = "axis",
        view: str = "iso",
        x_pointing=None,
        y_pointing=None,
        psi: int = 0,
        theta: int = 0,
        phi: int = 0,
        u=None,
    ) -> _FakeCoordinateSystem:
        _ = reference_cs, mode, view, x_pointing, y_pointing, psi, theta, phi, u
        assert isinstance(origin, list)
        assert name is not None
        self.create_coordinate_system_calls.append({"origin": list(origin), "name": name})
        self.coordinate_system_origins[name] = list(origin)
        return _FakeCoordinateSystem(name)

    def set_working_coordinate_system(self, name: str) -> bool:
        self.set_working_coordinate_system_calls.append(name)
        assert name in self.coordinate_system_origins
        self.current_coordinate_system = name
        return True

    def thicken_sheet(self, assignment: str, thickness: float) -> _FakePolylineObject:
        self.thicken_sheet_calls.append((assignment, thickness))
        source = self.objects[assignment]
        min_x, min_y, min_z, max_x, max_y, max_z = source.bounding_box
        span_x = max_x - min_x
        span_y = max_y - min_y
        if span_x <= 1e-9:
            points = [
                [min_x, min_y, min_z],
                [min_x + thickness, max_y, max_z],
            ]
        elif span_y <= 1e-9:
            points = [
                [min_x, min_y, min_z],
                [max_x, min_y + thickness, max_z],
            ]
        else:
            points = [
                [min_x, min_y, min_z],
                [max_x, max_y, min_z + thickness],
            ]
        thickened = _FakePolylineObject(assignment, points)
        thickened.edge_ids = list(source.edge_ids)
        thickened.edges = list(source.edges)
        self.objects[assignment] = thickened
        return thickened

    def duplicate_and_mirror(
        self,
        assignment: str,
        origin: list[float],
        vector: list[float],
        duplicate_assignment: bool,
    ) -> list[str]:
        _ = origin, vector, duplicate_assignment
        return [f"{assignment}_mirror"]

    def subtract(self, *, blank_list: list[str], tool_list: list[str], keep_originals: bool) -> bool:
        self.subtract_calls.append(
            {
                "blank_list": list(blank_list),
                "tool_list": list(tool_list),
                "keep_originals": keep_originals,
            }
        )
        return True

    def get_object_faces(self, assignment: str) -> list[int]:
        self.get_object_faces_calls.append(assignment)
        return [1]

    def get_object_from_name(self, assignment: str) -> _FakePolylineObject:
        return self._ensure_object(assignment)

    def get_object_edges(self, assignment: str) -> list[int]:
        self.get_object_edges_calls.append(assignment)
        return list(self._ensure_object(assignment).edge_ids)

    def get_edge_vertices(self, assignment: int) -> list[int]:
        vertices = self.edge_vertices.get(int(assignment))
        if vertices is None:
            return []
        return [vertices[0], vertices[1]]

    def get_vertex_position(self, assignment: int) -> list[float]:
        return list(self.vertex_positions[int(assignment)])

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
            obj = self._ensure_object(name)
            if obj.points:
                obj.points = [_rotate_point(point) for point in obj.points]
                xs = [point[0] for point in obj.points]
                ys = [point[1] for point in obj.points]
                zs = [point[2] for point in obj.points]
                obj.bounding_box = [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
                obj.edges = [
                    _FakeEdge(obj.points[idx], obj.points[idx + 1]) for idx in range(max(0, len(obj.points) - 1))
                ]
            else:
                corners = [
                    [obj.bounding_box[0], obj.bounding_box[1], obj.bounding_box[2]],
                    [obj.bounding_box[0], obj.bounding_box[1], obj.bounding_box[5]],
                    [obj.bounding_box[0], obj.bounding_box[4], obj.bounding_box[2]],
                    [obj.bounding_box[0], obj.bounding_box[4], obj.bounding_box[5]],
                    [obj.bounding_box[3], obj.bounding_box[1], obj.bounding_box[2]],
                    [obj.bounding_box[3], obj.bounding_box[1], obj.bounding_box[5]],
                    [obj.bounding_box[3], obj.bounding_box[4], obj.bounding_box[2]],
                    [obj.bounding_box[3], obj.bounding_box[4], obj.bounding_box[5]],
                ]
                rotated_corners = [_rotate_point(point) for point in corners]
                xs = [point[0] for point in rotated_corners]
                ys = [point[1] for point in rotated_corners]
                zs = [point[2] for point in rotated_corners]
                obj.bounding_box = [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
        return True

    def unite(self, *, assignment: list[str]) -> str:
        self.unite_calls.append(list(assignment))
        merged = self._ensure_object(assignment[0])
        merged_bbox = list(merged.bounding_box)
        merged_has_edges = bool(merged.edge_ids)
        for name in assignment[1:]:
            other = self._ensure_object(name)
            merged.edge_ids.extend(other.edge_ids)
            merged.edges.extend(other.edges)
            if other.edge_ids:
                if not merged_has_edges:
                    merged_bbox = list(other.bounding_box)
                    merged_has_edges = True
                else:
                    merged_bbox[0] = min(merged_bbox[0], other.bounding_box[0])
                    merged_bbox[1] = min(merged_bbox[1], other.bounding_box[1])
                    merged_bbox[2] = min(merged_bbox[2], other.bounding_box[2])
                    merged_bbox[3] = max(merged_bbox[3], other.bounding_box[3])
                    merged_bbox[4] = max(merged_bbox[4], other.bounding_box[4])
                    merged_bbox[5] = max(merged_bbox[5], other.bounding_box[5])
        merged.bounding_box = merged_bbox
        self.objects[assignment[0]] = merged
        return assignment[0]


def _edge_midpoint(modeler: _FakeModeler, edge_id: int) -> tuple[float, float, float]:
    vertex_ids = modeler.get_edge_vertices(edge_id)
    first = modeler.get_vertex_position(vertex_ids[0])
    second = modeler.get_vertex_position(vertex_ids[1])
    return (
        (first[0] + second[0]) / 2.0,
        (first[1] + second[1]) / 2.0,
        (first[2] + second[2]) / 2.0,
    )


def _edge_points(modeler: _FakeModeler, edge_id: int) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    vertex_ids = modeler.get_edge_vertices(edge_id)
    first = modeler.get_vertex_position(vertex_ids[0])
    second = modeler.get_vertex_position(vertex_ids[1])
    return (
        (float(first[0]), float(first[1]), float(first[2])),
        (float(second[0]), float(second[1]), float(second[2])),
    )


class _FakeBoundaryModule:
    def __init__(self, parent: "_FakeHfss | None" = None) -> None:
        self._parent = parent
        self.auto_identify_ports_calls: list[dict[str, object]] = []
        self.assign_lumped_port_calls: list[dict[str, object]] = []
        self.boundary_names: list[str] = []

    def AutoIdentifyPorts(
        self,
        faces: list[object],
        is_wave_port: bool,
        reference_conductors: list[object],
        port_name: str,
        renormalize: bool,
    ) -> None:
        self.auto_identify_ports_calls.append(
            {
                "faces": list(faces),
                "is_wave_port": is_wave_port,
                "reference_conductors": list(reference_conductors),
                "port_name": port_name,
                "renormalize": renormalize,
            }
        )

    def AssignLumpedPort(self, props: list[object]) -> None:
        call: dict[str, object] = {
            "name": "",
            "edges": [],
            "lumped_port_type": "",
            "do_deembed": None,
            "renormalize_all_terminals": None,
            "show_reporter_filter": None,
            "impedance": None,
        }
        for index, item in enumerate(props):
            if isinstance(item, str) and item.startswith("NAME:"):
                call["name"] = item.removeprefix("NAME:")
            elif item == "Edges:=" and index + 1 < len(props):
                call["edges"] = list(cast(list[object], props[index + 1]))
            elif item == "LumpedPortType:=" and index + 1 < len(props):
                call["lumped_port_type"] = props[index + 1]
            elif item == "DoDeembed:=" and index + 1 < len(props):
                call["do_deembed"] = props[index + 1]
            elif item == "RenormalizeAllTerminals:=" and index + 1 < len(props):
                call["renormalize_all_terminals"] = props[index + 1]
            elif item == "ShowReporterFilter:=" and index + 1 < len(props):
                call["show_reporter_filter"] = props[index + 1]
            elif item == "Impedance:=" and index + 1 < len(props):
                call["impedance"] = props[index + 1]
        self.assign_lumped_port_calls.append(call)
        boundary_name = cast(str, call["name"])
        if boundary_name:
            self.boundary_names.append(boundary_name)
        if self._parent is None:
            return
        if self._parent.lumped_port_new_names_per_call:
            new_names = list(self._parent.lumped_port_new_names_per_call.pop(0))
        else:
            new_names = [f"{boundary_name}_T1"] if boundary_name else []
        self._parent.excitation_names.extend(new_names)

    def GetBoundaries(self) -> list[object]:
        raw: list[object] = []
        for boundary_name in self.boundary_names:
            raw.extend([boundary_name, "Lumped Port"])
        return raw


class _FakeHfss:
    def __init__(self) -> None:
        self.oboundary = _FakeBoundaryModule(self)
        self.save_project_calls: list[str] = []
        self.excitation_names: list[str] = []
        self.lumped_port_new_names_per_call: list[list[str]] = []

    def save_project(self, path: str) -> None:
        self.save_project_calls.append(path)


def _ctx_base(*, selected_pcbs: list[ResolvedPcbInstance]) -> GeometryRuntimeContext:
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
        selected_pcbs=selected_pcbs,
        group_geometry_by_kind=cast(
            dict[Literal["tx_dd", "tx_vertical", "rx_dd"], GroupGeometryParams],
            {"tx_dd": cast(GroupGeometryParams, {}), "tx_vertical": cast(GroupGeometryParams, {}), "rx_dd": cast(GroupGeometryParams, {})},
        ),
        tx_board_ids={pcb["id"] for pcb in selected_pcbs if pcb["role"] == "tx"},
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
        tx_vertical_orientation_mode=1,
        rx_face_clearance=0.0,
        tx_vertical_plane="ZX",
    )


def test_tx_vertical_builder_supports_one_turn() -> None:
    pcb = cast(
        ResolvedPcbInstance,
        {
            "id": "tx_vertical_0",
            "role": "tx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [{"kind": "tx_vertical", "selector_mode": "all", "selector_index": None}],
        },
    )
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.tx_vertical_region_min = (0.0, -10.0, 0.0)
    ctx.tx_vertical_region_max = (40.0, 10.0, 20.0)
    ctx.tx_vertical_center_x = 10.0
    ctx.tx_vertical_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_vertical", "requested_count": 1, "selected_count": 1, "spacing_mm": 0.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "tx_vertical", "turn_count": 1, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()

    build_tx_vertical_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=group,
        geometry=geometry,
        edge_points_at_tx_vertical_terminal=_edge_points_at_tx_vertical_terminal,
        edge_points_at_tx_vertical_opposite_terminal=_edge_points_at_tx_vertical_opposite_terminal,
        tx_vertical_bridge_edges_from_node=_tx_vertical_bridge_edges_from_node,
    )

    assert len(modeler.polyline_calls) == 1
    assert len(state.group_objects["tx_vertical"]) == 1
    assert len(state.group_endpoints) == 1
    assert state.placement_violations == []
    board_nodes = finalize_inputs.tx_vertical_nodes_by_board[("tx_vertical_0", 0)]
    assert len(board_nodes) == 1
    actual_points = cast(list[list[float]], modeler.polyline_calls[0]["points"])
    expected_terminal_edge = _edge_points_at_tx_vertical_terminal(
        points=actual_points,
        trace=1.0,
        plane="ZX",
        cu_thickness=ctx.cu_thickness,
    )
    expected_opposite_edge = _edge_points_at_tx_vertical_opposite_terminal(
        points=actual_points,
        trace=1.0,
        plane="ZX",
        cu_thickness=ctx.cu_thickness,
    )
    for expected_edge, actual_edge in (
        (expected_terminal_edge, board_nodes[0][7]),
        (expected_opposite_edge, board_nodes[0][8]),
    ):
        for expected_point, actual_point in zip(expected_edge, actual_edge, strict=True):
            for expected_axis, actual_axis in zip(expected_point, actual_point, strict=True):
                assert actual_axis == pytest.approx(expected_axis)
    assert board_nodes[0][6] == pytest.approx(cast(float, ctx.tx_vertical_center_x))
    assert finalize_inputs.tx_series_binding.series_entry is not None
    assert finalize_inputs.tx_series_binding.series_exit is not None
    assert finalize_inputs.tx_series_binding.series_entry["center"] == pytest.approx(
        (
            (board_nodes[0][8][0][0] + board_nodes[0][8][1][0]) / 2.0,
            (board_nodes[0][8][0][1] + board_nodes[0][8][1][1]) / 2.0,
            (board_nodes[0][8][0][2] + board_nodes[0][8][1][2]) / 2.0,
        )
    )
    assert finalize_inputs.tx_series_binding.series_exit["center"] == pytest.approx(
        (
            (board_nodes[0][7][0][0] + board_nodes[0][7][1][0]) / 2.0,
            (board_nodes[0][7][0][1] + board_nodes[0][7][1][1]) / 2.0,
            (board_nodes[0][7][0][2] + board_nodes[0][7][1][2]) / 2.0,
        )
    )
    assert finalize_inputs.tx_series_binding.series_entry["terminal_role"] == "series_entry"
    assert finalize_inputs.tx_series_binding.series_exit["terminal_role"] == "series_exit"
    assert finalize_inputs.tx_series_binding.series_entry["terminal_polarity"] == "positive"
    assert finalize_inputs.tx_series_binding.series_exit["terminal_polarity"] == "negative"


def test_tx_vertical_builder_skips_non_host_board_without_zx_series_capture() -> None:
    pcb = cast(
        ResolvedPcbInstance,
        {
            "id": "tx_main_0",
            "role": "tx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [{"kind": "tx_dd", "selector_mode": "index", "selector_index": 0}],
        },
    )
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.tx_vertical_region_min = (0.0, -10.0, 0.0)
    ctx.tx_vertical_region_max = (40.0, 10.0, 20.0)
    ctx.tx_vertical_center_x = 10.0
    ctx.tx_vertical_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_vertical", "requested_count": 3, "selected_count": 3, "spacing_mm": 5.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "tx_vertical", "turn_count": 1, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()

    build_tx_vertical_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=group,
        geometry=geometry,
        edge_points_at_tx_vertical_terminal=_edge_points_at_tx_vertical_terminal,
        edge_points_at_tx_vertical_opposite_terminal=_edge_points_at_tx_vertical_opposite_terminal,
        tx_vertical_bridge_edges_from_node=_tx_vertical_bridge_edges_from_node,
    )

    assert not state.group_objects["tx_vertical"]
    assert ("tx_main_0", 0) not in finalize_inputs.tx_vertical_nodes_by_board
    assert not state_is_set(finalize_inputs.tx_series_binding.series_entry)
    assert not state_is_set(finalize_inputs.tx_series_binding.series_exit)


def test_create_hfss_session_uses_manifest_ansys_path_and_avoids_project_rename_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    executable_path = tmp_path / "v252" / "AnsysEM" / "Linux64" / "ansysedt"
    executable_path.parent.mkdir(parents=True)
    executable_path.write_text("", encoding="utf-8")
    monkeypatch.delenv("ANSYSEM_ROOT252", raising=False)

    def _fake_hfss(*, project: str | None = None, design: str | None = None, non_graphical: bool | None = False, new_desktop: bool | None = False, **kwargs: object) -> object:
        calls.append(
            {
                "project": project,
                "design": design,
                "non_graphical": non_graphical,
                "new_desktop": new_desktop,
                "kwargs": kwargs,
            }
        )
        return object()

    monkeypatch.setattr(build_tx_vertical_module, "Hfss", _fake_hfss)

    manifest = cast(
        Manifest,
        {
            "spec": {"design_name": "demo_design"},
            "inputs": {
                "non_graphical": True,
                "ansys_executable_path": str(tmp_path / "v252" / "AnsysEM"),
            },
        },
    )

    build_tx_vertical_module.create_hfss_session(manifest, Path("/tmp/demo.aedt"))

    assert calls == [
        {
            "project": None,
            "design": "demo_design",
            "non_graphical": True,
            "new_desktop": True,
            "kwargs": {"version": "2025.2"},
        }
    ]
    assert os.environ["ANSYSEM_ROOT252"] == str(executable_path.parent)


def test_create_hfss_session_rejects_invalid_manifest_ansys_path(tmp_path: Path) -> None:
    manifest = cast(
        Manifest,
        {
            "spec": {"design_name": "demo_design"},
            "inputs": {
                "non_graphical": True,
                "ansys_executable_path": str(tmp_path / "missing" / "AnsysEM"),
            },
        },
    )

    with pytest.raises(ValueError, match=r"did not resolve to a valid AEDT executable"):
        build_tx_vertical_module.create_hfss_session(manifest, Path("/tmp/demo.aedt"))


def test_tx_vertical_builder_rejects_turn_count_above_three_even_if_feasible() -> None:
    pcb = cast(
        ResolvedPcbInstance,
        {
            "id": "tx_vertical_0",
            "role": "tx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [{"kind": "tx_vertical", "selector_mode": "all", "selector_index": None}],
        },
    )
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.tx_vertical_outer_x = 100.0
    ctx.tx_vertical_outer_y = 40.0
    ctx.tx_vertical_region_min = (0.0, -10.0, 0.0)
    ctx.tx_vertical_region_max = (140.0, 10.0, 60.0)
    ctx.tx_vertical_center_x = 50.0
    ctx.tx_vertical_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_vertical", "requested_count": 1, "selected_count": 1, "spacing_mm": 0.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "tx_vertical", "turn_count": 4, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()

    with pytest.raises(ValueError, match=r"selected_group_geometry\.tx_vertical\.turn_count must be <= 3"):
        build_tx_vertical_for_board(
            modeler=cast(Modeler3D, modeler),
            ctx=ctx,
            state=state,
            finalize_inputs=finalize_inputs,
            board_idx=0,
            pcb=pcb,
            group=group,
            geometry=geometry,
            edge_points_at_tx_vertical_terminal=_edge_points_at_tx_vertical_terminal,
            edge_points_at_tx_vertical_opposite_terminal=_edge_points_at_tx_vertical_opposite_terminal,
            tx_vertical_bridge_edges_from_node=_tx_vertical_bridge_edges_from_node,
        )


def test_tx_dd_builder_captures_legacy_zx_series_terminals_for_single_layer() -> None:
    pcb = cast(
        ResolvedPcbInstance,
        {
            "id": "tx_main_0",
            "role": "tx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
            ],
        },
    )
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.tx_dd_region_min = (0.0, -40.0, 0.0)
    ctx.tx_dd_region_max = (60.0, 40.0, 10.0)
    ctx.tx_dd_center_x = 30.0
    ctx.tx_dd_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_dd", "layer_count": 1, "spacing_mm": 10.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "tx_dd", "turn_count": 1, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()

    build_tx_dd_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=group,
        geometry=geometry,
        edge_points_at_path_end=_edge_points_at_path_end,
    )

    assert len(modeler.polyline_calls) == 1
    assert len(cast(list[list[float]], modeler.polyline_calls[0]["points"])) == 5
    assert len(state.group_endpoints) == 1
    endpoint = state.group_endpoints[0]
    assert endpoint["group_instance_index"] == 1
    assert endpoint["start_label"] == "D"
    assert endpoint["end_label"] == "d"
    start_stub_sources = finalize_inputs.txdd_start_stub_sources["tx_main_0"]
    assert len(start_stub_sources) == 2
    assert finalize_inputs.tx_series_binding.feed_in is not None
    assert finalize_inputs.tx_series_binding.feed_out is not None
    assert finalize_inputs.tx_series_binding.inter_half_exit is not None
    assert finalize_inputs.tx_series_binding.inter_half_entry is not None
    assert finalize_inputs.tx_series_binding.feed_in["terminal_role"] == "feed_in"
    assert finalize_inputs.tx_series_binding.feed_out["terminal_role"] == "feed_out"
    assert finalize_inputs.tx_series_binding.inter_half_exit["terminal_role"] == "inter_half_exit"
    assert finalize_inputs.tx_series_binding.inter_half_entry["terminal_role"] in {"inter_half_entry", "feed_in"}
    assert finalize_inputs.tx_series_binding.feed_in["terminal_polarity"] == "positive"
    assert finalize_inputs.tx_series_binding.feed_out["terminal_polarity"] == "negative"
    assert finalize_inputs.tx_series_binding.inter_half_exit["terminal_polarity"] == "negative"
    assert finalize_inputs.tx_series_binding.inter_half_entry["terminal_polarity"] == "positive"
    assert finalize_inputs.tx_series_binding.feed_in["center"] == start_stub_sources[0][0]
    assert finalize_inputs.tx_series_binding.feed_out["center"] == start_stub_sources[1][0]
    assert finalize_inputs.tx_series_binding.inter_half_exit["center"] == finalize_inputs.tx_series_binding.feed_out["center"]
    assert finalize_inputs.tx_series_binding.inter_half_entry["center"] == finalize_inputs.tx_series_binding.feed_in["center"]
    source_points = {cast(tuple[float, float, float], source[0]) for source in start_stub_sources}
    assert endpoint["start_xyz"] in source_points
    assert endpoint["end_xyz"] in source_points
    assert state.coil_polarity == [
        {
            "group_kind": "tx_dd",
            "group_instance_index": 1,
            "board_id": "tx_main_0",
            "dd_family": "tx_dd",
            "dd_pair_index": 0,
            "instance_side": "right",
            "current_direction": "ccw",
        }
    ]


def test_resolve_tx_vertical_zx_series_chain_landings_uses_cross_diagonal_order() -> None:
    tx_vertical_nodes_by_board = {
        ("tx_vertical_0", 0): [
            (
                0,
                "coil_tx_v_g0_b0_demo",
                (10.0, -30.0, 0.5),
                (20.0, -30.0, 0.5),
                -30.0,
                1.0,
                15.0,
                ((20.0, -30.0, 0.0), (20.0, -30.0, 1.0)),
                ((10.0, -30.0, 0.0), (10.0, -30.0, 1.0)),
            ),
            (
                2,
                "coil_tx_v_g2_b0_demo",
                (10.0, 30.0, 9.5),
                (20.0, 30.0, 9.5),
                30.0,
                1.0,
                15.0,
                ((20.0, 30.0, 9.0), (20.0, 30.0, 10.0)),
                ((10.0, 30.0, 9.0), (10.0, 30.0, 10.0)),
            ),
        ]
    }

    series_entry, series_exit = _resolve_tx_vertical_zx_series_chain_landings(tx_vertical_nodes_by_board)

    assert series_entry["center"] == pytest.approx((10.0, -30.0, 0.5))
    assert series_entry["terminal_role"] == "series_entry"
    assert series_entry["terminal_polarity"] == "positive"
    assert series_exit["center"] == pytest.approx((20.0, 30.0, 9.5))
    assert series_exit["terminal_role"] == "series_exit"
    assert series_exit["terminal_polarity"] == "negative"


def test_resolve_tx_vertical_zx_series_chain_landings_supports_single_node() -> None:
    tx_vertical_nodes_by_board = {
        ("tx_vertical_0", 0): [
            (
                0,
                "coil_tx_v_g0_b0_demo",
                (10.0, 0.0, 0.5),
                (20.0, 0.0, 0.5),
                0.0,
                1.0,
                15.0,
                ((20.0, 0.0, 0.0), (20.0, 0.0, 1.0)),
                ((10.0, 0.0, 0.0), (10.0, 0.0, 1.0)),
            )
        ]
    }

    series_entry, series_exit = _resolve_tx_vertical_zx_series_chain_landings(tx_vertical_nodes_by_board)

    assert series_entry["center"] == pytest.approx((10.0, 0.0, 0.5))
    assert series_entry["terminal_role"] == "series_entry"
    assert series_entry["terminal_polarity"] == "positive"
    assert series_exit["center"] == pytest.approx((20.0, 0.0, 0.5))
    assert series_exit["terminal_role"] == "series_exit"
    assert series_exit["terminal_polarity"] == "negative"


def test_complete_tx_series_chain_binding_rejects_same_sign_pairing() -> None:
    inputs = TxSeriesBindingInputs(
        feed_in=cast(
            DirectedLandingSection,
            {
                "p_plus": (0.0, 0.0, 0.0),
                "p_minus": (1.0, 0.0, 0.0),
                "center": (0.5, 0.0, 0.0),
                "outward_dir": (-1.0, 0.0, 0.0),
                "plane_normal": (0.0, 0.0, 1.0),
                "object_name": "feed_in",
                "dd_family": "tx_dd",
                "dd_pair_index": 0,
                "side": "right",
                "terminal_polarity": "positive",
                "terminal_role": "feed_in",
            },
        ),
        feed_out=cast(
            DirectedLandingSection,
            {
                "p_plus": (0.0, 0.0, 0.0),
                "p_minus": (1.0, 0.0, 0.0),
                "center": (0.5, 0.0, 0.0),
                "outward_dir": (-1.0, 0.0, 0.0),
                "plane_normal": (0.0, 0.0, 1.0),
                "object_name": "feed_out",
                "dd_family": "tx_dd",
                "dd_pair_index": 0,
                "side": "left",
                "terminal_polarity": "negative",
                "terminal_role": "feed_out",
            },
        ),
        inter_half_exit=cast(
            DirectedLandingSection,
            {
                "p_plus": (0.0, 0.0, 0.0),
                "p_minus": (1.0, 0.0, 0.0),
                "center": (0.5, 0.0, 0.0),
                "outward_dir": (-1.0, 0.0, 0.0),
                "plane_normal": (0.0, 0.0, 1.0),
                "object_name": "inter_exit",
                "dd_family": "tx_dd",
                "dd_pair_index": 0,
                "side": "right",
                "terminal_polarity": "negative",
                "terminal_role": "inter_half_exit",
            },
        ),
        inter_half_entry=cast(
            DirectedLandingSection,
            {
                "p_plus": (0.0, 0.0, 0.0),
                "p_minus": (1.0, 0.0, 0.0),
                "center": (0.5, 0.0, 0.0),
                "outward_dir": (-1.0, 0.0, 0.0),
                "plane_normal": (0.0, 0.0, 1.0),
                "object_name": "inter_entry",
                "dd_family": "tx_dd",
                "dd_pair_index": 0,
                "side": "left",
                "terminal_polarity": "positive",
                "terminal_role": "inter_half_entry",
            },
        ),
    )
    same_sign_series_entry = cast(
        DirectedLandingSection,
        {
            "p_plus": (0.0, 0.0, 0.0),
            "p_minus": (1.0, 0.0, 0.0),
            "center": (0.5, 0.0, 0.0),
            "outward_dir": (1.0, 0.0, 0.0),
            "plane_normal": (0.0, -1.0, 0.0),
            "object_name": "series_entry",
            "dd_family": "none",
            "dd_pair_index": None,
            "side": "left",
            "terminal_polarity": "negative",
            "terminal_role": "series_entry",
        },
    )
    series_exit = cast(
        DirectedLandingSection,
        {
            "p_plus": (0.0, 0.0, 0.0),
            "p_minus": (1.0, 0.0, 0.0),
            "center": (0.5, 0.0, 0.0),
            "outward_dir": (1.0, 0.0, 0.0),
            "plane_normal": (0.0, -1.0, 0.0),
            "object_name": "series_exit",
            "dd_family": "none",
            "dd_pair_index": None,
            "side": "right",
            "terminal_polarity": "negative",
            "terminal_role": "series_exit",
        },
    )

    with pytest.raises(ValueError, match="cross-sign pairing"):
        _complete_tx_series_chain_binding(
            inputs=inputs,
            series_entry=same_sign_series_entry,
            series_exit=series_exit,
        )


def test_complete_tx_series_chain_binding_uses_builder_captured_series_terminals_when_args_omitted() -> None:
    inputs = TxSeriesBindingInputs(
        feed_in=cast(
            DirectedLandingSection,
            {
                "p_plus": (0.0, 0.0, 0.0),
                "p_minus": (1.0, 0.0, 0.0),
                "center": (0.5, 0.0, 0.0),
                "outward_dir": (-1.0, 0.0, 0.0),
                "plane_normal": (0.0, 0.0, 1.0),
                "object_name": "feed_in",
                "dd_family": "tx_dd",
                "dd_pair_index": 0,
                "side": "right",
                "terminal_polarity": "positive",
                "terminal_role": "feed_in",
            },
        ),
        feed_out=cast(
            DirectedLandingSection,
            {
                "p_plus": (0.0, 0.0, 0.0),
                "p_minus": (1.0, 0.0, 0.0),
                "center": (0.5, 0.0, 0.0),
                "outward_dir": (-1.0, 0.0, 0.0),
                "plane_normal": (0.0, 0.0, 1.0),
                "object_name": "feed_out",
                "dd_family": "tx_dd",
                "dd_pair_index": 0,
                "side": "left",
                "terminal_polarity": "negative",
                "terminal_role": "feed_out",
            },
        ),
        inter_half_exit=cast(
            DirectedLandingSection,
            {
                "p_plus": (0.0, 0.0, 0.0),
                "p_minus": (1.0, 0.0, 0.0),
                "center": (0.5, 0.0, 0.0),
                "outward_dir": (-1.0, 0.0, 0.0),
                "plane_normal": (0.0, 0.0, 1.0),
                "object_name": "inter_exit",
                "dd_family": "tx_dd",
                "dd_pair_index": 0,
                "side": "right",
                "terminal_polarity": "negative",
                "terminal_role": "inter_half_exit",
            },
        ),
        inter_half_entry=cast(
            DirectedLandingSection,
            {
                "p_plus": (0.0, 0.0, 0.0),
                "p_minus": (1.0, 0.0, 0.0),
                "center": (0.5, 0.0, 0.0),
                "outward_dir": (-1.0, 0.0, 0.0),
                "plane_normal": (0.0, 0.0, 1.0),
                "object_name": "inter_entry",
                "dd_family": "tx_dd",
                "dd_pair_index": 0,
                "side": "left",
                "terminal_polarity": "positive",
                "terminal_role": "inter_half_entry",
            },
        ),
        series_entry=cast(
            DirectedLandingSection,
            {
                "p_plus": (2.0, 0.0, 0.0),
                "p_minus": (3.0, 0.0, 0.0),
                "center": (2.5, 0.0, 0.0),
                "outward_dir": (1.0, 0.0, 0.0),
                "plane_normal": (0.0, -1.0, 0.0),
                "object_name": "series_entry",
                "dd_family": "none",
                "dd_pair_index": None,
                "side": "left",
                "terminal_polarity": "positive",
                "terminal_role": "series_entry",
            },
        ),
        series_exit=cast(
            DirectedLandingSection,
            {
                "p_plus": (4.0, 0.0, 0.0),
                "p_minus": (5.0, 0.0, 0.0),
                "center": (4.5, 0.0, 0.0),
                "outward_dir": (1.0, 0.0, 0.0),
                "plane_normal": (0.0, -1.0, 0.0),
                "object_name": "series_exit",
                "dd_family": "none",
                "dd_pair_index": None,
                "side": "right",
                "terminal_polarity": "negative",
                "terminal_role": "series_exit",
            },
        ),
    )

    binding = _complete_tx_series_chain_binding(inputs=inputs)

    assert binding["series_entry"]["object_name"] == "series_entry"
    assert binding["series_exit"]["object_name"] == "series_exit"


def test_assert_legacy_zx_tx_series_chain_graph_rejects_split_conductors() -> None:
    binding = cast(
        TxSeriesChainBinding,
        {
            "feed_in": {
                "p_plus": (0.0, 0.0, 0.0),
                "p_minus": (1.0, 0.0, 0.0),
                "center": (0.5, 0.0, 0.0),
                "outward_dir": (-1.0, 0.0, 0.0),
                "plane_normal": (0.0, 0.0, 1.0),
                "object_name": "right_obj",
                "dd_family": "tx_dd",
                "dd_pair_index": 0,
                "side": "right",
                "terminal_polarity": "positive",
                "terminal_role": "feed_in",
            },
            "feed_out": {
                "p_plus": (0.0, 0.0, 0.0),
                "p_minus": (1.0, 0.0, 0.0),
                "center": (0.5, 0.0, 0.0),
                "outward_dir": (-1.0, 0.0, 0.0),
                "plane_normal": (0.0, 0.0, 1.0),
                "object_name": "left_obj",
                "dd_family": "tx_dd",
                "dd_pair_index": 0,
                "side": "left",
                "terminal_polarity": "negative",
                "terminal_role": "feed_out",
            },
            "inter_half_exit": {
                "p_plus": (0.0, 0.0, 0.0),
                "p_minus": (1.0, 0.0, 0.0),
                "center": (0.5, 0.0, 0.0),
                "outward_dir": (-1.0, 0.0, 0.0),
                "plane_normal": (0.0, 0.0, 1.0),
                "object_name": "right_obj",
                "dd_family": "tx_dd",
                "dd_pair_index": 0,
                "side": "right",
                "terminal_polarity": "negative",
                "terminal_role": "inter_half_exit",
            },
            "inter_half_entry": {
                "p_plus": (0.0, 0.0, 0.0),
                "p_minus": (1.0, 0.0, 0.0),
                "center": (0.5, 0.0, 0.0),
                "outward_dir": (-1.0, 0.0, 0.0),
                "plane_normal": (0.0, 0.0, 1.0),
                "object_name": "left_obj",
                "dd_family": "tx_dd",
                "dd_pair_index": 0,
                "side": "left",
                "terminal_polarity": "positive",
                "terminal_role": "inter_half_entry",
            },
            "series_entry": {
                "p_plus": (0.0, 0.0, 0.0),
                "p_minus": (1.0, 0.0, 0.0),
                "center": (0.5, 0.0, 0.0),
                "outward_dir": (1.0, 0.0, 0.0),
                "plane_normal": (0.0, -1.0, 0.0),
                "object_name": "txv_obj",
                "dd_family": "none",
                "dd_pair_index": None,
                "side": "left",
                "terminal_polarity": "positive",
                "terminal_role": "series_entry",
            },
            "series_exit": {
                "p_plus": (0.0, 0.0, 0.0),
                "p_minus": (1.0, 0.0, 0.0),
                "center": (0.5, 0.0, 0.0),
                "outward_dir": (1.0, 0.0, 0.0),
                "plane_normal": (0.0, -1.0, 0.0),
                "object_name": "txv_obj",
                "dd_family": "none",
                "dd_pair_index": None,
                "side": "right",
                "terminal_polarity": "negative",
                "terminal_role": "series_exit",
            },
        },
    )
    group_objects = cast(
        GroupObjects,
        {
            "tx_dd": ["right_obj", "left_obj"],
            "tx_vertical": ["txv_obj"],
            "rx_dd": [],
            "ferrite": [],
        },
    )

    with pytest.raises(ValueError, match="single connected TX conductor"):
        _assert_legacy_zx_tx_series_chain_graph(
            binding=binding,
            txdd_right_object_names={0: "right_obj"},
            group_objects=group_objects,
            txdd_port_owner_names_by_board={"tx_main_0": {"right_obj", "left_obj"}},
        )


def test_assert_stacked_tx_dd_half_conductors_closed_rejects_ununited_layers() -> None:
    with pytest.raises(ValueError, match="right half closure violation"):
        _assert_stacked_tx_dd_half_conductors_closed(
            txdd_right_a_points={0: ((0.0, 0.0, 0.0), 1.0), 1: ((0.0, 0.0, 1.0), 1.0)},
            txdd_right_object_names={0: "right_lower", 1: "right_upper"},
        )


def test_assert_tx_conductor_graph_common_rejects_extra_external_edges() -> None:
    with pytest.raises(ValueError, match="exactly 2 external TX feed terminal edges"):
        _assert_tx_conductor_graph_common(
            txdd_right_object_names={0: "unified"},
            group_objects=cast(
                GroupObjects,
                {"tx_dd": ["unified"], "tx_vertical": ["unified"], "rx_dd": [], "ferrite": []},
            ),
            txdd_port_owner_names_by_board={"tx_main_0": {"unified"}},
            txdd_start_stub_port_edges_by_board={"tx_main_0": [((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))]},
            context="tx graph:",
        )


def test_finalize_solids_rejects_single_layer_txdd_to_tx_vertical_section_bridge_fallback() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    group_objects = cast(
        GroupObjects,
        {
            "tx_dd": ["coil_txdd_right", "coil_txv"],
            "tx_vertical": ["coil_txv"],
            "rx_dd": [],
            "ferrite": [],
        },
    )
    object_names = ["coil_txdd_right", "coil_txv"]
    right_dd_section = cast(
        OrderedTerminalSection,
        {
            "p0": (2.0, 5.0, 6.0),
            "p1": (2.0, 5.0, 7.0),
            "center": (2.0, 5.0, 6.5),
            "tangent_out": (-1.0, 0.0, 0.0),
            "plane_normal": (0.0, 0.0, 1.0),
        },
    )
    tx_vertical_section = cast(
        OrderedTerminalSection,
        {
            "p0": (1.0, -5.0, 7.0),
            "p1": (1.0, -5.0, 6.0),
            "center": (1.0, -5.0, 6.5),
            "tangent_out": (1.0, 0.0, 0.0),
            "plane_normal": (1.0, 0.0, 0.0),
        },
    )
    right_dd_landing = cast(
        DirectedLandingSection,
        {
            "p_plus": right_dd_section["p0"],
            "p_minus": right_dd_section["p1"],
            "center": right_dd_section["center"],
            "outward_dir": (-1.0, 0.0, 0.0),
            "plane_normal": right_dd_section["plane_normal"],
            "object_name": "coil_txdd_right",
            "dd_family": "tx_dd",
            "dd_pair_index": 0,
            "side": "right",
            "terminal_polarity": "negative",
            "terminal_role": "inter_half_exit",
        },
    )
    tx_vertical_landing = cast(
        DirectedLandingSection,
        {
            "p_plus": tx_vertical_section["p0"],
            "p_minus": tx_vertical_section["p1"],
            "center": tx_vertical_section["center"],
            "outward_dir": (1.0, 0.0, 0.0),
            "plane_normal": (0.0, -1.0, 0.0),
            "object_name": "coil_txv",
            "dd_family": "none",
            "dd_pair_index": None,
            "side": "right",
            "terminal_polarity": "neutral",
            "terminal_role": "none",
        },
    )

    _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo_txdd_txv_no_stub_face_fallback.aedt"),
        design_id="demo_txdd_txv_no_stub_face_fallback",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        tx_board_ids=set(),
        tx_vertical_nodes_by_board={},
        tx_vertical_region_min=(0.0, -70.0, 0.0),
        tx_vertical_region_max=(30.0, 70.0, 30.0),
        txdd_right_a_points={},
        txdd_right_object_names={0: "coil_txdd_right"},
        txdd_start_stub_sources={},
        rxdd_back_stub_sources=[],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=[],
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        txdd_global_right_bridge_landing=right_dd_landing,
        txdd_global_right_bridge_section=right_dd_section,
        txdd_global_right_bridge_object_name="coil_txdd_right",
        txdd_global_right_d_edge=None,
        txdd_global_right_d_object_name=None,
        tx_vertical_global_outer_right_edge=cast(
            tuple[tuple[float, float, float], tuple[float, float, float]],
            (tx_vertical_section["p0"], tx_vertical_section["p1"]),
        ),
        tx_vertical_global_outer_right_landing=tx_vertical_landing,
        tx_vertical_global_outer_right_section=tx_vertical_section,
        tx_vertical_global_outer_left_edge=None,
        tx_series_binding=TxSeriesBindingInputs(inter_half_exit=right_dd_landing),
    )

    assert modeler.polyline_calls == []

def test_tx_dd_builder_supports_one_turn_and_keeps_distinct_terminals() -> None:
    pcb = cast(
        ResolvedPcbInstance,
        {
            "id": "tx_main_0",
            "role": "tx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
            ],
        },
    )
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.tx_dd_outer_x = 100.0
    ctx.tx_dd_outer_y = 60.0
    ctx.tx_dd_region_min = (0.0, -80.0, 0.0)
    ctx.tx_dd_region_max = (160.0, 80.0, 20.0)
    ctx.tx_dd_center_x = 50.0
    ctx.tx_dd_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_dd", "layer_count": 1, "spacing_mm": 0.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "tx_dd", "turn_count": 1, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()

    build_tx_dd_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=group,
        geometry=geometry,
        edge_points_at_path_end=_edge_points_at_path_end,
    )

    right_points = cast(list[list[float]], modeler.polyline_calls[0]["points"])
    assert len(right_points) == 5
    assert len(modeler.polyline_calls) == 1
    assert max(point[0] for point in right_points) > min(point[0] for point in right_points)
    assert max(point[1] for point in right_points) > min(point[1] for point in right_points)
    assert len(state.group_endpoints) == 1
    assert state.group_endpoints[0]["group_instance_index"] == 1
    assert state.group_endpoints[0]["start_label"] == "D"
    assert state.group_endpoints[0]["end_label"] == "d"
    start_stub_sources = finalize_inputs.txdd_start_stub_sources["tx_main_0"]
    assert len(start_stub_sources) == 2
    assert finalize_inputs.tx_series_binding.feed_in is not None
    assert finalize_inputs.tx_series_binding.feed_out is not None
    assert finalize_inputs.tx_series_binding.feed_in["center"] == start_stub_sources[0][0]
    assert finalize_inputs.tx_series_binding.feed_out["center"] == start_stub_sources[1][0]
    assert finalize_inputs.tx_series_binding.feed_in["center"] != finalize_inputs.tx_series_binding.feed_out["center"]
    assert state.coil_polarity == [
        {
            "group_kind": "tx_dd",
            "group_instance_index": 1,
            "board_id": "tx_main_0",
            "dd_family": "tx_dd",
            "dd_pair_index": 0,
            "instance_side": "right",
            "current_direction": "ccw",
        }
    ]


def test_tx_dd_one_turn_a_to_d_raises_when_compact_geometry_would_be_required() -> None:
    with pytest.raises(ValueError, match="compact one-turn geometry is unsupported"):
        _build_txdd_right_points_a_to_d_one_turn(
            base=[[0.0, 0.0, 0.0]],
            outer_x=2.0,
            outer_y=2.0,
            trace=1.0,
            gap=1.0,
        )


def test_tx_dd_builder_records_right_only_sources_for_stacked_four_layer_case() -> None:
    pcb = cast(
        ResolvedPcbInstance,
        {
            "id": "tx_main_0",
            "role": "tx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 2},
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 3},
            ],
        },
    )
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.tx_dd_outer_x = 100.0
    ctx.tx_dd_outer_y = 60.0
    ctx.tx_dd_region_min = (0.0, -80.0, 0.0)
    ctx.tx_dd_region_max = (160.0, 80.0, 20.0)
    ctx.tx_dd_center_x = 50.0
    ctx.tx_dd_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_dd", "layer_count": 2, "spacing_mm": 0.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "tx_dd", "turn_count": 2, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()

    build_tx_dd_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=group,
        geometry=geometry,
        edge_points_at_path_end=_edge_points_at_path_end,
    )

    board_sources = finalize_inputs.txdd_start_stub_sources["tx_main_0"]
    source_owner_counts = Counter(cast(str, source[2]) for source in board_sources)
    assert "tx_main_1" not in finalize_inputs.txdd_start_stub_sources
    assert len(board_sources) == 2
    assert source_owner_counts == Counter(
        {
            cast(str, finalize_inputs.txdd_right_object_names[0]): 1,
            cast(str, finalize_inputs.txdd_right_object_names[1]): 1,
        }
    )
    assert {
        (
            entry["group_instance_index"],
            entry["instance_side"],
            entry["current_direction"],
        )
        for entry in state.coil_polarity
    } == {
        (1, "right", "ccw"),
        (3, "right", "ccw"),
    }


def test_tx_dd_builder_names_stacked_center_protrusions_as_via_tabs_with_2w_length() -> None:
    pcbs = [
        cast(
            ResolvedPcbInstance,
            {
                "id": "tx_main_0",
                "role": "tx",
                "position": (0.0, 0.0, 0.0),
                "rotation_deg": 0.0,
                "present": True,
                "z_mode": "absolute",
                "z_relative_base_id": None,
                "z_delta_path": None,
                "mounts": [
                    {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
                    {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
                ],
            },
        ),
        cast(
            ResolvedPcbInstance,
            {
                "id": "tx_main_1",
                "role": "tx",
                "position": (0.0, 0.0, 4.0),
                "rotation_deg": 0.0,
                "present": True,
                "z_mode": "absolute",
                "z_relative_base_id": None,
                "z_delta_path": None,
                "mounts": [
                    {"kind": "tx_dd", "selector_mode": "index", "selector_index": 2},
                    {"kind": "tx_dd", "selector_mode": "index", "selector_index": 3},
                ],
            },
        ),
    ]
    ctx = _ctx_base(selected_pcbs=pcbs)
    ctx.tx_dd_outer_x = 100.0
    ctx.tx_dd_outer_y = 60.0
    ctx.tx_dd_region_min = (0.0, -80.0, 0.0)
    ctx.tx_dd_region_max = (160.0, 80.0, 20.0)
    ctx.tx_dd_center_x = 50.0
    ctx.tx_dd_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_dd", "layer_count": 2, "spacing_mm": 0.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "tx_dd", "turn_count": 2, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()

    for board_idx, pcb in enumerate(pcbs):
        build_tx_dd_for_board(
            modeler=cast(Modeler3D, modeler),
            ctx=ctx,
            state=state,
            finalize_inputs=finalize_inputs,
            board_idx=board_idx,
            pcb=pcb,
            group=group,
            geometry=geometry,
            edge_points_at_path_end=_edge_points_at_path_end,
        )

    via_tab_calls = [
        call
        for call in modeler.polyline_calls
        if "via_tab_" in cast(str, call["name"])
    ]
    via_tab_names = [cast(str, call["name"]) for call in via_tab_calls]
    assert any(name.endswith("via_tab_feed_in") for name in via_tab_names)
    assert any(name.endswith("via_tab_feed_out") for name in via_tab_names)
    assert via_tab_names.count("coil_tx_dd_g1_b0_demo_via_tab_a") == 1
    assert via_tab_names.count("coil_tx_dd_g3_b1_demo_via_tab_a") == 1
    for call in via_tab_calls:
        points = cast(list[list[float]], call["points"])
        assert math.dist(points[0], points[3]) == pytest.approx(2.0)


def test_finalize_solids_supports_one_turn_tx_dd_geometry() -> None:
    pcb = cast(
        ResolvedPcbInstance,
        {
            "id": "tx_main_0",
            "role": "tx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
            ],
        },
    )
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.tx_dd_outer_x = 100.0
    ctx.tx_dd_outer_y = 60.0
    ctx.tx_dd_region_min = (0.0, -80.0, 0.0)
    ctx.tx_dd_region_max = (160.0, 80.0, 20.0)
    ctx.tx_dd_center_x = 50.0
    ctx.tx_dd_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_dd", "layer_count": 1, "spacing_mm": 0.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "tx_dd", "turn_count": 1, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()
    hfss = _FakeHfss()

    build_tx_dd_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=group,
        geometry=geometry,
        edge_points_at_path_end=_edge_points_at_path_end,
    )

    _, _, ports, port_assignments = _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo_tx_one_turn.aedt"),
        design_id="demo_tx_one_turn",
        cu_thickness=ctx.cu_thickness,
        pcb_thickness=ctx.pcb_thickness,
        tx_board_ids={"tx_main_0"},
        tx_vertical_nodes_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(10.0, 10.0, 10.0),
        txdd_right_a_points=finalize_inputs.txdd_right_a_points,
        txdd_right_object_names=finalize_inputs.txdd_right_object_names,
        txdd_start_stub_sources=finalize_inputs.txdd_start_stub_sources,
        rxdd_back_stub_sources=[],
        group_objects=state.group_objects,
        object_names=state.object_names,
        cad_probe=state.cad_probe,
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        txdd_global_right_d_edge=None,
        txdd_global_right_d_object_name=None,
        tx_vertical_global_outer_right_edge=None,
        tx_vertical_global_outer_left_edge=None,
    )

    assert len(finalize_inputs.txdd_start_stub_sources["tx_main_0"]) == 2
    assert ports == {"tx": [], "rx": []}
    assert len(port_assignments["tx"]) == 0
    start_stub_sources = finalize_inputs.txdd_start_stub_sources["tx_main_0"]
    assert [cast(str, call["name"]) for call in modeler.create_box_calls[-2:]] == [
        f"txs_in_above_{_object_name_tag('demo_tx_one_turn')}",
        f"txs_out_below_{_object_name_tag('demo_tx_one_turn')}",
    ]
    by_name = {cast(str, call["name"]): cast(list[float], call["origin"]) for call in modeler.create_box_calls[-2:]}
    assert by_name[f"txs_out_below_{_object_name_tag('demo_tx_one_turn')}"][2] == pytest.approx(start_stub_sources[0][0][2] - 5.0)
    assert by_name[f"txs_in_above_{_object_name_tag('demo_tx_one_turn')}"][2] == pytest.approx(start_stub_sources[0][0][2])
    by_name_sizes = {cast(str, call["name"]): cast(list[float], call["sizes"]) for call in modeler.create_box_calls[-2:]}
    assert by_name_sizes[f"txs_out_below_{_object_name_tag('demo_tx_one_turn')}"][2] == pytest.approx(5.0)
    assert by_name_sizes[f"txs_in_above_{_object_name_tag('demo_tx_one_turn')}"][2] == pytest.approx(1.0)


def test_finalize_solids_creates_zx_tx_vertical_external_stubs() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    group_objects = cast(
        GroupObjects,
        {"tx_dd": [], "tx_vertical": ["coil_txv"], "rx_dd": [], "ferrite": []},
    )
    object_names = ["coil_txv"]
    right_section = cast(
        OrderedTerminalSection,
        {
            "p0": (10.0, 0.0, 6.5),
            "p1": (10.0, 0.0, 7.5),
            "center": (10.0, 0.0, 7.0),
            "tangent_out": (1.0, 0.0, 0.0),
            "plane_normal": (0.0, -1.0, 0.0),
        },
    )
    left_section = cast(
        OrderedTerminalSection,
        {
            "p0": (2.0, 0.0, 2.5),
            "p1": (2.0, 0.0, 3.5),
            "center": (2.0, 0.0, 3.0),
            "tangent_out": (1.0, 0.0, 0.0),
            "plane_normal": (0.0, -1.0, 0.0),
        },
    )

    _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo_tx_vertical_zx_stub.aedt"),
        design_id="demo_tx_vertical_zx_stub",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        tx_board_ids=set(),
        tx_vertical_nodes_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(20.0, 10.0, 20.0),
        txdd_right_a_points={},
        txdd_right_object_names={},
        txdd_start_stub_sources={},
        rxdd_back_stub_sources=[],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=[],
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        txdd_global_right_d_edge=None,
        txdd_global_right_d_object_name=None,
        tx_vertical_global_outer_right_edge=cast(tuple[tuple[float, float, float], tuple[float, float, float]], (right_section["p0"], right_section["p1"])),
        tx_vertical_global_outer_left_edge=cast(tuple[tuple[float, float, float], tuple[float, float, float]], (left_section["p0"], left_section["p1"])),
        tx_vertical_global_outer_right_section=right_section,
        tx_vertical_global_outer_left_section=left_section,
        tx_vertical_global_outer_right_landing=cast(
            DirectedLandingSection,
            {
                "p_plus": right_section["p0"],
                "p_minus": right_section["p1"],
                "center": right_section["center"],
                "outward_dir": (1.0, 0.0, 0.0),
                "plane_normal": right_section["plane_normal"],
                "object_name": "coil_txv",
                "dd_family": "none",
                "dd_pair_index": None,
                "side": "right",
                "terminal_polarity": "neutral",
                "terminal_role": "none",
            },
        ),
        tx_vertical_global_outer_left_landing=cast(
            DirectedLandingSection,
            {
                "p_plus": left_section["p0"],
                "p_minus": left_section["p1"],
                "center": left_section["center"],
                "outward_dir": (1.0, 0.0, 0.0),
                "plane_normal": left_section["plane_normal"],
                "object_name": "coil_txv",
                "dd_family": "none",
                "dd_pair_index": None,
                "side": "left",
                "terminal_polarity": "neutral",
                "terminal_role": "none",
            },
        ),
    )

    assert [cast(str, call["name"]) for call in modeler.create_box_calls[-2:]] == [
        f"txvs_in_{_object_name_tag('demo_tx_vertical_zx_stub')}",
        f"txvs_out_{_object_name_tag('demo_tx_vertical_zx_stub')}",
    ]
    assert cast(list[float], modeler.create_box_calls[-2]["origin"]) == pytest.approx([10.0, -0.0175, 6.5])
    assert cast(list[float], modeler.create_box_calls[-1]["origin"]) == pytest.approx([2.0, -1.0175, 2.5])
    assert cast(list[float], modeler.create_box_calls[-2]["sizes"]) == pytest.approx([1.0, 1.0, 1.0])
    assert cast(list[float], modeler.create_box_calls[-1]["sizes"]) == pytest.approx([1.0, 1.0, 1.0])


def test_finalize_solids_connects_stacked_tx_dd_right_half_with_hex_vias() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    for name, origin in (
        ("coil_txdd_right_lower", [0.0, 0.0, 0.0]),
        ("coil_txdd_right_upper", [1.0, 0.0, 0.0]),
    ):
        modeler.create_box(origin=origin, sizes=[1.0, 1.0, 0.1], name=name, material="copper")
    group_objects = cast(
        GroupObjects,
        {
            "tx_dd": [
                "coil_txdd_right_lower",
                "coil_txdd_right_upper",
            ],
            "tx_vertical": [],
            "rx_dd": [],
            "ferrite": [],
        },
    )
    object_names = list(group_objects["tx_dd"])
    txdd_right_object_names = {0: "coil_txdd_right_lower", 1: "coil_txdd_right_upper"}

    finalized_object_names, _, ports, port_assignments = _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo_tx_dd_stacked_close.aedt"),
        design_id="demo_tx_dd_stacked_close",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        via_diameter_mm=0.5,
        tx_board_ids=set(),
        tx_vertical_nodes_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(10.0, 10.0, 10.0),
        txdd_right_a_points={0: ((0.0, 0.0, 0.0), 1.0), 1: ((0.0, 0.0, 0.0), 1.0)},
        txdd_right_object_names=txdd_right_object_names,
        txdd_start_stub_sources={},
        rxdd_back_stub_sources=[],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=[],
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
    )

    assert len(set(txdd_right_object_names.values())) == 1
    assert sorted(set(finalized_object_names)) == sorted(set(group_objects["tx_dd"]))
    assert len(modeler.create_cylinder_calls) == 4
    assert all(cast(int, call["num_sides"]) == 6 for call in modeler.create_cylinder_calls)
    assert all(cast(float, call["radius"]) == pytest.approx(0.25) for call in modeler.create_cylinder_calls)
    assert [cast(str, call["name"]) for call in modeler.create_cylinder_calls] == [
        f"via_txdd_right_a_0_{_object_name_tag('demo_tx_dd_stacked_close')}",
        f"via_txdd_right_a_1_{_object_name_tag('demo_tx_dd_stacked_close')}",
        f"via_txdd_right_a_2_{_object_name_tag('demo_tx_dd_stacked_close')}",
        f"via_txdd_right_a_3_{_object_name_tag('demo_tx_dd_stacked_close')}",
    ]
    assert len(modeler.unite_calls) == 1
    assert ports == {"tx": [], "rx": []}
    assert port_assignments == {"tx": [], "rx": []}


def test_finalize_solids_compacts_tx_vertical_zx_bridge_names_for_long_design_id() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    group_objects = cast(
        GroupObjects,
        {
            "tx_dd": [],
            "tx_vertical": ["coil_txv_left", "coil_txv_right"],
            "rx_dd": [],
            "ferrite": [],
        },
    )
    object_names = list(group_objects["tx_vertical"])

    with patch(
        "peetsfea.backend.pyaedt.geometry.builders.build_finalize_ops._close_stacked_tx_dd_half_conductors_with_hex_vias",
        _noop_close_stacked_tx_dd_half_conductors_with_hex_vias,
    ):
        _finalize_solids_and_substrates_impl(
            modeler=cast(Modeler3D, modeler),
            hfss=cast(Hfss, hfss),
            aedt_path=Path("/tmp/demo_tx_vertical_name_budget.aedt"),
            design_id="demo_tx_vertical_zx_link_name_budget_repro_case_extra",
            cu_thickness=0.035,
            pcb_thickness=1.6,
            tx_board_ids=set(),
            tx_vertical_nodes_by_board={
                ("tx_vertical_0", 0): [
                    (
                        0,
                        "coil_txv_left",
                        (10.0, -5.0, 9.5),
                        (20.0, -5.0, 0.5),
                        -5.0,
                        1.0,
                        15.0,
                        ((20.0, -5.0175, 9.0), (20.0, -5.0175, 10.0)),
                        ((10.0, -5.0175, 0.0), (10.0, -5.0175, 1.0)),
                    ),
                    (
                        1,
                        "coil_txv_right",
                        (10.0, 5.0, 9.5),
                        (20.0, 5.0, 0.5),
                        5.0,
                        1.0,
                        15.0,
                        ((20.0, 4.9825, 9.0), (20.0, 4.9825, 10.0)),
                        ((10.0, 4.9825, 0.0), (10.0, 4.9825, 1.0)),
                    ),
                ]
            },
            tx_vertical_region_min=(0.0, -10.0, 0.0),
            tx_vertical_region_max=(30.0, 10.0, 20.0),
            txdd_right_a_points={},
            txdd_right_object_names={},
            txdd_start_stub_sources={},
            rxdd_back_stub_sources=[],
            group_objects=group_objects,
            object_names=object_names,
            cad_probe=[],
            placement_violations=[],
            coil_plane_bboxes=[],
            fr4_object_names=[],
            tx_vertical_fr4_names=[],
        )

    bridge_names = _created_call_names(modeler.polyline_calls)
    assert len(bridge_names) == 1
    _assert_names_fit_local_aedt_limit(bridge_names)
    assert bridge_names[0].startswith("bridge_tx_vertical_link_g0_to_g1_b0_")
    assert modeler.unite_calls == [["coil_txv_left", "coil_txv_right", bridge_names[0]]]
    assert group_objects["tx_vertical"] == ["coil_txv_left"]
    assert object_names == ["coil_txv_left"]


def test_finalize_solids_rejects_tx_vertical_mode1_link_when_inward_x_shift_is_ambiguous() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    group_objects = cast(
        GroupObjects,
        {
            "tx_dd": [],
            "tx_vertical": ["coil_txv_left", "coil_txv_right"],
            "rx_dd": [],
            "ferrite": [],
        },
    )
    object_names = list(group_objects["tx_vertical"])

    with pytest.raises(ValueError, match="edge midpoint x equals coil center x"):
        with patch(
            "peetsfea.backend.pyaedt.geometry.builders.build_finalize_ops._close_stacked_tx_dd_half_conductors_with_hex_vias",
            _noop_close_stacked_tx_dd_half_conductors_with_hex_vias,
        ):
            _finalize_solids_and_substrates_impl(
                modeler=cast(Modeler3D, modeler),
                hfss=cast(Hfss, hfss),
                aedt_path=Path("/tmp/demo_tx_vertical_zx_link_ambiguous_x.aedt"),
                design_id="demo_tx_vertical_zx_link_ambiguous_x",
                cu_thickness=0.035,
                pcb_thickness=1.6,
                tx_board_ids=set(),
                tx_vertical_nodes_by_board={
                    ("tx_vertical_0", 0): [
                        (
                            0,
                            "coil_txv_left",
                            (10.0, -5.0, 9.5),
                            (20.0, -5.0, 0.5),
                            -5.0,
                            1.0,
                            20.0,
                            ((20.0, -5.0175, 9.0), (20.0, -5.0175, 10.0)),
                            ((10.0, -5.0175, 0.0), (10.0, -5.0175, 1.0)),
                        ),
                        (
                            1,
                            "coil_txv_right",
                            (10.0, 5.0, 9.5),
                            (20.0, 5.0, 0.5),
                            5.0,
                            1.0,
                            10.0,
                            ((20.0, 4.9825, 9.0), (20.0, 4.9825, 10.0)),
                            ((10.0, 4.9825, 0.0), (10.0, 4.9825, 1.0)),
                        ),
                    ]
                },
                tx_vertical_region_min=(0.0, -10.0, 0.0),
                tx_vertical_region_max=(30.0, 10.0, 20.0),
                txdd_right_a_points={},
                txdd_right_object_names={},
                txdd_start_stub_sources={},
                rxdd_back_stub_sources=[],
                group_objects=group_objects,
                object_names=object_names,
                cad_probe=[],
                placement_violations=[],
                coil_plane_bboxes=[],
                fr4_object_names=[],
                tx_vertical_fr4_names=[],
            )


def test_finalize_solids_uses_single_hex_via_per_site_when_trace_is_thin() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    for name, origin in (
        ("coil_txdd_right_lower", [0.0, 0.0, 0.0]),
        ("coil_txdd_right_upper", [1.0, 0.0, 0.0]),
    ):
        modeler.create_box(origin=origin, sizes=[1.0, 1.0, 0.1], name=name, material="copper")
    group_objects = cast(
        GroupObjects,
        {
            "tx_dd": [
                "coil_txdd_right_lower",
                "coil_txdd_right_upper",
            ],
            "tx_vertical": [],
            "rx_dd": [],
            "ferrite": [],
        },
    )
    object_names = list(group_objects["tx_dd"])
    txdd_right_object_names = {0: "coil_txdd_right_lower", 1: "coil_txdd_right_upper"}

    finalized_object_names, _, ports, port_assignments = _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo_tx_dd_stacked_single_via.aedt"),
        design_id="demo_tx_dd_stacked_single_via",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        via_diameter_mm=0.5,
        tx_board_ids=set(),
        tx_vertical_nodes_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(10.0, 10.0, 10.0),
        txdd_right_a_points={0: ((0.0, 0.0, 0.0), 0.8), 1: ((0.0, 0.0, 0.0), 0.8)},
        txdd_right_object_names=txdd_right_object_names,
        txdd_start_stub_sources={},
        rxdd_back_stub_sources=[],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=[],
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
    )

    assert len(set(txdd_right_object_names.values())) == 1
    assert sorted(set(finalized_object_names)) == sorted(set(group_objects["tx_dd"]))
    assert len(modeler.create_cylinder_calls) == 1
    assert all(cast(int, call["num_sides"]) == 6 for call in modeler.create_cylinder_calls)
    assert all(cast(float, call["radius"]) == pytest.approx(0.25) for call in modeler.create_cylinder_calls)
    assert [cast(str, call["name"]) for call in modeler.create_cylinder_calls] == [
        f"via_txdd_right_a_0_{_object_name_tag('demo_tx_dd_stacked_single_via')}",
    ]
    assert len(modeler.unite_calls) == 1
    assert ports == {"tx": [], "rx": []}
    assert port_assignments == {"tx": [], "rx": []}

def test_finalize_solids_places_stacked_tx_dd_right_half_vias_between_copper_layers() -> None:
    pcbs = [
        cast(
            ResolvedPcbInstance,
            {
                "id": "tx_main_0",
                "role": "tx",
                "position": (0.0, 0.0, 0.0),
                "rotation_deg": 0.0,
                "present": True,
                "z_mode": "absolute",
                "z_relative_base_id": None,
                "z_delta_path": None,
                "mounts": [
                    {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
                    {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
                ],
            },
        ),
        cast(
            ResolvedPcbInstance,
            {
                "id": "tx_main_1",
                "role": "tx",
                "position": (0.0, 0.0, 4.0),
                "rotation_deg": 0.0,
                "present": True,
                "z_mode": "absolute",
                "z_relative_base_id": None,
                "z_delta_path": None,
                "mounts": [
                    {"kind": "tx_dd", "selector_mode": "index", "selector_index": 2},
                    {"kind": "tx_dd", "selector_mode": "index", "selector_index": 3},
                ],
            },
        ),
    ]
    ctx = _ctx_base(selected_pcbs=pcbs)
    ctx.tx_dd_outer_x = 100.0
    ctx.tx_dd_outer_y = 60.0
    ctx.tx_dd_region_min = (0.0, -80.0, 0.0)
    ctx.tx_dd_region_max = (160.0, 80.0, 20.0)
    ctx.tx_dd_center_x = 50.0
    ctx.tx_dd_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "tx_dd", "layer_count": 2, "spacing_mm": 0.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "tx_dd", "turn_count": 2, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()
    hfss = _FakeHfss()

    for board_idx, pcb in enumerate(pcbs):
        build_tx_dd_for_board(
            modeler=cast(Modeler3D, modeler),
            ctx=ctx,
            state=state,
            finalize_inputs=finalize_inputs,
            board_idx=board_idx,
            pcb=pcb,
            group=group,
            geometry=geometry,
            edge_points_at_path_end=_edge_points_at_path_end,
        )

    _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo_tx_dd_two_board_vias.aedt"),
        design_id="demo_tx_dd_two_board_vias",
        cu_thickness=ctx.cu_thickness,
        pcb_thickness=ctx.pcb_thickness,
        via_diameter_mm=0.5,
        tx_board_ids={"tx_main_0", "tx_main_1"},
        tx_vertical_nodes_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(10.0, 10.0, 10.0),
        txdd_right_a_points=finalize_inputs.txdd_right_a_points,
        txdd_right_object_names=finalize_inputs.txdd_right_object_names,
        txdd_start_stub_sources=finalize_inputs.txdd_start_stub_sources,
        rxdd_back_stub_sources=[],
        group_objects=state.group_objects,
        object_names=state.object_names,
        cad_probe=state.cad_probe,
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        coil_polarity=state.coil_polarity,
        dd_half_geometries=state.dd_half_geometries,
        txdd_global_right_bridge_landing=finalize_inputs.txdd_global_right_bridge_landing,
        txdd_global_right_bridge_edge=finalize_inputs.txdd_global_right_bridge_edge,
        txdd_global_right_bridge_section=finalize_inputs.txdd_global_right_bridge_section,
        txdd_global_right_bridge_object_name=finalize_inputs.txdd_global_right_bridge_object_name,
        txdd_global_right_d_edge=finalize_inputs.txdd_global_right_d_edge,
        txdd_global_right_d_object_name=finalize_inputs.txdd_global_right_d_object_name,
        txdd_global_right_bridge_anchor=finalize_inputs.txdd_global_right_bridge_anchor,
    )

    created_via_names = _created_call_names(modeler.create_cylinder_calls)
    assert any(name.startswith("via_txdd_right_a_") for name in created_via_names)
    lower_right_z = min(
        finalize_inputs.txdd_right_a_points[0][0][2],
        finalize_inputs.txdd_right_a_points[1][0][2],
    )
    right_calls = [call for call in modeler.create_cylinder_calls if cast(str, call["name"]).startswith("via_txdd_right_a_")]
    _assert_created_call_names_fit_local_aedt_limit(modeler.create_cylinder_calls)
    assert all(cast(list[float], call["origin"])[2] == pytest.approx(lower_right_z) for call in right_calls)
    tx_stub_names = _created_call_names(modeler.create_box_calls)
    assert tx_stub_names == [
        f"txs_in_above_{_object_name_tag('demo_tx_dd_two_board_vias')}",
        f"txs_in_above_{_object_name_tag('demo_tx_dd_two_board_vias')}",
    ]
    _assert_names_fit_local_aedt_limit(tx_stub_names)


def test_stub_center_from_anchor_shifts_box_center_inward_by_half_trace() -> None:
    assert _stub_center_from_anchor(
        anchor_xyz=(10.0, 20.0, 30.0),
        trace=1.0,
        inward_dir=(0.0, -1.0, 0.0),
    ) == pytest.approx((10.0, 19.5, 30.0))
    diagonal = 1.0 / math.sqrt(2.0)
    assert _stub_center_from_anchor(
        anchor_xyz=(10.0, 20.0, 30.0),
        trace=1.0,
        inward_dir=(-diagonal, -diagonal, 0.0),
    ) == pytest.approx((10.0 - (0.5 * diagonal), 20.0 - (0.5 * diagonal), 30.0))
    assert _stub_center_from_anchor(
        anchor_xyz=(10.0, 20.0, 30.0),
        trace=1.0,
        inward_dir=None,
    ) == pytest.approx((10.0, 20.0, 30.0))


def test_rx_dd_builder_supports_one_turn() -> None:
    pcb = cast(
        ResolvedPcbInstance,
        {
            "id": "rx_main_0",
            "role": "rx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [{"kind": "rx_dd", "selector_mode": "all", "selector_index": None}],
        },
    )
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.rx_region_min = (0.0, -30.0, 0.0)
    ctx.rx_region_max = (4.0, 30.0, 20.0)
    ctx.rx_center_y = 0.0
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    group = cast(
        ResolvedCoilGroup,
        {"kind": "rx_dd", "requested_count": 2, "selected_count": 2, "spacing_mm": 4.0, "instance_transforms": []},
    )
    geometry = cast(
        GroupGeometryParams,
        {"kind": "rx_dd", "turn_count": 1, "band_ratio": 0.2, "metal_ratio": 0.5, "trace": 1.0, "gap": 1.0},
    )
    modeler = _FakeModeler()

    build_rx_dd_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=group,
        geometry=geometry,
        append_rxdd_back_stub_sources_if_needed=_append_rxdd_back_stub_sources_if_needed,
    )

    assert len(modeler.polyline_calls) == 2
    assert len(state.group_objects["rx_dd"]) == 2
    assert len(state.group_endpoints) == 2
    assert len(finalize_inputs.rxdd_back_stub_sources) == 4
    assert all(len(source) == 7 for source in finalize_inputs.rxdd_back_stub_sources)
    assert all(
        abs(
            cast(
                tuple[str, int, str, tuple[float, float, float], float, str, tuple[float, float, float]],
                source,
            )[6][0]
        )
        <= 1e-12
        for source in finalize_inputs.rxdd_back_stub_sources
    )
    assert state.placement_violations == []


def test_back_connect_stub_pair_bridge_builds_minus_x_yz_sheet_for_rx_dd() -> None:
    modeler = _FakeModeler()
    group_objects = cast(
        GroupObjects,
        {"tx_dd": [], "tx_vertical": [], "rx_dd": ["coil_rx_left", "coil_rx_right"], "ferrite": []},
    )
    object_names = ["coil_rx_left", "coil_rx_right"]
    cad_probe: list[CadProbe] = []

    _apply_back_connect_stub_pair_bridge(
        modeler=cast(Modeler3D, modeler),
        design_id="demo",
        cu_thickness=0.035,
        sources=[
            ("board_0", 0, "B", (1.0, -6.0, 1.0), 1.0, "coil_rx_left", (0.0, 1.0, 0.0)),
            ("board_0", 0, "d", (1.0, 5.0, 8.0), 1.0, "coil_rx_right", (0.0, -1.0, 0.0)),
        ],
        endpoint_labels=("d", "B"),
        stub_length_mm=1.0,
        group_objects=group_objects,
        group_key="rx_dd",
        object_names=object_names,
        cad_probe=cad_probe,
        bridge_name="bridge_rx_dd_d_to_b_demo",
        stub_name_prefix="rxc",
        stub_error_context="rx_dd connect stub",
        bridge_error_context="rx_dd yz sheet bridge",
    )

    assert [call["name"] for call in modeler.create_box_calls] == ["rxc_board_0_0_B", "rxc_board_0_0_d"]
    first_attach_center = _rxdd_stub_attach_center_from_anchor(
        anchor_xyz=(1.0, -6.0, 1.0),
        trace=1.0,
        inward_dir=(0.0, 1.0, 0.0),
    )
    second_attach_center = _rxdd_stub_attach_center_from_anchor(
        anchor_xyz=(1.0, 5.0, 8.0),
        trace=1.0,
        inward_dir=(0.0, -1.0, 0.0),
    )
    assert cast(list[float], modeler.create_box_calls[0]["origin"]) == [0.0, first_attach_center[1] - 0.5, 0.5]
    assert cast(list[float], modeler.create_box_calls[0]["sizes"]) == [1.0, 1.0, 1.0]
    assert cast(list[float], modeler.create_box_calls[1]["origin"]) == [0.0, second_attach_center[1] - 0.5, 7.5]
    assert cast(list[float], modeler.create_box_calls[1]["sizes"]) == [1.0, 1.0, 1.0]
    bridge_points = cast(list[list[float]], modeler.polyline_calls[0]["points"])
    _assert_points_close(
        bridge_points,
        _rxdd_connect_sheet_points_from_anchor_pair(
            first_anchor_xyz=second_attach_center,
            second_anchor_xyz=first_attach_center,
            first_trace=1.0,
            second_trace=1.0,
            stub_length_mm=1.0,
        ),
    )
    assert modeler.unite_calls == [
        ["coil_rx_left", "rxc_board_0_0_B"],
        ["coil_rx_right", "rxc_board_0_0_d"],
        ["bridge_rx_dd_d_to_b_demo", "coil_rx_left", "coil_rx_right"],
    ]
    assert cad_probe[-1]["bbox"] == pytest.approx([0.0, -5.786731172181664, 0.5903840397404798, 0.14, 4.786731172181664, 8.40961596025952])


def test_rxdd_connect_landing_segment_is_trace_wide_and_midpoint_centered() -> None:
    segment = _rxdd_connect_landing_segment_from_anchor_pair(
        anchor_xyz=(1.0, 5.0, 8.0),
        peer_anchor_xyz=(1.0, -6.0, 1.0),
        trace=1.0,
        stub_length_mm=1.0,
    )

    midpoint = (
        (segment[0][0] + segment[1][0]) / 2.0,
        (segment[0][1] + segment[1][1]) / 2.0,
        (segment[0][2] + segment[1][2]) / 2.0,
    )
    assert midpoint == pytest.approx((0.0, 5.0, 8.0))
    assert math.dist(segment[0], segment[1]) == pytest.approx(1.0)


def test_rxdd_connect_sheet_points_keep_trace_width_and_deterministic_ordering() -> None:
    points = _rxdd_connect_sheet_points_from_anchor_pair(
        first_anchor_xyz=(1.0, 5.0, 8.0),
        second_anchor_xyz=(1.0, -6.0, 1.0),
        first_trace=1.0,
        second_trace=1.0,
        stub_length_mm=1.0,
    )

    _assert_points_close(
        points,
        [
            [0.0, 5.26843774609658, 7.578169256133946],
            [0.0, 4.73156225390342, 8.421830743866053],
            [0.0, -6.26843774609658, 1.4218307438660538],
            [0.0, -5.73156225390342, 0.5781692561339462],
        ],
    )


def test_rxdd_connect_sheet_points_fail_on_trace_mismatch() -> None:
    with pytest.raises(ValueError, match="trace mismatch"):
        _rxdd_connect_sheet_points_from_anchor_pair(
            first_anchor_xyz=(1.0, 5.0, 8.0),
            second_anchor_xyz=(1.0, -6.0, 1.0),
            first_trace=1.0,
            second_trace=2.0,
            stub_length_mm=1.0,
        )


def test_rxdd_connect_landing_segment_fails_on_zero_centerline() -> None:
    with pytest.raises(ValueError, match="centerline length must be > 0"):
        _rxdd_connect_landing_segment_from_anchor_pair(
            anchor_xyz=(1.0, 5.0, 8.0),
            peer_anchor_xyz=(1.0, 5.0, 8.0),
            trace=1.0,
            stub_length_mm=1.0,
        )


def _record_rx_port_back_face(
    *,
    design_id: str,
    board_id: str,
    instance_index: int,
    endpoint_label: str,
    origin: tuple[float, float, float],
) -> str:
    return record_rx_dd_port_stub_back_face(
        design_id=design_id,
        board_id=board_id,
        instance_index=instance_index,
        endpoint_label=endpoint_label,
        origin=origin,
        sizes=(3.0, 1.0, 1.0),
    )


def test_resolve_rx_dd_port_edges_from_back_faces_selects_y_side_for_y_dominant_gap() -> None:
    design_id = "rx_port_edge_y"
    reset_rx_stub_port_back_face_corners(design_id)
    signal_stub_key = _record_rx_port_back_face(
        design_id=design_id,
        board_id="rx_main",
        instance_index=1,
        endpoint_label="A",
        origin=(-2.0, 5.5, 8.5),
    )
    reference_stub_key = _record_rx_port_back_face(
        design_id=design_id,
        board_id="rx_main",
        instance_index=0,
        endpoint_label="c",
        origin=(-2.0, -5.5, 1.5),
    )

    signal_edge, reference_edge = resolve_rx_dd_port_edges_from_back_faces(
        design_id=design_id,
        signal_stub_key=signal_stub_key,
        reference_stub_key=reference_stub_key,
    )

    _assert_edge_close(signal_edge, ((-2.0, 5.5, 8.5), (-2.0, 5.5, 9.5)))
    _assert_edge_close(reference_edge, ((-2.0, -4.5, 1.5), (-2.0, -4.5, 2.5)))


def test_resolve_rx_dd_port_edges_from_back_faces_selects_z_side_for_z_dominant_gap() -> None:
    design_id = "rx_port_edge_z"
    reset_rx_stub_port_back_face_corners(design_id)
    signal_stub_key = _record_rx_port_back_face(
        design_id=design_id,
        board_id="rx_main",
        instance_index=1,
        endpoint_label="A",
        origin=(-2.0, 5.5, 8.5),
    )
    reference_stub_key = _record_rx_port_back_face(
        design_id=design_id,
        board_id="rx_main",
        instance_index=0,
        endpoint_label="c",
        origin=(-2.0, 5.9, 19.5),
    )

    signal_edge, reference_edge = resolve_rx_dd_port_edges_from_back_faces(
        design_id=design_id,
        signal_stub_key=signal_stub_key,
        reference_stub_key=reference_stub_key,
    )

    _assert_edge_close(signal_edge, ((-2.0, 5.5, 9.5), (-2.0, 6.5, 9.5)))
    _assert_edge_close(reference_edge, ((-2.0, 5.9, 19.5), (-2.0, 6.9, 19.5)))


def test_resolve_rx_dd_port_edges_from_back_faces_prefers_y_side_on_tie() -> None:
    design_id = "rx_port_edge_tie"
    reset_rx_stub_port_back_face_corners(design_id)
    signal_stub_key = _record_rx_port_back_face(
        design_id=design_id,
        board_id="rx_main",
        instance_index=1,
        endpoint_label="A",
        origin=(-2.0, 5.5, 8.5),
    )
    reference_stub_key = _record_rx_port_back_face(
        design_id=design_id,
        board_id="rx_main",
        instance_index=0,
        endpoint_label="c",
        origin=(-2.0, 6.5, 9.5),
    )

    signal_edge, reference_edge = resolve_rx_dd_port_edges_from_back_faces(
        design_id=design_id,
        signal_stub_key=signal_stub_key,
        reference_stub_key=reference_stub_key,
    )

    _assert_edge_close(signal_edge, ((-2.0, 6.5, 8.5), (-2.0, 6.5, 9.5)))
    _assert_edge_close(reference_edge, ((-2.0, 6.5, 9.5), (-2.0, 6.5, 10.5)))


def test_resolve_rx_dd_port_edges_from_back_faces_fails_on_zero_peer_offset() -> None:
    design_id = "rx_port_edge_zero"
    reset_rx_stub_port_back_face_corners(design_id)
    signal_stub_key = _record_rx_port_back_face(
        design_id=design_id,
        board_id="rx_main",
        instance_index=1,
        endpoint_label="A",
        origin=(-2.0, 5.5, 8.5),
    )
    reference_stub_key = _record_rx_port_back_face(
        design_id=design_id,
        board_id="rx_main",
        instance_index=0,
        endpoint_label="c",
        origin=(-2.0, 5.5, 8.5),
    )

    with pytest.raises(ValueError, match="peer direction must be non-zero"):
        resolve_rx_dd_port_edges_from_back_faces(
            design_id=design_id,
            signal_stub_key=signal_stub_key,
            reference_stub_key=reference_stub_key,
        )


def test_finalize_solids_routes_rx_port_over_a_to_c_and_pair_connector_over_d_to_b() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    group_objects = cast(
        GroupObjects,
        {"tx_dd": [], "tx_vertical": [], "rx_dd": ["coil_rx_left", "coil_rx_right"], "ferrite": []},
    )
    object_names = ["coil_rx_left", "coil_rx_right"]
    cad_probe: list[CadProbe] = []

    finalized_object_names, _, ports, port_assignments = _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo.aedt"),
        design_id="demo",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        tx_board_ids=set(),
        tx_vertical_nodes_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(10.0, 10.0, 10.0),
        txdd_right_a_points={},
        txdd_right_object_names={},
        txdd_start_stub_sources={},
        rxdd_back_stub_sources=[
            ("rx_main", 0, "B", (1.0, -6.0, 1.0), 1.0, "coil_rx_left"),
            ("rx_main", 0, "c", (1.0, -5.0, 2.0), 1.0, "coil_rx_left"),
            ("rx_main", 1, "A", (1.0, 6.0, 9.0), 1.0, "coil_rx_right"),
            ("rx_main", 1, "d", (1.0, 5.0, 8.0), 1.0, "coil_rx_right"),
        ],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=cad_probe,
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        txdd_global_right_d_edge=None,
        txdd_global_right_d_object_name=None,
        tx_vertical_global_outer_right_edge=None,
        tx_vertical_global_outer_left_edge=None,
    )

    assert [call["name"] for call in modeler.create_box_calls] == [
        "rxs_rx_main_0_c",
        "rxs_rx_main_1_A",
        "rxc_rx_main_0_B",
        "rxc_rx_main_1_d",
    ]
    assert cast(list[float], modeler.create_box_calls[2]["origin"]) == [0.0, -6.5, 0.5]
    assert cast(list[float], modeler.create_box_calls[2]["sizes"]) == [1.0, 1.0, 1.0]
    assert cast(list[float], modeler.create_box_calls[3]["origin"]) == [0.0, 4.5, 7.5]
    assert cast(list[float], modeler.create_box_calls[3]["sizes"]) == [1.0, 1.0, 1.0]
    _assert_points_close(
        cast(list[list[float]], modeler.polyline_calls[0]["points"]),
        _rxdd_connect_sheet_points_from_anchor_pair(
            first_anchor_xyz=(1.0, 5.0, 8.0),
            second_anchor_xyz=(1.0, -6.0, 1.0),
            first_trace=1.0,
            second_trace=1.0,
            stub_length_mm=1.0,
        ),
    )
    assert cast(str, modeler.polyline_calls[0]["name"]) == "bridge_rx_dd_d_to_b_demo"
    assert modeler.get_object_faces_calls == []
    rx_edges = cast(list[object], hfss.oboundary.assign_lumped_port_calls[0]["edges"])
    assert hfss.oboundary.assign_lumped_port_calls == [
        {
            "name": "1",
            "edges": hfss.oboundary.assign_lumped_port_calls[0]["edges"],
            "lumped_port_type": "Terminal",
            "do_deembed": False,
            "renormalize_all_terminals": True,
            "show_reporter_filter": False,
            "impedance": "50ohm",
        }
    ]
    assert ports == {"tx": [], "rx": ["1_T1"]}
    assert port_assignments == {
        "tx": [],
        "rx": [
            {
                "boundary_name": "1",
                "excitation_name": "1_T1",
                "signal_object_name": port_assignments["rx"][0]["signal_object_name"],
                "signal_edge_id": cast(int, rx_edges[0]),
                "reference_object_name": port_assignments["rx"][0]["reference_object_name"],
                "reference_edge_id": cast(int, rx_edges[1]),
            }
        ],
    }
    signal_edge_points = _normalize_edge_points(_edge_points(modeler, port_assignments["rx"][0]["signal_edge_id"]))
    reference_edge_points = _normalize_edge_points(_edge_points(modeler, port_assignments["rx"][0]["reference_edge_id"]))
    _assert_edge_close(signal_edge_points, ((-2.0, 5.5, 8.5), (-2.0, 5.5, 9.5)))
    _assert_edge_close(reference_edge_points, ((-2.0, -4.5, 1.5), (-2.0, -4.5, 2.5)))
    assert _edge_midpoint(modeler, port_assignments["rx"][0]["signal_edge_id"])[1] > 0.0
    assert _edge_midpoint(modeler, port_assignments["rx"][0]["reference_edge_id"])[1] < 0.0
    assert hfss.save_project_calls == ["/tmp/demo.aedt"]
    assert "bridge_rx_dd_d_to_b_demo" in finalized_object_names
    assert "sheet_rxdd_ports" not in finalized_object_names


def test_finalize_solids_keeps_rx_port_reference_on_c_stub_when_sources_are_reversed() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    group_objects = cast(
        GroupObjects,
        {"tx_dd": [], "tx_vertical": [], "rx_dd": ["coil_rx_left", "coil_rx_right"], "ferrite": []},
    )
    object_names = ["coil_rx_left", "coil_rx_right"]
    cad_probe: list[CadProbe] = []

    _, _, ports, port_assignments = _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo_reversed.aedt"),
        design_id="demo_reversed",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        tx_board_ids=set(),
        tx_vertical_nodes_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(10.0, 10.0, 10.0),
        txdd_right_a_points={},
        txdd_right_object_names={},
        txdd_start_stub_sources={},
        rxdd_back_stub_sources=[
            ("rx_main", 1, "d", (1.0, 5.0, 8.0), 1.0, "coil_rx_right"),
            ("rx_main", 1, "A", (1.0, 6.0, 9.0), 1.0, "coil_rx_right"),
            ("rx_main", 0, "c", (1.0, -5.0, 2.0), 1.0, "coil_rx_left"),
            ("rx_main", 0, "B", (1.0, -6.0, 1.0), 1.0, "coil_rx_left"),
        ],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=cad_probe,
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        txdd_global_right_d_edge=None,
        txdd_global_right_d_object_name=None,
        tx_vertical_global_outer_right_edge=None,
        tx_vertical_global_outer_left_edge=None,
    )

    assert len(hfss.oboundary.assign_lumped_port_calls) == 1
    assert ports == {"tx": [], "rx": ["1_T1"]}
    signal_edge_points = _normalize_edge_points(_edge_points(modeler, port_assignments["rx"][0]["signal_edge_id"]))
    reference_edge_points = _normalize_edge_points(_edge_points(modeler, port_assignments["rx"][0]["reference_edge_id"]))
    _assert_edge_close(signal_edge_points, ((-2.0, 5.5, 8.5), (-2.0, 5.5, 9.5)))
    _assert_edge_close(reference_edge_points, ((-2.0, -4.5, 1.5), (-2.0, -4.5, 2.5)))
    assert _edge_midpoint(modeler, port_assignments["rx"][0]["signal_edge_id"])[1] > 0.0
    assert _edge_midpoint(modeler, port_assignments["rx"][0]["reference_edge_id"])[1] < 0.0


def test_finalize_solids_skips_tx_port_without_semantic_binding() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    group_objects = cast(
        GroupObjects,
        {"tx_dd": ["coil_tx_right", "coil_tx_left"], "tx_vertical": [], "rx_dd": [], "ferrite": []},
    )
    object_names = ["coil_tx_right", "coil_tx_left"]
    cad_probe: list[CadProbe] = []

    finalized_object_names, _, ports, port_assignments = _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo_tx.aedt"),
        design_id="demo_tx",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        tx_board_ids={"tx_main_0"},
        tx_vertical_nodes_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(10.0, 10.0, 10.0),
        txdd_right_a_points={},
        txdd_right_object_names={},
        txdd_start_stub_sources={
            "tx_main_0": [
                ((10.0, 6.0, 9.0), 1.0, "coil_tx_right"),
                ((10.0, -6.0, 9.0), 1.0, "coil_tx_left"),
            ]
        },
        rxdd_back_stub_sources=[],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=cad_probe,
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        txdd_global_right_d_edge=None,
        txdd_global_right_d_object_name=None,
        tx_vertical_global_outer_right_edge=None,
        tx_vertical_global_outer_left_edge=None,
    )

    assert [call["name"] for call in modeler.create_box_calls] == [
        f"txs_in_above_{_object_name_tag('demo_tx')}",
        f"txs_out_below_{_object_name_tag('demo_tx')}",
    ]
    _assert_created_call_names_fit_local_aedt_limit(modeler.create_box_calls)
    assert modeler.get_object_faces_calls == []
    assert hfss.oboundary.assign_lumped_port_calls == []
    assert ports == {"tx": [], "rx": []}
    assert port_assignments == {"tx": [], "rx": []}
    assert hfss.save_project_calls == ["/tmp/demo_tx.aedt"]
    assert "sheet_txdd_ports_tx_main_0" not in finalized_object_names


def test_finalize_solids_orders_tx_stub_creation_by_geometry_not_creation_order_without_semantic_binding() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    group_objects = cast(
        GroupObjects,
        {"tx_dd": ["coil_tx_right", "coil_tx_left"], "tx_vertical": [], "rx_dd": [], "ferrite": []},
    )
    object_names = ["coil_tx_right", "coil_tx_left"]
    cad_probe: list[CadProbe] = []

    _, _, ports, port_assignments = _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo_tx_ordering.aedt"),
        design_id="demo_tx_ordering",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        tx_board_ids={"tx_main_0"},
        tx_vertical_nodes_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(10.0, 10.0, 10.0),
        txdd_right_a_points={},
        txdd_right_object_names={},
        txdd_start_stub_sources={
            "tx_main_0": [
                ((10.0, -6.0, 9.0), 1.0, "coil_tx_left"),
                ((10.0, 6.0, 9.0), 1.0, "coil_tx_right"),
            ]
        },
        rxdd_back_stub_sources=[],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=cad_probe,
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        txdd_global_right_d_edge=None,
        txdd_global_right_d_object_name=None,
        tx_vertical_global_outer_right_edge=None,
        tx_vertical_global_outer_left_edge=None,
    )

    assert [cast(str, call["name"]) for call in modeler.create_box_calls] == [
        f"txs_in_above_{_object_name_tag('demo_tx_ordering')}",
        f"txs_out_below_{_object_name_tag('demo_tx_ordering')}",
    ]
    assert ports == {"tx": [], "rx": []}
    assert port_assignments == {"tx": [], "rx": []}
    assert hfss.oboundary.assign_lumped_port_calls == []


def test_finalize_solids_assigns_txdd_in_out_stub_roles_from_semantic_feed_bindings() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    group_objects = cast(
        GroupObjects,
        {
            "tx_dd": ["coil_feed_out", "coil_left_start", "coil_feed_in", "coil_left_end"],
            "tx_vertical": [],
            "rx_dd": [],
            "ferrite": [],
        },
    )
    object_names = ["coil_feed_out", "coil_left_start", "coil_feed_in", "coil_left_end"]
    cad_probe: list[CadProbe] = []

    with patch(
        "peetsfea.backend.pyaedt.geometry.builders.finalize_stage_tx._create_tx_semantic_port_if_needed",
        autospec=True,
    ) as semantic_port_stage:
        _, _, ports, port_assignments = _finalize_solids_and_substrates_impl(
            modeler=cast(Modeler3D, modeler),
            hfss=cast(Hfss, hfss),
            aedt_path=Path("/tmp/demo_tx_semantic_stub_roles.aedt"),
            design_id="demo_tx_semantic_stub_roles",
            cu_thickness=0.035,
            pcb_thickness=1.6,
            tx_board_ids={"tx_main_0"},
            tx_vertical_nodes_by_board={},
            tx_vertical_region_min=(0.0, -10.0, 0.0),
            tx_vertical_region_max=(10.0, 10.0, 10.0),
            txdd_right_a_points={},
            txdd_right_object_names={},
            txdd_start_stub_sources={
                "tx_main_0": [
                    ((3.0, -6.0, 9.0), 1.0, "coil_feed_out"),
                    ((6.0, 3.0, 9.0), 1.0, "coil_left_start"),
                    ((6.0, -3.0, 9.0), 1.0, "coil_feed_in"),
                    ((3.0, 6.0, 9.0), 1.0, "coil_left_end"),
                ]
            },
            rxdd_back_stub_sources=[],
            group_objects=group_objects,
            object_names=object_names,
            cad_probe=cad_probe,
            placement_violations=[],
            coil_plane_bboxes=[],
            fr4_object_names=[],
            tx_vertical_fr4_names=[],
            txdd_global_right_d_edge=None,
            txdd_global_right_d_object_name=None,
            tx_vertical_global_outer_right_edge=None,
            tx_vertical_global_outer_left_edge=None,
            tx_series_binding=TxSeriesBindingInputs(
                feed_in=cast(
                    DirectedLandingSection,
                    {
                        "p_plus": (6.0, -2.5, 9.0),
                        "p_minus": (6.0, -3.5, 9.0),
                        "center": (6.0, -3.0, 9.0),
                        "outward_dir": (-1.0, 0.0, 0.0),
                        "plane_normal": (0.0, 0.0, 1.0),
                        "object_name": "coil_feed_in",
                        "dd_family": "tx_dd",
                        "dd_pair_index": 0,
                        "side": "right",
                        "terminal_polarity": "positive",
                        "terminal_role": "feed_in",
                    },
                ),
                feed_out=cast(
                    DirectedLandingSection,
                    {
                        "p_plus": (3.0, -5.5, 9.0),
                        "p_minus": (3.0, -6.5, 9.0),
                        "center": (3.0, -6.0, 9.0),
                        "outward_dir": (-1.0, 0.0, 0.0),
                        "plane_normal": (0.0, 0.0, 1.0),
                        "object_name": "coil_feed_out",
                        "dd_family": "tx_dd",
                        "dd_pair_index": 0,
                        "side": "right",
                        "terminal_polarity": "negative",
                        "terminal_role": "feed_out",
                    },
                ),
            ),
        )

    created_origins = {
        cast(str, call["name"]): cast(list[float], call["origin"])
        for call in modeler.create_box_calls
        if str(cast(str, call["name"])).startswith("txs_")
    }
    assert created_origins[f"txs_in_below_{_object_name_tag('demo_tx_semantic_stub_roles')}"] == pytest.approx(
        [5.5, -3.5, 4.0]
    )
    assert created_origins[f"txs_out_above_{_object_name_tag('demo_tx_semantic_stub_roles')}"] == pytest.approx(
        [2.5, -6.5, 9.0]
    )
    assert semantic_port_stage.call_count == 1
    assert ports == {"tx": [], "rx": []}
    assert port_assignments == {"tx": [], "rx": []}


@pytest.mark.parametrize(
    ("new_names", "match_text"),
    [
        ([], "must create exactly one new excitation"),
        (["1_T1", "2_T1"], "must create exactly one new excitation"),
    ],
)
def test_finalize_solids_does_not_attempt_tx_port_capture_without_semantic_binding(
    new_names: list[str],
    match_text: str,
) -> None:
    _ = match_text
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    hfss.lumped_port_new_names_per_call = [new_names]
    group_objects = cast(
        GroupObjects,
        {"tx_dd": ["coil_tx_right", "coil_tx_left"], "tx_vertical": [], "rx_dd": [], "ferrite": []},
    )
    object_names = ["coil_tx_right", "coil_tx_left"]
    cad_probe: list[CadProbe] = []

    _, _, ports, port_assignments = _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/demo_tx_fail.aedt"),
        design_id="demo_tx_fail",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        tx_board_ids={"tx_main_0"},
        tx_vertical_nodes_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(10.0, 10.0, 10.0),
        txdd_right_a_points={},
        txdd_right_object_names={},
        txdd_start_stub_sources={
            "tx_main_0": [
                ((10.0, 6.0, 9.0), 1.0, "coil_tx_right"),
                ((10.0, -6.0, 9.0), 1.0, "coil_tx_left"),
            ]
        },
        rxdd_back_stub_sources=[],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=cad_probe,
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        txdd_global_right_d_edge=None,
        txdd_global_right_d_object_name=None,
        tx_vertical_global_outer_right_edge=None,
        tx_vertical_global_outer_left_edge=None,
    )

    assert ports == {"tx": [], "rx": []}
    assert port_assignments == {"tx": [], "rx": []}
    assert hfss.oboundary.assign_lumped_port_calls == []
    assert hfss.lumped_port_new_names_per_call == [new_names]

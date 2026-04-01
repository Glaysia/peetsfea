from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from peetsfea.aedt import Hfss
from peetsfea.aedt import Modeler3D

from peetsfea.backend.pyaedt.geometry.builders.build_artifacts import (
    _finalize_solids_and_substrates_impl,
    _find_matching_tx_stub_bottom_edge_id,
)
from peetsfea.backend.pyaedt.geometry.builders.build_port_ops import (
    _create_terminal_lumped_port_and_capture_assignment_from_edge_ids,
    _required_numeric_port_name_for_role,
)
from peetsfea.backend.pyaedt.geometry.build_state import (
    DirectedLandingSection,
    TxSeriesBindingInputs,
    _unset_directed_landing_section,
    _unset_tx_series_binding,
)
from peetsfea.types.manifest import CadProbe, GroupObjects


class _FakeObject:
    def __init__(self, name: str, points: list[list[float]]) -> None:
        self.name = name
        self.points = [point[:] for point in points]
        if points:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            zs = [point[2] for point in points]
            self.bounding_box = [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
        else:
            self.bounding_box = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.edge_ids: list[int] = []
        self.edges: list[_FakeEdge] = []
        self.face_ids: list[int] = []


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


class _FakeModeler:
    def __init__(self) -> None:
        self.create_box_calls: list[dict[str, object]] = []
        self.objects: dict[str, _FakeObject] = {}
        self.edge_vertices: dict[int, tuple[int, int]] = {}
        self.vertex_positions: dict[int, list[float]] = {}
        self.face_edges: dict[int, list[int]] = {}
        self.face_vertices: dict[int, list[int]] = {}
        self.face_centers: dict[int, list[float]] = {}
        self.face_areas: dict[int, float] = {}
        self.unite_calls: list[list[str]] = []
        self.next_edge_id = 1
        self.next_vertex_id = 1
        self.next_face_id = 1

    def _register_vertex(self, position: list[float]) -> int:
        vertex_id = self.next_vertex_id
        self.next_vertex_id += 1
        self.vertex_positions[vertex_id] = list(position)
        return vertex_id

    def _register_edge(self, first: list[float], second: list[float]) -> int:
        edge_id = self.next_edge_id
        self.next_edge_id += 1
        self.edge_vertices[edge_id] = (self._register_vertex(first), self._register_vertex(second))
        return edge_id

    def _register_face(
        self,
        *,
        obj: _FakeObject,
        vertex_ids: list[int],
        edge_ids: list[int],
        center: list[float],
        area: float,
    ) -> None:
        face_id = self.next_face_id
        self.next_face_id += 1
        self.face_vertices[face_id] = list(vertex_ids)
        self.face_edges[face_id] = list(edge_ids)
        self.face_centers[face_id] = list(center)
        self.face_areas[face_id] = float(area)
        obj.face_ids.append(face_id)

    def _ensure_object(self, name: str) -> _FakeObject:
        obj = self.objects.get(name)
        if obj is None:
            obj = _FakeObject(name, [])
            self.objects[name] = obj
        return obj

    def create_box(self, **kwargs: object) -> _FakeObject:
        self.create_box_calls.append(dict(kwargs))
        origin = cast(list[float], kwargs["origin"])
        sizes = cast(list[float], kwargs["sizes"])
        max_corner = [origin[0] + sizes[0], origin[1] + sizes[1], origin[2] + sizes[2]]
        obj = _FakeObject(str(kwargs["name"]), [origin[:], max_corner])
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
        edge_ids_by_key: dict[tuple[str, str], int] = {}
        for first_key, second_key in edge_keys:
            edge_id = self._register_edge(corners[first_key], corners[second_key])
            self.edge_vertices[edge_id] = (corner_vertex_ids[first_key], corner_vertex_ids[second_key])
            obj.edge_ids.append(edge_id)
            edge_ids_by_key[(first_key, second_key)] = edge_id
            edge_ids_by_key[(second_key, first_key)] = edge_id
            obj.edges.append(_FakeEdge(corners[first_key], corners[second_key]))
        self._register_face(
            obj=obj,
            vertex_ids=[corner_vertex_ids[key] for key in ("000", "100", "110", "010")],
            edge_ids=[edge_ids_by_key[key] for key in (("000", "100"), ("100", "110"), ("110", "010"), ("010", "000"))],
            center=[(origin[0] + max_corner[0]) / 2.0, (origin[1] + max_corner[1]) / 2.0, origin[2]],
            area=sizes[0] * sizes[1],
        )
        self._register_face(
            obj=obj,
            vertex_ids=[corner_vertex_ids[key] for key in ("001", "101", "111", "011")],
            edge_ids=[edge_ids_by_key[key] for key in (("001", "101"), ("101", "111"), ("111", "011"), ("011", "001"))],
            center=[(origin[0] + max_corner[0]) / 2.0, (origin[1] + max_corner[1]) / 2.0, max_corner[2]],
            area=sizes[0] * sizes[1],
        )
        self._register_face(
            obj=obj,
            vertex_ids=[corner_vertex_ids[key] for key in ("000", "100", "101", "001")],
            edge_ids=[edge_ids_by_key[key] for key in (("000", "100"), ("100", "101"), ("101", "001"), ("001", "000"))],
            center=[(origin[0] + max_corner[0]) / 2.0, origin[1], (origin[2] + max_corner[2]) / 2.0],
            area=sizes[0] * sizes[2],
        )
        self._register_face(
            obj=obj,
            vertex_ids=[corner_vertex_ids[key] for key in ("010", "110", "111", "011")],
            edge_ids=[edge_ids_by_key[key] for key in (("010", "110"), ("110", "111"), ("111", "011"), ("011", "010"))],
            center=[(origin[0] + max_corner[0]) / 2.0, max_corner[1], (origin[2] + max_corner[2]) / 2.0],
            area=sizes[0] * sizes[2],
        )
        self._register_face(
            obj=obj,
            vertex_ids=[corner_vertex_ids[key] for key in ("000", "010", "011", "001")],
            edge_ids=[edge_ids_by_key[key] for key in (("000", "010"), ("010", "011"), ("011", "001"), ("001", "000"))],
            center=[origin[0], (origin[1] + max_corner[1]) / 2.0, (origin[2] + max_corner[2]) / 2.0],
            area=sizes[1] * sizes[2],
        )
        self._register_face(
            obj=obj,
            vertex_ids=[corner_vertex_ids[key] for key in ("100", "110", "111", "101")],
            edge_ids=[edge_ids_by_key[key] for key in (("100", "110"), ("110", "111"), ("111", "101"), ("101", "100"))],
            center=[max_corner[0], (origin[1] + max_corner[1]) / 2.0, (origin[2] + max_corner[2]) / 2.0],
            area=sizes[1] * sizes[2],
        )
        self.objects[obj.name] = obj
        return obj

    def get_object_edges(self, assignment: str) -> list[int]:
        return list(self._ensure_object(assignment).edge_ids)

    def get_object_faces(self, assignment: str) -> list[int]:
        return list(self._ensure_object(assignment).face_ids)

    def get_face_edges(self, assignment: int) -> list[int]:
        return list(self.face_edges[int(assignment)])

    def get_face_vertices(self, assignment: int) -> list[int]:
        return list(self.face_vertices[int(assignment)])

    def get_face_center(self, assignment: int) -> list[float]:
        return list(self.face_centers[int(assignment)])

    def get_face_area(self, assignment: int) -> float:
        return float(self.face_areas[int(assignment)])

    def get_edge_vertices(self, assignment: int) -> list[int]:
        vertices = self.edge_vertices.get(int(assignment))
        if vertices is None:
            return []
        return [vertices[0], vertices[1]]

    def get_vertex_position(self, assignment: int) -> list[float]:
        return list(self.vertex_positions[int(assignment)])

    def unite(self, *, assignment: list[str]) -> str:
        self.unite_calls.append(list(assignment))
        merged = self._ensure_object(assignment[0])
        for name in assignment[1:]:
            other = self._ensure_object(name)
            merged.edge_ids.extend(other.edge_ids)
            merged.edges.extend(other.edges)
            merged.face_ids.extend(other.face_ids)
        self.objects[assignment[0]] = merged
        return assignment[0]

    def subtract(self, *, blank_list: list[str], tool_list: list[str], keep_originals: bool) -> bool:
        _ = blank_list, tool_list, keep_originals
        return True


class _FakeBoundaryModule:
    def __init__(self, parent: "_FakeHfss") -> None:
        self._parent = parent
        self.assign_lumped_port_calls: list[dict[str, object]] = []
        self.boundary_names: list[str] = []

    def AssignLumpedPort(self, props: list[object]) -> None:
        call: dict[str, object] = {"name": "", "edges": []}
        for index, item in enumerate(props):
            if isinstance(item, str) and item.startswith("NAME:"):
                call["name"] = item.removeprefix("NAME:")
            elif item == "Edges:=" and index + 1 < len(props):
                call["edges"] = list(cast(list[object], props[index + 1]))
        self.assign_lumped_port_calls.append(call)
        boundary_name = cast(str, call["name"])
        if boundary_name:
            self.boundary_names.append(boundary_name)
            self._parent.excitation_names.append(f"{boundary_name}_T1")

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
        self.save_project_result: bool | None = None

    def save_project(self, path: str) -> bool | None:
        self.save_project_calls.append(path)
        return self.save_project_result


def test_required_numeric_port_name_for_role_uses_tx_1_and_rx_2() -> None:
    hfss = _FakeHfss()

    assert _required_numeric_port_name_for_role(hfss=cast(Hfss, hfss), role="tx") == "1"
    hfss.excitation_names.append("1_T1")
    assert _required_numeric_port_name_for_role(hfss=cast(Hfss, hfss), role="rx") == "2"


def test_required_numeric_port_name_for_role_raises_on_fixed_name_conflict() -> None:
    hfss = _FakeHfss()
    hfss.excitation_names.append("2_T1")

    with pytest.raises(ValueError, match=r"rx semantic port requires fixed numeric boundary name 2"):
        _required_numeric_port_name_for_role(hfss=cast(Hfss, hfss), role="rx")


def test_create_terminal_lumped_port_uses_tx_1_then_rx_2() -> None:
    hfss = _FakeHfss()

    tx_assignment = _create_terminal_lumped_port_and_capture_assignment_from_edge_ids(
        hfss=cast(Hfss, hfss),
        signal_object_name="tx_obj",
        signal_edge_id=11,
        reference_object_name="tx_obj",
        reference_edge_id=12,
        role="tx",
        context="tx test port",
    )
    rx_assignment = _create_terminal_lumped_port_and_capture_assignment_from_edge_ids(
        hfss=cast(Hfss, hfss),
        signal_object_name="rx_obj",
        signal_edge_id=21,
        reference_object_name="rx_obj",
        reference_edge_id=22,
        role="rx",
        context="rx test port",
    )

    assert tx_assignment["boundary_name"] == "1"
    assert tx_assignment["excitation_name"] == "1_T1"
    assert rx_assignment["boundary_name"] == "2"
    assert rx_assignment["excitation_name"] == "2_T1"


def _edge_points(modeler: _FakeModeler, edge_id: int) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    vertex_ids = modeler.get_edge_vertices(edge_id)
    first = modeler.get_vertex_position(vertex_ids[0])
    second = modeler.get_vertex_position(vertex_ids[1])
    return (
        (float(first[0]), float(first[1]), float(first[2])),
        (float(second[0]), float(second[1]), float(second[2])),
    )


def _make_terminal(
    *,
    center: tuple[float, float, float],
    trace: float,
    object_name: str,
    terminal_polarity: str,
    terminal_role: str,
    side: str,
) -> DirectedLandingSection:
    half_trace = trace / 2.0
    return cast(
        DirectedLandingSection,
        {
            "p_plus": (center[0], center[1] + half_trace, center[2]),
            "p_minus": (center[0], center[1] - half_trace, center[2]),
            "center": center,
            "outward_dir": (1.0, 0.0, 0.0),
            "plane_normal": (0.0, -1.0, 0.0),
            "object_name": object_name,
            "dd_family": "tx_dd",
            "dd_pair_index": 0,
            "side": side,
            "terminal_polarity": terminal_polarity,
            "terminal_role": terminal_role,
        },
    )


def _binding_for_single_conductor(*, object_name: str) -> TxSeriesBindingInputs:
    return TxSeriesBindingInputs(
        feed_in=_make_terminal(
            center=(10.0, 6.0, 9.0),
            trace=1.0,
            object_name=object_name,
            terminal_polarity="positive",
            terminal_role="feed_in",
            side="right",
        ),
        feed_out=_make_terminal(
            center=(10.0, -6.0, 9.0),
            trace=1.0,
            object_name=object_name,
            terminal_polarity="negative",
            terminal_role="feed_out",
            side="left",
        ),
        inter_half_exit=_make_terminal(
            center=(5.0, 3.0, 9.0),
            trace=1.0,
            object_name=object_name,
            terminal_polarity="positive",
            terminal_role="inter_half_exit",
            side="right",
        ),
        inter_half_entry=_make_terminal(
            center=(5.0, -3.0, 9.0),
            trace=1.0,
            object_name=object_name,
            terminal_polarity="negative",
            terminal_role="inter_half_entry",
            side="left",
        ),
        series_entry=_make_terminal(
            center=(6.0, 1.0, 9.0),
            trace=1.0,
            object_name=object_name,
            terminal_polarity="negative",
            terminal_role="series_entry",
            side="right",
        ),
        series_exit=_make_terminal(
            center=(6.0, -1.0, 9.0),
            trace=1.0,
            object_name=object_name,
            terminal_polarity="positive",
            terminal_role="series_exit",
            side="left",
        ),
    )


def _disable_inter_half_bridge(binding: TxSeriesBindingInputs) -> TxSeriesBindingInputs:
    binding.inter_half_exit = _unset_directed_landing_section()
    binding.inter_half_entry = _unset_directed_landing_section()
    return binding


def test_finalize_tx_port_stage_is_skipped_when_semantic_port_is_disabled() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    modeler.create_box(origin=[0.0, -8.0, 8.0], sizes=[20.0, 16.0, 2.0], name="coil_tx_unified", material="copper")
    group_objects = cast(GroupObjects, {"tx_dd": ["coil_tx_unified"], "tx_vertical": [], "rx_dd": [], "ferrite": []})
    object_names = ["coil_tx_unified"]
    cad_probe: list[CadProbe] = []

    _, _, ports, port_assignments = _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/tx_semantic_port.aedt"),
        design_id="tx_semantic_port",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        tx_board_ids={"tx_main_0"},
        tx_vertical_nodes_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(20.0, 10.0, 20.0),
        txdd_right_a_points={},
        txdd_right_object_names={0: "coil_tx_unified"},
        txdd_start_stub_sources={"tx_main_0": [((99.0, 99.0, 99.0), 4.0, "coil_tx_unified")]},
        rxdd_back_stub_sources=[],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=cad_probe,
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        tx_series_binding=_unset_tx_series_binding(),
    )

    assert ports == {"tx": [], "rx": []}
    assert port_assignments == {"tx": [], "rx": []}
    assert [cast(str, call["name"]) for call in modeler.create_box_calls[-1:]] == [
        cast(str, modeler.create_box_calls[-1]["name"]),
    ]
    assert cast(str, modeler.create_box_calls[-1]["name"]).startswith("txs_in_above_")
    assert hfss.oboundary.assign_lumped_port_calls == []
    assert hfss.save_project_calls == ["/tmp/tx_semantic_port.aedt"]


def test_finalize_solids_and_substrates_raises_when_save_project_returns_false() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    hfss.save_project_result = False
    modeler.create_box(origin=[0.0, -8.0, 8.0], sizes=[20.0, 16.0, 2.0], name="coil_tx_unified", material="copper")
    group_objects = cast(GroupObjects, {"tx_dd": ["coil_tx_unified"], "tx_vertical": [], "rx_dd": [], "ferrite": []})
    object_names = ["coil_tx_unified"]
    cad_probe: list[CadProbe] = []

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: save_project"):
        _finalize_solids_and_substrates_impl(
            modeler=cast(Modeler3D, modeler),
            hfss=cast(Hfss, hfss),
            aedt_path=Path("/tmp/tx_semantic_port_fail.aedt"),
            design_id="tx_semantic_port_fail",
            cu_thickness=0.035,
            pcb_thickness=1.6,
            tx_board_ids={"tx_main_0"},
            tx_vertical_nodes_by_board={},
            tx_vertical_region_min=(0.0, -10.0, 0.0),
            tx_vertical_region_max=(20.0, 10.0, 20.0),
            txdd_right_a_points={},
            txdd_right_object_names={0: "coil_tx_unified"},
            txdd_start_stub_sources={"tx_main_0": [((99.0, 99.0, 99.0), 4.0, "coil_tx_unified")]},
            rxdd_back_stub_sources=[],
            group_objects=group_objects,
            object_names=object_names,
            cad_probe=cad_probe,
            placement_violations=[],
            coil_plane_bboxes=[],
            fr4_object_names=[],
            tx_vertical_fr4_names=[],
            tx_series_binding=_unset_tx_series_binding(),
        )


def test_finalize_tx_open_loop_does_not_assign_lumped_port_when_port_stage_is_disabled() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    modeler.create_box(origin=[0.0, 4.0, 8.0], sizes=[8.0, 4.0, 2.0], name="coil_tx_right", material="copper")
    modeler.create_box(origin=[0.0, -8.0, 8.0], sizes=[8.0, 4.0, 2.0], name="coil_tx_left", material="copper")
    group_objects = cast(GroupObjects, {"tx_dd": ["coil_tx_right", "coil_tx_left"], "tx_vertical": [], "rx_dd": [], "ferrite": []})
    object_names = ["coil_tx_right", "coil_tx_left"]
    cad_probe: list[CadProbe] = []
    _, _, ports, port_assignments = _finalize_solids_and_substrates_impl(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path("/tmp/tx_open_loop_fail.aedt"),
        design_id="tx_open_loop_fail",
        cu_thickness=0.035,
        pcb_thickness=1.6,
        tx_board_ids={"tx_main_0"},
        tx_vertical_nodes_by_board={},
        tx_vertical_region_min=(0.0, -10.0, 0.0),
        tx_vertical_region_max=(20.0, 10.0, 20.0),
        txdd_right_a_points={},
        txdd_right_object_names={0: "coil_tx_right"},
        txdd_start_stub_sources={},
        rxdd_back_stub_sources=[],
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=cad_probe,
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        tx_series_binding=_unset_tx_series_binding(),
    )

    assert ports == {"tx": [], "rx": []}
    assert port_assignments == {"tx": [], "rx": []}
    assert hfss.oboundary.assign_lumped_port_calls == []


def test_find_matching_tx_stub_bottom_edge_id_rejects_constant_x_target() -> None:
    modeler = _FakeModeler()
    modeler.create_box(origin=[0.0, -1.0, 0.0], sizes=[2.0, 2.0, 2.0], name="coil_tx_unified", material="copper")

    with pytest.raises(ValueError, match="constant-x / ZY-parallel"):
        _find_matching_tx_stub_bottom_edge_id(
            modeler=cast(Modeler3D, modeler),
            object_name="coil_tx_unified",
            target_edge=((1.0, 0.0, 0.0), (1.0, 0.0, 1.0)),
            context="tx stub test",
        )

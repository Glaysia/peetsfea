from __future__ import annotations

import pytest
from typing import cast

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.backend.pyaedt.em_pipeline.boundary_port import build_ports
from peetsfea.backend.pyaedt.em_pipeline import default_em_policy, run_em_pipeline
from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput


class _FakeHfss:
    pass


class _FakeModeler:
    pass


class _FakeVertex:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.position = (x, y, z)


class _FakeFace:
    def __init__(self, center_z: float, vertices: list[_FakeVertex]) -> None:
        self.center = (0.0, 0.0, center_z)
        self.vertices = vertices


class _FakeObject:
    def __init__(self, name: str, faces: list[_FakeFace]) -> None:
        self.name = name
        self.faces = faces


class _FakeModelerForPort:
    def __init__(self, objects_by_name: dict[str, _FakeObject]) -> None:
        self.objects_by_name = objects_by_name
        self.created_sheet_points: list[list[float]] | None = None
        self.created_sheet_name: str | None = None

    def get_object_from_name(self, object_name: str) -> _FakeObject | None:
        return self.objects_by_name.get(object_name)

    def create_polyline(self, **kwargs: object) -> object:
        points = kwargs.get("points")
        name = kwargs.get("name")
        if isinstance(points, list):
            self.created_sheet_points = [[float(v) for v in row] for row in points if isinstance(row, list)]
        if isinstance(name, str):
            self.created_sheet_name = name
            return _FakeObject(name=name, faces=[])
        return None


class _FakeHfssForPort:
    def __init__(self) -> None:
        self.last_assignment: str | None = None
        self.last_name: str | None = None

    def lumped_port(self, assignment: str, name: str) -> str:
        self.last_assignment = assignment
        self.last_name = name
        return name


def _input() -> EmPipelineInput:
    return {
        "ready_objects": {
            "tx_conductors": ["tx_a"],
            "rx_conductors": ["rx_a"],
            "fr4_objects": ["fr4_a"],
            "scene_bbox_source_objects": ["scene_a"],
        },
        "endpoints": {
            "tx": [
                {
                    "group_kind": "tx_dd",
                    "group_instance_index": 0,
                    "board_id": "tx_main_0",
                    "start_xyz": (0.0, 0.0, 0.0),
                    "end_xyz": (1.0, 0.0, 0.0),
                    "start_label": "A",
                    "end_label": "a",
                    "present": True,
                }
            ],
            "rx": [
                {
                    "group_kind": "rx_dd",
                    "group_instance_index": 0,
                    "board_id": "rx_main_0",
                    "start_xyz": (0.0, 0.0, 0.0),
                    "end_xyz": (1.0, 0.0, 0.0),
                    "start_label": "a",
                    "end_label": "D",
                    "present": True,
                }
            ],
        },
        "context": {
            "dd_mirror_plane": "XZ",
            "rx_plane": "YZ",
            "tx_vertical_plane": "ZX",
            "source": "type1_geometry",
            "object_names": ["tx_a", "rx_a", "fr4_a"],
        },
    }


def test_run_em_pipeline_returns_full_contract() -> None:
    result = run_em_pipeline(cast(Hfss, _FakeHfss()), cast(Modeler3D, _FakeModeler()), _input(), default_em_policy())
    assert set(result.keys()) == {
        "groups",
        "series",
        "subtract",
        "boundary",
        "ports",
        "analysis",
        "post_templates",
        "validation_report",
    }
    assert result["validation_report"]["ok"] is True


def test_run_em_pipeline_hard_fail_validation() -> None:
    data = _input()
    data["ready_objects"]["rx_conductors"] = []
    with pytest.raises(ValueError, match="validation failed"):
        run_em_pipeline(cast(Hfss, _FakeHfss()), cast(Modeler3D, _FakeModeler()), data, default_em_policy())


def test_build_ports_creates_single_tx_dd_bottom_lumped_port_from_two_lowest_faces() -> None:
    low_face_0 = _FakeFace(
        center_z=-9.0,
        vertices=[
            _FakeVertex(0.0, 0.0, -9.0),
            _FakeVertex(2.0, 0.0, -9.0),
            _FakeVertex(2.0, 1.0, -9.0),
            _FakeVertex(0.0, 1.0, -9.0),
        ],
    )
    low_face_1 = _FakeFace(
        center_z=-8.0,
        vertices=[
            _FakeVertex(0.0, 0.0, -8.0),
            _FakeVertex(2.0, 0.0, -8.0),
            _FakeVertex(2.0, 1.0, -8.0),
            _FakeVertex(0.0, 1.0, -8.0),
        ],
    )
    high_face = _FakeFace(
        center_z=1.0,
        vertices=[
            _FakeVertex(0.0, 0.0, 1.0),
            _FakeVertex(2.0, 0.0, 1.0),
            _FakeVertex(2.0, 1.0, 1.0),
            _FakeVertex(0.0, 1.0, 1.0),
        ],
    )
    tx_dd_obj = _FakeObject("coil_tx_dd_right_top", [high_face, low_face_1, low_face_0])
    modeler = _FakeModelerForPort(objects_by_name={"coil_tx_dd_right_top": tx_dd_obj})
    hfss = _FakeHfssForPort()
    data = _input()
    data["ready_objects"]["tx_conductors"] = ["coil_tx_dd_right_top", "tx_vertical_bridge"]

    ports = build_ports(cast(Hfss, hfss), cast(Modeler3D, modeler), data)

    assert ports["tx"] == ["tx_dd_lumped_port_1"]
    assert hfss.last_assignment == "sheet_tx_dd_bottom_port_1"
    assert hfss.last_name == "tx_dd_lumped_port_1"
    assert modeler.created_sheet_name == "sheet_tx_dd_bottom_port_1"
    assert modeler.created_sheet_points is not None
    zs = [point[2] for point in modeler.created_sheet_points]
    assert min(zs) == pytest.approx(-9.0, abs=1e-9)
    assert max(zs) == pytest.approx(-8.0, abs=1e-9)

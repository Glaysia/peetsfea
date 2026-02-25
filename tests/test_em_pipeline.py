from __future__ import annotations

import pytest
from typing import cast

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.backend.pyaedt.em_pipeline.boundary_port import build_ports
from peetsfea.backend.pyaedt.em_pipeline import default_em_policy, run_em_pipeline
from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput


class _FakeHfss:
    def __init__(self) -> None:
        self.radiation_assigned_faces: list[int] = []
        self.setup_names: list[str] = []
        self.deleted_setups: list[str] = []
        self.inserted_setup_types: list[str] = []
        self.inserted_setup_payloads: list[list[object]] = []
        self.inserted_sweep_setup_names: list[str] = []
        self.inserted_sweep_payloads: list[list[object]] = []
        self.odesign = self._Design(self)

    class _AnalysisModule:
        def __init__(self, parent: "_FakeHfss") -> None:
            self._parent = parent

        def InsertSetup(self, setup_type: str, props: list[object]) -> None:
            self._parent.inserted_setup_types.append(setup_type)
            self._parent.inserted_setup_payloads.append(props)
            if "Setup1" not in self._parent.setup_names:
                self._parent.setup_names.append("Setup1")

        def InsertFrequencySweep(self, setup_name: str, props: list[object]) -> None:
            self._parent.inserted_sweep_setup_names.append(setup_name)
            self._parent.inserted_sweep_payloads.append(props)

    class _Design:
        def __init__(self, parent: "_FakeHfss") -> None:
            self._parent = parent

        def GetModule(self, name: str) -> "_FakeHfss._AnalysisModule":
            if name != "AnalysisSetup":
                raise ValueError(f"unexpected module: {name}")
            return _FakeHfss._AnalysisModule(self._parent)

    def assign_radiation_boundary_to_faces(self, assignment: int, name: str | None = None) -> bool:
        _ = name
        self.radiation_assigned_faces.append(assignment)
        return True

    def delete_setup(self, name: str) -> bool:
        self.deleted_setups.append(name)
        self.setup_names = [setup for setup in self.setup_names if setup != name]
        return True


class _FakeModeler:
    def __init__(self) -> None:
        self.created_region_name: str | None = None

    class _Region:
        def __init__(self, name: str) -> None:
            self.name = name

    def create_region(self, pad_value: int, pad_type: str, name: str) -> "_FakeModeler._Region":
        _ = (pad_value, pad_type)
        self.created_region_name = name
        return _FakeModeler._Region(name)

    def get_object_faces(self, assignment: str) -> list[int]:
        if assignment != self.created_region_name:
            return []
        return [10, 11, 12, 13, 14, 15]


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
                    "start_label": "A",
                    "end_label": "d",
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
    fake_hfss = _FakeHfss()
    fake_modeler = _FakeModeler()
    result = run_em_pipeline(cast(Hfss, fake_hfss), cast(Modeler3D, fake_modeler), _input(), default_em_policy())
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
    assert sorted(fake_hfss.radiation_assigned_faces) == [10, 11, 12, 13, 14, 15]
    assert fake_hfss.inserted_setup_types == ["HfssDriven"]
    assert fake_hfss.inserted_sweep_setup_names == ["Setup1"]


def test_run_em_pipeline_hard_fail_validation() -> None:
    data = _input()
    data["ready_objects"]["rx_conductors"] = []
    with pytest.raises(ValueError, match="validation failed"):
        run_em_pipeline(cast(Hfss, _FakeHfss()), cast(Modeler3D, _FakeModeler()), data, default_em_policy())


def test_build_ports_returns_endpoint_based_default_port_names() -> None:
    ports = build_ports(cast(Hfss, _FakeHfss()), cast(Modeler3D, _FakeModeler()), _input())
    assert ports == {"tx": ["tx_port_0"], "rx": ["rx_port_0"]}

from __future__ import annotations

from typing import Literal, cast

import pytest

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.backend.pyaedt.geometry.build_rx_dd import build_em_artifacts
from peetsfea.backend.pyaedt.geometry.scene_objects import _assert_tx_ferrite_gap_from_live_objects, _create_ferrite_model_objects
from peetsfea.types.manifest import CadProbe, GroupObjects, SceneObjectEntry, SelectedParameters


_PlaneBbox = tuple[str, Literal["XY", "YZ", "ZX"], list[float]]


class _FakeMaterial:
    def __init__(self) -> None:
        self.permeability = ""
        self.permittivity = ""
        self.conductivity = ""
        self.dielectric_loss_tangent = ""
        self.magnetic_loss_tangent = ""


class _FakeMaterials:
    def __init__(self) -> None:
        self.material_keys: dict[str, _FakeMaterial] = {}

    def exists_material(self, name: str) -> bool:
        return name in self.material_keys

    def add_material(self, name: str, properties: object = None) -> _FakeMaterial:
        _ = properties
        material = _FakeMaterial()
        self.material_keys[name] = material
        return material


class _FakeHfss:
    def __init__(self) -> None:
        self.materials = _FakeMaterials()


class _FakeObject:
    def __init__(self, name: str, origin: list[float], sizes: list[float]) -> None:
        self.name = name
        self.bounding_box = [origin[0], origin[1], origin[2], origin[0] + sizes[0], origin[1] + sizes[1], origin[2] + sizes[2]]
        self.edges: list[object] = []


class _FakeModeler:
    def __init__(self) -> None:
        self.box_calls: list[dict[str, object]] = []
        self.subtract_calls: list[dict[str, object]] = []

    def create_box(self, **kwargs: object) -> _FakeObject:
        self.box_calls.append(dict(kwargs))
        name = cast(str, kwargs["name"])
        origin = cast(list[float], kwargs["origin"])
        sizes = cast(list[float], kwargs["sizes"])
        return _FakeObject(name=name, origin=origin, sizes=sizes)

    def subtract(self, *, blank_list: list[str], tool_list: list[str], keep_originals: bool) -> bool:
        self.subtract_calls.append(
            {"blank_list": list(blank_list), "tool_list": list(tool_list), "keep_originals": keep_originals}
        )
        return True


def _selected(*, ferrite_present: bool) -> SelectedParameters:
    return cast(
        SelectedParameters,
        {
            "tx_dd_outer_x": 140.0,
            "tx_dd_outer_y": 80.0,
            "tx_vertical_outer_x": 140.0,
            "tx_vertical_outer_y": 80.0,
            "rx_dd_outer_x": 100.0,
            "rx_dd_outer_y": 80.0,
            "inner_margin_x": 2.0,
            "inner_margin_y": 2.0,
            "tx_dd_pair_spacing_ratio": 0.1,
            "rx_dd_pair_spacing_ratio": 0.02,
            "tx_vertical_center_gap_mm": 10.0,
            "tx_dd_pair_spacing_mm": 28.0,
            "rx_dd_pair_spacing_mm": 7.2,
            "tx_vertical_span_mm": 10.0,
            "tv_width_mm": 1200.0,
            "tv_height_mm": 700.0,
            "tv_thickness_mm": 9.0,
            "tv_base_z_mm": 600.0,
            "tx_region_outer_w_mm": 160.0,
            "tx_region_outer_h_mm": 280.0,
            "tx_region_thickness_mm": 90.0,
            "tx_region_vertical_z_mm": 20.0,
            "tx_region_dd_z_mm": 20.0,
            "rx_region_outer_w_mm": 560.0,
            "rx_region_outer_h_mm": 360.0,
            "rx_region_thickness_mm": 4.0,
            "wall_thickness_mm": 200.0,
            "wall_size_y_mm": 4000.0,
            "wall_size_z_mm": 3000.0,
            "floor_thickness_mm": 300.0,
            "floor_size_x_mm": 5000.0,
            "floor_size_y_mm": 5000.0,
            "ferrite_present": ferrite_present,
            "rx_ferrite_thickness_mm": 2.0,
            "tx_ferrite_thickness_mm": 2.0,
            "tx_ferrite_gap_mm": 3.1,
            "ferrite_relative_permeability": 500.0,
            "shelf_height_mm": 400.0,
            "shelf_min_size_x_mm": 350.0,
            "rx_region_bottom_from_tv_mm": 1.0,
            "tx_dd_top_clearance_ratio": 0.005,
            "tx_dd_top_clearance_mm": 0.1,
            "rx_face_clearance_mm": 0.0,
            "tx_main_1_z_from_tx_main_0_mm": 3.0,
            "dd_mirror_plane": "XZ",
            "rx_plane": "YZ",
            "tx_vertical_plane": "ZX",
            "via_diameter_mm": 0.5,
            "pcb_thickness_mm": 1.6,
            "cu_thickness_mm": 0.035,
            "via_diameter": 0.5,
            "pcb_thickness": 1.6,
            "cu_thickness": 0.035,
            "fr4_er": 4.4,
        },
    )


def _scene_objects() -> list[SceneObjectEntry]:
    return [
        {
            "name": "scene_wall_demo",
            "kind": "wall",
            "present": True,
            "origin_xyz": (-200.0, -2000.0, 0.0),
            "size_xyz": (200.0, 4000.0, 3000.0),
            "plane": "YZ",
            "non_model": True,
        },
        {
            "name": "scene_tv_demo",
            "kind": "tv",
            "present": True,
            "origin_xyz": (0.0, -600.0, 600.0),
            "size_xyz": (9.0, 1200.0, 700.0),
            "plane": "YZ",
            "non_model": True,
        },
    ]


def _coil_plane_bboxes() -> list[_PlaneBbox]:
    return [
        ("rx_main_0", "YZ", [3.9, -40.0, 610.0, 3.935, 42.0, 690.0]),
        ("tx_main_0", "XY", [10.0, -30.0, 401.0, 60.0, 30.0, 401.035]),
        ("tx_main_1", "XY", [12.0, -28.0, 405.0, 58.0, 28.0, 405.035]),
        ("tx_main_0", "ZX", [15.0, -5.0, 420.0, 55.0, 5.0, 470.0]),
    ]


def _cad_probe() -> list[CadProbe]:
    return cast(
        list[CadProbe],
        [
        {"object_name": "fr4_tx_main_0_xy_0_demo", "bbox": [9.9, -30.1, 399.3, 90.1, 30.1, 400.9]},
        {"object_name": "fr4_tx_main_1_xy_1_demo", "bbox": [12.0, -28.0, 403.3, 58.0, 28.0, 404.9]},
        {"object_name": "fr4_tx_main_0_zx_2_demo", "bbox": [15.0, -5.1, 419.9, 55.0, 5.1, 470.1]},
        ],
    )


def test_create_ferrite_model_objects_creates_coil_footprint_plates_and_subtracts_live_tools() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()

    names, probes, entries = _create_ferrite_model_objects(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        design_id="demo",
        selected=_selected(ferrite_present=True),
        scene_objects=_scene_objects(),
        object_names=[
            "scene_wall_demo",
            "scene_tv_demo",
            "coil_rx_demo",
            "coil_tx_low_demo",
            "coil_tx_high_demo",
            "bridge_demo",
            "fr4_demo",
        ],
        coil_plane_bboxes=_coil_plane_bboxes(),
        cad_probe=_cad_probe(),
        tx_board_ids={"tx_main_0", "tx_main_1"},
    )

    assert names == ["ferrite_rx_demo", "ferrite_tx_demo"]
    assert len(probes) == 2
    assert [entry["kind"] for entry in entries] == ["rx_ferrite", "tx_ferrite"]
    assert all(entry["present"] is True for entry in entries)
    assert all(entry["non_model"] is False for entry in entries)
    assert entries[0]["origin_xyz"] == (1.9, -40.0, 610.0)
    assert entries[0]["size_xyz"] == (2.0, 82.0, 80.0)
    assert entries[1]["origin_xyz"] == (9.9, -30.1, 394.2)
    assert entries[1]["size_xyz"] == (80.19999999999999, 60.2, 2.0)
    tx_ferrite_top_z = entries[1]["origin_xyz"][2] + entries[1]["size_xyz"][2]
    lowest_tx_xy_fr4_min_z = min(probe["bbox"][2] for probe in _cad_probe() if "_xy_" in probe["object_name"])
    assert tx_ferrite_top_z == pytest.approx(lowest_tx_xy_fr4_min_z - 3.1)
    assert len(modeler.box_calls) == 2
    assert all(call["material"] == "peetsfea_ferrite_mu500" for call in modeler.box_calls)
    assert len(modeler.subtract_calls) == 2
    expected_tool_names = ["bridge_demo", "coil_rx_demo", "coil_tx_high_demo", "coil_tx_low_demo", "fr4_demo"]
    assert all(call["tool_list"] == expected_tool_names for call in modeler.subtract_calls)
    assert all(call["keep_originals"] is True for call in modeler.subtract_calls)
    ferrite_material = hfss.materials.material_keys["peetsfea_ferrite_mu500"]
    assert ferrite_material.permeability == "500.0"
    assert ferrite_material.permittivity == "1.0"
    assert ferrite_material.conductivity == "0"


def test_create_ferrite_model_objects_records_absence_without_creating_boxes() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()

    names, probes, entries = _create_ferrite_model_objects(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        design_id="demo",
        selected=_selected(ferrite_present=False),
        scene_objects=_scene_objects(),
        object_names=["scene_wall_demo", "scene_tv_demo", "coil_rx_demo", "coil_tx_low_demo", "fr4_demo"],
        coil_plane_bboxes=_coil_plane_bboxes(),
        cad_probe=_cad_probe(),
        tx_board_ids={"tx_main_0", "tx_main_1"},
    )

    assert names == []
    assert probes == []
    assert len(entries) == 2
    assert [entry["present"] for entry in entries] == [False, False]
    assert modeler.box_calls == []
    assert entries[0]["origin_xyz"] == (1.9, -40.0, 610.0)
    assert entries[1]["origin_xyz"] == (9.9, -30.1, 394.2)


def test_create_ferrite_model_objects_fails_when_rx_plate_would_leave_tv() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()

    with pytest.raises(ValueError, match="RX ferrite must stay inside the TV envelope"):
        _create_ferrite_model_objects(
            modeler=cast(Modeler3D, modeler),
            hfss=cast(Hfss, hfss),
            design_id="demo",
            selected=_selected(ferrite_present=True),
            scene_objects=_scene_objects(),
            object_names=["scene_wall_demo", "scene_tv_demo", "coil_rx_demo", "coil_tx_low_demo"],
            coil_plane_bboxes=cast(
                list[_PlaneBbox],
                [
                    ("rx_main_0", "YZ", [1.5, -40.0, 610.0, 1.535, 42.0, 690.0]),
                    ("tx_main_0", "XY", [10.0, -30.0, 401.0, 60.0, 30.0, 401.035]),
                ],
            ),
            cad_probe=_cad_probe(),
            tx_board_ids={"tx_main_0"},
        )


def test_create_ferrite_model_objects_fails_when_tx_xy_fr4_is_missing() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()

    with pytest.raises(ValueError, match="no TX XY FR4 bbox"):
        _create_ferrite_model_objects(
            modeler=cast(Modeler3D, modeler),
            hfss=cast(Hfss, hfss),
            design_id="demo",
            selected=_selected(ferrite_present=True),
            scene_objects=_scene_objects(),
            object_names=["scene_wall_demo", "scene_tv_demo", "coil_rx_demo"],
            coil_plane_bboxes=cast(list[_PlaneBbox], [("rx_main_0", "YZ", [3.9, -40.0, 610.0, 3.935, 42.0, 690.0])]),
            cad_probe=[],
            tx_board_ids={"tx_main_0"},
        )


def test_create_ferrite_model_objects_fails_when_tx_ferrite_touches_tx_live_object() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    touching_probe = cast(
        list[CadProbe],
        [
            {"object_name": "fr4_tx_main_0_xy_0_demo", "bbox": [9.9, -30.1, 399.3, 90.1, 30.1, 400.9]},
            {"object_name": "coil_tx_touch_demo", "bbox": [9.9, -30.1, 396.1, 90.1, 30.1, 396.8]},
        ],
    )

    with pytest.raises(
        ValueError,
        match=(
            "TX ferrite must keep a positive gap from TX coil copper, TX bridge objects, "
            "TX port sheet objects, and TX FR4 sheet objects"
        ),
    ):
        _create_ferrite_model_objects(
            modeler=cast(Modeler3D, modeler),
            hfss=cast(Hfss, hfss),
            design_id="demo",
            selected=_selected(ferrite_present=True),
            scene_objects=_scene_objects(),
            object_names=["scene_wall_demo", "scene_tv_demo", "coil_tx_low_demo", "fr4_demo"],
            coil_plane_bboxes=_coil_plane_bboxes(),
            cad_probe=touching_probe,
            tx_board_ids={"tx_main_0"},
        )


def test_assert_tx_ferrite_gap_from_live_objects_fails_when_tx_port_sheet_touches() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "TX ferrite must keep a positive gap from TX coil copper, TX bridge objects, "
            "TX port sheet objects, and TX FR4 sheet objects"
        ),
    ):
        _assert_tx_ferrite_gap_from_live_objects(
            ferrite_name="ferrite_tx_demo",
            origin_xyz=(9.9, -30.1, 394.2),
            size_xyz=(80.2, 60.2, 2.0),
            cad_probe=cast(
                list[CadProbe],
                [{"object_name": "sheet_txdd_ports_tx_main_0", "bbox": [9.9, -30.1, 396.0, 90.1, 30.1, 396.6]}],
            ),
            tx_board_ids={"tx_main_0"},
        )


def test_build_em_artifacts_includes_ferrite_objects_and_filters_absent_scene_entries() -> None:
    selected = cast(dict[str, object], {"dd_mirror_plane": "XZ", "rx_plane": "YZ", "tx_vertical_plane": "ZX"})
    group_objects = cast(
        GroupObjects,
        {"tx_dd": ["tx_a"], "tx_vertical": ["tx_v"], "rx_dd": ["rx_a"], "ferrite": ["ferrite_rx_demo", "ferrite_tx_demo"]},
    )
    scene_objects: list[SceneObjectEntry] = [
        {
            "name": "scene_wall_demo",
            "kind": "wall",
            "present": True,
            "origin_xyz": (-1.0, -1.0, 0.0),
            "size_xyz": (1.0, 2.0, 3.0),
            "plane": "YZ",
            "non_model": True,
        },
        {
            "name": "ferrite_tx_demo",
            "kind": "tx_ferrite",
            "present": False,
            "origin_xyz": (0.0, -1.0, 0.0),
            "size_xyz": (1.0, 2.0, 3.0),
            "plane": "XY",
            "non_model": False,
        },
    ]

    em_ready, em_endpoints, em_context = build_em_artifacts(
        selected=selected,
        object_names=["tx_a", "tx_v", "rx_a", "ferrite_rx_demo", "ferrite_tx_demo"],
        group_objects=group_objects,
        group_endpoints=[],
        scene_objects=scene_objects,
    )

    assert em_ready["ferrite_objects"] == ["ferrite_rx_demo", "ferrite_tx_demo"]
    assert em_ready["scene_bbox_source_objects"] == ["scene_wall_demo"]
    assert em_endpoints == {"tx": [], "rx": []}
    assert em_context["object_names"] == ["ferrite_rx_demo", "ferrite_tx_demo", "rx_a", "tx_a", "tx_v"]

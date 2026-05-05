from __future__ import annotations

from typing import cast

import pytest
from peetsfea.aedt import Modeler3D

from peetsfea.legacy.type1.backend.pyaedt.geometry.build_state import GeometryBuildState
from peetsfea.legacy.type1.backend.pyaedt.geometry.builders.neo_coil_instance import NeoCoilBoxInstance, NeoCoilInstance
from tests.backend_geometry_build.test_one_turn_geometry_build import _FakeModeler


def test_neo_coil_box_instance_registers_group_object() -> None:
    state = GeometryBuildState()
    modeler = _FakeModeler()

    created_name = NeoCoilBoxInstance(
        name_prefix="neo_coil_tx_dd_",
        board_id="tx_main_0",
        layer_index=0,
        origin_xyz=(1.0, 2.0, 3.0),
        size_xyz=(4.0, 5.0, 6.0),
        material="copper",
        color_rgb=(255, 128, 0),
        transparency=0.0,
        registry_target="tx_dd",
    ).instantiate(
        modeler=cast(Modeler3D, modeler),
        state=state,
        design_id="demo",
    )

    assert created_name == "neo_coil_tx_dd_tx_main_0_l0_demo"
    assert state.object_names == [created_name]
    assert state.group_objects["tx_dd"] == [created_name]
    assert state.fr4_object_names == []
    assert [probe["object_name"] for probe in state.cad_probe] == [created_name]
    assert modeler.objects[created_name].color == (255, 128, 0)
    assert modeler.objects[created_name].transparency == 0.0


def test_neo_coil_box_instance_registers_fr4_only_object() -> None:
    state = GeometryBuildState()
    modeler = _FakeModeler()

    created_name = NeoCoilBoxInstance(
        name_prefix="neo_fr4_tx_dd_",
        board_id="tx_main_0",
        layer_index=0,
        origin_xyz=(10.0, -5.0, 1.0),
        size_xyz=(20.0, 10.0, 1.6),
        material="FR4_epoxy",
        color_rgb=(0, 128, 0),
        transparency=0.85,
        registry_target="fr4_only",
    ).instantiate(
        modeler=cast(Modeler3D, modeler),
        state=state,
        design_id="demo",
    )

    assert created_name == "neo_fr4_tx_dd_tx_main_0_l0_demo"
    assert state.object_names == [created_name]
    assert state.fr4_object_names == [created_name]
    assert state.group_objects["tx_dd"] == []
    assert [probe["object_name"] for probe in state.cad_probe] == [created_name]
    assert modeler.objects[created_name].color == (0, 128, 0)
    assert modeler.objects[created_name].transparency == 0.85


def test_neo_coil_box_instance_rejects_duplicate_name() -> None:
    state = GeometryBuildState()
    modeler = _FakeModeler()
    instance = NeoCoilBoxInstance(
        name_prefix="neo_fr4_tx_dd_",
        board_id="tx_main_0",
        layer_index=0,
        origin_xyz=(10.0, -5.0, 1.0),
        size_xyz=(20.0, 10.0, 1.6),
        material="FR4_epoxy",
        color_rgb=(0, 128, 0),
        transparency=0.85,
        registry_target="fr4_only",
    )

    instance.instantiate(
        modeler=cast(Modeler3D, modeler),
        state=state,
        design_id="demo",
    )

    with pytest.raises(ValueError, match="name collision"):
        instance.instantiate(
            modeler=cast(Modeler3D, modeler),
            state=state,
            design_id="demo",
        )


def test_neo_coil_instance_builds_polyline_and_registers_endpoint_metadata() -> None:
    state = GeometryBuildState()
    modeler = _FakeModeler()

    created_name = NeoCoilInstance(
        name_prefix="neo_coil_tx_dd_right_",
        group_kind="tx_dd",
        board_id="tx_main_0",
        group_instance_index=1,
        layer_index=0,
        path_points=[
            (1.0, 2.0, 3.0),
            (4.0, 2.0, 3.0),
            (4.0, 5.0, 3.0),
        ],
        trace_width=1.2,
        thickness=0.035,
        material="copper",
        color_rgb=(184, 115, 51),
        transparency=0.0,
        plane="XY",
        start_label="D",
        end_label="d",
        dd_family="tx_dd",
        dd_pair_index=0,
        instance_side="right",
        current_direction="ccw",
    ).instantiate(
        modeler=cast(Modeler3D, modeler),
        state=state,
        design_id="demo",
    )

    assert created_name == "neo_coil_tx_dd_right_tx_main_0_i1_l0_demo"
    assert state.object_names == [created_name]
    assert state.group_objects["tx_dd"] == [created_name]
    assert state.group_endpoints[0]["start_label"] == "D"
    assert state.group_endpoints[0]["end_label"] == "d"
    assert state.coil_polarity[0]["current_direction"] == "ccw"
    assert state.coil_polarity[0]["instance_side"] == "right"
    assert modeler.objects[created_name].color == (184, 115, 51)
    assert modeler.objects[created_name].transparency == 0.0

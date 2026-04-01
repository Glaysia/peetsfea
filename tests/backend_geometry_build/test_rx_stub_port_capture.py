from __future__ import annotations

from pathlib import Path
from typing import cast

from peetsfea.aedt import Hfss, Modeler3D
from peetsfea.backend.pyaedt.geometry import (
    RX_STUB_PORT_BACK_FACE_CORNERS_BY_DESIGN,
    reset_rx_stub_port_back_face_corners,
)
from peetsfea.backend.pyaedt.geometry.build_state import (
    _unset_bridge_anchor,
    _unset_directed_landing_section,
    _unset_edge2p,
    _unset_ordered_terminal_section,
    _unset_string,
    _unset_tx_series_binding,
)
from peetsfea.backend.pyaedt.geometry.builders.finalize_stage_rx import _apply_rxdd_back_stub_stage
from peetsfea.backend.pyaedt.geometry.builders.finalize_types import FinalizePlan
from peetsfea.backend.pyaedt.geometry.rx_stub_ports import (
    record_rx_dd_port_stub_back_face,
    resolve_rx_dd_port_edges_from_back_faces,
)
from peetsfea.types.manifest import CadProbe, EmPortAssignments, EmPorts, GroupObjects
from tests.backend_geometry_build.test_tx_port_failfast import _FakeHfss, _FakeModeler, _edge_points


def test_resolve_rx_dd_port_edges_from_back_faces_prefers_gap_facing_edges() -> None:
    design_id = "rx_stub_edges"
    reset_rx_stub_port_back_face_corners(design_id)
    signal_stub_key = record_rx_dd_port_stub_back_face(
        design_id=design_id,
        board_id="rx_main",
        instance_index=1,
        endpoint_label="A",
        origin=(-2.0, 5.5, 8.5),
        sizes=(3.0, 1.0, 1.0),
    )
    reference_stub_key = record_rx_dd_port_stub_back_face(
        design_id=design_id,
        board_id="rx_main",
        instance_index=0,
        endpoint_label="c",
        origin=(-2.0, -5.5, 1.5),
        sizes=(3.0, 1.0, 1.0),
    )

    signal_edge, reference_edge = resolve_rx_dd_port_edges_from_back_faces(
        design_id=design_id,
        signal_stub_key=signal_stub_key,
        reference_stub_key=reference_stub_key,
    )

    assert signal_edge == ((-2.0, 5.5, 8.5), (-2.0, 5.5, 9.5))
    assert reference_edge == ((-2.0, -4.5, 1.5), (-2.0, -4.5, 2.5))


def _rx_finalize_plan(
    *,
    modeler: _FakeModeler,
    hfss: _FakeHfss,
    design_id: str,
) -> FinalizePlan:
    group_objects = cast(
        GroupObjects,
        {"tx_dd": [], "tx_vertical": [], "rx_dd": ["coil_rx_left", "coil_rx_right"], "ferrite": []},
    )
    return FinalizePlan(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        aedt_path=Path(f"/tmp/{design_id}.aedt"),
        design_id=design_id,
        cu_thickness=0.035,
        pcb_thickness=1.6,
        via_diameter_mm=0.5,
        tx_board_ids=set(),
        tx_vertical_nodes_by_board={},
        tx_vertical_region_min=(0.0, 0.0, 0.0),
        tx_vertical_region_max=(0.0, 0.0, 0.0),
        txdd_right_a_points={},
        txdd_right_object_names={},
        txdd_start_stub_sources={},
        rxdd_back_stub_sources=[
            ("rx_main", 0, "c", (1.0, -5.0, 2.0), 1.0, "coil_rx_left"),
            ("rx_main", 1, "A", (1.0, 6.0, 9.0), 1.0, "coil_rx_right"),
        ],
        group_objects=group_objects,
        object_names=["coil_rx_left", "coil_rx_right"],
        cad_probe=cast(list[CadProbe], []),
        placement_violations=[],
        coil_plane_bboxes=[],
        fr4_object_names=[],
        tx_vertical_fr4_names=[],
        coil_polarity=[],
        dd_half_geometries=[],
        txdd_global_right_bridge_landing=_unset_directed_landing_section(),
        txdd_global_right_bridge_edge=_unset_edge2p(),
        txdd_global_right_bridge_section=_unset_ordered_terminal_section(),
        txdd_global_right_bridge_object_name=_unset_string(),
        txdd_global_right_d_edge=_unset_edge2p(),
        txdd_global_right_d_object_name=_unset_string(),
        tx_vertical_global_outer_right_edge=_unset_edge2p(),
        tx_vertical_global_outer_left_edge=_unset_edge2p(),
        tx_vertical_global_outer_right_landing=_unset_directed_landing_section(),
        tx_vertical_global_outer_left_landing=_unset_directed_landing_section(),
        tx_vertical_global_outer_right_section=_unset_ordered_terminal_section(),
        tx_vertical_global_outer_left_section=_unset_ordered_terminal_section(),
        txdd_global_right_bridge_anchor=_unset_bridge_anchor(),
        tx_vertical_global_outer_right_anchor=_unset_bridge_anchor(),
        tx_vertical_global_outer_left_anchor=_unset_bridge_anchor(),
        tx_series_binding=_unset_tx_series_binding(),
    )


def test_apply_rxdd_back_stub_stage_captures_back_faces_and_assigns_port() -> None:
    design_id = "rx_stub_finalize"
    reset_rx_stub_port_back_face_corners(design_id)
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    plan = _rx_finalize_plan(modeler=modeler, hfss=hfss, design_id=design_id)
    resolved_ports = cast(EmPorts, {"tx": [], "rx": []})
    resolved_port_assignments = cast(EmPortAssignments, {"tx": [], "rx": []})

    _apply_rxdd_back_stub_stage(
        plan,
        object_name_tag="rx_stub_finalize",
        resolved_ports=resolved_ports,
        resolved_port_assignments=resolved_port_assignments,
    )

    assert RX_STUB_PORT_BACK_FACE_CORNERS_BY_DESIGN[design_id] == {
        "rx_dd_port:rx_main:0:c": (
            (-2.0, -5.5, 1.5),
            (-2.0, -4.5, 1.5),
            (-2.0, -5.5, 2.5),
            (-2.0, -4.5, 2.5),
        ),
        "rx_dd_port:rx_main:1:A": (
            (-2.0, 5.5, 8.5),
            (-2.0, 6.5, 8.5),
            (-2.0, 5.5, 9.5),
            (-2.0, 6.5, 9.5),
        ),
    }
    assert resolved_ports == {"tx": [], "rx": ["1_T1"]}
    assert len(resolved_port_assignments["rx"]) == 1
    assignment = resolved_port_assignments["rx"][0]
    assert modeler.unite_calls == [
        ["coil_rx_left", "rxs_rx_main_0_c"],
        ["coil_rx_right", "rxs_rx_main_1_A"],
    ]
    assert assignment["signal_object_name"] == "coil_rx_right"
    assert assignment["reference_object_name"] == "coil_rx_left"
    assert _edge_points(modeler, assignment["signal_edge_id"]) == ((-2.0, 5.5, 8.5), (-2.0, 5.5, 9.5))
    assert _edge_points(modeler, assignment["reference_edge_id"]) == ((-2.0, -4.5, 1.5), (-2.0, -4.5, 2.5))

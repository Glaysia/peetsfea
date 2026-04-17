from __future__ import annotations

from typing import cast

from peetsfea.aedt import Hfss, Modeler3D

from peetsfea.legacy.type1.backend.pyaedt.geometry.builders.build_excitation_ops import _create_tx_semantic_port_if_needed
from peetsfea.legacy.type1.backend.pyaedt.geometry.build_state import TxSeriesBindingInputs
from peetsfea.legacy.type1.backend.pyaedt.geometry.tx_stub_faces import (
    capture_stub_face_ref_from_object,
    remap_stub_face_ref_after_unite,
)
from peetsfea.types.manifest import EmPortAssignments, EmPorts, GroupObjects
from tests.backend_geometry_build.test_tx_port_failfast import _FakeHfss, _FakeModeler, _binding_for_single_conductor, _edge_points


def test_create_tx_semantic_port_reuses_captured_stub_face_refs_after_unite() -> None:
    modeler = _FakeModeler()
    hfss = _FakeHfss()
    modeler.create_box(origin=[9.5, 7.5, 9.0], sizes=[1.0, 1.0, 1.0], name="coil_tx_unified", material="copper")
    modeler.create_box(origin=[9.5, -8.5, 9.0], sizes=[1.0, 1.0, 1.0], name="coil_tx_aux", material="copper")
    signal_face_ref = capture_stub_face_ref_from_object(
        modeler=cast(Modeler3D, modeler),
        object_name="coil_tx_unified",
        expected_face_center=(10.0, 8.0, 10.0),
        face_kind="tx_dd_xy",
        stub_role="in_above",
        context="tx semantic port test signal",
    )
    reference_face_ref = capture_stub_face_ref_from_object(
        modeler=cast(Modeler3D, modeler),
        object_name="coil_tx_aux",
        expected_face_center=(10.0, -8.0, 10.0),
        face_kind="tx_dd_xy",
        stub_role="out_above",
        context="tx semantic port test reference",
    )
    modeler.unite(assignment=["coil_tx_unified", "coil_tx_aux"])
    binding = _binding_for_single_conductor(object_name="coil_tx_unified")
    binding.feed_out["object_name"] = "coil_tx_aux"
    binding.feed_in["stub_face_ref"] = remap_stub_face_ref_after_unite(
        modeler=cast(Modeler3D, modeler),
        united_object_name="coil_tx_unified",
        face_ref=signal_face_ref,
        context="tx semantic port test signal remap",
    )
    binding.feed_out["stub_face_ref"] = remap_stub_face_ref_after_unite(
        modeler=cast(Modeler3D, modeler),
        united_object_name="coil_tx_unified",
        face_ref=reference_face_ref,
        context="tx semantic port test reference remap",
    )
    initial_create_box_count = len(modeler.create_box_calls)
    resolved_ports = cast(EmPorts, {"tx": [], "rx": []})
    resolved_port_assignments = cast(EmPortAssignments, {"tx": [], "rx": []})

    _create_tx_semantic_port_if_needed(
        modeler=cast(Modeler3D, modeler),
        hfss=cast(Hfss, hfss),
        design_id="tx_semantic_port_reuse",
        tx_series_binding=cast(TxSeriesBindingInputs, binding),
        txdd_right_object_names={0: "coil_tx_unified"},
        group_objects=cast(GroupObjects, {"tx_dd": ["coil_tx_unified"], "tx_vertical": [], "rx_dd": [], "ferrite": []}),
        object_names=["coil_tx_unified"],
        resolved_ports=resolved_ports,
        resolved_port_assignments=resolved_port_assignments,
    )

    assert len(modeler.create_box_calls) == initial_create_box_count
    assert resolved_ports == {"tx": ["1_T1"], "rx": []}
    assignment = resolved_port_assignments["tx"][0]
    assert assignment["signal_object_name"] == "coil_tx_unified"
    assert assignment["reference_object_name"] == "coil_tx_unified"
    assert _edge_points(modeler, assignment["signal_edge_id"]) == ((9.5, 8.5, 10.0), (10.5, 8.5, 10.0))
    assert _edge_points(modeler, assignment["reference_edge_id"]) == ((9.5, -7.5, 10.0), (10.5, -7.5, 10.0))

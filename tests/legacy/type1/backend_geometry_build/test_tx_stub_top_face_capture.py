from __future__ import annotations

from typing import cast

from peetsfea.aedt import Modeler3D
from peetsfea.legacy.type1.backend.pyaedt.geometry.build_state import DirectedLandingSection
from peetsfea.legacy.type1.backend.pyaedt.geometry.builders.build_tx_terminals import _create_tx_vertical_external_stub
from peetsfea.legacy.type1.backend.pyaedt.geometry.tx_stub_faces import (
    capture_stub_face_ref_from_object,
    remap_stub_face_ref_after_unite,
)
from peetsfea.types.manifest import CadProbe, GroupObjects
from tests.backend_geometry_build.test_tx_port_failfast import _FakeModeler


def _tx_vertical_terminal(*, center: tuple[float, float, float], object_name: str) -> DirectedLandingSection:
    return cast(
        DirectedLandingSection,
        {
            "p_plus": (center[0], center[1], center[2] - 0.5),
            "p_minus": (center[0], center[1], center[2] + 0.5),
            "center": center,
            "outward_dir": (1.0, 0.0, 0.0),
            "plane_normal": (0.0, -1.0, 0.0),
            "object_name": object_name,
            "dd_family": "none",
            "dd_pair_index": -1,
            "side": "center",
            "terminal_polarity": "neutral",
            "terminal_role": "none",
        },
    )


def test_capture_stub_face_ref_from_object_for_tx_dd_stub() -> None:
    modeler = _FakeModeler()
    modeler.create_box(origin=[2.5, -6.5, 9.0], sizes=[1.0, 1.0, 1.0], name="txs_in_above_demo", material="copper")

    face_ref = capture_stub_face_ref_from_object(
        modeler=cast(Modeler3D, modeler),
        object_name="txs_in_above_demo",
        expected_face_center=(3.0, -6.0, 10.0),
        face_kind="tx_dd_xy",
        stub_role="in_above",
        context="tx_dd stub face capture test",
    )

    assert face_ref["object_name"] == "txs_in_above_demo"
    assert face_ref["face_kind"] == "tx_dd_xy"
    assert face_ref["stub_role"] == "in_above"
    assert face_ref["signature"]["center"] == (3.0, -6.0, 10.0)
    assert face_ref["signature"]["face_kind"] == "tx_dd_xy"


def test_remap_stub_face_ref_after_unite_resolves_same_external_face_on_united_object() -> None:
    modeler = _FakeModeler()
    modeler.create_box(origin=[9.5, 7.5, 9.0], sizes=[1.0, 1.0, 1.0], name="coil_tx_unified", material="copper")
    modeler.create_box(origin=[9.5, -8.5, 9.0], sizes=[1.0, 1.0, 1.0], name="coil_tx_aux", material="copper")
    signal_face_ref = capture_stub_face_ref_from_object(
        modeler=cast(Modeler3D, modeler),
        object_name="coil_tx_unified",
        expected_face_center=(10.0, 8.0, 10.0),
        face_kind="tx_dd_xy",
        stub_role="in_above",
        context="tx semantic signal pre-unite",
    )

    modeler.unite(assignment=["coil_tx_unified", "coil_tx_aux"])
    remapped_face_ref = remap_stub_face_ref_after_unite(
        modeler=cast(Modeler3D, modeler),
        united_object_name="coil_tx_unified",
        face_ref=signal_face_ref,
        context="tx semantic signal remap",
    )

    assert remapped_face_ref["object_name"] == "coil_tx_unified"
    assert remapped_face_ref["face_kind"] == "tx_dd_xy"
    assert remapped_face_ref["signature"]["center"] == (10.0, 8.0, 10.0)


def test_create_tx_vertical_external_stub_populates_stub_face_ref() -> None:
    modeler = _FakeModeler()
    modeler.create_box(origin=[0.0, -1.0, 0.0], sizes=[12.0, 2.0, 12.0], name="coil_txv", material="copper")
    group_objects = cast(GroupObjects, {"tx_dd": [], "tx_vertical": ["coil_txv"], "rx_dd": [], "ferrite": []})
    object_names = ["coil_txv"]
    cad_probe: list[CadProbe] = []
    terminal = _tx_vertical_terminal(center=(10.0, 0.0, 7.0), object_name="coil_txv")

    _create_tx_vertical_external_stub(
        modeler=cast(Modeler3D, modeler),
        design_id="tx_stub_capture_vertical",
        terminal=terminal,
        stub_role="in",
        cu_thickness=0.035,
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=cad_probe,
    )

    assert "stub_face_ref" in terminal
    face_ref = terminal["stub_face_ref"]
    assert face_ref["face_kind"] == "tx_vertical_xz"
    assert face_ref["stub_role"] == "in"
    assert face_ref["signature"]["center"] == (10.5, 0.9825, 7.0)

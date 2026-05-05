from __future__ import annotations

from typing import cast

import pytest
from peetsfea.aedt import Modeler3D
from peetsfea.legacy.type1.backend.pyaedt.geometry.builders.build_tx_bridges import (
    _resolve_tx_chain_bridge_edges_from_faces,
    _resolve_tx_dd_direct_bridge_edges_from_faces,
)
from peetsfea.legacy.type1.backend.pyaedt.geometry.build_state import DirectedLandingSection
from peetsfea.legacy.type1.backend.pyaedt.geometry.tx_stub_faces import capture_stub_face_ref_from_object
from tests.backend_geometry_build.test_tx_port_failfast import _FakeModeler


def _landing(
    *,
    object_name: str,
    center: tuple[float, float, float],
    polarity: str,
    role: str,
    side: str,
    stub_face_ref: object,
) -> DirectedLandingSection:
    return cast(
        DirectedLandingSection,
        {
            "p_plus": center,
            "p_minus": center,
            "center": center,
            "outward_dir": (1.0, 0.0, 0.0),
            "plane_normal": (0.0, 0.0, 1.0),
            "object_name": object_name,
            "dd_family": "tx_dd" if role != "series_entry" else "none",
            "dd_pair_index": 0,
            "side": side,
            "terminal_polarity": polarity,
            "terminal_role": role,
            "stub_face_ref": stub_face_ref,
        },
    )


def test_resolve_tx_chain_bridge_edges_from_face_refs() -> None:
    modeler = _FakeModeler()
    modeler.create_box(origin=[0.0, 0.0, 0.0], sizes=[2.0, 2.0, 1.0], name="tx_dd_stub", material="copper")
    modeler.create_box(origin=[4.0, 3.0, 0.0], sizes=[2.0, 1.0, 2.0], name="tx_vertical_stub", material="copper")
    tx_dd_face_ref = capture_stub_face_ref_from_object(
        modeler=cast(Modeler3D, modeler),
        object_name="tx_dd_stub",
        expected_face_center=(1.0, 1.0, 1.0),
        face_kind="tx_dd_xy",
        stub_role="out_above",
        context="tx_dd bridge face capture",
    )
    tx_vertical_face_ref = capture_stub_face_ref_from_object(
        modeler=cast(Modeler3D, modeler),
        object_name="tx_vertical_stub",
        expected_face_center=(5.0, 4.0, 1.0),
        face_kind="tx_vertical_xz",
        stub_role="in",
        context="tx_vertical bridge face capture",
    )

    tx_dd_edge, tx_vertical_edge = _resolve_tx_chain_bridge_edges_from_faces(
        modeler=cast(Modeler3D, modeler),
        cu_thickness=0.1,
        tx_dd_landing=_landing(
            object_name="tx_dd_stub",
            center=(1.0, 1.0, 1.0),
            polarity="positive",
            role="inter_half_exit",
            side="right",
            stub_face_ref=tx_dd_face_ref,
        ),
        tx_vertical_landing=_landing(
            object_name="tx_vertical_stub",
            center=(5.0, 4.0, 1.0),
            polarity="negative",
            role="series_entry",
            side="center",
            stub_face_ref=tx_vertical_face_ref,
        ),
    )

    assert tx_dd_edge == ((0.0, 0.1, 0.9), (2.0, 0.1, 0.9))
    assert tx_vertical_edge == ((4.0, 3.9, 1.9), (6.0, 3.9, 1.9))


def test_resolve_tx_dd_direct_bridge_edges_from_face_refs() -> None:
    modeler = _FakeModeler()
    modeler.create_box(origin=[0.0, 0.0, 0.0], sizes=[2.0, 2.0, 1.0], name="right_stub", material="copper")
    modeler.create_box(origin=[0.0, 5.0, 0.0], sizes=[2.0, 2.0, 1.0], name="left_stub", material="copper")
    right_face_ref = capture_stub_face_ref_from_object(
        modeler=cast(Modeler3D, modeler),
        object_name="right_stub",
        expected_face_center=(1.0, 1.0, 1.0),
        face_kind="tx_dd_xy",
        stub_role="out_above",
        context="right stub face capture",
    )
    left_face_ref = capture_stub_face_ref_from_object(
        modeler=cast(Modeler3D, modeler),
        object_name="left_stub",
        expected_face_center=(1.0, 6.0, 1.0),
        face_kind="tx_dd_xy",
        stub_role="in_above",
        context="left stub face capture",
    )

    right_edge, left_edge = _resolve_tx_dd_direct_bridge_edges_from_faces(
        modeler=cast(Modeler3D, modeler),
        cu_thickness=0.1,
        first_landing=_landing(
            object_name="right_stub",
            center=(1.0, 1.0, 1.0),
            polarity="positive",
            role="inter_half_exit",
            side="right",
            stub_face_ref=right_face_ref,
        ),
        second_landing=_landing(
            object_name="left_stub",
            center=(1.0, 6.0, 1.0),
            polarity="negative",
            role="inter_half_entry",
            side="left",
            stub_face_ref=left_face_ref,
        ),
    )

    assert right_edge == ((0.0, 0.1, 0.9), (2.0, 0.1, 0.9))
    assert left_edge == ((0.0, 5.1, 0.9), (2.0, 5.1, 0.9))


def test_resolve_tx_chain_bridge_requires_stub_face_refs() -> None:
    with pytest.raises(AssertionError, match="requires stub_face_ref"):
        _resolve_tx_chain_bridge_edges_from_faces(
            modeler=cast(Modeler3D, _FakeModeler()),
            cu_thickness=0.1,
            tx_dd_landing=cast(
                DirectedLandingSection,
                {
                    "p_plus": (0.0, 0.0, 0.0),
                    "p_minus": (0.0, 0.0, 0.0),
                    "center": (0.0, 0.0, 0.0),
                    "outward_dir": (1.0, 0.0, 0.0),
                    "plane_normal": (0.0, 0.0, 1.0),
                    "object_name": "a",
                    "dd_family": "tx_dd",
                    "dd_pair_index": 0,
                    "side": "right",
                    "terminal_polarity": "positive",
                    "terminal_role": "inter_half_exit",
                },
            ),
            tx_vertical_landing=cast(
                DirectedLandingSection,
                {
                    "p_plus": (0.0, 0.0, 0.0),
                    "p_minus": (0.0, 0.0, 0.0),
                    "center": (0.0, 0.0, 0.0),
                    "outward_dir": (1.0, 0.0, 0.0),
                    "plane_normal": (0.0, 0.0, 1.0),
                    "object_name": "b",
                    "dd_family": "none",
                    "dd_pair_index": 0,
                    "side": "center",
                    "terminal_polarity": "negative",
                    "terminal_role": "series_entry",
                },
            ),
        )

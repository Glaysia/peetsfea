from __future__ import annotations

import math
import pytest
from typing import Literal, cast

from peetsfea.legacy.type1.backend.pyaedt.geometry.build import _append_rxdd_back_stub_sources_if_needed
from peetsfea.legacy.type1.backend.pyaedt.geometry.builders.build_artifacts import (
    FR4_SUBTRACT_OVERLAP_MM,
    _is_rxdd_connect_stub_endpoint,
    _is_rxdd_port_stub_endpoint,
    _fr4_box_from_plane_bbox,
    _rxdd_stub_attach_center_from_anchor,
    _rxdd_back_stub_bridge_edge,
    _rxdd_back_stub_origin_and_sizes,
    _rxdd_back_stub_sort_key,
    _txdd_start_stub_port_edge,
)

_StubSource = (
    tuple[str, int, str, tuple[float, float, float], float, str]
    | tuple[str, int, str, tuple[float, float, float], float, str, tuple[float, float, float]]
)


def test_rxdd_back_stub_origin_and_sizes_use_trace_square_and_minus_x() -> None:
    anchor = (10.0, 20.0, 30.0)
    trace = 1.2
    origin, sizes = _rxdd_back_stub_origin_and_sizes(anchor_xyz=anchor, trace=trace)
    assert origin == [7.0, 19.4, 29.4]
    assert sizes == [3.0, 1.2, 1.2]


def test_rxdd_back_stub_origin_and_sizes_support_custom_minus_x_length() -> None:
    anchor = (10.0, 20.0, 30.0)
    trace = 1.2
    origin, sizes = _rxdd_back_stub_origin_and_sizes(anchor_xyz=anchor, trace=trace, length=1.0)
    assert origin == [9.0, 19.4, 29.4]
    assert sizes == [1.0, 1.2, 1.2]


def test_rxdd_stub_attach_center_from_anchor_shifts_inward_by_half_trace() -> None:
    assert _rxdd_stub_attach_center_from_anchor(
        anchor_xyz=(10.0, 20.0, 30.0),
        trace=2.0,
        inward_dir=(0.0, -1.0, 0.0),
    ) == pytest.approx((10.0, 19.0, 30.0))
    diagonal = 1.0 / math.sqrt(2.0)
    assert _rxdd_stub_attach_center_from_anchor(
        anchor_xyz=(10.0, 20.0, 30.0),
        trace=2.0,
        inward_dir=(0.0, -diagonal, diagonal),
    ) == pytest.approx((10.0, 20.0 - diagonal, 30.0 + diagonal))
    assert _rxdd_stub_attach_center_from_anchor(
        anchor_xyz=(10.0, 20.0, 30.0),
        trace=2.0,
        inward_dir=None,
    ) == pytest.approx((10.0, 20.0, 30.0))


def test_rxdd_back_stub_sort_key_is_deterministic_by_board_instance_endpoint() -> None:
    unsorted_sources = [
        ("rx_b", 1, "d", (0.0, 0.0, 0.0), 1.0, "obj1"),
        ("rx_a", 2, "A", (0.0, 0.0, 0.0), 1.0, "obj2"),
        ("rx_a", 1, "d", (0.0, 0.0, 0.0), 1.0, "obj3"),
        ("rx_a", 1, "A", (0.0, 0.0, 0.0), 1.0, "obj4"),
    ]
    ordered = sorted(unsorted_sources, key=_rxdd_back_stub_sort_key)
    assert [(src[0], src[1], src[2]) for src in ordered] == [
        ("rx_a", 1, "A"),
        ("rx_a", 1, "d"),
        ("rx_a", 2, "A"),
        ("rx_b", 1, "d"),
    ]


def test_append_rxdd_back_stub_sources_for_rxdd_left_and_right() -> None:
    storage: list[_StubSource] = []
    start_xyz = (1.0, 2.0, 3.0)
    end_xyz = (4.0, 5.0, 6.0)
    trace = 0.8
    source_object_name = "coil_rx_dd_g1"

    _append_rxdd_back_stub_sources_if_needed(
        kind="rx_dd",
        board_id="rx_main",
        instance_index=0,
        start_xyz=start_xyz,
        end_xyz=end_xyz,
        start_label="B",
        end_label="c",
        trace=trace,
        source_object_name=source_object_name,
        storage=storage,
    )
    _append_rxdd_back_stub_sources_if_needed(
        kind="tx_dd",
        board_id="rx_main",
        instance_index=0,
        start_xyz=start_xyz,
        end_xyz=end_xyz,
        start_label="A",
        end_label="a",
        trace=trace,
        source_object_name=source_object_name,
        storage=storage,
    )
    _append_rxdd_back_stub_sources_if_needed(
        kind="rx_dd",
        board_id="rx_main",
        instance_index=0,
        start_xyz=start_xyz,
        end_xyz=end_xyz,
        start_label="A",
        end_label="d",
        trace=trace,
        source_object_name=source_object_name,
        storage=storage,
    )

    assert storage == [
        ("rx_main", 0, "B", start_xyz, trace, source_object_name),
        ("rx_main", 0, "c", end_xyz, trace, source_object_name),
        ("rx_main", 0, "A", start_xyz, trace, source_object_name),
        ("rx_main", 0, "d", end_xyz, trace, source_object_name),
    ]


def test_rxdd_endpoint_partition_routes_d_b_to_connect_and_a_c_to_port() -> None:
    assert _is_rxdd_connect_stub_endpoint("d") is True
    assert _is_rxdd_connect_stub_endpoint("B") is True
    assert _is_rxdd_connect_stub_endpoint("A") is False
    assert _is_rxdd_connect_stub_endpoint("c") is False

    assert _is_rxdd_port_stub_endpoint("A") is True
    assert _is_rxdd_port_stub_endpoint("c") is True
    assert _is_rxdd_port_stub_endpoint("B") is False
    assert _is_rxdd_port_stub_endpoint("d") is False


def test_rxdd_back_stub_bridge_edge_uses_back_face_with_two_points() -> None:
    edge = _rxdd_back_stub_bridge_edge(anchor_xyz=(10.0, 20.0, 30.0), trace=2.0)
    assert edge == ((7.0, 19.0, 29.0), (7.0, 19.0, 31.0))


def test_rxdd_back_stub_bridge_edge_supports_custom_minus_x_length() -> None:
    edge = _rxdd_back_stub_bridge_edge(anchor_xyz=(10.0, 20.0, 30.0), trace=2.0, length=1.0)
    assert edge == ((9.0, 19.0, 29.0), (9.0, 19.0, 31.0))


def test_rxdd_back_stub_bridge_edge_rejects_non_positive_trace() -> None:
    with pytest.raises(ValueError, match=r"trace must be > 0"):
        _rxdd_back_stub_bridge_edge(anchor_xyz=(1.0, 2.0, 3.0), trace=0.0)


def test_txdd_start_stub_port_edge_uses_feed_role_external_face_with_two_points() -> None:
    feed_in_edge = _txdd_start_stub_port_edge(anchor_xyz=(10.0, 20.0, 30.0), trace=2.0, role="feed_in")
    feed_out_edge = _txdd_start_stub_port_edge(anchor_xyz=(10.0, 20.0, 30.0), trace=2.0, role="feed_out")
    assert feed_in_edge == ((9.0, 21.0, 31.0), (11.0, 21.0, 31.0))
    assert feed_out_edge == ((9.0, 21.0, 31.0), (11.0, 21.0, 31.0))


def test_txdd_start_stub_port_edge_rejects_non_positive_trace() -> None:
    with pytest.raises(ValueError, match=r"trace must be > 0"):
        _txdd_start_stub_port_edge(anchor_xyz=(1.0, 2.0, 3.0), trace=0.0, role="feed_in")


@pytest.mark.parametrize(
    ("plane", "expected_origin", "expected_sizes"),
    [
        ("XY", [0.9, 1.9, 1.3], [10.2, 20.2, 1.6]),
        ("YZ", [-0.7, 1.9, 2.9], [1.6, 20.2, 0.7]),
        ("ZX", [0.9, 0.3, 2.9], [10.2, 1.6, 0.7]),
    ],
)
def test_fr4_box_from_plane_bbox_applies_0p1mm_overlap_all_planes(
    plane: str, expected_origin: list[float], expected_sizes: list[float]
) -> None:
    origin, sizes = _fr4_box_from_plane_bbox(
        plane=cast(Literal["XY", "YZ", "ZX"], plane),
        bbox=[1.0, 2.0, 3.0, 11.0, 22.0, 3.5],
        pcb_thickness=1.6,
        overlap_mm=FR4_SUBTRACT_OVERLAP_MM,
        eps_len=1e-6,
    )
    assert origin == pytest.approx(expected_origin)
    assert sizes == pytest.approx(expected_sizes)


def test_fr4_box_from_plane_bbox_keeps_positive_thickness_via_overlap() -> None:
    origin, sizes = _fr4_box_from_plane_bbox(
        plane="XY",
        bbox=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        pcb_thickness=0.0,
        overlap_mm=FR4_SUBTRACT_OVERLAP_MM,
        eps_len=1e-6,
    )
    assert origin == pytest.approx([-0.1, -0.1, -0.1])
    assert sizes[0] > 0.0
    assert sizes[1] > 0.0
    assert sizes[2] > 0.0

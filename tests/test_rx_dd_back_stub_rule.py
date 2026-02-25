from __future__ import annotations

import pytest

from peetsfea.backend.pyaedt.geometry.build import _append_rxdd_back_stub_sources_if_needed
from peetsfea.backend.pyaedt.geometry.build_rx_dd import (
    _rxdd_back_stub_bridge_edge,
    _rxdd_back_stub_origin_and_sizes,
    _rxdd_back_stub_sort_key,
)


def test_rxdd_back_stub_origin_and_sizes_use_trace_square_and_minus_x() -> None:
    anchor = (10.0, 20.0, 30.0)
    trace = 1.2
    origin, sizes = _rxdd_back_stub_origin_and_sizes(anchor_xyz=anchor, trace=trace)
    assert origin == [7.0, 19.4, 29.4]
    assert sizes == [3.0, 1.2, 1.2]


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
    storage: list[tuple[str, int, str, tuple[float, float, float], float, str]] = []
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


def test_rxdd_back_stub_bridge_edge_uses_back_face_with_two_points() -> None:
    edge = _rxdd_back_stub_bridge_edge(anchor_xyz=(10.0, 20.0, 30.0), trace=2.0)
    assert edge == ((7.0, 19.0, 29.0), (7.0, 19.0, 31.0))


def test_rxdd_back_stub_bridge_edge_rejects_non_positive_trace() -> None:
    with pytest.raises(ValueError, match=r"trace must be > 0"):
        _rxdd_back_stub_bridge_edge(anchor_xyz=(1.0, 2.0, 3.0), trace=0.0)

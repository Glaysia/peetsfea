from __future__ import annotations

import pytest

from peetsfea.backend.pyaedt.geometry.placement_rules import _realized_txdd_geometry, _txdd_right_points


def test_realized_txdd_geometry_keeps_single_layer_geometry() -> None:
    assert _realized_txdd_geometry(
        turns=5,
        outer_x=120.0,
        outer_y=80.0,
        trace=1.2,
        gap=0.3,
        instance_count=2,
        layer_index=0,
    ) == (5, 120.0, 80.0)


def test_realized_txdd_geometry_uses_one_pitch_inset_on_lower_layer_for_four_layer_tx_dd() -> None:
    lower = _realized_txdd_geometry(
        turns=5,
        outer_x=120.0,
        outer_y=80.0,
        trace=1.2,
        gap=0.3,
        instance_count=4,
        layer_index=0,
    )
    upper = _realized_txdd_geometry(
        turns=5,
        outer_x=120.0,
        outer_y=80.0,
        trace=1.2,
        gap=0.3,
        instance_count=4,
        layer_index=1,
    )
    assert lower == (5, 118.5, 78.5)
    assert upper == (5, 120.0, 80.0)


def test_realized_txdd_geometry_rejects_invalid_lower_layer_result() -> None:
    with pytest.raises(ValueError, match="lower-layer interleave contract violation"):
        _realized_txdd_geometry(
            turns=6,
            outer_x=12.0,
            outer_y=12.0,
            trace=1.2,
            gap=0.3,
            instance_count=4,
            layer_index=0,
        )


def test_txdd_right_points_use_gap_centered_lower_layer_interleave_with_aligned_a_for_four_layer_tx_dd() -> None:
    lower_points = _txdd_right_points(
        turns=5,
        outer_x=120.0,
        outer_y=80.0,
        trace=1.2,
        gap=0.3,
        instance_count=4,
        layer_index=0,
    )
    upper_points = _txdd_right_points(
        turns=5,
        outer_x=120.0,
        outer_y=80.0,
        trace=1.2,
        gap=0.3,
        instance_count=4,
        layer_index=1,
    )
    pitch = 1.2 + 0.3
    lower_ring_points = lower_points[:-2]
    assert max(abs(point[0]) for point in lower_ring_points) == pytest.approx(
        max(abs(point[0]) for point in upper_points) - (pitch / 2.0)
    )
    assert max(abs(point[1]) for point in lower_ring_points) == pytest.approx(
        max(abs(point[1]) for point in upper_points) - (pitch / 2.0)
    )
    assert lower_points[-1][0] == pytest.approx(upper_points[0][0])
    assert lower_points[-1][1] == pytest.approx(upper_points[0][1])


def test_txdd_right_points_keeps_two_layer_contract_unchanged() -> None:
    points = _txdd_right_points(
        turns=3,
        outer_x=100.0,
        outer_y=60.0,
        trace=1.0,
        gap=0.25,
        instance_count=2,
        layer_index=0,
    )
    assert len(points) > 2

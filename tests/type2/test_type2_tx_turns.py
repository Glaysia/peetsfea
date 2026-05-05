from __future__ import annotations

from typing import cast

import pytest

from peetsfea.type2_tx_turns import allocate_parallel_turns
from peetsfea.type2_tx_turns import allocate_series_turns
from peetsfea.type2_tx_turns import normalized_tx_plane_distances
from peetsfea.type2_tx_turns import resolve_tx_turns
from peetsfea.type2_tx_turns import TxConnectionMode
from peetsfea.type2_tx_turns import turn_weights


def test_normalized_tx_plane_distances_uses_rx_xy_center_and_preserves_order() -> None:
    centers = ((2.0, 1.0, 0.0), (1.0, 3.0, 7.0), (4.0, 5.0, -3.0))
    distances = normalized_tx_plane_distances(centers, rx_center_xyz=(1.0, 1.0, 99.0))
    assert distances == pytest.approx((1.0 / 5.0, 2.0 / 5.0, 1.0))


def test_normalized_tx_plane_distances_with_zero_spread() -> None:
    centers = ((10.0, 5.0, 0.0), (10.0, 5.0, -1.0))
    assert normalized_tx_plane_distances(centers, rx_center_xyz=(10.0, 5.0, 123.0)) == (0.0, 0.0)


def test_turn_weights_positive_guard() -> None:
    centers = ((0.0, 0.0, 0.0), (5.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="turn_weight polynomial must be > 0"):
        turn_weights(centers, rx_center_xyz=(0.0, 0.0, 0.0), a=0.0, b=0.0, c=0.0)


def test_turn_weights_polynomial_and_max1_scaling() -> None:
    centers = ((0.0, 0.0, 0.0), (3.0, 4.0, 0.0))
    weights = turn_weights(centers, rx_center_xyz=(0.0, 0.0, 0.0), a=1.0, b=1.0, c=0.0)
    assert weights == (1.0, 2.0)


def test_allocate_series_turns_3x3_equivalent_turn_count_31_is_valid_only_with_sum_at_most_31() -> None:
    centers = (
        (-1.0, -1.0, 0.0),
        (0.0, -1.0, 0.0),
        (1.0, -1.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (-1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, 1.0, 0.0),
    )
    turns = allocate_series_turns(
        centers,
        rx_center_xyz=(0.0, 0.0, 0.0),
        equivalent_turn_count=31,
        turn_weight_a=2.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    assert sum(turns) <= 31
    assert min(turns) >= 1
    assert min(turns) < max(turns)


def test_allocate_series_turns_rejects_equivalent_turn_count_below_coil_count() -> None:
    centers = (
        (-1.0, -1.0, 0.0),
        (0.0, -1.0, 0.0),
        (1.0, -1.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (-1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, 1.0, 0.0),
    )
    with pytest.raises(ValueError):
        allocate_series_turns(
            centers,
            rx_center_xyz=(0.0, 0.0, 0.0),
            equivalent_turn_count=8,
            turn_weight_a=1.0,
            turn_weight_b=0.0,
            turn_weight_c=0.0,
        )


def test_allocate_parallel_turns_3x3_equivalent_turn_count_1_over_9_allocates_one_turn_each() -> None:
    centers = (
        (-1.0, -1.0, 0.0),
        (0.0, -1.0, 0.0),
        (1.0, -1.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (-1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, 1.0, 0.0),
    )
    turns = allocate_parallel_turns(
        centers,
        rx_center_xyz=(0.0, 0.0, 0.0),
        equivalent_turn_count=1.0 / 9.0,
        turn_weight_a=1.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    assert turns == (1, 1, 1, 1, 1, 1, 1, 1, 1)


def test_allocate_parallel_turns_3x3_equivalent_turn_count_10_over_9_allocates_ten_turns_each() -> None:
    centers = (
        (-1.0, -1.0, 0.0),
        (0.0, -1.0, 0.0),
        (1.0, -1.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (-1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, 1.0, 0.0),
    )
    turns = allocate_parallel_turns(
        centers,
        rx_center_xyz=(0.0, 0.0, 0.0),
        equivalent_turn_count=10.0 / 9.0,
        turn_weight_a=1.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    assert turns == (10, 10, 10, 10, 10, 10, 10, 10, 10)


def test_allocate_parallel_turns_3x3_equivalent_turn_count_4_is_infeasible() -> None:
    centers = (
        (-1.0, -1.0, 0.0),
        (0.0, -1.0, 0.0),
        (1.0, -1.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (-1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, 1.0, 0.0),
    )
    with pytest.raises(ValueError):
        allocate_parallel_turns(
            centers,
            rx_center_xyz=(0.0, 0.0, 0.0),
            equivalent_turn_count=4.0,
            turn_weight_a=1.0,
            turn_weight_b=0.0,
            turn_weight_c=0.0,
        )


def test_allocate_series_turns_rejects_equivalent_turn_count_above_31() -> None:
    centers = (
        (-1.0, -1.0, 0.0),
        (0.0, -1.0, 0.0),
        (1.0, -1.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (-1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, 1.0, 0.0),
    )
    with pytest.raises(ValueError):
        allocate_series_turns(
            centers,
            rx_center_xyz=(0.0, 0.0, 0.0),
            equivalent_turn_count=32,
            turn_weight_a=1.0,
            turn_weight_b=0.0,
            turn_weight_c=0.0,
        )


def test_allocate_series_turns_rejects_geometry_turn_cap_overflow() -> None:
    centers = ((-2.0, 0.0, 0.0), (0.0, 0.0, 0.0), (2.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="exceeds geometry turn cap"):
        allocate_series_turns(
            centers,
            rx_center_xyz=(0.0, 0.0, 0.0),
            equivalent_turn_count=10,
            turn_weight_a=1.0,
            turn_weight_b=0.0,
            turn_weight_c=0.0,
            max_turn_count=3,
        )


def test_resolve_tx_turns_router_parallel_and_series_modes() -> None:
    centers = ((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    parallel_turns = resolve_tx_turns(
        centers,
        rx_center_xyz=(0.0, 0.0, 0.0),
        connection_mode=0,
        equivalent_turn_count=1.0,
        turn_weight_a=1.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    series_turns = resolve_tx_turns(
        centers,
        rx_center_xyz=(0.0, 0.0, 0.0),
        connection_mode=1,
        equivalent_turn_count=4.0,
        turn_weight_a=1.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    assert parallel_turns[0] == parallel_turns[1]
    assert series_turns[0] == series_turns[1]


def test_resolve_tx_turns_rejects_invalid_mode() -> None:
    with pytest.raises(ValueError, match="unsupported connection_mode"):
        resolve_tx_turns(
            ((0.0, 0.0, 0.0),),
            rx_center_xyz=(0.0, 0.0, 0.0),
            connection_mode=cast(TxConnectionMode, 99),
            equivalent_turn_count=1.0,
            turn_weight_a=1.0,
            turn_weight_b=0.0,
            turn_weight_c=0.0,
        )

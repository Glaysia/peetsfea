from __future__ import annotations

from typing import cast

import pytest

from peetsfea.type2_tx_turns import allocate_parallel_turns
from peetsfea.type2_tx_turns import allocate_series_turns
from peetsfea.type2_tx_turns import normalized_x_distances
from peetsfea.type2_tx_turns import resolve_tx_turns
from peetsfea.type2_tx_turns import TxConnectionMode
from peetsfea.type2_tx_turns import turn_weights


def test_normalized_x_distances_uses_rx_center_and_preserves_order() -> None:
    centers = ((1.0, 0.0, 0.0), (4.0, 0.0, 0.0), (6.0, 0.0, 0.0))
    assert normalized_x_distances(centers, rx_center_x=2.0) == (0.25, 0.5, 1.0)


def test_normalized_x_distances_with_zero_spread() -> None:
    centers = ((10.0, 0.0, 0.0), (10.0, 5.0, -1.0))
    assert normalized_x_distances(centers, rx_center_x=10.0) == (0.0, 0.0)


def test_turn_weights_positive_guard() -> None:
    centers = ((0.0, 0.0, 0.0), (5.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="turn_weight polynomial must be > 0"):
        turn_weights(centers, rx_center_x=0.0, a=0.0, b=0.0, c=0.0)


def test_turn_weights_polynomial_and_max1_scaling() -> None:
    centers = ((0.0, 0.0, 0.0), (4.0, 0.0, 0.0))
    weights = turn_weights(centers, rx_center_x=0.0, a=1.0, b=1.0, c=0.0)
    assert weights == (1.0, 2.0)


def test_allocate_series_turns_largest_remainder_with_1_seed() -> None:
    centers = ((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    turns = allocate_series_turns(
        centers,
        rx_center_x=0.0,
        series_total_turn_count=5,
        turn_weight_a=2.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    assert turns == (3, 2)
    assert sum(turns) == 5
    assert min(turns) >= 1


def test_allocate_series_turns_rejects_low_total() -> None:
    centers = ((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (3.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="series_total_turn_count must be >= coil_count"):
        allocate_series_turns(
            centers,
            rx_center_x=0.0,
            series_total_turn_count=2,
            turn_weight_a=1.0,
            turn_weight_b=0.0,
            turn_weight_c=0.0,
        )


def test_allocate_parallel_turns_3x3_total_budget_36_equal_weights_allocates_4_each() -> None:
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
        rx_center_x=0.0,
        parallel_total_turn_count=36,
        turn_weight_a=1.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    assert turns == (4, 4, 4, 4, 4, 4, 4, 4, 4)


def test_allocate_parallel_turns_1x1_total_budget_36_allocates_36() -> None:
    centers = ((0.0, 0.0, 0.0),)
    turns = allocate_parallel_turns(
        centers,
        rx_center_x=0.0,
        parallel_total_turn_count=36,
        turn_weight_a=1.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    assert turns == (36,)


def test_allocate_parallel_turns_rejects_total_below_coil_count() -> None:
    centers = ((-1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="parallel_total_turn_count must be >= coil_count"):
        allocate_parallel_turns(
            centers,
            rx_center_x=0.0,
            parallel_total_turn_count=2,
            turn_weight_a=1.0,
            turn_weight_b=0.0,
            turn_weight_c=0.0,
        )


def test_allocate_parallel_turns_largest_remainder_with_weight_tie_break() -> None:
    centers = ((-2.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    turns = allocate_parallel_turns(
        centers,
        rx_center_x=0.0,
        parallel_total_turn_count=5,
        turn_weight_a=2.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    assert turns == (3, 2)


def test_allocate_parallel_turns_respects_geometry_turn_cap() -> None:
    centers = ((-2.0, 0.0, 0.0), (0.0, 0.0, 0.0), (2.0, 0.0, 0.0))
    turns = allocate_parallel_turns(
        centers,
        rx_center_x=0.0,
        parallel_total_turn_count=18,
        turn_weight_a=1.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
        max_turn_count=8,
    )
    assert max(turns) <= 8


def test_allocate_series_turns_rejects_geometry_turn_cap_overflow() -> None:
    centers = ((-2.0, 0.0, 0.0), (0.0, 0.0, 0.0), (2.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="exceeds geometry turn cap"):
        allocate_series_turns(
            centers,
            rx_center_x=0.0,
            series_total_turn_count=10,
            turn_weight_a=1.0,
            turn_weight_b=0.0,
            turn_weight_c=0.0,
            max_turn_count=3,
        )


def test_resolve_tx_turns_router_parallel_and_series_modes() -> None:
    centers = ((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    parallel_turns = resolve_tx_turns(
        centers,
        rx_center_x=0.0,
        connection_mode=0,
        relevant_turn_count=8.0,
        turn_weight_a=1.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    series_turns = resolve_tx_turns(
        centers,
        rx_center_x=0.0,
        connection_mode=1,
        relevant_turn_count=4.0,
        turn_weight_a=1.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    assert parallel_turns == (4, 4)
    assert series_turns == (2, 2)


def test_resolve_tx_turns_rejects_invalid_mode() -> None:
    with pytest.raises(ValueError, match="unsupported connection_mode"):
        resolve_tx_turns(
            ((0.0, 0.0, 0.0),),
            rx_center_x=0.0,
            connection_mode=cast(TxConnectionMode, 99),
            relevant_turn_count=1.0,
            turn_weight_a=1.0,
            turn_weight_b=0.0,
            turn_weight_c=0.0,
        )

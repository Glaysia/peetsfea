from __future__ import annotations

import math
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


def test_allocate_series_turns_symmetric_group_may_exceed_target_budget() -> None:
    centers = ((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    turns = allocate_series_turns(
        centers,
        rx_center_xyz=(0.0, 0.0, 0.0),
        series_total_turn_count=5,
        turn_weight_a=2.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    assert turns[0] == turns[1]
    assert sum(turns) >= 5
    assert min(turns) >= 1


def test_allocate_series_turns_rejects_low_total() -> None:
    centers = ((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (3.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="series_total_turn_count must be >= coil_count"):
        allocate_series_turns(
            centers,
            rx_center_xyz=(0.0, 0.0, 0.0),
            series_total_turn_count=2,
            turn_weight_a=1.0,
            turn_weight_b=0.0,
            turn_weight_c=0.0,
        )


def test_allocate_parallel_turns_1x3_center_favored_weights_target5() -> None:
    centers = ((-1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    turns = allocate_parallel_turns(
        centers,
        rx_center_xyz=(0.0, 0.0, 0.0),
        parallel_total_turn_count=5,
        turn_weight_a=1.0,
        turn_weight_b=-0.9,
        turn_weight_c=0.0,
    )
    assert turns == (1, 3, 1)
    assert sum(turns) >= 5


def test_allocate_parallel_turns_1x3_edge_favored_weights_target5() -> None:
    centers = ((-1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    turns = allocate_parallel_turns(
        centers,
        rx_center_xyz=(0.0, 0.0, 0.0),
        parallel_total_turn_count=5,
        turn_weight_a=1.0,
        turn_weight_b=1.0,
        turn_weight_c=0.0,
    )
    assert turns == (2, 1, 2)
    assert sum(turns) >= 5


def test_allocate_parallel_turns_3x3_equal_2d_distance_pairs_have_equal_counts() -> None:
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
        parallel_total_turn_count=11,
        turn_weight_a=1.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    rx_xy = (0.0, 0.0)
    groups: dict[float, list[int]] = {}
    for index, (x_value, y_value, _z_value) in enumerate(centers):
        distance = math.hypot(x_value - rx_xy[0], y_value - rx_xy[1])
        if distance in groups:
            groups[distance].append(index)
        else:
            groups[distance] = [index]
    for indices in groups.values():
        first_turn = turns[indices[0]]
        for index in indices[1:]:
            assert turns[index] == first_turn
    assert sum(turns) >= 11


def test_allocate_parallel_turns_1x1_total_budget_36_allocates_36() -> None:
    centers = ((0.0, 0.0, 0.0),)
    turns = allocate_parallel_turns(
        centers,
        rx_center_xyz=(0.0, 0.0, 0.0),
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
            rx_center_xyz=(0.0, 0.0, 0.0),
            parallel_total_turn_count=2,
            turn_weight_a=1.0,
            turn_weight_b=0.0,
            turn_weight_c=0.0,
        )


def test_allocate_parallel_turns_2x3_equal_2d_distance_pairs_have_equal_counts() -> None:
    centers = (
        (-1.0, -1.0, 0.0),
        (0.0, -1.0, 0.0),
        (1.0, -1.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
    )
    turns = allocate_parallel_turns(
        centers,
        rx_center_xyz=(0.0, 0.0, 0.0),
        parallel_total_turn_count=7,
        turn_weight_a=1.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    rx_xy = (0.0, 0.0)
    groups: dict[float, list[int]] = {}
    for index, (x_value, y_value, _z_value) in enumerate(centers):
        distance = math.hypot(x_value - rx_xy[0], y_value - rx_xy[1])
        if distance in groups:
            groups[distance].append(index)
        else:
            groups[distance] = [index]
    for indices in groups.values():
        first_turn = turns[indices[0]]
        for index in indices[1:]:
            assert turns[index] == first_turn
    assert sum(turns) >= 7


def test_allocate_parallel_turns_respects_geometry_turn_cap() -> None:
    centers = ((-2.0, 0.0, 0.0), (0.0, 0.0, 0.0), (2.0, 0.0, 0.0))
    turns = allocate_parallel_turns(
        centers,
        rx_center_xyz=(0.0, 0.0, 0.0),
        parallel_total_turn_count=14,
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
            rx_center_xyz=(0.0, 0.0, 0.0),
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
        rx_center_xyz=(0.0, 0.0, 0.0),
        connection_mode=0,
        relevant_turn_count=8.0,
        turn_weight_a=1.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    series_turns = resolve_tx_turns(
        centers,
        rx_center_xyz=(0.0, 0.0, 0.0),
        connection_mode=1,
        relevant_turn_count=4.0,
        turn_weight_a=1.0,
        turn_weight_b=0.0,
        turn_weight_c=0.0,
    )
    assert parallel_turns[0] == parallel_turns[1]
    assert series_turns[0] == series_turns[1]
    assert sum(parallel_turns) >= 8
    assert sum(series_turns) >= 4


def test_resolve_tx_turns_rejects_invalid_mode() -> None:
    with pytest.raises(ValueError, match="unsupported connection_mode"):
        resolve_tx_turns(
            ((0.0, 0.0, 0.0),),
            rx_center_xyz=(0.0, 0.0, 0.0),
            connection_mode=cast(TxConnectionMode, 99),
            relevant_turn_count=1.0,
            turn_weight_a=1.0,
            turn_weight_b=0.0,
            turn_weight_c=0.0,
        )

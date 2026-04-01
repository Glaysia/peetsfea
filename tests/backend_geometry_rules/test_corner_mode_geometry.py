from __future__ import annotations

from math import dist

from peetsfea.backend.pyaedt.geometry.rules.placement_rules import (
    _build_rxdd_right_points_A_to_d_cw,
    _txdd_right_points,
)
from peetsfea.backend.pyaedt.geometry.rules.spiral_points import _build_rect_spiral_centerline_absolute


def _assert_positive_segments(points: list[tuple[float, float, float]] | list[list[float]]) -> None:
    for first, second in zip(points, points[1:], strict=False):
        first_xyz = tuple(float(v) for v in first)
        second_xyz = tuple(float(v) for v in second)
        assert dist(first_xyz, second_xyz) > 0.0


def _has_diagonal_segment(points: list[tuple[float, float, float]] | list[list[float]]) -> bool:
    for first, second in zip(points, points[1:], strict=False):
        dx = abs(float(second[0]) - float(first[0]))
        dy = abs(float(second[1]) - float(first[1]))
        if dx > 0.0 and dy > 0.0:
            return True
    return False


def test_rect_spiral_corner_mode_blunt_preserves_endpoints_and_adds_points() -> None:
    sharp = _build_rect_spiral_centerline_absolute(
        turns=2,
        outer_x=40.0,
        outer_y=60.0,
        trace=2.0,
        gap=1.0,
        z=0.0,
        corner_mode=0,
    )
    blunt = _build_rect_spiral_centerline_absolute(
        turns=2,
        outer_x=40.0,
        outer_y=60.0,
        trace=2.0,
        gap=1.0,
        z=0.0,
        corner_mode=1,
    )

    assert blunt[0] == sharp[0]
    assert blunt[-1] == sharp[-1]
    assert len(blunt) > len(sharp)
    assert _has_diagonal_segment(blunt)
    _assert_positive_segments(blunt)


def test_rxdd_corner_mode_blunt_keeps_endpoint_contract_without_zero_length_segments() -> None:
    sharp = _build_rxdd_right_points_A_to_d_cw(
        turns=2,
        outer_x=80.0,
        outer_y=60.0,
        trace=2.0,
        gap=1.0,
        corner_mode=0,
    )
    blunt = _build_rxdd_right_points_A_to_d_cw(
        turns=2,
        outer_x=80.0,
        outer_y=60.0,
        trace=2.0,
        gap=1.0,
        corner_mode=1,
    )

    assert blunt[0] == sharp[0]
    assert blunt[-1] == sharp[-1]
    assert len(blunt) > len(sharp)
    assert _has_diagonal_segment(blunt)
    _assert_positive_segments(blunt)


def test_txdd_corner_mode_blunt_one_turn_keeps_endpoints_without_zero_length_segments() -> None:
    sharp = _txdd_right_points(
        turns=1,
        outer_x=80.0,
        outer_y=60.0,
        trace=2.0,
        gap=1.0,
        instance_count=2,
        layer_index=None,
        corner_mode=0,
    )
    blunt = _txdd_right_points(
        turns=1,
        outer_x=80.0,
        outer_y=60.0,
        trace=2.0,
        gap=1.0,
        instance_count=2,
        layer_index=None,
        corner_mode=1,
    )

    assert blunt[0] == sharp[0]
    assert blunt[-1] == sharp[-1]
    assert len(blunt) > len(sharp)
    assert _has_diagonal_segment(blunt)
    _assert_positive_segments(blunt)

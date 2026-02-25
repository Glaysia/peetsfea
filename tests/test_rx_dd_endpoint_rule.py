from __future__ import annotations

from typing import Literal

import pytest

from peetsfea.backend.pyaedt.geometry.placement_rules import (
    _apply_rxdd_endpoint_rule,
    _build_polarity,
    _instance_side,
    _validate_rxdd_single_layer_count,
)
from peetsfea.types.manifest import CoilPolaritySpec, GroupEndpointEntry


def _rx_endpoint(*, instance_index: int, board_id: str = "rx_main_0") -> GroupEndpointEntry:
    return {
        "group_kind": "rx_dd",
        "group_instance_index": instance_index,
        "board_id": board_id,
        "start_xyz": (0.0, 0.0, 0.0),
        "end_xyz": (1.0, 0.0, 0.0),
        "start_label": "A",
        "end_label": "a",
        "present": True,
    }


def _rx_polarity(
    *,
    instance_index: int,
    side: Literal["left", "right", "center"],
    current_direction: Literal["cw", "ccw"] = "cw",
    board_id: str = "rx_main_0",
) -> CoilPolaritySpec:
    return {
        "group_kind": "rx_dd",
        "group_instance_index": instance_index,
        "board_id": board_id,
        "instance_side": side,
        "current_direction": current_direction,
        "b_field_direction": "into_wall",
    }


def test_apply_rxdd_endpoint_rule_maps_left_and_right_labels() -> None:
    endpoints = [_rx_endpoint(instance_index=0), _rx_endpoint(instance_index=1)]
    polarity: list[CoilPolaritySpec] = [
        _rx_polarity(instance_index=0, side="left", current_direction="ccw"),
        _rx_polarity(instance_index=1, side="right", current_direction="cw"),
    ]

    _apply_rxdd_endpoint_rule(endpoints, polarity)

    by_index = {entry["group_instance_index"]: entry for entry in endpoints}
    assert by_index[0]["start_label"] == "C"
    assert by_index[0]["end_label"] == "b"
    assert by_index[1]["start_label"] == "a"
    assert by_index[1]["end_label"] == "D"


def test_apply_rxdd_endpoint_rule_supports_single_side_only_input() -> None:
    endpoints = [_rx_endpoint(instance_index=0)]
    polarity: list[CoilPolaritySpec] = [_rx_polarity(instance_index=0, side="left", current_direction="ccw")]

    _apply_rxdd_endpoint_rule(endpoints, polarity)

    assert endpoints[0]["start_label"] == "C"
    assert endpoints[0]["end_label"] == "b"


def test_apply_rxdd_endpoint_rule_rejects_center_side() -> None:
    endpoints = [_rx_endpoint(instance_index=0)]
    polarity: list[CoilPolaritySpec] = [_rx_polarity(instance_index=0, side="center")]

    with pytest.raises(ValueError, match=r"instance_side must be left or right"):
        _apply_rxdd_endpoint_rule(endpoints, polarity)


@pytest.mark.parametrize("instance_count", [1, 3, 4])
def test_validate_rxdd_single_layer_count_rejects_non_two(instance_count: int) -> None:
    with pytest.raises(ValueError, match=r"only selected_count=2 is supported"):
        _validate_rxdd_single_layer_count(instance_count)


def test_validate_rxdd_single_layer_count_accepts_two() -> None:
    _validate_rxdd_single_layer_count(2)


def test_rx_side_axis_convention_and_direction_contract() -> None:
    left_side = _instance_side("rx_dd", (0.0, -1.0, 0.0))
    right_side = _instance_side("rx_dd", (0.0, 1.0, 0.0))

    assert left_side == "left"
    assert right_side == "right"

    left_direction, _ = _build_polarity("rx_dd", left_side)
    right_direction, _ = _build_polarity("rx_dd", right_side)
    assert left_direction == "ccw"
    assert right_direction == "cw"

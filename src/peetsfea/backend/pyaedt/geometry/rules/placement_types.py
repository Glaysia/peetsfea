from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


_Point2 = tuple[float, float]
_Point3 = tuple[float, float, float]
_GroupInstanceKey = tuple[str, str, int]
_YzDdPairPlacement = tuple[Literal["left", "right"], list[list[float]], float, Literal["cw", "ccw"]]
_UNSET = object()


@dataclass(frozen=True)
class _TxDdRightLocalTopology:
    points: list[list[float]]
    bridge_edge_local: tuple[_Point3, _Point3] | object
    free_terminal_anchor_local: _Point3 | object
    a_anchor_local: _Point3 | object
    terminal_role: Literal[
        "single_right",
        "lower_right",
        "upper_right",
    ]


@dataclass(frozen=True)
class PlacementKernelInput:
    points: list[list[float]]
    trace: float
    terminal: Literal["start", "end"]


@dataclass(frozen=True)
class PlacementKernelOutput:
    edge: tuple[_Point3, _Point3]

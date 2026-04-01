from __future__ import annotations

from typing import Literal

from peetsfea.topology.tx_dd import rank_txdd_right_rows as _rank_txdd_right_rows
from peetsfea.types.manifest import (
    CoilPolaritySpec,
    GroupEndpointEntry,
    ResolvedPcbInstance,
    ResolvedPcbMount,
)

from .placement_shared import _resolve_txdd_counts
from .placement_types import _GroupInstanceKey, _Point3


def _coil_instance_offset(
    kind: str,
    instance_index: int,
    instance_count: int,
    spacing_mm: float,
    *,
    trace_mm: float = 0.0,
) -> _Point3:
    if kind == "tx_vertical":
        if instance_count <= 0:
            raise ValueError(f"tx_vertical selected_count must be >= 1 (actual={instance_count})")
        if instance_index < 0 or instance_index >= instance_count:
            raise ValueError(
                f"tx_vertical instance index out of range (instance_index={instance_index}, instance_count={instance_count})"
            )
        denom = max(1, instance_count - 1)
        d = spacing_mm / float(denom)
        if d < 0.0:
            raise ValueError(f"tx_vertical center gap d must be >= 0 (actual={d})")
        center = (instance_count - 1) / 2.0
        return (0.0, (float(instance_index) - center) * d, 0.0)
    return (0.0, 0.0, 0.0)


def _validate_rxdd_single_layer_count(instance_count: int) -> None:
    if instance_count != 2:
        raise ValueError(
            "rx_dd single-layer contract violation: only instance_count=2 is supported "
            f"(actual={instance_count})"
        )


def _rx_dd_center_offset_y(instance_index: int, instance_count: int, outer_x: float, edge_gap_mm: float) -> float:
    if instance_count < 1:
        raise ValueError("rx_dd selected_count must be >= 1")
    if edge_gap_mm < 0:
        raise ValueError(f"rx_dd edge gap must be >= 0 (actual={edge_gap_mm})")
    center = (instance_count - 1) / 2.0
    pair_center_distance = outer_x + edge_gap_mm
    return (instance_index - center) * pair_center_distance


def _mount_allows_instance(mounts: list[ResolvedPcbMount], kind: str, instance_index: int) -> bool:
    for mount in mounts:
        if mount["kind"] != kind:
            continue
        selector_mode = mount["selector_mode"]
        selector_index = mount["selector_index"]
        if selector_mode == "all":
            return True
        if selector_mode == "index" and selector_index == instance_index:
            return True
    return False


def _instance_side(kind: str, instance_offset: _Point3) -> Literal["left", "right", "center"]:
    if kind in ("tx_dd", "rx_dd"):
        if instance_offset[1] < 0:
            return "left"
        if instance_offset[1] > 0:
            return "right"
        return "center"
    return "center"


def _build_polarity(
    kind: str,
    side: Literal["left", "right", "center"],
) -> Literal["cw", "ccw"]:
    if kind == "tx_vertical":
        if side == "right":
            return "cw"
        if side == "left":
            return "ccw"
        return "ccw"
    if side == "right":
        return "cw"
    if side == "left":
        return "ccw"
    return "cw"


def _group_endpoint_key(entry: GroupEndpointEntry) -> _GroupInstanceKey:
    return (entry["group_kind"], entry["board_id"], entry["group_instance_index"])


def _coil_polarity_key(entry: CoilPolaritySpec) -> _GroupInstanceKey:
    return (entry["group_kind"], entry["board_id"], entry["group_instance_index"])


def _endpoint_z_center(entry: GroupEndpointEntry) -> float:
    return (entry["start_xyz"][2] + entry["end_xyz"][2]) / 2.0


def _txdd_right_layer_rank_by_z(
    *,
    selected_pcbs: list[ResolvedPcbInstance],
    layer_count: object,
    instance_count: object,
    transform_dz: float,
    tx_dd_anchor_z: float,
) -> dict[int, int]:
    resolved_layer_count, resolved_instance_count = _resolve_txdd_counts(
        layer_count=layer_count,
        instance_count=instance_count,
    )
    if resolved_layer_count != 2:
        return {}
    rows: list[tuple[float, str, int]] = []
    for instance_index in range(resolved_instance_count):
        if instance_index % 2 == 0:
            continue
        candidates: list[tuple[str, float]] = []
        for pcb in selected_pcbs:
            if not pcb["present"]:
                continue
            if _mount_allows_instance(pcb["mounts"], "tx_dd", instance_index):
                board_id = pcb["id"]
                board_z = pcb["position"][2]
                final_z = tx_dd_anchor_z - board_z + transform_dz
                candidates.append((board_id, final_z))
        if len(candidates) != 1:
            raise ValueError(
                "tx_dd right endpoint contract violation: each right instance must map to exactly one mounted board "
                f"(instance_index={instance_index}, candidates={len(candidates)})"
            )
        board_id, z_center = candidates[0]
        rows.append((z_center, board_id, instance_index))
    return _rank_txdd_right_rows(rows, layer_count=resolved_layer_count, instance_count=resolved_instance_count)

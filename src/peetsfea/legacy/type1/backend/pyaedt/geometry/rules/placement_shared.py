from __future__ import annotations

from typing import cast

from peetsfea.legacy.type1.topology.tx_dd import (
    txdd_instance_count_from_layer_count as _txdd_instance_count_from_layer_count,
    txdd_layer_count_from_instance_count as _txdd_layer_count_from_instance_count,
)

from .placement_types import _UNSET


def _normalize_optional_int(value: object) -> int | object:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return _UNSET


def _normalize_layer_index_for_shared(layer_count: int, layer_index: object) -> int:
    if layer_count == 1:
        return 0
    if isinstance(layer_index, int) and not isinstance(layer_index, bool):
        if layer_index in (0, 1):
            return layer_index
        raise ValueError(f"tx_dd layer index must be 0 or 1 for layer_count=2 (actual={layer_index})")
    raise ValueError(f"tx_dd layer index must be 0 or 1 for layer_count=2 (actual={layer_index})")


def _resolve_txdd_counts(*, layer_count: object = _UNSET, instance_count: object = _UNSET) -> tuple[int, int]:
    normalized_layer_count = _normalize_optional_int(layer_count)
    normalized_instance_count = _normalize_optional_int(instance_count)
    if normalized_layer_count is not _UNSET:
        resolved_layer_count = cast(int, normalized_layer_count)
        if resolved_layer_count not in (1, 2):
            raise ValueError(f"tx_dd layer_count must be 1 or 2 (actual={resolved_layer_count})")
        resolved_instance_count = _txdd_instance_count_from_layer_count(resolved_layer_count)
        if normalized_instance_count is not _UNSET and cast(int, normalized_instance_count) != resolved_instance_count:
            raise ValueError(
                "tx_dd layer_count/instance_count mismatch "
                f"(layer_count={resolved_layer_count}, instance_count={cast(int, normalized_instance_count)}, "
                f"expected_instance_count={resolved_instance_count})"
            )
        return resolved_layer_count, resolved_instance_count
    if normalized_instance_count is _UNSET:
        raise ValueError("tx_dd layer_count or instance_count must be provided")
    resolved_instance_count = cast(int, normalized_instance_count)
    return _txdd_layer_count_from_instance_count(resolved_instance_count), resolved_instance_count

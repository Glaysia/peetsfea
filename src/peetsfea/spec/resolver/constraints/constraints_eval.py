from __future__ import annotations

from .constraint_evaluator import compare, evaluate_constraints, resolve_operand_ref, validate_constraints
from .constraint_functions import eval_numeric_expr, resolve_func_ref
from .constraint_paths import (
    _mount_allows_instance,
    _tx_dd_center_y_and_layer as _tx_dd_center_y_and_layer_constraint_paths,
    _tx_vertical_instance_offset_y,
    max_supported_instances,
    mounts_for_kind,
    parse_group_kind,
    resolve_selected_comparable_path,
    resolve_selected_numeric_path,
    try_parse_number,
)
from peetsfea.topology.tx_dd import txdd_instance_count_from_layer_count


def _tx_dd_center_y_and_layer(
    *,
    layer_count: int | None = None,
    instance_count: int | None = None,
    instance_index: int,
    pair_clearance_mm: float,
    outer_y: float,
    region_center_y: float,
    region_min_y: float,
    region_max_y: float,
) -> tuple[float, int]:
    if layer_count is not None:
        expected_instance_count = txdd_instance_count_from_layer_count(layer_count)
        if instance_count is not None and instance_count != expected_instance_count:
            raise ValueError(
                "tx_dd layer_count/instance_count mismatch "
                f"(layer_count={layer_count}, instance_count={instance_count}, "
                f"expected_instance_count={expected_instance_count})"
            )
        instance_count = expected_instance_count
    if instance_count is None:
        raise ValueError("tx_dd layer_count or instance_count must be provided")
    return _tx_dd_center_y_and_layer_constraint_paths(
        instance_count=instance_count,
        instance_index=instance_index,
        pair_clearance_mm=pair_clearance_mm,
        outer_y=outer_y,
        region_center_y=region_center_y,
        region_min_y=region_min_y,
        region_max_y=region_max_y,
    )

__all__ = [
    "_mount_allows_instance",
    "_tx_dd_center_y_and_layer",
    "_tx_vertical_instance_offset_y",
    "compare",
    "eval_numeric_expr",
    "evaluate_constraints",
    "max_supported_instances",
    "mounts_for_kind",
    "parse_group_kind",
    "resolve_func_ref",
    "resolve_operand_ref",
    "resolve_selected_comparable_path",
    "resolve_selected_numeric_path",
    "try_parse_number",
    "validate_constraints",
]

from __future__ import annotations


def tx_vertical_mode2_center_x_from_tx_dd_min(
    *,
    tx_dd_min_x: float,
    tx_dd_outer_x: float,
    x_ratio: float,
) -> float:
    return tx_dd_min_x + (x_ratio * tx_dd_outer_x)

from __future__ import annotations

import math


def _require_finite_positive(value: float, *, path: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{path} must be finite (actual={value})")
    if value <= 0.0:
        raise ValueError(f"{path} must be > 0 (actual={value})")
    return value


def _require_open_ratio(value: float, *, path: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{path} must be finite (actual={value})")
    if value <= 0.0 or value >= 1.0:
        raise ValueError(f"{path} must be inside (0, 1) (actual={value})")
    return value


def min_centered_rect_void_trace_width_mm(
    *,
    outer_x_mm: float,
    outer_y_mm: float,
    turn_count: int,
    void_usage_ratio: float,
    margin_ratio: float,
    metal_fill_factor: float,
) -> float:
    _require_finite_positive(outer_x_mm, path="outer_x_mm")
    _require_finite_positive(outer_y_mm, path="outer_y_mm")
    if isinstance(turn_count, bool) or not isinstance(turn_count, int):
        raise TypeError(f"turn_count must be int (actual={turn_count!r})")
    if turn_count < 1:
        raise ValueError(f"turn_count must be >= 1 (actual={turn_count})")
    _require_open_ratio(void_usage_ratio, path="void_usage_ratio")
    _require_open_ratio(margin_ratio, path="margin_ratio")
    _require_open_ratio(metal_fill_factor, path="metal_fill_factor")
    if metal_fill_factor < 0.15 or metal_fill_factor > 0.60:
        raise ValueError(f"metal_fill_factor must be in [0.15, 0.60] (actual={metal_fill_factor})")

    void_x_mm = outer_x_mm * void_usage_ratio
    void_y_mm = outer_y_mm * void_usage_ratio
    margin_x_mm = outer_x_mm * margin_ratio
    margin_y_mm = outer_y_mm * margin_ratio
    side_band_x_mm = (outer_x_mm - void_x_mm) / 2.0
    side_band_y_mm = (outer_y_mm - void_y_mm) / 2.0
    if side_band_x_mm < margin_x_mm:
        raise ValueError(
            "void x bounds must stay inside outer bounds with margin "
            f"(side_band_x_mm={side_band_x_mm}, margin_x_mm={margin_x_mm})"
        )
    if side_band_y_mm < margin_y_mm:
        raise ValueError(
            "void y bounds must stay inside outer bounds with margin "
            f"(side_band_y_mm={side_band_y_mm}, margin_y_mm={margin_y_mm})"
        )
    uniform_band_width_mm = min(side_band_x_mm, side_band_y_mm)
    if uniform_band_width_mm <= 0.0:
        raise ValueError(f"uniform_band_width_mm must be > 0 (actual={uniform_band_width_mm})")
    pitch_mm = uniform_band_width_mm / (float(turn_count) + metal_fill_factor)
    trace_width_mm = pitch_mm * metal_fill_factor
    if not math.isfinite(trace_width_mm):
        raise ValueError(f"trace_width_mm must be finite (actual={trace_width_mm})")
    if trace_width_mm <= 0.0:
        raise ValueError(f"trace_width_mm must be > 0 (actual={trace_width_mm})")
    return trace_width_mm


__all__ = ["min_centered_rect_void_trace_width_mm"]

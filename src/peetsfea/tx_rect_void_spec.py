from __future__ import annotations

import hashlib
import math
import tomllib
from pathlib import Path
from typing import cast

from peetsfea.tx_rect_void_types import (
    Number,
    RangeSpec,
    RectBounds,
    RealizedSingleCoilRectVoid,
    SideGeometry,
    SingleCoilRangeSpec,
    SingleCoilRectVoidSpec,
    SingleCoilSideGeometry,
    SingleCoilProfile,
    TX_SINGLE_COIL_PROFILE,
    ManufacturingSpec,
    terminal_end_corner_label,
    terminal_path_from_quarter_turns,
    terminal_start_corner_label,
)

_MIN_COPPER_TRACE_WIDTH_MM = 0.5
_FIXED_VOID_CENTER_X_OVER_OUTER_X_RATIO = 0.0
_FIXED_VOID_CENTER_Y_OVER_OUTER_Y_RATIO = 0.0
_UNSUPPORTED_TX_COIL_KEYS: frozenset[str] = frozenset(
    {
        "terminal_path",
        "turn_count",
        "void_usage_ratio",
        "void_x_over_outer_x",
        "void_y_over_outer_y",
        "void_center_x_over_outer_x",
        "void_center_y_over_outer_y",
    }
)


def _fail_if_unsupported_tx_coil_keys(tx_table: dict[str, object]) -> None:
    present_unsupported_keys = tuple(
        key for key in _UNSUPPORTED_TX_COIL_KEYS if key in tx_table
    )
    if len(present_unsupported_keys) == 0:
        return
    unsupported_keys_text = ", ".join(f"tx_coil.{key}" for key in sorted(present_unsupported_keys))
    raise ValueError(
        "Unsupported tx_rect_void schema input; legacy single-coil ownership keys are removed "
        f"(keys={unsupported_keys_text})"
    )


def _require_key(table: dict[str, object], key: str, context: str) -> object:
    if key not in table:
        raise ValueError(f"{context} is missing required key '{key}'")
    return table[key]


def _require_table(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be a table")
    return cast(dict[str, object], value)


def _require_float_value(table: dict[str, object], key: str, context: str) -> float:
    raw_value = _require_key(table, key, context)
    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
        raise TypeError(f"{context}.{key} must be a number")
    return float(raw_value)


def _require_str_value(table: dict[str, object], key: str, context: str) -> str:
    raw_value = _require_key(table, key, context)
    if not isinstance(raw_value, str) or raw_value == "":
        raise TypeError(f"{context}.{key} must be a non-empty string")
    return raw_value


def _require_range_table(table: dict[str, object], key: str, context: str, *, expect_integer: bool) -> RangeSpec:
    raw_node = _require_key(table, key, context)
    node = _require_table(raw_node, f"{context}.{key}")
    if set(node.keys()) != {"range"}:
        raise ValueError(f"{context}.{key} must contain only ['range']")
    raw_range = node["range"]
    if not isinstance(raw_range, list):
        raise TypeError(f"{context}.{key}.range must be [is_integer, start, end, count]")
    if len(raw_range) != 4:
        raise ValueError(f"{context}.{key}.range must contain exactly four entries")
    raw_is_integer, raw_start, raw_end, raw_count = raw_range
    if not isinstance(raw_is_integer, bool):
        raise TypeError(f"{context}.{key}.range[0] must be bool")
    if raw_is_integer != expect_integer:
        expected = "true" if expect_integer else "false"
        raise ValueError(f"{context}.{key}.range[0] must be {expected}")
    if isinstance(raw_start, bool) or not isinstance(raw_start, (int, float)):
        raise TypeError(f"{context}.{key}.range[1] must be number")
    if isinstance(raw_end, bool) or not isinstance(raw_end, (int, float)):
        raise TypeError(f"{context}.{key}.range[2] must be number")
    if isinstance(raw_count, bool) or not isinstance(raw_count, int):
        raise TypeError(f"{context}.{key}.range[3] must be int")
    if raw_count < 1:
        raise ValueError(f"{context}.{key}.range[3] must be >= 1")
    start = float(raw_start)
    end = float(raw_end)
    if end < start:
        raise ValueError(f"{context}.{key}.range end must be >= start")
    return RangeSpec(path=f"{context}.{key}", is_integer=raw_is_integer, start=start, end=end, count=raw_count)


def load_tx_rect_void_spec(toml_path: Path) -> SingleCoilRectVoidSpec:
    raw_spec = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    root = cast(dict[str, object], raw_spec)
    design = _require_table(_require_key(root, "design", toml_path.name), "design")
    units = _require_str_value(design, "units", "design")
    if units != "mm":
        raise ValueError(f"design.units must be 'mm' (actual={units})")
    manufacturing_table = _require_table(_require_key(root, "manufacturing", toml_path.name), "manufacturing")
    manufacturing = ManufacturingSpec(
        pcb_thickness_mm=_require_float_value(manufacturing_table, "pcb_thickness_mm", "manufacturing"),
        copper_thickness_mm=_require_float_value(manufacturing_table, "copper_thickness_mm", "manufacturing"),
    )
    if manufacturing.pcb_thickness_mm <= 0.0:
        raise ValueError("manufacturing.pcb_thickness_mm must be > 0")
    if manufacturing.copper_thickness_mm <= 0.0:
        raise ValueError("manufacturing.copper_thickness_mm must be > 0")
    tx_table = _require_table(_require_key(root, "tx_coil", toml_path.name), "tx_coil")
    _fail_if_unsupported_tx_coil_keys(tx_table)
    schema_id = _require_str_value(root, "schema_id", toml_path.name)
    return SingleCoilRectVoidSpec(
        schema_id=schema_id,
        units="mm",
        manufacturing=manufacturing,
        tx_coil=SingleCoilRangeSpec(
            outer_x_mm=_require_range_table(tx_table, "outer_x_mm", "tx_coil", expect_integer=False),
            outer_y_mm=_require_range_table(tx_table, "outer_y_mm", "tx_coil", expect_integer=False),
            void_usage_ratio=_require_range_table(tx_table, "void_factor", "tx_coil", expect_integer=False),
            turn_qcount=_require_range_table(tx_table, "turn_qcount", "tx_coil", expect_integer=True),
            layer_count=_require_range_table(tx_table, "layer_count", "tx_coil", expect_integer=True),
            layer_gap_mm=_require_range_table(tx_table, "layer_gap_mm", "tx_coil", expect_integer=False),
            terminal_stub_length_mm=_require_range_table(
                tx_table,
                "terminal_stub_length_mm",
                "tx_coil",
                expect_integer=False,
            ),
            terminal_start=_require_range_table(tx_table, "terminal_start", "tx_coil", expect_integer=True),
            margin_ratio=_require_range_table(tx_table, "margin_ratio", "tx_coil", expect_integer=False),
            metal_fill_factor=_require_range_table(tx_table, "metal_fill_factor", "tx_coil", expect_integer=False),
        ),
    )


def _build_candidates(range_spec: RangeSpec) -> tuple[Number, ...]:
    if range_spec.count == 1:
        raw_values = (range_spec.start,)
    else:
        step = (range_spec.end - range_spec.start) / float(range_spec.count - 1)
        raw_values = tuple(range_spec.start + (step * index) for index in range(range_spec.count))
    if not range_spec.is_integer:
        return raw_values
    rounded_values = tuple(int(math.floor(value + 0.5)) for value in raw_values)
    deduped_values: list[int] = []
    seen_values: set[int] = set()
    for value in rounded_values:
        if value in seen_values:
            continue
        seen_values.add(value)
        deduped_values.append(value)
    return tuple(deduped_values)


def _select_range_value(range_spec: RangeSpec, *, seed: int) -> Number:
    candidates = _build_candidates(range_spec)
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated for {range_spec.path}")
    if len(candidates) == 1:
        return candidates[0]
    digest = hashlib.blake2b(f"{seed}:{range_spec.path}".encode("utf-8"), digest_size=8).digest()
    index = int.from_bytes(digest, byteorder="big", signed=False) % len(candidates)
    return candidates[index]


def _validate_ratio(value: float, *, path: str) -> None:
    if value <= 0.0 or value >= 1.0:
        raise ValueError(f"{path} must be > 0 and < 1 (actual={value})")


def _uniform_side_geometry(
    band_width_mm: float,
    effective_turn_count: float,
    metal_fill_factor: float,
) -> SideGeometry:
    if band_width_mm <= 0.0:
        raise ValueError(f"tx_coil uniform band width must be > 0 (actual={band_width_mm})")
    if effective_turn_count <= 0.0:
        raise ValueError(f"tx_coil effective turn count must be > 0 (actual={effective_turn_count})")
    pitch = band_width_mm / (effective_turn_count + metal_fill_factor)
    trace = pitch * metal_fill_factor
    gap = pitch * (1.0 - metal_fill_factor)
    if trace <= 0.0:
        raise ValueError(f"tx_coil uniform trace must be > 0 (actual={trace})")
    if gap <= 0.0:
        raise ValueError(f"tx_coil uniform gap must be > 0 (actual={gap})")
    return SideGeometry(
        band_width_mm=band_width_mm,
        pitch_mm=pitch,
        trace_mm=trace,
        gap_mm=gap,
    )


def _validate_min_trace_width(side_geometry: SingleCoilSideGeometry) -> None:
    traces_by_side = {
        "left": side_geometry.left.trace_mm,
        "right": side_geometry.right.trace_mm,
        "top": side_geometry.top.trace_mm,
        "bottom": side_geometry.bottom.trace_mm,
    }
    for side_name, trace_mm in traces_by_side.items():
        if trace_mm < _MIN_COPPER_TRACE_WIDTH_MM:
            raise ValueError(
                "tx_coil trace width must be >= "
                f"{_MIN_COPPER_TRACE_WIDTH_MM} mm "
                f"(side={side_name}, actual={trace_mm})"
            )


def _validate_void_inside_outer(
    *,
    outer: RectBounds,
    void: RectBounds,
    margin_x: float,
    margin_y: float,
) -> None:
    if void.min_x < outer.min_x + margin_x or void.max_x > outer.max_x - margin_x:
        raise ValueError(
            "tx_coil void x bounds must stay inside outer bounds with margin "
            f"(void=({void.min_x}, {void.max_x}), outer=({outer.min_x}, {outer.max_x}), margin_x={margin_x})"
        )
    if void.min_y < outer.min_y + margin_y or void.max_y > outer.max_y - margin_y:
        raise ValueError(
            "tx_coil void y bounds must stay inside outer bounds with margin "
            f"(void=({void.min_y}, {void.max_y}), outer=({outer.min_y}, {outer.max_y}), margin_y={margin_y})"
        )


def _validate_finite_positive(value: Number, *, path: str) -> float:
    resolved_value = float(value)
    if not math.isfinite(resolved_value) or resolved_value <= 0.0:
        raise ValueError(f"{path} must be finite and > 0 (actual={value})")
    return resolved_value


def _routing_depth(turn_qcount: int) -> int:
    if isinstance(turn_qcount, bool) or not isinstance(turn_qcount, int):
        raise TypeError(f"turn_qcount must be an int (actual={turn_qcount!r})")
    if turn_qcount < 1:
        raise ValueError(f"turn_qcount must be >= 1 (actual={turn_qcount})")
    if turn_qcount < 4:
        return 0
    return (turn_qcount + 2) // 4


def realize_tx_rect_void_spec(
    spec: SingleCoilRectVoidSpec,
    *,
    seed: int,
    profile: SingleCoilProfile = TX_SINGLE_COIL_PROFILE,
) -> RealizedSingleCoilRectVoid:
    coil = spec.tx_coil
    outer_x_mm = float(_select_range_value(coil.outer_x_mm, seed=seed))
    outer_y_mm = float(_select_range_value(coil.outer_y_mm, seed=seed))
    turn_qcount = int(_select_range_value(coil.turn_qcount, seed=seed))
    terminal_start = int(_select_range_value(coil.terminal_start, seed=seed))
    layer_count = int(_select_range_value(coil.layer_count, seed=seed))
    layer_gap_mm = float(_select_range_value(coil.layer_gap_mm, seed=seed))
    void_factor = float(_select_range_value(coil.void_usage_ratio, seed=seed))
    void_x_ratio = void_factor
    void_y_ratio = void_factor
    void_center_x_ratio = _FIXED_VOID_CENTER_X_OVER_OUTER_X_RATIO
    void_center_y_ratio = _FIXED_VOID_CENTER_Y_OVER_OUTER_Y_RATIO
    margin_ratio = float(_select_range_value(coil.margin_ratio, seed=seed))
    metal_fill_factor = float(_select_range_value(coil.metal_fill_factor, seed=seed))
    terminal_stub_length_mm = _validate_finite_positive(
        _select_range_value(coil.terminal_stub_length_mm, seed=seed),
        path="tx_coil.terminal_stub_length_mm",
    )
    if outer_x_mm <= 0.0:
        raise ValueError(f"tx_coil.outer_x_mm must resolve to > 0 (actual={outer_x_mm})")
    if outer_y_mm <= 0.0:
        raise ValueError(f"tx_coil.outer_y_mm must resolve to > 0 (actual={outer_y_mm})")
    if profile.max_turn_count < 1:
        raise ValueError(
            "single-coil profile max_turn_count must be >= 1 "
            f"(profile={profile.object_id}, actual={profile.max_turn_count})"
        )
    max_turn_qcount = profile.max_turn_count * 4
    if turn_qcount < 1 or turn_qcount > max_turn_qcount:
        raise ValueError(
            f"tx_coil.turn_qcount must resolve to [1,{max_turn_qcount}] "
            f"(actual={turn_qcount}, profile={profile.object_id})"
        )
    effective_turn_count = float(turn_qcount) / 4.0
    routing_depth = _routing_depth(turn_qcount)
    sizing_turn_count = max(effective_turn_count, float(routing_depth))
    terminal_start_corner = terminal_start_corner_label(terminal_start)
    terminal_end_corner = terminal_end_corner_label(terminal_start=terminal_start, turn_qcount=turn_qcount)
    terminal_path = terminal_path_from_quarter_turns(terminal_start=terminal_start, turn_qcount=turn_qcount)
    if layer_count < 1:
        raise ValueError(f"tx_coil.layer_count must resolve to >= 1 (actual={layer_count})")
    if profile.role == "rx_single_coil" and layer_count != 1:
        raise ValueError(
            "rx_single_coil.layer_count must resolve to 1 until RX multilayer support exists "
            f"(actual={layer_count})"
        )
    if layer_gap_mm < 2.0:
        raise ValueError(f"tx_coil.layer_gap_mm must be >= 2.0 (actual={layer_gap_mm})")
    _validate_ratio(void_factor, path=coil.void_usage_ratio.path)
    _validate_ratio(margin_ratio, path="tx_coil.margin_ratio")
    _validate_ratio(metal_fill_factor, path="tx_coil.metal_fill_factor")
    if metal_fill_factor < 0.15 or metal_fill_factor > 0.60:
        raise ValueError(
            "tx_coil.metal_fill_factor must resolve to [0.15,0.60] "
            f"(actual={metal_fill_factor})"
        )
    void_x_mm = outer_x_mm * void_x_ratio
    void_y_mm = outer_y_mm * void_y_ratio
    void_center_x_mm = outer_x_mm * void_center_x_ratio
    void_center_y_mm = outer_y_mm * void_center_y_ratio
    outer = RectBounds(
        min_x=-(outer_x_mm / 2.0),
        max_x=outer_x_mm / 2.0,
        min_y=-(outer_y_mm / 2.0),
        max_y=outer_y_mm / 2.0,
    )
    void = RectBounds(
        min_x=void_center_x_mm - (void_x_mm / 2.0),
        max_x=void_center_x_mm + (void_x_mm / 2.0),
        min_y=void_center_y_mm - (void_y_mm / 2.0),
        max_y=void_center_y_mm + (void_y_mm / 2.0),
    )
    margin_x_mm = outer_x_mm * margin_ratio
    margin_y_mm = outer_y_mm * margin_ratio
    _validate_void_inside_outer(outer=outer, void=void, margin_x=margin_x_mm, margin_y=margin_y_mm)
    uniform_band_width_mm = min(
        void.min_x - outer.min_x,
        outer.max_x - void.max_x,
        outer.max_y - void.max_y,
        void.min_y - outer.min_y,
    )
    uniform_geometry = _uniform_side_geometry(uniform_band_width_mm, sizing_turn_count, metal_fill_factor)
    side_geometry = SingleCoilSideGeometry(
        left=uniform_geometry,
        right=uniform_geometry,
        top=uniform_geometry,
        bottom=uniform_geometry,
    )
    _validate_min_trace_width(side_geometry)
    return RealizedSingleCoilRectVoid(
        seed=seed,
        terminal_path=terminal_path,
        terminal_start=terminal_start,
        terminal_start_corner=terminal_start_corner,
        terminal_end_corner=terminal_end_corner,
        terminal_direction="cw",
        turn_qcount=turn_qcount,
        effective_turn_count=effective_turn_count,
        outer_x_mm=outer_x_mm,
        outer_y_mm=outer_y_mm,
        turn_count=effective_turn_count,
        layer_count=layer_count,
        layer_gap_mm=layer_gap_mm,
        terminal_stub_length_mm=terminal_stub_length_mm,
        void_x_over_outer_x=void_x_ratio,
        void_y_over_outer_y=void_y_ratio,
        void_center_x_over_outer_x=void_center_x_ratio,
        void_center_y_over_outer_y=void_center_y_ratio,
        void_x_mm=void_x_mm,
        void_y_mm=void_y_mm,
        void_center_x_mm=void_center_x_mm,
        void_center_y_mm=void_center_y_mm,
        margin_ratio=margin_ratio,
        margin_x_mm=margin_x_mm,
        margin_y_mm=margin_y_mm,
        metal_fill_factor=metal_fill_factor,
        trace_width_mm=uniform_geometry.trace_mm,
        gap_width_mm=uniform_geometry.gap_mm,
        pitch_mm=uniform_geometry.pitch_mm,
        pcb_thickness_mm=spec.manufacturing.pcb_thickness_mm,
        copper_thickness_mm=spec.manufacturing.copper_thickness_mm,
        outer_bounds=outer,
        void_bounds=void,
        side_geometry=side_geometry,
    )


__all__ = [
    "load_tx_rect_void_spec",
    "realize_tx_rect_void_spec",
]

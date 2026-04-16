from __future__ import annotations

import hashlib
import json
import math
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

import build123d as bd

Number = int | float
CornerLabel = Literal["A", "B", "C", "D"]
InnerCornerLabel = Literal["a", "b", "c", "d"]
PathDirection = Literal["cw", "ccw"]
BoxRole = Literal["pcb", "copper"]
ModeledObjectRole = Literal["tx_single_coil"]
ModeledObjectMaterial = Literal["composite"]

_EPS = 1e-9
_OUTER_TO_INNER_CORNER: dict[CornerLabel, InnerCornerLabel] = {
    "A": "a",
    "B": "b",
    "C": "c",
    "D": "d",
}
_CW_CORNERS: tuple[CornerLabel, ...] = ("A", "B", "C", "D")
_CCW_CORNERS: tuple[CornerLabel, ...] = ("A", "D", "C", "B")
_MIN_COPPER_TRACE_WIDTH_MM = 0.5
_CORNER_INDEX_BY_LABEL: dict[CornerLabel, int] = {"A": 0, "B": 1, "C": 2, "D": 3}


@dataclass(frozen=True)
class RangeSpec:
    path: str
    is_integer: bool
    start: float
    end: float
    count: int


@dataclass(frozen=True)
class TxCoilRangeSpec:
    outer_x_mm: RangeSpec
    outer_y_mm: RangeSpec
    turn_count: RangeSpec
    layer_count: RangeSpec
    layer_gap_mm: RangeSpec
    void_x_over_outer_x: RangeSpec
    void_y_over_outer_y: RangeSpec
    void_center_x_over_outer_x: RangeSpec
    void_center_y_over_outer_y: RangeSpec
    margin_ratio: RangeSpec
    metal_fill_factor: RangeSpec


@dataclass(frozen=True)
class ManufacturingSpec:
    pcb_thickness_mm: float
    copper_thickness_mm: float


@dataclass(frozen=True)
class TerminalPath:
    raw: str
    outer_corner: CornerLabel
    direction: PathDirection
    inner_corner: InnerCornerLabel


@dataclass(frozen=True)
class TxRectVoidSpec:
    schema_id: str
    units: Literal["mm"]
    manufacturing: ManufacturingSpec
    tx_coil: TxCoilRangeSpec
    terminal_path: TerminalPath


@dataclass(frozen=True)
class RectBounds:
    min_x: float
    max_x: float
    min_y: float
    max_y: float


@dataclass(frozen=True)
class SideGeometry:
    band_width_mm: float
    pitch_mm: float
    trace_mm: float
    gap_mm: float


@dataclass(frozen=True)
class TxCoilSideGeometry:
    left: SideGeometry
    right: SideGeometry
    top: SideGeometry
    bottom: SideGeometry


@dataclass(frozen=True)
class RealizedTxRectVoidCoil:
    seed: int
    terminal_path: str
    outer_x_mm: float
    outer_y_mm: float
    turn_count: int
    layer_count: int
    layer_gap_mm: float
    void_x_over_outer_x: float
    void_y_over_outer_y: float
    void_center_x_over_outer_x: float
    void_center_y_over_outer_y: float
    void_x_mm: float
    void_y_mm: float
    void_center_x_mm: float
    void_center_y_mm: float
    margin_ratio: float
    margin_x_mm: float
    margin_y_mm: float
    metal_fill_factor: float
    trace_width_mm: float
    gap_width_mm: float
    pitch_mm: float
    pcb_thickness_mm: float
    copper_thickness_mm: float
    outer_bounds: RectBounds
    void_bounds: RectBounds
    side_geometry: TxCoilSideGeometry


@dataclass(frozen=True)
class BoxSpec:
    label: str
    role: BoxRole
    layer_index: int
    origin_xyz: tuple[float, float, float]
    size_xyz: tuple[float, float, float]


@dataclass(frozen=True)
class ModeledObjectCanonicalCoordinates:
    frame_origin_xyz: tuple[float, float, float]
    outer_bounds_min_xyz: tuple[float, float, float]
    outer_bounds_max_xyz: tuple[float, float, float]
    outer_bounds_size_xyz: tuple[float, float, float]
    pcb_layer_z_positions_mm: tuple[float, ...]
    copper_layer_z_positions_mm: tuple[float, ...]


@dataclass(frozen=True)
class ModeledObjectTerminalMetadata:
    path: str
    outer_corner: CornerLabel
    inner_corner: InnerCornerLabel
    direction: PathDirection
    start_point_xy_mm: tuple[float, float]
    end_point_xy_mm: tuple[float, float]


@dataclass(frozen=True)
class ModeledObjectEntry:
    object_id: str
    role: ModeledObjectRole
    material: ModeledObjectMaterial
    model_state: Literal[True]
    step_path: str
    expected_exported_body_names: tuple[str, ...]
    expected_exported_body_count: int
    canonical_coordinates: ModeledObjectCanonicalCoordinates
    terminal_metadata: ModeledObjectTerminalMetadata


@dataclass(frozen=True)
class TxRectVoidExportResult:
    source_toml_path: str
    output_step_path: str
    metadata_path: str
    expected_exported_body_names: tuple[str, ...]
    expected_exported_body_count: int
    realized: RealizedTxRectVoidCoil
    boxes: tuple[BoxSpec, ...]
    modeled_objects: tuple[ModeledObjectEntry, ...]


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


def _parse_terminal_path(value: str) -> TerminalPath:
    parts = value.split("_")
    if len(parts) != 4 or parts[2] != "to":
        raise ValueError(f"tx_coil.terminal_path must match '<outer>_<cw|ccw>_to_<inner>' (actual={value})")
    raw_outer = parts[0]
    raw_direction = parts[1]
    raw_inner = parts[3]
    if raw_outer not in _OUTER_TO_INNER_CORNER:
        raise ValueError(f"tx_coil.terminal_path outer corner must be one of A/B/C/D (actual={raw_outer})")
    if raw_direction not in ("cw", "ccw"):
        raise ValueError(f"tx_coil.terminal_path direction must be cw or ccw (actual={raw_direction})")
    outer_corner = cast(CornerLabel, raw_outer)
    expected_inner = _OUTER_TO_INNER_CORNER[outer_corner]
    if raw_inner != expected_inner:
        raise ValueError(
            "tx_coil.terminal_path v1 requires matching outer/inner corners "
            f"(outer={outer_corner}, expected_inner={expected_inner}, actual_inner={raw_inner})"
        )
    return TerminalPath(
        raw=value,
        outer_corner=outer_corner,
        direction=cast(PathDirection, raw_direction),
        inner_corner=expected_inner,
    )


def load_tx_rect_void_spec(toml_path: Path) -> TxRectVoidSpec:
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
    terminal_table = _require_table(_require_key(tx_table, "terminal_path", "tx_coil"), "tx_coil.terminal_path")
    if set(terminal_table.keys()) != {"value"}:
        raise ValueError("tx_coil.terminal_path must contain only ['value']")
    terminal_path = _parse_terminal_path(_require_str_value(terminal_table, "value", "tx_coil.terminal_path"))
    schema_id = _require_str_value(root, "schema_id", toml_path.name)
    return TxRectVoidSpec(
        schema_id=schema_id,
        units="mm",
        manufacturing=manufacturing,
        terminal_path=terminal_path,
        tx_coil=TxCoilRangeSpec(
            outer_x_mm=_require_range_table(tx_table, "outer_x_mm", "tx_coil", expect_integer=False),
            outer_y_mm=_require_range_table(tx_table, "outer_y_mm", "tx_coil", expect_integer=False),
            turn_count=_require_range_table(tx_table, "turn_count", "tx_coil", expect_integer=True),
            layer_count=_require_range_table(tx_table, "layer_count", "tx_coil", expect_integer=True),
            layer_gap_mm=_require_range_table(tx_table, "layer_gap_mm", "tx_coil", expect_integer=False),
            void_x_over_outer_x=_require_range_table(
                tx_table, "void_x_over_outer_x", "tx_coil", expect_integer=False
            ),
            void_y_over_outer_y=_require_range_table(
                tx_table, "void_y_over_outer_y", "tx_coil", expect_integer=False
            ),
            void_center_x_over_outer_x=_require_range_table(
                tx_table, "void_center_x_over_outer_x", "tx_coil", expect_integer=False
            ),
            void_center_y_over_outer_y=_require_range_table(
                tx_table, "void_center_y_over_outer_y", "tx_coil", expect_integer=False
            ),
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


def _side_geometry(side_name: str, band_width_mm: float, turn_count: int, metal_fill_factor: float) -> SideGeometry:
    if band_width_mm <= 0.0:
        raise ValueError(f"tx_coil {side_name} band width must be > 0 (actual={band_width_mm})")
    pitch = band_width_mm / float(turn_count)
    trace = pitch * metal_fill_factor
    gap = pitch * (1.0 - metal_fill_factor)
    if trace <= 0.0:
        raise ValueError(f"tx_coil {side_name} trace must be > 0 (actual={trace})")
    if gap <= 0.0:
        raise ValueError(f"tx_coil {side_name} gap must be > 0 (actual={gap})")
    return SideGeometry(
        band_width_mm=band_width_mm,
        pitch_mm=pitch,
        trace_mm=trace,
        gap_mm=gap,
    )


def _uniform_side_geometry(band_width_mm: float, turn_count: int, metal_fill_factor: float) -> SideGeometry:
    if band_width_mm <= 0.0:
        raise ValueError(f"tx_coil uniform band width must be > 0 (actual={band_width_mm})")
    pitch = band_width_mm / (float(turn_count) + metal_fill_factor)
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


def _validate_min_trace_width(side_geometry: TxCoilSideGeometry) -> None:
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


def realize_tx_rect_void_spec(spec: TxRectVoidSpec, *, seed: int) -> RealizedTxRectVoidCoil:
    coil = spec.tx_coil
    outer_x_mm = float(_select_range_value(coil.outer_x_mm, seed=seed))
    outer_y_mm = float(_select_range_value(coil.outer_y_mm, seed=seed))
    turn_count = int(_select_range_value(coil.turn_count, seed=seed))
    layer_count = int(_select_range_value(coil.layer_count, seed=seed))
    layer_gap_mm = float(_select_range_value(coil.layer_gap_mm, seed=seed))
    void_x_ratio = float(_select_range_value(coil.void_x_over_outer_x, seed=seed))
    void_y_ratio = float(_select_range_value(coil.void_y_over_outer_y, seed=seed))
    void_center_x_ratio = float(_select_range_value(coil.void_center_x_over_outer_x, seed=seed))
    void_center_y_ratio = float(_select_range_value(coil.void_center_y_over_outer_y, seed=seed))
    margin_ratio = float(_select_range_value(coil.margin_ratio, seed=seed))
    metal_fill_factor = float(_select_range_value(coil.metal_fill_factor, seed=seed))
    if outer_x_mm <= 0.0:
        raise ValueError(f"tx_coil.outer_x_mm must resolve to > 0 (actual={outer_x_mm})")
    if outer_y_mm <= 0.0:
        raise ValueError(f"tx_coil.outer_y_mm must resolve to > 0 (actual={outer_y_mm})")
    if turn_count < 1 or turn_count > 4:
        raise ValueError(f"tx_coil.turn_count must resolve to [1,4] (actual={turn_count})")
    if layer_count != 1:
        raise ValueError(
            "tx_coil.layer_count must resolve to 1 for type2 v1 single-layer TX coil "
            f"(actual={layer_count})"
        )
    if layer_gap_mm < 2.0:
        raise ValueError(f"tx_coil.layer_gap_mm must be >= 2.0 (actual={layer_gap_mm})")
    _validate_ratio(void_x_ratio, path="tx_coil.void_x_over_outer_x")
    _validate_ratio(void_y_ratio, path="tx_coil.void_y_over_outer_y")
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
    uniform_geometry = _uniform_side_geometry(uniform_band_width_mm, turn_count, metal_fill_factor)
    side_geometry = TxCoilSideGeometry(
        left=uniform_geometry,
        right=uniform_geometry,
        top=uniform_geometry,
        bottom=uniform_geometry,
    )
    _validate_min_trace_width(side_geometry)
    return RealizedTxRectVoidCoil(
        seed=seed,
        terminal_path=spec.terminal_path.raw,
        outer_x_mm=outer_x_mm,
        outer_y_mm=outer_y_mm,
        turn_count=turn_count,
        layer_count=layer_count,
        layer_gap_mm=layer_gap_mm,
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


def _ordered_corners(start: CornerLabel, direction: PathDirection) -> tuple[CornerLabel, ...]:
    base = _CW_CORNERS if direction == "cw" else _CCW_CORNERS
    start_index = base.index(start)
    return base[start_index:] + base[:start_index]


def _direction_step(direction: PathDirection) -> int:
    return 1 if direction == "cw" else -1


def _ring_left(*, realized: RealizedTxRectVoidCoil, ring_index: int) -> float:
    return realized.outer_bounds.min_x + (realized.trace_width_mm / 2.0) + (float(ring_index) * realized.pitch_mm)


def _ring_right(*, realized: RealizedTxRectVoidCoil, ring_index: int) -> float:
    return realized.outer_bounds.max_x - (realized.trace_width_mm / 2.0) - (float(ring_index) * realized.pitch_mm)


def _ring_top(*, realized: RealizedTxRectVoidCoil, ring_index: int) -> float:
    return realized.outer_bounds.max_y - (realized.trace_width_mm / 2.0) - (float(ring_index) * realized.pitch_mm)


def _ring_bottom(*, realized: RealizedTxRectVoidCoil, ring_index: int) -> float:
    return realized.outer_bounds.min_y + (realized.trace_width_mm / 2.0) + (float(ring_index) * realized.pitch_mm)


def _corner_point_by_index(
    *,
    realized: RealizedTxRectVoidCoil,
    corner_index: int,
    ring_index: int,
) -> tuple[float, float]:
    left = _ring_left(realized=realized, ring_index=ring_index)
    right = _ring_right(realized=realized, ring_index=ring_index)
    top = _ring_top(realized=realized, ring_index=ring_index)
    bottom = _ring_bottom(realized=realized, ring_index=ring_index)
    if left >= right or bottom >= top:
        raise ValueError(
            "tx rect/void requested turns do not fit realized uniform trace geometry "
            f"(ring_index={ring_index}, left={left}, right={right}, top={top}, bottom={bottom})"
        )
    if corner_index == 0:
        return (left, top)
    if corner_index == 1:
        return (right, top)
    if corner_index == 2:
        return (right, bottom)
    if corner_index == 3:
        return (left, bottom)
    raise ValueError(f"corner_index must be 0..3 (actual={corner_index})")


def _mixed_transition_point(
    *,
    realized: RealizedTxRectVoidCoil,
    start_corner_index: int,
    direction: PathDirection,
    last_corner_ring_index: int,
    next_start_ring_index: int,
) -> tuple[float, float]:
    last_corner = _corner_point_by_index(
        realized=realized,
        corner_index=(start_corner_index - _direction_step(direction)) % 4,
        ring_index=last_corner_ring_index,
    )
    next_start_corner = _corner_point_by_index(
        realized=realized,
        corner_index=start_corner_index,
        ring_index=next_start_ring_index,
    )
    use_next_start_x = (start_corner_index % 2 == 0) if direction == "ccw" else (start_corner_index % 2 == 1)
    if use_next_start_x:
        return (next_start_corner[0], last_corner[1])
    return (last_corner[0], next_start_corner[1])


def _build_same_corner_centerline(
    *,
    realized: RealizedTxRectVoidCoil,
    start_corner: CornerLabel,
    direction: PathDirection,
) -> tuple[tuple[float, float], ...]:
    start_corner_index = _CORNER_INDEX_BY_LABEL[start_corner]
    step = _direction_step(direction)
    prep_corner_index = (start_corner_index + step) % 4
    enter_corner_index = (start_corner_index + (2 * step)) % 4
    end_ring_index = realized.turn_count
    _ = _corner_point_by_index(realized=realized, corner_index=start_corner_index, ring_index=end_ring_index)
    points = [
        _corner_point_by_index(realized=realized, corner_index=start_corner_index, ring_index=0),
        _corner_point_by_index(realized=realized, corner_index=prep_corner_index, ring_index=0),
    ]
    for ring_index in range(1, end_ring_index + 1):
        transition_point = _mixed_transition_point(
            realized=realized,
            start_corner_index=enter_corner_index,
            direction=direction,
            last_corner_ring_index=ring_index - 1,
            next_start_ring_index=ring_index,
        )
        _append_point(points, transition_point)
        enter_corner = _corner_point_by_index(
            realized=realized,
            corner_index=enter_corner_index,
            ring_index=ring_index,
        )
        _append_point(points, enter_corner)
        current_corner_index = enter_corner_index
        while current_corner_index != start_corner_index:
            current_corner_index = (current_corner_index + step) % 4
            _append_point(
                points,
                _corner_point_by_index(
                    realized=realized,
                    corner_index=current_corner_index,
                    ring_index=ring_index,
                ),
            )
        if ring_index < end_ring_index:
            _append_point(
                points,
                _corner_point_by_index(
                    realized=realized,
                    corner_index=prep_corner_index,
                    ring_index=ring_index,
                ),
            )
    return tuple(_seed_outer_terminal_points(points))


def _seed_outer_terminal_points(points: tuple[tuple[float, float], ...] | list[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    if len(points) < 2:
        return tuple(points)
    eps = _EPS
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    unique_x = sorted({point[0] for point in points})
    unique_y = sorted({point[1] for point in points})
    seeded = list(points)

    def _is_outer_corner(point: tuple[float, float]) -> bool:
        on_x_extreme = abs(point[0] - min_x) <= eps or abs(point[0] - max_x) <= eps
        on_y_extreme = abs(point[1] - min_y) <= eps or abs(point[1] - max_y) <= eps
        return on_x_extreme and on_y_extreme

    def _seed_from_neighbor(point: tuple[float, float], neighbor: tuple[float, float]) -> tuple[float, float]:
        dx = neighbor[0] - point[0]
        dy = neighbor[1] - point[1]
        if abs(dx) > eps and abs(dy) > eps:
            raise ValueError("tx rect/void outer terminal seed requires axis-aligned terminal segment")
        if abs(dx) <= eps and abs(dy) <= eps:
            raise ValueError("tx rect/void outer terminal seed requires non-zero terminal segment")
        if abs(dx) > eps:
            if abs(point[0] - min_x) <= eps:
                if len(unique_x) <= 1:
                    raise ValueError("tx rect/void outer terminal seed requires inner x ring")
                return (unique_x[1], point[1])
            if abs(point[0] - max_x) <= eps:
                if len(unique_x) <= 1:
                    raise ValueError("tx rect/void outer terminal seed requires inner x ring")
                return (unique_x[-2], point[1])
            return point
        if abs(point[1] - min_y) <= eps:
            if len(unique_y) <= 1:
                raise ValueError("tx rect/void outer terminal seed requires inner y ring")
            return (point[0], unique_y[1])
        if abs(point[1] - max_y) <= eps:
            if len(unique_y) <= 1:
                raise ValueError("tx rect/void outer terminal seed requires inner y ring")
            return (point[0], unique_y[-2])
        return point

    if _is_outer_corner(seeded[0]):
        seeded[0] = _seed_from_neighbor(seeded[0], seeded[1])
    if _is_outer_corner(seeded[-1]):
        seeded[-1] = _seed_from_neighbor(seeded[-1], seeded[-2])
    return tuple(seeded)


def _corner_point(realized: RealizedTxRectVoidCoil, corner: CornerLabel, ring_index: int) -> tuple[float, float]:
    outer = realized.outer_bounds
    side = realized.side_geometry
    left_x = outer.min_x + (float(ring_index) * side.left.pitch_mm) + (side.left.trace_mm / 2.0)
    right_x = outer.max_x - (float(ring_index) * side.right.pitch_mm) - (side.right.trace_mm / 2.0)
    top_y = outer.max_y - (float(ring_index) * side.top.pitch_mm) - (side.top.trace_mm / 2.0)
    bottom_y = outer.min_y + (float(ring_index) * side.bottom.pitch_mm) + (side.bottom.trace_mm / 2.0)
    if corner == "A":
        return (left_x, top_y)
    if corner == "B":
        return (right_x, top_y)
    if corner == "C":
        return (right_x, bottom_y)
    return (left_x, bottom_y)


def _inner_corner_point(realized: RealizedTxRectVoidCoil, corner: CornerLabel) -> tuple[float, float]:
    void = realized.void_bounds
    side = realized.side_geometry
    if corner == "A":
        return (void.min_x - (side.left.trace_mm / 2.0), void.max_y + (side.top.trace_mm / 2.0))
    if corner == "B":
        return (void.max_x + (side.right.trace_mm / 2.0), void.max_y + (side.top.trace_mm / 2.0))
    if corner == "C":
        return (void.max_x + (side.right.trace_mm / 2.0), void.min_y - (side.bottom.trace_mm / 2.0))
    return (void.min_x - (side.left.trace_mm / 2.0), void.min_y - (side.bottom.trace_mm / 2.0))


def _append_point(points: list[tuple[float, float]], point: tuple[float, float]) -> None:
    if points and abs(points[-1][0] - point[0]) <= _EPS and abs(points[-1][1] - point[1]) <= _EPS:
        return
    points.append(point)


def build_tx_rect_void_centerline(realized: RealizedTxRectVoidCoil) -> tuple[tuple[float, float], ...]:
    terminal = _parse_terminal_path(realized.terminal_path)
    points = list(
        _build_same_corner_centerline(
            realized=realized,
            start_corner=terminal.outer_corner,
            direction=terminal.direction,
        )
    )
    if len(points) < 2:
        raise ValueError("tx rect/void centerline must contain at least two points")
    if len(points) != len(set(points)):
        raise ValueError(f"tx rect/void centerline must not reuse points (points={points})")
    return tuple(points)


def _rectangles_intersect(first: RectBounds, second: RectBounds) -> bool:
    x_overlap = max(first.min_x, second.min_x) < min(first.max_x, second.max_x) - _EPS
    y_overlap = max(first.min_y, second.min_y) < min(first.max_y, second.max_y) - _EPS
    return x_overlap and y_overlap


def _trace_for_segment(realized: RealizedTxRectVoidCoil, p0: tuple[float, float], p1: tuple[float, float]) -> float:
    if abs(p0[1] - p1[1]) <= _EPS:
        return realized.trace_width_mm
    if abs(p0[0] - p1[0]) <= _EPS:
        return realized.trace_width_mm
    raise ValueError(f"tx rect/void centerline segment must be axis aligned (p0={p0}, p1={p1})")


def _segment_box_bounds(p0: tuple[float, float], p1: tuple[float, float], trace: float) -> RectBounds:
    half_trace = trace / 2.0
    if abs(p0[1] - p1[1]) <= _EPS:
        min_x = min(p0[0], p1[0]) - half_trace
        max_x = max(p0[0], p1[0]) + half_trace
        y = p0[1]
        return RectBounds(min_x=min_x, max_x=max_x, min_y=y - half_trace, max_y=y + half_trace)
    if abs(p0[0] - p1[0]) <= _EPS:
        x = p0[0]
        min_y = min(p0[1], p1[1]) - half_trace
        max_y = max(p0[1], p1[1]) + half_trace
        return RectBounds(min_x=x - half_trace, max_x=x + half_trace, min_y=min_y, max_y=max_y)
    raise ValueError(f"tx rect/void segment must be axis aligned (p0={p0}, p1={p1})")


def _segment_box_spec(
    *,
    realized: RealizedTxRectVoidCoil,
    p0: tuple[float, float],
    p1: tuple[float, float],
    layer_index: int,
    segment_index: int,
    copper_z: float,
) -> BoxSpec:
    trace = _trace_for_segment(realized, p0, p1)
    bounds = _segment_box_bounds(p0, p1, trace)
    if bounds.max_x - bounds.min_x <= _EPS or bounds.max_y - bounds.min_y <= _EPS:
        raise ValueError(f"tx rect/void segment box must have positive XY size (p0={p0}, p1={p1})")
    if _rectangles_intersect(bounds, realized.void_bounds):
        raise ValueError(
            "tx rect/void copper segment intersects void keepout "
            f"(layer={layer_index}, segment={segment_index}, bounds={bounds}, void={realized.void_bounds})"
        )
    return BoxSpec(
        label=f"tx_copper_l{layer_index}_s{segment_index}",
        role="copper",
        layer_index=layer_index,
        origin_xyz=(bounds.min_x, bounds.min_y, copper_z),
        size_xyz=(
            bounds.max_x - bounds.min_x,
            bounds.max_y - bounds.min_y,
            realized.copper_thickness_mm,
        ),
    )


def _validate_copper_boxes_do_not_short(copper_boxes: tuple[BoxSpec, ...]) -> None:
    by_layer: dict[int, list[tuple[int, RectBounds]]] = {}
    for box in copper_boxes:
        label_parts = box.label.rsplit("_s", maxsplit=1)
        if len(label_parts) != 2:
            raise ValueError(f"tx rect/void copper box label must end with segment index (label={box.label})")
        segment_index = int(label_parts[1])
        by_layer.setdefault(box.layer_index, []).append((segment_index, _box_xy_bounds(box)))
    for layer_index, indexed_bounds in by_layer.items():
        for first_index, first_bounds in indexed_bounds:
            for second_index, second_bounds in indexed_bounds:
                if second_index <= first_index + 1:
                    continue
                if _rectangles_intersect(first_bounds, second_bounds):
                    raise ValueError(
                        "tx rect/void non-adjacent copper segments overlap and would short turns "
                        f"(layer={layer_index}, first_segment={first_index}, second_segment={second_index}, "
                        f"first_bounds={first_bounds}, second_bounds={second_bounds})"
                    )


def _box_xy_bounds(box: BoxSpec) -> RectBounds:
    origin_x, origin_y, _origin_z = box.origin_xyz
    size_x, size_y, _size_z = box.size_xyz
    return RectBounds(
        min_x=origin_x,
        max_x=origin_x + size_x,
        min_y=origin_y,
        max_y=origin_y + size_y,
    )


def build_tx_rect_void_box_specs(realized: RealizedTxRectVoidCoil) -> tuple[BoxSpec, ...]:
    centerline = build_tx_rect_void_centerline(realized)
    boxes: list[BoxSpec] = []
    for layer_index in range(realized.layer_count):
        pcb_z = float(layer_index) * (realized.pcb_thickness_mm + realized.layer_gap_mm)
        copper_z = pcb_z + realized.pcb_thickness_mm
        boxes.append(
            BoxSpec(
                label=f"tx_pcb_l{layer_index}",
                role="pcb",
                layer_index=layer_index,
                origin_xyz=(realized.outer_bounds.min_x, realized.outer_bounds.min_y, pcb_z),
                size_xyz=(realized.outer_x_mm, realized.outer_y_mm, realized.pcb_thickness_mm),
            )
        )
        for segment_index, (p0, p1) in enumerate(zip(centerline[:-1], centerline[1:])):
            boxes.append(
                _segment_box_spec(
                    realized=realized,
                    p0=p0,
                    p1=p1,
                    layer_index=layer_index,
                    segment_index=segment_index,
                    copper_z=copper_z,
                )
            )
    resolved_boxes = tuple(boxes)
    _validate_copper_boxes_do_not_short(tuple(box for box in resolved_boxes if box.role == "copper"))
    return resolved_boxes


def _build_box_shape(box_spec: BoxSpec) -> bd.Shape:
    size_x, size_y, size_z = box_spec.size_xyz
    if size_x <= 0.0 or size_y <= 0.0 or size_z <= 0.0:
        raise ValueError(f"box size must be positive for STEP export (box={box_spec})")
    shape = bd.Box(
        size_x,
        size_y,
        size_z,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    ).moved(bd.Location(box_spec.origin_xyz))
    shape.label = box_spec.label
    return shape


def _expected_exported_body_names(boxes: tuple[BoxSpec, ...]) -> tuple[str, ...]:
    pcb_names = tuple(box.label for box in boxes if box.role == "pcb")
    copper_layer_indices = tuple(sorted({box.layer_index for box in boxes if box.role == "copper"}))
    copper_names = tuple(f"tx_copper_l{layer_index}" for layer_index in copper_layer_indices)
    body_names = pcb_names + copper_names
    if len(body_names) == 0:
        raise ValueError("tx rect/void STEP scene requires at least one exported body")
    if len(body_names) != len(set(body_names)):
        raise ValueError(f"tx rect/void exported body names must be unique (actual={body_names})")
    return body_names


def _single_shape_from_fuse_result(fuse_result: object, *, label: str, source_count: int) -> bd.Shape:
    if isinstance(fuse_result, bd.ShapeList):
        raise RuntimeError(
            "build123d copper fuse returned multiple shapes "
            f"(label={label}, source_count={source_count}, result_count={len(fuse_result)})"
        )
    if not isinstance(fuse_result, bd.Shape):
        raise TypeError(f"build123d copper fuse returned unsupported result type: {type(fuse_result).__name__}")
    solids = tuple(fuse_result.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "fused copper layer must contain exactly one solid "
            f"(label={label}, source_count={source_count}, solid_count={len(solids)})"
        )
    fuse_result.label = label
    return fuse_result


def _build_fused_copper_layer_shape(layer_index: int, copper_boxes: tuple[BoxSpec, ...]) -> bd.Shape:
    if len(copper_boxes) == 0:
        raise ValueError(f"tx rect/void copper layer has no segment boxes (layer={layer_index})")
    copper_shapes = tuple(_build_box_shape(box_spec) for box_spec in copper_boxes)
    label = f"tx_copper_l{layer_index}"
    if len(copper_shapes) == 1:
        copper_shapes[0].label = label
        return copper_shapes[0]
    fuse_result = copper_shapes[0].fuse(*copper_shapes[1:])
    return _single_shape_from_fuse_result(fuse_result, label=label, source_count=len(copper_shapes))


def build_tx_rect_void_step_scene(boxes: tuple[BoxSpec, ...]) -> bd.Compound:
    if not boxes:
        raise ValueError("tx rect/void STEP scene requires at least one box")
    expected_body_names = _expected_exported_body_names(boxes)
    pcb_shapes = tuple(_build_box_shape(box_spec) for box_spec in boxes if box_spec.role == "pcb")
    copper_layer_indices = tuple(sorted({box.layer_index for box in boxes if box.role == "copper"}))
    copper_shapes = tuple(
        _build_fused_copper_layer_shape(
            layer_index,
            tuple(box for box in boxes if box.role == "copper" and box.layer_index == layer_index),
        )
        for layer_index in copper_layer_indices
    )
    shapes = pcb_shapes + copper_shapes
    actual_body_names = tuple(shape.label for shape in shapes)
    if actual_body_names != expected_body_names:
        raise RuntimeError(
            "tx rect/void exported body name mismatch "
            f"(expected={expected_body_names}, actual={actual_body_names})"
        )
    if len(shapes) != 2:
        raise RuntimeError(
            "type2 v1 tx rect/void STEP scene must export exactly 2 bodies "
            f"(actual={len(shapes)}, names={actual_body_names})"
        )
    return bd.Compound(children=shapes, label="tx_rect_void_coil")


def _write_metadata(path: Path, result: TxRectVoidExportResult) -> None:
    payload = asdict(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_modeled_object_entry(
    *,
    realized: RealizedTxRectVoidCoil,
    output_step_path: Path,
    expected_exported_body_names: tuple[str, ...],
) -> ModeledObjectEntry:
    terminal_path = _parse_terminal_path(realized.terminal_path)
    centerline = build_tx_rect_void_centerline(realized)
    pcb_layer_z_positions_mm = tuple(
        float(layer_index) * (realized.pcb_thickness_mm + realized.layer_gap_mm)
        for layer_index in range(realized.layer_count)
    )
    copper_layer_z_positions_mm = tuple(
        pcb_z + realized.pcb_thickness_mm
        for pcb_z in pcb_layer_z_positions_mm
    )
    total_height_mm = copper_layer_z_positions_mm[-1] + realized.copper_thickness_mm
    return ModeledObjectEntry(
        object_id="tx_rect_void_coil",
        role="tx_single_coil",
        material="composite",
        model_state=True,
        step_path=str(output_step_path),
        expected_exported_body_names=expected_exported_body_names,
        expected_exported_body_count=len(expected_exported_body_names),
        canonical_coordinates=ModeledObjectCanonicalCoordinates(
            frame_origin_xyz=(0.0, 0.0, 0.0),
            outer_bounds_min_xyz=(realized.outer_bounds.min_x, realized.outer_bounds.min_y, 0.0),
            outer_bounds_max_xyz=(realized.outer_bounds.max_x, realized.outer_bounds.max_y, total_height_mm),
            outer_bounds_size_xyz=(realized.outer_x_mm, realized.outer_y_mm, total_height_mm),
            pcb_layer_z_positions_mm=pcb_layer_z_positions_mm,
            copper_layer_z_positions_mm=copper_layer_z_positions_mm,
        ),
        terminal_metadata=ModeledObjectTerminalMetadata(
            path=terminal_path.raw,
            outer_corner=terminal_path.outer_corner,
            inner_corner=terminal_path.inner_corner,
            direction=terminal_path.direction,
            start_point_xy_mm=centerline[0],
            end_point_xy_mm=centerline[-1],
        ),
    )


def export_tx_rect_void_step_from_spec(
    *,
    spec: TxRectVoidSpec,
    source_toml_path: Path,
    output_step_path: Path,
    metadata_path: Path,
    seed: int,
) -> TxRectVoidExportResult:
    realized = realize_tx_rect_void_spec(spec, seed=seed)
    boxes = build_tx_rect_void_box_specs(realized)
    scene = build_tx_rect_void_step_scene(boxes)
    expected_exported_body_names = _expected_exported_body_names(boxes)
    output_step_path.parent.mkdir(parents=True, exist_ok=True)
    export_ok = bd.export_step(scene, output_step_path)
    if export_ok is not True:
        raise RuntimeError(f"build123d export_step returned False: {output_step_path}")
    modeled_object = _build_modeled_object_entry(
        realized=realized,
        output_step_path=output_step_path,
        expected_exported_body_names=expected_exported_body_names,
    )
    result = TxRectVoidExportResult(
        source_toml_path=str(source_toml_path),
        output_step_path=str(output_step_path),
        metadata_path=str(metadata_path),
        expected_exported_body_names=expected_exported_body_names,
        expected_exported_body_count=len(expected_exported_body_names),
        realized=realized,
        boxes=boxes,
        modeled_objects=(modeled_object,),
    )
    _write_metadata(metadata_path, result)
    return result


def export_tx_rect_void_step(
    *,
    toml_path: Path,
    output_step_path: Path,
    metadata_path: Path,
    seed: int,
) -> TxRectVoidExportResult:
    spec = load_tx_rect_void_spec(toml_path)
    return export_tx_rect_void_step_from_spec(
        spec=spec,
        source_toml_path=toml_path,
        output_step_path=output_step_path,
        metadata_path=metadata_path,
        seed=seed,
    )


__all__ = [
    "BoxSpec",
    "ManufacturingSpec",
    "ModeledObjectCanonicalCoordinates",
    "ModeledObjectEntry",
    "ModeledObjectTerminalMetadata",
    "RangeSpec",
    "RealizedTxRectVoidCoil",
    "RectBounds",
    "SideGeometry",
    "TerminalPath",
    "TxCoilRangeSpec",
    "TxCoilSideGeometry",
    "TxRectVoidExportResult",
    "TxRectVoidSpec",
    "build_tx_rect_void_box_specs",
    "build_tx_rect_void_centerline",
    "build_tx_rect_void_step_scene",
    "export_tx_rect_void_step",
    "export_tx_rect_void_step_from_spec",
    "load_tx_rect_void_spec",
    "realize_tx_rect_void_spec",
]

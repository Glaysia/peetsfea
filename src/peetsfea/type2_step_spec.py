from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

Point3 = tuple[float, float, float]
ModeledObjectRole = Literal["tx_single_coil", "rx_single_coil"]


@dataclass(frozen=True)
class RangeSpec:
    is_integer: bool
    start: float
    end: float
    count: int


@dataclass(frozen=True)
class NonModelBoxSpec:
    object_id: str
    kind: str
    primitive: Literal["box"]
    present: Literal[True]
    non_model: Literal[True]
    material: str
    plane: Literal["XY", "YZ", "ZX"]
    origin_xyz: Point3
    size_xyz: Point3


@dataclass(frozen=True)
class ModeledTxSingleCoilSpec:
    object_id: str
    role: ModeledObjectRole
    material: str
    model_state: Literal[True]
    pcb_thickness_mm: float
    copper_thickness_mm: float
    outer_x_mm: RangeSpec
    outer_y_mm: RangeSpec
    turn_count: RangeSpec
    layer_count: RangeSpec
    layer_gap_mm: RangeSpec
    terminal_stub_length_mm: RangeSpec
    void_x_over_outer_x: RangeSpec
    void_y_over_outer_y: RangeSpec
    void_center_x_over_outer_x: RangeSpec
    void_center_y_over_outer_y: RangeSpec
    margin_ratio: RangeSpec
    metal_fill_factor: RangeSpec
    terminal_path: str


@dataclass(frozen=True)
class Type2StepSpec:
    source_toml_path: str
    non_model_objects: tuple[NonModelBoxSpec, ...]
    modeled_objects: tuple[ModeledTxSingleCoilSpec, ...]


def _require_key(table: dict[str, object], key: str, context: str) -> object:
    if key not in table:
        raise ValueError(f"{context} is missing required key '{key}'")
    return table[key]


def _require_table(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be a table")
    return cast(dict[str, object], value)


def _require_non_empty_str(table: dict[str, object], key: str, context: str) -> str:
    raw_value = _require_key(table, key, context)
    if not isinstance(raw_value, str):
        raise TypeError(f"{context}.{key} must be str")
    if raw_value == "":
        raise ValueError(f"{context}.{key} must be non-empty")
    return raw_value


def _require_true(table: dict[str, object], key: str, context: str) -> Literal[True]:
    raw_value = _require_key(table, key, context)
    if raw_value is not True:
        raise ValueError(f"{context}.{key} must be true")
    return True


def _require_float_value(table: dict[str, object], key: str, context: str) -> float:
    raw_value = _require_key(table, key, context)
    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
        raise TypeError(f"{context}.{key} must be number")
    return float(raw_value)


def _require_point3(table: dict[str, object], key: str, context: str, *, positive: bool) -> Point3:
    raw_value = _require_key(table, key, context)
    if not isinstance(raw_value, list):
        raise TypeError(f"{context}.{key} must be a list of three numbers")
    if len(raw_value) != 3:
        raise ValueError(f"{context}.{key} must contain exactly three numbers")
    parsed_values: list[float] = []
    for index, component in enumerate(raw_value):
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise TypeError(f"{context}.{key}[{index}] must be numeric")
        value = float(component)
        if positive and value <= 0.0:
            raise ValueError(f"{context}.{key}[{index}] must be > 0")
        parsed_values.append(value)
    return (parsed_values[0], parsed_values[1], parsed_values[2])


def _require_plane(table: dict[str, object], key: str, context: str) -> Literal["XY", "YZ", "ZX"]:
    value = _require_non_empty_str(table, key, context)
    if value == "XY":
        return "XY"
    if value == "YZ":
        return "YZ"
    if value == "ZX":
        return "ZX"
    raise ValueError(f"{context}.{key} must be one of XY, YZ, ZX")


def _require_range(
    table: dict[str, object],
    key: str,
    context: str,
    *,
    expect_integer: bool,
) -> RangeSpec:
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
    return RangeSpec(is_integer=raw_is_integer, start=start, end=end, count=raw_count)


def _parse_non_model_box(
    raw_object: object,
    *,
    index: int,
    seen_object_ids: set[str],
) -> NonModelBoxSpec:
    context = f"non_model_objects[{index}]"
    table = _require_table(raw_object, context)
    object_id = _require_non_empty_str(table, "id", context)
    if object_id in seen_object_ids:
        raise ValueError(f"duplicate object id: {object_id}")
    seen_object_ids.add(object_id)

    primitive = _require_non_empty_str(table, "primitive", context)
    if primitive != "box":
        raise ValueError(f"{context}.primitive must be 'box'")

    return NonModelBoxSpec(
        object_id=object_id,
        kind=_require_non_empty_str(table, "kind", context),
        primitive="box",
        present=_require_true(table, "present", context),
        non_model=_require_true(table, "non_model", context),
        material=_require_non_empty_str(table, "material", context),
        plane=_require_plane(table, "plane", context),
        origin_xyz=_require_point3(table, "origin_xyz", context, positive=False),
        size_xyz=_require_point3(table, "size_xyz", context, positive=True),
    )


def _parse_modeled_single_coil(
    raw_object: object,
    *,
    index: int,
    seen_object_ids: set[str],
) -> ModeledTxSingleCoilSpec:
    from peetsfea.tx_rect_void import profile_for_modeled_role

    context = f"modeled_objects[{index}]"
    table = _require_table(raw_object, context)
    object_id = _require_non_empty_str(table, "object_id", context)
    if object_id in seen_object_ids:
        raise ValueError(f"duplicate object id: {object_id}")
    seen_object_ids.add(object_id)

    role = _require_non_empty_str(table, "role", context)
    if role not in ("tx_single_coil", "rx_single_coil"):
        raise ValueError(f"unsupported modeled object role: {role}")
    modeled_role = cast(ModeledObjectRole, role)
    profile = profile_for_modeled_role(modeled_role)
    if object_id != profile.object_id:
        raise ValueError(
            f"prototype modeled object_id must be '{profile.object_id}' for role {role} "
            f"(actual={object_id})"
        )

    raw_model_state = _require_key(table, "model_state", context)
    if not isinstance(raw_model_state, bool):
        raise TypeError(f"{context}.model_state must be bool")
    if raw_model_state is not True:
        raise ValueError(f"{context}.model_state must be true")

    pcb_thickness_mm = _require_float_value(table, "pcb_thickness_mm", context)
    if pcb_thickness_mm <= 0.0:
        raise ValueError(f"{context}.pcb_thickness_mm must be > 0")
    copper_thickness_mm = _require_float_value(table, "copper_thickness_mm", context)
    if copper_thickness_mm <= 0.0:
        raise ValueError(f"{context}.copper_thickness_mm must be > 0")
    material = _require_non_empty_str(table, "material", context)
    if material != "composite":
        raise ValueError(f"{context}.material must be 'composite' (actual={material})")

    terminal_node = _require_table(_require_key(table, "terminal_path", context), f"{context}.terminal_path")
    if set(terminal_node.keys()) != {"value"}:
        raise ValueError(f"{context}.terminal_path must contain only ['value']")
    terminal_path = _require_non_empty_str(terminal_node, "value", f"{context}.terminal_path")

    return ModeledTxSingleCoilSpec(
        object_id=object_id,
        role=modeled_role,
        material=material,
        model_state=True,
        pcb_thickness_mm=pcb_thickness_mm,
        copper_thickness_mm=copper_thickness_mm,
        outer_x_mm=_require_range(table, "outer_x_mm", context, expect_integer=False),
        outer_y_mm=_require_range(table, "outer_y_mm", context, expect_integer=False),
        turn_count=_require_range(table, "turn_count", context, expect_integer=True),
        layer_count=_require_range(table, "layer_count", context, expect_integer=True),
        layer_gap_mm=_require_range(table, "layer_gap_mm", context, expect_integer=False),
        terminal_stub_length_mm=_require_range(table, "terminal_stub_length_mm", context, expect_integer=False),
        void_x_over_outer_x=_require_range(table, "void_x_over_outer_x", context, expect_integer=False),
        void_y_over_outer_y=_require_range(table, "void_y_over_outer_y", context, expect_integer=False),
        void_center_x_over_outer_x=_require_range(table, "void_center_x_over_outer_x", context, expect_integer=False),
        void_center_y_over_outer_y=_require_range(table, "void_center_y_over_outer_y", context, expect_integer=False),
        margin_ratio=_require_range(table, "margin_ratio", context, expect_integer=False),
        metal_fill_factor=_require_range(table, "metal_fill_factor", context, expect_integer=False),
        terminal_path=terminal_path,
    )


def load_type2_step_spec(toml_path: Path) -> Type2StepSpec:
    raw_text = toml_path.read_text(encoding="utf-8")
    raw_spec = tomllib.loads(raw_text)
    root = _require_table(raw_spec, toml_path.name)

    design = _require_table(_require_key(root, "design", toml_path.name), "design")
    units = _require_non_empty_str(design, "units", "design")
    if units != "mm":
        raise ValueError(f"design.units must be 'mm' (actual={units})")

    raw_non_model_objects = _require_key(root, "non_model_objects", toml_path.name)
    if not isinstance(raw_non_model_objects, list):
        raise TypeError("non_model_objects must be an array of tables")
    if len(raw_non_model_objects) == 0:
        raise ValueError("non_model_objects must not be empty")

    raw_modeled_objects = _require_key(root, "modeled_objects", toml_path.name)
    if not isinstance(raw_modeled_objects, list):
        raise TypeError("modeled_objects must be an array of tables")
    if len(raw_modeled_objects) == 0:
        raise ValueError("modeled_objects must not be empty")

    seen_object_ids: set[str] = set()
    non_model_objects = tuple(
        _parse_non_model_box(raw_object, index=index, seen_object_ids=seen_object_ids)
        for index, raw_object in enumerate(raw_non_model_objects)
    )
    modeled_objects = tuple(
        _parse_modeled_single_coil(raw_object, index=index, seen_object_ids=seen_object_ids)
        for index, raw_object in enumerate(raw_modeled_objects)
    )
    return Type2StepSpec(
        source_toml_path=str(toml_path),
        non_model_objects=non_model_objects,
        modeled_objects=modeled_objects,
    )


def _format_range(range_spec: RangeSpec) -> str:
    is_integer = "true" if range_spec.is_integer else "false"
    return f"[{is_integer}, {range_spec.start}, {range_spec.end}, {range_spec.count}]"


def render_tx_rect_void_toml(spec: ModeledTxSingleCoilSpec) -> str:
    return "\n".join(
        (
            'spec_version = "0.2.22"',
            'schema_id = "peetsfea.tx_rect_void_coil.step.v1"',
            "runtime_compatible = false",
            "",
            "[design]",
            'units = "mm"',
            "",
            "[manufacturing]",
            f"pcb_thickness_mm = {spec.pcb_thickness_mm}",
            f"copper_thickness_mm = {spec.copper_thickness_mm}",
            "",
            "[tx_coil.outer_x_mm]",
            f"range = {_format_range(spec.outer_x_mm)}",
            "[tx_coil.outer_y_mm]",
            f"range = {_format_range(spec.outer_y_mm)}",
            "[tx_coil.turn_count]",
            f"range = {_format_range(spec.turn_count)}",
            "[tx_coil.layer_count]",
            f"range = {_format_range(spec.layer_count)}",
            "[tx_coil.layer_gap_mm]",
            f"range = {_format_range(spec.layer_gap_mm)}",
            "[tx_coil.terminal_stub_length_mm]",
            f"range = {_format_range(spec.terminal_stub_length_mm)}",
            "[tx_coil.void_x_over_outer_x]",
            f"range = {_format_range(spec.void_x_over_outer_x)}",
            "[tx_coil.void_y_over_outer_y]",
            f"range = {_format_range(spec.void_y_over_outer_y)}",
            "[tx_coil.void_center_x_over_outer_x]",
            f"range = {_format_range(spec.void_center_x_over_outer_x)}",
            "[tx_coil.void_center_y_over_outer_y]",
            f"range = {_format_range(spec.void_center_y_over_outer_y)}",
            "[tx_coil.margin_ratio]",
            f"range = {_format_range(spec.margin_ratio)}",
            "[tx_coil.metal_fill_factor]",
            f"range = {_format_range(spec.metal_fill_factor)}",
            "[tx_coil.terminal_path]",
            f'value = "{spec.terminal_path}"',
            "",
        )
    )


__all__ = [
    "ModeledObjectRole",
    "ModeledTxSingleCoilSpec",
    "NonModelBoxSpec",
    "Point3",
    "RangeSpec",
    "Type2StepSpec",
    "load_type2_step_spec",
    "render_tx_rect_void_toml",
]

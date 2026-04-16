from __future__ import annotations

import argparse
import json
import sys
import tempfile
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, TypedDict, cast

import build123d as bd

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.tx_rect_void import export_tx_rect_void_step_from_spec
from peetsfea.tx_rect_void import load_tx_rect_void_spec

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_TOML_PATH = REPO_ROOT / "examples" / "type2.toml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "run" / "step" / "type2"
DEFAULT_LEDGER_PATH = DEFAULT_OUTPUT_DIR / "type2_step_ledger.json"

Point3 = tuple[float, float, float]


class CanonicalCoordinates(TypedDict):
    frame_origin_xyz: Point3
    outer_bounds_min_xyz: Point3
    outer_bounds_max_xyz: Point3
    outer_bounds_size_xyz: Point3


class NonModelSceneMemberLedgerEntry(TypedDict):
    object_id: str
    role: str
    material: str
    model_state: Literal[False]
    canonical_coordinates: CanonicalCoordinates
    plane: Literal["XY", "YZ", "ZX"]
    non_model: Literal[True]


class NonModelObjectLedgerEntry(TypedDict):
    object_id: str
    role: str
    material: str
    model_state: Literal[False]
    step_path: str
    canonical_coordinates: CanonicalCoordinates
    plane: Literal["XY", "YZ", "ZX", "mixed"]
    non_model: Literal[True]
    member_object_ids: tuple[str, ...]
    member_objects: tuple[NonModelSceneMemberLedgerEntry, ...]


class ModeledObjectLedgerEntry(TypedDict):
    object_id: str
    role: Literal["tx_single_coil"]
    material: str
    model_state: Literal[True]
    step_path: str
    expected_exported_body_names: tuple[str, ...]
    expected_exported_body_count: int
    canonical_coordinates: dict[str, object]
    terminal_metadata: dict[str, object]
    source_metadata_path: str


class Type2StepLedger(TypedDict):
    source_toml_path: str
    output_dir: str
    seed: int
    non_model_objects: list[NonModelObjectLedgerEntry]
    modeled_objects: list[ModeledObjectLedgerEntry]


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
    role: Literal["tx_single_coil"]
    material: str
    model_state: Literal[True]
    pcb_thickness_mm: float
    copper_thickness_mm: float
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


def _parse_modeled_tx_single_coil(
    raw_object: object,
    *,
    index: int,
    seen_object_ids: set[str],
) -> ModeledTxSingleCoilSpec:
    context = f"modeled_objects[{index}]"
    table = _require_table(raw_object, context)
    object_id = _require_non_empty_str(table, "object_id", context)
    if object_id in seen_object_ids:
        raise ValueError(f"duplicate object id: {object_id}")
    seen_object_ids.add(object_id)

    role = _require_non_empty_str(table, "role", context)
    if role != "tx_single_coil":
        raise ValueError(f"unsupported modeled object role: {role}")
    if object_id != "tx_rect_void_coil":
        raise ValueError(
            "prototype modeled object_id must be 'tx_rect_void_coil' "
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
        role="tx_single_coil",
        material=material,
        model_state=True,
        pcb_thickness_mm=pcb_thickness_mm,
        copper_thickness_mm=copper_thickness_mm,
        outer_x_mm=_require_range(table, "outer_x_mm", context, expect_integer=False),
        outer_y_mm=_require_range(table, "outer_y_mm", context, expect_integer=False),
        turn_count=_require_range(table, "turn_count", context, expect_integer=True),
        layer_count=_require_range(table, "layer_count", context, expect_integer=True),
        layer_gap_mm=_require_range(table, "layer_gap_mm", context, expect_integer=False),
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
    if len(raw_modeled_objects) != 1:
        raise ValueError(
            "modeled_objects must contain exactly one tx_single_coil object in the prototype stage "
            f"(actual={len(raw_modeled_objects)})"
        )

    seen_object_ids: set[str] = set()
    non_model_objects = tuple(
        _parse_non_model_box(raw_object, index=index, seen_object_ids=seen_object_ids)
        for index, raw_object in enumerate(raw_non_model_objects)
    )
    modeled_objects = tuple(
        _parse_modeled_tx_single_coil(raw_object, index=index, seen_object_ids=seen_object_ids)
        for index, raw_object in enumerate(raw_modeled_objects)
    )
    return Type2StepSpec(
        source_toml_path=str(toml_path),
        non_model_objects=non_model_objects,
        modeled_objects=modeled_objects,
    )


def _build_non_model_shape(spec: NonModelBoxSpec) -> bd.Shape:
    size_x, size_y, size_z = spec.size_xyz
    box = bd.Box(
        size_x,
        size_y,
        size_z,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    ).moved(bd.Location(spec.origin_xyz))
    box.label = spec.object_id
    return box


def _canonical_from_box(spec: NonModelBoxSpec) -> CanonicalCoordinates:
    origin_x, origin_y, origin_z = spec.origin_xyz
    size_x, size_y, size_z = spec.size_xyz
    return {
        "frame_origin_xyz": spec.origin_xyz,
        "outer_bounds_min_xyz": (origin_x, origin_y, origin_z),
        "outer_bounds_max_xyz": (origin_x + size_x, origin_y + size_y, origin_z + size_z),
        "outer_bounds_size_xyz": spec.size_xyz,
    }


def _canonical_from_non_model_scene(specs: tuple[NonModelBoxSpec, ...]) -> CanonicalCoordinates:
    if not specs:
        raise ValueError("non-model scene canonical coordinates require at least one spec")
    min_x = min(spec.origin_xyz[0] for spec in specs)
    min_y = min(spec.origin_xyz[1] for spec in specs)
    min_z = min(spec.origin_xyz[2] for spec in specs)
    max_x = max(spec.origin_xyz[0] + spec.size_xyz[0] for spec in specs)
    max_y = max(spec.origin_xyz[1] + spec.size_xyz[1] for spec in specs)
    max_z = max(spec.origin_xyz[2] + spec.size_xyz[2] for spec in specs)
    return {
        "frame_origin_xyz": (min_x, min_y, min_z),
        "outer_bounds_min_xyz": (min_x, min_y, min_z),
        "outer_bounds_max_xyz": (max_x, max_y, max_z),
        "outer_bounds_size_xyz": (max_x - min_x, max_y - min_y, max_z - min_z),
    }


def _format_range(range_spec: RangeSpec) -> str:
    is_integer = "true" if range_spec.is_integer else "false"
    return f"[{is_integer}, {range_spec.start}, {range_spec.end}, {range_spec.count}]"


def _render_tx_rect_void_toml(spec: ModeledTxSingleCoilSpec) -> str:
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


def _export_non_model_object(spec: NonModelBoxSpec, *, output_path: Path) -> NonModelObjectLedgerEntry:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shape = _build_non_model_shape(spec)
    export_ok = bd.export_step(shape, output_path)
    if export_ok is not True:
        raise RuntimeError(f"build123d export_step returned False for non-model object: {spec.object_id}")
    return {
        "object_id": spec.object_id,
        "role": spec.kind,
        "material": spec.material,
        "model_state": False,
        "step_path": str(output_path),
        "canonical_coordinates": _canonical_from_box(spec),
        "plane": spec.plane,
        "non_model": True,
        "member_object_ids": (spec.object_id,),
        "member_objects": (
            {
                "object_id": spec.object_id,
                "role": spec.kind,
                "material": spec.material,
                "model_state": False,
                "canonical_coordinates": _canonical_from_box(spec),
                "plane": spec.plane,
                "non_model": True,
            },
        ),
    }


def _export_non_model_scene_object(
    specs: tuple[NonModelBoxSpec, ...],
    *,
    output_path: Path,
) -> NonModelObjectLedgerEntry:
    if not specs:
        raise ValueError("non-model scene export requires at least one spec")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shapes = [_build_non_model_shape(spec) for spec in specs]
    scene = bd.Compound(children=shapes, label="type2_non_model_scene")
    export_ok = bd.export_step(scene, output_path)
    if export_ok is not True:
        raise RuntimeError(f"build123d export_step returned False for non-model scene: {output_path}")
    material_names = tuple(sorted({spec.material for spec in specs}))
    material = material_names[0] if len(material_names) == 1 else "mixed"
    member_objects: list[NonModelSceneMemberLedgerEntry] = []
    for spec in specs:
        member_objects.append(
            {
                "object_id": spec.object_id,
                "role": spec.kind,
                "material": spec.material,
                "model_state": False,
                "canonical_coordinates": _canonical_from_box(spec),
                "plane": spec.plane,
                "non_model": True,
            }
        )
    return {
        "object_id": "type2_non_model_scene",
        "role": "non_model_scene",
        "material": material,
        "model_state": False,
        "step_path": str(output_path),
        "canonical_coordinates": _canonical_from_non_model_scene(specs),
        "plane": "mixed",
        "non_model": True,
        "member_object_ids": tuple(spec.object_id for spec in specs),
        "member_objects": tuple(member_objects),
    }


def _export_modeled_tx_single_coil(
    spec: ModeledTxSingleCoilSpec,
    *,
    source_toml_path: Path,
    output_path: Path,
    metadata_path: Path,
    seed: int,
) -> ModeledObjectLedgerEntry:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="type2_tx_rect_void_") as temp_dir:
        temp_toml_path = Path(temp_dir) / f"{spec.object_id}.toml"
        temp_toml_path.write_text(_render_tx_rect_void_toml(spec), encoding="utf-8")
        tx_rect_void_spec = load_tx_rect_void_spec(temp_toml_path)
        export_result = export_tx_rect_void_step_from_spec(
            spec=tx_rect_void_spec,
            source_toml_path=source_toml_path,
            output_step_path=output_path,
            metadata_path=metadata_path,
            seed=seed,
        )
    if len(export_result.modeled_objects) != 1:
        raise RuntimeError(
            "tx_rect_void export must return exactly one modeled object "
            f"(actual={len(export_result.modeled_objects)})"
        )
    modeled_object_raw = asdict(export_result.modeled_objects[0])
    modeled_object = _require_table(modeled_object_raw, f"modeled export [{spec.object_id}]")
    exported_object_id = _require_non_empty_str(modeled_object, "object_id", "modeled export object")
    if exported_object_id != spec.object_id:
        raise RuntimeError(
            "modeled object id mismatch between type2 TOML and tx_rect_void export "
            f"(spec={spec.object_id}, exported={exported_object_id})"
        )
    exported_material = _require_non_empty_str(modeled_object, "material", "modeled export object")
    if exported_material != spec.material:
        raise RuntimeError(
            "modeled object material mismatch between type2 TOML and tx_rect_void export "
            f"(spec={spec.material}, exported={exported_material})"
        )
    exported_role = _require_non_empty_str(modeled_object, "role", "modeled export object")
    if exported_role != "tx_single_coil":
        raise RuntimeError(f"modeled export role must be tx_single_coil (actual={exported_role})")
    raw_model_state = _require_key(modeled_object, "model_state", "modeled export object")
    if raw_model_state is not True:
        raise RuntimeError("modeled export model_state must be true")
    exported_step_path = _require_non_empty_str(modeled_object, "step_path", "modeled export object")
    if exported_step_path != str(output_path):
        raise RuntimeError(
            "modeled export step_path does not match requested output path "
            f"(exported={exported_step_path}, expected={output_path})"
        )

    raw_canonical = _require_key(modeled_object, "canonical_coordinates", "modeled export object")
    canonical_coordinates = _require_table(raw_canonical, "modeled export canonical_coordinates")
    raw_terminal = _require_key(modeled_object, "terminal_metadata", "modeled export object")
    terminal_metadata = _require_table(raw_terminal, "modeled export terminal_metadata")
    raw_expected_names = _require_key(modeled_object, "expected_exported_body_names", "modeled export object")
    if isinstance(raw_expected_names, (str, bytes)) or not isinstance(raw_expected_names, (list, tuple)):
        raise TypeError("modeled export expected_exported_body_names must be a list or tuple")
    expected_exported_body_names: list[str] = []
    for index, raw_name in enumerate(raw_expected_names):
        if not isinstance(raw_name, str) or raw_name == "":
            raise TypeError(f"modeled export expected_exported_body_names[{index}] must be non-empty str")
        expected_exported_body_names.append(raw_name)
    raw_expected_count = _require_key(modeled_object, "expected_exported_body_count", "modeled export object")
    if isinstance(raw_expected_count, bool) or not isinstance(raw_expected_count, int):
        raise TypeError("modeled export expected_exported_body_count must be int")
    if raw_expected_count != len(expected_exported_body_names):
        raise RuntimeError(
            "modeled export expected body count mismatch "
            f"(count={raw_expected_count}, names={expected_exported_body_names})"
        )
    return {
        "object_id": exported_object_id,
        "role": "tx_single_coil",
        "material": exported_material,
        "model_state": True,
        "step_path": exported_step_path,
        "expected_exported_body_names": tuple(expected_exported_body_names),
        "expected_exported_body_count": raw_expected_count,
        "canonical_coordinates": canonical_coordinates,
        "terminal_metadata": terminal_metadata,
        "source_metadata_path": str(metadata_path),
    }


def export_type2_tx_single_coil_artifact(
    *,
    toml_path: Path,
    output_step_path: Path,
    metadata_path: Path,
    seed: int,
) -> ModeledObjectLedgerEntry:
    spec = load_type2_step_spec(toml_path)
    if len(spec.modeled_objects) != 1:
        raise RuntimeError(
            "type2 tx_single_coil direct export requires exactly one modeled object "
            f"(actual={len(spec.modeled_objects)})"
        )
    return _export_modeled_tx_single_coil(
        spec.modeled_objects[0],
        source_toml_path=toml_path,
        output_path=output_step_path,
        metadata_path=metadata_path,
        seed=seed,
    )


def export_type2_step_artifacts(
    *,
    toml_path: Path = SOURCE_TOML_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    seed: int = 0,
) -> Type2StepLedger:
    spec = load_type2_step_spec(toml_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    object_steps_dir = output_dir / "objects"
    object_metadata_dir = output_dir / "metadata"

    non_model_step_path = output_dir / "type2_non_model_scene.step"
    non_model_entries = [_export_non_model_scene_object(spec.non_model_objects, output_path=non_model_step_path)]

    modeled_entries: list[ModeledObjectLedgerEntry] = []
    for modeled_spec in spec.modeled_objects:
        step_path = object_steps_dir / f"{modeled_spec.object_id}.step"
        metadata_path = object_metadata_dir / f"{modeled_spec.object_id}.metadata.json"
        modeled_entries.append(
            _export_modeled_tx_single_coil(
                modeled_spec,
                source_toml_path=toml_path,
                output_path=step_path,
                metadata_path=metadata_path,
                seed=seed,
            )
        )

    ledger: Type2StepLedger = {
        "source_toml_path": spec.source_toml_path,
        "output_dir": str(output_dir),
        "seed": seed,
        "non_model_objects": non_model_entries,
        "modeled_objects": modeled_entries,
    }
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    return ledger


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate type2 STEP artifacts from examples/type2.toml.")
    parser.add_argument("--toml", type=Path, default=SOURCE_TOML_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> Type2StepLedger:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)
    ledger = export_type2_step_artifacts(
        toml_path=args.toml,
        output_dir=args.output_dir,
        ledger_path=args.ledger,
        seed=args.seed,
    )
    print(f"source TOML: {ledger['source_toml_path']}")
    print(f"output dir: {ledger['output_dir']}")
    print(f"ledger JSON: {args.ledger}")
    print(f"non-model object count: {len(ledger['non_model_objects'])}")
    print(f"modeled object count: {len(ledger['modeled_objects'])}")
    return ledger


if __name__ == "__main__":
    main()

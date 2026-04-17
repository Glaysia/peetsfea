from __future__ import annotations

from pathlib import Path
from typing import Literal, TypedDict
import tomllib

import build123d as bd


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_TOML_PATH = REPO_ROOT / "examples" / "type2_fixed.toml"
OUTPUT_STEP_PATH = REPO_ROOT / "run" / "step" / "type2" / "type2_non_model_scene.step"

Point3 = tuple[float, float, float]


class NonModelBoxSpec(TypedDict):
    id: str
    kind: str
    primitive: Literal["box"]
    present: Literal[True]
    non_model: Literal[True]
    material: str
    plane: Literal["XY", "YZ", "ZX"]
    origin_xyz: Point3
    size_xyz: Point3


def _require_key(table: dict[str, object], key: str, context: str) -> object:
    if key not in table:
        raise ValueError(f"{context} is missing required key '{key}'")
    return table[key]


def _require_str(table: dict[str, object], key: str, context: str) -> str:
    raw_value = _require_key(table, key, context)
    if not isinstance(raw_value, str):
        raise TypeError(f"{context}.{key} must be str")
    return raw_value


def _require_true(table: dict[str, object], key: str, context: str) -> Literal[True]:
    raw_value = _require_key(table, key, context)
    if raw_value is not True:
        raise ValueError(f"{context}.{key} must be true")
    return True


def _require_plane(table: dict[str, object], key: str, context: str) -> Literal["XY", "YZ", "ZX"]:
    value = _require_str(table, key, context)
    if value == "XY":
        return "XY"
    if value == "YZ":
        return "YZ"
    if value == "ZX":
        return "ZX"
    raise ValueError(f"{context}.{key} must be one of XY, YZ, ZX")


def _require_point3(table: dict[str, object], key: str, context: str, *, positive: bool = False) -> Point3:
    raw_value = _require_key(table, key, context)
    if not isinstance(raw_value, list):
        raise TypeError(f"{context}.{key} must be a list of three numbers")
    if len(raw_value) != 3:
        raise ValueError(f"{context}.{key} must contain exactly three numbers")

    parsed_values: list[float] = []
    for index, component in enumerate(raw_value):
        if not isinstance(component, int | float):
            raise TypeError(f"{context}.{key}[{index}] must be numeric")
        value = float(component)
        if positive and value <= 0.0:
            raise ValueError(f"{context}.{key}[{index}] must be > 0")
        parsed_values.append(value)

    return (parsed_values[0], parsed_values[1], parsed_values[2])


def _parse_non_model_box(raw_object: object, *, seen_ids: set[str], index: int) -> NonModelBoxSpec:
    context = f"non_model_objects[{index}]"
    if not isinstance(raw_object, dict):
        raise TypeError(f"{context} must be a table")
    table: dict[str, object] = raw_object

    object_id = _require_str(table, "id", context)
    if object_id in seen_ids:
        raise ValueError(f"duplicate non_model_objects id: {object_id}")
    seen_ids.add(object_id)

    primitive = _require_str(table, "primitive", context)
    if primitive != "box":
        raise ValueError(f"{context}.primitive must be 'box'")

    return {
        "id": object_id,
        "kind": _require_str(table, "kind", context),
        "primitive": "box",
        "present": _require_true(table, "present", context),
        "non_model": _require_true(table, "non_model", context),
        "material": _require_str(table, "material", context),
        "plane": _require_plane(table, "plane", context),
        "origin_xyz": _require_point3(table, "origin_xyz", context),
        "size_xyz": _require_point3(table, "size_xyz", context, positive=True),
    }


def load_non_model_boxes(toml_path: Path) -> tuple[NonModelBoxSpec, ...]:
    raw_spec = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    raw_objects = _require_key(raw_spec, "non_model_objects", toml_path.name)
    if not isinstance(raw_objects, list):
        raise TypeError("non_model_objects must be an array of tables")

    seen_ids: set[str] = set()
    boxes = tuple(
        _parse_non_model_box(raw_object, seen_ids=seen_ids, index=index)
        for index, raw_object in enumerate(raw_objects)
    )
    if not boxes:
        raise ValueError("non_model_objects must not be empty")
    return boxes


def _build_box(spec: NonModelBoxSpec) -> bd.Shape:
    size_x, size_y, size_z = spec["size_xyz"]
    origin_xyz = spec["origin_xyz"]
    box = bd.Box(
        size_x,
        size_y,
        size_z,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    ).moved(bd.Location(origin_xyz))
    box.label = spec["id"]
    return box


def build_non_model_scene(box_specs: tuple[NonModelBoxSpec, ...]) -> bd.Compound:
    boxes = [_build_box(spec) for spec in box_specs]
    return bd.Compound(children=boxes, label="type2_non_model_scene")


def export_non_model_scene(
    *,
    toml_path: Path = SOURCE_TOML_PATH,
    output_path: Path = OUTPUT_STEP_PATH,
) -> Path:
    box_specs = load_non_model_boxes(toml_path)
    scene = build_non_model_scene(box_specs)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    export_ok = bd.export_step(scene, output_path)
    if export_ok is not True:
        raise RuntimeError(f"build123d export_step returned False: {output_path}")

    bbox = scene.bounding_box()
    print(f"source TOML: {toml_path}")
    print(f"output STEP: {output_path}")
    print(f"non-model object count: {len(box_specs)}")
    print(f"compound bbox min: {tuple(bbox.min)}")
    print(f"compound bbox max: {tuple(bbox.max)}")
    print(f"compound bbox size: {tuple(bbox.size)}")
    return output_path


def main() -> Path:
    return export_non_model_scene()


if __name__ == "__main__":
    main()

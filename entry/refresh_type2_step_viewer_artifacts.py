from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from entry.generate_type2_step import (
    DEFAULT_LEDGER_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SCENE_STEP_PATH,
    SOURCE_TOML_PATH,
    export_type2_step_artifacts,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
_PLACEMENT_TOLERANCE = 1e-9


class Type2StepViewerRefreshResult(TypedDict):
    source_toml_path: str
    output_dir: str
    ledger_path: str
    scene_step_path: str
    seed: int


def _require_key(table: dict[str, object], *, key: str, context: str) -> object:
    if key not in table:
        raise ValueError(f"{context} is missing required key '{key}'")
    return table[key]


def _require_table(value: object, *, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be a table/object")
    return cast(dict[str, object], value)


def _require_non_empty_str(value: object, *, context: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{context} must be str")
    if value == "":
        raise ValueError(f"{context} must be non-empty")
    return value


def _require_entry_list(value: object, *, context: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise TypeError(f"{context} must be a list")
    entries: list[dict[str, object]] = []
    for index, raw_entry in enumerate(value):
        entries.append(_require_table(raw_entry, context=f"{context}[{index}]"))
    return entries


def _require_float(value: object, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{context} must be number")
    return float(value)


def _require_float_triplet(value: object, *, context: str) -> tuple[float, float, float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{context} must be a sequence of length 3")
    if len(value) != 3:
        raise ValueError(f"{context} must contain exactly 3 entries")
    return (
        _require_float(value[0], context=f"{context}[0]"),
        _require_float(value[1], context=f"{context}[1]"),
        _require_float(value[2], context=f"{context}[2]"),
    )


def _require_existing_path_from_text(raw_path: object, *, context: str) -> Path:
    path_text = _require_non_empty_str(raw_path, context=context)
    resolved_path = Path(path_text).resolve(strict=False)
    if not resolved_path.is_file():
        raise FileNotFoundError(f"{context} does not exist: {resolved_path}")
    return resolved_path


def _canonical_coordinates(entry: dict[str, object], *, context: str) -> dict[str, object]:
    return _require_table(
        _require_key(entry, key="canonical_coordinates", context=context),
        context=f"{context}.canonical_coordinates",
    )


def _outer_bounds_min_xyz(entry: dict[str, object], *, context: str) -> tuple[float, float, float]:
    canonical_coordinates = _canonical_coordinates(entry, context=context)
    return _require_float_triplet(
        _require_key(canonical_coordinates, key="outer_bounds_min_xyz", context=f"{context}.canonical_coordinates"),
        context=f"{context}.canonical_coordinates.outer_bounds_min_xyz",
    )


def _outer_bounds_max_xyz(entry: dict[str, object], *, context: str) -> tuple[float, float, float]:
    canonical_coordinates = _canonical_coordinates(entry, context=context)
    return _require_float_triplet(
        _require_key(canonical_coordinates, key="outer_bounds_max_xyz", context=f"{context}.canonical_coordinates"),
        context=f"{context}.canonical_coordinates.outer_bounds_max_xyz",
    )


def _outer_bounds_size_xyz(entry: dict[str, object], *, context: str) -> tuple[float, float, float]:
    canonical_coordinates = _canonical_coordinates(entry, context=context)
    return _require_float_triplet(
        _require_key(canonical_coordinates, key="outer_bounds_size_xyz", context=f"{context}.canonical_coordinates"),
        context=f"{context}.canonical_coordinates.outer_bounds_size_xyz",
    )


def _remove_output_dir(output_dir: Path) -> None:
    if not output_dir.exists():
        return
    if not output_dir.is_dir():
        raise RuntimeError(f"type2 STEP output path must be a directory when present: {output_dir}")
    shutil.rmtree(output_dir)


def _load_step_ledger(ledger_path: Path) -> dict[str, object]:
    if not ledger_path.is_file():
        raise FileNotFoundError(f"type2 STEP ledger not found: {ledger_path}")
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    return _require_table(payload, context="type2_step_ledger")


def _scene_step_path(ledger_payload: dict[str, object]) -> Path:
    return _require_existing_path_from_text(
        _require_key(ledger_payload, key="scene_step_path", context="type2_step_ledger"),
        context="type2_step_ledger.scene_step_path",
    )


def _single_non_model_scene_entry(ledger_payload: dict[str, object]) -> dict[str, object]:
    non_model_objects = _require_entry_list(
        _require_key(ledger_payload, key="non_model_objects", context="type2_step_ledger"),
        context="type2_step_ledger.non_model_objects",
    )
    if len(non_model_objects) != 1:
        raise ValueError(
            "type2 STEP ledger must contain exactly one non-model scene entry "
            f"(actual={len(non_model_objects)})"
        )
    return non_model_objects[0]


def _member_objects(non_model_entry: dict[str, object], *, context: str) -> list[dict[str, object]]:
    return _require_entry_list(
        _require_key(non_model_entry, key="member_objects", context=context),
        context=f"{context}.member_objects",
    )


def _member_object_by_id(non_model_entry: dict[str, object], *, object_id: str) -> dict[str, object]:
    member_objects = _member_objects(non_model_entry, context="type2_step_ledger.non_model_objects[0]")
    matches: list[dict[str, object]] = []
    for index, member_object in enumerate(member_objects):
        member_context = f"type2_step_ledger.non_model_objects[0].member_objects[{index}]"
        actual_object_id = _require_non_empty_str(
            _require_key(member_object, key="object_id", context=member_context),
            context=f"{member_context}.object_id",
        )
        if actual_object_id == object_id:
            matches.append(member_object)
    if len(matches) != 1:
        raise ValueError(
            f"type2 STEP ledger must contain exactly one member object for {object_id} "
            f"(actual={len(matches)})"
        )
    return matches[0]


def _modeled_object_by_id(ledger_payload: dict[str, object], *, object_id: str) -> dict[str, object]:
    modeled_objects = _require_entry_list(
        _require_key(ledger_payload, key="modeled_objects", context="type2_step_ledger"),
        context="type2_step_ledger.modeled_objects",
    )
    matches: list[dict[str, object]] = []
    for index, modeled_object in enumerate(modeled_objects):
        modeled_context = f"type2_step_ledger.modeled_objects[{index}]"
        actual_object_id = _require_non_empty_str(
            _require_key(modeled_object, key="object_id", context=modeled_context),
            context=f"{modeled_context}.object_id",
        )
        if actual_object_id == object_id:
            matches.append(modeled_object)
    if len(matches) != 1:
        raise ValueError(
            f"type2 STEP ledger must contain exactly one modeled object for {object_id} "
            f"(actual={len(matches)})"
        )
    return matches[0]


def _assert_close(*, actual: float, expected: float, context: str) -> None:
    if abs(actual - expected) > _PLACEMENT_TOLERANCE:
        raise ValueError(f"{context} must match expected value (actual={actual}, expected={expected})")


def _validate_owner_fit(
    *,
    modeled_entry: dict[str, object],
    owner_entry: dict[str, object],
    context: str,
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    modeled_min_xyz = _outer_bounds_min_xyz(modeled_entry, context=context)
    modeled_max_xyz = _outer_bounds_max_xyz(modeled_entry, context=context)
    modeled_size_xyz = _outer_bounds_size_xyz(modeled_entry, context=context)
    owner_min_xyz = _outer_bounds_min_xyz(owner_entry, context=f"{context}.owner")
    owner_size_xyz = _outer_bounds_size_xyz(owner_entry, context=f"{context}.owner")
    if (
        modeled_size_xyz[0] > owner_size_xyz[0]
        or modeled_size_xyz[1] > owner_size_xyz[1]
        or modeled_size_xyz[2] > owner_size_xyz[2]
    ):
        raise ValueError(
            f"{context} must fit inside owner bounds "
            f"(modeled_size={modeled_size_xyz}, owner_size={owner_size_xyz})"
        )
    return (modeled_min_xyz, modeled_max_xyz, modeled_size_xyz, owner_min_xyz)


def _validate_tx_placement(modeled_entry: dict[str, object], owner_entry: dict[str, object]) -> None:
    modeled_min_xyz, _modeled_max_xyz, modeled_size_xyz, owner_min_xyz = _validate_owner_fit(
        modeled_entry=modeled_entry,
        owner_entry=owner_entry,
        context="tx_single_coil",
    )
    owner_size_xyz = _outer_bounds_size_xyz(owner_entry, context="tx_single_coil.owner")
    expected_min_x = owner_min_xyz[0] + (owner_size_xyz[0] - modeled_size_xyz[0]) / 2.0
    expected_min_y = owner_min_xyz[1] + (owner_size_xyz[1] - modeled_size_xyz[1]) / 2.0
    expected_min_z = owner_min_xyz[2] + owner_size_xyz[2] - modeled_size_xyz[2]
    _assert_close(actual=modeled_min_xyz[0], expected=expected_min_x, context="tx_single_coil.min_x")
    _assert_close(actual=modeled_min_xyz[1], expected=expected_min_y, context="tx_single_coil.min_y")
    _assert_close(actual=modeled_min_xyz[2], expected=expected_min_z, context="tx_single_coil.min_z")


def _validate_rx_placement(modeled_entry: dict[str, object], owner_entry: dict[str, object]) -> None:
    modeled_min_xyz, modeled_max_xyz, modeled_size_xyz, owner_min_xyz = _validate_owner_fit(
        modeled_entry=modeled_entry,
        owner_entry=owner_entry,
        context="rx_single_coil",
    )
    owner_max_xyz = _outer_bounds_max_xyz(owner_entry, context="rx_single_coil.owner")
    owner_size_xyz = _outer_bounds_size_xyz(owner_entry, context="rx_single_coil.owner")
    expected_min_x = owner_max_xyz[0] - modeled_size_xyz[0]
    expected_min_y = owner_min_xyz[1] + (owner_size_xyz[1] - modeled_size_xyz[1]) / 2.0
    expected_min_z = owner_min_xyz[2]
    _assert_close(actual=modeled_min_xyz[0], expected=expected_min_x, context="rx_single_coil.min_x")
    _assert_close(actual=modeled_min_xyz[1], expected=expected_min_y, context="rx_single_coil.min_y")
    _assert_close(actual=modeled_min_xyz[2], expected=expected_min_z, context="rx_single_coil.min_z")
    _assert_close(actual=modeled_max_xyz[0], expected=owner_max_xyz[0], context="rx_single_coil.max_x")


def validate_type2_step_viewer_placement_contract(ledger_payload: dict[str, object]) -> None:
    non_model_entry = _single_non_model_scene_entry(ledger_payload)
    tx_owner = _member_object_by_id(non_model_entry, object_id="tx_region")
    rx_owner = _member_object_by_id(non_model_entry, object_id="rx_region_max")
    tx_modeled = _modeled_object_by_id(ledger_payload, object_id="tx_rect_void_coil")
    rx_modeled = _modeled_object_by_id(ledger_payload, object_id="rx_rect_void_coil")
    _validate_tx_placement(tx_modeled, tx_owner)
    _validate_rx_placement(rx_modeled, rx_owner)


def refresh_type2_step_viewer_artifacts(
    *,
    toml_path: Path = SOURCE_TOML_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    seed: int = 0,
) -> Type2StepViewerRefreshResult:
    _remove_output_dir(output_dir)
    export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=output_dir,
        ledger_path=ledger_path,
        seed=seed,
    )
    ledger_payload = _load_step_ledger(ledger_path)
    validate_type2_step_viewer_placement_contract(ledger_payload)
    scene_step_path = _scene_step_path(ledger_payload)
    return {
        "source_toml_path": str(toml_path),
        "output_dir": str(output_dir),
        "ledger_path": str(ledger_path),
        "scene_step_path": str(scene_step_path),
        "seed": seed,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean-refresh type2 STEP viewer artifacts.")
    parser.add_argument("--toml", type=Path, default=SOURCE_TOML_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--scene-step", type=Path, default=DEFAULT_SCENE_STEP_PATH)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> Type2StepViewerRefreshResult:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)
    result = refresh_type2_step_viewer_artifacts(
        toml_path=args.toml,
        output_dir=args.output_dir,
        ledger_path=args.ledger,
        seed=args.seed,
    )
    if Path(result["scene_step_path"]).resolve(strict=False) != Path(args.scene_step).resolve(strict=False):
        raise RuntimeError(
            "refreshed scene STEP path does not match requested --scene-step "
            f"(result={result['scene_step_path']}, requested={args.scene_step})"
        )
    print(f"source TOML: {result['source_toml_path']}")
    print(f"output dir: {result['output_dir']}")
    print(f"ledger JSON: {result['ledger_path']}")
    print(f"scene STEP: {result['scene_step_path']}")
    return result


if __name__ == "__main__":
    main()

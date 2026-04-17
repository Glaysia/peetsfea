from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypedDict, cast

_SUPPORTED_ROLES: frozenset[str] = frozenset({"tx_single_coil", "rx_single_coil"})
_SUPPORTED_PLANES: frozenset[str] = frozenset({"XY", "YZ"})
_OUTER_CORNERS: frozenset[str] = frozenset({"A", "B", "C", "D"})
_INNER_CORNERS: frozenset[str] = frozenset({"a", "b", "c", "d"})
_PATH_DIRECTIONS: frozenset[str] = frozenset({"cw", "ccw"})


class ImportedModeledObjectCanonicalCoordinates(TypedDict):
    frame_origin_xyz: tuple[float, float, float]
    outer_bounds_min_xyz: tuple[float, float, float]
    outer_bounds_max_xyz: tuple[float, float, float]
    outer_bounds_size_xyz: tuple[float, float, float]
    pcb_layer_z_positions_mm: tuple[float, ...]
    copper_layer_z_positions_mm: tuple[float, ...]


class ImportedModeledObjectTerminalMetadata(TypedDict):
    path: str
    outer_corner: Literal["A", "B", "C", "D"]
    inner_corner: Literal["a", "b", "c", "d"]
    direction: Literal["cw", "ccw"]
    start_point_plane_mm: tuple[float, float]
    end_point_plane_mm: tuple[float, float]
    port_sheet_vertices_xyz: tuple[tuple[float, float, float], ...]


class ImportedModeledObjectEntry(TypedDict):
    object_id: str
    role: Literal["tx_single_coil", "rx_single_coil"]
    plane: Literal["XY", "YZ"]
    placement_owner_id: str
    material: str
    model_state: Literal[True]
    canonical_coordinates: ImportedModeledObjectCanonicalCoordinates
    terminal_metadata: ImportedModeledObjectTerminalMetadata
    imported_object_names: tuple[str, ...]


def _require_key(table: dict[str, object], *, key: str, context: str) -> object:
    assert key in table, f"{context} is missing required key '{key}'"
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


def _require_float(value: object, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{context} must be number")
    return float(value)


def _require_float_pair(value: object, *, context: str) -> tuple[float, float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{context} must be a sequence of length 2")
    if len(value) != 2:
        raise ValueError(f"{context} must contain exactly 2 entries")
    return (
        _require_float(value[0], context=f"{context}[0]"),
        _require_float(value[1], context=f"{context}[1]"),
    )


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


def _require_non_empty_float_sequence(value: object, *, context: str) -> tuple[float, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{context} must be a sequence of numbers")
    if len(value) == 0:
        raise ValueError(f"{context} must contain at least one entry")
    values: list[float] = []
    for index, raw_item in enumerate(value):
        values.append(_require_float(raw_item, context=f"{context}[{index}]"))
    return tuple(values)


def _require_float_triplet_sequence(
    value: object,
    *,
    context: str,
) -> tuple[tuple[float, float, float], ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{context} must be a sequence of 3D points")
    vertices: list[tuple[float, float, float]] = []
    for index, raw_vertex in enumerate(value):
        vertices.append(_require_float_triplet(raw_vertex, context=f"{context}[{index}]"))
    if len(vertices) != 4:
        raise ValueError(f"{context} must contain exactly 4 vertices")
    return tuple(vertices)


def _require_imported_object_names(imported_object_names: Sequence[str]) -> tuple[str, ...]:
    if isinstance(imported_object_names, (str, bytes)):
        raise TypeError("imported_object_names must be a sequence of strings, not str/bytes")
    names: list[str] = []
    for index, raw_name in enumerate(imported_object_names):
        if not isinstance(raw_name, str):
            raise TypeError(f"imported_object_names[{index}] must be str")
        if raw_name == "":
            raise ValueError(f"imported_object_names[{index}] must be non-empty")
        names.append(raw_name)
    if len(names) == 0:
        raise ValueError("imported_object_names must contain at least one object name")
    if len(names) != len(set(names)):
        raise ValueError(f"imported_object_names must be duplicate-free (actual={names})")
    return tuple(names)


def _require_terminal_outer_corner(value: object) -> Literal["A", "B", "C", "D"]:
    raw_value = _require_non_empty_str(value, context="modeled_object.terminal_metadata.outer_corner")
    if raw_value not in _OUTER_CORNERS:
        raise ValueError(
            "modeled_object.terminal_metadata.outer_corner must be one of ['A', 'B', 'C', 'D'] "
            f"(actual={raw_value!r})"
        )
    return cast(Literal["A", "B", "C", "D"], raw_value)


def _require_terminal_inner_corner(value: object) -> Literal["a", "b", "c", "d"]:
    raw_value = _require_non_empty_str(value, context="modeled_object.terminal_metadata.inner_corner")
    if raw_value not in _INNER_CORNERS:
        raise ValueError(
            "modeled_object.terminal_metadata.inner_corner must be one of ['a', 'b', 'c', 'd'] "
            f"(actual={raw_value!r})"
        )
    return cast(Literal["a", "b", "c", "d"], raw_value)


def _require_terminal_direction(value: object) -> Literal["cw", "ccw"]:
    raw_value = _require_non_empty_str(value, context="modeled_object.terminal_metadata.direction")
    if raw_value not in _PATH_DIRECTIONS:
        raise ValueError(
            "modeled_object.terminal_metadata.direction must be 'cw' or 'ccw' "
            f"(actual={raw_value!r})"
        )
    return cast(Literal["cw", "ccw"], raw_value)


def _parse_canonical_coordinates(value: object) -> ImportedModeledObjectCanonicalCoordinates:
    node = _require_table(value, context="modeled_object.canonical_coordinates")
    return {
        "frame_origin_xyz": _require_float_triplet(
            _require_key(node, key="frame_origin_xyz", context="modeled_object.canonical_coordinates"),
            context="modeled_object.canonical_coordinates.frame_origin_xyz",
        ),
        "outer_bounds_min_xyz": _require_float_triplet(
            _require_key(node, key="outer_bounds_min_xyz", context="modeled_object.canonical_coordinates"),
            context="modeled_object.canonical_coordinates.outer_bounds_min_xyz",
        ),
        "outer_bounds_max_xyz": _require_float_triplet(
            _require_key(node, key="outer_bounds_max_xyz", context="modeled_object.canonical_coordinates"),
            context="modeled_object.canonical_coordinates.outer_bounds_max_xyz",
        ),
        "outer_bounds_size_xyz": _require_float_triplet(
            _require_key(node, key="outer_bounds_size_xyz", context="modeled_object.canonical_coordinates"),
            context="modeled_object.canonical_coordinates.outer_bounds_size_xyz",
        ),
        "pcb_layer_z_positions_mm": _require_non_empty_float_sequence(
            _require_key(node, key="pcb_layer_z_positions_mm", context="modeled_object.canonical_coordinates"),
            context="modeled_object.canonical_coordinates.pcb_layer_z_positions_mm",
        ),
        "copper_layer_z_positions_mm": _require_non_empty_float_sequence(
            _require_key(node, key="copper_layer_z_positions_mm", context="modeled_object.canonical_coordinates"),
            context="modeled_object.canonical_coordinates.copper_layer_z_positions_mm",
        ),
    }


def _parse_terminal_metadata(value: object) -> ImportedModeledObjectTerminalMetadata:
    node = _require_table(value, context="modeled_object.terminal_metadata")
    terminal_metadata: dict[str, object] = {
        "path": _require_non_empty_str(
            _require_key(node, key="path", context="modeled_object.terminal_metadata"),
            context="modeled_object.terminal_metadata.path",
        ),
        "outer_corner": _require_terminal_outer_corner(
            _require_key(node, key="outer_corner", context="modeled_object.terminal_metadata")
        ),
        "inner_corner": _require_terminal_inner_corner(
            _require_key(node, key="inner_corner", context="modeled_object.terminal_metadata")
        ),
        "direction": _require_terminal_direction(
            _require_key(node, key="direction", context="modeled_object.terminal_metadata")
        ),
        "start_point_plane_mm": _require_float_pair(
            _require_key(node, key="start_point_plane_mm", context="modeled_object.terminal_metadata"),
            context="modeled_object.terminal_metadata.start_point_plane_mm",
        ),
        "end_point_plane_mm": _require_float_pair(
            _require_key(node, key="end_point_plane_mm", context="modeled_object.terminal_metadata"),
            context="modeled_object.terminal_metadata.end_point_plane_mm",
        ),
    }
    if "port_sheet_vertices_xyz" in node:
        terminal_metadata["port_sheet_vertices_xyz"] = _require_float_triplet_sequence(
            _require_key(node, key="port_sheet_vertices_xyz", context="modeled_object.terminal_metadata"),
            context="modeled_object.terminal_metadata.port_sheet_vertices_xyz",
        )
    return cast(ImportedModeledObjectTerminalMetadata, terminal_metadata)


def build_single_imported_modeled_object_entry(
    *,
    modeled_object: dict[str, object],
    imported_object_names: Sequence[str],
) -> ImportedModeledObjectEntry:
    role = _require_non_empty_str(
        _require_key(modeled_object, key="role", context="modeled_object"),
        context="modeled_object.role",
    )
    if role not in _SUPPORTED_ROLES:
        raise ValueError(
            "modeled_object.role must be one of ['tx_single_coil', 'rx_single_coil'] for single-coil import "
            f"(actual={role!r})"
        )
    plane = _require_non_empty_str(
        _require_key(modeled_object, key="plane", context="modeled_object"),
        context="modeled_object.plane",
    )
    if plane not in _SUPPORTED_PLANES:
        raise ValueError(f"modeled_object.plane must be one of ['XY', 'YZ'] (actual={plane!r})")
    placement_owner_id = _require_non_empty_str(
        _require_key(modeled_object, key="placement_owner_id", context="modeled_object"),
        context="modeled_object.placement_owner_id",
    )

    material = _require_non_empty_str(
        _require_key(modeled_object, key="material", context="modeled_object"),
        context="modeled_object.material",
    )
    model_state = _require_key(modeled_object, key="model_state", context="modeled_object")
    if not isinstance(model_state, bool):
        raise TypeError("modeled_object.model_state must be bool")
    if model_state is not True:
        raise ValueError("modeled_object.model_state must be true for modeled import adapter")

    object_id = _require_non_empty_str(
        _require_key(modeled_object, key="object_id", context="modeled_object"),
        context="modeled_object.object_id",
    )
    canonical_coordinates = _parse_canonical_coordinates(
        _require_key(modeled_object, key="canonical_coordinates", context="modeled_object")
    )
    terminal_metadata = _parse_terminal_metadata(
        _require_key(modeled_object, key="terminal_metadata", context="modeled_object")
    )
    validated_object_names = _require_imported_object_names(imported_object_names)

    return {
        "object_id": object_id,
        "role": cast(Literal["tx_single_coil", "rx_single_coil"], role),
        "plane": cast(Literal["XY", "YZ"], plane),
        "placement_owner_id": placement_owner_id,
        "material": material,
        "model_state": True,
        "canonical_coordinates": canonical_coordinates,
        "terminal_metadata": terminal_metadata,
        "imported_object_names": validated_object_names,
    }


__all__ = ["ImportedModeledObjectEntry", "build_single_imported_modeled_object_entry"]

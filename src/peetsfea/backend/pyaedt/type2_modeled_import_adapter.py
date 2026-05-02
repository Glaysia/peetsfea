from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypedDict, cast

_SUPPORTED_ROLES: frozenset[str] = frozenset(
    {
        "tx_single_coil",
        "tx_inner_single_coil",
        "tx_outer_single_coil",
        "rx_single_coil",
        "tx_plate_stack",
        "rx_plate_stack",
        "tx_rect_void_columns",
    }
)
_SUPPORTED_PLANES: frozenset[str] = frozenset({"XY", "YZ"})
_PLATE_STACK_ROLES: frozenset[str] = frozenset({"tx_plate_stack", "rx_plate_stack"})
_TX_RECT_VOID_COLUMNS_ROLE = "tx_rect_void_columns"
_OUTER_CORNERS: frozenset[str] = frozenset({"A", "B", "C", "D"})
_INNER_CORNERS: frozenset[str] = frozenset({"a", "b", "c", "d"})
_PATH_DIRECTIONS: frozenset[str] = frozenset({"cw", "ccw"})


class ImportedModeledObjectCanonicalCoordinatesRequired(TypedDict):
    frame_origin_xyz: tuple[float, float, float]
    outer_bounds_min_xyz: tuple[float, float, float]
    outer_bounds_max_xyz: tuple[float, float, float]
    outer_bounds_size_xyz: tuple[float, float, float]
    pcb_layer_z_positions_mm: tuple[float, ...]
    copper_layer_z_positions_mm: tuple[float, ...]


class ImportedModeledObjectCanonicalCoordinates(ImportedModeledObjectCanonicalCoordinatesRequired, total=False):
    # Present when the source emitter records rigid-tilt provenance for tx_outer_single_coil.
    outer_tilt_metadata: "ImportedTxOuterCanonicalTiltMetadata"


class ImportedTxOuterCanonicalTiltMetadata(TypedDict, total=False):
    # Maximum accepted protrusion beyond the outer region in world +X for rigid-tilt stack placement.
    max_world_x_protrusion_mm: float


class ImportedSingleCoilTerminalMetadataBase(TypedDict):
    path: str
    outer_corner: Literal["A", "B", "C", "D"]
    inner_corner: Literal["a", "b", "c", "d"]
    direction: Literal["cw", "ccw"]
    start_point_plane_mm: tuple[float, float]
    end_point_plane_mm: tuple[float, float]


class ImportedSingleCoilTerminalMetadata(ImportedSingleCoilTerminalMetadataBase, total=False):
    port_sheet_vertices_xyz: tuple[tuple[float, float, float], ...]


class ImportedPlateStackTerminalMetadata(TypedDict):
    kind: Literal["stub_port"]
    input_stub_body_name: str
    output_stub_body_name: str
    start_point_plane_mm: tuple[float, float]
    end_point_plane_mm: tuple[float, float]
    port_sheet_vertices_xyz: tuple[tuple[float, float, float], ...]


class ImportedTxRectVoidColumnsTabFace(TypedDict):
    terminal: Literal["start", "end"]
    vertices_xyz: tuple[tuple[float, float, float], ...]


class ImportedTxRectVoidColumnsTerminalMetadata(TypedDict, total=False):
    kind: Literal["parallel_collector_tabs", "series_collector_tabs"]
    connection_mode: int
    tab_face_vertices_xyz: tuple[ImportedTxRectVoidColumnsTabFace, ...]
    source_label_metadata: dict[str, object]
    branch_balance_audit: dict[str, object]
    overlap_audit: dict[str, object]
    layer_count: int
    x_column_count: int
    y_tile_count: int
    tile_order: tuple[tuple[int, int], ...]
    link_labels: tuple[str, ...]
    path_length_audit: dict[str, object]
    branch_count: int


class ImportedModeledObjectEntry(TypedDict):
    object_id: str
    role: Literal[
        "tx_single_coil",
        "tx_inner_single_coil",
        "tx_outer_single_coil",
        "rx_single_coil",
        "tx_plate_stack",
        "rx_plate_stack",
        "tx_rect_void_columns",
    ]
    plane: Literal["XY", "YZ"]
    placement_owner_id: str
    material: str
    model_state: Literal[True]
    canonical_coordinates: ImportedModeledObjectCanonicalCoordinates
    terminal_metadata: ImportedSingleCoilTerminalMetadata | ImportedPlateStackTerminalMetadata | ImportedTxRectVoidColumnsTerminalMetadata
    imported_object_names: tuple[str, ...]


def _require_positive_float_or_zero(value: object, *, context: str) -> float:
    checked_value = _require_float(value, context=context)
    if checked_value < 0:
        raise ValueError(f"{context} must be >= 0")
    return checked_value


def _parse_outer_tilt_metadata(value: object, *, context: str) -> ImportedTxOuterCanonicalTiltMetadata:
    node = _require_table(value, context=context)
    allowed_keys = ("max_world_x_protrusion_mm",)
    raw_keys = sorted(node.keys())
    if raw_keys != list(allowed_keys):
        raise ValueError(
            f"{context} must only expose keys {allowed_keys} "
            f"(actual={raw_keys})"
        )
    return {
        "max_world_x_protrusion_mm": _require_positive_float_or_zero(
            _require_key(node, key="max_world_x_protrusion_mm", context=context),
            context=f"{context}.max_world_x_protrusion_mm",
        )
    }


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
    parsed_coordinates: ImportedModeledObjectCanonicalCoordinates = {
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
    if "outer_tilt_metadata" in node:
        parsed_coordinates["outer_tilt_metadata"] = _parse_outer_tilt_metadata(
            node["outer_tilt_metadata"],
            context="modeled_object.canonical_coordinates.outer_tilt_metadata",
        )
    return parsed_coordinates


def _parse_single_coil_terminal_metadata(value: object) -> ImportedSingleCoilTerminalMetadata:
    node = _require_table(value, context="modeled_object.terminal_metadata")
    if "kind" in node:
        raw_kind = _require_non_empty_str(
            _require_key(node, key="kind", context="modeled_object.terminal_metadata"),
            context="modeled_object.terminal_metadata.kind",
        )
        raise ValueError(
            "modeled_object.terminal_metadata.kind is unsupported for coil import; "
            f"coil roles require explicit terminal geometry metadata (actual={raw_kind!r})"
        )
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
    return cast(ImportedSingleCoilTerminalMetadata, terminal_metadata)


def _parse_plate_stack_terminal_metadata(value: object, *, role: str) -> ImportedPlateStackTerminalMetadata:
    node = _require_table(value, context="modeled_object.terminal_metadata")
    kind = _require_non_empty_str(
        _require_key(node, key="kind", context="modeled_object.terminal_metadata"),
        context="modeled_object.terminal_metadata.kind",
    )
    if kind != "stub_port":
        raise ValueError(
            f"modeled_object.terminal_metadata.kind must be 'stub_port' for {role} geometry-only import "
            f"(actual={kind!r})"
        )
    expected_keys = {
        "kind",
        "input_stub_body_name",
        "output_stub_body_name",
        "start_point_plane_mm",
        "end_point_plane_mm",
        "port_sheet_vertices_xyz",
    }
    if set(node.keys()) != expected_keys:
        raise ValueError(
            "modeled_object.terminal_metadata must match the stub_port plate-stack import contract "
            f"(actual_keys={sorted(node)})"
        )
    input_stub_body_name = _require_non_empty_str(
        _require_key(node, key="input_stub_body_name", context="modeled_object.terminal_metadata"),
        context="modeled_object.terminal_metadata.input_stub_body_name",
    )
    output_stub_body_name = _require_non_empty_str(
        _require_key(node, key="output_stub_body_name", context="modeled_object.terminal_metadata"),
        context="modeled_object.terminal_metadata.output_stub_body_name",
    )
    if input_stub_body_name == output_stub_body_name:
        raise ValueError(
            "modeled_object.terminal_metadata input/output stub body names must differ "
            f"(actual={input_stub_body_name!r})"
        )
    return {
        "kind": "stub_port",
        "input_stub_body_name": input_stub_body_name,
        "output_stub_body_name": output_stub_body_name,
        "start_point_plane_mm": _require_float_pair(
            _require_key(node, key="start_point_plane_mm", context="modeled_object.terminal_metadata"),
            context="modeled_object.terminal_metadata.start_point_plane_mm",
        ),
        "end_point_plane_mm": _require_float_pair(
            _require_key(node, key="end_point_plane_mm", context="modeled_object.terminal_metadata"),
            context="modeled_object.terminal_metadata.end_point_plane_mm",
        ),
        "port_sheet_vertices_xyz": _require_float_triplet_sequence(
            _require_key(node, key="port_sheet_vertices_xyz", context="modeled_object.terminal_metadata"),
            context="modeled_object.terminal_metadata.port_sheet_vertices_xyz",
        ),
    }


def _parse_tx_rect_void_columns_terminal_metadata(value: object) -> ImportedTxRectVoidColumnsTerminalMetadata:
    node = _require_table(value, context="modeled_object.terminal_metadata")
    kind = _require_non_empty_str(
        _require_key(node, key="kind", context="modeled_object.terminal_metadata"),
        context="modeled_object.terminal_metadata.kind",
    )
    if kind not in ("parallel_collector_tabs", "series_collector_tabs"):
        raise ValueError(
            "modeled_object.terminal_metadata.kind must be 'parallel_collector_tabs' or 'series_collector_tabs' "
            f"for tx_rect_void_columns (actual={kind!r})"
        )
    raw_tab_faces = _require_key(
        node,
        key="tab_face_vertices_xyz",
        context="modeled_object.terminal_metadata",
    )
    if isinstance(raw_tab_faces, (str, bytes)) or not isinstance(raw_tab_faces, Sequence):
        raise TypeError("modeled_object.terminal_metadata.tab_face_vertices_xyz must be a sequence")
    tab_faces: list[ImportedTxRectVoidColumnsTabFace] = []
    seen_terminals: set[str] = set()
    for index, raw_tab_face in enumerate(raw_tab_faces):
        face_context = f"modeled_object.terminal_metadata.tab_face_vertices_xyz[{index}]"
        tab_face = _require_table(raw_tab_face, context=face_context)
        terminal = _require_non_empty_str(
            _require_key(tab_face, key="terminal", context=face_context),
            context=f"{face_context}.terminal",
        )
        if terminal not in ("start", "end"):
            raise ValueError(f"{face_context}.terminal must be 'start' or 'end' (actual={terminal!r})")
        if terminal in seen_terminals:
            raise ValueError(f"modeled_object.terminal_metadata.tab_face_vertices_xyz contains duplicate terminal {terminal!r}")
        seen_terminals.add(terminal)
        tab_faces.append(
            {
                "terminal": cast(Literal["start", "end"], terminal),
                "vertices_xyz": _require_float_triplet_sequence(
                    _require_key(tab_face, key="vertices_xyz", context=face_context),
                    context=f"{face_context}.vertices_xyz",
                ),
            }
        )
    if seen_terminals != {"start", "end"}:
        raise ValueError(
            "modeled_object.terminal_metadata.tab_face_vertices_xyz must contain start and end terminals "
            f"(actual={sorted(seen_terminals)})"
        )
    parsed = dict(node)
    parsed["kind"] = kind
    parsed["tab_face_vertices_xyz"] = tuple(tab_faces)
    return cast(ImportedTxRectVoidColumnsTerminalMetadata, parsed)


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
            "modeled_object.role must be one of ['tx_single_coil', 'tx_inner_single_coil', 'tx_outer_single_coil', 'rx_single_coil', 'tx_plate_stack', 'rx_plate_stack', 'tx_rect_void_columns'] "
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
    raw_terminal_metadata = _require_key(modeled_object, key="terminal_metadata", context="modeled_object")
    if role in _PLATE_STACK_ROLES:
        terminal_metadata = _parse_plate_stack_terminal_metadata(raw_terminal_metadata, role=role)
    elif role == _TX_RECT_VOID_COLUMNS_ROLE:
        terminal_metadata = _parse_tx_rect_void_columns_terminal_metadata(raw_terminal_metadata)
    else:
        terminal_metadata = _parse_single_coil_terminal_metadata(raw_terminal_metadata)
    validated_object_names = _require_imported_object_names(imported_object_names)

    return {
        "object_id": object_id,
        "role": cast(
            Literal[
                "tx_single_coil",
                "tx_inner_single_coil",
                "tx_outer_single_coil",
                "rx_single_coil",
                "tx_plate_stack",
                "rx_plate_stack",
                "tx_rect_void_columns",
            ],
            role,
        ),
        "plane": cast(Literal["XY", "YZ"], plane),
        "placement_owner_id": placement_owner_id,
        "material": material,
        "model_state": True,
        "canonical_coordinates": canonical_coordinates,
        "terminal_metadata": terminal_metadata,
        "imported_object_names": validated_object_names,
    }


__all__ = ["ImportedModeledObjectEntry", "build_single_imported_modeled_object_entry"]

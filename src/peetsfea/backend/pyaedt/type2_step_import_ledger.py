from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, TypedDict, cast

from peetsfea.aedt.failfast import validate_aedt_name
from peetsfea.spec.outputs import parse_outputs_table
from peetsfea.types.manifest import OutputsSpec

_SUPPORTED_MODELED_ROLES: frozenset[str] = frozenset(
    {
        "tx_single_coil",
        "tx_inner_single_coil",
        "rx_single_coil",
        "tx_plate_stack",
        "rx_plate_stack",
        "tx_rect_void_columns",
        "tv_aluminum_plate",
    }
)
_SUPPORTED_MODELED_PLANES: frozenset[str] = frozenset({"XY", "YZ"})
_PLATE_STACK_ROLES: frozenset[str] = frozenset({"tx_plate_stack", "rx_plate_stack"})
_SUPPORTED_SCHEMA_VERSION = "type2.step_ledger.v3"
_TX_RECT_VOID_COLUMNS_ROLE = "tx_rect_void_columns"
_TV_ALUMINUM_PLATE_ROLE = "tv_aluminum_plate"
_TX_COPPER_GROUP_NAME = "g_copper_tx"
_RX_COPPER_GROUP_NAME = "g_copper_rx"
_TX_FERRITE_GROUP_NAME = "g_ferrite_tx"
_TX_OUTER_FERRITE_GROUP_NAME = "g_ferrite_tx_outer"
_RX_FERRITE_GROUP_NAME = "g_ferrite_rx"
_TX_PLATE_COPPER_NAME = "tx_plate_copper"
_RX_PLATE_COPPER_NAME = "rx_plate_copper"
_TX_MERGED_STACK_PET_PSA_NAME = "tx_stack_pet_psa"
_TX_MERGED_STACK_FERRITE_NAME = "tx_stack_ferrite"
_TX_MERGED_STACK_AIR_NAME = "tx_stack_air"
_RX_MERGED_STACK_PET_PSA_NAME = "rx_stack_pet_psa"
_RX_MERGED_STACK_FERRITE_NAME = "rx_stack_ferrite"
_RX_MERGED_STACK_AIR_NAME = "rx_stack_air"
_TX_MERGED_STACK_MEMBER_NAMES: tuple[str, ...] = (
    _TX_MERGED_STACK_PET_PSA_NAME,
    _TX_MERGED_STACK_FERRITE_NAME,
    _TX_MERGED_STACK_AIR_NAME,
)
_RX_MERGED_STACK_MEMBER_NAMES: tuple[str, ...] = (
    _RX_MERGED_STACK_PET_PSA_NAME,
    _RX_MERGED_STACK_FERRITE_NAME,
    _RX_MERGED_STACK_AIR_NAME,
)
_TX_FERRITE_GROUP_MEMBER_PREFIXES: tuple[str, ...] = (
    "tx_underlay_ferrite_u",
    "tx_underlay_pet_psa_u",
    "tx_underlay_air_u",
    "tx_wall_ferrite_u",
    "tx_wall_pet_psa_u",
    "tx_wall_air_u",
)
_TX_INNER_FERRITE_GROUP_MEMBER_PREFIXES: tuple[str, ...] = (
    "tx_underlay_pet_psa_u",
    "tx_underlay_ferrite_u",
    "tx_void_ferrite_u",
    "tx_void_pet_psa_u",
)
_TX_OUTER_FERRITE_GROUP_MEMBER_PREFIXES: tuple[str, ...] = (
    "tx_outer_void_ferrite_u",
    "tx_outer_void_pet_psa_u",
    "tx_outer_underlay_ferrite_u",
    "tx_outer_underlay_pet_psa_u",
)
_RX_FERRITE_GROUP_MEMBER_PREFIXES: tuple[str, ...] = (
    "under_rx_ferrite_u",
    "under_rx_pet_psa_u",
    "under_rx_air_u",
)
_LEGACY_PLATE_STACK_COPPER_NAME_PREFIXES: tuple[str, ...] = (
    "tx_copper_wall_t",
    "tx_copper_coil_t",
    "tx_bridge_s",
    "tx_stub_",
    "rx_copper_wall_t",
    "rx_copper_coil_t",
    "rx_bridge_s",
    "rx_stub_",
)


def _is_legacy_plate_stack_copper_segment_name(name: str) -> bool:
    return name.startswith(_LEGACY_PLATE_STACK_COPPER_NAME_PREFIXES)


def _is_tx_ferrite_family_name(name: str) -> bool:
    if name in _TX_MERGED_STACK_MEMBER_NAMES:
        return True
    if _is_tx_branch_stack_member(name, suffix="_stack_ferrite"):
        return True
    if _is_tx_branch_stack_member(name, suffix="_stack_pet_psa"):
        return True
    if _is_tx_branch_stack_member(name, suffix="_stack_air"):
        return True
    return name.startswith(_TX_FERRITE_GROUP_MEMBER_PREFIXES) or name.startswith(
        _TX_OUTER_FERRITE_GROUP_MEMBER_PREFIXES
    )


def _is_rx_ferrite_family_name(name: str) -> bool:
    if name in _RX_MERGED_STACK_MEMBER_NAMES:
        return True
    return name.startswith(_RX_FERRITE_GROUP_MEMBER_PREFIXES)


def _is_tx_branch_stack_member(name: str, *, suffix: str) -> bool:
    if not name.startswith("tx_b") or not name.endswith(suffix):
        return False
    middle = name[len("tx_b") : -len(suffix)]
    return middle.isdigit()


def _is_tx_array_connector_sheet_name(name: str) -> bool:
    for prefix in ("tx_array_input_sheet_s", "tx_array_output_sheet_s"):
        if not name.startswith(prefix):
            continue
        suffix = name[len(prefix):]
        return suffix.isdigit()
    return False


def _is_tx_array_copper_name(name: str) -> bool:
    return _is_tx_branch_stack_member(name, suffix="_plate_copper") or _is_tx_array_connector_sheet_name(name)


def _is_tx_pre_unite_plate_stack_copper_name(name: str) -> bool:
    return _is_tx_array_copper_name(name)

_NON_MODEL_REQUIRED_FIELDS = (
    "object_id",
    "role",
    "material",
    "model_state",
    "canonical_coordinates",
    "plane",
    "non_model",
)
_MODELED_REQUIRED_FIELDS = (
    "object_id",
    "role",
    "plane",
    "placement_owner_id",
    "material",
    "model_state",
    "expected_exported_body_names",
    "expected_exported_body_count",
    "expected_exported_body_groups",
    "canonical_coordinates",
    "exported_body_canonical_coordinates",
    "terminal_metadata",
    "source_metadata_path",
)


class ValidatedStepEntry(TypedDict):
    object_id: str
    entry: dict[str, object]


class ValidatedStepLedger(TypedDict):
    schema_version: Literal["type2.step_ledger.v3"]
    source_toml_path: str
    source_toml_sha256: str
    scene_step_path: Path
    scene_step_sha256: str
    seed: int
    em_policy: "Type2ImportEmPolicy"
    outputs: OutputsSpec
    non_model_objects: list[ValidatedStepEntry]
    modeled_objects: list[ValidatedStepEntry]


class Type2ImportEmPolicy(TypedDict):
    radiation_margin_mm: float


def require_key(table: dict[str, object], *, key: str, context: str) -> object:
    if key not in table:
        raise ValueError(f"{context} is missing required key '{key}'")
    return table[key]


def _require_table(value: object, *, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be an object/table")
    return cast(dict[str, object], value)


def require_non_empty_str(value: object, *, context: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{context} must be str")
    if value == "":
        raise ValueError(f"{context} must be non-empty")
    return value


def require_int(value: object, *, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{context} must be int")
    return value


def require_sheet_present(value: object, *, context: str) -> int:
    sheet_present = require_int(value, context=context)
    if sheet_present not in (0, 1):
        raise ValueError(f"{context} must be 0 or 1 (actual={sheet_present})")
    return sheet_present


def _require_float(value: object, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{context} must be number")
    return float(value)


def _require_bool(value: object, *, context: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{context} must be bool")
    return value


def _require_positive_float(value: object, *, context: str) -> float:
    checked_value = _require_float(value, context=context)
    if checked_value <= 0.0:
        raise ValueError(f"{context} must be > 0")
    return checked_value


def _require_non_negative_float(value: object, *, context: str) -> float:
    checked_value = _require_float(value, context=context)
    if checked_value < 0.0:
        raise ValueError(f"{context} must be >= 0")
    return checked_value


def _require_entry_list(value: object, *, context: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise TypeError(f"{context} must be a list")
    entries: list[dict[str, object]] = []
    for index, raw_entry in enumerate(value):
        entries.append(_require_table(raw_entry, context=f"{context}[{index}]"))
    return entries


def _require_existing_file_from_text(raw_path: object, *, context: str, ledger_dir: Path) -> Path:
    path_text = require_non_empty_str(raw_path, context=context)
    candidate_path = Path(path_text)
    if not candidate_path.is_absolute():
        candidate_path = ledger_dir / candidate_path
    resolved_path = candidate_path.resolve(strict=False)
    if not resolved_path.is_file():
        raise FileNotFoundError(f"{context} does not exist: {resolved_path}")
    return resolved_path


def _sha256_hex_digest(path: Path, *, context: str) -> str:
    assert path.is_file(), f"{context} must resolve to a file path (actual={path!r})"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_float_triplet(value: object, *, context: str) -> tuple[float, float, float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{context} must be a sequence of length 3")
    if len(value) != 3:
        raise ValueError(f"{context} must contain exactly 3 entries")
    return (
        _require_float(value[0], context=f"{context}[0]"),
        _require_float(value[1], context=f"{context}[1]"),
        _require_float(value[2], context=f"{context}[2]"),
    )


def _require_float_pair(value: object, *, context: str) -> tuple[float, float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{context} must be a sequence of length 2")
    if len(value) != 2:
        raise ValueError(f"{context} must contain exactly 2 entries")
    return (
        _require_float(value[0], context=f"{context}[0]"),
        _require_float(value[1], context=f"{context}[1]"),
    )


def _require_float_triplet_sequence(
    value: object,
    *,
    context: str,
) -> tuple[tuple[float, float, float], ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{context} must be a sequence of 3D points")
    vertices: list[tuple[float, float, float]] = []
    for index, raw_vertex in enumerate(value):
        vertices.append(require_float_triplet(raw_vertex, context=f"{context}[{index}]"))
    if len(vertices) != 4:
        raise ValueError(f"{context} must contain exactly 4 vertices")
    return tuple(vertices)


def _require_required_fields(entry: dict[str, object], *, fields: tuple[str, ...], context: str) -> None:
    for field_name in fields:
        if field_name not in entry:
            raise ValueError(f"{context} is missing required key '{field_name}'")


def _validated_em_policy(raw_policy: object, *, context: str) -> Type2ImportEmPolicy:
    policy = _require_table(raw_policy, context=context)
    radiation_margin_mm = _require_positive_float(
        require_key(policy, key="radiation_margin_mm", context=context),
        context=f"{context}.radiation_margin_mm",
    )
    return {"radiation_margin_mm": radiation_margin_mm}


def _validated_canonical_coordinates(raw_coordinates: object, *, context: str) -> dict[str, object]:
    coordinates = _require_table(raw_coordinates, context=context)
    require_float_triplet(
        require_key(coordinates, key="frame_origin_xyz", context=context),
        context=f"{context}.frame_origin_xyz",
    )
    min_xyz = require_float_triplet(
        require_key(coordinates, key="outer_bounds_min_xyz", context=context),
        context=f"{context}.outer_bounds_min_xyz",
    )
    max_xyz = require_float_triplet(
        require_key(coordinates, key="outer_bounds_max_xyz", context=context),
        context=f"{context}.outer_bounds_max_xyz",
    )
    size_xyz = require_float_triplet(
        require_key(coordinates, key="outer_bounds_size_xyz", context=context),
        context=f"{context}.outer_bounds_size_xyz",
    )
    for axis_index in (0, 1, 2):
        if max_xyz[axis_index] < min_xyz[axis_index]:
            raise ValueError(f"{context}.outer_bounds_max_xyz must be >= outer_bounds_min_xyz on every axis")
        computed_size = max_xyz[axis_index] - min_xyz[axis_index]
        if abs(computed_size - size_xyz[axis_index]) > 1e-9:
            raise ValueError(
                f"{context}.outer_bounds_size_xyz must equal max-min on every axis "
                f"(axis_index={axis_index}, min={min_xyz}, max={max_xyz}, size={size_xyz})"
            )
    return coordinates


def _validated_plate_stack_terminal_metadata(
    raw_terminal_metadata: object,
    *,
    role: str,
    context: str,
) -> None:
    terminal_metadata = _require_table(raw_terminal_metadata, context=f"{context}.terminal_metadata")
    raw_kind = require_key(
        terminal_metadata,
        key="kind",
        context=f"{context}.terminal_metadata",
    )
    kind = require_non_empty_str(raw_kind, context=f"{context}.terminal_metadata.kind")
    if kind != "stub_port":
        raise ValueError(
            f"{context}.terminal_metadata.kind must be 'stub_port' for {role} import-only geometry metadata "
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
    if set(terminal_metadata) != expected_keys:
        raise ValueError(
            f"{context}.terminal_metadata must match the stub_port plate-stack import contract for {role} "
            f"(actual_keys={sorted(terminal_metadata)})"
        )
    input_stub_body_name = require_non_empty_str(
        require_key(terminal_metadata, key="input_stub_body_name", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.input_stub_body_name",
    )
    output_stub_body_name = require_non_empty_str(
        require_key(terminal_metadata, key="output_stub_body_name", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.output_stub_body_name",
    )
    if input_stub_body_name == output_stub_body_name:
        raise ValueError(
            f"{context}.terminal_metadata input/output stub body names must differ "
            f"(actual={input_stub_body_name!r})"
        )
    _require_float_pair(
        require_key(terminal_metadata, key="start_point_plane_mm", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.start_point_plane_mm",
    )
    _require_float_pair(
        require_key(terminal_metadata, key="end_point_plane_mm", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.end_point_plane_mm",
    )
    _require_float_triplet_sequence(
        require_key(terminal_metadata, key="port_sheet_vertices_xyz", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.port_sheet_vertices_xyz",
    )


def _validated_single_coil_terminal_metadata(
    raw_terminal_metadata: object,
    *,
    context: str,
) -> None:
    terminal_metadata = _require_table(raw_terminal_metadata, context=f"{context}.terminal_metadata")
    if "kind" not in terminal_metadata:
        raise ValueError(
            f"{context}.terminal_metadata.kind must be 'single_coil_port_v1' for coil import "
            "(actual=None)"
        )
    kind = require_non_empty_str(
        terminal_metadata["kind"],
        context=f"{context}.terminal_metadata.kind",
    )
    if kind != "single_coil_port_v1":
        raise ValueError(
            f"{context}.terminal_metadata.kind must be 'single_coil_port_v1' for coil import (actual={kind!r})"
        )
    allowed_keys = {
        "kind",
        "sheet_name",
        "vertices_xyz",
        "integration_line_start_xyz",
        "integration_line_end_xyz",
        "path",
        "outer_corner",
        "inner_corner",
        "direction",
    }
    extra_keys = sorted(set(terminal_metadata) - allowed_keys)
    if extra_keys:
        raise ValueError(
            f"{context}.terminal_metadata contains unsupported single_coil_port_v1 keys "
            f"(actual={extra_keys})"
        )
    require_non_empty_str(
        require_key(terminal_metadata, key="sheet_name", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.sheet_name",
    )
    _require_float_triplet_sequence(
        require_key(terminal_metadata, key="vertices_xyz", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.vertices_xyz",
    )
    require_float_triplet(
        require_key(terminal_metadata, key="integration_line_start_xyz", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.integration_line_start_xyz",
    )
    require_float_triplet(
        require_key(terminal_metadata, key="integration_line_end_xyz", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.integration_line_end_xyz",
    )
    if "path" in terminal_metadata:
        require_non_empty_str(
            require_key(terminal_metadata, key="path", context=f"{context}.terminal_metadata"),
            context=f"{context}.terminal_metadata.path",
        )
    if "outer_corner" in terminal_metadata:
        outer_corner = require_non_empty_str(
            require_key(terminal_metadata, key="outer_corner", context=f"{context}.terminal_metadata"),
            context=f"{context}.terminal_metadata.outer_corner",
        )
        if outer_corner not in ("A", "B", "C", "D"):
            raise ValueError(
                f"{context}.terminal_metadata.outer_corner must be one of ['A', 'B', 'C', 'D'] (actual={outer_corner!r})"
            )
    if "inner_corner" in terminal_metadata:
        inner_corner = require_non_empty_str(
            require_key(terminal_metadata, key="inner_corner", context=f"{context}.terminal_metadata"),
            context=f"{context}.terminal_metadata.inner_corner",
        )
        if inner_corner not in ("a", "b", "c", "d"):
            raise ValueError(
                f"{context}.terminal_metadata.inner_corner must be one of ['a', 'b', 'c', 'd'] "
                f"(actual={inner_corner!r})"
            )
    if "direction" in terminal_metadata:
        direction = require_non_empty_str(
            require_key(terminal_metadata, key="direction", context=f"{context}.terminal_metadata"),
            context=f"{context}.terminal_metadata.direction",
        )
        if direction not in ("cw", "ccw"):
            raise ValueError(
                f"{context}.terminal_metadata.direction must be 'cw' or 'ccw' (actual={direction!r})"
            )


def _validated_outer_tilt_metadata(
    raw_outer_tilt_metadata: object,
    *,
    context: str,
) -> None:
    outer_tilt_metadata = _require_table(raw_outer_tilt_metadata, context=context)
    expected_keys = {"max_world_x_protrusion_mm", "max_world_z_underhang_mm"}
    if set(outer_tilt_metadata) != expected_keys:
        raise ValueError(
            f"{context} must match tx outer canonical tilt metadata contract "
            f"(actual_keys={sorted(outer_tilt_metadata)})"
        )
    _require_non_negative_float(
        require_key(outer_tilt_metadata, key="max_world_x_protrusion_mm", context=context),
        context=f"{context}.max_world_x_protrusion_mm",
    )
    _require_non_negative_float(
        require_key(outer_tilt_metadata, key="max_world_z_underhang_mm", context=context),
        context=f"{context}.max_world_z_underhang_mm",
    )


def _validated_tx_rect_void_columns_terminal_metadata(
    raw_terminal_metadata: object,
    *,
    context: str,
) -> None:
    terminal_metadata = _require_table(raw_terminal_metadata, context=f"{context}.terminal_metadata")
    kind = require_non_empty_str(
        require_key(terminal_metadata, key="kind", context=f"{context}.terminal_metadata"),
        context=f"{context}.terminal_metadata.kind",
    )
    if kind not in ("parallel_collector_tabs", "series_collector_tabs"):
        raise ValueError(
            f"{context}.terminal_metadata.kind must be 'parallel_collector_tabs' or 'series_collector_tabs' "
            f"for tx_rect_void_columns (actual={kind!r})"
        )
    raw_tab_faces = require_key(
        terminal_metadata,
        key="tab_face_vertices_xyz",
        context=f"{context}.terminal_metadata",
    )
    tab_face_entries = _require_entry_list(
        raw_tab_faces,
        context=f"{context}.terminal_metadata.tab_face_vertices_xyz",
    )
    if len(tab_face_entries) != 2:
        raise ValueError(
            f"{context}.terminal_metadata.tab_face_vertices_xyz must contain exactly two terminal tab faces "
            f"(actual={len(tab_face_entries)})"
        )
    seen_terminals: set[str] = set()
    for index, tab_face_entry in enumerate(tab_face_entries):
        face_context = f"{context}.terminal_metadata.tab_face_vertices_xyz[{index}]"
        terminal = require_non_empty_str(
            require_key(tab_face_entry, key="terminal", context=face_context),
            context=f"{face_context}.terminal",
        )
        if terminal not in ("start", "end"):
            raise ValueError(f"{face_context}.terminal must be 'start' or 'end' (actual={terminal!r})")
        if terminal in seen_terminals:
            raise ValueError(f"{context}.terminal_metadata.tab_face_vertices_xyz contains duplicate terminal {terminal!r}")
        seen_terminals.add(terminal)
        _require_float_triplet_sequence(
            require_key(tab_face_entry, key="vertices_xyz", context=face_context),
            context=f"{face_context}.vertices_xyz",
        )
    if seen_terminals != {"start", "end"}:
        raise ValueError(
            f"{context}.terminal_metadata.tab_face_vertices_xyz must contain start and end terminals "
            f"(actual={sorted(seen_terminals)})"
        )


def _validated_exported_body_groups(
    raw_groups: object,
    *,
    context: str,
) -> list[dict[str, object]]:
    groups = _require_entry_list(raw_groups, context=context)
    validated_groups: list[dict[str, object]] = []
    seen_group_names: set[str] = set()
    seen_member_names: set[str] = set()
    for group_index, raw_group in enumerate(groups):
        group_context = f"{context}[{group_index}]"
        group_name = require_non_empty_str(
            require_key(raw_group, key="group_name", context=group_context),
            context=f"{group_context}.group_name",
        )
        validate_aedt_name(group_name, field=f"{group_context}.group_name")
        if group_name in seen_group_names:
            raise ValueError(f"duplicate modeled exported body group name in STEP ledger: {group_name}")
        seen_group_names.add(group_name)
        member_body_names = validated_object_names(
            cast(
                Sequence[object],
                require_key(raw_group, key="member_body_names", context=group_context),
            ),
            context=f"{group_context}.member_body_names",
        )
        for member_body_name in member_body_names:
            if member_body_name in seen_member_names:
                raise ValueError(f"duplicate modeled exported body group member in STEP ledger: {member_body_name}")
            seen_member_names.add(member_body_name)
        validated_groups.append(
            {
                "group_name": group_name,
                "member_body_names": member_body_names,
            }
        )
    return validated_groups


def _ferrite_group_contract_for_role(
    *,
    role: str,
    expected_exported_body_names: list[str],
    context: str,
) -> tuple[str, list[str]]:
    expected_group_name: str
    ferrite_group_members: list[str]
    mismatched_role_members: list[str]
    if role == "tx_plate_stack":
        expected_group_name = _TX_FERRITE_GROUP_NAME
        ferrite_group_members = [
            name
            for name in expected_exported_body_names
            if name in _TX_MERGED_STACK_MEMBER_NAMES
            or _is_tx_branch_stack_member(name, suffix="_stack_ferrite")
            or _is_tx_branch_stack_member(name, suffix="_stack_pet_psa")
            or _is_tx_branch_stack_member(name, suffix="_stack_air")
        ]
        mismatched_role_members = [
            name
            for name in expected_exported_body_names
            if _is_rx_ferrite_family_name(name)
            or (
                _is_tx_ferrite_family_name(name)
                and name not in _TX_MERGED_STACK_MEMBER_NAMES
                and not _is_tx_branch_stack_member(name, suffix="_stack_ferrite")
                and not _is_tx_branch_stack_member(name, suffix="_stack_pet_psa")
                and not _is_tx_branch_stack_member(name, suffix="_stack_air")
            )
        ]
    elif role == "rx_plate_stack":
        expected_group_name = _RX_FERRITE_GROUP_NAME
        ferrite_group_members = [name for name in expected_exported_body_names if name in _RX_MERGED_STACK_MEMBER_NAMES]
        mismatched_role_members = [
            name
            for name in expected_exported_body_names
            if _is_tx_ferrite_family_name(name)
            or (_is_rx_ferrite_family_name(name) and name not in _RX_MERGED_STACK_MEMBER_NAMES)
        ]
    elif role == "tx_inner_single_coil":
        expected_group_name = _TX_FERRITE_GROUP_NAME
        ferrite_group_members = [
            name for name in expected_exported_body_names if name.startswith(_TX_INNER_FERRITE_GROUP_MEMBER_PREFIXES)
        ]
        mismatched_role_members = [name for name in expected_exported_body_names if _is_rx_ferrite_family_name(name)]
    elif role == "tx_outer_single_coil":
        expected_group_name = _TX_OUTER_FERRITE_GROUP_NAME
        ferrite_group_members = [
            name
            for name in expected_exported_body_names
            if name.startswith(_TX_OUTER_FERRITE_GROUP_MEMBER_PREFIXES)
        ]
        mismatched_role_members = [
            name
            for name in expected_exported_body_names
            if _is_rx_ferrite_family_name(name)
            or (
                _is_tx_ferrite_family_name(name)
                and not name.startswith(_TX_OUTER_FERRITE_GROUP_MEMBER_PREFIXES)
            )
        ]
    elif role.startswith("tx_"):
        expected_group_name = _TX_FERRITE_GROUP_NAME
        ferrite_group_members = [name for name in expected_exported_body_names if name.startswith(_TX_FERRITE_GROUP_MEMBER_PREFIXES)]
        mismatched_role_members = [
            name
            for name in expected_exported_body_names
            if _is_rx_ferrite_family_name(name)
            or (
                _is_tx_ferrite_family_name(name)
                and not name.startswith(_TX_FERRITE_GROUP_MEMBER_PREFIXES)
            )
        ]
    elif role.startswith("rx_"):
        expected_group_name = _RX_FERRITE_GROUP_NAME
        ferrite_group_members = [name for name in expected_exported_body_names if name.startswith(_RX_FERRITE_GROUP_MEMBER_PREFIXES)]
        mismatched_role_members = [name for name in expected_exported_body_names if _is_tx_ferrite_family_name(name)]
    else:
        raise ValueError(f"{context}.role is unsupported for ferrite group validation (actual={role!r})")
    if role == "tx_plate_stack":
        ferrite_count = len([name for name in ferrite_group_members if _is_tx_ferrite_family_name(name) and (name.endswith("_stack_ferrite"))])
        pet_psa_count = len([name for name in ferrite_group_members if _is_tx_ferrite_family_name(name) and (name.endswith("_stack_pet_psa"))])
        air_count = len([name for name in ferrite_group_members if _is_tx_ferrite_family_name(name) and (name.endswith("_stack_air"))])
        if ferrite_count < 1 or pet_psa_count < 1 or air_count < 1:
            raise ValueError(
                f"{context}.expected_exported_body_names must include tx plate-stack ferrite-family members "
                f"(ferrite={ferrite_count}, pet_psa={pet_psa_count}, air={air_count})"
            )
        if ferrite_count != pet_psa_count or ferrite_count != air_count:
            raise ValueError(
                f"{context}.expected_exported_body_names must include balanced tx branch ferrite-family members "
                f"(ferrite={ferrite_count}, pet_psa={pet_psa_count}, air={air_count})"
            )
    if role == "rx_plate_stack":
        missing_rx_merged_member_names = [
            name for name in _RX_MERGED_STACK_MEMBER_NAMES if name not in expected_exported_body_names
        ]
        if missing_rx_merged_member_names:
            raise ValueError(
                f"{context}.expected_exported_body_names must include all merged rx plate-stack ferrite members "
                f"(missing={missing_rx_merged_member_names})"
            )
    if mismatched_role_members:
        raise ValueError(
            f"{context}.expected_exported_body_names contains ferrite family bodies that do not match {role} "
            f"(mismatched={mismatched_role_members})"
        )
    return (expected_group_name, ferrite_group_members)


def _group_contract_for_role(
    *,
    role: str,
    expected_exported_body_names: list[str],
    context: str,
) -> list[tuple[str, list[str]]]:
    ferrite_group_name, ferrite_group_members = _ferrite_group_contract_for_role(
        role=role,
        expected_exported_body_names=expected_exported_body_names,
        context=context,
    )
    if role == "tx_plate_stack":
        if _TX_PLATE_COPPER_NAME not in expected_exported_body_names:
            raise ValueError(
                f"{context}.expected_exported_body_names must include tx plate-stack copper members"
            )
        copper_group_members = [_TX_PLATE_COPPER_NAME]
        pre_unite_copper_names = [
            name for name in expected_exported_body_names if _is_tx_pre_unite_plate_stack_copper_name(name)
        ]
        if pre_unite_copper_names:
            raise ValueError(
                f"{context}.expected_exported_body_names contains pre-unite tx copper leakage "
                f"(leaked_names={pre_unite_copper_names})"
            )
        legacy_segment_names = [
            name for name in expected_exported_body_names if _is_legacy_plate_stack_copper_segment_name(name)
        ]
        if legacy_segment_names:
            raise ValueError(
                f"{context}.expected_exported_body_names contains legacy plate-stack copper segment names "
                f"(legacy_names={legacy_segment_names})"
            )
        return [
            (_TX_COPPER_GROUP_NAME, copper_group_members),
            (ferrite_group_name, ferrite_group_members),
        ]
    if role == "rx_plate_stack":
        if _RX_PLATE_COPPER_NAME not in expected_exported_body_names:
            raise ValueError(
                f"{context}.expected_exported_body_names must include {_RX_PLATE_COPPER_NAME!r} for rx_plate_stack"
            )
        legacy_segment_names = [
            name for name in expected_exported_body_names if _is_legacy_plate_stack_copper_segment_name(name)
        ]
        if legacy_segment_names:
            raise ValueError(
                f"{context}.expected_exported_body_names contains legacy plate-stack copper segment names "
                f"(legacy_names={legacy_segment_names})"
            )
        return [
            (_RX_COPPER_GROUP_NAME, [_RX_PLATE_COPPER_NAME]),
            (ferrite_group_name, ferrite_group_members),
        ]
    if len(ferrite_group_members) == 0:
        return []
    return [(ferrite_group_name, ferrite_group_members)]


def _validate_modeled_ferrite_group_contract(
    *,
    role: str,
    expected_exported_body_names: list[str],
    validated_groups: list[dict[str, object]],
    context: str,
) -> None:
    if role == _TV_ALUMINUM_PLATE_ROLE:
        if expected_exported_body_names:
            raise ValueError(
                f"{context}.expected_exported_body_names must be [] "
                f"for {_TV_ALUMINUM_PLATE_ROLE} (actual={expected_exported_body_names})"
            )
        if len(validated_groups) != 0:
            raise ValueError(
                f"{context}.expected_exported_body_groups must be empty for {_TV_ALUMINUM_PLATE_ROLE} "
                f"(actual_groups={len(validated_groups)})"
            )
        return
    expected_group_contract = _group_contract_for_role(
        role=role,
        expected_exported_body_names=expected_exported_body_names,
        context=context,
    )
    if len(validated_groups) != len(expected_group_contract):
        raise ValueError(
            f"{context}.expected_exported_body_groups must match required role group contract "
            f"(role={role}, expected_groups={len(expected_group_contract)}, actual_groups={len(validated_groups)})"
        )
    for index, (expected_group_name, expected_member_names) in enumerate(expected_group_contract):
        validated_group = validated_groups[index]
        actual_group_name = cast(str, validated_group["group_name"])
        if actual_group_name != expected_group_name:
            raise ValueError(
                f"{context}.expected_exported_body_groups[{index}].group_name must be {expected_group_name!r} "
                f"(actual={actual_group_name!r})"
            )
        actual_member_names = cast(list[str], validated_group["member_body_names"])
        if actual_member_names != expected_member_names:
            raise ValueError(
                f"{context}.expected_exported_body_groups[{index}].member_body_names must match role contract "
                "in expected_exported_body_names order "
                f"(expected={expected_member_names}, actual={actual_member_names})"
            )


def validated_object_names(raw_names: Sequence[object], *, context: str) -> list[str]:
    if isinstance(raw_names, (str, bytes)):
        raise TypeError(f"{context}.object_names must be a sequence of strings, not str/bytes")
    names: list[str] = []
    for index, raw_name in enumerate(raw_names):
        if not isinstance(raw_name, str):
            raise TypeError(f"{context}.object_names[{index}] must be str")
        if raw_name == "":
            raise ValueError(f"{context}.object_names[{index}] must be non-empty")
        validate_aedt_name(raw_name, field=f"{context}.object_names[{index}]")
        names.append(raw_name)
    return names


def _validated_non_model_entry(
    entry: dict[str, object],
    *,
    index: int,
) -> ValidatedStepEntry:
    context = f"non_model_objects[{index}]"
    _require_required_fields(entry, fields=_NON_MODEL_REQUIRED_FIELDS, context=context)
    object_id = require_non_empty_str(require_key(entry, key="object_id", context=context), context=f"{context}.object_id")
    require_non_empty_str(require_key(entry, key="role", context=context), context=f"{context}.role")
    require_non_empty_str(require_key(entry, key="material", context=context), context=f"{context}.material")
    if _require_bool(require_key(entry, key="model_state", context=context), context=f"{context}.model_state") is not False:
        raise ValueError(f"{context}.model_state must be false")
    if _require_bool(require_key(entry, key="non_model", context=context), context=f"{context}.non_model") is not True:
        raise ValueError(f"{context}.non_model must be true")
    _validated_canonical_coordinates(
        require_key(entry, key="canonical_coordinates", context=context),
        context=f"{context}.canonical_coordinates",
    )
    require_non_empty_str(require_key(entry, key="plane", context=context), context=f"{context}.plane")
    _require_entry_list(require_key(entry, key="member_objects", context=context), context=f"{context}.member_objects")
    return {"object_id": object_id, "entry": entry}


def _validated_modeled_entry(
    entry: dict[str, object],
    *,
    index: int,
) -> ValidatedStepEntry:
    context = f"modeled_objects[{index}]"
    _require_required_fields(entry, fields=_MODELED_REQUIRED_FIELDS, context=context)
    object_id = require_non_empty_str(require_key(entry, key="object_id", context=context), context=f"{context}.object_id")
    role = require_non_empty_str(require_key(entry, key="role", context=context), context=f"{context}.role")
    if role not in _SUPPORTED_MODELED_ROLES:
        raise ValueError(
            f"{context}.role must be one of ['tx_single_coil', 'tx_inner_single_coil', 'rx_single_coil', 'tx_plate_stack', 'rx_plate_stack', 'tx_rect_void_columns']; "
            "tx_outer_single_coil is inactive and unsupported in active Type2 import "
            f"(actual={role!r})"
        )
    plane = require_non_empty_str(require_key(entry, key="plane", context=context), context=f"{context}.plane")
    if plane not in _SUPPORTED_MODELED_PLANES:
        raise ValueError(f"{context}.plane must be one of ['XY', 'YZ'] (actual={plane!r})")
    if role == "tx_plate_stack" and plane != "YZ":
        raise ValueError(f"{context}.plane must be 'YZ' for tx_plate_stack import-only geometry (actual={plane!r})")
    if role == "rx_plate_stack" and plane != "YZ":
        raise ValueError(f"{context}.plane must be 'YZ' for rx_plate_stack import-only geometry (actual={plane!r})")
    placement_owner_id = require_non_empty_str(
        require_key(entry, key="placement_owner_id", context=context),
        context=f"{context}.placement_owner_id",
    )
    material = require_non_empty_str(require_key(entry, key="material", context=context), context=f"{context}.material")
    if _require_bool(require_key(entry, key="model_state", context=context), context=f"{context}.model_state") is not True:
        raise ValueError(f"{context}.model_state must be true")
    if role == _TV_ALUMINUM_PLATE_ROLE:
        require_sheet_present(
            require_key(entry, key="sheet_present", context=context),
            context=f"{context}.sheet_present",
        )
        if plane != "YZ":
            raise ValueError(f"{context}.plane must be 'YZ' for tv_aluminum_plate modeled geometry (actual={plane!r})")
        if placement_owner_id != "tv":
            raise ValueError(
                f"{context}.placement_owner_id must be 'tv' for tv_aluminum_plate modeled geometry "
                f"(actual={placement_owner_id!r})"
            )
        if material != "aluminum":
            raise ValueError(
                f"{context}.material must be 'aluminum' for tv_aluminum_plate modeled geometry "
                f"(actual={material!r})"
            )
    raw_canonical_coordinates = _validated_canonical_coordinates(
        require_key(entry, key="canonical_coordinates", context=context),
        context=f"{context}.canonical_coordinates",
    )
    _validated_canonical_coordinates(
        require_key(entry, key="exported_body_canonical_coordinates", context=context),
        context=f"{context}.exported_body_canonical_coordinates",
    )
    expected_exported_body_names = validated_object_names(
        cast(
            Sequence[object],
            require_key(entry, key="expected_exported_body_names", context=context),
        ),
        context=f"{context}.expected_exported_body_names",
    )
    expected_exported_body_count = require_int(
        require_key(entry, key="expected_exported_body_count", context=context),
        context=f"{context}.expected_exported_body_count",
    )
    if role == _TV_ALUMINUM_PLATE_ROLE:
        if expected_exported_body_count != 0:
            raise ValueError(
                f"{context}.expected_exported_body_count must be 0 for tv_aluminum_plate sheet geometry "
                f"(actual={expected_exported_body_count})"
            )
        if expected_exported_body_names:
            raise ValueError(
                f"{context}.expected_exported_body_names must be empty for tv_aluminum_plate sheet geometry "
                f"(actual={expected_exported_body_names})"
            )
        _require_float_triplet_sequence(
            require_key(raw_canonical_coordinates, key="sheet_vertices_xyz", context=f"{context}.canonical_coordinates"),
            context=f"{context}.canonical_coordinates.sheet_vertices_xyz",
        )
    elif expected_exported_body_count < 1:
        raise ValueError(f"{context}.expected_exported_body_count must be >= 1")
    if expected_exported_body_count != len(expected_exported_body_names):
        raise ValueError(
            f"{context}.expected_exported_body_count must match expected_exported_body_names length "
            f"(count={expected_exported_body_count}, names={len(expected_exported_body_names)})"
        )
    validated_groups = _validated_exported_body_groups(
        require_key(entry, key="expected_exported_body_groups", context=context),
        context=f"{context}.expected_exported_body_groups",
    )
    expected_name_set = set(expected_exported_body_names)
    grouped_member_name_set = {
        cast(str, member_name)
        for group in validated_groups
        for member_name in cast(list[str], group["member_body_names"])
    }
    if not grouped_member_name_set.issubset(expected_name_set):
        missing_names = sorted(grouped_member_name_set - expected_name_set)
        raise ValueError(
            f"{context}.expected_exported_body_groups members must be drawn from expected_exported_body_names "
            f"(missing={missing_names})"
        )
    _validate_modeled_ferrite_group_contract(
        role=role,
        expected_exported_body_names=expected_exported_body_names,
        validated_groups=validated_groups,
        context=context,
    )
    raw_terminal_metadata = require_key(entry, key="terminal_metadata", context=context)
    if role in _PLATE_STACK_ROLES:
        _validated_plate_stack_terminal_metadata(
            raw_terminal_metadata,
            role=role,
            context=context,
        )
    elif role == _TX_RECT_VOID_COLUMNS_ROLE:
        _validated_tx_rect_void_columns_terminal_metadata(
            raw_terminal_metadata,
            context=context,
        )
    elif role == _TV_ALUMINUM_PLATE_ROLE:
        terminal_metadata = _require_table(raw_terminal_metadata, context=f"{context}.terminal_metadata")
        if len(terminal_metadata) != 0:
            raise ValueError(
                f"{context}.terminal_metadata must be empty for tv_aluminum_plate modeled geometry "
                f"(actual_keys={sorted(terminal_metadata)})"
            )
    else:
        _validated_single_coil_terminal_metadata(
            raw_terminal_metadata,
            context=context,
        )
    if role == "tx_outer_single_coil":
        if "outer_tilt_metadata" in raw_canonical_coordinates:
            _validated_outer_tilt_metadata(
                require_key(
                    raw_canonical_coordinates,
                    key="outer_tilt_metadata",
                    context=f"{context}.canonical_coordinates",
                ),
                context=f"{context}.canonical_coordinates.outer_tilt_metadata",
            )
    require_non_empty_str(
        require_key(entry, key="source_metadata_path", context=context),
        context=f"{context}.source_metadata_path",
    )
    return {"object_id": object_id, "entry": entry}


def require_member_objects(entry: dict[str, object], *, context: str) -> list[dict[str, object]]:
    raw_member_objects = require_key(entry, key="member_objects", context=context)
    return _require_entry_list(raw_member_objects, context=f"{context}.member_objects")


def member_object_id(entry: dict[str, object], *, context: str) -> str:
    return require_non_empty_str(require_key(entry, key="object_id", context=context), context=f"{context}.object_id")


def _member_canonical_coordinates(entry: dict[str, object], *, context: str) -> dict[str, object]:
    return _require_table(
        require_key(entry, key="canonical_coordinates", context=context),
        context=f"{context}.canonical_coordinates",
    )


def _member_exported_body_canonical_coordinates(entry: dict[str, object], *, context: str) -> dict[str, object]:
    return _require_table(
        require_key(entry, key="exported_body_canonical_coordinates", context=context),
        context=f"{context}.exported_body_canonical_coordinates",
    )


def find_owner_member(non_model_entries: list[ValidatedStepEntry], *, object_id: str) -> dict[str, object]:
    matching_members: list[dict[str, object]] = []
    for entry_index, validated_entry in enumerate(non_model_entries):
        member_objects = require_member_objects(
            validated_entry["entry"],
            context=f"non_model_objects[{entry_index}]",
        )
        for member_index, member_object in enumerate(member_objects):
            member_context = f"non_model_objects[{entry_index}].member_objects[{member_index}]"
            if member_object_id(member_object, context=member_context) == object_id:
                matching_members.append(member_object)
    if len(matching_members) != 1:
        raise ValueError(
            f"type2 STEP ledger must contain exactly one {object_id} member object "
            f"(actual={len(matching_members)})"
        )
    return matching_members[0]


def find_owner_members_by_concrete_prefix(
    non_model_entries: list[ValidatedStepEntry],
    *,
    object_id: str,
) -> list[dict[str, object]]:
    matching_members: list[dict[str, object]] = []
    concrete_prefix = f"{object_id}_x"
    for entry_index, validated_entry in enumerate(non_model_entries):
        member_objects = require_member_objects(
            validated_entry["entry"],
            context=f"non_model_objects[{entry_index}]",
        )
        for member_index, member_object in enumerate(member_objects):
            member_context = f"non_model_objects[{entry_index}].member_objects[{member_index}]"
            current_object_id = member_object_id(member_object, context=member_context)
            if current_object_id == object_id or current_object_id.startswith(concrete_prefix):
                matching_members.append(member_object)
    if len(matching_members) == 0:
        raise ValueError(
            f"type2 STEP ledger must contain at least one {object_id} concrete member object "
            f"(actual=0)"
        )
    return matching_members


def outer_bounds_min_xyz(entry: dict[str, object], *, context: str) -> tuple[float, float, float]:
    canonical_coordinates = _member_canonical_coordinates(entry, context=context)
    return require_float_triplet(
        require_key(canonical_coordinates, key="outer_bounds_min_xyz", context=f"{context}.canonical_coordinates"),
        context=f"{context}.canonical_coordinates.outer_bounds_min_xyz",
    )


def outer_bounds_size_xyz(entry: dict[str, object], *, context: str) -> tuple[float, float, float]:
    canonical_coordinates = _member_canonical_coordinates(entry, context=context)
    return require_float_triplet(
        require_key(canonical_coordinates, key="outer_bounds_size_xyz", context=f"{context}.canonical_coordinates"),
        context=f"{context}.canonical_coordinates.outer_bounds_size_xyz",
    )


def exported_body_outer_bounds_min_xyz(entry: dict[str, object], *, context: str) -> tuple[float, float, float]:
    canonical_coordinates = _member_exported_body_canonical_coordinates(entry, context=context)
    return require_float_triplet(
        require_key(
            canonical_coordinates,
            key="outer_bounds_min_xyz",
            context=f"{context}.exported_body_canonical_coordinates",
        ),
        context=f"{context}.exported_body_canonical_coordinates.outer_bounds_min_xyz",
    )


def exported_body_outer_bounds_size_xyz(entry: dict[str, object], *, context: str) -> tuple[float, float, float]:
    canonical_coordinates = _member_exported_body_canonical_coordinates(entry, context=context)
    return require_float_triplet(
        require_key(
            canonical_coordinates,
            key="outer_bounds_size_xyz",
            context=f"{context}.exported_body_canonical_coordinates",
        ),
        context=f"{context}.exported_body_canonical_coordinates.outer_bounds_size_xyz",
    )


def load_step_ledger(step_ledger_path: Path) -> ValidatedStepLedger:
    if not step_ledger_path.is_file():
        raise FileNotFoundError(f"type2 STEP ledger not found: {step_ledger_path}")
    ledger_dir = step_ledger_path.parent
    raw_payload = json.loads(step_ledger_path.read_text(encoding="utf-8"))
    payload = _require_table(raw_payload, context="type2_step_ledger")
    schema_version = require_non_empty_str(
        require_key(payload, key="schema_version", context="type2_step_ledger"),
        context="type2_step_ledger.schema_version",
    )
    if schema_version != _SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"type2_step_ledger.schema_version must be {_SUPPORTED_SCHEMA_VERSION!r} "
            f"(actual={schema_version!r})"
        )
    source_toml_path = require_non_empty_str(
        require_key(payload, key="source_toml_path", context="type2_step_ledger"),
        context="type2_step_ledger.source_toml_path",
    )
    source_toml_sha256 = require_non_empty_str(
        require_key(payload, key="source_toml_sha256", context="type2_step_ledger"),
        context="type2_step_ledger.source_toml_sha256",
    )
    scene_step_sha256 = require_non_empty_str(
        require_key(payload, key="scene_step_sha256", context="type2_step_ledger"),
        context="type2_step_ledger.scene_step_sha256",
    )
    source_toml_path_resolved = _require_existing_file_from_text(
        source_toml_path,
        context="type2_step_ledger.source_toml_path",
        ledger_dir=ledger_dir,
    )
    actual_source_toml_sha256 = _sha256_hex_digest(source_toml_path_resolved, context="type2_step_ledger.source_toml_path")
    if source_toml_sha256 != actual_source_toml_sha256:
        raise ValueError(
            "type2_step_ledger.source_toml hash mismatch; refusing stale/mixed artifact import"
            f" (expected={source_toml_sha256}, actual={actual_source_toml_sha256})"
        )
    scene_step_path = _require_existing_file_from_text(
        require_key(payload, key="scene_step_path", context="type2_step_ledger"),
        context="type2_step_ledger.scene_step_path",
        ledger_dir=ledger_dir,
    )
    actual_scene_step_sha256 = _sha256_hex_digest(scene_step_path, context="type2_step_ledger.scene_step_path")
    if scene_step_sha256 != actual_scene_step_sha256:
        raise ValueError(
            "type2_step_ledger.scene_step hash mismatch; refusing stale/mixed artifact import"
            f" (expected={scene_step_sha256}, actual={actual_scene_step_sha256})"
        )
    seed = require_int(require_key(payload, key="seed", context="type2_step_ledger"), context="type2_step_ledger.seed")
    em_policy = _validated_em_policy(
        require_key(payload, key="em_policy", context="type2_step_ledger"),
        context="type2_step_ledger.em_policy",
    )
    outputs = parse_outputs_table(
        require_key(payload, key="outputs", context="type2_step_ledger"),
        context="type2_step_ledger.outputs",
    )
    raw_non_model_entries = _require_entry_list(
        require_key(payload, key="non_model_objects", context="type2_step_ledger"),
        context="type2_step_ledger.non_model_objects",
    )
    if len(raw_non_model_entries) == 0:
        raise ValueError("type2_step_ledger.non_model_objects must not be empty")
    raw_modeled_entries = _require_entry_list(
        require_key(payload, key="modeled_objects", context="type2_step_ledger"),
        context="type2_step_ledger.modeled_objects",
    )
    if len(raw_modeled_entries) == 0:
        raise ValueError("type2_step_ledger.modeled_objects must not be empty")

    seen_object_ids: set[str] = set()
    non_model_entries: list[ValidatedStepEntry] = []
    for index, raw_entry in enumerate(raw_non_model_entries):
        validated_entry = _validated_non_model_entry(raw_entry, index=index)
        object_id = validated_entry["object_id"]
        if object_id in seen_object_ids:
            raise ValueError(f"duplicate type2 object id in STEP ledger: {object_id}")
        seen_object_ids.add(object_id)
        non_model_entries.append(validated_entry)

    modeled_entries: list[ValidatedStepEntry] = []
    for index, raw_entry in enumerate(raw_modeled_entries):
        validated_entry = _validated_modeled_entry(raw_entry, index=index)
        object_id = validated_entry["object_id"]
        if object_id in seen_object_ids:
            raise ValueError(f"duplicate type2 object id in STEP ledger: {object_id}")
        seen_object_ids.add(object_id)
        modeled_entries.append(validated_entry)

    member_object_ids: list[str] = []
    for entry_index, validated_entry in enumerate(non_model_entries):
        member_objects = require_member_objects(validated_entry["entry"], context=f"non_model_objects[{entry_index}]")
        for member_index, member_object in enumerate(member_objects):
            member_context = f"non_model_objects[{entry_index}].member_objects[{member_index}]"
            member_object_ids.append(member_object_id(member_object, context=member_context))
    for index, validated_entry in enumerate(modeled_entries):
        context = f"modeled_objects[{index}]"
        role = require_non_empty_str(
            require_key(validated_entry["entry"], key="role", context=context),
            context=f"{context}.role",
        )
        owner_id = require_non_empty_str(
            require_key(validated_entry["entry"], key="placement_owner_id", context=context),
            context=f"{context}.placement_owner_id",
        )
        if role == _TX_RECT_VOID_COLUMNS_ROLE:
            _ = find_owner_members_by_concrete_prefix(non_model_entries, object_id=owner_id)
            continue
        if member_object_ids.count(owner_id) != 1:
            raise ValueError(
                f"type2 STEP ledger must contain exactly one {owner_id} member object "
                f"(actual={member_object_ids.count(owner_id)})"
            )

    return {
        "schema_version": schema_version,
        "source_toml_path": source_toml_path,
        "source_toml_sha256": source_toml_sha256,
        "scene_step_path": scene_step_path,
        "scene_step_sha256": scene_step_sha256,
        "seed": seed,
        "em_policy": em_policy,
        "outputs": outputs,
        "non_model_objects": non_model_entries,
        "modeled_objects": modeled_entries,
    }


__all__ = [
    "ValidatedStepEntry",
    "ValidatedStepLedger",
    "Type2ImportEmPolicy",
    "exported_body_outer_bounds_min_xyz",
    "exported_body_outer_bounds_size_xyz",
    "find_owner_member",
    "find_owner_members_by_concrete_prefix",
    "load_step_ledger",
    "member_object_id",
    "outer_bounds_min_xyz",
    "outer_bounds_size_xyz",
    "require_float_triplet",
    "require_int",
    "require_key",
    "require_member_objects",
    "require_non_empty_str",
    "validated_object_names",
]

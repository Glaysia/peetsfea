from __future__ import annotations

import math
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Literal, NoReturn, cast

import build123d as bd

from peetsfea.tx_rect_void import BoxSpec
from peetsfea.tx_rect_void import SingleCoilProfile
from peetsfea.tx_rect_void import TX_PARALLEL_SINGLE_COIL_ROLES
from peetsfea.tx_rect_void import build_tx_rect_void_box_specs
from peetsfea.tx_rect_void import load_tx_rect_void_spec
from peetsfea.tx_rect_void import modeled_body_bounds_from_boxes
from peetsfea.tx_rect_void import profile_for_modeled_role
from peetsfea.tx_rect_void import realize_tx_rect_void_spec
from peetsfea.type2_plate_stack import expected_plate_stack_body_groups
from peetsfea.type2_plate_stack import expected_plate_stack_body_names
from peetsfea.type2_step_ledger import Type2DirectModeledArtifact
from peetsfea.type2_step_ledger import Type2ImportEmPolicy
from peetsfea.type2_step_ledger import Type2StepLedger
from peetsfea.type2_step_ledger import NonModelObjectLedgerEntry
from peetsfea.type2_step_ledger import ModeledObjectSceneData
from peetsfea.type2_step_ledger import CanonicalCoordinates
from peetsfea.type2_step_ledger import build_modeled_object_ledger_entry
from peetsfea.type2_step_ledger import build_type2_step_ledger
from peetsfea.type2_step_ledger import write_modeled_source_metadata
from peetsfea.type2_step_ledger import write_type2_step_ledger
from peetsfea.type2_scene_geometry import canonical_from_shape
from peetsfea.type2_non_model_scene import TxRegionActualStackSpaceTiltTransform
from peetsfea.type2_non_model_scene import apply_tx_region_actual_stack_space_tilt_transform
from peetsfea.type2_non_model_scene import build_non_model_scene_entry
from peetsfea.type2_non_model_scene import build_non_model_scene_shapes
from peetsfea.type2_non_model_scene import is_concrete_tx_region_actual_stack_space_object_id
from peetsfea.type2_non_model_scene import parent_tx_region_actual_object_id_for_stack_space_object_id
from peetsfea.type2_non_model_scene import require_non_model_object_spec
from peetsfea.type2_non_model_scene import resolve_non_model_scene_specs
from peetsfea.type2_non_model_scene import resolve_tx_region_actual_stack_space_tilt_enabled
from peetsfea.type2_non_model_scene import resolve_tx_region_actual_stack_space_tilt_transform
from peetsfea.type2_step_scene import build_modeled_scene_data
from peetsfea.type2_step_scene import build_modeled_single_coil_scene_data
from peetsfea.type2_step_spec import ModeledRxPlateStackSpec
from peetsfea.type2_step_spec import ModeledRxSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxRectVoidColumnsSpec
from peetsfea.type2_step_spec import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec import NonModelTxRegionActualStackSpaceSpec
from peetsfea.type2_step_spec import ModeledSingleCoilSpec
from peetsfea.type2_step_spec import Type2StepSpec
from peetsfea.type2_step_spec import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import NonModelDerivedSpec
from peetsfea.type2_step_spec import Point3
from peetsfea.type2_step_spec import RangeSpec
from peetsfea.type2_step_spec import load_type2_step_spec
from peetsfea.type2_step_spec import placement_owner_id_for_role
from peetsfea.type2_step_spec import render_tx_rect_void_toml
from peetsfea.type2_step_spec import resolve_modeled_plate_stack_turn_count
from peetsfea.type2_step_spec import resolve_modeled_tx_coil_count
from peetsfea.type2_step_spec import resolve_modeled_underlay_repeat_count
from peetsfea.type2_step_spec import resolve_modeled_wall_parallel_stack_present
from peetsfea.type2_tx_rect_void_collectors import TxRectVoidCollectorBranchBalanceAudit
from peetsfea.type2_tx_rect_void_collectors import TxRectVoidCollectorExternalTabFaceVertices
from peetsfea.type2_tx_rect_void_collectors import TxRectVoidCollectorOverlapAudit
from peetsfea.type2_tx_rect_void_collectors import TxRectVoidCollectorPathLengthAudit
from peetsfea.type2_tx_rect_void_collectors import TxRectVoidCollectorSourceLabelGroups
from peetsfea.type2_tx_rect_void_collectors import TxRectVoidCollectorTileInput
from peetsfea.type2_tx_rect_void_collectors import TxRectVoidColumnsCollectorBuildResult
from peetsfea.type2_tx_rect_void_collectors import build_tx_rect_void_columns_collectors
from peetsfea.type2_tx_rect_void_columns import TxRectVoidColumnsBuildResult
from peetsfea.type2_tx_rect_void_columns import TxRectVoidColumnsTileTerminalAnchors
from peetsfea.type2_tx_rect_void_columns import build_tx_rect_void_columns_axis_aligned_tile_scenes
from peetsfea.type2_tx_plate_stack_array import build_tx_plate_stack_array_scene_data
from peetsfea.type2_tx_plate_stack_array import expected_tx_plate_stack_array_body_groups
from peetsfea.type2_tx_plate_stack_array import expected_tx_plate_stack_array_body_names

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_TOML_PATH = REPO_ROOT / "examples" / "type2_fixed.toml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "run" / "step" / "type2"
DEFAULT_LEDGER_PATH = DEFAULT_OUTPUT_DIR / "type2_step_ledger.json"
DEFAULT_SCENE_STEP_PATH = DEFAULT_OUTPUT_DIR / "type2_scene.step"
_TX_FERRITE_GROUP_NAME = "g_ferrite_tx"
_RX_FERRITE_GROUP_NAME = "g_ferrite_rx"
_PLATE_STACK_MERGED_BODY_NAMES: tuple[str, ...] = (
    "tx_plate_copper",
    "tx_stack_pet_psa",
    "tx_stack_ferrite",
    "tx_stack_air",
    "rx_plate_copper",
    "rx_stack_pet_psa",
    "rx_stack_ferrite",
    "rx_stack_air",
)
_TX_RECT_VOID_COLUMNS_FUSED_COPPER_BODY_LABEL = "tx_rect_void_columns_copper"
_Type2StepExportStage = Literal["build_scene", "export_scene_step", "finalize_step_artifacts"]


def _no_op_type2_step_export_stage_reporter(stage: _Type2StepExportStage) -> None:
    pass


def _raise_if_tx_rect_void_columns_modeled_role_present(
    *,
    spec: Type2StepSpec,
    context: str,
) -> None:
    tx_rect_void_columns_ids = _tx_rect_void_columns_object_ids(spec=spec)
    if tx_rect_void_columns_ids:
        _raise_tx_rect_void_columns_deactivated(
            context=context,
            object_ids=tx_rect_void_columns_ids,
        )


def _raise_if_modeled_tx_role_present(
    *,
    spec: Type2StepSpec,
    context: str,
) -> None:
    tx_modeled_entries = tuple(
        (modeled_spec.object_id, modeled_spec.role)
        for modeled_spec in spec.modeled_objects
        if modeled_spec.role in ("tx_single_coil", "tx_plate_stack", "tx_rect_void_columns")
    )
    if len(tx_modeled_entries) == 0:
        return
    raise ValueError(
        f"{context} does not support modeled TX geometry in active Type2 RxOnly export. "
        f"Remove TX modeled objects or use a future two-terminal export path. object_roles={tx_modeled_entries}"
    )


def _tx_rect_void_columns_object_ids(*, spec: Type2StepSpec) -> tuple[str, ...]:
    return tuple(
        modeled_spec.object_id
        for modeled_spec in spec.modeled_objects
        if modeled_spec.role == "tx_rect_void_columns"
    )


def _raise_tx_rect_void_columns_deactivated(
    *,
    context: str,
    object_ids: tuple[str, ...],
) -> NoReturn:
    raise ValueError(
        f"{context} failed at parser/sampler-only milestone: role is deactivated for active type2 inputs: "
        f"tx_rect_void_columns. object_ids={object_ids}"
    )


def _validate_top_level_scene_child(shape: bd.Shape) -> None:
    children = tuple(shape.children)
    if children:
        for child in children:
            _validate_top_level_scene_child(cast(bd.Shape, child))
        return
    solid_count = len(tuple(shape.solids()))
    if solid_count == 1:
        return
    if solid_count != 0:
        raise RuntimeError(
            "type2 scene STEP top-level child must contain either one solid or one sheet "
            f"(label={shape.label}, solid_count={solid_count})"
        )
    face_count = len(tuple(shape.faces()))
    if face_count != 1:
        raise RuntimeError(
            "type2 scene STEP top-level non-solid child must contain exactly one face "
            f"(label={shape.label}, face_count={face_count})"
        )


def _canonical_coordinates_center_xyz(
    *,
    canonical_coordinates: CanonicalCoordinates,
) -> Point3:
    origin_xyz = canonical_coordinates["outer_bounds_min_xyz"]
    size_xyz = canonical_coordinates["outer_bounds_size_xyz"]
    return (
        origin_xyz[0] + (size_xyz[0] * 0.5),
        origin_xyz[1] + (size_xyz[1] * 0.5),
        origin_xyz[2] + (size_xyz[2] * 0.5),
    )


def _face_from_xy_polygon(points_xy: tuple[tuple[float, float], ...]) -> bd.Face:
    if len(points_xy) < 3:
        raise RuntimeError(
            "tx_rect_void_columns terminal metadata polygon requires at least three points "
            f"(points={points_xy})"
        )
    with bd.BuildLine() as builder:
        bd.Polyline(*points_xy, close=True)
    line = builder.line
    if line is None:
        raise RuntimeError("tx_rect_void_columns terminal polygon builder returned no line")
    wires = tuple(line.wires())
    if len(wires) != 1:
        raise RuntimeError(
            "tx_rect_void_columns terminal polygon builder must produce one wire "
            f"(actual={len(wires)})"
        )
    return cast(bd.Face, bd.make_face(edges=tuple(wires[0].edges())))


def _face_from_box_spec_top_polygon(
    *,
    box_spec: BoxSpec,
) -> bd.Face:
    if box_spec.size_xyz[2] <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns terminal anchor box must have positive z extent "
            f"(label={box_spec.label}, size_xyz={box_spec.size_xyz})"
        )
    origin_x, origin_y, origin_z = box_spec.origin_xyz
    size_x, size_y, size_z = box_spec.size_xyz
    top_z = origin_z + size_z
    return _face_from_xy_polygon(
        points_xy=(
            (origin_x, origin_y),
            (origin_x + size_x, origin_y),
            (origin_x + size_x, origin_y + size_y),
            (origin_x, origin_y + size_y),
        )
    ).moved(
        bd.Location((0.0, 0.0, top_z))
    )


def _point_xyz_from_vertex(vertex: bd.Vertex) -> tuple[float, float, float]:
    return (vertex.X, vertex.Y, vertex.Z)


def _face_xy_vertices(face: bd.Face) -> tuple[tuple[float, float, float], ...]:
    vertices = tuple(face.vertices())
    if len(vertices) != 4:
        raise RuntimeError(
            "tx_rect_void_columns terminal anchor top polygon must have four vertices "
            f"(actual={len(vertices)}, label={face.label})"
        )
    return tuple(_point_xyz_from_vertex(vertex) for vertex in vertices)


def _build_tx_rect_void_parallel_collector_handoff(
    *,
    tile_inputs: tuple[TxRectVoidCollectorTileInput, ...],
    connection_mode: int,
) -> TxRectVoidColumnsCollectorBuildResult:
    return build_tx_rect_void_columns_collectors(connection_mode=connection_mode, tile_inputs=tile_inputs)


def _collector_source_label_metadata(
    *,
    label_groups: TxRectVoidCollectorSourceLabelGroups,
) -> dict[str, tuple[str, ...]]:
    return {
        "start_pours": label_groups.start_pours,
        "end_pours": label_groups.end_pours,
        "end_layer_drops": label_groups.end_layer_drops,
        "series_links": label_groups.series_links,
        "start_external_tabs": label_groups.start_external_tabs,
        "end_external_tabs": label_groups.end_external_tabs,
    }


def _collector_tab_face_vertices_metadata(
    *,
    vertices: TxRectVoidCollectorExternalTabFaceVertices,
) -> tuple[dict[str, object], dict[str, object]]:
    return (
        {"terminal": "start", "vertices_xyz": vertices.start},
        {"terminal": "end", "vertices_xyz": vertices.end},
    )


def _collector_branch_balance_metadata(
    *,
    audit: TxRectVoidCollectorBranchBalanceAudit,
) -> dict[str, object]:
    return {
        "branch_count": audit.branch_count,
        "start_total_feed_length_mm": audit.start_total_feed_length_mm,
        "end_total_feed_length_mm": audit.end_total_feed_length_mm,
        "balance_delta_mm": audit.balance_delta_mm,
        "max_branch_total_delta_mm": audit.max_branch_total_delta_mm,
        "branch_spread_limit_mm": audit.branch_spread_limit_mm,
        "tolerance_mm": audit.tolerance_mm,
    }


def _collector_overlap_audit_metadata(
    *,
    audit: TxRectVoidCollectorOverlapAudit,
) -> dict[str, object]:
    return {
        "checked_pair_count": audit.checked_pair_count,
        "positive_volume_pair_count": audit.positive_volume_pair_count,
        "max_intersection_volume_mm3": audit.max_intersection_volume_mm3,
        "tolerance_mm3": audit.tolerance_mm3,
    }


def _collector_path_length_metadata(
    *,
    audit: TxRectVoidCollectorPathLengthAudit,
) -> dict[str, object]:
    return {
        "branch_count": audit.branch_count,
        "series_link_count": audit.series_link_count,
        "total_link_length_mm": audit.total_link_length_mm,
        "path_length_delta_mm": audit.path_length_delta_mm,
        "tolerance_mm": audit.tolerance_mm,
    }


def _is_modeled_rx_object(*, role: str) -> bool:
    return role in ("rx_single_coil", "rx_plate_stack")


def _remove_generated_type2_artifacts(output_dir: Path) -> None:
    stale_file_paths = (
        output_dir / "type2_non_model_scene.step",
        output_dir / "type2_combined_preview.step",
    )
    for stale_file_path in stale_file_paths:
        if stale_file_path.exists():
            if not stale_file_path.is_file():
                raise RuntimeError(f"type2 generated artifact path must be a file: {stale_file_path}")
            stale_file_path.unlink()
    stale_dir_paths = (
        output_dir / "objects",
        output_dir / "metadata",
    )
    for stale_dir_path in stale_dir_paths:
        if stale_dir_path.exists():
            if not stale_dir_path.is_dir():
                raise RuntimeError(f"type2 generated artifact path must be a directory: {stale_dir_path}")
            shutil.rmtree(stale_dir_path)


def _require_plate_stack_merged_scene_shape_contract(*, scene_shapes: tuple[bd.Shape, ...]) -> None:
    scene_shape_by_label = {shape.label: shape for shape in scene_shapes}
    for body_name in _PLATE_STACK_MERGED_BODY_NAMES:
        if body_name not in scene_shape_by_label:
            continue
        shape = scene_shape_by_label[body_name]
        child_count = len(tuple(shape.children))
        if child_count != 0:
            raise RuntimeError(
                "type2 plate-stack merged body must be an exact solid without child expansion at STEP handoff "
                f"(body_name={body_name}, child_count={child_count})"
            )
        solid_count = len(tuple(shape.solids()))
        if solid_count != 1:
            raise RuntimeError(
                "type2 plate-stack merged body must be exactly one solid at STEP handoff "
                f"(body_name={body_name}, solid_count={solid_count})"
            )


def _single_solid_cut_shape(
    *,
    blank_shape: bd.Shape,
    tool_shape: bd.Shape,
    label: str,
    context: str,
) -> bd.Shape:
    cut_shape = cast(bd.Shape, blank_shape.cut(tool_shape))
    solids = tuple(cut_shape.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "type2 shape cut must produce exactly one solid "
            f"(label={label}, context={context}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = label
    return cast(bd.Shape, solid)


def _export_modeled_single_coil(
    spec: ModeledTxSingleCoilSpec | ModeledTxInnerSingleCoilSpec,
    *,
    owner_spec: NonModelBoxSpec,
    source_toml_path: Path,
    output_path: Path,
    metadata_path: Path,
    seed: int,
) -> Type2DirectModeledArtifact:
    profile = profile_for_modeled_role(spec.role)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    scene_children, scene_data = build_modeled_single_coil_scene_data(
        spec,
        owner_spec=owner_spec,
        seed=seed,
    )
    for shape in scene_children:
        _validate_top_level_scene_child(shape)
    scene = bd.Compound(children=scene_children, label=profile.compound_label)
    export_ok = bd.export_step(scene, output_path)
    if export_ok is not True:
        raise RuntimeError(f"build123d export_step returned False for modeled type2 STEP: {output_path}")
    write_modeled_source_metadata(
        metadata_path=metadata_path,
        source_toml_path=source_toml_path,
        scene_step_path=output_path,
        scene_data=scene_data,
    )
    return {
        "object_id": scene_data["object_id"],
        "role": scene_data["role"],
        "plane": scene_data["plane"],
        "placement_owner_id": scene_data["placement_owner_id"],
        "material": scene_data["material"],
        "model_state": scene_data["model_state"],
        "step_path": str(output_path),
        "expected_exported_body_names": scene_data["expected_exported_body_names"],
        "expected_exported_body_count": scene_data["expected_exported_body_count"],
        "expected_exported_body_groups": scene_data["expected_exported_body_groups"],
        "canonical_coordinates": scene_data["canonical_coordinates"],
        "terminal_metadata": scene_data["terminal_metadata"],
        "source_metadata_path": str(metadata_path),
    }


def export_type2_tx_single_coil_artifact(
    *,
    toml_path: Path,
    output_step_path: Path,
    metadata_path: Path,
    seed: int,
) -> Type2DirectModeledArtifact:
    spec = load_type2_step_spec(toml_path)
    _raise_if_modeled_tx_role_present(
        spec=spec,
        context="tx_single_coil direct export",
    )
    _raise_if_tx_rect_void_columns_modeled_role_present(
        spec=spec,
        context="tx_single_coil direct export",
    )
    tx_rect_void_columns_ids = _tx_rect_void_columns_object_ids(spec=spec)
    if tx_rect_void_columns_ids:
        _raise_tx_rect_void_columns_deactivated(
            context="tx_single_coil direct export modeled dispatch",
            object_ids=tx_rect_void_columns_ids,
        )
    tx_specs = [modeled_spec for modeled_spec in spec.modeled_objects if modeled_spec.role == "tx_single_coil"]
    if len(tx_specs) != 1:
        raise RuntimeError(
            "type2 tx_single_coil direct export requires exactly one tx_single_coil modeled object "
            f"(actual={len(tx_specs)})"
        )
    tx_profile = profile_for_modeled_role("tx_single_coil")
    owner_spec = require_non_model_object_spec(spec.non_model_objects, object_id=tx_profile.placement_owner_id)
    return _export_modeled_single_coil(
        tx_specs[0],
        owner_spec=owner_spec,
        source_toml_path=toml_path,
        output_path=output_step_path,
        metadata_path=metadata_path,
        seed=seed,
    )


def _tx_wall_expected_body_names(*, repeat_count: int) -> list[str]:
    if repeat_count == 0:
        return []
    return [
        "tx_wall_ferrite_u0",
        "tx_wall_pet_psa_u0",
        "tx_wall_air_u0",
    ]


def _rx_underlay_expected_body_names(*, repeat_count: int) -> list[str]:
    if repeat_count == 0:
        return []
    return [
        "under_rx_ferrite_u0",
        "under_rx_pet_psa_u0",
        "under_rx_air_u0",
    ]


def _plate_stack_expected_body_names(
    *,
    spec: ModeledTxPlateStackSpec | ModeledRxPlateStackSpec,
    seed: int,
) -> list[str]:
    if isinstance(spec, ModeledTxPlateStackSpec):
        return list(
            expected_tx_plate_stack_array_body_names(
                tx_coil_count=resolve_modeled_tx_coil_count(spec, seed=seed),
            )
        )
    realized_turn_count = resolve_modeled_plate_stack_turn_count(spec, seed=seed)
    return list(
        expected_plate_stack_body_names(
            role=spec.role,
            turn_count=realized_turn_count,
            pcb_total_thickness_mm=spec.pcb_total_thickness_mm,
        )
    )


def _plate_stack_expected_body_groups(
    *,
    spec: ModeledTxPlateStackSpec | ModeledRxPlateStackSpec,
    seed: int,
) -> list[dict[str, object]]:
    if isinstance(spec, ModeledTxPlateStackSpec):
        return [
            {
                "group_name": group_entry["group_name"],
                "member_body_names": group_entry["member_body_names"],
            }
            for group_entry in expected_tx_plate_stack_array_body_groups(
                tx_coil_count=resolve_modeled_tx_coil_count(spec, seed=seed),
            )
        ]
    return [
        {
            "group_name": group_entry["group_name"],
            "member_body_names": group_entry["member_body_names"],
        }
        for group_entry in expected_plate_stack_body_groups(
            role=spec.role,
        )
    ]


def _resolve_modeled_rx_center_from_scene_data(
    *,
    modeled_scene_data: tuple[ModeledObjectSceneData, ...],
) -> Point3:
    if not modeled_scene_data:
        raise RuntimeError("modeled scene data must exist when resolving modeled RX center")
    rx_scene_data = tuple(scene_data for scene_data in modeled_scene_data if _is_modeled_rx_object(role=scene_data["role"]))
    if len(rx_scene_data) != 1:
        raise RuntimeError(
            "type2 tilt-enabled tx_region_actual_stack_space requires exactly one modeled RX object "
            f"(actual={len(rx_scene_data)})"
        )
    return _canonical_coordinates_center_xyz(
        canonical_coordinates=cast(
            CanonicalCoordinates,
            rx_scene_data[0]["canonical_coordinates"],
        )
    )


def _build_non_model_scene_entry_and_shapes(
    *,
    resolved_non_model_specs: tuple[NonModelBoxSpec, ...],
    tilt_enabled: int,
    rx_center: Point3,
) -> tuple[NonModelObjectLedgerEntry, tuple[bd.Shape, ...], dict[str, dict[str, object]]]:
    del rx_center
    non_model_entry = build_non_model_scene_entry(resolved_non_model_specs)
    shapes = tuple(build_non_model_scene_shapes(resolved_non_model_specs))
    if tilt_enabled != 1:
        raise RuntimeError(f"tx_region_actual_stack_space tilt_enabled must be fixed to 1 (actual={tilt_enabled})")
    return non_model_entry, shapes, {}


def _build_tx_rect_void_columns_scene_data(
    *,
    modeled_spec: ModeledTxRectVoidColumnsSpec,
    resolved_non_model_specs: tuple[NonModelBoxSpec, ...],
    stack_space_tilt_placements: dict[str, dict[str, object]],
    seed: int,
) -> tuple[tuple[bd.Shape, ...], ModeledObjectSceneData]:
    stack_space_specs = tuple(
        spec for spec in resolved_non_model_specs if spec.kind == "tx_region_actual_stack_space"
    )
    if len(stack_space_specs) == 0:
        raise RuntimeError("tx_rect_void_columns requires resolved tx_region_actual_stack_space members")
    rx_region_max_spec = require_non_model_object_spec(
        resolved_non_model_specs,
        object_id="rx_region_max",
    )
    rx_center_xyz: tuple[float, float, float] = (
        rx_region_max_spec.origin_xyz[0] + (rx_region_max_spec.size_xyz[0] * 0.5),
        rx_region_max_spec.origin_xyz[1] + (rx_region_max_spec.size_xyz[1] * 0.5),
        rx_region_max_spec.origin_xyz[2] + (rx_region_max_spec.size_xyz[2] * 0.5),
    )
    build_result: TxRectVoidColumnsBuildResult = build_tx_rect_void_columns_axis_aligned_tile_scenes(
        spec=modeled_spec,
        stack_space_specs=stack_space_specs,
        rx_center_xyz=rx_center_xyz,
        seed=seed,
    )
    if build_result.connection_mode not in (0, 1):
        raise RuntimeError(
            "tx_rect_void_columns connection_mode must resolve to 0 or 1 "
            f"(actual={build_result.connection_mode})"
        )
    tile_terminal_anchors_by_stack_space: dict[str, TxRectVoidColumnsTileTerminalAnchors] = {}
    for tile_anchor in build_result.tile_terminal_anchors:
        if tile_anchor.stack_space_object_id in tile_terminal_anchors_by_stack_space:
            raise RuntimeError(
                "tx_rect_void_columns terminal anchor metadata must be unique per tile "
                f"(stack_space_object_id={tile_anchor.stack_space_object_id})"
            )
        tile_terminal_anchors_by_stack_space[tile_anchor.stack_space_object_id] = tile_anchor
    if len(tile_terminal_anchors_by_stack_space) != len(build_result.tile_scenes):
        raise RuntimeError(
            "tx_rect_void_columns terminal anchor metadata must provide one entry per tile scene "
            f"(tiles={len(build_result.tile_scenes)}, anchors={len(tile_terminal_anchors_by_stack_space)})"
        )
    if build_result.terminal_stub_length_mm <= 0.0:
        raise RuntimeError(
            "tx_rect_void_columns terminal_stub_length_mm must be positive "
            f"(actual={build_result.terminal_stub_length_mm})"
        )

    transformed_shapes: list[bd.Shape] = []
    tile_metadata: list[dict[str, object]] = []
    pcb_layer_positions: list[float] = []
    copper_layer_positions: list[float] = []
    vertical_stub_body_names: list[str] = []
    parallel_tile_inputs: list[TxRectVoidCollectorTileInput] = []

    def _collect_terminal_anchor_box_specs_from_metadata(
        *,
        tile_anchor_metadata: TxRectVoidColumnsTileTerminalAnchors,
        terminal_stub_label_pairs: tuple[tuple[str, str], ...],
    ) -> dict[str, tuple[BoxSpec, ...]]:
        if len(terminal_stub_label_pairs) != 1:
            raise RuntimeError(
                "tx_rect_void_columns terminal label metadata must expose exactly one terminal pair per tile "
                f"(tile={tile_anchor_metadata.stack_space_object_id}, actual={len(terminal_stub_label_pairs)})"
            )
        if len(tile_anchor_metadata.terminal_anchor_box_specs) != build_result.layer_count:
            raise RuntimeError(
                "tx_rect_void_columns terminal anchor metadata must expose one BoxSpec pair per realized layer "
                f"(tile={tile_anchor_metadata.stack_space_object_id}, expected={build_result.layer_count}, "
                f"actual={len(tile_anchor_metadata.terminal_anchor_box_specs)})"
            )
        start_terminal_body_name, end_terminal_body_name = terminal_stub_label_pairs[0]
        terminal_box_specs_by_body: dict[str, list[BoxSpec]] = {
            start_terminal_body_name: [],
            end_terminal_body_name: [],
        }
        for layer_index in range(build_result.layer_count):
            start_anchor_box_spec, end_anchor_box_spec = tile_anchor_metadata.terminal_anchor_box_specs[layer_index]
            for anchor_box_spec in (start_anchor_box_spec, end_anchor_box_spec):
                anchor_size_x, anchor_size_y, anchor_size_z = anchor_box_spec.size_xyz
                if anchor_size_x <= 0.0 or anchor_size_y <= 0.0 or anchor_size_z <= 0.0:
                    raise RuntimeError(
                        "tx_rect_void_columns terminal anchor BoxSpec must have positive dimensions "
                        f"(stack_space_object_id={tile_anchor_metadata.stack_space_object_id}, "
                        f"anchor_label={anchor_box_spec.label}, size_xyz={anchor_box_spec.size_xyz})"
                    )
            terminal_box_specs_by_body[start_terminal_body_name].append(start_anchor_box_spec)
            terminal_box_specs_by_body[end_terminal_body_name].append(end_anchor_box_spec)
        return {name: tuple(specs) for name, specs in terminal_box_specs_by_body.items()}

    def _transformed_terminal_top_faces_by_z(
        *,
        terminal_anchor_box_specs: tuple[BoxSpec, ...],
        transform: TxRegionActualStackSpaceTiltTransform,
        stack_space_object_id: str,
        terminal_body_name: str,
    ) -> tuple[tuple[float, bd.Face], ...]:
        if len(terminal_anchor_box_specs) != build_result.layer_count:
            raise RuntimeError(
                "tx_rect_void_columns terminal anchor metadata must provide one box spec per layer for each terminal "
                f"(tile={stack_space_object_id}, terminal={terminal_body_name}, expected={build_result.layer_count}, "
                f"actual={len(terminal_anchor_box_specs)})"
            )
        transformed_top_faces_by_z: list[tuple[float, bd.Face]] = []
        for terminal_anchor_box_spec in terminal_anchor_box_specs:
            top_face = _face_from_box_spec_top_polygon(box_spec=terminal_anchor_box_spec)
            transformed_top_face = apply_tx_region_actual_stack_space_tilt_transform(
                shape=top_face,
                transform=transform,
            )
            transformed_top_face = cast(bd.Face, transformed_top_face)
            transformed_top_face_vertices = _face_xy_vertices(face=transformed_top_face)
            transformed_top_face_avg_z = sum(vertex[2] for vertex in transformed_top_face_vertices) / 4.0
            transformed_top_faces_by_z.append((transformed_top_face_avg_z, transformed_top_face))
        if len(transformed_top_faces_by_z) == 0:
            raise RuntimeError(
                "tx_rect_void_columns terminal body requires at least one transformed top contact face "
                f"(stack_space_object_id={stack_space_object_id}, terminal_body_name={terminal_body_name})"
            )
        return tuple(transformed_top_faces_by_z)

    def _natural_floorward_terminal_bottom_z(
        *,
        transformed_top_faces_by_z: tuple[tuple[float, bd.Face], ...],
        stack_space_object_id: str,
        terminal_body_name: str,
    ) -> float:
        if len(transformed_top_faces_by_z) == 0:
            raise RuntimeError(
                "tx_rect_void_columns terminal body requires at least one transformed top contact face "
                f"(stack_space_object_id={stack_space_object_id}, terminal_body_name={terminal_body_name})"
            )
        lowest_top_face_avg_z = min(top_face_avg_z for top_face_avg_z, _face in transformed_top_faces_by_z)
        return lowest_top_face_avg_z - build_result.terminal_stub_length_mm

    def _build_slanted_terminal_body(
        *,
        terminal_body_name: str,
        terminal_anchor_box_specs: tuple[BoxSpec, ...],
        transform: TxRegionActualStackSpaceTiltTransform,
        stack_space_object_id: str,
        bottom_z: float,
    ) -> tuple[bd.Shape, bd.Face, tuple[tuple[float, float, float], ...]]:
        transformed_top_faces_by_z = _transformed_terminal_top_faces_by_z(
            terminal_anchor_box_specs=terminal_anchor_box_specs,
            transform=transform,
            stack_space_object_id=stack_space_object_id,
            terminal_body_name=terminal_body_name,
        )
        sorted_top_faces = tuple(
            transformed_top_face
            for _z, transformed_top_face in sorted(
                transformed_top_faces_by_z,
                key=lambda entry: entry[0],
                reverse=True,
            )
        )
        lowest_top_face = sorted_top_faces[-1]
        lowest_top_face_vertices = _face_xy_vertices(face=lowest_top_face)
        bottom_face = cast(
            bd.Face,
            _face_from_xy_polygon(
                points_xy=tuple((vertex[0], vertex[1]) for vertex in lowest_top_face_vertices)
            ).moved(bd.Location((0.0, 0.0, bottom_z))),
        )
        terminal_shape = cast(
            bd.Shape,
            bd.loft((*sorted_top_faces, bottom_face), ruled=True),
        )
        terminal_shape.label = terminal_body_name
        terminal_solids = tuple(terminal_shape.solids())
        if len(terminal_solids) != 1:
            raise RuntimeError(
                "tx_rect_void_columns terminal loft must produce exactly one solid "
                f"(stack_space_object_id={stack_space_object_id}, terminal_body_name={terminal_body_name}, "
                f"solid_count={len(terminal_solids)})"
            )
        if len(tuple(terminal_shape.solids())) != 1:
            raise RuntimeError(
                "tx_rect_void_columns terminal body must be a single solid "
                f"(stack_space_object_id={stack_space_object_id}, terminal_body_name={terminal_body_name})"
            )
        return terminal_shape, bottom_face, _face_xy_vertices(face=bottom_face)

    natural_terminal_bottom_z_values: list[float] = []
    for tile_scene in build_result.tile_scenes:
        stack_space_object_id = tile_scene.stack_space_object_id
        if stack_space_object_id not in stack_space_tilt_placements:
            raise RuntimeError(
                "tx_rect_void_columns requires tilt placement metadata for each stack-space tile "
                f"(missing={stack_space_object_id})"
            )
        tilt_placement = stack_space_tilt_placements[stack_space_object_id]
        transform = tilt_placement["transform"]
        if not isinstance(transform, TxRegionActualStackSpaceTiltTransform):
            raise RuntimeError(
                "tx_rect_void_columns tilt placement transform is missing "
                f"(stack_space_object_id={stack_space_object_id})"
            )
        assert stack_space_object_id in tile_terminal_anchors_by_stack_space
        tile_anchor_metadata = tile_terminal_anchors_by_stack_space[stack_space_object_id]
        terminal_box_specs_by_terminal = _collect_terminal_anchor_box_specs_from_metadata(
            tile_anchor_metadata=tile_anchor_metadata,
            terminal_stub_label_pairs=tile_anchor_metadata.terminal_stub_body_names,
        )
        for terminal_body_name, terminal_anchor_box_specs in terminal_box_specs_by_terminal.items():
            transformed_top_faces_by_z = _transformed_terminal_top_faces_by_z(
                terminal_anchor_box_specs=terminal_anchor_box_specs,
                transform=transform,
                stack_space_object_id=stack_space_object_id,
                terminal_body_name=terminal_body_name,
            )
            natural_terminal_bottom_z_values.append(
                _natural_floorward_terminal_bottom_z(
                    transformed_top_faces_by_z=transformed_top_faces_by_z,
                    stack_space_object_id=stack_space_object_id,
                    terminal_body_name=terminal_body_name,
                )
            )
    if len(natural_terminal_bottom_z_values) == 0:
        raise RuntimeError("tx_rect_void_columns terminal body generation requires at least one terminal bottom")
    shared_terminal_bottom_z = min(natural_terminal_bottom_z_values)

    for tile_scene in build_result.tile_scenes:
        stack_space_object_id = tile_scene.stack_space_object_id
        if stack_space_object_id not in stack_space_tilt_placements:
            raise RuntimeError(
                "tx_rect_void_columns requires tilt placement metadata for each stack-space tile "
                f"(missing={stack_space_object_id})"
            )
        tilt_placement = stack_space_tilt_placements[stack_space_object_id]
        transform = tilt_placement["transform"]
        if not isinstance(transform, TxRegionActualStackSpaceTiltTransform):
            raise RuntimeError(
                "tx_rect_void_columns tilt placement transform is missing "
                f"(stack_space_object_id={stack_space_object_id})"
            )
        assert stack_space_object_id in tile_terminal_anchors_by_stack_space
        tile_anchor_metadata = tile_terminal_anchors_by_stack_space[stack_space_object_id]
        if tile_anchor_metadata.stack_space_object_id != tile_scene.stack_space_object_id:
            raise RuntimeError(
                "tx_rect_void_columns terminal anchor metadata must target same stack-space tile "
                f"(expected={tile_scene.stack_space_object_id}, actual={tile_anchor_metadata.stack_space_object_id})"
            )
        if tile_anchor_metadata.terminal_stub_body_names != tile_scene.terminal_stub_body_names:
            raise RuntimeError(
                "tx_rect_void_columns terminal anchor metadata must match tile scene terminal stub labels "
                f"(tile={stack_space_object_id}, scene_labels={tile_scene.terminal_stub_body_names}, "
                f"anchor_labels={tile_anchor_metadata.terminal_stub_body_names})"
        )
        transformed_tile_shapes: list[bd.Shape] = []
        tile_body_names: list[str] = []
        tile_parallel_copper_shapes: list[bd.Shape] = []
        terminal_stub_label_pairs = tile_anchor_metadata.terminal_stub_body_names
        terminal_stub_labels = [stub_name for pair in terminal_stub_label_pairs for stub_name in pair]
        if len(terminal_stub_labels) != len(set(terminal_stub_labels)):
            raise RuntimeError(
                "tx_rect_void_columns terminal stub labels must be unique per tile "
                f"(tile={stack_space_object_id}, labels={terminal_stub_labels})"
            )
        terminal_box_specs_by_terminal = _collect_terminal_anchor_box_specs_from_metadata(
            tile_anchor_metadata=tile_anchor_metadata,
            terminal_stub_label_pairs=terminal_stub_label_pairs,
        )
        for shape in tile_scene.scene_shapes:
            transformed_shape = apply_tx_region_actual_stack_space_tilt_transform(
                shape=shape,
                transform=transform,
            )
            transformed_shape.label = shape.label
            transformed_tile_shapes.append(transformed_shape)
            bounds = transformed_shape.bounding_box()
            if "_pcb_l" in transformed_shape.label:
                pcb_layer_positions.append(bounds.min.Z)
                transformed_shapes.append(transformed_shape)
                tile_body_names.append(transformed_shape.label)
            elif "_cu_l" in transformed_shape.label:
                copper_layer_positions.append(bounds.min.Z)
                tile_parallel_copper_shapes.append(transformed_shape)
            else:
                raise RuntimeError(
                    "tx_rect_void_columns tile scene must expose only PCB or copper bodies "
                    f"(tile={stack_space_object_id}, body_name={transformed_shape.label})"
                )

        terminal_name_order: list[str] = []
        terminal_name_set: set[str] = set()
        for start_stub_name, end_stub_name in terminal_stub_label_pairs:
            if start_stub_name not in terminal_name_set:
                terminal_name_set.add(start_stub_name)
                terminal_name_order.append(start_stub_name)
            if end_stub_name not in terminal_name_set:
                terminal_name_set.add(end_stub_name)
                terminal_name_order.append(end_stub_name)
        if set(terminal_name_order) != set(terminal_box_specs_by_terminal):
            raise RuntimeError(
                "tx_rect_void_columns terminal anchor metadata must provide all configured terminal bodies "
                f"(tile={stack_space_object_id}, expected={terminal_name_order}, actual={tuple(terminal_box_specs_by_terminal)})"
            )
        parallel_terminal_shapes_by_name: dict[str, tuple[bd.Shape, tuple[tuple[float, float, float], ...]]] = {}
        for terminal_body_name in terminal_name_order:
            terminal_anchor_box_specs = terminal_box_specs_by_terminal[terminal_body_name]
            terminal_shape, _pickup_face, pickup_vertices = _build_slanted_terminal_body(
                terminal_body_name=terminal_body_name,
                terminal_anchor_box_specs=terminal_anchor_box_specs,
                transform=transform,
                stack_space_object_id=stack_space_object_id,
                bottom_z=shared_terminal_bottom_z,
            )
            parallel_terminal_shapes_by_name[terminal_body_name] = (terminal_shape, pickup_vertices)

        if build_result.connection_mode in (0, 1):
            if len(tile_parallel_copper_shapes) == 0:
                raise RuntimeError(
                    "tx_rect_void_columns collector tile input requires at least one copper body "
                    f"(tile={stack_space_object_id})"
                )
            start_stub_name, end_stub_name = terminal_stub_label_pairs[0]
            assert start_stub_name in parallel_terminal_shapes_by_name
            assert end_stub_name in parallel_terminal_shapes_by_name
            start_terminal_shape, start_pickup_vertices = parallel_terminal_shapes_by_name[start_stub_name]
            end_terminal_shape, end_pickup_vertices = parallel_terminal_shapes_by_name[end_stub_name]
            parallel_tile_inputs.append(
                TxRectVoidCollectorTileInput(
                    x_index=tile_scene.x_index,
                    y_index=tile_scene.y_index,
                    tile_copper_shapes=tuple(tile_parallel_copper_shapes),
                    start_terminal_stub_shape=start_terminal_shape,
                    end_terminal_stub_shape=end_terminal_shape,
                    start_pickup_vertices=start_pickup_vertices,
                    end_pickup_vertices=end_pickup_vertices,
                    copper_thickness_mm=modeled_spec.copper_thickness_mm,
                )
            )

        stack_space_canonical = cast(dict[str, object], tilt_placement["stack_space_canonical_coordinates"])
        stack_space_min_xyz = cast(tuple[float, float, float], stack_space_canonical["outer_bounds_min_xyz"])
        stack_space_max_xyz = cast(tuple[float, float, float], stack_space_canonical["outer_bounds_max_xyz"])
        containment_tolerance_mm = 5e-2
        terminal_body_names = {stub_name for pair in terminal_stub_label_pairs for stub_name in pair}
        for transformed_shape in transformed_tile_shapes:
            if transformed_shape.label in terminal_body_names:
                continue
            bbox = transformed_shape.bounding_box()
            if (
                bbox.min.X < stack_space_min_xyz[0] - containment_tolerance_mm
                or bbox.min.Y < stack_space_min_xyz[1] - containment_tolerance_mm
                or bbox.min.Z < stack_space_min_xyz[2] - containment_tolerance_mm
                or bbox.max.X > stack_space_max_xyz[0] + containment_tolerance_mm
                or bbox.max.Y > stack_space_max_xyz[1] + containment_tolerance_mm
                or bbox.max.Z > stack_space_max_xyz[2] + containment_tolerance_mm
            ):
                raise RuntimeError(
                    "tx_rect_void_columns body must remain inside its owning tilted stack-space member bbox "
                    f"(stack_space_object_id={stack_space_object_id}, body_name={transformed_shape.label}, "
                    f"body_min={(bbox.min.X, bbox.min.Y, bbox.min.Z)}, body_max={(bbox.max.X, bbox.max.Y, bbox.max.Z)}, "
                    f"stack_space_min={stack_space_min_xyz}, stack_space_max={stack_space_max_xyz})"
                )
        tile_metadata.append(
            {
                "stack_space_object_id": tile_scene.stack_space_object_id,
                "tx_region_actual_object_id": tile_scene.tx_region_actual_object_id,
                "x_index": tile_scene.x_index,
                "y_index": tile_scene.y_index,
                "body_names": tuple(tile_body_names),
            }
        )

    if build_result.connection_mode in (0, 1):
        if len(parallel_tile_inputs) != len(build_result.tile_scenes):
            raise RuntimeError(
                "tx_rect_void_columns collector input count must match tile scene count "
                f"(inputs={len(parallel_tile_inputs)}, tiles={len(build_result.tile_scenes)})"
            )
        collector_handoff = _build_tx_rect_void_parallel_collector_handoff(
            tile_inputs=tuple(parallel_tile_inputs),
            connection_mode=build_result.connection_mode,
        )
        if collector_handoff.expected_exported_body_name != _TX_RECT_VOID_COLUMNS_FUSED_COPPER_BODY_LABEL:
            raise RuntimeError(
                "tx_rect_void_columns collector handoff body name drifted "
                f"(actual={collector_handoff.expected_exported_body_name})"
            )
        fused_copper_body = collector_handoff.fused_copper_shape
        fused_copper_body.label = _TX_RECT_VOID_COLUMNS_FUSED_COPPER_BODY_LABEL
        source_label_metadata = _collector_source_label_metadata(
            label_groups=collector_handoff.source_labels_grouped_by_role,
        )
        tab_face_vertices_xyz = _collector_tab_face_vertices_metadata(
            vertices=collector_handoff.external_tab_face_vertices,
        )
        branch_balance_audit = _collector_branch_balance_metadata(
            audit=collector_handoff.branch_balance_audit,
        )
        overlap_audit = _collector_overlap_audit_metadata(
            audit=collector_handoff.overlap_audit,
        )
        cut_pcb_shapes = tuple(
            _single_solid_cut_shape(
                blank_shape=shape,
                tool_shape=fused_copper_body,
                label=shape.label,
                context="tx_rect_void_columns.final_pcb_copper_clearance",
            )
            for shape in transformed_shapes
            if "_pcb_l" in shape.label
        )
        transformed_shapes = [
            *cut_pcb_shapes,
            fused_copper_body,
        ]
        if build_result.connection_mode == 0:
            terminal_metadata = {
                "kind": "parallel_collector_tabs",
                "connection_mode": 0,
                "source_label_metadata": source_label_metadata,
                "tab_face_vertices_xyz": tab_face_vertices_xyz,
                "branch_balance_audit": branch_balance_audit,
                "overlap_audit": overlap_audit,
                "layer_count": build_result.layer_count,
                "x_column_count": len({tile["x_index"] for tile in tile_metadata}),
                "y_tile_count": len({tile["y_index"] for tile in tile_metadata}),
            }
        else:
            terminal_metadata = {
                "kind": "series_collector_tabs",
                "connection_mode": 1,
                "source_label_metadata": source_label_metadata,
                "tab_face_vertices_xyz": tab_face_vertices_xyz,
                "tile_order": collector_handoff.series_tile_order,
                "link_labels": collector_handoff.series_link_labels,
                "path_length_audit": _collector_path_length_metadata(audit=collector_handoff.path_length_audit),
                "overlap_audit": overlap_audit,
                "branch_count": len(tile_metadata),
                "layer_count": build_result.layer_count,
                "x_column_count": len({tile["x_index"] for tile in tile_metadata}),
                "y_tile_count": len({tile["y_index"] for tile in tile_metadata}),
            }
    else:
        terminal_metadata = {
            "kind": "geometry_only",
            "connection_status": "skipped_series",
            "x_column_count": len({tile["x_index"] for tile in tile_metadata}),
            "y_tile_count": len({tile["y_index"] for tile in tile_metadata}),
            "layer_count": build_result.layer_count,
            "vertical_stub_body_names": tuple(vertical_stub_body_names),
            "vertical_stub_length_mm": build_result.terminal_stub_length_mm,
        }

    actual_names = tuple(shape.label for shape in transformed_shapes)
    expected_names = actual_names
    if len(actual_names) != len(set(actual_names)):
        raise RuntimeError(
            "tx_rect_void_columns exported body names must remain unique "
            f"(count={len(expected_names)})"
        )
    compound = bd.Compound(children=tuple(transformed_shapes), label=modeled_spec.object_id)
    canonical_coordinates: dict[str, object] = dict(canonical_from_shape(cast(bd.Shape, compound)))
    canonical_coordinates["pcb_layer_z_positions_mm"] = tuple(sorted(set(round(value, 10) for value in pcb_layer_positions)))
    canonical_coordinates["copper_layer_z_positions_mm"] = tuple(
        sorted(set(round(value, 10) for value in copper_layer_positions))
    )
    canonical_coordinates["stack_space_tile_members"] = tuple(tile_metadata)
    scene_data = cast(
        ModeledObjectSceneData,
        {
            "object_id": modeled_spec.object_id,
            "role": "tx_rect_void_columns",
            "plane": "XY",
            "placement_owner_id": "tx_region_actual_stack_space",
            "material": modeled_spec.material,
            "model_state": True,
            "expected_exported_body_names": expected_names,
            "expected_exported_body_count": len(expected_names),
            "expected_exported_body_groups": (),
            "canonical_coordinates": canonical_coordinates,
            "terminal_metadata": terminal_metadata,
        },
    )
    return (tuple(transformed_shapes), scene_data)


def _ferrite_group_name_for_modeled_role(
    *,
    role: Literal["tx_single_coil", "rx_single_coil"],
) -> str:
    if role == "tx_single_coil":
        return _TX_FERRITE_GROUP_NAME
    if role == "rx_single_coil":
        return _RX_FERRITE_GROUP_NAME
    raise RuntimeError(f"unsupported ferrite grouping role: {role}")


def _require_modeled_expected_body_contract(
    ledger: Type2StepLedger,
    *,
    spec: Type2StepSpec,
    seed: int,
) -> None:
    modeled_spec_by_id = {modeled_spec.object_id: modeled_spec for modeled_spec in spec.modeled_objects}
    for modeled_entry in ledger["modeled_objects"]:
        object_id = modeled_entry["object_id"]
        if object_id not in modeled_spec_by_id:
            raise ValueError(f"type2 modeled object spec registry is missing exported object {object_id}")
        modeled_spec = modeled_spec_by_id[object_id]
        role = modeled_entry["role"]
        expected_body_names = modeled_entry["expected_exported_body_names"]
        expected_body_count = modeled_entry["expected_exported_body_count"]
        expected_body_groups = modeled_entry["expected_exported_body_groups"]
        if role == "tx_single_coil":
            if not isinstance(modeled_spec, ModeledTxSingleCoilSpec):
                raise ValueError(
                    f"type2 modeled object spec registry must retain ModeledTxSingleCoilSpec for {object_id} "
                    f"(actual={type(modeled_spec).__name__})"
                )
            pcb_layer_positions = cast(
                tuple[float, ...],
                modeled_entry["canonical_coordinates"]["pcb_layer_z_positions_mm"],
            )
            expected_names = [f"tx_pcb_l{index}" for index in range(len(pcb_layer_positions))]
            if len(pcb_layer_positions) == 1:
                expected_names.append("tx_copper_l0")
            else:
                expected_names.append("tx_copper_stack")
            repeat_count = resolve_modeled_underlay_repeat_count(modeled_spec, seed=seed)
            tx_wall_names = (
                _tx_wall_expected_body_names(repeat_count=repeat_count)
                if repeat_count > 0 and resolve_modeled_wall_parallel_stack_present(modeled_spec, seed=seed)
                else []
            )
            expected_names.extend(tx_wall_names)
            expected_groups = (
                [
                    {
                        "group_name": _ferrite_group_name_for_modeled_role(role=role),
                        "member_body_names": tuple(tx_wall_names),
                    }
                ]
                if len(tx_wall_names) > 0
                else []
            )
        elif role == "tx_inner_single_coil":
            if not isinstance(modeled_spec, ModeledTxInnerSingleCoilSpec):
                raise ValueError(
                    f"type2 modeled object spec registry must retain ModeledTxInnerSingleCoilSpec for {object_id} "
                    f"(actual={type(modeled_spec).__name__})"
                )
            pcb_layer_positions = cast(
                tuple[float, ...],
                modeled_entry["canonical_coordinates"]["pcb_layer_z_positions_mm"],
            )
            expected_names = [f"tx_inner_pcb_l{index}" for index in range(len(pcb_layer_positions))]
            if len(pcb_layer_positions) == 1:
                expected_names.append("tx_inner_copper_l0")
            else:
                expected_names.append("tx_inner_copper_stack")
            expected_groups = []
        elif role == "rx_single_coil":
            if not isinstance(modeled_spec, ModeledRxSingleCoilSpec):
                raise ValueError(
                    f"type2 modeled object spec registry must retain ModeledRxSingleCoilSpec for {object_id} "
                    f"(actual={type(modeled_spec).__name__})"
                )
            expected_names = ["rx_pcb_l0", "rx_copper_l0"]
            rx_underlay_names = _rx_underlay_expected_body_names(
                repeat_count=resolve_modeled_underlay_repeat_count(modeled_spec, seed=seed)
            )
            expected_names.extend(rx_underlay_names)
            expected_groups = (
                [
                    {
                        "group_name": _ferrite_group_name_for_modeled_role(role=role),
                        "member_body_names": tuple(rx_underlay_names),
                    }
                ]
                if len(rx_underlay_names) > 0
                else []
            )
        elif role in ("tx_plate_stack", "rx_plate_stack"):
            if role == "tx_plate_stack" and not isinstance(modeled_spec, ModeledTxPlateStackSpec):
                raise ValueError(
                    f"type2 modeled object spec registry must retain ModeledTxPlateStackSpec for {object_id} "
                    f"(actual={type(modeled_spec).__name__})"
                )
            if role == "rx_plate_stack" and not isinstance(modeled_spec, ModeledRxPlateStackSpec):
                raise ValueError(
                    f"type2 modeled object spec registry must retain ModeledRxPlateStackSpec for {object_id} "
                    f"(actual={type(modeled_spec).__name__})"
                )
            expected_names = _plate_stack_expected_body_names(
                spec=cast(ModeledTxPlateStackSpec | ModeledRxPlateStackSpec, modeled_spec),
                seed=seed,
            )
            expected_groups = _plate_stack_expected_body_groups(
                spec=cast(ModeledTxPlateStackSpec | ModeledRxPlateStackSpec, modeled_spec),
                seed=seed,
            )
        elif role == "tx_rect_void_columns":
            if not isinstance(modeled_spec, ModeledTxRectVoidColumnsSpec):
                raise ValueError(
                    f"type2 modeled object spec registry must retain ModeledTxRectVoidColumnsSpec for {object_id} "
                    f"(actual={type(modeled_spec).__name__})"
                )
            expected_names = list(
                cast(tuple[str, ...], modeled_entry["expected_exported_body_names"])
            )
            expected_groups = []
        else:
            raise ValueError(f"unsupported modeled object role in type2 ledger: {role}")
        if list(expected_body_names) != expected_names:
            raise ValueError(
                "type2 modeled export expected body contract mismatch "
                f"(role={role}, expected={expected_names}, actual={list(expected_body_names)})"
            )
        if expected_body_count != len(expected_names):
            raise ValueError(
                "type2 modeled export expected body count mismatch "
                f"(role={role}, expected={len(expected_names)}, actual={expected_body_count})"
            )
        if list(expected_body_groups) != expected_groups:
            raise ValueError(
                "type2 modeled export expected body group contract mismatch "
                f"(role={role}, expected={expected_groups}, actual={list(expected_body_groups)})"
            )


def _owner_bottom_face_square_plane_vertices(
    *,
    box_origin_xyz: tuple[float, float, float],
    box_size_xyz: tuple[float, float, float],
    plane: str,
) -> tuple[tuple[tuple[float, float], ...], float]:
    if plane == "XY":
        square_side_a = box_size_xyz[0]
        square_side_b = box_size_xyz[1]
        bottom_plane_coordinate = box_origin_xyz[2]
        plane_vertices = (
            (box_origin_xyz[0], box_origin_xyz[1]),
            (box_origin_xyz[0] + box_size_xyz[0], box_origin_xyz[1]),
            (box_origin_xyz[0] + box_size_xyz[0], box_origin_xyz[1] + box_size_xyz[1]),
            (box_origin_xyz[0], box_origin_xyz[1] + box_size_xyz[1]),
        )
    else:
        square_side_a = box_size_xyz[1]
        square_side_b = box_size_xyz[2]
        bottom_plane_coordinate = box_origin_xyz[0]
        plane_vertices = (
            (box_origin_xyz[1], box_origin_xyz[2]),
            (box_origin_xyz[1] + box_size_xyz[1], box_origin_xyz[2]),
            (box_origin_xyz[1] + box_size_xyz[1], box_origin_xyz[2] + box_size_xyz[2]),
            (box_origin_xyz[1], box_origin_xyz[2] + box_size_xyz[2]),
        )
    if square_side_a <= 0.0 or square_side_b <= 0.0:
        raise RuntimeError(
            "type2 port sheet widened diagonal validation requires positive owner bottom-face dimensions "
            f"(plane={plane}, origin={box_origin_xyz}, size={box_size_xyz})"
        )
    if abs(square_side_a - square_side_b) > 1e-8:
        raise RuntimeError(
            "type2 port sheet widened diagonal validation requires square owner bottom faces "
            f"(plane={plane}, origin={box_origin_xyz}, size={box_size_xyz})"
        )
    return (plane_vertices, bottom_plane_coordinate)


def _owner_centerline_perpendicular_distance(
    *,
    point_xy: tuple[float, float],
    first_center_xy: tuple[float, float],
    second_center_xy: tuple[float, float],
) -> float:
    delta_x = second_center_xy[0] - first_center_xy[0]
    delta_y = second_center_xy[1] - first_center_xy[1]
    denominator = math.hypot(delta_x, delta_y)
    if denominator <= 1e-12:
        raise RuntimeError(
            "type2 port sheet widened diagonal validation requires distinct owner centers "
            f"(first_center={first_center_xy}, second_center={second_center_xy})"
        )
    numerator = abs(
        delta_x * (first_center_xy[1] - point_xy[1])
        - (first_center_xy[0] - point_xy[0]) * delta_y
    )
    return numerator / denominator


def _widest_owner_bottom_face_diagonal_vertices(
    *,
    transformed_owner_boxes: tuple[tuple[tuple[float, float, float], tuple[float, float, float]], ...],
    plane: str,
) -> tuple[tuple[float, float, float], ...]:
    if len(transformed_owner_boxes) != 2:
        raise RuntimeError(
            "type2 port sheet widened diagonal validation requires exactly two owner boxes "
            f"(actual={len(transformed_owner_boxes)})"
        )
    plane_vertices_by_owner: list[tuple[tuple[float, float], ...]] = []
    bottom_plane_coordinates: list[float] = []
    owner_center_points: list[tuple[float, float]] = []
    for box_origin_xyz, box_size_xyz in transformed_owner_boxes:
        plane_vertices, bottom_plane_coordinate = _owner_bottom_face_square_plane_vertices(
            box_origin_xyz=box_origin_xyz,
            box_size_xyz=box_size_xyz,
            plane=plane,
        )
        plane_vertices_by_owner.append(plane_vertices)
        bottom_plane_coordinates.append(bottom_plane_coordinate)
        owner_center_points.append(
            (
                sum(point_xy[0] for point_xy in plane_vertices) / 4.0,
                sum(point_xy[1] for point_xy in plane_vertices) / 4.0,
            )
        )
    if max(bottom_plane_coordinates) - min(bottom_plane_coordinates) > 1e-8:
        raise RuntimeError(
            "type2 owner bottom faces must share one plane for widened sheet derivation "
            f"(plane={plane}, plane_values={bottom_plane_coordinates})"
        )

    def _selected_diagonal_vertices(
        *,
        plane_vertices: tuple[tuple[float, float], ...],
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        diagonal_index_pairs = ((0, 2), (1, 3))
        first_index, second_index = diagonal_index_pairs[0]
        first_diagonal_vertices = (plane_vertices[first_index], plane_vertices[second_index])
        best_score = sum(
            _owner_centerline_perpendicular_distance(
                point_xy=point_xy,
                first_center_xy=owner_center_points[0],
                second_center_xy=owner_center_points[1],
            )
            for point_xy in first_diagonal_vertices
        )
        best_diagonal = first_diagonal_vertices
        best_key = cast(
            tuple[tuple[float, float], tuple[float, float]],
            tuple(sorted(first_diagonal_vertices)),
        )
        for first_index, second_index in diagonal_index_pairs[1:]:
            diagonal_vertices = (plane_vertices[first_index], plane_vertices[second_index])
            score = sum(
                _owner_centerline_perpendicular_distance(
                    point_xy=point_xy,
                    first_center_xy=owner_center_points[0],
                    second_center_xy=owner_center_points[1],
                )
                for point_xy in diagonal_vertices
            )
            candidate_key = cast(
                tuple[tuple[float, float], tuple[float, float]],
                tuple(sorted(diagonal_vertices)),
            )
            if (
                score > best_score + 1e-9
                or (abs(score - best_score) <= 1e-9 and candidate_key < best_key)
            ):
                best_score = score
                best_diagonal = diagonal_vertices
                best_key = candidate_key
        return best_diagonal

    diagonal_vertices: list[tuple[float, float, float]] = []
    for plane_vertices, bottom_plane_coordinate in zip(plane_vertices_by_owner, bottom_plane_coordinates):
        selected_diagonal = _selected_diagonal_vertices(plane_vertices=plane_vertices)
        for point_u, point_v in selected_diagonal:
            if plane == "XY":
                diagonal_vertices.append((point_u, point_v, bottom_plane_coordinate))
            else:
                diagonal_vertices.append((bottom_plane_coordinate, point_u, point_v))
    return tuple(diagonal_vertices)


def _single_coil_placement_offset_from_local_bounds(
    *,
    owner_object_id: str,
    owner_origin_xyz: tuple[float, float, float],
    owner_size_xyz: tuple[float, float, float],
    local_bounds_min_xyz: tuple[float, float, float],
    local_size_xyz: tuple[float, float, float],
    profile: SingleCoilProfile,
) -> tuple[float, float, float]:
    plane = profile.plane
    world_size_xyz = profile.world_size(local_size_xyz)
    world_min_delta = profile.world_delta(local_bounds_min_xyz)
    if plane == "XY":
        target_world_min_x = (
            owner_origin_xyz[0]
            if owner_object_id == "tx_region"
            else owner_origin_xyz[0] + (owner_size_xyz[0] - world_size_xyz[0]) / 2.0
        )
        target_world_min_xyz = (
            target_world_min_x,
            owner_origin_xyz[1] + (owner_size_xyz[1] - world_size_xyz[1]) / 2.0,
            owner_origin_xyz[2] + owner_size_xyz[2] - world_size_xyz[2],
        )
    else:
        target_world_min_xyz = (
            owner_origin_xyz[0] + owner_size_xyz[0] - world_size_xyz[0],
            owner_origin_xyz[1] + (owner_size_xyz[1] - world_size_xyz[1]) / 2.0,
            owner_origin_xyz[2],
        )
    return (
        target_world_min_xyz[0] - world_min_delta[0],
        target_world_min_xyz[1] - world_min_delta[1],
        target_world_min_xyz[2] - world_min_delta[2],
    )


def _synthetic_tx_bus_owner_box(
    *,
    local_boxes: tuple[BoxSpec, ...],
    copper_body_prefix: str,
    terminal_column: Literal["start", "end"],
) -> BoxSpec:
    terminal_stub_boxes = tuple(box for box in local_boxes if box.feature == "terminal_stub")
    matching_stub_boxes = tuple(
        box for box in terminal_stub_boxes if box.label.endswith(f"_stub_{terminal_column}")
    )
    if len(matching_stub_boxes) == 0:
        raise RuntimeError(
            "type2 tx port sheet validation requires at least one terminal stub per terminal column "
            f"(terminal_column={terminal_column}, actual=0)"
        )
    if len(matching_stub_boxes) * 2 != len(terminal_stub_boxes):
        raise RuntimeError(
            "type2 tx port sheet validation requires balanced start/end terminal stub boxes "
            f"(terminal_column={terminal_column}, matching={len(matching_stub_boxes)}, total={len(terminal_stub_boxes)})"
        )
    min_x = min(box.origin_xyz[0] for box in matching_stub_boxes)
    min_y = min(box.origin_xyz[1] for box in matching_stub_boxes)
    min_z = min(box.origin_xyz[2] for box in matching_stub_boxes)
    max_x = max(box.origin_xyz[0] + box.size_xyz[0] for box in matching_stub_boxes)
    max_y = max(box.origin_xyz[1] + box.size_xyz[1] for box in matching_stub_boxes)
    max_z = max(box.origin_xyz[2] + box.size_xyz[2] for box in matching_stub_boxes)
    return BoxSpec(
        label=f"{copper_body_prefix}_bus_{terminal_column}",
        role="copper",
        feature="vertical_bus",
        layer_index=0,
        origin_xyz=(min_x, min_y, min_z),
        size_xyz=(max_x - min_x, max_y - min_y, max_z - min_z),
    )


def _local_port_sheet_owner_boxes(
    *,
    local_boxes: tuple[BoxSpec, ...],
    profile: SingleCoilProfile,
) -> tuple[BoxSpec, BoxSpec]:
    role = profile.role
    copper_body_prefix = profile.copper_body_prefix
    if role in TX_PARALLEL_SINGLE_COIL_ROLES:
        return (
            _synthetic_tx_bus_owner_box(
                local_boxes=local_boxes,
                copper_body_prefix=copper_body_prefix,
                terminal_column="start",
            ),
            _synthetic_tx_bus_owner_box(
                local_boxes=local_boxes,
                copper_body_prefix=copper_body_prefix,
                terminal_column="end",
            ),
        )
    terminal_stub_boxes = tuple(box for box in local_boxes if box.feature == "terminal_stub")
    start_matches = [box for box in terminal_stub_boxes if box.label == f"{copper_body_prefix}_l0_stub_start"]
    end_matches = [box for box in terminal_stub_boxes if box.label == f"{copper_body_prefix}_l0_stub_end"]
    if len(start_matches) != 1 or len(end_matches) != 1 or len(terminal_stub_boxes) != 2:
        raise RuntimeError(
            "type2 port sheet validation requires exactly one start/end terminal stub box "
            f"(role={role}, start_matches={len(start_matches)}, end_matches={len(end_matches)}, actual={len(terminal_stub_boxes)})"
        )
    return (start_matches[0], end_matches[0])


def _require_port_sheet_geometry_contract(*, ledger: Type2StepLedger, toml_path: Path, seed: int) -> None:
    spec = load_type2_step_spec(toml_path)
    resolved_non_model_specs = resolve_non_model_scene_specs(
        base_specs=spec.non_model_objects,
        derived_specs=spec.non_model_derived_objects,
        seed=seed,
    )
    for modeled_spec in spec.modeled_objects:
        modeled_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == modeled_spec.object_id)
        terminal_metadata = cast(dict[str, object], modeled_entry["terminal_metadata"])
        owner_spec = require_non_model_object_spec(
            resolved_non_model_specs,
            object_id=placement_owner_id_for_role(modeled_spec.role),
        )
        if isinstance(modeled_spec, (ModeledTxPlateStackSpec, ModeledRxPlateStackSpec)):
            if isinstance(modeled_spec, ModeledTxPlateStackSpec) and resolve_modeled_tx_coil_count(modeled_spec, seed=seed) > 1:
                rx_owner_spec = require_non_model_object_spec(spec.non_model_objects, object_id="rx_region_max")
                _scene_children, expected_scene_data = build_tx_plate_stack_array_scene_data(
                    modeled_spec,
                    owner_spec=owner_spec,
                    rx_owner_spec=rx_owner_spec,
                    seed=seed,
                )
            else:
                _scene_children, expected_scene_data = build_modeled_scene_data(
                    modeled_spec,
                    owner_spec=owner_spec,
                    seed=seed,
                )
            expected_terminal_metadata = expected_scene_data["terminal_metadata"]
            if terminal_metadata != expected_terminal_metadata:
                raise RuntimeError(
                    "type2 plate-stack terminal metadata drifted from geometry contract "
                    f"(object_id={modeled_spec.object_id}, actual={terminal_metadata}, expected={expected_terminal_metadata})"
                )
            continue
        if isinstance(modeled_spec, ModeledTxRectVoidColumnsSpec):
            if "kind" not in terminal_metadata:
                raise RuntimeError(
                    "tx_rect_void_columns terminal metadata must include connection kind sentinel "
                    f"(object_id={modeled_spec.object_id})"
                )
            raw_kind = terminal_metadata["kind"]
            if not isinstance(raw_kind, str):
                raise RuntimeError(
                    "tx_rect_void_columns terminal metadata kind sentinel must be str "
                    f"(object_id={modeled_spec.object_id}, actual={raw_kind!r})"
                )
            if raw_kind == "geometry_only":
                if "connection_status" not in terminal_metadata:
                    raise RuntimeError(
                        "tx_rect_void_columns geometry-only terminal metadata must include connection_status "
                        f"(object_id={modeled_spec.object_id})"
                    )
                raw_status = terminal_metadata["connection_status"]
                if not isinstance(raw_status, str):
                    raise RuntimeError(
                        "tx_rect_void_columns geometry-only terminal metadata connection_status must be str "
                        f"(object_id={modeled_spec.object_id}, actual={raw_status!r})"
                    )
                if raw_status != "skipped_series":
                    raise RuntimeError(
                        "tx_rect_void_columns geometry-only terminal metadata connection_status must be skipped_series "
                        f"(object_id={modeled_spec.object_id}, actual={raw_status!r})"
                    )
                if "tab_face_vertices_xyz" in terminal_metadata:
                    raise RuntimeError(
                        "tx_rect_void_columns geometry-only terminal metadata must not include tab faces "
                        f"(object_id={modeled_spec.object_id})"
                    )
                if "source_label_metadata" in terminal_metadata:
                    raise RuntimeError(
                        "tx_rect_void_columns geometry-only terminal metadata must not include collector labels "
                        f"(object_id={modeled_spec.object_id})"
                    )
                continue
            if raw_kind == "parallel_collector_tabs":
                if "connection_mode" not in terminal_metadata:
                    raise RuntimeError(
                        "tx_rect_void_columns parallel terminal metadata must include connection_mode "
                        f"(object_id={modeled_spec.object_id})"
                    )
                raw_connection_mode = terminal_metadata["connection_mode"]
                if isinstance(raw_connection_mode, bool) or not isinstance(raw_connection_mode, int):
                    raise RuntimeError(
                        "tx_rect_void_columns parallel terminal metadata connection_mode must be int "
                        f"(object_id={modeled_spec.object_id}, actual={raw_connection_mode!r})"
                    )
                if raw_connection_mode != 0:
                    raise RuntimeError(
                        "tx_rect_void_columns parallel terminal metadata connection_mode must be 0 "
                        f"(object_id={modeled_spec.object_id}, actual={raw_connection_mode!r})"
                    )
                if "source_label_metadata" not in terminal_metadata:
                    raise RuntimeError(
                        "tx_rect_void_columns parallel terminal metadata must include collector source labels "
                        f"(object_id={modeled_spec.object_id})"
                    )
                if "tab_face_vertices_xyz" not in terminal_metadata:
                    raise RuntimeError(
                        "tx_rect_void_columns parallel terminal metadata must include tab face vertices "
                        f"(object_id={modeled_spec.object_id})"
                    )
                raw_tab_face_vertices = terminal_metadata["tab_face_vertices_xyz"]
                if not isinstance(raw_tab_face_vertices, tuple):
                    raise RuntimeError(
                        "tx_rect_void_columns parallel terminal metadata tab_face_vertices_xyz must be tuple "
                        f"(object_id={modeled_spec.object_id}, actual={raw_tab_face_vertices!r})"
                    )
                if len(raw_tab_face_vertices) != 2:
                    raise RuntimeError(
                        "tx_rect_void_columns parallel terminal metadata must include exactly two tab face entries "
                        f"(object_id={modeled_spec.object_id}, actual={len(raw_tab_face_vertices)})"
                    )
                if "port_sheet_vertices_xyz" in terminal_metadata:
                    raise RuntimeError(
                        "tx_rect_void_columns parallel terminal metadata must not include per-branch port sheet vertices "
                        f"(object_id={modeled_spec.object_id})"
                    )
                if "branch_balance_audit" not in terminal_metadata:
                    raise RuntimeError(
                        "tx_rect_void_columns parallel terminal metadata must include branch balance audit "
                        f"(object_id={modeled_spec.object_id})"
                    )
                if "overlap_audit" not in terminal_metadata:
                    raise RuntimeError(
                        "tx_rect_void_columns parallel terminal metadata must include overlap audit "
                        f"(object_id={modeled_spec.object_id})"
                    )
                continue
            if raw_kind == "series_collector_tabs":
                if "connection_mode" not in terminal_metadata:
                    raise RuntimeError(
                        "tx_rect_void_columns series terminal metadata must include connection_mode "
                        f"(object_id={modeled_spec.object_id})"
                    )
                raw_connection_mode = terminal_metadata["connection_mode"]
                if isinstance(raw_connection_mode, bool) or not isinstance(raw_connection_mode, int):
                    raise RuntimeError(
                        "tx_rect_void_columns series terminal metadata connection_mode must be int "
                        f"(object_id={modeled_spec.object_id}, actual={raw_connection_mode!r})"
                    )
                if raw_connection_mode != 1:
                    raise RuntimeError(
                        "tx_rect_void_columns series terminal metadata connection_mode must be 1 "
                        f"(object_id={modeled_spec.object_id}, actual={raw_connection_mode!r})"
                    )
                for required_key in (
                    "source_label_metadata",
                    "tab_face_vertices_xyz",
                    "tile_order",
                    "link_labels",
                    "path_length_audit",
                    "overlap_audit",
                ):
                    if required_key not in terminal_metadata:
                        raise RuntimeError(
                            "tx_rect_void_columns series terminal metadata missing required key "
                            f"(object_id={modeled_spec.object_id}, key={required_key})"
                        )
                raw_tab_face_vertices = terminal_metadata["tab_face_vertices_xyz"]
                if not isinstance(raw_tab_face_vertices, tuple):
                    raise RuntimeError(
                        "tx_rect_void_columns series terminal metadata tab_face_vertices_xyz must be tuple "
                        f"(object_id={modeled_spec.object_id}, actual={raw_tab_face_vertices!r})"
                    )
                if len(raw_tab_face_vertices) != 2:
                    raise RuntimeError(
                        "tx_rect_void_columns series terminal metadata must include exactly two tab face entries "
                        f"(object_id={modeled_spec.object_id}, actual={len(raw_tab_face_vertices)})"
                    )
                if "port_sheet_vertices_xyz" in terminal_metadata:
                    raise RuntimeError(
                        "tx_rect_void_columns series terminal metadata must not include reconstructed port sheet vertices "
                        f"(object_id={modeled_spec.object_id})"
                    )
                continue
            raise RuntimeError(
                "tx_rect_void_columns terminal metadata kind sentinel must be geometry_only, parallel_collector_tabs, or series_collector_tabs "
                f"(object_id={modeled_spec.object_id}, actual={raw_kind!r})"
            )
        if "kind" in terminal_metadata:
            raw_kind = terminal_metadata["kind"]
            if not isinstance(raw_kind, str):
                raise RuntimeError(
                    "type2 terminal metadata kind sentinel must be str "
                    f"(object_id={modeled_spec.object_id}, actual={raw_kind!r})"
                )
            raise RuntimeError(
                "type2 terminal metadata kind sentinel is unsupported "
                f"(object_id={modeled_spec.object_id}, kind={raw_kind!r})"
            )
        single_coil_spec = cast(ModeledSingleCoilSpec, modeled_spec)
        profile = profile_for_modeled_role(single_coil_spec.role)
        owner_size_x, owner_size_y, owner_size_z = owner_spec.size_xyz
        if profile.plane == "XY":
            outer_x_owner_span_mm = owner_size_x
            outer_y_owner_span_mm = owner_size_y
        else:
            outer_x_owner_span_mm = owner_size_y
            outer_y_owner_span_mm = owner_size_z
        single_coil_spec = replace(
            single_coil_spec,
            outer_x_mm=RangeSpec(
                is_integer=False,
                start=single_coil_spec.outer_x_usage_ratio.start * outer_x_owner_span_mm,
                end=single_coil_spec.outer_x_usage_ratio.end * outer_x_owner_span_mm,
                count=single_coil_spec.outer_x_usage_ratio.count,
            ),
            outer_y_mm=RangeSpec(
                is_integer=False,
                start=single_coil_spec.outer_y_usage_ratio.start * outer_y_owner_span_mm,
                end=single_coil_spec.outer_y_usage_ratio.end * outer_y_owner_span_mm,
                count=single_coil_spec.outer_y_usage_ratio.count,
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            tx_rect_void_toml_path = Path(temp_dir) / f"{single_coil_spec.object_id}.toml"
            tx_rect_void_toml_path.write_text(render_tx_rect_void_toml(single_coil_spec), encoding="utf-8")
            tx_rect_void_spec = load_tx_rect_void_spec(tx_rect_void_toml_path)
            realized = realize_tx_rect_void_spec(tx_rect_void_spec, seed=seed, profile=profile)
        local_boxes = build_tx_rect_void_box_specs(realized, profile=profile)
        local_bounds_min_xyz, _local_bounds_max_xyz, local_size_xyz = modeled_body_bounds_from_boxes(local_boxes)
        frame_origin_xyz = _single_coil_placement_offset_from_local_bounds(
            owner_object_id=owner_spec.object_id,
            owner_origin_xyz=owner_spec.origin_xyz,
            owner_size_xyz=owner_spec.size_xyz,
            local_bounds_min_xyz=local_bounds_min_xyz,
            local_size_xyz=local_size_xyz,
            profile=profile,
        )
        owner_boxes = _local_port_sheet_owner_boxes(local_boxes=local_boxes, profile=profile)
        transformed_owner_boxes = tuple(
            (
                profile.world_point(box.origin_xyz, frame_origin_xyz=frame_origin_xyz),
                profile.world_size(box.size_xyz),
            )
            for box in owner_boxes
        )
        if single_coil_spec.role in TX_PARALLEL_SINGLE_COIL_ROLES:
            sheet_label = f"{profile.copper_body_prefix.removesuffix('_copper')}_port_sheet"
        else:
            sheet_label = "rx_port_sheet"
        raw_sheet_vertices = cast(
            tuple[tuple[float, float, float], ...],
            terminal_metadata["port_sheet_vertices_xyz"],
        )
        if len(raw_sheet_vertices) != 4:
            raise RuntimeError(
                "type2 port sheet metadata must contain exactly four unique vertices "
                f"(object_id={modeled_spec.object_id}, actual={len(raw_sheet_vertices)})"
            )
        sheet_vertices = tuple((float(vertex[0]), float(vertex[1]), float(vertex[2])) for vertex in raw_sheet_vertices)
        expected_vertices = _widest_owner_bottom_face_diagonal_vertices(
            transformed_owner_boxes=transformed_owner_boxes,
            plane=profile.plane,
        )
        if profile.plane == "XY":
            plane_coordinates = tuple(vertex[2] for vertex in sheet_vertices)
        else:
            plane_coordinates = tuple(vertex[0] for vertex in sheet_vertices)
        if max(plane_coordinates) - min(plane_coordinates) > 1e-8:
            raise RuntimeError(
                "type2 port sheet vertices must lie on one shared bottom-face plane "
                f"(object_id={modeled_spec.object_id}, label={sheet_label}, plane_values={plane_coordinates})"
            )
        actual_vertex_set = {
            (round(vertex[0], 8), round(vertex[1], 8), round(vertex[2], 8))
            for vertex in sheet_vertices
        }
        expected_vertex_set = {
            (round(vertex[0], 8), round(vertex[1], 8), round(vertex[2], 8))
            for vertex in expected_vertices
        }
        if actual_vertex_set != expected_vertex_set:
            raise RuntimeError(
                "type2 port sheet must bridge the widened bottom-face diagonals of both owner boxes "
                f"(object_id={modeled_spec.object_id}, label={sheet_label}, "
                f"actual_vertices={sorted(actual_vertex_set)}, expected_vertices={sorted(expected_vertex_set)})"
            )


def export_type2_step_artifacts(
    *,
    toml_path: Path = SOURCE_TOML_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    seed: int = 0,
    stage_reporter: Callable[[_Type2StepExportStage], None] = _no_op_type2_step_export_stage_reporter,
) -> Type2StepLedger:
    spec = load_type2_step_spec(toml_path)
    _raise_if_modeled_tx_role_present(
        spec=spec,
        context="type2 STEP export",
    )
    em_policy: Type2ImportEmPolicy = {
        "radiation_margin_mm": spec.simulation.radiation_margin_mm,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _remove_generated_type2_artifacts(output_dir)
    scene_step_path = output_dir / DEFAULT_SCENE_STEP_PATH.name
    object_metadata_dir = output_dir / "metadata"

    stage_reporter("build_scene")
    resolved_non_model_specs = resolve_non_model_scene_specs(
        base_specs=spec.non_model_objects,
        derived_specs=spec.non_model_derived_objects,
        seed=seed,
    )

    modeled_scene_data: list[ModeledObjectSceneData] = []
    modeled_scene_shapes: list[bd.Shape] = []
    modeled_entries = []
    for modeled_spec in spec.modeled_objects:
        owner_spec = require_non_model_object_spec(
            resolved_non_model_specs,
            object_id=placement_owner_id_for_role(modeled_spec.role),
        )
        metadata_path = object_metadata_dir / f"{modeled_spec.object_id}.metadata.json"
        current_modeled_scene_shapes, scene_data = build_modeled_scene_data(
            modeled_spec,
            owner_spec=owner_spec,
            seed=seed,
        )
        write_modeled_source_metadata(
            metadata_path=metadata_path,
            source_toml_path=toml_path,
            scene_step_path=scene_step_path,
            scene_data=scene_data,
        )
        modeled_entry = build_modeled_object_ledger_entry(
            scene_data=scene_data,
            source_metadata_path=metadata_path,
        )
        modeled_scene_data.append(scene_data)
        modeled_scene_shapes.extend(current_modeled_scene_shapes)
        modeled_entries.append(modeled_entry)

    rx_modeled_scene_data = tuple(scene_data for scene_data in modeled_scene_data if _is_modeled_rx_object(role=scene_data["role"]))
    if len(rx_modeled_scene_data) == 1:
        rx_center = _resolve_modeled_rx_center_from_scene_data(
            modeled_scene_data=tuple(modeled_scene_data),
        )
    elif len(rx_modeled_scene_data) == 0:
        rx_region_max_spec = require_non_model_object_spec(resolved_non_model_specs, object_id="rx_region_max")
        rx_center = (
            rx_region_max_spec.origin_xyz[0] + (rx_region_max_spec.size_xyz[0] * 0.5),
            rx_region_max_spec.origin_xyz[1] + (rx_region_max_spec.size_xyz[1] * 0.5),
            rx_region_max_spec.origin_xyz[2] + (rx_region_max_spec.size_xyz[2] * 0.5),
        )
    else:
        raise RuntimeError(
            "type2 tilt-enabled tx_region_actual_stack_space requires exactly one modeled RX object when present "
            f"(actual={len(rx_modeled_scene_data)})"
        )
    non_model_entry, non_model_scene_shapes, stack_space_tilt_placements = _build_non_model_scene_entry_and_shapes(
        resolved_non_model_specs=resolved_non_model_specs,
        tilt_enabled=1,
        rx_center=rx_center,
    )
    if stack_space_tilt_placements:
        raise RuntimeError(
            "active Type2 RxOnly export must not create tx_region_actual_stack_space placement metadata "
            f"(actual={tuple(stack_space_tilt_placements)})"
        )

    non_model_entries = [non_model_entry]
    scene_shapes = [*non_model_scene_shapes, *modeled_scene_shapes]

    scene_body_names = tuple(shape.label for shape in scene_shapes)
    if len(scene_body_names) != len(set(scene_body_names)):
        raise RuntimeError(f"type2 scene STEP body names must be unique (actual={scene_body_names})")
    _require_plate_stack_merged_scene_shape_contract(scene_shapes=tuple(scene_shapes))
    for shape in scene_shapes:
        _validate_top_level_scene_child(shape)
    scene = bd.Compound(children=scene_shapes, label="type2_scene")
    stage_reporter("export_scene_step")
    export_ok = bd.export_step(scene, scene_step_path)
    if export_ok is not True:
        raise RuntimeError(f"build123d export_step returned False for type2 scene STEP: {scene_step_path}")

    stage_reporter("finalize_step_artifacts")
    ledger = build_type2_step_ledger(
        source_toml_path=spec.source_toml_path,
        output_dir=output_dir,
        scene_step_path=scene_step_path,
        seed=seed,
        em_policy=em_policy,
        outputs=spec.outputs,
        non_model_objects=non_model_entries,
        modeled_objects=modeled_entries,
    )
    write_type2_step_ledger(ledger_path=ledger_path, ledger=ledger)
    _require_modeled_expected_body_contract(ledger, spec=spec, seed=seed)
    _require_port_sheet_geometry_contract(ledger=ledger, toml_path=toml_path, seed=seed)
    return ledger


__all__ = [
    "DEFAULT_LEDGER_PATH",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_SCENE_STEP_PATH",
    "REPO_ROOT",
    "SOURCE_TOML_PATH",
    "Type2DirectModeledArtifact",
    "Type2StepLedger",
    "export_type2_step_artifacts",
    "export_type2_tx_single_coil_artifact",
]

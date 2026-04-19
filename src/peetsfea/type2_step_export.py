from __future__ import annotations

import math
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Literal, cast

import build123d as bd

from peetsfea.tx_rect_void import BoxSpec
from peetsfea.tx_rect_void import SingleCoilProfile
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
from peetsfea.type2_step_ledger import build_modeled_object_ledger_entry
from peetsfea.type2_step_ledger import build_type2_step_ledger
from peetsfea.type2_step_ledger import write_modeled_source_metadata
from peetsfea.type2_step_ledger import write_type2_step_ledger
from peetsfea.type2_step_scene import build_modeled_scene_data
from peetsfea.type2_step_scene import build_modeled_single_coil_scene_data
from peetsfea.type2_step_scene import build_non_model_scene_entry
from peetsfea.type2_step_scene import build_non_model_scene_shapes
from peetsfea.type2_step_scene import require_non_model_object_spec
from peetsfea.type2_step_spec import ModeledRxPlateStackSpec
from peetsfea.type2_step_spec import ModeledRxSingleCoilSpec
from peetsfea.type2_step_spec import ModeledSingleCoilSpec
from peetsfea.type2_step_spec import Type2StepSpec
from peetsfea.type2_step_spec import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import load_type2_step_spec
from peetsfea.type2_step_spec import placement_owner_id_for_role
from peetsfea.type2_step_spec import render_tx_rect_void_toml
from peetsfea.type2_step_spec import resolve_modeled_plate_stack_turn_count
from peetsfea.type2_step_spec import resolve_modeled_tx_coil_count
from peetsfea.type2_step_spec import resolve_modeled_underlay_repeat_count
from peetsfea.type2_step_spec import resolve_modeled_wall_parallel_stack_present
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
_Type2StepExportStage = Literal["build_scene", "export_scene_step", "finalize_step_artifacts"]


def _no_op_type2_step_export_stage_reporter(stage: _Type2StepExportStage) -> None:
    pass


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


def _export_modeled_single_coil(
    spec: ModeledTxSingleCoilSpec,
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
        target_world_min_xyz = (
            owner_origin_xyz[0],
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
    if role == "tx_single_coil":
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
    for modeled_spec in spec.modeled_objects:
        modeled_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == modeled_spec.object_id)
        terminal_metadata = cast(dict[str, object], modeled_entry["terminal_metadata"])
        owner_spec = next(
            non_model for non_model in spec.non_model_objects if non_model.object_id == placement_owner_id_for_role(modeled_spec.role)
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
        with tempfile.TemporaryDirectory() as temp_dir:
            tx_rect_void_toml_path = Path(temp_dir) / f"{single_coil_spec.object_id}.toml"
            tx_rect_void_toml_path.write_text(render_tx_rect_void_toml(single_coil_spec), encoding="utf-8")
            tx_rect_void_spec = load_tx_rect_void_spec(tx_rect_void_toml_path)
            realized = realize_tx_rect_void_spec(tx_rect_void_spec, seed=seed, profile=profile)
        local_boxes = build_tx_rect_void_box_specs(realized, profile=profile)
        local_bounds_min_xyz, _local_bounds_max_xyz, local_size_xyz = modeled_body_bounds_from_boxes(local_boxes)
        frame_origin_xyz = _single_coil_placement_offset_from_local_bounds(
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
        sheet_label = "tx_port_sheet" if single_coil_spec.role == "tx_single_coil" else "rx_port_sheet"
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
    em_policy: Type2ImportEmPolicy = {
        "radiation_margin_mm": spec.simulation.radiation_margin_mm,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _remove_generated_type2_artifacts(output_dir)
    scene_step_path = output_dir / DEFAULT_SCENE_STEP_PATH.name
    object_metadata_dir = output_dir / "metadata"

    stage_reporter("build_scene")
    non_model_entries = [build_non_model_scene_entry(spec.non_model_objects)]
    scene_shapes: list[bd.Shape] = list(build_non_model_scene_shapes(spec.non_model_objects))
    modeled_entries = []
    for modeled_spec in spec.modeled_objects:
        owner_spec = require_non_model_object_spec(
            spec.non_model_objects,
            object_id=placement_owner_id_for_role(modeled_spec.role),
        )
        metadata_path = object_metadata_dir / f"{modeled_spec.object_id}.metadata.json"
        if isinstance(modeled_spec, ModeledTxPlateStackSpec):
            rx_owner_spec = require_non_model_object_spec(spec.non_model_objects, object_id="rx_region_max")
            modeled_scene_shapes, scene_data = build_tx_plate_stack_array_scene_data(
                modeled_spec,
                owner_spec=owner_spec,
                rx_owner_spec=rx_owner_spec,
                seed=seed,
            )
        else:
            modeled_scene_shapes, scene_data = build_modeled_scene_data(
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
        scene_shapes.extend(modeled_scene_shapes)
        modeled_entries.append(modeled_entry)

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

from __future__ import annotations

import argparse
import math
import sys
import tempfile
from pathlib import Path

import build123d as bd

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.type2_step_export import DEFAULT_LEDGER_PATH
from peetsfea.type2_step_export import DEFAULT_OUTPUT_DIR
from peetsfea.type2_step_export import DEFAULT_SCENE_STEP_PATH
from peetsfea.type2_step_export import SOURCE_TOML_PATH
from peetsfea.type2_step_export import Type2DirectModeledArtifact
from peetsfea.type2_step_export import Type2StepLedger
from peetsfea.type2_step_export import export_type2_step_artifacts as _core_export_type2_step_artifacts
from peetsfea.type2_step_export import export_type2_tx_single_coil_artifact
from peetsfea.tx_rect_void import build_tx_rect_void_box_specs
from peetsfea.tx_rect_void import load_tx_rect_void_spec
from peetsfea.tx_rect_void import modeled_body_bounds_from_boxes
from peetsfea.tx_rect_void import profile_for_modeled_role
from peetsfea.tx_rect_void import realize_tx_rect_void_spec
from peetsfea.type2_step_spec import Type2StepSpec
from peetsfea.type2_step_spec import load_type2_step_spec
from peetsfea.type2_step_spec import render_tx_rect_void_toml


def _require_single_coil_expected_body_contract(ledger: Type2StepLedger) -> None:
    for modeled_entry in ledger["modeled_objects"]:
        role = modeled_entry["role"]
        expected_body_names = modeled_entry["expected_exported_body_names"]
        expected_body_count = modeled_entry["expected_exported_body_count"]
        if role == "tx_single_coil":
            pcb_layer_positions = modeled_entry["canonical_coordinates"]["pcb_layer_z_positions_mm"]
            if len(pcb_layer_positions) != 1:
                continue
            expected_names = ["tx_pcb_l0", "tx_copper_l0", "tx_port_sheet"]
        elif role == "rx_single_coil":
            expected_names = ["rx_pcb_l0", "rx_copper_l0", "rx_port_sheet"]
        else:
            raise ValueError(f"unsupported modeled object role in type2 ledger: {role}")
        if list(expected_body_names) != expected_names:
            raise ValueError(
                "type2 single-coil export expected body contract mismatch "
                f"(role={role}, expected={expected_names}, actual={list(expected_body_names)})"
            )
        if expected_body_count != len(expected_names):
            raise ValueError(
                "type2 single-coil export expected body count mismatch "
                f"(role={role}, expected={len(expected_names)}, actual={expected_body_count})"
            )

def _shape_vertices(scene_step_path: Path, *, label: str) -> tuple[tuple[float, float, float], ...]:
    scene = bd.import_step(scene_step_path)
    children = tuple(scene.children) if tuple(scene.children) else (scene,)
    matches = [child for child in children if child.label == label]
    if len(matches) != 1:
        raise RuntimeError(f"type2 scene STEP must contain exactly one body with label {label} (actual={len(matches)})")
    unique_vertices: dict[tuple[float, float, float], tuple[float, float, float]] = {}
    for vertex in matches[0].vertices():
        rounded = (round(vertex.X, 8), round(vertex.Y, 8), round(vertex.Z, 8))
        if rounded not in unique_vertices:
            unique_vertices[rounded] = (vertex.X, vertex.Y, vertex.Z)
    return tuple(unique_vertices.values())


def _terminal_stub_bottom_face_square_plane_vertices(
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
            "type2 port sheet widened diagonal validation requires positive terminal-stub bottom-face dimensions "
            f"(plane={plane}, origin={box_origin_xyz}, size={box_size_xyz})"
        )
    if abs(square_side_a - square_side_b) > 1e-8:
        raise RuntimeError(
            "type2 port sheet widened diagonal validation requires square terminal-stub bottom faces "
            f"(plane={plane}, origin={box_origin_xyz}, size={box_size_xyz})"
        )
    return (plane_vertices, bottom_plane_coordinate)


def _stub_centerline_perpendicular_distance(
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
            "type2 port sheet widened diagonal validation requires distinct terminal-stub centers "
            f"(first_center={first_center_xy}, second_center={second_center_xy})"
        )
    numerator = abs(
        delta_x * (first_center_xy[1] - point_xy[1])
        - (first_center_xy[0] - point_xy[0]) * delta_y
    )
    return numerator / denominator


def _widest_stub_bottom_face_diagonal_vertices(
    *,
    transformed_terminal_stub_boxes: tuple[tuple[tuple[float, float, float], tuple[float, float, float]], ...],
    plane: str,
) -> tuple[tuple[float, float, float], ...]:
    if len(transformed_terminal_stub_boxes) != 2:
        raise RuntimeError(
            "type2 port sheet widened diagonal validation requires exactly two terminal stub boxes "
            f"(actual={len(transformed_terminal_stub_boxes)})"
        )
    plane_vertices_by_stub: list[tuple[tuple[float, float], ...]] = []
    bottom_plane_coordinates: list[float] = []
    stub_center_points: list[tuple[float, float]] = []
    for box_origin_xyz, box_size_xyz in transformed_terminal_stub_boxes:
        plane_vertices, bottom_plane_coordinate = _terminal_stub_bottom_face_square_plane_vertices(
            box_origin_xyz=box_origin_xyz,
            box_size_xyz=box_size_xyz,
            plane=plane,
        )
        plane_vertices_by_stub.append(plane_vertices)
        bottom_plane_coordinates.append(bottom_plane_coordinate)
        stub_center_points.append(
            (
                sum(point_xy[0] for point_xy in plane_vertices) / 4.0,
                sum(point_xy[1] for point_xy in plane_vertices) / 4.0,
            )
        )
    if max(bottom_plane_coordinates) - min(bottom_plane_coordinates) > 1e-8:
        raise RuntimeError(
            "type2 terminal stub bottom faces must share one plane for widened sheet derivation "
            f"(plane={plane}, plane_values={bottom_plane_coordinates})"
        )

    def _selected_diagonal_vertices(
        *,
        plane_vertices: tuple[tuple[float, float], ...],
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        best_score = -1.0
        best_diagonal: tuple[tuple[float, float], tuple[float, float]] | None = None
        best_key: tuple[tuple[float, float], tuple[float, float]] | None = None
        for first_index, second_index in ((0, 2), (1, 3)):
            diagonal_vertices = (plane_vertices[first_index], plane_vertices[second_index])
            score = sum(
                _stub_centerline_perpendicular_distance(
                    point_xy=point_xy,
                    first_center_xy=stub_center_points[0],
                    second_center_xy=stub_center_points[1],
                )
                for point_xy in diagonal_vertices
            )
            candidate_key = tuple(sorted(diagonal_vertices))
            if (
                score > best_score + 1e-9
                or (abs(score - best_score) <= 1e-9 and (best_key is None or candidate_key < best_key))
            ):
                best_score = score
                best_diagonal = diagonal_vertices
                best_key = candidate_key
        if best_diagonal is None:
            raise RuntimeError("type2 widened terminal-stub diagonal selection produced no candidate")
        return best_diagonal

    diagonal_vertices: list[tuple[float, float, float]] = []
    for plane_vertices, bottom_plane_coordinate in zip(plane_vertices_by_stub, bottom_plane_coordinates):
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
    profile: object,
) -> tuple[float, float, float]:
    assert hasattr(profile, "plane")
    assert hasattr(profile, "world_size")
    assert hasattr(profile, "world_delta")
    plane = profile.plane
    world_size_xyz = profile.world_size(local_size_xyz)
    world_min_delta = profile.world_delta(local_bounds_min_xyz)
    if plane == "XY":
        target_world_min_xyz = (
            owner_origin_xyz[0] + (owner_size_xyz[0] - world_size_xyz[0]) / 2.0,
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


def _require_port_sheet_geometry_contract(*, ledger: Type2StepLedger, toml_path: Path, seed: int) -> None:
    spec = load_type2_step_spec(toml_path)
    scene_step_path = Path(ledger["scene_step_path"])
    for modeled_spec in spec.modeled_objects:
        profile = profile_for_modeled_role(modeled_spec.role)
        if modeled_spec.role == "tx_single_coil" and int(modeled_spec.layer_count.start) != 1:
            continue
        owner_spec = next(non_model for non_model in spec.non_model_objects if non_model.object_id == profile.placement_owner_id)
        with tempfile.TemporaryDirectory() as temp_dir:
            tx_rect_void_toml_path = Path(temp_dir) / f"{modeled_spec.object_id}.toml"
            tx_rect_void_toml_path.write_text(render_tx_rect_void_toml(modeled_spec), encoding="utf-8")
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
        terminal_stub_boxes = tuple(box for box in local_boxes if box.feature == "terminal_stub")
        transformed_terminal_stub_boxes = tuple(
            (
                profile.world_point(box.origin_xyz, frame_origin_xyz=frame_origin_xyz),
                profile.world_size(box.size_xyz),
            )
            for box in terminal_stub_boxes
        )
        sheet_label = "tx_port_sheet" if modeled_spec.role == "tx_single_coil" else "rx_port_sheet"
        sheet_vertices = _shape_vertices(scene_step_path, label=sheet_label)
        if len(sheet_vertices) != 4:
            raise RuntimeError(
                "type2 port sheet must export exactly four unique vertices "
                f"(object_id={modeled_spec.object_id}, label={sheet_label}, actual={len(sheet_vertices)})"
            )
        expected_vertices = _widest_stub_bottom_face_diagonal_vertices(
            transformed_terminal_stub_boxes=transformed_terminal_stub_boxes,
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
                "type2 port sheet must bridge the widened bottom-face diagonals of both terminal stubs "
                f"(object_id={modeled_spec.object_id}, label={sheet_label}, "
                f"actual_vertices={sorted(actual_vertex_set)}, expected_vertices={sorted(expected_vertex_set)})"
            )


def export_type2_step_artifacts(
    *,
    toml_path: Path = SOURCE_TOML_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    seed: int = 0,
) -> Type2StepLedger:
    ledger = _core_export_type2_step_artifacts(
        toml_path=toml_path,
        output_dir=output_dir,
        ledger_path=ledger_path,
        seed=seed,
    )
    _require_single_coil_expected_body_contract(ledger)
    _require_port_sheet_geometry_contract(ledger=ledger, toml_path=toml_path, seed=seed)
    return ledger


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate type2 STEP artifacts from examples/type2_fixed.toml.")
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
    print(f"scene STEP: {ledger['scene_step_path']}")
    print(f"ledger JSON: {args.ledger}")
    print(f"non-model object count: {len(ledger['non_model_objects'])}")
    print(f"modeled object count: {len(ledger['modeled_objects'])}")
    return ledger


__all__ = [
    "DEFAULT_LEDGER_PATH",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_SCENE_STEP_PATH",
    "SOURCE_TOML_PATH",
    "Type2DirectModeledArtifact",
    "Type2StepLedger",
    "Type2StepSpec",
    "export_type2_step_artifacts",
    "export_type2_tx_single_coil_artifact",
    "load_type2_step_spec",
    "main",
    "parse_args",
]


if __name__ == "__main__":
    main()

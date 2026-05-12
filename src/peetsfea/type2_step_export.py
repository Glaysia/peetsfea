from __future__ import annotations

import math
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Literal, NoReturn, cast

import build123d as bd
from build123d.topology import Shape

from peetsfea.tx_rect_void import BoxSpec
from peetsfea.tx_rect_void import profile_for_modeled_role
from peetsfea.type2_plate_stack import expected_plate_stack_body_groups
from peetsfea.type2_plate_stack import expected_plate_stack_body_names
from peetsfea.type2_step_ledger import Type2DirectModeledArtifact
from peetsfea.type2_step_ledger import Type2ImportEmPolicy
from peetsfea.type2_step_ledger import Type2StepLedger
from peetsfea.type2_step_ledger import NonModelObjectLedgerEntry
from peetsfea.type2_step_ledger import NonModelSceneMemberEntry
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
from peetsfea.type2_non_model_scene import require_non_model_object_spec
from peetsfea.type2_non_model_scene import resolve_non_model_scene_specs
from peetsfea.type2_step_scene import build_modeled_scene_data
from peetsfea.type2_step_scene import build_modeled_single_coil_scene_data
from peetsfea.type2_step_spec import ModeledRxPlateStackSpec
from peetsfea.type2_step_spec import ModeledRxSingleCoilSpec
from peetsfea.type2_step_spec import ModeledTxRectVoidColumnsSpec
from peetsfea.type2_step_spec import ModeledTxInnerSingleCoilSpec
from peetsfea.type2_step_spec import Type2StepSpec
from peetsfea.type2_step_spec import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec import ModeledTxSingleCoilSpec
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import Point3
from peetsfea.type2_step_spec import ModeledTvAluminumPlateSpec
from peetsfea.type2_step_spec import load_type2_step_spec
from peetsfea.type2_step_spec import placement_owner_id_for_role
from peetsfea.type2_step_spec import resolve_modeled_plate_stack_turn_count
from peetsfea.type2_step_spec import resolve_modeled_tx_coil_count
from peetsfea.type2_step_spec import resolve_modeled_tx_inner_void_stack_present
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
from peetsfea.type2_tx_plate_stack_array import expected_tx_plate_stack_array_body_groups
from peetsfea.type2_tx_plate_stack_array import expected_tx_plate_stack_array_body_names

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_TOML_PATH = REPO_ROOT / "examples" / "type2_fixed.toml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "run" / "step" / "type2"
DEFAULT_LEDGER_PATH = DEFAULT_OUTPUT_DIR / "type2_step_ledger.json"
DEFAULT_SCENE_STEP_PATH = DEFAULT_OUTPUT_DIR / "type2_scene.step"
_TX_FERRITE_GROUP_NAME = "g_ferrite_tx"
_TX_OUTER_FERRITE_GROUP_NAME = "g_ferrite_tx_outer"
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
_TX_RECT_VOID_COLUMNS_TERMINAL_STUB_SIDE_RATIO = 0.60
_TX_POSITIVE_BRIDGE_PCB_OBJECT_ID = "tx_pos_bridge_pcb"
_TX_POSITIVE_BRIDGE_COPPER_OBJECT_ID = "tx_pos_bridge_copper"
_TX_POSITIVE_BRIDGE_ROLE = "tx_inner_outer_positive_bridge"
_TX_NEGATIVE_BRIDGE_PCB_OBJECT_ID = "tx_neg_bridge_pcb"
_TX_NEGATIVE_BRIDGE_COPPER_OBJECT_ID = "tx_neg_bridge_copper"
_TX_NEGATIVE_BRIDGE_ROLE = "tx_inner_outer_negative_bridge"
_TX_TERMINAL_BRIDGE_PCB_THICKNESS_MM = 0.365
_TX_TERMINAL_BRIDGE_COPPER_THICKNESS_MM = 0.035
_TX_TERMINAL_BRIDGE_TOTAL_THICKNESS_MM = 0.400
_Type2StepExportStage = Literal["build_scene", "export_scene_step", "finalize_step_artifacts"]
_TxTerminalBridgePolarity = Literal["positive", "negative"]


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


def _active_step_export_modeled_specs(
    *,
    spec: Type2StepSpec,
) -> tuple[
    ModeledRxPlateStackSpec
    | ModeledRxSingleCoilSpec
    | ModeledTxInnerSingleCoilSpec
    | ModeledTxPlateStackSpec
    | ModeledTvAluminumPlateSpec
    | ModeledTxRectVoidColumnsSpec
    | ModeledTxSingleCoilSpec,
    ...,
]:
    return tuple(
        modeled_spec
        for modeled_spec in spec.modeled_objects
        if modeled_spec.role != "tx_outer_single_coil"
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


def _validate_top_level_scene_child(shape: Shape) -> None:
    children = tuple(shape.children)
    if children:
        for child in children:
            _validate_top_level_scene_child(cast(Shape, child))
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


def _require_finite_float(value: object, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"{context} must be a numeric scalar (actual={value!r})")
    checked_value = float(value)
    if not math.isfinite(checked_value):
        raise RuntimeError(f"{context} must be finite (actual={checked_value!r})")
    return checked_value


def _require_point3_triplet(value: object, *, context: str) -> Point3:
    if isinstance(value, (str, bytes)) or not isinstance(value, (tuple, list)):
        raise RuntimeError(f"{context} must be a 3D point tuple")
    if len(value) != 3:
        raise RuntimeError(f"{context} must contain exactly 3 entries (actual={len(value)})")
    return (
        _require_finite_float(value[0], context=f"{context}[0]"),
        _require_finite_float(value[1], context=f"{context}[1]"),
        _require_finite_float(value[2], context=f"{context}[2]"),
    )


def _require_port_sheet_vertices_xyz(
    *,
    value: object,
    context: str,
) -> tuple[Point3, Point3, Point3, Point3]:
    if not isinstance(value, (tuple, list)):
        raise RuntimeError(f"{context} must be a sequence of four 3D points")
    if len(value) != 4:
        raise RuntimeError(
            "tx terminal bridge requires exactly four terminal sheet vertices "
            f"(actual={len(value)}, context={context})"
        )
    return (
        _require_point3_triplet(value[0], context=f"{context}[0]"),
        _require_point3_triplet(value[1], context=f"{context}[1]"),
        _require_point3_triplet(value[2], context=f"{context}[2]"),
        _require_point3_triplet(value[3], context=f"{context}[3]"),
    )


def _edge_length_sq(start_xyz: Point3, end_xyz: Point3) -> float:
    delta_x = end_xyz[0] - start_xyz[0]
    delta_y = end_xyz[1] - start_xyz[1]
    delta_z = end_xyz[2] - start_xyz[2]
    return (delta_x * delta_x) + (delta_y * delta_y) + (delta_z * delta_z)


def _triangle_area_sq_from_points(*, points: tuple[Point3, Point3, Point3], context: str) -> float:
    start_xyz, mid_xyz, end_xyz = points
    vector_a = (
        mid_xyz[0] - start_xyz[0],
        mid_xyz[1] - start_xyz[1],
        mid_xyz[2] - start_xyz[2],
    )
    vector_b = (
        end_xyz[0] - start_xyz[0],
        end_xyz[1] - start_xyz[1],
        end_xyz[2] - start_xyz[2],
    )
    cross_x = (vector_a[1] * vector_b[2]) - (vector_a[2] * vector_b[1])
    cross_y = (vector_a[2] * vector_b[0]) - (vector_a[0] * vector_b[2])
    cross_z = (vector_a[0] * vector_b[1]) - (vector_a[1] * vector_b[0])
    area_sq = (cross_x * cross_x) + (cross_y * cross_y) + (cross_z * cross_z)
    if area_sq <= 0.0:
        raise RuntimeError(f"tx terminal bridge triangle area is degenerate (context={context})")
    return area_sq


def _cross_product(
    *,
    left_vector: Point3,
    right_vector: Point3,
) -> Point3:
    return (
        (left_vector[1] * right_vector[2]) - (left_vector[2] * right_vector[1]),
        (left_vector[2] * right_vector[0]) - (left_vector[0] * right_vector[2]),
        (left_vector[0] * right_vector[1]) - (left_vector[1] * right_vector[0]),
    )


def _dot_product(
    *,
    left_vector: Point3,
    right_vector: Point3,
) -> float:
    return (
        (left_vector[0] * right_vector[0])
        + (left_vector[1] * right_vector[1])
        + (left_vector[2] * right_vector[2])
    )


def _normalize_vector(
    *,
    vector: Point3,
    context: str,
) -> Point3:
    norm_sq = (vector[0] * vector[0]) + (vector[1] * vector[1]) + (vector[2] * vector[2])
    if norm_sq <= 0.0:
        raise RuntimeError(f"tx terminal bridge normal vector is degenerate (context={context})")
    inverse_norm = 1.0 / math.sqrt(norm_sq)
    return (
        vector[0] * inverse_norm,
        vector[1] * inverse_norm,
        vector[2] * inverse_norm,
    )


def _ledger_plane_from_extrusion_axis(
    *,
    extrusion_axis: Point3,
) -> Literal["XY", "YZ", "ZX", "mixed"]:
    if abs(extrusion_axis[0]) >= (1.0 - 1e-9) and abs(extrusion_axis[0]) >= abs(extrusion_axis[1]) and abs(extrusion_axis[0]) >= abs(extrusion_axis[2]):
        return "YZ"
    if abs(extrusion_axis[1]) >= (1.0 - 1e-9) and abs(extrusion_axis[1]) >= abs(extrusion_axis[0]) and abs(extrusion_axis[1]) >= abs(extrusion_axis[2]):
        return "ZX"
    if abs(extrusion_axis[2]) >= (1.0 - 1e-9) and abs(extrusion_axis[2]) >= abs(extrusion_axis[0]) and abs(extrusion_axis[2]) >= abs(extrusion_axis[1]):
        return "XY"
    return "mixed"


def _bridge_extrusion_axis_from_polygon(
    *,
    polygon: tuple[Point3, Point3, Point3, Point3],
    context: str,
) -> Point3:
    tri0_raw_normal = _cross_product(
        left_vector=(
            polygon[1][0] - polygon[0][0],
            polygon[1][1] - polygon[0][1],
            polygon[1][2] - polygon[0][2],
        ),
        right_vector=(
            polygon[2][0] - polygon[0][0],
            polygon[2][1] - polygon[0][1],
            polygon[2][2] - polygon[0][2],
        ),
    )
    tri1_raw_normal = _cross_product(
        left_vector=(
            polygon[2][0] - polygon[0][0],
            polygon[2][1] - polygon[0][1],
            polygon[2][2] - polygon[0][2],
        ),
        right_vector=(
            polygon[3][0] - polygon[0][0],
            polygon[3][1] - polygon[0][1],
            polygon[3][2] - polygon[0][2],
        ),
    )
    tri0_area_sq = _triangle_area_sq_from_points(
        points=(polygon[0], polygon[1], polygon[2]),
        context=f"{context}[triangle0]",
    )
    tri1_area_sq = _triangle_area_sq_from_points(
        points=(polygon[0], polygon[2], polygon[3]),
        context=f"{context}[triangle1]",
    )
    if tri0_area_sq <= 1e-24 or tri1_area_sq <= 1e-24:
        raise RuntimeError(f"tx terminal bridge bridge mesh triangles must have non-zero area (context={context})")
    tri0_normal = _normalize_vector(
        vector=tri0_raw_normal,
        context=f"{context}[triangle0]_normal",
    )
    tri1_normal = _normalize_vector(
        vector=tri1_raw_normal,
        context=f"{context}[triangle1]_normal",
    )
    normal_dot = _dot_product(left_vector=tri0_normal, right_vector=tri1_normal)
    if normal_dot < 0.0:
        tri1_normal = (
            -tri1_normal[0],
            -tri1_normal[1],
            -tri1_normal[2],
        )
        normal_dot = -normal_dot
    if normal_dot <= 1e-12:
        raise RuntimeError(f"tx terminal bridge triangle normals are incoherent (context={context})")
    return _normalize_vector(
        vector=(
            0.5 * (tri0_normal[0] + tri1_normal[0]),
            0.5 * (tri0_normal[1] + tri1_normal[1]),
            0.5 * (tri0_normal[2] + tri1_normal[2]),
        ),
        context=f"{context}_averaged_normal",
    )


def _terminal_edge_from_port_sheet(
    *,
    vertices: tuple[Point3, Point3, Point3, Point3],
    start_vertex_index: int,
    end_vertex_index: int,
    context: str,
) -> tuple[Point3, Point3]:
    if start_vertex_index < 0 or start_vertex_index >= len(vertices):
        raise RuntimeError(
            "tx terminal bridge edge start index is outside port sheet vertices "
            f"(index={start_vertex_index}, context={context})"
        )
    if end_vertex_index < 0 or end_vertex_index >= len(vertices):
        raise RuntimeError(
            "tx terminal bridge edge end index is outside port sheet vertices "
            f"(index={end_vertex_index}, context={context})"
        )
    start_xyz = vertices[start_vertex_index]
    end_xyz = vertices[end_vertex_index]
    if _edge_length_sq(start_xyz, end_xyz) <= 1e-18:
        raise RuntimeError(f"tx terminal bridge edge is degenerate (context={context})")
    return (start_xyz, end_xyz)


def _build_tx_terminal_bridge_triangle_face(
    *,
    points: tuple[Point3, Point3, Point3],
    context: str,
) -> bd.Face:
    _triangle_area_sq_from_points(points=points, context=context)
    with bd.BuildLine() as builder:
        bd.Polyline(*points, close=True)
    line = builder.line
    if line is None:
        raise RuntimeError(f"tx terminal bridge triangle line builder failed (context={context})")
    wires = tuple(line.wires())
    if len(wires) != 1:
        raise RuntimeError(
            "tx terminal bridge triangle profile must produce one closed wire "
            f"(context={context}, actual={len(wires)})"
        )
    return cast(bd.Face, bd.make_face(edges=tuple(wires[0].edges())))


def _build_tx_terminal_bridge_mesh_shapes(
    *,
    polygon: tuple[Point3, Point3, Point3, Point3],
    context: str,
) -> tuple[bd.Face, bd.Face]:
    return (
        _build_tx_terminal_bridge_triangle_face(
            points=(polygon[0], polygon[1], polygon[2]),
            context=f"{context}[0]",
        ),
        _build_tx_terminal_bridge_triangle_face(
            points=(polygon[0], polygon[2], polygon[3]),
            context=f"{context}[1]",
        ),
    )


def _build_tx_terminal_bridge_polygon_shape(
    *,
    polygon: tuple[Point3, Point3, Point3, Point3],
    extrusion_axis: tuple[float, float, float],
    thickness_mm: float,
    context: str,
) -> Shape:
    if thickness_mm <= 0.0:
        raise RuntimeError(f"tx terminal bridge extrusion thickness must be positive (actual={thickness_mm}, context={context})")
    triangles = _build_tx_terminal_bridge_mesh_shapes(polygon=polygon, context=f"{context}.mesh")
    translated_triangles = tuple(
        cast(
            bd.Face,
            triangles[idx].moved(
                bd.Location((
                    extrusion_axis[0] * thickness_mm,
                    extrusion_axis[1] * thickness_mm,
                    extrusion_axis[2] * thickness_mm,
                ))
            ),
        )
        for idx in (0, 1)
    )
    bridged_parts = [
        cast(Shape, bd.loft((triangles[0], translated_triangles[0]), ruled=True)),
        cast(Shape, bd.loft((triangles[1], translated_triangles[1]), ruled=True)),
    ]
    bridged = bridged_parts[0]
    for bridge_part in bridged_parts[1:]:
        bridged = cast(Shape, bridged.fuse(bridge_part))
    solids = tuple(bridged.solids())
    if len(solids) != 1:
        raise RuntimeError(f"tx terminal bridge extrusion must return one solid (context={context}, solid_count={len(solids)})")
    return solids[0]


def _translate_shape_along_axis(shape: Shape, axis: tuple[float, float, float], distance_mm: float) -> Shape:
    if distance_mm == 0.0:
        return shape
    return shape.moved(bd.Location((axis[0] * distance_mm, axis[1] * distance_mm, axis[2] * distance_mm)))


def _terminal_bridge_member_entry(
    *,
    object_id: str,
    role: str,
    shape: Shape,
    plane: Literal["XY", "YZ", "ZX", "mixed"],
    material: str,
    material_thickness_mm: float,
    total_stack_thickness_mm: float,
) -> NonModelSceneMemberEntry:
    if material_thickness_mm <= 0.0 or not math.isfinite(material_thickness_mm):
        raise RuntimeError(
            "tx terminal bridge material thickness must be finite and positive "
            f"(object_id={object_id}, actual={material_thickness_mm})"
        )
    if total_stack_thickness_mm <= 0.0 or not math.isfinite(total_stack_thickness_mm):
        raise RuntimeError(
            "tx terminal bridge total stack thickness must be finite and positive "
            f"(object_id={object_id}, actual={total_stack_thickness_mm})"
        )
    return cast(
        NonModelSceneMemberEntry,
        {
            "object_id": object_id,
            "role": role,
            "material": material,
            "model_state": False,
            "canonical_coordinates": dict(canonical_from_shape(shape)),
            "plane": plane,
            "non_model": True,
            "bridge_material_thickness_mm": material_thickness_mm,
            "bridge_total_stack_thickness_mm": total_stack_thickness_mm,
        },
    )


def _build_tx_terminal_bridge_shapes_and_members(
    *,
    tx_inner_scene_data: ModeledObjectSceneData,
    tx_outer_scene_data: ModeledObjectSceneData,
    polarity: _TxTerminalBridgePolarity,
    start_vertex_index: int,
    end_vertex_index: int,
    pcb_object_id: str,
    copper_object_id: str,
    bridge_role: str,
) -> tuple[tuple[Shape, ...], tuple[NonModelSceneMemberEntry, ...]]:
    if not math.isclose(
        _TX_TERMINAL_BRIDGE_PCB_THICKNESS_MM + _TX_TERMINAL_BRIDGE_COPPER_THICKNESS_MM,
        _TX_TERMINAL_BRIDGE_TOTAL_THICKNESS_MM,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise RuntimeError(
            "tx terminal bridge fixed dimensions must satisfy pcb_thickness + copper_thickness == total_thickness "
            f"(pcb={_TX_TERMINAL_BRIDGE_PCB_THICKNESS_MM}, copper={_TX_TERMINAL_BRIDGE_COPPER_THICKNESS_MM}, "
            f"total={_TX_TERMINAL_BRIDGE_TOTAL_THICKNESS_MM})"
        )
    inner_terminal_metadata = cast(dict[str, object], tx_inner_scene_data["terminal_metadata"])
    if "vertices_xyz" not in inner_terminal_metadata:
        raise RuntimeError(
            f"tx inner {polarity} bridge requires vertices_xyz terminal metadata "
            f"(object_id={tx_inner_scene_data['object_id']})"
        )
    outer_terminal_metadata = cast(dict[str, object], tx_outer_scene_data["terminal_metadata"])
    if "vertices_xyz" not in outer_terminal_metadata:
        raise RuntimeError(
            f"tx outer {polarity} bridge requires vertices_xyz terminal metadata "
            f"(object_id={tx_outer_scene_data['object_id']})"
        )
    inner_sheet_vertices = _require_port_sheet_vertices_xyz(
        value=inner_terminal_metadata["vertices_xyz"],
        context=f"modeled_scene_data[{tx_inner_scene_data['object_id']}].terminal_metadata.vertices_xyz",
    )
    outer_sheet_vertices = _require_port_sheet_vertices_xyz(
        value=outer_terminal_metadata["vertices_xyz"],
        context=f"modeled_scene_data[{tx_outer_scene_data['object_id']}].terminal_metadata.vertices_xyz",
    )
    inner_terminal_edge = _terminal_edge_from_port_sheet(
        vertices=inner_sheet_vertices,
        start_vertex_index=start_vertex_index,
        end_vertex_index=end_vertex_index,
        context=f"modeled_scene_data[{tx_inner_scene_data['object_id']}].terminal_metadata.vertices_xyz",
    )
    outer_terminal_edge = _terminal_edge_from_port_sheet(
        vertices=outer_sheet_vertices,
        start_vertex_index=start_vertex_index,
        end_vertex_index=end_vertex_index,
        context=f"modeled_scene_data[{tx_outer_scene_data['object_id']}].terminal_metadata.vertices_xyz",
    )
    if _edge_length_sq(*inner_terminal_edge) <= 1e-18:
        raise RuntimeError(f"tx {polarity} bridge inner terminal edge length is zero")
    if _edge_length_sq(*outer_terminal_edge) <= 1e-18:
        raise RuntimeError(f"tx {polarity} bridge outer terminal edge length is zero")
    if _edge_length_sq(inner_terminal_edge[0], outer_terminal_edge[0]) <= 1e-18:
        raise RuntimeError(f"tx {polarity} bridge start-edge span is zero")
    if _edge_length_sq(inner_terminal_edge[1], outer_terminal_edge[1]) <= 1e-18:
        raise RuntimeError(f"tx {polarity} bridge end-edge span is zero")
    polygon = (
        inner_terminal_edge[0],
        inner_terminal_edge[1],
        outer_terminal_edge[1],
        outer_terminal_edge[0],
    )
    extrusion_axis = _bridge_extrusion_axis_from_polygon(
        polygon=polygon,
        context=f"tx_{polarity}_bridge_polygon",
    )
    plane = _ledger_plane_from_extrusion_axis(extrusion_axis=extrusion_axis)
    pcb_shape = _build_tx_terminal_bridge_polygon_shape(
        polygon=polygon,
        extrusion_axis=extrusion_axis,
        thickness_mm=_TX_TERMINAL_BRIDGE_PCB_THICKNESS_MM,
        context=f"tx_{polarity}_bridge_pcb",
    )
    copper_shape = _translate_shape_along_axis(
        shape=_build_tx_terminal_bridge_polygon_shape(
            polygon=polygon,
            extrusion_axis=extrusion_axis,
            thickness_mm=_TX_TERMINAL_BRIDGE_COPPER_THICKNESS_MM,
            context=f"tx_{polarity}_bridge_copper",
        ),
        axis=extrusion_axis,
        distance_mm=_TX_TERMINAL_BRIDGE_PCB_THICKNESS_MM,
    )
    pcb_shape.label = pcb_object_id
    copper_shape.label = copper_object_id
    pcb_member = _terminal_bridge_member_entry(
        object_id=pcb_object_id,
        role=bridge_role,
        shape=pcb_shape,
        plane=plane,
        material="FR4_epoxy",
        material_thickness_mm=_TX_TERMINAL_BRIDGE_PCB_THICKNESS_MM,
        total_stack_thickness_mm=_TX_TERMINAL_BRIDGE_TOTAL_THICKNESS_MM,
    )
    copper_member = _terminal_bridge_member_entry(
        object_id=copper_object_id,
        role=bridge_role,
        shape=copper_shape,
        plane=plane,
        material="copper",
        material_thickness_mm=_TX_TERMINAL_BRIDGE_COPPER_THICKNESS_MM,
        total_stack_thickness_mm=_TX_TERMINAL_BRIDGE_TOTAL_THICKNESS_MM,
    )
    return ((pcb_shape, copper_shape), (pcb_member, copper_member))


def _build_tx_terminal_bridge_set_shapes_and_members(
    *,
    tx_inner_scene_data: ModeledObjectSceneData,
    tx_outer_scene_data: ModeledObjectSceneData,
) -> tuple[tuple[Shape, ...], tuple[NonModelSceneMemberEntry, ...]]:
    positive_shapes, positive_members = _build_tx_terminal_bridge_shapes_and_members(
        tx_inner_scene_data=tx_inner_scene_data,
        tx_outer_scene_data=tx_outer_scene_data,
        polarity="positive",
        start_vertex_index=3,
        end_vertex_index=0,
        pcb_object_id=_TX_POSITIVE_BRIDGE_PCB_OBJECT_ID,
        copper_object_id=_TX_POSITIVE_BRIDGE_COPPER_OBJECT_ID,
        bridge_role=_TX_POSITIVE_BRIDGE_ROLE,
    )
    negative_shapes, negative_members = _build_tx_terminal_bridge_shapes_and_members(
        tx_inner_scene_data=tx_inner_scene_data,
        tx_outer_scene_data=tx_outer_scene_data,
        polarity="negative",
        start_vertex_index=1,
        end_vertex_index=2,
        pcb_object_id=_TX_NEGATIVE_BRIDGE_PCB_OBJECT_ID,
        copper_object_id=_TX_NEGATIVE_BRIDGE_COPPER_OBJECT_ID,
        bridge_role=_TX_NEGATIVE_BRIDGE_ROLE,
    )
    return ((*positive_shapes, *negative_shapes), (*positive_members, *negative_members))


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


def _require_plate_stack_merged_scene_shape_contract(*, scene_shapes: tuple[Shape, ...]) -> None:
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
    blank_shape: Shape,
    tool_shape: Shape,
    label: str,
    context: str,
) -> Shape:
    cut_shape = cast(Shape, blank_shape.cut(tool_shape))
    solids = tuple(cut_shape.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "type2 shape cut must produce exactly one solid "
            f"(label={label}, context={context}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = label
    return cast(Shape, solid)


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
        tx_region_max_z=owner_spec.origin_xyz[2] + owner_spec.size_xyz[2],
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


def _tx_inner_underlay_expected_body_names(*, repeat_count: int) -> list[str]:
    expected_names: list[str] = []
    for repeat_index in range(repeat_count):
        expected_names.append(f"tx_underlay_pet_psa_u{repeat_index}")
        expected_names.append(f"tx_underlay_ferrite_u{repeat_index}")
    return expected_names


def _tx_inner_void_expected_body_names_from_exported(*, expected_body_names: object) -> list[str]:
    if not isinstance(expected_body_names, tuple):
        raise ValueError(
            "type2 tx_inner expected exported body names must be a tuple "
            f"(actual={type(expected_body_names).__name__})"
        )
    void_names = [name for name in expected_body_names if isinstance(name, str) and name.startswith("tx_void_")]
    for void_index, void_name in enumerate(void_names):
        if void_index % 2 == 0:
            expected_name = f"tx_void_ferrite_u{void_index // 2}"
        else:
            expected_name = f"tx_void_pet_psa_u{void_index // 2}"
        if void_name != expected_name:
            raise ValueError(
                "type2 tx_inner void stack expected body contract mismatch "
                f"(expected={expected_name}, actual={void_name}, void_names={void_names})"
            )
    return void_names


def _tx_outer_void_expected_body_names_from_exported(*, expected_body_names: object) -> list[str]:
    if not isinstance(expected_body_names, tuple):
        raise ValueError(
            "type2 tx_outer expected exported body names must be a tuple "
            f"(actual={type(expected_body_names).__name__})"
        )
    void_names = [name for name in expected_body_names if isinstance(name, str) and name.startswith("tx_outer_void_")]
    for void_index, void_name in enumerate(void_names):
        if void_index % 2 == 0:
            expected_name = f"tx_outer_void_ferrite_u{void_index // 2}"
        else:
            expected_name = f"tx_outer_void_pet_psa_u{void_index // 2}"
        if void_name != expected_name:
            raise ValueError(
                "type2 tx_outer void stack expected body contract mismatch "
                f"(expected={expected_name}, actual={void_name}, void_names={void_names})"
            )
    return void_names


def _tx_outer_underlay_expected_body_names_from_exported(*, expected_body_names: object) -> list[str]:
    if not isinstance(expected_body_names, tuple):
        raise ValueError(
            "type2 tx_outer expected exported body names must be a tuple "
            f"(actual={type(expected_body_names).__name__})"
        )
    underlay_names = [
        name for name in expected_body_names if isinstance(name, str) and name.startswith("tx_outer_underlay_")
    ]
    for underlay_index, underlay_name in enumerate(underlay_names):
        if underlay_index % 2 == 0:
            expected_name = f"tx_outer_underlay_pet_psa_u{underlay_index // 2}"
        else:
            expected_name = f"tx_outer_underlay_ferrite_u{underlay_index // 2}"
        if underlay_name != expected_name:
            raise ValueError(
                "type2 tx_outer bottom underlay expected body contract mismatch "
                f"(expected={expected_name}, actual={underlay_name}, underlay_names={underlay_names})"
            )
    return underlay_names


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
) -> tuple[NonModelObjectLedgerEntry, tuple[Shape, ...], dict[str, dict[str, object]]]:
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
) -> tuple[tuple[Shape, ...], ModeledObjectSceneData]:
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

    transformed_shapes: list[Shape] = []
    tile_metadata: list[dict[str, object]] = []
    pcb_layer_positions: list[float] = []
    copper_layer_positions: list[float] = []
    vertical_stub_body_names: list[str] = []
    parallel_tile_inputs: list[TxRectVoidCollectorTileInput] = []
    terminal_stub_trace_width_mm_values: list[float] = []

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

    def _trace_width_mm_from_terminal_anchor_box(
        *,
        anchor_box_spec: BoxSpec,
        stack_space_object_id: str,
        terminal_body_name: str,
    ) -> float:
        anchor_size_x, anchor_size_y, anchor_size_z = anchor_box_spec.size_xyz
        if (
            not math.isfinite(anchor_size_x)
            or not math.isfinite(anchor_size_y)
            or not math.isfinite(anchor_size_z)
        ):
            raise RuntimeError(
                "tx_rect_void_columns terminal anchor box dimensions must be finite "
                f"(stack_space_object_id={stack_space_object_id}, terminal_body_name={terminal_body_name}, "
                f"anchor_label={anchor_box_spec.label}, size_xyz={anchor_box_spec.size_xyz})"
            )
        if anchor_size_x <= 0.0 or anchor_size_y <= 0.0 or anchor_size_z <= 0.0:
            raise RuntimeError(
                "tx_rect_void_columns terminal anchor BoxSpec must have positive dimensions "
                f"(stack_space_object_id={stack_space_object_id}, terminal_body_name={terminal_body_name}, "
                f"anchor_label={anchor_box_spec.label}, size_xyz={anchor_box_spec.size_xyz})"
            )
        anchor_stub_side_mm = math.hypot(anchor_size_x, anchor_size_y) / math.sqrt(2.0)
        if anchor_stub_side_mm <= 0.0:
            raise RuntimeError(
                "tx_rect_void_columns terminal anchor recovered stub side must be positive "
                f"(stack_space_object_id={stack_space_object_id}, terminal_body_name={terminal_body_name}, "
                f"anchor_label={anchor_box_spec.label}, size_xyz={anchor_box_spec.size_xyz})"
            )
        if _TX_RECT_VOID_COLUMNS_TERMINAL_STUB_SIDE_RATIO <= 0.0:
            raise RuntimeError(
                "tx_rect_void_columns terminal stub ratio must be positive "
                f"(actual={_TX_RECT_VOID_COLUMNS_TERMINAL_STUB_SIDE_RATIO})"
            )
        return anchor_stub_side_mm / _TX_RECT_VOID_COLUMNS_TERMINAL_STUB_SIDE_RATIO

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
    ) -> tuple[Shape, bd.Face, tuple[tuple[float, float, float], ...]]:
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
            Shape,
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
            for terminal_anchor_box_spec in terminal_anchor_box_specs:
                candidate_trace_width_mm = _trace_width_mm_from_terminal_anchor_box(
                    anchor_box_spec=terminal_anchor_box_spec,
                    stack_space_object_id=stack_space_object_id,
                    terminal_body_name=terminal_body_name,
                )
                if len(terminal_stub_trace_width_mm_values) == 0:
                    terminal_stub_trace_width_mm_values.append(candidate_trace_width_mm)
                elif not math.isclose(
                    terminal_stub_trace_width_mm_values[0],
                    candidate_trace_width_mm,
                    rel_tol=0.0,
                    abs_tol=1e-9,
                ):
                    raise RuntimeError(
                        "tx_rect_void_columns terminal anchor trace width mismatch "
                        f"(stack_space_object_id={stack_space_object_id}, terminal_body_name={terminal_body_name}, "
                        f"first={terminal_stub_trace_width_mm_values[0]}, actual={candidate_trace_width_mm})"
                    )
                else:
                    terminal_stub_trace_width_mm_values.append(candidate_trace_width_mm)
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
        transformed_tile_shapes: list[Shape] = []
        tile_body_names: list[str] = []
        tile_parallel_copper_shapes: list[Shape] = []
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
        parallel_terminal_shapes_by_name: dict[str, tuple[Shape, tuple[tuple[float, float, float], ...]]] = {}
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
    canonical_coordinates: dict[str, object] = dict(canonical_from_shape(cast(Shape, compound)))
    canonical_coordinates["pcb_layer_z_positions_mm"] = tuple(sorted(set(round(value, 10) for value in pcb_layer_positions)))
    canonical_coordinates["copper_layer_z_positions_mm"] = tuple(
        sorted(set(round(value, 10) for value in copper_layer_positions))
    )
    canonical_coordinates["stack_space_tile_members"] = tuple(tile_metadata)
    if len(terminal_stub_trace_width_mm_values) == 0:
        raise RuntimeError("tx_rect_void_columns terminal anchor trace width metadata is unavailable")
    canonical_coordinates["trace_width_mm"] = terminal_stub_trace_width_mm_values[0]
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
    role: Literal["tx_single_coil", "tx_inner_single_coil", "rx_single_coil"],
) -> str:
    if role in ("tx_single_coil", "tx_inner_single_coil"):
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
            tx_inner_underlay_names = _tx_inner_underlay_expected_body_names(
                repeat_count=resolve_modeled_underlay_repeat_count(modeled_spec, seed=seed)
            )
            tx_inner_void_names = _tx_inner_void_expected_body_names_from_exported(
                expected_body_names=expected_body_names
            )
            tx_inner_void_stack_present = resolve_modeled_tx_inner_void_stack_present(modeled_spec, seed=seed)
            if tx_inner_void_stack_present and len(tx_inner_void_names) == 0:
                raise ValueError(
                    "type2 tx_inner expected body contract requires tx_void_* names when void_stack_present is true "
                    f"(object_id={object_id})"
                )
            if not tx_inner_void_stack_present and len(tx_inner_void_names) != 0:
                raise ValueError(
                    "type2 tx_inner expected body contract forbids tx_void_* names when void_stack_present is false "
                    f"(object_id={object_id}, tx_void_names={tuple(tx_inner_void_names)})"
                )
            expected_names.extend(tx_inner_underlay_names)
            expected_names.extend(tx_inner_void_names)
            expected_groups = (
                [
                    {
                        "group_name": _ferrite_group_name_for_modeled_role(role=role),
                        "member_body_names": tuple(tx_inner_underlay_names + tx_inner_void_names),
                    }
                ]
                if len(tx_inner_underlay_names) + len(tx_inner_void_names) > 0
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
        elif role == "tv_aluminum_plate":
            expected_names = ["tv_aluminum_plate"]
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


def _require_port_sheet_geometry_contract(
    *,
    ledger: Type2StepLedger,
    modeled_specs: tuple[
        ModeledRxPlateStackSpec
        | ModeledRxSingleCoilSpec
        | ModeledTxInnerSingleCoilSpec
        | ModeledTxPlateStackSpec
        | ModeledTvAluminumPlateSpec
        | ModeledTxRectVoidColumnsSpec
        | ModeledTxSingleCoilSpec,
        ...,
    ],
    modeled_scene_data_by_object_id: dict[str, ModeledObjectSceneData],
) -> None:
    for modeled_spec in modeled_specs:
        modeled_entry = next(entry for entry in ledger["modeled_objects"] if entry["object_id"] == modeled_spec.object_id)
        terminal_metadata = cast(dict[str, object], modeled_entry["terminal_metadata"])
        if isinstance(modeled_spec, (ModeledTxPlateStackSpec, ModeledRxPlateStackSpec)):
            assert modeled_spec.object_id in modeled_scene_data_by_object_id, (
                "type2 plate-stack terminal contract missing first-pass modeled scene data "
                f"(object_id={modeled_spec.object_id})"
            )
            expected_scene_data = modeled_scene_data_by_object_id[modeled_spec.object_id]
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
        if isinstance(modeled_spec, ModeledTvAluminumPlateSpec):
            if terminal_metadata != {}:
                raise RuntimeError(
                    "tv_aluminum_plate terminal metadata must stay empty "
                    f"(object_id={modeled_spec.object_id}, actual={terminal_metadata})"
                )
            continue
        raw_kind = terminal_metadata["kind"] if "kind" in terminal_metadata else ""
        if not isinstance(raw_kind, str):
            raise RuntimeError(
                "type2 terminal metadata kind sentinel must be str "
                f"(object_id={modeled_spec.object_id}, actual={raw_kind!r})"
            )
        if raw_kind != "single_coil_port_v1":
            raise RuntimeError(
                "type2 single-coil terminal metadata kind sentinel must be single_coil_port_v1 "
                f"(object_id={modeled_spec.object_id}, kind={raw_kind!r})"
            )
        assert modeled_spec.object_id in modeled_scene_data_by_object_id, (
            "type2 port sheet contract missing first-pass modeled scene data "
            f"(object_id={modeled_spec.object_id})"
        )
        expected_scene_data = modeled_scene_data_by_object_id[modeled_spec.object_id]
        expected_terminal_metadata = expected_scene_data["terminal_metadata"]
        if terminal_metadata != expected_terminal_metadata:
            raise RuntimeError(
                "type2 port sheet metadata must match modeled scene construction contract "
                f"(object_id={modeled_spec.object_id}, actual={terminal_metadata}, expected={expected_terminal_metadata})"
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
    active_modeled_specs = _active_step_export_modeled_specs(spec=spec)
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
        modeled_specs=active_modeled_specs,
    )
    tx_region_spec = require_non_model_object_spec(resolved_non_model_specs, object_id="tx_region")
    tx_region_max_z = tx_region_spec.origin_xyz[2] + tx_region_spec.size_xyz[2]

    modeled_scene_data: list[ModeledObjectSceneData] = []
    modeled_scene_shapes: list[Shape] = []
    modeled_entries = []
    for modeled_spec in active_modeled_specs:
        if modeled_spec.role == "tv_aluminum_plate":
            owner_spec = require_non_model_object_spec(resolved_non_model_specs, object_id="tv")
        else:
            owner_spec = require_non_model_object_spec(
                resolved_non_model_specs,
                object_id=placement_owner_id_for_role(modeled_spec.role),
            )
        metadata_path = object_metadata_dir / f"{modeled_spec.object_id}.metadata.json"
        current_modeled_scene_shapes, scene_data = build_modeled_scene_data(
            modeled_spec,
            owner_spec=owner_spec,
            tx_region_max_z=tx_region_max_z,
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
    modeled_scene_data_by_object_id = {
        scene_data["object_id"]: scene_data for scene_data in modeled_scene_data
    }
    if "tx_inner_rect_void_coil" in modeled_scene_data_by_object_id and "tx_outer_rect_void_coil" in modeled_scene_data_by_object_id:
        tx_inner_scene_data = modeled_scene_data_by_object_id["tx_inner_rect_void_coil"]
        tx_outer_scene_data = modeled_scene_data_by_object_id["tx_outer_rect_void_coil"]
        bridge_shapes, bridge_members = _build_tx_terminal_bridge_set_shapes_and_members(
            tx_inner_scene_data=tx_inner_scene_data,
            tx_outer_scene_data=tx_outer_scene_data,
        )
        non_model_scene_shapes = (*non_model_scene_shapes, *bridge_shapes)
        member_object_ids = list(non_model_entry["member_object_ids"])
        member_objects = list(non_model_entry["member_objects"])
        for member in bridge_members:
            member_object_id = cast(str, member["object_id"])
            if member_object_id in member_object_ids:
                raise RuntimeError(
                    "type2 terminal bridge member object_id must be unique within non-model scene metadata "
                    f"(object_id={member_object_id})"
                )
            member_object_ids.append(member_object_id)
            member_objects.append(cast(NonModelSceneMemberEntry, member))
        non_model_entry["member_object_ids"] = tuple(member_object_ids)
        non_model_entry["member_objects"] = tuple(member_objects)

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
    _require_port_sheet_geometry_contract(
        ledger=ledger,
        modeled_specs=active_modeled_specs,
        modeled_scene_data_by_object_id=modeled_scene_data_by_object_id,
    )
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

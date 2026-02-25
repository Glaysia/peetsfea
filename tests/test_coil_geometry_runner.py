from __future__ import annotations

import math
from pathlib import Path
from typing import cast

import pytest

import peetsfea.backend.pyaedt.geometry.square_spiral as geom
import peetsfea.spec.resolver as resolver
from peetsfea.types.manifest import CoilPolaritySpec, GeometryMetadata, GroupEndpointEntry, Manifest, ResolvedPcbInstance


class _FakePoint:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class _FakeEdge:
    def __init__(self, midpoint: _FakePoint) -> None:
        self.midpoint = midpoint


class _FakeObject:
    def __init__(
        self, name: str, bbox: list[float], edge_samples: list[tuple[float, float]], points: list[list[float]] | None = None
    ) -> None:
        self.name = name
        self.bounding_box = bbox
        self.edges = [_FakeEdge(_FakePoint(x, y)) for x, y in edge_samples]
        self.points = points or []


class _FakeModeler:
    def __init__(self) -> None:
        self.polyline_calls: list[dict[str, object]] = []
        self.cover_calls: list[dict[str, object]] = []
        self.cylinder_calls: list[dict[str, object]] = []
        self.box_calls: list[dict[str, object]] = []
        self.thicken_calls: list[dict[str, object]] = []
        self.subtract_calls: list[dict[str, object]] = []
        self.unite_calls: list[dict[str, object]] = []
        self.duplicate_mirror_calls: list[dict[str, object]] = []
        self.objects: dict[str, _FakeObject] = {}

    def create_polyline(
        self,
        points: list[list[float]],
        segment_type: str | None = None,
        cover_surface: bool = False,
        close_surface: bool = False,
        name: str | None = None,
        material: str | None = None,
        xsection_type: str | None = None,
        xsection_orient: str | None = None,
        xsection_width: float = 1.0,
        xsection_topwidth: float = 1.0,
        xsection_height: float = 1.0,
        xsection_num_seg: int = 0,
        xsection_bend_type: str | None = None,
        non_model: bool = False,
    ) -> _FakeObject:
        self.polyline_calls.append(
            {
                "points": points,
                "name": name,
                "material": material,
                "xsection_width": xsection_width,
                "xsection_height": xsection_height,
                "xsection_type": xsection_type,
            }
        )
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        zs = [point[2] for point in points]
        edge_samples = []
        for idx in range(min(len(points) - 1, 8)):
            x_mid = (points[idx][0] + points[idx + 1][0]) / 2.0
            y_mid = (points[idx][1] + points[idx + 1][1]) / 2.0
            edge_samples.append((x_mid, y_mid))
        obj = _FakeObject(
            name or "polyline",
            [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)],
            edge_samples,
            points=points,
        )
        self.objects[obj.name] = obj
        return obj

    def create_cylinder(
        self,
        orientation: str,
        origin: list[float],
        radius: float,
        height: float,
        num_sides: int = 0,
        name: str | None = None,
        material: str | None = None,
    ) -> _FakeObject:
        self.cylinder_calls.append(
            {
                "orientation": orientation,
                "origin": origin,
                "radius": radius,
                "height": height,
                "name": name,
                "material": material,
            }
        )
        obj = _FakeObject(
            name or "cylinder",
            [
                origin[0] - radius,
                origin[1] - radius,
                origin[2],
                origin[0] + radius,
                origin[1] + radius,
                origin[2] + height,
            ],
            [(origin[0], origin[1])],
        )
        self.objects[obj.name] = obj
        return obj

    def create_box(
        self,
        origin: list[float],
        sizes: list[float],
        name: str | None = None,
        material: str | None = None,
        non_model: bool = False,
    ) -> _FakeObject:
        self.box_calls.append(
            {
                "origin": origin,
                "sizes": sizes,
                "name": name,
                "material": material,
                "non_model": non_model,
            }
        )
        obj = _FakeObject(
            name or "box",
            [
                origin[0],
                origin[1],
                origin[2],
                origin[0] + sizes[0],
                origin[1] + sizes[1],
                origin[2] + sizes[2],
            ],
            [(origin[0], origin[1])],
        )
        self.objects[obj.name] = obj
        return obj

    def duplicate_and_mirror(
        self,
        assignment: str | _FakeObject,
        origin: list[float],
        vector: list[float],
        is_3d_comp: bool = False,
        duplicate_assignment: bool = True,
    ) -> list[str]:
        del is_3d_comp
        del duplicate_assignment
        if isinstance(assignment, _FakeObject):
            source_name = assignment.name
        else:
            source_name = assignment
        source = self.objects[source_name]
        axis_y = float(origin[1])
        source_points = cast(list[list[float]], source.points)
        mirrored_points = [[p[0], (2.0 * axis_y) - p[1], p[2]] for p in source_points]
        new_name = f"{source_name}_mirror_{len(self.duplicate_mirror_calls)}"
        self.duplicate_mirror_calls.append(
            {"assignment": source_name, "origin": origin, "vector": vector, "name": new_name}
        )
        source_call = next((call for call in reversed(self.polyline_calls) if call["name"] == source_name), None)
        xsection_type = source_call["xsection_type"] if source_call is not None else "Rectangle"
        xsection_width = source_call["xsection_width"] if source_call is not None else 1.0
        xsection_height = source_call["xsection_height"] if source_call is not None else 1.0
        self.polyline_calls.append(
            {
                "points": mirrored_points,
                "name": new_name,
                "material": "copper",
                "xsection_width": xsection_width,
                "xsection_height": xsection_height,
                "xsection_type": xsection_type,
            }
        )
        xs = [point[0] for point in mirrored_points]
        ys = [point[1] for point in mirrored_points]
        zs = [point[2] for point in mirrored_points]
        edge_samples = []
        for idx in range(min(len(mirrored_points) - 1, 8)):
            x_mid = (mirrored_points[idx][0] + mirrored_points[idx + 1][0]) / 2.0
            y_mid = (mirrored_points[idx][1] + mirrored_points[idx + 1][1]) / 2.0
            edge_samples.append((x_mid, y_mid))
        mirrored_obj = _FakeObject(
            new_name,
            [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)],
            edge_samples,
            points=mirrored_points,
        )
        self.objects[new_name] = mirrored_obj
        return [new_name]

    def subtract(
        self,
        blank_list: str | _FakeObject | list[str | _FakeObject],
        tool_list: str | _FakeObject | list[str | _FakeObject],
        keep_originals: bool = True,
    ) -> bool:
        blanks = blank_list if isinstance(blank_list, list) else [blank_list]
        tools = tool_list if isinstance(tool_list, list) else [tool_list]
        self.subtract_calls.append(
            {
                "blank_list": [item.name if isinstance(item, _FakeObject) else item for item in blanks],
                "tool_list": [item.name if isinstance(item, _FakeObject) else item for item in tools],
                "keep_originals": keep_originals,
            }
        )
        return True

    def cover_lines(self, assignment: str | _FakeObject) -> _FakeObject:
        name = assignment.name if isinstance(assignment, _FakeObject) else assignment
        if name not in self.objects:
            raise ValueError(f"Unknown polyline object for cover_lines: {name}")
        self.cover_calls.append({"assignment": name})
        return self.objects[name]

    def thicken_sheet(
        self,
        assignment: str | _FakeObject,
        thickness: float,
    ) -> _FakeObject:
        name = assignment.name if isinstance(assignment, _FakeObject) else assignment
        if name not in self.objects:
            raise ValueError(f"Unknown sheet object for thicken: {name}")
        obj = self.objects[name]
        bbox = obj.bounding_box
        half = thickness / 2.0
        thickened_bbox = [bbox[0], bbox[1] - half, bbox[2], bbox[3], bbox[4] + half, bbox[5]]
        self.thicken_calls.append({"assignment": name, "thickness": thickness})
        edge_samples = [((thickened_bbox[0] + thickened_bbox[3]) / 2.0, (thickened_bbox[1] + thickened_bbox[4]) / 2.0)]
        thickened_obj = _FakeObject(name, thickened_bbox, edge_samples, points=obj.points)
        self.objects[name] = thickened_obj
        return thickened_obj

    def unite(self, assignment: str | _FakeObject | list[str | _FakeObject]) -> _FakeObject | list[str]:
        assignments = assignment if isinstance(assignment, list) else [assignment]
        names = [item.name if isinstance(item, _FakeObject) else item for item in assignments]
        self.unite_calls.append({"assignment": names[:]})
        if not names:
            return []
        keep_name = str(names[0])
        existing = [self.objects[str(name)] for name in names if str(name) in self.objects]
        if not existing:
            return [keep_name]
        min_x = min(obj.bounding_box[0] for obj in existing)
        min_y = min(obj.bounding_box[1] for obj in existing)
        min_z = min(obj.bounding_box[2] for obj in existing)
        max_x = max(obj.bounding_box[3] for obj in existing)
        max_y = max(obj.bounding_box[4] for obj in existing)
        max_z = max(obj.bounding_box[5] for obj in existing)
        merged_points: list[list[float]] = []
        for obj in existing:
            if obj.points:
                merged_points.extend(obj.points)
        merged = _FakeObject(keep_name, [min_x, min_y, min_z, max_x, max_y, max_z], [(min_x, min_y)], points=merged_points)
        self.objects[keep_name] = merged
        for name in names[1:]:
            self.objects.pop(str(name), None)
        return merged


class _FakeHfss:
    def __init__(self) -> None:
        self.modeler = _FakeModeler()
        self.saved_path: str | None = None
        self.release_args: tuple[bool, bool] | None = None
        self.design_vars: dict[str, str] = {}

    def __setitem__(self, key: str, value: str) -> None:
        self.design_vars[key] = value

    def save_project(self, project_file: str) -> None:
        self.saved_path = project_file

    def release_desktop(self, close_projects: bool = True, close_desktop: bool = True) -> None:
        self.release_args = (close_projects, close_desktop)


def _turn_sign_xy(points: list[list[float]]) -> float:
    assert len(points) >= 3
    ax = points[1][0] - points[0][0]
    ay = points[1][1] - points[0][1]
    bx = points[2][0] - points[1][0]
    by = points[2][1] - points[1][1]
    return (ax * by) - (ay * bx)


def _direction_from_xy_points(points: list[list[float]]) -> str:
    eps = 1e-9
    if len(points) < 3:
        raise AssertionError("Need at least 3 points to determine XY winding direction")
    for idx in range(1, len(points) - 1):
        vx1 = points[idx][0] - points[idx - 1][0]
        vy1 = points[idx][1] - points[idx - 1][1]
        vx2 = points[idx + 1][0] - points[idx][0]
        vy2 = points[idx + 1][1] - points[idx][1]
        cross = (vx1 * vy2) - (vy1 * vx2)
        if abs(cross) <= eps:
            continue
        return "ccw" if cross > 0.0 else "cw"
    raise AssertionError("Could not determine XY winding direction from provided points")


def _turn_sign_yz(points: list[list[float]]) -> float:
    assert len(points) >= 3
    ay = points[1][1] - points[0][1]
    az = points[1][2] - points[0][2]
    by = points[2][1] - points[1][1]
    bz = points[2][2] - points[1][2]
    return (ay * bz) - (az * by)


def _group_instance_key_from_endpoint(entry: GroupEndpointEntry) -> tuple[str, str, int]:
    return (entry["group_kind"], entry["board_id"], entry["group_instance_index"])


def _group_instance_key_from_polarity(entry: CoilPolaritySpec) -> tuple[str, str, int]:
    return (entry["group_kind"], entry["board_id"], entry["group_instance_index"])


def _endpoint_map(metadata: GeometryMetadata) -> dict[tuple[str, str, int], GroupEndpointEntry]:
    return {_group_instance_key_from_endpoint(entry): entry for entry in metadata["group_endpoints"]}


def _polarity_map(metadata: GeometryMetadata) -> dict[tuple[str, str, int], CoilPolaritySpec]:
    return {_group_instance_key_from_polarity(entry): entry for entry in metadata["coil_polarity"]}


def _endpoint_z_center(entry: GroupEndpointEntry) -> float:
    return (entry["start_xyz"][2] + entry["end_xyz"][2]) / 2.0


def _assert_no_topology_break(points: list[list[float]]) -> None:
    eps = 1e-9
    assert len(points) >= 2
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for idx in range(len(points) - 1):
        p0 = points[idx]
        p1 = points[idx + 1]
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        assert not (abs(dx) <= eps and abs(dy) <= eps)
        assert abs(dx) <= eps or abs(dy) <= eps
        segments.append(((p0[0], p0[1]), (p1[0], p1[1])))
    for idx in range(1, len(points) - 1):
        p_prev = points[idx - 1]
        p_curr = points[idx]
        p_next = points[idx + 1]
        vx1 = p_curr[0] - p_prev[0]
        vy1 = p_curr[1] - p_prev[1]
        vx2 = p_next[0] - p_curr[0]
        vy2 = p_next[1] - p_curr[1]
        assert not (abs(vx1 + vx2) <= eps and abs(vy1 + vy2) <= eps)
    for idx in range(len(segments)):
        for jdx in range(idx + 1, len(segments)):
            if jdx <= idx + 1:
                continue
            (ax0, ay0), (ax1, ay1) = segments[idx]
            (bx0, by0), (bx1, by1) = segments[jdx]
            a_vertical = abs(ax0 - ax1) <= eps
            b_vertical = abs(bx0 - bx1) <= eps
            if a_vertical and b_vertical:
                if abs(ax0 - bx0) > eps:
                    continue
                a_min, a_max = sorted((ay0, ay1))
                b_min, b_max = sorted((by0, by1))
                assert max(a_min, b_min) > (min(a_max, b_max) + eps)
                continue
            if (not a_vertical) and (not b_vertical):
                if abs(ay0 - by0) > eps:
                    continue
                a_min, a_max = sorted((ax0, ax1))
                b_min, b_max = sorted((bx0, bx1))
                assert max(a_min, b_min) > (min(a_max, b_max) + eps)
                continue
            if a_vertical:
                v_x = ax0
                v_min, v_max = sorted((ay0, ay1))
                h_y = by0
                h_min, h_max = sorted((bx0, bx1))
            else:
                v_x = bx0
                v_min, v_max = sorted((by0, by1))
                h_y = ay0
                h_min, h_max = sorted((ax0, ax1))
            intersects = (h_min - eps) <= v_x <= (h_max + eps) and (v_min - eps) <= h_y <= (v_max + eps)
            assert not intersects


def _manifest(tmp_path: Path) -> Manifest:
    return {
        "design_id": "abcd1234_eeeeeeee_1_0",
        "design_unique_hash": "abcd1234",
        "toml_space_hash": "eeeeeeee",
        "toml_hash": "t" * 64,
        "peetsfea_commit": "c" * 40,
        "seed": 1,
        "retry_attempt": 0,
        "retry_count": 0,
        "repro_mode": "manifest_json",
        "backend": "hfss",
        "selected_parameters": {
            "tx_dd_outer_x": 48.0,
            "tx_dd_outer_y": 48.0,
            "tx_vertical_outer_x": 48.0,
            "tx_vertical_outer_y": 48.0,
            "rx_dd_outer_x": 48.0,
            "rx_dd_outer_y": 48.0,
            "inner_margin_x": 2.0,
            "inner_margin_y": 2.0,
            "tx_dd_pair_spacing_ratio": 0.3,
            "rx_dd_pair_spacing_ratio": 0.3,
            "tx_vertical_center_gap_mm": 10.0,
            "tx_dd_pair_spacing_mm": 60.0,
            "rx_dd_pair_spacing_mm": 60.0,
            "tx_vertical_span_mm": 10.0,
            "tv_width_mm": 1200.0,
            "tv_height_mm": 700.0,
            "tv_thickness_mm": 9.0,
            "tv_base_z_mm": 700.0,
            "tx_region_outer_w_mm": 300.0,
            "tx_region_outer_h_mm": 200.0,
            "tx_region_thickness_mm": 20.0,
            "tx_region_vertical_z_mm": 8.0,
            "tx_region_dd_z_mm": 7.0,
            "rx_region_outer_w_mm": 280.0,
            "rx_region_outer_h_mm": 180.0,
            "rx_region_thickness_mm": 4.0,
            "wall_thickness_mm": 200.0,
            "wall_size_y_mm": 4000.0,
            "wall_size_z_mm": 3000.0,
            "floor_thickness_mm": 300.0,
            "floor_size_x_mm": 5000.0,
            "floor_size_y_mm": 5000.0,
            "shelf_height_mm": 400.0,
            "shelf_min_size_x_mm": 350.0,
            "rx_region_bottom_from_tv_mm": 1.0,
            "tx_dd_top_clearance_mm": 0.0,
            "rx_face_clearance_mm": 0.0,
            "tx_main_1_z_from_tx_main_0_mm": 3.0,
            "dd_mirror_plane": "XZ",
            "rx_plane": "YZ",
            "tx_vertical_plane": "ZX",
            "via_diameter_mm": 0.5,
            "pcb_thickness_mm": 1.6,
            "cu_thickness_mm": 0.035,
            "via_diameter": 0.5,
            "pcb_thickness": 1.6,
            "cu_thickness": 0.035,
            "fr4_er": 4.4,
        },
        "selected_parameters_max": {
            "tx_region_outer_w_mm": 300.0,
            "tx_region_outer_h_mm": 200.0,
            "tx_region_thickness_mm": 20.0,
            "tx_region_vertical_z_mm": 8.0,
            "tx_region_dd_z_mm": 7.0,
            "rx_region_outer_w_mm": 280.0,
            "rx_region_outer_h_mm": 180.0,
            "rx_region_thickness_mm": 4.0,
        },
        "selected_coil_groups": [
            {
                "kind": "tx_dd",
                "requested_count": 2,
                "selected_count": 2,
                "spacing_mm": 60.0,
                "instance_transforms": [{"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0}],
            },
            {
                "kind": "tx_vertical",
                "requested_count": 1,
                "selected_count": 1,
                "spacing_mm": 10.0,
                "instance_transforms": [{"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0}],
            },
            {
                "kind": "rx_dd",
                "requested_count": 2,
                "selected_count": 2,
                "spacing_mm": 60.0,
                "instance_transforms": [{"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0}],
            },
        ],
        "selected_group_geometry": [
            {"kind": "tx_dd", "turn_count_max": 5, "band_ratio": 0.3, "metal_ratio": 2.0 / 3.0, "trace": 1.0, "gap": 0.5},
            {"kind": "tx_vertical", "turn_count_max": 3, "band_ratio": 0.25, "metal_ratio": 0.9 / 1.3, "trace": 0.9, "gap": 0.4},
            {"kind": "rx_dd", "turn_count_max": 6, "band_ratio": 0.35, "metal_ratio": 1.1 / 1.4, "trace": 1.1, "gap": 0.3},
        ],
        "selected_pcbs": [
            {
                "id": "tx_main_0",
                "role": "tx",
                "position": (0.0, 0.0, 0.0),
                "rotation_deg": 0.0,
                "present": True,
                "z_mode": "absolute",
                "z_relative_base_id": None,
                "z_delta_path": None,
                "mounts": [
                    {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
                    {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
                    {"kind": "tx_vertical", "selector_mode": "all", "selector_index": None},
                ],
            },
            {
                "id": "rx_main_0",
                "role": "rx",
                "position": (0.0, 0.0, 110.0),
                "rotation_deg": 0.0,
                "present": True,
                "z_mode": "absolute",
                "z_relative_base_id": None,
                "z_delta_path": None,
                "mounts": [{"kind": "rx_dd", "selector_mode": "index", "selector_index": 0}],
            },
        ],
        "inputs": {
            "ansys_executable_path": "/opt/ansys_inc/v252/AnsysEM",
            "ansys_run_dir": str(tmp_path),
            "toml_path": str(tmp_path / "type1.toml"),
            "non_graphical": True,
            "close_on_exit": True,
        },
        "spec": {
            "spec_version": "0.2.2",
            "design_name": "square_test",
            "units": "mm",
        },
        "created_at_utc": "2026-02-20T00:00:00Z",
        "manifest_path": str(tmp_path / "manifest_abcd1234_eeeeeeee_1_0.json"),
    }


def test_centerline_absolute_axis_aligned() -> None:
    pts = geom._build_square_spiral_centerline_absolute(turns=2, outer=40.0, trace=1.0, gap=0.5, z=0.0)
    assert len(pts) == 9
    assert pts[0] == (-19.5, 19.5, 0.0)
    assert pts[4] == (-19.5, 18.0, 0.0)
    assert pts[5] == (-18.0, 18.0, 0.0)

    checks = geom._compute_axis_checks(pts, eps=1e-6)
    assert all(check["is_vertical"] or check["is_horizontal"] for check in checks)


def test_pitch_checks_consistent() -> None:
    pts = geom._build_square_spiral_centerline_absolute(turns=5, outer=48.0, trace=1.0, gap=0.5, z=0.0)
    checks = geom._compute_pitch_checks(pts, trace=1.0, gap=0.5, eps=1e-6)
    assert len(checks) == 4
    for check in checks:
        assert check["pitch_measured"] == pytest.approx(1.5)
        assert check["delta"] <= 1e-6


def test_corner_debug_contains_offsets() -> None:
    pts = geom._build_square_spiral_centerline_absolute(turns=3, outer=44.0, trace=0.8, gap=0.4, z=0.0)
    debug = geom._build_geometry_debug(
        centerline_vertices=pts,
        trace=0.8,
        gap=0.4,
        eps=1e-6,
        cad_probe=[],
        in_region_ok=True,
        violations=[],
    )

    assert debug["corner_debug"][0]["corner_type"] == "endpoint"
    assert debug["corner_debug"][-1]["corner_type"] == "endpoint"
    right_turn_count = sum(1 for corner in debug["corner_debug"] if corner["corner_type"] == "right_turn")
    assert right_turn_count >= 3

    non_endpoints = [corner for corner in debug["corner_debug"] if corner["corner_type"] != "endpoint"]
    assert all(corner["offset_applied"] is not None for corner in non_endpoints)


def test_bbox_violations_ignores_tiny_fp_overflow() -> None:
    violations = geom._bbox_violations(
        object_name="coil_tx_vertical_test",
        bbox=[0.0, 0.0, 0.0, 100.0 + 1.11022302462516e-13, 50.0, 10.0],
        region_kind="tx_region_vertical",
        region_min=(0.0, 0.0, 0.0),
        region_max=(100.0, 50.0, 10.0),
    )
    assert violations == []


def test_build_square_spiral_writes_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)

    metadata = geom.build_square_spiral_from_manifest(_manifest(tmp_path))

    assert metadata["design_id"] == "abcd1234_eeeeeeee_1_0"
    assert metadata["design_unique_hash"] == "abcd1234"
    assert metadata["toml_space_hash"] == "eeeeeeee"
    assert metadata["selected_parameters_max"]["rx_region_thickness_mm"] == 4.0
    assert Path(metadata["metadata_path"]).exists()
    assert metadata["aedt_path"].endswith("abcd1234_eeeeeeee_1_0.aedt")
    assert fake.release_args == (True, True)

    assert metadata["anchor_mode"] == "copper_outer_edge_corner"
    assert len(metadata["scene_objects"]) == 9
    assert {entry["kind"] for entry in metadata["scene_objects"]} == {
        "tv",
        "wall",
        "floor",
        "shelf",
        "tx_region_max",
        "tx_region_vertical",
        "tx_region_dd",
        "rx_region_max",
        "rx_region_actual",
    }
    plane_by_kind = {entry["kind"]: entry["plane"] for entry in metadata["scene_objects"]}
    scene_by_kind = {entry["kind"]: entry for entry in metadata["scene_objects"]}
    assert plane_by_kind["tv"] == "YZ"
    assert plane_by_kind["wall"] == "YZ"
    assert plane_by_kind["floor"] == "XY"
    assert plane_by_kind["shelf"] == "XY"
    assert plane_by_kind["tx_region_max"] == "XY"
    assert plane_by_kind["tx_region_vertical"] == "XY"
    assert plane_by_kind["tx_region_dd"] == "XY"
    assert plane_by_kind["rx_region_max"] == "YZ"
    assert plane_by_kind["rx_region_actual"] == "YZ"
    # Floor starts on the ZY plane and is placed below XY.
    assert scene_by_kind["floor"]["origin_xyz"][0] == 0.0
    assert scene_by_kind["floor"]["origin_xyz"][2] < 0.0
    assert scene_by_kind["shelf"]["origin_xyz"][2] == 0.0
    assert scene_by_kind["shelf"]["size_xyz"][2] == 400.0
    assert scene_by_kind["shelf"]["size_xyz"][0] == pytest.approx(max(350.0, scene_by_kind["tx_region_max"]["size_xyz"][0] * 2.5))
    # Wall is attached to ZY and extends to -X.
    assert scene_by_kind["wall"]["origin_xyz"][0] < 0.0
    # TV and RX regions are attached to ZY and extend to +X.
    assert scene_by_kind["tv"]["origin_xyz"][0] == 0.0
    assert scene_by_kind["rx_region_actual"]["origin_xyz"][0] == 0.0
    assert scene_by_kind["tv"]["origin_xyz"][2] == 700.0
    assert scene_by_kind["tv"]["size_xyz"][0] == 9.0
    # TX region bottom touches shelf top.
    shelf_top_z = scene_by_kind["shelf"]["origin_xyz"][2] + scene_by_kind["shelf"]["size_xyz"][2]
    assert scene_by_kind["tx_region_max"]["origin_xyz"][2] == shelf_top_z
    # TX 2-part split is stacked contiguously with bottom leftover space.
    tx_max_z0 = scene_by_kind["tx_region_max"]["origin_xyz"][2]
    tx_max_z1 = tx_max_z0 + scene_by_kind["tx_region_max"]["size_xyz"][2]
    dd_z0 = scene_by_kind["tx_region_dd"]["origin_xyz"][2]
    dd_z1 = dd_z0 + scene_by_kind["tx_region_dd"]["size_xyz"][2]
    vertical_z0 = scene_by_kind["tx_region_vertical"]["origin_xyz"][2]
    vertical_z1 = vertical_z0 + scene_by_kind["tx_region_vertical"]["size_xyz"][2]
    assert vertical_z0 == dd_z1
    assert dd_z0 >= tx_max_z0
    assert tx_max_z1 == vertical_z1
    assert (scene_by_kind["tx_region_dd"]["size_xyz"][2] + scene_by_kind["tx_region_vertical"]["size_xyz"][2]) <= scene_by_kind["tx_region_max"]["size_xyz"][2]
    # TX regions are entirely on +X side and do not cross the YZ plane.
    assert scene_by_kind["tx_region_max"]["origin_xyz"][0] == 0.0
    assert scene_by_kind["tx_region_vertical"]["origin_xyz"][0] == 0.0
    assert scene_by_kind["tx_region_dd"]["origin_xyz"][0] == 0.0
    expected_leftover = scene_by_kind["tx_region_max"]["size_xyz"][2] - scene_by_kind["tx_region_vertical"]["size_xyz"][2] - scene_by_kind["tx_region_dd"]["size_xyz"][2]
    assert scene_by_kind["tx_region_dd"]["origin_xyz"][2] == pytest.approx(tx_max_z0 + expected_leftover)
    # RX region bottom is fixed at +1mm from TV bottom.
    assert scene_by_kind["rx_region_actual"]["origin_xyz"][2] == scene_by_kind["tv"]["origin_xyz"][2] + 1.0
    # RX actual thickness must match RX max thickness.
    assert scene_by_kind["rx_region_actual"]["size_xyz"][0] == scene_by_kind["rx_region_max"]["size_xyz"][0]
    rx_coil_probe = next(probe for probe in metadata["debug"]["cad_probe"] if probe["object_name"].startswith("coil_rx_dd_"))
    tx_vertical_probe = next(probe for probe in metadata["debug"]["cad_probe"] if probe["object_name"].startswith("coil_tx_vertical_"))
    # TX vertical coil must be in a vertical plane (ZX): y must be constant.
    assert tx_vertical_probe["bbox"][1] == pytest.approx(tx_vertical_probe["bbox"][4], abs=1e-6)
    # Fake CAD probe uses centerline points only (no xsection), so z_min reflects centerline bottom.
    expected_rx_centerline_z_min = (
        scene_by_kind["rx_region_actual"]["origin_xyz"][2]
        + (metadata["selected_group_geometry"][2]["trace"] / 2.0)
        + 1e-6
    )
    assert rx_coil_probe["bbox"][2] == pytest.approx(expected_rx_centerline_z_min, abs=1e-4)
    # RX coil centerline is attached to +X face side with face clearance considered.
    expected_rx_centerline_x = (
        scene_by_kind["rx_region_actual"]["origin_xyz"][0]
        + scene_by_kind["rx_region_actual"]["size_xyz"][0]
        - metadata["selected_parameters"]["rx_face_clearance_mm"]
        - metadata["selected_parameters"]["cu_thickness"]
    )
    assert rx_coil_probe["bbox"][0] == pytest.approx(expected_rx_centerline_x)
    assert rx_coil_probe["bbox"][3] == pytest.approx(expected_rx_centerline_x)
    # ZX symmetry contract: Y-centered placement.
    for kind in (
        "floor",
        "shelf",
        "wall",
        "tv",
        "tx_region_max",
        "tx_region_vertical",
        "tx_region_dd",
        "rx_region_max",
        "rx_region_actual",
    ):
        assert scene_by_kind[kind]["origin_xyz"][1] == pytest.approx(-scene_by_kind[kind]["size_xyz"][1] / 2.0)
    assert all(entry["non_model"] for entry in metadata["scene_objects"])
    assert any(name.startswith("scene_tv_") for name in metadata["object_names"])
    assert any(name.startswith("scene_wall_") for name in metadata["object_names"])
    assert any(name.startswith("scene_floor_") for name in metadata["object_names"])
    assert any(name.startswith("scene_shelf_") for name in metadata["object_names"])
    assert any(name.startswith("scene_tx_region_max_") for name in metadata["object_names"])
    assert any(name.startswith("scene_tx_region_vertical_") for name in metadata["object_names"])
    assert any(name.startswith("scene_tx_region_dd_") for name in metadata["object_names"])
    assert any(name.startswith("scene_rx_region_max_") for name in metadata["object_names"])
    assert any(name.startswith("scene_rx_region_actual_") for name in metadata["object_names"])
    assert set(metadata["group_objects"].keys()) == {"tx_dd", "tx_vertical", "rx_dd"}
    assert len(metadata["group_objects"]["tx_dd"]) == 2
    assert len(metadata["group_objects"]["tx_vertical"]) == 1
    assert len(metadata["group_objects"]["rx_dd"]) == 1
    assert len(metadata["unite_groups"]["tx"]) == 3
    assert len(metadata["unite_groups"]["rx"]) == 1
    assert len(metadata["group_endpoints"]) == 4
    assert len(metadata["coil_polarity"]) == 4
    assert all(entry["present"] for entry in metadata["group_endpoints"])
    assert all(("start_label" in entry and "end_label" in entry) for entry in metadata["group_endpoints"])
    assert metadata["debug"]["constraints_ok"] is True
    assert len(metadata["debug"]["centerline_vertices"]) == 24
    assert len(metadata["debug"]["cad_probe"]) == 16

    assert len(fake.modeler.polyline_calls) == 4
    assert fake.design_vars["spec_tx_dd_outer_x"] == "48.0mm"
    assert fake.design_vars["spec_fr4_er"] == "4.4"
    assert fake.design_vars["group_geom_tx_dd_turn_count_max"] == "5"
    assert fake.design_vars["pcb_tx_main_0_position_z_mm"] == "0.0mm"
    for call in fake.modeler.polyline_calls:
        assert call["xsection_height"] == 0.035
    scene_boxes = [call for call in fake.modeler.box_calls if str(call["name"]).startswith("scene_")]
    assert len(scene_boxes) == 9
    assert all(call["non_model"] is True for call in scene_boxes)
    fr4_boxes = [call for call in fake.modeler.box_calls if str(call["name"]).startswith("fr4_")]
    assert len(fr4_boxes) == 3
    assert len(fake.modeler.subtract_calls) == 1
    subtract_call = fake.modeler.subtract_calls[0]
    assert len(cast(list[str], subtract_call["blank_list"])) == len(fr4_boxes)
    assert any(str(name).startswith("coil_tx_dd_") for name in cast(list[str], subtract_call["tool_list"]))
    assert any(str(name).startswith("coil_tx_vertical_") for name in cast(list[str], subtract_call["tool_list"]))
    assert any(str(name).startswith("coil_rx_dd_") for name in cast(list[str], subtract_call["tool_list"]))
    assert cast(bool, subtract_call["keep_originals"]) is True


def test_tx_vertical_span_distributes_on_y_and_stays_in_vertical_z_region(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_coil_groups"][1]["requested_count"] = 2
    manifest["selected_coil_groups"][1]["selected_count"] = 2
    manifest["selected_coil_groups"][1]["spacing_mm"] = 10.0

    metadata = geom.build_square_spiral_from_manifest(manifest)

    scene_by_kind = {entry["kind"]: entry for entry in metadata["scene_objects"]}
    vertical_region = scene_by_kind["tx_region_vertical"]
    region_center_y = vertical_region["origin_xyz"][1] + (vertical_region["size_xyz"][1] / 2.0)
    region_min_z = vertical_region["origin_xyz"][2]
    region_max_z = vertical_region["origin_xyz"][2] + vertical_region["size_xyz"][2]

    tx_vertical_probes = sorted(
        (
            probe
            for probe in metadata["debug"]["cad_probe"]
            if probe["object_name"].startswith("coil_tx_vertical_")
        ),
        key=lambda probe: probe["object_name"],
    )
    assert len(tx_vertical_probes) == 2

    y_centers = [(probe["bbox"][1] + probe["bbox"][4]) / 2.0 for probe in tx_vertical_probes]
    assert y_centers[0] == pytest.approx(region_center_y - 5.0, abs=1e-6)
    assert y_centers[1] == pytest.approx(region_center_y + 5.0, abs=1e-6)

    eps = 1e-6
    for probe in tx_vertical_probes:
        z_min = probe["bbox"][2]
        z_max = probe["bbox"][5]
        assert z_min >= (region_min_z - eps)
        assert z_max <= (region_max_z + eps)

    fr4_boxes = [call for call in fake.modeler.box_calls if str(call["name"]).startswith("fr4_")]
    assert len(fr4_boxes) == 4


def test_tx_vertical_four_instances_follow_half_step_pattern(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_coil_groups"][1]["requested_count"] = 4
    manifest["selected_coil_groups"][1]["selected_count"] = 4
    manifest["selected_coil_groups"][1]["spacing_mm"] = 30.0  # d = 10

    metadata = geom.build_square_spiral_from_manifest(manifest)
    scene_by_kind = {entry["kind"]: entry for entry in metadata["scene_objects"]}
    vertical_region = scene_by_kind["tx_region_vertical"]
    region_center_y = vertical_region["origin_xyz"][1] + (vertical_region["size_xyz"][1] / 2.0)
    tx_vertical_probes = sorted(
        (
            probe
            for probe in metadata["debug"]["cad_probe"]
            if probe["object_name"].startswith("coil_tx_vertical_")
        ),
        key=lambda probe: probe["object_name"],
    )
    assert len(tx_vertical_probes) == 4
    y_centers = sorted((probe["bbox"][1] + probe["bbox"][4]) / 2.0 for probe in tx_vertical_probes)
    assert y_centers[0] == pytest.approx(region_center_y - 15.0, abs=1e-6)
    assert y_centers[1] == pytest.approx(region_center_y - 5.0, abs=1e-6)
    assert y_centers[2] == pytest.approx(region_center_y + 5.0, abs=1e-6)
    assert y_centers[3] == pytest.approx(region_center_y + 15.0, abs=1e-6)


def test_tx_vertical_three_instances_middle_touches_x_axis_and_others_are_symmetric(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_coil_groups"][1]["requested_count"] = 3
    manifest["selected_coil_groups"][1]["selected_count"] = 3
    manifest["selected_coil_groups"][1]["spacing_mm"] = 20.0  # d = 10

    metadata = geom.build_square_spiral_from_manifest(manifest)
    scene_by_kind = {entry["kind"]: entry for entry in metadata["scene_objects"]}
    vertical_region = scene_by_kind["tx_region_vertical"]
    region_center_y = vertical_region["origin_xyz"][1] + (vertical_region["size_xyz"][1] / 2.0)
    region_min_x = vertical_region["origin_xyz"][0]
    region_max_x = vertical_region["origin_xyz"][0] + vertical_region["size_xyz"][0]
    trace = next(entry for entry in metadata["selected_group_geometry"] if entry["kind"] == "tx_vertical")["trace"]
    tx_vertical_probes = sorted(
        (
            probe
            for probe in metadata["debug"]["cad_probe"]
            if probe["object_name"].startswith("coil_tx_vertical_")
        ),
        key=lambda probe: probe["object_name"],
    )
    assert len(tx_vertical_probes) == 3
    y_centers = sorted((probe["bbox"][1] + probe["bbox"][4]) / 2.0 for probe in tx_vertical_probes)
    assert y_centers[0] == pytest.approx(region_center_y - 10.0, abs=1e-6)
    assert y_centers[1] == pytest.approx(region_center_y + (trace / 2.0), abs=1e-6)
    assert y_centers[2] == pytest.approx(region_center_y + 10.0, abs=1e-6)
    assert y_centers[0] == pytest.approx(2.0 * region_center_y - y_centers[2], abs=1e-6)

    endpoints = sorted(
        [entry for entry in metadata["group_endpoints"] if entry["group_kind"] == "tx_vertical"],
        key=lambda entry: (entry["start_xyz"][1] + entry["end_xyz"][1]) / 2.0,
    )
    assert len(endpoints) == 3
    bridge_calls = sorted(
        [
            call
            for call in fake.modeler.polyline_calls
            if str(call["name"]).startswith("bridge_tx_vertical_link_")
        ],
        key=lambda call: str(call["name"]),
    )
    assert len(bridge_calls) == 2
    assert len(fake.modeler.cover_calls) == 2
    assert len(fake.modeler.thicken_calls) == 2
    for idx, bridge_call in enumerate(bridge_calls):
        expected_start = endpoints[idx]["start_xyz"]
        source_end = endpoints[idx]["end_xyz"]
        target_start = endpoints[idx + 1]["start_xyz"]
        expected_end = endpoints[idx + 1]["end_xyz"]
        x_margin = trace / 2.0
        min_x_allowed = region_min_x + x_margin
        max_x_allowed = region_max_x - x_margin
        source_dx = source_end[0] - expected_start[0]
        source_anchor_x = expected_start[0] if abs(source_dx) <= 1e-9 else (expected_start[0] + math.copysign(x_margin, source_dx))
        target_dx = target_start[0] - expected_end[0]
        target_anchor_x = expected_end[0] if abs(target_dx) <= 1e-9 else (expected_end[0] + math.copysign(x_margin, target_dx))
        expected_start_x = min(max(source_anchor_x, min_x_allowed), max_x_allowed)
        expected_end_x = min(max(target_anchor_x, min_x_allowed), max_x_allowed)
        points = cast(list[list[float]], bridge_call["points"])
        assert len(points) == 4
        assert points[0][0] == pytest.approx(expected_start_x, abs=1e-6)
        assert points[1][0] == pytest.approx(expected_start_x, abs=1e-6)
        assert points[0][1] == pytest.approx(expected_start[1], abs=1e-6)
        assert points[1][1] == pytest.approx(expected_start[1], abs=1e-6)
        assert abs(points[1][2] - points[0][2]) == pytest.approx(trace, abs=1e-6)
        assert ((points[0][2] + points[1][2]) / 2.0) == pytest.approx(expected_start[2], abs=1e-6)
        assert points[2][0] == pytest.approx(expected_end_x, abs=1e-6)
        assert points[3][0] == pytest.approx(expected_end_x, abs=1e-6)
        assert points[2][1] == pytest.approx(expected_end[1], abs=1e-6)
        assert points[3][1] == pytest.approx(expected_end[1], abs=1e-6)
        assert abs(points[2][2] - points[3][2]) == pytest.approx(trace, abs=1e-6)
        assert ((points[2][2] + points[3][2]) / 2.0) == pytest.approx(expected_end[2], abs=1e-6)
        assert fake.modeler.thicken_calls[idx]["thickness"] == pytest.approx(
            metadata["selected_parameters"]["cu_thickness"] * 4.0, abs=1e-9
        )


def test_tx_vertical_single_instance_middle_copper_outer_edge_touches_x_axis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    metadata = geom.build_square_spiral_from_manifest(_manifest(tmp_path))
    scene_by_kind = {entry["kind"]: entry for entry in metadata["scene_objects"]}
    vertical_region = scene_by_kind["tx_region_vertical"]
    region_center_y = vertical_region["origin_xyz"][1] + (vertical_region["size_xyz"][1] / 2.0)
    trace = next(entry for entry in metadata["selected_group_geometry"] if entry["kind"] == "tx_vertical")["trace"]
    tx_vertical_probe = next(
        probe for probe in metadata["debug"]["cad_probe"] if probe["object_name"].startswith("coil_tx_vertical_")
    )
    y_center = (tx_vertical_probe["bbox"][1] + tx_vertical_probe["bbox"][4]) / 2.0
    assert y_center == pytest.approx(region_center_y + (trace / 2.0), abs=1e-6)
    bridge_calls = [
        call
        for call in fake.modeler.polyline_calls
        if str(call["name"]).startswith("bridge_tx_vertical_link_")
    ]
    assert len(bridge_calls) == 0
    assert len(fake.modeler.cover_calls) == 0
    assert len(fake.modeler.thicken_calls) == 0


def test_tx_vertical_offset_rejects_invalid_count_or_negative_d() -> None:
    with pytest.raises(ValueError, match="selected_count must be >= 1"):
        geom._coil_instance_offset("tx_vertical", instance_index=0, instance_count=0, spacing_mm=0.0, trace_mm=0.8)
    with pytest.raises(ValueError, match="center gap d must be >= 0"):
        geom._coil_instance_offset("tx_vertical", instance_index=0, instance_count=2, spacing_mm=-1.0, trace_mm=0.8)


def test_tx_vertical_multiple_instances_copy_zx_fr4_per_vertical_coil(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_coil_groups"][1]["requested_count"] = 3
    manifest["selected_coil_groups"][1]["selected_count"] = 3
    manifest["selected_coil_groups"][1]["spacing_mm"] = 12.0

    metadata = geom.build_square_spiral_from_manifest(manifest)

    tx_zx_fr4 = sorted(
        [
            name
            for name in metadata["em_ready_objects"]["fr4_objects"]
            if name.startswith("fr4_tx_main_0_zx_")
        ]
    )
    rx_yz_fr4 = sorted(
        [
            name
            for name in metadata["em_ready_objects"]["fr4_objects"]
            if name.startswith("fr4_rx_main_0_yz_")
        ]
    )
    tx_xy_fr4 = sorted(
        [
            name
            for name in metadata["em_ready_objects"]["fr4_objects"]
            if name.startswith("fr4_tx_main_0_xy_")
        ]
    )

    assert len(tx_zx_fr4) == 1
    assert len(tx_xy_fr4) == 1
    assert len(rx_yz_fr4) == 1
    assert len(metadata["group_objects"]["tx_vertical"]) == 1


def test_no_duplicate_tx_vertical_bboxes_after_fixed_topology_normalization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_coil_groups"][1]["requested_count"] = 2
    manifest["selected_coil_groups"][1]["selected_count"] = 2
    manifest["selected_coil_groups"][1]["spacing_mm"] = 10.0
    manifest["selected_pcbs"] = [
        {
            "id": "tx_main_0",
            "role": "tx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
                {"kind": "tx_vertical", "selector_mode": "all", "selector_index": None},
            ],
        },
        {
            "id": "tx_main_1",
            "role": "tx",
            "position": (0.0, 0.0, 3.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "relative_to_pcb",
            "z_relative_base_id": "tx_main_0",
            "z_delta_path": "pcb_spacing.tx_main_1_z_from_tx_main_0_mm",
            "mounts": [
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 2},
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 3},
                {"kind": "tx_vertical", "selector_mode": "all", "selector_index": None},
            ],
        },
        {
            "id": "tx_vertical_0",
            "role": "tx",
            "position": (0.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [],
        },
        {
            "id": "rx_main_0",
            "role": "rx",
            "position": (0.0, 0.0, 110.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [{"kind": "rx_dd", "selector_mode": "index", "selector_index": 0}],
        },
        {
            "id": "rx_main_1",
            "role": "rx",
            "position": (0.0, 0.0, 112.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [{"kind": "rx_dd", "selector_mode": "index", "selector_index": 1}],
        },
        {
            "id": "tx_opt_0",
            "role": "tx",
            "position": (40.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [{"kind": "tx_vertical", "selector_mode": "all", "selector_index": None}],
        },
        {
            "id": "tx_opt_1",
            "role": "tx",
            "position": (-40.0, 0.0, 0.0),
            "rotation_deg": 0.0,
            "present": False,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [],
        },
        {
            "id": "rx_opt_0",
            "role": "rx",
            "position": (40.0, 0.0, 110.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [{"kind": "rx_dd", "selector_mode": "index", "selector_index": 0}],
        },
        {
            "id": "rx_opt_1",
            "role": "rx",
            "position": (-40.0, 0.0, 110.0),
            "rotation_deg": 0.0,
            "present": False,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [],
        },
    ]

    with pytest.warns(UserWarning):
        normalized = resolver._normalize_pcbs_fixed_topology(cast(list[ResolvedPcbInstance], manifest["selected_pcbs"]))
    manifest["selected_pcbs"] = normalized

    metadata = geom.build_square_spiral_from_manifest(manifest)
    tx_vertical_bboxes = [
        tuple(round(coord, 6) for coord in probe["bbox"])
        for probe in metadata["debug"]["cad_probe"]
        if probe["object_name"].startswith("coil_tx_vertical_")
    ]
    assert len(tx_vertical_bboxes) == 2
    assert len(set(tx_vertical_bboxes)) == len(tx_vertical_bboxes)


def test_build_square_spiral_invalid_params(tmp_path: Path) -> None:
    bad = _manifest(tmp_path)
    bad["selected_parameters"]["cu_thickness"] = 0.0

    with pytest.raises(ValueError, match="cu_thickness"):
        geom.build_square_spiral_from_manifest(bad)


def test_build_square_spiral_invalid_absolute_geometry() -> None:
    with pytest.raises(ValueError, match="invalid spiral dimensions"):
        geom._build_square_spiral_centerline_absolute(turns=12, outer=20.0, trace=1.5, gap=0.5, z=0.0)


def test_pitch_checks_with_zero_gap() -> None:
    pts = geom._build_square_spiral_centerline_absolute(turns=4, outer=40.0, trace=1.0, gap=0.0, z=0.0)
    checks = geom._compute_pitch_checks(pts, trace=1.0, gap=0.0, eps=1e-6)
    for check in checks:
        assert check["pitch_measured"] == pytest.approx(1.0)
        assert check["delta"] <= 1e-6


def test_tx_dd_endpoint_extension_is_half_trace() -> None:
    raw_points = geom._txdd_right_points(
        turns=5,
        outer_x=48.0,
        outer_y=48.0,
        trace=1.0,
        gap=0.5,
        instance_count=2,
        layer_index=None,
    )
    extended_points = geom._extend_endpoints(raw_points, extension=0.5)
    start_delta = (
        ((extended_points[0][0] - raw_points[0][0]) ** 2)
        + ((extended_points[0][1] - raw_points[0][1]) ** 2)
        + ((extended_points[0][2] - raw_points[0][2]) ** 2)
    ) ** 0.5
    end_delta = (
        ((extended_points[-1][0] - raw_points[-1][0]) ** 2)
        + ((extended_points[-1][1] - raw_points[-1][1]) ** 2)
        + ((extended_points[-1][2] - raw_points[-1][2]) ** 2)
    ) ** 0.5
    assert start_delta == pytest.approx(0.5)
    assert end_delta == pytest.approx(0.5)


def test_tx_dd_symmetric_precheck_fails_for_tx_dd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_coil_groups"][0]["spacing_mm"] = 170.0

    with pytest.raises(RuntimeError, match="tx_dd symmetric placement out of region"):
        geom.build_square_spiral_from_manifest(manifest)


def test_tx_vertical_large_requested_turns_fail_when_infeasible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_group_geometry"][1]["turn_count_max"] = 11
    manifest["selected_group_geometry"][1]["trace"] = 2.932558139534884
    manifest["selected_group_geometry"][1]["gap"] = 2.7395348837209306

    with pytest.raises(RuntimeError, match="Infeasible turn_count_max for tx_vertical"):
        geom.build_square_spiral_from_manifest(manifest)


def test_tx_dd_large_requested_turns_fail_when_infeasible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_group_geometry"][0]["turn_count_max"] = 8
    manifest["selected_group_geometry"][0]["trace"] = 2.7953488372093025
    manifest["selected_group_geometry"][0]["gap"] = 2.5930232558139537

    with pytest.raises(RuntimeError, match="Infeasible turn_count_max for tx_dd"):
        geom.build_square_spiral_from_manifest(manifest)


def test_rx_dd_edge_gap_must_be_non_negative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_coil_groups"][2]["spacing_mm"] = -0.1

    with pytest.raises(RuntimeError, match="rx_dd edge gap must be >= 0"):
        geom.build_square_spiral_from_manifest(manifest)


def test_tx_dd_two_coils_use_single_layer_when_selected_count_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_pcbs"][0]["mounts"] = [
        {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
        {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
        {"kind": "tx_vertical", "selector_mode": "all", "selector_index": None},
    ]
    manifest["selected_coil_groups"][0]["selected_count"] = 2
    manifest["selected_coil_groups"][0]["requested_count"] = 2
    manifest["selected_coil_groups"][0]["spacing_mm"] = 25.0

    metadata = geom.build_square_spiral_from_manifest(manifest)
    tx_dd_probes = sorted(
        [probe for probe in metadata["debug"]["cad_probe"] if probe["object_name"].startswith("coil_tx_dd_")],
        key=lambda probe: probe["object_name"],
    )
    assert len(tx_dd_probes) == 2
    z_centers = [((probe["bbox"][2] + probe["bbox"][5]) / 2.0) for probe in tx_dd_probes]
    assert z_centers[0] == pytest.approx(z_centers[1], abs=1e-6)
    tx_dd_calls = sorted(
        [call for call in fake.modeler.polyline_calls if str(call["name"]).startswith("coil_tx_dd_")],
        key=lambda call: str(call["name"]),
    )
    assert len(tx_dd_calls) == 2
    sign_a = _turn_sign_xy(tx_dd_calls[0]["points"])  # type: ignore[arg-type]
    sign_b = _turn_sign_xy(tx_dd_calls[1]["points"])  # type: ignore[arg-type]
    # Left must be generated by mirror of the right instance.
    assert sign_a * sign_b < 0.0
    assert len(fake.modeler.duplicate_mirror_calls) == 1
    mirror_call = fake.modeler.duplicate_mirror_calls[0]
    assert mirror_call["vector"] == [0.0, 1.0, 0.0]


def test_tx_dd_right_only_rule_for_single_layer_labels_and_winding_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_pcbs"][0]["mounts"] = [
        {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
        {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
        {"kind": "tx_vertical", "selector_mode": "all", "selector_index": None},
    ]

    metadata = geom.build_square_spiral_from_manifest(manifest)
    endpoints = _endpoint_map(metadata)
    polarity = _polarity_map(metadata)

    left_key = ("tx_dd", "tx_main_0", 0)
    right_key = ("tx_dd", "tx_main_0", 1)

    # Right-only override.
    assert endpoints[right_key]["start_label"] == "C"
    assert endpoints[right_key]["end_label"] == "d"
    right_call = next(
        call for call in fake.modeler.polyline_calls if str(call["name"]).startswith("coil_tx_dd_g1_b0_")
    )
    right_points = cast(list[list[float]], right_call["points"])
    assert polarity[right_key]["current_direction"] == _direction_from_xy_points(right_points)
    _assert_no_topology_break(right_points)
    right_xs = [point[0] for point in right_points]
    right_ys = [point[1] for point in right_points]
    assert right_points[0][0] == pytest.approx(max(right_xs))
    assert right_points[0][1] == pytest.approx(min(right_ys))
    assert right_points[-1][0] < max(right_xs)
    assert right_points[-1][0] > min(right_xs)
    assert right_points[-1][1] > min(right_ys)
    assert right_points[-1][1] < max(right_ys)
    # Left keeps default endpoint and polarity contract.
    assert endpoints[left_key]["start_label"] == "A"
    assert endpoints[left_key]["end_label"] == "a"
    left_call = next(call for call in fake.modeler.polyline_calls if "_mirror_" in str(call["name"]))
    left_points = cast(list[list[float]], left_call["points"])
    assert polarity[left_key]["current_direction"] == _direction_from_xy_points(left_points)


def test_tx_dd_left_only_mount_fails_without_mirror_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_pcbs"][0]["mounts"] = [
        {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
        {"kind": "tx_vertical", "selector_mode": "all", "selector_index": None},
    ]

    with pytest.raises(RuntimeError, match="tx_dd mirror source missing"):
        geom.build_square_spiral_from_manifest(manifest)


def test_tx_dd_four_coils_use_two_layers_when_selected_count_four(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_coil_groups"][0]["selected_count"] = 4
    manifest["selected_coil_groups"][0]["requested_count"] = 4
    manifest["selected_coil_groups"][0]["spacing_mm"] = 25.0
    manifest["selected_pcbs"][0]["mounts"] = [
        {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
        {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
        {"kind": "tx_vertical", "selector_mode": "all", "selector_index": None},
    ]
    manifest["selected_pcbs"].append(
        {
            "id": "tx_main_1",
            "role": "tx",
            "position": (0.0, 0.0, 3.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 2},
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 3},
                {"kind": "tx_vertical", "selector_mode": "all", "selector_index": None},
            ],
        }
    )

    metadata = geom.build_square_spiral_from_manifest(manifest)
    scene_by_kind = {entry["kind"]: entry for entry in metadata["scene_objects"]}
    region_min_y = scene_by_kind["tx_region_dd"]["origin_xyz"][1]
    region_max_y = region_min_y + scene_by_kind["tx_region_dd"]["size_xyz"][1]
    region_center_y = (region_min_y + region_max_y) / 2.0
    outer_y = metadata["selected_parameters"]["tx_dd_outer_y"]
    pair_center_distance = outer_y + 25.0
    expected_y = sorted([region_center_y - (pair_center_distance / 2.0), region_center_y + (pair_center_distance / 2.0)])

    tx_dd_probes = sorted(
        [probe for probe in metadata["debug"]["cad_probe"] if probe["object_name"].startswith("coil_tx_dd_")],
        key=lambda probe: probe["object_name"],
    )
    assert len(tx_dd_probes) == 4
    bridge_names = [name for name in metadata["group_objects"]["tx_dd"] if name.startswith("bridge_tx_dd_a_link_")]
    assert len(bridge_names) == 0
    txdd_unite_calls = [
        cast(list[str], call["assignment"])
        for call in fake.modeler.unite_calls
        if any(str(name).startswith("bridge_tx_dd_a_link_") for name in cast(list[str], call["assignment"]))
    ]
    assert len(txdd_unite_calls) == 1
    unite_assignment = txdd_unite_calls[0]
    assert len(unite_assignment) == 3
    assert sum(1 for name in unite_assignment if str(name).startswith("coil_tx_dd_")) == 2
    assert any(str(name).startswith("bridge_tx_dd_a_link_") for name in unite_assignment)
    right_united_name = str(unite_assignment[0])
    assert right_united_name in metadata["group_objects"]["tx_dd"]
    assert all(str(name) not in metadata["group_objects"]["tx_dd"] for name in unite_assignment[1:])
    bridge_probe = next(
        probe for probe in metadata["debug"]["cad_probe"] if str(probe["object_name"]).startswith("bridge_tx_dd_a_link_")
    )
    bridge_bbox = bridge_probe["bbox"]
    bridge_trace = metadata["selected_group_geometry"][0]["trace"]
    assert (bridge_bbox[3] - bridge_bbox[0]) == pytest.approx(bridge_trace)
    assert (bridge_bbox[4] - bridge_bbox[1]) == pytest.approx(bridge_trace)
    assert (bridge_bbox[5] - bridge_bbox[2]) >= 3.0
    tx_dd_geom = next(entry for entry in metadata["selected_group_geometry"] if entry["kind"] == "tx_dd")
    lower_local_a = geom._txdd_right_points(
        turns=tx_dd_geom["turn_count_max"],
        outer_x=metadata["selected_parameters"]["tx_dd_outer_x"],
        outer_y=metadata["selected_parameters"]["tx_dd_outer_y"],
        trace=tx_dd_geom["trace"],
        gap=tx_dd_geom["gap"],
        instance_count=4,
        layer_index=0,
    )[-1]
    upper_local_a = geom._txdd_right_points(
        turns=tx_dd_geom["turn_count_max"],
        outer_x=metadata["selected_parameters"]["tx_dd_outer_x"],
        outer_y=metadata["selected_parameters"]["tx_dd_outer_y"],
        trace=tx_dd_geom["trace"],
        gap=tx_dd_geom["gap"],
        instance_count=4,
        layer_index=1,
    )[0]
    tx_dd_center_x = scene_by_kind["tx_region_dd"]["origin_xyz"][0] + (metadata["selected_parameters"]["tx_dd_outer_x"] / 2.0)
    transform = manifest["selected_coil_groups"][0]["instance_transforms"][0]
    right_center_y = expected_y[1]
    lower_world_a_x = tx_dd_center_x + transform["dx"] + lower_local_a[0]
    lower_world_a_y = right_center_y + transform["dy"] + lower_local_a[1]
    upper_world_a_x = tx_dd_center_x + transform["dx"] + upper_local_a[0]
    upper_world_a_y = right_center_y + transform["dy"] + upper_local_a[1]
    assert lower_world_a_x == pytest.approx(upper_world_a_x, abs=1e-6)
    assert lower_world_a_y == pytest.approx(upper_world_a_y, abs=1e-6)
    bridge_center_x = (bridge_bbox[0] + bridge_bbox[3]) / 2.0
    bridge_center_y = (bridge_bbox[1] + bridge_bbox[4]) / 2.0
    assert bridge_center_x == pytest.approx(lower_world_a_x, abs=1e-6)
    assert bridge_center_y == pytest.approx(lower_world_a_y, abs=1e-6)
    y_centers = sorted((probe["bbox"][1] + probe["bbox"][4]) / 2.0 for probe in tx_dd_probes)
    assert y_centers[0] == pytest.approx(expected_y[0], abs=0.5)
    assert y_centers[1] == pytest.approx(expected_y[0], abs=0.5)
    # Endpoint extension and partial path can slightly shift right-coil bbox center upward/downward.
    assert y_centers[2] == pytest.approx(expected_y[1], abs=1.0)
    assert y_centers[3] == pytest.approx(expected_y[1], abs=0.5)
    z_centers = sorted((probe["bbox"][2] + probe["bbox"][5]) / 2.0 for probe in tx_dd_probes)
    assert z_centers[1] == pytest.approx(z_centers[0], abs=1e-6)
    assert z_centers[3] == pytest.approx(z_centers[2], abs=1e-6)
    assert z_centers[2] > z_centers[1]
    assert (z_centers[2] - z_centers[1]) >= 3.0


def test_tx_dd_right_only_rule_for_two_layers_orders_by_z_center(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_coil_groups"][0]["selected_count"] = 4
    manifest["selected_coil_groups"][0]["requested_count"] = 4
    manifest["selected_coil_groups"][0]["spacing_mm"] = 25.0
    manifest["selected_pcbs"][0]["mounts"] = [
        {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
        {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
        {"kind": "tx_vertical", "selector_mode": "all", "selector_index": None},
    ]
    manifest["selected_pcbs"].append(
        {
            "id": "tx_main_1",
            "role": "tx",
            "position": (0.0, 0.0, 3.0),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": [
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 2},
                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 3},
                {"kind": "tx_vertical", "selector_mode": "all", "selector_index": None},
            ],
        }
    )

    metadata = geom.build_square_spiral_from_manifest(manifest)
    endpoints = _endpoint_map(metadata)
    polarity = _polarity_map(metadata)

    right_entries: list[tuple[float, str, int, GroupEndpointEntry, CoilPolaritySpec]] = []
    left_entries: list[tuple[float, str, int, GroupEndpointEntry, CoilPolaritySpec]] = []
    for key, entry in endpoints.items():
        if entry["group_kind"] != "tx_dd":
            continue
        pol = polarity[key]
        row = (_endpoint_z_center(entry), key[1], key[2], entry, pol)
        if pol["instance_side"] == "right":
            right_entries.append(row)
        elif pol["instance_side"] == "left":
            left_entries.append(row)

    right_entries.sort(key=lambda item: (item[0], item[1], item[2]))
    left_entries.sort(key=lambda item: (item[0], item[1], item[2]))

    assert len(right_entries) == 2
    assert right_entries[0][3]["start_label"] == "c"
    assert right_entries[0][3]["end_label"] == "A"
    assert right_entries[0][4]["current_direction"] == "ccw"
    assert right_entries[1][3]["start_label"] == "A"
    assert right_entries[1][3]["end_label"] == "d"
    assert right_entries[1][4]["current_direction"] == "ccw"
    right_calls = [
        call
        for call in fake.modeler.polyline_calls
        if str(call["name"]).startswith("coil_tx_dd_")
        and "_mirror_" not in str(call["name"])
        and str(call["name"]).startswith(("coil_tx_dd_g1_", "coil_tx_dd_g3_"))
    ]
    assert len(right_calls) == 2
    right_calls.sort(key=lambda call: float(cast(list[list[float]], call["points"])[0][2]))
    lower_points = cast(list[list[float]], right_calls[0]["points"])
    upper_points = cast(list[list[float]], right_calls[1]["points"])
    _assert_no_topology_break(lower_points)
    _assert_no_topology_break(upper_points)
    lower_xs = [point[0] for point in lower_points]
    lower_ys = [point[1] for point in lower_points]
    assert lower_points[0][0] < max(lower_xs)
    assert lower_points[0][0] > min(lower_xs)
    assert lower_points[0][1] > min(lower_ys)
    assert lower_points[0][1] < max(lower_ys)
    assert lower_points[-1][0] == pytest.approx(min(lower_xs))
    assert lower_points[-1][1] == pytest.approx(max(lower_ys))

    upper_xs = [point[0] for point in upper_points]
    upper_ys = [point[1] for point in upper_points]
    assert upper_points[0][0] == pytest.approx(min(upper_xs))
    assert upper_points[0][1] == pytest.approx(max(upper_ys))
    # Upper layer right is reoriented to A->D->...->C.
    assert upper_points[1][0] == pytest.approx(min(upper_xs))
    assert upper_points[1][1] == pytest.approx(min(upper_ys))
    assert upper_points[2][0] == pytest.approx(max(upper_xs))
    assert upper_points[2][1] == pytest.approx(min(upper_ys))
    assert upper_points[-1][0] < max(upper_xs)
    assert upper_points[-1][0] > min(upper_xs)
    assert upper_points[-1][1] > min(upper_ys)
    assert upper_points[-1][1] < max(upper_ys)
    assert _direction_from_xy_points(lower_points) == right_entries[0][4]["current_direction"]
    assert _direction_from_xy_points(upper_points) == right_entries[1][4]["current_direction"]

    # Left keeps default endpoint and polarity contract.
    assert len(left_entries) == 2
    for _, _, _, endpoint_entry, polarity_entry in left_entries:
        assert endpoint_entry["start_label"] == "A"
        assert endpoint_entry["end_label"] == "a"
        assert polarity_entry["current_direction"] == "cw"
    assert len(fake.modeler.duplicate_mirror_calls) == 2


def test_rx_dd_edge_gap_zero_means_touching_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_pcbs"][1]["mounts"] = [
        {"kind": "rx_dd", "selector_mode": "index", "selector_index": 0},
        {"kind": "rx_dd", "selector_mode": "index", "selector_index": 1},
    ]
    manifest["selected_coil_groups"][2]["spacing_mm"] = 0.0

    metadata = geom.build_square_spiral_from_manifest(manifest)
    rx_dd_probes = sorted(
        [probe for probe in metadata["debug"]["cad_probe"] if probe["object_name"].startswith("coil_rx_dd_")],
        key=lambda probe: probe["object_name"],
    )
    assert len(rx_dd_probes) == 2
    y_gap = rx_dd_probes[1]["bbox"][1] - rx_dd_probes[0]["bbox"][4]
    assert y_gap == pytest.approx(metadata["selected_group_geometry"][2]["trace"], abs=1e-6)
    rx_dd_calls = sorted(
        [call for call in fake.modeler.polyline_calls if str(call["name"]).startswith("coil_rx_dd_")],
        key=lambda call: str(call["name"]),
    )
    assert len(rx_dd_calls) == 2
    sign_a = _turn_sign_yz(rx_dd_calls[0]["points"])  # type: ignore[arg-type]
    sign_b = _turn_sign_yz(rx_dd_calls[1]["points"])  # type: ignore[arg-type]
    assert sign_a * sign_b < 0.0


def test_rx_dd_edge_gap_five_mm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_pcbs"][1]["mounts"] = [
        {"kind": "rx_dd", "selector_mode": "index", "selector_index": 0},
        {"kind": "rx_dd", "selector_mode": "index", "selector_index": 1},
    ]
    manifest["selected_coil_groups"][2]["spacing_mm"] = 5.0

    metadata = geom.build_square_spiral_from_manifest(manifest)
    rx_dd_probes = sorted(
        [probe for probe in metadata["debug"]["cad_probe"] if probe["object_name"].startswith("coil_rx_dd_")],
        key=lambda probe: probe["object_name"],
    )
    assert len(rx_dd_probes) == 2
    y_gap = rx_dd_probes[1]["bbox"][1] - rx_dd_probes[0]["bbox"][4]
    assert y_gap == pytest.approx(5.0 + metadata["selected_group_geometry"][2]["trace"], abs=1e-6)


def test_rx_dd_transform_dz_must_be_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_coil_groups"][2]["instance_transforms"][0]["dz"] = 1.0

    with pytest.raises(RuntimeError, match="rx_dd transform dz must be 0 for bottom-anchor contract"):
        geom.build_square_spiral_from_manifest(manifest)

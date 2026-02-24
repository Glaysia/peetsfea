from __future__ import annotations

from pathlib import Path

import pytest

import peetsfea.backend.pyaedt.geometry.square_spiral as geom
from peetsfea.types.manifest import Manifest


class _FakePoint:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class _FakeEdge:
    def __init__(self, midpoint: _FakePoint) -> None:
        self.midpoint = midpoint


class _FakeObject:
    def __init__(self, name: str, bbox: list[float], edge_samples: list[tuple[float, float]]) -> None:
        self.name = name
        self.bounding_box = bbox
        self.edges = [_FakeEdge(_FakePoint(x, y)) for x, y in edge_samples]


class _FakeModeler:
    def __init__(self) -> None:
        self.polyline_calls: list[dict[str, object]] = []
        self.cylinder_calls: list[dict[str, object]] = []
        self.box_calls: list[dict[str, object]] = []

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
        return _FakeObject(
            name or "polyline",
            [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)],
            edge_samples,
        )

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
        return _FakeObject(
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
        return _FakeObject(
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


def _turn_sign_yz(points: list[list[float]]) -> float:
    assert len(points) >= 3
    ay = points[1][1] - points[0][1]
    az = points[1][2] - points[0][2]
    by = points[2][1] - points[1][1]
    bz = points[2][2] - points[1][2]
    return (ay * bz) - (az * by)


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
            {"kind": "tx_vertical", "turn_count_max": 4, "band_ratio": 0.25, "metal_ratio": 0.9 / 1.3, "trace": 0.9, "gap": 0.4},
            {"kind": "rx_dd", "turn_count_max": 6, "band_ratio": 0.35, "metal_ratio": 1.1 / 1.4, "trace": 1.1, "gap": 0.3},
        ],
        "selected_pcbs": [
            {
                "id": "tx_main_0",
                "role": "tx",
                "position": (0.0, 0.0, 0.0),
                "rotation_deg": 0.0,
                "present": True,
                "mounts": ["tx_dd:0", "tx_vertical:*"],
            },
            {
                "id": "rx_main_0",
                "role": "rx",
                "position": (0.0, 0.0, 110.0),
                "rotation_deg": 0.0,
                "present": True,
                "mounts": ["rx_dd:0"],
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
            "spec_version": "0.1.8",
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
    assert len(metadata["group_objects"]["tx_dd"]) == 1
    assert len(metadata["group_objects"]["tx_vertical"]) == 1
    assert len(metadata["group_objects"]["rx_dd"]) == 1
    assert len(metadata["unite_groups"]["tx"]) == 2
    assert len(metadata["unite_groups"]["rx"]) == 1
    assert len(metadata["group_endpoints"]) == 3
    assert len(metadata["coil_polarity"]) == 3
    assert all(entry["present"] for entry in metadata["group_endpoints"])
    assert metadata["debug"]["constraints_ok"] is True
    assert len(metadata["debug"]["centerline_vertices"]) == 24
    assert len(metadata["debug"]["cad_probe"]) == 15

    assert len(fake.modeler.polyline_calls) == 3
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


def test_tx_dd_symmetric_precheck_fails_for_tx_dd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_coil_groups"][0]["spacing_mm"] = 170.0

    with pytest.raises(RuntimeError, match="tx_dd symmetric placement out of region"):
        geom.build_square_spiral_from_manifest(manifest)


def test_tx_vertical_large_requested_turns_are_clipped_to_fit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_group_geometry"][1]["turn_count_max"] = 11
    manifest["selected_group_geometry"][1]["trace"] = 2.932558139534884
    manifest["selected_group_geometry"][1]["gap"] = 2.7395348837209306

    metadata = geom.build_square_spiral_from_manifest(manifest)

    tx_vertical_calls = [
        call for call in fake.modeler.polyline_calls if str(call["name"]).startswith("coil_tx_vertical_")
    ]
    assert len(tx_vertical_calls) == 1
    # The requested turns are infeasible for the vertical region height; build path must clip turns.
    tx_vertical_points = tx_vertical_calls[0]["points"]
    assert isinstance(tx_vertical_points, list)
    assert len(tx_vertical_points) == 4
    assert len(metadata["group_objects"]["tx_vertical"]) == 1


def test_tx_dd_large_requested_turns_are_clipped_to_fit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_group_geometry"][0]["turn_count_max"] = 8
    manifest["selected_group_geometry"][0]["trace"] = 2.7953488372093025
    manifest["selected_group_geometry"][0]["gap"] = 2.5930232558139537

    metadata = geom.build_square_spiral_from_manifest(manifest)

    tx_dd_calls = [call for call in fake.modeler.polyline_calls if str(call["name"]).startswith("coil_tx_dd_")]
    assert len(tx_dd_calls) == 1
    tx_dd_points = tx_dd_calls[0]["points"]
    assert isinstance(tx_dd_points, list)
    expected_turns = min(
        manifest["selected_group_geometry"][0]["turn_count_max"],
        geom._max_feasible_turns(
            manifest["selected_parameters"]["tx_dd_outer_x"],
            manifest["selected_group_geometry"][0]["trace"],
            manifest["selected_group_geometry"][0]["gap"],
        ),
        geom._max_feasible_turns(
            manifest["selected_parameters"]["tx_dd_outer_y"],
            manifest["selected_group_geometry"][0]["trace"],
            manifest["selected_group_geometry"][0]["gap"],
        ),
    )
    assert expected_turns < manifest["selected_group_geometry"][0]["turn_count_max"]
    assert len(tx_dd_points) == (5 * expected_turns) - 1
    assert len(metadata["group_objects"]["tx_dd"]) == 1


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
    manifest["selected_pcbs"][0]["mounts"] = ["tx_dd:0", "tx_dd:1", "tx_vertical:*"]
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
    assert sign_a * sign_b < 0.0


def test_tx_dd_four_coils_use_two_layers_when_selected_count_four(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_coil_groups"][0]["selected_count"] = 4
    manifest["selected_coil_groups"][0]["requested_count"] = 4
    manifest["selected_coil_groups"][0]["spacing_mm"] = 25.0
    manifest["selected_pcbs"][0]["mounts"] = ["tx_dd:0", "tx_dd:1", "tx_vertical:*"]
    manifest["selected_pcbs"].append(
        {
            "id": "tx_main_1",
            "role": "tx",
            "position": (0.0, 0.0, 2.0),
            "rotation_deg": 0.0,
            "present": True,
            "mounts": ["tx_dd:2", "tx_dd:3", "tx_vertical:*"],
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
    y_centers = sorted((probe["bbox"][1] + probe["bbox"][4]) / 2.0 for probe in tx_dd_probes)
    assert y_centers[0] == pytest.approx(expected_y[0], abs=1e-6)
    assert y_centers[1] == pytest.approx(expected_y[0], abs=1e-6)
    assert y_centers[2] == pytest.approx(expected_y[1], abs=1e-6)
    assert y_centers[3] == pytest.approx(expected_y[1], abs=1e-6)
    z_centers = sorted((probe["bbox"][2] + probe["bbox"][5]) / 2.0 for probe in tx_dd_probes)
    assert z_centers[1] == pytest.approx(z_centers[0], abs=1e-6)
    assert z_centers[3] == pytest.approx(z_centers[2], abs=1e-6)
    assert z_centers[2] > z_centers[1]


def test_rx_dd_edge_gap_zero_means_touching_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)
    manifest = _manifest(tmp_path)
    manifest["selected_pcbs"][1]["mounts"] = ["rx_dd:0", "rx_dd:1"]
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
    manifest["selected_pcbs"][1]["mounts"] = ["rx_dd:0", "rx_dd:1"]
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

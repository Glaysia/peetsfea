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
    ) -> _FakeObject:
        self.box_calls.append({"origin": origin, "sizes": sizes, "name": name, "material": material})
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

    def save_project(self, project_file: str) -> None:
        self.saved_path = project_file

    def release_desktop(self, close_projects: bool = True, close_desktop: bool = True) -> None:
        self.release_args = (close_projects, close_desktop)


def _manifest(tmp_path: Path) -> Manifest:
    return {
        "design_id": "abcd1234_eeeeeeee_1",
        "design_unique_hash": "abcd1234",
        "toml_space_hash": "eeeeeeee",
        "toml_hash": "t" * 64,
        "peetsfea_commit": "c" * 40,
        "seed": 1,
        "backend": "hfss",
        "selected_parameters": {
            "outer_x": 48.0,
            "outer_y": 48.0,
            "turn_count_max": 5,
            "inner_margin_x": 2.0,
            "inner_margin_y": 2.0,
            "tx_dd_pair_spacing_mm": 40.0,
            "rx_dd_pair_spacing_mm": 40.0,
            "tx_vertical_span_mm": 10.0,
            "tv_width_mm": 1200.0,
            "tv_height_mm": 700.0,
            "tv_thickness_mm": 45.0,
            "tx_region_outer_w_mm": 300.0,
            "tx_region_outer_h_mm": 200.0,
            "tx_region_thickness_mm": 20.0,
            "rx_region_outer_w_mm": 280.0,
            "rx_region_outer_h_mm": 180.0,
            "rx_region_thickness_mm": 18.0,
            "wall_thickness_mm": 200.0,
            "wall_size_y_mm": 4000.0,
            "wall_size_z_mm": 3000.0,
            "floor_thickness_mm": 300.0,
            "floor_size_x_mm": 5000.0,
            "floor_size_y_mm": 5000.0,
            "trace_profile_base": 1.0,
            "trace_profile_outer_bias": 0.1,
            "trace_profile_inner_bias": -0.1,
            "trace_profile_clamp_min": 0.2,
            "gap_profile_base": 0.5,
            "gap_profile_outer_bias": 0.05,
            "gap_profile_inner_bias": -0.05,
            "gap_profile_clamp_min": 0.15,
            "turns": 5,
            "outer": 48.0,
            "trace": 1.0,
            "gap": 0.5,
            "via_diameter": 0.5,
            "pcb_thickness": 1.6,
            "cu_thickness": 0.035,
            "fr4_er": 4.4,
        },
        "selected_coil_groups": [
            {
                "kind": "tx_dd",
                "requested_count": 2,
                "selected_count": 2,
                "spacing_mm": 40.0,
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
                "spacing_mm": 40.0,
                "instance_transforms": [{"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0}],
            },
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
            "spec_version": "0.1.4",
            "design_name": "square_test",
            "units": "mm",
        },
        "created_at_utc": "2026-02-20T00:00:00Z",
        "manifest_path": str(tmp_path / "manifest_abcd1234_eeeeeeee_1.json"),
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
    )

    assert debug["corner_debug"][0]["corner_type"] == "endpoint"
    assert debug["corner_debug"][-1]["corner_type"] == "endpoint"
    right_turn_count = sum(1 for corner in debug["corner_debug"] if corner["corner_type"] == "right_turn")
    assert right_turn_count >= 3

    non_endpoints = [corner for corner in debug["corner_debug"] if corner["corner_type"] != "endpoint"]
    assert all(corner["offset_applied"] is not None for corner in non_endpoints)


def test_build_square_spiral_writes_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)

    metadata = geom.build_square_spiral_from_manifest(_manifest(tmp_path))

    assert metadata["design_id"] == "abcd1234_eeeeeeee_1"
    assert metadata["design_unique_hash"] == "abcd1234"
    assert metadata["toml_space_hash"] == "eeeeeeee"
    assert Path(metadata["metadata_path"]).exists()
    assert metadata["aedt_path"].endswith("abcd1234_eeeeeeee_1.aedt")
    assert fake.release_args == (True, True)

    assert metadata["anchor_mode"] == "copper_outer_edge_corner"
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
    assert len(metadata["debug"]["cad_probe"]) == 5

    assert len(fake.modeler.polyline_calls) == 3
    for call in fake.modeler.polyline_calls:
        assert call["xsection_height"] == 0.035


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

from __future__ import annotations

from pathlib import Path

import pytest

import peetsfea.backend.pyaedt.geometry.square_spiral as geom
from peetsfea.types.manifest import Manifest


class _FakeObject:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeModeler:
    def __init__(self) -> None:
        self.calls = []

    def create_polyline(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return _FakeObject(kwargs.get("name", "coil1"))


class _FakeHfss:
    def __init__(self) -> None:
        self.modeler = _FakeModeler()
        self.saved = None
        self.release_args = None

    def save_project(self, *args, **kwargs) -> None:
        self.saved = (args, kwargs)

    def release_desktop(self, close_projects: bool = True, close_desktop: bool = True) -> None:
        self.release_args = (close_projects, close_desktop)
        return None


def _manifest(tmp_path: Path) -> Manifest:
    return {
        "design_id": "abcd1234",
        "toml_hash": "t" * 64,
        "peetsfea_commit": "c" * 40,
        "seed": 1,
        "selected_parameters": {
            "turns": 5,
            "outer": 48.0,
            "trace": 1.0,
            "gap": 0.5,
            "thickness": 0.05,
        },
        "inputs": {
            "ansys_executable_path": "/opt/ansys_inc/v252/AnsysEM",
            "ansys_run_dir": str(tmp_path),
            "toml_path": str(tmp_path / "type1.toml"),
            "non_graphical": True,
            "close_on_exit": True,
        },
        "spec": {
            "spec_version": "0.1.0",
            "design_name": "square_test",
            "units": "mm",
        },
    }


def test_square_spiral_points_shape() -> None:
    pts = geom._square_spiral_points(turns=2, outer=40.0, trace=1.0, gap=0.5)
    assert len(pts) >= 8
    assert pts[0][2] == 0.0


def test_build_square_spiral_writes_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeHfss()
    monkeypatch.setattr(geom, "_create_hfss_session", lambda manifest, aedt_path: fake)

    metadata = geom.build_square_spiral_from_manifest(_manifest(tmp_path))

    assert metadata["design_id"] == "abcd1234"
    assert "metadata_path" in metadata
    assert Path(metadata["metadata_path"]).exists()
    assert metadata["aedt_path"].endswith("abcd1234.aedt")
    assert fake.release_args == (True, True)


def test_build_square_spiral_invalid_params(tmp_path: Path) -> None:
    bad = _manifest(tmp_path)
    bad["selected_parameters"]["thickness"] = 0.0

    with pytest.raises(ValueError, match="thickness"):
        geom.build_square_spiral_from_manifest(bad)

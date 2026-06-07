from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from entry.debug_view_0_3_0_ssw import (
    AEDT_IMPORTED_LEDGER_NAME,
    AEDT_PORT_LEDGER_NAME,
    SOURCE_TOML_PATH,
    export_ssw_aedt_port_artifacts,
)
from peetsfea.aedt.protocols import HfssSession
from peetsfea.backend.pyaedt.ssw_ports import (
    SswAedtBodyLedgerEntry,
    SswAedtPortStepLedger,
    setup_ssw_aedt_ports,
    setup_ssw_aedt_ports_into_hfss,
    write_ssw_aedt_port_ledger,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = REPO_ROOT / "run"


class _FakeBoundaryModule:
    def __init__(self, parent: "_FakeHfss") -> None:
        self._parent = parent
        self.assign_lumped_port_calls: list[list[object]] = []
        self.assign_result: object = True

    def AssignLumpedPort(self, props: list[object]) -> object:
        self.assign_lumped_port_calls.append(list(props))
        if self.assign_result is False:
            return False
        raw_name = props[0]
        assert isinstance(raw_name, str)
        boundary_name = raw_name.removeprefix("NAME:")
        self._parent.excitation_names.append(f"{boundary_name}_T1")
        return True

    def GetBoundaries(self) -> list[str]:
        return []


class _FakeDesktop:
    def __init__(self) -> None:
        self.release_calls: list[tuple[bool, bool]] = []

    def release_desktop(self, close_projects: bool, close_on_exit: bool) -> object:
        self.release_calls.append((close_projects, close_on_exit))
        return True


class _FakeMaterials:
    def __init__(self) -> None:
        self.exists_material_calls: list[str] = []

    def exists_material(self, name: str) -> object:
        self.exists_material_calls.append(name)
        return name == "copper"


class _FakeModelObject:
    def __init__(self, name: str) -> None:
        self.name = name
        self.material_name = ""
        self.color: tuple[int, int, int] = (0, 0, 0)
        self.transparency = 0.0


class _FakeModeler:
    def __init__(self, ledger: SswAedtPortStepLedger) -> None:
        self._ledger = ledger
        self._object_names: list[str] = []
        self._objects: dict[str, _FakeModelObject] = {}
        self.import_calls: list[Path] = []
        self.import_kwargs: list[dict[str, object]] = []
        self.set_model_state_calls: list[tuple[str, bool]] = []
        self._object_edges: dict[str, list[int]] = {}
        self._edge_vertices: dict[int, tuple[int, int]] = {}
        self._vertex_positions: dict[int, tuple[float, float, float]] = {}
        self._next_edge_id = 1
        self._next_vertex_id = 1

    @property
    def object_names(self) -> list[str]:
        return list(self._object_names)

    def import_3d_cad(self, input_file: Path, **kwargs: object) -> object:
        self.import_calls.append(input_file)
        self.import_kwargs.append(dict(kwargs))
        self._object_names.extend(self._ledger["body_names"])
        for object_name in self._ledger["body_names"]:
            self._objects[object_name] = _FakeModelObject(object_name)
        for cell in self._ledger["port_cells"]:
            self._seed_sheet_edges(cell["port_sheet_name"], cell["port_sheet_vertices_xyz"])
        return True

    def get_object_from_name(self, assignment: str) -> object:
        if assignment not in self._objects:
            return False
        return self._objects[assignment]

    def _seed_sheet_edges(self, sheet_name: str, vertices: list[list[float]]) -> None:
        vertex_ids: list[int] = []
        for raw_vertex in vertices:
            vertex_id = self._next_vertex_id
            self._next_vertex_id += 1
            self._vertex_positions[vertex_id] = (float(raw_vertex[0]), float(raw_vertex[1]), float(raw_vertex[2]))
            vertex_ids.append(vertex_id)
        edge_ids: list[int] = []
        for first_id, second_id in zip(vertex_ids, [*vertex_ids[1:], vertex_ids[0]], strict=True):
            edge_id = self._next_edge_id
            self._next_edge_id += 1
            self._edge_vertices[edge_id] = (first_id, second_id)
            edge_ids.append(edge_id)
        self._object_edges[sheet_name] = edge_ids

    def set_object_model_state(self, name: str, model: bool) -> object:
        self.set_model_state_calls.append((name, model))
        return True

    def get_object_edges(self, assignment: str) -> list[int]:
        if assignment not in self._object_edges:
            return []
        return list(self._object_edges[assignment])

    def get_edge_vertices(self, assignment: int) -> list[int]:
        first_id, second_id = self._edge_vertices[assignment]
        return [first_id, second_id]

    def get_vertex_position(self, assignment: int) -> list[float]:
        x, y, z = self._vertex_positions[assignment]
        return [x, y, z]


class _FakeHfss:
    def __init__(self, ledger: SswAedtPortStepLedger) -> None:
        self.modeler = _FakeModeler(ledger)
        self.desktop_class = _FakeDesktop()
        self.materials = _FakeMaterials()
        self.oboundary = _FakeBoundaryModule(self)
        self.excitation_names: list[str] = []
        self.saved_paths: list[str] = []

    def save_project(self, path: str) -> object:
        self.saved_paths.append(path)
        return True


def _body_entry(object_id: str, role: str, material: str, model_state: bool) -> SswAedtBodyLedgerEntry:
    return {
        "object_id": object_id,
        "role": role,
        "material": material,
        "model_state": model_state,
        "canonical_coordinates": {
            "outer_bounds_min_xyz": [0.0, 0.0, 0.0],
            "outer_bounds_max_xyz": [1.0, 1.0, 1.0],
            "outer_bounds_size_xyz": [1.0, 1.0, 1.0],
        },
    }


def _ledger(tmp_path: Path) -> SswAedtPortStepLedger:
    tx_vertices = [[-1.0, -0.5, 0.0], [1.0, -0.5, 0.0], [1.0, 0.5, 0.0], [-1.0, 0.5, 0.0]]
    rx_vertices = [[10.0, -1.0, -0.5], [10.0, 1.0, -0.5], [10.0, 1.0, 0.5], [10.0, -1.0, 0.5]]
    body_names = [
        "tv",
        "tx_ssw_coil_ssw_copper",
        "rx_ssw_coil_coil_copper",
        "tx_mull_ferrite_sheet",
        "tx_aedt_port_sheet",
        "rx_aedt_port_sheet",
    ]
    return {
        "source_step_ledger_path": str(tmp_path / "ssw_step_ledger.json"),
        "scene_step_path": str(tmp_path / "ssw_scene_with_ports.step"),
        "seed": 0,
        "units": "mm",
        "body_names": body_names,
        "copper_body_names": ["tx_ssw_coil_ssw_copper", "rx_ssw_coil_coil_copper"],
        "port_sheet_names": ["tx_aedt_port_sheet", "rx_aedt_port_sheet"],
        "non_model_body_names": ["tv", "tx_mull_ferrite_sheet"],
        "bodies": [
            _body_entry("tv", "non_model", "vacuum", False),
            _body_entry("tx_ssw_coil_ssw_copper", "copper", "copper", True),
            _body_entry("rx_ssw_coil_coil_copper", "copper", "copper", True),
            _body_entry("tx_mull_ferrite_sheet", "ferrite", "mull_ferrite", False),
            _body_entry("tx_aedt_port_sheet", "tx_port_sheet", "vacuum", True),
            _body_entry("rx_aedt_port_sheet", "rx_port_sheet", "vacuum", True),
        ],
        "port_cells": [
            {
                "role": "tx",
                "port_sheet_name": "tx_aedt_port_sheet",
                "port_sheet_vertices_xyz": tx_vertices,
                "signal_edge_vertices_xyz": [tx_vertices[0], tx_vertices[1]],
                "reference_edge_vertices_xyz": [tx_vertices[3], tx_vertices[2]],
            },
            {
                "role": "rx",
                "port_sheet_name": "rx_aedt_port_sheet",
                "port_sheet_vertices_xyz": rx_vertices,
                "signal_edge_vertices_xyz": [rx_vertices[0], rx_vertices[1]],
                "reference_edge_vertices_xyz": [rx_vertices[3], rx_vertices[2]],
            },
        ],
    }


def _ledger_path(tmp_path: Path) -> Path:
    ledger = _ledger(tmp_path)
    ledger_path = tmp_path / "ssw_aedt_port_ledger.json"
    write_ssw_aedt_port_ledger(ledger_path=ledger_path, ledger=ledger)
    Path(ledger["scene_step_path"]).write_text("placeholder", encoding="utf-8")
    return ledger_path


def test_setup_ssw_aedt_ports_into_hfss_creates_tx_rx_terminal_ports(tmp_path: Path) -> None:
    ledger_path = _ledger_path(tmp_path)
    ledger = _ledger(tmp_path)
    hfss = _FakeHfss(ledger)

    result = setup_ssw_aedt_ports_into_hfss(
        hfss=cast(HfssSession, hfss),
        port_ledger_path=ledger_path,
        output_aedt_path=tmp_path / "ssw_ports.aedt",
        imported_ledger_path=tmp_path / "ssw_imported.json",
    )

    assert hfss.modeler.import_calls == [Path(ledger["scene_step_path"])]
    assert hfss.modeler.import_kwargs == [{"create_group": False, "import_free_surfaces": True, "import_materials": False}]
    assert hfss.modeler.set_model_state_calls == [("tv", False), ("tx_mull_ferrite_sheet", False)]
    assert hfss.materials.exists_material_calls == ["copper", "copper"]
    assert [call[0] for call in hfss.oboundary.assign_lumped_port_calls] == ["NAME:1", "NAME:2"]
    assert result["ports"] == {"tx": ["1_T1"], "rx": ["2_T1"]}
    assert hfss.saved_paths == [str(tmp_path / "ssw_ports.aedt")]
    imported = json.loads((tmp_path / "ssw_imported.json").read_text(encoding="utf-8"))
    assert imported["source_port_ledger_path"] == str(ledger_path)
    assert imported["copper_body_names"] == ledger["copper_body_names"]
    assert imported["port_sheet_names"] == ledger["port_sheet_names"]
    assert imported["visual_assignments"]["tx_aedt_port_sheet"] == {"color": [180, 215, 255], "transparency": 0.88}


def test_setup_ssw_aedt_ports_into_hfss_raises_on_port_assignment_false(tmp_path: Path) -> None:
    ledger_path = _ledger_path(tmp_path)
    hfss = _FakeHfss(_ledger(tmp_path))
    hfss.oboundary.assign_result = False

    with pytest.raises(RuntimeError, match="AssignLumpedPort"):
        setup_ssw_aedt_ports_into_hfss(
            hfss=cast(HfssSession, hfss),
            port_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "ssw_ports.aedt",
            imported_ledger_path=tmp_path / "ssw_imported.json",
        )


def test_setup_ssw_aedt_ports_can_leave_graphical_desktop_open(tmp_path: Path) -> None:
    ledger_path = _ledger_path(tmp_path)
    hfss = _FakeHfss(_ledger(tmp_path))

    def _factory(design_name: str) -> HfssSession:
        assert design_name == "ssw_gui_test"
        return cast(HfssSession, hfss)

    setup_ssw_aedt_ports(
        port_ledger_path=ledger_path,
        output_aedt_path=tmp_path / "ssw_ports.aedt",
        imported_ledger_path=tmp_path / "ssw_imported.json",
        design_name="ssw_gui_test",
        hfss_factory=_factory,
        release_desktop_on_exit=False,
    )

    assert hfss.desktop_class.release_calls == []


@pytest.mark.pyaedt_integration
def test_setup_ssw_aedt_ports_runs_real_headless_ansys() -> None:
    output_dir = RUN_DIR / "ssw_headless_ansys_test"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    export_ssw_aedt_port_artifacts(source_toml_path=SOURCE_TOML_PATH, output_dir=output_dir, seed=0)

    result = setup_ssw_aedt_ports(
        port_ledger_path=output_dir / AEDT_PORT_LEDGER_NAME,
        output_aedt_path=output_dir / "ssw_headless_ports.aedt",
        imported_ledger_path=output_dir / AEDT_IMPORTED_LEDGER_NAME,
        design_name="ssw_headless_ports_test",
    )

    assert result["ports"] == {"tx": ["1_T1"], "rx": ["2_T1"]}
    assert Path(result["aedt_path"]).is_file()
    assert Path(result["imported_ledger_path"]).is_file()
    imported = json.loads(Path(result["imported_ledger_path"]).read_text(encoding="utf-8"))
    assert imported["port_sheet_names"] == ["tx_aedt_port_sheet", "rx_aedt_port_sheet"]
    assert "tx_ssw_coil_ssw_copper" in imported["copper_body_names"]
    assert "rx_ssw_coil_coil_copper" in imported["copper_body_names"]

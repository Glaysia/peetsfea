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
        self._seed_copper_port_edges()
        return True

    def get_object_from_name(self, assignment: str) -> object:
        if assignment not in self._objects:
            return False
        return self._objects[assignment]

    def _seed_edge(
        self,
        *,
        object_name: str,
        edge_id: int,
        first_xyz: tuple[float, float, float],
        second_xyz: tuple[float, float, float],
    ) -> None:
        first_vertex_id = self._next_vertex_id
        self._next_vertex_id += 1
        second_vertex_id = self._next_vertex_id
        self._next_vertex_id += 1
        self._vertex_positions[first_vertex_id] = first_xyz
        self._vertex_positions[second_vertex_id] = second_xyz
        self._edge_vertices[edge_id] = (first_vertex_id, second_vertex_id)
        if object_name not in self._object_edges:
            self._object_edges[object_name] = []
        self._object_edges[object_name].append(edge_id)

    def _seed_copper_port_edges(self) -> None:
        self._seed_edge(
            object_name="tx_ssw_coil_ssw_copper",
            edge_id=101,
            first_xyz=(0.0, -1.0, 0.0),
            second_xyz=(10.0, -1.0, 0.0),
        )
        self._seed_edge(
            object_name="tx_ssw_coil_ssw_copper",
            edge_id=102,
            first_xyz=(0.0, 1.0, 0.0),
            second_xyz=(10.0, 1.0, 0.0),
        )
        self._seed_edge(
            object_name="tx_ssw_coil_ssw_copper",
            edge_id=103,
            first_xyz=(0.0, 20.0, 0.0),
            second_xyz=(10.0, 20.0, 0.0),
        )
        self._seed_edge(
            object_name="rx_ssw_coil_coil_copper",
            edge_id=201,
            first_xyz=(9.0, 5.0, 0.0),
            second_xyz=(9.0, 5.0, 5.5),
        )
        self._seed_edge(
            object_name="rx_ssw_coil_coil_copper",
            edge_id=202,
            first_xyz=(9.0, 7.0, 0.0),
            second_xyz=(9.0, 7.0, 5.5),
        )
        self._seed_edge(
            object_name="rx_ssw_coil_coil_copper",
            edge_id=203,
            first_xyz=(10.0, 5.0, 0.0),
            second_xyz=(10.0, 5.0, 5.5),
        )
        self._seed_edge(
            object_name="rx_ssw_coil_coil_copper",
            edge_id=204,
            first_xyz=(10.0, 7.0, 0.0),
            second_xyz=(10.0, 7.0, 5.5),
        )

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
    body_names = [
        "tv",
        "tx_ssw_coil_ssw_copper",
        "rx_ssw_coil_coil_copper",
        "tx_mull_ferrite_sheet",
    ]
    return {
        "source_step_ledger_path": str(tmp_path / "ssw_step_ledger.json"),
        "scene_step_path": str(tmp_path / "ssw_scene.step"),
        "seed": 0,
        "units": "mm",
        "body_names": body_names,
        "copper_body_names": ["tx_ssw_coil_ssw_copper", "rx_ssw_coil_coil_copper"],
        "non_model_body_names": ["tv", "tx_mull_ferrite_sheet"],
        "bodies": [
            _body_entry("tv", "non_model", "vacuum", False),
            _body_entry("tx_ssw_coil_ssw_copper", "copper", "copper", True),
            _body_entry("rx_ssw_coil_coil_copper", "copper", "copper", True),
            _body_entry("tx_mull_ferrite_sheet", "ferrite", "mull_ferrite", False),
        ],
        "port_edges": [
            {
                "role": "tx",
                "copper_body_name": "tx_ssw_coil_ssw_copper",
                "selection": "nearest_long_face_edges",
                "face_axis": "z",
                "face_side": "min",
                "anchor_xyz": [5.0, 0.0, 0.0],
                "minimum_edge_length_mm": 5.5,
            },
            {
                "role": "rx",
                "copper_body_name": "rx_ssw_coil_coil_copper",
                "selection": "axis_spaced_face_edges",
                "face_axis": "x",
                "face_side": "min",
                "edge_axis": "z",
                "spacing_axis": "y",
                "edge_length_mm": 5.5,
                "pair_spacing_mm": 2.0,
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
    assert hfss.modeler.import_kwargs == [{"create_group": False, "import_free_surfaces": False, "import_materials": False}]
    assert hfss.modeler.set_model_state_calls == [("tv", False), ("tx_mull_ferrite_sheet", False)]
    assert hfss.materials.exists_material_calls == ["copper", "copper"]
    assert hfss.oboundary.assign_lumped_port_calls == [
        [
            "NAME:1",
            "Edges:=",
            [101, 102],
            "LumpedPortType:=",
            "Terminal",
            "DoDeembed:=",
            False,
            "RenormalizeAllTerminals:=",
            True,
            "ShowReporterFilter:=",
            False,
            "Impedance:=",
            "50ohm",
        ],
        [
            "NAME:2",
            "Edges:=",
            [201, 202],
            "LumpedPortType:=",
            "Terminal",
            "DoDeembed:=",
            False,
            "RenormalizeAllTerminals:=",
            True,
            "ShowReporterFilter:=",
            False,
            "Impedance:=",
            "50ohm",
        ],
    ]
    assert result["ports"] == {"tx": ["1_T1"], "rx": ["2_T1"]}
    assert hfss.saved_paths == [str(tmp_path / "ssw_ports.aedt")]
    imported = json.loads((tmp_path / "ssw_imported.json").read_text(encoding="utf-8"))
    assert imported["source_port_ledger_path"] == str(ledger_path)
    assert imported["copper_body_names"] == ledger["copper_body_names"]
    assert "port_sheet_names" not in imported
    assert "tx_aedt_port_sheet" not in imported["visual_assignments"]


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
    assert "port_sheet_names" not in imported
    assert "tx_ssw_coil_ssw_copper" in imported["copper_body_names"]
    assert "rx_ssw_coil_coil_copper" in imported["copper_body_names"]

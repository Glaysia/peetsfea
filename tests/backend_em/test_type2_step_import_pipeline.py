from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from peetsfea.aedt.protocols import HfssSession
from peetsfea.backend.pyaedt.type2_step_import_pipeline import import_type2_step_ledger
from peetsfea.backend.pyaedt.type2_step_import_pipeline import import_type2_step_ledger_into_hfss


def _write_step(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")
    return path


def _non_model_member_entry(
    *,
    object_id: str,
    role: str,
    origin_xyz: tuple[float, float, float],
    size_xyz: tuple[float, float, float],
    plane: str,
) -> dict[str, object]:
    origin_x, origin_y, origin_z = origin_xyz
    size_x, size_y, size_z = size_xyz
    return {
        "object_id": object_id,
        "role": role,
        "material": "vacuum",
        "model_state": False,
        "canonical_coordinates": {
            "frame_origin_xyz": list(origin_xyz),
            "outer_bounds_min_xyz": list(origin_xyz),
            "outer_bounds_max_xyz": [origin_x + size_x, origin_y + size_y, origin_z + size_z],
            "outer_bounds_size_xyz": list(size_xyz),
        },
        "plane": plane,
        "non_model": True,
    }


def _non_model_entry(*, object_id: str = "type2_non_model_scene") -> dict[str, object]:
    return {
        "object_id": object_id,
        "role": "non_model_scene",
        "material": "vacuum",
        "model_state": False,
        "canonical_coordinates": {
            "frame_origin_xyz": [0.0, -1000.0, -461.0],
            "outer_bounds_min_xyz": [0.0, -1000.0, -461.0],
            "outer_bounds_max_xyz": [2000.0, 1000.0, 1194.0],
            "outer_bounds_size_xyz": [2000.0, 2000.0, 1655.0],
        },
        "plane": "mixed",
        "non_model": True,
        "member_object_ids": ("environment", "tx_region", "rx_region_max"),
        "member_objects": [
            _non_model_member_entry(
                object_id="environment",
                role="environment",
                origin_xyz=(0.0, -1000.0, -461.0),
                size_xyz=(2000.0, 2000.0, 1655.0),
                plane="mixed",
            ),
            _non_model_member_entry(
                object_id="tx_region",
                role="tx_region",
                origin_xyz=(0.0, -140.0, 0.0),
                size_xyz=(160.0, 280.0, 90.0),
                plane="XY",
            ),
            _non_model_member_entry(
                object_id="rx_region_max",
                role="rx_region_max",
                origin_xyz=(0.0, -280.0, 139.0),
                size_xyz=(4.0, 560.0, 360.0),
                plane="YZ",
            ),
        ],
    }


def _modeled_entry(
    *,
    object_id: str = "tx_rect_void_coil",
    role: str = "tx_single_coil",
    plane: str = "XY",
    placement_owner_id: str = "tx_region",
    origin_xyz: tuple[float, float, float] = (55.0, -15.0, 87.2),
    size_xyz: tuple[float, float, float] = (50.0, 30.0, 2.8),
    source_metadata_path: str = "/tmp/type2.metadata.json",
    expected_names: list[str] | None = None,
    pcb_layer_positions_mm: list[float] | None = None,
    copper_layer_positions_mm: list[float] | None = None,
) -> dict[str, object]:
    origin_x, origin_y, origin_z = origin_xyz
    size_x, size_y, size_z = size_xyz
    offset_x = origin_x - (-25.0)
    offset_y = origin_y - (-15.0)
    if expected_names is None:
        expected_names = ["tx_pcb_l0", "tx_copper_l0"] if role == "tx_single_coil" else ["rx_pcb_l0", "rx_copper_l0"]
    if pcb_layer_positions_mm is None:
        pcb_layer_positions_mm = [origin_z]
    if copper_layer_positions_mm is None:
        copper_layer_positions_mm = [origin_z + 1.6]
    return {
        "object_id": object_id,
        "role": role,
        "plane": plane,
        "placement_owner_id": placement_owner_id,
        "material": "composite",
        "model_state": True,
        "expected_exported_body_names": expected_names,
        "expected_exported_body_count": len(expected_names),
        "canonical_coordinates": {
            "frame_origin_xyz": [offset_x, offset_y, origin_z],
            "outer_bounds_min_xyz": [origin_x, origin_y, origin_z],
            "outer_bounds_max_xyz": [origin_x + size_x, origin_y + size_y, origin_z + size_z],
            "outer_bounds_size_xyz": [size_x, size_y, size_z],
            "pcb_layer_z_positions_mm": pcb_layer_positions_mm,
            "copper_layer_z_positions_mm": copper_layer_positions_mm,
        },
        "terminal_metadata": {
            "path": "A_cw_to_a",
            "outer_corner": "A",
            "inner_corner": "a",
            "direction": "cw",
            "start_point_plane_mm": [55.0, 15.0],
            "end_point_plane_mm": [70.0, 5.0],
        },
        "source_metadata_path": source_metadata_path,
    }


def _write_ledger(
    path: Path,
    *,
    scene_step_path: Path,
    non_model_objects: list[dict[str, object]],
    modeled_objects: list[dict[str, object]],
) -> Path:
    payload = {
        "source_toml_path": str(path.parent / "type2_fixed.toml"),
        "output_dir": str(path.parent),
        "scene_step_path": str(scene_step_path),
        "seed": 7,
        "non_model_objects": non_model_objects,
        "modeled_objects": modeled_objects,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class _FakeObject:
    def __init__(self, name: str) -> None:
        self.name = name
        self.color = (0, 0, 0)
        self.transparency = 0.0
        self.material_name = "vacuum"


class _FakeModeler:
    def __init__(
        self,
        *,
        imported_name_batches: list[tuple[str, ...]],
        import_result: object = True,
    ) -> None:
        self._object_names: tuple[str, ...] = ("existing",)
        self._imported_name_batches = list(imported_name_batches)
        self._import_result = import_result
        self.import_calls: list[Path] = []
        self.model_state_calls: list[tuple[str, bool]] = []
        self.move_calls: list[tuple[list[str], list[float]]] = []
        self.objects: dict[str, _FakeObject] = {"existing": _FakeObject("existing")}

    @property
    def object_names(self) -> tuple[str, ...]:
        return self._object_names

    def import_3d_cad(self, input_file: str | Path, **_: object) -> object:
        self.import_calls.append(Path(input_file))
        if self._import_result is not True:
            return self._import_result
        if not self._imported_name_batches:
            raise AssertionError("fake import batch queue exhausted")
        next_names = self._imported_name_batches.pop(0)
        self._object_names = self._object_names + next_names
        for name in next_names:
            self.objects[name] = _FakeObject(name)
        return True

    def set_object_model_state(self, name: str, model: bool) -> object:
        self.model_state_calls.append((name, model))
        return True

    def get_object_from_name(self, assignment: str) -> object:
        return self.objects[assignment]

    def move(self, assignment: object, vector: list[float]) -> object:
        assert isinstance(assignment, list)
        self.move_calls.append((list(assignment), list(vector)))
        return True


class _FakeDesktop:
    def __init__(self) -> None:
        self.release_calls: list[tuple[bool, bool]] = []

    def release_desktop(self, close_projects: bool, close_on_exit: bool) -> object:
        self.release_calls.append((close_projects, close_on_exit))
        return True


class _FakeHfss:
    def __init__(self, *, modeler: _FakeModeler, save_project_result: object = True) -> None:
        self.modeler = modeler
        self.desktop_class = _FakeDesktop()
        self._save_project_result = save_project_result
        self.save_project_calls: list[str] = []

    def save_project(self, path: str) -> object:
        self.save_project_calls.append(path)
        return self._save_project_result


def _source_paths(tmp_path: Path) -> tuple[Path, Path]:
    scene_step = _write_step(tmp_path / "type2_scene.step")
    ledger_path = tmp_path / "type2_step_ledger.json"
    return (scene_step, ledger_path)


def test_import_type2_step_ledger_imports_single_scene_and_writes_partitioned_ledger(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[
            _modeled_entry(source_metadata_path=str(tmp_path / "tx.metadata.json")),
            _modeled_entry(
                object_id="rx_rect_void_coil",
                role="rx_single_coil",
                plane="YZ",
                placement_owner_id="rx_region_max",
                origin_xyz=(1.2, -25.0, 139.0),
                size_xyz=(2.8, 50.0, 30.0),
                source_metadata_path=str(tmp_path / "rx.metadata.json"),
            ),
        ],
    )
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[
                (
                    "environment",
                    "tx_region",
                    "rx_region_max",
                    "tx_pcb_l0",
                    "tx_copper_l0",
                    "rx_pcb_l0",
                    "rx_copper_l0",
                ),
            ]
        )
    )

    result = import_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        design_name="fake_type2_import",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    assert session.modeler.import_calls == [scene_step]
    assert session.modeler.model_state_calls == [
        ("environment", False),
        ("tx_region", False),
        ("rx_region_max", False),
        ("tx_pcb_l0", True),
        ("tx_copper_l0", True),
        ("rx_pcb_l0", True),
        ("rx_copper_l0", True),
    ]
    assert session.modeler.move_calls == []
    assert session.modeler.objects["environment"].color == (128, 128, 128)
    assert session.modeler.objects["environment"].transparency == pytest.approx(0.85)
    assert session.modeler.objects["tx_pcb_l0"].material_name == "FR4_epoxy"
    assert session.modeler.objects["tx_pcb_l0"].color == (0, 128, 0)
    assert session.modeler.objects["tx_pcb_l0"].transparency == pytest.approx(0.85)
    assert session.modeler.objects["tx_copper_l0"].material_name == "copper"
    assert session.modeler.objects["tx_copper_l0"].color == (184, 115, 51)
    assert session.modeler.objects["tx_copper_l0"].transparency == pytest.approx(0.0)
    assert session.modeler.objects["rx_pcb_l0"].material_name == "FR4_epoxy"
    assert session.modeler.objects["rx_copper_l0"].material_name == "copper"
    assert session.save_project_calls == [str(output_aedt_path)]
    assert session.desktop_class.release_calls == [(True, True)]
    assert result["scene_step_path"] == str(scene_step)
    assert result["non_model_objects"][0]["imported_object_names"] == ["environment", "tx_region", "rx_region_max"]
    modeled_by_id = {entry["object_id"]: entry for entry in result["modeled_objects"]}
    assert modeled_by_id["tx_rect_void_coil"]["imported_object_names"] == ["tx_pcb_l0", "tx_copper_l0"]
    assert modeled_by_id["rx_rect_void_coil"]["imported_object_names"] == ["rx_pcb_l0", "rx_copper_l0"]

    written = json.loads(imported_ledger_path.read_text(encoding="utf-8"))
    assert written == result


def test_import_type2_step_ledger_styles_multilayer_tx_parallel_stack(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[
            _modeled_entry(
                expected_names=["tx_pcb_l0", "tx_pcb_l1", "tx_copper_stack"],
                pcb_layer_positions_mm=[87.2, 91.3],
                copper_layer_positions_mm=[88.8, 92.9],
            ),
        ],
    )
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[
                ("environment", "tx_region", "rx_region_max", "tx_pcb_l0", "tx_pcb_l1", "tx_copper_stack"),
            ]
        )
    )

    result = import_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
        imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
        design_name="fake_type2_import",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    assert session.modeler.model_state_calls == [
        ("environment", False),
        ("tx_region", False),
        ("rx_region_max", False),
        ("tx_pcb_l0", True),
        ("tx_pcb_l1", True),
        ("tx_copper_stack", True),
    ]
    assert session.modeler.objects["tx_pcb_l0"].material_name == "FR4_epoxy"
    assert session.modeler.objects["tx_pcb_l1"].material_name == "FR4_epoxy"
    assert session.modeler.objects["tx_copper_stack"].material_name == "copper"
    assert session.modeler.objects["tx_pcb_l0"].color == (0, 128, 0)
    assert session.modeler.objects["tx_pcb_l1"].color == (0, 128, 0)
    assert session.modeler.objects["tx_copper_stack"].color == (184, 115, 51)
    modeled_entry = result["modeled_objects"][0]
    assert modeled_entry["imported_object_names"] == ["tx_pcb_l0", "tx_pcb_l1", "tx_copper_stack"]


def test_import_type2_step_ledger_fails_when_modeled_labels_are_not_preserved(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[("environment", "tx_region", "rx_region_max", "SOLID_7", "tx_copper_l0")]
        )
    )

    with pytest.raises(ValueError, match=r"missing required modeled body name"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_fails_when_scene_import_contains_unclaimed_object(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[
                ("environment", "tx_region", "rx_region_max", "tx_pcb_l0", "tx_copper_l0", "mystery"),
            ]
        )
    )

    with pytest.raises(ValueError, match=r"unclaimed imported object names"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_fails_when_scene_import_missing_non_model_member_name(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[("environment", "tx_region", "tx_pcb_l0", "tx_copper_l0")]
        )
    )

    with pytest.raises(ValueError, match=r"missing non-model member object names"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_fails_when_modeled_tx_is_not_centered_on_tx_region_y(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry(origin_xyz=(55.0, -16.0, 87.2))],
    )
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[("environment", "tx_region", "rx_region_max", "tx_pcb_l0", "tx_copper_l0")]
        )
    )

    with pytest.raises(ValueError, match=r"center_y must already align with tx_region center_y"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_fails_when_modeled_tx_does_not_fit_tx_region(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry(size_xyz=(170.0, 30.0, 2.8))],
    )
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[("environment", "tx_region", "rx_region_max", "tx_pcb_l0", "tx_copper_l0")]
        )
    )

    with pytest.raises(ValueError, match=r"outer bounds must fit inside tx_region"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_fails_when_modeled_tx_is_not_top_aligned_to_tx_region(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry(origin_xyz=(55.0, -15.0, 87.1))],
    )
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[("environment", "tx_region", "rx_region_max", "tx_pcb_l0", "tx_copper_l0")]
        )
    )

    with pytest.raises(ValueError, match=r"outer bounds max_z must already touch tx_region max_z"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_into_hfss_auto_detaches_after_import(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[("environment", "tx_region", "rx_region_max", "tx_pcb_l0", "tx_copper_l0")]
        )
    )

    result = import_type2_step_ledger_into_hfss(
        hfss=cast(HfssSession, session),
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
    )

    assert result["aedt_path"] == str(output_aedt_path)
    assert session.save_project_calls == [str(output_aedt_path)]
    assert session.modeler.import_calls == [scene_step]
    assert session.modeler.model_state_calls == [
        ("environment", False),
        ("tx_region", False),
        ("rx_region_max", False),
        ("tx_pcb_l0", True),
        ("tx_copper_l0", True),
    ]
    assert session.modeler.objects["environment"].color == (128, 128, 128)
    assert session.modeler.objects["environment"].transparency == pytest.approx(0.85)
    assert session.modeler.objects["tx_pcb_l0"].material_name == "FR4_epoxy"
    assert session.modeler.objects["tx_pcb_l0"].color == (0, 128, 0)
    assert session.modeler.objects["tx_pcb_l0"].transparency == pytest.approx(0.85)
    assert session.modeler.objects["tx_copper_l0"].material_name == "copper"
    assert session.modeler.objects["tx_copper_l0"].color == (184, 115, 51)
    assert session.modeler.objects["tx_copper_l0"].transparency == pytest.approx(0.0)
    assert session.desktop_class.release_calls == [(False, False)]


def test_import_type2_step_ledger_into_hfss_releases_desktop_when_import_returns_false(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[], import_result=False))

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: import_3d_cad"):
        import_type2_step_ledger_into_hfss(
            hfss=cast(HfssSession, session),
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
        )

    assert session.desktop_class.release_calls == [(False, False)]


def test_import_type2_step_ledger_into_hfss_releases_desktop_when_save_project_returns_false(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[("environment", "tx_region", "rx_region_max", "tx_pcb_l0", "tx_copper_l0")]
        ),
        save_project_result=False,
    )

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: save_project"):
        import_type2_step_ledger_into_hfss(
            hfss=cast(HfssSession, session),
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=imported_ledger_path,
        )

    assert session.desktop_class.release_calls == [(False, False)]
    assert not imported_ledger_path.exists()


def test_import_type2_step_ledger_fails_for_missing_scene_step_before_hfss_launch(tmp_path: Path) -> None:
    scene_step = tmp_path / "missing_type2_scene.step"
    ledger_path = tmp_path / "type2_step_ledger.json"
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    launch_count = 0

    def _factory(_: str) -> HfssSession:
        nonlocal launch_count
        launch_count += 1
        return cast(HfssSession, _FakeHfss(modeler=_FakeModeler(imported_name_batches=[])))

    with pytest.raises(FileNotFoundError, match=r"scene_step_path does not exist"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=_factory,
        )

    assert launch_count == 0


def test_import_type2_step_ledger_fails_for_missing_required_field(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    non_model_entry = _non_model_entry()
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[non_model_entry],
        modeled_objects=[_modeled_entry()],
    )
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    del payload["scene_step_path"]
    ledger_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=r"type2_step_ledger is missing required key 'scene_step_path'"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, _FakeHfss(modeler=_FakeModeler(imported_name_batches=[]))),
        )


def test_import_type2_step_ledger_fails_for_duplicate_object_id(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry(object_id="dup")],
        modeled_objects=[_modeled_entry(object_id="dup")],
    )

    with pytest.raises(ValueError, match=r"duplicate type2 object id in STEP ledger: dup"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, _FakeHfss(modeler=_FakeModeler(imported_name_batches=[]))),
        )


def test_import_type2_step_ledger_releases_desktop_when_import_returns_false(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[], import_result=False))

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: import_3d_cad"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, session),
        )

    assert session.desktop_class.release_calls == [(True, True)]


def test_import_type2_step_ledger_raises_when_save_project_returns_false(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[("environment", "tx_region", "rx_region_max", "tx_pcb_l0", "tx_copper_l0")]
        ),
        save_project_result=False,
    )

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: save_project"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=imported_ledger_path,
            hfss_factory=lambda _: cast(HfssSession, session),
        )

    assert session.desktop_class.release_calls == [(True, True)]
    assert not imported_ledger_path.exists()


@pytest.mark.parametrize(
    ("batches", "match"),
    [
        ([()], r"STEP import created no new HFSS objects"),
        ([("dup", "dup")], r"STEP import produced duplicate new HFSS object names"),
    ],
)
def test_import_type2_step_ledger_rejects_bad_import_diff(
    tmp_path: Path,
    batches: list[tuple[str, ...]],
    match: str,
) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=batches))

    with pytest.raises(RuntimeError, match=match):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, session),
        )

    assert session.desktop_class.release_calls == [(True, True)]


def test_import_type2_step_ledger_fails_when_tx_region_member_is_missing(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    non_model_entry = _non_model_entry()
    non_model_entry["member_object_ids"] = ("environment", "rx_region_max")
    non_model_entry["member_objects"] = [
        member
        for member in cast(list[dict[str, object]], non_model_entry["member_objects"])
        if cast(str, member["object_id"]) != "tx_region"
    ]
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[non_model_entry],
        modeled_objects=[_modeled_entry()],
    )
    launch_count = 0

    def _factory(_: str) -> HfssSession:
        nonlocal launch_count
        launch_count += 1
        return cast(HfssSession, _FakeHfss(modeler=_FakeModeler(imported_name_batches=[])))

    with pytest.raises(ValueError, match=r"exactly one tx_region member object"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=_factory,
        )

    assert launch_count == 0

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from peetsfea.backend.pyaedt.type2_step_import_pipeline import import_type2_step_ledger_into_hfss
from peetsfea.aedt.protocols import HfssSession
from peetsfea.backend.pyaedt.type2_step_import_pipeline import import_type2_step_ledger


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


def _non_model_entry(*, object_id: str, step_path: Path) -> dict[str, object]:
    return {
        "object_id": object_id,
        "role": object_id,
        "material": "vacuum",
        "model_state": False,
        "step_path": str(step_path),
        "canonical_coordinates": {
            "frame_origin_xyz": [0.0, 0.0, 0.0],
            "outer_bounds_min_xyz": [0.0, 0.0, 0.0],
            "outer_bounds_max_xyz": [1.0, 1.0, 1.0],
            "outer_bounds_size_xyz": [1.0, 1.0, 1.0],
        },
        "plane": "mixed",
        "non_model": True,
        "member_object_ids": ("floor", "wall", "tx_region"),
        "member_objects": [
            _non_model_member_entry(
                object_id="floor",
                role="floor",
                origin_xyz=(0.0, -1000.0, 0.0),
                size_xyz=(2000.0, 2000.0, 10.0),
                plane="XY",
            ),
            _non_model_member_entry(
                object_id="wall",
                role="wall",
                origin_xyz=(0.0, -921.0, 600.0),
                size_xyz=(9.0, 1842.0, 1055.0),
                plane="YZ",
            ),
            _non_model_member_entry(
                object_id="tx_region",
                role="tx_region",
                origin_xyz=(0.0, -140.0, 461.0),
                size_xyz=(160.0, 280.0, 90.0),
                plane="XY",
            ),
        ],
    }


def _modeled_entry(*, step_path: Path) -> dict[str, object]:
    return {
        "object_id": "tx_rect_void_coil",
        "role": "tx_single_coil",
        "material": "composite",
        "model_state": True,
        "step_path": str(step_path),
        "expected_exported_body_names": ["tx_pcb_l0", "tx_copper_l0"],
        "expected_exported_body_count": 2,
        "canonical_coordinates": {
            "frame_origin_xyz": [0.0, 0.0, 0.0],
            "outer_bounds_min_xyz": [-25.0, -15.0, 0.0],
            "outer_bounds_max_xyz": [25.0, 15.0, 2.8],
            "outer_bounds_size_xyz": [50.0, 30.0, 2.8],
            "pcb_layer_z_positions_mm": [0.0],
            "copper_layer_z_positions_mm": [1.6],
        },
        "terminal_metadata": {
            "path": "A_cw_to_a",
            "outer_corner": "A",
            "inner_corner": "a",
            "direction": "cw",
            "start_point_xy_mm": [-25.0, 15.0],
            "end_point_xy_mm": [-10.0, 5.0],
        },
        "source_metadata_path": str(step_path.with_suffix(".metadata.json")),
    }


def _write_ledger(
    path: Path,
    *,
    non_model_objects: list[dict[str, object]],
    modeled_objects: list[dict[str, object]],
) -> Path:
    payload = {
        "source_toml_path": str(path.parent / "type2.toml"),
        "output_dir": str(path.parent),
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
    def __init__(self, *, imported_name_batches: list[tuple[str, ...]], import_result: object = True) -> None:
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


def _source_paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    floor_step = _write_step(tmp_path / "type2_non_model_scene.step")
    wall_step = _write_step(tmp_path / "objects" / "wall.step")
    coil_step = _write_step(tmp_path / "objects" / "tx_rect_void_coil.step")
    ledger_path = tmp_path / "type2_step_ledger.json"
    return floor_step, wall_step, coil_step, ledger_path


def test_import_type2_step_ledger_imports_non_model_then_modeled_and_writes_ledger(tmp_path: Path) -> None:
    non_model_scene_step, _wall_step, coil_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        non_model_objects=[_non_model_entry(object_id="type2_non_model_scene", step_path=non_model_scene_step)],
        modeled_objects=[_modeled_entry(step_path=coil_step)],
    )
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[
                ("floor_body", "wall_body"),
                ("coil_pcb", "coil_copper"),
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

    assert session.modeler.import_calls == [non_model_scene_step, coil_step]
    assert session.modeler.model_state_calls == [
        ("floor_body", False),
        ("wall_body", False),
        ("coil_pcb", True),
        ("coil_copper", True),
    ]
    assert session.modeler.move_calls == [(["coil_pcb", "coil_copper"], [80.0, 0.0, 461.0])]
    assert session.modeler.objects["floor_body"].color == (128, 128, 128)
    assert session.modeler.objects["floor_body"].transparency == pytest.approx(0.85)
    assert session.modeler.objects["wall_body"].color == (128, 128, 128)
    assert session.modeler.objects["wall_body"].transparency == pytest.approx(0.85)
    assert session.modeler.objects["coil_pcb"].material_name == "FR4_epoxy"
    assert session.modeler.objects["coil_pcb"].color == (0, 128, 0)
    assert session.modeler.objects["coil_pcb"].transparency == pytest.approx(0.85)
    assert session.modeler.objects["coil_copper"].material_name == "copper"
    assert session.modeler.objects["coil_copper"].color == (184, 115, 51)
    assert session.modeler.objects["coil_copper"].transparency == pytest.approx(0.0)
    assert session.save_project_calls == [str(output_aedt_path)]
    assert session.desktop_class.release_calls == [(True, True)]
    assert result["seed"] == 7
    assert result["aedt_path"] == str(output_aedt_path)
    assert result["non_model_objects"][0]["object_id"] == "type2_non_model_scene"
    assert result["non_model_objects"][0]["imported_object_names"] == ["floor_body", "wall_body"]
    assert result["modeled_objects"][0]["object_id"] == "tx_rect_void_coil"
    assert result["modeled_objects"][0]["source_metadata_path"] == str(coil_step.with_suffix(".metadata.json"))
    assert result["modeled_objects"][0]["imported_object_names"] == ["coil_pcb", "coil_copper"]

    written = json.loads(imported_ledger_path.read_text(encoding="utf-8"))
    assert written == result


def test_import_type2_step_ledger_into_hfss_keeps_desktop_attached(tmp_path: Path) -> None:
    floor_step, _wall_step, coil_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        non_model_objects=[_non_model_entry(object_id="type2_non_model_scene", step_path=floor_step)],
        modeled_objects=[_modeled_entry(step_path=coil_step)],
    )
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[
                ("floor_body",),
                ("coil_pcb", "coil_copper"),
            ]
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
    assert session.desktop_class.release_calls == []


def test_import_type2_step_ledger_fails_for_missing_step_before_hfss_launch(tmp_path: Path) -> None:
    floor_step, _wall_step, coil_step, ledger_path = _source_paths(tmp_path)
    missing_step = tmp_path / "objects" / "missing_wall.step"
    _write_ledger(
        ledger_path,
        non_model_objects=[
            _non_model_entry(object_id="type2_non_model_scene", step_path=floor_step),
            _non_model_entry(object_id="type2_non_model_scene_extra", step_path=missing_step),
        ],
        modeled_objects=[_modeled_entry(step_path=coil_step)],
    )
    launch_count = 0

    def _factory(_: str) -> HfssSession:
        nonlocal launch_count
        launch_count += 1
        return cast(HfssSession, _FakeHfss(modeler=_FakeModeler(imported_name_batches=[])))

    with pytest.raises(FileNotFoundError, match=r"non_model_objects\[1\]\.step_path does not exist"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=_factory,
        )

    assert launch_count == 0


def test_import_type2_step_ledger_fails_for_missing_required_field(tmp_path: Path) -> None:
    floor_step, _wall_step, coil_step, ledger_path = _source_paths(tmp_path)
    floor_entry = _non_model_entry(object_id="type2_non_model_scene", step_path=floor_step)
    del floor_entry["step_path"]
    _write_ledger(
        ledger_path,
        non_model_objects=[floor_entry],
        modeled_objects=[_modeled_entry(step_path=coil_step)],
    )

    with pytest.raises(ValueError, match=r"non_model_objects\[0\] is missing required key 'step_path'"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, _FakeHfss(modeler=_FakeModeler(imported_name_batches=[]))),
        )


def test_import_type2_step_ledger_fails_for_duplicate_object_id(tmp_path: Path) -> None:
    floor_step, wall_step, coil_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        non_model_objects=[
            _non_model_entry(object_id="type2_non_model_scene", step_path=floor_step),
            _non_model_entry(object_id="type2_non_model_scene", step_path=wall_step),
        ],
        modeled_objects=[_modeled_entry(step_path=coil_step)],
    )

    with pytest.raises(ValueError, match=r"duplicate type2 object id in STEP ledger: type2_non_model_scene"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, _FakeHfss(modeler=_FakeModeler(imported_name_batches=[]))),
        )


def test_import_type2_step_ledger_releases_desktop_when_import_returns_false(tmp_path: Path) -> None:
    floor_step, _wall_step, coil_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        non_model_objects=[_non_model_entry(object_id="type2_non_model_scene", step_path=floor_step)],
        modeled_objects=[_modeled_entry(step_path=coil_step)],
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
    floor_step, _wall_step, coil_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        non_model_objects=[_non_model_entry(object_id="type2_non_model_scene", step_path=floor_step)],
        modeled_objects=[_modeled_entry(step_path=coil_step)],
    )
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(
        modeler=_FakeModeler(imported_name_batches=[("floor_body",), ("coil_pcb", "coil_copper")]),
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
    floor_step, _wall_step, coil_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        non_model_objects=[_non_model_entry(object_id="type2_non_model_scene", step_path=floor_step)],
        modeled_objects=[_modeled_entry(step_path=coil_step)],
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
    floor_step, _wall_step, coil_step, ledger_path = _source_paths(tmp_path)
    non_model_entry = _non_model_entry(object_id="type2_non_model_scene", step_path=floor_step)
    non_model_entry["member_object_ids"] = ("floor", "wall")
    non_model_entry["member_objects"] = cast(list[dict[str, object]], non_model_entry["member_objects"])[:2]
    _write_ledger(
        ledger_path,
        non_model_objects=[non_model_entry],
        modeled_objects=[_modeled_entry(step_path=coil_step)],
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

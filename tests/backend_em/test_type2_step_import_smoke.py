from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from examples.type2.import_non_model_step_to_hfss import _HfssSession
from examples.type2.import_non_model_step_to_hfss import import_step_to_hfss
from peetsfea.aedt import Modeler3D


class _RawImportModeler:
    def __init__(self, *, import_result: object = True, object_names: object = ("existing",)) -> None:
        self.import_result = import_result
        self.object_names = object_names
        self.import_calls: list[dict[str, object]] = []

    def import_3d_cad(self, **kwargs: object) -> object:
        self.import_calls.append(dict(kwargs))
        return self.import_result


def test_modeler_import_3d_cad_raises_on_false() -> None:
    raw_modeler = _RawImportModeler(import_result=False)
    modeler = Modeler3D(_raw=raw_modeler)

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: import_3d_cad"):
        modeler.import_3d_cad(input_file=Path("demo.step"))

    assert raw_modeler.import_calls
    assert raw_modeler.import_calls[0]["input_file"] == Path("demo.step")
    assert "input_file_unit" not in raw_modeler.import_calls[0]


def test_modeler_object_names_rejects_string_shape() -> None:
    raw_modeler = _RawImportModeler(object_names="not-a-sequence-of-names")
    modeler = Modeler3D(_raw=raw_modeler)

    with pytest.raises(AssertionError, match=r"must not be str/bytes"):
        _ = modeler.object_names


def test_modeler_object_names_rejects_non_string_item() -> None:
    raw_modeler = _RawImportModeler(object_names=("existing", 5))
    modeler = Modeler3D(_raw=raw_modeler)

    with pytest.raises(AssertionError, match=r"items must be str"):
        _ = modeler.object_names


class _FakeSmokeModeler:
    def __init__(self) -> None:
        self._object_names: tuple[str, ...] = ("existing",)
        self.import_calls: list[Path] = []
        self.model_state_calls: list[tuple[str, bool]] = []

    @property
    def object_names(self) -> tuple[str, ...]:
        return self._object_names

    def import_3d_cad(self, input_file: str | Path) -> bool:
        self.import_calls.append(Path(input_file))
        self._object_names = ("existing", "floor", "wall")
        return True

    def set_object_model_state(self, name: str, model: bool) -> bool:
        self.model_state_calls.append((name, model))
        return True


class _FakeDesktop:
    def __init__(self) -> None:
        self.release_calls: list[tuple[bool, bool]] = []

    def release_desktop(self, close_projects: bool, close_on_exit: bool) -> bool:
        self.release_calls.append((close_projects, close_on_exit))
        return True


class _FakeHfss:
    def __init__(self) -> None:
        self.modeler = _FakeSmokeModeler()
        self.desktop_class = _FakeDesktop()
        self.save_project_calls: list[str] = []

    def save_project(self, path: str) -> bool:
        self.save_project_calls.append(path)
        return True


def test_type2_step_import_smoke_uses_fake_hfss_without_launching_aedt(tmp_path: Path) -> None:
    step_path = tmp_path / "source.step"
    step_path.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")
    output_aedt_path = tmp_path / "aedt" / "imported.aedt"
    created_sessions: list[_FakeHfss] = []
    design_names: list[str] = []

    def _fake_hfss_factory(design_name: str) -> _HfssSession:
        design_names.append(design_name)
        session = _FakeHfss()
        created_sessions.append(session)
        return cast(_HfssSession, session)

    result = import_step_to_hfss(
        step_path=step_path,
        output_aedt_path=output_aedt_path,
        design_name="fake_design",
        hfss_factory=_fake_hfss_factory,
    )

    assert result == {
        "step_path": str(step_path),
        "aedt_path": str(output_aedt_path),
        "imported_object_names": ["floor", "wall"],
    }
    assert design_names == ["fake_design"]
    assert output_aedt_path.parent.is_dir()
    session = created_sessions[0]
    assert session.modeler.import_calls == [step_path]
    assert session.modeler.model_state_calls == [("floor", False), ("wall", False)]
    assert session.save_project_calls == [str(output_aedt_path)]
    assert session.desktop_class.release_calls == [(True, True)]

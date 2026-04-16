from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

import examples.type2.import_tx_rect_void_step_to_hfss as import_smoke_module
from examples.type2.import_tx_rect_void_step_to_hfss import _HfssSession
from examples.type2.import_tx_rect_void_step_to_hfss import _ModeledImportEntryBuilder
from examples.type2.import_tx_rect_void_step_to_hfss import import_tx_rect_void_step_to_hfss


def _write_step_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")


def _write_metadata_json(path: Path, *, step_path: Path, source_toml_path: Path | None = None) -> None:
    payload: dict[str, object] = {
        "modeled_objects": [
            {
                "object_id": "tx_rect_void_coil",
                "role": "tx_single_coil",
                "material": "composite",
                "model_state": True,
                "step_path": str(step_path),
                "expected_exported_body_names": ["tx_pcb_l0", "tx_copper_l0"],
                "expected_exported_body_count": 2,
                "canonical_coordinates": {"frame_origin_xyz": [0.0, 0.0, 0.0]},
                "terminal_metadata": {"path": "A_cw_to_a"},
            }
        ]
    }
    if source_toml_path is not None:
        payload["source_toml_path"] = str(source_toml_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class _FakeSmokeModeler:
    def __init__(
        self,
        *,
        import_result: object = True,
        before_import_names: tuple[str, ...] = ("existing",),
        after_import_names: tuple[str, ...] = ("existing", "coil_a", "coil_b"),
    ) -> None:
        self._object_names = before_import_names
        self._after_import_names = after_import_names
        self._import_result = import_result
        self.import_calls: list[Path] = []

    @property
    def object_names(self) -> tuple[str, ...]:
        return self._object_names

    def import_3d_cad(self, input_file: str | Path) -> object:
        self.import_calls.append(Path(input_file))
        self._object_names = self._after_import_names
        return self._import_result


class _FakeDesktop:
    def __init__(self, *, release_result: object = True) -> None:
        self._release_result = release_result
        self.release_calls: list[tuple[bool, bool]] = []

    def release_desktop(self, close_projects: bool, close_on_exit: bool) -> object:
        self.release_calls.append((close_projects, close_on_exit))
        return self._release_result


class _FakeHfss:
    def __init__(
        self,
        *,
        modeler: _FakeSmokeModeler | None = None,
        save_project_result: object = True,
        release_result: object = True,
    ) -> None:
        if modeler is None:
            modeler = _FakeSmokeModeler()
        self.modeler = modeler
        self.desktop_class = _FakeDesktop(release_result=release_result)
        self._save_project_result = save_project_result
        self.save_project_calls: list[str] = []

    def save_project(self, path: str) -> object:
        self.save_project_calls.append(path)
        return self._save_project_result


def test_tx_rect_void_modeled_step_import_smoke_uses_fake_hfss_and_adapter(tmp_path: Path) -> None:
    step_path = tmp_path / "step" / "tx_rect_void.step"
    metadata_path = tmp_path / "step" / "tx_rect_void.metadata.json"
    output_aedt_path = tmp_path / "aedt" / "tx_rect_void_import.aedt"
    _write_step_file(step_path)
    _write_metadata_json(metadata_path, step_path=step_path)

    session = _FakeHfss()
    adapter_calls: list[tuple[dict[str, object], list[str]]] = []

    def _adapter_builder(modeled_object: Mapping[str, object], imported_object_names: Sequence[str]) -> dict[str, object]:
        adapter_calls.append((dict(modeled_object), list(imported_object_names)))
        return {
            "object_id": "tx_rect_void_coil",
            "role": "tx_single_coil",
            "material": "composite",
            "model_state": True,
            "step_path": str(step_path),
            "canonical_coordinates": {"frame_origin_xyz": [0.0, 0.0, 0.0]},
            "terminal_metadata": {"path": "A_cw_to_a"},
            "imported_object_names": list(imported_object_names),
        }

    def _fake_hfss_factory(_: str) -> _HfssSession:
        return cast(_HfssSession, session)

    result = import_tx_rect_void_step_to_hfss(
        step_path=step_path,
        metadata_json_path=metadata_path,
        output_aedt_path=output_aedt_path,
        design_name="tx_rect_void_fake_design",
        hfss_factory=_fake_hfss_factory,
        modeled_entry_builder_loader=lambda: cast(_ModeledImportEntryBuilder, _adapter_builder),
    )

    assert result == {
        "import_result": {
            "step_path": str(step_path),
            "metadata_path": str(metadata_path),
            "aedt_path": str(output_aedt_path),
            "imported_object_names": ["coil_a", "coil_b"],
        },
        "imported_modeled_object_entry": {
            "object_id": "tx_rect_void_coil",
            "role": "tx_single_coil",
            "material": "composite",
            "model_state": True,
            "step_path": str(step_path),
            "canonical_coordinates": {"frame_origin_xyz": [0.0, 0.0, 0.0]},
            "terminal_metadata": {"path": "A_cw_to_a"},
            "imported_object_names": ["coil_a", "coil_b"],
        },
    }
    assert session.modeler.import_calls == [step_path]
    assert session.save_project_calls == [str(output_aedt_path)]
    assert session.desktop_class.release_calls == [(True, True)]
    assert adapter_calls[0][0]["step_path"] == str(step_path)
    assert adapter_calls[0][1] == ["coil_a", "coil_b"]


def test_tx_rect_void_modeled_step_import_smoke_accepts_tuple_imported_names_from_adapter(tmp_path: Path) -> None:
    step_path = tmp_path / "step" / "tx_rect_void.step"
    metadata_path = tmp_path / "step" / "tx_rect_void.metadata.json"
    _write_step_file(step_path)
    _write_metadata_json(metadata_path, step_path=step_path)
    session = _FakeHfss()

    def _adapter_builder(_: Mapping[str, object], __: Sequence[str]) -> dict[str, object]:
        return {
            "object_id": "tx_rect_void_coil",
            "role": "tx_single_coil",
            "material": "composite",
            "model_state": True,
            "step_path": str(step_path),
            "canonical_coordinates": {"frame_origin_xyz": [0.0, 0.0, 0.0]},
            "terminal_metadata": {"path": "A_cw_to_a"},
            "imported_object_names": ("coil_a", "coil_b"),
        }

    result = import_tx_rect_void_step_to_hfss(
        step_path=step_path,
        metadata_json_path=metadata_path,
        hfss_factory=lambda _: cast(_HfssSession, session),
        modeled_entry_builder_loader=lambda: cast(_ModeledImportEntryBuilder, _adapter_builder),
    )

    assert result["imported_modeled_object_entry"]["imported_object_names"] == ["coil_a", "coil_b"]


def test_tx_rect_void_modeled_step_import_smoke_loads_default_adapter_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    step_path = tmp_path / "step" / "tx_rect_void.step"
    metadata_path = tmp_path / "step" / "tx_rect_void.metadata.json"
    output_aedt_path = tmp_path / "aedt" / "tx_rect_void_import.aedt"
    _write_step_file(step_path)
    _write_metadata_json(metadata_path, step_path=step_path)

    session = _FakeHfss()
    adapter_call_names: list[list[str]] = []
    module_name = "peetsfea.backend.pyaedt.type2_modeled_import_adapter"
    fake_adapter_module = ModuleType(module_name)

    def _module_adapter(modeled_object: Mapping[str, object], imported_object_names: Sequence[str]) -> dict[str, object]:
        adapter_call_names.append(list(imported_object_names))
        return {
            "object_id": "tx_rect_void_coil",
            "role": "tx_single_coil",
            "material": "composite",
            "model_state": True,
            "step_path": str(step_path),
            "canonical_coordinates": {"frame_origin_xyz": [0.0, 0.0, 0.0]},
            "terminal_metadata": {"path": "A_cw_to_a"},
            "imported_object_names": list(imported_object_names),
        }

    setattr(fake_adapter_module, "build_single_imported_modeled_object_entry", _module_adapter)
    monkeypatch.setitem(sys.modules, module_name, fake_adapter_module)

    result = import_tx_rect_void_step_to_hfss(
        step_path=step_path,
        metadata_json_path=metadata_path,
        output_aedt_path=output_aedt_path,
        design_name="tx_rect_void_fake_design",
        hfss_factory=lambda _: cast(_HfssSession, session),
    )

    assert result["import_result"]["imported_object_names"] == ["coil_a", "coil_b"]
    assert adapter_call_names == [["coil_a", "coil_b"]]


def test_tx_rect_void_modeled_step_import_smoke_raises_for_missing_metadata_before_hfss_launch(tmp_path: Path) -> None:
    step_path = tmp_path / "step" / "tx_rect_void.step"
    _write_step_file(step_path)
    metadata_path = tmp_path / "step" / "missing.metadata.json"
    launch_count = 0

    def _counting_hfss_factory(_: str) -> _HfssSession:
        nonlocal launch_count
        launch_count += 1
        return cast(_HfssSession, _FakeHfss())

    def _unused_adapter_builder(_: Mapping[str, object], __: Sequence[str]) -> dict[str, object]:
        return {}

    with pytest.raises(FileNotFoundError, match=r"Metadata JSON file not found"):
        import_tx_rect_void_step_to_hfss(
            step_path=step_path,
            metadata_json_path=metadata_path,
            hfss_factory=_counting_hfss_factory,
            modeled_entry_builder_loader=lambda: cast(_ModeledImportEntryBuilder, _unused_adapter_builder),
        )

    assert launch_count == 0


def test_tx_rect_void_modeled_step_import_smoke_raises_when_import_returns_false(tmp_path: Path) -> None:
    step_path = tmp_path / "step" / "tx_rect_void.step"
    metadata_path = tmp_path / "step" / "tx_rect_void.metadata.json"
    _write_step_file(step_path)
    _write_metadata_json(metadata_path, step_path=step_path)
    session = _FakeHfss(modeler=_FakeSmokeModeler(import_result=False))

    def _unused_adapter_builder(_: Mapping[str, object], __: Sequence[str]) -> dict[str, object]:
        return {}

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: import_3d_cad"):
        import_tx_rect_void_step_to_hfss(
            step_path=step_path,
            metadata_json_path=metadata_path,
            hfss_factory=lambda _: cast(_HfssSession, session),
            modeled_entry_builder_loader=lambda: cast(_ModeledImportEntryBuilder, _unused_adapter_builder),
        )

    assert session.desktop_class.release_calls == [(True, True)]


def test_tx_rect_void_modeled_step_import_smoke_raises_when_import_diff_has_duplicates(tmp_path: Path) -> None:
    step_path = tmp_path / "step" / "tx_rect_void.step"
    metadata_path = tmp_path / "step" / "tx_rect_void.metadata.json"
    _write_step_file(step_path)
    _write_metadata_json(metadata_path, step_path=step_path)
    session = _FakeHfss(modeler=_FakeSmokeModeler(after_import_names=("existing", "coil_a", "coil_a")))

    def _unused_adapter_builder(_: Mapping[str, object], __: Sequence[str]) -> dict[str, object]:
        return {}

    with pytest.raises(RuntimeError, match=r"duplicate new HFSS object names"):
        import_tx_rect_void_step_to_hfss(
            step_path=step_path,
            metadata_json_path=metadata_path,
            hfss_factory=lambda _: cast(_HfssSession, session),
            modeled_entry_builder_loader=lambda: cast(_ModeledImportEntryBuilder, _unused_adapter_builder),
        )

    assert session.desktop_class.release_calls == [(True, True)]


def test_tx_rect_void_modeled_step_import_smoke_auto_resolves_type2_generated_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    type2_toml_path = repo_root / "examples" / "type2" / "type2.toml"
    exporter_script_path = repo_root / "examples" / "type2" / "generate_type2_step.py"
    step_path = repo_root / "run" / "step" / "type2" / "objects" / "tx_rect_void_coil.step"
    metadata_path = repo_root / "run" / "step" / "type2" / "metadata" / "tx_rect_void_coil.metadata.json"

    type2_toml_path.parent.mkdir(parents=True, exist_ok=True)
    type2_toml_path.write_text("spec_version = \"0.2.22\"\n", encoding="utf-8")
    exporter_script_path.write_text("# placeholder exporter for tests\n", encoding="utf-8")
    _write_step_file(step_path)
    _write_metadata_json(metadata_path, step_path=step_path, source_toml_path=type2_toml_path)

    monkeypatch.setattr(import_smoke_module, "REPO_ROOT", repo_root)
    session = _FakeHfss()

    def _adapter_builder(modeled_object: Mapping[str, object], imported_object_names: Sequence[str]) -> dict[str, object]:
        return {
            "object_id": "tx_rect_void_coil",
            "role": "tx_single_coil",
            "material": "composite",
            "model_state": True,
            "step_path": str(modeled_object["step_path"]),
            "canonical_coordinates": {"frame_origin_xyz": [0.0, 0.0, 0.0]},
            "terminal_metadata": {"path": "A_cw_to_a"},
            "imported_object_names": list(imported_object_names),
        }

    result = import_tx_rect_void_step_to_hfss(
        hfss_factory=lambda _: cast(_HfssSession, session),
        modeled_entry_builder_loader=lambda: cast(_ModeledImportEntryBuilder, _adapter_builder),
        type2_toml_path=type2_toml_path,
        type2_exporter_path=exporter_script_path,
    )

    assert result["import_result"]["step_path"] == str(step_path)
    assert result["import_result"]["metadata_path"] == str(metadata_path)
    assert result["import_result"]["imported_object_names"] == ["coil_a", "coil_b"]


def test_tx_rect_void_modeled_step_import_smoke_auto_resolve_invokes_type2_exporter_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    type2_toml_path = repo_root / "examples" / "type2" / "type2.toml"
    exporter_script_path = repo_root / "examples" / "type2" / "generate_type2_step.py"
    generated_step_path = repo_root / "run" / "step" / "type2" / "objects" / "tx_rect_void_coil.step"
    generated_metadata_path = repo_root / "run" / "step" / "type2" / "metadata" / "tx_rect_void_coil.metadata.json"

    type2_toml_path.parent.mkdir(parents=True, exist_ok=True)
    type2_toml_path.write_text("spec_version = \"0.2.22\"\n", encoding="utf-8")
    exporter_script_path.write_text("# placeholder exporter for tests\n", encoding="utf-8")
    monkeypatch.setattr(import_smoke_module, "REPO_ROOT", repo_root)

    run_calls: list[list[str]] = []

    def _fake_run(cmd: list[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess[str]:
        assert cwd == repo_root
        assert check is True
        run_calls.append(list(cmd))
        _write_step_file(generated_step_path)
        _write_metadata_json(generated_metadata_path, step_path=generated_step_path, source_toml_path=type2_toml_path)
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(import_smoke_module.subprocess, "run", _fake_run)
    session = _FakeHfss()

    def _adapter_builder(modeled_object: Mapping[str, object], imported_object_names: Sequence[str]) -> dict[str, object]:
        return {
            "object_id": "tx_rect_void_coil",
            "role": "tx_single_coil",
            "material": "composite",
            "model_state": True,
            "step_path": str(modeled_object["step_path"]),
            "canonical_coordinates": {"frame_origin_xyz": [0.0, 0.0, 0.0]},
            "terminal_metadata": {"path": "A_cw_to_a"},
            "imported_object_names": list(imported_object_names),
        }

    result = import_tx_rect_void_step_to_hfss(
        hfss_factory=lambda _: cast(_HfssSession, session),
        modeled_entry_builder_loader=lambda: cast(_ModeledImportEntryBuilder, _adapter_builder),
        type2_toml_path=type2_toml_path,
        type2_exporter_path=exporter_script_path,
    )

    assert run_calls == [[sys.executable, str(exporter_script_path.resolve())]]
    assert result["import_result"]["step_path"] == str(generated_step_path)
    assert result["import_result"]["metadata_path"] == str(generated_metadata_path)

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from peetsfea.aedt import Hfss

from peetsfea.legacy.type1.backend.pyaedt.geometry import build as build_module
from peetsfea.legacy.type1.backend.pyaedt.geometry.builders.build_artifacts import (
    _create_terminal_lumped_port_and_capture_assignment_from_edge_ids,
)
from peetsfea.types.manifest import Manifest


class _FakeDesktop:
    def __init__(self, *, release_result: bool | None = None) -> None:
        self.aedt_process_id: int | None = 1234
        self.release_result = release_result
        self.release_calls: list[tuple[bool | None, bool | None]] = []

    def release_desktop(
        self,
        close_projects: bool | None = True,
        close_on_exit: bool | None = True,
    ) -> bool | None:
        self.release_calls.append((close_projects, close_on_exit))
        return self.release_result


class _FakeBuildHfss:
    def __init__(self, *, release_result: bool | None = None) -> None:
        self.desktop_class = _FakeDesktop(release_result=release_result)
        self.modeler = object()


class _FakeBoundaryModule:
    def __init__(self, *, result: bool | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[list[object]] = []

    def AssignLumpedPort(self, props: list[object]) -> bool | None:
        self.calls.append(list(props))
        if self.error is not None:
            raise self.error
        return self.result

    def GetBoundaries(self) -> list[object]:
        return []


class _FakePortHfss:
    def __init__(self, boundary_module: _FakeBoundaryModule) -> None:
        self.excitation_names: list[str] = []
        self.oboundary = boundary_module


def _patch_build_square_spiral_context(
    monkeypatch: pytest.MonkeyPatch,
    *,
    hfss: _FakeBuildHfss,
    metadata_result: object | None = None,
    metadata_error: Exception | None = None,
) -> None:
    ctx = SimpleNamespace(
        aedt_path=Path("/tmp/failfast-demo.aedt"),
        metadata_path=Path("/tmp/failfast-demo.json"),
        design_id="failfast-demo",
        close_on_exit=True,
    )

    monkeypatch.setattr(build_module, "_prepare_runtime", lambda manifest: ctx)
    monkeypatch.setattr(build_module, "create_hfss_session", lambda manifest, aedt_path: cast(Hfss, hfss))
    monkeypatch.setattr(build_module, "_assign_design_variables", lambda hfss_arg, manifest: None)
    monkeypatch.setattr(build_module, "_build_scene", lambda ctx_arg, state, modeler: None)
    monkeypatch.setattr(build_module, "_build_all_coils", lambda ctx_arg, state, modeler: None)
    monkeypatch.setattr(build_module, "_finalize_geometry", lambda ctx_arg, state, inputs, modeler, hfss_arg: None)
    monkeypatch.setattr(build_module, "_build_tx_ferrite", lambda ctx_arg, state, modeler, hfss_arg: None)
    monkeypatch.setattr(build_module, "_build_rx_ferrite", lambda ctx_arg, state, modeler, hfss_arg: None)
    monkeypatch.setattr(build_module, "rotate_tx_mode0_objects_if_needed", lambda ctx_arg, state, inputs, modeler: None)

    def _fake_build_and_save_metadata(ctx_arg: object, state: object, manifest: object, hfss_arg: object) -> object:
        _ = ctx_arg, state, manifest, hfss_arg
        if metadata_error is not None:
            raise metadata_error
        return metadata_result

    monkeypatch.setattr(build_module, "_build_and_save_metadata", _fake_build_and_save_metadata)


def test_build_square_spiral_from_manifest_reraises_original_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    original_error = ValueError("metadata build failed")
    hfss = _FakeBuildHfss()
    _patch_build_square_spiral_context(monkeypatch, hfss=hfss, metadata_error=original_error)

    with pytest.raises(ValueError, match="metadata build failed") as exc_info:
        build_module.build_square_spiral_from_manifest(cast(Manifest, {}))

    assert exc_info.value is original_error
    assert hfss.desktop_class.release_calls == [(True, True)]


def test_build_square_spiral_from_manifest_asserts_false_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    hfss = _FakeBuildHfss()
    _patch_build_square_spiral_context(monkeypatch, hfss=hfss, metadata_result=False)

    with pytest.raises(RuntimeError, match=r"build_square_spiral_from_manifest returned False"):
        build_module.build_square_spiral_from_manifest(cast(Manifest, {}))

    assert hfss.desktop_class.release_calls == [(True, True)]


def test_build_square_spiral_from_manifest_raises_when_release_desktop_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hfss = _FakeBuildHfss(release_result=False)
    _patch_build_square_spiral_context(monkeypatch, hfss=hfss, metadata_result={"design_id": "ok"})

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: release_desktop") as exc_info:
        build_module.build_square_spiral_from_manifest(cast(Manifest, {}))

    message = str(exc_info.value)
    assert "design_id='failfast-demo'" in message
    assert "close_projects=True" in message
    assert "close_on_exit=True" in message
    assert hfss.desktop_class.release_calls == [(True, True)]


def test_create_terminal_lumped_port_asserts_false_return() -> None:
    boundary_module = _FakeBoundaryModule(result=False)
    hfss = _FakePortHfss(boundary_module)

    with pytest.raises(AssertionError, match=r"AssignLumpedPort returned False"):
        _create_terminal_lumped_port_and_capture_assignment_from_edge_ids(
            hfss=cast(Hfss, hfss),
            signal_object_name="signal",
            signal_edge_id=11,
            reference_object_name="reference",
            reference_edge_id=22,
            role="tx",
            context="test port creation",
        )


def test_create_terminal_lumped_port_reraises_original_exception() -> None:
    original_error = RuntimeError("assign exploded")
    boundary_module = _FakeBoundaryModule(error=original_error)
    hfss = _FakePortHfss(boundary_module)

    with pytest.raises(RuntimeError, match="assign exploded") as exc_info:
        _create_terminal_lumped_port_and_capture_assignment_from_edge_ids(
            hfss=cast(Hfss, hfss),
            signal_object_name="signal",
            signal_edge_id=11,
            reference_object_name="reference",
            reference_edge_id=22,
            role="rx",
            context="test port creation",
        )

    assert exc_info.value is original_error

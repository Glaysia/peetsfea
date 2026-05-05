from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

import peetsfea.legacy.type1.pipeline.run_design as runner
from peetsfea.legacy.type1.backend.pyaedt.geometry.build import _write_geometry_metadata_if_enabled
from peetsfea.types.manifest import GeometryMetadata, Manifest, ManifestInputs
from tests.fixtures.legacy.type1_spec import write_type1_toml

pytestmark = pytest.mark.contract


def test_ac06_default_run_does_not_emit_manifest_or_geometry_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "spec.toml"
    write_type1_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("1" * 40))

    result = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=5, backend="hfss"))
    manifest = result["manifest"]
    design_id = manifest["design_id"]

    assert result["manifest_path"] is None, "AC-06 manifest json must not be emitted by default"
    assert result["geometry_metadata_path"] is None, "AC-06 geometry metadata json must not be emitted by default"
    assert manifest["manifest_path"] is None, "AC-06 manifest.manifest_path must be None by default"
    assert (tmp_path / f"manifest_{design_id}.json").exists() is False, "AC-06 manifest_<design_id>.json must not exist"


def test_ac07_optional_flags_enable_manifest_and_geometry_metadata_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    toml_path = tmp_path / "spec.toml"
    write_type1_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("2" * 40))

    manifest_result = runner.run(
        runner.RunConfig(
            "/bin/ansysedt",
            str(tmp_path),
            str(toml_path),
            seed=6,
            backend="hfss",
            emit_manifest_json=True,
        )
    )

    assert manifest_result["manifest_path"] is not None, "AC-07 manifest must be emitted when emit_manifest_json=True"
    assert manifest_result["manifest"]["manifest_path"] == manifest_result["manifest_path"], (
        "AC-07 manifest_path contract mismatch between RunResult and Manifest"
    )
    assert Path(manifest_result["manifest_path"]).exists() is True, "AC-07 manifest output file must exist"

    metadata_result = runner.run(
        runner.RunConfig(
            "/bin/ansysedt",
            str(tmp_path),
            str(toml_path),
            seed=8,
            backend="hfss",
            emit_geometry_metadata_json=True,
        )
    )
    assert metadata_result["geometry_metadata_path"] is not None, (
        "AC-07 geometry metadata path must be set when emit_geometry_metadata_json=True"
    )

    manifest_for_gate = cast(Manifest, dict(metadata_result["manifest"]))
    manifest_inputs = dict(manifest_for_gate["inputs"])
    manifest_inputs["emit_geometry_metadata_json"] = True
    manifest_for_gate["inputs"] = cast(ManifestInputs, manifest_inputs)

    metadata_path = Path(metadata_result["geometry_metadata_path"])
    metadata = cast(GeometryMetadata, {"design_id": "dummy-enabled"})

    _write_geometry_metadata_if_enabled(manifest_for_gate, metadata, metadata_path)
    assert metadata_path.exists() is True, "AC-07 geometry_metadata must be emitted only when flag is enabled"

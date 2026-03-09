from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Callable

import pytest

import peetsfea.pipeline.run_batch as run_batch
from peetsfea.pipeline.run_batch import SampleManifestEntry, build_aedt_from_manifest_entry, generate_sample_artifact_for_seed
from peetsfea.pipeline.uniform_seedset import generate_eager_uniform_feasible_seed_points
from peetsfea.spec.loader import load_toml_bytes
from tests.fixtures.type1_spec import write_type1_toml


def _load_script(name: str) -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {name}.py module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_manifest_entry(*, design_id: str, toml_path: Path, source_toml_path: Path) -> SampleManifestEntry:
    return {
        "design_id": design_id,
        "seed": 11,
        "retry_attempt": 0,
        "toml_path": str(toml_path.resolve()),
        "source_toml_path": str(source_toml_path.resolve()),
        "design_unique_hash": "dead",
        "toml_space_hash": "cafe",
        "toml_hash": "a" * 64,
    }


def test_sample_script_generates_resolved_tomls_and_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sample_script = _load_script("sample")
    run_root = tmp_path / "run"
    run_root.mkdir()
    write_type1_toml(run_root / "type1.toml")

    monkeypatch.setattr(sample_script, "cwd", tmp_path)
    monkeypatch.setattr(sample_script, "SOURCE_TOML_PATH", run_root / "type1.toml")
    monkeypatch.setattr(sample_script, "SAMPLE_OUTPUT_DIR", run_root / "toml")
    monkeypatch.setattr(sample_script, "SAMPLE_MANIFEST_PATH", run_root / "toml" / "manifest.json")
    monkeypatch.setattr(sample_script, "ANSYS_RUN_DIR", run_root / "aedt")
    monkeypatch.setattr(sample_script, "EAGER_SEED_END", 100)
    monkeypatch.setattr(sample_script, "EAGER_TARGET_COUNT", 3)

    entries = sample_script.generate_sample_manifest()

    assert len(entries) == 3
    manifest_path = run_root / "toml" / "manifest.json"
    manifest_entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_entries == entries
    expected_seeds = [
        point.seed
        for point in generate_eager_uniform_feasible_seed_points(
            spec_path=run_root / "type1.toml",
            seed_start=sample_script.EAGER_SEED_START,
            seed_end=sample_script.EAGER_SEED_END,
            target_size=sample_script.EAGER_TARGET_COUNT,
            max_attempts=sample_script.EAGER_MAX_ATTEMPTS,
        )
    ]
    assert [entry["seed"] for entry in entries] == expected_seeds
    for entry in entries:
        toml_path = Path(entry["toml_path"])
        assert toml_path.is_absolute() is True
        assert toml_path.exists() is True
        assert toml_path.stem == entry["design_id"]
        exported_spec, _ = load_toml_bytes(toml_path)
        assert exported_spec["ferrite"]["present"]["range"][3] == 1


def test_build_debug_processes_full_manifest_sequentially(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    build_script = _load_script("build")
    source_toml_path = tmp_path / "source.toml"
    source_toml_path.write_text("spec_version = \"0.2.12\"\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    entries = [
        _make_manifest_entry(design_id="000001_dead_cafe_0", toml_path=tmp_path / "a.toml", source_toml_path=source_toml_path),
        _make_manifest_entry(design_id="000002_dead_cafe_0", toml_path=tmp_path / "b.toml", source_toml_path=source_toml_path),
    ]
    manifest_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    calls: list[tuple[str, bool]] = []

    def _fake_build(entry: SampleManifestEntry, *, ansys_run_dir: Path, ansys_executable_path: str, is_debug: bool) -> bool:
        calls.append((entry["toml_path"], is_debug))
        return True

    monkeypatch.setattr(build_script, "build_aedt_from_manifest_entry", _fake_build)
    monkeypatch.setenv("PEETSFEA_DEBUG", "1")

    result = build_script.build_from_manifest_path(manifest_path)

    assert result == [True, True]
    assert calls == [(entries[0]["toml_path"], True), (entries[1]["toml_path"], True)]


def test_build_non_debug_uses_process_pool_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    build_script = _load_script("build")
    source_toml_path = tmp_path / "source.toml"
    source_toml_path.write_text("spec_version = \"0.2.12\"\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    entries = [
        _make_manifest_entry(design_id="000001_dead_cafe_0", toml_path=tmp_path / "a.toml", source_toml_path=source_toml_path),
        _make_manifest_entry(design_id="000002_dead_cafe_0", toml_path=tmp_path / "b.toml", source_toml_path=source_toml_path),
    ]
    manifest_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    calls: list[str] = []
    workers: list[int] = []

    def _fake_build(entry: SampleManifestEntry, *, ansys_run_dir: Path, ansys_executable_path: str, is_debug: bool) -> bool:
        assert is_debug is False
        calls.append(entry["toml_path"])
        return True

    class _FakeProcessPoolExecutor:
        def __init__(self, *, max_workers: int) -> None:
            workers.append(max_workers)

        def __enter__(self) -> "_FakeProcessPoolExecutor":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

        def map(self, fn: Callable[[SampleManifestEntry], bool], values: list[SampleManifestEntry]) -> list[bool]:
            return [fn(value) for value in values]

    monkeypatch.setattr(build_script, "build_aedt_from_manifest_entry", _fake_build)
    monkeypatch.setattr(build_script, "ProcessPoolExecutor", _FakeProcessPoolExecutor)
    monkeypatch.delenv("PEETSFEA_DEBUG", raising=False)

    result = build_script.build_from_manifest_path(manifest_path)

    assert result == [True, True]
    assert workers == [build_script.BUILD_WORKER_COUNT]
    assert calls == [entries[0]["toml_path"], entries[1]["toml_path"]]


def test_build_helper_uses_toml_stem_for_aedt_and_cleans_aedtresults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    source_toml_path = run_root / "type1.toml"
    write_type1_toml(source_toml_path)
    entry = generate_sample_artifact_for_seed(
        source_toml_path=source_toml_path,
        output_dir=run_root / "toml",
        ansys_run_dir=run_root / "aedt",
        ansys_executable_path="/opt/ansys_inc/v252/AnsysEM",
        seed=11,
    )

    def _fake_build(manifest: dict[str, object]) -> dict[str, str]:
        design_id = str(manifest["design_id"])
        aedt_dir = run_root / "aedt"
        aedt_dir.mkdir(parents=True, exist_ok=True)
        aedt_path = aedt_dir / f"{design_id}.aedt"
        aedt_path.write_text("fake aedt", encoding="utf-8")
        results_dir = aedt_dir / f"{design_id}.aedtresults"
        results_dir.mkdir()
        (results_dir / "marker.txt").write_text("marker", encoding="utf-8")
        return {"aedt_path": str(aedt_path)}

    monkeypatch.setattr(run_batch, "build_square_spiral_from_manifest", _fake_build)

    ok = build_aedt_from_manifest_entry(
        entry=entry,
        ansys_run_dir=run_root / "aedt",
        ansys_executable_path="/opt/ansys_inc/v252/AnsysEM",
        is_debug=False,
    )

    assert ok is True
    design_id = Path(entry["toml_path"]).stem
    assert (run_root / "aedt" / f"{design_id}.aedt").exists() is True
    assert (run_root / "aedt" / f"{design_id}.aedtresults").exists() is False


def test_build_helper_cleans_failed_design_artifacts_and_aedtresults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    source_toml_path = run_root / "type1.toml"
    write_type1_toml(source_toml_path)
    entry = generate_sample_artifact_for_seed(
        source_toml_path=source_toml_path,
        output_dir=run_root / "toml",
        ansys_run_dir=run_root / "aedt",
        ansys_executable_path="/opt/ansys_inc/v252/AnsysEM",
        seed=11,
    )

    def _failing_build(manifest: dict[str, object]) -> dict[str, str]:
        design_id = str(manifest["design_id"])
        aedt_dir = run_root / "aedt"
        aedt_dir.mkdir(parents=True, exist_ok=True)
        (aedt_dir / f"{design_id}.aedt").write_text("fake aedt", encoding="utf-8")
        results_dir = aedt_dir / f"{design_id}.aedtresults"
        results_dir.mkdir()
        (results_dir / "marker.txt").write_text("marker", encoding="utf-8")
        raise RuntimeError("builder failed")

    monkeypatch.setattr(run_batch, "build_square_spiral_from_manifest", _failing_build)

    ok = build_aedt_from_manifest_entry(
        entry=entry,
        ansys_run_dir=run_root / "aedt",
        ansys_executable_path="/opt/ansys_inc/v252/AnsysEM",
        is_debug=False,
    )

    assert ok is False
    aedt_dir = run_root / "aedt"
    assert list(aedt_dir.glob("*.aedt")) == []
    assert list(aedt_dir.glob("*.aedtresults")) == []


def test_build_helper_rejects_non_frozen_toml_before_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_toml_path = tmp_path / "type1.toml"
    write_type1_toml(source_toml_path)
    entry = _make_manifest_entry(
        design_id="000011_dead_cafe_0",
        toml_path=source_toml_path,
        source_toml_path=source_toml_path,
    )

    monkeypatch.setattr(run_batch, "run", lambda config: (_ for _ in ()).throw(AssertionError("run() must not execute")))
    monkeypatch.setattr(
        run_batch,
        "build_square_spiral_from_manifest",
        lambda manifest: (_ for _ in ()).throw(AssertionError("geometry build must not execute")),
    )

    ok = build_aedt_from_manifest_entry(
        entry=entry,
        ansys_run_dir=tmp_path / "aedt",
        ansys_executable_path="/opt/ansys_inc/v252/AnsysEM",
        is_debug=False,
    )

    assert ok is False

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable

import pytest

import peetsfea.pipeline.run_batch as run_batch
from peetsfea.pipeline.run_batch import SampleManifestEntry, build_aedt_from_manifest_entry, generate_sample_artifact_for_seed
from peetsfea.pipeline.uniform_seedset import generate_eager_uniform_feasible_seed_points
from peetsfea.spec.loader import load_toml_bytes, require_table
from tests.fixtures.type1_spec import write_type1_toml


def _load_script(name: str) -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {name}.py module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
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

    entries = sample_script.generate_sample_manifest(
        seed_start=0,
        seed_end=100,
        target_count=3,
        source_toml_path=run_root / "type1.toml",
        output_dir=run_root / "toml",
        manifest_path=run_root / "toml" / "manifest.json",
        ansys_run_dir=run_root / "aedt",
    )

    assert len(entries) == 3
    manifest_path = run_root / "toml" / "manifest.json"
    manifest_entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_entries == entries
    expected_seeds = [
        point.seed
        for point in generate_eager_uniform_feasible_seed_points(
            spec_path=run_root / "type1.toml",
            seed_start=0,
            seed_end=100,
            target_size=3,
            max_attempts=sample_script.DEFAULT_EAGER_MAX_ATTEMPTS,
        )
    ]
    assert [entry["seed"] for entry in entries] == expected_seeds
    for entry in entries:
        toml_path = Path(entry["toml_path"])
        assert toml_path.is_absolute() is True
        assert toml_path.exists() is True
        assert toml_path.stem == entry["design_id"]
        exported_spec, _ = load_toml_bytes(toml_path)
        ferrite_table = require_table(exported_spec["ferrite"], "ferrite")
        ferrite_present = require_table(ferrite_table["present"], "ferrite.present")
        present_range = ferrite_present["range"]
        assert isinstance(present_range, list)
        assert present_range[3] == 1


def test_sample_script_seed_start_helpers_use_versioned_output_dirs(tmp_path: Path) -> None:
    sample_script = _load_script("sample")

    output_dir = sample_script.sample_output_dir_for_seed_start(500, workspace_root=tmp_path)
    manifest_path = sample_script.sample_manifest_path_for_seed_start(500, workspace_root=tmp_path)
    ansys_run_dir = sample_script.sample_ansys_run_dir_for_seed_start(500, workspace_root=tmp_path)

    assert output_dir == tmp_path / "run" / "toml" / f"toml_{sample_script.__version__}_500"
    assert manifest_path == output_dir / "manifest.json"
    assert ansys_run_dir == tmp_path / "run" / "aedt" / f"aedt_{sample_script.__version__}_500"


def test_multi_sample_orchestrates_profiles_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    multi_sample_script = _load_script("multi_sample")
    calls: list[tuple[int, int, int]] = []

    def _fake_generate(*, seed_start: int, seed_end: int, target_count: int) -> list[dict[str, object]]:
        calls.append((seed_start, seed_end, target_count))
        return [{"seed": seed_start}]

    profiles = (
        multi_sample_script.SampleProfile(seed_start=0, seed_end=500, target_count=100),
        multi_sample_script.SampleProfile(seed_start=500, seed_end=1000, target_count=1000),
    )
    monkeypatch.setattr(multi_sample_script, "generate_sample_manifest", _fake_generate)

    result = multi_sample_script.generate_all_sample_manifests(profiles)

    assert calls == [(0, 500, 100), (500, 1000, 1000)]
    assert result == [[{"seed": 0}], [{"seed": 500}]]


def test_build_debug_processes_full_manifest_sequentially(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    build_script = _load_script("build")
    source_toml_path = tmp_path / "source.toml"
    source_toml_path.write_text("spec_version = \"0.2.14\"\n", encoding="utf-8")
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

    result = build_script.build_from_manifest_path(manifest_path, ansys_run_dir=tmp_path / "aedt")

    assert result == [True, True]
    assert calls == [(entries[0]["toml_path"], True), (entries[1]["toml_path"], True)]


def test_build_non_debug_uses_process_pool_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    build_script = _load_script("build")
    source_toml_path = tmp_path / "source.toml"
    source_toml_path.write_text("spec_version = \"0.2.14\"\n", encoding="utf-8")
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

        def map(
            self,
            fn: Callable[[tuple[SampleManifestEntry, Path]], bool],
            values: list[tuple[SampleManifestEntry, Path]],
        ) -> list[bool]:
            return [fn(value) for value in values]

    monkeypatch.setattr(build_script, "build_aedt_from_manifest_entry", _fake_build)
    monkeypatch.setattr(build_script, "ProcessPoolExecutor", _FakeProcessPoolExecutor)
    monkeypatch.delenv("PEETSFEA_DEBUG", raising=False)

    result = build_script.build_from_manifest_path(manifest_path, ansys_run_dir=tmp_path / "aedt")

    assert result == [True, True]
    assert workers == [build_script.BUILD_WORKER_COUNT]
    assert calls == [entries[0]["toml_path"], entries[1]["toml_path"]]


def test_multi_build_discovers_batch_manifests_and_ignores_top_level_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    multi_build_script = _load_script("multi_build")
    calls: list[tuple[Path, Path]] = []

    def _fake_build(manifest_path: Path, *, ansys_run_dir: Path) -> list[bool]:
        calls.append((manifest_path, ansys_run_dir))
        return [True]

    run_toml_root = tmp_path / "run" / "toml"
    first_manifest = run_toml_root / "toml_0.2.14_0" / "manifest.json"
    second_manifest = run_toml_root / "toml_0.2.14_1000" / "manifest.json"
    ignored_manifest = run_toml_root / "manifest.json"
    first_manifest.parent.mkdir(parents=True)
    second_manifest.parent.mkdir(parents=True)
    ignored_manifest.parent.mkdir(parents=True, exist_ok=True)
    first_manifest.write_text("[]", encoding="utf-8")
    second_manifest.write_text("[]", encoding="utf-8")
    ignored_manifest.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(multi_build_script, "build_from_manifest_path", _fake_build)
    monkeypatch.setattr(multi_build_script, "cwd", tmp_path)
    monkeypatch.setattr(multi_build_script, "RUN_TOML_ROOT", run_toml_root)

    targets = multi_build_script.discover_build_targets(run_toml_root)
    result = multi_build_script.build_all_targets(targets)

    assert calls == [
        (first_manifest, tmp_path / "run" / "aedt" / "aedt_0.2.14_0"),
        (second_manifest, tmp_path / "run" / "aedt" / "aedt_0.2.14_1000"),
    ]
    assert result == [[True], [True]]


def test_multi_build_skips_invalid_batch_dir_and_fails_when_none_found(tmp_path: Path) -> None:
    multi_build_script = _load_script("multi_build")
    run_toml_root = tmp_path / "run" / "toml"
    invalid_manifest = run_toml_root / "random_dir" / "manifest.json"
    invalid_manifest.parent.mkdir(parents=True)
    invalid_manifest.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="No batch manifests found"):
        multi_build_script.discover_build_targets(run_toml_root)


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

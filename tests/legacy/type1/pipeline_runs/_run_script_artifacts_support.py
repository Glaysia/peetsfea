from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Callable, cast

import pytest

import peetsfea.legacy.type1.pipeline.run_batch as run_batch
from peetsfea.legacy.type1.pipeline.run_batch import (
    SampleManifestEntry,
    build_aedt_from_manifest_entry,
    build_aedt_from_manifest_entry_with_options,
    generate_sample_artifact_for_seed,
)
from peetsfea.legacy.type1.pipeline.selection.uniform_seedset import generate_eager_uniform_feasible_seed_points
from peetsfea.spec.loader import load_toml_bytes, require_table
from peetsfea.types.manifest import ResolvedPcbInstance, RunResult
from tests.fixtures.legacy.type1_spec import write_type1_toml


def _load_script(name: str) -> ModuleType:
    for module_name in (
        "entry",
        "entry.sample",
        "entry.build",
        "entry.sample_build",
        "entry.build_one",
        "entry.sample_one_build",
        "entry.multi_sample",
        "entry.multi_build",
    ):
        sys.modules.pop(module_name, None)
    module_path = Path(__file__).resolve().parents[4] / "entry" / "legacy" / "type1" / f"{name}.py"
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
    write_type1_toml(run_root / "legacy_type1.toml")

    entries = sample_script.generate_sample_manifest(
        seed_start=0,
        seed_end=100,
        target_count=3,
        source_toml_path=run_root / "legacy_type1.toml",
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
            spec_path=run_root / "legacy_type1.toml",
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


def test_write_resolved_toml_canonicalizes_fixed_topology_pcbs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_toml_path = tmp_path / "type1.toml"
    write_type1_toml(source_toml_path)
    source_bytes = source_toml_path.read_bytes()
    source_spec, _ = load_toml_bytes(source_toml_path)
    monkeypatch.setattr(run_batch, "freeze_sampled_ranges_only", lambda _source, _repro: source_spec)

    result = cast(
        RunResult,
        {
            "manifest": {
                "selected_pcbs": [
                    cast(
                        ResolvedPcbInstance,
                        {
                            "id": "tx_main_0",
                            "role": "tx",
                            "position": (0.0, 0.0, 0.0),
                            "rotation_deg": 0.0,
                            "present": True,
                            "z_mode": "absolute",
                            "z_relative_base_id": None,
                            "z_delta_path": None,
                            "mounts": [
                                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
                                {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
                            ],
                        },
                    ),
                    cast(
                        ResolvedPcbInstance,
                        {
                            "id": "tx_main_1",
                            "role": "tx",
                            "position": (0.0, 0.0, 3.0),
                            "rotation_deg": 0.0,
                            "present": True,
                            "z_mode": "relative_to_pcb",
                            "z_relative_base_id": "tx_main_0",
                            "z_delta_path": "pcb_spacing.tx_main_1_z_from_tx_main_0_mm",
                            "mounts": [],
                        },
                    ),
                ]
            },
            "repro_snapshot": {"toml_bytes": source_bytes},
        },
    )

    output_path = run_batch.write_resolved_toml(
        source_toml_path=source_toml_path,
        output_dir=tmp_path / "resolved",
        design_id="demo",
        result=result,
    )

    spec, _ = load_toml_bytes(output_path)
    raw_pcbs = spec["pcbs"]
    assert isinstance(raw_pcbs, list)
    tx_main_1 = next(pcb for pcb in raw_pcbs if isinstance(pcb, dict) and pcb.get("id") == "tx_main_1")
    tx_main_0 = next(pcb for pcb in raw_pcbs if isinstance(pcb, dict) and pcb.get("id") == "tx_main_0")
    assert tx_main_0["mounts"] == [
        {"kind": "tx_dd", "selector_mode": "index", "selector_index": 0},
        {"kind": "tx_dd", "selector_mode": "index", "selector_index": 1},
    ]
    assert tx_main_1["mounts"] == []


def test_sample_script_debug_constants_disable_parallel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PEETSFEA_DEBUG", "1")
    sample_script = _load_script("sample")

    assert sample_script.IS_DEBUG is True
    assert sample_script.SAMPLE_PARALLEL is False
    assert sample_script.SAMPLE_WORKER_COUNT == 1
    assert sample_script.SAMPLE_TOTAL_TOML_COUNT == 20
    assert sample_script.SAMPLE_BATCH_TOML_COUNT == 10
    assert sample_script.SAMPLE_BATCH_SEED_SPAN == 32
    assert sample_script.SAMPLE_BATCH_COUNT == 2


def test_sample_script_iterates_windowed_batch_profiles() -> None:
    sample_script = _load_script("sample")

    profiles = sample_script.iter_sample_batch_profiles(
        total_toml_count=200,
        batch_toml_count=100,
        first_seed_start=0,
        batch_seed_span=500,
    )

    assert profiles == (
        sample_script.SampleBatchProfile(seed_start=0, seed_end=500, target_count=100),
        sample_script.SampleBatchProfile(seed_start=500, seed_end=1000, target_count=100),
    )


def test_sample_script_partial_last_batch_uses_remaining_total() -> None:
    sample_script = _load_script("sample")

    profiles = sample_script.iter_sample_batch_profiles(
        total_toml_count=250,
        batch_toml_count=100,
        first_seed_start=0,
        batch_seed_span=500,
    )

    assert profiles[-1] == sample_script.SampleBatchProfile(seed_start=1000, seed_end=1500, target_count=50)


def test_sample_script_parallel_artifact_generation_preserves_seed_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PEETSFEA_DEBUG", raising=False)
    sample_script = _load_script("sample")
    workers: list[int] = []
    captured_entries: list[list[dict[str, object]]] = []

    class _FakeProcessPoolExecutor:
        def __init__(self, *, max_workers: int) -> None:
            workers.append(max_workers)

        def __enter__(self) -> "_FakeProcessPoolExecutor":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

        def map(
            self,
            fn: Callable[[tuple[int, Path, Path, Path, str]], dict[str, object] | None],
            values: list[tuple[int, Path, Path, Path, str]],
        ) -> list[dict[str, object] | None]:
            return [fn(value) for value in values]

    def _fake_generate_sample_artifact_for_seed(
        *,
        source_toml_path: Path,
        output_dir: Path,
        ansys_run_dir: Path,
        ansys_executable_path: str,
        seed: int,
    ) -> dict[str, object]:
        return {
            "design_id": f"{seed:06d}_dead_cafe_0",
            "seed": seed,
            "retry_attempt": 0,
            "toml_path": str((output_dir / f"{seed}.toml").resolve()),
            "source_toml_path": str(source_toml_path.resolve()),
            "design_unique_hash": "dead",
            "toml_space_hash": "cafe",
            "toml_hash": "a" * 64,
        }

    def _fake_write_sample_manifest(entries: list[dict[str, object]], manifest_path: Path) -> None:
        captured_entries.append(entries)

    monkeypatch.setattr(
        sample_script,
        "generate_eager_uniform_feasible_seed_points",
        lambda **_: [SimpleNamespace(seed=17), SimpleNamespace(seed=23)],
    )
    monkeypatch.setattr(sample_script, "generate_sample_artifact_for_seed", _fake_generate_sample_artifact_for_seed)
    monkeypatch.setattr(sample_script, "write_sample_manifest", _fake_write_sample_manifest)
    monkeypatch.setattr(sample_script, "ProcessPoolExecutor", _FakeProcessPoolExecutor)

    result = sample_script.generate_sample_manifest(
        seed_start=0,
        seed_end=100,
        target_count=2,
        parallel=True,
        max_workers=4,
    )

    assert workers == [4]
    assert [entry["seed"] for entry in result] == [17, 23]
    assert captured_entries == [result]


def test_sample_script_raises_instead_of_skipping_failed_seed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sample_script = _load_script("sample")
    manifest_path = tmp_path / "toml" / "manifest.json"
    monkeypatch.setattr(
        sample_script,
        "generate_eager_uniform_feasible_seed_points",
        lambda **_: [SimpleNamespace(seed=17)],
    )

    def _failing_generate_sample_artifact_for_seed(**_: object) -> dict[str, object]:
        raise RuntimeError("seed generation failed")

    monkeypatch.setattr(sample_script, "generate_sample_artifact_for_seed", _failing_generate_sample_artifact_for_seed)

    with pytest.raises(RuntimeError, match="seed generation failed"):
        sample_script.generate_sample_manifest(
            seed_start=0,
            seed_end=100,
            target_count=1,
            manifest_path=manifest_path,
            output_dir=tmp_path / "toml",
            ansys_run_dir=tmp_path / "aedt",
        )

    assert manifest_path.exists() is False


def test_sample_script_parallel_batches_use_process_pool_and_disable_nested_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PEETSFEA_DEBUG", raising=False)
    sample_script = _load_script("sample")
    calls: list[tuple[int, int, int, bool, int]] = []
    workers: list[int] = []

    class _FakeProcessPoolExecutor:
        def __init__(self, *, max_workers: int) -> None:
            workers.append(max_workers)

        def __enter__(self) -> "_FakeProcessPoolExecutor":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

        def map(
            self,
            fn: Callable[[tuple[object, Path, str, Path]], list[dict[str, object]]],
            values: list[tuple[object, Path, str, Path]],
        ) -> list[list[dict[str, object]]]:
            return [fn(value) for value in values]

    def _fake_generate_batch_manifest_task(
        task: tuple[object, Path, str, Path],
    ) -> list[dict[str, object]]:
        profile, source_toml_path, ansys_executable_path, workspace_root = task
        assert source_toml_path == sample_script.SOURCE_TOML_PATH
        assert ansys_executable_path == sample_script.ANSYS_EXECUTABLE_PATH
        assert workspace_root == sample_script.cwd
        seed_start = getattr(profile, "seed_start")
        seed_end = getattr(profile, "seed_end")
        target_count = getattr(profile, "target_count")
        calls.append((seed_start, seed_end, target_count, False, 1))
        return [{"seed": seed_start}]

    profiles = (
        sample_script.SampleBatchProfile(seed_start=0, seed_end=500, target_count=100),
        sample_script.SampleBatchProfile(seed_start=500, seed_end=1000, target_count=100),
    )
    monkeypatch.setattr(sample_script, "ProcessPoolExecutor", _FakeProcessPoolExecutor)
    monkeypatch.setattr(sample_script, "_generate_batch_manifest_task", _fake_generate_batch_manifest_task)

    result = sample_script.generate_all_sample_manifests(
        profiles,
        parallel=True,
        max_workers=8,
    )

    assert workers == [2]
    assert calls == [
        (0, 500, 100, False, 1),
        (500, 1000, 100, False, 1),
    ]
    assert result == [[{"seed": 0}], [{"seed": 500}]]


def test_generate_batch_manifest_disables_nested_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    sample_script = _load_script("sample")
    calls: list[dict[str, object]] = []

    def _fake_generate_sample_manifest(**kwargs: object) -> list[dict[str, object]]:
        calls.append(kwargs)
        return [{"seed": 11}]

    monkeypatch.setattr(sample_script, "generate_sample_manifest", _fake_generate_sample_manifest)

    result = sample_script._generate_batch_manifest(
        sample_script.SampleBatchProfile(seed_start=0, seed_end=500, target_count=100),
        source_toml_path=sample_script.SOURCE_TOML_PATH,
        ansys_executable_path=sample_script.ANSYS_EXECUTABLE_PATH,
        workspace_root=sample_script.cwd,
    )

    assert result == [{"seed": 11}]
    assert calls == [
        {
            "seed_start": 0,
            "seed_end": 500,
            "target_count": 100,
            "max_attempts": sample_script.SAMPLE_MAX_ATTEMPTS,
            "source_toml_path": sample_script.SOURCE_TOML_PATH,
            "ansys_executable_path": sample_script.ANSYS_EXECUTABLE_PATH,
            "output_dir": sample_script.sample_output_dir_for_seed_start(0, workspace_root=sample_script.cwd),
            "manifest_path": sample_script.sample_manifest_path_for_seed_start(0, workspace_root=sample_script.cwd),
            "ansys_run_dir": sample_script.sample_ansys_run_dir_for_seed_start(0, workspace_root=sample_script.cwd),
            "workspace_root": sample_script.cwd,
            "parallel": False,
            "max_workers": 1,
        }
    ]


def test_build_script_defaults_follow_first_batch_seed_window() -> None:
    build_script = _load_script("build")
    first_profile = build_script.sample.iter_sample_batch_profiles()[0]

    assert build_script.DEFAULT_SAMPLE_MANIFEST_PATH == build_script.sample.sample_manifest_path_for_seed_start(
        first_profile.seed_start,
        workspace_root=build_script.cwd,
    )
    assert build_script.DEFAULT_ANSYS_RUN_DIR == build_script.sample.sample_ansys_run_dir_for_seed_start(
        first_profile.seed_start,
        workspace_root=build_script.cwd,
    )


def test_build_script_iterates_default_build_targets_from_sample_profiles(monkeypatch: pytest.MonkeyPatch) -> None:
    build_script = _load_script("build")
    monkeypatch.setattr(
        build_script.sample,
        "iter_sample_batch_profiles",
        lambda: (
            build_script.sample.SampleBatchProfile(seed_start=0, seed_end=500, target_count=100),
            build_script.sample.SampleBatchProfile(seed_start=500, seed_end=1000, target_count=100),
        ),
    )

    targets = build_script.iter_default_build_targets(workspace_root=build_script.cwd)

    assert targets == (
        build_script.BuildTarget(
            manifest_path=build_script.cwd / "run" / "toml" / f"toml_{build_script.sample.__version__}_0" / "manifest.json",
            ansys_run_dir=build_script.cwd / "run" / "aedt" / f"aedt_{build_script.sample.__version__}_0",
        ),
        build_script.BuildTarget(
            manifest_path=build_script.cwd / "run" / "toml" / f"toml_{build_script.sample.__version__}_500" / "manifest.json",
            ansys_run_dir=build_script.cwd / "run" / "aedt" / f"aedt_{build_script.sample.__version__}_500",
        ),
    )


def test_build_debug_processes_full_manifest_sequentially(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PEETSFEA_DEBUG", "1")
    build_script = _load_script("build")
    source_toml_path = tmp_path / "source.toml"
    source_toml_path.write_text("spec_version = \"0.2.22\"\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    entries = [
        _make_manifest_entry(design_id="000001_dead_cafe_0", toml_path=tmp_path / "a.toml", source_toml_path=source_toml_path),
        _make_manifest_entry(design_id="000002_dead_cafe_0", toml_path=tmp_path / "b.toml", source_toml_path=source_toml_path),
    ]
    manifest_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    calls: list[tuple[str, bool, bool]] = []

    def _fake_build(
        entry: SampleManifestEntry,
        *,
        ansys_run_dir: Path,
        ansys_executable_path: str,
        non_graphical: bool,
        close_on_exit: bool,
    ) -> bool:
        calls.append((entry["toml_path"], non_graphical, close_on_exit))
        return True

    monkeypatch.setattr(build_script, "build_aedt_from_manifest_entry_with_options", _fake_build)

    result = build_script.build_from_manifest_path(manifest_path, ansys_run_dir=tmp_path / "aedt")

    assert result == [True, True]
    assert build_script.BUILD_PARALLEL is False
    assert build_script.BUILD_WORKER_COUNT == 1
    assert calls == [
        (entries[0]["toml_path"], False, False),
        (entries[1]["toml_path"], False, False),
    ]


def test_build_non_debug_uses_process_pool_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PEETSFEA_DEBUG", raising=False)
    build_script = _load_script("build")
    source_toml_path = tmp_path / "source.toml"
    source_toml_path.write_text("spec_version = \"0.2.22\"\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    entries = [
        _make_manifest_entry(design_id="000001_dead_cafe_0", toml_path=tmp_path / "a.toml", source_toml_path=source_toml_path),
        _make_manifest_entry(design_id="000002_dead_cafe_0", toml_path=tmp_path / "b.toml", source_toml_path=source_toml_path),
    ]
    manifest_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    calls: list[str] = []
    workers: list[int] = []

    def _fake_build(
        entry: SampleManifestEntry,
        *,
        ansys_run_dir: Path,
        ansys_executable_path: str,
        non_graphical: bool,
        close_on_exit: bool,
    ) -> bool:
        assert non_graphical is True
        assert close_on_exit is True
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
            fn: Callable[[tuple[SampleManifestEntry, Path, object]], bool],
            values: list[tuple[SampleManifestEntry, Path, object]],
        ) -> list[bool]:
            return [fn(value) for value in values]

    monkeypatch.setattr(build_script, "build_aedt_from_manifest_entry_with_options", _fake_build)
    monkeypatch.setattr(build_script, "ProcessPoolExecutor", _FakeProcessPoolExecutor)
    monkeypatch.delenv("PEETSFEA_DEBUG", raising=False)

    result = build_script.build_from_manifest_path(manifest_path, ansys_run_dir=tmp_path / "aedt")

    assert result == [True, True]
    assert workers == [build_script.BUILD_WORKER_COUNT]
    assert calls == [entries[0]["toml_path"], entries[1]["toml_path"]]


def test_build_entries_forces_sequential_gui_visible_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    build_script = _load_script("build")
    entries = [
        _make_manifest_entry(design_id="000001_dead_cafe_0", toml_path=tmp_path / "a.toml", source_toml_path=tmp_path / "source.toml"),
        _make_manifest_entry(design_id="000002_dead_cafe_0", toml_path=tmp_path / "b.toml", source_toml_path=tmp_path / "source.toml"),
    ]
    calls: list[tuple[str, bool, bool]] = []
    process_pool_used = False

    def _fake_build(
        entry: SampleManifestEntry,
        *,
        ansys_run_dir: Path,
        ansys_executable_path: str,
        non_graphical: bool,
        close_on_exit: bool,
    ) -> bool:
        calls.append((entry["toml_path"], non_graphical, close_on_exit))
        return True

    class _UnexpectedProcessPoolExecutor:
        def __init__(self, *, max_workers: int) -> None:
            nonlocal process_pool_used
            process_pool_used = True

        def __enter__(self) -> "_UnexpectedProcessPoolExecutor":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

        def map(self, fn: object, values: object) -> list[bool]:
            raise AssertionError("GUI-visible build must stay sequential")

    monkeypatch.setattr(build_script, "build_aedt_from_manifest_entry_with_options", _fake_build)
    monkeypatch.setattr(build_script, "ProcessPoolExecutor", _UnexpectedProcessPoolExecutor)

    result = build_script.build_entries(
        entries,
        ansys_run_dir=tmp_path / "aedt",
        runtime=build_script.GUI_VISIBLE_BUILD_RUNTIME,
        parallel=True,
    )

    assert result == [True, True]
    assert process_pool_used is False
    assert calls == [
        (entries[0]["toml_path"], False, True),
        (entries[1]["toml_path"], False, True),
    ]


def test_build_entries_continue_on_error_when_stop_on_error_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    build_script = _load_script("build")
    entries = [
        _make_manifest_entry(design_id="000001_dead_cafe_0", toml_path=tmp_path / "a.toml", source_toml_path=tmp_path / "source.toml"),
        _make_manifest_entry(design_id="000002_beef_cafe_0", toml_path=tmp_path / "b.toml", source_toml_path=tmp_path / "source.toml"),
    ]
    calls: list[str] = []

    def _fake_build(
        entry: dict[str, object],
        *,
        ansys_run_dir: Path,
        runtime: object,
    ) -> bool:
        calls.append(str(entry["design_id"]))
        if str(entry["design_id"]) == "000001_dead_cafe_0":
            raise RuntimeError("builder failed")
        return True

    monkeypatch.setattr(build_script, "_build_entry", _fake_build)

    result = build_script.build_entries(
        entries,
        ansys_run_dir=tmp_path / "aedt",
        stop_on_error=False,
        parallel=False,
    )

    assert result == [False, True]
    assert calls == ["000001_dead_cafe_0", "000002_beef_cafe_0"]


def test_build_all_targets_fails_on_missing_manifest_and_stops_immediately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_script = _load_script("build")
    manifest1 = tmp_path / "run" / "toml" / "toml_0.2.22_0" / "manifest.json"
    manifest2 = tmp_path / "run" / "toml" / "toml_0.2.22_500" / "manifest.json"
    manifest1.parent.mkdir(parents=True)
    manifest1.write_text("[]", encoding="utf-8")
    calls: list[tuple[Path, Path, object | None, bool | None, int | None, bool]] = []

    def _fake_build_from_manifest_path(
        manifest_path: Path,
        *,
        ansys_run_dir: Path,
        runtime: object | None = None,
        parallel: bool | None = None,
        max_workers: int | None = None,
        stop_on_error: bool = True,
    ) -> list[bool]:
        calls.append((manifest_path, ansys_run_dir, runtime, parallel, max_workers, stop_on_error))
        return [True]

    targets = (
        build_script.BuildTarget(manifest_path=manifest1, ansys_run_dir=tmp_path / "run" / "aedt" / "aedt_0.2.22_0"),
        build_script.BuildTarget(manifest_path=manifest2, ansys_run_dir=tmp_path / "run" / "aedt" / "aedt_0.2.22_500"),
    )
    monkeypatch.setattr(build_script, "build_from_manifest_path", _fake_build_from_manifest_path)

    with pytest.raises(FileNotFoundError, match=str(manifest2)):
        build_script.build_all_targets(targets)

    assert calls == [
        (manifest1, tmp_path / "run" / "aedt" / "aedt_0.2.22_0", None, None, None, True),
    ]


def test_build_all_targets_fails_when_all_manifests_are_missing(tmp_path: Path) -> None:
    build_script = _load_script("build")
    targets = (
        build_script.BuildTarget(
            manifest_path=tmp_path / "run" / "toml" / "toml_0.2.22_0" / "manifest.json",
            ansys_run_dir=tmp_path / "run" / "aedt" / "aedt_0.2.22_0",
        ),
    )

    with pytest.raises(FileNotFoundError, match="Missing batch manifest"):
        build_script.build_all_targets(targets)


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

    with pytest.raises(RuntimeError, match="builder failed"):
        build_aedt_from_manifest_entry(
            entry=entry,
            ansys_run_dir=run_root / "aedt",
            ansys_executable_path="/opt/ansys_inc/v252/AnsysEM",
            is_debug=False,
        )

    aedt_dir = run_root / "aedt"
    assert list(aedt_dir.glob("*.aedt")) == []
    assert list(aedt_dir.glob("*.aedtresults")) == []



def test_build_all_targets_with_options_forwards_runtime_controls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_script = _load_script("build")
    manifest = tmp_path / "run" / "toml" / "toml_0.2.22_0" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("[]", encoding="utf-8")
    calls: list[tuple[Path, Path, object | None, bool | None, int | None, bool]] = []

    def _fake_build_from_manifest_path(
        manifest_path: Path,
        *,
        ansys_run_dir: Path,
        runtime: object | None = None,
        parallel: bool | None = None,
        max_workers: int | None = None,
        stop_on_error: bool = True,
    ) -> list[bool]:
        calls.append((manifest_path, ansys_run_dir, runtime, parallel, max_workers, stop_on_error))
        return [True]

    targets = (
        build_script.BuildTarget(
            manifest_path=manifest,
            ansys_run_dir=tmp_path / "run" / "aedt" / "aedt_0.2.22_0",
        ),
    )
    monkeypatch.setattr(build_script, "build_from_manifest_path", _fake_build_from_manifest_path)

    result = build_script.build_all_targets_with_options(
        targets,
        runtime=build_script.GUI_VISIBLE_BUILD_RUNTIME,
        parallel=False,
        max_workers=1,
    )

    assert result == [[True]]
    assert calls == [
        (
            manifest,
            tmp_path / "run" / "aedt" / "aedt_0.2.22_0",
            build_script.GUI_VISIBLE_BUILD_RUNTIME,
            False,
            1,
            True,
        )
    ]


def test_sample_build_reuses_build_target_runner_and_skips_sampling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PEETSFEA_DEBUG", "1")
    monkeypatch.delenv("PEETSFEA_SAMPLE_BUILD_NON_GRAPHICAL", raising=False)
    sample_build_script = _load_script("sample_build")
    calls: list[tuple[object | None, bool | None, int | None, bool | None]] = []

    def _fake_build_all_targets_with_options(
        targets: object | None = None,
        *,
        runtime: object,
        parallel: bool,
        max_workers: int,
        stop_on_error: bool = True,
    ) -> list[list[bool]]:
        calls.append((runtime, parallel, max_workers, stop_on_error))
        assert targets is None
        return [[True]]

    monkeypatch.setattr(
        sample_build_script.build,
        "build_all_targets_with_options",
        _fake_build_all_targets_with_options,
    )

    result = sample_build_script.main()

    assert result == [[True]]
    assert calls == [
        (
            sample_build_script.build.GUI_VISIBLE_BUILD_RUNTIME,
            False,
            sample_build_script.SAMPLE_BUILD_WORKER_COUNT,
            True,
        )
    ]


def test_build_all_targets_with_options_forwards_stop_on_error_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_script = _load_script("build")
    manifest = tmp_path / "run" / "toml" / "toml_0.2.22_0" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("[]", encoding="utf-8")
    targets = (
        build_script.BuildTarget(
            manifest_path=manifest,
            ansys_run_dir=tmp_path / "run" / "aedt" / "aedt_0.2.22_0",
        ),
    )
    calls: list[bool] = []

    def _fake_build_from_manifest_path(
        manifest_path: Path,
        *,
        ansys_run_dir: Path,
        runtime: object | None = None,
        parallel: bool | None = None,
        max_workers: int | None = None,
        stop_on_error: bool = True,
    ) -> list[bool]:
        calls.append(stop_on_error)
        return [False, True]

    monkeypatch.setattr(build_script, "build_from_manifest_path", _fake_build_from_manifest_path)

    result = build_script.build_all_targets_with_options(targets, stop_on_error=False)

    assert result == [[False, True]]
    assert calls == [False]


def test_sample_build_can_force_non_graphical_runtime_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PEETSFEA_DEBUG", "1")
    monkeypatch.setenv("PEETSFEA_SAMPLE_BUILD_NON_GRAPHICAL", "1")
    sample_build_script = _load_script("sample_build")
    calls: list[tuple[object | None, bool | None, int | None, bool | None]] = []

    def _fake_build_all_targets_with_options(
        targets: object | None = None,
        *,
        runtime: object,
        parallel: bool,
        max_workers: int,
        stop_on_error: bool = True,
    ) -> list[list[bool]]:
        calls.append((runtime, parallel, max_workers, stop_on_error))
        assert targets is None
        return [[True]]

    monkeypatch.setattr(
        sample_build_script.build,
        "build_all_targets_with_options",
        _fake_build_all_targets_with_options,
    )

    result = sample_build_script.main()

    assert result == [[True]]
    assert calls == [
        (
            sample_build_script.NON_GUI_BUILD_RUNTIME,
            False,
            sample_build_script.SAMPLE_BUILD_WORKER_COUNT,
            True,
        )
    ]


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

    with pytest.raises(ValueError, match=r"Build input TOML must freeze every sampling owner"):
        build_aedt_from_manifest_entry(
            entry=entry,
            ansys_run_dir=tmp_path / "aedt",
            ansys_executable_path="/opt/ansys_inc/v252/AnsysEM",
            is_debug=False,
        )


def test_build_helper_preserves_original_geometry_cause(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    source_toml_path = run_root / "type1.toml"
    write_type1_toml(source_toml_path)
    entry = generate_sample_artifact_for_seed(
        source_toml_path=source_toml_path,
        output_dir=run_root / "toml",
        ansys_run_dir=run_root / "aedt",
        ansys_executable_path="/opt/ansys_inc/v252/AnsysEM",
        seed=17,
    )

    monkeypatch.setattr(
        run_batch,
        "build_square_spiral_from_manifest",
        lambda manifest: (_ for _ in ()).throw(ValueError("semantic landing missing")),
    )

    with pytest.raises(ValueError, match="semantic landing missing"):
        build_aedt_from_manifest_entry_with_options(
            entry=entry,
            ansys_run_dir=run_root / "aedt",
            ansys_executable_path="/opt/ansys_inc/v252/AnsysEM",
            non_graphical=True,
            close_on_exit=True,
        )


def test_write_resolved_toml_rejects_pcb_invariant_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_toml_path = tmp_path / "type1.toml"
    write_type1_toml(source_toml_path)
    source_bytes = source_toml_path.read_bytes()
    source_spec, _ = load_toml_bytes(source_toml_path)
    monkeypatch.setattr(run_batch, "freeze_sampled_ranges_only", lambda _source, _repro: source_spec)

    result = cast(
        RunResult,
        {
            "manifest": {
                "selected_pcbs": [
                    cast(
                        ResolvedPcbInstance,
                        {
                            "id": "tx_main_0",
                            "role": "rx",
                            "position": (0.0, 0.0, 0.0),
                            "rotation_deg": 0.0,
                            "present": True,
                            "z_mode": "absolute",
                            "z_relative_base_id": None,
                            "z_delta_path": None,
                            "mounts": [],
                        },
                    ),
                ]
            },
            "repro_snapshot": {"toml_bytes": source_bytes},
        },
    )

    with pytest.raises(ValueError, match="role mismatch"):
        run_batch.write_resolved_toml(
            source_toml_path=source_toml_path,
            output_dir=tmp_path / "resolved",
            design_id="demo",
            result=result,
        )

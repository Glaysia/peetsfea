from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path
from typing import TypedDict

from peetsfea.legacy.type1.backend.pyaedt.geometry.build import build_square_spiral_from_manifest
from peetsfea.console_log import info
from peetsfea.legacy.type1.pipeline.run_design import RunConfig, run
from peetsfea.legacy.type1.pipeline.selection.selection_snapshots import freeze_sampled_ranges_only, require_frozen_sampling_spec, toml_dumps
from peetsfea.spec.loader import TOMLTable, TOMLValue, load_toml_bytes
from peetsfea.types.manifest import Manifest, ResolvedPcbInstance, RunResult


class SampleManifestEntry(TypedDict):
    design_id: str
    seed: int
    retry_attempt: int
    toml_path: str
    source_toml_path: str
    design_unique_hash: str
    toml_space_hash: str
    toml_hash: str


def _safe_remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
        return
    if path.exists():
        path.unlink()


def _cleanup_failed_design_files(
    *,
    run_dir: Path,
    design_id: str,
    artifact_paths: dict[str, Path],
) -> None:
    targets: list[Path] = [
        run_dir / f"{design_id}.aedt",
        run_dir / f"{design_id}.aedt.lock",
        run_dir / f"{design_id}.aedtresults",
    ]
    targets.extend(artifact_paths.values())
    for target in targets:
        _safe_remove(target)


def cleanup_aedtresults(run_dir: Path, design_id: str) -> None:
    _safe_remove(run_dir / f"{design_id}.aedtresults")


def write_resolved_toml(*, source_toml_path: Path, output_dir: Path, design_id: str, result: RunResult) -> Path:
    spec, _ = load_toml_bytes(source_toml_path)
    repro_spec = tomllib.loads(result["repro_snapshot"]["toml_bytes"].decode("utf-8"))
    resolved_spec = freeze_sampled_ranges_only(spec, repro_spec)
    _canonicalize_resolved_pcbs(resolved_spec=resolved_spec, selected_pcbs=result["manifest"]["selected_pcbs"])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{design_id}.toml"
    output_path.write_text(toml_dumps(resolved_spec), encoding="utf-8")
    return output_path


def _present_range_from_bool(present: bool) -> list[TOMLValue]:
    value = 1 if present else 0
    return [True, value, value, 1]


def _mount_table_from_selected_pcb(pcb: ResolvedPcbInstance) -> list[TOMLValue]:
    tables: list[TOMLValue] = []
    for mount in pcb["mounts"]:
        table: TOMLTable = {
            "kind": mount["kind"],
            "selector_mode": mount["selector_mode"],
        }
        if mount["selector_mode"] == "index":
            selector_index = mount["selector_index"]
            if not isinstance(selector_index, int):
                raise ValueError("selected pcb mount selector_index must be int when selector_mode='index'")
            table["selector_index"] = selector_index
        tables.append(table)
    return tables


def _assert_resolved_pcb_invariants_match(
    *,
    raw_pcb: TOMLTable,
    selected_pcb: ResolvedPcbInstance,
    idx: int,
) -> None:
    assert "role" in raw_pcb, f"resolved spec pcbs[{idx}] must contain role before replay export"
    assert "rotation_deg" in raw_pcb, f"resolved spec pcbs[{idx}] must contain rotation_deg before replay export"
    assert "z_mode" in raw_pcb, f"resolved spec pcbs[{idx}] must contain z_mode before replay export"

    raw_role = raw_pcb["role"]
    raw_rotation_deg = raw_pcb["rotation_deg"]
    raw_z_mode = raw_pcb["z_mode"]
    raw_z_relative_base_id: str | None
    raw_z_delta_path: str | None
    if raw_z_mode == "absolute":
        if "z_relative_base_id" in raw_pcb:
            raise ValueError(f"resolved spec pcbs[{idx}] must not define z_relative_base_id when z_mode='absolute'")
        if "z_delta_path" in raw_pcb:
            raise ValueError(f"resolved spec pcbs[{idx}] must not define z_delta_path when z_mode='absolute'")
        raw_z_relative_base_id = None
        raw_z_delta_path = None
    else:
        assert "z_relative_base_id" in raw_pcb, (
            f"resolved spec pcbs[{idx}] must contain z_relative_base_id when z_mode='relative_to_pcb'"
        )
        assert "z_delta_path" in raw_pcb, f"resolved spec pcbs[{idx}] must contain z_delta_path when z_mode='relative_to_pcb'"
        raw_z_relative_base_id_value = raw_pcb["z_relative_base_id"]
        raw_z_delta_path_value = raw_pcb["z_delta_path"]
        if not isinstance(raw_z_relative_base_id_value, str) or raw_z_relative_base_id_value == "":
            raise ValueError(f"resolved spec pcbs[{idx}].z_relative_base_id must be non-empty string")
        if not isinstance(raw_z_delta_path_value, str) or raw_z_delta_path_value == "":
            raise ValueError(f"resolved spec pcbs[{idx}].z_delta_path must be non-empty string")
        raw_z_relative_base_id = raw_z_relative_base_id_value
        raw_z_delta_path = raw_z_delta_path_value
    if isinstance(raw_rotation_deg, bool) or not isinstance(raw_rotation_deg, (int, float)):
        raise ValueError(f"resolved spec pcbs[{idx}].rotation_deg must be numeric before replay export")
    raw_rotation_deg_float = float(raw_rotation_deg)

    if raw_role != selected_pcb["role"]:
        raise ValueError(
            f"resolved spec pcbs[{idx}] role mismatch for id={selected_pcb['id']} "
            f"(raw={raw_role}, selected={selected_pcb['role']})"
        )
    if raw_rotation_deg_float != selected_pcb["rotation_deg"]:
        raise ValueError(
            f"resolved spec pcbs[{idx}] rotation_deg mismatch for id={selected_pcb['id']} "
            f"(raw={raw_rotation_deg_float}, selected={selected_pcb['rotation_deg']})"
        )
    if raw_z_mode != selected_pcb["z_mode"]:
        raise ValueError(
            f"resolved spec pcbs[{idx}] z_mode mismatch for id={selected_pcb['id']} "
            f"(raw={raw_z_mode}, selected={selected_pcb['z_mode']})"
        )
    if raw_z_relative_base_id != selected_pcb["z_relative_base_id"]:
        raise ValueError(
            f"resolved spec pcbs[{idx}] z_relative_base_id mismatch for id={selected_pcb['id']} "
            f"(raw={raw_z_relative_base_id}, selected={selected_pcb['z_relative_base_id']})"
        )
    if raw_z_delta_path != selected_pcb["z_delta_path"]:
        raise ValueError(
            f"resolved spec pcbs[{idx}] z_delta_path mismatch for id={selected_pcb['id']} "
            f"(raw={raw_z_delta_path}, selected={selected_pcb['z_delta_path']})"
        )


def _canonicalize_resolved_pcbs(*, resolved_spec: TOMLTable, selected_pcbs: list[ResolvedPcbInstance]) -> None:
    assert "pcbs" in resolved_spec, "resolved spec must contain pcbs before replay export"
    raw_pcbs = resolved_spec["pcbs"]
    if not isinstance(raw_pcbs, list):
        raise ValueError("resolved spec must contain pcbs list before replay export")
    raw_by_id: dict[str, tuple[int, TOMLTable]] = {}
    for raw_idx, raw_pcb in enumerate(raw_pcbs):
        if not isinstance(raw_pcb, dict):
            raise ValueError(f"resolved spec pcbs[{raw_idx}] must be a table/object")
        assert "id" in raw_pcb, f"resolved spec pcbs[{raw_idx}] must contain id"
        raw_id = raw_pcb["id"]
        if not isinstance(raw_id, str):
            raise ValueError(f"resolved spec pcbs[{raw_idx}].id must be string")
        if raw_id in raw_by_id:
            raise ValueError(f"resolved spec contains duplicate pcb id before replay export: {raw_id}")
        raw_by_id[raw_id] = (raw_idx, raw_pcb)
    selected_by_id: dict[str, ResolvedPcbInstance] = {}
    for selected_idx, selected_pcb in enumerate(selected_pcbs):
        if not isinstance(selected_pcb, dict):
            raise ValueError(f"selected_pcbs[{selected_idx}] must be a table/object before replay export")
        assert "id" in selected_pcb, f"selected_pcbs[{selected_idx}] must contain id before replay export"
        selected_id = selected_pcb["id"]
        if not isinstance(selected_id, str):
            raise ValueError(f"selected_pcbs[{selected_idx}].id must be string before replay export")
        if selected_id in selected_by_id:
            raise ValueError(f"selected_pcbs contains duplicate pcb id before replay export: {selected_id}")
        selected_by_id[selected_id] = selected_pcb
    for selected_id, selected in selected_by_id.items():
        if selected_id not in raw_by_id:
            raise ValueError(f"selected_pcbs references unknown pcb id before replay export: {selected_id}")
        idx, raw_pcb = raw_by_id[selected_id]
        _assert_resolved_pcb_invariants_match(raw_pcb=raw_pcb, selected_pcb=selected, idx=idx)
        raw_pcb["present"] = _present_range_from_bool(bool(selected["present"]))
        raw_pcb["mounts"] = _mount_table_from_selected_pcb(selected)


def generate_sample_artifact_for_seed(
    *,
    source_toml_path: Path,
    output_dir: Path,
    ansys_run_dir: Path,
    ansys_executable_path: str,
    seed: int,
) -> SampleManifestEntry:
    result = run(
        RunConfig(
            ansys_executable_path=ansys_executable_path,
            ansys_run_dir=str(ansys_run_dir),
            toml_path=str(source_toml_path),
            seed=seed,
            backend="hfss",
            non_graphical=True,
            close_on_exit=True,
        )
    )
    manifest = result["manifest"]
    design_id = str(manifest["design_id"])
    resolved_toml_path = write_resolved_toml(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        design_id=design_id,
        result=result,
    )
    return {
        "design_id": design_id,
        "seed": seed,
        "retry_attempt": int(manifest["retry_attempt"]),
        "toml_path": str(resolved_toml_path.resolve()),
        "source_toml_path": str(source_toml_path.resolve()),
        "design_unique_hash": str(manifest["design_unique_hash"]),
        "toml_space_hash": str(manifest["toml_space_hash"]),
        "toml_hash": str(manifest["toml_hash"]),
    }


def _apply_sample_identity(manifest: Manifest, entry: SampleManifestEntry, *, toml_path: Path) -> None:
    manifest["design_id"] = toml_path.stem
    manifest["design_unique_hash"] = entry["design_unique_hash"]
    manifest["toml_space_hash"] = entry["toml_space_hash"]
    manifest["toml_hash"] = entry["toml_hash"]
    manifest["seed"] = entry["seed"]
    manifest["retry_attempt"] = entry["retry_attempt"]
    manifest["retry_count"] = entry["retry_attempt"]
    manifest["inputs"]["toml_path"] = str(toml_path)
    manifest["inputs"]["source_toml_path"] = entry["source_toml_path"]


def build_aedt_from_manifest_entry_with_options(
    *,
    entry: SampleManifestEntry,
    ansys_run_dir: Path,
    ansys_executable_path: str,
    non_graphical: bool,
    close_on_exit: bool,
) -> bool:
    config = RunConfig(
        ansys_executable_path=ansys_executable_path,
        ansys_run_dir=str(ansys_run_dir),
        toml_path=entry["toml_path"],
        seed=entry["seed"],
        backend="hfss",
        non_graphical=non_graphical,
        close_on_exit=close_on_exit,
    )
    run_dir = Path(config.ansys_run_dir)
    result_registry: dict[str, object] = {}
    artifact_paths: dict[str, Path] = {}
    toml_path = Path(entry["toml_path"])
    build_succeeded = False
    try:
        spec, _ = load_toml_bytes(toml_path)
        require_frozen_sampling_spec(spec)
        result = run(config)
        manifest = result["manifest"]
        result_registry["result"] = result
        result_registry["manifest"] = manifest
        _apply_sample_identity(manifest, entry, toml_path=toml_path)
        geometry = build_square_spiral_from_manifest(manifest)
        assert geometry is not False, (
            "build_square_spiral_from_manifest returned False "
            f"(design_id={toml_path.stem}, toml_path={toml_path})"
        )
        result["zip_path"] = None
        info(str(geometry["aedt_path"]))
        build_succeeded = True
        return True
    finally:
        design_id = toml_path.stem
        cleanup_aedtresults(run_dir, design_id)
        if not build_succeeded:
            if "result" in result_registry:
                stored_result = result_registry["result"]
                assert isinstance(stored_result, dict), "run result registry must contain mapping result"
                raw_manifest_path = stored_result["manifest_path"]
                raw_geometry_metadata_path = stored_result["geometry_metadata_path"]
                raw_zip_path = stored_result["zip_path"]
                if isinstance(raw_manifest_path, (str, Path)):
                    artifact_paths["manifest_path"] = Path(raw_manifest_path)
                if isinstance(raw_geometry_metadata_path, (str, Path)):
                    artifact_paths["geometry_metadata_path"] = Path(raw_geometry_metadata_path)
                if isinstance(raw_zip_path, (str, Path)):
                    artifact_paths["zip_path"] = Path(raw_zip_path)
            _cleanup_failed_design_files(run_dir=run_dir, design_id=design_id, artifact_paths=artifact_paths)


def build_aedt_from_manifest_entry(
    *,
    entry: SampleManifestEntry,
    ansys_run_dir: Path,
    ansys_executable_path: str,
    is_debug: bool,
) -> bool:
    return build_aedt_from_manifest_entry_with_options(
        entry=entry,
        ansys_run_dir=ansys_run_dir,
        ansys_executable_path=ansys_executable_path,
        non_graphical=not is_debug,
        close_on_exit=not is_debug,
    )


def write_sample_manifest(entries: list[SampleManifestEntry], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def load_sample_manifest(manifest_path: Path) -> list[SampleManifestEntry]:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("sample manifest must be a JSON array")
    entries: list[SampleManifestEntry] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"sample manifest entry {index} must be an object")
        required_keys = (
            "design_id",
            "seed",
            "retry_attempt",
            "toml_path",
            "source_toml_path",
            "design_unique_hash",
            "toml_space_hash",
            "toml_hash",
        )
        for key in required_keys:
            assert key in item, f"sample manifest entry {index} must contain {key}"
        design_id = item["design_id"]
        seed = item["seed"]
        retry_attempt = item["retry_attempt"]
        toml_path = item["toml_path"]
        source_toml_path = item["source_toml_path"]
        design_unique_hash = item["design_unique_hash"]
        toml_space_hash = item["toml_space_hash"]
        toml_hash = item["toml_hash"]
        if not isinstance(design_id, str) or design_id == "":
            raise ValueError(f"sample manifest entry {index} design_id must be a non-empty string")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError(f"sample manifest entry {index} seed must be int")
        if isinstance(retry_attempt, bool) or not isinstance(retry_attempt, int):
            raise ValueError(f"sample manifest entry {index} retry_attempt must be int")
        if not isinstance(toml_path, str) or toml_path == "":
            raise ValueError(f"sample manifest entry {index} toml_path must be a non-empty string")
        if not isinstance(source_toml_path, str) or source_toml_path == "":
            raise ValueError(f"sample manifest entry {index} source_toml_path must be a non-empty string")
        if not isinstance(design_unique_hash, str) or design_unique_hash == "":
            raise ValueError(f"sample manifest entry {index} design_unique_hash must be a non-empty string")
        if not isinstance(toml_space_hash, str) or toml_space_hash == "":
            raise ValueError(f"sample manifest entry {index} toml_space_hash must be a non-empty string")
        if not isinstance(toml_hash, str) or toml_hash == "":
            raise ValueError(f"sample manifest entry {index} toml_hash must be a non-empty string")
        entries.append(
            {
                "design_id": design_id,
                "seed": seed,
                "retry_attempt": retry_attempt,
                "toml_path": toml_path,
                "source_toml_path": source_toml_path,
                "design_unique_hash": design_unique_hash,
                "toml_space_hash": toml_space_hash,
                "toml_hash": toml_hash,
            }
        )
    return entries

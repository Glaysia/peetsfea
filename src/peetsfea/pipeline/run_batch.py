from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path
from typing import TypedDict

from peetsfea.backend.pyaedt.geometry.build import build_square_spiral_from_manifest
from peetsfea.pipeline.run_design import RunConfig, run
from peetsfea.pipeline.selection_snapshots import freeze_sampled_ranges_only, require_frozen_sampling_spec, toml_dumps
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.types.manifest import Manifest, RunResult


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
        shutil.rmtree(path, ignore_errors=True)
        return
    if path.exists():
        path.unlink(missing_ok=True)


def _cleanup_failed_design_files(
    *,
    run_dir: Path,
    design_id: str | None,
    manifest_path: Path | None,
    geometry_metadata_path: Path | None,
    zip_path: Path | None,
) -> None:
    if design_id is None:
        if manifest_path is not None:
            _safe_remove(manifest_path)
        if geometry_metadata_path is not None:
            _safe_remove(geometry_metadata_path)
        if zip_path is not None:
            _safe_remove(zip_path)
        return
    targets: list[Path] = [
        run_dir / f"{design_id}.aedt",
        run_dir / f"{design_id}.aedt.lock",
        run_dir / f"{design_id}.aedtresults",
    ]
    if manifest_path is not None:
        targets.append(manifest_path)
    if geometry_metadata_path is not None:
        targets.append(geometry_metadata_path)
    if zip_path is not None:
        targets.append(zip_path)
    for target in targets:
        _safe_remove(target)


def cleanup_aedtresults(run_dir: Path, design_id: str | None) -> None:
    if design_id is None:
        return
    _safe_remove(run_dir / f"{design_id}.aedtresults")


def write_resolved_toml(*, source_toml_path: Path, output_dir: Path, design_id: str, result: RunResult) -> Path:
    spec, _ = load_toml_bytes(source_toml_path)
    repro_spec = tomllib.loads(result["repro_snapshot"]["toml_bytes"].decode("utf-8"))
    resolved_spec = freeze_sampled_ranges_only(spec, repro_spec)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{design_id}.toml"
    output_path.write_text(toml_dumps(resolved_spec), encoding="utf-8")
    return output_path


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


def build_aedt_from_manifest_entry(
    *,
    entry: SampleManifestEntry,
    ansys_run_dir: Path,
    ansys_executable_path: str,
    is_debug: bool,
) -> bool:
    config = RunConfig(
        ansys_executable_path=ansys_executable_path,
        ansys_run_dir=str(ansys_run_dir),
        toml_path=entry["toml_path"],
        seed=entry["seed"],
        backend="hfss",
        non_graphical=not is_debug,
        close_on_exit=not is_debug,
    )
    run_dir = Path(config.ansys_run_dir)
    result: RunResult | None = None
    manifest: Manifest | None = None
    toml_path = Path(entry["toml_path"])
    try:
        spec, _ = load_toml_bytes(toml_path)
        require_frozen_sampling_spec(spec)
        result = run(config)
        manifest = result["manifest"]
        _apply_sample_identity(manifest, entry, toml_path=toml_path)
        geometry = build_square_spiral_from_manifest(manifest)
        cleanup_aedtresults(run_dir, toml_path.stem)
        result["zip_path"] = None
        print(geometry["aedt_path"])
        return True
    except Exception as exc:
        design_id = toml_path.stem
        cleanup_aedtresults(run_dir, design_id)
        manifest_path = Path(result["manifest_path"]) if result is not None and result["manifest_path"] is not None else None
        geometry_metadata_path = (
            Path(result["geometry_metadata_path"])
            if result is not None and result["geometry_metadata_path"] is not None
            else None
        )
        zip_path = Path(result["zip_path"]) if result is not None and result["zip_path"] is not None else None
        _cleanup_failed_design_files(
            run_dir=run_dir,
            design_id=design_id,
            manifest_path=manifest_path,
            geometry_metadata_path=geometry_metadata_path,
            zip_path=zip_path,
        )
        print(f"[design_id={design_id}] build failed; cleaned generated files and continue: {exc}")
        return False


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
        design_id = item.get("design_id")
        seed = item.get("seed")
        retry_attempt = item.get("retry_attempt")
        toml_path = item.get("toml_path")
        source_toml_path = item.get("source_toml_path")
        design_unique_hash = item.get("design_unique_hash")
        toml_space_hash = item.get("toml_space_hash")
        toml_hash = item.get("toml_hash")
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

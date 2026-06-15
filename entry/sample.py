from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import TypedDict, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.minimal_step import export_minimal_step_artifacts

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_TOML_PATH = REPO_ROOT / "examples" / "0.3.2_fixed.toml"
OUTPUT_DIR = REPO_ROOT / "run" / "sampled" / "0.3.0"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
SEED = 0


class MinimalManifestEntry(TypedDict):
    design_id: str
    seed: int
    source_toml_path: str
    sampled_toml_path: str
    source_snapshot_path: str
    repro_toml_path: str
    dataset_toml_path: str
    step_path: str
    step_ledger_path: str
    aedt_path: str
    imported_ledger_path: str


class MinimalManifest(TypedDict):
    source_toml_path: str
    output_dir: str
    seed: int
    entries: list[MinimalManifestEntry]


def _design_id(*, source_toml_path: Path, seed: int) -> str:
    digest = hashlib.sha256()
    digest.update(source_toml_path.read_bytes())
    digest.update(str(seed).encode("ascii"))
    return f"minimal_{digest.hexdigest()[:16]}"


def _write_text_snapshot(*, source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def _write_dataset_toml(*, path: Path, design_id: str, seed: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                'schema_id = "peetsfea.minimal_step_two_port.dataset.v1"',
                f'design_id = "{design_id}"',
                f"seed = {seed}",
                "sampled_dimension_count = 0",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_minimal_manifest(*, manifest: MinimalManifest, manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_minimal_manifest(manifest_path: Path) -> MinimalManifest:
    raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw_manifest, dict):
        raise TypeError(f"minimal manifest must be a JSON object: {manifest_path}")
    for key in ("source_toml_path", "output_dir", "seed", "entries"):
        if key not in raw_manifest:
            raise ValueError(f"minimal manifest is missing required key {key!r}: {manifest_path}")
    return cast(MinimalManifest, raw_manifest)


def sample_minimal(
    *,
    source_toml_path: Path = SOURCE_TOML_PATH,
    output_dir: Path = OUTPUT_DIR,
    manifest_path: Path = MANIFEST_PATH,
    seed: int = SEED,
) -> MinimalManifest:
    design_id = _design_id(source_toml_path=source_toml_path, seed=seed)
    design_dir = output_dir / design_id
    sampled_toml_path = design_dir / "sampled.toml"
    source_snapshot_path = design_dir / f"{design_id}.source.toml"
    repro_toml_path = design_dir / f"{design_id}.repro.toml"
    dataset_toml_path = design_dir / f"{design_id}.dataset.toml"
    step_path = design_dir / "minimal_scene.step"
    step_ledger_path = design_dir / "minimal_step_ledger.json"
    aedt_path = design_dir / f"{design_id}.aedt"
    imported_ledger_path = design_dir / "minimal_imported_ledger.json"

    _write_text_snapshot(source=source_toml_path, target=sampled_toml_path)
    _write_text_snapshot(source=source_toml_path, target=source_snapshot_path)
    _write_text_snapshot(source=source_toml_path, target=repro_toml_path)
    _write_dataset_toml(path=dataset_toml_path, design_id=design_id, seed=seed)
    artifacts = export_minimal_step_artifacts(
        source_toml_path=sampled_toml_path,
        output_dir=design_dir,
        seed=seed,
        scene_step_path=step_path,
        ledger_path=step_ledger_path,
    )
    entry: MinimalManifestEntry = {
        "design_id": design_id,
        "seed": seed,
        "source_toml_path": str(source_toml_path),
        "sampled_toml_path": str(sampled_toml_path),
        "source_snapshot_path": str(source_snapshot_path),
        "repro_toml_path": str(repro_toml_path),
        "dataset_toml_path": str(dataset_toml_path),
        "step_path": artifacts["scene_step_path"],
        "step_ledger_path": artifacts["ledger_path"],
        "aedt_path": str(aedt_path),
        "imported_ledger_path": str(imported_ledger_path),
    }
    manifest: MinimalManifest = {
        "source_toml_path": str(source_toml_path),
        "output_dir": str(output_dir),
        "seed": seed,
        "entries": [entry],
    }
    write_minimal_manifest(manifest=manifest, manifest_path=manifest_path)
    return manifest


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE_TOML_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--seed", type=int, default=SEED)
    return parser


def main() -> MinimalManifest:
    args = _build_arg_parser().parse_args()
    manifest = sample_minimal(
        source_toml_path=args.source,
        output_dir=args.output_dir,
        manifest_path=args.manifest,
        seed=args.seed,
    )
    print(f"manifest: {args.manifest}")
    print(f"design_id: {manifest['entries'][0]['design_id']}")
    return manifest


if __name__ == "__main__":
    main()

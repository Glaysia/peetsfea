from __future__ import annotations

from collections.abc import Callable
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from entry.generate_type2_step import export_type2_step_artifacts
from peetsfea.type2_runtime import export_prepared_type2_designs
from peetsfea.type2_sampled import (
    Type2SampleManifestDocument,
    build_type2_sample_manifest_config,
    build_type2_sample_manifest_document,
    generate_sample_manifest_entries,
    prepared_builds_from_manifest,
    write_type2_sample_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_TOML_PATH = REPO_ROOT / "examples" / "type2_sweep.toml"
OUTPUT_DIR = REPO_ROOT / "run" / "sampled" / "type2"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
SEED_FIRST = 0
SEED_N = 1000
SAMPLER_N = 10
STEP_BUILDER_N = 10
AEDT_BUILDER_N = 6

_Exporter = Callable[..., object]


def sample_type2(
    *,
    source_toml_path: Path = SOURCE_TOML_PATH,
    output_dir: Path = OUTPUT_DIR,
    manifest_path: Path = MANIFEST_PATH,
    seed_first: int = SEED_FIRST,
    seed_n: int = SEED_N,
    sampler_n: int = SAMPLER_N,
    step_builder_n: int = STEP_BUILDER_N,
    aedt_builder_n: int = AEDT_BUILDER_N,
    exporter: _Exporter = export_type2_step_artifacts,
) -> Type2SampleManifestDocument:
    config = build_type2_sample_manifest_config(
        source_toml_path=source_toml_path,
        seed_first=seed_first,
        seed_n=seed_n,
        sampler_n=sampler_n,
        step_builder_n=step_builder_n,
        aedt_builder_n=aedt_builder_n,
    )
    entries = generate_sample_manifest_entries(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        seed_start=seed_first,
        count=seed_n,
        jobs=sampler_n,
    )
    document = build_type2_sample_manifest_document(config=config, entries=entries)
    write_type2_sample_manifest(document=document, manifest_path=manifest_path)
    prepared_builds = prepared_builds_from_manifest(manifest_path, selected_design_ids=())
    export_prepared_type2_designs(prepared_builds, jobs=step_builder_n, exporter=exporter)
    return document


def main() -> Type2SampleManifestDocument:
    document = sample_type2()
    print(f"source TOML: {document['config']['source_toml_path']}")
    print(f"output dir: {OUTPUT_DIR}")
    print(f"manifest: {MANIFEST_PATH}")
    print(f"sampled design count: {len(document['entries'])}")
    for entry in document["entries"]:
        print(f"{entry['design_id']}: {entry['step_ledger_path']}")
    return document


if __name__ == "__main__":
    main()

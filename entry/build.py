from __future__ import annotations

from collections.abc import Callable
import sys
from pathlib import Path
from typing import TypedDict

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from entry.sample import MANIFEST_PATH
from peetsfea.backend.pyaedt.type2_step_setup_ready import setup_type2_step_ledger
from peetsfea.type2_runtime import Type2BuiltArtifact, build_prepared_type2_designs
from peetsfea.type2_step_export import export_type2_step_artifacts
from peetsfea.type2_sampled import load_type2_sample_manifest, prepared_builds_from_manifest

_Exporter = Callable[..., object]


class _Type2BuildRunnerResult(TypedDict):
    aedt_path: str
    source_step_ledger_path: str
    imported_ledger_path: str


_Runner = Callable[..., _Type2BuildRunnerResult]

def build_type2(
    *,
    manifest_path: Path = MANIFEST_PATH,
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _Runner = setup_type2_step_ledger,
) -> list[Type2BuiltArtifact]:
    document = load_type2_sample_manifest(manifest_path)
    prepared_builds = prepared_builds_from_manifest(manifest_path, selected_design_ids=())
    return build_prepared_type2_designs(
        prepared_builds,
        jobs=document["config"]["aedt_builder_n"],
        exporter=exporter,
        runner=runner,
    )


def main() -> list[Type2BuiltArtifact]:
    results = build_type2()
    print(f"manifest: {MANIFEST_PATH}")
    print(f"built design count: {len(results)}")
    for result in results:
        print(f"{result['design_id']}: {result['aedt_path']}")
    return results


if __name__ == "__main__":
    main()

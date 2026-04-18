from __future__ import annotations

from collections.abc import Callable
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from entry.sample import MANIFEST_PATH
from peetsfea.backend.pyaedt.type2_step_setup_ready import Type2SetupReadyResult, setup_type2_step_ledger
from peetsfea.type2_runtime import Type2BuiltArtifact, build_prepared_type2_designs, validate_prepared_type2_step_ledgers
from peetsfea.type2_sampled import load_type2_sample_manifest, prepared_builds_from_manifest

_Runner = Callable[..., Type2SetupReadyResult]

def build_type2(
    *,
    manifest_path: Path = MANIFEST_PATH,
    runner: _Runner = setup_type2_step_ledger,
) -> list[Type2BuiltArtifact]:
    document = load_type2_sample_manifest(manifest_path)
    prepared_builds = prepared_builds_from_manifest(manifest_path, selected_design_ids=())
    validate_prepared_type2_step_ledgers(prepared_builds)
    return build_prepared_type2_designs(
        prepared_builds,
        jobs=document["config"]["aedt_builder_n"],
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

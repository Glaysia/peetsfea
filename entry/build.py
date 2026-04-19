from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
import sys
from pathlib import Path
from typing import TypedDict, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from entry.sample import MANIFEST_PATH
from peetsfea.aedt import Hfss
from peetsfea.aedt.protocols import HfssSession
from peetsfea.backend.pyaedt.type2_step_setup_ready import (
    setup_type2_step_ledger,
    setup_type2_step_ledger_into_hfss,
)
from peetsfea.type2_runtime import Type2BuiltArtifact, build_prepared_type2_designs
from peetsfea.type2_step_export import export_type2_step_artifacts
from peetsfea.type2_sampled import DesignVariableEntry, load_type2_sample_manifest, prepared_builds_from_manifest

_Exporter = Callable[..., object]


class _Type2BuildRunnerResult(TypedDict):
    aedt_path: str
    source_step_ledger_path: str
    imported_ledger_path: str


_Runner = Callable[..., _Type2BuildRunnerResult]


def _create_gui_hfss(design_name: str) -> HfssSession:
    return cast(HfssSession, Hfss(design=design_name, non_graphical=False, new_desktop=True, close_on_exit=False))


def _setup_type2_step_ledger_gui_debug(
    *,
    step_ledger_path: Path,
    output_aedt_path: Path,
    imported_ledger_path: Path,
    design_name: str,
    design_variables: tuple[DesignVariableEntry, ...],
) -> _Type2BuildRunnerResult:
    hfss = _create_gui_hfss(design_name)
    return cast(
        _Type2BuildRunnerResult,
        setup_type2_step_ledger_into_hfss(
            hfss=hfss,
            step_ledger_path=step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            design_variables=design_variables,
        ),
    )


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


def build_type2_debug(
    *,
    manifest_path: Path = MANIFEST_PATH,
    design_id: str,
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _Runner = _setup_type2_step_ledger_gui_debug,
) -> list[Type2BuiltArtifact]:
    if design_id == "":
        raise ValueError("design_id is required for debug mode")
    prepared_builds = prepared_builds_from_manifest(manifest_path, selected_design_ids=(design_id,))
    return build_prepared_type2_designs(
        prepared_builds,
        jobs=1,
        exporter=exporter,
        runner=runner,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--design-id", default="")
    return parser


def run_build_cli(argv: Sequence[str]) -> list[Type2BuiltArtifact]:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if args.debug and args.design_id == "":
        parser.error("--debug requires --design-id")
    if not args.debug and args.design_id != "":
        parser.error("--design-id requires --debug")
    if args.debug:
        results = build_type2_debug(manifest_path=args.manifest, design_id=args.design_id)
    else:
        results = build_type2(manifest_path=args.manifest)

    print(f"manifest: {args.manifest}")
    print(f"built design count: {len(results)}")
    for result in results:
        print(f"{result['design_id']}: {result['aedt_path']}")
    return results


def main() -> list[Type2BuiltArtifact]:
    return run_build_cli(tuple(sys.argv[1:]))


if __name__ == "__main__":
    main()

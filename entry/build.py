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
    setup_and_solve_type2_step_ledger,
    setup_type2_step_ledger,
    setup_type2_step_ledger_into_hfss,
)
from peetsfea.backend.pyaedt.type2_step_em_solve import Type2EmSolveResult
from peetsfea.type2_runtime import (
    Type2BuiltArtifact,
    Type2EmArtifact,
    build_prepared_type2_designs_best_effort,
    build_prepared_type2_designs,
    ensure_prepared_type2_step_ledgers,
    write_type2_build_skipped_ledger,
)
from peetsfea.type2_runtime import solve_prepared_type2_designs
from peetsfea.type2_step_export import export_type2_step_artifacts
from peetsfea.type2_sampled import DesignVariableEntry, load_type2_sample_manifest, prepared_builds_from_manifest

_Exporter = Callable[..., object]


class _Type2BuildRunnerResult(TypedDict):
    aedt_path: str
    source_step_ledger_path: str
    imported_ledger_path: str


_Runner = Callable[..., _Type2BuildRunnerResult]


class _Type2SolveRunnerResult(_Type2BuildRunnerResult):
    em_solve: Type2EmSolveResult


_SolveRunner = Callable[..., _Type2SolveRunnerResult]


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
            run_aedt_design_validation=False,
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
    jobs = document["config"]["aedt_builder_n"]
    batch = build_prepared_type2_designs_best_effort(
        prepared_builds,
        jobs=jobs,
        exporter=exporter,
        runner=runner,
    )
    skipped_ledger_path = manifest_path.parent / "type2_build_skipped.json"
    write_type2_build_skipped_ledger(skipped_ledger_path, manifest_path=manifest_path, skipped=batch["skipped"])
    if len(batch["skipped"]) > 0:
        print(f"skipped design count: {len(batch['skipped'])}")
        print(f"build skipped ledger: {skipped_ledger_path}")
    return batch["built"]


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
    ensure_prepared_type2_step_ledgers(prepared_builds, jobs=1, exporter=exporter)
    return build_prepared_type2_designs(
        prepared_builds,
        jobs=1,
        exporter=exporter,
        runner=runner,
    )


def solve_type2(
    *,
    manifest_path: Path = MANIFEST_PATH,
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _SolveRunner = setup_and_solve_type2_step_ledger,
) -> list[Type2EmArtifact]:
    document = load_type2_sample_manifest(manifest_path)
    prepared_builds = prepared_builds_from_manifest(manifest_path, selected_design_ids=())
    jobs = document["config"]["aedt_builder_n"]
    ensure_prepared_type2_step_ledgers(prepared_builds, jobs=jobs, exporter=exporter)
    return solve_prepared_type2_designs(
        prepared_builds,
        jobs=jobs,
        exporter=exporter,
        runner=runner,
    )


def solve_type2_debug(
    *,
    manifest_path: Path = MANIFEST_PATH,
    design_id: str,
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _SolveRunner = setup_and_solve_type2_step_ledger,
) -> list[Type2EmArtifact]:
    if design_id == "":
        raise ValueError("design_id is required for debug solve mode")
    prepared_builds = prepared_builds_from_manifest(manifest_path, selected_design_ids=(design_id,))
    ensure_prepared_type2_step_ledgers(prepared_builds, jobs=1, exporter=exporter)
    return solve_prepared_type2_designs(
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
    parser.add_argument("--solve", action="store_true")
    return parser


def run_build_cli(argv: Sequence[str]) -> list[Type2BuiltArtifact] | list[Type2EmArtifact]:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if args.debug and args.design_id == "":
        parser.error("--debug requires --design-id")
    if not args.debug and args.design_id != "":
        parser.error("--design-id requires --debug")
    if args.solve and args.debug:
        results = solve_type2_debug(manifest_path=args.manifest, design_id=args.design_id)
    elif args.solve:
        results = solve_type2(manifest_path=args.manifest)
    elif args.debug:
        results = build_type2_debug(manifest_path=args.manifest, design_id=args.design_id)
    else:
        results = build_type2(manifest_path=args.manifest)

    print(f"manifest: {args.manifest}")
    stage_label = "solved" if args.solve else "built"
    print(f"{stage_label} design count: {len(results)}")
    for result in results:
        print(f"{result['design_id']}: {result['aedt_path']}")
        if "em_solve" in result:
            print(f"{result['design_id']} report: {result['em_solve']['report_csv_path']}")
    return results


def main() -> list[Type2BuiltArtifact] | list[Type2EmArtifact]:
    return run_build_cli(tuple(sys.argv[1:]))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
import os
import sys
import time
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
    DEFAULT_AEDT_LAUNCH_STAGGER_SEC,
    DEFAULT_AEDT_PORT_BASE,
    Type2BuiltArtifact,
    Type2EmArtifact,
    Type2AedtWorkerProcessError,
    build_type2_sampled_tomls_best_effort,
    build_prepared_type2_designs_best_effort,
    build_prepared_type2_designs,
    ensure_prepared_type2_step_ledgers,
    write_type2_build_skipped_ledger,
    solve_type2_sampled_tomls,
)
from peetsfea.type2_runtime import solve_prepared_type2_designs
from peetsfea.type2_step_export import export_type2_step_artifacts
from peetsfea.type2_sampled import (
    DesignVariableEntry,
    iter_type2_sample_manifest_entries,
    load_type2_sample_manifest_config,
    prepared_builds_from_manifest,
)

_Exporter = Callable[..., object]
_BUILD_RESTART_SLEEP_SEC: float = 60.0
_BUILD_RESTART_LIMIT: int = 500


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
    selected_design_ids: tuple[str, ...] = (),
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _Runner = setup_type2_step_ledger,
    reuse_aedt: bool = True,
    aedt_port_base: int = DEFAULT_AEDT_PORT_BASE,
    aedt_launch_stagger_sec: float = DEFAULT_AEDT_LAUNCH_STAGGER_SEC,
    sleep: Callable[[float], None] = time.sleep,
) -> list[Type2BuiltArtifact]:
    config = load_type2_sample_manifest_config(manifest_path)
    jobs = config["aedt_builder_n"]
    skipped_ledger_path = manifest_path.parent / "type2_build_skipped.json"
    if exporter is not export_type2_step_artifacts or runner is not setup_type2_step_ledger:
        batch = build_prepared_type2_designs_best_effort(
            prepared_builds_from_manifest(manifest_path, selected_design_ids=selected_design_ids),
            jobs=jobs,
            exporter=exporter,
            runner=runner,
        )
        write_type2_build_skipped_ledger(skipped_ledger_path, manifest_path=manifest_path, skipped=batch["skipped"])
    else:
        restart_attempt = 0
        while True:
            try:
                batch = build_type2_sampled_tomls_best_effort(
                    (
                        entry["sampled_toml_path"]
                        for entry in iter_type2_sample_manifest_entries(
                            manifest_path,
                            selected_design_ids=selected_design_ids,
                        )
                    ),
                    jobs=jobs,
                    skipped_ledger_path=skipped_ledger_path,
                    manifest_path=manifest_path,
                    progress_reporter=_build_progress_reporter("build"),
                    reuse_aedt=reuse_aedt,
                    aedt_port_base=aedt_port_base,
                    aedt_launch_stagger_sec=aedt_launch_stagger_sec,
                )
                break
            except Type2AedtWorkerProcessError:
                restart_attempt += 1
                if restart_attempt > _BUILD_RESTART_LIMIT:
                    raise
                sleep(_BUILD_RESTART_SLEEP_SEC)
    if len(batch["skipped"]) > 0:
        print(f"skipped design count: {len(batch['skipped'])}")
        print(f"build skipped ledger: {skipped_ledger_path}")
        raise RuntimeError(
            f"type2 build skipped {len(batch['skipped'])} design(s); "
            f"see skipped ledger at {skipped_ledger_path}"
        )
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
    selected_design_ids: tuple[str, ...] = (),
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _SolveRunner = setup_and_solve_type2_step_ledger,
) -> list[Type2EmArtifact]:
    config = load_type2_sample_manifest_config(manifest_path)
    jobs = config["aedt_builder_n"]
    if exporter is export_type2_step_artifacts and runner is setup_and_solve_type2_step_ledger:
        return solve_type2_sampled_tomls(
            (
                entry["sampled_toml_path"]
                for entry in iter_type2_sample_manifest_entries(manifest_path, selected_design_ids=selected_design_ids)
            ),
            jobs=jobs,
            progress_reporter=_build_progress_reporter("solve"),
        )
    prepared_builds = prepared_builds_from_manifest(manifest_path, selected_design_ids=selected_design_ids)
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
    parser.add_argument(
        "--aedt-port-base",
        type=int,
        default=int(os.environ.get("PEETSFEA_AEDT_PORT_BASE", str(DEFAULT_AEDT_PORT_BASE))),
    )
    parser.add_argument(
        "--aedt-launch-stagger-sec",
        type=float,
        default=float(os.environ.get("PEETSFEA_AEDT_LAUNCH_STAGGER_SEC", str(DEFAULT_AEDT_LAUNCH_STAGGER_SEC))),
    )
    parser.add_argument("--no-aedt-reuse", action="store_true")
    return parser


def _build_progress_reporter(stage: str) -> Callable[[int, int, int], None]:
    last_report_at = 0.0

    def report(completed_count: int, built_count: int, skipped_count: int) -> None:
        nonlocal last_report_at
        now = time.monotonic()
        if completed_count == 1 or completed_count % 100 == 0 or now - last_report_at >= 30:
            last_report_at = now
            print(f"{stage} progress: completed={completed_count} built={built_count} skipped={skipped_count}", flush=True)

    return report


def run_build_cli(argv: Sequence[str]) -> list[Type2BuiltArtifact] | list[Type2EmArtifact]:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if args.debug and args.design_id == "":
        parser.error("--debug requires --design-id")
    selected_design_ids = (args.design_id,) if args.design_id != "" else tuple()
    if args.solve and args.debug:
        results = solve_type2_debug(manifest_path=args.manifest, design_id=args.design_id)
    elif args.solve:
        results = solve_type2(manifest_path=args.manifest, selected_design_ids=selected_design_ids)
    elif args.debug:
        results = build_type2_debug(manifest_path=args.manifest, design_id=args.design_id)
    else:
        results = build_type2(
            manifest_path=args.manifest,
            selected_design_ids=selected_design_ids,
            reuse_aedt=not args.no_aedt_reuse,
            aedt_port_base=args.aedt_port_base,
            aedt_launch_stagger_sec=args.aedt_launch_stagger_sec,
        )

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

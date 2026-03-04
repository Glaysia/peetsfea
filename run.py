from __future__ import annotations

import shutil
import sys
from pathlib import Path

from peetsfea import RunConfig, build_square_spiral_from_manifest, run
from peetsfea.pipeline.package_export import export_design_zip
from peetsfea.pipeline.uniform_seedset import iter_uniform_feasible_seeds
from peetsfea.types.manifest import Manifest, RunResult

cwd = Path(__file__).parent.resolve()

UNIFORM_SEEDSET_ENABLED = True
UNIFORM_SEED_START = 0
UNIFORM_SEED_END = 100000
UNIFORM_SEED_TARGET_COUNT = 1000
UNIFORM_SEED_MAX_ATTEMPTS = 64

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


def run_one(seed: int) -> bool:
    config = RunConfig(
        ansys_executable_path="/opt/ansys_inc/v252/AnsysEM",
        ansys_run_dir=f"{cwd}/run/aedt",
        toml_path=f"{cwd}/run/type1.toml",
        seed=seed,
        backend="hfss",
        non_graphical=True,
        close_on_exit=True,
    )
    run_dir = Path(config.ansys_run_dir)
    result: RunResult | None = None
    manifest: Manifest | None = None
    try:
        result = run(config)
        manifest = result["manifest"]
        geometry = build_square_spiral_from_manifest(manifest)
        if config.export_zip:
            zip_path = export_design_zip(
                design_id=manifest["design_id"],
                aedt_path=Path(geometry["aedt_path"]),
                repro_toml=result["repro_snapshot"]["toml_bytes"],
                dataset_toml=result["dataset_snapshot"]["toml_bytes"],
                source_toml=result["source_toml_bytes"],
                output_dir=run_dir,
            )
            result["zip_path"] = str(zip_path)
        print(geometry["aedt_path"])
        return True
    except Exception as exc:
        design_id = str(manifest["design_id"]) if manifest is not None and "design_id" in manifest else None
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
        print(f"[seed={seed}] setup/validate failed; cleaned generated files and continue: {exc}")
        return False

MANY = "MANY"
SINGLE = "SINGLE"


RUN_MODE = MANY
# RUN_MODE = SINGLE

if __name__ == "__main__":
    cli_seed: int | None = None
    if len(sys.argv) > 1:
        try:
            cli_seed = int(sys.argv[1])
        except ValueError as exc:
            raise SystemExit(f"Invalid seed '{sys.argv[1]}'. Usage: python run.py [seed]") from exc

    if cli_seed is not None:
        run_one(cli_seed)
    elif RUN_MODE == MANY:
        failed_seeds: list[int] = []
        if UNIFORM_SEEDSET_ENABLED:
            seeds = iter_uniform_feasible_seeds(
                spec_path=Path(f"{cwd}/run/type1.toml"),
                seed_start=UNIFORM_SEED_START,
                seed_end=UNIFORM_SEED_END,
                target_size=UNIFORM_SEED_TARGET_COUNT,
                max_attempts=UNIFORM_SEED_MAX_ATTEMPTS,
            )
            print(
                "uniform seed stream enabled "
                f"(range=[{UNIFORM_SEED_START},{UNIFORM_SEED_END}), target={UNIFORM_SEED_TARGET_COUNT}, "
                f"max_attempts={UNIFORM_SEED_MAX_ATTEMPTS})"
            )
        else:
            seeds = range(10000)
        for seed in seeds:
            ok = run_one(seed)
            if not ok:
                failed_seeds.append(seed)
        if failed_seeds:
            print(f"failed seeds: {failed_seeds}")
        else:
            print("all seeds completed successfully")
    elif RUN_MODE == SINGLE:
        run_one(2)

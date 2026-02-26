from __future__ import annotations

import shutil
import sys
from pathlib import Path

from peetsfea import RunConfig, build_square_spiral_from_manifest, run
from peetsfea.types.manifest import Manifest

cwd = Path(__file__).parent.resolve()

def _safe_remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
        return
    if path.exists():
        path.unlink(missing_ok=True)


def _cleanup_failed_design_files(*, run_dir: Path, design_id: str | None, manifest_path: Path | None) -> None:
    if design_id is None:
        if manifest_path is not None:
            _safe_remove(manifest_path)
        return
    targets: list[Path] = [
        run_dir / f"{design_id}.aedt",
        run_dir / f"{design_id}.aedt.lock",
        run_dir / f"{design_id}.aedtresults",
        run_dir / f"geometry_metadata_{design_id}.json",
    ]
    if manifest_path is not None:
        targets.append(manifest_path)
    for target in targets:
        _safe_remove(target)


def run_one(seed: int) -> bool:
    config = RunConfig(
        ansys_executable_path="/opt/ansys_inc/v252/AnsysEM",
        ansys_run_dir=f"{cwd}/run/aedt",
        toml_path=f"{cwd}/run/type1.toml",
        seed=seed,
        backend="hfss",
        non_graphical=False,
        close_on_exit=False,
    )
    run_dir = Path(config.ansys_run_dir)
    manifest: Manifest | None = None
    try:
        manifest = run(config)
        geometry = build_square_spiral_from_manifest(manifest)
        print(geometry["aedt_path"])
        return True
    except Exception as exc:
        design_id = str(manifest["design_id"]) if manifest is not None and "design_id" in manifest else None
        manifest_path = (
            Path(str(manifest["manifest_path"]))
            if manifest is not None and "manifest_path" in manifest
            else None
        )
        _cleanup_failed_design_files(run_dir=run_dir, design_id=design_id, manifest_path=manifest_path)
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
        for seed in range(95,100):
            ok = run_one(seed)
            if not ok:
                failed_seeds.append(seed)
        if failed_seeds:
            print(f"failed seeds: {failed_seeds}")
        else:
            print("all seeds completed successfully")
    elif RUN_MODE == SINGLE:
        run_one(2)

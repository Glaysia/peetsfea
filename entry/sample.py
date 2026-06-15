"""Sample random in-design-space SSW STEP files over a seed range and view one in OCP.

Each seed in ``[--seed-start, --seed-end]`` draws one random point inside the reference design
space (``examples/0.3.2_sweep.toml``), freezes it to a fixed TOML, and exports a STEP scene plus
its ledger/token TOML into a gitignored output directory. After generation the script prints a
seed -> design_id -> step index and shows the ``--view-seed`` scene in the OCP viewer.

Run from ``run/``:

    ../.venv/bin/python ../entry/sample.py --seed-start 0 --seed-end 9
    ../.venv/bin/python ../entry/sample.py --seed-start 0 --seed-end 99 --jobs 10 --no-view
    ../.venv/bin/python ../entry/sample.py --seed-start 0 --seed-end 9 --view-seed 3
    ../.venv/bin/python ../entry/sample.py --debug   # use the hardcoded DEBUG_* constants
"""

from __future__ import annotations

import argparse
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cadquery as cq
from ocp_vscode import Camera, Collapse, show

from peetsfea.ssw_design_space import DEFAULT_REFERENCE_TOML_PATH, sample_ssw_fixed_tomls
from peetsfea.ssw_step import export_ssw_step_artifacts

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "run" / "ssw_step_samples"
OCP_PORT = 3939

# --debug uses these hardcoded constants instead of CLI args, so the VS Code launch.json
# config can run `sample.py --debug` with no arguments. Edit these to control a debug run.
DEBUG_SEED_START = 0
DEBUG_SEED_END = 9
DEBUG_VIEW_SEED = 0
DEBUG_NO_VIEW = False
DEBUG_OUTPUT_DIR = DEFAULT_OUTPUT_DIR
DEBUG_SWEEP_TOML = DEFAULT_REFERENCE_TOML_PATH
# Keep DEBUG_JOBS at 1: workers run in child processes where breakpoints will not hit.
DEBUG_JOBS = 10


class SampledStep:
    def __init__(self, *, seed: int, design_id: str, step_path: Path, sample_dir: Path) -> None:
        self.seed = seed
        self.design_id = design_id
        self.step_path = step_path
        self.sample_dir = sample_dir


def _seed_output_dir(*, output_root: Path, seed: int) -> Path:
    return output_root / f"seed_{seed:05d}"


def generate_step_for_seed(
    *,
    seed: int,
    sweep_toml_path: Path,
    output_root: Path,
    reference_toml_path: Path,
) -> SampledStep:
    sample_dir = _seed_output_dir(output_root=output_root, seed=seed)
    shutil.rmtree(sample_dir, ignore_errors=True)
    sample_dir.mkdir(parents=True, exist_ok=True)
    batch = sample_ssw_fixed_tomls(
        sample_count=1,
        seed=seed,
        sweep_toml_path=sweep_toml_path,
        output_dir=sample_dir,
        reference_toml_path=reference_toml_path,
    )
    sample = batch.samples[0]
    artifacts = export_ssw_step_artifacts(source_toml_path=sample.toml_path, output_dir=sample_dir, seed=seed)
    step_path = Path(artifacts["scene_step_path"])
    if not step_path.is_file():
        raise FileNotFoundError(f"STEP export did not create a scene file for seed {seed}: {step_path}")
    return SampledStep(seed=seed, design_id=sample.design_id, step_path=step_path, sample_dir=sample_dir)


def generate_steps(*, seeds: list[int], sweep_toml_path: Path, output_root: Path, jobs: int) -> list[SampledStep]:
    """Generate one STEP per seed, in parallel when ``jobs > 1``.

    Each seed writes to its own ``seed_<NNNNN>/`` directory, so the per-seed work is fully
    independent and safe to run across processes. Results are returned ordered by seed.
    """
    if jobs <= 1 or len(seeds) <= 1:
        return [
            generate_step_for_seed(
                seed=seed,
                sweep_toml_path=sweep_toml_path,
                output_root=output_root,
                reference_toml_path=sweep_toml_path,
            )
            for seed in seeds
        ]
    by_seed: dict[int, SampledStep] = {}
    with ProcessPoolExecutor(max_workers=min(jobs, len(seeds))) as executor:
        futures = {
            executor.submit(
                generate_step_for_seed,
                seed=seed,
                sweep_toml_path=sweep_toml_path,
                output_root=output_root,
                reference_toml_path=sweep_toml_path,
            ): seed
            for seed in seeds
        }
        for future in as_completed(futures):
            by_seed[futures[future]] = future.result()
    return [by_seed[seed] for seed in seeds]


def show_step_in_ocp(sample: SampledStep) -> None:
    imported = cq.importers.importStep(str(sample.step_path))
    solids = tuple(imported.solids().vals())
    if len(solids) == 0:
        raise RuntimeError(f"generated SSW STEP contains no solids: {sample.step_path}")
    show(
        imported,
        names=[f"seed_{sample.seed:05d}_{sample.design_id}"],
        axes=True,
        axes0=True,
        grid=True,
        collapse=Collapse.ROOT,
        reset_camera=Camera.RESET,
        port=OCP_PORT,
    )


@dataclass(frozen=True)
class RunConfig:
    seed_start: int
    seed_end: int
    view_seed: int | None
    no_view: bool
    output_dir: Path
    sweep_toml: Path
    jobs: int


def _resolve_config(argv: list[str]) -> RunConfig:
    parser = argparse.ArgumentParser(description="Generate random in-space SSW STEP files over a seed range.")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="ignore CLI args and use the hardcoded DEBUG_* constants (for VS Code launch.json)",
    )
    parser.add_argument("--seed-start", type=int, default=None, help="first seed (inclusive)")
    parser.add_argument("--seed-end", type=int, default=None, help="last seed (inclusive)")
    parser.add_argument(
        "--view-seed",
        type=int,
        default=None,
        help="seed whose STEP is shown in OCP (default: --seed-start)",
    )
    parser.add_argument("--no-view", action="store_true", help="generate only, skip the OCP viewer")
    parser.add_argument("--jobs", "-j", type=int, default=1, help="parallel worker processes for generation")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="gitignored output root")
    parser.add_argument("--sweep-toml", type=Path, default=DEFAULT_REFERENCE_TOML_PATH, help="sweep SSOT TOML")
    args = parser.parse_args(argv)
    if args.debug:
        return RunConfig(
            seed_start=DEBUG_SEED_START,
            seed_end=DEBUG_SEED_END,
            view_seed=DEBUG_VIEW_SEED,
            no_view=DEBUG_NO_VIEW,
            output_dir=DEBUG_OUTPUT_DIR,
            sweep_toml=DEBUG_SWEEP_TOML,
            jobs=DEBUG_JOBS,
        )
    if args.seed_start is None or args.seed_end is None:
        parser.error("--seed-start and --seed-end are required unless --debug is set")
    if args.jobs < 1:
        parser.error(f"--jobs must be >= 1 (actual={args.jobs})")
    return RunConfig(
        seed_start=args.seed_start,
        seed_end=args.seed_end,
        view_seed=args.view_seed,
        no_view=args.no_view,
        output_dir=args.output_dir,
        sweep_toml=args.sweep_toml,
        jobs=args.jobs,
    )


def main(argv: list[str] | None = None) -> list[SampledStep]:
    config = _resolve_config(sys.argv[1:] if argv is None else argv)
    if config.seed_end < config.seed_start:
        raise ValueError(f"seed_end ({config.seed_end}) must be >= seed_start ({config.seed_start})")
    view_seed = config.seed_start if config.view_seed is None else config.view_seed
    if not config.no_view and not (config.seed_start <= view_seed <= config.seed_end):
        raise ValueError(f"view_seed ({view_seed}) must be within [{config.seed_start}, {config.seed_end}]")

    output_root: Path = config.output_dir
    output_root.mkdir(parents=True, exist_ok=True)
    seeds = list(range(config.seed_start, config.seed_end + 1))
    worker_count = min(config.jobs, len(seeds))
    print(f"Generating {len(seeds)} SSW STEP file(s) with {worker_count} worker(s) ...")
    samples = generate_steps(
        seeds=seeds,
        sweep_toml_path=config.sweep_toml,
        output_root=output_root,
        jobs=config.jobs,
    )

    print(f"\nGenerated {len(samples)} SSW STEP file(s) under {output_root}")
    print(f"{'seed':>6}  {'design_id':<24}  step")
    for sample in samples:
        print(f"{sample.seed:>6}  {sample.design_id:<24}  {sample.step_path}")

    if config.no_view:
        print("\nno-view set; skipping OCP viewer.")
        return samples

    view_sample = next(sample for sample in samples if sample.seed == view_seed)
    print(f"\nShowing seed {view_seed} ({view_sample.design_id}) in OCP on port {OCP_PORT} ...")
    show_step_in_ocp(view_sample)
    return samples


if __name__ == "__main__":
    main()

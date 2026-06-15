"""View one sampled SSW design in the OCP viewer (with per-body color and transparency).

By default this calls ``entry/sample.py`` to generate STEP files for the seed range, then shows
``--view-seed`` in the OCP viewer. Pass ``--no-sample`` to skip generation and view a seed that
was already sampled into the output directory.

The viewer shows the rebuilt ``cq.Assembly`` (copper/coil/ferrite/non-model colors and
transparency), not the flattened STEP re-import which renders as a single default material.

Run from ``run/``:

    ../.venv/bin/python ../entry/view.py --seed-start 0 --seed-end 9 --view-seed 3
    ../.venv/bin/python ../entry/view.py --view-seed 3 --no-sample
    ../.venv/bin/python ../entry/view.py --debug   # use the hardcoded DEBUG_* constants
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ocp_vscode import Camera, Collapse, show

from peetsfea.ssw_step import build_ssw_assembly, load_ssw_fixed_spec

from entry.sample import (
    DEFAULT_OUTPUT_DIR,
    SCENE_STEP_NAME,
    RunConfig,
    SampledStep,
    add_sampling_arguments,
    run_sampling,
    seed_output_dir,
)
from peetsfea.ssw_design_space import DEFAULT_REFERENCE_TOML_PATH

OCP_PORT = 3939
TOKEN_TOML_NAME = "coil_making_token.toml"

# --debug uses these hardcoded constants instead of CLI args, so the VS Code launch.json
# config can run `view.py --debug` with no arguments. Edit these to control a debug run.
DEBUG_SEED_START = 0
DEBUG_SEED_END = 49
DEBUG_VIEW_SEED = 1
DEBUG_JOBS = 12
DEBUG_NO_SAMPLE = False
DEBUG_OUTPUT_DIR = DEFAULT_OUTPUT_DIR
DEBUG_SWEEP_TOML = DEFAULT_REFERENCE_TOML_PATH


@dataclass(frozen=True)
class ViewConfig:
    seed_start: int
    seed_end: int
    view_seed: int
    jobs: int
    no_sample: bool
    output_dir: Path
    sweep_toml: Path


def load_existing_sample(*, output_root: Path, seed: int) -> SampledStep:
    """Reconstruct a SampledStep for an already-generated seed directory (for --no-sample)."""
    sample_dir = seed_output_dir(output_root=output_root, seed=seed)
    step_path = sample_dir / SCENE_STEP_NAME
    if not step_path.is_file():
        raise FileNotFoundError(
            f"no generated STEP for seed {seed}: {step_path} (run without --no-sample first)"
        )
    design_tomls = [p for p in sorted(sample_dir.glob("*.toml")) if p.name != TOKEN_TOML_NAME]
    if len(design_tomls) != 1:
        raise RuntimeError(
            f"expected exactly one design TOML in {sample_dir} (found {[p.name for p in design_tomls]})"
        )
    toml_path = design_tomls[0]
    return SampledStep(
        seed=seed,
        design_id=toml_path.stem,
        toml_path=toml_path,
        step_path=step_path,
        sample_dir=sample_dir,
    )


def show_sample_in_ocp(sample: SampledStep) -> None:
    # Show the cq.Assembly rebuilt from the sampled spec, not the imported STEP: the assembly
    # carries per-body color and transparency (copper/coil/ferrite/non-model), whereas a
    # STEP re-import flattens everything to a single default (yellow) material.
    spec = load_ssw_fixed_spec(sample.toml_path)
    assembly = build_ssw_assembly(spec)
    show(
        assembly,
        names=[f"seed_{sample.seed:05d}_{sample.design_id}"],
        axes=True,
        axes0=True,
        grid=True,
        collapse=Collapse.ROOT,
        reset_camera=Camera.RESET,
        port=OCP_PORT,
    )


def _resolve_config(argv: list[str]) -> ViewConfig:
    parser = argparse.ArgumentParser(description="Generate (via sample.py) and view one SSW design in OCP.")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="ignore CLI args and use the hardcoded DEBUG_* constants (for VS Code launch.json)",
    )
    parser.add_argument("--view-seed", type=int, default=None, help="seed whose design is shown in OCP")
    parser.add_argument(
        "--no-sample",
        action="store_true",
        help="do not re-run sampling; view a seed already generated in --output-dir",
    )
    add_sampling_arguments(parser)
    args = parser.parse_args(argv)
    if args.debug:
        return ViewConfig(
            seed_start=DEBUG_SEED_START,
            seed_end=DEBUG_SEED_END,
            view_seed=DEBUG_VIEW_SEED,
            jobs=DEBUG_JOBS,
            no_sample=DEBUG_NO_SAMPLE,
            output_dir=DEBUG_OUTPUT_DIR,
            sweep_toml=DEBUG_SWEEP_TOML,
        )
    if args.jobs < 1:
        parser.error(f"--jobs must be >= 1 (actual={args.jobs})")
    if args.no_sample:
        if args.view_seed is None:
            parser.error("--view-seed is required with --no-sample")
        # seed range is unused when not sampling; pin it to the view seed.
        return ViewConfig(
            seed_start=args.view_seed,
            seed_end=args.view_seed,
            view_seed=args.view_seed,
            jobs=args.jobs,
            no_sample=True,
            output_dir=args.output_dir,
            sweep_toml=args.sweep_toml,
        )
    if args.seed_start is None or args.seed_end is None:
        parser.error("--seed-start and --seed-end are required unless --debug or --no-sample is set")
    if args.seed_end < args.seed_start:
        parser.error(f"--seed-end ({args.seed_end}) must be >= --seed-start ({args.seed_start})")
    view_seed = args.seed_start if args.view_seed is None else args.view_seed
    if not (args.seed_start <= view_seed <= args.seed_end):
        parser.error(f"--view-seed ({view_seed}) must be within [{args.seed_start}, {args.seed_end}]")
    return ViewConfig(
        seed_start=args.seed_start,
        seed_end=args.seed_end,
        view_seed=view_seed,
        jobs=args.jobs,
        no_sample=False,
        output_dir=args.output_dir,
        sweep_toml=args.sweep_toml,
    )


def main(argv: list[str] | None = None) -> SampledStep:
    config = _resolve_config(sys.argv[1:] if argv is None else argv)
    if config.no_sample:
        print(f"--no-sample set; reusing generated artifacts under {config.output_dir}")
        view_sample = load_existing_sample(output_root=config.output_dir, seed=config.view_seed)
    else:
        samples = run_sampling(
            RunConfig(
                seed_start=config.seed_start,
                seed_end=config.seed_end,
                output_dir=config.output_dir,
                sweep_toml=config.sweep_toml,
                jobs=config.jobs,
            )
        )
        view_sample = next(sample for sample in samples if sample.seed == config.view_seed)
    print(f"\nShowing seed {config.view_seed} ({view_sample.design_id}) in OCP on port {OCP_PORT} ...")
    show_sample_in_ocp(view_sample)
    return view_sample


if __name__ == "__main__":
    main()

"""Solve the canonical fixed-point TOML (data/0.3.x_fixed.toml) in headless HFSS.

This is the plain HFSS path (no Q3D / Maxwell 3D cross-validation): it samples the single
fixed point, exports the AEDT ports model, runs the HFSS setup/solve, and writes the report
CSVs under ``--output-dir``. By default it self-launches a headless ansysedt (new desktop);
pass ``--grpc-port`` to instead attach to a warm, runner-owned ansysedt session.

Run from ``run/``:

    ../.venv/bin/python ../entry/solve_fixed.py                      # self-launch, full passes
    ../.venv/bin/python ../entry/solve_fixed.py --mode semi_dry      # cheaper, fewer passes
    ../.venv/bin/python ../entry/solve_fixed.py --grpc-port 48579    # attach to warm AEDT
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from pprint import pprint

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.ssw_random_sample_reports import run_ssw_random_sample_reports_from_toml_text
from peetsfea.ssw_step import DEFAULT_SOURCE_TOML_PATH

DEFAULT_OUTPUT_DIR = Path("hfss_fixed_solve")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Solve data/0.3.x_fixed.toml in headless HFSS.")
    parser.add_argument("--fixed-toml", type=Path, default=DEFAULT_SOURCE_TOML_PATH, help="fixed-point TOML to solve")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="where AEDT + report CSVs land")
    parser.add_argument("--seed", type=int, default=0, help="sample seed (fixed point is deterministic anyway)")
    parser.add_argument("--mode", choices=("full", "semi_dry"), default="full", help="solve pass budget")
    parser.add_argument("--grpc-port", type=int, default=None, help="attach to a warm ansysedt on this gRPC port")
    parser.add_argument("--aedt-pid", type=int, default=None, help="optional ansysedt PID to attach (with --grpc-port)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    fixed_toml: Path = args.fixed_toml
    if not fixed_toml.is_file():
        parser.error(f"fixed TOML does not exist: {fixed_toml}")
    output_dir: Path = args.output_dir.resolve()

    print(f"Solving fixed point {fixed_toml} in HFSS (mode={args.mode}) -> {output_dir}")
    if args.grpc_port is not None:
        print(f"Attaching to warm ansysedt on gRPC port {args.grpc_port}")
    else:
        print("Self-launching a headless ansysedt (new desktop) ...")

    result = run_ssw_random_sample_reports_from_toml_text(
        fixed_toml.read_text(encoding="utf-8"),
        output_dir=output_dir,
        seed=args.seed,
        mode=args.mode,
        grpc_port=args.grpc_port,
        aedt_pid=args.aedt_pid,
    )

    print("\n=== SOLVE DONE ===")
    pprint(
        {
            "design_id": result["design_id"],
            "aedt_path": result["aedt_path"],
            "setup_pass_counts": result["setup_pass_counts"],
            "solve_outcome": result["solve_outcome"],
            "solve_telemetry": result["solve_telemetry"],
            "csv_paths": result["csv_paths"],
        }
    )


if __name__ == "__main__":
    main()

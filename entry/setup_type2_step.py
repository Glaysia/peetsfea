from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from entry.generate_type2_step import export_type2_step_artifacts
from peetsfea.aedt.protocols import HfssSession
from peetsfea.backend.pyaedt.type2_step_setup_ready import (
    DEFAULT_DESIGN_NAME,
    DEFAULT_IMPORTED_LEDGER_PATH,
    DEFAULT_OUTPUT_AEDT_PATH,
    DEFAULT_SOURCE_STEP_LEDGER_PATH,
    Type2SetupReadyResult,
    setup_type2_step_ledger,
    setup_type2_step_ledger_into_hfss,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TYPE2_TOML_PATH = REPO_ROOT / "examples" / "type2_fixed.toml"
DEFAULT_STEP_OUTPUT_DIR = REPO_ROOT / "run" / "step" / "type2"

_Exporter = Callable[..., object]
_Runner = Callable[..., Type2SetupReadyResult]
_AttachedRunner = Callable[..., Type2SetupReadyResult]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create setup-ready type2 STEP artifacts in HFSS.")
    parser.add_argument("--toml", type=Path, default=DEFAULT_TYPE2_TOML_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_STEP_OUTPUT_DIR)
    parser.add_argument("--step-ledger", type=Path, default=DEFAULT_SOURCE_STEP_LEDGER_PATH)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--output-aedt", type=Path, default=DEFAULT_OUTPUT_AEDT_PATH)
    parser.add_argument("--imported-ledger", type=Path, default=DEFAULT_IMPORTED_LEDGER_PATH)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--design-name", type=str, default=DEFAULT_DESIGN_NAME)
    return parser.parse_args(argv)


def export_and_setup_type2_step(
    *,
    toml_path: Path = DEFAULT_TYPE2_TOML_PATH,
    output_dir: Path = DEFAULT_STEP_OUTPUT_DIR,
    step_ledger_path: Path = DEFAULT_SOURCE_STEP_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
    seed: int = 0,
    design_name: str = DEFAULT_DESIGN_NAME,
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _Runner = setup_type2_step_ledger,
) -> Type2SetupReadyResult:
    exporter(
        toml_path=toml_path,
        output_dir=output_dir,
        ledger_path=step_ledger_path,
        seed=seed,
    )
    return runner(
        step_ledger_path=step_ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        design_name=design_name,
    )


def export_and_setup_type2_step_into_hfss(
    *,
    hfss: HfssSession,
    toml_path: Path = DEFAULT_TYPE2_TOML_PATH,
    output_dir: Path = DEFAULT_STEP_OUTPUT_DIR,
    step_ledger_path: Path = DEFAULT_SOURCE_STEP_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
    seed: int = 0,
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _AttachedRunner = setup_type2_step_ledger_into_hfss,
) -> Type2SetupReadyResult:
    exporter(
        toml_path=toml_path,
        output_dir=output_dir,
        ledger_path=step_ledger_path,
        seed=seed,
    )
    return runner(
        hfss=hfss,
        step_ledger_path=step_ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
    )


def setup_type2_step_from_args(
    args: argparse.Namespace,
    *,
    exporter: _Exporter = export_type2_step_artifacts,
    runner: _Runner = setup_type2_step_ledger,
) -> Type2SetupReadyResult:
    if args.ledger is not None:
        return runner(
            step_ledger_path=Path(args.ledger),
            output_aedt_path=Path(args.output_aedt),
            imported_ledger_path=Path(args.imported_ledger),
            design_name=str(args.design_name),
        )

    return export_and_setup_type2_step(
        toml_path=Path(args.toml),
        output_dir=Path(args.output_dir),
        step_ledger_path=Path(args.step_ledger),
        output_aedt_path=Path(args.output_aedt),
        imported_ledger_path=Path(args.imported_ledger),
        seed=int(args.seed),
        design_name=str(args.design_name),
        exporter=exporter,
        runner=runner,
    )


def main(argv: list[str] | None = None) -> Type2SetupReadyResult:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)
    result = setup_type2_step_from_args(args)
    print(f"source STEP ledger: {result['source_step_ledger_path']}")
    print(f"output AEDT: {result['aedt_path']}")
    print(f"imported ledger: {result['imported_ledger_path']}")
    print(
        "mesh: "
        f"{result['mesh']['operation_name']} "
        f"objects={result['mesh']['objects']} "
        f"max_length={result['mesh']['max_length']}"
    )
    print(
        "boundary: "
        f"{result['boundary']['type']} region={result['boundary']['region_name']} "
        f"faces={result['boundary']['face_count']} "
        f"offset={result['boundary']['offset_value']}"
    )
    print(f"ports: tx={result['ports']['tx']} rx={result['ports']['rx']}")
    print(
        "analysis: "
        f"{result['analysis']['setup_name']} "
        f"freq_hz={result['analysis']['setup_frequency_hz']}"
    )
    print(f"validation ok: {result['validation_report']['ok']}")
    return result


if __name__ == "__main__":
    main()

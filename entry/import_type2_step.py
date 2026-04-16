from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from entry.generate_type2_step import export_type2_step_artifacts
from peetsfea.backend.pyaedt.type2_step_import_pipeline import (
    DEFAULT_DESIGN_NAME,
    DEFAULT_IMPORTED_LEDGER_PATH,
    DEFAULT_OUTPUT_AEDT_PATH,
    DEFAULT_SOURCE_STEP_LEDGER_PATH,
    Type2ImportedLedger,
    import_type2_step_ledger,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TYPE2_TOML_PATH = REPO_ROOT / "examples" / "type2.toml"
DEFAULT_STEP_OUTPUT_DIR = REPO_ROOT / "run" / "step" / "type2"

_Exporter = Callable[..., object]
_Importer = Callable[..., Type2ImportedLedger]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import type2 STEP artifacts into headless HFSS.")
    parser.add_argument("--toml", type=Path, default=DEFAULT_TYPE2_TOML_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_STEP_OUTPUT_DIR)
    parser.add_argument("--step-ledger", type=Path, default=DEFAULT_SOURCE_STEP_LEDGER_PATH)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--output-aedt", type=Path, default=DEFAULT_OUTPUT_AEDT_PATH)
    parser.add_argument("--imported-ledger", type=Path, default=DEFAULT_IMPORTED_LEDGER_PATH)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--design-name", type=str, default=DEFAULT_DESIGN_NAME)
    return parser.parse_args(argv)


def import_type2_step_from_args(
    args: argparse.Namespace,
    *,
    exporter: _Exporter = export_type2_step_artifacts,
    importer: _Importer = import_type2_step_ledger,
) -> Type2ImportedLedger:
    if args.ledger is not None:
        step_ledger_path = Path(args.ledger)
    else:
        step_ledger_path = Path(args.step_ledger)
        exporter(
            toml_path=Path(args.toml),
            output_dir=Path(args.output_dir),
            ledger_path=step_ledger_path,
            seed=int(args.seed),
        )

    return importer(
        step_ledger_path=step_ledger_path,
        output_aedt_path=Path(args.output_aedt),
        imported_ledger_path=Path(args.imported_ledger),
        design_name=str(args.design_name),
    )


def main(argv: list[str] | None = None) -> Type2ImportedLedger:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)
    result = import_type2_step_from_args(args)
    print(f"source STEP ledger: {result['source_step_ledger_path']}")
    print(f"output AEDT: {result['aedt_path']}")
    print(f"imported ledger: {result['imported_ledger_path']}")
    print(f"non-model object count: {len(result['non_model_objects'])}")
    print(f"modeled object count: {len(result['modeled_objects'])}")
    return result


if __name__ == "__main__":
    main()

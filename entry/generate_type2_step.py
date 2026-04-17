from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.type2_step_export import DEFAULT_LEDGER_PATH
from peetsfea.type2_step_export import DEFAULT_OUTPUT_DIR
from peetsfea.type2_step_export import DEFAULT_SCENE_STEP_PATH
from peetsfea.type2_step_export import SOURCE_TOML_PATH
from peetsfea.type2_step_export import Type2DirectModeledArtifact
from peetsfea.type2_step_export import Type2StepLedger
from peetsfea.type2_step_export import export_type2_step_artifacts
from peetsfea.type2_step_export import export_type2_tx_single_coil_artifact
from peetsfea.type2_step_spec import Type2StepSpec
from peetsfea.type2_step_spec import load_type2_step_spec


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate type2 STEP artifacts from examples/type2_fixed.toml.")
    parser.add_argument("--toml", type=Path, default=SOURCE_TOML_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> Type2StepLedger:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)
    ledger = export_type2_step_artifacts(
        toml_path=args.toml,
        output_dir=args.output_dir,
        ledger_path=args.ledger,
        seed=args.seed,
    )
    print(f"source TOML: {ledger['source_toml_path']}")
    print(f"output dir: {ledger['output_dir']}")
    print(f"scene STEP: {ledger['scene_step_path']}")
    print(f"ledger JSON: {args.ledger}")
    print(f"non-model object count: {len(ledger['non_model_objects'])}")
    print(f"modeled object count: {len(ledger['modeled_objects'])}")
    return ledger


__all__ = [
    "DEFAULT_LEDGER_PATH",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_SCENE_STEP_PATH",
    "SOURCE_TOML_PATH",
    "Type2DirectModeledArtifact",
    "Type2StepLedger",
    "Type2StepSpec",
    "export_type2_step_artifacts",
    "export_type2_tx_single_coil_artifact",
    "load_type2_step_spec",
    "main",
    "parse_args",
]


if __name__ == "__main__":
    main()

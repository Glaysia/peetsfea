from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from entry.generate_type2_step import export_type2_tx_single_coil_artifact

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOML_PATH = REPO_ROOT / "examples" / "type2_fixed.toml"
DEFAULT_OUTPUT_STEP_PATH = REPO_ROOT / "run" / "step" / "tx_rect_void_coil.step"
DEFAULT_METADATA_PATH = REPO_ROOT / "run" / "step" / "tx_rect_void_coil.metadata.json"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the type2 tx_single_coil modeled object to STEP.")
    parser.add_argument("--toml", type=Path, default=DEFAULT_TOML_PATH)
    parser.add_argument("--output-step", type=Path, default=DEFAULT_OUTPUT_STEP_PATH)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: list[str]) -> Path:
    args = parse_args(argv)
    result = export_type2_tx_single_coil_artifact(
        toml_path=args.toml,
        output_step_path=args.output_step,
        metadata_path=args.metadata,
        seed=args.seed,
    )
    print(f"source TOML: {args.toml}")
    print(f"output STEP: {result['step_path']}")
    print(f"metadata JSON: {args.metadata}")
    print(f"expected exported body count: {result['expected_exported_body_count']}")
    return Path(result["step_path"])


if __name__ == "__main__":
    main(sys.argv[1:])

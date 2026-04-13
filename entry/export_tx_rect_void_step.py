from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.tx_rect_void import export_tx_rect_void_step

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOML_PATH = REPO_ROOT / "examples" / "tx_rect_void" / "tx_rect_void_coil.toml"
DEFAULT_OUTPUT_STEP_PATH = REPO_ROOT / "run" / "step" / "tx_rect_void_coil.step"
DEFAULT_METADATA_PATH = REPO_ROOT / "run" / "step" / "tx_rect_void_coil.metadata.json"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the standalone TX rect/void coil TOML to STEP.")
    parser.add_argument("--toml", type=Path, default=DEFAULT_TOML_PATH)
    parser.add_argument("--output-step", type=Path, default=DEFAULT_OUTPUT_STEP_PATH)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: list[str]) -> Path:
    args = parse_args(argv)
    result = export_tx_rect_void_step(
        toml_path=args.toml,
        output_step_path=args.output_step,
        metadata_path=args.metadata,
        seed=args.seed,
    )
    print(f"source TOML: {result.source_toml_path}")
    print(f"output STEP: {result.output_step_path}")
    print(f"metadata JSON: {result.metadata_path}")
    print(f"box count: {len(result.boxes)}")
    return Path(result.output_step_path)


if __name__ == "__main__":
    main(sys.argv[1:])

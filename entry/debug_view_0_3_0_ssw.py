from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TypedDict

import cadquery as cq
from ocp_vscode import Camera, Collapse, show

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.ssw_step import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_TOML_PATH,
    build_ssw_assembly,
    export_ssw_step_artifacts,
    load_ssw_fixed_spec,
    load_ssw_step_ledger,
)

SOURCE_TOML_PATH = DEFAULT_SOURCE_TOML_PATH
OUTPUT_DIR = DEFAULT_OUTPUT_DIR
SEED = 0
OCP_PORT = 3939


class DebugSswSummary(TypedDict):
    source_toml_path: str
    output_dir: str
    seed: int
    step_path: str
    step_ledger_path: str
    token_toml_path: str
    body_names: list[str]
    copper_body_names: list[str]
    fr4_body_names: list[str]
    non_model_body_names: list[str]


def _require_file(*, path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")


def generate_ssw_debug_summary(
    *,
    source_toml_path: Path = SOURCE_TOML_PATH,
    output_dir: Path = OUTPUT_DIR,
    seed: int = SEED,
) -> DebugSswSummary:
    artifacts = export_ssw_step_artifacts(source_toml_path=source_toml_path, output_dir=output_dir, seed=seed)
    step_path = Path(artifacts["scene_step_path"])
    ledger_path = Path(artifacts["ledger_path"])
    token_toml_path = Path(artifacts["token_toml_path"])
    _require_file(path=step_path, label="0.3.0 SSW STEP file")
    _require_file(path=ledger_path, label="0.3.0 SSW STEP ledger")
    _require_file(path=token_toml_path, label="0.3.0 SSW coil making token TOML")
    ledger = load_ssw_step_ledger(ledger_path)
    return {
        "source_toml_path": artifacts["source_toml_path"],
        "output_dir": str(output_dir),
        "seed": seed,
        "step_path": str(step_path),
        "step_ledger_path": str(ledger_path),
        "token_toml_path": str(token_toml_path),
        "body_names": ledger["body_names"],
        "copper_body_names": ledger["copper_body_names"],
        "fr4_body_names": ledger["fr4_body_names"],
        "non_model_body_names": ledger["non_model_body_names"],
    }


def show_ssw_fixed_in_ocp(
    *,
    source_toml_path: Path = SOURCE_TOML_PATH,
    output_dir: Path = OUTPUT_DIR,
    seed: int = SEED,
) -> DebugSswSummary:
    summary = generate_ssw_debug_summary(source_toml_path=source_toml_path, output_dir=output_dir, seed=seed)
    spec = load_ssw_fixed_spec(source_toml_path)
    assembly = build_ssw_assembly(spec)
    show(
        assembly,
        names=["0.3.0_fixed_tx_rx_ssw"],
        axes=True,
        axes0=True,
        grid=True,
        collapse=Collapse.ROOT,
        reset_camera=Camera.RESET,
        port=OCP_PORT,
    )
    imported = cq.importers.importStep(summary["step_path"])
    solids = tuple(imported.solids().vals())
    if len(solids) == 0:
        raise RuntimeError(f"imported SSW STEP contains no solids: {summary['step_path']}")
    return summary


def main() -> DebugSswSummary:
    summary = show_ssw_fixed_in_ocp()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    main()

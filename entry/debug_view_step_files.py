from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TypedDict

import build123d as bd
from ocp_vscode import Camera, Collapse, show

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from entry.sample import MinimalManifestEntry, sample_minimal
from peetsfea.backend.pyaedt.minimal_em import create_graphical_hfss, setup_minimal_step_ledger
from peetsfea.minimal_step import load_minimal_step_ledger

VIEW_INDEX = -1
BUILD_W_GUI = True


class DebugStepFilesSummary(TypedDict):
    view_index: int
    build_w_gui: bool
    manifest_path: str
    design_id: str
    step_path: str
    step_ledger_path: str
    aedt_path: str
    imported_ledger_path: str
    body_names: list[str]
    copper_body_names: list[str]
    port_sheet_names: list[str]


def _selected_entry(*, entries: list[MinimalManifestEntry], view_index: int) -> MinimalManifestEntry:
    if len(entries) == 0:
        raise ValueError("minimal manifest has no entries")
    selected_position = view_index if view_index >= 0 else len(entries) + view_index
    if selected_position < 0 or selected_position >= len(entries):
        raise IndexError(
            f"VIEW_INDEX out of range for minimal manifest "
            f"(view_index={view_index}, entry_count={len(entries)})"
        )
    entry = entries[selected_position]
    if not isinstance(entry, dict):
        raise TypeError(f"minimal manifest entries[{selected_position}] must be an object")
    return entry


def _require_file(*, path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")


def generate_minimal_step_summary(*, view_index: int = VIEW_INDEX) -> DebugStepFilesSummary:
    manifest = sample_minimal()
    entry = _selected_entry(entries=manifest["entries"], view_index=view_index)
    step_path = Path(entry["step_path"])
    step_ledger_path = Path(entry["step_ledger_path"])
    _require_file(path=step_path, label="minimal STEP file")
    _require_file(path=step_ledger_path, label="minimal STEP ledger")
    ledger = load_minimal_step_ledger(step_ledger_path)
    return {
        "view_index": view_index,
        "build_w_gui": BUILD_W_GUI,
        "manifest_path": str(Path(manifest["output_dir"]) / "manifest.json"),
        "design_id": entry["design_id"],
        "step_path": str(step_path),
        "step_ledger_path": str(step_ledger_path),
        "aedt_path": entry["aedt_path"],
        "imported_ledger_path": entry["imported_ledger_path"],
        "body_names": ledger["body_names"],
        "copper_body_names": ledger["copper_body_names"],
        "port_sheet_names": ledger["port_sheet_names"],
    }


def show_minimal_step_in_ocp(*, view_index: int = VIEW_INDEX) -> DebugStepFilesSummary:
    summary = generate_minimal_step_summary(view_index=view_index)
    model = bd.import_step(summary["step_path"])
    show(
        model,
        names=[summary["design_id"]],
        axes=True,
        axes0=True,
        grid=True,
        collapse=Collapse.ROOT,
        reset_camera=Camera.RESET,
    )
    if BUILD_W_GUI:
        setup_minimal_step_ledger(
            step_ledger_path=Path(summary["step_ledger_path"]),
            output_aedt_path=Path(summary["aedt_path"]),
            imported_ledger_path=Path(summary["imported_ledger_path"]),
            design_name=summary["design_id"],
            hfss_factory=create_graphical_hfss,
            release_desktop_on_exit=False,
        )
    return summary


def main() -> DebugStepFilesSummary:
    summary = show_minimal_step_in_ocp()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from entry.sample import MANIFEST_PATH, MinimalManifestEntry, load_minimal_manifest
from peetsfea.backend.pyaedt.minimal_em import MinimalSetupResult, MinimalSolveResult
from peetsfea.backend.pyaedt.minimal_em import setup_minimal_step_ledger, solve_minimal_step_ledger
from peetsfea.minimal_step import export_minimal_step_artifacts


def _selected_entries(
    *,
    manifest_path: Path,
    selected_design_id: str,
) -> list[MinimalManifestEntry]:
    manifest = load_minimal_manifest(manifest_path)
    entries = manifest["entries"]
    if not isinstance(entries, list):
        raise TypeError("minimal manifest entries must be a list")
    typed_entries: list[MinimalManifestEntry] = []
    for index, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, dict):
            raise TypeError(f"minimal manifest entries[{index}] must be an object")
        entry = raw_entry
        if selected_design_id != "" and entry["design_id"] != selected_design_id:
            continue
        typed_entries.append(entry)
    if not typed_entries:
        raise ValueError(f"no minimal manifest entries selected (design_id={selected_design_id!r})")
    return typed_entries


def _ensure_step_artifacts(entry: MinimalManifestEntry) -> None:
    ledger_path = Path(entry["step_ledger_path"])
    step_path = Path(entry["step_path"])
    if ledger_path.is_file() and step_path.is_file():
        return
    export_minimal_step_artifacts(
        source_toml_path=Path(entry["sampled_toml_path"]),
        output_dir=ledger_path.parent,
        seed=entry["seed"],
        scene_step_path=step_path,
        ledger_path=ledger_path,
    )


def build_minimal(
    *,
    manifest_path: Path = MANIFEST_PATH,
    selected_design_id: str = "",
) -> list[MinimalSetupResult]:
    results: list[MinimalSetupResult] = []
    for entry in _selected_entries(manifest_path=manifest_path, selected_design_id=selected_design_id):
        _ensure_step_artifacts(entry)
        results.append(
            setup_minimal_step_ledger(
                step_ledger_path=Path(entry["step_ledger_path"]),
                output_aedt_path=Path(entry["aedt_path"]),
                imported_ledger_path=Path(entry["imported_ledger_path"]),
                design_name=entry["design_id"],
            )
        )
    return results


def solve_minimal(
    *,
    manifest_path: Path = MANIFEST_PATH,
    selected_design_id: str = "",
) -> list[MinimalSolveResult]:
    results: list[MinimalSolveResult] = []
    for entry in _selected_entries(manifest_path=manifest_path, selected_design_id=selected_design_id):
        _ensure_step_artifacts(entry)
        results.append(
            solve_minimal_step_ledger(
                step_ledger_path=Path(entry["step_ledger_path"]),
                output_aedt_path=Path(entry["aedt_path"]),
                imported_ledger_path=Path(entry["imported_ledger_path"]),
                design_name=entry["design_id"],
            )
        )
    return results


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--design-id", default="")
    parser.add_argument("--solve", action="store_true")
    return parser


def main() -> list[MinimalSetupResult] | list[MinimalSolveResult]:
    args = _build_arg_parser().parse_args()
    if args.solve:
        solved = solve_minimal(manifest_path=args.manifest, selected_design_id=args.design_id)
        for result in solved:
            print(f"solved: {result['setup']['aedt_path']}")
            print(f"report: {result['report_csv_path']}")
        return solved
    built = build_minimal(manifest_path=args.manifest, selected_design_id=args.design_id)
    for result in built:
        print(f"built: {result['aedt_path']}")
    return built


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import sys
from pathlib import Path

import cadquery as cq
from ocp_vscode import Camera, Collapse, show

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.console_log import log_call_duration
from peetsfea.ssw_step import (
    build_ssw_assembly,
    load_ssw_fixed_spec,
)
from peetsfea.ssw_design_space import build_ssw_aedt_identity
from peetsfea.backend.pyaedt.ssw_ports import (
    SswAedtPortSetupResult,
    create_graphical_hfss,
    setup_ssw_aedt_ports,
)

# The artifact-generation core now lives in the package so the runner can use it from the wheel.
# Re-export the canonical names here for backward compatibility with existing entry/test imports.
from peetsfea.ssw_aedt_artifacts import (
    AEDT_IMPORTED_LEDGER_NAME,
    AEDT_PORT_LEDGER_NAME,
    AEDT_SCENE_STEP_NAME,
    OUTPUT_DIR,
    SEED,
    SOURCE_TOML_PATH,
    DebugSswSummary,
    export_ssw_aedt_port_artifacts,
    generate_ssw_debug_summary,
)

OCP_PORT = 3939
ANSYS = True


@log_call_duration
def setup_ansys_ports_for_ssw_debug(
    *,
    source_toml_path: Path = SOURCE_TOML_PATH,
    output_dir: Path = OUTPUT_DIR,
    seed: int = SEED,
) -> SswAedtPortSetupResult:
    identity = build_ssw_aedt_identity(source_toml_path)
    export_ssw_aedt_port_artifacts(source_toml_path=source_toml_path, output_dir=output_dir, seed=seed)
    return setup_ssw_aedt_ports(
        port_ledger_path=output_dir / AEDT_PORT_LEDGER_NAME,
        output_aedt_path=output_dir / identity.aedt_filename,
        imported_ledger_path=output_dir / AEDT_IMPORTED_LEDGER_NAME,
        design_name=identity.design_id,
        hfss_factory=create_graphical_hfss,
        release_desktop_on_exit=False,
    )


@log_call_duration
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
        names=["0.3.2_fixed_tx_rx_ssw"],
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


@log_call_duration
def main() -> DebugSswSummary:
    summary = show_ssw_fixed_in_ocp()
    if ANSYS:
        ansys_result = setup_ansys_ports_for_ssw_debug()
        summary["ansys_enabled"] = True
        summary["aedt_step_path"] = ansys_result["scene_step_path"]
        summary["aedt_port_ledger_path"] = ansys_result["source_port_ledger_path"]
        summary["aedt_imported_ledger_path"] = ansys_result["imported_ledger_path"]
        summary["aedt_path"] = ansys_result["aedt_path"]
        summary["aedt_ports"] = ansys_result["ports"]
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    main()

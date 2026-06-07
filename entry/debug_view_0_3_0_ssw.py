from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Literal, Mapping, TypedDict
import tomllib

import cadquery as cq
from ocp_vscode import Camera, Collapse, show

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.ssw_step import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_TOML_PATH,
    FixedDimensions,
    SswStepLedger,
    build_ssw_assembly,
    export_ssw_step_artifacts,
    load_ssw_fixed_spec,
    load_ssw_step_ledger,
)
from peetsfea.backend.pyaedt.ssw_ports import (
    CanonicalCoordinates,
    SswAedtBodyLedgerEntry,
    SswAedtPorts,
    SswAedtPortCellLedgerEntry,
    SswAedtPortSetupResult,
    SswAedtPortStepLedger,
    create_graphical_hfss,
    setup_ssw_aedt_ports,
    write_ssw_aedt_port_ledger,
)

SOURCE_TOML_PATH = DEFAULT_SOURCE_TOML_PATH
OUTPUT_DIR = DEFAULT_OUTPUT_DIR
SEED = 0
OCP_PORT = 3939
ANSYS = True
AEDT_SCENE_STEP_NAME = "ssw_scene_with_ports.step"
AEDT_PORT_LEDGER_NAME = "ssw_aedt_port_ledger.json"
AEDT_IMPORTED_LEDGER_NAME = "ssw_aedt_imported_ledger.json"
AEDT_PROJECT_NAME = "ssw_0_3_0_ports.aedt"
AEDT_DESIGN_NAME = "ssw_0_3_0_ports"
TX_PORT_SHEET_NAME = "tx_aedt_port_sheet"
RX_PORT_SHEET_NAME = "rx_aedt_port_sheet"


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
    ferrite_body_names: list[str]
    ansys_enabled: bool
    aedt_step_path: str
    aedt_port_ledger_path: str
    aedt_imported_ledger_path: str
    aedt_path: str
    aedt_ports: SswAedtPorts


class _PortSheetGeometry(TypedDict):
    name: str
    role: Literal["tx", "rx"]
    face: cq.Face
    vertices_xyz: list[list[float]]
    signal_edge_vertices_xyz: list[list[float]]
    reference_edge_vertices_xyz: list[list[float]]


def _require_file(*, path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")


def _json_action_params_by_key(action: Mapping[str, object]) -> dict[str, object]:
    params = action["params"]
    if isinstance(params, (str, bytes)) or not isinstance(params, list):
        raise TypeError("action params must be a list")
    mapped: dict[str, object] = {}
    for index, param in enumerate(params):
        if not isinstance(param, dict):
            raise TypeError(f"action params[{index}] must be an object")
        key = param["key"]
        value_json = param["value_json"]
        if not isinstance(key, str):
            raise TypeError(f"action params[{index}].key must be str")
        if not isinstance(value_json, str):
            raise TypeError(f"action params[{index}].value_json must be str")
        mapped[key] = json.loads(value_json)
    return mapped


def _port_anchor_from_token(*, token_toml_path: Path, target: str) -> tuple[float, float, float]:
    token_doc = tomllib.loads(token_toml_path.read_text(encoding="utf-8"))
    actions = token_doc["actions"]
    if isinstance(actions, (str, bytes)) or not isinstance(actions, list):
        raise TypeError("coil making token actions must be a list")
    matches = tuple(action for action in actions if isinstance(action, dict) and action["target"] == target)
    if len(matches) != 1:
        raise ValueError(f"expected exactly one scene placement action for {target!r} (count={len(matches)})")
    params = _json_action_params_by_key(matches[0])
    anchor = params["port_anchor_world_xyz_mm"]
    if isinstance(anchor, (str, bytes)) or not isinstance(anchor, list):
        raise TypeError(f"{target}.port_anchor_world_xyz_mm must be a list")
    if len(anchor) != 3:
        raise ValueError(f"{target}.port_anchor_world_xyz_mm must contain exactly three values")
    return (float(anchor[0]), float(anchor[1]), float(anchor[2]))


def _tx_port_sheet_geometry(*, fixed: FixedDimensions, anchor_xyz: tuple[float, float, float]) -> _PortSheetGeometry:
    center_x, center_y, center_z = anchor_xyz
    half_width = fixed.port_landing_pad_mm / 2.0
    half_gap = fixed.port_length_mm / 2.0
    vertices = [
        [center_x - half_width, center_y - half_gap, center_z],
        [center_x + half_width, center_y - half_gap, center_z],
        [center_x + half_width, center_y + half_gap, center_z],
        [center_x - half_width, center_y + half_gap, center_z],
    ]
    return {
        "name": TX_PORT_SHEET_NAME,
        "role": "tx",
        "face": cq.Face.makePlane(
            length=fixed.port_length_mm,
            width=fixed.port_landing_pad_mm,
            basePnt=anchor_xyz,
            dir=(0.0, 0.0, 1.0),
        ),
        "vertices_xyz": vertices,
        "signal_edge_vertices_xyz": [vertices[0], vertices[1]],
        "reference_edge_vertices_xyz": [vertices[3], vertices[2]],
    }


def _rx_port_sheet_geometry(*, fixed: FixedDimensions, anchor_xyz: tuple[float, float, float]) -> _PortSheetGeometry:
    center_x, center_y, center_z = anchor_xyz
    half_width = fixed.port_landing_pad_mm / 2.0
    half_gap = fixed.port_length_mm / 2.0
    vertices = [
        [center_x, center_y - half_width, center_z - half_gap],
        [center_x, center_y + half_width, center_z - half_gap],
        [center_x, center_y + half_width, center_z + half_gap],
        [center_x, center_y - half_width, center_z + half_gap],
    ]
    return {
        "name": RX_PORT_SHEET_NAME,
        "role": "rx",
        "face": cq.Face.makePlane(
            length=fixed.port_landing_pad_mm,
            width=fixed.port_length_mm,
            basePnt=anchor_xyz,
            dir=(1.0, 0.0, 0.0),
        ),
        "vertices_xyz": vertices,
        "signal_edge_vertices_xyz": [vertices[0], vertices[1]],
        "reference_edge_vertices_xyz": [vertices[3], vertices[2]],
    }


def _canonical_from_bounds(*, min_xyz: tuple[float, float, float], max_xyz: tuple[float, float, float]) -> CanonicalCoordinates:
    return {
        "outer_bounds_min_xyz": [min_xyz[0], min_xyz[1], min_xyz[2]],
        "outer_bounds_max_xyz": [max_xyz[0], max_xyz[1], max_xyz[2]],
        "outer_bounds_size_xyz": [max_xyz[0] - min_xyz[0], max_xyz[1] - min_xyz[1], max_xyz[2] - min_xyz[2]],
    }


def _body_entry_from_ssw(body: Mapping[str, object]) -> SswAedtBodyLedgerEntry:
    object_id = body["object_id"]
    role = body["role"]
    material = body["material"]
    center = body["center_xyz"]
    size = body["size_xyz"]
    if not isinstance(object_id, str) or object_id == "":
        raise TypeError("SSW ledger body object_id must be a non-empty str")
    if not isinstance(role, str) or role == "":
        raise TypeError(f"SSW ledger body role must be a non-empty str (object_id={object_id})")
    if not isinstance(material, str) or material == "":
        raise TypeError(f"SSW ledger body material must be a non-empty str (object_id={object_id})")
    if isinstance(center, (str, bytes)) or not isinstance(center, list) or len(center) != 3:
        raise TypeError(f"SSW ledger body center_xyz must be a list of three values (object_id={object_id})")
    if isinstance(size, (str, bytes)) or not isinstance(size, list) or len(size) != 3:
        raise TypeError(f"SSW ledger body size_xyz must be a list of three values (object_id={object_id})")
    center_xyz = (float(center[0]), float(center[1]), float(center[2]))
    size_xyz = (float(size[0]), float(size[1]), float(size[2]))
    min_xyz = (
        center_xyz[0] - size_xyz[0] / 2.0,
        center_xyz[1] - size_xyz[1] / 2.0,
        center_xyz[2] - size_xyz[2] / 2.0,
    )
    max_xyz = (
        center_xyz[0] + size_xyz[0] / 2.0,
        center_xyz[1] + size_xyz[1] / 2.0,
        center_xyz[2] + size_xyz[2] / 2.0,
    )
    return {
        "object_id": object_id,
        "role": role,
        "material": material,
        "model_state": role not in {"non_model", "ferrite"},
        "canonical_coordinates": _canonical_from_bounds(min_xyz=min_xyz, max_xyz=max_xyz),
    }


def _body_entry_from_port_sheet(sheet: _PortSheetGeometry) -> SswAedtBodyLedgerEntry:
    vertices = sheet["vertices_xyz"]
    min_xyz = (
        min(vertex[0] for vertex in vertices),
        min(vertex[1] for vertex in vertices),
        min(vertex[2] for vertex in vertices),
    )
    max_xyz = (
        max(vertex[0] for vertex in vertices),
        max(vertex[1] for vertex in vertices),
        max(vertex[2] for vertex in vertices),
    )
    return {
        "object_id": sheet["name"],
        "role": f"{sheet['role']}_port_sheet",
        "material": "vacuum",
        "model_state": True,
        "canonical_coordinates": _canonical_from_bounds(min_xyz=min_xyz, max_xyz=max_xyz),
    }


def _port_cell_from_sheet(sheet: _PortSheetGeometry) -> SswAedtPortCellLedgerEntry:
    return {
        "role": sheet["role"],
        "port_sheet_name": sheet["name"],
        "port_sheet_vertices_xyz": sheet["vertices_xyz"],
        "signal_edge_vertices_xyz": sheet["signal_edge_vertices_xyz"],
        "reference_edge_vertices_xyz": sheet["reference_edge_vertices_xyz"],
    }


def export_ssw_aedt_port_artifacts(
    *,
    source_toml_path: Path = SOURCE_TOML_PATH,
    output_dir: Path = OUTPUT_DIR,
    seed: int = SEED,
) -> SswAedtPortStepLedger:
    summary = generate_ssw_debug_summary(source_toml_path=source_toml_path, output_dir=output_dir, seed=seed)
    spec = load_ssw_fixed_spec(source_toml_path)
    ssw_ledger = load_ssw_step_ledger(Path(summary["step_ledger_path"]))
    token_toml_path = Path(summary["token_toml_path"])
    tx_sheet = _tx_port_sheet_geometry(
        fixed=spec.fixed,
        anchor_xyz=_port_anchor_from_token(token_toml_path=token_toml_path, target="scene.tx_ssw_coil.placement"),
    )
    rx_sheet = _rx_port_sheet_geometry(
        fixed=spec.fixed,
        anchor_xyz=_port_anchor_from_token(token_toml_path=token_toml_path, target="scene.rx_ssw_coil.placement"),
    )
    port_sheets = (tx_sheet, rx_sheet)
    assembly = build_ssw_assembly(spec)
    for sheet in port_sheets:
        assembly.add(cq.Workplane(obj=sheet["face"]), name=sheet["name"], color=cq.Color(0.7, 0.84, 1.0, 0.88))
    aedt_step_path = output_dir / AEDT_SCENE_STEP_NAME
    assembly.save(str(aedt_step_path), exportType="STEP")
    if not aedt_step_path.is_file() or aedt_step_path.stat().st_size == 0:
        raise RuntimeError(f"CadQuery STEP export failed for SSW AEDT port scene: {aedt_step_path}")
    ledger = _build_ssw_aedt_port_ledger(
        ssw_ledger=ssw_ledger,
        ssw_ledger_path=Path(summary["step_ledger_path"]),
        aedt_step_path=aedt_step_path,
        port_sheets=port_sheets,
    )
    write_ssw_aedt_port_ledger(ledger_path=output_dir / AEDT_PORT_LEDGER_NAME, ledger=ledger)
    return ledger


def _build_ssw_aedt_port_ledger(
    *,
    ssw_ledger: SswStepLedger,
    ssw_ledger_path: Path,
    aedt_step_path: Path,
    port_sheets: tuple[_PortSheetGeometry, _PortSheetGeometry],
) -> SswAedtPortStepLedger:
    body_entries = [_body_entry_from_ssw(body) for body in ssw_ledger["bodies"]]
    body_entries.extend(_body_entry_from_port_sheet(sheet) for sheet in port_sheets)
    return {
        "source_step_ledger_path": str(ssw_ledger_path),
        "scene_step_path": str(aedt_step_path),
        "seed": ssw_ledger["seed"],
        "units": ssw_ledger["units"],
        "body_names": [*ssw_ledger["body_names"], *(sheet["name"] for sheet in port_sheets)],
        "copper_body_names": list(ssw_ledger["copper_body_names"]),
        "port_sheet_names": [sheet["name"] for sheet in port_sheets],
        "non_model_body_names": [*ssw_ledger["non_model_body_names"], *ssw_ledger["ferrite_body_names"]],
        "bodies": body_entries,
        "port_cells": [_port_cell_from_sheet(sheet) for sheet in port_sheets],
    }


def setup_ansys_ports_for_ssw_debug(
    *,
    source_toml_path: Path = SOURCE_TOML_PATH,
    output_dir: Path = OUTPUT_DIR,
    seed: int = SEED,
) -> SswAedtPortSetupResult:
    export_ssw_aedt_port_artifacts(source_toml_path=source_toml_path, output_dir=output_dir, seed=seed)
    return setup_ssw_aedt_ports(
        port_ledger_path=output_dir / AEDT_PORT_LEDGER_NAME,
        output_aedt_path=output_dir / AEDT_PROJECT_NAME,
        imported_ledger_path=output_dir / AEDT_IMPORTED_LEDGER_NAME,
        design_name=AEDT_DESIGN_NAME,
        hfss_factory=create_graphical_hfss,
        release_desktop_on_exit=False,
    )


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
        "ferrite_body_names": ledger["ferrite_body_names"],
        "ansys_enabled": False,
        "aedt_step_path": "",
        "aedt_port_ledger_path": "",
        "aedt_imported_ledger_path": "",
        "aedt_path": "",
        "aedt_ports": {"tx": [], "rx": []},
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

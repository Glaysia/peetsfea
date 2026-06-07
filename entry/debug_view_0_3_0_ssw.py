from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Mapping, TypedDict
import tomllib

import cadquery as cq
from ocp_vscode import Camera, Collapse, show

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.ssw_step import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_TOML_PATH,
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
    SswAedtPortEdgeLedgerEntry,
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
AEDT_SCENE_STEP_NAME = "ssw_scene.step"
AEDT_PORT_LEDGER_NAME = "ssw_aedt_port_ledger.json"
AEDT_IMPORTED_LEDGER_NAME = "ssw_aedt_imported_ledger.json"
AEDT_PROJECT_NAME = "ssw_0_3_0_ports.aedt"
AEDT_DESIGN_NAME = "ssw_0_3_0_ports"


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


def _placement_params_from_token(*, token_toml_path: Path, target: str) -> dict[str, object]:
    token_doc = tomllib.loads(token_toml_path.read_text(encoding="utf-8"))
    actions = token_doc["actions"]
    if isinstance(actions, (str, bytes)) or not isinstance(actions, list):
        raise TypeError("coil making token actions must be a list")
    matches = tuple(action for action in actions if isinstance(action, dict) and action["target"] == target)
    if len(matches) != 1:
        raise ValueError(f"expected exactly one scene placement action for {target!r} (count={len(matches)})")
    return _json_action_params_by_key(matches[0])


def _required_str(params: Mapping[str, object], *, key: str, context: str) -> str:
    if key not in params:
        raise ValueError(f"{context} is missing required key {key!r}")
    value = params[key]
    if not isinstance(value, str) or value == "":
        raise TypeError(f"{context}.{key} must be a non-empty str")
    return value


def _required_point(params: Mapping[str, object], *, key: str, context: str) -> list[float]:
    if key not in params:
        raise ValueError(f"{context} is missing required key {key!r}")
    value = params[key]
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise TypeError(f"{context}.{key} must be a list of three numbers")
    if len(value) != 3:
        raise ValueError(f"{context}.{key} must contain exactly three values")
    point: list[float] = []
    for index, component in enumerate(value):
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise TypeError(f"{context}.{key}[{index}] must be numeric")
        point.append(float(component))
    return point


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


def _copper_body_for_role(*, ssw_ledger: SswStepLedger, role: str) -> str:
    prefix = f"{role}_"
    matches = tuple(name for name in ssw_ledger["copper_body_names"] if name.startswith(prefix))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one copper body for {role!r} (matches={matches!r})")
    return matches[0]


def _tx_port_edge_entry(
    *,
    ssw_ledger: SswStepLedger,
    placement_params: Mapping[str, object],
    minimum_edge_length_mm: float,
) -> SswAedtPortEdgeLedgerEntry:
    context = "scene.tx_ssw_coil.placement"
    port_face = _required_str(placement_params, key="port_face", context=context)
    if port_face != "lower_z":
        raise ValueError(f"{context}.port_face must be 'lower_z' for TX SSW edge ports (actual={port_face!r})")
    return {
        "role": "tx",
        "copper_body_name": _copper_body_for_role(ssw_ledger=ssw_ledger, role="tx_ssw_coil"),
        "selection": "nearest_long_face_edges",
        "face_axis": "z",
        "face_side": "min",
        "anchor_xyz": _required_point(placement_params, key="port_anchor_world_xyz_mm", context=context),
        "minimum_edge_length_mm": minimum_edge_length_mm,
    }


def _rx_port_edge_entry(
    *,
    ssw_ledger: SswStepLedger,
    placement_params: Mapping[str, object],
    minimum_edge_length_mm: float,
    pair_edge_length_mm: float,
    pair_spacing_mm: float,
) -> SswAedtPortEdgeLedgerEntry:
    context = "scene.rx_ssw_coil.placement"
    coil_mode = _required_str(placement_params, key="coil_mode", context=context)
    port_face = _required_str(placement_params, key="port_face", context=context)
    if coil_mode == "normal_spiral":
        if port_face != "normal_spiral_landing":
            raise ValueError(f"{context}.port_face must be normal_spiral_landing (actual={port_face!r})")
        return {
            "role": "rx",
            "copper_body_name": _copper_body_for_role(ssw_ledger=ssw_ledger, role="rx_ssw_coil"),
            "selection": "axis_spaced_face_edges",
            "face_axis": "x",
            "face_side": "min",
            "edge_axis": "z",
            "spacing_axis": "y",
            "edge_length_mm": pair_edge_length_mm,
            "pair_spacing_mm": pair_spacing_mm,
        }
    if coil_mode == "ssw":
        if port_face != "rx_x_min":
            raise ValueError(f"{context}.port_face must be rx_x_min for RX SSW edge ports (actual={port_face!r})")
        return {
            "role": "rx",
            "copper_body_name": _copper_body_for_role(ssw_ledger=ssw_ledger, role="rx_ssw_coil"),
            "selection": "nearest_long_face_edges",
            "face_axis": "x",
            "face_side": "min",
            "anchor_xyz": _required_point(placement_params, key="port_anchor_world_xyz_mm", context=context),
            "minimum_edge_length_mm": minimum_edge_length_mm,
        }
    raise ValueError(f"{context}.coil_mode is unsupported for edge ports (actual={coil_mode!r})")


def _port_edge_entries(
    *,
    ssw_ledger: SswStepLedger,
    token_toml_path: Path,
    minimum_edge_length_mm: float,
    pair_edge_length_mm: float,
    pair_spacing_mm: float,
) -> list[SswAedtPortEdgeLedgerEntry]:
    tx_placement = _placement_params_from_token(
        token_toml_path=token_toml_path,
        target="scene.tx_ssw_coil.placement",
    )
    rx_placement = _placement_params_from_token(
        token_toml_path=token_toml_path,
        target="scene.rx_ssw_coil.placement",
    )
    return [
        _tx_port_edge_entry(
            ssw_ledger=ssw_ledger,
            placement_params=tx_placement,
            minimum_edge_length_mm=minimum_edge_length_mm,
        ),
        _rx_port_edge_entry(
            ssw_ledger=ssw_ledger,
            placement_params=rx_placement,
            minimum_edge_length_mm=minimum_edge_length_mm,
            pair_edge_length_mm=pair_edge_length_mm,
            pair_spacing_mm=pair_spacing_mm,
        ),
    ]


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
    aedt_step_path = Path(summary["step_path"])
    ledger = _build_ssw_aedt_port_ledger(
        ssw_ledger=ssw_ledger,
        ssw_ledger_path=Path(summary["step_ledger_path"]),
        aedt_step_path=aedt_step_path,
        port_edges=_port_edge_entries(
            ssw_ledger=ssw_ledger,
            token_toml_path=token_toml_path,
            minimum_edge_length_mm=spec.fixed.port_landing_pad_mm,
            pair_edge_length_mm=spec.fixed.port_landing_pad_mm,
            pair_spacing_mm=spec.fixed.port_length_mm,
        ),
    )
    write_ssw_aedt_port_ledger(ledger_path=output_dir / AEDT_PORT_LEDGER_NAME, ledger=ledger)
    return ledger


def _build_ssw_aedt_port_ledger(
    *,
    ssw_ledger: SswStepLedger,
    ssw_ledger_path: Path,
    aedt_step_path: Path,
    port_edges: list[SswAedtPortEdgeLedgerEntry],
) -> SswAedtPortStepLedger:
    body_entries = [_body_entry_from_ssw(body) for body in ssw_ledger["bodies"]]
    return {
        "source_step_ledger_path": str(ssw_ledger_path),
        "scene_step_path": str(aedt_step_path),
        "seed": ssw_ledger["seed"],
        "units": ssw_ledger["units"],
        "body_names": list(ssw_ledger["body_names"]),
        "copper_body_names": list(ssw_ledger["copper_body_names"]),
        "non_model_body_names": [*ssw_ledger["non_model_body_names"], *ssw_ledger["ferrite_body_names"]],
        "bodies": body_entries,
        "port_edges": port_edges,
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

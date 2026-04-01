from __future__ import annotations

from typing import TypedDict

from peetsfea.types.manifest import Manifest


class BuildPrelude(TypedDict):
    tx_dd_outer_x: float
    tx_dd_outer_y: float
    tx_vertical_outer_x: float
    tx_vertical_outer_y: float
    rx_dd_outer_x: float
    rx_dd_outer_y: float
    corner_mode: int
    pcb_thickness: float
    cu_thickness: float
    fr4_er: float
    tx_dd_top_clearance: float
    tx_vertical_orientation_mode: int
    rx_face_clearance: float
    dd_mirror_plane: str
    rx_plane: str
    neo_tx_dd_right_terminal_path: str
    neo_tx_dd_left_terminal_path: str
    tx_vertical_plane: str


def _validate_neo_tx_dd_terminal_path_contract(value: str) -> None:
    parts = value.split("_")
    if len(parts) != 4 or parts[2] != "to":
        raise ValueError("selected_parameters.neo_tx_dd terminal path must match '<start>_<cw|ccw>_to_<end>'")
    start_label = parts[0]
    direction = parts[1]
    end_label = parts[3]
    if len(start_label) != 1 or len(end_label) != 1:
        raise ValueError("selected_parameters.neo_tx_dd terminal path terminals must be single letters")
    if start_label not in {"A", "B", "C", "D", "a", "b", "c", "d"}:
        raise ValueError("selected_parameters.neo_tx_dd terminal path start terminal is unsupported")
    if end_label not in {"A", "B", "C", "D", "a", "b", "c", "d"}:
        raise ValueError("selected_parameters.neo_tx_dd terminal path end terminal is unsupported")
    if direction not in {"cw", "ccw"}:
        raise ValueError("selected_parameters.neo_tx_dd terminal path direction must be 'cw' or 'ccw'")
    if start_label.isupper() == end_label.isupper():
        raise ValueError("selected_parameters.neo_tx_dd terminal path must use one uppercase and one lowercase terminal")


def extract_build_prelude(manifest: Manifest) -> BuildPrelude:
    selected = manifest["selected_parameters"]
    return {
        "tx_dd_outer_x": float(selected["tx_dd_outer_x"]),
        "tx_dd_outer_y": float(selected["tx_dd_outer_y"]),
        "tx_vertical_outer_x": float(selected["tx_vertical_outer_x"]),
        "tx_vertical_outer_y": float(selected["tx_vertical_outer_y"]),
        "rx_dd_outer_x": float(selected["rx_dd_outer_x"]),
        "rx_dd_outer_y": float(selected["rx_dd_outer_y"]),
        "corner_mode": int(selected["corner_mode"]),
        "pcb_thickness": float(selected["pcb_thickness"]),
        "cu_thickness": float(selected["cu_thickness"]),
        "fr4_er": float(selected["fr4_er"]),
        "tx_dd_top_clearance": float(selected["tx_dd_top_clearance_mm"]),
        "tx_vertical_orientation_mode": int(selected["tx_vertical_orientation_mode"]),
        "rx_face_clearance": float(selected["rx_face_clearance_mm"]),
        "dd_mirror_plane": str(selected["dd_mirror_plane"]),
        "rx_plane": str(selected["rx_plane"]),
        "neo_tx_dd_right_terminal_path": str(selected["neo_tx_dd_right_terminal_path"]),
        "neo_tx_dd_left_terminal_path": str(selected["neo_tx_dd_left_terminal_path"]),
        "tx_vertical_plane": str(selected["tx_vertical_plane"]),
    }


def validate_build_prelude(prelude: BuildPrelude) -> None:
    if prelude["corner_mode"] not in (0, 1):
        raise ValueError("selected_parameters.corner_mode must be 0 or 1")
    if prelude["pcb_thickness"] <= 0:
        raise ValueError("selected_parameters.pcb_thickness must be > 0")
    if prelude["cu_thickness"] <= 0:
        raise ValueError("selected_parameters.cu_thickness must be > 0")
    if prelude["fr4_er"] <= 1.0:
        raise ValueError("selected_parameters.fr4_er must be > 1.0")
    if prelude["tx_dd_top_clearance"] < 0:
        raise ValueError("selected_parameters.tx_dd_top_clearance_mm must be >= 0")
    if prelude["tx_vertical_orientation_mode"] not in (0, 1):
        raise ValueError("selected_parameters.tx_vertical_orientation_mode must be 0 or 1")
    if prelude["rx_face_clearance"] < 0:
        raise ValueError("selected_parameters.rx_face_clearance_mm must be >= 0")
    if prelude["dd_mirror_plane"] != "XZ":
        raise ValueError("selected_parameters.dd_mirror_plane must be 'XZ'")
    if prelude["rx_plane"] != "YZ":
        raise ValueError("selected_parameters.rx_plane must be 'YZ'")
    _validate_neo_tx_dd_terminal_path_contract(prelude["neo_tx_dd_right_terminal_path"])
    _validate_neo_tx_dd_terminal_path_contract(prelude["neo_tx_dd_left_terminal_path"])
    if prelude["tx_vertical_plane"] != "ZX":
        raise ValueError("selected_parameters.tx_vertical_plane must be 'ZX'")

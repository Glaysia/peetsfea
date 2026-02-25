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
    pcb_thickness: float
    cu_thickness: float
    fr4_er: float
    tx_dd_top_clearance: float
    rx_face_clearance: float
    dd_mirror_plane: str
    rx_plane: str
    tx_vertical_plane: str


def extract_build_prelude(manifest: Manifest) -> BuildPrelude:
    selected = manifest["selected_parameters"]
    return {
        "tx_dd_outer_x": float(selected["tx_dd_outer_x"]),
        "tx_dd_outer_y": float(selected["tx_dd_outer_y"]),
        "tx_vertical_outer_x": float(selected["tx_vertical_outer_x"]),
        "tx_vertical_outer_y": float(selected["tx_vertical_outer_y"]),
        "rx_dd_outer_x": float(selected["rx_dd_outer_x"]),
        "rx_dd_outer_y": float(selected["rx_dd_outer_y"]),
        "pcb_thickness": float(selected["pcb_thickness"]),
        "cu_thickness": float(selected["cu_thickness"]),
        "fr4_er": float(selected["fr4_er"]),
        "tx_dd_top_clearance": float(selected["tx_dd_top_clearance_mm"]),
        "rx_face_clearance": float(selected["rx_face_clearance_mm"]),
        "dd_mirror_plane": str(selected["dd_mirror_plane"]),
        "rx_plane": str(selected["rx_plane"]),
        "tx_vertical_plane": str(selected["tx_vertical_plane"]),
    }


def validate_build_prelude(prelude: BuildPrelude) -> None:
    if prelude["pcb_thickness"] <= 0:
        raise ValueError("selected_parameters.pcb_thickness must be > 0")
    if prelude["cu_thickness"] <= 0:
        raise ValueError("selected_parameters.cu_thickness must be > 0")
    if prelude["fr4_er"] <= 1.0:
        raise ValueError("selected_parameters.fr4_er must be > 1.0")
    if prelude["tx_dd_top_clearance"] < 0:
        raise ValueError("selected_parameters.tx_dd_top_clearance_mm must be >= 0")
    if prelude["rx_face_clearance"] < 0:
        raise ValueError("selected_parameters.rx_face_clearance_mm must be >= 0")
    if prelude["dd_mirror_plane"] != "XZ":
        raise ValueError("selected_parameters.dd_mirror_plane must be 'XZ'")
    if prelude["rx_plane"] != "YZ":
        raise ValueError("selected_parameters.rx_plane must be 'YZ'")
    if prelude["tx_vertical_plane"] != "ZX":
        raise ValueError("selected_parameters.tx_vertical_plane must be 'ZX'")

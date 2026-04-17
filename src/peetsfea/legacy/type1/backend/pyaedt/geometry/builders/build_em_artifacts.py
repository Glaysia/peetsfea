from __future__ import annotations

from .build_common import *

def build_em_artifacts(
    *,
    selected: dict[str, object],
    object_names: list[str],
    group_objects: GroupObjects,
    group_endpoints: list[GroupEndpointEntry],
    scene_objects: list[SceneObjectEntry],
) -> tuple[EmReadyObjects, EmEndpoints, EmContext]:
    em_ready_objects: EmReadyObjects = {
        "tx_conductors": sorted(set(group_objects["tx_dd"] + group_objects["tx_vertical"])),
        "rx_conductors": sorted(group_objects["rx_dd"]),
        "ferrite_objects": sorted(group_objects["ferrite"]),
        "fr4_objects": [],
        "scene_bbox_source_objects": sorted([entry["name"] for entry in scene_objects if entry["present"]]),
    }
    em_endpoints: EmEndpoints = {
        "tx": [entry for entry in group_endpoints if entry["group_kind"] in ("tx_dd", "tx_vertical")],
        "rx": [entry for entry in group_endpoints if entry["group_kind"] == "rx_dd"],
    }
    em_context: EmContext = {
        "dd_mirror_plane": cast(str, selected["dd_mirror_plane"]),
        "rx_plane": cast(str, selected["rx_plane"]),
        "tx_vertical_plane": cast(str, selected["tx_vertical_plane"]),
        "source": "type1_geometry",
        "object_names": sorted(object_names),
    }
    return em_ready_objects, em_endpoints, em_context


__all__ = [
    'build_em_artifacts',
]

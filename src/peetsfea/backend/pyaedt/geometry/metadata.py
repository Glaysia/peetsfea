from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from peetsfea.types.manifest import (
    CoilPolaritySpec,
    EmContext,
    EmEndpoints,
    EmPipelineResult,
    EmPolicy,
    EmReadyObjects,
    GeometryDebug,
    GeometryMetadata,
    GroupEndpointEntry,
    GroupObjects,
    Manifest,
    SceneObjectEntry,
    UniteGroups,
)

def _build_geometry_metadata(
    manifest: Manifest,
    aedt_path: Path,
    object_names: list[str],
    metadata_path: Path,
    group_objects: GroupObjects,
    unite_groups: UniteGroups,
    group_endpoints: list[GroupEndpointEntry],
    coil_polarity: list[CoilPolaritySpec],
    em_ready_objects: EmReadyObjects,
    em_endpoints: EmEndpoints,
    em_context: EmContext,
    em_policy: EmPolicy,
    em_pipeline_result: EmPipelineResult,
    scene_objects: list[SceneObjectEntry],
    debug: GeometryDebug,
) -> GeometryMetadata:
    return {
        "design_id": manifest["design_id"],
        "design_unique_hash": manifest["design_unique_hash"],
        "toml_space_hash": manifest["toml_space_hash"],
        "toml_hash": manifest["toml_hash"],
        "peetsfea_commit": manifest["peetsfea_commit"],
        "seed": manifest["seed"],
        "retry_attempt": manifest["retry_attempt"],
        "retry_count": manifest["retry_count"],
        "repro_mode": manifest["repro_mode"],
        "selected_parameters": manifest["selected_parameters"],
        "selected_parameters_max": manifest["selected_parameters_max"],
        "selected_group_geometry": manifest["selected_group_geometry"],
        "aedt_path": str(aedt_path),
        "object_names": object_names,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "metadata_path": str(metadata_path),
        "anchor_mode": "copper_outer_edge_corner",
        "group_objects": group_objects,
        "unite_groups": unite_groups,
        "group_endpoints": group_endpoints,
        "coil_polarity": coil_polarity,
        "em_ready_objects": em_ready_objects,
        "em_endpoints": em_endpoints,
        "em_context": em_context,
        "em_policy": em_policy,
        "em_pipeline_result": em_pipeline_result,
        "scene_objects": scene_objects,
        "debug": debug,
    }



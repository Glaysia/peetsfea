from __future__ import annotations

from typing import cast

from peetsfea.aedt import Object3d
from peetsfea.types.manifest import CadProbe, CoilPolaritySpec, GroupEndpointEntry, RegionViolation

from ..build_state import DdHalfGeometryCapture, Edge2P, Point3, require_tx_dd_scene
from ..rules.cad_probe import _probe_cad_object
from ..rules.debug_checks import _bbox_violations
from .txdd_types import TxDdBuildRequest, TxDdHalfRealization, TxDdRealization


def record_txdd_half_state(
    *,
    request: TxDdBuildRequest,
    half: TxDdHalfRealization,
    object_name: str,
    instance_index: int,
    layer_index: int,
    main_start_edge: Edge2P,
    main_end_edge: Edge2P,
    has_start_tail: bool,
    start_tail_far_midpoint: Point3,
    has_end_tail: bool,
    end_tail_far_midpoint: Point3,
    bridge_edge: Edge2P,
    obj: Object3d,
) -> None:
    state = request.state
    tx_dd_scene = require_tx_dd_scene(request.ctx)
    probe = _probe_cad_object(obj)
    state.cad_probe.append(cast(CadProbe, probe))
    state.coil_plane_bboxes.append((request.pcb["id"], "XY", probe["bbox"]))
    violations = _bbox_violations(
        object_name=object_name,
        bbox=probe["bbox"],
        region_kind="tx_region_dd",
        region_min=tx_dd_scene["region_min"],
        region_max=tx_dd_scene["region_max"],
    )
    if violations:
        state.placement_violations.extend(cast(list[RegionViolation], violations))
        first = violations[0]
        raise ValueError(
            f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
            f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
        )
    state.group_objects["tx_dd"].append(object_name)
    start_xyz = start_tail_far_midpoint if has_start_tail else cast(Point3, ((main_start_edge[0][0] + main_start_edge[1][0]) / 2.0, (main_start_edge[0][1] + main_start_edge[1][1]) / 2.0, (main_start_edge[0][2] + main_start_edge[1][2]) / 2.0))
    end_xyz = end_tail_far_midpoint if has_end_tail else cast(Point3, ((main_end_edge[0][0] + main_end_edge[1][0]) / 2.0, (main_end_edge[0][1] + main_end_edge[1][1]) / 2.0, (main_end_edge[0][2] + main_end_edge[1][2]) / 2.0))
    state.group_endpoints.append(
        cast(
            GroupEndpointEntry,
            {
                "group_kind": "tx_dd",
                "group_instance_index": instance_index,
                "board_id": request.pcb["id"],
                "start_xyz": start_xyz,
                "end_xyz": end_xyz,
                "start_label": half.start_label,
                "end_label": half.end_label,
                "present": True,
            },
        )
    )
    state.coil_polarity.append(
        cast(
            CoilPolaritySpec,
            {
                "group_kind": "tx_dd",
                "group_instance_index": instance_index,
                "board_id": request.pcb["id"],
                "dd_family": "tx_dd",
                "dd_pair_index": layer_index,
                "instance_side": half.instance_side,
                "current_direction": half.current_direction,
            },
        )
    )

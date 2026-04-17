from __future__ import annotations

from typing import cast

from peetsfea.aedt import Object3d
from peetsfea.types.manifest import EmPortAssignments, EmPorts

from ..build_state import DirectedLandingSection, Point3, StubFaceRef, _unset_directed_landing_section, _unset_edge2p, state_is_set
from ..rules.cad_probe import _object_name, _probe_cad_object
from ..rules.debug_checks import _bbox_violations
from ..rules.solid_ops import safe_unite
from .build_name_ops import (
    _replace_object_name_in_landing,
    _replace_object_name_in_map,
    _replace_object_name_in_tx_series_binding_inputs,
    _replace_object_name_in_txdd_start_stub_sources,
)
from .build_excitation_ops import _create_tx_semantic_port_if_needed
from .build_port_ops import _shift_edge_along_y
from .build_sheet_ops import _create_thickened_sheet_from_points
from .build_topology_ops import _anti_parallel_bridge_sheet_points
from .build_tx_terminals import (
    _create_tx_vertical_external_stub,
    _stub_center_from_anchor,
    _txdd_geometry_stub_sort_key,
    _txdd_stub_length_for_role,
    _txdd_stub_origin_z_for_role,
)
from .finalize_helpers import (
    _attach_bridge_stub_edge_to_landing,
    _attach_txdd_stub_to_semantic_bridge_landing,
    _points_match,
    _shift_edge_inward_along_x,
    _uses_tx_vertical_external_stub_bridge,
)
from .finalize_types import FinalizePlan
from ..tx_stub_faces import capture_stub_face_ref_from_object, remap_stub_face_ref_after_unite


_UNSET_LANDING = _unset_directed_landing_section()
_UNSET_POINT = cast(Point3, _unset_edge2p())


def _txdd_stub_role_by_source_index(source_idx: int) -> str:
    tx_stub_role_by_index = {0: "in_above", 1: "out_below", 2: "out_above", 3: "in_below"}
    return tx_stub_role_by_index[source_idx] if source_idx in tx_stub_role_by_index else f"aux_{source_idx}"


def _txdd_start_stub_source_parts(raw_source: tuple[object, ...]) -> tuple[Point3, float, str, Point3]:
    if len(raw_source) == 4:
        anchor_xyz, trace, source_object_name, inward_dir = raw_source
        return (
            cast(Point3, anchor_xyz),
            cast(float, trace),
            cast(str, source_object_name),
            cast(Point3, inward_dir),
        )
    anchor_xyz, trace, source_object_name = raw_source
    return (
        cast(Point3, anchor_xyz),
        cast(float, trace),
        cast(str, source_object_name),
        _UNSET_POINT,
    )


def _txdd_source_matches_landing(raw_source: tuple[object, ...], landing: DirectedLandingSection) -> bool:
    if not state_is_set(landing):
        return False
    anchor_xyz, _trace, source_object_name, _inward_dir = _txdd_start_stub_source_parts(raw_source)
    return source_object_name == landing["object_name"] and _points_match(anchor_xyz, landing["center"])


def _replace_object_name_in_tx_vertical_nodes(
    nodes: list[tuple[object, ...]],
    *,
    old_name: str,
    new_name: str,
) -> None:
    for node_index, raw_node in enumerate(nodes):
        (
            group_instance_index,
            object_name,
            start_xyz,
            end_xyz,
            y_center,
            trace,
            world_center_x,
            bridge_out_edge,
            bridge_in_edge,
        ) = raw_node
        if cast(str, object_name) != old_name:
            continue
        nodes[node_index] = (
            cast(int, group_instance_index),
            new_name,
            cast(Point3, start_xyz),
            cast(Point3, end_xyz),
            cast(float, y_center),
            cast(float, trace),
            cast(float, world_center_x),
            cast(tuple[Point3, Point3], bridge_out_edge),
            cast(tuple[Point3, Point3], bridge_in_edge),
        )


def _replace_object_name_in_anchor(anchor: object, *, old_name: str, new_name: str) -> None:
    if state_is_set(anchor) and cast(dict[str, object], anchor)["object_name"] == old_name:
        cast(dict[str, object], anchor)["object_name"] = new_name


def _replace_object_name_in_tx_path_state(
    plan: FinalizePlan,
    *,
    old_name: str,
    new_name: str,
) -> None:
    for nodes in plan.tx_vertical_nodes_by_board.values():
        _replace_object_name_in_tx_vertical_nodes(cast(list[tuple[object, ...]], nodes), old_name=old_name, new_name=new_name)
    _replace_object_name_in_map(plan.txdd_right_object_names, old_name=old_name, new_name=new_name)
    _replace_object_name_in_txdd_start_stub_sources(plan.txdd_start_stub_sources, old_name=old_name, new_name=new_name)
    _replace_object_name_in_landing(plan.txdd_global_right_bridge_landing, old_name=old_name, new_name=new_name)
    _replace_object_name_in_landing(plan.tx_vertical_global_outer_right_landing, old_name=old_name, new_name=new_name)
    _replace_object_name_in_landing(plan.tx_vertical_global_outer_left_landing, old_name=old_name, new_name=new_name)
    _replace_object_name_in_tx_series_binding_inputs(plan.tx_series_binding, old_name=old_name, new_name=new_name)
    _replace_object_name_in_anchor(plan.txdd_global_right_bridge_anchor, old_name=old_name, new_name=new_name)
    _replace_object_name_in_anchor(plan.tx_vertical_global_outer_right_anchor, old_name=old_name, new_name=new_name)
    _replace_object_name_in_anchor(plan.tx_vertical_global_outer_left_anchor, old_name=old_name, new_name=new_name)


def _landing_stub_face_ref(landing: DirectedLandingSection) -> StubFaceRef:
    assert "stub_face_ref" in landing, f"landing requires stub_face_ref (object_name={landing['object_name']})"
    return cast(StubFaceRef, landing["stub_face_ref"])


def _iter_tx_path_landings(plan: FinalizePlan) -> tuple[DirectedLandingSection, ...]:
    landings: list[DirectedLandingSection] = [
        plan.txdd_global_right_bridge_landing,
        plan.tx_vertical_global_outer_right_landing,
        plan.tx_vertical_global_outer_left_landing,
    ]
    if state_is_set(plan.tx_series_binding):
        landings.extend(
            [
                plan.tx_series_binding.feed_in,
                plan.tx_series_binding.feed_out,
                plan.tx_series_binding.inter_half_exit,
                plan.tx_series_binding.inter_half_entry,
                plan.tx_series_binding.series_entry,
                plan.tx_series_binding.series_exit,
            ]
        )
    return tuple(landing for landing in landings if state_is_set(landing))


def _remap_tx_path_stub_face_refs_after_unite(plan: FinalizePlan, *, united_name: str) -> None:
    for landing in _iter_tx_path_landings(plan):
        if landing["terminal_role"] not in ("feed_in", "feed_out"):
            continue
        if "stub_face_ref" not in landing:
            continue
        landing["stub_face_ref"] = remap_stub_face_ref_after_unite(
            modeler=plan.modeler,
            united_object_name=united_name,
            face_ref=_landing_stub_face_ref(landing),
            context=f"tx unify stub-face remap ({landing['terminal_role']})",
        )


def _txdd_plan_is_single_layer(plan: FinalizePlan) -> bool:
    txdd_layer_keys = set(plan.txdd_right_object_names.keys()) | set(plan.txdd_right_a_points.keys())
    return 1 not in txdd_layer_keys


def _resolve_txdd_start_stub_roles(
    *,
    plan: FinalizePlan,
    ordered_sources: list[tuple[object, ...]],
) -> list[str]:
    if not state_is_set(plan.tx_series_binding):
        return [_txdd_stub_role_by_source_index(source_idx) for source_idx, _ in enumerate(ordered_sources)]
    if not plan.tx_series_binding.has("feed_in") or not plan.tx_series_binding.has("feed_out"):
        return [_txdd_stub_role_by_source_index(source_idx) for source_idx, _ in enumerate(ordered_sources)]

    assigned_roles = [""] * len(ordered_sources)
    used_indices: set[int] = set()
    feed_in = plan.tx_series_binding.require("feed_in")
    is_single_layer_txdd = _txdd_plan_is_single_layer(plan)
    semantic_role_targets: list[tuple[DirectedLandingSection, str]] = [
        (
            feed_in,
            "in_below"
            if feed_in["dd_family"] == "tx_dd" and feed_in["side"] == "right" and is_single_layer_txdd
            else "in_above",
        )
    ]
    if plan.tx_series_binding.has("inter_half_exit"):
        inter_half_exit = plan.tx_series_binding.require("inter_half_exit")
        semantic_role_targets.append(
            (
                inter_half_exit,
                "out_above"
                if inter_half_exit["dd_family"] == "tx_dd" and inter_half_exit["side"] == "right" and is_single_layer_txdd
                else "out_below",
            )
        )
    if plan.tx_series_binding.has("inter_half_entry"):
        inter_half_entry = plan.tx_series_binding.require("inter_half_entry")
        semantic_role_targets.append(
            (
                inter_half_entry,
                "in_above"
                if inter_half_entry["dd_family"] == "tx_dd" and inter_half_entry["side"] == "left" and is_single_layer_txdd
                else "in_below",
            )
        )
    feed_out = plan.tx_series_binding.require("feed_out")
    semantic_role_targets.append(
        (
            feed_out,
            "out_below"
            if feed_out["dd_family"] == "tx_dd" and feed_out["side"] == "left" and is_single_layer_txdd
            else "out_above",
        )
    )

    for landing, stub_role in semantic_role_targets:
        for source_idx, raw_source in enumerate(ordered_sources):
            if source_idx in used_indices:
                continue
            if _txdd_source_matches_landing(raw_source, landing):
                assigned_roles[source_idx] = stub_role
                used_indices.add(source_idx)
                break

    remaining_roles: list[str] = []
    for source_idx, _raw_source in enumerate(ordered_sources):
        default_role = _txdd_stub_role_by_source_index(source_idx)
        if default_role in assigned_roles:
            continue
        remaining_roles.append(default_role)

    remaining_role_index = 0
    for source_idx, _raw_source in enumerate(ordered_sources):
        if source_idx in used_indices:
            continue
        if remaining_role_index >= len(remaining_roles):
            assigned_roles[source_idx] = _txdd_stub_role_by_source_index(source_idx)
            continue
        assigned_roles[source_idx] = remaining_roles[remaining_role_index]
        remaining_role_index += 1

    return assigned_roles


def _apply_section_bridge(
    plan: FinalizePlan,
    *,
    dd_section,
    tx_vertical_section,
    bridge_name: str,
) -> None:
    bridge_sheet_points = _anti_parallel_bridge_sheet_points(
        dd_section=dd_section,
        vertical_section=tx_vertical_section,
    )
    bridge_obj_name, bridge_obj = _create_thickened_sheet_from_points(
        modeler=plan.modeler,
        sheet_points=bridge_sheet_points,
        sheet_name=bridge_name,
        thickness=(plan.cu_thickness * 1.5),
    )
    plan.object_names.append(bridge_obj_name)
    plan.group_objects["tx_dd"].append(bridge_obj_name)
    plan.cad_probe.append(_probe_cad_object(bridge_obj))


def _apply_tx_vertical_stage(plan: FinalizePlan, *, object_name_tag: str, txdd_is_single_layer: bool) -> None:
    if state_is_set(plan.tx_vertical_global_outer_right_landing) and plan.tx_vertical_global_outer_right_landing["dd_family"] == "none":
        old_right_name = plan.tx_vertical_global_outer_right_landing["object_name"]
        united_right_name = _create_tx_vertical_external_stub(
            modeler=plan.modeler,
            design_id=plan.design_id,
            terminal=plan.tx_vertical_global_outer_right_landing,
            stub_role="in",
            cu_thickness=plan.cu_thickness,
            group_objects=plan.group_objects,
            object_names=plan.object_names,
            cad_probe=plan.cad_probe,
        )
        if state_is_set(plan.tx_series_binding) and plan.tx_series_binding.has("series_entry"):
            series_entry = plan.tx_series_binding.require("series_entry")
            if (
                series_entry["object_name"] == old_right_name
                and _points_match(series_entry["center"], plan.tx_vertical_global_outer_right_landing["center"])
                and "stub_face_ref" in plan.tx_vertical_global_outer_right_landing
            ):
                series_entry["stub_face_ref"] = plan.tx_vertical_global_outer_right_landing["stub_face_ref"]
        _replace_object_name_in_landing(plan.tx_vertical_global_outer_right_landing, old_name=old_right_name, new_name=united_right_name)
        if state_is_set(plan.tx_series_binding) and plan.tx_series_binding.has("series_entry"):
            _replace_object_name_in_landing(plan.tx_series_binding.require("series_entry"), old_name=old_right_name, new_name=united_right_name)
    if state_is_set(plan.tx_vertical_global_outer_left_landing) and plan.tx_vertical_global_outer_left_landing["dd_family"] == "none":
        old_left_name = plan.tx_vertical_global_outer_left_landing["object_name"]
        united_left_name = _create_tx_vertical_external_stub(
            modeler=plan.modeler,
            design_id=plan.design_id,
            terminal=plan.tx_vertical_global_outer_left_landing,
            stub_role="out",
            cu_thickness=plan.cu_thickness,
            group_objects=plan.group_objects,
            object_names=plan.object_names,
            cad_probe=plan.cad_probe,
        )
        if state_is_set(plan.tx_series_binding) and plan.tx_series_binding.has("series_exit"):
            series_exit = plan.tx_series_binding.require("series_exit")
            if (
                series_exit["object_name"] == old_left_name
                and _points_match(series_exit["center"], plan.tx_vertical_global_outer_left_landing["center"])
                and "stub_face_ref" in plan.tx_vertical_global_outer_left_landing
            ):
                series_exit["stub_face_ref"] = plan.tx_vertical_global_outer_left_landing["stub_face_ref"]
        _replace_object_name_in_landing(plan.tx_vertical_global_outer_left_landing, old_name=old_left_name, new_name=united_left_name)
        if state_is_set(plan.tx_series_binding) and plan.tx_series_binding.has("series_exit"):
            _replace_object_name_in_landing(plan.tx_series_binding.require("series_exit"), old_name=old_left_name, new_name=united_left_name)
    if txdd_is_single_layer:
        for (_board_id, board_idx), nodes in plan.tx_vertical_nodes_by_board.items():
            if len(nodes) < 2:
                continue
            sorted_nodes = sorted(nodes, key=lambda node: node[4])
            for idx in range(len(sorted_nodes) - 1):
                source_index, _source_name, _, _, _, source_trace, source_center_x, source_bridge_out_edge, _ = sorted_nodes[idx]
                target_index, _target_name, _, _, _, target_trace, target_center_x, _, target_bridge_in_edge = sorted_nodes[idx + 1]
                if abs(source_trace - target_trace) > 1e-9:
                    raise ValueError(
                        "tx_vertical bridge trace mismatch between adjacent nodes "
                        f"(source_index={source_index}, target_index={target_index}, "
                        f"source_trace={source_trace}, target_trace={target_trace})"
                    )
                shifted_source_bridge_out_edge = _shift_edge_inward_along_x(edge=source_bridge_out_edge, center_x=source_center_x, cu_thickness_mm=plan.cu_thickness)
                shifted_target_bridge_in_edge = _shift_edge_inward_along_x(edge=target_bridge_in_edge, center_x=target_center_x, cu_thickness_mm=plan.cu_thickness)
                source_edge_0, source_edge_1 = shifted_source_bridge_out_edge
                target_edge_0, target_edge_1 = _shift_edge_along_y(shifted_target_bridge_in_edge, delta_y=plan.cu_thickness)
                bridge_sheet_points = [
                    [source_edge_0[0], source_edge_0[1], source_edge_0[2]],
                    [source_edge_1[0], source_edge_1[1], source_edge_1[2]],
                    [target_edge_1[0], target_edge_1[1], target_edge_1[2]],
                    [target_edge_0[0], target_edge_0[1], target_edge_0[2]],
                ]
                bridge_obj_name, bridge_obj = _create_thickened_sheet_from_points(
                    modeler=plan.modeler,
                    sheet_points=bridge_sheet_points,
                    sheet_name=f"bridge_tx_vertical_link_g{source_index}_to_g{target_index}_b{board_idx}_{object_name_tag}"[:60],
                    thickness=(plan.cu_thickness * 2.0),
                )
                plan.object_names.append(bridge_obj_name)
                plan.group_objects["tx_vertical"].append(bridge_obj_name)
                bridge_probe = _probe_cad_object(bridge_obj)
                plan.cad_probe.append(bridge_probe)
                bridge_violations = _bbox_violations(
                    object_name=bridge_obj_name,
                    bbox=bridge_probe["bbox"],
                    region_kind="tx_region_vertical",
                    region_min=plan.tx_vertical_region_min,
                    region_max=plan.tx_vertical_region_max,
                )
                if bridge_violations:
                    plan.placement_violations.extend(bridge_violations)
                    first = bridge_violations[0]
                    raise ValueError(
                        f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
                        f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
                    )


def _apply_txdd_start_stub_stage(plan: FinalizePlan, *, object_name_tag: str) -> None:
    for board_id, sources in sorted(plan.txdd_start_stub_sources.items()):
        if not sources:
            continue
        ordered_sources = [cast(tuple[object, ...], source) for source in sorted(sources, key=_txdd_geometry_stub_sort_key)]
        stub_roles = _resolve_txdd_start_stub_roles(plan=plan, ordered_sources=ordered_sources)
        for source_idx, raw_source in enumerate(ordered_sources):
            anchor_xyz, trace, source_object_name, inward_dir = _txdd_start_stub_source_parts(raw_source)
            if trace <= 0.0:
                raise ValueError(
                    "tx_dd start stub source trace must be > 0 "
                    f"(board_id={board_id}, source_idx={source_idx}, trace={trace})"
                )
            stub_center_xyz = (
                anchor_xyz
                if not state_is_set(inward_dir)
                else _stub_center_from_anchor(anchor_xyz=anchor_xyz, trace=trace, inward_dir=inward_dir)
            )
            stub_role = stub_roles[source_idx]
            stub_length = _txdd_stub_length_for_role(stub_role)
            stub_origin_z = _txdd_stub_origin_z_for_role(stub_center_z=stub_center_xyz[2], stub_role=stub_role, stub_length=stub_length)
            stub_origin = [stub_center_xyz[0] - (trace / 2.0), stub_center_xyz[1] - (trace / 2.0), stub_origin_z]
            stub_sizes = [trace, trace, stub_length]
            stub_name = f"txs_{stub_role}_{object_name_tag}"
            stub_created = plan.modeler.create_box(origin=stub_origin, sizes=stub_sizes, name=stub_name, material="copper")
            if not stub_created:
                raise ValueError(
                    "tx_dd start stub creation failed "
                    f"(name={stub_name}, source={source_object_name}, origin={stub_origin}, sizes={stub_sizes})"
                )
            stub_obj = cast(Object3d, stub_created)
            stub_object_name = _object_name(stub_obj)
            stub_face_ref = capture_stub_face_ref_from_object(
                modeler=plan.modeler,
                object_name=stub_object_name,
                expected_face_center=(
                    stub_center_xyz[0],
                    stub_center_xyz[1],
                    stub_origin_z + (stub_length if stub_role.endswith("_above") else 0.0),
                ),
                face_kind="tx_dd_xy",
                stub_role=stub_role,
                context="tx_dd start stub face capture",
            )
            plan.object_names.append(stub_object_name)
            plan.group_objects["tx_dd"].append(stub_object_name)
            plan.cad_probe.append(_probe_cad_object(stub_obj))
            created_edge = (
                (stub_center_xyz[0] - (trace / 2.0), stub_center_xyz[1] + (trace / 2.0), stub_center_xyz[2]),
                (stub_center_xyz[0] + (trace / 2.0), stub_center_xyz[1] + (trace / 2.0), stub_center_xyz[2]),
            )
            _attach_bridge_stub_edge_to_landing(
                plan.txdd_global_right_bridge_landing,
                source_object_name=source_object_name,
                anchor_xyz=anchor_xyz,
                edge=created_edge,
                stub_face_ref=stub_face_ref,
            )
            _attach_txdd_stub_to_semantic_bridge_landing(
                plan.txdd_global_right_bridge_landing,
                source_object_name=source_object_name,
                stub_role=stub_role,
                edge=created_edge,
                stub_face_ref=stub_face_ref,
            )
            if state_is_set(plan.tx_series_binding):
                _attach_bridge_stub_edge_to_landing(
                    plan.tx_series_binding.feed_in,
                    source_object_name=source_object_name,
                    anchor_xyz=anchor_xyz,
                    edge=created_edge,
                    stub_face_ref=stub_face_ref,
                )
                _attach_bridge_stub_edge_to_landing(
                    plan.tx_series_binding.feed_out,
                    source_object_name=source_object_name,
                    anchor_xyz=anchor_xyz,
                    edge=created_edge,
                    stub_face_ref=stub_face_ref,
                )
                _attach_bridge_stub_edge_to_landing(
                    plan.tx_series_binding.inter_half_exit,
                    source_object_name=source_object_name,
                    anchor_xyz=anchor_xyz,
                    edge=created_edge,
                    stub_face_ref=stub_face_ref,
                )
                _attach_bridge_stub_edge_to_landing(
                    plan.tx_series_binding.inter_half_entry,
                    source_object_name=source_object_name,
                    anchor_xyz=anchor_xyz,
                    edge=created_edge,
                    stub_face_ref=stub_face_ref,
                )
                _attach_txdd_stub_to_semantic_bridge_landing(
                    plan.tx_series_binding.inter_half_exit,
                    source_object_name=source_object_name,
                    stub_role=stub_role,
                    edge=created_edge,
                    stub_face_ref=stub_face_ref,
                )
                _attach_txdd_stub_to_semantic_bridge_landing(
                    plan.tx_series_binding.inter_half_entry,
                    source_object_name=source_object_name,
                    stub_role=stub_role,
                    edge=created_edge,
                    stub_face_ref=stub_face_ref,
                )


def _apply_tx_chain_bridge_stage(plan: FinalizePlan, *, object_name_tag: str, txdd_is_single_layer: bool) -> None:
    if not txdd_is_single_layer:
        return
    if not state_is_set(plan.tx_series_binding):
        return
    if not plan.tx_series_binding.has("inter_half_exit") or not plan.tx_series_binding.has("inter_half_entry"):
        return
    from .build_tx_bridges import _apply_tx_chain_bridge, _apply_tx_dd_direct_bridge

    if not state_is_set(plan.tx_vertical_global_outer_right_landing) or not state_is_set(plan.tx_vertical_global_outer_left_landing):
        _apply_tx_dd_direct_bridge(
            modeler=plan.modeler,
            cu_thickness=plan.cu_thickness,
            first_landing=plan.tx_series_binding.require("inter_half_exit"),
            second_landing=plan.tx_series_binding.require("inter_half_entry"),
            group_objects=plan.group_objects,
            object_names=plan.object_names,
            cad_probe=plan.cad_probe,
            bridge_name=f"bridge_tx_right_out_to_left_in_{object_name_tag}",
            bridge_error_context="tx dd direct bridge right_out_to_left_in",
            region_min=plan.tx_vertical_region_min,
            region_max=plan.tx_vertical_region_max,
            placement_violations=plan.placement_violations,
        )
        return

    _apply_tx_chain_bridge(
        modeler=plan.modeler,
        cu_thickness=plan.cu_thickness,
        tx_dd_landing=plan.tx_series_binding.require("inter_half_exit"),
        tx_vertical_landing=plan.tx_vertical_global_outer_right_landing,
        group_objects=plan.group_objects,
        object_names=plan.object_names,
        cad_probe=plan.cad_probe,
        bridge_name=f"bridge_tx_right_out_to_vertical_in_{object_name_tag}",
        bridge_error_context="tx chain bridge right_out_to_vertical_in",
        region_min=plan.tx_vertical_region_min,
        region_max=plan.tx_vertical_region_max,
        placement_violations=plan.placement_violations,
    )
    _apply_tx_chain_bridge(
        modeler=plan.modeler,
        cu_thickness=plan.cu_thickness,
        tx_dd_landing=plan.tx_series_binding.require("inter_half_entry"),
        tx_vertical_landing=plan.tx_vertical_global_outer_left_landing,
        group_objects=plan.group_objects,
        object_names=plan.object_names,
        cad_probe=plan.cad_probe,
        bridge_name=f"bridge_tx_vertical_out_to_left_in_{object_name_tag}",
        bridge_error_context="tx chain bridge vertical_out_to_left_in",
        region_min=plan.tx_vertical_region_min,
        region_max=plan.tx_vertical_region_max,
        placement_violations=plan.placement_violations,
    )


def _apply_tx_global_unite_stage(plan: FinalizePlan) -> None:
    live_tx_targets: list[str] = []
    for name in sorted(set(plan.group_objects["tx_dd"] + plan.group_objects["tx_vertical"])):
        try:
            faces = plan.modeler.get_object_faces(name)
        except Exception:
            continue
        if faces:
            live_tx_targets.append(name)
    if not live_tx_targets:
        return
    united_name = safe_unite(
        modeler=plan.modeler,
        targets=live_tx_targets,
        error_context="final tx copper global unite",
    )
    plan.group_objects["tx_dd"] = [united_name]
    plan.group_objects["tx_vertical"] = [united_name]
    plan.object_names[:] = [name for name in plan.object_names if name not in live_tx_targets]
    if united_name not in plan.object_names:
        plan.object_names.append(united_name)
    for old_name in live_tx_targets:
        if old_name == united_name:
            continue
        _replace_object_name_in_tx_path_state(plan, old_name=old_name, new_name=united_name)
    _remap_tx_path_stub_face_refs_after_unite(plan, united_name=united_name)


def _apply_tx_semantic_port_stage(
    plan: FinalizePlan,
    *,
    resolved_ports: EmPorts,
    resolved_port_assignments: EmPortAssignments,
) -> None:
    if not state_is_set(plan.tx_series_binding):
        return
    if not plan.tx_series_binding.has("feed_in") or not plan.tx_series_binding.has("feed_out"):
        return
    _create_tx_semantic_port_if_needed(
        modeler=plan.modeler,
        hfss=plan.hfss,
        design_id=plan.design_id,
        tx_series_binding=plan.tx_series_binding,
        txdd_right_object_names=plan.txdd_right_object_names,
        group_objects=plan.group_objects,
        object_names=plan.object_names,
        resolved_ports=resolved_ports,
        resolved_port_assignments=resolved_port_assignments,
    )

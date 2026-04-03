from __future__ import annotations

import json
import os

from peetsfea.aedt.proxies import set_object_color, set_object_transparency
from peetsfea.console_log import info_json

from .build_common import *
from .build_sheet_ops import _fr4_box_from_plane_bbox
from .build_via_ops import _tx_dd_xy_tools

_NEO_TX_DD_FR4_PREFIX = "neo_fr4_tx_dd_"
_FR4_EPOXY_GREEN = (0, 128, 0)
_FR4_TRANSPARENCY = 0.85


def _fr4_group_board_id(
    *,
    board_id: str,
    plane: Literal["XY", "YZ", "ZX"],
    tx_board_ids: set[str],
) -> str:
    if board_id in tx_board_ids:
        return board_id
    if plane == "XY":
        return board_id
    return "rx_shared"


def _register_prebuilt_fr4_metadata(
    *,
    object_names: list[str],
    fr4_object_names: list[str],
    fr4_role_by_name: dict[str, Literal["tx", "rx"]],
    fr4_plane_by_name: dict[str, Literal["XY", "YZ", "ZX"]],
) -> None:
    live_object_names = set(object_names)
    for fr4_name in sorted(set(fr4_object_names)):
        if not fr4_name.startswith(_NEO_TX_DD_FR4_PREFIX):
            continue
        if fr4_name not in live_object_names:
            raise ValueError(f"Prebuilt tx_dd neo FR4 must exist in object registry (fr4_name={fr4_name})")
        fr4_role_by_name[fr4_name] = "tx"
        fr4_plane_by_name[fr4_name] = "XY"


def _live_model_object_names(
    *,
    modeler: Modeler3D,
    candidate_names: list[str],
) -> set[str]:
    live_names: set[str] = set()
    for name in candidate_names:
        try:
            faces = modeler.get_object_faces(name)
        except Exception:
            continue
        if faces:
            live_names.add(name)
    return live_names


def _debug_fr4_subtract_state(
    *,
    design_id: str,
    fr4_name: str,
    tool_name: str,
    fr4_plane: Literal["XY", "YZ", "ZX"],
    fr4_role: Literal["tx", "rx"],
    tx_tools: list[str],
    rx_tools: list[str],
    object_names: list[str],
    fr4_object_names: list[str],
    group_objects: GroupObjects,
    modeler: Modeler3D,
) -> None:
    if os.environ.get("PEETSFEA_DEBUG") != "1":
        return
    fr4_exists_in_registry = fr4_name in object_names
    tool_exists_in_registry = tool_name in object_names
    fr4_faces: list[int] = []
    tool_faces: list[int] = []
    fr4_face_error = ""
    tool_face_error = ""
    try:
        fr4_faces = modeler.get_object_faces(fr4_name)
    except Exception as exc:
        fr4_face_error = f"{type(exc).__name__}: {exc}"
    try:
        tool_faces = modeler.get_object_faces(tool_name)
    except Exception as exc:
        tool_face_error = f"{type(exc).__name__}: {exc}"
    payload = {
        "event": "fr4_subtract_preflight",
        "design_id": design_id,
        "fr4_name": fr4_name,
        "tool_name": tool_name,
        "fr4_plane": fr4_plane,
        "fr4_role": fr4_role,
        "fr4_exists_in_registry": fr4_exists_in_registry,
        "tool_exists_in_registry": tool_exists_in_registry,
        "fr4_face_count": len(fr4_faces),
        "tool_face_count": len(tool_faces),
        "fr4_face_error": fr4_face_error,
        "tool_face_error": tool_face_error,
        "tx_tools": tx_tools,
        "rx_tools": rx_tools,
        "fr4_object_names": sorted(set(fr4_object_names)),
        "group_tx_dd": sorted(set(group_objects["tx_dd"])),
        "group_tx_vertical": sorted(set(group_objects["tx_vertical"])),
        "group_rx_dd": sorted(set(group_objects["rx_dd"])),
        "object_names_count": len(object_names),
    }
    info_json(payload)


def _debug_fr4_subtract_result(
    *,
    design_id: str,
    fr4_name: str,
    tool_name: str,
    subtract_result: object,
    modeler: Modeler3D,
) -> None:
    if os.environ.get("PEETSFEA_DEBUG") != "1":
        return
    post_fr4_faces: list[int] = []
    post_fr4_error = ""
    try:
        post_fr4_faces = modeler.get_object_faces(fr4_name)
    except Exception as exc:
        post_fr4_error = f"{type(exc).__name__}: {exc}"
    payload = {
        "event": "fr4_subtract_post",
        "design_id": design_id,
        "fr4_name": fr4_name,
        "tool_name": tool_name,
        "subtract_result_type": type(subtract_result).__name__,
        "subtract_result_repr": repr(subtract_result),
        "post_fr4_face_count": len(post_fr4_faces),
        "post_fr4_error": post_fr4_error,
    }
    info_json(payload)


def _finalize_fr4(
    *,
    modeler: Modeler3D,
    design_id: str,
    pcb_thickness: float,
    tx_board_ids: set[str],
    txdd_right_object_names: dict[int, str],
    group_objects: GroupObjects,
    object_names: list[str],
    cad_probe: list[CadProbe],
    coil_plane_bboxes: list[tuple[str, Literal["XY", "YZ", "ZX"], list[float]]],
    fr4_object_names: list[str],
    tx_vertical_fr4_names: list[str],
    resolved_ports: EmPorts,
    resolved_port_assignments: EmPortAssignments,
) -> tuple[list[str], list[str], EmPorts, EmPortAssignments]:
    object_name_tag = object_name_tag_from_design_id(design_id)
    if len(resolved_ports["tx"]) > 1:
        raise ValueError(f"type1 tx excitation contract expects exactly 1 TX excitation (actual={resolved_ports['tx']})")
    if len(resolved_ports["rx"]) > 1:
        raise ValueError(f"type1 rx excitation contract expects exactly 1 RX excitation (actual={resolved_ports['rx']})")

    eps_len = 1e-6
    grouped_plane_bboxes: dict[tuple[str, Literal["XY", "YZ", "ZX"], int], list[float]] = {}
    fr4_role_by_name: dict[str, Literal["tx", "rx"]] = {}
    fr4_plane_by_name: dict[str, Literal["XY", "YZ", "ZX"]] = {}
    _register_prebuilt_fr4_metadata(
        object_names=object_names,
        fr4_object_names=fr4_object_names,
        fr4_role_by_name=fr4_role_by_name,
        fr4_plane_by_name=fr4_plane_by_name,
    )
    for board_id, plane, bbox in coil_plane_bboxes:
        if len(bbox) < 6:
            continue
        grouped_board_id = _fr4_group_board_id(
            board_id=board_id,
            plane=plane,
            tx_board_ids=tx_board_ids,
        )
        if plane == "XY":
            axis_center = (bbox[2] + bbox[5]) / 2.0
            layer_key = int(round(axis_center / eps_len))
        elif plane == "YZ":
            axis_center = (bbox[0] + bbox[3]) / 2.0
            layer_key = int(round(axis_center / eps_len))
        else:
            axis_center = (bbox[1] + bbox[4]) / 2.0
            layer_key = int(round(axis_center / eps_len))
        key = (grouped_board_id, plane, layer_key)
        if key not in grouped_plane_bboxes:
            grouped_plane_bboxes[key] = list(bbox[:6])
        else:
            existing = grouped_plane_bboxes[key]
            existing[0] = min(existing[0], bbox[0])
            existing[1] = min(existing[1], bbox[1])
            existing[2] = min(existing[2], bbox[2])
            existing[3] = max(existing[3], bbox[3])
            existing[4] = max(existing[4], bbox[4])
            existing[5] = max(existing[5], bbox[5])

    for layer_idx, ((grouped_board_id, plane, _), bbox) in enumerate(sorted(grouped_plane_bboxes.items())):
        origin, sizes = _fr4_box_from_plane_bbox(
            plane=plane,
            bbox=bbox,
            pcb_thickness=pcb_thickness,
            overlap_mm=FR4_SUBTRACT_OVERLAP_MM,
            eps_len=eps_len,
        )

        substrate_name = f"fr4_{grouped_board_id}_{plane.lower()}_{layer_idx}_{object_name_tag}"
        substrate = cast(
            Object3d,
            raise_on_false(
                modeler.create_box(origin=origin, sizes=sizes, name=substrate_name, material="FR4_epoxy"),
                operation="create_box",
                context={"name": substrate_name, "material": "FR4_epoxy"},
            ),
        )
        set_object_color(substrate, color=_FR4_EPOXY_GREEN)
        set_object_transparency(substrate, transparency=_FR4_TRANSPARENCY)
        substrate_object_name = _object_name(substrate)
        substrate_role: Literal["tx", "rx"] = "tx" if grouped_board_id in tx_board_ids else "rx"
        object_names.append(substrate_object_name)
        fr4_object_names.append(substrate_object_name)
        fr4_role_by_name[substrate_object_name] = substrate_role
        fr4_plane_by_name[substrate_object_name] = plane
        if plane != "XY" and substrate_role == "tx":
            tx_vertical_fr4_names.append(substrate_object_name)
        cad_probe.append(_probe_cad_object(substrate))

    if len(tx_vertical_fr4_names) > 1:
        tx_vertical_fr4_targets = sorted(set(tx_vertical_fr4_names))
        first_tx_vertical_fr4 = tx_vertical_fr4_targets[0]
        assert first_tx_vertical_fr4 in fr4_plane_by_name, "tx_vertical FR4 plane metadata is missing"
        tx_vertical_fr4_plane = fr4_plane_by_name[first_tx_vertical_fr4]
        tx_vertical_fr4_united_name = safe_unite(
            modeler=modeler,
            targets=tx_vertical_fr4_targets,
            error_context="tx vertical FR4 group",
        )
        fr4_object_names[:] = [name for name in fr4_object_names if name not in tx_vertical_fr4_targets[1:]]
        for removed_name in tx_vertical_fr4_targets[1:]:
            fr4_role_by_name.pop(removed_name, None)
            fr4_plane_by_name.pop(removed_name, None)
        if tx_vertical_fr4_united_name not in fr4_object_names:
            fr4_object_names.append(tx_vertical_fr4_united_name)
        fr4_role_by_name[tx_vertical_fr4_united_name] = "tx"
        fr4_plane_by_name[tx_vertical_fr4_united_name] = tx_vertical_fr4_plane
        object_names[:] = [name for name in object_names if name not in tx_vertical_fr4_targets[1:]]
        if tx_vertical_fr4_united_name not in object_names:
            object_names.append(tx_vertical_fr4_united_name)

    live_object_names = _live_model_object_names(modeler=modeler, candidate_names=object_names)
    tx_tools = sorted(
        name for name in set(group_objects["tx_dd"] + group_objects["tx_vertical"]) if name in live_object_names
    )
    if not tx_tools:
        tx_tools = _tx_dd_xy_tools(
            txdd_right_object_names=txdd_right_object_names,
            group_objects=group_objects,
            live_object_names=live_object_names,
        )
    rx_tools = sorted(name for name in set(group_objects["rx_dd"]) if name in live_object_names)
    for fr4_name in sorted(set(fr4_object_names)):
        assert fr4_name in fr4_role_by_name, f"FR4 role metadata is missing for {fr4_name}"
        assert fr4_name in fr4_plane_by_name, f"FR4 plane metadata is missing for {fr4_name}"
        fr4_role = fr4_role_by_name[fr4_name]
        fr4_plane = fr4_plane_by_name[fr4_name]
        fr4_tools = tx_tools if fr4_role == "tx" else rx_tools
        if not fr4_tools:
            raise ValueError(
                "No live tools found for FR4 subtraction "
                f"(plane={fr4_plane}, role={fr4_role}, fr4_name={fr4_name}, "
                f"tx_tools={tx_tools}, rx_tools={rx_tools})"
            )
        fr4_tools_to_subtract = [tool_name for tool_name in fr4_tools if tool_name != fr4_name]
        if not fr4_tools_to_subtract:
            raise ValueError(
                "No subtractable tools found for FR4 subtraction "
                f"(plane={fr4_plane}, role={fr4_role}, fr4_name={fr4_name}, fr4_tools={fr4_tools})"
            )
        for tool_name in fr4_tools_to_subtract:
            _debug_fr4_subtract_state(
                design_id=design_id,
                fr4_name=fr4_name,
                tool_name=tool_name,
                fr4_plane=fr4_plane,
                fr4_role=fr4_role,
                tx_tools=tx_tools,
                rx_tools=rx_tools,
                object_names=object_names,
                fr4_object_names=fr4_object_names,
                group_objects=group_objects,
                modeler=modeler,
            )
        subtract_ok = modeler.subtract(blank_list=[fr4_name], tool_list=fr4_tools_to_subtract, keep_originals=True)
        _debug_fr4_subtract_result(
            design_id=design_id,
            fr4_name=fr4_name,
            tool_name="|".join(fr4_tools_to_subtract),
            subtract_result=subtract_ok,
            modeler=modeler,
        )
        if not subtract_ok:
            raise ValueError(
                "Failed to subtract copper solids from FR4 substrate "
                f"(plane={fr4_plane}, role={fr4_role}, fr4_name={fr4_name}, "
                f"tool_names={fr4_tools_to_subtract}, overlap_mm={FR4_SUBTRACT_OVERLAP_MM})"
            )

    return object_names, fr4_object_names, resolved_ports, resolved_port_assignments


__all__ = ["_finalize_fr4"]

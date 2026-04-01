from __future__ import annotations

from typing import cast

from peetsfea.aedt import Object3d

from ..build_state import RxDdBackStubSource
from ..rx_stub_ports import (
    record_rx_dd_port_stub_back_face,
    resolve_rx_dd_port_edges_from_back_faces,
)
from ..rules.cad_probe import _object_name, _probe_cad_object
from ..rules.solid_ops import safe_unite
from .build_port_ops import (
    _create_terminal_lumped_port_and_capture_assignment_from_edge_ids,
    _find_matching_edge_id,
)
from .build_bridge_ops import (
    _apply_back_connect_stub_pair_bridge,
    _is_rxdd_connect_stub_endpoint,
    _is_rxdd_port_stub_endpoint,
    _rxdd_back_stub_origin_and_sizes,
    _rxdd_back_stub_sort_key,
    _rxdd_back_stub_source_parts,
    _rxdd_stub_attach_center_from_anchor,
)
from .build_common import RX_DD_CONNECT_ENDPOINT_LABELS, RX_DD_CONNECT_STUB_LEN_MM
from .finalize_types import FinalizePlan
from peetsfea.types.manifest import EmPortAssignments, EmPorts


def _apply_rxdd_back_stub_stage(
    plan: FinalizePlan,
    *,
    object_name_tag: str,
    resolved_ports: EmPorts,
    resolved_port_assignments: EmPortAssignments,
) -> None:
    sorted_rxdd_back_stub_sources = sorted(plan.rxdd_back_stub_sources, key=_rxdd_back_stub_sort_key)
    rxdd_connect_stub_sources: list[RxDdBackStubSource] = []
    rxdd_name_replacements: dict[str, str] = {}
    rxdd_port_stub_keys: dict[str, str] = {}

    def _resolve_rxdd_name(name: str) -> str:
        current = name
        for _ in range(10):
            if current not in rxdd_name_replacements:
                return current
            next_name = rxdd_name_replacements[current]
            if next_name == current:
                return current
            current = next_name
        raise ValueError(f"rx_dd replacement chain too deep (name={name})")

    for raw_source in sorted_rxdd_back_stub_sources:
        (
            board_id,
            instance_index,
            endpoint_label,
            anchor_xyz,
            trace,
            source_object_name_raw,
            has_inward_dir,
            inward_dir,
        ) = _rxdd_back_stub_source_parts(raw_source)
        source_object_name = _resolve_rxdd_name(source_object_name_raw)
        if _is_rxdd_connect_stub_endpoint(endpoint_label):
            if not has_inward_dir:
                rxdd_connect_stub_sources.append((board_id, instance_index, endpoint_label, anchor_xyz, trace, source_object_name))
            else:
                rxdd_connect_stub_sources.append(
                    (board_id, instance_index, endpoint_label, anchor_xyz, trace, source_object_name, inward_dir)
                )
            continue
        source_exists = (source_object_name in plan.object_names) or (source_object_name in plan.group_objects["rx_dd"])
        if not source_exists:
            raise ValueError(
                "rx_dd back stub source object missing "
                f"(board_id={board_id}, instance_index={instance_index}, endpoint={endpoint_label}, "
                f"source={source_object_name})"
            )
        stub_anchor_xyz = _rxdd_stub_attach_center_from_anchor(
            anchor_xyz=anchor_xyz,
            trace=trace,
            inward_dir=inward_dir,
            has_inward_dir=has_inward_dir,
        )
        stub_origin, stub_sizes = _rxdd_back_stub_origin_and_sizes(anchor_xyz=stub_anchor_xyz, trace=trace)
        stub_name = f"rxs_{board_id}_{instance_index}_{endpoint_label}"
        stub_created = plan.modeler.create_box(origin=stub_origin, sizes=stub_sizes, name=stub_name, material="copper")
        if not stub_created:
            raise ValueError(
                "rx_dd back stub creation failed "
                f"(name={stub_name}, source={source_object_name}, origin={stub_origin}, sizes={stub_sizes})"
            )
        stub_obj = cast(Object3d, stub_created)
        stub_object_name = _object_name(stub_obj)
        plan.object_names.append(stub_object_name)
        plan.group_objects["rx_dd"].append(stub_object_name)
        plan.cad_probe.append(_probe_cad_object(stub_obj))
        if _is_rxdd_port_stub_endpoint(endpoint_label):
            stub_back_face_key = record_rx_dd_port_stub_back_face(
                design_id=plan.design_id,
                board_id=board_id,
                instance_index=instance_index,
                endpoint_label=endpoint_label,
                origin=stub_origin,
                sizes=stub_sizes,
            )
            rxdd_port_stub_keys[endpoint_label] = stub_back_face_key
        unite_targets = [source_object_name, stub_object_name]
        united_name = safe_unite(
            modeler=plan.modeler,
            targets=unite_targets,
            error_context="rx_dd back port-stub with source conductor",
        )
        plan.group_objects["rx_dd"] = [name for name in plan.group_objects["rx_dd"] if name not in unite_targets[1:]]
        if united_name not in plan.group_objects["rx_dd"]:
            plan.group_objects["rx_dd"].append(united_name)
        plan.object_names[:] = [name for name in plan.object_names if name not in unite_targets[1:]]
        if united_name not in plan.object_names:
            plan.object_names.append(united_name)
        rxdd_name_replacements[source_object_name] = united_name
        rxdd_name_replacements[stub_object_name] = united_name

    _apply_back_connect_stub_pair_bridge(
        modeler=plan.modeler,
        design_id=plan.design_id,
        cu_thickness=plan.cu_thickness,
        sources=rxdd_connect_stub_sources,
        endpoint_labels=RX_DD_CONNECT_ENDPOINT_LABELS,
        stub_length_mm=RX_DD_CONNECT_STUB_LEN_MM,
        group_objects=plan.group_objects,
        group_key="rx_dd",
        object_names=plan.object_names,
        cad_probe=plan.cad_probe,
        bridge_name=(
            f"bridge_rx_dd_{RX_DD_CONNECT_ENDPOINT_LABELS[0].lower()}_to_"
            f"{RX_DD_CONNECT_ENDPOINT_LABELS[1].lower()}_{object_name_tag}"
        ),
        stub_name_prefix="rxc",
        stub_error_context="rx_dd d/B connect stub with source coils",
        bridge_error_context="rx_dd d/B YZ sheet bridge with connect stubs",
    )
    if "A" not in rxdd_port_stub_keys or "c" not in rxdd_port_stub_keys:
        return
    signal_stub_key = rxdd_port_stub_keys["A"]
    reference_stub_key = rxdd_port_stub_keys["c"]
    signal_edge, reference_edge = resolve_rx_dd_port_edges_from_back_faces(
        design_id=plan.design_id,
        signal_stub_key=signal_stub_key,
        reference_stub_key=reference_stub_key,
    )
    live_rx_object_names = sorted(set(plan.group_objects["rx_dd"]))
    if not live_rx_object_names:
        raise ValueError("rx semantic port assignment requires at least one live rx_dd object")
    signal_object_name, signal_edge_id = _find_matching_edge_id(
        modeler=plan.modeler,
        object_names=live_rx_object_names,
        target_edge=signal_edge,
        context="rx semantic port assignment signal",
    )
    reference_object_name, reference_edge_id = _find_matching_edge_id(
        modeler=plan.modeler,
        object_names=live_rx_object_names,
        target_edge=reference_edge,
        context="rx semantic port assignment reference",
    )
    port_assignment = _create_terminal_lumped_port_and_capture_assignment_from_edge_ids(
        hfss=plan.hfss,
        signal_object_name=signal_object_name,
        signal_edge_id=signal_edge_id,
        reference_object_name=reference_object_name,
        reference_edge_id=reference_edge_id,
        role="rx",
        context="rx semantic port assignment",
    )
    resolved_port_assignments["rx"].append(port_assignment)
    resolved_ports["rx"].append(port_assignment["excitation_name"])

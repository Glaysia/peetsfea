from __future__ import annotations

from .build_name_ops import _assert_tx_semantic_port_contract
from .build_port_ops import _create_terminal_lumped_port_and_capture_assignment_from_edge_ids
from .build_common import *
from ..build_state import StubFaceRef
from ..tx_stub_faces import edge_id_from_face_id


def _require_tx_feed_terminals(
    binding: _TxSeriesBindingInputs | _TxSeriesChainBinding,
) -> tuple[_DirectedLandingSection, _DirectedLandingSection]:
    if isinstance(binding, dict):
        return binding["feed_in"], binding["feed_out"]
    return binding.require("feed_in"), binding.require("feed_out")


def _require_stub_face_ref(
    *,
    terminal: _DirectedLandingSection,
    context: str,
) -> StubFaceRef:
    assert "stub_face_ref" in terminal, f"{context} requires stub_face_ref"
    return cast(StubFaceRef, terminal["stub_face_ref"])


def _create_tx_semantic_port_if_needed(
    *,
    modeler: Modeler3D,
    hfss: Hfss,
    design_id: str,
    tx_series_binding: _TxSeriesBindingInputs | _TxSeriesChainBinding,
    txdd_right_object_names: dict[int, str],
    group_objects: GroupObjects,
    object_names: list[str],
    resolved_ports: EmPorts,
    resolved_port_assignments: EmPortAssignments,
) -> None:
    _ = design_id
    conductor_name = _assert_tx_semantic_port_contract(
        binding=tx_series_binding,
        txdd_right_object_names=txdd_right_object_names,
        group_objects=group_objects,
        object_names=object_names,
        context="tx semantic port",
    )
    feed_in, feed_out = _require_tx_feed_terminals(tx_series_binding)
    signal_face_ref = _require_stub_face_ref(
        terminal=feed_in,
        context="tx semantic port feed_in",
    )
    reference_face_ref = _require_stub_face_ref(
        terminal=feed_out,
        context="tx semantic port feed_out",
    )
    if signal_face_ref["object_name"] != conductor_name or reference_face_ref["object_name"] != conductor_name:
        raise ValueError(
            "tx semantic port assignment requires feed face refs to resolve to final conductor "
            f"(signal_object={signal_face_ref['object_name']}, reference_object={reference_face_ref['object_name']}, conductor={conductor_name})"
        )
    signal_edge_id = edge_id_from_face_id(
        modeler=modeler,
        face_ref=signal_face_ref,
        edge_role="tx_port",
        context="tx semantic port assignment signal",
    )
    reference_edge_id = edge_id_from_face_id(
        modeler=modeler,
        face_ref=reference_face_ref,
        edge_role="tx_port",
        context="tx semantic port assignment reference",
    )
    port_assignment = _create_terminal_lumped_port_and_capture_assignment_from_edge_ids(
        hfss=hfss,
        signal_object_name=signal_face_ref["object_name"],
        signal_edge_id=signal_edge_id,
        reference_object_name=reference_face_ref["object_name"],
        reference_edge_id=reference_edge_id,
        role="tx",
        context="tx semantic port assignment",
    )
    resolved_port_assignments["tx"].append(port_assignment)
    resolved_ports["tx"].append(port_assignment["excitation_name"])


__all__ = ["_create_tx_semantic_port_if_needed"]

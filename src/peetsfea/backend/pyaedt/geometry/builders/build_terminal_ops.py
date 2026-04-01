from __future__ import annotations

from peetsfea.console_log import info

from .build_common import *
from .build_port_ops import _edge_midpoint, _edges_match, _tx_port_edge_sort_key
from .build_topology_ops import _landing_edge_length
from ..tx_stub_faces import capture_stub_face_ref_from_object, edge_points_from_edge_id

def _tx_terminal_trace(terminal: _DirectedLandingSection) -> float:
    trace = _landing_edge_length(terminal)
    if trace <= 1e-12:
        raise ValueError(
            "tx terminal contract violation: landing edge length must be > 0 "
            f"(role={terminal['terminal_role']}, object_name={terminal['object_name']})"
        )
    return trace

def _stub_center_from_anchor(
    *,
    anchor_xyz: _Point3,
    trace: float,
    inward_dir: _Point3,
    has_inward_dir: bool = True,
) -> _Point3:
    if trace <= 0.0:
        raise ValueError(f"stub trace must be > 0 (actual={trace})")
    if not has_inward_dir:
        return anchor_xyz
    half_trace = trace / 2.0
    return (
        anchor_xyz[0] + (inward_dir[0] * half_trace),
        anchor_xyz[1] + (inward_dir[1] * half_trace),
        anchor_xyz[2],
    )

def _txdd_geometry_stub_sort_key(source: _TxDdStartStubSource) -> tuple[int, float, float]:
    anchor_xyz = source[0]
    y_value = float(anchor_xyz[1])
    x_value = float(anchor_xyz[0])
    is_outer = abs(y_value) > abs(x_value)
    if y_value < 0.0 and is_outer:
        bucket = 0
    elif y_value > 0.0 and not is_outer:
        bucket = 1
    elif y_value < 0.0 and not is_outer:
        bucket = 2
    else:
        bucket = 3
    return (bucket, y_value, x_value)

def _txdd_stub_origin_z_for_role(*, stub_center_z: float, stub_role: str, stub_length: float) -> float:
    if stub_length <= 0.0:
        raise ValueError(f"tx_dd stub length must be > 0 (actual={stub_length})")
    if stub_role.endswith("_below"):
        return stub_center_z - stub_length
    if stub_role.endswith("_above"):
        return stub_center_z
    raise ValueError(f"tx_dd stub role must end with _below/_above (actual={stub_role})")

def _txdd_stub_length_for_role(stub_role: str) -> float:
    if stub_role.endswith("_below"):
        return TX_DD_START_STUB_LEN_BELOW_MM
    if stub_role.endswith("_above"):
        return TX_DD_START_STUB_LEN_MM
    raise ValueError(f"tx_dd stub role must end with _below/_above (actual={stub_role})")

def _tx_target_edge_must_be_external_stub_bottom_x_edge(
    *,
    target_edge: _Edge2P,
    context: str,
    tol: float = 1e-6,
) -> None:
    first, second = target_edge
    dx = abs(second[0] - first[0])
    dy = abs(second[1] - first[1])
    dz = abs(second[2] - first[2])
    if dx <= tol:
        raise ValueError(
            f"{context} TX lumped-port edge must not be constant-x / ZY-parallel "
            f"(target_edge={target_edge})"
        )
    if dy > tol or dz > tol:
        raise ValueError(
            f"{context} TX lumped-port edge must be an X-direction external stub bottom-face edge "
            f"(target_edge={target_edge})"
        )

def _find_matching_tx_stub_bottom_edge_id(
    *,
    modeler: Modeler3D,
    object_name: str,
    target_edge: _Edge2P,
    context: str,
    tol: float = 1e-6,
) -> int:
    _tx_target_edge_must_be_external_stub_bottom_x_edge(target_edge=target_edge, context=context, tol=tol)
    target_midpoint = _edge_midpoint(target_edge)
    matches: list[int] = []
    for raw_edge_id in list(modeler.get_object_edges(object_name)):
        edge_id = int(raw_edge_id)
        candidate_edge = edge_points_from_edge_id(
            modeler=modeler,
            edge_id=edge_id,
            context=f"{context} candidate edge",
        )
        candidate_first, candidate_second = candidate_edge
        dx = abs(candidate_second[0] - candidate_first[0])
        dy = abs(candidate_second[1] - candidate_first[1])
        dz = abs(candidate_second[2] - candidate_first[2])
        if dx <= tol:
            continue
        if dy > tol or dz > tol:
            continue
        candidate_midpoint = _edge_midpoint(candidate_edge)
        if abs(candidate_midpoint[2] - target_midpoint[2]) > tol:
            continue
        if not _edges_match(target_edge, candidate_edge, tol=tol):
            continue
        matches.append(edge_id)
    if len(matches) != 1:
        raise ValueError(
            f"{context} TX edge resolution must find exactly one X-direction external stub bottom-face edge "
            f"(object_name={object_name}, matches={matches}, target_edge={target_edge})"
        )
    return matches[0]

def _create_tx_external_stub(
    *,
    modeler: Modeler3D,
    design_id: str,
    terminal: _DirectedLandingSection,
    conductor_name: str,
    group_objects: GroupObjects,
    object_names: list[str],
    cad_probe: list[CadProbe],
) -> tuple[str, _Edge2P]:
    object_name_tag = object_name_tag_from_design_id(design_id)
    role = terminal["terminal_role"]
    if role not in ("feed_in", "feed_out"):
        raise ValueError(f"tx external stub contract violation: unsupported external role {role}")
    # `terminal["center"]` is the conductor attach-face center, not the stub-box center.
    # Shift the box inward by half the trace so the stub face lands flush on the coil endpoint plane.
    anchor_xyz = terminal["center"]
    trace = _tx_terminal_trace(terminal)
    half_trace = trace / 2.0
    stub_center_xyz = _stub_center_from_anchor(
        anchor_xyz=anchor_xyz,
        trace=trace,
        inward_dir=cast(_Point3, terminal["inward_dir"]) if "inward_dir" in terminal else anchor_xyz,
        has_inward_dir="inward_dir" in terminal,
    )
    target_edge = _txdd_start_stub_port_edge(anchor_xyz=stub_center_xyz, trace=trace, role=role)
    _tx_target_edge_must_be_external_stub_bottom_x_edge(
        target_edge=target_edge,
        context=f"tx external stub {role}",
    )
    terminal["bridge_stub_edge"] = target_edge
    stub_origin_z = stub_center_xyz[2]
    stub_origin = [stub_center_xyz[0] - half_trace, stub_center_xyz[1] - half_trace, stub_origin_z]
    stub_sizes = [trace, trace, TX_DD_START_STUB_LEN_MM]
    stub_name = f"txs_{role}_{object_name_tag}"
    stub_created = modeler.create_box(origin=stub_origin, sizes=stub_sizes, name=stub_name, material="copper")
    if not stub_created:
        raise ValueError(
            "tx external stub creation failed "
            f"(role={role}, conductor={conductor_name}, origin={stub_origin}, sizes={stub_sizes})"
        )
    info(
        "[tx_stub] "
        f"role={role} name={stub_name} anchor={anchor_xyz} center={stub_center_xyz} "
        f"origin={stub_origin} sizes={stub_sizes} owner={conductor_name}"
    )
    stub_obj = cast(Object3d, stub_created)
    stub_object_name = _object_name(stub_obj)
    object_names.append(stub_object_name)
    group_objects["tx_dd"].append(stub_object_name)
    if hasattr(stub_obj, "edges"):
        cad_probe.append(_probe_cad_object(stub_obj))
    # External TX stubs are IO markers only; they must not merge/connect TX layers.
    return stub_object_name, target_edge

def _create_tx_vertical_external_stub(
    *,
    modeler: Modeler3D,
    design_id: str,
    terminal: _DirectedLandingSection,
    stub_role: Literal["in", "out"],
    cu_thickness: float,
    group_objects: GroupObjects,
    object_names: list[str],
    cad_probe: list[CadProbe],
) -> str:
    object_name_tag = object_name_tag_from_design_id(design_id)
    trace = _tx_terminal_trace(terminal)
    if cu_thickness <= 0.0:
        raise ValueError(f"tx_vertical external stub cu_thickness must be > 0 (actual={cu_thickness})")
    if stub_role not in ("in", "out"):
        raise ValueError(f"tx_vertical external stub role must be in/out (actual={stub_role})")
    half_trace = trace / 2.0
    center = terminal["center"]
    plane_normal = terminal["plane_normal"]
    if abs(plane_normal[1]) <= 1e-12:
        raise ValueError(
            "tx_vertical external stub plane_normal must have Y component "
            f"(center={center}, plane_normal={plane_normal})"
        )
    # Legacy ZX tx_vertical external stubs are asymmetric by role:
    # `in` protrudes toward +Y, while `out` keeps the historical plane-normal-based direction.
    face_center_y = center[1] + (plane_normal[1] * (cu_thickness / 2.0))
    if stub_role == "in":
        origin_y = face_center_y
    else:
        origin_y = face_center_y if plane_normal[1] > 0.0 else face_center_y - TX_VERTICAL_START_STUB_LEN_MM
    stub_origin = [
        center[0],
        origin_y,
        center[2] - half_trace,
    ]
    stub_sizes = [trace, TX_VERTICAL_START_STUB_LEN_MM, trace]
    external_edge_y = origin_y + TX_VERTICAL_START_STUB_LEN_MM if (stub_role == "in" or plane_normal[1] > 0.0) else origin_y
    terminal["bridge_stub_edge"] = (
        (center[0], external_edge_y, center[2] - half_trace),
        (center[0] + trace, external_edge_y, center[2] - half_trace),
    )
    stub_name = f"txvs_{stub_role}_{object_name_tag}"
    stub_created = modeler.create_box(origin=stub_origin, sizes=stub_sizes, name=stub_name, material="copper")
    if not stub_created:
        raise ValueError(
            "tx_vertical external stub creation failed "
            f"(role={stub_role}, center={center}, origin={stub_origin}, sizes={stub_sizes})"
        )
    stub_obj = cast(Object3d, stub_created)
    stub_object_name = _object_name(stub_obj)
    terminal["stub_face_ref"] = capture_stub_face_ref_from_object(
        modeler=modeler,
        object_name=stub_object_name,
        expected_face_center=(center[0] + half_trace, external_edge_y, center[2]),
        face_kind="tx_vertical_xz",
        stub_role=stub_role,
        context="tx_vertical external stub face capture",
    )
    object_names.append(stub_object_name)
    group_objects["tx_vertical"].append(stub_object_name)
    if hasattr(stub_obj, "edges"):
        cad_probe.append(_probe_cad_object(stub_obj))
    return stub_object_name

def _txdd_start_stub_port_edge(
    *,
    anchor_xyz: _Point3,
    trace: float,
    role: Literal["feed_in", "feed_out"],
) -> _Edge2P:
    if trace <= 0.0:
        raise ValueError(f"tx_dd start stub port trace must be > 0 (actual={trace})")
    if role not in ("feed_in", "feed_out"):
        raise ValueError(f"tx_dd start stub port role must be feed_in/feed_out (actual={role})")
    half_trace = trace / 2.0
    z_plane = anchor_xyz[2] + TX_DD_START_STUB_LEN_MM
    # Use one deterministic X-direction edge on the external end face (max-Y side).
    p0: _Point3 = (anchor_xyz[0] - half_trace, anchor_xyz[1] + half_trace, z_plane)
    p1: _Point3 = (anchor_xyz[0] + half_trace, anchor_xyz[1] + half_trace, z_plane)
    return p0, p1

def _select_txdd_reference_conductor_name(reference_conductors: list[str]) -> str:
    if not reference_conductors:
        raise ValueError("tx_dd start port reference conductor list must not be empty")
    # TX_TML uses the opposite generated start stub as the deterministic HFSS reference.
    return sorted(reference_conductors)[-1]


__all__ = [
    '_tx_terminal_trace',
    '_stub_center_from_anchor',
    '_txdd_geometry_stub_sort_key',
    '_txdd_stub_origin_z_for_role',
    '_txdd_stub_length_for_role',
    '_tx_target_edge_must_be_external_stub_bottom_x_edge',
    '_find_matching_tx_stub_bottom_edge_id',
    '_create_tx_external_stub',
    '_create_tx_vertical_external_stub',
    '_txdd_start_stub_port_edge',
    '_select_txdd_reference_conductor_name',
]

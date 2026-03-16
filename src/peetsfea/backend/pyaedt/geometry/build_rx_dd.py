from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Literal, Protocol, TypedDict, cast

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.types.manifest import (
    CadProbe,
    EmContext,
    EmEndpoints,
    EmReadyObjects,
    GroupEndpointEntry,
    GroupObjects,
    RegionViolation,
    SceneObjectEntry,
)

from .cad_probe import _object_name, _probe_cad_object
from .debug_checks import _bbox_violations
from .solid_ops import safe_unite


_Point3 = tuple[float, float, float]
_Edge2P = tuple[_Point3, _Point3]
_BoardKey = tuple[str, int]
_TxVerticalLinkNode = tuple[int, str, _Point3, _Point3, float, float, _Edge2P, _Edge2P]
_BackConnectStubSource = tuple[str, int, str, _Point3, float, str]
_TxDdStartStubSource = tuple[_Point3, float, str]
_RxDdBackStubSource = _BackConnectStubSource
_RegionKind = Literal["tx_region_dd", "tx_region_vertical", "rx_region_actual"]
TX_DD_START_STUB_DOWN_MM = 3.0
RX_DD_BACK_STUB_LEN_MM = 3.0
RX_DD_BACK_STUB_AXIS_SIGN_X = -1.0
FR4_SUBTRACT_OVERLAP_MM = 0.1
TX_VERTICAL_MODE2_PAIR_JOG_X_MM = 1.0


class _TxVerticalMode2TerminalEdges(TypedDict):
    right_start_edge: _Edge2P
    right_start_object_name: str
    right_end_edge: _Edge2P
    right_end_object_name: str
    left_start_edge: _Edge2P
    left_start_object_name: str
    left_end_edge: _Edge2P
    left_end_object_name: str


class _BoundaryModule(Protocol):
    def AutoIdentifyPorts(
        self,
        faces: list[object],
        is_wave_port: bool,
        reference_conductors: list[object],
        port_name: str,
        renormalize: bool,
    ) -> None: ...


def _rxdd_back_stub_sort_key(source: _RxDdBackStubSource) -> tuple[str, int, str]:
    board_id, instance_index, endpoint_label, *_ = source
    return board_id, instance_index, endpoint_label


def _rxdd_back_stub_origin_and_sizes(*, anchor_xyz: _Point3, trace: float) -> tuple[list[float], list[float]]:
    length = RX_DD_BACK_STUB_LEN_MM
    if trace <= 0.0:
        raise ValueError(f"rx_dd back stub trace must be > 0 (actual={trace})")
    if abs(RX_DD_BACK_STUB_AXIS_SIGN_X + 1.0) > 1e-12:
        raise ValueError(
            "rx_dd back stub axis contract violation: RX_DD_BACK_STUB_AXIS_SIGN_X must be -1.0 "
            f"(actual={RX_DD_BACK_STUB_AXIS_SIGN_X})"
        )
    origin = [
        anchor_xyz[0] + (RX_DD_BACK_STUB_AXIS_SIGN_X * length),
        anchor_xyz[1] - (trace / 2.0),
        anchor_xyz[2] - (trace / 2.0),
    ]
    sizes = [length, trace, trace]
    return origin, sizes


def _rxdd_back_stub_bridge_edge(*, anchor_xyz: _Point3, trace: float) -> _Edge2P:
    if trace <= 0.0:
        raise ValueError(f"rx_dd back stub bridge trace must be > 0 (actual={trace})")
    x_at_back = anchor_xyz[0] + (RX_DD_BACK_STUB_AXIS_SIGN_X * RX_DD_BACK_STUB_LEN_MM)
    half_trace = trace / 2.0
    p0: _Point3 = (x_at_back, anchor_xyz[1] - half_trace, anchor_xyz[2] - half_trace)
    p1: _Point3 = (x_at_back, anchor_xyz[1] - half_trace, anchor_xyz[2] + half_trace)
    return p0, p1


def _apply_back_connect_stub_pair_bridge(
    *,
    modeler: Modeler3D,
    design_id: str,
    cu_thickness: float,
    sources: list[_BackConnectStubSource],
    group_objects: GroupObjects,
    group_key: Literal["rx_dd", "tx_vertical"],
    object_names: list[str],
    cad_probe: list[CadProbe],
    bridge_name: str,
    stub_name_prefix: str,
    stub_error_context: str,
    bridge_error_context: str,
    sheet_points_builder: Callable[..., list[list[float]]] | None = None,
    region_kind: _RegionKind | None = None,
    region_min: _Point3 | None = None,
    region_max: _Point3 | None = None,
    placement_violations: list[RegionViolation] | None = None,
) -> None:
    if not sources:
        return
    if sheet_points_builder is None:
        sheet_points_builder = _sheet_points_from_edge_pair

    name_replacements: dict[str, str] = {}
    connect_stub_edges: dict[str, _Edge2P] = {}
    connect_source_names: dict[str, str] = {}

    def _resolve_replaced_name(name: str) -> str:
        current = name
        for _ in range(10):
            next_name = name_replacements.get(current)
            if next_name is None or next_name == current:
                return current
            current = next_name
        raise ValueError(f"{group_key} replacement chain too deep (name={name})")

    def _check_region(*, object_name: str, bbox: list[float]) -> None:
        if region_kind is None or region_min is None or region_max is None:
            return
        violations = _bbox_violations(
            object_name=object_name,
            bbox=bbox,
            region_kind=region_kind,
            region_min=region_min,
            region_max=region_max,
        )
        if not violations:
            return
        if placement_violations is not None:
            placement_violations.extend(violations)
        first = violations[0]
        raise ValueError(
            f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
            f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
        )

    for board_id, instance_index, endpoint_label, anchor_xyz, trace, source_object_name_raw in sorted(
        sources,
        key=_rxdd_back_stub_sort_key,
    ):
        if endpoint_label not in ("c", "d"):
            raise ValueError(
                f"{group_key} back connect-stub endpoint must be c/d only "
                f"(actual={endpoint_label}, board_id={board_id}, instance_index={instance_index})"
            )
        source_object_name = _resolve_replaced_name(source_object_name_raw)
        source_exists = (source_object_name in object_names) or (source_object_name in group_objects[group_key])
        if not source_exists:
            raise ValueError(
                f"{group_key} back stub source object missing "
                f"(board_id={board_id}, instance_index={instance_index}, endpoint={endpoint_label}, "
                f"source={source_object_name}, source_raw={source_object_name_raw})"
            )
        stub_origin, stub_sizes = _rxdd_back_stub_origin_and_sizes(anchor_xyz=anchor_xyz, trace=trace)
        stub_name = f"{stub_name_prefix}_{board_id}_{instance_index}_{endpoint_label}"
        stub_created = modeler.create_box(origin=stub_origin, sizes=stub_sizes, name=stub_name, material="copper")
        if not stub_created:
            raise ValueError(
                f"{group_key} back stub creation failed "
                f"(name={stub_name}, source={source_object_name}, origin={stub_origin}, sizes={stub_sizes})"
            )
        stub_obj = cast(Object3d, stub_created)
        stub_object_name = _object_name(stub_obj, stub_name)
        object_names.append(stub_object_name)
        group_objects[group_key].append(stub_object_name)
        stub_probe = _probe_cad_object(stub_obj, stub_name)
        cad_probe.append(stub_probe)
        _check_region(object_name=stub_object_name, bbox=stub_probe["bbox"])

        stub_united_name = safe_unite(
            modeler=modeler,
            targets=[source_object_name, stub_object_name],
            fallback_name=source_object_name,
            error_context=stub_error_context,
        )
        group_objects[group_key] = [name for name in group_objects[group_key] if name != stub_object_name]
        object_names[:] = [name for name in object_names if name != stub_object_name]
        group_objects[group_key] = [stub_united_name if name == source_object_name else name for name in group_objects[group_key]]
        object_names[:] = [stub_united_name if name == source_object_name else name for name in object_names]
        if stub_united_name not in group_objects[group_key]:
            group_objects[group_key].append(stub_united_name)
        if stub_united_name not in object_names:
            object_names.append(stub_united_name)
        for old_name, mapped_name in list(name_replacements.items()):
            if mapped_name == source_object_name:
                name_replacements[old_name] = stub_united_name
        name_replacements[source_object_name] = stub_united_name
        name_replacements[source_object_name_raw] = stub_united_name
        if endpoint_label in connect_stub_edges:
            raise ValueError(
                f"{group_key} d/c bridge contract violation: duplicate stub endpoint captured "
                f"(endpoint={endpoint_label}, board_id={board_id}, instance_index={instance_index})"
            )
        connect_stub_edges[endpoint_label] = _rxdd_back_stub_bridge_edge(anchor_xyz=anchor_xyz, trace=trace)
        connect_source_names[endpoint_label] = source_object_name_raw

    has_c = "c" in connect_stub_edges
    has_d = "d" in connect_stub_edges
    if has_c != has_d:
        raise ValueError(
            f"{group_key} d/c bridge contract violation: both c and d stub edges must be present together "
            f"(has_c={has_c}, has_d={has_d})"
        )
    if not has_c:
        return

    c_edge = connect_stub_edges["c"]
    d_edge = connect_stub_edges["d"]
    c_object_name = _resolve_replaced_name(connect_source_names["c"])
    d_object_name = _resolve_replaced_name(connect_source_names["d"])
    c_exists = (c_object_name in object_names) or (c_object_name in group_objects[group_key])
    d_exists = (d_object_name in object_names) or (d_object_name in group_objects[group_key])
    if not c_exists or not d_exists:
        raise ValueError(f"{group_key} d/c bridge source object missing (c_source={c_object_name}, d_source={d_object_name})")

    dc_bridge_sheet_points = sheet_points_builder(dd_edge=d_edge, vertical_edge=c_edge)
    try:
        dc_bridge_obj_name, dc_bridge_obj = _create_thickened_sheet_from_points(
            modeler=modeler,
            sheet_points=dc_bridge_sheet_points,
            sheet_name=bridge_name,
            thickness=(cu_thickness * 4.0),
        )
    except ValueError as exc:
        message = str(exc)
        if message.startswith("Sheet loop creation failed"):
            raise ValueError(f"{bridge_error_context} rectangle loop creation failed (name={bridge_name})") from exc
        if message.startswith("Sheet cover_lines failed"):
            raise ValueError(f"{bridge_error_context} cover_lines failed (name={bridge_name})") from exc
        if message.startswith("Sheet thicken failed"):
            raise ValueError(f"{bridge_error_context} thicken failed (name={bridge_name}, thickness={cu_thickness * 4.0})") from exc
        raise

    object_names.append(dc_bridge_obj_name)
    group_objects[group_key].append(dc_bridge_obj_name)
    bridge_probe = _probe_cad_object(dc_bridge_obj, bridge_name)
    cad_probe.append(bridge_probe)
    _check_region(object_name=dc_bridge_obj_name, bbox=bridge_probe["bbox"])

    unite_targets = sorted(set([d_object_name, c_object_name, dc_bridge_obj_name]))
    if len(unite_targets) <= 1:
        return
    united_name = safe_unite(
        modeler=modeler,
        targets=unite_targets,
        fallback_name=unite_targets[0],
        error_context=bridge_error_context,
    )
    group_objects[group_key] = [name for name in group_objects[group_key] if name not in unite_targets[1:]]
    if united_name not in group_objects[group_key]:
        group_objects[group_key].append(united_name)
    object_names[:] = [name for name in object_names if name not in unite_targets[1:]]
    if united_name not in object_names:
        object_names.append(united_name)


def _apply_diagonal_connect_pair_conductor(
    *,
    modeler: Modeler3D,
    cu_thickness: float,
    sources: list[_BackConnectStubSource],
    group_objects: GroupObjects,
    group_key: Literal["rx_dd", "tx_vertical"],
    object_names: list[str],
    cad_probe: list[CadProbe],
    conductor_name: str,
    conductor_error_context: str,
    region_kind: _RegionKind | None = None,
    region_min: _Point3 | None = None,
    region_max: _Point3 | None = None,
    placement_violations: list[RegionViolation] | None = None,
) -> None:
    if not sources:
        return

    def _check_region(*, object_name: str, bbox: list[float]) -> None:
        if region_kind is None or region_min is None or region_max is None:
            return
        violations = _bbox_violations(
            object_name=object_name,
            bbox=bbox,
            region_kind=region_kind,
            region_min=region_min,
            region_max=region_max,
        )
        if not violations:
            return
        if placement_violations is not None:
            placement_violations.extend(violations)
        first = violations[0]
        raise ValueError(
            f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
            f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
        )

    endpoints: dict[str, tuple[_Point3, float, str]] = {}
    for board_id, instance_index, endpoint_label, anchor_xyz, trace, source_object_name in sorted(
        sources,
        key=_rxdd_back_stub_sort_key,
    ):
        if endpoint_label not in ("c", "d"):
            raise ValueError(
                f"{group_key} diagonal connector endpoint must be c/d only "
                f"(actual={endpoint_label}, board_id={board_id}, instance_index={instance_index})"
            )
        source_exists = (source_object_name in object_names) or (source_object_name in group_objects[group_key])
        if not source_exists:
            raise ValueError(
                f"{group_key} diagonal connector source object missing "
                f"(board_id={board_id}, instance_index={instance_index}, endpoint={endpoint_label}, "
                f"source={source_object_name})"
            )
        if endpoint_label in endpoints:
            raise ValueError(
                f"{group_key} diagonal connector contract violation: duplicate endpoint captured "
                f"(endpoint={endpoint_label}, board_id={board_id}, instance_index={instance_index})"
            )
        endpoints[endpoint_label] = (anchor_xyz, trace, source_object_name)

    has_c = "c" in endpoints
    has_d = "d" in endpoints
    if has_c != has_d:
        raise ValueError(
            f"{group_key} diagonal connector contract violation: both c and d endpoints must be present together "
            f"(has_c={has_c}, has_d={has_d})"
        )
    if not has_c:
        return

    c_anchor_xyz, c_trace, c_object_name = endpoints["c"]
    d_anchor_xyz, d_trace, d_object_name = endpoints["d"]
    if abs(c_trace - d_trace) > 1e-9:
        raise ValueError(
            f"{group_key} diagonal connector trace mismatch "
            f"(c_trace={c_trace}, d_trace={d_trace})"
        )

    conductor_created = modeler.create_polyline(
        points=[
            [d_anchor_xyz[0], d_anchor_xyz[1], d_anchor_xyz[2]],
            [c_anchor_xyz[0], c_anchor_xyz[1], c_anchor_xyz[2]],
        ],
        name=conductor_name,
        material="copper",
        xsection_type="Rectangle",
        xsection_width=d_trace,  # type: ignore[arg-type]
        xsection_height=cu_thickness,  # type: ignore[arg-type]
    )
    if not conductor_created:
        raise ValueError(f"{conductor_error_context} polyline creation failed (name={conductor_name})")
    conductor_obj = cast(Object3d, conductor_created)
    conductor_obj_name = _object_name(conductor_obj, conductor_name)
    object_names.append(conductor_obj_name)
    group_objects[group_key].append(conductor_obj_name)
    conductor_probe = _probe_cad_object(conductor_obj, conductor_name)
    cad_probe.append(conductor_probe)
    _check_region(object_name=conductor_obj_name, bbox=conductor_probe["bbox"])

    unite_targets = sorted(set([d_object_name, c_object_name, conductor_obj_name]))
    if len(unite_targets) <= 1:
        return
    united_name = safe_unite(
        modeler=modeler,
        targets=unite_targets,
        fallback_name=unite_targets[0],
        error_context=conductor_error_context,
    )
    group_objects[group_key] = [name for name in group_objects[group_key] if name not in unite_targets[1:]]
    if united_name not in group_objects[group_key]:
        group_objects[group_key].append(united_name)
    object_names[:] = [name for name in object_names if name not in unite_targets[1:]]
    if united_name not in object_names:
        object_names.append(united_name)


def _apply_existing_edge_bridge_conductor(
    *,
    modeler: Modeler3D,
    cu_thickness: float,
    first_edge: _Edge2P,
    first_object_name: str,
    second_edge: _Edge2P,
    second_object_name: str,
    group_objects: GroupObjects,
    group_key: Literal["tx_vertical"],
    object_names: list[str],
    cad_probe: list[CadProbe],
    bridge_name: str,
    bridge_error_context: str,
    region_kind: _RegionKind | None = None,
    region_min: _Point3 | None = None,
    region_max: _Point3 | None = None,
    placement_violations: list[RegionViolation] | None = None,
    x_jog_mm: float = 0.0,
) -> str:
    def _check_region(*, object_name: str, bbox: list[float]) -> None:
        if region_kind is None or region_min is None or region_max is None:
            return
        violations = _bbox_violations(
            object_name=object_name,
            bbox=bbox,
            region_kind=region_kind,
            region_min=region_min,
            region_max=region_max,
        )
        if not violations:
            return
        if placement_violations is not None:
            placement_violations.extend(violations)
        first = violations[0]
        raise ValueError(
            f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
            f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
        )

    for source_object_name in (first_object_name, second_object_name):
        source_exists = (source_object_name in object_names) or (source_object_name in group_objects[group_key])
        if not source_exists:
            raise ValueError(
                f"{group_key} edge-bridge source object missing "
                f"(bridge={bridge_name}, source={source_object_name})"
            )

    if x_jog_mm < 0.0:
        raise ValueError(f"{group_key} edge-bridge x_jog_mm must be >= 0 (actual={x_jog_mm})")

    def _offset_edge_x(edge: _Edge2P, dx: float) -> _Edge2P:
        return (
            (edge[0][0] + dx, edge[0][1], edge[0][2]),
            (edge[1][0] + dx, edge[1][1], edge[1][2]),
        )

    def _create_bridge_piece(
        *,
        piece_name: str,
        piece_first_edge: _Edge2P,
        piece_second_edge: _Edge2P,
        reverse_sheet_loop: bool = False,
    ) -> str:
        bridge_sheet_points = _sheet_points_from_edge_pair(dd_edge=piece_first_edge, vertical_edge=piece_second_edge)
        if reverse_sheet_loop:
            bridge_sheet_points = list(reversed(bridge_sheet_points))
        try:
            bridge_obj_name, bridge_obj = _create_thickened_sheet_from_points(
                modeler=modeler,
                sheet_points=bridge_sheet_points,
                sheet_name=piece_name,
                thickness=(cu_thickness * 4.0),
            )
        except ValueError as exc:
            message = str(exc)
            if message.startswith("Sheet loop creation failed"):
                raise ValueError(f"{bridge_error_context} rectangle loop creation failed (name={piece_name})") from exc
            if message.startswith("Sheet cover_lines failed"):
                raise ValueError(f"{bridge_error_context} cover_lines failed (name={piece_name})") from exc
            if message.startswith("Sheet thicken failed"):
                raise ValueError(
                    f"{bridge_error_context} thicken failed (name={piece_name}, thickness={cu_thickness * 4.0})"
                ) from exc
            raise

        object_names.append(bridge_obj_name)
        group_objects[group_key].append(bridge_obj_name)
        bridge_probe = _probe_cad_object(bridge_obj, piece_name)
        cad_probe.append(bridge_probe)
        _check_region(object_name=bridge_obj_name, bbox=bridge_probe["bbox"])
        return bridge_obj_name

    if x_jog_mm <= 1e-12:
        bridge_object_names = [
            _create_bridge_piece(
                piece_name=bridge_name,
                piece_first_edge=first_edge,
                piece_second_edge=second_edge,
            )
        ]
    else:
        first_offset_edge = _offset_edge_x(first_edge, x_jog_mm)
        second_offset_edge = _offset_edge_x(second_edge, x_jog_mm)
        bridge_object_names = [
            _create_bridge_piece(
                piece_name=f"{bridge_name}_jog_out",
                piece_first_edge=first_edge,
                piece_second_edge=first_offset_edge,
                reverse_sheet_loop=True,
            ),
            _create_bridge_piece(
                piece_name=bridge_name,
                piece_first_edge=first_offset_edge,
                piece_second_edge=second_offset_edge,
            ),
            _create_bridge_piece(
                piece_name=f"{bridge_name}_jog_in",
                piece_first_edge=second_offset_edge,
                piece_second_edge=second_edge,
            ),
        ]

    unite_targets = [first_object_name, second_object_name, *bridge_object_names]
    united_name = safe_unite(
        modeler=modeler,
        targets=unite_targets,
        fallback_name=first_object_name,
        error_context=bridge_error_context,
    )
    group_objects[group_key] = [name for name in group_objects[group_key] if name not in unite_targets]
    group_objects[group_key].append(united_name)
    object_names[:] = [name for name in object_names if name not in unite_targets]
    object_names.append(united_name)
    return united_name


def _auto_identify_ports_direct(
    *,
    hfss: Hfss,
    face_id: int,
    reference_conductor_name: str,
    port_name: str,
    sheet_name: str,
    board_id: str,
    context: str,
) -> None:
    boundary_module = cast(_BoundaryModule | None, hfss.oboundary)
    assert boundary_module is not None, "HFSS boundary module is not initialized"
    try:
        boundary_module.AutoIdentifyPorts(
            ["NAME:Faces", int(face_id)],
            False,
            ["NAME:ReferenceConductors", reference_conductor_name],
            port_name,
            True,
        )
    except Exception as exc:
        raise ValueError(
            f"{context} failed in AutoIdentifyPorts "
            f"(port={port_name}, sheet={sheet_name}, reference={reference_conductor_name}, board_id={board_id})"
        ) from exc


def _is_rxdd_connect_stub_endpoint(endpoint_label: str) -> bool:
    return endpoint_label in ("c", "d")


def _is_rxdd_port_stub_endpoint(endpoint_label: str) -> bool:
    return endpoint_label in ("A", "B")


def _txdd_start_stub_port_edge(*, anchor_xyz: _Point3, trace: float) -> _Edge2P:
    if trace <= 0.0:
        raise ValueError(f"tx_dd start stub port trace must be > 0 (actual={trace})")
    half_trace = trace / 2.0
    z_bottom = anchor_xyz[2] - TX_DD_START_STUB_DOWN_MM
    # Use one deterministic bottom-face edge (min-Y side) for 4-point sheet creation.
    p0: _Point3 = (anchor_xyz[0] - half_trace, anchor_xyz[1] - half_trace, z_bottom)
    p1: _Point3 = (anchor_xyz[0] + half_trace, anchor_xyz[1] - half_trace, z_bottom)
    return p0, p1


def _create_thickened_sheet_from_points(
    *,
    modeler: Modeler3D,
    sheet_points: list[list[float]],
    sheet_name: str,
    thickness: float,
) -> tuple[str, Object3d]:
    sheet_covered_name, sheet_loop_obj = _create_sheet_from_points(
        modeler=modeler,
        sheet_points=sheet_points,
        sheet_name=sheet_name,
    )
    try:
        thickened = modeler.thicken_sheet(assignment=sheet_covered_name, thickness=thickness)  # type: ignore[misc]
    except TypeError:
        thickened = modeler.thicken_sheet(sheet_covered_name, thickness)  # type: ignore[misc]
    if not thickened:
        raise ValueError(f"Sheet thicken failed (name={sheet_name}, thickness={thickness})")

    if isinstance(thickened, list):
        first = thickened[0] if thickened else sheet_covered_name
        thickened_name = first if isinstance(first, str) else _object_name(cast(Object3d, first), sheet_covered_name)
        thickened_obj = cast(Object3d, sheet_loop_obj)
    elif isinstance(thickened, str):
        thickened_name = thickened
        thickened_obj = cast(Object3d, sheet_loop_obj)
    else:
        thickened_obj = cast(Object3d, thickened)
        thickened_name = _object_name(thickened_obj, sheet_covered_name)
    return thickened_name, thickened_obj


def _create_sheet_from_points(
    *,
    modeler: Modeler3D,
    sheet_points: list[list[float]],
    sheet_name: str,
) -> tuple[str, Object3d]:
    sheet_created = modeler.create_polyline(points=sheet_points, name=sheet_name, material="copper", close_surface=True)
    if not sheet_created:
        raise ValueError(f"Sheet loop creation failed (name={sheet_name})")

    sheet_loop_obj = cast(Object3d, sheet_created)
    sheet_loop_name = _object_name(sheet_loop_obj, sheet_name)
    try:
        covered = modeler.cover_lines(assignment=sheet_loop_name)  # type: ignore[misc]
    except TypeError:
        covered = modeler.cover_lines(sheet_loop_name)  # type: ignore[misc]
    if not covered:
        raise ValueError(f"Sheet cover_lines failed (name={sheet_name})")

    if isinstance(covered, list):
        first = covered[0] if covered else sheet_loop_name
        sheet_covered_name = first if isinstance(first, str) else _object_name(cast(Object3d, first), sheet_loop_name)
    elif isinstance(covered, str):
        sheet_covered_name = covered
    else:
        sheet_covered_name = _object_name(cast(Object3d, covered), sheet_loop_name)
    return sheet_covered_name, sheet_loop_obj


def _sheet_points_from_edge_pair(*, dd_edge: _Edge2P, vertical_edge: _Edge2P) -> list[list[float]]:
    dd_edge_0, dd_edge_1 = dd_edge
    v_edge_0, v_edge_1 = vertical_edge
    same_pair_cost = math.dist(dd_edge_0, v_edge_0) + math.dist(dd_edge_1, v_edge_1)
    cross_pair_cost = math.dist(dd_edge_0, v_edge_1) + math.dist(dd_edge_1, v_edge_0)
    if cross_pair_cost < same_pair_cost:
        v_edge_0, v_edge_1 = v_edge_1, v_edge_0
    return [
        [dd_edge_0[0], dd_edge_0[1], dd_edge_0[2]],
        [dd_edge_1[0], dd_edge_1[1], dd_edge_1[2]],
        [v_edge_1[0], v_edge_1[1], v_edge_1[2]],
        [v_edge_0[0], v_edge_0[1], v_edge_0[2]],
    ]


def _diagonal_sheet_points_from_edge_pair(*, dd_edge: _Edge2P, vertical_edge: _Edge2P) -> list[list[float]]:
    dd_edge_0, dd_edge_1 = dd_edge
    v_edge_0, v_edge_1 = vertical_edge
    same_pair_cost = math.dist(dd_edge_0, v_edge_0) + math.dist(dd_edge_1, v_edge_1)
    cross_pair_cost = math.dist(dd_edge_0, v_edge_1) + math.dist(dd_edge_1, v_edge_0)
    if same_pair_cost <= cross_pair_cost:
        return [
            [dd_edge_0[0], dd_edge_0[1], dd_edge_0[2]],
            [dd_edge_1[0], dd_edge_1[1], dd_edge_1[2]],
            [v_edge_0[0], v_edge_0[1], v_edge_0[2]],
            [v_edge_1[0], v_edge_1[1], v_edge_1[2]],
        ]
    return [
        [dd_edge_0[0], dd_edge_0[1], dd_edge_0[2]],
        [dd_edge_1[0], dd_edge_1[1], dd_edge_1[2]],
        [v_edge_1[0], v_edge_1[1], v_edge_1[2]],
        [v_edge_0[0], v_edge_0[1], v_edge_0[2]],
    ]


def _fr4_box_from_plane_bbox(
    *,
    plane: Literal["XY", "YZ", "ZX"],
    bbox: list[float],
    pcb_thickness: float,
    overlap_mm: float,
    eps_len: float,
) -> tuple[list[float], list[float]]:
    min_x, min_y, min_z, max_x, max_y, max_z = bbox
    span_x = max(max_x - min_x, eps_len)
    span_y = max(max_y - min_y, eps_len)
    span_z = max(max_z - min_z, eps_len)
    if plane == "XY":
        origin = [min_x - overlap_mm, min_y - overlap_mm, min_z - pcb_thickness - overlap_mm]
        # Apply overlap in plane only. Keep FR4 thickness axis unchanged to avoid FR4-FR4 intersections.
        sizes = [span_x + (2.0 * overlap_mm), span_y + (2.0 * overlap_mm), max(pcb_thickness, eps_len)]
    elif plane == "YZ":
        origin = [min_x - pcb_thickness - overlap_mm, min_y - overlap_mm, min_z - overlap_mm]
        sizes = [max(pcb_thickness, eps_len), span_y + (2.0 * overlap_mm), span_z + (2.0 * overlap_mm)]
    else:
        origin = [min_x - overlap_mm, min_y - pcb_thickness - overlap_mm, min_z - overlap_mm]
        sizes = [span_x + (2.0 * overlap_mm), max(pcb_thickness, eps_len), span_z + (2.0 * overlap_mm)]
    return origin, sizes


def _txdd_left_a_edge_from_points(*, txdd_left_a_points: dict[int, tuple[_Point3, float]]) -> _Edge2P:
    if 0 not in txdd_left_a_points or 1 not in txdd_left_a_points:
        raise ValueError("tx_dd left a-edge contract violation: layer points [0,1] were not captured")
    lower_a, lower_trace = txdd_left_a_points[0]
    upper_a, upper_trace = txdd_left_a_points[1]
    if abs(lower_trace - upper_trace) > 1e-9:
        raise ValueError(
            "tx_dd left a-edge contract violation: lower/upper A trace must match "
            f"(lower_trace={lower_trace}, upper_trace={upper_trace})"
        )
    return lower_a, upper_a


def _replace_object_name_in_map(mapping: dict[int, str], *, old_name: str, new_name: str) -> None:
    for layer_key, object_name in list(mapping.items()):
        if object_name == old_name:
            mapping[layer_key] = new_name


def _tx_dd_xy_tools(
    *,
    txdd_right_object_names: dict[int, str],
    txdd_left_object_names: dict[int, str],
    group_objects: GroupObjects,
    live_object_names: set[str],
) -> list[str]:
    tools = sorted(
        name
        for name in (set(txdd_right_object_names.values()) | set(txdd_left_object_names.values()))
        if name in live_object_names
    )
    if tools:
        return tools
    return sorted(name for name in set(group_objects["tx_dd"]) if name in live_object_names)


def _finalize_solids_and_substrates_impl(
    *,
    modeler: Modeler3D,
    hfss: Hfss,
    aedt_path: Path,
    design_id: str,
    cu_thickness: float,
    pcb_thickness: float,
    tx_board_ids: set[str],
    tx_vertical_nodes_by_board: dict[_BoardKey, list[_TxVerticalLinkNode]],
    tx_vertical_mode2_terminal_edges_by_board: dict[_BoardKey, _TxVerticalMode2TerminalEdges],
    tx_vertical_region_min: _Point3,
    tx_vertical_region_max: _Point3,
    txdd_right_a_points: dict[int, tuple[_Point3, float]],
    txdd_right_object_names: dict[int, str],
    txdd_left_a_points: dict[int, tuple[_Point3, float]],
    txdd_left_object_names: dict[int, str],
    txdd_start_stub_sources: dict[str, list[_TxDdStartStubSource]],
    rxdd_back_stub_sources: list[_RxDdBackStubSource],
    group_objects: GroupObjects,
    object_names: list[str],
    cad_probe: list[CadProbe],
    placement_violations: list[RegionViolation],
    coil_plane_bboxes: list[tuple[str, Literal["XY", "YZ", "ZX"], list[float]]],
    fr4_object_names: list[str],
    tx_vertical_fr4_names: list[str],
    txdd_global_right_d_edge: _Edge2P | None,
    txdd_global_right_d_object_name: str | None,
    txdd_global_left_vertical_link_edge: _Edge2P | None,
    txdd_global_left_vertical_link_object_name: str | None,
    tx_vertical_global_outer_right_edge: _Edge2P | None,
    tx_vertical_global_outer_left_edge: _Edge2P | None,
) -> tuple[list[str], list[str]]:
    txdd_bridge_object_name: str | None = None
    txdd_left_bridge_object_name: str | None = None
    txdd_right_d_object_name_active = txdd_global_right_d_object_name
    txdd_left_vertical_link_object_name_active = (
        txdd_global_left_vertical_link_object_name or txdd_left_object_names.get(1) or txdd_left_object_names.get(0)
    )

    txdd_start_stub_port_edges_by_board: dict[str, list[_Edge2P]] = {}
    txdd_start_stub_reference_names_by_board: dict[str, list[str]] = {}
    rxdd_start_stub_edge_by_name: dict[str, _Edge2P] = {}
    rxdd_start_stub_board_by_name: dict[str, str] = {}

    sorted_rxdd_back_stub_sources = sorted(rxdd_back_stub_sources, key=_rxdd_back_stub_sort_key)
    rxdd_connect_stub_sources: list[_RxDdBackStubSource] = []
    for board_id, instance_index, endpoint_label, anchor_xyz, trace, source_object_name in sorted_rxdd_back_stub_sources:
        if _is_rxdd_connect_stub_endpoint(endpoint_label):
            rxdd_connect_stub_sources.append((board_id, instance_index, endpoint_label, anchor_xyz, trace, source_object_name))
            continue
        source_exists = (source_object_name in object_names) or (source_object_name in group_objects["rx_dd"])
        if not source_exists:
            raise ValueError(
                "rx_dd back stub source object missing "
                f"(board_id={board_id}, instance_index={instance_index}, endpoint={endpoint_label}, "
                f"source={source_object_name})"
            )
        stub_origin, stub_sizes = _rxdd_back_stub_origin_and_sizes(anchor_xyz=anchor_xyz, trace=trace)
        stub_name = f"rxs_{board_id}_{instance_index}_{endpoint_label}"
        stub_created = modeler.create_box(origin=stub_origin, sizes=stub_sizes, name=stub_name, material="copper")
        if not stub_created:
            raise ValueError(
                "rx_dd back stub creation failed "
                f"(name={stub_name}, source={source_object_name}, origin={stub_origin}, sizes={stub_sizes})"
            )
        stub_obj = cast(Object3d, stub_created)
        stub_object_name = _object_name(stub_obj, stub_name)
        object_names.append(stub_object_name)
        group_objects["rx_dd"].append(stub_object_name)
        cad_probe.append(_probe_cad_object(stub_obj, stub_name))
        subtract_ok = modeler.subtract(blank_list=[stub_object_name], tool_list=[source_object_name], keep_originals=True)
        if not subtract_ok:
            raise ValueError(
                "rx_dd back port-stub subtract-from-source failed "
                f"(stub={stub_object_name}, source={source_object_name}, board_id={board_id}, endpoint={endpoint_label})"
            )
        if _is_rxdd_port_stub_endpoint(endpoint_label):
            rxdd_start_stub_edge_by_name[stub_object_name] = _rxdd_back_stub_bridge_edge(anchor_xyz=anchor_xyz, trace=trace)
            rxdd_start_stub_board_by_name[stub_object_name] = board_id

    _apply_diagonal_connect_pair_conductor(
        modeler=modeler,
        cu_thickness=cu_thickness,
        sources=rxdd_connect_stub_sources,
        group_objects=group_objects,
        group_key="rx_dd",
        object_names=object_names,
        cad_probe=cad_probe,
        conductor_name=f"bridge_rx_dd_d_to_c_{design_id}",
        conductor_error_context="rx_dd d/c diagonal conductor with source coils",
    )

    for board_id, stub_sources in sorted(txdd_start_stub_sources.items()):
        for stub_idx, stub_source in enumerate(stub_sources):
            start_xyz, trace, source_object_name = stub_source
            source_exists = (source_object_name in object_names) or (source_object_name in group_objects["tx_dd"])
            if not source_exists:
                raise ValueError(
                    "tx_dd start stub source object missing "
                    f"(board_id={board_id}, source={source_object_name})"
                )
            stub_origin = [
                start_xyz[0] - (trace / 2.0),
                start_xyz[1] - (trace / 2.0),
                start_xyz[2] - TX_DD_START_STUB_DOWN_MM,
            ]
            stub_sizes = [trace, trace, TX_DD_START_STUB_DOWN_MM]
            # Keep the reference conductor name short because AEDT terminal names
            # are derived from it and are reused by post-processing.
            stub_name = f"txs_{board_id}_{stub_idx}"
            stub_created = modeler.create_box(origin=stub_origin, sizes=stub_sizes, name=stub_name, material="copper")
            if not stub_created:
                raise ValueError(
                    "tx_dd start stub creation failed "
                    f"(name={stub_name}, source={source_object_name}, origin={stub_origin}, sizes={stub_sizes})"
                )
            stub_obj = cast(Object3d, stub_created)
            stub_object_name = _object_name(stub_obj, stub_name)
            object_names.append(stub_object_name)
            group_objects["tx_dd"].append(stub_object_name)
            cad_probe.append(_probe_cad_object(stub_obj, stub_name))
            # Keep the source conductor unchanged and carve overlap volume out of the stub.
            subtract_ok = modeler.subtract(blank_list=[stub_object_name], tool_list=[source_object_name], keep_originals=True)
            if not subtract_ok:
                raise ValueError(
                    "tx_dd start stub subtract-from-source failed "
                    f"(stub={stub_object_name}, source={source_object_name}, board_id={board_id})"
                )
            txdd_start_stub_port_edges_by_board.setdefault(board_id, []).append(
                _txdd_start_stub_port_edge(anchor_xyz=start_xyz, trace=trace)
            )
            txdd_start_stub_reference_names_by_board.setdefault(board_id, []).append(stub_object_name)

    for board_id, port_edges in sorted(txdd_start_stub_port_edges_by_board.items()):
        if len(port_edges) != 2:
            raise ValueError(
                "tx_dd start port sheet contract violation: expected exactly 2 start stubs per board "
                f"(board_id={board_id}, actual={len(port_edges)})"
            )
        start_port_sheet_points = _sheet_points_from_edge_pair(dd_edge=port_edges[0], vertical_edge=port_edges[1])
        start_port_sheet_name = f"sheet_txdd_ports_{board_id}"
        try:
            start_port_sheet_obj_name, start_port_sheet_obj = _create_sheet_from_points(
                modeler=modeler,
                sheet_points=start_port_sheet_points,
                sheet_name=start_port_sheet_name,
            )
        except ValueError as exc:
            message = str(exc)
            if message.startswith("Sheet loop creation failed"):
                raise ValueError(
                    "tx_dd start port sheet rectangle loop creation failed "
                    f"(name={start_port_sheet_name}, board_id={board_id})"
                ) from exc
            if message.startswith("Sheet cover_lines failed"):
                raise ValueError(
                    "tx_dd start port sheet cover_lines failed "
                    f"(name={start_port_sheet_name}, board_id={board_id})"
                ) from exc
            raise
        object_names.append(start_port_sheet_obj_name)
        cad_probe.append(_probe_cad_object(start_port_sheet_obj, start_port_sheet_name))
        reference_conductors = txdd_start_stub_reference_names_by_board.get(board_id, [])
        if len(reference_conductors) < 1:
            raise ValueError(
                "tx_dd start port reference conductor contract violation: expected at least 1 start stub per board "
                f"(board_id={board_id}, actual={len(reference_conductors)})"
            )
        start_port_faces = modeler.get_object_faces(start_port_sheet_obj_name)
        if not start_port_faces:
            raise ValueError(
                "tx_dd start port assignment failed: no sheet faces were found "
                f"(sheet={start_port_sheet_obj_name}, board_id={board_id})"
            )
        # Match the direct HFSS COM invocation pattern (BoundarySetup.AutoIdentifyPorts)
        # using one deterministic reference conductor from the generated start stubs.
        reference_conductor_name = sorted(reference_conductors)[0]
        start_port_name = "TX_TML"
        _auto_identify_ports_direct(
            hfss=hfss,
            face_id=int(start_port_faces[0]),
            reference_conductor_name=reference_conductor_name,
            port_name=start_port_name,
            sheet_name=start_port_sheet_obj_name,
            board_id=board_id,
            context="tx_dd start port assignment",
        )
    if rxdd_start_stub_edge_by_name:
        sorted_rxdd_stub_names = sorted(rxdd_start_stub_edge_by_name)
        if len(sorted_rxdd_stub_names) < 2:
            raise ValueError(
                "rx_dd start port sheet contract violation: expected at least 2 rx_dd back stubs overall "
                f"(actual={len(sorted_rxdd_stub_names)})"
            )
        selected_rxdd_stub_names = sorted_rxdd_stub_names[:2]
        start_port_sheet_points = _sheet_points_from_edge_pair(
            dd_edge=rxdd_start_stub_edge_by_name[selected_rxdd_stub_names[0]],
            vertical_edge=rxdd_start_stub_edge_by_name[selected_rxdd_stub_names[1]],
        )
        start_port_sheet_name = "sheet_rxdd_ports"
        try:
            start_port_sheet_obj_name, start_port_sheet_obj = _create_sheet_from_points(
                modeler=modeler,
                sheet_points=start_port_sheet_points,
                sheet_name=start_port_sheet_name,
            )
        except ValueError as exc:
            message = str(exc)
            if message.startswith("Sheet loop creation failed"):
                raise ValueError(
                    "rx_dd start port sheet rectangle loop creation failed "
                    f"(name={start_port_sheet_name})"
                ) from exc
            if message.startswith("Sheet cover_lines failed"):
                raise ValueError(
                    "rx_dd start port sheet cover_lines failed "
                    f"(name={start_port_sheet_name})"
                ) from exc
            raise
        object_names.append(start_port_sheet_obj_name)
        cad_probe.append(_probe_cad_object(start_port_sheet_obj, start_port_sheet_name))
        start_port_faces = modeler.get_object_faces(start_port_sheet_obj_name)
        if not start_port_faces:
            raise ValueError(
                "rx_dd start port assignment failed: no sheet faces were found "
                f"(sheet={start_port_sheet_obj_name})"
            )
        reference_conductor_name = selected_rxdd_stub_names[0]
        board_id_context = ",".join(
            sorted(
                {
                    rxdd_start_stub_board_by_name[selected_rxdd_stub_names[0]],
                    rxdd_start_stub_board_by_name[selected_rxdd_stub_names[1]],
                }
            )
        )
        start_port_name = "RX_TML"
        _auto_identify_ports_direct(
            hfss=hfss,
            face_id=int(start_port_faces[0]),
            reference_conductor_name=reference_conductor_name,
            port_name=start_port_name,
            sheet_name=start_port_sheet_obj_name,
            board_id=board_id_context,
            context="rx_dd start port assignment",
        )

    for (_board_id, board_idx), terminal_edges in sorted(tx_vertical_mode2_terminal_edges_by_board.items()):
        _apply_existing_edge_bridge_conductor(
            modeler=modeler,
            cu_thickness=cu_thickness,
            first_edge=terminal_edges["right_end_edge"],
            first_object_name=terminal_edges["right_end_object_name"],
            second_edge=terminal_edges["left_start_edge"],
            second_object_name=terminal_edges["left_start_object_name"],
            group_objects=group_objects,
            group_key="tx_vertical",
            object_names=object_names,
            cad_probe=cad_probe,
            bridge_name=f"bridge_tx_vertical_mode2_pair_b{board_idx}_{design_id}",
            bridge_error_context="tx_vertical mode2 pair bridge with source coils",
            region_kind="tx_region_vertical",
            region_min=tx_vertical_region_min,
            region_max=tx_vertical_region_max,
            placement_violations=placement_violations,
            x_jog_mm=TX_VERTICAL_MODE2_PAIR_JOG_X_MM,
        )

    for (board_id, board_idx), nodes in tx_vertical_nodes_by_board.items():
        if len(nodes) < 2:
            continue
        sorted_nodes = sorted(nodes, key=lambda node: node[4])
        for idx in range(len(sorted_nodes) - 1):
            (
                source_index,
                _source_name,
                _source_start_xyz,
                _source_end_xyz,
                _source_y_center,
                source_trace,
                source_bridge_out_edge,
                _source_bridge_in_edge,
            ) = sorted_nodes[idx]
            (
                target_index,
                _target_name,
                _target_start_xyz,
                _target_end_xyz,
                _target_y_center,
                target_trace,
                _target_bridge_out_edge,
                target_bridge_in_edge,
            ) = sorted_nodes[idx + 1]
            if abs(source_trace - target_trace) > 1e-9:
                raise ValueError(
                    "tx_vertical bridge trace mismatch between adjacent nodes "
                    f"(board_id={board_id}, source_index={source_index}, target_index={target_index}, "
                    f"source_trace={source_trace}, target_trace={target_trace})"
                )
            source_edge_0, source_edge_1 = source_bridge_out_edge
            target_edge_0, target_edge_1 = target_bridge_in_edge
            bridge_sheet_points = [
                [source_edge_0[0], source_edge_0[1], source_edge_0[2]],
                [source_edge_1[0], source_edge_1[1], source_edge_1[2]],
                [target_edge_1[0], target_edge_1[1], target_edge_1[2]],
                [target_edge_0[0], target_edge_0[1], target_edge_0[2]],
            ]
            bridge_name = f"bridge_tx_vertical_link_g{source_index}_to_g{target_index}_b{board_idx}_{design_id}"
            try:
                bridge_obj_name, bridge_obj = _create_thickened_sheet_from_points(
                    modeler=modeler,
                    sheet_points=bridge_sheet_points,
                    sheet_name=bridge_name,
                    thickness=(cu_thickness * 4.0),
                )
            except ValueError as exc:
                message = str(exc)
                if message.startswith("Sheet loop creation failed"):
                    raise ValueError(
                        "tx_vertical bridge rectangle loop creation failed "
                        f"(name={bridge_name}, source_index={source_index}, target_index={target_index})"
                    ) from exc
                if message.startswith("Sheet cover_lines failed"):
                    raise ValueError(
                        "tx_vertical bridge cover_lines failed "
                        f"(name={bridge_name}, source_index={source_index}, target_index={target_index})"
                    ) from exc
                if message.startswith("Sheet thicken failed"):
                    raise ValueError(
                        "tx_vertical bridge thicken failed "
                        f"(name={bridge_name}, thickness={cu_thickness * 4.0})"
                    ) from exc
                raise
            object_names.append(bridge_obj_name)
            group_objects["tx_vertical"].append(bridge_obj_name)
            bridge_probe = _probe_cad_object(bridge_obj, bridge_name)
            cad_probe.append(bridge_probe)
            bridge_violations = _bbox_violations(
                object_name=bridge_obj_name,
                bbox=bridge_probe["bbox"],
                region_kind="tx_region_vertical",
                region_min=tx_vertical_region_min,
                region_max=tx_vertical_region_max,
            )
            if bridge_violations:
                placement_violations.extend(bridge_violations)
                first = bridge_violations[0]
                raise ValueError(
                    f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
                    f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
                )

    if 0 in txdd_right_a_points and 1 in txdd_right_a_points:
        lower_a, lower_trace = txdd_right_a_points[0]
        upper_a, upper_trace = txdd_right_a_points[1]
        if abs(lower_trace - upper_trace) > 1e-9:
            raise ValueError(
                "tx_dd layer bridge contract violation: lower/upper A trace must match "
                f"(lower_trace={lower_trace}, upper_trace={upper_trace})"
            )
        bridge_trace = lower_trace
        alignment_eps = 1e-6
        if abs(lower_a[0] - upper_a[0]) > alignment_eps or abs(lower_a[1] - upper_a[1]) > alignment_eps:
            raise ValueError(
                "tx_dd layer bridge contract violation: raw A anchors are not aligned "
                f"(lower_A={lower_a}, upper_A={upper_a})"
            )
        bridge_height = abs(upper_a[2] - lower_a[2])
        if bridge_height <= 1e-9:
            raise ValueError("tx_dd layer bridge contract violation: bridge height must be > 0")
        bridge_center_x = (lower_a[0] + upper_a[0]) / 2.0
        bridge_center_y = (lower_a[1] + upper_a[1]) / 2.0
        bridge_origin = [bridge_center_x - (bridge_trace / 2.0), bridge_center_y - (bridge_trace / 2.0), min(lower_a[2], upper_a[2])]
        bridge_sizes = [bridge_trace, bridge_trace, bridge_height]
        bridge_name = f"bridge_tx_dd_a_link_{design_id}"
        bridge_created = modeler.create_box(origin=bridge_origin, sizes=bridge_sizes, name=bridge_name, material="copper")
        if not bridge_created:
            raise ValueError("tx_dd layer bridge creation failed " f"(name={bridge_name}, origin={bridge_origin}, sizes={bridge_sizes})")
        bridge_obj = cast(Object3d, bridge_created)
        bridge_object_name = _object_name(bridge_obj, bridge_name)
        txdd_bridge_object_name = bridge_object_name
        object_names.append(bridge_object_name)
        group_objects["tx_dd"].append(bridge_object_name)
        cad_probe.append(_probe_cad_object(bridge_obj, bridge_name))

    if txdd_bridge_object_name is not None and 0 in txdd_right_object_names and 1 in txdd_right_object_names:
        txdd_unite_targets = [txdd_right_object_names[0], txdd_bridge_object_name, txdd_right_object_names[1]]
        united_object_name = safe_unite(
            modeler=modeler,
            targets=txdd_unite_targets,
            fallback_name=txdd_unite_targets[0],
            error_context="tx_dd right-layer bridge group",
        )
        group_objects["tx_dd"] = [name for name in group_objects["tx_dd"] if name not in txdd_unite_targets[1:]]
        if united_object_name not in group_objects["tx_dd"]:
            group_objects["tx_dd"].append(united_object_name)
        object_names = [name for name in object_names if name not in txdd_unite_targets[1:]]
        if united_object_name not in object_names:
            object_names.append(united_object_name)
        if txdd_right_d_object_name_active in txdd_unite_targets:
            txdd_right_d_object_name_active = united_object_name

    if 0 in txdd_left_a_points and 1 in txdd_left_a_points:
        lower_a, lower_trace = txdd_left_a_points[0]
        upper_a, upper_trace = txdd_left_a_points[1]
        if abs(lower_trace - upper_trace) > 1e-9:
            raise ValueError(
                "tx_dd left layer bridge contract violation: lower/upper A trace must match "
                f"(lower_trace={lower_trace}, upper_trace={upper_trace})"
            )
        bridge_trace = lower_trace
        alignment_eps = 1e-6
        if abs(lower_a[0] - upper_a[0]) > alignment_eps or abs(lower_a[1] - upper_a[1]) > alignment_eps:
            raise ValueError(
                "tx_dd left layer bridge contract violation: raw A anchors are not aligned "
                f"(lower_A={lower_a}, upper_A={upper_a})"
            )
        bridge_height = abs(upper_a[2] - lower_a[2])
        if bridge_height <= 1e-9:
            raise ValueError("tx_dd left layer bridge contract violation: bridge height must be > 0")
        bridge_center_x = (lower_a[0] + upper_a[0]) / 2.0
        bridge_center_y = (lower_a[1] + upper_a[1]) / 2.0
        bridge_origin = [bridge_center_x - (bridge_trace / 2.0), bridge_center_y - (bridge_trace / 2.0), min(lower_a[2], upper_a[2])]
        bridge_sizes = [bridge_trace, bridge_trace, bridge_height]
        bridge_name = f"bridge_tx_dd_left_a_link_{design_id}"
        bridge_created = modeler.create_box(origin=bridge_origin, sizes=bridge_sizes, name=bridge_name, material="copper")
        if not bridge_created:
            raise ValueError(
                "tx_dd left layer bridge creation failed "
                f"(name={bridge_name}, origin={bridge_origin}, sizes={bridge_sizes})"
            )
        bridge_obj = cast(Object3d, bridge_created)
        bridge_object_name = _object_name(bridge_obj, bridge_name)
        txdd_left_bridge_object_name = bridge_object_name
        object_names.append(bridge_object_name)
        group_objects["tx_dd"].append(bridge_object_name)
        cad_probe.append(_probe_cad_object(bridge_obj, bridge_name))

    if txdd_left_bridge_object_name is not None and 0 in txdd_left_object_names and 1 in txdd_left_object_names:
        txdd_left_unite_targets = [txdd_left_object_names[0], txdd_left_bridge_object_name, txdd_left_object_names[1]]
        left_united_object_name = safe_unite(
            modeler=modeler,
            targets=txdd_left_unite_targets,
            fallback_name=txdd_left_unite_targets[0],
            error_context="tx_dd left-layer bridge group",
        )
        group_objects["tx_dd"] = [name for name in group_objects["tx_dd"] if name not in txdd_left_unite_targets[1:]]
        if left_united_object_name not in group_objects["tx_dd"]:
            group_objects["tx_dd"].append(left_united_object_name)
        object_names = [name for name in object_names if name not in txdd_left_unite_targets[1:]]
        if left_united_object_name not in object_names:
            object_names.append(left_united_object_name)
        if txdd_left_vertical_link_object_name_active in txdd_left_unite_targets:
            txdd_left_vertical_link_object_name_active = left_united_object_name

    tx_vertical_unite_targets = sorted(set(group_objects["tx_vertical"]))
    if len(tx_vertical_unite_targets) > 1:
        tx_vertical_united_name = safe_unite(
            modeler=modeler,
            targets=tx_vertical_unite_targets,
            fallback_name=tx_vertical_unite_targets[0],
            error_context="tx_vertical group",
        )
        group_objects["tx_vertical"] = [tx_vertical_united_name]
        object_names = [name for name in object_names if name not in tx_vertical_unite_targets[1:]]
        if tx_vertical_united_name not in object_names:
            object_names.append(tx_vertical_united_name)

    if tx_vertical_unite_targets:
        if txdd_global_right_d_edge is None:
            raise ValueError("tx_dd global right d-edge points were not captured")
        if tx_vertical_global_outer_right_edge is None:
            raise ValueError("tx_vertical global outer-right edge points were not captured")
        dd_to_vertical_sheet_points = _sheet_points_from_edge_pair(
            dd_edge=txdd_global_right_d_edge,
            vertical_edge=tx_vertical_global_outer_right_edge,
        )
        dd_to_vertical_bridge_name = f"bridge_tx_dd_to_tx_vertical_{design_id}"
        try:
            dd_to_vertical_obj_name, dd_to_vertical_obj = _create_thickened_sheet_from_points(
                modeler=modeler,
                sheet_points=dd_to_vertical_sheet_points,
                sheet_name=dd_to_vertical_bridge_name,
                thickness=(cu_thickness * 4.0),
            )
        except ValueError as exc:
            message = str(exc)
            if message.startswith("Sheet loop creation failed"):
                raise ValueError(
                    "tx_dd_to_tx_vertical bridge rectangle loop creation failed "
                    f"(name={dd_to_vertical_bridge_name})"
                ) from exc
            if message.startswith("Sheet cover_lines failed"):
                raise ValueError(
                    "tx_dd_to_tx_vertical bridge cover_lines failed "
                    f"(name={dd_to_vertical_bridge_name})"
                ) from exc
            if message.startswith("Sheet thicken failed"):
                raise ValueError(
                    "tx_dd_to_tx_vertical bridge thicken failed "
                    f"(name={dd_to_vertical_bridge_name}, thickness={cu_thickness * 4.0})"
                ) from exc
            raise
        object_names.append(dd_to_vertical_obj_name)
        group_objects["tx_vertical"].append(dd_to_vertical_obj_name)
        cad_probe.append(_probe_cad_object(dd_to_vertical_obj, dd_to_vertical_bridge_name))
        if txdd_right_d_object_name_active is None:
            raise ValueError("tx_dd global right d-edge object name was not captured")
        tx_connect_unite_targets = sorted(set([txdd_right_d_object_name_active] + group_objects["tx_vertical"]))
        if len(tx_connect_unite_targets) > 1:
            tx_connect_united_name = safe_unite(
                modeler=modeler,
                targets=tx_connect_unite_targets,
                fallback_name=tx_connect_unite_targets[0],
                error_context="tx_dd right coil + dd_to_vertical bridge + tx_vertical group",
            )
            group_objects["tx_vertical"] = [tx_connect_united_name]
            object_names = [name for name in object_names if name not in tx_connect_unite_targets[1:]]
            if tx_connect_united_name not in object_names:
                object_names.append(tx_connect_united_name)
            if txdd_right_d_object_name_active is not None:
                _replace_object_name_in_map(
                    txdd_right_object_names,
                    old_name=txdd_right_d_object_name_active,
                    new_name=tx_connect_united_name,
                )
                _replace_object_name_in_map(
                    txdd_left_object_names,
                    old_name=txdd_right_d_object_name_active,
                    new_name=tx_connect_united_name,
                )
                txdd_right_d_object_name_active = tx_connect_united_name

        if tx_vertical_global_outer_left_edge is None:
            raise ValueError("tx_vertical global outer-left edge contract violation: points were not captured")
        if txdd_global_left_vertical_link_edge is None:
            raise ValueError("tx_dd global left vertical-link edge contract violation: points were not captured")
        dd_left_to_vertical_sheet_points = _sheet_points_from_edge_pair(
            dd_edge=txdd_global_left_vertical_link_edge,
            vertical_edge=tx_vertical_global_outer_left_edge,
        )
        dd_left_to_vertical_bridge_name = f"bridge_tx_dd_left_to_tx_vertical_{design_id}"
        try:
            dd_left_to_vertical_obj_name, dd_left_to_vertical_obj = _create_thickened_sheet_from_points(
                modeler=modeler,
                sheet_points=dd_left_to_vertical_sheet_points,
                sheet_name=dd_left_to_vertical_bridge_name,
                thickness=(cu_thickness * 4.0),
            )
        except ValueError as exc:
            message = str(exc)
            if message.startswith("Sheet loop creation failed"):
                raise ValueError(
                    "tx_dd_left_to_tx_vertical bridge rectangle loop creation failed "
                    f"(name={dd_left_to_vertical_bridge_name})"
                ) from exc
            if message.startswith("Sheet cover_lines failed"):
                raise ValueError(
                    "tx_dd_left_to_tx_vertical bridge cover_lines failed "
                    f"(name={dd_left_to_vertical_bridge_name})"
                ) from exc
            if message.startswith("Sheet thicken failed"):
                raise ValueError(
                    "tx_dd_left_to_tx_vertical bridge thicken failed "
                    f"(name={dd_left_to_vertical_bridge_name}, thickness={cu_thickness * 4.0})"
                ) from exc
            raise
        object_names.append(dd_left_to_vertical_obj_name)
        group_objects["tx_vertical"].append(dd_left_to_vertical_obj_name)
        cad_probe.append(_probe_cad_object(dd_left_to_vertical_obj, dd_left_to_vertical_bridge_name))
        if txdd_left_vertical_link_object_name_active is None:
            raise ValueError("tx_dd global left vertical-link edge contract violation: object name was not captured")
        tx_left_connect_unite_targets = sorted(set([txdd_left_vertical_link_object_name_active] + group_objects["tx_vertical"]))
        if len(tx_left_connect_unite_targets) > 1:
            tx_left_connect_united_name = safe_unite(
                modeler=modeler,
                targets=tx_left_connect_unite_targets,
                fallback_name=tx_left_connect_unite_targets[0],
                error_context="tx_dd left vertical-link coil + dd_left_to_vertical bridge + tx_vertical group",
            )
            group_objects["tx_vertical"] = [tx_left_connect_united_name]
            object_names = [name for name in object_names if name not in tx_left_connect_unite_targets[1:]]
            if tx_left_connect_united_name not in object_names:
                object_names.append(tx_left_connect_united_name)
            if txdd_left_vertical_link_object_name_active is not None:
                _replace_object_name_in_map(
                    txdd_right_object_names,
                    old_name=txdd_left_vertical_link_object_name_active,
                    new_name=tx_left_connect_united_name,
                )
                _replace_object_name_in_map(
                    txdd_left_object_names,
                    old_name=txdd_left_vertical_link_object_name_active,
                    new_name=tx_left_connect_united_name,
                )
                txdd_left_vertical_link_object_name_active = tx_left_connect_united_name

    eps_len = 1e-6
    grouped_plane_bboxes: dict[tuple[str, Literal["XY", "YZ", "ZX"], int], list[float]] = {}
    fr4_role_by_name: dict[str, Literal["tx", "rx"]] = {}
    fr4_plane_by_name: dict[str, Literal["XY", "YZ", "ZX"]] = {}
    for board_id, plane, bbox in coil_plane_bboxes:
        if len(bbox) < 6:
            continue
        if plane == "XY":
            axis_center = (bbox[2] + bbox[5]) / 2.0
            layer_key = int(round(axis_center / eps_len))
        elif plane == "YZ":
            axis_center = (bbox[0] + bbox[3]) / 2.0
            layer_key = int(round(axis_center / eps_len))
        else:
            axis_center = (bbox[1] + bbox[4]) / 2.0
            layer_key = int(round(axis_center / eps_len))
        key = (board_id, plane, layer_key)
        existing = grouped_plane_bboxes.get(key)
        if existing is None:
            grouped_plane_bboxes[key] = list(bbox[:6])
        else:
            existing[0] = min(existing[0], bbox[0])
            existing[1] = min(existing[1], bbox[1])
            existing[2] = min(existing[2], bbox[2])
            existing[3] = max(existing[3], bbox[3])
            existing[4] = max(existing[4], bbox[4])
            existing[5] = max(existing[5], bbox[5])

    for layer_idx, ((board_id, plane, _), bbox) in enumerate(sorted(grouped_plane_bboxes.items())):
        origin, sizes = _fr4_box_from_plane_bbox(
            plane=plane,
            bbox=bbox,
            pcb_thickness=pcb_thickness,
            overlap_mm=FR4_SUBTRACT_OVERLAP_MM,
            eps_len=eps_len,
        )

        substrate_name = f"fr4_{board_id}_{plane.lower()}_{layer_idx}_{design_id}"
        substrate = cast(Object3d, modeler.create_box(origin=origin, sizes=sizes, name=substrate_name, material="FR4_epoxy"))
        substrate_object_name = _object_name(substrate, substrate_name)
        substrate_role: Literal["tx", "rx"] = "tx" if board_id in tx_board_ids else "rx"
        object_names.append(substrate_object_name)
        fr4_object_names.append(substrate_object_name)
        fr4_role_by_name[substrate_object_name] = substrate_role
        fr4_plane_by_name[substrate_object_name] = plane
        if plane != "XY" and substrate_role == "tx":
            tx_vertical_fr4_names.append(substrate_object_name)
        cad_probe.append(_probe_cad_object(substrate, substrate_name))

    if len(tx_vertical_fr4_names) > 1:
        tx_vertical_fr4_targets = sorted(set(tx_vertical_fr4_names))
        tx_vertical_fr4_plane = fr4_plane_by_name.get(tx_vertical_fr4_targets[0], "ZX")
        tx_vertical_fr4_united_name = safe_unite(
            modeler=modeler,
            targets=tx_vertical_fr4_targets,
            fallback_name=tx_vertical_fr4_targets[0],
            error_context="tx vertical FR4 group",
        )
        fr4_object_names = [name for name in fr4_object_names if name not in tx_vertical_fr4_targets[1:]]
        for removed_name in tx_vertical_fr4_targets[1:]:
            fr4_role_by_name.pop(removed_name, None)
            fr4_plane_by_name.pop(removed_name, None)
        if tx_vertical_fr4_united_name not in fr4_object_names:
            fr4_object_names.append(tx_vertical_fr4_united_name)
        fr4_role_by_name[tx_vertical_fr4_united_name] = "tx"
        fr4_plane_by_name[tx_vertical_fr4_united_name] = tx_vertical_fr4_plane
        object_names = [name for name in object_names if name not in tx_vertical_fr4_targets[1:]]
        if tx_vertical_fr4_united_name not in object_names:
            object_names.append(tx_vertical_fr4_united_name)

    live_object_names = set(object_names)
    tx_tools = sorted(
        name for name in set(group_objects["tx_dd"] + group_objects["tx_vertical"]) if name in live_object_names
    )
    if not tx_tools:
        tx_tools = _tx_dd_xy_tools(
            txdd_right_object_names=txdd_right_object_names,
            txdd_left_object_names=txdd_left_object_names,
            group_objects=group_objects,
            live_object_names=live_object_names,
        )
    rx_tools = sorted(name for name in set(group_objects["rx_dd"]) if name in live_object_names)
    for fr4_name in sorted(set(fr4_object_names)):
        fr4_role = fr4_role_by_name.get(fr4_name)
        fr4_plane = fr4_plane_by_name.get(fr4_name)
        if fr4_role is None or fr4_plane is None:
            continue
        fr4_tools = tx_tools if fr4_role == "tx" else rx_tools
        if fr4_plane == "XY" and fr4_role == "tx" and not fr4_tools:
            raise ValueError("No live tx_dd XY tools found for FR4 subtraction")
        if not fr4_tools:
            continue
        for tool_name in fr4_tools:
            if fr4_name == tool_name:
                continue
            subtract_ok = modeler.subtract(blank_list=[fr4_name], tool_list=[tool_name], keep_originals=True)
            if not subtract_ok:
                raise ValueError(
                    "Failed to subtract copper solid from FR4 substrate "
                    f"(plane={fr4_plane}, role={fr4_role}, fr4_name={fr4_name}, "
                    f"tool_name={tool_name}, overlap_mm={FR4_SUBTRACT_OVERLAP_MM})"
                )

    hfss.save_project(str(aedt_path))
    return object_names, fr4_object_names


def finalize_solids_and_substrates(
    *,
    modeler: Modeler3D,
    hfss: Hfss,
    aedt_path: Path,
    design_id: str,
    cu_thickness: float,
    pcb_thickness: float,
    tx_board_ids: set[str],
    tx_vertical_nodes_by_board: dict[_BoardKey, list[_TxVerticalLinkNode]],
    tx_vertical_mode2_terminal_edges_by_board: dict[_BoardKey, _TxVerticalMode2TerminalEdges],
    tx_vertical_region_min: _Point3,
    tx_vertical_region_max: _Point3,
    txdd_right_a_points: dict[int, tuple[_Point3, float]],
    txdd_right_object_names: dict[int, str],
    txdd_left_a_points: dict[int, tuple[_Point3, float]],
    txdd_left_object_names: dict[int, str],
    txdd_start_stub_sources: dict[str, list[_TxDdStartStubSource]],
    rxdd_back_stub_sources: list[_RxDdBackStubSource],
    group_objects: GroupObjects,
    object_names: list[str],
    cad_probe: list[CadProbe],
    placement_violations: list[RegionViolation],
    coil_plane_bboxes: list[tuple[str, Literal["XY", "YZ", "ZX"], list[float]]],
    fr4_object_names: list[str],
    tx_vertical_fr4_names: list[str],
    txdd_global_right_d_edge: _Edge2P | None,
    txdd_global_right_d_object_name: str | None,
    txdd_global_left_vertical_link_edge: _Edge2P | None,
    txdd_global_left_vertical_link_object_name: str | None,
    tx_vertical_global_outer_right_edge: _Edge2P | None,
    tx_vertical_global_outer_left_edge: _Edge2P | None,
) -> tuple[list[str], list[str]]:
    return _finalize_solids_and_substrates_impl(
        modeler=modeler,
        hfss=hfss,
        aedt_path=aedt_path,
        design_id=design_id,
        cu_thickness=cu_thickness,
        pcb_thickness=pcb_thickness,
        tx_board_ids=tx_board_ids,
        tx_vertical_nodes_by_board=tx_vertical_nodes_by_board,
        tx_vertical_mode2_terminal_edges_by_board=tx_vertical_mode2_terminal_edges_by_board,
        tx_vertical_region_min=tx_vertical_region_min,
        tx_vertical_region_max=tx_vertical_region_max,
        txdd_right_a_points=txdd_right_a_points,
        txdd_right_object_names=txdd_right_object_names,
        txdd_left_a_points=txdd_left_a_points,
        txdd_left_object_names=txdd_left_object_names,
        txdd_start_stub_sources=txdd_start_stub_sources,
        rxdd_back_stub_sources=rxdd_back_stub_sources,
        group_objects=group_objects,
        object_names=object_names,
        cad_probe=cad_probe,
        placement_violations=placement_violations,
        coil_plane_bboxes=coil_plane_bboxes,
        fr4_object_names=fr4_object_names,
        tx_vertical_fr4_names=tx_vertical_fr4_names,
        txdd_global_right_d_edge=txdd_global_right_d_edge,
        txdd_global_right_d_object_name=txdd_global_right_d_object_name,
        txdd_global_left_vertical_link_edge=txdd_global_left_vertical_link_edge,
        txdd_global_left_vertical_link_object_name=txdd_global_left_vertical_link_object_name,
        tx_vertical_global_outer_right_edge=tx_vertical_global_outer_right_edge,
        tx_vertical_global_outer_left_edge=tx_vertical_global_outer_left_edge,
    )


def build_em_artifacts(
    *,
    selected: dict[str, object],
    object_names: list[str],
    group_objects: GroupObjects,
    group_endpoints: list[GroupEndpointEntry],
    scene_objects: list[SceneObjectEntry],
) -> tuple[EmReadyObjects, EmEndpoints, EmContext]:
    em_ready_objects: EmReadyObjects = {
        "tx_conductors": sorted(group_objects["tx_dd"] + group_objects["tx_vertical"]),
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

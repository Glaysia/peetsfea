from __future__ import annotations


from .build_common import *
from .build_port_ops import _shift_edge_along_y
from .build_topology_ops import _anti_parallel_bridge_sheet_points_from_landings
from .build_sheet_ops import _create_thickened_sheet_from_points, _rxdd_connect_sheet_points_from_anchor_pair, _sheet_points_from_edge_pair


_UNSET = object()

def _rxdd_stub_attach_center_from_anchor(
    *,
    anchor_xyz: _Point3,
    trace: float,
    inward_dir: _Point3,
    has_inward_dir: bool = True,
) -> _Point3:
    if trace <= 0.0:
        raise ValueError(f"rx_dd stub trace must be > 0 (actual={trace})")
    if not has_inward_dir:
        return anchor_xyz
    half_trace = trace / 2.0
    return (
        anchor_xyz[0] + (inward_dir[0] * half_trace),
        anchor_xyz[1] + (inward_dir[1] * half_trace),
        anchor_xyz[2] + (inward_dir[2] * half_trace),
    )

def _rxdd_back_stub_source_parts(
    source: _RxDdBackStubSource,
) -> tuple[str, int, str, _Point3, float, str, bool, _Point3]:
    if len(source) == 6:
        board_id, instance_index, endpoint_label, anchor_xyz, trace, source_object_name = source
        return board_id, instance_index, endpoint_label, anchor_xyz, trace, source_object_name, False, anchor_xyz
    board_id, instance_index, endpoint_label, anchor_xyz, trace, source_object_name, inward_dir = source
    return board_id, instance_index, endpoint_label, anchor_xyz, trace, source_object_name, True, inward_dir

def _rxdd_back_stub_sort_key(source: _RxDdBackStubSource) -> tuple[str, int, str]:
    board_id, instance_index, endpoint_label, *_ = source
    return board_id, instance_index, endpoint_label

def _rxdd_back_stub_origin_and_sizes(
    *,
    anchor_xyz: _Point3,
    trace: float,
    length: float = RX_DD_BACK_STUB_LEN_MM,
) -> tuple[list[float], list[float]]:
    if trace <= 0.0:
        raise ValueError(f"rx_dd back stub trace must be > 0 (actual={trace})")
    if length <= 0.0:
        raise ValueError(f"rx_dd back stub length must be > 0 (actual={length})")
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

def _rxdd_back_stub_bridge_edge(
    *,
    anchor_xyz: _Point3,
    trace: float,
    length: float = RX_DD_BACK_STUB_LEN_MM,
) -> _Edge2P:
    if trace <= 0.0:
        raise ValueError(f"rx_dd back stub bridge trace must be > 0 (actual={trace})")
    if length <= 0.0:
        raise ValueError(f"rx_dd back stub bridge length must be > 0 (actual={length})")
    x_at_back = anchor_xyz[0] + (RX_DD_BACK_STUB_AXIS_SIGN_X * length)
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
    endpoint_labels: tuple[str, str] = ("c", "d"),
    stub_length_mm: float = RX_DD_BACK_STUB_LEN_MM,
    group_objects: GroupObjects,
    group_key: Literal["rx_dd", "tx_vertical"],
    object_names: list[str],
    cad_probe: list[CadProbe],
    bridge_name: str,
    stub_name_prefix: str,
    stub_error_context: str,
    bridge_error_context: str,
    sheet_points_builder: Callable[..., list[list[float]]] = _sheet_points_from_edge_pair,
    region_kind: object = _UNSET,
    region_min: object = _UNSET,
    region_max: object = _UNSET,
    placement_violations: object = _UNSET,
) -> None:
    if not sources:
        return
    first_endpoint_label, second_endpoint_label = endpoint_labels
    if first_endpoint_label == second_endpoint_label:
        raise ValueError(
            f"{group_key} back connect-stub endpoint labels must be distinct "
            f"(labels={endpoint_labels})"
        )
    allowed_endpoint_labels = {first_endpoint_label, second_endpoint_label}
    allowed_endpoint_text = "/".join(endpoint_labels)

    name_replacements: dict[str, str] = {}
    connect_stub_edges: dict[str, _Edge2P] = {}
    connect_stub_anchor_xyz_by_endpoint: dict[str, _Point3] = {}
    connect_stub_trace_by_endpoint: dict[str, float] = {}
    connect_source_names: dict[str, str] = {}

    def _resolve_replaced_name(name: str) -> str:
        current = name
        for _ in range(10):
            if current not in name_replacements:
                return current
            next_name = name_replacements[current]
            if next_name == current:
                return current
            current = next_name
        raise ValueError(f"{group_key} replacement chain too deep (name={name})")

    def _check_region(*, object_name: str, bbox: list[float]) -> None:
        if region_kind is _UNSET or region_min is _UNSET or region_max is _UNSET:
            return
        violations = _bbox_violations(
            object_name=object_name,
            bbox=bbox,
            region_kind=cast(_RegionKind, region_kind),
            region_min=cast(_Point3, region_min),
            region_max=cast(_Point3, region_max),
        )
        if not violations:
            return
        if placement_violations is not _UNSET:
            assert isinstance(placement_violations, list), "placement_violations must be a list"
            placement_violations.extend(violations)
        first = violations[0]
        raise ValueError(
            f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
            f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
        )

    for raw_source in sorted(
        sources,
        key=_rxdd_back_stub_sort_key,
    ):
        board_id, instance_index, endpoint_label, anchor_xyz, trace, source_object_name_raw, has_inward_dir, inward_dir = _rxdd_back_stub_source_parts(raw_source)
        if endpoint_label not in allowed_endpoint_labels:
            raise ValueError(
                f"{group_key} back connect-stub endpoint must be {allowed_endpoint_text} only "
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
        stub_anchor_xyz = _rxdd_stub_attach_center_from_anchor(
            anchor_xyz=anchor_xyz,
            trace=trace,
            inward_dir=inward_dir,
            has_inward_dir=has_inward_dir,
        )
        stub_origin, stub_sizes = _rxdd_back_stub_origin_and_sizes(
            anchor_xyz=stub_anchor_xyz,
            trace=trace,
            length=stub_length_mm,
        )
        stub_name = f"{stub_name_prefix}_{board_id}_{instance_index}_{endpoint_label}"
        stub_created = modeler.create_box(origin=stub_origin, sizes=stub_sizes, name=stub_name, material="copper")
        if not stub_created:
            raise ValueError(
                f"{group_key} back stub creation failed "
                f"(name={stub_name}, source={source_object_name}, origin={stub_origin}, sizes={stub_sizes})"
            )
        stub_obj = cast(Object3d, stub_created)
        stub_object_name = _object_name(stub_obj)
        object_names.append(stub_object_name)
        group_objects[group_key].append(stub_object_name)
        stub_probe = _probe_cad_object(stub_obj)
        cad_probe.append(stub_probe)
        _check_region(object_name=stub_object_name, bbox=stub_probe["bbox"])

        stub_united_name = safe_unite(
            modeler=modeler,
            targets=[source_object_name, stub_object_name],
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
                f"{group_key} {allowed_endpoint_text} bridge contract violation: duplicate stub endpoint captured "
                f"(endpoint={endpoint_label}, board_id={board_id}, instance_index={instance_index})"
            )
        connect_stub_anchor_xyz_by_endpoint[endpoint_label] = stub_anchor_xyz
        connect_stub_trace_by_endpoint[endpoint_label] = trace
        if not (group_key == "rx_dd" and endpoint_labels == RX_DD_CONNECT_ENDPOINT_LABELS):
            connect_stub_edges[endpoint_label] = _rxdd_back_stub_bridge_edge(
                anchor_xyz=stub_anchor_xyz,
                trace=trace,
                length=stub_length_mm,
            )
        connect_source_names[endpoint_label] = source_object_name_raw

    if group_key == "rx_dd" and endpoint_labels == RX_DD_CONNECT_ENDPOINT_LABELS:
        has_first = first_endpoint_label in connect_stub_anchor_xyz_by_endpoint
        has_second = second_endpoint_label in connect_stub_anchor_xyz_by_endpoint
    else:
        has_first = first_endpoint_label in connect_stub_edges
        has_second = second_endpoint_label in connect_stub_edges
    if has_first != has_second:
        raise ValueError(
            f"{group_key} {allowed_endpoint_text} bridge contract violation: both endpoints must be present together "
            f"(has_{first_endpoint_label}={has_first}, has_{second_endpoint_label}={has_second})"
        )
    if not has_first:
        return

    first_object_name = _resolve_replaced_name(connect_source_names[first_endpoint_label])
    second_object_name = _resolve_replaced_name(connect_source_names[second_endpoint_label])
    first_exists = (first_object_name in object_names) or (first_object_name in group_objects[group_key])
    second_exists = (second_object_name in object_names) or (second_object_name in group_objects[group_key])
    if not first_exists or not second_exists:
        raise ValueError(
            f"{group_key} {allowed_endpoint_text} bridge source object missing "
            f"({first_endpoint_label}_source={first_object_name}, {second_endpoint_label}_source={second_object_name})"
        )

    if group_key == "rx_dd" and endpoint_labels == RX_DD_CONNECT_ENDPOINT_LABELS:
        first_anchor_xyz = connect_stub_anchor_xyz_by_endpoint[first_endpoint_label]
        second_anchor_xyz = connect_stub_anchor_xyz_by_endpoint[second_endpoint_label]
        first_trace = connect_stub_trace_by_endpoint[first_endpoint_label]
        second_trace = connect_stub_trace_by_endpoint[second_endpoint_label]
        dc_bridge_sheet_points = _rxdd_connect_sheet_points_from_anchor_pair(
            first_anchor_xyz=first_anchor_xyz,
            second_anchor_xyz=second_anchor_xyz,
            first_trace=first_trace,
            second_trace=second_trace,
            stub_length_mm=stub_length_mm,
        )
    else:
        first_edge = connect_stub_edges[first_endpoint_label]
        second_edge = connect_stub_edges[second_endpoint_label]
        dc_bridge_sheet_points = sheet_points_builder(dd_edge=first_edge, vertical_edge=second_edge)
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
    bridge_probe = _probe_cad_object(dc_bridge_obj)
    cad_probe.append(bridge_probe)
    _check_region(object_name=dc_bridge_obj_name, bbox=bridge_probe["bbox"])

    unite_targets = sorted(set([first_object_name, second_object_name, dc_bridge_obj_name]))
    if len(unite_targets) <= 1:
        return
    united_name = safe_unite(
        modeler=modeler,
        targets=unite_targets,
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
    endpoint_labels: tuple[str, str],
    group_objects: GroupObjects,
    group_key: Literal["rx_dd", "tx_vertical"],
    object_names: list[str],
    cad_probe: list[CadProbe],
    conductor_name: str,
    conductor_error_context: str,
    region_kind: object = _UNSET,
    region_min: object = _UNSET,
    region_max: object = _UNSET,
    placement_violations: object = _UNSET,
) -> None:
    if not sources:
        return
    first_endpoint_label, second_endpoint_label = endpoint_labels
    if first_endpoint_label == second_endpoint_label:
        raise ValueError(
            f"{group_key} diagonal connector endpoint labels must be distinct "
            f"(labels={endpoint_labels})"
        )
    allowed_endpoint_labels = {first_endpoint_label, second_endpoint_label}
    allowed_endpoint_text = "/".join(endpoint_labels)

    def _check_region(*, object_name: str, bbox: list[float]) -> None:
        if region_kind is _UNSET or region_min is _UNSET or region_max is _UNSET:
            return
        violations = _bbox_violations(
            object_name=object_name,
            bbox=bbox,
            region_kind=cast(_RegionKind, region_kind),
            region_min=cast(_Point3, region_min),
            region_max=cast(_Point3, region_max),
        )
        if not violations:
            return
        if placement_violations is not _UNSET:
            assert isinstance(placement_violations, list), "placement_violations must be a list"
            placement_violations.extend(violations)
        first = violations[0]
        raise ValueError(
            f"Coil placement out of region for {first['object_name']} in {first['region_kind']} "
            f"(axis={first['axis']}, overflow_mm={first['overflow_mm']})"
        )

    endpoints: dict[str, tuple[_Point3, float, str]] = {}
    for raw_source in sorted(
        sources,
        key=_rxdd_back_stub_sort_key,
    ):
        board_id, instance_index, endpoint_label, anchor_xyz, trace, source_object_name, has_inward_dir, inward_dir = _rxdd_back_stub_source_parts(raw_source)
        if endpoint_label not in allowed_endpoint_labels:
            raise ValueError(
                f"{group_key} diagonal connector endpoint must be {allowed_endpoint_text} only "
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
        endpoints[endpoint_label] = (
            _rxdd_stub_attach_center_from_anchor(
                anchor_xyz=anchor_xyz,
                trace=trace,
                inward_dir=inward_dir,
                has_inward_dir=has_inward_dir,
            ),
            trace,
            source_object_name,
        )

    has_first = first_endpoint_label in endpoints
    has_second = second_endpoint_label in endpoints
    if has_first != has_second:
        raise ValueError(
            f"{group_key} diagonal connector contract violation: both {allowed_endpoint_text} endpoints must be present together "
            f"(has_{first_endpoint_label}={has_first}, has_{second_endpoint_label}={has_second})"
        )
    if not has_first:
        return

    first_anchor_xyz, first_trace, first_object_name = endpoints[first_endpoint_label]
    second_anchor_xyz, second_trace, second_object_name = endpoints[second_endpoint_label]
    if abs(first_trace - second_trace) > 1e-9:
        raise ValueError(
            f"{group_key} diagonal connector trace mismatch "
            f"({first_endpoint_label}_trace={first_trace}, {second_endpoint_label}_trace={second_trace})"
        )

    conductor_created = modeler.create_polyline(
        points=[
            [first_anchor_xyz[0], first_anchor_xyz[1], first_anchor_xyz[2]],
            [second_anchor_xyz[0], second_anchor_xyz[1], second_anchor_xyz[2]],
        ],
        name=conductor_name,
        material="copper",
        xsection_type="Rectangle",
        xsection_width=first_trace,  # type: ignore[arg-type]
        xsection_height=cu_thickness,  # type: ignore[arg-type]
    )
    if not conductor_created:
        raise ValueError(f"{conductor_error_context} polyline creation failed (name={conductor_name})")
    conductor_obj = cast(Object3d, conductor_created)
    conductor_obj_name = _object_name(conductor_obj)
    object_names.append(conductor_obj_name)
    group_objects[group_key].append(conductor_obj_name)
    conductor_probe = _probe_cad_object(conductor_obj)
    cad_probe.append(conductor_probe)
    _check_region(object_name=conductor_obj_name, bbox=conductor_probe["bbox"])

    unite_targets = sorted(set([first_object_name, second_object_name, conductor_obj_name]))
    if len(unite_targets) <= 1:
        return
    united_name = safe_unite(
        modeler=modeler,
        targets=unite_targets,
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
    region_kind: object = _UNSET,
    region_min: object = _UNSET,
    region_max: object = _UNSET,
    placement_violations: object = _UNSET,
    x_jog_mm: float = 0.0,
) -> str:
    def _check_region(*, object_name: str, bbox: list[float]) -> None:
        if region_kind is _UNSET or region_min is _UNSET or region_max is _UNSET:
            return
        violations = _bbox_violations(
            object_name=object_name,
            bbox=bbox,
            region_kind=cast(_RegionKind, region_kind),
            region_min=cast(_Point3, region_min),
            region_max=cast(_Point3, region_max),
        )
        if not violations:
            return
        if placement_violations is not _UNSET:
            assert isinstance(placement_violations, list), "placement_violations must be a list"
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
        bridge_probe = _probe_cad_object(bridge_obj)
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

    # unite_targets = [first_object_name, second_object_name, *bridge_object_names]
    # united_name = safe_unite(
    #     modeler=modeler,
    #     targets=unite_targets,
    #     error_context=bridge_error_context,
    # )
    # group_objects[group_key] = [name for name in group_objects[group_key] if name not in unite_targets]
    # group_objects[group_key].append(united_name)
    # object_names[:] = [name for name in object_names if name not in unite_targets]
    # object_names.append(united_name)
    # return united_name
    return bridge_object_names[-1]


def _is_rxdd_connect_stub_endpoint(endpoint_label: str) -> bool:
    return endpoint_label in RX_DD_CONNECT_ENDPOINT_LABELS

def _is_rxdd_port_stub_endpoint(endpoint_label: str) -> bool:
    return endpoint_label in RX_DD_PORT_ENDPOINT_LABELS

def _select_rxdd_reference_conductor_name(reference_conductors_by_endpoint: dict[str, str]) -> str:
    paired_label, canonical_label = RX_DD_PORT_ENDPOINT_LABELS
    has_canonical_label = canonical_label in reference_conductors_by_endpoint
    has_paired_label = paired_label in reference_conductors_by_endpoint
    if has_canonical_label != has_paired_label:
        raise ValueError(
            "rx_dd start port reference conductor contract violation: both A and c stub names must be present together "
            f"(has_{canonical_label}={has_canonical_label}, has_{paired_label}={has_paired_label})"
        )
    if not has_canonical_label:
        raise ValueError(
            "rx_dd start port reference conductor contract violation: canonical c stub name was not captured"
        )
    return reference_conductors_by_endpoint[canonical_label]


__all__ = [
    '_rxdd_stub_attach_center_from_anchor',
    '_rxdd_back_stub_source_parts',
    '_rxdd_back_stub_sort_key',
    '_rxdd_back_stub_origin_and_sizes',
    '_rxdd_back_stub_bridge_edge',
    '_apply_back_connect_stub_pair_bridge',
    '_apply_diagonal_connect_pair_conductor',
    '_apply_existing_edge_bridge_conductor',
    '_is_rxdd_connect_stub_endpoint',
    '_is_rxdd_port_stub_endpoint',
    '_select_rxdd_reference_conductor_name',
]

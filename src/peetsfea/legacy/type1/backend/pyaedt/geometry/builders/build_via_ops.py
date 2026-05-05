from __future__ import annotations


from .build_common import *
from .build_name_ops import _replace_object_name_in_map, _replace_object_name_in_tx_series_binding_inputs, _replace_object_name_in_txdd_start_stub_sources

def _stacked_tx_dd_via_radius(*, via_diameter_mm: float) -> float:
    if via_diameter_mm <= 0.0:
        raise ValueError(f"stacked tx_dd via_diameter_mm must be > 0 (actual={via_diameter_mm})")
    return via_diameter_mm / 2.0

def _stacked_tx_dd_via_centers(*, anchor_xyz: _Point3, via_radius: float, via_count: int) -> list[_Point3]:
    if via_count == 1:
        return [anchor_xyz]
    if via_count != 4:
        raise ValueError(f"stacked tx_dd via_count must be 1 or 4 (actual={via_count})")
    return [
        (anchor_xyz[0] - via_radius, anchor_xyz[1] - via_radius, anchor_xyz[2]),
        (anchor_xyz[0] - via_radius, anchor_xyz[1] + via_radius, anchor_xyz[2]),
        (anchor_xyz[0] + via_radius, anchor_xyz[1] - via_radius, anchor_xyz[2]),
        (anchor_xyz[0] + via_radius, anchor_xyz[1] + via_radius, anchor_xyz[2]),
    ]

def _close_stacked_tx_dd_half_conductors_with_hex_vias(
    *,
    modeler: Modeler3D,
    object_names_by_layer: dict[int, str],
    via_anchor_points: dict[int, tuple[_Point3, float]],
    primary_object_name: str,
    design_id: str,
    via_site_label: str,
    via_diameter_mm: float,
    cu_thickness: float,
    pcb_thickness: float,
    group_objects: GroupObjects,
    object_names: list[str],
    cad_probe: list[CadProbe],
    txdd_start_stub_sources: dict[str, list[_TxDdStartStubSource]],
    tx_series_binding: _TxSeriesBindingInputs | _TxSeriesChainBinding,
    context: str,
) -> str:
    object_name_tag = object_name_tag_from_design_id(design_id)
    if set(object_names_by_layer.keys()) != {0, 1}:
        raise ValueError(
            f"{context} expected stacked via layer metadata for both layers "
            f"(actual_keys={sorted(object_names_by_layer.keys())}, primary_object_name={primary_object_name})"
        )
    if set(via_anchor_points.keys()) != {0, 1}:
        raise ValueError(
            f"{context} expected via anchors for both stacked layers "
            f"(actual_keys={sorted(via_anchor_points.keys())})"
        )
    unique_names = sorted(set(object_names_by_layer.values()))
    if not unique_names:
        raise ValueError(
            f"{context} expected at least one stacked via object name "
            f"(primary_object_name={primary_object_name})"
        )
    if len(unique_names) == 1:
        return unique_names[0]
    lower_anchor_xyz, lower_trace = via_anchor_points[0]
    upper_anchor_xyz, upper_trace = via_anchor_points[1]
    if abs(lower_trace - upper_trace) > 1e-9:
        raise ValueError(
            f"{context} via trace mismatch "
            f"(lower_trace={lower_trace}, upper_trace={upper_trace})"
        )
    via_anchor_xyz: _Point3 = (
        (lower_anchor_xyz[0] + upper_anchor_xyz[0]) / 2.0,
        (lower_anchor_xyz[1] + upper_anchor_xyz[1]) / 2.0,
        (lower_anchor_xyz[2] + upper_anchor_xyz[2]) / 2.0,
    )
    via_radius = _stacked_tx_dd_via_radius(via_diameter_mm=via_diameter_mm)
    via_count = 1 if lower_trace < (2.0 * via_diameter_mm) else 4
    via_origin_z = min(lower_anchor_xyz[2], upper_anchor_xyz[2])
    via_height = (max(lower_anchor_xyz[2], upper_anchor_xyz[2]) + cu_thickness) - via_origin_z
    via_object_names: list[str] = []
    for via_idx, via_center in enumerate(
        _stacked_tx_dd_via_centers(anchor_xyz=via_anchor_xyz, via_radius=via_radius, via_count=via_count)
    ):
        via_name = f"via_txdd_{via_site_label}_{via_idx}_{object_name_tag}"
        via_created = modeler.create_cylinder(
            orientation="Z",
            origin=[via_center[0], via_center[1], via_origin_z],
            radius=via_radius,
            height=via_height,
            num_sides=6,
            name=via_name,
            material="copper",
        )
        if not via_created:
            raise ValueError(
                f"{context} via creation failed "
                f"(name={via_name}, center={via_center}, radius={via_radius}, height={via_height})"
            )
        via_obj = cast(Object3d, via_created)
        via_object_name = _object_name(via_obj)
        via_object_names.append(via_object_name)
        object_names.append(via_object_name)
        group_objects["tx_dd"].append(via_object_name)
        if hasattr(via_obj, "edges"):
            cad_probe.append(_probe_cad_object(via_obj))
    if primary_object_name in unique_names:
        unite_targets = [cast(str, primary_object_name)] + [name for name in unique_names if name != primary_object_name]
    else:
        unite_targets = list(unique_names)
    unite_targets.extend(via_object_names)
    united_name = safe_unite(
        modeler=modeler,
        targets=unite_targets,
        error_context=context,
    )
    group_objects["tx_dd"] = [name for name in group_objects["tx_dd"] if name not in unite_targets]
    group_objects["tx_dd"].append(united_name)
    object_names[:] = [name for name in object_names if name not in unite_targets]
    object_names.append(united_name)
    for old_name in unique_names:
        _replace_object_name_in_map(object_names_by_layer, old_name=old_name, new_name=united_name)
        _replace_object_name_in_txdd_start_stub_sources(
            txdd_start_stub_sources,
            old_name=old_name,
            new_name=united_name,
        )
        _replace_object_name_in_tx_series_binding_inputs(
            tx_series_binding,
            old_name=old_name,
            new_name=united_name,
        )
    return united_name

def _tx_dd_xy_tools(
    *,
    txdd_right_object_names: dict[int, str],
    group_objects: GroupObjects,
    live_object_names: set[str],
) -> list[str]:
    tools = sorted(
        name
        for name in set(txdd_right_object_names.values())
        if name in live_object_names
    )
    if not tools:
        raise ValueError(
            "No live tx_dd XY tools found "
            f"(txdd_right_object_names={sorted(set(txdd_right_object_names.values()))}, "
            f"live_object_names={sorted(live_object_names)})"
        )
    return tools


__all__ = [
    '_stacked_tx_dd_via_radius',
    '_stacked_tx_dd_via_centers',
    '_close_stacked_tx_dd_half_conductors_with_hex_vias',
    '_tx_dd_xy_tools',
]

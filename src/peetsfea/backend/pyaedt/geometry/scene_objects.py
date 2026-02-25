from __future__ import annotations

from typing import Literal, cast

from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.types.manifest import CadProbe, SceneObjectEntry, SelectedParameters, SelectedParametersMax

from .cad_probe import _object_name, _probe_cad_object

_Point3 = tuple[float, float, float]

def _bounds_from_scene_entry(entry: SceneObjectEntry) -> tuple[_Point3, _Point3]:
    ox, oy, oz = entry["origin_xyz"]
    sx, sy, sz = entry["size_xyz"]
    return (ox, oy, oz), (ox + sx, oy + sy, oz + sz)


def _create_non_model_box(
    modeler: Modeler3D,
    *,
    origin: list[float],
    sizes: list[float],
    name: str,
) -> Object3d:
    try:
        obj = cast(
            Object3d,
            modeler.create_box(
                origin=origin,
                sizes=sizes,
                name=name,
                material="vacuum",
                non_model=True,
            ),
        )
    except TypeError:
        obj = cast(
            Object3d,
            modeler.create_box(
                origin=origin,
                sizes=sizes,
                name=name,
                material="vacuum",
            ),
        )
    # Keep non-model semantics explicit even when backend APIs differ.
    try:
        setattr(obj, "model", False)
    except Exception:
        pass
    try:
        set_model_state = getattr(modeler, "set_object_model_state", None)
        if callable(set_model_state):
            object_name = getattr(obj, "name", name)
            set_model_state(object_name, False)
    except Exception:
        pass
    return obj


def _create_scene_non_model_objects(
    modeler: Modeler3D,
    design_id: str,
    selected: SelectedParameters,
    selected_max: SelectedParametersMax,
) -> tuple[list[str], list[CadProbe], list[SceneObjectEntry]]:
    def _assert_positive(value: float, path: str) -> None:
        if value <= 0:
            raise ValueError(f"{path} must be > 0")

    floor_x = float(selected["floor_size_x_mm"])
    floor_y = float(selected["floor_size_y_mm"])
    floor_t = float(selected["floor_thickness_mm"])
    wall_t = float(selected["wall_thickness_mm"])
    wall_y = float(selected["wall_size_y_mm"])
    wall_z = float(selected["wall_size_z_mm"])
    tv_w = float(selected["tv_width_mm"])
    tv_h = float(selected["tv_height_mm"])
    tv_t = float(selected["tv_thickness_mm"])
    tv_base_z = float(selected["tv_base_z_mm"])
    tx_w = float(selected["tx_region_outer_w_mm"])
    tx_h = float(selected["tx_region_outer_h_mm"])
    tx_t = float(selected["tx_region_thickness_mm"])
    tx_vertical_z = float(selected["tx_region_vertical_z_mm"])
    tx_dd_z = float(selected["tx_region_dd_z_mm"])
    rx_w = float(selected["rx_region_outer_w_mm"])
    rx_h = float(selected["rx_region_outer_h_mm"])
    rx_t = float(selected["rx_region_thickness_mm"])
    shelf_height = float(selected["shelf_height_mm"])
    shelf_min_size_x = float(selected["shelf_min_size_x_mm"])
    rx_region_bottom_from_tv = float(selected["rx_region_bottom_from_tv_mm"])
    tx_w_max = float(selected_max["tx_region_outer_w_mm"])
    tx_h_max = float(selected_max["tx_region_outer_h_mm"])
    tx_t_max = float(selected_max["tx_region_thickness_mm"])
    rx_w_max = float(selected_max["rx_region_outer_w_mm"])
    rx_h_max = float(selected_max["rx_region_outer_h_mm"])
    rx_t_max = float(selected_max["rx_region_thickness_mm"])

    _assert_positive(floor_x, "floor.size_x_mm")
    _assert_positive(floor_y, "floor.size_y_mm")
    _assert_positive(floor_t, "floor.thickness_mm")
    _assert_positive(wall_t, "wall.thickness_mm")
    _assert_positive(wall_y, "wall.size_y_mm")
    _assert_positive(wall_z, "wall.size_z_mm")
    _assert_positive(tv_w, "tv.width_mm")
    _assert_positive(tv_h, "tv.height_mm")
    _assert_positive(tv_t, "tv.thickness_mm")
    _assert_positive(tx_w, "tx.region.outer_w_mm")
    _assert_positive(tx_h, "tx.region.outer_h_mm")
    _assert_positive(tx_t, "tx.region.thickness_mm")
    _assert_positive(tx_vertical_z, "tx.region.z_parts.vertical_z_mm")
    _assert_positive(tx_dd_z, "tx.region.z_parts.dd_z_mm")
    _assert_positive(rx_w, "rx.region.outer_w_mm")
    _assert_positive(rx_h, "rx.region.outer_h_mm")
    _assert_positive(rx_t, "rx.region.thickness_mm")
    _assert_positive(tx_w_max, "tx.region.outer_w_mm(max)")
    _assert_positive(tx_h_max, "tx.region.outer_h_mm(max)")
    _assert_positive(tx_t_max, "tx.region.thickness_mm(max)")
    _assert_positive(rx_w_max, "rx.region.outer_w_mm(max)")
    _assert_positive(rx_h_max, "rx.region.outer_h_mm(max)")
    _assert_positive(rx_t_max, "rx.region.thickness_mm(max)")
    _assert_positive(shelf_height, "scene_anchor.shelf_height_mm")
    _assert_positive(shelf_min_size_x, "scene_anchor.shelf_min_size_x_mm")
    if rx_region_bottom_from_tv < 0:
        raise ValueError("scene_anchor.rx_region_bottom_from_tv_mm must be >= 0")

    if tx_w > tx_w_max or tx_h > tx_h_max or tx_t > tx_t_max:
        raise ValueError("tx.region actual dimensions must be <= max dimensions")
    if rx_w > rx_w_max or rx_h > rx_h_max or rx_t > rx_t_max:
        raise ValueError("rx.region actual dimensions must be <= max dimensions")
    tx_leftover_z = tx_t - tx_vertical_z - tx_dd_z
    if tx_leftover_z < 0:
        raise ValueError("tx.region.leftover_z_mm computed negative; reduce vertical_z/dd_z or increase tx.region.thickness_mm")

    tv_x = 0.0
    # TX region is independent from coil geometry and its bottom touches shelf top.
    tx_origin_x_max = 0.0
    tx_origin_y_max = -tx_h_max / 2.0
    tx_origin_z_max = shelf_height
    shelf_x = max(shelf_min_size_x, tx_w_max * 2.5)
    shelf_y = max(tv_w, tx_h_max)
    # RX region is independent from coil geometry and anchored inside the TV volume.
    rx_origin_x = 0.0
    rx_origin_y = -rx_w / 2.0
    rx_origin_z = tv_base_z + rx_region_bottom_from_tv
    rx_origin_y_max = -rx_w_max / 2.0
    rx_origin_z_max = tv_base_z + rx_region_bottom_from_tv

    # Bottom leftover is kept as free space; DD and vertical zones are contiguous above it.
    tx_dd_origin_z = tx_origin_z_max + tx_leftover_z
    tx_vertical_origin_z = tx_dd_origin_z + tx_dd_z

    scene_specs: list[
        tuple[
            str,
            Literal[
                "tv",
                "wall",
                "floor",
                "shelf",
                "tx_region_max",
                "tx_region_vertical",
                "tx_region_dd",
                "rx_region_max",
                "rx_region_actual",
            ],
            _Point3,
            _Point3,
            Literal["XY", "YZ"],
        ]
    ] = [
        (
            f"scene_floor_{design_id}",
            "floor",
            # Start from the ZY plane (x=0) and place floor below the XY plane.
            (0.0, -floor_y / 2.0, -floor_t),
            (floor_x, floor_y, floor_t),
            "XY",
        ),
        (
            f"scene_shelf_{design_id}",
            "shelf",
            # Shelf bottom touches floor top (z=0), shelf top is z=400.
            (0.0, -shelf_y / 2.0, 0.0),
            (shelf_x, shelf_y, shelf_height),
            "XY",
        ),
        (
            f"scene_wall_{design_id}",
            "wall",
            (-wall_t, -wall_y / 2.0, 0.0),
            (wall_t, wall_y, wall_z),
            "YZ",
        ),
        (
            f"scene_tv_{design_id}",
            "tv",
            (tv_x, -tv_w / 2.0, tv_base_z),
            (tv_t, tv_w, tv_h),
            "YZ",
        ),
        (
            f"scene_tx_region_max_{design_id}",
            "tx_region_max",
            (tx_origin_x_max, tx_origin_y_max, tx_origin_z_max),
            (tx_w_max, tx_h_max, tx_t_max),
            "XY",
        ),
        (
            f"scene_tx_region_vertical_{design_id}",
            "tx_region_vertical",
            (tx_origin_x_max, tx_origin_y_max, tx_vertical_origin_z),
            (tx_w_max, tx_h_max, tx_vertical_z),
            "XY",
        ),
        (
            f"scene_tx_region_dd_{design_id}",
            "tx_region_dd",
            (tx_origin_x_max, tx_origin_y_max, tx_dd_origin_z),
            (tx_w_max, tx_h_max, tx_dd_z),
            "XY",
        ),
        (
            f"scene_rx_region_max_{design_id}",
            "rx_region_max",
            (rx_origin_x, rx_origin_y_max, rx_origin_z_max),
            (rx_t_max, rx_w_max, rx_h_max),
            "YZ",
        ),
        (
            f"scene_rx_region_actual_{design_id}",
            "rx_region_actual",
            (rx_origin_x, rx_origin_y, rx_origin_z),
            (rx_t_max, rx_w, rx_h),
            "YZ",
        ),
    ]

    names: list[str] = []
    probes: list[CadProbe] = []
    entries: list[SceneObjectEntry] = []
    for name, kind, origin_xyz, size_xyz, plane in scene_specs:
        obj = _create_non_model_box(
            modeler,
            origin=[origin_xyz[0], origin_xyz[1], origin_xyz[2]],
            sizes=[size_xyz[0], size_xyz[1], size_xyz[2]],
            name=name,
        )
        obj_name = _object_name(obj, name)
        names.append(obj_name)
        probes.append(_probe_cad_object(obj, name))
        entries.append(
            {
                "name": obj_name,
                "kind": kind,
                "present": True,
                "origin_xyz": origin_xyz,
                "size_xyz": size_xyz,
                "plane": plane,
                "non_model": True,
            }
        )
    return names, probes, entries



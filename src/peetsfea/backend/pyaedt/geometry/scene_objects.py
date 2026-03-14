from __future__ import annotations

from typing import Iterable, Literal, cast

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.types.manifest import CadProbe, SceneObjectEntry, SelectedParameters, SelectedParametersMax

from .cad_probe import _object_name, _probe_cad_object

_Point3 = tuple[float, float, float]
_FerriteKind = Literal["rx_ferrite", "tx_ferrite"]
_FERRITE_MATERIAL_NAME = "peetsfea_ferrite_mu500"

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


def _create_model_box(
    modeler: Modeler3D,
    *,
    origin: list[float],
    sizes: list[float],
    name: str,
    material: str,
) -> Object3d:
    obj = cast(
        Object3d,
        modeler.create_box(
            origin=origin,
            sizes=sizes,
            name=name,
            material=material,
        ),
    )
    try:
        setattr(obj, "model", True)
    except Exception:
        pass
    return obj


def _ensure_ferrite_material(hfss: Hfss, relative_permeability: float) -> str:
    materials = getattr(hfss, "materials", None)
    if materials is None:
        return _FERRITE_MATERIAL_NAME
    try:
        exists = bool(materials.exists_material(_FERRITE_MATERIAL_NAME))
    except Exception:
        exists = False
    try:
        material = (
            materials.material_keys.get(_FERRITE_MATERIAL_NAME)
            or materials.material_keys.get(_FERRITE_MATERIAL_NAME.lower())
            if exists and hasattr(materials, "material_keys")
            else None
        )
    except Exception:
        material = None
    if material is None:
        try:
            material = materials.add_material(_FERRITE_MATERIAL_NAME)
        except Exception:
            return _FERRITE_MATERIAL_NAME
    try:
        material.permeability = str(float(relative_permeability))
    except Exception:
        pass
    try:
        material.permittivity = "1.0"
    except Exception:
        pass
    try:
        material.conductivity = "0"
    except Exception:
        pass
    try:
        material.dielectric_loss_tangent = "0"
    except Exception:
        pass
    try:
        material.magnetic_loss_tangent = "0"
    except Exception:
        pass
    return _FERRITE_MATERIAL_NAME


def _union_bboxes(bboxes: Iterable[list[float]]) -> list[float]:
    iterator = iter(bboxes)
    try:
        first = list(next(iterator)[:6])
    except StopIteration as exc:
        raise ValueError("Cannot union an empty bbox collection") from exc
    union = first
    for bbox in iterator:
        union[0] = min(union[0], bbox[0])
        union[1] = min(union[1], bbox[1])
        union[2] = min(union[2], bbox[2])
        union[3] = max(union[3], bbox[3])
        union[4] = max(union[4], bbox[4])
        union[5] = max(union[5], bbox[5])
    return union


def _bbox_touches_or_overlaps(a: list[float], b: list[float], *, tol: float = 1e-9) -> bool:
    return not (
        a[3] < (b[0] - tol)
        or b[3] < (a[0] - tol)
        or a[4] < (b[1] - tol)
        or b[4] < (a[1] - tol)
        or a[5] < (b[2] - tol)
        or b[5] < (a[2] - tol)
    )


def _placeholder_ferrite_spec(
    *,
    design_id: str,
    kind: _FerriteKind,
    plane: Literal["XY", "YZ"],
) -> tuple[str, _FerriteKind, _Point3, _Point3, Literal["XY", "YZ"]]:
    suffix = "rx" if kind == "rx_ferrite" else "tx"
    return (f"ferrite_{suffix}_{design_id}", kind, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), plane)


def _resolve_rx_ferrite_spec(
    *,
    design_id: str,
    selected: SelectedParameters,
    scene_objects: list[SceneObjectEntry],
    coil_plane_bboxes: list[tuple[str, Literal["XY", "YZ", "ZX"], list[float]]],
    strict: bool,
) -> tuple[str, _FerriteKind, _Point3, _Point3, Literal["XY", "YZ"]]:
    rx_bboxes = [bbox for _, plane, bbox in coil_plane_bboxes if plane == "YZ"]
    if not rx_bboxes:
        if strict:
            raise ValueError("Ferrite requested but no RX YZ coil bbox was captured")
        return _placeholder_ferrite_spec(design_id=design_id, kind="rx_ferrite", plane="YZ")
    scene_by_kind = {entry["kind"]: entry for entry in scene_objects}
    tv_entry = scene_by_kind.get("tv")
    if tv_entry is None:
        raise ValueError("scene_objects is missing the TV entry required for RX ferrite placement")
    union = _union_bboxes(rx_bboxes)
    thickness = float(selected["rx_ferrite_thickness_mm"])
    ferrite_min_x = union[0] - thickness
    ferrite_max_x = union[0]
    tv_min, tv_max = _bounds_from_scene_entry(tv_entry)
    if ferrite_min_x < (tv_min[0] - 1e-9) or ferrite_max_x > (tv_max[0] + 1e-9):
        raise ValueError(
            "RX ferrite must stay inside the TV envelope "
            f"(ferrite_x=({ferrite_min_x}, {ferrite_max_x}), tv_x=({tv_min[0]}, {tv_max[0]}))"
        )
    origin_xyz: _Point3 = (ferrite_min_x, union[1], union[2])
    size_xyz: _Point3 = (thickness, union[4] - union[1], union[5] - union[2])
    return (f"ferrite_rx_{design_id}", "rx_ferrite", origin_xyz, size_xyz, "YZ")


def _resolve_tx_ferrite_spec(
    *,
    design_id: str,
    selected: SelectedParameters,
    cad_probe: list[CadProbe],
    tx_board_ids: set[str],
    strict: bool,
) -> tuple[str, _FerriteKind, _Point3, _Point3, Literal["XY", "YZ"]]:
    tx_xy_fr4_bboxes = [
        list(probe["bbox"][:6])
        for probe in cad_probe
        if any(probe["object_name"].startswith(f"fr4_{board_id}_xy_") for board_id in tx_board_ids)
    ]
    if not tx_xy_fr4_bboxes:
        if strict:
            raise ValueError("Ferrite requested but no TX XY FR4 bbox was captured")
        return _placeholder_ferrite_spec(design_id=design_id, kind="tx_ferrite", plane="XY")
    lowest_min_z = min(bbox[2] for bbox in tx_xy_fr4_bboxes)
    lowest_layer_bboxes = [bbox for bbox in tx_xy_fr4_bboxes if abs(bbox[2] - lowest_min_z) <= 1e-6]
    union = _union_bboxes(lowest_layer_bboxes)
    thickness = float(selected["tx_ferrite_thickness_mm"])
    gap_mm = float(selected["tx_ferrite_gap_mm"])
    top_z = union[2] - gap_mm
    origin_xyz: _Point3 = (union[0], union[1], top_z - thickness)
    size_xyz: _Point3 = (union[3] - union[0], union[4] - union[1], thickness)
    return (f"ferrite_tx_{design_id}", "tx_ferrite", origin_xyz, size_xyz, "XY")


def _assert_tx_ferrite_gap_from_live_objects(
    *,
    ferrite_name: str,
    origin_xyz: _Point3,
    size_xyz: _Point3,
    cad_probe: list[CadProbe],
    tx_board_ids: set[str],
) -> None:
    ferrite_bbox = [
        origin_xyz[0],
        origin_xyz[1],
        origin_xyz[2],
        origin_xyz[0] + size_xyz[0],
        origin_xyz[1] + size_xyz[1],
        origin_xyz[2] + size_xyz[2],
    ]
    tx_live_probes = [
        probe
        for probe in cad_probe
        if probe["object_name"].startswith("coil_tx_")
        or probe["object_name"].startswith("bridge_tx_")
        or probe["object_name"].startswith("sheet_tx")
        or any(probe["object_name"].startswith(f"fr4_{board_id}_") for board_id in tx_board_ids)
    ]
    for probe in tx_live_probes:
        probe_bbox = list(probe["bbox"][:6])
        if _bbox_touches_or_overlaps(ferrite_bbox, probe_bbox):
            raise ValueError(
                "TX ferrite must keep a positive gap from TX coil copper, TX bridge objects, "
                "TX port sheet objects, and TX FR4 sheet objects "
                f"(ferrite_name={ferrite_name}, live_object={probe['object_name']})"
            )


def _live_model_object_names(
    *,
    object_names: list[str],
    scene_objects: list[SceneObjectEntry],
    ferrite_names: set[str],
) -> list[str]:
    non_model_names = {entry["name"] for entry in scene_objects if entry["non_model"]}
    return sorted({name for name in object_names if name not in non_model_names and name not in ferrite_names})


def _create_ferrite_model_objects(
    modeler: Modeler3D,
    hfss: Hfss,
    design_id: str,
    selected: SelectedParameters,
    scene_objects: list[SceneObjectEntry],
    object_names: list[str],
    coil_plane_bboxes: list[tuple[str, Literal["XY", "YZ", "ZX"], list[float]]],
    cad_probe: list[CadProbe],
    tx_board_ids: set[str],
) -> tuple[list[str], list[CadProbe], list[SceneObjectEntry]]:
    ferrite_present = bool(selected["ferrite_present"])
    rx_ferrite_thickness = float(selected["rx_ferrite_thickness_mm"])
    tx_ferrite_thickness = float(selected["tx_ferrite_thickness_mm"])
    ferrite_relative_permeability = float(selected["ferrite_relative_permeability"])
    rx_region_thickness = float(selected["rx_region_thickness_mm"])
    pcb_thickness = float(selected["pcb_thickness_mm"])
    if ferrite_relative_permeability <= 1.0:
        raise ValueError("selected_parameters.ferrite_relative_permeability must be > 1.0")
    if rx_ferrite_thickness <= 0.0:
        raise ValueError("selected_parameters.rx_ferrite_thickness_mm must be > 0")
    if tx_ferrite_thickness <= 0.0:
        raise ValueError("selected_parameters.tx_ferrite_thickness_mm must be > 0")
    if (rx_ferrite_thickness + pcb_thickness) > (rx_region_thickness + 1e-9):
        raise ValueError(
            "RX ferrite thickness plus pcb_thickness_mm must be <= rx_region_thickness_mm "
            f"(rx_ferrite_thickness_mm={rx_ferrite_thickness}, pcb_thickness_mm={pcb_thickness}, rx_region_thickness_mm={rx_region_thickness})"
        )

    ferrite_specs: list[tuple[str, _FerriteKind, _Point3, _Point3, Literal["XY", "YZ"]]] = [
        _resolve_rx_ferrite_spec(
            design_id=design_id,
            selected=selected,
            scene_objects=scene_objects,
            coil_plane_bboxes=coil_plane_bboxes,
            strict=ferrite_present,
        ),
        _resolve_tx_ferrite_spec(
            design_id=design_id,
            selected=selected,
            cad_probe=cad_probe,
            tx_board_ids=tx_board_ids,
            strict=ferrite_present,
        ),
    ]

    entries: list[SceneObjectEntry] = []
    if not ferrite_present:
        for name, kind, origin_xyz, size_xyz, plane in ferrite_specs:
            entries.append(
                {
                    "name": name,
                    "kind": kind,
                    "present": False,
                    "origin_xyz": origin_xyz,
                    "size_xyz": size_xyz,
                    "plane": plane,
                    "non_model": False,
                }
            )
        return [], [], entries

    material_name = _ensure_ferrite_material(hfss, ferrite_relative_permeability)
    ferrite_names = {name for name, _, _, _, _ in ferrite_specs}
    tool_names = _live_model_object_names(object_names=object_names, scene_objects=scene_objects, ferrite_names=ferrite_names)
    if not tool_names:
        raise ValueError("Ferrite requested but no live model objects were available for subtract cutouts")
    names: list[str] = []
    probes: list[CadProbe] = []
    for name, kind, origin_xyz, size_xyz, plane in ferrite_specs:
        if kind == "tx_ferrite":
            _assert_tx_ferrite_gap_from_live_objects(
                ferrite_name=name,
                origin_xyz=origin_xyz,
                size_xyz=size_xyz,
                cad_probe=cad_probe,
                tx_board_ids=tx_board_ids,
            )
        obj = _create_model_box(
            modeler,
            origin=[origin_xyz[0], origin_xyz[1], origin_xyz[2]],
            sizes=[size_xyz[0], size_xyz[1], size_xyz[2]],
            name=name,
            material=material_name,
        )
        obj_name = _object_name(obj, name)
        subtract_ok = modeler.subtract(blank_list=[obj_name], tool_list=tool_names, keep_originals=True)
        if not subtract_ok:
            raise ValueError(
                "Failed to subtract live model objects from ferrite "
                f"(ferrite_name={obj_name}, tool_count={len(tool_names)})"
            )
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
                "non_model": False,
            }
        )
    return names, probes, entries


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

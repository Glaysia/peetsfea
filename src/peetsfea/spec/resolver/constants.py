from __future__ import annotations

from .types import _FixedPcbRule


SCALAR_RANGE_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("coil_shape.tx_dd.outer_x", "tx_dd_outer_x", False),
    ("coil_shape.tx_dd.outer_y", "tx_dd_outer_y", False),
    ("coil_shape.tx_vertical.outer_x", "tx_vertical_outer_x", False),
    ("coil_shape.tx_vertical.outer_y", "tx_vertical_outer_y", False),
    ("coil_shape.rx_dd.outer_x", "rx_dd_outer_x", False),
    ("coil_shape.rx_dd.outer_y", "rx_dd_outer_y", False),
    ("coil_shape.inner_margin_x", "inner_margin_x", False),
    ("coil_shape.inner_margin_y", "inner_margin_y", False),
    ("coil_spacing.tx_dd_pair_spacing_ratio", "tx_dd_pair_spacing_ratio", False),
    ("coil_spacing.rx_dd_pair_spacing_ratio", "rx_dd_pair_spacing_ratio", False),
    ("coil_spacing.tx_vertical_center_gap_mm", "tx_vertical_center_gap_mm", False),
    ("tv.width_mm", "tv_width_mm", False),
    ("tv.height_mm", "tv_height_mm", False),
    ("tv.thickness_mm", "tv_thickness_mm", False),
    ("tv.base_z_mm", "tv_base_z_mm", False),
    ("tx.region.outer_w_mm", "tx_region_outer_w_mm", False),
    ("tx.region.outer_h_mm", "tx_region_outer_h_mm", False),
    ("tx.region.thickness_mm", "tx_region_thickness_mm", False),
    ("tx.region.z_parts.vertical_z_mm", "tx_region_vertical_z_mm", False),
    ("tx.region.z_parts.dd_z_mm", "tx_region_dd_z_mm", False),
    ("rx.region.outer_w_mm", "rx_region_outer_w_mm", False),
    ("rx.region.outer_h_mm", "rx_region_outer_h_mm", False),
    ("rx.region.thickness_mm", "rx_region_thickness_mm", False),
    ("wall.thickness_mm", "wall_thickness_mm", False),
    ("wall.size_y_mm", "wall_size_y_mm", False),
    ("wall.size_z_mm", "wall_size_z_mm", False),
    ("floor.thickness_mm", "floor_thickness_mm", False),
    ("floor.size_x_mm", "floor_size_x_mm", False),
    ("floor.size_y_mm", "floor_size_y_mm", False),
    ("ferrite.present", "ferrite_present", True),
    ("ferrite.rx_thickness_mm", "rx_ferrite_thickness_mm", False),
    ("ferrite.tx_thickness_mm", "tx_ferrite_thickness_mm", False),
    ("ferrite.relative_permeability", "ferrite_relative_permeability", False),
    ("coil_material.via_diameter_mm", "via_diameter_mm", False),
    ("coil_material.pcb_thickness_mm", "pcb_thickness_mm", False),
    ("coil_material.cu_thickness_mm", "cu_thickness_mm", False),
    ("coil_material.fr4_er", "fr4_er", False),
    ("scene_anchor.shelf_height_mm", "shelf_height_mm", False),
    ("scene_anchor.shelf_min_size_x_mm", "shelf_min_size_x_mm", False),
    ("scene_anchor.rx_region_bottom_from_tv_mm", "rx_region_bottom_from_tv_mm", False),
    ("coil_placement.tx_dd_top_clearance_mm", "tx_dd_top_clearance_mm", False),
    ("coil_placement.rx_face_clearance_mm", "rx_face_clearance_mm", False),
    ("pcb_spacing.tx_main_1_z_from_tx_main_0_mm", "tx_main_1_z_from_tx_main_0_mm", False),
)

SCALAR_OFFSET: dict[str, int] = {path: idx for idx, (path, _, _) in enumerate(SCALAR_RANGE_SPECS)}
GROUP_KIND_ORDER: tuple[str, ...] = ("tx_dd", "tx_vertical", "rx_dd")
GROUP_OFFSET_BASE = 100
PCB_OFFSET_BASE = 200
GROUP_GEOMETRY_OFFSET_BASE = 300
PCB_SPACING_OFFSET_BASE = 400
ATTEMPT_STRIDE = 1009

REMOVED_PATHS: tuple[str, ...] = (
    "coil_shape.outer_x",
    "coil_shape.outer_y",
    "coil_spacing.tx_dd_pair_spacing_mm",
    "coil_spacing.rx_dd_pair_spacing_mm",
    "coil_spacing.tx_vertical_span_mm",
)

DERIVED_RANGE_PATHS: dict[str, str] = {
    "coil_shape.tx_vertical.outer_x": "coil_shape.tx_dd.outer_x",
}

FIXED_PCB_ORDER: tuple[str, ...] = (
    "tx_main_0",
    "tx_main_1",
    "tx_vertical_0",
    "rx_main_0",
    "rx_main_1",
    "tx_opt_0",
    "tx_opt_1",
    "rx_opt_0",
    "rx_opt_1",
)

FIXED_PCB_RULES: dict[str, _FixedPcbRule] = {
    "tx_main_0": {
        "role": "tx",
        "present": True,
        "mounts": (
            ("tx_dd", "index", 0),
            ("tx_dd", "index", 1),
        ),
    },
    "tx_main_1": {
        "role": "tx",
        "present": True,
        "mounts": (
            ("tx_dd", "index", 2),
            ("tx_dd", "index", 3),
        ),
    },
    "tx_vertical_0": {
        "role": "tx",
        "present": True,
        "mounts": (("tx_vertical", "all", None),),
    },
    "rx_main_0": {
        "role": "rx",
        "present": True,
        "mounts": (("rx_dd", "index", 0),),
    },
    "rx_main_1": {
        "role": "rx",
        "present": True,
        "mounts": (("rx_dd", "index", 1),),
    },
    "tx_opt_0": {"role": "tx", "present": False, "mounts": ()},
    "tx_opt_1": {"role": "tx", "present": False, "mounts": ()},
    "rx_opt_0": {"role": "rx", "present": False, "mounts": ()},
    "rx_opt_1": {"role": "rx", "present": False, "mounts": ()},
}

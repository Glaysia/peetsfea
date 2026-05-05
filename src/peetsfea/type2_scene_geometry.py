from __future__ import annotations

from typing import cast

import build123d as bd

from peetsfea.type2_step_ledger import CanonicalCoordinates
from peetsfea.type2_step_spec import NonModelBoxSpec
from peetsfea.type2_step_spec import Point3

_LABELED_SHAPE_MAX_LABEL_LENGTH = 32


def canonical_from_shape(shape: bd.Shape) -> CanonicalCoordinates:
    bbox = shape.bounding_box()
    min_xyz = (bbox.min.X, bbox.min.Y, bbox.min.Z)
    max_xyz = (bbox.max.X, bbox.max.Y, bbox.max.Z)
    return {
        "frame_origin_xyz": min_xyz,
        "outer_bounds_min_xyz": min_xyz,
        "outer_bounds_max_xyz": max_xyz,
        "outer_bounds_size_xyz": (max_xyz[0] - min_xyz[0], max_xyz[1] - min_xyz[1], max_xyz[2] - min_xyz[2]),
    }


def canonical_from_non_model_box(spec: NonModelBoxSpec) -> CanonicalCoordinates:
    origin_x, origin_y, origin_z = spec.origin_xyz
    size_x, size_y, size_z = spec.size_xyz
    return {
        "frame_origin_xyz": spec.origin_xyz,
        "outer_bounds_min_xyz": (origin_x, origin_y, origin_z),
        "outer_bounds_max_xyz": (origin_x + size_x, origin_y + size_y, origin_z + size_z),
        "outer_bounds_size_xyz": spec.size_xyz,
    }


def canonical_from_non_model_specs(specs: tuple[NonModelBoxSpec, ...], *, context: str) -> CanonicalCoordinates:
    if not specs:
        raise ValueError(f"{context} canonical coordinates require at least one spec")
    min_x = min(spec.origin_xyz[0] for spec in specs)
    min_y = min(spec.origin_xyz[1] for spec in specs)
    min_z = min(spec.origin_xyz[2] for spec in specs)
    max_x = max(spec.origin_xyz[0] + spec.size_xyz[0] for spec in specs)
    max_y = max(spec.origin_xyz[1] + spec.size_xyz[1] for spec in specs)
    max_z = max(spec.origin_xyz[2] + spec.size_xyz[2] for spec in specs)
    return {
        "frame_origin_xyz": (min_x, min_y, min_z),
        "outer_bounds_min_xyz": (min_x, min_y, min_z),
        "outer_bounds_max_xyz": (max_x, max_y, max_z),
        "outer_bounds_size_xyz": (max_x - min_x, max_y - min_y, max_z - min_z),
    }


def build_non_model_box_shape(spec: NonModelBoxSpec) -> bd.Shape:
    size_x, size_y, size_z = spec.size_xyz
    box = bd.Box(
        size_x,
        size_y,
        size_z,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    ).moved(bd.Location(spec.origin_xyz))
    solids = tuple(box.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "non-model box-derived STEP body must contain exactly one solid "
            f"(object_id={spec.object_id}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = spec.object_id
    return solid


def build_labeled_solid_box(
    *,
    label: str,
    origin_xyz: Point3,
    size_xyz: Point3,
) -> bd.Shape:
    if len(label) > _LABELED_SHAPE_MAX_LABEL_LENGTH:
        raise RuntimeError(
            "type2 underlay body label must be <= 32 chars "
            f"(label={label}, length={len(label)})"
        )
    size_x, size_y, size_z = size_xyz
    if size_x <= 0.0 or size_y <= 0.0 or size_z <= 0.0:
        raise RuntimeError(
            "type2 underlay body size must be positive "
            f"(label={label}, origin={origin_xyz}, size={size_xyz})"
        )
    shape = bd.Box(
        size_x,
        size_y,
        size_z,
        align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN),
    ).moved(bd.Location(origin_xyz))
    solids = tuple(shape.solids())
    if len(solids) != 1:
        raise RuntimeError(
            "type2 underlay STEP body must contain exactly one solid "
            f"(label={label}, solid_count={len(solids)})"
        )
    solid = solids[0]
    solid.label = label
    return solid


def build_labeled_group(*, label: str, children: tuple[bd.Shape, ...]) -> bd.Shape:
    if len(label) > _LABELED_SHAPE_MAX_LABEL_LENGTH:
        raise RuntimeError(
            "type2 underlay group label must be <= 32 chars "
            f"(label={label}, length={len(label)})"
        )
    if len(children) == 0:
        raise RuntimeError(f"type2 underlay group must contain children (label={label})")
    group = bd.Compound(children=children, label=label)
    return cast(bd.Shape, group)


__all__ = [
    "build_labeled_group",
    "build_labeled_solid_box",
    "build_non_model_box_shape",
    "canonical_from_non_model_box",
    "canonical_from_non_model_specs",
    "canonical_from_shape",
]

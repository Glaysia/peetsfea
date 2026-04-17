from __future__ import annotations

from typing import Callable, cast

from peetsfea.aedt import Object3d

from peetsfea.types.manifest import CadProbe

_Point2 = tuple[float, float]


def _require_attr(obj: object, attr_name: str, *, context: str) -> object:
    assert hasattr(obj, attr_name), f"{context} is missing required attribute {attr_name}"
    return getattr(obj, attr_name)


def _probe_from_points(object_name: str, points: list[list[float]]) -> CadProbe:
    if not points:
        raise ValueError(f"Cannot build CAD probe for {object_name} from an empty point collection")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
    edge_samples: list[_Point2] = []
    for idx in range(min(max(0, len(points) - 1), 8)):
        edge_samples.append(
            (
                (points[idx][0] + points[idx + 1][0]) / 2.0,
                (points[idx][1] + points[idx + 1][1]) / 2.0,
            )
        )
    return {
        "object_name": object_name,
        "bbox": [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)],
        "edge_samples_xy": edge_samples,
    }


def _point_xy(value: object) -> _Point2:
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        x = value[0]
        y = value[1]
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            return (float(x), float(y))

    x_attr = _require_attr(value, "x", context="CAD point")
    y_attr = _require_attr(value, "y", context="CAD point")
    if isinstance(x_attr, (int, float)) and isinstance(y_attr, (int, float)):
        return (float(x_attr), float(y_attr))

    raise TypeError(f"CAD point must expose numeric x/y coordinates (actual_type={type(value).__name__})")


def _extract_bbox(obj: Object3d) -> list[float]:
    raw_bbox = _require_attr(obj, "bounding_box", context="CAD object")
    if callable(raw_bbox):
        raw_bbox = cast(Callable[[], object], raw_bbox)()
    if not isinstance(raw_bbox, (tuple, list)) or len(raw_bbox) < 6:
        raise ValueError("CAD object bounding_box must be a sequence with at least 6 values")

    values: list[float] = []
    for item in raw_bbox[:6]:
        if not isinstance(item, (int, float)):
            raise TypeError("CAD object bounding_box must contain numeric values")
        values.append(float(item))
    return values


def _extract_edge_samples_xy(obj: Object3d, limit: int = 8) -> list[_Point2]:
    samples: list[_Point2] = []
    edges = _require_attr(obj, "edges", context="CAD object")
    if not isinstance(edges, list):
        raise TypeError("CAD object edges must be a list")

    for edge in edges[:limit]:
        midpoint = _require_attr(edge, "midpoint", context="CAD edge")
        samples.append(_point_xy(midpoint))

    return samples


def _probe_cad_object(obj: Object3d) -> CadProbe:
    return {
        "object_name": _object_name(obj),
        "bbox": _extract_bbox(obj),
        "edge_samples_xy": _extract_edge_samples_xy(obj),
    }


def _object_name(obj: Object3d) -> str:
    name = _require_attr(obj, "name", context="CAD object")
    if not isinstance(name, str) or not name:
        raise ValueError("CAD object name must be a non-empty string")
    return name

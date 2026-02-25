from __future__ import annotations

from ansys.aedt.core.modeler.cad.object_3d import Object3d

from peetsfea.types.manifest import CadProbe

_Point2 = tuple[float, float]

def _probe_from_points(object_name: str, points: list[list[float]]) -> CadProbe:
    if not points:
        return {"object_name": object_name, "bbox": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "edge_samples_xy": []}
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


def _point_xy(value: object) -> _Point2 | None:
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        x = value[0]
        y = value[1]
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            return (float(x), float(y))

    x_attr = getattr(value, "x", None)
    y_attr = getattr(value, "y", None)
    if isinstance(x_attr, (int, float)) and isinstance(y_attr, (int, float)):
        return (float(x_attr), float(y_attr))

    return None


def _extract_bbox(obj: Object3d) -> list[float]:
    for attr_name in ("bounding_box", "bbox"):
        attr = getattr(obj, attr_name, None)
        raw_bbox: object
        if callable(attr):
            try:
                raw_bbox = attr()
            except Exception:
                continue
        else:
            raw_bbox = attr

        if isinstance(raw_bbox, (tuple, list)) and len(raw_bbox) >= 6:
            values: list[float] = []
            for item in raw_bbox[:6]:
                if isinstance(item, (int, float)):
                    values.append(float(item))
            if len(values) == 6:
                return values

    return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def _extract_edge_samples_xy(obj: Object3d, limit: int = 8) -> list[_Point2]:
    samples: list[_Point2] = []
    edges = getattr(obj, "edges", None)
    if not isinstance(edges, list):
        return samples

    for edge in edges[:limit]:
        candidates = [
            getattr(edge, "midpoint", None),
            getattr(edge, "center", None),
            getattr(edge, "start", None),
            getattr(edge, "end", None),
        ]
        point: _Point2 | None = None
        for candidate in candidates:
            point = _point_xy(candidate)
            if point is not None:
                break

        if point is None:
            vertices = getattr(edge, "vertices", None)
            if isinstance(vertices, list) and vertices:
                point = _point_xy(vertices[0])

        if point is not None:
            samples.append(point)

    return samples


def _probe_cad_object(obj: Object3d, fallback_name: str) -> CadProbe:
    return {
        "object_name": _object_name(obj, fallback_name),
        "bbox": _extract_bbox(obj),
        "edge_samples_xy": _extract_edge_samples_xy(obj),
    }


def _object_name(obj: Object3d, fallback: str) -> str:
    name = getattr(obj, "name", "")
    if isinstance(name, str) and name:
        return name
    return fallback



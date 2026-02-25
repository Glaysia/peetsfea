from __future__ import annotations

from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.modeler_3d import Modeler3D
from typing import cast

from .cad_probe import _object_name


def normalize_united_name(*, unite_result: object, fallback_name: str) -> str:
    if isinstance(unite_result, list):
        first = unite_result[0] if unite_result else fallback_name
        return first if isinstance(first, str) else _object_name(cast(Object3d, first), fallback_name)
    if isinstance(unite_result, str):
        return unite_result
    return _object_name(cast(Object3d, unite_result), fallback_name)


def safe_unite(
    *,
    modeler: Modeler3D,
    targets: list[str],
    fallback_name: str,
    error_context: str,
) -> str:
    if not targets:
        raise ValueError(f"safe_unite requires at least one target ({error_context})")
    if len(targets) == 1:
        return targets[0]
    try:
        unite_result = modeler.unite(assignment=targets)  # type: ignore[misc]
    except TypeError:
        unite_result = modeler.unite(targets)  # type: ignore[misc]
    if not unite_result:
        raise ValueError(f"Failed to unite {error_context} (targets={targets})")
    return normalize_united_name(unite_result=unite_result, fallback_name=fallback_name)

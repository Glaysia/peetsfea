from __future__ import annotations

from peetsfea.aedt import Object3d
from peetsfea.aedt import Modeler3D
from typing import cast

from peetsfea.backend.pyaedt.failfast import raise_on_false
from .cad_probe import _object_name


def normalize_united_name(*, unite_result: object) -> str:
    if isinstance(unite_result, list):
        if not unite_result:
            raise ValueError("unite returned an empty result list")
        first = unite_result[0]
        if isinstance(first, str):
            if first == "":
                raise ValueError("unite returned an empty object name")
            return first
        return _object_name(cast(Object3d, first))
    if isinstance(unite_result, str):
        if unite_result == "":
            raise ValueError("unite returned an empty object name")
        return unite_result
    return _object_name(cast(Object3d, unite_result))


def safe_unite(
    *,
    modeler: Modeler3D,
    targets: list[str],
    error_context: str,
) -> str:
    if not targets:
        raise ValueError(f"safe_unite requires at least one target ({error_context})")
    if len(targets) == 1:
        return targets[0]
    unite_result = modeler.unite(assignment=targets)  # type: ignore[misc]
    unite_result = raise_on_false(
        unite_result,
        operation="unite",
        context={"error_context": error_context, "targets": list(targets)},
    )
    return normalize_united_name(unite_result=unite_result)

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from peetsfea.aedt import Hfss
from peetsfea.aedt.protocols import HfssSession, ModelerSession
from peetsfea.backend.pyaedt.type2_step_import_ledger import validated_object_names


def create_headless_hfss(design_name: str) -> HfssSession:
    return cast(HfssSession, Hfss(design=design_name, non_graphical=True, new_desktop=True))


def _unwrap_raw(value: object, *, context: str) -> object:
    if hasattr(value, "_raw"):
        raw_value = object.__getattribute__(value, "_raw")
        assert raw_value is not None, f"{context}._raw must not be null"
        return raw_value
    return value


def current_object_names(modeler: ModelerSession, *, context: str) -> list[str]:
    return validated_object_names(cast(Sequence[object], modeler.object_names), context=context)


def current_design_name(hfss: HfssSession) -> str:
    raw_hfss = _unwrap_raw(hfss, context="hfss")
    assert hasattr(raw_hfss, "design_name"), f"HFSS session must expose design_name (hfss_type={type(raw_hfss).__name__})"
    raw_design_name = getattr(raw_hfss, "design_name")
    assert isinstance(raw_design_name, str), (
        "HFSS design_name must be str "
        f"(actual={type(raw_design_name).__name__})"
    )
    if raw_design_name == "":
        raise ValueError("HFSS design_name must be non-empty")
    return raw_design_name


def prepare_attached_import_design(hfss: HfssSession) -> None:
    if not current_object_names(hfss.modeler, context="attached_import.current_design_object_names"):
        return

    raw_hfss = _unwrap_raw(hfss, context="hfss")
    assert hasattr(raw_hfss, "insert_design"), (
        f"HFSS session must expose insert_design when attached import rehomes into a fresh design "
        f"(hfss_type={type(raw_hfss).__name__})"
    )
    insert_design = getattr(raw_hfss, "insert_design")
    assert callable(insert_design), "HFSS insert_design must be callable"
    requested_design_name = current_design_name(hfss)
    inserted_design_name = insert_design(requested_design_name)
    assert isinstance(inserted_design_name, str), (
        "HFSS insert_design must return str "
        f"(actual={type(inserted_design_name).__name__})"
    )
    if inserted_design_name == "":
        raise ValueError("HFSS insert_design must return a non-empty design name")
    active_design_name = current_design_name(hfss)
    if active_design_name != inserted_design_name:
        raise RuntimeError(
            "Attached HFSS import must activate the newly inserted fresh design "
            f"(requested={requested_design_name}, inserted={inserted_design_name}, active={active_design_name})"
        )


__all__ = [
    "create_headless_hfss",
    "current_design_name",
    "current_object_names",
    "prepare_attached_import_design",
]

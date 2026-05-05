from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from peetsfea.aedt.failfast import raise_on_false
from peetsfea.aedt.protocols import HfssSession
from peetsfea.backend.pyaedt.type2_step_import_core import (
    Type2ImportedLedger,
    build_imported_ledger,
    write_imported_ledger,
)
from peetsfea.backend.pyaedt.type2_step_import_ledger import load_step_ledger
from peetsfea.backend.pyaedt.type2_step_runtime_common import (
    create_headless_hfss,
    prepare_attached_import_design,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SOURCE_STEP_LEDGER_PATH = REPO_ROOT / "run" / "step" / "type2" / "type2_step_ledger.json"
DEFAULT_OUTPUT_AEDT_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_import" / "type2_import.aedt"
DEFAULT_IMPORTED_LEDGER_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_import" / "type2_imported_ledger.json"
DEFAULT_DESIGN_NAME = "type2_step_import"

HfssFactory = Callable[[str], HfssSession]


def import_type2_step_geometry_view(
    *,
    step_ledger_path: Path = DEFAULT_SOURCE_STEP_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
    design_name: str = DEFAULT_DESIGN_NAME,
    hfss_factory: HfssFactory = create_headless_hfss,
) -> Type2ImportedLedger:
    return import_type2_step_ledger(
        step_ledger_path=step_ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        design_name=design_name,
        hfss_factory=hfss_factory,
    )


def import_type2_step_ledger(
    *,
    step_ledger_path: Path = DEFAULT_SOURCE_STEP_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
    design_name: str = DEFAULT_DESIGN_NAME,
    hfss_factory: HfssFactory = create_headless_hfss,
) -> Type2ImportedLedger:
    checked_step_ledger_path = step_ledger_path.resolve(strict=False)
    ledger = load_step_ledger(checked_step_ledger_path)
    output_aedt_path.parent.mkdir(parents=True, exist_ok=True)
    hfss = hfss_factory(design_name)
    try:
        imported_ledger = build_imported_ledger(
            hfss=hfss,
            step_ledger_path=checked_step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            ledger=ledger,
        )
        save_result = hfss.save_project(str(output_aedt_path))
        raise_on_false(save_result, operation="save_project", context={"path": str(output_aedt_path)})
        write_imported_ledger(imported_ledger_path=imported_ledger_path, imported_ledger=imported_ledger)
        return imported_ledger
    finally:
        release_result = hfss.desktop_class.release_desktop(close_projects=True, close_on_exit=True)
        raise_on_false(
            release_result,
            operation="release_desktop",
            context={"close_projects": True, "close_on_exit": True},
        )


def import_type2_step_ledger_into_hfss(
    *,
    hfss: HfssSession,
    step_ledger_path: Path = DEFAULT_SOURCE_STEP_LEDGER_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    imported_ledger_path: Path = DEFAULT_IMPORTED_LEDGER_PATH,
) -> Type2ImportedLedger:
    checked_step_ledger_path = step_ledger_path.resolve(strict=False)
    try:
        ledger = load_step_ledger(checked_step_ledger_path)
        output_aedt_path.parent.mkdir(parents=True, exist_ok=True)
        prepare_attached_import_design(hfss)
        imported_ledger = build_imported_ledger(
            hfss=hfss,
            step_ledger_path=checked_step_ledger_path,
            output_aedt_path=output_aedt_path,
            imported_ledger_path=imported_ledger_path,
            ledger=ledger,
        )
        save_result = hfss.save_project(str(output_aedt_path))
        raise_on_false(save_result, operation="save_project", context={"path": str(output_aedt_path)})
        write_imported_ledger(imported_ledger_path=imported_ledger_path, imported_ledger=imported_ledger)
        return imported_ledger
    finally:
        release_result = hfss.desktop_class.release_desktop(close_projects=False, close_on_exit=False)
        raise_on_false(
            release_result,
            operation="release_desktop",
            context={"close_projects": False, "close_on_exit": False},
        )


__all__ = [
    "DEFAULT_DESIGN_NAME",
    "DEFAULT_IMPORTED_LEDGER_PATH",
    "DEFAULT_OUTPUT_AEDT_PATH",
    "DEFAULT_SOURCE_STEP_LEDGER_PATH",
    "HfssFactory",
    "Type2ImportedLedger",
    "create_headless_hfss",
    "import_type2_step_geometry_view",
    "import_type2_step_ledger_into_hfss",
    "import_type2_step_ledger",
]

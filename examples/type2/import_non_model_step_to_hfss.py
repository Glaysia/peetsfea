from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, TypedDict, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from peetsfea.aedt import Hfss
from peetsfea.aedt.failfast import raise_on_false, validate_aedt_name

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STEP_PATH = REPO_ROOT / "run" / "step" / "type2" / "type2_non_model_scene.step"
DEFAULT_OUTPUT_AEDT_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_import_smoke" / "type2_non_model_scene_import.aedt"
DEFAULT_DESIGN_NAME = "type2_step_import_smoke"


class Type2StepImportResult(TypedDict):
    step_path: str
    aedt_path: str
    imported_object_names: list[str]


class _DesktopSession(Protocol):
    def release_desktop(self, close_projects: bool, close_on_exit: bool) -> object: ...


class _ModelerSession(Protocol):
    @property
    def object_names(self) -> Sequence[str]: ...

    def import_3d_cad(self, input_file: str | Path) -> bool: ...

    def set_object_model_state(self, name: str, model: bool) -> object: ...


class _HfssSession(Protocol):
    @property
    def modeler(self) -> _ModelerSession: ...

    @property
    def desktop_class(self) -> _DesktopSession: ...

    def save_project(self, path: str) -> object: ...


def _create_headless_hfss(design_name: str) -> _HfssSession:
    return cast(
        _HfssSession,
        Hfss(project=None, design=design_name, non_graphical=True, new_desktop=True),
    )


def _require_existing_file(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"STEP file not found for HFSS import: {path}")
    return path


def _validated_object_names(raw_names: Sequence[str], *, context: str) -> list[str]:
    names: list[str] = []
    for index, name in enumerate(raw_names):
        if not isinstance(name, str):
            raise TypeError(f"{context}.object_names[{index}] must be str")
        if not name:
            raise ValueError(f"{context}.object_names[{index}] must not be empty")
        validate_aedt_name(name, field=f"{context}.object_names[{index}]")
        names.append(name)
    return names


def _new_imported_object_names(*, before_import: Sequence[str], after_import: Sequence[str], step_path: Path) -> list[str]:
    before_names = set(before_import)
    imported_names = [name for name in after_import if name not in before_names]
    if not imported_names:
        raise RuntimeError(f"STEP import created no new HFSS objects: {step_path}")
    if len(imported_names) != len(set(imported_names)):
        raise RuntimeError(f"STEP import produced duplicate new HFSS object names: {imported_names}")
    return imported_names


def import_step_to_hfss(
    *,
    step_path: Path = DEFAULT_STEP_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    design_name: str = DEFAULT_DESIGN_NAME,
    hfss_factory: Callable[[str], _HfssSession] = _create_headless_hfss,
) -> Type2StepImportResult:
    checked_step_path = _require_existing_file(step_path)
    output_aedt_path.parent.mkdir(parents=True, exist_ok=True)

    hfss = hfss_factory(design_name)
    try:
        modeler = hfss.modeler
        before_import = _validated_object_names(modeler.object_names, context="before_import")
        import_result = modeler.import_3d_cad(input_file=checked_step_path)
        raise_on_false(import_result, operation="import_3d_cad", context={"input_file": str(checked_step_path)})
        after_import = _validated_object_names(modeler.object_names, context="after_import")
        imported_object_names = _new_imported_object_names(
            before_import=before_import,
            after_import=after_import,
            step_path=checked_step_path,
        )
        for object_name in imported_object_names:
            state_result = modeler.set_object_model_state(object_name, False)
            raise_on_false(
                state_result,
                operation="set_object_model_state",
                context={"name": object_name, "model": False},
            )
        save_result = hfss.save_project(str(output_aedt_path))
        raise_on_false(save_result, operation="save_project", context={"path": str(output_aedt_path)})
        return {
            "step_path": str(checked_step_path),
            "aedt_path": str(output_aedt_path),
            "imported_object_names": imported_object_names,
        }
    finally:
        release_result = hfss.desktop_class.release_desktop(close_projects=True, close_on_exit=True)
        raise_on_false(
            release_result,
            operation="release_desktop",
            context={"close_projects": True, "close_on_exit": True},
        )


def main() -> Type2StepImportResult:
    result = import_step_to_hfss()
    print(f"source STEP: {result['step_path']}")
    print(f"output AEDT: {result['aedt_path']}")
    print(f"imported object count: {len(result['imported_object_names'])}")
    for object_name in result["imported_object_names"]:
        print(f"- {object_name}")
    return result


if __name__ == "__main__":
    main()

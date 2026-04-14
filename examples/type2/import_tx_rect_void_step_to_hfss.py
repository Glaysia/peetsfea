from __future__ import annotations

import importlib
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Protocol, TypedDict, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from peetsfea.aedt import Hfss
from peetsfea.aedt.failfast import raise_on_false, validate_aedt_name

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STEP_PATH = REPO_ROOT / "run" / "step" / "tx_rect_void_coil.step"
DEFAULT_METADATA_JSON_PATH = REPO_ROOT / "run" / "step" / "tx_rect_void_coil.metadata.json"
DEFAULT_OUTPUT_AEDT_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_import_smoke" / "tx_rect_void_coil_import.aedt"
DEFAULT_DESIGN_NAME = "type2_tx_rect_void_import_smoke"
_ADAPTER_MODULE_PATH = "peetsfea.backend.pyaedt.type2_modeled_import_adapter"
_ADAPTER_FUNCTION_NAME = "build_single_imported_modeled_object_entry"
_REQUIRED_IMPORTED_LEDGER_FIELDS = (
    "object_id",
    "role",
    "material",
    "model_state",
    "step_path",
    "canonical_coordinates",
    "terminal_metadata",
    "imported_object_names",
)


class Type2ModeledStepImportResult(TypedDict):
    step_path: str
    metadata_path: str
    aedt_path: str
    imported_object_names: list[str]


class TxRectVoidModeledStepImportSmokeResult(TypedDict):
    import_result: Type2ModeledStepImportResult
    imported_modeled_object_entry: dict[str, object]


class _DesktopSession(Protocol):
    def release_desktop(self, close_projects: bool, close_on_exit: bool) -> object: ...


class _ModelerSession(Protocol):
    @property
    def object_names(self) -> Sequence[str]: ...

    def import_3d_cad(self, input_file: str | Path) -> bool: ...


class _HfssSession(Protocol):
    @property
    def modeler(self) -> _ModelerSession: ...

    @property
    def desktop_class(self) -> _DesktopSession: ...

    def save_project(self, path: str) -> object: ...


class _ModeledImportEntryBuilder(Protocol):
    def __call__(
        self,
        modeled_object: Mapping[str, object],
        imported_object_names: Sequence[str],
    ) -> object: ...


def _create_headless_hfss(design_name: str) -> _HfssSession:
    return cast(
        _HfssSession,
        Hfss(project=None, design=design_name, non_graphical=True, new_desktop=True),
    )


def _require_existing_file(path: Path, *, field_name: str) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"{field_name} not found: {path}")
    return path


def _require_table(value: object, *, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be a JSON object")
    return cast(dict[str, object], value)


def _require_modeled_object_entry(metadata_payload: dict[str, object], *, step_path: Path) -> dict[str, object]:
    if "modeled_objects" not in metadata_payload:
        raise ValueError("metadata JSON is missing required key 'modeled_objects'")
    raw_modeled_objects = metadata_payload["modeled_objects"]
    if not isinstance(raw_modeled_objects, list):
        raise TypeError("metadata JSON key 'modeled_objects' must be a list")
    if len(raw_modeled_objects) != 1:
        raise ValueError("metadata JSON must contain exactly one modeled object for tx_rect_void prototype")
    modeled_object_entry = _require_table(raw_modeled_objects[0], context="metadata.modeled_objects[0]")
    if "step_path" not in modeled_object_entry:
        raise ValueError("metadata.modeled_objects[0] is missing required key 'step_path'")
    raw_step_path = modeled_object_entry["step_path"]
    if not isinstance(raw_step_path, str) or raw_step_path == "":
        raise TypeError("metadata.modeled_objects[0].step_path must be a non-empty string")
    expected_step_path = str(step_path)
    if raw_step_path != expected_step_path:
        raise RuntimeError(
            "metadata.modeled_objects[0].step_path does not match STEP import input "
            f"(metadata={raw_step_path}, input={expected_step_path})"
        )
    return modeled_object_entry


def _load_modeled_object_entry_from_metadata(*, metadata_json_path: Path, step_path: Path) -> dict[str, object]:
    raw_text = metadata_json_path.read_text(encoding="utf-8")
    raw_payload = json.loads(raw_text)
    payload = _require_table(raw_payload, context="metadata")
    return _require_modeled_object_entry(payload, step_path=step_path)


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


def _load_modeled_import_builder() -> _ModeledImportEntryBuilder:
    adapter_module = importlib.import_module(_ADAPTER_MODULE_PATH)
    if not hasattr(adapter_module, _ADAPTER_FUNCTION_NAME):
        raise AttributeError(f"{_ADAPTER_MODULE_PATH} is missing '{_ADAPTER_FUNCTION_NAME}'")
    raw_builder = getattr(adapter_module, _ADAPTER_FUNCTION_NAME)
    if not callable(raw_builder):
        raise TypeError(f"{_ADAPTER_MODULE_PATH}.{_ADAPTER_FUNCTION_NAME} must be callable")
    return cast(_ModeledImportEntryBuilder, raw_builder)


def _validated_imported_modeled_object_entry(
    raw_entry: object,
    *,
    imported_object_names: list[str],
    step_path: Path,
) -> dict[str, object]:
    entry = _require_table(raw_entry, context="imported_modeled_object_entry")
    for field_name in _REQUIRED_IMPORTED_LEDGER_FIELDS:
        if field_name not in entry:
            raise ValueError(f"imported_modeled_object_entry is missing required field '{field_name}'")
    raw_entry_step_path = entry["step_path"]
    if not isinstance(raw_entry_step_path, str) or raw_entry_step_path == "":
        raise TypeError("imported_modeled_object_entry.step_path must be a non-empty string")
    expected_step_path = str(step_path)
    if raw_entry_step_path != expected_step_path:
        raise RuntimeError(
            "imported_modeled_object_entry.step_path does not match STEP import input "
            f"(entry={raw_entry_step_path}, input={expected_step_path})"
        )
    raw_entry_imported_names = entry["imported_object_names"]
    if not isinstance(raw_entry_imported_names, list):
        raise TypeError("imported_modeled_object_entry.imported_object_names must be a list")
    entry_imported_names = _validated_object_names(
        cast(list[str], raw_entry_imported_names),
        context="imported_modeled_object_entry",
    )
    if entry_imported_names != imported_object_names:
        raise RuntimeError(
            "adapter returned imported_object_names that do not match STEP import diff "
            f"(adapter={entry_imported_names}, diff={imported_object_names})"
        )
    return entry


def import_tx_rect_void_step_to_hfss(
    *,
    step_path: Path = DEFAULT_STEP_PATH,
    metadata_json_path: Path = DEFAULT_METADATA_JSON_PATH,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    design_name: str = DEFAULT_DESIGN_NAME,
    hfss_factory: Callable[[str], _HfssSession] = _create_headless_hfss,
    modeled_entry_builder_loader: Callable[[], _ModeledImportEntryBuilder] = _load_modeled_import_builder,
) -> TxRectVoidModeledStepImportSmokeResult:
    checked_step_path = _require_existing_file(step_path, field_name="STEP file")
    checked_metadata_json_path = _require_existing_file(metadata_json_path, field_name="Metadata JSON file")
    modeled_object_entry = _load_modeled_object_entry_from_metadata(
        metadata_json_path=checked_metadata_json_path,
        step_path=checked_step_path,
    )
    build_single_imported_modeled_object_entry = modeled_entry_builder_loader()
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
        save_result = hfss.save_project(str(output_aedt_path))
        raise_on_false(save_result, operation="save_project", context={"path": str(output_aedt_path)})
        imported_entry_raw = build_single_imported_modeled_object_entry(modeled_object_entry, imported_object_names)
        imported_entry = _validated_imported_modeled_object_entry(
            imported_entry_raw,
            imported_object_names=imported_object_names,
            step_path=checked_step_path,
        )
        return {
            "import_result": {
                "step_path": str(checked_step_path),
                "metadata_path": str(checked_metadata_json_path),
                "aedt_path": str(output_aedt_path),
                "imported_object_names": imported_object_names,
            },
            "imported_modeled_object_entry": imported_entry,
        }
    finally:
        release_result = hfss.desktop_class.release_desktop(close_projects=True, close_on_exit=True)
        raise_on_false(
            release_result,
            operation="release_desktop",
            context={"close_projects": True, "close_on_exit": True},
        )


def main() -> TxRectVoidModeledStepImportSmokeResult:
    result = import_tx_rect_void_step_to_hfss()
    import_result = result["import_result"]
    print(f"source STEP: {import_result['step_path']}")
    print(f"source metadata JSON: {import_result['metadata_path']}")
    print(f"output AEDT: {import_result['aedt_path']}")
    print(f"imported object count: {len(import_result['imported_object_names'])}")
    for object_name in import_result["imported_object_names"]:
        print(f"- {object_name}")
    print("imported modeled object entry:")
    print(json.dumps(result["imported_modeled_object_entry"], ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    main()

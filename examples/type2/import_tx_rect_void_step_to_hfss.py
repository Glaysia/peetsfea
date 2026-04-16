from __future__ import annotations

import importlib
import json
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Protocol, TypedDict, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from peetsfea.aedt import Hfss
from peetsfea.aedt.failfast import raise_on_false, validate_aedt_name

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TYPE2_TOML_PATH = REPO_ROOT / "examples" / "type2" / "type2.toml"
DEFAULT_TYPE2_EXPORTER_PATH = REPO_ROOT / "examples" / "type2" / "generate_type2_step.py"
DEFAULT_OUTPUT_AEDT_PATH = REPO_ROOT / "run" / "aedt" / "type2_step_import_smoke" / "type2_tx_single_coil_import.aedt"
DEFAULT_DESIGN_NAME = "type2_tx_single_coil_import_smoke"
_SUPPORTED_MODELED_ROLE = "tx_single_coil"
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


class _Type2ArtifactResolver(Protocol):
    def __call__(
        self,
        *,
        repo_root: Path,
        type2_toml_path: Path,
        type2_exporter_path: Path,
    ) -> tuple[Path, Path]: ...


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


def _require_non_empty_string(value: object, *, context: str) -> str:
    if not isinstance(value, str) or value == "":
        raise TypeError(f"{context} must be a non-empty string")
    return value


def _resolve_existing_path(path_text: str, *, context: str) -> Path:
    resolved = Path(path_text).resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{context} not found: {resolved}")
    return resolved


def _metadata_candidate_paths(repo_root: Path) -> tuple[Path, ...]:
    roots = (
        repo_root / "run" / "step",
        repo_root / "examples" / "type2" / "artifacts",
    )
    candidates: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for metadata_path in root.rglob("*.metadata.json"):
            if metadata_path.is_file():
                candidates.append(metadata_path.resolve())
    return tuple(sorted(set(candidates), key=str))


def _collect_type2_modeled_artifact_candidates(*, repo_root: Path, type2_toml_path: Path) -> tuple[tuple[Path, Path], ...]:
    candidates: list[tuple[Path, Path]] = []
    for metadata_path in _metadata_candidate_paths(repo_root):
        raw_text = metadata_path.read_text(encoding="utf-8")
        raw_payload = json.loads(raw_text)
        if not isinstance(raw_payload, dict):
            continue
        payload = cast(dict[str, object], raw_payload)
        raw_source_toml_path = payload.get("source_toml_path")
        if not isinstance(raw_source_toml_path, str) or raw_source_toml_path == "":
            continue
        if Path(raw_source_toml_path).resolve() != type2_toml_path:
            continue
        if "modeled_objects" not in payload:
            raise ValueError(f"metadata JSON is missing required key 'modeled_objects': {metadata_path}")
        raw_modeled_objects = payload["modeled_objects"]
        if not isinstance(raw_modeled_objects, list):
            raise TypeError(f"metadata JSON key 'modeled_objects' must be a list: {metadata_path}")
        if len(raw_modeled_objects) != 1:
            raise ValueError(
                "prototype metadata must contain exactly one modeled object "
                f"(metadata={metadata_path}, count={len(raw_modeled_objects)})"
            )
        modeled_object_entry = _require_table(raw_modeled_objects[0], context=f"{metadata_path}.modeled_objects[0]")
        raw_role = _require_non_empty_string(
            modeled_object_entry.get("role"),
            context=f"{metadata_path}.modeled_objects[0].role",
        )
        if raw_role != _SUPPORTED_MODELED_ROLE:
            raise ValueError(
                "prototype metadata modeled object role must be "
                f"'{_SUPPORTED_MODELED_ROLE}' (metadata={metadata_path}, actual={raw_role})"
            )
        raw_step_path = _require_non_empty_string(
            modeled_object_entry.get("step_path"),
            context=f"{metadata_path}.modeled_objects[0].step_path",
        )
        step_path = _resolve_existing_path(raw_step_path, context=f"modeled step_path from {metadata_path}")
        candidates.append((step_path, metadata_path))
    return tuple(sorted(set(candidates), key=lambda pair: (str(pair[0]), str(pair[1]))))


def resolve_type2_modeled_artifact_paths(
    *,
    repo_root: Path = REPO_ROOT,
    type2_toml_path: Path = DEFAULT_TYPE2_TOML_PATH,
    type2_exporter_path: Path = DEFAULT_TYPE2_EXPORTER_PATH,
) -> tuple[Path, Path]:
    checked_type2_toml_path = _require_existing_file(type2_toml_path, field_name="Type2 TOML file").resolve()
    checked_type2_exporter_path = _require_existing_file(type2_exporter_path, field_name="Type2 exporter script").resolve()
    candidates = _collect_type2_modeled_artifact_candidates(
        repo_root=repo_root,
        type2_toml_path=checked_type2_toml_path,
    )
    if not candidates:
        subprocess.run(
            [sys.executable, str(checked_type2_exporter_path)],
            cwd=repo_root,
            check=True,
        )
        candidates = _collect_type2_modeled_artifact_candidates(
            repo_root=repo_root,
            type2_toml_path=checked_type2_toml_path,
        )
    if not candidates:
        raise RuntimeError(
            "type2 exporter produced no usable tx_single_coil artifact "
            f"(type2_toml_path={checked_type2_toml_path})"
        )
    if len(candidates) != 1:
        raise RuntimeError(
            "expected exactly one type2 tx_single_coil artifact candidate, "
            f"but found {len(candidates)}: {candidates}"
        )
    return candidates[0]


def _require_modeled_object_entry(
    metadata_payload: dict[str, object],
    *,
    step_path: Path,
    expected_source_toml_path: Path | None = None,
) -> dict[str, object]:
    if "modeled_objects" not in metadata_payload:
        raise ValueError("metadata JSON is missing required key 'modeled_objects'")
    raw_modeled_objects = metadata_payload["modeled_objects"]
    if not isinstance(raw_modeled_objects, list):
        raise TypeError("metadata JSON key 'modeled_objects' must be a list")
    if len(raw_modeled_objects) != 1:
        raise ValueError("metadata JSON must contain exactly one modeled object for type2 tx_single_coil prototype")
    modeled_object_entry = _require_table(raw_modeled_objects[0], context="metadata.modeled_objects[0]")
    if "role" not in modeled_object_entry:
        raise ValueError("metadata.modeled_objects[0] is missing required key 'role'")
    raw_role = _require_non_empty_string(modeled_object_entry["role"], context="metadata.modeled_objects[0].role")
    if raw_role != _SUPPORTED_MODELED_ROLE:
        raise ValueError(
            f"metadata.modeled_objects[0].role must be '{_SUPPORTED_MODELED_ROLE}' "
            f"for the prototype import path (actual={raw_role})"
        )
    if "step_path" not in modeled_object_entry:
        raise ValueError("metadata.modeled_objects[0] is missing required key 'step_path'")
    raw_step_path = _require_non_empty_string(
        modeled_object_entry["step_path"],
        context="metadata.modeled_objects[0].step_path",
    )
    if expected_source_toml_path is not None:
        if "source_toml_path" not in metadata_payload:
            raise ValueError("metadata JSON is missing required key 'source_toml_path'")
        raw_source_toml_path = _require_non_empty_string(
            metadata_payload["source_toml_path"],
            context="metadata.source_toml_path",
        )
        resolved_source_toml_path = Path(raw_source_toml_path).resolve()
        if resolved_source_toml_path != expected_source_toml_path.resolve():
            raise RuntimeError(
                "metadata.source_toml_path does not match expected type2 TOML "
                f"(metadata={resolved_source_toml_path}, expected={expected_source_toml_path.resolve()})"
            )
    expected_step_path = str(step_path)
    if raw_step_path != expected_step_path:
        raise RuntimeError(
            "metadata.modeled_objects[0].step_path does not match STEP import input "
            f"(metadata={raw_step_path}, input={expected_step_path})"
        )
    return modeled_object_entry


def _expected_exported_body_count(modeled_object_entry: dict[str, object]) -> int:
    if "expected_exported_body_count" not in modeled_object_entry:
        raise ValueError("metadata.modeled_objects[0] is missing required key 'expected_exported_body_count'")
    raw_count = modeled_object_entry["expected_exported_body_count"]
    if isinstance(raw_count, bool) or not isinstance(raw_count, int):
        raise TypeError("metadata.modeled_objects[0].expected_exported_body_count must be int")
    if raw_count <= 0:
        raise ValueError("metadata.modeled_objects[0].expected_exported_body_count must be > 0")
    if "expected_exported_body_names" not in modeled_object_entry:
        raise ValueError("metadata.modeled_objects[0] is missing required key 'expected_exported_body_names'")
    raw_names = modeled_object_entry["expected_exported_body_names"]
    if isinstance(raw_names, (str, bytes)) or not isinstance(raw_names, Sequence):
        raise TypeError("metadata.modeled_objects[0].expected_exported_body_names must be a sequence")
    names: list[str] = []
    for index, raw_name in enumerate(raw_names):
        if not isinstance(raw_name, str) or raw_name == "":
            raise TypeError(
                "metadata.modeled_objects[0].expected_exported_body_names"
                f"[{index}] must be a non-empty string"
            )
        names.append(raw_name)
    if len(names) != raw_count:
        raise RuntimeError(
            "metadata modeled object expected body count mismatch "
            f"(count={raw_count}, names={names})"
        )
    if len(names) != len(set(names)):
        raise RuntimeError(f"metadata modeled object expected body names must be unique: {names}")
    return raw_count


def _load_modeled_object_entry_from_metadata(
    *,
    metadata_json_path: Path,
    step_path: Path,
    expected_source_toml_path: Path | None = None,
) -> dict[str, object]:
    raw_text = metadata_json_path.read_text(encoding="utf-8")
    raw_payload = json.loads(raw_text)
    payload = _require_table(raw_payload, context="metadata")
    return _require_modeled_object_entry(
        payload,
        step_path=step_path,
        expected_source_toml_path=expected_source_toml_path,
    )


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
    if isinstance(raw_entry_imported_names, (str, bytes)):
        raise TypeError("imported_modeled_object_entry.imported_object_names must be a sequence of strings")
    if not isinstance(raw_entry_imported_names, Sequence):
        raise TypeError("imported_modeled_object_entry.imported_object_names must be a sequence of strings")
    entry_imported_names = _validated_object_names(
        cast(Sequence[str], raw_entry_imported_names),
        context="imported_modeled_object_entry",
    )
    if entry_imported_names != imported_object_names:
        raise RuntimeError(
            "adapter returned imported_object_names that do not match STEP import diff "
            f"(adapter={entry_imported_names}, diff={imported_object_names})"
        )
    entry["imported_object_names"] = entry_imported_names
    return entry


def import_tx_rect_void_step_to_hfss(
    *,
    step_path: Path | None = None,
    metadata_json_path: Path | None = None,
    output_aedt_path: Path = DEFAULT_OUTPUT_AEDT_PATH,
    design_name: str = DEFAULT_DESIGN_NAME,
    hfss_factory: Callable[[str], _HfssSession] = _create_headless_hfss,
    modeled_entry_builder_loader: Callable[[], _ModeledImportEntryBuilder] = _load_modeled_import_builder,
    type2_toml_path: Path = DEFAULT_TYPE2_TOML_PATH,
    type2_exporter_path: Path = DEFAULT_TYPE2_EXPORTER_PATH,
    type2_artifact_resolver: _Type2ArtifactResolver = resolve_type2_modeled_artifact_paths,
) -> TxRectVoidModeledStepImportSmokeResult:
    expected_source_toml_path: Path | None = None
    if step_path is None and metadata_json_path is None:
        resolved_step_path, resolved_metadata_json_path = type2_artifact_resolver(
            repo_root=REPO_ROOT,
            type2_toml_path=type2_toml_path,
            type2_exporter_path=type2_exporter_path,
        )
        checked_step_path = _require_existing_file(resolved_step_path, field_name="STEP file")
        checked_metadata_json_path = _require_existing_file(resolved_metadata_json_path, field_name="Metadata JSON file")
        expected_source_toml_path = _require_existing_file(type2_toml_path, field_name="Type2 TOML file")
    elif step_path is not None and metadata_json_path is not None:
        checked_step_path = _require_existing_file(step_path, field_name="STEP file")
        checked_metadata_json_path = _require_existing_file(metadata_json_path, field_name="Metadata JSON file")
    else:
        raise ValueError(
            "step_path and metadata_json_path must be both provided or both omitted "
            "for type2 artifact auto-resolution"
        )
    modeled_object_entry = _load_modeled_object_entry_from_metadata(
        metadata_json_path=checked_metadata_json_path,
        step_path=checked_step_path,
        expected_source_toml_path=expected_source_toml_path,
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
        expected_body_count = _expected_exported_body_count(modeled_object_entry)
        if len(imported_object_names) != expected_body_count:
            raise RuntimeError(
                "STEP import object count does not match modeled metadata "
                f"(expected={expected_body_count}, actual={len(imported_object_names)}, "
                f"imported_object_names={imported_object_names})"
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

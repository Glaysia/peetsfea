from __future__ import annotations

import os
import re
from pathlib import Path

from peetsfea.aedt import Hfss
from peetsfea.aedt import aedt_versions

from peetsfea.types.manifest import Manifest

_AEDT_EXECUTABLE_BASENAMES = frozenset({"ansysedt", "ansysedtsv", "ansysedt.exe", "ansysedtsv.exe"})


def _normalize_manifest_aedt_executable_path(manifest: Manifest) -> tuple[Path, str]:
    inputs = manifest["inputs"]
    assert isinstance(inputs, dict), "manifest inputs must be a table/object"
    assert "ansys_executable_path" in inputs, "manifest inputs must include ansys_executable_path"
    raw_path = inputs["ansys_executable_path"]
    if not isinstance(raw_path, str) or raw_path == "":
        raise ValueError("manifest inputs.ansys_executable_path must be a non-empty string")

    base = Path(raw_path)
    candidates: list[Path]
    if base.name.lower() in _AEDT_EXECUTABLE_BASENAMES:
        candidates = [base]
    else:
        candidates = [
            base / "ansysedt",
            base / "ansysedt.exe",
            base / "Linux64" / "ansysedt",
            base / "Win64" / "ansysedt.exe",
        ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate, _aedt_version_from_path(candidate)

    checked = ", ".join(str(path) for path in candidates)
    raise ValueError(
        "manifest inputs.ansys_executable_path did not resolve to a valid AEDT executable "
        f"(raw={raw_path}, checked=[{checked}])"
    )


def _aedt_version_from_path(executable_path: Path) -> str:
    for part in executable_path.parts:
        match = re.fullmatch(r"v(\d{3})", part, flags=re.IGNORECASE)
        if not match:
            continue
        version_digits = match.group(1)
        major = int(version_digits[:2])
        release = int(version_digits[2])
        if major < 20:
            if release < 3:
                major -= 1
            else:
                release -= 2
        return f"20{major}.{release}"
    return ""


def _version_env_var_for_executable(executable_path: Path, version: str) -> str:
    for part in executable_path.parts:
        match = re.fullmatch(r"v(\d{3})", part, flags=re.IGNORECASE)
        if match:
            return f"ANSYSEM_ROOT{match.group(1)}"
    if version:
        return aedt_versions.get_version_env_variable(version)
    return ""


def _reset_pyaedt_version_cache() -> None:
    aedt_versions._list_installed_ansysem = None
    aedt_versions._installed_versions = None
    aedt_versions._stable_versions = None
    aedt_versions._current_version = None
    aedt_versions._current_student_version = None
    aedt_versions._latest_version = None


def _configure_pyaedt_install_dir(*, executable_path: Path, version: str) -> None:
    version_env_var = _version_env_var_for_executable(executable_path, version)
    if not version_env_var:
        return
    os.environ[version_env_var] = str(executable_path.parent)
    _reset_pyaedt_version_cache()


def create_hfss_session(manifest: Manifest, aedt_path: Path) -> Hfss:
    _ = aedt_path
    design_name = manifest["spec"]["design_name"]
    non_graphical = manifest["inputs"]["non_graphical"]
    executable_path, version = _normalize_manifest_aedt_executable_path(manifest)
    _configure_pyaedt_install_dir(executable_path=executable_path, version=version)
    # Create an unnamed in-memory project first and persist it later via save_project().
    # Passing the target .aedt path here makes PyAEDT call project Rename() during startup,
    # which is currently the first failing point in headless runs on this environment.
    if not version:
        return Hfss(project=None, design=design_name, non_graphical=non_graphical, new_desktop=True)
    return Hfss(project=None, design=design_name, version=version, non_graphical=non_graphical, new_desktop=True)

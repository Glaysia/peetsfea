from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from peetsfea.pipeline.run_batch import SampleManifestEntry, build_aedt_from_manifest_entry, load_sample_manifest

cwd = Path(__file__).parent.resolve()

ANSYS_EXECUTABLE_PATH = "/opt/ansys_inc/v252/AnsysEM"
DEFAULT_SAMPLE_MANIFEST_PATH = cwd / "run" / "toml" / "manifest.json"
ANSYS_RUN_DIR = cwd / "run" / "aedt"
BUILD_WORKER_COUNT = 4


def _is_debug_enabled() -> bool:
    return os.environ.get("PEETSFEA_DEBUG") == "1"


def _build_entry(entry: SampleManifestEntry, *, is_debug: bool) -> bool:
    return build_aedt_from_manifest_entry(
        entry=entry,
        ansys_run_dir=ANSYS_RUN_DIR,
        ansys_executable_path=ANSYS_EXECUTABLE_PATH,
        is_debug=is_debug,
    )


def _build_worker(entry: SampleManifestEntry) -> bool:
    return _build_entry(entry, is_debug=False)


def build_from_manifest_path(manifest_path: Path = DEFAULT_SAMPLE_MANIFEST_PATH) -> list[bool]:
    entries = load_sample_manifest(manifest_path)
    is_debug = _is_debug_enabled()
    if is_debug or BUILD_WORKER_COUNT <= 1:
        return [_build_entry(entry, is_debug=is_debug) for entry in entries]

    with ProcessPoolExecutor(max_workers=BUILD_WORKER_COUNT) as executor:
        return list(executor.map(_build_worker, entries))


if __name__ == "__main__":
    build_from_manifest_path()

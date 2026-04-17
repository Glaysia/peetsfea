from __future__ import annotations

import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from entry.legacy.type1 import build

SAMPLE_BUILD_WORKER_COUNT = 1
FORCE_NON_GRAPHICAL = os.environ.get("PEETSFEA_SAMPLE_BUILD_NON_GRAPHICAL") == "1"
NON_GUI_BUILD_RUNTIME = build.BuildRuntime(non_graphical=True, close_on_exit=True)


def main() -> list[list[bool]]:
    runtime = NON_GUI_BUILD_RUNTIME if FORCE_NON_GRAPHICAL else build.GUI_VISIBLE_BUILD_RUNTIME
    return build.build_all_targets_with_options(
        runtime=runtime,
        parallel=False,
        max_workers=SAMPLE_BUILD_WORKER_COUNT,
        stop_on_error=True,
    )


if __name__ == "__main__":
    main()

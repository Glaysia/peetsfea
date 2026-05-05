from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.backend.pyaedt.type2_step_import_pipeline import (
    DEFAULT_SOURCE_STEP_LEDGER_PATH,
    Type2ImportedLedger,
    import_type2_step_geometry_view as import_type2_step_geometry_view_pipeline,
)


def import_type2_step_geometry_view() -> Type2ImportedLedger:
    return import_type2_step_geometry_view_pipeline()


def main() -> Type2ImportedLedger:
    result = import_type2_step_geometry_view()
    print(f"step ledger: {DEFAULT_SOURCE_STEP_LEDGER_PATH}")
    print(f"aedt: {result['aedt_path']}")
    print(f"imported ledger: {result['imported_ledger_path']}")
    print(f"modeled object count: {len(result['modeled_objects'])}")
    return result


if __name__ == "__main__":
    main()

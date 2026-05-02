---
title: Type2 STEP Import Boundary
created: 2026-05-03 @ 00:00
updated: 2026-05-03 @ 00:00
tags:
  - import
  - pyaedt
  - sdd
---

# Type2 STEP Import Boundary

This note owns the graph cluster for importing type2 STEP artifacts into HFSS without creating mesh, boundary, ports, reports, or solve artifacts.

## Boundary Role
- Read retained STEP ledger data and import the declared STEP geometry into HFSS.
- Partition imported object names into modeled and non-modeled ownership buckets.
- Apply visual/material styling and reconstruct import-time metadata needed by later setup.
- Write `type2_imported_ledger.json` as the handoff artifact for setup-ready runtime.

## Owned Code Notes
- [import_type2_step.py](../code/entry/import_type2_step.py.md)
- [type2_step_import_pipeline.py](../code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py.md)
- [type2_step_import_core.py](../code/src/peetsfea/backend/pyaedt/type2_step_import_core.py.md)
- [type2_step_import_partition.py](../code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py.md)
- [type2_step_import_style.py](../code/src/peetsfea/backend/pyaedt/type2_step_import_style.py.md)
- [type2_step_import_ledger.py](../code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py.md)
- [type2_modeled_import_adapter.py](../code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py.md)

## Exceptional Handoffs
- Raw HFSS/session access is owned by [pyaedt-boundary](pyaedt-boundary.md).
- Full setup-ready generation starts from the imported ledger and is owned by [type2-em-setup-boundary](type2-em-setup-boundary.md).
- Export-side ledger provenance is owned by [type2_step_ledger.py](../code/src/peetsfea/type2_step_ledger.py.md).

## Graph Intent
- This node should be larger than helper code notes because it owns the import-only artifact handoff.
- Direct code-note links inside this cluster should show real handoff edges: core to partition/style/ledger, ledger to export ledger, style to port-sheet consumers.

---
title: test_type2_port_sheet_runtime_contract.py
created: 2026-05-13 @ 00:00
updated: 2026-05-13 @ 00:00
tags:
  - tests
  - type2
  - pyaedt
  - ports
---

# test_type2_port_sheet_runtime_contract.py

## Source
- Path: `tests/backend_em/test_type2_port_sheet_runtime_contract.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_port_sheet_runtime_contract.py.md`
- Status: active

## 역할
- Active Type2 runtime port sheet contract tests for fake AEDT modeler/import paths.
- Covers direct ledger-vertex sheet creation and bbox drift fail-fast ordering without launching AEDT.

## 입력 / 출력
- 입력: fake imported ledgers and fake AEDT modeler object bounds.
- 출력: assertions that runtime sheet creation consumes ledger vertices exactly, bbox match permits creation, and bbox drift fails before sheet creation.

## Canonical state
- Single-coil runtime sheets are created only from `single_coil_port_v1` terminal metadata.
- Imported body bbox validation runs before sheet primitive creation.

## Invariants / fail-fast
- Mismatched imported bbox versus ledger canonical bounds raises before `create_polyline`.
- Missing or malformed single-coil port contract raises without fallback.

## Collaborators
- [type2_step_import_core.py](../../src/peetsfea/backend/pyaedt/type2_step_import_core.py.md)
- [type2_step_import_style.py](../../src/peetsfea/backend/pyaedt/type2_step_import_style.py.md)
- [0.2.25 Type2 Port Sheet Contract Rewrite](../../../plans/0.2.25-type2-port-sheet-contract-rewrite.md)

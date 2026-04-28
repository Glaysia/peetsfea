---
title: test_type2_step_import_pipeline.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - test
  - import
---

# test_type2_step_import_pipeline.py

## Source
- Path: `tests/backend_em/test_type2_step_import_pipeline.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_step_import_pipeline.py.md`
- Status: active

## 역할
- type2 STEP import-only pipeline behavior를 검증한다.
- 0.2.24 SDD 기준 RX modeled import and non-modeled guide/context import are active.

## Canonical state
- Import ledger preserves source paths, seed, imported ownership, and imported object names.
- Import-only path must not create boundary, ports, mesh, or reports.
- `tx_region` may be carried as guide context only.

## Invariants / fail-fast
- Missing RX imported bodies and generic imported names fail.
- RxOnly import tests must not require TX modeled bodies.

## Collaborators
- [type2_step_import_pipeline.py](../../src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py.md)
- [type2_step_import_core.py](../../src/peetsfea/backend/pyaedt/type2_step_import_core.py.md)

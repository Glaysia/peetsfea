---
title: test_type2_modeled_import_adapter.py
created: 2026-04-18 @ 09:09
updated: 2026-05-03 @ 00:00
tags:
  - test
  - import
---

# test_type2_modeled_import_adapter.py

## Source
- Path: `tests/backend_em/test_type2_modeled_import_adapter.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_modeled_import_adapter.py.md`
- Status: active
- Primary graph owner: [type2-step-import-boundary](../../../architecture/type2-step-import-boundary.md)

## 역할
- Modeled import adapter의 RX metadata validation을 검증한다.

## Canonical state
- RX terminal metadata is required for RxOnly.
- TX metadata is not an active RxOnly assertion.

## Invariants / fail-fast
- Missing RX terminal metadata fails immediately.

## Graph links
- Primary owner: [type2-step-import-boundary](../../../architecture/type2-step-import-boundary.md)
- Direct verification: [type2_modeled_import_adapter.py](../../src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py.md)

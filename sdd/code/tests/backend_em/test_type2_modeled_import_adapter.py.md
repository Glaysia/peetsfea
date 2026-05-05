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
- Modeled import adapter의 단일 코일/스택 모사 객체 입력 계약을 검증한다.
- TX/RX 단일 코일 `terminal_metadata.port_sheet_vertices_xyz`가 입력 시 리스트 기반 좌표라도
  출력 ledger에서 world-좌표 기반 튜플 시퀀스로 정규화되는지를 검증한다.

## Canonical state
- RX terminal metadata is required for RxOnly.
- TX 단일 코일의 `terminal_metadata.port_sheet_vertices_xyz`는 `tuple[tuple[float, float, float], ...]` 형태로
  정규화되어야 하며, 4개 정점 모두 world 좌표 정밀도를 유지해야 한다.

## Invariants / fail-fast
- Missing RX terminal metadata fails immediately.

## Graph links
- Primary owner: [type2-step-import-boundary](../../../architecture/type2-step-import-boundary.md)
- Direct verification: [type2_modeled_import_adapter.py](../../src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py.md)

---
title: test_type2_modeled_import_adapter.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - hfss-import
---

# test_type2_modeled_import_adapter.py

## Source
- Path: `tests/backend_em/test_type2_modeled_import_adapter.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_modeled_import_adapter.py.md`
- Related code: [[sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py]]
- Related architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- modeled import adapter의 single-coil fail-fast 계약을 pure-Python pytest로 검증한다.
- metadata dict shape와 imported object name contract 위반이 즉시 예외로 중단되는지 확인한다.

## 입력 / 출력
- 입력: test-local `modeled_object` dict fixture와 imported object name sequence.
- 출력: pytest assertions only (no AEDT launch, no solve artifact).

## Canonical state
- module-level mutable state는 없다.
- canonical fixture는 `_modeled_object()`가 반환하는 single-coil metadata shape다.

## Invariants / fail-fast
- success case는 normalized typed contract(`ImportedModeledObjectEntry`)를 반환해야 한다.
- success case는 `tx_single_coil`, `rx_single_coil` 둘 다 수용해야 한다.
- unsupported plane은 즉시 실패해야 한다.
- `model_state != True`이면 즉시 실패해야 한다.
- `imported_object_names` empty/duplicate는 즉시 실패해야 한다.
- required metadata key 누락(`terminal_metadata`)과 invalid terminal direction은 즉시 실패해야 한다.

## 직접 의존
- `pytest`
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py]]

## 이 파일을 쓰는 곳
- backend_em default pytest collection.

## 관련 테스트
- 이 파일 자체.

## 변경 시 주의점
- adapter contract 필드나 예외 메시지 정책을 바꾸면 실패 케이스 정규식과 fixture shape를 함께 갱신한다.
- AEDT integration 검증은 이 파일에 추가하지 않는다.

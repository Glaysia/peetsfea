---
title: type2_step_import_style.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 10:41
tags:
  - type2
  - hfss-import
  - aedt
---

# type2_step_import_style.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_style.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py.md`
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Parent note: [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 역할
- imported object model-state 고정, material/color styling, owner-fit placement validation을 담당한다.
- geometry repair 없이 export ledger placement truth를 검증만 수행한다.

## 입력 / 출력
- 입력: modeler/hfss session, validated ledger metadata, partitioned imported names
- 출력: styled imported objects, validated placement state

## Canonical state
- non-model: gray/transparency + `model=False`.
- modeled: PCB `FR4_epoxy`/green, copper `copper`/copper-color + `model=True`.

## Invariants / fail-fast
- PyAEDT `set_object_model_state` `False` return은 즉시 raise.
- TX/RX owner-fit mismatch는 move() repair 없이 즉시 raise.
- TX multilayer exact-name body set도 PCB/copper styling contract를 그대로 적용한다.

## 직접 의존
- `peetsfea.aedt.failfast`
- `peetsfea.aedt.proxies`
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- style/model-state와 import diff ownership resolution을 분리 유지한다.
- placement validation에서 fallback repair path를 넣지 않는다.

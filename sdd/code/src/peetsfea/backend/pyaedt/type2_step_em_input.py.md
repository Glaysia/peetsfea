---
title: type2_step_em_input.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 23:30
tags:
  - type2
  - em
  - adapter
---

# type2_step_em_input.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_em_input.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py.md`
- Related architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- import-only ledger를 setup-ready용 `EmPipelineInput` shape로 변환한다.
- imported object ownership에서 TX/RX conductor, FR4 object, transitional endpoints/context를 조립한다.

## 입력 / 출력
- 입력:
  - import-only `Type2ImportedLedger`
- 출력:
  - `EmPipelineInput`

## Canonical state
- type2 -> shared EM pipeline adapter의 canonical owner다.

## Invariants / fail-fast
- current setup-ready baseline은 single-layer TX/RX each one entry만 지원한다.
- `context.source`는 `type2_step_setup_ready`로 고정한다.
- transitional context/endpoints는 placeholder fallback이 아니라 deterministic adapter output이어야 한다.

## 직접 의존
- `peetsfea.backend.pyaedt.em_pipeline.contracts`
- `peetsfea.types.manifest`
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- legacy `tx_dd` / `rx_dd` endpoint taxonomy를 type2 public contract로 승격하지 않는다.
- shared EM step들이 실제로 쓰는 최소 shape만 유지하되, adapter drift는 문서 없이 암묵적으로 만들지 않는다.


---
title: type2_runtime.py
created: 2026-04-18 @ 23:10
updated: 2026-04-21 @ 15:20
tags:
  - build
  - runtime
---

# type2_runtime.py

## Source
- Path: `src/peetsfea/type2_runtime.py`
- Code note path: `sdd/code/src/peetsfea/type2_runtime.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]], [[sdd/plans/0.2.22-type2-plate-stack-full-em]]

## 역할
- sampled manifest 기준 export/build orchestration helper를 제공한다.

## 입력 / 출력
- 입력: prepared builds, exporter, runner
- 출력: stepped artifacts, built artifacts

## Canonical state
- default build runner는 `setup_type2_step_ledger` facade다.
- active RX-only role set(`rx_single_coil`)은 setup-ready facade 내부의 full setup-ready branch를 쓴다.
- coil pair exact roles는 retained setup-ready full path를 쓴다.
- plate-stack exact roles(`tx_plate_stack` + `rx_plate_stack`)도 setup-ready facade 내부의 full setup-ready branch를 쓴다.
- mixed retained role set(`tx_plate_stack` + `rx_single_coil`)은 setup-ready facade가 명시적으로 지원하는 경우에만 build preflight를 통과한다.
- plate-stack free sampled owners가 있으면 prepared build design variables가 비어 있지 않은 채 runner로 전달된다.

## Invariants / fail-fast
- existing broken ledger는 rebuild fallback 없이 실패한다.
- sampled metadata-derived design variables는 setup facade 호출 인자로 전달한다.
- 지원되는 setup-ready role set이 아니면 build는 fail-fast 하며 다른 경로로 fallback하지 않는다.
- `tx_rect_void_columns`는 parser/sampler-only milestone 경계 역할로 간주되며, setup-ready 경계에서 parser/sampler 메시지로 즉시 실패해야 한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_sampled.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]
- [[sdd/code/entry/build.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 변경 시 주의점
- plate-stack build를 import-only로 되돌리는 우회 경로를 만들지 않는다.
- plate-stack branch contract를 reduced port-ready surface로 낮추지 않는다.

---
title: type2_step_export.py
created: 2026-04-17 @ 09:09
updated: 2026-04-19 @ 21:42
tags:
  - step-export
  - export
---

# type2_step_export.py

## Source
- Path: `src/peetsfea/type2_step_export.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_export.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- type2 export facade다.
- active TX/RX plate-stack exact body-name contract와 terminal sentinel export contract를 step ledger에 고정한다.

## 입력 / 출력
- 입력: TOML path, output dir, ledger path, seed
- 출력: `type2_scene.step`, per-modeled metadata, `type2_step_ledger.json`

## Canonical state
- TX plate exact body order는 `tx_copper_wall`, `tx_pcb_wall`, `tx_stack_*`, `tx_pcb_coil`, `tx_copper_coil` 34 bodies다.
- RX plate exact body order는 `rx_copper_wall`, `rx_pcb_wall`, `rx_stack_*`, `rx_pcb_coil`, `rx_copper_coil` 34 bodies다.
- active plate roles는 port-sheet self-check를 하지 않고 `terminal_metadata.kind == "none"`으로 skip된다.

## Invariants / fail-fast
- export body names/count는 role contract와 exact match여야 한다.
- active plate roles는 `tx_rect_void` direct-export bridge를 통과하면 안 된다.
- plate role body-order drift는 import-side exact-name contract drift다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- geometry-only plate roles를 coil export self-check 규칙에 다시 묶지 않는다.
- direct TX single-coil export helper와 active full-scene export contract를 혼동하지 않는다.

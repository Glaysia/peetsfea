---
title: tx_rect_void_export.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - type2
  - tx-rect-void
  - step-export
---

# tx_rect_void_export.py

## Source
- Path: `src/peetsfea/tx_rect_void_export.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void_export.py.md`
- Status: planned split target; source file is not created yet.
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Parent note: [[sdd/code/src/peetsfea/tx_rect_void.py]]

## 역할
- copper primitive assembly, box decomposition, STEP scene generation, metadata writing, export orchestration을 담당한다.

## 입력 / 출력
- 입력: realized single-coil state, centerline, placement offset, output paths, role profile.
- 출력: `build_tx_rect_void_box_specs()`, `build_tx_rect_void_step_scene()`, `export_tx_rect_void_step_from_spec()`, metadata payload.

## Canonical state
- canonical geometry owner는 validated copper primitive set과 exported body set이다.
- debug `BoxSpec`은 derived decomposition이며 live geometry owner가 아니다.
- exported PCB body는 debug `BoxSpec` box를 그대로 쓰지 않고, corresponding exported copper body로 boolean cut된 solid다.

## Invariants / fail-fast
- positive-area short/void overlap은 즉시 raise한다.
- expected exported body names/count는 metadata와 exact-name import contract를 일치시켜야 한다.
- scene-absolute bounds와 terminal plane metadata는 export 시점에 완결돼야 한다.
- exported PCB and copper solids must have zero shared volume in the final STEP body set.
- PCB cut 결과가 exactly one solid가 아니면 즉시 실패해야 한다.

## 직접 의존
- [[sdd/code/src/peetsfea/tx_rect_void_types.py]]
- [[sdd/code/src/peetsfea/tx_rect_void_centerline.py]]
- [[sdd/code/src/peetsfea/tx_rect_void_geometry.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/entry/export_tx_rect_void_step.py]]
- [[sdd/code/entry/generate_type2_step.py]]
- compatibility facade `tx_rect_void.py`

## 관련 테스트
- [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- box decomposition, primitive geometry, modeled metadata를 같은 owner처럼 다루지 않는다.
- body naming을 바꾸면 type2 import pipeline exact-name matching이 같이 깨진다.

## Links
- [[sdd/code/src/peetsfea/tx_rect_void_geometry.py]]
- [[sdd/code/src/peetsfea/tx_rect_void_centerline.py]]
- [[sdd/code/entry/generate_type2_step.py]]

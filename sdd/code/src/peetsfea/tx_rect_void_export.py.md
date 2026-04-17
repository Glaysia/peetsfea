---
title: tx_rect_void_export.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 14:11
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
- single-layer type2 STEP export adds one extra exported sheet body per single-coil modeled object (`tx_port_sheet` / `rx_port_sheet`) without changing copper/PCB ownership.
- the current single-layer type2 scene exports exactly two port sheets total: `tx_port_sheet` and `rx_port_sheet`.
- each sheet is a single face that connects the two terminal stubs of its coil.
- the single-layer port-sheet geometry is rebuilt from the two terminal-stub bottom-face squares.
- in the shared bottom-face plane, the straight line between the two stub centers is the diagonal-selection reference.
- on each stub square, the chosen diagonal is the one whose two endpoints maximize the sum of perpendicular distances to that inter-stub centerline; ties stay deterministic by preserving candidate order.
- the final sheet bridges those two widened diagonals as one separate face body.

## Invariants / fail-fast
- positive-area short/void overlap은 즉시 raise한다.
- expected exported body names/count는 metadata와 exact-name import contract를 일치시켜야 한다.
- scene-absolute bounds와 terminal plane metadata는 export 시점에 완결돼야 한다.
- exported PCB and copper solids must have zero shared volume in the final STEP body set.
- PCB cut 결과가 exactly one solid가 아니면 즉시 실패해야 한다.
- port sheet body is a separate top-level STEP child: it must not be fused into copper and must not be cut from PCB.
- port sheet geometry is owned by the pair of terminal-stub bottom-face squares, not by a single lowest stub square and not by the terminal-pair span.
- for the single-layer path, the sheet face must lie in the shared plane of the two stub bottom faces, include both widened stub diagonals as sheet edges, and use the remaining two edges as cross-stub bridges.
- when the layer-0 copper primitive set does not expose exactly one `start` stub and one `end` stub, two valid bottom-face squares, a shared bottom-face plane, distinct stub centers, or two non-degenerate widened diagonals, export must raise immediately with stub context.
- the current port-sheet path requires `tx_single_coil.layer_count == 1`; TX multilayer entering this path is a fail-fast error until follow-up work lands.

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
- exact stable sheet labels `tx_port_sheet` and `rx_port_sheet` are now part of the modeled export contract for the single-layer path.
- the widened diagonal choice on each terminal-stub bottom square must stay deterministic; changing the inter-stub-centerline scoring contract changes the exported sheet boundary.
- sheet label/order changes also break modeled metadata `expected_exported_body_names` and downstream import partition assumptions.

## Links
- [[sdd/code/src/peetsfea/tx_rect_void_geometry.py]]
- [[sdd/code/src/peetsfea/tx_rect_void_centerline.py]]
- [[sdd/code/entry/generate_type2_step.py]]

---
title: type2_single_coil_ports.py
created: 2026-04-20 @ 00:00
updated: 2026-04-20 @ 00:00
tags:
  - scene
  - ports
---

# type2_single_coil_ports.py

## Source
- Path: `src/peetsfea/type2_single_coil_ports.py`
- Code note path: `sdd/code/src/peetsfea/type2_single_coil_ports.py.md`
- Status: planned
- Primary plan: [[sdd/plans/0.2.22-type2-step-scene-split]]

## 역할
- single-coil terminal metadata와 legacy port-sheet helper geometry를 담당한다.
- terminal path parsing, terminal plane points, selected diagonal plane points, port-sheet vertices, and port-sheet labels를 소유한다.

## 입력 / 출력
- 입력: realized terminal path, centerline, `SingleCoilProfile`, frame origin, transformed `BoxSpec` tuple
- 출력: terminal metadata payload, optional port-sheet `bd.Shape`, port-sheet vertices

## Canonical state
- terminal metadata is scene-absolute when a type2 placement offset is applied.
- port-sheet helper geometry follows the existing single-coil metadata-owned sheet rule and is not used for active plate-stack roles.

## Invariants / fail-fast
- malformed terminal paths raise.
- missing terminal owner boxes raise.
- port-sheet vertex selection must not silently swap to alternate terminal geometry.

## Collaborators
- [[sdd/code/src/peetsfea/type2_single_coil_scene.py]]
- [[sdd/code/src/peetsfea/tx_rect_void.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- Do not pull plate-stack `stub_port` behavior into this module.
- Do not reconstruct removed single-coil public `void_*` inputs from scene state.

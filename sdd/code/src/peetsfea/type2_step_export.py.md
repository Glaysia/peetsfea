---
title: type2_step_export.py
created: 2026-04-17 @ 09:09
updated: 2026-04-20 @ 02:20
tags:
  - step-export
  - export
---

# type2_step_export.py

## Source
- Path: `src/peetsfea/type2_step_export.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_export.py.md`
- Status: active

## Ownership
- Primary plan: [[sdd/plans/0.2.22-type2-plate-stack-material-merge]]
- Primary architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- type2 export facade다.
- active TX/RX plate-stack exact body-name contract와 `stub_port` metadata export contract를 step ledger에 고정한다.

## 입력 / 출력
- 입력: TOML path, output dir, ledger path, seed
- 출력: `type2_scene.step`, per-modeled metadata, `type2_step_ledger.json`

## Canonical state
- TX/RX plate-stack ledger validation contract는 full exact body-name surface를 유지한다.
- plate-stack exact body list에는 explicit copper/pcb/bridge/stub names가 그대로 남고, ferrite-family만
  merged per-material names로 collapse된다:
  TX=`tx_stack_pet_psa`, `tx_stack_ferrite`, `tx_stack_air`; RX=`rx_stack_pet_psa`, `rx_stack_ferrite`, `rx_stack_air`.
- plate exact body count는 realized turn-count에 따라 달라지며 role당 `3`으로 축약되지 않는다.
- non-overlap bridge/slab geometry update는 `tx_bridge_s*` / `rx_bridge_s*` 포함 exact body-name family를 변경하지 않는다.
- `tx_bridge_s*` / `rx_bridge_s*` bridge family는 wall copper outer face와 coil copper inner face 사이 interior X span만 소유한다.
- bridge와 `*_pcb_wall`, merged stack slab(`*_stack_pet_psa`, `*_stack_ferrite`, `*_stack_air`), `*_pcb_coil`, adjacent copper turn(`*_copper_wall_t*`, `*_copper_coil_t*`)은 positive-volume overlap이 없어야 한다. face/edge contact는 허용한다.
- ferrite group contract는 role당 정확히 1개다:
  TX `g_ferrite_tx`, RX `g_ferrite_rx`.
- ferrite group members는 merged material names 3개 순서와 exact match해야 한다.
- active plate roles도 metadata-only port-sheet self-check를 수행한다.

## Invariants / fail-fast
- export body names/count는 role contract와 exact match여야 한다.
- export body groups는 ferrite family group contract와 exact match여야 한다.
- active plate roles에서 old `*_stack_*_uN` contract는 허용하지 않는다.
- active plate roles는 `tx_rect_void` direct-export bridge를 통과하면 안 된다.
- exported solid pair positive-volume overlap은 fail-fast failure다.
- plate role body-order drift는 import-side exact-name contract drift다.
- plate role `terminal_metadata.kind`는 `stub_port` 외 값을 허용하지 않는다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_plate_stack.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- geometry-only plate roles를 coil export self-check 규칙에 다시 묶지 않는다.
- direct TX single-coil export helper와 active full-scene export contract를 혼동하지 않는다.
- plate-stack metadata-only port sheet를 STEP body list에 섞지 않는다.
- spec parser가 여전히 `shoe_depth_mm`를 가질 수 있어도 export contract는 그 field에 의존하지 않는다.
- import/runtime에서 geometry heal/subtract를 하지 않으므로 export 단계 non-overlap contract를 약화하지 않는다.

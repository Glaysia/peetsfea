---
title: type2_step_export.py
created: 2026-04-17 @ 09:09
updated: 2026-04-19 @ 23:59
tags:
  - step-export
  - export
---

# type2_step_export.py

## Source
- Path: `src/peetsfea/type2_step_export.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_export.py.md`
- Status: active
- Related feature plans: [[sdd/plans/0.2.22-type2-rx-plate-stack-striped-copper]], [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]], [[sdd/plans/0.2.22-type2-plate-stack-bridge-non-overlap-export]]

## 역할
- type2 export facade다.
- active TX/RX plate-stack exact body-name contract와 `stub_port` metadata export contract를 step ledger에 고정한다.

## 입력 / 출력
- 입력: TOML path, output dir, ledger path, seed
- 출력: `type2_scene.step`, per-modeled metadata, `type2_step_ledger.json`

## Canonical state
- TX/RX plate exact body order는 `*_copper_wall_t*`, `*_pcb_wall`, `*_stack_*`, `*_pcb_coil`,
  `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_in/out`다.
- plate exact body count는 formula가 아니라 `expected_plate_stack_body_names()` generator 결과가 owner다.
- active fixed baselines는 TX/RX 모두 `43` bodies다.
- non-overlap bridge/slab geometry update는 `tx_bridge_s*` / `rx_bridge_s*` 포함 exact body-name family를 변경하지 않는다.
- `tx_bridge_s*` / `rx_bridge_s*` bridge family는 wall copper outer face와 coil copper inner face 사이 interior X span만 소유한다.
- bridge와 `*_pcb_wall`, `*_stack_pet_psa_u*`, `*_stack_ferrite_u*`, `*_stack_air_u*`, `*_pcb_coil`, adjacent copper turn(`*_copper_wall_t*`, `*_copper_coil_t*`)은 positive-volume overlap이 없어야 한다. face/edge contact는 허용한다.
- ferrite group contract는 role당 정확히 1개다:
  TX `g_ferrite_tx`, RX `g_ferrite_rx`.
- ferrite group members는 exported ferrite family flat body names를 생성 순서 그대로 flatten한 목록이다.
- active plate roles도 metadata-only port-sheet self-check를 수행한다.

## Invariants / fail-fast
- export body names/count는 role contract와 exact match여야 한다.
- export body groups는 ferrite family group contract와 exact match여야 한다.
- active plate roles는 `tx_rect_void` direct-export bridge를 통과하면 안 된다.
- exported solid pair positive-volume overlap은 fail-fast failure다.
- plate role body-order drift는 import-side exact-name contract drift다.
- plate role `terminal_metadata.kind`는 `stub_port` 외 값을 허용하지 않는다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- geometry-only plate roles를 coil export self-check 규칙에 다시 묶지 않는다.
- direct TX single-coil export helper와 active full-scene export contract를 혼동하지 않는다.
- plate-stack metadata-only port sheet를 STEP body list에 섞지 않는다.
- spec parser가 여전히 `shoe_depth_mm`를 가질 수 있어도 export contract는 그 field에 의존하지 않는다.
- import/runtime에서 geometry heal/subtract를 하지 않으므로 export 단계 non-overlap contract를 약화하지 않는다.

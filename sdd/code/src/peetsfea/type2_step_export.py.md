---
title: type2_step_export.py
created: 2026-04-17 @ 09:09
updated: 2026-04-20 @ 04:18
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
- Primary plan: [[sdd/plans/0.2.22-type2-plate-stack-copper-unite-grouping]]
- Primary architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- type2 export facade다.
- active TX/RX plate-stack exact body-name contract와 `stub_port` metadata export contract를 step ledger에 고정한다.
- sample entrypoint가 긴 STEP 생성 중 coarse phase를 표시할 수 있도록 optional stage reporter를 호출한다.

## 입력 / 출력
- 입력: TOML path, output dir, ledger path, seed, optional stage reporter
- 출력: `type2_scene.step`, per-modeled metadata, `type2_step_ledger.json`

## Canonical state
- TX/RX plate-stack ledger validation contract는 pre-unite surface와 final handoff surface를 분리해 유지한다.
- pre-unite exact body list에는 explicit copper/pcb/bridge/stub names가 남고, ferrite-family는 merged material body names로 정규화된다.
- final export surface에서는 role당 6개 이름만 handoff한다(동일 순서로 import reconstruction/mesh 기대치도 공유):
  `tx_plate_copper`, `tx_pcb_wall`, `tx_stack_pet_psa`, `tx_stack_ferrite`, `tx_stack_air`, `tx_pcb_coil`,
  `rx_plate_copper`, `rx_pcb_wall`, `rx_stack_pet_psa`, `rx_stack_ferrite`, `rx_stack_air`, `rx_pcb_coil`.
- pre-unite 정확 body count는 realized turn-count에 따라 달라지며 role당 `3`으로 축약되지 않는다.
- expected_exported_body_groups는 copper/ferrite family를 각각 다음으로 노출한다:
  - `g_copper_tx -> [tx_plate_copper]`
  - `g_ferrite_tx -> [tx_stack_pet_psa, tx_stack_ferrite, tx_stack_air]`
  - `g_copper_rx -> [rx_plate_copper]`
  - `g_ferrite_rx -> [rx_stack_pet_psa, rx_stack_ferrite, rx_stack_air]`
- non-overlap bridge/slab geometry update는 `tx_bridge_s*` / `rx_bridge_s*` pre-unite segment label family를 유지한다.
- `tx_bridge_s*` / `rx_bridge_s*` bridge segment family는 wall copper outer face와 coil copper inner face 사이 interior X span만 소유한다.
- bridge와 `*_pcb_wall`, merged stack slab(`*_stack_pet_psa`, `*_stack_ferrite`, `*_stack_air`), `*_pcb_coil`, adjacent copper turn(`*_copper_wall_t*`, `*_copper_coil_t*`)은 positive-volume overlap이 없어야 한다. face/edge contact는 허용한다.
- ferrite/copper group contract는 role당 정확히 1개씩이다:
  - `g_copper_tx`, `g_ferrite_tx`
  - `g_copper_rx`, `g_ferrite_rx`
- ferrite group members는 merged material names 3개 순서와 exact match해야 한다.
- active plate roles도 metadata-only port-sheet self-check를 수행한다.
- `stub_port` metadata의 `input_stub_body_name`, `output_stub_body_name`은 imported copper 이름이 아닌 pre-unite 라벨(`*_stub_in/out`)으로 채워야 한다.
- imported body handoff는 copper/ferrite role body names를 그대로 사용하며, copper 그룹은 `g_copper_tx`, `g_copper_rx`로, ferrite 그룹은 `g_ferrite_tx`, `g_ferrite_rx`로 복원해야 한다.
- reporter phase surface는 `build_scene`, `export_scene_step`, `finalize_step_artifacts`로 제한한다.

## Invariants / fail-fast
- export body names/count는 role contract와 exact match여야 한다.
- export body groups는 `expected_exported_body_groups` contract과 exact match여야 한다. (`g_copper_*`, `g_ferrite_*`)
- `expected_exported_body_count`는 TX/RX 각각 `6`이어야 한다.
- active plate roles에서 old `*_stack_*_uN` contract는 허용하지 않는다.
- final export body list에서는 `*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_in/out`가 없어야 한다.
- active plate roles는 `tx_rect_void` direct-export bridge를 통과하면 안 된다.
- exported solid pair positive-volume overlap은 fail-fast failure다.
- plate role body-order drift는 import-side exact-name contract drift다.
- plate role `terminal_metadata.kind`는 `stub_port` 외 값을 허용하지 않는다.
- reporter callback은 progress visibility only이며 exporter의 fail-fast contract를 완화하지 않는다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_plate_stack.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]
- [[sdd/code/src/peetsfea/type2_sampled.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- geometry-only plate roles를 coil export self-check 규칙에 다시 묶지 않는다.
- direct TX single-coil export helper와 active full-scene export contract를 혼동하지 않는다.
- plate-stack metadata-only port sheet를 STEP body list에 섞지 않는다.
- spec parser가 여전히 `shoe_depth_mm`를 가질 수 있어도 export contract는 그 field에 의존하지 않는다.
- import/runtime에서 geometry heal/subtract를 하지 않으므로 export 단계 non-overlap contract를 약화하지 않는다.

---
title: type2_step_ledger.py
created: 2026-04-17 @ 09:09
updated: 2026-04-22 @ 00:00
tags:
  - step-export
  - ledger
---

# type2_step_ledger.py

## Source
- Path: `src/peetsfea/type2_step_ledger.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_ledger.py.md`
- Status: active
- Primary plan: [[sdd/plans/0.2.22-type2-plate-stack-copper-unite-grouping]]
- Related feature plan: [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]]
- Related TX array plan: [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]]
- Related TX rect/void columns plan: [[sdd/plans/0.2.22-type2-tx-rect-void-columns-geometry]]

## 역할
- exported type2 scene metadata를 top-level step ledger와 per-modeled metadata JSON으로 고정한다.

## 입력 / 출력
- 입력: scene data, output paths, source TOML provenance, retained `outputs`
- 출력: `type2_step_ledger.json`, modeled metadata JSON files

## Canonical state
- modeled role union에는 `tx_plate_stack`, `rx_plate_stack`, and geometry-only `tx_rect_void_columns`가 포함된다.
- non-model member union allows material-bearing members and materialless reservation members; `tx_region_actual_stack_space` uses the materialless member shape.
- active plate role canonical handoff는 `expected_exported_body_names`, `expected_exported_body_groups`,
  `expected_exported_body_count`, `canonical_coordinates`, `terminal_metadata.kind = "stub_port"`다.
- `expected_exported_body_names`는 RX와 single-branch TX에서 role-local 6-body 정렬을 유지한다:
  `*_plate_copper`, `*_pcb_wall`, `*_stack_pet_psa`, `*_stack_ferrite`, `*_stack_air`, `*_pcb_coil`.
- TX arrays expand branch-local non-copper exact names while keeping one united `tx_plate_copper` in the same TX modeled entry.
- `tx_rect_void_columns` modeled entries are STEP-export-only handoff entries. Parallel mode records `kind = "parallel_collector_tabs"` and series mode records `kind = "series_collector_tabs"`; both expose exactly two metadata-owned future terminal-tab faces and remain unsupported for setup-ready attach/port setup as well as import handoff.
- plate role field ownership은 input TOML에 두고, ledger는 exact export contract만 보존한다.
- final handoff expected_exported_body_count is the exact exported list length; RX and TX `tx_coil_count = 1` remain `6`.
- expected_exported_body_groups는 다음을 반영한다:
  - `g_copper_tx -> [tx_plate_copper]`
  - `g_ferrite_tx -> [TX exact ferrite-family body names in export order]`
  - `g_copper_rx -> [rx_plate_copper]`
  - `g_ferrite_rx -> [rx_stack_pet_psa, rx_stack_ferrite, rx_stack_air]`
- `terminal_metadata.input_stub_body_name`/`output_stub_body_name`은 plate-stack source terminal labels이며
  TX array에서는 branch 0 terminal geometry를 기준으로 한다.

## Invariants / fail-fast
- active plate roles는 generator-owned exact-name order와 exact-name count를 lossless로 유지해야 한다.
- plate role terminal metadata wire shape는 stub body names, plane endpoints, 4-vertex port sheet를 lossless로 유지해야 한다.
- ledger shape mismatch와 missing retained `outputs`는 hard failure다.
- active plate roles에서 exported/imported handoff body list는 pre-unite 라벨(`*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_in/out`)을 포함해선 안 된다.
- materialless non-model members must omit the `material` key instead of carrying a fake material token.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- plate role runtime state를 ledger duplicated field로 늘리지 않는다.
- active import-only/runtime validation contract와 exact-name taxonomy를 같이 유지해야 한다.
- plate-stack terminal metadata wire shape drift는 import-ledger validation과 modeled import adapter를 같이 갱신해야 한다.

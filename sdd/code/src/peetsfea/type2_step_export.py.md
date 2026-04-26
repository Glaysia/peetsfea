---
title: type2_step_export.py
created: 2026-04-17 @ 09:09
updated: 2026-04-22 @ 04:35
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
- Primary plan: [[sdd/plans/0.2.22-type2-plate-stack-equivalent-3-slab]]
- TX array plan: [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]]
- TX actual-region plan: [[sdd/plans/0.2.22-type2-tx-actual-region-non-model-sampling]]
- Scene split plan: [[sdd/plans/0.2.22-type2-step-scene-split]]
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
- ferrite-family material names are produced as direct equivalent slabs; export does not depend on a public `ferrite_set_count`.
- final export surface for RX and single-branch TX handoff uses role-local 6-name order:
  `tx_plate_copper`, `tx_pcb_wall`, `tx_stack_pet_psa`, `tx_stack_ferrite`, `tx_stack_air`, `tx_pcb_coil`,
  `rx_plate_copper`, `rx_pcb_wall`, `rx_stack_pet_psa`, `rx_stack_ferrite`, `rx_stack_air`, `rx_pcb_coil`.
- TX `tx_coil_count > 1` expands branch-local non-copper final names, but exports one united `tx_plate_copper`
  conductor that includes branch copper and thick connector bridge solids.
- pre-unite 정확 body count는 realized turn-count에 따라 달라지며 role당 `3`으로 축약되지 않는다.
- expected_exported_body_groups는 copper/ferrite family를 각각 다음으로 노출한다:
  - `g_copper_tx -> [tx_plate_copper]`
  - `g_ferrite_tx -> [tx branch ferrite-family bodies in exact export order]`
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
- `stub_port` metadata의 `input_stub_body_name`, `output_stub_body_name`은 plate-stack source terminal labels이며
  TX array에서는 branch 0 terminal geometry를 기준으로 한 단일 TX port를 유지한다.
- imported body handoff는 copper/ferrite role body names를 그대로 사용하며, copper 그룹은 `g_copper_tx`, `g_copper_rx`로, ferrite 그룹은 `g_ferrite_tx`, `g_ferrite_rx`로 복원해야 한다.
- reporter phase surface는 `build_scene`, `export_scene_step`, `finalize_step_artifacts`로 제한한다.
- Full-scene export must carry resolved `tx_region_actual` tile bodies as non-model members in the shared non-model scene ledger.
- Full-scene export must carry resolved `tx_region_actual_stack_space` materialless tile members and apply deterministic tilt transforms shared with geometry-only TX column bodies.
- Shared non-model tilt helpers and canonical shape extraction are imported from split scene helper modules, not private helpers on `type2_step_scene.py`.
- `tx_rect_void_columns` now participates in active full-scene STEP geometry export as a geometry-only modeled role.
- Full-scene modeled dispatch routes `tx_rect_void_columns` through `_build_tx_rect_void_columns_scene_data`, computes
  `rx_center_xyz` from `rx_region_max`, and passes it through to the column builder for deterministic TX-plane 2D distance turn allocation.
- `tx_rect_void_columns` terminal stub bodies use a shared floorward bottom Z: export computes every terminal's natural
  bottom candidate from its transformed lowest contact face and requested `terminal_stub_length_mm`, then lofts all
  terminal stubs down to the lowest candidate so tilted columns terminate at one common height.
- For realized `tx_rect_void_columns.connection_mode = 0`, export delegates underside start/end collector pours to
  `type2_tx_rect_void_collectors.py`, fuses all branch copper, vertical stubs, collector pours/drops, and external
  tabs into one `tx_rect_void_columns_copper` body, and records the two future port-tab faces in terminal metadata.
- Pour source label metadata for the parallel collector branch is now strictly pour-centric: `start_pours`, `end_pours`,
  `end_layer_drops`, `start_external_tabs`, and `end_external_tabs`.
- For realized `tx_rect_void_columns.connection_mode = 1`, export delegates underside series straps to
  `type2_tx_rect_void_collectors.py`, fuses all branch copper, vertical stubs, series straps, and external
  tabs into one `tx_rect_void_columns_copper` body, and records the two future port-tab faces in terminal metadata.
- After the final fused `tx_rect_void_columns_copper` body is created, every TX columns PCB body is cut by that final
  conductor so the STEP handoff has no positive-volume PCB/copper intersections for HFSS validation.
- Full-scene export preflight deactivation is removed for `tx_rect_void_columns`; direct `export_type2_tx_single_coil_artifact` continues to reject this role with the parser/sampler milestone message.
- Internal modeled export-contract validation now checks `tx_rect_void_columns` using scene-metadata expected names/count and requires empty body groups for geometry-only phase.

## Invariants / fail-fast
- export body names/count는 role contract와 exact match여야 한다.
- export body groups는 `expected_exported_body_groups` contract과 exact match여야 한다. (`g_copper_*`, `g_ferrite_*`)
- `expected_exported_body_count` must match the exact exported list length; RX and TX `tx_coil_count = 1` remain `6`.
- active plate roles에서 old `*_stack_*_uN` contract는 허용하지 않는다.
- active plate roles에서 `ferrite_set_count`를 public input 또는 ledger/export 계산 dependency로 되살리면 안 된다.
- final export body list에서는 `*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_in/out`가 없어야 한다.
- full-scene export은 `tx_rect_void_columns`를 생성 경로로 허용한다.
- `tx_rect_void_columns` floorward terminal stub bottoms must share one Z coordinate after tilt transform; per-tile fixed-length
  bottom drift is contract drift.
- Parallel and series `tx_rect_void_columns` collector metadata must expose exactly two future terminal-tab faces and no per-branch port-sheet contract.
- TX columns PCB final cuts must produce exactly one solid per PCB body; split or empty PCB results are export failures.
- Parallel `tx_rect_void_columns` collector source labels must expose only pour-centric groups and must not emit deprecated row rail/spine/feeder labels.
- Parallel `tx_rect_void_columns` collector pour routing must fail fast on positive-volume start/end collector intersection, aggregate start/end reach imbalance, or per-branch spread beyond the internal limit.
- tx_single_coil direct export는 parser/sampler milestone rejection 메시지로 `tx_rect_void_columns`를 거부한다.
- preflight guard bypass(예: monkeypatch/no-op) 상황에서는 tx-single-coil direct export 경계에서 parser/sampler milestone 메시지로 즉시 오류를 raise해야 한다.
- exported solid pair positive-volume overlap은 fail-fast failure다.
- plate role body-order drift는 import-side exact-name contract drift다.
- plate role `terminal_metadata.kind`는 `stub_port` 외 값을 허용하지 않는다.
- reporter callback은 progress visibility only이며 exporter의 fail-fast contract를 완화하지 않는다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_plate_stack.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_scene_geometry.py]]
- [[sdd/code/src/peetsfea/type2_non_model_scene.py]]
- [[sdd/code/src/peetsfea/type2_tx_rect_void_columns.py]]
- [[sdd/code/src/peetsfea/type2_tx_rect_void_collectors.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]
- [[sdd/code/src/peetsfea/type2_sampled.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- geometry-only plate roles를 coil export self-check 규칙에 다시 묶지 않는다.
- direct TX single-coil export helper와 active full-scene export contract를 혼동하지 않는다.
- plate-stack metadata-only port sheet를 STEP body list에 섞지 않는다.
- removed public fields such as `shoe_depth_mm` and `ferrite_set_count` must not re-enter export contracts.
- import/runtime에서 geometry heal/subtract를 하지 않으므로 export 단계 non-overlap contract를 약화하지 않는다.

---
title: type2_step_ledger.py
created: 2026-04-17 @ 09:09
updated: 2026-04-19 @ 21:42
tags:
  - step-export
  - ledger
---

# type2_step_ledger.py

## Source
- Path: `src/peetsfea/type2_step_ledger.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_ledger.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- exported type2 scene metadata를 top-level step ledger와 per-modeled metadata JSON으로 고정한다.

## 입력 / 출력
- 입력: scene data, output paths, source TOML provenance, retained `outputs`
- 출력: `type2_step_ledger.json`, modeled metadata JSON files

## Canonical state
- modeled role union에는 `tx_plate_stack`와 `rx_plate_stack`가 포함된다.
- active plate role canonical handoff는 `expected_exported_body_names`, `expected_exported_body_count`, `canonical_coordinates`, `terminal_metadata = {"kind": "none"}`다.
- plate role field ownership은 input TOML에 두고, ledger는 exact export contract만 보존한다.

## Invariants / fail-fast
- active plate roles는 literal 34-body exact-name order를 lossless로 유지해야 한다.
- geometry-only roles terminal metadata는 sentinel shape를 유지해야 한다.
- ledger shape mismatch와 missing retained `outputs`는 hard failure다.

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

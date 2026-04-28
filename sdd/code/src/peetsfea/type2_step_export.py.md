---
title: type2_step_export.py
created: 2026-04-17 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - step-export
  - export
---

# type2_step_export.py

## Source
- Path: `src/peetsfea/type2_step_export.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_export.py.md`
- Status: active

## 역할
- type2 STEP export facade다.
- sampled/build path가 RX modeled geometry와 retained non-model guide/context를 STEP/ledger artifact로 넘기도록 조율한다.
- sample entrypoint가 긴 STEP 생성 중 coarse phase를 표시할 수 있도록 optional stage reporter를 호출한다.

## 입력 / 출력
- 입력: TOML path, output dir, ledger path, seed, optional stage reporter
- 출력: `type2_scene.step`, RX modeled metadata, `type2_step_ledger.json`

## Canonical state
- RX exported body names/counts/groups must be exact and deterministic.
- `tx_region` may be exported as non-modeled future guide context, but it is not modeled TX geometry.
- RxOnly handoff carries enough RX terminal metadata for one RX lumped port.
- report variable ownership is deferred to [type2-em-report-contract](../../../architecture/type2-em-report-contract.md).
- reporter phase surface is `build_scene`, `export_scene_step`, `finalize_step_artifacts`.

## Invariants / fail-fast
- export body names/counts must match the active RX contract exactly.
- export body groups must match the active RX ledger contract exactly.
- generic `SOLID*` drift is an export contract failure, not an import rename task.
- RxOnly export must not require or synthesize TX modeled geometry.
- reporter callback is progress visibility only and must not weaken fail-fast behavior.

## Collaborators
- [type2_step_scene.py](type2_step_scene.py.md)
- [type2_scene_geometry.py](type2_scene_geometry.py.md)
- [type2_non_model_scene.py](type2_non_model_scene.py.md)
- [type2_step_ledger.py](type2_step_ledger.py.md)
- [type2_sampled.py](type2_sampled.py.md)
- [type2_step_import_ledger.py](backend/pyaedt/type2_step_import_ledger.py.md)

## 관련 테스트
- [test_generate_type2_step.py](../../tests/type2/test_generate_type2_step.py.md)

## 변경 시 주의점
- TX shape-specific body sets, arrays, or collector geometry must not be documented here during the 0.2.24 reset.
- Port-sheet metadata must stay metadata; do not add it as a STEP body contract.

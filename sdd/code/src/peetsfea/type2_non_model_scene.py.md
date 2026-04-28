---
title: type2_non_model_scene.py
created: 2026-04-20 @ 00:00
updated: 2026-04-28 @ 00:00
tags:
  - scene
  - non-model
---

# type2_non_model_scene.py

## Source
- Path: `src/peetsfea/type2_non_model_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_non_model_scene.py.md`
- Status: active

## 역할
- type2 non-model scene resolution과 non-model scene ledger/shape 생성을 담당한다.
- 0.2.24 SDD 기준 `tx_region`은 future TX placement guide only다.
- RX non-model context remains valid when owned by RX setup/export flow.

## 입력 / 출력
- 입력: parsed non-model specs, seed, active modeled RX context
- 출력: resolved non-model specs, non-model shapes, non-model ledger entries

## Canonical state
- non-model scene member order must be deterministic.
- `environment`, `tx_region`, and RX region/context objects are non-conductor context unless a specific RX path owns otherwise.
- `tx_region` guide bodies are never mesh or port owners.

## Invariants / fail-fast
- unsupported object ids, duplicate specs, invalid ranges, and missing parent specs raise immediately.
- non-model guide geometry must not create TX ports, TX output variables, or conductor mesh targets in RxOnly.

## Collaborators
- [type2_scene_geometry.py](type2_scene_geometry.py.md)
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_step_ledger.py](type2_step_ledger.py.md)
- [type2_step_export.py](type2_step_export.py.md)

## 관련 테스트
- [test_generate_type2_step.py](../../tests/type2/test_generate_type2_step.py.md)

## 변경 시 주의점
- Do not restore derived TX actual/stack-space shape contracts while the 0.2.24 TX reset is active.

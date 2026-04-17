---
title: type2_step_spec.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 16:02
tags:
  - type2
  - step-export
---

# type2_step_spec.py

## Source
- Path: `src/peetsfea/type2_step_spec.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec.py.md`
- Status: active
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Parent note: [[sdd/code/entry/generate_type2_step.py]]

## 역할
- `type2_fixed.toml`의 unified object registry를 읽어 non-model / modeled spec dataclass로 정규화한다.
- type2 modeled single-coil spec를 `tx_rect_void` reusable TOML text로 렌더링하는 helper를 제공한다.

## 입력 / 출력
- 입력: type2 TOML path
- 출력: parsed non-model box spec, modeled single-coil spec, top-level type2 step spec

## Canonical state
- module-level mutable state는 없다.
- canonical input state는 parsed type2 object registry다.

## Invariants / fail-fast
- `design.units = mm`
- non-model and modeled registries are non-empty
- object ids are unique across both registries
- supported modeled roles are explicit and fail-fast
- modeled prototype id는 role별 canonical id와 일치해야 한다.
- modeled `material = composite`, `model_state = true`를 강제한다.

## 직접 의존
- profile ownership mapping from [[sdd/code/src/peetsfea/tx_rect_void.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- [[sdd/code/entry/generate_type2_step.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- spec parsing과 scene export를 다시 한 파일에 섞지 않는다.
- field shape 변경은 ledger and docs contract를 같이 갱신해야 한다.

## Links
- [[sdd/code/entry/generate_type2_step.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]

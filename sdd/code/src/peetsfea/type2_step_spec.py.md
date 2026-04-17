---
title: type2_step_spec.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 19:20
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
- Related feature plan: [[sdd/plans/0.2.22-type2-tx-underlay-mull12060ferrite]]
- Parent note: [[sdd/code/entry/generate_type2_step.py]]

## 역할
- `type2_fixed.toml`의 unified object registry를 읽어 non-model / modeled spec dataclass로 정규화한다.
- type2 modeled single-coil spec를 `tx_rect_void` reusable TOML text로 렌더링하는 helper를 제공한다.
- shared modeled-object public field인 `underlay_repeat_count` ownership을 parser layer에서 고정하고, underlay scene-layer 책임과 `tx_rect_void` core geometry 책임을 분리한다.

## 입력 / 출력
- 입력: type2 TOML path
- 출력: parsed non-model box spec, modeled single-coil spec, top-level type2 step spec

## Canonical state
- module-level mutable state는 없다.
- canonical input state는 parsed type2 object registry다.
- `underlay_repeat_count`는 type2 modeled-object registry canonical field이며, per-unit underlay geometry decomposition은 parser가 아니라 scene layer에서 소유한다.

## Invariants / fail-fast
- `design.units = mm`
- non-model and modeled registries are non-empty
- object ids are unique across both registries
- supported modeled roles are explicit and fail-fast
- modeled prototype id는 role별 canonical id와 일치해야 한다.
- modeled `material = composite`, `model_state = true`를 강제한다.
- modeled `underlay_repeat_count`는 shared range field이며 canonical encoding은 `[true, 0, 8, 5]`다.
- TX는 realized candidate set `{0, 2, 4, 6, 8}`를 지원하고, RX는 current milestone에서 `0` 이외의 resolved value를 허용하지 않는다.
- `underlay_repeat_count`는 `tx_rect_void` reusable TOML bridge로 내려보내지 않는다. underlay는 single-coil core가 아니라 type2 scene/export/import 계층의 책임이다.

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
- modeled-object field를 `tx_rect_void` core field처럼 취급하지 않는다. `underlay_repeat_count` drift는 scene/import docs와 같이 고쳐야 한다.

## Links
- [[sdd/code/entry/generate_type2_step.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]

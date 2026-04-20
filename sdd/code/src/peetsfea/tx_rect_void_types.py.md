---
title: tx_rect_void_types.py
created: 2026-04-17 @ 09:09
updated: 2026-04-20 @ 23:59
tags:
  - tx-rect-void
---

# tx_rect_void_types.py

## Source
- Path: `src/peetsfea/tx_rect_void_types.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void_types.py.md`
- Status: planned split target; source file is not created yet.
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Parent note: [[sdd/code/src/peetsfea/tx_rect_void.py]]

## 역할
- rect/void single-coil runtime dataclass, typed metadata shape, role profile registry를 한곳에 모은다.

## 입력 / 출력
- 입력: role/profile literals, dataclass field definitions, metadata typed dict definitions.
- 출력: `SingleCoilProfile`, `RangeSpec`, `SingleCoilRectVoidSpec`, `RealizedSingleCoilRectVoid`, `BoxSpec`, modeled metadata types, `profile_for_modeled_role()`.

## Canonical state
- module-level mutable state는 없다.
- canonical profile registry `_PROFILE_BY_ROLE`만 이 파일이 소유한다.
- `SingleCoilRangeSpec` owns sampled/public ranges accepted by the core TOML, including canonical `void_usage_ratio`.

## Invariants / fail-fast
- role별 `object_id`, `plane`, `placement_owner_id`, body-name prefix는 stable contract여야 한다.
- runtime/state type는 nullable fallback 없이 required field를 유지해야 한다.
- `SingleCoilRangeSpec`는 public TOML sampled fields만 소유하며 legacy split/centered `void_*` range ownership을 포함하지 않는다.
- realized state may retain derived split void dimensions/bounds needed by geometry, but canonical input ownership is the single `void_usage_ratio` range.

## 직접 의존
- 표준 라이브러리 `dataclasses`, `typing`.

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/tx_rect_void_spec.py]]
- [[sdd/code/src/peetsfea/tx_rect_void_centerline.py]]
- [[sdd/code/src/peetsfea/tx_rect_void_export.py]]
- compatibility facade `tx_rect_void.py`

## 관련 테스트
- [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]

## 변경 시 주의점
- profile registry를 바꾸면 type2 placement, expected body names, import ownership contract가 같이 바뀐다.
- typed metadata shape를 바꾸면 export/import ledger와 tests를 같이 갱신해야 한다.

## Links
- [[sdd/code/src/peetsfea/tx_rect_void.py]]
- [[sdd/code/src/peetsfea/tx_rect_void_spec.py]]
- [[sdd/code/src/peetsfea/tx_rect_void_centerline.py]]
- [[sdd/code/src/peetsfea/tx_rect_void_export.py]]

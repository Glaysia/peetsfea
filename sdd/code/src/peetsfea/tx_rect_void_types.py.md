---
title: tx_rect_void_types.py
created: 2026-04-17 @ 09:09
updated: 2026-05-03 @ 00:00
tags:
  - tx-rect-void
---

# tx_rect_void_types.py

## Source
- Path: `src/peetsfea/tx_rect_void_types.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void_types.py.md`
- Status: planned split target; source file is not created yet.
- Primary graph owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)

## 역할
- rect/void single-coil runtime dataclass, typed metadata shape, role profile registry를 한곳에 모은다.
- Role profile별 geometry limit처럼 동일 core engine 안에서 caller별로 달라지는 authoring cap을 보관한다.

## 입력 / 출력
- 입력: role/profile literals, dataclass field definitions, metadata typed dict definitions.
- 출력: `SingleCoilProfile`, `RangeSpec`, `SingleCoilRectVoidSpec`, `RealizedSingleCoilRectVoid`, `BoxSpec`, modeled metadata types, `profile_for_modeled_role()`.

## Canonical state
- module-level mutable state는 없다.
- canonical profile registry `_PROFILE_BY_ROLE`만 이 파일이 소유한다.
- `SingleCoilRangeSpec` owns sampled/public ranges accepted by the core TOML, including canonical `void_usage_ratio`.
- `tx_inner_single_coil` owns explicit inner TX identity, `tx_inner_rect_void_coil` object id, XY plane, `tx_inner_region` placement owner, and `tx_inner_*` body prefixes.
- `tx_outer_single_coil` owns explicit outer TX identity, `tx_outer_rect_void_coil` object id, XY plane, `tx_outer_region` placement owner, and `tx_outer_*` body prefixes. Its profile identity is concrete even when its numeric ranges are derived from the inner TX spec.

## Invariants / fail-fast
- role별 `object_id`, `plane`, `placement_owner_id`, body-name prefix는 stable contract여야 한다.
- TX parallel rect-void roles share multilayer bus behavior, but only the explicit role names decide whether the caller may use them.
- TX inner/outer companion roles share multilayer bus behavior and sampling topology, but each role owns distinct object/body names and placement owner ids.
- `TX_PARALLEL_SINGLE_COIL_ROLES` includes the outer companion role so downstream geometry/export code can classify it as TX parallel-capable without guessing from object id text.
- `SingleCoilProfile.max_turn_count`는 core public single-coil path와 internal type2 TX columns 재사용 path의 turn cap을 분리한다.
- runtime/state type는 nullable fallback 없이 required field를 유지해야 한다.
- `SingleCoilRangeSpec`는 public TOML sampled fields만 소유하며 legacy split/centered `void_*` range ownership을 포함하지 않는다.
- realized state may retain derived split void dimensions/bounds needed by geometry, but canonical input ownership is the single `void_usage_ratio` range.

## 직접 의존
- 표준 라이브러리 `dataclasses`, `typing`.

## 이 파일을 쓰는 곳
- [tx_rect_void_spec.py](tx_rect_void_spec.py.md)
- [tx_rect_void_centerline.py](tx_rect_void_centerline.py.md)
- [tx_rect_void_export.py](tx_rect_void_export.py.md)
- compatibility facade `tx_rect_void.py`

## 관련 테스트
- `tests/tx_rect_void/test_tx_rect_void.py`

## 변경 시 주의점
- profile registry나 profile caps를 바꾸면 type2 placement, expected body names, import ownership contract가 같이 바뀐다.
- typed metadata shape를 바꾸면 export/import ledger와 tests를 같이 갱신해야 한다.

## Graph links
- Primary owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)
- Parent facade: [tx_rect_void.py](tx_rect_void.py.md)
- Direct parser contract: [tx_rect_void_spec.py](tx_rect_void_spec.py.md)
- Centerline handoff: [tx_rect_void_centerline.py](tx_rect_void_centerline.py.md)
- Export handoff: [tx_rect_void_export.py](tx_rect_void_export.py.md)
- Exceptional plan: [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)

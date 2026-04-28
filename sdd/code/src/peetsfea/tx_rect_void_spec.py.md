---
title: tx_rect_void_spec.py
created: 2026-04-17 @ 09:09
updated: 2026-04-20 @ 23:59
tags:
  - tx-rect-void
---

# tx_rect_void_spec.py

## Source
- Path: `src/peetsfea/tx_rect_void_spec.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void_spec.py.md`
- Status: planned split target; source file is not created yet.
- Related plan: [0.2.22-src-entry-800-line-refactor-threshold](../../../plans/0.2.22-src-entry-800-line-refactor-threshold.md)
- Parent note: [tx_rect_void.py](tx_rect_void.py.md)

## 역할
- rect/void TOML parsing, range validation, sampled realization을 담당한다.

## 입력 / 출력
- 입력: TOML path, integer seed, role profile.
- 출력: `load_tx_rect_void_spec()`, `realize_tx_rect_void_spec()`, range/validation helpers.

## Canonical state
- module-level mutable state는 없다.
- canonical realized geometry inputs는 `SingleCoilRectVoidSpec`와 `RealizedSingleCoilRectVoid`다.
- void keepout size is TOML-owned by canonical `void_usage_ratio`; realization applies the selected value to both local X and local Y while keeping the void centered.

## Invariants / fail-fast
- `design.units`는 `mm`여야 한다.
- range table shape/count/type 위반은 즉시 raise한다.
- `terminal_stub_length_mm` runtime ownership은 derived `layer_gap_mm * 0.8` 규칙을 따른다.
- TOML legacy split/centered `void_*` keys are unsupported and fail immediately instead of changing geometry.
- `void_usage_ratio` must realize to `0 < ratio < 1`; invalid candidates fail before geometry construction.
- `turn_count` resolved value는 active `SingleCoilProfile.max_turn_count` 이하여야 하며 범위를 벗어나면 즉시 raise한다. Public single-coil profiles keep max 6; internal type2 TX columns profile may allow the TOML-owned allocation range up to 36.
- `rx_single_coil.layer_count != 1`은 계속 fail-fast한다.

## 직접 의존
- [tx_rect_void_types.py](tx_rect_void_types.py.md)

## 이 파일을 쓰는 곳
- [tx_rect_void_centerline.py](tx_rect_void_centerline.py.md)
- [tx_rect_void_export.py](tx_rect_void_export.py.md)
- compatibility facade `tx_rect_void.py`

## 관련 테스트
- [test_tx_rect_void.py](../../tests/tx_rect_void/test_tx_rect_void.py.md)

## 변경 시 주의점
- parser shape를 바꾸면 active RX/reusable code notes와 type2 export path를 같이 갱신해야 한다.
- realization formula나 profile-specific validation cap을 바꾸면 centerline/export/import 계약이 모두 흔들린다.

## Links
- [tx_rect_void_types.py](tx_rect_void_types.py.md)
- [tx_rect_void_centerline.py](tx_rect_void_centerline.py.md)
- [tx_rect_void_export.py](tx_rect_void_export.py.md)

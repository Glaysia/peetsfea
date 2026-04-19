---
title: tx_rect_void_spec.py
created: 2026-04-17 @ 09:09
updated: 2026-04-20 @ 15:05
tags:
  - tx-rect-void
---

# tx_rect_void_spec.py

## Source
- Path: `src/peetsfea/tx_rect_void_spec.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void_spec.py.md`
- Status: planned split target; source file is not created yet.
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Parent note: [[sdd/code/src/peetsfea/tx_rect_void.py]]

## 역할
- rect/void TOML parsing, range validation, sampled realization을 담당한다.

## 입력 / 출력
- 입력: TOML path, integer seed, role profile.
- 출력: `load_tx_rect_void_spec()`, `realize_tx_rect_void_spec()`, range/validation helpers.

## Canonical state
- module-level mutable state는 없다.
- canonical realized geometry inputs는 `SingleCoilRectVoidSpec`와 `RealizedSingleCoilRectVoid`다.
- void keepout geometry is no longer a TOML-owned input; realization uses fixed centered ratios `0.3 x 0.3`.

## Invariants / fail-fast
- `design.units`는 `mm`여야 한다.
- range table shape/count/type 위반은 즉시 raise한다.
- `terminal_stub_length_mm` runtime ownership은 derived `layer_gap_mm * 0.8` 규칙을 따른다.
- TOML `void_*` keys are unsupported and fail immediately instead of changing geometry.
- `turn_count` resolved value는 `1..6`이어야 하며 범위를 벗어나면 즉시 raise한다.
- `rx_single_coil.layer_count != 1`은 계속 fail-fast한다.

## 직접 의존
- [[sdd/code/src/peetsfea/tx_rect_void_types.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/tx_rect_void_centerline.py]]
- [[sdd/code/src/peetsfea/tx_rect_void_export.py]]
- compatibility facade `tx_rect_void.py`

## 관련 테스트
- [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]

## 변경 시 주의점
- parser shape를 바꾸면 `docs/tx-rect-void-step.md`와 type2 export path를 같이 갱신해야 한다.
- realization formula를 바꾸면 centerline/export/import 계약이 모두 흔들린다.

## Links
- [[sdd/code/src/peetsfea/tx_rect_void_types.py]]
- [[sdd/code/src/peetsfea/tx_rect_void_centerline.py]]
- [[sdd/code/src/peetsfea/tx_rect_void_export.py]]

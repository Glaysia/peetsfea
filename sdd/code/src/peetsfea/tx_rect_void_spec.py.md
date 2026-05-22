---
title: tx_rect_void_spec.py
created: 2026-04-17 @ 09:09
updated: 2026-05-03 @ 00:00
tags:
  - tx-rect-void
---

# tx_rect_void_spec.py

## Source
- Path: `src/peetsfea/tx_rect_void_spec.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void_spec.py.md`
- Status: planned split target; source file is not created yet.
- Primary graph owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)

## 역할
- rect/void TOML parsing, range validation, sampled quarter-turn realization을 담당한다.
- TX terminal stub 길이는 `tx_coil.terminal_stub_length_mm` 샘플 범위에서 단일 소유자로 선정한다.

## 입력 / 출력
- 입력: TOML path, integer seed, role profile.
- 출력: `load_tx_rect_void_spec()`, `realize_tx_rect_void_spec()`, range/validation helpers.

## Canonical state
- module-level mutable state는 없다.
- canonical realized geometry inputs는 `SingleCoilRectVoidSpec`와 `RealizedSingleCoilRectVoid`다.
- Winding ownership is the integer public range `tx_coil.turn_qcount`; effective turn count is `turn_qcount / 4.0` for pitch/trace/gap calculations.
- Terminal ownership is the integer public range `tx_coil.terminal_start`, with `0=A`, `1=B`, `2=C`, `3=D`, fixed `cw` direction, and derived end corner `(terminal_start + turn_qcount) % 4`.
- void keepout size is TOML-owned by canonical `tx_coil.void_factor`; the loader maps that one table into the existing internal `SingleCoilRangeSpec.void_usage_ratio` field as the single bridge location, and realization applies the selected value to both local X and local Y while keeping the void centered.
- `terminal_stub_length_mm`는 TOML `tx_coil.terminal_stub_length_mm` range에서 `_select_range_value`로 결정되며,
  `layer_gap_mm` 계산식(기존 `* 0.8`)은 사용하지 않는다.

## Invariants / fail-fast
- `design.units`는 `mm`여야 한다.
- range table shape/count/type 위반은 즉시 raise한다.
- `terminal_stub_length_mm` runtime ownership은 TOML range(`tx_coil.terminal_stub_length_mm`)에 기반한다.
- 선택된 `terminal_stub_length_mm`는 유한한 값이고 0보다 커야 하며, 아니면 즉시 실패한다.
- TOML legacy split/centered `void_*` keys, legacy `void_usage_ratio`, legacy `turn_count`, and raw `terminal_path` are unsupported and fail immediately instead of changing geometry.
- `void_factor` must realize to `0 < ratio < 1`; invalid candidates fail before geometry construction.
- `turn_qcount` resolved value must be in `1..SingleCoilProfile.max_turn_count * 4`; invalid quarter-turn counts fail before geometry construction.
- `terminal_start` resolved value must be in `0..3`; invalid terminal owners fail before derived metadata is built.
- `rx_single_coil.layer_count != 1`은 계속 fail-fast한다.

## 직접 의존
- [tx_rect_void_types.py](tx_rect_void_types.py.md)

## 이 파일을 쓰는 곳
- [tx_rect_void_centerline.py](tx_rect_void_centerline.py.md)
- [tx_rect_void_export.py](tx_rect_void_export.py.md)
- compatibility facade `tx_rect_void.py`

## 관련 테스트
- `tests/tx_rect_void/test_tx_rect_void.py`

## 변경 시 주의점
- parser shape를 바꾸면 active RX/reusable code notes와 type2 export path를 같이 갱신해야 한다.
- realization formula나 profile-specific validation cap을 바꾸면 centerline/export/import 계약이 모두 흔들린다.

## Graph links
- Primary owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)
- Parent facade: [tx_rect_void.py](tx_rect_void.py.md)
- Direct type contract: [tx_rect_void_types.py](tx_rect_void_types.py.md)
- Centerline handoff: [tx_rect_void_centerline.py](tx_rect_void_centerline.py.md)
- Export handoff: [tx_rect_void_export.py](tx_rect_void_export.py.md)

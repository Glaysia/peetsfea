---
title: type2_step_spec_modeled.py
created: 2026-04-20 @ 00:00
updated: 2026-05-06 @ 00:00
tags:
  - spec
  - modeled
---

# type2_step_spec_modeled.py

## Source
- Path: `src/peetsfea/type2_step_spec_modeled.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec_modeled.py.md`
- Status: active

## 역할
- type2 modeled-object parsing and validation helper다.
- 0.2.24 SDD 기준 active EM-ready path는 RX modeled roles다.
- `tx_inner_single_coil`은 geometry-only TX STEP body로 허용하고 active `tx_outer_single_coil` companion state는 제거됐다.

## 입력 / 출력
- 입력: modeled object TOML tables
- 출력: validated modeled object specs

## Canonical state
- RX single-coil and RX plate-stack parsing remain documented.
- Generic/legacy TX modeled roles are rejected at the active parser boundary during the reset.
- `tx_inner_single_coil` is parsed as an explicit rect-void inner TX coil placed by derived `tx_inner_region`; it also owns the TOML-controlled actual-region underlay stack fields.
- `tx_inner_single_coil` parses `x_position_ratio` as the inner coil local X placement owner.
- `tx_outer_terminal_path` and `tx_outer_x_position_ratio` are no longer active fields on `tx_inner_single_coil`; declaring either must fail as unsupported schema state.
- `tx_region` remains outside modeled parsing as future guide context.

## Invariants / fail-fast
- Unsupported modeled roles/fields fail during parse.
- `tx_single_coil`, `tx_rect_void_columns`, and `tx_plate_stack` fail before active runtime state is bound.
- `tx_inner_single_coil` accepts any canonical or fixed `underlay_repeat_count` value and enforces fixed positive actual-underlay PET/PSA/ferrite thickness fields while still rejecting `underlay_gap_mm` and `wall_parallel_stack_present`.
- `x_position_ratio` must realize only inclusive candidates between `0.0` and `1.0`.
- `tx_outer_terminal_path` and `tx_outer_x_position_ratio` must fail through unsupported-key validation, not by deriving a companion object.
- RxOnly must parse without requiring TX modeled roles.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_step_spec_types.py](type2_step_spec_types.py.md)
- [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)
- [0.2.24 Type2 TX Inner Actual Underlay Stack](../../../plans/0.2.24-type2-tx-inner-actual-underlay-stack.md)
- [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)

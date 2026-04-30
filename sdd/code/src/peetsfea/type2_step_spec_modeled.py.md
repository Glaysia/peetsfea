---
title: type2_step_spec_modeled.py
created: 2026-04-20 @ 00:00
updated: 2026-04-30 @ 00:00
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
- `tx_inner_single_coil`과 그 derived companion인 `tx_outer_single_coil`은 geometry-only TX STEP body로 허용한다.

## 입력 / 출력
- 입력: modeled object TOML tables
- 출력: validated modeled object specs

## Canonical state
- RX single-coil and RX plate-stack parsing remain documented.
- Generic/legacy TX modeled roles are rejected at the active parser boundary during the reset.
- `tx_inner_single_coil` is parsed as an explicit rect-void inner TX coil placed by derived `tx_inner_region`; it carries no underlay/ferrite fields.
- `tx_outer_single_coil` is derived from exactly one parsed inner TX coil and a fixed outer terminal selector; it must not introduce a second public sampled range table.
- The outer terminal selector is fixed TOML state, intended as `A_cw_to_a`, and must fail if it cannot be associated with exactly one inner TX modeled spec.
- `append_tx_outer_single_coil_companion_specs()` appends the concrete companion after all explicit modeled objects parse, sharing the inner coil RangeSpec objects and replacing only role/object/terminal identity.
- `tx_region` remains outside modeled parsing as future guide context.

## Invariants / fail-fast
- Unsupported modeled roles/fields fail during parse.
- `tx_single_coil`, `tx_rect_void_columns`, and `tx_plate_stack` fail before active runtime state is bound.
- `tx_inner_single_coil` requires fixed zero underlay repeat count and rejects TX underlay/wall-stack fields.
- `tx_outer_single_coil` must inherit the inner coil's fixed-zero underlay/no-wall-stack constraints and must fail on ambiguous/missing inner companion state.
- The selector is valid only as `[modeled_objects.tx_outer_terminal_path] value = "A_cw_to_a"` on the single `tx_inner_single_coil` object.
- RxOnly must parse without requiring TX modeled roles.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_step_spec_types.py](type2_step_spec_types.py.md)
- [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)

---
title: type2_step_spec_modeled.py
created: 2026-04-20 @ 00:00
updated: 2026-05-07 @ 00:00
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
- `tx_inner_single_coil.void_stack_present` is parsed as a required integer range and controls only YZ void-stack body presence.
- `tx_inner_single_coil` requires `x_position_ratio` only as fixed-zero compatibility source state; it is not an effective sampled placement owner.
- `tx_outer_terminal_path` and `tx_outer_x_position_ratio` are no longer active fields on `tx_inner_single_coil`; declaring either must fail as unsupported schema state.
- `tx_region` remains outside modeled parsing as future guide context.
- `tv_aluminum_plate` is parsed as a fixed, non-sampled modeled geometry block with required fields
  (`primitive=box`, `material=aluminum`, `model_state=true`, `source_non_model_object_id=tv`, `face=+x`, `thickness_mm>0`).

## Invariants / fail-fast
- Unsupported modeled roles/fields fail during parse.
- `tx_single_coil`, `tx_rect_void_columns`, and `tx_plate_stack` fail before active runtime state is bound.
- `tx_inner_single_coil` accepts the canonical underlay repeat sweep or a supported fixed `underlay_repeat_count`; fixed `1` is supported for coarsened active TX inner underlay stacks while the canonical sweep remains `(0, 2, 4, 6, 8)`.
- `tx_inner_single_coil` accepts canonical `void_stack_present = [true, 0, 1, 2]` or fixed singleton `0`/`1`; unsupported roles must not accept this field.
- `tx_inner_single_coil` enforces fixed positive actual-underlay PET/PSA/ferrite thickness fields while still rejecting `underlay_gap_mm` and `wall_parallel_stack_present`.
- TX inner `x_position_ratio` must be the fixed compatibility table `[false, 0.0, 0.0, 1]`; sampled or nonzero TX inner values fail at the modeled parser boundary.
- Usage ratios and position ratios accept mathematically inclusive `1.0` endpoints when range candidate generation produces a binary floating-point value within `1e-12` above `1.0`; values outside that tolerance still fail before specs are bound.
- `tx_outer_terminal_path` and `tx_outer_x_position_ratio` must fail through unsupported-key validation, not by deriving a companion object.
- RxOnly must parse without requiring TX modeled roles.
- `tv_aluminum_plate` role parsing fails immediately for any invalid source owner, face, primitive, material, model state, or thickness.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_step_spec_types.py](type2_step_spec_types.py.md)
- [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)
- [0.2.24 Type2 TX Inner Actual Underlay Stack](../../../plans/0.2.24-type2-tx-inner-actual-underlay-stack.md)
- [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)

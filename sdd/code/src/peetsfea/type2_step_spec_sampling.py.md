---
title: type2_step_spec_sampling.py
created: 2026-04-20 @ 00:00
updated: 2026-05-21 @ 00:00
tags:
  - spec
  - sampling
---

# type2_step_spec_sampling.py

## Source
- Path: `src/peetsfea/type2_step_spec_sampling.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec_sampling.py.md`
- Status: active

## 역할
- type2 source spec에서 sampled owner paths를 도출한다.
- 0.2.24 SDD 기준 RX owner paths and shared constraints are active.

## 입력 / 출력
- 입력: parsed type2 spec
- 출력: ordered sampled owner descriptors

## Canonical state
- Owner paths remain deterministic and source-order stable.
- `tx_region` is fixed guide context, not sampled TX geometry.
- `tx_inner_single_coil` underlay repeat count is resolved through the shared scalar resolver. Canonical sampled candidates remain `(0, 2, 4, 6, 8)`, while fixed supported candidates include `1` for the coarsened active TX inner stack.
- `void_stack_present` resolves independently from bottom underlay count with canonical candidates `(0, 1)` and fixed singleton support for TX inner and RX single-coil specs.
- Single-coil terminal start and quarter-turn count resolution use public owner paths `terminal_start` and `turn_qcount`; legacy `terminal_path` and `turn_count` are not resolver state for active type2 single-coil specs.
- `tx_inner_single_coil` underlay PET/PSA/ferrite thickness fields are separately resolved as fixed positive scalars.

## Invariants / fail-fast
- Unknown owner paths fail immediately.
- RxOnly sampled owner discovery must not require TX modeled paths.
- `tx_inner_single_coil` PET/PSA/ferrite underlay thickness resolver contracts reject non-fixed or non-positive values.
- `void_stack_present` resolver must reject non-integer, non-canonical, or unsupported singleton values immediately for supported single-coil roles.
- `terminal_start` resolver must reject values outside `0..3` with an explicit integer-candidate range error before applying canonical/fixed owner-shape validation.
- `turn_qcount` resolver must reject values outside `[1, profile.max_turn_count * 4]`.
- Underlay repeat count resolution rejects non-canonical multi-candidate ranges and fixed values outside the supported fixed candidate set.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_sampled.py](type2_sampled.py.md)
- [0.2.25 Type2 Quarter-Turn Single Coil](../../../plans/0.2.25-type2-quarter-turn-single-coil.md)

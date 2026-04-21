---
title: type2_step_spec_non_model.py
created: 2026-04-21 @ 00:00
updated: 2026-04-21 @ 00:00
tags:
  - step-export
  - spec
  - non-model
---

# type2_step_spec_non_model.py

## Source
- Path: `src/peetsfea/type2_step_spec_non_model.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec_non_model.py.md`
- Status: active

## 역할
- type2 TOML validation helpers that support the step-spec loader live here.
- This module owns the non-model spec dataclasses, schema-id checks, design-units checks, and simulation-policy parsing for type2 inputs.
- It keeps non-model parsing isolated from modeled-object parsing so `type2_step_spec.py` can delegate only the non-model boundary.
- shared dataclass and alias definitions are sourced from [[sdd/code/src/peetsfea/type2_step_spec_types.py]].

## 입력 / 출력
- 입력: raw type2 TOML tables and nested tables
- 출력: `RangeSpec`, non-model spec dataclasses, and `Type2SimulationPolicy`

## Canonical state
- `RangeSpec` is the canonical in-memory form for TOML range tables.
- `tx_region_actual` and `tx_region_actual_stack_space` are the only derived non-model object kinds accepted here.
- active type2 schema id remains `peetsfea.type2.step.v8`.
- type2 design units remain `mm`.

## Invariants / fail-fast
- required-key, table-shape, numeric-type, plane, and range-table checks raise immediately on malformed input.
- non-model range bounds are validated before any object dataclass is bound.
- `tx_region_actual` must have exact source/kind/id contract and supported sampled ranges.
- `tx_region_actual_stack_space` must keep the fixed 5.0 mm thickness contract and fixed tilt flag contract.
- simulation policy must expose a positive `radiation_margin_mm`.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec_types.py]]
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_non_model_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- [[sdd/code/src/peetsfea/type2_sampled.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]
- [[sdd/code/tests/type2/test_sample_type2_entry.py]]

## 변경 시 주의점
- Keep this module free of `type2_step_spec.py` imports to avoid import cycles.
- Preserve the exact fail-fast text and unsupported-key behavior for non-model object parsing.
- Any schema-id or design-units drift must be reflected in the type2 parser note and tests.
- Related boundary notes: [[sdd/code/src/peetsfea/type2_step_spec.py]], [[sdd/code/src/peetsfea/type2_non_model_scene.py]]

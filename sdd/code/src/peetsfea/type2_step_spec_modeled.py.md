---
title: type2_step_spec_modeled.py
created: 2026-04-21 @ 23:50
updated: 2026-04-21 @ 23:50
tags:
  - step-export
  - spec
---

# type2_step_spec_modeled.py

## Source
- Path: `src/peetsfea/type2_step_spec_modeled.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec_modeled.py.md`
- Status: active
- Related plan: [[sdd/plans/0.2.22-type2-step-spec-split]]

## 역할
- type2 modeled-object TOML parsing ownership을 가진다.
- single-coil, plate-stack, and `tx_rect_void_columns` modeled role validation, role/owner/plane helpers, and `tx_rect_void` TOML rendering bridge를 제공한다.
- shared dataclasses and role constants come from [[sdd/code/src/peetsfea/type2_step_spec_types.py]].
- generic table and range validators come from [[sdd/code/src/peetsfea/type2_step_spec_non_model.py]].

## 입력 / 출력
- 입력: raw modeled object tables, `seen_object_ids`, `non_model_specs_by_id`, modeled spec instances for render bridge
- 출력: parsed modeled spec objects, deterministic role helper results, rendered `tx_rect_void` TOML text

## Canonical state
- canonical modeled roles remain `tx_single_coil`, `rx_single_coil`, `tx_rect_void_columns`, `tx_plate_stack`, and `rx_plate_stack`.
- canonical object/owner/plane resolution stays role-driven and deterministic.
- `tx_rect_void` rendering preserves the canonical `void_usage_ratio` bridge contract.

## Invariants / fail-fast
- Unsupported modeled role, role/object_id mismatch, unsupported legacy keys, or invalid range tables fail immediately with context.
- `tx_rect_void_columns` parsing preserves the current supported field surface and rejects legacy column fields without fallback.
- rendering keeps the current canonical text layout and does not infer alternate TOML shapes.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_spec_sampling.py]]
- [[sdd/code/src/peetsfea/tx_rect_void.py]]
- [[sdd/code/src/peetsfea/type2_step_spec_types.py]]
- [[sdd/code/src/peetsfea/type2_step_spec_non_model.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]
- [[sdd/code/tests/type2/test_build_type2_entry.py]]
- [[sdd/code/tests/type2/test_sample_type2_entry.py]]

## 변경 시 주의점
- Do not import from `type2_step_spec.py` in a way that reintroduces a loader cycle beyond the existing facade bootstrap.
- Keep all fail-fast messages and canonical range acceptance unchanged.

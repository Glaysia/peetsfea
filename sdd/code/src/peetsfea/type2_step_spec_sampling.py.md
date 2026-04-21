---
title: type2_step_spec_sampling.py
created: 2026-04-21 @ 23:50
updated: 2026-04-21 @ 23:50
tags:
  - sampling
  - spec
---

# type2_step_spec_sampling.py

## Source
- Path: `src/peetsfea/type2_step_spec_sampling.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec_sampling.py.md`
- Status: active
- Related plan: [[sdd/plans/0.2.22-type2-step-spec-split]]

## 역할
- type2 sampled candidate extraction and seeded resolution ownership을 가진다.
- modeled and non-model sampled fields에 대해 deterministic candidate selection helper를 제공한다.
- shared dataclasses and range constants come from [[sdd/code/src/peetsfea/type2_step_spec_types.py]].
- generic table and range validators come from [[sdd/code/src/peetsfea/type2_step_spec_non_model.py]].

## 입력 / 출력
- 입력: `RangeSpec`, modeled/non-model spec instances, integer `seed`, logical range path
- 출력: realized scalar values for sampled owners and candidate tuples for validation

## Canonical state
- candidate generation is deterministic and derived only from the range spec.
- seeded selection uses the stable `seed` + `range_path` hash input.
- range helper output preserves the original canonical list semantics for integer and float ranges.

## Invariants / fail-fast
- Integer helpers only accept integer range specs; float helpers only accept non-integer range specs.
- Canonical candidate validation fails immediately when realized values drift outside the accepted owner contract.
- Non-model tilt resolution remains fixed and ignores `seed` while still validating the canonical candidate set.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_spec_modeled.py]]
- [[sdd/code/src/peetsfea/type2_step_spec_types.py]]
- [[sdd/code/src/peetsfea/type2_step_spec_non_model.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]
- [[sdd/code/tests/type2/test_type2_tx_plate_stack_array_export.py]]
- [[sdd/code/tests/type2/test_type2_tx_coil_count_spec_sampling.py]]

## 변경 시 주의점
- Do not add alternate sampling paths or best-effort fallback behavior.
- Keep seed hashing and candidate ordering identical to the existing facade implementation.

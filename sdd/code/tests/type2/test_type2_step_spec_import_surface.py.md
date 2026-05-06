---
title: test_type2_step_spec_import_surface.py
created: 2026-04-21 @ 17:45
updated: 2026-05-03 @ 00:00
tags:
  - tests
  - type2
  - import-surface
---

# test_type2_step_spec_import_surface.py

## Source
- Path: `tests/type2/test_type2_step_spec_import_surface.py`
- Code note path: `sdd/code/tests/type2/test_type2_step_spec_import_surface.py.md`
- Direct owner: [type2_step_spec.py](../../src/peetsfea/type2_step_spec.py.md)
- Primary graph owner: [type2-spec-boundary](../../../architecture/type2-spec-boundary.md)

## 역할
- verify `peetsfea.type2_step_spec` exposes the expected split-facing import surface via `__all__`
- verify chosen façade symbols still resolve to their owning split modules for role/object mapping, resolvers, and rendering helper paths
- verify output mode parsing exposes active `RxOnly`와 `TxRx` 계약의 fail-fast 동작을 검증한다

## 입력 / 출력
- 입력: runtime import of `peetsfea.type2_step_spec`
- 출력: assertions that `__all__` matches the expected symbol contract and selected symbols resolve from expected module origins

## Canonical state
- expected surface is frozen as a set of canonical public names (including parser, modeled/non-modeled types, resolvers, and helpers)
- `resolve_modeled_tx_inner_void_stack_present` is part of the facade resolver contract and must resolve from `type2_step_spec_sampling`
- import-path coverage includes `type2_step_spec_modeled` and `type2_step_spec_sampling` owner paths for split-owned functions
- failures should be fail-fast when the facade cannot import

## 불변식 / 실패-즉시
- `type2_step_spec.__all__` must exist and equal `test_type2_step_spec_import_surface._EXPECTED_PUBLIC_SURFACE`
- selected split-owned symbols must have deterministic `__module__` paths
- facade import errors are surfaced as hard assertion failures

## 협력 모듈
- [type2_step_spec.py](../../src/peetsfea/type2_step_spec.py.md)
- [type2_step_spec_modeled.py](../../src/peetsfea/type2_step_spec_modeled.py.md)
- [type2_step_spec_sampling.py](../../src/peetsfea/type2_step_spec_sampling.py.md)
- [type2_step_spec_types.py](../../src/peetsfea/type2_step_spec_types.py.md)
- [type2_step_spec_constraints.py](../../src/peetsfea/type2_step_spec_constraints.py.md)
- [type2_step_spec_non_model.py](../../src/peetsfea/type2_step_spec_non_model.py.md)

## 변경 시 주의점
- keep the expected surface list synchronized if split ownership intentionally changes
- do not relax to fallback assertions; missing or renamed public symbols must fail this test immediately

## Graph links
- Primary owner: [type2-spec-boundary](../../../architecture/type2-spec-boundary.md)
- Direct owner: [type2_step_spec.py](../../src/peetsfea/type2_step_spec.py.md)
- Direct parser contract: [outputs.py](../../src/peetsfea/spec/outputs.py.md)

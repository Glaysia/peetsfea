---
title: type2_step_spec.py
created: 2026-04-17 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - step-export
  - spec
---

# type2_step_spec.py

## Source
- Path: `src/peetsfea/type2_step_spec.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec.py.md`
- Status: active

## 역할
- active type2 TOML 입력을 통합 타입으로 조합하는 thin compatibility facade다.
- 파서/검증/샘플링의 실질 구현은 분리 모듈에 위임하고, facade는 공개 심벌 재노출과 `load_type2_step_spec` 경계를 유지한다.
- 0.2.24 SDD 기준 active modeled shape contract는 RX 경로만 문서화한다.
- TX geometry는 재설계 대상이므로 이 노트는 TX shape, TX port, TX output variable 생성을 명세하지 않는다.

## 입력 / 출력
- 입력: type2 TOML path
- 출력: parsed type2 step spec, parsed RX modeled/non-model objects, parsed `outputs`, parsed optional `constraints`

## Canonical state
- active schema facade는 RX single-coil / RX plate-stack 관련 parsing surface를 유지한다.
- `tx_region`은 future TX placement guide로만 보존한다.
- `outputs.mode = "RxOnly"`는 TX port를 만들지 않고 RX 변수만 요청하는 모드다.
- two-terminal output variable 이름은 [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)에서 shape-independent dormant contract로 보존한다.
- constraints parsing remains declarative and deterministic.

## Invariants / fail-fast
- unsupported schema keys fail during load; compatibility fallback is not allowed.
- RxOnly mode must not require a TX modeled object.
- RxOnly mode must not request TX report expressions.
- malformed constraints, duplicate rule ids, unknown owner paths, unsupported functions, and unsupported operators fail during type2 source loading or sampling preflight.

## Collaborators
- [type2_step_spec_non_model.py](type2_step_spec_non_model.py.md)
- [type2_step_spec_modeled.py](type2_step_spec_modeled.py.md)
- [type2_step_spec_sampling.py](type2_step_spec_sampling.py.md)
- [type2_step_spec_types.py](type2_step_spec_types.py.md)
- [type2_step_spec_constraints.py](type2_step_spec_constraints.py.md)
- [type2_sampled.py](type2_sampled.py.md)
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)

## 관련 테스트
- [test_generate_type2_step.py](../../tests/type2/test_generate_type2_step.py.md)
- [test_sample_type2_entry.py](../../tests/type2/test_sample_type2_entry.py.md)

## 변경 시 주의점
- TX shape fields must not be reintroduced through this facade while the 0.2.24 TX reset is active.
- Any active output mode change must update [type2-em-report-contract](../../../architecture/type2-em-report-contract.md).

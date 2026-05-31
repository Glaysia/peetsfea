---
title: type2_step_spec.py
created: 2026-04-17 @ 09:09
updated: 2026-05-21 @ 00:00
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
- 0.2.24 removal 기준 active modeled shape contract includes geometry-only TX inner and RX single coil, with no active TX outer companion materialization.

## 입력 / 출력
- 입력: type2 TOML path
- 출력: parsed type2 step spec, parsed RX modeled/non-model objects, parsed geometry-only TX inner objects, parsed `outputs`, parsed optional `constraints`

## Canonical state
- active schema facade는 RX single-coil / RX plate-stack 관련 parsing surface를 유지한다.
- `tx_region`은 future TX placement guide로만 보존한다.
- `NonModelTxRegionSpec`과 `NonModelTxReferenceLineSpec`은 facade에서 재노출되어 non-model scene/export가 concrete parser state를 공유한다.
- `ModeledTxInnerSingleCoilSpec`, `NonModelTxReferenceLineSpec`, and `NonModelTxRegionSpec` are included in the facade export list so scene, sampling, and tests can import the concrete active type2 parser types from one boundary.
- `tx_region_actual`과 `tx_region_actual_stack_space`는 active RxOnly 입력에서 제거된 TX 형상 파생 객체다.
- `outputs.mode = "RxOnly"`는 TX port를 만들지 않고 RX 변수만 요청하는 모드다.
- active modeled object parsing rejects generic/legacy TX modeled roles before downstream sampling/export can treat them as runtime state.
- `tx_inner_single_coil` is parsed as geometry-only modeled state for STEP export/import, and the facade re-exports the shared single-coil `void_stack_present` resolver as the public switch-sampling surface for TX inner and RX.
- Single-coil active schema fields exposed through this facade are `x_ratio`, `y_ratio`, `turn_qcount`, `void_factor`, `metal_fill_factor`, `terminal_start`, and `void_stack_present`; legacy `outer_x_usage_ratio`, `outer_y_usage_ratio`, `turn_count`, `void_usage_ratio`, and `terminal_path` fail during load.
- two-terminal output variable 이름은 [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)에서 shape-independent dormant contract로 보존한다.
- constraints parsing remains declarative and deterministic.

## Invariants / fail-fast
- unsupported schema keys fail during load; compatibility fallback is not allowed.
- RxOnly mode must not require a TX modeled object.
- RxOnly mode must reject generic/legacy TX modeled object roles.
- RxOnly mode may carry geometry-only `tx_inner_single_coil` through parsed/exported/imported state, but downstream setup must filter it out of mesh, ports, sources, and reports.
- `tx_outer_terminal_path`, `tx_outer_x_position_ratio`, and explicit/derived `tx_outer_single_coil` active modeled state must fail at the parser boundary.
- RxOnly mode must reject TX derived non-model object kinds instead of requiring or materializing them.
- RxOnly mode must not request TX report expressions.
- TX reference-line parsing must remain guide-only and must not activate generic/legacy TX modeled roles through this facade.
- malformed constraints, duplicate rule ids, unknown owner paths, unsupported functions, and unsupported operators fail during type2 source loading or sampling preflight.
- Facade re-exports the fixed modeled plate type `ModeledTvAluminumPlateSpec` so downstream entrypoints can reference the fixed role type uniformly with other modeled spec classes.
- Active modeled TOML parsing in this surface now accepts fixed `tv_aluminum_plate` modeled objects (object_id `tv_aluminum_plate`) through the modeled parser dependency without introducing sampled owner paths.
- Facade resolver exports include single-coil terminal-start, quarter-turn-count, and void-stack presence helpers so scene/sampling code can derive clockwise terminal metadata without TOML-owned terminal paths.

## Collaborators
- [type2_step_spec_non_model.py](type2_step_spec_non_model.py.md)
- [type2_step_spec_modeled.py](type2_step_spec_modeled.py.md)
- [type2_step_spec_sampling.py](type2_step_spec_sampling.py.md)
- [type2_step_spec_types.py](type2_step_spec_types.py.md)
- [type2_step_spec_constraints.py](type2_step_spec_constraints.py.md)
- [type2_sampled.py](type2_sampled.py.md)
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
- [0.2.25 Type2 Quarter-Turn Single Coil](../../../plans/0.2.25-type2-quarter-turn-single-coil.md)
- [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)

## 관련 테스트
- [test_generate_type2_step.py](../../tests/type2/test_generate_type2_step.py.md)
- [test_sample_type2_entry.py](../../tests/type2/test_sample_type2_entry.py.md)

## 변경 시 주의점
- TX shape fields must not be reintroduced through this facade while the 0.2.24 TX reset is active.
- Any active output mode change must update [type2-em-report-contract](../../../architecture/type2-em-report-contract.md).

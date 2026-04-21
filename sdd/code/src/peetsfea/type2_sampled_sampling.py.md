---
title: type2_sampled_sampling.py
created: 2026-04-21 @ 23:40
updated: 2026-04-21 @ 23:40
tags:
  - sampling
  - sdd
---

# type2_sampled_sampling.py

## Source
- Path: `src/peetsfea/type2_sampled_sampling.py`
- Code note path: `sdd/code/src/peetsfea/type2_sampled_sampling.py.md`
- Status: active
- Related feature plans: [[sdd/plans/0.2.22-type2-sampled-build-split]]

## 역할
- `type2_sampled`가 import해 사용하는 샘플링 코어를 소유한다.
- type2 sampled owner path 해석, deterministic sampled scalar 선택, constraint 파싱/평가를 담당한다.
- `tx_rect_void_columns` mode-aware sampled owner 계산과 inactive owner freeze 값을 제공한다.

## 입력 / 출력
- 입력: `Type2StepSpec`, source TOML table 일부, seed/retry/sampled owner path
- 출력: sampled owner path/value tuple, constraint rule list, validation/evaluation 결과

## Canonical state
- sampled owner canonical path는 `modeled_objects.<object_id>.<field>` / `non_model_objects.<object_id>.<field>`다.
- constraint retry 입력은 `seed` + `owner_path` + `retry_number` 결정 규칙을 따른다.

## Invariants / fail-fast
- unknown owner path, malformed constraint operand/function/operator는 즉시 raise한다.
- count==1 owner는 sampled owner set에서 제외하고 fixed scalar로만 해석한다.
- mode-aware tx columns owner 선택은 `connection_mode`와 realized coil count 제약을 유지한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_sampled.py]]
- [[sdd/code/src/peetsfea/type2_step_spec.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_sample_type2_entry.py]]
- [[sdd/code/tests/type2/test_type2_tx_coil_count_spec_sampling.py]]

## 변경 시 주의점
- public import contract는 `peetsfea.type2_sampled`에 남겨야 하며, 직접 외부 공개 경로 전환은 허용하지 않는다.

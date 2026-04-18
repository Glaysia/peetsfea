---
title: outputs.py
created: 2026-04-18 @ 13:45
updated: 2026-04-18 @ 18:46
tags:
  - spec
  - em
---

# outputs.py

## Source
- Path: `src/peetsfea/spec/outputs.py`
- Code note path: `sdd/code/src/peetsfea/spec/outputs.py.md`
- Status: active

## 역할
- active/shared EM report/output-variable contract parser를 제공한다.
- `[outputs]` TOML table과 retained step ledger top-level `outputs` object를 같은 fail-fast 규칙으로 검증한다.

## 입력 / 출력
- 입력:
  - TOML/JSON에서 읽은 mapping-like object
  - context string
- 출력:
  - validated `OutputsSpec`

## Canonical state
- module-level mutable state는 없다.
- canonical report contract는 `OutputsSpec` 한 shape로 고정한다.
- active type2와 retained step ledger는 같은 parser/validator를 공유한다.

## Invariants / fail-fast
- `outputs`는 exact required keys만 허용한다.
- `outputs.variables`는 non-empty array of tables여야 한다.
- variable name은 `^[A-Za-z][A-Za-z0-9_]*$`를 따라야 하고 unique여야 한다.
- empty string expression/name, unsupported key, missing key는 즉시 실패다.

## 직접 의존
- [[sdd/code/src/peetsfea/types/manifest.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- legacy parser를 active path의 hidden dependency로 다시 끌어오지 않는다.
- report contract drift는 type2 TOML, ledger handoff, setup-ready tests를 함께 갱신한다.

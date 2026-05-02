---
title: outputs.py
created: 2026-04-18 @ 13:45
updated: 2026-05-03 @ 00:00
tags:
  - spec
  - em
---

# outputs.py

## Source
- Path: `src/peetsfea/spec/outputs.py`
- Code note path: `sdd/code/src/peetsfea/spec/outputs.py.md`
- Status: active
- Primary graph owner: [type2-spec-boundary](../../../../architecture/type2-spec-boundary.md)

## 역할
- active/shared EM report/output-variable contract parser를 제공한다.
- `[outputs]` TOML table과 retained step ledger top-level `outputs` object를 같은 fail-fast 규칙으로 검증한다.
- active type2 output mode를 `RxOnly` 또는 `TxRx`로 명시적으로 지원한다.
- `TxRx`는 [type2-em-report-contract](../../../../architecture/type2-em-report-contract.md)의 two-terminal report variable contract를 따른다.
- `RxOnly` 계약은 TX 단말식 `TX_TML`과 TX 전용 변수명을 허용하지 않는다.
- 지원되지 않는 output mode/변수는 모두 즉시 실패한다.

## 입력 / 출력
- 입력:
  - TOML/JSON에서 읽은 mapping-like object
  - context string
- 출력:
  - validated `OutputsSpec`

## Canonical state
- module-level mutable state는 없다.
- canonical report contract는 `OutputsSpec` 한 shape로 고정한다.
- canonical active output mode 집합은 `{"RxOnly","TxRx"}`로 고정한다.
- 모드별 canonical 변수 집합은 [type2-em-report-contract](../../../../architecture/type2-em-report-contract.md)의 활성 계약과 일치한다.
- active type2와 retained step ledger는 같은 parser/validator를 공유한다.

## Invariants / fail-fast
- `outputs`는 exact required keys만 허용하며 `mode`는 `RxOnly` 또는 `TxRx`만 허용한다.
- `outputs.variables`는 non-empty array of tables여야 한다.
- variable name은 `^[A-Za-z][A-Za-z0-9_]*$`를 따라야 하고 unique여야 한다.
- 선택한 mode의 변수 집합 안에 이름이 있어야 한다.
- `RxOnly` expression은 `TX_TML`을 참조할 수 없다.
- empty string expression/name, unsupported key, missing key는 즉시 실패다.

## 직접 의존
- `src/peetsfea/types/manifest.py`

## 이 파일을 쓰는 곳
- `src/peetsfea/type2_step_spec.py`
- `src/peetsfea/backend/pyaedt/type2_step_import_ledger.py`

## 관련 테스트
- `tests/type2/test_generate_type2_step.py`
- `tests/backend_em/test_type2_step_setup_ready.py`

## 변경 시 주의점
- legacy parser를 active path의 hidden dependency로 다시 끌어오지 않는다.
- report contract drift는 type2 TOML, ledger handoff, setup-ready tests를 함께 갱신한다.

## Graph links
- Primary owner: [type2-spec-boundary](../../../../architecture/type2-spec-boundary.md)
- Exceptional contract: [type2-em-report-contract](../../../../architecture/type2-em-report-contract.md)
- Runtime handoff: [type2_step_import_ledger.py](../backend/pyaedt/type2_step_import_ledger.py.md)
- Representative verification: [test_type2_step_spec_import_surface.py](../../../tests/type2/test_type2_step_spec_import_surface.py.md)

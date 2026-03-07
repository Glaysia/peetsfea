# V0.2.11-00B Selection API Simplification And Refactor

## 상태/목적
- 상태: Planned
- 목적: resolver와 pipeline의 selection 경로를 LLM과 사람이 읽기 쉬운 구조로 단순화하고, path-dict 중심 API를 제거한다.
- 이번 문서는 내부 구조 정리 계획서이며 실제 리팩토링은 아직 수행하지 않는다.
- sampling ownership은 `00A`, replay/dataset public contract는 `00C`에서 정의한다.

## 반환 계약
- `SamplingContext = dict[path, value]`는 폐기한다.
- selection 결과는 `SelectionResult + SamplingLedger` 중심 반환 계약으로 재구성한다.
- downstream은 raw path-dict를 직접 다루지 않고 ledger를 통해 sampled value에 접근한다.
- `resolve_selection()` / `resolve_selection_with_context()`의 중복 계약은 단일 selection entrypoint로 정리한다.

## 구조 정리 원칙
- sampling, snapshot freeze, dataset export, repro-mode 판정을 작은 모듈로 분리한다.
- 동일 의미를 두 군데에서 조립하는 중복 코드를 제거한다.
- heuristic tree walk에 의존하는 path 처리 로직은 ledger owner map 기반으로 교체한다.
- dead path, direct path-dict access, 중복 selection assembly는 제거 대상이다.
- 공통 sampling API 밖 후보 생성과 선택 구현은 금지한다.

## 비범위
- canonical owner 분류 규칙 자체
- `dataset.toml` public contract
- `repro.toml` public contract
- ferrite 전용 수치/geometry 계약

## AGENTS/개발 규칙
- 새 샘플링 필드는 registry에 canonical owner로 1회만 등록한다.
- alias/derived path는 owner를 가질 수 없고 명시 선언해야 한다.
- 새 샘플링 필드를 추가하면 replay test, dimension audit, docs를 함께 갱신해야 한다.
- 공통 API 밖 샘플링 구현은 회귀 버그로 간주한다.

## 테스트 축
- selection result/ledger 반환 계약
- direct path-dict access regression
- shared sampling API 사용 강제
- resolver 중복 경로 제거 후 동일 결과 유지

## 수용 기준
- selection 관련 핵심 데이터 흐름이 `SelectionResult + SamplingLedger` 중심으로 설명되어 있다.
- 사람이 읽을 때 sampling ownership, selection assembly, snapshot/export 책임 경계가 명확하다.
- 새 기능 추가 시 어디에 샘플링 규칙을 넣어야 하는지 문서만 읽고 판단할 수 있다.

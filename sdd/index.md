# SDD Vault

이 공간은 `0.2.22+` 이후 변경을 위한 옵시디언 중심 설계 문서 허브다. 규칙 원문은 [[SDD]], 작업 규칙은 [[AGENTS]], 저장소 전역 fail-fast 규칙은 [[CODE_COMMANDMENTS]]를 본다.

## 시작점
- 정책: [[SDD]]
- 코드 대응 문서 허브: [[sdd/code/index]]
- 계획 허브: [[sdd/plans/index]]
- 아키텍처 허브: [[sdd/architecture/index]]
- 구조 허브: [[sdd/structure/index]]
- 다이어그램 허브: [[sdd/diagrams/index]]
- 템플릿:
  - [[sdd/templates/source-note]]
  - [[sdd/templates/plan-note]]
  - [[sdd/templates/architecture-note]]

## 현재 부트스트랩 문서
- 계획: [[sdd/plans/0.2.22-sdd-adoption]]
- 아키텍처: [[sdd/architecture/current-pipeline-sdd-view]]
- 구조: [[sdd/structure/sdd-vault-layout]]
- 구조도: [[sdd/diagrams/sample-build-flow]]
- 코드 예시:
  - [[sdd/code/src/peetsfea/spec/loader.py]]
  - [[sdd/code/entry/sample.py]]
  - [[sdd/code/tests/spec_resolver/test_sampling_registry.py]]

## 운영 루프
1. 큰 변경이면 먼저 [[sdd/plans/index]]에 계획을 남긴다.
2. 경계/흐름/레이어 변경이면 [[sdd/architecture/index]] 또는 [[sdd/structure/index]]를 갱신한다.
3. 같은 변경 안에서 대응 코드 노트를 만든다.
4. 필요한 경우 [[sdd/diagrams/index]]에 Mermaid 구조도를 추가한다.

## 경계
- 현재는 forward-only 도입이다.
- untouched 레거시 코드는 자동 백필하지 않는다.
- 새로 만들거나 실질 수정한 `src/`, `entry/`, `tests/` 코드부터 강제한다.

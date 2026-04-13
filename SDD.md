# SDD

이 저장소의 Software Design Documentation 운영 규칙은 이 문서가 정한다. 실무 기준점은 [[AGENTS]], [[CODE_COMMANDMENTS]], [[README]], [[docs/current-pipeline]], [[sdd/index]]다.

## 목적
- `0.2.22` 이후의 변경부터 코드와 설계 의도를 옵시디언에서 바로 추적 가능하게 만든다.
- 구현, 계획, 구조, 구조도, 테스트 의도가 분리되지 않게 유지한다.
- TOML spec SSOT를 유지하면서도, 구현 경계와 fail-fast 계약은 문서로 빠르게 찾을 수 있게 만든다.

## 적용 범위
- 적용 시작점은 `0.2.22`다.
- 기본 대상은 추적되는 Python 코드 `src/`, `entry/`, `tests/`다.
- 새로 만든 파일과 실질 수정된 파일은 SDD 의무 대상이다.
- 기존 레거시 파일은 untouched 상태에서는 소급하지 않는다.
- 생성 산출물, 캐시, 임시 파일, 과거 문서 자산은 기본 대상이 아니다.

## 일대일 대응 규칙
- 코드 대응 문서의 정규 경로는 `sdd/code/<repo-relative-code-path>.md`다.
- 예시:
  - `src/peetsfea/spec/loader.py` -> `[[sdd/code/src/peetsfea/spec/loader.py]]`
  - `entry/sample.py` -> `[[sdd/code/entry/sample.py]]`
  - `tests/spec_resolver/test_sampling_registry.py` -> `[[sdd/code/tests/spec_resolver/test_sampling_registry.py]]`
  - `src/peetsfea/spec/__init__.py` -> `sdd/code/src/peetsfea/spec/__init__.py.md`
- 신규 파일 생성과 실질 수정은 같은 변경 안에서 대응 문서를 만들거나 갱신해야 한다.
- 코드 대응 문서가 없는 신규/실질 수정 코드는 `0.2.22+` 기준의 완료 상태로 보지 않는다.

## 실질 수정 정의
- 아래는 실질 수정이다:
  - 로직 변경
  - 공개/내부 인터페이스 변경
  - runtime state 모델 변경
  - invariant, fail-fast, validation 계약 변경
  - 입력/출력 형식 변경
  - 데이터 흐름, ownership, registry 책임 변경
- 아래는 기본적으로 실질 수정이 아니다:
  - 포맷팅-only
  - comment-only
  - 순수 rename-only이면서 의미/행동이 바뀌지 않는 기계적 정리
- 애매하면 실질 수정으로 간주하고 문서를 같이 갱신한다.

## 코드 대응 문서 필수 섹션
각 코드 대응 문서는 아래를 반드시 포함한다.

- 정확한 소스 경로
- 이 파일의 단일 책임
- 주요 입력 / 출력
- canonical state 또는 state 없음 선언
- 핵심 invariant / fail-fast 포인트
- 직접 의존 모듈과 자신을 쓰는 대표 모듈/테스트
- 관련 테스트
- 변경 시 주의점
- 관련 `[[wikilink]]`

기본 시작점은 [[sdd/templates/source-note]]를 사용한다.

## 비코드 문서 체계
- 계획 문서: `[[sdd/plans/index]]`
  - 신규 기능, 큰 리팩터링, 장기 작업은 여기서 시작한다.
- 아키텍처 문서: `[[sdd/architecture/index]]`
  - 계층, 경계, 실행 흐름, 협력 구조가 바뀌면 갱신한다.
- 구조 문서: `[[sdd/structure/index]]`
  - 저장소 구조, 모듈 배치, 문서 배치, ownership map을 다룬다.
- 구조도/다이어그램 문서: `[[sdd/diagrams/index]]`
  - Mermaid를 허용한다.

큰 변경은 계획 문서에서 시작하고, 경계/흐름/계층이 바뀌면 아키텍처 또는 구조 문서를 추가한다.

## 링크 규칙
- 기본 링크 형식은 Obsidian `[[wikilink]]`다.
- 충돌을 피하려면 path-qualified 링크를 우선 사용한다.
- 코드 문서는 최소한 상위 허브, 관련 계획, 관련 아키텍처/구조도, 관련 테스트 문서로 링크해야 한다.
- 계획/구조 문서는 영향 받는 코드 대응 문서로 역링크해야 한다.
- 예시 연결:
  - [[sdd/index]]
  - [[sdd/plans/0.2.22-sdd-adoption]]
  - [[sdd/architecture/current-pipeline-sdd-view]]
  - [[sdd/structure/sdd-vault-layout]]
  - [[sdd/diagrams/sample-build-flow]]

## TOML spec SSOT와의 관계
- TOML spec은 기능/입력의 SSOT다.
- SDD는 구현 의도, 구조, 경계, fail-fast 계약, 변경 맥락의 문서 SSOT다.
- SDD는 TOML spec을 대체하지 않는다.
- Spec이 바뀌면 spec docs와 함께 관련 SDD 문서도 갱신해야 한다.

## 작업 체크리스트
- `src/`, `entry/`, `tests/`의 새 파일을 만들었는가: 대응 코드 노트를 만든다.
- 기존 파일을 실질 수정했는가: 대응 코드 노트를 갱신한다.
- 신규 기능 또는 큰 리팩터링인가: `[[sdd/plans/index]]` 아래 계획 문서를 만든다.
- 경계/흐름/레이어가 바뀌는가: `[[sdd/architecture/index]]`, `[[sdd/structure/index]]`, `[[sdd/diagrams/index]]` 중 필요한 문서를 만든다.
- 기존 전체 코드를 한 번에 백필하려고 하는가: 사용자가 명시적으로 요청하지 않았다면 하지 않는다.

## 부트스트랩 시작점
- 허브: [[sdd/index]]
- 코드 허브: [[sdd/code/index]]
- 예시 코드 노트:
  - [[sdd/code/src/peetsfea/spec/loader.py]]
  - [[sdd/code/entry/sample.py]]
  - [[sdd/code/tests/spec_resolver/test_sampling_registry.py]]
- 예시 비코드 문서:
  - [[sdd/plans/0.2.22-sdd-adoption]]
  - [[sdd/architecture/current-pipeline-sdd-view]]
  - [[sdd/structure/sdd-vault-layout]]
  - [[sdd/diagrams/sample-build-flow]]

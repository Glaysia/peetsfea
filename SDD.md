---
title: SDD
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 20:35
tags:
  - governance
---

# SDD

이 저장소의 Software Design Documentation 운영 규칙은 이 문서가 정한다. 실무 기준점은 `AGENTS.md`, `CODE_COMMANDMENTS.md`, `README.md`, `docs/current-pipeline.md`, 그리고 `sdd/sdd-index.md`다.

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
  - `src/peetsfea/spec/loader.py` -> `sdd/code/src/peetsfea/spec/loader.py.md`
  - `entry/sample.py` -> `sdd/code/entry/sample.py.md`
  - `tests/spec_resolver/test_sampling_registry.py` -> `sdd/code/tests/spec_resolver/test_sampling_registry.py.md`
  - `src/peetsfea/spec/__init__.py` -> `sdd/code/src/peetsfea/spec/__init__.py.md`
- 신규 파일 생성과 실질 수정은 같은 변경 안에서 대응 문서를 만들거나 갱신해야 한다.
- 코드 대응 문서가 없는 신규/실질 수정 코드는 `0.2.22+` 기준의 완료 상태로 보지 않는다.
- 실질 수정 대상 Python 파일은 가능하면 코드 편집 전에 대응 `sdd/code/...md` 노트를 먼저 만들거나 갱신한다. 같은 변경 안에서 맞추는 것만으로 충분하다고 간주하지 말고, 기본 작업 순서는 `SDD note 선행 -> 코드 수정 -> 테스트/검증`으로 유지한다.

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
- 관련 Markdown 상대경로 링크

기본 시작점은 [source-note](sdd/templates/source-note.md)를 사용한다.

## 비코드 문서 체계
- 계획 문서: `sdd/plans/`
  - 신규 기능, 큰 리팩터링, 장기 작업은 여기서 시작한다.
  - `src/`와 `entry/`의 tracked Python 파일이 800줄을 넘으면 strong guideline 기준의 분리 검토를 계획 문서에서 먼저 고정한다.
- 아키텍처 문서: `sdd/architecture/`
  - 계층, 경계, 실행 흐름, 협력 구조가 바뀌면 갱신한다.
- 구조 문서: `sdd/structure/`
  - 저장소 구조, 모듈 배치, 문서 배치, ownership map을 다룬다.
- 구조도/다이어그램 문서: `sdd/diagrams/`
  - Mermaid를 허용한다.
- 커밋 운영 문서: [commit-policy](sdd/structure/commit-policy.md)
  - SDD note와 코드 변경을 같은 논리 커밋으로 묶는 기준을 다룬다.

큰 변경은 계획 문서에서 시작하고, 경계/흐름/계층이 바뀌면 아키텍처 또는 구조 문서를 추가한다.

## 링크 규칙
- 기본 링크 형식은 실제 `.md` 파일을 가리키는 Markdown 상대경로 링크다.
- 충돌과 새 문서 생성을 피하려면 path-qualified 상대경로 링크를 우선 사용한다.
- 허용 링크 역할은 `parent hub`, `primary plan`, `primary architecture/structure`, `direct collaborator`, `direct verification`로 제한한다.
- backlog, split map, inventory, future work, historical context, broad relatedness는 plain text path나 inline code로 기록한다.
- 전역 정책 문서나 허브 문서를 모든 노트에 반복 링크하지 않는다.
- 세부 예산과 demotion 규칙은 [obsidian-link-policy](sdd/structure/obsidian-link-policy.md)를 따른다.

## TOML spec SSOT와의 관계
- TOML spec은 기능/입력의 SSOT다.
- SDD는 구현 의도, 구조, 경계, fail-fast 계약, 변경 맥락의 문서 SSOT다.
- SDD는 TOML spec을 대체하지 않는다.
- Spec이 바뀌면 spec docs와 함께 관련 SDD 문서도 갱신해야 한다.

## STEP artifact registry
- 추적되는 durable `.step` / `.stp` artifact를 생성하는 소스코드를 새로 만들거나 실질 수정하면 `notebooks/view_step_files.ipynb`의 `STEP_ARTIFACTS` registry를 같은 변경 안에서 갱신해야 한다.
- 각 추적 STEP artifact는 notebook 안에 전용 viewer cell을 가져야 한다.
- registry 항목은 artifact 경로, 생성 소스 경로, 사람이 읽을 label을 포함해야 한다.
- `run/`, `tmp/` 등에서 생성되는 non-tracked STEP artifact라도 repo의 정식 entrypoint, example script, test-supported workflow가 생성한다면 notebook에 generated artifact viewer cell을 추가해야 한다.
- generated artifact viewer cell은 생성 소스, 기본 output path, metadata path를 명시하고, 파일이 없을 때 실행할 repo-local 생성 명령을 포함해야 한다.
- SDD 대상 소스 파일이 STEP artifact를 생성하면 해당 코드 노트에 generator/output 관계와 viewer notebook 연결을 기록해야 한다.
- 일회성 scratch artifact, 예를 들어 수동 실험으로 만든 `tmp/` 아래 STEP 파일은 registry 대상이 아니다.

## 작업 체크리스트
- `src/`, `entry/`, `tests/`의 새 파일을 만들었는가: 대응 코드 노트를 만든다.
- 기존 파일을 실질 수정했는가: 대응 코드 노트를 갱신한다.
- 실질 수정 대상 Python 파일 작업을 시작하려는가: 가능하면 먼저 대응 코드 노트를 열어 책임, canonical state, invariants, fail-fast 변화부터 고정한 뒤 코드에 들어간다.
- 신규 기능 또는 큰 리팩터링인가: `sdd/plans/` 아래 계획 문서를 만든다.
- `src/` 또는 `entry/`의 tracked Python 파일이 800줄을 넘는가: strong guideline 기준의 분리 검토 대상이다. 예외는 문서화된 ownership boundary 판단으로만 남긴다.
- 위와 같은 분리에서 새 tracked Python 파일이 생기는가: 새 파일마다 대응 `sdd/code/<repo-relative-path>.md`를 같은 변경에 추가한다.
- 위와 같은 분리를 여러 에이전트가 구현할 예정인가: target source path별 `sdd/code/<repo-relative-path>.md`를 코드보다 먼저 만들어 구현 경계를 선행 고정한다.
- 위와 같은 분리 후 원본 파일이 남는가: 기존 `sdd/code/...md` 노트를 축소된 책임과 새 협력 관계에 맞게 갱신한다.
- 경계/흐름/레이어가 바뀌는가: `sdd/architecture/`, `sdd/structure/`, `sdd/diagrams/` 중 필요한 문서를 만든다.
- `tests/`는 ordinary SDD code-note coverage 대상이지만, 800줄 분리 기준에서는 제외한다.
- 추적되는 `.step` / `.stp` artifact를 생성하는가: `notebooks/view_step_files.ipynb`에 registry 항목과 전용 viewer cell을 추가하고 관련 코드 노트를 갱신한다.
- 정식 entrypoint/example workflow가 non-tracked `.step` / `.stp` artifact를 새로 생성하는가: `notebooks/view_step_files.ipynb`에 generated artifact viewer cell을 추가하고 생성 명령을 기록한다.
- 기존 전체 코드를 한 번에 백필하려고 하는가: 사용자가 명시적으로 요청하지 않았다면 하지 않는다.

## 부트스트랩 시작점
- 허브: [sdd-index](sdd/sdd-index.md)
- 코드 노트 index: `sdd/code/sdd-code-index.md`
- 계획 index: `sdd/plans/sdd-plans-index.md`
- 아키텍처 index: `sdd/architecture/sdd-architecture-index.md`
- 구조 index: `sdd/structure/sdd-structure-index.md`
- 다이어그램 index: `sdd/diagrams/sdd-diagrams-index.md`

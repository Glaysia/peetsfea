# SDD Vault Layout

이 문서는 SDD 볼트 구조와 경로 규칙을 설명한다. 상위 정책은 [[SDD]], 전체 허브는 [[sdd/sdd-index]], 현재 도입 계획은 [[sdd/plans/0.2.22-sdd-adoption]]다.

## Directory roles
- [[sdd/code/sdd-code-index]]: 코드와 일대일 대응되는 노트
- [[sdd/plans/sdd-plans-index]]: 기능/리팩터링 계획
- [[sdd/architecture/sdd-architecture-index]]: 계층, 경계, 흐름
- [[sdd/structure/sdd-structure-index]]: 저장소/문서 구조와 ownership map
- [[sdd/diagrams/sdd-diagrams-index]]: Mermaid 구조도와 흐름도
- 템플릿:
  - [[sdd/templates/source-note]]
  - [[sdd/templates/plan-note]]
  - [[sdd/templates/architecture-note]]

## Path mapping
- 코드 노트는 소스 경로를 그대로 미러링한다.
- 예시:
  - `src/peetsfea/spec/loader.py` -> [[sdd/code/src/peetsfea/spec/loader.py]]
  - `entry/sample.py` -> [[sdd/code/entry/sample.py]]
  - `tests/spec_resolver/test_sampling_registry.py` -> [[sdd/code/tests/spec_resolver/test_sampling_registry.py]]
- `__init__.py`도 예외 없이 같은 규칙을 따른다.

## Link style
- 기본 링크는 `[[wikilink]]`다.
- 가능한 한 path-qualified 링크를 써서 같은 이름 충돌을 피한다.
- 계획 문서와 구조 문서는 영향 받는 코드 노트로 역링크해야 한다.
- 코드 노트는 허브, 계획, 구조, 테스트 노트로 링크해야 한다.

## Adoption boundary
- 현재는 forward-only다.
- 기존 untouched 레거시 파일은 여기에서 일괄 백필하지 않는다.
- 새 파일 또는 실질 수정 파일이 생길 때마다 관련 노트를 추가한다.

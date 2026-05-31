---
title: SDD Vault Layout
created: 2026-04-17 @ 09:09
updated: 2026-06-01 @ 00:00
tags:
  - sdd
---

# SDD Vault Layout

이 문서는 SDD 볼트 구조와 경로 규칙을 설명한다. 현재 도입 계획은 [0.2.22-sdd-adoption](../plans/0.2.22-sdd-adoption.md)다.

## Directory roles
- [sdd-code-index](../code/sdd-code-index.md): 코드와 일대일 대응되는 노트
- [sdd-plans-index](../plans/sdd-plans-index.md): 기능/리팩터링 계획
- [sdd-architecture-index](../architecture/sdd-architecture-index.md): 계층, 경계, 흐름
- [sdd-structure-index](sdd-structure-index.md): 저장소/문서 구조와 ownership map
- [sdd-diagrams-index](../diagrams/sdd-diagrams-index.md): Mermaid 구조도와 흐름도
- 템플릿:
  - [source-note](../templates/source-note.md)
  - [plan-note](../templates/plan-note.md)
  - [architecture-note](../templates/architecture-note.md)

## Path mapping
- 코드 노트는 소스 경로를 그대로 미러링한다.
- 예시:
  - `src/peetsfea/minimal_spec.py` -> [minimal_spec.py](../code/src/peetsfea/minimal_spec.py.md)
  - `entry/sample.py` -> [sample.py](../code/entry/sample.py.md)
  - `tests/test_minimal_spec.py` -> [test_minimal_spec.py](../code/tests/test_minimal_spec.py.md)
- `__init__.py`도 예외 없이 같은 규칙을 따른다.

## Link style
- 기본 링크는 실제 `.md` 파일을 가리키는 Markdown 상대경로 링크다.
- 가능한 한 path-qualified 상대경로 링크를 써서 같은 이름 충돌과 새 문서 생성을 피한다.
- 전역 정책/허브 링크를 모든 노트에 반복하지 않는다.
- 계획 문서는 실제 영향 받는 코드 노트와 직접 선행/후속 계획만 링크한다.
- 코드 노트는 직접 계획, 협력 코드, 테스트, 구체적 관련 문서만 링크한다.

## Adoption boundary
- 현재는 forward-only다.
- 기존 untouched 레거시 파일은 여기에서 일괄 백필하지 않는다.
- 새 파일 또는 실질 수정 파일이 생길 때마다 관련 노트를 추가한다.

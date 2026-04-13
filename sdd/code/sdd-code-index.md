# Code Note Index

이 허브는 코드와 일대일 대응되는 노트의 진입점이다. 운영 규칙은 [[SDD]], 에이전트 강제 규칙은 [[AGENTS]], 전체 허브는 [[sdd/sdd-index]]를 본다.

## 경로 규칙
- 정규 규칙: `sdd/code/<repo-relative-code-path>.md`
- 예시:
  - `src/peetsfea/spec/loader.py` -> [[sdd/code/src/peetsfea/spec/loader.py]]
  - `entry/sample.py` -> [[sdd/code/entry/sample.py]]
  - `tests/spec_resolver/test_sampling_registry.py` -> [[sdd/code/tests/spec_resolver/test_sampling_registry.py]]
  - `src/peetsfea/spec/__init__.py` -> `sdd/code/src/peetsfea/spec/__init__.py.md`

## 필수 내용
- source path
- single responsibility
- inputs / outputs
- canonical state
- invariant / fail-fast
- collaborators
- related tests
- change hazards
- 관련 `[[wikilink]]`

템플릿 시작점은 [[sdd/templates/source-note]]다.

## 예시 노트
- [[sdd/code/src/peetsfea/spec/loader.py]]
- [[sdd/code/entry/sample.py]]
- [[sdd/code/tests/spec_resolver/test_sampling_registry.py]]
- [[sdd/code/src/peetsfea/tx_rect_void.py]]
- [[sdd/code/entry/export_tx_rect_void_step.py]]
- [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]

## 운영 메모
- 이 인덱스는 전체 레포 백필 목록이 아니다.
- `0.2.22+` 이후 새로 만들거나 실질 수정하는 파일부터 대응 노트를 늘린다.

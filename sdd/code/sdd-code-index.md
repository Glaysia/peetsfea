# Code Note Index

이 허브는 코드와 일대일 대응되는 노트의 진입점이다. 상위 허브는 [[sdd/sdd-index]]다.

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
- 관련 Obsidian wikilink

템플릿 시작점은 [[sdd/templates/source-note]]다.

## 현재 노트
- [[sdd/code/entry/export_tx_rect_void_step.py.md]]
- [[sdd/code/entry/import_type2_step.py.md]]
- [[sdd/code/entry/sample.py.md]]
- [[sdd/code/entry/generate_non_model_step.py.md]]
- [[sdd/code/entry/generate_type2_step.py.md]]
- [[sdd/code/entry/import_non_model_step_to_hfss.py.md]]
- [[sdd/code/entry/import_tx_rect_void_step_to_hfss.py.md]]
- [[sdd/code/src/peetsfea/aedt/protocols.py.md]]
- [[sdd/code/src/peetsfea/aedt/wrappers.py.md]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py.md]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py.md]]
- [[sdd/code/src/peetsfea/spec/loader.py.md]]
- [[sdd/code/src/peetsfea/tx_rect_void.py.md]]
- [[sdd/code/tests/backend_em/test_type2_step_import_smoke.py.md]]
- [[sdd/code/tests/backend_em/test_tx_rect_void_step_import_smoke.py.md]]
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py.md]]
- [[sdd/code/tests/type2/test_generate_type2_step.py.md]]
- [[sdd/code/tests/type2/test_import_type2_step_entry.py.md]]
- [[sdd/code/tests/spec_resolver/test_sampling_registry.py.md]]
- [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py.md]]

## 운영 메모
- 이 인덱스는 전체 레포 백필 목록이 아니다.
- `0.2.22+` 이후 새로 만들거나 실질 수정하는 파일부터 대응 노트를 늘린다.

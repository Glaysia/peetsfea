---
title: Code Note Index
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - sdd
---

# Code Note Index

이 허브는 코드와 일대일 대응되는 노트의 진입점이다. 상위 허브는 [[sdd/sdd-index]]다.

## 경로 규칙
- 정규 규칙: `sdd/code/<repo-relative-code-path>.md`
- 예시:
  - `src/peetsfea/spec/loader.py` -> `sdd/code/src/peetsfea/spec/loader.py.md`
  - `entry/legacy/type1/sample.py` -> `sdd/code/entry/legacy/type1/sample.py.md`
  - `tests/legacy/type1/spec_resolver/test_sampling_registry.py` -> `sdd/code/tests/spec_resolver/test_sampling_registry.py.md`
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
Entry note inventory:
- `sdd/code/entry/export_tx_rect_void_step.py.md`
- `sdd/code/entry/import_type2_step.py.md`
- `sdd/code/entry/build.py.md`
- `sdd/code/entry/sample.py.md`
- `sdd/code/entry/generate_non_model_step.py.md`
- `sdd/code/entry/generate_type2_step.py.md`
- `sdd/code/entry/import_non_model_step_to_hfss.py.md`
- `sdd/code/entry/import_tx_rect_void_step_to_hfss.py.md`

Src note inventory:
- `sdd/code/src/peetsfea/aedt/protocols.py.md`
- `sdd/code/src/peetsfea/aedt/wrappers.py.md`
- `sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py.md`
- `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py.md`
- `sdd/code/src/peetsfea/spec/loader.py.md`
- `sdd/code/src/peetsfea/spec/toml_render.py.md`
- `sdd/code/src/peetsfea/type2_runtime.py.md`
- `sdd/code/src/peetsfea/type2_sampled.py.md`
- `sdd/code/src/peetsfea/tx_rect_void.py.md`

Test note inventory:
- `sdd/code/tests/backend_em/test_type2_step_import_smoke.py.md`
- `sdd/code/tests/backend_em/test_tx_rect_void_step_import_smoke.py.md`
- `sdd/code/tests/backend_em/test_type2_step_import_pipeline.py.md`
- `sdd/code/tests/backend_em/test_type2_step_setup_ready.py.md`
- `sdd/code/tests/type2/test_build_type2_entry.py.md`
- `sdd/code/tests/type2/test_generate_type2_step.py.md`
- `sdd/code/tests/type2/test_import_type2_step_entry.py.md`
- `sdd/code/tests/type2/test_sample_type2_entry.py.md`
- `sdd/code/tests/spec_resolver/test_sampling_registry.py.md`
- `sdd/code/tests/tx_rect_void/test_tx_rect_void.py.md`

## Planned Split Notes
- Active size-driven split planning may pre-create `sdd/code/...md` notes before the source files land, so implementing agents can code against fixed boundaries.
- Current pre-created split notes follow [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]:
  - `sdd/code/src/peetsfea/tx_rect_void_types.py.md`
  - `sdd/code/src/peetsfea/tx_rect_void_spec.py.md`
  - `sdd/code/src/peetsfea/tx_rect_void_centerline.py.md`
  - `sdd/code/src/peetsfea/tx_rect_void_export.py.md`
- `sdd/code/src/peetsfea/type2_step_spec.py.md`
- `sdd/code/src/peetsfea/type2_step_scene.py.md`
- `sdd/code/src/peetsfea/type2_step_ledger.py.md`
- `sdd/code/src/peetsfea/type2_step_export.py.md`
- `sdd/code/src/peetsfea/type2_rx_plate_stack.py.md`
- `sdd/code/src/peetsfea/type2_tx_plate_stack_array.py.md`
  - `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py.md`
  - `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py.md`
  - `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py.md`
  - `sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_path.py.md`
  - `sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_placement.py.md`
  - `sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_build.py.md`
  - `sdd/code/src/peetsfea/aedt/wrappers_common.py.md`
  - `sdd/code/src/peetsfea/aedt/wrappers_modules.py.md`
  - `sdd/code/src/peetsfea/aedt/wrappers_hfss.py.md`
  - `sdd/code/src/peetsfea/aedt/proxies_base.py.md`
  - `sdd/code/src/peetsfea/aedt/proxies_ops.py.md`
  - `sdd/code/src/peetsfea/aedt/proxies_inspect.py.md`
- Planned TX array test notes:
  - `sdd/code/tests/type2/test_type2_tx_coil_count_spec_sampling.py.md`
  - `sdd/code/tests/type2/test_type2_tx_plate_stack_array_export.py.md`
  - `sdd/code/tests/backend_em/test_type2_tx_plate_stack_array_import.py.md`

## 운영 메모
- 이 인덱스는 전체 레포 백필 목록이 아니다.
- `0.2.22+` 이후 새로 만들거나 실질 수정하는 파일부터 대응 노트를 늘린다.
- 아직 source file이 없는 pre-created split note는 active plan이 가리키는 경우에만 허용한다.

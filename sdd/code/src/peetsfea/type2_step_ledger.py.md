---
title: type2_step_ledger.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - type2
  - step-export
---

# type2_step_ledger.py

## Source
- Path: `src/peetsfea/type2_step_ledger.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_ledger.py.md`
- Status: planned split target; source file is not created yet.
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Parent note: [[sdd/code/entry/generate_type2_step.py]]

## 역할
- type2 scene export 결과를 retained metadata ledger와 per-modeled metadata JSON으로 직렬화한다.

## 입력 / 출력
- 입력: parsed specs, scene assembly output, modeled export metadata, output directory
- 출력: `type2_step_ledger.json`, modeled source metadata JSON, canonical coordinate payloads

## Canonical state
- canonical artifact handoff는 top-level ledger의 `scene_step_path`와 object-level metadata entries다.
- canonical retained boundary-policy field는 top-level `em_policy`다.
- boundary handoff contract는 `type2_step_ledger.em_policy.radiation_margin_mm`를 기준으로 문서화한다.

## Invariants / fail-fast
- modeled object metadata는 expected body names/count, canonical coordinates, terminal metadata를 모두 가져야 한다.
- canonical ledger schema docs는 top-level `scene_step_path`, `em_policy`, `non_model_objects`, `modeled_objects`를 함께 유지한다.
- ledger shape mismatch or missing owner/member metadata is a hard failure.

## 직접 의존
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- downstream import path documented by [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]
- [[sdd/code/tests/type2/test_import_type2_step_entry.py]]

## 변경 시 주의점
- ledger shape를 바꾸면 import adapter, tests, notebooks를 같이 바꿔야 한다.
- canonical docs는 policy key를 `em_policy`로 고정한다. importer가 `import_time_policy`를 기대하는 현재 runtime mismatch는 문서 fallback이 아니라 후속 코드 수정으로 해소해야 한다.
- scene writing concern을 여기로 다시 끌어오지 않는다.

## Links
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

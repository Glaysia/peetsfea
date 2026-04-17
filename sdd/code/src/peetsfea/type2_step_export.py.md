---
title: type2_step_export.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - type2
  - step-export
---

# type2_step_export.py

## Source
- Path: `src/peetsfea/type2_step_export.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_export.py.md`
- Status: planned split target; source file is not created yet.
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Parent note: [[sdd/code/entry/generate_type2_step.py]]

## 역할
- type2 scene export orchestration public API를 제공하고 entry CLI가 호출하는 thin library surface를 담당한다.

## 입력 / 출력
- 입력: TOML path, output dir, ledger path, seed
- 출력: exported scene artifacts and typed ledger result

## Canonical state
- module-level mutable state는 없다.
- canonical orchestration surface는 `export_type2_step_artifacts()` 한곳에 모은다.

## Invariants / fail-fast
- cleanup, spec parse, scene build, ledger write 순서가 deterministic해야 한다.
- entry CLI는 내부 helper에 직접 접근하지 않고 이 facade를 통해서만 export한다.

## 직접 의존
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/entry/generate_type2_step.py]]
- [[sdd/code/entry/refresh_type2_step_viewer_artifacts.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]
- [[sdd/code/tests/type2/test_refresh_type2_step_viewer_artifacts.py]]

## 변경 시 주의점
- CLI parsing을 다시 library orchestration에 섞지 않는다.
- tx-only convenience export와 full scene export의 public entrypoint를 명시적으로 분리한다.

## Links
- [[sdd/code/entry/generate_type2_step.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]

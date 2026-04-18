---
title: build.py
created: 2026-04-18 @ 23:10
updated: 2026-04-19 @ 11:05
tags:
  - build
  - em
---

# build.py

## Source
- Path: `entry/build.py`
- Code note path: `sdd/code/entry/build.py.md`
- Related plan: [[sdd/plans/0.2.23-type2-sampled-build-split]]
- Collaborators:
  - [[sdd/code/entry/sample.py]]
  - [[sdd/code/src/peetsfea/type2_runtime.py]]
  - [[sdd/code/src/peetsfea/type2_sampled.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]

## 역할
- active type2 AEDT replay owner entrypoint다.
- canonical manifest를 읽고 existing STEP ledger를 재사용하거나 missing STEP을 같은 worker에서 생성한 뒤 `.aedt`를 만든다.
- build worker count는 manifest config가 owner다.

## 입력 / 출력
- 입력:
  - `run/sampled/type2/manifest.json`
- 출력:
  - optional `run/sampled/type2/<design_id>/type2_scene.step`
  - optional `run/sampled/type2/<design_id>/type2_step_ledger.json`
  - `run/sampled/type2/<design_id>/type2_imported_ledger.json`
  - `run/sampled/type2/<design_id>/<design_id>.aedt`

## Canonical state
- `entry.sample.MANIFEST_PATH`가 default manifest path다.
- manifest top-level `config.aedt_builder_n`이 AEDT build 병렬도 source-of-truth다.
- build-side STEP ownership policy는 `missing-only`다.

## Invariants / fail-fast
- manifest는 object shape여야 하며 `config`, `entries`를 모두 가져야 한다.
- existing `step_ledger_path`가 있으면 referenced scene STEP까지 검증한 뒤 runner로 넘겨야 한다.
- existing `step_ledger_path`가 없으면 same-worker STEP export 후 AEDT build로 이어져야 한다.
- existing ledger가 깨졌으면 rebuild fallback 없이 즉시 실패해야 한다.
- build는 sampled metadata-derived design variables만 runner에 전달한다.

## 직접 의존
- `entry.sample`
- `peetsfea.type2_runtime`
- `peetsfea.type2_sampled`
- `peetsfea.backend.pyaedt.type2_step_setup_ready`

## 이 파일을 쓰는 곳
- Human/agent active build entrypoint.

## 관련 테스트
- [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 변경 시 주의점
- manifest config ownership을 build local constant로 되돌리지 않는다.
- missing-only STEP policy를 whole-stage STEP-first policy로 되돌리지 않는다.

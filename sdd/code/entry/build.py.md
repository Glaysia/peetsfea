---
title: build.py
created: 2026-04-18 @ 23:10
updated: 2026-04-20 @ 12:24
tags:
  - build
  - em
---

# build.py

## Source
- Path: `entry/build.py`
- Code note path: `sdd/code/entry/build.py.md`
- Status: active
- Related feature plans: [[sdd/plans/0.2.22-type2-sampled-build-split]], [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- manifest 기반 active type2 build entrypoint다.
- sampled outputs를 role-aware runtime selection으로 넘겨 `.aedt` generation을 수행한다.
- type2 GUI debug build의 CLI owner다. 노트북은 build orchestration을 직접 하지 않고 이 entrypoint를 subprocess로 호출한다.

## 입력 / 출력
- 입력: manifest path, optional CLI debug flag, debug 대상 design id
- 출력: built artifact summaries, optional generated STEP/ledger/AEDT artifacts

## Canonical state
- default manifest path는 `entry.sample.MANIFEST_PATH`다.
- `config.aedt_builder_n`이 build parallelism source of truth다.
- exact coil pair와 exact plate-stack pair 모두 default build path에서 setup-ready facade로 간다.
- plate-stack pair는 setup-ready facade 내부에서 full-EM-ready setup branch를 사용한다.
- debug CLI mode는 manifest parallelism과 entry count를 무시하고 명시된 `design_id` 1개만 `jobs=1`로 실행한다.
- debug CLI mode는 GUI-visible HFSS session을 만들고 attached-session setup-ready path를 사용한다.
- debug CLI mode의 AEDT retention contract는 `release_desktop(close_projects=False, close_on_exit=False)`다.

## Invariants / fail-fast
- missing-only STEP policy를 유지한다.
- existing ledger corruption은 rebuild fallback 없이 실패한다.
- custom runner를 caller가 명시하면 build entry는 그 runner override를 그대로 존중한다.
- debug CLI mode에서 `design_id`가 비어 있거나 manifest에 없으면 다른 entry로 대체하지 않고 실패한다.
- debug GUI path는 import-only helper로 강등하지 않는다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_runtime.py]]
- [[sdd/code/src/peetsfea/type2_sampled.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]
- [[sdd/code/entry/import_type2_step.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 변경 시 주의점
- default build routing과 explicit runner override semantics를 섞지 않는다.
- plate-stack branch를 축소된 partial-setup contract로 되돌리지 않는다.
- notebook convenience flow가 이 파일의 debug orchestration ownership을 다시 가져가지 않게 유지한다.

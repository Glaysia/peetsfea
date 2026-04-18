---
title: build.py
created: 2026-04-18 @ 23:10
updated: 2026-04-20 @ 00:42
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

## 입력 / 출력
- 입력: manifest path
- 출력: built artifact summaries, optional generated STEP/ledger/AEDT artifacts

## Canonical state
- default manifest path는 `entry.sample.MANIFEST_PATH`다.
- `config.aedt_builder_n`이 build parallelism source of truth다.
- exact coil pair와 exact plate-stack pair 모두 default build path에서 setup-ready facade로 간다.
- plate-stack pair는 setup-ready facade 내부에서 port-ready branch를 사용한다.

## Invariants / fail-fast
- missing-only STEP policy를 유지한다.
- existing ledger corruption은 rebuild fallback 없이 실패한다.
- custom runner를 caller가 명시하면 build entry는 그 runner override를 그대로 존중한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_runtime.py]]
- [[sdd/code/src/peetsfea/type2_sampled.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]
- [[sdd/code/entry/import_type2_step.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 변경 시 주의점
- default build routing과 explicit runner override semantics를 섞지 않는다.
- plate-stack branch를 full setup path로 넓히지 않고 port-ready contract를 유지한다.

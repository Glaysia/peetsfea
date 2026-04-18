---
title: build.py
created: 2026-04-18 @ 23:10
updated: 2026-04-19 @ 21:42
tags:
  - build
  - em
---

# build.py

## Source
- Path: `entry/build.py`
- Code note path: `sdd/code/entry/build.py.md`
- Status: active
- Related feature plans: [[sdd/plans/0.2.23-type2-sampled-build-split]], [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- manifest 기반 active type2 build entrypoint다.
- sampled outputs를 setup-ready runner로 전달하는 thin entry layer를 유지한다.

## 입력 / 출력
- 입력: manifest path
- 출력: built artifact summaries, optional generated STEP/ledger/AEDT artifacts

## Canonical state
- default manifest path는 `entry.sample.MANIFEST_PATH`다.
- `config.aedt_builder_n`이 build parallelism source of truth다.
- active plate-stack manifest를 build로 태우면 runner의 explicit unsupported error가 surface로 전파된다.

## Invariants / fail-fast
- build entry는 import-only로 자동 갈라지지 않는다.
- missing-only STEP policy를 유지한다.
- existing ledger corruption은 rebuild fallback 없이 실패한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_runtime.py]]
- [[sdd/code/src/peetsfea/type2_sampled.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]
- [[sdd/code/entry/import_type2_step.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 변경 시 주의점
- active plate-stack geometry-view path를 여기의 EM build semantics 안에 숨기지 않는다.

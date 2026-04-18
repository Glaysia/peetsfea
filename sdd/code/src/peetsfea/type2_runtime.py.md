---
title: type2_runtime.py
created: 2026-04-18 @ 23:10
updated: 2026-04-19 @ 21:42
tags:
  - build
  - runtime
---

# type2_runtime.py

## Source
- Path: `src/peetsfea/type2_runtime.py`
- Code note path: `sdd/code/src/peetsfea/type2_runtime.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- sampled manifest 기준 export/build orchestration helper를 제공한다.

## 입력 / 출력
- 입력: prepared builds, exporter, runner
- 출력: stepped artifacts, built artifacts

## Canonical state
- default build runner selection은 role-aware다.
- coil pair manifest는 setup-ready facade를 쓴다.
- active plate-stack manifest는 import-only facade로 자동 전환되어 `.aedt` geometry-view artifact를 만든다.

## Invariants / fail-fast
- existing broken ledger는 rebuild fallback 없이 실패한다.
- sampled metadata-derived design variables는 setup-ready path에만 전달한다.
- custom runner를 강제로 주면 그 runner contract를 유지하고, unsupported plate roles는 여전히 fail-fast 한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_sampled.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]
- [[sdd/code/entry/build.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 변경 시 주의점
- role-aware runner selection과 direct import entry semantics를 서로 엇갈리게 만들지 않는다.
- setup-ready path에 import-only parameter shape를 억지로 밀어 넣지 않는다.

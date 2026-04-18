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
- default build runner는 setup-ready facade다.
- active plate-stack example에서는 setup-ready runner가 explicit unsupported error를 내는 것이 canonical behavior다.
- import-only geometry viewing은 separate import entry/pipeline의 책임이다.

## Invariants / fail-fast
- build path는 import-only로 자동 우회하지 않는다.
- existing broken ledger는 rebuild fallback 없이 실패한다.
- sampled metadata-derived design variables만 runner에 전달한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_sampled.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]
- [[sdd/code/entry/build.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 변경 시 주의점
- active plate-stack runtime policy를 hidden fallback으로 가리지 않는다.
- geometry-view import-only path와 EM build path를 같은 entrypoint 안에서 섞지 않는다.

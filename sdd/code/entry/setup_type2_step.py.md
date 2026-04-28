---
title: setup_type2_step.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - hfss-import
  - em
---

# setup_type2_step.py

## Source
- Path: `entry/setup_type2_step.py`
- Code note path: `sdd/code/entry/setup_type2_step.py.md`
- Runtime module: [type2_step_setup_ready.py](../src/peetsfea/backend/pyaedt/type2_step_setup_ready.py.md)

## 역할
- type2 export + full setup-ready runtime을 연결하는 CLI entrypoint다.
- import-only entry와 분리된 owner surface로 mesh, boundary, ports, analysis, validation까지 이어지는 helper를 제공한다.
- active sampled/build operator flow에서는 lower-level helper로 남고, direct human/agent invocation은 opt-in이다.

## 입력 / 출력
- 기본 입력:
  - `examples/type2_fixed.toml`
  - `entry/generate_type2_step.py`
- 기본 출력:
  - `run/aedt/type2_step_setup_ready/type2_setup_ready.aedt`
  - `run/aedt/type2_step_import/type2_imported_ledger.json`

## Canonical state
- module-level mutable state는 없다.
- code-owned orchestration surface는 `export_and_setup_type2_step(...)` / `export_and_setup_type2_step_into_hfss(...)`다.
- `--ledger` mode도 source TOML을 다시 읽지 않고 retained step ledger `outputs`로 setup-ready report를 재생한다.

## Invariants / fail-fast
- default mode는 exporter 후 setup-ready runtime을 호출한다.
- `--ledger` mode는 exporter를 건너뛰고 setup-ready runtime만 호출한다.
- sampled/build notebook은 이 entry를 직접 호출하지 않는다.

## 직접 의존
- [generate_type2_step.py](generate_type2_step.py.md)
- [type2_step_setup_ready.py](../src/peetsfea/backend/pyaedt/type2_step_setup_ready.py.md)

## 이 파일을 쓰는 곳
- Human/agent opt-in type2 setup-ready validation entrypoint.
- [build.py](build.py.md)가 사용하는 lower-level runtime surface.

## 관련 테스트
- [test_setup_type2_step_entry.py](../tests/type2/test_setup_type2_step_entry.py.md)

## 변경 시 주의점
- import-only entry [import_type2_step.py](import_type2_step.py.md)를 full setup-ready owner로 다시 합치지 않는다.

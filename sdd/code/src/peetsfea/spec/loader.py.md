---
title: src/peetsfea/spec/loader.py
created: 2026-04-17 @ 09:09
updated: 2026-05-03 @ 00:00
tags:
  - sdd
---

# src/peetsfea/spec/loader.py

- Source path: `src/peetsfea/spec/loader.py`
- Code note path: `sdd/code/src/peetsfea/spec/loader.py.md`
- Primary graph owner: [type2-spec-boundary](../../../../architecture/type2-spec-boundary.md)

## 역할
- TOML 파일을 UTF-8 bytes에서 fail-fast로 로드하고, parsed table과 raw bytes를 함께 반환한다.
- downstream 코드가 required table/string shape를 빠르게 강제할 수 있게 최소 validator를 제공한다.

## 입력 / 출력
- `load_toml_bytes(path: Path) -> tuple[TOMLTable, bytes]`
- `require_table(value: object, name: str) -> TOMLTable`
- `require_str(value: object, name: str) -> str`

## Canonical state
- module-level mutable state는 없다.
- canonical output은 `parsed TOML table + original raw bytes` 쌍이다.

## Invariants / fail-fast
- path가 존재하지 않으면 즉시 `FileNotFoundError`를 raise한다.
- TOML bytes는 UTF-8이어야 하며 아니면 `ValueError`를 raise한다.
- TOML parse 실패는 `ValueError`로 변환해 즉시 멈춘다.
- required table/string shape가 아니면 fallback 없이 `ValueError`를 raise한다.

## 직접 의존
- `pathlib.Path`
- `tomllib`
- type aliases for TOML shape

## 이 파일을 직접 쓰는 곳
- `src/peetsfea/pipeline/run_design.py`
- `src/peetsfea/pipeline/run_batch.py`
- `src/peetsfea/pipeline/selection/uniform_seedset.py`
- `src/peetsfea/backend/pyaedt/geometry/design_vars.py`
- 여러 pipeline/spec test modules

## 관련 테스트
- `tests/spec_resolver/test_sampling_registry.py`
- `tests/spec_resolver/test_selection_result.py`
- `tests/pipeline_runs/test_manifest_validation.py`
- `tests/pipeline_outputs/test_selection_snapshot_exports.py`

## 변경 시 주의점
- 반환 shape를 바꾸면 selection, replay, hashing, snapshot 흐름이 같이 깨질 수 있다.
- validator semantics를 완화하면 `CODE_COMMANDMENTS.md`의 fail-fast 방향과 충돌할 수 있다.
- 이 파일을 바꾸면 관련 테스트와 `sdd/architecture/current-pipeline-sdd-view.md`를 같이 확인한다.

## Graph links
- Primary owner: [type2-spec-boundary](../../../../architecture/type2-spec-boundary.md)
- Direct collaborator: [toml_render.py](toml_render.py.md)

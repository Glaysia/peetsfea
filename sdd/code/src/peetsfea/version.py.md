---
title: version.py
created: 2026-04-28 @ 00:00
updated: 2026-05-13 @ 00:00
tags:
  - version
  - sdd
---

# version.py

## Source
- Path: `src/peetsfea/version.py`
- Code note path: `sdd/code/src/peetsfea/version.py.md`
- Status: active

## 역할
- Package/spec version constants의 canonical owner다.

## 입력 / 출력
- 입력: 없음
- 출력: `SUPPORTED_SPEC_VERSION`, `__version__`

## Canonical state
- Current version baseline is `0.2.25.1`.
- `__version__` mirrors `SUPPORTED_SPEC_VERSION`.

## Invariants / fail-fast
- Runtime spec-version checks should compare against this constant.
- Version drift between package metadata and this module must be corrected immediately.

## Collaborators
- `pyproject.toml`
- [sdd-plans-index](../../../plans/sdd-plans-index.md)

## 관련 테스트
- Version synchronization tests should assert package/runtime constants match.

## 변경 시 주의점
- Legacy type1 expectations may pin older fixture text; do not update legacy fixtures unless explicitly doing legacy maintenance.

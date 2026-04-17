---
title: test_legacy_import_boundary.py
created: 2026-04-17 @ 16:02
updated: 2026-04-17 @ 16:02
tags:
  - legacy
  - governance
  - tests
---

# test_legacy_import_boundary.py

## Source
- Path: `tests/test_legacy_import_boundary.py`
- Code note path: `sdd/code/tests/test_legacy_import_boundary.py.md`

## 역할
- active 기본 수집 경로(`src/`, `entry/`, `tests/`)에서 legacy `type1` import가 다시 섞이지 않도록 정적 guard를 수행한다.

## 입력 / 출력
- 입력: repository Python source text
- 출력: offending file path list가 비어 있어야 한다는 pytest assertion

## Canonical state
- forbidden import prefix는 `peetsfea.legacy.type1` 하나다.
- `legacy/`, `__pycache__/`, `.venv/`, `.git/` 아래 파일은 검사 대상에서 제외한다.

## Invariants / fail-fast
- active tree에서 `peetsfea.legacy.type1` 문자열이 보이면 즉시 실패한다.
- legacy code는 explicit legacy path 안에서만 참조돼야 한다.

## 관련 테스트
- 이 파일 자체

## 변경 시 주의점
- active shared helper를 legacy로 옮긴 뒤 다시 active surface에서 참조해야 한다면, 이 테스트를 우회하지 말고 shared helper로 재분리해야 한다.

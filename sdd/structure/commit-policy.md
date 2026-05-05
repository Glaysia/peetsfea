---
title: Commit Policy
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - governance
---

# Commit Policy

## Goal
- 커밋은 SDD 추적 단위와 구현 단위를 분리하지 않게 만든다.
- 변경 이력을 사람이 읽을 수 있는 논리 단위로 유지한다.
- 파일 수 기준은 커밋 품질을 돕는 보조 규칙으로만 사용한다.

## Grouping Rules
- 커밋은 논리 단위를 우선한다.
- 관련 파일이 자연스럽게 5개 이상이면 한 커밋에 함께 묶는다.
- 5개 이상을 맞추기 위해 무관한 파일을 끼우지 않는다.
- 여러 기능이나 서로 다른 검증 범위가 섞이면 커밋을 분리한다.
- 공유 인덱스 문서는 hunk 단위로 stage해서 아직 포함되지 않은 문서를 먼저 가리키지 않게 한다.

## SDD Coupling
- `src/`, `entry/`, `tests/`의 새 Python 파일 또는 실질 수정 파일은 같은 커밋에 대응 `sdd/code/` note를 포함한다.
- 신규 기능이나 큰 리팩터링은 같은 커밋에 관련 `sdd/plans/` note를 포함한다.
- 문서 배치, ownership, 운영 규칙이 바뀌면 관련 `sdd/structure/` note와 허브 링크를 같은 커밋에 포함한다.
- SDD 링크를 추가할 때는 가능한 한 실제 `.md` 파일을 가리키는 path-qualified Markdown 상대경로 링크를 쓴다.

## Exclusions
- 생성물, cache, `run/` 산출물, AEDT output, `.aedt.lock` 파일은 명시 요청 없이는 커밋하지 않는다.
- `.obsidian` workspace 상태는 기본적으로 제외한다.
- SDD vault 상태 보존을 사용자가 명시적으로 요청한 경우에만 `.obsidian` 변경을 포함한다.
- GUI/AEDT 검증 산출물은 사용자가 명시적으로 요청하지 않았으면 커밋하지 않는다.

## Commit Message
- 기본 형식은 `<area>: <summary>`다.
- `area`는 `sdd`, `type2`, `tx_rect_void`, `spec`, `aedt`, `tests`처럼 변경의 주 소유 영역을 쓴다.
- summary는 명령형 또는 명사형 중 하나로 짧게 쓰되, 같은 작업 묶음에서는 일관성을 유지한다.
- 릴리스 커밋은 기존 release 형식을 따른다.

## Pre-Commit Checks
- 커밋 직전 `git status --short --untracked-files=all`로 예상 밖 변경이 없는지 확인한다.
- 순수 Python 테스트는 `.venv`와 `run/` cwd 규칙을 우선한다.
- Pylance 계열 진단은 가능한 경우 `.venv/bin/pyright`로 확인한다.
- GUI/AEDT 검증은 사용자가 명시적으로 요청한 현재 작업에서만 수행한다.

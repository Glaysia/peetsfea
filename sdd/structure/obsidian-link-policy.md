---
title: Obsidian Link Policy
created: 2026-04-17 @ 20:25
updated: 2026-04-18 @ 18:46
tags:
  - sdd
  - obsidian
  - structure
---

# Obsidian Link Policy

이 문서는 SDD markdown를 Obsidian graph에서 읽히게 유지하기 위한 링크 위생 규칙을 정의한다. 상위 허브는 [[sdd/structure/sdd-structure-index]]다.

## Goal
- 문서 탐색용 wikilink는 유지하되, graph를 의미 없는 대형 허브로 만들지 않는다.
- 문서 간 직접 ownership, boundary, verification 관계만 graph edge로 남긴다.
- backlog, inventory, historical context는 문서 안에 남기되 graph edge로 승격하지 않는다.

## Allowed Link Roles
- `parent hub`: 이 문서가 속한 직접 상위 허브 1개
- `primary plan`: 이 문서가 직접 구현하거나 따르는 핵심 계획 1개
- `primary architecture/structure`: 이 문서의 직접 경계나 배치 규칙을 소유하는 상위 구조 문서 1개
- `direct collaborator`: 이 문서가 직접 호출하거나 직접 협력하는 owner-level 문서
- `direct verification`: 이 문서를 직접 방어하는 대표 테스트나 대표 소비자

위 다섯 역할 밖의 관련성은 기본적으로 wikilink가 아니라 plain text path 또는 inline code로 기록한다.

## Demotion Rules
- 아래 항목은 graph edge로 만들지 않고 plain text/code path로 기록한다:
  - backlog 목록
  - split map
  - bulk inventory
  - future work / TODO registry
  - historical context
  - broad relatedness
  - helper-module enumeration
- 같은 문서에서 이미 한 번 연결한 대상은 다시 링크하지 않는다. 반복 언급은 plain text로 내린다.
- index note는 전체 목록을 링크하지 않는다. canonical entrypoint만 링크하고 나머지는 경로 인벤토리로 적는다.

## Budget By Note Type
- code note:
  - parent hub는 필요할 때만 1개
  - primary plan 최대 1개
  - primary architecture/structure 최대 1개
  - direct collaborator 최대 4개
  - direct verification 최대 2개
- plan note:
  - parent/umbrella plan 최대 1개
  - primary architecture note 최대 1개
  - directly affected code notes 최대 5개
- architecture note:
  - boundary owner만 링크한다.
  - helper implementation, supporting module, 상세 inventory는 plain text로 적는다.
- index note:
  - direct hub와 canonical entrypoint만 링크한다.
  - bulk registry, plan inventory, split inventory는 plain text path inventory로 적는다.

## Practical Rules
- code note는 graph를 설명 문맥이 아니라 ownership map으로 취급한다.
- plan note는 영향 범위를 다 보여주기보다 현재 구현 결정을 추적하는 진입점만 남긴다.
- architecture note는 경계 소유자와 handoff 문서만 연결하고, 내부 세부 helper는 경로만 적는다.
- 새 문서를 만들 때는 "이 링크가 local graph에서 직접 구조를 드러내는가"를 먼저 확인한다. 아니면 plain text로 내린다.

## Review Checklist
- 이 링크가 다섯 allowed roles 중 하나인가?
- 이 링크가 문서 안에서 중복되는가?
- 이 목록은 inventory인가, ownership map인가?
- 이 helper는 boundary owner인가?
- plain text path로 적어도 탐색성이 충분한가?

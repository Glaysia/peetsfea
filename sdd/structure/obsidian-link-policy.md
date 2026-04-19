---
title: Obsidian Link Policy
created: 2026-04-17 @ 20:25
updated: 2026-04-20 @ 01:30
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
- graph 품질을 "허브 억제"만으로 정의하지 않는다. local cluster, handoff 경로, 대표 검증 경로도 읽혀야 한다.
- template/archive 성격을 제외한 note는 vault 안으로 들어오는 경로와 나가는 경로를 최소 1개 이상 가져야 한다.

## Allowed Link Roles
- `parent hub`: 이 문서가 속한 직접 상위 허브 1개
- `primary plan`: 이 문서가 직접 구현하거나 따르는 핵심 계획 1개
- `primary architecture/structure`: 이 문서의 직접 경계나 배치 규칙을 소유하는 상위 구조 문서 1개
- `direct collaborator`: 이 문서가 직접 호출하거나 직접 협력하는 owner-level 문서
- `direct verification`: 이 문서를 직접 방어하는 대표 테스트나 대표 소비자
- `discovery bridge`: sink/star leaf를 피하기 위한 최소 연결 1개. broad relatedness가 아니라 nearest owner, nearest sibling canonical note, 또는 direct consumer만 허용한다.

위 여섯 역할 밖의 관련성은 기본적으로 wikilink가 아니라 plain text path 또는 inline code로 기록한다.

## Minimum Connectivity
- `sdd/templates/`, release note, archive, generated registry 성격의 note는 최소 연결성 budget에서 제외한다.
- 나머지 note는 새로 만들거나 실질 수정할 때 같은 변경 안에서 기존 note 1개 이상이 새 note를 가리키게 만든다.
- code note:
  - outbound 최소 2개
  - owner 문서(`primary plan` 또는 `primary architecture/structure`) 1개는 필수다.
  - verification/collaborator/discovery bridge 중 최소 1개는 추가한다.
- test note:
  - outbound 최소 2개
  - 직접 방어하는 code note 1개와 owning plan/architecture 1개를 남긴다.
- diagram note:
  - outbound 최소 2개
  - owning architecture 1개와 primary plan 또는 primary consumer 1개를 남긴다.
- plan note:
  - outbound는 현재 결정 추적에 필요한 범위로 제한하되, landing 후 inbound 최소 1개를 가진다.
  - relevant hub, structure note, architecture note 중 최소 1곳에서 다시 가리켜야 한다.
- index/hub note:
  - canonical entrypoint만 직접 링크한다.
  - 동일 주제 sibling가 8개를 넘으면 one-hop sub-hub 또는 topic split을 만든다.
- inbound 0 또는 outbound 0인 non-exempt note는 예외로 두지 않는다.
  - 같은 변경에서 연결을 추가하거나
  - 문서 본문에 temporary isolation 사유와 owning follow-up note를 plain text로 남긴다.

## Anti-Star Rules
- 한 hub/index 문서가 많은 child를 직접 나열해 star graph를 만들면 안 된다.
- sibling note 여러 개가 parent hub 하나만 공유하고 서로 아무도 연결하지 않으면, 아래 둘 중 하나를 한다:
  - canonical sibling 1~2개에 direct collaborator/discovery bridge를 추가한다.
  - topic sub-hub를 만들어 parent 부하를 분리한다.
- test cluster는 inbound-only sink가 되면 안 된다. 대표 테스트는 defended code note와 owning plan/architecture를 다시 링크한다.
- diagram note는 screenshot/archive leaf가 아니라 ownership handoff note여야 한다. consumer 또는 owner로 되돌아가는 링크를 남긴다.
- release note, template, registry, backlog index는 star pattern을 만들 수 있으므로 default graph 품질 판단에서 제외하고, 필요하면 graph filter에서 숨긴다.

## Demotion Rules
- 아래 항목은 graph edge로 만들지 않고 plain text/code path로 기록한다:
  - backlog 목록
  - split map
  - bulk inventory
  - future work / TODO registry
  - historical context
  - broad relatedness
  - helper-module enumeration
  - bulk release note listing
  - template catalog
- 같은 문서에서 이미 한 번 연결한 대상은 다시 링크하지 않는다. 반복 언급은 plain text로 내린다.
- index note는 전체 목록을 링크하지 않는다. canonical entrypoint만 링크하고 나머지는 경로 인벤토리로 적는다.

## Budget By Note Type
- code note:
  - parent hub는 필요할 때만 1개
  - primary plan 최대 1개
  - primary architecture/structure 최대 1개
  - direct collaborator 최대 4개
  - direct verification 최대 2개
  - discovery bridge 최대 1개
- plan note:
  - parent/umbrella plan 최대 1개
  - primary architecture note 최대 1개
  - directly affected code notes 최대 5개
  - discovery bridge 최대 1개
- architecture note:
  - boundary owner만 링크한다.
  - helper implementation, supporting module, 상세 inventory는 plain text로 적는다.
  - hub 역할이 강해질 때는 canonical handoff note만 링크하고 topic sub-hub를 추가한다.
- index note:
  - direct hub와 canonical entrypoint만 링크한다.
  - bulk registry, plan inventory, split inventory는 plain text path inventory로 적는다.
  - child note 다수가 sink가 되면 one-hop sub-hub를 만든다.

## Practical Rules
- code note는 graph를 설명 문맥이 아니라 ownership map으로 취급한다.
- plan note는 영향 범위를 다 보여주기보다 현재 구현 결정을 추적하는 진입점만 남긴다.
- architecture note는 경계 소유자와 handoff 문서만 연결하고, 내부 세부 helper는 경로만 적는다.
- 새 문서를 만들 때는 "이 링크가 local graph에서 직접 구조를 드러내는가"를 먼저 확인한다. 아니면 plain text로 내린다.
- 새 문서를 만들면 "이 note를 누가 가리키는가"와 "이 note가 어디로 되돌아가는가"를 둘 다 확인한다.
- graph에서 큰 허브 하나와 degree-1 leaf 여러 개만 남는다면, 링크 수를 더 줄이기보다 sub-hub 또는 discovery bridge를 먼저 고려한다.

## Review Checklist
- 이 링크가 여섯 allowed roles 중 하나인가?
- 이 링크가 문서 안에서 중복되는가?
- 이 목록은 inventory인가, ownership map인가?
- 이 helper는 boundary owner인가?
- plain text path로 적어도 탐색성이 충분한가?
- 이 note는 non-exempt인데 inbound 0 또는 outbound 0이 아닌가?
- 이 변경이 새로운 star cluster 또는 inbound-only sink를 만들지는 않는가?

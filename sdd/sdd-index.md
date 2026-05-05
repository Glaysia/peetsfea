---
title: SDD Vault
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - sdd
---

# SDD Vault

이 공간은 `0.2.22+` 이후 변경을 위한 옵시디언 중심 설계 문서 허브다. 규칙 원문은 `SDD.md`를 본다.

## 시작점
- 정책: [SDD](../SDD.md)
- 코드 대응 문서 허브: [sdd-code-index](code/sdd-code-index.md)
- 계획 허브: [sdd-plans-index](plans/sdd-plans-index.md)
- 아키텍처 허브: [sdd-architecture-index](architecture/sdd-architecture-index.md)
- 구조 허브: [sdd-structure-index](structure/sdd-structure-index.md)
- 다이어그램 허브: [sdd-diagrams-index](diagrams/sdd-diagrams-index.md)

## 운영 루프
1. 큰 변경이면 먼저 [sdd-plans-index](plans/sdd-plans-index.md)에 계획을 남긴다.
2. 경계/흐름/레이어 변경이면 [sdd-architecture-index](architecture/sdd-architecture-index.md) 또는 [sdd-structure-index](structure/sdd-structure-index.md)를 갱신한다.
3. 같은 변경 안에서 대응 코드 노트를 만든다.
4. 필요한 경우 [sdd-diagrams-index](diagrams/sdd-diagrams-index.md)에 Mermaid 구조도를 추가한다.
5. 커밋은 [commit-policy](structure/commit-policy.md)에 따라 논리 단위와 SDD note를 함께 묶는다.

## 경계
- 현재는 forward-only 도입이다.
- untouched 레거시 코드는 자동 백필하지 않는다.
- 새로 만들거나 실질 수정한 `src/`, `entry/`, `tests/` 코드부터 강제한다.

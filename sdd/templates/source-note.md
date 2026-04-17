---
title: Source Note Template
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - sdd
---

# Source Note Template

이 템플릿은 코드 대응 문서의 기본 골격이다. 실제 링크는 직접 관련 계획, 협력 코드, 테스트, 구체적 docs/architecture/diagram에만 추가한다.

## Source
- Path: `<repo-relative-path>`
- Code note path: `sdd/code/<repo-relative-path>.md`
- Related plan: `<direct plan note only when one exists>`
- Related docs/architecture/diagram: `<direct note only when it explains this file>`

## 역할
- 이 파일의 단일 책임을 한두 문장으로 적는다.

## 입력 / 출력
- 핵심 함수, 클래스, CLI entry, 반환값, 부작용을 적는다.

## Canonical state
- 이 파일이 보유하는 canonical state를 적는다.
- state가 없다면 명시적으로 "없음"이라고 적는다.

## Invariants / fail-fast
- 반드시 유지해야 하는 invariant를 적는다.
- 실패 시 즉시 raise해야 하는 지점을 적는다.

## 직접 의존
- 직접 import/호출하는 핵심 모듈을 적는다.

## 이 파일을 쓰는 곳
- 이 파일을 직접 import/호출하는 대표 코드와 테스트를 적는다.

## 관련 테스트
- 직접 방어하는 테스트 파일이나 시나리오를 적는다.

## 변경 시 주의점
- 바꾸면 같이 깨질 수 있는 계약, 역링크해야 하는 문서, 리플레이/결정성/SSOT 주의점을 적는다.

## Links
- `<direct collaborator/test/plan note>`

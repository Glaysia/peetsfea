---
title: toml_render.py
created: 2026-04-18 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - spec
  - toml
---

# toml_render.py

## Source
- Path: `src/peetsfea/spec/toml_render.py`
- Code note path: `sdd/code/src/peetsfea/spec/toml_render.py.md`
- Related plan: [[sdd/plans/0.2.23-type2-sampled-build-split]]

## 역할
- active path에서 사용할 generic TOML serializer를 제공한다.
- sampled type2 TOML 같은 generated TOML artifact를 legacy helper에 기대지 않고 쓸 수 있게 한다.

## 입력 / 출력
- 입력: `TOMLTable`
- 출력: UTF-8 TOML text

## Canonical state
- module-level mutable state는 없다.
- active serializer surface는 `toml_dumps()` 하나다.

## Invariants / fail-fast
- unsupported TOML value type은 즉시 실패한다.
- array-of-tables와 nested tables ordering을 입력 table 순서대로 유지한다.

## 직접 의존
- [[sdd/code/src/peetsfea/spec/loader.py]]

## 관련 테스트
- indirect coverage:
  - [[sdd/code/tests/type2/test_sample_type2_entry.py]]

## 변경 시 주의점
- active type2가 legacy type1 TOML dump helper를 다시 직접 의존하게 만들지 않는다.

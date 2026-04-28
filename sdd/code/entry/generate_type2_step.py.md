---
title: generate_type2_step.py
created: 2026-04-17 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - entry
  - step-export
---

# generate_type2_step.py

## Source
- Path: `entry/generate_type2_step.py`
- Code note path: `sdd/code/entry/generate_type2_step.py.md`
- Status: active

## 역할
- type2 source/sampled TOML을 STEP scene과 ledger artifact로 export하는 CLI entrypoint다.
- 0.2.24 SDD 기준 RX geometry and non-modeled guide/context export만 active contract로 문서화한다.

## 입력 / 출력
- 입력: type2 TOML path, output directory, optional seed/reporting options
- 출력: `type2_scene.step`, `type2_step_ledger.json`

## Canonical state
- CLI delegates validation/export to library code.
- `tx_region` may be emitted as non-modeled guide context.
- RxOnly setup must not depend on TX modeled geometry from this entrypoint.

## Invariants / fail-fast
- Export failures raise immediately.
- Generic exported body-name drift is a contract failure.

## Collaborators
- [type2_step_export.py](../src/peetsfea/type2_step_export.py.md)
- [type2_step_spec.py](../src/peetsfea/type2_step_spec.py.md)

---
title: type2_step_post_import_mesh.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - em
  - pyaedt
---

# type2_step_post_import_mesh.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py.md`
- Status: active

## 역할
- STEP import 후 setup-ready mesh operation을 적용한다.
- 0.2.24 SDD 기준 RxOnly conductor-only mesh target을 소유한다.

## 입력 / 출력
- 입력: HFSS design, imported RX conductor names, mesh policy
- 출력: `Length1` mesh operation

## Canonical state
- Mesh target set contains RX conductor bodies only.
- `tx_region` and other non-modeled guide/context objects are never mesh targets.

## Invariants / fail-fast
- Missing RX conductor target fails immediately.
- PyAEDT mesh assignment false returns fail immediately.
- RxOnly must not include TX bodies in the mesh payload.

## Collaborators
- [type2_step_em_input.py](type2_step_em_input.py.md)
- [type2-step-to-em-validate-pipeline](../../../../../architecture/type2-step-to-em-validate-pipeline.md)

---
title: type2_step_post_import_mesh.py
created: 2026-04-18 @ 09:09
updated: 2026-04-29 @ 00:00
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
- `RxOnly` conductor-only mesh target and `TxRx` TX inner + RX conductor mesh targets을 소유한다.
- TX inner conductor names must be deterministic and role-specific; generic `tx_copper_*` matching is not sufficient.

## 입력 / 출력
- 입력: HFSS design, imported TX inner/RX conductor names, mesh policy
- 출력: `Length1` mesh operation

## Canonical state
- Mesh target set contains only RX conductor bodies in RxOnly and TX inner + RX conductor bodies in TxRx.
- `tx_region` and other non-modeled guide/context objects are never mesh targets.
- TX inner mesh lookup uses `tx_inner_copper_l*` / `tx_inner_copper_stack` explicitly; it does not fall back to `tx_copper_*`.

## Invariants / fail-fast
- Missing RX or TX role-specific conductor target fails immediately with role and available names context.
- Unsupported TX role families are rejected before mesh assignment.
- PyAEDT mesh assignment false returns fail immediately.
- RxOnly must not include TX bodies in the mesh payload.

## Collaborators
- [type2_step_em_input.py](type2_step_em_input.py.md)
- [type2-step-to-em-validate-pipeline](../../../../../architecture/type2-step-to-em-validate-pipeline.md)

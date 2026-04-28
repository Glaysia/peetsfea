---
title: type2_step_scene.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - scene
  - step-export
---

# type2_step_scene.py

## Source
- Path: `src/peetsfea/type2_step_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_scene.py.md`
- Status: active

## 역할
- type2 scene assembly facade다.
- 0.2.24 SDD 기준 RX geometry and non-modeled guide/context assembly만 active contract다.

## Canonical state
- RX scene bodies are deterministic and exact.
- `tx_region` is future placement guide context only.
- RxOnly scene assembly must not require TX modeled geometry.

## Invariants / fail-fast
- Missing RX inputs or unsupported object ids fail immediately.
- TX guide context must not become mesh, port, or report owner.

## Collaborators
- [type2_non_model_scene.py](type2_non_model_scene.py.md)
- [type2_step_export.py](type2_step_export.py.md)

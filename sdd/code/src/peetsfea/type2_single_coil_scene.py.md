---
title: type2_single_coil_scene.py
created: 2026-04-20 @ 00:00
updated: 2026-04-28 @ 00:00
tags:
  - rx
  - scene
---

# type2_single_coil_scene.py

## Source
- Path: `src/peetsfea/type2_single_coil_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_single_coil_scene.py.md`
- Status: active

## 역할
- RX single-coil and geometry-only TX inner single-coil scene assembly helper다.

## Invariants / fail-fast
- Invalid RX scene dimensions fail immediately.
- Invalid TX inner scene dimensions fail immediately.
- TX inner scene assembly computes mm outer ranges from the resolved `tx_inner_region` owner before building the rect-void geometry.
- TX ferrite/underlay contracts are not active for `tx_inner_single_coil`.

## Collaborators
- [type2_step_scene.py](type2_step_scene.py.md)

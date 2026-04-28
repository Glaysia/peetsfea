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
- RX single-coil scene assembly helper다.

## Invariants / fail-fast
- Invalid RX scene dimensions fail immediately.
- TX ferrite/group shape contracts are not active SDD contracts during the reset.

## Collaborators
- [type2_step_scene.py](type2_step_scene.py.md)

---
title: type2_step_import_style.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - import
  - pyaedt
---

# type2_step_import_style.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_style.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py.md`
- Status: active

## 역할
- Imported RX conductor/context objects에 material/color/name styling을 적용한다.
- RX port sheet reconstruction support remains runtime metadata, not imported STEP geometry.

## 입력 / 출력
- 입력: partitioned imported object groups, HFSS modeler
- 출력: styled imported objects and runtime reconstructed RX sheet geometry where needed

## Canonical state
- RX conductor receives conductor material/styling.
- Non-modeled guide/context objects remain non-conductor context.
- RxOnly creates no TX reconstructed sheets.

## Invariants / fail-fast
- Missing required RX imported objects fail immediately.
- Styling false returns fail immediately.
- Guide/context bodies must not be treated as conductor bodies.

## Collaborators
- [type2_step_import_core.py](type2_step_import_core.py.md)
- [type2_step_port_assignment.py](type2_step_port_assignment.py.md)

---
title: type2_single_coil_ports.py
created: 2026-04-20 @ 00:00
updated: 2026-04-28 @ 00:00
tags:
  - rx
  - ports
---

# type2_single_coil_ports.py

## Source
- Path: `src/peetsfea/type2_single_coil_ports.py`
- Code note path: `sdd/code/src/peetsfea/type2_single_coil_ports.py.md`
- Status: active

## 역할
- RX single-coil terminal metadata helper다.

## Invariants / fail-fast
- Missing or ambiguous RX terminal metadata fails immediately.

## Collaborators
- [type2_step_port_assignment.py](backend/pyaedt/type2_step_port_assignment.py.md)

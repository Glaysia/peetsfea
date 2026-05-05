---
title: type2-plate-stack
created: 2026-04-19 @ 21:20
updated: 2026-04-28 @ 00:00
tags:
  - type2
  - rx
  - plate-stack
  - hfss
---

# Type2 Plate Stack

This document is no longer a shared paired-coil runtime contract.

## Status
- Active type2 setup-ready is RxOnly.
- Plate-stack material remains component/reference material only unless an active RX path explicitly selects it.
- Transmitter-side plate-stack geometry, ports, groups, arrays, and report variables are not active type2 contracts.

## Active Reference
- RX role-local notes live in [`docs/type2-rx-plate-stack.md`](type2-rx-plate-stack.md).
- Active setup/report behavior is summarized in [`docs/current-pipeline.md`](current-pipeline.md).
- Shape-independent report variable continuity is documented in `sdd/architecture/type2-em-report-contract.md`.

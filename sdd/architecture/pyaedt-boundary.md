---
title: PyAEDT Boundary
created: 2026-05-03 @ 00:00
updated: 2026-06-01 @ 00:00
tags:
  - aedt
  - pyaedt
  - sdd
---

# PyAEDT Boundary

This note owns raw PyAEDT access for the 0.3.0 minimal path. It keeps code notes under `src/peetsfea/aedt/` and headless backend helpers attached to one boundary.

## Boundary Role
- Wrap raw PyAEDT/HFSS objects behind validated repository-owned surfaces.
- Convert PyAEDT `False` returns into immediate exceptions.
- Provide Protocol contracts for fake sessions and headless backend runtime modules.
- Keep headless AEDT validation as the authoritative completion gate for AEDT/PyAEDT behavior. GUI launch behavior may help diagnosis but does not replace headless validation.

## Owned Code Notes
- [protocols.py](../code/src/peetsfea/aedt/protocols.py.md)
- [proxies.py](../code/src/peetsfea/aedt/proxies.py.md)
- [wrappers.py](../code/src/peetsfea/aedt/wrappers.py.md)
- [wrappers_common.py](../code/src/peetsfea/aedt/wrappers_common.py.md)
- [wrappers_modules.py](../code/src/peetsfea/aedt/wrappers_modules.py.md)
- [wrappers_hfss.py](../code/src/peetsfea/aedt/wrappers_hfss.py.md)

## Active Handoff
- Minimal STEP setup/solve consumes this boundary through [minimal_em.py](../code/src/peetsfea/backend/pyaedt/minimal_em.py.md).

## Graph Intent
- This node is intentionally high-degree: it is the canonical owner for raw AEDT access, fake-session protocol shape, and fail-fast PyAEDT wrappers.
- Wrapper/proxy sibling notes should link to this owner first.

---
title: PyAEDT Boundary
created: 2026-05-03 @ 00:00
updated: 2026-05-03 @ 00:00
tags:
  - aedt
  - pyaedt
  - sdd
---

# PyAEDT Boundary

This note owns the graph cluster for raw PyAEDT access. It exists so code notes under `src/peetsfea/aedt/` and shared HFSS session helpers do not form a sibling mesh in Obsidian graph view.

## Boundary Role
- Wrap raw PyAEDT/HFSS objects behind validated repository-owned surfaces.
- Keep `False`-return conversion, dynamic attribute validation, and raw-session shape checks at the AEDT boundary.
- Provide Protocol contracts for fake sessions and backend runtime modules.
- Keep planned wrapper/proxy split notes attached to this boundary until their source files exist.

## Owned Code Notes
- [protocols.py](../code/src/peetsfea/aedt/protocols.py.md)
- [wrappers.py](../code/src/peetsfea/aedt/wrappers.py.md)
- [wrappers_common.py](../code/src/peetsfea/aedt/wrappers_common.py.md)
- [wrappers_modules.py](../code/src/peetsfea/aedt/wrappers_modules.py.md)
- [wrappers_hfss.py](../code/src/peetsfea/aedt/wrappers_hfss.py.md)
- [proxies_base.py](../code/src/peetsfea/aedt/proxies_base.py.md)
- [proxies_ops.py](../code/src/peetsfea/aedt/proxies_ops.py.md)
- [proxies_inspect.py](../code/src/peetsfea/aedt/proxies_inspect.py.md)
- [type2_step_runtime_common.py](../code/src/peetsfea/backend/pyaedt/type2_step_runtime_common.py.md)

## Exceptional Handoffs
- Type2 STEP import consumes this boundary through [type2-step-import-boundary](type2-step-import-boundary.md).
- Type2 setup-ready and solve consume this boundary through [type2-em-setup-boundary](type2-em-setup-boundary.md).
- Report variable ownership remains outside this boundary in [type2-em-report-contract](type2-em-report-contract.md).

## Graph Intent
- This node is intentionally high-degree: it is the canonical owner for raw AEDT access, fake-session protocol shape, and fail-fast PyAEDT wrappers.
- Wrapper/proxy sibling notes should link to this owner first. Sibling links are reserved for split handoffs such as common helpers feeding module/HFSS wrappers.

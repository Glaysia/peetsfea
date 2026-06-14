---
title: proxies.py
created: 2026-06-01 @ 00:00
updated: 2026-06-01 @ 00:00
tags:
  - aedt
  - fail-fast
---

# proxies.py

## Source
- Path: `src/peetsfea/aedt/proxies.py`
- Code note path: `sdd/code/src/peetsfea/aedt/proxies.py.md`
- Primary graph owner: [pyaedt-boundary](../../../../architecture/pyaedt-boundary.md)

## Single Responsibility
- Wrap raw PyAEDT/session objects behind explicit structural protocol boundaries.
- Provide fail-fast helper functions for AEDT operations used by headless setup and tests.

## Inputs / Outputs
- Input: raw AEDT objects, protocol-shaped sessions, operation names, payloads, validated object names.
- Output: wrapped protocol sessions, primitive operation results, and immediate exceptions for invalid names or `False` PyAEDT returns.

## Canonical State
- Proxy instances retain only the raw wrapped object reference.
- Module-level cache reset sentinel is immutable.

## Invariants
- Required attributes are asserted before binding and before use.
- Required callables are returned as callable objects, not loose `object` values.
- AEDT name validation happens before mutation helpers issue calls.
- Fallback signature retries are forbidden.

## Fail-Fast Points
- Missing raw attributes assert immediately.
- PyAEDT calls returning `False` raise through `raise_on_false`.
- Invalid AEDT object names raise before reaching the raw API.

## Collaborators
- [protocols.py](protocols.py.md)
- [wrappers.py](wrappers.py.md)

## Related Tests
- [\_aedt_sidecar_support.py](../../../tests/backend_em/_aedt_sidecar_support.py.md)

## Change Hazards
- PyAEDT API drift changes protocol, proxy, and fake-test surfaces together.
- Keep this module headless and free of GUI launch behavior.

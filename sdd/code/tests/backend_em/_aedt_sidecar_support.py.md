---
title: _aedt_sidecar_support.py
created: 2026-06-01 @ 00:00
updated: 2026-06-01 @ 00:00
tags:
  - tests
  - aedt
---

# _aedt_sidecar_support.py

## Source
- Path: `tests/backend_em/_aedt_sidecar_support.py`
- Code note path: `sdd/code/tests/backend_em/_aedt_sidecar_support.py.md`

## Single Responsibility
- Hosts the shared pure-Python fake AEDT sidecar tests re-exported by the focused `test_aedt_sidecar_*` modules.
- Verifies fail-fast wrapper/proxy behavior and explicit AEDT protocol/proxy export lists without launching AEDT.

## Inputs / Outputs
- Input: fake modeler, design, module, object, and desktop classes local to the test helper.
- Output: pytest assertions for wrapper return handling, name validation, mutation helpers, module method payloads, and exported API names.

## Canonical State
- Test-local fake objects own call ledgers and mutation fields.
- The expected public API list mirrors `src/peetsfea/aedt/protocols.py` and `src/peetsfea/aedt/proxies.py`.

## Invariants
- PyAEDT calls returning `False` must raise through the wrapper/proxy surface.
- Public protocol exports include all structural boundaries used by headless EM setup, including `MeshModuleSession`.
- The helper must stay AEDT-free and deterministic.

## Fail-Fast Points
- Unsupported legacy keyword signatures raise `TypeError`.
- Invalid AEDT object names raise before fake calls are issued.
- Missing or stale exported names fail by exact list comparison.

## Collaborators
- [protocols.py](../../../src/peetsfea/aedt/protocols.py.md)
- [wrappers.py](../../../src/peetsfea/aedt/wrappers.py.md)

## Related Tests
- `tests/backend_em/test_aedt_sidecar_modeler.py`
- `tests/backend_em/test_aedt_sidecar_session.py`

## Change Hazards
- Adding or removing protocol methods requires synchronizing this helper, protocol code notes, and pyright checks.
- Do not add GUI/AEDT runtime requirements to this helper.

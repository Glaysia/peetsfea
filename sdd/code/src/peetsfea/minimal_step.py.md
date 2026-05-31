---
title: minimal_step.py
created: 2026-06-01
updated: 2026-06-01
tags:
  - sdd
  - code
---

# minimal_step.py

- Path: `src/peetsfea/minimal_step.py`
- Responsibility: build the minimal STEP scene and ledger from a validated 0.3.0 spec.
- Inputs: `MinimalSpec`, output directory, seed.
- Outputs: `minimal_scene.step`, `minimal_step_ledger.json`, and artifact metadata.
- Canonical state: generated body names, body roles, canonical coordinates, and port sheet vertices in the ledger.
- Invariants: body names are unique, all dimensions are positive, Tx/Rx body names remain fixed, and `bd.export_step` must return `True`.
- Fail-fast points: duplicate names, invalid body dimensions, failed STEP export, failed ledger serialization.
- Collaborators: [minimal_spec.py](minimal_spec.py.md), [minimal_em.py](backend/pyaedt/minimal_em.py.md).
- Tests: `tests/test_minimal_step.py`.
- Hazards: keep this module as the only active geometry generation owner.
- Related plan: [0.3.0 minimal step two port reset](../../plans/0.3.0-minimal-step-two-port-reset.md).

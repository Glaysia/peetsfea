---
title: minimal_spec.py
created: 2026-06-01
updated: 2026-06-01
tags:
  - sdd
  - code
---

# minimal_spec.py

- Path: `src/peetsfea/minimal_spec.py`
- Responsibility: parse and validate the 0.3.0 non-model-only TOML surface.
- Inputs: TOML file path.
- Outputs: immutable spec dataclasses for design units and non-model boxes.
- Canonical state: parsed TOML values after fail-fast validation.
- Invariants: schema/version must be 0.3.0 minimal, units must be `mm`, non-model boxes must be present and positive-sized, and old geometry sections are rejected.
- Fail-fast points: missing required keys, unsupported sections, duplicate IDs, non-positive sizes, unsupported primitive/kind state.
- Collaborators: [minimal_step.py](minimal_step.py.md), [sample.py](../../../entry/sample.py.md), [build.py](../../../entry/build.py.md).
- Tests: `tests/test_minimal_spec.py`.
- Hazards: do not reintroduce nullable runtime state or fallback parsing for old type2 geometry.
- Related plan: [0.3.0 minimal step two port reset](../../../plans/0.3.0-minimal-step-two-port-reset.md).

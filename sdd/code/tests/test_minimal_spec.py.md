---
title: test_minimal_spec.py
created: 2026-06-01
updated: 2026-06-01
tags:
  - sdd
  - code
---

# test_minimal_spec.py

- Path: `tests/test_minimal_spec.py`
- Responsibility: verify the 0.3.0 minimal TOML parser contract.
- Inputs: temporary TOML files.
- Outputs: parser assertions and fail-fast expectations.
- Canonical state: none.
- Invariants: non-model-only input passes, including restored `tv` context; old geometry sections fail.
- Fail-fast points: parser exceptions are expected for invalid inputs.
- Collaborators: [minimal_spec.py](../src/peetsfea/minimal_spec.py.md).
- Tests: this file.
- Hazards: keep tests focused on public TOML contract, not implementation details.
- Related plan: [0.3.0 minimal step two port reset](../plans/0.3.0-minimal-step-two-port-reset.md).

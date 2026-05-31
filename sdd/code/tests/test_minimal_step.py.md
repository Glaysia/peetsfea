---
title: test_minimal_step.py
created: 2026-06-01
updated: 2026-06-01
tags:
  - sdd
  - code
---

# test_minimal_step.py

- Path: `tests/test_minimal_step.py`
- Responsibility: verify minimal STEP artifact and ledger generation.
- Inputs: temporary minimal TOML files and monkeypatched STEP export functions.
- Outputs: ledger/body-name assertions and failure expectations.
- Canonical state: none.
- Invariants: body names are fixed and `bd.export_step` failure raises.
- Fail-fast points: failed export and invalid ledger state.
- Collaborators: [minimal_step.py](../src/peetsfea/minimal_step.py.md).
- Tests: this file.
- Hazards: do not depend on old type2 geometry helpers.
- Related plan: [0.3.0 minimal step two port reset](../plans/0.3.0-minimal-step-two-port-reset.md).

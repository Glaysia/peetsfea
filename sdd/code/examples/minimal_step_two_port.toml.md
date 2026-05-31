---
title: minimal_step_two_port.toml
created: 2026-06-01
updated: 2026-06-01
tags:
  - sdd
  - example
---

# minimal_step_two_port.toml

- Path: `examples/minimal_step_two_port.toml`
- Responsibility: canonical 0.3.0 non-model-only authoring example.
- Inputs: none.
- Outputs: parsed source for `entry/sample.py`.
- Canonical state: one `air_context` non-model box.
- Invariants: no modeled geometry, outputs, backend, simulation, or constraints sections.
- Fail-fast points: parser rejects this file if schema/version or non-model box shape drifts.
- Collaborators: [minimal_spec.py](../src/peetsfea/minimal_spec.py.md), [sample.py](../entry/sample.py.md).
- Related tests: `tests/test_minimal_spec.py`.
- Related plan: [0.3.0 minimal step two port reset](../plans/0.3.0-minimal-step-two-port-reset.md).

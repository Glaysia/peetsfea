---
title: Current Pipeline SDD View
created: 2026-04-17 @ 09:09
updated: 2026-06-01 @ 00:00
tags:
  - minimal
  - sdd
---

# Current Pipeline SDD View

This note summarizes the active 0.3.0 minimal STEP two-port pipeline. The public runtime overview is [current-pipeline](../../docs/current-pipeline.md).

## Boundary
- TOML SSOT is [minimal_step_two_port.toml](../../examples/minimal_step_two_port.toml).
- Parser ownership: [minimal_spec.py](../code/src/peetsfea/minimal_spec.py.md).
- STEP/ledger ownership: [minimal_step.py](../code/src/peetsfea/minimal_step.py.md).
- HFSS setup/solve ownership: [minimal_em.py](../code/src/peetsfea/backend/pyaedt/minimal_em.py.md).
- Entrypoint ownership: [sample.py](../code/entry/sample.py.md) and [build.py](../code/entry/build.py.md).

## Flow
1. `entry/sample.py` snapshots the source TOML and exports one minimal STEP scene.
2. `minimal_step.py` writes canonical body names, non-model state, copper bodies, and port sheet edge coordinates into `minimal_step_ledger.json`.
3. `entry/build.py` imports the STEP into headless HFSS through `minimal_em.py`.
4. HFSS setup assigns copper-pad mesh, radiation boundary, Tx/Rx lumped ports, source phase, setup, sweep, and report.
5. Optional solve exports the report CSV next to the `.aedt`.

## Structural Invariants
- Old modeled-object TOML sections are rejected before STEP generation.
- The only generated modeled metal is the fixed Tx/Rx port-cell pair.
- Non-model objects remain authored by TOML and are marked non-model after import.
- Failures raise immediately; fallback continuation is outside the active contract.

## Related Notes
- Plan: [0.3.0-minimal-step-two-port-reset](../plans/0.3.0-minimal-step-two-port-reset.md)
- Diagram: [sample-build-flow](../diagrams/sample-build-flow.md)

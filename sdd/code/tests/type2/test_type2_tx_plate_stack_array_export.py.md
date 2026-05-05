---
title: test_type2_tx_plate_stack_array_export.py
created: 2026-04-28 @ 19:40
updated: 2026-05-04 @ 00:00
tags:
  - test
  - type2
  - export
---

# test_type2_tx_plate_stack_array_export.py

## Source
- Path: `tests/type2/test_type2_tx_plate_stack_array_export.py`
- Code note path: `sdd/code/tests/type2/test_type2_tx_plate_stack_array_export.py.md`
- Status: active but xfailed while generic TX plate-stack export contracts are inactive.

## Single Responsibility
- Records the older type2 TX plate-stack array export contract, including branch rotation and exported body grouping expectations.
- Keeps the historical export assertions available for a future generic TX plate-stack reactivation.
- Covers the TX plate-stack array ferrite/PET_PSA-priority PCB clearance contract for branch PCB wall/coil bodies.

## Inputs / Outputs
- Inputs are test-local type2 TX plate-stack TOML fixtures and generated STEP artifacts.
- Outputs are ledger, body-name, group-name, canonical-coordinate, and terminal-metadata assertions.

## Canonical State
- The active RxOnly parser rejects generic `tx_plate_stack` before export.
- `tx_inner_single_coil` is the supported geometry-only TX path for current type2 work.

## Invariants
- Active RxOnly type2 export tests must not require generic TX plate-stack modeled objects.
- If generic TX plate-stack export support returns, remove or narrow the xfail and re-check geometry assertions against current ledger schema.
- For each branch, exported PCB wall/coil bodies should have no greater volume than the uncut branch source bodies after ferrite-family clearance while ferrite-family labels and `g_ferrite_tx` member order stay stable.

## Fail-Fast Points
- `load_type2_step_spec()` raises for unsupported generic TX roles in active RxOnly mode.
- STEP export assertions fail on missing expected bodies, groups, coordinates, or terminal metadata when the path is re-enabled.
- Clearance assertions fail on missing branch PCB/ferrite bodies, non-positive cut volumes, or residual PCB/ferrite overlap.

## Collaborators
- [type2_step_export.py](../../src/peetsfea/type2_step_export.py.md)
- [type2_plate_stack.py](../../src/peetsfea/type2_plate_stack.py.md)
- [type2_step_spec.py](../../src/peetsfea/type2_step_spec.py.md)

## Related Tests
- [test_generate_type2_step.py](test_generate_type2_step.py.md)

## Change Hazards
- Removing the xfail while generic TX plate-stack remains rejected will fail the active type2 suite.
- Ledger schema changes require updating the coordinate, body group, and terminal metadata assertions together.

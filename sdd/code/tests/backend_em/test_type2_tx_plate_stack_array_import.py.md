---
title: test_type2_tx_plate_stack_array_import.py
created: 2026-05-07 @ 00:00
updated: 2026-05-07 @ 00:00
tags:
  - test
  - import
  - plate-stack
---

# test_type2_tx_plate_stack_array_import.py

## Source
- Path: `tests/backend_em/test_type2_tx_plate_stack_array_import.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_tx_plate_stack_array_import.py.md`
- Status: active regression coverage for TX plate-stack array import fixtures.

## Responsibility
- Verify imported TX plate-stack array body names partition to the modeled `tx_plate_stack` entry.
- Verify array-style TX body names coexist with RX plate-stack bodies and strict non-model member partitioning.

## Inputs / Outputs
- Inputs: synthetic STEP ledger fixtures and fake imported object-name batches.
- Outputs: imported ledger assertions or fail-fast import errors.

## Canonical State
- Imported object batches must include all required non-model members from the shared plate-stack non-model fixture, including `tx_region_actual`.
- TX array expected names use branch-indexed plate-stack array labels and must not collapse to legacy single TX plate-stack labels.

## Invariants / Fail-Fast
- Missing expected modeled names fail before style/setup work.
- Generic `SOLID*` leakage remains a hard import-contract failure.
- Z overflow remains validated against `tx_region` outer bounds after object-name partitioning succeeds.

## Collaborators
- [test_type2_step_import_pipeline.py](test_type2_step_import_pipeline.py.md)
- [0.2.24 Type2 Trace Width Mesh Length](../../../plans/0.2.24-type2-trace-width-mesh-length.md)

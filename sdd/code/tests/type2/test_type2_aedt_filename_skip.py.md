---
title: test_type2_aedt_filename_skip.py
created: 2026-05-13 @ 00:00
updated: 2026-05-13 @ 00:00
tags:
  - test
  - type2
  - build
---

# test_type2_aedt_filename_skip.py

## Source
- Path: `tests/type2/test_type2_aedt_filename_skip.py`
- Code note path: `sdd/code/tests/type2/test_type2_aedt_filename_skip.py.md`
- Status: active

## Single Responsibility
- Focused pure-Python coverage for the type2 target-AEDT filename skip policy.
- Documents that sampled TOML metadata derives the design ID from sampled bytes and maps the target AEDT file to `<design_dir>/<design_id>.aedt`.
- Documents that default best-effort build treats an existing exact target AEDT file as already built without requiring an imported ledger.
- Documents that a missing exact target AEDT file remains eligible for the normal runner path.

## Inputs / Outputs
- Inputs: synthetic `sampled.toml` metadata, a synthetic source TOML path, local STEP ledger JSON, local AEDT marker files, and local fake runner/exporter callables.
- Outputs: `Type2BuildBatchResult` assertions over `built` and `skipped` entries plus captured fake runner calls.

## Canonical State
- `sampled.toml` bytes are the canonical input for the generated hash component of `design_id`.
- The target AEDT path is canonical only when it exactly equals the prepared build path `<design_id>.aedt`.
- A sibling or differently named AEDT file must not satisfy the skip policy.

## Invariants
- Tests must not launch AEDT and must not require PyAEDT.
- The local prepared build uses an active supported role set: `("rx_single_coil",)`.
- The STEP ledger is valid when testing imported-ledger independence so the test isolates AEDT filename skip behavior.
- The runner must not be called when the exact target AEDT file already exists.
- The runner must be called with the hash-derived target AEDT path when that exact file does not exist.

## Fail-Fast Points
- Unexpected exporter or runner calls raise `AssertionError`.
- Missing normal-runner calls fail through explicit call-count assertions.
- Hash-derived design ID or target path drift fails through direct manifest-entry assertions.

## Collaborators
- [type2_runtime.py](../../src/peetsfea/type2_runtime.py.md)
- [type2_sampled.py](../../src/peetsfea/type2_sampled.py.md)

## Related Tests
- [test_build_type2_entry.py](test_build_type2_entry.py.md)

## Change Hazards
- Keep this file small and focused; broader build CLI, manifest, persistent-worker, or AEDT setup behavior belongs in dedicated tests.
- If the design ID hashing contract changes, update the expected target-path assertions together with sampled manifest generation tests.
- If best-effort build changes its resume/skip policy, keep the exact-target and non-exact-target cases paired so false-positive filename reuse remains covered.

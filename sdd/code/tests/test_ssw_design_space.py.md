---
title: test_ssw_design_space.py
created: 2026-06-08
updated: 2026-06-14
tags:
  - sdd
  - code
  - test
---

# test_ssw_design_space.py

- Path: `tests/test_ssw_design_space.py`
- Responsibility: verify the public 0.3.1 SSW design-space inclusion, AEDT point identity API, and fixed TOML sampling API.
- Inputs: `examples/0.3.0_fixed.toml`, `examples/0.3.0_sweep.toml`, and temporary mutated candidate TOML files.
- Outputs: pytest assertions for subset checks, point checks, dimension count, free owner paths, deterministic hash/design/file identity, fixed TOML sampling, allowed larger candidate counts, violation reporting, and fail-fast identity rejection for range candidates.
- Canonical state: none.
- Invariants: the live reference sweep derives 20 free dimensions, excludes all TX under-coil owners as fixed disabled values, fixes TX/RX `void_profile` to scaled void profile `1`, and keeps the fixed example as a single point inside that space; split TX/RX ferrite ratios are independent owner paths, TX/RX MULL ferrite enable flags are fixed point ranges and do not enter `free_owner_paths`, continuous realized values drive the hash payload, sampled results expose every free path in `point_values`, random report API ledgers preserve setup pass counts and solve telemetry, and seed/count/grid do not enter the identity.
- Fail-fast points: invalid candidate TOML scenarios are expected to produce violations or raise during identity creation.
- Collaborators: [ssw_design_space.py](../src/peetsfea/ssw_design_space.py.md).
- Tests: this file.
- Hazards: keep tests on the public API and avoid relying on private TOML traversal helpers except for temporary fixture mutation helpers local to the test file.
- Related plans: [0.3.0 ssw aedt design space identity](../plans/0.3.0-ssw-aedt-design-space-identity.md), [0.3.0 ssw fixed toml sampling](../plans/0.3.0-ssw-fixed-toml-sampling.md).
